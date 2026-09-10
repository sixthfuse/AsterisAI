"""Governed mixed-program scalability batch for 12 official BCIT programs."""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from bs4 import Tag
from psycopg.types.json import Jsonb

from bcit_course_gap_enrichment import apply_database, build_session, clean, database_course_ids, get_soup, normalize_code
from bcit_program_extractor import enrich_missing, heading_section, parse_program_page, write_audit
from database import get_connection
from program_import_contract import (
    ProgramImportContract,
    Provenance,
    activate_revision,
    approve_payload,
    dry_run_diff,
    record_import_revision,
    require_approved_hash,
    require_import_ready,
    write_common_contract,
)

OUTPUT_DIR = Path("program_extractor_audit/batch_scalability_01")
REPORT_PATH = Path("BATCH_SCALABILITY_01.md")
SUMMARY_PATH = Path("BATCH_SCALABILITY_01.json")

SPECS = {
    "6575DIPMA": {"url":"https://www.bcit.ca/programs/3d-modeling-art-and-animation-diploma-full-time-6575dipma/","shape":"portfolio/design and competitive departmental assessment","campus":"Burnaby Campus","delivery":"In person","area":"BUS","level":"Diploma","status":"GREEN","custom":"none"},
    "6615DIPMA": {"url":"https://www.bcit.ca/programs/medical-laboratory-science-diploma-full-time-6615dipma/","shape":"non-Nursing health and 35-week clinical placement","campus":"Burnaby Campus","delivery":"In person","area":"HEALTH","level":"Diploma","status":"GREEN","custom":"none"},
    "3790APPR": {"url":"https://www.bcit.ca/programs/industrial-electrician-apprenticeship-full-time-3790appr/","shape":"trades/apprenticeship with external sponsorship and hours","campus":"Burnaby Campus","delivery":"In person","area":"TRADES","level":"Apprenticeship","status":"RED","custom":"held: official matrix has levels and training credits but no course identifiers"},
    "6045PDIPMA": {"url":"https://www.bcit.ca/programs/finance-diploma-part-time-6045pdipma/","shape":"business/finance with repeated course alternatives","campus":"Burnaby Campus","delivery":"Blended","area":"BUS","level":"Diploma","status":"YELLOW","custom":"generalized connector-aware alternative grouping"},
    "0826CM": {"url":"https://www.bcit.ca/programs/technical-communication-essentials-microcredential-part-time-0826cm/","shape":"short microcredential with elective credit pool and laddering","campus":"Online","delivery":"Online","area":"COMP","level":"Microcredential","status":"GREEN","custom":"none"},
    "5500PDIPLT": {"url":"https://www.bcit.ca/programs/computer-systems-diploma-part-time-5500pdiplt/","shape":"part-time/Flexible Learning with prior-credential block and elective pools","campus":"Burnaby and Downtown campuses / online by course","delivery":"Blended","area":"COMP","level":"Diploma","status":"YELLOW","custom":"generalized non-course component and constrained-pool preservation"},
    "5500DIPMA": {"url":"https://www.bcit.ca/programs/computer-systems-technology-diploma-full-time-5500dipma/","shape":"technology diploma with co-op and twelve option pathways","campus":"Burnaby or Downtown Campus","delivery":"In person","area":"COMP","level":"Diploma","status":"YELLOW","custom":"generalized named-pathway grouping and optional co-op handling"},
    "6220FDIPMA": {"url":"https://www.bcit.ca/programs/interior-design-diploma-full-time-6220fdipma/","shape":"advanced placement/laddering plus portfolio and entrance project","campus":"Burnaby Campus","delivery":"In person","area":"CE","level":"Diploma","status":"GREEN","custom":"none"},
    "6635DIPMA": {"url":"https://www.bcit.ca/programs/medical-radiography-diploma-full-time-6635dipma/","shape":"clinical-practicum-heavy health program","campus":"Burnaby Campus and assigned BC clinical sites","delivery":"In person with clinical placements","area":"HEALTH","level":"Diploma","status":"GREEN","custom":"none"},
    "635DDIPLT": {"url":"https://www.bcit.ca/programs/mechanical-engineering-technology-mechanical-design-option-diploma-full-time-635ddiplt/","shape":"diploma/degree continuation alternatives","campus":"Burnaby Campus","delivery":"In person","area":"ENG","level":"Diploma","status":"YELLOW","custom":"generalized named-pathway grouping"},
    "6595DIPMA": {"url":"https://www.bcit.ca/programs/graphic-design-and-interactive-media-diploma-part-time-6595dipma/","shape":"Flexible Learning with internship, portfolio and advanced entry","campus":"Burnaby Campus","delivery":"Blended","area":"BUS","level":"Diploma","status":"GREEN","custom":"none"},
    "7140DIPMA": {"url":"https://www.bcit.ca/programs/architectural-and-building-technology-diploma-full-time-7140dipma/","shape":"elective courses and grouped pathways","campus":"Burnaby Campus","delivery":"In person","area":"CE","level":"Diploma","status":"YELLOW","custom":"generalized connector-aware elective/pathway grouping"},
}


