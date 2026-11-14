-- Link attempts to their actual approved terms, not invented payment history.
ALTER TABLE transfer_attempt ADD COLUMN payee_version_id TEXT REFERENCES payee_version(id);
ALTER TABLE transfer_attempt ADD COLUMN packet_id TEXT REFERENCES approval_packet(id);
ALTER TABLE transfer_attempt ADD COLUMN run_id TEXT REFERENCES run(id);
ALTER TABLE transfer_attempt ADD COLUMN amount_usd TEXT;
CREATE INDEX idx_attempt_payee ON transfer_attempt(payee_version_id,created_at);
CREATE TABLE compliance_review (
    id TEXT PRIMARY KEY,
    payee_version_id TEXT NOT NULL REFERENCES payee_version(id),
    recorded_by TEXT NOT NULL REFERENCES user(id),
    result TEXT NOT NULL CHECK(result IN ('CLEAR','HIT','ERROR')),
    source TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TRIGGER compliance_review_no_update BEFORE UPDATE ON compliance_review
BEGIN SELECT RAISE(ABORT, 'compliance reviews are append-only'); END;
CREATE TRIGGER compliance_review_no_delete BEFORE DELETE ON compliance_review
BEGIN SELECT RAISE(ABORT, 'compliance reviews are append-only'); END;
CREATE TABLE provider_job (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('REFRESH','QUOTE','PLAN')),
    requested_by TEXT NOT NULL REFERENCES user(id),
    request_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('PENDING','DONE','FAILED')),
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE provider_snapshot (
    kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    canonical_json TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    PRIMARY KEY(kind,subject)
);
UPDATE schema_meta SET value='4' WHERE key='user_version';
