# Production status — 2026-11-14

**Not production-ready. Do not use for real payments.** The overnight checklist is
unfinished. This document distinguishes implemented source from provider acceptance.

## Stretch 1

Read the 40-commit history, README, demo/V2-VERIFICATION.md, master build prompt,
spec index and relevant locked-spec controls/endpoints. Baseline `e9edb77` has core
libraries and a separate simulated recording app, with empty API/integration/worker
packages. No local `.env` or inherited AWX_CLIENT_ID/AWX_API_KEY were found; values
were never displayed. Python 3.12.15 and uv 0.12.22 are available.

Implemented:

- Source audit in PROD-AUDIT.md, committed as `e943c05`.
- A real sandbox HTTP client (no fixture fallback): token caching/expired-token
  refresh, timeout, safe error categories, 429/read-5xx backoff, exact request IDs,
  balances/history, global account reads, beneficiary schema/validation/create/read,
  FX quote/conversion/rate operations, transfer create/read/lookup, transaction lists.
  A mutation 5xx or timeout is AMBIGUOUS and requires lookup before any retry.
  Beneficiary creates are never blindly retried. Redirects/proxies are disabled.
- Product setup page, readiness and signed webhook ingestion. Raw-byte HMAC,
  five-minute timestamp tolerance, size cap, constant-time comparison, durable
  deduplication and audit append. Webhook order cannot change transfer state.
  No demo import, runtime company seed or simulated provider response is used.

Verification so far (actual runs):

```
uv run pytest tests/unit/test_airwallex.py -q
15 passed in 1.26s                         # initial client
uv run pytest tests/unit/test_product_webhooks.py -q
5 passed in 0.93s
uv run pytest tests/unit/test_airwallex.py tests/unit/test_product_webhooks.py tests/live/test_airwallex_read.py -q
20 passed, 1 skipped in 1.18s              # revised mutation-5xx handling
uv run pytest tests -q --timeout=180
791 passed, 37 skipped in 50.90s           # before final mutation-5xx revision
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
53 files already formatted
uv run mypy app
Success: no issues found in 30 source files
git diff --check
exit 0
```

One webhook test attempt failed because Windows constructs the event-loop's internal
socketpair using loopback TCP. The test fixture now allows loopback connections while
refusing outbound connections; no application code was mocked. The client fault
vectors are synthetic HTTP-boundary tests, **not recorded Airwallex contract fixtures**.

## Remaining engineering work

- Guarded payout execution, durable intent/approval consumption and lookup recovery
  are implemented and tested at the HTTP boundary (stretch 5). The service loop,
  conversion execution, complete incident/settlement guards and live acceptance are
  still incomplete. This is not a production acceptance claim.
- Operator session authentication, authorization, passkey enrollment and packet
  approval APIs are built (stretch 3). Callback and policy decision APIs are built
  (stretch 4). Native payment packet construction and explicit entity/policy setup
  exist (stretch 5). Supplier/invoice intake endpoints, provider-job dispatch and
  operational UI are not built.
- Ledger-to-provider reconciliation, settlement windows, incident handling and poller
  are not built. Existing core tests do not certify those missing integrations.
- Native installation policy has no demo marker and runtime policy refuses that
  marker. Shared legacy floor/test helpers still contain historical vocabulary.
  The product diagnostic surface continues to refuse readiness pending integration.
- Global account creation, beneficiary ambiguous-create recovery, conversion recovery,
  startup audit sealing, outbound rate buckets, structured operational logs and
  credential-separated worker readiness remain incomplete.
- Historical app/demo recording source remains isolated; fixtures have not yet been
  relocated into tests. No files inside demo/ were edited.
- Concurrent approval double clicks are tested. Crash/restart without duplicate payout, insufficient-balance
  execution guards, expired FX quotes, unsupported corridors, concurrent operators
  and reconciliation mismatches need integrated tests after those flows exist.
- 36 pre-existing compliance-index skips cover unbuilt milestones. They are not
  passing acceptance checks. One additional live test skips without explicit live
  confirmation (and also requires credentials). No live provider calls were made.

## Vedant's actions and unresolved decisions

Add AWX_CLIENT_ID and AWX_API_KEY to a gitignored local .env for the worker only,
using an existing sandbox account; do not send keys in chat. Configure a webhook
subscription secret as AWX_WEBHOOK_SECRET if webhooks will be used. No signup is
performed. Production-host enablement is outside the current sandbox-only safety
contract. Keep the real 72-hour cooling floor and require human approval for all
consequential actions; do not enable automatic T0 payments.

Adding credentials does **not** complete the missing engineering work or make this
application ready for users. Readiness deliberately remains HTTP 503. No push,
PR, publication, deployment, or external message has been made.

