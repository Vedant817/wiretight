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
---

## D-B19 - Concurrency and durability defects, found by measurement

- **When:** Sat 10 Oct 2026, 00:10 IST
- **Method:** two independent audits, one a database/concurrency review, one an adversarial
  edge-case hunt. Every finding was **reproduced with a throwaway script before any code
  changed**. A finding that could not be reproduced is recorded below as ruled out, not as
  fixed.
- **Supersedes:** nothing. This tightens, and never loosens, any 4.5 lock, 4.8 ordering,
  4.15 floor row or 10.1 honesty rule.

### 10.1 rule 11 - measurements added

Two numbers in this entry are claims about our own performance and are recorded as
measurements taken on one Windows machine, not as properties of the system in production:

| Measurement | Value | Conditions |
|---|---|---|
| Durable commits/sec | ~1,100-2,200 | `synchronous=FULL`, WAL, 1 KiB records |
| `verify()` over 1M entries | 13.26 s, ~0.51 GB RSS | single-threaded, materialises all rows |
| `count(*)` on 1M-row `audit_log` | 0.173 s | was on the hot path of every append |
| Write lock held across a 2.0 s call | 4 writers stalled 1.8-2.0 s each | the 4.8 hazard, demonstrated |
| Ledger half-postings | 2 of 8 trials, unbalanced by 10.00 | 8 threads x 20 postings |

None of these is a benchmark of the finished product. They are the numbers that justified
specific design choices, and they are reproducible from `tests/unit/test_b_concurrency.py`.

### Ruled out, not fixed

Two claims from the audits did not survive checking and are recorded so nobody 'fixes' them
later or believes them in a writeup:

- **"ZWSP splits the duplicate key."** False. `\s` does not match U+200B, but the invoice
  normaliser's `re.sub` character class did strip it. The genuine bypass characters are
  U+FEFF, U+00AD, U+2060, U+200D, U+202E and the combining marks, which are category Cf/Mn
  and were not stripped. Verified by codepoint, after a first test run was itself corrupted by
  PowerShell encoding and gave the wrong answer.
- **"`0V042` and `V42` collide."** False for the stated case, but a real widening exists:
  `lstrip("0")` now applies only to a wholly numeric invoice, so `000000042` and `42`
  still agree while an alpha-prefixed vendor code is preserved.

## D-B20 - Control defects: the lock, the floor and the money type

- **When:** Sat 10 Oct 2026, 00:10 IST
- **Supersedes:** nothing, except as noted below.

### The duplicate lock was one invisible character wide

`(vendor_id, normalised invoice no.)` is 4.3's duplicate-detection strategy and `DUPLICATE`
is a HARD_BLOCK. Verified by codepoint: `INV-2291` and `INV-2291` + U+FEFF produce two
different `obligation_key` values and both take the PRIMARY KEY row. The same characters
split the bank fingerprint of an unchanged account, producing `HOLD: BANK_CHANGE` and a 72-hour
cooling-off on a supplier whose bank did not move - the exact false positive that
4.14.5's `bank_change_flag_precision` measures. U+202E additionally reversed what a human
reads in the queue while the key stayed the same string. Fixed by `app/core/text_normalisation.py`,
which strips category Cf/Cc/Zl/Zp/Mn/Mc. It deliberately does **not** fold homoglyphs: Cyrillic
U+0430 is a real letter in a real supplier name, and merging two different suppliers silently is
worse than reporting a near-miss. That belongs in vendor matching, where a human can see it.

### `extra` could shadow the account being fingerprinted

`PayeeDetails.extra` was expanded into the fingerprint's identifiers dict **after** the real
account, so `extra={"account": ...}` made two different bank accounts hash identically. 4.3's
core claim - a different fingerprint always produces a PayeeChangeRequest - was therefore
falsifiable by an attacker-controlled corridor field, and a real bank change would never have
fired the lock. Reserved keys are now refused, and `extra` is a read-only mapping because
`frozen=True` never protected a mutable dict field.

### The floor's T0 row consulted only the type

`_check_exact` checked `isinstance(value, bool)` and never read `constraint.value`. So
`t0.enabled: true` passed a row whose shipped value is `False`, and the only remaining barrier
to live auto-payout was the signature file - which `load_policy(..., allow_unsigned=True)`
skips. 4.15 r10 makes T0 legal *only* under a two-signature policy, which is not expressible as
a plain bound because the floor cannot see signatures. The violation is therefore marked
signature-gated and resolved by `load_policy` after verification. `policy.demo.yaml` still
loads when signed; it no longer loads unsigned, which is the point.

