-- Wiretight schema. FINAL.md §8.1.
--
-- SQLite, `PRAGMA user_version` migrations, foreign_keys=ON, WAL.
--
-- Design rules that the tests enforce, not just this comment:
--   * `audit_log` is append-only. UPDATE and DELETE raise ABORT, so a bug cannot
--     quietly rewrite history (T-13).
--   * Money is stored as TEXT, never a REAL. SQLite would happily store a float
--     and lose the exactness the packet hash depends on (§7.3).
--   * Timestamps are ISO-8601 UTC TEXT, sortable as strings.
--   * There is exactly one entity (single-tenant by design, §4.0). `entity` has a
--     single row and its id is the constant `entity_id`.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- entity, users, roster
-- ---------------------------------------------------------------------------
CREATE TABLE entity (
    id                  TEXT PRIMARY KEY,
    legal_name          TEXT NOT NULL,
    base_currency       TEXT NOT NULL,
    created_at          TEXT NOT NULL
);

CREATE TABLE user (
    id                      TEXT PRIMARY KEY,
    name                    TEXT NOT NULL,
    role                    TEXT NOT NULL CHECK (role IN ('approver', 'ops')),
    email                   TEXT NOT NULL UNIQUE,
    -- WebAuthn registration material. NULL means "not registered yet".
    webauthn_credential_id  TEXT UNIQUE,
    public_key              BLOB,
    sign_count              INTEGER NOT NULL DEFAULT 0,
    -- HMAC fallback: sha256 of the per-approver key. The key itself lives in
    -- var/keys/approvers.json and is never in the DB or in git.
    hmac_key_sha256         TEXT,
    created_at              TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Vendors, contacts, payee versions, beneficiaries
-- ---------------------------------------------------------------------------
CREATE TABLE vendor (
    id                     TEXT PRIMARY KEY,
    legal_name_norm        TEXT NOT NULL,
    display_name           TEXT NOT NULL,
    tax_id                 TEXT,
    category               TEXT NOT NULL,
    known_sender_domains   TEXT NOT NULL DEFAULT '[]',   -- JSON array
    flags                  TEXT NOT NULL DEFAULT '[]',   -- JSON array
    -- Set when a change request is REJECTED or EXPIRED. Drives the T2 fraud
    -- trigger for 30 days (R4 J-4).
    fraud_flagged_at       TEXT,
    created_at             TEXT NOT NULL
);
CREATE INDEX idx_vendor_norm ON vendor (legal_name_norm);

CREATE TABLE vendor_contact (
    id            TEXT PRIMARY KEY,
    vendor_id     TEXT NOT NULL REFERENCES vendor (id),
    kind          TEXT NOT NULL CHECK (kind IN ('phone', 'email')),
    value         TEXT NOT NULL,
    value_norm    TEXT NOT NULL,           -- digits only / lowercased
    provenance    TEXT NOT NULL CHECK (provenance IN
                      ('contract', 'prior_invoice', 'website', 'registry', 'document')),
    source_ref    TEXT,
    created_at    TEXT NOT NULL,
    changed_at    TEXT,
    active        INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_contact_vendor ON vendor_contact (vendor_id);

CREATE TABLE payee_version (
    id                  TEXT PRIMARY KEY,
    vendor_id           TEXT NOT NULL REFERENCES vendor (id),
    fingerprint         TEXT NOT NULL,          -- sha256 over rfc8785(...), §4.3
    -- Airwallex's own beneficiary `fingerprint` when the response carries one
    -- (documented as optional, U16 unverified).
    awx_fingerprint     TEXT,
    details_ref         TEXT NOT NULL,          -- pointer into the identifier store
    masked              TEXT NOT NULL,          -- e.g. DE•• •••• 7740
    method              TEXT NOT NULL CHECK (method IN ('LOCAL', 'SWIFT')),
    rail                TEXT,                   -- SEPA | FPS | ACH | SWIFT
    country             TEXT NOT NULL,
    currency            TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN
                          ('PROPOSED', 'ACTIVE_CAPPED', 'ACTIVE', 'SUSPENDED',
                           'SUPERSEDED', 'REJECTED', 'RETIRED', 'COMPLIANCE_HOLD')),
    final_payment_count INTEGER NOT NULL DEFAULT 0,
    cooling_off_until   TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX idx_payee_vendor ON payee_version (vendor_id, status);

-- Airwallex beneficiary id <-> payee version. The executor uses this to check,
-- before every transfer, that the beneficiary it is about to pay maps to the
-- signed payee version (U16, §4.8 step 3).
CREATE TABLE beneficiary_map (
    payee_version_id  TEXT PRIMARY KEY REFERENCES payee_version (id),
    beneficiary_id    TEXT NOT NULL UNIQUE,
    nickname          TEXT NOT NULL UNIQUE,     -- "wt-<payee_version_id>"
    created_at        TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- The bank-change lock (§4.5)
-- ---------------------------------------------------------------------------
CREATE TABLE payee_change_request (
    id                     TEXT PRIMARY KEY,
    vendor_id              TEXT NOT NULL REFERENCES vendor (id),
    source_kind            TEXT NOT NULL CHECK (source_kind IN
                             ('email', 'upload', 'failure_recovery', 'manual')),
    source_message_id      TEXT,
    received_at            TEXT NOT NULL,
    intake_user_id         TEXT NOT NULL REFERENCES user (id),
    requester_set          TEXT NOT NULL,        -- JSON array of user ids
    old_payee_version_id   TEXT REFERENCES payee_version (id),
    proposed_details_ref   TEXT NOT NULL,
    proposed_masked        TEXT NOT NULL,
    proposed_fingerprint   TEXT NOT NULL,
    evidence               TEXT NOT NULL DEFAULT '[]',   -- JSON array of flags
    -- FORMAT_VALID | FORMAT_INVALID, from POST /beneficiaries/validate.
    -- Never surfaced as "verified": valid means the format parsed.
    validate_result        TEXT CHECK (validate_result IN ('FORMAT_VALID', 'FORMAT_INVALID')),
    vop_result             TEXT,               -- Verification of Payee, evidence only
    status                 TEXT NOT NULL CHECK (status IN
                             ('RECEIVED', 'PENDING_CALLBACK', 'COOLING_OFF', 'APPROVED',
                              'REJECTED', 'EXPIRED', 'WITHDRAWN')),
    status_reason          TEXT,
    decided_at             TEXT
);
CREATE INDEX idx_change_vendor_status ON payee_change_request (vendor_id, status);

CREATE TABLE callback_verification (
    id                  TEXT PRIMARY KEY,
    change_request_id   TEXT NOT NULL REFERENCES payee_change_request (id),
    contact_id          TEXT NOT NULL REFERENCES vendor_contact (id),
    recorded_by         TEXT NOT NULL REFERENCES user (id),
    vendor_person_name  TEXT,
    vendor_person_role  TEXT,
    called_at           TEXT NOT NULL,
    readback_last4_ok   INTEGER,
    readback_name_ok    INTEGER,
    outcome             TEXT NOT NULL CHECK (outcome IN ('CONFIRMED', 'DENIED', 'NO_ANSWER')),
    attachment_sha256   TEXT,
    -- sha256 over the canonical callback record. Goes into the PAYMENT packet.
    record_sha256       TEXT NOT NULL,
    -- The ops user's signature over that hash (R4 C-1). A row without a valid
    -- signature counts as NO callback at all (T-10b).
    recorder_signature  BLOB NOT NULL,
    recorder_nonce      TEXT NOT NULL UNIQUE,     -- single use
    signing_method      TEXT NOT NULL CHECK (signing_method IN ('WEBAUTHN', 'HMAC_FALLBACK')),
    signed_via          TEXT NOT NULL CHECK (signed_via IN ('ui_passkey', 'cli_hmac')),
    created_at          TEXT NOT NULL
);
CREATE INDEX idx_callback_change ON callback_verification (change_request_id);

-- ---------------------------------------------------------------------------
-- Ingest: bills, obligations, tranches, the duplicate lock
-- ---------------------------------------------------------------------------
CREATE TABLE bill (
    id                TEXT PRIMARY KEY,
    source_kind       TEXT NOT NULL CHECK (source_kind IN
                        ('json', 'eml', 'pdf', 'manual')),
    source_ref        TEXT,
    document_sha256   TEXT NOT NULL,
    raw_json          TEXT NOT NULL,
    ingested_by       TEXT NOT NULL REFERENCES user (id),
    ingested_at       TEXT NOT NULL
);

CREATE TABLE obligation (
    id                TEXT PRIMARY KEY,
    vendor_id         TEXT NOT NULL REFERENCES vendor (id),
    invoice_no_norm   TEXT NOT NULL,
    invoice_no_raw    TEXT,
    amount            TEXT NOT NULL,        -- TEXT, never REAL
    currency          TEXT NOT NULL,
    due_date          TEXT NOT NULL,
    state             TEXT NOT NULL,
    requester_set     TEXT NOT NULL DEFAULT '[]',   -- JSON array of user ids
    bill_id           TEXT REFERENCES bill (id),
    flags             TEXT NOT NULL DEFAULT '[]',
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
CREATE INDEX idx_obligation_state ON obligation (state);
CREATE INDEX idx_obligation_vendor ON obligation (vendor_id);

-- Tranche 1 = the first-payment cap, rounded down. Tranche 2 = the remainder,
-- HELD_TRANCHE until tranche 1 is FINAL (§4.5.4).
CREATE TABLE obligation_tranche (
    obligation_id  TEXT NOT NULL REFERENCES obligation (id),
    tranche_no     INTEGER NOT NULL CHECK (tranche_no >= 1),
    amount          TEXT NOT NULL,
    currency        TEXT NOT NULL,
    state           TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    PRIMARY KEY (obligation_id, tranche_no)
);

-- One row per obligation, UNIQUE on (vendor, normalised invoice no). Taken when
-- the obligation is created, so two runs can never both think they own it.
CREATE TABLE duplicate_lock (
    obligation_key   TEXT PRIMARY KEY,     -- "<vendor_id>:<invoice_no_norm>"
    obligation_id    TEXT NOT NULL REFERENCES obligation (id),
    holder_attempt   INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL
);

CREATE TABLE run (
    id               TEXT PRIMARY KEY,
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    -- Balances snapshotted at start. The tie-out is computed from this, because
    -- sandbox state accumulates across runs (§4.13).
    opening_balances TEXT NOT NULL DEFAULT '{}',
    shadow           INTEGER NOT NULL DEFAULT 0,
    state            TEXT NOT NULL
);
CREATE INDEX idx_run_started ON run (started_at);

-- ---------------------------------------------------------------------------
-- Plan. Stored as canonical JSON plus its sha256, so a re-plan can be diffed
-- and a plan cannot be edited after the fact without detection.
-- ---------------------------------------------------------------------------
CREATE TABLE plan (
    id                TEXT PRIMARY KEY,
    run_id            TEXT NOT NULL REFERENCES run (id),
    canonical_json    TEXT NOT NULL,
    sha256            TEXT NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE TABLE plan_item (
    id                TEXT PRIMARY KEY,
    plan_id           TEXT NOT NULL REFERENCES plan (id),
    obligation_id     TEXT REFERENCES obligation (id),
    tranche_no        INTEGER,
    kind              TEXT NOT NULL CHECK (kind IN ('PAYMENT', 'CONVERSION')),
    tier              TEXT CHECK (tier IN ('T0', 'T1', 'T2', 'HARD_BLOCK')),
    decision          TEXT NOT NULL,
    reasons           TEXT NOT NULL DEFAULT '[]',
    diff_vs_previous  TEXT,
    sort_order        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_planitem_plan ON plan_item (plan_id, sort_order);

-- ---------------------------------------------------------------------------
-- Approval packets and signatures (§4.7)
-- ---------------------------------------------------------------------------
CREATE TABLE approval_packet (
    id                   TEXT PRIMARY KEY,
    kind                 TEXT NOT NULL CHECK (kind IN ('CONVERSION', 'PAYMENT')),
    canonical_json       TEXT NOT NULL,
    sha256               TEXT NOT NULL UNIQUE,
    tier                 TEXT NOT NULL CHECK (tier IN ('T0', 'T1', 'T2')),
    required_approvers   INTEGER NOT NULL,
    created_at           TEXT NOT NULL,
    expires_at           TEXT NOT NULL,
    state                TEXT NOT NULL CHECK (state IN
                           ('OPEN', 'APPROVED', 'CONSUMED', 'EXPIRED', 'VOID'))
);

CREATE TABLE approval_signature (
    id               TEXT PRIMARY KEY,
    packet_id        TEXT NOT NULL REFERENCES approval_packet (id),
    approver_id      TEXT NOT NULL REFERENCES user (id),
    method           TEXT NOT NULL CHECK (method IN ('WEBAUTHN', 'HMAC_FALLBACK')),
    signed_via       TEXT NOT NULL CHECK (signed_via IN ('ui_passkey', 'cli_hmac')),
    assertion        BLOB,                  -- WebAuthn assertion blob
    signature        BLOB,                  -- HMAC fallback bytes
    challenge_nonce  TEXT NOT NULL UNIQUE,  -- single use, replay-proof
    signed_at        TEXT NOT NULL
);
CREATE INDEX idx_signature_packet ON approval_signature (packet_id);

-- An approval is consumed in the same transaction that records the executor's
-- INTENT. A consumed approval can never be reused (T-06).
CREATE TABLE approval_consumption (
    packet_id        TEXT PRIMARY KEY REFERENCES approval_packet (id),
    consumed_at      TEXT NOT NULL,
    intent_audit_seq INTEGER NOT NULL
);

-- ---------------------------------------------------------------------------
-- Conversions and transfer attempts
-- ---------------------------------------------------------------------------
CREATE TABLE conversion (
    id              TEXT PRIMARY KEY,
    request_id      TEXT NOT NULL UNIQUE,
    conversion_id   TEXT,
    quote_id        TEXT,
    buy_currency    TEXT,
    sell_currency   TEXT,
    buy_amount      TEXT,
    status          TEXT NOT NULL,
    raw_json        TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE transfer_attempt (
    id                      TEXT PRIMARY KEY,
    obligation_id           TEXT NOT NULL REFERENCES obligation (id),
    tranche_no              INTEGER NOT NULL DEFAULT 1,
    attempt_no              INTEGER NOT NULL,
    -- uuid5 per §7.3: key = transfer:{obligation_id}:t{tranche}:a{attempt}.
    -- NO run_id, so a re-plan in a later run reuses the same key.
    request_id              TEXT NOT NULL UNIQUE,
    transfer_id             TEXT,
    replaces_transfer_id    TEXT,
    -- Two status columns on purpose (§4.10).
    awx_status              TEXT,   -- mirrors Airwallex, documented transitions only
    wt_state                TEXT,   -- our overlay: SUBMITTING | AMBIGUOUS | PAID_PROVISIONAL
                                    -- | FINAL | PRESUMED_SETTLED | REOPENED | RFI_OPEN
                                    -- | CANCELLED_FAILED | REJECTED
    failure_type            TEXT,   -- captured on FIRST SIGHT and never nulled
    failure_reason          TEXT,
    first_paid_at           TEXT,
    final_at                TEXT,
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL,
    UNIQUE (obligation_id, tranche_no, attempt_no)
);
CREATE INDEX idx_attempt_obligation ON transfer_attempt (obligation_id, tranche_no);

-- Every polled raw object, appended. Lets a disagreement between what we were
-- told and what we later read be settled from evidence.
CREATE TABLE transfer_observation (
    id             TEXT PRIMARY KEY,
    transfer_id    TEXT NOT NULL,
    observed_at    TEXT NOT NULL,
    awx_status     TEXT,
    raw_json       TEXT NOT NULL
);
CREATE INDEX idx_observation_transfer ON transfer_observation (transfer_id, observed_at);

-- ---------------------------------------------------------------------------
-- Incidents, RFIs, screening
-- ---------------------------------------------------------------------------
CREATE TABLE incident (
    id              TEXT PRIMARY KEY,
    obligation_id   TEXT REFERENCES obligation (id),
    payee_version_id TEXT REFERENCES payee_version (id),
    kind            TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'critical')),
    detail          TEXT NOT NULL DEFAULT '{}',
    opened_at       TEXT NOT NULL,
    closed_at       TEXT
);

CREATE TABLE rfi (
    id              TEXT PRIMARY KEY,
    external_id     TEXT NOT NULL UNIQUE,
    transfer_id     TEXT,
    payee_version_id TEXT REFERENCES payee_version (id),
    status          TEXT NOT NULL CHECK (status IN ('ACTION_REQUIRED', 'ANSWERED', 'CLOSED')),
    detail          TEXT NOT NULL DEFAULT '{}',
    opened_at       TEXT NOT NULL,
    closed_at       TEXT
);

CREATE TABLE screening_result (
    id            TEXT PRIMARY KEY,
    subject       TEXT NOT NULL,
    result        TEXT NOT NULL CHECK (result IN ('CLEAR', 'HIT', 'ERROR')),
    detail        TEXT NOT NULL DEFAULT '{}',
    checked_at    TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Reconciliation, journal
-- ---------------------------------------------------------------------------
CREATE TABLE tie_out (
    id                TEXT PRIMARY KEY,
    run_id            TEXT NOT NULL REFERENCES run (id),
    currency          TEXT NOT NULL,
    b_open            TEXT NOT NULL,
    b_close_computed  TEXT NOT NULL,
    b_actual          TEXT NOT NULL,
    residual          TEXT NOT NULL,
    -- RESIDUAL_0.00 | RESIDUAL_EXPLAINED | RESIDUAL_UNEXPLAINED
    state             TEXT NOT NULL CHECK (state IN
                        ('RESIDUAL_0.00', 'RESIDUAL_EXPLAINED', 'RESIDUAL_UNEXPLAINED')),
    explanation       TEXT,
    terms             TEXT NOT NULL DEFAULT '{}',
    created_at        TEXT NOT NULL
);

CREATE TABLE recon_exception (
    id           TEXT PRIMARY KEY,
    tie_out_id   TEXT NOT NULL REFERENCES tie_out (id),
    kind         TEXT NOT NULL,     -- UNMAPPED_ROW | MISSING_ROW | AMOUNT_MISMATCH
    source_id    TEXT,
    reason       TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE journal_line (
    id             TEXT PRIMARY KEY,
    run_id         TEXT NOT NULL REFERENCES run (id),
    line_no        INTEGER NOT NULL,
    occurred_at    TEXT NOT NULL,
    account        TEXT NOT NULL,
    debit          TEXT,
    credit         TEXT,
    currency       TEXT NOT NULL,
    amount_usd     TEXT,
    source_id      TEXT,
    memo           TEXT
);
CREATE INDEX idx_journal_run ON journal_line (run_id, line_no);

-- ---------------------------------------------------------------------------
-- Audit chain and kill switch
-- ---------------------------------------------------------------------------
-- entry_hash = sha256(prev_hash || rfc8785(payload) || seq || at_iso)  (§14 b)
CREATE TABLE audit_log (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    prev_hash   TEXT NOT NULL,
    entry_hash  TEXT NOT NULL,
    kind        TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    at          TEXT NOT NULL
);

-- Append-only. A bug must not be able to quietly rewrite history (T-13).
CREATE TRIGGER audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;

CREATE TRIGGER audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;

CREATE TABLE killswitch_state (
    id          INTEGER PRIMARY KEY CHECK (id = 1),   -- exactly one row
    halted      INTEGER NOT NULL DEFAULT 0,
    halted_at   TEXT,
    reason      TEXT,
    trip_id     TEXT
);

CREATE TABLE trip (
    id          TEXT PRIMARY KEY,
    reason      TEXT NOT NULL,
    origin      TEXT NOT NULL,     -- 'human' | the automatic row that fired
    tripped_at  TEXT NOT NULL,
    cleared_at  TEXT,
    cleared_by  TEXT
);

-- Clearing the kill switch needs 2 distinct approver signatures over
-- sha256("clear|" + trip_id + "|" + reason)  (§4.9, floor row 30).
CREATE TABLE trip_clear_signature (
    id             TEXT PRIMARY KEY,
    trip_id        TEXT NOT NULL REFERENCES trip (id),
    approver_id    TEXT NOT NULL REFERENCES user (id),
    method         TEXT NOT NULL CHECK (method IN ('WEBAUTHN', 'HMAC_FALLBACK')),
    signed_via     TEXT NOT NULL CHECK (signed_via IN ('ui_passkey', 'cli_hmac')),
    signature      BLOB NOT NULL,
    challenge_nonce TEXT NOT NULL UNIQUE,
    signed_at      TEXT NOT NULL
);

CREATE TABLE policy_load (
    id           TEXT PRIMARY KEY,
    path         TEXT NOT NULL,
    sha256       TEXT NOT NULL,
    signatures   TEXT NOT NULL DEFAULT '[]',
    loaded_at    TEXT NOT NULL,
    result       TEXT NOT NULL CHECK (result IN ('OK', 'REJECTED'))
);

CREATE TABLE webhook_event (
    event_id       TEXT PRIMARY KEY,
    raw_sha256     TEXT NOT NULL,
    received_at    TEXT NOT NULL,
    processed_at   TEXT,
    -- Webhooks never set state; they only enqueue a poll (§4.10).
    enqueued_poll  INTEGER NOT NULL DEFAULT 0
);

-- Rolling counters for floor rows 13-17 and 26-28. Recomputed from the ledger
-- PLUS GET /transfers, never from this table alone (R4 J-3): wiping the local
-- DB must not reset a cap.
CREATE TABLE counters (
    key          TEXT PRIMARY KEY,
    value        TEXT NOT NULL,
    recomputed_at TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Meta
-- ---------------------------------------------------------------------------
CREATE TABLE schema_meta (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);

INSERT INTO schema_meta (key, value) VALUES ('user_version', '1');