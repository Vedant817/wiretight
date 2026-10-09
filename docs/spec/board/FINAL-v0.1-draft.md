# Wiretight: FINAL build document (draft)

> **Wiretight: supplier payouts that can't be quietly redirected.**
> *New or changed bank details stay locked until a second person confirms them by callback.*

---

## 0. Status

| Field | Value |
|---|---|
| Document | `board/FINAL.md`, **draft v0.1** (Round 3 integration) |
| Written | Thu 8 Oct 2026, ~7:45 PM IST |
| Authority | `board/DECISIONS.md` (D0–D9 and all R2-* entries) overrides every other source. Then `board/round2/*.md`, then `board/SPEC-v1.md`, then the research pack (`01-real-world-problems.md`, `04-sources.md`). Any conflict this draft resolved on its own is listed in **Appendix A, Integration notes**. |
| Next step | **Round 4 red-team** (Judge + Compliance & Risk + Staff Engineer) on this draft, then fix and lock (see §14.4). |
| Audience | (1) Vedant; (2) Grok Bot, who writes the master build prompt from this file; (3) the coding agent that builds the whole project from it. Everything the builder needs is inline. No "see other file" dependencies. |
| Testing status | **Nothing in this document has been run against a live Airwallex sandbox.** No account or keys exist yet (OPEN-3). Every API behaviour is from the Airwallex docs or the hackathon guide. Anything that needs a live check is marked **⚠ unverified** and appears in the day-1 table (§9.5). |

### 0.1 Key dates (IST)

| Date | Event |
|---|---|
| Mon 5 Oct 2026, 9:00 PM | Registration & idea phase opened |
| **Fri 23 Oct 2026, 11:59 PM** | **Idea application deadline** (target: submit by Wed 21 Oct) |
| **Sun 25 Oct 2026, 10:00 AM** | Accepted teams notified; **build phase starts**. First project commit allowed from this moment. |
| Fri 30 Oct | Checkpoint 1: live money path in the sandbox |
| Thu 5 Nov | Checkpoint 2: full demo headless, with tie-out |
| Sat 7 Nov | Checkpoint 3: full demo through the UI |
| Wed 11 Nov | Feature freeze |
| Thu 12 Nov | Video recorded, package built, Vedant submits |
| **Fri 13 Nov 2026, 11:59 PM** | **Submission deadline** (internal last-resort target 6:00 PM IST). Fri 13 is buffer only. |
| Sun 15 Nov | Finalists selected |
| Thu 19 Nov | Demo Day, San Francisco (remote optional) |

### 0.2 ⚑ Actions only Vedant can take

> **Before the idea deadline**
> 1. **Check the login-gated HackerEarth rules tab** (OPEN-1 / OPEN-4). Look for the clause "Your hack must be developed entirely during the Hackathon duration" (standard HackerEarth boilerplate on other events). Also screenshot every **idea-form field and its character limit**, so the right block from §3 can be pasted into each one.
> 2. **Submit the idea application** using the paste-ready text in §3. Deadline **Fri 23 Oct, 11:59 PM IST**. Aim for **Wed 21 Oct**. Fill in the one bracketed "status on the day" line truthfully.
> 3. **Create the Airwallex sandbox account and API keys before Sun 25 Oct** (sign-up at `sandbox.airwallex.com`, free, no card). Name the business exactly `Sandbox Business` or `New Business Sandbox` so KYB auto-approves. Copy the Client ID and API key from **Account > Developer > API keys**. Keep the keys out of chat and out of any repo. The coding agent needs them on Sun 25 Oct for the day-1 spike.
>
> **Standing rules (already in force)**
> - **No project code and no repo commits before Sun 25 Oct, 10:00 AM IST.** Before then: design documents and throwaway spikes only, kept **outside** the project repo (e.g. `~/scratch/wiretight-spikes/`). Findings (notes) carry over; spike code does not.
> - **Nobody outside the board has been contacted**: no devhelp@ email, no Discord, no partner Slack, no HackerEarth support. Any such contact is Vedant's decision.
> - Nothing has been submitted, registered or purchased by any agent.
>
> **Later (build phase)**
> - Optional: configure a webhook URL in the sandbox web app (Settings > Developer > Webhooks) if the day-1 spike shows webhooks are worth it. Polling works without it.
> - Record the video voiceover (the coding agent prepares the script, the replay mode and the seeded run).
> - Submit on HackerEarth (zip + public repo link + video) on **Thu 12 Nov**. Agents never submit.
> - Rotate the sandbox API key before Demo Day; revoking it in the web app is also the ultimate stop for the kill switch (§4.9).

---

## 1. The chosen idea

| | |
|---|---|
| **Name** | **Wiretight** (always one word; never "Wire Tight" or "WireTIGHT") |
| **Title** | Wiretight: supplier payouts that can't be quietly redirected |
| **Sub-line** | New or changed bank details stay locked until a second person confirms them by callback. |
| **Descriptive sub-label (UI)** | "pay-run lock" (on the incident view) |
| **The rule the product enforces** | No payout reaches a bank account that a human hasn't confirmed and signed off on exact terms. |
| **First buyer** | The **finance lead or founder-operator at a small company (SMB)** who pays overseas suppliers from **their own Airwallex account**. The fraud loss lands on the payer, so the payer owns the budget. |
| **Year-2 channel (not the first buyer)** | Bookkeeping and fractional-CFO firms. The build is single-entity by design, and a firm releasing a client's money to changed bank details carries liability, so firms adopt after their clients trust the lock. |
| **Prize lane** | **Founder's Choice** (open category; Judges' Choice is also open and we stay eligible). **Not** Visa (agent-checkout tooling with merchant prerequisites, wrong shape for B2B payouts). **Not** Metal (cut; the landing page says "L1 blockchain" while earlier plans said "L2 testnet", unconfirmed). |
| **Track field** | Treasury & Ops, original idea: payee-change fraud control plus landed-payment reconciliation. Neither is a starter kit. Borrows kit 3's no-double-pay discipline. |

### 1.1 One-paragraph pitch
Small finance teams pay overseas suppliers every week from an inbox, a spreadsheet and a bank portal, and a single "we've changed banks" email is enough to redirect a payment. Wiretight runs the weekly supplier payment run on Airwallex with one rule enforced in code: **no payout goes to bank details a human hasn't confirmed and signed off on exact terms.** Code, not the model, parses bank details, finds duplicates and plans payments across USD, EUR and GBP without breaching a cash reserve. Every sign-off is a passkey signature over a hash of the exact payee, account, amount, currency and evidence, so if anything changes after sign-off, the signature stops matching and the executor refuses to pay. New or changed bank details need a callback by a separate ops person to a contact that predates the change, a cooling-off period, two sign-offs and a capped first payment. The same lock applies when a supplier sends a genuine new account after a payout bounces, because recovery is where redirection fraud hides. Every payout is tracked until it lands (PAID is treated as provisional), then tied out against Airwallex's financial transactions. Teams start in shadow mode, where Wiretight moves no money and reports what it would have caught.

**The story judges should remember (CEO):** two days before a €7,500 bill is due, a "we've changed banks" email arrives. Wiretight voids the sign-off and freezes that payee, pays everyone else without touching the reserve, and when the real supplier's payout comes back because its account closed, the supplier's new account goes through the same lock before anything is paid again.

**Who signs vs what they sign (answer to "why not my existing approvals?"):** approval workflows decide *who* signs. Wiretight decides *what they are signing*: is this the same bank fingerprint as the last final payment, is the bill unpaid, does the reserve hold, and has anything changed since sign-off. It sits in front of a customer's existing approval chain as pre-approval screening, not as a second queue.

### 1.2 Why this beat the shortlist
The Round 1 shortlist had three ideas. **S3 Float** (multi-currency cash placement) scored 5.20 and was dropped: it reads as kit 1 without the payouts and has thin evidence and shallow API use. **S1 Ledgerline** (receivables cash application) scored 7.35 against 7.55 for this idea (then called "PayRun Warden"), and the Judge made the choice depend on one sandbox fact: whether simulated deposits carry payer bank details. Per the Airwallex docs (not a live test), the deposit simulator accepts only `payer_name`, `payer_country`, `payer_bankname` and `reference`, with no account identifiers, and bank-transfer deposit reversal can't be simulated (reversal is Direct Debit only). That left two of S1's three demo beats running on fixtures or our own ledger rather than on Airwallex. This idea needs no special access (sandbox only, starter-kit 1–4 territory), had the Staff Engineer's higher feasibility rating (medium-high vs medium), and was projected at about 8.45 once re-centred on the payee-change lock. The Round 2 Judge scored the base spec 7.75 and set out the path past 8.5 that this document implements: lead with the lock, show it fire twice, enforce the callback in code, sign with passkeys, and fix the stats.

---

## 2. Evidence

**Rules for this section:** every number below was read from its primary source by a board member (Banking Domain citation audit, Round 2), unless marked otherwise. Nothing is rounded up or generalised. **The application text (§3) uses at most two of these: AFP 2026 74% and APQC 1.5%.**

### 2.1 Pain table

