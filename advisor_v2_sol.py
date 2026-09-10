"""Grounded GPT-5.6 Sol language boundary for the experimental advisor v2.

Sol plans the student's current task and may write natural advisor prose from a
compact, verified evidence packet. Entity confirmation, retrieval, eligibility,
and post-generation claim validation remain deterministic.
"""
from __future__ import annotations

import os
import re
import json
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from production_config import SETTINGS


MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "medium"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedGrade(_StrictModel):
    subject: str = Field(min_length=1, max_length=100)
    value: float = Field(ge=0, le=100)


class ExtractedCredentialGpa(_StrictModel):
    credential: str = Field(min_length=1, max_length=160)
    value: float = Field(ge=0, le=100)


class ExtractedExperienceMonths(_StrictModel):
    area: str = Field(min_length=1, max_length=100)
    months: float = Field(ge=0, le=1200)


class ExtractedStudentFacts(_StrictModel):
    grades: list[ExtractedGrade] = Field(default_factory=list, max_length=20)
    gpa: float | None = Field(default=None, ge=0, le=100)
    credentials: list[str] = Field(default_factory=list, max_length=10)
    completed_courses: list[str] = Field(default_factory=list, max_length=50)
    documents: list[str] = Field(default_factory=list, max_length=30)
    assessments_completed: list[str] = Field(default_factory=list, max_length=30)
    licences: list[str] = Field(default_factory=list, max_length=20)
    work_experience_years: float | None = Field(default=None, ge=0, le=100)
    work_experience_months_by_area: list[ExtractedExperienceMonths] = Field(default_factory=list, max_length=20)
    credential_gpas: list[ExtractedCredentialGpa] = Field(default_factory=list, max_length=20)
    red_seal_trade: str | None = Field(default=None, max_length=120)
    high_school_graduated: bool | None = None
    international_status: Literal["international", "domestic"] | None = None
    credential_country: str | None = Field(default=None, max_length=100)


class AdvisorV2Interpretation(_StrictModel):
    intent: Literal[
        "greeting", "institutional_counts", "campus_information",
        "program_discovery", "program_facts", "course_discovery", "course_facts",
        "admission_requirements", "admission_eligibility",
        "red_seal_options", "international_availability",
        "institutional_decision", "unknown",
    ]
    question_class: Literal[
        "greeting", "institutional_counts", "campus_information",
        "program_discovery", "program_facts", "course_discovery", "course_facts",
        "admission_requirements", "admission_eligibility",
        "red_seal_options", "international_availability",
        "admission_decision", "unknown",
    ]
    program_reference: str | None = Field(default=None, max_length=180)
    subject_area: str | None = Field(default=None, max_length=100)
    course_reference: str | None = Field(default=None, max_length=100)
    student_facts: ExtractedStudentFacts = Field(default_factory=ExtractedStudentFacts)
    reference_behavior: Literal[
        "explicit_new_subject", "follow_up_program", "follow_up_course",
        "ordinal_candidate", "no_reference",
    ]
    ordinal_candidate: int | None = Field(default=None, ge=1, le=100)
    clarification_needed: bool
    clarification_reason: str | None = Field(default=None, max_length=180)
    scope: Literal[
        "institution", "campus_directory", "program_area", "program_family",
        "program", "course", "unknown",
    ] = "unknown"
    requested_facts: list[Literal[
        "campus_count", "campus_details", "program_count", "course_count",
        "main_campus", "phone", "program_list", "course_list", "admission_requirements", "eligibility",
        "international_availability", "red_seal_pathways",
    ]] = Field(default_factory=list, max_length=8)
    operation: Literal[
        "list", "count", "select", "filter", "compare", "details",
        "eligibility", "clarify", "follow_up",
    ] = "details"
    subject: str | None = Field(default=None, max_length=180)
    entity_category: Literal[
        "institution", "campus", "program", "program_set", "course",
        "course_set", "admission", "unknown",
    ] = "unknown"
    constraints: list[str] = Field(default_factory=list, max_length=12)
    referent: str | None = Field(default=None, max_length=180)
    answer_shape: Literal[
        "single_answer", "shortlist", "grouped_summary", "exhaustive_list",
        "explanation",
    ] = "explanation"
    correction: bool = False


