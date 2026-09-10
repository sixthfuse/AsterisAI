"""Governed import adapter for BCIT A700GRCERT Business Administration."""
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
from program_import_contract import (ProgramImportContract, Provenance, activate_revision, approve_payload,
    dry_run_diff, record_import_revision, require_approved_hash, require_import_ready, write_common_contract)

PROGRAM_ID="A700GRCERT"
SOURCE_URL="https://www.bcit.ca/programs/business-administration-graduate-certificate-full-time-a700grcert/"
OUTPUT_DIR=Path("program_extractor_audit/a700grcert_governed")

def _between(text,start,end):
    left=text.find(start); right=text.find(end,left+len(start)) if left>=0 else -1
    return text[left:right if right>=0 else None].strip() if left>=0 else ""

def normalize_audit(raw,db_ids):
    refs=[c for component in raw.components for c in component.courses]
    for ref in refs: ref.reconciliation="existing_database" if ref.course_id in db_ids else "missing_course"
    missing=sorted({r.course_id for r in refs}-db_ids); entrance=raw.entrance_requirements_raw
    unresolved=[k for k,v in (("program_id",raw.program_id),("program_name",raw.program_name),("total_credits",raw.total_credits),("entrance_requirements",entrance),("curriculum",raw.components)) if not v]
    flags=[
      {"code":"BACHELOR_DEGREE","severity":"human_confirmation","classification":"executable","raw":"A recognized bachelor’s degree in any field is required; recognition is institutionally verified."},
      {"code":"NO_PUBLISHED_GPA_THRESHOLD","severity":"preserved_raw","classification":"human/raw","raw":"No admission GPA threshold is stated. GPA calculations are required only within specified international credential-evaluation reports."},
      {"code":"NO_BUSINESS_BACKGROUND_PREREQUISITE","severity":"preserved_raw","classification":"human/raw","raw":"The recognized bachelor’s degree may be in any field; no business prerequisite or foundation course is stated."},
      {"code":"FIRST_QUALIFIED_SELECTION","severity":"human_confirmation","classification":"representable-not-executable","raw":"Applicants meeting all entrance requirements are accepted on a first-qualified basis while space remains."},
      {"code":"INTERNATIONAL_CREDENTIAL_EVALUATION","severity":"human_confirmation","classification":"representable-not-executable","raw":"Specified foreign post-secondary studies require an ICES basic evaluation or potentially another accepted Canadian service, including course-by-course evaluation and GPA calculation."},
      {"code":"RECOMMENDED_WORK_EXPERIENCE","severity":"preserved_raw","classification":"human/raw","raw":"At least two years of progressive work experience is preferred for success, not an entrance requirement."},
      {"code":"COHORT_SEQUENCE","severity":"human_confirmation","classification":"representable-not-executable","raw":"Students proceed through the full-time, two-term program as a cohort."},
      {"code":"NO_ADDITIONAL_APPLICATION_DOCUMENTS","severity":"preserved_raw","classification":"human/raw","raw":"The page requires proof of entrance requirements and PDF transcripts/supporting documents; it does not state a résumé, statement, references, or departmental review."},
      {"code":"TRANSFER_ADVANCED_PLACEMENT","severity":"human_confirmation","classification":"representable-not-executable","raw":"The page directs transfer-credit and advanced-placement questions to advising and describes developing MBA pathways; it states no program-specific PLAR rules."},
      {"code":"PGWP_RESTRICTION","severity":"human_confirmation","classification":"representable-not-executable","raw":"International applicants are eligible, but the program is not PGWP eligible under the stated field-of-study requirement (CIP 52.0201)."}]
    return replace(raw,credential="Graduate Certificate",study_mode="Full-time",school="School of Business + Media",
      campus="Downtown Campus, Vancouver",delivery_method="Blended (on campus and online)",intakes=["September"],
      continuation_requirements_raw="Courses must be passed with a 60% mark. Students proceed through two sequenced terms as a cohort.",
      completion_requirements_raw="Complete all six prescribed graduate-level courses (19.0 credits), including the Business Capstone Project, with each course passed at 60% or higher.",
      international_requirements_raw=_between(entrance,"International applicants","Apply to program"),
      transfer_advanced_placement_plar_raw="Transfer credit and advanced placement inquiries are assessed through program advising; no program-specific PLAR policy is published.",
      costs_supplies_raw="Students require a laptop and stable internet for online classes.",
      application_status_raw=_between(entrance,"To submit your application:","Apply Now"),existing_course_ids=sorted({r.course_id for r in refs}&db_ids),
      missing_course_ids=missing,unresolved_fields=unresolved,review_flags=flags,import_ready=not missing and not unresolved)

