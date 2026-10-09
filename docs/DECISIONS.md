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