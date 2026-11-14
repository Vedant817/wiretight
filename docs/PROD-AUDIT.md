# Production audit — 2026-11-14

Baseline: `e9edb77`, branch `demo/video`. This is a source audit, not live acceptance.
The only runnable UI is the pitch demo. There is no runnable product server or executor.

| Location at baseline | Finding | Required treatment |
|---|---|---|
| app/demo/mock_airwallex.py:1,117 | All provider responses are scripted, including balances and transfers. | Exclude package from product imports; use real HTTP client. |
| app/demo/seed.py:24,30,286,449,691 | Fixed date, invented company/people/banks/emails and historical records. | Never seed a product database. Keep historical recording reproducibility separate. |
| app/demo/seed.py:460,473,481,500,527,674 | Scripted transfer transitions, cooling display and in-memory audit demonstration. | Real durable executor, polling, signed approvals and journal required. |
| app/demo/page.py:374,381 | Static demo pages and synthetic shadow report. | A product UI must render persisted user/provider data. |
| app/demo/server.py:38,68,85 | DEMO_MODE=video serves generated payload, no provider sockets. | No product route may mount or import it. |
| app/config.py:130,158,162,209 | Replay default, demo timing fields, demo RP name. | Product entry point must explicitly reject replay/demo settings. |
| app/config.py:164,171,219 | HMAC fallback and shadow feature flags exist without operator flows. | Do not represent these as implemented authentication. |
| app/core/policy.py:68; app/core/policy_floor.py:119,211,297 | Demo policy vocabulary and documented two-minute override. | Runtime cooling must be at least 72 hours. Core oob currently uses real 72 hours. |
| app/integrations/__init__.py:1 | No provider client. | Build one typed sandbox client. |
| app/api/__init__.py:1 | No product API, UI, sessions, passkeys, readiness or webhooks. | Implement and test before exposing money actions. |
| app/workers/__init__.py:1; Makefile:169,174 | Serve/worker targets reference missing implementations. | Build execution/recovery with real provider reads. |
| app/cli.py:1 | Only audit verification exists. Setup, roster, policy signing and operational commands absent. | Build real commands and remove misleading setup promises. |
| app/core/vendors.py:1; app/core/dupes.py:1; app/core/oob.py:1 | Tested libraries are not connected to a product workflow. | Integrate, preserving refusal semantics. |
| app/core/schema.sql:1; app/core/db.py:326 | Schema exists; only initial version supported. | Subsequent changes need explicit migrations preserving existing databases. |
| README.md:40 | Synthetic screening is disclosed but there is no real screening integration. | Never claim sanctions clearance. |
| docs/spec/FINAL.md:938 | Rail cutoffs and settlement return windows are assumptions. | Label assumptions; never infer final settlement from a simulated status. |
| app/core/singlewriter.py:156 | Age-based stale-file reclamation can evict a still-live executor. | Do not use age alone as authority to take over a money writer. |
| app/core/policy.py:109,176 | Public `wiretight-ci-key-seed` derives signatures accepted by the historical loader. | New runtime policy loader requires two WebAuthn-signed records; historical helper relocation remains pending. |
| app/core/killswitch.py:87,311 | Historical clear verifier accepts signatures derived from a public test seed. | Runtime halt-clear routes use two fresh WebAuthn records, never that verifier. Move legacy signer/verifier fixtures out of app/. |
| app/core/oob.py:105 | Historical callback verifier uses raw Ed25519 test signatures while returning a UI-passkey label. | Runtime callbacks use actual WebAuthn ceremonies and signed-record verification; retain no test signer in the product path. |

No other executable TODO/NotImplemented stub was found in app/. `app/money.py:322`
returns Python's `NotImplemented` for unsupported comparison operands; that is protocol
behaviour, not a missing implementation. Sandbox host pinning, policy limits, currency
exponents and state enums are safety constraints, not fake customer data.

`demo/` media will remain untouched. Historical `app/demo` source is isolated from new
product entry points; it remains an explicitly simulated recording tool, not a product fallback.
No credentials in local `.env` were present at audit time. Environment credentials must
be checked by presence only, without displaying values.

## Supervisor follow-up scan — 14 November 2026

Read-only scan of `app/` Python sources used
`rg -n -i 'demo|dummy|mock|hardcoded|stale|notimplemented|todo|test_key_seed' app --glob '*.py'`.
The historical recording package is still present and remains excluded from product
entry-point imports; its relocation is **not complete**. Media in `demo/` is untouched.

| Current location | Finding / disposition |
|---|---|
| app/core/operators.py:94 | Nonexistent-account password hash exists to equalize password verification cost. Renamed to unmatched_password_hash; this is a timing defense, not a default login or fake operator. |
| app/core/policy.py:111; app/core/killswitch.py:87 | Public historical HMAC test seeds remain in legacy modules. New runtime signing paths do not accept them, but relocation out of app/ remains OPEN. |
| app/core/runtime_policy.py:27,31 | Rejects demo configuration; an inert false compatibility marker is still passed to the historical floor validator. Removal of that legacy vocabulary remains OPEN. |
| app/workers/service.py:135; app/api/main.py:129 | Demo-environment references are refusal guards, not feature flags enabling a simulation. |
| app/workers/executor.py:266; app/api/intake.py:344 | Staleness guards and an observation TTL are safety checks, not cached fake customer data. |
| app/workers/executor.py:627 | Real GET polling added. No canned provider state is returned. Polling now continues after operator revocation without authorizing new money. |
| app/core/reconciliation.py:71,100 | Actual opening cash/history and financial postings added. Full worker integration and settlement finalization remain OPEN; no zero opening balance is manufactured. |

The scan does not establish completion of cleanup. Legacy signer/demo source is
still listed above rather than being represented as removed. FX execution/expiry,
actual financial-worker process-crash proof, settlement and the rest of the supervisor
scenario matrix remain unfinished until separately implemented and run.
