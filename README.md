# Wiretight: supplier payouts that can't be quietly redirected

> *New or changed bank details stay locked until a second person confirms them by callback.*

**The rule:** no payout reaches a bank account that a human hasn't confirmed and signed off on exact terms.

Wiretight runs a small company's weekly cross-border supplier payment run on the
Airwallex **sandbox**. Code, never the model, decides money. Every sign-off is a passkey
signature over a hash of the exact terms. Any new or changed bank details go through a lock:
a signed operations callback to an older contact, a cooling-off period, two sign-offs, and a
capped first payment. `PAID` is provisional. Every wallet movement ties out against Airwallex
financial transactions.

---

## ⚠ Status: under construction

**Production assignment status (14 November 2026): incomplete.** The new product
service includes readiness, webhooks, authenticated operator sessions and passkey
approval APIs, plus signed policy, callback and halt-clear decisions. A guarded
payout dispatcher now exists with offline fault tests; the service loop, conversion
execution, reconciliation and operational UI are unfinished. See
[the audit](docs/PROD-AUDIT.md) and [verified status](docs/PROD-STATUS.md).
The real sandbox HTTP client has offline fault tests; it has no live acceptance yet.
The 36 skipped compliance-index tests correspond to missing milestones (including
approvals, execution, reconciliation, and operator UI); they are known gaps.

From a fresh checkout with Python 3.12 and uv installed, run this single command
to install pinned dependencies and start the diagnostic service on localhost:

```powershell
uv run --frozen --extra dev uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open `http://127.0.0.1:8000/`. `/health` and `/ready` return HTTP 503 with setup and
implementation blockers. This command does not create companies, fund accounts,
simulate transactions or enable money movement.

Current service variables (set in its process environment): `AWX_ENV=sandbox`,
`AWX_BASE_URL=https://api.sandbox.airwallex.com`, `AWX_MODE=live`,
`APP_DB_PATH` (optional; defaults to `var/app.sqlite`), and `AWX_WEBHOOK_SECRET`
(required only for receiving signed webhooks). Keep Airwallex API credentials out
of the web process. Worker/client credentials are `AWX_CLIENT_ID` and `AWX_API_KEY`,
read by `WorkerSettings` from environment or a gitignored `.env`; optional
`AWX_LOGIN_AS`, `AWX_API_VERSION`, `AWX_HTTP_TIMEOUT_S` configure the client.
There is no functional worker command yet. No production-host mode is supported.

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
(default `http://localhost:8000`); HTTPS is required outside localhost. Operator UI
and first-run enrollment screens are still pending. Password login alone cannot
approve a payment: sign-off requires a user-verified passkey assertion bound to the
exact packet hash. No HMAC or test signer is accepted by these product endpoints.
Runtime policy approval requires two passkeys and an exact match to the configured
entity and enabled roster. Callback confirmation records the full 72-hour minimum
cooling window. Clearing a database halt needs two fresh sign-offs; a local `HALT`
file remains an independent stop. First-run business/policy setup and the operator
screens are still under construction, so these APIs do not yet form a usable
payment application.

After provisioning the roster, `init-installation --legal-name ... --reserve-usd ...`
creates the business, policy and private local keys using the values you supply.
After real passkey enrollment and policy signing, `trust-operators` pins the enrolled
roster outside SQLite. Use `uv run python -m app.cli <command> --help` for paths and
arguments. Never put a password or Airwallex key in command arguments. The full-app
launcher and intake/planning screens are still pending; these setup commands alone
do not make the app usable for payments.

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
- All companies, people, emails, balances and payment histories are **synthetic fixtures**.
- The callback record is **evidence of** a callback; the system cannot prove a phone call happened.
- **No real sanctions screening** is performed. The screening call checks a tiny synthetic list.
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

`docs/spec/FINAL.md` is the locked v1.0 specification and the only authority for behaviour. Where
anything in this repository disagrees with it, the spec wins and the disagreement belongs in
`docs/DECISIONS.md`.

## Demo mode (simulated)

The branch `demo/video` carries a labelled demo mode used for the pitch recording. Run it with
`make demo-video` (or `DEMO_MODE=video uv run python -m app.demo.server --port 8765`). The server
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
`MockAirwallexClient` (`app/demo/mock_airwallex.py`) that returns documented-shape responses from
a script and never opens a socket. The UI pages are demo-only HTML, not the product UI; the
executor, poller and passkey flows are not exercised. A persistent on-screen badge reads
`SIMULATED DEMO DATA · Airwallex sandbox calls mocked`, and synthetic items carry
`synthetic email`, `FIXTURE`, `mocked API response` or `demo timing` tags. The demo recording under
`demo/` is generated from this branch and no live Airwallex call, customer, revenue figure or
metric claim appears in it; the only statistics shown are the sourced ones footnoted on screen.

## License

Apache-2.0.
