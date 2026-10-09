# Round 1 feasibility review: S1 Ledgerline (deep), S2 PayRun Warden (brief)
**Seat:** AB Staff Engineer · **Written:** Thu 8 Oct 2026, ~7:30 PM IST
**Inputs:**
- `board/ROUND1-SHORTLIST.md`
- `board/DECISIONS.md`
- `raw/doc_*.txt`
- official Airwallex docs, fetched live on 8 Oct 2026
- the public, no-auth Airwallex Docs MCP (`https://mcp.sandbox.airwallex.com/docs`)

**Greenfield.** No reference to past projects. Nothing was registered, submitted, or sent, and no other agents were messaged.

---

## Sandbox status: nothing was TESTED
I checked for existing credentials:
- process env vars (no `AWX_*`, `AIRWALLEX*`, `CLIENT_ID`, or `API_KEY`)
- `.env*` files and config files under `/workspace/agentic-banking-hack/` (none)
- `raw/mcp.sh` and `raw/mcp.py`, which call only the public **Docs** MCP and hold no sandbox credentials

**No sandbox credentials exist on the box, so no sandbox call was made.** Every verdict below is **UNTESTED (docs only)**. Creating a sandbox account is a sign-up, which is outside my remit. Vedant has to do it, or explicitly authorize it, before the day-1 spike in §7.

---

## 1. Verdicts on the four logged conflicts

### a) Does the deposit simulator take a `reference` field?
**Verdict: YES.** Banking-domain was right; senior-dev's "no reference field" is wrong. **UNTESTED (docs only).**
- API reference, *Create a Global Account Deposit* (`POST /api/v1/simulation/deposit/create`), request body:
  > "`reference` (string, optional) Description of the deposit."

  The same body also takes `payer_name`, `payer_country`, `payer_bankname`, `statement_ref` ("needs to be unique"), and `status`:
  > "Target next_status of this deposit. Default value is SETTLED. Possible values: `PENDING` `REJECTED` `SETTLED`"

  Source: https://www.airwallex.com/docs/api/simulation/deposits/create.md (HTML version: https://www.airwallex.com/docs/api/simulation/deposits)
- The official simulation guide's example request sends `"reference": "test"`, and the example response echoes `"reference": "test"`. Source: https://www.airwallex.com/docs/developer-tools/sandbox-environment/deposits/simulate-deposits-to-your-global-account
- `raw/doc_*.txt` does not cover this endpoint; the local docs are silent here.

**Catch that matters more for S1:** the simulator has **no field for the payer's bank account** (no account number, IBAN, or routing). The read side lists `payer.bank_account` (`GET /api/v1/deposits`, https://www.airwallex.com/docs/api/core_resources/deposits/list.md), but `raw/doc_deposit_wh.txt` warns:
> "Depending on the Global Account financial institution & payment method, the availability of deposit details (e.g. payer name, payer bank account number etc.) will vary."

So S1's "refund only to the account the deposit came from" **cannot be built from simulated deposit data alone**. Assume `payer.bank_account` is empty or synthetic in sandbox. The refund beneficiary has to come from a customer-master fixture, gated on a match against the deposit's `payer_name` and `payer_country`, and labelled that way on screen.

### b) Do the current `deposit.*` webhooks fire for simulated deposits?
**Verdict: NOT DOCUMENTED. Treat it as unknown and build on polling.** **UNTESTED (docs only).**
- The current events exist: `deposit.pending`, `deposit.settled`, `deposit.rejected`, `deposit.reversed`. `raw/doc_deposit_wh.txt`:
  > "The following events cover both bank transfer and direct debit deposits"
- `ga.new` is the only one limited to old versions. `raw/doc_deposit_wh.txt`:
  > "the deposit webhook applies only to API version 2025-02-14 and before"

  That confirms the DECISIONS.md correction to F3.
- The simulation guide promises webhooks only in general terms:
  > "Triggering webhook event notifications for Global Accounts"

  The link on that line goes to the **Global Accounts** webhook page (`global_account.active`/`closed`/`failed`, plus legacy `ga.new`), **not** the deposits webhook page. No official page says `deposit.*` or `balance.ga.top_up` fire for a simulated deposit. Source: https://www.airwallex.com/docs/developer-tools/sandbox-environment/deposits/simulate-deposits-to-your-global-account
