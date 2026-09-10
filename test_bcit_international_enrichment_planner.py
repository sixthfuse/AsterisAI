import copy
import json
import unittest
from pathlib import Path
import bcit_international_enrichment_planner as p

class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=json.loads((p.OUT/'input_snapshot.json').read_text(encoding='utf-8'))
        cls.coverage=p.rows(p.AUDIT/'program_coverage.csv')
        cls.availability=p.rows(p.AUDIT/'availability_offerings.csv')
        cls.conflicts=p.rows(p.AUDIT/'conflicts_and_refinements.csv')
        # Parse verified captured lists with the current parser, independent of old derived cache.
        for key in p.LISTS:
            s=cls.inputs['sources'][key]
            if not s['error']:
                s['records']=p.list_records((p.ROOT/s['live_path']).read_bytes())
    def plan(self,db=None,sources=None,coverage=None):
        return p.build_plan(coverage or self.coverage,db or self.inputs['db'],sources or self.inputs['sources'],self.availability,self.conflicts)
    def test_fixed_inputs_deterministic(self):
        self.assertEqual(p.packed(self.plan()),p.packed(self.plan()))
    def test_unknowns_never_have_actions(self):
        plan=self.plan(); self.assertEqual(108,len(plan['unknown_programs']))
        self.assertTrue(all(not e['proposed_db_actions'] for e in plan['unknown_programs']))
    def test_canonicalized_nursing_urls_converge(self):
        plan=self.plan()
        for pid in ('810BBSN','810CBSN','810KBSN','810NBSN'):
            e=next(e for e in plan['proposed_programs'] if e['program_id']==pid)
            self.assertEqual('UNCHANGED',e['action']); self.assertFalse(e['proposed_db_actions'])
    def test_url_mismatch_blocks(self):
        db=copy.deepcopy(self.inputs['db']); target=next(x for x in db['programs'] if x['program_id']=='0800CM'); target['source_url']='https://www.bcit.ca/programs/wrong-0800cm/'
        self.assertEqual('SKIP',next(e for e in self.plan(db=db)['proposed_programs'] if e['program_id']=='0800CM')['action'])
    def test_source_failure_blocks(self):
        sources=copy.deepcopy(self.inputs['sources']); sources['international_flexible']['error']='Unexplained source change'
        e=next(e for e in self.plan(sources=sources)['proposed_programs'] if e['program_id']=='0800CM')
        self.assertEqual('SKIP',e['action']); self.assertFalse(e['proposed_db_actions'])
    def test_duplicate_conflicting_list_id_rejected(self):
        body=b'<a class="programslist--link" data-id="x" href="https://www.bcit.ca/programs/a-x/"><i class="available--international"></i></a><a class="programslist--link" data-id="X" href="https://www.bcit.ca/programs/b-x/"></a>'
        with self.assertRaises(ValueError): p.list_records(body)
    def test_narrow_timestamp_exception(self):
        a=b'x<!-- Last generated: September 8, 2026 at 10:14:35 -->y'
        b=b'x<!-- Last generated: September 8, 2026 at 10:35:37 -->y'
        self.assertEqual(p.stable_source_bytes(a),p.stable_source_bytes(b))
        self.assertNotEqual(p.stable_source_bytes(a),p.stable_source_bytes(b.replace(b'x',b'z')))
    def test_work_term_restriction_is_not_program_negative(self):
        self.assertEqual(p.UNKNOWN,p.status_from_text('FMGT courses are not available to international students.'))
        self.assertEqual('ACCEPTED_AVAILABLE',p.status_from_text('This program is available to international applicants. Courses are not available to international students.'))
    def test_nursing_existing_rules_not_duplicated(self):
        for e in self.plan()['proposed_programs']:
            if e['proposed_status'] in ('NOT_ACCEPTED','CONDITIONAL_RESTRICTED'):
                self.assertFalse(e['candidate_db_actions'])
                self.assertTrue(e['existing_semantically_correct'])
    def test_preserves_delivery_raw_and_other_fields(self):
        for e in self.plan()['proposed_programs']:
            for a in e['proposed_db_actions']:
                if a['table']=='program_delivery_facts' and a['action']=='UPDATE':
                    self.assertTrue(a['values']['authoritative_raw'].startswith(a['precondition']['authoritative_raw'] or ''))
                    self.assertFalse({'duration_years','total_credits','terms_per_year','intake_months'} & set(a['values']))
    def test_scoped_domestic_only_never_negative(self):
        for e in self.plan()['proposed_programs']:
            if e['proposed_status']=='ACCEPTED_AVAILABLE':
                self.assertTrue(all(a['table']!='program_offerings' for a in e['proposed_db_actions']))
    def test_in_memory_apply_has_no_repeated_mutations(self):
        plan=self.plan(); db=copy.deepcopy(self.inputs['db']); changed=set()
        for e in plan['proposed_programs']:
            for a in e['proposed_db_actions']:
                changed.add(e['program_id'])
                if a['table']=='program_delivery_facts':
                    old=next((r for r in db[a['table']] if r['program_id']==e['program_id']),None)
                    if old is None: db[a['table']].append({**a['key'],**a['values']})
                    else: old.update(a['values'])
                else:
                    db[a['table']].append({**a['key'],**a['values'],'rule_set_id':100000+len(db[a['table']])})
        if not changed:
            self.assertTrue(all(e['action']=='UNCHANGED' for e in plan['proposed_programs']))
            return
        for e in self.plan(db=db)['proposed_programs']:
            if e['program_id'] in changed:
                self.assertEqual('UNCHANGED',e['action'],e['program_id']); self.assertFalse(e['proposed_db_actions'])
    def test_missing_flag_is_unknown(self):
        data=p.list_records(b'<a class="programslist--link" data-id="x" href="https://www.bcit.ca/programs/a-x/"></a>')
        self.assertFalse(data['X']['international'])
    def test_program_page_restriction_precedence(self):
        e=next(e for e in self.plan()['proposed_programs'] if e['program_id']=='810ABSN')
        self.assertEqual('CONDITIONAL_RESTRICTED',e['proposed_status'])
        self.assertEqual(['810ABSN'],[s['key'] for s in e['evidence']])
    def test_program_specific_study_permit_evidence_is_required(self):
        e=next(e for e in self.plan()['proposed_programs'] if e['program_id']=='M600MSC')
        self.assertEqual('UNCHANGED',e['action'])
        self.assertEqual(['international_full_time','M600MSC'],[s['key'] for s in e['evidence']])
        note=json.loads(next(r for r in e['current_state']['international_rule_sets'] if p.status_from_text(r['notes'])=='ACCEPTED_AVAILABLE')['notes'])
        self.assertEqual('REQUIRED',note['study_permit'])
        self.assertEqual('exact_program_page',note['evidence'][-1]['evidence_type'])
    def test_schema_columns_are_real(self):
        columns={}
        for c in self.inputs['db']['schema']: columns.setdefault(c['table_name'],set()).add(c['column_name'])
        for e in self.plan()['proposed_programs']:
            for a in e['proposed_db_actions']:
                self.assertLessEqual(set(a['key'])|set(a['values']),columns[a['table']])

if __name__=='__main__': unittest.main()
