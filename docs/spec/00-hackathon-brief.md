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
