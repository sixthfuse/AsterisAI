"""Semantically planned, PostgreSQL-grounded side-by-side advisor v2 path.

Sol interprets the current message into a bounded plan. Deterministic confirmation
then selects a read-only capability and PostgreSQL records or normalized academic
rules remain the only authority for BCIT facts and eligibility. The existing
production advisor implementation is not imported or changed by this module.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from datetime import date
from decimal import Decimal
import re
import time
import unicodedata
from typing import Any, Literal

import psycopg
from pydantic import BaseModel, Field

from academic_rules import get_course_requirements, get_program_rules
from advisor_v2_sol import (
    MODEL as SOL_MODEL,
    AdvisorV2Interpretation,
    SolLanguageLayer,
    compact_interpretation_payload,
    render_synthesis,
    safe_error_name,
    synthesis_payload,
    validate_grounded_answer,
)
from database import get_connection


RetrievalStatus = Literal["found", "not_found", "ambiguous", "data_unavailable"]
EvaluationStatus = Literal[
    "met", "unmet", "missing_student_information", "human_review_required",
    "evidence_unavailable", "retrieval_failure",
]


class StudentProfileV2(BaseModel):
    """User assertions only; none of these fields are treated as BCIT facts."""

    grades: dict[str, float] = Field(default_factory=dict)
    gpa: float | None = Field(default=None, ge=0, le=100)
    gpa_scale: float = Field(default=100, gt=0, le=100)
    credentials: list[str] = Field(default_factory=list, max_length=20)
    credential_gpas: dict[str, float] = Field(default_factory=dict)
    course_credits: dict[str, float] = Field(default_factory=dict)
    completed_courses: list[str] = Field(default_factory=list, max_length=200)
    admitted_programs: list[str] = Field(default_factory=list, max_length=30)
    subject_sequence_averages: list[float] = Field(default_factory=list, max_length=30)
    work_experience_years: float | None = Field(default=None, ge=0, le=100)
    work_experience_months_by_area: dict[str, float] = Field(default_factory=dict)
    high_school_graduated: bool | None = None
    documents: list[str] = Field(default_factory=list, max_length=30)
    assessments_completed: list[str] = Field(default_factory=list, max_length=30)
    red_seal_trade: str | None = Field(default=None, max_length=120)
    licences: list[str] = Field(default_factory=list, max_length=20)
    international_status: Literal["international", "domestic"] | None = None
    credential_country: str | None = Field(default=None, max_length=100)
    application_date: date | None = None
    intake: str | None = Field(default=None, max_length=30)
    requested_campus: str | None = Field(default=None, max_length=100)
    requested_delivery_mode: str | None = Field(default=None, max_length=100)


class AdvisorV2State(BaseModel):
    version: Literal[1] = 1
    active_kind: Literal["none", "program", "course", "discovery", "campus_directory", "ambiguous"] = "none"
    program_id: str | None = Field(default=None, max_length=64)
    course_id: str | None = Field(default=None, max_length=64)
    discovery_query: str | None = Field(default=None, max_length=300)
    candidate_program_ids: list[str] = Field(default_factory=list, max_length=100)
    recent_result_objects: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    last_answer_shape: str | None = Field(default=None, max_length=40)
    student_profile: StudentProfileV2 = Field(default_factory=StudentProfileV2)
    profile_provenance: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    last_question_class: str | None = Field(default=None, max_length=64)
    turn_index: int = Field(default=0, ge=0)


def _result(status: RetrievalStatus, capability: str, *, data: Any = None,
            evidence_ids: list[str] | None = None, detail: str | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "capability": capability,
        "data": data,
        "evidence_ids": evidence_ids or [],
        "detail": detail,
    }


def _norm(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.lower()))


def _tokens(value: str) -> set[str]:
    ignored = {
        "a", "about", "all", "an", "are", "at", "bcit", "do", "for", "have",
        "in", "is", "list", "me", "of", "please", "program", "programs", "show",
        "s", "tell", "the", "there", "what", "which", "with",
    }
    return {token for token in _norm(value).split() if token not in ignored}


def _credential_markers(value: str) -> set[str]:
    words = set(_norm(value).split())
    markers = words & {"bachelor", "bachelors", "degree", "diploma", "certificate", "master", "masters"}
    if markers & {"bachelor", "bachelors", "degree"}:
        return {"degree"}
    if markers & {"master", "masters"}:
        return {"master"}
    return markers


def _credential_matches(credential: str, markers: set[str]) -> bool:
    value = _norm(credential)
    return all(
        ((marker in value) or (marker == "degree" and ("bachelor" in value or "master" in value)))
        for marker in markers
    )


def _requests_program_collection(question: str) -> bool:
    value = _norm(question)
    return bool(re.search(r"\b(?:programs|all programs|which programs|any programs)\b", value))


def _task_metadata(question: str, interpreted: AdvisorV2Interpretation,
                   previous: AdvisorV2State) -> dict[str, Any]:
    """Normalize the reusable conversational task dimensions for every turn."""
    text = _norm(question)
    correction = interpreted.correction or bool(re.match(r"^(?:no|not that|i mean|actually)\b", text))
    explicit_all = bool(re.search(r"\b(?:list|show)\s+(?:me\s+)?(?:all|every)|\bcomplete list\b|\bexhaustive\b", text))
    operation = interpreted.operation
    if "how many" in text:
        operation = "count"
    elif re.search(r"\b(?:which one|the (?:first|second|third|fourth|last) one|master s degree|master degree)\b", text):
        operation = "select"
    elif interpreted.intent in {"admission_eligibility", "institutional_decision"}:
        operation = "eligibility"
    elif explicit_all or interpreted.intent in {"program_discovery", "course_discovery", "international_availability"}:
        operation = "list" if explicit_all else ("filter" if "international" in text else "list")
    elif interpreted.reference_behavior.startswith("follow_up"):
        operation = "follow_up"
    answer_shape = interpreted.answer_shape
    if operation == "select" or operation == "count":
        answer_shape = "single_answer"
    elif explicit_all:
        answer_shape = "exhaustive_list"
    elif interpreted.scope == "program_area" and operation == "list":
        answer_shape = "grouped_summary"
    elif operation in {"eligibility", "details", "follow_up"}:
        answer_shape = "explanation"
    elif operation in {"list", "filter"}:
        answer_shape = "shortlist"
    constraints = list(interpreted.constraints)
    if "international" in text and "international_status=international" not in constraints:
        constraints.append("international_status=international")
    if "not available" in text or "unavailable" in text or "can t apply" in text or "cannot apply" in text:
        constraints.append("international_available=false")
    referent = interpreted.referent
    if not referent:
        match = re.search(r"\b(this program|that program|the program|which one|the (?:first|second|third|fourth|last) one|the master s degree|master s degree)\b", text)
        referent = match.group(1) if match else None
    subject = interpreted.subject or interpreted.program_reference or interpreted.subject_area or interpreted.course_reference
    return {
        "operation": operation, "subject": subject,
        "entity_category": interpreted.entity_category,
        "constraints": list(dict.fromkeys(constraints)), "referent": referent,
        "answer_shape": answer_shape, "correction": correction,
        "explicit_exhaustive_request": explicit_all,
        "prior_result_count": len(previous.recent_result_objects),
    }


def _result_object(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in (
        "program_id", "program_name", "credential", "study_mode", "campus",
        "delivery_method", "source_url", "international_eligibility",
    ) if row.get(key) is not None}


def _resolve_prior_referent(question: str, previous: AdvisorV2State,
                            task_plan: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Resolve exact/contextual references before any global fuzzy search."""
    rows = previous.recent_result_objects
    text = _norm(question)
    if not rows:
        if previous.program_id and re.search(r"\b(?:this|that|the) program\b", text):
            return {"program_id": previous.program_id}, "active_program_id"
        return None, "none"
    # An exact pasted code or full displayed name always outranks fuzzy search.
    exact = [row for row in rows if (
        _norm(str(row.get("program_id") or "")) in text.split()
        or (_norm(str(row.get("program_name") or "")) and _norm(str(row.get("program_name"))) in text)
    )]
    if len(exact) == 1:
        return exact[0], "prior_result_exact"
    ordinal_words = {"first": 1, "second": 2, "third": 3, "fourth": 4, "last": len(rows)}
    for word, index in ordinal_words.items():
        if re.search(rf"\b(?:the\s+)?{word}\s+one\b", text) and 0 < index <= len(rows):
            return rows[index - 1], "prior_result_ordinal"
    if re.search(r"\bmaster(?:s)?(?: degree)?\b", text):
        matches = [row for row in rows if "master" in _norm(str(row.get("credential") or ""))]
        if len(matches) == 1:
            return matches[0], "prior_result_credential"
    if task_plan["operation"] in {"select", "filter"} and "international_available=false" in task_plan["constraints"]:
        matches = [row for row in rows if "not available" in _norm(str(row.get("international_eligibility") or ""))]
        if len(matches) == 1:
            return matches[0], "prior_result_filter"
    if previous.program_id and re.search(r"\b(?:this|that|the) program\b", text):
        return {"program_id": previous.program_id}, "active_program_id"
    return None, "none"


def _program_score(query: str, row: dict[str, Any]) -> float:
    query_norm = _norm(query)
    name_norm = _norm(row["program_name"])
    if query_norm == name_norm or query_norm == _norm(row["program_id"]):
        return 10.0
    query_tokens = _tokens(query)
    name_tokens = _tokens(name_norm)
    overlap = len(query_tokens & name_tokens) / max(len(query_tokens), 1)
    containment = 1.0 if query_norm and query_norm in name_norm else 0.0
    fuzzy = SequenceMatcher(None, query_norm, name_norm).ratio()
    return 3.0 * overlap + 2.0 * containment + fuzzy


def _program_score_diagnostic(query: str, row: dict[str, Any]) -> dict[str, Any]:
    query_norm = _norm(query)
    name_norm = _norm(row["program_name"])
    query_tokens = _tokens(query)
    name_tokens = _tokens(name_norm)
    return {
        "program_id": row["program_id"],
        "program_name": row["program_name"],
        "score": round(_program_score(query, row), 4),
        "fuzzy_ratio": round(SequenceMatcher(None, query_norm, name_norm).ratio(), 4),
        "token_overlap": round(len(query_tokens & name_tokens) / max(len(query_tokens), 1), 4),
        "exact": query_norm in {_norm(row["program_name"]), _norm(row["program_id"])},
    }


