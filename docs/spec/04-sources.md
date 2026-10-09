# 04 · Sources

Accessed **Oct 8, 2026 (IST)**. Labels:
- **[V]** = page or PDF opened and the content seen.
- **[S]** = known from search-index results or snippets only; the page was blocked, errored, or not opened.
- **[Q]** = qualitative (forum or Reddit), cited for sentiment only. Reddit blocked direct fetches with HTTP 403.

## Hackathon (official)
- [V] HackerEarth challenge page (phases, team size, registrations, generic FAQ): https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/
- [V] Same page, canonical URL: https://www.hackerearth.com/challenges/hackathon/agentic-banking-hackathon/
- [S] Registration / idea form (login required, fields not visible): https://www.hackerearth.com/community/challenges/hackathon/agentic-banking-hackathon/?register=true
- [V] Landing page (tracks, key dates, prizes, partners, FAQ): https://airwallex.hackerearth.com/
- [V] Landing "About" image (48 hours / 3 weeks / 12 tracks): https://uc.hackerearth.com/he-s3-ap-south-1/media/sprint/agentic-banking-hackathon/editor/editor_image_2733610_62fda2e.png
- [V] Builder guide (kits, access, conventions, sandbox constraints): https://airwallexdev.com/guide
- [V] Developer lab home (MCP configs, webhooks, simulation notes): https://airwallexdev.com/
- [V] Builds page + JSON (reference builds, agent recipes): https://airwallexdev.com/builds · https://airwallexdev.com/content/builds.json · https://airwallexdev.com/content/library.json
- [S] Reference build repos: https://github.com/awx-devx/airwallex-agent-cards · https://github.com/awx-devx/awx-drop-in-checkout · https://github.com/awx-devx/airwallex-slack-bot · https://github.com/awx-devx/airwallex-finance-manager · https://github.com/awx-devx/airwallex-allocard
- [S] Dan Kim (Airwallex) launch post (partners, prize split): https://nitter.cf/dankimxyz/status/2107146234020684187
- [S] Dan Kim LinkedIn, Sep 24, 2026 ("$70k, up from $50k"): https://www.linkedin.com/posts/danieljkim_the-airwallex-agentic-banking-hackathon-will-activity-7508933085132922880-HNRC
- [S] Third-party summary: https://devgrantsdaily.com/items/2026-10-06-airwallex-agentic-banking-hackathon/

## Judge signals
- [S] Sam Waldo, "Judging the Agents, Everywhere hackathon" (criteria): https://www.linkedin.com/posts/sam-waldo_judging-the-agents-everywhere-hackathon-activity-7500783609373462528-jCSr
- [S] AI Tinkerers Singapore post (5 judge questions): https://www.linkedin.com/posts/ai-tinkerers-singapore_what-happens-when-ai-agents-move-beyond-conversationand-activity-7500499794403049472-36H9
- [S] Sam Waldo recap (favourite: invoice agent with explicit human approval): https://www.linkedin.com/posts/sam-waldo_aitinkerers-agentseverywhere-agentos-activity-7506525100737929216-Jhgg

## Airwallex docs (via the public Docs MCP `https://mcp.sandbox.airwallex.com/docs`, tool `search_public_docs`) [V]
- Financial transactions (list): https://www.airwallex.com/docs/api/finance/financial_transactions/list.md
- Transfers (retrieve, list, statuses incl. late failure after PAID): https://www.airwallex.com/docs/api/payouts/transfers.md · https://www.airwallex.com/docs/payouts/transfers/create-a-transfer/transfer-statuses.md · https://www.airwallex.com/docs/payouts/transfers/manage-transfers/handle-failed-transfers.md
- Transfer simulation (failure_type values): POST /api/v1/simulation/transfers/{id}/transition
- Transfer webhooks: https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events/transfers.md
- Beneficiaries (create, list, update, validate, verify_account, schemas): https://www.airwallex.com/docs/api/payouts/beneficiaries/verify_account.md and siblings
- Balance history: https://www.airwallex.com/docs/api/core_resources/balances/history.md
- FX quotes (validity options, valid_to_at): https://www.airwallex.com/docs/api/transactional_fx/quotes/create.md
- Financial reports (TRANSACTION_RECON_REPORT): POST /api/v1/finance/financial_reports/create
- Stablecoin payouts (USDC on Ethereum, account-manager enablement): https://www.airwallex.com/docs/payouts/payout-network/stablecoin-wallets.md
- API intro / sandbox / AgentOS / Postman / webhooks: https://www.airwallex.com/docs/api/introduction · https://www.airwallex.com/docs/developer-tools/sandbox-environment · https://www.airwallex.com/docs/developer-tools/ai/agentos · https://www.airwallex.com/docs/developer-tools/api/quickstart-with-postman · https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events

