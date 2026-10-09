# Round 0: Banking domain brief

**Author:** AB Banking Domain · **Date:** 2026-10-08 · **Lens:** domain realism. Does this match how finance teams actually work?

---

## 0. What the organisers say: judging, deliverables, dates

**There are no formal judging criteria on the page.** As of 2026-10-08 the landing page (https://airwallex.hackerearth.com/) has About, Tracks, Key dates, Prizes, Partners and FAQ sections, and no rubric. The HackerEarth challenge page (https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/) shows phases only. Its `/judging-criteria` and `/rules` paths redirect. Below are the closest verbatim official statements, which we should treat as the de facto rubric.

**A. Builder guide, "Build around a financial decision"** (https://airwallexdev.com/guide), verbatim:
> "Choose a finance task that someone repeats and identify the decision inside it. The agent should choose differently when a balance, deadline, piece of evidence, or risk changes. Let the agent move money or update financial state, and state which actions require a person's approval."
> "In the demo, show the user's goal, the agent's initial plan, the new information, the revised decision, and the resulting balance, payment, or status. Keep amounts, limits, reserves, validation, duplicate protection, and state transitions in code. Use the model to read unstructured text, compare evidence, propose a plan, and explain an exception. Give the model typed tools rather than unrestricted credentials, and bind each approval to the amount, currency, counterparty, purchase terms, and evidence shown to the approver."
> "Finish the demo with a financial action or an escalation to a person. If the agent should make the same choice every time, write the rule in code instead of asking a model to narrate it."

The guide also says: *"Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them. Good territory if you want a problem few other builders will take on."*

**B. Airwallex judge signal, from a different event.** Sam Waldo (Head of Startups, Asia, Airwallex) judged the AI Tinkerers SG hackathon on 12 Sep 2026. Its post (https://www.linkedin.com/posts/ai-tinkerers-singapore_what-happens-when-ai-agents-move-beyond-conversationand-activity-7500499794403049472-36H9) lists his questions verbatim: *"Does this solve a genuine problem for founders or operators? / Can it work across markets, currencies and business environments? / Is there a credible path from prototype to adoption? / Has the team built the operational foundation—not only the interface? / Does the system balance autonomous execution with appropriate control?"* This is a proxy only. It is not this hackathon's rubric.

**Deliverables, from the landing page FAQ:** "A working demo, a short video walkthrough under five minutes, and a link to your repository with setup instructions." Teams are 1–4 people. Prizes are Founder's Choice $30K and Judges Choice $20K (both "Open category. No specific requirements"), plus Visa Award $15K and Metal Award $15K, each requiring that partner's tooling.

**Key dates:**

| Milestone | Landing page | HackerEarth (UTC → IST) |
|---|---|---|
| Applications close | Oct 23 | Registration & Idea Phase ends Oct 23 18:29 UTC = **Oct 23, 23:59 IST** |
| Build starts | Oct 25 (teams notified) | Oct 25 04:30 UTC = **Oct 25, 10:00 IST** |
| Submissions due | Nov 13 | Nov 13 18:29 UTC = **Nov 13, 23:59 IST** |
| Finalists | Nov 15 | n/a |
| Demo Day (SF, remote optional) | Nov 19 | n/a |

---

## 1. Top 3 operator pains

### Pain 1: Cash application. Matching incoming money to invoices is still mostly manual.
- **Who feels it:** AR specialist or clerk, AR manager, controller at month-end. For a founder-led SMB, the founder.
- **How it runs today:** Each morning someone exports the bank feed and works through a spreadsheet. Payer names don't match the customer master ("AMZN… ", "ACME GMBH" vs "Acme Holdings"), and references are missing or truncated. Remittance advice arrives separately by email or PDF. Short-pays and deductions get parked in "unapplied cash" while someone emails the customer. Nothing gets posted to the ERP until a human decides.
- **Numbers:**
  - In a BILL × Treasury Webinars survey (Jan 2026, n=211), **70% of companies have at best 50% straight-through processing** and 22% take at least a day to apply cash. The most common problems were deductions/disputes/exceptions (58%), missing remittance info (55%) and "cash unapplied too long" (46%). Source: https://www.bill.com/blog/cash-application-metrics
  - The Hackett Group (Aug 2025) says many organisations accept **automation rates below 40%, take up to 3 days to post payments, and carry up to 6% unapplied cash**. Source: https://www.thehackettgroup.com/ai-software-e-payments-hackett-cash-vendors/
  - Why it hurts: **43% of US credit-based B2B sales are overdue** (Atradius 2025; average terms 45 days). If you can't tell which invoices are actually paid, collections chase the wrong customers. Source: https://group.atradius.com/knowledge-and-research/reports/b2b-payment-practices-trends-in-north-america-2025

### Pain 2: Cross-border receipts arrive short, and FX costs are opaque.
- **Who feels it:** AR plus a founder or finance lead selling internationally.
- **How it runs today:** A EUR or GBP customer pays by SWIFT. Intermediary or lifting fees and FX margin mean the receipt is smaller than the invoice. Someone has to decide whether to write off the difference, re-bill it, or chase. Foreign-currency balances then sit idle until someone remembers to convert.
- **Numbers:**
  - A Wise-commissioned Censuswide survey (Apr 2024, n=1,003 US SMBs) found **82% either don't believe their bank is transparent about cross-border costs or aren't sure**. Capital Economics, also for Wise, estimates US SMBs lost **~$800M to hidden fees on international payments in 2023**. Source: https://newsroom.wise.com/en-NAM/237198-hidden-costs-complexity-of-international-payments-threaten-small-business-expansion-new-research-reveals/
  - Caveat: Wise sells FX, so treat these as directional.
  - **Gap:** I found no credible figure for how often B2B SWIFT receipts arrive short. Don't claim one.

### Pain 3: Outbound money movement is the fraud surface, especially "please send it to our new account."
- **Who feels it:** AP and treasury, plus whoever approves payments (controller or CFO).
- **How it runs today:** Refunds, supplier payments and bank-detail changes are requested over email. Approvers see an amount but often not the evidence behind it. Callback verification happens inconsistently.
- **Numbers:** From the AFP 2025 Payments Fraud & Control Survey (2024 data, n=521):
  - **79% of organisations hit by attempted or actual payments fraud**
  - BEC was the top avenue (63%)
  - **Vendor-imposter fraud 45%, up 11 percentage points**
  - Wires were the method most targeted by BEC (63%)
  - Only 22% recovered 75% or more of lost funds

  Source: https://www.afponline.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024

---

## 2. The one idea I'd back: an AR cash-application and reconciliation agent on Airwallex Global Accounts

**Working name: "Unapplied."** Every inbound deposit on a multi-currency Global Account (USD/EUR/GBP) gets matched to open invoices. The agent decides what to do with each one:
- apply it
- apply it and write off a fee within tolerance
- open a deduction and draft the chase
- refund an overpayment or duplicate
- hold it in suspense and escalate

It then converts surplus foreign currency above an operating buffer into the home currency. Code handles matching tolerances, amounts and state. The model reads remittance emails and PDFs, compares evidence and explains exceptions.

**Demo arc (fits the guide's goal → plan → new info → revised decision → result):**
1. **Seed.** 8 open invoices across 3 currencies. Fire 5 simulated deposits with realistic `payer_name`/`reference` noise: an exact match, a EUR SWIFT short-pay of a few euros, a lump sum covering two invoices, a duplicate payment, and an unidentified payer.
2. **Initial plan.** The agent auto-applies 2, writes off the small short-pay to bank charges (inside tolerance), proposes refunding the duplicate, and parks the unidentified one.
3. **New information.**
   - A remittance email says the lump sum was "INV-1043 + INV-1047 less 2% early-pay discount." The code checks the payment date against the terms window. If the discount was unearned, it reverses the plan to a deduction plus a chase draft.
   - A second email from the "customer" asks for the duplicate refund to go to a **new bank account**. The agent refuses to change the payee, because the refund must go to the account the money came from. It escalates as suspected BEC (Pain 3).
   - One deposit gets **reversed** (`deposit.reversed`), so the agent un-applies it and reopens the invoice.
4. **Money moves.** After maker-checker approval, the agent sends one refund transfer to the verified original payer account. It books one FX conversion of surplus EUR→USD above the buffer on a single-use quote.
5. **Close the loop.** It produces a reconciliation report showing applied + unapplied + suspense + refunded = deposits, tied to Airwallex Financial Transactions, plus an ERP-ready journal export and an audit log.

**Why it wins on each official statement:**
- *"A finance task that someone repeats":* Cash application is daily work (BILL: 70% at ≤50% STP).
- *"Choose differently when a balance, deadline, piece of evidence, or risk changes":* All four happen in the demo. Evidence: the remittance email. Deadline: the discount window. Risk: the payee-change request. Balance: the reversal, plus the FX buffer.
- *"Move money or update financial state":* Invoice state changes, a refund payout and an FX conversion.
- *"State which actions require a person's approval":* An explicit policy table (below).
- *"Amounts, limits, reserves, validation, duplicate protection, state transitions in code":* Match tolerances, write-off caps, FX buffer, `request_id` idempotency and a ledger state machine all live in code.
- *"Model to read unstructured text, compare evidence… explain an exception":* Remittance parsing and fuzzy payer resolution are genuinely LLM-shaped work.
- *"Bind each approval to amount, currency, counterparty… evidence":* The approval card hashes {amount, currency, beneficiary id, invoice ids, evidence doc ids}. Any change invalidates it.
- *"Finish with a financial action or an escalation":* Both happen.
- **Open territory:** The guide flags reconciliation as un-kitted. Most teams will build Kits 1–4, so we stand out.
- **Proxy questions:** It's a genuine operator problem, it's multi-currency by design, and the adoption path is "plugs in beside the ERP." Its operational foundation is the ledger, reconciliation and idempotency, with autonomy bounded by policy.

**Realism checks:**
- **Approval policy (in code):**
  - Auto: apply exact or ≤tolerance matches; write off ≤ the configured cap (e.g., ≤€15 or ≤0.5%).
  - One approver: any refund; any FX conversion above an autonomous limit; any write-off above the cap.
  - Two approvers (maker-checker, different users): refunds above a threshold. The agent can *propose* a payment but never approve one.
- **Payee controls:** Refunds go only to a beneficiary built from the original deposit's `payer.bank_account`. Any request for a different account is hard-blocked and escalated. Agent tools cannot edit beneficiaries.
- **Audit trail:** An append-only event log records each decision, its inputs (deposit id, invoice ids, evidence hash), the policy rule fired, model rationale, approver and timestamp. Reconciliation must tie to `GET /financial_transactions`.
- **Human in the loop:** Every outbound money movement and every customer-facing email is draft-only. The agent never sends customer mail itself.
- **Failure modes we demo or handle:**
  - Deposit reversed after application.
  - Duplicate webhook delivery: dedupe on event id, since delivery is at-least-once.
  - Transfer ends CANCELLED with a `failure_type`: the invoice stays "refund pending" and nothing is re-sent without a new approval.
  - FX quote expired: requote, never reuse.
  - Ambiguous match (two invoices with equal amounts): escalate, don't guess.
  - Partial-application rounding: the code holds amounts in major units with currency precision.

---

## 3. Airwallex APIs it would exercise

Paths per https://airwallexdev.com/guide and https://www.airwallex.com/docs/api. Base URL: `https://api.sandbox.airwallex.com`.

| API (docs name) | Endpoints | Used for | Doc |
|---|---|---|---|
| Authentication · API Access Token | `POST /api/v1/authentication/login` | 30-min bearer token | https://www.airwallex.com/docs/api/authentication/api_access_token |
| Core Resources · Global Accounts | `GET /api/v1/global_accounts`, `POST /api/v1/global_accounts/create`, `GET /api/v1/global_accounts/{id}/transactions` | USD/EUR/GBP collection accounts; per-account inbound feed | https://www.airwallex.com/docs/api/core_resources/global_accounts |
| Core Resources · Deposits | `GET /api/v1/deposits`, `GET /api/v1/deposits/{id}` | Deposit detail: `payer.name`, `payer.bank_account`, `reference`, `fee`, status `PENDING/SETTLED/REJECTED/REVERSED` | https://www.airwallex.com/docs/api/core_resources/deposits |
| Simulation · Deposits | `POST /api/v1/simulation/deposit/create` (takes `payer_name`, `reference`, `payer_country`, `payer_bankname`, `status`), `POST /api/v1/simulation/deposits/{id}/reverse` | Seed realistic messy receipts; reversal beat | https://www.airwallex.com/docs/api/simulation/deposits |
| Core Resources · Balances | `GET /api/v1/balances/current`, `GET /api/v1/balances/history` | FX buffer check, before/after proof | https://www.airwallex.com/docs/api/core_resources/balances |
| Transactional FX · Rates / Quotes / Conversion | `GET /api/v1/fx/rates/current`, `POST /api/v1/fx/quotes/create`, `POST /api/v1/fx/conversions/create` (REST only; no MCP tool) | Show the rate in the approval card; convert surplus EUR/GBP on a single-use quote | https://www.airwallex.com/docs/api/transactional_fx/quotes · …/conversion · …/rates |
| Payouts · Beneficiaries | `POST /api/v1/beneficiaries/schema`, `POST /api/v1/beneficiaries/validate`, `POST /api/v1/beneficiaries/create` | Refund beneficiary built from the original payer's bank details | https://www.airwallex.com/docs/api/payouts/beneficiaries |
| Payouts · Transfers | `POST /api/v1/transfers/create`, `GET /api/v1/transfers`, `GET /api/v1/transfers/{id}` | Approved refund of a duplicate or overpayment; poll to terminal state | https://www.airwallex.com/docs/api/payouts/transfers |
| Simulation · Transfers | `POST /api/v1/simulation/transfers/{id}/transition` | Drive the refund SENT→PAID or →FAILED | https://www.airwallex.com/docs/api/simulation/transfers |
| Finance · Financial Transactions | `GET /api/v1/financial_transactions` | Ledger-to-bank tie-out (DEPOSIT, PAYOUT, CONVERSION_BUY/SELL, FEE) | https://www.airwallex.com/docs/api/finance/financial_transactions |
| Webhooks | `POST /api/v1/webhooks/create` (or set up in the web app); events `deposit.pending/settled/rejected/reversed`, `payout.transfer.paid/failed/cancelled` | Event-driven trigger; HMAC-SHA256 verify; dedupe on event id | https://www.airwallex.com/docs/api/webhooks/webhooks · https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events/deposits |
| *(stretch)* Billing · Invoices / Payment Acceptance · Payment Links | `POST /api/v1/billing/invoices/create`, `…/{id}/mark_as_paid`; `POST /api/v1/pa/payment_links/create` | Keep invoices in Airwallex instead of a mock ERP; send a pay-link for a short-pay balance | https://www.airwallex.com/docs/api/billing/invoices · https://www.airwallex.com/docs/api/payments/payment_links |

All of this runs on the plain sandbox. Kits 1–4-style setup needs no platform or connected-account enablement.

---

## 4. Open risks / what I'd verify next
1. **No published rubric.** Ask in Discord or email whether Founder's/Judges Choice criteria exist. Until then, design to the guide's "Build around a financial decision" text above.
2. **Sandbox fidelity:** Confirm that simulated `payer_name`/`reference` come back on `GET /deposits` and `/global_accounts/{id}/transactions`. Confirm `deposit.*` webhooks fire for *simulated* GA deposits (the docs say `ga.new` applies only to API versions ≤2025-02-14). Check whether `simulation/deposits/{id}/reverse` works on bank-transfer deposits or only direct debit; the docs label reverse/settle/reject as "Direct Debit."
3. **Can a simulated deposit carry a fee or short amount?** If not, model the SWIFT lifting fee in our invoice data instead and say so on screen.
4. **Refund-to-origin:** Check whether the deposit's `payer.bank_account` is populated well enough in sandbox to build a valid beneficiary. The guide warns that invented routing codes fail with code `010`.
5. **Billing/Invoices API availability in sandbox.** Fall back to a local invoice table if it isn't enabled.
6. **Partner prizes:** Visa and Metal awards need their tooling. This idea doesn't naturally use either, so we're aiming at the two open categories.
7. **Inconsistencies to clarify:**
   - The landing page says "Over 48 hours" but also "3 WEEKS."
   - The HackerEarth generic FAQ says to submit a tar/zip and that "all code needs to be in public domain (open source)." The landing page says to submit a repo link.
   - Plan for a public repo.
