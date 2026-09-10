"""Governed onboarding for joint BCIT/UBC program 9940BSC."""
from __future__ import annotations
import argparse, hashlib, json, urllib.request
from datetime import date
from pathlib import Path
from psycopg.types.json import Jsonb
from database import get_connection
from program_import_contract import ProgramImportContract, Provenance, activate_revision, approve_payload, dry_run_diff, record_import_revision, require_approved_hash, require_import_ready, write_common_contract

PROGRAM_ID="9940BSC"
SOURCE_URL="https://www.bcit.ca/programs/combined-honours-in-biochemistry-and-forensic-science-bachelor-of-science-full-time-9940bsc/"
OUTPUT_DIR=Path("program_extractor_audit/9940bsc_governed")

BCIT={
"COMM7200":("Report Writing and Workplace Communication for Forensic Investigation",3),"FSCT7320":("Introduction to Forensic Science",3),"LIBS7020":("Bioethics",3),
"FSCT8150":("Forensic Biology: DNA Typing Theory",3),"FSCT8155":("Forensic Biology: Evidence Recovery",3),"FSCT8370":("Quality Assurance for Forensic Science",3),"FSCT8371":("Business Management for Forensic Science",3),
"FSCT7310":("Crime and Incident Scene Investigation",3),"FSCT7910":("Research Methodology and Measurement Models",3),"FSCT8230":("The Medicolegal Aspects of Alcohol",3),"FSCT8240":("Forensic Toxicology",3),"FSCT8320":("The Science of Fingerprints - Theory",3),
"FSCT7009":("Law for Forensic Science",3),"FSCT7010":("The Expert Witness: Prepared for Court",2),"FSCT8156":("Instrumental Analysis for Forensic Chemistry",3),"FSCT8160":("Forensic Biology: DNA Typing Applications",3)}

UBC={
"BIOL112":"Biology of the Cell","CHEM121":"Principles of Chemistry","CHEM111":"Principles of Chemistry","CHEM141":"Principles of Chemistry","CHEM123":"Principles of Chemistry 2","MATH100":"Differential Calculus","MATH102":"Differential Calculus","MATH104":"Differential Calculus","DSCI100":"Introduction to Data Science","CPSC103":"Introduction to Systematic Program Design","SCIE113":"First-Year Seminar in Science",
"BIOC203":"Fundamentals of Biochemistry","BIOL200":"Fundamentals of Cell Biology","BIOL234":"Fundamentals of Genetics","CHEM203":"Introduction to Organic Chemistry","CHEM211":"Introduction to Chemical Analysis","CHEM213":"Organic Chemistry","CHEM245":"Intermediate Organic Chemistry Lab","STAT201":"Statistical Inference for Data Science","CPSC203":"Programming, Problem Solving, and Algorithms",
"BIOC301":"Biochemistry Laboratory","BIOC303":"Molecular Biochemistry","BIOL335":"Molecular Genetics","BIOC402":"Proteins: Structure and Function","BIOC410":"Nucleic Acid: Structure and Function","BIOC449":"Honours Thesis","BIOC420":"Advanced Biochemical Techniques",
"BIOC306":"Quantitative Methods in Biochemistry","BIOC403":"Enzymology","BIOC421":"Recombinant DNA Techniques","BIOC430":"Advanced Topics in Protein Biochemistry","BIOC440":"Concepts in Molecular Biology","BIOC450":"Membrane Biochemistry","BIOC460":"Advanced Techniques in Biochemistry","BIOC470":"Biochemistry and Society: Current Issues","BIOL301":"Biomathematics","BIOL336":"Fundamentals of Evolutionary Biology","BIOL462":"Ecological Plant Biochemistry","CPSC330":"Applied Machine Learning","MEDG421":"Genetics and Cell Biology of Cancer","MICB405":"Bioinformatics","PCTH325":"Rational Basis of Drug Therapy"}

def uid(code): return f"UBC-{code[:4]}-{code[4:]}"
def course(code,role="REQUIRED"): return {"course_id":code if code in BCIT else uid(code),"role":role}