## Partner tooling
- [S] Visa Intelligent Commerce: https://developer.visa.com/capabilities/visa-intelligent-commerce
- [S] Visa Trusted Agent Protocol docs/spec: https://developer.visa.com/capabilities/trusted-agent-protocol/docs · https://developer.visa.com/capabilities/trusted-agent-protocol/trusted-agent-protocol-specifications/
- [S] TAP sample implementation: https://github.com/visa/trusted-agent-protocol
- [S] VIC on Visa Acceptance prerequisites (MID, token requester ID, relationship ID): https://developer.visaacceptance.com/docs/vas/en-us/intelligent-commerce/developer/all/rest/intelligent-commerce/intelligent-commerce-intro-requirements.html
- [V] Metal L2 testnet faucets: https://docs.metall2.com/builders/tools/build/faucets
- [S] Metal L2 tools / Metal Blockchain / Metallicus developers: https://docs.metall2.com/builders/tools · https://metallicus.com/developers/metal-blockchain · https://metalblockchain.org/ · https://metallicus.com/developers

## Pain evidence (see 01 for how each is used)
- [V] AFP 2026 Payments Fraud & Control (BEC 74%, AI 17%, treasury detects 83%): https://www.prnewswire.com/news-releases/over-75-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags-302738857.html
- [V] AFP 2025 press release (79% fraud, BEC 63%, vendor imposter 45%, wires 63%): https://www.financialprofessionals.org/about/learn-more/press-releases/Details/survey-79-percent-of-organizations-were-victims-of-attempted-or-actual-payments-fraud-activity-in-2024
- [S] AFP 2025 full report PDF: https://7185359.fs1.hubspotusercontent-na1.net/hubfs/7185359/Research%20Surveys/SURVEYS/2025%20Payments%20Fraud%20and%20Control%20Survey%20Report%20Comprehensive.pdf
- [S] FBI IC3 2024 report (BEC $2.77B): https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf · https://www.fbi.gov/news/press-releases/fbi-releases-annual-internet-crime-report
- [V] APQC duplicate/erroneous payments median 1.5%: https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-total-annual-number
- [S] CFO.com metric of the month (duplicates): https://www.cfo.com/news/metric-of-the-month-detect-and-prevent-duplicate-or-erroneous-payments/656852/
- [V] Ardent Partners State of ePayables 2025 ($9.84, 8.2 days): https://www.bottomline.com/cdn/1517/5157/1685/Ardent_Partners_-_State_of_ePayables_2025_-_Bottomline_-_FINAL.pdf
- [S] LexisNexis/Accuity failed payments $118.5B: https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20210714-true-cost-of-failed-payments
- [V] Swift investigations $1.6B/yr, 5–10 working days: https://www.swift.com/news-events/press-releases/swift-solution-managing-cross-border-payments-investigations-could-save-industry-millions-operational-costs
- [S] Swift exceptions & investigations paper: https://www.swift.com/sites/default/files/files/its-time-to-transform-exceptions-and-investigations-april2025.pdf
- [S] BNY payment investigations: https://www.bny.com/corporate/global/en/insights/payment-investigations-from-evolution-to-revolution.html
- [V] Wise / Capital Economics £2.8bn hidden fees: https://wise.com/imaginary-v2/images/3377a6584910ba4ef7b4225eb5bff069-Wise%20%E2%80%94%20End%20the%20Opt%20Out%20Campaign.pdf
- [S] UK £4bn SME FX fees (Accourt): https://www.leaprate.com/news/sme-international-forex-transfers-generate-4-billion-in-hidden-uk-bank-fees-accourt/
- [S] Bibby Financial Services 2025 international trade report: https://www.bibbyfinancialservices.com/assets/documents/bltcaabb0e00358b2d2/blte04864e15d01ca6f/trading-places-bfs-international-trade-report-2025.pdf · https://www.leasinglife.com/news/uk-smes-count-cost-of-currency-volatility-average-53k-lost-in-2025/
- [S] Corpay Economic Outlook 2025: https://assets.ctfassets.net/h83dujey17us/4VayZIHNOpKZb4Xm3Aagv8/cdc4c33998f24c09bdccac615156fdf5/Economic_Outlook_Survey_2025.pdf
- [S] MillTechFX hedging: https://tradetreasurypayments.com/articles/81-of-corporates-now-hedging-fx-risk-new-milltechfx-data-shows
- [S] AFP 2025 Treasury Benchmarking (forecasting 62%): https://7185359.fs1.hubspotusercontent-na1.net/hubfs/7185359/Research%20Surveys/SURVEYS/2025%20AFP%20Treasury%20Benchmarking%20Survey%20Comprehensive%20Report.pdf
- [V] Atradius Payment Practices Barometer W. Europe 2025: https://group.atradius.com/dam/jcr:80448207-97e5-4005-98b5-d5bb90e7107d/payment-practices-barometer-western-europe-2025-en.pdf
- [S] Intuit QuickBooks 2025 late payments report (page returned HTTP 500): https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2025/
- [S] India MSME delayed payments: https://economictimes.indiatimes.com/small-biz/sme-sector/delayed-payments-to-msmes-in-india-decrease-to-rs-7-34-lakh-crore-but-challenges-persist-report/articleshow/125585516.cms · https://economictimes.indiatimes.com/small-biz/sme-sector/rs-8-1-lakh-crore-stuck-in-delayed-msme-payments-eco-survey-2026/articleshow/127765852.cms · https://fisme.org.in/study/delayed-payments-to-msmes-decline-from-rs-10-lakh-cr-to-rs-7-lakh-cr-but-challenges-persist-game-fisme-report/
- [S] FEMA export realisation (RBI amendment, effective Oct 1, 2026): https://taxupdate.in/finance/983/fema-export-realisation-period-october-1-2026-nine-months-rbi-amendment/ · https://taxguru.in/rbi/fema-export-import-regulations-2026-key-effective-1-october.html · https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12908&Mode=0
- [S] India inbound payment cost comparisons (vendor pages): https://www.xflowpay.com/compare/wise-vs-payoneer · https://www.indietoolkit.in/blog/how-to-accept-international-payments-indian-freelancer
- [S] Airwallex India availability (competitor blog): https://www.skydo.com/blog/airwallex-india-availability-fees
- [S] GST on foreign SaaS (reverse charge, forex markup): https://taxguru.in/goods-and-service-tax/foreign-software-subscriptions-attract-gst-reverse-charge-itc.html
- [V] Ledge month-end close benchmarks 2025: https://www.ledge.co/content/month-end-close-benchmarks-for-2025
- [S] CFO.com on Ledge: https://www.cfo.com/news/50-of-finance-take-week-to-close-books-ledge-month-end-close-time-cfo-three-day-close-myth-/746085/
- [V] LexisNexis True Cost of Fraud 2025 ($4.61): https://risk.lexisnexis.com/global/en/about-us/press-room/press-release/20250402-tcof-ecommerce-and-retail
- [V] Chargebacks911 stats (vendor): https://chargebacks911.com/chargeback-stats/
- [S] Shopify chargeback process: https://help.shopify.com/en/manual/payments/chargebacks/chargeback-process
- [S] Amazon Currency Converter for Sellers: https://sell.amazon.com/programs/amazon-currency-converter
- [Q] Amazon seller forums on DD+7: https://sellercentral.amazon.com/seller-forums/discussions/t/508f864b-9bbc-4c38-bf6f-2c5913304009
- [V] Zylo 2025 SaaS Management Index: https://zylo.com/news/2025-saas-management-index
- [S] EY payroll errors $291: https://www.businesswire.com/news/home/20221222005093/en/EY-survey-Payroll-errors-average-%24291-each-impacting-the-economy
- [V]/[S] World Bank Remittance Prices Worldwide (6.36% Q3 2025): https://remittanceprices.worldbank.org/ · https://remittanceprices.worldbank.org/sites/default/files/2026-04/RPW_main_report_and_annex_Q325.pdf
- [S] Secondary RPW table (by country/channel): https://arcawallet.app/research/true-cost-of-sending-200-by-country/
- [S] Airwallex / Payoneer reviews: https://www.paymentprocessingguide.com/processor/airwallex/reviews · https://www.trustpilot.com/review/airwallex.com · https://www.trustpilot.com/review/www.payoneer.com · https://statrys.com/reviews/payoneer-business-account
- [S] Ramp vs Brex international limits: https://www.airwallex.com/en-us/blog/ramp-vs-brex-comparison · https://www.g2.com/compare/brex-vs-ramp-financial-ramp
- [S] Agentic commerce trust: https://www.forrester.com/report/many-us-consumers-believe-in-agentic-commerce-but-few-trust-it-to-make-purchases/RES188737 · https://contentsquare.com/press/ai-is-reshaping-online-shopping/ · https://www.worldpay.com/en-GB/news/ai-agents-set-transform-how-americans-shop-261-billion-predicted · https://www.americanbanker.com/payments/news/consumers-are-warming-up-to-agentic-payments
- [S] ACFE Report to the Nations 2024: https://www.acfe.com/-/media/files/acfe/pdfs/rttn/2024/2024-report-to-the-nations.pdf
- [S] Stripe Connect risk/reserves (marketplace context): https://docs.stripe.com/connect/risk-management · https://docs.stripe.com/connect/marketplace/tasks/refunds-disputes