- The hackathon dev lab lists its "Expected events" as `payout.transfer.paid`, `payout.transfer.failed`, `payout.transfer.cancelled`, `issuing.transaction.succeeded`, and `issuing.transaction.failed`, with **no deposit events**. Source: https://airwallexdev.com/
- **Design consequence:**
  - Primary path: poll.
  - Webhooks are an optimisation, never a dependency.
  - The same guide names the read paths that do surface simulated deposits:
    > "Retrieving deposits via Get Global Accounts transactions …, Get list of financial transactions …, and Get balance history"

    It does **not** name `GET /deposits`. So poll `GET /global_accounts/{id}/transactions` first, and treat `GET /deposits` as unverified for simulated deposits.
  - `GET /deposits` has no status or Global Account filter, only `from_created_at`, `to_created_at`, `page_num`, and `page_size`, so filter client-side.

### c) Can a bank-transfer deposit reversal be simulated, or must it live in our own ledger?
**Verdict: it can't be simulated for bank-transfer (Global Account) deposits. It must live in our own ledger, labelled as simulated.** **UNTESTED (docs only).**
- The simulation reference scopes reverse, settle, and reject to Direct Debit only:
  > "The Direct Debit deposit simulation APIs allow you to transition Direct Debit deposit statuses in the sandbox environment."
  > "Reverse a Direct Debit Deposit — `POST /api/v1/simulation/deposits/{deposit_id}/reverse`"

  The endpoint page says:
  > "Creates a new direct debit deposit in the `SETTLED` state with an amount that offsets the original amount … and also deactivates the Linked Account."
  > "`deposit_id` … Unique identifier of the direct debit deposit."

  Sources: https://www.airwallex.com/docs/api/simulation/deposits.md, https://www.airwallex.com/docs/api/simulation/deposits/reverse.md
- The bank-transfer status machine has no reversed state. *Bank transfer deposit statuses* lists only `PENDING`, `SETTLED`, and `REJECTED` ("Deposit was rejected and the funds will be returned to the original source"). Sources: https://www.airwallex.com/docs/global-treasury/receive-funds/receive-bank-transfers-to-global-accounts/bank-transfer-deposit-statuses.md and `raw/doc_deposit_wh.txt` (same table).
- `REVERSED` does appear in the `GET /deposits` status enum and the `deposit.reversed` webhook. Read that as applying to Direct Debit, since the bank-transfer status page omits it.
- Why the Direct Debit route doesn't help S1: Direct Debit models pulling money from *our own* Linked Account, not a customer paying an invoice. Using it would misrepresent the story.
- **The API-real alternative:** the simulator *can* create a deposit directly as `REJECTED`. Use that for the "cash you thought you had isn't there" beat (see §3).

### d) Can one sandbox account hold several Global Accounts?
**Verdict: YES in production per the docs. Sandbox limits are undocumented.** **UNTESTED (docs only).**
- *Treasury concepts*:
  > "You can create multiple Global Accounts programmatically without complex application processes or approval delays."
  > "when funds are received in AUD via direct debit from Linked Accounts or different Global Accounts; all those funds will be settled into the Wallet"

  The second quote implies several Global Accounts in the **same currency** are allowed. Source: https://www.airwallex.com/docs/global-treasury/understanding-global-treasury/treasury-concepts.md
- The API supports it in shape: `POST /global_accounts/create` takes a `nick_name` (example: "GBP in UK for Subsidiary Company ABC"), and `GET /global_accounts` returns a list. Source: https://www.airwallex.com/docs/api/core_resources/global_accounts/create.md
- The hackathon guide only *advises* reuse:
  > "List your Global Accounts first and reuse one … Create one only if the list is empty"

  Source: https://airwallexdev.com/guide
- I found no documented per-account or sandbox cap.
- **Caveat for S1:** Global Accounts are conduits, and all funds pool into one wallet balance per currency:
  > "Global Accounts only act as conduits … and do not hold balances"

  Per-customer Global Accounts would help *matching* (the `global_account_id` on a deposit identifies the payer). They would not separate balances.

---

## 2. Go / no-go on S1's 3-week solo scope
**GO, with a re-cut demo. Confidence: medium.** That is one notch below my medium-high for S2.

**Why GO:**
- Every money-moving step in S1 uses documented, no-enablement sandbox APIs:
  - deposit simulation with `reference`
  - Global Account transactions
  - beneficiaries
  - transfers plus status simulation
  - FX quotes and conversions
  - financial transactions
