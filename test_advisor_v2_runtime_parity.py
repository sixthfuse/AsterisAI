"""Real-process route/session parity tests for the experimental advisor."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import URLError
from urllib.request import Request, urlopen

from advisor_v2_runtime_parity_audit import TRANSCRIPT


ROOT = Path(__file__).resolve().parent


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _json(url: str, *, payload=None, headers=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url, data=body, method="GET" if body is None else "POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read()), dict(response.headers)


class AdvisorV2RuntimeParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        environment = os.environ.copy()
        environment["ASTERIS_ADVISOR_V2_SOL"] = "0"
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(cls.port)],
            cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with urlopen(cls.base + "/health/live", timeout=1):
                    break
            except URLError:
                if cls.process.poll() is not None:
                    raise RuntimeError("isolated uvicorn process exited during startup")
                time.sleep(0.1)
        else:
            raise RuntimeError("isolated uvicorn process did not become ready")

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()

    def test_diagnostics_prove_single_semantic_v2_route_and_loaded_files(self):
        data, _ = _json(self.base + "/advisor-v2/diagnostics")
        self.assertEqual(data["advisor_v2_post_route_count"], 1)
        self.assertEqual(data["route_id"], "advisor-v2.conversational-core.v2")
        self.assertEqual(data["router_mode"], "task_plan_context_first_grounded_synthesis")
        self.assertFalse(data["sol_enabled"])
        self.assertEqual(Path(data["module_paths"]["advisor_v2"]), ROOT / "advisor_v2.py")
        self.assertEqual(Path(data["module_paths"]["main"]), ROOT / "main.py")
        self.assertEqual(len(data["build_fingerprint"]), 16)

    def test_browser_payload_uses_server_session_and_semantic_capability(self):
        session = "parity-browser-session"
        result, headers = _json(
            self.base + "/advisor-v2",
            payload={"question": "do yo offer any engineering programs?"},
            headers={"X-Session-ID": session, "X-Request-ID": "parity-browser-request"},
        )
        runtime = result["observability"]["runtime"]
        response_request_id = next(value for key, value in headers.items() if key.lower() == "x-request-id")
        self.assertEqual(response_request_id, "parity-browser-request")
        self.assertEqual(result["observability"]["final_response_path"], "taxonomy_program_discovery")
        self.assertIn("list_programs_by_area", runtime["capability_path"])
        self.assertEqual(runtime["request_id"], "parity-browser-request")
        self.assertTrue(result["observability"]["server_session_enabled"])

        follow_up, _ = _json(
            self.base + "/advisor-v2", payload={"question": "mechanical engineering"},
            headers={"X-Session-ID": session, "X-Request-ID": "parity-browser-followup"},
        )
        self.assertEqual(follow_up["observability"]["state_source"], "server_session")
        self.assertNotIn("saved topic applies", follow_up["answer"])

    def test_app_v2_is_uncached_and_loads_only_v2_client(self):
        with urlopen(self.base + "/app-v2", timeout=10) as response:
            html = response.read().decode("utf-8")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertTrue(response.headers["X-Asteris-V2-Build"])
        self.assertIn("/static/advisor-v2.js?v=runtime-parity-20260910", html)
        self.assertNotIn("/static/app.js", html)
        javascript = (ROOT / "static" / "advisor-v2.js").read_text(encoding="utf-8")
        self.assertIn('fetch("/advisor-v2"', javascript)
        self.assertNotIn('fetch("/advisor"', javascript)

    def test_complete_founder_transcript_over_real_route_and_server_session(self):
        session = "complete-founder-parity"
        results = []
        for index, message in enumerate(TRANSCRIPT, 1):
            result, _ = _json(
                self.base + "/advisor-v2", payload={"question": message},
                headers={"X-Session-ID": session, "X-Request-ID": f"founder-{index}"},
            )
            results.append(result)
            self.assertEqual(result["conversation_state"]["turn_index"], index)
            self.assertEqual(result["observability"]["runtime"]["request_id"], f"founder-{index}")

        self.assertIn("nursing", results[1]["answer"].lower())
        self.assertEqual(results[2]["observability"]["final_response_path"], "international_program_availability")
        self.assertEqual(results[4]["observability"]["final_response_path"], "taxonomy_program_discovery")
        self.assertEqual(results[5]["observability"]["final_response_path"], "course_discovery")
        self.assertNotIn("0 matching programs", results[6]["answer"])
        self.assertEqual(results[8]["observability"]["final_response_path"], "taxonomy_program_discovery")
        self.assertIn("Civil Engineering", results[8]["answer"])
        self.assertNotIn("saved topic applies", results[9]["answer"])
        self.assertEqual(results[11]["observability"]["final_response_path"], "course_discovery")
        self.assertNotIn("0 matching programs", results[12]["answer"])
        self.assertIn("Aircraft Maintenance Engineer", results[12]["answer"])
        self.assertIn("Burnaby Campus", results[15]["answer"])
        self.assertIn("Burnaby Campus", results[16]["answer"])
        self.assertIn("604-434-5734", results[17]["answer"])
        self.assertEqual(results[18]["observability"]["final_response_path"], "deterministic_rule_evaluation")
        self.assertIn("not met: One accepted math option at 60%; you reported 55.0", results[18]["answer"])
        self.assertNotIn("find_red_seal_programs", [row["capability"] for row in results[18]["retrieval"]])
        self.assertEqual(results[20]["observability"]["context"]["action"], "resolved_credential")
        self.assertEqual(results[20]["resolved_program"], "8800BTECH")
        self.assertEqual(results[21]["resolved_program"], "8800BTECH")


if __name__ == "__main__":
    unittest.main(verbosity=2)