COMPONENTS=[
 {"name":"Year 1 - UBC","order":1,"required_credits":34,"courses":[course(c,"OPTION" if c in {'CHEM121','CHEM111','CHEM141','MATH100','MATH102','MATH104','DSCI100','CPSC103'} else "REQUIRED") for c in ['BIOL112','CHEM121','CHEM111','CHEM141','CHEM123','MATH100','MATH102','MATH104','DSCI100','CPSC103','SCIE113']]},
 {"name":"Year 2 - BCIT","order":2,"required_credits":9,"courses":[course(c) for c in ['COMM7200','FSCT7320','LIBS7020']]},
 {"name":"Year 2 - UBC","order":3,"required_credits":24,"courses":[course(c,"OPTION" if c in {'STAT201','CPSC203'} else "REQUIRED") for c in ['BIOC203','BIOL200','BIOL234','CHEM203','CHEM211','CHEM213','CHEM245','STAT201','CPSC203']]},
 {"name":"Year 3 - BCIT","order":4,"required_credits":18,"courses":[course(c,"ELECTIVE_POOL" if c in {'FSCT7310','FSCT7910','FSCT8230','FSCT8240','FSCT8320'} else "REQUIRED") for c in ['FSCT8150','FSCT8155','FSCT8370','FSCT8371','FSCT7310','FSCT7910','FSCT8230','FSCT8240','FSCT8320']]},
 {"name":"Year 3 - UBC","order":5,"required_credits":15,"courses":[course(c) for c in ['BIOC301','BIOC303','BIOL335']]},
 {"name":"Year 4 - BCIT","order":6,"required_credits":11,"courses":[course(c) for c in ['FSCT7009','FSCT7010','FSCT8156','FSCT8160']]},
 {"name":"Year 4 - UBC","order":7,"required_credits":21,"courses":[course(c,"OPTION") for c in ['BIOC402','BIOC410','BIOC449','BIOC420','BIOC306','BIOC403','BIOC421','BIOC430','BIOC440','BIOC450','BIOC460','BIOC470','BIOL301','BIOL336','BIOL462','CPSC330','MEDG421','MICB405','PCTH325']]},
]

REQUIREMENTS=[
 ("Y1_CHEMISTRY","alternative_courses","UBC",8,None,False,None,"CHEM 121 (or 111 or 141) and CHEM 123."),
 ("Y1_CALCULUS","alternative_courses","UBC",3,1,False,None,"One of MATH 100, 102, or 104."),
 ("Y1_DATA_SCIENCE","alternative_courses","UBC",3,1,False,None,"Three credits from the required alternative set DSCI 100 or CPSC 103; required for graduation, not admission. Neither course is individually mandatory; an institution-approved transfer or equivalent may satisfy the requirement."),
 ("Y1_PHYSICS_GRADUATION_ONLY","subject_credits","UBC",3,None,False,None,"100-level Physics beyond PHYS 100; required for graduation, not admission."),
 ("Y1_ADDITIONAL_COMMUNICATION","subject_credits","UBC",3,None,False,None,"Three credits satisfying the UBC Communication Requirement; required for Option 1 admission."),
 ("Y1_ENGLISH_GRADUATION_ONLY","subject_credits","UBC",3,None,False,None,"Three credits of 100-level UBC English; required for graduation, not admission."),
 ("Y1_ELECTIVES","elective_credits","UBC",8,None,False,None,"Eight credits of electives; required for graduation, not admission."),
 ("Y2_COMPUTING_OR_STATISTICS","alternative_courses","UBC",3,1,False,None,"STAT 201 or CPSC 203."),
 ("Y3_FSCT_POOL","minimum_credits_from_pool","BCIT",6,2,False,None,"Six credits from the five published FSCT electives."),
 ("Y3_UBC_ELECTIVES","elective_credits","UBC",3,None,False,None,"Three credits of electives under UBC Academic Calendar requirements."),
 ("Y4_COMPLETION_PATH","ANY_OF","UBC",None,None,False,None,"Complete either the thesis or advanced biochemical techniques pathway."),
 ("Y4_PATH_1","alternative_path","UBC",9,None,False,"Y4_COMPLETION_PATH","BIOC 449 plus 3 credits of advanced biochemistry electives."),
 ("Y4_PATH_2","alternative_path","UBC",9,None,False,"Y4_COMPLETION_PATH","BIOC 420 plus 6 credits of advanced biochemistry electives."),
 ("Y4_FSCT_UPPER_ELECTIVE","minimum_credits_from_pool","UBC",3,1,True,None,"Three credits from the published FSCT Upper Year Elective pool; advanced biochemistry electives cannot be double counted."),
]