class AdvisorV2Repository:
    """Structured, read-only capabilities exposed after semantic interpretation."""

    def get_catalog_counts(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT
                         (SELECT count(*) FROM programs WHERE status='Active'),
                         (SELECT count(*) FROM courses WHERE status='Active'),
                         (SELECT count(*) FROM programs WHERE status='Active'
                            AND lower(coalesce(credential,'')) LIKE '%bachelor of technology%')"""
                )
                programs, courses, bachelor_technology = cursor.fetchone()
        except psycopg.Error as error:
            return _result("data_unavailable", "get_catalog_counts", detail=type(error).__name__)
        return _result(
            "found", "get_catalog_counts",
            data={"active_programs": programs, "active_courses": courses,
                  "bachelor_of_technology_programs": bachelor_technology},
            evidence_ids=["catalog:active_program_count", "catalog:active_course_count"],
            detail=f"query_count=1;latency_ms={(time.perf_counter()-started)*1000:.2f}",
        )

    def get_campus_directory(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT campus_key, official_name, address, city, region, postal_code,
                              main_phone, description, official_source_url
                       FROM campuses WHERE active=TRUE ORDER BY official_name"""
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "get_campus_directory", detail=type(error).__name__)
        names = ("campus_key", "official_name", "address", "city", "region", "postal_code",
                 "main_phone", "description", "source_url")
        campuses = [dict(zip(names, row)) for row in rows]
        return _result(
            "found", "get_campus_directory", data={"campuses": campuses},
            evidence_ids=[f"campus:{row['campus_key']}" for row in campuses],
            detail=f"query_count=1;latency_ms={(time.perf_counter()-started)*1000:.2f}",
        )

    @staticmethod
    def _canonical_area(proposal: str) -> str | None:
        value = _norm(proposal).replace(" and ", " ")
        aliases = {
            "computing": "computing it", "computing it": "computing it",
            "computing information technology": "computing it",
            "computer science": "computing it", "information technology": "computing it",
            "engineering": "engineering", "ingenieria": "engineering",
            "business": "business media", "business media": "business media",
            "health": "health sciences", "health sciences": "health sciences",
            "trades": "trades apprenticeships", "trades apprenticeships": "trades apprenticeships",
            "transportation": "transportation",
            "applied natural sciences": "applied natural sciences",
        }
        exact = aliases.get(value)
        if exact:
            return exact
        # Sol may propose a composite family such as "structural, civil, or
        # other engineering". Confirm its institutional head area here; the
        # executor only calls this path when no specific program was proposed.
        tokens = set(value.split())
        if {"engineering", "ingenieria"} & tokens:
            return "engineering"
        if "computing" in tokens or "computer science" in value or "information technology" in value:
            return "computing it"
        return None

    def list_programs_by_area(self, proposal: str, limit: int = 100) -> dict[str, Any]:
        """Confirm a semantic area against the stored institutional taxonomy."""
        canonical = self._canonical_area(proposal)
        if canonical is None:
            return _result("not_found", "list_programs_by_area", data={"proposal": proposal})
        started = time.perf_counter()
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT a.area_id, a.area_name, p.program_id, p.program_name,
                              p.credential, p.source_url
                       FROM areas_of_study a JOIN programs p ON p.area_id=a.area_id
                       WHERE p.status='Active' ORDER BY p.program_name, p.program_id"""
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "list_programs_by_area", detail=type(error).__name__)
        matched = []
        for row in rows:
            area_norm = _norm(row[1]).replace(" and ", " ").replace("information technology", "it")
            if area_norm == canonical:
                matched.append(dict(zip(
                    ("area_id", "area_name", "program_id", "program_name", "credential", "source_url"), row,
                )))
        total = len(matched)
        matched = matched[:max(1, min(limit, 100))]
        if not matched:
            return _result("not_found", "list_programs_by_area", data={"proposal": proposal})
        return _result(
            "found", "list_programs_by_area",
            data={"proposal": proposal, "canonical_area": canonical, "total": total, "programs": matched},
            evidence_ids=[f"area:{row['area_id']}" for row in matched]
                         + [f"program:{row['program_id']}" for row in matched],
            detail=f"query_count=1;rows_scanned={len(rows)};rows_returned={len(matched)};latency_ms={(time.perf_counter()-started)*1000:.2f}",
        )

    def find_red_seal_programs(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT DISTINCT p.program_id, p.program_name, p.credential, p.source_url
                       FROM academic_rule_conditions c
                       JOIN academic_rule_groups g ON g.rule_group_id=c.rule_group_id
                       JOIN academic_rule_sets s ON s.rule_set_id=g.rule_set_id
                       JOIN programs p ON p.program_id=s.program_id
                       WHERE p.status='Active' AND s.rule_scope='ADMISSION'
                         AND (lower(coalesce(c.description,'')) LIKE '%red seal%'
                              OR lower(c.parameters::text) LIKE '%red seal%')
                       ORDER BY p.program_name"""
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "find_red_seal_programs", detail=type(error).__name__)
        programs = [dict(zip(("program_id", "program_name", "credential", "source_url"), row)) for row in rows]
        return _result(
            "found" if programs else "not_found", "find_red_seal_programs", data={"programs": programs},
            evidence_ids=[f"program:{row['program_id']}" for row in programs],
            detail=f"query_count=1;rows_returned={len(programs)};latency_ms={(time.perf_counter()-started)*1000:.2f}",
        )

    def get_international_availability(self, family: str) -> dict[str, Any]:
        """Retrieve explicit availability records for a semantically selected family."""
        term = _norm(family)
        if not term or len(term.split()) > 4:
            return _result("not_found", "get_international_availability", data={"family": family})
        started = time.perf_counter()
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT p.program_id, p.program_name, p.credential,
                              d.international_eligibility, d.source_url
                       FROM programs p JOIN program_delivery_facts d ON d.program_id=p.program_id
                       WHERE p.status='Active' AND lower(p.program_name) LIKE %s
                       ORDER BY p.program_name, p.program_id""",
                    (f"%{term}%",),
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "get_international_availability", detail=type(error).__name__)
        programs = [dict(zip(("program_id", "program_name", "credential", "international_eligibility", "source_url"), row)) for row in rows]
        return _result(
            "found" if programs else "not_found", "get_international_availability",
            data={"family": family, "programs": programs},
            evidence_ids=[f"delivery:{row['program_id']}" for row in programs],
            detail=f"query_count=1;rows_returned={len(programs)};latency_ms={(time.perf_counter()-started)*1000:.2f}",
        )

    def get_program_international_availability(self, program_id: str) -> dict[str, Any]:
        """Retrieve availability for one already-resolved program id."""
        started = time.perf_counter()
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT p.program_id, p.program_name, p.credential,
                              d.international_eligibility, d.source_url
                       FROM programs p JOIN program_delivery_facts d ON d.program_id=p.program_id
                       WHERE p.status='Active' AND p.program_id=%s
                       ORDER BY d.source_url LIMIT 1""",
                    (program_id.upper(),),
                )
                row = cursor.fetchone()
        except psycopg.Error as error:
            return _result("data_unavailable", "get_program_international_availability", detail=type(error).__name__)
        if row is None:
            return _result("not_found", "get_program_international_availability", data={"program_id": program_id.upper()})
        item = dict(zip(("program_id", "program_name", "credential", "international_eligibility", "source_url"), row))
        return _result(
            "found", "get_program_international_availability", data=item,
            evidence_ids=[f"delivery:{item['program_id']}"],
            detail=f"query_count=1;rows_returned=1;latency_ms={(time.perf_counter()-started)*1000:.2f}",
        )

    def search_programs(self, query: str, limit: int = 12) -> dict[str, Any]:
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT program_id, program_name, credential, study_mode, campus,
                              delivery_method, source_url
                       FROM programs WHERE status = 'Active' ORDER BY program_name"""
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "search_programs", detail=type(error).__name__)

        records = [
            {"program_id": row[0], "program_name": row[1], "credential": row[2],
             "study_mode": row[3], "campus": row[4], "delivery_method": row[5],
             "source_url": row[6]}
            for row in rows
        ]
        query_tokens = _tokens(query)
        # These are search concepts, not institutional claims. Returned facts still
        # come exclusively from the records above.
        if "computing" in query_tokens:
            query_tokens |= {"computer", "computing", "software", "information", "data"}
        scored = []
        for record in records:
            name_tokens = _tokens(record["program_name"])
            subject_match = bool(query_tokens & name_tokens)
            concept_overlap = len(query_tokens & name_tokens) / max(len(query_tokens), 1)
            score = _program_score(query, record) + 2.0 * concept_overlap
            fuzzy_match = SequenceMatcher(None, _norm(query), _norm(record["program_name"])).ratio() >= 0.68
            if subject_match or fuzzy_match or score >= 1.05 or _norm(query) in {"", "all"}:
                scored.append((score, record["program_name"], record))
        scored.sort(key=lambda item: (-item[0], item[1]))
        matches = [item[2] for item in scored[:limit]]
        if not matches:
            return _result("not_found", "search_programs", data={"query": query, "programs": []})
        return _result(
            "found", "search_programs", data={"query": query, "programs": matches,
                                                "candidates": [
                                                    _program_score_diagnostic(query, item) for item in matches
                                                ]},
            evidence_ids=[f"program:{item['program_id']}" for item in matches],
        )

    def search_program_family(self, query: str, limit: int = 100) -> dict[str, Any]:
        """Search a confirmed family across curated names and program descriptions."""
        term = _norm(query)
        if not term or len(term.split()) > 4:
            return _result("not_found", "search_program_family", data={"query": query, "programs": []})
        started = time.perf_counter()
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT program_id, program_name, credential, study_mode, campus,
                              delivery_method, source_url
                       FROM programs
                       WHERE status='Active'
                         AND (lower(program_name) LIKE %s OR lower(coalesce(program_overview,'')) LIKE %s)
                       ORDER BY program_name, program_id
                       LIMIT %s""",
                    (f"%{term}%", f"%{term}%", max(1, min(limit, 100))),
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "search_program_family", detail=type(error).__name__)
        programs = [dict(zip(
            ("program_id", "program_name", "credential", "study_mode", "campus", "delivery_method", "source_url"), row,
        )) for row in rows]
        return _result(
            "found" if programs else "not_found", "search_program_family",
            data={"query": query, "total": len(programs), "programs": programs},
            evidence_ids=[f"program:{item['program_id']}" for item in programs],
            detail=f"query_count=1;rows_returned={len(programs)};latency_ms={(time.perf_counter()-started)*1000:.2f}",
        )

    def search_courses(self, query: str, limit: int = 20) -> dict[str, Any]:
        """Bounded family search for a semantically selected course subject."""
        term = _norm(query)
        if not term:
            return _result("not_found", "search_courses", data={"query": query, "courses": []})
        started = time.perf_counter()
        canonical_area = self._canonical_area(query)
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT DISTINCT c.course_id, c.course_name, c.credits,
                              c.source_url, c.display_course_code
                       FROM courses c
                       LEFT JOIN program_courses pc ON pc.course_id=c.course_id
                       LEFT JOIN programs p ON p.program_id=pc.program_id AND p.status='Active'
                       LEFT JOIN areas_of_study a ON a.area_id=p.area_id
                       WHERE c.status='Active'
                         AND (lower(c.course_name) LIKE %s
                              OR lower(coalesce(c.course_overview,'')) LIKE %s
                              OR lower(coalesce(p.program_name,'')) LIKE %s
                              OR (%s::text IS NOT NULL AND lower(coalesce(a.area_name,'')) LIKE %s))
                       ORDER BY c.course_name, c.course_id
                       LIMIT %s""",
                    (f"%{term}%", f"%{term}%", f"%{term}%", canonical_area,
                     f"%{canonical_area or ''}%", max(1, min(limit, 50))),
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "search_courses", detail=type(error).__name__)
        courses = [dict(zip(("course_id", "course_name", "credits", "source_url", "display_course_code"), row))
                   for row in rows]
        return _result(
            "found" if courses else "not_found", "search_courses",
            data={"query": query, "courses": courses},
            evidence_ids=[f"course:{item['course_id']}" for item in courses],
            detail=f"query_count=1;rows_returned={len(courses)};latency_ms={(time.perf_counter()-started)*1000:.2f}",
        )

    def resolve_candidate_credential(self, candidate_ids: list[str], query: str) -> dict[str, Any]:
        """Resolve a clarification against only candidates already shown."""
        markers = _credential_markers(query)
        if not candidate_ids or not markers:
            return _result("not_found", "resolve_candidate_credential", data={"query": query})
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT program_id, program_name, credential
                       FROM programs WHERE status='Active' AND program_id = ANY(%s)
                       ORDER BY program_name, program_id""",
                    (candidate_ids,),
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "resolve_candidate_credential", detail=type(error).__name__)
        programs = [dict(zip(("program_id", "program_name", "credential"), row)) for row in rows]
        matched = [item for item in programs if _credential_matches(str(item.get("credential") or ""), markers)]
        if len(matched) != 1:
            return _result(
                "ambiguous" if matched else "not_found", "resolve_candidate_credential",
                data={"query": query, "programs": matched or programs},
                evidence_ids=[f"program:{item['program_id']}" for item in matched],
            )
        return _result(
            "found", "resolve_candidate_credential", data=matched[0],
            evidence_ids=[f"program:{matched[0]['program_id']}"],
        )

    def resolve_program(self, query: str) -> dict[str, Any]:
        searched = self.search_programs(query, limit=8)
        if searched["status"] != "found":
            return {**searched, "capability": "resolve_program"}
        programs = searched["data"]["programs"]
        diagnostics = [_program_score_diagnostic(query, item) for item in programs]
        scores = [item["score"] for item in diagnostics]
        fuzzy_scores = [item["fuzzy_ratio"] for item in diagnostics]
        exact = [item for item in programs if _norm(query) in {_norm(item["program_name"]), _norm(item["program_id"])}]
        query_tokens = _tokens(query)
        credential_markers = [marker for marker in ("bachelor", "master", "diploma", "certificate")
                              if marker in query_tokens or f"{marker}s" in query_tokens]
        core_tokens = query_tokens - {"bachelor", "bachelors", "degree", "master", "masters",
                                      "diploma", "certificate", "credential"}
        credential_confirmed = [
            item for item in programs
            if core_tokens and core_tokens <= _tokens(item["program_name"])
            and all(marker in _norm(str(item.get("credential") or "")) for marker in credential_markers)
        ]
        broad_subject = len(query_tokens) <= 1 and bool(
            query_tokens & {"business", "computing", "design", "engineering", "health", "science", "technology"}
        )
        if broad_subject:
            candidates = programs[:5]
            return _result(
                "ambiguous", "resolve_program",
                data={"query": query, "programs": candidates, "candidates": diagnostics[:5],
                      "reason": "broad_subject"},
                evidence_ids=[f"program:{item['program_id']}" for item in candidates],
            )
        elif len(credential_confirmed) == 1:
            chosen = credential_confirmed[0]
        elif len(exact) == 1:
            chosen = exact[0]
        elif scores and scores[0] >= 3.0 and (len(scores) == 1 or scores[0] - scores[1] >= 0.35):
            chosen = programs[0]
        elif scores and scores[0] >= 1.8 and (len(scores) == 1 or scores[0] - scores[1] >= 0.8):
            chosen = programs[0]
        elif fuzzy_scores and fuzzy_scores[0] >= 0.78 and (
                len(fuzzy_scores) == 1 or fuzzy_scores[0] - fuzzy_scores[1] >= 0.08):
            chosen = programs[0]
        elif scores and scores[0] < 1.05 and fuzzy_scores[0] < 0.55:
            return _result(
                "not_found", "resolve_program", data={"query": query, "programs": [],
                                                        "candidates": diagnostics[:5],
                                                        "reason": "low_relevance"},
            )
        else:
            candidates = programs[:5]
            return _result(
                "ambiguous", "resolve_program", data={"query": query, "programs": candidates,
                                                        "candidates": diagnostics[:5],
                                                        "reason": "broad_subject" if broad_subject else "insufficient_margin"},
                evidence_ids=[f"program:{item['program_id']}" for item in candidates],
            )
        return _result(
            "found", "resolve_program", data={**chosen, "resolution": {
                "reason": "exact" if len(exact) == 1 else "overwhelming_candidate",
                "candidates": diagnostics[:5],
            }},
            evidence_ids=[f"program:{chosen['program_id']}"],
        )

    def get_program_facts(self, program_id: str) -> dict[str, Any]:
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT program_id, program_name, program_overview, school, credential,
                              study_mode, campus, delivery_method, status, source_url
                       FROM programs WHERE program_id = %s AND status = 'Active'""",
                    (program_id.upper(),),
                )
                row = cursor.fetchone()
        except psycopg.Error as error:
            return _result("data_unavailable", "get_program_facts", detail=type(error).__name__)
        if row is None:
            return _result("not_found", "get_program_facts", data={"program_id": program_id.upper()})
        data = dict(zip(
            ("program_id", "program_name", "program_overview", "school", "credential",
             "study_mode", "campus", "delivery_method", "status", "source_url"), row,
        ))
        return _result("found", "get_program_facts", data=data,
                       evidence_ids=[f"program:{data['program_id']}"])

    def get_course_facts(self, query: str) -> dict[str, Any]:
        compact = re.sub(r"[^A-Za-z0-9]", "", query).upper()
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT course_id, course_name, credits, course_overview, status,
                              source_url, display_course_code
                       FROM courses
                       WHERE course_id = %s OR display_course_code ILIKE %s
                          OR course_name ILIKE %s
                       ORDER BY CASE WHEN course_id = %s THEN 0 ELSE 1 END, course_name
                       LIMIT 8""",
                    (compact, query.strip(), f"%{query.strip()}%", compact),
                )
                rows = cursor.fetchall()
        except psycopg.Error as error:
            return _result("data_unavailable", "get_course_facts", detail=type(error).__name__)
        items = [dict(zip(
            ("course_id", "course_name", "credits", "course_overview", "status",
             "source_url", "display_course_code"), row,
        )) for row in rows]
        if not items:
            return _result("not_found", "get_course_facts", data={"query": query})
        if len(items) > 1 and items[0]["course_id"] != compact:
            return _result("ambiguous", "get_course_facts", data={"query": query, "courses": items},
                           evidence_ids=[f"course:{item['course_id']}" for item in items])
        item = items[0]
        return _result("found", "get_course_facts", data=item,
                       evidence_ids=[f"course:{item['course_id']}"])

    def get_admission_rules(self, program_id: str) -> dict[str, Any]:
        try:
            packet = get_program_rules(program_id, "ADMISSION")
        except psycopg.Error as error:
            return _result("data_unavailable", "get_admission_rules", detail=type(error).__name__)
        rules = packet.get("rule_sets", [])
        if not rules:
            return _result("not_found", "get_admission_rules", data={"program_id": program_id.upper(), "rule_sets": []})
        evidence = [f"rule_set:{rule['rule_set_id']}" for rule in rules]
        return _result("found", "get_admission_rules", data=packet, evidence_ids=evidence)

    def get_course_requirements(self, course_id: str) -> dict[str, Any]:
        try:
            packet = get_course_requirements(course_id)
        except psycopg.Error as error:
            return _result("data_unavailable", "get_course_requirements", detail=type(error).__name__)
        if not packet.get("groups"):
            return _result("not_found", "get_course_requirements", data=packet)
        return _result("found", "get_course_requirements", data=packet,
                       evidence_ids=[f"course_prerequisites:{course_id.upper()}"])

    def evaluate_course_eligibility(self, course_id: str, profile: StudentProfileV2) -> dict[str, Any]:
        requirements = self.get_course_requirements(course_id)
        if requirements["status"] == "data_unavailable":
            return _result("data_unavailable", "evaluate_course_eligibility", data={
                "course_id": course_id.upper(), "status": "retrieval_failure"}, detail=requirements.get("detail"))
        if requirements["status"] == "not_found":
            return _result("found", "evaluate_course_eligibility", data={
                "course_id": course_id.upper(), "status": "met", "groups": [],
                "reason": "no_prerequisites_recorded"}, evidence_ids=[])
        groups = [_evaluate_prerequisite_group(group, profile) for group in requirements["data"]["groups"]]
        status = _combine([group["status"] for group in groups], "AND")
        return _result("found", "evaluate_course_eligibility", data={
            "course_id": course_id.upper(), "status": status, "groups": groups,
            "needed_student_fields": sorted(_needed_fields(groups)) if status == "missing_student_information" else [],
        }, evidence_ids=requirements["evidence_ids"])

    def evaluate_admission(self, program_id: str, profile: StudentProfileV2) -> dict[str, Any]:
        rules = self.get_admission_rules(program_id)
        if rules["status"] == "data_unavailable":
            return _result("data_unavailable", "evaluate_admission", data={
                "program_id": program_id.upper(), "status": "retrieval_failure",
            }, detail=rules["detail"])
        if rules["status"] == "not_found":
            return _result("not_found", "evaluate_admission", data={
                "program_id": program_id.upper(), "status": "evidence_unavailable",
            })
        evaluations = [_evaluate_rule_set(rule, profile) for rule in rules["data"]["rule_sets"]]
        status = _combine([item["status"] for item in evaluations if item.get("applicable", True)], "AND")
        leaves = list(_evaluation_leaves(evaluations))
        decisive_leaves = list(_decisive_leaves(evaluations))
        summary = {candidate: sum(item["status"] == candidate for item in leaves) for candidate in (
            "met", "unmet", "missing_student_information", "evidence_unavailable",
            "human_review_required", "retrieval_failure",
        )}
        return _result("found", "evaluate_admission", data={
            "program_id": program_id.upper(), "status": status,
            "status_counts": {candidate: sum(item["status"] == candidate for item in decisive_leaves)
                              for candidate in summary},
            "all_branch_status_counts": summary,
            "needed_student_fields": sorted(_needed_fields(evaluations)) if status == "missing_student_information" else [],
            "rule_sets": evaluations,
        }, evidence_ids=rules["evidence_ids"])


