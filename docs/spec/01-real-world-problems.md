# 01 · Real-World Pains: Finance Ops for Cross-Border SMBs, Platforms and Exporters

**Method.** For each pain I list who has it, what happens, the cost (with a cited number), today's workaround, why an *agent with controlled money movement* helps, and the evidence URLs.

**Rules I followed:**
- No invented numbers.
- Every figure names its source.
- **(verified)** = I opened the primary page or PDF and saw the number.
- **(search-index)** = the number came from a search result snippet or a secondary page, and the primary page was blocked or errored. Treat these as unverified until re-checked.
- Reddit blocked direct fetching (HTTP 403 "blocked by network security"). Reddit threads are cited by URL with the gist from the search index, and they are qualitative signal only.

---

## Summary table

| # | Pain | Headline number | Status |
|---|---|---|---|
| P1 | Vendor impersonation / BEC / redirected supplier payments | **74%** of US orgs hit by BEC in 2025 (AFP 2026); **$2.77B** BEC losses reported to FBI in 2024 | verified / search-index |
| P2 | Duplicate & erroneous supplier payments | **1.5%** of disbursements duplicate or erroneous (APQC median, n=1,686) | verified |
| P3 | Manual AP processing cost and slowness | **$9.84** per invoice, **8.2 days** average cycle (Ardent 2025) | verified |
| P4 | Failed / delayed cross-border payments and investigations | **$118.5B** global cost of failed payments in 2020 (LexisNexis/Accuity); **$1.6B/yr** spent on investigations (Swift 2025) | verified |
| P5 | "Supplier says it never arrived": status opacity and double-pay risk | Investigations take **5–10 working days** (Swift); PAID is not final (Airwallex docs) | verified |
| P6 | Hidden FX markups on business payments | UK SMBs lost **£2.8B** in 2023 to hidden international payment fees, +27% since 2018 (Wise / Capital Economics) | verified |
| P7 | FX volatility hits unhedged SMEs | **54%** of UK SME traders hurt by currency volatility, avg loss **>£53k** (Bibby 2025) | search-index |
| P8 | Cash shortfalls and liquidity forecasting | **62%** of treasury pros call cash forecasting their #1 challenge (AFP 2025) | search-index |
| P9 | Late customer payments (AR) | **47%** of B2B invoices overdue in W. Europe, bad debt on **6%** (Atradius 2025); US SMBs owed **$17.5k** avg (Intuit 2025) | verified / search-index |
| P10 | India MSME delayed receivables | **₹7.34 lakh crore** delayed (Mar 2024, GAME-FISME); **₹8.1 lakh crore** (Economic Survey 2025–26) | search-index |
| P11 | India exporters & freelancers: inbound FX cost + FEMA/FIRA compliance | Export proceeds must be realised in **9 months** (RBI amendment, effective Oct 1, 2026); platform FX ~**1.6–2%** (comparison sites) | search-index |
| P12 | Month-end close and cash reconciliation | **50%** of teams take 6+ business days to close; cash rec **20–50 hrs/month** across 3–5 systems; Excel used by **94%** (Ledge 2025) | verified |
| P13 | Multi-currency bookkeeping (realised FX gain/loss, clearing accounts) | Qualitative (r/Accounting, r/xero threads) | qualitative |
| P14 | Chargebacks and friendly fraud | **$4.61** cost per $1 of fraud for US merchants (LexisNexis 2025); net chargeback recovery **10.7%** (Chargebacks911, vendor) | verified / vendor |
| P15 | Marketplace and seller cash held in reserves; conversion fees on payouts | Amazon ACCS fee **1.5%** below $500k trailing volume; DD+7 hold complaints | verified (Amazon page via search) / qualitative |
| P16 | SaaS spend sprawl and surprise renewals | **66.5%** of IT leaders saw unexpected SaaS charges; avg **$21M/yr** wasted on unused licenses (Zylo 2025, enterprise-skewed) | verified |
| P17 | Contractor and payroll payout errors | **$291** average cost per payroll error, **80.15%** accuracy (EY 2022, US) | search-index |
| P18 | Small cross-border transfers still expensive | Global average remittance cost **6.36%** of $200 (World Bank RPW Q3 2025) | verified (snippet of RPW PDF + RPW homepage) |
| P19 | Fintech account freezes and opaque support | Airwallex Trustpilot ~**3.1** vs G2 ~4.3; Payoneer ~3.5 on ~62.7k reviews | search-index |
| P20 | Trust gap for agents that spend money | Only **24%** of US online adults trust agents for routine purchases (Forrester 2025) | search-index |
| P21 | Internal billing and expense fraud | Orgs lose **5%** of revenue to fraud; billing schemes = 22% of cases, $100k median (ACFE 2024) | search-index |
| P22 | Fraud detection lives in treasury, but AI adoption lags | Treasury finds **83%** of attempted fraud; only **17%** of orgs use AI against payments fraud (AFP 2026) | verified |

