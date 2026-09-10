"""Canonical, audit-first contract for governed BCIT program imports."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from dataclasses import asdict, dataclass, field
from typing import Any

CONTRACT_VERSION = "1.0"
SUPPORTED_SEMANTICS = {"all", "choose_n", "minimum_credits", "substitution", "alternative_path", "threshold", "human_confirmation", "raw_policy"}
REVIEW_STATUSES = {"auto-clean", "needs-human-review", "approved"}
CONFIDENCE_STATUSES = {"high", "medium", "low", "human-interpreted", "unknown"}


@dataclass(frozen=True)
class Provenance:
    authoritative_source_url: str
    source_type: str = "official_program_page"
    extracted_at: str = ""
    last_checked: str = ""
    pipeline_version: str = "asteris-program-import/1.0"
    provenance_tag: str = ""
    review_status: str = "needs-human-review"
    confidence: str = "unknown"
    human_approved: bool = False
    approved_by: str = ""
    approved_at: str = ""
    source_sha256: str = ""


@dataclass(frozen=True)
class ReviewItem:
    code: str
    message: str
    category: str = "interpretation"
    blocking: bool = False
    human_confirmation_only: bool = False
    source_excerpt: str = ""
    disposition: str = "open"


@dataclass
class ProgramImportContract:
    program: dict[str, Any]
    offerings: list[dict[str, Any]] = field(default_factory=list)
    curriculum_components: list[dict[str, Any]] = field(default_factory=list)
    course_references: list[dict[str, Any]] = field(default_factory=list)
    rules: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    non_course_requirements: list[dict[str, Any]] = field(default_factory=list)
    international: dict[str, Any] = field(default_factory=dict)
    provenance: Provenance | dict[str, Any] = field(default_factory=lambda: Provenance(""))
    unresolved_items: list[ReviewItem | dict[str, Any]] = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION

    def to_dict(self): return asdict(self)
    def canonical_json(self): return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @property
    def payload_sha256(self): return hashlib.sha256(self.canonical_json().encode()).hexdigest()

    @property
    def idempotency_key(self): return f"{self.program.get('program_id','')}:{self.contract_version}:{self.payload_sha256}"


@dataclass(frozen=True)
class ReadinessReport:
    go: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    payload_sha256: str
    idempotency_key: str


def _courses(components): return [c for component in components for c in component.get("courses", [])]


def validate_import_readiness(contract):
    blockers, warnings = [], []
    provenance = asdict(contract.provenance) if isinstance(contract.provenance, Provenance) else contract.provenance
    for key in ("program_id", "program_name", "credential", "study_mode"):
        if not contract.program.get(key): blockers.append(f"missing required program metadata: {key}")
    if not provenance.get("authoritative_source_url"): blockers.append("missing authoritative source URL")
    if provenance.get("review_status") not in REVIEW_STATUSES: blockers.append("invalid provenance review status")
    if provenance.get("confidence") not in CONFIDENCE_STATUSES: blockers.append("invalid provenance confidence status")
    if not contract.curriculum_components: blockers.append("curriculum is empty")
    seen = set()
    for ref in contract.course_references or _courses(contract.curriculum_components):
        course_id = ref.get("course_id", "")
        if not course_id: blockers.append("course reference missing course_id")
        elif course_id in seen: warnings.append(f"duplicate course reference normalized during import: {course_id}")
        seen.add(course_id)
        if ref.get("reconciliation") in {"missing_course", "unresolved", "needs_review"}: blockers.append(f"unresolved course reference: {course_id or '<unknown>'}")
    for scope, rules in contract.rules.items():
        for rule in rules:
            semantic = rule.get("semantic", "raw_policy")
            if semantic not in SUPPORTED_SEMANTICS: blockers.append(f"unsupported evaluator semantics in {scope}: {semantic}")
            if rule.get("ambiguous") and not rule.get("human_confirmation_only"): blockers.append(f"ambiguous executable rule mapping in {scope}: {rule.get('code', semantic)}")
    for raw in contract.unresolved_items:
        item = raw if isinstance(raw, dict) else asdict(raw)
        label = item.get("code") or item.get("message") or "unresolved item"
        if item.get("blocking"): blockers.append(f"blocking review item: {label}")
        elif item.get("human_confirmation_only"): warnings.append(f"human confirmation required: {label}")
        elif item.get("disposition") not in {"resolved", "accepted"}: blockers.append(f"undisposed review item: {label}")
    return ReadinessReport(not blockers, tuple(dict.fromkeys(blockers)), tuple(dict.fromkeys(warnings)), contract.payload_sha256, contract.idempotency_key)


def require_import_ready(contract):
    report = validate_import_readiness(contract)
    if not report.go: raise ValueError("Import STOP: " + "; ".join(report.blockers))
    return report


def _json_value(value):
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, Decimal): return str(value)
    return value


def contract_rows(contract):
    """Project a normalized contract into stable, database-shaped rows."""
    p, provenance = contract.program, asdict(contract.provenance) if isinstance(contract.provenance, Provenance) else contract.provenance
    program_id = p["program_id"]
    rows = {"programs": [{"program_id":program_id,"program_name":p.get("program_name"),"credential":p.get("credential"),
        "study_mode":p.get("study_mode"),"school":p.get("school"),"campus":p.get("campus"),
        "delivery_method":p.get("delivery_method"),"source_url":provenance.get("authoritative_source_url"),"status":"Active"}],
        "program_offerings": [], "curriculum_components": [], "program_courses": [], "academic_rule_sets": []}
    for index, item in enumerate(contract.offerings, 1):
        intake = str(item.get("intake") or item.get("start_date") or index)
        rows["program_offerings"].append({"offering_id":item.get("offering_id") or f"{program_id}-{intake}","program_id":program_id,
            "start_date":item.get("start_date") or (intake if len(intake) == 10 else None),"study_mode":item.get("study_mode") or p.get("study_mode"),
            "campus":item.get("campus") or p.get("campus"),"delivery_method":item.get("delivery_method") or p.get("delivery_method"),
            "application_status":item.get("application_status") or item.get("status")})
    seen_courses = set()
    for order, component in enumerate(contract.curriculum_components, 1):
        name = component.get("name") or component.get("component_name") or f"Component {order}"
        rows["curriculum_components"].append({"program_id":program_id,"component_name":name,
            "component_order":component.get("order") or component.get("component_order") or order,
            "required_credits":component.get("required_credits") or None,"notes":component.get("raw_text") or component.get("notes")})
        for course in component.get("courses", []):
            cid = course.get("course_id")
            if cid and cid not in seen_courses:
                rows["program_courses"].append({"program_id":program_id,"course_id":cid,
                    "course_type":course.get("course_type") or course.get("role"),"required":course.get("role","REQUIRED") == "REQUIRED",
                    "level":course.get("level"),"term":course.get("term"),"notes":name})
                seen_courses.add(cid)
    for scope, rules in sorted(contract.rules.items()):
        for rule in rules:
            rows["academic_rule_sets"].append({"program_id":program_id,"rule_scope":scope.upper(),
                "rule_name":rule.get("code") or rule.get("semantic") or scope,"study_mode":p.get("study_mode"),
                "exact_choice_count":rule.get("choose_n"),"source_url":provenance.get("authoritative_source_url"),
                "notes":rule.get("raw")})
    return {table: sorted(values, key=lambda row: tuple(str(row.get(k,'')) for k in sorted(row))) for table, values in sorted(rows.items())}


ROW_KEYS = {"programs":("program_id",), "program_offerings":("offering_id",),
    "curriculum_components":("program_id","component_name"), "program_courses":("program_id","course_id"),
    "academic_rule_sets":("program_id","rule_scope","rule_name")}


def dry_run_diff(cursor, contract):
    """Return a deterministic row-level change set without mutating the database."""
    desired, program_id = contract_rows(contract), contract.program["program_id"]
    changes = []
    for table, rows in desired.items():
        keys = ROW_KEYS[table]
        columns = sorted({"program_id", *keys, *(column for row in rows for column in row)})
        cursor.execute(f"SELECT {','.join(columns)} FROM {table} WHERE program_id=%s", (program_id,))
        current = {tuple(str(row[columns.index(k)]) for k in keys): dict(zip(columns, map(_json_value, row))) for row in cursor.fetchall()}
        target = {tuple(str(row.get(k)) for k in keys): {c:_json_value(row.get(c)) for c in columns} for row in rows}
        for key in sorted(set(current) | set(target)):
            before, after = current.get(key), target.get(key)
            action = "insert" if before is None else "delete-or-deactivate" if after is None else "unchanged" if before == after else "update"
            changed = {} if action in {"insert","delete-or-deactivate"} else {c:{"before":before.get(c),"after":after.get(c)} for c in columns if before.get(c) != after.get(c)}
            changes.append({"action":action,"table":table,"key":dict(zip(keys,key)),"before":before,"after":after,"changed":changed})
    changes.sort(key=lambda x:(x["table"],tuple(x["key"].values()),x["action"]))
    return {"contract_version":contract.contract_version,"program_id":program_id,"payload_sha256":contract.payload_sha256,
        "summary":{kind:sum(c["action"] == kind for c in changes) for kind in ("insert","update","unchanged","delete-or-deactivate")},"changes":changes}


def write_common_contract(cursor, contract, *, program_overrides=None, course_adapter=None, rule_adapter=None):
    """Idempotently write stable common structures; adapters own unsafe semantics."""
    rows, program_id = contract_rows(contract), contract.program["program_id"]
    program = dict(rows["programs"][0]); program.update(program_overrides or {})
    columns = list(program)
    updates = [c for c in columns if c != "program_id"]
    cursor.execute(f"INSERT INTO programs({','.join(columns)}) VALUES({','.join(['%s']*len(columns))}) "
        f"ON CONFLICT(program_id) DO UPDATE SET {','.join(f'{c}=EXCLUDED.{c}' for c in updates)}", tuple(program[c] for c in columns))
    desired_components = {row["component_name"] for row in rows["curriculum_components"]}
    for component in rows["curriculum_components"]:
        cursor.execute("""INSERT INTO curriculum_components(program_id,component_name,component_order,required_credits,notes)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(program_id,component_name) DO UPDATE SET
            component_order=EXCLUDED.component_order,required_credits=EXCLUDED.required_credits,notes=EXCLUDED.notes RETURNING component_id""",
            tuple(component[k] for k in ("program_id","component_name","component_order","required_credits","notes")))
        component_id=cursor.fetchone()[0]
        source=next(c for c in contract.curriculum_components if (c.get("name") or c.get("component_name")) == component["component_name"])
        desired_courses=set()
        for course in source.get("courses",[]):
            cid=course.get("course_id"); desired_courses.add(cid)
            # The live key includes role and study mode. Replace a course's
            # mapping so role/mode changes remain declarative and idempotent.
            cursor.execute("DELETE FROM curriculum_component_courses WHERE component_id=%s AND course_id=%s", (component_id,cid))
            cursor.execute("""INSERT INTO curriculum_component_courses(component_id,course_id,course_role,study_mode)
                VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (component_id,cid,course.get("role","REQUIRED"),course.get("study_mode","ALL")))
        if desired_courses: cursor.execute("DELETE FROM curriculum_component_courses WHERE component_id=%s AND NOT (course_id=ANY(%s))",(component_id,list(desired_courses)))
        else: cursor.execute("DELETE FROM curriculum_component_courses WHERE component_id=%s",(component_id,))
    if desired_components:
        cursor.execute("DELETE FROM curriculum_component_courses WHERE component_id IN (SELECT component_id FROM curriculum_components WHERE program_id=%s AND NOT (component_name=ANY(%s)))",(program_id,list(desired_components)))
        cursor.execute("DELETE FROM curriculum_components WHERE program_id=%s AND NOT (component_name=ANY(%s))",(program_id,list(desired_components)))
    desired_courses={r["course_id"] for r in rows["program_courses"]}
    for row in rows["program_courses"]:
        mapped=course_adapter(row, contract) if course_adapter else row
        cursor.execute("""INSERT INTO program_courses(program_id,course_id,course_type,required,level,term,notes)
            VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(program_id,course_id) DO UPDATE SET
            course_type=EXCLUDED.course_type,required=EXCLUDED.required,level=EXCLUDED.level,term=EXCLUDED.term,notes=EXCLUDED.notes""",
            tuple(mapped.get(k) for k in ("program_id","course_id","course_type","required","level","term","notes")))
    if desired_courses: cursor.execute("DELETE FROM program_courses WHERE program_id=%s AND NOT (course_id=ANY(%s))",(program_id,list(desired_courses)))
    else: cursor.execute("DELETE FROM program_courses WHERE program_id=%s",(program_id,))
    if rule_adapter: rule_adapter(cursor, contract)
    return rows


