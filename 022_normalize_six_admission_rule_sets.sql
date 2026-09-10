-- Normalize the final six active programs onto the singular ADMISSION scope.
-- This migration is deliberately admissions-only: progression, completion,
-- attendance, and regulator rules remain in their existing scopes.
BEGIN;

-- The AME importer originally emitted the plural scope ADMISSIONS.  Preserve
-- every rule and condition, changing only the generalized scope spelling.
UPDATE academic_rule_sets
SET rule_scope = 'ADMISSION'
WHERE program_id IN ('1165DIPMA', '1230DIPMA', '1205DIPMA')
  AND rule_scope = 'ADMISSIONS';

-- Make the deterministic grade comparator able to recognize the AME English
-- and mathematics subjects without changing the stored thresholds.
UPDATE academic_rule_conditions arc
SET condition_type = 'GRADE',
    subject_id = 'ENGLISH_STUDIES_12',
    parameters = COALESCE(arc.parameters, '{}'::jsonb) ||
      CASE ars.rule_name
        WHEN 'ENGLISH_AFTER_2026_09_30' THEN
          '{"semantic":"threshold","executable":true,"effective_for_applications_after":"2026-09-30"}'::jsonb
        ELSE '{"semantic":"threshold","executable":true,"accepted_equivalent_or_assessment":true}'::jsonb
      END
FROM academic_rule_groups arg
JOIN academic_rule_sets ars ON ars.rule_set_id = arg.rule_set_id
WHERE arc.rule_group_id = arg.rule_group_id
  AND ars.program_id IN ('1165DIPMA', '1230DIPMA', '1205DIPMA')
  AND ars.rule_scope = 'ADMISSION'
  AND ars.rule_name IN ('ENGLISH_CURRENT', 'ENGLISH_AFTER_2026_09_30');

UPDATE academic_rule_conditions arc
SET condition_type = 'GRADE',
    subject_id = 'MATH_11',
    accepted_values = '["Pre-Calculus 11", "Foundations of Math 11", "Workplace Math 11", "accepted BC/Yukon equivalent", "BCIT Math Trades Entry Assessment"]'::jsonb,
    parameters = COALESCE(arc.parameters, '{}'::jsonb) ||
      '{"semantic":"alternative_subject_or_assessment","executable":true,"accepted_equivalent_or_assessment":true}'::jsonb
FROM academic_rule_groups arg
JOIN academic_rule_sets ars ON ars.rule_set_id = arg.rule_set_id
WHERE arc.rule_group_id = arg.rule_group_id
  AND ars.program_id IN ('1165DIPMA', '1230DIPMA', '1205DIPMA')
  AND ars.rule_scope = 'ADMISSION' AND ars.rule_name = 'MATH';

UPDATE academic_rule_conditions arc
SET parameters = COALESCE(arc.parameters, '{}'::jsonb) ||
    '{"semantic":"intake_transition","executable":false,"human_confirmation":true,"effective_intake":"2027-01"}'::jsonb
FROM academic_rule_groups arg
JOIN academic_rule_sets ars ON ars.rule_set_id = arg.rule_set_id
WHERE arc.rule_group_id = arg.rule_group_id
  AND ars.program_id = '1230DIPMA'
  AND ars.rule_scope = 'ADMISSION'
  AND ars.rule_name = 'MECHANICAL_REASONING_TRANSITION';

INSERT INTO academic_rule_conditions
  (rule_group_id, condition_type, subject_id, parameters, description, sort_order)
SELECT arg.rule_group_id, 'ASSESSMENT', 'BCIT_MECHANICAL_REASONING_TRADES_ENTRY_ASSESSMENT',
       '{"semantic":"intake_transition","executable":false,"human_confirmation":true,"required_before_intake":"2027-01"}'::jsonb,
       'BCIT Mechanical Reasoning Trades Entry Assessment is listed for current intakes and is removed for January 2027 and later intakes; confirm the applicant intake.', 2
