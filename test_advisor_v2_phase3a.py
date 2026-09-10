"""Mocked Phase 3A language-boundary and 50-question golden checks."""
import json
from pathlib import Path
import unittest

from advisor_v2 import AdvisorV2State, answer_advisor_v2, answer_advisor_v2_hybrid
from advisor_v2_sol import AdvisorV2Interpretation, AdvisorV2SynthesisPlan, SolLanguageLayer
from test_advisor_v2 import FixtureRepository


class MockLanguageLayer:
    def __init__(self, interpretation=None, *, interpretation_error=None,
                 synthesis_error=None, plan=None):
        self.value = interpretation
        self.interpretation_error = interpretation_error
        self.synthesis_error = synthesis_error
        self.plan = plan

    def interpret(self, payload):
        if self.interpretation_error:
            raise self.interpretation_error
        return AdvisorV2Interpretation.model_validate(self.value), {
            "input_tokens": 11, "output_tokens": 7, "cached_tokens": 2,
        }

    def synthesize(self, payload):
        if self.synthesis_error:
            raise self.synthesis_error
        fact_ids = [item["fact_id"] for item in payload["facts"]]
        plan = self.plan or {"opening": "direct", "fact_ids": fact_ids, "closing": "none"}
        return AdvisorV2SynthesisPlan.model_validate(plan), {
            "input_tokens": 9, "output_tokens": 5, "cached_tokens": 0,
        }


def interpretation(**overrides):
    payload = {
        "intent": "program_facts", "question_class": "program_facts",
        "program_reference": None, "subject_area": None, "course_reference": None,
        "student_facts": {}, "reference_behavior": "no_reference",
        "ordinal_candidate": None, "clarification_needed": False,
        "clarification_reason": None,
    }
    payload.update(overrides)
    return payload