| Pain | Accurate statement (scope included) | Source, year | URL | Status |
|---|---|---|---|---|
| Redirected payments / business email compromise | **74%** of **US organisations** were affected by business email compromise (BEC) in 2025. Survey of 465 US treasury and finance practitioners. | AFP 2026 Payments Fraud and Control Survey (press release) | https://www.prnewswire.com/news-releases/over-75-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags-302738857.html | Verified [V] |
| Vendor impersonation is rising | Vendor imposter fraud was cited by **45%** of organisations, **an 11-percentage-point increase** (2024 data). | AFP 2025 Payments Fraud and Control Survey (press release) | https://www.financialprofessionals.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024 | Verified [V] |
| BEC losses | **$2,770,151,146** in BEC losses reported to the FBI's IC3 in 2024. | FBI IC3 2024 Internet Crime Report | https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf | Verified by Banking Domain in Round 2 (`04-sources.md` still labels it [S]) |
| Paying twice | Median **1.5% of disbursements** are duplicate **or erroneous** payments (APQC Open Standards Benchmarking, cross-industry, sample 1,686). Not "duplicates" alone. | APQC | https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number | Verified [V] |
| The control Wiretight enforces | The FBI advises: "Use secondary channels and/or two-factor authentication to verify requests for changes in account information." The IC3 BEC page says: "Use secondary channels or two-factor authentication to verify requests for changes in account information with the intended recipient." | FBI IC3 PSA I-091124-PSA (11 Sep 2024); IC3 BEC page | https://www.ic3.gov/PSA/2024/PSA240911 · https://www.ic3.gov/CrimeInfo/BEC | Verified [V] (both pages re-opened 8 Oct 2026 for this draft) |
| AI is rarely used against payments fraud | Just **17%** of organisations use AI to combat payments fraud (US, AFP 2026). | AFP 2026 (same release) | (AFP 2026 URL above) | Verified [V] |
| "PAID" isn't final | Airwallex documents that a transfer can move to FAILED **after** PAID, and says to keep listening for `payout.transfer.failed` until arrival is confirmed. Failed transfers are automatically cancelled within seconds. | Airwallex docs | https://www.airwallex.com/docs/payouts/transfers/create-a-transfer/transfer-statuses.md · https://www.airwallex.com/docs/payouts/transfers/manage-transfers/handle-failed-transfers.md | Docs [V]; sandbox simulation of PAID→FAILED ⚠ unverified (U1) |
| Stuck cross-border payments are expensive (bank-side) | Financial institutions spend **$1.6B a year** investigating held-up payments; investigations of delays caused by missing information take **5–10 working days**. Counterweight from the same release: **90%** of transactions over Swift reach end banks within an hour. This is a bank cost, not an SMB cost. | Swift press release | https://www.swift.com/news-events/press-releases/swift-solution-managing-cross-border-payments-investigations-could-save-industry-millions-operational-costs | Verified [V]; context only |
| AP processing cost (enterprise benchmark) | **$9.84** per invoice and **8.2 days** cycle time are the **average across all respondents**; "All Others" (not best-in-class) are **$12.42 / 13.5 days**. Sample of 204, **54% with revenue over $1B**. Not a manual-AP or SMB figure. | Ardent Partners, State of ePayables 2025 | https://www.bottomline.com/cdn/1517/5157/1685/Ardent_Partners_-_State_of_ePayables_2025_-_Bottomline_-_FINAL.pdf | Verified [V]; context only |
| Cash forecasting (context for the reserve floor) | Cash or liquidity forecasting is among the **five most challenging tasks**, cited by **62%** of treasury professionals (**60%** at organisations under $1B). It is a top-five list, not "the #1 challenge". | AFP 2025 Treasury Benchmarking Survey | https://7185359.fs1.hubspotusercontent-na1.net/hubfs/7185359/Research%20Surveys/SURVEYS/2025%20AFP%20Treasury%20Benchmarking%20Survey%20Comprehensive%20Report.pdf | Verified by Banking Domain in Round 2 (`04-sources.md` still labels it [S]); context only |

**Dropped on purpose:** the Ledge close-time figures (they belong to the parked receivables idea), the Wise/Capital Economics £2.8bn (UK-only, vendor-commissioned, off-story), the LexisNexis $118.5B (2020-dated, off-story), the "20–300 suppliers a month" range (unsourced), and the Trustpilot "frozen funds at fintechs" line (reads as a dig at the host). The AFP 2025 "wire transfers were the payment method most targeted by BEC (63%)" figure is verified but not used, because the product speaks of payouts and bank transfers.

### 2.2 Persona: what is sourced and what is assumed

| Persona element | Status | Source |
|---|---|---|
| Firms under $100M revenue typically manage up to 500 vendors | Sourced (Codat, 700 US businesses, $10M–$1B revenue) | https://codat.io/resources/how-hundreds-of-middle-market-businesses-really-spend/ |
| Supplier payments ranged from 1 to more than 2,000 per month, with most in the 101–250 range | Sourced (MineralTree 2022 State of AP, 912 AP professionals, mostly $10–100M revenue) | https://www.mineraltree.com/wp-content/uploads/2022-State-of-AP-Report.pdf |
| Company size of 10–200 people | **ASSUMPTION** (no source); validate in user interviews | – |
| A weekly or bi-weekly payment run | **ASSUMPTION** (no source) | – |
| Pays in 3+ currencies | **ASSUMPTION** (no source) | – |
| No dedicated treasury or AP team; the founder, a finance lead or a fractional CFO runs it | **ASSUMPTION** (no source) | – |
| Demo company "Halden Robotics": 40 people, USD wallet, pays USD/EUR/GBP suppliers weekly | **Synthetic fixture**, not a claim | – |

### 2.3 Why now
Airwallex exposes the whole loop over one API: multi-currency balances, FX quotes and conversions, beneficiaries with corridor schemas, transfers with a typed failure lifecycle, and financial transactions for reconciliation. Language models can now read messy bills and emails well enough to *raise* flags, while deterministic code keeps every money decision. And per AFP 2026, only 17% of organisations use AI against payments fraud.

---

## 3. HackerEarth idea-phase submission text (paste-ready)

**How to use:** the form fields are behind login and unknown. Paste the block that fits each field. Rules applied to every block: lead with the lock; at most two statistics in the short and full text (AFP 2026 74%, APQC 1.5%); "sign off" and "confirm", never "countersign"; "payout" or "bank transfer", never "wire" for local payments; no claim about Verification of Payee / `verify_account`; no claim that anything has been built or tested yet; future tense for what will be built.

**Title**
> Wiretight: supplier payouts that can't be quietly redirected

**Sub-line (if there is a subtitle field)**
> New or changed bank details stay locked until a second person confirms them by callback.

**Track / theme**
> Treasury & Ops. Original idea: payee-change fraud control plus landed-payment reconciliation; neither is a starter kit. Borrows kit 3's no-double-pay discipline.

**Tagline (24 words)**
> Wiretight locks any new or changed supplier bank details until a second person confirms them by callback, then pays, tracks and reconciles every payout.

**Short description (~75 words)**
> Small finance teams pay overseas suppliers every week from an inbox and a bank portal. One "we've changed banks" email can redirect a payment. Wiretight will run that payment run on Airwallex with one rule: no payout goes to bank details a human hasn't confirmed and signed off on exact terms. That covers a fraudster's new IBAN and a supplier's genuine new account after a returned payment. Every payout is tracked until it lands, then reconciled.

**Full description (~210 words)**
> *Problem.* In AFP's 2026 survey, 74% of US organisations were affected by business email compromise. The FBI advises verifying any request to change account information through a second channel. APQC benchmarks put duplicate or erroneous disbursements at a 1.5% median. In a small company, all of this can land on one person, every week.
>
> *The lock.* Each sign-off will be a passkey signature over a hash of the exact payee, bank account, amount, currency and evidence. If anything changes after sign-off, including the bank details, the signature no longer matches and the executor refuses to pay. Paying new or changed details will require a recorded callback by a separate operations user to a supplier contact that predates the change, a cooling-off period, two sign-offs, and a capped first payment with the rest held until it lands. The same lock covers a supplier's genuine new account after a payout is returned, because recovery is where redirection fraud hides.
>
> *The proof.* PAID is treated as provisional, because Airwallex documents failures after PAID. Every wallet movement will tie out per currency against Airwallex financial transactions; any residual is shown and explained, never hidden.
>
> *Division of labour.* A language model reads bills and explains anomalies. Code decides amounts, plans, limits and state. The model never holds keys.

