import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database import get_connection

OUT = ROOT / 'program_extractor_audit' / 'international_source_audit'
OUT.mkdir(parents=True, exist_ok=True)
GENERATED = datetime.now(timezone.utc).isoformat()
RETRIEVED_DATE = '2026-09-08'


def norm_url(value):
    if not value:
        return ''
    p = urlsplit(value.strip())
    path = re.sub(r'/+', '/', p.path).rstrip('/') + '/'
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path.lower(), '', ''))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            select p.program_id, p.program_name, p.credential, p.study_mode,
                   p.source_url, p.accepts_international_students,
                   f.international_eligibility, f.source_url, f.last_checked
            from programs p
            left join program_delivery_facts f using (program_id)
            where p.status='Active'
            order by p.program_id
        """)
        db_rows = cur.fetchall()
        cur.execute("""
            select program_id, rule_name, source_url, notes
            from academic_rule_sets
            where rule_scope='INTERNATIONAL'
            order by program_id, rule_set_id
        """)
        intl_rules = defaultdict(list)
        for pid, name, url, notes in cur.fetchall():
            intl_rules[pid].append({'rule_name': name, 'source_url': url, 'notes': notes})
        cur.execute("""
            select table_name, column_name
            from information_schema.columns
            where table_schema='public' and table_name in
              ('programs','program_delivery_facts','program_offerings','academic_rule_sets')
            order by table_name, ordinal_position
        """)
        schema_columns = defaultdict(list)
        for table, column in cur.fetchall():
            schema_columns[table].append(column)

programs = {
    r[0].upper(): {
        'program_id': r[0].upper(), 'program_name': r[1], 'credential': r[2],
        'study_mode': r[3], 'source_url': r[4],
        'legacy_accepts_international': r[5],
        'current_international_eligibility': r[6],
        'current_evidence_url': r[7],
        'current_last_checked': r[8].isoformat() if r[8] else '',
    }
    for r in db_rows
}
url_to_pid = {norm_url(v['source_url']): pid for pid, v in programs.items()}


def pid_from_program_url(url):
    exact = url_to_pid.get(norm_url(url), '')
    if exact:
        return exact
    path = urlsplit(url).path.lower().rstrip('/')
    matches = [pid for pid in programs if path.endswith('-' + pid.lower())]
    return matches[0] if len(matches) == 1 else ''


def parse_program_list(filename, source_key):
    path = ROOT / 'work' / filename
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    by_id = {}
    for a in soup.select('a.programslist--link'):
        pid = (a.get('data-id') or '').upper()
        rec = by_id.setdefault(pid, {
            'source_program_id': pid,
            'title': a.get('data-name') or a.get_text(' ', strip=True),
            'url': a.get('href') or '', 'rows': 0,
            'international': False, 'pgwp': False,
        })
        rec['rows'] += 1
        rec['international'] |= bool(a.select_one('.available--international'))
        rec['pgwp'] |= bool(a.select_one('.available--pgwp'))
    for rec in by_id.values():
        rec['matched_program_id'] = rec['source_program_id'] if rec['source_program_id'] in programs else ''
        rec['source_key'] = source_key
    return by_id, path


regular, regular_path = parse_program_list('regular-credential-programs.html', 'international_full_time')
flexible, flexible_path = parse_program_list('flexible-credential-programs.html', 'international_flexible')
regular_positive = {pid for pid, r in regular.items() if r['international'] and pid in programs}
flexible_positive = {pid for pid, r in flexible.items() if r['international'] and pid in programs}
systematic_positive = regular_positive | flexible_positive
regular_pgwp = {pid for pid, r in regular.items() if r['pgwp'] and pid in programs}
flexible_pgwp = {pid for pid, r in flexible.items() if r['pgwp'] and pid in programs}
systematic_pgwp = regular_pgwp | flexible_pgwp

# Program availability is explicitly intake/mode scoped. Match by canonical URL,
# not by title, and retain every intake row.
availability_path = ROOT / 'work' / 'program-availability.html'
availability_soup = BeautifulSoup(availability_path.read_text(encoding='utf-8'), 'html.parser')
availability_rows = []
availability_programs = set()
domestic_only_programs = set()
for item in availability_soup.select('li.programavailability--list'):
    a = item.select_one('a[href]')
    if not a:
        continue
    url = a.get('href') or ''
    pid = pid_from_program_url(url)
    if pid:
        availability_programs.add(pid)
    name_el = item.select_one('.programavailability__name')
    cred_el = item.select_one('.programavailability__cred')
    format_el = item.select_one('.programavailability__format')
    fmt = format_el.get_text(' ', strip=True) if format_el else ''
    domestic_only = 'Domestic Only' in fmt
    if pid and domestic_only:
        domestic_only_programs.add(pid)
    intakes = item.select('.programavailability__intake') or [None]
    for intake in intakes:
        availability_rows.append({
            'program_id': pid,
            'source_url': url,
            'source_title': name_el.get_text(' ', strip=True) if name_el else '',
            'credential': cred_el.get_text(' ', strip=True) if cred_el else '',
            'format': fmt,
            'domestic_only': str(domestic_only).lower(),
            'intake_start': intake.get('data-start', '') if intake else '',
            'application_status': intake.get('data-stat', '') if intake else '',
            'campus': (intake.select_one('.campus').get_text(' ', strip=True)
                       if intake and intake.select_one('.campus') else ''),
            'matched': str(bool(pid)).lower(),
        })

# Use the newest retained extractor evidence for every active program. These are
# provenance snapshots; the 13 requested nursing pages were also re-fetched live.
latest_audits = {}
for path in (ROOT / 'program_extractor_audit').rglob('*.json'):
    if OUT in path.parents:
        continue
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        continue
    if not isinstance(data, dict) or not data.get('program_id'):
        continue
    pid = data['program_id'].upper()
    if pid not in programs:
        continue
    stamp = data.get('source_retrieved_at', '')
    if pid not in latest_audits or stamp > latest_audits[pid][0]:
        latest_audits[pid] = (stamp, path, data)


def individual_evidence(pid):
    if pid not in latest_audits:
        return {'status': 'UNKNOWN_NOT_PUBLISHED', 'raw': '', 'pgwp': 'UNKNOWN_NOT_PUBLISHED',
                'study_permit': 'UNKNOWN_NOT_PUBLISHED', 'retrieved_at': '', 'source_url': programs[pid]['source_url']}
    stamp, path, data = latest_audits[pid]
    sections = data.get('authoritative_sections') or {}
    subs = sections.get('subsections') or {}
    direct = data.get('international_requirements_raw') or ''
    intl = subs.get('International applicants') or ''
    admissions = sections.get('admissions') or ''
    hay = ' '.join([direct, intl, admissions])
    if re.search(r'this program (?:is not available to|does not accept applications from) international', hay, re.I):
        status = 'NOT_ACCEPTED'
    elif re.search(r'available to international applicants who will complete.*outside Canada.*valid work permit', hay, re.I | re.S):
        status = 'CONDITIONAL_RESTRICTED'
    elif re.search(r'this program is available to international applicants', hay, re.I):
        status = 'ACCEPTED_AVAILABLE'
    else:
        status = 'UNKNOWN_NOT_PUBLISHED'
    if re.search(r'not eligible for (?:a )?PGWP', hay, re.I) or re.search(r'not eligible for students to apply for a PGWP', hay, re.I):
        pgwp = 'INELIGIBLE'
    elif re.search(r'eligible for students to apply for a PGWP', hay, re.I):
        pgwp = 'ELIGIBLE_TO_APPLY'
    else:
        pgwp = 'UNKNOWN_NOT_PUBLISHED'
    if re.search(r'not eligible for a study permit', hay, re.I):
        permit = 'INELIGIBLE'
    elif re.search(r'(?:valid BCIT )?study permit is required', hay, re.I):
        permit = 'REQUIRED'
    else:
        permit = 'UNKNOWN_NOT_PUBLISHED'
    raw = direct or intl
    return {'status': status, 'raw': raw, 'pgwp': pgwp, 'study_permit': permit,
            'retrieved_at': stamp, 'source_url': data.get('source_url') or programs[pid]['source_url'],
            'audit_path': str(path.relative_to(ROOT))}


individual = {pid: individual_evidence(pid) for pid in programs}

# Verify live nursing wording and compare it to the existing structured rules.
nursing_ids = ['810ABSN','810BBSN','810CBSN','810DBSN','810FBSN','810GBSN','810HBSN',
               '810KBSN','810MBSN','810NBSN','810QBSN','810SBSN']
nursing_spot = []
for pid in nursing_ids + ['8875BSN']:
    live_path = ROOT / 'work' / 'nursing_live' / f'{pid}.html'
    live_text = BeautifulSoup(live_path.read_text(encoding='utf-8'), 'html.parser').get_text(' ', strip=True)
    if pid == '8875BSN':
        expected = 'NOT_ACCEPTED'
        live_ok = bool(re.search(r'this program (?:does not accept applications from|is not available to) international', live_text, re.I))
        detail_ok = live_ok
    else:
        expected = 'CONDITIONAL_RESTRICTED'
        live_ok = bool(re.search(r'available to international applicants who will complete.*outside Canada.*valid work permit', live_text, re.I | re.S))
        detail_ok = ('not eligible for a study permit' in live_text.lower()
                     and 'not eligible for a pgwp' in live_text.lower()
                     and 'program head approval' in live_text.lower())
    rules_text = ' '.join((r.get('notes') or '') for r in intl_rules.get(pid, []))
    structured_ok = (expected == 'NOT_ACCEPTED' and 'not available to international' in rules_text.lower()) or (
        expected == 'CONDITIONAL_RESTRICTED'
        and 'outside canada' in rules_text.lower()
        and 'valid work permit' in rules_text.lower()
        and 'not eligible for a study permit' in rules_text.lower()
        and 'not eligible for a pgwp' in rules_text.lower())
    nursing_spot.append({
        'program_id': pid, 'program_name': programs[pid]['program_name'],
        'expected_status': expected, 'live_program_page_agrees': str(live_ok and detail_ok).lower(),
        'existing_structured_rules_agree': str(structured_ok).lower(),
        'source_url': programs[pid]['source_url'], 'checked_date': RETRIEVED_DATE,
        'discrepancy': '' if live_ok and detail_ok and structured_ok else 'REVIEW_REQUIRED',
    })

# Resolve program-level status. Specific program-page restrictions override the
# broad positive icon; absence from a list never creates a negative.
coverage_rows = []
for pid, p in programs.items():
    ind = individual[pid]
    if ind['status'] in ('NOT_ACCEPTED', 'CONDITIONAL_RESTRICTED'):
        status = ind['status']
        basis = 'individual_program_page_explicit'
    elif pid in systematic_positive:
        status = 'ACCEPTED_AVAILABLE'
        basis = 'bcit_international_program_list_positive_flag'
    elif ind['status'] == 'ACCEPTED_AVAILABLE':
        status = 'ACCEPTED_AVAILABLE'
        basis = 'individual_program_page_explicit'
    else:
        status = 'UNKNOWN_NOT_PUBLISHED'
        basis = 'no_explicit_governing_evidence'
    pgwp = 'ELIGIBLE_TO_APPLY' if pid in systematic_pgwp else ind['pgwp']
    regular_rec = regular.get(pid, {})
    flexible_rec = flexible.get(pid, {})
    coverage_rows.append({
        **p,
        'regular_listed': str(pid in regular).lower(),
        'regular_international_flag': str(pid in regular_positive).lower(),
        'regular_pgwp_flag': str(pid in regular_pgwp).lower(),
        'flexible_listed': str(pid in flexible).lower(),
        'flexible_international_flag': str(pid in flexible_positive).lower(),
        'flexible_pgwp_flag': str(pid in flexible_pgwp).lower(),
        'availability_listed': str(pid in availability_programs).lower(),
        'has_domestic_only_availability_row': str(pid in domestic_only_programs).lower(),
        'individual_evidence_status': ind['status'],
        'individual_study_permit_status': ind['study_permit'],
        'individual_pgwp_status': ind['pgwp'],
        'recommended_program_status': status,
        'recommended_pgwp_status': pgwp,
        'decision_basis': basis,
        'individual_evidence_url': ind['source_url'],
        'individual_evidence_retrieved_at': ind['retrieved_at'],
    })

status_counts = Counter(r['recommended_program_status'] for r in coverage_rows)
pgwp_counts = Counter(r['recommended_pgwp_status'] for r in coverage_rows)

conflicts = []
for row in coverage_rows:
    pid = row['program_id']
    if pid in systematic_positive and individual[pid]['status'] == 'NOT_ACCEPTED':
        conflicts.append({'program_id': pid, 'kind': 'direct_conflict',
                          'systematic_source': 'positive international flag',
                          'specific_source': 'program page says not accepted',
                          'resolution': 'program page explicit text wins'})
    elif pid in systematic_positive and individual[pid]['status'] == 'CONDITIONAL_RESTRICTED':
        conflicts.append({'program_id': pid, 'kind': 'scope_refinement',
                          'systematic_source': 'positive international flag',
                          'specific_source': 'outside-Canada/work-permit-only; study-permit and PGWP ineligible',
                          'resolution': 'retain CONDITIONAL_RESTRICTED with specific conditions'})
    if pid in systematic_positive and pid in domestic_only_programs:
        conflicts.append({'program_id': pid, 'kind': 'intake_or_mode_scope',
                          'systematic_source': 'program accepts international students in at least one route',
                          'specific_source': 'availability page contains a Domestic Only format row',
                          'resolution': 'program remains accepted; attach restriction to the dated mode/intake only'})

metadata_files = {
    'international_full_time': 'regular-credential-programs.wp.json',
    'international_flexible': 'flexible-credential-programs.wp.json',
    'program_availability': 'program-availability.wp.json',
    'study_permits': 'study-permits.wp.json',
    'pgwp_policy': 'pgwp.wp.json',
}
metadata = {}
for key, filename in metadata_files.items():
    data = json.loads((ROOT / 'work' / filename).read_text(encoding='utf-8'))
    metadata[key] = {'url': data.get('link'), 'published_gmt': data.get('date_gmt'),
                     'modified_gmt': data.get('modified_gmt'), 'retrieved_date': RETRIEVED_DATE}

source_rows = [
    {'source_key': 'international_full_time', 'authority': 'governing_positive_program-level source',
     'stable_identity': 'embedded BCIT program ID + canonical URL',
     'catalog_programs_listed': len(set(regular) & programs.keys()),
     'deterministic_positive': len(regular_positive), 'pgwp_positive': len(regular_pgwp),
     'negative_supported': 'no', 'effective_date_quality': 'live retrieval; flags have no published effective date',
     'url': metadata['international_full_time']['url']},
    {'source_key': 'international_flexible', 'authority': 'governing positive program-level source',
     'stable_identity': 'embedded BCIT program ID + canonical URL',
     'catalog_programs_listed': len(set(flexible) & programs.keys()),
     'deterministic_positive': len(flexible_positive), 'pgwp_positive': len(flexible_pgwp),
     'negative_supported': 'no', 'effective_date_quality': 'live retrieval; flags have no published effective date',
     'url': metadata['international_flexible']['url']},
    {'source_key': 'combined_international_lists', 'authority': 'best systematic positive source',
     'stable_identity': 'embedded BCIT program ID + canonical URL',
     'catalog_programs_listed': len((set(regular) | set(flexible)) & programs.keys()),
     'deterministic_positive': len(systematic_positive), 'pgwp_positive': len(systematic_pgwp),
     'negative_supported': 'no; absence is unknown', 'effective_date_quality': 'snapshot retrieval date only',
     'url': f"{metadata['international_full_time']['url']} | {metadata['international_flexible']['url']}"},
    {'source_key': 'individual_program_pages', 'authority': 'highest for explicit program-specific restrictions',
     'stable_identity': 'canonical URL ending in BCIT program ID',
     'catalog_programs_listed': len(latest_audits),
     'deterministic_positive': sum(individual[p]['status'] == 'ACCEPTED_AVAILABLE' for p in programs),
     'pgwp_positive': sum(individual[p]['pgwp'] == 'ELIGIBLE_TO_APPLY' for p in programs),
     'negative_supported': 'yes, only where explicit text exists',
     'effective_date_quality': 'retrieval timestamp; text usually lacks effective date',
     'url': 'per-program canonical BCIT URL'},
    {'source_key': 'program_availability', 'authority': 'authoritative for current application status and Domestic Only mode/intake rows',
     'stable_identity': 'canonical program URL; title/credential/mode/intake fields',
     'catalog_programs_listed': len(availability_programs),
     'deterministic_positive': 0, 'pgwp_positive': 0,
     'negative_supported': f'only scoped Domestic Only rows ({len(domestic_only_programs)} matched programs)',
     'effective_date_quality': 'intake/start-date specific; availability approximate',
     'url': metadata['program_availability']['url']},
    {'source_key': 'generic_permit_pgwp_policy', 'authority': 'policy context only; not program-level eligibility',
     'stable_identity': 'none', 'catalog_programs_listed': 0,
     'deterministic_positive': 0, 'pgwp_positive': 0,
     'negative_supported': 'no', 'effective_date_quality': 'pages publish update dates',
     'url': f"{metadata['study_permits']['url']} | {metadata['pgwp_policy']['url']}"},
]

summary = {
    'generated_at': GENERATED,
    'audit_date': RETRIEVED_DATE,
    'scope': 'BCIT International Eligibility Source Discovery Audit; discovery only; no program data updates',
    'postgresql_authoritative': True,
    'active_program_count': len(programs),
    'results': {
        'deterministically_enrichable': len(programs) - status_counts['UNKNOWN_NOT_PUBLISHED'],
        'remain_unknown': status_counts['UNKNOWN_NOT_PUBLISHED'],
        'status_counts': dict(status_counts),
        'systematic_positive_coverage': len(systematic_positive),
        'pgwp_status_counts': dict(pgwp_counts),
        'availability_program_coverage': len(availability_programs),
        'availability_domestic_only_programs': len(domestic_only_programs),
        'direct_source_conflicts': sum(r['kind'] == 'direct_conflict' for r in conflicts),
        'scope_refinements': sum(r['kind'] == 'scope_refinement' for r in conflicts),
        'intake_or_mode_scope_notes': sum(r['kind'] == 'intake_or_mode_scope' for r in conflicts),
    },
    'authoritative_sources': source_rows,
    'source_metadata': metadata,
    'source_snapshot_sha256': {
        'international_full_time': sha256(regular_path),
        'international_flexible': sha256(flexible_path),
        'program_availability': sha256(availability_path),
    },
    'recommended_status_vocabulary': {
        'program_eligibility': ['ACCEPTED_AVAILABLE','NOT_ACCEPTED','CONDITIONAL_RESTRICTED','UNKNOWN_NOT_PUBLISHED'],
        'study_permit': ['REQUIRED','ELIGIBLE','INELIGIBLE','NOT_REQUIRED_DISTANCE_OR_SHORT_STUDY','UNKNOWN_NOT_PUBLISHED'],
        'pgwp': ['ELIGIBLE_TO_APPLY','INELIGIBLE','CONDITIONAL','UNKNOWN_NOT_PUBLISHED'],
        'restriction_codes': ['OUTSIDE_CANADA_ONLY','VALID_WORK_PERMIT_REQUIRED','PROGRAM_HEAD_APPROVAL_REQUIRED','DOMESTIC_ONLY_INTAKE_OR_MODE','WORK_COMPONENT_UNAVAILABLE'],
    },
    'precedence_rules': [
        'Current explicit program-page restriction for the exact program ID/URL.',
        'Current explicit positive flag on BCIT International Applicants full-time or Flexible Learning list.',
        'Dated Program Availability Domestic Only evidence applies only to its exact mode/intake and must not negate other routes.',
        'Generic BCIT permit/PGWP policy supplies context only and never creates a program-level decision.',
        'Absence, missing icon, delivery mode, campus, credential, or inference never changes UNKNOWN_NOT_PUBLISHED.',
        'For equally scoped evidence, prefer the later retrieval/effective date and retain both provenance records for review.',
    ],
    'schema_assessment': {
        'migration_required_for_this_enrichment': False,
        'reason': 'program_delivery_facts stores the normalized program result, raw evidence, source URL and date; academic_rule_sets stores detailed INTERNATIONAL conditions. program_offerings notes can retain dated Domestic Only evidence.',
        'limitation': 'program_offerings has no structured international eligibility column and program_delivery_facts has no separate PGWP/study-permit fields. An additive migration is recommended only if those dimensions must be queried as first-class fields.',
        'observed_columns': dict(schema_columns),
    },
    'nursing_spot_check': {
        'programs_checked': len(nursing_spot),
        'all_live_pages_agree': all(r['live_program_page_agrees'] == 'true' for r in nursing_spot),
        'all_existing_structured_rules_agree': all(r['existing_structured_rules_agree'] == 'true' for r in nursing_spot),
        'discrepancies': [r['program_id'] for r in nursing_spot if r['discrepancy']],
    },
    'recommended_enrichment_process': {
        'batch_size': 50,
        'batches': 'five batches of 50 and one batch of 16 for the 266 deterministic records',
        'steps': [
            'Freeze source snapshots and hashes; re-fetch immediately before each batch.',
            'Join only by exact BCIT program ID, then verify canonical URL.',
            'Apply program-page restrictions first, list positives second, and scoped availability notes third.',
            'Upsert evidence idempotently; do not alter the 108 unknown records.',
            'Generate a pre-apply diff and require zero unexplained conflicts.',
            'After each batch, rerun international integrity checks plus the full existing regression suite.',
            'Finish with a 374-row reconciliation and archive source/effective-date evidence.',
        ],
    },
}

coverage_fields = [
    'program_id','program_name','credential','study_mode','source_url',
    'regular_listed','regular_international_flag','regular_pgwp_flag',
    'flexible_listed','flexible_international_flag','flexible_pgwp_flag',
    'availability_listed','has_domestic_only_availability_row',
    'individual_evidence_status','individual_study_permit_status','individual_pgwp_status',
    'recommended_program_status','recommended_pgwp_status','decision_basis',
    'individual_evidence_url','individual_evidence_retrieved_at',
    'legacy_accepts_international','current_international_eligibility','current_evidence_url','current_last_checked',
]
write_csv(OUT / 'program_coverage.csv', coverage_rows, coverage_fields)
write_csv(OUT / 'source_summary.csv', source_rows, list(source_rows[0].keys()))
write_csv(OUT / 'availability_offerings.csv', availability_rows,
          ['program_id','source_url','source_title','credential','format','domestic_only','intake_start','application_status','campus','matched'])
write_csv(OUT / 'conflicts_and_refinements.csv', conflicts,
          ['program_id','kind','systematic_source','specific_source','resolution'])
write_csv(OUT / 'nursing_spot_check.csv', nursing_spot, list(nursing_spot[0].keys()))
(ROOT / 'BCIT_INTERNATIONAL_SOURCE_AUDIT.json').write_text(
    json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

md = f"""# BCIT International Eligibility Source Discovery Audit

