import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            select table_name, column_name, data_type
            from information_schema.columns
            where table_schema = 'public'
              and (table_name = 'programs' or column_name ilike '%international%')
            order by table_name, ordinal_position
        """)
        for row in cur.fetchall():
            print(row)
        cur.execute("""
            select program_id, program_name, credential, study_mode, source_url,
                   accepts_international_students
            from programs where status = 'Active' order by program_id
        """)
        rows = cur.fetchall()
        print('ACTIVE', len(rows))
        for row in rows[:5]:
            print(row)
        cur.execute("""
            select table_name, column_name, data_type
            from information_schema.columns
            where table_schema = 'public'
              and table_name in ('program_delivery_facts', 'academic_rule_sets', 'academic_rules', 'source_evidence')
            order by table_name, ordinal_position
        """)
        for row in cur.fetchall():
            print('SCHEMA', row)
        cur.execute("""
            select p.program_id, p.program_name, p.accepts_international_students,
                   f.international_eligibility, f.authoritative_raw, f.source_url,
                   f.last_checked
            from programs p
            left join program_delivery_facts f on f.program_id = p.program_id
            where p.status = 'Active'
              and (p.accepts_international_students is not null
                   or f.international_eligibility is not null)
            order by p.program_id
        """)
        for row in cur.fetchall():
            print('INTL', row)
        cur.execute("""
            select program_id, rule_set_id, rule_name, study_mode, source_url, notes
            from academic_rule_sets
            where rule_scope = 'INTERNATIONAL'
            order by program_id, rule_set_id
        """)
        for row in cur.fetchall():
            print('RULESET', row)
