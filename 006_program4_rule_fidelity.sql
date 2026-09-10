BEGIN;
DO $$
DECLARE rs BIGINT; root_group BIGINT;
BEGIN
  SELECT rule_set_id INTO rs FROM academic_rule_sets
  WHERE program_id='8800BTECH' AND rule_scope='ADMISSION';
  SELECT rule_group_id INTO root_group FROM academic_rule_groups
  WHERE rule_set_id=rs AND parent_group_id IS NULL ORDER BY rule_group_id LIMIT 1;
  IF NOT EXISTS (SELECT 1 FROM academic_rule_conditions WHERE rule_group_id=root_group AND condition_type='INTERNATIONAL_CREDENTIAL_EVALUATION') THEN
    INSERT INTO academic_rule_conditions(rule_group_id,condition_type,accepted_values,parameters,description,sort_order)
    VALUES(root_group,'INTERNATIONAL_CREDENTIAL_EVALUATION',
      '["ICES comprehensive evaluation","accepted Canadian credential-assessment service"]',
      '{"applies_outside":["Canada","United States","United Kingdom","Australia","New Zealand"],"requires":"course-by-course evaluation and GPA calculation"}',
      'Specified international post-secondary credentials require an accepted comprehensive credential evaluation',4),
      (root_group,'CREDENTIAL_EXCLUSION','["master''s degree alone"]','{}',
      'A master''s degree alone is not sufficient for admission',5);
  END IF;
END $$;

-- Preserve the three alternative Liberal Studies entry forms as OR conditions.
DO $$
DECLARE target TEXT; gid BIGINT;
BEGIN
  FOREACH target IN ARRAY ARRAY['LIBS7001','LIBS7002','LIBS7013'] LOOP
    DELETE FROM prerequisite_conditions WHERE prerequisite_group_id IN
      (SELECT prerequisite_group_id FROM prerequisite_groups WHERE course_id=target);
    DELETE FROM prerequisite_groups WHERE course_id=target;
    INSERT INTO prerequisite_groups(course_id,group_type) VALUES(target,'OR')
      RETURNING prerequisite_group_id INTO gid;
    INSERT INTO prerequisite_conditions(prerequisite_group_id,prerequisite_course_id,minimum_grade,condition_type,parameters,description,notes) VALUES
      (gid,'ENGL1177',CASE WHEN target='LIBS7001' THEN '50' ELSE NULL END,'COURSE','{}','BCIT ENGL 1177 or equivalent','Alternative 1 of 3'),
      (gid,NULL,NULL,'COMMUNICATION_CREDITS','{"minimum_credits":6,"institution":"BCIT","minimum_level":1100}','6 credits of BCIT Communication at 1100-level or above','Alternative 2 of 3'),
      (gid,NULL,NULL,'POSTSECONDARY_SUBJECT_CREDITS','{"minimum_credits":3,"level":"first-year","subjects":["social science","humanities"]}','3 credits of first-year university/college social science or humanities','Alternative 3 of 3');
  END LOOP;
END $$;

INSERT INTO prerequisite_conditions(prerequisite_group_id,condition_type,description,notes)
SELECT pg.prerequisite_group_id,'DEPARTMENT_APPROVAL','Department approval required','Department approval required'
FROM prerequisite_groups pg WHERE pg.course_id IN ('CMGT8800','CMGT8810')
AND NOT EXISTS (SELECT 1 FROM prerequisite_conditions pc WHERE pc.prerequisite_group_id=pg.prerequisite_group_id AND pc.condition_type='DEPARTMENT_APPROVAL');
COMMIT;
