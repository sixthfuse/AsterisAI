"""Database-managed official institutional resources for advisor responses."""

import os
import re
from typing import Any

from database import get_connection


DEFAULT_INSTITUTION_KEY = os.getenv("ASTERIS_INSTITUTION_KEY", "BCIT").upper()
MAX_RESOURCE_LINKS = 2


def _phrase_matches(text: str, phrase: str) -> bool:
    phrase = re.sub(r"\s+", " ", phrase.strip().lower())
    return bool(phrase and re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text))


def find_institutional_resources(question: str, institution_key: str = DEFAULT_INSTITUTION_KEY,
                                 normalized_intents: list[str] | None = None,
                                 limit: int = MAX_RESOURCE_LINKS) -> list[dict[str, Any]]:
    """Return a small ranked set using only curated records from PostgreSQL."""
    if limit <= 0:
        return []
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT resource_key, title, official_url, topic, trigger_phrases,
                          normalized_intents, description, priority
                   FROM institutional_resources
                   WHERE institution_key = %s AND active = TRUE
                   ORDER BY priority, resource_key""",
                (institution_key.upper(),),
            )
            rows = cursor.fetchall()
    text = re.sub(r"\s+", " ", question.strip().lower())
    requested = {value.upper() for value in (normalized_intents or [])}
    matches = []
    for row in rows:
        hits = sum(_phrase_matches(text, phrase) for phrase in (row[4] or []))
        intent_hit = bool(requested & {value.upper() for value in (row[5] or [])})
        if hits or intent_hit:
            matches.append((not intent_hit, -hits, row[7], row[0], row))
    return [{"resource_key": row[0], "title": row[1], "official_url": row[2],
             "topic": row[3], "description": row[6], "priority": row[7]}
            for *_, row in sorted(matches)[:min(limit, MAX_RESOURCE_LINKS)]]


def append_institutional_resources(answer: str, question: str,
                                   institution_key: str = DEFAULT_INSTITUTION_KEY) -> str:
    resources = find_institutional_resources(question, institution_key=institution_key)
    resources = [item for item in resources if item["official_url"] not in (answer or "")]
    if not resources:
        return answer
    links = [f"{item['title']}: {item['official_url']}" for item in resources]
    lead = "For more information, see " if len(links) == 1 else "You can also check "
    return f"{(answer or '').rstrip()}\n\n{lead}{'; '.join(links)}."


def is_direct_resource_request(question: str) -> bool:
    return bool(re.search(r"\b(?:where(?:'s| is)|find|show|give|send|link|url|webpage|page)\b",
                          question, re.IGNORECASE))


def direct_resource_answer(resources: list[dict[str, Any]]) -> str:
    if len(resources) == 1:
        item = resources[0]
        return f"Here is the official {item['title']} page: {item['official_url']}"
    return "Here are the relevant official pages:\n\n" + "\n".join(
        f"- {item['title']}: {item['official_url']}" for item in resources)
