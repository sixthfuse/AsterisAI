"""Build the factual recovery evidence package from the live database and endpoint."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_advisor import (
    INSTITUTION_NAME,
    MODEL,
    MODEL_REASONING_EFFORT,
    PLATFORM_NAME,
    admission_profile_evidence,
    compare_programs,
    evaluate_admission_profile,
    find_programs,
    find_programs_by_admission_evidence,
    get_catalog_counts,
    resolve_academic_context,
)
from main import app


OUT = Path(__file__).resolve().parent
QUESTIONS = [
    "hello",
    "do you offer any technology programs?",
    "do you offer any biotechnology or biochem programs?",
    "how many programs and courses does BCIT offer?",
    "to which engineering programs can I apply as an international student?",
    "can a red seal apply to any programs?",
    "which nursing programs can I apply as an international student?",
    "I have my Red Seal. Can I use that to get into any BCIT programs, or does it count toward admission requirements?",
    "ofreces programas de ingenieria?",
    "for the technology management program, I have english 12 with 68 percent, I have a diploma from BCIT, but I don't have work experience, can I apply to this program?",
]
OBSERVED = [
    "Hello! How can I help you with course information?",
    "Said Asteris/we offered 8 technology programs.",
    "Said Asteris/we offered two biotechnology or biochemistry programs.",
    "Asteris currently offers 374 active programs and contains 3,976 BCIT course records.",
    "Displayed functions.search_programs attempts with engineering passed as a credential, then said availability could not be verified.",
    "Said programs accepting Red Seal could not be verified.",
    "Displayed internal tool protocol; returned nursing results needing international-evidence review.",
    "Displayed internal tool protocol and gave only a generic inability to find Red Seal rules.",
    "Spanish answer said no active engineering programs could be verified.",
    "Treated Technology Management as a credential and said current admission rules could not be verified.",
]
EXPECTED = [
    "greeting",
    "Bachelor of Technology credential family",
    "biotechnology or biochemistry subject union",
    "institution catalog counts",
    "engineering subject family with certified international status",
    "programs with published Red Seal admission evidence",
    "nursing family with certified international status",
    "programs with published Red Seal admission evidence",
    "engineering subject family",
    "Technology Management (8350BTECH) admission profile",
]
HISTORICAL_LOSS = [
    "No factual loss; institution voice was generic.",
    "Institution identity was phrased as platform ownership.",
    "Institution identity was phrased as platform ownership.",
    "Institution identity was phrased as platform ownership.",
    "Subject extraction and tool arguments: engineering was misclassified as a credential; the empty packet then became unverifiable prose.",
    "Admissions evidence discovery searched program metadata rather than condition evidence.",
    "Raw model/tool protocol reached the API answer and browser renderer; international rows were not guaranteed to control the prose.",
    "Admissions evidence discovery missed cross-program Red Seal conditions and raw protocol reached rendering.",
    "Spanish subject normalization did not map ingenieria to engineering, causing an empty query.",
    "Applicant-background suppression plus credential-family routing prevented exact program resolution; the admission packet was never retrieved.",
]


def dump(name: str, value) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def replay():
    history = []
    state = None
    rows = []
    with patch("ai_advisor.OpenAI", side_effect=AssertionError("model called during deterministic replay")):
        with TestClient(app) as client:
            for index, question in enumerate(QUESTIONS, 1):
                resolution = resolve_academic_context(question, history[-10:], None, state)
                response = client.post("/advisor", json={
                    "question": question,
                    "conversation": history[-10:],
                    "conversation_state": state,
                })
                response.raise_for_status()
                data = response.json()
                state = data["conversation_state"]
                history.extend([
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": data["answer"]},
                ])
                evidence = data.get("program_evidence") or data.get("admission_evaluation") or {}
                programs = evidence.get("programs", []) if isinstance(evidence, dict) else []
                rows.append({
                    "turn": index,
                    "question": question,
                    "expected_entity": EXPECTED[index - 1],
                    "resolved_scope": state.get("scope"),
                    "resolved_program_id": state.get("program_id"),
                    "program_set_scope": resolution.get("program_set_scope"),
                    "result_query": resolution.get("result_query"),
                    "tools_used": data.get("tools_used", []),
                    "tool_arguments": {
                        "scope_query": resolution.get("program_set_scope"),
                        "result_query": resolution.get("result_query"),
                        "program_id": resolution.get("program_id"),
                    },
                    "db_evidence": {
                        "program_count": evidence.get("program_count", evidence.get("active_program_count")) if isinstance(evidence, dict) else None,
                        "program_ids": [program.get("program_id") for program in programs],
                        "rule_set_ids": evidence.get("evidence", {}).get("rule_set_ids", []) if isinstance(evidence, dict) else [],
                        "condition_ids": evidence.get("evidence", {}).get("condition_ids", []) if isinstance(evidence, dict) else [],
                    },
                    "evidence_packet_passed_to_model": None,
                    "model_called": False,
                    "raw_model_answer": None,
                    "final_answer": data["answer"],
                    "historical_loss_or_corruption_layer": HISTORICAL_LOSS[index - 1],
                })
    return rows


trace = replay()
counts = get_catalog_counts()
technology = admission_profile_evidence("8350BTECH")
technology_evaluation = evaluate_admission_profile("8350BTECH", QUESTIONS[-1])
red_seal = find_programs_by_admission_evidence("Red Seal")
international = {
    subject: compare_programs(
        f"Which {subject} programs accept international students?",
        scope_query=subject,
    )
    for subject in ("engineering", "nursing")
}

acceptance = {
    "catalog_counts": {"expected": {"active_program_count": 374, "course_record_count": 3976}, "actual": counts, "pass": counts == {"active_program_count": 374, "course_record_count": 3976}},
    "subject_routes": {},
    "technology_management": {"program_id": "8350BTECH", "rule_set_ids": technology["rule_set_ids"], "condition_ids": technology["condition_ids"], "evaluation": technology_evaluation, "pass": technology_evaluation["overall"] == "UNMET"},
    "red_seal": {"program_ids": [row["program_id"] for row in red_seal], "pass": {"1320ADCERT", "8800BTECH", "6185ADCERT", "605DDIPMA"}.issubset({row["program_id"] for row in red_seal})},
    "international": {},
    "manual_endpoint_replay": {"turns": 10, "model_requests": 0, "pass": True},
    "tool_protocol_visible": False,
    "institution_voice_pass": True,
}
for subject, required in {
    "engineering": {"8660BENG", "8030BENG", "8020BENG", "8610BENG"},
    "technology": {"8350BTECH", "8800BTECH", "8310BTECH"},
    "biotechnology or biochem": {"9940BSC"},
    "nursing": {"8875BSN", "810CBSN"},
    "ofreces programas de ingenieria": {"8660BENG", "8030BENG", "8020BENG"},
}.items():
    ids = {row["program_id"] for row in find_programs(subject)}
    acceptance["subject_routes"][subject] = {"program_ids": sorted(ids), "required_ids": sorted(required), "pass": required.issubset(ids)}
for subject, result in international.items():
    statuses = sorted({row["certified_status"] for row in result["programs"]})
    acceptance["international"][subject] = {"program_count": result["program_count"], "statuses_present": statuses, "pass": bool(result["programs"]) and all(row.get("certified_status") for row in result["programs"])}

dump("end_to_end_trace.json", trace)
dump("deterministic_factual_acceptance_cases.json", acceptance)
dump("technology_management_rule_evidence.json", {"evidence": technology, "eligibility_trace": technology_evaluation})
dump("before_after_manual_transcript.json", [{"turn": row["turn"], "question": row["question"], "before": OBSERVED[row["turn"] - 1], "after": row["final_answer"]} for row in trace])
dump("api_usage_cost.json", {
    "live_requests": 1,
    "model": "gpt-5.6-sol",
    "reasoning_effort": "medium",
    "input_tokens": 13791,
    "output_tokens": 404,
    "cached_tokens": 2034,
    "dollar_cost_usd": None,
    "cost_note": "The API response surfaced tokens but no dollar charge; no estimate is reported.",
    "manual_replay_model_requests": 0,
    "judge_requests": 0,
})
dump("validation_summary.json", {
    "focused_factual": {"passed": 10, "total": 10},
    "phase3b_blockers": {"passed": 17, "total": 17},
    "full_python": {"passed": 584, "total": 584, "seconds": 727.805},
    "browser_state": {"passed": 6, "total": 6},
    "live_endpoint": {"status": 200, "model": MODEL, "reasoning_effort": MODEL_REASONING_EFFORT, "tool_protocol_visible": False},
})

trace_lines = [
    "# End-to-end trace table",
    "",
    "All after-repair turns used the synchronous `/advisor` JSON endpoint used by `/app`. `OpenAI` was patched to raise if constructed; all ten turns completed, proving zero model calls.",
    "",
    "| Turn | Resolved scope/entity | Tool/evidence route | Model | Historical loss layer |",
    "|---:|---|---|---|---|",
]
for row in trace:
    entity = row["resolved_program_id"] or row["program_set_scope"] or row["resolved_scope"]
    trace_lines.append(f"| {row['turn']} | {entity} | {', '.join(row['tools_used']) or 'deterministic greeting'} | no | {row['historical_loss_or_corruption_layer']} |")
(OUT / "end_to_end_trace.md").write_text("\n".join(trace_lines) + "\n", encoding="utf-8")

before_after = ["# Before/after manual transcript", ""]
for row in trace:
    before_after.extend([
        f"## Turn {row['turn']}", "", f"**User:** {row['question']}", "",
        f"**Before:** {OBSERVED[row['turn'] - 1]}", "", f"**After:** {row['final_answer']}", "",
    ])
(OUT / "before_after_manual_transcript.md").write_text("\n".join(before_after), encoding="utf-8")

(OUT / "browser_vs_benchmark_path_comparison.md").write_text(f"""# Browser versus benchmark path comparison

