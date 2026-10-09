# Round 1 shortlist

**Owner:** Agentic Banking (orchestrator). **Written:** Thu 8 Oct 2026, ~7:45 PM IST.
**Inputs:** the 7 Round 0 memos in `board/round0/`, `board/DECISIONS.md` (candidates C1–C6, findings F1–F5), `raw/builds.json`, `raw/doc_*.txt`, and the finished research brief `00-hackathon-brief.md`. No other research files were finished at writing time; nothing below waits on the rest of the pack.

**Greenfield.** This shortlist references none of Vedant's past projects. Nothing was submitted, registered, or sent.

**Scoring lens (provisional, from `judge.md`).** Pain + real financial decision 25%, depth of real Airwallex API use 25%, safety controls 20%, reproducible demo 20%, originality + adoption 10%. Any unapproved money-movement path caps the total at 4/10. No official rubric exists (F1, F5).

---

## 1. Merged pain table

Numbers are copied verbatim from the memos. Where two memos disagree, both versions are shown and the conflict is flagged rather than averaged. Credibility notes are the memos' own caveats.

| # | Pain | Number (verbatim) | Source, year, URL | Credibility | Used by |
|---|---|---|---|---|---|
| P1 | Cash application is mostly exceptions, not straight-through | "70% of companies get at best 50% straight-through cash application" (product-design); "70% of companies have at best 50% straight-through processing" (banking-domain); "70% of companies get straight-through processing on 50% of payments or fewer" (senior-dev). Also "22% take a day or more to apply cash" / "22% take at least a day to apply cash"; top causes "deductions, disputes, and exceptions (58%)", "missing remittance info (55%)", "cash left unapplied too long (46%)" | BILL × Treasury Webinars, Jan 2026, n=211. https://www.bill.com/blog/cash-application-metrics | Vendor blog (BILL sells AR automation) reporting its own survey. Three memos paraphrase the same page slightly differently; the 70/22/58/55/46 figures are consistent across them. | C3, C5, C6 |
| P2 | Cash reconciliation dominates the close | "20–50 hrs a month" and "the #1 most time-consuming close task" (product-design); "20–50 hours/month across 3–5 systems" and "50% of teams take 6+ business days to close" (senior-dev, judge) | Ledge, *State of month-end close 2025*, survey of 100 finance professionals. https://www.ledge.co/content/month-end-close-benchmarks-for-2025 | Vendor-commissioned/published (Ledge sells close software). Sample "51 to 10,000+ employees" (product-design); senior-dev flags it skews to 51+ employees. | C3, C6, Judge P1 |
| P3 | Reconciliation is the top AR concern and almost un-automated below enterprise | "44% of US businesses rank data reconciliation as their most pressing AR concern"; "Only 9% of mid-market firms have automated reconciliation (24% of large firms)" | PYMNTS × Mastercard, *Accelerating the Time to Realized Revenue*, 2021. https://www.pymnts.com/news/b2b-payments/2021/44-pct-of-us-businesses-consider-data-reconciliation-most-pressing-ar-concern/ | Five years old (2021). Partnership research, not a regulator. US only. | C4 |
| P4 | Cross-border receipts land short, and the cause is opaque | **Conflict, do not merge:** CEO cites "~55% of SMEs reported landed amounts that did not cover the full invoice", "Typical deductions are $25–$50", "~3.5 hours of internal handling vs ~2 hours" (FXC Intelligence × Mastercard, *Principality at Risk*, 25 Jun 2026, https://mastercardcontentexchange.com/news/media/xl2l42gr/fxc_mc_whitepaper-en-final-25_06.pdf). Product-design cites "48% named hidden charges as their top frustration and 51% named high fees" among "10,000+ Indian businesses" (Skydo, https://www.skydo.com/blog/survey-on-how-indian-businesses-receive-interntaional-payments). Product-design and banking-domain both say **no credible public number exists for the share of cross-border B2B receipts that arrive short specifically because of intermediary deductions.** | See cells | FXC figure is "directional, n=41 SME interviews in Mexico, Brazil, and Colombia" (CEO's own caveat). Skydo sells cross-border collection to Indian exporters, so it is vendor-published and region-limited. The two numbers measure different things. | C3, C4 |
| P5 | FX and cross-border cost opacity | "82% of US SMB leaders don't believe their bank is transparent about cross-border costs or aren't sure" and "an estimated $800M was lost to hidden fees in 2023" (product-design, banking-domain). Separately, staff-engineer cites "1 in 3 SMBs struggle with manual reconciliation" and "32% cite high fees or opaque FX costs" | Wise-commissioned Censuswide survey, Apr 2024, n=1,003 US SMBs, plus a Capital Economics estimate for Wise. https://newsroom.wise.com/en-NAM/237198-hidden-costs-complexity-of-international-payments-threaten-small-business-expansion-new-research-reveals/ · Visa SMB page dated "05/01/2026": https://corporate.visa.com/en/sites/visa-perspectives/trends-insights/as-smbs-go-global-payment-complexity-remains.html | **Wise sells FX, so treat as directional** (banking-domain's caveat). The $800M is an estimate commissioned by Wise, not a measured loss. Visa page date order is ambiguous (staff-engineer) and the survey is Visa-commissioned (Basis Research, businesses under 250 employees). | C3, C5, C2 |
| P6 | Payments fraud, chiefly business-email compromise and vendor impersonation | "79% of organisations were hit by attempted or actual payments fraud"; "BEC was the No. 1 avenue, at 63%"; "Vendor imposter fraud reached 45%, up 11 percentage points"; "Wire transfers were the payment method most targeted by BEC, at 63%"; "Only 22% recovered 75% or more of lost funds". Corroboration: "$2,770,151,146 in BEC losses across 21,442 complaints" | AFP 2025 Payments Fraud and Control Survey, 2024 data, n=521. https://www.afponline.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024 (staff-engineer and judge link the same release on financialprofessionals.org). FBI IC3 2024: https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf | Strongest source in the set: an industry body, large n, primary press release, and compliance verified the IC3 dollar figure in the PDF. **Caveat:** "AFP's sample skews toward mid-size and large US corporates, not only SMBs" (staff-engineer). | C1, C2, C5, Judge P3 |
| P7 | Duplicate and erroneous disbursements | "median of 1.5%" of total annual disbursements processed as duplicate or erroneous payments, "sample: 1,686 companies" | APQC Open Standards Benchmarking, measure 105905. https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number | Only the median is public; the year and the quartiles are behind a member wall (compliance, staff-engineer). Counts disbursements, not dollars. A Corpay blog's 0.8%/2.0% split was **not verified** and is not used. | C1, C2 |
| P8 | B2B invoices are overdue, so cash is unpredictable | "43% of US credit-based B2B sales are overdue" (product-design, banking-domain, senior-dev); "47% of B2B invoices in Western Europe"; "44% across Asia" (product-design, senior-dev). Separately CEO cites "56% of US small businesses are owed money, $17,500 on average" and "47% have invoices more than 30 days overdue" | Atradius 2025: US https://group.atradius.com/dam/jcr:5609b617-ac29-4e30-8b01-0663a01d94bd/payment-practices-barometer-us-2025-en.pdf · W. Europe https://group.atradius.com/dam/jcr:80448207-97e5-4005-98b5-d5bb90e7107d/payment-practices-barometer-western-europe-2025-en.pdf · Asia https://atradius.at/dam/jcr:de5379ba-2ad5-415f-9c77-6e6c2669d13e/payment-practices-barometer-asia-2025-en.pdf · Intuit QuickBooks 2025, Jan 2025, n=2,487: https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2025/ | Atradius is an insurer publishing its own barometer; consistent across three memos. **Conflict inside P8:** the CEO's "47%" is QuickBooks ("invoices more than 30 days overdue" among US small businesses), not Atradius's "47% of B2B invoices in Western Europe". Same digits, different population. Do not combine them. | C3, C4, C5, C6 |

### Conflicts and exclusions

- **AFP 2025 vs AFP 2026.** Judge P3 cites a later edition: "More than three-quarters of organizations (76%) … experienced attempted or actual payments fraud in 2025" and "74% were affected by business email compromise (BEC) in 2025", n=465 US treasury practitioners (AFP press release, 14 Apr 2026, https://www.financialprofessionals.org/about/learn-more/press-releases/Details/over-75-percent-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags). That is a **different survey year** from the 79%/63% figures everyone else uses. Both stand; neither is a correction of the other.
- **Payout-delay 48%.** Judge P2 cites an Airwallex / Edgar, Dunn & Company survey of 1,000 SMBs (US, UK, China, AU, SG), Q3 2023: "delays in processing and disbursing payments (48 per cent)", "managing multiple payout methods and currencies … (47 per cent)", "Forced currency conversion … (41 per cent)" (https://www.airwallex.com/global/newsroom/demand-for-embedded-finance-soars-among-smbs-as-traditional-banks-fall-short). Host-published and three years old, so directional. Not used by any candidate memo.
- **ARP Digital 2026 is region-limited.** "72% of GCC and MENA SMEs reconcile cross-border payments manually", "47% … cite settlement delays", "24% cite failed or returned payments", "22% unexpected fees", "only 16% get same-day settlement", "200+ SMEs, Feb 2026" (staff-engineer, https://www.arpdigital.io/en/resources/news-insights/gcc-sme-cross-border-payments-2026). Staff-engineer says no equally recent global SMB return-rate figure was found.
- **Cross-border DSO.** "32 days vs 21 domestic (55% longer)"; correspondent fees and FX swings "a concern for 42% of US / 41% of UK" (senior-dev, PYMNTS × Visa, n=456, https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/48327/pymnts-innovating-cross-border-payments-what-us-and-uk-businesse.523e2320521f.pdf). Senior-dev flags the report as **undated in the extracted text**.
- **Dropped on purpose.** Staff-engineer excluded the "82% of small businesses fail because of cash flow" stat and a "15+ hours/week on reconciliation" vendor-blog figure for lack of a primary source. Compliance's Starling fine (£28,959,426, FCA 2024) documents a bank's sanctions-screening failure, not an SMB operator pain, and the guide has no sanctions-screening API, so it is not a build pain. Gartner's "18% of accountants make financial errors at least daily" (CEO, S4) is supporting colour only.

---

## 2. The three shortlisted ideas

All three target **Founder's Choice ($30,000)** and **Judges Choice ($20,000)**, both "Open category. No specific requirements." None targets the Visa or Metal awards: both require that partner's tooling, and none of the three ideas uses it. All run on the plain sandbox, so none needs the off-board email that kits 5–10 require (OPEN-2).

### S1. Ledgerline: the AR cash-application agent

Merges C3 Clearline, C4 Closer, C5 Unapplied and C6 Inbound. Working name is new so it isn't owned by one memo.

**Pitch.** When money lands in a multi-currency Airwallex Global Account, the agent matches it to open invoices, explains the gap, and acts: close, write off a fee, chase, refund to the original payer, or hold. New evidence flips the decision, and the books stay tied to Airwallex's own transactions.

**Buyer and user.** Buyer: the founder, controller, or fractional CFO of a 10–200 person firm that bills clients across borders (agencies, SaaS, exporters, studios) in the US, Europe, or APAC, already receiving into Global Accounts. User: the AR clerk or outsourced bookkeeper. Channel wedge, from C4: bookkeeping firms that close the books for many such clients.

**The decision, and what flips it.** For each deposit the agent chooses one of: apply, apply-and-write-off, chase, refund, or hold. Four inputs change the choice, one per guide trigger:
- *Evidence:* a remittance PDF showing 3% withholding tax flips "chase the $300" to "close the invoice, book a tax receivable, cancel the chase" (C3's beat; C4's variant is a certificate that deactivates a payment link).
- *Deadline:* a claimed early-pay discount whose window has closed flips an allocation into a deduction plus a chase draft (C5).
- *Risk:* a request to refund a duplicate to a **new** bank account is hard-blocked; the refund can only return to the account the deposit came from (C5, and C3's "refund only to the source").
- *Balance:* a `deposit.reversed` event reopens the invoice and reverses the write-off (C5, C6), and surplus foreign currency above a per-currency buffer is converted while cash needed for upcoming same-currency bills is held (C3, C6).

**Three-beat demo (under 5 minutes).**
1. **$9,700 vs a $10,000 invoice.** The card proposes chasing $300. A remittance PDF then shows 3% withholding tax, and the card flips to close + book a $300 tax receivable + cancel the chase, with the old and new plan side by side (C3).
2. **Duplicate, refunded once.** A second payment of the same amount is refunded to the original payer's account after one approval. A second approval click is blocked by the duplicate lock (C3), and an email asking for that refund to go to a new IBAN is refused and escalated (C5).
3. **Reversal, then surplus.** A settled deposit is reversed, so the invoice reopens (C5, C6). With applied cash now known, surplus EUR above the buffer converts to USD on a single-use quote, and the reserve still covers upcoming EUR bills (C3, C6).

C4's split-deposit beat (one receipt covering two invoices, with a $37.85 gap inside tolerance written off) is the opening seed, not a separate beat. C4's payment link for a real shortfall is a stretch, not a core beat (see sandbox unknowns).

**Approvals and guardrails.** Drawn from `compliance-risk.md` §"Controlled-autonomy guardrails", applied to receipts:
- Auto, in code: exact matches and variances at or under a per-currency cap that match a known fee pattern (C3, C5). The model reads remittance text and explains; it never does the arithmetic.
- One approver: any refund, any write-off above the cap, any FX conversion above an autonomous limit (C5).
- Two approvers, maker-checker, for refunds above a threshold (C5, guardrail 9). The agent proposes; it cannot approve.
- Refunds only to a beneficiary built from the deposit's own payer bank details. Bank details found in an email can only raise risk, never authorise a payout (guardrail 12, C3).
- One refund per deposit, capped at the overpaid amount, with a deterministic `request_id` and a duplicate lock (guardrails 5 and 6).
- Every approval is bound to amount, currency, counterparty, invoice ids and evidence hashes; any change voids it (guardrail 3).
- Unknown payer or no invoice match: hold and escalate, never auto-apply or auto-refund (C3).
- Append-only audit log, and a reconciliation that must tie out to `GET /financial_transactions` (guardrail 7, C5).
- Sandbox host only, typed tools, no raw credentials, kill switch, webhook HMAC plus dedupe on event id (guardrails 1, 8, 10, 14).
- No sanctions screening is claimed. The guide documents no such API (guardrail 17).

**Airwallex APIs.** Named in the memos or in `raw/doc_*.txt`:
- `GET /global_accounts`, `POST /global_accounts/create`, `GET /global_accounts/{id}/transactions`
- `GET /deposits`, `GET /deposits/{id}` (payer name, payer bank account, reference, fee, status)
- `POST /simulation/deposit/create` (takes `payer_name`, `payer_country`, `payer_bankname`, `reference`, `status`, per banking-domain)
- `GET /balances/current`, `GET /balances/history`
- `GET /fx/rates/current`, `POST /fx/quotes/create`, `POST /fx/conversions/create` (REST only; no MCP tool)
- `POST /beneficiaries/schema`, `POST /beneficiaries/validate`, `POST /beneficiaries/create`, `POST /transfers/create`, `GET /transfers`, `POST /simulation/transfers/{id}/transition`
- `GET /financial_transactions`
- Webhooks: `deposit.pending`, `deposit.settled`, `deposit.rejected`, `deposit.reversed` (`raw/doc_deposit_wh.txt`); `balance.ga.top_up` (product-design). `ga.new` exists only on API versions up to 2025-02-14 (F3, confirmed in `raw/doc_deposit_wh.txt`).
- Stretch: `POST /billing/invoices/create`, `POST /billing/invoices/{id}/mark_as_paid`, `POST /pa/payment_links/create`, `POST /pa/payment_links/{id}/deactivate` (C4, C5).

**Sandbox unknowns (day-one spike, untested by every memo).**
- Whether simulated deposits come back with `payer_name`, `reference` and `payer.bank_account` populated well enough to build a beneficiary. Senior-dev's reading of the docs says the simulator has **no reference field**; banking-domain says the simulator takes `reference`. Both can't be confirmed without a sandbox call, so the demo must not depend on it: remittance emails and PDFs are synthetic fixtures.
- Whether `deposit.*` webhooks fire for **simulated** deposits. Fallback: poll `GET /deposits`.
- Whether a **bank-transfer** deposit can be reversed. Banking-domain notes the docs label reverse/settle/reject as "Direct Debit", so the reversal beat may have to be simulated in our own ledger and labelled as such on screen.
- Whether one sandbox account can hold several Global Accounts (C6's per-customer account idea) and whether Billing and Payment Links are enabled (C4). Both are stretch, not core.
- Whether `GET /financial_transactions` shows fee and conversion rows promptly (staff-engineer; unverified).

**Three-week solo feasibility.** Orchestrator estimate, not yet reviewed by AB Staff Engineer: feasible, at roughly the medium-high confidence staff-engineer gave S2's comparable scope, **if the demo is frozen at the three beats above**. Invoices live in a local table; the accounting output is a CSV. Cut payment links and billing first, then per-customer Global Accounts. No platform access and no allowlist needed. Week 1 is the typed client plus the ledger; week 2 is matching, the evidence flip and the refund lock; week 3 is the one-page UI, the video and the README.

**Overlap.**
- *Reference builds* (`raw/builds.json`): none of the five does cash application. "Invoicing in Slack" creates invoices and payment links; "AI finance manager" reads balances and prepares payments. S1 neither sends invoices from Slack nor chats about balances. Low overlap.
- *Starter kits:* none covers reconciliation. The guide says so: "Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them." The refund beat borrows kit 3's discipline (never pay twice) but applies it to returning money to a customer, which kit 3 doesn't do. Kits 1–4 need no enablement.

**Prize lane.** Founder's Choice and Judges Choice. Not Visa, not Metal.

### S2. PayRun Warden: the supplier payment-run agent with a payee-change lock

Merges C1 PayeeLock and C2 PayRun Warden. Keeps C2's name because it describes the whole run, not only the lock.

**Pitch.** The agent runs a cross-border SMB's weekly supplier payment run in USD, GBP and EUR: code, not the model, decides pay, convert, defer or escalate under a cash-reserve floor, and it holds any payout to a supplier whose bank details just changed until a human confirms them out of band.

**Buyer and user.** The founder, finance lead, or ops person at a 10–200 person company paying suppliers and contractors in several currencies from one Airwallex wallet (C2). The approver is the controller or the founder.

**The decision, and what flips it.** For each invoice: pay, convert-then-pay, defer, or escalate. What changes it:
- *Risk:* an email from a lookalike domain giving a new IBAN in another country flips "pay" to "hold", and the old beneficiary stays in force until an out-of-band confirmation is recorded (C1, C2).
- *Evidence:* the original transfer's status. A "never arrived, please pay again" request is refused while the original is `SENT`, which is not final; only after a simulated bank return does exactly one replacement go out, under a new `request_id` (C1).
- *Balance:* a customer deposit landing mid-run re-opens only the decisions the new cash changes, so a deferred invoice can now be paid without breaching the reserve floor (C2, and kit 1's own rule).

**Three-beat demo.**
1. **Payee change.** Five invoices across USD, GBP and EUR; the plan is pay three, convert one, defer one. An email "from" the EUR supplier changes its IBAN, so that invoice freezes and the other four proceed.
2. **Returned payment.** The GBP payout goes SENT then fails with a bank-return type. The agent records the original's fate before sending exactly one replacement, and a second replacement is blocked.
3. **Cash arrives.** A simulated customer deposit lands, the reserve floor still holds, and the deferred invoice is paid. The close shows each invoice tied to its transfer, conversion and fee, with the true FX cost per invoice.

**Approvals and guardrails.** The full list in `compliance-risk.md` was written for this shape of product:
- Any new or changed beneficiary, any replacement or re-send, any amount above threshold, and any FX conversion above the confidence-adjusted limit needs approval (guardrail 3). Small LOCAL payouts under a threshold can run autonomously (C2).
- Approvals are signed records of amount, currency, beneficiary id, invoice id and evidence hashes; a re-quote or a different beneficiary voids them.
- Autonomous payouts only to beneficiaries on a verified allowlist, with a cooling-off period for anything new (guardrail 4). `POST /beneficiaries/validate` proves the details are well-formed, not that they belong to the vendor.
- `POST /beneficiaries/verify_account` (in `raw/doc_verify.txt`, not in the memos' API lists) adds a real name-match signal for UK Faster Payments (Confirmation of Payee) and SEPA EUR (Verification of Payee). **Not yet confirmed to work in the sandbox, and the doc says UK CoP is enabled on request**, so it is a spike, not a commitment. Anything other than `FULL_MATCH` holds.
- Deterministic `request_id` per invoice + beneficiary + version, and a check of `GET /transfers` before any replacement (guardrail 5). A failed transfer ends `CANCELLED`; `SENT` is not final; `PAID` is not always final either (`raw/doc_tstatus.txt`).
- Reserve floor and the flat EUR 12.85 SWIFT fee are applied in code before converting (guardrail 15).
- Segregation of duties: the person or agent that changes a beneficiary cannot approve paying it (guardrail 9). Emails and PDFs are data, never instructions (guardrail 12).
- Hash-chained audit log, kill switch, sandbox-only egress, typed tools, webhook HMAC and dedupe (guardrails 1, 7, 8, 10, 14).
- Screening stays a stub. The README must say real sanctions screening is not performed (guardrail 17).

**Airwallex APIs.** All named by C1 or C2:
- `POST /authentication/login`, `GET /balances/current`, `GET /global_accounts`, `POST /global_accounts/create`, `POST /simulation/deposit/create`
- `GET /fx/rates/current`, `POST /fx/quotes/create`, `POST /fx/conversions/create` (REST only)
- `POST /beneficiaries/schema`, `POST /beneficiaries/validate`, `POST /beneficiaries/create`
- `POST /transfers/create`, `GET /transfers`, `POST /simulation/transfers/{id}/transition`
- `GET /financial_transactions` (source types PAYOUT, CONVERSION, FEE)
- Webhooks `payout.transfer.paid`, `.failed`, `.cancelled`
- Spike, from `raw/doc_verify.txt`: `POST /beneficiaries/verify_account`
- Optional stretch named by C2: issuing card freeze, `GET /audit_log/security_audit_logs`. Cut first.

**Sandbox unknowns.**
- Whether fee and conversion rows appear promptly in `GET /financial_transactions` (staff-engineer: unverified; fallback is the transfer and conversion objects plus the guide's documented EUR 12.85 fee).
- Whether `verify_account` returns anything meaningful in sandbox, and for which corridors. UK CoP needs an enablement request per the doc, which is off-board contact, so the core demo cannot depend on it.
- Transfer-state timing: a FAILED transition auto-cancels within seconds, so a slow poll can lose `failure_reason` (staff-engineer, from the guide).

**Three-week solo feasibility.** Staff-engineer judged this shape feasible for one person at medium-high confidence, and it is the most buildable of the three because every API is in kits 1 and 3, which need only a funded wallet. The risk is scope, not access. Freeze at one scripted run, three currencies, three exceptions. Design only until the build phase opens on Sun 25 Oct 2026, 10:00 AM IST (F2: the rules don't say whether earlier code is allowed).

**Overlap. This is S2's real weakness.**
- *Starter kits:* it combines kit 1 (Adaptive Treasury Controller: fund, convert, defer, escalate under a reserve floor, re-plan after a deposit) and kit 3 (Payment Ops Incident Commander: resolve a delayed transfer without paying twice). Both beats will be crowded. The payee-change lock is the part no kit covers (compliance's own caveat).
- *Reference builds:* "AI finance manager" already shows an agent that reads balances, prepares a payment and waits for a yes. S2 has to look clearly deeper than that: the lock, the state machine and the per-invoice reconciliation, not a chat window.

**Prize lane.** Founder's Choice and Judges Choice. Visa and Metal are out of scope (C2).

### S3. Float: the multi-currency cash-placement agent

Not a re-skin of S1 or S2. Grounded in the guide's own whitespace line, quoted by the CEO, product-design, banking-domain, senior-dev and judge memos: *"Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them."* Every candidate memo spent the reconciliation half of that sentence. Nobody took the cash-placement half. Kit 1 decides which **bills** to pay when cash is short. Float decides where cash **sits** when it isn't short: which currency to hold, which to convert, and when a change in rates, bills or risk reverses that.

**Why it is distinct.** S1's question is "which invoice does this deposit pay?" S2's question is "which supplier do we pay, and is the payee safe?" Float's question is "in which currency should today's surplus sit until it is needed?" It never matches an invoice and it never pays a supplier. Its only money movement is FX conversion, plus a hold. A team could ship Float without building any of S1's matching or S2's payout state machine.

**Pitch.** Each day the agent looks at balances in USD, EUR and GBP, the bills due in each currency over the next two weeks, and live FX quotes, then decides what to hold as a natural hedge and what to convert. When a bill, a rate, or a risk changes, it unwinds only the conversions that decision no longer supports.

**Pain grounding.** P5 (FX cost opacity) plus Judge P2's "Forced currency conversion leading to high transaction fees … (41 per cent)" and senior-dev's "FX swings … 42% of US / 41% of UK". No memo cites a source on idle or mis-placed currency balances specifically, so S3 has the thinnest evidence of the three.

**Buyer and user.** The founder-operator or finance lead at a 10–200 person exporter or agency that both receives and pays in several currencies and has no treasurer. This is the same firm as S1 and S2's buyer, but the job is the treasurer's, done weekly, not the AR clerk's daily task or the AP run.

**The decision, and what flips it.** For each currency balance: hold, convert, or escalate. Code applies the rules; the model reads the one unstructured input (the customer email below) and explains.
- *Balance:* EUR held against a supplier bill due in 10 days is a natural hedge and is not converted (senior-dev's hold-vs-convert beat, promoted from a side action to the whole product). A later deposit that pushes EUR above the buffer flips the surplus to "convert".
- *Deadline:* when that bill is deferred or cancelled, the hedge no longer has a purpose, so the held EUR flips to "convert".
- *Evidence:* a customer email (unstructured, read by the model) says an expected EUR receipt will slip two weeks. EUR coverage for the upcoming bill is now short, so a queued EUR→USD conversion is cancelled. This is the only beat where the model reads text, which is a weakness against the guide's "use the model to read unstructured text".
- *Risk:* a fresh quote that moves the rate past a threshold set in code flips a queued conversion to "escalate", because the assumption it was priced on has expired. Quotes are single-use and expire (`raw/doc_fxquote.txt`: validity options from 1 minute to 24 hours). A conversion that would take any currency under its reserve floor is refused outright.

**Three-beat demo.**
1. **Hold.** Balances in three currencies, bills due in EUR within 10 days. The plan holds the EUR as a natural hedge, converts only the GBP surplus above its buffer, and shows the bill, the buffer and the quote it priced against.
2. **The bill moves.** The EUR supplier invoice is deferred 30 days. The agent unwinds only that hold and converts the released EUR to USD on a new quote. The GBP hold, backed by a bill still due, is untouched.
3. **The rate moves.** A second conversion is queued, but the requote breaches the threshold in code, so the agent escalates instead of executing and shows both quotes. The reserve floor in every currency still holds, on screen, before and after.

The customer-email evidence flip is the alternate beat 3 if the sandbox quotes barely move (see unknowns).

**Approvals and guardrails.** From `compliance-risk.md`, the ones that apply to FX:
- Conversions above an autonomous limit, and any conversion near the reserve floor, need approval bound to amount, currency pair, quote id and the bill evidence (guardrail 3). A requote voids the approval.
- The reserve floor and the decision to hold are code, not prompt (guardrail 15). A conversion that breaks the floor is blocked, not retried.
- Quotes are single-use; on expiry the agent requotes and re-asks (banking-domain's failure mode).
- Idempotent `request_id` per conversion intent, so a timeout can't book it twice (guardrail 5).
- No beneficiary and no transfer is created. That is deliberate: it removes the payee-fraud surface entirely, and the README should say so rather than imply payout controls it doesn't have.
- Audit log of every quote, decision and conversion (guardrail 7); sandbox only; typed tools; kill switch that halts the conversion tool (guardrails 1, 8, 10).

**Airwallex APIs.** All named in the memos:
- `GET /balances/current`, `GET /balances/history`
- `GET /global_accounts`, `POST /simulation/deposit/create` (to land the surplus mid-demo)
- `GET /fx/rates/current`, `POST /fx/quotes/create`, `POST /fx/conversions/create` (REST only, no MCP tool, per the guide and `raw/doc_fxquote.txt`)
- `GET /financial_transactions` to show the `CONVERSION_BUY` / `CONVERSION_SELL` rows afterwards
- No beneficiaries, no transfers, no issuing.

Bills and due dates are synthetic fixtures, the same way every memo treats invoices. Nothing in the docs read here shows Airwallex holding a bill calendar, so the agent cannot discover payables from the API. That constraint is stated in the demo, not hidden.

**Sandbox unknowns.**
- Whether conversions settle immediately and completely in sandbox (the guide, via `00-hackathon-brief.md` §8, says they settle immediately; not tested by this board).
- Whether `GET /financial_transactions` shows both legs of a conversion promptly (the same unverified gap as S1 and S2).
- How wide sandbox quotes move. If they barely move, beat 3 has to be driven by a threshold the demo sets, with the live quote shown beside it, not by a faked rate.

**Three-week solo feasibility.** The smallest of the three by API surface: one product family plus balances. A solo builder can have the loop running in week 1 and spend weeks 2 and 3 on the decision log, the UI and the video. The risk is not scope. It is whether judges find a convert-or-hold decision as compelling as one that pays someone. Mitigation: every beat ends in a real conversion or a visible refusal, with balances on screen.

**Overlap.**
- *Starter kits:* closest to kit 1, more than "adjacent". Kit 1 also converts under a reserve floor, re-plans after a deposit, and (per `00-hackathon-brief.md` §7) ties "the autonomous FX limit to forecast confidence". The difference is that kit 1 ranks bills and pays them under scarcity, while Float never creates a transfer and works on surplus. A judge could still read it as kit 1 without the payouts. The guide's cash-placement line is unmet by any kit.
- *Yield placement:* `YIELD` appears as a balance-activity transaction type in `raw/doc_finrep.txt`, which hints at a yield product, but no memo or raw doc names an API for placing funds into it. Out of scope; do not claim it.
- *Reference builds:* "AI finance manager" computes runway from balances. Float books conversions under a written policy. Overlap is the balance read, nothing more.
- *S1 and S2:* both mention surplus conversion as a closing beat. Float's defence is that placement is its entire decision, with hold-vs-convert-vs-unwind shown three times, not a tail action after reconciliation. If the board later folds placement back into S1, Float should be dropped rather than shipped as a feature of it.

**Prize lane.** Founder's Choice and Judges Choice. Not Visa, not Metal.

---

## Cross-memo conflicts and gaps

1. **Simulated deposit `reference` field.** Banking-domain, CEO and product-design say `POST /simulation/deposit/create` takes `reference`; senior-dev says it has "no reference field". Unresolved until a sandbox call. S1 must not depend on it.
2. **Deposit webhooks.** DECISIONS.md F3 says the deposit-received webhook "only exists on API versions up to 2025-02-14". `raw/doc_deposit_wh.txt` shows that applies only to the legacy `ga.new` event; `deposit.pending/settled/rejected/reversed` are current events. Product-design's own memo was precise about `ga.new`; the F3 summary is overbroad. Whether they fire for **simulated** deposits is still untested.
3. **Deposit reversal on bank transfers.** Banking-domain notes the simulator labels reverse as "Direct Debit"; the webhook doc describes `deposit.reversed` as "recalled by the payer's bank" for both rails. Unverified for simulated bank-transfer deposits.
4. **The three AFP "63%" figures.** Compliance and banking-domain give "BEC … 63%" as the top avenue and "wires … 63%" as the top BEC target; staff-engineer adds "Third-party impersonation (63%) is the most common BEC type". Three different claims share one number. Check the press release before quoting any of them in the idea text.
5. **AFP 2025 vs 2026.** The Judge's 76% / 74% are the newer edition (2025 data); everyone else uses 79% / 63% (2024 data). Use the 2026 numbers as "latest" and the 2025 ones only with their year.
6. **"47%".** QuickBooks (US small businesses with invoices more than 30 days overdue) and Atradius (Western Europe B2B invoices overdue) share the number but not the population.
7. **Short-landing receipts.** CEO cites ~55% (n=41, LatAm); product-design and banking-domain say no credible figure exists. Both are honest; the CEO's number is the only one and is tiny.
8. **Wise.** The memos cite a US Censuswide survey (82% / $800M). The research pack's `raw/wise.txt` is a different, UK Wise report whose "82%" is a separate stat (82% agree regulation should push banks to be transparent). Don't let the two merge in later drafts.
9. **Buyer size.** CEO and staff-engineer say 10–200 people; product-design says roughly 10–500. The shortlist uses 10–200.
10. **Partner identity.** Product-design inferred the "AI accounting, MCP server, sandbox" partner is Light; staff-engineer and `00-hackathon-brief.md` say it is T:0 / tZERO (logo alt text). The landing HTML contains both strings. It matters only if S1 pitches an accounting-partner integration.
11. **Reference-build count.** `raw/builds.html` says "7 Reference builds" but `raw/builds.json` lists 5 (Agent cards, Drop-in checkout, Invoicing in Slack, AI finance manager, Allocard). Overlap above is checked against those 5 only.
12. **`PAID` is not final.** The memos only say `SENT` is not final. `raw/doc_tstatus.txt` says a transfer can still move from `PAID` to `FAILED`. Every refund and payout state machine must keep listening after `PAID`.
13. **`verify_account`.** No memo names `POST /beneficiaries/verify_account`; it is in `raw/doc_verify.txt` (UK CoP and SEPA VoP name-match). It strengthens S2 and S1's refund path, but sandbox support is untested and UK CoP needs enablement on request.
14. **Still open from DECISIONS.md.** OPEN-1 (judging criteria and idea-form fields, likely behind the HackerEarth login) and OPEN-2 (kits 5–10 access email, not needed by any shortlisted idea).

---

## 3. Orchestrator note (provisional, pending the Judge's scoring)

S1 (Ledgerline) looks strongest against the Judge's provisional rubric: it is the pain with the most independent support (four of the seven memos, plus the Judge's own P1 and the guide's whitespace line), it flips a decision on evidence, deadline, risk and balance within one workflow, and it moves money under the strictest approval rules the compliance memo wrote, while its only kit overlap is a discipline it borrows rather than a kit it copies. S2 is the safer build and the stronger fraud story, but kit 1 and kit 3 already script two of its three beats, so it has to win entirely on the payee-change lock. S3 is the cleanest whitespace and the smallest build, but its evidence is thinnest (cited FX-cost pains, nothing on idle-currency placement itself), it overlaps kit 1 more than its framing suggests, and it never pays anyone, which weakens Airwallex-depth scoring. The biggest risk to S1 is sandbox fidelity: if simulated deposits don't carry payer details or can't be reversed, beats 2 and 3 lean on our own ledger, and the Staff Engineer should spike that before the Judge's score is treated as final. This ranking is provisional until AB Judge scores all three on the published rubric.