## Reddit / forums (qualitative, [Q])
- https://www.reddit.com/r/IndiaTax/comments/1tvgeuk/indian_freelancers_who_get_paid_internationally/
- https://www.reddit.com/r/indianstartups/comments/1ufbl50/best_way_to_receive_international_client_payments/
- https://www.reddit.com/r/FreelanceIndia/comments/1vp1b6n/receiving_international_payments_as_a_freelancer/
- https://www.reddit.com/r/Accounting/comments/1rio68b/invoicing_in_different_currencies_creating/
- https://www.reddit.com/r/AccountingDepartment/comments/1v0p9bm/need_help_with_foreign_currency_bookkeeping_and/
- https://www.reddit.com/r/xero/comments/1sjpn88/question_on_multicurrency_support_for_real_xero/
- https://www.reddit.com/r/FulfillmentByAmazon/comments/1sk0uqc/am_i_bugged_or_is_everyone_really_chill_about/
- https://www.reddit.com/r/Banking/comments/1u2xjdl/
- https://www.reddit.com/r/shopify/comments/1okb701/we_need_to_talk_about_chargebacks_this_system_is/
- https://www.reddit.com/r/shopify/comments/1uv9vpb/when_you_win_a_shopify_chargeback_what_evidence/
- https://www.reddit.com/r/ecommerce/comments/1v5d7ty/were_paying_fx_on_every_transaction_to_our_china/
- https://www.reddit.com/r/ecommerce/comments/1vcf4x2/how_do_you_pay_chinese_vendors_who_only_have_a/
- https://www.reddit.com/r/fintech/comments/1rvsakg/cheapest_way_to_pay_contractors_in_8_countries/
- https://www.reddit.com/r/smallbusiness/comments/warxpa/dont_use_wise_transferwise_for_money_transfers/
- https://community.shopify.com/t/charge-back-on-an-item-successfully-delivered-with-tracking-evidence/347448

## Raw captures (in `raw/` inside this folder)
HackerEarth HTML + decoded flight data (`he_flight.txt`), landing HTML, airwallexdev builds/library JSON, Docs MCP query outputs (`doc_*.txt`), and PDF text extractions (Ardent, Wise, Atradius).
