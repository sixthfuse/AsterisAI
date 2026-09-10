"""Deterministic, institution-scoped campus facts and program relationships."""

import os
import re
from typing import Any

from database import get_connection

DEFAULT_INSTITUTION_KEY = os.getenv("ASTERIS_INSTITUTION_KEY", "BCIT").upper()


def _campus_rows(institution_key: str) -> list[tuple]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT campus_key,official_name,address,city,region,postal_code,main_phone,
                          description,official_source_url,notes
                   FROM campuses WHERE institution_key=%s AND active=TRUE
                   ORDER BY official_name""", (institution_key.upper(),))
            return cursor.fetchall()


def find_campus(question: str, institution_key: str = DEFAULT_INSTITUTION_KEY) -> dict[str, Any] | None:
    text = re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()
    aliases = {
        "burnaby": ("burnaby",), "downtown": ("downtown", "seymour"),
        "aerospace": ("aerospace", "cessna"),
        "annacis_island": ("annacis island", "annacis"),
        "marine": ("marine campus", "west esplanade"),
    }
    for row in _campus_rows(institution_key):
        phrases = aliases.get(row[0], ()) + (row[1].lower(),)
        if any(re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text) for value in phrases):
            return dict(zip(("campus_key","official_name","address","city","region",
                             "postal_code","main_phone","description","official_source_url","notes"), row))
    return None


def campus_address(campus: dict[str, Any]) -> str:
    return f"**{campus['official_name']}** — {_full_address(campus)}."


def _full_address(campus: dict[str, Any]) -> str:
    parts = [campus.get("address"), campus.get("city"), campus.get("region")]
    address = ", ".join(str(part) for part in parts if part)
    if campus.get("postal_code"):
        address += f" {campus['postal_code']}"
    return address


def campus_directory_context_active(
    conversation: list[dict[str, str]] | None,
) -> bool:
    """Return whether the newest subject established the institution campus set."""
    for message in reversed(conversation or []):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if is_campus_question(content):
            return True
        # An explicit academic entity starts a different subject. This deliberately
        # ignores generic words such as "programs", which may describe campus data.
        if re.search(
            r"\b(?:course\s+[A-Z]{2,5}\s*\d{3,4}|accounting|nursing|civil engineering|"
            r"construction management|aircraft maintenance|electronics)\b",
            content,
            re.I,
        ):
            return False
    return False


def programs_at_campus(campus_key: str, institution_key: str = DEFAULT_INSTITUTION_KEY) -> list[dict[str, str]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT p.program_id,p.program_name,pc.relationship_type,pc.notes
                   FROM program_campuses pc JOIN programs p ON p.program_id=pc.program_id
                   WHERE pc.institution_key=%s AND pc.campus_key=%s AND p.status='Active'
                   ORDER BY p.program_name,p.program_id""", (institution_key.upper(), campus_key))
            return [dict(zip(("program_id","program_name","relationship_type","notes"), row))
                    for row in cursor.fetchall()]


