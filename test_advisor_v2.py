"""Focused, zero-model regression corpus for the advisor-v2 proof of concept."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from advisor_v2 import (
    AdvisorV2Repository, StudentProfileV2, _evaluate_rule_set, _result,
    answer_advisor_v2,
)
from main import PUBLIC_PRODUCTION_PATHS, app


PROGRAMS = {
    "8350BTECH": {"program_id": "8350BTECH", "program_name": "Technology Management",
                  "credential": "Bachelor of Technology", "study_mode": "Part-time",
                  "campus": "Burnaby", "delivery_method": "Blended", "source_url": "https://example/8350"},
    "M600MSC": {"program_id": "M600MSC", "program_name": "Applied Computing",
                "credential": "Master of Science / Master's Degree", "study_mode": "Full-time",
                "campus": "Burnaby", "delivery_method": "In-person", "source_url": "https://example/m600"},
    "5500DIPMA": {"program_id": "5500DIPMA", "program_name": "Computer Systems Technology",
                  "credential": "Diploma", "study_mode": "Full-time", "campus": "Burnaby",
                  "delivery_method": "In-person", "source_url": "https://example/5500"},
    "5430ACERT": {"program_id": "5430ACERT", "program_name": "Civil Technology",
                  "credential": "Associate Certificate", "study_mode": "Part-time", "campus": "Burnaby",
                  "delivery_method": "Blended", "source_url": "https://example/5430a"},
    "5430CERT": {"program_id": "5430CERT", "program_name": "Civil Technology",
                 "credential": "Certificate", "study_mode": "Part-time", "campus": "Burnaby",
                 "delivery_method": "Blended", "source_url": "https://example/5430c"},
}


class FixtureRepository(AdvisorV2Repository):
    def search_programs(self, query, limit=12):
        if query == "database failure":
            return _result("data_unavailable", "search_programs", detail="fixture_failure")
        if "comput" in query.lower():
            items = [PROGRAMS["M600MSC"], PROGRAMS["5500DIPMA"]]
        elif "civil technology" in query.lower():
            items = [PROGRAMS["5430ACERT"], PROGRAMS["5430CERT"]]
        else:
            items = list(PROGRAMS.values())
        return _result("found", "search_programs", data={"query": query, "programs": items[:limit]},
                       evidence_ids=[f"program:{item['program_id']}" for item in items[:limit]])

    def resolve_program(self, query):
        normalized = query.lower()
        if normalized == "database failure":
            return _result("data_unavailable", "resolve_program", detail="fixture_failure")
        if "lunar gardening" in normalized:
            return _result("not_found", "resolve_program", data={"query": query})
        return super().resolve_program(query)

    def get_program_facts(self, program_id):
        item = PROGRAMS.get(program_id)
        if not item:
            return _result("not_found", "get_program_facts", data={"program_id": program_id})
        return _result("found", "get_program_facts", data={**item, "program_overview": "Fixture overview."},
                       evidence_ids=[f"program:{program_id}"])

    def get_course_facts(self, query):
        if query != "COMP1511":
            return _result("not_found", "get_course_facts", data={"query": query})
        data = {"course_id": "COMP1511", "display_course_code": "COMP 1511",
                "course_name": "Programming Methods", "credits": 4, "course_overview": "Fixture course."}
        return _result("found", "get_course_facts", data=data, evidence_ids=["course:COMP1511"])

    def get_admission_rules(self, program_id):
        packet = {"program_id": program_id, "rule_sets": [{
            "rule_set_id": 10, "name": "Fixture admission", "groups": [{
                "rule_group_id": 20, "operator": "AND", "label": "Admission", "children": [],
                "conditions": [
                    {"condition_id": 30, "condition_type": "GPA", "minimum_value": 70,
                     "subject_id": None, "parameters": {"executable": True}, "description": "Minimum 70% GPA."},
                    {"condition_id": 31, "condition_type": "WORK_EXPERIENCE", "minimum_value": 2,
                     "subject_id": None, "parameters": {"executable": True}, "description": "Two years of experience."},
                ],
            }],
        }]}
        return _result("found", "get_admission_rules", data=packet, evidence_ids=["rule_set:10"])


class AdvisorV2RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(Path(__file__).with_name("advisor_v2_regression_corpus.json").read_text())
        cls.torture = json.loads(Path(__file__).with_name("advisor_v2_torture_corpus.json").read_text())
        cls.repo = FixtureRepository()

    def test_regression_corpus(self):
        results = {}
        for case in self.corpus:
            prior = results.get(case.get("prior_case"), {}).get("conversation_state")
            profile = {"gpa": 75} if case["id"] == "partial_eligibility" else None
            result = answer_advisor_v2(case["question"], conversation_state=prior,
                                       student_profile=profile, repository=self.repo)
            results[case["id"]] = result
            with self.subTest(case=case["id"]):
                if "expected_kind" in case:
                    self.assertEqual(result["conversation_state"]["active_kind"], case["expected_kind"])
                if "expected_program_id" in case:
                    self.assertEqual(result["resolved_program"], case["expected_program_id"])
                if "expected_course_id" in case:
                    self.assertEqual(result["conversation_state"]["course_id"], case["expected_course_id"])
                if "expected_retrieval_status" in case:
                    self.assertEqual(result["retrieval"][0]["status"], case["expected_retrieval_status"])
                if "expected_evaluation_status" in case:
                    evaluated = next(item for item in result["retrieval"] if item["capability"] == "evaluate_admission")
                    self.assertEqual(evaluated["data"]["status"], case["expected_evaluation_status"])

    def test_topic_switch_does_not_reuse_old_program(self):
        first = answer_advisor_v2("Tell me about Technology Management", repository=self.repo)
        switched = answer_advisor_v2("What computing programs are there?",
                                     conversation_state=first["conversation_state"], repository=self.repo)
        self.assertEqual(switched["conversation_state"]["active_kind"], "discovery")
        self.assertIsNone(switched["conversation_state"]["program_id"])
        self.assertNotIn("8350BTECH", switched["conversation_state"]["candidate_program_ids"])

    def test_follow_up_uses_one_resolved_program(self):
        first = answer_advisor_v2("Tell me about Technology Management", repository=self.repo)
        later = answer_advisor_v2("Tell me more", conversation_state=first["conversation_state"], repository=self.repo)
        self.assertEqual(later["resolved_program"], "8350BTECH")

    def test_retrieval_failure_is_not_rendered_as_absence(self):
        result = answer_advisor_v2("Tell me about database failure", repository=self.repo)
        self.assertIn("unavailable", result["answer"])
        self.assertIn("not evidence", result["answer"])
        self.assertEqual(result["verification"]["status"], "data_unavailable")

    def test_structured_rule_evaluation_marks_known_failure(self):
        profile = StudentProfileV2(gpa=65, work_experience_years=4, credentials=["diploma"])
        result = answer_advisor_v2("Am I eligible for Technology Management?",
                                   student_profile=profile, repository=self.repo)
        evaluation = next(item for item in result["retrieval"] if item["capability"] == "evaluate_admission")
        self.assertEqual(evaluation["data"]["status"], "unmet")

    def test_rule_tree_preserves_or_routes(self):
        condition = lambda identifier, kind, minimum=None: {
            "condition_id": identifier, "condition_type": kind, "minimum_value": minimum,
            "subject_id": None, "parameters": {"executable": True}, "description": kind,
        }
        rule = {"rule_set_id": 1, "name": "Alternative entry", "groups": [{
            "rule_group_id": 2, "operator": "OR", "label": "Choose a route", "conditions": [],
            "children": [
                {"rule_group_id": 3, "operator": "AND", "label": "Experienced route", "children": [],
                 "conditions": [condition(4, "WORK_EXPERIENCE", 2)]},
                {"rule_group_id": 5, "operator": "AND", "label": "Academic route", "children": [],
                 "conditions": [condition(6, "GPA", 80)]},
            ],
        }]}
        evaluated = _evaluate_rule_set(rule, StudentProfileV2(work_experience_years=3))
        self.assertEqual(evaluated["status"], "met")

    def test_api_contract_is_separate(self):
        fixture = answer_advisor_v2("Tell me about Technology Management", repository=self.repo)
        with patch("main.answer_advisor_v2", return_value=fixture) as called:
            response = TestClient(app).post("/advisor-v2", json={"question": "Tell me about Technology Management"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["resolved_program"], "8350BTECH")
        called.assert_called_once()

    def test_fuzzy_guardrails_and_candidate_diagnostics(self):
        broad = answer_advisor_v2("technology", repository=self.repo)
        self.assertEqual(broad["conversation_state"]["active_kind"], "discovery")
        self.assertEqual(broad["observability"]["entity_resolution"]["status"], "discovery_set")
        misspelled = answer_advisor_v2("Tell me about Technlogy Managment", repository=self.repo)
        self.assertEqual(misspelled["resolved_program"], "8350BTECH")
        candidates = misspelled["observability"]["entity_resolution"]["candidates"]
        self.assertGreater(candidates[0]["fuzzy_ratio"], .8)
        self.assertGreater(candidates[0]["score"], candidates[1]["score"])

    def test_server_session_state_and_explicit_reset(self):
        client = TestClient(app)
        headers = {"X-Session-ID": "advisor-v2-session-test"}
        def fixture_answer(question, **kwargs):
            return answer_advisor_v2(question, repository=self.repo, **kwargs)
        with patch("main.answer_advisor_v2", side_effect=fixture_answer):
            first = client.post("/advisor-v2", json={"question": "Tell me about Technology Management"}, headers=headers)
            follow = client.post("/advisor-v2", json={"question": "What are its admission requirements?"}, headers=headers)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(follow.json()["resolved_program"], "8350BTECH")
            self.assertEqual(follow.json()["observability"]["state_source"], "server_session")
            reset = client.post("/advisor-v2", json={"question": "Tell me more", "reset_conversation": True}, headers=headers)
            self.assertEqual(reset.json()["observability"]["entity_resolution"]["status"], "missing_context")

    def test_experimental_ui_is_separate(self):
        client = TestClient(app)
        page = client.get("/app-v2")
        script = client.get("/static/advisor-v2.js")
        self.assertEqual(page.status_code, 200)
        self.assertIn("EXPERIMENT", page.text)
        self.assertIn('fetch("/advisor-v2"', script.text)
        self.assertNotIn('fetch("/advisor"', script.text)
        self.assertNotIn("/app-v2", PUBLIC_PRODUCTION_PATHS)
        self.assertNotIn("/advisor-v2", PUBLIC_PRODUCTION_PATHS)
        self.assertIn("/app", PUBLIC_PRODUCTION_PATHS)
        self.assertIn("/advisor", PUBLIC_PRODUCTION_PATHS)

    def test_28_turn_manual_conversation_torture_corpus(self):
        state = None
        self.assertGreaterEqual(len(self.torture["turns"]), 20)
        self.assertLessEqual(len(self.torture["turns"]), 30)
        for turn in self.torture["turns"]:
            result = answer_advisor_v2(
                turn["question"], conversation_state=state,
                student_profile=turn.get("student_profile"), repository=self.repo,
            )
            state = result["conversation_state"]
            with self.subTest(turn=turn["turn"], question=turn["question"]):
                expected = turn.get("expect", {})
                if "kind" in expected:
                    self.assertEqual(state["active_kind"], expected["kind"])
                if "program_id" in expected:
                    self.assertEqual(result["resolved_program"], expected["program_id"])
                if "retrieval_status" in expected:
                    self.assertEqual(result["retrieval"][0]["status"], expected["retrieval_status"])
                if "context_action" in expected:
                    self.assertEqual(result["observability"]["context"]["action"], expected["context_action"])
                if "response_path" in expected:
                    self.assertEqual(result["observability"]["final_response_path"], expected["response_path"])
                if "evaluation_status" in expected:
                    self.assertEqual(result["observability"]["rule_evaluation_status"], expected["evaluation_status"])
                if expected.get("profile_conflict"):
                    self.assertTrue(result["observability"]["profile"]["conflicting_fields"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
