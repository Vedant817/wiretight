# Production hardening: the failures other implementations miss

**Status:** honest record of what was measured, fixed, and deliberately left open.
**Rule:** every number here was produced by running code in this repo. Nothing is estimated,
extrapolated, or remembered from documentation. Anything not measured says so.

FINAL.md is a locked specification. Nothing in this document loosens it. Every control below is
a control the spec already requires; what changed is that each one was *tested against the way it
actually fails*, and several turned out not to work at all.

---

## 1. The single-writer design is correct, and here is its exact price

One SQLite file in WAL mode gives one writer and many readers. That is not a limitation to be
apologised for; it is the property that makes a payment system auditable. What matters is
knowing what it costs.

| Measurement | Value | Conditions |
|---|---|---|
| Durable commits | **~1,100–2,200/sec** | `synchronous=FULL`, WAL |
| Throughput vs. thread count | **flat** | adding threads adds latency (max 854 ms at 8), never throughput |
| 1 thread vs. 8 threads | identical rate | WAL serialises writers; that is the design |
| Write lock held across a 2.0 s HTTP call | **4 concurrent writers stalled 1.8–2.0 s each** | the §4.8 hazard, demonstrated |
| The same call with the configured 20 s timeout | 20-second system-wide stall | one misplaced `with` block |

That last row is the one that shapes the architecture. Because there is exactly one writer,
**a transaction held across a network call serialises the entire system behind that call's
latency.** So §4.8's ordering rule is not a style preference, it is the difference between a
responsive service and a self-inflicted outage. It is now enforced by
`db.assert_no_write_lock()`, which refuses the outbound call rather than trusting review to
remember.

## 2. Concurrent access was broken at 100%

SQLite connections belong to the thread that created them. The database layer handed out one
connection and shared it. Measured with four threads doing real writes:

```
4 threads x 50 audit appends  ->  4 errors, 0 rows written
error: SQLite objects created in a thread can only be used in that same thread
```

**100% failure rate.** This is not a "rare race under heavy load" — the web process could not
have served a second request. `db.Database` now issues one connection per thread, keeps SQLite's
own thread guard switched *on* (so a mistake is an error at the boundary, not undefined behaviour),
and offers one explicitly shared connection for read-only dashboards with `query_only=ON` so a
stray write fails at SQLite rather than silently racing.

## 3. Retry without jitter livelocks

WAL gives one writer, so waiters queue. When the retry budget is exhausted, SQLite raises
`database is locked`. The obvious fix is a retry loop. The naive version is worse than no fix:
N waiters that time out together retry in lockstep, each grabbing the lock just long enough for
the next one to fail, and the system livelocks at a fraction of its capacity.

`with_retry()` uses exponential backoff with **full jitter**, because the jitter is the mechanism
and not decoration. Two tests assert it: one that the delays actually vary, one that they stay
bounded.

Crucially, the retry is *narrow*. Only lock contention is retried. A `UNIQUE` violation is
raised immediately, because retrying it converts a clear failure into a slow one.

## 4. A false halt costs more than a false pass

SQLite reports `SQLITE_BUSY_SNAPSHOT` with the same message as ordinary contention. It means the
connection holds a read snapshot that cannot be upgraded — and **waiting cannot fix it**. A
uniform retry loop burns the whole budget and then reports a busy database, which §4.16 turns into
a halt.

Any code that writes inside a lazily-read cursor can hit this, including `ledger.balances` and
`audit.verify`. It is now recognised by extended error code and raised as a distinct,
non-retryable error. The general principle: **in a payment system, a false halt is a business
outage and a false pass is a fraud.** The retry logic is written to fail toward the halt, and the
cases that cannot be fixed by retrying are separated out so they do not masquerade as contention.

## 5. Three silent failures where the write succeeded

These are the ones worth dwelling on, because in every case the operation *looked* like it
worked.

### 5.1 A halt with no record of it

The kill switch committed its state, then wrote its audit entry in a separate transaction.
Forcing the audit write to fail produced:

```
trip rows: 1
killswitch_state: halted = 1, reason = 'real incident'
audit rows: 0
audit.verify()  ->  ok=True, checked=0
```

The system was halted, for a real reason, and **every audit control reported a clean chain**.
The log-before-act requirement (§14 b) held for transfers and did not hold for the control that
stops all of them. One transaction now covers the trip row, the state update and the audit
entry.

### 5.2 Half-postings in the ledger

`ledger.post` read the next line number and inserted each leg as a separate autocommitted
statement. Two concurrent postings read the same next number; the loser collided on its second
leg, and the first leg stayed committed:

```
8 trials, 8 threads, 20 postings each:
  2 of 8 trials left the ledger UNBALANCED by 10.00
  max(line_no) = 380 against 400 posted  ->  20 legs lost entirely
```

