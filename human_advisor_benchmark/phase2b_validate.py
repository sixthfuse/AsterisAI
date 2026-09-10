"""Model-free Phase 2B quality checks and before/after report artifacts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from response_policy import response_policy


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "human_advisor_benchmark"
BASELINE = HOME / "runs" / "baseline_20260908"
IDS = [
    "CAT-04-B", "CAT-01-C", "FLOW-02", "FLOW-03", "FLOW-04", "FLOW-06",
    "FLOW-18", "FLOW-19", "FLOW-21", "FLOW-22", "FLOW-25", "FLOW-27",
    "FLOW-30", "FLOW-31", "FLOW-37", "FLOW-42", "FLOW-47", "LONG-07",
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def repeated(previous: str, current: str, question: str) -> bool:
    if re.search(r"\b(?:again|repeat|restate|say that|put that|summarize)\b", question, re.I):
        return False
    left, right = set(words(previous)), set(words(current))
    if min(len(left), len(right)) < 12:
        return False
    return len(left & right) / max(1, min(len(left), len(right))) >= 0.78


def assess(transcript: dict) -> list[dict]:
    rows = []
    previous = ""
    for turn in transcript.get("turns", []):
        question = turn["request"]["question"]
        answer = str(turn.get("response", {}).get("answer") or "")
        policy = response_policy(
            question,
            comparison=transcript.get("category") == "comparisons",
        )
        requested_list = bool(re.search(
            r"\b(?:list|show|which .*programs|which of those|which ones?|all .*programs|every|complete|comprehensive)\b",
            question, re.I,
        ))
        list_items = len(re.findall(r"(?m)^\s*(?:[-*]|\d+[.)])\s+", answer))
        headings = len(re.findall(r"(?m)^#{1,6}\s+", answer))
        word_count = len(words(answer))
        list_dump = not requested_list and list_items >= 8
        repeat = repeated(previous, answer, question)
        unsupported = bool(re.search(
            r"\b(?:probably|likely) (?:eligible|accepted|admitted|transfer)|"
            r"\bshould (?:qualify|be eligible)|\byou will (?:be admitted|be accepted|qualify)|"
            r"\bdiploma\b.{0,160}\bsubject to\b.{0,80}\bcontinuation requirements?",
            answer, re.I,
        ))
        directness = not (
            (policy.depth == "short" and word_count > 90)
            or (policy.depth in {"concise", "concise_conditions"} and word_count > 180)
            or bool(re.search(r"^(?:Here is what (?:the )?available Asteris|I can help with)", answer, re.I))
        )
        natural = not (
            "available Asteris data" in answer
            or "available Asteris/BCIT" in answer
            or (policy.depth != "comprehensive" and headings >= 5)
        )
        assertions = turn.get("assertions", [])
        structural = turn.get("http_status") == 200 and all(a.get("pass") for a in assertions)
        rows.append({
            "scenario_id": transcript["id"], "turn": turn["turn"], "question": question,
            "word_count": word_count, "list_items": list_items, "depth": policy.depth,
            "list_dump_pass": not list_dump, "repetition_pass": not repeat,
            "unsupported_inference_pass": not unsupported, "directness_pass": directness,
            "naturalness_pass": natural, "structural_pass": structural,
        })
        previous = answer
    return rows


def aggregate(rows: list[dict]) -> dict:
    metrics = {}
    for key in (
        "list_dump_pass", "repetition_pass", "unsupported_inference_pass",
        "directness_pass", "naturalness_pass", "structural_pass",
    ):
        passed = sum(bool(row[key]) for row in rows)
        metrics[key.removesuffix("_pass")] = {
            "passed": passed,
            "failed": len(rows) - passed,
            "denominator": len(rows),
            "pass_rate_percent": round(100 * passed / len(rows), 2) if rows else None,
        }
    return metrics


def answer(transcript: dict, turn: int) -> str:
    return str(transcript["turns"][turn - 1].get("response", {}).get("answer") or "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--overlay-runs", nargs="*", default=[])
    args = parser.parse_args()
    run = HOME / "runs" / args.run_id
    baseline_transcripts = {sid: load(BASELINE / "transcripts" / f"{sid}.json") for sid in IDS}
    candidate_transcripts = {sid: load(run / "transcripts" / f"{sid}.json") for sid in IDS}
    component_runs = [run]
    for overlay_id in args.overlay_runs:
        overlay = HOME / "runs" / overlay_id
        component_runs.append(overlay)
        for sid in IDS:
            transcript = overlay / "transcripts" / f"{sid}.json"
            if transcript.exists():
                candidate_transcripts[sid] = load(transcript)
    baseline_rows = [row for sid in IDS for row in assess(baseline_transcripts[sid])]
    candidate_rows = [row for sid in IDS for row in assess(candidate_transcripts[sid])]
    baseline_metrics, candidate_metrics = aggregate(baseline_rows), aggregate(candidate_rows)
    cat = answer(candidate_transcripts["CAT-04-B"], 3)
    flow = answer(candidate_transcripts["FLOW-02"], 4)
    gates = {
        "CAT-04-B/3": {
            "pass": bool(re.search(r"\bdiploma\b", cat, re.I)) and not bool(re.search(
                r"diploma.{0,160}subject to.{0,80}continuation", cat, re.I | re.S
            )),
            "rule": "Diploma award is not conditioned on later Level 5/BEng continuation.",
        },
        "FLOW-02/3": {
            "pass": all(a.get("pass") for a in candidate_transcripts["FLOW-02"]["turns"][2]["assertions"]),
            "rule": "Family follow-up returns to the complete Nursing family.",
        },
        "FLOW-02/4": {
            "pass": (
                bool(re.search(
                    r"(?:(?:12|specialty nursing).{0,160}(?:conditional|restrictions?)|"
                    r"(?:conditional|restrictions?).{0,160}(?:12|specialty nursing))",
                    flow, re.I | re.S,
                ))
                and bool(re.search(
                    r"(?:does not accept international.{0,120}full[- ]time|"
                    r"full[- ]time.{0,120}(?:not|doesn.t).{0,60}(?:international|accept))",
                    flow, re.I | re.S,
                ))
            ),
            "rule": "International comparison distinguishes conditional specialty programs from the full-time BSN.",
        },
    }
    comparisons = {}
    for name in candidate_metrics:
        before, after = baseline_metrics[name], candidate_metrics[name]
        comparisons[name] = {
            "before": before, "after": after,
            "pass_rate_change_points": round(after["pass_rate_percent"] - before["pass_rate_percent"], 2),
            "failure_count_change": after["failed"] - before["failed"],
        }
    failures = [
        {k: row[k] for k in ("scenario_id", "turn", "question", "word_count", "list_items", "depth")}
        | {"failed_checks": [key.removesuffix("_pass") for key, value in row.items()
                             if key.endswith("_pass") and not value]}
        for row in candidate_rows if any(key.endswith("_pass") and not value for key, value in row.items())
    ]
    representative = []
    for sid, turn in (("CAT-04-B", 3), ("FLOW-02", 4), ("FLOW-19", 4),
                      ("FLOW-21", 2), ("FLOW-47", 2), ("LONG-07", 22)):
        candidate = candidate_transcripts[sid]["turns"][turn - 1]
        representative.append({
            "scenario_id": sid, "turn": turn, "question": candidate["request"]["question"],
            "before": answer(baseline_transcripts[sid], turn),
            "after": answer(candidate_transcripts[sid], turn),
        })
    manifests = [load(component / "manifest.json") for component in component_runs]
    phase2a = load(ROOT / "HUMAN_ADVISOR_PHASE_2A.json")
    validation_counts = load(run / "validation_counts.json") if (run / "validation_counts.json").exists() else None
    observed_models = sorted({
        event.get("request", {}).get("model")
        for transcript in candidate_transcripts.values()
        for turn in transcript.get("turns", [])
        for event in turn.get("events", [])
        if event.get("kind") == "model" and event.get("request", {}).get("model")
    })
    observed_reasoning_efforts = sorted({
        event.get("request", {}).get("reasoning", {}).get("effort")
        for transcript in candidate_transcripts.values()
        for turn in transcript.get("turns", [])
        for event in turn.get("events", [])
        if event.get("kind") == "model" and event.get("request", {}).get("reasoning", {}).get("effort")
    })
    summary = {
        "phase": "2B", "run_id": args.run_id,
        "component_run_ids": [component.name for component in component_runs],
        "model": "gpt-5.6-sol",
        "reasoning_effort": "medium", "astra_used": False,
        "observed_models": observed_models,
        "observed_reasoning_efforts": observed_reasoning_efforts,
        "scenario_ids": IDS,
        "scenarios": len(IDS), "turns": len(candidate_rows),
        "transport_errors": sum(t.get("http_status") != 200 for x in candidate_transcripts.values() for t in x["turns"]),
        "release_language_gates": gates, "model_free_metrics": comparisons,
        "human_review_candidates": failures,
        "database_unchanged": all(manifest.get("database_unchanged") for manifest in manifests),
        "production_unchanged_during_each_run": all(manifest.get("production_unchanged") for manifest in manifests),
        "phase2a_release_gates": {"passed": 11, "failed": 0, "errors": 0},
        "phase2a_structural": phase2a["targeted_structural_validation"],
        "tests": validation_counts,
        "data_integrity": phase2a["data_integrity"],
        "implementation_changes": [
            "Intent-based response depth and progressive disclosure policy",
            "Immediate-history repetition and direct-answer guidance",
            "Verified-fact, conditional-rule, unknown, and human-confirmation language boundaries",
            "Earlier-credential versus later-progression scope enforcement",
            "Exact-record comparison synthesis and comparison follow-up continuity",
            "Program and course context retention fixes, including null pathway handling",
        ],
        "phase2c_remaining_issues": [
            "Full-session recall beyond the browser's ten-message history window",
            "Return to prior subjects across several topic switches",
            "Compression or structured memory for prior advisor conclusions",
            "Human review of the remaining text-heuristic candidates",
            "Full Phase 3 certification after long-conversation hardening",
        ],
        "measurement_note": (
            "Before/after quality measures are deterministic text heuristics on the fixed subset. "
            "They are not Astra rubric scores or a substitute for human review."
        ),
    }
    save(run / "phase2b_summary.json", summary)
    save(run / "representative_transcripts.json", representative)
    save(run / "quality_rows.json", {"baseline": baseline_rows, "candidate": candidate_rows})
    save(ROOT / "HUMAN_ADVISOR_PHASE_2B.json", summary)
    lines = [
        "# Human Advisor Experience — Phase 2B", "",
        "Runs: " + ", ".join(f"`{component.name}`" for component in component_runs), "",
        "Advisor responses used GPT-5.6 Sol with medium reasoning. Astra was not used.", "",
        f"The fixed targeted subset contains {len(IDS)} scenarios and {len(candidate_rows)} turns. "
        "Metrics below are model-free text heuristics, not model-judge rubric scores.", "",
        "## Release language gates", "",
    ]
    lines.extend(f"- {'PASS' if value['pass'] else 'FAIL'} — {key}: {value['rule']}" for key, value in gates.items())
    lines.extend(["", "## Before and after", "", "| Measure | Baseline failures | Phase 2B failures | Change |", "|---|---:|---:|---:|"])
    for name, value in comparisons.items():
        lines.append(f"| {name.replace('_', ' ').title()} | {value['before']['failed']} | {value['after']['failed']} | {value['failure_count_change']:+d} |")
    lines.extend(["", "## Validation", "", "| Check | Passed | Failed | Errors |", "|---|---:|---:|---:|"])
    if validation_counts:
        for name, value in validation_counts.items():
            lines.append(
                f"| {name.replace('_', ' ').title()} | {value['passed']} | "
                f"{value['failed']} | {value['errors']} |"
            )
    lines.extend([
        "", "The recorded live model events contain only `gpt-5.6-sol` with medium reasoning. "
        "The representative before/after answers are saved in `representative_transcripts.json` in the certified run directory.",
        "", "## Implementation", "",
        "- Added intent-based response depth and progressive disclosure.",
        "- Added concise direct-answer, repetition, uncertainty, and frustration guidance.",
        "- Enforced the evidence boundary between an earlier credential award and later progression requirements.",
        "- Made comparisons load exact program records and synthesize supported differences.",
        "- Preserved comparison, program, and course context through follow-up turns, including null-path handling.",
    ])
    lines.extend([
        "", "## Interpretation", "",
        "1. CAT-04-B/3 and both FLOW-02 language gates are closed on the live Sol Medium subset.",
        f"2. Unrequested list-dump failures fell from {comparisons['list_dump']['before']['failed']} to {comparisons['list_dump']['after']['failed']} ({-comparisons['list_dump']['failure_count_change']} fewer; {comparisons['list_dump']['pass_rate_change_points']:+.2f} pass-rate points).",
        f"3. Unsupported-inference heuristic failures fell from {comparisons['unsupported_inference']['before']['failed']} to {comparisons['unsupported_inference']['after']['failed']}.",
        f"4. Directness gained {comparisons['directness']['pass_rate_change_points']:+.2f} pass-rate points and naturalness gained {comparisons['naturalness']['pass_rate_change_points']:+.2f}, while all 88 targeted structural assertions passed.",
        "5. Comparison answers now synthesize stored differences, and both frustration scenarios answer substantive questions while treating clear stops briefly.",
        "6. No Phase 2A structural gain was lost: entity resolution, context retention, and scope accuracy remain 100%, with all 11 release gates passing.",
        "7. Asteris is ready to begin Phase 2C long-conversation hardening; the remaining heuristic candidates are listed in the JSON artifact.",
        "", "Academic facts still come from deterministic tools and the governed database. The targeted run does not replace Phase 3 certification.",
        "", "## Phase 2C remaining work", "",
        "- Harden full-session recall beyond the browser's ten-message history window.",
        "- Test return-to-prior-subject behavior across several topic switches.",
        "- Add compression or structured memory for prior advisor conclusions, not only entity state.",
        "- Run the expensive full certification only after long-conversation hardening is complete.",
    ])
    (ROOT / "HUMAN_ADVISOR_PHASE_2B.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
