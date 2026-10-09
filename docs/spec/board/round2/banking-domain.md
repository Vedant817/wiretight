# Round 2 · Banking-domain realism review of SPEC-v1 "Countersign"
*AB Banking Domain · 8 Oct 2026 (IST). Inputs: `board/SPEC-v1.md`, `board/DECISIONS.md` (D3, F7), `04-sources.md`, `raw/`. Every number below was read from the cited page or file in this round or in an earlier one. [V] = opened and read. [S] = search snippet only. Nothing was submitted and no one was contacted.*

## Verdicts (short)
| Area | Verdict |
|---|---|
| Persona (§1) | **Mostly realistic.** The supplier count is supported by sources. Headcount, the weekly cadence and "3+ currencies" have no source and should be labelled as assumptions. |
| Netting / FX sizing (§4.3) | **Mislabelled.** "Net by currency" is really FX aggregation, not netting. Supplier credit notes, the netting that actually happens at this size, are missing. Multilateral netting is correctly absent. |
| LOCAL vs SWIFT (§4.3, §10) | **The demo contradicts the spec's own rule.** The German EUR bill goes by SWIFT, but Airwallex pays Germany locally (SEPA / SEPA Instant), and VoP name checking only works on that local rail. |
| SWIFT fees / charge bearer | **Missing.** Airwallex defaults to `swift_charge_option=SHARED`, so the supplier receives less than the invoice. The 12.85 fee is hard-coded. |
| Cut-offs / value dates | **Missing.** The planner has due dates but no rail lead time, business days or holidays. |
| Reserve floor | **Sound concept.** It ignores prepayment holds and fees deducted after a failure. |
| Out-of-band callback | **Right practice**, consistent with AFP and IC3. It should also cover new payees and use the real verify_account result enums. |
| Returned payments | **Under-modelled.** The 48h settle window is shorter than the SEPA return window. Refund currency, non-refundable fees, third-party fees and FX-delta fees are not handled. |
| failure_type playbooks (§4.7) | **Partly wrong and incomplete.** The timeout/system-error action is wrong, roughly 9 failure_types have no playbook, and there is no RFI or sanctions (watchlist) path. |
| Journal / realised FX (§4.8) | **Directionally right.** The base rate is wrong once an invoice crosses a period end. Return entries and a clearing account are missing. |
| Citations (§2) | **11 of 12 numbers match their primary source.** One is misattributed (Ardent "Manual AP"), several need scope framing, and three are now verified ([S] upgraded to [V]). |

---

## MUST-FIX

**M1. §10 demo + §4.3 "prefer LOCAL": the German EUR 7,500 bill must not default to SWIFT.**
- **Evidence:**
  - Airwallex's Germany payout page lists **LOCAL EUR via "SEPA Instant / SEPA", 0–2 business days, no limit**. SWIFT is the 0–3 day alternative.
  - Airwallex's verify-account doc says VoP covers **LOCAL SEPA only**, so a SWIFT payment to a German IBAN gets no name check at all.
  - A treasury judge will ask "why SWIFT to Germany?"
- **Fix:**
  - Pay #2 by LOCAL SEPA (fee per the API response, VoP available).
  - If you want a SWIFT/fee beat, use a supplier with no local rail, or say on screen why SWIFT is forced.
  - On SEPA a name mismatch is normally caught *before* sending (VoP). A realistic post-SENT failure there is a scheme Return for "wrong account number or account closed" (EPC SCT Rulebook §4.3.2.2). Simulate `ACCOUNT_CLOSED` or `BENEFICIARY_BANK_RETURNED` instead.
  - Bonus: "our old account closed, here are new details" is also the classic BEC pretext, so it shows the bank-change lock again.
- **Sources:**
  - https://www.airwallex.com/docs/payouts/payout-network/bank-accounts/germany.md
  - `raw/doc_verify.txt` (lines 20–26)
  - https://www.europeanpaymentscouncil.eu/sites/default/files/kb/file/2025-09/EPC125-05%202025%20SCT%20Rulebook%20version%201.1.pdf

