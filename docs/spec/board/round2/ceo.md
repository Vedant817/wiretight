# Round 2: CEO critique of SPEC-v1 (adoption + story)
*AB CEO · Thu Oct 8, 2026, ~7:35 PM IST. Inputs: SPEC-v1, DECISIONS (D3, F7), 04-sources, round0 memos, round1 judge scores. Every stat below is already in 04-sources or a round0 memo. No new figures are added. Greenfield.*

**Name:** "Countersign" is dropped. Candidates and clash checks are in `board/round2/names.md`. My pick there is **Wiretight**, and it's used in the copy below.

## 1. Persona and buyer: who pays first?
**Verdict: the SMB finance lead (or founder-operator) paying from their *own* Airwallex account pays first. Bookkeeping and fractional-CFO firms are the year-2 channel, not the first buyer.**
- **The spec is single-entity by design.**
  - §1 says "multi-entity comes later", and §14.6 puts the firm version on connected accounts. That needs kit 5–8 enablement, which is off-board (OPEN-2).
  - A firm can't adopt a tool that handles one client at a time and has no client-side sign-off.
- **The loss sits with the payer.** Redirected-payment fraud costs the company whose money leaves, so that company owns the budget.
  - AFP 2026: 74% of US organizations were hit by BEC. AFP 2025: vendor-imposter fraud was cited by 45%.
  - Caveat from the Staff Engineer's round-0 memo: AFP skews toward mid-size and large US corporates. The SMB-specific signal is Visa's SMB research: 31% of SMBs paying cross-border raise fraud and security concerns, and 29% have approval delays.
- **Liability sits with the client.** A firm that releases a client's payment to a changed IBAN takes on liability. Firms will adopt after their clients trust the lock, not before.
- **Persona realism.** The persona is real, but tighten it.
  - "20–300 suppliers… a month" for a 10–200-person company has no source in our pack. Label it an assumption or drop the range.
  - Anchor the persona to the demo company instead: 40 people, USD/EUR/GBP, a weekly run.

## 2. Shadow mode: believable, but not yet specified
The concept is right. Compliance & Risk independently proposed "ship in shadow mode (score only) before it enforces". But §14.2 is one sentence, and a finance lead needs to *see* it work before letting it touch money.

**What earns trust:**
1. A read-only start.
2. Decisions made by code, not the model, with every number linked to its source row (§4.9).
3. A policy file the controller owns.
4. The model never holds the key (§6.4).
5. An approval that voids itself if anything changes (§6.2).

**What's missing:**
- **The shadow data path.** Which history does it replay: past `GET /transfers` + `financial_transactions` + last month's bills? And what does the "what I would have caught" report contain?
- **Graduation criteria.** Example: N clean runs where shadow decisions match the humans' or every disagreement is explained → T1 on → per-payee T0.
- **The false-positive release path.** A legitimate supplier stuck in quarantine is a late payment and a damaged relationship (Judge Q2). The spec needs a "verified callback → release in this run" path, and the precision metric must sit beside recall in §13.
- **Coexistence with native approvals.** If the customer keeps Airwallex's native approval chain (§6.3, API path unverified), Wiretight must not become a *second* queue. Position it as pre-approval screening.
- **The answer to Judge Q6, "why not my existing approvals?"** Approval workflows decide *who* signs. Wiretight decides *what they're signing*: is it the same payee bank fingerprint as the last final payment, is the bill unpaid, does the reserve hold? Say that in §14.

## 3. Name
See `names.md`. Top pick: **Wiretight**. Runner-up: Remitlock.

## 4. The one sentence judges should remember
**"Two days before a €7,500 bill is due, a 'we've changed banks' email arrives. Wiretight freezes that payee, pays everyone else in three currencies without touching the reserve, and when a transfer bounces it pays the replacement exactly once and proves where every dollar landed."**

## 5. Prize lane
**Pick: Founder's Choice ($30K).** Both open lanes are "Open category. No specific requirements", and nobody has said who judges which, so this is a judgment call.
- **Why Founder's Choice:** Our Round 1 profile is strong on safety and buildability (Judge: C3 9, C4 8) and weak on originality (C5 4, kit 1 + kit 3 overlap). A pure "judges" panel that has seen every kit-3 clone punishes overlap. A founder-style read rewards "is this a company?", which is where the adoption story works for us.
- **What pitches the lane:**
  - One named buyer.
  - One fear: redirected payments.
  - A zero-migration wedge: a read-only key on an existing Airwallex account, then shadow mode.
  - A visible ladder to autonomy.
  - Year-2 expansion through firms.
  - This maps onto Waldo's questions (unofficial proxy): "genuine problem… credible path from prototype to adoption… balance autonomous execution with appropriate control".
