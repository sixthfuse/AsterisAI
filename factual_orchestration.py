"""Model-free orchestration policy for factual English advising.

This module deliberately does not retrieve or phrase academic facts.  It records
what the current turn asks, chooses an accuracy lane, and checks that the answer
packet came from evidence compatible with that turn before release.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class AccuracyLane(str, Enum):
    FAST = "FAST"
    NORMAL = "NORMAL"
    DEEP = "DEEP"


@dataclass(frozen=True)
class TurnUnderstanding:
    family: str
    lane: AccuracyLane
    factual: bool
    context_reference: bool
    explicit_current_subject: bool

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["lane"] = self.lane.value
        return value


@dataclass(frozen=True)
class VerificationDecision:
    passed: bool
    reason: str
    evidence_count: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_CAPABILITY = re.compile(
    r"\b(?:how many|what)\s+languages?\s+(?:can|do)\s+you\s+(?:speak|support|understand)\b|"
    r"\b(?:what can you do|how can you help|who are you|are you (?:a )?(?:human|person|bot|ai))\b",
    re.IGNORECASE,
)
_GREETING = re.compile(r"^\s*(?:hello|hi|hey)[.!?]*\s*$", re.IGNORECASE)
_STOP = re.compile(
    r"^\s*(?:stop|quit|exit|cancel|never mind|nevermind|that's all|that is all|"
    r"thanks,? that's all|thank you,? that's all)[.!?]*\s*$",
    re.IGNORECASE,
)
_OFF_TOPIC = re.compile(
    r"\b(?:weather|forecast|world cup|fifa|prime minister|president|election|"
    r"celebrity|movie|music|singer|actor|actress|shakira)\b",
    re.IGNORECASE,
)
_CONTEXT_REFERENCE = re.compile(
    r"\b(?:it|its|itself|this|that|these|those|them|they|their|each one|"
    r"the other one|others|any others|same (?:program|course)|tell me more|more (?:information|details)|"
    r"this program|that program|"
    r"this course|that course|this campus|that campus)\b",
    re.IGNORECASE,
)
_CAMPUS = re.compile(
    r"\b(?:campus(?:es)?|address(?:es)?|phone(?: numbers?)?|telephone|call)\b|"
    r"\b(?:where is|where's|located|location)\b[^?.!]{0,80}"
    r"\b(?:bcit|campus|burnaby|downtown|aerospace|annacis|marine)\b",
    re.IGNORECASE,
)
_COUNT = re.compile(r"\bhow many\b.*\b(?:programs?|courses?|campus(?:es)?)\b", re.IGNORECASE)
_COURSE = re.compile(
    r"\b(?:course|courses|prerequisite|prerequisites|credits?|electives?)\b|"
    r"\b[A-Z]{3,5}[\s\-:_]*\d{4}\b",
    re.IGNORECASE,
)
_PROGRAM = re.compile(
    r"\b(?:program|programs|degree|diploma|certificate|credential|micro-?credential|admission|admissions)\b",
    re.IGNORECASE,
)
_DEEP = re.compile(
    r"\b(?:eligible|eligibility|qualify|can i apply|compare|versus|vs\.?|"
    r"progress|graduate|graduation|what am i missing|what do i still need|"
    r"work experience|international students?)\b",
    re.IGNORECASE,
)
_INSTITUTIONAL = re.compile(
    r"\b(?:tuition|fees?|financial aid|transcript|registration|registrar|"
    r"student services|accessibility|indigenous services|equivalencies|equivalency|"
    r"website|webpage|url|link)\b",
    re.IGNORECASE,
)


def understand_current_turn(question: str, prior_scope: str | None = None) -> TurnUnderstanding:
    """Classify only the current turn; prior state may resolve an explicit reference."""
    text = re.sub(r"\s+", " ", question.strip())
    reference = bool(_CONTEXT_REFERENCE.search(text))
    if _GREETING.fullmatch(text) or _STOP.fullmatch(text):
        return TurnUnderstanding("conversation", AccuracyLane.FAST, False, False, True)
    if _OFF_TOPIC.search(text):
        return TurnUnderstanding("off_topic", AccuracyLane.FAST, False, False, True)
    if _CAPABILITY.search(text):
        return TurnUnderstanding("capability", AccuracyLane.FAST, False, False, True)
    if _COUNT.search(text):
        family = "campus" if re.search(r"\bcampus", text, re.I) else "catalog"
        return TurnUnderstanding(family, AccuracyLane.FAST, True, reference, True)
    if _CAMPUS.search(text):
        return TurnUnderstanding("campus", AccuracyLane.NORMAL, True, reference, True)
    if _DEEP.search(text):
        family = "course" if _COURSE.search(text) and not _PROGRAM.search(text) else "program"
        return TurnUnderstanding(family, AccuracyLane.DEEP, True, reference, True)
    if _COURSE.search(text):
        return TurnUnderstanding("course", AccuracyLane.NORMAL, True, reference, True)
    if _PROGRAM.search(text):
        return TurnUnderstanding("program", AccuracyLane.NORMAL, True, reference, True)
    if _INSTITUTIONAL.search(text):
        return TurnUnderstanding("institutional", AccuracyLane.NORMAL, True, reference, True)
    if reference and prior_scope in {"program", "program_family", "course", "campus", "campus_directory", "global"}:
        family = "campus" if prior_scope in {"campus", "campus_directory"} else (
            "course" if prior_scope == "course" else "program"
        )
        return TurnUnderstanding(family, AccuracyLane.NORMAL, True, True, False)
    return TurnUnderstanding("unknown", AccuracyLane.NORMAL, False, False, False)


def advisor_capability_answer(question: str) -> str | None:
    if not _CAPABILITY.search(question):
        return None
    if re.search(r"\blanguages?\b", question, re.I):
        return (
            "I’m currently certified for English advising. I may understand some other-language "
            "questions, but English is the reliable supported language for this release."
        )
    return (
        "I’m Asteris, an academic advising assistant. I can check verified BCIT program, course, "
        "admission, prerequisite, campus, and international-availability information."
    )


_TOOL_FAMILIES = {
    "campus_information": {"campus", "program"},
    "get_catalog_counts": {"catalog"},
    "find_institutional_resources": {"institutional"},
    "search_courses": {"course"},
    "get_course_details": {"course"},
    "check_course_eligibility": {"course"},
    "search_programs": {"program"},
    "compare_programs": {"program"},
    "get_program_details": {"program", "course"},
    "get_program_level_courses": {"program", "course"},
    "get_program_electives": {"program", "course"},
    "get_program_progression_requirements": {"program"},
    "get_student_program_advice": {"program", "course"},
    "get_student_level_readiness": {"program", "course"},
    "evaluate_program_curriculum": {"program", "course"},
    "evaluate_admission_profile": {"program"},
    "find_programs_by_admission_evidence": {"program"},
}


def verify_answer_packet(
    understanding: TurnUnderstanding,
    result: dict[str, Any],
    *,
    prior_scope: str | None,
    resolved_scope: str | None,
    prior_subject: dict[str, Any] | None = None,
    resolved_subject: dict[str, Any] | None = None,
) -> VerificationDecision:
    """Reject stale-subject and unsupported factual packets before they reach the UI."""
    tools = list(result.get("tools_used") or [])
    verification = result.get("verification") or {}
    evidence_count = int(verification.get("count") or 0)

    if understanding.family == "capability":
        return VerificationDecision(not tools, "capability_answer_is_model_free", evidence_count)
    if understanding.family in {"conversation", "off_topic"}:
        return VerificationDecision(not tools, "conversation_answer_is_model_free", evidence_count)

    identity_fields = (
        "scope", "program_id", "course_id", "scope_query", "result_query",
        "unique_result_program_id", "campus_name", "catalog_kind",
    )
    prior_identity = tuple((prior_subject or {}).get(key) for key in identity_fields)
    resolved_identity = tuple((resolved_subject or {}).get(key) for key in identity_fields)
    inherited = bool(
        prior_scope
        and resolved_scope == prior_scope
        and prior_identity == resolved_identity
        and not understanding.context_reference
    )
    if inherited and understanding.family == "unknown":
        return VerificationDecision(False, "stale_subject_not_authorized_by_current_turn", evidence_count)
    if inherited and prior_scope in {"campus", "campus_directory"} and understanding.family != "campus":
        return VerificationDecision(False, "campus_state_conflicts_with_current_turn", evidence_count)

    # Unknown wording may still resolve to a fresh, verified entity (including
    # existing non-English compatibility).  Enforce tool-family matching only
    # when the current-turn classifier made an affirmative family decision.
    if understanding.family != "unknown":
        resolved_family = {
            "program": "program", "program_family": "program", "global": "program",
            "course": "course", "campus": "campus", "campus_directory": "campus",
        }.get(resolved_scope)
        compatible_families = {understanding.family, resolved_family}
        for tool in tools:
            families = _TOOL_FAMILIES.get(tool)
            if families and not (families & compatible_families):
                return VerificationDecision(False, f"tool_{tool}_does_not_match_{understanding.family}", evidence_count)

    if tools and understanding.factual and not verification:
        # Institutional resources carry their governed records in a separate field.
        if not (tools == ["find_institutional_resources"] and result.get("resources")):
            return VerificationDecision(False, "retrieved_facts_lack_verification_metadata", evidence_count)

    if understanding.factual and result.get("usage") and not tools:
        return VerificationDecision(False, "model_answer_has_no_retrieved_evidence", evidence_count)

    return VerificationDecision(True, "evidence_matches_current_turn", evidence_count)


def orchestration_trace(
    understanding: TurnUnderstanding,
    result: dict[str, Any],
    decision: VerificationDecision,
    *,
    resolved_scope: str | None,
) -> dict[str, Any]:
    return {
        "pipeline": ["UNDERSTAND", "RESOLVE", "RETRIEVE", "VERIFY", "ANSWER"],
        "understand": understanding.as_dict(),
        "resolve": {"scope": resolved_scope, "intent": result.get("intent")},
        "retrieve": {"tools": list(result.get("tools_used") or [])},
        "verify": decision.as_dict(),
        "answer_released": decision.passed,
    }
