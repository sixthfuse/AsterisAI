"""Deterministic evaluation of normalized curriculum requirement trees."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import re

from database import get_connection

SATISFIED = "satisfied"
NOT_SATISFIED = "not_satisfied"
PARTIAL = "partially_satisfied"
UNKNOWN = "unknown_human_confirmation"


def _number(value):
    return Decimal(str(value)) if value is not None else None


def _serialize(value):
    return float(value) if isinstance(value, Decimal) else value


def _load(program_id):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT r.curriculum_requirement_id, r.requirement_code,
                   r.requirement_type, r.institution_key, r.minimum_credits,
                   r.exact_course_count, r.double_count_prohibited,
                   r.parent_requirement_code, r.executable,
                   r.verification_method, r.description, r.parameters,
                   r.sort_order, rc.course_id, c.institution_key,
                   c.native_course_code, c.credits
            FROM curriculum_requirements r
            LEFT JOIN curriculum_requirement_courses rc
              USING (curriculum_requirement_id)
            LEFT JOIN courses c ON c.course_id = rc.course_id
            WHERE r.program_id = %s
            ORDER BY r.sort_order, r.requirement_code, rc.course_id
            """,
            (program_id.upper(),),
        )
        rows = cursor.fetchall()
    nodes = {}
    for row in rows:
        node = nodes.setdefault(row[1], {
            "id": row[0], "code": row[1], "type": row[2],
            "institution_key": row[3], "minimum_credits": row[4],
            "exact_course_count": row[5], "double_count_prohibited": row[6],
            "parent": row[7], "executable": row[8],
            "verification_method": row[9], "description": row[10],
            "parameters": row[11] or {}, "sort_order": row[12],
            "courses": [], "children": [],
        })
        if row[13]:
            node["courses"].append({"course_id": row[13],
                "institution_key": row[14], "native_course_code": row[15],
                "credits": row[16]})
    for node in nodes.values():
        if node["parent"] in nodes:
            nodes[node["parent"]]["children"].append(node)
    roots = [n for n in nodes.values() if n["parent"] not in nodes]
    return sorted(roots, key=lambda n: (n["sort_order"], n["code"]))


def _normalize_evidence(items):
    evidence = []
    for index, item in enumerate(items or []):
        institution = item.get("institution_key")
        native = item.get("native_course_code")
        course_id = item.get("course_id")
        evidence.append({
            "key": f"evidence:{index}", "course_id": course_id.upper() if course_id else None,
            "institution_key": institution.upper() if institution else None,
            "native_course_code": native.upper() if native else None,
            "subject": item.get("subject", "").upper() or None,
            "credits": _number(item.get("credits")), "completed": item.get("completed", True),
        })
    return evidence


def _match(course, item):
    if item["course_id"]:
        return item["course_id"] == course["course_id"].upper()
    return bool(item["institution_key"] and item["native_course_code"] and
        item["institution_key"] == course["institution_key"] and
        item["native_course_code"] == (course["native_course_code"] or "").upper())


def _leaf(node, evidence, unavailable):
    matches = []
    missing_credit = []
    for course in node["courses"]:
        item = next((x for x in evidence if x["completed"] and _match(course, x)), None)
        if not item:
            continue
        credits = item["credits"] if item["credits"] is not None else _number(course["credits"])
        match = {**item, "credits": credits, "matched_course_id": course["course_id"]}
        (missing_credit if credits is None else matches).append(match)

    requirement_type = node["type"].lower()
    if requirement_type == "subject_credits":
        subject = str(node["parameters"].get("subject", "")).upper()
        minimum_level = node["parameters"].get("minimum_level")
        excluded = {x.upper() for x in node["parameters"].get("excluded_native_course_codes", [])}
        candidate_subject_evidence = [x for x in evidence if x["completed"] and x["subject"] == subject]
        if any(not x["institution_key"] or not x["native_course_code"] or x["credits"] is None
               for x in candidate_subject_evidence):
            return _result(node, UNKNOWN, [], "Institution, subject, course code, and credit evidence is required.")
        subject_matches = [x for x in evidence if x["completed"] and
            x["institution_key"] == node["institution_key"] and x["subject"] == subject and
            (x["native_course_code"] or "") not in excluded]
        sufficiently_identified = all(x["native_course_code"] for x in subject_matches)
        if minimum_level is not None:
            subject_matches = [x for x in subject_matches if (lambda m: m and
                int(m.group(1)) >= int(minimum_level))(re.search(r"(\d{3,4})", x["native_course_code"] or ""))]
        if not subject or not sufficiently_identified or any(x["credits"] is None for x in subject_matches):
            return _result(node, UNKNOWN, [], "Institution, subject, and credit evidence is required.")
        matches = subject_matches

    usable = [x for x in matches if x["key"] not in unavailable]
    completed_credits = sum((x["credits"] for x in usable), Decimal("0"))
    completed_count = len(usable)
    minimum = _number(node["minimum_credits"])
    exact = node["exact_course_count"]
    credit_ok = minimum is None or completed_credits >= minimum
    count_ok = exact is None or completed_count == exact
    required_courses = {x.upper() for x in node["parameters"].get("required_course_ids", [])}
    completed_ids = {x["matched_course_id"].upper() for x in usable if x.get("matched_course_id")}
    required_ok = required_courses.issubset(completed_ids)

    if missing_credit and minimum is not None and not credit_ok:
        status, reason = UNKNOWN, "Completed matching course credits are not known."
    elif credit_ok and count_ok and required_ok:
        status, reason = SATISFIED, "The modeled course and credit thresholds are met."
    elif completed_count or completed_credits:
        status, reason = PARTIAL, "Some applicable coursework is complete."
    else:
        status, reason = NOT_SATISFIED, "No qualifying completed evidence was found."
    return _result(node, status, usable, reason, completed_credits, completed_count,
                   minimum, exact, required_courses - completed_ids)


