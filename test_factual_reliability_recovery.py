"""Model-free gates for the browser factual reliability recovery."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

from ai_advisor import (
    admission_profile_evidence,
    compare_programs,
    evaluate_admission_profile,
    find_programs,
    find_programs_by_admission_evidence,
    get_catalog_counts,
    resolve_academic_context,
    sanitize_student_answer,
)


MANUAL_PREFIX = [
    "hello",
    "do you offer any technology programs?",
    "do you offer any biotechnology or biochem programs?",
    "how many programs and courses does BCIT offer?",
    "to which engineering programs can I apply as an international student?",
    "can a red seal apply to any programs?",
    "which nursing programs can I apply as an international student?",
    "I have my Red Seal. Can I use that to get into any BCIT programs, or does it count toward admission requirements?",
    "ofreces programas de ingenieria?",
]


def replay(questions):
    state = None
    history = []
    results = []
    for question in questions:
        result = resolve_academic_context(question, history[-10:], None, state)
        state = result["conversation_state"]
        results.append(result)
        history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": "Saved browser response."},
        ])
    return results


class FactualReliabilityRecoveryTests(unittest.TestCase):
    def test_certified_catalog_counts_are_intact(self):
        self.assertEqual(get_catalog_counts(), {
            "course_record_count": 3976,
            "active_program_count": 374,
        })

    def test_subject_searches_return_program_ids_not_credentials(self):
        expected = {
            "engineering": {"8660BENG", "8030BENG", "8020BENG", "8610BENG"},
            "technology": {"8350BTECH", "8800BTECH", "8310BTECH"},
            "biotechnology or biochem": {"9940BSC"},
            "nursing": {"8875BSN", "810CBSN"},
        }
        for query, required in expected.items():
            ids = {row["program_id"] for row in find_programs(query)}
            self.assertTrue(required.issubset(ids), (query, required - ids))

    def test_spanish_engineering_routes_to_english_subject(self):
        ids = {row["program_id"] for row in find_programs("ofreces programas de ingenieria")}
        self.assertTrue({"8660BENG", "8030BENG", "8020BENG"}.issubset(ids))
        result = resolve_academic_context(
            "ofreces programas de ingenieria?", [], None, None
        )
        self.assertEqual(result["program_set_scope"], "engineering")

    def test_exact_program_name_wins_over_credential_category(self):
        rows = find_programs("Technology Management")
        self.assertEqual([row["program_id"] for row in rows], ["8350BTECH"])

    def test_manual_state_replay_switches_subjects_and_resolves_tm(self):
        final = replay(MANUAL_PREFIX + [
            "for the technology management program, I have english 12 with 68 percent, "
            "I have a diploma from BCIT, but I don't have work experience, can I apply to this program?"
        ])
        self.assertEqual(final[4]["program_set_scope"], "engineering")
        self.assertEqual(final[6]["program_set_scope"], "nursing programs")
        self.assertEqual(final[8]["program_set_scope"], "engineering")
        self.assertEqual(final[9]["program_id"], "8350BTECH")
        self.assertEqual(final[9]["conversation_state"]["scope"], "program")

    def test_international_subject_comparison_uses_certified_four_state(self):
        result = compare_programs(
            "Which nursing programs can I apply to as an international student?",
            scope_query="nursing",
        )
        by_id = {row["program_id"]: row for row in result["programs"]}
        self.assertIn("8875BSN", by_id)
        self.assertIn("810CBSN", by_id)
        self.assertEqual(by_id["810CBSN"]["certified_status"], "CONDITIONAL_RESTRICTED")
        self.assertTrue(all(row.get("certified_status") in {
            "ACCEPTED_AVAILABLE", "CONDITIONAL_RESTRICTED", "NOT_ACCEPTED",
            "UNKNOWN_NOT_PUBLISHED",
        } for row in by_id.values()))

    def test_technology_management_rule_and_profile_gate(self):
        evidence = admission_profile_evidence("8350BTECH")
        self.assertEqual(evidence["program_id"], "8350BTECH")
        self.assertIn(1186, evidence["rule_set_ids"])
        self.assertIn(1330, evidence["condition_ids"])
        self.assertEqual(evidence["english_studies_12_minimum_percent"], 67)
        self.assertEqual(evidence["minimum_relevant_work_experience_years"], 1)
        self.assertTrue(evidence["bcit_diploma_accepted"])
        result = evaluate_admission_profile(
            "8350BTECH",
            "I have English 12 with 68 percent, I have a diploma from BCIT, "
            "but I don't have work experience. Can I apply?",
        )
        self.assertEqual(result["requirements"]["english"]["status"], "MET")
        self.assertEqual(result["requirements"]["post_secondary"]["status"], "MET")
        self.assertEqual(result["requirements"]["work_experience"]["status"], "UNMET")
        self.assertEqual(result["overall"], "UNMET")

    def test_red_seal_search_reports_only_published_evidence(self):
        rows = find_programs_by_admission_evidence("Red Seal")
        by_id = {row["program_id"]: row for row in rows}
        self.assertTrue({"1320ADCERT", "8800BTECH", "6185ADCERT", "605DDIPMA"}.issubset(by_id))
        self.assertEqual(by_id["8800BTECH"]["condition_type"], "RED_SEAL_TRADE")
        self.assertIn(10, by_id["8800BTECH"]["condition_ids"])
        self.assertTrue(all(row["source_url"] for row in rows))

    def test_internal_tool_protocol_is_removed(self):
        leaked = (
            'functions.search_programs {"credential":"engineering"}\n'
            '{"query":"engineering","credential":"engineering"}\n'
            "BCIT offers Civil Engineering."
        )
        cleaned = sanitize_student_answer(leaked)
        self.assertEqual(cleaned, "BCIT offers Civil Engineering.")
        self.assertNotIn("functions.", cleaned)
        self.assertNotIn('"credential"', cleaned)

    def test_exact_manual_conversation_passes_real_endpoint_without_model(self):
        questions = MANUAL_PREFIX + [
            "for the technology management program, I have english 12 with 68 percent, "
            "I have a diploma from BCIT, but I don't have work experience, can I apply to this program?"
        ]
        history = []
        state = None
        responses = []
        with patch("ai_advisor.OpenAI", side_effect=AssertionError("model called")):
            with TestClient(app) as client:
                for question in questions:
                    response = client.post("/advisor", json={
                        "question": question,
                        "conversation": history[-10:],
                        "conversation_state": state,
                    })
                    self.assertEqual(response.status_code, 200, response.text)
                    data = response.json()
                    responses.append(data)
                    history.extend([
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": data["answer"]},
                    ])
                    state = data["conversation_state"]
        self.assertIn("certified international-availability", responses[4]["answer"])
        self.assertIn("published Red Seal admission evidence", responses[5]["answer"])
        self.assertIn("BCIT ofrece", responses[8]["answer"])
        self.assertEqual(responses[9]["conversation_state"]["program_id"], "8350BTECH")
        self.assertIn("UNMET", responses[9]["answer"])
        self.assertIn("at least 1 year", responses[9]["answer"])
        for response in responses:
            answer = response["answer"]
            self.assertNotRegex(answer, r"functions?\.|\"query\"\s*:|\"credential\"\s*:")
            self.assertNotRegex(answer, r"(?i)\b(?:we|Asteris) (?:offer|offers|require|requires)\b")


if __name__ == "__main__":
    unittest.main()
