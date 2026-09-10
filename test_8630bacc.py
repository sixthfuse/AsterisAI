import unittest

from academic_rules import get_course_requirements, get_program_curriculum, get_program_rules
from ai_advisor import find_programs, get_program_details, get_program_progression_requirements, resolve_academic_context
from database import get_connection
from eligibility import check_course_eligibility


class BachelorAccountingTests(unittest.TestCase):
    PROGRAM_ID = "8630BACC"

    def test_identity_aliases_and_bachelor_family(self):
        details = get_program_details(self.PROGRAM_ID)
        self.assertEqual((details["program_name"], details["credential"]), ("Accounting", "Bachelor's Degree"))
        self.assertIn("Full-time", details["study_mode"]); self.assertIn("Flexible Learning", details["study_mode"])
        for query in ("Bachelor of Accounting", "Accounting degree", "BCIT accounting bachelor", "BAcc"):
            self.assertEqual([p["program_id"] for p in find_programs(query)], [self.PROGRAM_ID])
        self.assertIn(self.PROGRAM_ID, [p["program_id"] for p in find_programs("bachelor degree programs")])

    def test_admission_pathways_and_thresholds(self):
        rules = get_program_rules(self.PROGRAM_ID, "ADMISSION")["rule_sets"]
        conditions = [c for r in rules for g in r["groups"] for c in g["conditions"]]
        by_type = {c["condition_type"]: c for c in conditions}
        self.assertEqual(float(by_type["GPA"]["minimum_value"]), 70)
        self.assertEqual(float(by_type["ENGLISH_GRADE"]["minimum_value"]), 67)
        self.assertTrue(by_type["PRIOR_DIPLOMA"]["parameters"]["executable"])
        self.assertTrue(any(c["parameters"].get("human_confirmation_only") for c in conditions))

    def test_complete_matrix_choice_pool_and_optional_workterms(self):
        curriculum = get_program_curriculum(self.PROGRAM_ID)
        courses = {c["course_id"]: c for component in curriculum["components"] for c in component["courses"]}
        self.assertEqual(len(courses), 17)
        self.assertEqual(courses["FMGT8911"]["course_role"], "REQUIRED")
        self.assertEqual(courses["ACCG6310"]["course_role"], "ELECTIVE_POOL")
        self.assertEqual(courses["FMGT7610"]["course_role"], "OPTIONAL")
        choice = get_program_rules(self.PROGRAM_ID, "CURRICULUM")["rule_sets"]
        self.assertTrue(any(r["exact_choice_count"] == 7 for r in choice))

    def test_mode_international_progression_and_professional_advisory(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT study_mode,start_date FROM program_offerings WHERE program_id=%s", (self.PROGRAM_ID,))
            offerings = cursor.fetchall()
        self.assertEqual(sum("Full-time" == row[0] for row in offerings), 2)
        self.assertEqual(sum("Part-time" in row[0] for row in offerings), 3)
        international = get_program_rules(self.PROGRAM_ID, "INTERNATIONAL")["rule_sets"]
        self.assertTrue(any("unavailable to international" in (r["notes"] or "") for r in international))
        professional = get_program_rules(self.PROGRAM_ID, "PROFESSIONAL")["rule_sets"]
        conditions = [c for r in professional for g in r["groups"] for c in g["conditions"]]
        self.assertTrue(all(not c["parameters"]["executable"] for c in conditions))
        self.assertTrue(any("seven years" in row["description"] for row in get_program_progression_requirements(self.PROGRAM_ID)))

    def test_workterm_prerequisite_and_context_switching(self):
        conditions = get_course_requirements("FMGT7620")["groups"][0]["conditions"]
        self.assertEqual(conditions[0]["prerequisite_course_id"], "FMGT7610")
        self.assertFalse(check_course_eligibility("FMGT7620", [], self.PROGRAM_ID)["eligible"])
        conversation = [{"role":"user","content":"Tell me about the Business Administration Graduate Certificate"},
                        {"role":"assistant","content":"It is a graduate business program."}]
        self.assertEqual(resolve_academic_context("Switch to BAcc", conversation, "A700GRCERT")["program_id"], self.PROGRAM_ID)
        reverse = [{"role":"user","content":"Tell me about the Bachelor of Accounting"},
                   {"role":"assistant","content":"It is a bachelor's degree."}]
        self.assertEqual(resolve_academic_context("What about the graduate business certificate?", reverse, self.PROGRAM_ID)["program_id"], "A700GRCERT")

    def test_governed_revision_is_active_and_hash_approved(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("""SELECT r.payload_sha256,r.lifecycle_status,a.approval_status
                FROM program_active_import_revisions ar JOIN program_import_revisions r USING(revision_id)
                JOIN program_import_approvals a ON a.program_id=r.program_id AND a.payload_sha256=r.payload_sha256
                WHERE ar.program_id=%s""", (self.PROGRAM_ID,))
            payload_hash, status, approval = cursor.fetchone()
        self.assertEqual((len(payload_hash), status, approval), (64, "active", "approved"))


if __name__ == "__main__": unittest.main()