---

## P1 · Vendor impersonation / BEC / redirected supplier payments
- **Who:** AP clerks, founders and finance leads paying suppliers by wire/ACH/local transfer, especially across borders, where they can't easily phone the supplier's bank.
- **What happens:** A fraudster spoofs a supplier's email (or compromises it) and sends "updated bank details" or a lookalike invoice. The payer edits the beneficiary and wires the money to a mule account. Cross-border recovery is slow and often fails.
- **Cost:**
  - AFP 2026 Payments Fraud & Control Survey (465 US treasury practitioners, Jan 2026): **74% of organizations were affected by BEC in 2025**. 76% had attempted or actual payments fraud. Financial losses were reported by 48% of orgs under $1B revenue. **(verified)**
  - AFP 2025 survey (2024 data, 521 respondents): BEC was the #1 avenue at 63%. **Vendor imposter fraud 45%, up 11 points.** Third-party impersonation was 63% of BEC types. **Wires were the payment method most targeted by BEC (63%, up from 39%).** Only 22% recovered ≥75% of lost funds (down from 41%). **(verified)**
  - FBI IC3 2024 report: **BEC losses $2,770,151,146** from 21,442 complaints. **(search-index**: IC3 PDF link from search, not opened)
- **Workaround today:** "Call-back" verification to a known phone number, dual approval in banking portals, manual checks of vendor master changes, staff training.
- **Why an agent helps:** It can diff every invoice's remittance details against the vendor's **bank-detail fingerprint on file**. A change, a new country, or name/IBAN/routing drift **quarantines** the payment, forces out-of-band verification and **requires a second human approval bound to the new details**. Code enforces it; the LLM only reads the email/PDF and explains the anomaly. Airwallex exposes `POST /api/v1/beneficiaries/verify_account` (account verification; its sandbox behaviour is unverified) and beneficiary update history via `POST /beneficiaries/{id}/update`.
- **Evidence:** https://www.prnewswire.com/news-releases/over-75-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags-302738857.html · https://www.financialprofessionals.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024 · https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf

## P2 · Duplicate and erroneous supplier payments
- **Who:** AP teams with invoices arriving by email, portal and paper, often several copies of the same invoice (reminder, PDF re-send, statement).
- **What happens:** The same invoice is keyed twice (different invoice-number formatting, a re-sent PDF, a credit note ignored), or a "failed" transfer is re-sent while the original still clears.
- **Cost:** APQC Open Standards Benchmarking: **median 1.5% of disbursements are duplicate or erroneous payments** (total sample 1,686 companies). **(verified)** Some secondary sites claim top performers at ~0.8% and the bottom at >2%. **(search-index, unverified)**
- **Workaround:** Exact-match ERP checks (vendor + invoice number), post-payment audit/recovery firms, spreadsheets.
- **Why an agent helps:** Fuzzy duplicate detection (normalized invoice numbers, amount ± tolerance, date window, PDF hash, line-item similarity read by the LLM) **before** payment. **Idempotent execution** (deterministic `request_id` per obligation and attempt, checked via `GET /api/v1/transfers?request_id=` before any retry). A **duplicate lock** per obligation so a replacement can't be issued until the original is terminal.
- **Evidence:** https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number · https://www.cfo.com/news/metric-of-the-month-detect-and-prevent-duplicate-or-erroneous-payments/656852/