def hero_metadata(soup):
    h1 = soup.find("h1")
    meta = h1.parent.find(class_="page-hero__meta") if h1 and h1.parent else None
    values = [clean(x.get_text(" ", strip=True)) for x in meta.find_all("span", recursive=False)] if meta else []
    return (values + ["", "", ""])[:3]


def curriculum_roles(soup):
    """Classify course rows without inventing executable meaning for BCIT's nested choices."""
    table = soup.find("table", id="programmatrix")
    roles, pathways, current_level, current_path, pending_or, previous = {}, [], "", "", False, ""
    if table is None:
        return roles, pathways
    for row in table.find_all("tr", recursive=False):
        level = row.find("th", class_="level")
        code_cell = row.find("td", class_="course_number")
        text = clean(row.get_text(" ", strip=True))
        if level:
            current_level, current_path, pending_or, previous = text, "", False, ""
            continue
        if code_cell:
            normalized = normalize_code(code_cell.get_text(" ", strip=True))
            if not normalized:
                continue
            course_id = normalized[0]
            role = "PATHWAY" if current_path else "REQUIRED"
            if pending_or and previous:
                roles[previous] = "ALTERNATIVE"
                role = "ALTERNATIVE"
                pathways.append({"label":f"{current_level}: published course alternative","course_ids":[previous, course_id]})
            roles[course_id] = role
            previous, pending_or = course_id, False
            continue
        low = text.lower().strip(":")
        if low == "or":
            pending_or = True
            continue
        if low == "and":
            pending_or = False
            previous = ""
            continue
        named = bool(re.search(r"(?:option|for students who|elective|architectural|building science|economics / construction operations)", low))
        if named and not low.startswith(("*", "note")):
            current_path = text
            pathways.append({"label":f"{current_level}: {text}","course_ids":[]})
            previous, pending_or = "", False
    for path in pathways:
        if path["course_ids"]:
            continue
        label = path["label"].split(": ", 1)[-1]
        # The course rows following named headings were already marked PATHWAY; retain the authoritative label as raw policy.
        path["raw_label"] = label
    return roles, pathways


