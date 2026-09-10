BEGIN;

CREATE TABLE IF NOT EXISTS program_import_revisions (
    revision_id BIGSERIAL PRIMARY KEY,
    program_id VARCHAR(32) NOT NULL REFERENCES programs(program_id),
    contract_version VARCHAR(16) NOT NULL,
    payload_sha256 CHAR(64) NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    normalized_payload JSONB NOT NULL,
    source_url TEXT NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    extracted_at TIMESTAMPTZ,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pipeline_version VARCHAR(128) NOT NULL,
    review_status VARCHAR(32) NOT NULL CHECK (review_status IN ('auto-clean','needs-human-review','approved')),
    confidence_status VARCHAR(32) NOT NULL,
    human_approved BOOLEAN NOT NULL DEFAULT FALSE,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    importer VARCHAR(128) NOT NULL,
    import_status VARCHAR(32) NOT NULL DEFAULT 'applied',
    CHECK (NOT human_approved OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_program_import_revisions_program
    ON program_import_revisions(program_id, imported_at DESC);

COMMIT;
