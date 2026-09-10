"""Production controls shared by the Asteris API and advisor client."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _csv(name: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, "").split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    environment: str
    internal_api_key: str | None
    allowed_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    max_request_bytes: int
    rate_limit_per_minute: int
    max_concurrent_advisor_requests: int
    openai_timeout_seconds: int
    openai_max_retries: int
    openai_max_output_tokens: int
    database_connect_timeout_seconds: int

    @property
    def production(self) -> bool:
        return self.environment == "production"


def load_settings() -> Settings:
    environment = os.getenv("ASTERIS_ENV", "development").strip().lower()
    if environment not in {"development", "test", "production"}:
        raise RuntimeError("ASTERIS_ENV must be development, test, or production")
    settings = Settings(
        environment=environment,
        internal_api_key=os.getenv("ASTERIS_INTERNAL_API_KEY") or None,
        allowed_origins=_csv("ASTERIS_ALLOWED_ORIGINS"),
        allowed_hosts=_csv("ASTERIS_ALLOWED_HOSTS") or ("127.0.0.1", "localhost", "testserver"),
        max_request_bytes=_integer("ASTERIS_MAX_REQUEST_BYTES", 65_536, 1_024, 1_048_576),
        rate_limit_per_minute=_integer("ASTERIS_RATE_LIMIT_PER_MINUTE", 20, 1, 10_000),
        max_concurrent_advisor_requests=_integer("ASTERIS_MAX_CONCURRENT_ADVISOR_REQUESTS", 4, 1, 128),
        openai_timeout_seconds=_integer("ASTERIS_OPENAI_TIMEOUT_SECONDS", 30, 1, 300),
        openai_max_retries=_integer("ASTERIS_OPENAI_MAX_RETRIES", 1, 0, 3),
        openai_max_output_tokens=_integer("ASTERIS_OPENAI_MAX_OUTPUT_TOKENS", 1_200, 128, 8_192),
        database_connect_timeout_seconds=_integer("ASTERIS_DB_CONNECT_TIMEOUT_SECONDS", 5, 1, 60),
    )
    if settings.production:
        missing = [name for name in ("OPENAI_API_KEY", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD") if not os.getenv(name)]
        if missing:
            raise RuntimeError("Missing required production configuration: " + ", ".join(missing))
        if not settings.internal_api_key or len(settings.internal_api_key) < 24:
            raise RuntimeError("ASTERIS_INTERNAL_API_KEY must be at least 24 characters in production")
        if any(origin == "*" for origin in settings.allowed_origins):
            raise RuntimeError("Wildcard CORS origins are forbidden in production")
    return settings


SETTINGS = load_settings()


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int]:
        current = time.monotonic() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False, max(1, int(self.window_seconds - (current - events[0])))
            events.append(current)
            return True, 0


def opaque_identifier(value: str | None) -> str:
    return hashlib.sha256((value or "unknown").encode("utf-8")).hexdigest()[:12]


class JsonFormatter(logging.Formatter):
    """Emit operational metadata without request bodies or conversation text."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in ("request_id", "session_id", "endpoint", "method", "status", "latency_ms", "outcome", "error_class", "model", "input_tokens", "output_tokens", "cached_tokens",
                    "intent", "question_class", "context_action", "entity_status", "retrieval_trace",
                    "rule_evaluation_status", "response_path"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("asteris")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(os.getenv("ASTERIS_LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    return logger


SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
