# Round 0: Judge brief (AB Judge)
_Written 2026-10-08 IST. Read-only research. Nothing submitted, registered, or sent._
Sources: [HE landing](https://airwallex.hackerearth.com/) · [HE challenge page](https://www.hackerearth.com/challenges/hackathon/agentic-banking-hackathon/) · [Builder guide](https://airwallexdev.com/guide) · [airwallexdev.com](https://airwallexdev.com/)

---
## 1. What the official pages actually say

### 1a. Judging criteria and weights: **NOT PUBLISHED**
- None of the HE landing page, the HE challenge page (Overview/Tracks/Key Dates/Prizes/Questions tabs), airwallexdev.com, or the builder guide publishes judging criteria, a rubric, or weights. I checked the raw HTML and Next.js payloads too.
- The only official judging-related lines:
  - "a demo day in front of judges from fintech and venture" ([HE landing](https://airwallex.hackerearth.com/))
  - Prizes: **Founder's Choice $30,000**, "Open category. No specific requirements." **Judges Choice $20,000**, "Open category. No specific requirements." **Visa Award $15,000**, "Requires use of Visa and Airwallex tooling". **Metal Award $15,000**, "Requires use of Metal and Airwallex tooling" ([HE landing](https://airwallex.hackerearth.com/))
  - HE generic FAQ: "The entire idea need not be fully implemented however, the submission should be functional so that it can be reviewed by the judges." ([HE challenge page](https://www.hackerearth.com/challenges/hackathon/agentic-banking-hackathon/))
- **The closest thing to official "criteria"** is the guide's *Build around a financial decision* section ([guide](https://airwallexdev.com/guide#build-around-a-financial-decision)). Quoted verbatim:
  > "Choose a finance task that someone repeats and identify the decision inside it. The agent should choose differently when a balance, deadline, piece of evidence, or risk changes. Let the agent move money or update financial state, and state which actions require a person's approval."
  > "In the demo, show the user's goal, the agent's initial plan, the new information, the revised decision, and the resulting balance, payment, or status. Keep amounts, limits, reserves, validation, duplicate protection, and state transitions in code. Use the model to read unstructured text, compare evidence, propose a plan, and explain an exception. Give the model typed tools rather than unrestricted credentials, and bind each approval to the amount, currency, counterparty, purchase terms, and evidence shown to the approver."
  > "Finish the demo with a financial action or an escalation to a person. If the agent should make the same choice every time, write the rule in code instead of asking a model to narrate it."
- *Unofficial signal, not for this hackathon:* Sam Waldo (Head of Startups, Asia at Airwallex) judged a different Airwallex-backed event, "Agents, Everywhere" (Singapore, 12 Sep 2026). He wrote: "does this solve a real problem for founders or operators, does it hold up across markets and currencies, is there a credible path from prototype to something someone would actually adopt. These days, the interface is the easy part" ([LinkedIn](https://www.linkedin.com/posts/sam-waldo_judging-the-agents-everywhere-hackathon-activity-7500783609373462528-jCSr)). Treat this as a hint about how Airwallex judges think, not as a published criterion here.

### 1b. Dates and the idea-phase deadline
| Phase | Official (HE, shown in UTC) | IST | PT (PDT) |
|---|---|---|---|
| Registration & Idea Phase | Oct 5 3:30 PM to **Oct 23, 2026 6:29 PM UTC** | **Oct 23, 11:59 PM IST** ✅ | Oct 23, 11:29 AM PT |
| Build Phase | Oct 25 4:30 AM to Nov 13, 2026 6:29 PM UTC | Oct 25 10:00 AM to Nov 13 11:59 PM IST | |
- Landing page dates: "Oct 23 Applications Close"; "Oct 25 Accepted teams are notified. Official hackathon build period begins."; "Nov 13 Project submissions due."; "Nov 15 Finalists are selected."; "Nov 19 Demo Day in San Francisco (remote participation optional)." ([HE landing](https://airwallex.hackerearth.com/))
- **Confirmed:** the 11:59 PM deadline is **IST**. The page gives 18:29 UTC, which is 23:59 IST.
- **This is a selection gate.** Teams have to be *accepted* to build ("Accepted teams are notified"). The idea/application is what earns the slot.

### 1c. Idea-phase submission requirements: **NOT PUBLISHED**
- No public page lists idea-phase deliverables, format, length, or selection criteria. The HE "Submissions" tab probably shows the form only to logged-in users. That's unverified, and I did not log in or register.
- Final (build-phase) submission, verbatim: "A working demo, a short video walkthrough under five minutes, and a link to your repository with setup instructions." ([HE landing FAQ](https://airwallex.hackerearth.com/))
- HE generic FAQ adds: "submit it on HackerEarth in tar/zip file format along with instructions to run the application and source code" ([HE challenge page](https://www.hackerearth.com/challenges/hackathon/agentic-banking-hackathon/))

### 1d. Eligibility and rules that could bite
- "Developers, designers, data scientists, and founders aged 18 and over, anywhere in the world." Solo or "a team of up to four". Free. ([HE landing](https://airwallex.hackerearth.com/))
- IP: "You retain full ownership of your project. Submitting only grants us permission to showcase your work" ([HE landing](https://airwallex.hackerearth.com/))
- ⚠️ **Conflicts to resolve before build.** The HE generic FAQ says "all code needs to be in public domain (open source) so that it can be evaluated by the judges", and that a demo video is "not mandatory, and only good to have" ([HE challenge page](https://www.hackerearth.com/challenges/hackathon/agentic-banking-hackathon/)). The Airwallex FAQ *requires* a <5 min video. **Plan for the stricter version: a public repo plus a <5 min video.**
- ⚠️ The landing page says "Over 48 hours, teams build" but also "3 WEEKS To design, build, ship". Plan for the 3-week build phase.
- Sandbox-only and synthetic data: "Use only sandbox data"; for kits 1–8 "build with synthetic data" ([guide](https://airwallexdev.com/guide)). Kit 9 is the exception: it uses real merchants with an Airwallex-issued pre-funded card.
- **Access lead times (delivery risk):** kits 5–8 need connected accounts and platform payments enabled by Airwallex ("You cannot switch those on yourself"). Kit 9 needs allowlisted Airi CLI. Kit 10 needs merchant-side Agentic Commerce access. Each one means emailing devhelp@airwallex.com and waiting ([guide](https://airwallexdev.com/guide#before-you-start)). Kits 1–4 need no extra enablement.
- Partner awards need partner tooling: Visa (TAP/VIC) or Metal (L1 blockchain) **plus** Airwallex tooling.

### 1e. Airwallex tooling the guide highlights (judges will expect real use)
- **Hosted MCP servers:** Docs MCP `https://mcp.sandbox.airwallex.com/docs` (no account) and Developer MCP `https://mcp.sandbox.airwallex.com/developer` (real sandbox calls). **AgentOS** is "skills bundled with both servers", installed as a Claude plugin `airwallex-agentos` ([airwallexdev.com](https://airwallexdev.com/)).
- **REST** at `api.sandbox.airwallex.com/api/v1` with 30-min bearer auth. **Use REST** for "FX conversions, beneficiary validation, dispute challenges, connected-account calls, and platform money movement" because there's no MCP tool or the tool is incomplete ([guide](https://airwallexdev.com/guide#rest-or-mcp)).
- **Product surface:** Global Accounts, balances, FX rates/quotes/conversions, beneficiaries + schema/validate, transfers, Issuing (cardholders, cards, limits, freeze), Payment Acceptance and disputes, Connected Accounts (`x-on-behalf-of`), `connected_account_transfers`, `charges`, platform reports.
- **Simulation APIs** (deposits, card auth/capture/reverse, transfer state transitions, disputes) make a demo reproducible.
- **Webhooks:** HMAC-SHA256 on raw bytes, dedupe on event id, at-least-once delivery.
- **10 starter kits** in 6 areas. The guide flags open whitespace: "Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them. Good territory if you want a problem few other builders will take on." ([guide](https://airwallexdev.com/guide#where-to-start))
- **Reference builds** at airwallexdev.com/builds: Agent cards, Drop-in checkout, Invoicing in Slack, AI finance manager (AgentOS/Telegram), Allocard (budget-driven card limits). Judges have seen these, so cloning one won't stand out.

---
## 2. Round 1 scoring rubric (PROVISIONAL, not official)
No official criteria or weights exist, so the five criteria below are **my provisional ones**. They come from the guide's "Build around a financial decision", the submission FAQ, and the prize text. Replace them if Airwallex publishes official criteria.

| # | Criterion (provisional) | Weight | Derived from |
|---|---|---|---|
| C1 | Real operator pain + a genuine financial *decision* | 25% | Guide: "finance task that someone repeats… the decision inside it" |
| C2 | Depth of real Airwallex API/MCP use | 25% | "Build on Airwallex APIs"; kit endpoint lists |
| C3 | Bounded autonomy and safety (approvals, limits, idempotency, audit) | 20% | Guide: limits/validation/duplicate protection in code, bound approvals, typed tools |
| C4 | Working, reproducible demo | 20% | FAQ: working demo + <5 min video + repo with setup |
| C5 | Originality + adoption path | 10% | "Few other builders" whitespace note; reference builds; Waldo signal (unofficial) |

**Total** = Σ(score × weight), out of 10. Example: 8, 7, 9, 6, 5 → 2.0 + 1.75 + 1.8 + 1.2 + 0.5 = **7.25**.
**Hard caps (my judgment call):**
- The agent can move money with no approval/limit path → **C3 = 0, and the total is capped at 4**.
- Zero real Airwallex calls (all mocked) → **C2 ≤ 2**.

| | 3 (weak) | 6 (solid) | 9 (winning) |
|---|---|---|---|
| **C1 Pain/decision** | A generic "finance copilot". The agent answers questions or summarizes, and nothing gets decided. | A real recurring task with a named persona. The agent makes one decision, but it wouldn't change when inputs change. | A named operator with a cited pain. The agent's choice *visibly changes* when a balance, deadline, evidence, or risk changes (plan → new info → revised decision → financial outcome). |
| **C2 Airwallex depth** | 1–2 read calls (list balances) and the rest is mocked. | Several write calls on one product (e.g. beneficiary + transfer) via MCP or REST, with sandbox simulation. | Multiple products composed: FX quote→conversion→transfer, issuing controls, or connected accounts. REST is used where MCP falls short, webhooks are verified, and simulations sit behind one interface. |
| **C3 Safety** | The LLM holds the API key and amounts live in the prompt. No retry or idempotency story. | There's an approval step and some limits in code, but the approval isn't bound to exact terms, and retry behaviour is unclear. | Policy is in code. Approval is bound to amount/currency/counterparty/evidence and re-asked when terms change. request_id idempotency and a duplicate lock are in place, plus an audit log and a kill switch (e.g. card freeze). Tenant isolation is enforced where relevant. |
| **C4 Demo** | Slides or a screen recording of a mock. No one else can run it. | It runs end-to-end on sandbox with a README, but needs hand-holding or breaks on the exception path. | A one-command setup that seeds itself via simulation. A deterministic <5 min video shows the happy path plus one exception (decline, failed transfer, changed price). The public repo has no secrets. |
| **C5 Originality/adoption** | Re-skins a starter kit or reference build verbatim. | A kit adapted with a meaningful twist. A plausible buyer. | It takes uncovered territory (e.g. reconciliation or cash placement) or a sharp new angle. There's a clear first user, a multi-currency/multi-market story, and a way it becomes a product. |

---
## 3. Five most likely ways this entry loses
| # | Loss mode | How a judge spots it | How to avoid it |
|---|---|---|---|
| 1 | **Generic chatbot wrapper.** A "talk to your finances" bot with no decision. | The demo is mostly Q&A, and if you strip out the LLM nothing financial happens. | Build around one decision that flips on new information, and end on a payment, conversion, card-control change, or escalation (guide rule). |
| 2 | **Unsafe or unbounded autonomy over money.** | The model holds raw creds. Limits are in prompts. A retry could double-pay. Approval says "OK?" with no amount or counterparty. | Use typed tools only and keep limits/reserves/validation in code. Use request_id plus a duplicate lock, bind approval to exact terms, keep an audit log, and add a revoke path (card freeze). |
| 3 | **Shallow or fake Airwallex use.** Mocked APIs, or a single `GET /balances`. | No sandbox IDs on screen and no FX/transfer/issuing writes. The code just has `mock_airwallex.py`. | Show real sandbox objects changing state live: quote→conversion, beneficiary→transfer→simulated SENT/FAILED, card auth decline with `failure_reason`. |
| 4 | **Idea too broad, or the demo can't be reproduced.** | "AI CFO for everything". The video skips the exception path, and the README won't run on a fresh sandbox. | Pick one persona, one workflow, and one exception. Seed through simulation endpoints, script the demo, and test from a clean sandbox account. Also pick kits 1–4, or request platform/Airi access *early*: access delays sink kits 5–10. |
| 5 | **Compliance / financial-correctness blind spots.** | Ignores payee verification or vendor-imposter risk, sums balances across tenants, ignores SWIFT fees (EUR 12.85) or major-unit amounts, treats CANCELLED/SENT wrongly. | Model the state machines (transfer CANCELLED ≠ human cancel; SENT ≠ final). Include fees, keep tenants isolated, and add beneficiary validation and escalation on new-payee/changed-details. State plainly what a production version would need (KYB/AML/sanctions screening) without claiming to do it. |
_Honourable mention: copying an Airwallex reference build (AI finance manager, Allocard). The judges built those._

---
## 4. Top 3 real operator pains I want addressed (cited)
**P1: Cash reconciliation is the close bottleneck.** The guide itself says no kit covers it, so it's whitespace.
- Ledge, *State of month-end close 2025* (survey of 100 finance professionals): "50% of teams take 6+ business days to close"; "Cash reconciliation is the #1 most time-consuming activity"; "Average time spent on cash reconciliation: 20–50 hours per month"; "Common blockers: missing payment details, mismatched amounts, fragmented sources, and manual workarounds" ([ledge.co](https://www.ledge.co/content/month-end-close-benchmarks-for-2025))
- Guide: "Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them." ([guide](https://airwallexdev.com/guide#where-to-start))

**P2: Cross-border payout and FX operations: delays, multi-currency complexity, conversion fees.**
- Airwallex / Edgar, Dunn & Company survey of 1,000 SMBs (US, UK, China, AU, SG), Q3 2023: "delays in processing and disbursing payments (48 per cent)"; "Complexity in managing multiple payout methods and currencies is also a challenge globally for SMBs (47 per cent)"; "Forced currency conversion leading to high transaction fees is the second most commonly cited issue (41 per cent)" ([Airwallex newsroom](https://www.airwallex.com/global/newsroom/demand-for-embedded-finance-soars-among-smbs-as-traditional-banks-fall-short))

**P3: Payments fraud and payout control (BEC, vendor impostors).** Agents that pay have to verify *who* they're paying.
- AFP *2026 Payments Fraud and Control Survey* (465 US treasury practitioners): "More than three-quarters of organizations (76%) in the United States experienced attempted or actual payments fraud in 2025"; "About three in four organizations (74%) were affected by business email compromise (BEC) in 2025"; "Just 17% of organizations leverage AI to combat payments fraud." ([AFP press release, Apr 14 2026](https://www.financialprofessionals.org/about/learn-more/press-releases/Details/over-75-percent-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags))
- AFP 2025 edition: "Vendor imposter fraud, cited by 45% of respondents, saw an 11-percentage-point increase in incidences from the previous survey." ([AFP press release, Apr 15 2025](https://www.financialprofessionals.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024))

**Judge's take:** the strongest entry fuses P1–P3 into **one decision**. Example shape (not a pick): match incoming and outgoing money, then decide pay / hold / escalate on a supplier payout when details or evidence change, with policy in code and approvals bound to exact terms.

---
## 5. Gaps / open questions for the orchestrator
1. **No official judging criteria or weights** anywhere public. The rubric above is provisional.
2. **No public idea-phase form spec** (fields, length, selection criteria). It probably sits behind HE login, and someone with the account has to look.
3. **Conflicting rules:** HE generic FAQ (open-source code, optional video) vs the Airwallex FAQ (video required, IP retained). "48 hours" vs "3 weeks". Assume the stricter version.
4. **Access lead time:** kits 5–10 need Airwallex enablement by email. Decide early whether the idea depends on it. (I contacted no one.)
5. No published judge names for this event.
