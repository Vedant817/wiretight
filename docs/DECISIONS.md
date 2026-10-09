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

## D-B11 — Four floor rows needed a reading the spec does not spell out

FINAL.md §4.15 ships values in a column headed "Shipped value (loosest allowed)", which fixes the
*direction* only by inference. Four rows were genuinely ambiguous; each is resolved here and each
has a test asserting the chosen reading, so a later reader sees the decision rather than the guess.

1. **Row 3, callback validity — MAXIMUM 7.** The spec writes "valid ≤ 7 days", so the loosest
   allowed value is 7 and a policy may only *shorten* it. Read as a minimum it would permit a
   90-day window, which would let a stale confirmation release brand-new bank details — exactly the
   attack the lock exists to stop.
2. **Row 11, T1 band — MINIMUM 10,000.** Rows 11 and 12 both constrain `tiers.t2_threshold_usd`.
   Left undecided, lowering and raising it would each be "permitted" by a different row, which makes
   the control unfalsifiable. MINIMUM follows the column header. Consequence worth stating plainly:
   **raising** the threshold is the *tightening* direction, because more items then need two
   sign-offs. A test asserts both directions.
3. **Row 22, settle window — per rail, not one number.** §4.15 says "SEPA 3 TARGET2 days; FPS 3 UK
   days; ACH 2 US days". Those are not uniform. A single minimum of 3 would have rejected the spec's
   own shipped ACH value of 2, which is how the bug was found. The floor is now a per-rail table, and
   SWIFT is required to set `final_by_timer: false` plus a ≥ 10-business-day presumed-settled window.
4. **Row 29 vs row 25 — `rails.flight_business_days` is a MINIMUM.** Row 29 covers "trip on first
   occurrence"; the only rail-keyed knob that behaves like it is flight time, which must never be
   shortened. Row 25's demo-visible value is the SEPA fee *reservation*, a MINIMUM, since reducing it
   would let the planner promise a reserve the wallet does not hold.

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