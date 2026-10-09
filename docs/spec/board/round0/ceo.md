# Round 0: CEO seat memo
*Lens: market pull, adoptability, and the story judges remember. Written Oct 8, 2026 (IST). Brand-new greenfield idea.*

## What the hackathon page actually says

**No scored rubric is published.** Neither airwallex.hackerearth.com nor the HackerEarth challenge page lists judging criteria or weights. The HackerEarth page has these tabs: Overview, Tracks, Key Dates, Prizes & Credits, Product Partners, Questions, Teams, Submissions, and Discussion. None of them is a judging tab. What *is* written:

- **Prizes:**
  - Founder's Choice $30,000: "Open category. No specific requirements."
  - Judges Choice $20,000: "Open category. No specific requirements."
  - Visa Award $15,000: "Requires use of Visa and Airwallex tooling."
  - Metal Award $15,000: "Requires use of Metal and Airwallex tooling."
- **Judges:** "a demo day in front of judges from fintech and venture."
- **What to submit:** "A working demo, a short video walkthrough under five minutes, and a link to your repository with setup instructions." The HackerEarth FAQ adds that "the submission should be functional so that it can be reviewed by the judges" and "all code needs to be in public domain (open source) so that it can be evaluated by the judges."
- **De facto rubric** (Builder Guide, "Build around a financial decision"):
  - "Choose a finance task that someone repeats and identify the decision inside it. The agent should choose differently when a balance, deadline, piece of evidence, or risk changes. Let the agent move money or update financial state, and state which actions require a person's approval."
  - "In the demo, show the user's goal, the agent's initial plan, the new information, the revised decision, and the resulting balance, payment, or status."
  - "Keep amounts, limits, reserves, validation, duplicate protection, and state transitions in code. Use the model to read unstructured text, compare evidence, propose a plan, and explain an exception."
  - "bind each approval to the amount, currency, counterparty, purchase terms, and evidence shown to the approver."
  - "Finish the demo with a financial action or an escalation to a person."
  - **Explicit hint:** "Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them. Good territory if you want a problem few other builders will take on."

**Key dates (HackerEarth phases, converted to IST):**
- Applications close Oct 23, 23:59 IST.
- Accepted teams are notified and the build starts Oct 25, 10:00 IST.
- Submissions are due Nov 13, 23:59 IST.
- Finalists are named Nov 15.
- Demo Day is Nov 19 in San Francisco (remote participation optional).
- Teams can have 1 to 4 people. Entry is free and open to anyone 18 or older worldwide.
- About 433 registrations so far.

## (1) Top 3 operator pains

| # | Who feels it | The pain | Number | Source |
|---|---|---|---|---|
| 1 | SMB/mid-market AR clerks and controllers | Matching incoming money to invoices is the biggest AR headache, and almost nobody below the enterprise level has automated it. | **44%** of US businesses rank data reconciliation as their most pressing AR concern, about twice the share of any other issue. Only **9%** of mid-market firms have automated reconciliation (24% of large firms). | PYMNTS × Mastercard, *Accelerating the Time to Realized Revenue* (2021) [S1] |
| 2 | Cross-border sellers and exporters | International receipts land **short or unpredictably**: intermediary banks deduct fees, so the invoice doesn't close cleanly, and each exception eats staff hours. | **~55%** of SMEs reported landed amounts that did not cover the full invoice. Typical deductions are **$25–$50**. A problematic payment takes **~3.5 hours** of internal handling vs ~2 hours for a typical one. *Caveat: directional, n=41 SME interviews in Mexico, Brazil, and Colombia.* | FXC Intelligence × Mastercard, *Principality at Risk* (Jun 25, 2026) [S2] |
| 3 | Small-business owners and finance leads | Unpaid and late invoices strain cash. Chasing the remainder is manual work. | **56%** of US small businesses are owed money on unpaid invoices, **$17,500** on average. **47%** have invoices more than 30 days overdue. (UK: 62% are owed money, £21.4K on average.) | Intuit QuickBooks 2025 Small Business Late Payments Report (Jan 2025, n=2,487) [S3] |

Supporting evidence: 18% of accountants make financial errors at least daily, and Gartner ties this to capacity constraints [S4].

## (2) The one idea I'd back: **Closer**

**One-liner:** Closer is an agent that watches every deposit landing in your Airwallex Global Accounts and works out which invoice it pays. It then acts to close the gap: it writes off fee short-pays within policy, sends a payment link for real shortfalls, reclassifies withheld amounts, and holds refunds of overpayments for a person's approval.

**Buyer vs user:**
- **Buyer:** the founder, controller, or fractional CFO at a 10–200-person business that bills clients across borders. Examples are agencies, SaaS companies, exporters, and studios already receiving through Global Accounts.
- **User:** the AR or bookkeeping operator.
- **Distribution wedge:** outsourced bookkeeping firms that run month-end for dozens of such clients.
- **Natural home:** a feature of Airwallex itself, since the deposit data is already there.

**Why now:**
1. Airwallex exposes deposit-level payer name and reference (`GET /deposits`, `/balances/history`). The sandbox can simulate realistic messy deposits (`simulation/deposit/create` takes `payer_name`, `reference`, `payer_country`, and `status`).
2. LLMs can finally read the unstructured remittance that rules engines choke on: emails, PDFs, and "INV 1042+1043" style references.
3. Airwallex explicitly flagged reconciliation as un-kitted territory, so we likely face little competition in a field of 400+ registrations.

