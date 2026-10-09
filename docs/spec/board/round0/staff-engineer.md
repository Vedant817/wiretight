# Round 0: Staff Engineer memo
**Seat:** AB Staff Engineer (architecture, feasibility) · **Written:** Thu 8 Oct 2026, ~7:30 PM IST
**Scope:** read-only research. Nothing registered, submitted, or sent.

---

## TL;DR
- **Back:** **"PayRun Warden"** (working title). It runs a cross-border SMB's weekly supplier payment run. The agent plans which invoices to pay, convert, defer, or escalate against a reserve floor. It refuses to pay any supplier whose bank details just changed until a human verifies them out of band. It executes FX and payouts under duplicate-payment locks, handles a returned payment without paying twice, and finishes by reconciling every invoice to its transfer, FX conversion, and fee.
- **Why it wins:** it combines the two no-enablement kits (1 Treasury, 3 Payment Ops). It adds reconciliation, which the official guide calls territory "few other builders will take on". It also puts Airwallex's own governance thesis on screen: limits and approvals enforced in code, not prompts.
- **Feasibility:** **Yes, a solo developer can ship a credible demo in the roughly 20-day build window**, if scope is locked to one scripted payment run with 3 currencies and 3 exception paths. Every API it needs is sandbox-only and needs no platform access or allowlisting.
- **Key deadline:** submissions close **Fri 13 Nov 2026, 11:59 PM IST**.

---

## 0. Hackathon facts (verified)

