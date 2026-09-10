import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
          select coalesce(f.international_eligibility, '<NULL>'), count(*)
          from programs p left join program_delivery_facts f using (program_id)
          where p.status='Active' group by 1 order by 2 desc, 1
        """)
        print('DELIVERY STATUS COUNTS')
        for r in cur.fetchall(): print(r)
        cur.execute("""
          select table_name, column_name, data_type
          from information_schema.columns
          where table_schema='public' and table_name in
            ('program_offerings','academic_rules','program_delivery_facts','programs')
          order by table_name, ordinal_position
        """)
        print('RELEVANT SCHEMA')
        for r in cur.fetchall(): print(r)
        cur.execute("""
          select p.program_id, p.program_name, p.accepts_international_students,
                 f.international_eligibility, f.source_url
          from programs p left join program_delivery_facts f using(program_id)
          where p.status='Active' and (
            p.accepts_international_students is not null or
            coalesce(f.international_eligibility,'') <> 'Refer to official program page')
          order by p.program_id
        """)
        print('DETERMINATE/LEGACY')
        for r in cur.fetchall(): print(r)
        cur.execute("""
          select program_id, rule_name, study_mode, source_url, notes
          from academic_rule_sets where rule_scope='INTERNATIONAL'
          order by program_id, rule_set_id
        """)
        print('INTERNATIONAL RULE SETS')
        for r in cur.fetchall(): print(r)