**This is a 10.1 rule 11 entry:** a previously-passing assertion (`t0.enabled: true` satisfies
the floor) was **wrong**, and the fix makes the test suite assert the correct behaviour.

### r22's conjunction

4.15 r22 reads ">= 48 h **and** >= the rail's business-day window". The two were checked
independently, so a policy could set `business_days: 30` beside `min_hours: 48` while
`min_hours` - the number the poller actually consults - stayed at two days. Now checked where
both values are visible. It is deliberately **not** a `Constraint`: T-27 parametrises one value
at a time, and a conjunctive check cannot be expressed that way. A first attempt that did
express it as an hour bound rejected the spec's own shipped policy, because 48 h is legitimately
less than three banking days; that attempt was reverted and is recorded here so it is not
retried.

### Money

- The ISO 4217 table had 12 entries; 22 currencies inherited exponent 2. KRW 1,000,000 became
  `"1000000.00"`, a **100x overstatement** carried into every cap comparison, ledger leg and
  tie-out term. An unlisted code is now refused rather than guessed, because the default of 2
  is not a safe default in either direction for a zero-decimal currency.
- `MONEY` rows accepted negative limits. Only the reserve row had a guard. A negative
  `first_payment_cap_usd` makes tranche 1 a negative payment; a negative
  `per_approver_day_usd` stops row 17 binding at all.
- `parse_amount` placed its quantise call outside the `try`, so a 27-digit amount escaped as
  an uncaught `decimal.InvalidOperation` - an `ArithmeticError`, not a `ValueError`. At
  JPY's exponent of 0 the same amount **succeeded**, rounding 1e27 to a completely different
  number, because the fractional part simply disappeared.

### One trailing space

`playbook_for("ACCOUNT_UNDER_RESTRICTION ")` returned `H`, not `F`. 4.15 r29 says any
compliance failure trips the kill switch **on first occurrence**; `H` is "escalate, never
auto-retry", so the run continues. 4.16's "unknown failure_type -> DEFAULT" makes `H` sound
safe, and it is not safe for the one group where the spec's answer is "stop". Lookup now
normalises case and whitespace first, so a near-miss still reaches its real playbook and a
genuinely unknown type still reaches `H`.

## D-B21 - Concurrency and durability: what measurement found

- **When:** Sat 10 Oct 2026, 00:10 IST
- **Why one entry:** these are the defects found by the concurrency audit, plus one introduced by
  the D-B19 fix itself.

### `Database.transaction()` held no transaction at all

My own D-B19 rewrite. The wrapper did `transaction(conn).__enter__()` and discarded the
generator context manager; CPython finalised it immediately, throwing `GeneratorExit` into the
`yield`, which ran `ROLLBACK` **before the caller's block started**. Two failures, both
silent because the writes succeeded: `conn.in_transaction` was `False` for the whole body, so
the 4.8 guard could never fire; and an exception mid-block left every row committed, since each
statement autocommitted with no transaction to roll back. Verified before fixing: 2 rows survived
an abort that should have removed both.

### A halt with no record of it

`killswitch.trip` committed `halted=1` and the trip row, then called `audit.log_intent` in
its own transaction. Forcing that append to fail left the switch engaged and durable, with a
reason, and **zero** rows in the append-only log - and `audit.verify()` reported
`ok=True, checked=0`. 14(b) requires the log before the act; that held for transfers and not for
the kill switch. Now one transaction, so the trip row, the state update and the audit entry
commit or roll back together.

Concurrent trips compounded it: four calls produced six `trip` rows and six ids, of which five
could never be cleared, because `clear()` refuses any id that is not the active trip. An
operator who tripped, read the id and cleared it was stuck in HALTED with no in-band way out. This
is reachable from **one operator**, by two rapid clicks.

### The anchor was decorative

The head anchor is the one artefact that survives an attacker deleting every seal, and it is the
only signed file in the system whose signature was never verified - `read_anchor` parsed
`data["signature"]` and discarded it. Reproduced end to end: a 200-entry chain truncated to 150,
with the seals above 150 deleted and the anchor forged, produced
`verify_checkpoints -> ok=True, checked=150`, `head_is_sealed -> ok=True` and a clean chain.
Fifty INTENT/RESULT records - the log-before-act evidence that money was about to move - were
deleted with every check green.

