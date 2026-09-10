"""Import audited Specialty Nursing BScN programs as independent records.

The nursing batch JSON files remain the authoritative source. Missing courses are
validated through the existing BCIT gap-enrichment parser before any program is
written. Non-course professional and clinical requirements remain separate from
course prerequisites and default to human confirmation.
"""

import argparse
import json
import re
from pathlib import Path

from bcit_course_gap_enrichment import Discovery, apply_database, build_session, database_course_ids, parse_course_page
from database import get_connection
from program_import_contract import activate_revision, adapt_nursing_audit, record_import_revision, require_approved_hash, require_import_ready


SOURCE_METHOD = "nursing_family_audit"
COMMON_CLINICAL = (
    ("RN_REGISTRATION", "Practicing RN registration", "LICENSURE", "EACH_CLINICAL_COURSE", "Proof of current professional registration is required for clinical participation."),
    ("CPR_CERTIFICATION", "Current CPR certification", "CERTIFICATION", "CLINICAL_COURSES", "Current qualifying CPR certification with the required practical component must be confirmed."),
    ("RESPIRATOR_FIT_TEST", "Respirator fit testing", "HEALTH_AND_SAFETY", "CLINICAL_PRACTICUM", "Current fit-testing evidence and any required renewal must be confirmed."),
    ("INFLUENZA_POLICY", "Influenza immunization or masking", "HEALTH_AND_SAFETY", "CLINICAL_PLACEMENT", "Compliance with the published immunization or masking policy must be confirmed."),
)