## P3 · Manual AP: cost per invoice and cycle time
- **Who:** AP/finance ops at SMBs and mid-market companies.
- **What happens:** Invoices are keyed by hand, approvals chased in email, payment runs built in spreadsheets.
- **Cost:** Ardent Partners *State of ePayables 2025*: average all-inclusive **$9.84 to process one invoice**, **8.2-day** average cycle. Best-in-class: $2.65 and 2.9 days, vs **$12.42 and 13.5 days** for everyone else. **(verified**, PDF opened)
- **Workaround:** AP automation suites (Bill.com, Tipalti, Coupa), mostly domestic-first. Many SMBs still use spreadsheets + bank portal.
- **Why an agent helps:** The LLM extracts invoice data. Code validates it and routes approvals by policy. Payment runs execute directly on the money rails (Airwallex) instead of being re-keyed into a bank portal.
- **Evidence:** https://www.bottomline.com/cdn/1517/5157/1685/Ardent_Partners_-_State_of_ePayables_2025_-_Bottomline_-_FINAL.pdf

## P4 · Failed and delayed cross-border payments
- **Who:** Anyone paying abroad: SMB importers, platforms paying sellers, payroll operators.
- **What happens:** Payments bounce (name mismatch, closed account, wrong routing/BIC, missing purpose code), get stuck in compliance review at an intermediary, or return weeks later minus fees.
- **Cost:**
  - LexisNexis/Accuity: **failed payments cost the global economy $118.5B in 2020** (fees, labour, lost business). Corporates averaged ~$220k/yr, banks ~$360k/yr. **(search-index**: the press-release title is verified in search; numbers from the snippet)
  - Swift (Apr 17, 2025): the industry spends **>$1.6B a year** on labour-intensive investigations of held-up payments. Some large banks pay >$20M/yr in fees and penalties. "It can typically take **five to ten working days**" to investigate and resolve. 90% of Swift payments reach the end bank within an hour; delays come mostly from missing information. **(verified)**
  - BNY: ~5% of cross-border payments hit friction needing manual intervention. **(search-index)**
- **Workaround:** Ops staff open bank "traces", email screenshots of MT103s, re-send and hope.
- **Why an agent helps:** It validates payees *before* paying (`POST /beneficiaries/validate`, schema per corridor). It reads `failure_type` (`BENEFICIARY_NAME_MISMATCH`, `INVALID_BANK_OR_BRANCH_CODE`, `INVALID_PAYMENT_PURPOSE`, `ACCOUNT_CLOSED`, …), maps each to a remediation playbook, drafts the supplier request for corrected details, and only re-pays once the original is terminal.
- **Evidence:** https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20210714-true-cost-of-failed-payments · https://www.swift.com/news-events/press-releases/swift-solution-managing-cross-border-payments-investigations-could-save-industry-millions-operational-costs · https://www.bny.com/corporate/global/en/insights/payment-investigations-from-evolution-to-revolution.html

## P5 · "Supplier says it never arrived": status opacity and double-pay risk
- **Who:** Founders and ops leads under supplier pressure ("ship is held until paid").
- **What happens:** The payer sees "sent" or even "paid". The supplier sees nothing. Under deadline pressure the payer sends again, then both payments land. Or the first one fails *after* looking final.
- **Cost:** Swift: 5–10 working days to resolve an investigation (above). Airwallex's own docs: *"`PAID` is not always final. A transfer can still move to `FAILED` after `PAID` if it is later rejected by the local clearing system or the recipient bank."* **(verified via Airwallex Docs MCP)** A Reddit r/Banking thread: "sent a SWIFT transfer from abroad 10 business days ago and it still hasn't arrived" (qualitative).
- **Workaround:** Phone calls, UETR traces, manual "do not re-send" notes.
- **Why an agent helps:** A state machine that treats SENT/PAID as non-final, listens for `payout.transfer.failed` after PAID, and enforces a **wait / replace / escalate** decision with a duplicate lock. It sends the supplier a proof-of-payment pack (transfer id, reference, amount, timestamps) as a **draft** for a human to send.
- **Evidence:** Airwallex docs, transfer statuses: https://www.airwallex.com/docs/payouts/transfers/create-a-transfer/transfer-statuses.md · https://www.reddit.com/r/Banking/comments/1u2xjdl/ · https://airwallexdev.com/guide (kit 3)