def _subject_key(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "_", (value or "").upper()).strip("_")


def _as_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float, Decimal)) else None


def _profile_gpa_percent(profile: StudentProfileV2) -> float | None:
    if profile.gpa is None:
        return None
    return profile.gpa / profile.gpa_scale * 100


def _credential_match(credentials: list[str], wanted: str) -> bool:
    wanted_norm = _norm(wanted)
    wanted_tokens = {token for token in _tokens(wanted_norm) if token not in {"recognized", "related", "prior"}}
    for credential in credentials:
        item = _norm(credential)
        if wanted_tokens and wanted_tokens & _tokens(item):
            return True
        if any(word in wanted_norm and word in item for word in ("degree", "diploma", "certificate")):
            return True
    return False


def _reported_grade(condition: dict[str, Any], profile: StudentProfileV2) -> tuple[float | None, str | None]:
    subject = _subject_key(condition.get("subject_id"))
    kind = str(condition.get("condition_type") or "").upper()
    candidates = [subject] if subject else []
    for accepted in condition.get("accepted_values") or []:
        candidate = _subject_key(str(accepted))
        if candidate:
            candidates.append(candidate)
            candidates.append(candidate.replace("_OF_", "_"))
    if subject == "ENGLISH_STUDIES_12":
        candidates.append("ENGLISH_12")
    if subject == "MATH_11" or kind == "MATH_OPTION_GRADE":
        candidates.extend(["PRE_CALCULUS_11", "FOUNDATIONS_OF_MATH_11", "WORKPLACE_MATH_11"])
    for candidate in candidates:
        if candidate in profile.grades:
            return profile.grades[candidate], candidate
    return None, subject or None


