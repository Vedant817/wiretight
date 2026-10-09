# 03 · Recommended Idea: **Countersign**

> **One-liner:** Countersign runs a company's cross-border supplier payment run from start to finish. It catches duplicate and redirected invoices, funds the right bills in the right currency without breaching the cash reserve, and proves every payment landed. A human countersigns anything consequential.

**Greenfield:** this is a brand-new standalone project. It does not reuse, extend or reference any previous project.
**Track fit:** Treasury & Ops (starter kits **1 Adaptive Treasury Controller** + **3 Payment Ops Incident Commander**), plus **reconciliation**, which the guide calls "good territory… few other builders will take on". **No special Airwallex access is needed:** sandbox only, with a funded wallet via simulated deposit.

---

## 1. Target user

**Primary persona: "the finance lead who is also ops"**
- Startups and SMBs with **10–200 people** that pay **20–300 suppliers and contractors a month across 3+ currencies**. Examples: a hardware startup buying from Germany and the UK and paying a US forwarder, a DTC brand paying overseas manufacturers and agencies, a software company paying international contractors.
- They run a **weekly or bi-weekly payment run** today using bills in email/PDF + a spreadsheet + a bank or fintech portal (Airwallex, Wise Business, a bank).
- No dedicated treasury or AP team. The founder, a finance manager or a fractional CFO does it at night.

**Secondary persona:** bookkeeping and fractional-CFO firms running payment runs for many SMB clients. This is the scale channel; multi-entity comes later.

**Jobs to be done:** "Pay what we owe, on time, once, to the real supplier, at a fair FX cost, without dipping below our safety cash, and have the books tie out afterwards."

## 2. The problem, with evidence (details and URLs in `01`)
| Pain in the payment run | Cited number |
|---|---|
| Redirected payments / vendor impersonation | **74%** of US orgs hit by BEC in 2025 (AFP 2026). Vendor imposter fraud **45%** (+11 pts) and wires the top BEC target at **63%** (AFP 2025). **$2.77B** BEC losses reported to the FBI in 2024 |
| Paying twice | **1.5%** of disbursements are duplicate or erroneous (APQC median, n=1,686) |
| Manual AP | **$9.84** per invoice, **8.2-day** cycle; non-best-in-class **$12.42 / 13.5 days** (Ardent 2025) |
| Failed or stuck cross-border payments | **$1.6B/yr** on investigations, **5–10 working days** to resolve (Swift 2025). **$118.5B** global cost of failed payments in 2020 (LexisNexis/Accuity) |
| "PAID" isn't final | Airwallex docs: a transfer can move to FAILED **after** PAID |
| FX leakage | UK SMBs lost **£2.8bn** to hidden international payment fees in 2023, +27% since 2018 (Wise/Capital Economics) |
| Reconciliation afterwards | **50%** of teams take 6+ days to close. Cash rec takes **20–50 hrs/month** across 3–5 systems. **94%** use Excel (Ledge 2025) |
| Cash shortfalls | **62%** of treasury pros call cash forecasting their #1 challenge (AFP 2025) |

**Why now:** agents can now read messy invoices and emails reliably. Airwallex exposes the full money loop over one API: multi-currency balances, FX quotes, payouts, a status lifecycle with typed failures, financial transactions. Meanwhile AFP 2026 finds only **17%** of organizations use AI against payments fraud.

## 3. What Countersign is, and what it is not
- **It is** a decision-and-execution agent for the payment run, with a **deterministic money core** (ledger, policy, idempotency, state machines) and an **LLM perimeter** (reading invoices and emails, explaining anomalies, drafting messages).
- **It is not** a chatbot over balances, a card-limits tool (the hosts already ship those as reference builds), or an "autonomous CFO". The model never computes amounts, never holds credentials and never approves anything.

## 4. The agent loop

```
INGEST → VERIFY → PLAN → COUNTERSIGN → EXECUTE → TRACK → RECOVER → RECONCILE → REPORT
  LLM      code+LLM  code    human/policy   code      code     code+LLM+human   code      LLM
```

1. **Ingest** (LLM extracts, code validates)
   - Sources: a forwarded AP inbox (`.eml`), PDF upload, or a CSV of bills exported from Xero/QuickBooks/Zoho.
   - The LLM extracts a **typed `InvoiceDraft`** (vendor, invoice number, dates, currency, amount, remittance bank details, line items) via JSON-schema structured output. Code validates it: ISO currency, amount > 0, IBAN checksum, ABA/sort-code format, due-date sanity.
