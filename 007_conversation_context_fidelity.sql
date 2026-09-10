BEGIN;

-- Keep the official structured exception set unchanged (both final-project
-- choices), while removing legacy prose that implied CMGT 8800 was the only
-- final project.
UPDATE courses
SET notes = (
    'Completion of required program coursework before the chosen final-project '
    'course. Corequisites: minimum 2 years related work experience, an industry '
    'topic, and an industry sponsor.'
)
WHERE course_id = 'CMGT8700';

UPDATE prerequisite_conditions pc
SET description = 'Completion of required program coursework before the chosen final-project course'
FROM prerequisite_groups pg
WHERE pc.prerequisite_group_id = pg.prerequisite_group_id
  AND pg.course_id = 'CMGT8700'
  AND pc.condition_type = 'PROGRAM_COURSES_COMPLETE_EXCEPT';

COMMIT;