**M2. §4.3 / §6.2 packet / `policy.yaml fees`: charge bearer and fees.**
- **The docs say:**
  - `swift_charge_option` is "either `SHARED` (default) or `PAYER`". Under SHARED, "the beneficiary will receive the `amount_beneficiary_receives` less corresponding SWIFT charges by the beneficiary bank."
  - There is no BEN option for SWIFT charges. `fee_paid_by` (PAYER default / BENEFICIARY) is the separate Airwallex transfer fee.
- **Why it matters:** on the default, the supplier is short-paid, the invoice stays partly open and the supplier chases the difference.
- **Fix:**
  - Set `swift_charge_option: PAYER` explicitly for supplier invoices (policy default) and `fee_paid_by: PAYER`.
  - Put both fields in the approval packet.
  - Size conversions from the create response (`fee_amount`, `fee_currency`, `amount_payer_pays`, `amount_beneficiary_receives`) instead of the hard-coded EUR 12.85 and `LOCAL: 0`. Airwallex only says LOCAL is "more cost-effective", not free. Handle the `fee_unknown` create error.
- **Sources:** `raw/doc_create_transfer.txt` (lines 190–191, 242–243, 430, 442–444); https://www.airwallex.com/docs/payouts/transfers/create-a-transfer.md (§Transfer fee)

**M3. §4.6 Track + `settle_window_hours: 48`: the window is shorter than the real return window.**
- **Evidence:**
  - SEPA Returns "must be transmitted to the Originator PSP within three Banking Business Days after Settlement Date". Over a weekend that is more than 48h.
  - Airwallex: "A failure can occur after `PAID`, so continue listening for `payout.transfer.failed` until funds arrival is confirmed."
  - SWIFT returns have no comparable fixed scheme deadline in the sources fetched. Swift puts investigations at 5–10 working days.
- **Fix:**
  - Make settle windows per rail and in **business days**: SEPA ≥ 3 BBD after settlement. ACH ≈ 2 banking days for administrative returns [S, NACHA rule via search snippet, not opened].
  - SWIFT: never FINAL by timer alone. Require supplier confirmation or remittance acknowledgement, or label it "presumed settled".
  - Keep listening after FINAL and re-open if a late failure arrives.
- **Sources:**
  - EPC SCT Rulebook §4.3.2.2 / CT-01.04R (URL above)
  - https://www.airwallex.com/docs/payouts/transfers/manage-transfers/handle-failed-transfers.md
  - https://www.swift.com/news-events/press-releases/swift-solution-managing-cross-border-payments-investigations-could-save-industry-millions-operational-costs

**M4. §4.7 Recover playbooks: one is wrong, several are missing, and there is no RFI or sanctions path.**
- **(a) Wrong action.** `CHANNEL_TIMEOUT` / `SYSTEM_ERROR` are set to "wait and re-check; no replacement until terminal". But a transfer carrying a failure_type is already FAILED, and Airwallex says "failed transfers will be automatically cancelled in seconds". The recommended action for 91401/91402 is "Contact Airwallex".
  - Fix: confirm CANCELLED, escalate to an Airwallex support ticket, then allow a T2 replacement.
  - Keep the "ambiguous, don't retry" logic for *create* timeouts (S6). That is a different case.
- **(b) Missing failure_types.** Map every value in Airwallex's list, with a default of `ESCALATE`:
  - `BENEFICIARY_BANK_RETURNED`, `BENEFICIARY_REQUESTED` (Airwallex: "advise your beneficiary to check with the receiving bank") → supplier confirmation + T2 replacement
  - `ACCOUNT_CURRENCY_MISMATCH`, `INVALID_BANK_INFORMATION`, `INVALID_CORRESPONDENT_BANK_INFORMATION`, `INVALID_SPECIAL_CHARACTER` → "create a new transfer with updated parameters". Special-character and correspondent issues are data fixes. Account/bank changes are bank-detail changes and go to T2.
  - `EXCEEDED_TRANSACTION_AMOUNT_OR_LIMIT` → split or change rail, re-countersign
  - `UNABLE_TO_APPLY`, `OTHER` → escalate
  - `DUPLICATION_RETURN` is already listed. Keep it.