Compounding it, the corrupt-anchor branch set `highest = seq`, which is precisely the rollback
the docstring claims cannot happen. A damaged anchor now raises `AnchorCorruptError`: it is the
only record of how far the chain reached, so rebuilding it from what is left is the one response
guaranteed to destroy the evidence.

### Torn writes read as tampering

Checkpoints and the anchor were written with `Path.write_text` - open, write, close. Power loss
between write and flush leaves a truncated file, and for the anchor a truncated file is
indistinguishable from an attacker editing it: `verify_checkpoints` reports failure and the
executor halts. Now temp file, `fsync`, `os.replace`, `fsync` the directory.

### A false halt

SQLite reports `SQLITE_BUSY_SNAPSHOT` with the same message as ordinary contention. It means the
connection holds a read snapshot that cannot be upgraded; waiting cannot fix it, so the retry loop
burned its whole budget and then reported `DatabaseBusyError` - which 4.16 turns into a halt.
Reachable from any code that writes inside a lazy read cursor, which includes
`ledger.balances` and `audit.verify`. Now recognised by extended code and raised as
`StaleSnapshotError`, which is not retryable.

### Half-postings

`ledger.post` read `MAX(line_no)` and inserted each leg as a separate autocommitted statement.
Two concurrent postings read the same head, the loser collided on the second leg, and the first
leg stayed committed. 2 of 8 trials of 8 threads x 20 postings left the ledger **unbalanced by
10.00**, with an orphaned debit that reads as money leaving the business. Now one transaction;
re-measured 8/8 trials balanced with all 320 legs committed.

### The migration lock wedged every database on the machine

One fixed filename in the system temp directory, created `O_EXCL` and removed only in the
creating process's `finally`. A `kill -9` between `os.open` and `unlink` left it forever,
and because the name was fixed it blocked **every unrelated database** for the full 30 s timeout
before failing. Now keyed by the resolved database path, with a stale-holder reclaim.

### 4.8 made checkable

Holding the single write lock across an HTTP call serialises every other writer behind that call's
latency: measured, four concurrent writers stalled 1.8-2.0 s behind a 2.0 s call, and the configured
timeout is 20 s. `db.assert_no_write_lock(conn, doing=...)` now refuses the call, so 4.8 is an
assertion rather than an intention. It is called immediately before every outbound request.

### Also

- `maybe_write_checkpoint` ran `SELECT count(*) FROM audit_log` on **every append**: 0.173 s at
  1M rows, a 173-second stall per write. Now reads the head seq (0.05 ms).
- `account_prefix_totals` concatenated its prefix into a `LIKE` pattern with no `ESCAPE`, so
  `AP_clearing` matched `APXclearing` and `%` matched the whole ledger. A single underscore
  typo in an account family silently doubled the reconciliation population and the tie-out still
  produced a number - a wrong one, with no error.
- `Leg` accepted any currency string. A posting in a currency absent from the table balanced
  inside a bucket no reconciliation reads, so a USD-scoped tie-out reported a perfect residual
  while money had left the ledger's line of sight.
- `tzdata` was not a dependency. `ZoneInfo("Asia/Kolkata")` raised on Windows and in slim
  containers, so the IST daily caps would have crashed on day one. Added and pinned.

## D-B22 - Gaps recorded honestly, not yet built

Found by the same audits. None is fixed because each needs a module that does not exist yet. Each
is a place a reviewer should look first.

1. **The lock has no cross-row invariant.** `change_request_next(current, event)` takes no
   `vendor_id`, so it cannot see a second change request for the same supplier. Two requests can
   both sit in `COOLING_OFF` and both reach `APPROVED`, and 4.5.1's "the old version becomes
   `SUPERSEDED`" has no defined answer for which wins. The machine is correct per-request and the
   property that matters is cross-request. This belongs in `oob.py`, which is the next module.
2. **No cap counter is atomic.** `payee_version.final_payment_count` and `counters` have no code
   and no CAS. A read-modify-write lost 83% of its increments under 8 threads. The counter that
   lifts the first-payment cap must move by `UPDATE ... RETURNING` with a rowcount check, and a
   zero-row result must re-read and re-decide rather than proceed.
3. **No retention policy.** `audit_log` is deliberately un-prunable (T-13), so the answer is
   archival, not deletion: `VACUUM INTO` a verified snapshot and carry the sealed anchor forward.
   `transfer_observation` grows one row per poll with no cap; it needs the first and last sighting
   plus every *change*, not every poll.
4. **`verify()` is O(n) and materialises every row.** 13.26 s and ~0.51 GB at 1M entries, single
   threaded, before the executor does anything. It needs to verify from the last sealed anchor.
