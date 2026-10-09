# Round 1: Judge scores (AB Judge)
_Written Thu 8 Oct 2026, ~7:20 PM IST. Inputs: `board/ROUND1-SHORTLIST.md` (S1–S3 sections), `board/round0/judge.md`, `raw/doc_deposit_wh.txt`, `raw/doc_verify.txt`, plus a re-fetch of the [guide](https://airwallexdev.com/guide), [builds page](https://airwallexdev.com/builds), its data files [builds.json](https://airwallexdev.com/content/builds.json) and [library.json](https://airwallexdev.com/content/library.json) (agent recipes). Greenfield. Nothing submitted, nobody contacted._

**Rubric (provisional, from round0/judge.md):** C1 pain + financial decision 25% · C2 Airwallex API depth 25% · C3 safety 20% · C4 reproducible demo 20% · C5 originality + adoption 10%. The total is capped at 4 if any money path has no approval or limit.
**Cap check:** **no idea triggers the cap.** S1 needs approval for every refund and for FX above a limit. S2 lets only small LOCAL payouts to allowlisted payees run on their own, and everything else needs approval. S3 needs approval for FX above a limit or near the floor. All three bound their autonomy in code.

---
## 1. Scores

### S1 Ledgerline (AR cash-application agent)
| Crit | Score | Justification (from the shortlist text) |
|---|---|---|
| C1 (25%) | **8** | It is a real decision (apply / write-off / chase / refund / hold) and each guide trigger flips it, e.g. the withholding-tax PDF flips "chase $300" to "close + tax receivable". The pain is backed three ways (P1 BILL, P2 Ledge, P3 PYMNTS), but all are vendor surveys and P3 is from 2021. |
| C2 (25%) | **7** | Broadest surface: deposits, GA, FX quote→conversion, beneficiaries, transfers, transfer simulation, `financial_transactions`, `deposit.*` webhooks. But the core data is **unverified**: payer bank details and `reference` on simulated deposits, and whether a bank-transfer deposit can be reversed. Airwallex's own doc says payer details "vary by Global Account financial institution and payment method" (`raw/doc_deposit_wh.txt`). |
| C3 (20%) | **8** | Refunds go only to the source account. Maker-checker above a threshold. Approvals are bound to amount/currency/counterparty/invoice/evidence hash. One refund per deposit with a dup lock. Audit ties out to `financial_transactions`. It loses points because the refund-to-source control depends on payer bank data that may not exist, and the FX autonomous-limit value is not stated. |
| C4 (20%) | **6** | The three beats are frozen. But beat 3's reversal "may have to be simulated in our own ledger", remittance PDFs are fixtures, there are about 6 sub-moments in under 5 minutes, and the feasibility estimate is "not yet reviewed by AB Staff Engineer". |
| C5 (10%) | **8** | It takes the guide's stated whitespace ("reconciliation… we have not written kits"), and the bookkeeping-firm channel is a credible adoption path. Risk: that same guide line invites many teams, so expect crowding. |
| **Total** | **7.35** | 2.00 + 1.75 + 1.60 + 1.20 + 0.80 |

### S2 PayRun Warden (supplier payment run + payee-change lock)
| Crit | Score | Justification |
|---|---|---|
| C1 (25%) | **7** | A real pay / convert-then-pay / defer / escalate decision, flipped by risk (new IBAN), evidence (SENT is not final) and balance (deposit). It has the strongest pain source in the set (AFP P6). Points off: two of the three flips are already scripted by kits 1 and 3, and the model's role is narrow (reading one email). |
| C2 (25%) | **8** | FX quote→conversion (REST), beneficiaries schema/validate/create, transfers + simulation, `payout.transfer.*` webhooks, `financial_transactions`. Every core call sits in kits 1 and 3, which the guide documents end to end. The `verify_account` spike is a bonus, but it's unconfirmed in sandbox. |
| C3 (20%) | **9** | The strongest control set: payee-change lock with out-of-band confirmation, allowlist + cooling-off, segregation of duties, signed approvals voided on requote or beneficiary change, deterministic `request_id` + `GET /transfers` check, PAID-is-not-final handling, SWIFT fee in code, hash-chained audit, kill switch, and an honest screening stub. |
| C4 (20%) | **8** | The most buildable: no enablement, every flow has documented simulation, and staff-engineer gave it medium-high confidence. Minor risk: the FAILED→CANCELLED auto-cancel can lose `failure_reason` on a slow poll. |
| C5 (10%) | **4** | The shortlist itself says overlap is "S2's real weakness": beats 2 and 3 are kit 3 and kit 1 / recipes 03 and 01, and the payee approval pattern echoes the "AI finance manager" reference build. Only the payee-change lock is new. |
| **Total** | **7.55** | 1.75 + 2.00 + 1.80 + 1.60 + 0.40 |

### S3 Float (multi-currency cash-placement agent)
| Crit | Score | Justification |
|---|---|---|
| C1 (25%) | **4** | The hold / convert / escalate decision is real, but the shortlist admits "No memo cites a source on idle or mis-placed currency balances", so it has the thinnest evidence. Stakes are low for a 10–200-person firm, and the model only reads one email. |
| C2 (25%) | **4** | One product family (FX rates / quotes / conversions) plus balances and a deposit simulation. "No beneficiaries, no transfers, no issuing." |
| C3 (20%) | **7** | Floor in code, approvals bound to quote id + evidence, requote voids approval, idempotent `request_id`, audit, kill switch. A sound, deliberately small risk surface, so there's little to show off. |
| C4 (20%) | **7** | The smallest build, and the guide says conversions settle immediately. But beat 3 needs the quote to move. If sandbox quotes barely move, a threshold set by the demo drives it, which looks staged. |
| C5 (10%) | **4** | Cash placement is real whitespace, but the shortlist concedes "a judge could still read it as kit 1 without the payouts". The adoption path is unclear: firms without a treasurer may not buy a weekly convert-or-hold tool. |
| **Total** | **5.20** | 1.00 + 1.00 + 1.40 + 1.40 + 0.40 |

**Sensitivity (read this before treating the ranking as final):** S2 leads S1 by only 0.2. If the day-one sandbox spike confirms that simulated deposits carry payer bank details and `reference`, and that reversal works for bank transfers, S1 rises to C2 8 / C4 7 = **7.80** and overtakes. S2's gap is originality, which no spike can fix.

---
## 2. Red-team of the top scorer: S2 PayRun Warden (7.55)

**Three weakest points**
1. **It reads as kit 1 + kit 3 stapled together.** Beat 3 ("a deposit lands… re-opens only the decisions the new cash changes") is nearly word for word the guide's kit 1 ("recalculates only the decisions affected by the new balance") and recipe 01. Beat 2 is kit 3 / recipe 03 ("SENT then FAILED… new request_id"). Judges will have seen many of these.
2. **The "agent" is thin.** "Bank details changed → hold" is a deterministic rule. The guide itself says "If the agent should make the same choice every time, write the rule in code". So what does the model add beyond reading one email? A judge can strip out the LLM and lose almost nothing.
3. **The lock is a checkbox.** `beneficiaries/validate` only proves format. `verify_account` is unconfirmed in sandbox, and UK CoP "is enabled on request" (`raw/doc_verify.txt`), which would need off-board contact. So "out-of-band confirmation" is just a button in the demo. Also, the "AI finance manager" reference build already flags "a supplier you've never paid" and "waits for you to say yes" before moving money ([builds.json](https://airwallexdev.com/content/builds.json)).

**Questions a skeptical Airwallex judge will ask**
1. "Kits 1 and 3 already do two of your three beats. What's left that's yours, and why does it need a model?"
2. "How do you tell a fraudulent IBAN change from a legitimate one? What does a false positive cost: a late supplier and a damaged relationship?"
3. "What *is* out-of-band confirmation in your product: who calls whom, what gets recorded, and how do you stop a compromised approver from just clicking through?"
4. "If `verify_account` returns FULL_MATCH on the *new* account, do you release the payout? What if the fraudster opened an account in the supplier's name?"
5. "Kill the process mid-run and restart it. Show me it doesn't pay twice, and that a requote voids the old approval."
6. "Why would a 10–200-person firm adopt this instead of the approval controls already in their AP or banking tools?"

**Changes that raise each sub-score**
| Crit | Now | Change | New |
|---|---|---|---|
| C1 | 7 | Make the model do real evidence work. Compare the change-request email to the supplier's past thread and invoices (bank details on the invoice vs on file, sender domain, timing next to a due invoice, amount change), and explain the mismatch. Rules still decide; evidence picks the path (hold / release / escalate). Lead with AFP 2026 BEC 74% + vendor-impostor data. | 8 |
| C2 | 8 | Spike `verify_account` on **SEPA EUR VoP** (CoP needs enablement, so skip it) and show a NOT_MATCHED/PARTIAL_MATCH result driving the hold. Verify `payout.transfer.*` webhooks live with HMAC + dedupe. Tie every invoice to its `financial_transactions` rows (PAYOUT / CONVERSION / FEE). | 9 |
| C3 | 9 | Show, rather than claim, two things in the video: (a) restart mid-run → no double pay; (b) requote or beneficiary edit → approval voided. Make out-of-band confirmation a recorded callback by a *different* user than the one who changed the payee. | 9 (secured) |
| C4 | 8 | One-command seed via simulation endpoints, a deterministic replay mode, and the exception path recorded. Test from a fresh sandbox account. | 9 |
| C5 | 4 | **Reposition as "the payout firewall": the payee-change lock is the product, and the payment run is its context.** Cut beat 3 to ≤15 s, or replace it with a second fraud variant (an amount-change or a lookalike domain on an invoice PDF). Add a per-supplier "known-good fingerprint" built from payout history (`GET /transfers`). Pitch the channel as AP or bookkeeping firms running runs for many clients. | 6 |
| **Total** | 7.55 | | **8.45** (2.00 + 2.25 + 1.80 + 1.80 + 0.60) |

**S1's single biggest weakness, for comparison:** sandbox fidelity. Its headline safety control (refund only to the source account) and its beat 3 (reversal) both depend on deposit data Airwallex says "vary by… institution and payment method". If the spike fails, S1 drops to about C2 6 / C3 7 / C4 5, which is **6.70**.

---
## 3. Overlap check
Sources re-fetched today:
- [Guide: starter kits](https://airwallexdev.com/guide#the-starter-kits)
- [Builds page](https://airwallexdev.com/builds)
- Live data behind it: [builds.json](https://airwallexdev.com/content/builds.json) has **5** reference builds; [library.json](https://airwallexdev.com/content/library.json) has **8 agent recipes**, which mirror kits 1–8.

**This resolves shortlist conflict #11.** "6 Agent recipes / 7 Reference builds" are **step numbers** on the page (they continue the 1–5 setup steps on airwallexdev.com), not counts. There are exactly 5 builds.

| Idea | Closest kit / recipe | Closest reference build | Severity | How to differentiate |
|---|---|---|---|---|
| **S1** | No kit covers reconciliation (the guide says so). Kit 3 / recipe 03's never-pay-twice discipline is borrowed for refunds. Kit 8 asks to "reconcile each cycle", but that's for a marketplace platform, a different job. | **AI finance manager**: "put your month-end together. Cash, spend, budget and anomalies". That's a moderate framing clash if S1 is pitched as a "close" tool. **Invoicing in Slack** makes invoices and payment links, which clashes with S1's *stretch* (billing invoices / payment links). | **Low–Med** | Pitch as *cash application that moves money* (refund-to-source, FX), not as "month-end close" or reporting. Drop the payment-link stretch. **Crowding flag:** the guide openly advertises reconciliation as whitespace, so expect several rival entries. Win on the refund lock and the evidence flips. |
| **S2** | **Kit 1 / recipe 01** (fund / convert / defer / escalate, re-plan after a deposit) **and kit 3 / recipe 03** (no double pay on a failed transfer). Two of the three beats. | **AI finance manager**: flags "a supplier you've never paid", and "when you ask it to move money, it stops… waits for you to say yes". That's close to S2's approval + new-payee story. | **HIGH** | Make the payee-change lock the product (see §2 C5): multi-signal evidence, VoP name-match, a recorded out-of-band callback by a second user, a per-supplier fingerprint. Show that a *changed* known supplier is caught, which the reference build doesn't claim. |
| **S3** | **Kit 1 / recipe 01**: converts under a reserve floor and re-plans after a deposit. The shortlist concedes it "could… read… as kit 1 without the payouts". | AI finance manager: a runway read from balances (low). Allocard: "rules run again" on change, a pattern match only (low). | **Med–High** | Lean hard on *surplus* placement and the natural hedge vs kit 1's *scarcity*. Show unwinding a hold when a bill moves. Even so, evidence and API depth stay weak. |

---
## 4. Verdict
**S2 PayRun Warden (7.55) ≈ S1 Ledgerline (7.35) ≫ S3 Float (5.20).** S2 wins today on safety and buildability but carries a HIGH kit and reference-build overlap. S1 is the more original bet and overtakes (7.80) if the day-one deposit-data spike passes. Run that spike before choosing between them, and drop S3.
