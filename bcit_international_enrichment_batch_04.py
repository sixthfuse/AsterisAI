"""Apply exactly the next 50 ready BCIT international-enrichment programs after Batches 01-03."""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import bcit_international_enrichment_planner as planner
from database import get_connection
from psycopg.rows import dict_row


ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "BCIT_INTERNATIONAL_ENRICHMENT_PLAN.json"
BATCH_01_SUMMARY = ROOT / "BCIT_INTERNATIONAL_ENRICHMENT_BATCH_01.json"
BATCH_02_SUMMARY = ROOT / "BCIT_INTERNATIONAL_ENRICHMENT_BATCH_02.json"
BATCH_03_SUMMARY = ROOT / "BCIT_INTERNATIONAL_ENRICHMENT_BATCH_03.json"
OUT = ROOT / "program_extractor_audit/international_enrichment_batch_04"
SUMMARY = ROOT / "BCIT_INTERNATIONAL_ENRICHMENT_BATCH_04.json"
REPORT = ROOT / "BCIT_INTERNATIONAL_ENRICHMENT_BATCH_04.md"
BLOCKED = {"6130DIPMA", "810BBSN", "810CBSN", "810KBSN", "810NBSN", "M600MSC"}


def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def jsonable(value):
    return json.loads(packed(value))


def load_approved():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if len(plan.get("first_batch_program_ids", [])) != 50:
        from bcit_international_batch_archive import load_archived
        return load_archived(SUMMARY, OUT)
    batch_01 = json.loads(BATCH_01_SUMMARY.read_text(encoding="utf-8"))
    batch_02 = json.loads(BATCH_02_SUMMARY.read_text(encoding="utf-8"))
    batch_03 = json.loads(BATCH_03_SUMMARY.read_text(encoding="utf-8"))
    batch_01_ids = batch_01["approved_program_ids"]
    batch_02_ids = batch_02["approved_program_ids"]
    batch_03_ids = batch_03["approved_program_ids"]
    if batch_01_ids != plan["first_batch_program_ids"] or batch_01["applied_count"] != 50:
        raise RuntimeError("Batch 01 applied scope does not match the planner's approved first 50")
    if batch_02["applied_count"] != 50 or set(batch_01_ids) & set(batch_02_ids):
        raise RuntimeError("Batch 02 applied scope is incomplete or overlaps Batch 01")
    prior_ids = batch_01_ids + batch_02_ids
    if batch_03["applied_count"] != 50 or set(prior_ids) & set(batch_03_ids):
        raise RuntimeError("Batch 03 applied scope is incomplete or overlaps Batches 01-02")
    ids = [
        row["program_id"] for row in plan["proposed_programs"]
        if row["action"] in ("INSERT", "UPDATE")
        and row["program_id"] not in batch_01_ids
        and row["program_id"] not in batch_02_ids
        and row["program_id"] not in batch_03_ids
        and row["program_id"] not in BLOCKED
    ][:50]
    batch_rows = [{"program_id": pid} for pid in ids]
    if len(ids) != 50 or len(set(ids)) != 50:
        raise RuntimeError("Planner does not contain exactly 50 distinct next-ready programs")
    if set(ids) & BLOCKED:
        raise RuntimeError("A known blocked program appears in Batch 04")
    entries = {row["program_id"]: row for row in plan["proposed_programs"] if row["program_id"] in ids}
    if list(pid for pid in ids if pid not in entries):
        raise RuntimeError("Approved batch contains a program absent from proposed_programs")
    if any(entries[pid]["action"] not in ("INSERT", "UPDATE") for pid in ids):
        raise RuntimeError("Approved batch contains a non-actionable program")
    return plan, batch_rows, ids, entries