- **Visa:** not realistic. TAP and VIC are agent-checkout tooling with merchant prerequisites (MID, token requester ID per 04-sources), and our flow is B2B payouts. Adding it would be a bolt-on that dilutes the story.
- **Metal:** realistic only as the §8 audit-head anchor, and only after Nov 10. Flag: the landing page lists Metal as an "L1 blockchain", but the spec anchors on "Metal L2 testnet". Confirm which counts as "Metal tooling" before spending an hour on it.

## 6. Critique of §14 and §15
**§14 (adoption):**
- "Runs on the customer's existing Airwallex account. Scoped API key, no new bank" is the best adoption line we have. Keep it first.
- "Shadow mode first" is right but unmeasured (see §2). Make it a demo beat.
- "Auditor-friendly: hash-chained audit log… optional public anchoring": auditors and SMB buyers don't ask for public anchoring. Move it to the tech appendix.
- "Clear business model hypothesis (unvalidated)": "clear" and "unvalidated" contradict each other. Write "Pricing hypothesis: per-entity monthly".
- "Failure-honest… given public complaints about frozen funds at fintechs (Trustpilot themes…)": **cut this.** It reads as a dig at the host's own product in front of the host's judges.
- Missing: who buys first, the trigger moment (the first bank-change email), and time-to-value.

**§15 (application text):**
- Title, "Countersign: the cross-border payment run that never pays twice":
  - The name is dropped.
  - "Never pays twice" is kit 3's promise almost word for word ("without paying twice"), so it leads with our least original claim. D3 says lead with the bank-change lock.
- Tagline, "An agent that runs a multi-currency supplier payment run: it blocks duplicates and redirected invoices, protects the cash reserve, recovers failed transfers and reconciles every payment": five verbs, no person, no stakes.
- Full description: "…half of finance teams need more than six days to close their books (Ledge)": the close stat belongs to the parked AR story, and it's a 100-person vendor survey. Drop it. Four stats in one paragraph blur together; keep two.
- "Approvals are cryptographically bound": jargon. Say "an approval is void if anything about the payment changes".
- §11 hook, "74% of companies were hit by business email compromise last year": AFP's base is "US organizations" (n=465), not "companies". Attribute it exactly.

**Proposed copy:**
- **Title:** *Wiretight: the supplier payment run that can't be redirected*
- **Tagline (21 words):** *Pays overseas suppliers in the right currency, freezes any payee whose bank details change, never pays twice, and proves every payment landed.*
- **Hook (video 0:00–0:20 and the app's first line):** *"Two days before a €7,500 invoice is due, an email arrives: 'We've changed banks, please use our new IBAN.' In AFP's 2026 survey, 74% of US organizations were hit by business email compromise. Here's what Wiretight does with that email."*
- **Short description (rewrite, ~75 words):** *Small companies pay overseas suppliers every week from a spreadsheet and a bank portal, which is exactly where redirected-invoice fraud and double payments slip through. Wiretight reads the bills, freezes any payee whose bank details changed until someone verifies them out of band, plans payments across currencies without breaching the cash reserve, and pays through Airwallex. It replaces a bounced transfer exactly once and ties every movement back to the books. People sign off on anything risky, and any change voids the sign-off.*

## 7. Fixes
**Must-fix:**
1. Rename everywhere: the §0 title, §6.3 "Countersign queue", the §9 diagram, §15, and the `countersign/` repo folder. Use "sign-off" as the verb. "Countersign" collides with live agent-payments and invoice-review products (see names.md).
2. Re-order the story around the bank-change lock. The hook, the first demo beat and the title all lead with it. Cut the "deposit lands → re-plan" beat to ≤15 s, as the Judge advised.
3. Name the first buyer in §1, §14 and §15: the SMB finance lead on their own account. Demote firms to "year-2 channel". Drop or label the unsourced "20–300 suppliers" band.
4. Specify shadow mode: data sources, the "would have caught" report, and graduation criteria. Add a 10–15 s shadow-report beat to the video.
5. Delete the §14.7 Trustpilot / "frozen funds at fintechs" line from anything judges will see.
6. Apply stat hygiene to §15 and §11: at most 2 stats, attributed exactly ("74% of US organizations, AFP 2026"; "1.5% of disbursements, APQC median"). Remove the Ledge close stat.

**Should-fix:**
1. Replace jargon in public text: "T0/T1/T2", "packet hash", "cryptographically bound", "hash-chained" → "auto / one sign-off / two sign-offs", "void on change", "tamper-evident log".
2. Add a quarantine release path and report duplicate/bank-change **precision** next to recall in §13.
3. Add the "who signs vs what they sign" answer to §14, positioned as complementary to Airwallex native approvals.
4. Fix §14.6 wording: "Pricing hypothesis: per-entity monthly".
5. Change slide 1 from "Problem + 4 numbers" to one story plus one number.
6. Confirm Metal L1 vs L2 eligibility before building the anchor stretch. If it's unclear, drop it. Asking partner Slack is Vedant's call.
7. Add a time-to-value line ("read-only key → shadow report") only once the eval harness has measured it. Don't promise a number now.
