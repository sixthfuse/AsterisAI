BEGIN;

CREATE TABLE IF NOT EXISTS clinical_placement_requirements (
  clinical_requirement_id BIGSERIAL PRIMARY KEY,
  program_id VARCHAR NOT NULL REFERENCES programs(program_id),
  requirement_code TEXT NOT NULL,
  requirement_name TEXT NOT NULL,
  requirement_type TEXT NOT NULL,
  applies_to TEXT NOT NULL DEFAULT 'CLINICAL_COURSES',
  executable BOOLEAN NOT NULL DEFAULT FALSE,
  verification_method TEXT NOT NULL DEFAULT 'HUMAN_CONFIRMATION',
  description TEXT NOT NULL,
  source_url TEXT NOT NULL,
  parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
  sort_order INTEGER NOT NULL DEFAULT 0,
  UNIQUE(program_id, requirement_code)
);

CREATE TABLE IF NOT EXISTS practice_hour_requirements (
  practice_hour_requirement_id BIGSERIAL PRIMARY KEY,
  program_id VARCHAR NOT NULL REFERENCES programs(program_id),
  requirement_code TEXT NOT NULL,
  requirement_name TEXT NOT NULL,
  required_hours NUMERIC,
  tracking_scope TEXT NOT NULL,
  executable BOOLEAN NOT NULL DEFAULT FALSE,
  verification_method TEXT NOT NULL DEFAULT 'HUMAN_CONFIRMATION',
  description TEXT NOT NULL,
  source_url TEXT NOT NULL,
  parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
  sort_order INTEGER NOT NULL DEFAULT 0,
  UNIQUE(program_id, requirement_code)
);

INSERT INTO programs(program_id,program_name,program_overview,area_id,school,credential,program_level,study_mode,accepts_international_students,campus,delivery_method,status,source_url,last_checked,notes)
VALUES ('810ABSN','Specialty Nursing (Critical Care - Standard Option), Bachelor of Science in Nursing','The BCIT Critical Care Nursing program prepares registered nurses to care for patients who are seriously ill or injured and in failing health.','A05','School of Health Sciences','Bachelor of Science in Nursing','Bachelor''s Degree','Part-time',TRUE,'Online','Online','Active','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/',CURRENT_DATE,'Independent program record. Nursing component 44-55 credits; total 60-69 credits. Admission, clinical, PLAR and international conditions retain authoritative wording where human determination is required.')
ON CONFLICT(program_id) DO UPDATE SET program_name=EXCLUDED.program_name,program_overview=EXCLUDED.program_overview,school=EXCLUDED.school,credential=EXCLUDED.credential,program_level=EXCLUDED.program_level,study_mode=EXCLUDED.study_mode,campus=EXCLUDED.campus,delivery_method=EXCLUDED.delivery_method,status=EXCLUDED.status,source_url=EXCLUDED.source_url,last_checked=EXCLUDED.last_checked,notes=EXCLUDED.notes;

INSERT INTO curriculum_components(program_id,component_name,component_order,required_credits,notes) VALUES
('810ABSN','Required Courses',1,27,'Critical Care Health Nursing Advanced Certificate specialty courses and clinicals.'),
('810ABSN','Core/Management Component',2,18,'Required Nursing Specialty BSN core and management courses.'),
('810ABSN','Liberal Studies Component',3,6,'Named liberal studies courses in the published matrix; broader degree structure states 12 liberal studies credits.')
ON CONFLICT(program_id,component_name) DO UPDATE SET component_order=EXCLUDED.component_order,required_credits=EXCLUDED.required_credits,notes=EXCLUDED.notes;