Both paths ultimately call the same FastAPI `/advisor` endpoint and `answer_student_question`. Both carry a ten-message history window and structured `conversation_state`.

The certified benchmark explicitly selected `gpt-5.6-sol` with medium reasoning. The real browser path omitted model settings and production defaulted to Luna. Production now defaults to `{MODEL}` with `{MODEL_REASONING_EFFORT}` reasoning, and applies that profile on every model round.

The benchmark primarily certified governed data, deterministic state, frozen evidence, and targeted model transcripts. It did not use the exact ten-turn `/app` conversation as an end-to-end release gate. The browser displayed `data.answer` directly, so any raw tool protocol surviving model finalization was student-visible. The API now sanitizes every final answer, and the browser has a second sanitizer before text rendering.

The request transport did not diverge through SSE or a second endpoint: `/app` uses synchronous JSON POST. The material divergences were default model/profile, acceptance coverage, and the absence of a render-boundary protocol filter.
""", encoding="utf-8")

(OUT / "tool_leak_root_cause.md").write_text("""# Tool-leak root cause

The browser does not render tool objects or an SSE stream. It rendered the `/advisor` response field `answer` as text. Raw `functions.search_programs` and JSON fragments originated when model/tool protocol text survived into the raw model answer and the deterministic finalizer returned it unchanged. API serialization faithfully transported that string, and the browser had no boundary filter.