class AdvisorV2SynthesisPlan(_StrictModel):
    # Legacy presentation fields remain optional for test doubles and safe
    # fallback compatibility. Live synthesis uses answer_text + claim_ids.
    opening: Literal["none", "direct", "supportive"] = "none"
    fact_ids: list[str] = Field(default_factory=list, max_length=100)
    closing: Literal[
        "none", "invite_follow_up", "ask_program_name",
        "ask_missing_information", "confirm_with_bcit",
    ] = "none"
    answer_text: str | None = Field(default=None, max_length=6000)
    claim_ids: list[str] = Field(default_factory=list, max_length=100)


INTERPRETATION_INSTRUCTIONS = """You create the semantic execution plan for one
BCIT advisor message. Return only the strict schema. Interpret the CURRENT
message into operation, subject, entity_category, constraints, referent,
answer_shape, and correction. Then populate the compatibility intent fields.
Prior result objects are for resolving references, never for overriding an
explicit new subject. Direct pasted names and codes are explicit subjects.
Understand multilingual student language directly; preserve the meaning of an
academic area in subject_area without inventing BCIT taxonomy.

Use institutional_counts for counts of all programs/courses or an ambiguous
institution-wide phrase such as 'technology programs'. Use campus_information
for campus counts/details, the main campus, or a campus phone number. Distinguish
course discovery from program discovery from the object the student asks for.
Use program_area only for an institutional area such as Engineering or Computing
& IT; use program_family for a subject family such as nursing or aviation; use
program for a specific named program such as Mechanical Engineering or Aviation
Management and Operations. Use red_seal_options for broad requests asking which
programs accept or mention Red Seal. A request about one named program that asks
whether the student's stated credentials/grades/experience meet requirements is
always admission_eligibility, even if it also mentions Red Seal or uses wording
like 'do I have the requirements'. Use international_availability when an
international student asks which programs in a named family are available.
Corrections or objections that clearly restate an area still mean discovery for
that area. Program/course strings and subject areas are proposals only; the
repository must confirm them.

Use select or filter when the student asks which item in prior results has a
property. Use single_answer for one requested item, grouped_summary for broad
area discovery, shortlist for bounded recommendations, and exhaustive_list only
when the student explicitly asks for all/every/complete. Phrases such as "this
program", "the second one", "the master's degree", and "which one" are
referents, not program search strings. Mark correction when the student rejects
or corrects the prior answer.

Extract student facts only when explicitly stated in the current message. Put a
Red Seal trade in red_seal_trade, each named credential average as a
credential/value record in credential_gpas (name the BCIT Construction Operations
Associate Certificate precisely), and months of experience as an area/months
record in work_experience_months_by_area (use a clear area or GENERAL). Do not
treat a credential average as a school-subject grade. Do not
supply BCIT facts, resolve entities, or decide eligibility."""

SYNTHESIS_INSTRUCTIONS = """Write the direct, natural answer to the student's
CURRENT question using only the supplied verified evidence objects and the
deterministic decision fields. Return only the strict schema. Put the prose in
answer_text and list every evidence id used in claim_ids. You may select,
filter, summarize, group, rank, compare, and explain the supplied evidence. Do
not invent, infer, or soften BCIT facts. Never change an explicit availability
or deterministic eligibility status. Respect answer_shape: a single answer is
one answer; grouped_summary is concise; exhaustive_list is complete. Do not
repeat URLs unless links/details were requested; exact details may include one
official link. Avoid boilerplate about verified records and avoid a generic
follow-up offer when the answer is already complete. If evidence is insufficient,
set answer_text to null so the deterministic safe fallback is used."""


def _usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    details = getattr(usage, "input_tokens_details", None) if usage else None
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "cached_tokens": int(getattr(details, "cached_tokens", 0) or 0),
    }


