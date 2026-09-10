import unittest

from academic_rules import get_program_rules
from ai_advisor import get_program_details, get_program_progression_requirements
from database import get_connection


AME_IDS = {"1165DIPMA", "1230DIPMA", "1205DIPMA"}
ALL_IDS = AME_IDS | {"0816CM", "8660BENG", "5410DIPLT"}


def flatten(groups):
    for group in groups:
        yield from group["conditions"]
        yield from flatten(group["children"])


class SixProgramAdmissionNormalizationTests(unittest.TestCase):
    def test_all_six_use_generalized_singular_admission_scope(self):
        for program_id in ALL_IDS:
            with self.subTest(program=program_id):
                self.assertTrue(get_program_rules(program_id, "ADMISSION")["rule_sets"])
                self.assertFalse(get_program_rules(program_id, "ADMISSIONS")["rule_sets"])

    def test_advisor_program_details_exposes_normalized_admission_rules(self):
        for program_id in ALL_IDS:
            with self.subTest(program=program_id):
                rules = get_program_details(program_id)["academic_rules"]["rule_sets"]
                self.assertTrue(any(rule["scope"] == "ADMISSION" for rule in rules))

    def test_ame_admission_does_not_absorb_progression_or_regulator_rules(self):
        forbidden = {"THEORY_PASS", "PRACTICAL_PASS", "TC_ATTENDANCE", "TC_APPROVED_PROGRAM", "TC_EXPERIENCE_CREDIT"}
        for program_id in AME_IDS:
            admissions = get_program_rules(program_id, "ADMISSION")["rule_sets"]
            self.assertFalse(forbidden & {rule["name"] for rule in admissions})
            self.assertEqual({70.0}, {
                float(condition["minimum_value"])
                for scope in ("PROGRESSION",)
                for rule in get_program_rules(program_id, scope)["rule_sets"]
                for condition in flatten(rule["groups"])
                if condition["minimum_value"] is not None
            })
            self.assertEqual(95.0, float(next(flatten(
                get_program_rules(program_id, "ATTENDANCE")["rule_sets"][0]["groups"]
            ))["minimum_value"]))

    def test_applied_circular_economy_has_no_fabricated_admission_gate(self):
        rule = get_program_rules("0816CM", "ADMISSION")["rule_sets"][0]
        condition = next(flatten(rule["groups"]))
        self.assertEqual(condition["condition_type"], "NO_FORMAL_APPLICATION_REQUIRED")
        self.assertTrue(condition["parameters"]["recommended_background_is_not_required"])

    def test_ame_m_mechanical_assessment_transition_requires_intake_confirmation(self):
        rules = get_program_rules("1230DIPMA", "ADMISSION")["rule_sets"]
        conditions = [condition for rule in rules for condition in flatten(rule["groups"])]
        assessment = next(c for c in conditions if c["subject_id"] == "BCIT_MECHANICAL_REASONING_TRADES_ENTRY_ASSESSMENT")
        self.assertEqual(assessment["parameters"]["required_before_intake"], "2027-01")
        self.assertTrue(assessment["parameters"]["human_confirmation"])
        self.assertFalse(assessment["parameters"]["executable"])

    def test_civil_beng_initial_admission_exact_thresholds(self):
        rules = get_program_rules("8660BENG", "ADMISSION")["rule_sets"]
        conditions = list(flatten(rules[0]["groups"]))
        thresholds = {c["subject_id"]: float(c["minimum_value"]) for c in conditions if c["minimum_value"] is not None}
        self.assertEqual(thresholds, {
            "ENGLISH_STUDIES_12": 73.0, "PRE_CALCULUS_12": 73.0,
            "CHEMISTRY_11": 73.0, "PHYSICS_12": 73.0,
            "APPROVED_GRADE_12_ACADEMIC_COURSE": 73.0,
        })
        self.assertTrue(all(not c["parameters"].get("executable", False) for c in conditions
                            if c["condition_type"] in {"DOCUMENT", "DEPARTMENT_ASSESSMENT"}))
        self.assertNotIn("continuation", " ".join(c["description"] for c in conditions).lower())

    def test_civil_diploma_uses_beng_route_not_level_five_continuation(self):
        rule = get_program_rules("5410DIPLT", "ADMISSION")["rule_sets"][0]
        condition = next(flatten(rule["groups"]))
        self.assertEqual(condition["condition_type"], "LINKED_PROGRAM_ADMISSION")
        self.assertEqual(condition["subject_id"], "8660BENG")
        self.assertNotIn("70%", rule["notes"])
        self.assertNotIn("300 hours", rule["notes"])

    def test_progression_payload_never_contains_admission_rules(self):
        for program_id in ALL_IDS:
            with self.subTest(program=program_id):
                requirements = get_program_progression_requirements(program_id)
                self.assertFalse(any(row.get("scope") == "ADMISSION" for row in requirements))

    def test_all_active_programs_now_have_admission_rules(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.program_id FROM programs p
                WHERE p.status='Active' AND NOT EXISTS (
                    SELECT 1 FROM academic_rule_sets ars
                    WHERE ars.program_id=p.program_id AND ars.rule_scope='ADMISSION')
            """)
            self.assertEqual(cursor.fetchall(), [])


if __name__ == "__main__":
    unittest.main()
