# Wiretight — build decisions

Append-only. Every entry is `(IST timestamp, what, why, which FINAL.md section it supersedes)`.
The coding agent may change behaviour only through an entry here. It may **never** loosen a §4.15
floor row, any part of the lock (§4.5), the executor sequence (§4.8), or the honesty rules (§10.1).

---

## D-B01 — Build starts Fri 9 Oct 2026; whole calendar shifted back 16 days

- **When:** Fri 9 Oct 2026, 22:35 IST
- **What:** The build starts today instead of Sun 25 Oct 2026 10:00 AM IST. Every date in
  FINAL.md §0.1 and §13.1 moves back exactly 16 days (25 Oct → 9 Oct), preserving the spacing and
  the order of the milestones.
- **Why:** Vedant's explicit instruction when starting the agent, after being shown that today is
  16 days before the spec's sanctioned start. He owns the schedule decision.
- **Supersedes:** §0.2 standing rule "No project code and no repo commits before Sun 25 Oct 2026,
  10:00 AM IST"; §9.2 "Pre-build rule"; the calendar in §0.1 and §13.1; and §11.1 item 11's
  literal development-period sentence.

### Derived calendar (IST)

| Original | Shifted | Milestone |
|---|---|---|
| Sun 25 Oct | **Fri 9 Oct** | Day 1 — scaffold, day-1 spike, (a) client |
| Mon 26 Oct | Sat 10 Oct | (a) finish, (b) schema + state machines + audit chain |
| Tue 27 Oct | Sun 11 Oct | (b) policy floor, kill switch, ledger |
| Wed 28 Oct | Mon 12 Oct | (c1) verify + lock, (d) planner |
| Thu 29 Oct | Tue 13 Oct | (d) tiers/caps/tranches, (e1) packets + signing |
| **Fri 30 Oct** | **Wed 14 Oct** | **Checkpoint 1** — 1 EUR SEPA + 1 USD ACH paid live |
| Sat 31 Oct – Sun 1 Nov | Thu 15 – Fri 16 Oct | Buffer, fake parity, shadow skeleton |
| Mon 2 – Tue 3 Nov | Sat 17 – Sun 18 Oct | (f2) incidents, replacement, RFI, webhooks |
| **Thu 5 Nov** | **Tue 20 Oct** | **Checkpoint 2** — full demo headless with tie-out |
| **Sat 7 Nov** | **Thu 22 Oct** | **Checkpoint 3** — same run through the UI |
| Sun 8 Nov | Fri 23 Oct | Demo script, shot list, live take #1 |
| Mon 9 – Tue 10 Nov | Sat 24 – Sun 25 Oct | (h) eval + self-test, README, live take #2 |
| **Wed 11 Nov** | **Mon 26 Oct** | **Feature freeze**, tag `v1.0-freeze` |
| Thu 12 Nov | Tue 27 Oct | Final take, video, `make package`, Vedant submits |
| Fri 13 Nov | Wed 28 Oct | Buffer only. Hard deadline 11:59 PM IST |

### ⚠ Open consequence — must not be papered over

1. **§11.1 item 11 must not be hardcoded.** FINAL.md asks the README to say *"All project code was
   written from 25 Oct 2026, 10:00 AM IST"*. With this shift that sentence is **false**. The README
   will instead derive the first-commit timestamp from `git log` so it stays true whatever the date.
2. **Hackathon rule risk (FINAL.md OPEN-1/OPEN-4).** The unverified HackerEarth rule *"Your hack must
   be developed entirely during the Hackathon duration"* is unresolved. Code committed today sits
   before the official build phase. This is recorded in `NEEDS_HUMAN.md` for Vedant to resolve
   before submission; it is his call, not the agent's.

---

## D-B02 — `raw/` credential-shaped strings redacted before the first commit

- **When:** Fri 9 Oct 2026, 22:35 IST
- **What:** `docs/spec/raw/doc_failure_types.txt` contained an `x-api-key` and an `x-client-id` from
  Airwallex's own published documentation curl examples (sandbox host). Both were replaced with
  `<REDACTED-AIRWALLEX-PUBLISHED-DOC-EXAMPLE>` before the first commit. No other file in `raw/`
  matched the secret scan.
