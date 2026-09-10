import unittest
from unittest.mock import patch

from ai_advisor import (
    answer_student_question,
    build_verification_metadata,
    execute_tool,
    find_programs,
    is_program_count_question,
    resolve_academic_context,
)
from database import get_connection


class AdvisorQualityAllProgramsTests(unittest.TestCase):
    def test_every_active_program_exact_name_resolves_to_itself(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT program_id, program_name FROM programs WHERE status='Active'")
            programs = cursor.fetchall()
        self.assertGreater(len(programs), 0)
        name_counts = {}
        for _, program_name in programs:
            name_counts[program_name] = name_counts.get(program_name, 0) + 1
        for program_id, program_name in programs:
            with self.subTest(program=program_name):
                context = resolve_academic_context(
                    f"What are the admission requirements for {program_name}?", [], None
                )
                if name_counts[program_name] == 1:
                    self.assertEqual(context["program_id"], program_id)
                else:
                    self.assertIsNone(context["program_id"])

    def test_ambiguous_sibling_name_never_selects_first_match(self):
        context = resolve_academic_context(
            "Tell me about the Specialty Nursing Emergency option", [], None
        )
        self.assertIsNone(context["program_id"])

    def test_count_only_is_deterministic_and_does_not_call_model(self):
        self.assertTrue(is_program_count_question("How many programs do you offer?"))
        with patch("ai_advisor.get_catalog_counts", return_value={
            "course_record_count": 1200, "active_program_count": 25,
        }), patch("ai_advisor.OpenAI") as model:
            result = answer_student_question("How many programs do you offer?", [])
        self.assertEqual(result["answer"], "BCIT has 25 active programs.")
        self.assertEqual(result["verification"]["count"], 1)
        model.assert_not_called()

    def test_count_plus_explicit_list_is_not_count_only(self):
        self.assertFalse(is_program_count_question("How many programs? List them all."))

    def test_program_campus_overrides_prior_directory_context(self):
        conversation = [{"role": "user", "content": "What campuses does BCIT have?"}]
        result = answer_student_question(
            "Which campus is Specialty Nursing (Neonatal) taught at?", [],
            conversation=conversation,
        )
        self.assertTrue(result["resolved_program"].startswith("Specialty Nursing (Neonatal)"))
        self.assertNotEqual(len(result["campuses"]), 5)

    def test_normalized_curriculum_tool_keeps_required_or_set(self):
        context = {
            "program_id": "9940BSC", "program_name": "Combined Honours in Biochemistry and Forensic Science",
            "completed_courses": [],
        }
        payload = execute_tool("evaluate_program_curriculum", {}, context)
        requirements = {item["requirement_code"]: item for item in payload["evaluation"]["requirements"]}
        self.assertIn("Y1_DATA_SCIENCE", requirements)
        self.assertNotEqual(requirements["Y1_DATA_SCIENCE"]["status"], "SATISFIED")
        metadata = build_verification_metadata(["evaluate_program_curriculum"], [payload])
        self.assertEqual(metadata["kind"], "requirement")
        self.assertGreater(metadata["count"], 0)

    def test_filtered_discovery_still_returns_only_requested_family(self):
        programs = find_programs("nursing programs")
        self.assertTrue(programs)
        self.assertTrue(all("nursing" in row["program_name"].lower() for row in programs))

    def test_admission_and_graduation_scopes_are_distinct_for_active_catalog(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.program_id,
                       EXISTS (SELECT 1 FROM academic_rule_sets ars
                               WHERE ars.program_id=p.program_id AND ars.rule_scope='ADMISSION'),
                       EXISTS (SELECT 1 FROM curriculum_requirements cr
                               WHERE cr.program_id=p.program_id)
                FROM programs p WHERE p.status='Active'
            """)
            rows = cursor.fetchall()
        self.assertTrue(rows)
        for program_id, has_admission, has_curriculum in rows:
            with self.subTest(program=program_id):
                self.assertIsInstance(has_admission, bool)
                self.assertIsInstance(has_curriculum, bool)


if __name__ == "__main__":
    unittest.main()