def _condition(condition: dict[str, Any], profile: StudentProfileV2) -> dict[str, Any]:
    kind = str(condition.get("condition_type") or "").upper()
    subject = _subject_key(condition.get("subject_id"))
    minimum = condition.get("minimum_value")
    parameters = condition.get("parameters") or {}
    base = {"condition_id": condition.get("condition_id"), "condition_type": kind,
            "subject_id": condition.get("subject_id"), "description": condition.get("description"),
            "applicable": True}
    effective_after = parameters.get("effective_for_applications_after")
    if effective_after:
        if profile.application_date is None:
            return {**base, "status": "missing_student_information",
                    "needed_student_fields": ["application_date"], "reason": "date_controls_requirement"}
        if profile.application_date <= date.fromisoformat(str(effective_after)):
            return {**base, "status": "met", "applicable": False,
                    "reason": "requirement_not_effective_for_application_date"}
    if kind == "OFFICIAL_ADMISSION_REQUIREMENTS":
        return {**base, "status": "human_review_required", "reason": "unstructured_official_requirement"}
    if kind in {"DEPARTMENT_ASSESSMENT", "COMPETITIVE_DEPARTMENT_REVIEW", "INDIVIDUAL_EQUIVALENCY",
                "ASSESSMENT", "FIRST_QUALIFIED", "LINKED_PROGRAM_ADMISSION",
                "MECHANICAL_REASONING_TRANSITION", "ADMISSION_PATH_UBC", "ADMISSION_PATH_TRANSFER"}:
        return {**base, "status": "human_review_required", "reason": "institutional_judgment"}
    if kind == "INTERNATIONAL_CREDENTIAL_EVALUATION":
        if profile.international_status == "domestic" or (profile.credential_country and
                profile.credential_country.lower() in {"canada", "united states", "united kingdom", "australia", "new zealand"}):
            return {**base, "status": "met", "applicable": False,
                    "reason": "international_evaluation_not_applicable"}
        if profile.international_status is None and profile.credential_country is None:
            return {**base, "status": "missing_student_information",
                    "needed_student_fields": ["credential_country"], "reason": "applicability_unknown"}
        return {**base, "status": "human_review_required", "reason": "credential_evaluation_requires_institution"}
    if kind in {"GRADE", "ENGLISH_GRADE", "MATH_OPTION_GRADE", "PROGRAM_COURSE_GRADE"}:
        value, matched_subject = _reported_grade(condition, profile)
        if value is None and parameters.get("accepted_equivalent_or_assessment") and profile.assessments_completed:
            return {**base, "status": "met", "reported_value": profile.assessments_completed,
                    "minimum_value": minimum, "reason": "reported_accepted_assessment"}
        status = "missing_student_information" if value is None else ("met" if minimum is None or value >= float(minimum) else "unmet")
        return {**base, "status": status, "reported_value": value, "matched_subject": matched_subject,
                "minimum_value": minimum, "needed_student_fields": [f"grades.{subject}"] if value is None else []}
    if kind in {"GPA", "RELATED_POSTSECONDARY_CREDENTIAL_GPA", "UNRELATED_POSTSECONDARY_CREDENTIAL_GPA",
                "BRIDGING_CREDENTIAL_GPA"}:
        if not profile.credentials:
            status = "missing_student_information"
            value = None
        else:
            value = profile.credential_gpas.get(kind)
            if value is None:
                value = _profile_gpa_percent(profile)
        if profile.credentials and value is None:
            status = "missing_student_information"
        elif profile.credentials:
            status = "met" if minimum is None or value >= float(minimum) else "unmet"
        return {**base, "status": status, "reported_value": value, "minimum_value": minimum,
                "needed_student_fields": (["credentials"] if not profile.credentials else
                                           (["gpa"] if value is None else []))}
    if kind == "WORK_EXPERIENCE" or "EXPERIENCE" in kind:
        if kind == "RELEVANT_INDUSTRY_EXPERIENCE" and minimum is None:
            return {**base, "status": "met", "applicable": False,
                    "reason": "recommended_not_required"}
        area_value = profile.work_experience_months_by_area.get(subject) if subject else None
        unit = str(condition.get("unit") or "YEAR").upper()
        value = area_value if area_value is not None else profile.work_experience_years
        threshold = _as_number(minimum)
        if area_value is None and value is not None and unit.startswith("MONTH"):
            value = value * 12
        status = "missing_student_information" if value is None else ("met" if threshold is None or value >= threshold else "unmet")
        if status == "met" and parameters.get("recency_qualification") == "human_confirmation":
            status = "human_review_required"
        return {**base, "status": status, "reported_value": value, "minimum_value": minimum,
                "unit": unit, "needed_student_fields": ["work_experience"] if value is None else [],
                "reason": "recency_requires_confirmation" if status == "human_review_required" else None}
    if kind == "HIGH_SCHOOL_GRADUATION":
        value = profile.high_school_graduated
        return {**base, "status": "missing_student_information" if value is None else ("met" if value else "unmet")}
    if kind in {"CREDENTIAL", "PRIOR_DIPLOMA", "PRIOR_DEGREE"}:
        if not profile.credentials:
            return {**base, "status": "missing_student_information", "needed_student_fields": ["credentials"]}
        wanted = str(condition.get("subject_id") or condition.get("description") or kind)
        return {**base, "status": "met" if _credential_match(profile.credentials, wanted) else "unmet",
                "reported_value": profile.credentials}
    if kind == "CREDENTIAL_EXCLUSION":
        if not profile.credentials:
            return {**base, "status": "missing_student_information", "needed_student_fields": ["credentials"]}
        alone = len(profile.credentials) == 1 and "master" in _norm(profile.credentials[0])
        return {**base, "status": "unmet" if alone else "met", "reported_value": profile.credentials}
    if kind == "RED_SEAL_TRADE":
        if not profile.red_seal_trade:
            return {**base, "status": "missing_student_information",
                    "needed_student_fields": ["red_seal_trade"]}
        accepted = [_norm(str(item)) for item in condition.get("accepted_values") or []]
        reported = _norm(profile.red_seal_trade)
        matched = not accepted or any(item in reported or reported in item for item in accepted)
        return {**base, "status": "met" if matched else "unmet",
                "reported_value": profile.red_seal_trade, "accepted_values": condition.get("accepted_values")}
    if kind == "DOCUMENT" or "QUESTIONNAIRE" in kind or kind == "REFERENCES":
        wanted = _subject_key(condition.get("subject_id") or kind)
        supplied = {_subject_key(item) for item in profile.documents}
        if wanted not in supplied:
            return {**base, "status": "missing_student_information",
                    "needed_student_fields": [f"documents.{wanted}"]}
        return {**base, "status": "human_review_required" if parameters.get("executable") is False else "met",
                "reported_value": wanted, "reason": "document_verification" if parameters.get("executable") is False else None}
    if kind == "PRE_ENTRY_ASSESSMENT":
        if not profile.assessments_completed:
            return {**base, "status": "missing_student_information", "needed_student_fields": ["assessments_completed"]}
        needs_review = (parameters.get("program_of_study_approval") or
                        parameters.get("human_confirmation_only") or parameters.get("executable") is False)
        return {**base, "status": "human_review_required" if needs_review else "met",
                "reported_value": profile.assessments_completed}
    if kind == "LICENSURE":
        return {**base, "status": "human_review_required" if profile.licences else "missing_student_information",
                "reported_value": profile.licences, "needed_student_fields": [] if profile.licences else ["licences"],
                "reason": "licensure_verification" if profile.licences else None}
    if kind == "CREDITS":
        total = sum(profile.course_credits.values()) if profile.course_credits else None
        threshold = _as_number(minimum)
        return {**base, "status": "missing_student_information" if total is None else
                ("met" if threshold is None or total >= threshold else "unmet"),
                "reported_value": total, "minimum_value": minimum,
                "needed_student_fields": ["course_credits"] if total is None else []}
    if kind == "SUBJECT_SEQUENCE_AVERAGES":
        values = profile.subject_sequence_averages
        if len(values) < 5:
            return {**base, "status": "missing_student_information",
                    "reported_value": values, "needed_student_fields": ["subject_sequence_averages"]}
        met = all(value >= 62 for value in values[:5]) and sum(value < 65 for value in values[:5]) <= 2
        return {**base, "status": "met" if met else "unmet", "reported_value": values[:5]}
    if kind == "STANDARD_ENTRY":
        has_degree = any("degree" in _norm(item) and ("computer" in _norm(item) or "computing" in _norm(item))
                         for item in profile.credentials)
        gpa_percent = _profile_gpa_percent(profile)
        if not profile.credentials or gpa_percent is None:
            return {**base, "status": "missing_student_information",
                    "needed_student_fields": [key for key, missing in (("credentials", not profile.credentials), ("gpa", profile.gpa is None)) if missing]}
        required = float(parameters.get("percentage_equivalent") or minimum or 0)
        return {**base, "status": "met" if has_degree and gpa_percent >= required else "unmet",
                "reported_value": {"credentials": profile.credentials, "gpa": profile.gpa,
                                   "gpa_scale": profile.gpa_scale, "percentage_equivalent": gpa_percent},
                "minimum_value": required}
    if kind.startswith("ENTRY_OPTION_"):
        wanted = str(parameters.get("credential") or "")
        if wanted:
            if not profile.credentials:
                return {**base, "status": "missing_student_information", "needed_student_fields": ["credentials"]}
            matched = _credential_match(profile.credentials, wanted)
            average = profile.gpa
            minimum_average = _as_number(parameters.get("minimum_course_average"))
            if matched and minimum_average is not None and average is None:
                return {**base, "status": "missing_student_information", "needed_student_fields": ["gpa"]}
            return {**base, "status": "met" if matched and (minimum_average is None or average >= minimum_average) else "unmet"}
        courses = [_subject_key(item) for item in parameters.get("courses") or []]
        if courses:
            values = [profile.grades[item] for item in courses if item in profile.grades]
            required_count = int(parameters.get("courses_required") or len(courses))
            if len(values) < required_count:
                return {**base, "status": "missing_student_information", "reported_value": values,
                        "needed_student_fields": ["grades"]}
            average = sum(sorted(values, reverse=True)[:required_count]) / required_count
            threshold = float(parameters.get("aggregate_average_minimum") or 0)
            return {**base, "status": "met" if average >= threshold else "unmet", "reported_value": average,
                    "minimum_value": threshold}
        return {**base, "status": "human_review_required", "reason": "professional_equivalency"}
    if kind == "ENGLISH_CATEGORY":
        return {**base, "status": "human_review_required", "reason": "category_equivalency_not_structured"}
    if kind == "INTAKE_2026_GPA_EXCEPTION":
        if profile.intake is None:
            return {**base, "status": "missing_student_information", "needed_student_fields": ["intake"]}
        if "2026" not in profile.intake:
            return {**base, "status": "met", "applicable": False, "reason": "intake_exception_not_applicable"}
        return {**base, "status": "missing_student_information" if profile.gpa is None else
                ("met" if profile.gpa >= float(minimum) else "unmet"), "reported_value": profile.gpa,
                "minimum_value": minimum, "needed_student_fields": ["gpa"] if profile.gpa is None else []}
    if parameters.get("executable") is False or parameters.get("human_confirmation"):
        return {**base, "status": "human_review_required", "reason": "institutional_confirmation"}
    if kind in {"NO_FORMAL_APPLICATION_REQUIRED", "INTERNATIONAL_ELIGIBLE"}:
        return {**base, "status": "met"}
    return {**base, "status": "human_review_required", "reason": "unsupported_structured_condition"}


def _prerequisite_condition(condition: dict[str, Any], profile: StudentProfileV2) -> dict[str, Any]:
    kind = str(condition.get("condition_type") or "COURSE").upper()
    course_id = _subject_key(condition.get("prerequisite_course_id"))
    base = {"condition_type": kind, "prerequisite_course_id": condition.get("prerequisite_course_id"),
            "description": condition.get("description"), "applicable": True}
    if kind == "COURSE":
        completed = {_subject_key(item) for item in profile.completed_courses}
        grade = profile.grades.get(course_id)
        if course_id not in completed and grade is None:
            return {**base, "status": "missing_student_information",
                    "needed_student_fields": [f"completed_courses.{course_id}"]}
        minimum = _as_number(condition.get("minimum_grade"))
        if minimum is not None and grade is None:
            return {**base, "status": "missing_student_information",
                    "needed_student_fields": [f"grades.{course_id}"]}
        return {**base, "status": "met" if minimum is None or grade >= minimum else "unmet",
                "reported_value": grade, "minimum_value": minimum}
    if kind == "PROGRAM_ADMISSION":
        required = _subject_key(condition.get("required_program_id"))
        if not profile.admitted_programs:
            return {**base, "status": "missing_student_information", "needed_student_fields": ["admitted_programs"]}
        return {**base, "status": "met" if required in {_subject_key(item) for item in profile.admitted_programs} else "unmet"}
    if kind == "WORK_EXPERIENCE":
        normalized = {"condition_type": kind, "condition_id": None,
                      "minimum_value": (condition.get("parameters") or {}).get("minimum_value"),
                      "unit": (condition.get("parameters") or {}).get("unit", "YEAR"),
                      "parameters": condition.get("parameters") or {}, "description": condition.get("description")}
        return _condition(normalized, profile)
    if kind in {"DEPARTMENT_APPROVAL", "APPROVAL", "INDUSTRY_SPONSOR", "INDUSTRY_TOPIC",
                "PROGRAM_COURSES_COMPLETE_EXCEPT", "POSTSECONDARY_SUBJECT_CREDITS", "COMMUNICATION_CREDITS"}:
        return {**base, "status": "human_review_required", "reason": "institutional_or_unstructured_prerequisite"}
    return {**base, "status": "human_review_required", "reason": "unsupported_prerequisite"}


def _evaluate_prerequisite_group(group: dict[str, Any], profile: StudentProfileV2) -> dict[str, Any]:
    conditions = [_prerequisite_condition(item, profile) for item in group.get("conditions", [])]
    operator = group.get("group_type") or "AND"
    return {"operator": operator, "status": _combine([item["status"] for item in conditions], operator),
            "applicable": True, "conditions": conditions, "children": []}


def _combine(statuses: list[EvaluationStatus], operator: str) -> EvaluationStatus:
    if not statuses:
        return "human_review_required"
    operator = operator.upper()
    if operator in {"OR", "ANY_OF", "ALTERNATIVE"}:
        if "met" in statuses:
            return "met"
        if "retrieval_failure" in statuses:
            return "retrieval_failure"
        if "evidence_unavailable" in statuses:
            return "evidence_unavailable"
        if "human_review_required" in statuses:
            return "human_review_required"
        if "missing_student_information" in statuses:
            return "missing_student_information"
        return "unmet"
    if "unmet" in statuses:
        return "unmet"
    if "retrieval_failure" in statuses:
        return "retrieval_failure"
    if "evidence_unavailable" in statuses:
        return "evidence_unavailable"
    if "human_review_required" in statuses:
        return "human_review_required"
    if "missing_student_information" in statuses:
        return "missing_student_information"
    return "met"


def _evaluate_group(group: dict[str, Any], profile: StudentProfileV2) -> dict[str, Any]:
    conditions = [_condition(item, profile) for item in group.get("conditions", [])]
    children = [_evaluate_group(item, profile) for item in group.get("children", [])]
    statuses = [item["status"] for item in conditions + children if item.get("applicable", True)]
    return {"rule_group_id": group.get("rule_group_id"), "label": group.get("label"),
            "operator": group.get("operator"), "status": _combine(statuses, group.get("operator") or "AND"),
            "applicable": bool(statuses),
            "conditions": conditions, "children": children}


def _evaluate_rule_set(rule: dict[str, Any], profile: StudentProfileV2) -> dict[str, Any]:
    groups = [_evaluate_group(group, profile) for group in rule.get("groups", [])]
    return {"rule_set_id": rule.get("rule_set_id"), "name": rule.get("name"),
            "status": _combine([group["status"] for group in groups if group.get("applicable", True)], "AND"),
            "applicable": any(group.get("applicable", True) for group in groups), "groups": groups}


def _evaluation_leaves(nodes: list[dict[str, Any]]):
    for node in nodes:
        for condition in node.get("conditions", []):
            if condition.get("applicable", True):
                yield condition
        yield from _evaluation_leaves(node.get("children", []))
        yield from _evaluation_leaves(node.get("groups", []))