An unbalanced ledger with an orphaned debit is worse than a failed posting: it reads as money
leaving the business, and there is no way to tell which leg to reverse. All legs now commit
together or none do. Re-measured: **8/8 trials balanced, all 320 legs committed.**

### 5.3 A transaction that was not one

The per-thread connection fix came with a `Database.transaction()` convenience wrapper that
discarded its generator context manager. CPython finalised it immediately and ran `ROLLBACK`
*before the caller's block started*. So the write lock was never held, `in_transaction` was
`False` throughout, and an exception mid-block left every row committed. Both failures were
invisible because the writes succeeded.

This one is worth naming plainly: **it was introduced by the fix for finding 2, and only a test
written specifically to check the transaction's behaviour found it.** A concurrency fix that
only checks "do concurrent writes succeed?" would have shipped it.

## 6. Concurrency must not manufacture a false accusation

A false positive on the audit chain halts the executor. So the property that matters is not
"the chain survives concurrency", it is "**concurrency never produces a pattern that looks like
tampering**."

Four threads writing 480 entries produced a dense, gapless, correctly linked chain, and
`verify()` reported clean. Four *processes* did the same. An aborted transaction leaves no hole,
because the sequence number is supplied explicitly rather than taken from `lastrowid`. A writer
killed between `INSERT` and `COMMIT` leaves no orphan, and the next writer proceeds immediately
— the OS releases the WAL lock on process death.

Each of those is a test, because each was a way the chain could develop a false positive.

## 7. The tamper-evidence that was not tamper-evident

The design has an append-only hash chain, signed checkpoints, and a signed "head anchor" holding
the highest sequence number ever sealed. The anchor exists for one reason: every checkpoint can
be deleted along with the entries it covers, and the survivors still verify, because a seal at
seq 100 pins entry 100's hash and a chain truncated to 100 has that same hash. The anchor is
what makes truncation detectable.

It was the one signed file in the system whose signature was never checked. `read_anchor` parsed
`data["signature"]` and discarded it.

Reproduced end to end — a 200-entry chain, truncate to 150, delete the seals above 150, forge the
anchor to 150:

```
verify_checkpoints  -> ok=True, checked=150
head_is_sealed      -> ok=True, checked=150
chain verify        -> ok=True, checked=150
```

**Fifty INTENT/RESULT records — the evidence that money was about to move — deleted, with every
check green.**

Worse, the corrupt-anchor branch set the recorded maximum to the *current* sequence number,
which is exactly the silent rollback the function's own docstring claimed could not happen.

Both are fixed: the signature is verified with the same public key as every seal, and a damaged
anchor raises rather than rebuilding. The reasoning matters more than the fix — **the anchor is
the only artefact that survives a thorough attacker, so "reconstruct it from what remains" is the
one response guaranteed to destroy the evidence.**

### 6b. Torn writes read as tampering

Both files were written with `write_text`: open, write, close. Power loss between write and flush
leaves a truncated file — and for the anchor that is indistinguishable from an attacker editing
it, so a power cut would halt the executor with a tampering verdict. Now: temp file, `fsync`,
atomic replace, `fsync` the directory.

This is the general lesson worth stating: **durability bugs and integrity bugs look identical
from the outside.** An operator seeing "chain verification failed" cannot tell a power cut from an
intrusion, and must assume the worse. Anything that can produce a spurious integrity failure
needs an fsync.

## 8. The duplicate lock was one invisible character wide

§4.3 makes `(vendor_id, normalised invoice number)` *the* duplicate-detection strategy, and
`DUPLICATE` a hard block. The key was built by normalising the invoice number. Python's `\s`
does not match Unicode format characters, so the normaliser stripped spaces but not:

| Character | Code point | Effect |
|---|---|---|
| Zero-width space | U+200B | renders as nothing |
| Byte-order mark | U+FEFF | invisible |
| Soft hyphen | U+00AD | invisible, inserted by some banking systems |
| Word joiner | U+2060 | invisible |
| Zero-width joiner | U+200D | invisible |
| Right-to-left override | U+202E | **reverses what a human sees** |

Verified by codepoint: `INV-2291` and `INV-2291` + U+FEFF produce two different
`obligation_key` values, and both take the primary key. **The same invoice submitted twice, one
copy carrying a byte that renders as nothing, is paid twice.**

This is not exotic. A zero-width space is what several mainstream PDF exporters and copy-paste
pipelines insert into long strings. The bypass is one character wide.