**Airwallex APIs:**
- **Inbound:** Global Accounts (`/global_accounts`), Deposits (`GET /deposits`), Balances (`/balances/current`, `/balances/history`), sandbox `simulation/deposit/create`.
- **Collecting shortfalls:** Payment Links (`/pa/payment_links/create`, `/{id}/deactivate`), optionally Billing invoices (`/billing/invoices/create`).
- **Refunds:** `beneficiaries/create` and `transfers/create`, held behind approval.
- **FX (optional):** quotes and conversions to sweep matched foreign-currency cash above an operating buffer.
- **Event-driven:** webhooks for deposit events.

**Criterion-by-criterion (against the text above):**
- **"A finance task that someone repeats":** Cash application happens every day and at every month-end. Pain 1 shows it is the top AR concern and almost never automated in the mid-market.
- **"Choose differently when a balance, deadline, piece of evidence, or risk changes":** The same shortfall gets a different treatment depending on the evidence:
  - $37.85 that fits a SWIFT-deduction pattern within tolerance is written off.
  - €900 with no explanation gets a payment link.
  - €900 backed by a withholding-tax certificate is reclassified and the link is deactivated.
- **"Move money or update financial state" plus approval:**
  - The agent marks invoices paid or partial and posts fee write-offs on its own.
  - It sends a payment link on its own (it collects money and never moves money out).
  - A **refund transfer** always waits for a person's approval. The approval is bound to the amount, currency, beneficiary, and the duplicate-payment evidence.
- **"Amounts… validation, duplicate protection… in code; model reads unstructured text":**
  - Code handles the tolerance math, split allocation, idempotent `request_id`s, and the invoice state machine.
  - The model reads remittance emails and PDFs, proposes matches, and explains exceptions.
- **"Show goal → plan → new information → revised decision → resulting status":** The withholding-tax reply is the built-in "new information" beat (see the demo below).
- **Founder's Choice and Judges Choice ("fintech and venture"):**
  - Clear buyer and repeat usage: every deposit, every month.
  - Obvious expansion into AR collections and cash placement.
  - It strengthens Airwallex's own receiving product, so the hosts are likely to see it as a feature they would ship.
- **Visa and Metal awards:** Not targeted. Neither fits naturally, and bolting them on would dilute the story.

**The story judges remember (demo):**
- It's month-end at a 15-person studio. $9,962.15 lands from "MUELLER GMBH" with reference "INV 1042 1043". Closer splits it across both invoices, recognizes the $37.85 gap as an intermediary-bank deduction within the $50 policy, and closes both.
- Next, €4,100 arrives with no reference. Closer reads the client's remittance email, matches it to a €5,000 invoice, and sends a €900 payment link.
- The client then replies with a withholding-tax certificate. Closer **changes its mind**: it deactivates the link, books €900 as a tax receivable, and hands the controller one approval card for a duplicate-payment refund.
- **Closing line:** "Every dollar that landed today is explained, and a human touched exactly one."

**Biggest risk and mitigations:**
- **Risk:** Judges see "a matching script" rather than an agent, because reconciliation sounds boring.
- **Mitigations:**
  - Every match ends in a visible money or state action: a write-off, a payment link, a deactivated link, or a refund that needs approval.
  - Script one evidence flip that reverses a live decision.
  - Show a running "unexplained cash: $X → $0" counter.
- **Second-order risks:**
  - Sandbox Payment Links or Billing may need enablement, and deposit payer fields vary by rail. Mitigation: smoke-test both on day 1 and put all simulation calls behind one interface, as the guide advises.
  - Enterprise incumbents (HighRadius, Billtrust) already do cash application. Mitigation: position Closer as SMB-native and Airwallex-embedded. The 9% mid-market automation figure is the gap we fill.

## Sources
- [S1] PYMNTS: "44% of US Businesses Consider Data Reconciliation as the Most Pressing AR Concern" (Nov 13, 2021), https://www.pymnts.com/news/b2b-payments/2021/44-pct-of-us-businesses-consider-data-reconciliation-most-pressing-ar-concern/
- [S2] FXC Intelligence × Mastercard Move: "Principality at Risk: How Friction and Uncertainty Erode SME Cross-Border Relationships" (Jun 25, 2026), https://mastercardcontentexchange.com/news/media/xl2l42gr/fxc_mc_whitepaper-en-final-25_06.pdf
- [S3] Intuit QuickBooks 2025 Small Business Late Payments Report, https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2025/ (UK edition: https://quickbooks.intuit.com/uk/blog/small-business-late-payments-report-2025/)
- [S4] Gartner press release (Feb 21, 2024), https://www.gartner.com/en/newsroom/press-releases/2024-02-21-gartner-survey-shows-that-a-third-of-accountants-make-several-error-per-weeo-due-to-capacity-constraints
- Hackathon page: https://airwallex.hackerearth.com/; HackerEarth challenge page: https://www.hackerearth.com/challenges/hackathon/agentic-banking-hackathon/
- Builder Guide: https://airwallexdev.com/guide; Developer lab: https://airwallexdev.com/
- Airwallex Docs MCP (https://mcp.sandbox.airwallex.com/docs), queried for the Deposits, Balance History, Payment Links, Billing Invoices, and deposit-simulation references.
