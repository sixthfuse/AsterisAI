import unittest

from academic_rules import get_program_curriculum, get_program_rules
from ai_advisor import (
    AdvisorIntent,
    classify_intent,
    find_programs,
    get_program_details,
    get_program_progression_requirements,
    resolve_academic_context,
)
from database import get_connection


class AppliedComputingMScTests(unittest.TestCase):
    PROGRAM_ID = "M600MSC"

    def test_program_identity_delivery_and_duration(self):
        details = get_program_details(self.PROGRAM_ID)
        self.assertEqual(details["program_name"], "Applied Computing")
        self.assertEqual(details["credential"], "Master of Science / Master's Degree")
        self.assertEqual(details["study_mode"], "Full-time")
        self.assertEqual(details["delivery_method"], "In person")
        self.assertIn("Burnaby", details["campus"])
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT duration_years,terms_per_year,total_credits,intake_months FROM program_delivery_facts WHERE program_id=%s", (self.PROGRAM_ID,))
            self.assertEqual(cursor.fetchone(), (2, 2, 30, ["September"]))

    def test_natural_name_routing_and_context_switching(self):
        for query in ("Applied Computing MSc", "Master of Science in Applied Computing", "computing masters"):
            self.assertEqual([p["program_id"] for p in find_programs(query)], [self.PROGRAM_ID])
            self.assertEqual(resolve_academic_context(query, [], None)["program_id"], self.PROGRAM_ID)
        self.assertEqual(classify_intent("computing masters"), AdvisorIntent.PROGRAM_INFO)
        conversation = [{"role":"user","content":"Tell me about the full-time Nursing program"},
                        {"role":"assistant","content":"The Nursing BSN is full-time."}]
        self.assertEqual(resolve_academic_context("What about Applied Computing MSc?", conversation, "8875BSN")["program_id"], self.PROGRAM_ID)

    def test_curriculum_preserves_true_year_two_alternatives(self):
        curriculum = get_program_curriculum(self.PROGRAM_ID)
        names = {component["component_name"] for component in curriculum["components"]}
        self.assertIn("Thesis Path (30 weeks – September to April)", names)
        self.assertIn("Project & Internship Path", names)
        rules = get_program_rules(self.PROGRAM_ID, "PATHWAY")["rule_sets"][0]
        self.assertEqual(rules["exact_choice_count"], 1)
        root = rules["groups"][0]
        labels = {group["label"] for group in root["children"]}
        self.assertEqual(labels, {"Thesis Path", "Project & Internship Path"})
        courses = {group["label"]: {c["subject_id"] for c in group["conditions"]} for group in root["children"]}
        self.assertEqual(courses["Thesis Path"], {"COMP9600"})
        self.assertEqual(courses["Project & Internship Path"], {"COMP9290", "COMP9400", "COMP9500"})

    def test_admission_structure_separates_human_confirmation(self):
        rule = get_program_rules(self.PROGRAM_ID, "ADMISSION")["rule_sets"][0]
        conditions = []
        def collect(group):
            conditions.extend(group["conditions"])
            for child in group["children"]:
                collect(child)
        collect(rule["groups"][0])
        by_type = {item["condition_type"]: item for item in conditions}
        self.assertTrue(by_type["ENGLISH_GRADE"]["parameters"]["executable"])
        self.assertTrue(by_type["STANDARD_ENTRY"]["parameters"]["executable"])
        for kind in ("ALTERNATE_ENTRY", "REFERENCES", "INTERNATIONAL_CREDENTIAL_EVALUATION", "COMPETITIVE_DEPARTMENT_REVIEW"):
            self.assertEqual(by_type[kind]["parameters"]["verification"], "human_confirmation")

    def test_intake_application_status_and_sequence(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT offering_id,application_status FROM program_offerings WHERE program_id=%s ORDER BY start_date", (self.PROGRAM_ID,))
            self.assertEqual(cursor.fetchall(), [("M600MSC-2026-09", "Closed to new applications"), ("M600MSC-2027-09", "Opens 2026-10-01")])
        requirements = get_program_progression_requirements(self.PROGRAM_ID)
        self.assertTrue(any(r.get("type") == "PROGRAM_AVERAGE" and "70%" in r["description"] for r in requirements))
        self.assertTrue(any(r.get("type") == "SUPERVISORY_REVIEW" for r in requirements))

    def test_course_gap_reconciliation_and_master_credential_family(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM courses WHERE course_id IN ('COMP9040','COMP9060','COMP9080','COMP9130','COMP9150','COMP9170','COMP9190','COMP9200','COMP9290','COMP9400','COMP9500','COMP9600')")
            self.assertEqual(cursor.fetchone()[0], 12)
        masters = find_programs("What Master's Degree programs are available?")
        self.assertEqual([p["program_id"] for p in masters],
                         [self.PROGRAM_ID, "M220MASC", "M120MENG", "M410MSC", "M500MENG"])


if __name__ == "__main__":
    unittest.main()