## P6 · Hidden FX markups on business payments
- **Who:** SMB importers and exporters, e-commerce sellers, startups paying overseas contractors and SaaS.
- **What happens:** Banks quote "no fee" but embed a wide spread in the exchange rate. Businesses can't see the true cost, so they convert too often, in small amounts, at bad times.
- **Cost:** Wise / Capital Economics report ("The £2.8bn business problem"): **UK SMBs lost £2.8bn in 2023 to hidden fees on international payments, up 27% from £2.2bn in 2018.** **26%** are put off expanding overseas by the high cost of international banking. **(verified**, PDF opened) An older UK analysis estimated ~£4bn/yr and found 96% of bank revenue on a typical £75k EU transfer came from the FX spread. **(search-index)**
- **India-specific:** card forex markups of 1–3.5% plus GST on the markup for foreign SaaS paid by Indian startups. **(search-index**, tax-guide sites)
- **Workaround:** Switching to Wise/Airwallex/Revolut Business. Manual "convert once a month" habits.
- **Why an agent helps:** **Net obligations by currency**, convert once per run with a locked quote, prefer LOCAL rails over SWIFT where available (Airwallex sandbox: LOCAL fee 0 vs SWIFT EUR 12.85), and show the realised cost per payment in the run report.
- **Evidence:** https://wise.com/imaginary-v2/images/3377a6584910ba4ef7b4225eb5bff069-Wise%20%E2%80%94%20End%20the%20Opt%20Out%20Campaign.pdf · https://www.leaprate.com/news/sme-international-forex-transfers-generate-4-billion-in-hidden-uk-bank-fees-accourt/ · https://taxguru.in/goods-and-service-tax/foreign-software-subscriptions-attract-gst-reverse-charge-itc.html

## P7 · FX volatility on unhedged SMEs
- **Who:** SME importers and exporters with foreign-currency payables or receivables and no treasury function.
- **Cost:** Bibby Financial Services UK international trade report 2025: **54%** of SME traders negatively affected by currency volatility, **average loss >£53,000**. Only 36% of overseas traders use specialist FX providers. **(search-index)** Corpay 2025 Economic Outlook: **56% of businesses have no formal hedging policy.** **(search-index)** Mid-sized corporates hedge far more (81%, MillTechFX). **(search-index)**
- **Workaround:** Ad-hoc conversion when a bill is due, or none.
- **Why an agent helps:** Rule-based "convert the minimum now, lock a 24h quote for known near-term payables, leave the rest". It is *not* speculative: policy lives in code, quotes are bound to approvals, and the agent explains the trade-off.
- **Evidence:** https://www.bibbyfinancialservices.com/assets/documents/bltcaabb0e00358b2d2/blte04864e15d01ca6f/trading-places-bfs-international-trade-report-2025.pdf · https://www.leasinglife.com/news/uk-smes-count-cost-of-currency-volatility-average-53k-lost-in-2025/ · https://assets.ctfassets.net/h83dujey17us/4VayZIHNOpKZb4Xm3Aagv8/cdc4c33998f24c09bdccac615156fdf5/Economic_Outlook_Survey_2025.pdf