- **Why:** §10.1 rule 2 and the master prompt's secrets rule. Key-shaped strings must not be
  published even when they are documentation examples, and the pre-commit hook will flag them.
- **Supersedes:** nothing. Preserves the capture's evidentiary value; FINAL.md cites `raw/doc_*.txt`
  for these endpoints and the text is otherwise intact.

---

## D-B03 — Plan B for the day-1 spike (no sandbox keys in `.env`)

- **When:** Fri 9 Oct 2026, 22:35 IST
- **What:** `.env` does not exist, so `AWX_CLIENT_ID` / `AWX_API_KEY` are absent. Per §9.1 Plan B the
  offline part of milestones (a)–(b) proceeds; every §9.5 check is recorded as `NOT RUN (no keys)`.
- **Why:** §9.1 Plan B (R4 S-4). Never fabricate a fixture or a spike verdict.
- **Supersedes:** nothing. Resolves automatically the moment Vedant writes the keys into `.env`.

---

## D-B04 — Two test-authoring corrections in `test_config_separation.py`

FINAL.md §10.1 rule 11: an assertion change needs an entry saying why the old expectation was wrong.
Neither of these changed what the guard *does*; both were wrong test data.

- **a) The `NOT SET` row was not testing what it claimed.** The row intended to assert that a missing
  `AWX_ENV` is refused actually supplied `AWX_ENV: "sandbox"`, so the guard correctly reported
  `AWX_BASE_URL is not set`. Corrected to `{}` plus a separate empty-string row.
- **b) `{**SANDBOX_ENV, "AWX_ENV": ...}` order.** Three rows put the bad `AWX_ENV` *before* the
  `**SANDBOX_ENV` spread, so the spread silently overwrote the bad value with the good one and the
  guard correctly accepted. Reordered so the bad value wins.

**Also a behaviour change, made deliberately:** `check_sandbox_guard` now treats an empty
`AWX_ENV=` / `AWX_BASE_URL=` in `.env` as *not set* rather than falling through to the exact-match
comparison. Both paths refused the process either way; this only makes the error message accurate
("is not set" instead of "expected exactly"). It tightens nothing and loosens nothing.

## D-B07 — Build autonomy granted; the agent decides, the human supplies credentials only

- **When:** Fri 9 Oct 2026
- **What:** Vedant delegated day-to-day build decisions to the agent: architecture choices, naming,
  module boundaries, library selections within the §6.1 pins, scope sequencing, and any judgement
  call the spec leaves open. The agent proceeds without asking.
- **Still human-only** (unchanged, and these are not delegable):
  - writing Airwallex sandbox credentials into `.env`;
  - the four passkey gestures (`make passkeys`) and `make sign-policy`;
  - reading the login-gated HackerEarth rules tab;
  - recording the video and submitting on HackerEarth;
  - any account sign-up, purchase, or contact with an outside party.
- **How to get a second opinion:** the agent may spawn sub-agents to act as reviewers and advisers,
  and may build on their advice. It is not obliged to follow it.
- **Why:** the build is long and mostly unattended. Stopping to ask about a module boundary would
  stall it, and the spec already fixes the parts that are genuinely load-bearing (the lock, the
  policy floor, the executor sequence, the honesty rules).
- **Supersedes:** nothing. It widens how the agent may decide *how* to build; it cannot widen *what*
  the system does. Every deviation from FINAL.md still needs its own entry here.

---

## D-B08 — Endpoint layer, model, and the `awx_status` transition table are built ahead of fixtures

- **When:** Fri 9 Oct 2026
- **What:** Milestone (a) is being built offline per §9.1 Plan B: the client, transport, error classes
  and response models are written against FINAL.md §7.2/§7.3 and marked **⚠ unverified** at every
  point where the sandbox has not yet answered. Contract tests that need a recorded response are
  written as `pending-fixture` and live in `tests/contract`, never in `tests/acceptance`.
- **Why:** §7.2 says explicitly "Nothing here has been called live", and §9.4 requires the code to
  follow the *recorded* behaviour. Writing the client now and rewriting it later wastes the milestone;
  writing it against docs and treating docs as truth would violate §9.4. The compromise is to build
  the structure, isolate every unverified assumption behind a named constant, and make the day-1
  spike able to contradict any of them cheaply.