The same characters split the **bank fingerprint** of an account that had not changed — producing
`HOLD: BANK_CHANGE`, a 72-hour cooling-off and a callback on a supplier whose bank details did not
move. That is the exact false positive §4.14.5's `bank_change_flag_precision` is measured
against, and it is the *other* failure direction: not a missed attack, but a supplier whose
payment stops for three days because a character rendered as nothing.

`app/core/text_normalisation.py` strips category `Cf`/`Cc`/`Zl`/`Zp`/`Mn`/`Mc`. It deliberately
**does not fold homoglyphs** — the Cyrillic "a" (U+0430) is a real letter in a real supplier name,
and silently merging two different suppliers is worse than reporting a near-miss. That belongs in
vendor matching, where a human can see it.

## 9. The fingerprint could be made to collide

`PayeeDetails.extra` holds corridor-specific identifiers, and the fingerprint builds an
identifiers dict with `account` first and then expands `extra` over it. So an `extra` key named
`account` **shadows the real account**:

```
victim   account = 370400440532013000
attacker account = 990000111222223333  +  extra={"account": "370400440532013000"}
fingerprint(victim) == fingerprint(attacker)   ->  True
```

Two *different* bank accounts hashing identically means the core claim — "a different
fingerprint always produces a change request" — is falsifiable by an attacker-controlled field,
and a real bank change never fires the lock. The lock does not fail loudly; it silently does
nothing, which is the worst way for it to fail.

Reserved keys are now refused, and `extra` is a read-only mapping — because `frozen=True` on a
dataclass never protected a mutable `dict` field, so the fingerprint of a "frozen" object changed
underneath its holder.

## 10. The floor row that could not fail

§4.15 row 10 pins T0 auto-pay **off**; turning it on requires a two-signature policy. The floor's
check for that row validated only the *type* — `isinstance(value, bool)` — and never read the
constraint's own value. So `t0.enabled: true` passed.

The remaining barrier was therefore the signature file, which `load_policy(..., allow_unsigned=True)`
skips. That parameter exists for tests and shipped defaults. It was also, in effect, a switch
turning on automatic payouts.

The constraint is now genuinely enforced, with one honest wrinkle: §4.15 r10's condition depends
on signatures, and **a floor check cannot see signatures.** So the violation is marked
signature-gated and `load_policy` resolves it after verification. The shipped demo policy still
loads when signed. It no longer loads unsigned.

Two related floors had the same shape:

- **Negative money.** Only the reserve row rejected negatives. `first_payment_cap_usd: -2500`
  makes tranche 1 a negative payment. `per_approver_day_usd: -30000` stops the daily cap binding
  at all — the limit becomes unlimited by being negative.
- **Row 22's conjunction.** The spec reads "≥ 48 h **and** ≥ the rail's business-day window". The
  two were checked independently, so a policy could declare 30 business days beside a 48-hour
  timer — and the timer is the number the poller actually consults. The policy would *read* as a
  month and *behave* as two days.

  A first attempt expressed this as an hour bound. It rejected the spec's own shipped policy,
  because 48 hours is legitimately less than three banking days. That attempt was reverted and
  is recorded in DECISIONS D-B20 so nobody retries it.

## 11. A currency table that overstated money 100×

The ISO 4217 exponent table had 12 entries. Everything else inherited a default of 2 — including
**17 zero-decimal currencies and 7 three-decimal ones**.

```
KRW 1,000,000  ->  "1000000.00"      (ISO 4217: KRW has 0 decimal places)
OMR     100   ->  "100.00"          (ISO 4217: OMR has 3)
```

For a zero-decimal currency the default is not a safe rounding choice; it is a **100×
overstatement** carried into every cap comparison, every ledger leg, every reconciliation total
and every tie-out term. The demo scopes to USD/EUR/GBP, which is exactly why no demo path would
have caught it, and the table was nonetheless written to look authoritative.

The fix is not a longer table — it is that **an unlisted code is refused rather than guessed.**
A default exponent is only defensible where the alternative is refusing to operate; here it was
defensible nowhere.

## 12. One trailing space turned a fraud stop into a shrug

Failure types route to playbooks, and the compliance group is the one where the answer is *stop*:
§4.15 r29 says any compliance failure trips the kill switch **on first occurrence**, which is the
only trip that is not threshold-based.

The lookup was an exact dictionary hit on a raw string:

```
"ACCOUNT_UNDER_RESTRICTION"   -> playbook F, trips the kill switch
"account_under_restriction"   -> playbook H
"ACCOUNT_UNDER_RESTRICTION "  -> playbook H      (trailing space)
"Account_Closed"              -> playbook H
```

Playbook H is "escalate, never auto-retry" — the run continues. And §4.16's "unknown
`failure_type` → DEFAULT handler" makes H sound like the safe default. It is the opposite of safe
for the one group where the spec says stop.