def approve_payload(cursor, contract, *, approved_by, review_notes=None):
    cursor.execute("""INSERT INTO program_import_approvals(program_id,payload_sha256,approved_by,review_notes)
        VALUES(%s,%s,%s,%s) ON CONFLICT(program_id,payload_sha256) DO UPDATE SET
        approved_by=EXCLUDED.approved_by,approved_at=CURRENT_TIMESTAMP,approval_status='approved',review_notes=EXCLUDED.review_notes
        RETURNING approval_id""", (contract.program["program_id"],contract.payload_sha256,approved_by,review_notes))
    return cursor.fetchone()[0]


def require_approved_hash(cursor, contract):
    provenance = asdict(contract.provenance) if isinstance(contract.provenance, Provenance) else contract.provenance
    if provenance.get("review_status") == "auto-clean": return True
    cursor.execute("SELECT 1 FROM program_import_approvals WHERE program_id=%s AND payload_sha256=%s AND approval_status='approved'",
        (contract.program["program_id"],contract.payload_sha256))
    if cursor.fetchone() is None: raise ValueError(f"Import STOP: exact normalized payload hash {contract.payload_sha256} is not approved")
    return True


def transition_revision(cursor, revision_id, to_status, *, changed_by, reason=None):
    cursor.execute("SELECT lifecycle_status FROM program_import_revisions WHERE revision_id=%s FOR UPDATE",(revision_id,)); row=cursor.fetchone()
    if not row: raise ValueError(f"unknown revision: {revision_id}")
    old=row[0]
    cursor.execute("UPDATE program_import_revisions SET lifecycle_status=%s WHERE revision_id=%s",(to_status,revision_id))
    cursor.execute("INSERT INTO program_import_revision_transitions(revision_id,from_status,to_status,changed_by,reason) VALUES(%s,%s,%s,%s,%s)",(revision_id,old,to_status,changed_by,reason))


