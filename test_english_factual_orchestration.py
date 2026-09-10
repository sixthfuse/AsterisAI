"""Large, model-free certification for English factual orchestration."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_advisor import find_programs, resolve_academic_context
from database import get_connection
from factual_orchestration import AccuracyLane, understand_current_turn
from main import app


class EnglishFactualOrchestrationTests(unittest.TestCase):
    def test_lane_policy_is_accuracy_driven(self):
        cases = {
            "How many campuses does BCIT have?": ("campus", AccuracyLane.FAST),
            "Tell me about the Technology Management program.": ("program", AccuracyLane.NORMAL),
            "What are the prerequisites for COMM 1100?": ("course", AccuracyLane.NORMAL),
            "Can I apply as an international student?": ("program", AccuracyLane.DEEP),
            "Compare the Civil Engineering programs.": ("program", AccuracyLane.DEEP),
        }
        for question, expected in cases.items():
            turn = understand_current_turn(question)
            self.assertEqual((turn.family, turn.lane), expected)

    def test_every_active_program_name_resolves_to_its_canonical_id(self):
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT program_id, program_name FROM programs "
                "WHERE status='Active' ORDER BY program_id"
            )
            programs = cursor.fetchall()
        self.assertGreaterEqual(len(programs), 370)
        failures = []
        for program_id, program_name in programs:
            rows = find_programs(program_name)
            ids = {row["program_id"] for row in rows}
            if program_id not in ids:
                failures.append((program_id, program_name, sorted(ids)[:5]))
        self.assertEqual(failures, [])

    def test_current_turn_outranks_campus_state_at_real_endpoint(self):
        with patch("ai_advisor.OpenAI", side_effect=AssertionError("model called")):
            with TestClient(app) as client:
                first = client.post("/advisor", json={
                    "question": "How many campuses does BCIT have?",
                }).json()
                follow = client.post("/advisor", json={
                    "question": "How many languages can you speak?",
                    "conversation": [
                        {"role": "user", "content": "How many campuses does BCIT have?"},
                        {"role": "assistant", "content": first["answer"]},
                    ],
                    "conversation_state": first["conversation_state"],
                })
        self.assertEqual(follow.status_code, 200, follow.text)
        data = follow.json()
        self.assertIn("certified for English", data["answer"])
        self.assertNotIn("campus", data["answer"].lower())
        self.assertEqual(data["tools_used"], [])
        self.assertEqual(data["conversation_state"]["scope"], "none")
        self.assertTrue(data["orchestration"]["verify"]["passed"])
        self.assertEqual(data["orchestration"]["understand"]["family"], "capability")

    def test_real_endpoint_keeps_valid_campus_follow_up(self):
        with patch("ai_advisor.OpenAI", side_effect=AssertionError("model called")):
            with TestClient(app) as client:
                first = client.post("/advisor", json={
                    "question": "How many campuses does BCIT have?",
                }).json()
                follow = client.post("/advisor", json={
                    "question": "What are their phone numbers?",
                    "conversation_state": first["conversation_state"],
                    "conversation": [
                        {"role": "user", "content": "How many campuses does BCIT have?"},
                        {"role": "assistant", "content": first["answer"]},
                    ],
                })
        self.assertEqual(follow.status_code, 200, follow.text)
        data = follow.json()
        self.assertEqual(data["tools_used"], ["campus_information"])
        self.assertTrue(data["orchestration"]["verify"]["passed"])

    def test_unrelated_unknown_turn_cannot_reuse_campus_evidence(self):
        with patch("ai_advisor.OpenAI", side_effect=AssertionError("model called")):
            with TestClient(app) as client:
                first = client.post("/advisor", json={
                    "question": "How many campuses does BCIT have?",
                }).json()
                follow = client.post("/advisor", json={
                    "question": "Tell me a joke.",
                    "conversation_state": first["conversation_state"],
                })
        self.assertEqual(follow.status_code, 200, follow.text)
        data = follow.json()
        self.assertEqual(data["error"], "verification_failed")
        self.assertNotIn("campuses", data["answer"].lower())
        self.assertEqual(data["conversation_state"]["scope"], "none")
        self.assertFalse(data["orchestration"]["answer_released"])

    def test_off_topic_turn_resets_active_program_subject(self):
        state = resolve_academic_context(
            "Tell me about Technology Management.", [], None, None
        )["conversation_state"]
        with patch("ai_advisor.OpenAI", side_effect=AssertionError("model called")):
            with TestClient(app) as client:
                follow = client.post("/advisor", json={
                    "question": "What is the weather tomorrow?",
                    "conversation_state": state,
                })
        self.assertEqual(follow.status_code, 200, follow.text)
        data = follow.json()
        self.assertIn("academic", data["answer"].lower())
        self.assertEqual(data["conversation_state"]["scope"], "none")
        self.assertTrue(data["orchestration"]["verify"]["passed"])

    def test_model_free_factual_matrix_exercises_real_endpoint(self):
        questions = [
            "How many programs does BCIT have?",
            "How many courses does BCIT have?",
            "How many programs and courses does BCIT have?",
            "How many campuses does BCIT have?",
            "What are the campus names?",
            "What are the campus addresses?",
            "What is BCIT's phone number?",
            "Do you offer any technology programs?",
            "Do you offer any engineering programs?",
            "Do you offer any nursing programs?",
            "Do you offer any biotechnology programs?",
            "Can a Red Seal count toward admission requirements?",
            "I have a Red Seal. Can I apply to any programs?",
            "How many languages can you speak?",
            "What can you do?",
            "Who are you?",
        ]
        with patch("ai_advisor.OpenAI", side_effect=AssertionError("model called")):
            with TestClient(app) as client:
                responses = [client.post("/advisor", json={"question": q}) for q in questions]
        for question, response in zip(questions, responses):
            self.assertEqual(response.status_code, 200, (question, response.text))
            data = response.json()
            self.assertTrue(data["orchestration"]["verify"]["passed"], (question, data))
            self.assertNotRegex(data["answer"], r"functions?\.|\"query\"\s*:")


if __name__ == "__main__":
    unittest.main()
