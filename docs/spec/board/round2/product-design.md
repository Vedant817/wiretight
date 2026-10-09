# Round 2: Product & Design (demo + UX lens) on SPEC-v1
*Written Thu 8 Oct 2026, ~7:40 PM IST.*

**Version history:**
- v3 applies the Red-Team Judge (`round2/judge.md`), D5–D7 (Compliance defaults) and R2-CEO, all in `DECISIONS.md`.

**Inputs:**
- `board/SPEC-v1.md` (all of it) and `DECISIONS.md` (D3, F7, D5, D6, D7, R2-CEO)
- `round1/judge-scores.md`, `round1/staff-engineer-feasibility.md`, `round1/banking-domain-realism.md`
- `round2/judge.md` and `round2/compliance-risk.md` (defaults table and Bill #1 / demo sections)
- `raw/doc_tstatus.txt` and `raw/doc_failure_types.txt`
- the guide, re-fetched today

*Greenfield. Nothing submitted, nobody contacted.*

**House rules for this file:**
- **Name.** The product is **[PRODUCT]**, a single find-and-replace token. It becomes **Wiretight** if the board adopts the CEO's pick; see `round2/names.md`.
- **Verb.** **"sign-off"** is used everywhere: voiceover, UI and application text. We don't use "approve" or "countersign". The UI card is the **sign-off card**.

**The guide's demo bar** (re-checked Oct 8, [airwallexdev.com/guide](https://airwallexdev.com/guide)):
> *"show the user's goal, the agent's initial plan, the new information, the revised decision, and the resulting balance, payment, or status… Finish the demo with a financial action or an escalation to a person."*

**The rule the video sells:** *No payout reaches a bank account a human hasn't signed off on exact terms.*

**Video structure:** a cold open on the lock, then 3 beats (Judge cap).
- **Beat A, Fraud:** the lock fires on a fake "new IBAN" email.
- **Beat B, Fix:** the supplier's SEPA account is closed, the payout returns, and the supplier then sends a legitimate new account. That new account is lock fire #2, with a callback, a cooling-off hold, dual sign-off and the first-payment cap.
- **Beat C, Proof:** the tie-out.
- **Close:** a shadow-mode "would have caught" slide of 10 s or less. It's a closing line, not a fourth beat.

**Airtime limits:**
- Planning: 15 s or less.
- Deposit re-plan: 0 s on video.
- "PAID isn't final": one line.
- Invoice reading: never narrated.

**Failure code (D8, docs-only, not live-tested).** Both candidates are documented `failure_type` values on `POST /api/v1/simulation/transfers/{id}/transition`, and the sandbox guide maps them to a returned `failure_reason` when you simulate FAILED (Docs MCP, Oct 8 2026; also `raw/doc_failure_types.txt` and `raw/doc_transfer.txt`):
- **Primary: `ACCOUNT_CLOSED`** → documented response `90701: Account closed`. This is the story: the account on file no longer exists.
- **Fallback: `BENEFICIARY_BANK_RETURNED`** → documented response `90802: Beneficiary bank returned`. Same beat if the simulator rejects the primary.
- **Caveats:** no sandbox keys yet, so neither has been simulated live. A chosen failure type applies only after SENT, and FAILED auto-cancels in seconds. The caption always reads back the `failure_type` and `failure_reason` the API actually returned. Never invent one.
- EUR to Germany is **LOCAL over SEPA** (IBAN, fee 0). Docs: local EUR to DE is SEPA Instant / SEPA; over EUR 100,000 or a bank without Instant falls back to SEPA, up to 2 business days. This bill is EUR 7,500, so Instant is the expected scheme. Show `LOCAL · SEPA` on screen, not a wire.

---

## 1. Must-fix / should-fix

### 1a. §11 demo script
| # | Sev | Problem in §11 | Fix (applied in §2) |
|---|---|---|---|
| D1 | **MUST** | It reads as kit 1 + kit 3: 9 beats, plus a deposit re-plan (kit 1) and a failure → replacement (kit 3). Judge M1/M4. | **Cold open on the lock**, then **3 beats** (A fraud, B fix, C proof). Planning gets 15 s or less (CEO). The deposit re-plan, re-quote void, FX baseline and eval metrics move to the README. |
| D2 | **MUST** | The lock is buried. #5 is quarantined before any plan exists. | The change email lands **after #2 has been signed off**. The packet holds `bank_fingerprint` (§6.2), so the sign-off goes **VOID** on screen, only #2 re-plans, and the executor logs a HARD BLOCK. |
| D3 | **MUST** | The recovery flow copies kit 3 and is a BEC vector (Judge S7). D8 also makes the rail and the failure realistic. | Beat B: the on-file account pays **LOCAL over SEPA**. After SENT it fails `ACCOUNT_CLOSED` (fallback `BENEFICIARY_BANK_RETURNED`). The supplier's legitimate new account then goes through **the same lock**, with every D7 control: callback by a separate **ops** user to a contact 30+ days old and older than the change; **cooling-off** (72 h in policy, **2 min in the demo, labelled**); **dual passkey sign-off**; **first-payment cap** (tranche 1 about USD 2,500 paid, tranche 2 **held**). |
| D4 | **MUST** | It contradicts policy. #1 at USD 4,200 auto-pays despite a 2,000 limit (Judge M2). | Per D6/D7, #1 is **USD 1,800** and goes out under T0. The seeded history **1,500 / 1,650 / 1,800** carries a `FIXTURE · prod source: GET /transfers + ledger` tag, plus `demo policy: T0 on` (T0 is OFF by default, D7). Nothing pays above a limit. |
| D5 | **MUST** | The out-of-band check is a checkbox (Judge M3, Compliance M6). | The screen shows code enforcement: callback contact age and provenance, and any number found in the change email rejected. The requester can't record the callback. The callback recorder is a **separate ops user who isn't a signer** (D6). |
| D6 | **MUST** | The five guide elements aren't labelled. | Corner chips `GOAL` · `INITIAL PLAN` · `NEW INFO` · `REVISED DECISION` · `RESULT` inside the 3 beats. |
| D7 | **MUST** | A live "0 residual" is untested (Judge M5). | The tie-out screen has designed **explained** and **unexplained** residual states (§3.4). No staged zero. |
| D8 | **MUST** | `verify_account` and PAID→FAILED behaviour in the sandbox is unknown. | Neither is a beat. On-screen note: *"Name check (Verification of Payee): not available in the sandbox demo. Production: `POST /beneficiaries/verify_account`."* PAID→FAILED appears as one line plus a `PAID · provisional` badge (§2 Constraints). |
| D9 | **MUST** | Sign-off is just a click. | Each signer **signs off the packet hash with a passkey** (WebAuthn, D5) on camera. The fallback is a per-signer HMAC key, labelled "integrity-bound" (D5). |
| D10 | **MUST** | The CEO wants the video to open with the lock and to show shadow mode. | 8 s cold open on the VOID moment. Shadow-mode "would have caught" is the 10 s closing slide. |
| D11 | **MUST** | Timing: 4:55 planned, no buffer. | **4:07 planned, 53 s buffer.** Running totals in §2. |
| D12 | SHOULD | Stats are overgeneralised. | "74% of US organisations (AFP 2026, n=465)", plus the FBI IC3 advice to verify account changes through a second channel. |
| D13 | SHOULD | Simulations and fixtures aren't labelled. | Grey tags: `sandbox simulation`, `synthetic email`, `FIXTURE`, `demo timing`. |
| D14 | SHOULD | `failure_type` can be lost when FAILED auto-cancels. | Use a 1 s poll or a webhook during beat B, and store the reason on first read (Staff M4). |
| D15 | SHOULD | No retake path. | `run_demo.py --replay`: seeded, resettable. Record 2–3 takes. |
| D16 | NICE | Hard to read. | Masked accounts, amounts at 28 pt+, one colour system (§3). |

### 1b. §15 HackerEarth application text
| # | Sev | Problem | Fix |
|---|---|---|---|
| A1 | **MUST** | Uses the dropped name, and "approve/countersign" verbs. | `[PRODUCT]` everywhere. **"sign-off"** as the verb (R2-CEO). |
| A2 | **MUST** | Title "never pays twice", track "kit 1 + kit 3", and a tagline that lists 5 features. | Lead with the lock. Track: "Treasury & Ops, original idea (payee-change control + reconciliation); borrows kit 3's no-double-pay discipline" (Judge M1). |
| A3 | **MUST** | Claims spikes are "done before the build phase". There are no sandbox keys, and R2-Staff M1 allows no project code before Oct 25. | Claim only what's true on the day you submit. |
| A4 | SHOULD | "Cryptographically bound" overclaims for a plain hash. | "Signed off with each signer's passkey over a hash of the exact terms" (D5). If the passkey slips: "integrity-bound". |
| A5 | SHOULD | Too many stats, plus `verify_account`, Ledge and "20–300 suppliers" (unsourced). | At most 2 stats: AFP 2026 74% (US) and APQC 1.5% ("disbursements"). Remove `verify_account`, Ledge and the unsourced range (R2-CEO). |
| A6 | SHOULD | "50-scenario harness" reads as done. | "Will publish": it's a plan (20 scenarios per Staff). |
| A7 | NICE | Metal anchoring is in the stack line. | Drop it. It's cut (D6). |

### 1c. Revised §15 text (drop-in)
**Title:** [PRODUCT]: no payout reaches a bank account a human hasn't signed off

**Track:** Treasury & Ops, original idea: payee-change fraud control plus landed-payment reconciliation (no starter kit covers either). Borrows kit 3's no-double-pay discipline.

**Tagline (≤25 words):** Your supplier payment run, with a lock: any new or changed bank account freezes the payment until a second person verifies it and two people sign off.

**Short description (~75 words):**
Small finance teams pay overseas suppliers weekly from inboxes and bank portals. One "our bank details have changed" email can redirect a payment. [PRODUCT] runs the payment run on Airwallex, and **no payout reaches a bank account a human hasn't signed off on exact terms**. That holds for a fraudster's new IBAN and for a supplier's genuine correction after a returned payment. Someone else verifies by calling back on the number already on file. Every payment is tracked until it lands, then reconciled.

**Full description (~210 words):**

*Problem.*
- In AFP's 2026 survey, 74% of US organisations were hit by business email compromise. The FBI advises verifying any account-change request through a second channel.
- APQC benchmarks put duplicate or erroneous disbursements at a 1.5% median.
- In a 40-person company, one person carries all of this, every week.

*The lock.*
- Each sign-off is a passkey signature over a hash of the exact payee, bank account, amount, currency, FX quote and evidence.
- If the bank details change, even after sign-off, the signature no longer matches. The payment freezes and the executor refuses to send it.
- Paying new or changed details requires:
  - a recorded callback, by a separate ops user, to a supplier contact that predates the change;
  - a cooling-off period;
  - two sign-offs;
  - a capped first payment, with the rest held until the first one lands.
- The same lock covers a supplier's genuine new account after a payment returns because the old account was closed. Recovery is where redirection fraud hides.

*The proof.*
- PAID is treated as provisional, because Airwallex documents failures after PAID.
- Every wallet movement ties out per currency against Airwallex financial transactions. Any residual is shown and explained, and a journal is exported.
- Teams start in shadow mode: [PRODUCT] moves no money and reports what it would have caught.

*Division of labour.* An LLM reads bills and emails and explains anomalies. Code decides amounts, plans, limits and state.

*Airwallex APIs:* balances, FX quotes and conversions, beneficiaries (schema, validate, create), transfers and status events, financial transactions, balance history, sandbox simulations.

**Long-description additions (only if a field exists):**
- Policy floors: auto-pay off by default, and capped when enabled; dual sign-off for any bank change or replacement; daily, per-payee and per-signer caps; a kill switch.
- Bills come in from email or PDF; a journal CSV goes out.
- Will publish a seeded eval: double-pays, floor breaches, unverified bank-change payments, reconciliation residual.
- Builder: solo developer from India. *[State the sandbox spike status truthfully on the day.]*

**Stack:** Python, FastAPI, SQLite, HTMX, WebAuthn passkeys, Airwallex REST + Docs MCP, hosted LLM, cloudflared for webhooks.

---

## 2. Revised §11 demo script: cold open + 3 beats, planned 4:07 (cap < 5:00)
**Scenario:** §10 Halden Robotics: USD wallet, seed USD 25,000, reserve floor USD 8,000. These changes apply:
- **#1 is USD 1,800** (D6/D7).
- **#5, the bank-change email, is not in the opening inbox.** It lands mid-beat-A.
- **The failing transfer is #2**, the German supplier, paid **LOCAL over SEPA** (not a wire; fee 0). One supplier carries both lock firings.
- **No scripted figures.** USD equivalents, rates and the tranche-1 EUR amount all come from the live sandbox quote.

**Cast (D6):**

| Person | Role | Signs off? |
|---|---|---|
| Arun | AP clerk / requester | Never |
| Meera | Finance lead | Yes |
| Kabir | Founder | Yes |
| Priya | Ops | No. She only records callbacks |

All four are synthetic.

| Beat | Time | Dur | Running | Guide label | On screen | Traces to |
|---|---|---|---|---|---|---|
| Cold open | 0:00–0:08 | 8s | 0:08 | – | The sign-off card for #2 flips to **VOID: bank_fingerprint changed**. VO: "This payment was signed off. Then the bank details changed." | Spec §6.2 |
| Hook | 0:08–0:18 | 10s | 0:18 | – | VO: "In AFP's 2026 survey, 74% of US organisations were hit by business email compromise. The FBI says to verify account changes through a second channel. We built that into the payment run." | `01` P1 (verified); IC3 via Judge |
| **A · Fraud** | 0:18–0:26 | 8s | 0:26 | **GOAL** | Banner: *"Pay this week's bills on time, once, to the real supplier, never below USD 8,000."* Live balances shown. | `GET /balances/current` (seed deposit runs off-camera, tagged) |
| | 0:26–0:41 | 15s | 0:41 | **INITIAL PLAN** | The only treasury segment:<br>• #1 USD 1,800: **auto (T0)**, with tags `history 1,500/1,650/1,800 · FIXTURE` and `demo policy: T0 on`<br>• one GBP conversion for #3 and #7 (LOCAL)<br>• #2 EUR 7,500 **LOCAL · SEPA** (fee 0)<br>• #6 DEFER (floor)<br>• #4 duplicate, HARD BLOCK | `GET /fx/rates/current`, `POST /fx/quotes/create`; spec §4.3; D6/D7 |
| | 0:41–0:57 | 16s | 0:57 | – | Meera taps **Sign off with passkey** on the #2 card and the GBP card. The OS passkey sheet appears, then "Signed off ✓". The executor sends #1, #3 and #7: GBP conversion, transfers, `SENT`. #2 waits, because EUR converts just in time. | `POST /fx/conversions/create`, `POST /transfers/create`, transition SENT (tagged) |
| | 0:57–1:09 | 12s | 1:09 | **NEW INFO** | Email arrives (`synthetic email`): "New bank account for INV-2291, urgent before Friday." Lookalike domain, LT IBAN. | Spec S2; fixture |
| | 1:09–1:39 ★ | 30s | 1:39 | **REVISED DECISION** | **Lock fires (1 of 2).** #2 goes **VOID**. The incident view shows:<br>• the fingerprint diff<br>• the evidence: lookalike domain, new country, urgency, and an invoice PDF that still carries the on-file IBAN<br>• `beneficiaries/validate` = **VALID**, labelled "valid ≠ legitimate"<br>• the note *"Name check not available in sandbox demo"*<br>The plan diff shows only #2 → BLOCKED, with the EUR conversion withdrawn unbooked. The executor logs `HARD BLOCK`. | Spec §4.2, §6.1–6.2; `POST /beneficiaries/validate` |
| | 1:39–2:02 | 23s | 2:02 | **RESULT** | Arun's "Record callback" is blocked. Priya (ops) calls the vendor-master contact (`FIXTURE`, created 14 months before the request; numbers found in the email are rejected). Result: "no change made", and the change is **REJECTED**. Meera signs off #2 by passkey to the **on-file** account. EUR quote, conversion, **LOCAL · SEPA** transfer, `SENT`. Caption: **"Fraudulent IBAN: never paid."** | `/fx/quotes/create`, `/fx/conversions/create`, `/transfers/create`, transition SENT |
| **B · Fix** | 2:02–2:12 | 10s | 2:12 | **NEW INFO** | #2 (LOCAL · SEPA) goes SENT → **FAILED `ACCOUNT_CLOSED`** (`sandbox simulation`; caption = the returned `failure_reason`), then CANCELLED. The original's outcome is recorded. | `POST /simulation/transfers/{id}/transition` + `failure_type`; `GET /transfers/{id}` |
| | 2:12–2:57 ★ | 45s | 2:57 | **REVISED DECISION** | **Lock fires (2 of 2).** Banner: "Account closed. The supplier's new account is a new destination. Same lock."<br>1. The supplier sends a legitimate new DE IBAN (`synthetic email`, same known domain).<br>2. Priya (ops) calls the older vendor-master contact and the supplier confirms the closure and the new account.<br>3. New beneficiary version, new fingerprint. Method stays **LOCAL · SEPA**.<br>4. **Cooling-off countdown 2:00**, labelled `demo timing · policy 72 h`. Jump cut, labelled.<br>5. Fresh quote, then **dual passkey sign-off** (Meera + Kabir). The card shows `Callback ✓ Priya` and `Cooling-off ✓`.<br>6. **First-payment cap:** tranche 1 about USD 2,500 at the locked quote, paid; tranche 2 **HELD until tranche 1 FINAL**.<br>"Replace" is enabled only because the original is CANCELLED. | Spec §4.7 (`ACCOUNT_CLOSED` playbook = new details + dual sign-off); D7; D8; `POST /beneficiaries/create` |
| | 2:57–3:22 | 25s | 3:22 | **RESULT** | Tranche 1 goes out with a new `request_id` and a `replaces` link: `SENT`, then `PAID · provisional`. One VO line: "Airwallex documents failures even after PAID, so it stays provisional until the SEPA return window passes." (D8: FINAL is set by the per-rail window, not a timer.) Tranche 2 stays amber, **HELD**. A supplier note is drafted, not sent. | `/transfers/create`, transition SENT→PAID (tagged) |
| **C · Proof** | 3:22–3:57 | 35s | 3:57 | **RESULT (balance/status)** | Tie-out per currency: opening + in − out − fees + return refunds (less any retained fee, D8) = closing = live balance. **Residual 0.00, or the residual with its explanation (§3.4).** Status board:<br>• paid-provisional<br>• #2 original returned; tranche 1 paid; tranche 2 held<br>• #6 deferred<br>• #4 blocked<br>• change request REJECTED, never paid<br>Journal CSV. | `GET /financial_transactions`, `GET /balances/history`, `GET /balances/current` |
| Close | 3:57–4:07 | 10s | **4:07** | – | **Shadow-mode slide**: "Start in shadow mode. It moves no money and tells you what it would have caught." The report rows come from *this demo run* (labelled synthetic): 1 changed-IBAN request frozen, 1 duplicate blocked, 1 returned payment routed through the lock. Repo URL. | CEO R2; spec §14 |
| | | | **4:07 total** | | **53 s buffer** under the 5:00 cap | |

**Treasury airtime:** planning 15 s (0:26–0:41) plus deposit re-plan 0 s, so 15 s in total. That meets the CEO's 15 s limit and the Judge's 20 s limit. "PAID isn't final" gets one line, at 2:57. Invoice reading is never narrated.

**Voiceover for the key moments:**
- **Beat A, 1:09:** "This payment was already signed off. Then this email arrives: new account, urgent. The details are perfectly valid, and that's the point. The sign-off was for *the old account*, so it's void. Nothing moves until someone who didn't make the request calls the supplier on the number we already had."
- **Beat B, 2:12:** "The payment went out over SEPA, and the account is closed. The money comes back. Then the supplier sends a new account, which is exactly where redirection fraud hides. So the new account goes through the same lock: a callback, a cooling-off period, two sign-offs, and a capped first payment. Recovery gets no shortcuts."

**If a take runs long, cut in this order:**
1. Hook down to 6 s.
2. 0:41–0:57 down to 10 s.
3. Shadow slide down to 6 s.

Never cut either ★ segment or beat C.

### Constraints and fallbacks
- **Failure code for this bill:** primary `ACCOUNT_CLOSED`, fallback `BENEFICIARY_BANK_RETURNED`. Both are in the simulator's `failure_type` enum and both have a documented `failure_reason` (see the header). The day-1 spike confirms which one the sandbox accepts after SENT.
  - Caption = the `failure_type` and `failure_reason` actually returned (expected `90701: Account closed`, or `90802: Beneficiary bank returned` on the fallback).
  - If FAILED works but no reason survives the auto-cancel, the incident reads "failure type: not returned by sandbox" and is tagged **"reason not returned by sandbox"**. The operator does not type a reason in. We never caption one Airwallex didn't send.
  - The earlier name-mismatch idea is an eval case only (D8). It is not this bill.
- **`verify_account`:** never a beat, and the on-screen note stays. If the spike shows a usable SEPA VoP result, it can appear as a read-only chip. It never lowers the tier or removes the callback (Compliance T-14).
- **PAID→FAILED:** never shown live. It appears as the `PAID · provisional` badge and one VO line. If the spike shows it's accepted, beat B's trigger can move to an already-PAID transfer at the same length. Otherwise it stays a fixture test in the README.
- **Cooling-off (2 min):** a demo override that only loads in the sandbox, labelled `demo timing · policy 72 h` (Compliance defaults). FINAL is **not** shortened on camera. D8 sets FINAL by the per-rail window (SEPA return window ≥ 3 business days), so tranche 1 stays `PAID · provisional`.
  - In the video the countdown is jump-cut, labelled.
  - The fresh quote is taken **after** cooling-off, so no quote is booked with less than 120 s of validity left (D7).
  - Tranche 2 stays HELD for the whole video, because tranche 1 isn't FINAL yet. That's correct behaviour, not a gap.
- **Passkey:** a WebAuthn assertion with the packet hash as the challenge, on localhost (D5).
  - If the screen recorder can't capture the OS sheet, show the "Signed off ✓ passkey · credential …" row with a caption.
  - If the passkey work slips, fall back to a per-signer HMAC key, labelled "integrity-bound".
- **Fixtures, said out loud:** the change email, payee history, the vendor-master contact and the four users are all fixtures, each tagged. The callback is a human act the product *records*; it can't prove the call happened.

---

## 3. Key screens (ASCII wireframes)
**Colours and states:**

| Colour | States |
|---|---|
| green | `FINAL`, residual 0.00, Signed off ✓ |
| blue | `SENT`, `PAID · provisional` |
| amber | `NEEDS SIGN-OFF`, `QUARANTINED`, cooling-off, `HELD` tranche, residual explained |
| red | `VOID`, `HARD BLOCK`, `REJECTED`, residual unexplained |
| grey | `DEFERRED`, `FIXTURE`, `demo timing`, `sandbox simulation` |

PNG renders sit next to this file (`screen-*.png`). Every name, IBAN fragment, domain, number and date in them is a **synthetic placeholder**.

### 3.1 Sign-off card (beat B state: dual sign-off, callback, cooling-off, tranches)
```
┌─ SIGN-OFF CARD ─ #2 replacement ───────── [ NEEDS SIGN-OFF · DUAL ] ┐
│ Brandt Zerspanung GmbH · INV-2291 · replaces tr_… (CANCELLED ✓)      │
│ LOCAL · SEPA · fee 0 · To DE•• •••• 7740 · fingerprint 4c07… (NEW)   │
│ Callback   ✓ Priya (ops) · contact on file 14 mo · not from email    │
│ Cooling-off ✓ 0:00 left  [demo timing · policy 72 h]                 │
│ First-payment cap (new details): min(USD 2,500, 50% of median)       │
│   Tranche 1  EUR ‹live quote ≈ USD 2,500›  → pays now                │
│   Tranche 2  EUR ‹remainder›  HELD until tranche 1 FINAL             │
│ FX quote q_… · rate (live) · ≥120 s validity left                    │
│ Packet hash 9a41…  ·  expires min(4 h, quote − 120 s), single use    │
│ Signer 1  Meera   [ Sign off with passkey ]  → Signed off ✓ cred …9f2│
│ Signer 2  Kabir   [ Sign off with passkey ]  → Signed off ✓ cred …1c7│
│ Not allowed: Arun (requester) · Priya (callback recorder)            │
└──────────────────────────────────────────────────────────────────────┘
 Beat A variant: single signer · "History 1,500/1,650/1,800 [FIXTURE ·
 prod: GET /transfers + ledger]" · later  [ VOID · bank_fingerprint changed ]
```
*What this proves to judges:*
- Each sign-off is a passkey signature over the exact terms.
- Every Compliance control is visible on one card: callback, cooling-off, two signers, first-payment cap.
- Separation of duties is explicit.
- Fixtures are labelled together with their production source.

### 3.2 Plan diff (beat A)
```
┌─ PLAN r_118 · floor USD 8,000 · [ REVISED DECISION ] ───────────────┐
│ item   payee          before                  → after               │
│ #1     US forwarder   PAY 1,800 · auto T0     = SENT                │
│                       [demo policy: T0 on]                          │
│ #2     Brandt GmbH    EUR 7,500 LOCAL · SEPA  → BLOCKED: quarantine │
│  fx    USD→EUR        1 conversion            → withdrawn, unbooked │
│ #3/#7  UK payees      GBP conv + 2× LOCAL     = SENT                │
│ #4     UK (dup)       HARD BLOCK              = HARD BLOCK          │
│ #6     US SaaS        DEFER (floor)           = DEFER               │
│ Re-opened 1 of 6 · cause: change request e_77 (synthetic email)     │
└─────────────────────────────────────────────────────────────────────┘
```
*What this proves:* new evidence flipped exactly one decision, and auto-pay stays inside policy.

### 3.3 Incident view: the bank-detail-change lock ★
```
┌─ INCIDENT · change request · Brandt Zerspanung GmbH  [ QUARANTINED ] ┐
│ ON FILE                                │ REQUESTED (email, 2d pre-due)│
│ IBAN DE•• … 3001                       │ IBAN LT•• … 8820      [diff] │
│ Country DE                             │ Country LT            [diff] │
│ Domain brandt-zerspanung.example       │ brandt-zerspanunq.example    │
│ Why held (rules decide · AI explains, unverified):                   │
│  • fingerprint changed • new country • look-alike domain • "urgent"  │
│  • invoice PDF still shows the ON FILE IBAN                          │
│ Format  beneficiaries/validate: VALID   ← valid ≠ legitimate         │
│ Name check (VoP): not available in sandbox demo                      │
│                   prod: POST /beneficiaries/verify_account           │
│ Sign-off #2: VOID     Executor: HARD BLOCK logged 14:31:07           │
│ ── OUT-OF-BAND CALLBACK ─────────────────────────────────────────────│
│ Contact: vendor master +49 ••• 4410 · created 14 mo before request   │
│   [FIXTURE · prod: your vendor master / ERP]  numbers in email: ✗    │
│ Arun (requester): ✗ blocked    Priya (ops, non-signer): allowed      │
│ Outcome (•) change NOT made  ( ) change confirmed                    │
│ [ Record callback ] → REJECTED · re-sign-off ON FILE account         │
└──────────────────────────────────────────────────────────────────────┘
 Firing 2/2 (after ACCOUNT_CLOSED on the LOCAL · SEPA payout): same
 screen + banner "Account closed. Supplier's new account = new destination.
 Same lock." New IBAN is DE (same country, known domain). Callback ✓ ·
 cooling-off countdown 1:47 [demo timing · policy 72 h] · dual passkey
 sign-off · tranche 1 ~USD 2,500 pays · tranche 2 HELD.
```
*What this proves:*
- The lock is evidence plus enforced human control, not a checkbox (Judge Q2/Q3).
- A valid format doesn't release money.
- Both firings use the same screen, so judges learn it once.

### 3.4 Tie-out with designed residual states
```
┌─ TIE-OUT r_118 · source GET /financial_transactions ─ [ STATE ] ─────┐
│ ccy  opening +in  −out  −fees +refunds = closing │ live bal │ resid  │
│ USD    …      …    …     –      –          …     │    …     │  0.00  │
│ EUR    0      …    …     …      …          …     │    …     │  ?     │
│ GBP    0      …    …     –      –          …     │    …     │  0.00  │
│ #1 #3 #7 PAID·prov · #2 SEPA returned ACCOUNT_CLOSED (CANCELLED)     │
│ #2 tranche 1 PAID·prov · tranche 2 HELD (not a wallet movement yet)  │
│ #4 BLOCKED dup · #6 DEFERRED · change e_77 REJECTED (never paid)     │
│ [ Download journal CSV ]                                             │
└──────────────────────────────────────────────────────────────────────┘
 STATE = one of:
 [ RESIDUAL 0.00 ✓ ]   green, every row matched to a transfer/conversion/fee
 [ RESIDUAL EXPLAINED ] amber, e.g. "EUR ‹x›: return on #2 (ACCOUNT_CLOSED)
     refunded less a retained/third-party fee (row ft_…)" or "rows pending:
     tied out from transfer/conversion objects (fin. txns lagging)"
 [ RESIDUAL UNEXPLAINED ] red, run stays OPEN, exception raised to Meera
```
*What this proves:*
- Landed-payment proof. A held tranche is shown as an obligation, not as cash that moved.
- The screen stays honest if the sandbox doesn't tie out (Judge M5).
- The residual examples are categories, not known sandbox behaviour.

---

## 4. Risks and open questions
**Staff Engineer**
1. **Demo blocker: no payee-change entity.**
   - Spec §4.1 only types `InvoiceDraft`. It needs a `PayeeChangeRequest` entity.
   - `payee_version` needs a `REJECTED` state.
   - `obligation` needs tranche rows for the first-payment cap (parent obligation → tranche 1/2, with a `held_until` condition).
2. **Executor order.**
   - Convert just in time, one currency at a time: GBP first, EUR when #2 executes.
   - Quote only after cooling-off.
   - Never book a quote with less than 120 s of validity left (D7).
3. **Day-1 spike: questions it must answer.**
   - Does the sandbox accept a **DE · EUR · LOCAL (SEPA)** beneficiary? Run `POST /beneficiaries/schema` and then `validate`. The hackathon guide's worked examples cover only US/GB LOCAL and EUR/GBP SWIFT ("Other corridors use different beneficiary fields, so check the schema first"), but Airwallex docs list Local EUR to DE via SEPA Instant / SEPA with an IBAN. If DE LOCAL won't create in the sandbox, pick another SEPA country the schema accepts (e.g. NL or FR IBAN), label the change, and never fall back to a wire silently.
   - Are `ACCOUNT_CLOSED` and `BENEFICIARY_BANK_RETURNED` accepted after SENT on a LOCAL EUR transfer, and is `failure_reason` still readable after the auto-cancel?
   - Is PAID→FAILED accepted?
   - How quickly do `financial_transactions` rows (FEE, payout failure) appear?
   - Does a failed LOCAL (SEPA) payout refund the principal, and does any fee row appear? LOCAL is documented as fee 0.
   - What does `verify_account` return?
4. **Passkey.**
   - WebAuthn on localhost, with the challenge set to the packet hash.
   - Can the screen recorder capture the OS sheet?
   - The executor verifies each assertion against the roster's public keys (D6).
5. **Fixtures.**
   - 4 seeded identities.
   - `seed_history.py`: payee #1 at 1,500 / 1,650 / 1,800 FINAL, written into our ledger only and labelled.
   - The German supplier's history, which is needed for the 50%-of-median cap input. *Open:* exact seed values, which must keep tranche 1 at ≤ USD 2,500.
   - A vendor contact with `created_at` set 30+ days before the request.
   - Demo-timing overrides that only load in the sandbox.
   - A `--replay` mode.

**Compliance & Risk**
1. **Re-sign-off after a rejected change (beat A).** Is a single sign-off enough to pay the *unchanged* on-file account after an attempted fraud, or should it go to dual?
2. **Supplier relations.** Tranche 2 is held until tranche 1 is FINAL (48 h in policy). Should the drafted supplier note explain the partial payment, and who sends it?
3. **Shadow-mode slide wording.** The "would have caught" rows come from this demo run (synthetic). Confirm that "would have caught" makes no claim about real data.
4. **Callback honesty line.** Confirm "records evidence of a call, can't prove it" is stated in the README and in the voiceover or a caption.
5. **Fraud alert.** Should a REJECTED fraudulent change trigger a drafted internal fraud alert for a human to send?

**Spec items that block the demo as written:**
- **(a)** #5 is in the opening inbox (§10/§11).
- **(b)** There's no `PayeeChangeRequest`, `REJECTED` state, or tranche model (§4.1, §8).
- **(c)** #1 at USD 4,200 contradicts T0. Fixed by D6 but still in §10/§11.
- **(d)** Passkey sign-off, cooling-off and the first-payment cap are absent from spec §6. D5–D7 add them.
- **(e)** The re-quote-void beat depends on sandbox quote movement, which we can't control.
- **(f)** PAID→FAILED and a live 0.00 tie-out can't be promised; both have designed fallbacks.