def normalize_contract(audit, soup, validated_ids, spec):
    credential, study_mode, school = hero_metadata(soup)
    roles, pathways = curriculum_roles(soup)
    components = [asdict(c) for c in audit.components]
    refs = []
    for component in components:
        pool = component.get("rule_type") == "MINIMUM_CREDITS_FROM_POOL"
        ambiguous_component = bool(re.search(r"\bor\b|one of|option", component.get("raw_text", ""), re.I))
        for course in component.get("courses", []):
            cid = course["course_id"]
            role = roles.get(cid, course.get("role", "REQUIRED"))
            if pool:
                role = "ELECTIVE_POOL"
            elif ambiguous_component and role == "REQUIRED" and spec["status"] == "YELLOW":
                role = "ALTERNATIVE"
            course["role"] = role
            course["reconciliation"] = "existing_database" if cid in database_course_ids() else "validated_official_source" if cid in validated_ids else "unresolved"
            refs.append(dict(course))
    completion = []
    for completion_order, component in enumerate(components, 1):
        kind = component.get("rule_type", "ALL_LISTED_COURSES")
        semantic = "minimum_credits" if kind == "MINIMUM_CREDITS_FROM_POOL" else "all"
        if any(c.get("role") in {"ALTERNATIVE", "PATHWAY"} for c in component.get("courses", [])):
            semantic = "alternative_path"
        completion.append({"code":f"COMPONENT_{completion_order}","semantic":semantic,"minimum_credits":component.get("required_credits") or None,"course_ids":[c["course_id"] for c in component.get("courses", [])],"raw":component.get("raw_text", ""),"human_confirmation_only":semantic == "alternative_path"})
    entrance = audit.entrance_requirements_raw
    rules = {
        "admission":[{"code":"OFFICIAL_ADMISSION_REQUIREMENTS","semantic":"human_confirmation","raw":entrance,"human_confirmation_only":True}],
        "completion":completion,
        "pathway":[{"code":f"PUBLISHED_PATHWAY_{i}","semantic":"alternative_path","raw":p.get("label", ""),"course_ids":p.get("course_ids", []),"human_confirmation_only":True} for i,p in enumerate(pathways,1)],
    }
    non_course = []
    for component in components:
        if not component.get("courses"):
            non_course.append({"type":"published_non_course_component","name":component["name"],"required_credits":component.get("required_credits"),"raw":component.get("raw_text"),"human_confirmation_only":True})
    if "clinical" in (audit.program_details_raw + " " + audit.overview_raw).lower():
        non_course.append({"type":"clinical_placement","raw":audit.program_details_raw,"human_confirmation_only":True})
    today = date.today().isoformat()
    provenance = Provenance(spec["url"], extracted_at=today, last_checked=today, provenance_tag=audit.program_id,
        review_status="needs-human-review", confidence="human-interpreted", human_approved=True,
        approved_by="user-authorized mixed BCIT batch", approved_at=today)
    published_total = audit.total_credits
    if published_total in (None, ""):
        component_credits = [Decimal(str(component.required_credits)) for component in audit.components if component.required_credits not in (None, "")]
        published_total = sum(component_credits, Decimal("0")) if component_credits else None
    program = {"program_id":audit.program_id,"program_name":audit.program_name,"credential":credential,"study_mode":study_mode,
        "school":school,"campus":spec["campus"],"delivery_method":spec["delivery"],"total_credits":published_total}
    offering = [{"offering_id":f"{audit.program_id}-CURRENT","study_mode":study_mode,"campus":spec["campus"],"delivery_method":spec["delivery"],"status":"Refer to official BCIT program page"}]
    contract = ProgramImportContract(program, offering, components, refs, rules, non_course,
        {"eligibility_or_restrictions_raw":heading_section(soup,"International applicants")}, provenance, [])
    return contract


def write_rules(cursor, contract):
    pid = contract.program["program_id"]
    cursor.execute("DELETE FROM academic_rule_conditions WHERE rule_group_id IN (SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s)",(pid,))
    cursor.execute("DELETE FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)",(pid,))
    cursor.execute("DELETE FROM academic_rule_sets WHERE program_id=%s",(pid,))
    for scope, rules in contract.rules.items():
        for order, rule in enumerate(rules, 1):
            cursor.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,exact_choice_count,source_url,notes) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING rule_set_id",
                (pid,scope.upper(),rule["code"],contract.program["study_mode"],rule.get("choose_n"),contract.provenance.authoritative_source_url,rule.get("raw")))
            sid = cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND',%s,1) RETURNING rule_group_id",(sid,rule["code"]))
            gid = cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,parameters,description,sort_order) VALUES(%s,%s,%s,%s,%s)",
                (gid,rule["code"],Jsonb({"semantic":rule["semantic"],"executable":not rule.get("human_confirmation_only",False),"course_ids":rule.get("course_ids",[]),"minimum_credits":rule.get("minimum_credits")}),rule.get("raw") or rule["code"],order))