- The core value (matching, the evidence flip, the refund lock, the audit trail) is deterministic code we control.

**Why not higher:**
- Two of S1's three beats, as written, lean on things the sandbox doesn't do: bank-transfer reversal (c) and payer bank details for refund-to-source (a).
- Its event path (b) is undocumented.
- S1 also has more custom domain logic than S2 (matching tolerances, withholding-tax treatment, write-off rules), and that logic is where solo time goes.

**Conditions for GO:**
1. **Rework beat 3** so it doesn't rely on an API reversal (see §3).
2. **The refund beneficiary comes from a customer-master fixture**, not from the deposit, and the screen says so.
3. **Build the event path on polling.** Webhooks are a bonus.
4. **Run the day-1 spike** (§7) on Sun 25 Oct. If the refund transfer path or reading simulated deposits fails by **Wed 28 Oct**, pivot to S2. About 60% of the plumbing is shared (§5), so a pivot costs roughly 2 days, not a restart.

---

## 3. Demo beats: keep, change, cut, or stub

| Beat (shortlist) | Call | What changes |
|---|---|---|
| 1. $9,700 vs $10,000, then a withholding-tax PDF flips "chase $300" to "close + book a tax receivable" | **KEEP (API-real deposit)** | Simulate the deposit with `amount: 9700`, `payer_name`, and `reference: "INV-1042"` (supported per a). The remittance PDF is a synthetic fixture read by the LLM; the arithmetic happens in code |
| 2. Duplicate refunded once, second click blocked, new-IBAN email refused | **KEEP, with a stubbed beneficiary source** | The duplicate is a second simulated deposit with the same reference and amount. The refund is a real `transfers/create` to a beneficiary built from the **customer-master fixture**, allowed only when the deposit's `payer_name` and `payer_country` match. A deterministic `request_id` plus a lock enforce one refund per deposit. The state machine keeps listening after `PAID` (`raw/doc_tstatus.txt`: PAID can still go to FAILED) |
| 3. Settled deposit reversed, invoice reopens, surplus EUR converts | **CHANGE** | Replace the API reversal with a **simulated `REJECTED` deposit**, which is API-real. A remittance email claims payment and the matching deposit arrives `REJECTED`. The invoice stays open, the cash isn't counted, a chase is drafted, and the EUR surplus is recomputed smaller before **one** conversion on a single-use quote. A reversal-after-settle can survive only as an **own-ledger event, labelled "simulated in our ledger: the sandbox can't reverse bank-transfer deposits"**, and only if week 3 has slack |
| Split-deposit opener (one receipt, two invoices, $37.85 gap written off) | **KEEP as the seed** | Cheap: pure matching logic |
| Early-pay discount deadline flip | **CUT to stretch** | It adds a rule family without a new API |
| Payment links and Billing invoices | **CUT** | Unverified enablement; shortlist already marked them stretch |
| One Global Account per customer | **CUT to two currency Global Accounts** (USD and EUR) | Probably allowed (d), but it adds setup and isn't needed for the story. Match on `reference` plus `payer_name` |
| Two-approver maker-checker | **KEEP, minimal** | One config flag plus a second approver role; show it once on the refund |
| `verify_account` name check | **CUT** | UK Confirmation of Payee needs enablement on request (off-board contact) |
| Webhooks | **STUB as optional** | Poll `GET /global_accounts/{id}/transactions` every few seconds during the demo. Add the HMAC receiver only if day-1 shows deposit events fire |
| `GET /financial_transactions` tie-out | **KEEP, with a fallback** | If rows lag, tie out from the deposit, transfer, and conversion objects and say so |
| Accounting system or ERP | **STUB** | CSV export only |
| Chase emails and supplier notices | **STUB** | Drafted in the UI, never sent |

---

## 4. Trimmed week-by-week plan (build window: Sun 25 Oct, 10:00 AM IST to Fri 13 Nov, 11:59 PM IST)

**Before 25 Oct: design only, no code (F2).**
- Fixtures spec: about 8 invoices, 4 customers, a customer master with bank details, a remittance PDF, 2 emails.
- Matching rules table, approval matrix, and screen sketch.

