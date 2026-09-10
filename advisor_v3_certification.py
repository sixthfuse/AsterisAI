"""Small browser-equivalent HTTP certification replay for advisor v3."""
from __future__ import annotations

import json
import sys
from urllib.request import Request, urlopen


BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
QUESTIONS = [
    "computing",
    "sure",
    "list all 44 programs",
    "I have English 12 with 60 percent, I have Red Seal certification as an electrician, and I have Foundations of Math 11 with 55 percent, I have the associate certificate construction operations with 70 percent and I have an 11-month work experience, do I have the requirements for the construction management bachelor degree?",
    "do you have any master's degrees?",
    "no, those are not master's degrees",
    "computing master's",
    "m600msc",
    "oh wow you found it!",
    "how many campuses are there?",
    "which nursing programs are not available to international students?",
]


def get(path: str) -> tuple[int, str, dict[str, str]]:
    with urlopen(Request(BASE + path, headers={"Cache-Control": "no-store"}), timeout=30) as response:
        return response.status, response.read().decode(), dict(response.headers)


def post(question: str, session: str) -> dict:
    payload = json.dumps({"question": question}).encode()
    request = Request(BASE + "/advisor-v3", data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "X-Session-ID": session,
        "X-Request-ID": f"cert-v3-{QUESTIONS.index(question) + 1}",
        "Cache-Control": "no-store",
    })
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def main() -> None:
    app_status, app_body, app_headers = get("/app-v3")
    js_status, js_body, _ = get("/static/advisor-v3.js")
    diag_status, diag_body, _ = get("/advisor-v3/diagnostics")
    turns = []
    totals = {"calls": 0, "calls_attempted": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0}
    for index, question in enumerate(QUESTIONS, 1):
        result = post(question, "browser-equivalent-v3-live")
        usage = result["usage"]
        for key in totals:
            totals[key] += int(usage.get(key, 0))
        turns.append({
            "turn": index,
            "question": question,
            "answer": result["answer"],
            "speech_act": result["plan"]["speech_act"],
            "task": result["plan"]["task"],
            "operation_kinds": [node["kind"] for node in result["developer_trace"]["operation_graph"]],
            "evidence_count": result["developer_trace"]["evidence_count"],
            "verification": result["verification"],
            "usage": usage,
            "fallback_reason": result["developer_trace"]["fallback_reason"],
            "active_program_id": result["conversation_state"]["active_entities"]["program_id"],
            "latest_result_total": (result["conversation_state"]["recent_result_sets"][0]["total"]
                                    if result["conversation_state"]["recent_result_sets"] else None),
        })
    print(json.dumps({
        "transport": {
            "base_url": BASE,
            "app_v3_status": app_status,
            "app_v3_references_v3_js": "/static/advisor-v3.js" in app_body,
            "app_v3_cache_control": app_headers.get("Cache-Control"),
            "js_status": js_status,
            "js_posts_advisor_v3": 'fetch("/advisor-v3"' in js_body,
            "diagnostics_status": diag_status,
            "diagnostics": json.loads(diag_body),
        },
        "turns": turns,
        "usage_totals": totals,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
