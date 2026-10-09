# Agentic Banking Hackathon: Research Pack (Vedant Mahajan)

_Compiled Thu Oct 8, 2026 (IST). Files: 00 brief · 01 pains · 02 idea board · 03 recommended idea (Countersign) · 04 sources._

**Idea-phase deadline: Fri Oct 23, 2026, 11:59 PM IST (18:29 UTC). Build: Oct 25 10:00 AM IST → Nov 13 11:59 PM IST.**


---

# 00 · Airwallex Agentic Banking Hackathon: Full Brief

**Compiled:** Thu Oct 8, 2026 (IST) · **For:** Vedant Mahajan (solo, India, sandbox / free tiers only)
**Primary sources (fetched Oct 8, 2026):** HackerEarth challenge page + its embedded event data, `airwallex.hackerearth.com` landing page, `airwallexdev.com` (home, `/guide`, `/builds`, `/content/library.json`, `/content/builds.json`), Airwallex Docs MCP (`mcp.sandbox.airwallex.com/docs`, public).

> Ground rule for this pack: anything not seen on an official page is marked **(unverified)**. Times are given in UTC (as HackerEarth stores them) and IST (UTC+5:30).

---

## 1. Key dates

| Milestone | UTC (HackerEarth raw data) | IST (Vedant) | Source |
|---|---|---|---|
| Registration & Idea Phase opens | **Mon Oct 5, 2026 15:30** | Mon Oct 5, 9:00 PM | HackerEarth `phases[0].start = 2026-10-05T15:30:00` |
| **Registration & Idea Phase closes (APPLICATION DEADLINE)** | **Fri Oct 23, 2026 18:29** | **Fri Oct 23, 11:59 PM IST** | HackerEarth `phases[0].end = 2026-10-23T18:29:00` |
| Accepted teams notified + build period begins | Sun Oct 25, 2026 04:30 | Sun Oct 25, 10:00 AM | HackerEarth `phases[1].start`, landing page "Oct 25: Accepted teams are notified" |
| **Project submissions due** | **Fri Nov 13, 2026 18:29** | **Fri Nov 13, 11:59 PM IST** | HackerEarth `phases[1].end = 2026-11-13T18:29:00` |
| Finalists selected | Nov 15, 2026 (no time given) | Nov 15 | Landing page |
| Demo Day, San Francisco (remote optional) | Nov 19, 2026 (no time given) | Likely the night of Nov 19 / early Nov 20 IST if held in PT business hours (unverified) | Landing page |

**Important:** the landing page says *"Accepted teams are notified"* on Oct 25. So the idea application is a **selection gate**, not just a formality. The idea write-up has to earn the spot.

**Mismatches between official pages (be aware of them):**
- The landing page says "Over 48 hours, teams build…" but also "3 WEEKS to design, build, ship". The HackerEarth phases show **~20 days** (Oct 25 to Nov 13). Plan for 3 weeks.
- The landing page shows "12 tracks across the stack", but only **10 starter kits** exist. Kits 11 and 12 say "Coming soon".
- The landing page writes "Allowlisted **Air** CLI access" for kit 9. The guide says **Airi CLI** (app.airi.com). The guide is the more detailed source.
- A Sep 24 LinkedIn post by Airwallex's Dan Kim said the prize pool was "$70k (up from $50k)". The current pages say $100K in prizes and credits. Current pages win.
- HackerEarth's generic FAQ (shown on the event page) says to submit "on HackerEarth in tar/zip file format along with instructions" and that "all code needs to be in public domain (open source) so that it can be evaluated by the judges". Airwallex's FAQ says "a link to your repository with setup instructions". **Do both:** a public GitHub repo plus a zip upload on HackerEarth.

## 2. Format, eligibility, cost, IP

- **Host:** Airwallex, run on HackerEarth. Event slug `agentic-banking-hackathon`, **433 registrations** as of Oct 8, 2026 (HackerEarth counter).
- **Online and global.** Optional in-person demo day in SF. "Mentors and judging are available to remote teams too."
- **Team size:** 1 to 4. Solo is explicitly allowed ("Both work"). There's a community Discord for finding teammates, but the invite link wasn't on the public pages. It is probably inside the registered dashboard (unverified).
- **Who can enter:** "Developers, designers, data scientists, and founders aged **18 and over**, anywhere in the world."
- **Cost:** free. "Every registered participant gets access to the Airwallex sandbox and workshops."
- **IP:** "You retain full ownership of your project. Submitting only grants us permission to showcase your work." HackerEarth's generic FAQ adds that the code must be public/open source so judges can evaluate it.
- **Support:** support@hackerearth.com (platform). devhelp@airwallex.com (API/sandbox, access requests).

## 3. What to submit (final, by Nov 13)

From the official FAQ:
1. **A working demo**
2. **A short video walkthrough under 5 minutes**
3. **A link to your repository with setup instructions**

From HackerEarth's generic FAQ: a zip/tar upload with source and run instructions. A DB dump is optional. A prototype is acceptable, but "the submission should be functional so that it can be reviewed by the judges."

## 4. The idea application (due Oct 23, 11:59 PM IST)

**I could not see the form fields.** The `?register=true` flow needs a logged-in HackerEarth session, and the public event data has no form schema. Vedant has to open it while logged in.

What we know: the phase is called "Registration & Idea Phase" and acceptance is announced Oct 25. Typical HackerEarth idea phases ask for (unverified): idea title, track/theme, a problem + solution description (often a rich-text box), tech stack, team details, and sometimes a PDF/PPT upload. `03-recommended-idea.md` §15 has the write-up in **modular blocks** (25-word, 75-word, 200-word and 500-word versions, plus a slide outline), so it fits whatever the form asks for.

**Action for Vedant:** log in, open the form, screenshot every field and its character limit, and paste the right block from §15.

## 5. Prizes and credits

| Prize | Amount | Requirement (verbatim) |
|---|---|---|
| Founder's Choice | **$30,000** | "Open category. No specific requirements." |
| Judges' Choice | **$20,000** | "Open category. No specific requirements." |
| Visa Award | **$15,000** | "Requires use of Visa and Airwallex tooling" |
| Metal Award | **$15,000** | "Requires use of Metal and Airwallex tooling" |
| Claude credits | $10,000 | (pool; distribution rules not stated) |
| AWS credits | TBD | (not stated) |
| Base44 credits | $16,000 | (pool) |

Cash prizes total **$80K**. With credits, it is about $106K+ ("$100K"). Whether one project can win more than one prize **is not stated** (unverified). Ask in Discord/Slack.

### Product partners (from the landing page logo table)
| Partner | What they offer builders |
|---|---|
| **Visa** | Trusted Agent Protocol (TAP), Visa Intelligent Commerce (VIC), Slack support |
| **Claude** (Anthropic) | Free LLM tokens, email support |
| **AWS** | Compute credits, Bedrock AgentCore, Slack support |
| **Metal** (Metallicus; X handle @metalntwx) | "L1 blockchain, docs, nodes, faucet, wallets", Slack support |
| **Coinbase** | CDP, stablecoin infrastructure, Slack support |
| **T:0** (logo alt text "tZERO"; X handle @t0finance) | "AI accounting, docs, MCP server, sandbox", Slack support |
| **Base44** | AI no-code app builder, developer credits, Slack support |

**What "Visa tooling" probably means:** Visa's Trusted Agent Protocol is open source (github.com/visa/trusted-agent-protocol: RFC 9421 HTTP message signatures, sample agent, merchant, CDN proxy and registry). VIC is "free to use in Sandbox" per developer.visa.com. However, VIC on the Visa Acceptance Platform needs a merchant ID, a token requester ID and a relationship ID, and you get those from a Visa account manager. That is high access risk for a solo builder. TAP alone is usable with no access request.

**What "Metal tooling" probably means:** Metal L2 (an OP Stack, Ethereum-aligned chain) has a public testnet with faucets (Superchain faucet, QuickNode, thirdweb, a native USDC testnet faucet). Metal Blockchain (L0/L1, EVM subnets) has docs, nodes and an explorer. **Both are usable with no card and no access request.** The exact award bar ("use of Metal") isn't defined, so confirm with Metal's Slack.

## 6. Judging signals

No official rubric is published on the hackathon pages (gap). The best proxy is **Sam Waldo (Airwallex, Head of Startups, Asia)**, who judged Airwallex-backed hackathons in 2026. From his LinkedIn posts and the AI Tinkerers Singapore post:
1. Does it solve a **genuine problem for founders or operators**?
2. Does it **work across markets, currencies and business environments**?
3. Is there a **credible path from prototype to adoption**?
4. Has the team built the **operational foundation, not only the interface**?
5. Does it **balance autonomous execution with appropriate control**?

His favorite at AI Tinkerers SG (Sep 2026) was a meeting agent built on AgentOS MCP. It proposed invoice actions, pulled contract, fulfillment and invoice context together, and "requires explicit human approval before writing into Airwallex."

The builder guide adds the hosts' own rubric under "Build around a financial decision":
- Choose a finance task someone repeats, and find the **decision** inside it. The agent must **choose differently when balance, deadline, evidence or risk changes.**
- Let the agent **move money or update financial state**, and state which actions need a person's approval.
- The demo shows: the goal → the initial plan → **new information** → the **revised decision** → the resulting balance/payment/status.
- **Keep amounts, limits, reserves, validation, duplicate protection and state transitions in code.** Use the model to read unstructured text, compare evidence, propose a plan and explain exceptions.
- Give the model **typed tools, not unrestricted credentials**. **Bind each approval** to amount, currency, counterparty, terms and evidence.
- Put sandbox simulation calls behind one interface.
- End with a financial action or an escalation to a person. "If the agent should make the same choice every time, write the rule in code."
- Explicit hint: *"Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them. **Good territory if you want a problem few other builders will take on.**"*

## 7. Starter kits: what you build and what access you need

Kits 1–8 run on the plain sandbox. Kits 5–8 need Airwallex to switch on features for you. Kits 9–10 need allowlisting.

