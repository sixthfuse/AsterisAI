import csv
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from database import get_connection

summary = json.loads((root / 'BCIT_INTERNATIONAL_SOURCE_AUDIT.json').read_text(encoding='utf-8'))
with (root / 'program_extractor_audit' / 'international_source_audit' / 'program_coverage.csv').open(encoding='utf-8-sig', newline='') as handle:
    coverage = list(csv.DictReader(handle))
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("select count(*) from programs where status='Active'")
        active = cur.fetchone()[0]
        cur.execute("select count(*) from academic_rule_sets where rule_scope='INTERNATIONAL'")
        international_rule_sets = cur.fetchone()[0]
assert active == 374 == len(coverage)
assert international_rule_sets == 19
assert summary['results']['deterministically_enrichable'] + summary['results']['remain_unknown'] == 374
print({'active_programs': active, 'international_rule_sets_unchanged': international_rule_sets,
       'coverage_rows': len(coverage), 'audit_reconciles': True})
