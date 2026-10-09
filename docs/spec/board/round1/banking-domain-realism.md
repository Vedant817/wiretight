> **Superseded by D3 (S2 chosen).** Finished just before the stop; not reviewed further.

# Round 1b: domain-realism check on S1 Ledgerline

**Author:** AB Banking Domain · **Date:** 2026-10-08 · **Lens:** would a treasury or AR person recognise this?

Checked against Staff Engineer's conditions in `round1/staff-engineer-feasibility.md`: the refund beneficiary comes from a customer-master fixture, and beat 3 uses a `REJECTED` deposit instead of a bank-transfer reversal.

## Verdicts

1. **Customer master as the refund destination is honest, with a label.** Once a receipt is credited, a refund is a *new* outgoing credit transfer, and ERPs take the destination from the customer (or vendor) master, not from the email asking for it. A scheme return (pacs.004) is a different thing, and the company does not initiate it. Show `source: customer master, verified <date>`, matched to the deposit on payer name and country, and say that in production you would cross-check against the ordering-party account on the statement when the bank actually sends one.
2. **`REJECTED` is a fair stand-in for "this cash never became usable." It is a bad stand-in for "we booked it and it came back."** Use it for a receipt that arrives rejected and is never applied. Do not narrate it as a reversal. A settle-then-reverse belongs on `REVERSED`, which Airwallex documents as a recall after the wallet was credited, and which the sandbox cannot simulate for bank transfers.
3. **The hybrid lock is what good treasury teams already do.** Block any new or changed destination until someone calls a number already on file, and keep maker-checker on the payment. Do not put that same friction on a refund to an unchanged master account. Confirmation of Payee and Verification of Payee are name checks at the moment of payment. They do not prove the account is the one the money came from.

---

## 1. Where the refund account really comes from

**The workflow splits in two, and only one of them is the company's job.**

A payment that never gets credited is sent back by the *beneficiary's bank*, on the original rails, to the originator. The company never chooses an account. The EPC SEPA Credit Transfer rulebook (EPC125-05, 2025 v1.1, §4.3.2.2) says a Return happens when the credit transfer cannot be executed (wrong or closed account) so the beneficiary account is not credited, and: *"The Return procedure must not be used in cases where the Beneficiary's account has already been credited and the Beneficiary wishes to return the funds. Instead, the procedure of initiating a new SEPA Credit Transfer applies."* The Return message (pacs.004, data set DS-03) goes back along the original path with the original amount. A Recall is different again: only the originator's bank starts it (camt.056), and only for duplicate, technical error, or fraud. So "return to source" is a bank operation. A customer refund of a duplicate or overpayment, after the cash has landed, is a brand-new credit transfer, and someone has to name the destination.

**That destination is looked up, in this order.**

