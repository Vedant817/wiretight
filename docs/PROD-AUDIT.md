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

## Complete supervisor source-match register

Command: `rg -n -i 'demo|dummy|mock|fake|sample|hardcoded|seed' app/`.
Every match from this scan is indexed below. A retained justification is not a claim
that historical code was deleted or that the whole application is production-ready.

| Matched file:line locations | Disposition and justification |
|---|---|
| `app/api/main.py:1`, `app/api/main.py:143`, `app/api/main.py:147` | Documentation or explicit refusal of recording environment flags. These references cannot enable synthetic provider responses. |
| `app/workers/service.py:135`, `app/workers/service.py:136` | Documentation or explicit refusal of recording environment flags. These references cannot enable synthetic provider responses. |
| `app/core/installation.py:1` | Documentation explicitly distinguishing real controls from historical recording captions or fixtures; executable decisions use actual inputs. No runtime sample data is introduced. |
| `app/core/calendars.py:1` | Documentation explicitly distinguishing real controls from historical recording captions or fixtures; executable decisions use actual inputs. No runtime sample data is introduced. |
| `app/core/killswitch.py:87`, `app/core/killswitch.py:91` | Legacy clear-signature compatibility API, retained for existing tests. Product halt clearing uses runtime_halt and two real passkey signatures; no runtime route calls this legacy clear verifier. |
| `app/core/audit.py:36` | Cryptographic genesis-hash sentinel and its comment; not a customer, account, transaction or provider response. |
| `app/core/migration_003.sql:1` | Documentation explicitly distinguishing real controls from historical recording captions or fixtures; executable decisions use actual inputs. No runtime sample data is introduced. |
| `app/demo/mock_airwallex.py:1`, `app/demo/mock_airwallex.py:4`, `app/demo/mock_airwallex.py:16`, `app/demo/mock_airwallex.py:17`, `app/demo/mock_airwallex.py:25`, `app/demo/mock_airwallex.py:29`, `app/demo/mock_airwallex.py:38`, `app/demo/mock_airwallex.py:58`, `app/demo/mock_airwallex.py:73`, `app/demo/mock_airwallex.py:82`, `app/demo/mock_airwallex.py:90`, `app/demo/mock_airwallex.py:105`, `app/demo/mock_airwallex.py:113`, `app/demo/mock_airwallex.py:119`, `app/demo/mock_airwallex.py:120`, `app/demo/mock_airwallex.py:121` | Retained historical recording harness, isolated from product imports; it requires explicit recording mode and refuses Airwallex credentials. This is archival source, never a product fallback. |
| `app/core/policy_floor.py:119`, `app/core/policy_floor.py:186`, `app/core/policy_floor.py:211`, `app/core/policy_floor.py:218`, `app/core/policy_floor.py:264`, `app/core/policy_floor.py:297`, `app/core/policy_floor.py:409`, `app/core/policy_floor.py:696` | Legacy floor vocabulary/refusal adapter. Runtime rejects demo policy keys, supplies an inert false marker only to the shared validator, requires human approval and never shortens the 72-hour floor. |
| `app/core/oob.py:24`, `app/core/oob.py:46`, `app/core/oob.py:473` | Documentation explicitly distinguishing real controls from historical recording captions or fixtures; executable decisions use actual inputs. No runtime sample data is introduced. |
| `app/core/policy.py:68`, `app/core/policy.py:69`, `app/core/policy.py:104`, `app/core/policy.py:111`, `app/core/policy.py:114`, `app/core/policy.py:115`, `app/core/policy.py:116`, `app/core/policy.py:123`, `app/core/policy.py:135`, `app/core/policy.py:149`, `app/core/policy.py:164`, `app/core/policy.py:176`, `app/core/policy.py:177`, `app/core/policy.py:182`, `app/core/policy.py:266` | Legacy policy-loader/test-signature compatibility API. Product entry points use runtime_policy and real passkeys; these public-seed helpers are not accepted as money authority. Full relocation remains an outstanding cleanup, not a production signing option. |
| `app/core/runtime_policy.py:27`, `app/core/runtime_policy.py:28`, `app/core/runtime_policy.py:31` | Legacy floor vocabulary/refusal adapter. Runtime rejects demo policy keys, supplies an inert false marker only to the shared validator, requires human approval and never shortens the 72-hour floor. |
| `app/core/parsers.py:536` | Documentation explicitly distinguishing real controls from historical recording captions or fixtures; executable decisions use actual inputs. No runtime sample data is introduced. |
| `app/demo/page.py:1`, `app/demo/page.py:5`, `app/demo/page.py:47`, `app/demo/page.py:121`, `app/demo/page.py:243`, `app/demo/page.py:281`, `app/demo/page.py:318`, `app/demo/page.py:429` | Retained historical recording harness, isolated from product imports; it requires explicit recording mode and refuses Airwallex credentials. This is archival source, never a product fallback. |
| `app/core/singlewriter.py:192` | Substring in the word demoted/documentation. Money execution uses the kernel process lock, not a simulated worker. |
| `app/demo/server.py:1`, `app/demo/server.py:3`, `app/demo/server.py:6`, `app/demo/server.py:19`, `app/demo/server.py:20`, `app/demo/server.py:26`, `app/demo/server.py:38`, `app/demo/server.py:52`, `app/demo/server.py:53`, `app/demo/server.py:60`, `app/demo/server.py:61`, `app/demo/server.py:67`, `app/demo/server.py:68`, `app/demo/server.py:70`, `app/demo/server.py:71`, `app/demo/server.py:79`, `app/demo/server.py:80`, `app/demo/server.py:85`, `app/demo/server.py:86`, `app/demo/server.py:87`, `app/demo/server.py:89`, `app/demo/server.py:91`, `app/demo/server.py:92` | Retained historical recording harness, isolated from product imports; it requires explicit recording mode and refuses Airwallex credentials. This is archival source, never a product fallback. |
| `app/demo/seed.py:1`, `app/demo/seed.py:6`, `app/demo/seed.py:7`, `app/demo/seed.py:8`, `app/demo/seed.py:9`, `app/demo/seed.py:20`, `app/demo/seed.py:23`, `app/demo/seed.py:24`, `app/demo/seed.py:205`, `app/demo/seed.py:392`, `app/demo/seed.py:473`, `app/demo/seed.py:475`, `app/demo/seed.py:478`, `app/demo/seed.py:481`, `app/demo/seed.py:495`, `app/demo/seed.py:500`, `app/demo/seed.py:505`, `app/demo/seed.py:527`, `app/demo/seed.py:536`, `app/demo/seed.py:537`, `app/demo/seed.py:538`, `app/demo/seed.py:557`, `app/demo/seed.py:565`, `app/demo/seed.py:674`, `app/demo/seed.py:676`, `app/demo/seed.py:684`, `app/demo/seed.py:689`, `app/demo/seed.py:690`, `app/demo/seed.py:691`, `app/demo/seed.py:692`, `app/demo/seed.py:703`, `app/demo/seed.py:704`, `app/demo/seed.py:713` | Retained historical recording harness, isolated from product imports; it requires explicit recording mode and refuses Airwallex credentials. This is archival source, never a product fallback. |
| `app/demo/__init__.py:1`, `app/demo/__init__.py:4`, `app/demo/__init__.py:7` | Retained historical recording harness, isolated from product imports; it requires explicit recording mode and refuses Airwallex credentials. This is archival source, never a product fallback. |
| `app/core/statemachine.py:5`, `app/core/statemachine.py:155` | Documentation explicitly distinguishing real controls from historical recording captions or fixtures; executable decisions use actual inputs. No runtime sample data is introduced. |

