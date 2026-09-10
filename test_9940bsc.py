import unittest
from fastapi.testclient import TestClient
from academic_rules import get_program_curriculum,get_program_rules
from ai_advisor import find_programs,resolve_academic_context,required_alternative_graduation_answer
from database import get_connection
from curriculum_evaluator import UNKNOWN, evaluate_curriculum
from advisor_engine import run_advisor_engine
from main import app

class CombinedHonours9940Tests(unittest.TestCase):
 PROGRAM_ID='9940BSC'
 @classmethod
 def setUpClass(cls): cls.client=TestClient(app)
 def test_identity_and_aliases(self):
  for query in ('biochemistry and forensic science','biochem and forensic science','forensic science combined honours','9940bsc'):
   self.assertEqual([x['program_id'] for x in find_programs(query)],[self.PROGRAM_ID])
 def test_institution_ownership_and_counts(self):
  with get_connection() as c,c.cursor() as q:
   q.execute("SELECT institution_key,count(*) FROM courses JOIN program_courses USING(course_id) WHERE program_id=%s GROUP BY institution_key",(self.PROGRAM_ID,)); self.assertEqual(dict(q.fetchall()),{'BCIT':16,'UBC':42})
   q.execute("SELECT count(*) FROM courses WHERE course_id LIKE 'UBC-%%' AND institution_key<>'UBC'"); self.assertEqual(q.fetchone()[0],0)
 def test_curriculum_and_year3_pool(self):
  data=get_program_curriculum(self.PROGRAM_ID); self.assertEqual(len(data['components']),7)
  with get_connection() as c,c.cursor() as q:
   q.execute("SELECT minimum_credits,exact_course_count,count(*) FROM curriculum_requirements r JOIN curriculum_requirement_courses rc USING(curriculum_requirement_id) WHERE requirement_code='Y3_FSCT_POOL' GROUP BY minimum_credits,exact_course_count"); self.assertEqual(q.fetchone(),(6,2,5))
 def test_admission_paths_and_intake_gpa(self):
  rules=get_program_rules(self.PROGRAM_ID,'ADMISSION')['rule_sets']; self.assertEqual({r['name'] for r in rules},{'ADMISSION_PATH_UBC','ADMISSION_PATH_TRANSFER','INTAKE_2026_GPA_EXCEPTION'})
  values={r['name']:float(r['groups'][0]['conditions'][0]['minimum_value']) for r in rules}; self.assertEqual(values['INTAKE_2026_GPA_EXCEPTION'],70); self.assertEqual(values['ADMISSION_PATH_UBC'],76)
  option_one=next(r for r in rules if r['name']=='ADMISSION_PATH_UBC')['notes']
  for expected in ('honours specialization','76%','70%','8.0 credits','CHEM 121','CHEM 123','Communication Requirement','BIOL 112','differential calculus'): self.assertIn(expected,option_one)
 def test_graduation_only_and_no_double_count(self):
  with get_connection() as c,c.cursor() as q:
   q.execute("SELECT description FROM curriculum_requirements WHERE program_id=%s AND requirement_code='Y1_PHYSICS_GRADUATION_ONLY'",(self.PROGRAM_ID,)); self.assertIn('not admission',q.fetchone()[0])
   q.execute("SELECT double_count_prohibited FROM curriculum_requirements WHERE program_id=%s AND requirement_code='Y4_FSCT_UPPER_ELECTIVE'",(self.PROGRAM_ID,)); self.assertTrue(q.fetchone()[0])
   q.execute("SELECT requirement_code,description FROM curriculum_requirements WHERE program_id=%s AND requirement_code IN ('Y1_PHYSICS_GRADUATION_ONLY','Y1_ENGLISH_GRADUATION_ONLY','Y1_DATA_SCIENCE','Y1_ELECTIVES')",(self.PROGRAM_ID,)); graduation=dict(q.fetchall())
   self.assertEqual(set(graduation),{'Y1_PHYSICS_GRADUATION_ONLY','Y1_ENGLISH_GRADUATION_ONLY','Y1_DATA_SCIENCE','Y1_ELECTIVES'})
   self.assertIn('DSCI 100 or CPSC 103',graduation['Y1_DATA_SCIENCE']); self.assertIn('Eight credits',graduation['Y1_ELECTIVES'])
  with get_connection() as c,c.cursor() as q:
   q.execute("SELECT requirement_type,institution_key,minimum_credits,exact_course_count,parameters FROM curriculum_requirements WHERE program_id=%s AND requirement_code='Y1_DATA_SCIENCE'",(self.PROGRAM_ID,)); typ,owner,credits,count,parameters=q.fetchone()
   q.execute("SELECT DISTINCT course_role FROM curriculum_requirement_courses rc JOIN curriculum_requirements r USING(curriculum_requirement_id) WHERE r.program_id=%s AND r.requirement_code='Y1_DATA_SCIENCE'",(self.PROGRAM_ID,)); roles={row[0] for row in q.fetchall()}
  self.assertEqual((typ,owner,credits,count),('alternative_courses','UBC',3,1))
  self.assertEqual(parameters['scope'],'GRADUATION'); self.assertFalse(parameters['individual_options_mandatory'])
  self.assertEqual(roles,{'REQUIRED_ALTERNATIVE'})

 def test_required_data_science_alternative_evaluation(self):
  for course_id in ('UBC-DSCI-100','UBC-CPSC-103'):
   with self.subTest(course_id=course_id):
    result=evaluate_curriculum(self.PROGRAM_ID,[{'course_id':course_id}])
    requirement=self.requirement(result,'Y1_DATA_SCIENCE')
    self.assertEqual(requirement['status'],'satisfied')
    self.assertTrue(requirement['required_alternative'])
    self.assertFalse(requirement['individual_options_mandatory'])
    self.assertEqual(requirement['institution_key'],'UBC')
  missing=self.requirement(evaluate_curriculum(self.PROGRAM_ID,[]),'Y1_DATA_SCIENCE')
  self.assertEqual(missing['status'],'not_satisfied'); self.assertEqual(missing['remaining_credits'],3.0)

 def test_component_presentation_never_calls_required_alternatives_optional(self):
  curriculum=get_program_curriculum(self.PROGRAM_ID)
  courses={course['course_id']:course for component in curriculum['components'] for course in component['courses']}
  for course_id in ('UBC-DSCI-100','UBC-CPSC-103','UBC-MATH-100','UBC-STAT-201'):
   self.assertEqual(courses[course_id]['course_role'],'REQUIRED_ALTERNATIVE')
   self.assertTrue(courses[course_id]['alternative_requirement']['required'])
   self.assertFalse(courses[course_id]['alternative_requirement']['individual_option_mandatory'])

 def test_top_level_advisor_data_science_graduation_answers(self):
  cases=(
   ("if I don't have 3.0 credits of DSCI 100 or CPSC 103, can I still graduate?",'not yet satisfied'),
   ('I completed DSCI 100. Can I graduate with that option?','satisfied by DSCI 100'),
   ('I completed CPSC 103. Can I graduate with that option?','satisfied by CPSC 103'),
  )
  for question,expected in cases:
   with self.subTest(question=question):
    response=self.client.post('/advisor',json={'question':question,'conversation':[]})
    self.assertEqual(response.status_code,200); result=response.json(); answer=result['answer']
    self.assertEqual(result['tools_used'],['evaluate_program_curriculum'])
    self.assertIn(expected,answer); self.assertIn('graduation requirement, not an admission requirement',answer)
    self.assertIn('Neither option is individually mandatory',answer)
    self.assertIn('UBC',answer)

 def test_required_alternative_rule_is_not_used_for_admission_answer(self):
  self.assertIsNone(required_alternative_graduation_answer(
   'Are DSCI 100 and CPSC 103 admission requirements?',self.PROGRAM_ID,[]))

 def test_criminal_record_check_timing_is_unknown(self):
  with get_connection() as c,c.cursor() as q:
   q.execute("SELECT notes FROM academic_rule_sets WHERE program_id=%s AND rule_name='CRIMINAL_RECORD_CHECK'",(self.PROGRAM_ID,)); text=q.fetchone()[0]
  self.assertIn('timing is not verified',text); self.assertNotIn('after',text.lower())
 def test_context_switch(self):
  conversation=[{'role':'user','content':'Tell me about nursing'},{'role':'assistant','content':'Okay'}]
  self.assertEqual(resolve_academic_context('What about biochem and forensic science?',conversation,None)['program_id'],self.PROGRAM_ID)

 def requirement(self,result,code):
  pending=list(result['requirements'])
  while pending:
   item=pending.pop(0)
   if item['requirement_code']==code: return item
   pending.extend(item['children'])
  self.fail(f'Missing evaluated requirement {code}')

 def test_year3_pool_credit_progress(self):
  enough=evaluate_curriculum(self.PROGRAM_ID,[{'course_id':'FSCT7310'},{'course_id':'FSCT7910'}])
  pool=self.requirement(enough,'Y3_FSCT_POOL')
  self.assertEqual(pool['status'],'satisfied'); self.assertEqual(pool['completed_credits'],6.0)
  short=evaluate_curriculum(self.PROGRAM_ID,[{'course_id':'FSCT7310'}])
  pool=self.requirement(short,'Y3_FSCT_POOL')
  self.assertEqual(pool['status'],'partially_satisfied'); self.assertEqual(pool['remaining_credits'],3.0)
  self.assertEqual(pool['remaining_course_count'],1)

 def test_top_level_advisor_exposes_generalized_progress(self):
  advisor=run_advisor_engine(self.PROGRAM_ID,[
   {'course_id':'FSCT7310'}, {'course_id':'FSCT7910'}])
  evaluation=advisor['program_progress']['curriculum_evaluation']
  self.assertEqual(self.requirement(evaluation,'Y3_FSCT_POOL')['status'],'satisfied')

 def test_nested_year4_alternative_and_no_double_count(self):
  transcript=[
   {'course_id':'UBC-BIOC-449','credits':6},
   {'course_id':'UBC-BIOC-403','credits':3},
  ]
  result=evaluate_curriculum(self.PROGRAM_ID,transcript)
  path=self.requirement(result,'Y4_COMPLETION_PATH')
  self.assertEqual(path['status'],'satisfied')
  self.assertIn('Y4_PATH_1',path['reason'])
  upper=self.requirement(result,'Y4_FSCT_UPPER_ELECTIVE')
  self.assertEqual(upper['status'],'not_satisfied')

 def test_nested_year4_neither_branch_complete(self):
  result=evaluate_curriculum(self.PROGRAM_ID,[{'course_id':'UBC-BIOC-403','credits':3}])
  self.assertEqual(self.requirement(result,'Y4_COMPLETION_PATH')['status'],'partially_satisfied')

 def test_institution_identity_and_partial_subject_evidence(self):
  wrong=evaluate_curriculum(self.PROGRAM_ID,[
   {'institution_key':'UBC','native_course_code':'FSCT 7310','credits':3},
   {'institution_key':'UBC','native_course_code':'FSCT 7910','credits':3},
  ])
  self.assertEqual(self.requirement(wrong,'Y3_FSCT_POOL')['status'],'not_satisfied')
  partial=evaluate_curriculum(self.PROGRAM_ID,[{'subject':'PHYS','credits':3}])
  self.assertEqual(self.requirement(partial,'Y1_PHYSICS_GRADUATION_ONLY')['status'],UNKNOWN)
  self.assertEqual(self.requirement(partial,'Y3_FSCT_POOL')['status'],'not_satisfied')
  complete=evaluate_curriculum(self.PROGRAM_ID,[{
   'institution_key':'UBC','native_course_code':'PHYS 101','subject':'PHYS','credits':3}])
  self.assertEqual(self.requirement(complete,'Y1_PHYSICS_GRADUATION_ONLY')['status'],'satisfied')

if __name__=='__main__': unittest.main()
