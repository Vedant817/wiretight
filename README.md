# Wiretight: supplier payouts that can't be quietly redirected

> *New or changed bank details stay locked until a second person confirms them by callback.*

**The rule:** no payout reaches a bank account that a human hasn't confirmed and signed off on exact terms.

Wiretight runs a small company's weekly cross-border supplier payment run on the
Airwallex **sandbox**. Code, never the model, decides money. Every sign-off is a passkey
signature over a hash of the exact terms. Any new or changed bank details go through a lock:
a signed operations callback to an older contact, a cooling-off period, two sign-offs, and a
capped first payment. `PAID` is provisional. Reconciliation against Airwallex financial
transactions is implemented against the real sandbox client. Live provider acceptance
has not been performed; this is not a claim of production payment readiness.

---

## Local setup and current status

The operational desk includes the approval queue, passkey approval, server-enforced
cooling, execution requests/status, run planning and reconciliation exceptions.
All provider observations and money requests go through the genuine sandbox client.
Test fixtures and historical recording tools live under `tests/support/`.
See [the audit](docs/PROD-AUDIT.md) and [verified status](docs/PROD-STATUS.md).
Known verification gaps: the original spec index still has 36 declared skipped
placeholders; real sandbox and physical-device acceptance are not established.
Passing the current focused tests does not certify every historical spec milestone.

With Python 3.12 and uv installed, install pinned dependencies and start both isolated
processes with one command:

```powershell
uv run --frozen --extra dev python -m app.local
```

Open `http://localhost:8000/`. The launcher removes Airwallex credentials from the
web process and the LLM/webhook secrets from the worker's environment. Ctrl+C stops
the owned children, including Windows virtualenv launcher descendants. On Windows,
process-tree termination is abrupt; committed money intents remain recoverable.

Use environment variables or a **gitignored** `.env`. Required for provider operation:

| Variable | Value or purpose |
|---|---|
| `AWX_CLIENT_ID` | Your existing Airwallex sandbox client ID; worker only |
| `AWX_API_KEY` | Your existing sandbox API key; worker only |
| `AWX_WEBHOOK_SECRET` | Your sandbox webhook signing secret; web only |

The following defaults require no configuration for localhost:
`AWX_ENV=sandbox`, `AWX_BASE_URL=https://api.sandbox.airwallex.com`, `AWX_MODE=live`,
`SIGNING_MODE=webauthn`, `APP_HOST=127.0.0.1`, `APP_PORT=8000`,
`WEBAUTHN_RP_ID=localhost`, `WEBAUTHN_ORIGIN=http://localhost:8000`,
`APP_DB_PATH=var/app.sqlite`, `APP_POLICY_PATH=policy.yaml`, `APP_KEY_DIR=var/keys`,
`APP_HALT_FILE=var/HALT`, `APP_AUDIT_CHECKPOINT_DIR=var/audit-checkpoints`,
`POLL_INTERVAL_S=2`, `AWX_HTTP_TIMEOUT_S=20`, `LOG_LEVEL=INFO`.
Optional provider headers: `AWX_LOGIN_AS`, `AWX_API_VERSION`.
If changing the origin, set a matching RP ID and use HTTPS outside localhost.
Recording modes, HMAC signing and shortened cooling configuration are refused.

Without keys the worker exits 2 and records a setup error without contacting the
provider. The UI remains available; `/health` and `/ready` return 503 with the real
missing dependency state. Readiness requires a fresh worker heartbeat, a fresh
provider balance observation, trusted operator keys, signed policy, no halt, and
successful reconciliation checks. It is never a live-acceptance certificate.

To run only the web service, remove Airwallex credentials from its process environment:
`uv run uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --no-access-log`.
The separate worker is `uv run python -m app.workers.service` (`--once` for one cycle).
It consumes REFRESH, PLAN, QUOTE and EXECUTE jobs, watches transfers/conversions,
and reconciles open runs. A crash never authorizes a second blind money POST.

Run offline checks with `uv run --extra dev pytest tests -q --timeout=180`,
`uv run ruff check app tests`, `uv run ruff format --check app tests` and
`uv run mypy app`. The read-only sandbox test additionally requires
`CONFIRM_LIVE=1` and both credentials; otherwise it reports a skip with the reason.
Do not treat passing HTTP fault tests as recorded sandbox contracts.

Provision each real operator locally with `uv run python -m app.cli operator-add`
and the required `--name`, `--email`, `--role approver|ops` options (password prompted,
14–256 characters; no password argument). Use three distinct approvers and a separate
ops operator for the two-person approval workflow. There are no default accounts.
`operator-disable --email ...` immediately revokes an operator's sessions and approval
eligibility. Both commands accept `--db`; otherwise they use `APP_DB_PATH`.
Passkey APIs use `WEBAUTHN_RP_ID` (default `localhost`) and `WEBAUTHN_ORIGIN`
(default `http://localhost:8000`); HTTPS is required outside localhost. The account
section offers passkey registration and policy review/signing. Password login alone cannot
approve a payment: sign-off requires a user-verified passkey assertion bound to the
exact packet hash. No HMAC or test signer is accepted by these product endpoints.
Runtime policy approval requires two passkeys and an exact match to the configured
entity and enabled roster. Callback confirmation records the full 72-hour minimum
cooling window. Clearing a database halt needs two fresh sign-offs; a local `HALT`
file remains an independent stop. The operations desk exposes these approvals and
execution requests; the worker rechecks all authoritative controls.

