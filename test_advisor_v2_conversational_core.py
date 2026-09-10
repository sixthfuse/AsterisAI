"""Reusable operation/state/answer-shape regressions for advisor v2."""
from __future__ import annotations

import unittest

from advisor_v2 import AdvisorV2State, answer_advisor_v2_hybrid


def turn(message: str, state=None):
    return answer_advisor_v2_hybrid(message, conversation_state=state, language_layer=None)


class AdvisorV2ConversationalCoreTests(unittest.TestCase):
    def test_selects_single_unavailable_item_from_prior_results_variants(self):
        for question in (
            "which one is the program that I cannot apply to as an international student?",
            "No, which one of those is unavailable to an international applicant?",
        ):
            with self.subTest(question=question):
                first = turn("As an international student, which nursing programs can I apply to?")
                result = turn(question, first["conversation_state"])
                self.assertEqual(result["observability"]["task_plan"]["operation"], "select")
                self.assertEqual(result["observability"]["referent_resolution"]["source"], "prior_result_filter")
                self.assertEqual(result["resolved_program"], "8875BSN")
                self.assertEqual(result["verification"]["status"], "grounded")
                self.assertIn("reuse_prior_result", [row["capability"] for row in result["retrieval"]])
                self.assertEqual(result["answer"].count("Nursing, Bachelor"), 1)
                self.assertNotIn("Critical Care Nursing", result["answer"])

    def test_this_program_after_code_uses_active_id_not_literal_search(self):
        for follow_up in (
            "Can I apply to this program as an international student?",
            "Is that program available to international applicants?",
        ):
            with self.subTest(follow_up=follow_up):
                first = turn("8875bsn")
                result = turn(follow_up, first["conversation_state"])
                trace = result["observability"]
                self.assertEqual(trace["referent_resolution"]["source"], "active_program_id")
                self.assertEqual(trace["final_response_path"], "single_program_international_availability")
                self.assertIn("not available", result["answer"].lower())
                self.assertNotIn("resolve_program", [row["capability"] for row in result["retrieval"]])

    def test_unique_masters_degree_resolves_from_recent_computing_results(self):
        for follow_up in ("more about the master's degree", "tell me about the master degree"):
            with self.subTest(follow_up=follow_up):
                first = turn("Do you offer computing programs?")
                result = turn(follow_up, first["conversation_state"])
                self.assertEqual(result["resolved_program"], "M600MSC")
                self.assertEqual(result["observability"]["referent_resolution"]["source"], "prior_result_credential")
                self.assertIn("Applied Computing", result["answer"])

    def test_exact_pasted_prior_name_outranks_similar_global_names(self):
        first = turn("Do you offer computing programs?")
        for exact_name in (
            "Applied Computing — Master of Science / Master's Degree",
            "No, I mean exactly Applied Computing",
        ):
            with self.subTest(exact_name=exact_name):
                result = turn(exact_name, first["conversation_state"])
                self.assertEqual(result["resolved_program"], "M600MSC")
                self.assertEqual(result["observability"]["referent_resolution"]["source"], "prior_result_exact")

    def test_follow_up_phrase_is_never_global_program_search(self):
        first = turn("8875bsn")
        result = turn("follow up", first["conversation_state"])
        self.assertNotEqual(result["observability"]["final_response_path"], "program_resolution_failure")
        self.assertNotIn("follow up in the active", result["answer"].lower())

    def test_broad_area_is_grouped_but_explicit_all_is_exhaustive(self):
        for area in ("engineering", "computing"):
            with self.subTest(area=area):
                broad = turn(f"Do you offer any {area} programs?")
                self.assertEqual(broad["observability"]["answer_shape_decision"], "grouped_summary")
                self.assertLessEqual(len(broad["answer"].splitlines()), 9)
                self.assertIn("credential groups", broad["answer"])
                exhaustive = turn(f"List all {area} programs")
                self.assertEqual(exhaustive["observability"]["answer_shape_decision"], "exhaustive_list")
                self.assertGreater(len(exhaustive["answer"].splitlines()), 20)

    def test_international_availability_has_question_shaped_summary_without_urls(self):
        result = turn("As an international student, which nursing programs can I apply to?")
        self.assertEqual(result["observability"]["answer_shape_decision"], "shortlist")
        self.assertLessEqual(len(result["answer"].splitlines()), 4)
        self.assertNotIn("http", result["answer"])
        self.assertIn("15", result["answer"])
        self.assertIn("Unavailable:", result["answer"])

    def test_eligibility_is_deterministic_concise_and_traced(self):
        question = (
            "I have English 12 with 73 percent, an electrician Red Seal, Foundations of Math 11 "
            "with 55 percent, the Construction Operations associate certificate with 70 percent, "
            "and 11 months of work experience. Do I meet the requirements for the Construction "
            "Management bachelor degree?"
        )
        result = turn(question)
        self.assertEqual(result["observability"]["task_plan"]["operation"], "eligibility")
        self.assertEqual(result["observability"]["rule_evaluation_status"], "unmet")
        self.assertEqual(result["observability"]["final_response_path"], "deterministic_rule_evaluation")
        self.assertLessEqual(len(result["answer"].splitlines()), 10)

    def test_observability_exposes_core_without_chain_of_thought(self):
        result = turn("Do you offer engineering programs?")
        trace = result["observability"]
        for key in (
            "task_plan", "referent_resolution", "selected_evidence_objects",
            "answer_shape_decision", "synthesis", "grounding_validation",
        ):
            self.assertIn(key, trace)
        self.assertNotIn("chain_of_thought", trace)
        self.assertNotIn("reasoning", trace)


if __name__ == "__main__":
    unittest.main(verbosity=2)