- **Consequence, recorded so it cannot be forgotten:** every field read off these models carries an
  unverified tag. If the spike contradicts one, the model changes and the affected tests change with
  it — the *test expectations* never move to match a surprising sandbox response without a
  `DECISIONS.md` entry naming the old expectation and why it was wrong (§10.1 rule 11).
- **Supersedes:** nothing.

---

## D-B13 — Red-team review of milestone (b): every P0 finding reproduced and fixed

- **When:** Sat 10 Oct 2026
- **Who:** an independent review agent with no stake in the implementation, asked to find ways a
  floor row could be bypassed, the audit chain could verify OK after tampering, and the kill switch
  could read RUNNING when it should read HALTED. 30 findings; **every P0 was reproduced locally
  before any code changed**, which is recorded here because the fixes below are only trustworthy
  to the extent the reproductions were.

### The floor was porous in ways the tests could not see

The floor checked **one value per row**, while §4.15 names several. A row that names five caps and
bounds one of them reads as covered and is not. Nine values were accepted that should not have been:

| Value | Was accepted | Consequence |
|---|---|---|
| `t0.bank_details_unchanged_days: 0` | yes | a payee whose bank details changed **yesterday** qualified for T0 — auto-pay, no callback, no cooling-off. The single worst finding. |
| `t0.min_payment_fraction_of_limit: "0.00"` | yes | T0 history requirement voided |
| `limits.per_day.max_runs: 999` | yes | §4.15 r14 exists to cap daily runs |
| `limits.per_day.max_new_beneficiaries`, `max_payments` | yes | r14 unbounded |
| `limits.per_run.all_usd`, `max_payments` | yes | r13 unbounded |
| `limits.per_payee_24h.max_t0: 100000` | yes | r16 velocity cap voided |
| `approvals.challenge_ttl_seconds: 31536000` | yes | a sign-off challenge valid for a year |
| `bank_change.contact_provenance_min_invoice_age_days: 0` | yes | §4.5.2's 90-day provenance bar gone; the constant existed in the file and nothing read it |

**Fix.** A row now carries one `Constraint` per value §4.15 names: 30 rows, **51 constraints**. T-27
is parametrised over *constraints*, and each assertion requires the violated **path** to appear in
the error — the old row-level assertion was satisfied by any one of a row's values, which is exactly
how four of them could have been deleted with the suite still green.

### Three more floor holes

1. **`Infinity` and `NaN` defeated every numeric bound.** `Decimal("Infinity")` parses, and
   `Infinity < 10000` is False, so a MINIMUM row accepted it. With
   `tiers.t2_threshold_usd: "Infinity"` no payment ever exceeds the threshold, so **nothing ever
   escalated to T2 and one signature moved any amount**. `-Infinity` did the same to every MAXIMUM
   row. `NaN` was worse than accepted: the comparison sat outside the `try`, so an uncaught
   `decimal.InvalidOperation` escaped `load_policy` as a **crash** — skipping the `policy_load`
   REJECTED row and the kill-switch trip, in place of the documented load error.
2. **`settlement` could omit a rail.** `_check_settlement` iterated only the rails present, so a
   policy containing just `SWIFT` passed and SEPA transfers were left with no return window — i.e.
   `PAID` could become `FINAL` immediately. Fail-open on the row that stops us declaring money
   settled when it is not. All four rails are now required and an unknown rail is refused.
3. **Missing keys were silently defaulted.** `validate_shape` reported unknown keys but no missing
   ones, and `_check_shape_at` skipped absent keys entirely. **Nine of ten deleted keys loaded
   without error**, each falling through to a downstream `.get()` default. A missing key is now an
   error at every level, naming its row.

### Row 11 was inverted, and my earlier reasoning was backwards — see D-B16.

## D-B14 — The kill switch could read RUNNING four different ways

All four reproduced. §4.9's kill switch is the control that is supposed to stop everything, and
every one of these holes ran in the *safe* direction:

1. **`Haltswitch` snapshotted the DB flag at load time.** `guard()` — documented as "called before
   every mutating API call (§4.8 step 1)" — re-read the file but not the database, so an executor
   holding one switch object for a run never saw a trip raised mid-run. The switch now re-reads
   both sources on every call.