5. **No `var/executor.lock` exists.** The single-writer guarantee the whole design rests on is
   currently enforced by nothing, and two `make worker` invocations would both write money state.
6. **No `audit_log(kind, at)` index**, so every incident timeline is a full scan.
7. **Unknown events to a state machine are silent no-ops** rather than errors. Fail-closed, but a
   typo leaves a change request in `PENDING_CALLBACK` forever with nothing logged.

---

## D-B23 - Three requirements named in the spec that were not built

- **When:** Sat 10 Oct 2026, 01:38 IST
- **Background:** reading §14 back against the tree found three items that the
  spec names and that I had reported as complete. One of them was a claim made for
  a milestone marked done.

### 1. `tests/property/` was empty (14 b)

§14(b) lists three properties as acceptance for the trust substrate - no regression
past terminal, `failure_type` never nulled, ledger sums to zero - and
`tests/property` was an empty directory. Written in
`tests/property/test_trust_substrate.py` as Hypothesis properties rather than
examples, because the claim is that *no* input violates the rule.

Two things came out of the first run, and both are the point:

- **A real defect.** `failure_type: ""` was stored verbatim, so the column held
  a third value between NULL and a real type: truthy to `is not None`, yet
  `playbook_for("")` reports an unknown type. A code path reading the column
  concluded a failure *was* recorded. Blank and whitespace-only are now `None`
  (§4.11's "never nulled" only means anything if absent is one state).
- **An assertion of mine was backwards.** I had asserted that a terminal
  `awx_status` makes `is_regression` false. Observing `FAILED` after
  `CANCELLED` **is** a backwards move and the code correctly flags it while
  still holding the state. The state and the flag are separate claims; they are now
  tested separately. **This is a §10.1 rule 11 entry: a previously-passing
  assertion was wrong.**

A third lesson is recorded in `money_at`: amounts must be drawn at the currency's
own exponent. Drawing every currency at two decimal places produced an
`UnbalancedError` - in the test, not the code. UGX has no minor unit, so four legs
of `0.01` each quantize to `0` while their sum quantizes to `1`.

### 2. `make verify-audit` had no command to run

§14(b) makes *"`make verify-audit` 0/1 behaviour"* the Done clause, and the
Makefile already called `python -m app.cli`. That module did not exist, so the
Done clause was unreachable. Written as `app/cli.py` with three exit codes:

- `0` - verified;
- `1` - verification **failed**. Must never be `0`;
- `2` - could not run: no database, no key, unparseable key.

`2` is deliberate and is not a convenience. A CI job that cannot reach the
database has a different cause from a job that proved the chain was edited, and the
Makefile's live targets use it to refuse to run without `CONFIRM_LIVE=1`.
Related: an unknown public key is **refused**, not treated as an all-forged chain,
because reporting every checkpoint as tampered when the real problem is a
configuration typo is a false alarm that trains an operator to ignore the alarm.

### 3. The lock had no cross-row invariant (14 c1)

§4.5.1 defines the change-request states, and §8.4 implements them as
`change_request_next(current, event)` - a pure two-argument function with no
`vendor_id`. It therefore cannot see a second change request, and the property that
matters had **no implementation anywhere**:

> at most one change request per supplier is ever in a lock-bearing state.

Measured before the fix: two concurrent requests for one supplier could both sit in
`COOLING_OFF` and both reach `APPROVED`, and §4.5.1's "the old version becomes
`SUPERSEDED`" had no defined answer for which one won. The first to be approved
would have won by accident, with no record that the second was ever a real request.

The fix is a **partial UNIQUE index** over the non-terminal statuses, and that
choice is the substance of this entry. A `UNIQUE(vendor_id)` would be wrong: a
supplier whose November request was rejected must be able to file again in January,
because §4.4 makes a re-request within 30 days force tier 2, and that only works if
the history stays queryable. So the constraint is on *active* rows only, the
database refuses the second concurrent request, and the application does not have to
remember to check.

**Two design notes worth stating, both recorded so they are not lost:**

1. The integrity check can find a violation but not create one. A database migrated
   from before the index could already hold two active requests, so
   `assert_lock_integrity` exists for exactly that and **fails loudly** - a silent
   violation of the product's central claim is worse than a refused start.
2. The lock's guarantee must live in the database, not a process. A lock held in
   Python would pass every single-threaded test and fail at the moment two
   processes exist, which is the deployment §5.3 actually describes. The test proves
   this by opening a *second* database object post-"restart" and asserting it is
   refused.

### Also

`.github/workflows/ci.yml` per §6.6: offline job with no secrets; the live job
behind `workflow_dispatch` and a protected environment, so a push can never spend
sandbox money on its own. Every step of the offline job runs without a credential,
which is the point - the whole trust substrate is testable offline because
`tests/conftest.py` blocks sockets. A build that needs a sandbox key to prove the
ledger balances cannot be trusted in CI.

## D-B24 - Progress table said "not started" for work that was done

The milestone table in `docs/PROGRESS.md` marked milestone (b) *not started* while
its six modules were committed and its gates were green. That is a reporting
inaccuracy rather than a code defect, but it is the kind that makes every other
number in the file suspect, and it hid the three missing §14 items above. The table
now reflects the tree. **Not a §10.1 rule 11 entry**: no assertion about the
system's behaviour was wrong, only a line in a log I wrote.

---

## D-B25 - Vendor matching and duplicate detection: findings from building them

- **When:** Sat 10 Oct 2026, 02:36 IST
- **Background:** closing gaps 2 and 3 of the (c1) milestone. Four defects were found
  while building them, **all in my own work**, and one is a genuine gap in the spec
  that should not be worked around.

### 1. A lookalike check that flagged legitimate suppliers

The first version quarantined a known domain appearing as a *suffix*, which caught
`mail.acme.com` - an ordinary supplier subdomain. The dot boundary is what separates
a real subdomain from a domain takeover, and the first version had it backwards. It
would have quarantined ordinary suppliers on their ordinary mail servers.

The corrected rule: a domain **appended** after a known one (`acme.com.evil.example`)
or **prepended** without a dot boundary (`notacme.com`) is an attack; a proper
subdomain is not. `notacme.com` is not within edit distance 2 of `acme.com` either,
so distance alone would have missed it entirely.

### 2. A bounded distance that lied

`edit_distance` returned `MAX + 1` to mean "at least three", conflating that with
"exactly three". Every caller compared `<= MAX`, so the conflation was invisible -
until someone asked for the true value. Reverted; the fast path is now
`within_distance()`, which returns a boolean and therefore has no sentinel to
misread.

### 3. Two of my own test expectations were wrong

I asserted `acrne.com` was one edit from `acme.com` and `acme.con` was two. Both
are the other way round. The code was right; I had not counted the positions. Caught
because I checked the arithmetic rather than assuming the test was the source of
truth.

### 4. An intermittent failure that passed in isolation

`test_a_balanced_posting_leaves_the_ledger_at_zero` hardcoded run id `'r'` while
the drawn `run_id` differed, so the foreign key on `journal_line.run_id` failed.
It appeared only in a full-suite run, because Hypothesis's example depends on the
database file name, which depends on a counter that advances with the other tests in
the same module - so the failure needed the counter and the example to line up. Five
passing runs in a row preceded two failures, which is what made it findable.

Diagnosed to the line and fixed, and there are three consecutive green full-suite runs
since. **Recorded because "it passes when I run it" is not evidence.**

### 5. A spec gap, named and not worked around

§4.3 says "known sender domain **exact**". A supplier whose bills arrive from
`billing.acme.com` therefore never resolves and always needs a human. That is not a
bug in the matcher, and the fix is a schema change - record domains per *sender* in
the vendor contact table rather than one domain per vendor - which this milestone does
not attempt. It is recorded here so it is a known gap rather than a silent one.

---

## D-B26 - Atomic counters, and the unknown-event guard

- **When:** 10/10/2026 02:50:50.ToUniversalTime().AddHours(5.5).ToString('ddd d MMM yyyy, HH:mm') IST
- **Supersedes:** nothing. Both tighten.

### Atomic counters (audit gap 2)

`counters` and `payee_version.final_payment_count` had no code at all. Measured
first: 6 threads x 40 read-then-increment, with no transaction and no CAS, stored
**40 of 240** - a 83% loss with **zero errors**. The counter governs when the
first-payment cap lifts, so the cap lifted early.

`app/core/counters.py` serialises inside SQLite's write lock, and the rowcount of
the conditional `UPDATE` answers "did I win". A zero rowcount raises
`CounterLostUpdateError`, because a caller that believes it won when it lost has the
same defect under a different name.

The condition `WHERE status = 'ACTIVE_CAPPED'` is as load-bearing as the atomicity:
an unconditional increment would count a payment against a superseded payee, and
4.4's "3 FINAL payments to the same unchanged beneficiary" would be satisfiable
across two different sets of details.

**One defect in my own implementation, and it is the reason the module exists.** The
first version wrote the arithmetic in SQL as `CAST(value AS REAL)`, which forces the
value through IEEE-754 binary floating point: ten increments of 0.01 sum to
**0.099999999999999992**. Measured, not theorised. It is the exact class of bug
FINAL.md 7.3 bans floats to prevent, reintroduced inside the one module whose whole
job is counting money exactly. The arithmetic now happens in Python, in `Decimal`.

### Unknown events now raise (audit gap 7)

`change_request_next` returned the current state for an event it did not know,
which is fail-*silent*. A typo at a call site - `callback:confirmed` instead of
`CALLBACK:CONFIRMED` - would strand a request in `PENDING_CALLBACK` forever with
nothing logged, and the supplier could not be paid.

An unknown event now raises `UnknownEventError`. A known event that does not apply
in the current state still returns the current state, which is the correct behaviour
for "not yet" and is why this is not simply "raise on any non-transition".

All 710 tests pass unchanged, so no call site relied on the silent no-op.

---

## D-B27 - The executor's single-writer lock, and a liveness probe that killed processes

- **When:** Sat 10 Oct 2026, 12:35 IST
- **Supersedes:** nothing. §5.3's requirement was unimplemented; this implements it.

### The lock

`db.lock_path()` existed and was called from nowhere, so two `make worker`
invocations both wrote money state. `app/core/singlewriter.py` implements it:
a lock file, the holder's pid inside it, and a reclaim for the case that matters more
than the lock itself - a `kill -9` between creating and removing the file.
Without a reclaim the executor is dead forever with no in-band way out, the same
failure shape as the kill switch's unclearable trip in D-B21.

A lock whose pid is gone, or whose age exceeds the timeout, is reclaimed. The age
check is a deliberate backstop rather than an optimisation: a pid on this machine is
answerable, one across a container or a pid namespace is not, and a lock held that
long has almost certainly died anyway.

### Consequential defect in my own implementation

`_pid_alive` used `os.kill(pid, 0)`, the idiomatic POSIX liveness probe. On
Windows CPython **ignores the signal argument** and calls `TerminateProcess`, so
`os.kill(pid, 0)` **terminates the process if it exists**. Measured: calling it on
the test process's own pid killed the run instantly, the shell produced no output at
all, and the file it was asked to write was never created - which looked like a hang
and was actually a kill.

It is not a hypothetical hazard in production either. The function is not called on
the executor's own pid, so it would not have killed itself - it would have killed
**another live executor** the first time a stale-lock check ran against one. A module
whose entire purpose is to prevent two processes writing money state would have
destroyed one of them.

The Windows branch now asks through `OpenProcess` with
`PROCESS_QUERY_LIMITED_INFORMATION`, which looks without signalling. The POSIX
branch keeps the probe, where it is correct. Both are tested, including a test whose
only assertion is that the process survives the check.

**A note on the debugging**, because it cost time and the reason is worth recording:
the first symptom was silence. Three commands in a row returned nothing at all, which
reads as a harness fault. It was not - the process was being terminated before it
could write its output file. A tool that returns no output is not the same as a tool
that is fine.

### Also fixed while here

`executor_lock` accepted a `stale_after_s` argument it never used. Removed, and
the docstring now says that reclaiming is the caller's job, so there is no question
about whose timeout applies.
# Production correction — 14 November 2026: stale holder and cooling configuration

The overnight production audit found D-B27's age-based reclamation unsafe: a
live executor becomes reclaimable after an hour, allowing a second money writer.
Age no longer authorizes eviction. A malformed lock is also preserved because a
peer can be between file creation and writing its PID. Windows OpenProcess now
uses last-error capture: ERROR_INVALID_PARAMETER (87) proves no such PID; other
errors preserve the lock. CloseHandle has explicit pointer-width argument types.
The three old tests encoded unsafe or incorrect expectations (reclaiming a live
old holder, reclaiming a partially written file, and treating a provably absent
PID as alive); they were corrected with these reasons, not weakened for a pass.
These are bounded repairs: file/PID reclaim still needs an OS-backed locking
design to eliminate reclaim races before a production executor can rely on it.

Cooling configuration now accepts integer hours at least 72, based on the later
of callback and request. It cannot silently shorten the window. Seven new tests
cover tightening and malformed/reduced values. The user explicitly forbids demo
shortcuts in the product path; historical media remain untouched.