def extract_international_applicant_rules(audit):
    text = (audit.get("authoritative_sections") or {}).get("admissions") or ""
    match = re.search(r"International applicants\s+(.*?)(?=\s+Apply to program\b|\s+Prior Learning\b|$)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    sections = audit.get("authoritative_sections") or {}
    apply_text = (sections.get("subsections") or {}).get("Apply to program") or ""
    approval = re.search(r"International students?\s+must\s+receive.*?(?=\s+To submit|$)", apply_text, re.IGNORECASE | re.DOTALL)
    combined = match.group(1) + (" " + approval.group(0) if approval else "")
    return re.sub(r"\s+", " ", combined).strip()


def load_audits(audit_dir, exclude=("810ABSN",)):
    audits = []
    for path in sorted(Path(audit_dir).glob("810*bsn_audit.json")):
        audit = json.loads(path.read_text(encoding="utf-8"))
        if audit["program_id"] not in exclude:
            audits.append(audit)
    return audits


def validate_missing_courses(audits):
    with get_connection() as connection, connection.cursor() as cursor:
        require_approved_hash(cursor, contract)
        cursor.execute("SELECT course_id FROM courses")
        existing = {row[0] for row in cursor.fetchall()}
    references = {
        ref["course_id"]: ref for audit in audits for ref in audit["course_references"]
        if ref["course_id"] not in existing
    }
    session = build_session()
    records = []
    for course_id, ref in sorted(references.items()):
        discovery = Discovery(
            course_id, ref["display_course_code"], ref["course_url"],
            audit_source_for(audits, course_id), SOURCE_METHOD,
        )
        record = parse_course_page(session, discovery, 0)
        if record.validation_status != "validated":
            record = parse_course_page(session, discovery, 0)
        records.append(record)
    return records


def audit_source_for(audits, course_id):
    return next(
        audit["source_url"] for audit in audits
        if course_id in audit["unique_course_ids"]
    )


def insert_rule_set(cursor, program_id, scope, name, source_url, notes):
    cursor.execute(
        """INSERT INTO academic_rule_sets
           (program_id,rule_scope,rule_name,study_mode,source_url,notes)
           VALUES(%s,%s,%s,'PART_TIME',%s,%s) RETURNING rule_set_id""",
        (program_id, scope, name, source_url, notes),
    )
    return cursor.fetchone()[0]


def import_program(audit):
    normalized_audit = dict(audit)
    normalized_audit["missing_unresolved_course_ids"] = sorted(
        set(audit.get("missing_unresolved_course_ids", [])) - database_course_ids()
    )
    contract = adapt_nursing_audit(normalized_audit)
    require_import_ready(contract)
    program_id = audit["program_id"]
    source = audit["source_url"]
    structured = audit.get("structured_requirement_text") or {}
    clinical_raw = structured.get("clinical_practicum_requirements_raw") or ""
    admissions_raw = structured.get("applicant_prerequisites_raw") or ""
    transfer_raw = structured.get("advanced_placement_plar_transfer_raw") or ""
    continuation_raw = structured.get("progression_continuation_completion_raw") or ""
    international_raw = extract_international_applicant_rules(audit)
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO programs
               (program_id,program_name,program_overview,area_id,school,credential,
                program_level,study_mode,accepts_international_students,campus,
                delivery_method,status,source_url,last_checked,notes)
               VALUES(%s,%s,%s,'A05',%s,%s,'Bachelor''s Degree',%s,%s,%s,%s,
                      'Active',%s,CURRENT_DATE,%s)
               ON CONFLICT(program_id) DO UPDATE SET program_name=EXCLUDED.program_name,
                 program_overview=EXCLUDED.program_overview,school=EXCLUDED.school,
                 credential=EXCLUDED.credential,study_mode=EXCLUDED.study_mode,
                 accepts_international_students=EXCLUDED.accepts_international_students,
                 campus=EXCLUDED.campus,delivery_method=EXCLUDED.delivery_method,
                 status=EXCLUDED.status,source_url=EXCLUDED.source_url,
                 last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes""",
            (program_id, audit["official_name"], audit["description"], audit["school_area"],
             audit["credential"], audit["study_mode"], bool(international_raw), audit["campus"], audit["delivery"],
             source, "Independent Specialty Nursing program; authoritative ambiguous rules require human confirmation."),
        )
        cursor.execute("DELETE FROM curriculum_component_courses WHERE component_id IN (SELECT component_id FROM curriculum_components WHERE program_id=%s)", (program_id,))
        cursor.execute("DELETE FROM credit_requirements WHERE program_id=%s", (program_id,))
        cursor.execute("DELETE FROM curriculum_components WHERE program_id=%s", (program_id,))
        cursor.execute("DELETE FROM program_courses WHERE program_id=%s", (program_id,))
        for component in audit["curriculum_components"]:
            required_credits = component.get("required_credits") or None
            cursor.execute(
                """INSERT INTO curriculum_components
                   (program_id,component_name,component_order,required_credits,notes)
                   VALUES(%s,%s,%s,%s,%s) RETURNING component_id""",
                (program_id, component["name"], component["order"], required_credits, component.get("raw_text")),
            )
            component_id = cursor.fetchone()[0]
            for course in component["courses"]:
                cursor.execute(
                    "INSERT INTO curriculum_component_courses(component_id,course_id,course_role) VALUES(%s,%s,%s)",
                    (component_id, course["course_id"], course["role"]),
                )
                course_type = "CLINICAL" if course["course_id"] in audit["clinical_practicum_course_ids"] else course["role"]
                cursor.execute(
                    """INSERT INTO program_courses(program_id,course_id,course_type,required,notes)
                       VALUES(%s,%s,%s,%s,%s)
                       ON CONFLICT(program_id,course_id) DO UPDATE SET
                         course_type=EXCLUDED.course_type,
                         required=(program_courses.required OR EXCLUDED.required),
                         notes=CONCAT_WS('; ',program_courses.notes,EXCLUDED.notes)""",
                    (program_id, course["course_id"], course_type, course["role"] == "REQUIRED", component["name"]),
                )
            if component["rule_type"] == "MINIMUM_CREDITS_FROM_POOL":
                credits = component.get("required_credits")
                if not credits:
                    import re
                    match = re.search(r"(\d+(?:\.\d+)?)\s+credits", component["name"], re.I)
                    credits = match.group(1) if match else None
                cursor.execute(
                    """INSERT INTO credit_requirements
                       (program_id,component_id,requirement_name,minimum_credits,study_mode,
                        allows_external_courses,approval_required,notes)
                       VALUES(%s,%s,%s,%s,'ALL',FALSE,FALSE,%s)""",
                    (program_id, component_id, component["name"], credits, component.get("raw_text")),
                )
        cursor.execute("DELETE FROM academic_rule_conditions WHERE rule_group_id IN (SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s)", (program_id,))
        cursor.execute("DELETE FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)", (program_id,))
        cursor.execute("DELETE FROM academic_rule_sets WHERE program_id=%s", (program_id,))
        admission_id = insert_rule_set(cursor, program_id, "ADMISSION", "Specialty Nursing entrance requirements", source, admissions_raw)
        cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND','Admission requirements',1) RETURNING rule_group_id", (admission_id,))
        group_id = cursor.fetchone()[0]
        common = (
            ("GRADE", "ENGLISH_STUDIES_12", 73, "PERCENT", True, "English Studies 12 at 73% or equivalent"),
            ("CREDENTIAL", "NURSING_DIPLOMA", None, None, True, "Post-secondary diploma in nursing"),
            ("LICENSURE", "PRACTICING_RN_REGISTRATION", None, None, False, "Professional registration requires institutional verification"),
            ("WORK_EXPERIENCE", "ACUTE_CARE", 6, "MONTHS", True, "Published minimum acute-care experience; recency and equivalence require confirmation"),
            ("DOCUMENT", "RESUME", None, None, False, "Resume and placement documentation require confirmation"),
        )
        for order, (kind, subject, minimum, unit, executable, description) in enumerate(common, 1):
            parameters = {"executable": executable, "verification": "human_confirmation" if not executable else "structured"}
            if kind == "WORK_EXPERIENCE":
                parameters["recency_qualification"] = "human_confirmation"
            cursor.execute(
                """INSERT INTO academic_rule_conditions
                   (rule_group_id,condition_type,subject_id,minimum_value,unit,parameters,description,sort_order)
                   VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s,%s)""",
                (group_id, kind, subject, minimum, unit, json.dumps(parameters), description, order),
            )
        if transfer_raw:
            insert_rule_set(cursor, program_id, "TRANSFER", "PLAR and transfer credit", source, transfer_raw)
        if continuation_raw:
            insert_rule_set(cursor, program_id, "CONTINUATION", "Specialty sequence, employment and placement conditions", source, continuation_raw)
        if international_raw:
            insert_rule_set(cursor, program_id, "INTERNATIONAL", "International applicant eligibility and permit restrictions", source, international_raw)
        cursor.execute("DELETE FROM clinical_placement_requirements WHERE program_id=%s", (program_id,))
        if clinical_raw or audit["clinical_practicum_course_ids"]:
            for order, (code, name, kind, applies_to, description) in enumerate(COMMON_CLINICAL, 1):
                cursor.execute(
                    """INSERT INTO clinical_placement_requirements
                       (program_id,requirement_code,requirement_name,requirement_type,applies_to,
                        executable,verification_method,description,source_url,parameters,sort_order)
                       VALUES(%s,%s,%s,%s,%s,FALSE,'HUMAN_CONFIRMATION',%s,%s,'{}',%s)""",
                    (program_id, code, name, kind, applies_to, description, source, order),
                )
            cursor.execute(
                """INSERT INTO clinical_placement_requirements
                   (program_id,requirement_code,requirement_name,requirement_type,applies_to,
                    executable,verification_method,description,source_url,parameters,sort_order)
                   VALUES(%s,'CLINICAL_APPLICATION','Completed clinical application','DOCUMENT',
                          'CLINICAL_COURSES',TRUE,'SELF_REPORTED',%s,%s,'{}',9)""",
                (program_id, "A completed clinical application is required for clinical courses.", source),
            )
        if any(rule["concept"] == "employer_site_requirement" for rule in audit["rules"]):
            cursor.execute(
                """INSERT INTO clinical_placement_requirements
                   (program_id,requirement_code,requirement_name,requirement_type,applies_to,
                    executable,verification_method,description,source_url,parameters,sort_order)
                   VALUES(%s,'EMPLOYER_SITE_REQUIREMENTS','Employer or clinical-site requirements',
                          'EMPLOYER_SITE','CLINICAL_PLACEMENT',FALSE,'HUMAN_CONFIRMATION',
                          %s,%s,'{}',10)""",
                (program_id, continuation_raw or clinical_raw or "Employer or site approval requirements must be confirmed.", source),
            )
        cursor.execute("DELETE FROM practice_hour_requirements WHERE program_id=%s", (program_id,))
        if audit["clinical_practicum_course_ids"]:
            cursor.execute(
                """INSERT INTO practice_hour_requirements
                   (program_id,requirement_code,requirement_name,required_hours,tracking_scope,
                    executable,verification_method,description,source_url,parameters,sort_order)
                   VALUES(%s,'PUBLISHED_CLINICAL_HOURS','Clinical practice hours',NULL,'PROGRAM',
                          FALSE,'HUMAN_CONFIRMATION',%s,%s,%s::jsonb,1)""",
                (program_id, "Clinical practice is required, but no authoritative numeric threshold is stated in the audit.", source,
                 json.dumps({"clinical_courses": audit["clinical_practicum_course_ids"]})),
            )
        revision_id=record_import_revision(cursor, contract, importer="import_nursing_family.import_program")
        if revision_id: activate_revision(cursor,revision_id,changed_by="import_nursing_family.import_program")
        connection.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--apply-db", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    audits = load_audits(args.audit_dir)
    records = validate_missing_courses(audits)
    invalid = [record.course_id for record in records if record.validation_status != "validated"]
    held_back = sorted({audit["program_id"] for audit in audits if set(audit["missing_unresolved_course_ids"]) & set(invalid)})
    imported = []
    inserted_courses = 0
    if args.apply_db:
        inserted_courses = apply_database(record for record in records if record.validation_status == "validated")
        for audit in audits:
            if audit["program_id"] not in held_back:
                import_program(audit)
                imported.append(audit["program_id"])
    report = {
        "audited_programs": [audit["program_id"] for audit in audits],
        "validated_missing_courses": [record.course_id for record in records if record.validation_status == "validated"],
        "invalid_courses": invalid, "held_back": held_back, "imported": imported,
        "inserted_courses": inserted_courses,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
