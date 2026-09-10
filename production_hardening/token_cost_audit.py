"""Model-free token estimate from frozen Phase 3 transcripts.

This deliberately makes no API calls. Estimates use the conventional four
characters-per-token approximation and compare only replayed conversation text;
system instructions, tool schemas, evidence payloads, and outputs are unchanged.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_advisor import compact_history_for_model


TRANSCRIPTS = ROOT / "human_advisor_benchmark" / "runs" / "phase3_certification_sol_medium_20260908" / "transcripts"
CASES = {
    "simple_fact": ("FLOW-04", 1),
    "admissions": ("FLOW-27", 1),
    "international_eligibility": ("CAT-01-B", 1),
    "prerequisite": ("FLOW-03", 1),
    "comparison": ("FLOW-22", 3),
    "long_session_follow_up": ("LONG-01", 22),
}


def legacy_history(conversation):
    lines = []
    for message in conversation[-10:]:
        role = message.get("role")
        content = message.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            lines.append(f"{role.title()}: {content}")
    history = "\n".join(lines)
    return history[-4_000:] if len(history) > 4_000 else history


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def main():
    rows = []
    for label, (scenario_id, turn_number) in CASES.items():
        transcript = json.loads((TRANSCRIPTS / f"{scenario_id}.json").read_text(encoding="utf-8"))
        turn = transcript["turns"][turn_number - 1]
        conversation = turn["request"].get("conversation") or []
        before = estimate_tokens(legacy_history(conversation))
        after = estimate_tokens(compact_history_for_model(conversation))
        rows.append({
            "case": label,
            "scenario_id": scenario_id,
            "turn": turn["turn"],
            "question": turn["request"]["question"],
            "legacy_history_estimated_tokens": before,
            "hardened_history_estimated_tokens": after,
            "estimated_tokens_saved": before - after,
            "estimated_percent_saved": round((before - after) * 100 / before, 1) if before else 0.0,
        })
    print(json.dumps({
        "method": "frozen transcripts; ceil(text characters / 4); conversation replay only",
        "live_api_requests": 0,
        "live_api_tokens": 0,
        "live_api_cost_usd": 0,
        "cases": rows,
        "totals": {
            "legacy_history_estimated_tokens": sum(row["legacy_history_estimated_tokens"] for row in rows),
            "hardened_history_estimated_tokens": sum(row["hardened_history_estimated_tokens"] for row in rows),
            "estimated_tokens_saved": sum(row["estimated_tokens_saved"] for row in rows),
        },
    }, indent=2))


if __name__ == "__main__":
    main()
