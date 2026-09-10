BEGIN;

-- Preserve the official Option 1 meaning: the set is required for graduation,
-- while each individual course remains an alternative rather than mandatory.
UPDATE curriculum_requirements
SET description = 'Three credits from the required alternative set DSCI 100 or CPSC 103; required for graduation, not admission. Neither course is individually mandatory; an institution-approved transfer or equivalent may satisfy the requirement.',
    requirement_type = 'alternative_courses',
    institution_key = 'UBC',
    minimum_credits = 3,
    exact_course_count = 1,
    executable = TRUE,
    verification_method = 'deterministic_transcript_evaluation',
    parameters = COALESCE(parameters, '{}'::jsonb) ||
        '{"scope":"GRADUATION","required_alternative":true,"individual_options_mandatory":false,"approved_equivalent_allowed":true,"equivalent_verification":"institution_confirmation"}'::jsonb
WHERE program_id = '9940BSC'
  AND requirement_code = 'Y1_DATA_SCIENCE';

UPDATE curriculum_requirement_courses rc
SET course_role = 'REQUIRED_ALTERNATIVE'
FROM curriculum_requirements r
WHERE r.curriculum_requirement_id = rc.curriculum_requirement_id
  AND r.program_id = '9940BSC'
  AND r.requirement_code = 'Y1_DATA_SCIENCE';

UPDATE courses
SET credits = 3
WHERE course_id IN ('UBC-DSCI-100', 'UBC-CPSC-103')
  AND institution_key = 'UBC';

COMMIT;
