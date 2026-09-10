"""Batch, audit-only extraction for related BCIT program families.

This module deliberately has no database write path.  It reuses the canonical
program matrix parser and course-database reconciliation helpers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from bcit_course_gap_enrichment import build_session, clean, database_course_ids, get_soup
from bcit_program_extractor import parse_matrix, PROGRAM_ID_RE


PROGRAMS = {
    "810KBSN": "https://www.bcit.ca/programs/specialty-nursing-critical-care-combined-critical-care-emergency-option-bachelor-of-science-in-nursing-part-time-810kbsn/",
    "810ABSN": "https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/",
    "810NBSN": "https://www.bcit.ca/programs/specialty-nursing-emergency-combined-emergency-critical-care-option-bachelor-of-science-in-nursing-part-time-810nbsn/",
    "810BBSN": "https://www.bcit.ca/programs/specialty-nursing-emergency-standard-option-bachelor-of-science-in-nursing-part-time-810bbsn/",
    "810MBSN": "https://www.bcit.ca/programs/specialty-nursing-high-acuity-bachelor-of-science-in-nursing-part-time-810mbsn/",
    "810CBSN": "https://www.bcit.ca/programs/specialty-nursing-neonatal-bachelor-of-science-in-nursing-part-time-810cbsn/",
    "810DBSN": "https://www.bcit.ca/programs/specialty-nursing-nephrology-bachelor-of-science-in-nursing-part-time-810dbsn/",
    "810QBSN": "https://www.bcit.ca/programs/specialty-nursing-pediatric-critical-care-option-bachelor-of-science-in-nursing-part-time-810qbsn/",
    "810FBSN": "https://www.bcit.ca/programs/specialty-nursing-pediatric-standard-option-bachelor-of-science-in-nursing-part-time-810fbsn/",
    "810SBSN": "https://www.bcit.ca/programs/specialty-nursing-perinatal-perioperative-option-bachelor-of-science-in-nursing-part-time-810sbsn/",
    "810GBSN": "https://www.bcit.ca/programs/specialty-nursing-perinatal-standard-option-bachelor-of-science-in-nursing-part-time-810gbsn/",
    "810HBSN": "https://www.bcit.ca/programs/specialty-nursing-perioperative-bachelor-of-science-in-nursing-part-time-810hbsn/",
}

SECTION_ALIASES = {
    "overview": ("Overview",),
    "admissions": ("Entrance Requirements", "Admission Requirements"),
    "advanced_placement": ("Advanced Placement",),
    "program_details": ("Program Details",),
    "costs_and_supplies": ("Costs & Supplies", "Costs and Supplies"),
    "graduating_and_jobs": ("Graduating & Jobs", "Graduating and Jobs"),
}

RULE_PATTERNS = [
    ("professional_registration_licensure", r"registered nurse|registration with|practising registration|licen[cs]"),
    ("specialty_employment_experience", r"work experience|employed|employment|experience in"),
    ("clinical_placement_eligibility", r"clinical placement|practice placement|clinical site|placement site"),
    ("clinical_practice_hours", r"practice hours?|clinical hours?"),
    ("health_safety_clearance", r"immuni[sz]|criminal record|background check|cpr|basic life support|fit test|respirator"),
    ("cohort_or_sequence", r"cohort|sequence|sequential|in order|concurrent|concurrently"),
    ("completion_time_limit", r"within \d+ (?:years?|months?)|time limit|maximum.*years?"),
    ("advanced_placement_transfer_plar", r"advanced placement|prior learning|\bplar\b|transfer credit"),
    ("employer_site_requirement", r"employer|agency requirement|site requirement"),
]

CLASSIFICATION = {
    "professional_registration_licensure": "storable/representable but not yet executable",
    "specialty_employment_experience": "storable/representable but not yet executable",
    "clinical_placement_eligibility": "requires schema/model extension",
    "clinical_practice_hours": "requires schema/model extension",
    "health_safety_clearance": "should remain authoritative raw text + human confirmation",
    "cohort_or_sequence": "requires schema/model extension",
    "completion_time_limit": "storable/representable but not yet executable",
    "advanced_placement_transfer_plar": "storable/representable but not yet executable",
    "employer_site_requirement": "should remain authoritative raw text + human confirmation",
    "curriculum_all_listed_courses": "already fully supported and executable",
    "curriculum_minimum_credits_from_pool": "storable/representable but not yet executable",
    "course_prerequisite": "already fully supported and executable",
}


def section_after_heading(soup: BeautifulSoup, names: tuple[str, ...]) -> str:
    wanted = {n.lower() for n in names}
    heading = next((h for h in soup.find_all(["h2", "h3"]) if clean(h.get_text(" ", strip=True)).lower() in wanted), None)
    if heading is None:
        return ""
    pieces = []
    for node in heading.next_siblings:
        if isinstance(node, Tag) and node.name == heading.name:
            break
        if isinstance(node, Tag):
            text = clean(node.get_text(" ", strip=True))
            if text:
                pieces.append(text)
    return clean(" ".join(pieces))


def json_ld_program(soup: BeautifulSoup) -> dict:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            value = json.loads(script.string or "null")
        except json.JSONDecodeError:
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, dict) and item.get("@type") == "EducationalOccupationalProgram":
                return item
    return {}


def metadata(soup: BeautifulSoup, url: str) -> dict:
    data = json_ld_program(soup)
    provider = data.get("provider") if isinstance(data.get("provider"), dict) else {}
    department = provider.get("department") if isinstance(provider.get("department"), dict) else {}
    address = provider.get("address") if isinstance(provider.get("address"), dict) else {}
    h1 = soup.find("h1")
    program_id_match = PROGRAM_ID_RE.search(url.rstrip("/"))
    delivery_node = soup.select_one("#delivery")
    location_node = soup.select_one("#pgm_location")
    delivery_raw = clean(delivery_node.get_text(" ", strip=True)) if delivery_node else ""
    location_raw = clean(location_node.get_text(" ", strip=True)) if location_node else ""
    return {
        "program_id": (data.get("identifier") or (program_id_match.group(1) if program_id_match else "")).upper(),
        "official_name": data.get("alternateName") or data.get("name") or clean(h1.get_text(" ", strip=True) if h1 else ""),
        "credential": data.get("educationalCredentialAwarded") or "",
        "school_area": department.get("name") or "",
        "study_mode": data.get("educationalProgramMode") or "",
        "campus": "Online" if re.search(r"online|distance", location_raw, re.I) else (address.get("addressLocality") or ""),
        "delivery": delivery_raw,
        "intakes_mentioned": [],
        "description": data.get("description") or "",
    }


def extract_rules(sections: dict[str, str], components: list) -> list[dict]:
    rules = []
    for component in components:
        concept = "curriculum_minimum_credits_from_pool" if component.rule_type == "MINIMUM_CREDITS_FROM_POOL" else "curriculum_all_listed_courses"
        rules.append({"concept": concept, "classification": CLASSIFICATION[concept], "source_section": "curriculum", "authoritative_raw": component.raw_text})
        for course in component.courses:
            if course.prerequisite_raw:
                rules.append({"concept": "course_prerequisite", "classification": CLASSIFICATION["course_prerequisite"], "source_section": "curriculum", "course_id": course.course_id, "authoritative_raw": course.prerequisite_raw})
    for section, text in sections.items():
        for concept, pattern in RULE_PATTERNS:
            if re.search(pattern, text, re.I):
                rules.append({"concept": concept, "classification": CLASSIFICATION[concept], "source_section": section, "authoritative_raw": text})
    return rules


def extract_one(soup: BeautifulSoup, url: str, db_ids: set[str]) -> dict:
    meta = metadata(soup, url)
    components, total = parse_matrix(soup, url)
    refs = [asdict(c) for component in components for c in component.courses]
    unique = sorted({r["course_id"] for r in refs})
    for ref in refs:
        ref["reconciliation"] = "existing_database" if ref["course_id"] in db_ids else "missing_unresolved"
    sections = {key: section_after_heading(soup, aliases) for key, aliases in SECTION_ALIASES.items()}
    intake_match = re.search(r"Three intakes per year:\s*([^.;]+)", sections.get("overview", ""), re.I)
    if intake_match:
        meta["intakes_mentioned"] = re.findall(r"January|April|September", intake_match.group(1), re.I)
    for node in soup.find_all("h3"):
        label = clean(node.get_text(" ", strip=True))
        parent = node.parent
        value = clean(parent.get_text(" ", strip=True)) if isinstance(parent, Tag) else ""
        if label and value and label.lower() not in {"overview", "entrance requirements", "program details"}:
            sections.setdefault("subsections", {})[label] = value
    subsections = sections.get("subsections", {})
    def matched_raw(pattern: str) -> str:
        return clean(" ".join(value for label, value in subsections.items() if re.search(pattern, label, re.I)))
    structured_requirements = {
        "applicant_prerequisites_raw": clean(" ".join(filter(None, [sections.get("admissions", ""), matched_raw(r"current experience|entrance|admission|eligib|pre.?entry")]))),
        "licensure_registration_raw": matched_raw(r"clinical requirements|registration|licen[cs]"),
        "work_experience_raw": matched_raw(r"current experience|work experience|employment"),
        "clinical_practicum_requirements_raw": matched_raw(r"clinical requirements|practicum|placement"),
        "progression_continuation_completion_raw": matched_raw(r"continuation|completion|graduat|program length|maximum time"),
        "advanced_placement_plar_transfer_raw": clean(" ".join(filter(None, [sections.get("advanced_placement", ""), matched_raw(r"advanced placement|prior learning|plar|transfer|re-admission")]))),
    }
    return {
        **meta,
        "source_url": url,
        "source_retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(str(soup).encode("utf-8")).hexdigest(),
        "total_credits": total,
        "authoritative_sections": sections,
        "structured_requirement_text": structured_requirements,
        "curriculum_components": [asdict(c) for c in components],
        "course_references": refs,
        "unique_course_ids": unique,
        "existing_course_ids": sorted(set(unique) & db_ids),
        "missing_unresolved_course_ids": sorted(set(unique) - db_ids),
        "clinical_practicum_course_ids": sorted({r["course_id"] for r in refs if re.search(r"clinical|practicum|practice|precept", r["course_name"], re.I)}),
        "rules": extract_rules({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for k, v in sections.items()}, components),
        "unresolved_fields": [k for k, v in {**meta, "curriculum": components}.items() if not v],
        "extraction_success": bool(meta["program_id"] and meta["official_name"] and components),
    }


def compare(programs: list[dict], db_count: int) -> dict:
    all_sets = [set(p["unique_course_ids"]) for p in programs]
    shared_all = sorted(set.intersection(*all_sets)) if all_sets else []
    occurrence = Counter(c for values in all_sets for c in values)
    union = set(occurrence)
    concepts = defaultdict(list)
    for p in programs:
        for rule in p["rules"]:
            concepts[rule["concept"]].append(p["program_id"])
    signatures = defaultdict(list)
    for p in programs:
        signatures[tuple(p["unique_course_ids"])].append(p["program_id"])
    existing = sorted(union & database_course_ids())
    missing = sorted(union - set(existing))
    by_id = {p["program_id"]: set(p["unique_course_ids"]) for p in programs}
    def delta(left: str, right: str) -> list[str]:
        return sorted(by_id.get(left, set()) - by_id.get(right, set()))
    return {
        "programs_requested": len(PROGRAMS), "programs_extracted_successfully": sum(p["extraction_success"] for p in programs),
        "live_database_course_count": db_count, "unique_course_references": len(union),
        "existing_course_references": len(existing), "missing_unresolved_course_references": len(missing),
        "existing_course_ids": existing, "missing_unresolved_course_ids": missing,
        "courses_shared_by_all_programs": shared_all,
        "duplicated_shared_course_pools": {c: n for c, n in sorted(occurrence.items()) if n > 1},
        "unique_courses_by_program": {p["program_id"]: sorted(set(p["unique_course_ids"]) - set().union(*(s for s in all_sets if s is not all_sets[i]))) for i, p in enumerate(programs)},
        "clinical_practicum_patterns": {p["program_id"]: p["clinical_practicum_course_ids"] for p in programs},
        "program_structures": {p["program_id"]: {"total_credits": p["total_credits"], "components": [{"name": c["name"], "required_credits": c["required_credits"], "rule_type": c["rule_type"], "course_count": len(c["courses"])} for c in p["curriculum_components"]]} for p in programs},
        "option_pair_differences": {
            "critical_care_combined_vs_standard": {"combined": "810KBSN", "standard": "810ABSN", "combined_only": delta("810KBSN", "810ABSN"), "standard_only": delta("810ABSN", "810KBSN")},
            "emergency_combined_vs_standard": {"combined": "810NBSN", "standard": "810BBSN", "combined_only": delta("810NBSN", "810BBSN"), "standard_only": delta("810BBSN", "810NBSN")},
            "pediatric_critical_care_vs_standard": {"critical_care": "810QBSN", "standard": "810FBSN", "critical_care_only": delta("810QBSN", "810FBSN"), "standard_only": delta("810FBSN", "810QBSN")},
            "perinatal_perioperative_vs_standard": {"perioperative_option": "810SBSN", "standard": "810GBSN", "perioperative_only": delta("810SBSN", "810GBSN"), "standard_only": delta("810GBSN", "810SBSN")},
        },
        "rule_concepts": {k: {"classification": CLASSIFICATION[k], "programs": sorted(set(v))} for k, v in sorted(concepts.items())},
        "identical_curriculum_groups": [ids for ids in signatures.values() if len(ids) > 1],
        "modeling_assessment": {
            "recommended": "12 independent program records with explicitly shared reusable rule/course-pool data",
            "current_architecture_fit": "Can store independent programs, curriculum and raw rule text without redesign; nursing-specific clinical/professional evaluation needs extensions before full automation.",
            "tradeoff": "A base-program-plus-variants model reduces duplication but introduces inheritance/override semantics absent from current Asteris. Independent programs preserve BCIT identifiers and source fidelity, while shared reusable rule definitions can be added incrementally.",
        },
    }


def write_reports(programs: list[dict], comparison: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for program in programs:
        (output_dir / f"{program['program_id'].lower()}_audit.json").write_text(json.dumps(program, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "family_comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output_dir / "family_comparison.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["program_id", "official_name", "courses", "existing", "missing_unresolved", "clinical_practicum", "success"])
        for p in programs:
            writer.writerow([p["program_id"], p["official_name"], len(p["unique_course_ids"]), len(p["existing_course_ids"]), len(p["missing_unresolved_course_ids"]), ";".join(p["clinical_practicum_course_ids"]), p["extraction_success"]])
    lines = ["# BCIT Specialty Nursing family extraction audit", "", "Audit only — no program or course data was imported.", "", "## Summary", "",
             f"- Extracted successfully: {comparison['programs_extracted_successfully']}/{comparison['programs_requested']}",
             f"- Unique course references: {comparison['unique_course_references']}",
             f"- Existing / missing-unresolved: {comparison['existing_course_references']} / {comparison['missing_unresolved_course_references']}", "", "## Program comparison", "",
             "| Program | Courses | Existing | Missing | Clinical/practicum |", "|---|---:|---:|---:|---|"]
    for p in programs:
        lines.append(f"| {p['program_id']} | {len(p['unique_course_ids'])} | {len(p['existing_course_ids'])} | {len(p['missing_unresolved_course_ids'])} | {', '.join(p['clinical_practicum_course_ids']) or '—'} |")
    lines += ["", "## Shared and variant structure", "", f"Courses shared by all 12: {', '.join(comparison['courses_shared_by_all_programs']) or 'None'}.", "",
              "BCIT exposes twelve authoritative program identifiers and pages. Keep twelve independent program records, with reusable shared rule/course-pool objects where duplication is proven. A base/variant inheritance redesign is not justified before the current architecture has override semantics.", "", "## Rule and model gaps", ""]
    for concept, detail in comparison["rule_concepts"].items():
        lines.append(f"- `{concept}` — {detail['classification']} ({len(detail['programs'])} programs)")
    lines += ["", "## Option-specific course differences", ""]
    for label, values in comparison["option_pair_differences"].items():
        sides = [f"{key}: {', '.join(value) or 'none'}" for key, value in values.items() if isinstance(value, list)]
        lines.append(f"- {label.replace('_', ' ')} — {'; '.join(sides)}")
    lines += ["", "## Missing/unresolved course references", "", ", ".join(comparison["missing_unresolved_course_ids"]), "", "## Recommended first import", "", "810ABSN (Critical Care — Standard Option): it is a standard rather than combined option, making it the smallest clean test of nursing registration, specialty admission, curriculum, and clinical/practice semantics before nested cross-specialty option logic is introduced."]
    (output_dir / "family_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path, delay: float = 0.15) -> tuple[list[dict], dict]:
    session, db_ids = build_session(), database_course_ids()
    output_dir.mkdir(parents=True, exist_ok=True)
    programs = []
    for expected_id, url in PROGRAMS.items():
        source_path = output_dir / f"{expected_id.lower()}_source.html"
        soup = None
        for attempt in range(4):
            try:
                soup, _ = get_soup(session, url, delay)
                source_path.write_text(str(soup), encoding="utf-8")
                break
            except Exception:
                if attempt == 3:
                    if source_path.exists():
                        soup = BeautifulSoup(source_path.read_text(encoding="utf-8"), "html.parser")
                        break
                    raise
                time.sleep(2 ** attempt)
        assert soup is not None
        program = extract_one(soup, url, db_ids)
        if program["program_id"] != expected_id:
            program["unresolved_fields"].append(f"program_id_expected_{expected_id}")
            program["extraction_success"] = False
        programs.append(program)
    comparison = compare(programs, len(db_ids))
    write_reports(programs, comparison, output_dir)
    return programs, comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "program_extractor_audit" / "nursing_batch")
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()
    _, comparison = run(args.output_dir, args.delay)
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