- **Customer master, when you are the one sending the money.** SAP's online-payment process (transaction F111) is explicit: for a customer payment request you enter the customer account and *"the system automatically adopts the name, address, and bank details from the master record."* A free-form payment can also "adopt this information from the vendor or customer master record" rather than typing it. A release step can be required before the payment runs. https://help.sap.com/doc/9960d353c6244308e10000000a174cb4/700_SFIN3E%20006/en-US/0be98e7c07294a31acb6b4ad04aa9296.html Customer bank details are often thin compared with a vendor master, because you rarely pay customers. They get populated from onboarding, a direct-debit mandate, or a previous verified refund, not from every inbound receipt.
- **The bank statement's ordering party, as a cross-check, not as a guaranteed field.** ISO 20022 camt.053 puts the payer on the credit entry under `Ntry/NtryDtls/TxDtls/RltdPties`: `Dbtr` is "the party that owes an amount of money to the (ultimate) creditor," and `DbtrAcct` is that party's account. Bank implementations mark both optional. Goldman Sachs's camt.053 guide says `Dbtr/Nm` and `DbtrAcct` (IBAN or account id) are "provided in case of a credit payment" and are `[0..1]`. https://developer.gs.com/docs/services/transaction-banking/camt-details/ The older SWIFT path is the same shape. MT103 tag 50a is the ordering customer (account, name, address) and tag 52A is the ordering institution. BNP Paribas's MT940 specification maps statement field 86 `/ORDP/NAME/` to MT103 tag 50a and marks it optional, maps `/INFO/` to "account number of the originator" and marks that optional too, and maps `/OBK/` to tag 52A. https://www.bnpparibas.de/app/uploads/sites/21/2022/04/mt940-details.pdf So a real statement sometimes has a name only. Airwallex says the same thing about its own deposits: *"Depending on the Global Account financial institution & payment method, the availability of deposit details (e.g. payer name, payer bank account number etc.) will vary,"* and the `bank_account` object can be country-specific, an IBAN, a SWIFT account, or `partial`. https://www.airwallex.com/docs/global-treasury/receive-funds/receive-bank-transfers-to-global-accounts/retrieve-your-deposits
- **Remittance advice does not carry the account.** It tells you which invoices the payment covers. Useful for matching, useless as a payee.
- **Asking the customer is the fraud path.** The email that says "please refund the duplicate to this new IBAN" is the same pattern as a vendor-bank-detail change. AFP's guidance is to verify changes to bank details with a callback to a number from the system of record, never the number in the email. One respondent: *"When a new vendor is set up, or an existing vendor changes their banking information, treasury contacts that vendor through their main phone line… We do NOT call the vendor at the phone number they supplied us."* https://www.financialprofessionals.org/training-resources/resources/articles/Details/4-ways-to-reduce-payments-fraud

**Is the fixture honest?** Yes, for the leg Ledgerline actually performs: a new transfer to a known customer, after the deposit's `payer_name` and `payer_country` match that customer. It is not honest if the screen says "refunded to the account the deposit came from," because the sandbox deposit has no account to come from (Staff Engineer, condition 2).

Label every refund card:

> Source: customer master, verified on <date>. Matched to this deposit on payer name and country only. In production this account is paid only if it agrees with the ordering-party account on the statement (`DbtrAcct`, or MT103 field 50) when the bank sent one. An account taken from an email is never paid.

That caveat is what makes it honest. It also matches how the controls work: a master-data change is the sensitive event, and it gets the same treatment as a vendor-master change (dual control, no email as evidence, callback before the new account can be paid).

## 2. Is `REJECTED` "the payment didn't land"?

**On Airwallex, for a bank transfer, yes. As a reversal, no.**

