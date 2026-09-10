import unittest

from academic_rules import get_program_rules
from ai_advisor import find_programs, get_program_details, resolve_academic_context
from nursing_requirements import assess_nursing_applicant, assess_nursing_requirements, get_nursing_requirements


class Program6NursingRegressionTests(unittest.TestCase):
    PROGRAM_ID = "810ABSN"

    def test_program_identification_and_overview(self):
        matches = find_programs("critical care standard nursing")
        self.assertEqual(matches[0]["program_id"], self.PROGRAM_ID)
        details = get_program_details(self.PROGRAM_ID)
        self.assertIn("seriously ill", details["program_overview"].lower())
        self.assertEqual(details["study_mode"], "Part-time")
        self.assertEqual(len(details["courses"]), 16)

    def test_admissions_and_eligibility_routing_stays_in_program(self):
        context = resolve_academic_context(
            "What admissions requirements do I need for the Critical Care Standard nursing program?",
            [], None,
        )
        self.assertEqual(context["program_id"], self.PROGRAM_ID)
        follow_up = resolve_academic_context(
            "Do I qualify if I have six months of acute-care experience?",
            [{"role": "user", "content": "Tell me about Critical Care Standard nursing."}],
            self.PROGRAM_ID,
        )
        self.assertEqual(follow_up["program_id"], self.PROGRAM_ID)

    def test_licensure_and_specialty_experience_classification(self):
        rules = get_program_rules(self.PROGRAM_ID, "ADMISSION")["rule_sets"][0]
        conditions = [c for group in rules["groups"] for c in group["conditions"]]
        licence = next(c for c in conditions if c["condition_type"] == "LICENSURE")
        experience = next(c for c in conditions if c["condition_type"] == "WORK_EXPERIENCE")
        self.assertFalse(licence["parameters"]["executable"])
        self.assertEqual(float(experience["minimum_value"]), 6)
        self.assertEqual(experience["unit"], "MONTHS")
        self.assertEqual(experience["parameters"]["recency_qualification"], "human_confirmation")

    def test_clinical_placement_is_not_an_academic_prerequisite(self):
        requirements = get_nursing_requirements(self.PROGRAM_ID)
        codes = {item["requirement_code"] for item in requirements["clinical_placement"]}
        self.assertIn("CPR_CERTIFICATION", codes)
        self.assertIn("RESPIRATOR_FIT_TEST", codes)
        details = get_program_details(self.PROGRAM_ID)
        clinical_courses = {c["course_id"] for c in details["courses"] if c["course_type"] == "CLINICAL"}
        self.assertEqual(clinical_courses, {"NSCC7420", "NSCC7620"})

    def test_practice_hours_are_distinct_and_not_invented(self):
        requirements = get_nursing_requirements(self.PROGRAM_ID)
        practice = requirements["practice_hours"][0]
        self.assertIsNone(practice["required_hours"])
        self.assertFalse(practice["executable"])
        assessment = assess_nursing_requirements(self.PROGRAM_ID, {}, {})
        self.assertTrue(any(i["category"] == "PRACTICE_HOURS" for i in assessment["human_confirmation"]))

    def test_course_follow_up_stays_in_scope_and_specialty_not_substituted(self):
        conversation = [{"role": "user", "content": "Tell me about Critical Care Standard nursing."}]
        context = resolve_academic_context("What courses are in this program?", conversation, self.PROGRAM_ID)
        self.assertEqual(context["program_id"], self.PROGRAM_ID)
        details = get_program_details(context["program_id"])
        self.assertNotIn("Emergency", details["program_name"])
        self.assertTrue(all(course["course_id"] not in {"NSER7110", "NSHA7100"} for course in details["courses"]))

    def test_complex_applicant_separates_met_missing_and_confirmation(self):
        assessment = assess_nursing_applicant(
            self.PROGRAM_ID,
            {"ENGLISH_STUDIES_12": 80, "NURSING_DIPLOMA": True, "ACUTE_CARE": 4},
            {"CLINICAL_APPLICATION": True, "CPR_CERTIFICATION": True, "RN_REGISTRATION": True},
            {},
        )
        met_subjects = {i.get("subject_id") for i in assessment["met"]}
        self.assertTrue({"ENGLISH_STUDIES_12", "NURSING_DIPLOMA"}.issubset(met_subjects))
        self.assertTrue(any(i.get("requirement_code") == "CLINICAL_APPLICATION" for i in assessment["met"]))
        self.assertTrue(any(i.get("subject_id") == "ACUTE_CARE" for i in assessment["missing"]))
        confirmation = {i.get("requirement_code") for i in assessment["human_confirmation"]}
        self.assertTrue({"RN_REGISTRATION", "CPR_CERTIFICATION", "RESPIRATOR_FIT_TEST", "INFLUENZA_POLICY", "PUBLISHED_CLINICAL_HOURS"}.issubset(confirmation))
        self.assertFalse(assessment["eligible"])
        self.assertTrue(assessment["academic_and_non_course_separated"])


if __name__ == "__main__":
    unittest.main()
