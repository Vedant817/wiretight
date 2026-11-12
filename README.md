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