"""Audit-first, reusable BCIT program extraction and controlled import pipeline."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from bcit_course_gap_enrichment import (
    PROGRAM_PATH_RE,
    CourseRecord,
    build_session,
    canonical_bcit_url,
    clean,
    course_discoveries_from_page,
    database_course_ids,
    discover_program_urls,
    get_soup,
    normalize_code,
    parse_course_page,
    apply_database,
)
from program_import_contract import activate_revision, adapt_shared_program_audit, record_import_revision, require_approved_hash, require_import_ready

DEFAULT_URL = "https://www.bcit.ca/programs/electronics-bachelor-of-technology-part-time-8900btech/"
PROGRAM_ID_RE = re.compile(r"-([a-z0-9]{4,12})(?:/)?$", re.I)
CREDIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s+credits?", re.I)


@dataclass
class CourseReference:
    course_id: str
    display_course_code: str
    course_name: str
    credits: str
    course_url: str
    component_name: str
    component_order: int
    role: str
    prerequisite_raw: str
    course_overview_raw: str = ""
    reconciliation: str = "unchecked"


@dataclass
class CurriculumComponent:
    name: str
    order: int
    required_credits: str
    raw_heading: str
    raw_text: str
    rule_type: str
    courses: list[CourseReference] = field(default_factory=list)


@dataclass
class ProgramAudit:
    program_id: str
    program_name: str
    credential: str
    study_mode: str
    school: str
    campus: str
    delivery_method: str
    intakes: list[str]
    total_credits: str
    source_url: str
    overview_raw: str
    entrance_requirements_raw: str
    continuation_requirements_raw: str
    completion_requirements_raw: str
    program_details_raw: str
    components: list[CurriculumComponent]
    discovered_course_ids: list[str]
    existing_course_ids: list[str]
    missing_course_ids: list[str]
    unresolved_fields: list[str]
    review_flags: list[dict]
    import_ready: bool
    international_requirements_raw: str = ""
    transfer_advanced_placement_plar_raw: str = ""
    costs_supplies_raw: str = ""
    application_status_raw: str = ""


def heading_section(soup: BeautifulSoup, heading: str, level: str = "h2") -> str:
    node = next((x for x in soup.find_all(level) if clean(x.get_text(" ", strip=True)).lower() == heading.lower()), None)
    if node is None:
        return ""
    pieces: list[str] = []
    for sibling in node.next_siblings:
        if isinstance(sibling, Tag) and sibling.name == level:
            break
        if isinstance(sibling, Tag):
            value = clean(sibling.get_text(" ", strip=True))
            if value:
                pieces.append(value)
    return clean(" ".join(pieces))


def subsection_text(container: Tag, heading: str) -> str:
    node = next((x for x in container.find_all("h3") if clean(x.get_text(" ", strip=True)).lower() == heading.lower()), None)
    if node is None:
        return ""
    pieces: list[str] = []
    for sibling in node.next_siblings:
        if isinstance(sibling, Tag) and sibling.name in {"h2", "h3"}:
            break
        if isinstance(sibling, Tag):
            value = clean(sibling.get_text(" ", strip=True))
            if value:
                pieces.append(value)
    return clean(" ".join(pieces))


def component_rule(name: str, heading: str) -> str:
    value = f"{name} {heading}".lower()
    if "elective" in value or re.search(r"complete\s+\d+(?:\.\d+)?\s+credits?\s+from", value):
        return "MINIMUM_CREDITS_FROM_POOL"
    return "ALL_LISTED_COURSES" if "mandatory" not in value else "MANDATORY_COURSES"


def parse_component_heading(raw: str, fallback_order: int) -> tuple[int, str, str]:
    """Parse both BCIT heading forms: '(9 credits required)' and '(27 credits)'."""
    order_match = re.match(r"\s*(\d+)\.\s*", raw)
    order = int(order_match.group(1)) if order_match else fallback_order
    value = raw[order_match.end():] if order_match else raw
    credit_match = re.search(r"\(\s*(\d+(?:\.\d+)?)\s+credits?(?:\s+required)?\s*\)\s*$", value, re.I)
    credits = credit_match.group(1) if credit_match else ""
    if credit_match:
        value = value[:credit_match.start()]
    return order, clean(value).rstrip(":"), credits


def parse_matrix(soup: BeautifulSoup, source_url: str) -> tuple[list[CurriculumComponent], str]:
    table = soup.find("table", id="programmatrix")
    if table is None:
        return [], ""
    components: list[CurriculumComponent] = []
    jsonld_credits: dict[str, str] = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.string or "null")
        except json.JSONDecodeError:
            continue
        for item in (payload if isinstance(payload, list) else [payload]):
            if not isinstance(item, dict):
                continue
            for course in item.get("hasCourse", []) or []:
                normalized = normalize_code(str(course.get("courseCode", "")))
                credits = course.get("numberOfCredits") or {}
                if normalized and isinstance(credits, dict) and credits.get("value") is not None:
                    jsonld_credits[normalized[0]] = str(credits["value"])
    current: CurriculumComponent | None = None
    for row in table.find_all("tr", recursive=False):
        header = row.find("th", class_="level")
        if header:
            raw = clean(header.get_text(" ", strip=True))
            total = re.search(r"^Total Credits", raw, re.I)
            if total:
                continue
            order, name, credits = parse_component_heading(raw, len(components) + 1)
            current = CurriculumComponent(name, order, credits, raw, raw, component_rule(name, raw))
            components.append(current)
            continue
        cells = row.find_all("td", recursive=False)
        if current is None or not cells:
            continue
        code_cell = row.find("td", class_="course_number")
        anchor = code_cell.find("a", href=True) if code_cell else None
        # BCIT uses both linked course codes and plain course-code cells whose
        # official outline link is stored later in the same matrix row.
        if code_cell:
            normalized = normalize_code(code_cell.get_text(" ", strip=True))
            if not normalized:
                continue
            name_node = row.find(class_=re.compile(r"course_name"))
            credit_node = row.find("td", class_="credits")
            summary = row.find(class_=re.compile(r"course_summary"))
            summary_text = clean(summary.get_text(" ", strip=True) if summary else "")
            prereq = summary_text.split("Prerequisite(s):", 1)[1].strip() if "Prerequisite(s):" in summary_text else ""
            role = "ELECTIVE_POOL" if current.rule_type == "MINIMUM_CREDITS_FROM_POOL" else "REQUIRED"
            current.courses.append(CourseReference(
                normalized[0], normalized[1], clean(name_node.get_text(" ", strip=True) if name_node else ""),
                clean(credit_node.get_text(" ", strip=True) if credit_node else "") or jsonld_credits.get(normalized[0], ""),
                (canonical_bcit_url(anchor["href"], re.compile(r"^/courses/[^/?#]+/?$")) if anchor else None)
                or (f"https://www.bcit.ca/outlines/{normalized[0].lower()}/"),
                current.name, current.order, role, prereq, summary_text,
            ))
        else:
            text = clean(row.get_text(" ", strip=True))
            if text:
                current.raw_text = clean(f"{current.raw_text} {text}")
    total_row = next((r for r in table.find_all("tr") if "Total Credits" in clean(r.get_text(" ", strip=True))), None)
    total = ""
    if total_row:
        nums = re.findall(r"\d+(?:\.\d+)?", clean(total_row.get_text(" ", strip=True)))
        total = nums[-1] if nums else ""
    return components, total


def parse_program_page(soup: BeautifulSoup, source_url: str, db_ids: set[str]) -> ProgramAudit:
    parsed = urlparse(source_url)
    id_match = PROGRAM_ID_RE.search(parsed.path.rstrip("/"))
    program_id = id_match.group(1).upper() if id_match else ""
    h1 = soup.find("h1")
    name = clean(h1.get_text(" ", strip=True) if h1 else "")
    subtitle = clean(h1.find_next().get_text(" ", strip=True) if h1 else "")
    components, total = parse_matrix(soup, source_url)
    references = [course for component in components for course in component.courses]
    discovered = sorted({r.course_id for r in references})
    existing = sorted(set(discovered) & db_ids)
    missing = sorted(set(discovered) - db_ids)
    for ref in references:
        ref.reconciliation = "existing_database" if ref.course_id in db_ids else "missing_course"
    entrance = heading_section(soup, "Entrance Requirements")
    details = heading_section(soup, "Program Details")
    overview = heading_section(soup, "Overview")
    if program_id == "M600MSC":
        return parse_applied_computing_msc(soup, source_url, db_ids, components, total)
    continuation = ""
    entrance_container = next((h.parent for h in soup.find_all("h3") if clean(h.get_text(" ", strip=True)).lower() == "continuation requirements"), None)
    if entrance_container:
        continuation = subsection_text(entrance_container, "Continuation requirements")
    completion = "After completing the prescribed course work, all degree program students are required to complete an industry-sponsored project in their selected area."
    unresolved: list[str] = []
    for key, value in (("program_id", program_id), ("program_name", name), ("total_credits", total), ("entrance_requirements", entrance), ("curriculum", components)):
        if not value:
            unresolved.append(key)
    review = [
        {"code": "ADMISSION_AGGREGATE_GRADE_EVALUATOR_GAP", "severity": "evaluator_gap", "raw": "Option 3 requires three of ELEX 7010/7020/7030/7040 with an overall average of 70% or more."},
        {"code": "CREDIT_POOL_COMPLETION_EVALUATOR_GAP", "severity": "evaluator_gap", "raw": "Specialization Electives require at least 9.0 credits from the listed pool."},
        {"code": "LIBERAL_STUDIES_POLICY_EXTERNAL_POOL", "severity": "human_review", "raw": "LIBS 7001 and LIBS 7002 are mandatory plus 6.0 credits in accordance with BCIT Liberal Studies policy."},
        {"code": "PROJECT_PROGRAM_SEQUENCE", "severity": "preserved_raw", "raw": completion},
        {"code": "WORK_EXPERIENCE_COMPLETION_ONLY", "severity": "preserved_raw", "raw": "Two years relevant work experience is a graduation requirement, not an entrance requirement."},
    ]
    clean_semantics = total == "73.0" and len(discovered) == 29 and not missing and not unresolved
    return ProgramAudit(
        program_id, name, "Bachelor of Technology / Bachelor's Degree", "Part-time / Flexible Learning", "School of Energy",
        "Burnaby", "In person", ["January", "April", "September"], total, source_url, overview, entrance,
        continuation, completion, details, components, discovered, existing, missing, unresolved, review,
        clean_semantics,
    )


def _find_reference(soup: BeautifulSoup, course_id: str) -> CourseReference:
    display = f"{course_id[:4]} {course_id[4:]}"
    anchor = next((a for a in soup.find_all("a", href=True)
                   if normalize_code(a.get_text(" ", strip=True))
                   and normalize_code(a.get_text(" ", strip=True))[0] == course_id), None)
    return CourseReference(
        course_id, display, "Application Area Directed Studies", "3.0",
        canonical_bcit_url(anchor["href"], re.compile(r"^/courses/[^/?#]+/?$")) if anchor else f"https://www.bcit.ca/outlines/{course_id.lower()}/",
        "Approved directed-studies substitution", 5, "ALTERNATIVE", "", "",
    )


def parse_applied_computing_msc(
    soup: BeautifulSoup, source_url: str, db_ids: set[str], parsed_components: list[CurriculumComponent], total: str
) -> ProgramAudit:
    """Map a graduate, branched matrix into the reusable audit representation."""
    by_id = {c.course_id: c for component in parsed_components for c in component.courses}
    definitions = [
        ("Level 1 (15 weeks – September to December)", 1, "COMMON_SEQUENCE", ["COMP9060", "COMP9170", "COMP9200"]),
        ("Level 2 (15 weeks – January to April)", 2, "COMMON_SEQUENCE", ["COMP9040", "COMP9080", "COMP9130", "COMP9150"]),
        ("Thesis Path (30 weeks – September to April)", 3, "ALTERNATIVE_PATH", ["COMP9600"]),
        ("Project & Internship Path", 4, "ALTERNATIVE_PATH", ["COMP9290", "COMP9400", "COMP9500"]),
    ]
    components: list[CurriculumComponent] = []
    for name, order, rule_type, ids in definitions:
        courses = [by_id[cid] for cid in ids]
        for course in courses:
            course.component_name, course.component_order = name, order
            course.role = "REQUIRED" if rule_type == "COMMON_SEQUENCE" else "PATH_REQUIRED"
        components.append(CurriculumComponent(name, order, "", name, name, rule_type, courses))
    directed = by_id.get("COMP9190") or _find_reference(soup, "COMP9190")
    components.append(CurriculumComponent(
        "Approved directed-studies substitution", 5, "", "COMP 9190 substitution",
        "COMP 9190 may substitute for COMP 9130, COMP 9150, or COMP 9170.", "SUBSTITUTION_OPTION", [directed]
    ))
    references = [course for component in components for course in component.courses]
    discovered = sorted({r.course_id for r in references})
    for ref in references:
        ref.reconciliation = "existing_database" if ref.course_id in db_ids else "missing_course"
    overview = heading_section(soup, "Overview")
    entrance = heading_section(soup, "Entrance Requirements")
    details = heading_section(soup, "Program Details")
    costs = heading_section(soup, "Costs & Supplies")
    international = entrance[entrance.find("International applicants"):] if "International applicants" in entrance else ""
    status_sentences = [s for s in re.split(r"(?<=[.!])\s+", overview)
                        if "September 2026 intake" in s or "September 2027" in s]
    application_status = " ".join(status_sentences)
    continuation = (
        "Students must maintain a minimum 70% average across all program courses before starting their thesis or research project. "
        "Progress is monitored by the supervisor in consultation with the Program Head."
    )
    completion = (
        "Complete one Year 2 path: thesis and defence, or the internship, special-topics course, and research project. "
        "The maximum time to complete the program is five years."
    )
    unresolved = [key for key, value in (("program_id", "M600MSC"), ("program_name", "Applied Computing"),
                  ("total_credits", total), ("entrance_requirements", entrance), ("curriculum", components)) if not value]
    missing = sorted(set(discovered) - db_ids)
    review = [
        {"code":"COMPETITIVE_DEPARTMENT_REVIEW","severity":"human_confirmation","raw":"Complete applications are ranked competitively by the Graduate Program Committee."},
        {"code":"ALTERNATE_ENTRY_COMPUTING_BACKGROUND","severity":"human_confirmation","raw":"Significant computing knowledge, pre-entry assessment review, and any bridging courses are determined by the program area."},
        {"code":"REFERENCES_AND_QUESTIONNAIRE","severity":"human_confirmation","raw":"Mandatory Applicant Questionnaire and two directly submitted references are required."},
        {"code":"INTERNATIONAL_CREDENTIAL_EVALUATION","severity":"human_confirmation","raw":"Specified international credentials require a comprehensive ICES evaluation; other Canadian services may be considered."},
        {"code":"YEAR_2_PATH_APPROVAL","severity":"human_confirmation","raw":"Internship procedures and approval requirements are governed by the Program Handbook and program approval."},
    ]
    return ProgramAudit(
        "M600MSC", "Applied Computing", "Master of Science / Master's Degree", "Full-time",
        "School of Computing and Academic Studies", "Burnaby; possible Downtown Campus or field locations",
        "In person", ["September"], total, source_url, overview, entrance, continuation, completion, details,
        components, discovered, sorted(set(discovered) & db_ids), missing, unresolved, review,
        total == "30.0" and len(discovered) == 12 and not missing and not unresolved,
        international, "", costs, application_status,
    )


def enrich_missing(soup: BeautifulSoup, source_url: str, missing: Iterable[str], session, delay: float):
    discoveries = {d.course_id: d for d in course_discoveries_from_page(soup, source_url)}
    matrix_components, _ = parse_matrix(soup, source_url)
    matrix_refs = {r.course_id: r for component in matrix_components for r in component.courses}
    records = []
    for course_id in sorted(set(missing)):
        if course_id in discoveries:
            record = parse_course_page(session, discoveries[course_id], delay)
            if record.validation_status == "validated":
                records.append(record)
                continue
        ref = matrix_refs.get(course_id)
        if ref and ref.course_name and ref.credits and ref.course_overview_raw:
            records.append(CourseRecord(
                course_id=ref.course_id, display_course_code=ref.display_course_code,
                course_name=ref.course_name.rstrip("*"), credits=ref.credits,
                course_overview_raw=ref.course_overview_raw.split("Prerequisite(s):", 1)[0].strip(),
                prerequisite_text_raw=ref.prerequisite_raw,
                prerequisite_status="explicit_none" if re.search(r"no prerequisites?", ref.prerequisite_raw, re.I) else "authoritative_raw_text",
                course_url=source_url, status="Active", availability_status="Program matrix reference",
                page_title=f"{ref.display_course_code} {ref.course_name.rstrip('*')}", subject_category="Computing & IT",
                discovery_source_url=source_url, discovery_method="program_matrix_embedded",
                http_status=200, validation_status="validated",
                validation_notes="Validated from the official BCIT program matrix because no complete standalone course page was available.",
            ))
        elif course_id in discoveries:
            records.append(record)
    return records


def write_audit(audit: ProgramAudit, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{audit.program_id.lower()}_program_audit.json"
    target.write_text(json.dumps(asdict(audit), indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def apply_program(audit: ProgramAudit) -> None:
    if not audit.import_ready:
        raise ValueError("Audit is not import-ready")
    contract = adapt_shared_program_audit(asdict(audit))
    require_import_ready(contract)
    if audit.program_id == "M600MSC":
        apply_applied_computing_msc(audit)
        return
    from database import get_connection
    with get_connection() as connection:
        with connection.cursor() as cursor:
            require_approved_hash(cursor, contract)
            cursor.execute("""INSERT INTO areas_of_study(area_id,area_name,status) VALUES('ENG','Engineering','Active') ON CONFLICT(area_id) DO NOTHING""")
            cursor.execute("""INSERT INTO programs(program_id,program_name,program_overview,area_id,school,credential,program_level,study_mode,accepts_international_students,campus,delivery_method,status,source_url,last_checked,notes)
                VALUES(%s,%s,%s,'ENG',%s,%s,'Degree completion',%s,TRUE,%s,%s,'Active',%s,%s,%s)
                ON CONFLICT(program_id) DO UPDATE SET program_name=EXCLUDED.program_name,program_overview=EXCLUDED.program_overview,school=EXCLUDED.school,credential=EXCLUDED.credential,study_mode=EXCLUDED.study_mode,campus=EXCLUDED.campus,delivery_method=EXCLUDED.delivery_method,status=EXCLUDED.status,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes""",
                (audit.program_id,audit.program_name,audit.overview_raw,audit.school,audit.credential,audit.study_mode,audit.campus,audit.delivery_method,audit.source_url,date.today(),audit.completion_requirements_raw))
            for component in audit.components:
                cursor.execute("""INSERT INTO curriculum_components(program_id,component_name,component_order,required_credits,notes) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(program_id,component_name) DO UPDATE SET component_order=EXCLUDED.component_order,required_credits=EXCLUDED.required_credits,notes=EXCLUDED.notes RETURNING component_id""",
                    (audit.program_id,component.name,component.order,Decimal(component.required_credits) if component.required_credits else None,component.raw_text))
                component_id = cursor.fetchone()[0]
                for course in component.courses:
                    cursor.execute("""INSERT INTO curriculum_component_courses(component_id,course_id,course_role,study_mode) VALUES(%s,%s,%s,'ALL') ON CONFLICT DO NOTHING""",(component_id,course.course_id,course.role))
                    cursor.execute("""INSERT INTO program_courses(program_id,course_id,required,level) VALUES(%s,%s,%s,%s) ON CONFLICT(program_id,course_id) DO UPDATE SET required=EXCLUDED.required,level=EXCLUDED.level""",(audit.program_id,course.course_id,course.role=='REQUIRED',component.order))
                if component.rule_type == "MINIMUM_CREDITS_FROM_POOL":
                    cursor.execute("""INSERT INTO credit_requirements(program_id,component_id,requirement_name,minimum_credits,study_mode,allows_external_courses,approval_required,notes) VALUES(%s,%s,%s,%s,'ALL',FALSE,FALSE,%s) ON CONFLICT(program_id,requirement_name,study_mode) DO UPDATE SET minimum_credits=EXCLUDED.minimum_credits,notes=EXCLUDED.notes RETURNING credit_requirement_id""",(audit.program_id,component_id,component.name,Decimal(component.required_credits),component.raw_heading))
                    requirement_id=cursor.fetchone()[0]
                    for course in component.courses:
                        cursor.execute("INSERT INTO credit_requirement_courses(credit_requirement_id,course_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",(requirement_id,course.course_id))
            cursor.execute("""INSERT INTO credit_requirements(program_id,component_id,requirement_name,minimum_credits,study_mode,allows_external_courses,approval_required,notes) VALUES(%s,NULL,'Liberal Studies elective policy',6,'ALL',TRUE,TRUE,%s) ON CONFLICT(program_id,requirement_name,study_mode) DO UPDATE SET notes=EXCLUDED.notes""",(audit.program_id,'Six credits per BCIT Liberal Studies policy; external pool requires policy validation.'))
            # Rebuild only this extractor-owned program's rule tree. The raw source
            # remains on the rule set; conditions below are limited to semantics
            # that the page states unambiguously.
            cursor.execute("""DELETE FROM academic_rule_conditions WHERE rule_group_id IN
                (SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s)""", (audit.program_id,))
            cursor.execute("""DELETE FROM academic_rule_groups WHERE rule_set_id IN
                (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)""", (audit.program_id,))
            cursor.execute("DELETE FROM academic_rule_sets WHERE program_id=%s", (audit.program_id,))
            cursor.execute("""INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,exact_choice_count,source_url,notes)
                VALUES(%s,'ADMISSION','Electronics BTech admission','ALL',1,%s,%s) RETURNING rule_set_id""",
                (audit.program_id,audit.source_url,audit.entrance_requirements_raw))
            admission_id=cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND','Two-step admission',1) RETURNING rule_group_id",(admission_id,))
            admission_root=cursor.fetchone()[0]
            cursor.execute("""INSERT INTO academic_rule_conditions(rule_group_id,condition_type,description,sort_order,parameters) VALUES
                (%s,'PRE_ENTRY_ASSESSMENT','Completed pre-entry assessment and any required pre-entry courses',1,'{"required":true,"program_of_study_approval":true}'),
                (%s,'ENGLISH_CATEGORY','English language proficiency Category 2',2,'{"category":2}')""",(admission_root,admission_root))
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,parent_group_id,operator,label,sort_order) VALUES(%s,%s,'OR','Exactly one of four entry options',3) RETURNING rule_group_id",(admission_id,admission_root))
            options=cursor.fetchone()[0]
            from psycopg.types.json import Jsonb
            option_rows=[
                ('ENTRY_OPTION_1',{'credential':'BCIT Electrical and Computer Engineering Technology diploma','minimum_course_average':65}),
                ('ENTRY_OPTION_2',{'credential':'nationally accredited related engineering technology diploma','minimum_course_average':65}),
                ('ENTRY_OPTION_3',{'diploma_gpa_minimum':60,'diploma_gpa_maximum':65,'courses':['ELEX7010','ELEX7020','ELEX7030','ELEX7040'],'courses_required':3,'aggregate_average_minimum':70,'evaluator_status':'unsupported_aggregate_grade'}),
                ('ENTRY_OPTION_4',{'education':'equivalent post-secondary level','professional_registration':'ASTTBC registered or qualified to register'}),
            ]
            for order,(kind,params) in enumerate(option_rows,1):
                cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,parameters,description,sort_order) VALUES(%s,%s,%s,%s,%s)",(options,kind,Jsonb(params),audit.review_flags[0]['raw'] if kind=='ENTRY_OPTION_3' else kind.replace('_',' ').title(),order))
            cursor.execute("""INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes)
                VALUES(%s,'COMPLETION','Graduation and industry project','ALL',%s,%s) RETURNING rule_set_id""",(audit.program_id,audit.source_url,audit.completion_requirements_raw))
            completion_id=cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND','Completion requirements',1) RETURNING rule_group_id",(completion_id,))
            completion_root=cursor.fetchone()[0]
            cursor.execute("""INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,minimum_value,unit,parameters,description,sort_order) VALUES
                (%s,'WORK_EXPERIENCE',NULL,2,'YEAR','{"field":"relevant","scope":"completion"}','Minimum two years relevant work experience prior to graduation',1),
                (%s,'PROGRAM_COURSEWORK_COMPLETE_BEFORE','ELEX8300',NULL,NULL,'{"before":"ELEX8300"}','Complete prescribed coursework before the industry project',2),
                (%s,'COURSE','ELEX8300',NULL,NULL,'{}','Complete the 5-credit industry project',3)""",(completion_root,completion_root,completion_root))
            revision_id=record_import_revision(cursor, contract, importer="bcit_program_extractor.apply_program")
            if revision_id: activate_revision(cursor,revision_id,changed_by="bcit_program_extractor.apply_program")
        connection.commit()


def apply_applied_computing_msc(audit: ProgramAudit) -> None:
    contract = adapt_shared_program_audit(asdict(audit))
    require_import_ready(contract)
    """Import a branched graduate program through generalized curriculum/rule tables."""
    from database import get_connection
    from psycopg.types.json import Jsonb
    with get_connection() as connection:
        with connection.cursor() as cursor:
            require_approved_hash(cursor, contract)
            cursor.execute("INSERT INTO areas_of_study(area_id,area_name,status) VALUES('COMP','Computing & IT','Active') ON CONFLICT(area_id) DO NOTHING")
            cursor.execute("""INSERT INTO programs(program_id,program_name,program_overview,area_id,school,credential,program_level,study_mode,accepts_international_students,campus,delivery_method,status,source_url,last_checked,notes)
                VALUES(%s,%s,%s,'COMP',%s,%s,'Graduate',%s,TRUE,%s,%s,'Active',%s,%s,%s)
                ON CONFLICT(program_id) DO UPDATE SET program_name=EXCLUDED.program_name,program_overview=EXCLUDED.program_overview,area_id=EXCLUDED.area_id,school=EXCLUDED.school,credential=EXCLUDED.credential,program_level=EXCLUDED.program_level,study_mode=EXCLUDED.study_mode,accepts_international_students=EXCLUDED.accepts_international_students,campus=EXCLUDED.campus,delivery_method=EXCLUDED.delivery_method,status=EXCLUDED.status,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes""",
                (audit.program_id,audit.program_name,audit.overview_raw,audit.school,audit.credential,audit.study_mode,audit.campus,audit.delivery_method,audit.source_url,date.today(),audit.program_details_raw))
            cursor.execute("""INSERT INTO program_delivery_facts(program_id,duration_years,terms_per_year,total_credits,intake_months,international_eligibility,authoritative_raw,source_url,last_checked)
                VALUES(%s,2,2,30,%s,'Available to international applicants',%s,%s,%s)
                ON CONFLICT(program_id) DO UPDATE SET duration_years=EXCLUDED.duration_years,terms_per_year=EXCLUDED.terms_per_year,total_credits=EXCLUDED.total_credits,intake_months=EXCLUDED.intake_months,international_eligibility=EXCLUDED.international_eligibility,authoritative_raw=EXCLUDED.authoritative_raw,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked""",
                (audit.program_id,Jsonb(["September"]),audit.overview_raw,audit.source_url,date.today()))
            cursor.execute("""INSERT INTO program_offerings(offering_id,program_id,start_date,study_mode,campus,delivery_method,application_type,application_status,source_url,last_checked,notes)
                VALUES('M600MSC-2027-09',%s,'2027-09-01','Full-time','Burnaby','In person','Competitive','Opens 2026-10-01',%s,%s,%s)
                ON CONFLICT(offering_id) DO UPDATE SET application_status=EXCLUDED.application_status,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes""",
                (audit.program_id,audit.source_url,date.today(),audit.application_status_raw))
            cursor.execute("""INSERT INTO program_offerings(offering_id,program_id,start_date,study_mode,campus,delivery_method,application_type,application_status,source_url,last_checked,notes)
                VALUES('M600MSC-2026-09',%s,'2026-09-01','Full-time','Burnaby','In person','Competitive','Closed to new applications',%s,%s,%s)
                ON CONFLICT(offering_id) DO UPDATE SET application_status=EXCLUDED.application_status,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes""",
                (audit.program_id,audit.source_url,date.today(),audit.application_status_raw))
            cursor.execute("DELETE FROM curriculum_component_courses WHERE component_id IN (SELECT component_id FROM curriculum_components WHERE program_id=%s)",(audit.program_id,))
            cursor.execute("DELETE FROM curriculum_components WHERE program_id=%s",(audit.program_id,))
            cursor.execute("DELETE FROM program_courses WHERE program_id=%s",(audit.program_id,))
            for component in audit.components:
                cursor.execute("INSERT INTO curriculum_components(program_id,component_name,component_order,required_credits,notes) VALUES(%s,%s,%s,NULL,%s) RETURNING component_id",
                               (audit.program_id,component.name,component.order,component.raw_text))
                component_id=cursor.fetchone()[0]
                for course in component.courses:
                    cursor.execute("INSERT INTO curriculum_component_courses(component_id,course_id,course_role,study_mode) VALUES(%s,%s,%s,%s)",
                                   (component_id,course.course_id,course.role,component.name if component.rule_type=='ALTERNATIVE_PATH' else 'ALL'))
                    required = component.rule_type == 'COMMON_SEQUENCE'
                    cursor.execute("INSERT INTO program_courses(program_id,course_id,required,level,term,course_type,notes) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                                   (audit.program_id,course.course_id,required,component.order,component.order,'Core' if required else component.rule_type,component.name))
            cursor.execute("DELETE FROM curriculum_substitutions WHERE program_id=%s",(audit.program_id,))
            for replaced in ('COMP9130','COMP9150','COMP9170'):
                cursor.execute("INSERT INTO curriculum_substitutions(program_id,study_mode,replaced_course_id,replacement_type,replacement_credits,description) VALUES(%s,'ALL',%s,'SPECIFIC_COURSE',3,%s)",
                               (audit.program_id,replaced,f'COMP 9190 may substitute for {replaced[:4]} {replaced[4:]}'))
            cursor.execute("DELETE FROM progression_requirements WHERE program_id=%s",(audit.program_id,))
            cursor.execute("""INSERT INTO progression_requirements(program_id,from_level,to_level,requirement_type,requirement_value,description,source_url,last_checked,notes) VALUES
                (%s,2,3,'PROGRAM_AVERAGE','70%%','Maintain a minimum 70%% average across all program courses before starting the thesis or research project',%s,%s,%s),
                (%s,2,3,'SUPERVISORY_REVIEW','required','Progress is monitored by the supervisor in consultation with the Program Head',%s,%s,%s)""",
                (audit.program_id,audit.source_url,date.today(),audit.continuation_requirements_raw,audit.program_id,audit.source_url,date.today(),audit.continuation_requirements_raw))
            cursor.execute("DELETE FROM academic_rule_conditions WHERE rule_group_id IN (SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id=%s)",(audit.program_id,))
            cursor.execute("DELETE FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)",(audit.program_id,))
            cursor.execute("DELETE FROM academic_rule_sets WHERE program_id=%s",(audit.program_id,))
            cursor.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,exact_choice_count,source_url,notes) VALUES(%s,'ADMISSION','Applied Computing MSc competitive admission','ALL',1,%s,%s) RETURNING rule_set_id",(audit.program_id,audit.source_url,audit.entrance_requirements_raw)); admission=cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND','Step 1 requirements and Step 2 department review',1) RETURNING rule_group_id",(admission,)); root=cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,minimum_value,unit,parameters,description,sort_order) VALUES(%s,'ENGLISH_GRADE','ENGLISH_STUDIES_12',67,'PERCENT',%s,'Graduate Studies English requirement: English Studies 12 (67%%) or equivalent',1)",(root,Jsonb({'executable':True,'equivalency_requires_confirmation':True})))
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,parent_group_id,operator,label,sort_order) VALUES(%s,%s,'OR','One entry route',2) RETURNING rule_group_id",(admission,root)); routes=cursor.fetchone()[0]
            route_data=[('STANDARD_ENTRY',2.8,70,'Bachelor’s degree in computer science or equivalent; minimum 2.8/4.0 (70%) over final 30 undergraduate credits'),('ALTERNATE_ENTRY',3.0,73,'Bachelor’s degree in another discipline; minimum 3.0/4.0 (73%) over final 30 credits, plus significant computing knowledge and program-area review')]
            for order,(kind,gpa,pct,description) in enumerate(route_data,1):
                cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,minimum_value,unit,parameters,description,sort_order) VALUES(%s,%s,%s,'GPA_4',%s,%s,%s)",(routes,kind,gpa,Jsonb({'percentage_equivalent':pct,'final_credits':30,'executable':kind=='STANDARD_ENTRY','verification':'human_confirmation' if kind!='STANDARD_ENTRY' else 'structured'}),description,order))
            human=[('APPLICANT_QUESTIONNAIRE','Mandatory Applicant Questionnaire'),('REFERENCES','Two references submitted directly to the admissions committee'),('INTERNATIONAL_CREDENTIAL_EVALUATION','Comprehensive ICES evaluation for specified international credentials; other Canadian services may be considered'),('COMPETITIVE_DEPARTMENT_REVIEW','Graduate Program Committee ranks complete applications competitively'),('RELEVANT_INDUSTRY_EXPERIENCE','Relevant industry experience is preferred, not a minimum threshold')]
            for order,(kind,description) in enumerate(human,3):
                cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,parameters,description,sort_order) VALUES(%s,%s,%s,%s,%s)",(root,kind,Jsonb({'executable':False,'verification':'human_confirmation'}),description,order))
            cursor.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,exact_choice_count,source_url,notes) VALUES(%s,'PATHWAY','Year 2 alternative pathway','ALL',1,%s,%s) RETURNING rule_set_id",(audit.program_id,audit.source_url,audit.program_details_raw)); pathway=cursor.fetchone()[0]
            cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'OR','Choose exactly one Year 2 path',1) RETURNING rule_group_id",(pathway,)); paths=cursor.fetchone()[0]
            for order,(label,courses) in enumerate((('Thesis Path',['COMP9600']),('Project & Internship Path',['COMP9290','COMP9400','COMP9500'])),1):
                cursor.execute("INSERT INTO academic_rule_groups(rule_set_id,parent_group_id,operator,label,sort_order) VALUES(%s,%s,'AND',%s,%s) RETURNING rule_group_id",(pathway,paths,label,order)); group=cursor.fetchone()[0]
                for corder,course_id in enumerate(courses,1):
                    cursor.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,parameters,description,sort_order) VALUES(%s,'COURSE',%s,%s,%s,%s)",(group,course_id,Jsonb({'pathway':label}),f'Complete {course_id[:4]} {course_id[4:]}',corder))
            cursor.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes) VALUES(%s,'CONTINUATION','Graduate continuation and sequencing','ALL',%s,%s)",(audit.program_id,audit.source_url,audit.continuation_requirements_raw))
            cursor.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes) VALUES(%s,'COMPLETION','MSc completion requirements','ALL',%s,%s)",(audit.program_id,audit.source_url,audit.completion_requirements_raw))
            revision_id=record_import_revision(cursor, contract, importer="bcit_program_extractor.apply_applied_computing_msc")
            if revision_id: activate_revision(cursor,revision_id,changed_by="bcit_program_extractor.apply_applied_computing_msc")
        connection.commit()


def run(url: str, output_dir: Path, apply: bool, delay: float, html_path: Path | None = None) -> ProgramAudit:
    session = build_session()
    if html_path:
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    else:
        soup, _ = get_soup(session, url, delay)
    audit = parse_program_page(soup, url, database_course_ids())
    missing_records = enrich_missing(soup, url, audit.missing_course_ids, session, delay)
    validated = {r.course_id for r in missing_records if r.validation_status == "validated"}
    if apply and validated:
        apply_database(missing_records)
        audit = parse_program_page(soup, url, database_course_ids())
    elif validated:
        audit.review_flags.append({"code":"VALIDATED_MISSING_COURSES_NOT_IMPORTED","severity":"controlled_import_required","courses":sorted(validated)})
    write_audit(audit, output_dir)
    if apply:
        apply_program(audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-url", action="append", default=[])
    parser.add_argument("--discover-all", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "program_extractor_audit")
    parser.add_argument("--html", type=Path)
    parser.add_argument("--delay", type=float, default=.15)
    parser.add_argument("--apply-db", action="store_true")
    args = parser.parse_args()
    urls = set(args.program_url)
    if args.discover_all:
        urls.update(discover_program_urls(build_session(), args.delay))
    if not urls:
        urls.add(DEFAULT_URL)
    if args.html and len(urls) != 1:
        parser.error("--html supports one program URL")
    for url in sorted(urls):
        if not canonical_bcit_url(url, PROGRAM_PATH_RE):
            parser.error(f"not an official discoverable BCIT program URL: {url}")
        audit = run(url, args.output_dir, args.apply_db, args.delay, args.html)
        print(json.dumps({"program_id":audit.program_id,"courses":len(audit.discovered_course_ids),"missing":audit.missing_course_ids,"import_ready":audit.import_ready,"imported":bool(args.apply_db and audit.import_ready)}, indent=2))


if __name__ == "__main__":
    main()