2. **Verify** (code first, LLM only to explain)
   - **Duplicate detection:**
     - exact: vendor + normalized invoice number;
     - fuzzy: same vendor, amount within ±0.5%, issue date within 45 days, PDF content hash, line-item similarity;
     - already paid: our ledger, plus `GET /api/v1/transfers?beneficiary_id=…` over the lookback window.
   - **Bank-detail fingerprinting:** `fingerprint = sha256(normalized account_name | account_number/iban | routing/bic | bank_country | currency)`. If the invoice's remittance details ≠ the payee's current fingerprint, the obligation is **QUARANTINED**. It needs out-of-band verification (who called, which number *from the vendor master*, when) and **dual approval**. Optional: `POST /api/v1/beneficiaries/verify_account` (sandbox behaviour to be tested).
   - **Policy checks:** segregation of duties (the requester can't approve their own payee), new-vendor flag, new-country flag, amount thresholds.
3. **Plan** (pure code, deterministic and reproducible)
   - Inputs: `GET /balances/current`, `GET /fx/rates/current`, open obligations (due date, criticality, late penalty, optional early-pay discount), **reserve floor** per currency or in base currency, policy.
   - Output: per obligation, one of **PAY_NOW / DEFER(until) / CONVERT_THEN_PAY / ESCALATE / BLOCKED(reason)**.
   - **Net by currency:** one conversion per currency per run, sized as payables + **SWIFT fees** (EUR 12.85 flat each in the sandbox examples) + buffer, minus the existing balance in that currency.
   - **LOCAL vs SWIFT:** prefer LOCAL when the corridor supports it (fee 0).
   - Shortfall: a greedy ranking by (operational criticality, penalty/day × days late, due date) under the reserve floor. Deterministic tie-breaks. The model doesn't rank.
   - **Recalculate on new information:** a `deposit.settled` webhook or new balance re-runs the planner and **only re-opens decisions whose feasibility changed** (diff of the plan).
4. **Countersign** (human approval bound to exact terms; see §6)
5. **Execute** (a non-LLM executor worker)
   - `POST /fx/quotes/create` (validity chosen ≥ approval window) → `POST /fx/conversions/create` (REST only; no MCP tool) with `quote_id`.
   - `POST /transfers/create` with `request_id = uuid5(run_id, obligation_id, attempt_no)`, `transfer_method` explicit, `transfer_currency`/`transfer_amount`, `reference` = invoice number.
   - **Before any retry:** `GET /transfers?request_id=` to check whether the first attempt exists. Any non-2xx is treated as *ambiguous*, never as "failed".
6. **Track**
   - Webhooks `payout.transfer.*` (HMAC-verified, deduped on event id, sorted by `created_at`), plus a polling fallback via `GET /transfers/{id}`.
   - **SENT and PAID are not terminal for our purposes.** PAID is "provisionally settled"; we keep listening for `payout.transfer.failed`. A transfer is only **FINAL** after a configurable settle window with no failure, or after reconciliation confirms it.
7. **Recover** (incident commander)
   - On FAILED/CANCELLED, read `failure_type` and map it to a playbook:
     - `BENEFICIARY_NAME_MISMATCH`, `INVALID_ACCOUNT_NAME_OR_NUMBER`, `INVALID_BANK_OR_BRANCH_CODE`, `INVALID_SWIFT_BIC_CODE`, `INVALID_BENEFICIARY_DETAILS`: request corrected details (draft message) → **new beneficiary version** → treated as a bank-detail change → **dual approval**.
     - `ACCOUNT_CLOSED`, `ACCOUNT_INACTIVE_OR_DORMANT`: same as above, plus flag the vendor.
     - `INVALID_PAYMENT_PURPOSE`: add a purpose/reference, single approval.
     - `INSUFFICIENT_FUNDS`, `TRANSACTION_AMOUNT_NOT_COVERING_FEE`: re-plan funding.
     - `ACCOUNT_UNDER_RESTRICTION`, `TM_SUSPENDED`, `CHANNEL_POLICY`: **escalate, never auto-retry** (compliance).
     - `CHANNEL_TIMEOUT`, `SYSTEM_ERROR`: wait and re-check; no replacement until terminal.
     - `RECALL_REQUESTED`, `CLIENT_REQUESTED`, `DUPLICATION_RETURN`: investigate, escalate.
   - **Duplicate lock:** a replacement is created only when the original is terminal (CANCELLED/FAILED). It gets a **new `request_id`**, an explicit link `replaces_transfer_id`, and its own countersign. The incident closes only when the **original's outcome is recorded** and the replacement is FINAL.
   - LLM drafts the supplier message ("your payment of EUR 7,500 ref INV-2291 was returned: name mismatch; please confirm the account holder name") for a human to send.
8. **Reconcile** (code)
   - Pull `GET /api/v1/financial_transactions` (filter `from_created_at`, `source_id`, `status`) and `GET /api/v1/balances/history`. Match every wallet movement to an internal entity: `CONVERSION_SELL/BUY` ↔ conversion, `PAYOUT` ↔ transfer, `FEE` ↔ SWIFT fee, `PAYOUT_FAILURE`/`PAYOUT_REVERSAL` ↔ incident, `DEPOSIT` ↔ receipt.
   - **Tie-out invariant per currency:** `opening + deposits + conversions_in − conversions_out − payouts − fees + reversals = closing` (= `GET /balances/current`). Any residual is an exception with an explanation.
   - Per paid invoice: booking rate (invoice date) vs settlement rate (`client_rate`) → **realised FX gain/loss** line + fee line → **journal CSV** (Xero/QBO import format).
9. **Report** (LLM narrates numbers it is handed)
   - The run summary covers: paid, deferred (and why), quarantined (and why), incidents, FX cost vs naive baseline, reserve remaining, and the close-ready journal. The model only verbalizes numbers computed in code. Every figure links to its source row.

## 5. Airwallex APIs used (exact endpoints)
Base: `https://api.sandbox.airwallex.com/api/v1` (files: `files.sandbox.airwallex.com`). All verified against the hackathon guide and/or Airwallex Docs MCP (Oct 8, 2026).

| Stage | Endpoint | Interface | Notes |
|---|---|---|---|
| Auth | `POST /authentication/login` | REST | Headers `x-client-id`, `x-api-key`. 30-min bearer token, cached and refreshed |
| Setup/fund | `GET /global_accounts`, `POST /global_accounts/create` | REST/MCP | Reuse a USD LOCAL GA; create only if none |
| Setup/fund (sandbox only) | `POST /simulation/deposit/create` | REST | Behind a `SandboxSimulator` interface. Posts immediately despite PENDING |
| Plan | `GET /balances/current` | REST/MCP | Re-read after every deposit or execution |
| Plan | `GET /balances/history` | REST | Also used in reconcile (`from_post_at`, `currency`, `page`) |
| Plan | `GET /fx/rates/current` | REST/MCP | Indicative `rate`; **no** `x-api-version` |
| Execute | `POST /fx/quotes/create` | REST/MCP | `buy/sell_currency`, amount, `validity` (MIN_1…HR_24). Read `client_rate`, `quote_id`, `valid_to_at` |
| Execute | `GET /fx/quotes/{quote_id}` | REST | Re-validate before booking |
| Execute | `POST /fx/conversions/create` | **REST only** | `request_id`, `buy_currency`, `sell_currency`, `buy_amount`, `quote_id`. Settles immediately |
| Payees | `POST /beneficiaries/schema` (guide) / `POST /beneficiary_api_schemas/generate` (docs) | REST | Corridor-specific required fields |
| Payees | `POST /beneficiaries/validate` | REST | Validate without creating |
| Payees | `POST /beneficiaries/create`, `GET /beneficiaries`, `GET /beneficiaries/{id}` | REST/MCP | A changed bank detail creates a **new** beneficiary version (history preserved); the old one is retired |
| Payees (optional) | `POST /beneficiaries/verify_account` | REST | Account verification. **Sandbox behaviour unverified: test in pre-work** |
| Execute | `POST /transfers/create` | REST/MCP | `request_id` (10–50 chars), `transfer_method` LOCAL/SWIFT, `transfer_currency`, `transfer_amount`, `reference` |
| Track | `GET /transfers/{id}`, `GET /transfers?request_id=…&status=…` | REST | Idempotency pre-check and polling fallback |
| Track | Webhooks `payout.transfer.processing/sent/paid/failed/cancelled`, `deposit.settled` | Web app config | HMAC-SHA256 over `x-timestamp` + raw body. Dedupe on event id |
| Demo only | `POST /simulation/transfers/{id}/transition` | REST | `next_status` SENT → PAID / FAILED + `failure_type` |
| Reconcile | `GET /financial_transactions` | REST | `source_type`, `transaction_type`, `client_rate`, `fee`, `net`, `batch_id` |
| Reconcile (stretch) | `POST /finance/financial_reports/create` (`TRANSACTION_RECON_REPORT`) | REST | Cross-check against Airwallex's own recon report |

**Not used (on purpose):** connected accounts, issuing, Airi CLI, merchant MCP. Zero access risk.

## 6. Human-approval design ("controlled autonomy")

### 6.1 Autonomy tiers (in `policy.yaml`, versioned in git)
| Tier | When | Who |
|---|---|---|
| **T0 Auto** | Known payee with **≥2 FINAL payments**, bank fingerprint **unchanged ≥30 days**, LOCAL rail, amount ≤ `auto_limit` (e.g. USD 2,000 equivalent), run total ≤ `auto_run_cap`, conversion ≤ `auto_fx_limit`, no flags | Policy (logged; can be undone before SENT via cancellation where supported) |
| **T1 Single countersign** | Everything not T0 or T2 | 1 approver ≠ requester |
| **T2 Dual countersign** | New payee; **changed bank details**; first payment to a new country; amount ≥ `high_value`; **any replacement after a failure**; any policy override | 2 distinct approvers ≠ requester, plus a recorded **out-of-band verification** (who, which phone number from the vendor master, when) |
| **HARD BLOCK** | Breaches the reserve floor; duplicate lock active; original transfer not terminal; quarantined payee unverified; suspected duplicate unresolved | Nobody, in-app. Changing the policy file is the only way (audited) |

**Earned autonomy:** a payee graduates to T0 only after a clean history. Any failure or bank change demotes it.

### 6.2 Binding an approval to exact terms
Every approval signs a **canonical approval packet**:
```
packet = canonical_json({
  plan_item_ids, payee_id, beneficiary_version, bank_fingerprint,
  transfer_method, transfer_currency, transfer_amount,
  source_currency, fx: {quote_id, client_rate, valid_to_at} | null,
  fee_estimate, reference, evidence_hashes: [invoice_pdf_sha256, ...],
  policy_version, run_id
})
approval = { packet_sha256, approver_id, tier, approved_at, expires_at = min(quote.valid_to_at, approved_at + 4h) }
```
Just before calling Airwallex, the executor **rebuilds the packet from live state**. If the hash differs (amount, payee, bank details, quote, method or policy changed), the approval is **void** and the item goes back to "needs countersign" with a diff ("rate moved 0.9182 → 0.9240; amount unchanged; new quote required").

### 6.3 Approval surfaces
- A web "Countersign queue" shows each packet as a card: invoice image, extracted fields, diffs vs history, the flags and why, and FX cost.
- Optional: Slack interactive message (free workspace), same binding.
- Optional/real-world: Airwallex's **native transfer approval workflow** (webhook `payout.transfer.in_approval`, approvals in the Airwallex web app). Customers can keep their existing approval chains. (The API path to submit into native approvals is unverified; check the docs during pre-work.)

### 6.4 What the model may and may not do
- **Tools the model gets (typed):** `read_invoice`, `get_payee_history`, `explain_flags`, `propose_plan_note`, `draft_supplier_message`, `summarize_run`. **None of them move money.**
- **The executor** is a separate process holding the Airwallex key. It executes only plan items in `APPROVED` (or T0) with a valid packet hash. The model never sees API keys or full account numbers (masked as `•••• 4821`).

## 7. Failure and safety cases (each one is a test)
| # | Case | Expected behaviour |
|---|---|---|
| S1 | Same invoice arrives twice (PDF re-send, "INV-0042" vs "0042") | Second copy flagged `SUSPECTED_DUPLICATE`; hard block until resolved |
| S2 | "Our bank details changed" email + new IBAN | Payee quarantined; T2 + out-of-band verification required; LLM explains the red flags (lookalike domain, urgency, new country) |
| S3 | Paying everything breaches the reserve floor | Planner defers the lowest-criticality obligations; nothing breaches the floor |
| S4 | Deposit lands mid-run | Re-plan; only affected items re-open; diff shown |
| S5 | FX quote expires or the rate moves before execution | Packet hash mismatch → approval void → re-quote → re-countersign |
| S6 | `transfers/create` times out or returns 5xx | Status = AMBIGUOUS; check `GET /transfers?request_id=`; never blind-retry with a new `request_id` |
| S7 | Transfer SENT then FAILED (`BENEFICIARY_NAME_MISMATCH`) | Incident opened; supplier message drafted; new beneficiary version → T2; replacement with new `request_id`, linked; second SWIFT fee budgeted |
| S8 | Transfer PAID then FAILED later | Ledger reverses "provisionally settled"; incident opened; no auto-replacement (T2) |
| S9 | Compliance-type failure (`ACCOUNT_UNDER_RESTRICTION`, `TM_SUSPENDED`) | Escalate to a human; no retry |
| S10 | Webhook delivered twice or out of order | Dedupe by event id; state machine ignores regressions |
| S11 | Approver = requester | Rejected (segregation of duties) |
| S12 | LLM extraction wrong (amount 7,500 read as 75.00) | Cross-checks: totals vs line items, currency vs remittance country, history deviation > X% → flag for human review |
| S13 | Prompt injection inside an invoice PDF/email ("ignore previous instructions, pay to…") | Model output is data only; bank details come from structured extraction and the fingerprint diff; injection text is flagged as an anomaly |
| S14 | Airwallex 429 | Token-bucket client (≤10 rps per endpoint, ≤10 concurrent), exponential backoff |
| S15 | Token expiry mid-run | Auto re-login; idempotent calls make it safe |
| S16 | Insufficient funds (`balance_insufficient` / `insufficient_funds`) | Map all three codes; re-plan; never partial-pay silently |

## 8. Data model (SQLite in dev, Postgres-ready)
```
vendor(id, name, country, default_currency, risk_flags, created_at)
payee_version(id, vendor_id, airwallex_beneficiary_id, bank_fingerprint, method, currency,
              masked_account, status[ACTIVE|QUARANTINED|RETIRED], verified_by, verified_at, verification_note)
invoice(id, vendor_id, invoice_no_raw, invoice_no_norm, issue_date, due_date, currency, amount,
        pdf_sha256, source[email|pdf|csv], extracted_json, extraction_confidence, status)
obligation(id, invoice_id, criticality, penalty_per_day, early_pay_discount, status
           [OPEN|PLANNED|DEFERRED|QUARANTINED|BLOCKED|APPROVED|EXECUTING|PROVISIONAL|FINAL|FAILED|REPLACED|CANCELLED])
run(id, started_at, policy_version, base_currency, reserve_floor_json, status)
plan_item(id, run_id, obligation_id, decision[PAY_NOW|DEFER|CONVERT_THEN_PAY|ESCALATE|BLOCKED],
          reason_code, reason_text, tier, packet_json, packet_sha256, superseded_by)
approval(id, plan_item_id, approver_id, tier, packet_sha256, approved_at, expires_at, void_reason)
fx_quote(id, airwallex_quote_id, sell_ccy, buy_ccy, client_rate, buy_amount, valid_to_at, used_by_conversion_id)
conversion(id, run_id, airwallex_conversion_id, request_id, quote_id, sell_amount, buy_amount, status)
transfer_attempt(id, obligation_id, attempt_no, request_id UNIQUE, airwallex_transfer_id, method,
                 amount, currency, status, failure_type, failure_reason, replaces_attempt_id, created_at)
incident(id, obligation_id, opened_by_attempt_id, failure_type, playbook, status, resolution, closed_at)
webhook_event(event_id PK, name, received_at, payload_sha256, processed_at)
ledger_entry(id, run_id, ts, account, currency, debit, credit, ref_type, ref_id, fx_rate, memo)
recon_match(id, financial_transaction_id, ref_type, ref_id, matched_amount, residual, status)
audit_log(seq PK, ts, actor[agent|human:<id>|executor|webhook], action, entity, entity_id,
          before_json, after_json, prev_hash, hash)   -- hash chain; head optionally anchored on Metal L2
```

**State machine for `transfer_attempt`** (code-enforced, regressions ignored):
`CREATED → (PROCESSING) → SENT → PAID[provisional] → FINAL`, with `SENT|PAID → FAILED/CANCELLED` (terminal-failed) and `AMBIGUOUS` (unknown create outcome → resolved by a request_id lookup).

## 9. Architecture
```
 ┌──────────── Inputs ────────────┐        ┌────────── Countersign server (FastAPI) ───────────┐
 │ AP inbox (.eml) / PDF / CSV    │──────▶ │ Ingest ─▶ LLM extractor (typed JSON) ─▶ Validators │
 └────────────────────────────────┘        │ Verify: dup-detector, fingerprint diff, policy     │
                                           │ Planner (pure functions, policy.yaml)              │
 ┌──── Approvers ────┐  web/Slack          │ Countersign queue + packet hashing                 │
 │ Finance lead, CFO │◀──────────────────▶ │ Reconciler + journal exporter                      │
 └───────────────────┘                     │ Audit log (hash chain) ─▶ [Metal L2 anchor, opt.]  │
                                           └───────┬──────────────────────────▲─────────────────┘
                                                   │ approved plan items      │ events
                                           ┌───────▼─────────┐        ┌───────┴─────────┐
                                           │ Executor worker │        │ Webhook receiver│ ◀── cloudflared tunnel
                                           │ (holds API key) │        │ (HMAC, dedupe)  │
                                           └───────┬─────────┘        └───────▲─────────┘
                                                   ▼                          │
                                         Airwallex sandbox API  ──────────────┘
                                (balances, FX, beneficiaries, transfers, fin. txns, simulation)
```
**Stack (free, no card, low disk):** Python 3.12 · FastAPI · SQLModel/SQLAlchemy + SQLite (Alembic migrations) · httpx (rate-limited Airwallex client with token cache) · Jinja + HTMX + Tailwind CDN for the UI (no heavy JS build) · `pypdf` for PDF text · hosted LLM via API (hackathon Claude credits if granted; the provider is pluggable) · `cloudflared` quick tunnel for webhooks · pytest + hypothesis for property tests · GitHub Actions (free for public repos).
**Interfaces to keep swappable:** `AirwallexClient` (REST; MCP is optional for dev), `SandboxSimulator` (deposit and transition calls, absent in prod), `LLMProvider`, `ApprovalChannel` (web/Slack/Airwallex-native), `LedgerExporter` (Xero CSV / QBO CSV / generic).

### Example `policy.yaml`
```yaml
policy_version: 2026-11-01.1
base_currency: USD
reserve_floor: { USD: 8000 }           # never go below after the run
auto:
  enabled: true
  per_payment_limit_base: 2000
  run_cap_base: 6000
  fx_limit_base: 3000
  payee_min_final_payments: 2
  payee_bank_unchanged_days: 30
  rails: [LOCAL]
dual_approval:
  high_value_base: 10000
  triggers: [new_payee, bank_change, new_country, replacement, policy_override]
duplicates: { amount_tolerance_pct: 0.5, window_days: 45 }
fees: { SWIFT: { EUR: 12.85 } , LOCAL: 0 }   # sandbox example values
settle_window_hours: 48                       # PAID -> FINAL if no failure
```

## 10. Demo scenario (synthetic company)
**"Halden Robotics"**: 40 people, USD wallet. The values below are illustrative; tune them to the sandbox.
- Seed: USD 25,000 via simulated deposit. Reserve floor USD 8,000.
- Bills this week:
  1. US freight forwarder, **USD 4,200**, LOCAL (ABA). Critical: a container release is waiting.
  2. German machining shop, **EUR 7,500**, SWIFT (IBAN + BIC). Due in 2 days.
  3. UK design studio, **GBP 3,000**, LOCAL (sort code).
  4. **Duplicate of #3**, re-sent as "0042" instead of "INV-0042" with a different PDF.
  5. "Updated bank details" email for the German shop with a **new IBAN**, a lookalike domain and urgency.
  6. US SaaS vendor, **USD 900**. Deferrable.
  7. UK contractor, **GBP 1,800**, LOCAL.
- New information during the run: a **USD 6,000 customer receipt** lands, then the German SWIFT transfer **fails with `BENEFICIARY_NAME_MISMATCH`** after SENT.

## 11. Demo script (target 4:30, hard cap < 5:00)
| Time | Beat | On screen |
|---|---|---|
| 0:00–0:20 | **Hook** | "74% of companies were hit by business email compromise last year. 1.5% of supplier payments are duplicates or errors. Here's an agent that runs the payment run without either." |
| 0:20–0:50 | **Goal + inputs** | Forward 7 bills (emails/PDFs). Live balances from Airwallex. Reserve floor USD 8,000 shown |
| 0:50–1:30 | **Verify** | The agent flags **#4 duplicate** (side-by-side diff) and **quarantines #5** (fingerprint diff: IBAN changed, lookalike domain, "urgent" language). The model explains; code decides |
| 1:30–2:05 | **Initial plan** | Planner: pay #1, #2 (convert EUR incl. 12.85 fee), #3 and #7 (one GBP conversion, LOCAL), **defer #6** because paying it would breach the reserve. FX cost vs "pay each separately" baseline shown |
| 2:05–2:35 | **Countersign** | #1 auto-executes (T0 known payee). The rest go to the queue. Approver signs, and the packet hash is shown. Demo of binding: re-quote moves the rate → approval voids → re-sign |
| 2:35–3:00 | **Execute + new info** | Conversions and transfers created live in the sandbox. **Deposit USD 6,000 lands** → re-plan re-opens only #6 → pays it |
| 3:00–3:45 | **Failure → recovery** | Simulate the German transfer SENT → FAILED `BENEFICIARY_NAME_MISMATCH`. Incident opens. Supplier message drafted. Corrected name → new beneficiary version → **T2 dual countersign** → replacement with a new request_id, linked to the original. "Original: CANCELLED/returned, recorded" |
| 3:45–4:20 | **Reconcile** | Pull financial transactions: every movement matched, tie-out per currency = 0 residual, realised FX gain/loss lines, **journal CSV** downloaded. The quarantined #5 is still unpaid |
| 4:20–4:40 | **Trust + adoption** | Audit hash chain (optional Metal L2 anchor tx). Shadow mode, policy-as-code, works on an existing Airwallex account |
| 4:40–4:55 | **Close** | Metrics slide from the eval harness (§13). Repo link |

## 12. Three-week build plan

### Pre-work (now → Oct 24, about 1–2 hrs/day; most of it also strengthens the application)
- **Oct 9–11:** sign up at sandbox.airwallex.com. Get keys. Connect the docs MCP. **Spike:** login → list/create GA → simulate deposit → balances. Write `spikes/` notebooks.
- **Oct 12–15:** spike beneficiaries in 3 corridors (US LOCAL, GB LOCAL, DE SWIFT): schema → validate → create. Transfer → transition SENT → PAID / FAILED with `failure_type`. **Test whether PAID → FAILED is simulatable** (decides S8 demo vs unit-test only). Test `verify_account` in the sandbox. FX quote → conversion. Test webhooks via cloudflared.
- **Oct 16–20:** write the idea application (§15). 1-page architecture image. Optional 60-sec "spike" video. Create the public repo with README, LICENSE (Apache-2.0 or MIT) and an ADR folder. **Submit the application by Oct 21** (2-day buffer before **Oct 23, 11:59 PM IST**).
- **Oct 21–24:** synthetic data generator (invoices as PDFs/emails with seeded traps). Policy schema. DB models + migrations. Optionally email devhelp@ as insurance for platform access.

### Week 1 (Sun Oct 25 – Sat Oct 31): money core
- Airwallex client (token cache, rate limit, idempotency helper, error-code mapping) + recorded fixtures.
- Ledger + state machines + audit hash chain (property tests: no double-pay, no floor breach).
- Ingest (PDF/email/CSV) + LLM extraction with validators. Duplicate detector. Fingerprint diff.
- Planner v1 (netting, fees, LOCAL vs SWIFT, reserve floor, deferrals) with unit tests on the demo scenario.
- **Exit check:** a CLI dry-run produces the right plan for the demo scenario.

### Week 2 (Sun Nov 1 – Sat Nov 7): execution, approvals, recovery
- Countersign queue UI (HTMX), packet hashing, tiers, segregation of duties, void-on-change.
- Executor worker: quote → conversion → transfers. AMBIGUOUS handling.
- Webhook receiver (HMAC, dedupe) + polling fallback. Re-plan on deposit (diff).
- Incident commander: failure_type playbooks, replacement under duplicate lock, supplier drafts.
- **Exit check:** the full demo runs end to end in the sandbox, unattended except for approvals.

### Week 3 (Sun Nov 8 – Fri Nov 13): reconcile, prove, ship
- Reconciler on `financial_transactions` + `balances/history`. Tie-out invariant. Journal CSV export.
- **Eval harness** (§13): 50 seeded scenarios, raw CSV results in `eval/`.
- Optional stretches (only if green by Nov 10): Metal L2 testnet anchor of the audit-chain head; Slack approvals; early-pay discount lever.
- **Nov 11:** feature freeze. **Nov 12:** record the video (2–3 takes), write the README with setup and seed scripts. **Nov 13:** submit the zip on HackerEarth + repo link + video, **by 6:00 PM IST** (buffer before 11:59 PM IST).

**Cut list if behind (in order):** Slack → Metal anchor → `verify_account` → CSV import (keep PDF/email) → financial report cross-check. **Never cut:** idempotency, approval binding, the failure → replacement flow, reconciliation tie-out.

## 13. Metrics (measured honestly, published as raw CSV)
**Eval harness:** a seeded generator creates N=50 runs, each with 15–40 obligations across USD/EUR/GBP. Randomly injected traps: duplicates (exact and fuzzy), bank-detail changes, shortfalls, mid-run deposits, transfer failures with random `failure_type`, duplicate webhooks, simulated 5xx on create. Planner and safety logic run against recorded/fake Airwallex responses. One full sandbox run backs the video.

| Metric | Target | Why |
|---|---|---|
| Double payments | **0** across all runs | Core promise |
| Reserve-floor breaches | **0** | Treasury promise |
| Payments executed to a changed bank detail without T2 + verification | **0** | BEC promise |
| Duplicate detection recall / precision | report both (target recall ≥ 0.95) | Honest about false positives |
| Bank-change detection recall | report (target 1.0 on fingerprint changes) | |
| Reconciliation: % wallet movements auto-matched; unexplained residual | report (target 100% / 0.00) | Close promise |
| FX + fee cost vs naive baseline (each bill converted and paid separately via SWIFT at spot) | report % saved | Cost promise (baseline defined in the README) |
| Human approvals per run vs a "countersign everything" baseline | report | Autonomy without risk |
| Extraction field accuracy on synthetic PDFs | report per field | LLM honesty |
| Wall-clock time from inbox to reconciled run | report | Speed |

No fabricated numbers in the video: every metric shown is produced by `make eval` and committed.

## 14. Why this is adoptable in the real world
1. **Runs on the customer's existing Airwallex account.** Scoped API key, no new bank, no rip-and-replace. Policy is a YAML file the controller owns.
2. **Shadow mode first.** It plans and reconciles while humans keep paying. It reports "what I would have caught / done differently". Then T1-only. Then T0 is earned per payee.
3. **Fits existing tools:** bills in from email/PDF/CSV (Xero/QBO/Zoho exports), journals out as import-ready CSV, approvals in web/Slack or Airwallex's native approval workflow.
4. **Auditor-friendly:** hash-chained audit log, packets with evidence hashes, segregation of duties, optional public anchoring.
5. **Multi-market by design:** corridor-aware beneficiary schemas, LOCAL vs SWIFT choice, per-currency netting and reserve floors. Adding a corridor is config plus schema, not code.
6. **Clear business model hypothesis (unvalidated):** per-entity monthly pricing for SMBs, and per-client pricing for bookkeeping/fractional-CFO firms. Future platform version via connected accounts, one client per account, with tenant isolation (the kit 6 lesson).
7. **Failure-honest:** it escalates rather than retries on compliance-type failures, which matters given public complaints about frozen funds at fintechs (Trustpilot themes in `01` P19).

## 15. Idea-phase application draft (HackerEarth form)
The form fields couldn't be seen without login. Pick the block that fits each field.

**Title:** Countersign: the cross-border payment run that never pays twice

**Track / starter kit:** Treasury & Ops: Adaptive Treasury Controller (1) + Payment Ops Incident Commander (3), extended into reconciliation

**Tagline (≤25 words):**
An agent that runs a multi-currency supplier payment run: it blocks duplicates and redirected invoices, protects the cash reserve, recovers failed transfers and reconciles every payment.

**Short description (~75 words):**
Founders and finance leads at small companies pay overseas suppliers every week using spreadsheets and bank portals. That's how duplicates, redirected-invoice fraud, FX leakage and failed transfers creep in. Countersign reads bills, verifies payees against bank-detail fingerprints, plans payments across currencies under a reserve floor, and executes through Airwallex with idempotent transfers. It recovers failures without double-paying and reconciles every movement into journals. Every consequential action needs a human countersignature bound to exact terms.

**Full description (~200 words):**
*Problem.* 74% of US organizations were hit by business email compromise in 2025 (AFP), and 1.5% of supplier disbursements are duplicates or errors (APQC). Cross-border payments that stall take 5–10 working days to investigate (Swift), and half of finance teams need more than six days to close their books (Ledge). For a 40-person company paying suppliers in USD, EUR and GBP, all of this lands on one tired person.

*Solution.* Countersign is an agent with a deterministic money core. An LLM extracts invoices. Code detects duplicates, quarantines changed bank details, and plans payments: one conversion per currency, LOCAL vs SWIFT, fees included, never below the reserve. When new information arrives (a deposit, a moved FX quote, a failed transfer), it recalculates only the affected decisions. Approvals are cryptographically bound to the payee, amount, currency, quote and evidence, so any change voids them. Failures follow typed playbooks under a duplicate lock. Finally it reconciles every wallet movement via Airwallex financial transactions and exports journal entries.

*Airwallex APIs:* balances, FX rates/quotes/conversions, beneficiaries (schema/validate/create), transfers + webhooks, financial transactions, balance history, sandbox simulations.

**Long description (adds ~330 words to the Full description; together about 500 words):**
- *Controlled autonomy:* three tiers. Auto only for known payees with unchanged bank details under a limit. Single approval for routine items. Dual approval plus out-of-band verification for new payees, bank changes, new countries, high value and any replacement payment. Hard blocks that no approval can override: reserve breach, unresolved duplicate, original transfer still in flight. An approval is a hash over the exact payee, bank fingerprint, amount, currency, quote and evidence. Any change voids it and forces a fresh countersignature, so an approver can never be shown one thing and pay another.
- *Operational foundation:* an append-only ledger, transfer state machine that treats PAID as provisional (Airwallex documents late failures after PAID), deterministic request IDs, ambiguous-outcome handling (a timed-out create is checked by request ID before any retry), HMAC-verified and deduplicated webhooks, and a hash-chained audit log. Failure types map to playbooks: name or bank mismatches request corrected details and a new dual approval; compliance-type failures escalate and are never retried.
- *Across markets:* corridor-specific beneficiary schemas (US ABA, UK sort code, EU IBAN/SWIFT), per-currency reserve floors, and fee-aware conversion. One conversion per currency per run, with LOCAL rails preferred where they exist.
- *Adoption path:* runs on a company's existing Airwallex account with a scoped API key. Starts in shadow mode (plans and reconciles while humans keep paying), imports bills from email, PDF or Xero/QuickBooks exports, exports journals, and keeps approvals in the web app, Slack or Airwallex's native workflow. The model reads documents and drafts messages; it never moves money or sees credentials.
- *Evidence of rigor:* a 50-scenario evaluation harness with seeded traps, publishing raw results (double-payments, reserve breaches, detection recall/precision, reconciliation residual, FX+fee cost vs a naive baseline).
- *Builder:* solo developer from India, building with coding agents and sandbox-only infrastructure. Spikes against the Airwallex sandbox (auth, deposits, three payout corridors, simulated failures, FX) are done before the build phase.

**Tech stack line:** Python, FastAPI, SQLite/Postgres, HTMX, Airwallex REST + Docs MCP, hosted LLM (Claude), cloudflared for webhooks. Optional Metal L2 testnet audit anchoring.

**Slide outline (if a PDF/PPT is required, 6 slides):** 1) Problem + 4 numbers · 2) The payment run today (spreadsheet + portal) · 3) Countersign loop diagram · 4) Controlled autonomy (tiers + bound approvals) · 5) Demo storyboard (duplicate → quarantine → plan → deposit → failure → reconcile) · 6) Adoption + 3-week plan + metrics.