- **(c) RFI and compliance.** `TM_SUSPENDED` (code 90502) carries `failure.details.reason_codes`. Airwallex's example is `EXPIRED_TRANSACTION_RFI` with message "Unable to process due to risk concerns". `WATCHLIST_RESTRICTION_PAYER/_BENEFICIARY` also appear as reason values.
  - Add an **RFI tracker**: subscribe to `rfi.action_required` / `rfi.answered` / `rfi.closed` and show "Airwallex needs the invoice/contract for transfer X" in the queue. Answering the RFI is human-only. The agent may attach the invoice PDF it already holds.
  - Airwallex: PROCESSING/SENT transfers "may need to provide additional information requested by Airwallex".
  - **Watchlist/sanctions** → hard-block the payee pending compliance. The LLM must **not** draft a supplier message giving the reason.
- **(d) Not failure_types.** Insufficient funds before sending is `balance_insufficient` at create, and a missed cut-off simply rolls the date (see M7). Model both as plan states, not as incident playbooks. S16 already partly does this.
- **Sources:**
  - `raw/doc_failure_types.txt` (lines 880–1004 recommended actions; list near top)
  - `raw/doc_list_transfers.txt` (lines 800–808, 941–948, 1214–1216)
  - `raw/doc_tstatus.txt` (line 124)
  - https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events/rfi.md
  - https://www.airwallex.com/docs/banking-as-a-service/risk/rfi-(request-for-information)/handle-transaction-rfi.md

**M5. §4.7 / §4.8 / S7–S8: returned-payment money flow and entries are missing.**
- **What Airwallex does:**
  - After a FAILED transfer, "Transfer amount less transfer fee will be refunded. Third-party and FX cancellation delta fees may apply."
  - The **transfer fee is non-refundable**.
  - A third-party fee "is deducted by the external bank… this fee will be separately deducted from your Wallet".
  - Refunds come back **in the transfer currency by default** (EUR back to the EUR wallet, no automatic re-conversion). If the account is set to refund in the source currency, an FX cancellation delta fee applies.
- **Fix:**
  - The replacement should reuse the returned EUR (no second conversion) and budget the **second transfer fee**.
  - Re-read the balance after `PAYOUT_FAILURE` / `PAYOUT_REVERSAL` posts rather than assuming a full refund.
  - Extend the tie-out invariant with `− third_party_fees − fx_delta_fees ± ADJUSTMENT ± CONVERSION_REVERSAL ± PREPAYMENT/PREPAYMENT_RELEASE`. All of these are Airwallex `transaction_type` values.
- **Journal for a return** (USD functional currency, EUR bill):
  1. Dr EUR wallet / Cr AP clearing (or AP) for the refunded EUR, reversing the payout leg at the original carrying amounts.
  2. Original transfer fee stays in Bank fees.
  3. Dr Bank fees / Cr EUR wallet for any third-party fee.
  4. Dr/Cr FX loss/gain for any FX delta fee.
  5. The reinstated EUR liability, and the EUR cash, are monetary items revalued at period end.
- **Sources:**
  - https://www.airwallex.com/docs/payouts/transfers/manage-transfers/handle-failed-transfers.md (§Refund and Fees)
  - `raw/doc_fin_tx.txt` (transaction_type list)
  - IAS 21 ¶23/¶28: https://www.ifrs.org/content/dam/ifrs/publications/html-standards/english/2025/issued/ias21.html

**M6. §2 "Manual AP" row: misattributed.**
- **Evidence:**
  - Ardent's $9.84 / 8.2 days are the **average across all respondents**, not "manual AP".
  - $12.42 / 13.5 days is "All Others" (not Best-in-Class), not "non-best-in-class manual".
  - The sample is 204 respondents: **54% revenue >$1B, 26% $250M–1B, 20% <$250M**. These are enterprise benchmarks, not SMB ones.
