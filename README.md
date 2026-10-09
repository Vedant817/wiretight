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

## License

Apache-2.0.