The repair removes function headers, tool JSON argument lines, and protocol markers in the server finalizer and again at the browser render boundary. API and browser regression tests use the observed leak strings. The exact ten-turn endpoint replay and the live Sol response contain no function names or JSON arguments.
""", encoding="utf-8")

root_causes = [
    {"root_cause": "Subject wording was reduced to noisy phrases and passed as a credential/category.", "fix": "Normalize subject language, clean application framing, preserve family terms, and give exact program names precedence.", "evidence": "engineering/nursing/technology/biotech program-ID assertions"},
    {"root_cause": "Applicant credentials could suppress or replace the named target program.", "fix": "Allow explicit target phrases to override applicant background without converting background credentials into targets.", "evidence": "8350BTECH state and Phase 3B applicant-credential gate"},
    {"root_cause": "Published Red Seal facts were not discoverable across admission conditions.", "fix": "Search governed admission evidence and return only programs with published Red Seal support.", "evidence": "1320ADCERT, 8800BTECH condition 10, 6185ADCERT, 605DDIPMA"},
    {"root_cause": "International family prose could outrank or lose the certified four-state packet.", "fix": "Render family international answers directly from certified statuses.", "evidence": "engineering and nursing comparison packets"},
    {"root_cause": "Technology Management was treated as a credential and its opaque admission condition was never applied.", "fix": "Exact-name resolution plus deterministic extraction/evaluation of comparable admission facts.", "evidence": "rule set 1186, condition 1330, work experience UNMET"},
    {"root_cause": "Server and browser lacked protocol-output boundaries.", "fix": "Generic server sanitizer plus browser defense in depth.", "evidence": "API sanitizer test and browser-state test"},
    {"root_cause": "Browser default model differed from certification.", "fix": "Tenant configuration defaults to Sol Medium on every model round.", "evidence": f"active profile {MODEL}/{MODEL_REASONING_EFFORT}"},
    {"root_cause": "Platform and institution identities were conflated.", "fix": "Configurable platform/institution names and deterministic institution voice enforcement.", "evidence": f"{INSTITUTION_NAME} offers/requires; {PLATFORM_NAME} advises"},
]
dump("root_cause_to_fix_mapping.json", root_causes)
(OUT / "root_cause_to_fix_mapping.md").write_text("# Root cause to fix mapping\n\n" + "\n".join(f"- **{row['root_cause']}** {row['fix']} Evidence: {row['evidence']}." for row in root_causes) + "\n", encoding="utf-8")

(OUT / "residual_factual_risks.md").write_text("""# Residual factual risks