def _decisive_leaves(nodes: list[dict[str, Any]]):
    for node in nodes:
        items = [item for item in node.get("conditions", []) + node.get("children", []) + node.get("groups", [])
                 if item.get("applicable", True)]
        operator = str(node.get("operator") or "AND").upper()
        if operator in {"OR", "ANY_OF", "ALTERNATIVE"}:
            target = node.get("status")
            preferred = [item for item in items if item.get("status") == target]
            items = preferred or items
        for item in items:
            if "condition_type" in item:
                yield item
            else:
                yield from _decisive_leaves([item])


def _needed_fields(nodes: list[dict[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for node in nodes:
        if node.get("status") != "missing_student_information":
            continue
        items = [item for item in node.get("conditions", []) + node.get("children", []) + node.get("groups", [])
                 if item.get("applicable", True)]
        operator = str(node.get("operator") or "AND").upper()
        missing_items = [item for item in items if item.get("status") == "missing_student_information"]
        if operator in {"OR", "ANY_OF", "ALTERNATIVE"} and missing_items:
            # One viable alternative is enough; ask for the smallest missing route.
            candidates = []
            for item in missing_items:
                candidate = set(item.get("needed_student_fields", [])) if "condition_type" in item else _needed_fields([item])
                candidates.append(candidate)
            fields |= min(candidates, key=lambda item: (len(item), sorted(item)))
        else:
            for item in missing_items:
                fields |= (set(item.get("needed_student_fields", [])) if "condition_type" in item
                           else _needed_fields([item]))
    return fields


def _merge_profile(previous: StudentProfileV2, supplied: StudentProfileV2 | None,
                   question: str, *, provenance: dict[str, list[dict[str, Any]]] | None = None,
                   turn_index: int = 0, source: str = "explicit_message") \
        -> tuple[StudentProfileV2, list[str], list[str], dict[str, list[dict[str, Any]]]]:
    data = previous.model_copy(deep=True)
    history = {key: [dict(item) for item in values] for key, values in (provenance or {}).items()}
    changes: list[str] = []
    conflicts: list[str] = []

    def assign(key: str, value: Any) -> None:
        prior = getattr(data, key)
        if prior not in (None, [], {}) and prior != value:
            conflicts.append(key)
        if prior != value:
            changes.append(key)
            setattr(data, key, value)
            history.setdefault(key, []).append({
                "turn": turn_index, "source": source, "assertion": "explicit",
                "value": value, "supersedes": prior if prior not in (None, [], {}) else None,
            })

    if supplied is not None:
        incoming = supplied.model_dump(exclude_unset=True)
        for key, value in incoming.items():
            if value not in (None, [], {}):
                assign(key, value)
    years = re.search(r"\b(?:i have|with|actually(?:\s+i have)?)\s+(\d+(?:\.\d+)?)\s+years?", question, re.I)
    if years:
        assign("work_experience_years", float(years.group(1)))
    months = re.search(r"\b(?:i have|with|and)\s+(?:an?\s+)?(\d+(?:\.\d+)?)[ -]months?(?:'|\s)", question, re.I)
    if months:
        month_value = float(months.group(1))
        assign("work_experience_years", month_value / 12)
        mapped = dict(data.work_experience_months_by_area)
        mapped["GENERAL"] = month_value
        assign("work_experience_months_by_area", mapped)
    gpa = re.search(r"\b(?:my\s+)?gpa\s+(?:is|of)?\s*(\d+(?:\.\d+)?)\s*%?", question, re.I)
    if gpa:
        assign("gpa", float(gpa.group(1)))
    for subject, grade in re.findall(r"\b([A-Za-z][A-Za-z ]+?\s*\d{2})\s+(?:at|with|is)\s+(\d+(?:\.\d+)?)\s*(?:%|percent\b)", question, re.I):
        subject = re.sub(r"^(?:actually|correction|corrected|my|(?:and\s+)?i\s+have)\s+", "", subject.strip(), flags=re.I)
        key = _subject_key(subject)
        value = float(grade)
        if key in data.grades and data.grades[key] != value:
            conflicts.append(f"grades.{key}")
        prior = data.grades.get(key)
        data.grades[key] = value
        changes.append(f"grades.{key}")
        history.setdefault(f"grades.{key}", []).append({
            "turn": turn_index, "source": source, "assertion": "explicit",
            "value": value, "supersedes": prior,
        })
    trade = re.search(r"\bRed Seal(?: certification| endorsement)?(?:\s+as)?(?:\s+an?)?\s+([A-Za-z][A-Za-z /&-]{1,60}?)(?:,|\band\b|\.|$)", question, re.I)
    if trade:
        assign("red_seal_trade", trade.group(1).strip())
    credential_grade = re.search(
        r"\b(?:associate certificate|certificate)\s+(?:in\s+)?([A-Za-z ]+?)\s+(?:at|with)\s+(\d+(?:\.\d+)?)\s*(?:percent|%)", question, re.I,
    )
    if credential_grade:
        credential = ("Associate Certificate " + credential_grade.group(1).strip()).strip()
        if credential not in data.credentials:
            data.credentials.append(credential)
            changes.append("credentials")
        gpas = dict(data.credential_gpas)
        gpas["BRIDGING_CREDENTIAL_GPA"] = float(credential_grade.group(2))
        assign("credential_gpas", gpas)
    if re.search(r"\b(?:i have|i hold|with)\s+(?:an?\s+)?(?:college\s+)?diploma\b", question, re.I):
        if "diploma" not in data.credentials:
            data.credentials.append("diploma (institution not stated)")
    if re.search(r"\bi (?:graduated|finished) high school\b", question, re.I):
        assign("high_school_graduated", True)
    if re.search(r"\bi (?:did not|didn't|have not|haven't) (?:graduate|finished?) high school\b", question, re.I):
        assign("high_school_graduated", False)
    return data, list(dict.fromkeys(changes)), list(dict.fromkeys(conflicts)), history


def _is_discovery(question: str) -> bool:
    text = _norm(question)
    return bool(re.search(r"\b(?:what|which|list|show|any)\b.*\bprograms?\b", text))


def _is_broad_program_query(question: str) -> bool:
    tokens = _tokens(question)
    return len(tokens) == 1 and bool(
        tokens & {"business", "computing", "design", "engineering", "health", "science", "technology"}
    )


def _is_follow_up(question: str) -> bool:
    text = _norm(question)
    if text in {"tell me more", "what about it", "what about that", "and it", "how about it",
                "what are the requirements", "and the requirements", "how about admissions",
                "follow up", "a follow up"}:
        return True
    return (bool(re.search(r"\b(?:it|its|that|this|the program|the course)\b", text))
            or bool(re.match(r"^(?:and|also)\s+(?:admissions?|requirements?|eligibility)", text))) \
        and not _course_query(question)


def _contains_profile_fact(question: str) -> bool:
    return bool(re.search(
        r"\b(?:my\s+gpa|i\s+(?:have|hold|graduated|finished)|with\s+\d+(?:\.\d+)?\s+years?|"
        r"[A-Za-z][A-Za-z ]+\s+\d{2}\s+(?:at|with|is)\s+\d+(?:\.\d+)?\s*%|"
        r"actually\s+(?:my\s+gpa|i\s+have|\d+(?:\.\d+)?\s+years?))\b", question, re.I
    ))


def _entity_query(question: str) -> str:
    eligibility_target = re.search(r"(?i)\b(?:eligible|qualify)\s+for\s+(.+)$", question)
    if eligibility_target:
        return eligibility_target.group(1).strip(" ?.,")
    text = re.sub(
        r"(?i)\b(?:am i eligible for|do i qualify for|what are the (?:admission )?requirements for|"
        r"(?:admission )?requirements for|tell me about|what about|give me information about)\b", " ", question,
    )
    text = re.sub(r"(?i)\b(?:and|now|program|at bcit|please)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip(" ?.,")


def _discovery_query(question: str) -> str:
    text = re.sub(r"(?i)\b(?:what|which|list|show|are|there|any|do you have|does bcit offer|programs?)\b", " ", question)
    return re.sub(r"\s+", " ", text).strip(" ?.,") or "all"


def _course_query(question: str) -> str | None:
    match = re.search(r"\b([A-Za-z]{2,8})[ -]?(\d{3,4})\b", question)
    return f"{match.group(1)}{match.group(2)}" if match else None


def _fallback_interpretation(question: str, previous: AdvisorV2State) -> AdvisorV2Interpretation:
    """One bounded semantic fallback used only when Sol is unavailable or fails."""
    text = _norm(question)
    subject_area = None
    for pattern, subject in (
        (r"\b(?:computing|computer science|computing and it|information technology)\b", "Computing & IT"),
        (r"\b(?:engineering|ingenieria)\b", "Engineering"),
        (r"\bnursing\b", "nursing"),
        (r"\baviation\b", "aviation"),
        (r"\btechnology\b", "technology"),
    ):
        if re.search(pattern, text):
            subject_area = subject
            break
    requested: list[str] = []
    scope = "unknown"
    reference = "explicit_new_subject" if subject_area else "no_reference"
    program_reference = None
    course_reference = _course_query(question)
    asks_personal_requirements = bool(re.search(
        r"\b(?:do|did|would)\s+i\s+(?:have|meet)|\bam\s+i\s+(?:eligible|qualified)|\bdo\s+i\s+qualify", text,
    ))
    if text in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
        intent = question_class = "greeting"
        scope = "institution"
    elif "campus" in text:
        intent = question_class = "campus_information"
        scope = "campus_directory"
        requested = ["campus_count"] if "how many" in text else ["campus_details"]
        reference = "follow_up_program" if text.startswith("more information") else "explicit_new_subject"
    elif ("how many" in text and ("program" in text or "course" in text)):
        intent = question_class = "institutional_counts"
        scope = "institution"
        requested = (["program_count"] if "program" in text else []) + (["course_count"] if "course" in text else [])
    elif asks_personal_requirements and subject_area != "nursing":
        intent = question_class = "admission_eligibility"
        scope = "program"
        requested = ["eligibility"]
        targets = re.findall(r"\bfor\s+(?:the\s+)?([^?.,]+(?:degree|diploma|certificate|program))", question, re.I)
        program_reference = targets[-1].strip() if targets else _entity_query(question)
    elif "red seal" in text and ("programs" in text or "any program" in text):
        intent = question_class = "red_seal_options"
        scope = "institution"
        requested = ["red_seal_pathways"]
    elif "international" in text and (subject_area or previous.discovery_query or previous.program_id
                                       or re.search(r"\b(?:this|that|the) program\b", text)):
        intent = question_class = "international_availability"
        scope = "program" if previous.program_id and not subject_area else "program_family"
        requested = ["international_availability", "program_list"]
        if not subject_area:
            subject_area = previous.discovery_query if previous.active_kind == "discovery" else None
            reference = "follow_up_program"
    elif re.search(r"\b(?:admission|requirements?)\b", text):
        intent = question_class = "admission_requirements"
        scope = "program"
        requested = ["admission_requirements"]
        program_reference = _entity_query(question)
    elif course_reference:
        intent = question_class = "course_facts"
        scope = "course"
    elif subject_area and ("program" in text or "list" in text or "offer" in text or "more" in text
                           or text in {_norm(subject_area), "technology", "engineering", "computing"}):
        intent = question_class = "program_discovery"
        scope = "program_area" if subject_area in {"Computing & IT", "Engineering"} else "program_family"
        requested = ["program_list"]
    elif _is_follow_up(question):
        intent = question_class = "program_facts"
        reference = "follow_up_program"
        scope = "program"
    else:
        intent = question_class = "program_facts"
        scope = "program"
        program_reference = _entity_query(question)
    return AdvisorV2Interpretation(
        intent=intent, question_class=question_class,
        program_reference=program_reference, subject_area=subject_area,
        course_reference=course_reference, reference_behavior=reference,
        ordinal_candidate=None, clarification_needed=False, clarification_reason=None,
        scope=scope, requested_facts=requested,
    )


def _answer_failure(result: dict[str, Any], subject: str) -> str:
    if result["status"] == "data_unavailable":
        return f"I couldn't retrieve {subject} because the academic data service is unavailable. This is not evidence that the information is absent."
    if result["status"] == "not_found":
        return f"I couldn't find {subject} in the active Asteris records."
    return f"I found more than one possible match for {subject}. Please choose one."


def _program_summary(item: dict[str, Any], *, include_link: bool = False) -> str:
    fields = [item.get("credential"), item.get("study_mode"), item.get("campus"), item.get("delivery_method")]
    details = "; ".join(str(value) for value in fields if value)
    overview = str(item.get("program_overview") or "").strip()
    if overview:
        sentences = re.split(r"(?<=[.!?])\s+", overview)
        overview = " ".join(sentences[:2])[:700].rstrip()
    answer = f"{item['program_name']} ({details})." + (f" {overview}" if overview else "")
    if include_link and item.get("source_url"):
        answer += f" Official program page: {item['source_url']}"
    return answer


def _display_course_id(item: dict[str, Any]) -> str:
    if item.get("display_course_code"):
        return str(item["display_course_code"])
    return re.sub(r"^([A-Z]+)(\d+)$", r"\1 \2", str(item["course_id"]))


def _condition_descriptions(groups: list[dict[str, Any]]):
    for group in groups:
        for condition in group.get("conditions", []):
            if condition.get("description"):
                yield condition["description"]
        yield from _condition_descriptions(group.get("children", []))


def answer_advisor_v2(question: str, *, conversation_state: AdvisorV2State | dict | None = None,
                      student_profile: StudentProfileV2 | dict | None = None,
                      repository: AdvisorV2Repository | None = None,
                      interpretation: AdvisorV2Interpretation | dict | None = None) -> dict[str, Any]:
    """Run one deterministic v2 turn, optionally using a non-authoritative interpretation."""
    repo = repository or AdvisorV2Repository()
    previous = AdvisorV2State.model_validate(conversation_state) if conversation_state else AdvisorV2State()
    interpreted = AdvisorV2Interpretation.model_validate(interpretation) if interpretation else None
    if interpreted is None:
        interpreted = _fallback_interpretation(question, previous)
    supplied = StudentProfileV2.model_validate(student_profile) if student_profile is not None else None
    interpreted_profile = None
    if interpreted is not None:
        facts = interpreted.student_facts.model_dump(exclude_none=True)
        facts["grades"] = {
            _subject_key(item["subject"]): item["value"] for item in facts.get("grades", [])
        }
        credential_gpas = {
            item["credential"]: item["value"] for item in facts.get("credential_gpas", [])
        }
        for key, value in list(credential_gpas.items()):
            if "construction operations" in _norm(key):
                credential_gpas["BRIDGING_CREDENTIAL_GPA"] = value
        facts["credential_gpas"] = credential_gpas
        months = {
            _subject_key(item["area"]): item["months"]
            for item in facts.get("work_experience_months_by_area", [])
        }
        facts["work_experience_months_by_area"] = months
        if months and facts.get("work_experience_years") is None:
            facts["work_experience_years"] = next(iter(months.values())) / 12
        if any(value not in (None, [], {}) for value in facts.values()):
            interpreted_profile = StudentProfileV2.model_validate(facts)
    next_turn = previous.turn_index + 1
    profile, model_updates, model_conflicts, provenance = _merge_profile(
        previous.student_profile, interpreted_profile, "", provenance=previous.profile_provenance,
        turn_index=next_turn, source="sol_extracted_explicit",
    )
    profile, profile_updates, profile_conflicts, provenance = _merge_profile(
        profile, supplied, question, provenance=provenance, turn_index=next_turn,
        source="request_profile_or_message",
    )
    profile_updates = list(dict.fromkeys(model_updates + profile_updates))
    profile_conflicts = list(dict.fromkeys(model_conflicts + profile_conflicts))
    state = AdvisorV2State(
        student_profile=profile, profile_provenance=provenance, turn_index=next_turn,
        recent_result_objects=list(previous.recent_result_objects),
        last_answer_shape=previous.last_answer_shape,
    )
    retrieval: list[dict[str, Any]] = []
    deterministic_decision: dict[str, Any] = {}
    lower = question.lower()
    course_query = interpreted.course_reference or _course_query(question)
    discovery = interpreted.intent == "program_discovery"
    profile_fact_follow_up = (_contains_profile_fact(question) and previous.active_kind == "program"
                              and previous.last_question_class == "admission_eligibility")
    model_follow_up = interpreted.reference_behavior in {
        "follow_up_program", "follow_up_course", "ordinal_candidate",
    }
    explicit_new_subject = interpreted.reference_behavior == "explicit_new_subject"
    follow_up = (_is_follow_up(question) or profile_fact_follow_up or model_follow_up) \
        and not explicit_new_subject and not discovery and course_query is None
    wants_admission = bool(re.search(r"\b(?:admission|admissions|eligible|eligibility|qualify|requirements?)\b", lower))
    if profile_fact_follow_up:
        wants_admission = True
    institutional_decision = bool(re.search(
        r"\b(?:will|would|can)\s+bcit\s+(?:accept|admit|approve)|\bguarantee(?:d)?\s+admission\b", lower
    ))
    wants_admission = interpreted.intent in {
        "admission_requirements", "admission_eligibility", "institutional_decision",
    } or wants_admission
    institutional_decision = interpreted.intent == "institutional_decision" or institutional_decision

    intent = interpreted.intent
    question_class = interpreted.question_class
    # Intent is the capability decision. The duplicate question_class field may
    # not demote a specific eligibility request to a rule summary.
    if intent == "admission_eligibility":
        question_class = "admission_eligibility"
    # Confirm the requested catalog object from the explicit current message.
    # This is entity-kind validation, not a competing intent router.
    if (re.search(r"\bcourses\b", lower) and course_query is None
            and not re.search(r"\bhow many\b", lower)):
        intent = question_class = "course_discovery"
        discovery = False
    if previous.active_kind == "campus_directory" and ("phone" in lower or "main" in lower):
        intent = question_class = "campus_information"
        discovery = False
        follow_up = True
    if (previous.active_kind == "discovery" and previous.discovery_query
            and interpreted.student_facts.international_status == "international"
            and interpreted.reference_behavior != "explicit_new_subject"):
        intent = question_class = "international_availability"
        discovery = False
        follow_up = True
    if (intent in {"program_facts", "program_discovery", "unknown"}
            and previous.active_kind == "discovery" and previous.discovery_query
            and _requests_program_collection(question)
            and not interpreted.subject_area and not interpreted.program_reference):
        intent = question_class = "program_discovery"
        discovery = True
        follow_up = True
    if (intent in {"program_discovery", "program_facts", "unknown"}
            and previous.active_kind in {"ambiguous", "program"}
            and _credential_markers(question)):
        intent = question_class = "program_facts"
        discovery = False
        follow_up = True
    if profile_fact_follow_up:
        intent = question_class = "admission_eligibility"
    if intent == "unknown":
        intent = question_class = "program_facts"
    state.last_question_class = question_class
    task_plan = _task_metadata(question, interpreted, previous)
    state.last_answer_shape = task_plan["answer_shape"]
    resolved_referent, referent_source = _resolve_prior_referent(question, previous, task_plan)

    context_action = "none"
    if previous.turn_index:
        context_action = "inherited" if follow_up and previous.active_kind in {"program", "course"} else (
            "preserved_ambiguous" if follow_up and previous.active_kind in {"ambiguous", "discovery"} else "reset"
        )
    observation: dict[str, Any] = {
        "current_message": question,
        "turn_index": state.turn_index,
        "detected_intent": intent,
        "question_class": question_class,
        "entity_resolution": {"kind": "none", "query": None, "status": "not_attempted", "candidates": []},
        "context": {"action": context_action, "previous_kind": previous.active_kind,
                    "inherited_program_id": previous.program_id if context_action == "inherited" else None,
                    "inherited_course_id": previous.course_id if context_action == "inherited" else None},
        "retrieval": [],
        "rule_evaluation_status": "not_invoked",
        "profile": {"updated_fields": profile_updates, "conflicting_fields": profile_conflicts,
                    "provenance": provenance},
        "final_response_path": None,
        "task_plan": task_plan,
        "referent_resolution": {
            "source": referent_source,
            "program_id": (resolved_referent or {}).get("program_id"),
            "status": "resolved" if resolved_referent else "not_resolved",
        },
        "answer_shape_decision": task_plan["answer_shape"],
        "selected_evidence_objects": [],
        "links_requested": bool(re.search(r"\b(?:link|links|url|website|official page)\b", lower)),
    }
    if referent_source == "prior_result_credential":
        observation["context"]["action"] = "resolved_credential"
    elif referent_source == "prior_result_ordinal":
        observation["context"]["action"] = "resolved_ordinal"
    elif previous.active_kind == "program" and _credential_markers(question):
        observation["context"]["action"] = "resolved_credential"

    def finish(answer: str, path: str, resolved_program: str | None = None) -> dict[str, Any]:
        observation["retrieval"] = [
            {"capability": item["capability"], "status": item["status"], "detail": item.get("detail")}
            for item in retrieval
        ]
        observation["final_response_path"] = path
        evidence_objects = [
            {"evidence_id": f"E{index + 1}", "fact": line}
            for index, line in enumerate(line.strip() for line in answer.splitlines()) if line
        ]
        observation["selected_evidence_objects"] = evidence_objects
        return _response(answer, state, retrieval, resolved_program, observation,
                         evidence_objects=evidence_objects,
                         deterministic_decision=deterministic_decision)

    # Contextual selection happens before family or global fuzzy retrieval.
    if resolved_referent and referent_source == "prior_result_filter":
        program_id = str(resolved_referent["program_id"])
        retrieval.append(_result(
            "found", "reuse_prior_result",
            data=resolved_referent,
            evidence_ids=[f"delivery:{program_id}"],
            detail="source=durable_conversation_state",
        ))
        state.active_kind, state.program_id = "program", program_id
        state.recent_result_objects = [resolved_referent]
        name = str(resolved_referent.get("program_name") or program_id)
        status = str(resolved_referent.get("international_eligibility") or "")
        deterministic_decision.update({
            "kind": "international_availability", "status": "unavailable",
            "required_phrase": "unavailable to international applicants",
        })
        return finish(
            f"The one that is unavailable to international applicants is {name}.",
            "prior_result_filtered_selection", program_id,
        )

    if (intent == "international_availability" and resolved_referent
            and resolved_referent.get("program_id")
            and referent_source in {"prior_result_exact", "active_program_id", "prior_result_ordinal", "prior_result_credential"}):
        program_id = str(resolved_referent["program_id"])
        found = repo.get_program_international_availability(program_id)
        retrieval.append(found)
        observation["entity_resolution"] = {
            "kind": "program", "query": program_id, "status": found["status"], "candidates": [],
        }
        if found["status"] != "found":
            return finish(_answer_failure(found, f"international availability for {program_id}"),
                          "international_availability_failure", program_id)
        item = found["data"]
        state.active_kind, state.program_id = "program", program_id
        state.recent_result_objects = [_result_object(item)]
        status = str(item.get("international_eligibility") or "").rstrip(".")
        deterministic_decision.update({
            "kind": "international_availability", "status": status,
            "required_phrase": status,
        })
        return finish(f"{item['program_name']}: {status}.",
                      "single_program_international_availability", program_id)

    if intent == "greeting":
        observation["entity_resolution"] = {
            "kind": "institution", "query": "BCIT", "status": "conversation_opening", "candidates": [],
        }
        return finish(
            "Hello! I can help with BCIT programs, courses, admission requirements, campuses, and international availability.",
            "greeting",
        )

    if intent == "institutional_counts":
        found = repo.get_catalog_counts()
        retrieval.append(found)
        observation["entity_resolution"] = {
            "kind": "institution", "query": interpreted.subject_area, "status": found["status"], "candidates": [],
        }
        if found["status"] != "found":
            return finish(_answer_failure(found, "catalog counts"), "institutional_counts_failure")
        counts = found["data"]
        requested = set(interpreted.requested_facts)
        if interpreted.subject_area and _norm(interpreted.subject_area) == "technology":
            answer = (
                f"BCIT has {counts['active_programs']} active programs across its academic areas. "
                f"If you mean programs whose credential is specifically Bachelor of Technology, there are "
                f"{counts['bachelor_of_technology_programs']}."
            )
        elif {"program_count", "course_count"} <= requested or ("program" in lower and "course" in lower):
            answer = f"BCIT has {counts['active_programs']} active programs and {counts['active_courses']} active courses."
        elif "course_count" in requested or "course" in lower:
            answer = f"BCIT has {counts['active_courses']} active courses."
        else:
            answer = f"BCIT has {counts['active_programs']} active programs."
        return finish(answer, "institutional_counts")

    if intent == "campus_information":
        found = repo.get_campus_directory()
        retrieval.append(found)
        observation["entity_resolution"] = {
            "kind": "campus_directory", "query": "BCIT campuses", "status": found["status"], "candidates": [],
        }
        if found["status"] != "found":
            return finish(_answer_failure(found, "campus information"), "campus_information_failure")
        campuses = found["data"]["campuses"]
        state.active_kind = "campus_directory"
        wants_phone = "phone" in interpreted.requested_facts or "phone" in lower
        wants_main = "main_campus" in interpreted.requested_facts or bool(re.search(r"\bmain\b", lower))
        wants_details = "campus_details" in interpreted.requested_facts or "more information" in lower
        if wants_phone:
            phone = next((row.get("main_phone") for row in campuses if row.get("main_phone")), None)
            answer = f"BCIT's main general phone number is {phone}." if phone else "BCIT's main phone number is not recorded."
        elif wants_main:
            main = next((row for row in campuses if "largest campus" in str(row.get("description") or "").lower()), None)
            if main:
                answer = (
                    f"If by main campus you mean BCIT's largest campus, that is {main['official_name']} — "
                    f"{main.get('address')}, {main.get('city')}, {main.get('region')} {main.get('postal_code')}."
                )
            else:
                answer = "The campus records do not designate one campus as the main campus."
        elif wants_details:
            lines = []
            for campus in campuses:
                address = ", ".join(str(value) for value in (
                    campus.get("address"), campus.get("city"), campus.get("region"), campus.get("postal_code")
                ) if value)
                detail = f"{campus['official_name']} — {address}"
                if campus.get("description"):
                    detail += f" — {str(campus['description']).rstrip('.')}"
                lines.append(detail + ".")
            answer = "BCIT's campuses are:\n" + "\n".join(f"• {line}" for line in lines)
        else:
            answer = f"BCIT has {len(campuses)} campuses: " + ", ".join(row["official_name"] for row in campuses) + "."
        return finish(answer, "campus_directory")

    if intent == "red_seal_options":
        found = repo.find_red_seal_programs()
        retrieval.append(found)
        observation["entity_resolution"] = {
            "kind": "program_set", "query": "Red Seal admission evidence", "status": found["status"], "candidates": [],
        }
        if found["status"] != "found":
            return finish(_answer_failure(found, "programs with Red Seal admission evidence"), "red_seal_options_failure")
        programs = found["data"]["programs"]
        state.active_kind = "discovery"
        state.discovery_query = "Red Seal admission pathways"
        state.candidate_program_ids = [row["program_id"] for row in programs]
        lines = [f"{row['program_name']} — {row.get('credential') or 'credential not recorded'} — {row['source_url']}"
                 for row in programs]
        answer = (
            "These active BCIT programs have published admission evidence involving a Red Seal:\n"
            + "\n".join(f"• {line}" for line in lines)
            + "\nA Red Seal can satisfy only the stated pathway; each program may have additional requirements."
        )
        return finish(answer, "red_seal_program_options")

    if intent == "international_availability":
        family = interpreted.subject_area or interpreted.program_reference or (
            previous.discovery_query if interpreted.reference_behavior != "explicit_new_subject"
            and previous.active_kind == "discovery" else ""
        )
        found = repo.get_international_availability(family)
        retrieval.append(found)
        observation["entity_resolution"] = {
            "kind": "program_family", "query": family, "status": found["status"], "candidates": [],
        }
        if found["status"] != "found":
            return finish(_answer_failure(found, f"international availability for {family}"),
                          "international_availability_failure")
        programs = found["data"]["programs"]
        state.active_kind = "discovery"
        state.discovery_query = family
        state.candidate_program_ids = [row["program_id"] for row in programs]
        state.recent_result_objects = [_result_object(row) for row in programs]
        available, unavailable, conditional = [], [], []
        for row in programs:
            status_text = str(row.get("international_eligibility") or "")
            target = (unavailable if "not available" in status_text.lower() else
                      conditional if status_text.lower().startswith("refer") else available)
            target.append(row)
        parts = []
        exhaustive = task_plan["answer_shape"] == "exhaustive_list"
        include_links = observation["links_requested"]
        def names(rows: list[dict[str, Any]], limit: int | None = None) -> str:
            chosen = rows if limit is None else rows[:limit]
            rendered = []
            for row in chosen:
                line = row["program_name"]
                if include_links:
                    line += f" — {row['source_url']}"
                rendered.append(f"• {line}")
            return "\n".join(rendered)
        if exhaustive:
            if available:
                parts.append("Available to international applicants:\n" + names(available))
            if conditional:
                parts.append("Check the official program page for current availability:\n" + names(conditional))
            if unavailable:
                parts.append("Unavailable to international applicants:\n" + names(unavailable))
        else:
            if available:
                credentials = sorted({str(row.get("credential") or "credential not recorded") for row in available})
                parts.append(
                    f"BCIT lists {len(available)} {family} programs as available to international applicants, "
                    f"mainly {', '.join(credentials)}. Examples include "
                    + "; ".join(row["program_name"] for row in available[:4]) + "."
                )
            if conditional:
                parts.append(f"{len(conditional)} additional program(s) require checking the official program page.")
            if unavailable:
                parts.append("Unavailable: " + "; ".join(row["program_name"] for row in unavailable) + ".")
        return finish("\n".join(parts), "international_program_availability")

    if intent == "course_discovery":
        query = interpreted.subject_area or interpreted.course_reference
        if not query:
            subject_tokens = _tokens(question) - {"course", "courses", "overall", "offer"}
            query = " ".join(sorted(subject_tokens))
        found = repo.search_courses(query)
        retrieval.append(found)
        observation["entity_resolution"] = {
            "kind": "course_set", "query": query, "status": found["status"], "candidates": [],
        }
        if found["status"] != "found":
            return finish(_answer_failure(found, f"courses matching {query}"), "course_discovery_failure")
        courses = found["data"]["courses"]
        lines = [f"{_display_course_id(item)} — {item['course_name']}" for item in courses]
        state.active_kind, state.discovery_query = "discovery", query
        return finish(
            f"BCIT has {len(courses)} matching active courses for {query}:\n" + "\n".join(f"• {line}" for line in lines),
            "course_discovery",
        )

    pre_resolved = None
    if discovery:
        query = (
            interpreted.subject_area
            or interpreted.program_reference
            or (previous.discovery_query if follow_up and previous.active_kind == "discovery" else None)
            or (_norm(question) if _is_broad_program_query(question) else _discovery_query(question))
        )
        if (interpreted.program_reference and not _requests_program_collection(question)
                and repo._canonical_area(query) is None):
            candidate = repo.resolve_program(query)
            retrieval.append(candidate)
            if candidate["status"] == "found":
                pre_resolved = candidate
                discovery = False
                intent = question_class = "program_facts"
            elif candidate["status"] == "ambiguous":
                programs = candidate["data"]["programs"]
                state.active_kind = "ambiguous"
                state.candidate_program_ids = [item["program_id"] for item in programs]
                observation["entity_resolution"] = {
                    "kind": "program", "query": query, "status": "ambiguous",
                    "candidates": candidate["data"].get("candidates", []),
                }
                choices = "\n".join(
                    f"• {item['program_name']} — {item.get('credential') or 'credential not recorded'}"
                    for item in programs
                )
                return finish("I found several possible programs. Which one do you mean?\n" + choices,
                              "program_ambiguity_clarification")
        if discovery:
            found = (repo.list_programs_by_area(query) if interpreted.scope == "program_area"
                     else repo.search_program_family(query, limit=100))
            if found["status"] == "not_found" and found["capability"] == "list_programs_by_area":
                family_found = repo.search_program_family(query, limit=100)
                retrieval.append(found)
                found = family_found
        if discovery:
            retrieval.append(found)
            observation["entity_resolution"] = {
                "kind": "program", "query": query, "status": "discovery_set" if found["status"] == "found" else found["status"],
                "candidates": (found.get("data") or {}).get("candidates", []),
            }
            if found["status"] == "found":
                programs = found["data"]["programs"]
                state.active_kind, state.discovery_query = "discovery", query
                state.candidate_program_ids = [item["program_id"] for item in programs]
                state.recent_result_objects = [_result_object(item) for item in programs]
                lines = [f"{item['program_name']} — {item.get('credential') or 'credential not recorded'}" for item in programs]
                total = found["data"].get("total", len(programs))
                label = found["data"].get("canonical_area", query)
                if task_plan["answer_shape"] == "exhaustive_list":
                    answer = f"BCIT has {total} active programs in {label}:\n" + "\n".join(f"• {line}" for line in lines)
                elif found["capability"] == "list_programs_by_area":
                    groups: dict[str, list[str]] = {}
                    for item in programs:
                        credential = str(item.get("credential") or "Other credentials")
                        if "Bachelor" in credential:
                            group = "Bachelor's degrees"
                        elif "Master" in credential:
                            group = "Master's degrees"
                        elif "Diploma" in credential:
                            group = "Diplomas"
                        elif "Certificate" in credential:
                            group = "Certificates"
                        elif "Microcredential" in credential:
                            group = "Microcredentials"
                        else:
                            group = "Other credentials"
                        groups.setdefault(group, []).append(item["program_name"])
                    order = ["Bachelor's degrees", "Master's degrees", "Diplomas", "Certificates", "Microcredentials", "Other credentials"]
                    summaries = []
                    for group in order:
                        if group not in groups:
                            continue
                        examples = ", ".join(groups[group][:4])
                        suffix = "" if len(groups[group]) <= 4 else f", and {len(groups[group]) - 4} more"
                        summaries.append(f"• {group} ({len(groups[group])}): {examples}{suffix}")
                    answer = (
                        f"Yes. BCIT has {total} active programs in {label}, across these credential groups:\n"
                        + "\n".join(summaries)
                        + "\nI can list every program if you want the full catalogue."
                    )
                else:
                    shown = lines[:8]
                    answer = f"BCIT has {total} active programs related to {label}. Here are the most relevant matches:\n" + "\n".join(f"• {line}" for line in shown)
                    if len(lines) > len(shown):
                        answer += f"\nThere are {len(lines) - len(shown)} more in this result set."
                return finish(answer, "taxonomy_program_discovery" if found["capability"] == "list_programs_by_area" else "program_family_discovery")
            answer = _answer_failure(found, f"programs matching {query}")
            return finish(answer, "program_discovery_failure")

    credential_program_id = None
    if previous.active_kind == "ambiguous" and _credential_markers(question):
        credential_choice = repo.resolve_candidate_credential(previous.candidate_program_ids, question)
        retrieval.append(credential_choice)
        if credential_choice["status"] == "found":
            credential_program_id = credential_choice["data"]["program_id"]
            follow_up = True
            observation["context"]["action"] = "resolved_credential"

    has_valid_ordinal = bool(
        interpreted and interpreted.reference_behavior == "ordinal_candidate"
        and interpreted.ordinal_candidate is not None
        and 0 < interpreted.ordinal_candidate <= len(previous.candidate_program_ids)
    )
    if (follow_up and previous.active_kind in {"ambiguous", "discovery"}
            and not has_valid_ordinal and credential_program_id is None
            and not (resolved_referent and resolved_referent.get("program_id"))):
        state.active_kind = previous.active_kind
        state.discovery_query = previous.discovery_query
        state.candidate_program_ids = list(previous.candidate_program_ids)
        observation["entity_resolution"] = {
            "kind": "program", "query": previous.discovery_query, "status": "ambiguous_context",
            "candidates": [{"program_id": item} for item in previous.candidate_program_ids],
        }
        return finish("That reference could point to more than one program. Please name the program you mean.",
                      "ambiguous_context_clarification")

    effective_course = course_query or (previous.course_id if follow_up and previous.active_kind == "course" else None)
    if effective_course:
        found = repo.get_course_facts(effective_course)
        retrieval.append(found)
        observation["entity_resolution"] = {
            "kind": "course", "query": effective_course, "status": found["status"],
            "candidates": ([{"course_id": found["data"]["course_id"]}]
                           if found["status"] == "found" else []),
        }
        if found["status"] != "found":
            return finish(_answer_failure(found, effective_course), "course_facts_failure")
        item = found["data"]
        state.active_kind, state.course_id = "course", item["course_id"]
        code = _display_course_id(item)
        wants_course_eligibility = bool(re.search(r"\b(?:eligible|qualify|take|register|enroll)\b", lower))
        if wants_course_eligibility:
            evaluated = repo.evaluate_course_eligibility(item["course_id"], profile)
            retrieval.append(evaluated)
            status = (evaluated.get("data") or {}).get("status", "retrieval_failure")
            observation["rule_evaluation_status"] = status
            labels = {
                "met": "the recorded prerequisites are met",
                "unmet": "at least one recorded prerequisite is not met",
                "missing_student_information": "more information about your prior study is needed",
                "human_review_required": "BCIT review is required for at least one prerequisite",
                "evidence_unavailable": "prerequisite evidence is unavailable",
                "retrieval_failure": "the prerequisite service failed",
            }
            answer = f"For {code}, {labels[status]}."
            needed = (evaluated.get("data") or {}).get("needed_student_fields", [])
            if needed:
                answer += " Needed from you: " + ", ".join(needed) + "."
            return finish(answer, "deterministic_course_eligibility", resolved_program=None)
        answer = f"{code}: {item['course_name']}."
        if item.get("credits") is not None:
            answer += f" Credits: {item['credits']}."
        if item.get("course_overview"):
            answer += f" {item['course_overview']}"
        return finish(answer, "course_facts")

    ordinal_program_id = None
    if (interpreted and interpreted.reference_behavior == "ordinal_candidate"
            and interpreted.ordinal_candidate is not None
            and previous.active_kind in {"ambiguous", "discovery"}):
        index = interpreted.ordinal_candidate - 1
        if 0 <= index < len(previous.candidate_program_ids):
            ordinal_program_id = previous.candidate_program_ids[index]
            observation["context"]["action"] = "resolved_ordinal"
    contextual_program_id = (
        str(resolved_referent.get("program_id"))
        if resolved_referent and resolved_referent.get("program_id") else None
    )
    program_id = contextual_program_id or credential_program_id or ordinal_program_id or (
        previous.program_id if follow_up and previous.active_kind == "program" else None
    )
    if follow_up and not program_id:
        observation["entity_resolution"]["status"] = "missing_context"
        return finish("I don't have one resolved program to apply that reference to. Please name the program.",
                      "missing_context_clarification")
    if pre_resolved is not None:
        program_id = pre_resolved["data"]["program_id"]
        observation["entity_resolution"] = {
            "kind": "program", "query": pre_resolved["data"].get("program_name"),
            "status": "semantic_proposal_confirmed", "candidates": [],
        }
    if not program_id:
        query = (interpreted.program_reference if interpreted and interpreted.program_reference else None) or _entity_query(question)
        resolved = repo.resolve_program(query)
        retrieval.append(resolved)
        data = resolved.get("data") or {}
        observation["entity_resolution"] = {
            "kind": "program", "query": query, "status": resolved["status"],
            "candidates": data.get("candidates") or (data.get("resolution") or {}).get("candidates", []),
        }
        if resolved["status"] != "found":
            if resolved["status"] == "ambiguous":
                candidates = data["programs"]
                state.active_kind = "ambiguous"
                state.candidate_program_ids = [item["program_id"] for item in candidates]
                choices = "\n".join(f"• {item['program_name']} — {item.get('credential') or 'credential not recorded'}" for item in candidates)
                answer = "I found several possible programs. Which one do you mean?\n" + choices
                return finish(answer, "program_ambiguity_clarification")
            return finish(_answer_failure(resolved, query or "that program"), "program_resolution_failure")
        program_id = data["program_id"]
    else:
        observation["entity_resolution"] = {
            "kind": "program", "query": None,
            "status": ("prior_result_confirmed" if contextual_program_id else
                       "ordinal_candidate_confirmed" if ordinal_program_id else "inherited_confident"),
            "candidates": [{"program_id": program_id}],
        }

    facts = repo.get_program_facts(program_id)
    retrieval.append(facts)
    if facts["status"] != "found":
        return finish(_answer_failure(facts, program_id), "program_facts_failure")
    item = facts["data"]
    state.active_kind, state.program_id = "program", program_id
    state.recent_result_objects = [_result_object(item)]

    if institutional_decision:
        observation["rule_evaluation_status"] = "human_review_required"
        return finish(
            f"I can summarize recorded requirements for {item['program_name']}, but only BCIT can make or guarantee an admission decision.",
            "institutional_decision_boundary", program_id,
        )
    if question_class == "admission_eligibility":
        evaluated = repo.evaluate_admission(program_id, profile)
        retrieval.append(evaluated)
        if evaluated["status"] == "found":
            status = evaluated["data"]["status"]
            observation["rule_evaluation_status"] = status
            labels = {"met": "the modeled requirements are met",
                      "unmet": "at least one modeled requirement is not met",
                      "missing_student_information": "more student information is needed",
                      "human_review_required": "BCIT review is required",
                      "evidence_unavailable": "the institutional rule evidence is unavailable",
                      "retrieval_failure": "the rule service failed, so eligibility could not be evaluated"}
            deterministic_decision.update({
                "kind": "eligibility", "status": status,
                "required_phrase": labels[status],
            })
            answer = f"For {item['program_name']}, {labels[status]}."
            rule_sets = evaluated["data"].get("rule_sets", [])
            selected_conditions: list[dict[str, Any]] = []
            if rule_sets and rule_sets[0].get("groups"):
                root = rule_sets[0]["groups"][0]
                selected_conditions.extend(root.get("conditions", []))
                for child in root.get("children", []):
                    branches = child.get("children", [])
                    if branches:
                        relevant = None
                        if profile.red_seal_trade:
                            relevant = next((branch for branch in branches if any(
                                condition.get("condition_type") == "RED_SEAL_TRADE"
                                for condition in branch.get("conditions", [])
                            )), None)
                        relevant = relevant or max(
                            branches,
                            key=lambda branch: sum(c.get("status") == "met" for c in branch.get("conditions", [])),
                        )
                        selected_conditions.extend(relevant.get("conditions", []))
            if selected_conditions:
                status_words = {
                    "met": "met", "unmet": "not met", "missing_student_information": "not yet provided",
                    "human_review_required": "requires BCIT review", "evidence_unavailable": "evidence unavailable",
                    "retrieval_failure": "retrieval failed",
                }
                lines = []
                # A direct eligibility answer should explain blockers and
                # unresolved checks, not dump every passing rule.
                decisive = [condition for condition in selected_conditions if condition.get("status") != "met"]
                for condition in decisive:
                    description = condition.get("description") or condition.get("condition_type")
                    reported = condition.get("reported_value")
                    minimum = condition.get("minimum_value")
                    suffix = ""
                    if reported is not None:
                        if (isinstance(reported, (int, float)) and isinstance(minimum, (int, float))
                                and minimum == 1 and "year" in str(description).lower()
                                and 0 <= reported < 2):
                            suffix += f"; you reported {round(reported * 12):g} months"
                        else:
                            suffix += f"; you reported {reported}"
                    if minimum is not None:
                        suffix += f"; minimum {minimum}"
                    lines.append(f"{status_words.get(condition['status'], condition['status'])}: {description}{suffix}")
                if lines:
                    answer += "\n" + "\n".join(f"• {line}" for line in lines)
            needed = evaluated["data"].get("needed_student_fields", [])
            if needed:
                answer += " Needed from you: " + ", ".join(needed) + "."
            return finish(answer, "deterministic_rule_evaluation", program_id)
        failure_status = ((evaluated.get("data") or {}).get("status") or
                          ("retrieval_failure" if evaluated["status"] == "data_unavailable" else "evidence_unavailable"))
        observation["rule_evaluation_status"] = failure_status
        return finish(_answer_failure(evaluated, f"admission rules for {item['program_name']}"),
                      "rule_evaluation_failure", program_id)
    if wants_admission:
        rules = repo.get_admission_rules(program_id)
        retrieval.append(rules)
        if rules["status"] == "found":
            descriptions = []
            for rule in rules["data"]["rule_sets"]:
                descriptions.extend(_condition_descriptions(rule.get("groups", [])))
            answer = f"Admission requirements recorded for {item['program_name']}:\n" + "\n".join(f"• {line}" for line in descriptions)
            return finish(answer, "admission_rule_summary", program_id)
        return finish(_answer_failure(rules, f"admission rules for {item['program_name']}"),
                      "admission_rule_retrieval_failure", program_id)
    return finish(_program_summary(item, include_link=observation["links_requested"]), "program_facts", program_id)


def _response(answer: str, state: AdvisorV2State, retrieval: list[dict[str, Any]],
              resolved_program: str | None, observability: dict[str, Any], *,
              evidence_objects: list[dict[str, Any]] | None = None,
              deterministic_decision: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = [identifier for item in retrieval for identifier in item.get("evidence_ids", [])]
    statuses = [item["status"] for item in retrieval]
    verification_status = "data_unavailable" if "data_unavailable" in statuses else (
        "grounded" if evidence else "unverified"
    )
    return {"answer": answer, "conversation_state": state.model_dump(),
            "resolved_program": resolved_program, "retrieval": retrieval,
            "evidence_objects": evidence_objects or [],
            "deterministic_decision": deterministic_decision or {},
            "observability": observability,
            "verification": {"status": verification_status,
                             "label": "Academic records consulted" if evidence else None,
                             "evidence_ids": list(dict.fromkeys(evidence))},
            "usage": {"model": None, "input_tokens": 0, "output_tokens": 0}}


def answer_advisor_v2_hybrid(question: str, *,
                             conversation_state: AdvisorV2State | dict | None = None,
                             student_profile: StudentProfileV2 | dict | None = None,
                             repository: AdvisorV2Repository | None = None,
                             language_layer: SolLanguageLayer | None = None) -> dict[str, Any]:
    """Interpret -> deterministic execution -> constrained rendering.

    Either model call may fail independently. The returned answer and state then
    remain the Phase 2 deterministic result.
    """
    previous = AdvisorV2State.model_validate(conversation_state) if conversation_state else AdvisorV2State()
    interpretation_payload = compact_interpretation_payload(question, previous)
    interpretation = None
    interpretation_status = "disabled"
    interpretation_error = None
    interpretation_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    interpretation_started = time.perf_counter()
    total_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    if language_layer is not None:
        try:
            interpretation, used = language_layer.interpret(interpretation_payload)
            interpretation_usage = {key: used.get(key, 0) for key in interpretation_usage}
            interpretation_status = "ok"
            for key in total_usage:
                total_usage[key] += used.get(key, 0)
        except Exception as error:  # external timeout, transport, refusal, or schema mismatch
            interpretation_status = "fallback"
            interpretation_error = safe_error_name(error)

    result = answer_advisor_v2(
        question,
        conversation_state=previous,
        student_profile=student_profile,
        repository=repository,
        interpretation=interpretation,
    )
    observed = result["observability"]
    proposed = {
        "program_reference": interpretation.program_reference if interpretation else None,
        "subject_area": interpretation.subject_area if interpretation else None,
        "course_reference": interpretation.course_reference if interpretation else None,
        "reference_behavior": interpretation.reference_behavior if interpretation else None,
        "ordinal_candidate": interpretation.ordinal_candidate if interpretation else None,
    }
    observed["interpretation"] = {
        "model": SOL_MODEL if language_layer is not None else None,
        "status": interpretation_status,
        "error_class": interpretation_error,
        "payload": interpretation_payload,
        "result": interpretation.model_dump() if interpretation else None,
        "usage": interpretation_usage,
        "latency_ms": round((time.perf_counter() - interpretation_started) * 1000, 2),
    }
    observed["entity_proposal_confirmation"] = {
        "proposals": proposed,
        "confirmation": observed["entity_resolution"],
        "authority": "deterministic_repository",
    }
    synth_input = synthesis_payload(result)
    observed["synthesis"] = {
        "model": SOL_MODEL if language_layer is not None else None,
        "status": ("disabled" if language_layer is None else
                   "not_attempted" if interpretation_status == "ok" else
                   "skipped_interpretation_fallback"),
        "inputs": synth_input,
        "result": None,
        "error_class": None,
        "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
        "latency_ms": 0,
    }
    observed["grounding_validation"] = {
        "status": "not_attempted", "validated_claim_ids": [], "fallback_reason": None,
    }
    observed["final_response_source"] = "deterministic_phase2"

    if language_layer is not None and interpretation_status == "ok":
        synthesis_started = time.perf_counter()
        try:
            plan, used = language_layer.synthesize(synth_input)
            if plan.answer_text:
                rendered = validate_grounded_answer(plan, synth_input)
                observed["grounding_validation"] = {
                    "status": "passed", "validated_claim_ids": plan.claim_ids,
                    "fallback_reason": None,
                }
            else:
                rendered = render_synthesis(
                    result["answer"], plan,
                    path=observed["final_response_path"],
                    evaluation_status=observed["rule_evaluation_status"],
                    verification_status=result["verification"]["status"],
                )
                observed["grounding_validation"] = {
                    "status": "legacy_exact_fact_renderer", "validated_claim_ids": plan.fact_ids,
                    "fallback_reason": None,
                }
            result["answer"] = rendered
            observed["synthesis"].update({"status": "ok", "result": plan.model_dump()})
            observed["synthesis"]["usage"] = {key: used.get(key, 0) for key in total_usage}
            observed["final_response_source"] = (
                "sol_grounded_synthesis" if plan.answer_text else "sol_constrained_renderer"
            )
            for key in total_usage:
                total_usage[key] += used.get(key, 0)
        except Exception as error:
            observed["synthesis"].update({
                "status": "fallback", "error_class": safe_error_name(error),
            })
            observed["grounding_validation"] = {
                "status": "failed", "validated_claim_ids": [],
                "fallback_reason": safe_error_name(error),
            }
        finally:
            observed["synthesis"]["latency_ms"] = round((time.perf_counter() - synthesis_started) * 1000, 2)

    if language_layer is not None:
        result["usage"] = {"model": SOL_MODEL, **total_usage}
    return result