This is the general shape of the bug class: **a fail-safe default that is only safe for some
inputs.** Lookup now normalises case and whitespace first, so a near-miss still reaches its real
playbook and a genuinely unknown type still reaches H.

## 13. Reconciliation primitives that produced wrong numbers silently

Three primitives whose only job is to be right about scope:

- **`LIKE` without `ESCAPE`.** `account_prefix_totals("AP_clearing")` matched `APXclearing` too,
  and `account_prefix_totals("%")` matched the entire ledger. One underscore typo in an account
  family silently doubled the reconciliation population — and the tie-out still produced a
  number. A wrong number, with no error.
- **Unvalidated currency on a ledger leg.** A posting in a currency absent from the table balanced
  perfectly *within its own invented bucket*, and a USD-scoped tie-out saw an empty set and
  reported a perfect residual. Money had left the ledger's line of sight with no error anywhere.
- **An account mask that disclosed the whole account.** For a 5-character account the 2-character
  prefix and the 4-character tail overlap, so the mask rendered every character — in every UI row
  and every log line.

None of these announces itself. They return a plausible answer, which is why reconciliation
disagreements in production are so hard to trace.

## 14. An invisible-text detector blind to the standard notation

The §4.3 hidden-text control flags text too small or too light to be meant as read — the attack
where the human reads the invoice and the model reads the whole text layer.

The implementation matched literal colour strings. `rgb(255,255,255)` — **the notation every
HTML-to-PDF renderer and every browser emits** — was not caught, while `#fff` was. Also missed:
a NaN font size (which fails every comparison, so it read as "visible") and an empty run at 0.5pt.

Detection is now by computed luminance, so the notation does not matter.

## 15. A missing timezone package that would have crashed on day one

Daily caps are per **IST calendar day**. `tzdata` was not a dependency. On Windows and in slim
containers, `ZoneInfo("Asia/Kolkata")` raises `ZoneInfoNotFoundError`.

There is no code for the daily caps yet, so nothing failed today. It would have failed on the
first day of the first run, in the control that enforces the cap. A one-line dependency is the
difference between a designed system and a system that assumes its environment.

---

# What is deliberately not built yet

Naming these is part of the hardening. Each is a place a reviewer should look first.

| # | Gap | Why it matters | Where it belongs |
|---|---|---|---|
| 1 | **The lock has no cross-row invariant.** `change_request_next` takes no `vendor_id`. | Two change requests for one supplier can both reach `APPROVED`, and which one supersedes the old bank details is undefined. The state machine is correct *per request*; the property that matters is *across* them. | `oob.py` |
| 2 | **No cap counter is atomic.** | 83% of increments lost under 8 threads. The counter that lifts the first-payment cap must move by `UPDATE … RETURNING`, and a zero-row result must re-read and re-decide. | executor |
| 3 | **`verify()` is O(n) and materialises every row.** | 13.26 s and ~0.51 GB at 1M entries, single-threaded, before the executor starts. Needs to verify from the last sealed anchor. | `audit.py` |
| 4 | **No retention policy.** | The audit log is deliberately un-prunable, so the answer is archival, not deletion. Observation rows grow one per poll with no cap. | operations |
| 5 | **No `var/executor.lock`.** | The single-writer guarantee the whole design rests on is currently enforced by nothing. | worker |
| 6 | **Unknown events to a state machine are silent no-ops.** | Fail-closed, but a typo strands a change request in `PENDING_CALLBACK` forever with nothing logged. | `statemachine.py` |
| 7 | **No executor, client, planner or web layer.** | Roughly 7% of the build. Everything here is the foundation being hardened ahead of the code that will sit on it. | milestones |

---

## The pattern worth naming

Almost none of the above were found by reading the code. Each was found by **constructing the
condition and observing the behaviour**, and several were found by deliberately trying to break a
control that its own test suite already declared green.

The recurring shape:

- A control that **cannot fail** is indistinguishable from a control that **does not work**.
  A type check that never reads the value; a signature that is parsed and discarded; an audit
  entry written after the fact rather than before.
- A safety mechanism that **returns a plausible wrong answer** is worse than one that returns
  none. A reconciliation that doubles its population, a mask that shows the whole account, a
  currency table that multiplies by 100.
- A **default that is only safe for some inputs** is a hidden fail-open. Case-sensitivity turning
  a fraud stop into a shrug; a fallback exponent for a currency that has none.
- **Silent success is the failure mode to fear.** Every defect in §5 looked like a working
  system, because the write succeeded.

None of these are exotic adversaries. They are what a payment system does under ordinary
concurrency, ordinary unicode, ordinary file formats and ordinary mistakes — which is exactly why
they are the ones worth demonstrating.