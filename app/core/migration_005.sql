-- Existing conflicting requests make migration fail atomically. Never select
-- an arbitrary winner or silently discard supplier bank-change evidence.
CREATE UNIQUE INDEX IF NOT EXISTS idx_change_request_one_active_per_vendor
ON payee_change_request(vendor_id)
WHERE status IN ('RECEIVED','PENDING_CALLBACK','COOLING_OFF');
CREATE TABLE evidence_file (
    sha256 TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    encrypted_content BLOB NOT NULL,
    size_bytes INTEGER NOT NULL CHECK(size_bytes>0 AND size_bytes<=4194304),
    uploaded_by TEXT NOT NULL REFERENCES user(id),
    uploaded_at TEXT NOT NULL
);
CREATE TRIGGER evidence_file_no_update BEFORE UPDATE ON evidence_file
BEGIN SELECT RAISE(ABORT, 'evidence files are immutable'); END;
CREATE TRIGGER evidence_file_no_delete BEFORE DELETE ON evidence_file
BEGIN SELECT RAISE(ABORT, 'evidence files are retained for audit'); END;
ALTER TABLE vendor_contact ADD COLUMN provenance_sha256 TEXT REFERENCES evidence_file(sha256);
ALTER TABLE vendor_contact ADD COLUMN imported_at TEXT;
ALTER TABLE signing_challenge ADD COLUMN record_json TEXT;
ALTER TABLE compliance_review ADD COLUMN payee_fingerprint TEXT;
ALTER TABLE compliance_review ADD COLUMN details_sha256 TEXT;
UPDATE schema_meta SET value='5' WHERE key='user_version';
