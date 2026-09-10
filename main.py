import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import logging
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import uuid
from typing import Literal

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import database_ready, get_connection
from eligibility import check_course_eligibility
from program_requirements import check_program_progress
from progression import check_progression
from ai_advisor import AdvisorServiceError, answer_student_question
from conversation_state import TopicState
from advisor_eligibility import find_eligible_courses
from advisor_engine import run_advisor_engine
from academic_rules import get_course_requirements, get_program_curriculum, get_program_rules
from advisor import clean_course_title, display_course_code
from advisor_v2 import AdvisorV2State, StudentProfileV2, answer_advisor_v2_hybrid
import advisor_v2 as advisor_v2_module
import advisor_v2_sol as advisor_v2_sol_module
from advisor_v2_sol import MODEL as ADVISOR_V2_MODEL, REASONING_EFFORT as ADVISOR_V2_REASONING_EFFORT, available_default_layer
from advisor_v3 import AdvisorV3State, answer_advisor_v3
import advisor_v3 as advisor_v3_module
import advisor_v3_sol as advisor_v3_sol_module
from advisor_v3_sol import MODEL as ADVISOR_V3_MODEL, REASONING_EFFORT as ADVISOR_V3_REASONING_EFFORT, available_v3_layer
from production_config import SAFE_ID, SETTINGS, SlidingWindowLimiter, configure_logging, opaque_identifier

app = FastAPI(
    title="Asteris API",
    docs_url=None if SETTINGS.production else "/docs",
    redoc_url=None if SETTINGS.production else "/redoc",
    openapi_url=None if SETTINGS.production else "/openapi.json",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
if SETTINGS.production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(SETTINGS.allowed_hosts))
if SETTINGS.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(SETTINGS.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID", "X-Session-ID"],
    )

logger = configure_logging()
advisor_limiter = SlidingWindowLimiter(SETTINGS.rate_limit_per_minute)
advisor_capacity = asyncio.Semaphore(SETTINGS.max_concurrent_advisor_requests)
PUBLIC_PRODUCTION_PATHS = {"/", "/app", "/health/live", "/health/ready", "/ask", "/advisor"}


def _safe_error(status: int, code: str, message: str, request_id: str, retry_after: int | None = None):
    headers = {"X-Request-ID": request_id}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(status_code=status, content={"detail": message, "error": code, "request_id": request_id}, headers=headers)


@app.middleware("http")
async def production_controls(request: Request, call_next):
    started = time.perf_counter()
    supplied_id = request.headers.get("x-request-id")
    request_id = supplied_id if supplied_id and SAFE_ID.fullmatch(supplied_id) else uuid.uuid4().hex
    request.state.request_id = request_id
    session_source = request.headers.get("x-session-id") or (request.client.host if request.client else None)
    session_id = opaque_identifier(session_source)
    path = request.url.path
    acquired = False
    status = 500
    outcome = "error"
    try:
        if SETTINGS.production and not (path in PUBLIC_PRODUCTION_PATHS or path.startswith("/static/")):
            supplied_key = request.headers.get("x-asteris-internal-key", "")
            if not SETTINGS.internal_api_key or not secrets.compare_digest(supplied_key, SETTINGS.internal_api_key):
                status, outcome = 404, "internal_endpoint_denied"
                return _safe_error(404, "not_found", "Not found", request_id)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                status, outcome = 400, "invalid_content_length"
                return _safe_error(400, "invalid_request", "Invalid request", request_id)
            if declared_size > SETTINGS.max_request_bytes:
                status, outcome = 413, "request_too_large"
                return _safe_error(413, "request_too_large", "Request is too large", request_id)

        if request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()
            if len(body) > SETTINGS.max_request_bytes:
                status, outcome = 413, "request_too_large"
                return _safe_error(413, "request_too_large", "Request is too large", request_id)

        if path in {"/advisor", "/ask"} and SETTINGS.production:
            allowed, retry_after = advisor_limiter.allow(session_id)
            if not allowed:
                status, outcome = 429, "rate_limited"
                return _safe_error(429, "rate_limited", "Too many requests. Please wait and try again.", request_id, retry_after)
            try:
                await asyncio.wait_for(advisor_capacity.acquire(), timeout=0.1)
                acquired = True
            except TimeoutError:
                status, outcome = 503, "advisor_busy"
                return _safe_error(503, "advisor_busy", "The advisor is busy. Please try again shortly.", request_id, 1)

        response = await call_next(request)
        status = response.status_code
        outcome = "ok" if status < 400 else "client_or_dependency_error"
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        if acquired:
            advisor_capacity.release()
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "endpoint": path,
                "method": request.method,
                "status": status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "outcome": outcome,
            },
        )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    return _safe_error(422, "invalid_request", "The request format is invalid", request_id)