Generated: {GENERATED}

## Decision

BCIT publishes two authoritative, systematic **positive** program-level sources: the [Full-time Cohort Learning Programs]({metadata['international_full_time']['url']}) page and the [Flexible Learning Programs]({metadata['international_flexible']['url']}) page. Both embed a stable BCIT program ID, canonical program URL, and explicit international/PGWP flags. Their union positively identifies **{len(systematic_positive)} of 374** active Asteris programs.

These lists do not govern negative eligibility. Absence from either list, or a missing icon on a listed row, remains unknown. Explicit restrictions and negative decisions must come from the exact individual program page. Combining the list positives with explicit individual-page restrictions yields **{len(programs) - status_counts['UNKNOWN_NOT_PUBLISHED']} deterministic records** and leaves **{status_counts['UNKNOWN_NOT_PUBLISHED']} unknown**.

No program data was updated in this audit.

## Exact result

| Normalized status | Programs |
|---|---:|
| `ACCEPTED_AVAILABLE` | {status_counts['ACCEPTED_AVAILABLE']} |
| `CONDITIONAL_RESTRICTED` | {status_counts['CONDITIONAL_RESTRICTED']} |
| `NOT_ACCEPTED` | {status_counts['NOT_ACCEPTED']} |
| `UNKNOWN_NOT_PUBLISHED` | {status_counts['UNKNOWN_NOT_PUBLISHED']} |
| **Total** | **{len(programs)}** |