def verify_sources(ids, entries):
    OUT.mkdir(parents=True, exist_ok=True)
    source_dir = OUT / "sources"
    source_dir.mkdir(exist_ok=True)
    specs = {}
    for pid in ids:
        for source in entries[pid]["evidence"]:
            specs[source["key"]] = source
    results = {}
    for key, source in specs.items():
        result = {
            "key": key,
            "url": source["url"],
            "approved_raw_sha256": source["live_sha256"],
            "approved_stable_content_sha256": source["live_content_sha256"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "error": "",
        }
        try:
            approved_path = ROOT / source["live_path"]
            approved = approved_path.read_bytes()
            if planner.digest(approved) != source["live_sha256"]:
                raise RuntimeError("Approved retained source bytes no longer match the planner hash")
            request = urllib.request.Request(source["url"], headers={"User-Agent": "Asteris BCIT international enrichment Batch 04/1.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                result["final_url"] = response.url
                if planner.canonical(response.url) != planner.canonical(source["url"]):
                    raise RuntimeError("Unexpected source redirect URL")
                fresh = response.read()
            result["live_raw_sha256"] = planner.digest(fresh)
            result["live_stable_content_sha256"] = planner.digest(planner.stable_source_bytes(fresh))
            (source_dir / f"{key}.html").write_bytes(fresh)
            if planner.stable_source_bytes(fresh) != planner.stable_source_bytes(approved):
                raise RuntimeError("Source drift outside the allowed WordPress generation timestamp comment")
            result["verification"] = (
                "EXACT_BYTES_MATCH" if fresh == approved else "ONLY_GENERATION_TIMESTAMP_COMMENT_CHANGED"
            )
            result["records"] = planner.list_records(fresh) if key in planner.LISTS else None
        except Exception as exc:
            result["error"] = str(exc)
            result["verification"] = "DRIFT_OR_ERROR"
        results[key] = result

    program_errors = {pid: [] for pid in ids}
    for pid in ids:
        entry = entries[pid]
        for approved_source in entry["evidence"]:
            current = results[approved_source["key"]]
            if current["error"]:
                program_errors[pid].append(f"{approved_source['key']}: {current['error']}")
                continue
            if approved_source["key"] in planner.LISTS:
                record = current["records"].get(pid)
                expected_url = planner.canonical(entry["current_state"]["delivery_facts"]["source_url"] if entry["current_state"]["delivery_facts"] else next(
                    p["source_url"] for p in json.loads((planner.OUT / "input_snapshot.json").read_text(encoding="utf-8"))["db"]["programs"] if p["program_id"] == pid
                ))
                if not record or not record["international"] or record["url"] != expected_url:
                    program_errors[pid].append(f"{approved_source['key']}: exact ID/URL/positive flag no longer matches")
                approved_note = json.loads(next(a for a in entry["proposed_db_actions"] if a["table"] == "academic_rule_sets")["values"]["notes"])
                if record and record["pgwp"] != (approved_note["pgwp"] == "ELIGIBLE_TO_APPLY"):
                    program_errors[pid].append(f"{approved_source['key']}: PGWP flag changed")
    return results, program_errors


def fetch_selected_state(cursor, pid):
    cursor.execute("SELECT * FROM programs WHERE program_id=%s FOR UPDATE", (pid,))
    program = cursor.fetchone()
    cursor.execute("SELECT * FROM program_delivery_facts WHERE program_id=%s FOR UPDATE", (pid,))
    fact = cursor.fetchone()
    cursor.execute("SELECT * FROM academic_rule_sets WHERE program_id=%s AND rule_scope='INTERNATIONAL' ORDER BY rule_set_id FOR UPDATE", (pid,))
    rules = cursor.fetchall()
    return {"program": jsonable(program), "delivery_facts": jsonable(fact), "international_rule_sets": jsonable(rules)}


def action_is_already_satisfied(cursor, action, status):
    pid = action["key"]["program_id"]
    if action["table"] == "program_delivery_facts":
        cursor.execute("SELECT * FROM program_delivery_facts WHERE program_id=%s", (pid,))
        row = cursor.fetchone()
        return row is not None and planner.status_from_text(row["international_eligibility"]) == status
    cursor.execute("SELECT notes FROM academic_rule_sets WHERE program_id=%s AND rule_scope='INTERNATIONAL'", (pid,))
    return any(planner.status_from_text(row["notes"]) == status for row in cursor.fetchall())


def validate_precondition(cursor, action):
    pid = action["key"]["program_id"]
    if action["table"] != "program_delivery_facts":
        return
    cursor.execute("SELECT * FROM program_delivery_facts WHERE program_id=%s", (pid,))
    current = jsonable(cursor.fetchone())
    expected = jsonable(action["precondition"])
    if current != expected:
        raise RuntimeError(f"{pid}: delivery-facts precondition changed after planner approval")


def execute_action(cursor, action):
    table = action["table"]
    values = {**action["key"], **action["values"]}
    if action["action"] == "UPDATE":
        assignments = ",".join(f"{column}=%s" for column in action["values"])
        cursor.execute(
            f"UPDATE {table} SET {assignments} WHERE program_id=%s",
            (*action["values"].values(), action["key"]["program_id"]),
        )
        if cursor.rowcount != 1:
            raise RuntimeError(f"Expected one updated row in {table}")
    elif action["action"] == "INSERT":
        columns = ",".join(values)
        placeholders = ",".join(["%s"] * len(values))
        cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))
    else:
        raise RuntimeError("Unsupported approved database action")


def count_stored_deterministic(db):
    rule_statuses = {}
    for row in db["academic_rule_sets"]:
        if row["rule_scope"] == "INTERNATIONAL":
            rule_statuses.setdefault(row["program_id"], set()).add(planner.status_from_text(row["notes"]))
    facts = {row["program_id"]: planner.status_from_text(row["international_eligibility"]) for row in db["program_delivery_facts"]}
    active = {row["program_id"] for row in db["programs"] if row["status"].upper() == "ACTIVE"}
    return sum(
        facts.get(pid) != planner.UNKNOWN or any(status != planner.UNKNOWN for status in rule_statuses.get(pid, set()))
        for pid in active
    )


def exact_duplicate_count(db):
    keys = [
        (r["program_id"], r["rule_scope"], r["rule_name"], r["study_mode"], r["source_url"], r["notes"])
        for r in db["academic_rule_sets"] if r["rule_scope"] == "INTERNATIONAL"
    ]
    return sum(count - 1 for count in Counter(keys).values() if count > 1)


def write_csv(name, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["program_id"]
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: packed(value) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def render(summary):
    tests = summary.get("testing", {})
    lines = [
        "# BCIT International Eligibility Enrichment Batch 04", "",
        f"Run date: {summary['run_date']}", "",
        "## Outcome", "",
        f"Requested batch size: **{summary['requested_batch_size']}**. Applied: **{summary['applied_count']}**; held: **{summary['held_count']}**.", "",
        f"Program actions: `{packed(summary['program_action_counts'])}`. Database-row actions: `{packed(summary['database_row_action_counts'])}`.", "",
        f"The database now has {summary['deterministic_structured_programs']} active programs with deterministic structured international status. {summary['remaining_ready_programs']} planner-ready programs remain; {summary['remaining_blocked_programs']} deterministic programs remain blocked; all {summary['unknown_untouched']} unknown programs remain untouched.", "",
        f"PGWP evidence changed for {summary['pgwp_evidence_changed']} programs; study-permit evidence changed for {summary['study_permit_evidence_changed']} programs. BCIT wording remains `eligible to apply`.", "",
        "## Safeguards", "",
        f"Source drift detected: **{str(summary['source_drift_detected']).lower()}**. Exact duplicate INTERNATIONAL rows: **{summary['duplicate_international_rows']}**. Idempotency replay database-row changes: **{summary['idempotency_replay_changes']}**.", "",
        f"No schema migration occurred. Active program/course totals remain **{summary['final_active_programs']} / {summary['final_active_courses']}**. Existing non-batch INTERNATIONAL rows, including Accounting and Business Administration restrictions, were unchanged: **{str(summary['existing_international_rows_preserved']).lower()}**.", "",
        "## Per-program result", "",
        "| # | Program | Status | Action | Apply status | Source | Evidence SHA-256 | Before / after |", "|---:|---|---|---|---|---|---|---|",
    ]
    for row in summary["programs"]:
        state = f"{row['before_status']} → {row['after_status']}"
        lines.append(f"| {row['order']} | {row['program_id']} — {row['program_title'].replace('|', '/')} | {row['proposed_status']} | {row['approved_action']} | {row['apply_status']} | {row['source_url']} | `{row['source_sha256']}` | {state} |")
    lines += ["", "## Validation", ""]
    if tests:
        for label in ("focused", "python", "browser"):
            result = tests[label]
            lines.append(f"- {result['name']}: {result['passed']} passed of {result['run']}; {result['failures']} failures, {result['errors']} errors")
            lines.append("")
    else:
        lines.append("Test results pending.")
    lines += ["", "## Evidence files", "", "`program_extractor_audit/international_enrichment_batch_04/` contains per-program before/after state, applied database actions, source verification, the post-apply planner diff, and test logs."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_batch():
    started = time.monotonic()
    plan, batch_rows, ids, entries = load_approved()
    inputs = json.loads((planner.OUT / "input_snapshot.json").read_text(encoding="utf-8"))
    sources, source_errors = verify_sources(ids, entries)
    source_drift = any(result["error"] for result in sources.values())
    before_db = planner.database_snapshot()
    if sum(p["status"].upper() == "ACTIVE" for p in before_db["programs"]) != 374 or before_db["active_courses"] != 3976:
        raise RuntimeError("Required 374 active-program / 3,976 active-course baseline is not present")
    live_plan = planner.build_plan(planner.rows(planner.AUDIT / "program_coverage.csv"), before_db, inputs["sources"], planner.rows(planner.AUDIT / "availability_offerings.csv"), planner.rows(planner.AUDIT / "conflicts_and_refinements.csv"))
    live_entries = {entry["program_id"]: entry for entry in live_plan["proposed_programs"]}
    program_rows = []
    eligible = []
    for order, pid in enumerate(ids, 1):
        approved = entries[pid]
        current = live_entries[pid]
        errors = list(source_errors[pid])
        if current["action"] == "UNCHANGED":
            apply_status = "UNCHANGED"
        elif current["action"] not in ("INSERT", "UPDATE") or packed(current["proposed_db_actions"]) != packed(approved["proposed_db_actions"]):
            errors += current.get("blockers", []) or ["Current database proposal differs from the approved planner action"]
            apply_status = "HELD"
        elif errors:
            apply_status = "HELD"
        else:
            apply_status = "PENDING"
            eligible.append(pid)
        note = json.loads(next(a for a in approved["proposed_db_actions"] if a["table"] == "academic_rule_sets")["values"]["notes"])
        evidence = note["evidence"][0]
        program_rows.append({
            "order": order, "program_id": pid, "program_title": approved["program_title"],
            "proposed_status": approved["proposed_status"], "approved_action": approved["action"],
            "apply_status": apply_status, "hold_reasons": errors, "source_url": evidence["url"],
            "source_sha256": evidence["source_sha256"], "source_checked_at": evidence["checked_at"],
            "evidence_type": evidence["evidence_type"], "pgwp": note["pgwp"], "study_permit": note["study_permit"],
            "before_status": planner.status_from_text((current["current_state"].get("delivery_facts") or {}).get("international_eligibility")),
            "after_status": None, "before_state": current["current_state"], "after_state": None,
        })

    before_existing = [r for r in before_db["academic_rule_sets"] if r["rule_scope"] == "INTERNATIONAL" and r["program_id"] not in ids]
    applied_actions = []
    if eligible:
        with get_connection() as conn:
            conn.isolation_level = __import__("psycopg").IsolationLevel.SERIALIZABLE
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", (2026090804,))
                locked = {pid: fetch_selected_state(cursor, pid) for pid in eligible}
                for pid in eligible:
                    approved = entries[pid]
                    status = approved["proposed_status"]
                    for action in approved["proposed_db_actions"]:
                        if action_is_already_satisfied(cursor, action, status):
                            raise RuntimeError(f"{pid}: action became satisfied after the pre-apply diff; refusing partial replay")
                        validate_precondition(cursor, action)
                        execute_action(cursor, action)
                        applied_actions.append({"program_id": pid, **action})
                conn.commit()
        for row in program_rows:
            if row["program_id"] in eligible:
                row["apply_status"] = "APPLIED"

    after_db = planner.database_snapshot()
    post_plan = planner.build_plan(planner.rows(planner.AUDIT / "program_coverage.csv"), after_db, inputs["sources"], planner.rows(planner.AUDIT / "availability_offerings.csv"), planner.rows(planner.AUDIT / "conflicts_and_refinements.csv"))
    post_entries = {entry["program_id"]: entry for entry in post_plan["proposed_programs"]}
    replay_changes = 0
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
        for pid in eligible:
            for action in entries[pid]["proposed_db_actions"]:
                if not action_is_already_satisfied(cursor, action, entries[pid]["proposed_status"]):
                    replay_changes += 1
        conn.rollback()
    for row in program_rows:
        current = post_entries[row["program_id"]]
        row["after_status"] = planner.status_from_text((current["current_state"].get("delivery_facts") or {}).get("international_eligibility"))
        if row["after_status"] == planner.UNKNOWN:
            statuses = [planner.status_from_text(rule["notes"]) for rule in current["current_state"]["international_rule_sets"]]
            row["after_status"] = next((status for status in statuses if status != planner.UNKNOWN), planner.UNKNOWN)
        row["after_state"] = current["current_state"]
        if row["apply_status"] == "APPLIED" and (current["action"] != "UNCHANGED" or current["proposed_db_actions"]):
            raise RuntimeError(f"{row['program_id']}: post-apply planner did not converge to UNCHANGED")

    after_existing = [r for r in after_db["academic_rule_sets"] if r["rule_scope"] == "INTERNATIONAL" and r["program_id"] not in ids]
    applied = [row for row in program_rows if row["apply_status"] == "APPLIED"]
    held = [row for row in program_rows if row["apply_status"] == "HELD"]
    unchanged = [row for row in program_rows if row["apply_status"] == "UNCHANGED"]
    summary = {
        "run_date": datetime.now(timezone.utc).date().isoformat(),
        "requested_batch_size": 50, "approved_program_ids": ids,
        "applied_count": len(applied), "held_count": len(held),
        "program_action_counts": dict(Counter(row["approved_action"] if row["apply_status"] == "APPLIED" else row["apply_status"] for row in program_rows)),
        "database_row_action_counts": dict(Counter(action["action"] for action in applied_actions)),
        "deterministic_structured_programs": count_stored_deterministic(after_db),
        "remaining_ready_programs": post_plan["ready_for_enrichment"],
        "remaining_blocked_programs": post_plan["blocked_programs"],
        "unknown_untouched": post_plan["unknown_untouched"],
        "pgwp_evidence_changed": sum(row["pgwp"] == "ELIGIBLE_TO_APPLY" for row in applied),
        "study_permit_evidence_changed": sum(row["study_permit"] != planner.UNKNOWN for row in applied),
        "duplicate_international_rows": exact_duplicate_count(after_db),
        "idempotency_replay_changes": replay_changes,
        "source_drift_detected": source_drift,
        "source_verification": [{key: value for key, value in result.items() if key != "records"} for result in sources.values()],
        "existing_international_rows_preserved": packed(before_existing) == packed(after_existing),
        "final_active_programs": sum(p["status"].upper() == "ACTIVE" for p in after_db["programs"]),
        "final_active_courses": after_db["active_courses"],
        "schema_migration_count": 0,
        "planner_post_apply": {
            "ready_for_enrichment": post_plan["ready_for_enrichment"], "blocked_programs": post_plan["blocked_programs"],
            "unknown_untouched": post_plan["unknown_untouched"], "batch_entries_unchanged": sum(post_entries[pid]["action"] == "UNCHANGED" for pid in ids),
        },
        "programs": program_rows, "runtime_seconds_before_tests": round(time.monotonic() - started, 3),
    }
    if summary["duplicate_international_rows"] or replay_changes or not summary["existing_international_rows_preserved"]:
        raise RuntimeError("Post-apply integrity check failed")
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv("pre_apply_diff.csv", [{
        "order": row["order"], "program_id": row["program_id"], "program_title": row["program_title"],
        "proposed_status": row["proposed_status"], "approved_action": row["approved_action"],
        "apply_status": row["apply_status"], "hold_reasons": row["hold_reasons"],
        "proposed_db_actions": entries[row["program_id"]]["proposed_db_actions"],
        "before_state": row["before_state"],
    } for row in program_rows])
    write_csv("program_summary.csv", program_rows)
    write_csv("applied_actions.csv", applied_actions)
    write_csv("source_verification.csv", summary["source_verification"])
    write_csv("post_apply_planner_diff.csv", [{"program_id": pid, "action": post_entries[pid]["action"], "proposed_db_actions": post_entries[pid]["proposed_db_actions"], "blockers": post_entries[pid]["blockers"]} for pid in ids])
    render(summary)
    print(packed({key: summary[key] for key in ("requested_batch_size", "applied_count", "held_count", "program_action_counts", "database_row_action_counts", "deterministic_structured_programs", "remaining_ready_programs", "remaining_blocked_programs", "unknown_untouched", "source_drift_detected", "idempotency_replay_changes", "final_active_programs", "final_active_courses")}))


def parse_unittest(path, name):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Ran (\d+) tests?", text)
    run = int(match.group(1)) if match else 0
    failures = int((re.search(r"failures=(\d+)", text) or [None, 0])[1])
    errors = int((re.search(r"errors=(\d+)", text) or [None, 0])[1])
    skipped = int((re.search(r"skipped=(\d+)", text) or [None, 0])[1])
    return {"name": name, "run": run, "passed": run - failures - errors - skipped, "failures": failures, "errors": errors, "skipped": skipped, "status": "PASS" if run and not failures and not errors and "FAILED" not in text else "FAIL"}


def parse_browser(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    def metric(label):
        match = re.search(rf"(?:#|ℹ) {label} (\d+)", text)
        return int(match.group(1)) if match else 0
    return {"name": "Browser-state suite", "run": metric("tests"), "passed": metric("pass"), "failures": metric("fail"), "errors": 0, "skipped": metric("skipped"), "status": "PASS" if metric("tests") and metric("fail") == 0 else "FAIL"}


def finalize(focused, python, browser):
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    _, _, _, entries = load_approved()
    write_csv("pre_apply_diff.csv", [{
        "order": row["order"], "program_id": row["program_id"], "program_title": row["program_title"],
        "proposed_status": row["proposed_status"], "approved_action": row["approved_action"],
        "apply_status": row["apply_status"], "hold_reasons": row["hold_reasons"],
        "proposed_db_actions": entries[row["program_id"]]["proposed_db_actions"],
        "before_state": row["before_state"],
    } for row in summary["programs"]])
    summary["testing"] = {
        "focused": parse_unittest(focused, "Focused international-enrichment tests"),
        "python": parse_unittest(python, "Full Python regression suite"),
        "browser": parse_browser(browser),
    }
    summary["testing_all_passed"] = all(result["status"] == "PASS" for result in summary["testing"].values())
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render(summary)
    print(packed(summary["testing"]))
    if not summary["testing_all_passed"]:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--finalize", nargs=3, metavar=("FOCUSED_LOG", "PYTHON_LOG", "BROWSER_LOG"))
    args = parser.parse_args()
    if args.apply:
        apply_batch()
    elif args.finalize:
        finalize(*args.finalize)
    else:
        parser.error("Choose --apply or --finalize")


if __name__ == "__main__":
    main()
