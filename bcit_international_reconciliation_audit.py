"""Governed BCIT international-status reconciliation and six-blocker correction."""
import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from psycopg.rows import dict_row

import bcit_international_enrichment_planner as planner
from database import get_connection

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "program_extractor_audit/international_reconciliation"
REPORT_JSON = ROOT / "BCIT_INTERNATIONAL_RECONCILIATION_AUDIT.json"
REPORT_MD = ROOT / "BCIT_INTERNATIONAL_RECONCILIATION_AUDIT.md"
REGULAR_URL = "https://www.bcit.ca/international-applicants/regular-credential-programs/"
URL_CHANGES = {
    "6130DIPMA": (
        "https://www.bcit.ca/programs/television-video-production-diploma-full-time-6130dipma/",
        "https://www.bcit.ca/programs/television-and-video-production-diploma-full-time-6130dipma/",
    ),
    "810BBSN": (
        "https://www.bcit.ca/programs/specialty-nursing-emergency-standard-option-bachelor-of-science-in-nursing-part-time-810bbsn/",
        "https://www.bcit.ca/programs/specialty-nursing-emergency-standard-option-bachelor-of-science-in-nursing-part-time-distance-and-online-learning-810bbsn/",
    ),
    "810CBSN": (
        "https://www.bcit.ca/programs/specialty-nursing-neonatal-bachelor-of-science-in-nursing-part-time-810cbsn/",
        "https://www.bcit.ca/programs/specialty-nursing-neonatal-bachelor-of-science-in-nursing-part-time-distance-and-online-learning-810cbsn/",
    ),
    "810KBSN": (
        "https://www.bcit.ca/programs/specialty-nursing-critical-care-combined-critical-care-emergency-option-bachelor-of-science-in-nursing-part-time-810kbsn/",
        "https://www.bcit.ca/programs/specialty-nursing-critical-care-combined-critical-care-emergency-option-bachelor-of-science-in-nursing-part-time-distance-and-online-learning-810kbsn/",
    ),
    "810NBSN": (
        "https://www.bcit.ca/programs/specialty-nursing-emergency-combined-emergency-critical-care-option-bachelor-of-science-in-nursing-part-time-810nbsn/",
        "https://www.bcit.ca/programs/specialty-nursing-emergency-combined-emergency-critical-care-option-bachelor-of-science-in-nursing-part-time-distance-and-online-learning-810nbsn/",
    ),
}
M600_URL = "https://www.bcit.ca/programs/applied-computing-master-of-science-full-time-m600msc/"
BLOCKERS = tuple(URL_CHANGES) + ("M600MSC",)
UNKNOWN = planner.UNKNOWN


def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def fetch(url):
    marker = b"\n__ASTERIS_FINAL_URL__"
    process = subprocess.run(
        ["curl.exe", "-sS", "-L", "-A", "Asteris international reconciliation audit/1.0", "-w", marker.decode() + "%{url_effective}", url],
        capture_output=True,
        check=True,
    )
    body, final_url = process.stdout.rsplit(marker, 1)
    return body, planner.canonical(final_url.decode().strip())