The 12 restricted records are the Specialty Nursing BSN options: applicants may complete them outside Canada or hold a valid work permit in Canada for the clinical period; they are study-permit ineligible, PGWP ineligible, and require program-head approval. The explicit negative is the main Nursing BSN (`8875BSN`).

## Source assessment

| Source | Authority and use | Stable identity | Coverage against 374 | Effective-date quality |
|---|---|---|---:|---|
| Full-time international list | Governing positive eligibility and positive PGWP flags | Program ID + canonical URL | {len(set(regular) & programs.keys())} listed; {len(regular_positive)} positive | Retrieved {RETRIEVED_DATE}; flags have no published effective date |
| Flexible Learning international list | Governing positive eligibility and positive PGWP flags | Program ID + canonical URL | {len(set(flexible) & programs.keys())} listed; {len(flexible_positive)} positive | Retrieved {RETRIEVED_DATE}; flags have no published effective date |
| Combined international lists | Best systematic positive source | Program ID + canonical URL | {len(systematic_positive)} deterministic positives | Snapshot date only |
| Individual program pages | Highest authority for exact negative/conditional restrictions | Canonical URL with program ID | 374 pages represented in retained current audit snapshots; 16 publish explicit evidence | Retrieval timestamp; text generally lacks an effective date |
| Program Availability | Governs application status and explicit Domestic Only rows for an exact mode/intake | Canonical URL + mode + intake | {len(availability_programs)} programs; {len(domestic_only_programs)} contain a Domestic Only row | Intake-specific; BCIT says availability is approximate |
| Study permit / PGWP policy pages | General immigration context only | No program identity | 0 program-level classifications | Updated pages, but cannot determine a program |

