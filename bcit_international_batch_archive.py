"""Read immutable applied-batch evidence after the mutable planner moves to final state."""
import csv
import hashlib
import json


def load_archived(summary_path, audit_dir):
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    ids = summary["approved_program_ids"]
    program_rows = {row["program_id"]: row for row in summary["programs"]}
    actions = {pid: [] for pid in ids}
    with (audit_dir / "applied_actions.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            actions[row["program_id"]].append({
                "table": row["table"], "action": row["action"], "key": json.loads(row["key"]),
                "values": json.loads(row["values"]),
                "precondition": json.loads(row["precondition"]) if row["precondition"].startswith(("{", "[", '"')) else row["precondition"],
            })
    entries = {}
    for pid in ids:
        row = program_rows[pid]
        source_url = row["source_url"]
        key = "international_full_time" if source_url.endswith("regular-credential-programs/") else "international_flexible" if source_url.endswith("flexible-credential-programs/") else pid
        source_path = audit_dir / "sources" / (key + ".html")
        source = source_path.read_bytes()
        entries[pid] = {
            "program_id": pid, "program_title": row["program_title"], "action": row["approved_action"],
            "proposed_status": row["proposed_status"], "proposed_db_actions": actions[pid],
            "evidence": [{"key": key, "url": source_url, "live_path": str(source_path),
                          "live_sha256": hashlib.sha256(source).hexdigest(),
                          "live_content_sha256": hashlib.sha256(source).hexdigest()}],
        }
    return summary, [{"program_id": pid} for pid in ids], ids, entries