2. **`clear()` accepted any caller-supplied `trip_id`** and set `halted = 0` unconditionally.
   Trip A, cleared; trip B raised; `clear(A.id, …)` again → switch reads RUNNING while **trip B is
   still open**. One approver pair could wave through an unresolved incident by replaying an old
   id. Now the id must match the *active* trip.
3. **`clear()` was not atomic.** It wrote `halted = 0` in autocommit before inserting the signature
   rows. A failure midway left `killswitch_state = {halted: 0, …}` with the incident still open —
   and the code comment *invited* a human to delete the now-stale HALT file, which would have
   completed the failure. Now one transaction, verification before any write.
4. **`clear()` verified no signatures.** It counted distinct approver *strings*; two entries with no
   `signature` field and no nonce cleared the switch. §4.9 requires each approver to sign
   `sha256("clear|" + trip_id + "|" + reason)`, and `clear_signature_payload` had **no caller in
   `app/`** — only its own three tests. Signatures are now verified in constant time.

Plus: a `killswitch_state.trip_id` pointing at a deleted row returned an empty `Trip` and left
`halted` alone. A dangling pointer is now treated as **halted** and repaired.

## D-B15 — Checkpoints could be deleted wholesale and the chain still verified

- **Tail truncation.** With seals at 50/100/110, deleting entries 101..110 *and* the 110 seal
  verified **clean**: the surviving seal at 100 pins entry 100's hash, and a chain truncated to 100
  has that same hash. Nothing checked that newer entries had ever existed.
- **Seals overwrote each other.** Files were named `{seq}.checkpoint.json`, so the run-end seal
  silently replaced the interval seal whenever the chain length was already a multiple of 50. The
  seal count was not evidence of anything.
- **A malformed seal crashed instead of failing closed.** `data["body"]` was inside a `try` whose
  `except` did not include `KeyError`. `verify_checkpoints` runs *before the executor starts*, so a
  traceback there looks like "verification did not run" rather than "verification failed".

**Fixes.** A monotone signed **anchor** (`head.anchor.json`) records the highest seq ever sealed and
only ever moves forward; truncation leaves it pointing past the end of the chain. Seal filenames
carry a reason discriminator so interval and run-end seals coexist. Malformed seals are a
verification failure.

**Consequence, recorded because it cut both ways.** Requiring "the newest seal covers the head"
inside the integrity check produced a **false failure every few runs** — an unsealed tail is the
normal mid-run state (entries 101–110 exist, the next interval seal is at 150). Integrity now asks
"is this history what it claims to be"; the separate `head_is_sealed()` asks "was the last run
finished and sealed", and that is what the executor calls before starting. A test asserts the
mid-run state verifies.

## D-B16 — Row 11 was inverted, and my first reading was backwards

**Correction to D-B11 item 2.** I read `tiers.t2_threshold_usd` as a MINIMUM, reasoning that "raising
the threshold sends more items to two sign-offs, which is stricter". **That is wrong.** Raising the
T2 threshold means a USD 400,000 payment no longer *exceeds* it, so it gets T1 — one signature. The
T1 band is a **ceiling** and may only fall. `t2_threshold_usd: "900000000.00"` was accepted, leaving
the one-sign-off band unbounded.

Consequence worth stating plainly, because it is counter-intuitive: for this control **lowering** is
the tightening direction. Lowering to 5,000 sends more items to two sign-offs and is permitted.
`test_a_higher_t2_threshold_is_accepted` encoded the wrong behaviour and is replaced by
`test_a_higher_t2_threshold_is_refused`, with both directions tested (§10.1 rule 11).

## D-B17 — Test-honesty defects that would have let CI stay green

§10.1 makes test honesty non-negotiable, so these matter as much as the production bugs:

- **T-19's "unsigned" test never exercised signature verification.** `load_policy` checks shape →
  floor → signature, so `pytest.raises(PolicyError)` was satisfied by the **floor** rejection.
  **Deleting `verify_signatures` entirely would have left that test green** while its docstring
  claimed to cover signatures.
