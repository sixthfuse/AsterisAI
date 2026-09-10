"""Read-only BCIT planner. No apply mode; database transactions are server-enforced read-only."""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from psycopg.rows import dict_row
from database import get_connection

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / 'program_extractor_audit/international_source_audit'
OUT = ROOT / 'program_extractor_audit/international_enrichment_plan'
UNKNOWN = 'UNKNOWN_NOT_PUBLISHED'
LISTS = {'international_full_time': ('regular', 'regular-credential-programs'), 'international_flexible': ('flexible', 'flexible-credential-programs')}

def canonical(value):
    p = urlsplit(value or '')
    if p.scheme != 'https' or p.netloc.lower() != 'www.bcit.ca' or p.query:
        raise ValueError('Noncanonical BCIT URL: ' + str(value))
    return 'https://www.bcit.ca' + p.path.rstrip('/') + '/'

def packed(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)

def digest(obj):
    return hashlib.sha256(obj if isinstance(obj, bytes) else packed(obj).encode()).hexdigest()

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def normalized(text):
    return ' '.join((text or '').lower().split())

def status_from_text(text):
    try:
        metadata = json.loads(text or '')
        if isinstance(metadata, dict) and metadata.get('status') in ('ACCEPTED_AVAILABLE', 'NOT_ACCEPTED', 'CONDITIONAL_RESTRICTED'):
            return metadata['status']
    except (ValueError, TypeError):
        pass
    text = normalized(text)
    if re.search(r'(?:this program (?:is not available to|does not accept applications from) international|^not available to international)', text):
        return 'NOT_ACCEPTED'
    if 'outside canada' in text and 'valid work permit' in text:
        return 'CONDITIONAL_RESTRICTED'
    if 'available to international applicants' in text or text.startswith(('eligible;', 'available;')):
        return 'ACCEPTED_AVAILABLE'
    if text.upper() in ('ACCEPTED_AVAILABLE', 'NOT_ACCEPTED', 'CONDITIONAL_RESTRICTED'):
        return text.upper()
    return UNKNOWN

def stable_source_bytes(body):
    # Only the observed WordPress generation comment may vary. All other bytes must match.
    return re.sub(rb'<!-- Last generated: [A-Za-z]+ [0-9]{1,2}, [0-9]{4} at [0-9]{2}:[0-9]{2}:[0-9]{2} -->', b'<!-- Last generated: VERIFIED_VOLATILE_TIMESTAMP -->', body)

def list_records(body):
    soup = BeautifulSoup(body, 'html.parser')
    result = {}
    for a in soup.select('a.programslist--link'):
        pid = a.get('data-id', '').upper()
        if not pid:
            raise ValueError('Missing exact program ID')
        rec = {'url': canonical(a.get('href')), 'international': bool(a.select_one('.available--international')), 'pgwp': bool(a.select_one('.available--pgwp'))}
        if pid in result and result[pid] != rec:
            raise ValueError('Conflicting duplicate list ID ' + pid)
        result[pid] = rec
    if not result:
        raise ValueError('Empty international list')
    return result

def database_snapshot():
    conn = get_connection()
    conn.read_only = True
    conn.isolation_level = __import__('psycopg').IsolationLevel.REPEATABLE_READ
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SHOW transaction_read_only')
            assert cur.fetchone()['transaction_read_only'] == 'on'
            result = {}
            for table in ('programs', 'program_delivery_facts', 'academic_rule_sets', 'academic_rule_groups', 'academic_rule_conditions', 'program_offerings'):
                cur.execute('SELECT * FROM ' + table)
                result[table] = sorted(cur.fetchall(), key=packed)
            cur.execute("SELECT count(*) AS n FROM courses WHERE upper(status)='ACTIVE'")
            result['active_courses'] = cur.fetchone()['n']
            cur.execute("SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position")
            result['schema'] = cur.fetchall()
        return json.loads(packed(result))
    finally:
        conn.rollback()
        conn.close()