POOLS={"Y1_CHEMISTRY":['CHEM121','CHEM111','CHEM141','CHEM123'],"Y1_CALCULUS":['MATH100','MATH102','MATH104'],"Y1_DATA_SCIENCE":['DSCI100','CPSC103'],"Y2_COMPUTING_OR_STATISTICS":['STAT201','CPSC203'],"Y3_FSCT_POOL":['FSCT7310','FSCT7910','FSCT8230','FSCT8240','FSCT8320'],"Y4_PATH_1":['BIOC449','BIOC403','BIOC421','BIOC430','BIOC440','BIOC450','BIOC460','BIOC470'],"Y4_PATH_2":['BIOC420','BIOC403','BIOC421','BIOC430','BIOC440','BIOC450','BIOC460','BIOC470'],"Y4_FSCT_UPPER_ELECTIVE":['BIOC306','BIOC403','BIOC421','BIOC430','BIOC440','BIOC450','BIOC460','BIOC470','BIOL301','BIOL336','BIOL462','CPSC330','MEDG421','MICB405','PCTH325']}

def build_contract(source_hash=""):
 rules={"admission":[
  {"code":"ADMISSION_PATH_UBC","semantic":"alternative_path","minimum":76,"unit":"PERCENT","human_confirmation_only":True,"raw":"Option 1 UBC pathway: eligible for the honours specialization, with minimum GPA 76% (70% for September 2026), 8.0 credits of UBC Chemistry (CHEM 121, 111, or 141, plus CHEM 123), 3.0 credits satisfying the UBC Communication Requirement, BIOL 112, and 3.0 credits of differential calculus."},
  {"code":"ADMISSION_PATH_TRANSFER","semantic":"alternative_path","minimum":76,"unit":"PERCENT","human_confirmation_only":True,"raw":"Transfer pathway: two terms Chemistry with lab; one term each Biology, English, and differential calculus."},
  {"code":"INTAKE_2026_GPA_EXCEPTION","semantic":"threshold","minimum":70,"unit":"PERCENT","raw":"September 2026 intake minimum GPA is 70%."}],
 "application":[{"code":"UBC_APPLICATION_WORKFLOW","semantic":"human_confirmation","human_confirmation_only":True,"raw":"Applications are made through UBC Science/UBC Admissions; eligible students then apply for the specialization in June."}],
 "completion":[{"code":"TOTAL_132_CREDITS","semantic":"minimum_credits","minimum_credits":132,"raw":"Total 132.0 credits, including Year-1 graduation-only requirements."}],
 "pathway":[{"code":"OPTIONAL_COOP","semantic":"raw_policy","human_confirmation_only":True,"raw":"Co-op placement is optional."}],
 "non_course":[{"code":"CRIMINAL_RECORD_CHECK","semantic":"human_confirmation","human_confirmation_only":True,"raw":"A criminal record check is an entrance requirement; timing is not verified in the stored source data."}]}
 refs=[]
 for x in COMPONENTS:
  for c in x['courses']:
   if c['course_id'] not in {r['course_id'] for r in refs}: refs.append({**c,"reconciliation":"existing_database"})
 return ProgramImportContract({"program_id":PROGRAM_ID,"program_name":"Combined Honours in Biochemistry and Forensic Science","credential":"Bachelor of Science","study_mode":"Full-time","school":"School of Computing and Academic Studies","campus":"Burnaby Campus and UBC Vancouver","delivery_method":"In person","total_credits":132},[{"offering_id":"9940BSC-SEP","intake":"September","status":"Annual September intake"}],COMPONENTS,refs,rules,[{"type":"criminal_record_check","timing":None,"verification":"human_confirmation","notes":"Timing is unknown in governed source data."},{"type":"optional_coop","required":False}],{"eligible":True},Provenance(SOURCE_URL,extracted_at="2026-09-07",last_checked="2026-09-07",pipeline_version="asteris-program-import/1.1",provenance_tag=PROGRAM_ID,review_status="needs-human-review",confidence="human-interpreted",source_sha256=source_hash),[])

def upsert_courses(q):
 for code,(name,credits) in BCIT.items(): q.execute("INSERT INTO courses(course_id,course_name,credits,status,source_url,last_checked,display_course_code,institution_key,native_course_code,import_source) VALUES(%s,%s,%s,'Active',%s,%s,%s,'BCIT',%s,'9940BSC official matrix') ON CONFLICT(course_id) DO UPDATE SET institution_key='BCIT',native_course_code=EXCLUDED.native_course_code",(code,name,credits,SOURCE_URL,date.today(),f'{code[:4]} {code[4:]}',f'{code[:4]} {code[4:]}'))
 for code,name in UBC.items():
  cid=uid(code); display=f'{code[:4]} {code[4:]}'
  credits=3 if code in {'DSCI100','CPSC103'} else None
  q.execute("INSERT INTO courses(course_id,course_name,credits,status,source_url,last_checked,display_course_code,institution_key,native_course_code,import_source,notes) VALUES(%s,%s,%s,'Active',%s,%s,%s,'UBC',%s,'9940BSC official matrix','External-institution course; not a BCIT course') ON CONFLICT(course_id) DO UPDATE SET course_name=EXCLUDED.course_name,credits=COALESCE(EXCLUDED.credits,courses.credits),institution_key='UBC',native_course_code=EXCLUDED.native_course_code",(cid,name,credits,SOURCE_URL,date.today(),display,display))