**Week 1 (Sun 25 – Sat 31 Oct): rails, plus spike, plus pivot gate.**
- Day 1: sandbox spike (§7).
- Typed client (30-minute token refresh, backoff for 20 req/s) for:
  - deposit simulation
  - Global Account transactions, deposits, and balances
  - beneficiaries (schema, validate, create)
  - transfers plus transitions
  - FX rates, quotes, and conversions
  - financial transactions
- SQLite ledger (invoices, receipts, applications, refunds, audit) with deterministic `request_id` and locks.
- Poller.
- **Gate, Wed 28 Oct:** reading a simulated deposit and a refund that reaches `PAID` must both work end to end. Otherwise switch to S2.

**Week 2 (Sun 1 – Sat 7 Nov): brain and controls.**
- Matching engine: exact, split, in-tolerance write-off, short pay, duplicate, unknown payer leading to hold.
- LLM extraction of the remittance PDF and emails into a typed schema with code validation. Emails are treated as untrusted data.
- Decision engine with old-versus-new plan diffs.
- Approval service bound to amount, currency, counterparty, invoice ids, and evidence hashes, plus maker-checker.
- Refund guard: customer-master only, one per deposit, capped at the overpaid amount.
- Rejected-deposit handling.
- Surplus-FX calculation with a buffer for upcoming EUR bills.
- **Exit:** all three beats run headless from one command, with a reset.

**Week 3 (Sun 8 – Fri 13 Nov): demo and ship.**
- One-page UI: receipts queue, decision card with plan diff, approval drawer, audit log, CSV export.
- Contract tests against the sandbox.
- Small eval set (about 20 remittance docs, including prompt-injection attempts).
- README, `.env.example`, public repo.
- **Record the video by Wed 11 Nov.**
- **Submit Thu 12 Nov**, a day ahead of the 11:59 PM IST deadline on 13 Nov.
- Own-ledger reversal beat only if everything else is done by Tue 10 Nov.

---

## 5. S2 comparison: is it the safer fallback?
**Yes. S2 is the safer build and the right fallback.**
- **Sandbox fidelity:** every S2 beat is API-real and documented.
  - Payee change: beneficiary create plus our hold logic.
  - Returned payment: `POST /simulation/transfers/{id}/transition` takes SENT, then FAILED with a `failure_type` (`raw/doc_failure_types.txt`).
  - Cash arrives: deposit simulation, where the balance appears immediately per the guide.

  S2 doesn't depend on (a), (b), or (c). Its only shared unknown is `GET /financial_transactions` latency, which has the same fallback.
- **Confidence:** S2 is medium-high; S1 is medium.
- **Weakness:** originality. Kits 1 and 3 script two of S2's three beats, so it wins only on the payee-change lock and per-invoice reconciliation. S1 sits in the guide's explicit whitespace ("we have not written kits for them").
- **Pivot cost from S1 to S2 is low.** These pieces carry over unchanged:
  - auth client
  - beneficiary and transfer modules
  - transfer state machine (CANCELLED-not-FAILED, PAID-not-final)
  - FX quote and convert
  - idempotency and locks
  - approval binding
  - audit log
  - financial-transactions tie-out
  - UI shell

  Roughly 60% shared, so the Wed 28 Oct gate can switch tracks without losing week 1.
- **Recommendation:** build S1 with S2 as the named fallback. Design week-1 modules to be product-neutral so either can sit on top.

---

## 6. Sources
**Local**
- `raw/doc_deposit_wh.txt` (deposit events; legacy `ga.new` version limit; bank-transfer status table; "availability of deposit details … will vary")
- `raw/doc_failure_types.txt` (transfer transition simulation, failure types)
- `raw/doc_tstatus.txt` (PAID can go to FAILED)
- `board/ROUND1-SHORTLIST.md`, `board/DECISIONS.md`

**Official Airwallex (fetched 8 Oct 2026)**
- Simulation, Deposits overview: https://www.airwallex.com/docs/api/simulation/deposits.md
- Create a Global Account Deposit: https://www.airwallex.com/docs/api/simulation/deposits/create.md
- Reverse a Direct Debit Deposit: https://www.airwallex.com/docs/api/simulation/deposits/reverse.md
- Simulate deposits guide: https://www.airwallex.com/docs/developer-tools/sandbox-environment/deposits/simulate-deposits-to-your-global-account
- Bank transfer deposit statuses: https://www.airwallex.com/docs/global-treasury/receive-funds/receive-bank-transfers-to-global-accounts/bank-transfer-deposit-statuses.md
- List all Deposits: https://www.airwallex.com/docs/api/core_resources/deposits/list.md
- Global Accounts API: https://www.airwallex.com/docs/api/core_resources/global_accounts.md · Create: https://www.airwallex.com/docs/api/core_resources/global_accounts/create.md
- Treasury concepts: https://www.airwallex.com/docs/global-treasury/understanding-global-treasury/treasury-concepts.md
- Hackathon guide: https://airwallexdev.com/guide · Dev lab (expected webhook events): https://airwallexdev.com/
- Airwallex Docs MCP (public, no auth): `https://mcp.sandbox.airwallex.com/docs`, `search_public_docs`. It returned the simulation guide and the treasury-concepts text quoted above.

