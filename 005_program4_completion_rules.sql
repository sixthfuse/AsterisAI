BEGIN;
DO $$
DECLARE rs BIGINT; root_group BIGINT; choice_group BIGINT;
BEGIN
  SELECT rule_set_id INTO rs FROM academic_rule_sets
  WHERE program_id='8800BTECH' AND rule_scope='CONTINUATION'
    AND rule_name='Capstone and graduation work experience';
  IF NOT EXISTS (SELECT 1 FROM academic_rule_groups WHERE rule_set_id=rs) THEN
    INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order)
    VALUES(rs,'AND','Capstone and graduation eligibility',1)
    RETURNING rule_group_id INTO root_group;
    INSERT INTO academic_rule_conditions(rule_group_id,condition_type,minimum_value,unit,parameters,description)
    VALUES(root_group,'WORK_EXPERIENCE',2,'YEAR',
      '{"field":"related","admission_experience_counts":true}',
      'Minimum 2 years related work experience total; qualifying admission experience counts toward the total');
  END IF;

  SELECT rule_set_id INTO rs FROM academic_rule_sets
  WHERE program_id='8800BTECH' AND rule_scope='COMPLETION'
    AND rule_name='Professional Standards capstone choice';
  IF NOT EXISTS (SELECT 1 FROM academic_rule_groups WHERE rule_set_id=rs) THEN
    INSERT INTO academic_rule_groups(rule_set_id,operator,label,sort_order)
    VALUES(rs,'AND','Professional Standards',1)
    RETURNING rule_group_id INTO root_group;
    INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,description,sort_order)
    VALUES(root_group,'COURSE','CMGT8700','Complete CMGT 8700',1);
    INSERT INTO academic_rule_groups(rule_set_id,parent_group_id,operator,label,sort_order)
    VALUES(rs,root_group,'OR','Choose one final project',2)
    RETURNING rule_group_id INTO choice_group;
    INSERT INTO academic_rule_conditions(rule_group_id,condition_type,subject_id,minimum_value,unit,description,sort_order)
    VALUES(choice_group,'COURSE','CMGT8800',50,'PERCENT','CMGT 8800 after CMGT 8700 and department approval',1),
          (choice_group,'COURSE','CMGT8810',50,'PERCENT','CMGT 8810 after CMGT 8700 and department approval',2);
  END IF;
END $$;
COMMIT;