FROM academic_rule_sets ars
JOIN academic_rule_groups arg USING(rule_set_id)
WHERE ars.program_id='1230DIPMA' AND ars.rule_scope='ADMISSION'
  AND ars.rule_name='MECHANICAL_REASONING_TRANSITION'
  AND NOT EXISTS (
    SELECT 1 FROM academic_rule_conditions arc
    WHERE arc.rule_group_id=arg.rule_group_id
      AND arc.subject_id='BCIT_MECHANICAL_REASONING_TRADES_ENTRY_ASSESSMENT'
  );

-- Applied Circular Economy has no formal program application or mandatory
-- program-specific entrance requirement.  Industry background is recommended,
-- not an eligibility gate.
INSERT INTO academic_rule_sets
  (program_id, rule_scope, rule_name, study_mode, source_url, notes)
VALUES
  ('0816CM', 'ADMISSION', 'NO_FORMAL_PROGRAM_APPLICATION', 'Part-time',
   'https://www.bcit.ca/programs/applied-circular-economy-zero-waste-buildings-microcredential-part-time-0816cm/',
   'Formal application to the microcredential is not required. Students register course-by-course. Construction, building-design, environmental-engineering, or related experience is recommended for success, not required for admission.')
ON CONFLICT (program_id, rule_scope, rule_name, study_mode) DO UPDATE
SET source_url = EXCLUDED.source_url, notes = EXCLUDED.notes;

WITH rs AS (
  SELECT rule_set_id FROM academic_rule_sets
  WHERE program_id='0816CM' AND rule_scope='ADMISSION'
    AND rule_name='NO_FORMAL_PROGRAM_APPLICATION' AND study_mode='Part-time'
), g AS (
  INSERT INTO academic_rule_groups(rule_set_id, operator, label, sort_order)
  SELECT rule_set_id, 'AND', 'No program-specific admission gate', 1 FROM rs
  WHERE NOT EXISTS (SELECT 1 FROM academic_rule_groups x WHERE x.rule_set_id=rs.rule_set_id)
  RETURNING rule_group_id
)
INSERT INTO academic_rule_conditions
  (rule_group_id, condition_type, parameters, description, sort_order)
SELECT rule_group_id, 'NO_FORMAL_APPLICATION_REQUIRED',
       '{"semantic":"no_program_specific_admission_requirements","executable":true,"recommended_background_is_not_required":true}'::jsonb,
       'Formal application is not required; register in the courses directly. Listed industry or educational background is recommended for success only.', 1
FROM g;

-- The diploma is not a separately admitted program.  It is conferred after the
-- first two years of the Civil Engineering BEng route.
INSERT INTO academic_rule_sets
  (program_id, rule_scope, rule_name, study_mode, source_url, notes)
VALUES
  ('5410DIPLT', 'ADMISSION', 'APPLY_THROUGH_CIVIL_BENG', 'Full-time',
   'https://www.bcit.ca/programs/civil-engineering-diploma-full-time-5410diplt/',
   'There is no separate Diploma application. To obtain the Diploma, apply to the full-time Civil Engineering Bachelor of Engineering program; the Diploma is conferred after successful completion of its first two years.')
ON CONFLICT (program_id, rule_scope, rule_name, study_mode) DO UPDATE
SET source_url = EXCLUDED.source_url, notes = EXCLUDED.notes;

WITH rs AS (
  SELECT rule_set_id FROM academic_rule_sets
  WHERE program_id='5410DIPLT' AND rule_scope='ADMISSION'
    AND rule_name='APPLY_THROUGH_CIVIL_BENG' AND study_mode='Full-time'
), g AS (
  INSERT INTO academic_rule_groups(rule_set_id, operator, label, sort_order)
  SELECT rule_set_id, 'AND', 'Application route', 1 FROM rs
  WHERE NOT EXISTS (SELECT 1 FROM academic_rule_groups x WHERE x.rule_set_id=rs.rule_set_id)
  RETURNING rule_group_id
)
INSERT INTO academic_rule_conditions
  (rule_group_id, condition_type, subject_id, parameters, description, sort_order)
SELECT rule_group_id, 'LINKED_PROGRAM_ADMISSION', '8660BENG',
       '{"semantic":"linked_application_route","executable":false,"human_confirmation":true,"separate_diploma_application":false}'::jsonb,
       'Apply to Civil Engineering Bachelor of Engineering (8660BENG); BCIT does not publish a separate Diploma admission route.', 1
FROM g;

