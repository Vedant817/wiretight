# Round 2 · Staff Engineer: architecture and 3-week scope review of SPEC-v1 (Countersign)
**Written:** Thu 8 Oct 2026, ~7:35 PM IST.
**Inputs:**
- `board/SPEC-v1.md`, read in full, with §8, §9, §12 and §16 in depth
- `board/DECISIONS.md` (D3, F7)
- `raw/doc_*.txt`
- live Airwallex docs, re-fetched today
- the hackathon pages, re-fetched today

**Sandbox:** there are still no credentials on the box (env vars and repo files checked), so every day-1 test below is **UNTESTED**.

**Greenfield.** No reference to past projects. Nothing registered, submitted or sent, and no agents messaged.

---

## 1. Right-sizing verdict
**The core is the right size. The edges are over-scoped by roughly 30–40%. The gaps are few but real.**

The core shape fits one person:
- one FastAPI app plus one executor loop
- SQLite
- HTMX with no JS build
- a deterministic planner
- typed LLM tools

There are no queues, no microservices, no multi-tenancy, and no cloud infrastructure beyond a cloudflared tunnel. Keep all of that. What's too big is the feature surface around the core: six optional integrations, a 50-scenario eval, journal-grade FX accounting, and a pre-work plan that writes project code before the build window.

### Over-engineering (cut or simplify)
| Item | SPEC § | Call |
|---|---|---|
| Metal L2 anchor of the audit-chain head | §8, §9, §11, §15 | **Cut.** It needs Metal tooling we aren't targeting, it costs a day, and the hash chain alone carries the story |
| Slack interactive approvals | §6.3 | **Cut.** A second approval surface doubles the binding tests |
| Airwallex native approval workflow (`payout.transfer.in_approval`) | §6.3, §14 | **Cut from the build** and keep only as an adoption sentence. The sandbox can't drive it: "Transfer statuses that are only applicable to the transfers created and submitted for approval are not currently supported" (`raw/doc_failure_types.txt`) |
| "Postgres-ready", Alembic migrations | §8, §9 | **SQLite only**, `create_all` plus a seed script. Migrations are wasted effort on a 3-week, single-database app |
| Separate executor *process* | §9 | **Keep it logically separate, not as infrastructure.** One `executor` module, run as a CLI loop or a background task over SQLite (WAL mode). It is the only module that loads the Airwallex key. No queue or broker |
| CSV import of Xero/QBO/Zoho bills | §4.1, §14 | **Cut.** Keep `.eml` and PDF fixtures only |
| `financial_reports` cross-check | §5, §12 | **Cut** |
| 50-scenario eval harness, 15–40 obligations each, 10 metrics | §13 | **Trim** to 20 seeded scenarios on a fake client and the 5 metrics that back the claims: double-pays, floor breaches, unverified bank-change payments, duplicate recall/precision, recon residual |
| Realised FX gain/loss at the *invoice-date* booking rate | §4.8 | **Stretch.** We have no historical-rate endpoint in our API list. If kept, use the rate captured at ingest via `GET /fx/rates/current` and label it that way |
| Earned-autonomy rule (≥2 FINAL payments, fingerprint unchanged ≥30 days) | §6.1 | **Keep** the rule, but seed the history as fixtures. It can't be earned live in a demo |
| "Undone before SENT via cancellation where supported" for T0 | §6.1 | **Drop the claim.** It's unverified, and the simulator only moves forward |
| Auth, users, multi-tenancy | §8 (`approver_id`), §14 | **No auth system.** Use an identity switcher (Requester / Approver A / Approver B) stored per session. Segregation of duties is enforced on those ids. Multi-entity is roadmap only |

### Gaps (must close)
1. **Approval binding collides with per-currency netting (§4.3, §6.2).** The packet binds `fx.quote_id` to each payee item. But one SINGLE_USE quote covers *all* items in that currency (`usage: SINGLE_USE` in `raw/doc_fxquote.txt`). Rejecting or deferring one item resizes the conversion, which needs a new quote and so voids every other packet in that currency. **Fix:** use two packet types.
   - **CONVERSION packet:** pair, sell/buy amount, `quote_id`, `client_rate`, `valid_to_at`, the obligation ids it funds.
   - **PAYMENT packet:** payee, beneficiary version, fingerprint, method, currency, amount, fee, reference, evidence hashes.

   Payments pay from the currency balance and don't carry the quote. If the net changes, only the CONVERSION packet is voided.
