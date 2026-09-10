"""Governed batch audit and import for BCIT's independent AME E/M/S diplomas."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from bcit_course_gap_enrichment import apply_database, build_session, database_course_ids, get_soup
from bcit_program_extractor import enrich_missing, parse_program_page, write_audit
from database import get_connection
from program_import_contract import (
    ProgramImportContract, Provenance, activate_revision, approve_payload, dry_run_diff,
    record_import_revision, require_approved_hash, require_import_ready, write_common_contract,
)

PROGRAMS = {
    "1165DIPMA": {
        "url": "https://www.bcit.ca/programs/aircraft-maintenance-engineer-category-e-electronics-diploma-full-time-1165dipma/",
        "name": "Aircraft Maintenance Engineer Category ‘E’ (Electronics)", "specialty": "E", "weeks": 68,
        "intakes": ["January", "August"], "practical_share": 50, "experience_credit": "18 months of the 48 months required toward an AME-E licence",
    },
    "1230DIPMA": {
        "url": "https://www.bcit.ca/programs/aircraft-maintenance-engineer-category-m-maintenance-diploma-full-time-1230dipma/",
        "name": "Aircraft Maintenance Engineer Category 'M' (Maintenance)", "specialty": "M", "weeks": 64,
        "intakes": ["January", "May", "August/September"], "practical_share": 50, "experience_credit": "18 months of the 48 months required toward an AME-M licence",
    },
    "1205DIPMA": {
        "url": "https://www.bcit.ca/programs/aircraft-maintenance-engineer-category-s-structures-diploma-full-time-1205dipma/",
        "name": "Aircraft Maintenance Engineer Category 'S' (Structures)", "specialty": "S", "weeks": 40,
        "intakes": ["September"], "practical_share": 60, "experience_credit": "12 months of the 36 months required toward an AME-S licence; technical-exam exemption is conditional on Transport Canada accreditation requirements",
    },
}


def _international(text):
    start = text.find("International applicants")
    end = text.find("Apply to program", start)
    return text[start:end].strip() if start >= 0 else ""


def normalize_audit(raw, spec, db_ids):
    """Correct generic metadata and classify only semantics stated by this AME page."""
    refs = [course for component in raw.components for course in component.courses]
    for ref in refs:
        ref.reconciliation = "existing_database" if ref.course_id in db_ids else "missing_course"
    missing = sorted({r.course_id for r in refs} - db_ids)
    unresolved = [key for key, value in (("program_id", raw.program_id), ("program_name", spec["name"]),
                  ("total_credits", raw.total_credits), ("entrance_requirements", raw.entrance_requirements_raw),
                  ("curriculum", raw.components)) if not value]
    flags = [
        {"code":"REGULATOR_APPROVAL", "severity":"human_confirmation", "classification":"representable-not-executable",
         "raw":"Program is approved by Transport Canada; licensing/accreditation remains an external-authority decision."},
        {"code":"PRACTICAL_SHOP_COMPONENT", "severity":"human_confirmation", "classification":"representable-not-executable",
         "raw":f"Approximately {spec['practical_share']}% of instruction is hands-on practical training; no authoritative shop-hour total is stated."},
        {"code":"ATTENDANCE_ACCREDITATION", "severity":"human_confirmation", "classification":"supported/executable",
         "raw":"Transport Canada permits at most 5% absence for specified circumstances; excess lost theory, workshop and laboratory time must be made up through documented supplementary studies for accreditation credit."},
        {"code":"LICENSING_EXPERIENCE_CREDIT", "severity":"human_confirmation", "classification":"representable-not-executable", "raw":spec["experience_credit"]},
        {"code":"EMPLOYER_SPONSOR_STATUS", "severity":"preserved_raw", "classification":"authoritative raw/human-confirmation", "raw":"No employer or sponsor prerequisite is stated on the official program page."},
        {"code":"TECHNICAL_TRAINING_BLOCKS", "severity":"preserved_raw", "classification":"authoritative raw/human-confirmation", "raw":"No apprenticeship technical-training blocks are stated on the official program page."},
        {"code":"PLAR_TRANSFER_ADVANCED_PLACEMENT", "severity":"preserved_raw", "classification":"authoritative raw/human-confirmation", "raw":"No PLAR, transfer, or advanced-placement policy is stated on the official program page."},
    ]
    return replace(raw, program_name=spec["name"], credential="Diploma", study_mode="Full-time",
        school="School of Transportation", campus="Aerospace Technology Campus, Richmond",
        delivery_method="In person", intakes=spec["intakes"], completion_requirements_raw="",
        international_requirements_raw=_international(raw.entrance_requirements_raw),
        existing_course_ids=sorted(set(raw.discovered_course_ids) & db_ids), missing_course_ids=missing,
        unresolved_fields=unresolved, review_flags=flags, import_ready=not missing and not unresolved)


def contract_for(audit, spec):
    components = [asdict(c) for c in audit.components]
    refs = [asdict(c) for comp in audit.components for c in comp.courses]
    source = audit.source_url
    admission = [
        {"code":"ENGLISH_CURRENT", "semantic":"threshold", "minimum":50, "unit":"PERCENT", "raw":audit.entrance_requirements_raw},
        {"code":"MATH", "semantic":"threshold", "minimum":60, "unit":"PERCENT", "raw":"One of Pre-Calculus 11, Foundations of Math 11, Workplace Math 11, accepted equivalent, or BCIT Math Trades Entry Assessment."},
    ]
    if audit.program_id in {"1165DIPMA","1230DIPMA"}:
        admission.append({"code":"ENGLISH_AFTER_2026_09_30", "semantic":"threshold", "minimum":67, "unit":"PERCENT", "raw":"Applications after September 30, 2026 require Category 2 English (67%)."})
    if audit.program_id == "1230DIPMA":
        admission.append({"code":"MECHANICAL_REASONING_TRANSITION", "semantic":"raw_policy", "human_confirmation_only":True, "raw":"Mechanical Reasoning Trades Entry Assessment is no longer required for January 2027 and later intakes."})
    rules = {
        "admission": admission,
        "progression": [
            {"code":"THEORY_PASS", "semantic":"threshold", "minimum":70, "unit":"PERCENT", "raw":"Theory component must be passed with 70%."},
            {"code":"PRACTICAL_PASS", "semantic":"threshold", "minimum":70, "unit":"PERCENT", "raw":"Practical component must be passed independently with 70%."},
            {"code":"SECOND_FAILURE_READMISSION", "semantic":"human_confirmation", "human_confirmation_only":True, "raw":"After an unsuccessful second attempt, Associate Dean approval is required for readmission/continuation."},
        ],
        "attendance": [{"code":"TC_ATTENDANCE", "semantic":"threshold", "minimum":95, "unit":"PERCENT", "raw":"At least 95% attendance, or documented make-up of lost theory, workshop and laboratory time, is required for Transport Canada course approval/accreditation credit."}],
        "regulatory": [
            {"code":"TC_APPROVED_PROGRAM", "semantic":"human_confirmation", "human_confirmation_only":True, "raw":"Program is approved by Transport Canada; BCIT completion does not itself grant an AME licence."},
            {"code":"TC_EXPERIENCE_CREDIT", "semantic":"human_confirmation", "human_confirmation_only":True, "raw":spec["experience_credit"]},
        ],
        "completion": [{"code":"ALL_TERM_COURSES", "semantic":"all", "raw":"Complete all listed term courses and meet BCIT credential requirements."}],
    }
    provenance = Provenance(source, extracted_at=date.today().isoformat(), last_checked=date.today().isoformat(),
        provenance_tag=audit.program_id, review_status="needs-human-review", confidence="human-interpreted")
    program = {"program_id":audit.program_id,"program_name":audit.program_name,"credential":audit.credential,
        "study_mode":audit.study_mode,"school":audit.school,"campus":audit.campus,"delivery_method":audit.delivery_method,
        "total_credits":audit.total_credits}
    offerings = [{"offering_id":f"{audit.program_id}-{x.lower().replace('/','-')}", "intake":x,
                  "study_mode":"Full-time","campus":audit.campus,"delivery_method":"In person","status":"published"}
                 for x in audit.intakes]
    non_course = [{"type":"practical_shop", "approximate_instruction_percent":spec["practical_share"], "hours":None,
                   "classification":"representable-not-executable"},
                  {"type":"external_regulator", "authority":"Transport Canada", "classification":"representable-not-executable"}]
    return ProgramImportContract(program, offerings, components, refs, rules, non_course,
        {"eligible":True,"eligibility_or_restrictions_raw":audit.international_requirements_raw}, provenance, [])


def write_rules(cursor, contract):
    from psycopg.types.json import Jsonb
    pid = contract.program["program_id"]
    cursor.execute("DELETE FROM academic_rule_conditions WHERE rule_group_id IN (SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s)",(pid,))
    cursor.execute("DELETE FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)",(pid,))
    cursor.execute("DELETE FROM academic_rule_sets WHERE program_id=%s",(pid,))
    for scope, rules in contract.rules.items():
        for order, rule in enumerate(rules,1):
            cursor.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes) VALUES(%s,%s,%s,'Full-time',%s,%s) RETURNING rule_set_id",
                (pid,scope.upper(),rule["code"],contract.provenance.authoritative_source_url,rule.get("raw"))); sid=cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND',%s,1) RETURNING rule_group_id",(sid,rule["code"])); gid=cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,minimum_value,unit,parameters,description,sort_order) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (gid,rule["code"],rule.get("minimum"),rule.get("unit"),Jsonb({"semantic":rule["semantic"],"executable":rule["semantic"]=="threshold","human_confirmation":rule.get("human_confirmation_only",False)}),rule.get("raw"),order))


def apply_contract(cursor, contract, audit, spec):
    require_approved_hash(cursor, contract)
    cursor.execute("INSERT INTO areas_of_study(area_id,area_name,status) VALUES('TRADES','Trades & Apprenticeships','Active') ON CONFLICT(area_id) DO NOTHING")
    write_common_contract(cursor, contract, program_overrides={"program_overview":audit.overview_raw,"area_id":"TRADES",
        "program_level":"Diploma","accepts_international_students":True,"last_checked":date.today(),"notes":audit.program_details_raw}, rule_adapter=write_rules)
    cursor.execute("""INSERT INTO program_delivery_facts(program_id,duration_years,terms_per_year,total_credits,intake_months,international_eligibility,authoritative_raw,source_url,last_checked)
        VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s) ON CONFLICT(program_id) DO UPDATE SET duration_years=EXCLUDED.duration_years,terms_per_year=EXCLUDED.terms_per_year,total_credits=EXCLUDED.total_credits,intake_months=EXCLUDED.intake_months,international_eligibility=EXCLUDED.international_eligibility,authoritative_raw=EXCLUDED.authoritative_raw,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked""",
        (audit.program_id,Decimal(spec["weeks"])/52,len(audit.components),Decimal(audit.total_credits),json.dumps(audit.intakes),"Available to international applicants",audit.program_details_raw,audit.source_url,date.today()))
    for item in contract.offerings:
        cursor.execute("""INSERT INTO program_offerings(offering_id,program_id,study_mode,campus,delivery_method,application_status,source_url,last_checked,notes)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(offering_id) DO UPDATE SET application_status=EXCLUDED.application_status,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes""",
            (item["offering_id"],audit.program_id,"Full-time",audit.campus,"In person",item["status"],audit.source_url,date.today(),item["intake"]))
    revision=record_import_revision(cursor,contract,importer="aircraft_maintenance_batch")
    if revision: activate_revision(cursor,revision,changed_by="aircraft_maintenance_batch",reason="reviewed AME family governed import")
    return revision


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output-dir",type=Path,default=Path("program_extractor_audit/aircraft_maintenance_governed"))
    parser.add_argument("--import-courses",action="store_true"); parser.add_argument("--approve",action="store_true"); parser.add_argument("--apply",action="store_true"); args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True); session=build_session(); initial_ids=database_course_ids(); prepared=[]; all_records={}
    for pid,spec in PROGRAMS.items():
        soup,_=get_soup(session,spec["url"],.15); raw=parse_program_page(soup,spec["url"],initial_ids)
        for record in enrich_missing(soup,spec["url"],raw.missing_course_ids,session,.15): all_records[record.course_id]=record
        prepared.append((pid,spec,soup,raw))
    validated=[r for r in all_records.values() if r.validation_status=="validated"]
    if args.import_courses: apply_database(validated)
    current_ids=database_course_ids()
    summaries=[]
    with get_connection() as connection, connection.cursor() as cursor:
        for pid,spec,soup,raw in prepared:
            audit=normalize_audit(raw,spec,current_ids); write_audit(audit,args.output_dir); contract=contract_for(audit,spec); readiness=require_import_ready(contract)
            diff=dry_run_diff(cursor,contract); (args.output_dir/f"{pid.lower()}_dry_run.json").write_text(json.dumps(diff,indent=2,default=str),encoding="utf-8")
            if args.approve: approve_payload(cursor,contract,approved_by="user-authorized governed AME family review",review_notes="Exact normalized payload reviewed after deterministic dry-run; non-executable regulator semantics preserved.")
            revision=apply_contract(cursor,contract,audit,spec) if args.apply else None
            summaries.append({"program_id":pid,"ready":"GREEN" if readiness.go else "RED","hash":contract.payload_sha256,"diff":diff["summary"],"revision_id":revision,"courses":len(audit.discovered_course_ids),"missing":audit.missing_course_ids})
        connection.commit()
    result={"database_courses_before":len(initial_ids),"validated_missing_courses":len(validated),"database_courses_after":len(database_course_ids()),"programs":summaries}
    (args.output_dir/"batch_summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result,indent=2))

if __name__ == "__main__": main()
