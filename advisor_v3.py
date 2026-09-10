"""Advisor v3: one typed, evidence-grounded turn pipeline.

This module intentionally imports only the proven read-only repository and
deterministic rule evaluator from v2. It does not call or reuse the v2
orchestrator, interpreter fallback, response branches, or state machine.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
from typing import Any, Literal

import psycopg
from pydantic import BaseModel, Field

from advisor_v2 import AdvisorV2Repository, StudentProfileV2, _merge_profile
from advisor_v3_sol import MODEL, REASONING_EFFORT, SolV3LanguageLayer, V3Filter, V3SemanticPlan
from database import get_connection


SpeechAct = Literal["new_task", "follow_up", "confirmation", "correction", "clarification", "social"]
TaskName = Literal[
    "discover", "list_all", "count", "select", "filter", "details", "compare",
    "eligibility", "requirements", "course_lookup", "campus_info",
    "international_availability", "clarification_response", "social_ack", "unknown",
]


class ActiveEntitiesV3(BaseModel):
    program_id: str | None = None
    course_id: str | None = None


class DurableResultSetV3(BaseModel):
    result_set_id: str
    entity_type: Literal["program", "course", "campus"]
    ids: list[str] = Field(default_factory=list, max_length=100)
    rows: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    task: str
    category: str | None = None
    filters: dict[str, str] = Field(default_factory=dict)
    total: int = 0
    created_turn: int


class OfferedActionV3(BaseModel):
    action: Literal["list_all", "show_details"]
    result_set_id: str | None = None
    entity_id: str | None = None
    offered_turn: int


class TaskThreadV3(BaseModel):
    task: str = "unknown"
    domain: str = "unknown"
    category: str | None = None
    result_set_id: str | None = None


class PriorAnswerIntentV3(BaseModel):
    task: str = "unknown"
    answer_shape: str = "summary"
    offered_action: OfferedActionV3 | None = None


class AdvisorV3State(BaseModel):
    version: Literal[3] = 3
    turn_index: int = Field(default=0, ge=0)
    active_entities: ActiveEntitiesV3 = Field(default_factory=ActiveEntitiesV3)
    recent_result_sets: list[DurableResultSetV3] = Field(default_factory=list, max_length=8)
    unresolved_references: list[str] = Field(default_factory=list, max_length=8)
    student_profile: StudentProfileV2 = Field(default_factory=StudentProfileV2)
    student_assertion_provenance: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    current_task_thread: TaskThreadV3 = Field(default_factory=TaskThreadV3)
    prior_answer_intent: PriorAnswerIntentV3 = Field(default_factory=PriorAnswerIntentV3)


class OperationNodeV3(BaseModel):
    operation_id: str
    kind: Literal[
        "noop", "taxonomy_list", "catalog_filter", "reuse_result_set", "resolve_program",
        "program_details", "eligibility", "campus_directory", "international_family",
        "international_program", "course_lookup", "red_seal_programs", "clarify",
    ]
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class EvidenceV3(BaseModel):
    evidence_id: str
    source: str
    entity_id: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)
    status: str = "found"


def _norm(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower().replace("’", "'")))


def _blank_plan(**overrides: Any) -> V3SemanticPlan:
    data = {
        "speech_act": "new_task", "task": "unknown", "target_domain": "unknown",
        "target_entity": None, "target_category": None, "referent_source": "none",
        "referent_value": None, "filters": [], "reuse_prior_results": False,
        "clarification": None, "answer_shape": "summary", "student_facts": [],
    }
    data.update(overrides)
    return V3SemanticPlan.model_validate(data)


def classify_turn(question: str, state: AdvisorV3State) -> SpeechAct:
    text = _norm(question)
    if re.fullmatch(r"(?:sure|yes|yes please|okay|ok|please do|go ahead)", text):
        return "confirmation" if state.prior_answer_intent.offered_action else "clarification"
    if re.search(r"^(?:no|nope|actually|correction|that s not|those are not|that is not)\b", text):
        return "correction"
    if re.fullmatch(r"(?:oh )?(?:wow|great|nice|awesome|amazing)(?: you found it)?[!. ]*", text) or \
            re.search(r"\b(?:thank you|thanks|you found it)\b", text):
        return "social"
    if re.search(r"\b(?:this|that|those|these|which one|the \w+ degree|first|second|third)\b", text):
        return "follow_up"
    return "new_task"


def _subject_category(text: str) -> str | None:
    patterns = (
        (r"\b(?:computing|computer science|information technology|computing and it)\b", "Computing & IT"),
        (r"\bengineering\b", "Engineering"),
        (r"\b(?:business|media)\b", "Business & Media"),
        (r"\bhealth(?: sciences?)?\b", "Health Sciences"),
        (r"\b(?:trades?|apprenticeships?)\b", "Trades & Apprenticeships"),
        (r"\btransportation\b", "Transportation"),
        (r"\b(?:applied|natural) sciences?\b", "Applied & Natural Sciences"),
    )
    return next((value for pattern, value in patterns if re.search(pattern, text)), None)


def deterministic_plan(question: str, state: AdvisorV3State) -> V3SemanticPlan:
    """Conservative no-model planner used for tests and dependency fallback."""
    text = _norm(question)
    act = classify_turn(question, state)
    if act == "social":
        return _blank_plan(speech_act=act, task="social_ack", target_domain="social", answer_shape="single")
    if act == "confirmation":
        action = state.prior_answer_intent.offered_action
        return _blank_plan(
            speech_act=act, task=action.action if action else "clarification_response",
            target_domain="program", referent_source="offered_action",
            referent_value=action.result_set_id if action else None,
            reuse_prior_results=bool(action and action.result_set_id),
            answer_shape="exhaustive" if action and action.action == "list_all" else "single",
        )

    exact_id = next((token.upper() for token in re.findall(r"\b[A-Za-z0-9]{5,12}\b", question)
                     if any(c.isalpha() for c in token) and any(c.isdigit() for c in token)), None)
    category = _subject_category(text)
    filters: list[V3Filter] = []
    if re.search(r"\bmaster(?:'s|s)?(?: degrees?)?\b", question, re.I):
        filters.append(V3Filter(field="credential", value="master"))
    if "nursing" in text:
        filters.append(V3Filter(field="subject", value="nursing"))
    elif "aviation" in text:
        filters.append(V3Filter(field="subject", value="aviation"))

    if "campus" in text:
        return _blank_plan(speech_act=act, task="count" if "how many" in text or "count" in text else "campus_info",
                           target_domain="campus", target_category="campus", answer_shape="single")
    if exact_id:
        course_like = bool(re.fullmatch(r"[A-Za-z]{2,6}\d{3,4}", exact_id)) and not exact_id.startswith("M")
        return _blank_plan(speech_act=act, task="course_lookup" if course_like else "details",
                           target_domain="course" if course_like else "program", target_entity=exact_id,
                           referent_source="exact_id", referent_value=exact_id, answer_shape="single")

    eligibility = bool(re.search(r"\b(?:do i have|do i meet|am i eligible|do i qualify|eligible for|requirements for)\b", text))
    if eligibility:
        target = re.split(r"\b(?:eligible for|qualify for|requirements for)\b", question, flags=re.I)[-1].strip(" ?.,")
        return _blank_plan(speech_act=act, task="eligibility", target_domain="program",
                           target_entity=target, referent_source="current_message",
                           referent_value=target, answer_shape="single")

    if "red seal" in text and re.search(r"\b(?:programs?|pathways?|options?)\b", text):
        return _blank_plan(speech_act=act, task="discover", target_domain="program",
                           target_category="Red Seal", referent_source="current_message",
                           answer_shape="grouped")

    if "international" in text:
        if "not available" in text or "unavailable" in text:
            filters.append(V3Filter(field="international_status", value="not_available"))
        elif re.search(r"\bwhich (?:ones?|programs?) (?:are )?available\b", text):
            filters.append(V3Filter(field="international_status", value="available"))
        entity_ref = None
        source = "current_message"
        if re.search(r"\b(?:this|that|the) program\b", text) and state.active_entities.program_id:
            entity_ref, source = state.active_entities.program_id, "active_entity"
        return _blank_plan(speech_act=act, task="international_availability", target_domain="program",
                           target_entity=entity_ref, target_category=category or next((f.value for f in filters if f.field == "subject"), None),
                           referent_source=source, referent_value=entity_ref, filters=filters,
                           answer_shape="summary")

    exhaustive = bool(re.search(r"\b(?:list|show) all(?: \d+)? programs?\b|\bevery program\b|\bfull list\b", text))
    if exhaustive:
        prior = state.recent_result_sets[0] if state.recent_result_sets else None
        return _blank_plan(speech_act=act, task="list_all", target_domain="program",
                           target_category=category, referent_source="prior_set" if prior else "current_message",
                           referent_value=prior.result_set_id if prior else None, filters=filters,
                           reuse_prior_results=prior is not None, answer_shape="exhaustive")

    if re.search(r"\b(?:which one|the (?:master(?:'s|s)?|bachelor(?:'s|s)?|diploma|certificate) degree|first|second|third)\b", question, re.I):
        value = next((word for word in ("master", "bachelor", "diploma", "certificate") if word in text), text)
        return _blank_plan(speech_act=act, task="select", target_domain="program",
                           referent_source="prior_set", referent_value=value,
                           reuse_prior_results=True, answer_shape="single")

    if re.search(r"\b(?:this|that|the) program\b", text) and state.active_entities.program_id:
        task = "requirements" if "requirement" in text else "details"
        return _blank_plan(speech_act=act, task=task, target_domain="program",
                           target_entity=state.active_entities.program_id, referent_source="active_entity",
                           referent_value=state.active_entities.program_id, answer_shape="single")

    looks_like_pasted_name = (
        len(text.split()) >= 2
        and not re.search(r"\b(?:what|which|list|show|do you|does bcit|any|have|offer|find)\b", text)
        and not (category and len(text.split()) <= 3)
        and not any(item.field == "credential" for item in filters)
    )
    if looks_like_pasted_name:
        return _blank_plan(speech_act=act, task="details", target_domain="program",
                           target_entity=question.strip(), referent_source="current_message",
                           referent_value=question.strip(), answer_shape="single")

    if filters or category or re.search(r"\b(?:programs?|degrees?)\b", text):
        task = "filter" if filters and (act == "correction" or category) else "discover"
        return _blank_plan(speech_act=act, task=task, target_domain="program",
                           target_category=category, referent_source="current_message",
                           filters=filters, reuse_prior_results=False, answer_shape="grouped")

    if re.search(r"\b(?:hi|hello|hey)\b", text):
        return _blank_plan(speech_act="social", task="social_ack", target_domain="social", answer_shape="single")
    return _blank_plan(speech_act=act, task="unknown", target_domain="unknown",
                       clarification="What BCIT program, course, or topic would you like help with?",
                       answer_shape="clarification")


class V3ReadOnlyAdapter:
    def __init__(self, legacy_repository: AdvisorV2Repository | None = None):
        self.repo = legacy_repository or AdvisorV2Repository()

    def exact_program(self, reference: str) -> dict[str, Any]:
        compact = reference.strip().upper()
        normalized = _norm(reference)
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT program_id, program_name, credential, study_mode, campus,
                              delivery_method, source_url
                       FROM programs WHERE status='Active'
                         AND (program_id=%s OR lower(program_name)=lower(%s))
                       ORDER BY CASE WHEN program_id=%s THEN 0 ELSE 1 END""",
                    (compact, reference.strip(), compact),
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return {"status": "data_unavailable", "capability": "exact_program", "data": None,
                    "evidence_ids": [], "detail": type(error).__name__}
        items = [dict(zip(("program_id", "program_name", "credential", "study_mode", "campus", "delivery_method", "source_url"), row)) for row in rows]
        if len(items) == 1:
            return {"status": "found", "capability": "exact_program", "data": items[0],
                    "evidence_ids": [f"program:{items[0]['program_id']}"], "detail": None}
        if len(items) > 1:
            return {"status": "ambiguous", "capability": "exact_program", "data": {"programs": items},
                    "evidence_ids": [f"program:{x['program_id']}" for x in items], "detail": "duplicate_name"}
        return {"status": "not_found", "capability": "exact_program", "data": None, "evidence_ids": [], "detail": None}

    def filtered_programs(self, category: str | None, filters: list[V3Filter]) -> dict[str, Any]:
        base = self.repo.list_programs_by_area(category) if category else None
        try:
            if base and base["status"] != "found":
                return base
            if base:
                rows = base["data"]["programs"]
            else:
                with get_connection() as connection, connection.cursor() as cursor:
                    cursor.execute("""SELECT program_id, program_name, credential, study_mode, campus,
                                             delivery_method, source_url
                                      FROM programs WHERE status='Active' ORDER BY program_name, program_id""")
                    rows = [dict(zip(("program_id", "program_name", "credential", "study_mode", "campus", "delivery_method", "source_url"), row))
                            for row in cursor.fetchall()]
        except psycopg.Error as error:
            return {"status": "data_unavailable", "capability": "filtered_programs", "data": None,
                    "evidence_ids": [], "detail": type(error).__name__}
        for item in filters:
            value = _norm(item.value)
            if item.field == "credential" and value == "master":
                rows = [row for row in rows if re.search(r"\bmaster(?:'s)?\b", str(row.get("credential") or ""), re.I)]
            elif item.field == "subject":
                rows = [row for row in rows if value in _norm(str(row.get("program_name") or ""))]
            elif item.field in {"campus", "study_mode"}:
                rows = [row for row in rows if value in _norm(str(row.get(item.field) or ""))]
        return {"status": "found" if rows else "not_found", "capability": "filtered_programs",
                "data": {"programs": rows, "total": len(rows), "category": category},
                "evidence_ids": [f"program:{row['program_id']}" for row in rows], "detail": None}


