-- Main full-time BSN facts. Specialty Nursing programs remain independent.
CREATE TABLE IF NOT EXISTS program_delivery_facts (
    program_id varchar(20) PRIMARY KEY REFERENCES programs(program_id) ON DELETE CASCADE,
    duration_years numeric,
    terms_per_year integer,
    total_credits numeric,
    intake_months jsonb NOT NULL DEFAULT '[]'::jsonb,
    international_eligibility text,
    authoritative_raw text,
    source_url text NOT NULL,
    last_checked date NOT NULL DEFAULT CURRENT_DATE
);