def write_rules(q,contract):
 q.execute("DELETE FROM academic_rule_conditions WHERE rule_group_id IN (SELECT rule_group_id FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s))",(PROGRAM_ID,)); q.execute("DELETE FROM academic_rule_groups WHERE rule_set_id IN (SELECT rule_set_id FROM academic_rule_sets WHERE program_id=%s)",(PROGRAM_ID,)); q.execute("DELETE FROM academic_rule_sets WHERE program_id=%s",(PROGRAM_ID,))
 for scope,rules in contract.rules.items():
  for rule in rules:
   q.execute("INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes) VALUES(%s,%s,%s,'Full-time',%s,%s) RETURNING rule_set_id",(PROGRAM_ID,scope.upper(),rule['code'],SOURCE_URL,rule['raw'])); sid=q.fetchone()[0]
   q.execute("INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order) VALUES(%s,'AND',%s,1) RETURNING rule_group_id",(sid,rule['code'])); gid=q.fetchone()[0]
   q.execute("INSERT INTO academic_rule_conditions(rule_group_id,condition_type,minimum_value,unit,parameters,description,sort_order) VALUES(%s,%s,%s,%s,%s,%s,1)",(gid,rule['code'],rule.get('minimum'),rule.get('unit'),Jsonb({"semantic":rule['semantic'],"executable":rule['code']=='INTAKE_2026_GPA_EXCEPTION',"human_confirmation":rule.get('human_confirmation_only',False)}),rule['raw']))

