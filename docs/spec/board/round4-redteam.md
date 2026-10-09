# Round 4: red-team of FINAL.md draft v0.1 (Judge · Compliance & Risk · Staff Engineer)

*Written Fri 9 Oct 2026, ~10:30 PM IST, by Grok Bot running the three Round 4 lenses (the board's planned Round 4 never ran).*
*Input: `board/FINAL.md` draft v0.1 (554 lines), checked against `board/DECISIONS.md` (D0–D9 and every R2-* entry, which are authoritative), `board/round2/*.md`, `board/SPEC-v1.md`, and the research pack.*
*Output: every finding below is applied in `board/FINAL.md` **v1.0** (locked). Nothing was run against a live sandbox; no account or keys exist yet (OPEN-3). Scores are paper scores against a provisional rubric, not results.*

---

## 0. Summary

| Lens | Findings | Blocking | All fixed in v1.0 |
|---|---|---|---|
| Judge | 7 | 2 | ✅ |
| Compliance & Risk | 10 | 3 | ✅ |
| Staff Engineer | 11 | 3 | ✅ |
| Consistency (DECISIONS, D7/D8/D9, R2-SeniorDev, greenfield) | 9 | 0 | ✅ |

**The biggest finding:** v0.1 stopped at §4.17. Everything an autonomous builder needs after the policy (architecture, stack and pins, repo tree, env vars, sandbox setup, endpoint list, data model, state machines, tests, eval, day-1 spike, milestones, demo script, README and video requirements) was missing, though v0.1 referred to it (§5.3, §9.5, §14.4, Appendix A). v1.0 adds §5–§15 and Appendices A–C, taken from the Round 2 memos with the corrections below.

**Judge score (provisional rubric F5: C1 pain + decision 25 · C2 API depth 25 · C3 safety 20 · C4 reproducible demo 20 · C5 originality + adoption 10; any unapproved money path caps the total at 4):**

| | C1 | C2 | C3 | C4 | C5 | Total |
|---|---|---|---|---|---|---|
| v0.1 draft (before Round 4) | 9 | 9 | 9 | 6 | 8 | **8.30** |
| v1.0 locked (after fixes) | 9 | 9 | 10 | 8 | 8 | **8.90** |

- **Why v0.1 scored 8.30:** stats and positioning were already fixed (C1 9, C5 8). But C4 was 6: there was no demo script or build plan in the document, two bugs would break the demo (C-3 and S-2 below), and the demo could not be re-recorded on the same day without hitting the policy's own caps (J-3). C3 was 9 because the callback recorder's identity was unauthenticated (C-1) and live signing could be automated (C-2).
- **Why v1.0 scores 8.90 and not more:** C2 stays at 9 and C4 at 8 until the day-1 spike turns the ⚠ unverified items (U1–U16) into recorded fixtures. That is the next real gain, and it can only happen from Sun 25 Oct.
- **Cap check:** after fixes, no path moves money or creates a payout destination without a signed packet or a two-signature policy (C-2, C-5). **No cap.**

---

## 1. Judge lens (score against the judging signals)

The signals checked: the guide's "Build around a financial decision" (goal → initial plan → new information → revised decision → result; amounts and limits in code; typed tools; approvals bound to exact terms; finish with an action or an escalation), Sam Waldo's five questions (genuine operator problem; works across markets and currencies; path to adoption; operational foundation; autonomy balanced with control), and the submission rules (working demo, video under 5:00, repo with setup steps).

| # | Sev | Finding | Fix in v1.0 |
|---|---|---|---|
| J-1 | **BLOCK** | No demo script in FINAL.md. The 3-beat script, the 5 guide labels and the airtime limits existed only in `round2/product-design.md`, and that script predates D8 in places. | §12 Demo script: cold open + 3 beats, 4:07 planned, D8 failure (`ACCOUNT_CLOSED` on LOCAL · SEPA, fallback `BENEFICIARY_BANK_RETURNED`), guide labels on screen, cut order, honesty captions. |
| J-2 | **BLOCK** | Beat B showed an "FX quote" on the tranche-1 card, but per §4.11 a replacement reuses the refunded EUR, so no conversion is booked. The card would show a quote that never existed. | §4.5.4 + §12: tranche 1 is sized from the USD-equivalent at the **worse of the indicative rate and the last booked rate** (rounded down) and funded from the refunded EUR. A CONVERSION packet appears only if the refund hasn't landed (U15). The card shows "rate basis", not a quote. |
| J-3 | MAJOR | The policy floor makes repeat takes fail: ≤ 2 runs per IST day, ≤ 3 payments per payee per 24 h (Brandt gets 2 per take), all-tier USD 75k a day (~USD 20k per take), ≤ 5 new beneficiaries a day. A 2nd live take on the same day can hit HARD_BLOCK on camera. The demo policy can't loosen caps (floor). | §12.4 Take plan: **at most one live take per IST day**; rehearsals run in `--replay`; live takes on Sun 8, Tue 10 and Thu 12 Nov (morning). Cap counters include Airwallex's own transfer list, so wiping the local DB doesn't reset them (tested). |
| J-4 | MAJOR | In beat A, the payment to the on-file account straight after a fraud attempt was one sign-off (Compliance open question Q1, never answered). Judges will ask why a vendor under attack gets a lighter control. | New T2 trigger: **the vendor had a change request REJECTED or EXPIRED in the last 30 days**. Beat A's re-sign-off is Meera + Kabir by passkey (+~5 s; buffer is 53 s → 48 s). |
| J-5 | MINOR | SEPA "fee 0" was presented as fact on the card. It is the documented expectation, not a measured value. | The card shows the fee **read from the transfer response**. "0 expected (docs)" is labelled ⚠ until U-checked. |
| J-6 | MINOR | Shadow-mode graduation was "proposed, Round 4 to confirm". | Confirmed as **board defaults** (not industry values): 4 consecutive weekly shadow runs with every disagreement explained and zero unexplained residuals; T0 only via a two-signature policy; automatic demotion. |
| J-7 | NOTE | Application text checked: title 8 words, tagline 24, short 76, full 213, long +342; ≤ 2 stats (AFP 2026 74%, APQC 1.5%); lock-led; future tense; no VoP claim; no build claim. Kept as is apart from one change: "Bills come in from email or PDF" becomes "as structured data, email or PDF", because PDF/LLM ingest is a Week 2 optional item that can be cut. | §3 updated. |

**Judging-signal map (v1.0):**
- Genuine operator problem → §2 (AFP 2026, APQC, FBI IC3 advice).
- Across markets and currencies → USD/EUR/GBP, LOCAL rails per currency, SWIFT with payer fees, holiday calendars.
- Adoption → shadow mode, existing Airwallex account, graduation criteria.
- Operational foundation → idempotency, lookup-before-retry, failure playbooks, tie-out, audit chain.
- Autonomy with control → tiers, policy floor, passkey sign-offs, kill switch.
- The guide's demo elements → labelled chips in §12.

---

## 2. Compliance & Risk lens (controlled autonomy, no unapproved money path, kill switch, passkeys, lock rules)

| # | Sev | Finding | Fix in v1.0 |
|---|---|---|---|
| C-1 | **BLOCK** | The callback record, the lock's key evidence, was attributed to "Priya (ops)" through the **identity switcher alone**. Anyone at the keyboard could record a CONFIRMED callback as Priya. | §4.5.2 rule 7: the ops user **signs the callback record's sha256 with her own passkey** (HMAC fallback labelled). The executor re-verifies that signature like an approval. A test covers a callback row inserted with no valid signature (T-10b). |
| C-2 | **BLOCK** | An automated signing path could exist: the headless demo (`run_demo.py`) and the eval need signatures, and the test-only software authenticator could leak into live runs. Unattended signing of live payouts = an unapproved money path (Judge cap). | §4.8 + §10.1 rule 13: the soft authenticator lives only under `tests/support/`. An import-graph test forbids importing it from `app/` or `scripts/`, and it refuses when `AWX_MODE=live`. Live sandbox signing by the coding agent is allowed **only** through `wiretight sign` with `SIGNING_MODE=hmac_fallback`, recorded as `signed_via=cli_hmac` and shown as "TEST SIGNER (HMAC)". Never in the video, never with passkeys. Video sign-offs are Vedant's passkey gestures. |
| C-3 | **BLOCK** | The PAYMENT packet hashed `beneficiary_id: null until created`. For every new or changed payee, the executor creates the beneficiary, rebuilds the packet with a real id, the hash no longer matches, and the approval voids. That breaks the lock's own happy path (beat B) and tempts a builder to special-case the hash. | §4.7: `beneficiary_id` is **removed from the hashed item**. The packet binds `payee_version_id`, `payee_fingerprint` and `beneficiary_nickname` (`wt-<payee_version_id>`). The executor checks that the created or fetched beneficiary maps to that payee version and fingerprint (U16 fallback below). Test T-04c. |
| C-4 | MAJOR | `seed_sandbox.py` created beneficiaries outside the executor: a destination-creation path with no packet, no halt check and no cap. | §8.6: seeding creates only the **on-file** beneficiaries for seeded vendors. It is audited as `SEED`, counts toward the ≤ 5 new beneficiaries per day cap, refuses to run if any run exists in the DB or if halted, and needs `CONFIRM_LIVE=1`. Every seeded payee is labelled FIXTURE. Seeding moves no money (the deposit is a sandbox simulation). |
| C-5 | MAJOR | Policy signatures: who signs `policy.demo.yaml`, and how does CI get a signed policy? v0.1 was silent, which risks a committed "pre-signed" policy or an unsigned bypass. | §6.4: `make sign-policy` needs two approver passkey gestures (Vedant, NEEDS_HUMAN), or the labelled HMAC fallback. CI generates ephemeral test approver keys and signs `policy.ci.yaml` at setup (test-only). No signature files built from real keys are committed. |
| C-6 | MAJOR | "Process separation" claimed the web process holds no Airwallex key, but one `.env` feeds both processes. That is an overclaim. | §5.3: `WebSettings` and `WorkerSettings` load disjoint key sets. The web process refuses to start if `AWX_API_KEY` is visible in its settings; the worker refuses if `ANTHROPIC_API_KEY` is. An import-graph test checks this. Documented honestly as **logical separation on one laptop, not OS isolation**. |
| C-7 | MINOR | The executor did CAS `APPROVED → EXECUTING` before the halt check, so a halt could strand items in EXECUTING. | §4.8: halt check first; any abort before INTENT reverts the item in the same transaction (to APPROVED, or VOID on a hash mismatch). |
| C-8 | MINOR | SPLIT_SUSPECT used "≥ a tier threshold", which made T-05's expected outcome (1,900 × 3 → T0 then T1) contradict the code (it would be T2). | §4.3: SPLIT_SUSPECT uses the **T2 threshold** (USD 10k). T0 splitting is handled by rows 15/16. T-05 expectations are restated in §10.3. |
| C-9 | MINOR | T-08 (Compliance) expected "T0 items demote to T1" when the daily T0 cap is used, while R2-SeniorDev expected DEFERRED_CAP. Both were treated as one rule. | §4.6: T0 cap headroom < amount → **T1** (r9 `cap_headroom`). All-tier caps → **DEFERRED_CAP**. A breach attempt at the executor → **kill-switch trip** (r29). |
| C-10 | NOTE | Honest limits are stated in the README: anyone at the keyboard can trip the kill switch (fail-closed, acceptable); the audit signing key sits on the same laptop; a callback record is evidence of a call, not proof; screening is a stub; the passkey is not a legal e-signature. | §11 README requirements. |

**Unapproved-money-path sweep (v1.0):**
- `transfers/create`, `fx/conversions/create` and `beneficiaries/create` are reachable only from `app/workers/executor.py` (import-graph test plus an HTTP-boundary test).
- Every call needs a verified packet, or T0 under a two-signature policy.
- The seed path creates on-file beneficiaries only, with no transfers, and is audited.
- Sandbox simulations exist only in `SandboxSimulator`, which can't be built unless `AWX_ENV=sandbox`.
- `POST /rfis/{id}/respond` is never called by workers.

**Result: no unapproved path.**

---

## 3. Staff Engineer lens (feasibility for one autonomous coding agent, Sun 25 Oct → Fri 13 Nov)

| # | Sev | Finding | Fix in v1.0 |
|---|---|---|---|
| S-1 | **BLOCK** | FINAL.md was not self-contained (truncated at §4.17). | §5–§15 + Appendices A–C written inline: architecture, pins, tree, env, setup, endpoints, data model, state machines, Makefile/CI essentials, tests, eval, spike, plan, demo, README/video, application text. |
| S-2 | **BLOCK** | Senior Dev's reference-charset regex `[A-Za-z0-9 -/.]` has an unescaped hyphen. It reads as the range space–slash, which lets `!"#$%&'()*+,` through. FINAL §4.3 had the correct `^[A-Za-z0-9 ./-]{1,35}$`, but the R2 prompts carried the bad one. | One canonical regex in §4.3 and in the prompt; T-03 includes `INV-1; DROP TABLE` and `A,B` cases. |
| S-3 | **BLOCK** | Two conflicting milestone plans: Staff's Checkpoint 1 (4 transfers, failure, replacement by Fri 30 Oct) vs Senior Dev's (1 EUR + 1 USD paid via CLI). | §13 adopts Senior Dev §6 sequencing with Staff's checkpoint dates. Checkpoint 1 = 1 EUR SEPA + 1 USD ACH paid live via CLI sign-offs, audit verified. The failure → replacement path moves to Week 2 (Mon 2–Tue 3 Nov). Ordered cut list and never-cut list are explicit. |
| S-4 | MAJOR | Day 1 depends on Vedant's sandbox keys at 10:00 AM IST on a Sunday. If they're late, the agent stalls. | §9.1 day-1 Plan B: scaffold, client, offline contract tests against hand-specified shapes, then write `docs/NEEDS_HUMAN.md`. The live spike runs as soon as keys exist. The checkpoint slips by at most one day before the cut list applies. |
| S-5 | MAJOR | Version pins were "checked 8 Oct" by a board member and can't be re-verified here. A pin that doesn't resolve would stall `uv lock`. | §6.1: pins are targets. The agent runs `uv lock`; if a pin doesn't resolve, it takes the nearest released version, records it in `docs/DECISIONS.md`, and never loosens to an unpinned range. |
| S-6 | MAJOR | The request-id derivation was ambiguous for tranches and replacements (`{tranche_no}:{attempt_no}`: is the attempt per tranche or per obligation?). | §7.3: `transfer:{obligation_id}:t{tranche_no}:a{attempt_no}`, where `attempt_no` increases **per obligation** across tranches. Conversions use `conversion:{conversion_id}:a{attempt_no}`. Property test: no two attempts share a key. |
| S-7 | MAJOR | The executor's beneficiary fingerprint re-check assumes `GET /beneficiaries/{id}` returns full account identifiers. Undocumented. | New **U16**. Fallback: compare the bank country, currency, method and the last 4 digits returned against the payee version, plus the stored `beneficiary_id ↔ payee_version_id` mapping. Labelled in `docs/undocumented-behaviour.md`. |
| S-8 | MINOR | The `APP_DEMO_TIMING` description in R2-SeniorDev said it shortens cooling-off **and** settle. FINAL (row 22) says FINAL is never shortened. | §6.3: `APP_DEMO_TIMING` affects cooling-off only. |
| S-9 | MINOR | Leftover naming in build artefacts: beneficiary nickname prefix `cs-`, WebAuthn RP name "Payment run sign-off (demo)", prompt headers saying "human countersign". | `wt-` prefix, RP name `Wiretight (demo)`, prompts reworded. |
| S-10 | MINOR | The scope is large but feasible for a continuously running agent **if** Week 1 stays free of LLM and UI. Most at risk: UI + passkeys (Fri 6–Sat 7 Nov) and the live tie-out (Thu 5 Nov). | §13.3 ordered cuts: `verify_account` → webhooks → PDF/LLM ingest → realised FX → UI to 2 pages → passkeys to labelled HMAC fallback. **Never cut:** idempotency, packet binding, the lock (callback, cooling-off, cap), executor guards, the failure → replacement flow, the tie-out with honest residual states, the audit chain, the kill switch. |
| S-11 | NOTE | Feasibility verdict: **GO, medium-high confidence** for the never-cut core by Thu 5 Nov. The UI and passkeys by Sat 7 Nov are **medium**. The eval (20 scenarios) on Mon 9–Tue 10 Nov is **medium-high**, because scenarios are fixtures over the same pipeline. | — |

---

## 4. Consistency checks against DECISIONS.md

| # | Check | v0.1 status | v1.0 |
|---|---|---|---|
| X-1 | **D8**: demo failure = `ACCOUNT_CLOSED` (fallback `BENEFICIARY_BANK_RETURNED`) after SENT on LOCAL · SEPA; `BENEFICIARY_NAME_MISMATCH` only in unit/eval | ✅ §4.12 correct; no script yet | ✅ also in §12 script, eval S11/S13 |
| X-2 | **D8**: SWIFT `swift_charge_option=PAYER` + `fee_paid_by=PAYER`; fees from responses; per-rail FINAL; no wait-and-re-check; DEFAULT handler; RFI; return journal; cut-off/holiday logic | ✅ | ✅ |
| X-3 | **D7** values (72 h, 30 d contact, cap min(2,500, 50% median), T0 ≤ 2,000 / ≤ 1.5× / off by default, 10k dual, run 6k/50k/40, day 6k/75k/60/2 runs/5 benef., payee 1 T0 + 3 per 24 h, approver 30k/day, expiry min(4 h, quote − 120 s), 25 bp, floor 8k, ≥ 120 s quote margin, mismatch quarantine + ≥ 3/24 h trip, seed history 1,500/1,650/1,800) | ✅ all match | ✅ unchanged; only stricter additions (J-4) |
| X-4 | **D9** naming and wording | ⚠ "Wire Tight" spelled out in §1; "wire transfers" quoted in §2.1 dropped-stats line; one "Countersign" in the authority line | ✅ the banned-term list appears **once** (§4.0, as a lint rule); the historical rename note appears once (Appendix A); §1 and §2.1 reworded |
| X-5 | **R2-SeniorDev**: `duplicate_request_id` = 400, no replay, lookup before retry; beneficiaries looked up by nickname; `request_id` excludes `run_id`; only timeout/5xx = AMBIGUOUS; `reason` enum (22 values) + `reference` + string amounts on transfers; `/beneficiary_api_schemas/generate` + `/beneficiaries/validate`; TM/restriction/channel-policy trip; no `x-api-version` by default and never on `/fx/*` | partial (in §4.8, no endpoint section) | ✅ §7 endpoint table + client rules |
| X-6 | **R2-SeniorDev** state machine (SCHEDULED, OVERDUE, IN_APPROVAL, PAID→FAILED, FAILED auto-cancels, FINAL is ours) | ✅ §4.10/§4.11 | ✅ §8.3 full machine |
| X-7 | **Greenfield**: no reference to past projects | ✅ FINAL clean; ⚠ DECISIONS.md line 8 lists past project names | ✅ the package copy of DECISIONS.md has the names redacted to "Vedant's past projects (names withheld)" |
| X-8 | **D5/D6**: WebAuthn primary, HMAC fallback labelled "integrity-bound"; identity switcher; 3 approvers + ops; INSUFFICIENT_APPROVERS | ✅ | ✅ + C-1 (signed callback) |
| X-9 | **M1 / OPEN-4**: no project code before Sun 25 Oct 10:00 AM IST; application claims only what is true | ✅ | ✅ + the prompt's first rule |

Every "⚠ unverified" marker in v0.1 is kept. U16 is added. No test result, fee, latency or residual is stated as measured.

---

## 5. Open items that only Vedant can close
1. OPEN-1/OPEN-4: read the login-gated HackerEarth rules tab; screenshot the idea-form fields and limits.
2. Submit the idea application (target Wed 21 Oct; deadline Fri 23 Oct, 11:59 PM IST), filling the one "status on the day" line truthfully.
3. OPEN-3: create the Airwallex sandbox account (business name `Sandbox Business` or `New Business Sandbox`) and API keys before Sun 25 Oct, and put them into the repo's `.env` himself.
4. Create the empty GitHub repo `wiretight` at or after Sun 25 Oct, 10:00 AM IST.
5. Register the 4 demo passkeys (`make passkeys`) and sign the policies (`make sign-policy`), during Week 2.
6. Record the voiceover and the video (live takes Sun 8 / Tue 10 / Thu 12 Nov), and submit on HackerEarth on Thu 12 Nov.
7. OPEN-2 is closed as not needed: Wiretight uses no kit 5–10 features, so no access request is required.
