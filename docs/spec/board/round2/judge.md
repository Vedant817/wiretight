# Round 2: Judge red-team of SPEC-v1 "Countersign" (AB Judge)
_Written Thu 8 Oct 2026, ~7:25 PM IST. Inputs: `board/SPEC-v1.md`, `board/DECISIONS.md` (D3, F7), `board/round1/judge-scores.md`, `board/round1/staff-engineer-feasibility.md`. Also re-checked: [guide](https://airwallexdev.com/guide), [builds.json](https://airwallexdev.com/content/builds.json), [library.json](https://airwallexdev.com/content/library.json). Greenfield. Nothing submitted, nobody contacted. (Round 1b `judge-rescore.md` was never written, so there's nothing to mark superseded.)_

**Lens:** a skeptical Airwallex judge with 5 minutes of video and a repo. Same provisional rubric: C1 pain + decision 25 · C2 API depth 25 · C3 safety 20 · C4 reproducible demo 20 · C5 originality + adoption 10. Total capped at 4 if any money path has no approval.

---
## 1. Score: **7.75 / 10**
| Crit | Score | Justification |
|---|---|---|
| C1 (25%) | **8** | A real, repeated job (the weekly cross-border payment run) with a decision that flips on evidence (duplicate, changed IBAN), balance (reserve floor, deposit), risk (quote moved) and failure type (§4, §7). The pain is well cited (AFP 2026, APQC, Ledge, Swift). Points off: the hook generalises US-only AFP data to "companies", and one stat is still unverified (see S1). |
| C2 (25%) | **9** | Deep, correct surface: FX quote→conversion over REST with `quote_id`, beneficiaries schema/validate/create with versioning, transfers with deterministic `request_id` plus a lookup before retry, transition simulation with typed `failure_type`, `payout.transfer.*` webhooks with HMAC, `financial_transactions` + `balances/history` tie-out (§5). It follows the guide's gotchas (no `x-api-version` on FX, the SWIFT fee, LOCAL vs SWIFT). A few endpoints and events are unverified (S3). |
| C3 (20%) | **9** | Best in class on paper: T0/T1/T2/HARD BLOCK tiers, earned autonomy, a canonical packet hash rebuilt from live state before execution (§6.2), segregation of duties, the executor process holds the key and the model holds none (§6.4), AMBIGUOUS handling, PAID treated as provisional. **Cap check: no cap.** T0 auto-pay is bounded by payee history, LOCAL-only, per-payment/run/FX limits and the floor. Held back from 10 because out-of-band verification is a self-attested form (M3). |
| C4 (20%) | **6** | Nine beats and seven bills squeezed into 4:30 (§11). The T0 beat contradicts `policy.yaml` (M2). The live "0 residual" tie-out and the PAID→FAILED path are both untested in sandbox (M5, §16). The solo scope (PDF/email/CSV ingest, fuzzy dupes, planner, approvals, executor, incidents, recon, FX gain/loss journal, a 50-scenario eval) is the biggest of any idea we've seen. |
| C5 (10%) | **5** | The adoption story is strong (shadow mode, policy as YAML, existing Airwallex account, bookkeeper channel, §14). But the spec **still positions itself as kits 1 + 3**: the track line, the application "starter kit" field, and the title "never pays twice" all echo kit 3. D3's repositioning hasn't reached the text (M1). |
| **Total** | **7.75** | 2.00 + 2.25 + 1.80 + 1.20 + 0.50 |

**Carry-over checks (all pass; no hard dependency):**
- `verify_account` is cut from the demo, but the spec still lists it in §2, §5, pre-work and the cut list. That's optional, not relied on. Remove it from the pitch text (S4).
- **Deposit payer bank account:** not needed. Deposits are used only for funding, re-planning and DEPOSIT↔receipt matching. ✅
- **Bank-transfer reversal:** not used. `PAYOUT_REVERSAL` concerns transfers, not deposits. ✅
- **Simulated `deposit.*` webhooks** are undocumented (F7). §4.3 says "a `deposit.settled` webhook **or** new balance", so polling has to be the primary path in the text and the code (S3).

---
## 2. MUST-FIX (each of these would lose)
| # | Problem (where) | Exact fix |
|---|---|---|
| **M1** | **It still reads as kit 1 + kit 3.** §0 track line, §15 "Track / starter kit: … (1) + … (3)", the title "the cross-border payment run that never pays twice" (kit 3's line is "without paying twice"), and a tagline that leads with "runs a multi-currency supplier payment run". | Retitle to e.g. **"Countersign: no payout reaches a bank account a human hasn't countersigned"**. Track field: "Treasury & Ops, original idea (payee-change control + reconciliation); borrows kit 3's no-double-pay discipline". Tagline: lead with the redirected-payment lock, then the proof that every payment landed and tied out. Treat planning/netting as context, not the claim. |
| **M2** | **The demo contradicts the policy.** §11 2:05 says "#1 auto-executes (T0 known payee)", but #1 is USD 4,200 and `auto.per_payment_limit_base: 2000`. T0 also needs "≥2 FINAL payments" and "unchanged ≥30 days", and with `settle_window_hours: 48` a fresh sandbox can't produce that history. | Make #1 ≤ USD 2,000 (or show it going to T1 because it's over the limit, which is a better beat). Seed payee history with a `seed_history.py` that creates two prior simulated transfers to PAID and back-dates the fingerprint age **in our ledger**. Label it on screen: *"Payee history seeded for demo. Production: built from your past Airwallex transfers (`GET /transfers`)."* |
| **M3** | **The headline control is a checkbox.** With `verify_account` cut, "out-of-band verification (who called, which number from the vendor master, when)" is free text any approver can type. A judge will ask "what stops the approver from just typing it?" | Enforce in code. (a) The verifier must differ from the requester and from whoever ingested the change email. (b) The callback number must come from a vendor-master record **created before** the change request: compare timestamps and show the record's age, and reject any number found in the change email. (c) Add a cooling-off hold on the first payment to new details (`policy.yaml`; shorten it for the demo and say so). (d) Add a first-payment cap. On screen: *"Name check (Verification of Payee) not available in sandbox. Production: `/beneficiaries/verify_account`."* This mirrors the FBI's advice: "Use secondary channels or two-factor authentication to verify requests for changes in account information" ([IC3](https://www.ic3.gov/CrimeInfo/BEC)). |
| **M4** | **Overstuffed video.** Nine beats (verify, plan, auto-exec, re-quote void, execute, deposit re-plan, failure, recovery, recon, audit/Metal, metrics) in 4:30 won't be readable, and over 5:00 breaks the FAQ rule ("video walkthrough under five minutes"). | Three headline beats plus a 20 s plan. See §6 change 1 for the script. Move re-quote void, the FX baseline, Metal and the eval metrics into README/eval CSVs and **one** 10 s closing card. |
| **M5** | **The live "tie-out = 0 residual" is untested.** Whether `financial_transactions` shows FEE/PAYOUT_FAILURE rows promptly, and whether a failed SWIFT transfer refunds principal and fee, is unverified (shortlist conflict list; staff-engineer §1). If the residual is non-zero on camera, a headline fails. | Make it a day-1 spike (staff-engineer §7 item 6). If rows lag, tie out from the transfer/conversion objects and **show the residual with its explanation**. An honest "residual 12.85 EUR: SWIFT fee on returned transfer, booked as expense" is better than a staged zero. |
| **M6** | **Possible rule exposure from pre-built code.** §12 pre-work (Oct 21–24) builds "synthetic data generator… DB models + migrations" and a public repo before the build phase opens Oct 25. The application (§15) claims "Spikes… are done before the build phase". The rules don't say whether earlier code is allowed (F2). | Keep pre-work to throwaway spikes in a separate scratch repo, and keep product code at zero until Sun 25 Oct 10:00 AM IST. Change the application line to what will be true on the submission date (e.g. "sandbox auth, deposit and transfer simulations tested"). Never claim spikes that haven't run. |

---
## 3. SHOULD-FIX
- **S1 Stat hygiene:**
  - "74% of companies" should be "74% of US organizations (AFP 2026, n=465)".
  - "wires the top BEC target at 63%" is unverified (shortlist conflict #4): check the AFP release or drop it.
  - APQC 1.5% is a share of the **number of disbursements**, so say "disbursements", not "payments".
  - Label the Wise £2.8bn as Wise-commissioned and UK-only.
  - The "62% cash forecasting" figure (AFP 2025) wasn't in any verified set: verify or drop it.
- **S2 "Cryptographically bound"** (§15) overclaims, since a SHA-256 hash isn't a signature. Say "hash-bound", or (better, see §6 change 3) have the approver **sign the packet hash with a passkey (WebAuthn)**.
- **S3 Remove or verify unverified claims:**
  - T0 "can be undone before SENT via cancellation where supported".
  - Native approvals via `payout.transfer.in_approval` (API path unverified).
  - `GET /fx/quotes/{quote_id}`.
  - The event names `payout.transfer.processing/sent`: the dev lab's "Expected events" list only `paid/failed/cancelled` ([airwallexdev.com](https://airwallexdev.com/)).
  - Make polling primary for simulated deposits.
- **S4 `verify_account`:** remove it from the application and the §2 table. Keep it in code behind a flag. F7 says SEPA VoP has no enablement gate, so test it on day 1, but it's never a demo beat.
- **S5 Metal anchor:** either target the **Metal Award** properly ("Requires use of Metal and Airwallex tooling", [HE](https://airwallex.hackerearth.com/)) as a separate, scoped stretch, or remove it from the main video. Half-done, it looks like a gimmick.
- **S6 Solo scope:** cut CSV import and Slack from the core (already on the cut list, so just say so up front). Keep FX gain/loss as one journal line, not a feature.
- **S7 Recovery path = BEC vector:** asking a supplier by email for "corrected details" after `BENEFICIARY_NAME_MISMATCH` is exactly how redirect fraud works. The spec already routes it to T2; **say so on screen**, because it's the strongest moment in the demo (see §5).

---
## 4. Overlap risk (would a judge call it a copy?)
| Source | What it says | Spec overlap | Copy? |
|---|---|---|---|
| **Kit 1 Adaptive Treasury Controller** ([guide](https://airwallexdev.com/guide#1-adaptive-treasury-controller)), recipe 01 ([library.json](https://airwallexdev.com/content/library.json)) | "funds… converts the minimum… defers the cheapest obligation, and escalates…"; "After a deposit arrives, the agent recalculates only the decisions affected by the new balance." | §4.3 planner (PAY_NOW/DEFER/CONVERT_THEN_PAY/ESCALATE), S3/S4, and demo 1:30–3:00 ("re-plan re-opens only #6"). Almost word for word. | **Yes, for that segment.** Compress to ≤20 s of context. |
| **Kit 3 Payment Ops Incident Commander** ([guide](https://airwallexdev.com/guide#3-payment-ops-incident-commander)), recipe 03 | "Resolve a delayed supplier transfer without paying twice"; "different `request_id` values"; "Do not close the incident only because the replacement reaches PAID. Record what happened to the original." | §4.7 Recover, S7, demo 3:00–3:45 ("Original: CANCELLED/returned, recorded"), and the title. | **Yes, if shown as-is.** It becomes distinctive only when the replacement's new bank details are forced through the payee-change lock (S7). |
| **AI finance manager** ([builds.json](https://airwallexdev.com/content/builds.json)) | "a supplier you've never paid"; "when you ask it to move money, it stops. It shows you the amount, the counterparty, the account… waits for you to say yes"; "put your month-end together". | New-payee flag, the approval card, the reconcile/report step. | **Partial.** The judges built this. The difference has to be visible: a *known* supplier whose details *changed*, approvals that **void** on any change, and a tie-out to zero rather than a narrated summary. |
| **Allocard** (builds.json) | "Every limit is a rule… No ticket. No approvals." | Policy-as-code (`policy.yaml`) only. No issuing. | No. |
| **Agent cards / Drop-in checkout** | Card policy declines / embedded checkout. | None (issuing and acceptance excluded, §5). | No. |
| **Invoicing in Slack** | "Tag a Slack thread, get an Airwallex invoice." | Optional Slack approvals only. | No, as long as Slack stays optional and isn't the UI. |

---
## 5. Distinctiveness verdict: the three candidate leads
**Verdict:** the three leads are distinctive enough **only if the lock headlines and is shown twice**. As SPEC-v1 is written, they aren't.
- **Headline: the bank-detail-change lock.** No kit or reference build covers it. It sits on the strongest evidence (AFP 2026 BEC 74%, vendor-impostor fraud up 11 pts in AFP 2025), and its control is FBI-recommended practice ([IC3](https://www.ic3.gov/CrimeInfo/BEC)). Generalise it into one rule a judge can repeat: **"No payout reaches a destination that hasn't been countersigned on exact terms."** Show it fire twice:
  1. On the lookalike-domain "new IBAN" email (fraud).
  2. On the *legitimate* corrected details after a `BENEFICIARY_NAME_MISMATCH` failure. Recovery doesn't get a shortcut.

  That second firing is what turns a kit 3 copy into something nobody else will show.
- **Supporting: the reconciliation tie-out.** The guide calls it whitespace ("we have not written kits for them"), and it's the "proof" close that the AI finance manager only narrates. Keep it as the final beat, but only after M5's spike. It's the riskiest live sandbox dependency.
- **Supporting detail, not headline: PAID isn't final.** Airwallex judges know their own state machine, so it reads as diligence, not as a product. PAID→FAILED may not be simulatable (§16). Keep it as one line in the incident flow plus a unit test, and show the ledger's `PROVISIONAL → FINAL` badge. Don't cut it: it's cheap and signals rigour.
- **Cut from the lead:** treasury planning/netting and the deposit re-plan (kit 1) become ≤20 s of context. Invoice OCR is never mentioned as a feature.

---
## 6. Ranked changes to pass 8.5 (from 7.75)
| # | Change | Sub-score gain | Running total |
|---|---|---|---|
| 1 | **Reposition + re-cut the video around the lock** (M1 + M4). Script: 0:00 hook (US-scoped AFP + IC3 advice) → 0:20 inputs + 20 s plan → **Beat A (1:00–2:15):** duplicate blocked; "new IBAN" email quarantined with evidence (lookalike domain, new country, urgency); callback by a second user to the pre-existing vendor-master number; approval packet shown; the other bills execute live. → **Beat B (2:15–3:30):** German SWIFT SENT→FAILED `BENEFICIARY_NAME_MISMATCH`; corrected details hit **the same lock** (T2 + callback); replacement under a new `request_id`, original's fate recorded, PROVISIONAL badge. → **Beat C (3:30–4:30):** `financial_transactions` tie-out per currency, every row linked, journal CSV. → 10 s close card. | C5 5→7 (+0.20), C4 6→7 (+0.20) | **8.15** |
| 2 | **Fix the demo contradictions and disclose fixtures on screen** (M2, M3 labels, M5 fallback): #1 under the T0 limit or shown going to T1; seeded payee history labelled with its production source (`GET /transfers`); "Name check not available in sandbox; production: `verify_account`"; the honest residual line. | C4 7→8 (+0.20) | **8.35** |
| 3 | **Enforce the out-of-band callback in code, and sign approvals with a passkey** (M3 + S2): verifier ≠ requester ≠ ingester, callback number from a vendor record older than the change request, cooling-off and first-payment cap, approver signs the packet hash via WebAuthn (a real signature, so "cryptographically bound" becomes true). | C3 9→10 (+0.20), C5 7→8 (+0.10) | **8.65** ✅ |
| 4 | **Stat hygiene + cite the control's provenance** (S1): US-scoped AFP 2026, drop or verify the 63% wires figure, APQC "disbursements", add the IC3 "secondary channels" line as the reason the lock exists. | C1 8→9 (+0.25) | **8.90** |
| 5 | **Day-1 spike results published in the repo** (M5, S3): `financial_transactions` row latency, failed-transfer refund/fee rows, `GET /transfers?request_id=`, webhook event names, SEPA VoP behind a flag. Keeps C2 at 9 by removing the downside; webhooks HMAC-verified live on camera could make it 10. | C2 risk removed (+0.25 possible) | **8.90–9.15** |

**The single change that matters most:** #1. Until the title, track field and video lead with "no payout reaches an un-countersigned destination", and show it firing on the recovery path too, a judge files Countersign under "kit 1 + kit 3, well engineered".
