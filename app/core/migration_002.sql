-- Operator authentication and single-use passkey ceremonies. No default users.
CREATE TABLE operator_auth (
    user_id TEXT PRIMARY KEY REFERENCES user(id),
    password_hash TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1))
);
CREATE TABLE operator_session (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user(id),
    csrf_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX idx_session_expiry ON operator_session(expires_at);
CREATE TABLE login_attempt (
    bucket TEXT PRIMARY KEY,
    failures INTEGER NOT NULL,
    reset_at TEXT NOT NULL
);
CREATE TABLE signing_challenge (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user(id),
    session_hash TEXT NOT NULL REFERENCES operator_session(token_hash),
    purpose TEXT NOT NULL CHECK(purpose IN ('REGISTER','APPROVE','CALLBACK','POLICY','CLEAR')),
    subject_id TEXT,
    subject_hash TEXT,
    nonce TEXT NOT NULL UNIQUE,
    challenge BLOB NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);
CREATE INDEX idx_challenge_user ON signing_challenge(user_id, expires_at);
CREATE UNIQUE INDEX idx_signature_once ON approval_signature(packet_id, approver_id);
CREATE TRIGGER approval_signature_no_update BEFORE UPDATE ON approval_signature
BEGIN SELECT RAISE(ABORT, 'approval_signature is append-only'); END;
CREATE TRIGGER approval_signature_no_delete BEFORE DELETE ON approval_signature
BEGIN SELECT RAISE(ABORT, 'approval_signature is append-only'); END;
CREATE INDEX idx_audit_kind_at ON audit_log(kind, at);
UPDATE schema_meta SET value='2' WHERE key='user_version';