| # | Kit | Use case | What you build (guide wording, condensed) | Before you start | Solo access risk |
|---|---|---|---|---|---|
| 1 | Adaptive Treasury Controller | Treasury & Ops | Five obligations, three currencies, 72 hours, a reserve floor. Fund / convert / defer / escalate. Recalculate only the affected decisions after a deposit. Tie the autonomous FX limit to forecast confidence. | Fund a wallet (simulated deposit) | **None** |
| 2 | Intent-Bound Purchase Agent | Expense & Policy | Monthly vs. annual SaaS term against the reserve. Enforce the choice with virtual-card controls (limits, currency allowlist, MCC). Simulate pass and fail authorizations. | Fund a wallet | **None** |
| 3 | Payment Ops Incident Commander | Treasury & Ops | A supplier says the transfer never arrived. Wait / replace / escalate, with finality, idempotency and duplicate locks so you never pay twice. | Fund a wallet | **None** |
| 4 | Dispute Response Agent | Revenue Protection | Three chargebacks with different economics: challenge, accept or escalate. Handle the issuer rejecting your evidence. | **None** | **None** |
| 5 | Platform Spend Controller | Multi-Tenant Platforms | Issue cards to connected accounts. Ration scarce bridge capital when customer deposits are late. Collect a fee. | **Request platform access** (connected accounts + platform payments) | **Medium–High**: needs devhelp@ to enable; reply time unknown |
| 6 | Multi-Employer Payroll Executor | Multi-Tenant Platforms | Payroll across 3 employers. Never use one employer's funds for another. Price fees before converting. | **Platform access; three accounts** | **Medium–High** |
| 7 | Portfolio Lending Agent | Dynamic Lending | Collect revenue-share repayments. Size a new advance without breaching the reserve floor. | **Request platform access** | **Medium–High** |
| 8 | Marketplace Settlement Agent | Multi-Tenant Platforms | Per-seller reserves from refund risk, pay the net, re-reserve one seller after a carrier failure, recover the shortfall. | **Request platform access** | **Medium–High** |
| 9 | Approval-Bound Shopping Agent | Agentic Commerce | A real merchant checkout via browser automation. The shopper approves product/merchant/total and is re-asked if anything changes. Payment credentials + mandate via Airi CLI. Real orders with an Airwallex-funded card. | **Allowlisted Airi CLI access** (create an account at app.airi.com, then email devhelp@airwallex.com) | **High**: internal testing, allowlist, unknown wait |
| 10 | Merchant-Enabled Agentic Checkout | Agentic Commerce | A sandbox storefront with 100+ synthetic products, discoverable through Claude via a merchant MCP. Test-card checkout returns a merchant order number. | **Request merchant-side Agentic Commerce access.** The Merchant Onboarding API is a **draft, not deployed**. | **Very high**: the contracts are proposed, not live |

**Kits that need special access (the answer to "which ones can a solo applicant get stuck on"):** kits **5, 6, 7, 8** (connected accounts + platform payments, enabled by Airwallex on request), kit **9** (Airi CLI allowlist) and kit **10** (merchant-side Agentic Commerce, draft API). **Kits 1–4 need nothing extra.** The guide itself says "Pick kit 2 or 4 if you want to call the API before funding a wallet."

