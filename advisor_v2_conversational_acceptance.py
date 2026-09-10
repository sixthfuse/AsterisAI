"""Compressed real-route acceptance replay for the conversational core."""
from __future__ import annotations

import json
import sys
import time
from urllib.request import Request, urlopen


SEQUENCE = [
    "Do you offer any engineering programs?",
    "As an international student, which nursing programs can I apply to?",
    "Which one is the program that I can't apply to as an international student?",
    "8875bsn",
    "Can I apply to this program as an international student?",
    "Do you offer any computing programs?",
    "More about the master's degree",
    "Applied Computing — Master of Science / Master's Degree",
    (
        "I have English 12 with 73 percent, an electrician Red Seal, Foundations of Math 11 "
        "with 55 percent, the Construction Operations associate certificate with 70 percent, "
        "and 11 months of work experience. Do I meet the requirements for the Construction "
        "Management bachelor degree?"
    ),
]


def request_json(url: str, payload: dict | None = None, headers: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, method="GET" if data is None else "POST", headers={
        "Content-Type": "application/json", **(headers or {}),
    })
    with urlopen(request, timeout=90) as response:
        return json.loads(response.read())


def run(base_url: str) -> dict:
    diagnostics = request_json(base_url + "/advisor-v2/diagnostics")
    rows = []
    totals = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0}
    session_id = "conversational-core-live"
    for index, message in enumerate(SEQUENCE, 1):
        started = time.perf_counter()
        result = request_json(
            base_url + "/advisor-v2", {"question": message},
            {"X-Session-ID": session_id, "X-Request-ID": f"core-live-{index}"},
        )
        usage = result.get("usage") or {}
        for key in totals:
            totals[key] += int(usage.get(key, 0) or 0)
        trace = result["observability"]
        rows.append({
            "turn": index, "message": message,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "answer": result["answer"], "usage": usage,
            "operation": trace["task_plan"]["operation"],
            "answer_shape": trace["answer_shape_decision"],
            "referent_source": trace["referent_resolution"]["source"],
            "response_path": trace["final_response_path"],
            "response_source": trace["final_response_source"],
            "grounding": trace["grounding_validation"],
            "capabilities": [item["capability"] for item in result["retrieval"]],
            "resolved_program": result.get("resolved_program"),
            "runtime_build": trace["runtime"]["build_fingerprint"],
        })
    checks = {
        "single_runtime_build": len({row["runtime_build"] for row in rows}) == 1,
        "all_grounded": all(row["grounding"]["status"] in {"passed", "legacy_exact_fact_renderer"} for row in rows),
        "no_synthesis_fallback": all(row["response_source"] != "deterministic_phase2" for row in rows),
        "broad_engineering_grouped": len(rows[0]["answer"].splitlines()) <= 9 and rows[0]["answer_shape"] == "grouped_summary",
        "single_unavailable_selected": rows[2]["resolved_program"] == "8875BSN" and "Critical Care" not in rows[2]["answer"],
        "this_program_resolved": rows[4]["referent_source"] == "active_program_id" and rows[4]["response_path"] == "single_program_international_availability",
        "masters_resolved": rows[6]["resolved_program"] == "M600MSC",
        "pasted_name_resolved": rows[7]["resolved_program"] == "M600MSC",
        "eligibility_deterministic": rows[8]["response_path"] == "deterministic_rule_evaluation" and "evaluate_admission" in rows[8]["capabilities"],
    }
    return {"diagnostics": diagnostics, "totals": totals, "checks": checks, "turns": rows}


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
    report = run(base.rstrip("/"))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if all(report["checks"].values()) else 1)
