import unittest
from types import SimpleNamespace

from ai_advisor import answer_student_question, finalize_student_answer
from institutional_resources import (
    MAX_RESOURCE_LINKS,
    append_institutional_resources,
    find_institutional_resources,
)


class _Responses:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(id="resource-test", output=[], output_text=self.answer)


class _Client:
    def __init__(self, answer):
        self.responses = _Responses(answer)


class InstitutionalResourceTests(unittest.TestCase):
    def test_equivalencies_direct_request_returns_official_resource(self):
        result = answer_student_question("Where is the equivalencies page?", [], client=_Client("unused"))
        self.assertIn("https://www.bcit.ca/admission/entrance-requirements/equivalencies/", result["answer"])
        self.assertEqual(result["tools_used"], ["find_institutional_resources"])

    def test_admissions_query_gets_official_admissions_resource(self):
        answer = finalize_student_answer("Admission requirements vary by program.", "What are BCIT admissions requirements?", [])
        self.assertIn("https://www.bcit.ca/admission/", answer)

    def test_international_student_query_gets_official_resource(self):
        answer = append_institutional_resources("I can help with that.", "I am an international student")
        self.assertIn("https://www.bcit.ca/international-students/", answer)

    def test_tuition_cost_query_gets_official_resource(self):
        answer = append_institutional_resources("Costs depend on the program.", "What is the program cost?")
        self.assertIn("https://www.bcit.ca/admission/tuition-fees/", answer)

    def test_known_answer_stays_first_then_relevant_link(self):
        client = _Client("The stored admission rule says applicants need a 70% minimum.")
        result = answer_student_question(
            "What are the admission requirements for 8875BSN?",
            [],
            client=client,
        )
        self.assertEqual(result.get("error"), "verification_failed")
        self.assertFalse(result["orchestration"]["answer_released"])
        self.assertNotIn("70%", result["answer"])

    def test_insufficient_data_answer_has_helpful_next_step(self):
        client = _Client("I cannot verify your personal award eligibility from the available Asteris data.")
        result = answer_student_question("Which scholarships am I eligible for?", [], client=client)
        self.assertIn("Which program", result["answer"])
        self.assertIn("https://www.bcit.ca/financial-aid/", result["answer"])

    def test_irrelevant_academic_question_gets_no_random_resource(self):
        answer = append_institutional_resources("CIVL 2020 is a course.", "What are the prerequisites for CIVL 2020?")
        self.assertEqual(answer, "CIVL 2020 is a course.")

    def test_resource_append_is_capped(self):
        question = "International student admission tuition and financial aid application process"
        resources = find_institutional_resources(question, limit=99)
        self.assertLessEqual(len(resources), MAX_RESOURCE_LINKS)
        answer = append_institutional_resources("Here is the answer.", question)
        self.assertLessEqual(answer.count("https://"), MAX_RESOURCE_LINKS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
