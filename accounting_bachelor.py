"""Governed BCIT 8630BACC Bachelor of Accounting ingestion adapter."""
from __future__ import annotations

import argparse, json
from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from psycopg.types.json import Jsonb

from bcit_course_gap_enrichment import apply_database, build_session, database_course_ids, get_soup
from bcit_program_extractor import enrich_missing, parse_program_page, write_audit
from database import get_connection
from program_import_contract import (
    ProgramImportContract, Provenance, activate_revision, approve_payload, dry_run_diff,
    record_import_revision, require_approved_hash, require_import_ready, write_common_contract,
)

PROGRAM_ID = "8630BACC"
SOURCE_URL = "https://www.bcit.ca/programs/accounting-bachelor-of-accounting-full-time-part-time-8630bacc/"
OUTPUT_DIR = Path("program_extractor_audit/8630bacc_governed")


def _between(text, start, end):
    left = text.find(start)
    right = text.find(end, left + len(start)) if left >= 0 else -1
    return text[left:right if right >= 0 else None].strip() if left >= 0 else ""


def normalize_audit(raw, db_ids):
    refs = [course for component in raw.components for course in component.courses]
    for ref in refs:
        ref.reconciliation = "existing_database" if ref.course_id in db_ids else "missing_course"
    missing = sorted({ref.course_id for ref in refs} - db_ids)
    entrance = raw.entrance_requirements_raw
    flags = [
        {"code":"DIPLOMA_LADDERING","classification":"executable","raw":"BCIT Accounting, Finance, or Financial Planning diploma, or an individually assessed equivalent diploma."},
        {"code":"MULTIPLE_ENTRY_PATHWAYS","classification":"executable-with-human-equivalency","raw":"Three named BCIT diploma pathways or an equivalent external diploma; bridging may be required."},
        {"code":"DIPLOMA_GPA_70","classification":"executable","raw":"Minimum diploma GPA of 70%."},
        {"code":"SUBJECT_SEQUENCE_AVERAGES","classification":"schema-extension-needed","raw":"Minimum 65% average in each of five named second-year subject sequences; up to two sequences may be between 62% and 65%."},
        {"code":"PRE_ENTRY_ASSESSMENT","classification":"human/raw","raw":"Department-signed pre-entry assessment is required; information session, interview, bridging, or upgrading may be requested."},
        {"code":"COMPETITIVE_VS_FIRST_QUALIFIED","classification":"representable-not-executable","raw":"Full-time admission is competitive; part-time admission is first-qualified while space remains."},
        {"code":"SEVEN_TECHNICAL_ELECTIVES","classification":"executable","raw":"Complete seven courses from the published Advanced Technical Specialty elective pool."},
        {"code":"GENERAL_EDUCATION_POOLS","classification":"schema-extension-needed","raw":"36 credits: two mandatory LIBS courses plus 6 Social Science/Humanities, 9 Arts/Science, and 15 unspecified credits under the linked policy."},
        {"code":"MODE_SEQUENCE","classification":"representable-not-executable","raw":"Full-time students receive four specialty courses per term; Flexible Learning students register course-by-course."},
        {"code":"MAXIMUM_COMPLETION_TIME","classification":"executable","raw":"Maximum completion time is seven years."},
        {"code":"OPTIONAL_DOMESTIC_WORK_TERMS","classification":"executable","raw":"FMGT 7610 and 7620 are optional and available only to full-time domestic students."},
        {"code":"INTERNATIONAL_RESTRICTION","classification":"executable","raw":"International students may apply but cannot take optional FMGT 7610 or FMGT 7620."},
        {"code":"CPA_ALIGNMENT","classification":"human/raw","raw":"The degree and certain courses lead toward or satisfy prerequisites for CPA PEP; degree completion does not confer CPA certification."},
        {"code":"TRANSFER_PLAR","classification":"human/raw","raw":"External diplomas are individually assessed and bridging may be required; no program-specific transfer-credit limit or PLAR rule is published."},
    ]
    unresolved = [key for key, value in (("program_id", raw.program_id), ("program_name", raw.program_name),
        ("total_credits", raw.total_credits), ("entrance_requirements", entrance), ("curriculum", raw.components)) if not value]
    return replace(raw, credential="Bachelor's Degree", study_mode="Full-time / Part-time (Flexible Learning)",
        school="School of Business + Media", campus="Burnaby Campus", delivery_method="In person",
        intakes=["January", "April", "September"],
        continuation_requirements_raw="Full-time specialty courses are sequenced across Fall and Winter; Flexible Learning is course-by-course. Maximum completion time is seven years.",
        completion_requirements_raw="Complete 60.0 credits: FMGT 8911, seven Advanced Technical Specialty electives, and 36.0 General Education credits. The industry-sponsored-project statement is preserved as published. Optional work terms do not form part of the 60.0-credit academic requirement.",
        international_requirements_raw=_between(entrance, "International applicants", "Apply to program"),
        transfer_advanced_placement_plar_raw="External diplomas are assessed individually for equivalency and may require bridging. No program-specific transfer-credit maximum or PLAR rule is stated.",
        costs_supplies_raw="Students require computer equipment capable of course research, computing, and processing functions.",
        application_status_raw=_between(entrance, "Scheduled intakes", "Entrance requirements"),
        existing_course_ids=sorted({r.course_id for r in refs} & db_ids), missing_course_ids=missing,
        unresolved_fields=unresolved, review_flags=flags, import_ready=not missing and not unresolved)


