"""
Asteris / BCIT Course Extractor
Phase 1: Build the master course list from BCIT catalogue index pages.
Phase 2: Visit each course page and collect richer course information.

Run:
    python asteris_bcit_course_extractor.py

Requirements:
    pip install requests beautifulsoup4 pandas openpyxl

Output:
    BCIT_Courses_Phase1_2.xlsx

Notes:
- This uses BCIT's public catalogue pages as the source.
- It does NOT try to interpret program rules. That is Phase 5.
- Phase 1 captures the catalogue index: area, subject/category, course name,
  course code, and URL.
- Phase 2 visits each course URL and attempts to capture the page title,
  description, credits, and prerequisite text when present.
- Because website HTML can change, the extractor is deliberately conservative:
  anything it cannot confidently find is left blank rather than invented.
"""

import re
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://www.bcit.ca"

CATALOGUES = {
    "Applied & Natural Sciences": f"{BASE}/study/applied-natural-sciences/courses/",
    "Business & Media": f"{BASE}/study/business-media/courses/",
    "Computing & IT": f"{BASE}/study/computing-it/courses/",
    "Engineering": f"{BASE}/study/engineering/courses/",
    "Health Sciences": f"{BASE}/study/health-sciences/courses/",
    "Trades & Apprenticeships": f"{BASE}/study/trades-apprenticeships/courses/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Asteris BCIT catalogue research; +https://asteristech.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-CA,en;q=0.9",
}

# Keep a pause between successful requests. Retry also applies exponential
# backoff (1, 2, 4, 8 seconds) and honours BCIT's Retry-After header.
REQUEST_DELAY_SECONDS = 0.25
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 30


def build_session():
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        allowed_methods=frozenset({"GET"}),
        status_forcelist=(429, 500, 502, 503, 504),
        backoff_factor=1.0,
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=2)
    new_session = requests.Session()
    new_session.headers.update(HEADERS)
    new_session.mount("https://", adapter)
    new_session.mount("http://", adapter)
    return new_session


session = build_session()


def get_soup(url):
    response = session.get(
        url,
        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def parse_course_text(text):
    # Expected BCIT catalogue pattern:
    # Course Name (ABCD 1234)
    m = re.search(r"\(([^()]*\b[A-Z]{3,5}\s+\d{3,5})\)\s*$", text)
    if not m:
        return None, None
    code = clean(m.group(1))
    name = clean(text[:m.start()].strip())
    return code, name


def phase1():
    rows = []
    for area, url in CATALOGUES.items():
        print("Reading catalogue:", area)
        try:
            soup = get_soup(url)
        except requests.RequestException as error:
            print(f"  WARNING: catalogue skipped after retries: {error}")
            continue

        # BCIT's catalogue uses headings for subject/category and linked
        # course entries beneath them.
        current_subject = ""
        for tag in soup.find_all(["h2", "h3", "li"]):
            if tag.name in ("h2", "h3"):
                current_subject = clean(tag.get_text(" ", strip=True))
                continue

            a = tag.find("a", href=True)
            if not a:
                continue

            href = a.get("href", "")
            if "/courses/" not in href:
                continue

            text = clean(a.get_text(" ", strip=True))
            code, name = parse_course_text(text)
            if not code:
                continue

            course_url = urljoin(BASE, href)
            rows.append({
                "area_of_study": area,
                "subject_category": current_subject,
                "course_code": code,
                "course_name": name,
                "course_url": course_url,
                "source_catalogue_url": url,
            })

        # Be polite to BCIT's public site between catalogue requests too.
        time.sleep(REQUEST_DELAY_SECONDS)

    df = pd.DataFrame(rows)

    # De-duplicate by course code + URL, preserving first occurrence.
    if not df.empty:
        df = df.drop_duplicates(subset=["course_code", "course_url"])
        df = df.sort_values(["area_of_study", "course_code", "course_name"])

    return df.reset_index(drop=True)


def first_matching_text(soup, labels):
    text = soup.get_text("\n", strip=True)
    lines = [clean(x) for x in text.splitlines() if clean(x)]
    for i, line in enumerate(lines):
        low = line.lower()
        if any(low == label.lower() or low.startswith(label.lower()) for label in labels):
            # Return a short window after the label, excluding obvious nav noise.
            window = []
            for nxt in lines[i+1:i+8]:
                if nxt.lower() in {"prerequisite(s):", "credits:", "course outline"}:
                    break
                window.append(nxt)
            if window:
                return " ".join(window[:3])
    return ""


def phase2(df):
    descriptions = []
    credits = []
    prerequisites = []
    titles = []

    for n, row in df.iterrows():
        url = row["course_url"]
        print(f"Phase 2 {n+1}/{len(df)}: {row['course_code']}")
        try:
            soup = get_soup(url)

            h1 = soup.find("h1")
            titles.append(clean(h1.get_text(" ", strip=True)) if h1 else "")

            # Description: use the main content area where possible.
            desc = ""
            for selector in ["main", "article", ".entry-content", ".wp-block-post-content"]:
                node = soup.select_one(selector)
                if node:
                    txt = clean(node.get_text(" ", strip=True))
                    # Avoid returning the entire page if selector is broad.
                    marker = txt.lower().find(row["course_name"].lower())
                    if marker >= 0:
                        desc = txt[marker:marker+2500]
                        break
            descriptions.append(desc)

            # Credits and prerequisites are intentionally conservative.
            full = soup.get_text("\n", strip=True)
            credit_match = re.search(r"\bCredits?\s*:?\s*([0-9]+(?:\.[0-9]+)?)", full, re.I)
            credits.append(credit_match.group(1) if credit_match else "")

            prereq = first_matching_text(soup, ["Prerequisite(s):", "Prerequisites:"])
            prerequisites.append(prereq)

        except requests.RequestException as error:
            print(f"  WARNING: page skipped after retries: {error}")
            titles.append("")
            descriptions.append("")
            credits.append("")
            prerequisites.append("")
        except Exception as error:
            # A malformed or changed page should not stop the remaining courses.
            print(f"  WARNING: could not parse page: {error}")
            titles.append("")
            descriptions.append("")
            credits.append("")
            prerequisites.append("")

        # Be polite to BCIT's public site.
        time.sleep(REQUEST_DELAY_SECONDS)

    out = df.copy()
    out["page_title"] = titles
    out["description_raw"] = descriptions
    out["credits"] = credits
    out["prerequisites_raw"] = prerequisites
    return out


def main():
    df1 = phase1()
    print("\nPhase 1 courses found:", len(df1))

    df2 = phase2(df1)

    output = "BCIT_Courses_Phase1_2.xlsx"
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name="Phase1_Master_Courses", index=False)
        df2.to_excel(writer, sheet_name="Phase2_Course_Details", index=False)

        summary = pd.DataFrame([
            ["Source", "BCIT public course catalogue pages"],
            ["Phase 1", "Course code, course name, category, area, URL"],
            ["Phase 2", "Page title, description, credits, prerequisite text"],
            ["Important", "Blank fields mean the extractor did not confidently find the value."],
            ["Next", "Human review/cleanup, then import to PostgreSQL."],
        ], columns=["Item", "Value"])
        summary.to_excel(writer, sheet_name="README", index=False)

    print("\nDone:", output)


if __name__ == "__main__":
    main()