## P8 · Cash shortfalls: deciding what to pay when you can't pay everything
- **Who:** Founders and finance leads at startups and SMBs with lumpy receipts.
- **Cost:** AFP 2025 Treasury Benchmarking Survey: **cash/liquidity forecasting is the biggest challenge for 62%** of treasury professionals, and the top priority for 73%. **(search-index**, AFP PDF link from search)
- **Workaround:** A spreadsheet of "who screams loudest", paying critical suppliers late, emergency credit.
- **Why an agent helps:** This is exactly kit 1. A code-side planner ranks obligations by operational criticality, penalty and due date against a **reserve floor**. It defers the cheapest, escalates exceptions, and recalculates **only affected decisions** when a deposit lands.
- **Evidence:** https://7185359.fs1.hubspotusercontent-na1.net/hubfs/7185359/Research%20Surveys/SURVEYS/2025%20AFP%20Treasury%20Benchmarking%20Survey%20Comprehensive%20Report.pdf · https://airwallexdev.com/guide

## P9 · Late customer payments (AR)
- **Who:** SMB sellers, agencies, B2B exporters.
- **Cost:** Atradius Payment Practices Barometer, Western Europe 2025: **47% of B2B invoices overdue; bad debts hit 6% of B2B invoices.** **(verified**, PDF opened) Intuit QuickBooks 2025 US Small Business Late Payments Report (survey of 2,487 businesses, Jan 2025): **56% had unpaid invoices, owed $17,500 on average.** **(search-index**: the Intuit page returned HTTP 500 when fetched)
- **Workaround:** Manual dunning emails, factoring, giving up.
- **Why an agent helps:** It matches incoming deposits (Global Account `deposit.settled` webhooks / `GET /financial_transactions`) to open invoices across currencies, flags short-pays (fees deducted by intermediaries), drafts dunning messages and decides when to convert the receipts.
- **Evidence:** https://group.atradius.com/dam/jcr:80448207-97e5-4005-98b5-d5bb90e7107d/payment-practices-barometer-western-europe-2025-en.pdf · https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2025/

## P10 · India MSME delayed receivables
- **Who:** Indian MSMEs selling to larger buyers, domestically and abroad.
- **Cost:** GAME–FISME report: delayed payments to MSMEs **₹7.34 lakh crore as of March 2024** (down from ₹8.27 lakh crore in 2023 and ₹10.7 lakh crore in 2022), more than 4.6% of GVA. The Economic Survey 2025–26 estimates **₹8.1 lakh crore** stuck. **(search-index**, Economic Times / KNN / FISME)
- **Why an agent helps:** The same AR matching and dunning, plus deadline tracking. This sets up P11.
- **Evidence:** https://economictimes.indiatimes.com/small-biz/sme-sector/delayed-payments-to-msmes-in-india-decrease-to-rs-7-34-lakh-crore-but-challenges-persist-report/articleshow/125585516.cms · https://economictimes.indiatimes.com/small-biz/sme-sector/rs-8-1-lakh-crore-stuck-in-delayed-msme-payments-eco-survey-2026/articleshow/127765852.cms · https://fisme.org.in/study/delayed-payments-to-msmes-decline-from-rs-10-lakh-cr-to-rs-7-lakh-cr-but-challenges-persist-game-fisme-report/

## P11 · India exporters and freelancers receiving USD/EUR: cost and compliance
- **Who:** Indian service exporters (agencies, SaaS, freelancers) and goods exporters paid in USD/EUR/GBP.
- **What happens:**
  - The money arrives via a bank SWIFT (intermediary deductions + bank FX spread) or a platform (Payoneer/Wise/Skydo/Xflow) with markups or fees.
  - Each receipt needs a **FIRA/FIRC** and the correct **purpose code**, and must be matched to an invoice for GST (LUT for zero-rated export) and income tax.
  - Proceeds must be **realised within the FEMA deadline**. The RBI amendment of Sep 22, 2026 (effective Oct 1, 2026) keeps it at **9 months** but moves the clock to the invoice date for services. INR-invoiced exports get 12 months. EDPMS entries up to ₹10 lakh can be closed on declaration. **(search-index**: taxupdate.in, taxguru.in; verify on rbi.org.in)