-- Initial competitive admission to Civil Engineering BEng.  Ranking and the
-- mandatory questionnaire are review steps, not invented transcript logic.
INSERT INTO academic_rule_sets
  (program_id, rule_scope, rule_name, study_mode, source_url, notes)
VALUES
  ('8660BENG', 'ADMISSION', 'COMPETITIVE_INITIAL_ADMISSION', 'Full-time',
   'https://www.bcit.ca/programs/civil-engineering-bachelor-of-engineering-full-time-8660beng/',
   'Competitive initial admission requires high-school graduation, Category 1 English, specified mathematics and sciences, one approved Grade 12 academic course, and the Mandatory Applicant Questionnaire. Departmental ranking is a human institutional decision. Level 5 continuation is not an admission condition in this rule set.')
ON CONFLICT (program_id, rule_scope, rule_name, study_mode) DO UPDATE
SET source_url = EXCLUDED.source_url, notes = EXCLUDED.notes;

WITH rs AS (
  SELECT rule_set_id FROM academic_rule_sets
  WHERE program_id='8660BENG' AND rule_scope='ADMISSION'
    AND rule_name='COMPETITIVE_INITIAL_ADMISSION' AND study_mode='Full-time'
), g AS (
  INSERT INTO academic_rule_groups(rule_set_id, operator, label, sort_order)
  SELECT rule_set_id, 'AND', 'Step 1 minimum requirements and Step 2 assessment', 1 FROM rs
  WHERE NOT EXISTS (SELECT 1 FROM academic_rule_groups x WHERE x.rule_set_id=rs.rule_set_id)
  RETURNING rule_group_id
)
INSERT INTO academic_rule_conditions
  (rule_group_id, condition_type, subject_id, minimum_value, unit, accepted_values, parameters, description, sort_order)
SELECT g.rule_group_id, v.condition_type, v.subject_id, v.minimum_value, v.unit,
       v.accepted_values::jsonb, v.parameters::jsonb, v.description, v.sort_order
FROM g CROSS JOIN (VALUES
  ('HIGH_SCHOOL_GRADUATION', NULL, NULL::numeric, NULL, NULL,
   '{"semantic":"credential","executable":true}', 'High school graduation.', 1),
  ('GRADE', 'ENGLISH_STUDIES_12', 73, 'PERCENT', '["Category 1 equivalent"]',
   '{"semantic":"threshold","executable":true,"accepted_equivalent":true}', 'Category 1 English: English Studies 12 at 73% or equivalent.', 2),
  ('GRADE', 'PRE_CALCULUS_12', 73, 'PERCENT', '["accepted BC/Yukon equivalent"]',
   '{"semantic":"threshold","executable":true,"accepted_equivalent":true}', 'Pre-Calculus 12 at 73% or another accepted BC/Yukon course.', 3),
  ('GRADE', 'CHEMISTRY_11', 73, 'PERCENT', NULL,
   '{"semantic":"threshold","executable":true}', 'Chemistry 11 at 73%.', 4),
  ('GRADE', 'PHYSICS_12', 73, 'PERCENT', NULL,
   '{"semantic":"threshold","executable":true}', 'Physics 12 at 73%.', 5),
  ('GRADE', 'APPROVED_GRADE_12_ACADEMIC_COURSE', 73, 'PERCENT', NULL,
   '{"semantic":"threshold","executable":false,"human_confirmation":true,"reason":"approved-course list requires institutional equivalency confirmation"}', 'One approved Grade 12 academic course at 73%.', 6),
  ('DOCUMENT', 'MANDATORY_APPLICANT_QUESTIONNAIRE', NULL, NULL, NULL,
   '{"semantic":"document","executable":false,"human_confirmation":true}', 'Submit the Mandatory Applicant Questionnaire for competitive selection.', 7),
  ('DEPARTMENT_ASSESSMENT', 'COMPETITIVE_RANKING', NULL, NULL, NULL,
   '{"semantic":"institutional_decision","executable":false,"human_confirmation":true}', 'The program area ranks qualified applicants using academic success, recency, and complete records.', 8)
) AS v(condition_type, subject_id, minimum_value, unit, accepted_values, parameters, description, sort_order);

COMMIT;
