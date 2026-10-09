# Round 0: AB Senior Dev (hands-on builder)

Written 2026-10-08 IST. Sources: the live [hackathon page](https://airwallex.hackerearth.com/), the [HackerEarth challenge page](https://www.hackerearth.com/challenges/hackathon/agentic-banking-hackathon/) (checked against `raw/he.html`), the [builder guide](https://airwallexdev.com/guide), and the public Airwallex docs MCP (`https://mcp.sandbox.airwallex.com/docs`, queried directly).

## Dates (IST = UTC+5:30)
| Milestone | Source time | IST |
|---|---|---|
| Registration & Idea Phase | Oct 5 15:30 UTC → **Oct 23 18:29 UTC** (HackerEarth) | Oct 5 9:00 PM → **Oct 23 11:59 PM IST** ✅ matches orchestrator |
| Build Phase | Oct 25 04:30 UTC → Nov 13 18:29 UTC | Oct 25 10:00 AM → **Nov 13 11:59 PM IST** (submissions due) |
| Finalists selected | Nov 15 (no time given) | Nov 15 / 16 IST |
| Demo Day, San Francisco (remote optional) | Nov 19 (no time given) | probably the night of Nov 19 or early Nov 20 IST, if it runs in PT |

- **Submission:** "a working demo, a short video walkthrough under five minutes, and a link to your repository with setup instructions" ([landing FAQ](https://airwallex.hackerearth.com/)). The HackerEarth FAQ adds a tar/zip with source plus run instructions, and says "all code needs to be in public domain (open source) so that it can be evaluated by the judges."
- **Teams and prizes:** teams of 1–4. Founder's Choice ($30K) and Judges Choice ($20K) are open categories. The Visa Award ($15K) requires Visa plus Airwallex tooling, and the Metal Award ($15K) requires Metal plus Airwallex tooling.
- **⚠️ No judging criteria are published** on the landing page or on HackerEarth (checked live). So I scored against two stand-ins: **(A)** the guide's own bar, ["Build around a financial decision"](https://airwallexdev.com/guide), and **(B)** the 5 questions that Airwallex's Head of Startups Asia, Sam Waldo, posted as his judging lens for a *different* Airwallex-backed hackathon ([LinkedIn, Sep 2026](https://www.linkedin.com/posts/ai-tinkerers-singapore_what-happens-when-ai-agents-move-beyond-conversationand-activity-7500499794403049472-36H9)). (B) is only a proxy.

## 1. Top 3 operator pains (cited)
1. **Cash reconciliation takes the most time in the close.** It averages **20–50 hours/month across 3–5 systems**, and **50% of teams take 6+ business days to close** ([Ledge 2025 benchmarks](https://www.ledge.co/content/month-end-close-benchmarks-for-2025), n=100). The blockers they name are "missing payment details, mismatched amounts."
2. **Cash application is mostly exceptions.** **70%** of companies get straight-through processing on 50% of payments or fewer. **58%** cite deductions/disputes/exceptions, **55%** missing remittance info, and **46%** cash left unapplied too long ([BILL × Treasury Webinars survey, Jan 2026, n=211](https://www.bill.com/blog/cash-application-metrics)).
3. **Cross-border receipts arrive late and short.** Cross-border DSO is **32 days vs 21 domestic (55% longer)**. Correspondent fees and FX swings are each a concern for **42% of US / 41% of UK** businesses receiving payments, and remittance data is lacking for about a third of mid-size firms ([PYMNTS × Visa, n=456](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/48327/pymnts-innovating-cross-border-payments-what-us-and-uk-businesse.523e2320521f.pdf)). On top of that, **43% (US) / 47% (W. Europe) / 44% (Asia)** of B2B invoices are overdue ([Atradius 2025 US](https://group.atradius.com/dam/jcr:5609b617-ac29-4e30-8b01-0663a01d94bd/payment-practices-barometer-us-2025-en.pdf), [W. Europe](https://group.atradius.com/dam/jcr:80448207-97e5-4005-98b5-d5bb90e7107d/payment-practices-barometer-western-europe-2025-en.pdf), [Asia](https://atradius.at/dam/jcr:de5379ba-2ad5-415f-9c77-6e6c2669d13e/payment-practices-barometer-asia-2025-en.pdf)).

## 2. The idea I'd back: **"Inbound": a cross-border cash-application agent**
**One line:** each B2B customer pays into its own Airwallex Global Account. When money lands, the agent matches it to open invoices, then *acts* on every exception. It writes off fee short-pays within tolerance, chases real short-pays, refunds or credits duplicates and overpayments, decides whether to hold or convert foreign-currency receipts, and reopens invoices when a deposit is reversed. Every money move is bound to policy code and human approval.

**Why this lane:** the guide says outright that *"Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them. Good territory if you want a problem few other builders will take on."* Most teams will clone kits 1–10. This one has no kit and is native to Airwallex, because per-payer Global Accounts are the matching key.

**Demo beats** (the guide's required arc: goal → plan → new info → revised decision → resulting state):
1. Goal: "close this week's receivables." There are 9 open invoices in USD, EUR and GBP. Simulated deposits land in 4 customer Global Accounts.
2. Initial plan: 5 auto-matches. A **USD 49,975 receipt against a USD 50,000 invoice** (SHA intermediary fee) is under the fee tolerance in policy code, so it is applied, the difference is written off, and the invoice is marked paid. A EUR receipt is held because a EUR supplier bill is due in 10 days (natural hedge).
3. New info: the customer's remittance email (unstructured; the LLM parses it) says the payment covers invoices 1041 + 1043 net of a credit note. The agent re-allocates. A second deposit of the same amount from the same payer is flagged as a duplicate.
4. Revised decision: refund the duplicate. It is above the auto limit, so an approval card goes out, bound to amount, currency, beneficiary and evidence. On approval, the agent sends a transfer under a duplicate lock. Separately it converts only the *surplus* EUR to USD (quote, then conversion).
5. Twist: a `deposit.reversed` event arrives on an applied deposit. The agent reopens the invoice, reverses the write-off and escalates. It ends on balances plus a reconciled ledger: applied, unapplied, written off, refunded.

**Scored against the stand-in criteria:**
- **(A) Guide: "choose differently when a balance, deadline, piece of evidence, or risk changes".** Evidence (the remittance email), risk (the reversal) and balance (EUR surplus vs upcoming bill) each change a decision on screen.
- **(A) "Let the agent move money or update financial state… state which actions require approval".** It does refund transfers, FX conversion, and invoice mark-paid or reopen. Auto vs approval thresholds live in code.
- **(A) "Keep amounts, limits… duplicate protection, and state transitions in code; use the model to read unstructured text".** Matching tolerances, write-off limits and refund locks are deterministic. The LLM only parses remittance advice and explains exceptions.
- **(B) "Genuine problem for founders or operators?"** Yes, pains 1–2 above: 58% exceptions, 20–50 h/month.
- **(B) "Work across markets, currencies?"** Built on multi-currency Global Accounts (US/GB/EU local details), SHA fee short-pays and the FX hold-vs-convert call.
- **(B) "Credible path to adoption?"** Small cross-border sellers already receive into Airwallex Global Accounts, so the agent sits on rails they have, with no new bank.
- **(B) "Operational foundation, not only the interface?"** A ledger with an append-only event log, webhook dedupe, idempotent request_ids and a reconciliation invariant check every cycle.
- **(B) "Autonomous execution with appropriate control?"** It auto-applies inside tolerance, needs approval for refunds and write-offs above a limit, and escalates on reversal.

## 3. Hands-on read
**Base URL:** `https://api.sandbox.airwallex.com/api/v1/...` (guide). Older docs and the Node SDK call this env `demo` (`api-demo.airwallex.com`). Use what the guide says.

**Auth flow (verified in guide + docs MCP):** `POST /api/v1/authentication/login` with headers `x-client-id` and `x-api-key` and no body. It returns `{token, expires_at}`, and the token is valid for **30 min**. Send `Authorization: Bearer <token>` on every call, cache the token and refresh it from `expires_at` rather than logging in on every request. A scoped key with access to several accounts needs `x-login-as`. `x-on-behalf-of: acct_…` applies only to platform or connected-account flows, which we don't need. Leave `x-api-version` off FX calls. Credentials come from sandbox.airwallex.com → Account > Developer > API keys.

**Endpoints I'd hit first, in this order:**
| Purpose | Call |
|---|---|
| Customer receiving accounts | `GET /global_accounts`, `POST /global_accounts/create` (`country_code` US/GB/NL + `required_features`) |
| Simulate receipts | `POST /simulation/deposit/create` (`global_account_id`, `amount` in **major units**, optional `payer_name`, `payer_bankname`, `payer_country`; no reference field) |
| Read receipts | `GET /global_accounts/{id}/transactions` (amount, fee_amount, payer_name, status), `GET /financial_transactions` (filter `source_id`/`currency`, has `fee`, `net`) |
| Balances | `GET /balances/current` |
| Invoices (optional mirror) | `POST /billing/invoices/create`, `POST /billing/invoices/{id}/mark_as_paid` |
| FX hold-vs-convert | `GET /fx/rates/current` → `POST /fx/quotes/create` → `POST /fx/conversions/create` (REST only, no MCP tool; quote is single-use) |
| Refund duplicates | `POST /beneficiaries/schema` → `POST /beneficiaries/validate` → `/beneficiaries/create` → `POST /transfers/create` (`transfer_currency`/`transfer_amount`, LOCAL or SWIFT) → `POST /simulation/transfers/{id}/transition` |
| Events | Webhooks `deposit.settled` / `deposit.pending` / `deposit.rejected` / `deposit.reversed` (`ga.new` on API versions ≤2025-02-14), plus `payout.transfer.paid` / `failed`. Subscribe in the web app (Settings > Developer > Webhooks). Verify HMAC-SHA256 of `x-timestamp` + raw body with the secret against `x-signature`, dedupe on event id, return 200 fast. |

**Sandbox gotchas to build around (from the guide):**
- New `request_id` (UUID) per operation, reused only for retries. Reusing one within 7 days gives `duplicate_request_id`.
- A failed transfer ends in `CANCELLED`, not FAILED. Read `failure_type`.
- Each SWIFT payout costs a flat EUR 12.85.
- Rate limit is 20 rps global, 10 per endpoint.
- Business name must be `New Business Sandbox` or `Sandbox Business` to auto-pass KYB.

**SDKs and tooling:**
- Official [`@airwallex/node-sdk@beta`](https://www.airwallex.com/docs/developer-tools/sdks/server-side-sdks-(beta)), TypeScript, with token refresh and retries. It is the *only* official server SDK, so no official Java or Python.
- [Airwallex.js](https://www.airwallex.com/docs/developer-tools/sdks) browser elements; we don't need them.
- Hosted MCP servers: **Docs** `https://mcp.sandbox.airwallex.com/docs` (public; I confirmed it answers `search_public_docs`) and **Developer** `https://mcp.sandbox.airwallex.com/developer` (needs sandbox login; cannot create Global Accounts or book FX).
- [AgentOS](https://www.airwallex.com/docs/developer-tools/ai/agentos) skills plugin (`claude plugin install airwallex-agentos@claude-plugins-official`).
- Reference builds on GitHub at `awx-devx/*` (agent-cards, finance-manager, slack invoicing bot), to read for patterns only.
- **Proposed stack:** Node/TS + `@airwallex/node-sdk`, Postgres ledger, a Claude model with typed tools, and a small web console with approval cards.

**Hardest part: deposit → invoice matching when the sandbox can't produce realistic remittance data.** The deposit simulator has no reference or remittance field, and real cross-border receipts arrive fee-deducted and unreferenced (pain 3). How I'd de-risk it:
1. **Make the payer deterministic by design.** One Global Account per customer, so matching only has to solve *which invoices* and *why the amount differs*, not *who paid*.
2. **Put all simulation behind one `BankFeed` interface.** Remittance emails and PDFs are synthetic fixtures fed to the LLM, which is the realistic channel anyway.
3. **Day-1 spike (≤4 h):** create 3 Global Accounts, simulate deposits, and record exactly which fields `global_accounts/{id}/transactions`, `financial_transactions` and `deposit.settled` actually return in sandbox (payer_name? fee?). Confirm the webhook fires at all and fall back to polling if not.
4. **Golden test set:** 30 deposit/invoice cases (exact, SHA short-pay, partial, multi-invoice, duplicate, FX, reversal) with expected allocations. The matcher must hit 100% on deterministic cases before the LLM touches the ambiguous ones.

## Couldn't verify
- **Official judging criteria:** none are published on the landing or HackerEarth pages, so section 2 uses the guide and a judge's posted lens from another event.
- **What the Oct 23 "application/idea" submission must contain:** the form isn't visible without logging in.
- **Demo Day clock time and the Nov 15 finalist time.**
- **Event length:** the landing "About" text says "Over 48 hours" but elsewhere says "3 weeks" (HackerEarth shows Oct 25–Nov 13).
- **Sandbox details still to test:** whether one sandbox account can create many Global Accounts, whether the Billing API is enabled in sandbox, and whether deposit webhooks fire for simulated deposits. These belong in the day-1 spike.
- **Two pain sources:** the PYMNTS × Visa report is undated in the extracted text, and the Ledge sample skews toward companies with 51+ employees.
