BEGIN;

CREATE TABLE IF NOT EXISTS program_import_approvals (
    approval_id BIGSERIAL PRIMARY KEY,
    program_id VARCHAR(32) NOT NULL,
    payload_sha256 CHAR(64) NOT NULL,
    approved_by TEXT NOT NULL,
    approved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approval_status VARCHAR(16) NOT NULL DEFAULT 'approved'
        CHECK (approval_status IN ('approved','revoked')),
    review_notes TEXT,
    UNIQUE(program_id, payload_sha256)
);

ALTER TABLE program_import_revisions
    ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(24) NOT NULL DEFAULT 'staged';
ALTER TABLE program_import_revisions DROP CONSTRAINT IF EXISTS program_import_revisions_lifecycle_status_check;
ALTER TABLE program_import_revisions ADD CONSTRAINT program_import_revisions_lifecycle_status_check
    CHECK (lifecycle_status IN ('staged','approved','active','superseded','rolled-back'));

CREATE TABLE IF NOT EXISTS program_import_revision_transitions (
    transition_id BIGSERIAL PRIMARY KEY,
    revision_id BIGINT NOT NULL REFERENCES program_import_revisions(revision_id),
    from_status VARCHAR(24),
    to_status VARCHAR(24) NOT NULL CHECK (to_status IN ('staged','approved','active','superseded','rolled-back')),
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS program_active_import_revisions (
    program_id VARCHAR(32) PRIMARY KEY REFERENCES programs(program_id),
    revision_id BIGINT NOT NULL UNIQUE REFERENCES program_import_revisions(revision_id),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS program_advisor_aliases (
    alias_id BIGSERIAL PRIMARY KEY,
    normalized_alias TEXT NOT NULL UNIQUE,
    program_id VARCHAR(32) REFERENCES programs(program_id),
    alias_scope VARCHAR(24) NOT NULL DEFAULT 'program'
        CHECK (alias_scope IN ('program','family','category')),
    family_key TEXT,
    priority INTEGER NOT NULL DEFAULT 100,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK ((alias_scope='program' AND program_id IS NOT NULL) OR
           (alias_scope<>'program' AND family_key IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS program_relationships (
    relationship_id BIGSERIAL PRIMARY KEY,
    program_id VARCHAR(32) NOT NULL REFERENCES programs(program_id),
    related_program_id VARCHAR(32) REFERENCES programs(program_id),
    relationship_type VARCHAR(32) NOT NULL,
    relationship_key TEXT NOT NULL,
    independent_program BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(program_id, relationship_type, relationship_key)
);

INSERT INTO program_advisor_aliases(normalized_alias,program_id,priority) VALUES
 ('applied computing','M600MSC',10),('applied computing msc','M600MSC',10),
 ('master of science in applied computing','M600MSC',10),('computing masters','M600MSC',20),
 ('main bsn','8875BSN',10),('regular nursing','8875BSN',10),
 ('regular nursing degree','8875BSN',10),('full time nursing program','8875BSN',10),
 ('the nursing program','8875BSN',20)
ON CONFLICT(normalized_alias) DO UPDATE SET program_id=EXCLUDED.program_id,active=TRUE;

INSERT INTO program_advisor_aliases(normalized_alias,alias_scope,family_key,priority) VALUES
 ('specialty nursing','family','specialty_nursing',10),
 ('nursing specialties','family','specialty_nursing',10),
 ('nursing programs','family','nursing',20)
ON CONFLICT(normalized_alias) DO UPDATE SET alias_scope=EXCLUDED.alias_scope,family_key=EXCLUDED.family_key,active=TRUE;

INSERT INTO program_relationships(program_id,relationship_type,relationship_key,independent_program)
SELECT program_id,'member_of','specialty_nursing',TRUE FROM programs
WHERE program_id LIKE '810%BSN'
ON CONFLICT(program_id,relationship_type,relationship_key) DO UPDATE SET independent_program=TRUE,active=TRUE;
INSERT INTO program_relationships(program_id,relationship_type,relationship_key,independent_program)
SELECT program_id,'member_of','nursing',TRUE FROM programs
WHERE program_id='8875BSN' OR program_id LIKE '810%BSN'
ON CONFLICT(program_id,relationship_type,relationship_key) DO UPDATE SET independent_program=TRUE,active=TRUE;

COMMIT;
