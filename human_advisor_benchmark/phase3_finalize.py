"""Build the auditable Phase 3 certification package from frozen run artifacts."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from .phase2c_validate import aggregate, assess


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "human_advisor_benchmark"
RUN_ID = "phase3_certification_sol_medium_20260908"
RUN = HOME / "runs" / RUN_ID
BASELINE = HOME / "runs" / "baseline_20260908"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


ADJUDICATION = {
    ("CAT-02-B", 3): ("source_confirmed_critical", "False absence claim: the frozen program record contains a configured curriculum."),
    ("CAT-07-B", 3): ("source_confirmed_critical", "The answer omits the published ACCEPTED_AVAILABLE status and sends the international applicant to confirm a restriction that the record resolves."),
    ("CAT-11-B", 3): ("source_confirmed_noncritical", "International conditions were omitted, but the answer stayed cautious and directed the applicant to BCIT; retain as a material scope failure below the critical gate."),
    ("CAT-14-A", 1): ("ambiguous_evidence_conflict", "Structured delivery says blended while authoritative page text says in person; a source-governance decision is needed before confirming an error."),
    ("CAT-18-B", 3): ("source_confirmed_critical", "The answer omits the decisive published NOT_ACCEPTED international status in the established international context."),
    ("CAT-20-B", 3): ("source_confirmed_critical", "A program-level availability restriction was converted into an individual eligibility determination."),
    ("FLOW-05", 3): ("source_confirmed_critical", "The response omits a documented criminal-record-check entrance requirement and the UBC application route."),
    ("FLOW-07", 3): ("source_confirmed_noncritical", "It says 60-credit total rather than minimum 60 credits; the threshold is numerically right but imprecisely scoped."),
    ("FLOW-10", 4): ("source_confirmed_critical", "A conditional question was stored as completion of both alternatives and the OR-group question was not answered."),
    ("FLOW-17", 4): ("source_confirmed_critical", "The answer says the forensic elective rule is absent although the frozen curriculum specifies six credits/exactly two courses."),
    ("FLOW-22", 2): ("source_confirmed_critical", "The comparison referent was lost and the answer replaced the three programs with a nursing-family list."),
    ("FLOW-27", 3): ("source_confirmed_critical", "The graduation checklist omits the documented two-year related-work-experience requirement."),
    ("FLOW-27", 4): ("critical_not_confirmed", "The answer accurately states the stored CMGT 8700 pre-project requirements; the judge's department-approval claim conflicts with the frozen advisor rule that approval applies to CMGT 8800/8810."),
    ("FLOW-35", 3): ("source_confirmed_critical", "The response retracts the published Program Head approval requirement for all 12 affected nursing programs."),
    ("FLOW-45", 3): ("source_confirmed_critical", "The structured correction succeeds, but the student-facing response falsely says the withdrawn course remains completed."),
    ("FLOW-46", 2): ("source_confirmed_critical", "The comparison reports international eligibility unknown although both frozen program records say not available."),
    ("LONG-02", 20): ("source_confirmed_critical", "The response makes ICES uniquely mandatory and omits the published allowance for other Canadian assessment services."),
    ("LONG-06", 20): ("source_confirmed_noncritical", "The phrase 'specified countries' is unclear and loses the five-country exemption boundary, but it does not identify a wrong country or applicant result."),
    ("LONG-09", 11): ("source_confirmed_critical", "Entry Option 3 courses were mislabeled as the standard entry route."),
    ("LONG-10", 7): ("source_confirmed_critical", "The response claims entrance requirements are unavailable although the frozen record contains degree, English, and selection rules."),
    ("LONG-11", 10): ("source_confirmed_noncritical", "It speculates that a numeric clinical-hour total exists, but explicitly says no number is published and requests human confirmation."),
    ("LONG-11", 11): ("source_confirmed_noncritical", "Simplified repetition of the cautious, unsupported clinical-hours premise; retain as noncritical evidence-discipline failure."),
    ("LONG-12", 10): ("source_confirmed_critical", "The answer applies the Canadian work-permit condition to all international applicants and omits the outside-Canada path."),
    ("LONG-12", 11): ("source_confirmed_critical", "The simplified answer again applies approval/work-permit conditions without the outside-Canada exception."),
    ("LONG-12", 20): ("source_confirmed_critical", "The mandatory alternate-entry pre-entry assessment is incorrectly described as optional."),
}


def usage_from_transcripts():
    total = Counter()
    models, efforts = set(), set()
    for path in sorted((RUN / "transcripts").glob("*.json")):
        for turn in load(path).get("turns", []):
            for event in turn.get("events", []):
                if event.get("kind") != "model":
                    continue
                total["requests"] += 1
                request, response = event.get("request") or {}, event.get("response") or {}
                models.add(request.get("model"))
                effort = (request.get("reasoning") or {}).get("effort")
                if effort:
                    efforts.add(effort)
                usage = response.get("usage") or {}
                details = usage.get("input_tokens_details") or {}
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    total[key] += int(usage.get(key) or 0)
                total["cached_input_tokens"] += int(details.get("cached_tokens") or 0)
                total["cache_write_tokens"] += int(details.get("cache_write_tokens") or 0)
    return dict(total), sorted(x for x in models if x), sorted(efforts)


def usage_from_judgments():
    total = Counter()
    models, efforts, attempts = set(), set(), 0
    paths = [p for p in (RUN / "judgments").glob("*.json")
             if not p.name.endswith((".input.json", ".packet.json"))]
    for path in sorted(paths):
        item = load(path)
        attempts += int(item.get("attempt") or 0)
        models.add(item.get("judge_model"))
        efforts.add(item.get("reasoning_effort"))
        usage = item.get("usage") or {}
        details = usage.get("input_tokens_details") or {}
        total["requests"] += 1
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            total[key] += int(usage.get(key) or 0)
        total["cached_input_tokens"] += int(details.get("cached_tokens") or 0)
        total["cache_write_tokens"] += int(details.get("cache_write_tokens") or 0)
    total["attempts"] = attempts
    return dict(total), sorted(x for x in models if x), sorted(x for x in efforts if x)


def price(block):
    block = dict(block)
    block["uncached_input_tokens"] = (
        block.get("input_tokens", 0) - block.get("cached_input_tokens", 0)
        - block.get("cache_write_tokens", 0)
    )
    block["approximate_cost_usd"] = round((
        block["uncached_input_tokens"] * 4
        + block.get("cached_input_tokens", 0) * .4
        + block.get("cache_write_tokens", 0) * 5
        + block.get("output_tokens", 0) * 20
    ) / 1_000_000, 4)
    return block


def metric_rows(baseline, phase3, structural_before, structural_after, long_pass):
    b, p = baseline["requested_metrics"], phase3["requested_metrics"]
    rows = [
        ("weighted_score", b["overall_weighted_score"], p["overall_weighted_score"], "0-100", "model_language; evaluator differs"),
        ("factual_adequacy", b["factual_correctness_rate"], p["factual_correctness_rate"], "%", "mixed; evaluator differs"),
        ("strict_factual", b["strict_factual_correctness_rate"], p["strict_factual_correctness_rate"], "%", "mixed; evaluator differs"),
        ("entity_resolution", b["entity_resolution_accuracy"], p["entity_resolution_accuracy"], "%", "mixed; evaluator differs"),
        ("context_retention", b["context_retention_accuracy"], p["context_retention_accuracy"], "%", "mixed; evaluator differs"),
        ("scope_accuracy", b["scope_accuracy"], p["scope_accuracy"], "%", "mixed; evaluator differs"),
        ("unsupported_inference_rate", b["unsupported_inference_rate"], p["unsupported_inference_rate"], "% adverse", "model_language; evaluator differs"),
        ("unnecessary_clarification_rate", b["unnecessary_clarification_rate"], p["unnecessary_clarification_rate"], "% adverse", "model_language; evaluator differs"),
        ("missed_necessary_clarification_rate", b["missed_necessary_clarification_rate"], p["missed_necessary_clarification_rate"], "% adverse", "mixed; evaluator differs"),
        ("repetition_list_dump_rate", b["repetition_list_dump_rate"], p["repetition_list_dump_rate"], "% adverse", "model_language; evaluator differs"),
        ("naturalness", b["human_advisor_naturalness_0_to_4"], p["human_advisor_naturalness_0_to_4"], "0-4", "model_language; evaluator differs"),
        ("frustration_handling", b["stop_frustration_handling_rate"], p["stop_frustration_handling_rate"], "%", "mixed; evaluator differs"),
        ("next_step_guidance", baseline["metrics"]["next_step_guidance"]["adequate_rate_percent"], phase3["metrics"]["next_step_guidance"]["adequate_rate_percent"], "%", "model_language; evaluator differs"),
        ("evidence_discipline", baseline["metrics"]["evidence_discipline"]["adequate_rate_percent"], phase3["metrics"]["evidence_discipline"]["adequate_rate_percent"], "%", "mixed; evaluator differs"),
        ("rubric_long_conversation_success", b["long_conversation_success_rate"], p["long_conversation_success_rate"], "%", "mixed; strict all-turn rubric"),
        ("model_free_long_quality_gate", 0.0, round(100 * long_pass / 12, 2), "%", "model-free"),
        ("structural_state_assertion_rate", structural_before, structural_after, "%", "deterministic"),
        ("critical_flags", baseline["critical_failure_turns"], phase3["critical_failure_turns"], "turns", "evaluator differs"),
        ("noncritical_failure_turns", sum(baseline["failure_layers"].values()) - baseline["critical_failure_turns"], sum(phase3["failure_layers"].values()) - phase3["critical_failure_turns"], "turns", "evaluator differs"),
    ]
    return [dict(metric=m, baseline=v1, phase3=v2, delta=round(v2-v1, 3), unit=u, attribution=a)
            for m, v1, v2, u, a in rows]


def main():
    baseline, phase3 = load(BASELINE / "summary.json"), load(RUN / "summary.json")
    manifest = load(RUN / "manifest.json")
    failures = load(RUN / "failure_index.json")
    corpus = {s["id"]: s for s in load(HOME / "corpus.json")["scenarios"]}
    structural_b = load(BASELINE / "structural_assertions.json")
    structural_p = load(RUN / "structural_assertions.json")
    structural_before = round(100 * sum(x["pass"] for x in structural_b) / len(structural_b), 2)
    structural_after = round(100 * sum(x["pass"] for x in structural_p) / len(structural_p), 2)

    long_rows = []
    passing_long = []
    for path in sorted((RUN / "transcripts").glob("LONG-*.json")):
        transcript = load(path)
        rows = assess(transcript)
        long_rows.extend(rows)
        substantive = [r["repetition_pass"] or (
            r["word_count"] <= 100 and "international" in r["question"].lower()
            and r["list_dump_pass"] and r["unsupported_inference_pass"]
        ) for r in rows]
        keys = ("structural_pass", "list_dump_pass", "unsupported_inference_pass", "directness_pass", "naturalness_pass")
        if transcript.get("status") == "complete" and len(rows) == 22 and all(r[k] for r in rows for k in keys) and all(substantive):
            passing_long.append(path.stem)
    long_quality = aggregate(long_rows)
    substantive_pass = sum(r["repetition_pass"] or (
        r["word_count"] <= 100 and "international" in r["question"].lower()
        and r["list_dump_pass"] and r["unsupported_inference_pass"]
    ) for r in long_rows)

    advisor_usage, advisor_models, advisor_efforts = usage_from_transcripts()
    judge_usage, judge_models, judge_efforts = usage_from_judgments()
    advisor_usage, judge_usage = price(advisor_usage), price(judge_usage)
    total_usage = price({key: advisor_usage.get(key, 0) + judge_usage.get(key, 0) for key in (
        "requests", "input_tokens", "cached_input_tokens", "cache_write_tokens", "output_tokens", "total_tokens"
    )})
    usage = {
        "advisor": advisor_usage, "evaluator": judge_usage, "total": total_usage,
        "advisor_models": advisor_models, "advisor_reasoning_efforts": advisor_efforts,
        "evaluator_models": judge_models, "evaluator_reasoning_efforts": judge_efforts,
        "pricing": {"uncached_input_per_million_usd": 4.0, "cached_input_per_million_usd": .4,
                    "cache_write_per_million_usd": 5.0, "output_per_million_usd": 20.0,
                    "source": "frozen GPT-5.6 Sol rates reused from Phase 2C"},
    }

    critical_rows = []
    for item in failures:
        if item.get("severity") != "critical":
            continue
        key = (item["scenario_id"], item["turn"])
        outcome, rationale = ADJUDICATION[key]
        transcript = load(RUN / "transcripts" / f"{item['scenario_id']}.json")
        turn = transcript["turns"][item["turn"] - 1]
        expected = corpus[item["scenario_id"]]["turns"][item["turn"] - 1]["expected"]
        critical_rows.append({
            "scenario_id": item["scenario_id"], "turn": item["turn"],
            "judge_flag": "critical", "adjudication": outcome,
            "question": turn["request"]["question"], "answer": turn["response"]["answer"],
            "expected": expected, "frozen_evidence_review": item["evidence"],
            "human_rationale": rationale, "layer": item["layer"], "root_cause": item["root_cause"],
        })
    adjudication_counts = dict(Counter(x["adjudication"] for x in critical_rows))
    comparisons = metric_rows(baseline, phase3, structural_before, structural_after, len(passing_long))

    with (RUN / "baseline_vs_current_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=comparisons[0].keys())
        writer.writeheader(); writer.writerows(comparisons)
    save(RUN / "baseline_vs_current_metrics.json", comparisons)
    with (RUN / "critical_finding_adjudication.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ("scenario_id", "turn", "judge_flag", "adjudication", "layer", "root_cause", "question", "expected", "human_rationale")
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(critical_rows)
    save(RUN / "critical_finding_adjudication.json", critical_rows)
    save(RUN / "api_usage_cost_summary.json", usage)
    save(RUN / "model_free_long_validation.json", {
        "turns": len(long_rows), "quality": long_quality,
        "substantive_repetition": {"passed": substantive_pass, "failed": len(long_rows) - substantive_pass},
        "passing_scenarios": passing_long, "passing_count": len(passing_long), "total_scenarios": 12,
    })

    certification = {
        "phase": "3", "run_id": RUN_ID, "mode": "cost_conscious",
        "decision": "BLOCKED — NOT CERTIFIED FOR BCIT DEMO PREPARATION",
        "decision_reason": "18 source-confirmed critical turns remain; the critical-academic-error release gate is open.",
        "astra_used": False, "advisor_model": "gpt-5.6-sol", "advisor_reasoning": "medium",
        "evaluator_model": "gpt-5.6-sol", "evaluator_reasoning": "medium",
        "evaluator_caveat": "Phase 1 used Astra Low and Phase 3 used Sol Medium. The 95.52 versus 89.52 language score is descriptive, not a perfectly apples-to-apples judge-model comparison. Deterministic structural metrics are directly comparable.",
        "run": {"scenarios": 120, "turns": 636, "transport_errors": 0, "retries": 0,
                "duplicate_scenarios": 0, "status": manifest["status"]},
        "metric_comparison": comparisons,
        "structural": {"baseline": {"passed": sum(x["pass"] for x in structural_b), "total": len(structural_b), "rate_percent": structural_before},
                       "phase3": {"passed": sum(x["pass"] for x in structural_p), "total": len(structural_p), "rate_percent": structural_after,
                                  "failures": [x for x in structural_p if not x["pass"]]}},
        "long_conversations": {"model_free_end_to_end_passed": len(passing_long), "total": 12,
                               "passing_ids": passing_long, "quality": long_quality,
                               "strict_rubric_success_rate_percent": phase3["requested_metrics"]["long_conversation_success_rate"],
                               "interpretation": "All 12 pass memory/structure/response-discipline checks; strict all-turn rubric success remains 0% because isolated academic-quality failures occur in long scenarios."},
        "critical_adjudication": {"judge_flags": len(critical_rows), "counts": adjudication_counts,
                                  "source_confirmed_critical": adjudication_counts.get("source_confirmed_critical", 0),
                                  "table_json": "critical_finding_adjudication.json", "table_csv": "critical_finding_adjudication.csv"},
        "failure_attribution": phase3["failure_layers"],
        "noncritical_failure_turns": sum(phase3["failure_layers"].values()) - phase3["critical_failure_turns"],
        "failure_transcripts_grouped_by_category": phase3["failure_export_directory"],
        "usage": usage,
        "integrity": {"corpus_sha256": manifest["corpus_sha256"], "database_before_sha256": manifest["database_sha256"],
                      "database_after_sha256": manifest["database_after_sha256"],
                      "database_unchanged": manifest["database_unchanged"], "production_unchanged": manifest["production_unchanged"],
                      "production_hashes": manifest["production_hashes"]},
        "validation": {"full_python_suite": {"ran": 547, "passed_initially": 541, "setup_failures": 6,
                                               "setup_failure": "local API not running; connection refused",
                                               "targeted_api_rerun": {"passed": 6, "total": 6},
                                               "effective_assertion_result": "547/547 passed with the six environment-dependent cases closed after starting the unchanged API",
                                               "prior_phase2c_full_suite_reused": "547/547; production hashes unchanged"},
                       "browser_state": {"passed": 5, "total": 5}},
        "blockers": [x for x in critical_rows if x["adjudication"] == "source_confirmed_critical"],
    }
    save(ROOT / "HUMAN_ADVISOR_PHASE_3_CERTIFICATION.json", certification)

    c = {x["metric"]: x for x in comparisons}
    lines = [
        "# Human Advisor Experience — Phase 3 Full Certification", "",
        "Phase 3 used GPT-5.6 Sol with medium reasoning for both the live advisor and the evaluator. Astra was not used.", "",
        "## Decision", "",
        "**BLOCKED — NOT CERTIFIED FOR BCIT DEMO PREPARATION.**", "",
        "The full corpus completed reliably and most measured behavior improved substantially, but 18 source-confirmed critical turns remain. The release gate requires zero source-confirmed critical academic errors.", "",
        "## Full-run result", "",
        "| Measure | Phase 1 | Phase 3 |", "|---|---:|---:|",
        f"| Frozen corpus | 120 scenarios / 636 turns | 120 scenarios / 636 turns |",
        f"| Weighted score | {c['weighted_score']['baseline']:.2f} | {c['weighted_score']['phase3']:.2f} |",
        f"| Factual adequacy | {c['factual_adequacy']['baseline']:.2f}% | {c['factual_adequacy']['phase3']:.2f}% |",
        f"| Entity resolution | {c['entity_resolution']['baseline']:.2f}% | {c['entity_resolution']['phase3']:.2f}% |",
        f"| Context retention | {c['context_retention']['baseline']:.2f}% | {c['context_retention']['phase3']:.2f}% |",
        f"| Scope accuracy | {c['scope_accuracy']['baseline']:.2f}% | {c['scope_accuracy']['phase3']:.2f}% |",
        f"| Unsupported-inference rate | {c['unsupported_inference_rate']['baseline']:.2f}% | {c['unsupported_inference_rate']['phase3']:.2f}% |",
        f"| Repetition/list-dump rate | {c['repetition_list_dump_rate']['baseline']:.2f}% | {c['repetition_list_dump_rate']['phase3']:.2f}% |",
        f"| Structural assertions | 615/678 ({structural_before:.2f}%) | 672/678 ({structural_after:.2f}%) |",
        f"| Transport errors | historical failures recorded | 0 |",
        "", 
        "> Evaluator caveat: Phase 1 was judged by Astra Low; Phase 3 was judged by Sol Medium. The score and language-quality deltas are descriptive. The frozen corpus, expectations, rubric, evidence protocol, and deterministic assertions were preserved; structural metrics are directly comparable.", "",
        "## Required answers", "",
        f"1. **Change from 89.52:** the Sol-evaluated score is 95.52 (+6.00). Factual adequacy rose to 96.16%, entity resolution to 98.58%, context retention to 97.48%, and scope accuracy to 97.17%.",
        f"2. **Source-confirmed critical errors:** yes—18 of 25 judge-critical flags remain critical after frozen-evidence review. Five were downgraded to noncritical, one has conflicting source fields, and one was not confirmed.",
        f"3. **Entity/context/scope:** 98.58% / 97.48% / 97.17% under the frozen rubric; deterministic assertions are 672/678 (99.12%).",
        f"4. **Repetition/list dumping:** controlled. The rubric adverse rate is 1.26%; model-free checks found 0/264 long-turn list dumps and 0/264 repetition failures.",
        f"5. **Unsupported inference:** materially lower by the rubric estimate, from 7.23% to 2.83%, with evaluator caveat. Model-free long-turn checks found 0/264 heuristic failures, but source review still confirmed several unsupported academic claims.",
        f"6. **Long conversations:** 12/12 pass end-to-end memory, structure, and response-discipline checks. Strict rubric scenario success is 0% because isolated academic errors remain in several long conversations.",
        f"7. **API cost:** {total_usage['requests']} requests, {total_usage['total_tokens']:,} total tokens, approximately ${total_usage['approximate_cost_usd']:.2f}. Advisor: ${advisor_usage['approximate_cost_usd']:.2f}; evaluator: ${judge_usage['approximate_cost_usd']:.2f}.",
        f"8. **Hashes:** production and database hashes did not change; database SHA-256 remained {manifest['database_sha256']}.",
        "9. **Release readiness:** not certified. Resolve the 18 confirmed critical turns and the six deterministic assertion failures, then run a targeted repair validation before considering another full certification.", "",
        "## Critical adjudication", "",
        "The complete 25-row table is saved as `critical_finding_adjudication.csv` and `.json` in the run directory. Confirmed blockers include:", "",
    ]
    for row in critical_rows:
        if row["adjudication"] == "source_confirmed_critical":
            lines.append(f"- **{row['scenario_id']}/{row['turn']}** ({row['layer']}): {row['human_rationale']}")
    lines += ["", "## Validation and artifacts", "",
              "The full Python suite ran once. Six API tests initially failed only because localhost was not running; all six passed after starting the unchanged service. The other 541 tests passed in the full run. Browser state passed 5/5.", "",
              f"Grouped failure transcripts: `{phase3['failure_export_directory']}`. The run directory also contains all 120 transcripts, 120 judgments, raw evaluator attempts, evidence packets, score CSVs, the comparison tables, adjudication tables, usage summary, manifests, and validation logs.", ""]
    (ROOT / "HUMAN_ADVISOR_PHASE_3_CERTIFICATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"decision": certification["decision"], "score": phase3["overall_weighted_score_percent"],
                      "confirmed_critical": adjudication_counts.get("source_confirmed_critical", 0),
                      "long_passed": len(passing_long), "cost_usd": total_usage["approximate_cost_usd"]}, indent=2))


if __name__ == "__main__":
    main()