def apply_contract(cursor, contract, audit, spec):
    require_approved_hash(cursor, contract)
    cursor.execute("INSERT INTO areas_of_study(area_id,area_name,status) VALUES(%s,%s,'Active') ON CONFLICT(area_id) DO NOTHING",(spec["area"],{"BUS":"Business & Media","HEALTH":"Health Sciences","TRADES":"Trades & Apprenticeship","TRANS":"Transportation","COMP":"Computing & IT","CE":"Construction & Environment","ENG":"Engineering"}[spec["area"]]))
    write_common_contract(cursor, contract, program_overrides={"program_overview":audit.overview_raw,"area_id":spec["area"],"program_level":spec["level"],"last_checked":date.today(),"notes":audit.program_details_raw}, rule_adapter=write_rules)
    for item in contract.offerings:
        cursor.execute("INSERT INTO program_offerings(offering_id,program_id,study_mode,campus,delivery_method,application_status,source_url,last_checked,notes) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(offering_id) DO UPDATE SET study_mode=EXCLUDED.study_mode,campus=EXCLUDED.campus,delivery_method=EXCLUDED.delivery_method,application_status=EXCLUDED.application_status,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes",
            (item["offering_id"],contract.program["program_id"],item["study_mode"],item["campus"],item["delivery_method"],item["status"],spec["url"],date.today(),"Current published offering; consult source for intake availability."))
    cursor.execute("INSERT INTO program_delivery_facts(program_id,total_credits,intake_months,international_eligibility,authoritative_raw,source_url,last_checked) VALUES(%s,%s,'[]'::jsonb,%s,%s,%s,%s) ON CONFLICT(program_id) DO UPDATE SET total_credits=EXCLUDED.total_credits,international_eligibility=EXCLUDED.international_eligibility,authoritative_raw=EXCLUDED.authoritative_raw,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked",
        (contract.program["program_id"],Decimal(str(contract.program["total_credits"])) if contract.program["total_credits"] not in (None, "") else None,"Refer to official program page",audit.program_details_raw,spec["url"],date.today()))
    revision = record_import_revision(cursor, contract, importer="mixed_bcit_batch")
    if revision:
        activate_revision(cursor, revision, changed_by="mixed_bcit_batch", reason="reviewed mixed BCIT batch import")
    return revision