INSERT INTO curriculum_component_courses(component_id,course_id,course_role)
SELECT cc.component_id,v.course_id,'REQUIRED' FROM curriculum_components cc JOIN (VALUES
('Required Courses','NSCC7120'),('Required Courses','NSCC7150'),('Required Courses','NSCC7220'),('Required Courses','NSCC7320'),('Required Courses','NSCC7420'),('Required Courses','NSCC7520'),('Required Courses','NSCC7620'),
('Core/Management Component','BUSA7250'),('Core/Management Component','NSSC7115'),('Core/Management Component','NSSC8000'),('Core/Management Component','NSSC8300'),('Core/Management Component','NSSC8500'),('Core/Management Component','NSSC8600'),('Core/Management Component','NSSC8800'),
('Liberal Studies Component','COMM7100'),('Liberal Studies Component','LIBS7021')) AS v(component_name,course_id) ON v.component_name=cc.component_name
WHERE cc.program_id='810ABSN' ON CONFLICT DO NOTHING;

INSERT INTO program_courses(program_id,course_id,course_type,required,notes)
SELECT '810ABSN',v.course_id,v.component,TRUE,'Published 810ABSN program matrix' FROM (VALUES
('NSCC7120','SPECIALTY'),('NSCC7150','SPECIALTY'),('NSCC7220','SPECIALTY'),('NSCC7320','SPECIALTY'),('NSCC7420','CLINICAL'),('NSCC7520','SPECIALTY'),('NSCC7620','CLINICAL'),('BUSA7250','CORE'),('NSSC7115','CORE'),('NSSC8000','CORE'),('NSSC8300','CORE'),('NSSC8500','CORE'),('NSSC8600','CORE'),('NSSC8800','CORE'),('COMM7100','LIBERAL_STUDIES'),('LIBS7021','LIBERAL_STUDIES')) AS v(course_id,component)
ON CONFLICT(program_id,course_id) DO UPDATE SET course_type=EXCLUDED.course_type,required=EXCLUDED.required,notes=EXCLUDED.notes;

DELETE FROM academic_rule_conditions WHERE rule_group_id IN (
  SELECT g.rule_group_id FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) WHERE s.program_id='810ABSN'
);
DELETE FROM academic_rule_groups WHERE rule_set_id IN (
  SELECT rule_set_id FROM academic_rule_sets WHERE program_id='810ABSN'
);
DELETE FROM academic_rule_sets WHERE program_id='810ABSN';

INSERT INTO academic_rule_sets(program_id,rule_scope,rule_name,study_mode,source_url,notes) VALUES
('810ABSN','ADMISSION','Specialty Nursing entrance requirements','PART_TIME','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/','English Category 1 (English Studies 12 at 73% or equivalent); nursing diploma; current practicing registration; minimum six months acute-care work experience and resume. Waiving and qualification decisions are at the program head''s discretion.'),
('810ABSN','TRANSFER','PLAR and transfer credit','PART_TIME','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/','Specialty course work, relevant experience, BCIT work, non-BCIT specialty courses, experiential learning and Liberal Studies transfer credit are assessed individually by faculty or the Registrar; original transcripts and course outlines are required.')
ON CONFLICT(program_id,rule_scope,rule_name,study_mode) DO UPDATE SET source_url=EXCLUDED.source_url,notes=EXCLUDED.notes;

INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order)
SELECT rule_set_id,'AND','Admission requirements',1 FROM academic_rule_sets WHERE program_id='810ABSN' AND rule_scope='ADMISSION'
ON CONFLICT DO NOTHING;

INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,minimum_value,unit,parameters,description,sort_order)
SELECT g.rule_group_id,v.condition_type,v.subject_id,v.minimum_value,v.unit,v.parameters::jsonb,v.description,v.sort_order
FROM academic_rule_groups g JOIN academic_rule_sets s USING(rule_set_id) JOIN (VALUES
('GRADE','ENGLISH_STUDIES_12',73,'PERCENT','{"executable":true}','English Studies 12 at 73% or equivalent',1),
('CREDENTIAL','NURSING_DIPLOMA',NULL,NULL,'{"executable":true}','Post-secondary diploma in nursing',2),
('LICENSURE','PRACTICING_RN_REGISTRATION',NULL,NULL,'{"executable":false,"verification":"human_confirmation"}','Current BCCNM, Canadian provincial equivalent, or RN licence outside Canada',3),
('WORK_EXPERIENCE','ACUTE_CARE',6,'MONTHS','{"executable":true,"recency_qualification":"human_confirmation"}','Minimum six months acute-care experience; exceptions and refresher need are determined by the program head',4),
('DOCUMENT','RESUME',NULL,NULL,'{"executable":false,"verification":"human_confirmation"}','Resume of work experience required',5)
) AS v(condition_type,subject_id,minimum_value,unit,parameters,description,sort_order) ON TRUE
WHERE s.program_id='810ABSN' AND s.rule_scope='ADMISSION'
AND NOT EXISTS (SELECT 1 FROM academic_rule_conditions x WHERE x.rule_group_id=g.rule_group_id AND x.subject_id=v.subject_id);

INSERT INTO clinical_placement_requirements(program_id,requirement_code,requirement_name,requirement_type,applies_to,executable,verification_method,description,source_url,parameters,sort_order) VALUES
('810ABSN','RN_REGISTRATION','Practicing RN registration','LICENSURE','EACH_CLINICAL_COURSE',FALSE,'HUMAN_CONFIRMATION','Proof of current BCCNM membership, Canadian provincial equivalent, or RN licence number is required for each clinical course.','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/','{}',1),
('810ABSN','CPR_CERTIFICATION','Current CPR certification','CERTIFICATION','CLINICAL_COURSES',FALSE,'HUMAN_CONFIRMATION','Current CPR Level C or HCP from a Canadian provider, including a practical component; original certificate required.','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/','{}',2),
('810ABSN','RESPIRATOR_FIT_TEST','N95 respirator fit testing','HEALTH_AND_SAFETY','CLINICAL_PRACTICUM',FALSE,'HUMAN_CONFIRMATION','Fit test required before practicum; original certificate and annual re-fitting required.','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/','{"renewal":"annual"}',3),
('810ABSN','INFLUENZA_POLICY','Influenza immunization or masking','HEALTH_AND_SAFETY','CLINICAL_PLACEMENT',FALSE,'HUMAN_CONFIRMATION','Proof of influenza immunization or agreement to mask during flu season is required before clinical placement.','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/','{}',4),
('810ABSN','CLINICAL_APPLICATION','Completed clinical application','DOCUMENT','NSCC7420_AND_NSCC7620',TRUE,'SELF_REPORTED','A completed clinical application is required for the clinical courses.','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/','{}',5)
ON CONFLICT(program_id,requirement_code) DO UPDATE SET requirement_name=EXCLUDED.requirement_name,requirement_type=EXCLUDED.requirement_type,applies_to=EXCLUDED.applies_to,executable=EXCLUDED.executable,verification_method=EXCLUDED.verification_method,description=EXCLUDED.description,parameters=EXCLUDED.parameters;

INSERT INTO practice_hour_requirements(program_id,requirement_code,requirement_name,required_hours,tracking_scope,executable,verification_method,description,source_url,parameters,sort_order) VALUES
('810ABSN','PUBLISHED_CLINICAL_HOURS','Clinical practice hours',NULL,'PROGRAM',FALSE,'HUMAN_CONFIRMATION','The published 810ABSN page requires clinical practice but does not state an authoritative numeric hour threshold; hours must be confirmed and tracked by BCIT.','https://www.bcit.ca/programs/specialty-nursing-critical-care-standard-option-bachelor-of-science-in-nursing-part-time-810absn/','{"clinical_courses":["NSCC7420","NSCC7620"]}',1)
ON CONFLICT(program_id,requirement_code) DO UPDATE SET required_hours=EXCLUDED.required_hours,tracking_scope=EXCLUDED.tracking_scope,executable=EXCLUDED.executable,verification_method=EXCLUDED.verification_method,description=EXCLUDED.description,parameters=EXCLUDED.parameters;

COMMIT;