---

## 7. What's untested, and the day-1 spike (Sun 25 Oct, needs sandbox credentials Vedant creates)
Every item is UNTESTED; there are no credentials on the box. Run these in this order. All are read or sandbox-simulation calls.
1. **(a)** Simulate a deposit with `reference`, `payer_name`, and `payer_country`. Read it back via `GET /global_accounts/{id}/transactions`, `GET /deposits`, and `GET /financial_transactions`. Record which fields appear, especially `reference` and whether `payer.bank_account` is empty.
2. **(b)** Subscribe to `deposit.*` and `balance.ga.top_up` in the sandbox web app through a tunnel. Simulate SETTLED, PENDING, and REJECTED deposits and log which events arrive and how fast.
3. **(c)** Call `POST /simulation/deposits/{id}/reverse` on a **Global Account** deposit id and expect a 4xx. Record the error, which confirms the own-ledger decision.
4. **(d)** Create a second USD Global Account and a EUR (DE) one. Confirm both are listed and that a deposit to each pools into the wallet balance.
5. Refund path: create a beneficiary from fixture details, then a transfer, then transitions SENT, PAID, and FAILED. Confirm the post-PAID failure is visible.
6. Measure `GET /financial_transactions` latency for deposit, payout, conversion, and fee rows.
7. Check whether a `PENDING` simulated deposit can later be moved to SETTLED. The docs show no Global Account settle endpoint (settle is Direct Debit only), so expect no.

---

## Round 1 addendum: payer details and verify_account
**Written:** Thu 8 Oct 2026, ~7:25 PM IST. **Status of every answer: CONFIRMED IN DOCS ONLY or NOT AVAILABLE. Nothing is CONFIRMED IN SANDBOX.** Rechecked env vars and files under this repo: still no sandbox credentials, so no sandbox call was made. Docs MCP (`https://mcp.sandbox.airwallex.com/docs`, no login) and the live API reference were re-fetched today.

### Q1. Do deposits carry payer bank details usable for refund-to-source?
**Split verdict: simulated deposits NOT AVAILABLE for account details; real deposits CONFIRMED IN DOCS ONLY, and no field is guaranteed.**

#### (i) Simulated deposits (`POST /api/v1/simulation/deposit/create`): NOT AVAILABLE
Re-verified against the current API reference and the Docs MCP. The request body accepts only:
> "`payer_bankname` (string, optional) Name of the bank that the deposit is made from."
> "`payer_country` (string, optional) Payer country code of the transaction (2-letter ISO 3166-2 country code)."
> "`payer_name` (string, optional) Name of the payer making the deposit."
> "`reference` (string, optional) Description of the deposit."

The 201 response echoes `payer_name`, `payer_country` and `reference` only. There is **no account number, IBAN, sort code, routing number, BIC or SWIFT field** on either side. `payer_bankname` is a free-text bank name, not a code, and it isn't even in the response schema. Source: https://www.airwallex.com/docs/api/simulation/deposits/create.md. The Docs MCP returned the same field list and the guide example, which sends only `payer_bankname`, `payer_country`, `payer_name` and `reference` (https://www.airwallex.com/docs/developer-tools/sandbox-environment/deposits/simulate-deposits-to-your-global-account).

**A simulated deposit cannot carry payer account details at all.** It can carry payer name, payer country, a free-text bank name, and a reference.

#### (ii) Real deposits: CONFIRMED IN DOCS ONLY, conditional, nothing guaranteed
`GET /api/v1/deposits` and `GET /api/v1/deposits/{id}` return an optional `payer` object. The guide states the rule:
> "For a bank transfer deposit, the payer's details may vary depending on factors such as the country and transfer method (Local Clearing System or SWIFT) of the deposit received."
> "The nested objects are mutually exclusive"

