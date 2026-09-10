"""Read-only live PostgreSQL smoke checks for Advisor V2 Phase 4."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from advisor_v2 import AdvisorV2Repository, StudentProfileV2
from database import get_connection
from phase4_eligibility_inventory import json_value


REPRESENTATIVE_PROFILES = {
    "1165DIPMA": StudentProfileV2(
        grades={"ENGLISH_STUDIES_12": 73, "PRE_CALCULUS_11": 65},
        application_date="2026-10-01",
    ),
    "8630BACC": StudentProfileV2(
        grades={"ENGLISH_STUDIES_12": 72}, gpa=75,
        credentials=["BCIT Accounting diploma"],
        subject_sequence_averages=[66, 67, 68, 64, 63],
        assessments_completed=["departmental pre-entry assessment"],
    ),
    "8800BTECH": StudentProfileV2(
        grades={"ENGLISH_STUDIES_12": 75}, gpa=72,
        credentials=["construction technology diploma"], work_experience_years=2,
        assessments_completed=["departmental pre-entry assessment"],
        international_status="domestic",
    ),
    "8900BTECH": StudentProfileV2(
        gpa=70, credentials=["BCIT Electrical and Computer Engineering Technology diploma"],
        assessments_completed=["pre-entry assessment"],
    ),
    "9940BSC": StudentProfileV2(gpa=78, intake="September 2026"),
    "M600MSC": StudentProfileV2(
        grades={"ENGLISH_STUDIES_12": 72}, gpa=75,
        credentials=["bachelor degree in computer science"],
        documents=["applicant questionnaire", "references"], international_status="domestic",
    ),
}


def run() -> dict:
    with get_connection() as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        rows = connection.execute(
            """SELECT DISTINCT ars.program_id
               FROM academic_rule_sets ars JOIN programs p USING(program_id)
               WHERE ars.rule_scope = 'ADMISSION' AND p.status = 'Active'
               ORDER BY ars.program_id"""
        ).fetchall()
    repo = AdvisorV2Repository()
    empty_statuses = Counter()
    failures = []
    for (program_id,) in rows:
        result = repo.evaluate_admission(program_id, StudentProfileV2())
        status = (result.get("data") or {}).get("status")
        empty_statuses[status] += 1
        if result["status"] not in {"found", "not_found"}:
            failures.append({"program_id": program_id, "retrieval_status": result["status"], "detail": result.get("detail")})
    representative = {}
    for program_id, profile in REPRESENTATIVE_PROFILES.items():
        result = repo.evaluate_admission(program_id, profile)
        representative[program_id] = {
            "retrieval_status": result["status"],
            "evaluation_status": (result.get("data") or {}).get("status"),
            "status_counts": (result.get("data") or {}).get("status_counts"),
            "needed_student_fields": (result.get("data") or {}).get("needed_student_fields"),
        }
    return json_value({
        "mode": "read-only smoke; inventory selection used SET TRANSACTION READ ONLY",
        "programs_checked": len(rows), "retrieval_failures": failures,
        "empty_profile_status_distribution": dict(empty_statuses),
        "representative_programs": representative,
    })


if __name__ == "__main__":
    output = run()
    path = Path("outputs") / "phase4_live_db_smoke.json"
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
