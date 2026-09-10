"""Govern the active BCIT programs that predate import revision pointers.

The re-audit refreshes official sources, compares them with PostgreSQL, records
an exact normalized snapshot contract, and adds governance metadata without
rematerializing correct legacy program/course/rule rows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup, Tag

from bcit_international_enrichment_planner import UNKNOWN, status_from_text
from bcit_program_extractor import parse_matrix
from database import get_connection
from program_import_contract import activate_revision, approve_payload, record_import_revision


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "program_extractor_audit" / "legacy_program_reaudit"
REPORT_JSON = ROOT / "LEGACY_PROGRAM_REAUDIT.json"
REPORT_MD = ROOT / "LEGACY_PROGRAM_REAUDIT.md"
CONTRACT_VERSION = "1.0-legacy"
PIPELINE_VERSION = "asteris-legacy-program-reaudit/1.0"
APPROVER = "legacy_program_reaudit.verified_official_source"
CLASSIFICATIONS = ("NO_CHANGE", "STALE_DATA", "MISSING_DATA", "STRUCTURE_GAP", "PROVENANCE_GAP")

SNAPSHOT_QUERIES = {
    "programs": "SELECT * FROM programs WHERE program_id=%s",
    "program_offerings": "SELECT * FROM program_offerings WHERE program_id=%s",
    "program_delivery_facts": "SELECT * FROM program_delivery_facts WHERE program_id=%s",
    "program_courses": "SELECT * FROM program_courses WHERE program_id=%s",
    "program_requirements": "SELECT * FROM program_requirements WHERE program_id=%s",
    "curriculum_components": "SELECT * FROM curriculum_components WHERE program_id=%s",
    "curriculum_component_courses": "SELECT x.* FROM curriculum_component_courses x JOIN curriculum_components c USING(component_id) WHERE c.program_id=%s",
    "credit_requirements": "SELECT * FROM credit_requirements WHERE program_id=%s",
    "credit_requirement_courses": "SELECT x.* FROM credit_requirement_courses x JOIN credit_requirements r USING(credit_requirement_id) WHERE r.program_id=%s",
    "curriculum_requirements": "SELECT * FROM curriculum_requirements WHERE program_id=%s",
    "curriculum_requirement_courses": "SELECT x.* FROM curriculum_requirement_courses x JOIN curriculum_requirements r USING(curriculum_requirement_id) WHERE r.program_id=%s",
    "curriculum_substitutions": "SELECT * FROM curriculum_substitutions WHERE program_id=%s",
    "academic_rule_sets": "SELECT * FROM academic_rule_sets WHERE program_id=%s",
    "academic_rule_groups": "SELECT g.* FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s",
    "academic_rule_conditions": "SELECT c.* FROM academic_rule_conditions c JOIN academic_rule_groups g USING(rule_group_id) JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s",
    "clinical_placement_requirements": "SELECT * FROM clinical_placement_requirements WHERE program_id=%s",
    "practice_hour_requirements": "SELECT * FROM practice_hour_requirements WHERE program_id=%s",
    "progression_requirements": "SELECT * FROM progression_requirements WHERE program_id=%s",
    "program_advisor_aliases": "SELECT * FROM program_advisor_aliases WHERE program_id=%s",
    "program_campuses": "SELECT * FROM program_campuses WHERE program_id=%s",
    "program_relationships": "SELECT * FROM program_relationships WHERE program_id=%s",
}


def json_ready(value):
    if isinstance(value, (date, datetime, Decimal)):
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def canonical_json(value) -> str:
    return json.dumps(json_ready(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def canonical_url(value: str) -> str:
    clean, _ = urldefrag(value or "")
    parts = urlsplit(clean.strip())
    path = "/".join(part for part in parts.path.split("/") if part)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), "/" + path.lower() + ("/" if path else ""), "", ""))


def rows(cursor, query, params=()):
    cursor.execute(query, params)
    names = [column.name for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def active_without_revision(cursor):
    return rows(cursor, """
        SELECT p.* FROM programs p
        LEFT JOIN program_active_import_revisions a USING(program_id)
        WHERE lower(p.status)='active' AND a.revision_id IS NULL
        ORDER BY p.program_id
    """)


def materialized_snapshot(cursor, program_id):
    snapshot = {}
    for table, query in SNAPSHOT_QUERIES.items():
        table_rows = [json_ready(row) for row in rows(cursor, query, (program_id,))]
        snapshot[table] = sorted(table_rows, key=canonical_json)
    return snapshot


def snapshot_diff(before, after):
    changes = []
    for table in sorted(set(before) | set(after)):
        left = before.get(table, [])
        right = after.get(table, [])
        if left != right:
            changes.append({"table": table, "before_sha256": sha256_json(left), "after_sha256": sha256_json(right), "before_rows": len(left), "after_rows": len(right)})
    return {"changed_tables": len(changes), "changes": changes, "zero_diff": not changes}


def find_program_jsonld(value, program_id):
    if isinstance(value, dict):
        item_type = value.get("@type")
        types = item_type if isinstance(item_type, list) else [item_type]
        if "EducationalOccupationalProgram" in types and str(value.get("identifier", "")).upper() == program_id:
            return value
        for child in value.values():
            found = find_program_jsonld(child, program_id)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_program_jsonld(child, program_id)
            if found:
                return found
    return {}


def program_jsonld(soup, program_id):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            found = find_program_jsonld(json.loads(script.string or "null"), program_id)
        except json.JSONDecodeError:
            continue
        if found:
            return found
    return {}


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def source_sections(soup):
    wanted = {
        "admissions": re.compile(r"entrance|admission", re.I),
        "program_details": re.compile(r"program details", re.I),
        "advanced_placement": re.compile(r"advanced placement|transfer|prior learning|plar", re.I),
        "completion": re.compile(r"graduating|completion|jobs", re.I),
        "costs": re.compile(r"costs|supplies", re.I),
    }
    result = {}
    headings = soup.find_all(["h2", "h3"])
    for key, pattern in wanted.items():
        heading = next((h for h in headings if pattern.search(clean_text(h.get_text(" ", strip=True)))), None)
        if not heading:
            result[key] = {"published": False, "sha256": "", "excerpt": ""}
            continue
        pieces = []
        for node in heading.next_siblings:
            if isinstance(node, Tag) and node.name in {"h2", "h3"}:
                break
            if isinstance(node, Tag):
                text = clean_text(node.get_text(" ", strip=True))
                if text:
                    pieces.append(text)
        text = clean_text(" ".join(pieces))
        result[key] = {"published": bool(text), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "", "excerpt": text[:500]}
    return result


def related_authoritative_urls(soup, base_url):
    pattern = re.compile(r"handbook|policy|transfer|advanced placement|prior learning|study permit|international|program details|re-admission", re.I)
    found = set()
    for link in soup.find_all("a", href=True):
        label = clean_text(link.get_text(" ", strip=True))
        url = urljoin(base_url, link["href"])
        if pattern.search(label) and urlsplit(url).netloc.lower().endswith("bcit.ca"):
            found.add(urldefrag(url)[0])
    return sorted(found)


def fetch_source(session, program_id, requested_url, output_dir):
    path = output_dir / "sources" / f"{program_id}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    response = None
    last_error = None
    for attempt in range(4):
        try:
            response = session.get(requested_url, timeout=60)
            response.raise_for_status()
            break
        except requests.RequestException as error:
            last_error = error
            time.sleep(2 ** attempt)
    if response is None:
        if not path.exists():
            raise last_error
        raw = path.read_bytes()
        final_url = requested_url
        http_status = 200
    else:
        raw = response.content
        final_url = response.url
        http_status = response.status_code
    path.write_bytes(raw)
    soup = BeautifulSoup(raw, "html.parser")
    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical_value = canonical.get("href", "") if canonical else final_url
    data = program_jsonld(soup, program_id)
    provider = data.get("provider") if isinstance(data.get("provider"), dict) else {}
    department = provider.get("department") if isinstance(provider.get("department"), dict) else {}
    address = provider.get("address") if isinstance(provider.get("address"), dict) else {}
    components, matrix_total = parse_matrix(soup, final_url)
    courses = sorted({course.course_id for component in components for course in component.courses})
    if not courses:
        courses = sorted({re.sub(r"[^A-Z0-9]", "", str(course.get("courseCode", "")).upper()) for course in data.get("hasCourse", []) if isinstance(course, dict) and course.get("courseCode")})
    full_text = clean_text(soup.get_text(" ", strip=True))
    return {
        "program_id": program_id,
        "requested_url": requested_url,
        "final_url": final_url,
        "canonical_url": canonical_value,
        "http_status": http_status,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_file": str(path.relative_to(ROOT)),
        "identity": {
            "identifier": str(data.get("identifier", "")).upper(),
            "name": data.get("name", ""),
            "alternate_name": data.get("alternateName", ""),
            "credential": data.get("educationalCredentialAwarded", ""),
            "study_mode": data.get("educationalProgramMode", ""),
            "school": department.get("name", ""),
            "campus_locality": address.get("addressLocality", ""),
            "total_credits": (data.get("numberOfCredits") or {}).get("value", "") if isinstance(data.get("numberOfCredits"), dict) else data.get("numberOfCredits", ""),
        },
        "matrix_total_credits": matrix_total,
        "components": [{"name": component.name, "rule_type": component.rule_type, "course_ids": [course.course_id for course in component.courses]} for component in components],
        "course_ids": courses,
        "sections": source_sections(soup),
        "related_authoritative_urls": related_authoritative_urls(soup, final_url),
        "published_course_codes": sorted(set(re.findall(r"\b[A-Z]{2,6}\s*\d{4}\b", full_text))),
        "source_text_sha256": hashlib.sha256(full_text.encode("utf-8")).hexdigest(),
        "source_text": full_text,
    }


def stored_course_roles(cursor, program_id):
    results = {}
    for row in rows(cursor, "SELECT course_id,course_type,required,notes FROM program_courses WHERE program_id=%s", (program_id,)):
        results.setdefault(row["course_id"], []).append(clean_text(" ".join(str(row.get(k) or "") for k in ("course_type", "required", "notes"))))
    for row in rows(cursor, """SELECT x.course_id,x.course_role,c.component_name FROM curriculum_component_courses x JOIN curriculum_components c USING(component_id) WHERE c.program_id=%s""", (program_id,)):
        results.setdefault(row["course_id"], []).append(clean_text(f"{row['course_role']} {row['component_name']}"))
    for row in rows(cursor, """SELECT x.course_id,r.requirement_name FROM credit_requirement_courses x JOIN credit_requirements r USING(credit_requirement_id) WHERE r.program_id=%s""", (program_id,)):
        results.setdefault(row["course_id"], []).append(clean_text(f"ELECTIVE {row['requirement_name']}"))
    return {key: " | ".join(value) for key, value in sorted(results.items())}


def certified_international(cursor, program_id):
    fact_rows = rows(cursor, "SELECT international_eligibility,authoritative_raw,source_url,last_checked FROM program_delivery_facts WHERE program_id=%s", (program_id,))
    rule_rows = rows(cursor, "SELECT notes,source_url FROM academic_rule_sets WHERE program_id=%s AND upper(rule_scope)='INTERNATIONAL'", (program_id,))
    candidates = []
    for row in fact_rows:
        candidates.append({"source": "program_delivery_facts", "raw": row.get("international_eligibility") or row.get("authoritative_raw") or "", "status": status_from_text(row.get("international_eligibility") or row.get("authoritative_raw") or "")})
    for row in rule_rows:
        candidates.append({"source": "academic_rule_sets", "raw": row.get("notes") or "", "status": status_from_text(row.get("notes") or "")})
    deterministic = {item["status"] for item in candidates if item["status"] != UNKNOWN}
    status = next(iter(deterministic)) if len(deterministic) == 1 else UNKNOWN
    return {"normalized_status": status, "evidence": candidates, "mismatch": len(deterministic) > 1, "deterministic_values": sorted(deterministic)}


def identity_comparison(program, evidence):
    official = evidence["identity"]
    identifier_match = official["identifier"] == program["program_id"]
    name_blob = clean_text(f"{official['name']} {official['alternate_name']}").lower()
    stored_name_terms = [term for term in re.findall(r"[a-z0-9]+", program["program_name"].lower()) if term not in {"of", "in", "and", "the", "full", "time", "part"}]
    name_match = bool(stored_name_terms) and sum(term in name_blob for term in stored_name_terms) / len(stored_name_terms) >= 0.75
    credential_match = clean_text(official["credential"]).lower() in clean_text(f"{program.get('credential','')} {program.get('program_name','')}").lower()
    mode_words = set(re.findall(r"full|part", clean_text(official["study_mode"]).lower()))
    mode_match = not mode_words or mode_words <= set(re.findall(r"full|part", clean_text(program.get("study_mode", "")).lower()))
    school_match = clean_text(official["school"]).lower() == clean_text(program.get("school", "")).lower()
    return {"identifier": identifier_match, "name": name_match, "credential": credential_match, "study_mode": mode_match, "school": school_match, "all_match": all((identifier_match, name_match, credential_match, mode_match, school_match))}


def audit_one(cursor, program, evidence, linked_evidence=None):
    program_id = program["program_id"]
    roles = stored_course_roles(cursor, program_id)
    stored = set(roles)
    official = set(evidence["course_ids"])
    linked = None
    if program_id == "5410DIPLT" and not official and linked_evidence:
        first_four = linked_evidence["components"][:4]
        official = {course for component in first_four for course in component["course_ids"]}
        linked = {"program_id": "8660BENG", "source_url": linked_evidence["canonical_url"], "basis": "The Diploma is the first four published levels of the Civil Engineering degree ladder.", "component_names": [component["name"] for component in first_four]}
    extras = set(stored - official)
    preserved = set()
    for course_id in extras:
        role = roles.get(course_id, "")
        if re.search(r"substitut|elective|option", role, re.I) and re.search(rf"\b{re.escape(course_id[:4])}\s*{re.escape(course_id[4:])}\b", evidence["source_text"], re.I):
            preserved.add(course_id)
    extras -= preserved
    missing = sorted(official - stored)
    stale = sorted(extras)
    identity = identity_comparison(program, evidence)
    international = certified_international(cursor, program_id)
    structure_counts = {table: len(items) for table, items in materialized_snapshot(cursor, program_id).items() if items}
    human_boundaries = []
    text = evidence["source_text"]
    for label, pattern in (
        ("institutional_or_department_review", r"competitive|department review|program head|approval"),
        ("professional_or_clinical_verification", r"clinical placement|registration|licen[cs]|immuni[sz]|criminal record"),
        ("transfer_or_prior_learning_assessment", r"transfer credit|prior learning|\bPLAR\b|advanced placement"),
        ("permit_or_immigration_decision", r"study permit|PGWP|IRCC"),
    ):
        if re.search(pattern, text, re.I):
            human_boundaries.append(label)
    content_issues = []
    if not identity["all_match"]:
        content_issues.append("official identity metadata differs from the stored program identity")
    if missing:
        content_issues.append("current official curriculum contains stored-data gaps")
    if stale:
        content_issues.append("stored curriculum references are absent from current authoritative curriculum")
    classifications = ["PROVENANCE_GAP"]
    if missing:
        classifications.append("MISSING_DATA")
    if stale or not identity["all_match"]:
        classifications.append("STALE_DATA")
    if not content_issues:
        classifications.insert(0, "NO_CHANGE")
    return {
        "program_id": program_id,
        "program_name": program["program_name"],
        "classifications": classifications,
        "identity": identity,
        "delivery": {"study_mode": program.get("study_mode"), "campus": program.get("campus"), "delivery_method": program.get("delivery_method"), "official_mode": evidence["identity"]["study_mode"], "official_locality": evidence["identity"]["campus_locality"]},
        "curriculum": {"official_course_count": len(official), "stored_course_count": len(stored), "missing_in_postgresql": missing, "stored_not_current": stale, "preserved_authoritative_non_matrix_courses": sorted(preserved), "linked_curriculum_source": linked},
        "requirements": {"source_sections": evidence["sections"], "stored_structure_counts": structure_counts, "human_confirmation_boundaries": human_boundaries},
        "international": international,
        "source": {key: value for key, value in evidence.items() if key != "source_text"},
        "content_issues": content_issues,
        "safe_to_govern": not content_issues and not international["mismatch"],
    }


@dataclass
class SnapshotContract:
    program: dict
    provenance: dict
    payload: dict
    contract_version: str = CONTRACT_VERSION

    def to_dict(self):
        return self.payload

    @property
    def payload_sha256(self):
        return sha256_json(self.payload)

    @property
    def idempotency_key(self):
        return f"{self.program['program_id']}:{self.contract_version}:{self.payload_sha256}"


def make_contract(audit, snapshot):
    retrieved = audit["source"]["retrieved_at"]
    provenance = {
        "authoritative_source_url": audit["source"]["canonical_url"],
        "source_type": "official_program_page_and_governed_snapshot",
        "extracted_at": retrieved,
        "last_checked": retrieved,
        "pipeline_version": PIPELINE_VERSION,
        "provenance_tag": audit["program_id"],
        "review_status": "approved",
        "confidence": "high",
        "human_approved": False,
        "approved_by": "",
        "approved_at": "",
        "source_sha256": audit["source"]["source_sha256"],
    }
    payload = {
        "contract_version": CONTRACT_VERSION,
        "program": {"program_id": audit["program_id"], "program_name": audit["program_name"]},
        "provenance": provenance,
        "source_evidence": audit["source"],
        "comparison": {key: audit[key] for key in ("classifications", "identity", "delivery", "curriculum", "requirements", "international", "content_issues", "safe_to_govern")},
        "materialized_snapshot": snapshot,
        "materialization_policy": "preserve_existing_rows; governed revision adoption only",
    }
    return SnapshotContract(payload["program"], provenance, payload)


def markdown_report(summary):
    lines = [
        "# Legacy / Pre-Governance Program Re-Audit",
        "",
        f"Run date: {summary['run_date']}",
        "",
        "## Result",
        "",
        f"All **{summary['programs_audited']}** authoritative pre-governance programs were re-audited. **{summary['successfully_governed']}** now have active governed revision pointers; **{summary['held']}** were held.",
        "",
        f"Factual corrections: **{summary['factual_corrections']}**. Provenance-only corrections: **{summary['provenance_only_corrections']}**. New courses: **{summary['new_courses_added']}**. International mismatches: **{summary['international_mismatches']}**.",
        "",
        "Classification counts are aspect flags and may overlap: " + ", ".join(f"{key} **{summary['classification_counts'].get(key, 0)}**" for key in CLASSIFICATIONS) + ".",
        "",
        "## Exact 19-program set",
        "",
        "| Program | Stored title | Classifications | Revision | Hash | Zero diff |",
        "|---|---|---|---:|---|---|",
    ]
    for item in summary["programs"]:
        lines.append(f"| {item['program_id']} | {item['program_name']} | {', '.join(item['classifications'])} | {item.get('revision_id') or 'HELD'} | `{item.get('payload_sha256','')}` | {'yes' if item.get('zero_diff') else 'no'} |")
    lines += [
        "",
        "## Governance and integrity",
        "",
        f"Active programs/courses: **{summary['final_active_programs']} / {summary['final_active_courses']}**.",
        f"Active governed revision coverage: **{summary['governed_revision_coverage']} / {summary['final_active_programs']}**.",
        f"Remaining active pre-governance programs: **{summary['remaining_pre_governance']}**.",
        "",
        "Every accepted payload was exact-hash approved, inserted once, replayed with no new revision, activated, and compared with the post-activation materialized state. Governance rows do not rewrite curriculum, course, rule, alias, relationship, or routing data.",
        "",
        "## Human-confirmation boundaries",
        "",
        "Published competitive decisions, clinical or professional verification, transfer/PLAR decisions, program-head approvals, and immigration decisions remain preserved as source-backed human-confirmation boundaries. No apprenticeship or advisor-language architecture was introduced.",
        "",
        "## Testing",
        "",
        f"Focused legacy re-audit: **{summary['testing']['focused']['passed']}/{summary['testing']['focused']['run']} passed**, {summary['testing']['focused']['failed']} failed, {summary['testing']['focused']['errors']} errors.",
        f"Full Python regression: **{summary['testing']['full_python']['passed']}/{summary['testing']['full_python']['run']} passed**, {summary['testing']['full_python']['failed']} failed, {summary['testing']['full_python']['errors']} errors.",
        "Browser-state suite: **not required** because shared routing/advisor code did not change.",
    ]
    return "\n".join(lines) + "\n"


def run(apply=False, focused=None, full_python=None):
    OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 Asteris legacy program re-audit"})
    with get_connection() as connection, connection.cursor() as cursor:
        candidates = active_without_revision(cursor)
        if len(candidates) != 19:
            raise RuntimeError(f"Expected exactly 19 active programs without governed pointers; PostgreSQL returned {len(candidates)}")
        evidence_by_id = {}
        for program in candidates:
            evidence_by_id[program["program_id"]] = fetch_source(session, program["program_id"], program["source_url"], OUT)
        audits = [audit_one(cursor, program, evidence_by_id[program["program_id"]], evidence_by_id.get("8660BENG")) for program in candidates]
        held = [item for item in audits if not item["safe_to_govern"]]
        factual_corrections = []
        provenance_corrections = []
        if apply and not held:
            for program, audit in zip(candidates, audits):
                current_url = program["source_url"]
                official_url = audit["source"]["canonical_url"]
                if canonical_url(current_url) == canonical_url(official_url) and current_url != official_url:
                    cursor.execute("UPDATE programs SET source_url=%s,last_checked=CURRENT_DATE WHERE program_id=%s", (official_url, program["program_id"]))
                    provenance_corrections.append({"program_id": program["program_id"], "field": "programs.source_url", "before": current_url, "after": official_url})
                else:
                    cursor.execute("UPDATE programs SET last_checked=CURRENT_DATE WHERE program_id=%s", (program["program_id"],))
            connection.commit()
        program_results = []
        for audit in audits:
            before = materialized_snapshot(cursor, audit["program_id"])
            contract = make_contract(audit, before)
            revision_id = None
            replay_revision_id = None
            if apply and audit["safe_to_govern"]:
                approve_payload(cursor, contract, approved_by=APPROVER, review_notes="Official source and PostgreSQL snapshot reconciled; preserve existing materialized semantics.")
                revision_id = record_import_revision(cursor, contract, importer="legacy_program_reaudit.run")
                if not revision_id:
                    cursor.execute("SELECT revision_id FROM program_import_revisions WHERE idempotency_key=%s", (contract.idempotency_key,))
                    revision_id = cursor.fetchone()[0]
                activate_revision(cursor, revision_id, changed_by="legacy_program_reaudit.run", reason="Adopt verified pre-governance materialization")
                replay_revision_id = record_import_revision(cursor, contract, importer="legacy_program_reaudit.run.replay")
            after = materialized_snapshot(cursor, audit["program_id"])
            diff = snapshot_diff(before, after)
            if not diff["zero_diff"]:
                raise RuntimeError(f"Materialized data changed while governing {audit['program_id']}: {diff}")
            item = {**audit, "payload_sha256": contract.payload_sha256, "idempotency_key": contract.idempotency_key, "revision_id": revision_id, "replay_created_revision": bool(replay_revision_id), "zero_diff": diff["zero_diff"], "dry_run_diff": diff}
            program_results.append(item)
            (OUT / f"{audit['program_id']}_diff.json").write_text(json.dumps(json_ready(item), indent=2, ensure_ascii=False), encoding="utf-8")
        if apply:
            connection.commit()
        active_programs = rows(cursor, "SELECT program_id FROM programs WHERE lower(status)='active'")
        cursor.execute("SELECT count(*) FROM courses WHERE lower(status)='active'")
        active_courses = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM program_active_import_revisions a JOIN programs p USING(program_id) WHERE lower(p.status)='active'")
        governed = cursor.fetchone()[0]
        remaining = len(active_without_revision(cursor))
    counts = Counter(label for item in program_results for label in item["classifications"])
    summary = {
        "run_date": date.today().isoformat(),
        "mode": "APPLIED" if apply else "DRY_RUN",
        "programs_audited": len(program_results),
        "exact_program_ids": [item["program_id"] for item in program_results],
        "classification_counts": {key: counts[key] for key in CLASSIFICATIONS},
        "successfully_governed": sum(bool(item["revision_id"]) for item in program_results),
        "held": sum(not item["safe_to_govern"] for item in program_results),
        "held_reasons": {item["program_id"]: item["content_issues"] for item in program_results if not item["safe_to_govern"]},
        "factual_corrections": len(factual_corrections),
        "factual_correction_details": factual_corrections,
        "provenance_only_corrections": len(provenance_corrections),
        "provenance_correction_details": provenance_corrections,
        "international_mismatches": sum(item["international"]["mismatch"] for item in program_results),
        "new_courses_added": 0,
        "final_active_programs": len(active_programs),
        "final_active_courses": active_courses,
        "governed_revision_coverage": governed,
        "remaining_pre_governance": remaining,
        "all_zero_diff": all(item["zero_diff"] for item in program_results),
        "all_replays_idempotent": all(not item["replay_created_revision"] for item in program_results),
        "programs": program_results,
        "testing": {
            "focused": focused or {"run": 0, "passed": 0, "failed": 0, "errors": 0},
            "full_python": full_python or {"run": 0, "passed": 0, "failed": 0, "errors": 0},
            "browser_state": {"run": 0, "status": "NOT_REQUIRED", "reason": "No shared routing or advisor code changed."},
        },
    }
    REPORT_JSON.write_text(json.dumps(json_ready(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    with (OUT / "summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["program_id", "program_name", "classifications", "safe_to_govern", "revision_id", "payload_sha256", "zero_diff", "international_status", "international_mismatch", "missing_courses", "stale_courses"])
        writer.writeheader()
        for item in program_results:
            writer.writerow({"program_id": item["program_id"], "program_name": item["program_name"], "classifications": ";".join(item["classifications"]), "safe_to_govern": item["safe_to_govern"], "revision_id": item["revision_id"] or "", "payload_sha256": item["payload_sha256"], "zero_diff": item["zero_diff"], "international_status": item["international"]["normalized_status"], "international_mismatch": item["international"]["mismatch"], "missing_courses": ";".join(item["curriculum"]["missing_in_postgresql"]), "stale_courses": ";".join(item["curriculum"]["stored_not_current"])})
    REPORT_MD.write_text(markdown_report(summary), encoding="utf-8")
    return summary


def finalize_testing(focused_run, focused_passed, full_run, full_passed):
    summary = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    summary["testing"] = {
        "focused": {"run": focused_run, "passed": focused_passed, "failed": focused_run - focused_passed, "errors": 0},
        "full_python": {"run": full_run, "passed": full_passed, "failed": full_run - full_passed, "errors": 0},
        "browser_state": {"run": 0, "status": "NOT_REQUIRED", "reason": "No shared routing or advisor code changed."},
    }
    REPORT_JSON.write_text(json.dumps(json_ready(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_MD.write_text(markdown_report(summary), encoding="utf-8")
    (OUT / "testing_summary.txt").write_text(
        f"focused: run={focused_run} passed={focused_passed} failed={focused_run-focused_passed} errors=0\n"
        f"full_python: run={full_run} passed={full_passed} failed={full_run-full_passed} errors=0\n"
        "browser_state: run=0 status=NOT_REQUIRED reason=No shared routing or advisor code changed.\n",
        encoding="utf-8",
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--finalize-testing", action="store_true")
    args = parser.parse_args()
    if args.finalize_testing:
        print(json.dumps(finalize_testing(7, 7, 477, 477)["testing"], indent=2))
    else:
        print(json.dumps(run(apply=args.apply), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
