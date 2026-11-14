-- Durable human decisions and execution intents; no automatic business records.
CREATE TABLE signed_record (
    id TEXT PRIMARY KEY,
    purpose TEXT NOT NULL CHECK(purpose IN ('POLICY','CALLBACK','CLEAR')),
    subject_id TEXT NOT NULL,
    canonical_json TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES user(id),
    assertion BLOB NOT NULL,
    nonce TEXT NOT NULL UNIQUE,
    signed_at TEXT NOT NULL,
    UNIQUE(purpose, subject_id, user_id)
);
CREATE INDEX idx_record_subject ON signed_record(purpose, subject_id);
CREATE TRIGGER signed_record_no_update BEFORE UPDATE ON signed_record
BEGIN SELECT RAISE(ABORT, 'signed_record is append-only'); END;
CREATE TRIGGER signed_record_no_delete BEFORE DELETE ON signed_record
BEGIN SELECT RAISE(ABORT, 'signed_record is append-only'); END;
CREATE TABLE execution_intent (
    id TEXT PRIMARY KEY,
    packet_id TEXT NOT NULL REFERENCES approval_packet(id),
    kind TEXT NOT NULL CHECK(kind IN ('TRANSFER','CONVERSION','BENEFICIARY')),
    request_id TEXT NOT NULL UNIQUE,
    canonical_payload TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('PREPARED','SUBMITTED','AMBIGUOUS','REJECTED')),
    provider_id TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_money_packet_once ON execution_intent(packet_id)
WHERE kind IN ('TRANSFER','CONVERSION');
CREATE TRIGGER execution_payload_immutable
BEFORE UPDATE OF packet_id,kind,request_id,canonical_payload,payload_sha256 ON execution_intent
BEGIN SELECT RAISE(ABORT, 'execution intent terms are immutable'); END;
CREATE TRIGGER execution_intent_no_delete BEFORE DELETE ON execution_intent
BEGIN SELECT RAISE(ABORT, 'execution intents cannot be deleted'); END;
CREATE TABLE protected_details (
    id TEXT PRIMARY KEY,
    encrypted_json BLOB NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TRIGGER protected_details_no_update BEFORE UPDATE ON protected_details
BEGIN SELECT RAISE(ABORT, 'bank details are versioned'); END;
CREATE TABLE worker_health (
    id INTEGER PRIMARY KEY CHECK(id=1),
    ready INTEGER NOT NULL,
    detail TEXT NOT NULL,
    checked_at TEXT NOT NULL
);
UPDATE schema_meta SET value='3' WHERE key='user_version';