2. **Idempotency covers only transfers (§4.5, §7 S6).** Extend AMBIGUOUS handling to:
   - **conversions:** `GET /api/v1/fx/conversions?request_id=` exists (params `request_id`, `status`, `from_created_at` per https://www.airwallex.com/docs/api/transactional_fx/conversion/list.md)
   - **beneficiary creation:** look up by our fingerprint stored in `nickname` (or by a stored id) via `GET /api/v1/beneficiaries` before re-creating

   Note that `GET /api/v1/transfers` does take `request_id` (`raw/doc_list_transfers.txt`), so the transfer pre-check in the spec is valid.
3. **The failure playbook has no default, and a late read loses `failure_type` (§4.7, §8).** The simulator supports 32 failure types (`raw/doc_failure_types.txt`). The spec maps 18 and omits, for example, `BENEFICIARY_BANK_RETURNED`, `BENEFICIARY_REQUESTED`, `ACCOUNT_CURRENCY_MISMATCH`, `EXCEEDED_TRANSACTION_AMOUNT_OR_LIMIT`, `INVALID_BANK_INFORMATION`, `INVALID_CORRESPONDENT_BANK_INFORMATION`, `INVALID_SPECIAL_CHARACTER`, `UNABLE_TO_APPLY` and `OTHER`. **Fix:** add a default of ESCALATE with no auto-retry. Also, "Failed transfers will be automatically cancelled in seconds" (transfer-statuses page), so record `failure_type` from the webhook or an immediate poll, and model `FAILED → CANCELLED` explicitly. **There is no RETURNED status.** A bank return is `FAILED` with `failure_type: BENEFICIARY_BANK_RETURNED`.
4. **The prompt-injection boundary has one hole (§4.1, §6.4).** If the LLM decides *which vendor* an invoice belongs to, a crafted email can attach itself to a trusted payee's history. **Fix:**
   - Resolve the vendor in code: sender domain or vendor-master id, plus a normalized vendor name with an exact-match table.
   - The LLM fills only the `InvoiceDraft` schema.
   - `explain_flags` and `propose_plan_note` output is display text, never parsed back into decisions.
   - Bank details in an email can only *raise* a flag (fingerprint diff, leading to quarantine). They never become a payee without T2 plus a callback.
5. **The executor must re-check HARD BLOCKs against live state at execution time (§4.5, §6.2).** That means the reserve floor against a fresh `GET /balances/current`, the duplicate lock, and whether the original is terminal. Re-hashing the packet alone won't catch a balance drop between approval and execution.
6. **No demo-reset strategy (§10, §11).** Sandbox state accumulates: balances, beneficiaries, transfers. **Fix:** snapshot the opening balances at run start, compute tie-out from that snapshot (not from zero), use run-scoped references, and make `scripts/run_demo.py` idempotent. A clean "New Business Sandbox" entity is an option, but creating one is Vedant's action.

Already covered well, no change needed: ledger and recon tables, the transfer state machine with PAID treated as provisional, webhook dedupe on event id, the hash-chained audit log, 429 and token-expiry handling, segregation of duties, and masking of account numbers to the model.

---

## 2. Minimum demo-complete scope, and the cut list
**Must ship. If any of these is missing, the demo doesn't stand:**
1. **Fixtures:** 7 synthetic bills (PDF + `.eml`), a vendor master with fingerprints, seeded payee history for one T0 payee.
2. **Ingest:** LLM to `InvoiceDraft` (JSON schema), plus validators (IBAN checksum, ABA and sort-code format, currency, totals vs line items).
3. **Verify:** exact plus one fuzzy duplicate rule, bank-fingerprint diff leading to QUARANTINE, vendor resolved in code.
4. **Plan:** reserve floor, one conversion per currency, SWIFT fee included, LOCAL preferred, DEFER, re-plan diff on a new balance.
5. **Countersign:**
   - T0, T1 and T2 tiers, with CONVERSION and PAYMENT packets.
   - Void on change, segregation of duties via the identity switcher.
   - T2 requires an out-of-band callback record.
6. **Execute:** quote, conversion, transfers with deterministic `request_id`. AMBIGUOUS lookups for transfers and conversions.
7. **Track:** polling first (webhooks only if day-1 shows them firing). PAID shown as PROVISIONAL with a short demo settle window.
8. **Recover:** SENT → FAILED `BENEFICIARY_NAME_MISMATCH`, then incident, drafted message, new beneficiary version, T2, one linked replacement. A second replacement is blocked.
9. **Reconcile:**
   - Per-currency tie-out from the opening snapshot via `GET /financial_transactions`, with a fallback to transfer and conversion objects plus balance deltas.
   - Simple journal CSV (payments, conversions, fees).
10. **Audit and ship:** hash-chained audit log; README with seed and demo scripts; a sub-5-minute video.

| Item | Call |
|---|---|
| Metal anchor, Slack approvals, Airwallex native approvals | **Cut** |
| CSV bill import, financial-report cross-check, Postgres and Alembic | **Cut** |
| `verify_account` (SEPA VoP) | **Stub**: behind a flag, shown only if day-1 returns something usable (F7) |
| Webhook receiver | **Stub, then promote**: build HMAC and dedupe only if the day-1 test shows deliveries. Polling is the real path |
| PAID → FAILED late failure (S8) | **Stub/conditional**: live only if day-1 shows the simulator allows it; otherwise unit test plus a recorded fixture |
| FX void demo via a "rate moved" requote | **Change**: drive the void with an **expired MIN_1 quote** or an amount edit. Sandbox rates may not move during a 4-minute take |
| Realised FX gain/loss at booking rate | **Stretch** (label it "rate at ingest" if done) |
| Early-pay discount lever | **Stretch** |
| Eval harness | **Trim** to 20 scenarios and 5 metrics |
| Supplier messages | **Stub**: drafted in the UI, never sent |

---

## 3. Is the §12 plan realistic? Where exactly it breaks
1. **Pre-work, Oct 16–24, builds project code before the build window.** It creates the public repo, the synthetic data generator, the policy schema, DB models and migrations. That conflicts with the ruling in §4. It also says "Optionally email devhelp@ as insurance for platform access", which is off-board contact and unnecessary: S2 uses no platform features (§5, "Zero access risk"). **Remove it.**
2. **Week 1 is overloaded with 9 components in 7 days:** Airwallex client, ledger, state machines, audit chain, PDF/email ingest, LLM extraction, duplicate detector, fingerprint diff, planner. Ingest plus LLM is a sinkhole on its own (PDF text quirks, schema retries, validators). **It breaks around Thu 29 Oct.** The exit check is "CLI dry-run plan", which doesn't even touch the sandbox. So the riskiest part, live money movement, isn't proven until week 2.
3. **Week 2's exit check ("full demo end to end", Sat 7 Nov) carries everything else:** UI, packets, executor, webhooks, incident commander, re-plan. A slip anywhere in week 1 or 2 lands here with no buffer.
4. **The "never cut" reconciliation tie-out is scheduled last** (week 3, Sun 8 – Tue 10 Nov), next to a 50-scenario eval and a Nov 11 freeze. **This is the single biggest scheduling error:** a never-cut item in the slot most likely to be squeezed.
5. **The §16 fallback is unworkable.** "Fall back to Runner-up C if Countersign isn't end-to-end by Nov 7" leaves 6 days to build a different product. The fallback has to be **descoping Countersign**, decided earlier.
6. **Small issues:**
   - `settle_window_hours: 48` can't play out in a demo (use a demo override, e.g. 2 minutes).
   - The application text (§15) says spikes "are done before the build phase". That's fine *only* if they really happened and were throwaway (see §4).

---

## 4. Ruling: pre-build-phase spikes
**What the rules actually say (re-fetched 8 Oct 2026):**
- Landing page, Key dates: "Oct 25 · Accepted teams are notified. Official hackathon build period begins." and "Nov 13 · Project submissions due." (https://airwallex.hackerearth.com/)
- HackerEarth challenge page phases: "Registration & Idea Phase Oct 5 – Oct 23, 2026" and "Build Phase Oct 25 – Nov 13, 2026" (https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/; snapshot `raw/he.html`)
- HackerEarth generic FAQ on the same page: "You have to develop the application on your local system and submit it on HackerEarth in tar/zip file format along with instructions to run the application and source code." and "all code needs to be in public domain (open source) so that it can be evaluated by the judges."
- Landing copy: "Over 48 hours, teams build on Airwallex APIs" next to "3 WEEKS To design, build, ship". The two contradict each other; the dated schedule wins (DECISIONS standing constraints).
- The builder guide tells anyone to "Sign up at sandbox.airwallex.com"; the sandbox isn't gated on acceptance (https://airwallexdev.com/guide).

**What the rules do not say, and the likely hidden clause:**
- On the pages I can read, there is no clause requiring code to be "developed entirely during the hackathon" and no ban on prior work.
- However, "Your hack must be developed entirely during the Hackathon duration" is **HackerEarth's standard "HackerEarth rules" boilerplate**. It appears word for word on two other HackerEarth events:
  - TinyFish 2026: https://www.hackerearth.com/challenges/hackathon/the-tiny-fish-hackathon-2026/rules/
  - Global MCP Hackathon, under its "HackerEarth rules" section: https://www.hackerearth.com/challenges/hackathon/mcp-hackathon/custom-tab/official-rules/
- This event's rules tab may sit behind login (DECISIONS OPEN-1). **Assume the clause applies** until Vedant confirms otherwise. "Hackathon duration" here plausibly means the Build Phase (25 Oct – 13 Nov), though the event also has an idea phase from 5 Oct. That ambiguity is real, and it's why project code waits.

**Ruling (default stance confirmed):**
- **Throwaway spikes are OK** in a separate scratch folder outside the project repo (for example `~/scratch/countersign-spikes/`), never pushed to the submission repo.
- **No project-repo commits before Sun 25 Oct, 10:00 AM IST.** This includes no public repo, README, LICENSE, models, migrations or generator. Create the repo at 10:00 AM IST on 25 Oct so the commit history starts inside the build phase.
- **Notes and findings carry over** (markdown: endpoint quirks, error codes, payload shapes, timings). **Spike code does not get copied in.** Contract tests are rewritten in the repo from the notes.
- **Allowed before 25 Oct:** design docs, ADR text, demo script, fixture *specifications* (a table of the 7 bills and traps), policy *values*, the idea-phase application.
- **Who does what:** creating the sandbox account is a sign-up, so it's Vedant's action. Submitting the application by Oct 21 (buffer before **Fri 23 Oct, 11:59 PM IST**) is also his call. No devhelp email, and no Discord or partner-Slack questions without his say-so.
- **If OPEN-1 confirms the boilerplate clause** (likely), the ruling still holds: throwaway spikes aren't part of the hack, and no spike code enters the repo. To be safe, soften the §15 sentence to "API behaviour was explored before the build phase; all project code was written during it".

---

## 5. Day-1 sandbox tests (all UNTESTED: no credentials)
Run these in the build-phase repo as contract tests rewritten from spike notes. If Vedant creates the account earlier, run them as throwaway spikes per §4. Base: `https://api.sandbox.airwallex.com/api/v1`.

| # | Question | Exact call(s) | Expected (per docs) | Fallback if it fails |
|---|---|---|---|---|
| T1 | Auth and token life | `POST /authentication/login` (headers `x-client-id`, `x-api-key`, no body) | 200 + bearer token, about 30 minutes | Fix key scopes; nothing works without it |
| T2 | Funding | `GET /global_accounts`, `POST /simulation/deposit/create` `{global_account_id, amount, payer_name, reference}`, then `GET /balances/current` | 201 `status: PENDING`, balance up immediately (guide) | Create a USD LOCAL Global Account (`POST /global_accounts/create`) and retry |
| T3 | **Can a transfer go PAID → FAILED / "returned"?** | `POST /transfers/create`, then `POST /simulation/transfers/{id}/transition` with `next_status` SENT → PAID → `FAILED` + `failure_type: BENEFICIARY_BANK_RETURNED` | Docs state machine: "SENT→(PAID,FAILED); PAID→(FAILED,end); FAILED→CANCELLED". The simulator allows only "the next valid status". `PAID` needs API version ≥ 2024-04-30. **There is no RETURNED status**; a return is FAILED + `BENEFICIARY_BANK_RETURNED` | If PAID → FAILED is rejected: demo SENT → FAILED live, cover S8 with a unit test plus a recorded fixture |
| T4 | Is `failure_type` still readable after auto-cancel? | `GET /transfers/{id}` immediately and 10 s after the FAILED transition | Docs: "Failed transfers will be automatically cancelled in seconds". Expect CANCELLED with `failure_type`/`failure_reason` retained | Capture from the `payout.transfer.failed` webhook or a sub-second poll right after the transition |
| T5 | VoP / `verify_account`, SEPA EUR | `POST /beneficiaries/verify_account` `{entity_type: "COMPANY", transfer_method: "LOCAL", bank_details: {iban: "DE…", account_name: "…", bank_country_code: "DE"}}` | One of `VERIFIED` (+ `FULL_MATCH`/`PARTIAL_MATCH`/`NOT_MATCHED`), `CANNOT_VERIFY`, `EXTERNAL_SERVICE_UNAVAILABLE`. No documented sandbox test values (F7) | Flag off; fingerprint diff + `beneficiaries/validate` + out-of-band callback is the control |
| T6 | `beneficiaries/validate` per corridor | `POST /beneficiaries/validate` `{"beneficiary": {...}, "transfer_methods": ["LOCAL"]}` for US/ABA and GB/sort code; `["SWIFT"]` for DE/IBAN+BIC; plus one bad IBAN | 200 OK for valid input. Bad routing → code `010`/`011`/`016`; bad IBAN fails at create with `083` (guide) | Our own checksum validators plus the MCP `create_beneficiary` `dry_run: true` |
| T7 | Schema endpoint name | `POST /beneficiaries/schema` (guide) vs `POST /beneficiary_api_schemas/generate` (API reference) | One of them returns corridor fields | Hard-code the 3 corridors' field sets from the guide |
| T8 | Do webhooks fire (transfers and deposits)? | Subscribe in the sandbox web app (Settings → Developer → Webhooks) to `payout.transfer.*` and `deposit.*`; cloudflared tunnel; repeat T2 and T3 | Deliveries with `x-timestamp` and `x-signature`; HMAC-SHA256 over timestamp + raw body; may arrive twice or out of order (dev lab). Deposit events for simulations are a documented test case (F7) | Polling: `GET /transfers/{id}`, `GET /balances/current`, `GET /global_accounts/{id}/transactions` |
| T9 | FX quote window and lock | `POST /fx/quotes/create` with `validity: MIN_1` and `HR_4`; `GET /fx/quotes/{quote_id}`; `POST /fx/conversions/create` with `quote_id` (a) within validity, (b) after MIN_1 expiry, (c) a second time with the same quote | Response has `usage: SINGLE_USE`, `valid_to_at`, `client_rate` (`raw/doc_fxquote.txt`). Expect (a) SETTLED immediately, (b) error, (c) error. Validity enum: MIN_1, MIN_15, MIN_30, HR_1, HR_4, HR_8, HR_24 | If (b)/(c) don't error: enforce single use and expiry in code before booking. Also measure rate drift between two quotes 2 minutes apart; if flat, drive the void beat by expiry |
| T10 | Transfer idempotency replay | `POST /transfers/create` twice with the **same** `request_id` and body; once with the same `request_id` and a **different** body; then `GET /transfers?request_id=` | Guide: reuse for a different operation within 7 days → `duplicate_request_id`, not processed. Same-body replay behaviour (original object vs error) undocumented. `request_id` is 10–50 chars (code `018`) | Always look up by `request_id` before any retry (already §4.5); treat any non-2xx as AMBIGUOUS |
| T11 | Conversion idempotency replay | `POST /fx/conversions/create` twice with the same `request_id`; `GET /fx/conversions?request_id=` | One conversion; the second call errors or returns the original | Pre-check via `GET /fx/conversions?request_id=` before any retry |
| T12 | `financial_transactions` latency and shape | After T2, T9(a), a SWIFT transfer and T3: poll `GET /financial_transactions?from_created_at=<run start>` every 5 s | Rows with `source_type` DEPOSIT / CONVERSION / PAYOUT (and FEE or a `fee` field), `transaction_type` incl. `CONVERSION_SELL/BUY`, `PAYOUT_FAILURE`/`PAYOUT_REVERSAL` after the failure. Record the lag per type | Reconcile from the deposit, conversion and transfer objects plus `GET /balances/history`; flag "provider rows pending" |
| T13 | SWIFT fee reality | EUR SWIFT transfer of 100; compare `GET /balances/current` before and after | EUR 12.85 flat deducted (guide) | Read the fee from the transfer or financial-transactions row; make `policy.yaml` fees config-driven |
| T14 | Duplicate lookback query | `GET /transfers?beneficiary_id=…&from_created_at=…` | Filters work (`raw/doc_list_transfers.txt`) | Rely on our ledger for duplicates; the API lookback is belt-and-braces |
| T15 | Balance history for tie-out | `GET /balances/history` with currency and time filters | Each movement listed with running balance | Tie out from the snapshot + financial transactions only |

---

## 6. Must-fix and should-fix (mapped to SPEC sections)

### Must-fix
| # | Fix | SPEC § |
|---|---|---|
| M1 | Pre-work: no repo, models, migrations or generator before 25 Oct 10:00 AM IST. Spikes go in a scratch folder; only notes carry over. Delete "email devhelp@" | §12 Pre-work, §15 last bullet |
| M2 | Split approvals into **CONVERSION** and **PAYMENT** packets, so netting changes void only the conversion | §6.2, §8 (`approval`, `plan_item`, add `packet_type`) |
| M3 | Extend AMBIGUOUS and idempotent lookups to conversions (`GET /fx/conversions?request_id=`) and beneficiary creation | §4.5, §7 S6, §8 (`conversion.request_id UNIQUE`) |
| M4 | Default playbook = ESCALATE for every unmapped `failure_type`. Capture `failure_type` before auto-cancel. Model `FAILED → CANCELLED` explicitly. No RETURNED status; a return is `BENEFICIARY_BANK_RETURNED` | §4.7, §7 S7–S9, §8 state machine |
| M5 | Executor re-checks HARD BLOCKs against live state (fresh balance vs floor, duplicate lock, original terminal) immediately before each call | §4.5, §6.1, §6.2 |
| M6 | Vendor resolved in code, never by the LLM. LLM output enters only via the `InvoiceDraft` schema. Explanations are display-only | §4.1, §6.4, §7 S13 |
| M7 | Re-sequence the plan: live money path in week 1 (no LLM), reconciliation tie-out in week 2, fallback = descoping, not switching products | §12, §16 row 1 |
| M8 | Cut Metal anchor, Slack, native approvals, CSV import, financial-report cross-check, and Postgres/Alembic from the build | §6.3, §8, §9, §11 (4:20 beat), §12 stretches |

### Should-fix
| # | Fix | SPEC § |
|---|---|---|
| S1 | Demo FX-void beat: use an expired MIN_1 quote or an amount edit, not "rate moved" | §11 (2:05 beat), §7 S5 |
| S2 | `settle_window` demo override (minutes); show PROVISIONAL → FINAL on screen | §4.6, §9 `policy.yaml` |
| S3 | Demo reset: opening-balance snapshot, run-scoped references, idempotent `run_demo.py` | §10, §17 `scripts/` |
| S4 | Identity switcher instead of auth; no multi-tenant code | §6.1, §8 |
| S5 | Eval: 20 scenarios, 5 metrics, fake client; drop the wall-clock and "approvals vs baseline" metrics unless time allows | §13 |
| S6 | FX gain/loss to stretch, or "rate at ingest" with a label | §4.8 |
| S7 | Drop the "undo T0 before SENT" claim; seed payee history for T0 | §6.1 |
| S8 | Resolve the schema endpoint name (T7) and record it in §5 | §5 |
| S9 | Webhook receiver only after T8 shows deliveries; polling is first-class | §4.6, §9, §16 |
| S10 | §15 application: keep the "spikes done" sentence only if true and throwaway; drop the Metal mention | §15 |
| S11 | Make PAID → FAILED (S8) conditional on T3 | §7 S8, §16 row 2 |

---

## 7. Revised week-by-week plan, with go/no-go checkpoints
**Pre-work (now → Sat 24 Oct, design only):**
- design docs, ADRs, demo script
- fixture spec table (7 bills and their traps)
- `policy.yaml` values
- application text (Vedant submits; target Wed 21 Oct, deadline Fri 23 Oct, 11:59 PM IST)
- if Vedant has created a sandbox account: throwaway spikes for T1–T15 in `~/scratch/`, findings in `spike-notes.md`

**Week 1 (Sun 25 – Sat 31 Oct): live money path, no LLM, no UI**
- **Sun 25 (from 10:00 AM IST):** create the repo; rewrite T1–T15 as contract tests from the notes; run them.
- **Mon 26 – Wed 28:**
  - `AirwallexClient` (token cache, rate limit, error-code map, request-id helper, AMBIGUOUS lookups)
  - `SandboxSimulator`
  - ledger, transfer and conversion state machines, audit hash chain
- **Thu 29 – Fri 30:** planner over *hand-typed* obligations (floor, netting, fees, LOCAL/SWIFT, defer, re-plan diff), plus a CLI executor.
- **✅ Checkpoint 1, Fri 30 Oct:** the CLI executes the demo money path *live*: deposit, quotes, 2 conversions, 4 transfers, one SENT → FAILED, one linked replacement under the lock, ledger correct.
  - **NO-GO action:** drop T0 auto-tier and the second currency conversion; carry the rest to week 2.

**Week 2 (Sun 1 – Sat 7 Nov): decisions, controls, reconciliation**
- **Sun 1 – Mon 2:** CONVERSION and PAYMENT packets, tiers, segregation of duties via the identity switcher, void-on-change, executor re-check of HARD BLOCKs.
- **Tue 3:**
  - duplicate detector (exact + one fuzzy rule)
  - fingerprint diff → QUARANTINE → T2 with a callback record
  - vendor resolution in code
- **Wed 4:** LLM ingest of the 7 fixtures into `InvoiceDraft`, validators, injection fixture.
- **Thu 5:** reconciliation tie-out per currency (financial transactions, with the object fallback) and a simple journal CSV.
- **Fri 6 – Sat 7:** HTMX countersign queue and run screens; deposit re-plan via polling; webhooks only if T8 passed.
- **✅ Checkpoint 2, Thu 5 Nov:** the full demo runs **headless** end to end (script plus approval CLI) with a 0.00 tie-out residual.
- **✅ Checkpoint 3, Sat 7 Nov:** the same run through the UI.
  - **NO-GO action, in order:** cut `verify_account` → drop webhooks → drop FX gain/loss → simplify the UI to one queue page + one run page. Never cut: idempotency, approval binding, the failure → replacement flow, the tie-out.

**Week 3 (Sun 8 – Fri 13 Nov): prove and ship**
- **Sun 8 – Mon 9:** eval harness (20 scenarios, 5 metrics, raw CSV); fix what it finds.
- **Tue 10:** re-run the contract tests against the sandbox (the guide warns behaviour can change); stretches only if all green (early-pay lever, FX gain/loss).
- **Wed 11:** feature freeze; README (setup, seed, demo, metrics); record video takes.
- **Thu 12:** final video (under 5:00); package the zip; **submit Thu 12 Nov evening**.
- **Fri 13:** buffer only. The hard deadline is **11:59 PM IST**; SPEC's 6:00 PM IST internal cutoff stays as the last-resort target.

---

## Sources
- `board/SPEC-v1.md` §4–§17; `board/DECISIONS.md` (D3, F7, OPEN-1, standing constraints)
- `raw/doc_failure_types.txt` (transition rules, 32 failure types, "submitted for approval … not currently supported")
- `raw/doc_tstatus.txt` (PAID not final)
- `raw/doc_list_transfers.txt` (`request_id`, `beneficiary_id` filters)
- `raw/doc_fxquote.txt` (validity enum, `SINGLE_USE`/`MULTI_USE`, `valid_to_at`)
- `raw/doc_verify.txt` (VoP / CoP)
- Transfer statuses and state machine: https://www.airwallex.com/docs/payouts/transfers/create-a-transfer/transfer-statuses.md
- Older statuses (simulator sequence): https://www.airwallex.com/docs/payouts/older-api-versions/transfers/transfer-statuses.md
- Conversions list (`request_id` filter): https://www.airwallex.com/docs/api/transactional_fx/conversion/list.md · Quotes (incl. `GET /fx/quotes/{quote_id}`): https://www.airwallex.com/docs/api/transactional_fx/quotes.md
- Beneficiaries endpoints (incl. `POST /beneficiary_api_schemas/generate`, `POST /beneficiaries/validate`, `POST /beneficiaries/verify_account`): https://www.airwallex.com/docs/api/payouts/beneficiaries.md
- Financial transactions: https://www.airwallex.com/docs/api/finance/financial_transactions.md
- Hackathon: https://airwallex.hackerearth.com/ · https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/ · https://airwallexdev.com/guide · https://airwallexdev.com/
- HackerEarth boilerplate clause (other events): https://www.hackerearth.com/challenges/hackathon/the-tiny-fish-hackathon-2026/rules/ · https://www.hackerearth.com/challenges/hackathon/mcp-hackathon/custom-tab/official-rules/

## Untested
Everything in §5 (T1–T15). There are no sandbox credentials on the box. All API behaviour above is docs-only, including the PAID → FAILED simulation, `failure_type` retention after auto-cancel, quote expiry and reuse errors, same-body `request_id` replay, webhook delivery for simulations, `verify_account` sandbox output, financial-transactions latency, and the real SWIFT fee.
