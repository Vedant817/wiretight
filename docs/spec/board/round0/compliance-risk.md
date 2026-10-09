# Compliance & Risk — Round 0

_Seat: Compliance & Risk · Written Thu 8 Oct 2026, 7:15 PM IST · All URLs below were fetched or searched on that date._

## Judging criteria (as written)

**Read this first: the official pages do not publish judging criteria.** I checked the landing page ([airwallex.hackerearth.com](https://airwallex.hackerearth.com/)), including a raw-HTML grep for "judg", "criteria", "scor", and "evaluat". I also checked the HackerEarth challenge page ([hackerearth.com/.../agentic-banking-hackathon](https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/)) and the builder guide ([airwallexdev.com/guide](https://airwallexdev.com/guide)). None of them has a rubric, scoring weights, or a list of criteria. The landing page mentions judges only once: teams get "a demo day in front of judges from fintech and venture." So I can't quote any criteria word for word. The closest official statements are below, quoted exactly. After them is one clearly labelled proxy.

**A. What the organisers say a build must show.** This comes from the "Build around a financial decision" section of [airwallexdev.com/guide](https://airwallexdev.com/guide):

> "Choose a finance task that someone repeats and identify the decision inside it. The agent should choose differently when a balance, deadline, piece of evidence, or risk changes. Let the agent move money or update financial state, and state which actions require a person's approval."

> "In the demo, show the user's goal, the agent's initial plan, the new information, the revised decision, and the resulting balance, payment, or status. Keep amounts, limits, reserves, validation, duplicate protection, and state transitions in code. Use the model to read unstructured text, compare evidence, propose a plan, and explain an exception. Give the model typed tools rather than unrestricted credentials, and bind each approval to the amount, currency, counterparty, purchase terms, and evidence shown to the approver."

> "Put sandbox-only simulation calls behind one interface so you can replace them without rewriting the decision logic. Finish the demo with a financial action or an escalation to a person. If the agent should make the same choice every time, write the rule in code instead of asking a model to narrate it."

**B. What must be submitted.** From the landing-page FAQ:

> "A working demo, a short video walkthrough under five minutes, and a link to your repository with setup instructions."

**C. What each prize requires.** From the landing page:

> Founder's Choice $30,000 — "Open category. No specific requirements."
> Judges Choice $20,000 — "Open category. No specific requirements."
> Visa Award $15,000 — "Requires use of Visa and Airwallex tooling"
> Metal Award $15,000 — "Requires use of Metal and Airwallex tooling"

**D. Proxy only: these are NOT this hackathon's published criteria.** Sam Waldo, Airwallex's Head of Startups, Asia, judged a different event: the "Agents, Everywhere — OpenAI Agents Hackathon" in Singapore on 12 Sep 2026. AI Tinkerers Singapore posted the questions he would ask ([LinkedIn post](https://www.linkedin.com/feed/update/urn:li:activity:7500499794403049472), verified via curl):

> "🔍 Does this solve a genuine problem for founders or operators?
> 🌏 Can it work across markets, currencies and business environments?
> 📈 Is there a credible path from prototype to adoption?
> 🧱 Has the team built the operational foundation—not only the interface?
> 🛡️ Does the system balance autonomous execution with appropriate control?"

These match guide text A closely, so I score the idea against A plus D. I label D as a proxy everywhere I use it.

**Deadlines and facts.** Landing-page dates have no time of day. HackerEarth phase times are shown in UTC and converted to IST here.

| Milestone | Landing page | HackerEarth phase (UTC → IST) |
|---|---|---|
| Applications open | Oct 5 (SF Tech Week) | Oct 5 15:30 UTC → **Oct 5, 9:00 PM IST** |
| Applications / "Registration & Idea Phase" close | Oct 23 | Oct 23 18:29 UTC → **Oct 23, 11:59 PM IST** |
| Teams notified, build starts | Oct 25 | Oct 25 04:30 UTC → **Oct 25, 10:00 AM IST** |
| **Project submissions due** | **Nov 13** | Nov 13 18:29 UTC → **Nov 13, 11:59 PM IST** |
| Finalists selected | Nov 15 | — |
| Demo Day, San Francisco (remote optional) | Nov 19 | — |

- **Eligibility:** age 18+, anywhere in the world. Solo entries or teams of up to 4 (HackerEarth: "Team size: 1 - 4"). Entry is free. Teams keep full IP; submitting only lets the organisers showcase the work.
- **Product:** "ship agents that run real financial workflows" on Airwallex APIs: "global accounts, FX, payouts, cards, and transactional data". Sandbox access is provided. There are 10 starter kits plus 2 marked "coming soon".
- **Inconsistencies to flag:**
  - The landing page says "Over 48 hours, teams build…" but also "3 WEEKS To design, build, ship". The dates support three weeks.
  - HackerEarth's generic FAQ says the demo video is "not mandatory" and that code must be "in public domain (open source)" and uploaded as tar/zip. The Airwallex landing page asks for a video under 5 minutes plus a repository link.
  - Plan to meet the stricter version: public repo, tar/zip upload, and a video under 5 minutes.
- HackerEarth showed **433 registrations** when I fetched it on 8 Oct.

### What the guide says an agent can use (airwallexdev.com/guide, plus one level of links)

These come only from the guide text. Prefix every path with `https://api.sandbox.airwallex.com/api/v1`.

- **Auth:** `POST /authentication/login` with `x-client-id` and `x-api-key` returns a 30-minute bearer token.
- **Balances and Global Accounts:** `GET /balances/current`, `GET /global_accounts`, `POST /global_accounts/create`.
- **Funding (sandbox only):** `POST /simulation/deposit/create`. Accounts start empty and there is no top-up button.
- **FX:**
  - `GET /fx/rates/current` gives an indicative rate with no `quote_id`.
  - `POST /fx/quotes/create` gives a quote that can be booked only once.
  - `POST /fx/conversions/create` settles immediately. There is no MCP tool for it, so use REST.
- **Payouts:**
  - Beneficiaries: `POST /beneficiaries/schema`, `POST /beneficiaries/validate`, `POST /beneficiaries/create`.
  - Transfers: `POST /transfers/create` (`LOCAL` or `SWIFT` only) and `GET /transfers`.
  - Transfer states (sandbox only): `POST /simulation/transfers/{id}/transition`.
- **Cards (Issuing):**
  - Create: cardholders/create, cards/create.
  - Read and change: `GET /issuing/cards/{id}/limits`, cards/{id}/update (freeze, unfreeze, close), `GET /issuing/transactions`.
  - Sandbox simulators: auth, capture, reverse, refund.
- **Disputes (Payments Acceptance):**
  - Payment intents: create and confirm.
  - Disputes: `GET /pa/payment_disputes`, accept, challenge.
  - Sandbox simulators: create, escalate, resolve.
  - Evidence: `POST /files/upload` on `files.sandbox.airwallex.com`, JPG or PDF only.
- **Platform (needs enablement by email to devhelp@airwallex.com):**
  - Connected accounts: create, update, submit, then simulated activation.
  - Use `x-on-behalf-of` for customer-scoped calls.
  - Money movement: `POST /connected_account_transfers/create` and `POST /charges/create`.
  - Reports: `POST /platform_reports/create`.
- **MCP:**
  - Docs server (no login): `https://mcp.sandbox.airwallex.com/docs`.
  - Developer server (sandbox login): `https://mcp.sandbox.airwallex.com/developer`.
  - MCP `create_beneficiary` supports `dry_run: true`. MCP cannot send `x-on-behalf-of`.
- **Webhooks:** "Verify the HMAC-SHA256 signature against the raw bytes… dedupe on event id because delivery is at-least-once, and return 200 fast."
- **Sandbox constraints the guide states:**
  - Amounts are in major units, not cents.
  - Reusing a `request_id` within 7 days returns `duplicate_request_id`. A transfer `request_id` must be 10–50 characters.
  - SWIFT payouts carry a flat EUR 12.85 fee. LOCAL payouts are free.
  - A failed transfer ends `CANCELLED`, not `FAILED`, and `CANCELLED` doesn't mean a person cancelled it. `SENT` is not final.
  - Bank details are validated when the beneficiary is created, not when it's paid.
  - Card per-transaction limits are inclusive and not cumulative.
  - Three different insufficient-funds codes exist: `balance_insufficient`, `insufficient_fund`, `insufficient_funds`.
  - Rate limits: 20 req/s globally, 10 per endpoint, 10 concurrent.
  - Sandbox behaviour "may change… without warning".
- **Limited access:**
  - Kit 9 (Airi CLI) is allowlisted and places real orders at real merchants with a pre-funded card.
  - Kit 10's Merchant Onboarding API is a draft ("proposed, not deployed").

## Top 3 operator pains

### 1. Vendor-impersonation and payee-change fraud (BEC) hits outbound wires and payouts

- **Who hurts:** AP and treasury teams, and founders who pay suppliers by wire or local transfer.
- **How:** A fraudster spoofs a real vendor, or hijacks a vendor mailbox, and sends "new bank details". The next genuine invoice then goes to the fraudster's account. Once the money is sent it is often unrecoverable. The payer usually still owes the real vendor too, so it effectively pays twice.
- **Numbers:** The 2025 AFP Payments Fraud and Control Survey covered 521 corporate practitioners and 2024 data. It found:
  - **79%** of organisations were hit by attempted or actual payments fraud.
  - BEC was the No. 1 avenue, at **63%**.
  - **Vendor imposter fraud reached 45%**, up 11 percentage points.
  - **Wire transfers were the payment method most targeted by BEC, at 63%** (up from 39%).
  - Only **22%** recovered 75% or more of lost funds, down from 41% the year before.
- **Source:** [AFP press release, 15 Apr 2025](https://www.afponline.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024).
- **Corroborating dollar figure (not the primary citation):** the FBI IC3 2024 Internet Crime Report records **$2,770,151,146** in BEC losses across 21,442 complaints ([IC3 2024 report PDF](https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf), verified in the PDF text).

### 2. Duplicate and erroneous disbursements, especially on retries and replacement payments

- **Who hurts:** AP and payment-ops teams. The risk peaks when a payment looks stuck, a supplier chases, and someone sends a replacement before the original's fate is known. This is exactly the scenario in the guide's Kit 3.
- **How:** Cash leaves that shouldn't. Recovering it means vendor credit notes, clawbacks, or recovery audits. The reconciliation work lands on the same team.
- **Number:** APQC Open Standards Benchmarking reports a **median of 1.5%** of total annual disbursements processed as duplicate or erroneous payments (sample: 1,686 companies) ([APQC measure 105905](https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number)).
- **Caveats:**
  - The public APQC page doesn't show the data year or the 25th and 75th percentiles; those are member-only.
  - A secondary source (Corpay's blog) attributes the figure to APQC's 2024 data and cites 0.8% for top performers and 2.0% for bottom performers. I could not verify those on APQC's public page.
  - The figure counts disbursements, not dollars. I found no verified dollar-loss total.

### 3. Sanctions and financial-crime screening that doesn't keep pace with cross-border payment growth

- **Who hurts:** Fintechs, platforms, and banks whose cross-border payment volume grows faster than their screening controls. The businesses relying on them hurt too, through frozen accounts, offboarding, and onboarding bans.
- **How:** Screening misses names. Cross-border payments go out unscreened. Regulators then impose fines and growth restrictions.
- **Number:** The FCA fined Starling Bank **£28,959,426**; it would have been £40,959,426 without the settlement discount.
  - Its automated system had been screening customers "against a fraction of the names on the Consolidated List" since 2017.
  - It "was not screening all of its cross border/international payments against the Consolidated List, despite such payments presenting a much higher financial sanctions risk than domestic payments."
  - Inbound cross-border payments grew from 385 in 2017 to over 1 million in 2023.
  - Its look-back reviewed **3,988,143 payments**, which generated **795,712 alerts**.
  - Source: [FCA Final Notice: Starling Bank Limited, 2024](https://www.fca.org.uk/publication/final-notices/starling-bank-limited-2024.pdf), with figures verified in the PDF text.
- **Caveat:** Starling is a bank, not an SME operator. I use it because it is the cleanest regulator-documented number on cross-border payment-screening failure. A smaller-firm example is OFSI's £465,000 penalty (Mar 2025) on HSF Moscow over outbound-payment screening. I only saw that one through a law-firm summary ([Akin](https://www.akingump.com/en/insights/alerts/ofsi-imposes-monetary-penalty-against-former-moscow-office-of-international-law-firm-for-sanctions-breaches)), not the OFSI notice itself.

## The idea I'd back

### PayeeLock: the payee-change and duplicate-payment tripwire agent

**Pitch.** PayeeLock is an agent that sits between "an invoice or payment instruction arrives" and "money leaves via Airwallex `transfers/create`".

- It treats every new or changed beneficiary, and every "it didn't arrive, please pay again" request, as untrusted until proven otherwise.
- The LLM only reads the unstructured inputs: the vendor email, the PDF invoice, and the supplier's "we changed banks" letter. It extracts claims such as payee name, bank country, IBAN or routing number, urgency language, and reply-to domain, and compares them with vendor history.
- Deterministic policy code computes a risk tier. Signals include:
  - beneficiary age
  - a change of bank country versus the vendor's registered country
  - account-holder name mismatch
  - a lookalike sender domain
  - an amount outside the vendor's normal band
  - an invoice number already paid or already in flight
- Code then decides one of four outcomes:
  - **Pay** to the existing verified beneficiary.
  - **Hold** and request out-of-band verification, bound to amount, currency, counterparty, invoice ID, and evidence.
  - **Pay a capped partial amount** to the verified old account if the supplier deadline is critical.
  - **Escalate.**
- When new evidence arrives, the agent revises the decision and executes or escalates. That evidence can be a callback confirmation, a second email that contradicts the first, or a webhook showing the original transfer moved to `SENT`. Every step goes into a hash-chained audit log that a controller can replay.

**Which pain it kills.** Primarily **Pain 1** (vendor-impersonation BEC, 45% incidence). Its duplicate lock also directly attacks **Pain 2**: no second payout for the same invoice while an original is in flight or not provably `CANCELLED`. Its hook for a pre-payout screening provider gives a seam for **Pain 3** later. That hook is a stub interface in the hackathon, and I won't claim real screening.

**Airwallex surface used (all from the guide):**
- `POST /beneficiaries/schema`, `/beneficiaries/validate`, and `/beneficiaries/create` for corridor-correct payee records, created only after verification.
- `POST /transfers/create`, with `request_id` derived from the invoice ID plus beneficiary ID plus version.
- `GET /transfers` to find an in-flight original before any replacement.
- `POST /simulation/transfers/{id}/transition` to stage `SENT` then `FAILED`, with a bank-return failure type.
- `GET /balances/current`.
- Optionally `POST /fx/quotes/create` and `POST /fx/conversions/create` for a cross-currency supplier, with the SWIFT fee included.
- Webhooks for transfer status, with HMAC verification and dedupe on event ID.
- Optional extension for the card side: freeze a virtual card that pays the same vendor (`/issuing/cards/{id}/update`) when the vendor is flagged.

**Demo script.** This follows the guide's goal → plan → new info → revised decision → result format.

1. Goal: pay three supplier invoices this week across USD and EUR.
2. Initial plan: pay all three to their existing verified beneficiaries.
3. New info: an email from a lookalike domain asks to route invoice #2 to a new IBAN in a different country, and is marked "urgent".
4. Revised decision: hold invoice #2, keep the old beneficiary, and require a human callback approval bound to €X, IBAN Y, and invoice #2. Invoices #1 and #3 proceed.
5. Second twist: the supplier says "never arrived" on #3. PayeeLock finds the original in `SENT`, which is not final, and refuses a replacement. After the simulator moves it to `FAILED` with a bank-return type, PayeeLock issues exactly one replacement with a new `request_id` and records the fate of both transfers.
6. Result: the ending balance is shown alongside the audit trail.

**Why it wins against each criterion quoted above.**

- **A, "decision inside a repeated finance task… choose differently when… evidence, or risk changes"**
  - Paying supplier invoices is the most repeated finance task there is.
  - The decision flips on evidence: a new email, a callback, or a transfer-state change.
- **A, "Let the agent move money… and state which actions require a person's approval"**
  - It moves money: transfers, and optionally FX.
  - Approval rules are explicit and in code: any new or changed beneficiary above $0 needs human approval, and so does any replacement payment.
- **A, "show the user's goal, the agent's initial plan, the new information, the revised decision, and the resulting balance, payment, or status"**
  - The demo script above follows those five beats one for one.
- **A, "Keep amounts, limits, reserves, validation, duplicate protection, and state transitions in code"**
  - Risk scoring, limits, duplicate locks, and the transfer state machine are code.
  - The model only extracts and explains.
- **A, "Use the model to read unstructured text, compare evidence… explain an exception"**
  - BEC is an unstructured-text problem: spoofed emails and doctored PDFs.
  - That is the model's job here, and the model never holds credentials.
- **A, "bind each approval to the amount, currency, counterparty… and evidence"**
  - The approval token is a hash of those fields plus evidence IDs.
  - Any change invalidates it.
- **A, "Finish the demo with a financial action or an escalation to a person"**
  - The demo ends with both: one held-and-escalated payment and one correctly replaced payment.
- **B, submission (working demo, under-5-minute video, repo)**
  - The scope is two Airwallex flows (beneficiaries and transfers) with no platform enablement needed.
  - It runs on a fresh sandbox the same day. The guide says kits 1–4 need "no extra enablement", and this builds on that tier.
  - That lowers the risk of an incomplete demo.
- **C, Founder's or Judges Choice (open category)**
  - It is eligible for both with no partner dependency.
  - The Visa and Metal awards need partner tooling, which we can add later if the board wants.
- **D (proxy), "genuine problem for founders or operators?"**
  - Yes: 63% of organisations faced BEC and 45% faced vendor imposter fraud (AFP 2025).
- **D (proxy), "work across markets, currencies and business environments?"**
  - It is corridor-aware via the beneficiary schema (US LOCAL, GB LOCAL, EUR SWIFT).
  - A bank-country change is itself a risk signal.
  - It handles FX and SWIFT fees.
- **D (proxy), "credible path from prototype to adoption?"**
  - It drops in as a pre-payout control for any business already paying suppliers on Airwallex.
  - It needs no new rails and can ship in shadow mode (score only) before it enforces.
- **D (proxy), "operational foundation—not only the interface?"**
  - That foundation is idempotency keys, a duplicate lock, a transfer state machine that respects "CANCELLED ≠ human cancel" and "SENT ≠ final", webhook HMAC plus dedupe, and a replayable audit log.
- **D (proxy), "balance autonomous execution with appropriate control?"**
  - Clean, known payees go fully autonomous. Anything touching payee identity or a repeat payment needs a human.
  - That balance is the product itself.

**Differentiation risk.** Kit 3 (Payment Ops Incident Commander) overlaps with PayeeLock's duplicate-payment beat, so other teams will build that part. PayeeLock's lead feature, the payee-change and BEC tripwire, isn't covered by any kit. The guide also invites "your own idea" through the decision criteria.

## Controlled-autonomy guardrails

### 1. Sandbox-only execution
All calls go to `api.sandbox.airwallex.com` and `files.sandbox.airwallex.com`, and the production host is blocked by an egress allowlist in code. All `/simulation/*` calls sit behind one interface, as the guide asks, so decision logic never depends on simulators. Use synthetic names and accounts only; the guide requires synthetic data for kits 1–8.

### 2. Per-transaction and rolling daily limits
Hard caps per payout, per beneficiary per day, and in total per day live in policy code, never in the prompt. A breach blocks the payout and routes it to approval rather than failing silently. The guide notes card `PER_TRANSACTION` limits are not cumulative, so pair them with `ALL_TIME` or `MONTHLY` limits on cards and with a ledger-level daily sum on transfers.

### 3. Human approval thresholds, with approvals bound to terms
Approval is required for:
- any new or changed beneficiary
- any replacement or re-send
- any amount above threshold
- any FX conversion above the confidence-adjusted limit

Each approval is a signed record of amount, currency, counterparty, beneficiary ID, invoice ID, and evidence hashes. Any drift voids it, following the guide's "bind each approval to the amount, currency, counterparty, purchase terms, and evidence."

### 4. Beneficiary allowlist and cooling-off
The agent may pay autonomously only to beneficiaries on a verified allowlist. A new or changed beneficiary enters a quarantine state until an out-of-band verification is recorded. Validate with `POST /beneficiaries/validate`, or `dry_run` on MCP, before `create`. Validation proves the details are well-formed, not that they belong to the vendor.

### 5. Idempotency and duplicate locks
Derive each `request_id` deterministically per logical operation (invoice plus beneficiary plus version). Reuse it only to retry the same operation and never for a new one, since Airwallex rejects reuse within 7 days. Before any replacement, query `GET /transfers` for an in-flight original. Treat every non-success or timeout response as ambiguous until checked, as the guide instructs for kits 5 and 9.

### 6. State-machine finality
Model transfer and card states as separate state machines in code. `SENT` and `PROCESSING` are in flight. A failed transfer ends `CANCELLED` (read `failure_type`); a declined card ends `FAILED`. Never close an incident on the replacement's `PAID` alone; record the original's fate too.

### 7. Immutable audit trail
Every model input hash, extracted claim, policy decision, approval, API request ID, and response gets appended to a hash-chained log. That lets a reviewer replay why money moved or didn't. This is what a controller, auditor, or regulator asks for first, and it underpins the "operational foundation" judges will probe.

### 8. Kill switch
A single flag halts all money-moving tools immediately, and the agent can freeze its own virtual cards via `POST /issuing/cards/{id}/update`, which the guide suggests "to show an agent revoking its own authority mid-run". Trip it automatically on anomaly bursts, such as several holds in a row or repeated 4xx responses on transfers. Trip it manually from the approval UI.

### 9. Segregation of duties
The model proposes; policy code decides; a human approves. Only a separate executor holding the credential can call `transfers/create`. The person or agent that adds or changes a beneficiary must not be the one that approves paying it. That's classic maker-checker, and it is the control BEC defeats when it is missing.

### 10. Least privilege: typed tools, no raw credentials
The model gets typed tools (e.g. `propose_payout(invoice_id)`), never the API key or bearer token, matching the guide's "Give the model typed tools rather than unrestricted credentials." Credentials stay in environment variables and out of the repo; the guide says "do not commit either credential". Scope API keys to the minimum needed.

### 11. Data minimisation
Send the model only the fields it needs to extract or compare. Mask account numbers to their last 4 digits in prompts and logs. Keep card data out of model context and logs entirely, as the guide requires for kits 9 and 10, and retain demo data only as long as the demo needs.

### 12. Prompt-injection resistance on untrusted inputs
Emails, PDFs, and webhook payloads are data, not instructions. A "please pay to this new account" instruction can only raise risk, never authorise payment. Model output is schema-validated, and any free-text "instruction" in it is ignored by the executor.

### 13. Tenant and fund segregation (if using platform kits)
Never sum balances across connected accounts, and never fund one customer's obligation from another's wallet. The guide warns that Airwallex will execute such a transfer if authorised, so the policy must block it. Send `x-on-behalf-of` on every customer-scoped call, and assert the landing account after FX.

### 14. Webhook integrity
Verify HMAC-SHA256 over the raw bytes, dedupe on event ID because delivery is at-least-once, and return 200 fast, as the guide states. Never let an unverified webhook advance a payment state.

### 15. Money-math correctness
Amounts are in major units: assert units at the tool boundary, because the guide warns that `5000` means $5,000. Include the per-payout SWIFT fee in FX amounts, and treat FX quotes as single-use. Preserve a reserve floor in code before any autonomous payout.

### 16. Rate limiting and backoff
Respect the sandbox limits of 20 req/s globally, 10 per endpoint, and 10 concurrent. On a 429, back off with jitter. Never retry a money-moving call without the ambiguity check from guardrail 5.

### 17. Screening hook: honest scope
The guide documents no sanctions-screening API, so the hackathon build has a stubbed `screen(counterparty)` interface that can block or hold. The README must state plainly that real screening is not performed. Starling shows the cost of thinking you screen cross-border payments when you don't.

## Sources

- https://airwallex.hackerearth.com/ (landing page: tracks, dates, prizes, FAQ; fetched + raw HTML grep)
- https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/ (phase times in UTC, team size, registration count, generic FAQ; curl)
- https://airwallexdev.com/guide (builder guide: endpoints, sandbox constraints, decision criteria)
- https://airwallexdev.com/ and https://airwallexdev.com/builds (index pages; /builds is thin, with titles only)
- https://devgrantsdaily.com/items/2026-10-06-airwallex-agentic-banking-hackathon/ (third-party mirror of dates and prizes; no criteria)
- https://www.linkedin.com/feed/update/urn:li:activity:7500499794403049472 (AI Tinkerers Singapore; Airwallex judge questions for a different hackathon; proxy only)
- https://www.afponline.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024 (Pain 1)
- https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf (Pain 1 corroboration)
- https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number (Pain 2)
- https://www.corpay.com/resources/blog/duplicate-payment (Pain 2 secondary; seen via search snippet only, not used as the citation)
- https://www.fca.org.uk/publication/final-notices/starling-bank-limited-2024.pdf (Pain 3)
- https://www.akingump.com/en/insights/alerts/ofsi-imposes-monetary-penalty-against-former-moscow-office-of-international-law-firm-for-sanctions-breaches (Pain 3 secondary; search snippet only)
