BEGIN;

CREATE TABLE IF NOT EXISTS institutional_resources (
    institutional_resource_id BIGSERIAL PRIMARY KEY,
    institution_key TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    title TEXT NOT NULL,
    official_url TEXT NOT NULL,
    topic TEXT NOT NULL,
    trigger_phrases TEXT[] NOT NULL DEFAULT '{}',
    normalized_intents TEXT[] NOT NULL DEFAULT '{}',
    description TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100 CHECK (priority >= 0),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    source_type TEXT NOT NULL DEFAULT 'official_institution_page',
    source_checked_at DATE,
    source_metadata JSONB NOT NULL DEFAULT '{}',
    UNIQUE (institution_key, resource_key)
);

CREATE INDEX IF NOT EXISTS institutional_resources_lookup_idx
    ON institutional_resources (institution_key, active, priority, resource_key);

INSERT INTO institutional_resources
    (institution_key, resource_key, title, official_url, topic, trigger_phrases,
     normalized_intents, description, priority, active, source_checked_at, source_metadata)
VALUES
    ('BCIT', 'equivalencies', 'BCIT Equivalencies', 'https://www.bcit.ca/admission/entrance-requirements/equivalencies/', 'equivalencies', ARRAY['equivalency', 'equivalencies', 'equivalent course', 'course equivalent', 'requirement equivalency'], ARRAY['EQUIVALENCIES'], 'Find Canadian, international, and post-secondary entrance-requirement equivalencies.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'admissions', 'BCIT Admissions', 'https://www.bcit.ca/admission/', 'admissions', ARRAY['admission', 'admissions', 'admission requirement', 'admission requirements'], ARRAY['ADMISSIONS'], 'Start with BCIT admissions information and entrance requirements.', 20, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'international_students', 'BCIT International Students', 'https://www.bcit.ca/international-students/', 'international_students', ARRAY['international student', 'international students', 'international applicant', 'study permit'], ARRAY['INTERNATIONAL_STUDENTS'], 'Programs, services, permits, guides, and support for international students.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'english_language_proficiency', 'BCIT English Language Proficiency', 'https://www.bcit.ca/admission/entrance-requirements/english-language-proficiency/', 'english_language', ARRAY['english language requirement', 'english language requirements', 'english proficiency', 'language proficiency', 'ielts', 'toefl', 'duolingo english'], ARRAY['ENGLISH_LANGUAGE_REQUIREMENTS'], 'Review BCIT English-language proficiency categories and accepted assessments.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'tuition_fees', 'BCIT Tuition & Fees', 'https://www.bcit.ca/admission/tuition-fees/', 'tuition_and_fees', ARRAY['tuition', 'tuition fees', 'program cost', 'course cost', 'cost of attendance', 'how much does bcit cost', 'student fees'], ARRAY['TUITION_AND_FEES'], 'Find tuition, fee, estimator, payment, and refund information.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'financial_aid_awards', 'BCIT Student Financial Aid & Awards', 'https://www.bcit.ca/financial-aid/', 'financial_aid', ARRAY['financial aid', 'student funding', 'scholarship', 'scholarships', 'bursary', 'bursaries', 'student loan', 'awards'], ARRAY['FINANCIAL_AID'], 'Explore loans, grants, scholarships, bursaries, awards, and emergency funding.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'transfer_credit', 'BCIT Transfer Credit', 'https://www.bcit.ca/admission/entrance-requirements/transfer-credit/', 'transfer_credit', ARRAY['transfer credit', 'transfer credits', 'course credit', 'advanced placement'], ARRAY['TRANSFER_CREDIT'], 'Search transfer equivalencies and review transfer-credit and advanced-placement routes.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'plar', 'BCIT Prior Learning Assessment & Recognition', 'https://www.bcit.ca/admission/entrance-requirements/transfer-credit/prior-learning-assessment-recognition/', 'prior_learning', ARRAY['plar', 'prior learning', 'prior learning assessment', 'recognition of prior learning'], ARRAY['PLAR'], 'Learn how prior informal or experiential learning may be assessed for course credit.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'program_availability', 'BCIT Program Availability', 'https://www.bcit.ca/admission/program-availability/', 'program_availability', ARRAY['program availability', 'program available', 'applications open', 'accepting applications', 'application open', 'program full'], ARRAY['PROGRAM_AVAILABILITY'], 'Check current program availability and application status by intake.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'application_process', 'How to Apply to BCIT', 'https://www.bcit.ca/admission/how-to-apply/', 'application_process', ARRAY['how to apply', 'application process', 'apply to bcit', 'submit application', 'application deadline', 'application deadlines', 'when to apply'], ARRAY['APPLICATION_PROCESS'], 'Review application steps, documents, timing, and applicant routes.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'application_status', 'BCIT Application Status', 'https://www.bcit.ca/admission/after-you-apply/application-status/', 'application_status', ARRAY['application status', 'check my application', 'after i apply', 'after applying', 'admission decision'], ARRAY['APPLICATION_STATUS'], 'Track an application and understand BCIT application and decision statuses.', 10, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}'),
    ('BCIT', 'program_advising', 'BCIT Program Advising', 'https://www.bcit.ca/advising/', 'advising', ARRAY['program advising', 'academic advising', 'academic advisor', 'program advisor', 'talk to an advisor', 'contact an advisor'], ARRAY['ADVISING'], 'Contact BCIT Program Advising for help planning academic next steps.', 20, TRUE, CURRENT_DATE, '{"publisher":"BCIT"}')
ON CONFLICT (institution_key, resource_key) DO UPDATE SET
    title = EXCLUDED.title, official_url = EXCLUDED.official_url, topic = EXCLUDED.topic,
    trigger_phrases = EXCLUDED.trigger_phrases, normalized_intents = EXCLUDED.normalized_intents,
    description = EXCLUDED.description, priority = EXCLUDED.priority, active = EXCLUDED.active,
    source_type = EXCLUDED.source_type, source_checked_at = EXCLUDED.source_checked_at,
    source_metadata = EXCLUDED.source_metadata;

COMMIT;