- **Fix:** relabel to "AP cost and cycle time (Ardent 2025, all respondents; mostly >$1B companies)" or drop the row.
- **Source:** `raw/ardent.txt` (Table 1, Table 2, demographics); https://www.bottomline.com/cdn/1517/5157/1685/Ardent_Partners_-_State_of_ePayables_2025_-_Bottomline_-_FINAL.pdf

**M7. §4.3 Plan + §10: no cut-off, value-date or holiday logic.**
- **Evidence:**
  - Airwallex: "The transfer date is the day we send the money to your recipient, not the day they receive it". Dates falling on a holiday or non-business day for the recipient's currency go out the next business day, and "regional holidays in the countries you are sending to and from" also apply.
  - Flight times differ by rail: DE SEPA 0–2 BD, SWIFT 0–3 BD, UK Faster Payments 0–1 BD, US ACH 0–2 BD (ACH is 1–2 BD for non-US customers).
  - Demo #2 is "due in 2 days" by SWIFT and could land late.
- **Fix:**
  - The planner computes `latest_send_date = due_date − max_flight_days(rail) − holidays` and flags "at risk of late" items.
  - Omit `transfer_date` for ASAP. Airwallex warns that setting it, "including today's date", routes the transfer through scheduled logic.
  - Use a small holiday calendar fixture per currency.
- **Sources:**
  - https://help.airwallex.com/hc/en-gb/articles/4407753207449-When-can-I-send-my-transfer
  - Germany page above
  - https://www.airwallex.com/docs/payouts/payout-network/bank-accounts/united-kingdom.md
  - https://www.airwallex.com/docs/payouts/payout-network/bank-accounts/united-states
  - `raw/doc_create_transfer.txt` (lines 446–456)

**M8. §10 / §11 vs §6.1: demo item #1 can't be T0.**
- **Evidence:** #1 is USD 4,200, but the T0 limit (`per_payment_limit_base`) is 2,000. The demo says "#1 auto-executes (T0 known payee)". Code that enforces the policy will route it to T1.
- **Fix:** lower #1 to ≤ USD 2,000, or raise the limit, and seed ≥2 FINAL prior payments with a fingerprint unchanged for ≥30 days.
- **Source:** SPEC-v1 §6.1, `policy.yaml`, §10, §11 (internal consistency)

---

## SHOULD-FIX (15)

1. **§1 persona: label what's sourced.**
   - Supplier counts are plausible:
     - Codat (700 US businesses, $10M–$1B revenue) finds "firms under $100M in revenue typically manage up to 500 vendors".
     - MineralTree 2022 (912 AP professionals, majority $10–100M revenue) says supplier payments ran "from 1 to more than 2,000 per month, with the majority in the 101-250 range".
   - I found **no source** for the 10–200 headcount, weekly/bi-weekly cadence, or "3+ currencies". Label them as assumptions to validate in user interviews.
   - Sources: https://codat.io/resources/how-hundreds-of-middle-market-businesses-really-spend/ ; https://www.mineraltree.com/wp-content/uploads/2022-State-of-AP-Report.pdf
2. **§4.3 netting.**
   - Rename "Net by currency" to "Aggregate FX by currency".
   - Add **supplier credit-note offset** (same supplier and currency) before paying: ingest negative documents, pay the net amount, and list invoices and credits in the remittance.
   - Xero: "Apply credit to reduce the amount you owe on a supplier's bill… you can only credit up to the outstanding amount of the bill."
   - State that multilateral netting is out of scope.
   - Source: https://central.xero.com/0/article/Apply-a-supplier-s-credit-to-a-bill
3. **§4.8 realised FX base rate.**
   - Use the invoice-date rate only if the invoice is paid **in the same period**.
   - Otherwise measure from the last revaluation (period-end) rate. IAS 21 ¶29 says the difference "in each period up to the date of settlement is determined by the change in exchange rates during each period". ASC 830-20-40-1 measures "from the transaction date or the most recent intervening balance sheet date, whichever is later".
   - Sources: IFRS IAS 21 (URL above); https://asc.understandingaccounting.org/asc/830/20/ ; https://dart.deloitte.com/USDART/home/codification/broad-transactions/asc830-10/roadmap-foreign-currency-transactions-translations/chapter-4-foreign-currency-transactions/4-3-subsequent-measurement-foreign-currency
