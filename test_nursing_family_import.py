import unittest

from ai_advisor import find_programs, get_catalog_counts, get_program_details, resolve_academic_context
from nursing_requirements import get_nursing_requirements
from import_nursing_family import extract_international_applicant_rules, load_audits


class NursingFamilyImportTests(unittest.TestCase):
    PROGRAM_IDS = {
        "810ABSN", "810BBSN", "810CBSN", "810DBSN", "810FBSN", "810GBSN",
        "810HBSN", "810KBSN", "810MBSN", "810NBSN", "810QBSN", "810SBSN",
    }

    def test_audits_capture_authoritative_international_restrictions(self):
        audits = load_audits("program_extractor_audit/nursing_batch", exclude=())
        self.assertEqual(len(audits), 12)
        for audit in audits:
            text = extract_international_applicant_rules(audit)
            self.assertIn("valid work permit", text.lower())
            self.assertIn("not eligible for a study permit", text.lower())
            self.assertIn("not eligible for a pgwp", text.lower())
            self.assertIn("program head approval", text.lower())

    def test_all_specialties_are_independent_active_records(self):
        programs = find_programs("all programs")
        ids = {program["program_id"] for program in programs if program["program_id"].startswith("810")}
        self.assertEqual(ids, self.PROGRAM_IDS)
        self.assertEqual(len(ids), 12)

    def test_updated_active_program_and_course_counts(self):
        self.assertEqual(get_catalog_counts(), {
            "active_program_count": 374,
            "course_record_count": 3976,
        })

    def test_standard_and_combined_critical_care_options_do_not_collapse(self):
        standard = get_program_details("810ABSN")
        combined = get_program_details("810KBSN")
        self.assertIn("Standard Option", standard["program_name"])
        self.assertIn("Combined Critical Care/Emergency", combined["program_name"])
        standard_courses = {course["course_id"] for course in standard["courses"]}
        combined_courses = {course["course_id"] for course in combined["courses"]}
        self.assertNotEqual(standard_courses, combined_courses)
        self.assertIn("NSER7410", combined_courses)
        self.assertNotIn("NSER7410", standard_courses)

    def test_standard_and_combined_emergency_options_do_not_collapse(self):
        standard = get_program_details("810BBSN")
        combined = get_program_details("810NBSN")
        self.assertIn("Standard Option", standard["program_name"])
        self.assertIn("Combined Emergency/Critical Care", combined["program_name"])
        self.assertNotEqual(
            {course["course_id"] for course in standard["courses"]},
            {course["course_id"] for course in combined["courses"]},
        )

    def test_context_switches_between_similar_specialties(self):
        conversation = [
            {"role": "user", "content": "Tell me about the Critical Care Standard nursing program."},
            {"role": "assistant", "content": "Here is the Critical Care Standard option."},
        ]
        first = resolve_academic_context("What courses are in this program?", conversation, "810ABSN")
        self.assertEqual(first["program_id"], "810ABSN")
        switched = resolve_academic_context(
            "Switch to the combined Critical Care Emergency nursing option.", conversation, "810ABSN"
        )
        self.assertEqual(switched["program_id"], "810KBSN")
        follow_up = resolve_academic_context(
            "What clinical requirements apply?",
            conversation + [{"role": "user", "content": "Switch to the combined Critical Care Emergency nursing option."}],
            "810KBSN",
        )
        self.assertEqual(follow_up["program_id"], "810KBSN")

    def test_each_clinical_specialty_uses_human_confirmation_without_hours(self):
        for program_id in self.PROGRAM_IDS:
            with self.subTest(program_id=program_id):
                requirements = get_nursing_requirements(program_id)
                for requirement in requirements["clinical_placement"]:
                    if not requirement["executable"]:
                        self.assertEqual(requirement["verification_method"], "HUMAN_CONFIRMATION")
                for requirement in requirements["practice_hours"]:
                    self.assertIsNone(requirement["required_hours"])
                    self.assertFalse(requirement["executable"])


if __name__ == "__main__":
    unittest.main()
