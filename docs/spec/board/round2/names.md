# Round 2: Name candidates

Shared file for the replacement name ("Countersign" is dropped). Each seat appends its own section and never overwrites anyone else's.

## CEO candidates (AB CEO)
*Checked on Thu Oct 8, 2026, ~7:30 PM IST. Nothing was registered.*

**How each name was checked:**
- **(a) Fintech clash:** a web search for each name.
- **(b) Airwallex builds clash:** grepped `raw/builds.json` (the 5 reference builds: Agent cards, Drop-in checkout flow, Invoicing in Slack, AI finance manager, Allocard) and `raw/library.json` (8 recipes: Treasury agent, Purchase agent, Payment recovery agent, Chargeback agent, Corporate card platform, Contractor payroll platform, Revenue-based lending platform, Marketplace payments platform).
- **(c) Domains:** RDAP lookups (Verisign for .com, Identity Digital for .ai, Google Registry for .dev). "Free" means RDAP returned 404, which is a strong sign the domain is unregistered but not proof it can be bought; premium pricing and registry reserves weren't checked. `whois` couldn't be installed (no root), so RDAP was used instead.
- **(d) GitHub:** `api.github.com/users/<name>`, where 404 means no user or org has the handle.

**Briefed on:** an agentic cross-border supplier payment run with a payee-change fraud lock, duplicate prevention, human approval, and landed-payment proof.