def activate_revision(cursor, revision_id, *, changed_by, reason=None):
    cursor.execute("SELECT program_id FROM program_import_revisions WHERE revision_id=%s",(revision_id,)); row=cursor.fetchone()
    if not row: raise ValueError(f"unknown revision: {revision_id}")
    program_id=row[0]
    cursor.execute("SELECT revision_id FROM program_active_import_revisions WHERE program_id=%s FOR UPDATE",(program_id,)); prior=cursor.fetchone()
    if prior and prior[0] != revision_id: transition_revision(cursor,prior[0],"superseded",changed_by=changed_by,reason=reason)
    transition_revision(cursor,revision_id,"active",changed_by=changed_by,reason=reason)
    cursor.execute("""INSERT INTO program_active_import_revisions(program_id,revision_id,activated_by) VALUES(%s,%s,%s)
        ON CONFLICT(program_id) DO UPDATE SET revision_id=EXCLUDED.revision_id,activated_at=CURRENT_TIMESTAMP,activated_by=EXCLUDED.activated_by""",(program_id,revision_id,changed_by))


def rollback_revision(cursor, program_id, *, changed_by, reason=None):
    cursor.execute("SELECT revision_id FROM program_active_import_revisions WHERE program_id=%s FOR UPDATE",(program_id,)); active=cursor.fetchone()
    if not active: raise ValueError(f"no active revision for {program_id}")
    cursor.execute("""SELECT revision_id FROM program_import_revisions WHERE program_id=%s AND revision_id<>%s
        AND lifecycle_status IN ('superseded','active') ORDER BY revision_id DESC LIMIT 1""",(program_id,active[0])); previous=cursor.fetchone()
    if not previous: raise ValueError(f"no previous known-good revision for {program_id}")
    transition_revision(cursor,active[0],"rolled-back",changed_by=changed_by,reason=reason)
    activate_revision(cursor,previous[0],changed_by=changed_by,reason=reason or f"rollback from {active[0]}")
    return previous[0]