class AdvisorV2Phase3ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = FixtureRepository()
        cls.golden = json.loads(
            Path(__file__).with_name("advisor_v2_phase3a_golden.json").read_text(encoding="utf-8")
        )

    def test_50_question_golden_schema_and_coverage(self):
        self.assertGreaterEqual(len(self.golden), 40)
        self.assertLessEqual(len(self.golden), 60)
        categories = {case["category"] for case in self.golden}
        required = {
            "messy_language", "discovery", "exact_lookup", "misspelling", "follow_up",
            "ordinal_follow_up", "diploma_follow_up", "abrupt_switch", "partial_facts",
            "conflicting_facts", "international", "course", "misinformation", "exceptions",
            "ambiguity", "unknown", "retrieval_failure", "model_failure", "clarification",
        }
        self.assertTrue(required <= categories)
        for case in self.golden:
            with self.subTest(case=case["id"]):
                value = interpretation(
                    intent=case["intent"], question_class=case["question_class"],
                    program_reference=case.get("program_reference"),
                    subject_area=case.get("subject_area"),
                    course_reference=case.get("course_reference"),
                    student_facts=case.get("student_facts", {}),
                    reference_behavior=case["reference_behavior"],
                    ordinal_candidate=case.get("ordinal_candidate"),
                    clarification_needed=case.get("clarification_needed", False),
                )
                parsed = AdvisorV2Interpretation.model_validate(value)
                self.assertEqual(parsed.intent, case["intent"])

    def test_openai_boundary_pins_sol_medium_strict_parse_and_no_storage(self):
        calls = []

        class Response:
            usage = None
            output_parsed = AdvisorV2Interpretation.model_validate(interpretation())

        class Responses:
            def parse(self, **kwargs):
                calls.append(kwargs)
                return Response()

        class Client:
            responses = Responses()

        layer = SolLanguageLayer(client=Client())
        parsed, _ = layer.interpret({"message": "hello", "prior": {}})
        self.assertEqual(parsed.intent, "program_facts")
        self.assertEqual(calls[0]["model"], "gpt-5.6-sol")
        self.assertEqual(calls[0]["reasoning"], {"effort": "medium"})
        self.assertIs(calls[0]["text_format"], AdvisorV2Interpretation)
        self.assertFalse(calls[0]["store"])

    def test_model_program_proposal_requires_repository_confirmation(self):
        layer = MockLanguageLayer(interpretation(
            program_reference="Technology Management",
            reference_behavior="explicit_new_subject",
        ))
        result = answer_advisor_v2_hybrid("tech mgmt pls", repository=self.repo, language_layer=layer)
        self.assertEqual(result["resolved_program"], "8350BTECH")
        trace = result["observability"]["entity_proposal_confirmation"]
        self.assertEqual(trace["proposals"]["program_reference"], "Technology Management")
        self.assertEqual(trace["confirmation"]["status"], "found")
        self.assertEqual(trace["authority"], "deterministic_repository")

    def test_unknown_model_proposal_stays_not_found(self):
        layer = MockLanguageLayer(interpretation(
            program_reference="Lunar Gardening", reference_behavior="explicit_new_subject",
        ))
        result = answer_advisor_v2_hybrid("the moon plants degree", repository=self.repo, language_layer=layer)
        self.assertEqual(result["retrieval"][0]["status"], "not_found")
        self.assertEqual(result["observability"]["entity_resolution"]["status"], "not_found")

    def test_ordinal_candidate_is_confirmed_by_facts_lookup(self):
        state = AdvisorV2State(active_kind="discovery", discovery_query="computing",
                               candidate_program_ids=["M600MSC", "5500DIPMA"], turn_index=1)
        layer = MockLanguageLayer(interpretation(
            reference_behavior="ordinal_candidate", ordinal_candidate=2,
        ))
        result = answer_advisor_v2_hybrid("the second one", conversation_state=state,
                                          repository=self.repo, language_layer=layer)
        self.assertEqual(result["resolved_program"], "5500DIPMA")
        self.assertEqual(result["retrieval"][0]["capability"], "get_program_facts")
        self.assertEqual(result["observability"]["entity_resolution"]["status"],
                         "ordinal_candidate_confirmed")
        self.assertEqual(result["observability"]["context"]["action"], "resolved_ordinal")

    def test_explicit_new_subject_overrides_old_context(self):
        old = answer_advisor_v2("Technology Management", repository=self.repo)
        layer = MockLanguageLayer(interpretation(
            program_reference="Applied Computing", reference_behavior="explicit_new_subject",
        ))
        result = answer_advisor_v2_hybrid("actually the applied computing one",
                                          conversation_state=old["conversation_state"],
                                          repository=self.repo, language_layer=layer)
        self.assertEqual(result["resolved_program"], "M600MSC")
        self.assertEqual(result["observability"]["context"]["action"], "reset")

    def test_extracted_facts_feed_only_deterministic_evaluator(self):
        state = AdvisorV2State(active_kind="program", program_id="8350BTECH",
                               last_question_class="admission_eligibility", turn_index=1)
        layer = MockLanguageLayer(interpretation(
            intent="admission_eligibility", question_class="admission_eligibility",
            reference_behavior="follow_up_program",
            student_facts={"gpa": 75, "credentials": ["diploma"], "work_experience_years": 3},
        ))
        result = answer_advisor_v2_hybrid("yeah I meet those", conversation_state=state,
                                          repository=self.repo, language_layer=layer)
        self.assertEqual(result["observability"]["rule_evaluation_status"], "met")
        evaluated = next(item for item in result["retrieval"] if item["capability"] == "evaluate_admission")
        self.assertEqual(evaluated["data"]["status"], "met")

    def test_conflicting_model_extraction_is_visible(self):
        state = AdvisorV2State(active_kind="program", program_id="8350BTECH", turn_index=1,
                               last_question_class="admission_eligibility",
                               student_profile={"gpa": 75, "credentials": ["diploma"]})
        layer = MockLanguageLayer(interpretation(
            intent="admission_eligibility", question_class="admission_eligibility",
            reference_behavior="follow_up_program", student_facts={"gpa": 68},
        ))
        result = answer_advisor_v2_hybrid("correction, sixty eight", conversation_state=state,
                                          repository=self.repo, language_layer=layer)
        self.assertIn("gpa", result["observability"]["profile"]["conflicting_fields"])
        self.assertEqual(result["conversation_state"]["student_profile"]["gpa"], 68)

    def test_international_status_is_explicit_user_fact_not_bcit_fact(self):
        layer = MockLanguageLayer(interpretation(
            program_reference="Technology Management", reference_behavior="explicit_new_subject",
            student_facts={"international_status": "international"},
        ))
        result = answer_advisor_v2_hybrid("international student, tech management",
                                          repository=self.repo, language_layer=layer)
        self.assertEqual(result["conversation_state"]["student_profile"]["international_status"],
                         "international")
        self.assertNotIn("international", result["answer"].lower())

    def test_course_proposal_is_confirmed(self):
        layer = MockLanguageLayer(interpretation(
            intent="course_facts", question_class="course_facts", course_reference="COMP1511",
            reference_behavior="explicit_new_subject",
        ))
        result = answer_advisor_v2_hybrid("programming methods class", repository=self.repo,
                                          language_layer=layer)
        self.assertEqual(result["conversation_state"]["course_id"], "COMP1511")
        self.assertEqual(result["observability"]["entity_resolution"]["status"], "found")

    def test_interpretation_timeout_returns_exact_phase2_answer(self):
        baseline = answer_advisor_v2("Tell me about Technology Management", repository=self.repo)
        layer = MockLanguageLayer(interpretation_error=TimeoutError("fixture"))
        result = answer_advisor_v2_hybrid("Tell me about Technology Management",
                                          repository=self.repo, language_layer=layer)
        self.assertEqual(result["answer"], baseline["answer"])
        self.assertEqual(result["observability"]["interpretation"]["status"], "fallback")
        self.assertEqual(result["observability"]["synthesis"]["status"],
                         "skipped_interpretation_fallback")

    def test_synthesis_failure_returns_exact_deterministic_answer(self):
        baseline = answer_advisor_v2("Tell me about Technology Management", repository=self.repo)
        layer = MockLanguageLayer(interpretation(
            program_reference="Technology Management", reference_behavior="explicit_new_subject",
        ), synthesis_error=ValueError("bad schema"))
        result = answer_advisor_v2_hybrid("Tell me about Technology Management",
                                          repository=self.repo, language_layer=layer)
        self.assertEqual(result["answer"], baseline["answer"])
        self.assertEqual(result["observability"]["synthesis"]["status"], "fallback")
        self.assertEqual(result["observability"]["final_response_source"], "deterministic_phase2")

    def test_synthesis_cannot_drop_or_invent_fact_lines(self):
        layer = MockLanguageLayer(interpretation(
            program_reference="Technology Management", reference_behavior="explicit_new_subject",
        ), plan={"opening": "supportive", "fact_ids": [], "closing": "none"})
        baseline = answer_advisor_v2("Tell me about Technology Management", repository=self.repo)
        result = answer_advisor_v2_hybrid("Tell me about Technology Management",
                                          repository=self.repo, language_layer=layer)
        self.assertEqual(result["answer"], baseline["answer"])
        self.assertEqual(result["observability"]["synthesis"]["error_class"], "ValueError")

    def test_successful_synthesis_preserves_exact_grounded_line_and_usage(self):
        layer = MockLanguageLayer(interpretation(
            program_reference="Technology Management", reference_behavior="explicit_new_subject",
        ))
        result = answer_advisor_v2_hybrid("tech management", repository=self.repo, language_layer=layer)
        self.assertIn("Technology Management (Bachelor of Technology", result["answer"])
        self.assertEqual(result["observability"]["final_response_source"], "sol_constrained_renderer")
        self.assertEqual(result["usage"]["model"], "gpt-5.6-sol")
        self.assertEqual(result["usage"]["input_tokens"], 20)
        self.assertNotIn("reasoning", json.dumps(result["observability"]).lower())
        inputs = result["observability"]["synthesis"]["inputs"]
        self.assertEqual(inputs["allowed_openings"], ["none", "direct", "supportive"])
        self.assertEqual(inputs["allowed_closings"], ["none", "invite_follow_up"])

    def test_synthesis_choices_match_deterministic_status_boundaries(self):
        layer = MockLanguageLayer(interpretation(
            program_reference="Technology Management", intent="institutional_decision",
            question_class="admission_decision", reference_behavior="explicit_new_subject",
        ), plan={"opening": "direct", "fact_ids": ["F1"], "closing": "confirm_with_bcit"})
        decision = answer_advisor_v2_hybrid(
            "Will BCIT accept me into Technology Management?",
            repository=self.repo, language_layer=layer,
        )
        allowed = decision["observability"]["synthesis"]["inputs"]["allowed_closings"]
        self.assertIn("confirm_with_bcit", allowed)

        discovery_layer = MockLanguageLayer(interpretation(
            intent="program_discovery", question_class="program_discovery",
            subject_area="computing", reference_behavior="explicit_new_subject",
        ))
        discovery = answer_advisor_v2_hybrid(
            "What computing programs are there?", repository=self.repo,
            language_layer=discovery_layer,
        )
        discovery_allowed = discovery["observability"]["synthesis"]["inputs"]["allowed_closings"]
        self.assertEqual(discovery_allowed, ["none", "invite_follow_up"])

    def test_retrieval_failure_status_survives_synthesis(self):
        layer = MockLanguageLayer(interpretation(
            program_reference="database failure", reference_behavior="explicit_new_subject",
        ))
        result = answer_advisor_v2_hybrid("broken db", repository=self.repo, language_layer=layer)
        self.assertEqual(result["verification"]["status"], "data_unavailable")
        self.assertEqual(result["retrieval"][0]["status"], "data_unavailable")
        self.assertIn("not evidence", result["answer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