and the retrieve page:
> "Depending on the Global Account financial institution & payment method, the availability of deposit details (e.g. payer name, payer bank account number etc.) will vary."

Sources: https://www.airwallex.com/docs/global-treasury/receive-funds/receive-bank-transfers-to-global-accounts/retrieve-your-deposits.md, https://www.airwallex.com/docs/api/core_resources/deposits/retrieve.md, https://www.airwallex.com/docs/api/core_resources/deposits/list.md. Every field below is marked **optional**. None is guaranteed.

The guide's mapping of `payer.bank_account` (one of these, never several):

| Rail | Object (`bank_account.type`) | Documented payer fields |
|---|---|---|
| Local AUD | `AU_BSB` | `au_bsb.bsb`, `au_bsb.account_number`, plus `name` and `institution` (name, swift_code, country_code) |
| AUD PayID | `AU_PAYID` | `au_payid.payid`, `account_identifier_type`, `account_number`, `bsb` |
| Faster Payments / local GBP | `GB_SORT_CODE` | `gb_sort_code.account_number`, `gb_sort_code.sort_code` |
| ACH USD | `US_ACH` | `us_ach.account_number`, `us_ach.ach` (routing number) |
| Fedwire USD | `US_WIRE` | `us_wire.account_number`, `us_wire.wire` (routing number) |
| SEPA EUR (local) and SWIFT | `IBAN` | `iban.iban`. The guide: "`iban` … IBAN information on this deposit received via local clearing system (e.g. SEPA) and SWIFT" |
| SWIFT (and some local) | `SWIFT_CODE` | `swift_code.swift_code`, `swift_code.account_number` |
| Incomplete data, any rail | `PARTIAL` | "`partial` … Only partial bank account information is available on this deposit": `account_number`, `account_routing_type1/2`, `account_routing_value1/2` |
| Also in the schema, not in the demo corridors | `BR_BANK_CODE`, `CA_INSTITUTION_NUMBER`, `CN_CNAPS_CODE`, `DK_BANK_CODE`, `HK_BANK_CODE`, `JP_BANK_CODE`, `KR_BANK_CODE`, `MX_BANK_CODE`, `NZ_BANK_CODE`, `PH_BANK_CODE` | account number plus that country's routing code |

Common to all, still optional: `payer.name`, `payer.country_code`, `bank_account.name` (account holder), `bank_account.institution` (bank name, SWIFT code, country).

**Other read paths, and what they don't carry:**
- `GET /api/v1/global_accounts/{id}/transactions` carries only `payer_name` and `payer_country`, both optional. No account object. Source: https://www.airwallex.com/docs/api/core_resources/global_accounts/transactions.md
- `deposit.*` webhook payloads carry the same `payer` object as `GET /deposits` when it's a bank transfer. The published `deposit.pending` example (type `BANK_TRANSFER`) includes `payer.name`, `payer.country_code`, `bank_account.au_bsb` (bsb + account_number), `bank_account.name` and `institution`. The published `deposit.settled`, `deposit.rejected` and `deposit.reversed` examples are `DIRECT_DEBIT` and carry **no payer object at all**, only `funding_source_id`. Source: https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events/deposits.md
- `GET /api/v1/financial_transactions` has no payer fields. A row links back through `source_id` and `source_type` (`DEPOSIT`, `PAYOUT`, `CONVERSION`, `FEE`, …) and carries `amount`, `fee`, `net`, `currency`, `description`, `client_rate`. Source: https://www.airwallex.com/docs/api/finance/financial_transactions

**Correction to verdict (b) above.** The sandbox deposits page now says, explicitly:
> "Test if your subscribed deposits webhook events are received and managed in your integration."

and links the deposits webhook page. Source: https://www.airwallex.com/docs/developer-tools/sandbox-environment/deposits.md. So deposit webhooks firing for simulated deposits is **CONFIRMED IN DOCS ONLY** as a supported test, not merely undocumented. Still untested, and still not a demo dependency until the day-1 spike shows which events actually arrive.

### Q2. Does `POST /api/v1/beneficiaries/verify_account` work in the sandbox for SEPA EUR?
**Verdict: NOT AVAILABLE as a documented sandbox feature. The SEPA EUR coverage itself is CONFIRMED IN DOCS ONLY, with no enablement gate.**