def _review_items(audit):
    required = {"program_id", "program_name", "official_name", "credential", "study_mode", "curriculum"}
    items = [asdict(ReviewItem(f"UNRESOLVED_{str(x).upper()}", f"Unresolved field: {x}",
        blocking=str(x) in required, human_confirmation_only=str(x) not in required,
        disposition="open" if str(x) in required else "accepted")) for x in audit.get("unresolved_fields", []) or []]
    for flag in audit.get("review_flags", []) or []:
        severity = flag.get("severity", "human_review")
        human = severity in {"human_review", "human_confirmation", "preserved_raw", "evaluator_gap"}
        items.append(asdict(ReviewItem(flag.get("code", "REVIEW_REQUIRED"), flag.get("raw", "Review required"), severity,
            severity in {"blocking", "error", "unsupported"}, human, flag.get("raw", ""), "accepted" if human else "open")))
    return items


def _provenance(audit, review):
    extracted = audit.get("source_retrieved_at") or audit.get("extracted_at") or ""
    return Provenance(audit.get("source_url", ""), extracted_at=extracted, last_checked=extracted,
        provenance_tag=audit.get("program_id", ""), review_status="needs-human-review" if review else "auto-clean",
        confidence="human-interpreted" if review else "high", source_sha256=audit.get("source_sha256", ""))