| Item | Detail | Source |
|---|---|---|
| Name / host | Agentic Banking Hackathon, hosted by Airwallex on HackerEarth | [landing](https://airwallex.hackerearth.com/), [HE page](https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/) |
| Format | Online and global. Optional in-person Demo Day in SF, with remote participation allowed. Team size 1–4, so solo is allowed. Free. Age 18+ | landing FAQ |
| Scale | **433 registrations** on the HackerEarth page as of 8 Oct 2026 | HE page |
| Prizes | Founder's Choice **$30K** (open). Judges Choice **$20K** (open). Visa Award **$15K** (requires Visa and Airwallex tooling). Metal Award **$15K** (requires Metal and Airwallex tooling). Credits: Claude $10K, Base44 $16K, AWS TBD | landing |
| Partners | Visa (TAP, VIC), Claude, AWS (Bedrock AgentCore), Metal (L1 chain), Coinbase (CDP, stablecoins), tZERO ("T:0": AI accounting, MCP server, sandbox), Base44 | landing |
| Tracks | 10 starter kits plus 2 "coming soon". Kits 1–4 use the sandbox only. Kits 5–8 need connected accounts and platform access enabled by Airwallex. Kit 9 needs allowlisted Airi CLI. Kit 10 needs merchant-side access and uses a *draft* API | landing, [guide](https://airwallexdev.com/guide) |
| Required tech | Must build on Airwallex APIs. No mandated stack or LLM | landing, guide |
| Submission | "A working demo, a short video walkthrough under five minutes, and a link to your repository with setup instructions." HackerEarth's generic FAQ also says code must be open source for judging and that the upload is a tar or zip with run instructions | landing FAQ, HE page FAQ |
| IP | Team keeps IP. Airwallex may showcase the project | landing FAQ |

### Key dates, converted to IST (UTC+5:30)
The HackerEarth page publishes exact UTC times for the two phases. The other dates have no published time.

| Milestone | Published | **IST** |
|---|---|---|
| Applications open | Oct 5, 3:30 PM UTC | **Mon 5 Oct 2026, 9:00 PM IST** |
| **Applications close** | Oct 23, 6:29 PM UTC | **Fri 23 Oct 2026, 11:59 PM IST** |
| Accepted teams notified, build begins | Oct 25, 4:30 AM UTC | **Sun 25 Oct 2026, 10:00 AM IST** |
| **Project submissions due** | Nov 13, 6:29 PM UTC | **Fri 13 Nov 2026, 11:59 PM IST** |
| Finalists selected | Nov 15 (no time given) | Sun 15 Nov 2026 (time unknown) |
| Demo Day, San Francisco (remote optional) | Nov 19 (no time given) | Thu 19 Nov 2026. SF is on PST (UTC−8) by then, so SF daytime lands late night IST (10 AM PST = 11:30 PM IST) |

Build window: about **19.5 days**, from Sun 25 Oct 10:00 AM IST to Fri 13 Nov 11:59 PM IST.

### Judging criteria: what is and isn't published
**No scoring rubric is published** on the landing page, in its raw HTML, or on the HackerEarth challenge page. The landing page's sections run 01 About, 02 Tracks, 03 Timeline, 04 Prizes, 05 Partners, 06 FAQ, with no judging section. The only stated prize conditions are "open category" for Founder's and Judges Choice and the tooling requirements for Visa and Metal. In place of a rubric, I map the idea to the three strongest **official Airwallex signals** below. Each is labelled as a proxy, not a rubric.

- **C1–C5: Airwallex judge questions** (Sam Waldo, Head of Startups Asia, Airwallex) for a Sept 2026 Airwallex-partnered hackathon. This was a different event, so treat it as a strong signal of how Airwallex judges think:
  1. solves a genuine founder or operator problem;
  2. works across markets and currencies;
  3. credible path from prototype to adoption;
  4. operational foundation, not just interface;
  5. balances autonomous execution with control.
  ([LinkedIn post 1](https://www.linkedin.com/feed/update/urn:li:activity:7500499794403049472), [post 2](https://www.linkedin.com/posts/sam-waldo_judging-the-agents-everywhere-hackathon-activity-7500783609373462528-jCSr))
- **G: the official guide's "Build around a financial decision" demo spec** for this hackathon. The demo should show the user's goal, the agent's initial plan, new information, a revised decision, and the resulting balance, payment, or status. Amounts, limits, reserves, validation, duplicate protection, and state transitions belong in code. The model gets typed tools, not raw credentials. Each approval must be bound to amount, currency, counterparty, terms, and evidence. ([guide](https://airwallexdev.com/guide))
- **B: Airwallex blog "Agentic banking starts with governance"**, 7 Oct 2026. It argues: grant scoped authority, set limits and an approval chain, enforce through infrastructure, and log everything for audit. Its line: "A prompt is not a financial control." ([blog](https://www.airwallex.com/global/blog/agentic-banking-governance))

---

## 1. Top 3 real operator pains (SMB, startup, and cross-border finance and ops)

### Pain 1: Payees' bank details get hijacked, and outbound payments go to fraudsters
- **79%** of organizations were victims of attempted or actual payments fraud in 2024. **Business email compromise (BEC) was the #1 avenue at 63%.** **Vendor-imposter fraud hit 45%, up 11 percentage points.** **Third-party impersonation (63%)** is the most common BEC type. **Wires were the top BEC target at 63%, up from 39%.** Only **22%** of organizations recovered 75% or more of lost funds, down from 41%. Source: [AFP 2025 Payments Fraud & Control Survey press release](https://www.financialprofessionals.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024) (n=521 corporate practitioners, Jan 2025).
- **31%** of SMBs making cross-border payments raise fraud and security concerns ([Visa SMB research, page dated "05/01/2026"](https://corporate.visa.com/en/sites/visa-perspectives/trends-insights/as-smbs-go-global-payment-complexity-remains.html)).
- *Caveat:* AFP's sample skews toward mid-size and large US corporates, not only SMBs.

### Pain 2: Cross-border payments are reconciled by hand, and true FX and fee cost is opaque
- **38%** of SMB expenses are international. **1 in 3** SMBs struggle with manual reconciliation. **32%** cite high fees or opaque FX costs. **30%** lack visibility across systems. **29%** experience approval delays ([Visa SMB research](https://corporate.visa.com/en/sites/visa-perspectives/trends-insights/as-smbs-go-global-payment-complexity-remains.html); Visa-commissioned Basis Research survey of businesses with fewer than 250 employees).
- **72%** of GCC and MENA SMEs reconcile cross-border payments manually; only 28% have ERP-integrated reconciliation. **16%** can't say what they pay per transfer ([ARP Digital 2026 survey](https://www.arpdigital.io/en/resources/news-insights/gcc-sme-cross-border-payments-2026), 200+ SMEs, Feb 2026).
- Supporting figure from a different population (UK payments companies, n=250): **700+ hours a year** go to reconciliation data prep alone, and **cross-currency transactions are the #1 matching barrier (23%)** ([Kani Payments 2025 survey PDF](https://kanipayments.com/wp-content/uploads/2025/04/Reconciliation-and-Reporting-Survey-2025_Kani-Payments.pdf)).

### Pain 3: Payment exceptions (delays, returns, duplicates) burn cash and supplier trust
- **47%** of GCC SMEs cite settlement delays as their primary pain. **24%** cite failed or returned payments, and **22%** unexpected fees. Only **16%** get same-day settlement ([ARP Digital 2026](https://www.arpdigital.io/en/resources/news-insights/gcc-sme-cross-border-payments-2026)).
- The **median duplicate or erroneous disbursement rate is 1.5%** of all disbursements (APQC Open Standards Benchmarking, n=1,686 organizations, [APQC measure 105905](https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number)). Only the median is publicly visible; the quartiles are behind the member wall.
- *Caveat:* the ARP figures are regional (GCC and MENA). I found no equally recent *global* SMB figure for return rates.

**Not used (could not source to a primary):** the widely repeated "82% of small businesses fail because of cash flow" stat, and the "15+ hours/week on reconciliation" figure from a vendor blog. Both are excluded on purpose.

---

## 2. The idea I'd back: **PayRun Warden**
*An agentic weekly payables run for cross-border SMBs, built to stay safe when cash is short and BEC attempts are common.*

**User:** the founder, finance lead, or ops person at a 10–200 person company that pays suppliers and contractors in USD, GBP, and EUR (and more) from an Airwallex wallet.

**What the agent does in one run:**
1. **Ingest.** It reads this week's invoices and supplier emails (synthetic PDFs and text). The LLM extracts structured fields; code validates totals, currency, due date, and payee identity against the vendor master.
2. **Guard.** It runs a **bank-detail-change tripwire.** If any email or invoice carries new bank details, or a beneficiary record differs from the last paid one, that invoice is frozen. The agent drafts a verification task (a call-back to a known number, simulated in the demo) and never pays new details without a human's out-of-band confirmation plus a cooling-off period. This targets Pain 1.
3. **Plan.** A **deterministic planner in code** handles the cash decisions: it reads balances, takes FX quotes, adds SWIFT fees to the convert amount, and applies the reserve floor. It ranks invoices by operational criticality, late penalty, and early-pay discount, then decides pay, convert-then-pay, defer, or escalate. The LLM only *explains* the plan and drafts notes to suppliers.
4. **Approve.** Each approval is cryptographically bound to (amount, currency, beneficiary ID, FX quote ID, evidence hash). If anything changes, such as a re-quote or a different beneficiary, the approval is void and the agent re-asks. Small LOCAL payouts under a threshold run autonomously; SWIFT payouts, new payees, and anything near the reserve floor need a human.
5. **Execute.** It books the FX conversion, then the transfer, with an idempotency ledger (one `request_id` per intent) and a **duplicate lock per invoice**.
6. **Handle exceptions.** A webhook or poll reports a transfer that went SENT then FAILED (bank return). The agent decides wait, replace, or escalate. A replacement goes out under a new `request_id`, with the original's terminal state recorded first so the supplier is never paid twice. A late customer deposit lands mid-run, and the agent re-plans *only* the affected decisions. This targets Pain 3.
7. **Reconcile.** It matches every invoice to its transfer, conversion (`CONVERSION_SELL`/`CONVERSION_BUY`), and fee via Financial Transactions. It computes the true effective FX cost and fee per invoice, then exports a close-ready ledger CSV and an audit trail of every decision, approval, and API call. This targets Pain 2.

### Demo script (fits under 5 minutes; follows the guide's "goal → plan → new info → revised decision → result")
Goal: pay 5 invoices across USD, GBP, and EUR this week while keeping $X in reserve. Initial plan: pay 3, convert for 1, defer 1. **New info #1:** an email "from" the EUR supplier changes its IBAN, so the agent freezes that invoice and escalates for verification. **New info #2:** a simulated customer deposit lands, so the agent re-plans and pays the deferred invoice. **New info #3:** the GBP payout is returned, so the agent replaces it under a duplicate lock. **Result:** final balances, reserve still intact, and a reconciliation table with effective FX and fee cost per invoice.

### Mapping to the criteria
| Criterion (proxy, see §0) | How PayRun Warden scores |
|---|---|
| **C1 Genuine operator problem** | Three sourced pains: 63% BEC, 45% vendor-imposter fraud, 1 in 3 SMBs reconciling manually, 1.5% median duplicate or erroneous payments. A weekly payment run is something almost every company already does |
| **C2 Across markets and currencies** | Three corridors with different rails and fees (US LOCAL/ABA, GB LOCAL/sort code, DE SWIFT/IBAN with the EUR 12.85 fee), plus FX quotes and conversions. Reconciliation shows true cross-currency cost |
| **C3 Path to adoption** | Plugs into a workflow companies already run. Sandbox-to-production path via Airwallex AgentOS/CLI ([AgentOS docs](https://www.airwallex.com/docs/developer-tools/ai/agentos)). The CSV export maps to existing accounting tools. Visa reports 81% of SMBs are open to new cross-border solutions |
| **C4 Operational foundation, not UI** | Idempotency ledger, duplicate locks, transfer and card state machines, HMAC-verified, deduplicated webhooks, reserve-floor policy engine, reconciliation, full audit log. This is the part judges say most teams skip |
| **C5 Autonomy balanced with control** | Tiered autonomy: LOCAL payouts under a threshold run automatically; SWIFT, new-payee, and near-floor payouts need approval; approvals are bound to terms and void on change. Matches Airwallex's governance blog almost line for line (B) |
| **G Guide's demo spec** | Hits every beat: goal, plan, three new-info events, revised decisions, final balances and status. Money logic lives in code; the LLM gets typed tools only |
| **Prize fit** | Targets **Founder's Choice ($30K)** and **Judges Choice ($20K)**, both open category. Visa and Metal awards are out of scope; they need partner tooling that adds risk |
| **Differentiation** | Many teams will build kit 1 or 3 exactly as written. This merges both and adds the BEC guard and reconciliation, which the guide flags as under-claimed |

---

## 3. Feasibility read

### Airwallex sandbox APIs it needs
All of these appear in the official guide's kits 1 and 3, which need only a funded wallet: **no platform access, no allowlist**. Base URL: `https://api.sandbox.airwallex.com/api/v1`.

| Need | Endpoint(s) | Doc |
|---|---|---|
| Auth (30-min bearer token) | `POST /authentication/login` | [API access token](https://www.airwallex.com/docs/api/authentication/api_access_token) |
| Wallet and funding | `GET /global_accounts`, `POST /global_accounts/create`, `POST /simulation/deposit/create` | [Global Accounts](https://www.airwallex.com/docs/api/core_resources/global_accounts), [Sim: Deposits](https://www.airwallex.com/docs/api/simulation/deposits) |
| Balances | `GET /balances/current` | [Balances](https://www.airwallex.com/docs/api/core_resources/balances) |
| FX | `GET /fx/rates/current`, `POST /fx/quotes/create`, `POST /fx/conversions/create` (REST only; no MCP tool) | [Rates](https://www.airwallex.com/docs/api/transactional_fx/rates), [Quotes](https://www.airwallex.com/docs/api/transactional_fx/quotes), [Conversion](https://www.airwallex.com/docs/api/transactional_fx/conversion) |
| Payees | `POST /beneficiaries/schema`, `POST /beneficiaries/validate`, `POST /beneficiaries/create` | [Beneficiaries](https://www.airwallex.com/docs/api/payouts/beneficiaries) |
| Payouts | `POST /transfers/create`, `GET /transfers` | [Transfers](https://www.airwallex.com/docs/api/payouts/transfers) |
| Failure injection | `POST /simulation/transfers/{id}/transition` (SENT, then FAILED with `failure_type`) | [Sim: Transfers](https://www.airwallex.com/docs/api/simulation/transfers) |
| Reconciliation | `GET /financial_transactions` (source_type PAYOUT, CONVERSION, FEE; fee, net, client_rate) | [Financial Transactions](https://www.airwallex.com/docs/api/finance/financial_transactions) |
| Events | Webhooks `payout.transfer.paid`, `.failed`, `.cancelled` (configured in the sandbox web app; HMAC-SHA256 over x-timestamp plus raw body) | [Webhooks](https://www.airwallex.com/docs/api/webhooks/webhooks), [airwallexdev.com](https://airwallexdev.com/) |
| Dev tooling | Docs MCP `https://mcp.sandbox.airwallex.com/docs` (no auth); Developer MCP `https://mcp.sandbox.airwallex.com/developer` (sandbox OAuth) | [Developer connectors](https://www.airwallex.com/docs/developer-tools/ai/developer-connector) |
| Optional stretch | Issuing (virtual card for SaaS invoices); Security audit log `GET /audit_log/security_audit_logs` | [Cards](https://www.airwallex.com/docs/api/issuing/cards), [Activity Log](https://www.airwallex.com/docs/api/security/activity_log) |

**AgentOS note:** the AgentOS MCP (`https://mcp.airwallex.com/mcp`) and its skills are **production-only**, with money-out off by default. Use them only as the adoption story, not in the build. The build uses REST plus Developer MCP.

### Risks and mitigations
| Risk | Severity | Mitigation |
|---|---|---|
| **Sandbox quirks** (from the guide): failed transfers end in CANCELLED, not FAILED; a FAILED transition auto-cancels within seconds, so a slow poll can lose `failure_reason`; corridor-specific beneficiary fields and error codes (`010`, `011`, `016`, `083`); `request_id` length rule (10–50 characters); three different insufficient-funds codes | Med | Build a typed client in week 1 with a contract-test suite run against the sandbox daily. Branch on both FAILED and CANCELLED. Use webhooks plus polling |
| **FX has no MCP tool**; quotes are single-use; do not send `x-api-version` on FX calls | Low | REST-only FX module; fresh quote per conversion |
| **SWIFT fee math** (flat EUR 12.85 per SWIFT payout in sandbox); a replacement payout doubles fees | Low | The planner adds fees before converting; the replacement path re-checks funds |
| **Financial Transactions in sandbox:** whether fee and conversion rows show up promptly and completely is *unverified* | Med | Day-1 spike. Fallback: reconcile from transfer and conversion objects plus a fee table built from the guide's documented values |
| **Webhooks** need the web app plus a public tunnel; delivery is at-least-once and out of order | Low | Use a tunnel (cloudflared or ngrok); deduplicate on event ID; poll as backstop |
| **Auth/KYC:** sandbox KYB auto-approves only for businesses named "New Business Sandbox" or "Sandbox Business"; 30-minute token | Low | Use the default business; refresh the token automatically |
| **Rate limits:** 20 req/s global, 10 per endpoint, 10 concurrent | Low | Serial execution plus backoff; no parallel bursts in the demo |
| **Sandbox behavior may change without notice** (guide says so) | Med | Put simulation calls behind one interface; record a backup demo video by about 10 Nov |
| **LLM reliability:** invoice extraction errors, made-up bank details, prompt injection from supplier emails | Med–High | Structured output with code validation; the LLM never touches money fields or credentials; email text is treated as untrusted data; bank details only ever come from the vendor master or a human-verified update. Build a small eval set (~30 synthetic invoices and emails, including injection attempts) |
| **Agent safety and approvals** | High if done wrong | Policy engine in code; approvals bound to a hash of the terms; kill switch; every action logged before and after |
| **Scope creep** (three exception paths plus reconciliation plus UI) | **Highest** | Freeze scope at the demo script above. UI = one dashboard page plus an approval drawer. Cut the issuing stretch first |
| **Rules ambiguity:** whether pre-build-period work is allowed is unstated | Med | Do design and research only before 25 Oct 10:00 AM IST; write all code in the build window and commit history from day 1 |

### Verdict
**Yes, a solo developer can ship a credible demo in 3 weeks.** Confidence is medium-high. Every API involved is sandbox-only, documented in the guide's own kits, and needs no enablement email. The hard parts (state machines, idempotency, reconciliation) are deterministic code. The LLM's job is deliberately narrow: extract, explain, and draft. The main risk is scope, not APIs.

### Rough build plan (build window Sun 25 Oct, 10:00 AM IST to Fri 13 Nov, 11:59 PM IST)
- **Before 25 Oct (design only, no code):** finalize the demo script, synthetic data spec (5 vendors, 3 corridors, invoices, a BEC email), policy thresholds, and architecture diagram. Get sandbox login and the Docs MCP ready if the rules allow.
- **Week 1 (25–31 Oct): rails.**
  - Sandbox setup, auth, and funded USD wallet.
  - Typed Airwallex client covering balances, FX rates, quotes, and conversions, beneficiaries (US, GB, DE), transfers, transfer simulations, deposit simulation, and financial transactions.
  - SQLite idempotency ledger and duplicate locks.
  - Webhook receiver with HMAC verification and deduplication.
  - Contract tests.
  - **Exit:** a scripted end-to-end payout in all 3 corridors, including a forced return.
- **Week 2 (1–7 Nov): brain and controls.**
  - LLM extraction with validation, plus the eval set.
  - BEC tripwire (vendor master diff, freeze, verification task).
  - Deterministic planner (reserve floor, fees, priorities, defer).
  - Approval service bound to the terms hash.
  - Incident handler (wait, replace, or escalate).
  - Re-plan on deposit.
  - Reconciliation engine and ledger CSV export.
  - **Exit:** the full demo scenario runs headless from one command.
- **Week 3 (8–13 Nov): demo and ship.**
  - Minimal web UI: plan timeline, approval drawer, reconciliation table, audit log.
  - Scenario runner with a reset button.
  - Failure-injection tests.
  - README with setup and `.env.example`; open-source repo.
  - Record the video by **Wed 11 Nov** and keep a backup recording.
  - Submit by **Thu 12 Nov**, a full day before the Fri 13 Nov 11:59 PM IST deadline.

### What to stub for the demo
- Invoices, supplier emails, and the vendor master: **synthetic** files.
- Out-of-band call-back verification: a "Verified by phone" button for a human.
- Customer receipts: `simulation/deposit/create`.
- Transfer outcomes: `simulation/transfers/{id}/transition`.
- Accounting system: **CSV export** only (no Xero or QBO integration).
- Supplier notifications: drafted in the UI, never sent.
- If sandbox fee rows are missing, fees come from the guide's documented fee table.

---

## Sources
- Hackathon landing: https://airwallex.hackerearth.com/
- HackerEarth challenge page (exact UTC phase times, registrations, generic FAQ): https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/
- Official builder guide: https://airwallexdev.com/guide · developer lab: https://airwallexdev.com/
- Listing confirming dates and prizes: https://devgrantsdaily.com/items/2026-10-06-airwallex-agentic-banking-hackathon/
- Airwallex governance blog (7 Oct 2026): https://www.airwallex.com/global/blog/agentic-banking-governance
- Airwallex judge criteria (Sept 2026 partner hackathon): https://www.linkedin.com/feed/update/urn:li:activity:7500499794403049472 · https://www.linkedin.com/posts/sam-waldo_judging-the-agents-everywhere-hackathon-activity-7500783609373462528-jCSr
- Airwallex docs: https://www.airwallex.com/docs · API reference: https://www.airwallex.com/docs/api · AgentOS: https://www.airwallex.com/docs/developer-tools/ai/agentos · Developer connectors: https://www.airwallex.com/docs/developer-tools/ai/developer-connector
- AFP 2025 Payments Fraud survey: https://www.financialprofessionals.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024
- Visa SMB cross-border research (page dated "05/01/2026", day/month order ambiguous): https://corporate.visa.com/en/sites/visa-perspectives/trends-insights/as-smbs-go-global-payment-complexity-remains.html
- ARP Digital GCC SME survey 2026: https://www.arpdigital.io/en/resources/news-insights/gcc-sme-cross-border-payments-2026
- APQC duplicate or erroneous disbursements benchmark: https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number
- Kani Payments reconciliation survey 2025: https://kanipayments.com/wp-content/uploads/2025/04/Reconciliation-and-Reporting-Survey-2025_Kani-Payments.pdf

## Could not verify
1. **Official judging rubric or weights.** Not published anywhere I could reach: landing page, raw HTML, HackerEarth page, or search. The criteria above are proxies from official Airwallex sources (guide, blog) and an Airwallex judge's published criteria for a *different* event.
2. **Judges' identities.** The landing HTML contains styling for a judges section, but no judges are listed yet.
3. **Times for finalist selection (15 Nov) and Demo Day (19 Nov).** No time published, so no IST conversion is possible.
4. **Whether pre-build work or code is allowed.** No event-specific rule found. HackerEarth's generic FAQ is silent. Other HackerEarth hackathons require code to be written during the event, so assume the same.
5. **Whether the video is mandatory.** The Airwallex FAQ lists it as required, but HackerEarth's generic FAQ calls a demo video optional. Treat it as required.
6. **Inconsistent wording on the landing page:** "Over 48 hours" versus "3 weeks to design, build, ship." The HackerEarth phase dates confirm about 3 weeks.
7. **Kits 11 and 12** are "coming soon"; contents unknown.
8. **Sandbox behavior of `GET /financial_transactions`** (fee and conversion rows, timing). Documented, but not tested. I made no sandbox calls.
9. **Visa (TAP, VIC) and Metal tooling** requirements for the partner awards. Not researched in depth, since this idea doesn't target them.
10. **Pain numbers:** AFP is skewed toward larger US corporates; ARP is GCC and MENA only; Kani covers UK payments companies; APQC publishes only the median publicly. I found no primary-sourced global SMB figure for payment return rates or hours spent on reconciliation.