No product entry point imports the historical recording package or test transport.
The fixed unmatched-account password hash is a timing defense, not a usable default
login; earlier dummy naming was removed. Legacy public-seed helper relocation remains
explicitly open, although runtime policy/callback/payment/FX/halt decisions reject
those helpers. No media under demo/ was edited.

## Current audit checklist

- [x] Every result of `rg -n -i 'demo|dummy|mock|fake|sample|hardcoded|seed' app/`
  has a file:line entry and explicit disposition in the register above.
- [x] Product isolation checked with `uv run python -m tests.support.audit_runtime_imports`:
  50 product modules passed, without recording/test imports, mock transport or legacy authority calls.
- [x] Removed the diagnostic page's false static empty-data claim and stale
  read-only-worker implementation claims.
- [ ] Historical recording source relocation out of app/: retained and justified
  above for recording reproducibility, never an enabled product fallback.
- [ ] Legacy public-seed helper relocation: retained compatibility code, rejected
  as runtime authority, not claimed deleted. Broader cleanup remains open.
- [ ] Live protocol acceptance: no sandbox keys; live tests explicitly skip.

The current supervisor requirement permits removal **or justification** of each
match. That audit is complete; remaining relocation is still listed rather than
being misrepresented as completed production cleanup. No root demo/ file changed.


## 2026-11-14: legacy authority physically removed from the product tree

The older retained-code dispositions below are superseded by these moves:

- `app/demo/{__init__,mock_airwallex,page,seed,server}.py` ->
  `tests/support/recording/`. Root `demo/` media and scripts remain untouched.
- HMAC policy loader/signers -> `tests/support/legacy_policy.py`.
  `app/core/policy.py` contains shared value types and safe YAML parsing only.
- HMAC halt clear/signers -> `tests/support/legacy_killswitch.py`; it imports
  the real production trip/read controls for historical tests.
- Raw Ed25519 callback fixtures -> `tests/support/legacy_oob.py`.
  Product callback verification uses registered WebAuthn credentials.
- Obsolete PID lock -> `tests/support/legacy_singlewriter.py`.
- Obsolete demonstration timing shape/override labels were removed from the
  real safety floor; runtime policy accepts no shortened cooling window.

Proof: `uv run python -m tests.support.audit_runtime_imports` scans every Python
module under `app/` (no archive exclusions), rejects test/script/recording
imports, then imports the web, worker, executor and CLI in four fresh Python
interpreters with an import finder that raises on archived dependencies. It
also asserts the legacy signer attributes are absent from the shared modules.
`tests/unit/test_runtime_boundary.py` runs that same check in the full suite.
Observed output: `PASS: 49 product modules scanned; 4 isolated entry imports; archive imports and legacy signers forbidden`.
Targeted legacy/control regression command:
`uv run pytest tests/acceptance/test_b_policy_floor.py tests/acceptance/test_b_killswitch.py tests/unit/test_oob.py tests/unit/test_singlewriter.py tests/unit/test_real_decisions.py -q --timeout=180`
Observed final line: `289 passed in 104.74s (0:01:44)`.
