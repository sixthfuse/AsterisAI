"""Real-route integration and cross-turn invariants for the isolated v3 advisor."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

import main


ELIGIBILITY_QUESTION = (
    "I have English 12 with 60 percent, I have Red Seal certification as an electrician, "
    "and I have Foundations of Math 11 with 55 percent, I have the associate certificate "
    "construction operations with 70 percent and I have an 11-month work experience, do I "
    "have the requirements for the construction management bachelor degree?"
)


class AdvisorV3RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_layer = main.advisor_v3_language_layer
        main.advisor_v3_language_layer = None
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        main.advisor_v3_language_layer = cls.original_layer

    def setUp(self):
        self.session = f"v3-test-{self._testMethodName}"
        self.headers = {"X-Session-ID": self.session, "X-Request-ID": self.session}

    def ask(self, question: str) -> dict:
        response = self.client.post("/advisor-v3", json={"question": question}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["verification"]["status"], "grounded", data)
        return data

    def test_primary_acceptance_sequence_uses_one_pipeline(self):
        computing = self.ask("computing")
        first_set = computing["conversation_state"]["recent_result_sets"][0]
        self.assertEqual(first_set["total"], 44)
        self.assertEqual(len(first_set["ids"]), 44)
        self.assertEqual(computing["developer_trace"]["operation_graph"][0]["kind"], "catalog_filter")

        assent = self.ask("sure")
        self.assertEqual(assent["plan"]["speech_act"], "confirmation")
        self.assertEqual(assent["developer_trace"]["operation_graph"][0]["kind"], "reuse_result_set")
        self.assertNotIn("couldn't find", assent["answer"])
        self.assertEqual(assent["answer"].count("\n• "), 44)

        explicit = self.ask("list all 44 programs")
        self.assertEqual(explicit["developer_trace"]["operation_graph"][0]["kind"], "reuse_result_set")
        self.assertEqual(explicit["answer"].count("\n• "), 44)

        eligibility = self.ask(ELIGIBILITY_QUESTION)
        self.assertEqual(eligibility["developer_trace"]["evaluator_result"]["status"], "unmet")
        self.assertEqual(eligibility["conversation_state"]["active_entities"]["program_id"], "8800BTECH")

        masters = self.ask("do you have any master's degrees?")
        master_set = masters["conversation_state"]["recent_result_sets"][0]
        self.assertEqual(master_set["total"], 5)
        self.assertTrue(all("master" in row["credential"].lower() for row in master_set["rows"]))
        self.assertNotEqual(masters["conversation_state"]["current_task_thread"]["category"], "Construction Management")

        correction = self.ask("no, those are not master's degrees")
        self.assertEqual(correction["plan"]["speech_act"], "correction")
        self.assertEqual(correction["conversation_state"]["recent_result_sets"][0]["total"], 5)

        computing_master = self.ask("computing master's")
        cm_set = computing_master["conversation_state"]["recent_result_sets"][0]
        self.assertEqual(cm_set["ids"], ["M600MSC"])

        exact = self.ask("m600msc")
        self.assertEqual(exact["conversation_state"]["active_entities"]["program_id"], "M600MSC")
        self.assertEqual(exact["developer_trace"]["referent_resolution"]["source"], "exact_id")

        social = self.ask("oh wow you found it!")
        self.assertEqual(social["plan"]["task"], "social_ack")
        self.assertEqual(social["conversation_state"]["active_entities"]["program_id"], "M600MSC")
        self.assertEqual(social["conversation_state"]["recent_result_sets"][0]["ids"], ["M600MSC"])

        campuses = self.ask("how many campuses are there?")
        self.assertEqual(campuses["developer_trace"]["evaluator_result"]["count"], 5)

        nursing = self.ask("which nursing programs are not available to international students?")
        self.assertEqual(nursing["conversation_state"]["recent_result_sets"][0]["ids"], ["8875BSN"])
        self.assertIn("Not available to international students", nursing["answer"])

    def test_referents_exact_names_and_credential_clarification(self):
        ambiguous = self.ask("Construction Management")
        self.assertEqual(ambiguous["operations"][-1]["status"], "ambiguous")
        selected = self.ask("the bachelor's degree")
        self.assertEqual(selected["conversation_state"]["active_entities"]["program_id"], "8800BTECH")

        pasted = self.ask("Nursing, Bachelor of Science in Nursing, Full-time")
        self.assertEqual(pasted["conversation_state"]["active_entities"]["program_id"], "8875BSN")
        follow_up = self.ask("is this program available to international students?")
        self.assertIn("Not available", follow_up["answer"])

    def test_broad_discovery_and_red_seal_do_not_bypass_compiler(self):
        engineering = self.ask("engineering programs")
        self.assertGreater(engineering["conversation_state"]["recent_result_sets"][0]["total"], 1)
        self.assertEqual(engineering["developer_trace"]["operation_graph"][0]["kind"], "catalog_filter")

        aviation = self.ask("aviation programs")
        self.assertGreater(aviation["conversation_state"]["recent_result_sets"][0]["total"], 1)

        red_seal = self.ask("what programs have Red Seal admission pathways?")
        self.assertEqual(red_seal["developer_trace"]["operation_graph"][0]["kind"], "red_seal_programs")
        self.assertGreater(red_seal["conversation_state"]["recent_result_sets"][0]["total"], 0)

    def test_experimental_ui_and_diagnostics_are_real_routes(self):
        page = self.client.get("/app-v3")
        self.assertEqual(page.status_code, 200)
        self.assertIn("/static/advisor-v3.js", page.text)
        diagnostics = self.client.get("/advisor-v3/diagnostics").json()
        self.assertEqual(diagnostics["advisor_v3_post_route_count"], 1)
        self.assertEqual(diagnostics["sol_model"], "gpt-5.6-sol")
        self.assertEqual(diagnostics["sol_reasoning_effort"], "medium")


if __name__ == "__main__":
    unittest.main()
