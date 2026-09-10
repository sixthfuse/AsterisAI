"""Audit, enrich, and import BCIT's main full-time BSN through shared extractors."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path

from bcit_course_gap_enrichment import CourseRecord, apply_database, database_course_ids
from database import get_connection
from program_import_contract import activate_revision, adapt_nursing_audit, record_import_revision, require_approved_hash, require_import_ready

PROGRAM_ID = "8875BSN"
SOURCE = "https://www.bcit.ca/programs/nursing-bachelor-of-science-in-nursing-full-time-8875bsn/"


def records_from_audit(audit):
    """Create validated gap records from authoritative matrix rows.

    The program matrix is the official source for name, credits, overview and
    prerequisite text. This feeds the existing controlled course insert path.
    """
    existing = database_course_ids()
    records = []
    for ref in audit["course_references"]:
        if ref["course_id"] in existing:
            continue
        valid = bool(ref["course_name"] and ref["credits"] != "" and ref["course_url"])
        records.append(CourseRecord(
            ref["course_id"], ref["display_course_code"], ref["course_name"],
            ref["credits"], ref.get("course_overview_raw") or
            next(c["raw_text"] for c in audit["curriculum_components"] if c["name"] == ref["component_name"]),
            ref.get("prerequisite_raw") or "No prerequisite text stated in the program matrix.",
            "authoritative_raw_text" if ref.get("prerequisite_raw") else "unknown",
            ref["course_url"], "Active", "Status not stated", f'{ref["display_course_code"]} {ref["course_name"]}',
            "Nursing", SOURCE, "program_matrix_gap_enrichment", 200,
            "validated" if valid else "needs_review", "" if valid else "matrix row missing name, credits, or official outline URL",
        ))
    return records


def _insert_rule(cursor, scope, name, notes):
    cursor.execute("""INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes)
        VALUES(%s,%s,%s,'FULL_TIME',%s,%s) RETURNING rule_set_id""", (PROGRAM_ID, scope, name, SOURCE, notes))
    return cursor.fetchone()[0]


def import_program(audit):
    contract = adapt_nursing_audit(audit, main_bsn=True)
    require_import_ready(contract)
    sections = audit["authoritative_sections"]
    requirements = audit["structured_requirement_text"]
    overview = sections["overview"]
    admissions = sections["admissions"]
    details = sections["program_details"]
    with get_connection() as connection, connection.cursor() as cursor:
        require_approved_hash(cursor, contract)
        cursor.execute("""INSERT INTO programs(program_id,program_name,program_overview,area_id,school,credential,
            program_level,study_mode,accepts_international_students,campus,delivery_method,status,source_url,last_checked,notes)
            VALUES(%s,%s,%s,'A05',%s,%s,'Bachelor''s Degree','Full-time',FALSE,%s,%s,'Active',%s,CURRENT_DATE,%s)
            ON CONFLICT(program_id) DO UPDATE SET program_name=EXCLUDED.program_name,program_overview=EXCLUDED.program_overview,
            school=EXCLUDED.school,credential=EXCLUDED.credential,study_mode=EXCLUDED.study_mode,
            accepts_international_students=FALSE,campus=EXCLUDED.campus,delivery_method=EXCLUDED.delivery_method,
            status='Active',source_url=EXCLUDED.source_url,last_checked=CURRENT_DATE,notes=EXCLUDED.notes""",
            (PROGRAM_ID,audit["official_name"],overview,audit["school_area"],audit["credential"],audit["campus"],audit["delivery"],SOURCE,
             "Main/regular accelerated BSN; distinct from the 12 part-time Specialty Nursing programs. Three years, three terms per year."))
        cursor.execute("DELETE FROM curriculum_component_courses WHERE component_id IN (SELECT component_id FROM curriculum_components WHERE program_id=%s)",(PROGRAM_ID,))
        cursor.execute("DELETE FROM curriculum_components WHERE program_id=%s",(PROGRAM_ID,))
        cursor.execute("DELETE FROM program_courses WHERE program_id=%s",(PROGRAM_ID,))
        for component in audit["curriculum_components"]:
            cursor.execute("""INSERT INTO curriculum_components(program_id,component_name,component_order,required_credits,notes)
                VALUES(%s,%s,%s,%s,%s) RETURNING component_id""",(PROGRAM_ID,component["name"],component["order"],component.get("required_credits") or None,component["raw_text"]))
            component_id=cursor.fetchone()[0]
            term_match = __import__('re').search(r'Term\s+(\d+)', component["name"], __import__('re').I)
            term=int(term_match.group(1)) if term_match else None
            year=math.ceil(term/3) if term else None
            for course in component["courses"]:
                clinical=course["course_id"] in audit["clinical_practicum_course_ids"]
                cursor.execute("INSERT INTO curriculum_component_courses(component_id,course_id,course_role,study_mode) VALUES(%s,%s,%s,'FULL_TIME')",(component_id,course["course_id"],course["role"]))
                cursor.execute("""INSERT INTO program_courses(program_id,course_id,course_type,required,level,term,notes)
                    VALUES(%s,%s,%s,TRUE,%s,%s,%s) ON CONFLICT(program_id,course_id) DO UPDATE SET
                    course_type=EXCLUDED.course_type,required=TRUE,level=EXCLUDED.level,term=EXCLUDED.term,notes=EXCLUDED.notes""",
                    (PROGRAM_ID,course["course_id"],"CLINICAL" if clinical else "REQUIRED",year,term,component["name"]))
        cursor.execute("DELETE FROM academic_rule_conditions WHERE rule_group_id IN (SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s)",(PROGRAM_ID,))
        cursor.execute("DELETE FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)",(PROGRAM_ID,))
        cursor.execute("DELETE FROM academic_rule_sets WHERE program_id=%s",(PROGRAM_ID,))
        admission_id=_insert_rule(cursor,"ADMISSION","Competitive three-step BSN admission",admissions)
        cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND','Step 1 minimum requirements and competitive assessment',1) RETURNING rule_group_id",(admission_id,)); group=cursor.fetchone()[0]
        conditions=[("GRADE","ENGLISH_STUDIES_12",67,"PERCENT",True,"English Category 2: English Studies 12 at 67% or equivalent"),("GRADE","CHEMISTRY_11",73,"PERCENT",True,"Chemistry 11 at 73% or equivalent"),("CREDITS","ACADEMIC_FOUNDATIONS",18,"CREDITS",True,"18 post-secondary Academic Foundations credits, minimum 67% in each"),("DOCUMENT","MANDATORY_APPLICANT_QUESTIONNAIRE",None,None,False,"Mandatory Applicant Questionnaire used in competitive selection"),("ASSESSMENT","DEPARTMENT_COMPETITIVE_RANKING",None,None,False,"Department competitive assessment and ranking"),("DOCUMENT","CRIMINAL_RECORD_CHECK",None,None,False,"Required after conditional selection"),("DOCUMENT","IMMUNIZATION_RECORDS",None,None,False,"Required after conditional selection")]
        for order,(kind,subject,minimum,unit,executable,description) in enumerate(conditions,1):
            cursor.execute("""INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,minimum_value,unit,parameters,description,sort_order)
                VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s,%s)""",(group,kind,subject,minimum,unit,json.dumps({"executable":executable,"human_confirmation":not executable}),description,order))
        _insert_rule(cursor,"CONTINUATION","BSN progression and passing standard",details)
        _insert_rule(cursor,"COMPLETION","BSN completion and RN licensure",sections.get("graduating_and_jobs","") or details)
        _insert_rule(cursor,"TRANSFER","Advanced placement, re-admission, and transfer",requirements["advanced_placement_plar_transfer_raw"] or sections.get("advanced_placement", ""))
        _insert_rule(cursor,"INTERNATIONAL","International eligibility", "This program is not available to international students.")
        cursor.execute("DELETE FROM clinical_placement_requirements WHERE program_id=%s",(PROGRAM_ID,))
        clinical=requirements["clinical_practicum_requirements_raw"]
        items=[("CRIMINAL_RECORD_CHECK","Criminal record check","DOCUMENT","PROGRAM_ENTRY"),("IMMUNIZATION_RECORDS","Immunization records","HEALTH_AND_SAFETY","CLINICAL_PLACEMENT"),("INFLUENZA_POLICY","Influenza immunization or masking","HEALTH_AND_SAFETY","CLINICAL_PLACEMENT"),("RESPIRATOR_FIT_TEST","N95 respirator fit testing","HEALTH_AND_SAFETY","CLINICAL_PRACTICUM"),("CPR_BLS_HCP","Current CPR-BLS (HCP), renewed annually","CERTIFICATION","CLINICAL_PRACTICUM")]
        for order,(code,name,kind,applies) in enumerate(items,1): cursor.execute("""INSERT INTO clinical_placement_requirements(program_id,requirement_code,requirement_name,requirement_type,applies_to,executable,verification_method,description,source_url,parameters,sort_order)
            VALUES(%s,%s,%s,%s,%s,FALSE,'HUMAN_CONFIRMATION',%s,%s,'{}',%s)""",(PROGRAM_ID,code,name,kind,applies,clinical,SOURCE,order))
        cursor.execute("""INSERT INTO program_delivery_facts(program_id,duration_years,terms_per_year,total_credits,intake_months,international_eligibility,authoritative_raw,source_url)
            VALUES(%s,3,3,137,'["January","April","September"]','Not available to international students',%s,%s)
            ON CONFLICT(program_id) DO UPDATE SET duration_years=3,terms_per_year=3,total_credits=137,intake_months=EXCLUDED.intake_months,international_eligibility=EXCLUDED.international_eligibility,authoritative_raw=EXCLUDED.authoritative_raw,last_checked=CURRENT_DATE""",(PROGRAM_ID,details,SOURCE))
        revision_id=record_import_revision(cursor, contract, importer="import_main_nursing.import_program")
        if revision_id: activate_revision(cursor,revision_id,changed_by="import_main_nursing.import_program")
        connection.commit()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--audit",type=Path,default=Path("program_extractor_audit/8875bsn/8875bsn_audit.json")); parser.add_argument("--apply-db",action="store_true"); args=parser.parse_args()
    audit=json.loads(args.audit.read_text(encoding="utf-8")); records=records_from_audit(audit); invalid=[r.course_id for r in records if r.validation_status != "validated"]
    if invalid: raise SystemExit(f"Unvalidated course gaps: {invalid}")
    inserted=0
    if args.apply_db: inserted=apply_database(records); import_program(audit)
    print(json.dumps({"program_id":PROGRAM_ID,"gap_courses":[r.course_id for r in records],"validated":len(records),"inserted":inserted,"imported":bool(args.apply_db)},indent=2))

if __name__ == "__main__": main()
