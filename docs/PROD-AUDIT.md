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

No other executable TODO/NotImplemented stub was found in app/. `app/money.py:322`
returns Python's `NotImplemented` for unsupported comparison operands; that is protocol
behaviour, not a missing implementation. Sandbox host pinning, policy limits, currency
exponents and state enums are safety constraints, not fake customer data.

`demo/` media will remain untouched. Historical `app/demo` source is isolated from new
product entry points; it remains an explicitly simulated recording tool, not a product fallback.
No credentials in local `.env` were present at audit time. Environment credentials must
be checked by presence only, without displaying values.
