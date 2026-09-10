"""Phase 4 deterministic eligibility tests; no model calls and no database writes."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from advisor_v2 import (
    AdvisorV2Repository, AdvisorV2State, StudentProfileV2, _combine, _condition,
    _evaluate_prerequisite_group, _evaluate_rule_set, _result, answer_advisor_v2,
)
from human_advisor_benchmark.phase3b_finalize import save


def condition(identifier, kind, minimum=None, *, subject=None, unit="PERCENT",
              parameters=None, accepted_values=None):
    return {"condition_id": identifier, "condition_type": kind, "minimum_value": minimum,
            "subject_id": subject, "unit": unit, "parameters": parameters or {},
            "accepted_values": accepted_values, "description": kind}


class FailureRepository(AdvisorV2Repository):
    def __init__(self, rule_status):
        self.rule_status = rule_status

    def get_program_facts(self, program_id):
        return _result("found", "get_program_facts", data={
            "program_id": program_id, "program_name": "Fixture Program", "credential": "Diploma",
            "study_mode": "Full-time", "campus": "Burnaby", "delivery_method": "In-person",
            "program_overview": "Fixture", "source_url": "https://example.test/program",
        }, evidence_ids=[f"program:{program_id}"])

    def resolve_program(self, query):
        return _result("found", "resolve_program", data={"program_id": "FIXTURE"})

    def get_admission_rules(self, program_id):
        if self.rule_status == "failure":
            return _result("data_unavailable", "get_admission_rules", detail="fixture_failure")
        return _result("not_found", "get_admission_rules", data={"program_id": program_id, "rule_sets": []})


class Phase4EligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(Path("advisor_v2_phase4_golden.json").read_text(encoding="utf-8"))

    def test_corpus_has_required_torture_categories(self):
        categories = {item["category"] for item in self.corpus["cases"]}
        self.assertTrue({"nested_and_or", "multi_factor_partial", "multi_turn_correction",
                         "evidence_unavailable", "retrieval_failure", "time_window",
                         "international_credential", "combined_course_average"} <= categories)

    def test_real_grade_and_alternative_subject_shapes(self):
        english = condition(1, "GRADE", 67, subject="ENGLISH_STUDIES_12")
        self.assertEqual(_condition(english, StudentProfileV2(grades={"ENGLISH_STUDIES_12": 73}))["status"], "met")
        self.assertEqual(_condition(english, StudentProfileV2(grades={"ENGLISH_STUDIES_12": 66}))["status"], "unmet")
        math = condition(2, "GRADE", 60, subject="MATH_11",
                         parameters={"accepted_equivalent_or_assessment": True},
                         accepted_values=["Pre-Calculus 11", "Foundations of Math 11"])
        evaluated = _condition(math, StudentProfileV2(grades={"PRE_CALCULUS_11": 64}))
        self.assertEqual(evaluated["status"], "met")
        self.assertEqual(evaluated["matched_subject"], "PRE_CALCULUS_11")

    def test_nested_and_or_keeps_mixed_branch_states(self):
        rule = {"rule_set_id": 1, "name": "Construction-style pathways", "groups": [{
            "rule_group_id": 1, "operator": "AND", "conditions": [
                condition(1, "ENGLISH_GRADE", 73, subject="ENGLISH_STUDIES_12")],
            "children": [{"rule_group_id": 2, "operator": "OR", "conditions": [], "children": [
                {"rule_group_id": 3, "operator": "AND", "children": [], "conditions": [
                    condition(3, "RELATED_POSTSECONDARY_CREDENTIAL_GPA", 67),
                    condition(4, "WORK_EXPERIENCE", 1, unit="YEAR") ]},
                {"rule_group_id": 4, "operator": "AND", "children": [], "conditions": [
                    condition(5, "RED_SEAL_TRADE") ]}
            ]}]
        }]}
        result = _evaluate_rule_set(rule, StudentProfileV2(
            grades={"ENGLISH_STUDIES_12": 75}, red_seal_trade="Carpenter",
        ))
        self.assertEqual(result["status"], "met")
        failed_route, passed_route = result["groups"][0]["children"][0]["children"]
        self.assertEqual(failed_route["status"], "missing_student_information")
        self.assertEqual(passed_route["status"], "met")

    def test_multifactor_partial_does_not_collapse_to_yes_or_no(self):
        rule = {"rule_set_id": 1, "name": "Partial", "groups": [{
            "rule_group_id": 1, "operator": "AND", "children": [], "conditions": [
                condition(1, "GRADE", 67, subject="ENGLISH_STUDIES_12"),
                condition(2, "WORK_EXPERIENCE", 2, unit="YEAR"),
                condition(3, "CREDENTIAL", subject="NURSING_DIPLOMA"),
            ]}]}
        result = _evaluate_rule_set(rule, StudentProfileV2(
            grades={"ENGLISH_STUDIES_12": 70}, work_experience_years=3,
        ))
        self.assertEqual(result["status"], "missing_student_information")
        self.assertEqual([x["status"] for x in result["groups"][0]["conditions"]],
                         ["met", "met", "missing_student_information"])

    def test_work_experience_units_and_recency(self):
        item = condition(1, "WORK_EXPERIENCE", 6, subject="ACUTE_CARE", unit="MONTHS",
                         parameters={"recency_qualification": "human_confirmation"})
        result = _condition(item, StudentProfileV2(work_experience_months_by_area={"ACUTE_CARE": 8}))
        self.assertEqual(result["status"], "human_review_required")
        self.assertEqual(result["reason"], "recency_requires_confirmation")
        self.assertEqual(_condition(item, StudentProfileV2(
            work_experience_months_by_area={"ACUTE_CARE": 4}))["status"], "unmet")

    def test_combined_average_and_credit_thresholds(self):
        option = condition(1, "ENTRY_OPTION_3", parameters={
            "courses": ["ELEX7010", "ELEX7020", "ELEX7030", "ELEX7040"],
            "courses_required": 3, "aggregate_average_minimum": 70,
        })
        profile = StudentProfileV2(grades={"ELEX7010": 68, "ELEX7020": 70,
                                           "ELEX7030": 72, "ELEX7040": 80})
        self.assertEqual(_condition(option, profile)["status"], "met")
        credits = condition(2, "CREDITS", 18, subject="ACADEMIC_FOUNDATIONS", unit="CREDITS")
        self.assertEqual(_condition(credits, StudentProfileV2(
            course_credits={"ENGL1177": 3, "MATH1001": 6}))["status"], "unmet")
        standard = condition(3, "STANDARD_ENTRY", 2.8, unit="GPA_4",
                             parameters={"percentage_equivalent": 70})
        self.assertEqual(_condition(standard, StudentProfileV2(
            credentials=["bachelor degree in computer science"], gpa=3.1, gpa_scale=4))["status"], "met")

    def test_course_prerequisite_and_or_minimum_grades(self):
        group = {"group_type": "OR", "conditions": [
            {"condition_type": "COURSE", "prerequisite_course_id": "COMP1511", "minimum_grade": 60},
            {"condition_type": "COURSE", "prerequisite_course_id": "COMP1537", "minimum_grade": 65},
        ]}
        result = _evaluate_prerequisite_group(group, StudentProfileV2(
            completed_courses=["COMP1537"], grades={"COMP1537": 70}))
        self.assertEqual(result["status"], "met")
        self.assertEqual([item["status"] for item in result["conditions"]],
                         ["missing_student_information", "met"])
        low = _evaluate_prerequisite_group({"group_type": "AND", "conditions": [
            {"condition_type": "COURSE", "prerequisite_course_id": "COMP1511", "minimum_grade": 60},
        ]}, StudentProfileV2(completed_courses=["COMP1511"], grades={"COMP1511": 55}))
        self.assertEqual(low["status"], "unmet")

    def test_effective_date_and_intake_require_student_context(self):
        transition = condition(1, "GRADE", 67, subject="ENGLISH_STUDIES_12",
                               parameters={"effective_for_applications_after": "2026-09-30"})
        self.assertEqual(_condition(transition, StudentProfileV2())["status"], "missing_student_information")
        before = _condition(transition, StudentProfileV2(application_date=date(2026, 9, 1)))
        self.assertFalse(before["applicable"])
        after = _condition(transition, StudentProfileV2(
            application_date=date(2026, 10, 1), grades={"ENGLISH_STUDIES_12": 68}))
        self.assertEqual(after["status"], "met")

    def test_international_applicability_and_human_boundary(self):
        item = condition(1, "INTERNATIONAL_CREDENTIAL_EVALUATION")
        self.assertEqual(_condition(item, StudentProfileV2())["status"], "missing_student_information")
        domestic = _condition(item, StudentProfileV2(international_status="domestic"))
        self.assertFalse(domestic["applicable"])
        international = _condition(item, StudentProfileV2(
            international_status="international", credential_country="India"))
        self.assertEqual(international["status"], "human_review_required")

    def test_unstructured_and_unknown_are_explicit_human_review(self):
        self.assertEqual(_condition(condition(1, "OFFICIAL_ADMISSION_REQUIREMENTS"), StudentProfileV2())["reason"],
                         "unstructured_official_requirement")
        unknown = _condition(condition(2, "NEW_UNSUPPORTED_RULE"), StudentProfileV2())
        self.assertEqual(unknown["status"], "human_review_required")
        self.assertEqual(unknown["reason"], "unsupported_structured_condition")

    def test_evidence_unavailable_and_retrieval_failure_are_distinct(self):
        absent = FailureRepository("absent").evaluate_admission("FIXTURE", StudentProfileV2())
        failed = FailureRepository("failure").evaluate_admission("FIXTURE", StudentProfileV2())
        self.assertEqual(absent["data"]["status"], "evidence_unavailable")
        self.assertEqual(failed["data"]["status"], "retrieval_failure")
        self.assertEqual(failed["status"], "data_unavailable")
        self.assertEqual(_combine(["unmet", "retrieval_failure"], "AND"), "unmet")
        self.assertEqual(_combine(["met", "retrieval_failure"], "OR"), "met")

    def test_later_grade_correction_supersedes_with_provenance(self):
        initial = AdvisorV2State(active_kind="program", program_id="FIXTURE",
                                 last_question_class="admission_eligibility")
        first = answer_advisor_v2("English Studies 12 is 68%", conversation_state=initial,
                                  repository=FailureRepository("absent"))
        corrected = answer_advisor_v2("Actually English Studies 12 is 73%",
                                      conversation_state=first["conversation_state"],
                                      repository=FailureRepository("absent"))
        state = corrected["conversation_state"]
        self.assertEqual(state["student_profile"]["grades"]["ENGLISH_STUDIES_12"], 73)
        history = state["profile_provenance"]["grades.ENGLISH_STUDIES_12"]
        self.assertEqual([item["value"] for item in history], [68, 73])
        self.assertEqual(history[-1]["supersedes"], 68)
        self.assertIn("grades.ENGLISH_STUDIES_12",
                      corrected["observability"]["profile"]["conflicting_fields"])

    def test_decimal_telemetry_serializer_keeps_json_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "telemetry.json"
            save(path, {"credits": Decimal("1.00"), "price": Decimal("0.127436")})
            raw = path.read_text(encoding="utf-8")
            loaded = json.loads(raw)
            self.assertEqual(loaded["credits"], 1)
            self.assertIsInstance(loaded["price"], float)
            self.assertNotIn('"0.127436"', raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
