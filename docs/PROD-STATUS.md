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

- Durable executor, lookup/recovery orchestration, live policy/cap/reserve rechecks,
  signature re-verification and exactly-once approval consumption are not built.
- Operator authentication/authorization, passkey enrollment, approval and callback
  workflows, supplier/invoice ingestion and the operational UI are not built.
- Ledger-to-provider reconciliation, settlement windows, incident handling and poller
  are not built. Existing core tests do not certify those missing integrations.
- Runtime configuration still has historical replay/demo vocabulary; the product
  diagnostic surface refuses readiness, but removal from shared settings is pending.
- Global account creation, beneficiary ambiguous-create recovery, conversion recovery,
  startup audit sealing, outbound rate buckets, structured operational logs and
  credential-separated worker readiness remain incomplete.
- Historical app/demo recording source remains isolated; fixtures have not yet been
  relocated into tests. No files inside demo/ were edited.
- Approval double clicks, crash/restart without duplicate payout, insufficient-balance
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