- **Cost:** Comparison sites put platform costs at **~1.6–1.9% (Wise) + a ~$2–2.50 FIRA fee**, and **~2% FX markup** for Payoneer on direct invoices. **(search-index, vendor comparison pages: treat as unverified)** World Bank RPW: remittances to India cost **5.30%** of $200 on average. **(search-index**, secondary table built from RPW)
- **Workaround:** Spreadsheets of invoices vs credits, chasing banks for FIRCs, CAs reconciling at year-end. r/IndiaTax thread: "Indian freelancers who get paid internationally, what's your actual workflow for FIRA and taxes?" (qualitative)
- **Caveat for an Airwallex build:** Airwallex does **not** appear on RBI's PA-CB authorised list as of Sep 2026. Indian businesses reportedly onboard via Airwallex Singapore and receive into foreign-currency Global Accounts. **(search-index**, Skydo blog, a competitor) So adoption in India is uncertain. The sandbox demo is fine.
- **Evidence:** https://taxupdate.in/finance/983/fema-export-realisation-period-october-1-2026-nine-months-rbi-amendment/ · https://taxguru.in/rbi/fema-export-import-regulations-2026-key-effective-1-october.html · https://www.xflowpay.com/compare/wise-vs-payoneer · https://www.reddit.com/r/IndiaTax/comments/1tvgeuk/ · https://www.reddit.com/r/indianstartups/comments/1ufbl50/ · https://www.skydo.com/blog/airwallex-india-availability-fees

## P12 · Month-end close and cash reconciliation
- **Who:** Controllers, accountants, fractional CFOs.
- **Cost:** Ledge 2025 benchmark (100 finance professionals): **50% take 6+ business days to close** (18% 1–3 days, 32% 4–5, 23% 6–7, 27% >7). **Cash reconciliation is the #1 time sink at 20–50 hours/month, using 3–5 systems.** **94% use Excel** and 50% say it slows the close. Quote: "Cash reconciliation alone takes 30+ hours each month." **(verified)**
- **Workaround:** Exports from the bank, PSP and ERP matched by hand in Excel.
- **Why an agent helps:** When the agent *initiated* the payment, it already knows the obligation ↔ conversion ↔ payout ↔ fee linkage. It can auto-reconcile against `GET /api/v1/financial_transactions` (source types `PAYOUT`, `CONVERSION`, `FEE`, `DEPOSIT`; transaction types incl. `PAYOUT_FAILURE`, `PAYOUT_REVERSAL`) and `GET /api/v1/balances/history`, then produce a tie-out. **Airwallex explicitly names reconciliation as an unwritten kit "few builders will take on".**
- **Evidence:** https://www.ledge.co/content/month-end-close-benchmarks-for-2025 · https://www.cfo.com/news/50-of-finance-take-week-to-close-books-ledge-month-end-close-time-cfo-three-day-close-myth-/746085/ · https://airwallexdev.com/guide

## P13 · Multi-currency bookkeeping: realised FX gain/loss and clearing accounts
- **Who:** Bookkeepers for companies invoicing or paying in several currencies (Xero/QBO users).
- **What happens:** An invoice is booked at one rate and paid at another, with bank fees deducted in between. People can't figure out where the difference goes, so they "invoice everything in USD" and push FX risk onto customers.
- **Cost:** Qualitative only. r/Accounting: "invoicing in different currencies creating reconciliation mess!!! should I just invoice everything in USD?"; r/AccountingDepartment: "Need help with foreign currency bookkeeping and bank reconciliation"; r/xero multicurrency threads.
- **Why an agent helps:** It emits journal lines with booking rate vs settlement rate, a fee line and a realised FX gain/loss line per payment, in an import-ready CSV.
- **Evidence:** https://www.reddit.com/r/Accounting/comments/1rio68b/ · https://www.reddit.com/r/AccountingDepartment/comments/1v0p9bm/ · https://www.reddit.com/r/xero/comments/1sjpn88/