After provisioning the roster, `init-installation --legal-name ... --reserve-usd ...`
creates the business, policy and private local keys using the values you supply.
After real passkey enrollment and policy signing, `trust-operators` pins the enrolled
roster outside SQLite. Use `uv run python -m app.cli <command> --help` for paths and
arguments. Never put a password or Airwallex key in command arguments. Enroll each
operator in the UI, have two independent approvers sign the policy, then pin the
reviewed roster with `trust-operators`. Provision at least three approvers and an
independent ops callback recorder. These genuine human setup steps are required;
the launcher creates no business records. Supplier/evidence intake uses the
authenticated API below; planning, approvals and operational follow-up use the UI.

Authenticated intake routes are documented in [the intake guide](docs/INTAKE.md).
New contacts get the current time. To import an existing supplier-master contact,
use `import-contact` with its actual historical timestamp and genuine source file;
the CLI prompts for an existing operator password and records both the claimed
master date and actual import time. It does not record a callback or bypass cooling.

This repository is being built from `docs/spec/FINAL.md` (v1.0, locked). **Nothing here has been
run against a live Airwallex sandbox yet.** The readme, the metrics table and the demo script are
written when there is something true to put in them — see `docs/PROGRESS.md` for what is real so
far and `docs/NEEDS_HUMAN.md` for what is blocked.

Every API behaviour in the spec is currently marked **⚠ unverified**: it comes from Airwallex's
documentation, not from an observed call. `docs/undocumented-behaviour.md` carries the register,
and a check stays `NOT RUN` until a real, redacted fixture backs it.

## Honest disclosures

- **Sandbox only.** The app refuses to start unless `AWX_ENV=sandbox` and `AWX_BASE_URL` is
  exactly `https://api.sandbox.airwallex.com`. There is no production URL anywhere in `app/`.
- The product starts empty and requires your business data. Historical recording
  tools and tests use synthetic fixtures; product routes do not seed those fixtures.
- The callback record is **evidence of** a callback; the system cannot prove a phone call happened.
- **No automated sanctions screening integration** is available. Product compliance
  review records are evidence-backed manual operator decisions signed with a passkey,
  bound to the exact bank version and valid for at most 24 hours. They do not prove
  that a sanctions provider cleared the beneficiary. The synthetic demo list is isolated.
- A passkey signature proves a registered device holder signed these exact terms in this app.
  It is **not** a legal e-signature.
- Process separation (web vs worker) is **logical, on one laptop** — not OS-level isolation.
  Someone with shell access can read `.env`.
- The FPS and ACH return windows and the per-rail cut-off times are **assumptions**, labelled as
  such wherever they appear. None of the policy floor numbers is an industry standard.
- No metrics table appears here yet. When it does it is generated from `eval/results/`, never
  typed by hand.

## Layout

```
app/        the system: core trust substrate, integrations, workers, api
eval/       20 labelled scenarios and the harness that computes the metrics
scripts/    day-1 spike, fixture recording, seeding, demo runner
tests/      unit · property · contract · acceptance · live
docs/       spec/ (read-only) · PROGRESS · DECISIONS · NEEDS_HUMAN · undocumented-behaviour
```

## Source of truth

`docs/spec/FINAL.md` is the locked v1.0 specification. The current production assignment
requires human approval for every money action and forbids demo timing in the product.
These requirements take precedence over the historical demo/T0 allowances; deviations
are recorded in `docs/DECISIONS.md`.

## Demo mode (simulated)

The branch `demo/video` carries a labelled demo mode used for the pitch recording. Run it with
`make demo-video` (or `DEMO_MODE=video uv run python -m tests.support.recording.server --port 8765`). The server
refuses to start without `DEMO_MODE=video` and refuses to start if Airwallex credentials are
visible in its environment. Nothing in it talks to the network.

What is real in demo mode: the decisions on screen are computed by the production modules in
`app/core` — vendor match and lookalike-domain distance, duplicate classification (`HARD_BLOCK`),
IBAN parsing and bank fingerprints, the out-of-band callback rules (rule 2 contact checks, rule 3
requester independence, rule 7 signed recorder callbacks via Ed25519), cooling-off and
first-payment-cap tranche splits, the transfer status state machine, ledger balance checks for the
tie-out, and the audit hash chain.

What is simulated: the company (Halden Robotics), people (Arun, Priya, Meera, Kabir), suppliers,
emails, IBANs, amounts and every Airwallex response — produced by a mocked
`MockAirwallexClient` (`tests/support/recording/mock_airwallex.py`) that returns documented-shape responses from
a script and never opens a socket. The UI pages are demo-only HTML, not the product UI; the
executor, poller and passkey flows are not exercised. A persistent on-screen badge reads
`SIMULATED DEMO DATA · Airwallex sandbox calls mocked`, and synthetic items carry
`synthetic email`, `FIXTURE`, `mocked API response` or `demo timing` tags. The demo recording under
`demo/` is generated from this branch and no live Airwallex call, customer, revenue figure or
metric claim appears in it; the only statistics shown are the sourced ones footnoted on screen.

## License

Apache-2.0.
