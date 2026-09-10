import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ai_advisor import (
    answer_student_question, compare_programs, enforce_academic_scope_boundaries,
    enforce_response_word_limit, execute_tool,
    resolve_academic_context,
)
from response_policy import conversation_quality_instructions, response_policy


class RecordingResponses:
    def __init__(self):
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(id="response-1", output=[], output_text="A concise verified answer.")


class RecordingClient:
    def __init__(self):
        self.responses = RecordingResponses()


class ResponseDepthPolicyTests(unittest.TestCase):
    def test_concise_condition_answer_is_deterministically_bounded(self):
        answer = '\n'.join(f'- Requirement {index} has enough explanatory words to be useful.'
                           for index in range(30))
        limited = enforce_response_word_limit(answer, 'What are the admission requirements?')
        self.assertLessEqual(len(re.findall(r'[a-z0-9]+', limited.casefold())), 180)
        self.assertTrue(limited.startswith('- Requirement 0'))

    def test_simple_fact_is_short(self):
        policy = response_policy("What credential does it lead to?")
        self.assertEqual(policy.depth, "short")
        self.assertIn("first sentence", policy.instruction)

    def test_direct_eligibility_is_concise_with_conditions(self):
        policy = response_policy("Am I eligible for admission?")
        self.assertEqual(policy.depth, "concise_conditions")
        self.assertIn("decisive verified conditions", policy.instruction)
        self.assertEqual(
            response_policy("What should I know before applying?").depth,
            "concise_conditions",
        )

    def test_more_information_expands_without_repeating_card(self):
        policy = response_policy("Tell me more about this program")
        self.assertEqual(policy.depth, "expanded")
        self.assertIn("Do not repeat", policy.instruction)

    def test_comprehensive_request_keeps_detail(self):
        policy = response_policy("Give me a comprehensive curriculum breakdown")
        self.assertEqual(policy.depth, "comprehensive")

    def test_comparison_is_synthesized(self):
        policy = response_policy("Compare these two programs")
        self.assertEqual(policy.depth, "comparison")
        self.assertIn("Do not write separate program profiles", policy.instruction)

    def test_quality_policy_covers_repetition_uncertainty_and_frustration(self):
        instructions = conversation_quality_instructions(response_policy("Can I apply?"))
        self.assertIn("immediately preceding assistant turn", instructions)
        self.assertIn("missing or unpublished information", instructions)
        self.assertIn("frustration plus a substantive question", instructions)
        self.assertIn("never dump", instructions)

    def test_later_progression_does_not_condition_earlier_credential(self):
        answer = (
            "Successful completion of the first two years leads to a Civil Engineering "
            "Diploma, subject to the program's continuation requirements."
        )
        evidence = [{
            "academic_scope_boundaries": {
                "credential_award_evidence": [
                    "Students receive a diploma upon successful completion of the first two years."
                ],
                "later_level_progression_requirements": [{"from_level": 4, "to_level": 5}],
            }
        }]
        result = enforce_academic_scope_boundaries(answer, evidence)
        self.assertIn("Civil Engineering Diploma", result)
        self.assertNotIn("subject to", result.lower())

    def test_boundary_filter_does_nothing_without_authoritative_separation(self):
        answer = "The credential is subject to the stated continuation requirements."
        self.assertEqual(enforce_academic_scope_boundaries(answer, [{}]), answer)

    @patch("ai_advisor.get_program_level_courses", return_value=[])
    def test_level_course_tool_accepts_selected_program_with_null_pathway(self, level_courses):
        result = execute_tool(
            "get_program_level_courses",
            {"level": 1},
            {"program_id": "0816CM", "pathway": None},
        )
        self.assertEqual(result, {"pathway": None, "level": 1, "courses": []})
        level_courses.assert_called_once_with("0816CM", 1)

    @patch("ai_advisor.get_program_rules", return_value={"rule_sets": []})
    @patch("ai_advisor.get_connection")
    @patch("ai_advisor.get_program_details")
    def test_comparison_ids_load_exact_programs(self, details, connection, rules):
        records = {
            "M500MENG": {"program_id": "M500MENG", "program_name": "Smart Grid Systems and Technologies",
                           "credential": "Master of Engineering", "study_mode": "Full-time",
                           "campus": "Burnaby", "delivery_method": "In person", "source_url": "https://one"},
            "M600MSC": {"program_id": "M600MSC", "program_name": "Applied Computing",
                         "credential": "Master of Science", "study_mode": "Full-time",
                         "campus": "Burnaby", "delivery_method": "In person", "source_url": "https://two"},
        }
        details.side_effect = records.get
        result = compare_programs(
            "Compare these programs", program_ids=["M500MENG", "M600MSC"]
        )
        self.assertEqual(result["program_count"], 2)
        self.assertEqual({item["program_id"] for item in result["programs"]}, set(records))
        self.assertTrue(all(item["classification"] == "verified program record" for item in result["programs"]))

    def test_applicant_background_does_not_hide_named_program(self):
        state = resolve_academic_context(
            "Can I apply to Applied Computing MSc with an international bachelor's degree?",
            [], None,
        )["conversation_state"]
        self.assertEqual(state["program_id"], "M600MSC")

    def test_prerequisite_course_keeps_active_program(self):
        first = resolve_academic_context(
            "What are the admissions requirements for Construction Management BTech?",
            [], None,
        )
        follow = resolve_academic_context(
            "And what is needed specifically before CMGT 8700?",
            [], None, first["conversation_state"],
        )["conversation_state"]
        self.assertEqual(follow["scope"], "program")
        self.assertEqual(follow["program_id"], "8800BTECH")
        self.assertEqual(follow["course_id"], "CMGT8700")

    def test_referential_comparison_followup_keeps_comparison_set(self):
        first = resolve_academic_context(
            "Compare the Construction Management diploma and Bachelor of Technology.",
            [], None,
        )
        follow = resolve_academic_context(
            "Is the other one also a degree?", [], None, first["conversation_state"]
        )["conversation_state"]
        self.assertEqual(follow["scope"], "program_family")
        self.assertEqual(set(follow["comparison_program_ids"]), {"7710DIPMA", "8800BTECH"})

    @patch("ai_advisor.get_connection")
    def test_generation_request_carries_depth_and_scope_boundaries(self, connection):
        cursor = connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            ("5410DIPLT", "Civil Engineering Diploma", "Diploma"),
        ]
        client = RecordingClient()
        answer_student_question(
            "How long is the Civil Engineering Diploma?",
            [],
            client=client,
        )
        request = client.responses.requests[0]
        self.assertIn("Required response depth: short", request["input"])
        self.assertIn("academic_scope_boundaries", request["instructions"])
        self.assertIn("not a condition for an earlier credential", request["instructions"])


if __name__ == "__main__":
    unittest.main()
