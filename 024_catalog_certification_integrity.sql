BEGIN;

-- The current 8660BENG page still identifies CIVL 1011 as a prerequisite for
-- CIVL 3020 and CIVL 3033. The course has been replaced in the current Level 1
-- matrix by CIVL 1012, so preserve CIVL 1011 as a historical BCIT identity
-- rather than fabricating a currently offered course.
INSERT INTO courses (
    course_id,
    course_name,
    status,
    source_url,
    last_checked,
    notes,
    display_course_code,
    area_of_study,
    subject_category,
    source_catalogue_url,
    page_title,
    description_status,
    prerequisite_status,
    import_source,
    institution_key,
    native_course_code
) VALUES (
    'CIVL1011',
    'Introduction to Civil Engineering',
    'Historical',
    'https://civil.commons.bcit.ca/pdfs/civil_eng_student_manual.pdf',
    DATE '2026-09-08',
    'Historical BCIT course identity retained because the current 8660BENG program page still cites CIVL 1011 as a prerequisite for CIVL 3020 and CIVL 3033. It is not represented as a current program-matrix course.',
    'CIVL 1011',
    'CIVL',
    'Civil Engineering',
    'https://www.bcit.ca/programs/civil-engineering-bachelor-of-engineering-full-time-8660beng/',
    'BCIT Civil Engineering Student Handbook',
    'historical_identity_only',
    'referenced_by_current_program_page',
    'catalog-certification-2026-09-08',
    'BCIT',
    'CIVL 1011'
)
ON CONFLICT (course_id) DO NOTHING;

-- The published 810MBSN elective rule allows 7000/8000-level BCIT courses or
-- third/fourth-level university-transfer courses and requires Program Head
-- approval. Align the structured flags with the already-preserved source text.
UPDATE credit_requirements
SET allows_external_courses = TRUE,
    approval_required = TRUE
WHERE program_id = '810MBSN'
  AND requirement_name = 'Complete an additional 3.0 credits of electives'
  AND minimum_credits = 3.0;

COMMIT;