4. **§4.8 settlement rate when no conversion happened.**
   - A payout funded from an *existing* EUR balance has no `client_rate`.
   - Use the carrying rate of that EUR balance (state the policy: average or FIFO), and treat FX on holding EUR cash separately.
   - Source: IAS 21 ¶21/¶28 (URL above); `raw/doc_fin_tx.txt`
5. **§4.8 journal shape.**
   - Recommend an **AP clearing / payments-in-transit** account that matches the spec's PROVISIONAL state:
     - At payout: Dr Clearing, Cr EUR wallet; Dr Bank fees, Cr EUR wallet.
     - At FINAL: Dr AP (carrying amount), Cr Clearing, with the realised FX difference to FX gain/loss.
     - On a return: Dr EUR wallet, Cr Clearing (see M5).
   - Keeps AP honest while "PAID isn't final".
   - Source: Airwallex PAID→FAILED, `raw/doc_tstatus.txt`
6. **§4.8 recon details: test in pre-work.**
   - Financial transactions carry `amount`, `fee` and `net`, so a fee may sit on the PAYOUT row rather than as a separate `FEE` row. Handle both.
   - Rows have `status` PENDING / SETTLED / CANCELLED. Tie out on settled rows plus an explicit pending bucket.
   - Source: `raw/doc_fin_tx.txt`
7. **§4.3 reserve floor.**
   - Count `lock_rate_on_create` prepayment holds (for future-dated transfers "A `prepayment`… is held upfront") as committed.
   - Keep a small buffer for later third-party / FX-delta deductions (M5).
   - Sources: `raw/doc_create_transfer.txt` (lines 462–464); handle-failed-transfers URL
8. **§4.2 / §6.1 callback scope.**
   - Apply the out-of-band callback to **new payees** as well as changes, always to a number from the vendor master and never one from the request.
   - AFP: 93% rated verification policy/callback effective. IC3: "Use secondary channels and/or two-factor authentication to verify requests for changes in account information".
   - The "corrected name" from a failed-payment reply (S7) must also go through the callback, not the email thread.
   - Sources: https://www.financialprofessionals.org/training-resources/resources/articles/Details/4-ways-to-reduce-payments-fraud ; https://www.ic3.gov/PSA/2024/PSA240911
9. **§4.2 verify_account enums (F7 shorthand vs real fields).**
   - The response has `code` (`VERIFIED` / `INVALID` / `CANNOT_VERIFY` / `EXTERNAL_SERVICE_UNAVAILABLE`) and `account_name_match_result` (`FULL_MATCH` / `PARTIAL_MATCH` / `NOT_MATCHED` / `*_INCORRECT_TYPE`).
   - `INVALID` = "Do NOT proceed". Anything other than `FULL_MATCH` carries misdirection risk, so route it to T2.
   - UK CoP is "enabled on request" and its UI copy needs Airwallex approval.
   - Source: `raw/doc_verify.txt` (lines 7–18, 186–192)
10. **§4.2 fingerprint.**
    - Airwallex bank details already carry a `fingerprint` ("Fingerprint of current beneficiary's bank account").
    - Store it next to your sha256 and diff both.
    - Source: `raw/doc_create_transfer.txt` (lines 123–124)
11. **§4.5 / playbook purpose codes.**
    - `INVALID_PAYMENT_PURPOSE` maps to the transfer `reason` enum (e.g. `goods_purchased`, `professional_business_services`, `freight`). Set it from the invoice category at plan time, not only after a failure.
    - Quotes "cannot be applied for creating and submitting a transfer for approval". Note this if you use Airwallex-native approvals (§6.3).
    - Source: `raw/doc_create_transfer.txt` (lines 436, 468)