def compact_state(state: AdvisorV3State) -> dict[str, Any]:
    offer = state.prior_answer_intent.offered_action
    return {
        "turn_index": state.turn_index,
        "active_entities": state.active_entities.model_dump(),
        "recent_result_sets": [
            {"result_set_id": item.result_set_id, "entity_type": item.entity_type,
             "ids": item.ids[:20], "total": item.total, "task": item.task,
             "category": item.category, "filters": item.filters}
            for item in state.recent_result_sets[:3]
        ],
        "unresolved_references": state.unresolved_references,
        "current_task_thread": state.current_task_thread.model_dump(),
        "prior_answer_intent": {
            "task": state.prior_answer_intent.task,
            "answer_shape": state.prior_answer_intent.answer_shape,
            "offered_action": offer.model_dump() if offer else None,
        },
    }


def choose_plan(question: str, state: AdvisorV3State, language_layer: SolV3LanguageLayer | None) -> tuple[V3SemanticPlan, dict[str, int], str, str | None]:
    fallback = deterministic_plan(question, state)
    if language_layer is None:
        return fallback, {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0}, "deterministic", "model_unavailable"
    try:
        proposal, usage = language_layer.plan({"current_message": question, "typed_state": compact_state(state)})
        # Deterministic invariants override unsafe semantic proposals, not ordinary meaning.
        act = classify_turn(question, state)
        if act in {"confirmation", "social"}:
            proposal = fallback
        elif fallback.referent_source == "exact_id":
            proposal.referent_source = "exact_id"
            proposal.referent_value = fallback.referent_value
            proposal.target_entity = fallback.target_entity
        elif fallback.task == "list_all" and fallback.reuse_prior_results:
            proposal = fallback
        elif fallback.target_category and proposal.target_category is None:
            proposal.target_category = fallback.target_category
        # Explicit deterministic constraints extracted from the current message
        # are mandatory even when Sol omits them. This is compiler validation,
        # not a competing answer path.
        if fallback.task != "unknown":
            proposal.speech_act = fallback.speech_act
            proposal.task = fallback.task
            proposal.target_domain = fallback.target_domain
            proposal.answer_shape = fallback.answer_shape
            if fallback.referent_source in {"current_message", "active_entity", "prior_set", "offered_action"}:
                proposal.referent_source = fallback.referent_source
                proposal.referent_value = fallback.referent_value
                proposal.target_entity = fallback.target_entity
        if fallback.target_category:
            proposal.target_category = fallback.target_category
        if fallback.filters:
            merged = {item.field: item for item in proposal.filters}
            for item in fallback.filters:
                merged[item.field] = item
            proposal.filters = list(merged.values())
        if fallback.reuse_prior_results:
            proposal.reuse_prior_results = True
            proposal.referent_source = fallback.referent_source
            proposal.referent_value = fallback.referent_value
        return proposal, usage, "sol", None
    except Exception as error:
        return fallback, {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0}, "deterministic", type(error).__name__


