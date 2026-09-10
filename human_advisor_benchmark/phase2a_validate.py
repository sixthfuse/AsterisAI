"""Model-free Phase 2A release gates against the frozen Phase 1 baseline."""
from __future__ import annotations

import json
from pathlib import Path

from advisor import get_course_details
from ai_advisor import (
    TopicState,
    _scope_program_details,
    answer_student_question,
    course_prerequisites_answer,
    execute_tool,
    finalize_student_answer,
    find_programs,
    is_conversational_stop,
    resolve_academic_context,
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "human_advisor_benchmark" / "runs" / "baseline_20260908"
OUT = ROOT / "human_advisor_benchmark" / "runs" / "phase2a_deterministic_20260908"
IDS = [
    "FLOW-07", "FLOW-13", "CAT-06-A", "CAT-06-B", "CAT-04-B", "LONG-07",
    "FLOW-02", "FLOW-01", "FLOW-06", "FLOW-09", "FLOW-18", "FLOW-21",
    "FLOW-22", "FLOW-23", "FLOW-30", "FLOW-31", "FLOW-42", "FLOW-47",
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(name: str, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def scope_pass(expected: str, state: dict, stop: bool, clarification: str) -> bool:
    scope = state.get("scope")
    if scope == "ambiguous" and clarification == "required":
        return True
    if expected == "stop":
        return stop
    if expected in {"catalog", "comparison"}:
        return scope in {"program_family", "global"}
    if expected == "prerequisites":
        return scope in {"course", "program"}
    if expected in {"campus", "delivery", "international", "admission", "outcomes", "source", "program_information"}:
        return scope in {"program", "program_family"}
    return scope not in {None, "none", "ambiguous"}


def state_metrics(rows: list[dict]) -> dict:
    entity = [row["entity_pass"] for row in rows if row["entity_applicable"]]
    context = [row["context_pass"] for row in rows if row["context_applicable"]]
    scope = [row["scope_pass"] for row in rows]

    def metric(values):
        return {"passed": sum(values), "applicable": len(values),
                "percent": round(100 * sum(values) / len(values), 2) if values else None}

    return {"turns": len(rows), "entity_resolution": metric(entity),
            "context_retention": metric(context), "scope_accuracy": metric(scope)}


def response_row(scenario, index, response):
    turn = scenario["turns"][index - 1]
    state = response.get("conversation_state") or {}
    state_checks = [check for check in turn.get("checks", []) if check["op"] == "state_in"]
    entity_pass = all(state.get(check["field"]) in check["value"] for check in state_checks)
    context_applicable = bool(turn.get("context_required"))
    context_pass = state.get("scope") not in {None, "none", "ambiguous"}
    if state_checks:
        context_pass = context_pass and entity_pass
    return {
        "scenario_id": scenario["id"], "turn": index, "expected_scope": turn["scope"],
        "state": state, "entity_applicable": bool(state_checks), "entity_pass": entity_pass,
        "context_applicable": context_applicable, "context_pass": context_pass,
        "scope_pass": scope_pass(turn["scope"], state, is_conversational_stop(turn["question"]),
                                 turn["clarification"]),
    }


def replay_candidate(scenarios):
    rows = []
    for scenario in scenarios:
        state = None
        history = []
        for index, turn in enumerate(scenario["turns"], 1):
            resolution = resolve_academic_context(turn["question"], history[-10:], None, state)
            state = resolution["conversation_state"]
            # Mirror the production post-tool state update for a unique verified
            # program search result without invoking a language model.
            if state.get("scope") in {"program_family", "global"} and state.get("result_query"):
                records = find_programs(state["result_query"])
                if state.get("scope_query"):
                    allowed = {program["program_id"] for program in find_programs(state["scope_query"])}
                    records = [program for program in records if program["program_id"] in allowed]
                if len(records) == 1:
                    updated = TopicState.from_value(state)
                    updated.unique_result_program_id = records[0]["program_id"]
                    state = updated.model_dump()
            response = {"conversation_state": state}
            rows.append(response_row(scenario, index, response))
            history.extend([{"role": "user", "content": turn["question"]},
                            {"role": "assistant", "content": "Verified advising response."}])
    return rows


def replay_baseline(scenarios):
    rows = []
    for scenario in scenarios:
        transcript = load(BASELINE / "transcripts" / f"{scenario['id']}.json")
        by_turn = {turn["turn"]: turn for turn in transcript["turns"]}
        for index in range(1, len(scenario["turns"]) + 1):
            rows.append(response_row(scenario, index, by_turn[index].get("response") or {}))
    return rows


def release_gates():
    course, prerequisites = get_course_details("LIBS7001")
    prerequisite_answer = course_prerequisites_answer(course, prerequisites)
    ambiguous = resolve_academic_context("Tell me about Civil Technology.", [], None)
    associate = resolve_academic_context("The associate certificate.", [], None,
                                         ambiguous["conversation_state"])
    certificate = resolve_academic_context("Now the Civil Technology certificate.", [], None,
                                           associate["conversation_state"])
    first = resolve_academic_context("Tell me about Applied Computing MSc.", [], None)
    second = resolve_academic_context("Now tell me about Construction Management BTech.", [], None,
                                      first["conversation_state"])
    returned = resolve_academic_context("Let's return to the first program I mentioned today.",
                                        [], None, second["conversation_state"])
    family = find_programs("nursing programs")
    family_state = resolve_academic_context("Which nursing programs are available?", [], None)
    family_follow = resolve_academic_context("Which of those accept international applicants?", [], None,
                                             family_state["conversation_state"])
    comparison = resolve_academic_context(
        "Compare the Construction Management diploma and Bachelor of Technology.", [], None)
    comparison_follow = resolve_academic_context(
        "Is the other one also a degree?", [], None, comparison["conversation_state"])
    comparison_choice = resolve_academic_context(
        "I mean the diploma.", [], None, comparison_follow["conversation_state"])
    program_state = resolve_academic_context("Tell me about Construction Management BTech.", [], None)
    course_in_program = resolve_academic_context(
        "What are the prerequisites for CMGT 8700 in this program?", [], None,
        program_state["conversation_state"],
    )
    duplicate_title = finalize_student_answer("Engineering Economics is included.", "What is included?", [{
        "courses": [
            {"course_id": "CIVL7000", "display_course_code": "CIVL 7000",
             "course_name": "Engineering Economics"},
            {"course_id": "UBCCIVL7000", "display_course_code": "UBC CIVL 7000",
             "course_name": "Engineering Economics"},
        ]
    }])
    corruption_replays = {}
    for scenario_id, turn_number, forbidden_codes in (
        ("CAT-06-A", 1, ["UBC-CHEM-213"]),
        ("CAT-06-B", 3, ["UBC-CHEM-111", "UBC-CHEM-121", "UBC-CHEM-141"]),
        ("FLOW-31", 2, ["CIVL 1020"]),
    ):
        transcript_turn = load(BASELINE / "transcripts" / f"{scenario_id}.json")["turns"][turn_number - 1]
        finalization = next(event for event in transcript_turn["events"]
                            if event.get("kind") == "finalization")
        replayed = finalize_student_answer(
            finalization["raw_answer"], transcript_turn["request"]["question"],
            [event["result"] for event in transcript_turn["events"] if event.get("kind") == "tool"],
        )
        inserted = [code for code in forbidden_codes
                    if code in replayed and code not in finalization["raw_answer"]]
        corruption_replays[f"{scenario_id}/{turn_number}"] = {
            "pass": not inserted, "inserted_unrelated_codes": inserted,
        }
    null_path = execute_tool("get_program_level_courses", {"level": 1},
                             {"program_id": None, "pathway": None})
    scoped = _scope_program_details(execute_tool("get_program_details", {"program_id": "8660BENG"},
                                                 {"program_id": "8660BENG"})["program"], "admission")
    gates = [
        ("prerequisite_semantics", prerequisite_answer.count(" OR ") == 2 and "None" not in prerequisite_answer,
         prerequisite_answer),
        ("course_code_identity", duplicate_title == "Engineering Economics is included." and
         all(result["pass"] for result in corruption_replays.values()),
         {"ambiguous_title": duplicate_title, "frozen_replays": corruption_replays}),
        ("academic_scope_binding", "not conditions for an earlier credential" in
         scoped["academic_scope_boundaries"]["binding_rule"], scoped["academic_scope_boundaries"]),
        ("null_pathway", "error" in null_path, null_path),
        ("family_completeness", len(family) == 28 and {"680XADCERT", "680FASCERT"}.issubset(
            {program["program_id"] for program in family}), {"count": len(family)}),
        ("credential_disambiguation", associate["program_id"] == "5430ACERT" and
         certificate["program_id"] == "5430CERT", {"associate": associate["program_id"],
                                                     "certificate": certificate["program_id"]}),
        ("course_in_program_context", course_in_program["program_id"] == "8800BTECH",
         course_in_program["conversation_state"]),
        ("family_followup_continuity", family_follow["program_set_query"] and
         family_follow["program_set_scope"] == "nursing programs", family_follow["conversation_state"]),
        ("comparison_continuity", comparison["comparison_program_ids"] ==
         ["7710DIPMA", "8800BTECH"] and comparison_follow["comparison_program_ids"] ==
         ["7710DIPMA", "8800BTECH"] and comparison_choice["program_id"] == "7710DIPMA",
         {"initial": comparison["comparison_program_ids"],
          "followup": comparison_follow["comparison_program_ids"],
          "resolved": comparison_choice["program_id"]}),
        ("long_history_return", returned["program_id"] == "M600MSC", returned["conversation_state"]),
        ("stop_and_question_handling", is_conversational_stop("Thanks, that's all.") and
         not is_conversational_stop("Never mind, where is the program taught?"), None),
    ]
    return [{"gate": name, "pass": passed, "evidence": evidence} for name, passed, evidence in gates]


def main():
    corpus = load(ROOT / "human_advisor_benchmark" / "corpus.json")
    scenarios = [scenario for scenario in corpus["scenarios"] if scenario["id"] in IDS]
    baseline_rows = replay_baseline(scenarios)
    candidate_rows = replay_candidate(scenarios)
    gates = release_gates()
    manifest = {"phase": "2A", "mode": "deterministic_no_model", "scenario_ids": IDS,
                "scenario_count": len(scenarios), "turn_count": sum(len(s["turns"]) for s in scenarios),
                "baseline_run": "baseline_20260908", "live_sol_run": "phase2a_sol_medium_20260908",
                "language_judge": None, "reason": "Sol API credits exhausted; Astra prohibited by phase rule"}
    summary = {"manifest": manifest, "baseline_structural": state_metrics(baseline_rows),
               "candidate_structural": state_metrics(candidate_rows),
               "release_gates": {"passed": sum(g["pass"] for g in gates), "total": len(gates),
                                 "results": gates}}
    save("manifest.json", manifest)
    save("baseline_state_replay.json", baseline_rows)
    save("candidate_state_replay.json", candidate_rows)
    save("release_gates.json", gates)
    save("summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