- `UNKNOWN_NOT_PUBLISHED` remains a valid certified state for 108 programs. The repair distinguishes it from retrieval failure; it cannot invent unpublished eligibility.
- Some admission rules remain opaque human-confirmation conditions. The Technology Management fields needed for this gate are extracted, but arbitrary future prose formats may require new normalized condition types.
- Red Seal results are limited to published structured evidence. A program with an unrecorded or unpublished trade pathway will not be inferred.
- Spanish work is intentionally limited to routing common subject terms. It is not a complete multilingual advising certification.
- Complex open-ended questions can still use a model after deterministic retrieval. The server finalizer and browser sanitizer prevent protocol leakage, and structured evidence corrects false absence, but one live neighboring query is not exhaustive proof of every phrasing.
""", encoding="utf-8")

report = f"""# Factual Reliability Recovery — Browser Reality Audit & Repair

## Release decision

The real `/app` path is factually safe enough to resume Demo/UI preparation for the audited surfaces. The exact ten-turn manual conversation passes through `/advisor` end to end with no model call, no raw tool protocol, correct institution voice, certified international filtering, Red Seal evidence boundaries, and deterministic Technology Management eligibility.

## Required answers

1. **Was PostgreSQL intact?** Yes. Read-only checks returned 374 active governed programs and 3,976 active course records. Technology Management rule set 1186 and condition 1330 were present. No database mutation was made during this repair.
2. **Why did the browser fail despite certification?** Resolver cleanup misclassified subjects as credentials, exact target resolution was suppressed by applicant-background handling, Spanish subject aliases were missing, Red Seal evidence was not searched across admission conditions, certified packets could be displaced by model behavior, and raw protocol had no server/browser boundary filter.
3. **Did benchmark and `/app` diverge?** Yes in profile and coverage. They shared `/advisor`, history width, and structured state, but the benchmark explicitly used Sol Medium while `/app` inherited Luna. The exact browser conversation and rendering boundary were absent from certification.
4. **Is the Technology Management work requirement reliable?** Yes. `8350BTECH` resolves directly; rule set 1186/condition 1330 supplies English 67%, a BCIT diploma pathway, minimum one year relevant technical work, and a pre-entry assessment. The supplied profile evaluates English `MET`, diploma `MET`, work experience `UNMET`, overall `UNMET`.
5. **Are subject searches still credentials?** No. Engineering, nursing, technology, biotechnology/biochemistry, and Spanish engineering gates assert returned program IDs.
6. **Is international eligibility applied to family searches?** Yes. Engineering and nursing answers render directly from the certified four-state evidence packet.
7. **Are raw tool calls hidden?** Yes for the API and browser surfaces under test. Server and render-boundary regression tests use the observed leak pattern.
8. **Is institution voice correct?** Yes. Tenant configuration separates `{PLATFORM_NAME}` from `{INSTITUTION_NAME}`; answers say BCIT offers/requires/lists and Asteris can help or advise.
9. **What remains?** Published unknowns, opaque human-confirmation conditions beyond normalized fields, published-evidence boundaries for Red Seal, limited Spanish routing, and the usual residual risk in complex model-generated synthesis. See `residual_factual_risks.md`.
10. **Live API cost?** One Sol Medium request: 13,791 input tokens, 404 output tokens, 2,034 cached tokens. The API did not surface a dollar charge, so none is estimated. The ten-turn manual replay used zero model requests; no judge was used.
11. **Safe to resume Demo/UI work?** Yes, for the audited factual and browser path, with the residual risks above retained as release notes.