def _result(node, status, matches, reason, credits=Decimal("0"), count=0,
            minimum=None, exact=None, missing_required=frozenset(), children=None):
    requirement_type = node["type"].lower()
    is_required_alternative = requirement_type in {
        "alternative_courses", "alternative_path", "any_of", "or"
    } or str(node["parameters"].get("operator", "")).upper() in {
        "OR", "ANY_OF", "ALTERNATIVE"
    }
    return {
        "requirement_code": node["code"], "requirement_type": node["type"],
        "description": node["description"],
        "institution_key": node["institution_key"],
        "required_alternative": is_required_alternative,
        "individual_options_mandatory": False if is_required_alternative else None,
        "status": status, "satisfied": status == SATISFIED, "reason": reason,
        "completed_credits": _serialize(credits), "required_credits": _serialize(minimum),
        "remaining_credits": _serialize(max(minimum - credits, 0)) if minimum is not None else None,
        "completed_course_count": count, "required_course_count": exact,
        "remaining_course_count": max(exact - count, 0) if exact is not None else None,
        "completed_courses": sorted({x.get("matched_course_id") or x.get("course_id") for x in matches}),
        "remaining_required_courses": sorted(missing_required),
        "eligible_options": sorted(c["course_id"] for c in node["courses"]
                                   if c["course_id"] not in {x.get("matched_course_id") for x in matches}),
        "claimed_evidence": sorted(x["key"] for x in matches),
        "children": children or [], "human_confirmation_required": status == UNKNOWN,
    }


def _evaluate(node, evidence, unavailable):
    if not node["executable"]:
        return _result(node, UNKNOWN, [], node["verification_method"] or
                       "This requirement requires human confirmation.")
    if not node["children"]:
        return _leaf(node, evidence, unavailable if node["double_count_prohibited"] else set())
    children = [_evaluate(child, evidence, unavailable) for child in
                sorted(node["children"], key=lambda n: (n["sort_order"], n["code"]))]
    operator = str(node["parameters"].get("operator", node["type"])).upper()
    if operator in {"OR", "ANY_OF", "ALTERNATIVE"}:
        winner = next((x for x in children if x["status"] == SATISFIED), None)
        selected = winner or max(children, key=lambda x: (x["completed_credits"], x["completed_course_count"]))
        status = SATISFIED if winner else (UNKNOWN if any(x["status"] == UNKNOWN for x in children)
                                           else PARTIAL if any(x["status"] == PARTIAL for x in children)
                                           else NOT_SATISFIED)
        claims = selected["claimed_evidence"]
        reason = f"Alternative branch {selected['requirement_code']} selected deterministically."
    else:
        statuses = {x["status"] for x in children}
        status = SATISFIED if statuses == {SATISFIED} else (UNKNOWN if UNKNOWN in statuses
                 else PARTIAL if SATISFIED in statuses or PARTIAL in statuses else NOT_SATISFIED)
        claims = sorted({key for x in children for key in x["claimed_evidence"]})
        reason = "All child requirements must be satisfied."
    result = _result(node, status, [], reason, children=children)
    result["claimed_evidence"] = claims
    return result


def evaluate_curriculum(program_id, transcript_evidence):
    """Evaluate all normalized roots while preserving unknown human-review nodes."""
    evidence = _normalize_evidence(transcript_evidence)
    unavailable, results = set(), []
    for root in _load(program_id):
        result = _evaluate(root, evidence, unavailable)
        results.append(result)
        # Earlier satisfied roots reserve their evidence. A later root only
        # consults this set when its normalized rule prohibits double count.
        if result["status"] == SATISFIED:
            unavailable.update(result["claimed_evidence"])
    statuses = {x["status"] for x in results}
    overall = SATISFIED if results and statuses == {SATISFIED} else (
        UNKNOWN if UNKNOWN in statuses else PARTIAL if SATISFIED in statuses or PARTIAL in statuses
        else NOT_SATISFIED)
    return {"program_id": program_id.upper(), "status": overall,
            "requirements": results, "human_confirmation_required": UNKNOWN in statuses}