def adapt_shared_program_audit(audit):
    """Normalize Electronics and M600MSC ProgramAudit payloads."""
    components = audit.get("components", [])
    refs = audit.get("course_references") or _courses(components)
    rules = {scope: [] for scope in ("admissions", "progression", "completion", "substitution", "pathway")}
    for component in components:
        rule_type = component.get("rule_type", "")
        semantic = {"MINIMUM_CREDITS_FROM_POOL":"minimum_credits", "SUBSTITUTION_OPTION":"substitution", "ALTERNATIVE_PATH":"alternative_path"}.get(rule_type, "all")
        scope = "substitution" if semantic == "substitution" else "pathway" if semantic == "alternative_path" else "completion"
        rules[scope].append({"code":rule_type or "ALL_LISTED_COURSES", "semantic":semantic,
            "minimum_credits":component.get("required_credits") or None,
            "course_ids":[c.get("course_id") for c in component.get("courses", [])]})
    for scope, field_name in (("admissions","entrance_requirements_raw"), ("progression","continuation_requirements_raw"), ("completion","completion_requirements_raw")):
        if audit.get(field_name): rules[scope].append({"code":field_name.upper(), "semantic":"raw_policy", "raw":audit[field_name], "human_confirmation_only":True})
    review = _review_items(audit)
    for cid in audit.get("missing_course_ids", []) or []: review.append(asdict(ReviewItem("UNRESOLVED_COURSE", cid, "course_reference", True)))
    program = {key:audit.get(key, "") for key in ("program_id","program_name","credential","study_mode","school","campus","delivery_method","total_credits")}
    offerings = [{"intake":x, "status":"published"} for x in audit.get("intakes", [])]
    return ProgramImportContract(program, offerings, components, refs, rules, [],
        {"eligibility_or_restrictions_raw":audit.get("international_requirements_raw", "")}, _provenance(audit, review), review)