| Rank | Name | One-line rationale | Fintech clash (a) | Airwallex builds clash (b) | .com / .ai / .dev (c) | GitHub (d) | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | **Wiretight** | "Your wires, done tight": no leaks to fraudsters, no double pays, no slack in the reserve. Two plain words, one stress pattern, easy to say on a demo stage. | **None found.** The only hit is a *dead* USPTO mark for wire-crimper hand tools (Lisle Corp, serial 88435162, Class 8: https://www.trademarkelite.com/trademark/trademark-detail/88435162/WIRETIGHT) and a consumer pliers product (https://maldaro.com/products/1-1-free-wiretight-pro-twist-wires-quickly-without-pain-or-fatigue-in-the-hands). | None | **free / free / free** | **free** | **TOP PICK** |
| 2 | **Remitlock** | Says the fraud lock directly ("lock the remittance"). | No product found. Sounds close to Remitly (https://www.remitly.com/), which also does business payouts, so mild confusion is possible. | None | taken / free / free | free | Strong runner-up |
| 3 | **Truepaid** | "Paid to the true payee, and truly paid": covers the fraud lock and landed proof. | truepaid.com is parked (Afternic). Near-miss TruePay, a Texas merchant-services firm (https://gotruepay.com/). | None | taken (parked) / free / free | free | Viable |
| 4 | **Paidonce** | The no-double-pay promise in two words. | No exact product. Near-misses: Paid, a UK AR fintech (https://tracxn.com/d/companies/paid/__I_Pkyj8tsZxdIoMRQliydikvbmpnzfP2baJDc_LsjRM), and Pay Once, a UPI API (https://www.payonce.shop/). | None | taken / free / free | free | Backup. Too narrow, and it echoes kit 3's "without paying twice" |
| 5 | **Wireward** | Ward = guard for wire payouts. | No exact product, but spoken aloud it sounds like WireGuard (VPN, https://www.wireguard.com/) and Payward (Kraken's parent, https://www.payward.com/). | None | taken / free / free | free | Risky on stage |
| 6 | **Remitproof** | Remittance + proof of landing. | Search snippets tie remitproof.com to AI-agent governance (REMIT Foundation, https://remit.foundation/agent-passport/specification). Unverified, but it sits in the agentic-trust space. | None | taken / free / free | free | Avoid |
| 7 | **Payfence** | A fence around outgoing pay. | **Clash:** PayFence, an API-monetization payments product on Stripe Connect (https://payfence.io/). | None | taken / free / free | free | Avoid |

**Rejected outright, with clear clashes:**
- *PaySeal*: ICICI Bank's payment gateway (https://synicsys.com/payment-gateway-integration/icici-payseal-payment-gateway-integration/), a live Indian fintech brand.
- *PaidProof*: a freelancer payment-protection SaaS (https://www.paidproof.app/pricing).
- *Keelpay*: close to Keel, an agentic-payments API (https://keel.money/).
- *Holdfast*, *Landfall*, *Tripline*: every domain and the GitHub handle are taken.

**Why "Countersign" had to go, for the record:**
- countersign.com is a live e-signature product (https://countersign.com/).
- countersign.network is "the kill switch for AI agents that spend money", with an MCP server, spend policy and approvals (https://countersign.network/).
- A Devpost project called "Countersign" is an agent invoice-review workbench that catches duplicates and "a changed bank account" and "requests your countersign" (https://devpost.com/software/countersign-4ym0tq).
- That last two overlap with our pitch almost exactly. Also, avoid "countersign" as the UI verb; use "sign-off".

**Top pick: Wiretight.**
- It is the only candidate that is clean on every check: no fintech product, no Airwallex build or recipe overlap, and .com, .ai, .dev and the GitHub handle all unregistered as of tonight.
- It makes the product's promise in plain English. "Wire" points at the cross-border payout, and "tight" covers the three guarantees we demo: nothing leaks to a redirected account, nothing goes out twice, and the reserve doesn't slip.
- It's short, says itself on stage, and doesn't box us in if the product later handles LOCAL rails as well as SWIFT.
- **Caveat:** "wire" reads US-centric, and in a strict sense SWIFT and local transfers aren't all "wires". Remitlock is the fallback if the board wants a name that says the fraud lock outright.

## Product & Design candidates (AB Product & Design)
*Checked Thu Oct 8, 2026, ~7:45 PM IST. Nothing registered, nobody contacted.*

**Methods** (same as CEO, so results can be compared):
- **Fintech clash:** web search per name.
- **Airwallex builds clash:** case-insensitive grep of `raw/builds.json` and `raw/library.json`. **0 hits** for every name below, and also 0 for the substrings "lock", "tight", "payee" and "pay run".
- **Domains:** RDAP via `rdap.org` (404 = likely unregistered; premium or reserved status not checked).
- **GitHub:** `api.github.com/users/<name>` (404 = handle free) plus a repo-name search count.

**Brief tested against:** an agentic cross-border supplier payment run with a payee-change fraud lock, duplicate prevention, human sign-off and landed-payment proof.

**Voiceover test:** I said each name inside the demo's key line, *"…so [NAME] voids the sign-off."*

### My candidates
| # | Name | Idea | Fintech / product clash | .com / .ai / .dev | GitHub handle / repos | Aloud (VO) | On screen (UI) | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **PayrunLock** | Says the job and the control | No product found. "Lock pay run" is a common **payroll** feature (Dayforce, Hectre, FlowPayroll docs), and there's a Staffology payroll repo `staffology-bureau-payrunlock`. Payroll confusion is the main risk. | **free / free / free** | free / 1 repo | "pay-run lock": 3 beats, clear, self-explaining | 10 chars, needs CamelCase. Fine as a sub-label ("pay-run lock") under a brand. | **Best of mine.** Better as the feature name than the brand. |
| 2 | **PayeeLock** | Names the lock exactly | **Serious clash:** the ETHGlobal showcase "PayeeLock" is an on-chain supplier-payout recovery protocol that pauses payouts when a supplier wallet is unsafe and makes earlier authorizations stale. Almost the same story. https://ethglobal.com/showcase/payeelock-16jyz | taken / free / free | free / 2 repos | "pay-ee lock": the double-e sound blurs on mic | OK | **Avoid.** Reads as a copy. |
| 3 | **Changelock** | Lock on bank-detail changes | **Clash:** ChangeLock, a Kubernetes delivery-security control plane. https://github.com/denisgrosek7-ai/changelock-public | taken / free / free | free / 6 repos | Clear | Clear | **Avoid** |
| 4 | **Wiresure** | Wires you can be sure of | **Close clash:** Wiresurance, a US "secure payment gateway" for paying suppliers (https://wiresurance.com/), plus a WireSure cable brand in India | taken / free / free | free | "wire-sure" can be heard as "wire-shore" | OK | **Avoid** |
| 5 | **Landproof** | Proof the payment landed | **Clash:** LandProof, "AI-powered property trust" (https://www.landproof.io/) | taken / free / free | **taken** / 8 repos | Says proof, not lock | OK | **Avoid** |

**Also tried and dropped** (taken or clashing):
- **Holdfast, Landfall, Countercheck, Holdline, Dualkey, Twokey, Holdpoint:** `.com` and/or every TLD taken.
- **Paylock:** PayLock escrow brands in NZ (https://www.paylock.co.nz/) and Nigeria (https://paylock.com.ng/).
- **Lockrun:** a well-known Unix cron-lock tool, and the GitHub handle is taken.
- **Payeeproof** and **Proofrun:** `.com` taken.
- **Payoutlock:** `.com` taken. A search summary claimed a "PayoutLock" platform exists, but the cited source was a different site, so it's unverified.

### My take on the CEO's candidates
I spot-checked the CEO's results myself:
- RDAP: wiretight.com, wiretight.ai and wiretight.dev all **404**; remitlock.com **taken** but remitlock.ai **404**; truepaid.ai and paidonce.ai **404**.
- GitHub handles **404** for wiretight, remitlock, truepaid and paidonce.
- Repo search for "wiretight": **0** repos.
- The builds and library grep is 0 for all of them.

| CEO name | Agree? | Aloud | UI | Notes |
|---|---|---|---|---|
| **Wiretight** | **Yes, top pick** | "WIRE-tight": 2 syllables, one stress, no spelling needed. Heard next to "Airwallex", it echoes "airtight", which helps memory. | 9 chars. Short in the nav and favicon, and reads well in "Wiretight · sign-off card". | See the full assessment below. |
| Remitlock | Runner-up | "REM-it lock": says the lock outright, but "remit" is heard as consumer remittances. It also sits close to **Remitly** on air. | Fine | .com taken. It names the control, not the outcome. |
| Truepaid | No | **Risky on air:** "true paid" can be heard as **"two paid"**, the exact failure we prevent | Fine | truepaid.com parked |
| Paidonce | No | Clear, but it pitches kit 3's promise | Fine | Contradicts the Judge M1 reposition |
| Wireward | No | Heard as **WireGuard** | Fine | Agree with the CEO |
| Remitproof | No | – | – | Agentic-trust clash (CEO) |
| Payfence | No | – | – | PayFence clash (CEO) |

### Explicit assessment: **Wiretight**
**Clashes**
- The only trademark is a **dead** USPTO mark for wire-crimper hand tools: Lisle Corp, serial 88435162, Class 8, status "continued use not filed… un-revivable", dated Jun 5, 2026 (https://www.trademarkelite.com/trademark/trademark-detail/88435162/WIRETIGHT).
- There's a consumer "WireTight Pro" pliers product (https://maldaro.com/products/1-1-free-wiretight-pro-twist-wires-quickly-without-pain-or-fatigue-in-the-hands).
- One GitHub README uses "wiretight DI" as a phrase, not a project name.
- No fintech or payments product found.
- No Airwallex reference build or recipe uses it.
- The nearest payments name is Wiresurance (shares "Wire-", different suffix). Low risk.
- *Not checked:* trademark registries outside the USPTO (UKIPO, EUIPO, India). Run that before any real launch. It doesn't matter for the hackathon.

**Domains and code hosting:** .com, .ai and .dev all unregistered per RDAP tonight (premium pricing not checked). The GitHub user/org handle is free, and no repo is named "wiretight".

**Read aloud in the voiceover:**
- *"…so Wiretight voids the sign-off"* and *"Wiretight froze it"* both land cleanly at speaking pace.
- One mild risk: in a fast US accent it can blur toward "wire-type". Say it once slowly in the hook, and show the wordmark on screen.
- There's no "wiretap" confusion in a run-through, but avoid saying "wire" twice in one sentence.

**On screen in the UI:**
- Short enough for the nav, the cold-open lower third and the tab title.
- Pairs with the house verb: "Wiretight · sign-off card", "Signed off ✓ in Wiretight".
- **It doesn't say *lock* or *proof* by itself.** The tagline has to carry that: *"Wiretight: no payout reaches a bank account a human hasn't signed off."* A sub-label "pay-run lock" (my #1) can sit on the incident view.

**Scope caveats:**
- "Wire" reads US-centric, and strictly SWIFT/LOCAL payouts aren't all wires. Judges will hear "wire transfer = money out", which is the right association for a payout control.
- If the product later covers card or stablecoin payouts, the name still works as a metaphor (tight = nothing leaks).

**Find-replace:** a single token, no spaces. In `round2/product-design.md` the token is currently `[PRODUCT]`. Replace it with `Wiretight` in one pass once the board confirms.

### Top pick: **Wiretight**, with "pay-run lock" as the descriptive sub-label
**Why:**
1. It's the only name in either list that passes every check: no live fintech clash, no Airwallex build overlap, all three domains and the GitHub handle free. Every one of my own candidates except PayrunLock has a real clash.
2. It says itself on stage in 2 syllables and survives a noisy demo-day mic. The "airtight" echo next to Airwallex is a bonus.
3. Its one weakness, not naming the lock, is fixed by the tagline and the on-screen sub-label rather than by a longer name.

**Fallbacks, in order:** Remitlock (names the lock; .com taken), then PayrunLock (all domains free; payroll-confusion risk). Avoid PayeeLock, because of the near-identical ETHGlobal project.

## Judge verdict (AB Judge)
*Checked Thu Oct 8, 2026, ~7:30 PM IST. Nothing registered, nobody contacted.*
- **Pick: CONFIRM Wiretight, on conditions.**
  - **Memorable:** 2 beats, and it echoes "airtight" next to Airwallex.
  - **Clean on my checks:** RDAP 404 for wiretight .com/.io/.ai/.dev and wire-tight.com. GitHub handle 404, 0 repos. The only USPTO mark is dead (Lisle, Class 8 crimpers, [Markinton](https://markinton.com/trademark/wiretight-88435162)).
  - **Slang:** "wired tight" means "highest state of organization and readiness" (Urban Dictionary), which is a positive.
- **Missed adjacency (low risk):** **Tight** ([tight.com](http://tight.com/)), an "AI-native embedded accounting" API for SaaS/fintech that does reconciliation. A different word, but don't write the name as "Wire Tight" or "WireTIGHT".
- **Connotations a skeptical Airwallex judge will raise:**
  - "Wire" is US-speak. Airwallex is global and APAC-heavy, and 5 of our 7 demo bills go over **LOCAL** rails. SF demo-day judges will hear "money out", which works for us.
  - Wiretap: not heard aloud in a run-through, so ignore it.
  - **The name does not say "locked payee details".** The tagline must carry the lock.
  - Rule: in the product and the video, say "payout" or "bank transfer", never "wire", for LOCAL payments.
- **Fallback order: override.** Put **PayrunLock** ahead of Remitlock (all domains free; the payroll confusion is manageable). Remitlock has a missed clash: the GitHub project **devOnyx-01/RemitLock**, "Time-Locked Cross-Border Escrow for Freelancers on Stellar" (updated May 2026). That's cross-border payments under the same name, on top of the Remitly sound-alike and a taken .com.
- **Title: amend.** "…that can't be redirected" is an absolute claim a judge will poke ("what if the approver is compromised?"), and it leads with "payment run", which reads as kits 1 + 3.
  - **Recommended:** **"Wiretight: supplier payouts that can't be quietly redirected"**, with the sub-line *"New or changed bank details stay locked until a second person confirms them by callback."*
  - **Alt 1:** "Wiretight: changed bank details don't get paid until a human calls back."
  - **Alt 2:** "Wiretight: every new payee needs a second person's yes."
  - Avoid "countersign" as a verb (clash, per CEO). Use "confirm" or "sign off".