def contract_for(audit):
    components = [asdict(component) for component in audit.components]
    # Work terms are optional, despite the generic matrix parser's default role.
    for component in components:
        if component["name"].startswith("Optional Work Term"):
            for course in component["courses"]: course["role"] = "OPTIONAL"
    refs = [course for component in components for course in component["courses"]]
    admission = [
        {"code":"DIPLOMA_PATHWAY","semantic":"alternative_path","raw":"BCIT Accounting, Finance, or Financial Planning diploma, or equivalent external diploma assessed individually."},
        {"code":"DIPLOMA_GPA","semantic":"threshold","minimum":70,"unit":"PERCENT","raw":"Minimum diploma GPA 70%."},
        {"code":"ENGLISH","semantic":"threshold","minimum":67,"unit":"PERCENT","raw":"English Studies 12 (67%) or equivalent."},
        {"code":"SUBJECT_SEQUENCE_AVERAGES","semantic":"human_confirmation","human_confirmation_only":True,"raw":"Five second-year subject-sequence averages normally 65%; no more than two may be 62%-65%."},
        {"code":"PRE_ENTRY_ASSESSMENT","semantic":"human_confirmation","human_confirmation_only":True,"raw":"Signed departmental pre-entry assessment and any assigned bridging/upgrading are required."},
    ]
    rules = {"admission":admission,
        "curriculum":[
            {"code":"SEVEN_TECHNICAL_ELECTIVES","semantic":"choose_n","choose_n":7,"raw":"Complete seven courses from the listed Advanced Technical Specialty elective pool."},
            {"code":"GENERAL_EDUCATION_36","semantic":"minimum_credits","minimum":36,"unit":"CREDITS","human_confirmation_only":True,"raw":"36.0 General Education credits under the published category policy."}],
        "progression":[{"code":"MAX_SEVEN_YEARS","semantic":"threshold","maximum":7,"unit":"YEARS","raw":"Maximum completion time is seven years."},
            {"code":"MODE_SEQUENCE","semantic":"raw_policy","human_confirmation_only":True,"raw":audit.continuation_requirements_raw}],
        "completion":[{"code":"COMPLETE_60_CREDITS","semantic":"minimum_credits","minimum":60,"unit":"CREDITS","raw":audit.completion_requirements_raw}],
        "international":[{"code":"INTERNATIONAL_ELIGIBLE","semantic":"human_confirmation","human_confirmation_only":True,"raw":audit.international_requirements_raw},
            {"code":"WORK_TERM_RESTRICTION","semantic":"raw_policy","human_confirmation_only":True,"raw":"FMGT 7610 and FMGT 7620 are unavailable to international students."},
            {"code":"PGWP_ADVISORY","semantic":"raw_policy","human_confirmation_only":True,"raw":"The page says bachelor-degree graduates may apply for a PGWP; IRCC makes the final decision."}],
        "professional":[{"code":"CPA_ALIGNMENT_NOT_CERTIFICATION","semantic":"raw_policy","human_confirmation_only":True,"raw":"Academic preparation/alignment toward CPA PEP is advisory and does not award CPA designation or licensure."}],
        "transfer":[{"code":"INDIVIDUAL_EQUIVALENCY","semantic":"human_confirmation","human_confirmation_only":True,"raw":audit.transfer_advanced_placement_plar_raw}]}
    provenance = Provenance(SOURCE_URL, extracted_at=date.today().isoformat(), last_checked=date.today().isoformat(),
        provenance_tag=PROGRAM_ID, review_status="needs-human-review", confidence="human-interpreted")
    program = {"program_id":PROGRAM_ID,"program_name":"Accounting","credential":"Bachelor's Degree",
        "study_mode":"Full-time / Part-time (Flexible Learning)","school":audit.school,"campus":audit.campus,
        "delivery_method":audit.delivery_method,"total_credits":audit.total_credits}
    offerings = [
        {"offering_id":f"{PROGRAM_ID}-FT-JAN","intake":"January","study_mode":"Full-time","campus":audit.campus,"delivery_method":"In person","status":"Published recurring intake"},
        {"offering_id":f"{PROGRAM_ID}-FT-SEP","intake":"September","study_mode":"Full-time","campus":audit.campus,"delivery_method":"In person","status":"Published recurring intake"},
        {"offering_id":f"{PROGRAM_ID}-PT-JAN","intake":"January","study_mode":"Part-time (Flexible Learning)","campus":audit.campus,"delivery_method":"In person","status":"Published recurring intake"},
        {"offering_id":f"{PROGRAM_ID}-PT-APR","intake":"April","study_mode":"Part-time (Flexible Learning)","campus":audit.campus,"delivery_method":"In person","status":"Published recurring intake"},
        {"offering_id":f"{PROGRAM_ID}-PT-SEP","intake":"September","study_mode":"Part-time (Flexible Learning)","campus":audit.campus,"delivery_method":"In person","status":"Published recurring intake"}]
    non_course = [{"type":"diploma_or_equivalent","classification":"executable-with-human-equivalency"},
        {"type":"pre_entry_assessment","classification":"human/raw"},
        {"type":"computer_access","classification":"human/raw"}]
    return ProgramImportContract(program, offerings, components, refs, rules, non_course,
        {"eligible":True,"restrictions":["optional work terms unavailable"]}, provenance, [])