def _latest_set(state: AdvisorV3State, result_set_id: str | None = None) -> DurableResultSetV3 | None:
    if result_set_id:
        return next((item for item in state.recent_result_sets if item.result_set_id == result_set_id), None)
    return state.recent_result_sets[0] if state.recent_result_sets else None


def resolve_referent(plan: V3SemanticPlan, state: AdvisorV3State, adapter: V3ReadOnlyAdapter) -> dict[str, Any]:
    source = plan.referent_source
    if plan.task == "list_all" and plan.reuse_prior_results:
        result_set = _latest_set(state, plan.referent_value)
        return {"status": "resolved" if result_set else "unresolved", "source": source,
                "result_set_id": result_set.result_set_id if result_set else None,
                "entity_id": None, "reason": None if result_set else "no_prior_result_set"}
    if source == "offered_action":
        offer = state.prior_answer_intent.offered_action
        valid = bool(offer and offer.offered_turn == state.turn_index and offer.result_set_id)
        return {"status": "resolved" if valid else "unresolved", "source": source,
                "result_set_id": offer.result_set_id if valid else None, "entity_id": None}
    if source == "prior_set":
        result_set = _latest_set(state)
        if not result_set:
            return {"status": "unresolved", "source": source, "reason": "no_prior_result_set"}
        query = _norm(plan.referent_value or "")
        candidates = result_set.rows
        ordinal_map = {"first": 0, "second": 1, "third": 2}
        if query in ordinal_map and len(candidates) > ordinal_map[query]:
            row = candidates[ordinal_map[query]]
            return {"status": "resolved", "source": "ordinal", "entity_id": row.get("program_id"), "result_set_id": result_set.result_set_id}
        credential_word = next((word for word in ("master", "bachelor", "diploma", "certificate") if word in query), None)
        if credential_word:
            matches = [row for row in candidates if credential_word in _norm(str(row.get("credential") or ""))]
        elif len(candidates) == 1 or "which one" in query:
            matches = candidates if len(candidates) == 1 else []
        else:
            matches = [row for row in candidates if query and query in _norm(str(row.get("program_name") or ""))]
        if len(matches) == 1:
            return {"status": "resolved", "source": source, "entity_id": matches[0].get("program_id"), "result_set_id": result_set.result_set_id}
        return {"status": "unresolved", "source": source, "result_set_id": result_set.result_set_id,
                "reason": "ambiguous_prior_set", "candidate_ids": [row.get("program_id") for row in (matches or candidates)][:12]}
    if source == "active_entity" and state.active_entities.program_id:
        return {"status": "resolved", "source": source, "entity_id": state.active_entities.program_id}
    if source == "exact_id" and plan.referent_value:
        exact = adapter.exact_program(plan.referent_value)
        return {"status": "resolved" if exact["status"] == "found" else exact["status"], "source": source,
                "entity_id": exact.get("data", {}).get("program_id") if isinstance(exact.get("data"), dict) else None,
                "retrieval": exact}
    return {"status": "not_applicable", "source": source, "entity_id": None}