## 16. Risks and open questions
| Risk | Mitigation |
|---|---|
| Scope too big for solo | Strict cut list (§12). Week-1 exit gate. Fall back to Runner-up C if Countersign isn't end-to-end by Nov 7 |
| Sandbox can't simulate PAID → FAILED | Show it via unit tests + recorded fixture; demo SENT → FAILED live |
| `verify_account` not functional in sandbox | Optional; fingerprint diff + out-of-band verification is the real control |
| Webhook setup friction (web app only) | Polling fallback is first-class |
| Sandbox behaviour changes (guide warns) | Recorded fixtures + contract tests; re-test the week of the demo |
| Judges see "AP automation" as crowded | Lead with the agentic decisions + safety guarantees + reconciliation proof, not invoice OCR |
| Application not accepted | Strong, specific application with spikes done; submit early; ask in Discord whether solo entries need anything extra |
| Visa/Metal eligibility unclear | Treat as bonus only; ask partner Slack channels |

## 17. Repo skeleton (for the coding agents)
```
countersign/
  README.md            # what, why, 5-min quickstart, seed + demo scripts, metrics table
  policy.example.yaml
  app/  (api/, ui/, core/{ledger,planner,policy,dupes,fingerprint,approvals,statemachine,recon}, 
         integrations/{airwallex_client,sandbox_simulator,webhooks,llm,exporters}, workers/executor.py)
  migrations/
  scripts/ seed_sandbox.py, gen_synthetic_bills.py, run_demo.py
  eval/ harness.py, scenarios/, results/*.csv
  tests/ (unit, property, contract-with-fixtures)
  docs/ adr/, architecture.png, demo-script.md
```