def campuses_for_program(program_id: str, institution_key: str = DEFAULT_INSTITUTION_KEY) -> list[dict[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT c.campus_key,c.official_name,c.address,c.city,c.region,c.postal_code,
                          pc.relationship_type,pc.notes
                   FROM program_campuses pc JOIN campuses c
                     ON c.institution_key=pc.institution_key AND c.campus_key=pc.campus_key
                   WHERE pc.program_id=%s AND pc.institution_key=%s AND c.active=TRUE
                   ORDER BY CASE pc.relationship_type WHEN 'offered' THEN 0 ELSE 1 END,c.official_name""",
                (program_id.upper(), institution_key.upper()))
            return [dict(zip(("campus_key","official_name","address","city","region","postal_code",
                             "relationship_type","notes"), row)) for row in cursor.fetchall()]


def stored_location_for_program(program_id: str) -> dict[str, Any] | None:
    """Fallback to the governed program location without inventing a campus relation."""
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT program_name, campus, source_url FROM programs WHERE program_id=%s AND status='Active'",
            (program_id.upper(),),
        )
        row = cursor.fetchone()
    if not row or not row[1]:
        return None
    return {
        "program_id": program_id.upper(), "program_name": row[0],
        "stored_location": row[1], "source_url": row[2],
        "relationship_type": "program_record",
    }


def is_campus_question(question: str) -> bool:
    institution = re.escape(DEFAULT_INSTITUTION_KEY)
    return bool(
        re.search(
            r"\b(?:campus(?:es)?|address|where is|where's|offered|located|location)\b",
            question,
            re.I,
        )
        or re.search(
            rf"\b{institution}\b[^?.!]*\b(?:phone|telephone|number|call)\b|"
            rf"\b(?:phone|telephone|number|call)\b[^?.!]*\b{institution}\b",
            question,
            re.I,
        )
    )


def campus_question_answer(question: str, program_id: str | None = None,
                           institution_key: str = DEFAULT_INSTITUTION_KEY,
                           conversation: list[dict[str, str]] | None = None) -> tuple[str, list[dict]] | None:
    directory_context = campus_directory_context_active(conversation)
    follow_up = bool(re.search(
        r"\b(?:their|them|those|each\s+one|phone\s+numbers?|addresses?|names?|"
        r"(?:tell|give|show)\s+me\s+more|more\s+(?:information|details?)|"
        r"what\s+(?:other|more)\s+information|what\s+about)\b",
        question,
        re.I,
    ))
    if not is_campus_question(question) and not (directory_context and follow_up):
        return None
    campuses = _campus_rows(institution_key)
    campus_records = [
        dict(zip(("campus_key", "official_name", "address", "city", "region",
                  "postal_code", "main_phone", "description", "official_source_url", "notes"), row))
        for row in campuses
    ]
    campus = find_campus(question, institution_key)
    if campus and re.search(r"\b(?:which|what|list|show)\b[^?.!]*\bprograms?\b|\bprograms?\b[^?.!]*\b(?:at|offered)", question, re.I):
        programs = programs_at_campus(campus["campus_key"], institution_key)
        if not programs:
            return f"I don't have any active programs associated with {campus['official_name']} in the current catalog.", []
        names = [p["program_name"] for p in programs]
        return f"Programs associated with {campus['official_name']}: " + "; ".join(names) + ".", programs
    if campus:
        if re.search(r"\b(?:phone|telephone|call|number)\b", question, re.I):
            return f"**{campus['official_name']}** main phone: {campus['main_phone']}.", [campus]
        return campus_address(campus), [campus]
    if re.search(r"\bhow\s+many\s+campus(?:es)?\b", question, re.I):
        count = len(campus_records)
        noun = "campus" if count == 1 else "campuses"
        return f"{institution_key.upper()} has {count} {noun} in the stored campus directory.", campus_records
    if re.search(r"\b(?:phone|telephone|call|number)\b", question, re.I):
        phones = sorted({item["main_phone"] for item in campus_records if item.get("main_phone")})
        if len(phones) == 1 and campus_records:
            return (
                f"{institution_key.upper()}'s main general phone number is {phones[0]}, and it is "
                f"listed for all {len(campus_records)} campuses."
            ), campus_records
        if phones:
            return f"{institution_key.upper()} campus main phones: " + "; ".join(
                f"**{item['official_name']}**: {item['main_phone']}" for item in campus_records
                if item.get("main_phone")
            ) + ".", campus_records
    if re.search(r"\b(?:names?|called)\b", question, re.I) and not re.search(
        r"\b(?:address|phone|information|details?)\b", question, re.I
    ):
        return (
            f"{institution_key.upper()}'s {len(campus_records)} campuses are: "
            + "; ".join(f"**{item['official_name']}**" for item in campus_records)
            + "."
        ), campus_records
    if re.search(r"\baddresses?\b", question, re.I):
        return "; ".join(
            f"**{item['official_name']}** — {_full_address(item)}"
            for item in campus_records
        ) + ".", campus_records
    # A named program is more specific than the generic campus-directory trigger.
    if program_id and re.search(r"\b(?:where|campus|offered|location|located)\b", question, re.I):
        program_campuses = campuses_for_program(program_id, institution_key)
        if program_campuses:
            parts = []
            for item in program_campuses:
                qualifier = "Possible site" if item["relationship_type"] == "possible" else "Campus"
                parts.append(f"{qualifier}: **{item['official_name']}** — {item['address']}, {item['city']}, {item['region']} {item['postal_code']}")
            notes = next((item["notes"] for item in program_campuses if item.get("notes") and "field" in item["notes"].lower()), None)
            suffix = f" The stored program listing says: {notes}." if notes else "."
            return "; ".join(parts) + suffix, program_campuses
        stored = stored_location_for_program(program_id)
        if stored:
            return (
                f"**{stored['program_name']}** has the stored location: "
                f"**{stored['stored_location']}**.", [stored]
            )
    if re.search(
        r"\b(?:what\s+(?:other|more)\s+information|other information|"
        r"(?:tell|give|show)\s+me\s+more|more\s+(?:information|details?))\b",
        question,
        re.I,
    ):
        entries = []
        for item in campus_records:
            programs = programs_at_campus(item["campus_key"], institution_key)
            program_text = (
                f"{len(programs)} stored active program association"
                + ("" if len(programs) == 1 else "s")
            )
            description = f" — {item['description']}" if item.get("description") else ""
            entries.append(
                f"**{item['official_name']}** — {_full_address(item)}{description} "
                f"({program_text})"
            )
        phone_text = ""
        phones = sorted({item["main_phone"] for item in campus_records if item.get("main_phone")})
        if len(phones) == 1:
            phone_text = (
                f" {institution_key.upper()}'s main general phone number is {phones[0]}, and it is "
                f"listed for all {len(campus_records)} campuses."
            )
        return (
            "The stored campus directory includes full addresses, a main phone, short descriptions, "
            "official source links, and active program associations. "
            + "; ".join(entries) + "." + phone_text
        ), campus_records
    if re.search(r"\bcampus(?:es)?\b", question, re.I) and campus_records:
        summary = "; ".join(
            f"**{item['official_name']}** — {_full_address(item)}"
            for item in campus_records
        )
        return f"{institution_key.upper()} has {len(campus_records)} campuses: {summary}.", campus_records
    return None
