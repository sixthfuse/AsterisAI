"""Permanent sequence and architecture regressions for the failed acceptance run."""
from __future__ import annotations

import json
from pathlib import Path
import time
import unittest

from advisor_v2 import AdvisorV2Repository, AdvisorV2State, answer_advisor_v2_hybrid
from advisor_v2_sol import AdvisorV2Interpretation


class AdvisorV2AcceptanceArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(
            Path(__file__).with_name("advisor_v2_failed_acceptance.json").read_text(encoding="utf-8")
        )["turns"]

    def test_every_failed_acceptance_turn_as_one_sequence(self):
        state = AdvisorV2State()
        for index, case in enumerate(self.corpus, 1):
            result = answer_advisor_v2_hybrid(case["message"], conversation_state=state, language_layer=None)
            state = AdvisorV2State.model_validate(result["conversation_state"])
            with self.subTest(turn=index, message=case["message"]):
                trace = result["observability"]
                self.assertEqual(trace["detected_intent"], case["intent"])
                self.assertEqual(trace["final_response_path"], case["path"])
                self.assertIn(case["contains"], result["answer"])
                if "evaluation" in case:
                    self.assertEqual(trace["rule_evaluation_status"], case["evaluation"])

    def test_specific_eligibility_is_not_hijacked_by_red_seal_or_programs(self):
        question = (
            "I have an electrician Red Seal and a Construction Operations certificate; "
            "do I meet the requirements for the Construction Management bachelor program?"
        )
        result = answer_advisor_v2_hybrid(question, language_layer=None)
        self.assertEqual(result["observability"]["detected_intent"], "admission_eligibility")
        self.assertEqual(result["observability"]["final_response_path"], "deterministic_rule_evaluation")
        self.assertIn("evaluate_admission", [row["capability"] for row in result["retrieval"]])
        self.assertNotIn("find_red_seal_programs", [row["capability"] for row in result["retrieval"]])

    def test_explicit_spanish_engineering_switch_overrides_program_memory(self):
        first = answer_advisor_v2_hybrid("Tell me about Construction Management", language_layer=None)
        switched = answer_advisor_v2_hybrid(
            "tienen programas de ingenieria?",
            conversation_state=first["conversation_state"], language_layer=None,
        )
        self.assertEqual(switched["observability"]["context"]["action"], "reset")
        self.assertEqual(switched["observability"]["final_response_path"], "taxonomy_program_discovery")
        self.assertIn("51 active programs", switched["answer"])

    def test_multilingual_sol_plan_needs_no_language_pack_or_model_fact_authority(self):
        plan = AdvisorV2Interpretation(
            intent="program_discovery", question_class="program_discovery",
            subject_area="ingeniería", program_reference=None, course_reference=None,
            reference_behavior="explicit_new_subject", ordinal_candidate=None,
            clarification_needed=False, clarification_reason=None,
            scope="program_area", requested_facts=["program_list"],
        )
        result = answer_advisor_v2_hybrid(
            "tienen programas de ingenieria?", language_layer=None,
        )
        direct = __import__("advisor_v2").answer_advisor_v2(
            "tienen programas de ingenieria?", interpretation=plan,
        )
        self.assertEqual(result["answer"], direct["answer"])
        self.assertTrue(all(item.startswith(("area:", "program:"))
                            for item in direct["verification"]["evidence_ids"]))

    def test_taxonomy_retrieval_is_bounded_and_traced(self):
        started = time.perf_counter()
        result = AdvisorV2Repository().list_programs_by_area("Computing & IT", limit=500)
        elapsed = time.perf_counter() - started
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["data"]["total"], 44)
        self.assertLessEqual(len(result["data"]["programs"]), 100)
        self.assertIn("query_count=1", result["detail"])
        self.assertIn("rows_returned=44", result["detail"])
        self.assertLess(elapsed, 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