- **`test_a_missing_required_key_is_a_load_error` passed for the wrong reason.** Its regex was
  `match="missing"`, which matched the pytest **`tmp_path` directory name**, which embeds the test
  name. Run from a neutral directory, the message contained no "missing" at all.
- **T-27's loosen cases masked the unchecked keys** — the mechanism behind the nine unbounded values
  above. A row-level assertion cannot detect a missing constraint; a path-level one can.
- **`test_a_yaml_anchor_is_refused` covered nothing.** Its fixture had a top-level `base:` key that
  `validate_shape` rejects regardless of the merge key.
- **`test_clearing_resumes_nothing` was tautological** — it asserted two counts were zero on a
  fresh database, and its docstring conceded it.
- **Source-text greps presented as behavioural tests**, including one asserting
  `"import anthropic" not in source` on a single file, where §10.3 T-R4a asks for an **import-graph**
  test that a different import spelling or a different file would pass.
- **An autouse fixture inspected `Path("var")` relative to the developer's CWD**, so a stray
  `policy*.yaml` there would fail 30 unrelated tests. Now scoped to `tmp_path` with a `chdir`.
- **A dead `WT_STATES` constant** sat next to a working `awx_status` machine, reading as if the
  overlay existed. It now exists: `wt_next()` implements §4.10's overlay, with `PAID_PROVISIONAL`
  never reaching `FINAL` without the return window, and `FINAL → REOPENED` on a late failure.
- **`failure_reason` first-sight was gated on `current_failure_type`**, so a stored reason could be
  overwritten by a later poll that supplied a type while the type column was still empty. That is
  precisely §4.11 group H's "a bare cancel returns only `failure_reason: 'simulation'`". The two are
  now captured independently.
- **`is_regression` fired on every poll of a terminal transfer**, since re-observing `CANCELLED` was
  treated as a regression. Poll noise; a real anomaly now stands out.

## D-B18 — `tests/acceptance/test_compliance_index.py` now exists, and what it reports

Required by §10.1 by name. The §10.3 index is transcribed into the file rather than imported, so a
row dropped from the implementation cannot shrink the index with it. **7 of 41 ids are implemented**
(T-03, T-07, T-13, T-17, T-19, T-27, T-R4e, plus T-09a/b); the other 34 are declared `PENDING` with
the milestone they belong to, so a failure names the missing work instead of dumping unexplained ids.

Two bookkeeping invariants, both enforced: an id that has a marker must not remain `PENDING`, and an
id with no marker must be `PENDING` — otherwise a skipped test is silently absent rather than
declared. §10.1 rule 8 requires every one of those skips to have a README known-gaps line before the
freeze; `docs/PROGRESS.md` carries the list.

## D-B11 — Four floor rows needed a reading the spec does not spell out

*(Items 1, 3 and 4 stand. Item 2, row 11, was wrong and is corrected in D-B16.)*

FINAL.md §4.15 ships values in a column headed "Shipped value (loosest allowed)", which fixes the
*direction* only by inference. Four rows were genuinely ambiguous; each is resolved here and each
has a test asserting the chosen reading, so a later reader sees the decision rather than the guess.

1. **Row 3, callback validity — MAXIMUM 7.** The spec writes "valid ≤ 7 days", so the loosest
   allowed value is 7 and a policy may only *shorten* it. Read as a minimum it would permit a
   90-day window, which would let a stale confirmation release brand-new bank details — exactly the
   attack the lock exists to stop. Row 3 also bounds
   `contact_provenance_min_invoice_age_days` at 90, which §4.5.2 requires and which nothing
   previously read (D-B13).
2. **Row 11 — see D-B16. My first reading here was backwards and is corrected there.**
3. **Row 22, settle window — per rail, not one number.** §4.15 says "SEPA 3 TARGET2 days; FPS 3 UK
   days; ACH 2 US days". Those are not uniform. A single minimum of 3 would have rejected the spec's
   own shipped ACH value of 2, which is how the bug was found. The floor is now a per-rail table, and
   SWIFT is required to set `final_by_timer: false` plus a ≥ 10-business-day presumed-settled window.
   All four rails must be **present** (D-B13).