**Coverage (docs):**
> "Local EUR accounts from SEPA (Single Euro Payments Area) countries can be verified via the Verification of Payee (VoP) scheme, facilitated by the European Payments Council."

Required fields are `iban` (country code one of AT, BE, BG, CH, CY, CZ, DE, DK, EE, ES, FI, FR, GB, GG, GI, GR, HR, HU, IE, IS, IT, LI, LT, LU, LV, MC, MQ, MT, NL, NO, PL, PM, PT, RO, SE, SI, SK, SM, YT) and `account_name`. Supported results: `VERIFIED` with `FULL_MATCH`, `PARTIAL_MATCH` or `NOT_MATCHED`; `CANNOT_VERIFY` (which "covers the scenario where the IBAN provided is invalid. A standalone `INVALID` code is not available."); `EXTERNAL_SERVICE_UNAVAILABLE`. The resolved name comes back "only when the name match result is one of `FULL_MATCH` or `PARTIAL_MATCH`". Source: https://www.airwallex.com/docs/payouts/beneficiaries/verify-a-beneficiary-account/europe.md

The supported-methods table lists Europe (SEPA Instant / SEPA, VoP, name matching: Yes) with **no "enabled on request" caveat**. Source: https://www.airwallex.com/docs/payouts/beneficiaries/verify-a-beneficiary-account.md

**Contrast, UK:**
> "UK Confirmation of Payee (CoP) is enabled on request. If you are building a custom CoP user interface, Airwallex and our local partners must approve your user-facing messaging before go-live."

Source: https://www.airwallex.com/docs/payouts/beneficiaries/verify-a-beneficiary-account/united-kingdom.md. UK CoP is therefore off the table for this hackathon: using it needs an access request, which is off-board contact.

**Response shape** (https://www.airwallex.com/docs/api/payouts/beneficiaries/verify_account.md):
> "`code` … `VERIFIED` … `INVALID` … `CANNOT_VERIFY` … `EXTERNAL_SERVICE_UNAVAILABLE`"
> "`details.account_name_match_result` … `details.resolved_account_name` … `details.resolved_bank_name`"

**Sandbox and test values: NOT AVAILABLE.** The cURL example uses the sandbox host, but no page describes sandbox behaviour, a mock, or test values. A Docs MCP search for test numbers that simulate `FULL_MATCH`, `PARTIAL_MATCH` and `NOT_MATCHED` returned only unrelated direct-debit test pages (ACH, Bacs, SEPA Direct Debit, EFT PAD). The sandbox payouts page lists transfer-status simulation and transfer webhooks, and doesn't mention `verify_account` (https://www.airwallex.com/docs/developer-tools/sandbox-environment/payouts.md). So there is no documented way to make the demo show match, close match and no match on demand.

### What this means for S1 vs S2
- **S1's refund-to-source beat cannot be real in this demo. It must be a fixture.** The demo runs on simulated deposits, and a simulated deposit has no payer account, IBAN or routing code to refund to. The refund beneficiary has to come from our customer file, allowed only when the deposit's `payer_name` and `payer_country` match that customer, and the screen must say so. In production the schema does support refund-to-source (SEPA via `iban`, GBP via `gb_sort_code`, USD via `us_ach`/`us_wire`, SWIFT via `swift_code` or `iban`), but only as a best-effort rule: if `payer.bank_account` is missing or `PARTIAL`, the agent holds. That is an adoption story, not a demo beat. The reversal beat is unchanged: bank-transfer reversals still can't be simulated.
- **S2's payee-change lock can only be our own rule plus a human callback.** A real SEPA EUR name check is documented and, unlike UK CoP, needs no enablement request, so it's a legitimate day-1 spike. But with no documented sandbox behaviour and no test values, the demo cannot depend on it: a judge can't be shown full match, close match and no match on cue, and a live call to real VoP from the sandbox may simply fail or hit a real scheme. The lock that ships is: changed bank details freeze the payout, `POST /beneficiaries/validate` proves the details are well-formed, and a person confirms out of band. `verify_account` sits behind a flag and is dropped the moment it doesn't return a usable result.
- **Net:** these answers don't flip the ranking. They confirm S1's signature beat is partly staged, and they cap S2's signature beat at a rule we enforce ourselves. S2 remains the safer build; S1 remains the better whitespace story, with its refund shown honestly as fixture-backed.
