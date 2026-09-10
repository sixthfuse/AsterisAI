-- Generalized advisor-quality correction: remove unsupported 9940BSC CRC timing.
UPDATE academic_rule_conditions arc
SET description = 'A criminal record check is an entrance requirement; timing is not verified in the stored source data.',
    parameters = COALESCE(parameters, '{}'::jsonb) - 'timing' ||
                 '{"human_confirmation": true, "timing_verified": false}'::jsonb
FROM academic_rule_groups arg
JOIN academic_rule_sets ars ON ars.rule_set_id = arg.rule_set_id
WHERE arc.rule_group_id = arg.rule_group_id
  AND ars.program_id = '9940BSC'
  AND ars.rule_name = 'CRIMINAL_RECORD_CHECK';

UPDATE academic_rule_sets
SET notes = 'A criminal record check is an entrance requirement; timing is not verified in the stored source data.'
WHERE program_id = '9940BSC' AND rule_name = 'CRIMINAL_RECORD_CHECK';

UPDATE academic_rule_sets
SET notes = 'Option 1 UBC pathway: eligible for the honours specialization, with minimum GPA 76% (70% for September 2026), 8.0 credits of UBC Chemistry (CHEM 121, 111, or 141, plus CHEM 123), 3.0 credits satisfying the UBC Communication Requirement, BIOL 112, and 3.0 credits of differential calculus.'
WHERE program_id = '9940BSC' AND rule_name = 'ADMISSION_PATH_UBC';

UPDATE academic_rule_conditions arc
SET description = ars.notes
FROM academic_rule_groups arg
JOIN academic_rule_sets ars ON ars.rule_set_id = arg.rule_set_id
WHERE arc.rule_group_id = arg.rule_group_id
  AND ars.program_id = '9940BSC'
  AND ars.rule_name = 'ADMISSION_PATH_UBC';

UPDATE curriculum_requirements
SET description = 'Three credits satisfying the UBC Communication Requirement; required for Option 1 admission.'
WHERE program_id = '9940BSC' AND requirement_code = 'Y1_ADDITIONAL_COMMUNICATION';

UPDATE curriculum_requirements
SET description = 'Eight credits of electives; required for graduation, not admission.'
WHERE program_id = '9940BSC' AND requirement_code = 'Y1_ELECTIVES';

INSERT INTO curriculum_requirements
    (program_id, component_id, requirement_code, requirement_type, institution_key,
     minimum_credits, double_count_prohibited, executable, verification_method,
     description, parameters, source_url, sort_order)
SELECT '9940BSC', component_id, 'Y1_ENGLISH_GRADUATION_ONLY', 'subject_credits', 'UBC',
       3, FALSE, TRUE, 'deterministic_transcript_evaluation',
       'Three credits of 100-level UBC English; required for graduation, not admission.',
       '{"official_matrix": true, "subject": "ENGL", "minimum_level": 100}'::jsonb,
       'https://www.bcit.ca/programs/combined-honours-in-biochemistry-and-forensic-science-bachelor-of-science-full-time-9940bsc/', 6
FROM curriculum_components
WHERE program_id = '9940BSC' AND component_name LIKE 'Year 1%'
ORDER BY component_order LIMIT 1
ON CONFLICT (program_id, requirement_code) DO UPDATE
SET description = EXCLUDED.description, parameters = EXCLUDED.parameters,
    executable = TRUE, verification_method = EXCLUDED.verification_method;
