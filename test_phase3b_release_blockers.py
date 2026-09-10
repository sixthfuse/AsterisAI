"""Model-free release gates for Phase 3B blocker root causes."""
import json
import unittest
from types import SimpleNamespace

from ai_advisor import (
    _scope_program_details,
    answer_student_question,
    certified_international_evidence,
    compare_programs,
    finalize_student_answer,
    get_program_details,
    resolve_academic_context,
)


class FailIfCalled:
    def create(self, **kwargs):
        raise AssertionError("deterministic Phase 3B gate called the model")


CLIENT = SimpleNamespace(responses=FailIfCalled())


class ToolClient:
    def __init__(self, tool, arguments):
        self.requests = []
        self.tool = tool
        self.arguments = arguments

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            return SimpleNamespace(id="first", output_text="", output=[SimpleNamespace(
                type="function_call", name=self.tool,
                arguments=json.dumps(self.arguments), call_id="call",
            )])
        return SimpleNamespace(id="second", output=[], output_text="Verified comparison.")


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
            {"role": "assistant", "content": "Saved verified response."},
        ])
    return results


class Phase3BReleaseBlockerTests(unittest.TestCase):
    def test_open_ended_plural_program_query_keeps_catalog_scope(self):
        result = resolve_academic_context("hey got any biochem programs?", [], None, None)
        self.assertEqual(result["conversation_state"]["scope"], "program_family")

    def test_named_campus_program_listing_keeps_campus_scope(self):
        result = resolve_academic_context(
            "Which programs are at the Aerospace Technology Campus?", [], None, None
        )
        self.assertEqual(result["conversation_state"]["scope"], "campus")

    def test_mandatory_alternate_entry_form_survives_length_cleanup(self):
        details = get_program_details("M600MSC")
        answer = finalize_student_answer(
            " ".join(["Admission details with verified evidence."] * 150),
            "What about its admission requirements?",
            [details],
        )
        self.assertIn("must submit the completed Pre-entry Assessment form", answer)

    def test_course_requirement_keeps_active_program(self):
        results = replay([
            "I'm in Construction Management Bachelor of Technology.",
            "For CMGT 8700, I have 1.5 years of related work experience. Enough?",
            "Correction: I have 2 years now.",
            "Does that mean I can graduate?",
        ])
        self.assertEqual([row["program_id"] for row in results], ["8800BTECH"] * 4)

    def test_applicant_credential_does_not_replace_target(self):
        results = replay([
            "Tell me about full-time Nursing BSN.",
            "I have a nursing background, but now I want to apply to Applied Computing MSc.",
            "What if I also have a civil engineering diploma?",
            "And its campus?",
        ])
        self.assertEqual([row["program_id"] for row in results],
                         ["8875BSN", "M600MSC", "M600MSC", "M600MSC"])

    def test_credential_correction_resolves_same_name_peers(self):
        results = replay([
            "Tell me about Construction Management.",
            "The BTech, please.",
            "Actually the diploma, not the degree.",
            "What's the credential for this one?",
        ])
        self.assertEqual([row["program_id"] for row in results[1:]],
                         ["8800BTECH", "7710DIPMA", "7710DIPMA"])

    def test_three_member_comparison_survives_followups(self):
        results = replay([
            "Compare the Nursing BSN full-time, Applied Computing MSc, and Construction Management BTech.",
            "Which of them are degrees?",
            "Are these all at the same campus?",
        ])
        expected = {"8875BSN", "M600MSC", "8800BTECH"}
        for row in results:
            self.assertEqual(set(row["comparison_program_ids"]), expected)

    def test_three_member_comparison_followup_forces_exact_comparison_tool(self):
        state = replay([
            "Compare the Nursing BSN full-time, Applied Computing MSc, and Construction Management BTech."
        ])[0]["conversation_state"]
        responses = ToolClient("compare_programs", {"query": "Which of them are degrees?"})
        answer_student_question(
            "Which of them are degrees?", [], conversation_state=state,
            client=SimpleNamespace(responses=responses),
        )
        self.assertEqual(responses.requests[0]["tool_choice"]["name"], "compare_programs")
        payload = json.loads(responses.requests[1]["input"][0]["output"])
        self.assertEqual({row["program_id"] for row in payload["programs"]},
                         {"8875BSN", "M600MSC", "8800BTECH"})

    def test_hypothetical_completion_is_not_persisted_and_answers_or_rule(self):
        state = replay(["I'm in Construction Management Bachelor of Technology."])[0]["conversation_state"]
        result = answer_student_question(
            "If I complete CMGT 8810, is CMGT 8800 still required too?",
            [], conversation_state=state, client=CLIENT,
        )
        self.assertEqual(result["conversation_state"]["reported_completed_course_ids"], [])
        self.assertIn("not additionally required", result["answer"])

    def test_withdrawn_completion_changes_state_and_student_answer(self):
        state = replay(["I'm studying Construction Management Bachelor of Technology."])[0]["conversation_state"]
        first = answer_student_question(
            "I completed CMGT 8800. Which of the final-project alternatives remains?",
            [], conversation_state=state, client=CLIENT,
        )
        self.assertIn("CMGT8800", first["conversation_state"]["reported_completed_course_ids"])
        corrected = answer_student_question(
            "Sorry, I only planned to take it; I haven't completed CMGT 8800.",
            [], conversation_state=first["conversation_state"], client=CLIENT,
        )
        self.assertEqual(corrected["conversation_state"]["reported_completed_course_ids"], [])
        self.assertIn("removed", corrected["answer"].lower())
        self.assertNotIn("saved **CMGT 8800** as", corrected["answer"])

    def test_certified_international_four_state_mapping(self):
        expected = {
            "0816CM": "ACCEPTED_AVAILABLE",
            "5430ACERT": "NOT_ACCEPTED",
            "5430CERT": "NOT_ACCEPTED",
            "2958CERT": "NOT_ACCEPTED",
            "810CBSN": "CONDITIONAL_RESTRICTED",
        }
        self.assertEqual({pid: certified_international_evidence(pid)["status"]
                          for pid in expected}, expected)

    def test_international_comparison_uses_published_restrictions(self):
        result = compare_programs(
            "Do they accept international students?",
            program_ids=["5430ACERT", "5430CERT"],
        )
        self.assertEqual([row["certified_status"] for row in result["programs"]],
                         ["NOT_ACCEPTED", "NOT_ACCEPTED"])
        self.assertTrue(all(not row["human_confirmation_required"]
                            for row in result["programs"]))

    def test_scoped_evidence_keeps_application_noncourse_and_continuation_rules(self):
        admission = _scope_program_details(get_program_details("9940BSC"), "admission")
        scopes = {rule["scope"] for rule in admission["academic_rules"]["rule_sets"]}
        self.assertTrue({"ADMISSION", "APPLICATION", "NON_COURSE"}.issubset(scopes))
        graduation = _scope_program_details(get_program_details("8800BTECH"), "graduation")
        scopes = {rule["scope"] for rule in graduation["academic_rules"]["rule_sets"]}
        self.assertIn("CONTINUATION", scopes)

    def test_evidence_inventory_survives_scoping(self):
        details = _scope_program_details(get_program_details("8800BTECH"), "international")
        self.assertTrue(details["evidence_inventory"]["curriculum_configured"])
        self.assertEqual(details["international_eligibility"]["status"], "ACCEPTED_AVAILABLE")

    def test_finalizer_corrects_false_absence_and_personal_ineligibility(self):
        cmgt = {"program": _scope_program_details(get_program_details("8800BTECH"), "international")}
        corrected = finalize_student_answer(
            "The curriculum is not configured. International details are unknown.",
            "What can you verify for an international applicant?", [cmgt],
        )
        self.assertIn("available to international applicants", corrected)
        self.assertIn("configured curriculum", corrected)
        corrected = finalize_student_answer(
            "The current record does not return a related-course list.",
            "What can you verify?", [cmgt],
        )
        self.assertIn("configured curriculum", corrected)
        corrected = finalize_student_answer(
            "No individual program courses are listed in the record.",
            "What can you verify?", [cmgt],
        )
        self.assertIn("configured curriculum", corrected)
        civil = {"program": _scope_program_details(get_program_details("5430ACERT"), "international")}
        corrected = finalize_student_answer(
            "Based on that, you are ineligible.",
            "Can an international applicant apply?", [civil],
        )
        self.assertIn("program availability restriction", corrected)

    def test_finalizer_preserves_credential_service_and_work_permit_scope(self):
        msc = {"program": _scope_program_details(get_program_details("M600MSC"), "admission")}
        corrected = finalize_student_answer(
            "Affected applicants require an ICES evaluation.",
            "What are the admission requirements?", [msc],
        )
        self.assertRegex(corrected, r"other Canadian.*services")
        neonatal = {"program": _scope_program_details(get_program_details("810CBSN"), "international")}
        corrected = finalize_student_answer(
            "International applicants need program-head approval.",
            "Which details need human confirmation?", [neonatal],
        )
        self.assertIn("outside Canada", corrected)
        corrected = finalize_student_answer(
            "The alternate route requires a different degree and computing knowledge.",
            "What are the admission requirements?", [msc],
        )
        self.assertIn("must submit the completed Pre-entry Assessment form", corrected)

    def test_finalizer_surfaces_noncourse_and_credit_pool_requirements(self):
        bio_admission = {"program": _scope_program_details(
            get_program_details("9940BSC"), "admission"
        )}
        corrected = finalize_student_answer(
            "Admission has two academic pathways.",
            "What are the admission requirements?", [bio_admission],
        )
        self.assertIn("criminal record check", corrected.lower())
        bio_graduation = {"program": _scope_program_details(
            get_program_details("9940BSC"), "graduation"
        )}
        corrected = finalize_student_answer(
            "Graduation requires the published courses.",
            "What are the graduation requirements?", [bio_graduation],
        )
        self.assertRegex(corrected, r"(?i)six credits.*FSCT")
        self.assertRegex(corrected, r"(?i)exactly 2 courses")


if __name__ == "__main__":
    unittest.main()