def verify_source(spec):
    key, url, path, expected = spec
    rec = {'key': key, 'url': url, 'snapshot_path': str(path.relative_to(ROOT)), 'checked_at': datetime.now(timezone.utc).isoformat(), 'error': ''}
    try:
        old = path.read_bytes() if path.exists() else None
        if old is not None:
            rec['snapshot_sha256'] = digest(old)
        if expected and (old is None or digest(old) != expected):
            raise ValueError('Retained audit snapshot hash mismatch')
        request = urllib.request.Request(url, headers={'User-Agent': 'Asteris read-only enrichment planner/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                rec['final_url'] = response.url
                fresh = response.read()
        except Exception:
            marker = b'\n__ASTERIS_FINAL_URL__'
            process = subprocess.run(['curl.exe','-sS','-L','-A','Asteris read-only enrichment planner/1.0','-w',marker.decode()+'%{url_effective}',url],capture_output=True,check=True)
            fresh, final = process.stdout.rsplit(marker,1)
            rec['final_url'] = final.decode().strip()
        rec['live_sha256'] = digest(fresh)
        target = OUT / 'sources' / (key + '.html')
        target.write_bytes(fresh)
        rec['live_path'] = str(target.relative_to(ROOT))
        if old is not None:
            rec['snapshot_content_sha256'] = digest(stable_source_bytes(old))
        rec['live_content_sha256'] = digest(stable_source_bytes(fresh))
        if expected and fresh != old and stable_source_bytes(fresh) != stable_source_bytes(old):
            raise ValueError('Unexplained source hash change outside the precisely allowed generation timestamp comment')
        if expected:
            if canonical(rec['final_url']) != canonical(url):
                raise ValueError('Unexpected source redirect URL')
            rec['verification'] = 'EXACT_BYTES_MATCH' if fresh == old else 'ONLY_GENERATION_TIMESTAMP_COMMENT_CHANGED'
            rec['hash_change_explanation'] = '' if fresh == old else 'Raw-byte diff is solely the WordPress Last generated timestamp comment; all remaining bytes match.'
        else:
            rec['verification'] = 'EXACT_BYTES_MATCH' if old is not None and fresh == old else 'LIVE_PROGRAM_PAGE_SEMANTICALLY_REVERIFIED'
            rec['hash_change_explanation'] = '' if old is not None and fresh == old else 'Live individual program page is revalidated by exact program ID, declared canonical URL, and required eligibility text.'
        if key in LISTS:
            rec['records'] = list_records(fresh)
        elif key != 'program_availability':
            soup = BeautifulSoup(fresh, 'html.parser')
            link = soup.select_one('link[rel="canonical"]')
            rec['declared_canonical_url'] = link.get('href') if link else None
            if not link or canonical(link.get('href')) != canonical(url):
                raise ValueError('Program canonical link mismatch')
            if not canonical(rec['final_url']).rstrip('/').lower().endswith('-'+key.lower()) and canonical(rec['final_url']) != canonical(url):
                raise ValueError('Program redirect changed exact program identity')
            rec['text'] = soup.get_text(' ', strip=True)
    except Exception as exc:
        rec['error'] = str(exc)
    return rec

def build_plan(coverage, db, sources, availability, conflicts):
    active = {p['program_id']: p for p in db['programs'] if p['status'].upper() == 'ACTIVE'}
    facts = {p['program_id']: p for p in db['program_delivery_facts']}
    all_rules = [r for r in db['academic_rule_sets'] if r['rule_scope'] == 'INTERNATIONAL']
    issues, proposed, unknown = [], [], []
    global_errors = []
    if len(coverage) != 374 or len({p['program_id'] for p in coverage}) != 374 or set(active) != {p['program_id'] for p in coverage}:
        global_errors.append('Audit/current program identity or 374-program baseline mismatch')
    if db['active_courses'] != 3976:
        global_errors.append('Active course baseline mismatch')
    if Counter(p['recommended_program_status'] for p in coverage) != Counter({'ACCEPTED_AVAILABLE':253, 'CONDITIONAL_RESTRICTED':12, 'NOT_ACCEPTED':1, UNKNOWN:108}):
        global_errors.append('Audit classification baseline mismatch')
    for table, required in {'program_delivery_facts': {'program_id','international_eligibility','authoritative_raw','source_url','last_checked'}, 'academic_rule_sets': {'program_id','rule_scope','rule_name','study_mode','source_url','notes'}}.items():
        if not required <= {c['column_name'] for c in db['schema'] if c['table_name']==table}:
            global_errors.append('Required existing schema missing: ' + table)
    for row in sorted(coverage, key=lambda r:r['program_id']):
        pid, status = row['program_id'], row['recommended_program_status']
        p = active.get(pid, {})
        existing = [r for r in all_rules if r['program_id']==pid]
        group_ids = {g['rule_group_id'] for g in db['academic_rule_groups'] if g['rule_set_id'] in {r['rule_set_id'] for r in existing}}
        current = {'legacy_accepts_international_students': p.get('accepts_international_students'), 'delivery_facts': facts.get(pid), 'international_rule_sets': existing, 'international_conditions': [c for c in db['academic_rule_conditions'] if c['rule_group_id'] in group_ids]}
        entry = {'program_id': pid, 'program_title': p.get('program_name',row['program_name']), 'current_state':current, 'proposed_status':status, 'action':'SKIP', 'proposed_db_actions':[], 'evidence':[], 'notes':[], 'blockers':[]}
        if status == UNKNOWN:
            entry['notes'] = ['Unknown: no database actions; list absence/missing flags never imply rejection.']
            unknown.append(entry)
            continue
        errors = list(global_errors)
        try:
            url = canonical(row['source_url'])
            if canonical(p.get('source_url')) != url or not url.rstrip('/').lower().endswith('-'+pid.lower()):
                errors.append('Exact program ID/canonical URL mismatch')
        except ValueError as exc:
            errors.append(str(exc))
        restricted = status in ('NOT_ACCEPTED', 'CONDITIONAL_RESTRICTED')
        keys = [pid] if restricted else [k for k,(prefix,_) in LISTS.items() if row[prefix+'_international_flag']=='true']
        if not restricted and row['individual_study_permit_status'] != UNKNOWN:
            keys.append(pid)
        if not keys:
            errors.append('No governing source')
        for key in keys:
            source = sources.get(key, {'error':'Missing source verification'})
            entry['evidence_type'] = 'exact_program_page_restriction' if restricted else 'international_list_positive_flag'
            entry['evidence'].append({k:v for k,v in source.items() if k not in ('text','records')})
            if source.get('error'):
                errors.append(key + ': ' + source['error'])
                continue
            if key in LISTS:
                record = source['records'].get(pid)
                if not record or not record['international'] or record['url'] != url:
                    errors.append(key + ': exact list ID/URL/positive flag mismatch; expected ' + url + '; observed ' + packed(record))
                elif record['pgwp'] != (row[LISTS[key][0]+'_pgwp_flag']=='true'):
                    errors.append(key + ': PGWP flag mismatch')
            elif key not in LISTS and status_from_text(source.get('text')) != status:
                errors.append('Program page restriction differs from audit')
            elif key not in LISTS and status == 'CONDITIONAL_RESTRICTED':
                for phrase in ('not eligible for a study permit','not eligible for a pgwp','program head approval'):
                    if phrase not in normalized(source.get('text')):
                        errors.append('Missing current restriction: '+phrase)
            elif key not in LISTS and row['individual_study_permit_status'] == 'REQUIRED':
                if 'a valid bcit study permit is required prior to starting the program' not in normalized(source.get('text')):
                    errors.append('Program page does not confirm the audited study-permit requirement')
        for c in conflicts:
            if c['program_id']==pid and c['kind'] not in ('intake_or_mode_scope','scope_refinement'):
                errors.append('Unrecognized audit conflict: '+packed(c))
        scoped = [a for a in availability if a['program_id']==pid and a['domestic_only']=='true']
        if scoped:
            entry['notes'].append({'Domestic Only offering scope':scoped, 'action':'Context only; no offering rows proposed; never a program-level negative.', 'snapshot_verification':{k:v for k,v in sources['program_availability'].items() if k not in ('text','records')}})
        entry['notes'].append({'study_permit':row['individual_study_permit_status'],'pgwp':row['recommended_pgwp_status'], 'representation':'Existing INTERNATIONAL notes/conditions preserved; new evidence uses existing text columns.'})
        if restricted:
            entry['notes'].append('Outside Canada OR a Canadian work permit valid throughout clinical training; study-permit and PGWP ineligible; program-head approval required.' if status=='CONDITIONAL_RESTRICTED' else 'International applications not accepted.')
        known = [status_from_text(r['notes']) for r in existing] + [status_from_text((facts.get(pid) or {}).get('international_eligibility'))]
        if any(s != UNKNOWN and s != status for s in known):
            errors.append('Existing stored program eligibility conflicts with audited status')
        legacy = p.get('accepts_international_students')
        if legacy is False and status != 'NOT_ACCEPTED' or legacy is True and status == 'NOT_ACCEPTED':
            errors.append('Legacy international flag contradicts proposal')
        for r in existing:
            if canonical(r['source_url']) not in {url} | ({sources[k]['url'] for k in LISTS} if not restricted else set()):
                errors.append('Existing INTERNATIONAL evidence URL mismatch')
        matching = [r for r in existing if status_from_text(r['notes'])==status]
        if restricted and matching:
            if status=='CONDITIONAL_RESTRICTED' and any(term not in normalized(' '.join(r['notes'] for r in matching)) for term in ('not eligible for a study permit','not eligible for a pgwp','program head approval')):
                errors.append('Existing Nursing rule is incomplete')
        # Preserve all semantically matching existing rules. No duplicate or cosmetic normalization.
        candidate = []
        if not matching:
            evidence = [{'url':s.get('url'),'source_sha256':s.get('live_sha256'),'checked_at':s.get('checked_at'),'evidence_type':'exact_program_page' if s.get('key') == pid else 'international_list_positive_flag'} for s in entry['evidence']]
            note = packed({'status':status,'evidence':evidence,'pgwp':row['recommended_pgwp_status'],'study_permit':row['individual_study_permit_status'],'offering_scope':'Any Domestic Only offering remains mode/intake-specific.'})
            fact = facts.get(pid)
            if status_from_text((fact or {}).get('international_eligibility')) != status:
                patch = {'international_eligibility':status,'authoritative_raw':((fact or {}).get('authoritative_raw') or '')+'\nInternational evidence: '+note,'source_url':(fact or {}).get('source_url') or url,'last_checked': min((s.get('checked_at','')[:10] for s in entry['evidence']), default='')}
                candidate.append({'table':'program_delivery_facts','action':'UPDATE' if fact else 'INSERT','key':{'program_id':pid},'values':patch,'precondition':fact})
            exact_page = next((s for s in entry['evidence'] if s.get('key') == pid), None)
            candidate.append({'table':'academic_rule_sets','action':'INSERT','key':{'program_id':pid,'rule_scope':'INTERNATIONAL','rule_name':'International eligibility source evidence','study_mode':p.get('study_mode') or 'ALL'},'values':{'source_url':(exact_page or entry['evidence'][0]).get('url'),'notes':note},'precondition':'No semantically equivalent INTERNATIONAL rule exists'})
        entry['candidate_db_actions'] = candidate
        entry['existing_semantically_correct'] = bool(matching)
        entry['blockers'] = sorted(set(errors))
        if errors:
            issues.extend({'program_id':pid,'blocker':e} for e in sorted(set(errors)))
        else:
            entry['proposed_db_actions'] = candidate
            entry['action'] = ('UPDATE' if any(a['action']=='UPDATE' for a in candidate) else 'INSERT') if candidate else 'UNCHANGED'
        proposed.append(entry)
    counts = {a:sum(e['action']==a for e in proposed) for a in ('INSERT','UPDATE','UNCHANGED','SKIP')}
    row_counts = Counter(a['action'] for e in proposed for a in e['proposed_db_actions'])
    ready = [e for e in proposed if e['action'] in ('INSERT','UPDATE')]
    batch = [e['program_id'] for e in sorted(ready, key=lambda e:(bool(any(isinstance(n,dict) and 'Domestic Only offering scope' in n for n in e['notes'])),e['program_id']))[:50]]
    return {'program_action_counts':counts,'db_row_action_counts':dict(row_counts),'ready_for_enrichment':len(ready),'verified_deterministic_programs':266-counts['SKIP'],'blocked_programs':counts['SKIP'],'unknown_untouched':len(unknown),'schema_migration_required':False,'existing_international_rule_sets':len(all_rules),'first_batch_program_ids':batch,'batch_order':'Programs without Domestic Only scope first, then exact program ID ascending; unchanged programs excluded.','batch_1_recommendation':'GO for separate review/authorization of the listed 50; this planner never applies changes.' if len(batch)==50 and not global_errors else 'NO-GO: fewer than 50 verified changes or baseline/schema blockers.','proposed_programs':proposed,'unknown_programs':unknown,'conflicts_or_blockers':issues}

def csv_write(name, data):
    fields = list(dict.fromkeys(k for r in data for k in r)) or ['program_id','blocker']
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        w.writerows({k:packed(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in data)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--replay',action='store_true'); args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'sources').mkdir(exist_ok=True)
    paths=[ROOT/'BCIT_INTERNATIONAL_SOURCE_AUDIT.json', ROOT/'BCIT_INTERNATIONAL_SOURCE_AUDIT.md']+sorted(AUDIT.glob('*.csv'))
    audit_hashes={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths}
    audit=json.loads(paths[0].read_text(encoding='utf-8'))
    coverage=rows(AUDIT/'program_coverage.csv'); availability=rows(AUDIT/'availability_offerings.csv'); conflicts=rows(AUDIT/'conflicts_and_refinements.csv')
    capture=OUT/'input_snapshot.json'
    if args.replay:
        inputs=json.loads(capture.read_text(encoding='utf-8'))
        if inputs['audit_hashes']!=audit_hashes: raise RuntimeError('Audit files changed since capture')
        for source in inputs['sources'].values():
            if source.get('live_path') and digest((ROOT/source['live_path']).read_bytes()) != source['live_sha256']:
                raise RuntimeError('Captured source file changed: ' + source['key'])
    else:
        db=database_snapshot()
        specs=[(k,'https://www.bcit.ca/international-applicants/'+slug+'/', ROOT/'work'/(slug+'.html'),audit['source_snapshot_sha256'][k]) for k,(_,slug) in LISTS.items()]
        specs.append(('program_availability','https://www.bcit.ca/admission/program-availability/',ROOT/'work/program-availability.html',audit['source_snapshot_sha256']['program_availability']))
        specs.extend((r['program_id'],r['source_url'],ROOT/'work/nursing_live'/(r['program_id']+'.html'),None) for r in coverage if r['recommended_program_status'] in ('NOT_ACCEPTED','CONDITIONAL_RESTRICTED') or r['individual_study_permit_status'] != UNKNOWN)
        with ThreadPoolExecutor(max_workers=4) as pool: sources={s['key']:s for s in pool.map(verify_source,specs)}
        inputs={'db':db,'sources':sources,'audit_hashes':audit_hashes,'transaction_read_only':'on','database_sha256':digest(db)}
        capture.write_text(packed(inputs),encoding='utf-8')
    plan=build_plan(coverage,inputs['db'],inputs['sources'],availability,conflicts)
    replay=build_plan(coverage,inputs['db'],inputs['sources'],availability,conflicts)
    assert packed(plan)==packed(replay)
    previous=ROOT/'BCIT_INTERNATIONAL_ENRICHMENT_PLAN.json'
    stable=digest(plan)
    if args.replay and previous.exists():
        assert json.loads(previous.read_text(encoding='utf-8'))['proposal_sha256']==stable, 'Replay proposal changed'
    plan['proposal_sha256']=stable
    plan['input_sha256']=digest(inputs)
    plan['idempotency']={'two_independent_builds_identical':True,'replay_identical':args.replay,'definition':'Fixed database, audit and source input snapshots include fixed retrieval timestamps. No run clock participates in proposal generation.'}
    test_run = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'test_bcit_international_enrichment_planner', '-v'], cwd=ROOT, capture_output=True, text=True)
    (OUT/'focused_tests.txt').write_text(test_run.stdout + test_run.stderr, encoding='utf-8')
    plan['validation'] = {'focused_tests_exit_code':test_run.returncode,'focused_tests_passed':test_run.returncode == 0,'shared_production_code_touched':False}
    if test_run.returncode: plan['batch_1_recommendation'] = 'NO-GO: focused planner tests failed.'
    plan['source_verification']=[{k:v for k,v in s.items() if k not in ('records','text')} for s in inputs['sources'].values()]
    after=database_snapshot()
    plan['database_unchanged_after_planning']=digest(after)==inputs['database_sha256']
    if not plan['database_unchanged_after_planning']: plan['batch_1_recommendation']='NO-GO: live database changed since captured inputs.'
    previous.write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    csv_write('proposed_changes.csv',[e for e in plan['proposed_programs'] if e['action']!='UNCHANGED'])
    csv_write('unchanged_existing.csv',[e for e in plan['proposed_programs'] if e['action']=='UNCHANGED'])
    csv_write('unknown_untouched.csv',plan['unknown_programs']); csv_write('conflicts_or_blockers.csv',plan['conflicts_or_blockers'])
    csv_write('source_verification.csv',plan['source_verification'])
    csv_write('first_batch.csv',[{'order':i+1,'program_id':pid,'program_title':next(e['program_title'] for e in plan['proposed_programs'] if e['program_id']==pid)} for i,pid in enumerate(plan['first_batch_program_ids'])])
    nursing=[e for e in plan['proposed_programs'] if e['proposed_status'] in ('NOT_ACCEPTED','CONDITIONAL_RESTRICTED')]
    md=['# BCIT International Eligibility Enrichment Plan — Read Only','', 'No PostgreSQL writes, migration, advisor changes, or enrichment were performed. All reads use a server-enforced read-only repeatable-read transaction.','', '## Decision',plan['batch_1_recommendation'],'', 'Program actions: '+packed(plan['program_action_counts']), 'Program action convention: UPDATE if any row is updated; otherwise INSERT if any row is inserted; UNCHANGED if existing evidence is semantically correct; SKIP for a blocked deterministic program. Unknown-program SKIPs are counted separately from blocked deterministic programs.', 'Database row actions: '+packed(plan['db_row_action_counts']),f"Ready for enrichment: {plan['ready_for_enrichment']}; blocked deterministic programs: {plan['blocked_programs']}; unknown untouched: {plan['unknown_untouched']}.", 'Schema migration required: no. Existing text evidence columns suffice; no new permit/PGWP columns or condition types are introduced.', 'Nursing actions: '+packed(Counter(e['action'] for e in nursing))+'. Matching rules are reused, even when no delivery-facts row exists.', 'Validation: '+packed(plan['validation'])+'. The focused_tests.txt log records each test, including in-memory apply/replan duplicate prevention.', 'Existing Accounting/Business Administration INTERNATIONAL rules and conditions are preserved, including their work-component, study-permit and PGWP restrictions.','', '## Verification', 'Raw-byte and stable-content SHA-256 are retained. Only the observed WordPress Last generated timestamp comment is normalized; all other byte changes block the source. URL fragments identify sections and are removed for document identity; query strings and host/path changes are rejected. Nursing audit HTML lacked a published audit hash: its retained bytes are hashed now and compared to live bytes; this does not retroactively authenticate the original snapshot.', 'Offering Domestic Only rows are retained as dated audit context only, with their source verification outcome; no offering updates are proposed.', 'Snapshot input SHA-256: '+plan['input_sha256'], 'Proposal SHA-256: '+stable, 'Idempotency: '+packed(plan['idempotency']), 'Database snapshot unchanged: '+str(plan['database_unchanged_after_planning']), '', '## First batch', plan['batch_order'], ', '.join(plan['first_batch_program_ids']) or 'No verified batch available.', '', '## All deterministic programs', '| Program | Title | Status | Action | Blockers |','|---|---|---|---|---|']
    md += ['| '+ ' | '.join(str(e[k]).replace('|','/') for k in ('program_id','program_title','proposed_status','action'))+' | '+'; '.join(e['blockers']).replace('|','/')+' |' for e in plan['proposed_programs']]
    md += ['', '## Unknown programs — untouched', '| Program | Title |','|---|---|']+['| '+e['program_id']+' | '+e['program_title'].replace('|','/')+' |' for e in plan['unknown_programs']]
    md += ['', '## Review files','The JSON and CSVs contain current complete stored state, exact candidate rows, permitted proposal actions, sources, hashes, retrieval times and restrictions. Blocked rows have no proposed executable actions; candidate rows are review-only.','Run: `.\\.venv\\Scripts\\python.exe -B bcit_international_enrichment_planner.py`; deterministic replay: add `--replay`. No apply option exists.']
    (ROOT/'BCIT_INTERNATIONAL_ENRICHMENT_PLAN.md').write_text('\n'.join(md),encoding='utf-8')
    print(packed({k:v for k,v in plan.items() if k not in ('proposed_programs','unknown_programs','source_verification','conflicts_or_blockers')}))

if __name__=='__main__': main()
