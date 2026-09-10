import unittest

from fastapi.testclient import TestClient

from ai_advisor import answer_student_question
from campus_information import find_campus, programs_at_campus
from main import app


class CampusInformationTests(unittest.TestCase):
    def answer(self, question, **kwargs):
        return answer_student_question(question, [], **kwargs)["answer"]

    def test_burnaby_address_lookup(self):
        answer = self.answer("Where is the Burnaby campus?")
        self.assertIn("3700 Willingdon Avenue, Burnaby, BC V5G 3H2", answer)

    def test_burnaby_main_phone_lookup(self):
        answer = self.answer("What is the phone number for the Burnaby campus?")
        self.assertEqual(answer, "**Burnaby Campus** main phone: 604-434-5734.")

    def test_phone_is_general_campus_number_not_service_specific(self):
        answer = self.answer("What is the phone number for the Aerospace Technology Campus?")
        self.assertEqual(answer, "**Aerospace Technology Campus** main phone: 604-434-5734.")

    def test_aerospace_address_lookup(self):
        answer = self.answer("What is the address of the Aerospace Technology Campus?")
        self.assertIn("3800 Cessna Drive, Richmond, BC V7B 0A1", answer)

    def test_annacis_island_lookup(self):
        answer = self.answer("Where is Annacis Island Campus?")
        self.assertIn("1608 Cliveden Avenue, Delta, BC V3M 6P1", answer)

    def test_programs_at_campus(self):
        answer = self.answer("Which programs are at the Aerospace Technology Campus?")
        self.assertIn("Aircraft Maintenance Engineer", answer)

    def test_active_program_context(self):
        answer = self.answer("Where is this program offered?", program_id="8630BACC")
        self.assertIn("Burnaby Campus", answer)

    def test_multi_campus_possible_site_preserved(self):
        answer = self.answer("Where is this program offered?", program_id="M600MSC")
        self.assertIn("Burnaby Campus", answer)
        self.assertIn("Possible site: **Downtown Campus**", answer)
        self.assertIn("field locations", answer)

    def test_no_navigation_content(self):
        answer = self.answer("Where is the Marine Campus?").lower()
        for forbidden in ("map", "directions", "transit", "parking", "route"):
            self.assertNotIn(forbidden, answer)

    def test_institution_scope(self):
        self.assertIsNotNone(find_campus("Burnaby campus", "BCIT"))
        self.assertIsNone(find_campus("Burnaby campus", "SAIT"))
        self.assertEqual(programs_at_campus("burnaby", "SAIT"), [])

    def test_campus_question_does_not_activate_program(self):
        result = answer_student_question("Where is the Burnaby campus?", [])
        self.assertIsNone(result["resolved_program"])


class CampusAdvisorEntryPathTests(unittest.TestCase):
    """Exercise the same /advisor entry point used by the student web app."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def post(self, question, conversation=None):
        response = self.client.post(
            "/advisor",
            json={"question": question, "conversation": conversation or []},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_exact_live_campus_count_phrases(self):
        for question in (
            "how many campuses does BCIT have?",
            "how many campus does bcit have?",
        ):
            with self.subTest(question=question):
                result = self.post(question)
                self.assertIn("5 campuses", result["answer"])
                self.assertEqual(result["tools_used"], ["campus_information"])
                self.assertIsNone(result["resolved_program"])

    def test_exact_live_campus_summary_phrase(self):
        result = self.post("campus information")
        self.assertIn("5 campuses", result["answer"])
        for name in ("Burnaby", "Downtown", "Aerospace Technology", "Annacis Island", "Marine"):
            self.assertIn(name, result["answer"])
        self.assertIsNone(result["resolved_program"])

    def test_exact_live_institution_phone_phrase(self):
        result = self.post("bcit phone number")
        self.assertIn("604-434-5734", result["answer"])
        self.assertIn("all 5 campuses", result["answer"])
        self.assertIsNone(result["resolved_program"])

    def test_named_campus_queries_through_live_entry_path(self):
        cases = {
            "what is the Burnaby campus address?": "3700 Willingdon Avenue",
            "what is the phone number for Annacis Island Campus?": "604-434-5734",
            "which programs are at the Aerospace Technology Campus?": "Aircraft Maintenance Engineer",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertIn(expected, self.post(question)["answer"])

    def test_active_program_follow_up_through_live_entry_path(self):
        conversation = [
            {"role": "user", "content": "Tell me about the Accounting bachelor's degree."},
            {"role": "assistant", "content": "Accounting is an active bachelor's degree."},
        ]
        result = self.post("where is this program offered?", conversation)
        self.assertIn("Burnaby Campus", result["answer"])

    def test_exact_multi_turn_campus_directory_sequence(self):
        conversation = []
        sequence = (
            ("how many campus does bcit have?", ("5 campuses",)),
            ("can you give me the names of them?", ("**Burnaby Campus**", "**Marine Campus**")),
            ("what about the addresses for each one of them?", ("V5G 3H2", "V7M 1A5")),
            ("what about phone numbers?", ("604-434-5734", "listed for all 5 campuses")),
        )
        for question, expected_parts in sequence:
            result = self.post(question, conversation)
            self.assertEqual(result["tools_used"], ["campus_information"])
            self.assertIsNone(result["resolved_program"])
            for expected in expected_parts:
                self.assertIn(expected, result["answer"])
            conversation.extend((
                {"role": "user", "content": question},
                {"role": "assistant", "content": result["answer"]},
            ))

    def test_live_campus_count_context_outranks_course_clarification(self):
        first_question = "how many campus are there at bcit?"
        first = self.post(first_question)
        conversation = [
            {"role": "user", "content": first_question},
            {"role": "assistant", "content": first["answer"]},
        ]
        cases = {
            "can you give me more information on them?": "**Burnaby Campus**",
            "tell me more about them": "**Downtown Campus**",
            "more information on those": "**Marine Campus**",
            "what about their addresses?": "3700 Willingdon Avenue",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                result = self.post(question, conversation)
                self.assertEqual(result["tools_used"], ["campus_information"])
                self.assertIsNone(result["resolved_program"])
                self.assertIn(expected, result["answer"])
                self.assertNotIn("course name", result["answer"].lower())

    def test_other_information_follow_up_uses_all_stored_directory_fields(self):
        conversation = [
            {"role": "user", "content": "more information about campus directory"},
            {"role": "assistant", "content": "BCIT has 5 campuses."},
        ]
        result = self.post("what other information do you have on campuses?", conversation)
        for expected in (
            "**Burnaby Campus**", "BC V5G 3H2", "largest campus",
            "active program association", "official source links", "604-434-5734",
        ):
            self.assertIn(expected, result["answer"])
        self.assertIsNone(result["resolved_program"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