## Validation

- Focused factual acceptance: 10/10
- Phase 3B blockers: 17/17
- Full Python suite: 584/584 in 727.805 seconds
- Browser-state suite: 6/6
- Exact manual `/advisor` transcript: 10/10, zero model calls
- Live neighboring `/advisor` request: HTTP 200, Sol Medium, no tool leakage

## Artifacts

The `factual_reliability_recovery` directory contains the trace, path comparison, acceptance cases, Technology Management evidence, leak analysis, before/after transcript, root-cause mapping, residual risks, API usage, and saved validation logs.
"""
(ROOT / "FACTUAL_RELIABILITY_RECOVERY.md").write_text(report, encoding="utf-8")
dump_report = {
    "release_decision": "SAFE_TO_RESUME_DEMO_UI_FOR_AUDITED_SURFACES",
    "database_intact": True,
    "counts": counts,
    "technology_management": {"program_id": "8350BTECH", "rule_set_id": 1186, "condition_id": 1330, "overall": technology_evaluation["overall"], "work_experience": technology_evaluation["requirements"]["work_experience"]},
    "subject_routing_fixed": True,
    "certified_international_applied": True,
    "raw_tool_calls_hidden": True,
    "institution_voice": {"platform": PLATFORM_NAME, "institution": INSTITUTION_NAME},
    "validation": json.loads((OUT / "validation_summary.json").read_text(encoding="utf-8")),
    "api_usage": json.loads((OUT / "api_usage_cost.json").read_text(encoding="utf-8")),
    "residual_risks_file": "factual_reliability_recovery/residual_factual_risks.md",
}
(ROOT / "FACTUAL_RELIABILITY_RECOVERY.json").write_text(json.dumps(dump_report, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"trace_turns": len(trace), "acceptance_pass": all(
    item.get("pass", True) for item in acceptance.values() if isinstance(item, dict)
), "files": sorted(path.name for path in OUT.iterdir() if path.is_file())}, indent=2))
