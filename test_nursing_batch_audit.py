import unittest
from bs4 import BeautifulSoup

from nursing_batch_audit import extract_one, compare


HTML = '''<html><head><script type="application/ld+json">{"@type":"EducationalOccupationalProgram","identifier":"810ABSN","alternateName":"Specialty Nursing (Critical Care - Standard Option), Bachelor of Science in Nursing, Part-time","educationalCredentialAwarded":"Bachelor of Science in Nursing","educationalProgramMode":"Part-time","provider":{"department":{"name":"School of Health Sciences"},"address":{"addressLocality":"Burnaby"}}}</script></head><body><h1>Specialty Nursing</h1><h2>Entrance Requirements</h2><p>Applicants must be a registered nurse and employed in the specialty.</p><h2>Program Details</h2><p>Complete within seven years.</p><table id="programmatrix"><tr><th class="level">1. Required Courses</th></tr><tr><td class="course_number"><a href="/courses/example-nurs-1000/">NURS 1000</a></td><td><strong class="course_name">Clinical Practice</strong></td><td class="credits">3.0</td></tr><tr><th class="level">Total Credits:</th><th>3.0</th></tr></table></body></html>'''
URL = "https://www.bcit.ca/programs/example-810absn/"


class NursingBatchAuditTests(unittest.TestCase):
    def test_extracts_non_course_professional_rules_without_fake_prerequisites(self):
        audit = extract_one(BeautifulSoup(HTML, "html.parser"), URL, {"NURS1000"})
        concepts = {r["concept"] for r in audit["rules"]}
        self.assertIn("professional_registration_licensure", concepts)
        self.assertIn("specialty_employment_experience", concepts)
        self.assertNotIn("registered nurse", [r["course_id"] for r in audit["course_references"]])

    def test_reconciles_and_marks_clinical_courses(self):
        audit = extract_one(BeautifulSoup(HTML, "html.parser"), URL, {"NURS1000"})
        self.assertEqual(audit["existing_course_ids"], ["NURS1000"])
        self.assertEqual(audit["clinical_practicum_course_ids"], ["NURS1000"])

    def test_family_comparison_is_machine_readable(self):
        audit = extract_one(BeautifulSoup(HTML, "html.parser"), URL, {"NURS1000"})
        result = compare([audit, audit], 1168)
        self.assertEqual(result["unique_course_references"], 1)
        self.assertEqual(result["courses_shared_by_all_programs"], ["NURS1000"])
        self.assertIn("modeling_assessment", result)


if __name__ == "__main__":
    unittest.main()
