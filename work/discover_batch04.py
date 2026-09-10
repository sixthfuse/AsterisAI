"""Discover a balanced, non-duplicate Batch 04 from BCIT's official sitemap."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from database import get_connection
from mixed_bcit_batch import curriculum_roles, hero_metadata
from bcit_program_extractor import parse_program_page


SITEMAP = "https://www.bcit.ca/wp-sitemap-posts-program-1.xml"
OUTPUT = Path("program_extractor_audit/batch_scalability_04/discovery.json")
PROGRAM_ID_RE = re.compile(r"-([a-z0-9]+)/*$", re.I)
SCHOOL_ORDER = [
    "School of Business + Media",
    "School of Computing and Academic Studies",
    "School of Construction and the Environment",
    "School of Energy",
    "School of Health Sciences",
    "School of Transportation",
]
AREA_BY_SCHOOL = {
    "School of Business + Media": "BUS",
    "School of Computing and Academic Studies": "COMP",
    "School of Construction and the Environment": "CE",
    "School of Energy": "ENG",
    "School of Health Sciences": "HEALTH",
    "School of Transportation": "TRANS",
}


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") + "/", "", ""))


def slug_id(url: str) -> str:
    match = PROGRAM_ID_RE.search(urlsplit(url).path)
    return match.group(1).upper() if match else ""


def campus_delivery(text: str, study_mode: str) -> tuple[str, str]:
    low = text.lower()
    campuses = []
    for needle, label in (
        ("downtown campus", "Downtown Campus"),
        ("aerospace technology campus", "Aerospace Technology Campus"),
        ("marine campus", "Marine Campus"),
        ("annacis island campus", "Annacis Island Campus"),
        ("burnaby campus", "Burnaby Campus"),
    ):
        if needle in low:
            campuses.append(label)
    online = "online" in low or "distance" in low
    if online:
        campuses.append("Online")
    campus = " / ".join(dict.fromkeys(campuses)) or "Refer to official BCIT program page"
    if online and len(campuses) == 1:
        delivery = "Online"
    elif online:
        delivery = "Blended"
    else:
        delivery = "In person"
    return campus, delivery


def inspect(url: str, existing_course_ids: set[str]) -> dict:
    session = requests.Session()
    session.headers["User-Agent"] = "Asteris governed catalog audit/1.0"
    response = session.get(url, timeout=35, allow_redirects=True)
    response.raise_for_status()
    final_url = clean_url(response.url)
    soup = BeautifulSoup(response.text, "html.parser")
    audit = parse_program_page(soup, final_url, existing_course_ids)
    credential, study_mode, school = hero_metadata(soup)
    canonical_id = (audit.program_id or slug_id(final_url)).upper()
    roles, pathways = curriculum_roles(soup)
    non_course = any(not component.courses for component in audit.components)
    credit_pool = any(component.rule_type == "MINIMUM_CREDITS_FROM_POOL" for component in audit.components)
    identifiable = sorted({course.course_id for component in audit.components for course in component.courses})
    status = "GREEN"
    custom = "none"
    blockers = []
    if not identifiable:
        status = "RED"
        custom = "held: official curriculum publishes no identifiable BCIT course references"
        blockers = ["no identifiable BCIT course references in the published curriculum"]
    elif pathways or non_course or credit_pool:
        status = "YELLOW"
        custom = "existing Batch 01 connector/pathway adapter; no new code"
    campus, delivery = campus_delivery(audit.program_details_raw + " " + audit.overview_raw, study_mode)
    features = []
    if pathways:
        features.append("published alternatives or pathways")
    if credit_pool:
        features.append("credit pool")
    if non_course:
        features.append("non-course component")
    if "clinical" in (audit.program_details_raw + " " + audit.overview_raw).lower():
        features.append("clinical placement")
    shape = credential.lower() if credential else "official non-credential program"
    if features:
        shape += " with " + ", ".join(features)
    elif identifiable:
        shape += " with flat published curriculum"
    return {
        "program_id": canonical_id,
        "program_name": audit.program_name,
        "url": final_url,
        "sitemap_url": clean_url(url),
        "credential": credential,
        "study_mode": study_mode,
        "school": school,
        "shape": shape,
        "campus": campus,
        "delivery": delivery,
        "area": AREA_BY_SCHOOL.get(school, "CE"),
        "level": credential or "Other",
        "status": status,
        "custom": custom,
        "blockers": blockers,
        "course_reference_count": len(identifiable),
    }


def main() -> None:
    xml = requests.get(SITEMAP, timeout=35).content
    root = ElementTree.fromstring(xml)
    urls = [node.text for node in root.findall("{https://www.sitemaps.org/schemas/sitemap/0.9}url/{https://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT program_id, source_url, program_name, credential FROM programs WHERE status='Active'")
        active_rows = cursor.fetchall()
        cursor.execute("SELECT course_id FROM courses")
        existing_course_ids = {row[0] for row in cursor.fetchall()}
    active_ids = {row[0].upper() for row in active_rows}
    active_urls = {clean_url(row[1]) for row in active_rows if row[1]}
    active_name_credentials = {(row[2].strip().casefold(), (row[3] or "").strip().casefold()) for row in active_rows}
    pending = [url for url in urls if slug_id(url) not in active_ids and not slug_id(url).endswith("APPR")]

    inspected, errors = [], []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(inspect, url, existing_course_ids): url for url in pending}
        for future in as_completed(futures):
            try:
                inspected.append(future.result())
            except Exception as exc:
                errors.append({"url": futures[future], "error": str(exc)})

    deduped = {}
    excluded = []
    for item in sorted(inspected, key=lambda row: (row["school"], row["credential"], row["program_id"], row["url"])):
        name_credential = (item["program_name"].strip().casefold(), item["credential"].strip().casefold())
        reason = None
        if item["program_id"] in active_ids:
            reason = "canonical program ID already active after redirect"
        elif item["url"] in active_urls:
            reason = "canonical URL already active after redirect"
        elif name_credential in active_name_credentials:
            reason = "program name and credential already active under an alias"
        elif item["program_id"] in deduped:
            reason = "duplicate canonical program ID in sitemap"
        elif item["url"] in {row["url"] for row in deduped.values()}:
            reason = "duplicate canonical URL in sitemap"
        if reason:
            excluded.append({**item, "exclusion_reason": reason})
        else:
            deduped[item["program_id"]] = item

    pools = defaultdict(list)
    for item in deduped.values():
        pools[item["school"]].append(item)
    for rows in pools.values():
        rows.sort(key=lambda row: (row["status"] == "RED", row["credential"], row["program_id"]))
    selected = []
    while len(selected) < 100:
        added = False
        for school in SCHOOL_ORDER:
            if pools[school] and len(selected) < 100:
                selected.append(pools[school].pop(0))
                added = True
        if not added:
            break
    # Natural RED structures are represented, but do not let no-course records crowd out the batch.
    if not any(row["status"] == "RED" for row in selected):
        red = next((row for row in deduped.values() if row["status"] == "RED"), None)
        if red and selected:
            selected[-1] = red
    selected = sorted({row["program_id"]: row for row in selected}.values(), key=lambda row: row["program_id"])
    result = {
        "sitemap_url": SITEMAP,
        "sitemap_count": len(urls),
        "active_baseline_count": len(active_ids),
        "non_apprenticeship_urls_inspected": len(inspected),
        "inspection_errors": errors,
        "duplicate_or_alias_exclusions": excluded,
        "eligible_count": len(deduped),
        "selected_count": len(selected),
        "selected": selected,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("sitemap_count", "active_baseline_count", "non_apprenticeship_urls_inspected", "eligible_count", "selected_count")}, indent=2))
    counts = defaultdict(int)
    for row in selected:
        counts[(row["school"], row["status"])] += 1
    for key, count in sorted(counts.items()):
        print(key, count)


if __name__ == "__main__":
    main()