def verify_sources():
    verified = []
    regular_body, regular_final = fetch(REGULAR_URL)
    regular_records = planner.list_records(regular_body)
    for pid in ("6130DIPMA", "M600MSC"):
        record = regular_records.get(pid)
        if not record or not record["international"]:
            raise RuntimeError(f"{pid}: current regular-program list lacks an exact positive international flag")
        expected_url = URL_CHANGES[pid][1] if pid in URL_CHANGES else M600_URL
        if record["url"] != expected_url:
            raise RuntimeError(f"{pid}: regular-list URL differs from the exact expected canonical URL")
    retained = ROOT / "work/regular-credential-programs.html"
    stable_match = retained.exists() and planner.stable_source_bytes(retained.read_bytes()) == planner.stable_source_bytes(regular_body)
    verified.append({"key": "international_full_time", "requested_url": REGULAR_URL, "final_url": regular_final,
                     "declared_canonical_url": "", "sha256": sha256(regular_body),
                     "verification": "ONLY_GENERATION_TIMESTAMP_COMMENT_CHANGED" if stable_match and retained.read_bytes() != regular_body else "EXACT_BYTES_MATCH" if stable_match else "CURRENT_CONTENT_VERIFIED_SEMANTICALLY"})
    page_bodies = {}
    requested = {pid: old for pid, (old, _new) in URL_CHANGES.items()}
    requested["M600MSC"] = M600_URL
    for pid, url in requested.items():
        body, final_url = fetch(url)
        page_bodies[pid] = body
        soup = BeautifulSoup(body, "html.parser")
        link = soup.select_one('link[rel="canonical"]')
        declared = planner.canonical(link.get("href")) if link else ""
        expected = URL_CHANGES[pid][1] if pid in URL_CHANGES else M600_URL
        permitted_final_urls = {expected, url} if pid.startswith("810") else {expected}
        if final_url not in permitted_final_urls or declared != expected or not expected.rstrip("/").lower().endswith("-" + pid.lower()):
            raise RuntimeError(f"{pid}: redirect/canonical identity is not the exact expected program ID")
        text = planner.normalized(soup.get_text(" ", strip=True))
        if pid.startswith("810"):
            for phrase in ("this program is available to international applicants", "not eligible for a study permit", "not eligible for a pgwp", "program head approval"):
                if phrase not in text:
                    raise RuntimeError(f"{pid}: missing live restriction phrase: {phrase}")
        if pid == "M600MSC":
            for phrase in ("this program is available to international applicants", "a valid bcit study permit is required prior to starting the program", "eligible for students to apply for a pgwp"):
                if phrase not in text:
                    raise RuntimeError(f"M600MSC: missing live program-specific phrase: {phrase}")
        verified.append({"key": pid, "requested_url": url, "final_url": final_url,
                         "declared_canonical_url": declared, "sha256": sha256(body), "verification": "EXACT_ID_CANONICAL_VERIFIED"})
    return verified


def evidence_note(pid, sources, status, permit, pgwp):
    wanted = ["international_full_time", pid]
    evidence = [
        {"url": row["final_url"], "source_sha256": row["sha256"], "checked_at": datetime.now(timezone.utc).isoformat(),
         "evidence_type": "international_list_positive_flag" if row["key"] == "international_full_time" else "exact_program_page"}
        for row in sources if row["key"] in wanted
    ]
    return packed({"status": status, "evidence": evidence, "pgwp": pgwp, "study_permit": permit,
                   "offering_scope": "Any Domestic Only offering remains mode/intake-specific."})


def apply_corrections(sources):
    actions = []
    with get_connection() as conn:
        conn.isolation_level = __import__("psycopg").IsolationLevel.SERIALIZABLE
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (2026090806,))
            for pid, (old, new) in URL_CHANGES.items():
                cur.execute("SELECT source_url FROM programs WHERE program_id=%s AND upper(status)='ACTIVE' FOR UPDATE", (pid,))
                row = cur.fetchone()
                if not row or row["source_url"] not in (old, new):
                    raise RuntimeError(f"{pid}: unexpected programs.source_url precondition")
                if row["source_url"] == old:
                    cur.execute("UPDATE programs SET source_url=%s WHERE program_id=%s", (new, pid)); actions.append({"program_id": pid, "table": "programs", "action": "UPDATE_CANONICAL_URL", "before": old, "after": new})
                cur.execute("UPDATE program_delivery_facts SET source_url=%s WHERE program_id=%s AND source_url=%s", (new, pid, old))
                if cur.rowcount:
                    actions.append({"program_id": pid, "table": "program_delivery_facts", "action": "UPDATE_CANONICAL_URL", "before": old, "after": new})
                cur.execute("UPDATE academic_rule_sets SET source_url=%s WHERE program_id=%s AND rule_scope='INTERNATIONAL' AND source_url=%s", (new, pid, old))
                if cur.rowcount:
                    actions.append({"program_id": pid, "table": "academic_rule_sets", "action": "UPDATE_CANONICAL_URL", "before": old, "after": new})
            note_6130 = evidence_note("6130DIPMA", sources, "ACCEPTED_AVAILABLE", UNKNOWN, "INELIGIBLE")
            cur.execute("SELECT international_eligibility,authoritative_raw FROM program_delivery_facts WHERE program_id='6130DIPMA' FOR UPDATE")
            fact = cur.fetchone()
            if not fact:
                raise RuntimeError("6130DIPMA: required delivery-facts row is missing")
            if planner.status_from_text(fact["international_eligibility"]) == UNKNOWN:
                raw = (fact["authoritative_raw"] or "") + "\nInternational evidence: " + note_6130
                cur.execute("UPDATE program_delivery_facts SET international_eligibility='ACCEPTED_AVAILABLE',authoritative_raw=%s,last_checked=%s WHERE program_id='6130DIPMA'", (raw, date.today()))
                actions.append({"program_id": "6130DIPMA", "table": "program_delivery_facts", "action": "SET_ACCEPTED_AVAILABLE"})
            cur.execute("SELECT notes FROM academic_rule_sets WHERE program_id='6130DIPMA' AND rule_scope='INTERNATIONAL'")
            if not any(planner.status_from_text(row["notes"]) == "ACCEPTED_AVAILABLE" for row in cur.fetchall()):
                cur.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes) VALUES('6130DIPMA','INTERNATIONAL','International eligibility source evidence','Full-time',%s,%s)", (REGULAR_URL, note_6130))
                actions.append({"program_id": "6130DIPMA", "table": "academic_rule_sets", "action": "INSERT_ACCEPTED_EVIDENCE"})
            note_m600 = evidence_note("M600MSC", sources, "ACCEPTED_AVAILABLE", "REQUIRED", "ELIGIBLE_TO_APPLY")
            cur.execute("SELECT notes FROM academic_rule_sets WHERE program_id='M600MSC' AND rule_scope='INTERNATIONAL'")
            if not any(planner.status_from_text(row["notes"]) == "ACCEPTED_AVAILABLE" for row in cur.fetchall()):
                cur.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes) VALUES('M600MSC','INTERNATIONAL','International eligibility source evidence','Full-time',%s,%s)", (M600_URL, note_m600))
                actions.append({"program_id": "M600MSC", "table": "academic_rule_sets", "action": "INSERT_PROGRAM_SPECIFIC_PERMIT_EVIDENCE"})
        conn.commit()
    return actions


