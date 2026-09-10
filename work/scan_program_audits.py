import json
import re
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
latest = {}
for path in (root / 'program_extractor_audit').rglob('*.json'):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        continue
    pid = data.get('program_id') if isinstance(data, dict) else None
    if not pid:
        continue
    stamp = data.get('source_retrieved_at', '')
    if pid.upper() not in latest or stamp > latest[pid.upper()][0]:
        latest[pid.upper()] = (stamp, path, data)

print('program audits', len(latest))
classified = Counter()
examples = {}
for pid, (stamp, path, data) in latest.items():
    sections = data.get('authoritative_sections') or {}
    subs = sections.get('subsections') or {}
    intl = subs.get('International applicants', '')
    admissions = sections.get('admissions', '')
    direct = data.get('international_requirements_raw', '') or ''
    hay = ' '.join([direct, intl, admissions])
    if re.search(r'not available to international (?:students|applicants)', hay, re.I):
        status = 'not_available'
    elif re.search(r'available to international applicants who will complete.*outside Canada.*valid work permit', hay, re.I):
        status = 'conditional_outside_canada_or_work_permit'
    elif re.search(r'(?:program is )?available to international applicants', hay, re.I):
        status = 'available'
    elif direct or intl:
        status = 'other_explicit_section'
    else:
        status = 'no_explicit_section'
    classified[status] += 1
    examples.setdefault(status, (pid, str(path.relative_to(root)), (direct or intl)[:500]))
print(classified)
for k,v in examples.items(): print(k, v)

for pid in ['810ABSN','810BBSN','810CBSN','810DBSN','810FBSN','810GBSN','810HBSN','810KBSN','810MBSN','810NBSN','810QBSN','810SBSN','8875BSN']:
    stamp, path, data = latest[pid]
    subs = (data.get('authoritative_sections') or {}).get('subsections') or {}
    print('NURSING', pid, stamp, subs.get('International applicants','')[:1000])