Sources checked: repository raw Airwallex docs, current
[authentication reference](https://www.airwallex.com/docs/api/authentication/api_access_token),
[transfer reference](https://www.airwallex.com/docs/api/payouts/transfers), and
[webhook signature guidance](https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events).

## Stretch 2 — safety corrections and process smoke

- Preserved live locks regardless of age and partially written locks regardless
  of content. Corrected Windows dead-PID detection and CloseHandle pointer typing.
  Remaining file-reclaim race requires OS-backed locking before worker acceptance.
- Cooling-off now accepts a configurable integer number of hours, with a hard
  minimum of 72; tightening to 96 is tested. Historical video paths were not edited.
- README includes a one-command diagnostic startup, variables and known gaps.
- Started uvicorn in an owned subprocess with a temporary SQLite database outside
  the repo. Real HTTP checks: `/` 200, `/health` 503 with ready=false,
  `POST /transfers` 404, unconfigured `POST /webhooks/airwallex` 503. Stopped that
  subprocess and removed its temporary directory. This is diagnostic-service
  evidence, not payment-flow end-to-end acceptance.

Final checks for this stretch:

```
uv run pytest tests/unit/test_singlewriter.py tests/unit/test_oob.py tests/unit/test_cooling_configuration.py -q
68 passed in 1.23s
CONFIRM_LIVE=1 uv run pytest tests/live/test_airwallex_read.py -q
1 skipped in 0.45s — AWX_CLIENT_ID and AWX_API_KEY are not configured
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
54 files already formatted
uv run mypy app
Success: no issues found in 30 source files
uv run pytest tests -q --timeout=180
798 passed, 37 skipped in 50.63s
git diff --check
exit 0 after removing an extra trailing blank line in DECISIONS.md
```

The assignment remains active. Next: replace the PID-file lock with kernel-backed
exclusion, then add authenticated operators and bound human approvals before a
durable executor can be exposed. Credential absence blocks live acceptance only;
it does not block continuing the remaining engineering work.

## Stretch 3 — authenticated operators and bound passkey approvals

Implemented:

- Kernel-backed single-writer exclusion (`app/core/process_lock.py`). Persistent
  inode, no PID/age reclamation. A second process is refused; `os._exit` releases
  the OS lock so a restarted process can acquire it. Tested on this Windows host;
  POSIX branch has not been run here. The worker still needs to use this primitive.
- Explicit version-1 to version-2 SQLite migration, with DDL and version changes
  in one transaction. Upgrade test preserves a pre-existing audit entry and proves
  migration idempotence. No users or companies are seeded.
- Locally provisioned operators, scrypt password hashing, revocable eight-hour
  sessions, DB-backed account/source failure limits, bounded password-verification
  concurrency, CSRF tokens, same-origin checks and secure-cookie support for HTTPS.
- User-verified passkey registration and exact-packet-hash sign-off. Two distinct
  T2 approvers; requester and ops identities cannot approve; fewer than three
  enabled approvers blocks T2. Single-use five-minute ceremonies bind session,
  operator, nonce and packet. Concurrent double clicks record one signature.
- Immutable signature rows and executor-side verification of the original stored
  assertion, signing counter and ceremony. Current requester/role/revocation checks
  run again. Registered public-key and credential fingerprints are bound to the
  audit log. The future executor must verify/seal that log before money actions.
- Protected operator/approval API endpoints; bounded request bodies including
  chunked requests; validation responses omit raw inputs (including passwords).
  Unexpected errors log only a structured event/type, with no body or key data.
- CLI `operator-add` prompts for a password; `operator-disable` revokes access.

Verification (actual commands/results):

```
uv run pytest tests/unit/test_process_lock.py -q
2 passed in 0.61s
uv run pytest tests/unit/test_operators_signing.py tests/unit/test_b_concurrency.py -q
44 passed in 35.64s
uv run pytest tests -q --timeout=180
814 passed, 37 skipped in 65.81s
uv run pytest tests/unit/test_operators_signing.py -q
15 passed in 32.55s
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
62 files already formatted
uv run mypy app
Success: no issues found in 34 source files
git diff --check
exit 0
uv run python -m app.cli --help
uv run python -m app.cli operator-add --help
uv run python -m app.cli operator-disable --help
all exit 0
```

The full-suite run preceded the last registration-fingerprint check and one new
stored-assertion-tampering test; the final 15-test focused run covers those changes.
The software authenticator is strictly under tests/support, generates real ES256
signatures/CBOR, and exercises the installed WebAuthn verifier. It does not prove
physical-device enrollment or browser user-verification acceptance.

During focused verification an existing shared-reader test returned one `None`
instead of a COUNT value (1 failure / 117 passes). Shared connections now disable
the CPython statement cache; the concurrent regression performs 1,000 reads across
eight threads and checks every result. This agrees with the documented CPython
[shared-cache inconsistency issue](https://github.com/python/cpython/issues/118172).
WAL alone never made Python's shared statement cache safe.

Remaining: construct real packets from supplier/invoice data, connect signed callback
and policy workflows, build the executor/recovery/reconciliation and UI, and run the
full hard-scenario/live matrix. Credentials are still absent; no provider calls,
media edits, pushes, PRs, publication or external messages were made.

## Stretch 4 — real policy, callback and halt decisions

Implemented runtime paths:

- Domain-separated WebAuthn signed records for policy, callbacks and halt clearing.
  Immutable records bind the acting identity/session, exact canonical terms, nonce,
  origin and audited registered credential. A public legacy HMAC signature is
  explicitly tested as rejected. There is no runtime HMAC fallback in these paths.
- Runtime policy loading validates the safety floor, actual installation entity and
  enabled operator roster, then requires two independent passkey signatures over
  the exact file hash. T0 automatic payments and shortened cooling are refused.
  YAML anchors/aliases are refused. Policy API reports cryptographic verification
  separately from the raw signature count.
- Callback recording uses the real supplier-master contact and change request,
  enforces independent ops identity, contact age/provenance, recent-contact changes,
  readback and timing. Signed fields are checked again on verification. Confirmation
  stores the real minimum 72-hour cooling deadline; denial rejects proposed details.
  A NO_ANSWER can be followed by a separately signed confirmation. These records are
  evidence of a human's callback account; they cannot prove the phone call occurred.
- Database halt clearing requires two fresh passkeys over the same active trip and
  exact reason. It never removes a local HALT marker, which remains an independent
  stop requiring explicit local removal. Missing/corrupt active-trip evidence refuses
  clear. Protected authenticated routes expose these decisions.
- Version-3 migration adds signed records, immutable execution-intent terms,
  protected-detail storage and worker-health tables. Version-2 upgrade preservation
  is tested. Execution-intent tables are foundations, **not a working executor**.

Verification (actual commands and results):

```
uv run pytest tests/unit/test_real_decisions.py::test_real_policy_callback_and_halt_http_flows -q
1 passed in 7.66s
uv run pytest tests/unit/test_real_decisions.py -q
10 passed in 26.47s
uv run pytest tests -q --timeout=180
825 passed, 37 skipped in 105.51s
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
67 files already formatted
uv run mypy app
Success: no issues found in 38 source files
git diff --check
exit 0
```

The full run includes the final callback-row consistency, policy-alias and halt-trip
checks. The HTTP test drives the real FastAPI routes and real crypto verifier using
the test-only software authenticator. It is not browser/device acceptance or a live
provider call. One interim test run failed from misplaced test lines (`body` was
undefined); corrected the test layout and reran it and the full suite.

Follow-up audit found public test-derived policy/clear HMAC helpers in legacy core
modules, plus the legacy raw-Ed25519 callback helper. The new runtime routes bypass
those helpers. Their relocation/removal, along with historical app/demo fixtures,
remains required cleanup; do not mistake old core-library tests for production
authentication evidence. First registration fingerprints are authoritative; appended
registration entries cannot silently replace the trusted credential.

Still absent: first-run business/entity and reserve-policy setup, supplier/invoice
ingestion, canonical payment/conversion packet construction, executor live guards,
durable dispatch/recovery, polling, reconciliation and the operational UI. Startup
must ultimately anchor operator registrations to verified audit checkpoints before
any mutation. The worker must use the new kernel lock. No money route is enabled.
The real business name and reserve floor must come from operator input, not invented
defaults. Credentials remain absent (presence-only check: no .env or inherited keys).
No files in demo/ were changed; no push, PR, publication, deployment or messages.

## Stretch 5 — real setup and durable payout execution

Implemented:

- `init-installation` requires the real business legal name, an explicitly chosen
  USD reserve and a provisioned roster. It generates fresh cryptographic keys and
  a persistent UUID namespace, writes a real policy, and never overwrites an existing
  policy. `trust-operators` locally pins enrolled credentials outside SQLite and
  writes an audit checkpoint. Worker audit seals cannot silently enroll new keys.
- Typed corridor inputs and immutable encrypted bank-detail versions. Full provider
  account/routing/name/currency identifiers must match before paying; last-four-only
  data cannot authorize a destination. Supported current inputs are company bank
  accounts in US/USD, GB/GBP and DE/NL/FR EUR, LOCAL or SWIFT with required BIC.
  Sandbox acceptance of each payload is still unverified.
- Payment packets come from actual persisted invoice, duplicate lock, bank version,
  signed callback, signed manual compliance-review evidence, policy and run. A manual
  review is labelled `OPERATOR_REVIEW_CLEAR`, not automatic sanctions clearance.
  Names, masked destination, bank-version hash, payer fee choice and absolute validity
  timestamps are signed. Mutable database expiry fields cannot extend signed expiry.
  The callback also binds the request arrival timestamp and the executor recomputes
  the real cooling floor. Native tranches are fixed once and live USD caps rechecked.
- `app/workers/executor.py` is now a real payout dispatcher using the actual HTTP
  client. It verifies policy/roster/audit trust and stored human signatures, rebuilds
  terms, reads current balances, rates, transfer history, beneficiaries and RFIs,
  checks reserve/cap/timing/duplicate conditions, consumes approval with an audit
  INTENT and immutable outbox record, seals that intent, then calls the provider.
  No SQLite write transaction spans an HTTP call.
- New beneficiary creation is under the signed payment approval; nickname lookup
  resolves uncertain creates. Money-moving request IDs remain stable. Restarting a
  PREPARED/AMBIGUOUS payout only looks up its existing key. If no payout is found,
  it remains AMBIGUOUS and never silently gets a second POST. Recovering only a
  beneficiary returns BENEFICIARY_READY, never a false payout-submitted result.
- Current global/provider transfer history counts toward caps; the local ledger
  cannot be cleared to reset those counts. Version-4 migration links attempts to
  approved payee/run/packet terms and adds review/job/snapshot tables.
- Corrected provider protocol mistakes against current official docs: beneficiary
  validation returns `OK`, and the rates response's top-level `rate` must not be
  assumed to be an exchange rate. CLIENT buy/sell amounts determine the exact USD
  basis, conservatively compared to the last booked USD pair. JSON fractional numbers
  decode directly to Decimal, never binary float. Holiday rules and timezone data
  are now pinned runtime dependencies. Runtime settings default to live sandbox mode;
  demo-timing and fixture-directory fields were removed from shared settings.

Verification (actual runs):

```
uv run pytest tests/unit/test_real_executor.py -q
13 passed in 102.28s
uv run pytest tests -q --timeout=180
845 passed, 37 skipped in 219.91s
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
75 files already formatted
uv run mypy app
Success: no issues found in 44 source files
git diff --check
exit 0
uv run python -m app.cli init-installation --help
uv run python -m app.cli trust-operators --help
both exit 0
uv lock
Resolved 73 packages
```

The full run includes the final absolute-expiry/request-arrival bindings, rate-basis
changes and packet display/fee fields. HTTP fault cases cover one-time payout, lost
response after acceptance, uncertain missing payout held without repost, provider
5xx after commit, process-control loss followed by recovery, insufficient funds,
bank change after signing, concurrent executor calls, bad stored assertion, changed
trusted roster and external-provider history breaching caps. The process-control-loss
test raises SystemExit at the HTTP transport boundary; it is not a real killed worker
connected to a live provider. Earlier kernel-lock tests separately use real subprocess
exit. All provider responses in these tests are synthetic and confined to tests/;
they are **not** recorded sandbox contracts or live payout evidence.

One new input test found all-zero routing data passed the checksum parser; the typed
destination boundary now rejects it. Offline dependency resolution initially lacked
cached registry metadata; the normal `uv lock` then succeeded without changing pins.

Still incomplete: continuous service/job loop and heartbeat-backed readiness,
authenticated supplier/invoice/review intake and planning endpoints, conversion
packets/execution, complete poll/return/settlement/incident handling, reconciliation,
outbound rate buckets, operational UI and one-command full-app launch. Mature-payee
planning must incorporate live aggregate history; complete replacement/refund guards
and policy-tightening cases need the remaining matrix. Legacy test signers/demo
source cleanup is still pending. No production readiness claim or live provider
acceptance is made. The ordinary web service remains unready.

Vedant must eventually provide the real business inputs, register real devices and
pin the roster, sign the actual policy, and add sandbox credentials. Those actions
do not replace the remaining engineering. No keys were printed or committed. No
demo/ media, push, PR, publication, deployment or external messages were touched.

Protocol references checked this stretch:
[beneficiary validation](https://www.airwallex.com/docs/api/payouts/beneficiaries/validate),
[rates](https://www.airwallex.com/docs/api/transactional_fx/rates),
[beneficiary list filters](https://www.airwallex.com/docs/api/payouts/beneficiaries).

## Stretch 6 — actual intake, review bindings and migration verification

Implemented authenticated supplier, contact, bank-change and invoice intake;
encrypted immutable source-file upload/download; evidence-backed manual compliance
review with actual passkey assertions; and a password-prompted local historical
contact import. Requester identity and receipt times come from the session/server,
not client-selected IDs or dates. New web contacts cannot be backdated. See INTAKE.md
for supported inputs and explicit limits. US account category is now required.
Review signatures bind the bank fingerprint and full encrypted-detail hash. A
HIT/ERROR holds the bank version and voids open approvals. Halt clearing now binds
an absolute four-hour round and can collect fresh signatures after an old round
expires. Provider refresh requests are durably queued and report PENDING; no job
completion or provider data is fabricated while the worker remains unfinished.

A concurrent bank-change test initially failed: both requests committed. Investigation
found the old unit fixture created a unique index which database migration never
installed. Migration 5 now installs it. The losing transaction rolls back its vault
and bank-version writes. A legacy database with conflicting requests refuses upgrade
atomically and retains all records; an operator must resolve the actual conflict,
never let a migration arbitrarily pick a bank version.

Actual verification:

```
uv run pytest tests/unit/test_product_intake.py -q --timeout=180
9 passed in 23.78s                         # initial intake subset
uv run pytest tests/unit/test_product_intake.py tests/unit/test_real_decisions.py -q --timeout=180
1 failed, 22 passed in 82.67s              # exposed missing migration index
uv run pytest tests/unit/test_product_intake.py::test_concurrent_bank_changes_rollback_losing_vault_write tests/unit/test_product_intake.py::test_cli_import_preserves_historical_master_source_and_actual_import_time tests/unit/test_real_decisions.py::test_expired_halt_clear_round_requires_new_signatures_even_with_same_reason -q --timeout=180
3 passed in 11.72s                        # after index correction
uv run pytest tests/unit/test_intake_migration.py -q
1 passed in 0.59s
uv run pytest tests -q --timeout=180
859 passed, 37 skipped in 256.28s
uv run python -m tests.support.http_smoke
exit 0; separate-process loopback HTTP login, evidence, supplier, invoice,
duplicate/CSRF enforcement and logout passed; readiness remained 503
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
82 files already formatted
uv run mypy app
Success: no issues found in 48 source files
git diff --check
exit 0
uv run python -m app.cli import-contact --help
exit 0
```

The full suite ran after all runtime changes and includes the migration, concurrency,
review-tampering/replay, malformed-input, encrypted evidence, historical import and
expired halt-round cases. The standalone HTTP harness was subsequently added and
run against an actual separate Uvicorn process using temporary test-only business
data. It does not prove browser/device passkeys or provider acceptance. The 37 skips
remain 36 unimplemented compliance-index milestones and one unconfirmed live test.

Still unfinished: continuous worker/job processing and truthful heartbeat readiness,
provider-backed planning, FX execution, complete poll/settlement/return handling,
reconciliation, outbound rate budgets, operational UI, full-app launcher and legacy
test-signer/demo-source relocation. No sandbox credentials were added or live calls
claimed. Vedant still needs genuine business/master inputs, real device enrollment,
roster/policy approval and sandbox keys; engineering gaps remain independent of keys.
No demo/ media was changed; no push, PR, publication, deployment or external message.

## Stretch 7 — read-only refresh worker

Added `uv run python -m app.workers.service` with `--once`, sandbox/config/credential
guards, kernel process exclusion, bounded polling interval and graceful stop signals.
It performs real typed-client balance reads outside SQLite transactions, validates
finite amounts/unique currencies and provider clock, atomically persists an actual
dated observation with REFRESH completion, and records a heartbeat. Revoked requester
jobs fail. Failed reads mark pending jobs FAILED, preserve earlier observations and
their timestamps, and store only safe error categories. Every heartbeat remains
unready: this is a read-only refresh worker, not completed payment automation.

Actual checks after this worker addition:

```
uv run pytest tests/unit/test_refresh_worker.py tests/unit/test_airwallex.py -q --timeout=180
19 passed in 6.46s
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
84 files already formatted
uv run mypy app
Success: no issues found in 49 source files
```

The 859-pass full-suite run above preceded this isolated worker addition. These
targeted tests exercised real SQLite and the actual HTTP client with test-only
transport responses, plus missing-credential startup refusal without a socket.
No live balance read or background configured worker was claimed. Provider-backed
planning, payment polling/settlement, conversion execution, reconciliation, outbound
rate buckets, complete readiness, UI, launcher and legacy fixture relocation remain
unfinished. Real sandbox keys and real-device enrollment still require Vedant.

## Stretch 8 — supervisor verification and tracking/reconciliation foundations

First reran the complete suite after the refresh worker addition, before editing:

```
uv run pytest tests -q --timeout=180
862 passed, 37 skipped in 227.05s (0:03:47)
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
84 files already formatted
uv run mypy app
Success: no issues found in 49 source files
```

Added real provider GET polling of submitted/uncertain transfers, including those
previously marked FINAL. Audited intent/packet terms remain authoritative; a missing
attempt row is recovered from those terms without another payout POST. Missing USD
risk basis is not invented during recovery. Observations preserve first-paid time
and first failure details, tolerate skipped forward status transitions, ignore stale
backward snapshots and hold the obligation/bank version on failure, cancellation or
unknown status. Previously final/presumed-settled returns reopen tracking. Polling
uses audit/intent verification while permitting read recovery after approver revocation;
new money still requires the current trusted roster and actual signatures. The
refresh worker now invokes polling when transfer intents exist.

Migration 6 and a real reconciliation module capture fenced actual opening cash
totals and complete financial history. Missing totals, pending/reserved balances,
changed balances during a read, missing history and inconsistent postings fail
closed. Available balance is not confused with total cash. New settled transactions
produce exact balanced journal legs once. Existing posting legs are independently
verified, including detecting deletion of both legs. Cash residuals are exact;
an unmapped provider payout prevents a clean tie-out even if the residual is zero.
Opening terms are bound to their audit event. This module is not yet fully wired
into run/planning endpoints or settlement finalization; its tests do not constitute
live provider reconciliation acceptance.

Actual targeted runs during development:

```
uv run pytest tests/unit/test_real_executor.py -q --timeout=180
1 failed, 15 passed in 147.45s (0:02:27)
```

The failure was a new test referring to nonexistent `approval_signature.user_id`;
the actual column is `approver_id`. Corrected the test, then ran:

```
uv run pytest tests/unit/test_real_executor.py::test_revoked_approver_cannot_execute_already_approved_packet -q --timeout=180
1 passed in 11.36s
uv run pytest tests/unit/test_reconciliation_runtime.py -q --timeout=180
4 passed in 9.53s
uv run pytest tests/unit/test_reconciliation_runtime.py tests/unit/test_refresh_worker.py -q --timeout=180
7 passed in 14.00s
$env:CONFIRM_LIVE='1'
uv run pytest tests/live/test_airwallex_read.py -q -rs
SKIPPED [1] tests\live\test_airwallex_read.py:21: AWX_CLIENT_ID and AWX_API_KEY are not configured
1 skipped in 0.79s
```

All provider responses in these fault tests are test-only transport fixtures. No
live call, browser/device proof, actual money-worker OS-crash test, FX-expiry guard
or completed settlement lifecycle is claimed. The full supervisor scenario matrix,
settlement finalization, FX execution, complete service orchestration and removal
of legacy demo/signers remain required. PROD-AUDIT.md records the current source
scan honestly, including retained legacy code. No push, PR, publication, signup,
external message or demo/ media edit.

References consulted: [transfer lifecycle](https://www.airwallex.com/docs/payouts/transfers/create-a-transfer/transfer-statuses),
[failure/refund behavior](https://www.airwallex.com/docs/payouts/transfers/manage-transfers/handle-failed-transfers),
[cash balance fields](https://www.airwallex.com/docs/api/core_resources/balances/current),
[financial transaction fields](https://www.airwallex.com/docs/api/2024-08-07/finance/financial_transactions).

Final verification of this slice (after runtime changes, including read polling
after revocation and the new expired-approval case):

```
uv run pytest tests -q --timeout=180
871 passed, 37 skipped in 315.57s (0:05:15)
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
87 files already formatted
uv run mypy app
Success: no issues found in 51 source files
git diff --check
exit 0
```

The lint run initially found nested-context style in the new expiry test; it was
flattened without changing test behavior and lint then passed. The full suite
includes approval bypass/tampering, timeout/lookup idempotency, concurrent executor
calls, revoked approver refusal, expired approval during renewed cooling, provider
PAID with a missing attempt, skipped failure/return states and ledger mismatches.
It still does not prove actual OS process death mid-money-job or FX quote expiry
at execution: those remain explicit unfinished scenarios, along with bank-change
workflow coverage during cooling and full settlement orchestration.

### Settlement follow-through after the full-suite checkpoint

Added policy-calendar settlement labelling behind `Executor.reconcile_run`.
Actual audited intent terms, a current matched cash/financial tie-out, a single
matching settled payout principal, no payout reversal, and the full signed rail
window are required. First PAID observation starts the clock conservatively.
SWIFT can receive PRESUMED_SETTLED only, never FINAL by timer. Labels explicitly
remain policy assumptions; polling continues and late failure/cancellation reopens
them. Tranches, obligation closure and capped-bank activation follow a local FINAL.

```
uv run pytest tests/unit/test_real_executor.py::test_settlement_requires_reconciled_financial_payout_and_window_and_reopens_return -q --timeout=180
1 passed in 7.78s
uv run ruff check app tests --output-format concise
All checks passed!
uv run mypy app
Success: no issues found in 52 source files
```

The test includes a later provider cancellation, a partial refund net of an actual
fee, balanced return posting and continued REOPENED status. Provider values are
test-only HTTP fixtures. This addition follows the 871-pass full-suite checkpoint;
it has the targeted result above, not a newly claimed full-suite result. Run opening
and reconciliation still need complete service/API orchestration. FX and real OS
crash acceptance remain unfinished. No live provider/arrival proof is claimed.

## Stretch 9 — locked FX, authenticated jobs and actual process-crash proof

Done/not-done checklist for the supervisor's current assignment:

- [x] Locked-quote FX execution through the actual sandbox HTTP client. Only USD
  funding of a genuinely approved GBP/EUR payment shortfall is supported. Unsupported
  directions are refused. The quote binds currencies, date, CLIENT amounts, rate,
  expiry and maximum USD sale. Funding includes the signed fee reservation/native
  reserve floor; it is not an arbitrary speculative conversion.
- [x] Two real passkey approvals for the CONVERSION packet, independently of the
  underlying payment approvals. Requester separation, current roster, bank/callback,
  cooling, policy, balances, reserve/caps and expiry are checked again on the server.
- [x] Expired quotes require a fresh quote and re-approval. Changing the database's
  expiry column cannot extend the signed deadline. Locked quote changes, funding
  amount changes and market drift above the signed tolerance block execution.
- [x] Authenticated/CSRF-protected QUOTE and EXECUTE request routes backed by migration
  7 and durable jobs. The worker verifies approvals again. Duplicate requests coalesce;
  uncertain money outcomes remain lookup-only and PENDING rather than being reported
  as completed. Scheduled/overdue FX cannot silently fund a payout.
- [x] Every hard scenario listed below has a passing real test. The provider transport
  fixtures are confined to tests; product entry points construct the real client.
- [x] Scanned all of app/ for the requested terms. PROD-AUDIT.md indexes every match
  and its retained justification. Legacy helper/recording relocation is not falsely
  represented as deletion. A static boundary check verifies no product imports of
  recording/test modules, mock transport construction or legacy signing authority.
- [x] Full suite, ruff and mypy rerun, with actual output below.
- [ ] Live Airwallex contract/payment acceptance: keys remain absent; explicitly skipped.
- [ ] Overall production application: complete run/planning/reconciliation orchestration,
  operational UI/full-app launcher, real-device/browser acceptance and remaining
  compliance-index milestones are still unfinished. Readiness remains false.

Hard-scenario evidence (all included in the final full-suite run):

| Scenario | Actual test location |
|---|---|
| Direct API bypass and self-approval | tests/unit/test_execution_requests.py::test_direct_api_cannot_bypass_approval_and_self_approval_is_refused |
| Replayed/forged assertion | tests/unit/test_execution_requests.py::test_replayed_or_forged_assertion_does_not_approve_or_queue |
| Approval expiry during cooling | tests/unit/test_real_executor.py::test_approval_expiring_during_renewed_cooling_cannot_execute |
| Bank terms changed during cooling | tests/unit/test_execution_requests.py::test_bank_change_during_renewed_cooling_refuses_queued_execution |
| Concurrent actual worker processes | tests/unit/test_worker_process_crash.py::test_two_actual_worker_processes_cannot_double_execute |
| Duplicate execution requests/idempotency | tests/unit/test_execution_requests.py::test_duplicate_execution_requests_and_worker_retry_create_one_payout |
| Provider timeout, retry, no duplicate payout | tests/unit/test_real_executor.py::test_timeout_after_provider_commit_resolves_without_second_payout |
| Provider PAID but missing attempt and journal | tests/unit/test_reconciliation_runtime.py::test_provider_paid_payout_missing_attempt_and_journal_are_recovered_from_evidence |
| Actual OS process death with PENDING job, then restart | tests/unit/test_worker_process_crash.py::test_real_worker_process_death_then_restart_never_reposts |
| Quote expires between approval/execution | tests/unit/test_fx_execution.py::test_elapsed_quote_window_cannot_be_reused_even_if_database_expiry_is_extended |
| Fresh quote and new approvals | tests/unit/test_fx_execution.py::test_quote_expiry_requires_new_quote_and_new_human_approval |
| Rate/amount/bank drift | tests/unit/test_fx_execution.py::test_rate_amount_or_bank_drift_blocks_conversion |
| Conversion timeout recovery | tests/unit/test_fx_execution.py::test_conversion_lost_response_is_resolved_without_second_post |
| FX funds an actual payout including fee reservation | tests/unit/test_fx_execution.py::test_settled_fx_funds_the_real_payout_including_fee_reservation |

The crash test now really exits the worker process with os._exit after its test-only
provider commits, retaining PENDING job/PREPARED intent state. A new process resolves
that same request without another payout POST. This is stronger than the earlier
SystemExit-only test, but it remains an offline provider-transport test, not live
Airwallex crash acceptance. Recovery now restores a missing attempt's USD risk basis
from its original sealed INTENT; it never invents a replacement basis.

The two-process test initially exposed a Windows race: a losing worker wrote an
initial marker into byte zero after the winning worker had locked it, raising
PermissionError before normal lock contention handling. Removed the unnecessary
marker write; Windows supports locking beyond EOF. Both exclusion and actual process
crash/restart tests then passed. Initial API test setup also tried to duplicate an
approval hash, correctly hitting the database uniqueness constraint; the test now
constructs distinct canonical terms and their real hash without weakening the index.
An early FX fixture omitted rate currency fields and correctly failed validation;
the fixture was corrected to the provider protocol.

Added real outbound rolling budgets (20 requests globally and 10 per resource per
second). The shared client remains serialized, so concurrency is at most one.
Booked USD risk-rate selection compares timezone-aware dates and explicitly requests
history rather than assuming the provider's default 31-day listing is complete.
Execution observation age now starts before its first read, preventing later slow
guard reads from making an old balance appear fresh. Its regression test passed.
Removed the diagnostic page's static claim that no supplier/balance data is loaded,
and corrected stale read-only-worker documentation. The final diagnostic copy was
separately exercised by the separate-process HTTP smoke harness while the full
suite ran; no financial behavior changed after that full run began.

Actual final command output:

```
uv run pytest tests -q --timeout=180
891 passed, 37 skipped in 270.69s (0:04:30)
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
97 files already formatted
uv run mypy app
Success: no issues found in 55 source files
uv run python -m tests.support.audit_runtime_imports
PASS: 50 product modules; no recording/test imports, mock transport or legacy authority calls
uv run python -m tests.support.http_smoke
PASS: separate-process HTTP login, evidence, supplier, invoice, duplicate/CSRF, logout
PASS: health remains unready; no provider, device or payment acceptance claimed
git diff --check
exit 0
```

An earlier full run before the observation-age correction reported exactly
`890 passed, 37 skipped in 271.91s`. The new freshness regression plus rate-budget
test then reported `2 passed in 5.39s`, followed by the final full run above.
Other actual focused runs included `25 passed in 47.03s` (FX/client),
`5 passed in 24.14s` (direct API), `4 passed in 16.25s` (process/lock), and
`1 passed in 6.08s` (missing payout ledger recovery). These are not added together
or presented as live acceptance. The 37 skips remain the 36 legacy compliance-index
placeholders and the unconfirmed live test.

Explicit live guard invocation and actual result:

```
uv run python -c "import os, pytest; os.environ['CONFIRM_LIVE']='1'; raise SystemExit(pytest.main(['tests/live/test_airwallex_read.py','-q','-rs']))"
SKIPPED [1] tests\live\test_airwallex_read.py:21: AWX_CLIENT_ID and AWX_API_KEY are not configured
1 skipped in 0.65s
```

The native terminal launcher returned Access is denied (OS error 5), so verification
used the same local executables through the Node process tool. A PowerShell launcher
also lacked uv on its PATH; the explicit live guard above succeeded through uv's
Python entry point. Neither failed launcher is reported as passing.

Vedant still must supply real sandbox credentials, genuine business/master inputs,
real-device enrollment and signed policy/roster approvals before live acceptance.
No account signup, external message, push, PR, publication or demo/ media edit.
Keys were not printed, logged or committed. No claim of overall production readiness.

Protocol references: [locked quotes](https://www.airwallex.com/docs/api/transactional_fx/quotes/create),
[conversion request/lookup](https://www.airwallex.com/docs/api/transactional_fx/conversion/create),
[Windows byte-range locking](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking?view=msvc-170).


## 2026-11-14: operational UI, isolation and security verification

This section supersedes the preceding stretch's implementation checklist. It does
not supersede the explicit lack of live provider acceptance.

- [x] Historical recording code and legacy signers moved under `tests/support/`; shared product modules contain no HMAC authority helpers.
- [x] Static scan of every product Python module plus isolated imports of web, worker, executor, CLI and launcher reject transitive archive/test imports.
- [x] Real operational UI wired to authenticated approval packets, server-time cooling deadlines, execution/payment states, durable jobs, tie-outs and exceptions.
- [x] Durable run opening, planning, reconciliation and closing consume the real provider client; open-run recovery preserves its original committed baseline.
- [x] Server-side approver authorization, CSRF checks and cancellation/state rechecks prevent direct API bypass and stale-tab approvals.
- [x] Startup configuration refuses unsafe modes/origins/signing; structured logs redact secrets and omit private exception bodies, with real tests.
- [x] Health/readiness report persisted worker/provider freshness and actual worker control checks; missing keys fail closed.
- [x] One-command local launcher, secret separation and exact setup variables documented; separate-process HTTP and headed browser checks run.
- [ ] Live sandbox contract and money acceptance: blocked on absent Airwallex sandbox credentials; explicitly skipped, never represented by test doubles as live proof.
- [ ] Owner acceptance with genuine business/master records and physical passkeys: not performed by this agent. Chromium virtual authenticator checks are not physical-device proof.

The current product supports manual evidence-backed intake/review, not optional
PDF/LLM extraction or autonomous T0 payment approval. Historical spec-index tests
remain in the suite with 36 declared skips. Their broad milestone descriptions are
old compatibility bookkeeping; they are **not passed**, and this stretch does not
claim complete original-spec certification. Current implementation evidence is in
`test_operation_jobs.py`, `test_operations_security.py`, `test_product_readiness.py`,
`test_runtime_boundary.py`, and the existing real executor/FX/reconciliation suites.
No automated sanctions-provider acceptance or real bank-account ownership check is
claimed. Those capabilities are not replaced by fabricated responses.

Observed focused commands and final results:

```text
uv run pytest tests/unit/test_operations_security.py tests/unit/test_product_webhooks.py tests/unit/test_operation_jobs.py tests/unit/test_execution_requests.py tests/unit/test_refresh_worker.py -q --timeout=180
40 passed in 218.06s (0:03:38)
uv run pytest tests/unit/test_product_readiness.py -q --timeout=180
8 passed in 3.28s
uv run python -m tests.support.audit_runtime_imports
PASS: 53 product modules scanned; 5 isolated entry imports; archive imports and legacy signers forbidden
uv run python -m tests.support.http_smoke
PASS: separate-process HTTP login, evidence, supplier, invoice, duplicate/CSRF, logout
PASS: health remains unready; no provider, device or payment acceptance claimed
uv run python -m tests.support.http_smoke --launcher
PASS: separate-process HTTP login, evidence, supplier, invoice, duplicate/CSRF, logout
PASS: health remains unready; no provider, device or payment acceptance claimed
PASS: one-command launcher serves real HTTP with missing-key readiness; owned children stopped
uv run python -m tests.support.browser_smoke --headed
PASS: ops UI hides money controls; direct requests to every packet action are refused
PASS: browser passkey registration and approval verify on the server; CSRF is refused
PASS: genuine browser assertion from tab A is refused after tab B cancels
PASS: cancellation updates the approval UI; mobile layout fits; no browser script errors
```

Browser preview reported `available:false`; a separate visible Playwright Chromium
session was used and closed. Browser records are disposable fixtures strictly under
test support; the service and WebAuthn verifier are real, with no provider calls.
Desktop/mobile screenshots and the browser result are local, ignored artifacts at
`output/playwright/`. The test browser/server were closed after verification.

Defects found and repaired during this stretch: policy role checking occurred after
policy access; it now runs first. Settings are resolved once at startup, so webhook
secret-removal testing now restarts the application rather than assuming hot reload.
A Windows virtualenv launcher can leave a Python child behind; owned process trees
are now stopped, preventing orphan workers and test database handles. The first
browser test's cleanup failed on an open database; the final headed rerun above
returned exit 0. Earlier failing attempts are not counted as passing checks.

Explicit live guard:

```text
uv run python -c "import os, pytest; os.environ['CONFIRM_LIVE']='1'; raise SystemExit(pytest.main(['tests/live/test_airwallex_read.py','-q','-rs']))"
SKIPPED [1] tests\live\test_airwallex_read.py:21: AWX_CLIENT_ID and AWX_API_KEY are not configured
1 skipped in 1.28s
```

Vedant must provide his existing sandbox credentials and webhook signing secret
privately, provision the real roster/entity/reserve, register passkeys, obtain two
policy signatures, pin the reviewed roster, and supply genuine bank/contact/invoice
evidence before live acceptance. No signup or credential entry was attempted.
No keys printed/committed, no external messages, push, PR, publication, or root
`demo/` media changes. Final verification output is recorded below.


The first full run after the UI/worker changes finished with:
`1 failed, 926 passed, 37 skipped in 561.75s (0:09:21)`.
The failed policy HTTP fixture changed APP_POLICY_PATH after startup. The fixture
now establishes its path before creating the app, preserving startup-only config.
The corrected scenario command and observed result:

```text
uv run pytest tests/unit/test_real_decisions.py::test_real_policy_callback_and_halt_http_flows -q --timeout=180
1 passed in 8.85s
uv run pytest tests/unit/test_operation_jobs.py -q --timeout=180
4 passed in 31.25s
```

The latter run includes successful clean run closure, durable baseline recovery,
planning during cooling/revocation refusal, and malformed queued payload refusal.
These focused checks do not replace the final full-suite rerun.


### Final full-suite rerun, exact captured output

The actual PowerShell command also preserved stdout/stderr to a local ignored artifact:

```powershell
uv run pytest tests -q --timeout=180 2>&1 | Tee-Object -FilePath output/playwright/final-pytest.txt
exit $LASTEXITCODE
```

Exit code: 0. Exact test output:

```text
........................................................................ [  7%]
........................................................................ [ 14%]
........................................................................ [ 22%]
........................................................................ [ 29%]
..................ss.sssss.ssssss.sss.s.ssssssss.sssssssssss............ [ 37%]
...................................s.................................... [ 44%]
........................................................................ [ 52%]
........................................................................ [ 59%]
........................................................................ [ 67%]
........................................................................ [ 74%]
........................................................................ [ 82%]
........................................................................ [ 89%]
........................................................................ [ 96%]
.............................                                            [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-01 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-02 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-04 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-04b belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-04c belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-05 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-06 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-08 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-09 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-10 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-10b belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-11 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-12 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-14 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-15 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-16 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-18 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-20 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-21 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-21b belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-22 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-23 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-24 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-25 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-26 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-28 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-29 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-30 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-31 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-32 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-33 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-34 belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-R4a belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-R4b belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-R4c belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\acceptance\test_compliance_index.py:205: T-R4d belongs to a milestone not built yet (see docs/PROGRESS.md). �10.1 rule 8: a skip needs a README known-gaps line before the freeze.
SKIPPED [1] tests\live\test_airwallex_read.py:19: Read-only sandbox test requires CONFIRM_LIVE=1
928 passed, 37 skipped in 560.91s (0:09:20)
```

Final lint/type checks (exit 0):

```text
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
110 files already formatted
uv run mypy app
Success: no issues found in 53 source files
```

`git diff --check` returned exit 0. Comparing against the starting commit `a938d47`,
`git diff a938d47 --name-only -- demo` produced no paths. The 37 skips comprise
36 historical spec-index placeholders and one unconfirmed live test; the separate
confirmed live guard above reported absent credentials. No skip is counted as a pass.


## Next stretch: remove deferred tests and attack execution interleavings

The following checklist supersedes the preceding stretch's historical-index gap.

- [x] All 36 not-written placeholder skips removed: 24 replaced by registered behavior tests, 12 obsolete cases deleted with per-ID reasons in PROD-AUDIT.md and scope rationale in DECISIONS.md. Deleted cases are not claimed as passes.
- [x] Active registry entries require actual collected test functions, including inherited class markers. Marker-looking strings/comments do not count; there is no PENDING exemption.
- [x] Replay/double approval, unsigned callback evidence, tampered cooling deadline, provider clock skew, corrupt beneficiary last-four, and IST daily cap boundaries exercised.
- [x] Kill after durable claim but before the payout POST exercised in a real child process; restart is lookup-only with one consumption and no blind repost.
- [x] Timeout/accepted-but-response-lost retries preserve the original request identity and create one provider payout/conversion; ambiguous absence does not authorize a new attempt or cross-run replan.
- [x] Duplicate/out-of-order signed webhook hints cannot override actual GET state; forged signatures are rejected.
- [x] Expired quotes, including a 60-second quote inside the safety margin, require a new quote and new human approval; rate/bank/amount drift blocks conversion.
- [x] Actual concurrent worker processes race on the same packet. Cancel/execution races are tested in both orders with HTTP barriers, independent of UI visibility.
- [x] Halt or raw policy replacement after claim prevents POST. A replacement policy newly signed by two real test passkeys also invalidates the old payment approval.
- [x] Real defect fixed: provider compliance failure now trips persistent halt, retains a separate destination/obligation compliance hold, and voids unused destination approvals. Polling continues while halted.
- [x] Product source grep completed; each remaining match has a line-level disposition in PROD-AUDIT.md. No product-path test doubles introduced.
- [x] Final full suite, ruff check, format check and mypy completed; exact output below.
- [ ] Live Airwallex acceptance: sandbox credentials remain absent; live guard explicitly skips with reason.
- [ ] Owner acceptance using real business/contact/bank/invoice records and physical passkeys remains unperformed. Test virtual authenticators are not physical-device acceptance.

Only synthetic HTTP boundaries and explicit test clocks/data are used in tests;
production executor, SQLite, WebAuthn verification, state machine and audit logic
are exercised directly. No money guard or signature verifier is replaced by a stub.
The process-kill fixture waits after TRANSFER claim and kills the owned process tree
before a payout POST; a missing provider result is honestly retained as AMBIGUOUS.

Actual focused results so far:

```text
uv run pytest tests/unit/test_execution_adversaries.py -q --timeout=180 --tb=short
16 passed in 116.80s (0:01:56)
uv run pytest 'tests/unit/test_execution_adversaries.py::test_control_change_after_claim_prevents_the_money_post[signed_policy]' -q --timeout=180 --tb=short
1 passed in 10.21s
uv run pytest tests/unit/test_execution_adversaries.py::test_signed_callback_first_payment_is_capped_and_remainder_held tests/unit/test_execution_adversaries.py::test_unsigned_callback_row_never_authorizes_execution tests/unit/test_execution_adversaries.py::test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused -q --timeout=180 --tb=short
3 passed in 24.70s
```

The first focused adversarial run found the real compliance-halt defect.
Additional test-development failures were not passing verification: the initial
cooling test encountered the future-dated review guard before cooling, so it now
creates a genuine newly signed callback at 71 hours; the first tranche fixture
needed to replace its test setup's old tranche split, and its cap assertion needed
to allow the conservative risk margin (the cap is an upper limit). A partial
selection including the registry deliberately lacked required collected cases;
the final registry check runs with the full suite and includes class-level markers.
No such earlier failed command is counted as passing.

Explicit confirmed live guard:

```text
uv run python -c "import os, pytest; os.environ['CONFIRM_LIVE']='1'; raise SystemExit(pytest.main(['tests/live/test_airwallex_read.py','-q','-rs']))"
SKIPPED [1] tests\live\test_airwallex_read.py:21: AWX_CLIENT_ID and AWX_API_KEY are not configured
1 skipped in 0.53s
```


Final full-suite invocation (PowerShell captured both streams to the local ignored artifact):

```powershell
uv run pytest tests -q --timeout=180 --tb=short 2>&1 | Tee-Object -FilePath output/playwright/adversarial-full-pytest.txt
exit $LASTEXITCODE
```

Exit code 0. Exact captured output:

```text
........................................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 31%]
............................................s........................... [ 39%]
........................................................................ [ 46%]
........................................................................ [ 54%]
........................................................................ [ 62%]
........................................................................ [ 70%]
........................................................................ [ 78%]
........................................................................ [ 85%]
........................................................................ [ 93%]
...........................................................              [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\live\test_airwallex_read.py:19: Read-only sandbox test requires CONFIRM_LIVE=1
922 passed, 1 skipped in 659.47s (0:10:59)
```

Final checks (all exit 0):

```text
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
111 files already formatted
uv run mypy app
Success: no issues found in 53 source files
```

The single full-suite skip is the unconfirmed live guard. The separate confirmed
guard above explicitly reported absent sandbox credentials. There are no historical
not-written skips. The changed test total reflects removal of obsolete cases and
redundant index-bookkeeping parameterizations, together with new behavior tests;
it is not a claim that deleted historical scenarios passed.

`git diff --check` returned exit 0. Comparison to starting commit `bf575fd` showed
no paths under root `demo/`. Code/test/audit decision commit: `e360a20`.
No push, PR, publication, signup, external message, or secret disclosure. Live
Airwallex and owner/physical-device acceptance remain the open items above.


## Acceptance evidence review: counts, exact nodes and mutations

The detailed report is [PROD-ACCEPTANCE-EVIDENCE.md](PROD-ACCEPTANCE-EVIDENCE.md).
It lists every one of the 96 removed/merged collected nodes and all 54 additions
between bf575fd and ba02b6e, with individual reasons/replacements. The only removed
behavior node is the GBP quote-expiry node expanded into two parameter cases.
Registry completeness and nonempty descriptions/milestones were lost in the rewrite;
those bookkeeping guarantees are now restored. No monetary behavior coverage was lost.

Actual collection results, using a detached temporary bf575fd worktree and removing
it afterwards: bf575fd `965 tests collected in 5.09s`; initial HEAD ba02b6e
`923 tests collected in 1.77s`. Temporary worktree removal returned exit 0 and
`git worktree list` then listed only the current checkout. Arithmetic:
`965 - 96 + 54 = 923`; passes `928 - 60 + 54 = 922`; skips `37 - 36 = 1`.
The current review adds two real behavior tests, giving 925 collected nodes.

Requested scenario selection uses exactly the unique nodes in
`tests/support/acceptance_scenarios.json`, with output:

```text
.............                                                            [100%]
13 passed in 91.48s (0:01:31)
```

The manifest maps one line per requested scenario; the single webhook test covers
all three webhook assertions, and cancel runs both interleavings. The separate
role-positive-control bundle reported `2 passed in 15.09s`.

Six mutations were applied individually with valid Python syntax, tested, and
restored byte-for-byte. All six final mutations failed relevant test calls, with
no setup/collection errors. SHA-256 before/after matched and git status was empty
after each restore. The initial unsigned-packet role test survived the role mutation
(`1 passed in 5.70s`, exit 0), exposing a test blind spot; the new fully approved
packet test fails that same mutation (202 instead of required 403).
The other mutations bypass cooling, omit consumption persistence, replace the
persisted retry lookup key with a fresh UUID, bypass HMAC verification, and remove
the halt guard. Full failure outputs are in the detailed report, not presented as
successful product tests. No deliberate product mutation remains.

Current open-items checklist, verbatim:

- [ ] Live Airwallex acceptance: sandbox credentials remain absent; live guard explicitly skips with reason.
- [ ] Owner acceptance using real business/contact/bank/invoice records and physical passkeys remains unperformed. Test virtual authenticators are not physical-device acceptance.

These need private provider credentials, genuine owner inputs or a physical device;
no key-independent engineering task remains in this open-items checklist. Real
business records must not be invented to close owner acceptance. The local count,
coverage and mutation evidence work is implemented; final restored-tree checks
are recorded below after process completion. No signup or external communication.

## Final restored-tree verification

```powershell
uv run pytest tests -q --timeout=180 --tb=short 2>&1 | Tee-Object -FilePath output/playwright/acceptance-evidence/final-full-pytest.txt
exit $LASTEXITCODE
```

Exit 0; exact captured output:

```text
........................................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 31%]
............................................s........................... [ 38%]
........................................................................ [ 46%]
........................................................................ [ 54%]
........................................................................ [ 62%]
........................................................................ [ 70%]
........................................................................ [ 77%]
........................................................................ [ 85%]
........................................................................ [ 93%]
.............................................................            [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\live\test_airwallex_read.py:19: Read-only sandbox test requires CONFIRM_LIVE=1
924 passed, 1 skipped in 743.13s (0:12:23)
```

```text
uv run ruff check app tests --output-format concise
All checks passed!
uv run ruff format --check app tests
112 files already formatted
uv run mypy app
Success: no issues found in 53 source files
```

Confirmed live guard (also exit 0, skipped rather than faked):

```text
uv run python -c "import os, pytest; os.environ['CONFIRM_LIVE']='1'; raise SystemExit(pytest.main(['tests/live/test_airwallex_read.py','-q','-rs']))"
SKIPPED [1] tests\live\test_airwallex_read.py:21: AWX_CLIENT_ID and AWX_API_KEY are not configured
1 skipped in 0.66s
```

Final review-tree counts reconcile to `965 - 96 + 56 = 925` collected tests:
the earlier 54 additions plus two mutation-sensitive behavior tests. Passing
counts therefore reconcile to `928 - 60 + 56 = 924`, with one live skip.
No actual monetary behavior test was deleted. The metadata assertions identified
as lost were restored, and the full suite above includes them.

Acceptance evidence work is complete: count/node reconciliation, restoration of
registry guarantees, exact scenario run, and six killed-and-reverted mutations.
`git diff --check` returned exit 0. Root demo files remain unchanged from bf575fd.
Only the two key/device/owner-dependent open items listed above remain. No push,
PR, publication, signup, outside-team message or secret disclosure.