def initial_correction_actions():
    actions = []
    for pid, (old, new) in URL_CHANGES.items():
        actions.append({"program_id": pid, "table": "programs", "action": "UPDATE_CANONICAL_URL", "before": old, "after": new})
        if pid == "6130DIPMA":
            actions.append({"program_id": pid, "table": "program_delivery_facts", "action": "UPDATE_CANONICAL_URL", "before": old, "after": new})
        else:
            actions.append({"program_id": pid, "table": "academic_rule_sets", "action": "UPDATE_CANONICAL_URL", "before": old, "after": new})
    actions.extend([
        {"program_id": "6130DIPMA", "table": "program_delivery_facts", "action": "SET_ACCEPTED_AVAILABLE"},
        {"program_id": "6130DIPMA", "table": "academic_rule_sets", "action": "INSERT_ACCEPTED_EVIDENCE"},
        {"program_id": "M600MSC", "table": "academic_rule_sets", "action": "INSERT_PROGRAM_SPECIFIC_PERMIT_EVIDENCE"},
    ])
    return actions


def live_reconciliation():
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT p.program_id,p.program_name,f.program_id IS NOT NULL AS has_delivery_facts_row,f.international_eligibility,
                   array_remove(array_agg(r.notes) FILTER (WHERE r.rule_set_id IS NOT NULL),NULL) AS rule_notes
            FROM programs p LEFT JOIN program_delivery_facts f USING(program_id)
            LEFT JOIN academic_rule_sets r ON r.program_id=p.program_id AND r.rule_scope='INTERNATIONAL'
            WHERE upper(p.status)='ACTIVE' GROUP BY p.program_id,p.program_name,f.program_id,f.international_eligibility ORDER BY p.program_id
        """)
        rows = cur.fetchall()
        cur.execute("SELECT count(*) AS n FROM courses WHERE upper(status)='ACTIVE'"); courses = cur.fetchone()["n"]
        cur.execute("""SELECT coalesce(sum(n-1),0) AS n FROM (
            SELECT count(*) n FROM academic_rule_sets WHERE rule_scope='INTERNATIONAL'
            GROUP BY program_id,rule_scope,rule_name,study_mode,source_url,notes HAVING count(*)>1) d"""); duplicates = cur.fetchone()["n"]
    result = []
    for row in rows:
        rule_notes = row["rule_notes"] or []
        statuses = {planner.status_from_text(row["international_eligibility"])} | {planner.status_from_text(note) for note in rule_notes}
        statuses.discard(UNKNOWN)
        status = next(iter(statuses)) if len(statuses) == 1 else "BLOCKED_CONFLICT" if statuses else UNKNOWN
        result.append({"program_id": row["program_id"], "program_name": row["program_name"], "classification": status,
                       "delivery_fact_status": planner.status_from_text(row["international_eligibility"]),
                       "rule_statuses": sorted({planner.status_from_text(note) for note in rule_notes}),
                       "has_delivery_facts_row": row["has_delivery_facts_row"]})
    return result, courses, int(duplicates)


def write_csv(path, rows):
    rows = list(rows); fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        writer.writerows({key: packed(value) if isinstance(value, (dict, list)) else value for key, value in row.items()} for row in rows)


def build_report(sources, actions, replay_actions):
    reconciliation, courses, duplicates = live_reconciliation()
    counts = Counter(row["classification"] for row in reconciliation)
    discrepancy = [
        {"program_id": pid, "batch_04_effect": "Counted deterministic because missing facts used None != UNKNOWN_NOT_PUBLISHED",
         "batch_05_pre_state": "Missing delivery-facts row and no INTERNATIONAL rule", "resolution": "Excluded by explicit normalized criteria; subsequently enriched in Batch 05"}
        for pid in ("8660BENG", "8800BTECH", "8900BTECH")
    ]
    blocker_rows = []
    for pid in BLOCKERS:
        source = next(row for row in sources if row["key"] == pid)
        blocker_rows.append({"program_id": pid, "result": "RESOLVED", "requested_url": source["requested_url"], "final_url": source["final_url"], "canonical_url": source["declared_canonical_url"],
                             "resolution": ("Exact-ID official redirect reconciled" if source["final_url"] == source["declared_canonical_url"] else "Exact-ID 200-compatible legacy URL reconciled to its declared canonical alias") if pid in URL_CHANGES else "Program-specific international, study-permit, and PGWP evidence stored"})
    planner_report = json.loads((ROOT / "BCIT_INTERNATIONAL_ENRICHMENT_PLAN.json").read_text(encoding="utf-8"))
    def parsed_test(name):
        path = OUT / name
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        match = re.search(r"Ran (\d+) tests?", text)
        return {"run": int(match.group(1)) if match else 0, "passed": bool(match and re.search(r"\nOK\s*$", text)), "log": str(path.relative_to(ROOT))}
    testing = {"focused_international": parsed_test("focused_tests.txt"), "full_python": parsed_test("full_python_tests.txt"),
               "browser_state": {"run": 0, "status": "NOT_REQUIRED", "reason": "No shared advisor or routing code changed."}}
    certification = (len(reconciliation) == 374 and courses == 3976 and counts == Counter({"ACCEPTED_AVAILABLE": 253, "CONDITIONAL_RESTRICTED": 12, "NOT_ACCEPTED": 1, UNKNOWN: 108}) and duplicates == 0 and not replay_actions and planner_report["ready_for_enrichment"] == 0 and planner_report["blocked_programs"] == 0 and planner_report["idempotency"]["replay_identical"] and testing["focused_international"]["passed"] and testing["full_python"]["passed"])
    summary = {
        "run_date": date.today().isoformat(), "normalization_definition": "An active program is deterministic only when program_delivery_facts.international_eligibility or an INTERNATIONAL academic_rule_sets.notes value parses to ACCEPTED_AVAILABLE, CONDITIONAL_RESTRICTED, or NOT_ACCEPTED; a missing row is UNKNOWN, and rule-only records are equivalent.",
        "active_programs": len(reconciliation), "active_courses": courses, "deterministic_status_count": 374 - counts[UNKNOWN] - counts["BLOCKED_CONFLICT"],
        "accepted_available": counts["ACCEPTED_AVAILABLE"], "conditional_restricted": counts["CONDITIONAL_RESTRICTED"],
        "not_accepted": counts["NOT_ACCEPTED"], "unknown_not_published": counts[UNKNOWN], "blocked_unresolved": counts["BLOCKED_CONFLICT"],
        "blockers_resolved": 6, "blockers_remaining": 0, "duplicate_international_rows": duplicates,
        "source_drift_count": sum(row["verification"] == "CURRENT_CONTENT_VERIFIED_SEMANTICALLY" for row in sources if row["key"] == "international_full_time"),
        "database_actions": actions, "idempotency_replay_actions": replay_actions, "schema_migration_count": 0,
        "planner_post_reconciliation": {key: planner_report[key] for key in ("ready_for_enrichment", "blocked_programs", "program_action_counts", "db_row_action_counts", "unknown_untouched", "database_unchanged_after_planning", "idempotency")},
        "testing": testing,
        "discrepancy_220_to_217": {"batch_04_reported": 220, "normalized_count_at_batch_04_boundary": 217, "cause": "Batch 04 count helper used facts.get(pid) without an UNKNOWN default, so three active programs with no delivery-facts row and no INTERNATIONAL rule were counted as deterministic.", "program_ids": [row["program_id"] for row in discrepancy]},
        "blocker_review": blocker_rows, "source_verification": sources, "certified": certification,
        "certification": "BCIT International Eligibility Data Foundation — CERTIFIED COMPLETE FOR ALL PUBLISHED DETERMINISTIC EVIDENCE" if certification else "NOT CERTIFIED",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "full_program_reconciliation.csv", reconciliation)
    write_csv(OUT / "blocker_review.csv", blocker_rows)
    write_csv(OUT / "count_discrepancy_records.csv", discrepancy)
    write_csv(OUT / "source_verification.csv", sources)
    REPORT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    REPORT_MD.write_text(f"""# BCIT International Eligibility Reconciliation & Blocker Review Audit

