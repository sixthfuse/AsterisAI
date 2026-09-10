BEGIN;

CREATE TABLE IF NOT EXISTS institutions (
    institution_key TEXT PRIMARY KEY,
    official_name TEXT NOT NULL,
    official_url TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO institutions(institution_key,official_name,official_url) VALUES
 ('BCIT','British Columbia Institute of Technology','https://www.bcit.ca/'),
 ('UBC','University of British Columbia','https://www.ubc.ca/')
ON CONFLICT(institution_key) DO UPDATE SET official_name=EXCLUDED.official_name,
 official_url=EXCLUDED.official_url,active=TRUE;

ALTER TABLE courses ADD COLUMN IF NOT EXISTS institution_key TEXT REFERENCES institutions(institution_key);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS native_course_code TEXT;
UPDATE courses SET institution_key='BCIT' WHERE institution_key IS NULL;
UPDATE courses SET native_course_code=display_course_code WHERE native_course_code IS NULL;
ALTER TABLE courses ALTER COLUMN institution_key SET DEFAULT 'BCIT';
ALTER TABLE courses ALTER COLUMN institution_key SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_courses_institution_native_code
 ON courses(institution_key,native_course_code) WHERE native_course_code IS NOT NULL;

CREATE TABLE IF NOT EXISTS curriculum_requirements (
    curriculum_requirement_id BIGSERIAL PRIMARY KEY,
    program_id VARCHAR(32) NOT NULL REFERENCES programs(program_id),
    component_id BIGINT REFERENCES curriculum_components(component_id),
    requirement_code TEXT NOT NULL,
    requirement_type TEXT NOT NULL,
    institution_key TEXT REFERENCES institutions(institution_key),
    minimum_credits NUMERIC,
    exact_course_count INTEGER,
    double_count_prohibited BOOLEAN NOT NULL DEFAULT FALSE,
    parent_requirement_code TEXT,
    executable BOOLEAN NOT NULL DEFAULT FALSE,
    verification_method TEXT,
    description TEXT NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_url TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 1,
    UNIQUE(program_id,requirement_code)
);

CREATE TABLE IF NOT EXISTS curriculum_requirement_courses (
    curriculum_requirement_id BIGINT NOT NULL REFERENCES curriculum_requirements(curriculum_requirement_id) ON DELETE CASCADE,
    course_id VARCHAR(32) NOT NULL REFERENCES courses(course_id),
    course_role TEXT NOT NULL DEFAULT 'OPTION',
    PRIMARY KEY(curriculum_requirement_id,course_id)
);

COMMIT;