4. **Row 29 vs row 25 — `rails.flight_business_days` is a MINIMUM.** Row 29 covers "trip on first
   occurrence"; the only rail-keyed knob that behaves like it is flight time, which must never be
   shortened. Row 25's demo-visible value is the per-rail fee *reservation*, a MINIMUM, since
   reducing it would let the planner promise a reserve the wallet does not hold.

Also recorded: `t0.enabled` must be a **real YAML boolean**. The string `"false"` is truthy, so
`if policy["t0"]["enabled"]` would enable auto-pay from a value that reads as off. Shape validation
now rejects it, and the error names r10 rather than saying only "must be a boolean".

## D-B12 — Structural errors name the floor row they offend

`PATH_TO_ROW` maps a policy path to its row number so a shape error reads
"`t0.enabled` must be a boolean (FINAL.md §4.15 r10)" instead of leaving the operator to guess which
control they had just attempted to loosen. T-27 asserts each refusal names its row, which is what
made this necessary.

## D-B09 — Checkpoints pin a hash, not a position (found by the harder half of T-13)

- **When:** Fri 9 Oct 2026
- **What:** `verify_checkpoints` originally checked each checkpoint's Ed25519 signature and that no
  checkpoint sat ahead of the chain head. It did **not** compare the sealed `entry_hash` against the
  chain's hash at that sequence number.
- **Why it mattered:** that left a real hole in T-13's harder half. An attacker who drops the
  `audit_log` triggers, edits a payload **and recomputes every downstream hash** produces a
  self-consistent chain that `verify()` passes. The signature still covers the *old* hash, so the
  signature check alone passes too. Only the value comparison catches it.
- **Fix:** `verify_checkpoints` now looks up the chain's `entry_hash` at the checkpoint's `seq` and
  requires it to equal the sealed hash. `tests/acceptance/test_b_trust_substrate.py` asserts the
  tampered-but-rehashed chain verifies internally (`verify().ok` is True) and *still* fails
  `verify_checkpoints` — the exact shape of the attack.
- **Lesson recorded deliberately:** a hash chain plus an external signature is not tamper-evident on
  its own. The checkpoint has to bind the value, not just the height.
- **Supersedes:** nothing. Tightens a check; loosens nothing.

## D-B10 — `awx_status` moves PAID → FAILED; the overlay is what stays provisional

- **When:** Fri 9 Oct 2026
- **What:** The test for §8.3's `PAID → FAILED` originally asserted the state stayed `PAID`. The
  implementation moves it to `FAILED`, and that is correct.
- **Why:** `awx_status` mirrors Airwallex and follows documented transitions; §8.3 lists
  `PAID→FAILED` explicitly, because a bank return can arrive after a transfer is paid. What stays
  provisional is the *other* column, our overlay `wt_state`, which is what `PAID_PROVISIONAL` and
  `FINAL` live in. Conflating the two is the mistake the two-column design exists to prevent.
- **Consequence:** recorded here because a reader of the old test could reasonably have thought the
  state machine was suppressing a real return. It is not.
- **Supersedes:** the assertion in `tests/acceptance/test_b_trust_substrate.py::test_paid_to_failed_is_allowed`.

## D-B05 — Real bug found by a test: the socket block was uncatchable

- **When:** Fri 9 Oct 2026, 23:10 IST
- **Symptom:** `tests/unit/test_offline_guarantees.py` failed 5 tests. `SocketBlockedError` *was*
  being raised, but `pytest.raises(SocketBlockedError)` did not catch it.
- **Cause:** with no `tests/__init__.py`, pytest imported the root conftest as top-level module
  `conftest`, while the test imported `tests.conftest`. Two module objects, two distinct
  `SocketBlockedError` classes.
- **Fix:** added `tests/__init__.py` so both resolve to one module.
- **Why it matters:** this was a live hole in the §10.1 rule 9 guarantee. Every future test that
  asserted "no network here" would have failed for the wrong reason, or worse, a test could have
  caught the wrong class and passed without the block ever being verified.
- **Supersedes:** nothing.

## D-B06 — The banned-library scan must not match itself

`test_no_test_module_imports_an_unpinned_http_mock_library` necessarily contains the strings
`import respx` / `import vcr` as data, so it flagged itself. It now skips its own file. Not a
relaxation: `respx` and `vcrpy` remain banned everywhere else, which is checked on every run.