"""Read-only trace harness for the advisor-v2 failed acceptance conversation."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from dotenv import load_dotenv

from advisor_v2 import AdvisorV2State, AdvisorV2Repository, answer_advisor_v2_hybrid
from advisor_v2_sol import SolLanguageLayer, compact_interpretation_payload
from database import get_connection


TRANSCRIPT = [
    "Hello",
    "How many campuses does BCIT have?",
    "more information about the campuses",
    "how many technology programs do you offer?",
    "how many programs and courses do you offer?",
    "Do you offer any computing programs?",
    "Do you have any programs where I can use my Red Seal certification that would help me get into any programs at bcit?",
    "I have English 12 with 73 percent, I have Red Seal certification as an electrician, and I have Foundations of Math 11 with 55 percent, I have the associate certificate construction operations with 70 percent and I have an 11-month work experience, do I have the requirements for the construction management bachelor degree?",
    "what are the requirements for the construction management bachelors degree",
    "tienen programas de ingenieria?",
    "engineering. list all programs related to engineering",
    "do you have any computing programs?",
    "computing programs",
    "I know you have more computing programs",
    "BCIT is the largest Computing and IT school in canada and you are telling me you have one computing program",
    "list all programs under the computing and IT area of study",
    "list all programs under the computing and IT area of study",
    "as an international student, which programs can I apply for the nursing programs?",
]


def database_inventory() -> dict:
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM programs WHERE status='Active'")
        active_programs = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM courses WHERE status='Active'")
        active_courses = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM campuses WHERE active=TRUE")
        campuses = cursor.fetchone()[0]
        cursor.execute(
            """SELECT a.area_id, a.area_name, count(*)
               FROM programs p JOIN areas_of_study a ON a.area_id=p.area_id
               WHERE p.status='Active'
               GROUP BY a.area_id, a.area_name ORDER BY a.area_id"""
        )
        areas = [dict(zip(("area_id", "area_name", "active_programs"), row)) for row in cursor.fetchall()]
        cursor.execute(
            """SELECT count(*) FROM programs p JOIN areas_of_study a ON a.area_id=p.area_id
               WHERE p.status='Active' AND a.area_id='COMP'"""
        )
        computing = cursor.fetchone()[0]
    return {
        "active_programs": active_programs,
        "active_courses": active_courses,
        "campuses": campuses,
        "computing_area_programs": computing,
        "areas": areas,
    }


def run_deterministic() -> list[dict]:
    state = AdvisorV2State()
    rows = []
    repository = AdvisorV2Repository()
    for index, message in enumerate(TRANSCRIPT, 1):
        started = time.perf_counter()
        result = answer_advisor_v2_hybrid(
            message, conversation_state=state, repository=repository, language_layer=None,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        state = AdvisorV2State.model_validate(result["conversation_state"])
        trace = result["observability"]
        rows.append({
            "turn": index,
            "message": message,
            "latency_ms": elapsed_ms,
            "intent": trace["detected_intent"],
            "question_class": trace["question_class"],
            "context": trace["context"],
            "entity_resolution": trace["entity_resolution"],
            "retrieval": trace["retrieval"],
            "evaluation": trace["rule_evaluation_status"],
            "response_path": trace["final_response_path"],
            "answer": result["answer"],
        })
    return rows


def run_live_interpretations() -> list[dict]:
    layer = SolLanguageLayer()
    state = AdvisorV2State()
    selected = (TRANSCRIPT[3], TRANSCRIPT[7], TRANSCRIPT[9], TRANSCRIPT[17])
    rows = []
    for message in selected:
        payload = compact_interpretation_payload(message, state)
        started = time.perf_counter()
        interpretation, usage = layer.interpret(payload)
        rows.append({
            "message": message,
            "input": payload,
            "output": interpretation.model_dump(mode="json"),
            "usage": usage,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        })
    return rows


def run_live_sequence() -> list[dict]:
    layer = SolLanguageLayer()
    state = AdvisorV2State()
    rows = []
    for index, message in enumerate(TRANSCRIPT, 1):
        started = time.perf_counter()
        result = answer_advisor_v2_hybrid(message, conversation_state=state, language_layer=layer)
        state = AdvisorV2State.model_validate(result["conversation_state"])
        observed = result["observability"]
        rows.append({
            "turn": index, "message": message,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "interpretation_call": observed["interpretation"],
            "retrieval": observed["retrieval"],
            "synthesis_call": observed["synthesis"],
            "usage_total": result.get("usage"),
            "intent": observed["detected_intent"],
            "response_path": observed["final_response_path"],
            "evaluation": observed["rule_evaluation_status"],
            "answer": result["answer"],
        })
    return rows


def run_live_turn9_retest() -> dict:
    state = AdvisorV2State()
    for message in TRANSCRIPT[:8]:
        prior = answer_advisor_v2_hybrid(message, conversation_state=state, language_layer=None)
        state = AdvisorV2State.model_validate(prior["conversation_state"])
    started = time.perf_counter()
    result = answer_advisor_v2_hybrid(
        TRANSCRIPT[8], conversation_state=state, language_layer=SolLanguageLayer(),
    )
    observed = result["observability"]
    return {
        "turn": 9, "message": TRANSCRIPT[8],
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "interpretation_call": observed["interpretation"],
        "retrieval": observed["retrieval"], "synthesis_call": observed["synthesis"],
        "usage_total": result.get("usage"), "intent": observed["detected_intent"],
        "response_path": observed["final_response_path"], "answer": result["answer"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-sol", action="store_true")
    parser.add_argument("--live-sequence", action="store_true")
    parser.add_argument("--live-turn9-retest", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    load_dotenv()
    report = {
        "database_inventory": database_inventory(),
        "deterministic_current_path": run_deterministic(),
        "live_sol_interpretations": run_live_interpretations() if args.live_sol else [],
        "live_sequence": run_live_sequence() if args.live_sequence else [],
        "live_turn9_retest": run_live_turn9_retest() if args.live_turn9_retest else None,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