def write_rules(cursor, contract):
    pid = contract.program["program_id"]
    cursor.execute("DELETE FROM academic_rule_conditions WHERE rule_group_id IN (SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s)",(pid,))
    cursor.execute("DELETE FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)",(pid,))
    cursor.execute("DELETE FROM academic_rule_sets WHERE program_id=%s",(pid,))
    types={"DIPLOMA_PATHWAY":"PRIOR_DIPLOMA","DIPLOMA_GPA":"GPA","ENGLISH":"ENGLISH_GRADE","SEVEN_TECHNICAL_ELECTIVES":"COURSE_CHOICE_COUNT","GENERAL_EDUCATION_36":"CREDITS","MAX_SEVEN_YEARS":"MAXIMUM_DURATION","COMPLETE_60_CREDITS":"CREDITS"}
    for scope, rules in contract.rules.items():
        for order, rule in enumerate(rules,1):
            cursor.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,exact_choice_count,source_url,notes) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING rule_set_id",(pid,scope.upper(),rule["code"],contract.program["study_mode"],rule.get("choose_n"),SOURCE_URL,rule.get("raw"))); sid=cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND',%s,1) RETURNING rule_group_id",(sid,rule["code"])); gid=cursor.fetchone()[0]
            executable=rule["code"] in {"DIPLOMA_PATHWAY","DIPLOMA_GPA","ENGLISH","SEVEN_TECHNICAL_ELECTIVES","MAX_SEVEN_YEARS","COMPLETE_60_CREDITS"}
            cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,minimum_value,unit,parameters,description,sort_order) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(gid,types.get(rule["code"],rule["code"]),"ENGLISH_STUDIES_12" if rule["code"]=="ENGLISH" else None,rule.get("minimum") or rule.get("maximum"),rule.get("unit"),Jsonb({"semantic":rule["semantic"],"executable":executable,"human_confirmation_only":rule.get("human_confirmation_only",False)}),rule.get("raw"),order))


