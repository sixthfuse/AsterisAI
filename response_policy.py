"""General response-depth and language policy for the student advisor."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ResponsePolicy:
    depth: str
    instruction: str


_COMPREHENSIVE = re.compile(
    r"\b(?:comprehensive|in[- ]depth|everything|all (?:the )?(?:details|information)|"
    r"full (?:details|breakdown|curriculum|list)|complete (?:details|list|curriculum))\b",
    re.IGNORECASE,
)
_MORE_INFORMATION = re.compile(
    r"\b(?:tell me more|more (?:about|information|details)|expand|overview)\b",
    re.IGNORECASE,
)
_COMPARISON = re.compile(
    r"\b(?:compare|comparison|difference|different|versus|vs\.?|which (?:one|program))\b",
    re.IGNORECASE,
)
_SIMPLE_FACT = re.compile(
    r"\b(?:how many|how long|where|when|what (?:credential|campus|code|link|url)|"
    r"online or in person|full[- ]time or part[- ]time)\b",
    re.IGNORECASE,
)
_ELIGIBILITY = re.compile(
    r"\b(?:eligible|qualify|admission|admissions|apply|applying|requirement|prerequisite|can i|do i need)\b",
    re.IGNORECASE,
)


def response_policy(question: str, *, comparison: bool = False) -> ResponsePolicy:
    """Choose depth from intent without coupling behavior to benchmark wording."""
    text = question.strip()
    if comparison or _COMPARISON.search(text):
        return ResponsePolicy(
            "comparison",
            "Synthesize the programs against the student's stated criterion. Lead with the "
            "practical difference, then compare only supported attributes. Do not write "
            "separate program profiles or repeat shared facts.",
        )
    if _COMPREHENSIVE.search(text):
        return ResponsePolicy(
            "comprehensive",
            "The student requested comprehensive detail. Give a structured, complete answer "
            "using only relevant verified evidence; detail is appropriate here.",
        )
    if _MORE_INFORMATION.search(text):
        return ResponsePolicy(
            "expanded",
            "Add useful new detail about the active subject. Do not repeat the prior result card "
            "or opening summary. Use a short overview followed by the most relevant details.",
        )
    if _SIMPLE_FACT.search(text):
        return ResponsePolicy(
            "short",
            "Answer the requested fact in the first sentence. Usually stop after one or two "
            "sentences and 60 words unless a condition is essential to accuracy.",
        )
    if _ELIGIBILITY.search(text):
        return ResponsePolicy(
            "concise_conditions",
            "Answer the eligibility question directly, then state only the decisive verified "
            "conditions and the most useful specific next step. Target 160 words and never "
            "exceed 180 words unless "
            "more detail is essential to avoid a misleading answer.",
        )
    return ResponsePolicy(
        "concise",
        "Answer the actual question first and keep supporting detail selective. Offer one "
        "specific next step only when it materially helps.",
    )


def conversation_quality_instructions(policy: ResponsePolicy) -> str:
    """Return stable generation guidance shared across all advising scenarios."""
    return (
        f"Response-depth policy ({policy.depth}): {policy.instruction} "
        "Write like a concise professional academic advisor. Use natural transitions and "
        "plain language around exact program names, course names, and codes. Do not restate "
        "the question, narrate tool use, or repeat information from the immediately preceding "
        "assistant turn unless the student asks for repetition. Avoid generic disclaimers and "
        "the phrase 'available Asteris data' when a specific boundary can be stated. "
        "When the active program was already named, use a short natural reference instead of "
        "repeating its full long title. For an international follow-up after general admission "
        "requirements, state only the international-specific availability, restrictions, and "
        "verification needs; do not restate the general admission list. "
        "Use bullets only when three or more parallel items are genuinely useful; never dump "
        "a curriculum or catalog unless requested or necessary. For comparisons, state the "
        "meaningful differences and shared facts once. For frustration plus a substantive "
        "question, briefly acknowledge the problem and answer it. For a clear stop, stop. "
        "Describe evidence boundaries precisely: distinguish a verified fact, a conditional "
        "rule, missing or unpublished information, and a point requiring institutional "
        "confirmation. Never convert unknown information into a likely yes or no, and never "
        "guarantee admission, transfer credit, licensing, placement, employment, or permits."
    )
