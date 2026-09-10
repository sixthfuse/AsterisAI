BEGIN;

-- Express the Year-4 completion alternatives as an explicit reusable OR tree.
INSERT INTO curriculum_requirements(
    program_id, component_id, requirement_code, requirement_type,
    institution_key, executable, verification_method, description,
    parameters, source_url, sort_order
)
SELECT '9940BSC', component_id, 'Y4_COMPLETION_PATH', 'ANY_OF', 'UBC', TRUE,
       'deterministic_transcript_evaluation',
       'Complete either the thesis or advanced biochemical techniques pathway.',
       '{"operator":"OR"}'::jsonb, source_url, 10
FROM curriculum_requirements
WHERE program_id='9940BSC' AND requirement_code='Y4_PATH_1'
ON CONFLICT(program_id,requirement_code) DO UPDATE
SET requirement_type=EXCLUDED.requirement_type, executable=TRUE,
    verification_method=EXCLUDED.verification_method,
    parameters=EXCLUDED.parameters;

UPDATE curriculum_requirements
SET executable=TRUE, verification_method='deterministic_transcript_evaluation'
WHERE program_id='9940BSC'
  AND requirement_code IN ('Y1_CHEMISTRY','Y1_CALCULUS','Y1_DATA_SCIENCE',
      'Y2_COMPUTING_OR_STATISTICS','Y3_FSCT_POOL','Y4_PATH_1','Y4_PATH_2',
      'Y4_FSCT_UPPER_ELECTIVE');

UPDATE curriculum_requirements
SET parent_requirement_code='Y4_COMPLETION_PATH',
    parameters=parameters || CASE requirement_code
      WHEN 'Y4_PATH_1' THEN '{"required_course_ids":["UBC-BIOC-449"]}'::jsonb
      ELSE '{"required_course_ids":["UBC-BIOC-420"]}'::jsonb END
WHERE program_id='9940BSC' AND requirement_code IN ('Y4_PATH_1','Y4_PATH_2');

UPDATE curriculum_requirements
SET executable=TRUE,
    verification_method='deterministic_transcript_evaluation',
    parameters=parameters || '{"subject":"PHYS","minimum_level":100,"excluded_native_course_codes":["PHYS 100"]}'::jsonb
WHERE program_id='9940BSC' AND requirement_code='Y1_PHYSICS_GRADUATION_ONLY';

COMMIT;