**Long description (adds ~340 words to the full description; ~550 together)**
> *Controls, enforced in code.* Auto-pay is off by default; when a company turns it on it is limited to small local payouts to suppliers with a clean payment history. One sign-off below a value threshold; two sign-offs above it, and for any new payee, bank change or replacement payment. Daily, per-payee and per-signer caps stop someone splitting a large payment into small ones. A kill switch is checked before every money movement and takes two people to clear. Approvals expire and are single-use. The app refuses to start unless it points at the Airwallex sandbox, and policy files can only make the built-in safety floor stricter, never looser.
>
> *Airwallex APIs.* Balances and balance history; FX rates, quotes and conversions; beneficiary schemas, validation and creation; transfers with deterministic request IDs and lookup-before-retry; transfer status tracking (polling first, signed webhooks optional); financial transactions for the tie-out; sandbox simulations for deposits and transfer failures, kept behind one interface.
>
> *Across markets.* Local rails are preferred (SEPA for EUR, Faster Payments for GBP, ACH for USD), with the payer covering fees on any SWIFT payout. The planner knows business days, cut-offs and holidays, because the send date is not the arrival date.
>
> *Adoption.* It runs on a company's existing Airwallex account. Teams start in shadow mode: Wiretight moves no money and reports what it would have caught compared with what the team actually paid. Bills come in from email or PDF; a journal CSV goes out. A shadow report graduates the team to one-sign-off payments, then to auto-pay per supplier.
>
> *Evidence we will publish.* A seeded evaluation of 20 labelled scenarios with raw results: double payments, unauthorised executions, duplicate and bank-change detection with precision as well as recall, and reconciliation residuals.
>
> *Builder.* Solo builder based in India, using coding agents and sandbox-only infrastructure. [STATUS ON THE DAY: write exactly one true sentence, e.g. "No project code has been written yet; the build starts on 25 October." or "Sandbox authentication and transfer simulations were explored in throwaway tests; all project code will be written during the build phase."]

**Tech stack line**
> Python 3.12, FastAPI, SQLite, HTMX, WebAuthn passkeys, Airwallex REST API (sandbox), optional hosted LLM (Claude) for reading bills, pytest + Hypothesis.

**Slide outline (only if a PDF/PPT upload is required; 6 slides)**
1. **One story, one number.** "Two days before a €7,500 bill is due, an email arrives: we've changed banks." 74% of US organisations were affected by BEC in 2025 (AFP 2026).
2. **The rule.** No payout reaches a bank account a human hasn't confirmed and signed off on exact terms. Why: the FBI's second-channel advice.
3. **The lock fires twice.** (a) The fraudulent new-IBAN email voids the sign-off; (b) after the supplier's account closes and the payout returns, its genuine new account goes through the same lock (callback, cooling-off, two passkey sign-offs, capped first payment).
4. **Code decides, the model reads.** Architecture: the model has no keys and sees masked account numbers; a separate executor holds the key and re-checks everything live before each call.
5. **Proof it landed.** PAID is provisional; per-currency tie-out against Airwallex financial transactions; journal CSV.
6. **Adoption and plan.** Existing Airwallex account → shadow mode → one sign-off → earned auto-pay; 3-week build plan; the metrics we will publish.

---

## 4. Product behaviour

**Wording rules for every UI string, log message, README line and voiceover (D9):** the product is "Wiretight"; the human act is "sign off" (noun "sign-off"); the callback act is "confirm"; local payments are "payouts" or "bank transfers", never "wires"; SWIFT payments are "SWIFT payouts". Approval tiers are shown to users as "auto", "one sign-off", "two sign-offs"; T0/T1/T2 are internal names only.

**Scope (single entity):** one Airwallex sandbox account = one company (`run.entity_id` is constant; asserted in tests). No connected accounts, no multi-tenant code, no production code path.

### 4.1 The agent loop

```
INGEST ──▶ VERIFY ──▶ PLAN ──▶ SIGN OFF ──▶ EXECUTE ──▶ TRACK ──▶ RECOVER ──▶ RECONCILE ──▶ REPORT
code(+LLM   code       code     human /       code         code      code + human  code          code numbers,
 optional)  (LLM may   (pure)   pre-signed    (executor,             (+LLM drafts               LLM may narrate
            explain)            policy (T0)   holds key)             for a human)               (optional)
```

| Step | What happens | Who decides |
|---|---|---|
| **Ingest** | Bills arrive as structured `InvoiceDraft` JSON (Week 1), and from `.eml`/PDF (Week 2, optional LLM). Deterministic parsers extract bank identifiers and amounts. The LLM (optional) may fill only vendor name, invoice number, dates and a memo summary, from **one document per call**, with account numbers masked to the last 4. | Code. The LLM output is checked field by field against the parsers; any disagreement → `EXTRACTION_CONFLICT` quarantine. |
| **Verify** | Deterministic vendor matching; lookalike-domain detection; duplicate detection; bank-fingerprint diff; screening stub; open change requests. | Code only. The LLM may write an explanation shown in a separate "AI explanation (unverified)" box. |
| **Plan** | Pure function over a snapshot: rail choice, business-day/cut-off/holiday logic, FX aggregation by currency, reserve floor, tiers, caps, tranches, deferrals; re-plan diff when anything changes. | Code only. Same input → byte-identical plan. |
| **Sign off** | CONVERSION and PAYMENT packets; passkey signatures by roster approvers; T0 items are pre-approved by the two-signature policy file. | Humans (or the signed policy for T0). |
| **Execute** | Single-writer executor: halt check → rebuild packet from live data → verify signatures → live guards → audit INTENT → API call → lookup-before-retry. | Code (the only component holding the Airwallex key). |
| **Track** | Polling is primary; optional webhooks only trigger a poll. PAID is provisional; FINAL is our label after the rail's business-day return window. | Code. |
| **Recover** | `failure_type` captured on first sight → playbook or DEFAULT handler → replacement only under the duplicate lock, through the full bank-change lock if details change. | Code + humans (sign-off, callback, supplier contact). The LLM may draft a supplier message; a human sends it outside the app. |
| **Reconcile** | Every settled financial-transaction row is matched to one internal object and one tie-out term; residual per currency must be 0.00 or explained with cited rows. | Code. |
| **Report** | Run summary, tie-out, journal CSV, shadow-mode "would have caught" report. | Code computes every number; an optional LLM paragraph may only restate numbers it is given. |

### 4.2 What the model may and may not do
- **Tools the model gets (typed, none move money):** `extract_invoice_fields(doc)` (masked text in, partial `InvoiceDraft` out), `explain_flags(flags, masked_facts)`, `draft_supplier_message(template_id, masked_facts)`, `summarize_run(numbers)`. Recipients of any draft always come from the vendor-contact table, never from model text.
- **The model never:** sees API keys or full account numbers; selects a vendor; sets or clears a flag, tier, verification state or bank detail; computes an amount; approves anything. Model text that claims "verified", "confirmed", "approved" or "called" without a backing record is stripped before display.
- **When the LLM is disabled or down** (`LLM_ENABLED=false` is the default): PDFs and emails go to REVIEW, the structured path still works, nothing degraded is ever T0 (fail closed).
- **Process separation:** the web/ingest process holds the LLM key and no Airwallex credentials; the worker process (executor + poller) holds the Airwallex credentials and no LLM key (§5.3).

