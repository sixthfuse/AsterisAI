from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup
import re
import json
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from database import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("select program_id, program_name, source_url from programs where status='Active'")
        db = {r[0].upper(): {'name': r[1], 'url': r[2]} for r in cur.fetchall()}

positive_sets = {}

for filename in ('regular-credential-programs.html', 'flexible-credential-programs.html'):
    soup = BeautifulSoup((root / 'work' / filename).read_text(encoding='utf-8'), 'html.parser')
    anchors = soup.select('a.programslist--link')
    print(filename, 'anchors', len(anchors), 'unique ids', len({a.get('data-id','').upper() for a in anchors}),
          'intl', sum(bool(a.select_one('.available--international')) for a in anchors),
          'pgwp', sum(bool(a.select_one('.available--pgwp')) for a in anchors))
    sections = Counter()
    for a in anchors:
        h = a.find_previous(['h2','h3'])
        sections[h.get_text(' ', strip=True) if h else 'NONE'] += 1
    print('sections', sections)
    positives = {a.get('data-id','').upper() for a in anchors if a.select_one('.available--international')}
    pgwp = {a.get('data-id','').upper() for a in anchors if a.select_one('.available--pgwp')}
    positive_sets[filename] = positives
    print('matched intl', len(positives & db.keys()), 'unmatched intl', sorted(positives - db.keys()))
    print('matched pgwp', len(pgwp & db.keys()), 'unmatched pgwp', sorted(pgwp - db.keys()))
    for a in anchors:
        if not a.select_one('.available--international'):
            h = a.find_previous(['h2','h3'])
            print('NOINTL', a.get('data-id'), a.get('data-name'), h.get_text(' ', strip=True) if h else '')

soup = BeautifulSoup((root / 'work' / 'program-availability.html').read_text(encoding='utf-8'), 'html.parser')
items = soup.select('li.programavailability--list')
print('availability items', len(items))
for item in items[:3]:
    a = item.select_one('a[href]')
    print(a.get('href') if a else None, item.get_text(' ', strip=True)[:300])

availability_ids = []
domestic = []
for item in items:
    a = item.select_one('a[href]')
    if not a:
        continue
    m = re.search(r'-([a-z0-9]+?)/?$', a['href'].rstrip('/') + '/')
    pid = m.group(1).upper() if m else ''
    availability_ids.append(pid)
    fmt = item.select_one('.programavailability__format')
    if fmt and 'Domestic Only' in fmt.get_text(' ', strip=True):
        domestic.append(pid)
print('availability unique', len(set(availability_ids)), 'matched', len(set(availability_ids)&db.keys()),
      'unmatched', sorted(set(availability_ids)-db.keys()))
print('domestic-only rows', len(domestic), 'unique', len(set(domestic)), 'matched', len(set(domestic)&db.keys()))
union = set().union(*positive_sets.values())
print('international union unique', len(union), 'matched', len(union & db.keys()),
      'unmatched', sorted(union-db.keys()), 'db unknown by list', len(db.keys()-union))