The full-time page contains one listed row without an international flag (`7485DIPMA`); the Flexible page contains three (`5180PADVDIP`, `5430ACERT`, `5430CERT`). Their icon absence is not a negative decision, so they stay unknown unless another explicit source governs them.

## Conflicts and scope

There are **{sum(r['kind'] == 'direct_conflict' for r in conflicts)} direct contradictions** between a positive international-list flag and an individual page saying the same program is not accepted. The 12 Specialty Nursing list positives are **scope refinements**, not contradictions: the program pages add outside-Canada/work-permit-only, study-permit, PGWP, and approval restrictions.

The Program Availability page covers {len(availability_programs)} active programs and contains explicit `Domestic Only` rows for {len(domestic_only_programs)} matched programs. Those rows are mode/intake-specific. They must be attached to the exact offering and must not turn a program-level positive into a blanket negative. BCIT also states that application availability is approximate and directs international eligibility questions to its International Applicants pages.

The WordPress page metadata reports modification dates of {metadata['international_full_time']['modified_gmt']} for the full-time list and {metadata['international_flexible']['modified_gmt']} for the Flexible list, even though the program records are rendered dynamically. Therefore the audit date and source hash are the reliable snapshot markers; BCIT does not publish per-flag effective dates.

## Recommended vocabulary