class SolLanguageLayer:
    """Two small structured-output calls with no tools and no retained response."""

    def __init__(self, client: OpenAI | None = None):
        self.client = client or OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=SETTINGS.openai_timeout_seconds,
            max_retries=SETTINGS.openai_max_retries,
        )

    def interpret(self, payload: dict[str, Any]) -> tuple[AdvisorV2Interpretation, dict[str, int]]:
        response = self.client.responses.parse(
            model=MODEL,
            reasoning={"effort": REASONING_EFFORT},
            instructions=INTERPRETATION_INSTRUCTIONS,
            input=json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            text_format=AdvisorV2Interpretation,
            max_output_tokens=SETTINGS.openai_max_output_tokens,
            store=False,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("interpretation_schema_failure")
        return AdvisorV2Interpretation.model_validate(parsed), _usage(response)

    def synthesize(self, payload: dict[str, Any]) -> tuple[AdvisorV2SynthesisPlan, dict[str, int]]:
        response = self.client.responses.parse(
            model=MODEL,
            reasoning={"effort": REASONING_EFFORT},
            instructions=SYNTHESIS_INSTRUCTIONS,
            input=json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            text_format=AdvisorV2SynthesisPlan,
            max_output_tokens=SETTINGS.openai_max_output_tokens,
            store=False,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("synthesis_schema_failure")
        return AdvisorV2SynthesisPlan.model_validate(parsed), _usage(response)


def available_default_layer() -> SolLanguageLayer | None:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    enabled = os.getenv("ASTERIS_ADVISOR_V2_SOL", "1").strip().lower() not in {"0", "false", "off"}
    if not enabled or not key or key == "replace-with-secret":
        return None
    return SolLanguageLayer()


def compact_interpretation_payload(question: str, state: Any) -> dict[str, Any]:
    """Bounded current-message context; no transcript or retrieved facts."""
    return {
        "message": question[:2_000],
        "prior": {
            "active_kind": state.active_kind,
            "program_id": state.program_id,
            "course_id": state.course_id,
            "discovery_query": state.discovery_query,
            "candidate_program_ids": list(state.candidate_program_ids[:12]),
            "candidate_count": len(state.candidate_program_ids),
            "recent_result_objects": list(state.recent_result_objects[:20]),
            "last_question_class": state.last_question_class,
            "last_answer_shape": state.last_answer_shape,
        },
    }


def render_synthesis(canonical_answer: str, plan: AdvisorV2SynthesisPlan,
                     *, path: str, evaluation_status: str,
                     verification_status: str) -> str:
    """Render only exact deterministic facts plus allow-listed conversational text."""
    fact_lines = [line for line in canonical_answer.splitlines() if line.strip()]
    fact_map = {f"F{index + 1}": line for index, line in enumerate(fact_lines)}
    if plan.fact_ids != list(fact_map):
        raise ValueError("synthesis_fact_set_mismatch")
    if verification_status != "grounded" and plan.opening != "none":
        raise ValueError("synthesis_grounding_opening_not_allowed")
    allowed_closings = {"none", "invite_follow_up"}
    if "clarification" in path:
        allowed_closings.add("ask_program_name")
    if evaluation_status == "missing_student_information":
        allowed_closings.add("ask_missing_information")
    if evaluation_status == "human_review_required" or "decision_boundary" in path:
        allowed_closings.add("confirm_with_bcit")
    if plan.closing not in allowed_closings:
        raise ValueError("synthesis_closing_not_allowed")
    openings = {"none": "", "direct": "Here’s what the verified records show:\n",
                "supportive": "I can help with that. Here’s what the verified records show:\n"}
    closings = {"none": "", "invite_follow_up": "\nYou can ask a follow-up about these results.",
                "ask_program_name": "\nPlease name the program you mean.",
                "ask_missing_information": "\nShare any missing details you know if you want me to check again.",
                "confirm_with_bcit": "\nBCIT must confirm the final decision."}
    return openings[plan.opening] + "\n".join(fact_map[item] for item in plan.fact_ids) + closings[plan.closing]


def validate_grounded_answer(plan: AdvisorV2SynthesisPlan, payload: dict[str, Any]) -> str:
    """Validate the model's declared claims against the exact evidence packet.

    This intentionally validates structured claim attribution rather than hidden
    reasoning. The model never receives facts outside ``evidence`` and every
    declared claim id must exist in that packet. Deterministic statuses must also
    appear verbatim when the answer makes the corresponding decision.
    """
    answer = (plan.answer_text or "").strip()
    if not answer:
        raise ValueError("synthesis_empty_answer")
    evidence = payload.get("evidence") or []
    allowed = {str(item["evidence_id"]) for item in evidence}
    used = list(dict.fromkeys(plan.claim_ids))
    if not used or any(item not in allowed for item in used):
        raise ValueError("synthesis_unknown_claim_id")
    if len(answer) > int(payload.get("max_answer_chars", 6000)):
        raise ValueError("synthesis_answer_too_long")
    decision = payload.get("deterministic_decision") or {}
    required_phrase = decision.get("required_phrase")
    if required_phrase:
        normalized_answer = _norm_text(answer)
        status = decision.get("status")
        if decision.get("kind") == "eligibility" and status == "unmet":
            preserved = any(phrase in normalized_answer for phrase in (
                "not met", "do not meet", "does not meet", "don t meet", "requirements are unmet",
            ))
        elif decision.get("kind") == "eligibility" and status == "met":
            preserved = "requirements are met" in normalized_answer or "meet the modeled requirements" in normalized_answer
        else:
            preserved = _norm_text(required_phrase) in normalized_answer
        if not preserved:
            raise ValueError("synthesis_deterministic_status_changed")
    urls = re.findall(r"https?://\S+", answer)
    if not payload.get("links_requested") and urls:
        raise ValueError("synthesis_unrequested_url")
    evidence_text = " ".join(str(item.get("fact") or item) for item in evidence)
    numeric_source = " ".join((
        evidence_text, str(payload.get("question") or ""),
        " ".join(str(item) for item in (payload.get("task_plan") or {}).get("constraints", [])),
    ))
    evidence_numbers = [float(item.rstrip("%")) for item in re.findall(r"\b\d+(?:\.\d+)?%?\b", numeric_source)]
    answer_numbers = [float(item.rstrip("%")) for item in re.findall(r"\b\d+(?:\.\d+)?%?\b", answer)]
    for number in answer_numbers:
        if not any(abs(number - candidate) <= max(0.01, abs(candidate) * 0.001) for candidate in evidence_numbers):
            raise ValueError("synthesis_unsupported_number")
    if urls and any(url.rstrip(".,)") not in evidence_text for url in urls):
        raise ValueError("synthesis_unsupported_url")
    return answer


def _norm_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def synthesis_payload(result: dict[str, Any]) -> dict[str, Any]:
    lines = [line for line in result["answer"].splitlines() if line.strip()]
    path = result["observability"]["final_response_path"]
    evaluation_status = result["observability"]["rule_evaluation_status"]
    verification_status = result["verification"]["status"]
    allowed_openings = (["none", "direct", "supportive"]
                        if verification_status == "grounded" else ["none"])
    allowed_closings = ["none", "invite_follow_up"]
    if "clarification" in path:
        allowed_closings.append("ask_program_name")
    if evaluation_status == "missing_student_information":
        allowed_closings.append("ask_missing_information")
    if evaluation_status == "human_review_required" or "decision_boundary" in path:
        allowed_closings.append("confirm_with_bcit")
    evidence = result.get("evidence_objects") or [
        {"evidence_id": f"F{index + 1}", "fact": line}
        for index, line in enumerate(lines)
    ]
    task_plan = result.get("observability", {}).get("task_plan") or {}
    return {
        "question": result.get("observability", {}).get("current_message"),
        "task_plan": task_plan,
        "evidence": evidence,
        "deterministic_decision": result.get("deterministic_decision") or {},
        "links_requested": bool(result.get("observability", {}).get("links_requested")),
        "max_answer_chars": 6000,
        "facts": [{"fact_id": f"F{index + 1}", "exact_text": line}
                  for index, line in enumerate(lines)],
        "path": path,
        "retrieval_statuses": [item["status"] for item in result["retrieval"]],
        "evaluation_status": evaluation_status,
        "allowed_openings": allowed_openings,
        "allowed_closings": allowed_closings,
    }


def safe_error_name(error: Exception) -> str:
    name = type(error).__name__
    return re.sub(r"[^A-Za-z0-9_]", "", name)[:80] or "ModelError"