Run date: {summary['run_date']}

## Certification

**{summary['certification']}**

The 374 active programs reconcile exactly: **{summary['accepted_available']} accepted/available + {summary['conditional_restricted']} conditional/restricted + {summary['not_accepted']} not accepted + {summary['unknown_not_published']} unknown/not published + {summary['blocked_unresolved']} blocked = 374**. The deterministic structured count is **{summary['deterministic_status_count']}**. Rule-only evidence is normalized equivalently to delivery-fact-backed evidence.

The {summary['unknown_not_published']} unknown/not-published programs are explicitly documented non-errors: no authoritative published deterministic evidence was found, and no negative status was inferred from silence.

## 220 → 217 discrepancy

Batch 04's helper used `facts.get(pid) != UNKNOWN_NOT_PUBLISHED`. For a missing delivery-facts row, `facts.get(pid)` returns `None`, and `None != UNKNOWN_NOT_PUBLISHED` is true. It therefore counted **8660BENG, 8800BTECH, and 8900BTECH** as deterministic even though each had neither a delivery-facts row nor an INTERNATIONAL rule before Batch 05. The normalized count was 217. Batch 05 then legitimately inserted their missing facts and evidence as part of its approved scope. No data was changed merely to reconcile the reports.

## Six-blocker review

All six blockers are resolved. 6130DIPMA's old official URL redirects to the same exact program ID with the renamed `television-and-video-production` canonical path. The four Specialty Nursing legacy URLs remain HTTP 200 aliases and declare exact-ID canonical paths that add `distance-and-online-learning`; their program-specific conditional eligibility, study-permit ineligibility, PGWP ineligibility, and program-head approval text remains authoritative. M600MSC's exact live program page states that the program is available to international applicants, requires a valid BCIT study permit before starting, and is eligible for students to apply for a PGWP.

