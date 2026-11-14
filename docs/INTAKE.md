# Authenticated intake

These are working APIs, not a complete payment application. Full run/planning and
reconciliation orchestration and operator screens remain unfinished; `/ready`
remains 503. Uploads and operator assertions do not prove that
an invoice, bank instruction, compliance check or telephone call is genuine.

Every route below requires the `wt_session` cookie issued by `/api/login`.
POST requests additionally require the returned `csrf_token` in `x-csrf-token`;
an Origin header, when present, must match `WEBAUTHN_ORIGIN`. Operator accounts
are provisioned locally. No default operator, company, supplier or history is seeded.

1. Complete local roster and `init-installation` setup described in the README.
2. `POST /api/evidence` uploads the actual source bytes. Use a simple ASCII
   filename in `x-filename` and one of `text/plain`, `application/json`,
   `message/rfc822`, `application/pdf` as Content-Type. Maximum size is 4 MiB.
   The response contains the SHA-256 content address. Files are encrypted using
   the installation key, retained immutably, and downloaded only as attachments
   through authenticated `GET /api/evidence/{sha256}`.
3. `POST /api/suppliers` accepts `legal_name`, `display_name`, `category` and optional
   `tax_id`. The category must exist in the installation policy's reason mapping.
   Duplicate normalized legal names or exact tax identifiers are refused. List
   persisted suppliers with `GET /api/suppliers`.
4. `POST /api/suppliers/{vendor_id}/contacts` accepts `phone` in +E164 format,
   `provenance` (`contract`, `prior_invoice`, `website`, `registry`) and
   `evidence_sha256`. The server supplies creation/import times. There is no web
   field for backdating. Existing master history can be imported locally with
   `uv run python -m app.cli import-contact --help`; supply the actual source date,
   never a date invented to satisfy the age rule. A new contact cannot immediately
   qualify for independent callback confirmation.
5. `POST /api/suppliers/{vendor_id}/bank-changes` accepts `details` and
   `evidence_sha256`. BankDetails accepts company destinations in US/USD, GB/GBP,
   DE/NL/FR EUR only, with LOCAL or SWIFT transfer method. US accounts require
   explicit Checking/Savings, full account number and ABA. GB requires account,
   sort code and bank name. EUR requires an IBAN matching the country. SWIFT
   requires a valid BIC. Unsupported corridors fail at intake. The source bank
   instruction must be readable UTF-8 text, JSON, or unencoded plain email;
   multipart/HTML/encoded email and PDF bank instructions are refused until safely
   converted. Source phone hashes are retained so a phone supplied in the request
   cannot independently confirm that request. No unverified destination becomes
   ACTIVE. Concurrent requests for one supplier cannot both commit.
6. `POST /api/invoices` accepts `vendor_id`, `invoice_number`, `amount` (positive
   decimal string with exactly two fractional digits), `currency` (USD/GBP/EUR),
   `due_date` (YYYY-MM-DD) and `evidence_sha256`. The server supplies the requester
   and receipt time and atomically acquires the normalized duplicate lock. A
   READY invoice is eligible for planning checks, not approved or authorized for
   payment. Exact duplicates are blocked. Planning must still recompute duplicate,
   split, timing and live USD risk checks. Read invoices at `GET /api/invoices`.
7. An ops operator performs a genuine independent manual compliance review and
   uploads the supporting evidence. `POST /api/banks/{payee_id}/reviews/options`
   takes `result` (CLEAR/HIT/ERROR), `source`, `evidence_sha256` and timezone-aware
   `checked_at` within the last 24 hours. It returns exact terms and a WebAuthn
   challenge. `POST .../reviews/finish` takes `ceremony_id` and the actual passkey
   `credential` assertion. Replays and changed bank terms are refused. HIT/ERROR
   puts the bank version on COMPLIANCE_HOLD and voids open payment approvals;
   a later CLEAR does not automatically release that hold. CLEAR is never a claim
   of automated sanctions-provider clearance. Read records at `GET .../reviews`.

The existing callback, policy and approval endpoints require real WebAuthn proofs.
Callback confirmation enforces independent, established master contact provenance,
requester separation, readback and the signed policy's minimum 72-hour cooling
period. A local historical-contact import cannot create signed callback evidence.

`POST /api/provider/refresh` only queues a durable REFRESH request. Duplicate pending
refreshes coalesce. `GET /api/provider/jobs/{id}` reports its actual persisted state;
`GET /api/provider/snapshots` returns only stored observations with timestamps. At
this stage `uv run python -m app.workers.service` consumes REFRESH jobs with genuine
sandbox balance reads. Use `--once` for one attempt. Without a running configured
worker, jobs remain PENDING; failed reads mark jobs FAILED and retain the original
observation timestamp. Successful refreshes do not authorize payments or make the
application ready. Neither endpoint fabricates provider results.

`POST /api/approvals/{packet_id}/quote` requests an actual locked FX quote for an
already approved payment's shortfall. Currently only USD funding for GBP/EUR is
supported. The amount includes the signed policy's fee reservation and native
reserve floor. It returns a job ID; the worker's result contains a new CONVERSION
packet requiring two actual approvers. No conversion is authorized by quote creation.

`POST /api/approvals/{packet_id}/execute` queues a durable execution request after
checking actual passkey approvals, session/CSRF and requester separation. The worker
checks them again with current bank, cooling, policy, balance, reserve and cap data.
Conversion execution locks quote identity, currencies, date, amounts, rate and
expiry; expired/changed quotes require a new quote and new human approval. Current
market drift beyond the signed tolerance blocks execution. An ambiguous money
request remains lookup-only, including after a worker process dies. An execution
job reporting PENDING/AMBIGUOUS is not a successful or settled payout. A DONE job
means the request was processed; inspect its `execution_state` and tracked provider
status rather than interpreting DONE as funds arrival.

The web process needs `APP_DB_PATH`, `APP_POLICY_PATH`, `APP_KEY_DIR` and the WebAuthn
origin settings to match local setup. Defaults are documented in `.env.example`;
currently the web service reads these values from its process environment. Keep
Airwallex API credentials out of that process. Back up the database and encryption
key securely together; the API intentionally provides no destructive evidence purge.