## P14 · Chargebacks and friendly fraud
- **Who:** Online merchants, DTC brands, SaaS.
- **Cost:** LexisNexis True Cost of Fraud 2025 (569 US/Canada execs): **US merchants incur $4.61 for every $1 of fraud** (Canada $4.52). 41% still rely on manual fraud processes. **(verified)** Chargebacks911 (a chargeback vendor, so treat as biased): merchants win ~44% of represented chargebacks but **net recovery is only 10.7%**, and 72% of cardholders see disputes as a valid alternative to refunds. **(verified on the vendor page; vendor data)** Shopify: a $15 chargeback fee, returned only if you win. **(search-index)**
- **Workaround:** Manual evidence packs, outsourced representment, or accepting everything.
- **Why an agent helps:** This is kit 4. It runs per-case economics (fee vs amount vs win probability vs deadline), assembles an evidence pack, uploads it (JPG/PDF only), escalates the ambiguous case, and never re-sends rejected evidence.
- **Evidence:** https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20250402-tcof-ecommerce-and-retail · https://chargebacks911.com/chargeback-stats/ · https://www.reddit.com/r/shopify/comments/1okb701/ · https://help.shopify.com/en/manual/payments/chargebacks/chargeback-process

## P15 · Marketplace sellers: cash held in reserves, and conversion fees on payouts
- **Who:** Amazon/marketplace sellers, especially international ones. Marketplace operators on the other side.
- **Cost:** Amazon Currency Converter for Sellers: **1.50% fee** on cross-currency payouts below $500k trailing 12-month proceeds (1.25% → 0.75% at higher tiers), on top of the provider rate. **(search-index**, Amazon program page) Seller forum and Reddit complaints about **DD+7** (funds held until 7 days after delivery) and account-level reserves squeezing cash flow. **(qualitative)**
- **Why an agent helps:** On the platform side (kit 8), per-seller risk-based reserves, recomputed only for the affected seller. On the seller side, receive in local Global Accounts and convert on schedule.
- **Evidence:** https://sell.amazon.com/programs/amazon-currency-converter · https://www.reddit.com/r/FulfillmentByAmazon/comments/1sk0uqc/ · https://sellercentral.amazon.com/seller-forums/discussions/t/508f864b-9bbc-4c38-bf6f-2c5913304009

## P16 · SaaS spend sprawl and surprise renewals
- **Who:** Startup founders and ops leads. Every employee with a company card.
- **Cost:** Zylo 2025 SaaS Management Index (40M licenses, $40B spend under management): **66.5% of IT leaders reported unexpected SaaS charges** from consumption/AI pricing. Organizations waste **$21M/yr on unused licenses** on average (enterprise-skewed). SaaS spend is **$4,830 per employee (+21.9% YoY)**. Lines of business now control 70% of SaaS spend. **(verified)**
- **Why an agent helps:** This is kit 2. One virtual card per vendor with limits and an MCC/currency allowlist enforcing the purchase decision. Auto-freeze before renewal unless someone re-approves.
- **Evidence:** https://zylo.com/news/2025-saas-management-index

## P17 · Contractor and payroll payout errors
- **Who:** Payroll operators and startups paying international contractors.
- **Cost:** EY 2022 HR processing risk and cost survey (US, 508 respondents): payroll accuracy **80.15%**, ~15 corrections per pay period, **$291 average cost per error**. **(search-index**, the Business Wire release in search) Deel ~$49/contractor/month (review site, unverified).
- **Why an agent helps:** This is kit 6. Price fees before converting, keep employer funds isolated, validate beneficiaries per corridor.
- **Evidence:** https://www.businesswire.com/news/home/20221222005093/en/EY-survey-Payroll-errors-average-%24291-each-impacting-the-economy · https://www.reddit.com/r/fintech/comments/1rvsakg/

## P18 · Small cross-border transfers are still expensive
- **Cost:** World Bank Remittance Prices Worldwide, Q3 2025: global average cost of sending $200 is **6.36%** (down from 6.49% in Q1 2025). Digital is 4.59%, non-digital 7.30%. The RPW homepage states 6.36%. **(verified via the RPW homepage text + PDF snippet)** Banks are the costliest channel at ~14.99% (secondary site built on RPW, unverified).
- **Relevance:** This is consumer remittance, not B2B. It's useful context for contractor payouts and micro-exporters, but don't pitch it as the core B2B pain.
- **Evidence:** https://remittanceprices.worldbank.org/ · https://remittanceprices.worldbank.org/sites/default/files/2026-04/RPW_main_report_and_annex_Q325.pdf