def adapt_nursing_audit(audit, *, main_bsn=False):
    """Normalize Specialty Nursing family and main 8875BSN audits."""
    components = audit.get("curriculum_components", [])
    refs = audit.get("course_references") or _courses(components)
    sections, requirements = audit.get("authoritative_sections", {}), audit.get("structured_requirement_text", {})
    program = {"program_id":audit.get("program_id", ""), "program_name":audit.get("official_name") or audit.get("program_name", ""),
        "credential":audit.get("credential", ""), "study_mode":audit.get("study_mode", ""), "school":audit.get("school_area", ""),
        "campus":audit.get("campus", ""), "delivery_method":audit.get("delivery", ""), "total_credits":audit.get("total_credits", "")}
    rules = {
        "admissions":[{"semantic":"raw_policy", "code":"ADMISSIONS", "raw":sections.get("admissions") or audit.get("admissions_raw", ""), "human_confirmation_only":True}],
        "progression":[{"semantic":"raw_policy", "code":"CONTINUATION", "raw":sections.get("program_details") or requirements.get("continuation_requirements_raw", ""), "human_confirmation_only":True}],
        "completion":[{"semantic":"raw_policy", "code":"COMPLETION", "raw":sections.get("graduating_and_jobs", ""), "human_confirmation_only":True}],
        "substitution":[], "pathway":[]}
    review = _review_items(audit)
    for cid in audit.get("missing_unresolved_course_ids", []) or []: review.append(asdict(ReviewItem("UNRESOLVED_COURSE", cid, "course_reference", True)))
    clinical = audit.get("clinical_practicum_course_ids", []) or []
    non_course = [{"type":"clinical_or_practicum", "course_ids":clinical, "human_confirmation_only":True}] if clinical else []
    international = requirements.get("international_requirements_raw", "") or sections.get("international_applicants", "")
    if main_bsn and not international: international = "Not available to international students"
    return ProgramImportContract(program, [{"intake":x,"status":"published"} for x in audit.get("intakes_mentioned", audit.get("intakes", []))],
        components, refs, rules, non_course, {"eligibility_or_restrictions_raw":international}, _provenance(audit, review), review)


def record_import_revision(cursor, contract, *, importer, import_status="applied"):
    """Record a normalized payload once; False means the same payload was replayed."""
    payload = contract.to_dict(); p = payload["provenance"]
    cursor.execute("""INSERT INTO program_import_revisions
        (program_id,contract_version,payload_sha256,idempotency_key,normalized_payload,source_url,source_type,
         extracted_at,pipeline_version,review_status,confidence_status,human_approved,approved_by,approved_at,importer,import_status)
        VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s,NULLIF(%s,'')::timestamptz,%s,%s,%s,%s,NULLIF(%s,''),NULLIF(%s,'')::timestamptz,%s,%s)
        ON CONFLICT(idempotency_key) DO NOTHING RETURNING revision_id""",
        (contract.program["program_id"], contract.contract_version, contract.payload_sha256, contract.idempotency_key,
         json.dumps(payload), p["authoritative_source_url"], p["source_type"], p["extracted_at"], p["pipeline_version"],
         p["review_status"], p["confidence"], p["human_approved"], p["approved_by"], p["approved_at"], importer, import_status))
    row = cursor.fetchone()
    return row[0] if row else False
