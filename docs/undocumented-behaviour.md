# Wiretight — undocumented and unverified behaviour

Every **⚠ unverified** label in the spec, and every §9.5 day-1 check, with a recorded verdict.

Verdict vocabulary is exactly FINAL.md §9.4:

| Verdict | Meaning |
|---|---|
| `CONFIRMED` | The sandbox did what the docs said. |
| `CONTRADICTED` | The docs said X, the sandbox did Y. **State both.** |
| `NOT SUPPORTED IN SANDBOX` | The sandbox refused or does not simulate it. |
| `NOT RUN` | Could not run. A reason is mandatory. |

**Rules.** Never fabricate a fixture or a verdict. Code follows the recorded behaviour, and the
departure is written here and in `DECISIONS.md`. A check stays `NOT RUN` until a real fixture exists.

---

## Status: the U-register is EMPTY because there are no sandbox keys

`.env` does not exist, so `AWX_CLIENT_ID` / `AWX_API_KEY` are absent and **no §9.5 check has been
run**. Every row below is `NOT RUN (no keys)` by §9.1 Plan B, not by choice.

**Unblock:** `NEEDS_HUMAN.md` H1 — business name must be exactly `Sandbox Business` or
`New Business Sandbox` or KYB will not auto-approve and every call 403s.

Each row gains: what was sent (redacted), what came back (status, error code, relevant fields), the
IST timestamp, the account API version, and a link to the redacted fixture in
`tests/fixtures/airwallex/`. `scripts/record_fixtures.py` writes the fixture; `scripts/check_fixtures.py`
refuses hand-edited ones (sha256 per file in `manifest.json`).

---

## §9.5 day-1 check register