def compile_operations(plan: V3SemanticPlan, resolution: dict[str, Any], state: AdvisorV3State) -> list[OperationNodeV3]:
    task = plan.task
    if task == "social_ack":
        return [OperationNodeV3(operation_id="op1", kind="noop")]
    if resolution.get("status") == "unresolved" and plan.referent_source in {"prior_set", "active_entity", "offered_action"}:
        return [OperationNodeV3(operation_id="op1", kind="clarify", inputs={"reason": resolution.get("reason", "unresolved_reference")})]
    if task == "campus_info" or (task == "count" and plan.target_domain == "campus"):
        return [OperationNodeV3(operation_id="op1", kind="campus_directory")]
    if task == "list_all" and (resolution.get("result_set_id") or plan.reuse_prior_results):
        return [OperationNodeV3(operation_id="op1", kind="reuse_result_set",
                                inputs={"result_set_id": resolution.get("result_set_id") or plan.referent_value})]
    if task in {"discover", "filter", "list_all"}:
        if plan.target_category == "Red Seal":
            return [OperationNodeV3(operation_id="op1", kind="red_seal_programs")]
        return [OperationNodeV3(operation_id="op1", kind="catalog_filter",
                                inputs={"category": plan.target_category,
                                        "filters": [item.model_dump() for item in plan.filters]})]
    if task == "international_availability":
        entity_id = resolution.get("entity_id") or plan.target_entity
        if entity_id:
            return [OperationNodeV3(operation_id="op1", kind="international_program", inputs={"program_id": entity_id})]
        return [OperationNodeV3(operation_id="op1", kind="international_family",
                                inputs={"family": plan.target_category or next((f.value for f in plan.filters if f.field == "subject"), ""),
                                        "availability": next((f.value for f in plan.filters if f.field == "international_status"), None)})]
    if task in {"details", "requirements", "eligibility", "select"}:
        entity_id = resolution.get("entity_id")
        nodes: list[OperationNodeV3] = []
        if not entity_id:
            nodes.append(OperationNodeV3(operation_id="op1", kind="resolve_program",
                                         inputs={"reference": plan.target_entity or plan.referent_value or ""}))
            depends = ["op1"]
        else:
            depends = []
        kind = "eligibility" if task == "eligibility" else "program_details"
        nodes.append(OperationNodeV3(operation_id=f"op{len(nodes)+1}", kind=kind,
                                     inputs={"program_id": entity_id}, depends_on=depends))
        return nodes
    if task == "course_lookup":
        return [OperationNodeV3(operation_id="op1", kind="course_lookup", inputs={"reference": plan.target_entity or ""})]
    return [OperationNodeV3(operation_id="op1", kind="clarify", inputs={"reason": "unknown_task"})]


