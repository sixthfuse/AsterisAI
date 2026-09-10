"""Replay the founder's second browser transcript through internal and real HTTP paths."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any
from urllib.request import Request, urlopen
import uuid

from dotenv import load_dotenv

from advisor_v2 import AdvisorV2State, answer_advisor_v2_hybrid
from advisor_v2_sol import SolLanguageLayer


TRANSCRIPT = [
    "hello",
    "nursing programs?",
    "which of these programs can I apply to as an international student?",
    "I am a red seal certified, can I use that to apply for any programs at BCIT?",
    "do yo offer any engineering programs?",
    "are there any engineering courses overall at BCIT?",
    "can you reset your memory and think about engineering programs?",
    "civil engineering",
    "do you offer any structural, civil or any other engineering?",
    "do you offer mechanical engineering",
    "mechanical engineering bachelor degree",
    "do you offer any aviation courses?",
    "what about programs? I think I want to get into aviation. Do you offer any programs?",
    "aviation management and operations program?",
    "which is the man campus?",
    "which is the main BCIT campus?",
    "i know it has 5, but which one is the main one?",
    "phone number?",
    (
        "I have English 12 with 60 percent, I have Red Seal certification as an electrician, "
        "and I have Foundations of Math 11 with 55 percent, I have the associate certificate "
        "construction operations with 70 percent and I have an 11-month work experience, "
        "do I have the requirements for the construction management bachelor degree?"
    ),
    "construction management program",
    "degree",
    "degree",
    "bachelor",
]


def _row(index: int, message: str, result: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    observed = result.get("observability", {})
    runtime = observed.get("runtime", {})
    return {
        "turn": index,
        "message": message,
        "elapsed_ms": round(elapsed_ms, 2),
        "answer": result.get("answer"),
        "intent": observed.get("detected_intent"),
        "question_class": observed.get("question_class"),
        "decision_path": observed.get("final_response_path"),
        "capability_path": [item.get("capability") for item in result.get("retrieval", [])],
        "context": observed.get("context"),
        "entity_resolution": observed.get("entity_resolution"),
        "retrieval_trace": observed.get("retrieval"),
        "rule_evaluation_status": observed.get("rule_evaluation_status"),
        "interpretation": observed.get("interpretation"),
        "state_source": observed.get("state_source"),
        "build_fingerprint": runtime.get("build_fingerprint"),
        "request_id": runtime.get("request_id"),
        "session_id": runtime.get("session_id"),
        "runtime_provenance": runtime,
        "interpretation_status": (observed.get("interpretation") or {}).get("status"),
        "usage": result.get("usage"),
        "conversation_state": result.get("conversation_state"),
    }


def run_internal(live_sol: bool) -> dict[str, Any]:
    state = AdvisorV2State()
    layer = SolLanguageLayer() if live_sol else None
    rows = []
    for index, message in enumerate(TRANSCRIPT, 1):
        started = time.perf_counter()
        result = answer_advisor_v2_hybrid(message, conversation_state=state, language_layer=layer)
        elapsed_ms = (time.perf_counter() - started) * 1000
        state = AdvisorV2State.model_validate(result["conversation_state"])
        rows.append(_row(index, message, result, elapsed_ms))
    return {"path": "internal_live" if live_sol else "internal_fallback", "turns": rows}


def _get_json(url: str) -> dict[str, Any]:
    with urlopen(Request(url, headers={"Cache-Control": "no-store"}), timeout=30) as response:
        return json.loads(response.read())


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Cache-Control": "no-store", **headers},
        method="POST",
    )
    with urlopen(request, timeout=90) as response:
        return json.loads(response.read())


def run_http(base_url: str, browser_equivalent: bool) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    diagnostics = _get_json(base_url + "/advisor-v2/diagnostics")
    state = None
    session_id = "browser-parity-" + uuid.uuid4().hex
    rows = []
    for index, message in enumerate(TRANSCRIPT, 1):
        payload: dict[str, Any] = {"question": message}
        headers = {"X-Request-ID": f"parity-{index}-{uuid.uuid4().hex[:10]}"}
        if browser_equivalent:
            headers["X-Session-ID"] = session_id
        elif state is not None:
            payload["conversation_state"] = state
        started = time.perf_counter()
        result = _post_json(base_url + "/advisor-v2", payload, headers)
        elapsed_ms = (time.perf_counter() - started) * 1000
        state = result["conversation_state"]
        rows.append(_row(index, message, result, elapsed_ms))
    return {
        "path": "browser_equivalent_session" if browser_equivalent else "direct_http_client_state",
        "diagnostics": diagnostics,
        "turns": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("internal", "http", "browser"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--live-sol", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    load_dotenv()
    if args.mode == "internal":
        report = run_internal(args.live_sol)
    else:
        report = run_http(args.base_url, browser_equivalent=args.mode == "browser")
    rendered = json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