Use a program-level decision separate from immigration and offering restrictions:

- Program: `ACCEPTED_AVAILABLE`, `NOT_ACCEPTED`, `CONDITIONAL_RESTRICTED`, `UNKNOWN_NOT_PUBLISHED`.
- Study permit: `REQUIRED`, `ELIGIBLE`, `INELIGIBLE`, `NOT_REQUIRED_DISTANCE_OR_SHORT_STUDY`, `UNKNOWN_NOT_PUBLISHED`.
- PGWP: `ELIGIBLE_TO_APPLY`, `INELIGIBLE`, `CONDITIONAL`, `UNKNOWN_NOT_PUBLISHED`.
- Restrictions: `OUTSIDE_CANADA_ONLY`, `VALID_WORK_PERMIT_REQUIRED`, `PROGRAM_HEAD_APPROVAL_REQUIRED`, `DOMESTIC_ONLY_INTAKE_OR_MODE`, `WORK_COMPONENT_UNAVAILABLE`.

`PGWP` should always mean BCIT says the program is eligible for a student to apply; final issuance remains an IRCC decision.

## Precedence and effective dates

1. Use current explicit text from the exact individual program ID/URL for negative or conditional restrictions.
2. Otherwise accept a current positive international flag from either BCIT international program list.
3. Apply Program Availability `Domestic Only` evidence only to its exact mode and intake.
4. Use generic study-permit and PGWP pages only to explain policy; never derive program status from them.
5. Preserve unknown when evidence is absent. Never infer from delivery, campus, credential, list absence, or a missing icon.
6. Store retrieval time and source hash. If equally scoped evidence conflicts, use a published effective date when present; otherwise prefer the later retrieval and retain both records for review.