def contract_for(audit):
    components=[asdict(c) for c in audit.components]; refs=[asdict(c) for x in audit.components for c in x.courses]
    rules={"admission":[
      {"code":"RECOGNIZED_BACHELOR","semantic":"all","raw":"A recognized bachelor’s degree in any field."},
      {"code":"GRADUATE_ENGLISH","semantic":"threshold","minimum":67,"unit":"PERCENT","raw":"Graduate Studies English proficiency: English Studies 12 (67%) or equivalent."},
      {"code":"FIRST_QUALIFIED","semantic":"human_confirmation","human_confirmation_only":True,"raw":"First-qualified acceptance while space remains."}],
      "international":[
      {"code":"INTERNATIONAL_ELIGIBLE","semantic":"human_confirmation","human_confirmation_only":True,"raw":audit.international_requirements_raw},
      {"code":"CREDENTIAL_EVALUATION","semantic":"human_confirmation","human_confirmation_only":True,"raw":"Specified international credentials require course-by-course evaluation and GPA calculations."},
      {"code":"PGWP_NOT_ELIGIBLE","semantic":"raw_policy","human_confirmation_only":True,"raw":"The program is not PGWP eligible under the stated field-of-study requirement (CIP 52.0201)."}],
      "progression":[
      {"code":"COURSE_PASS","semantic":"threshold","minimum":60,"unit":"PERCENT","raw":"Every course must be passed with a 60% mark."},
      {"code":"COHORT_SEQUENCE","semantic":"human_confirmation","human_confirmation_only":True,"raw":"Full-time cohort sequence: Term 1 precedes Term 2."}],
      "completion":[{"code":"ALL_SIX_COURSES_19_CREDITS","semantic":"all","raw":audit.completion_requirements_raw}],
      "pathway":[{"code":"MBA_ADVANCED_PLACEMENT","semantic":"raw_policy","human_confirmation_only":True,"raw":"MBA pathways and advanced placement are external/in-development; partner-specific grades and decisions apply."}]}
    provenance=Provenance(SOURCE_URL,extracted_at=date.today().isoformat(),last_checked=date.today().isoformat(),provenance_tag=PROGRAM_ID,review_status="needs-human-review",confidence="human-interpreted")
    program={"program_id":PROGRAM_ID,"program_name":"Business Administration","credential":"Graduate Certificate","study_mode":"Full-time","school":audit.school,"campus":audit.campus,"delivery_method":audit.delivery_method,"total_credits":audit.total_credits}
    offering=[{"offering_id":f"{PROGRAM_ID}-SEP","intake":"September","study_mode":"Full-time","campus":audit.campus,"delivery_method":audit.delivery_method,"status":"September 2026 closed; September 2027 opens 2026-10-01"}]
    non_course=[{"type":"recognized_bachelor_degree","field":"any","classification":"executable-with-institutional-verification"},{"type":"international_credential_evaluation","classification":"representable-not-executable"},{"type":"application_documents","required":["proof of entrance requirements","transcripts/supporting documents as PDF"],"classification":"human/raw"}]
    return ProgramImportContract(program,offering,components,refs,rules,non_course,{"eligible":True,"pgwp_eligible":False,"eligibility_or_restrictions_raw":audit.international_requirements_raw},provenance,[])