def apply_contract(cursor, contract, audit):
    require_approved_hash(cursor, contract)
    cursor.execute("INSERT INTO areas_of_study(area_id,area_name,status) VALUES('BUS','Business & Media','Active') ON CONFLICT(area_id) DO NOTHING")
    write_common_contract(cursor, contract, program_overrides={"program_overview":audit.overview_raw,"area_id":"BUS","program_level":"Bachelor's Degree","accepts_international_students":True,"last_checked":date.today(),"notes":audit.program_details_raw}, rule_adapter=write_rules)
    for offering in contract.offerings:
        cursor.execute("""INSERT INTO program_offerings(offering_id,program_id,study_mode,campus,delivery_method,application_status,source_url,last_checked,notes)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(offering_id) DO UPDATE SET
            study_mode=EXCLUDED.study_mode,campus=EXCLUDED.campus,delivery_method=EXCLUDED.delivery_method,
            application_status=EXCLUDED.application_status,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes""",
            (offering["offering_id"],PROGRAM_ID,offering["study_mode"],offering["campus"],offering["delivery_method"],
             offering["status"],SOURCE_URL,date.today(),offering["intake"]))
    cursor.executemany("""INSERT INTO program_advisor_aliases(normalized_alias,program_id,priority) VALUES(%s,%s,5)
        ON CONFLICT(normalized_alias) DO UPDATE SET program_id=EXCLUDED.program_id,alias_scope='program',family_key=NULL,priority=EXCLUDED.priority,active=TRUE""",
        [(alias,PROGRAM_ID) for alias in ("bachelor of accounting","accounting degree","bcit accounting bachelor","bacc")])
    cursor.executemany("""INSERT INTO program_relationships(program_id,relationship_type,relationship_key,independent_program) VALUES(%s,'member_of',%s,TRUE)
        ON CONFLICT(program_id,relationship_type,relationship_key) DO UPDATE SET independent_program=TRUE,active=TRUE""",
        [(PROGRAM_ID,"bachelor_degree"),(PROGRAM_ID,"business_accounting")])
    # Only the unambiguous accounting-specific chain is executable here. More
    # complex OR/average prerequisites remain authoritative raw course text.
    cursor.execute("DELETE FROM prerequisite_conditions WHERE prerequisite_group_id IN (SELECT prerequisite_group_id FROM prerequisite_groups WHERE course_id='FMGT7620')")
    cursor.execute("DELETE FROM prerequisite_groups WHERE course_id='FMGT7620'")
    cursor.execute("INSERT INTO prerequisite_groups(course_id,group_type) VALUES('FMGT7620','AND') RETURNING prerequisite_group_id"); gid=cursor.fetchone()[0]
    cursor.execute("""INSERT INTO prerequisite_conditions(prerequisite_group_id,prerequisite_course_id,required_program_id,condition_type,parameters,description,notes)
        VALUES(%s,'FMGT7610',%s,'COURSE',%s,'Complete FMGT 7610','8630BACC optional work-term sequence')""",
        (gid,PROGRAM_ID,Jsonb({"source":"official_course_page","executable":True})))
    cursor.execute("DELETE FROM progression_requirements WHERE program_id=%s",(PROGRAM_ID,))
    cursor.execute("INSERT INTO progression_requirements(program_id,from_level,to_level,requirement_type,requirement_value,description,source_url,last_checked,notes) VALUES(%s,1,2,'MAXIMUM_DURATION','7 years',%s,%s,%s,%s)",(PROGRAM_ID,audit.continuation_requirements_raw,SOURCE_URL,date.today(),"Mode sequencing remains human-confirmed."))
    cursor.execute("""INSERT INTO program_delivery_facts(program_id,duration_years,terms_per_year,total_credits,intake_months,international_eligibility,authoritative_raw,source_url,last_checked) VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s) ON CONFLICT(program_id) DO UPDATE SET duration_years=EXCLUDED.duration_years,terms_per_year=EXCLUDED.terms_per_year,total_credits=EXCLUDED.total_credits,intake_months=EXCLUDED.intake_months,international_eligibility=EXCLUDED.international_eligibility,authoritative_raw=EXCLUDED.authoritative_raw,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked""",(PROGRAM_ID,Decimal(2),2,Decimal("60.0"),json.dumps(["January","April","September"]),"Eligible; study permit required; optional work terms unavailable",audit.program_details_raw,SOURCE_URL,date.today()))
    revision=record_import_revision(cursor,contract,importer="accounting_bachelor")
    if revision: activate_revision(cursor,revision,changed_by="accounting_bachelor",reason="reviewed accounting-degree governed import")
    return revision


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output-dir",type=Path,default=OUTPUT_DIR); parser.add_argument("--import-courses",action="store_true"); parser.add_argument("--approve",action="store_true"); parser.add_argument("--apply",action="store_true"); args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    session=build_session(); before=database_course_ids(); soup,_=get_soup(session,SOURCE_URL,.15); raw=parse_program_page(soup,SOURCE_URL,before)
    records=enrich_missing(soup,SOURCE_URL,raw.missing_course_ids,session,.15); validated=[r for r in records if r.validation_status=="validated"]
    (args.output_dir/"course_gap.json").write_text(json.dumps([asdict(r) for r in records],indent=2,ensure_ascii=False),encoding="utf-8")
    imported=apply_database(validated) if args.import_courses else 0; current=database_course_ids(); audit=normalize_audit(raw,current); write_audit(audit,args.output_dir)
    contract=contract_for(audit); readiness=require_import_ready(contract)
    (args.output_dir/"normalized_contract.json").write_text(json.dumps(contract.to_dict(),indent=2,ensure_ascii=False),encoding="utf-8")
    with get_connection() as connection, connection.cursor() as cursor:
        diff=dry_run_diff(cursor,contract); (args.output_dir/"dry_run.json").write_text(json.dumps(diff,indent=2,default=str),encoding="utf-8")
        if args.approve: approve_payload(cursor,contract,approved_by="user-authorized 8630BACC governed review",review_notes="Exact normalized payload reviewed after row-level dry-run; accounting-specific human decisions preserved.")
        revision=apply_contract(cursor,contract,audit) if args.apply else None; connection.commit()
    result={"database_courses_before":len(before),"validated_missing_courses":len(validated),"courses_imported":imported,"database_courses_after":len(database_course_ids()),"program_id":PROGRAM_ID,"ready":"GREEN" if readiness.go else "RED","hash":contract.payload_sha256,"diff":diff["summary"],"revision_id":revision}
    (args.output_dir/"summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