def apply_contract(q,contract):
 require_approved_hash(q,contract); upsert_courses(q)
 q.execute("INSERT INTO areas_of_study(area_id,area_name,status) VALUES('SCI','Applied & Natural Sciences','Active') ON CONFLICT(area_id) DO NOTHING")
 write_common_contract(q,contract,program_overrides={"program_overview":"Four-year joint UBC/BCIT combined honours BSc.","area_id":"SCI","program_level":"Bachelor's Degree","accepts_international_students":True,"last_checked":date.today(),"notes":"Joint program; course ownership is institution-qualified."},rule_adapter=write_rules)
 q.execute("DELETE FROM curriculum_requirements WHERE program_id=%s",(PROGRAM_ID,))
 for i,(code,typ,inst,credits,count,no_double,parent,description) in enumerate(REQUIREMENTS,1):
  component=next((x['name'] for x in COMPONENTS if code.startswith('Y'+x['name'][5]) ),None)
  q.execute("SELECT component_id FROM curriculum_components WHERE program_id=%s AND component_name LIKE %s ORDER BY component_order LIMIT 1",(PROGRAM_ID,f"Year {code[1]}%")); component_id=q.fetchone()[0]
  executable=code in {'Y1_CHEMISTRY','Y1_CALCULUS','Y1_DATA_SCIENCE','Y1_PHYSICS_GRADUATION_ONLY','Y1_ENGLISH_GRADUATION_ONLY','Y2_COMPUTING_OR_STATISTICS','Y3_FSCT_POOL','Y4_COMPLETION_PATH','Y4_PATH_1','Y4_PATH_2','Y4_FSCT_UPPER_ELECTIVE'}
  parameters={"official_matrix":True}
  if code=='Y1_DATA_SCIENCE': parameters.update({'scope':'GRADUATION','required_alternative':True,'individual_options_mandatory':False,'approved_equivalent_allowed':True,'equivalent_verification':'institution_confirmation'})
  if code=='Y4_COMPLETION_PATH': parameters['operator']='OR'
  if code=='Y4_PATH_1': parameters['required_course_ids']=['UBC-BIOC-449']
  if code=='Y4_PATH_2': parameters['required_course_ids']=['UBC-BIOC-420']
  if code=='Y1_PHYSICS_GRADUATION_ONLY': parameters.update({'subject':'PHYS','minimum_level':100,'excluded_native_course_codes':['PHYS 100']})
  if code=='Y1_ENGLISH_GRADUATION_ONLY': parameters.update({'subject':'ENGL','minimum_level':100})
  q.execute("INSERT INTO curriculum_requirements(program_id,component_id,requirement_code,requirement_type,institution_key,minimum_credits,exact_course_count,double_count_prohibited,parent_requirement_code,executable,verification_method,description,parameters,source_url,sort_order) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING curriculum_requirement_id",(PROGRAM_ID,component_id,code,typ,inst,credits,count,no_double,parent,executable,'deterministic_transcript_evaluation' if executable else 'advisor_or_registrar_confirmation',description,Jsonb(parameters),SOURCE_URL,i)); rid=q.fetchone()[0]
  for c in POOLS.get(code,[]): q.execute("INSERT INTO curriculum_requirement_courses(curriculum_requirement_id,course_id,course_role) VALUES(%s,%s,%s)",(rid,c if c in BCIT else uid(c),'REQUIRED_ALTERNATIVE' if typ in {'alternative_courses','alternative_path','ANY_OF','OR'} else 'OPTION'))
 q.execute("INSERT INTO program_offerings(offering_id,program_id,study_mode,campus,delivery_method,application_type,application_status,source_url,last_checked,notes) VALUES('9940BSC-SEP',%s,'Full-time','Burnaby Campus and UBC Vancouver','In person','UBC application workflow','Annual September intake',%s,%s,'One intake; applications handled through UBC') ON CONFLICT(offering_id) DO UPDATE SET application_status=EXCLUDED.application_status,last_checked=EXCLUDED.last_checked",(PROGRAM_ID,SOURCE_URL,date.today()))
 q.execute("INSERT INTO program_delivery_facts(program_id,duration_years,total_credits,intake_months,international_eligibility,authoritative_raw,source_url,last_checked) VALUES(%s,4,132,'[\"September\"]'::jsonb,'Available; joint UBC/BCIT program','Optional co-op; Years 2-4 at UBC and BCIT',%s,%s) ON CONFLICT(program_id) DO UPDATE SET total_credits=132,last_checked=EXCLUDED.last_checked",(PROGRAM_ID,SOURCE_URL,date.today()))
 q.execute("DELETE FROM program_advisor_aliases WHERE program_id=%s",(PROGRAM_ID,))
 for alias in ['combined honours in biochemistry and forensic science','biochemistry and forensic science','biochem and forensic science','forensic science combined honours','9940bsc']:
  q.execute("INSERT INTO program_advisor_aliases(normalized_alias,program_id,priority) VALUES(%s,%s,10) ON CONFLICT(normalized_alias) DO UPDATE SET program_id=EXCLUDED.program_id,active=TRUE",(alias,PROGRAM_ID))
 revision=record_import_revision(q,contract,importer="combined_honours_biochem_forensics")
 if revision: activate_revision(q,revision,changed_by="combined_honours_biochem_forensics",reason="governed joint-institution stress-test import")
 return revision

def main():
 p=argparse.ArgumentParser(); p.add_argument('--approve',action='store_true'); p.add_argument('--apply',action='store_true'); p.add_argument('--source-file',type=Path); args=p.parse_args()
 if args.source_file:
  source_bytes=args.source_file.read_bytes()
 else:
  request=urllib.request.Request(SOURCE_URL,headers={'User-Agent':'Asteris governed importer/1.1'})
  with urllib.request.urlopen(request,timeout=30) as response: source_bytes=response.read()
 source_hash=hashlib.sha256(source_bytes).hexdigest(); contract=build_contract(source_hash); readiness=require_import_ready(contract)
 with get_connection() as c,c.cursor() as q:
  # Migration must be applied before this importer is run.
  diff=dry_run_diff(q,contract)
  if args.approve: approve_payload(q,contract,approved_by='user-authorized 9940BSC governed onboarding',review_notes='Official BCIT page reviewed; external UBC ownership and human-confirmation boundaries preserved.')
  revision=apply_contract(q,contract) if args.apply else None; c.commit()
 result={"program_id":PROGRAM_ID,"ready":readiness.go,"source_sha256":source_hash,"payload_sha256":contract.payload_sha256,"revision_id":revision,"dry_run":diff['summary'],"bcit_courses":len(BCIT),"external_courses":len(UBC),"human_confirmation":["UBC/registrar equivalencies and subject-level transfer assessment","UBC application/admission outcome","criminal-record check completion","optional co-op placement","elective approval and no-double-count enforcement"]}; print(json.dumps(result,indent=2))
if __name__=='__main__': main()