| ID | Question | What it decides | Verdict | Fixture |
|---|---|---|---|---|
| S-T1 | Auth + token life (E1) | token cache, refresh at `expires_at − 5 min`, re-login once on 401 `credentials_expired` | `NOT RUN (no keys)` | — |
| S-T2 | Funding via simulated deposit; balance timing (E4, E5, E2) | the USD 25,000 seed; whether balance is available while PENDING | `NOT RUN (no keys)` | — |
| S-T3 / **U1** | Can a transfer go PAID → FAILED (`BENEFICIARY_BANK_RETURNED`)? (E15, E17) | whether "PAID isn't final" is a live beat or fixture-only | `NOT RUN (no keys)` | — |
| S-T4 / **U2** | Is `failure_type`/`failure_reason` still on the auto-CANCELLED object, read at 0 s and 10 s? (E16) | poll interval ≤ 2 s near failure, vs the DEFAULT handler and "reason not returned by sandbox" | `NOT RUN (no keys)` | — |
| S-T5 / **U10** | `verify_account` for SEPA EUR in sandbox (E10) | whether Verification of Payee yields any evidence at all | `NOT RUN (no keys)` | — |
| S-T6 | `beneficiaries/validate` per corridor + one bad IBAN (E7) | `validate_result` values; the "valid ≠ legitimate" label | `NOT RUN (no keys)` | — |
| S-T7 / **U7** | Schema endpoint name: `/beneficiary_api_schemas/generate` vs the guide alias `/beneficiaries/schema` (E6) | which path the client calls | `NOT RUN (no keys)` | — |
| S-T8 / **U4** | Do webhooks fire for simulated transfers/deposits? Are retries re-signed? (E20) | whether webhooks are worth enabling at all (polling is primary) | `NOT RUN (no keys)` | — |
| S-T9 / **U8** | Quote MIN_1 vs HR_4; convert within validity, after MIN_1 expiry (+70 s), and reusing a quote (E12, E13) | that MIN_1 is never bookable (row 19) | `NOT RUN (no keys)` | — |
| S-T10 | `request_id` reuse on transfers: same body, different body, then lookup (E15, E16) | 400 `duplicate_request_id` → EXISTS_FOUND, no replay of the original | `NOT RUN (no keys)` | — |
| S-T11 | Conversion `request_id` reuse; lookup (E13, E14) | the same for `fx/conversions/create` | `NOT RUN (no keys)` | — |
| S-T12 | `financial_transactions` latency and shape per type, polling every 5 s (E18) | whether the tie-out uses rows or the object fallback ("rows pending") | `NOT RUN (no keys)` | — |
| S-T13 | SWIFT fee reality for EUR 100 SWIFT with PAYER (E15, E16, E2) | fees read from responses only, never computed | `NOT RUN (no keys)` | — |
| S-T14 | `GET /transfers?beneficiary_id=&from_created_at=` filters (E16) | the already-paid check and cap counting across runs (R4 J-3) | `NOT RUN (no keys)` | — |
| S-T15 | `balances/history` with currency + time filters and the cursor (E3) | tie-out opening/closing snapshots | `NOT RUN (no keys)` | — |
| **U3** | Is `GET /beneficiaries?nick_name=` exact or substring? (E9) | lookup-before-retry for beneficiaries (no `request_id` on that endpoint) | `NOT RUN (no keys)` | — |
| **U5** | SCA gating on `GET /balances/current` for direct API keys (E2) | whether the floor re-check works at all | `NOT RUN (no keys)` | — |
| **U6** | Account API version, where shown; is it ≥ `2025-06-30`? | startup check `AWX_MIN_ACCOUNT_API_VERSION` | `NOT RUN (no keys)` | — |
| **U9** | Does a deposit created with `status: REJECTED` appear in financial transactions? (E5, E18) | whether the tie-out must handle a rejected deposit row | `NOT RUN (no keys)` | — |
| **U11** | RFI simulation on a non-platform account; does `GET /rfis` link to the transfer? (E19) | whether the RFI hold is demonstrable at all | `NOT RUN (no keys)` | — |
| **U12** | Is `failure.details.reason_codes` real on `TM_SUSPENDED`? (E17, E16) | the `WATCHLIST_*` compliance trip (row 29) | `NOT RUN (no keys)` | — |
| **U13** | How third-party and FX-cancellation fees appear as `transaction_type` rows (E18) | recon `TERM_MAP` entries F_3p, F_fxc | `NOT RUN (no keys)` | — |
| **U14** | Transfer fee inside the PAYOUT row's `fee` field, or a separate FEE row? (E18) | recon `TERM_MAP` entry F_tx | `NOT RUN (no keys)` | — |
| **U15** | Return shape: refund = amount − retained fee; fee netted once or twice? (E17, E18) | the return identity `R_T = A_T − F_T,retained` | `NOT RUN (no keys)` | — |
| **U16** | Does `GET /beneficiaries/{id}` return full account identifiers, or masked only? (E9) | whether the executor can do a full-fingerprint compare, or must fall back to last-4/country (T-04b) | `NOT RUN (no keys)` | — |
| C-1 | Transfer cancel endpoint existence/behaviour — **record only, not used in the design** | nothing; §4.9 is honest that in-flight transfers are not recalled | `NOT RUN (no keys)` | — |
| C-2 | Key scope: does any endpoint return 403? (all) | whether every §7.2 endpoint is reachable with these keys | `NOT RUN (no keys)` | — |
| C-3 | Does an out-of-app beneficiary edit change what E9 returns? (web app + E9) | whether the executor's fingerprint re-check can catch a tampered beneficiary | `NOT RUN (no keys)` | — |
| DA-1 | Does the sandbox accept a **DE · EUR · LOCAL (SEPA)** beneficiary, else NL/FR labelled? (E6, E7, E8) | demo beat B's corridor. Never switch to SWIFT silently. | `NOT RUN (no keys)` | — |
| DA-2 | Are `ACCOUNT_CLOSED` and `BENEFICIARY_BANK_RETURNED` both accepted after SENT on LOCAL EUR, with `failure_reason` text? (E17, E16) | the demo's failure code and its on-screen caption | `NOT RUN (no keys)` | — |
| DA-3 | Does a failed SEPA payout refund in full; does any fee row appear? (E18, E2) | the return journal and the tie-out after the demo's failure | `NOT RUN (no keys)` | — |

---

## Labelled assumptions (not Airwallex facts)

These stay labelled in the UI until a source replaces them. They are not sandbox questions and are
never presented as verified.

| Assumption | Where it is used | Why it is only an assumption |
|---|---|---|
| Per-rail cut-off times (SEPA/FPS/ACH 14:00, SWIFT 12:00) | planner §4.6 `cutoff_local_time` | conservative internal choice; Airwallex publishes no cut-off for these rails |
| UK FPS 3 business days to FINAL | §4.10 settle window | not documented by Airwallex |
| US ACH 2 banking days to FINAL | §4.10 settle window | sourced only from a search snippet |
| SWIFT `PRESUMED_SETTLED` after 10 business days | §4.10 | SWIFT is never FINAL by timer, so this is our own display label |
| Reserve floor USD 8,000 for the demo | §4.15 row 21 | a board default for a small company, not a standard |
| Every §4.15 number | §4.15 | **none of them is an industry standard**; they are board defaults and may only be tightened |
| The whole demo company, people, emails, balances and histories | §8.5 | synthetic fixtures, labelled everywhere they appear |

---

## Fake-only behaviour (must be listed here if the sandbox refuses it)

§10.1 rule 4: any `FakeAirwallex` behaviour the eval relies on that has no recorded fixture is
"fake-only, unverified" and must be listed below.

- *(none yet — the fake does not exist until milestone (a))*

The likeliest candidate is **U1 PAID → FAILED**. If the sandbox refuses the transition, eval scenario
S12 must be labelled fake-only here, and the demo beat B caption keeps the real returned
`failure_type`/`failure_reason` or reads "not returned by sandbox" (§12.3).