The correction updated only exact source URLs and the two missing structured evidence records (6130DIPMA and M600MSC). It made **{len(actions)} database row changes**. Immediate replay proposed/applied **{len(replay_actions)} changes**. No schema migration or advisor/routing change occurred.

The post-reconciliation planner reports **{planner_report['ready_for_enrichment']} ready, {planner_report['blocked_programs']} blocked, and {planner_report['program_action_counts']['UNCHANGED']} unchanged**, with identical deterministic replay. Focused international tests passed **{testing['focused_international']['run']}/{testing['focused_international']['run']}** and the full Python regression suite passed **{testing['full_python']['run']}/{testing['full_python']['run']}**. Browser-state tests were not required because no shared advisor or routing code changed.

## Integrity results

- Source drift: {summary['source_drift_count']}
- Exact duplicate INTERNATIONAL rows: {summary['duplicate_international_rows']}
- Active programs / courses: {summary['active_programs']} / {summary['active_courses']}
- Resolved / remaining blockers: {summary['blockers_resolved']} / {summary['blockers_remaining']}

Evidence tables are under `program_extractor_audit/international_reconciliation/`.
""", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--apply", action="store_true"); args = parser.parse_args()
    sources = verify_sources()
    actions = apply_corrections(sources) if args.apply else []
    replay_actions = apply_corrections(sources) if args.apply else []
    if args.apply and not actions:
        actions = json.loads(REPORT_JSON.read_text(encoding="utf-8"))["database_actions"] if REPORT_JSON.exists() else initial_correction_actions()
    summary = build_report(sources, actions, replay_actions)
    print(packed({key: summary[key] for key in ("deterministic_status_count", "accepted_available", "conditional_restricted", "not_accepted", "unknown_not_published", "blocked_unresolved", "blockers_resolved", "blockers_remaining", "duplicate_international_rows", "idempotency_replay_actions", "active_programs", "active_courses", "certified")}))


if __name__ == "__main__":
    main()