def _evidence_for_rows(rows: list[dict[str, Any]], source: str, prefix: str = "program") -> list[EvidenceV3]:
    result = []
    for row in rows:
        entity_id = str(row.get(f"{prefix}_id") or row.get("campus_key") or "")
        result.append(EvidenceV3(evidence_id=f"{prefix}:{entity_id}", source=source,
                                 entity_id=entity_id, fields=row, status="found"))
    return result


def execute_operations(nodes: list[OperationNodeV3], adapter: V3ReadOnlyAdapter,
                       state: AdvisorV3State, profile: StudentProfileV2) -> tuple[list[dict[str, Any]], list[EvidenceV3], dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    evidence: list[EvidenceV3] = []
    context: dict[str, Any] = {}
    for node in nodes:
        if node.kind == "noop":
            output = {"status": "found", "capability": "noop", "data": {}}
        elif node.kind == "clarify":
            output = {"status": "ambiguous", "capability": "clarify", "data": node.inputs}
        elif node.kind == "campus_directory":
            output = adapter.repo.get_campus_directory()
            if output["status"] == "found":
                evidence += _evidence_for_rows(output["data"]["campuses"], "campuses", "campus")
        elif node.kind == "catalog_filter":
            output = adapter.filtered_programs(node.inputs.get("category"), [V3Filter.model_validate(x) for x in node.inputs.get("filters", [])])
            if output["status"] == "found":
                evidence += _evidence_for_rows(output["data"]["programs"], "programs")
        elif node.kind == "red_seal_programs":
            output = adapter.repo.find_red_seal_programs()
            if output["status"] == "found":
                output["data"]["total"] = len(output["data"]["programs"])
                evidence += _evidence_for_rows(output["data"]["programs"], "academic_rules")
        elif node.kind == "reuse_result_set":
            result_set = _latest_set(state, node.inputs.get("result_set_id"))
            output = ({"status": "found", "capability": "reuse_result_set", "data": {"result_set": result_set.model_dump()}}
                      if result_set else {"status": "not_found", "capability": "reuse_result_set", "data": {}})
            if result_set:
                evidence += _evidence_for_rows(result_set.rows, "durable_result_set", result_set.entity_type)
        elif node.kind == "resolve_program":
            reference = node.inputs["reference"]
            output = adapter.exact_program(reference)
            if output["status"] == "not_found":
                output = adapter.repo.resolve_program(reference)
            if output["status"] == "found":
                context["program_id"] = output["data"]["program_id"]
                evidence += _evidence_for_rows([output["data"]], output["capability"])
            elif output["status"] == "ambiguous":
                rows = output.get("data", {}).get("programs", [])
                context["ambiguous_programs"] = rows
                evidence += _evidence_for_rows(rows, output["capability"])
        elif node.kind == "program_details":
            program_id = node.inputs.get("program_id") or context.get("program_id")
            if program_id:
                output = adapter.repo.get_program_facts(program_id)
            elif context.get("ambiguous_programs"):
                output = {"status": "ambiguous", "capability": "program_details",
                          "data": {"programs": context["ambiguous_programs"], "reason": "ambiguous_program_name"}}
            else:
                output = {"status": "not_found", "capability": "program_details", "data": {}}
            if output["status"] == "found":
                context["program_id"] = output["data"]["program_id"]
                evidence += _evidence_for_rows([output["data"]], "program_facts")
        elif node.kind == "eligibility":
            program_id = node.inputs.get("program_id") or context.get("program_id")
            facts = adapter.repo.get_program_facts(program_id) if program_id else {"status": "not_found"}
            output = adapter.repo.evaluate_admission(program_id, profile) if program_id else {"status": "not_found", "capability": "evaluate_admission", "data": {}}
            if facts.get("status") == "found":
                evidence += _evidence_for_rows([facts["data"]], "program_facts")
            if output["status"] == "found":
                context["program_id"] = program_id
                evidence.append(EvidenceV3(evidence_id=f"eligibility:{program_id}", source="deterministic_academic_rules",
                                           entity_id=program_id, fields={"status": output["data"]["status"],
                                           "status_counts": output["data"].get("status_counts", {}),
                                           "needed_student_fields": output["data"].get("needed_student_fields", [])}, status=output["data"]["status"]))
        elif node.kind == "international_family":
            output = adapter.repo.get_international_availability(node.inputs.get("family", ""))
            if output["status"] == "found":
                availability = node.inputs.get("availability")
                rows = output["data"]["programs"]
                if availability == "not_available":
                    rows = [row for row in rows if "not available" in _norm(str(row.get("international_eligibility") or ""))]
                elif availability == "available":
                    rows = [row for row in rows if "accepted available" in _norm(str(row.get("international_eligibility") or ""))]
                output["data"]["programs"] = rows
                output["data"]["total"] = len(rows)
                output["status"] = "found" if rows else "not_found"
                evidence += _evidence_for_rows(rows, "program_delivery")
        elif node.kind == "international_program":
            output = adapter.repo.get_program_international_availability(node.inputs["program_id"])
            if output["status"] == "found":
                context["program_id"] = output["data"]["program_id"]
                evidence += _evidence_for_rows([output["data"]], "program_delivery")
        elif node.kind == "course_lookup":
            output = adapter.repo.get_course_facts(node.inputs["reference"])
            if output["status"] == "found":
                evidence += _evidence_for_rows([output["data"]], "course_facts", "course")
        else:
            output = {"status": "not_found", "capability": node.kind, "data": {}}
        outputs.append({"operation_id": node.operation_id, **output})
    return outputs, evidence, context


def _new_result_set(plan: V3SemanticPlan, rows: list[dict[str, Any]], turn: int) -> DurableResultSetV3:
    total = len(rows)
    bounded_rows = rows[:100]
    ids = [str(row.get("program_id") or row.get("course_id") or row.get("campus_key")) for row in bounded_rows]
    digest = hashlib.sha256((str(turn) + "|" + "|".join(ids)).encode()).hexdigest()[:12]
    entity_type = "program" if any("program_id" in row for row in rows) else ("course" if any("course_id" in row for row in rows) else "campus")
    return DurableResultSetV3(result_set_id=f"rs-{digest}", entity_type=entity_type, ids=ids, rows=bounded_rows,
                              task=plan.task, category=plan.target_category,
                              filters={item.field: item.value for item in plan.filters}, total=total, created_turn=turn)


def deterministic_answer(question: str, plan: V3SemanticPlan, outputs: list[dict[str, Any]],
                         evidence: list[EvidenceV3], resolution: dict[str, Any]) -> tuple[str, OfferedActionV3 | None, dict[str, Any]]:
    if plan.task == "social_ack":
        return "Glad we found it!", None, {"kind": "social", "status": "acknowledged"}
    if not outputs or outputs[-1]["status"] in {"not_found", "data_unavailable"}:
        status = outputs[-1]["status"] if outputs else "not_found"
        return ("I couldn't find that in the current BCIT records." if status == "not_found" else
                "The academic data is temporarily unavailable."), None, {"kind": "retrieval", "status": status}
    if outputs[-1]["status"] == "ambiguous":
        ids = resolution.get("candidate_ids", [])
        suffix = f" Candidate IDs: {', '.join(ids)}." if ids else ""
        return "I need a more specific program name or selection." + suffix, None, {"kind": "clarification", "status": "ambiguous"}

    data = outputs[-1].get("data") or {}
    if plan.target_domain == "campus":
        campuses = data.get("campuses", [])
        if plan.task == "count":
            return f"BCIT has {len(campuses)} active campuses in the campus directory.", None, {"kind": "count", "status": "found", "count": len(campuses)}
        return "BCIT's active campuses are:\n" + "\n".join(f"• {row['official_name']} — {row['city']}" for row in campuses), None, {"kind": "campus", "status": "found"}

    if plan.task in {"discover", "filter", "list_all"} or outputs[-1].get("capability") == "reuse_result_set":
        result_set = data.get("result_set")
        rows = result_set.get("rows", []) if result_set else data.get("programs", [])
        total = result_set.get("total", len(rows)) if result_set else data.get("total", len(rows))
        if plan.answer_shape == "exhaustive":
            return f"All {total} matching programs:\n" + "\n".join(
                f"• {row['program_name']} — {row.get('credential') or 'Credential not recorded'} ({row['program_id']})" for row in rows
            ), None, {"kind": "program_set", "status": "found", "count": total}
        groups = Counter(str(row.get("credential") or "Credential not recorded") for row in rows)
        label = plan.target_category or next((f.value for f in plan.filters if f.field == "subject"), "matching")
        lines = [f"• {credential}: {count}" for credential, count in sorted(groups.items())]
        answer = f"BCIT has {total} active {label} programs, grouped by credential:\n" + "\n".join(lines)
        answer += "\nI can list all of them if you'd like."
        return answer, OfferedActionV3(action="list_all", offered_turn=0), {
            "kind": "program_set", "status": "found", "count": total, "group_counts": dict(groups),
        }

    if plan.task == "international_availability":
        rows = data.get("programs", []) if "programs" in data else [data]
        lower = _norm(question)
        if "not available" in lower or "unavailable" in lower:
            rows = [row for row in rows if "not available" in _norm(str(row.get("international_eligibility") or ""))]
        elif re.search(r"\bavailable\b", lower):
            # Generic family questions show both sides compactly; a request for
            # available-only can be selected explicitly with 'which are available'.
            if re.search(r"\bwhich (?:ones?|programs?) (?:are )?available\b", lower):
                rows = [row for row in rows if "accepted available" in _norm(str(row.get("international_eligibility") or ""))]
        if len(rows) == 1:
            row = rows[0]
            status = row.get("international_eligibility") or "status not recorded"
            return f"{row['program_name']} ({row['program_id']}) is {status}.", None, {"kind": "international", "status": status}
        available = sum("accepted available" in _norm(str(row.get("international_eligibility") or "")) for row in rows)
        unavailable = sum("not available" in _norm(str(row.get("international_eligibility") or "")) for row in rows)
        return f"I found {len(rows)} matching programs: {available} are marked available and {unavailable} are marked not available to international students.", None, {"kind": "international", "status": "found", "count": len(rows)}

    if plan.task == "eligibility":
        status = data.get("status", "evidence_unavailable")
        facts = next((item.fields for item in evidence if item.source == "program_facts"), {})
        name = facts.get("program_name") or data.get("program_id") or "that program"
        counts = data.get("status_counts", {})
        if status == "met":
            answer = f"Based on the structured admission rules and the details you provided, you meet the modeled requirements for {name}."
        elif status == "unmet":
            answer = f"Based on the structured admission rules, you do not meet all modeled requirements for {name}."
        elif status == "missing_student_information":
            needed = ", ".join(data.get("needed_student_fields", [])) or "additional student information"
            answer = f"I can't complete the eligibility check for {name} yet. I still need: {needed}."
        else:
            answer = f"The structured check for {name} requires BCIT review before a final decision."
        return answer + f" Rule results: {counts}.", None, {"kind": "eligibility", "status": status}

    row = data
    if "program_name" in row:
        details = [f"{row['program_name']} ({row['program_id']})", str(row.get("credential") or "")]
        if row.get("study_mode"): details.append(str(row["study_mode"]))
        if row.get("campus"): details.append(f"Campus: {row['campus']}")
        return " — ".join(item for item in details if item), None, {"kind": "program", "status": "found"}
    if "course_name" in row:
        return f"{row['course_name']} ({row['course_id']}) — {row.get('credits')} credits.", None, {"kind": "course", "status": "found"}
    return "I found the requested record.", None, {"kind": "retrieval", "status": "found"}


def validate_grounding(answer: str, evidence: list[EvidenceV3], decision: dict[str, Any],
                       declared_ids: list[str] | None = None, *, links_requested: bool = False) -> tuple[bool, str | None]:
    allowed_ids = {item.evidence_id for item in evidence}
    if declared_ids is not None and (not declared_ids or any(item not in allowed_ids for item in declared_ids)):
        return False, "unknown_evidence_id"
    packet = json.dumps({"evidence": [item.model_dump() for item in evidence], "decision": decision}, default=str)
    allowed_numbers = {float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", packet)}
    for value in re.findall(r"\b\d+(?:\.\d+)?\b", answer):
        if float(value) not in allowed_numbers:
            return False, "unsupported_number"
    urls = re.findall(r"https?://\S+", answer)
    if urls and not links_requested:
        return False, "unrequested_url"
    for url in urls:
        if url.rstrip(".,)") not in packet:
            return False, "unsupported_url"
    known_entity_ids = {item.entity_id for item in evidence if item.entity_id}
    for candidate in re.findall(r"\(([A-Z0-9]{5,12})\)", answer):
        if candidate not in known_entity_ids:
            return False, "unsupported_entity_id"
    if decision.get("kind") == "eligibility":
        norm = _norm(answer)
        status = decision.get("status")
        if status == "met" and "meet the modeled requirements" not in norm:
            return False, "eligibility_status_changed"
        if status == "unmet" and not any(x in norm for x in ("do not meet", "does not meet", "not meet")):
            return False, "eligibility_status_changed"
    return True, None


def transition_state(state: AdvisorV3State, plan: V3SemanticPlan, resolution: dict[str, Any],
                     outputs: list[dict[str, Any]], evidence: list[EvidenceV3], context: dict[str, Any],
                     profile: StudentProfileV2, provenance: dict[str, list[dict[str, Any]]],
                     offered_action: OfferedActionV3 | None) -> AdvisorV3State:
    new = state.model_copy(deep=True)
    new.turn_index += 1
    new.student_profile = profile
    new.student_assertion_provenance = provenance
    if plan.task != "social_ack":
        new.prior_answer_intent = PriorAnswerIntentV3(task=plan.task, answer_shape=plan.answer_shape)
    rows: list[dict[str, Any]] = []
    if outputs:
        data = outputs[-1].get("data") or {}
        rows = data.get("programs", []) or data.get("courses", []) or data.get("campuses", [])
        if data.get("result_set"):
            rows = data["result_set"].get("rows", [])
    if rows and (plan.task in {"discover", "filter", "international_availability", "list_all"}
                 or outputs[-1].get("status") == "ambiguous"):
        result_set = _new_result_set(plan, rows, new.turn_index)
        new.recent_result_sets = [result_set] + [item for item in new.recent_result_sets if item.result_set_id != result_set.result_set_id][:7]
        new.current_task_thread = TaskThreadV3(task=plan.task, domain=plan.target_domain,
                                               category=plan.target_category, result_set_id=result_set.result_set_id)
        if offered_action:
            offered_action.result_set_id = result_set.result_set_id
            offered_action.offered_turn = new.turn_index
            new.prior_answer_intent.offered_action = offered_action
        if result_set.entity_type == "program":
            new.active_entities.program_id = result_set.ids[0] if len(result_set.ids) == 1 else None
    elif plan.task != "social_ack":
        new.current_task_thread = TaskThreadV3(task=plan.task, domain=plan.target_domain,
                                               category=plan.target_category,
                                               result_set_id=resolution.get("result_set_id"))
        new.prior_answer_intent.offered_action = None
    program_id = context.get("program_id") or resolution.get("entity_id")
    if program_id:
        new.active_entities.program_id = program_id
    course = next((item.entity_id for item in evidence if item.evidence_id.startswith("course:")), None)
    if course:
        new.active_entities.course_id = course
    if outputs and outputs[-1].get("status") == "ambiguous":
        marker = outputs[-1].get("data", {}).get("reason", "unresolved_reference")
        new.unresolved_references = [marker] + new.unresolved_references[:7]
    else:
        new.unresolved_references = []
    return new


def _state_diff(before: AdvisorV3State, after: AdvisorV3State) -> dict[str, Any]:
    a, b = before.model_dump(), after.model_dump()
    return {key: {"before": a.get(key), "after": b.get(key)} for key in b if a.get(key) != b.get(key)}


def answer_advisor_v3(question: str, *, conversation_state: AdvisorV3State | None = None,
                      language_layer: SolV3LanguageLayer | None = None,
                      repository: AdvisorV2Repository | None = None) -> dict[str, Any]:
    state = (conversation_state or AdvisorV3State()).model_copy(deep=True)
    adapter = V3ReadOnlyAdapter(repository)
    plan, plan_usage, planner_mode, planner_fallback = choose_plan(question, state, language_layer)
    profile, profile_changes, profile_conflicts, provenance = _merge_profile(
        state.student_profile, None, question, provenance=state.student_assertion_provenance,
        turn_index=state.turn_index + 1, source="current_message",
    )
    resolution = resolve_referent(plan, state, adapter)
    graph = compile_operations(plan, resolution, state)
    outputs, evidence, context = execute_operations(graph, adapter, state, profile)
    canonical, offered, decision = deterministic_answer(question, plan, outputs, evidence, resolution)
    links_requested = bool(re.search(r"\b(?:link|url|website|source)\b", _norm(question)))
    answer = canonical
    synth_usage = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0}
    synthesis_mode = "deterministic"
    synthesis_fallback = None
    # Exhaustive lists and clarifications stay deterministic to guarantee shape.
    if language_layer is not None and plan.answer_shape != "exhaustive" and plan.task not in {"social_ack"}:
        try:
            synthesis, synth_usage = language_layer.synthesize({
                "current_message": question, "plan": plan.model_dump(),
                "answer_shape": plan.answer_shape, "evidence": [item.model_dump() for item in evidence],
                "deterministic_outcome": decision, "deterministic_fallback": canonical,
            })
            if synthesis.answer_text:
                valid, reason = validate_grounding(synthesis.answer_text, evidence, decision, synthesis.evidence_ids,
                                                   links_requested=links_requested)
                if valid:
                    answer, synthesis_mode = synthesis.answer_text, "sol"
                else:
                    synthesis_fallback = reason
            else:
                synthesis_fallback = "empty_synthesis"
        except Exception as error:
            synthesis_fallback = type(error).__name__
    grounded, grounding_reason = validate_grounding(answer, evidence, decision, links_requested=links_requested)
    if not grounded:
        answer = canonical
        synthesis_mode = "deterministic"
        synthesis_fallback = synthesis_fallback or grounding_reason
        grounded, grounding_reason = validate_grounding(answer, evidence, decision, links_requested=links_requested)
    new_state = transition_state(state, plan, resolution, outputs, evidence, context, profile, provenance, offered)
    usage = {key: plan_usage.get(key, 0) + synth_usage.get(key, 0)
             for key in ("input_tokens", "cached_tokens", "output_tokens")}
    usage.update({"model": MODEL, "reasoning_effort": REASONING_EFFORT,
                  "calls": int(sum(plan_usage.values()) > 0) + int(sum(synth_usage.values()) > 0),
                  "calls_attempted": int(language_layer is not None) + int(language_layer is not None and plan.answer_shape != "exhaustive" and plan.task != "social_ack")})
    trace = {
        "speech_act": plan.speech_act,
        "plan": plan.model_dump(),
        "referent_resolution": resolution,
        "state_read": compact_state(state),
        "state_write_diff": _state_diff(state, new_state),
        "operation_graph": [item.model_dump() for item in graph],
        "evidence_ids": [item.evidence_id for item in evidence],
        "evidence_count": len(evidence),
        "evaluator_result": decision,
        "planner_mode": planner_mode,
        "synthesis_mode": synthesis_mode,
        "grounding_result": "grounded" if grounded else "failed",
        "fallback_reason": synthesis_fallback or planner_fallback,
        "profile_changes": profile_changes,
        "profile_conflicts": profile_conflicts,
    }
    return {
        "answer": answer,
        "conversation_state": new_state.model_dump(mode="json"),
        "plan": plan.model_dump(),
        "operations": outputs,
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "verification": {"status": "grounded" if grounded else "failed", "reason": grounding_reason},
        "usage": usage,
        "developer_trace": trace,
    }