def write_rules(cursor,contract):
    pid=contract.program["program_id"]
    cursor.execute("DELETE FROM academic_rule_conditions WHERE rule_group_id IN (SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s)",(pid,)); cursor.execute("DELETE FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)",(pid,)); cursor.execute("DELETE FROM academic_rule_sets WHERE program_id=%s",(pid,))
    types={"RECOGNIZED_BACHELOR":"PRIOR_DEGREE","GRADUATE_ENGLISH":"ENGLISH_GRADE","CREDENTIAL_EVALUATION":"INTERNATIONAL_CREDENTIAL_EVALUATION","COURSE_PASS":"PROGRAM_COURSE_GRADE"}; subjects={"GRADUATE_ENGLISH":"ENGLISH_STUDIES_12"}
    for scope,rules in contract.rules.items():
      for order,rule in enumerate(rules,1):
        cursor.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes) VALUES(%s,%s,%s,'Full-time',%s,%s) RETURNING rule_set_id",(pid,scope.upper(),rule["code"],SOURCE_URL,rule.get("raw"))); sid=cursor.fetchone()[0]
        cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND',%s,1) RETURNING rule_group_id",(sid,rule["code"])); gid=cursor.fetchone()[0]
        executable=rule["code"] in {"RECOGNIZED_BACHELOR","GRADUATE_ENGLISH","COURSE_PASS"}
        cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,minimum_value,unit,parameters,description,sort_order) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(gid,types.get(rule["code"],rule["code"]),subjects.get(rule["code"]),rule.get("minimum"),rule.get("unit"),Jsonb({"semantic":rule["semantic"],"executable":executable,"verification":"self_reported" if executable else "human_confirmation"}),rule.get("raw"),order))

def write_course_prerequisites(cursor):
    cursor.execute("DELETE FROM prerequisite_conditions WHERE prerequisite_group_id IN (SELECT prerequisite_group_id FROM prerequisite_groups WHERE course_id IN ('FMGT9260','GLBL9200'))"); cursor.execute("DELETE FROM prerequisite_groups WHERE course_id IN ('FMGT9260','GLBL9200')")
    for course_id,requirements in (("FMGT9260",[("FMGT9152",None)]),("GLBL9200",[("ECON9100",60),("FMGT9152",60),("MKTG9120",60)])):
      cursor.execute("INSERT INTO prerequisite_groups(course_id,group_type) VALUES(%s,'AND') RETURNING prerequisite_group_id",(course_id,)); gid=cursor.fetchone()[0]
      for required,grade in requirements:
        cursor.execute("INSERT INTO prerequisite_conditions(prerequisite_group_id,prerequisite_course_id,minimum_grade,required_program_id,condition_type,parameters,description,notes) VALUES(%s,%s,%s,%s,'COURSE',%s,%s,%s)",(gid,required,grade,PROGRAM_ID,Jsonb({"source":"official_program_matrix"}),f"Complete {required[:4]} {required[4:]}"+(f" with at least {grade}%" if grade else ""),"A700GRCERT-only prerequisite"))