## P19 · Fintech account freezes and opaque support
- **Who:** SMBs that depend on one fintech for all their money movement.
- **Cost / signal:** Airwallex ~**3.1/5 on Trustpilot** vs ~**4.3/5 on G2** (review aggregator). Recurring complaints: sudden suspensions, funds frozen during compliance reviews, slow generic support. Payoneer ~**3.5/5 from ~62.7k Trustpilot reviews**, with complaints about blocked accounts and held funds. **(search-index**; G2, Capterra and Trustpilot block automated fetches)
- **Design implication:** An agent that moves money must be **transparent**: every action explained, logged and reversible where possible. It should also hold a reserve floor and **escalate rather than retry** when the provider returns compliance errors (e.g. `ACCOUNT_UNDER_RESTRICTION`, `TM_SUSPENDED`).
- **Evidence:** https://www.paymentprocessingguide.com/processor/airwallex/reviews · https://www.trustpilot.com/review/airwallex.com · https://www.trustpilot.com/review/www.payoneer.com

## P20 · The trust gap for agents that spend money
- **Cost / signal:** Forrester 2025: only **24%** of US online adults trust agents for routine purchases. Contentsquare: 30% would let an agent complete a purchase. A Worldpay-cited figure: **only 6% would allow automatic purchases without checking first**. **(search-index)**
- **Design implication:** Judges ask about "controlled autonomy". Approvals must be **bound to exact terms** and invalidated on any change, with tiered autonomy that is earned (e.g. auto only for known payees, unchanged bank details and amounts under a limit).
- **Evidence:** https://www.forrester.com/report/many-us-consumers-believe-in-agentic-commerce-but-few-trust-it-to-make-purchases/RES188737 · https://contentsquare.com/press/ai-is-reshaping-online-shopping/ · https://www.worldpay.com/en-GB/news/ai-agents-set-transform-how-americans-shop-261-billion-predicted

## P21 · Internal billing and expense fraud
- **Cost:** ACFE Report to the Nations 2024: organizations lose **~5% of revenue** to occupational fraud. **Billing schemes** are 22% of cases with a $100k median loss. **Expense reimbursement** schemes are 13% with a $50k median. **(search-index**, ACFE PDF linked)
- **Why an agent helps:** Segregation of duties enforced in code (the requester can't approve their own payee), anomaly flags on new vendors, and policy checks before money moves.
- **Evidence:** https://www.acfe.com/-/media/files/acfe/pdfs/rttn/2024/2024-report-to-the-nations.pdf

## P22 · Treasury catches the fraud, but tooling lags
- **Cost / signal:** AFP 2026: treasury is the department most likely to discover **attempted (83%)** and **actual (55%)** fraud. **Only 17%** of organizations use AI to fight payments fraud. Smaller firms "are much more likely to absorb the full financial loss". **(verified)**
- **Implication:** There is room for an operator-grade agent at SMB scale that does what big-company treasury does: verification, disciplined approvals, timely detection.
- **Evidence:** https://www.prnewswire.com/news-releases/over-75-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags-302738857.html

---

## Cross-cutting takeaways for the idea
1. The **costliest, most-cited, best-evidenced** pains sit around the **supplier payment run**: fraud (P1), duplicates (P2), manual AP (P3), failures (P4/P5), FX leakage (P6) and reconciliation afterwards (P12/P13).
2. These map onto **kits 1 + 3 plus the reconciliation gap** Airwallex flagged. **No special access is needed.**
3. Judges reward **operational foundation + controlled autonomy**. Approval binding, idempotency, a finality-aware state machine and a reconciliation tie-out *are* that foundation.
4. India exporters (P10/P11) are a strong secondary market, but Airwallex's India licensing status is a real adoption risk. That makes it a runner-up, not the winner.
