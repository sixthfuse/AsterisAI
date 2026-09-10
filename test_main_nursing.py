import unittest

from academic_rules import get_program_rules
from ai_advisor import compare_programs, find_programs, get_program_details, resolve_academic_context
from database import get_connection
from nursing_requirements import get_nursing_requirements


class MainNursingRegressionTests(unittest.TestCase):
    PROGRAM_ID = "8875BSN"

    def test_main_program_aliases_do_not_route_to_specialty(self):
        for query in ("show me the nursing program", "regular nursing degree", "full-time nursing program", "main BSN"):
            with self.subTest(query=query):
                self.assertEqual([p["program_id"] for p in find_programs(query)], [self.PROGRAM_ID])

    def test_family_counts_distinguish_all_nursing_from_specialty(self):
        all_nursing = find_programs("how many nursing programs do you offer?")
        specialty = find_programs("how many Specialty Nursing programs?")
        self.assertEqual(len(all_nursing), 28)
        self.assertEqual(len(specialty), 27)
        self.assertIn(self.PROGRAM_ID, {p["program_id"] for p in all_nursing})
        self.assertNotIn(self.PROGRAM_ID, {p["program_id"] for p in specialty})
        self.assertIn("Advanced Certificate", {p["credential"] for p in all_nursing})

    def test_three_year_three_term_delivery_and_intakes(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT duration_years,terms_per_year,total_credits,intake_months,international_eligibility FROM program_delivery_facts WHERE program_id=%s", (self.PROGRAM_ID,))
            years, terms, credits, intakes, international = cursor.fetchone()
        self.assertEqual(float(years), 3)
        self.assertEqual(terms, 3)
        self.assertEqual(float(credits), 137)
        self.assertEqual(intakes, ["January", "April", "September"])
        self.assertIn("not available", international.lower())

    def test_course_matrix_has_nine_terms_and_specialty_component(self):
        details = get_program_details(self.PROGRAM_ID)
        names = [c["component_name"] for c in details["curriculum"]["components"]]
        self.assertTrue(all(f"Term {term}" in names for term in range(1, 10)))
        self.assertTrue(any("Specialty Nursing" in name for name in names))
        self.assertEqual(len({c["course_id"] for c in details["courses"]}), 48)
        self.assertEqual({c["level"] for c in details["courses"] if str(c["term"]) in ("1","2","3")}, {1})
        self.assertEqual({c["level"] for c in details["courses"] if str(c["term"]) in ("7","8","9")}, {3})

    def test_admission_raw_and_structured_thresholds(self):
        admission = get_program_rules(self.PROGRAM_ID, "ADMISSION")["rule_sets"][0]
        self.assertIn("Competitive Entry: Three-step process", admission["notes"])
        self.assertIn("18.0 post-secondary credits", admission["notes"])
        conditions = [c for g in admission["groups"] for c in g["conditions"]]
        english = next(c for c in conditions if c["subject_id"] == "ENGLISH_STUDIES_12")
        self.assertEqual(float(english["minimum_value"]), 67)
        self.assertTrue(any(c["subject_id"] == "MANDATORY_APPLICANT_QUESTIONNAIRE" and not c["parameters"]["executable"] for c in conditions))

    def test_clinical_practicum_and_human_confirmation(self):
        requirements = get_nursing_requirements(self.PROGRAM_ID)
        codes = {r["requirement_code"] for r in requirements["clinical_placement"]}
        self.assertTrue({"CRIMINAL_RECORD_CHECK", "IMMUNIZATION_RECORDS", "RESPIRATOR_FIT_TEST", "CPR_BLS_HCP"}.issubset(codes))
        self.assertTrue(all(r["verification_method"] == "HUMAN_CONFIRMATION" for r in requirements["clinical_placement"]))
        details = get_program_details(self.PROGRAM_ID)
        self.assertIn("BSNC8100", {c["course_id"] for c in details["courses"] if c["course_type"] == "CLINICAL"})

    def test_progression_completion_transfer_and_international_rules(self):
        for scope in ("CONTINUATION", "COMPLETION", "TRANSFER", "INTERNATIONAL"):
            self.assertTrue(get_program_rules(self.PROGRAM_ID, scope)["rule_sets"], scope)
        continuation = get_program_rules(self.PROGRAM_ID, "CONTINUATION")["rule_sets"][0]["notes"]
        self.assertIn("minimum passing grade", continuation.lower())
        international = compare_programs("Which nursing programs accept international students?")
        main = next(p for p in international["programs"] if p["program_id"] == self.PROGRAM_ID)
        self.assertEqual(main["classification"], "explicitly unavailable")

    def test_context_switches_between_main_and_specialty(self):
        context = resolve_academic_context("Tell me about the main BSN", [], None)
        self.assertEqual(context["program_id"], self.PROGRAM_ID)
        switched = resolve_academic_context("Switch to Critical Care Standard specialty nursing", [], self.PROGRAM_ID)
        self.assertEqual(switched["program_id"], "810ABSN")
        back = resolve_academic_context("Now switch to the regular nursing degree", [], "810ABSN")
        self.assertEqual(back["program_id"], self.PROGRAM_ID)


if __name__ == "__main__":
    unittest.main()