def apply_contract(cursor,contract,audit):
    require_approved_hash(cursor,contract); cursor.execute("INSERT INTO areas_of_study(area_id,area_name,status) VALUES('BUS','Business & Media','Active') ON CONFLICT(area_id) DO NOTHING")
    write_common_contract(cursor,contract,program_overrides={"program_overview":audit.overview_raw,"area_id":"BUS","program_level":"Graduate Certificate","accepts_international_students":True,"last_checked":date.today(),"notes":audit.program_details_raw},rule_adapter=write_rules); write_course_prerequisites(cursor)
    cursor.execute("DELETE FROM progression_requirements WHERE program_id=%s",(PROGRAM_ID,))
    cursor.execute("INSERT INTO progression_requirements(program_id,from_level,to_level,requirement_type,requirement_value,description,source_url,last_checked,notes) VALUES(%s,1,2,'PROGRAM_COURSE_GRADE','60',%s,%s,%s,%s)",(PROGRAM_ID,"Every course must be passed with a 60% mark.",SOURCE_URL,date.today(),"Executable threshold; cohort sequencing remains human-confirmed."))
    cursor.execute("""INSERT INTO program_delivery_facts(program_id,duration_years,terms_per_year,total_credits,intake_months,international_eligibility,authoritative_raw,source_url,last_checked) VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s) ON CONFLICT(program_id) DO UPDATE SET duration_years=EXCLUDED.duration_years,terms_per_year=EXCLUDED.terms_per_year,total_credits=EXCLUDED.total_credits,intake_months=EXCLUDED.intake_months,international_eligibility=EXCLUDED.international_eligibility,authoritative_raw=EXCLUDED.authoritative_raw,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked""",(PROGRAM_ID,Decimal(9)/12,2,Decimal(audit.total_credits),json.dumps(["September"]),"Available; study permit required; not PGWP eligible (CIP 52.0201)",audit.program_details_raw,SOURCE_URL,date.today()))
    cursor.execute("""INSERT INTO program_offerings(offering_id,program_id,study_mode,campus,delivery_method,application_status,source_url,last_checked,notes) VALUES(%s,%s,'Full-time',%s,%s,%s,%s,%s,%s) ON CONFLICT(offering_id) DO UPDATE SET application_status=EXCLUDED.application_status,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes""",(f"{PROGRAM_ID}-SEP",PROGRAM_ID,audit.campus,audit.delivery_method,"September 2026 closed; September 2027 opens 2026-10-01",SOURCE_URL,date.today(),"Annual September intake"))
    revision=record_import_revision(cursor,contract,importer="business_administration_graduate_certificate")
    if revision: activate_revision(cursor,revision,changed_by="business_administration_graduate_certificate",reason="reviewed graduate-business governed import")
    return revision

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output-dir",type=Path,default=OUTPUT_DIR); parser.add_argument("--import-courses",action="store_true"); parser.add_argument("--approve",action="store_true"); parser.add_argument("--apply",action="store_true"); args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    session=build_session(); before=database_course_ids(); soup,_=get_soup(session,SOURCE_URL,.15); raw=parse_program_page(soup,SOURCE_URL,before); records=enrich_missing(soup,SOURCE_URL,raw.missing_course_ids,session,.15); validated=[r for r in records if r.validation_status=="validated"]
    (args.output_dir/"course_gap.json").write_text(json.dumps([asdict(r) for r in records],indent=2,ensure_ascii=False),encoding="utf-8"); imported=apply_database(validated) if args.import_courses else 0
    current=database_course_ids(); audit=normalize_audit(raw,current); write_audit(audit,args.output_dir); contract=contract_for(audit); readiness=require_import_ready(contract)
    with get_connection() as connection,connection.cursor() as cursor:
      diff=dry_run_diff(cursor,contract); (args.output_dir/"dry_run.json").write_text(json.dumps(diff,indent=2,default=str),encoding="utf-8")
      if args.approve: approve_payload(cursor,contract,approved_by="user-authorized A700GRCERT governed review",review_notes="Exact normalized payload reviewed after row-level dry-run; graduate-business human decisions preserved.")
      revision=apply_contract(cursor,contract,audit) if args.apply else None; connection.commit()
    result={"database_courses_before":len(before),"validated_missing_courses":len(validated),"courses_imported":imported,"database_courses_after":len(database_course_ids()),"program_id":PROGRAM_ID,"ready":"GREEN" if readiness.go else "RED","hash":contract.payload_sha256,"diff":diff["summary"],"revision_id":revision}; (args.output_dir/"summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result,indent=2))

if __name__=="__main__": main()