@app.exception_handler(AdvisorServiceError)
async def advisor_service_error_handler(request: Request, error: AdvisorServiceError):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    logger.warning("advisor_dependency_error", extra={"request_id": request_id, "endpoint": request.url.path, "error_class": error.error_class, "outcome": "dependency_error"})
    return _safe_error(error.status_code, error.error_class, error.public_message, request_id, error.retry_after)


@app.exception_handler(psycopg.Error)
async def database_error_handler(request: Request, error: psycopg.Error):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    logger.error("database_unavailable", extra={"request_id": request_id, "endpoint": request.url.path, "error_class": type(error).__name__, "outcome": "dependency_error"})
    return _safe_error(503, "database_unavailable", "Academic data is temporarily unavailable. Please try again shortly.", request_id, 5)


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    logger.exception("unhandled_error", extra={"request_id": request_id, "endpoint": request.url.path, "error_class": type(error).__name__, "outcome": "error"})
    return _safe_error(500, "internal_error", "Asteris could not complete the request", request_id)

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class CompletedCourse(BaseModel):
    course_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9 _:-]+$")
    grade: float | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4_000)


class EligibilityRequest(BaseModel):
    completed_courses: list[CompletedCourse] = Field(max_length=500)
    program_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9 _:-]+$")
    gpa: float | None = None
    work_hours: float = 0
    diploma_completed: bool = False

class AdvisorRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    conversation: list[ChatMessage] = Field(default_factory=list, max_length=10)
    conversation_state: TopicState | None = None