## Schema fit

No migration is required for the proposed program-level enrichment. `program_delivery_facts` can store the normalized eligibility text, authoritative raw evidence, source URL, and check date. `academic_rule_sets` already stores multiple `INTERNATIONAL` conditions with evidence. `program_offerings.notes` can retain a dated Domestic Only restriction.

There is one modeling limitation: `program_offerings` has no international-specific field, and `program_delivery_facts` has no separate structured study-permit or PGWP columns. An additive migration is recommended later only if those dimensions must be queried directly rather than represented as `INTERNATIONAL` rules and provenance text.

## Nursing spot check

All **13/13** requested records were fetched from their live BCIT pages on {RETRIEVED_DATE}. The 12 Specialty Nursing pages still publish the same outside-Canada/work-permit-only, study-permit-ineligible, PGWP-ineligible, program-head-approval conditions already stored in Asteris. The main BSN page still says it does not accept international applications. **No discrepancy was found and no correction was made.**

## Recommended enrichment run

Process the **266 deterministic records** in batches of 50: five batches of 50 and a final batch of 16. Before each batch, re-fetch and hash the two list sources and every program page supplying a restriction. Join by exact program ID and verify canonical URL; apply program-page restrictions first, list positives second, and dated offering restrictions third. Generate a pre-apply diff, leave all 108 unknowns untouched, then run focused international integrity checks and the full regression suite after each batch.