### 4.3 Verify: vendors, parsers, duplicates, fingerprint, screening
- **Parsers (authoritative for identifiers and amounts):** IBAN mod-97 + country length; US ABA checksum; UK sort code (6 digits); BIC (8 or 11); ISO-4217 currency with exponent; amounts as `Decimal` at the currency exponent; invoice-number normalisation (upper-case, strip spaces, dashes and leading zeros). Transfer `reference` must match `^[A-Za-z0-9 ./-]{1,35}$` (our limit, not Airwallex's) or the item goes to REVIEW; it is further truncated to any limit the corridor schema returns.
- **Vendor matching (code only), in priority order:** tax ID exact → normalised legal name exact → known sender domain exact. A sender domain within edit distance ≤ 2 of a known vendor domain, or matching it under a homoglyph map, → `QUARANTINE: LOOKALIKE_DOMAIN`, never a match. No fuzzy name auto-match, ever.
- **Bank fingerprint:** `sha256(rfc8785({country, currency, method, normalised account identifiers, bic}))`, compared against the current `payee_version`. Also store Airwallex's own beneficiary `fingerprint` field when the response carries one (documented as optional) and diff both. A different fingerprint → a **PayeeChangeRequest** (§4.5), never a silent update.
- **Duplicates:** `(vendor_id, normalised invoice no.)` exact → `DUPLICATE` (HARD_BLOCK). Same vendor + same amount + due date within ±7 days → `SUSPECT_DUPLICATE` (T2 trigger, T0 disqualifier). Several bills from one vendor within 7 days summing to at least a tier threshold → `SPLIT_SUSPECT` (T2 trigger). A `duplicate_lock` row with a UNIQUE `obligation_key` is taken when the obligation is created. Already-paid check: our ledger plus `GET /transfers?beneficiary_id=…&from_created_at=…`.
- **Screening stub (honest scope):** `screen(counterparty) → CLEAR | HIT | ERROR`, called at plan time and again by the executor before each call. It checks a tiny synthetic list in `tests/fixtures/screening/list.yaml`. HIT or ERROR → HARD_BLOCK (fail closed). The README states that **no real sanctions screening is performed**.

### 4.4 Autonomy tiers (evaluated in this order; the first match wins)

| Tier (UI name) | When | Who signs |
|---|---|---|
| **HARD_BLOCK** ("blocked") | `DUPLICATE`; a non-terminal or AMBIGUOUS attempt exists for the obligation (any run); open PayeeChangeRequest for the vendor (`HOLD: BANK_CHANGE`); cooling-off not finished; tranche 2 waiting for tranche 1 FINAL; `QUARANTINE` (lookalike domain, extraction conflict, hidden text); `COMPLIANCE_HOLD`; open RFI on the payee (`RFI_OPEN`); screening HIT/ERROR; `INSUFFICIENT_APPROVERS` (roster < 3 humans who can sign); a 4th payment to one payee within 24 h; daily all-tier cap reached; kill switch halted. | Nobody. Only the underlying condition can be resolved (and every resolution is audited). There is no "policy override" action. |
| **T2** ("two sign-offs") | ≥ USD 10,000 equivalent; the payee's rolling 7-day aggregate including this item ≥ USD 10,000; any payment to a `payee_version` with fewer than 2 FINAL payments (new payee, changed details, tranche 2); any replacement after a failure; first payment to a new country; `SUSPECT_DUPLICATE`; `SPLIT_SUSPECT`; `AT_RISK_LATE`; any degraded check. | Two distinct roster approvers, neither in the requester set, neither the callback recorder. Plus callback evidence when details are new or changed. |
| **T1** ("one sign-off") | Everything else under USD 10,000 equivalent. | One roster approver not in the requester set. |
| **T0** ("auto") | Only if `t0.enabled: true` in a policy carrying two approver signatures **and** every condition holds: amount ≤ USD 2,000 and ≤ 1.5 × the payee's median FINAL amount; ≥ 3 FINAL payments to the same unchanged beneficiary, each ≥ 25% of the limit; bank details unchanged ≥ 60 days; LOCAL rail; sender on the vendor's known-sender list; no disqualifier (§4.15 row 9); cap headroom ≥ amount (rows 13–16). | No human at run time; still a packet + audit entry. T0 is a pre-approved policy limit, never an unapproved path. **Off by default.** |

**Requester set** = {the user who ingested, forwarded or uploaded the invoice; every user who edited the obligation or plan item; the user who created the payee version or recorded the change request}. Roster entries must have unique emails (duplicates fail policy load). **Earned autonomy:** any failure or bank change demotes a payee out of T0.

### 4.5 The bank-change lock: PayeeChangeRequest, callback, cooling-off, tranches

#### 4.5.1 Entity
`payee_change_request` (UI: "change request"): `id`, `vendor_id`, `source_kind` (email | upload | failure_recovery | manual), `source_message_id`, `received_at`, `intake_user_id`, `requester_set` (JSON), `old_payee_version_id`, `proposed_details_ref` (pointer into the encrypted identifier store), `proposed_masked` (e.g. `DE•• •••• 7740`), `proposed_fingerprint`, `evidence` (JSON: flags such as LOOKALIKE_DOMAIN, NEW_COUNTRY, URGENCY_LANGUAGE, INVOICE_SHOWS_ON_FILE_IBAN), `validate_result` (`FORMAT_VALID` | `FORMAT_INVALID` from `POST /beneficiaries/validate`; never shown as "verified"), `vop_result` (optional evidence only), `status`, `status_reason`, `decided_at`.

**States:**
```
RECEIVED ─▶ PENDING_CALLBACK ─┬─(callback CONFIRMED)──▶ COOLING_OFF ─(cooling-off ends)─▶ APPROVED
                              ├─(callback DENIED / "no change made")──▶ REJECTED (terminal)
                              ├─(no valid callback within 7 days)─────▶ EXPIRED  (terminal)
                              └─(ops withdraws, with reason)──────────▶ WITHDRAWN (terminal)
NO_ANSWER keeps PENDING_CALLBACK (counted, audited).
```
- **REJECTED** makes the proposed payee version `REJECTED` (it was never usable; no Airwallex beneficiary is ever created for it), flags the vendor, and drafts an internal fraud-alert note for a human (never sent by the app). The vendor's on-file version becomes payable again, but any packet that was voided stays void: a fresh sign-off is required.
- **APPROVED** makes the new payee version `ACTIVE_CAPPED` and the old one `SUPERSEDED`. The Airwallex beneficiary for the new version is created by the executor at execution time (it is a mutating call, so it passes the halt check and the daily new-beneficiary cap).
- A REJECTED or EXPIRED request is never reopened. Releasing a supplier wrongly rejected means a **new** change request through the same callback rules (§4.14.4).

**How an open change request voids an earlier sign-off (the cold-open beat):** every PAYMENT packet item binds `open_change_request_ids` for its vendor (normally `[]`). When a change request opens, the executor's rebuilt packet has a non-empty list, the hash no longer matches, the approval is voided with a diff, and the obligation goes to `HOLD: BANK_CHANGE` (HARD_BLOCK). Zero transfer requests are emitted.

#### 4.5.2 Callback enforcement (code rules; all must pass)
The callback is an evidence record (`callback_verification`), recorded through the UI by the **ops** user. The UI shows the number to dial from a `vendor_contact` row; the human cannot type a number.
1. **Who:** `recorded_by` has role `ops` and is not in the requester set, not the intake user, and not an approver on any packet of the run (D6; stricter than "at most one of the two approvers").
2. **Which contact:** the `vendor_contact` row was created ≥ 30 days before the change request, before any other contact or bank change on that vendor, and has not itself changed in the last 30 days (`CONTACT_RECENTLY_CHANGED`). Its normalised number/email must not appear in **any** artefact of the triggering thread (email body, signature, headers, PDF text, attachments) (`CALLBACK_NUMBER_FROM_CHANGE_REQUEST`). Provenance must be one of: signed contract, prior paid invoice ≥ 90 days old, the vendor's public website, a company registry. For a **new payee** the contact must come from a source independent of the document that supplied the bank details.
3. **When:** after the change request was received and within 7 days of it.
4. **What:** `vendor_person_name`, `vendor_person_role`, `called_at`, readback results (the vendor reads the last 4 digits and the account-holder name back to us; our caller never reads them out; the record stores whether they matched), `outcome` ∈ {CONFIRMED, DENIED, NO_ANSWER}, optional `attachment_sha256`. The record's sha256 goes into the PAYMENT packet's `callback_record_sha256`.
5. **Contact changes** are themselves T2 changes that need a callback to a different, older contact.
6. **Honesty:** the README and a demo caption say the system records **evidence of** a callback and cannot prove a phone call happened.

`verify_account` (Verification of Payee), when `VERIFY_ACCOUNT_ENABLED=true`, is **evidence only**: NOT_MATCHED or PARTIAL adds a red flag; FULL is shown as supporting evidence; CANNOT_VERIFY, EXTERNAL_SERVICE_UNAVAILABLE, errors or flag-off mean "no evidence". **It never removes the callback, never lowers a tier, never releases a hold.** It is off by default and never appears in the pitch or the demo as a capability.

#### 4.5.3 Cooling-off
No payment to new or changed details until **72 hours** after the later of (callback CONFIRMED, change request received). In the sandbox demo only, the override is **2 minutes**, loaded only when `AWX_ENV=sandbox`, the host pin passes and `APP_DEMO_TIMING=true`; every affected screen shows `demo timing · policy 72 h`.

#### 4.5.4 First-payment cap and the tranche model
- **Cap** for the first payment to a new payee version: `min(USD 2,500, 50% × the vendor's 12-month median FINAL payment in USD-eq)`; a vendor with no history gets USD 2,500. USD-equivalent uses the locked quote's `client_rate` when one exists, otherwise the **worse** of the indicative rate and the last booked rate.
- **Tranches:** an obligation larger than the cap is split into `obligation_tranche` rows: tranche 1 = the cap converted to the transfer currency, **rounded down** to the currency exponent; tranche 2 = the remainder, status `HELD_TRANCHE` until tranche 1 is **FINAL**. Tranches belong to one obligation, so they are not "splitting" (no SPLIT_SUSPECT). Each tranche has its own `request_id`, PAYMENT packet and sign-off (T2, because the version has < 2 FINAL payments).
- **Cap lift:** the cap applies to every new obligation for that payee version until it has **2 FINAL** payments with no failure or recall. (Interpretation recorded in Appendix A.)

### 4.6 Plan
`plan(snapshot, policy, now) -> Plan` is a pure function (no I/O, no LLM). Snapshot = balances (`GET /balances/current`, `available_amount`), open obligations and tranches, payee versions, recent transfers (for aggregates and caps), approver roster, calendars.
- **Rail choice:** EUR to a SEPA-country IBAN → `LOCAL` (SEPA); GBP to a UK sort code → `LOCAL` (Faster Payments); USD to a US ABA → `LOCAL` (ACH); otherwise `SWIFT` with `swift_charge_option=PAYER` and `fee_paid_by=PAYER`. SWIFT disqualifies T0. Never switch a LOCAL-eligible payee to SWIFT silently.
- **Business days, cut-offs, value dates:** calendars per currency (`EUR_TARGET2`, `GBP_ENGLAND`, `USD_FED`) for 2026–2027, generated from the `holidays` package and committed, plus weekends. `latest_send_date = business_days_before(due_date, flight_days[rail], calendar)`, with flight days SEPA 2, FPS 1, ACH 2, SWIFT 3 (business days). If now is past the rail's cut-off (policy value, **ASSUMPTION**, labelled in the UI), the send date rolls to the next business day. `latest_send_date < today` → `AT_RISK_LATE` (still payable, T2). A deferred item must keep `latest_send_date ≥ next business day`. Transfers are created **without** `transfer_date` (ASAP); setting it, even to today, routes into scheduled logic.
- **FX aggregation by currency** (not "netting"): conversion per currency = Σ planned PAYMENT amounts in that currency − available balance in that currency (never negative), rounded **up** to the exponent. Rates from `GET /fx/rates/current` are for planning only; any amount a human signs comes from a quote's `client_rate`. Conversions happen just in time, one currency at a time.
- **Reserve floor:** Σ USD-eq outflows + Σ per-rail `fee_reservation` (labelled "reservation, not a fee estimate") must leave `available_amount` ≥ the floor. Otherwise defer the lowest-priority items (priority: criticality, then latest due) with reason `DEFERRED_FLOOR`. Count any prepayment holds as committed.
- **Caps** (§4.15 rows 13–17) applied in order; excess items → `DEFERRED_CAP(<cap name>)`.
- **Re-plan:** a new balance (polled) or any changed input re-runs `plan()`; the output carries `diff_vs_previous`, and only items whose feasibility changed re-open.
- **Output:** `Plan{conversions[], payments[], deferred[], holds[], diff_vs_previous}`.
- **Out of scope:** supplier credit-note offset, multilateral netting, early-pay discounts.

### 4.7 Approval packets: CONVERSION vs PAYMENT
Two packet kinds, each with its own canonical JSON (RFC 8785), sha256, tier and signatures. Amounts are decimal **strings**; a float anywhere in a packet is a build error. A netted conversion change voids only the CONVERSION packet, never the PAYMENT packets.

**CONVERSION packet**
```json
{"kind":"CONVERSION","packet_version":1,"run_id":"…","conversion_id":"…","request_id":"…",
 "sell_currency":"USD","buy_currency":"EUR","buy_amount":"7500.00",
 "approved_sell_amount":"…","max_sell_amount":"…  (= approved_sell × 1.0025, rounded down)",
 "quote_id":"…","client_rate":"…","quote_valid_to_at":"…",
 "funded_items":["<obligation_id>:<tranche_no>", "…"],
 "policy_sha256":"…","tier":"T1","required_approvers":1,"max_validity_seconds":14400}
```

**PAYMENT packet** (carries no quote; lists the CONVERSION packets it depends on)
```json
{"kind":"PAYMENT","packet_version":1,"run_id":"…",
 "items":[{"obligation_id":"…","tranche_no":1,"attempt_no":1,"request_id":"…",
           "replaces_transfer_id":null,"beneficiary_id":"… | null until created",
           "payee_version_id":"…","payee_fingerprint":"…","open_change_request_ids":[],
           "transfer_method":"LOCAL","rail":"SEPA","transfer_currency":"EUR","transfer_amount":"7500.00",
           "source_currency":"EUR","reason":"goods_purchased","reference":"INV-2291",
           "swift_charge_option":null,"fee_paid_by":null,"latest_send_date":"2026-…",
           "cooling_off_until":null,"callback_record_sha256":null,
           "evidence_hashes":["<invoice document sha256>"],"dup_check_sha256":"…","screening":"CLEAR"}],
 "totals_by_currency":{"EUR":"7500.00"},"funding_packets":["<conversion packet sha256>"],
 "policy_sha256":"…","tier":"T1","required_approvers":1,"max_validity_seconds":14400}
```
- **Expiry** = min(first signature time + 4 h, `quote_valid_to_at` − 120 s) for CONVERSION packets; first signature time + 4 h for PAYMENT packets. A PAYMENT packet can only execute when every funding CONVERSION is `SETTLED`.
- **Single use:** an approval is consumed in the same DB transaction that records the executor's INTENT; a consumed approval can never be reused (replacements, retries with a new attempt number and new runs all need fresh sign-offs).
- **Quote rules:** quotes are created at sign-off time with validity `HR_4`; a quote with < 120 s validity left is never booked (so `MIN_1` quotes are never bookable); every quote is treated as single-use even if the sandbox accepts reuse. A re-quote within 25 bp **and** ≤ `max_sell_amount` may continue under the same CONVERSION sign-off (recorded); otherwise the packet is void and must be signed again with a diff ("rate 0.9182 → 0.9219").
- **Sign-off card rules:** the card renders **only** from the canonical packet JSON and shows the hash prefix; any model text sits in a separate "AI explanation (unverified)" box. T2 items are signed one at a time, with the callback record and fingerprint diff displayed; bulk sign-off is allowed only for T1 items from unflagged payees.

### 4.8 Passkey signing and executor verification
- **Roster (D6):** 3 approver identities plus 1 separate ops user (demo: Arun = AP clerk, Meera = finance lead, Kabir = founder; Priya = ops, records callbacks only and can never sign). All synthetic. Arun is on the approver roster but, as the requester of the demo bills, separation of duties excludes him from signing them, so the demo T2 sign-offs are Meera + Kabir. A roster with fewer than 3 approvers makes every T2 item `INSUFFICIENT_APPROVERS` (HARD_BLOCK); the kill switch can still be cleared by 2 approvers. No full user auth: an **identity switcher** chooses the acting identity, and each signing identity proves itself with its own passkey.
- **WebAuthn (primary):** challenge = `sha256(bytes.fromhex(packet_sha256) || nonce32)`, nonce single-use, valid 5 minutes. The server verifies with `webauthn.verify_authentication_response(...)` against the roster's registered public key, expected RP ID and origin, `require_user_verification=True`, and a sign count that must increase when non-zero. Registration happens once via `make passkeys` on localhost.
- **HMAC fallback (D5, only if passkeys slip):** `sig = HMAC-SHA256(approver_key, "pkt-v1|" + packet_sha256 + "|" + nonce)` with per-approver random 32-byte keys generated locally. Every UI, CLI and README surface then shows **"FALLBACK (HMAC, not phishing-resistant)"**, and the claim drops from "signed with a passkey" to "integrity-bound".
- **Executor verification:** the executor re-verifies every stored assertion from stored material (credential public key, challenge, nonce, packet hash) at execution time and **never trusts a status column**. An assertion that fails at the executor trips the kill switch.
- **Honesty:** a passkey signature proves that a registered device holder signed these exact terms in our app. It is not a legal e-signature.

**Executor sequence for every mutating call** (`beneficiaries/create`, `fx/conversions/create`, `transfers/create`); single writer, file lock `var/executor.lock`:
1. **CAS** the item `APPROVED → EXECUTING` (single-row conditional update); if it fails, stop.
2. **Halt check** (DB flag, HALT file, unreadable HALT file = halted).
3. **Rebuild the packet from live data:** `GET /beneficiaries/{id}` (when the beneficiary exists; fingerprint must match our record), the quote (`GET /fx/quotes/{id}`) for conversions, open change requests, cooling-off, tranche state, screening. The rebuilt sha256 must equal the signed sha256, else VOID with a diff.
4. **Verify signatures** (`approvals.is_approved`): required approver count and identities, SoD, expiry, not consumed, per-approver daily total (row 17).
5. **Live guards:** `GET /balances/current` → available − this outflow − remaining planned outflows ≥ reserve floor (else abort + kill-switch trip); duplicate lock held by this obligation and `GET /transfers?request_id=` for this **and every prior attempt key** returns nothing live (anything not CANCELLED → abort + incident `DUPLICATE_LIVE`); daily/run/payee caps (an attempted breach trips); quote ≥ 120 s from expiry and sell ≤ `max_sell_amount`.
6. **Audit INTENT** (log-before-act). If the write fails, do not call; the kill switch trips. Consume the approval in the same transaction.
7. **Call** through the client (`IdemResult`: CREATED, EXISTS_FOUND, REJECTED, AMBIGUOUS). Then audit RESULT.
8. **AMBIGUOUS** stops all further items in the run, counts toward the kill-switch trip, and is resolved only by lookups with the **same** key; > 6 days unresolved → human escalation. Never mint a new key.

Order within a run: beneficiaries → conversions (wait for `SETTLED` via polling) → transfers. After a crash, restart resumes from the DB and resolves every SUBMITTING/AMBIGUOUS attempt by lookup **before** anything else runs.

### 4.9 Kill switch
- **State** lives in two places: a DB flag and a `HALT` file (`APP_HALT_FILE`). Either set, or the file path unreadable, = halted (fail closed).
- **Halted blocks** every mutating call (`beneficiaries/create`, `fx/conversions/create`, `transfers/create`). **Reads continue**: polling, AMBIGUOUS lookups, RFI polling, reconciliation.
- **Who trips:** any roster approver (UI button or `wiretight halt --reason "…"`), plus the automatic trips in §4.15 rows 24–29.
- **Who clears:** two distinct roster approvers, each signing `sha256("clear|" + trip_id + "|" + reason)` (passkey or labelled fallback), plus a reason. Clearing resumes nothing: approvals that expired while halted need fresh sign-offs.
- **Honest limits:** in-flight transfers are not recalled; no transfer-cancellation endpoint is part of this design. The ultimate stop is revoking the API key in the Airwallex web app (a human action, in the runbook).
- Every trip and clear is audited.

### 4.10 Tracking and FINAL
- **Polling is primary:** `GET /transfers/{id}` for every non-terminal transfer (fast interval `POLL_INTERVAL_S=2` near expected transitions, backing off to 60 s), `GET /fx/conversions/{id}`, `GET /transfers?request_id=` for AMBIGUOUS items, `GET /balances/current` for re-plans, `GET /rfis?…` for RFIs. Webhooks, if enabled, are HMAC-verified, deduped on event id and **only enqueue a poll**; they never set state.
- **Two status columns per transfer:** `awx_status` mirrors Airwallex and follows only documented transitions (regressions are ignored and audited); `wt_state` is our overlay (AMBIGUOUS, PAID_PROVISIONAL, FINAL, PRESUMED_SETTLED, REOPENED, RFI_OPEN).
- **FINAL** (our label, never Airwallex's): PAID + the rail's return window measured from the first PAID observation on the rail's calendar, with a 48 h minimum: SEPA 3 TARGET2 business days; UK Faster Payments 3 UK business days (**ASSUMPTION**, labelled); US ACH 2 US banking days (**ASSUMPTION**: sourced only from a search snippet, labelled). **SWIFT is never FINAL by timer:** it needs a recorded supplier confirmation; otherwise it shows `PRESUMED_SETTLED` (not FINAL) after 10 business days.
- **After FINAL** the poller keeps checking once a day for 30 days (design value). A FAILED observed after FINAL is never ignored: `wt_state → REOPENED`, an incident `LATE_FAILURE_AFTER_FINAL` opens, and the return journal posts.
- FINAL increments `payee_version.final_payment_count` (which releases tranche 2 and, at 2, lifts the cap).
- The FINAL window is **not** shortened in the demo (tranche 1 stays `PAID · provisional` on camera and tranche 2 stays HELD); tests use clock control.

### 4.11 Failure playbooks (all 32 simulator `failure_type` values + DEFAULT)
`failure_type` and `failure_reason` are persisted **the first time they are seen**, whether the first observation is FAILED or the auto-cancelled CANCELLED (FAILED auto-cancels within seconds). There is **no "wait and re-check"** anywhere. A bank return is modelled as FAILED + `BENEFICIARY_BANK_RETURNED` (there is no RETURNED status).

| Group | `failure_type` values | Playbook |
|---|---|---|
| A. Bank details / account wrong or closed | `ACCOUNT_CLOSED` (90701), `ACCOUNT_INACTIVE_OR_DORMANT` (90702), `ACCOUNT_CURRENCY_MISMATCH`, `BENEFICIARY_NAME_MISMATCH` (90301), `INVALID_ACCOUNT_NAME_OR_NUMBER` (90101), `INVALID_BANK_OR_BRANCH_CODE` (90201), `INVALID_SWIFT_BIC_CODE` (90202), `INVALID_BENEFICIARY_DETAILS` (90401), `INVALID_BANK_INFORMATION`, `INVALID_CORRESPONDENT_BANK_INFORMATION` | Payee version → `SUSPENDED`; incident opens; supplier message drafted (human sends it via a vendor-master contact); **any new details enter as a PayeeChangeRequest with `source_kind=failure_recovery` and go through the full lock (§4.5)**; replacement = new attempt under the same duplicate lock, T2. Vendor flagged for CLOSED/DORMANT. |
| B. Bank return | `BENEFICIARY_BANK_RETURNED` (90802) (FAILED after SENT or PAID) | Return journal (§4.13); supplier confirmation; replacement T2; new details → full lock. |
| C. Data fixes | `INVALID_SPECIAL_CHARACTER`, `INVALID_PAYMENT_PURPOSE` (91101) | Sanitise reference/name or change `reason`; same payee version; fresh PAYMENT packet (T1 unless another trigger). |
| D. Funding / limits | `INSUFFICIENT_FUNDS`, `TRANSACTION_AMOUNT_NOT_COVERING_FEE`, `EXCEEDED_TRANSACTION_AMOUNT_OR_LIMIT` | Re-plan funding; for the limit case any split or rail change needs a new sign-off (T2). |
| E. Channel / system | `CHANNEL_TIMEOUT` (91401), `SYSTEM_ERROR` (91402) | Already terminal (FAILED → CANCELLED). Escalate to a human ("contact Airwallex" is a human action); a T2 replacement is allowed. |
| F. Compliance | `ACCOUNT_UNDER_RESTRICTION` (90703), `TM_SUSPENDED` (90502), `CHANNEL_POLICY` (90501); any `WATCHLIST_*` reason code (parsed defensively from `failure.details.reason_codes`, ⚠ path unverified) | Payee → `COMPLIANCE_HOLD` (HARD_BLOCK); **kill switch trips on first occurrence**; escalation to founder + finance lead; supplier-message drafting is disabled for that payee (no reason text leaves the system); never auto-retry. |
| G. Investigate | `RECALL_REQUESTED` (91001), `CLIENT_REQUESTED` (91002), `DUPLICATION_RETURN`, `BENEFICIARY_REQUESTED` | Escalate; no automatic replacement; any replacement is T2. |
| H. DEFAULT handler | `UNABLE_TO_APPLY`, `OTHER`, `CARD_ISSUER_ERROR`, `INBOUND_2B_CARD_NOT_SUPPORTED`, `INBOUND_BENFICIARY_VALIDATION_ERROR` (sic: misspelled in the enum, match byte-for-byte), `INBOUND_COMPANY_REGISTRATION_NUMBER_ERROR`, `INBOUND_ORDER_ERROR`; also `null`, `"simulation"` (a bare cancel returns only `failure_reason: "simulation"`) and any unknown string | Incident `UNKNOWN_FAILURE`; payee HOLD; raw `failure_reason` stored; escalate; never auto-retry; any replacement is T2. |

**Create-time outcomes are not failure types:** `balance_insufficient` (transfers) / `insufficient_funds` (FX) → plan state, re-plan; 400 validation → REJECTED (definitive) + incident; `duplicate_request_id` → "exists, look it up".

**Replacement rule (duplicate lock):** a replacement is created only when the original's Airwallex status is CANCELLED (or FAILED-after-return), confirmed by our own `GET /transfers/{id}`, never by a webhook alone. It gets `attempt_no + 1` (so a new `request_id`), `replaces_transfer_id`, and its own T2 sign-off. The incident closes only when the original's outcome is recorded and the replacement is FINAL. A second replacement for the same attempt is blocked by the lock. **Funding:** the replacement reuses the refunded currency (no new conversion when the balance covers it) and budgets a second fee reservation; a CONVERSION packet is added only if the balance is short.

**RFI tracking:** poll `GET /rfis?types=TRANSACTION&statuses=ACTION_REQUIRED`. An RFI linked to a transfer → `wt_state RFI_OPEN`, a queue card ("Airwallex needs information about transfer X"), and a hold on new payments and replacements for that payee. `ANSWERED` → waiting; `CLOSED` → holds release only when the transfer state allows. **Responding (`POST /rfis/{id}/respond`) is human-only via the UI; workers never call it.**

### 4.12 What the demo's failure looks like
Bill #2 (EUR 7,500) pays `LOCAL · SEPA`. After `SENT` it fails with `ACCOUNT_CLOSED` (documented reason `90701: Account closed`); if the simulator rejects that, `BENEFICIARY_BANK_RETURNED` (`90802: Beneficiary bank returned`). The caption always shows the `failure_type` and `failure_reason` Airwallex actually returned, or "not returned by sandbox". `BENEFICIARY_NAME_MISMATCH` stays a unit/eval case only.

### 4.13 Reconciliation and journals
**Inputs:** `GET /financial_transactions` (filters `from_created_at`, `to_created_at`, `source_id`, `currency`, `status`; `source_type` is filtered client-side because there is no server filter), `GET /balances/history` (≤ 7-day windows when paging by number; use the cursor), `GET /balances/current`, plus our transfers, conversions and ledger. Each run snapshots opening balances at start, so the tie-out is computed from that snapshot (sandbox state accumulates across demo runs).

**Matching:** each SETTLED row maps to exactly one internal object (via `source_id`) and exactly one formula term. Unmapped row → `UNMAPPED_ROW`; internal object with no row after the window → `MISSING_ROW`; amount mismatch → `AMOUNT_MISMATCH`. One row counted in two terms is a test failure.

**Tie-out formula** (per currency c, window [t0, t1], SETTLED rows, Decimal at the currency exponent):
```
B_close(c) = B_open(c) + DEP(c) + CB(c) − CS(c) ± CR(c) − P(c) − F_tx(c) + R(c) − F_3p(c) − F_fxc(c) ± ADJ(c) ± PRE(c)
  DEP  deposits                         CB/CS  conversion buy / sell legs     CR  conversion reversals (signed)
  P    payout principal (PAYOUT rows)   F_tx   Airwallex transfer fees, incl. fees retained on failed/returned payouts
  R    refunds of failed/returned payouts in the transfer currency (PAYOUT_FAILURE / PAYOUT_REVERSAL)
  F_3p third-party fees deducted separately    F_fxc FX cancellation delta fee (only if refunded in source currency)
  ADJ  ADJUSTMENT rows (signed)         PRE    PREPAYMENT / PREPAYMENT_RELEASE (signed)
residual(c) = B_actual(c) − B_close(c)
```
`B_actual` = the balance-history closing balance at t1 (or available + pending + reserved from `GET /balances/current` when t1 = now). **Return identity** per returned transfer T (⚠ U15): `R_T = A_T − F_T,retained`; net wallet cost of T = `F_T,retained + F_3p,T + F_fxc,T`. How fee types appear as rows (inside the PAYOUT row's `fee` field or as separate FEE rows; how third-party and FX-delta fees are typed) is ⚠ unverified (U13/U14); the day-1 fixtures decide the mapping table `TERM_MAP`, and each entry cites its fixture file. If a fixture contradicts the identity, the code follows the fixture and `docs/undocumented-behaviour.md` says so. **Never bend a fixture to fit the formula; never plug a residual.**

**Tie-out states (shown on screen):**
- **RESIDUAL 0.00** (green): every row matched.
- **RESIDUAL EXPLAINED** (amber): each non-zero component is tied to a cited row or object with a reason code (e.g. "rows pending: tied out from transfer/conversion objects"; "refund on #2 less a retained fee, row ft_…"). An explanation is never a plug.
- **RESIDUAL UNEXPLAINED** (red): the run stays OPEN and an exception goes to the finance lead.

**Journal** (functional currency USD; transfer currency kept on every line; generic CSV `date, account, debit, credit, currency, amount_usd, source_id, memo`; no accounting-software API):
- Payout sent: Dr `AP-clearing:<CCY>` / Cr `Wallet:<CCY>`; Dr `Bank fees` / Cr `Wallet:<CCY>` for the fee read from the transfer response.
- Payout FINAL: Dr `AP:<vendor>` / Cr `AP-clearing:<CCY>`.
- Conversion: Dr `Wallet:<buy>` / Cr `Wallet:<sell>`.
- Return: (1) Dr `Wallet:<CCY>` R / Cr `AP-clearing:<CCY>` R; (2) the original fee stays in `Bank fees`; (3) Dr `Bank fees (third-party)` / Cr `Wallet` for any F_3p; (4) Dr `FX loss` (or Cr `FX gain`) / Cr `Wallet` for any F_fxc; (5) the AP liability stays open, so the invoice is still owed.
- Replacement: as a payout, with its own fee read from its own response.
- Realised FX (stretch, cut item 3): measured against the rate captured at ingest via `GET /fx/rates/current`, labelled "rate at ingest" (there is no historical-rate endpoint in our API list).

### 4.14 Shadow mode
Shadow mode is how a real customer starts, and its report closes the demo.

#### 4.14.1 What it does
`SHADOW_MODE=true` runs the whole loop (ingest, verify, plan, packets, executor guards) but the Airwallex client's mutating methods raise `ShadowModeViolation`, so no beneficiary, conversion or transfer can be created. Where the executor would have called, it writes a `WOULD_EXECUTE` audit entry with the packet hash. Sign-offs are optional in shadow mode (unsigned items are reported as "would need one/two sign-offs").

#### 4.14.2 Replay data (read-only)
- The bills the team received in the period (structured JSON, `.eml`, PDF).
- What the team actually paid: `GET /transfers` (with `from_created_at`), `GET /beneficiaries`, `GET /financial_transactions` and `GET /balances/history` over the same period, all read-only.
- The vendor master and contacts with their `created_at` provenance.
In the hackathon the "history" is the sandbox history the seeded demo created; that is labelled synthetic.

#### 4.14.3 The "would have caught" report (`make shadow-report RUN=…`, also a UI page)
Per period, computed by code from the audit log and the replay data:
- bank-change requests that would have been frozen (with evidence flags), and whether the team actually paid the new details;
- duplicates that would have been blocked, and whether the team paid them twice;
- payments that would have breached the reserve floor or a cap;
- payments the team made that Wiretight would have held, with the reason (each one is a disagreement to explain);
- payments Wiretight would have made that the team did not (deferred vs paid);
- the false-positive measure (below) and the human sign-offs it would have needed.
The demo's closing slide shows these rows **from the demo run itself**, labelled synthetic (no claim about real data).

#### 4.14.4 Releasing a wrongly frozen supplier
- **Frozen because of new or changed details:** the only release is the lock itself: an ops callback to an older contact (§4.5.2) → CONFIRMED → cooling-off → two sign-offs → capped first payment. If the due date is now at risk, the item is flagged `AT_RISK_LATE` and a supplier note explaining the delay is drafted for a human to send. There is no same-run bypass (the 72 h floor applies).
- **Frozen without a detail change** (e.g. a lookalike-domain false positive, a `SUSPECT_DUPLICATE` that isn't one): two approvers record a `release` decision with a reason on that specific item; the obligation then plans normally at T2. Releases are audited and counted.
- **A change request REJECTED in error:** open a **new** change request; the old one stays REJECTED.

#### 4.14.5 False-positive measure
- `false_hold_rate` = holds on obligations later confirmed legitimate ÷ legitimate obligations in the period.
- `bank_change_flag_precision` = flagged changes later confirmed fraudulent or unverifiable ÷ flagged changes; `duplicate_precision` likewise. Recall is always reported next to precision.
- "Later confirmed" comes from recorded outcomes: callback CONFIRMED (legitimate), DENIED (fraud), release decisions, and the team's own payments in the replay data.

#### 4.14.6 Graduation criteria (proposed defaults; Round 4 to confirm)
1. **Shadow → one-sign-off enforcement (T1/T2 live, T0 off):** at least 4 consecutive weekly shadow runs (proposed value) in which every disagreement with what the team paid is explained in the report, and zero unexplained reconciliation residuals.
2. **T0 per payee:** only by turning on `t0.enabled` in a two-signature policy, and then only for payees that meet every row 6–9 condition (≥ 3 FINAL payments, ≥ 60 days unchanged, etc.).
3. **Demotion:** any bank change, failure, or disagreement on that payee drops it out of T0 automatically.

### 4.15 The policy floor (hard-coded; `policy.yaml` may only tighten)
Source: Compliance & Risk Round 2b, adopted by D7, amended by D8. Currency basis: USD-equivalent at the locked quote's `client_rate`, otherwise the worse of the indicative and last booked rates. **None of these numbers is an industry standard**; they are the board's defaults for a small company paying USD/EUR/GBP suppliers. Loosening any row, an unknown key (e.g. `duplicates.enabled`, `skip_callback`), a missing required key, YAML tags/anchors, or a policy without two distinct approver signatures over `sha256(file bytes)` → load error → kill-switch trip → non-zero exit.

| # | Control | Shipped value (loosest allowed) | Demo override |
|---|---|---|---|
| 1 | Cooling-off for new or changed details | ≥ 72 h from the later of callback CONFIRMED and change-request arrival | 2 min, only if `AWX_ENV=sandbox` + host pin + `APP_DEMO_TIMING=true`; labelled |
| 2 | Callback contact age | ≥ 30 days; older than the change request and any other contact or bank change on the vendor; a changed contact is unusable for 30 days | None (seed the fixture contact as old) |
| 3 | Callback validity and recorder | After the change request; valid ≤ 7 days; recorded by role `ops`, not in requester set, not an approver | None |
| 4 | First-payment cap | ≤ min(USD 2,500, 50% of vendor's 12-month median FINAL); no history → USD 2,500; excess = tranche 2 held until tranche 1 FINAL | None |
| 5 | Cap lift | After ≥ 2 FINAL payments to the new details with no failure or recall | None |
| 6 | T0 per-payment limit | ≤ USD 2,000 | None |
| 7 | T0 history | ≥ 3 FINAL to the same unchanged beneficiary, each ≥ 25% of the limit; details unchanged ≥ 60 days | None (history seeded and labelled) |
| 8 | T0 amount band | ≤ 1.5 × payee median FINAL | None |
| 9 | T0 disqualifiers (list can only grow) | duplicate suspicion; `EXTRACTION_CONFLICT`; `HIDDEN_TEXT`; new country; contact new or changed < 30 days; unknown sender; SWIFT rail; any degraded check (LLM, parser, screening); cap headroom < amount | None |
| 10 | T0 enabled by default | **Off**; turning it on needs a policy with 2 approver signatures | `policy.demo.yaml` turns it on, signed, labelled "demo policy: T0 on" |
| 11 | T1 band | Above T0 and < USD 10,000, no T2 trigger | None |
| 12 | T2 threshold | ≥ USD 10,000, or payee rolling 7-day aggregate incl. this item ≥ USD 10,000, or any T2 trigger; roster < 3 → `INSUFFICIENT_APPROVERS` | None |
| 13 | Per-run caps | T0 ≤ USD 6,000; all tiers ≤ USD 50,000 and ≤ 40 payments | None |
| 14 | Per-day caps (IST calendar day, all runs) | T0 ≤ USD 6,000; all tiers ≤ USD 75,000 and ≤ 60 payments; ≤ 2 runs; ≤ 5 beneficiaries created | None |
| 15 | Per-payee rolling 7 days | T0 aggregate ≤ USD 2,000; all-tier aggregate counts toward row 12 | None |
| 16 | Per-payee 24 h velocity | ≤ 1 T0 and ≤ 3 payments of any tier; a 4th is HARD_BLOCK until the next day | None |
| 17 | Per-approver daily total | ≤ USD 30,000 | None |
| 18 | Approval expiry and challenge | min(quote `valid_to_at` − 120 s, first signature + 4 h); WebAuthn challenge = packet hash + single-use nonce, ≤ 5 min; approvals consumed on use | None |
| 19 | Quote safety margin | Never book a quote with < 120 s validity left (`MIN_1` never bookable) | None |
| 20 | FX drift tolerance | ≤ 25 bp: CONVERSION binds `buy_amount` + `max_sell_amount` = approved sell × 1.0025 | None |
| 21 | Reserve floor | Must be set (demo USD 8,000); missing → executor refuses to start | — |
| 22 | Settle window (PAID → FINAL) | ≥ 48 h **and** ≥ the rail's business-day window (SEPA 3 TARGET2 days; FPS 3 UK days; ACH 2 US days); SWIFT never FINAL by timer | **Not used** (FINAL is not shortened; see Appendix A) |
| 23 | AMBIGUOUS escalation | Unresolved after ≤ 6 days → human; never auto-retry | None |
| 24 | Trip: clock skew | > 120 s vs the Airwallex `Date` header | None |
| 25 | Trip on first occurrence | non-sandbox host or redirect; audit write failure; policy parse/signature failure; reserve-floor re-check failure at execution | None |
| 26 | Trip: AMBIGUOUS creates | ≥ 2 in one run, or ≥ 2 in a rolling 24 h across runs | None |
| 27 | Trip: FAILED transfers | ≥ 3 in a rolling 1 h across runs | None |
| 28 | LLM vs parser identifier mismatch | That item → `EXTRACTION_CONFLICT` quarantine; trip only at ≥ 3 within 24 h | None |
| 29 | Trip on first occurrence (added) | any compliance-type `failure_type` (`ACCOUNT_UNDER_RESTRICTION`, `TM_SUSPENDED`, `CHANNEL_POLICY`) or `WATCHLIST_*` reason; any daily-cap breach attempt; audit-chain **verify** failure; an approval whose signature fails verification at the executor | None |
| 30 | Clearing the kill switch | 2 distinct approvers (passkey or labelled fallback) + a reason; expired approvals need re-signing | None |

**Code invariants (not configurable, not in YAML at all):** the duplicate lock; "original not terminal" block; the non-terminal-attempt block across runs; "quarantined/unverified payee" block; the sandbox guard; "T2 for new/changed details needs callback evidence"; executor signature re-verification.

### 4.16 Fail-closed defaults

| Failure | Safe default |
|---|---|
| LLM error, timeout or low confidence | Item → REVIEW; no T0 |
| Parser vs LLM disagreement | `EXTRACTION_CONFLICT` quarantine (row 28 rate trip) |
| Policy parse, signature or floor failure | Kill switch trips; process exits non-zero |
| DB unavailable / locked | Executor halts |
| Clock skew > 120 s | Kill switch trips |
| Webhook HMAC failure or timestamp outside tolerance | Drop, 401, alert; never touch state |
| Audit write failure | No API mutation; kill switch trips |
| `verify_account` error or flag off | "No evidence"; flow unchanged |
| Fingerprint computation error | QUARANTINE |
| Screening ERROR | HARD_BLOCK |
| Unknown `failure_type` | DEFAULT handler; escalate; never retry |
| Unknown transfer status | Keep previous state; incident `UNKNOWN_STATUS`; treat as non-terminal |
| Missing reserve floor | Executor refuses to start |

### 4.17 Example policy files
`policy.example.yaml` (shipped default; T0 off). `policy.demo.yaml` is identical except `t0.enabled: true` and `demo_timing: true`, and both carry two approver signatures in `policy.sig.json` / `policy.demo.sig.json`. Every key carries a comment naming its floor row.

```yaml
policy_version: "2026-11-01.1"
entity_id: "halden-robotics-demo"
base_currency: USD
reserve_floor: { USD: "8000.00" }                 # r21 (EUR/GBP floors 0 unless set)
roster:                                          # r12 / D6; unique emails; < 3 approvers → INSUFFICIENT_APPROVERS
  - { id: arun,  name: "Arun (AP clerk)",      role: approver, email: arun@halden.example  }   # SoD bars him on items he requested
  - { id: meera, name: "Meera (finance lead)", role: approver, email: meera@halden.example }
  - { id: kabir, name: "Kabir (founder)",      role: approver, email: kabir@halden.example }
  - { id: priya, name: "Priya (ops)",          role: ops,      email: priya@halden.example }   # records callbacks; never signs
bank_change:
  cooling_off_hours: 72                        # r1
  callback_contact_min_age_days: 30            # r2
  callback_validity_days: 7                    # r3
  contact_provenance_min_invoice_age_days: 90  # §4.5.2
  first_payment_cap_usd: "2500.00"             # r4
  first_payment_cap_median_fraction: "0.50"    # r4
  cap_lift_final_payments: 2                   # r5
t0:
  enabled: false                               # r10
  per_payment_limit_usd: "2000.00"             # r6
  min_final_payments: 3                        # r7
  min_payment_fraction_of_limit: "0.25"        # r7
  bank_details_unchanged_days: 60              # r7
  max_multiple_of_payee_median: "1.5"          # r8
  disqualifiers: [duplicate_suspicion, EXTRACTION_CONFLICT, HIDDEN_TEXT, new_country, contact_lt_30d,
                  unknown_sender, SWIFT, degraded_check, cap_headroom]   # r9
tiers:
  t2_threshold_usd: "10000.00"                 # r11/r12
  t2_payee_7d_aggregate_usd: "10000.00"        # r12
limits:
  per_run:      { t0_usd: "6000.00", all_usd: "50000.00", max_payments: 40 }                       # r13
  per_day:      { t0_usd: "6000.00", all_usd: "75000.00", max_payments: 60, max_runs: 2,
                  max_new_beneficiaries: 5, calendar_tz: "Asia/Kolkata" }                          # r14
  per_payee_7d: { t0_usd: "2000.00" }                                                             # r15
  per_payee_24h: { max_t0: 1, max_payments: 3 }                                                   # r16
  per_approver_day_usd: "30000.00"                                                                # r17
approvals: { max_validity_hours: 4, challenge_ttl_seconds: 300 }                                  # r18
fx: { quote_validity: HR_4, quote_safety_margin_seconds: 120, drift_bp: 25 }                     # r19, r20
settlement:                                                                                       # r22
  SEPA:  { business_days: 3, calendar: EUR_TARGET2, min_hours: 48 }
  FPS:   { business_days: 3, calendar: GBP_ENGLAND, min_hours: 48 }     # ASSUMPTION (labelled)
  ACH:   { business_days: 2, calendar: USD_FED,     min_hours: 48 }     # ASSUMPTION (labelled)
  SWIFT: { final_by_timer: false, presumed_settled_business_days: 10 }
ambiguous: { escalate_after_days: 6 }                                                            # r23
killswitch:
  clock_skew_seconds: 120                                                                        # r24
  ambiguous_creates_per_run: 2                                                                   # r26
  ambiguous_creates_rolling_24h: 2                                                               # r26
  failed_transfers_rolling_1h: 3                                                                 # r27
  extraction_conflicts_rolling_24h: 3                                                            # r28
  clear_signatures: 2                                                                            # r30
rails:
  flight_business_days: { SEPA: 2, FPS: 1, ACH: 2, SWIFT: 3 }
  cutoff_local_time:   { SEPA: "14:00", FPS: "14:00", ACH: "14:00", SWIFT: "12:00" }   # ASSUMPTION, conservative, not Airwallex data
  fee_reservation_usd: { SEPA: "5.00", FPS: "5.00", ACH: "5.00", SWIFT: "30.00" }      # reservation against the floor, NOT a fee estimate
vendor_category_reason:                          # transfer `reason` enum values
  freight: freight
  manufacturing: goods_purchased
  design_services: professional_business_services
  software: technical_services
  contractor: professional_business_services
demo_timing: false                               # true only in policy.demo.yaml; sandbox + host pin required
```
The roster is exactly the D6 cast. Because Arun requested the demo bills, he cannot sign them; Meera and Kabir provide the two T2 sign-offs. Removing any approver from the roster makes T2 items `INSUFFICIENT_APPROVERS` (tested).

