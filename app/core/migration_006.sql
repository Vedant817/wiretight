CREATE TABLE run_baseline (
    run_id TEXT PRIMARY KEY REFERENCES run(id),
    settled_ids TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
CREATE TRIGGER run_baseline_immutable BEFORE UPDATE ON run_baseline
BEGIN SELECT RAISE(ABORT, 'run baseline is immutable'); END;
CREATE TABLE financial_posting (
    financial_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES run(id),
    canonical_json TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    posted_at TEXT NOT NULL
);
CREATE TRIGGER financial_posting_immutable BEFORE UPDATE ON financial_posting
BEGIN SELECT RAISE(ABORT, 'financial postings are immutable'); END;
CREATE TRIGGER financial_posting_retained BEFORE DELETE ON financial_posting
BEGIN SELECT RAISE(ABORT, 'financial postings are retained'); END;
UPDATE schema_meta SET value='6' WHERE key='user_version';