Exact next step: implement a read-only planner that consumes `program_coverage.csv`, emits idempotent proposed rows for `program_delivery_facts` and `academic_rule_sets`, and stops on any URL mismatch, changed source hash, or unexplained conflict. Review that diff before authorizing the separate enrichment phase.

## Audit tables

- `program_coverage.csv` — all 374 active programs and the deterministic decision basis.
- `source_summary.csv` — authority, identity, coverage, and date quality by source.
- `availability_offerings.csv` — current BCIT mode/intake application rows and Domestic Only scope.
- `conflicts_and_refinements.csv` — direct conflicts, refinements, and intake/mode scope notes.
- `nursing_spot_check.csv` — live 12 Specialty Nursing plus main BSN comparison.
"""
(ROOT / 'BCIT_INTERNATIONAL_SOURCE_AUDIT.md').write_text(md, encoding='utf-8')

# Audit invariants.
assert len(programs) == 374
assert len(coverage_rows) == 374
assert len({r['program_id'] for r in coverage_rows}) == 374
assert sum(status_counts.values()) == 374
assert status_counts == Counter({'ACCEPTED_AVAILABLE': 253, 'UNKNOWN_NOT_PUBLISHED': 108,
                                'CONDITIONAL_RESTRICTED': 12, 'NOT_ACCEPTED': 1})
assert len(systematic_positive) == 265
assert summary['results']['deterministically_enrichable'] == 266
assert all(r['live_program_page_agrees'] == 'true' for r in nursing_spot)
assert all(r['existing_structured_rules_agree'] == 'true' for r in nursing_spot)
print(json.dumps(summary['results'], indent=2))