**To request platform access anyway (cheap insurance):** email devhelp@airwallex.com with your sandbox email + Client ID and ask for **both** "connected accounts" **and** "platform payments" (connected accounts alone won't allow `connected_account_transfers/create` or `charges/create`).

### Per-kit endpoints (from the guide; all prefixed `https://api.sandbox.airwallex.com/api/v1`)
- **Kit 1:** `GET /balances/current`, `GET /fx/rates/current`, `POST /fx/quotes/create`, `POST /fx/conversions/create`, `POST /beneficiaries/schema`, `POST /beneficiaries/create`, `POST /transfers/create`, `POST /simulation/deposit/create`, `POST /simulation/transfers/{id}/transition`
- **Kit 2:** `POST /issuing/cardholders/create`, `POST /issuing/cards/create`, `GET /issuing/cards/{card_id}/limits`, `POST /issuing/cards/{id}/update`, `POST /simulation/issuing/create`, `/simulation/issuing/{transaction_id}/capture`, `/simulation/issuing/{transaction_id}/reverse`, `/simulation/issuing/refund`, `GET /issuing/transactions`
- **Kit 3:** `POST /beneficiaries/schema`, `POST /beneficiaries/create`, `POST /transfers/create`, `POST /simulation/transfers/{id}/transition`, `GET /transfers`
- **Kit 4:** `POST /pa/payment_intents/create`, `POST /pa/payment_intents/{id}/confirm`, `POST /simulation/pa/payment_disputes/create`, `GET /pa/payment_disputes`, `POST /files/upload` (on `files.sandbox.airwallex.com`), `POST /pa/payment_disputes/{id}/accept`, `POST /pa/payment_disputes/{id}/challenge`, `POST /simulation/pa/payment_disputes/{id}/escalate`, `POST /simulation/pa/payment_disputes/{id}/resolve`, `GET /pa/refunds`
- **Kits 5–8 (platform):** `POST /accounts/create`, `/accounts/{id}/update`, `/accounts/{id}/submit`, `POST /simulation/accounts/{id}/update_status`, `GET /accounts/{id}`, plus `x-on-behalf-of` on customer-scoped calls, `POST /connected_account_transfers/create`, `POST /charges/create`, `POST /platform_reports/create`, `GET /reference/industry_categories`

## 8. Sandbox setup and conventions (from the guide)
1. Sign up at **sandbox.airwallex.com**. A personal email is fine. Keys are under Account > Developer > API keys. If you add a second business, name it exactly `New Business Sandbox` or `Sandbox Business` (otherwise it stays "In review").
2. MCP: Docs `https://mcp.sandbox.airwallex.com/docs` (no account) and Developer `https://mcp.sandbox.airwallex.com/developer` (sandbox login). AgentOS plugin: `claude plugin install airwallex-agentos@claude-plugins-official`. Cursor, Codex, Gemini CLI and Windsurf configs are on airwallexdev.com.
3. Verify by asking the agent to list Global Accounts. An empty list still means you're connected.
4. Conventions: base URL `https://api.sandbox.airwallex.com/api/v1`. Auth with `POST /authentication/login` (headers `x-client-id`, `x-api-key`, no body); the token lasts **30 min**. **Amounts are major units** (100 = $100). `request_id` is a UUID, reused only for a retry of the *same* operation; reusing one within 7 days for a new operation returns `duplicate_request_id`. Transfers require a 10–50 char `request_id`.
5. Funding: no top-up button. `GET /global_accounts` → create one if needed (`country_code` is the *country*, e.g. US for USD, NL/FR/DE for EUR) → `POST /simulation/deposit/create {global_account_id, amount}` posts immediately even though it says PENDING.
6. Rate limits: **20 rps global, 10 per endpoint, 10 concurrent**. Back off on 429.

### Sandbox gotchas worth designing around
- **Transfers:** a failed transfer ends in **CANCELLED** (never a status called FAILED in the final state). Read `failure_type` and `failure_reason`. FAILED auto-cancels in seconds, so slow polling can miss `failure_reason`; branch on both. Simulate SENT before PAID or FAILED. **PAID is not always final.** The docs say a transfer can move to FAILED after PAID if the clearing system or recipient bank rejects it, so keep listening for `payout.transfer.failed`.
- **Simulated failure types** (docs MCP): `ACCOUNT_CLOSED, ACCOUNT_CURRENCY_MISMATCH, ACCOUNT_INACTIVE_OR_DORMANT, ACCOUNT_UNDER_RESTRICTION, BENEFICIARY_BANK_RETURNED, BENEFICIARY_NAME_MISMATCH, BENEFICIARY_REQUESTED, CARD_ISSUER_ERROR, CHANNEL_POLICY, CHANNEL_TIMEOUT, CLIENT_REQUESTED, DUPLICATION_RETURN, EXCEEDED_TRANSACTION_AMOUNT_OR_LIMIT, INBOUND_* , INSUFFICIENT_FUNDS, INVALID_ACCOUNT_NAME_OR_NUMBER, INVALID_BANK_INFORMATION, INVALID_BANK_OR_BRANCH_CODE, INVALID_BENEFICIARY_DETAILS, INVALID_CORRESPONDENT_BANK_INFORMATION, INVALID_PAYMENT_PURPOSE, INVALID_SPECIAL_CHARACTER, INVALID_SWIFT_BIC_CODE, OTHER, RECALL_REQUESTED, SYSTEM_ERROR, TM_SUSPENDED, TRANSACTION_AMOUNT_NOT_COVERING_FEE, UNABLE_TO_APPLY`.
- **Fees:** SWIFT payouts cost a flat **EUR 12.85** in the sandbox examples. LOCAL payouts are free. Add the fees *before* converting.
- **FX:** leave `x-api-version` off FX calls. A rate (`rate`) is not a quote (`client_rate`, `quote_id`). The docs list quote validity options of 1 min / 15 min / 30 min / 1 h / 4 h / 8 h / 24 h (`valid_to_at`). Treat a quote as single-use in your code (the sandbox will actually accept a re-use). Conversions settle immediately (`SETTLED`). **No MCP tool for conversions: use REST.**
- **Beneficiaries:** bank details are validated at *create*, not at pay (a bad IBAN fails with code `083`). Use real routing codes with synthetic account numbers. US: `account_routing_type1: "aba"`, `bank_account_category` exactly `Checking`/`Savings`. GB: `sort_code` (lowercase) + `bank_name`. DE/EUR SWIFT: IBAN + `swift_code`.
- **Insufficient funds:** three different codes for the same state: `balance_insufficient` (transfers), `insufficient_fund` (charges), `insufficient_funds` (FX).
- **Cards:** don't wait for APPROVED. Treat `transaction_type: CLEARING` as accepted and `failure_reason` as declined. Per-transaction limits are inclusive.
- **Webhooks:** configure them in the sandbox web app (Settings > Developer > Webhooks), not via the API. HMAC-SHA256 over `x-timestamp` + raw body. At-least-once and out of order, so dedupe on event id and return 200 fast. Airwallex retries for about 3 days. Tunnel localhost for dev.

## 9. Reference builds published by the hosts (to avoid cloning them)
From `airwallexdev.com/content/builds.json` (all under github.com/awx-devx):
- **Agent cards**: an agent gets a card and off-policy charges decline.
- **Drop-in checkout flow**: an embedded card checkout.
- **Invoicing in Slack**: tag a thread, get an Airwallex invoice.
- **AI finance manager** (Hermes/Telegram): reads live balances, flags anomalies, prepares payments and waits for a yes.
- **Allocard**: company cards with rule-driven dynamic limits.

→ Judges have already seen "chat with your balances", "cards with limits" and "invoice from Slack". **A new entry has to go deeper operationally than these.**

## 10. Constraints specific to Vedant
- **No credit card:** the Airwallex sandbox signup is free with no card. Metal L2 testnet faucets are free. Visa TAP's sample is open source. VIC needs account-manager IDs. Avoid paid hosting; local + a tunnel (e.g. `cloudflared` quick tunnel, free) is enough for webhooks.
- **Limited disk, no local LLMs:** use a hosted model API (hackathon Claude credits if granted, otherwise any free tier). Keep model calls few and typed.
- **Solo:** stick to kits 1–4 territory (no access gate). Request platform access only as optional insurance.
- **Fresh project:** per Vedant's instruction, the idea must be greenfield and must not reuse or extend any previous project.

---

# 01 · Real-World Pains: Finance Ops for Cross-Border SMBs, Platforms and Exporters

**Method.** For each pain I list who has it, what happens, the cost (with a cited number), today's workaround, why an *agent with controlled money movement* helps, and the evidence URLs.

**Rules I followed:**
- No invented numbers.
- Every figure names its source.
- **(verified)** = I opened the primary page or PDF and saw the number.
- **(search-index)** = the number came from a search result snippet or a secondary page, and the primary page was blocked or errored. Treat these as unverified until re-checked.
- Reddit blocked direct fetching (HTTP 403 "blocked by network security"). Reddit threads are cited by URL with the gist from the search index, and they are qualitative signal only.

---

## Summary table

| # | Pain | Headline number | Status |
|---|---|---|---|
| P1 | Vendor impersonation / BEC / redirected supplier payments | **74%** of US orgs hit by BEC in 2025 (AFP 2026); **$2.77B** BEC losses reported to FBI in 2024 | verified / search-index |
| P2 | Duplicate & erroneous supplier payments | **1.5%** of disbursements duplicate or erroneous (APQC median, n=1,686) | verified |
| P3 | Manual AP processing cost and slowness | **$9.84** per invoice, **8.2 days** average cycle (Ardent 2025) | verified |
| P4 | Failed / delayed cross-border payments and investigations | **$118.5B** global cost of failed payments in 2020 (LexisNexis/Accuity); **$1.6B/yr** spent on investigations (Swift 2025) | verified |
| P5 | "Supplier says it never arrived": status opacity and double-pay risk | Investigations take **5–10 working days** (Swift); PAID is not final (Airwallex docs) | verified |
| P6 | Hidden FX markups on business payments | UK SMBs lost **£2.8B** in 2023 to hidden international payment fees, +27% since 2018 (Wise / Capital Economics) | verified |
| P7 | FX volatility hits unhedged SMEs | **54%** of UK SME traders hurt by currency volatility, avg loss **>£53k** (Bibby 2025) | search-index |
| P8 | Cash shortfalls and liquidity forecasting | **62%** of treasury pros call cash forecasting their #1 challenge (AFP 2025) | search-index |
| P9 | Late customer payments (AR) | **47%** of B2B invoices overdue in W. Europe, bad debt on **6%** (Atradius 2025); US SMBs owed **$17.5k** avg (Intuit 2025) | verified / search-index |
| P10 | India MSME delayed receivables | **₹7.34 lakh crore** delayed (Mar 2024, GAME-FISME); **₹8.1 lakh crore** (Economic Survey 2025–26) | search-index |
| P11 | India exporters & freelancers: inbound FX cost + FEMA/FIRA compliance | Export proceeds must be realised in **9 months** (RBI amendment, effective Oct 1, 2026); platform FX ~**1.6–2%** (comparison sites) | search-index |
| P12 | Month-end close and cash reconciliation | **50%** of teams take 6+ business days to close; cash rec **20–50 hrs/month** across 3–5 systems; Excel used by **94%** (Ledge 2025) | verified |
| P13 | Multi-currency bookkeeping (realised FX gain/loss, clearing accounts) | Qualitative (r/Accounting, r/xero threads) | qualitative |
| P14 | Chargebacks and friendly fraud | **$4.61** cost per $1 of fraud for US merchants (LexisNexis 2025); net chargeback recovery **10.7%** (Chargebacks911, vendor) | verified / vendor |
| P15 | Marketplace and seller cash held in reserves; conversion fees on payouts | Amazon ACCS fee **1.5%** below $500k trailing volume; DD+7 hold complaints | verified (Amazon page via search) / qualitative |
| P16 | SaaS spend sprawl and surprise renewals | **66.5%** of IT leaders saw unexpected SaaS charges; avg **$21M/yr** wasted on unused licenses (Zylo 2025, enterprise-skewed) | verified |
| P17 | Contractor and payroll payout errors | **$291** average cost per payroll error, **80.15%** accuracy (EY 2022, US) | search-index |
| P18 | Small cross-border transfers still expensive | Global average remittance cost **6.36%** of $200 (World Bank RPW Q3 2025) | verified (snippet of RPW PDF + RPW homepage) |
| P19 | Fintech account freezes and opaque support | Airwallex Trustpilot ~**3.1** vs G2 ~4.3; Payoneer ~3.5 on ~62.7k reviews | search-index |
| P20 | Trust gap for agents that spend money | Only **24%** of US online adults trust agents for routine purchases (Forrester 2025) | search-index |
| P21 | Internal billing and expense fraud | Orgs lose **5%** of revenue to fraud; billing schemes = 22% of cases, $100k median (ACFE 2024) | search-index |
| P22 | Fraud detection lives in treasury, but AI adoption lags | Treasury finds **83%** of attempted fraud; only **17%** of orgs use AI against payments fraud (AFP 2026) | verified |

---

## P1 · Vendor impersonation / BEC / redirected supplier payments
- **Who:** AP clerks, founders and finance leads paying suppliers by wire/ACH/local transfer, especially across borders, where they can't easily phone the supplier's bank.
- **What happens:** A fraudster spoofs a supplier's email (or compromises it) and sends "updated bank details" or a lookalike invoice. The payer edits the beneficiary and wires the money to a mule account. Cross-border recovery is slow and often fails.
- **Cost:**
  - AFP 2026 Payments Fraud & Control Survey (465 US treasury practitioners, Jan 2026): **74% of organizations were affected by BEC in 2025**. 76% had attempted or actual payments fraud. Financial losses were reported by 48% of orgs under $1B revenue. **(verified)**
  - AFP 2025 survey (2024 data, 521 respondents): BEC was the #1 avenue at 63%. **Vendor imposter fraud 45%, up 11 points.** Third-party impersonation was 63% of BEC types. **Wires were the payment method most targeted by BEC (63%, up from 39%).** Only 22% recovered ≥75% of lost funds (down from 41%). **(verified)**
  - FBI IC3 2024 report: **BEC losses $2,770,151,146** from 21,442 complaints. **(search-index**: IC3 PDF link from search, not opened)
- **Workaround today:** "Call-back" verification to a known phone number, dual approval in banking portals, manual checks of vendor master changes, staff training.
- **Why an agent helps:** It can diff every invoice's remittance details against the vendor's **bank-detail fingerprint on file**. A change, a new country, or name/IBAN/routing drift **quarantines** the payment, forces out-of-band verification and **requires a second human approval bound to the new details**. Code enforces it; the LLM only reads the email/PDF and explains the anomaly. Airwallex exposes `POST /api/v1/beneficiaries/verify_account` (account verification; its sandbox behaviour is unverified) and beneficiary update history via `POST /beneficiaries/{id}/update`.
- **Evidence:** https://www.prnewswire.com/news-releases/over-75-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags-302738857.html · https://www.financialprofessionals.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024 · https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf

## P2 · Duplicate and erroneous supplier payments
- **Who:** AP teams with invoices arriving by email, portal and paper, often several copies of the same invoice (reminder, PDF re-send, statement).
- **What happens:** The same invoice is keyed twice (different invoice-number formatting, a re-sent PDF, a credit note ignored), or a "failed" transfer is re-sent while the original still clears.
- **Cost:** APQC Open Standards Benchmarking: **median 1.5% of disbursements are duplicate or erroneous payments** (total sample 1,686 companies). **(verified)** Some secondary sites claim top performers at ~0.8% and the bottom at >2%. **(search-index, unverified)**
- **Workaround:** Exact-match ERP checks (vendor + invoice number), post-payment audit/recovery firms, spreadsheets.
- **Why an agent helps:** Fuzzy duplicate detection (normalized invoice numbers, amount ± tolerance, date window, PDF hash, line-item similarity read by the LLM) **before** payment. **Idempotent execution** (deterministic `request_id` per obligation and attempt, checked via `GET /api/v1/transfers?request_id=` before any retry). A **duplicate lock** per obligation so a replacement can't be issued until the original is terminal.
- **Evidence:** https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number · https://www.cfo.com/news/metric-of-the-month-detect-and-prevent-duplicate-or-erroneous-payments/656852/

## P3 · Manual AP: cost per invoice and cycle time
- **Who:** AP/finance ops at SMBs and mid-market companies.
- **What happens:** Invoices are keyed by hand, approvals chased in email, payment runs built in spreadsheets.
- **Cost:** Ardent Partners *State of ePayables 2025*: average all-inclusive **$9.84 to process one invoice**, **8.2-day** average cycle. Best-in-class: $2.65 and 2.9 days, vs **$12.42 and 13.5 days** for everyone else. **(verified**, PDF opened)
- **Workaround:** AP automation suites (Bill.com, Tipalti, Coupa), mostly domestic-first. Many SMBs still use spreadsheets + bank portal.
- **Why an agent helps:** The LLM extracts invoice data. Code validates it and routes approvals by policy. Payment runs execute directly on the money rails (Airwallex) instead of being re-keyed into a bank portal.
- **Evidence:** https://www.bottomline.com/cdn/1517/5157/1685/Ardent_Partners_-_State_of_ePayables_2025_-_Bottomline_-_FINAL.pdf

## P4 · Failed and delayed cross-border payments
- **Who:** Anyone paying abroad: SMB importers, platforms paying sellers, payroll operators.
- **What happens:** Payments bounce (name mismatch, closed account, wrong routing/BIC, missing purpose code), get stuck in compliance review at an intermediary, or return weeks later minus fees.
- **Cost:**
  - LexisNexis/Accuity: **failed payments cost the global economy $118.5B in 2020** (fees, labour, lost business). Corporates averaged ~$220k/yr, banks ~$360k/yr. **(search-index**: the press-release title is verified in search; numbers from the snippet)
  - Swift (Apr 17, 2025): the industry spends **>$1.6B a year** on labour-intensive investigations of held-up payments. Some large banks pay >$20M/yr in fees and penalties. "It can typically take **five to ten working days**" to investigate and resolve. 90% of Swift payments reach the end bank within an hour; delays come mostly from missing information. **(verified)**
  - BNY: ~5% of cross-border payments hit friction needing manual intervention. **(search-index)**
- **Workaround:** Ops staff open bank "traces", email screenshots of MT103s, re-send and hope.
- **Why an agent helps:** It validates payees *before* paying (`POST /beneficiaries/validate`, schema per corridor). It reads `failure_type` (`BENEFICIARY_NAME_MISMATCH`, `INVALID_BANK_OR_BRANCH_CODE`, `INVALID_PAYMENT_PURPOSE`, `ACCOUNT_CLOSED`, …), maps each to a remediation playbook, drafts the supplier request for corrected details, and only re-pays once the original is terminal.
- **Evidence:** https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20210714-true-cost-of-failed-payments · https://www.swift.com/news-events/press-releases/swift-solution-managing-cross-border-payments-investigations-could-save-industry-millions-operational-costs · https://www.bny.com/corporate/global/en/insights/payment-investigations-from-evolution-to-revolution.html

## P5 · "Supplier says it never arrived": status opacity and double-pay risk
- **Who:** Founders and ops leads under supplier pressure ("ship is held until paid").
- **What happens:** The payer sees "sent" or even "paid". The supplier sees nothing. Under deadline pressure the payer sends again, then both payments land. Or the first one fails *after* looking final.
- **Cost:** Swift: 5–10 working days to resolve an investigation (above). Airwallex's own docs: *"`PAID` is not always final. A transfer can still move to `FAILED` after `PAID` if it is later rejected by the local clearing system or the recipient bank."* **(verified via Airwallex Docs MCP)** A Reddit r/Banking thread: "sent a SWIFT transfer from abroad 10 business days ago and it still hasn't arrived" (qualitative).
- **Workaround:** Phone calls, UETR traces, manual "do not re-send" notes.
- **Why an agent helps:** A state machine that treats SENT/PAID as non-final, listens for `payout.transfer.failed` after PAID, and enforces a **wait / replace / escalate** decision with a duplicate lock. It sends the supplier a proof-of-payment pack (transfer id, reference, amount, timestamps) as a **draft** for a human to send.
- **Evidence:** Airwallex docs, transfer statuses: https://www.airwallex.com/docs/payouts/transfers/create-a-transfer/transfer-statuses.md · https://www.reddit.com/r/Banking/comments/1u2xjdl/ · https://airwallexdev.com/guide (kit 3)

## P6 · Hidden FX markups on business payments
- **Who:** SMB importers and exporters, e-commerce sellers, startups paying overseas contractors and SaaS.
- **What happens:** Banks quote "no fee" but embed a wide spread in the exchange rate. Businesses can't see the true cost, so they convert too often, in small amounts, at bad times.
- **Cost:** Wise / Capital Economics report ("The £2.8bn business problem"): **UK SMBs lost £2.8bn in 2023 to hidden fees on international payments, up 27% from £2.2bn in 2018.** **26%** are put off expanding overseas by the high cost of international banking. **(verified**, PDF opened) An older UK analysis estimated ~£4bn/yr and found 96% of bank revenue on a typical £75k EU transfer came from the FX spread. **(search-index)**
- **India-specific:** card forex markups of 1–3.5% plus GST on the markup for foreign SaaS paid by Indian startups. **(search-index**, tax-guide sites)
- **Workaround:** Switching to Wise/Airwallex/Revolut Business. Manual "convert once a month" habits.
- **Why an agent helps:** **Net obligations by currency**, convert once per run with a locked quote, prefer LOCAL rails over SWIFT where available (Airwallex sandbox: LOCAL fee 0 vs SWIFT EUR 12.85), and show the realised cost per payment in the run report.
- **Evidence:** https://wise.com/imaginary-v2/images/3377a6584910ba4ef7b4225eb5bff069-Wise%20%E2%80%94%20End%20the%20Opt%20Out%20Campaign.pdf · https://www.leaprate.com/news/sme-international-forex-transfers-generate-4-billion-in-hidden-uk-bank-fees-accourt/ · https://taxguru.in/goods-and-service-tax/foreign-software-subscriptions-attract-gst-reverse-charge-itc.html

## P7 · FX volatility on unhedged SMEs
- **Who:** SME importers and exporters with foreign-currency payables or receivables and no treasury function.
- **Cost:** Bibby Financial Services UK international trade report 2025: **54%** of SME traders negatively affected by currency volatility, **average loss >£53,000**. Only 36% of overseas traders use specialist FX providers. **(search-index)** Corpay 2025 Economic Outlook: **56% of businesses have no formal hedging policy.** **(search-index)** Mid-sized corporates hedge far more (81%, MillTechFX). **(search-index)**
- **Workaround:** Ad-hoc conversion when a bill is due, or none.
- **Why an agent helps:** Rule-based "convert the minimum now, lock a 24h quote for known near-term payables, leave the rest". It is *not* speculative: policy lives in code, quotes are bound to approvals, and the agent explains the trade-off.
- **Evidence:** https://www.bibbyfinancialservices.com/assets/documents/bltcaabb0e00358b2d2/blte04864e15d01ca6f/trading-places-bfs-international-trade-report-2025.pdf · https://www.leasinglife.com/news/uk-smes-count-cost-of-currency-volatility-average-53k-lost-in-2025/ · https://assets.ctfassets.net/h83dujey17us/4VayZIHNOpKZb4Xm3Aagv8/cdc4c33998f24c09bdccac615156fdf5/Economic_Outlook_Survey_2025.pdf

## P8 · Cash shortfalls: deciding what to pay when you can't pay everything
- **Who:** Founders and finance leads at startups and SMBs with lumpy receipts.
- **Cost:** AFP 2025 Treasury Benchmarking Survey: **cash/liquidity forecasting is the biggest challenge for 62%** of treasury professionals, and the top priority for 73%. **(search-index**, AFP PDF link from search)
- **Workaround:** A spreadsheet of "who screams loudest", paying critical suppliers late, emergency credit.
- **Why an agent helps:** This is exactly kit 1. A code-side planner ranks obligations by operational criticality, penalty and due date against a **reserve floor**. It defers the cheapest, escalates exceptions, and recalculates **only affected decisions** when a deposit lands.
- **Evidence:** https://7185359.fs1.hubspotusercontent-na1.net/hubfs/7185359/Research%20Surveys/SURVEYS/2025%20AFP%20Treasury%20Benchmarking%20Survey%20Comprehensive%20Report.pdf · https://airwallexdev.com/guide

## P9 · Late customer payments (AR)
- **Who:** SMB sellers, agencies, B2B exporters.
- **Cost:** Atradius Payment Practices Barometer, Western Europe 2025: **47% of B2B invoices overdue; bad debts hit 6% of B2B invoices.** **(verified**, PDF opened) Intuit QuickBooks 2025 US Small Business Late Payments Report (survey of 2,487 businesses, Jan 2025): **56% had unpaid invoices, owed $17,500 on average.** **(search-index**: the Intuit page returned HTTP 500 when fetched)
- **Workaround:** Manual dunning emails, factoring, giving up.
- **Why an agent helps:** It matches incoming deposits (Global Account `deposit.settled` webhooks / `GET /financial_transactions`) to open invoices across currencies, flags short-pays (fees deducted by intermediaries), drafts dunning messages and decides when to convert the receipts.
- **Evidence:** https://group.atradius.com/dam/jcr:80448207-97e5-4005-98b5-d5bb90e7107d/payment-practices-barometer-western-europe-2025-en.pdf · https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2025/

## P10 · India MSME delayed receivables
- **Who:** Indian MSMEs selling to larger buyers, domestically and abroad.
- **Cost:** GAME–FISME report: delayed payments to MSMEs **₹7.34 lakh crore as of March 2024** (down from ₹8.27 lakh crore in 2023 and ₹10.7 lakh crore in 2022), more than 4.6% of GVA. The Economic Survey 2025–26 estimates **₹8.1 lakh crore** stuck. **(search-index**, Economic Times / KNN / FISME)
- **Why an agent helps:** The same AR matching and dunning, plus deadline tracking. This sets up P11.
- **Evidence:** https://economictimes.indiatimes.com/small-biz/sme-sector/delayed-payments-to-msmes-in-india-decrease-to-rs-7-34-lakh-crore-but-challenges-persist-report/articleshow/125585516.cms · https://economictimes.indiatimes.com/small-biz/sme-sector/rs-8-1-lakh-crore-stuck-in-delayed-msme-payments-eco-survey-2026/articleshow/127765852.cms · https://fisme.org.in/study/delayed-payments-to-msmes-decline-from-rs-10-lakh-cr-to-rs-7-lakh-cr-but-challenges-persist-game-fisme-report/

## P11 · India exporters and freelancers receiving USD/EUR: cost and compliance
- **Who:** Indian service exporters (agencies, SaaS, freelancers) and goods exporters paid in USD/EUR/GBP.
- **What happens:**
  - The money arrives via a bank SWIFT (intermediary deductions + bank FX spread) or a platform (Payoneer/Wise/Skydo/Xflow) with markups or fees.
  - Each receipt needs a **FIRA/FIRC** and the correct **purpose code**, and must be matched to an invoice for GST (LUT for zero-rated export) and income tax.
  - Proceeds must be **realised within the FEMA deadline**. The RBI amendment of Sep 22, 2026 (effective Oct 1, 2026) keeps it at **9 months** but moves the clock to the invoice date for services. INR-invoiced exports get 12 months. EDPMS entries up to ₹10 lakh can be closed on declaration. **(search-index**: taxupdate.in, taxguru.in; verify on rbi.org.in)
- **Cost:** Comparison sites put platform costs at **~1.6–1.9% (Wise) + a ~$2–2.50 FIRA fee**, and **~2% FX markup** for Payoneer on direct invoices. **(search-index, vendor comparison pages: treat as unverified)** World Bank RPW: remittances to India cost **5.30%** of $200 on average. **(search-index**, secondary table built from RPW)
- **Workaround:** Spreadsheets of invoices vs credits, chasing banks for FIRCs, CAs reconciling at year-end. r/IndiaTax thread: "Indian freelancers who get paid internationally, what's your actual workflow for FIRA and taxes?" (qualitative)
- **Caveat for an Airwallex build:** Airwallex does **not** appear on RBI's PA-CB authorised list as of Sep 2026. Indian businesses reportedly onboard via Airwallex Singapore and receive into foreign-currency Global Accounts. **(search-index**, Skydo blog, a competitor) So adoption in India is uncertain. The sandbox demo is fine.
- **Evidence:** https://taxupdate.in/finance/983/fema-export-realisation-period-october-1-2026-nine-months-rbi-amendment/ · https://taxguru.in/rbi/fema-export-import-regulations-2026-key-effective-1-october.html · https://www.xflowpay.com/compare/wise-vs-payoneer · https://www.reddit.com/r/IndiaTax/comments/1tvgeuk/ · https://www.reddit.com/r/indianstartups/comments/1ufbl50/ · https://www.skydo.com/blog/airwallex-india-availability-fees

## P12 · Month-end close and cash reconciliation
- **Who:** Controllers, accountants, fractional CFOs.
- **Cost:** Ledge 2025 benchmark (100 finance professionals): **50% take 6+ business days to close** (18% 1–3 days, 32% 4–5, 23% 6–7, 27% >7). **Cash reconciliation is the #1 time sink at 20–50 hours/month, using 3–5 systems.** **94% use Excel** and 50% say it slows the close. Quote: "Cash reconciliation alone takes 30+ hours each month." **(verified)**
- **Workaround:** Exports from the bank, PSP and ERP matched by hand in Excel.
- **Why an agent helps:** When the agent *initiated* the payment, it already knows the obligation ↔ conversion ↔ payout ↔ fee linkage. It can auto-reconcile against `GET /api/v1/financial_transactions` (source types `PAYOUT`, `CONVERSION`, `FEE`, `DEPOSIT`; transaction types incl. `PAYOUT_FAILURE`, `PAYOUT_REVERSAL`) and `GET /api/v1/balances/history`, then produce a tie-out. **Airwallex explicitly names reconciliation as an unwritten kit "few builders will take on".**
- **Evidence:** https://www.ledge.co/content/month-end-close-benchmarks-for-2025 · https://www.cfo.com/news/50-of-finance-take-week-to-close-books-ledge-month-end-close-time-cfo-three-day-close-myth-/746085/ · https://airwallexdev.com/guide

## P13 · Multi-currency bookkeeping: realised FX gain/loss and clearing accounts
- **Who:** Bookkeepers for companies invoicing or paying in several currencies (Xero/QBO users).
- **What happens:** An invoice is booked at one rate and paid at another, with bank fees deducted in between. People can't figure out where the difference goes, so they "invoice everything in USD" and push FX risk onto customers.
- **Cost:** Qualitative only. r/Accounting: "invoicing in different currencies creating reconciliation mess!!! should I just invoice everything in USD?"; r/AccountingDepartment: "Need help with foreign currency bookkeeping and bank reconciliation"; r/xero multicurrency threads.
- **Why an agent helps:** It emits journal lines with booking rate vs settlement rate, a fee line and a realised FX gain/loss line per payment, in an import-ready CSV.
- **Evidence:** https://www.reddit.com/r/Accounting/comments/1rio68b/ · https://www.reddit.com/r/AccountingDepartment/comments/1v0p9bm/ · https://www.reddit.com/r/xero/comments/1sjpn88/

## P14 · Chargebacks and friendly fraud
- **Who:** Online merchants, DTC brands, SaaS.
- **Cost:** LexisNexis True Cost of Fraud 2025 (569 US/Canada execs): **US merchants incur $4.61 for every $1 of fraud** (Canada $4.52). 41% still rely on manual fraud processes. **(verified)** Chargebacks911 (a chargeback vendor, so treat as biased): merchants win ~44% of represented chargebacks but **net recovery is only 10.7%**, and 72% of cardholders see disputes as a valid alternative to refunds. **(verified on the vendor page; vendor data)** Shopify: a $15 chargeback fee, returned only if you win. **(search-index)**
- **Workaround:** Manual evidence packs, outsourced representment, or accepting everything.
- **Why an agent helps:** This is kit 4. It runs per-case economics (fee vs amount vs win probability vs deadline), assembles an evidence pack, uploads it (JPG/PDF only), escalates the ambiguous case, and never re-sends rejected evidence.
- **Evidence:** https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20250402-tcof-ecommerce-and-retail · https://chargebacks911.com/chargeback-stats/ · https://www.reddit.com/r/shopify/comments/1okb701/ · https://help.shopify.com/en/manual/payments/chargebacks/chargeback-process

## P15 · Marketplace sellers: cash held in reserves, and conversion fees on payouts
- **Who:** Amazon/marketplace sellers, especially international ones. Marketplace operators on the other side.
- **Cost:** Amazon Currency Converter for Sellers: **1.50% fee** on cross-currency payouts below $500k trailing 12-month proceeds (1.25% → 0.75% at higher tiers), on top of the provider rate. **(search-index**, Amazon program page) Seller forum and Reddit complaints about **DD+7** (funds held until 7 days after delivery) and account-level reserves squeezing cash flow. **(qualitative)**
- **Why an agent helps:** On the platform side (kit 8), per-seller risk-based reserves, recomputed only for the affected seller. On the seller side, receive in local Global Accounts and convert on schedule.
- **Evidence:** https://sell.amazon.com/programs/amazon-currency-converter · https://www.reddit.com/r/FulfillmentByAmazon/comments/1sk0uqc/ · https://sellercentral.amazon.com/seller-forums/discussions/t/508f864b-9bbc-4c38-bf6f-2c5913304009

## P16 · SaaS spend sprawl and surprise renewals
- **Who:** Startup founders and ops leads. Every employee with a company card.
- **Cost:** Zylo 2025 SaaS Management Index (40M licenses, $40B spend under management): **66.5% of IT leaders reported unexpected SaaS charges** from consumption/AI pricing. Organizations waste **$21M/yr on unused licenses** on average (enterprise-skewed). SaaS spend is **$4,830 per employee (+21.9% YoY)**. Lines of business now control 70% of SaaS spend. **(verified)**
- **Why an agent helps:** This is kit 2. One virtual card per vendor with limits and an MCC/currency allowlist enforcing the purchase decision. Auto-freeze before renewal unless someone re-approves.
- **Evidence:** https://zylo.com/news/2025-saas-management-index

## P17 · Contractor and payroll payout errors
- **Who:** Payroll operators and startups paying international contractors.
- **Cost:** EY 2022 HR processing risk and cost survey (US, 508 respondents): payroll accuracy **80.15%**, ~15 corrections per pay period, **$291 average cost per error**. **(search-index**, the Business Wire release in search) Deel ~$49/contractor/month (review site, unverified).
- **Why an agent helps:** This is kit 6. Price fees before converting, keep employer funds isolated, validate beneficiaries per corridor.
- **Evidence:** https://www.businesswire.com/news/home/20221222005093/en/EY-survey-Payroll-errors-average-%24291-each-impacting-the-economy · https://www.reddit.com/r/fintech/comments/1rvsakg/

## P18 · Small cross-border transfers are still expensive
- **Cost:** World Bank Remittance Prices Worldwide, Q3 2025: global average cost of sending $200 is **6.36%** (down from 6.49% in Q1 2025). Digital is 4.59%, non-digital 7.30%. The RPW homepage states 6.36%. **(verified via the RPW homepage text + PDF snippet)** Banks are the costliest channel at ~14.99% (secondary site built on RPW, unverified).
- **Relevance:** This is consumer remittance, not B2B. It's useful context for contractor payouts and micro-exporters, but don't pitch it as the core B2B pain.
- **Evidence:** https://remittanceprices.worldbank.org/ · https://remittanceprices.worldbank.org/sites/default/files/2026-04/RPW_main_report_and_annex_Q325.pdf

## P19 · Fintech account freezes and opaque support
- **Who:** SMBs that depend on one fintech for all their money movement.
- **Cost / signal:** Airwallex ~**3.1/5 on Trustpilot** vs ~**4.3/5 on G2** (review aggregator). Recurring complaints: sudden suspensions, funds frozen during compliance reviews, slow generic support. Payoneer ~**3.5/5 from ~62.7k Trustpilot reviews**, with complaints about blocked accounts and held funds. **(search-index**; G2, Capterra and Trustpilot block automated fetches)
- **Design implication:** An agent that moves money must be **transparent**: every action explained, logged and reversible where possible. It should also hold a reserve floor and **escalate rather than retry** when the provider returns compliance errors (e.g. `ACCOUNT_UNDER_RESTRICTION`, `TM_SUSPENDED`).
- **Evidence:** https://www.paymentprocessingguide.com/processor/airwallex/reviews · https://www.trustpilot.com/review/airwallex.com · https://www.trustpilot.com/review/www.payoneer.com

## P20 · The trust gap for agents that spend money
- **Cost / signal:** Forrester 2025: only **24%** of US online adults trust agents for routine purchases. Contentsquare: 30% would let an agent complete a purchase. A Worldpay-cited figure: **only 6% would allow automatic purchases without checking first**. **(search-index)**
- **Design implication:** Judges ask about "controlled autonomy". Approvals must be **bound to exact terms** and invalidated on any change, with tiered autonomy that is earned (e.g. auto only for known payees, unchanged bank details and amounts under a limit).
- **Evidence:** https://www.forrester.com/report/many-us-consumers-believe-in-agentic-commerce-but-few-trust-it-to-make-purchases/RES188737 · https://contentsquare.com/press/ai-is-reshaping-online-shopping/ · https://www.worldpay.com/en-GB/news/ai-agents-set-transform-how-americans-shop-261-billion-predicted

## P21 · Internal billing and expense fraud
- **Cost:** ACFE Report to the Nations 2024: organizations lose **~5% of revenue** to occupational fraud. **Billing schemes** are 22% of cases with a $100k median loss. **Expense reimbursement** schemes are 13% with a $50k median. **(search-index**, ACFE PDF linked)
- **Why an agent helps:** Segregation of duties enforced in code (the requester can't approve their own payee), anomaly flags on new vendors, and policy checks before money moves.
- **Evidence:** https://www.acfe.com/-/media/files/acfe/pdfs/rttn/2024/2024-report-to-the-nations.pdf

## P22 · Treasury catches the fraud, but tooling lags
- **Cost / signal:** AFP 2026: treasury is the department most likely to discover **attempted (83%)** and **actual (55%)** fraud. **Only 17%** of organizations use AI to fight payments fraud. Smaller firms "are much more likely to absorb the full financial loss". **(verified)**
- **Implication:** There is room for an operator-grade agent at SMB scale that does what big-company treasury does: verification, disciplined approvals, timely detection.
- **Evidence:** https://www.prnewswire.com/news-releases/over-75-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags-302738857.html

---

## Cross-cutting takeaways for the idea
1. The **costliest, most-cited, best-evidenced** pains sit around the **supplier payment run**: fraud (P1), duplicates (P2), manual AP (P3), failures (P4/P5), FX leakage (P6) and reconciliation afterwards (P12/P13).
2. These map onto **kits 1 + 3 plus the reconciliation gap** Airwallex flagged. **No special access is needed.**
3. Judges reward **operational foundation + controlled autonomy**. Approval binding, idempotency, a finality-aware state machine and a reconciliation tie-out *are* that foundation.
4. India exporters (P10/P11) are a strong secondary market, but Airwallex's India licensing status is a real adoption risk. That makes it a runner-up, not the winner.

---

# 02 · Idea Board (all greenfield)

**Constraint:** every idea here is a fresh build. None reuses, extends or references any of Vedant's earlier projects. Generic "chat with your balance" bots are excluded on purpose. The hosts already ship one (the AI finance manager reference build).

## How ideas were scored (1–5, higher is better)
| Criterion | Meaning | Weight |
|---|---|---|
| **Pain** | Severity and frequency of the operator pain, backed by cited numbers in `01` | ×2 |
| **X-mkt/ccy** | Works across markets and currencies by design (a judge signal) | ×1 |
| **Adoption** | A credible path from prototype to a real customer using it (a judge signal) | ×1.5 |
| **Ops depth** | Operational foundation: state machines, idempotency, ledger, reconciliation (a judge signal) | ×1.5 |
| **Ctrl autonomy** | Agent decides and moves money, with human approval bound to consequential actions (a judge signal) | ×1.5 |
| **Demo 3wk solo** | Can one person with coding agents ship a convincing, honest demo by Nov 13 | ×2 |
| **Visa/Metal** | Plausible eligibility for the $15k Visa or Metal award (5 = clearly eligible) | ×0.5 |
| **Access (5 = none)** | 5 = sandbox only. 1 = blocked on allowlist or a draft API | ×2 |

Weights favour things that win "open" prizes (Founder's / Judges' Choice, $50k combined) and things a solo builder can control. The Visa/Metal criterion is down-weighted because both awards need partner tooling whose bar isn't defined.

## The ideas
| ID | Name | What it does | Pains (see 01) | Starter kit |
|---|---|---|---|---|
| A | **Countersign** | Cross-border supplier payment-run agent: fraud/duplicate gate → FX-aware plan → bound approvals → idempotent execution → failure recovery → reconciliation tie-out | P1,P2,P3,P4,P5,P6,P12,P13 | 1 + 3 + reconciliation gap |
| B | **Realize** | Receivables agent for exporters (India-first): match USD/EUR/GBP Global Account deposits to invoices, track FEMA 9-month realisation clocks, decide when to convert, draft dunning and FIRA/purpose-code packs | P9,P10,P11,P6,P13 | Custom (Global Accounts, deposits, FX) |
| C | **Rebuttal** | Chargeback economics desk: per-case EV (fee vs amount vs win odds vs deadline), evidence-pack builder, accept/challenge/escalate, handles rejected evidence | P14 | 4 |
| D | **Runway Triage** | Shortfall treasury controller: rank obligations vs reserve floor, autonomy limit tied to forecast confidence, recalc only affected decisions on deposit | P8,P6,P7 | 1 |
| E | **Renewal Sentinel** | SaaS commitment agent: monthly vs annual decision against cash, one virtual card per vendor whose controls enforce it, auto-freeze before renewal unless re-approved | P16,P21 | 2 |
| F | **Closebook FX** | Multi-currency close agent: pull financial_transactions + balance history, match to ledger, compute realised FX gain/loss, explain breaks, export journals | P12,P13 | Reconciliation gap (no kit) |
| G | **Discount Harvester** | Early-payment discount optimizer: take 2/10-net-30 style supplier discounts across currencies only when the reserve floor and FX cost allow | P8,P6 | 1 (variant) |
| H | **Ledgerfair Payroll** | Multi-employer contractor payroll with hard tenant isolation, fee-aware conversion, per-corridor beneficiary validation | P17,P4 | 6 |
| I | **Reserve Sentinel** | Marketplace settlement: risk-based seller reserves, net payouts, re-reserve one seller on carrier-failure evidence, recover shortfall | P15,P14 | 8 |
| J | **Bridgekeeper** | Card-issuing platform that rations scarce bridge capital across late-funding customers under a reserve floor | P8 | 5 |
| K | **Mandate Cart (+Visa TAP)** | Approval-bound shopping agent that signs merchant requests with Visa Trusted Agent Protocol and re-asks on any term change; pays via Airi CLI | P20 | 9 + Visa TAP |
| L | **Stablecoin Settlement on Metal** | Exporter receives USDC on Metal L2 testnet; agent decides hold vs off-ramp, then pays suppliers via Airwallex | P11,P6 | Custom + Metal |
| M | **Agent-Ready Storefront** | Merchant catalogue exposed to Claude via merchant MCP with approval-bound test checkout | P20 | 10 |
## Scores
| Rank | ID | Idea | Pain | X-mkt/ccy | Adoption | Ops depth | Ctrl autonomy | Demo 3wk solo | Visa/Metal | Access (5=none) | Raw /40 | Weighted /60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A | **Countersign** | 5 | 5 | 4 | 5 | 5 | 4 | 3 | 5 | 36 | **55.5** |
| 2 | D | **Runway Triage** | 4 | 5 | 3 | 4 | 5 | 5 | 1 | 5 | 32 | **51.5** |
| 3 | C | **Rebuttal** | 4 | 3 | 4 | 4 | 4 | 5 | 2 | 5 | 31 | **50** |
| 4 | F | **Closebook FX** | 5 | 5 | 4 | 5 | 3 | 3 | 2 | 5 | 32 | **50** |
| 5 | B | **Realize** | 4 | 5 | 3 | 4 | 4 | 4 | 2 | 5 | 31 | **48.5** |
| 6 | E | **Renewal Sentinel** | 3 | 3 | 4 | 3 | 4 | 5 | 2 | 5 | 29 | **46.5** |
| 7 | G | **Discount Harvester** | 3 | 4 | 3 | 4 | 4 | 4 | 1 | 5 | 28 | **45** |
| 8 | H | **Ledgerfair Payroll** | 4 | 5 | 4 | 5 | 4 | 3 | 1 | 2 | 28 | **43** |
| 9 | I | **Reserve Sentinel** | 4 | 3 | 3 | 5 | 4 | 3 | 1 | 2 | 25 | **39.5** |
| 10 | K | **Mandate Cart (+Visa TAP)** | 3 | 3 | 3 | 3 | 5 | 4 | 5 | 1 | 27 | **38** |
| 11 | J | **Bridgekeeper** | 3 | 3 | 3 | 4 | 4 | 3 | 2 | 2 | 24 | **36.5** |
| 12 | L | **Stablecoin Settlement on Metal** | 2 | 4 | 2 | 3 | 3 | 3 | 5 | 3 | 25 | **34.5** |
| 13 | M | **Agent-Ready Storefront** | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 1 | 22 | **33** |
## Notes per idea (why each score)
- **A · Countersign.** It goes after the best-evidenced money pains: BEC (74% of orgs), 1.5% duplicate/erroneous disbursements, $9.84/invoice, $1.6B/yr investigations, £2.8bn hidden FX, 20–50 hrs/month cash rec. It combines kits 1 and 3 with the reconciliation gap Airwallex says few builders will take. It needs no special access. It is demo-able because sandbox simulations cover every beat: deposit, FX, transfer SENT/PAID/FAILED with `failure_type`. Demo is 4, not 5, because the scope is broad and must be cut hard (see `03` §12). Visa/Metal is 3 because a Metal L2 testnet anchor for the approval/audit log is cheap and plausible, but eligibility is unconfirmed. Visa is weak.
- **D · Runway Triage.** A clean kit 1 with very high demo-ability. It is a near-verbatim starter kit, though, so many teams will submit it, and its planner is already a module inside Countersign. Adoption is 3 because "cash short this week" tooling is episodic.
- **C · Rebuttal.** The safest fallback: kit 4, no wallet funding even needed, crisp economics. The domain is crowded with chargeback vendors (Chargebacks911, Chargeflow, Justt), and it is mostly single-currency, so X-mkt is 3.
- **F · Closebook FX.** It hits the reconciliation gap squarely and the pain is real (verified Ledge data). It moves little money, though, so the "agent moves money" signal is weak, and reconciliation is hard to make visually exciting in 5 minutes. Its core is absorbed into Countersign's reconcile step.
- **B · Realize.** It is differentiated (India exporters, FEMA clocks, FIRA/purpose codes) and very cross-currency. Adoption is 3 because Airwallex is not on RBI's PA-CB list (search-index) and Indian businesses onboard via Singapore. Judges in SF may find the regulatory detail niche.
- **E · Renewal Sentinel.** Easy and visual, but too close to the hosts' own reference builds (Agent cards, Allocard).
- **G · Discount Harvester.** A nice treasury lever, but thin on its own. It becomes a planner feature in Countersign (stretch).
- **H / I / J · Platform kits (6 / 8 / 5).** Excellent operational depth, but blocked on "request platform access" (connected accounts + platform payments), with an unknown turnaround. Only pursue if access is granted by ~Oct 20.
- **K · Mandate Cart + Visa TAP.** The best Visa-award fit (TAP is open source, RFC 9421 signatures). It is blocked on the Airi CLI allowlist and spends real money on real merchants, so it is very risky solo.
- **L · Stablecoin settlement on Metal.** Clearly Metal-eligible, but the Airwallex side is weak: stablecoin payouts need account-manager enablement and only support USDC on Ethereum per the docs. B2B pain evidence is thin.
- **M · Agent-Ready Storefront.** The Merchant Onboarding API is a draft, not deployed. Do not bet a solo build on it.

## Recommendation

### Winner: **A · Countersign**
*"The cross-border supplier payment run, done by an agent that never pays twice, never pays a fraudster, and proves every payment landed. A human countersigns anything that matters."*

Why it wins:
1. **Strongest evidence base.** Six of the top-cited pains converge on one weekly workflow.
2. **Hits all five judge signals at once.** Real operator pain. Multi-currency by construction: netting, LOCAL vs SWIFT, FX quotes. Adoption path: it runs on a company's existing Airwallex account and exports to its existing ledger, with a shadow mode first. Operational foundation: ledger, idempotency, finality-aware state machine, reconciliation. Controlled autonomy: tiered autonomy with approvals bound to exact terms.
3. **Uses the territory the hosts flagged** (reconciliation) while staying inside zero-access kits.
4. **Clear "decision changes when information changes" beats** for the demo: a bank-detail change, a duplicate, an FX shortfall, a deposit arriving, a transfer failing after looking final.

### Runner-up #1: **C · Rebuttal**: the lowest-risk pivot
Choose this if the Countersign scope proves too big by ~Nov 1 or if sandbox payouts misbehave. Kit 4 needs **no enablement and no wallet funding**, the economics are crisp, and the sandbox supports the full dispute lifecycle including rejection. Make it stand out with **per-case expected value**, a strict "never re-submit rejected evidence" rule, and multi-currency merchant settlement (disputes in USD/EUR/GBP and the fee in the merchant's currency).

### Runner-up #2: **B · Realize**: the differentiated, India-first pivot
Choose this if Vedant wants a story nobody else in the room will tell. It is built around real Indian regulatory clocks (FEMA 9-month realisation from invoice date, effective Oct 1, 2026), FIRA/purpose-code packs and conversion timing on Global Account receipts. Risk: Airwallex India availability (onboarding via Singapore; not on the PA-CB list), so pitch it as "exporters in any market with realisation rules" with India as the first locale.

**Why not Runway Triage (#2 by raw score)?** It is a near-verbatim starter kit (crowded), and its core planner already lives inside Countersign. A runner-up should be a *different* fallback, not a subset of the winner.

### Optional prize add-ons (only after the core works)
- **Metal:** anchor a hash-chain of approvals and payment receipts to **Metal L2 testnet** (free faucets, so no card). That gives a tamper-evident audit trail for auditors. Confirm eligibility in Metal's Slack first.
- **Visa:** no honest fit inside Countersign without VIC access. Don't contort the product for it.

---

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

---

# 04 · Sources

Accessed **Oct 8, 2026 (IST)**. Labels:
- **[V]** = page or PDF opened and the content seen.
- **[S]** = known from search-index results or snippets only; the page was blocked, errored, or not opened.
- **[Q]** = qualitative (forum or Reddit), cited for sentiment only. Reddit blocked direct fetches with HTTP 403.

## Hackathon (official)
- [V] HackerEarth challenge page (phases, team size, registrations, generic FAQ): https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/
- [V] Same page, canonical URL: https://www.hackerearth.com/challenges/hackathon/agentic-banking-hackathon/
- [S] Registration / idea form (login required, fields not visible): https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/?register=true
- [V] Landing page (tracks, key dates, prizes, partners, FAQ): https://airwallex.hackerearth.com/
- [V] Landing "About" image (48 hours / 3 weeks / 12 tracks): https://uc.hackerearth.com/he-s3-ap-south-1/media/sprint/agentic-banking-hackathon/editor/editor_image_2733610_62fda2e.png
- [V] Builder guide (kits, access, conventions, sandbox constraints): https://airwallexdev.com/guide
- [V] Developer lab home (MCP configs, webhooks, simulation notes): https://airwallexdev.com/
- [V] Builds page + JSON (reference builds, agent recipes): https://airwallexdev.com/builds · https://airwallexdev.com/content/builds.json · https://airwallexdev.com/content/library.json
- [S] Reference build repos: https://github.com/awx-devx/airwallex-agent-cards · https://github.com/awx-devx/awx-drop-in-checkout · https://github.com/awx-devx/airwallex-slack-bot · https://github.com/awx-devx/airwallex-finance-manager · https://github.com/awx-devx/airwallex-allocard
- [S] Dan Kim (Airwallex) launch post (partners, prize split): https://nitter.cf/dankimxyz/status/2107146234020684187
- [S] Dan Kim LinkedIn, Sep 24, 2026 ("$70k, up from $50k"): https://www.linkedin.com/posts/danieljkim_the-airwallex-agentic-banking-hackathon-will-activity-7508933085132922880-HNRC
- [S] Third-party summary: https://devgrantsdaily.com/items/2026-10-06-airwallex-agentic-banking-hackathon/

## Judge signals
- [S] Sam Waldo, "Judging the Agents, Everywhere hackathon" (criteria): https://www.linkedin.com/posts/sam-waldo_judging-the-agents-everywhere-hackathon-activity-7500783609373462528-jCSr
- [S] AI Tinkerers Singapore post (5 judge questions): https://www.linkedin.com/posts/ai-tinkerers-singapore_what-happens-when-ai-agents-move-beyond-conversationand-activity-7500499794403049472-36H9
- [S] Sam Waldo recap (favourite: invoice agent with explicit human approval): https://www.linkedin.com/posts/sam-waldo_aitinkerers-agentseverywhere-agentos-activity-7506525100737929216-Jhgg

## Airwallex docs (via the public Docs MCP `https://mcp.sandbox.airwallex.com/docs`, tool `search_public_docs`) [V]
- Financial transactions (list): https://www.airwallex.com/docs/api/finance/financial_transactions/list.md
- Transfers (retrieve, list, statuses incl. late failure after PAID): https://www.airwallex.com/docs/api/payouts/transfers.md · https://www.airwallex.com/docs/payouts/transfers/create-a-transfer/transfer-statuses.md · https://www.airwallex.com/docs/payouts/transfers/manage-transfers/handle-failed-transfers.md
- Transfer simulation (failure_type values): POST /api/v1/simulation/transfers/{id}/transition
- Transfer webhooks: https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events/transfers.md
- Beneficiaries (create, list, update, validate, verify_account, schemas): https://www.airwallex.com/docs/api/payouts/beneficiaries/verify_account.md and siblings
- Balance history: https://www.airwallex.com/docs/api/core_resources/balances/history.md
- FX quotes (validity options, valid_to_at): https://www.airwallex.com/docs/api/transactional_fx/quotes/create.md
- Financial reports (TRANSACTION_RECON_REPORT): POST /api/v1/finance/financial_reports/create
- Stablecoin payouts (USDC on Ethereum, account-manager enablement): https://www.airwallex.com/docs/payouts/payout-network/stablecoin-wallets.md
- API intro / sandbox / AgentOS / Postman / webhooks: https://www.airwallex.com/docs/api/introduction · https://www.airwallex.com/docs/developer-tools/sandbox-environment · https://www.airwallex.com/docs/developer-tools/ai/agentos · https://www.airwallex.com/docs/developer-tools/api/quickstart-with-postman · https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events

## Partner tooling
- [S] Visa Intelligent Commerce: https://developer.visa.com/capabilities/visa-intelligent-commerce
- [S] Visa Trusted Agent Protocol docs/spec: https://developer.visa.com/capabilities/trusted-agent-protocol/docs · https://developer.visa.com/capabilities/trusted-agent-protocol/trusted-agent-protocol-specifications/
- [S] TAP sample implementation: https://github.com/visa/trusted-agent-protocol
- [S] VIC on Visa Acceptance prerequisites (MID, token requester ID, relationship ID): https://developer.visaacceptance.com/docs/vas/en-us/intelligent-commerce/developer/all/rest/intelligent-commerce/intelligent-commerce-intro-requirements.html
- [V] Metal L2 testnet faucets: https://docs.metall2.com/builders/tools/build/faucets
- [S] Metal L2 tools / Metal Blockchain / Metallicus developers: https://docs.metall2.com/builders/tools · https://metallicus.com/developers/metal-blockchain · https://metalblockchain.org/ · https://metallicus.com/developers

## Pain evidence (see 01 for how each is used)
- [V] AFP 2026 Payments Fraud & Control (BEC 74%, AI 17%, treasury detects 83%): https://www.prnewswire.com/news-releases/over-75-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags-302738857.html
- [V] AFP 2025 press release (79% fraud, BEC 63%, vendor imposter 45%, wires 63%): https://www.financialprofessionals.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024
- [S] AFP 2025 full report PDF: https://7185359.fs1.hubspotusercontent-na1.net/hubfs/7185359/Research%20Surveys/SURVEYS/2025%20Payments%20Fraud%20and%20Control%20Survey%20Report%20Comprehensive.pdf
- [S] FBI IC3 2024 report (BEC $2.77B): https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf · https://www.fbi.gov/news/press-releases/fbi-releases-annual-internet-crime-report
- [V] APQC duplicate/erroneous payments median 1.5%: https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number
- [S] CFO.com metric of the month (duplicates): https://www.cfo.com/news/metric-of-the-month-detect-and-prevent-duplicate-or-erroneous-payments/656852/
- [V] Ardent Partners State of ePayables 2025 ($9.84, 8.2 days): https://www.bottomline.com/cdn/1517/5157/1685/Ardent_Partners_-_State_of_ePayables_2025_-_Bottomline_-_FINAL.pdf
- [S] LexisNexis/Accuity failed payments $118.5B: https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20210714-true-cost-of-failed-payments
- [V] Swift investigations $1.6B/yr, 5–10 working days: https://www.swift.com/news-events/press-releases/swift-solution-managing-cross-border-payments-investigations-could-save-industry-millions-operational-costs
- [S] Swift exceptions & investigations paper: https://www.swift.com/sites/default/files/files/its-time-to-transform-exceptions-and-investigations-april2025.pdf
- [S] BNY payment investigations: https://www.bny.com/corporate/global/en/insights/payment-investigations-from-evolution-to-revolution.html
- [V] Wise / Capital Economics £2.8bn hidden fees: https://wise.com/imaginary-v2/images/3377a6584910ba4ef7b4225eb5bff069-Wise%20%E2%80%94%20End%20the%20Opt%20Out%20Campaign.pdf
- [S] UK £4bn SME FX fees (Accourt): https://www.leaprate.com/news/sme-international-forex-transfers-generate-4-billion-in-hidden-uk-bank-fees-accourt/
- [S] Bibby Financial Services 2025 international trade report: https://www.bibbyfinancialservices.com/assets/documents/bltcaabb0e00358b2d2/blte04864e15d01ca6f/trading-places-bfs-international-trade-report-2025.pdf · https://www.leasinglife.com/news/uk-smes-count-cost-of-currency-volatility-average-53k-lost-in-2025/
- [S] Corpay Economic Outlook 2025: https://assets.ctfassets.net/h83dujey17us/4VayZIHNOpKZb4Xm3Aagv8/cdc4c33998f24c09bdccac615156fdf5/Economic_Outlook_Survey_2025.pdf
- [S] MillTechFX hedging: https://tradetreasurypayments.com/articles/81-of-corporates-now-hedging-fx-risk-new-milltechfx-data-shows
- [S] AFP 2025 Treasury Benchmarking (forecasting 62%): https://7185359.fs1.hubspotusercontent-na1.net/hubfs/7185359/Research%20Surveys/SURVEYS/2025%20AFP%20Treasury%20Benchmarking%20Survey%20Comprehensive%20Report.pdf
- [V] Atradius Payment Practices Barometer W. Europe 2025: https://group.atradius.com/dam/jcr:80448207-97e5-4005-98b5-d5bb90e7107d/payment-practices-barometer-western-europe-2025-en.pdf
- [S] Intuit QuickBooks 2025 late payments report (page returned HTTP 500): https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2025/
- [S] India MSME delayed payments: https://economictimes.indiatimes.com/small-biz/sme-sector/delayed-payments-to-msmes-in-india-decrease-to-rs-7-34-lakh-crore-but-challenges-persist-report/articleshow/125585516.cms · https://economictimes.indiatimes.com/small-biz/sme-sector/rs-8-1-lakh-crore-stuck-in-delayed-msme-payments-eco-survey-2026/articleshow/127765852.cms · https://fisme.org.in/study/delayed-payments-to-msmes-decline-from-rs-10-lakh-cr-to-rs-7-lakh-cr-but-challenges-persist-game-fisme-report/
- [S] FEMA export realisation (RBI amendment, effective Oct 1, 2026): https://taxupdate.in/finance/983/fema-export-realisation-period-october-1-2026-nine-months-rbi-amendment/ · https://taxguru.in/rbi/fema-export-import-regulations-2026-key-effective-1-october.html · https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12908&Mode=0
- [S] India inbound payment cost comparisons (vendor pages): https://www.xflowpay.com/compare/wise-vs-payoneer · https://www.indietoolkit.in/blog/how-to-accept-international-payments-indian-freelancer
- [S] Airwallex India availability (competitor blog): https://www.skydo.com/blog/airwallex-india-availability-fees
- [S] GST on foreign SaaS (reverse charge, forex markup): https://taxguru.in/goods-and-service-tax/foreign-software-subscriptions-attract-gst-reverse-charge-itc.html
- [V] Ledge month-end close benchmarks 2025: https://www.ledge.co/content/month-end-close-benchmarks-for-2025
- [S] CFO.com on Ledge: https://www.cfo.com/news/50-of-finance-take-week-to-close-books-ledge-month-end-close-time-cfo-three-day-close-myth-/746085/
- [V] LexisNexis True Cost of Fraud 2025 ($4.61): https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20250402-tcof-ecommerce-and-retail
- [V] Chargebacks911 stats (vendor): https://chargebacks911.com/chargeback-stats/
- [S] Shopify chargeback process: https://help.shopify.com/en/manual/payments/chargebacks/chargeback-process
- [S] Amazon Currency Converter for Sellers: https://sell.amazon.com/programs/amazon-currency-converter
- [Q] Amazon seller forums on DD+7: https://sellercentral.amazon.com/seller-forums/discussions/t/508f864b-9bbc-4c38-bf6f-2c5913304009
- [V] Zylo 2025 SaaS Management Index: https://zylo.com/news/2025-saas-management-index
- [S] EY payroll errors $291: https://www.businesswire.com/news/home/20221222005093/en/EY-survey-Payroll-errors-average-%24291-each-impacting-the-economy
- [V]/[S] World Bank Remittance Prices Worldwide (6.36% Q3 2025): https://remittanceprices.worldbank.org/ · https://remittanceprices.worldbank.org/sites/default/files/2026-04/RPW_main_report_and_annex_Q325.pdf
- [S] Secondary RPW table (by country/channel): https://arcawallet.app/research/true-cost-of-sending-200-by-country/
- [S] Airwallex / Payoneer reviews: https://www.paymentprocessingguide.com/processor/airwallex/reviews · https://www.trustpilot.com/review/airwallex.com · https://www.trustpilot.com/review/www.payoneer.com · https://statrys.com/reviews/payoneer-business-account
- [S] Ramp vs Brex international limits: https://www.airwallex.com/en-us/blog/ramp-vs-brex-comparison · https://www.g2.com/compare/brex-vs-ramp-financial-ramp
- [S] Agentic commerce trust: https://www.forrester.com/report/many-us-consumers-believe-in-agentic-commerce-but-few-trust-it-to-make-purchases/RES188737 · https://contentsquare.com/press/ai-is-reshaping-online-shopping/ · https://www.worldpay.com/en-GB/news/ai-agents-set-transform-how-americans-shop-261-billion-predicted · https://www.americanbanker.com/payments/news/consumers-are-warming-up-to-agentic-payments
- [S] ACFE Report to the Nations 2024: https://www.acfe.com/-/media/files/acfe/pdfs/rttn/2024/2024-report-to-the-nations.pdf
- [S] Stripe Connect risk/reserves (marketplace context): https://docs.stripe.com/connect/risk-management · https://docs.stripe.com/connect/marketplace/tasks/refunds-disputes

## Reddit / forums (qualitative, [Q])
- https://www.reddit.com/r/IndiaTax/comments/1tvgeuk/indian_freelancers_who_get_paid_internationally/
- https://www.reddit.com/r/indianstartups/comments/1ufbl50/best_way_to_receive_international_client_payments/
- https://www.reddit.com/r/FreelanceIndia/comments/1vp1b6n/receiving_international_payments_as_a_freelancer/
- https://www.reddit.com/r/Accounting/comments/1rio68b/invoicing_in_different_currencies_creating/
- https://www.reddit.com/r/AccountingDepartment/comments/1v0p9bm/need_help_with_foreign_currency_bookkeeping_and/
- https://www.reddit.com/r/xero/comments/1sjpn88/question_on_multicurrency_support_for_real_xero/
- https://www.reddit.com/r/FulfillmentByAmazon/comments/1sk0uqc/am_i_bugged_or_is_everyone_really_chill_about/
- https://www.reddit.com/r/Banking/comments/1u2xjdl/
- https://www.reddit.com/r/shopify/comments/1okb701/we_need_to_talk_about_chargebacks_this_system_is/
- https://www.reddit.com/r/shopify/comments/1uv9vpb/when_you_win_a_shopify_chargeback_what_evidence/
- https://www.reddit.com/r/ecommerce/comments/1v5d7ty/were_paying_fx_on_every_transaction_to_our_china/
- https://www.reddit.com/r/ecommerce/comments/1vcf4x2/how_do_you_pay_chinese_vendors_who_only_have_a/
- https://www.reddit.com/r/fintech/comments/1rvsakg/cheapest_way_to_pay_contractors_in_8_countries/
- https://www.reddit.com/r/smallbusiness/comments/warxpa/dont_use_wise_transferwise_for_money_transfers/
- https://community.shopify.com/t/charge-back-on-an-item-successfully-delivered-with-tracking-evidence/347448

## Raw captures (in `raw/` inside this folder)
HackerEarth HTML + decoded flight data (`he_flight.txt`), landing HTML, airwallexdev builds/library JSON, Docs MCP query outputs (`doc_*.txt`), and PDF text extractions (Ardent, Wise, Atradius).
