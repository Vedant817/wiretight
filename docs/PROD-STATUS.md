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