12. **§2 Swift row framing.**
    - The $1.6B is what "financial institutions spend… each year… to investigate payments that get held up", a bank cost and not an SMB cost.
    - The 5–10 working days is the time to investigate delays that "typically arise when a payment instruction is missing key information".
    - Add the counterweight from the same release: "90% of transactions over Swift… reach end banks within an hour."
    - Source: Swift press release (URL in M3)
13. **§2 cash-forecasting row.**
    - The source is the **AFP 2025 Treasury Benchmarking Survey**, not the fraud survey. The wording is "five most challenging tasks… Cash or liquidity forecasting (cited by 62%)". It is the top item, but this is a top-five list, not a single "#1 challenge".
    - The figure is **60% at organizations under $1B**, which fits the persona better.
    - Rename the pain to "cash forecasting" (not "shortfalls").
    - Source: https://7185359.fs1.hubspotusercontent-na1.net/hubfs/7185359/Research%20Surveys/SURVEYS/2025%20AFP%20Treasury%20Benchmarking%20Survey%20Comprehensive%20Report.pdf
14. **§2 / §11 scope labels.**
    - AFP 74% is "organizations in the United States… affected by business email compromise (BEC) in 2025". The §11 hook ("74% of companies") should say "US organizations".
    - Wise £2.8bn is UK SMBs only and Capital Economics research commissioned by Wise. Label it so.
    - APQC 1.5% is "duplicate **or erroneous**" disbursements (n=1,686, cross-industry), so the "Paying twice" row overstates duplicates alone.
    - Sources: https://www.prnewswire.com/news-releases/over-75-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags-302738857.html ; `raw/wise.txt` ; https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number
15. **`04-sources.md` labels.** Upgrade three entries from [S] to [V], now opened:
    - FBI IC3 2024 report: BEC **$2,770,151,146**.
    - LexisNexis/Accuity **$118.5B** "in fees, labor and lost business in 2020". It is 2020-dated, so keep the year in the spec.
    - AFP Treasury Benchmarking 62%.
    - Sources: https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf ; https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20210714-true-cost-of-failed-payments

---

## Citation audit table (§2 and Why-now)
| Spec claim | Primary says | Status |
|---|---|---|
| 74% BEC (AFP 2026) | "About three in four organizations (74%) were affected by business email compromise (BEC) in 2025" (US) | ✅ match. Add "US" |
| 17% use AI (AFP 2026) | "Just 17% of organizations leverage AI to combat payments fraud" | ✅ |
| Vendor imposter 45% (+11 pts) (AFP 2025) | "cited by 45%… an 11-percentage-point increase" | ✅ |
| Wires top BEC target 63% (AFP 2025) | "Wire transfers… most frequently targeted by BEC… 63%" | ✅ |
| $2.77B BEC (FBI 2024) | IC3 2024 table: BEC $2,770,151,146 | ✅ (now [V]) |
| 1.5% duplicate/erroneous, n=1,686 (APQC) | Median 1.5%, sample 1,686 | ✅ wording: "or erroneous" |
| $9.84 / 8.2 days; $12.42 / 13.5 days (Ardent) | Averages; "All Others" vs Best-in-Class; 54% >$1B | ❌ mislabelled "Manual AP" (M6) |
| $1.6B/yr, 5–10 working days (Swift) | Bank investigation cost; 5–10 working days to investigate | ✅ numbers, ⚠ framing (SF12) |
| $118.5B failed payments 2020 (LexisNexis) | "$118.5 billion in fees, labor and lost business in 2020" | ✅ (now [V]) |
| PAID→FAILED (Airwallex) | "`PAID` is not always final" | ✅ |
| £2.8bn, +27% since 2018 (Wise) | £2.8bn in 2023, up from £2.2bn in 2018 | ✅ UK-only, vendor-commissioned |
| 50% 6+ days; 20–50 hrs; 3–5 systems; 94% Excel (Ledge) | All four present. n=100, companies with 51–200 to 10,000+ employees | ✅ |
| 62% forecasting #1 (AFP 2025) | Treasury Benchmarking: 62% in top-5 challenging tasks; 60% for <$1B | ⚠ misattributed survey + wording (SF13) |
