BEGIN;

CREATE TABLE IF NOT EXISTS campuses (
    campus_id BIGSERIAL PRIMARY KEY,
    institution_key TEXT NOT NULL,
    campus_key TEXT NOT NULL,
    official_name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    region TEXT,
    postal_code TEXT NOT NULL,
    main_phone TEXT NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    official_source_url TEXT NOT NULL,
    source_checked_at DATE,
    source_metadata JSONB NOT NULL DEFAULT '{}',
    notes TEXT,
    UNIQUE (institution_key, campus_key)
);

CREATE INDEX IF NOT EXISTS campuses_lookup_idx
    ON campuses (institution_key, active, campus_key);

ALTER TABLE campuses ADD COLUMN IF NOT EXISTS main_phone TEXT;

CREATE TABLE IF NOT EXISTS program_campuses (
    program_id VARCHAR(50) NOT NULL REFERENCES programs(program_id) ON DELETE CASCADE,
    institution_key TEXT NOT NULL,
    campus_key TEXT NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'offered',
    notes TEXT,
    source_url TEXT,
    PRIMARY KEY (program_id, institution_key, campus_key),
    FOREIGN KEY (institution_key, campus_key)
        REFERENCES campuses(institution_key, campus_key)
);

INSERT INTO campuses
    (institution_key, campus_key, official_name, address, city, region, postal_code, main_phone,
     description, official_source_url, source_checked_at, source_metadata, notes)
VALUES
    ('BCIT','burnaby','Burnaby Campus','3700 Willingdon Avenue','Burnaby','BC','V5G 3H2','604-434-5734',
     'BCIT''s largest campus, with classrooms, shops, labs, simulators, and other specialized learning spaces.',
     'https://www.bcit.ca/about/visit/campuses-directions/burnaby/',CURRENT_DATE,'{"publisher":"BCIT"}',NULL),
    ('BCIT','downtown','Downtown Campus','555 Seymour Street','Vancouver','BC','V6B 3H6','604-434-5734',
     'BCIT''s campus in Vancouver''s business and technology core.',
     'https://www.bcit.ca/about/visit/campuses-directions/downtown/',CURRENT_DATE,'{"publisher":"BCIT"}',NULL),
    ('BCIT','aerospace','Aerospace Technology Campus','3800 Cessna Drive','Richmond','BC','V7B 0A1','604-434-5734',
     'BCIT''s specialized aerospace training campus in Richmond.',
     'https://www.bcit.ca/about/visit/campuses-directions/aerospace-technology/',CURRENT_DATE,'{"publisher":"BCIT"}',NULL),
    ('BCIT','annacis_island','Annacis Island Campus','1608 Cliveden Avenue','Delta','BC','V3M 6P1','604-434-5734',
     'A specialized facility for motive power and heavy mechanical trades programs.',
     'https://www.bcit.ca/about/visit/campuses-directions/annacis-island/',CURRENT_DATE,'{"publisher":"BCIT"}',NULL),
    ('BCIT','marine','Marine Campus','265 West Esplanade','North Vancouver','BC','V7M 1A5','604-434-5734',
     'BCIT''s centre for maritime training in Western Canada.',
     'https://www.bcit.ca/about/visit/campuses-directions/marine/',CURRENT_DATE,'{"publisher":"BCIT"}',NULL)
ON CONFLICT (institution_key, campus_key) DO UPDATE SET
    official_name=EXCLUDED.official_name,address=EXCLUDED.address,city=EXCLUDED.city,
    region=EXCLUDED.region,postal_code=EXCLUDED.postal_code,main_phone=EXCLUDED.main_phone,description=EXCLUDED.description,
    active=TRUE,official_source_url=EXCLUDED.official_source_url,
    source_checked_at=EXCLUDED.source_checked_at,source_metadata=EXCLUDED.source_metadata,
    notes=EXCLUDED.notes;

ALTER TABLE campuses ALTER COLUMN main_phone SET NOT NULL;

INSERT INTO program_campuses(program_id,institution_key,campus_key,relationship_type,notes,source_url)
SELECT program_id,'BCIT','burnaby','offered',campus,source_url FROM programs
 WHERE status='Active' AND campus ~* 'Burnaby'
UNION ALL
SELECT program_id,'BCIT','downtown',
       CASE WHEN campus ~* 'possible Downtown' THEN 'possible' ELSE 'offered' END,
       campus,source_url FROM programs WHERE status='Active' AND campus ~* 'Downtown'
UNION ALL
SELECT program_id,'BCIT','aerospace','offered',campus,source_url FROM programs
 WHERE status='Active' AND campus ~* 'Aerospace'
ON CONFLICT (program_id,institution_key,campus_key) DO UPDATE SET
 relationship_type=EXCLUDED.relationship_type,notes=EXCLUDED.notes,source_url=EXCLUDED.source_url;

COMMIT;