class AdvisorV2Request(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    conversation_state: AdvisorV2State | None = None
    student_profile: StudentProfileV2 | None = None
    reset_conversation: bool = False


class AdvisorV3Request(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    conversation_state: AdvisorV3State | None = None
    reset_conversation: bool = False


class _AdvisorV2SessionStore:
    """Small process-local TTL store used only by the experimental route."""

    def __init__(self, max_sessions: int = 256, ttl_seconds: int = 7_200):
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._items: OrderedDict[str, tuple[float, AdvisorV2State]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> AdvisorV2State | None:
        now = time.monotonic()
        with self._lock:
            expired = [item_key for item_key, (seen, _) in self._items.items()
                       if now - seen > self.ttl_seconds]
            for item_key in expired:
                self._items.pop(item_key, None)
            item = self._items.pop(key, None)
            if item is None:
                return None
            self._items[key] = (now, item[1])
            return item[1].model_copy(deep=True)

    def set(self, key: str, state: AdvisorV2State) -> None:
        with self._lock:
            self._items.pop(key, None)
            self._items[key] = (time.monotonic(), state.model_copy(deep=True))
            while len(self._items) > self.max_sessions:
                self._items.popitem(last=False)

    def clear(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)


advisor_v2_sessions = _AdvisorV2SessionStore()
advisor_v2_language_layer = available_default_layer()


class _AdvisorV3SessionStore:
    """Bounded process-local state for the isolated v3 route."""

    def __init__(self, max_sessions: int = 256, ttl_seconds: int = 7_200):
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._items: OrderedDict[str, tuple[float, AdvisorV3State]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> AdvisorV3State | None:
        now = time.monotonic()
        with self._lock:
            for item_key in [k for k, (seen, _) in self._items.items() if now - seen > self.ttl_seconds]:
                self._items.pop(item_key, None)
            item = self._items.pop(key, None)
            if item is None:
                return None
            self._items[key] = (now, item[1])
            return item[1].model_copy(deep=True)

    def set(self, key: str, state: AdvisorV3State) -> None:
        with self._lock:
            self._items.pop(key, None)
            self._items[key] = (time.monotonic(), state.model_copy(deep=True))
            while len(self._items) > self.max_sessions:
                self._items.popitem(last=False)

    def clear(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)


advisor_v3_sessions = _AdvisorV3SessionStore()
advisor_v3_language_layer = available_v3_layer()


def _advisor_v2_runtime_metadata() -> dict:
    """Fingerprint the exact experimental files imported by this process."""
    paths = {
        "main": Path(__file__).resolve(),
        "advisor_v2": Path(advisor_v2_module.__file__).resolve(),
        "advisor_v2_sol": Path(advisor_v2_sol_module.__file__).resolve(),
        "app_v2_html": Path("static/advisor-v2.html").resolve(),
        "app_v2_js": Path("static/advisor-v2.js").resolve(),
    }
    hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    }
    combined = hashlib.sha256(
        "\n".join(f"{name}:{hashes[name]}" for name in sorted(hashes)).encode("ascii")
    ).hexdigest()
    return {
        "build_fingerprint": combined[:16],
        "startup_utc": datetime.now(timezone.utc).isoformat(),
        "process_id": os.getpid(),
        "python_executable": str(Path(sys.executable).resolve()),
        "working_directory": str(Path.cwd().resolve()),
        "route_id": "advisor-v2.conversational-core.v2",
        "router_mode": "task_plan_context_first_grounded_synthesis",
        "sol_enabled": advisor_v2_language_layer is not None,
        "sol_model": ADVISOR_V2_MODEL,
        "sol_reasoning_effort": ADVISOR_V2_REASONING_EFFORT,
        "module_paths": {name: str(path) for name, path in paths.items()},
        "file_sha256": hashes,
    }


ADVISOR_V2_RUNTIME = _advisor_v2_runtime_metadata()


def _advisor_v3_runtime_metadata() -> dict:
    paths = {
        "main": Path(__file__).resolve(),
        "advisor_v3": Path(advisor_v3_module.__file__).resolve(),
        "advisor_v3_sol": Path(advisor_v3_sol_module.__file__).resolve(),
        "app_v3_html": Path("static/advisor-v3.html").resolve(),
        "app_v3_js": Path("static/advisor-v3.js").resolve(),
    }
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    combined = hashlib.sha256("\n".join(f"{name}:{hashes[name]}" for name in sorted(hashes)).encode("ascii")).hexdigest()
    return {
        "build_fingerprint": combined[:16],
        "startup_utc": datetime.now(timezone.utc).isoformat(),
        "process_id": os.getpid(),
        "route_id": "advisor-v3.single-pipeline.v1",
        "pipeline": "classify-plan-resolve-compile-execute-synthesize-ground-transition",
        "sol_enabled": advisor_v3_language_layer is not None,
        "sol_model": ADVISOR_V3_MODEL,
        "sol_reasoning_effort": ADVISOR_V3_REASONING_EFFORT,
        "module_paths": {name: str(path) for name, path in paths.items()},
        "file_sha256": hashes,
    }


ADVISOR_V3_RUNTIME = _advisor_v3_runtime_metadata()


def answer_advisor_v2(question: str, **kwargs):
    """Runtime v2 entry point kept patchable for focused endpoint tests."""
    return answer_advisor_v2_hybrid(
        question, language_layer=advisor_v2_language_layer, **kwargs,
    )


@app.get("/")
def root():
    return {"message": "Asteris API is running"}


@app.get("/health/live", include_in_schema=False)
def health_live():
    return {"status": "alive"}


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    if not database_ready():
        return JSONResponse(status_code=503, content={"status": "not_ready", "dependencies": {"database": "unavailable"}})
    return {"status": "ready", "dependencies": {"database": "available"}}


@app.get("/app", include_in_schema=False)
def student_app():
    return FileResponse("static/index.html")


@app.get("/app-v2", include_in_schema=False)
def student_app_v2():
    """Local experimental UI; production middleware keeps this route private."""
    return FileResponse(
        "static/advisor-v2.html",
        headers={"Cache-Control": "no-store", "X-Asteris-V2-Build": ADVISOR_V2_RUNTIME["build_fingerprint"]},
    )


@app.get("/app-v3", include_in_schema=False)
def student_app_v3():
    """Isolated local v3 UI; production middleware keeps it private."""
    return FileResponse(
        "static/advisor-v3.html",
        headers={"Cache-Control": "no-store", "X-Asteris-V3-Build": ADVISOR_V3_RUNTIME["build_fingerprint"]},
    )


@app.get("/advisor-v2/diagnostics", include_in_schema=False)
def advisor_v2_diagnostics(request: Request):
    """Non-production provenance for browser/runtime parity audits."""
    route_count = sum(
        1 for route in app.routes
        if getattr(route, "path", None) == "/advisor-v2"
        and "POST" in (getattr(route, "methods", set()) or set())
    )
    return {
        **ADVISOR_V2_RUNTIME,
        "request_id": getattr(request.state, "request_id", None),
        "advisor_v2_post_route_count": route_count,
        "endpoint": str(request.url.path),
    }


@app.get("/advisor-v3/diagnostics", include_in_schema=False)
def advisor_v3_diagnostics(request: Request):
    route_count = sum(
        1 for route in app.routes
        if getattr(route, "path", None) == "/advisor-v3"
        and "POST" in (getattr(route, "methods", set()) or set())
    )
    return {
        **ADVISOR_V3_RUNTIME,
        "request_id": getattr(request.state, "request_id", None),
        "advisor_v3_post_route_count": route_count,
        "endpoint": str(request.url.path),
    }


@app.get("/courses/count")
def course_count():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM courses")
            count = cursor.fetchone()[0]

    return {"course_count": count}


@app.get("/programs")
def list_programs():
    """Return friendly choices for the student interface."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT program_id, program_name, credential
                FROM programs
                WHERE status = 'Active'
                ORDER BY program_name
                """
            )
            rows = cursor.fetchall()
    return {
        "programs": [
            {"program_id": row[0], "program_name": row[1], "credential": row[2]}
            for row in rows
        ]
    }


@app.get("/program/{program_id}/curriculum")
def program_curriculum(program_id: str):
    return get_program_curriculum(program_id)


@app.get("/program/{program_id}/rules")
def program_rules(program_id: str, scope: str | None = None):
    return get_program_rules(program_id, scope)


@app.get("/courses/{course_id}/requirements")
def course_requirements(course_id: str):
    return get_course_requirements(course_id)


@app.get("/courses/{course_id}")
def get_course(course_id: str):

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    course_id,
                    course_name,
                    credits,
                    course_overview,
                    status,
                    source_url,
                    last_checked,
                    notes,
                    display_course_code
                FROM courses
                WHERE course_id = %s
                """,
                (course_id.upper(),),
            )

            course = cursor.fetchone()

    if course is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found",
        )

    return {
        "course_id": course[0],
        "display_course_code": display_course_code(course[0], course[8]),
        "course_name": clean_course_title(course[1], course[0]),
        "credits": course[2],
        "course_overview": course[3],
        "status": course[4],
        "source_url": course[5],
        "last_checked": course[6],
        "notes": course[7],
    }


@app.get("/courses/{course_id}/prerequisites")
def get_prerequisites(course_id: str):

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    pg.group_type,
                    pc.prerequisite_course_id,
                    pc.minimum_grade,
                    pc.required_program_id,
                    pc.condition_type,
                    pc.notes,
                    c.display_course_code
                FROM prerequisite_groups pg
                JOIN prerequisite_conditions pc
                    ON pc.prerequisite_group_id =
                       pg.prerequisite_group_id
                LEFT JOIN courses c
                    ON c.course_id = pc.prerequisite_course_id
                WHERE pg.course_id = %s
                ORDER BY pg.prerequisite_group_id,
                         pc.prerequisite_condition_id
                """,
                (course_id.upper(),),
            )

            rows = cursor.fetchall()

    return {
        "course_id": course_id.upper(),
        "display_course_code": display_course_code(course_id.upper()),
        "prerequisites": [
            {
                "group_type": row[0],
                "prerequisite_course_id": row[1],
                "display_course_code": display_course_code(row[1], row[6]),
                "minimum_grade": row[2],
                "required_program_id": row[3],
                "condition_type": row[4],
                "notes": row[5],
            }
            for row in rows
        ],
    }


@app.post("/eligibility/{course_id}")
def eligibility(
    course_id: str,
    request: EligibilityRequest,
):

    completed_courses = [
        {
            "course_id": item.course_id,
            "grade": item.grade,
        }
        for item in request.completed_courses
    ]

    return check_course_eligibility(
        course_id=course_id,
        completed_courses=completed_courses,
        program_id=request.program_id,
    )

@app.post("/program/{program_id}/eligible-courses")
def eligible_courses(
    program_id: str,
    request: EligibilityRequest,
):
    completed_courses = [
        {
            "course_id": item.course_id,
            "grade": item.grade,
        }
        for item in request.completed_courses
    ]

    return find_eligible_courses(
        program_id=program_id,
        completed_courses=completed_courses,
    )

@app.get("/program/{program_id}/courses")
def get_program_courses(program_id: str):

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    pc.course_id,
                    c.course_name,
                    c.credits,
                    c.source_url,
                    pc.level,
                    pc.term,
                    pc.course_type,
                    pc.required,
                    pc.notes
                    , c.display_course_code
                FROM program_courses pc
                JOIN courses c
                    ON c.course_id = pc.course_id
                WHERE pc.program_id = %s
                ORDER BY pc.level, pc.course_id
                """,
                (program_id.upper(),),
            )

            rows = cursor.fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Program courses not found",
        )

    return {
        "program_id": program_id.upper(),
        "course_count": len(rows),
        "courses": [
            {
                "course_id": row[0],
                "display_course_code": display_course_code(row[0], row[9]),
                "course_name": clean_course_title(row[1], row[0]),
                "credits": row[2],
                "source_url": row[3],
                "level": row[4],
                "term": row[5],
                "course_type": row[6],
                "required": row[7],
                "notes": row[8],
            }
            for row in rows
        ],
    }


@app.post("/program/{program_id}/progress")
def program_progress(
    program_id: str,
    request: EligibilityRequest,
):
    completed_courses = [
        {
            "course_id": item.course_id,
            "grade": item.grade,
        }
        for item in request.completed_courses
    ]

    return check_program_progress(
        program_id=program_id,
        completed_courses=completed_courses,
    )


@app.post("/program/{program_id}/progression/{from_level}")
def progression(
    program_id: str,
    from_level: int,
    request: EligibilityRequest,
):
    completed_courses = [
        {
            "course_id": item.course_id,
            "grade": item.grade,
        }
        for item in request.completed_courses
    ]

    return check_progression(
        program_id=program_id,
        from_level=from_level,
        completed_courses=completed_courses,
        gpa=request.gpa,
        work_hours=request.work_hours,
        diploma_completed=request.diploma_completed,
    )


def _log_advisor_usage(result: dict, request: Request) -> None:
    usage = result.get("usage") or {}
    if not usage:
        return
    logger.info("advisor_model_usage", extra={
        "request_id": getattr(request.state, "request_id", None),
        "session_id": opaque_identifier(request.headers.get("x-session-id")),
        "endpoint": request.url.path,
        "model": usage.get("model"),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cached_tokens": usage.get("cached_tokens", 0),
        "outcome": "ok",
    })


@app.post("/ask")
def ask(payload: AskRequest, request: Request):
    try:
        result = answer_student_question(
            question=payload.question,
            completed_courses=[],
        )
        _log_advisor_usage(result, request)
        return result
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

@app.post("/advisor")
def advisor(payload: AdvisorRequest, request: Request):
    try:
        result = answer_student_question(
            question=payload.question,
            completed_courses=[],
            conversation=[
                message.model_dump()
                for message in payload.conversation
            ],
            conversation_state=payload.conversation_state,
        )
        _log_advisor_usage(result, request)
        return result
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/advisor-v2")
def advisor_v2(payload: AdvisorV2Request, request: Request):
    """Experimental hybrid advisor path; /advisor remains unchanged."""
    raw_session_id = request.headers.get("x-session-id")
    session_key = opaque_identifier(raw_session_id) if raw_session_id and SAFE_ID.fullmatch(raw_session_id) else None
    if payload.reset_conversation and session_key:
        advisor_v2_sessions.clear(session_key)
    prior_state = payload.conversation_state
    state_source = "client" if prior_state is not None else "none"
    if prior_state is None and session_key and not payload.reset_conversation:
        prior_state = advisor_v2_sessions.get(session_key)
        state_source = "server_session" if prior_state is not None else "none"
    result = answer_advisor_v2(
        payload.question,
        conversation_state=prior_state,
        student_profile=payload.student_profile,
    )
    result["observability"]["state_source"] = state_source
    result["observability"]["server_session_enabled"] = session_key is not None
    result["observability"]["runtime"] = {
        **ADVISOR_V2_RUNTIME,
        "request_id": getattr(request.state, "request_id", None),
        "session_id": session_key,
        "endpoint": str(request.url.path),
        "capability_path": [item.get("capability") for item in result.get("retrieval", [])],
        "decision_path": result["observability"].get("final_response_path"),
    }
    if session_key:
        advisor_v2_sessions.set(session_key, AdvisorV2State.model_validate(result["conversation_state"]))
    diagnostic = result["observability"]
    logger.info("advisor_v2_turn", extra={
        "request_id": getattr(request.state, "request_id", None),
        "session_id": session_key,
        "endpoint": request.url.path,
        "intent": diagnostic["detected_intent"],
        "question_class": diagnostic["question_class"],
        "context_action": diagnostic["context"]["action"],
        "entity_status": diagnostic["entity_resolution"]["status"],
        "retrieval_trace": diagnostic["retrieval"],
        "rule_evaluation_status": diagnostic["rule_evaluation_status"],
        "model": (result.get("usage") or {}).get("model"),
        "input_tokens": (result.get("usage") or {}).get("input_tokens", 0),
        "output_tokens": (result.get("usage") or {}).get("output_tokens", 0),
        "cached_tokens": (result.get("usage") or {}).get("cached_tokens", 0),
        "response_path": diagnostic["final_response_path"],
        "outcome": "ok",
    })
    return result


@app.post("/advisor-v3")
def advisor_v3(payload: AdvisorV3Request, request: Request):
    """Experimental v3 route. Production /advisor remains unchanged."""
    raw_session_id = request.headers.get("x-session-id")
    session_key = opaque_identifier(raw_session_id) if raw_session_id and SAFE_ID.fullmatch(raw_session_id) else None
    if payload.reset_conversation and session_key:
        advisor_v3_sessions.clear(session_key)
    prior_state = payload.conversation_state
    state_source = "client" if prior_state is not None else "none"
    if prior_state is None and session_key and not payload.reset_conversation:
        prior_state = advisor_v3_sessions.get(session_key)
        state_source = "server_session" if prior_state is not None else "none"
    result = answer_advisor_v3(
        payload.question,
        conversation_state=prior_state,
        language_layer=advisor_v3_language_layer,
    )
    result["developer_trace"]["build_fingerprint"] = ADVISOR_V3_RUNTIME["build_fingerprint"]
    result["developer_trace"]["state_source"] = state_source
    result["developer_trace"]["runtime"] = {
        **ADVISOR_V3_RUNTIME,
        "request_id": getattr(request.state, "request_id", None),
        "session_id": session_key,
        "endpoint": str(request.url.path),
    }
    if session_key:
        advisor_v3_sessions.set(session_key, AdvisorV3State.model_validate(result["conversation_state"]))
    _log_advisor_usage(result, request)
    logger.info("advisor_v3_turn", extra={
        "request_id": getattr(request.state, "request_id", None),
        "session_id": session_key,
        "endpoint": request.url.path,
        "speech_act": result["plan"]["speech_act"],
        "task": result["plan"]["task"],
        "operation_graph": [item["kind"] for item in result["developer_trace"]["operation_graph"]],
        "evidence_count": result["developer_trace"]["evidence_count"],
        "grounding_result": result["developer_trace"]["grounding_result"],
        "model": result["usage"]["model"],
        "input_tokens": result["usage"]["input_tokens"],
        "output_tokens": result["usage"]["output_tokens"],
        "cached_tokens": result["usage"]["cached_tokens"],
        "outcome": "ok",
    })
    return result

@app.post("/advisor/engine")
def advisor_engine(request: EligibilityRequest):

    completed_courses = [
        {
            "course_id": item.course_id,
            "grade": item.grade,
        }
        for item in request.completed_courses
    ]

    return run_advisor_engine(
        program_id=request.program_id,
        completed_courses=completed_courses,
        gpa=request.gpa,
        work_hours=request.work_hours,
        diploma_completed=request.diploma_completed,
    )