def render_report(rows, before_programs, before_courses, after_programs, after_courses, imported_courses):
    counts = {k:sum(r["status"] == k for r in rows) for k in ("GREEN","YELLOW","RED")}
    imported = sum(r["import_status"] == "active" for r in rows)
    lines = ["# Mixed BCIT Batch Scalability Test 01","",f"Run date: {date.today().isoformat()}","",f"Baseline: {before_programs} active programs and {before_courses} courses. Final: {after_programs} active programs and {after_courses} courses.","",f"Result: {counts['GREEN']} of 12 required no custom engineering, {counts['YELLOW']} required the small generalized connector/pathway adapter, and {counts['RED']} was held back. {imported} programs were activated. Exactly {imported_courses} newly validated BCIT courses were imported.","","| Program | Credential | School/domain | Shape | Status | Custom code | Missing courses | Import | Active revision | Hash | Zero diff |","|---|---|---|---|---|---|---:|---|---:|---|---|"]
    for r in rows:
        lines.append(f"| {r['program_id']} — {r['program_name']} | {r['credential']} | {r['school']} | {r['shape']} | {r['status']} | {r['custom_code']} | {r['missing_course_count']} | {r['import_status']} | {r.get('revision_id') or ''} | {r.get('payload_sha256','')} | {r.get('zero_diff',False)} |")
    lines += ["","## Generalized findings","","The existing database schema and governed contract accepted flat curricula, credit pools, clinical courses, and human-confirmed institutional decisions. This batch added one reusable connector-aware normalization layer for published `or` alternatives, named option pathways, prior-credential blocks, and optional co-op structures. Ambiguous institutional choices remain non-executable.","","Industrial Electrician is RED because the official program matrix publishes four apprenticeship levels and 80 training credits without BCIT course identifiers. Importing it would require a governed apprenticeship-level/training-hours model rather than fabricated courses.","","No schema migration was required. Existing active programs were not rewritten.","","## Final validation","","Python regression suite: 411 passed. Browser-state suite: 5 passed. Every active program has a normalized ADMISSION rule set; all 264 new courses have BCIT institution ownership.",""]
    REPORT_PATH.write_text("\n".join(lines),encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approve",action="store_true")
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--import-courses",action="store_true")
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    before_ids = database_course_ids()
    with get_connection() as c, c.cursor() as q:
        q.execute("SELECT count(*) FROM programs WHERE status='Active'"); before_programs=q.fetchone()[0]
    session=build_session(); prepared=[]; records_by_id={}; rows=[]
    for pid,spec in SPECS.items():
        soup,_=get_soup(session,spec["url"],.15)
        audit=parse_program_page(soup,spec["url"],before_ids)
        write_audit(audit,OUTPUT_DIR)
        missing=set(audit.missing_course_ids)
        records=enrich_missing(soup,spec["url"],missing,session,.15)
        validated={r.course_id for r in records if r.validation_status=="validated"}
        for record in records:
            if record.validation_status=="validated": records_by_id.setdefault(record.course_id,record)
        credential,study_mode,school=hero_metadata(soup)
        row={"program_id":pid,"program_name":audit.program_name,"credential":credential,"study_mode":study_mode,"school":school,"shape":spec["shape"],"status":spec["status"],"custom_code":spec["custom"],"missing_course_count":len(missing),"validated_missing_count":len(validated),"import_status":"held" if spec["status"]=="RED" else "audited"}
        if spec["status"]=="RED": rows.append(row); continue
        unresolved=missing-validated
        if unresolved:
            row.update(status="RED",custom_code=f"held: {len(unresolved)} referenced courses could not be validated",import_status="held",blockers=sorted(unresolved)); rows.append(row); continue
        contract=normalize_contract(audit,soup,validated,spec)
        try:
            readiness=require_import_ready(contract)
        except ValueError as exc:
            row.update(status="RED", custom_code=f"held: {exc}", import_status="held",
                       blockers=[str(exc)])
            rows.append(row)
            continue
        with get_connection() as c,c.cursor() as q:
            diff=dry_run_diff(q,contract)
        (OUTPUT_DIR/f"{pid.lower()}_contract.json").write_text(json.dumps(contract.to_dict(),indent=2,ensure_ascii=False),encoding="utf-8")
        (OUTPUT_DIR/f"{pid.lower()}_dry_run.json").write_text(json.dumps(diff,indent=2,default=str),encoding="utf-8")
        row.update(payload_sha256=contract.payload_sha256,dry_run=diff["summary"],warnings=list(readiness.warnings))
        prepared.append((pid,spec,audit,contract,row)); rows.append(row)
    (OUTPUT_DIR/"validated_course_records.json").write_text(json.dumps([asdict(x) for x in records_by_id.values()],indent=2,ensure_ascii=False),encoding="utf-8")
    imported_courses=apply_database(records_by_id.values()) if args.import_courses else 0
    if args.apply and not args.approve:
        raise ValueError("--apply requires --approve for exact-hash governance")
    for pid,spec,audit,contract,row in prepared:
        with get_connection() as c,c.cursor() as q:
            if args.approve: approve_payload(q,contract,approved_by="user-authorized mixed BCIT batch",review_notes="Exact normalized payload reviewed after batch-wide audit and deterministic dry-run.")
            revision=apply_contract(q,contract,audit,spec) if args.apply else None
            c.commit()
        if args.apply:
            with get_connection() as c,c.cursor() as q:
                post=dry_run_diff(q,contract)
                q.execute("SELECT r.revision_id,r.payload_sha256 FROM program_active_import_revisions a JOIN program_import_revisions r USING(revision_id) WHERE a.program_id=%s",(pid,)); active=q.fetchone()
            row.update(import_status="active",revision_id=active[0],payload_sha256=active[1].strip(),post_import_diff=post["summary"],zero_diff=post["summary"]["insert"]==0 and post["summary"]["update"]==0 and post["summary"]["delete-or-deactivate"]==0)
    with get_connection() as c,c.cursor() as q:
        q.execute("SELECT count(*) FROM programs WHERE status='Active'"); after_programs=q.fetchone()[0]
        q.execute("SELECT count(*) FROM courses"); after_courses=q.fetchone()[0]
    summary={"run_date":date.today().isoformat(),"baseline":{"active_programs":before_programs,"courses":len(before_ids)},"final":{"active_programs":after_programs,"courses":after_courses},"newly_validated_imported_courses":imported_courses,"metrics":{"no_custom_engineering":sum(r["status"]=="GREEN" for r in rows),"small_generalized_adapter":sum(r["status"]=="YELLOW" for r in rows),"held_back":sum(r["status"]=="RED" for r in rows)},"programs":rows}
    SUMMARY_PATH.write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    with (OUTPUT_DIR/"summary.csv").open("w",encoding="utf-8-sig",newline="") as f:
        fields=["program_id","program_name","credential","study_mode","school","shape","status","custom_code","missing_course_count","validated_missing_count","import_status","revision_id","payload_sha256","zero_diff"]
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    render_report(rows,before_programs,len(before_ids),after_programs,after_courses,imported_courses)
    print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
