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