Bank-transfer deposit statuses (https://www.airwallex.com/docs/global-treasury/receive-funds/receive-bank-transfers-to-global-accounts/bank-transfer-deposit-statuses):

| Status | Airwallex's words |
|---|---|
| `PENDING` | "Deposit has arrived and is on hold for review. Most deposits are auto-cleared and moved into the settled state." |
| `SETTLED` | "Deposit has been credited to your Wallet balance." |
| `REJECTED` | "Deposit was rejected and the funds will be returned to the original source." |

The webhook page splits the two failure modes (https://www.airwallex.com/docs/developer-tools/webhooks/listen-for-webhook-events/deposits):

- `deposit.rejected`: "Deposit is rejected after being reviewed by Airwallex or the clearing system."
- `deposit.reversed`: "Deposit is recalled by the payer's bank after the funds were settled to your Wallet."

So `REJECTED` means the money was turned around before it became spendable balance. `REVERSED` means it was credited and later pulled back. The simulator can create a Global Account deposit already in `REJECTED`. It cannot reverse a bank-transfer deposit. `POST /simulation/deposits/{id}/reverse` is documented for direct debits only.

**How treasury sees the same facts.**

- A **rejection or return before credit** is ordinary. SEPA Return (§4.3.2.2, above) is exactly this: interbank settlement happened, the beneficiary account was not credited, and the funds go back on the original path. Airwallex's `REJECTED` line ("funds will be returned to the original source") is that story. A treasurer accepts it.
- A **recall or return after credit** is the beat the shortlist originally wrote. The payer's bank asks for the money back (SEPA Recall, a pacs.004 with reason FOCR, or an ACH return). NACHA maps those to camt.053 as reversals: the entry carries `RvslInd` true and bank transaction code `RRTN`, "reversal due to return," and the return keeps the original account fields. https://www.nacha.org/system/files/2023-08/NACHA_ISO20022_Guide_camt.053_returns%2008-09-23.pdf The cash was in the book, then it wasn't. That is Airwallex `REVERSED`, not `REJECTED`.
- **Unapplied or suspense cash is neither.** The cash did land. You just cannot tell which invoice it pays. Putting it on a `REJECTED` deposit would confuse the person you are demoing to.

**Framing that will not get a frown.** A customer email says "we paid invoice 1042." The matching deposit arrives `REJECTED`. The invoice stays open, the cash is not counted, a chase is drafted, and the surplus available to convert gets smaller. On-screen label: "Rejected by Airwallex or the clearing system. Not credited. Not a reversal." Keep a settle-then-reverse only as an own-ledger event, with the Staff Engineer's label that the sandbox cannot reverse a bank-transfer deposit.

## 3. The hybrid lock

A lock that refuses any new or changed destination account until it is confirmed out of band is realistic, and it is the control treasury teams already run on vendor-master changes. It should apply to a customer-master change for the same reason: the fraud is the change of destination, not the fact that the payee is a customer rather than a supplier. AFP (23 Apr 2024, citing its 2024 survey) says 93% of respondents rated both of these as effective or highly effective: a policy to verify any change to invoices, bank-deposit information and contact details, and a callback to a verified contact at the payee using a phone number from a system of record. The quoted practice is to call the main line already on file, not the number in the request. https://www.financialprofessionals.org/training-resources/resources/articles/Details/4-ways-to-reduce-payments-fraud The FBI says the same in fewer words: "Use secondary channels and/or two-factor authentication to verify requests for changes in account information" (IC3 PSA I-091124-PSA, 11 Sep 2024, which also puts BEC exposed losses at $55.5 billion across 305,033 incidents from Oct 2013 to Dec 2023). https://www.ic3.gov/PSA/2024/PSA240911

Two scheme checks sit beside the callback, and neither replaces it. UK Confirmation of Payee, run by Pay.UK, checks name against sort code and account number when a new payee is set up or existing details are amended, and returns match, close match, no match, or unavailable. It "does not automatically guarantee that a fraudulent payment will be detected." https://www.wearepay.uk/what-we-do/overlay-services/confirmation-of-payee/faqs/ In the EU, the EPC Verification of Payee rulebook entered into force on 5 Oct 2025, and from 9 Oct 2025 euro-area payment providers must offer a free name-versus-IBAN check before the payer authorises a standard or instant credit transfer (EPC press release EPC266-25; ECB Instant Payments Regulation timetable). https://www.europeanpaymentscouncil.eu/sites/default/files/kb/file/2025-10/EPC266-25%20Press%20Release%20VOP%20rulebook%20now%20into%20force.pdf https://www.ecb.europa.eu/paym/retail/instant_payments/html/instant_payments_regulation.en.html Both answer "does this name belong to this account?" They do not answer "is this the account the money arrived from?"

**Where the friction should and should not sit.** A refund to the unchanged master account, already matched on payer name and country, needs maker-checker above the threshold and nothing more. The same callback, cooling-off and dual approval that AFP describes should fire only when the destination is new or differs from the account on file. I found no source that sets a standard cooling-off length, so the demo should show the hold without quoting a number of hours as if it were a rule. Airwallex's own beneficiary name-check (`verify_account`, where enabled) can stand in for CoP or VoP on the way out. Show its result on the approval card, and still block the payment if the account came from the email.
