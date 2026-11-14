CREATE TABLE provider_job_next (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('REFRESH','QUOTE','PLAN','EXECUTE')),
    requested_by TEXT NOT NULL REFERENCES user(id),
    request_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('PENDING','DONE','FAILED')),
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT INTO provider_job_next SELECT * FROM provider_job;
DROP TABLE provider_job;
ALTER TABLE provider_job_next RENAME TO provider_job;
CREATE UNIQUE INDEX provider_job_pending_execution ON provider_job(kind,request_json)
WHERE kind IN ('EXECUTE','QUOTE') AND state='PENDING';
UPDATE schema_meta SET value='7' WHERE key='user_version';
