"""Bounded GPT-5.6 Sol language boundaries for advisor v3.

Sol proposes a strict semantic plan and may phrase already-verified evidence. It
does not resolve catalog entities, execute operations, decide academic outcomes,
or mutate conversation state.
"""
from __future__ import annotations

import json
import os
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from production_config import SETTINGS


MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "medium"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class V3Filter(StrictModel):
    field: Literal["credential", "subject", "international_status", "campus", "study_mode"]
    value: str = Field(min_length=1, max_length=120)


class V3StudentFact(StrictModel):
    field: Literal[
        "grade", "credential", "credential_gpa", "work_experience_months",
        "red_seal_trade", "gpa", "international_status", "credential_country",
    ]
    key: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=160)


class V3SemanticPlan(StrictModel):
    speech_act: Literal[
        "new_task", "follow_up", "confirmation", "correction", "clarification", "social",
    ]
    task: Literal[
        "discover", "list_all", "count", "select", "filter", "details", "compare",
        "eligibility", "requirements", "course_lookup", "campus_info",
        "international_availability", "clarification_response", "social_ack", "unknown",
    ]
    target_domain: Literal["program", "course", "campus", "institution", "social", "unknown"]
    target_entity: str | None = Field(default=None, max_length=220)
    target_category: str | None = Field(default=None, max_length=120)
    referent_source: Literal[
        "current_message", "prior_set", "active_entity", "ordinal", "exact_id", "offered_action", "none",
    ]
    referent_value: str | None = Field(default=None, max_length=220)
    filters: list[V3Filter] = Field(default_factory=list, max_length=8)
    reuse_prior_results: bool = False
    clarification: str | None = Field(default=None, max_length=240)
    answer_shape: Literal["single", "summary", "grouped", "shortlist", "exhaustive", "clarification"]
    student_facts: list[V3StudentFact] = Field(default_factory=list, max_length=24)


class V3Synthesis(StrictModel):
    answer_text: str | None = Field(default=None, max_length=8000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=120)


PLAN_INSTRUCTIONS = """Plan one BCIT advisor turn. Return only the strict schema.
The CURRENT message always outranks prior state. Classify speech_act first.
Assent such as 'sure', 'yes', or 'okay' is confirmation only when the immediately
preceding offered_action exists; it refers to offered_action and must never be a
search query. Praise or surprise is social and preserves academic context.

Explicit new areas, credentials, program names, course codes, campus questions,
and broad categories start or refine the current task regardless of stale active
entities. 'No, those are not master's degrees' is a correction that preserves the
broad master's-program task and filters by a genuine master's credential. Direct
IDs are exact_id. 'This program' uses active_entity. Ordinals and phrases such as
'which one' or 'the master's degree' use prior_set. Ask for exhaustive output only
for explicit all/every/full/list-all language or accepted exhaustive-list offer.

Use institutional area categories for broad Computing, Engineering, Health,
Business, Trades, Transportation, or Applied/Natural Sciences discovery. Use
subject filters for families such as nursing or aviation. A master's request is a
credential filter, not a text search for the word master in program names.

Extract only student assertions explicitly present in the CURRENT message. Sol
may normalize the assertion keys but must not decide eligibility or supply BCIT
facts. Corrections should contain the replacement fact only."""


SYNTHESIS_INSTRUCTIONS = """Write a concise answer using only the supplied typed
evidence and deterministic outcome. Preserve exact program IDs, counts, status
labels, and URLs. Do not invent or infer facts. Respect answer_shape, including a
complete list only for exhaustive. If the packet is insufficient, return null.
List every evidence_id used. Do not mention internal architecture or tracing."""


def _usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    details = getattr(usage, "input_tokens_details", None) if usage else None
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "cached_tokens": int(getattr(details, "cached_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }


class SolV3LanguageLayer:
    def __init__(self, client: OpenAI | None = None):
        self.client = client or OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=SETTINGS.openai_timeout_seconds,
            max_retries=SETTINGS.openai_max_retries,
        )

    def plan(self, payload: dict[str, Any]) -> tuple[V3SemanticPlan, dict[str, int]]:
        response = self.client.responses.parse(
            model=MODEL,
            reasoning={"effort": REASONING_EFFORT},
            instructions=PLAN_INSTRUCTIONS,
            input=json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            text_format=V3SemanticPlan,
            max_output_tokens=SETTINGS.openai_max_output_tokens,
            store=False,
        )
        if response.output_parsed is None:
            raise ValueError("v3_plan_schema_failure")
        return V3SemanticPlan.model_validate(response.output_parsed), _usage(response)

    def synthesize(self, payload: dict[str, Any]) -> tuple[V3Synthesis, dict[str, int]]:
        response = self.client.responses.parse(
            model=MODEL,
            reasoning={"effort": REASONING_EFFORT},
            instructions=SYNTHESIS_INSTRUCTIONS,
            input=json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=str),
            text_format=V3Synthesis,
            max_output_tokens=SETTINGS.openai_max_output_tokens,
            store=False,
        )
        if response.output_parsed is None:
            raise ValueError("v3_synthesis_schema_failure")
        return V3Synthesis.model_validate(response.output_parsed), _usage(response)


def available_v3_layer() -> SolV3LanguageLayer | None:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    enabled = os.getenv("ASTERIS_ADVISOR_V3_SOL", "1").strip().lower() not in {"0", "false", "off"}
    if not enabled or not key or key == "replace-with-secret":
        return None
    return SolV3LanguageLayer()
