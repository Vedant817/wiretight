# Round 2: Senior Dev, API correctness, build specs and coding-agent prompts

Written 2026-10-08 (IST). My lens is API correctness and build-readiness for `board/SPEC-v1.md` ("Countersign"). I folded in the Round 2 board constraints logged in `DECISIONS.md`: split packets, lookup-before-retry everywhere, default failure handler, pre-call guards, deterministic vendor matching, polling first, out-of-band (OOB) rules, WebAuthn signing, cuts, 20 scenarios, and a Week 1 money path with no LLM or UI. I also folded in **D7/D8** and Compliance Round 2b:
- SEPA LOCAL demo; SWIFT `swift_charge_option=PAYER`; fees read from responses;
- per-rail business-day FINAL; no wait-and-re-check; RFI and sanctions escalation;
- return journals and an explicit tie-out formula;
- cut-off, value-date and holiday logic;
- policy floor rows 1-30 as tighten-only invariants;
- T-01..T-34 mapped to milestones (§5.9).

**Contents:** §1 verification, §2 unverified, §3 patches, §4 build specs (stack, layout, env, sandbox setup, Makefile, CI, test honesty), §5 prompts (a)-(h), §6 plan.

**Evidence sources:**
- `raw/doc_*.txt`, cited as `file:line`.
- The public Airwallex Docs MCP (`https://mcp.sandbox.airwallex.com/docs`, tool `search_public_docs`), queried live on 2026-10-08 and cited as **[MCP: page]**.
- The hackathon guide (https://airwallexdev.com/guide), cited as **[guide]**.

Nothing here was tested against a live sandbox. I had no account, and creating one is OPEN-3. Everything marked *unverified* goes into the day-1 fixture-recording spike in §4.4.

---

## 1. Verification of SPEC-v1 §5 (endpoints, fields, enums) plus related claims in §4, §7 and §8

The verdicts are **correct**, **wrong**, **renamed** and **unverified**. Paths are relative to `https://api.sandbox.airwallex.com/api/v1`.

| # | Spec item (as written) | Verdict | Evidence | Correction / note |
|---|---|---|---|---|
| A1 | Base `https://api.sandbox.airwallex.com/api/v1` | correct | [guide] "main API base URL is `https://api.sandbox.airwallex.com`… paths start with `/api/v1`"; every docs cURL uses this host, e.g. `doc_benef`/[MCP: Validate a Beneficiary] | none |
| A2 | Files host `files.sandbox.airwallex.com` | correct | [guide]: only for kit-4 evidence uploads | Countersign doesn't use it, so drop it from §5 |
| A3 | `POST /authentication/login`, headers `x-client-id`, `x-api-key` | correct | [MCP: Obtain an access token] "specifying your `x-client-id` and `x-api-key` in the HTTP request header"; [guide] "no body" | Add optional `x-login-as` for scoped keys that span several accounts [MCP: same page] |
| A4 | "30-min bearer token, cached and refreshed" | correct | [MCP] "valid for 30 minutes… Always refer to the `expires_at` field"; "Do not call the authentication endpoint before each request" | Refresh from `expires_at` minus 60 s of skew. On 401 the codes are `credentials_invalid` and `credentials_expired` [MCP: auth errors]. Re-login once on `credentials_expired` only |
| A5 | `GET /global_accounts` | correct | [guide] step 5 | none |
| A6 | `POST /global_accounts/create` | correct | [MCP: Create a global account] body has `request_id` (req), `country_code` (req), `required_features` (req, array of objects), `nick_name` | `country_code` is the account country, not the currency (NL/DE/FR for EUR) [guide] |
| A7 | `POST /simulation/deposit/create` | correct | [MCP: Simulate deposit] body has `amount` (req), `global_account_id` (req), `payer_name`, `payer_country`, `payer_bankname`, `reference`, `statement_ref`, `status` | It takes no `currency`: the deposit lands in the GA's currency [guide]. No payer account identifiers (matches F7) |
| A8 | "Posts immediately despite PENDING" | unverified | [guide] only; not stated in the docs | Planner must re-read `GET /balances/current` after seeding rather than trust the response |
| A9 | `GET /balances/current` | correct | [MCP: List all Current Balances] fields `available_amount`, `pending_amount`, `reserved_amount`, `prepayment_amount`, `total_amount`, `currency`, `account_type` | Floor checks use **`available_amount`**. `doc_bal_hist.txt:343-356` lists this endpoint as SCA-gated for "platform user" access (see U5) |
| A10 | `GET /balances/history` (`from_post_at`, `currency`, `page`) | correct | `doc_bal_hist.txt:9,22-39`: params `currency`, `from_post_at`, `to_post_at`, `page` (cursor), `page_num`, `page_size`, `account_type`, `request_id`. Line 1: "date range should be within 7 days when using `page_num`" | Use the `page` cursor (`page_after`/`page_before`, lines 110-112) and avoid `page_num` for windows over 7 days |
| A11 | `GET /fx/rates/current`, indicative `rate`, no `x-api-version` | correct | [MCP: Retrieve current rate] `rate` field; [guide] "Leave `x-api-version` off the FX calls… `incorrect_version` for a stale value" | Indicative only. **Never** put it in a packet as a bound term |
| A12 | `POST /fx/quotes/create`, `buy/sell_currency`, amount, `validity` (MIN_1…HR_24); read `client_rate`, `quote_id`, `valid_to_at` | correct | `doc_fxquote.txt:1` "1 minute up to 24 hours"; [MCP: Create a Quote] `validity` ∈ `MIN_1, MIN_15, MIN_30, HR_1, HR_4, HR_8, HR_24`; response `quote_id`, `client_rate`, `valid_from_at`, `valid_to_at`, `usage` ∈ `SINGLE_USE, MULTI_USE`, `awx_rate`, `mid_rate` | Store `usage`. Treat every quote as single-use [guide] |
| A13 | `GET /fx/quotes/{quote_id}` | correct | [MCP: Retrieve a Quote] "`GET /api/v1/fx/quotes/{quote_id}`" | none |
| A14 | `POST /fx/conversions/create` with `request_id`, `buy_currency`, `sell_currency`, `buy_amount`, `quote_id` | correct | [MCP: Create a Conversion] "define only one of either `buy_amount` or `sell_amount`"; `request_id` "maximum of 64 characters… same `request_id` will be rejected"; quote must match `buy_currency`/`sell_currency`/`conversion_date`; minimum USD 1 | The response id field is **`conversion_id`**, not `id` |
| A15 | Conversion "settles immediately" | correct | [guide] "Conversions settle immediately with `status: "SETTLED"`"; [MCP: List conversions] status ∈ `SCHEDULED, OVERDUE, CANCELLED, SETTLED` | The state machine still has to handle the other three statuses (future `conversion_date` or funding gaps) |
| A16 | `POST /beneficiaries/schema` (guide) | **renamed** | Not in the docs: an MCP search for "beneficiaries/schema" returned only `beneficiary_api_schemas/generate` and `beneficiary_form_schemas/generate`. The guide uses the short name | Use **`POST /beneficiary_api_schemas/generate`**. Probe the guide alias once on day 1 and record the result |
| A17 | `POST /beneficiary_api_schemas/generate` (docs) | correct | [MCP: Retrieve the API Schema] params `entity_type`, `bank_country_code`, `account_currency`, `transfer_method`, `local_clearing_system`; error `SCHEMA_DEFINITION_NOT_FOUND` | Cache the schema per corridor in fixtures |
| A18 | `POST /beneficiaries/validate` | correct | [MCP: Validate a Beneficiary] body `beneficiary` (req), `transfer_methods` (req, `SWIFT`/`LOCAL`), `nickname`, `payer_entity_type`, `transfer_reason`; 200 `"OK"` or 400 with all failed fields | Send `transfer_methods`, not `payment_methods` (error 001) [guide] |
| A19 | `POST /beneficiaries/create` | correct | [MCP: Create beneficiary] body `beneficiary`, `transfer_methods` (req), `nickname`, `payer_entity_type`, `transfer_reason`, `sca_exemptible` | **There is no `request_id` field.** Lookup-before-retry (constraint 2) therefore keys on `nickname = "cs-" + payee_version_id`. See A20 |
| A20 | `GET /beneficiaries` | correct | [MCP: List beneficiaries] query `name`, `nick_name`, `bank_account_number`, `company_name`, `entity_type`, `from_date`, `to_date`, `page_num`, `page_size`, `type` | No status or version filter. Lookup = `nick_name` plus a client-side exact match. Whether `nick_name` filtering is exact or substring is unverified (U3) |
| A21 | `GET /beneficiaries/{id}` | correct | [MCP] / `doc_benef.txt` endpoint list | none |
| A22 | "A changed bank detail creates a **new** beneficiary version… the old one is retired" | wrong (as an API claim) | Airwallex has no beneficiary versions. Its endpoints are `…/{id}/update` and `…/{id}/delete` (`doc_benef.txt:1`, endpoint list) | Keep `payee_version` as an **internal** concept. A new version means a new Airwallex beneficiary. Retirement is internal status `RETIRED` and **must not** call `/update`, so history stays auditable. Optional `/{id}/delete` happens after the incident closes |
| A23 | `POST /beneficiaries/verify_account` | correct (endpoint); sandbox behaviour unverified | `doc_verify.txt:5-18,79-124`: `code` ∈ {`VERIFIED`, `CANNOT_VERIFY`, …}; `account_name_match_result` ∈ {`FULL_MATCH`, `PARTIAL_MATCH`, `NOT_MATCHED`, `FULL_MATCH_INCORRECT_TYPE`, `PARTIAL_MATCH_INCORRECT_TYPE`} | Feature flag, default off (F7) |
| A24 | `POST /transfers/create` with `request_id`, `transfer_method`, `transfer_currency`, `transfer_amount`, `reference` | **wrong (incomplete)** | `doc_create_transfer.txt:7-14`: **`reason` (required)**, `reference` (required), `request_id` (required), `transfer_currency` (required); line 436 lists the `reason` enum; `transfer_amount` is a **string** (line 244); `beneficiary_id`, `source_currency`, `source_amount`, `quote_id`, `swift_charge_option` (`SHARED`/`PAYER`), `fee_paid_by` (`PAYER`/`BENEFICIARY`) | Add **`reason`** from policy per vendor category (e.g. `goods_purchased`, `freight`, `professional_business_services`, `technical_services`) plus `beneficiary_id`. Send amounts as decimal **strings**. Set `source_currency = transfer_currency` when funding from a pre-converted balance |
| A25 | `request_id` "10–50 chars" | correct | `doc_create_transfer.txt:11-13` "used in the past 7 days are treated as duplicated payout… Can be non-UUID"; `:792-793` "Up to 50 characters"; [guide] under 10 or over 50 gives code `018` | Conversions allow up to 64 (A14). Use one 36-char UUID format for both |
| A26 | `request_id = uuid5(run_id, obligation_id, attempt_no)` | correct (format); derivation changed | uuid5 output is 36 chars and satisfies A25 | Per Compliance T-16, **drop `run_id`** so a re-plan in a new run reuses the same id and hits Airwallex dedupe. Derive it as `uuid5(AWX_REQUEST_ID_NAMESPACE, "transfer:{obligation_id}:{tranche_no}:{attempt_no}")`. The namespace salt is per install |
| A27 | Idempotency semantics (implied: retry is safe) | wrong (as implied) | [MCP] error lists show `duplicate_request_id` as a **400**; `doc_create_transfer.txt:12` says "cannot be processed… try to get a payout with this `request_id` to find out" | Airwallex **rejects** duplicates and does **not** replay the original response. On a timeout: look up by `request_id`, then retry with the **same** id only if the lookup comes back empty. Treat `duplicate_request_id` as "it exists, look it up" |
| A28 | `transfer_method` LOCAL/SWIFT | correct | `doc_create_transfer.txt:250` "SWIFT, LOCAL"; [guide] "accepts only `LOCAL` and `SWIFT`" | none |
| A29 | `GET /transfers/{id}` | correct | `doc_transfer.txt:1`; SCA list path `/transfers/{transfer_id}` (`doc_bal_hist.txt`) | none |
| A30 | `GET /transfers?request_id=…&status=…` | correct | `doc_list_transfers.txt:20-38`: `request_id`, `status`, `beneficiary_id`, `from_created_at`, `to_created_at`, `transfer_currency`, `short_reference_id`, `page`, `page_size`; line 1: with no `from_created_at`, it covers "30 days in arrears" | Always pass `from_created_at` for the duplicate-lock lookback. Cursor paging uses `page` |
| A31 | `GET /transfers?beneficiary_id=…` (§4 already-paid check) | correct | `doc_list_transfers.txt:22` | none |
| A32 | Webhooks `payout.transfer.processing/sent/paid/failed/cancelled` | correct | `doc_webhooks.txt` table; also `scheduled`, `overdue`, `cancellation_requested`, `in_approval`, `funding.*` | Handle `scheduled` and `overdue` too |
| A33 | `deposit.settled` triggers re-plan | correct (name); unverified for simulations | `doc_deposit_wh.txt:1`; whether simulated deposits fire it is undocumented (F7) | Constraint 6: re-plan is triggered by **polling** balances. Webhooks only nudge a poll |
| A34 | Signature "HMAC-SHA256 over `x-timestamp` + raw body" | correct | [MCP: Check webhook signatures] "concatenating the `x-timestamp` (as a string) and the actual JSON payload"; "HMAC hex digest… SHA-256… secret as the HMAC key"; `x-timestamp` = "Unix timestamp in milliseconds" | Compare a **lowercase hex** digest with `hmac.compare_digest`. The key is the per-URL secret from the web app. Test events are signed with the key in the `client-secret-key` header |
| A35 | Replay window (spec silent) | unverified | [MCP]: "decide if the difference is within your tolerance" (no value given); retries use "exponential back-off over about three days" | We pick `WEBHOOK_TOLERANCE_SECONDS=300`. Whether retries are re-signed with a fresh timestamp is undocumented, so dedupe on event `id` is the real replay control (U4) |
| A36 | Dedupe on event id; sort by `created_at` | correct | [MCP: Webhooks overview] "same event more than once… tracking the event `id`"; "does not guarantee… order… use the `created_at` field"; payload fields `id`, `name`, `account_id`, `data.object`, `created_at`, `version` | `data.object` follows the same schema as the Retrieve API response |
| A37 | Webhook config in the web app | correct | [guide]/airwallexdev "Settings > Developer > Webhooks in the sandbox web app, not the API" | Optional (constraint 6) |
| A38 | `POST /simulation/transfers/{id}/transition`, `next_status` SENT → PAID / FAILED + `failure_type` | correct | `doc_failure_types.txt:9,27-63`: `next_status` ∈ `OVERDUE, PROCESSING, SENT, PAID, FAILED, CANCELLED`; "only… if the `next_status`… is the next valid status"; "`PAID` can only be simulated in API version 2024-04-30 or later" (line ~88) | Step one status at a time. Whether PAID→FAILED can be simulated is unverified (U1) |
| A39 | `GET /financial_transactions` fields `source_type`, `transaction_type`, `client_rate`, `fee`, `net`, `batch_id` | correct | `doc_fin_tx.txt:36-85`; filters (MCP) are `from_created_at`, `to_created_at`, `source_id`, `status`, `currency`, `batch_id`, `page_num`, `page_size` | There is **no** `source_type` filter, so filter client-side. Status ∈ `PENDING, SETTLED, CANCELLED` (`doc_fin_tx.txt:72-73`) |
| A40 | Recon mapping `CONVERSION_SELL/BUY`, `PAYOUT`, `FEE`, `PAYOUT_FAILURE`/`PAYOUT_REVERSAL`, `DEPOSIT` | correct | `doc_fin_tx.txt:74-85` lists all of them | Also map `CONVERSION_REVERSAL` and `ADJUSTMENT`. Unknown types become an exception, never a silent skip |
| A41 | `POST /finance/financial_reports/create` (`TRANSACTION_RECON_REPORT`) | correct | `doc_finrep.txt:9,20-37`: required `file_format` (`CSV`…), `from_date`, `to_date`, `type`; fetch via `GET /finance/financial_reports/{id}` and `/{id}/content` | Stretch only. Default `report_version` is 1.1.0 (`doc_bal_hist.txt:189-199`) |
| A42 | `x-api-version` ("no `x-api-version`" on FX) | unverified | [MCP: Versioning] "Your version is stored in your account and automatically applied… You may override… `x-api-version`… only… in exceptional cases"; "The latest version is `2026-08-21`". `doc_tstatus.txt:105` describes statuses "for **API version 2025-06-30 or later**" | Read the account version on day 1 and record it in `fixtures/manifest.json`. Default: **send no header**. Optional env `AWX_API_VERSION` applies to non-`/fx/` paths only. Subscribe webhooks with the same version. Fail fast if the account version is below `2025-06-30` |
| A43 | §8 transfer state machine `CREATED → (PROCESSING) → SENT → PAID → FINAL`, `SENT\|PAID → FAILED/CANCELLED` | **wrong** | `doc_tstatus.txt:110` diagram: "Created→(IN_APPROVAL,SCHEDULED)… SCHEDULED→(PROCESSING,OVERDUE,CANCELLED); OVERDUE→(PROCESSING,CANCELLED); PROCESSING→(SENT,FAILED); SENT→(PAID,FAILED); PAID→(FAILED,end); FAILED→CANCELLED"; line 127 "Failed transfers will be automatically cancelled in seconds" | It is missing `SCHEDULED` and `OVERDUE`, and `FAILED` is transient (it auto-becomes `CANCELLED`). Corrected machine in §3 P5 |
| A44 | Spec relies on terminal status FAILED (S7/S8 "FAILED/CANCELLED terminal") | wrong (partly) | As A43; [guide] "A failed transfer ends in CANCELLED, never in a status called FAILED" | Terminal-failed = `CANCELLED`, with `failure_type` captured. Record `failure_type`/`failure_reason` at the **first** observation of FAILED or CANCELLED (constraint 3) |
| A45 | Approval expiry `min(quote.valid_to_at, approved_at+4h)`, quote validity ≥ approval window | correct | A12 validity enum | Use `HR_4` for packets that bind a quote. `MIN_1` exists for the expiry fixture |
| A46 | Native approvals via `payout.transfer.in_approval` | correct (event); **CUT** | `doc_tstatus.txt:118` | Constraint 9 cuts this. Remove it from the spec |
| A47 | Insufficient-funds codes `balance_insufficient` / `insufficient_funds` | correct | [guide] "`transfers/create` returns `balance_insufficient`… `fx/conversions/create` returns `insufficient_funds`" (`charges/create` → `insufficient_fund`, not used) | The client maps all three to `InsufficientFunds` |
| A48 | Rate limits "≤10 rps per endpoint, ≤10 concurrent" | correct | [guide] "20 requests per second globally, 10 per endpoint, and 10 concurrent" | Add the 20 rps global bucket |
| A49 | SWIFT fee EUR 12.85 flat | correct (sandbox example) | [guide] "EUR SWIFT transfers of 100, 1,000, 2,000 and 4,000 each cost a flat EUR 12.85" | Planner uses policy `fees`. Recon uses the **actual** `fee_amount`/`amount_payer_pays` from the transfer object (`doc_list_transfers.txt:84-160`) |
| A50 | §4.5 "Any non-2xx is treated as ambiguous" | wrong (too broad) | 400 `validation_error` and `duplicate_request_id` are definitive [MCP error lists]; 401/429 have defined meanings | **Ambiguous** = timeout, connection reset, or 5xx on a **mutating** call. 400 validation is a definitive reject. `duplicate_request_id` means look it up. 429 means back off and retry the same request |
| A51 | §4.5 `reference` = invoice number | unverified | `doc_create_transfer.txt:434` "Whether this reference appears on the beneficiary's bank statement depends on the local clearing system" | Per-corridor length and charset limits are not in the raw docs. Truncate per the schema response and test `INVALID_SPECIAL_CHARACTER` |
| A53 | (D8) SWIFT charge bearer | correct | `doc_create_transfer.txt:242-243` "`swift_charge_option`… either `SHARED` (default) or `PAYER`"; `:442` `fee_paid_by` = `PAYER` (default) / `BENEFICIARY` | A SWIFT PAYMENT packet binds `swift_charge_option: "PAYER"` and `fee_paid_by: "PAYER"`. LOCAL packets bind `null`. There is **no** BEN option |
| A54 | (D8) RFI tracking | correct (endpoints); sandbox unverified | [MCP: Transaction RFI] `GET /api/v1/rfis` (`statuses`, `types=TRANSACTION`), `GET /api/v1/rfis/{id}`, `POST /api/v1/rfis/{id}/respond`, `POST /api/v1/simulation/rfis/create`; statuses `ACTION_REQUIRED`, `ANSWERED`, `CLOSED`; webhooks `rfi.action_required`, `rfi.answered`, `rfi.closed`. "can be used directly for RFIs related to your own account" | Poll `GET /rfis` (polling first). Responding is **human-only** |
| A55 | (D8) `TM_SUSPENDED` reason codes / watchlist | unverified | Banking Domain round2 M4 cites `failure.details.reason_codes` (e.g. `EXPIRED_TRANSACTION_RFI`, `WATCHLIST_RESTRICTION_PAYER/_BENEFICIARY`). That field path is not in `raw/` and I did not see it in my MCP results | Parse defensively. Any `WATCHLIST_*` code or any compliance-type failure → payee `COMPLIANCE_HOLD` + kill-switch trip + escalation. The LLM must not draft a reason to the supplier |
| A52 | Transfer object fields used for recon (spec implies `fee`) | correct | `doc_list_transfers.txt:84-160`: `fee_amount`, `fee_currency`, `amount_payer_pays`, `amount_beneficiary_receives`, `short_reference_id`, `funding.status`, `status` | Persist the whole raw object per poll (`transfer_observation` table) |

### 1.1 `failure_type` list in SPEC §4 step 7

Source: `doc_failure_types.txt:29-63`, the `failure_type` enum of the transition endpoint (32 values).

| # | Spec value | Verdict | Note |
|---|---|---|---|
| F1 | `BENEFICIARY_NAME_MISMATCH` | correct | reason table `90301` (line 113) |
| F2 | `INVALID_ACCOUNT_NAME_OR_NUMBER` | correct | `90101` |
| F3 | `INVALID_BANK_OR_BRANCH_CODE` | correct | `90201` |
| F4 | `INVALID_SWIFT_BIC_CODE` | correct | `90202` |
| F5 | `INVALID_BENEFICIARY_DETAILS` | correct | `90401` |
| F6 | `ACCOUNT_CLOSED` | correct | `90701` |
| F7 | `ACCOUNT_INACTIVE_OR_DORMANT` | correct | `90702` |
| F8 | `INVALID_PAYMENT_PURPOSE` | correct | `91101` |
| F9 | `INSUFFICIENT_FUNDS` | correct | in the enum, not in the reason table |
| F10 | `TRANSACTION_AMOUNT_NOT_COVERING_FEE` | correct | enum only |
| F11 | `ACCOUNT_UNDER_RESTRICTION` | correct | `90703` |
| F12 | `TM_SUSPENDED` | correct | `90502` |
| F13 | `CHANNEL_POLICY` | correct | `90501` |
| F14 | `CHANNEL_TIMEOUT` | correct (name); **playbook wrong** | Shows up only on FAILED (then auto-CANCELLED), so the transfer is already terminal. "Wait and re-check" is wrong: treat it as terminal-failed and allow a T2 replacement |
| F15 | `SYSTEM_ERROR` | correct (name); **playbook wrong** | Same as F14 |
| F16 | `RECALL_REQUESTED` | correct | `91001` |
| F17 | `CLIENT_REQUESTED` | correct | `91002` |
| F18 | `DUPLICATION_RETURN` | correct | enum only |

**Missing from the spec playbooks (14):**
- `ACCOUNT_CURRENCY_MISMATCH`, `INVALID_BANK_INFORMATION` and `INVALID_CORRESPONDENT_BANK_INFORMATION` go to the bank-detail playbook (T2).
- `INVALID_SPECIAL_CHARACTER` goes to the reference/name-sanitize playbook (T1).
- `BENEFICIARY_BANK_RETURNED` gets a bank-return playbook (constraint 3: modelled as FAILED + this type, T2).
- `BENEFICIARY_REQUESTED` goes to investigate (escalate).
- `EXCEEDED_TRANSACTION_AMOUNT_OR_LIMIT` goes to re-plan (split is not allowed without a new countersign).
- `UNABLE_TO_APPLY`, `OTHER`, `CARD_ISSUER_ERROR`, `INBOUND_2B_CARD_NOT_SUPPORTED`, `INBOUND_BENFICIARY_VALIDATION_ERROR` (sic, misspelled in the enum, so match it byte-for-byte), `INBOUND_COMPANY_REGISTRATION_NUMBER_ERROR` and `INBOUND_ORDER_ERROR` go to the **DEFAULT handler** (constraint 3).

The DEFAULT handler also catches any string not in this list, `null` and `"simulation"` (a bare cancel returns only `failure_reason: "simulation"` [guide]). It escalates, never auto-retries, and makes any replacement require T2.

### 1.2 Verdict counts
**73 items checked:** A1-A55 (§5 endpoints, fields and enums, plus the D8 additions A53-A55) and F1-F18 (§4 failure types).

| Verdict | A (endpoints/fields) | F (failure types) | Total |
|---|---|---|---|
| correct | 43 | 18 | **61** |
| wrong | 6 (A22, A24, A27, A43, A44, A50) | 0 | **6** |
| renamed | 1 (A16) | 0 | **1** |
| unverified | 5 (A8, A35, A42, A51, A55) | 0 | **5** |

Notes on the counts:
- A54 (RFI endpoints) counts as correct because the endpoints are documented, but whether it works in sandbox is U11.
- The failure-type check also found **2 wrong playbooks on correctly named types**: F14 and F15 (CHANNEL_TIMEOUT/SYSTEM_ERROR "wait and re-check"; there is no re-check because failures auto-cancel).
- **14 enum values are missing** from the spec's playbook list, and the spec has **no DEFAULT handler** (§1.1).

---

## 2. Unverified items for the day-1 spike (U-list)
- **U1.** Can a simulated transfer go PAID → FAILED? (The state diagram allows it; the simulator rule is "next valid status".) This decides whether S8 is a live demo beat or a fixture-only test.
- **U2.** When polling skips the transient FAILED, does the CANCELLED object still carry `failure_type`/`failure_reason`? If not, the poll interval near failure must be ≤ 2 s. Otherwise `failure_type = UNKNOWN` goes to the DEFAULT handler.
- **U3.** Is `GET /beneficiaries?nick_name=` an exact match? This is needed for beneficiary lookup-before-retry.
- **U4.** Are webhook retries re-signed with a fresh `x-timestamp`? Do simulated deposits and transfers fire webhooks at all?
- **U5.** Do SCA rules (`doc_bal_hist.txt:343`) apply to direct API-key access in sandbox? (Expected: no, since they target "platform user" access.)
- **U6.** Which API version is the account on, and where is it shown in the web app?
- **U7.** Is the guide alias `POST /beneficiaries/schema` live?
- **U8.** What error does converting with an expired quote return? Record a `MIN_1` quote and convert after 70 s.
- **U9.** Does a `deposit` created with `status: REJECTED` show in `financial_transactions`?
- **U10.** Does `verify_account` respond in sandbox?
- **U11.** Can a non-platform sandbox account simulate RFIs (`POST /simulation/rfis/create`)? Does `GET /rfis` link `sources` to a transfer id?
- **U12.** Is the `failure.details.reason_codes` path on `TM_SUSPENDED` real (Banking Domain M4; not in `raw/`)?
- **U13.** How do third-party fees and FX cancellation delta fees appear in `financial_transactions` (`transaction_type`)?
- **U14.** Is the transfer fee inside the PAYOUT row (`fee` field) or a separate FEE row? This decides the recon TERM_MAP.
- **U15.** On a return, is the refund "transfer amount less fee" *in addition to* a separately debited fee (fee lost twice), or is the fee netted only once? This decides the return identity in §5(g).
- **Assumptions (not Airwallex facts, labelled in the UI):**
  - per-rail cut-off times;
  - the UK FPS return window (3 business days);
  - the US ACH 2-day window (search snippet only);
  - the SWIFT 10-business-day PRESUMED_SETTLED label.

---

## 3. Spec patches (old → new)
- **P1** §5 Payees: `POST /beneficiaries/schema` (guide) / `…/generate` (docs) → **`POST /beneficiary_api_schemas/generate`** (canonical). The guide alias is probed once in the spike.
- **P2** §4.5 / §5 transfers: `request_id, transfer_method, transfer_currency, transfer_amount, reference` → **`request_id, beneficiary_id, reason, reference, transfer_currency, transfer_amount (string), source_currency, transfer_method[, swift_charge_option]`**. `reason` comes from `policy.yaml: vendor_category_reason`.
- **P3** §4.5: "Any non-2xx is treated as ambiguous" → "Ambiguous = timeout / connection error / 5xx on a mutating call. `duplicate_request_id` → exists, look up. 400 `validation_error` → REJECTED (definitive). 429 → back off, same request."
- **P4** §4.5 + constraint 2: lookup-before-retry covers **all three** creates:
  - transfers: `GET /transfers?request_id=`
  - conversions: `GET /fx/conversions?request_id=`
  - beneficiaries: `GET /beneficiaries?nick_name=cs-<payee_version_id>` plus an exact client-side match

  A retry reuses the **same** `request_id`/nickname and never mints a new one for the same attempt.
- **P5** §8 transfer state machine → Airwallex statuses `SCHEDULED → PROCESSING → SENT → PAID → (FAILED) → CANCELLED`, plus `OVERDUE`. Internal statuses: `DRAFT, APPROVED, SUBMITTING, AMBIGUOUS, REJECTED, SCHEDULED, OVERDUE, PROCESSING, SENT, PAID_PROVISIONAL, FINAL, FAILED, CANCELLED_FAILED, CANCELLED_BY_US`.
  - FAILED is transient. `failure_type`/`failure_reason` are persisted on first sight, even if the first observation is CANCELLED.
  - Regressions are ignored and audited.
  - PAID→FAILED is allowed.
- **P6** §4.7: there is **no "wait and re-check" anywhere** (D8: failures auto-cancel in seconds). CHANNEL_TIMEOUT/SYSTEM_ERROR → terminal-failed, T2 replacement allowed. Add the 14 missing types and the DEFAULT handler (§1.1). Bank return = FAILED + `BENEFICIARY_BANK_RETURNED`.
- **P7** §6.2: one packet → **two packet types**, `CONVERSION` and `PAYMENT`, each with its own hash, tier and countersign. A PAYMENT packet that depends on a conversion embeds `conversion_packet_sha256`, and executing it requires that conversion SETTLED.
- **P8** §4.5 Execute: add a **pre-call guard** before every mutating call: live `GET /balances/current` ≥ floor after this call, and the duplicate lock is re-checked against live `GET /transfers` (or `GET /fx/conversions`). Otherwise ABORT, flag the item, and leave the approval unconsumed but void.
- **P9** §4.2: "Duplicate detection… line-item similarity" plus the implicit LLM vendor resolution → **vendor matching is deterministic code only**: exact normalized name, alias table, sender domain, IBAN/account fingerprint. The LLM never selects a vendor.
- **P10** §4.6/§5 Track: webhooks primary → **polling primary** (`GET /transfers/{id}` on a schedule). Webhooks are optional (`WEBHOOKS_ENABLED=false`), signature-verified, deduped, and only *trigger a poll*.
- **P11** §4.2 + §6.1 T2: "recorded out-of-band verification" → code-enforced rules:
  - (a) verifier ∉ {requester, intake_user};
  - (b) the callback number comes from a `vendor_contact` row whose `created_at` < `bank_change_request.created_at`;
  - (c) a cooling-off hold (`policy.bank_change.cooling_off_hours`);
  - (d) a first-payment cap (`policy.bank_change.first_payment_cap_base`).
- **P12** §6.2/§6.3 → approvers sign `packet_sha256` with a **WebAuthn passkey** (`webauthn==3.0.1`) under demo identities. The fallback is a per-approver HMAC key, shown as "FALLBACK (HMAC, not phishing-resistant)" in the UI and README.
- **P13** §5/§9/§12 cuts: remove Metal anchor, Slack, Airwallex native approvals, CSV bill import, Postgres/Alembic and `payout.transfer.in_approval`. Storage = SQLite (stdlib driver through SQLAlchemy Core), schema in `app/core/schema.sql` with `PRAGMA user_version` migrations.
- **P14** §13: "N=50 runs" → **exactly 20 labelled scenarios** (`eval/scenarios/S01…S20.yaml`).
- **P15** §12: Week 1 = money path only (client, ledger/state machines/audit, structured ingest + duplicates + fingerprint, planner, packets + signatures (CLI), executor + polling). No LLM, no UI. The LLM extraction adapter and planner notes are Week 2 and optional.
- **P16** §5 auth: add `expires_at`-based refresh, the `credentials_expired` handling and optional `x-login-as`.
- **P17** §5: add `GET /fx/conversions` and `GET /fx/conversions/{conversion_id}`. Conversion id field = `conversion_id`.
- **P18** §5 Track: also handle `payout.transfer.scheduled`/`overdue`. Fetch financial transactions with client-side `source_type` filtering (there is no server filter).
- **P19** `request_id` derivation → `uuid5(AWX_REQUEST_ID_NAMESPACE, f"{kind}:{entity_id}:{tranche_no}:{attempt_no}")`, with **no `run_id`** (Compliance T-16). `kind` ∈ {transfer, conversion}. Beneficiary nickname = `cs-{payee_version_id}`.
- **P20** §4.3: rates from `GET /fx/rates/current` feed **planning only**. Any amount a human signs comes from a quote (`client_rate`), never from an indicative `rate`.
- **P21 (D8)** §10 demo: bill #2 EUR 7,500 → **LOCAL (SEPA)**. The mid-run failure is `ACCOUNT_CLOSED` (or `BENEFICIARY_BANK_RETURNED`, whichever the simulator accepts; day-1 test) after SENT, replacing `BENEFICIARY_NAME_MISMATCH`, which moves to unit/eval tests. A SWIFT payment binds `swift_charge_option=PAYER`, `fee_paid_by=PAYER` (A53). **Fees come from the transfer response** (`fee_amount`, `fee_currency`, `amount_payer_pays`) and are never estimated in packets, journals or recon. The planner may only hold a per-rail `fee_reservation` against the floor, labelled as a reservation.
- **P22 (D8)** §4.6 / `settle_window_hours: 48` → per-rail **business-day FINAL windows**, measured from the first PAID observation on the rail's holiday calendar:
  - SEPA ≥ 3 TARGET2 business days, with a 48 h floor;
  - UK FPS ≥ 3 UK business days (an assumption, labelled);
  - US ACH ≥ 2 US banking days (sourced only as a search snippet, labelled);
  - **SWIFT never becomes FINAL by timer**: it needs a recorded supplier confirmation, otherwise it shows "PRESUMED_SETTLED" (not FINAL) after 10 business days.

  The demo override (2 min, sandbox-only, labelled) is permitted by Compliance row 22.
- **P23 (D8)** §4.7: add **RFI tracking** (A54). Poll `GET /rfis?types=TRANSACTION&statuses=ACTION_REQUIRED`. An open RFI linked to a transfer → item `RFI_OPEN`, a queue card, and holds on any replacement or new payment to that payee. Add **sanctions/TM escalation** (A55).
- **P24 (D8)** §4.8 recon: return journals and an explicit tie-out formula covering refund in transfer currency, retained transfer fee, third-party fee and FX cancellation delta fee (see §5(g)).
- **P25 (D8)** §4.3 planner: add **cut-off, value-date and holiday logic**: `latest_send_date = business_days_before(due_date, max_flight_days(rail), calendar(currency))`. A send date falling after the cut-off rolls to the next business day. Items flag `AT_RISK_LATE`.
- **P26 (D7)** Compliance Round 2b rows 1-30 = **hard-coded policy floor** (`app/core/policy_floor.py`). `policy.yaml` may only tighten it. Loosening, unknown keys, a missing floor or missing policy signatures → load error → halt. Demo overrides only apply when `AWX_ENV=sandbox` and the host pin passes, and they are labelled on screen.
- **P27 (D6/D7)** Add a kill switch (`HALT` file + DB flag) with Compliance trips (rows 24-29), cleared by 2 approver signatures. Add append-only audit triggers, signed external checkpoints, log-before-act, a sandbox host pin, no redirects and no proxies (`trust_env=False`).

---

## 4. Exact build specs

The product name is pending (D4; CEO top pick "Wiretight"). The repo root is written `<repo>/`. The Python package is **`app`** regardless of name, so a rename only touches README, UI strings and `pyproject.name`.

### 4.1 Pinned stack (exact versions; checked with `pip index` / npm / GitHub releases on 2026-10-08)
| Layer | Package / tool | Version | Why |
|---|---|---|---|
| Runtime | CPython | **3.12.15** | Spec says 3.12; latest 3.12 patch listed by `uv python list` |
| Env/locking | uv | **0.12.23** | `uv sync --frozen`, lockfile committed |
| Web | fastapi | **0.143.0** | API + server-rendered UI |
| ASGI | uvicorn | **0.54.0** | dev server |
| Forms | python-multipart | **0.0.32** | FastAPI form posts |
| Templates | jinja2 | **3.1.6** | autoescape on (T-03) |
| HTTP | httpx | **0.28.1** | Airwallex client, `trust_env=False`, `follow_redirects=False` |
| DB | sqlalchemy | **2.1.4** | Core only, over stdlib `sqlite3` (no Alembic, no Postgres) |
| Models | pydantic | **2.13.5** | typed DTOs, `Decimal` money |
| Settings | pydantic-settings | **2.15.0** | `.env` loading |
| Policy | pyyaml | **6.0.3** | `policy.yaml` (safe_load only) |
| Canonical JSON | rfc8785 | **0.1.4** | packet canonicalisation (JCS). Amounts are **strings**, never floats |
| Passkeys | webauthn | **3.0.1** | approver assertions (needs Python ≥3.10; deps cryptography ≥49, cbor2, pyOpenSSL) |
| Crypto | cryptography | **50.0.2** | ES256 soft-authenticator in tests, Ed25519 audit checkpoints |
| PDF | pdfplumber | **0.11.10** | Week 2: text + per-char size/colour for `HIDDEN_TEXT` (T-01). No OCR |
| PDF (fallback) | pypdf | **6.19.0** | page text fallback |
| Calendars (dev) | holidays | **0.106** | generates committed calendar fixtures; not imported at runtime |
| LLM (Week 2, optional) | anthropic | **1.12.1** | behind `LLMProvider`; `LLM_ENABLED=false` by default |
| Tests | pytest | **9.1.1** | |
| Tests | hypothesis | **6.168.5** | property tests (no double-pay, floor, determinism) |
| Tests | pytest-cov | **7.1.0** | coverage report (no % gate presented as quality) |
| Tests | pytest-timeout | **2.4.0** | hung-poll protection |
| Tests | time-machine | **3.5.1** | clock control for cooling-off, expiry, business days |
| Lint | ruff | **0.16.10** | lint + format |
| Types | mypy | **2.4.0** | `--strict` on `app/core`, `app/integrations` |
| Types | types-PyYAML | **6.0.12.20260906** | |
| UI (CDN, pinned + SRI) | htmx.org | **2.0.11** | no JS build |
| UI (CDN) | @tailwindcss/browser | **4.3.3** | |
| UI (CDN) | @simplewebauthn/browser | **14.0.0** | browser passkey ceremony only. The server verifies with `webauthn` |
| Tunnel (optional) | cloudflared | **2026.10.0** | only if `WEBHOOKS_ENABLED=true` |
| CI | actions/checkout | **v7.0.1** | |
| CI | astral-sh/setup-uv | **v10.2.0** | check input names against the action README at build time (major versions moved) |
| CI | actions/upload-artifact | **v7.0.2** | eval CSVs |

**Not used (cut, constraint 9):** Postgres, Alembic, SQLModel, Slack SDK, Metal, CSV bill import, Airwallex native approvals. `respx` and `vcrpy` are **not** used either. The record/replay transport is ~150 lines in-repo, so its behaviour is visible and tested.

### 4.2 Repo layout
```
<repo>/
├─ README.md                      # what/why, 5-min quickstart, "demo timing" + "HMAC fallback" disclosures, metrics table generated by make eval
├─ LICENSE                        # Apache-2.0
├─ pyproject.toml                 # pinned deps (exact ==), ruff/mypy/pytest config, python = "==3.12.15"
├─ uv.lock                        # committed lockfile
├─ Makefile                       # §4.5
├─ .env.example                   # §4.3, no secrets
├─ .gitignore                     # .env, *.sqlite, var/, tests/fixtures/**/raw_unredacted/
├─ policy.example.yaml            # T0 OFF; floor-compliant values; comments cite Compliance row numbers
├─ policy.demo.yaml               # T0 ON + demo timing overrides (sandbox only), must carry 2 policy signatures
├─ policy.sig.json                # approver signatures over sha256(policy file bytes) (T-19)
├─ .github/workflows/ci.yml       # §4.6
├─ app/
│  ├─ __init__.py
│  ├─ config.py                   # pydantic-settings; refuses start if AWX_ENV!=sandbox or base URL not allowlisted (T-09)
│  ├─ money.py                    # Decimal helpers, currency exponents, quantize, string serialisation
│  ├─ core/
│  │  ├─ schema.sql               # all tables + append-only triggers on audit_log/approval_signature/webhook_event
│  │  ├─ db.py                    # SQLAlchemy Core engine, PRAGMA foreign_keys/journal_mode=WAL, user_version migrations
│  │  ├─ policy_floor.py          # HARD-CODED Compliance rows 1-30 + tighten-only comparators
│  │  ├─ policy.py                # load + validate policy.yaml against floor, unknown-key rejection, signature check
│  │  ├─ killswitch.py            # HALT file + DB flag, trip reasons, two-approver clear
│  │  ├─ audit.py                 # hash chain, log-before-act INTENT/RESULT, signed checkpoints (outside DB), verify
│  │  ├─ ledger.py                # double-entry postings per currency; balanced-entry invariant
│  │  ├─ statemachine.py          # transfer / conversion / obligation / payee_version / rfi machines (regressions ignored + audited)
│  │  ├─ calendars.py             # business-day math from fixtures; cut-offs; flight days per rail
│  │  ├─ calendars/               # EUR_TARGET2.yaml, GBP_ENGLAND.yaml, USD_FED.yaml (2026-2027, generated + committed)
│  │  ├─ parsers.py               # IBAN mod-97, ABA checksum, UK sort code, BIC, currency, invoice-no normalisation
│  │  ├─ vendors.py               # deterministic vendor matching (no LLM), lookalike-domain detection
│  │  ├─ dupes.py                 # exact/fuzzy duplicate rules + live already-paid check interface
│  │  ├─ fingerprint.py           # bank-detail fingerprint + diff
│  │  ├─ oob.py                   # bank-change request, callback verification rules (P11), cooling-off, tranches
│  │  ├─ planner.py               # pure planner: netting, rails, cut-offs, floor, deferrals, tiers, caps, diff
│  │  ├─ tiers.py                 # T0/T1/T2/HARD_BLOCK assignment against policy + floor
│  │  ├─ packets.py               # CONVERSION + PAYMENT packet builders, RFC 8785 canonical JSON, sha256
│  │  ├─ signing.py               # WebAuthn verification + HMAC fallback, single-use challenges, roster
│  │  ├─ approvals.py             # SoD, distinct approvers, expiry, consumption, void-on-change
│  │  ├─ incidents.py             # failure_type playbooks + DEFAULT handler, replacement under duplicate lock
│  │  ├─ rfi.py                   # RFI tracking state + holds
│  │  ├─ recon.py                 # financial_transactions matching, tie-out formula, residual exceptions
│  │  └─ journal.py               # journal lines incl. return entries, realised FX, generic CSV export
│  ├─ integrations/
│  │  ├─ airwallex/
│  │  │  ├─ client.py             # AirwallexClient: auth cache, rate limits, error classification, typed methods
│  │  │  ├─ errors.py             # ErrorClass enum + code tables (insufficient-funds triple, duplicate_request_id, ...)
│  │  │  ├─ models.py             # pydantic response models (extra="allow": unknown fields tolerated)
│  │  │  ├─ transport.py          # RecordingTransport / ReplayTransport (HTTP boundary only) + redaction
│  │  │  └─ simulator.py          # SandboxSimulator: deposit/create, transfers/{id}/transition, rfis/create (absent in prod)
│  │  ├─ fake_airwallex.py        # in-process stateful fake for the eval at scale; parity-tested against recorded fixtures
│  │  ├─ webhooks.py              # optional receiver: raw-body HMAC verify, tolerance, dedupe → enqueue poll
│  │  └─ llm/                     # Week 2 optional: provider.py (interface), anthropic_provider.py, extract.py (one doc per call)
│  ├─ workers/
│  │  ├─ executor.py              # single-writer executor: rebuild packet → guards → INTENT → call → lookup-before-retry
│  │  └─ poller.py                # primary status mechanism: transfers, conversions, balances, RFIs
│  ├─ api/                        # FastAPI routers (Week 2): queue, approve (WebAuthn), incidents, recon, killswitch
│  └─ ui/templates/               # Jinja (autoescape), HTMX partials; "AI explanation (unverified)" box; demo-timing labels
├─ scripts/
│  ├─ day1_spike.py               # runs the §2 U-list against live sandbox, writes findings JSON (no app code paths)
│  ├─ record_fixtures.py          # records named scenarios through RecordingTransport (live, guarded)
│  ├─ check_fixtures.py           # redaction + schema lint over tests/fixtures (CI)
│  ├─ seed_sandbox.py             # live: GA reuse/create, simulated deposit, beneficiaries for demo vendors
│  ├─ seed_local.py               # SQLite: vendors, contacts (aged), roster, seeded bill-#1 history (labelled)
│  ├─ gen_calendars.py            # writes app/core/calendars/*.yaml from `holidays` (dev only)
│  ├─ register_passkeys.py        # starts local server page to register demo approver passkeys
│  └─ run_demo.py                 # scripted demo against live sandbox (or replay) with on-screen labels
├─ eval/
│  ├─ scenarios/S01.yaml … S20.yaml   # exactly 20 labelled scenarios (§5(h))
│  ├─ harness.py                  # runs pipeline per scenario, compares to labels, computes metrics
│  └─ results/                    # metrics.csv, per_scenario.csv, run_meta.json (committed only from make eval)
├─ tests/
│  ├─ conftest.py                 # blocks sockets unless @pytest.mark.live; freezes AWX_ENV=sandbox
│  ├─ unit/                       # pure logic per module
│  ├─ property/                   # hypothesis suites
│  ├─ contract/                   # client vs recorded fixtures; fake_airwallex parity
│  ├─ acceptance/                 # T-01..T-34 + milestone acceptance tests (file per milestone)
│  ├─ live/                       # @pytest.mark.live, manual only
│  └─ fixtures/
│     ├─ airwallex/<scenario>/NNN_<METHOD>_<path-slug>.json   # redacted request/response pairs
│     ├─ airwallex/manifest.json  # recorded_at (IST), account API version, sandbox notes per scenario
│     ├─ webhooks/                # raw body + headers captures (if webhooks were enabled during recording)
│     ├─ bills/                   # Week 1 structured InvoiceDraft JSON; Week 2 synthetic PDFs/.eml incl. injection cases
│     └─ vendors/                 # vendor master + contacts with created_at provenance
└─ docs/
   ├─ adr/                        # 0001-polling-primary, 0002-split-packets, 0003-webauthn-vs-hmac, 0004-policy-floor
   ├─ undocumented-behaviour.md   # day-1 findings register (U1-U14), each linked to a fixture
   └─ demo-script.md
```

### 4.3 `.env` variables (`.env.example` holds placeholders only)
| Var | Req | Example | Description |
|---|---|---|---|
| `AWX_ENV` | yes | `sandbox` | Must equal `sandbox`, or the process exits non-zero (T-09b) |
| `AWX_BASE_URL` | yes | `https://api.sandbox.airwallex.com` | Exact-match allowlist. Anything else → refuse start (T-09a) |
| `AWX_CLIENT_ID` | live only | `your-sandbox-client-id` | From sandbox web app → Account > Developer > API keys [guide] |
| `AWX_API_KEY` | live only | `your-sandbox-api-key` | Same. Held only by executor/poller processes; never logged, never sent to the LLM |
| `AWX_LOGIN_AS` | no | *(empty)* | `x-login-as` for scoped keys spanning accounts [MCP auth] |
| `AWX_API_VERSION` | no | *(empty)* | If set, sent as `x-api-version` on non-`/fx/` paths only (A42). Leave empty to use the account version |
| `AWX_MIN_ACCOUNT_API_VERSION` | yes | `2025-06-30` | Startup check against the version recorded by the day-1 spike (A43) |
| `AWX_MODE` | yes | `replay` | `replay` (tests/CI, no network) \| `live` (sandbox) \| `record` (live + write fixtures) |
| `AWX_FIXTURES_DIR` | yes | `tests/fixtures/airwallex` | Replay/record root |
| `AWX_REQUEST_ID_NAMESPACE` | yes | `3f1c2a9e-0000-4000-8000-000000000001` | UUID namespace for `uuid5` request ids (P19). Generate once per install |
| `AWX_RPS_GLOBAL` | no | `20` | [guide] global limit |
| `AWX_RPS_PER_ENDPOINT` | no | `10` | [guide] |
| `AWX_MAX_CONCURRENCY` | no | `10` | [guide] |
| `AWX_HTTP_TIMEOUT_S` | no | `20` | A timeout on a mutating call → AMBIGUOUS |
| `APP_DB_PATH` | yes | `var/app.sqlite` | SQLite file |
| `APP_POLICY_PATH` | yes | `policy.example.yaml` | Must validate against the floor and carry valid signatures |
| `APP_POLICY_SIG_PATH` | yes | `policy.sig.json` | Two approver signatures over the policy file hash |
| `APP_HALT_FILE` | yes | `var/HALT` | Kill switch file. Unreadable = halted (T-07) |
| `APP_AUDIT_CHECKPOINT_DIR` | yes | `var/audit-checkpoints` | **Outside** the DB file. Signed checkpoints |
| `APP_AUDIT_SIGNING_KEY_PATH` | yes | `var/keys/audit_ed25519.pem` | Generated by `make setup`; never committed |
| `APP_DISPLAY_TZ` | no | `Asia/Kolkata` | UI timestamps; daily caps use the IST calendar day (row 14) |
| `APP_DEMO_TIMING` | no | `false` | `true` enables cooling-off 2 min and settle 2 min **only** if `AWX_ENV=sandbox` and the host pin passes. Every affected screen is labelled |
| `SIGNING_MODE` | yes | `webauthn` | `webauthn` \| `hmac_fallback` (UI banner + README disclosure when fallback) |
| `WEBAUTHN_RP_ID` | webauthn | `localhost` | Relying-party id |
| `WEBAUTHN_RP_NAME` | webauthn | `Payment run sign-off (demo)` | |
| `WEBAUTHN_ORIGIN` | webauthn | `http://localhost:8000` | Expected origin |
| `APPROVER_HMAC_KEYS_PATH` | fallback | `var/keys/approvers.json` | Per-approver random 32-byte keys; generated locally; never committed |
| `POLL_INTERVAL_S` | no | `2` | Fast poll near state changes (U2) |
| `POLL_MAX_INTERVAL_S` | no | `60` | Backoff ceiling |
| `WEBHOOKS_ENABLED` | no | `false` | Optional, additive (constraint 6) |
| `AWX_WEBHOOK_SECRET` | if webhooks | `whsec-placeholder` | Per-URL secret from Settings > Developer > Webhooks |
| `WEBHOOK_TOLERANCE_SECONDS` | no | `300` | Our replay window (A35) |
| `VERIFY_ACCOUNT_ENABLED` | no | `false` | VoP lookup = evidence only, never a release path (T-14) |
| `LLM_ENABLED` | no | `false` | Week 2. When false, PDFs/emails go to REVIEW and nothing is T0 (T-18) |
| `LLM_PROVIDER` | if LLM | `anthropic` | |
| `ANTHROPIC_API_KEY` | if LLM | `sk-ant-placeholder` | Never available to the executor process |
| `LLM_MODEL` | if LLM | `<model id from your provider console>` | Not hard-coded; recorded in eval `run_meta.json` |
| `APP_HOST` / `APP_PORT` | no | `127.0.0.1` / `8000` | |
| `LOG_LEVEL` | no | `INFO` | Logs are redacted (account numbers masked `•••• 4821`) |

### 4.4 Airwallex sandbox setup (cited; ✅ = documented, ⚠️ = unverified until the day-1 spike)
1. ✅ Sign up at `sandbox.airwallex.com`. Name the business **`Sandbox Business`** or **`New Business Sandbox`** so KYB auto-approves; "Any other name stays In review" (`raw/2e9b4f34.html:92`).
2. ✅ **API key:** web app → **Account > Developer > API keys**. Copy the Client ID and API key into `.env` [guide]. ⚠️ Scopes: the scope table (`raw/doc_bal_hist.txt:549-600`) lists `balance:read`, `global_account:write` and `financial_transaction:read`. I didn't capture the payout/FX/beneficiary scope names, so the spike asserts every endpoint we call returns non-403 and records it.
3. ✅ **Auth:**
   ```sh
   curl -sS -X POST https://api.sandbox.airwallex.com/api/v1/authentication/login \
     -H "x-client-id: $AWX_CLIENT_ID" -H "x-api-key: $AWX_API_KEY"
   # → {"token":"...","expires_at":"...+0000"}  valid 30 min [MCP: Obtain an access token]
   ```
4. ⚠️ **Record the account API version** (U6). Docs say "log in to view your version" [MCP: Versioning]. Put it in `tests/fixtures/airwallex/manifest.json`. Abort if it is below `2025-06-30`.
5. ✅ **Fund:** `GET /api/v1/global_accounts`. Reuse a USD LOCAL GA, or `POST /api/v1/global_accounts/create {"request_id":"<uuid>","country_code":"US","required_features":[{"currency":"USD","transfer_method":"LOCAL"}]}`. Then `POST /api/v1/simulation/deposit/create {"global_account_id":"…","amount":25000,"payer_name":"Seed funding","reference":"SEED-1"}` (`raw/2e9b4f34.html:385-400`: "Amounts are major units… The balance is available immediately even if the response says PENDING"; EUR GA needs `country_code` NL/DE/FR, not BE). Re-read `GET /api/v1/balances/current` (A8).
6. ✅ **Corridor beneficiaries** (demo vendors): `POST /api/v1/beneficiary_api_schemas/generate` → `POST /api/v1/beneficiaries/validate` → `POST /api/v1/beneficiaries/create`, with `nickname="cs-<payee_version_id>"`. Corridors are US/USD/LOCAL (ABA, `bank_account_category` exactly `Checking`), GB/GBP/LOCAL (`sort_code` lowercase, `bank_name` required) and **DE/EUR/LOCAL (SEPA, IBAN)** [guide beneficiary notes]. ⚠️ The DE LOCAL payload shape is not in the guide (it shows DE SWIFT), so get it from the schema endpoint.
7. ✅ **FX:** `POST /api/v1/fx/quotes/create` (`validity: "HR_4"`) → `POST /api/v1/fx/conversions/create` with `quote_id`, no `x-api-version` [guide; MCP].
8. ✅ **Transfers + status simulation:** `POST /api/v1/transfers/create` → `POST /api/v1/simulation/transfers/{id}/transition` with `{"next_status":"PROCESSING"}`, then `SENT`, then `PAID`, or `{"next_status":"FAILED","failure_type":"ACCOUNT_CLOSED"}` after SENT (`doc_failure_types.txt:27-63`). ⚠️ PAID→FAILED (U1). ⚠️ Is `failure_type` still on the auto-CANCELLED object (U2)?
9. ⚠️ **RFI:** `POST /api/v1/simulation/rfis/create` with `type: "TRANSACTION"` linked to the transfer via question `sources`, then poll `GET /api/v1/rfis?types=TRANSACTION&statuses=ACTION_REQUIRED` [MCP: Transaction RFI] (U11).
10. ✅ **Recon:** `GET /api/v1/financial_transactions?from_created_at=…` and `GET /api/v1/balances/history?from_post_at=…&currency=EUR` (`doc_fin_tx.txt`, `doc_bal_hist.txt`). ⚠️ How third-party and FX cancellation fees appear as `transaction_type` rows (U13). ⚠️ Whether PAYOUT rows include the fee or a separate FEE row exists (U14).
11. Optional ✅ **Webhooks:** web app → Settings > Developer > Webhooks; copy the secret; tunnel with cloudflared [airwallexdev guide]. Subscribe with the same API version as the account.
12. **Day-1 spike (Sun 25 Oct, after 10:00 AM IST, per M1):** `make spike` runs `scripts/day1_spike.py` for U1-U14 and Staff T1-T15, then `make fixtures-record` for every scenario in §5(a). Findings go to `docs/undocumented-behaviour.md`.

Additional unverified items from this batch:
- **U11.** RFI simulation on a non-platform sandbox account.
- **U12.** `failure.details.reason_codes` path on TM_SUSPENDED.
- **U13.** How third-party and FX-delta fees are typed in `financial_transactions`.
- **U14.** Fee placement in financial transactions (inside PAYOUT `fee` vs separate FEE rows).

### 4.5 Makefile (complete; recipe lines are real tabs)
```make
SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help
UV      ?= uv
PY      := $(UV) run --frozen python
PYTEST  := $(UV) run --frozen pytest
export AWX_ENV ?= sandbox

.PHONY: help setup lint fmt typecheck test test-unit test-property test-contract test-acceptance test-live \
        spike fixtures-record fixtures-check seed seed-local eval eval-live eval-selftest demo serve \
        verify-audit calendars passkeys keys ci clean

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "%-18s %s\n",$$1,$$2}'

setup: ## install pinned toolchain + deps, create .env, local keys, DB
	$(UV) python install 3.12.15
	$(UV) sync --frozen
	test -f .env || cp .env.example .env
	mkdir -p var/keys var/audit-checkpoints
	$(MAKE) keys
	$(PY) -m app.core.db init

keys: ## generate local audit Ed25519 key + per-approver HMAC fallback keys (never committed)
	test -f var/keys/audit_ed25519.pem || $(PY) -m app.core.audit genkey var/keys/audit_ed25519.pem
	test -f var/keys/approvers.json || $(PY) -m app.core.signing gen-hmac-keys var/keys/approvers.json

lint: ## ruff lint + format check + mypy
	$(UV) run --frozen ruff check .
	$(UV) run --frozen ruff format --check .
	$(MAKE) typecheck

fmt: ## auto-format
	$(UV) run --frozen ruff format .
	$(UV) run --frozen ruff check --fix .

typecheck:
	$(UV) run --frozen mypy app

test: test-unit test-property test-contract test-acceptance ## all offline suites (no network, AWX_MODE=replay)

test-unit:
	AWX_MODE=replay $(PYTEST) tests/unit -q --timeout=60

test-property:
	AWX_MODE=replay $(PYTEST) tests/property -q --timeout=300

test-contract: fixtures-check ## client + fake parity against recorded sandbox fixtures
	AWX_MODE=replay $(PYTEST) tests/contract -q --timeout=120

test-acceptance: ## milestone acceptance + Compliance T-01..T-34
	AWX_MODE=replay $(PYTEST) tests/acceptance -q --timeout=300 --cov=app --cov-report=term-missing

test-live: ## live sandbox, manual only (needs AWX_CLIENT_ID/AWX_API_KEY)
	test "$${CONFIRM_LIVE:-}" = "1" || { echo "set CONFIRM_LIVE=1"; exit 2; }
	AWX_MODE=live $(PYTEST) tests/live -m live -q --timeout=900

spike: ## day-1 spike: U1-U14 + Staff T1-T15 against live sandbox; writes docs/undocumented-behaviour.md
	test "$${CONFIRM_LIVE:-}" = "1" || { echo "set CONFIRM_LIVE=1"; exit 2; }
	AWX_MODE=live $(PY) scripts/day1_spike.py --out docs/undocumented-behaviour.md

fixtures-record: ## record sandbox fixtures (SCENARIO=name or all); redacts before writing
	test "$${CONFIRM_LIVE:-}" = "1" || { echo "set CONFIRM_LIVE=1"; exit 2; }
	AWX_MODE=record $(PY) scripts/record_fixtures.py --scenario "$${SCENARIO:-all}" --out $${AWX_FIXTURES_DIR:-tests/fixtures/airwallex}
	$(MAKE) fixtures-check

fixtures-check: ## fail if any fixture holds a token/key/full account number, or a manifest entry is missing
	$(PY) scripts/check_fixtures.py tests/fixtures

calendars: ## regenerate holiday calendar fixtures (dev only; commit the diff)
	$(PY) scripts/gen_calendars.py --years 2026 2027 --out app/core/calendars

seed-local: ## SQLite: vendors, aged contacts, roster, labelled bill-#1 history
	$(PY) scripts/seed_local.py

seed: seed-local ## live sandbox: GA reuse/create, simulated deposit, demo beneficiaries (idempotent)
	test "$${CONFIRM_LIVE:-}" = "1" || { echo "set CONFIRM_LIVE=1"; exit 2; }
	AWX_MODE=live $(PY) scripts/seed_sandbox.py

eval: ## run exactly 20 labelled scenarios offline (FakeAirwallex); metrics computed from run outputs
	AWX_MODE=replay $(PY) -m eval.harness --scenarios eval/scenarios --expect-count 20 --out eval/results

eval-selftest: ## proves metrics move when a control is disabled (guards against hardcoded metrics)
	AWX_MODE=replay $(PY) -m eval.harness --scenarios eval/scenarios --expect-count 20 --selftest --out var/eval-selftest

eval-live: ## run the live-capable subset against sandbox
	test "$${CONFIRM_LIVE:-}" = "1" || { echo "set CONFIRM_LIVE=1"; exit 2; }
	AWX_MODE=live $(PY) -m eval.harness --scenarios eval/scenarios --live-subset --out eval/results/live

passkeys: ## register the 3 demo approvers + ops user passkeys in a browser
	$(PY) scripts/register_passkeys.py

serve: ## web UI on APP_HOST:APP_PORT
	$(UV) run --frozen uvicorn app.api.main:app --host $${APP_HOST:-127.0.0.1} --port $${APP_PORT:-8000}

demo: ## scripted demo against live sandbox (DEMO_MODE=replay for offline rehearsal)
	AWX_MODE=$${DEMO_MODE:-live} $(PY) scripts/run_demo.py

verify-audit: ## verify hash chain + signed checkpoints; non-zero exit on any break (T-13)
	$(PY) -m app.core.audit verify --db $${APP_DB_PATH:-var/app.sqlite} --checkpoints $${APP_AUDIT_CHECKPOINT_DIR:-var/audit-checkpoints}

ci: lint test eval eval-selftest ## what CI runs

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache var/eval-selftest htmlcov .coverage
```

### 4.6 GitHub Actions CI (`.github/workflows/ci.yml`, complete)
```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
    inputs:
      run_live:
        description: "Run live sandbox job (type YES)"
        required: true
        default: "NO"

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

env:
  AWX_ENV: sandbox
  AWX_BASE_URL: https://api.sandbox.airwallex.com
  AWX_MODE: replay
  AWX_FIXTURES_DIR: tests/fixtures/airwallex
  AWX_REQUEST_ID_NAMESPACE: 00000000-0000-4000-8000-0000000000c1
  AWX_MIN_ACCOUNT_API_VERSION: "2025-06-30"
  APP_DB_PATH: var/ci.sqlite
  APP_POLICY_PATH: tests/fixtures/policy/policy.ci.yaml
  APP_POLICY_SIG_PATH: tests/fixtures/policy/policy.ci.sig.json
  APP_HALT_FILE: var/HALT
  APP_AUDIT_CHECKPOINT_DIR: var/audit-checkpoints
  APP_AUDIT_SIGNING_KEY_PATH: var/keys/audit_ed25519.pem
  APPROVER_HMAC_KEYS_PATH: var/keys/approvers.json
  SIGNING_MODE: webauthn
  WEBAUTHN_RP_ID: localhost
  WEBAUTHN_RP_NAME: ci
  WEBAUTHN_ORIGIN: http://localhost:8000
  LLM_ENABLED: "false"
  WEBHOOKS_ENABLED: "false"

jobs:
  offline:
    name: lint + unit + property + contract + acceptance + eval (no secrets, no network)
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v7.0.1
      - uses: astral-sh/setup-uv@v10.2.0
        with:
          version: "0.12.23"
      - run: uv python install 3.12.15
      - run: uv sync --frozen
      - name: prepare local keys + DB
        run: |
          mkdir -p var/keys var/audit-checkpoints
          make keys
          uv run --frozen python -m app.core.db init
      - run: make lint
      - name: tests (sockets blocked by conftest; secrets absent by construction)
        run: make test
      - name: eval (20 labelled scenarios) + selftest
        run: |
          make eval
          make eval-selftest
      - name: audit verify on the test DB
        run: make verify-audit
      - uses: actions/upload-artifact@v7.0.2
        if: always()
        with:
          name: eval-results
          path: |
            eval/results/
            var/eval-selftest/

  live-sandbox:
    name: live sandbox (manual)
    if: github.event_name == 'workflow_dispatch' && inputs.run_live == 'YES'
    needs: offline
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    environment: airwallex-sandbox   # protected environment: required reviewer = repo owner
    env:
      AWX_MODE: live
      AWX_CLIENT_ID: ${{ secrets.AWX_CLIENT_ID }}
      AWX_API_KEY: ${{ secrets.AWX_API_KEY }}
      CONFIRM_LIVE: "1"
    steps:
      - uses: actions/checkout@v7.0.1
      - uses: astral-sh/setup-uv@v10.2.0
        with:
          version: "0.12.23"
      - run: uv python install 3.12.15
      - run: uv sync --frozen
      - run: |
          mkdir -p var/keys var/audit-checkpoints
          make keys
          uv run --frozen python -m app.core.db init
      - run: make test-live
      - run: make eval-live
      - uses: actions/upload-artifact@v7.0.2
        if: always()
        with:
          name: live-results
          path: eval/results/live/
```
CI notes:
- Secrets exist only in the `airwallex-sandbox` environment. The `offline` job has none, so a test that tries the network fails because `conftest.py` blocks sockets.
- No job records fixtures (recording is local, `make fixtures-record`).
- The live job's sandbox host pin still applies, so the secrets can't be pointed at production.
- ⚠️ Check the `setup-uv` `version` input name against the v10 README when the repo is created.

### 4.7 Test honesty checklist (the coding agent must follow it, and it goes in `CONTRIBUTING.md`)
1. **Red first.** Write each acceptance test before the behaviour and run it against a stub that raises `NotImplementedError`; it must fail. Put the failing output in the PR description.
2. **Never mock the code under test.** Mocks/fakes are allowed only at the **HTTP boundary** (ReplayTransport replaying *recorded* sandbox bytes, or `FakeAirwallex`), the **clock** (`time-machine`) and **randomness** (seeded). No `patch("app.core.…")` in tests of `app.core`.
3. **Assert outcomes, not calls.** Check DB rows, ledger postings, audit entries, HTTP requests actually emitted by the transport, packet hashes and exit codes. `assert_called_once` is not an acceptance assertion.
4. **The fake is held to the same contract as the real thing.** Every `FakeAirwallex` behaviour used by the eval needs a parity test that replays the same request sequence against a recorded fixture and compares the normalised responses. Undocumented fake behaviour = test failure.
5. **No hardcoded metric outputs.** Eval metrics are computed by `eval/harness.py` from per-scenario run artefacts compared with labels in `S*.yaml`. `make eval-selftest` disables a control (e.g. the duplicate lock) and must see the relevant metric drop. If it doesn't, CI fails.
6. **Exactly 20 labelled scenarios.** The harness asserts `count == 20` and that each label file has `expected:` blocks. Labels are written before the run and are never generated from outputs.
7. **Negative paths are mandatory.** Each control ships at least one test proving the money does **not** move when the control fails: no transfer request emitted, balance unchanged, audit shows the refusal.
8. **No skipped or xfail acceptance tests on main** without a linked issue and a README "known gaps" line. CI greps for `skip`/`xfail` in `tests/acceptance` and lists them.
9. **No sleeps, no network, no wall clock** in offline tests. Time comes from `time-machine`; sockets are blocked.
10. **Fixtures are evidence.** They're recorded from the real sandbox and redacted, never hand-written (except the webhook signature vectors, which are computed in the test from a known secret). `manifest.json` records who, when (IST) and which API version. A hand-edited fixture fails `fixtures-check` via its stored sha256.
11. **Don't touch a test to make it pass.** A change to an assertion needs a PR note explaining why the old expectation was wrong.
12. **Coverage is reported, not targeted.** No % gate is presented as quality.

---

## 5. Coding-agent prompts (milestone order follows constraint 10: Week 1 = money path, no LLM, no UI)

Order and timing:
- **Week 1:** (a) → (b) → (c) Part 1 → (d) → (e) Part 1 → (f) Part 1.
- **Week 2:** (f) Part 2, (g), (e) Part 2 (UI + passkeys), (c) Part 2 (optional LLM).
- **Week 3:** (h).

Each prompt is **COMMON HEADER + milestone body**. Paste both. They are self-contained, apart from the shared files the earlier milestones produced, which are named explicitly.

### 5.0 COMMON HEADER (paste at the top of every prompt)
```text
You are building a greenfield Python service that pays supplier bills through the Airwallex SANDBOX
API with human countersign. Repo root <repo>/, package `app`. Work only inside the repo.

STACK (exact pins, already in pyproject.toml/uv.lock; do not add deps without asking):
Python 3.12.15, uv 0.12.23, fastapi 0.143.0, uvicorn 0.54.0, httpx 0.28.1, sqlalchemy 2.1.4 (Core,
SQLite only), pydantic 2.13.5, pydantic-settings 2.15.0, pyyaml 6.0.3, rfc8785 0.1.4, webauthn 3.0.1,
cryptography 50.0.2, jinja2 3.1.6, python-multipart 0.0.32, pdfplumber 0.11.10, pypdf 6.19.0,
anthropic 1.12.1 (optional), holidays 0.106 (dev), pytest 9.1.1, hypothesis 6.168.5, pytest-cov 7.1.0,
pytest-timeout 2.4.0, time-machine 3.5.1, ruff 0.16.10, mypy 2.4.0.
NOT ALLOWED: Postgres/Alembic, Slack, Metal, CSV import, Airwallex native approvals, respx/vcrpy,
LLM calls anywhere in the money path, floats for money (use Decimal; serialise amounts as strings).

AIRWALLEX FACTS (from the docs; do not "improve" them):
- Base https://api.sandbox.airwallex.com/api/v1. POST /authentication/login with headers x-client-id,
  x-api-key → {token, expires_at}; the token is valid 30 min; refresh 5 min early; Bearer auth.
- No x-api-version by default (the account version applies). If AWX_API_VERSION is set, send it only
  on non-/fx/ paths.
- request_id: unique per 7 days; a duplicate gets HTTP 400 code duplicate_request_id. Airwallex does
  NOT replay the original response. Transfers: ≤50 chars. Conversions: ≤64 chars. Our ids are uuid5 =
  36 chars, derived as uuid5(AWX_REQUEST_ID_NAMESPACE, f"{kind}:{entity_id}:{tranche_no}:{attempt_no}")
  with NO run_id. beneficiaries/create has NO request_id: use nickname "cs-{payee_version_id}" and
  look up with GET /beneficiaries?nick_name= plus an exact client-side match.
- Transfer statuses (API ≥2025-06-30): IN_APPROVAL, SCHEDULED, OVERDUE, PROCESSING, SENT, PAID,
  FAILED, CANCELLED. Transitions: SCHEDULED→PROCESSING|OVERDUE|CANCELLED; OVERDUE→PROCESSING|CANCELLED;
  PROCESSING→SENT|FAILED; SENT→PAID|FAILED; PAID→FAILED (returns); FAILED→CANCELLED automatically
  within seconds. Persist failure_type/failure_reason the first time you see them.
- Error classes: 2xx=OK; 400 with a validation code = REJECTED (definitive); 400 duplicate_request_id
  = EXISTS (look up); 401 credentials_expired = re-auth once; 429 = back off (20 rps global,
  10/endpoint, 10 concurrent); timeout/connection error/5xx on a MUTATING call = AMBIGUOUS. Never
  blind-retry AMBIGUOUS: look up by request_id (or nickname) first and retry with the SAME key only if
  the lookup is empty. Insufficient funds codes: balance_insufficient (transfers),
  insufficient_funds (FX).

TEST HONESTY RULES (non-negotiable):
1. Write the acceptance test first; it must fail against a NotImplementedError stub. Show that output.
2. Never mock code under test. Fakes are allowed only at the HTTP boundary (ReplayTransport over
   recorded sandbox fixtures, or FakeAirwallex with parity tests), the clock (time-machine) and seeds.
3. Assert outcomes (DB rows, ledger, audit entries, HTTP requests actually emitted, exit codes),
   not mock calls.
4. Every control has a negative test proving money does NOT move when the control fails.
5. No sleeps, no network, no wall clock in offline tests (conftest blocks sockets). No hardcoded
   metrics. No skip/xfail in tests/acceptance without a README "known gaps" line.
Run `make lint test` before you say "done". Paste the summary output.

### 5(a) Airwallex client + record/replay fixtures. Week 1, day 1-2 (Sun 25 to Mon 26 Oct)
```text
GOAL: app/integrations/airwallex/{client.py,errors.py,models.py,transport.py,simulator.py},
app/config.py, scripts/{day1_spike.py,record_fixtures.py,check_fixtures.py}, tests/contract/*,
tests/conftest.py. One typed client that every other module uses. No business logic here.

INTERFACES (exact):
class AirwallexClient:
  login() -> None                                  # caches token + expires_at; refresh at expires_at-5min
  get_balances() -> list[Balance]                  # GET /balances/current
  get_balance_history(currency, from_post_at, to_post_at) -> Iterator[BalanceHistoryItem]  # ≤7-day windows, page cursor
  generate_beneficiary_schema(country, currency, transfer_method, entity_type) -> dict  # POST /beneficiary_api_schemas/generate
  validate_beneficiary(payload) -> ValidationResult  # POST /beneficiaries/validate
  create_beneficiary(payload, nickname) -> IdemResult[Beneficiary]   # lookup-before-retry by nickname
  find_beneficiary_by_nickname(nickname) -> Beneficiary | None       # exact match over all pages
  verify_account(payload) -> VerifyResult           # POST /beneficiaries/verify_account (evidence only)
  create_quote(sell_currency, buy_currency, buy_amount|sell_amount, validity) -> Quote  # POST /fx/quotes/create
  create_conversion(request_id, quote_id, buy_currency, sell_currency, buy_amount) -> IdemResult[Conversion]
  find_conversion_by_request_id(request_id) -> Conversion | None     # GET /fx/conversions?request_id=
  get_conversion(conversion_id) -> Conversion
  create_transfer(request_id, payload) -> IdemResult[Transfer]
  find_transfer_by_request_id(request_id) -> Transfer | None         # GET /transfers?request_id= (widen from_created_at to 30d)
  get_transfer(transfer_id) -> Transfer
  list_financial_transactions(from_created_at, to_created_at, source_id=None, currency=None) -> Iterator[FinTx]
  list_rfis(statuses, types) -> list[Rfi]; get_rfi(id) -> Rfi       # GET /rfis
class IdemResult: outcome in {CREATED, EXISTS_FOUND, REJECTED, AMBIGUOUS}, obj | None, error_code | None
SandboxSimulator (only constructible when AWX_ENV == "sandbox"): deposit(global_account_id, amount,
  reference), transition_transfer(id, next_status, failure_type=None), create_rfi(...).
Every create_* follows: send → on 2xx CREATED; on 400 duplicate_request_id/nickname exists → lookup →
EXISTS_FOUND; on 400 other → REJECTED; on timeout/conn/5xx → lookup → found ⇒ EXISTS_FOUND, empty ⇒
retry ONCE with the same key/nickname → still unknown ⇒ AMBIGUOUS. Never invent a new key.

TRANSFER PAYLOAD (required fields): reason (enum below), reference (≤ Airwallex limit, charset
[A-Za-z0-9 -/.]), request_id, transfer_currency; plus beneficiary_id, transfer_amount (string),
source_currency, transfer_method ("LOCAL"|"SWIFT"), swift_charge_option="PAYER" and fee_paid_by="PAYER"
for SWIFT only. reason enum: audio_visual_services, bill_payment, business_expenses, construction,
donation_charitable_contribution, education_training, freight, goods_purchased, investment_capital,
investment_proceeds, living_expenses, loan_credit_repayment, medical_services, pension,
professional_business_services, real_estate, taxes, technical_services, transfer_to_own_account,
travel, wages_salary, other_services. Read fee_amount, fee_currency, amount_payer_pays,
amount_beneficiary_receives from responses. Never compute fees.

SAFETY (T-09): config refuses to start unless AWX_ENV == "sandbox" and AWX_BASE_URL ==
"https://api.sandbox.airwallex.com" exactly. httpx.Client(trust_env=False, follow_redirects=False).
Any 3xx → error + kill-switch trip hook (callable injected; the kill switch itself comes in (b)).
Compare the server Date header with local UTC; skew > 120 s → raise ClockSkewError (trip hook).

FIXTURES: transport.py provides RecordingTransport/ReplayTransport (httpx.BaseTransport).
Layout: tests/fixtures/airwallex/<scenario>/NNN_<METHOD>_<path-slug>.json, each file holding
{request:{method,path,query,headers_subset,body}, response:{status,headers_subset,body}, sha256}.
manifest.json maps scenario → {recorded_at_ist, recorded_by, account_api_version, notes}.
Redaction BEFORE writing: drop the Authorization, x-api-key and x-client-id values; replace token
values; mask account_number/iban/routing to the last 4 digits; keep ids. Replay matches in order on
method+path+query+body (volatile fields like request_id/dates matched by regex placeholders
recorded in the file). Unmatched or extra requests raise ReplayMismatch. Leftover un-replayed
entries fail the test at teardown. Fault injection: ReplayTransport(raise_on={"NNN": ReadTimeout})
raises AFTER the recorded request (the server really did receive it) to model ambiguous timeouts.
check_fixtures.py fails on any 9+ digit run outside masked fields, any "token" value, a sha256
mismatch (hand edits), or a missing manifest entry.

SCENARIOS TO RECORD (make fixtures-record CONFIRM_LIVE=1; one dir each):
auth_ok, auth_bad_key, balances, ga_list_and_deposit, schema_de_eur_local, schema_us_usd_local,
benef_validate_ok, benef_validate_bad_iban, benef_create_then_lookup_by_nickname,
quote_hr4_then_conversion, conversion_duplicate_request_id, conversion_lookup_by_request_id,
transfer_local_eur_paid (create→PROCESSING→SENT→PAID, polling GETs),
transfer_swift_payer_fee (swift_charge_option=PAYER, fee fields), transfer_duplicate_request_id,
transfer_insufficient_funds, transfer_failed_account_closed_after_sent (FAILED → auto-CANCELLED; poll
until CANCELLED), transfer_paid_then_failed (U1, record even if rejected), transfer_validation_400,
fin_tx_window, balance_history_window, rfi_simulated (U11; record even if rejected), webhook test event
(only if WEBHOOKS_ENABLED; save raw body + headers to tests/fixtures/webhooks/).

ACCEPTANCE TESTS (tests/contract/test_client_*.py, all via ReplayTransport):
- login caches; with time-machine at expires_at-4min the next call re-logs in (2 logins recorded).
- auth_bad_key → AuthError carrying code credentials_invalid; no retry loop (1 request emitted).
- create_transfer on transfer_duplicate_request_id → EXISTS_FOUND with the original transfer id
  (lookup GET emitted).
- create_transfer with raise_on timeout on the create → lookup finds it → EXISTS_FOUND; exactly one
  POST emitted.
- the same with an empty lookup fixture → one retry with an IDENTICAL request_id (assert byte-equal
  body) → AMBIGUOUS if it times out again.
- create_conversion: same three cases against conversion_* fixtures (≤64-char key, buy_amount
  string).
- create_beneficiary: the timeout-after-create fixture → nickname lookup finds it → EXISTS_FOUND;
  no second POST.
- transfer_validation_400 → REJECTED with the error code and the field from the body; no lookup.
- insufficient funds → REJECTED with code balance_insufficient; no retry.
- 429 fixture (synthetic status at the transport, the only synthetic case) → backoff honoured with
  time-machine; ≤ AWX_RPS limits enforced (token bucket unit test).
- x-api-version is absent by default; when AWX_API_VERSION is set it appears on /transfers and
  NEVER on /fx/*.
- T-09 (a-d): AWX_ENV=production refuses start; AWX_BASE_URL=https://api.airwallex.com refuses
  start; a 302 fixture raises and calls the trip hook; HTTPS_PROXY set in env is ignored (assert
  the transport saw the sandbox host).
- Clock skew: a Date header 3 min off → ClockSkewError + trip hook called once.
- models tolerate unknown response fields (extra="allow") but reject a missing required field
  (failure_type stays optional).
- check_fixtures.py: a fixture with an unmasked IBAN fails; a hand-edited fixture fails the sha256
  check.
DEFINITION OF DONE: every recorded scenario has a passing contract test; `make test-contract` is
green offline; docs/undocumented-behaviour.md has a row per U1-U14 and links its fixture; no
business logic in the client.
```

### 5(b) Ledger, state machines, audit chain, policy floor, kill switch. Week 1, day 2-3 (Mon 26 to Tue 27 Oct)
```text
GOAL: app/core/{schema.sql,db.py,ledger.py,statemachine.py,audit.py,policy_floor.py,policy.py,
killswitch.py,money.py}. The trust substrate. Everything later writes through these modules.

DATA MODEL (schema.sql, SQLite, PRAGMA user_version=1, foreign_keys=ON, WAL):
vendor, contact(id, vendor_id, kind, value, created_at, changed_at, source), payee_version(id,
vendor_id, fingerprint, details_json_masked, created_at, superseded_at, cooling_off_until,
first_payment_cap, final_payment_count), bank_change_request, callback_verification, obligation,
plan_item, run, conversion, transfer(request_id UNIQUE, ...), approval_packet(id, kind
CONVERSION|PAYMENT, canonical_json, sha256), approval_signature(packet_id, approver_id, method
WEBAUTHN|HMAC_FALLBACK, sig, challenge_nonce UNIQUE, consumed_at), duplicate_lock(obligation_key
UNIQUE), incident, rfi, journal_line, recon_exception, webhook_event(event_id UNIQUE), audit_log(seq,
prev_hash, entry_hash, kind, payload_json, at), killswitch_state, policy_load.
Append-only: BEFORE UPDATE / BEFORE DELETE triggers RAISE(ABORT) on audit_log,
approval_signature (consumed_at is set via a separate consumption table), webhook_event.

STATE MACHINES (statemachine.py). Pure functions apply(state, observed) -> (new_state, effects):
- Transfer: the transitions in the common header. Unknown status → keep the state + incident
  UNKNOWN_STATUS. A regression (e.g. PAID observed after FAILED) → ignored + audited. Internal overlay
  statuses: AMBIGUOUS (create outcome unknown), FINAL (set by calendars in (d)/(f), never by timer),
  PRESUMED_SETTLED (SWIFT, labelled), RFI_OPEN.
- Conversion: CREATED → SETTLED | CANCELLED | OVERDUE (from GET /fx/conversions).
- Obligation: OPEN → PLANNED → APPROVED → EXECUTING → PAID → FINAL | FAILED → REPLACEMENT_PENDING;
  HOLD/QUARANTINE/COMPLIANCE_HOLD.

AUDIT (audit.py): entry_hash = sha256(prev_hash || rfc8785(payload) || seq || at_iso).
log_intent(kind, payload) must succeed BEFORE any mutating Airwallex call; log_result after. If
log_intent raises, the caller must not call the API (enforced in (f)). Signed checkpoints: every N=50
entries and at run end, write {seq, entry_hash, at} signed Ed25519 (APP_AUDIT_SIGNING_KEY_PATH) to
APP_AUDIT_CHECKPOINT_DIR (outside the DB). `python -m app.core.audit verify` recomputes the chain and
checks every checkpoint; non-zero exit on any mismatch.

LEDGER (ledger.py): double-entry per currency; post(entry) rejects unbalanced entries; accounts
include Wallet:<CCY>, AP:<vendor>, AP-clearing:<CCY>, Bank fees, FX gain/loss, Third-party fees.

POLICY FLOOR (policy_floor.py: HARD-CODED, from Compliance Round 2b; policy.yaml can only TIGHTEN):
 r1  cooling_off_hours >= 72            (demo override 2 min only if sandbox + host pin + APP_DEMO_TIMING)
 r2  callback_contact_min_age_days >= 30; contact older than the change and any other change;
     a changed contact is unusable 30 days
 r3  callback after the change request; valid <= 7 days; recorder role=ops ∉ requester_set ∪ approvers
 r4  first_payment_cap <= min(USD 2500, 0.5 × 12-month median FINAL); the excess = tranche 2, held
     until tranche 1 is FINAL
 r5  cap lifts only after >= 2 FINAL payments
 r6  t0_limit_usd <= 2000
 r7  t0 history >= 3 FINAL, each >= 25% of the limit, details unchanged >= 60 days
 r8  t0 band <= 1.5 × payee median
 r9  t0 disqualifiers ⊇ {duplicate_suspicion, EXTRACTION_CONFLICT, HIDDEN_TEXT, new_country,
     contact_lt_30d, unknown_sender, SWIFT, degraded_check, cap_headroom}
 r10 t0_enabled default false; turning it on needs 2 policy signatures
 r11 T1 < 10000 USD-eq; r12 T2 if >= 10000 or payee 7-day aggregate >= 10000 or any trigger;
     roster < 3 approvers → INSUFFICIENT_APPROVERS (no T2 possible)
 r13 per run: T0 <= 6000; all tiers <= 50000 and <= 40 payments
 r14 per IST day: T0 <= 6000; all <= 75000 and <= 60 payments; <= 2 runs; <= 5 new beneficiaries
 r15 per payee 7-day: T0 <= 2000
 r16 per payee 24 h: <= 1 T0, <= 3 payments of any tier
 r17 per approver per day <= 30000
 r18 approval expiry = min(quote.valid_to_at − 120 s, signed_at + 4 h); WebAuthn challenge
     = sha256(packet_sha256 || nonce), single-use, 5 min; approvals consumed on use
 r19 quote_safety_margin_seconds >= 120 (MIN_1 quotes never bookable)
 r20 fx_drift_bp <= 25: CONVERSION packet binds buy_amount and max_sell_amount = approved_sell × 1.0025
 r21 reserve_floor_usd present (demo 8000); missing → executor refuses to start
 r22 settle window >= 48 h AND >= the rail business-day window (SEPA 3 TARGET2 days; FPS 3 UK days;
     ACH 2 US days; SWIFT never by timer)
 r23 AMBIGUOUS > 6 days → human; never auto-retry
 r24-29 kill-switch trips: clock skew > 120 s; non-sandbox host; audit write failure; policy
     parse/signature failure; floor recheck failure; >= 2 AMBIGUOUS creates per run or rolling 24 h;
     >= 3 FAILED in 1 h; >= 3 EXTRACTION_CONFLICT in 24 h; compliance failure types
     (ACCOUNT_UNDER_RESTRICTION, TM_SUSPENDED, CHANNEL_POLICY); daily-cap breach attempt; audit
     verify failure; executor signature verification failure
 r30 clearing the kill switch = 2 distinct approver signatures + a reason
Each key has a direction (MAX or MIN or SUPERSET). policy.load(path) compares each value with the
floor; a looser value → PolicyLoosenError naming the row; unknown keys → PolicyUnknownKeyError
(e.g. `duplicates.enabled`, `skip_callback`); a missing required key → error; YAML anchors/tags →
error (safe_load + reject tags); policy.sig.json must hold 2 distinct approver signatures over
sha256(file bytes). Any load failure trips the kill switch and the process exits non-zero.

KILL SWITCH (killswitch.py): halted() is true if the DB flag is set OR the HALT file exists OR the
HALT file path is unreadable/permission-denied (fail closed). trip(reason) writes the audit entry +
flag + file. clear(sig_a, sig_b, reason) requires 2 distinct roster approvers with valid signatures
over sha256("clear|"+trip_id+"|"+reason) (verification lib from (e). Until then, accept an injected
verifier interface and test with the HMAC fallback).

ACCEPTANCE TESTS (tests/acceptance/test_b_*.py; real SQLite in tmp_path):
- property (hypothesis): any random sequence of observed transfer statuses → the stored status
  never regresses past FINAL/CANCELLED; failure_type, once set, is never nulled.
- FAILED observed then CANCELLED with failure_type=None → failure_type retained from FAILED.
- CANCELLED observed first with failure_type present → recorded (U2 path).
- the audit chain: append 200 entries, verify ok; UPDATE audit_log → sqlite3.IntegrityError
  (trigger); copy the DB file, edit a row via a raw file write of a recomputed chain → verify fails
  against the signed checkpoint (T-13).
- T-17: make the audit insert fail (DB opened read-only) → log_intent raises; a guarded_call(fn)
  helper never invokes fn (assert via an HTTP request counter on ReplayTransport: 0 requests).
- T-19 / T-27: for EACH floor row write a policy that loosens it by the smallest step → load raises
  PolicyLoosenError naming that row (parametrised over 30 rows; a row without a test = failure via a
  coverage assertion over policy_floor.ROWS). A tightened policy loads. An unknown key fails. A
  missing signature fails. A policy signed by one approver twice fails. Demo timing with
  AWX_ENV=sandbox loads, labelled; the same with the host pin failing → PolicyLoosenError.
- T-07: HALT file created → halted() True; HALT path chmod 000 → halted() True; clear with one
  approver → refused; two distinct → cleared + audited.
- ledger: an unbalanced entry is refused; hypothesis: the sum of all postings per currency == 0.
- T-34 (policy part): a roster with 2 humans → tier engine stub returns INSUFFICIENT_APPROVERS for any
  T2 trigger (the full test is in (e)).
DEFINITION OF DONE: `make test` green; `make verify-audit` exits 0 on a seeded DB and 1 on a
tampered copy; every floor row has a loosen test; no module outside app/core writes audit_log
directly.
```

### 5(c) Ingest, deterministic vendor match, duplicates, fingerprint, OOB verification. Part 1 in Week 1 (Wed 28 Oct); Part 2 (optional LLM) in Week 2
```text
GOAL Part 1 (NO LLM): app/core/{parsers.py,vendors.py,dupes.py,fingerprint.py,oob.py},
app/ingest/structured.py. Input = structured InvoiceDraft JSON (tests/fixtures/bills/*.json):
{source:{kind: email|upload, sender, received_at, message_id}, vendor_name, vendor_tax_id?,
invoice_number, invoice_date, due_date, currency, amount (string), bank:{country, iban|account_number+
routing|sort_code, bic?, account_name}, memo?}. Output = Obligation rows or a HOLD/QUARANTINE reason.

RULES (all deterministic code; an LLM must never decide any of these):
- parsers: IBAN mod-97 + country length; ABA checksum; UK sort code 6 digits; BIC 8/11; ISO-4217
  currency with exponent; amount Decimal with currency exponent; invoice-no normalisation (upper,
  strip spaces/dashes/leading zeros); reference charset [A-Za-z0-9 -/.] → reject otherwise (T-03).
- vendors.match(draft) → VendorMatch(vendor_id | None, rule) by priority: tax id exact → normalised
  legal name exact → known sender domain exact. A lookalike domain (edit distance ≤ 2 or a homoglyph
  map to a known domain) → QUARANTINE LOOKALIKE_DOMAIN, never a match. No fuzzy-name auto-match.
- fingerprint = sha256(rfc8785({country, currency, method, normalised account identifiers,
  bic})). A different fingerprint from the current payee_version → BankChangeRequest (status PENDING),
  obligation HOLD BANK_CHANGE; the old payee_version stays active for nothing new.
- dupes: (vendor_id, norm_invoice_no) exact → DUPLICATE; same vendor + same amount + due date ±7 days
  → SUSPECT_DUPLICATE (T2 trigger, T0 disqualifier); a split (several bills from the same vendor in
  7 days summing to ≥ a tier threshold) → SPLIT_SUSPECT T2 trigger (T-05). A duplicate_lock row with a
  UNIQUE obligation_key is taken at obligation creation.
- OOB (oob.py): verify_callback(change_id, contact_id, recorded_by, outcome, at) succeeds ONLY if
  (1) recorded_by has role ops and ∉ {requester, intake person, any approver of the run};
  (2) contact.created_at ≤ change.created_at − 30 days, the contact is not from the change
      email/attachment, the contact has not been changed in the last 30 days, and its changed_at <
      change.created_at;
  (3) at > change.created_at and at ≤ change.created_at + 7 days.
  After verification the new payee_version gets cooling_off_until = verified_at + 72 h (demo 2 min
  only under the r1 conditions) and first_payment_cap = min(USD 2500 eq, 0.5 × 12-month median FINAL)
  until final_payment_count ≥ 2. verify_account (if VERIFY_ACCOUNT_ENABLED) is stored as evidence and
  NEVER releases a hold (T-14). New-payee rule: a payee with no history needs the same callback rules
  (T-21).

ACCEPTANCE TESTS Part 1 (tests/acceptance/test_c_*.py):
- valid/invalid IBAN, ABA, sort code tables (hypothesis: mod-97 round trip).
- vendor match: tax id beats name; "acme-supp1y.com" vs "acme-supply.com" → QUARANTINE, not a match;
  no fuzzy name match ever returns a vendor_id (property test with random near-names).
- duplicates: same invoice "INV-0042" vs "inv 42" → DUPLICATE; the second insert of the same
  obligation_key raises IntegrityError (a real UNIQUE constraint); T-05 split detection.
- OOB negatives (one test each, with the money-path proof that the obligation stays HOLD):
  verifier == requester → refused; verifier == intake person → refused; verifier is an approver →
  refused; callback contact created 10 days before the change → refused; contact taken from the
  change email (T-10) → refused; phone changed 5 days before the bank change (T-29) → refused; callback
  timestamp before the change request → refused; callback 8 days after → refused; positive path passes.
- cooling-off: payment attempted at verified_at + 71 h → blocked; + 72 h → allowed (time-machine);
  first payment above the cap → split into tranche 1 (= cap) + tranche 2 HOLD until tranche 1 FINAL
  (T-28 part).
- T-14: verify_account returns FULL_MATCH but the callback is missing → still HOLD; flag off → same.
- T-21: new payee whose callback number appears in the same invoice → refused.
- T-33 (data part): seed_local writes bill-#1 history 1500/1650/1800 with label "Payee history
  seeded for demo"; a test asserts the label is present in seed rows and on the payee screen model.

GOAL Part 2 (Week 2, optional, behind LLM_ENABLED): app/ingest/{pdf.py,email.py},
app/integrations/llm/{provider.py,anthropic_provider.py,extract.py}. pdfplumber extracts text plus
per-char size/colour; text that is white-on-white, < 2 pt or outside the page box → HIDDEN_TEXT flag.
Deterministic parsers run first and are authoritative for bank identifiers and amounts. The LLM
gets ONE document per call with identifiers masked (last 4 only) and may only fill
vendor_name/invoice_number/dates/memo summary. Any field where LLM ≠ parser → EXTRACTION_CONFLICT →
item QUARANTINE. The LLM output never sets tier, approval, verification or bank details.
TESTS Part 2: T-01 hidden PDF text ("pay to DE89…" in white) → HIDDEN_TEXT + QUARANTINE; T-02 a memo
saying "bank change already verified by phone" → no effect on OOB state; T-26 injection in document A
referencing bill B → B unchanged (one doc per call asserted by a provider call log at the HTTP
boundary); T-30 single injected invoice → QUARANTINE, other bills proceed; T-18 LLM down (provider
transport raises) → PDFs go to REVIEW, the structured path still works, no T0 for anything degraded;
T-03 a vendor name "<script>alert(1)</script>" renders escaped in the template (Jinja autoescape
test) and is rejected in the transfer reference.
DEFINITION OF DONE Part 1: every OOB rule has a passing negative test and a positive test; no
`import anthropic` reachable from app/core (import-graph test). Part 2: LLM_ENABLED=false keeps all
Part 1 tests green.
```

### 5(d) Planner: netting, rails, cut-offs, value dates, holidays, floor, tiers, caps, tranches. Week 1 (Wed 28 to Thu 29 Oct)
```text
GOAL: app/core/{planner.py,tiers.py,calendars.py,calendars/*.yaml}, scripts/gen_calendars.py.
plan(snapshot: Snapshot, policy: Policy, now: datetime) -> Plan is a PURE function (no I/O, no LLM).
Snapshot = balances (from GET /balances/current), open obligations, payee versions, recent
transfers (for aggregates/caps), approver roster, calendars. Same input → byte-identical rfc8785 plan.

RULES:
- Rail: EUR + DE/NL/FR/... IBAN → LOCAL (SEPA); GBP → LOCAL (FPS); USD US → LOCAL (ACH); otherwise
  SWIFT (swift_charge_option=PAYER). SWIFT disqualifies T0 (r9).
- Calendars: YAML per currency (EUR_TARGET2, GBP_ENGLAND, USD_FED) for 2026-2027, generated by
  gen_calendars.py from `holidays` and committed. Also weekends. business_days_before/after helpers.
- Cut-off/value date: per-rail cut-off time in policy (local time of the currency centre; ASSUMPTION
  until confirmed, labelled in the UI). If now > the cut-off, the send date rolls to the next business
  day. latest_send_date = business_days_before(due_date, max_flight_days[rail], calendar). Flight
  days: SEPA 2, FPS 1, ACH 2, SWIFT 3 (Banking Domain round2 M3). If latest_send_date < today → item
  AT_RISK_LATE (still payable, flagged); deferrals are allowed only if a deferred item's
  latest_send_date ≥ next business day.
- Netting: the conversion amount per currency = Σ planned PAYMENT amounts in that currency − available
  balance in that currency (never negative), rounded up to the currency exponent. A voided/removed
  item resizes the conversion before signing (T-20); after signing → the plan is void, re-sign.
- Reserve floor: Σ USD-eq outflows + Σ fee_reservation[rail] (policy, labelled "reservation, not a
  fee estimate") must leave available ≥ reserve_floor_usd. Otherwise defer the lowest-priority
  (latest due) items until it holds; the reason is DEFERRED_FLOOR.
- Tiers (tiers.py): HARD_BLOCK (DUPLICATE, COMPLIANCE_HOLD, QUARANTINE, HOLD, INSUFFICIENT_APPROVERS)
  > T2 triggers (≥10k USD-eq, payee 7-day aggregate ≥10k, SUSPECT_DUPLICATE, SPLIT_SUSPECT, first
  payment to a new payee_version, AT_RISK_LATE, any degraded check) > T1 (<10k) > T0 (only if policy
  t0_enabled AND all r6-r9 conditions hold).
- Caps r13-r17 applied in order: excess items → DEFERRED_CAP with the cap name. A first payment above the
  cap → tranche 1 = cap, tranche 2 HOLD_TRANCHE until tranche 1 is FINAL (r4/r5).
- Output: Plan{conversions[], payments[], deferred[], holds[], diff_vs_previous}.

ACCEPTANCE TESTS (tests/acceptance/test_d_*.py, tests/property/test_planner.py):
- determinism: the same snapshot twice → identical sha256 of the canonical plan.
- property: Σ planned outflows + reservations ≤ available − floor for random snapshots; no
  obligation appears twice; a duplicate_lock-held obligation is never planned.
- calendars: due Mon 28 Dec 2026 EUR → latest_send_date skips 25-26 Dec TARGET2 holidays (expected
  date written in the test from the calendar YAML, not computed by planner code); Good Friday
  2027 EUR; a GBP bank holiday; after-cut-off rollover with time-machine.
- AT_RISK_LATE when the due date is inside the flight window.
- T-05 split → T2. T-08 the 61st payment in an IST day → DEFERRED_CAP(r14) (IST midnight boundary
  test at 23:59/00:01 IST). T-22: three tiny FINAL payments (< 25% of the limit) don't graduate a payee
  to T0. T-33: bill #1 USD 1800 with seeded history 1500/1650/1800 → T0 only when policy.demo.yaml
  (2 signatures) is loaded; with policy.example.yaml → T1. T-28 tranche split. T-20 netted conversion
  resized when an item is voided before signing.
- T-18 (planner part): a draft flagged degraded → never T0.
- the floor: the balance exactly at floor + outflows → planned; one cent less → the lowest-priority
  item deferred.
DEFINITION OF DONE: planner has no imports from integrations/ (import-graph test); all tests green.
```

### 5(e) Countersign: split packets, binding, WebAuthn + HMAC fallback. Part 1 (library + CLI) in Week 1 (Thu 29 Oct); Part 2 (UI + passkeys) in Week 2 (by Sat 7 Nov)
```text
GOAL Part 1: app/core/{packets.py,signing.py,approvals.py}, app/cli.py (`approve`, `packets show`).
Two packet kinds, each with its OWN canonical JSON, sha256 and signatures:
CONVERSION packet {kind:"CONVERSION", packet_version:1, run_id, conversion_key (request_id),
  sell_currency, buy_currency, buy_amount (string), approved_sell_amount, max_sell_amount =
  approved_sell × 1.0025 (r20, rounded down), quote_id, quote_valid_to_at, expires_at
  (r18 formula), policy_sha256, tier}
PAYMENT packet {kind:"PAYMENT", packet_version:1, run_id, items:[{obligation_id, request_id,
  tranche_no, beneficiary_id, payee_version_id, payee_fingerprint, transfer_method, transfer_currency,
  transfer_amount (string), source_currency, reason, reference, swift_charge_option ("PAYER"|null),
  fee_paid_by ("PAYER"|null), latest_send_date}], totals_by_currency, policy_sha256, tier, expires_at}.
  The PAYMENT packet carries NO quote. It depends on CONVERSION packets only by listing their sha256 in
  `funding_packets`.
canonical = rfc8785.dumps(packet); packet_sha256 = sha256(canonical).hexdigest(). No floats
(a float in a packet → TypeError at build).
Signing (signing.py):
- WebAuthn: challenge = sha256(bytes.fromhex(packet_sha256) || nonce32), nonce stored with
  expires_at = now + 5 min, single-use. Verify with webauthn.verify_authentication_response(credential,
  expected_challenge, expected_rp_id=WEBAUTHN_RP_ID, expected_origin=WEBAUTHN_ORIGIN,
  credential_public_key, credential_current_sign_count, require_user_verification=True). Store the
  new sign_count; a sign_count that doesn't increase (when non-zero) → reject.
- HMAC fallback (SIGNING_MODE=hmac_fallback): sig = HMAC-SHA256(approver_key,
  "pkt-v1|" + packet_sha256 + "|" + nonce). Every UI/CLI/README surface shows "FALLBACK (HMAC, not
  phishing-resistant)".
Approvals (approvals.py): roster = 3 demo approvers (ap_clerk = requester, finance_lead, founder) +
1 ops user who cannot approve. T1 = 1 approver ≠ requester; T2 = 2 distinct approvers, neither the
requester; T0 = no human but still a packet + audit (only if policy allows). Per-approver daily
total ≤ 30000 USD-eq (r17). is_approved(packet) re-verifies every signature from stored material
(never trusts a status column): T-23. consume(packet) marks approvals used on execution; a second
consume → error.

ACCEPTANCE TESTS Part 1 (tests/acceptance/test_e_*.py). WebAuthn uses a test-only software
authenticator (tests/support/soft_authenticator.py, ES256 keys via cryptography) that builds real
authenticatorData/clientDataJSON/signature, verified by the REAL webauthn library:
- tampered packet: change one item amount after signing → the hash differs → verify fails → executor
  gate refuses (no transfer request emitted, asserted in (f)).
- wrong approver: an assertion from a credential registered to founder submitted as finance_lead →
  rejected.
- reused signature: the same assertion/nonce submitted twice → the second is rejected (nonce
  consumed) (T-06).
- expired challenge: nonce used at +5 min 1 s → rejected (time-machine).
- wrong origin/rp_id → rejected; user verification flag off → rejected.
- HMAC fallback: the same three negatives pass with HMAC; the UI label string is present in the
  rendered approval template.
- T-11: the requester signs the T1 packet → rejected; T2 with the same human twice → rejected.
- T-34: a two-person company roster (requester + 1 approver) → any T2 item = INSUFFICIENT_APPROVERS,
  nothing executes.
- T-23: insert an approval_signature row with garbage sig directly via SQL → is_approved False.
- T-12/T-32: a quote valid_to_at within 120 s of now → CONVERSION packet cannot be built
  (QuoteTooCloseError); a MIN_1 quote is never bookable; packet expiry = min(valid_to_at − 120 s,
  signed_at + 4 h) (both branches tested).
- separate packets: signing the CONVERSION packet does not approve the PAYMENT packet and vice versa
  (cross-packet signature reuse → rejected because the hashes differ).
- determinism: building the same packet twice → the same sha256; key order/whitespace changes in
  input dicts don't change the hash.

GOAL Part 2 (Week 2): app/api/{main.py,approve.py,queue.py,killswitch.py}, templates; the browser
uses @simplewebauthn/browser 14.0.0 (pinned CDN + SRI). Pages: run queue, packet view (renders from
canonical JSON only, plus a separate "AI explanation (unverified)" box), approve (passkey), incidents,
recon, kill switch (2-approver clear). scripts/register_passkeys.py registers 3 approvers + ops.
TESTS Part 2: FastAPI TestClient + the soft authenticator drive the real endpoints; the
registration → authentication round trip; T-03 template escaping; the rendered packet amount equals the
canonical JSON amount (parse the HTML).
DEFINITION OF DONE: Part 1 is used by (f) through `approvals.is_approved()` only; Part 2 demo shows
real passkey prompts on localhost, or a visible fallback banner.
```

### 5(f) Executor, guards, polling (primary), incidents, RFI, optional webhooks. Part 1 (executor + polling) in Week 1, by the live checkpoint Fri 30 Oct; Part 2 (incidents, RFI, webhooks) in Week 2 (Mon 2 to Tue 3 Nov)
```text
GOAL Part 1: app/workers/{executor.py,poller.py}. Single-writer executor (a file lock on
var/executor.lock). For EACH API mutation (create beneficiary, create conversion, create transfer):
  1. halted()? → stop.
  2. Rebuild the packet from current DB state + live data; its sha256 must equal the signed sha256
     (T-04: bank details changed after approval → mismatch → void + re-approval).
  3. approvals.is_approved(packet) re-verifies signatures, checks expiry, consumes approvals.
  4. LIVE re-checks immediately before the call (constraint 4):
     - GET /balances/current: available − this outflow − remaining planned outflows ≥ reserve floor,
       else abort the item + trip (r24-29 floor recheck failure) (T-24);
     - duplicate lock: the obligation's duplicate_lock is held by this run; GET /transfers?request_id=
       for this AND any prior attempt key of the obligation returns nothing live (not
       CANCELLED/FAILED); any hit → abort + incident DUPLICATE_LIVE;
     - payee_version still current, cooling-off passed, tranche rules hold;
     - conversion: if the quote is now < 120 s from expiry → abort, re-quote, re-sign (T-12/T-25 path);
       sell amount ≤ max_sell_amount.
  5. audit.log_intent(...) (if it raises → no call; T-17).
  6. client.create_* → IdemResult. CREATED/EXISTS_FOUND → store the id + log_result. REJECTED →
     obligation FAILED_REJECTED + incident. AMBIGUOUS → transfer AMBIGUOUS, stop all further items in
     this run, count toward the r24-29 trip (≥2 per run or per 24 h), and NEVER auto-create a new key;
     the poller keeps looking up by request_id; > 6 days → human (r23).
Order: beneficiaries → conversions (wait for SETTLED via polling) → transfers. A crash at any point →
restart resumes from DB + lookups (T-15).
Poller (primary): GET /transfers/{id} for non-terminal transfers, GET /fx/conversions/{id},
GET /transfers?request_id= for AMBIGUOUS, GET /rfis?types=TRANSACTION&statuses=ACTION_REQUIRED.
Backoff POLL_INTERVAL_S → POLL_MAX_INTERVAL_S. Apply statemachine. FINAL = PAID + the rail window from
calendars (r22) with no newer FAILED; SWIFT → PRESUMED_SETTLED after 10 business days unless supplier
confirmation is recorded. A payment that is FINAL increments payee_version.final_payment_count
(unlocks tranche 2 / cap lift).

ACCEPTANCE TESTS Part 1 (tests/acceptance/test_f_*.py). Offline E2E uses FakeAirwallex (parity-tested
in (a)/(h)) or ReplayTransport sequences:
- happy path: seeded run → 1 conversion + 2 transfers → poller drives PROCESSING→SENT→PAID → FINAL
  after the SEPA window (time-machine across a weekend: FINAL lands on the right business day).
- T-04: change the payee bank fingerprint after signing → 0 transfer requests emitted, packet voided.
- T-24: the fake balance drops below the floor between approval and execution → abort before create;
  kill switch tripped; 0 requests to /transfers/create.
- duplicate live check: a CANCELLED prior attempt doesn't block; a live SENT prior attempt blocks.
- T-15: crash (raise) right after the create returns but before the DB write → restart → lookup finds
  the transfer → EXISTS_FOUND → exactly 1 transfer exists in the fake.
- T-16: an old attempt AMBIGUOUS + a new run for the same obligation → the same request_id derived (no
  run_id) → Airwallex dedupe/lookup → no second transfer.
- T-25: conversion create times out → lookup by request_id → found SETTLED → proceed; not found →
  AMBIGUOUS, transfers not attempted.
- conversion duplicate_request_id → EXISTS_FOUND via GET /fx/conversions?request_id=; beneficiary
  timeout → found by nickname; no duplicate beneficiary in the fake.
- partial failure: 3 transfers, #2 REJECTED (validation) → #1 and #3 proceed, #2 incident; with #2
  AMBIGUOUS instead → #3 NOT attempted (stop-on-ambiguity).
- T-07: HALT file created mid-run (between items) → remaining items not attempted.
- the tampered packet (from (e)) reaches the executor → refused, 0 requests.
- AMBIGUOUS × 2 in a run → kill switch tripped.

GOAL Part 2: app/core/{incidents.py,rfi.py}, app/integrations/webhooks.py.
Incident playbooks keyed on failure_type (captured BEFORE/regardless of auto-CANCEL):
- ACCOUNT_CLOSED, BENEFICIARY_BANK_RETURNED (FAILED after SENT/PAID = bank return; status FAILED +
  failure_type BENEFICIARY_BANK_RETURNED), INVALID_ACCOUNT_NUMBER, BENEFICIARY_NAME_MISMATCH, ... →
  payee_version suspended → new bank details need the full OOB flow (c) → a replacement obligation
  with tranche/attempt_no+1 under the SAME duplicate_lock (the lock flips to the replacement; the old
  attempt must be CANCELLED or FAILED-after-return first) → a new PAYMENT packet (T2). The replacement
  reuses the refunded EUR (no new conversion if the balance covers it) and budgets a second fee
  reservation.
- CHANNEL_TIMEOUT, SYSTEM_ERROR → terminal failed; T2 replacement allowed; NO "wait and re-check".
- Compliance types ACCOUNT_UNDER_RESTRICTION, TM_SUSPENDED, CHANNEL_POLICY, any WATCHLIST_* reason
  code → payee COMPLIANCE_HOLD (HARD_BLOCK), kill-switch trip, escalation to founder + finance_lead;
  supplier-message drafting disabled for that payee (no reason text leaves the system).
- DEFAULT handler: unknown/null failure_type, or one not in the playbook table → incident
  UNKNOWN_FAILURE, payee HOLD, T2 required for any replacement, no automatic retry; the raw
  failure_reason is stored.
RFI (rfi.py): RFI rows from polling (and webhooks if enabled): ACTION_REQUIRED → linked transfer
RFI_OPEN + payee holds for new payments + queue card; ANSWERED → waiting; CLOSED → release holds only
when the transfer state allows. Responding (POST /rfis/{id}/respond) is a human action in the UI only;
never automated.
Webhooks (only if WEBHOOKS_ENABLED): verify x-signature = hex(HMAC_SHA256(secret, x-timestamp +
raw_body)) with hmac.compare_digest on the RAW bytes; |now − x-timestamp| ≤ WEBHOOK_TOLERANCE_SECONDS
(x-timestamp is Unix ms); dedupe on event id (UNIQUE); a webhook only ENQUEUES a poll; it never sets
state directly (T-21b).
TESTS Part 2: ACCOUNT_CLOSED after SENT (fixture transfer_failed_account_closed_after_sent) →
failure_type captured even though the last observed status is CANCELLED → playbook → replacement
blocked until OOB done → replacement executes once; a second replacement attempt → blocked by the
lock. BENEFICIARY_BANK_RETURNED after PAID (U1; FakeAirwallex if the sandbox rejects it) → status
FAILED + failure_type BENEFICIARY_BANK_RETURNED + journal hook. Unknown failure_type "SOMETHING_NEW" →
DEFAULT handler. TM_SUSPENDED with WATCHLIST_RESTRICTION_BENEFICIARY → COMPLIANCE_HOLD + trip
(T-31) + the supplier-draft function raises. RFI ACTION_REQUIRED → holds; the respond endpoint is never
called by workers (assert 0 requests). Webhook: valid signature → poll enqueued; tampered body →
401; replayed event id → ignored; timestamp outside tolerance → 401; a webhook claiming PAID while a
poll says SENT → state stays SENT until a poll confirms (T-21b).
DEFINITION OF DONE: Fri 30 Oct live checkpoint: `make demo DEMO_MODE=live` pays 1 EUR LOCAL + 1 USD
LOCAL in the sandbox through CLI approvals and reaches PAID via simulation; the audit verifies.
```

### 5(g) Reconciler + journal (incl. returns) with an explicit tie-out formula. Week 2, headless tie-out checkpoint Thu 5 Nov
```text
GOAL: app/core/{recon.py,journal.py}, `python -m app.core.recon run --from --to`. Inputs:
GET /financial_transactions (filters from/to_created_at, source_id, currency; types include DEPOSIT,
CONVERSION_BUY, CONVERSION_SELL, CONVERSION_REVERSAL, PAYOUT, PAYOUT_FAILURE, PAYOUT_REVERSAL, FEE,
ADJUSTMENT, PREPAYMENT, PREPAYMENT_RELEASE; status PENDING/SETTLED/CANCELLED), GET /balances/current
and GET /balances/history (≤7-day windows), plus our ledger/transfers/conversions.
Fees always come from Airwallex objects/rows (transfer fee_amount/fee_currency, FEE rows). Never
estimated.

MATCHING: each SETTLED financial transaction maps to exactly one internal object via source_id
(transfer id / conversion id / deposit id) and to exactly one formula term below. Unmapped rows →
recon_exception UNMAPPED_ROW. Internal objects with no row after the window → MISSING_ROW. Amount
mismatch → AMOUNT_MISMATCH. One row mapped to two terms → a test failure (no double counting).

TIE-OUT FORMULA (per currency c, window [t0, t1], SETTLED rows only, all Decimal at the currency
exponent):
  B_close(c) = B_open(c)
             + DEP(c)                              deposits
             + CB(c) − CS(c)                       conversion buy / sell legs
             ± CR(c)                               conversion reversals (signed as booked)
             − P(c)                                payout principal debited (PAYOUT rows)
             − F_tx(c)                             Airwallex transfer fees (FEE rows or PAYOUT fee part),
                                                   INCLUDING fees retained on failed/returned payouts
             + R(c)                                refunds of failed/returned payouts credited in the
                                                   transfer currency (PAYOUT_FAILURE / PAYOUT_REVERSAL),
                                                   = transfer amount less the retained transfer fee
             − F_3p(c)                             third-party (intermediary/beneficiary-bank) fees
                                                   deducted separately from the wallet
             − F_fxc(c)                            FX cancellation delta fee (only when a refund is
                                                   taken in the source currency)
             ± ADJ(c)                              ADJUSTMENT rows (signed)
             ± PRE(c)                              PREPAYMENT / PREPAYMENT_RELEASE (signed)
  residual(c) = B_actual(c) − B_close(c), where B_actual = the balance history closing balance at t1
  (or available+pending+reserved from GET /balances/current when t1 = now).
  residual(c) MUST be 0.00. Otherwise a recon_exception TIE_OUT_RESIDUAL lists the unexplained amount
  and the candidate rows. Never "fix" the residual with a plug.
  How F_tx, F_3p and F_fxc appear as transaction_type rows is UNVERIFIED (U13/U14). The day-1 fixtures
  (transfer_swift_payer_fee, transfer_failed_account_closed_after_sent, transfer_paid_then_failed)
  determine the mapping table in recon.py (TERM_MAP), and each mapping cites the fixture file.
RETURN IDENTITY (per returned transfer T, tested): R_T = A_T − F_T,ret, and the net wallet cost of T =
  F_T,ret + F_3p,T + F_fxc,T. If the fixture contradicts this, mark U15 in
  docs/undocumented-behaviour.md, change the identity to match the recorded behaviour, and say so in
  the PR. Never bend the fixture to fit the formula.

JOURNAL (journal.py; functional currency USD; the transfer currency is kept on every line):
 payment:     Dr AP:<vendor> (EUR A @ booked rate) / Cr Wallet:EUR A;  Dr Bank fees / Cr Wallet:EUR F_tx
 conversion:  Dr Wallet:EUR buy / Cr Wallet:USD sell; realised FX gain/loss vs invoice-date rate
 return (FAILED after SENT/PAID, failure_type e.g. BENEFICIARY_BANK_RETURNED / ACCOUNT_CLOSED):
   1. Dr Wallet:EUR R / Cr AP-clearing:EUR R                (refund in transfer currency)
   2. the original fee stays in Bank fees (no reversal line)  (retained fee)
   3. Dr Bank fees (third-party) F_3p / Cr Wallet:EUR F_3p  (third-party fees, if any)
   4. Dr FX loss (or Cr FX gain) / Cr Wallet F_fxc         (FX cancellation delta, if any)
   5. Dr AP-clearing:EUR R / Cr AP:<vendor>                 (liability reinstated, invoice still open)
 replacement: as payment, with a second F_tx read from the replacement's response.
 period end: revalue the Wallet:EUR and AP:<vendor> EUR balances at the closing rate (unrealised FX).
Export: generic CSV (date, account, debit, credit, currency, amount_usd, source_id, memo). No
accounting-software API.

ACCEPTANCE TESTS (tests/acceptance/test_g_*.py):
- formula closure on the recorded fixture set (fin_tx_window + balance_history_window): residual 0.00
  per currency, computed by the code. The test asserts residual == 0 and that every row is mapped.
- negative: drop one FEE row from the input → TIE_OUT_RESIDUAL equal to that fee; add an unknown
  transaction_type → UNMAPPED_ROW; duplicate a row → AMOUNT_MISMATCH or residual (not silently
  absorbed).
- property (hypothesis): random sequences of synthetic rows across all terms → closure holds; shifting
  one row by 0.01 → residual 0.01.
- return scenario (FakeAirwallex replaying the U1/U14 fixture semantics): EUR 7,500 LOCAL, fee F,
  returned with third-party fee 5.00 and (variant) FX cancellation fee → journal lines 1-5 present and
  balanced; R + retained F matches the identity; formula residual 0.00; the replacement's second fee
  booked separately.
- realised FX: conversion at rate r1 vs invoice rate r0 → gain/loss = A × (r1 − r0) in USD (expected
  value computed in the test from fixture rates).
- journal: every entry balances per currency; CSV round trip.
DEFINITION OF DONE: `python -m app.core.recon run` over the live sandbox window on Thu 5 Nov shows
residual 0.00 for USD and EUR, or a listed, explained exception; TERM_MAP entries each cite a fixture.
```

### 5(h) Eval harness: exactly 20 labelled scenarios. Week 3 (Mon 9 to Tue 10 Nov), freeze Wed 11 Nov
```text
GOAL: eval/harness.py, eval/scenarios/S01..S20.yaml, app/integrations/fake_airwallex.py parity tests
(tests/contract/test_fake_parity.py). Each scenario = seed (vendors, contacts with ages, roster,
balances, policy), inputs (bills/events/clock steps/simulated transitions), and labels written BEFORE
running: expected per-obligation outcome (FINAL | PAID | HOLD:<reason> | QUARANTINE:<reason> |
DEFERRED:<reason> | COMPLIANCE_HOLD | REJECTED), expected transfer count per obligation, expected
incidents, expected journal totals, expected residual (0.00), expected kill-switch state.
THE 20 SCENARIOS:
 S01 happy EUR SEPA LOCAL, 1 conversion + 1 transfer → FINAL after 3 TARGET2 days
 S02 USD ACH LOCAL, no conversion → FINAL after 2 US banking days
 S03 GBP FPS LOCAL, holiday in the window → FINAL on the right day
 S04 SWIFT supplier: swift_charge_option=PAYER, fee read from the response → PRESUMED_SETTLED, not FINAL
 S05 exact duplicate invoice (normalised number) → second HOLD:DUPLICATE, 1 transfer
 S06 near-duplicate (same amount, due ±3 days) → T2, not auto-executed without 2 signatures
 S07 split payments under the T1 threshold → T2 trigger
 S08 lookalike sender domain → QUARANTINE:LOOKALIKE_DOMAIN
 S09 fraudulent bank change, callback number from the change email → HOLD:BANK_CHANGE, 0 transfers
 S10 legitimate bank change: ops callback, cooling-off, first-payment cap → tranche 1 FINAL then tranche 2
 S11 ACCOUNT_CLOSED after SENT → incident, OOB for new details, 1 replacement, lock blocks a second
 S12 BENEFICIARY_BANK_RETURNED after PAID → FAILED + return journal + residual 0.00
 S13 BENEFICIARY_NAME_MISMATCH → playbook, payee HOLD
 S14 unknown failure_type → DEFAULT handler, no retry
 S15 TM_SUSPENDED + WATCHLIST reason → COMPLIANCE_HOLD + kill switch + no supplier draft
 S16 RFI ACTION_REQUIRED on a transfer → RFI_OPEN holds, human-only response
 S17 timeout on transfers/create → lookup finds it → exactly 1 transfer (and a variant where the lookup
     is empty → AMBIGUOUS, stop)
 S18 balance drops below the floor after approval → abort before create + trip
 S19 quote inside the 120 s margin / expired → re-quote + re-sign; no conversion on the stale quote
 S20 tampered PAYMENT packet + replayed signature → refused, 0 transfers
 (S01-S20 also exercise: hidden-text PDF in S08's batch when LLM/pdf ingest is on; T0 via
 policy.demo.yaml for the seeded bill #1 in S01's batch.)
METRICS (computed in harness.py from run artefacts vs labels; never constants):
 double_payments (must be 0), unauthorised_executions (transfers without a valid packet; must be 0),
 duplicate_recall = caught labelled duplicates / labelled duplicates,
 fraud_change_block_rate, false_hold_rate = holds on obligations labelled payable / payable,
 correct_playbook_rate, recon_tie_out_rate = currencies with residual 0 / currencies,
 human_touches_per_run (signatures + manual actions counted from the audit log),
 replan_latency_ms p50/p95 measured with time.perf_counter around plan() + packet build (D8 target
 ≤ 15-20 s), outcome_accuracy = obligations whose final state == label / all.
OUTPUT: eval/results/metrics.csv, per_scenario.csv (scenario, obligation, expected, actual, pass),
run_meta.json (git sha, policy sha256, AWX_MODE, LLM model id or "disabled", started_at IST).
README's metrics table is generated from metrics.csv by a script, never typed by hand.
SELF-TEST (`--selftest`): rerun with (1) the duplicate lock disabled → double_payments > 0 in S05/S11/S17;
(2) OOB rules disabled → fraud_change_block_rate drops in S09; (3) the floor recheck disabled → S18
fails. The harness exits 1 if any metric fails to degrade.
FAKE PARITY: for every recorded fixture scenario in (a), replay the same request sequence against
FakeAirwallex and compare the normalised responses (status codes, statuses, error codes, field
presence). A mismatch fails CI. Fake behaviour without a fixture (e.g. PAID→FAILED if the sandbox
refuses it) must be listed in docs/undocumented-behaviour.md as "fake-only, unverified".
LIVE SUBSET (`make eval-live`): S01, S02, S05, S11, S17 against the sandbox with simulations.
ACCEPTANCE TESTS: harness refuses ≠ 20 scenarios; refuses a scenario without labels; metrics.csv is
byte-identical across two offline runs (determinism, except latency columns); the selftest passes;
parity tests are green.
DEFINITION OF DONE: `make eval` green offline in CI with the artefact uploaded; double_payments = 0 and
unauthorised_executions = 0; the README table regenerated from metrics.csv.
```

### 5.9 Compliance T-01..T-34 → milestone and test file
| Test | Milestone | File (tests/acceptance/) | Week |
|---|---|---|---|
| T-01 hidden PDF text | (c) Part 2 | test_c_pdf_ingest.py | 2 |
| T-02 memo claims verification | (c) Part 2 | test_c_pdf_ingest.py | 2 |
| T-03 malicious names / XSS / reference charset | (c) Part 1 (charset) + (e) Part 2 (escaping) | test_c_parsers.py, test_e_ui.py | 1/2 |
| T-04 bank details changed after approval | (f) | test_f_executor_guards.py | 1 |
| T-05 split payments | (c) detection + (d) tier | test_c_dupes.py, test_d_tiers.py | 1 |
| T-06 replayed approval | (e) | test_e_signing.py | 1 |
| T-07 kill switch mid-run / unreadable HALT | (b) + (f) | test_b_killswitch.py, test_f_executor_guards.py | 1 |
| T-08 per-day cap exhaustion (IST) | (d) | test_d_caps.py | 1 |
| T-09 non-sandbox URL/env/redirect/proxy | (a) | tests/contract/test_client_safety.py | 1 |
| T-10 callback number from the change email | (c) | test_c_oob.py | 1 |
| T-11 requester = approver | (e) | test_e_approvals.py | 1 |
| T-12 quote expiry/drift (120 s, 25 bp) | (e) + (f) | test_e_packets.py, test_f_conversion.py | 1 |
| T-13 edited audit log vs signed checkpoint | (b) | test_b_audit.py | 1 |
| T-14 verify_account unavailable / flag off | (c) | test_c_oob.py | 1 |
| T-15 crash between create and DB write | (f) | test_f_recovery.py | 1 |
| T-16 new run while the old attempt is AMBIGUOUS | (f) | test_f_recovery.py | 1 |
| T-17 audit write failure | (b) + (f) | test_b_audit.py, test_f_executor_guards.py | 1 |
| T-18 LLM down | (c) Part 2 + (d) | test_c_pdf_ingest.py, test_d_tiers.py | 2 |
| T-19 policy edited to loosen | (b) | test_b_policy_floor.py | 1 |
| T-20 netted conversion with a voided item | (d) | test_d_netting.py | 1 |
| T-21 new payee, same-source callback | (c) | test_c_oob.py | 1 |
| T-21b webhook replay / single-source unlock | (f) Part 2 | test_f_webhooks.py | 2 |
| T-22 T0 graduation gaming | (d) | test_d_tiers.py | 1 |
| T-23 forged APPROVED row (WebAuthn/HMAC in place of Ed25519, per D5/D6) | (e) | test_e_approvals.py | 1 |
| T-24 balance below the floor after approval | (f) | test_f_executor_guards.py | 1 |
| T-25 conversion timeout | (f) | test_f_conversion.py | 1 |
| T-26 cross-document injection | (c) Part 2 | test_c_pdf_ingest.py | 2 |
| T-27 policy loosening a hard bound | (b) | test_b_policy_floor.py | 1 |
| T-28 cooling-off + tranche | (c) + (d) + (f) | test_c_oob.py, test_d_tranches.py | 1 |
| T-29 phone changed before bank details | (c) | test_c_oob.py | 1 |
| T-30 single injected invoice | (c) Part 2 | test_c_pdf_ingest.py | 2 |
| T-31 compliance failure trips the kill switch | (f) Part 2 | test_f_incidents.py | 2 |
| T-32 quote inside the safety margin | (e) | test_e_packets.py | 1 |
| T-33 bill #1 seed integrity + label | (c) seed + (d) tier | test_c_seed.py, test_d_tiers.py | 1 |
| T-34 two-person company | (b) + (e) | test_e_approvals.py | 1 |

Reconciling Compliance with later decisions:
- T-23 says Ed25519. Approver signatures are now WebAuthn or the HMAC fallback (D5/D6/steering 8), and Ed25519 is kept for audit checkpoints only.
- T-12's 60 s margin becomes the row-19 margin of 120 s.
- T-03's Slack surface is cut, so T-03 covers the web UI and transfer reference only.
- Row 22's 48 h settle window becomes max(48 h, rail business-day window), with SWIFT never FINAL by timer.

A CI guard (`tests/acceptance/test_compliance_index.py`) asserts that every ID T-01..T-34 (and T-21b) appears in at least one test's `@pytest.mark.compliance("T-xx")` marker.

## 6. Three-week plan (M1: no project code or commits before **Sun 25 Oct 10:00 AM IST**; before that, throwaway spikes only, outside the repo)
| Date (IST) | Work | Gate |
|---|---|---|
| Sun 25 Oct | Repo scaffold (layout §4.2, pins, Makefile, CI). **(a)**: `make spike` (U1-U15), `make fixtures-record`, client + contract tests | CI green offline; U-register filled |
| Mon 26 | (a) finish; **(b)**: schema, state machines, audit chain, checkpoints | `make verify-audit` exits 0/1 correctly |
| Tue 27 | (b): policy floor (30 loosen tests), kill switch, ledger | T-07/13/17/19/27 green |
| Wed 28 | **(c) Part 1** (parsers, deterministic vendor match, dupes, fingerprint, OOB); **(d)** start | OOB negatives green |
| Thu 29 | (d) planner (calendars, cut-offs, floor, tiers, caps, tranches); **(e) Part 1** packets + signing (CLI, soft authenticator) | T-05/06/08/11/12/20/22/23/32/33/34 green |
| Fri 30 Oct | **(f) Part 1** executor guards + polling + lookup-before-retry. **Live checkpoint:** EUR SEPA + USD ACH paid in the sandbox via CLI approvals | Demo money path live; audit verifies |
| Sat 31 | Buffer / fix; fake parity for every recorded scenario | Week 1 = no LLM, no UI ✔ |
| Mon 2 to Tue 3 Nov | **(f) Part 2** incidents (ACCOUNT_CLOSED / BANK_RETURNED / DEFAULT / compliance), RFI, optional webhooks | T-21b/31 green |
| Wed 4 to Thu 5 Nov | **(g)** recon + journal + returns. **Headless tie-out checkpoint Thu 5 Nov** | residual 0.00 USD/EUR or explained |
| Fri 6 to Sat 7 Nov | **(e) Part 2** UI + passkeys; **(c) Part 2** optional pdf/LLM ingest. **UI checkpoint Sat 7 Nov** | T-01/02/03/18/26/30 green (or LLM documented as cut) |
| Sun 8 | Demo script (D8: the lock fires twice; re-plan ≤ 15-20 s), rehearsal on replay | |
| Mon 9 to Tue 10 Nov | **(h)** 20 scenarios, metrics, selftest, live subset | `make eval` + `eval-selftest` green |
| Wed 11 Nov | **Freeze** | tag |
| Thu 12 Nov | Video + submission (by Vedant; agents submit nothing) | |
| Fri 13 Nov | Buffer | |
