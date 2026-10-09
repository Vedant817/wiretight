# Wiretight — progress log

Append-only. One entry per working session: IST timestamp, milestone, what was done, commands run and
their real summarised output, what's next, risks, checkpoint status.

All times **IST**. Dates follow the 16-day shift in `DECISIONS.md` D-B01.

---

## Plan (from FINAL.md §14 milestone order, shifted)

| # | Milestone | Shifted target | State |
|---|---|---|---|
| — | Scaffold + day-1 spike (§9) + plan A/B decision | Fri 9 Oct | **in progress** |
| a | Airwallex client + record/replay transport | Fri 9 – Sat 10 Oct | not started |
| b | Trust substrate: schema, state machines, audit chain, policy floor, kill switch, ledger | Sat 10 – Sun 11 Oct | not started |
| c1 | Verify + the lock: parsers, vendors, dupes, fingerprint, change requests, signed callbacks | Mon 12 Oct | not started |
| d | Planner + tiers + caps + tranches | Mon 12 – Tue 13 Oct | not started |
| e1 | Packets + signing (WebAuthn + labelled HMAC fallback) | Tue 13 Oct | not started |
| f1 | Executor + poller | **Wed 14 Oct — Checkpoint 1** | not started |
| — | Buffer, fake parity, shadow skeleton | Thu 15 – Fri 16 Oct | not started |
| f2 | Incidents, replacement, RFI, webhooks | Sat 17 – Sun 18 Oct | not started |
| g | Recon + journal + returns | Mon 19 – **Tue 20 Oct — Checkpoint 2** | not started |
| e2 | UI + passkeys | Wed 21 – **Thu 22 Oct — Checkpoint 3** | not started |
| c2 | Optional PDF/email + LLM ingest (cut item 3) | Thu 22 Oct | not started |
| h | Eval: 20 scenarios, metrics, self-test, README | Sat 24 – Sun 25 Oct | not started |
| — | Demo script, shot list, take #1 | Fri 23 Oct | not started |
| — | **Feature freeze**, tag `v1.0-freeze` | **Mon 26 Oct** | not started |
| — | Final take, video, `make package`, submission | Tue 27 Oct | not started |
| — | Buffer only | Wed 28 Oct | not started |

**Never cut** (§13.3): idempotency + lookup-before-retry · packet binding + executor re-verification ·
the lock (change requests, signed callback, cooling-off, cap, tranches) · executor live guards ·
failure → replacement · tie-out with honest residual states · audit chain · kill switch ·
the 20-scenario eval with self-test.

---

## Session 1 — Fri 9 Oct 2026, 22:35 IST

### Milestone: pre-scaffold (FIRST ACTIONS 1–2)

### What was done

1. **Read `docs/spec/FINAL.md` end to end** (1,252 lines) before writing any code, per the master prompt.
2. **Environment preflight** (cheapest checks only, per repo AGENTS.md):
   ```
   git FOUND     C:\Program Files\Git\cmd\git.exe
   uv FOUND      0.12.22
   python FOUND  3.14.0   (system; project pins 3.12.15 via uv)
   gh FOUND      make FOUND   docker FOUND   node FOUND
   ```
3. **Repo setup.** The folder was **not** a git repo; the nearest repo was a stray, commit-less
   repo at `C:\Users\vedan` that would have swept the entire home directory into any `git add`.
   Ran `git init -b main` here, which isolates this project. `git rev-parse --show-toplevel` now
   returns the wiretight folder. **No remote yet** (`NEEDS_HUMAN.md` H2).
4. **Spec relocated** per the master prompt's step 2: `FINAL.md` + the research pack + `board/` +
   `raw/` are now under `docs/spec/`. The old package index became `docs/spec/README.md`; the root
   `README.md` will be written to §11.1 once there is something true to put in it.
5. **Secret scan of `raw/` before it goes public**, as the master prompt requires. Found
   `x-api-key` and `x-client-id` in `raw/doc_failure_types.txt`: they are Airwallex's *own published
   documentation* curl examples against the sandbox host, not account keys. Redacted anyway
   (`DECISIONS.md` D-B02). No other file in `raw/` matched.
6. **Created** `docs/DECISIONS.md`, `docs/NEEDS_HUMAN.md`, `docs/undocumented-behaviour.md`, this file.

### Scaffold + money (FIRST ACTIONS 1–2 continued)

Built `pyproject.toml` with the §6.1 exact pins, and the modules the rest of the build rests on.

- **`app/config.py`** — sandbox-only guard. Exact match on `AWX_ENV` and `AWX_BASE_URL`; there is
  deliberately **no production-URL constant to compare against**, so no production host can appear
  in `app/` at all. `WebSettings` / `WorkerSettings` each refuse to start if the other process's
  secret is visible (T-09a/b, T-R4e).
- **`tests/conftest.py`** — blocks `socket.socket`, `create_connection` and `getaddrinfo` for every
  non-`live` test, pins `AWX_ENV=sandbox`, and redirects every writable path into `tmp_path`.
- **`app/money.py`** — `Decimal` everywhere, string serialisation at the currency exponent, and
  `raise_on_float()` which walks a payload and names the exact path (`items.0.amount`).

**Gates, real output:**

```
uv lock                 -> Resolved 70 packages in 16.32s   (every §6.1 pin resolved unchanged)
uv sync --extra dev     -> + 70 packages
uv run ruff check       -> All checks passed!
uv run ruff format      -> 12 files already formatted
uv run mypy app         -> Success: no issues found in 7 source files
uv run pytest tests/unit-> 82 passed in 1.15s
```

**Three real bugs found and fixed while writing the tests, not after:**

1. **The socket block was uncatchable.** `test_offline_guarantees.py` failed 5 tests: the block
   *was* raising, but `pytest.raises` missed it. Without `tests/__init__.py`, pytest imports the root
   conftest as top-level `conftest` while the test imported `tests.conftest` — two module objects,
   two different exception classes. Every future "no network here" assertion would have failed for
   the wrong reason. Fixed by adding `tests/__init__.py`. (`DECISIONS.md` D-B05)
2. **The banned-library scan matched itself**, since it holds `import respx` as data. It now skips
   its own file; `respx`/`vcrpy` stay banned everywhere else. (D-B06)
3. **`parse_money` accepted scientific notation.** `Decimal("1E+2")` parses fine, so `1E+2` and
   `100.00` were both valid spellings of one amount that could canonicalise to different packet
   hashes. Now refused, along with a leading `+`. Two test expectations in
   `test_config_separation.py` were also wrong test data, not wrong behaviour (D-B04).

### Day-1 spike (§9): **Plan B**

`.env` does not exist, so `AWX_CLIENT_ID` / `AWX_API_KEY` are absent and no §9.5 check can run.
Recorded in `docs/undocumented-behaviour.md` as the U-register with every row `NOT RUN (no keys)`.
The exact steps to unblock are in `NEEDS_HUMAN.md` H1.

### What's next

Scaffold per §6.2: `pyproject.toml` with the §6.1 pins, `uv lock`, `Makefile`, CI, `.gitignore`,
`.env.example`, the sandbox-only guard in `app/config.py`, and a `conftest.py` that blocks sockets.
Then milestone (a).

### Risks

| Risk | Effect | Mitigation |
|---|---|---|
| No sandbox keys | Contract tests stay `pending-fixture`; ⚠ labels persist; Checkpoint 1 at risk | `NEEDS_HUMAN.md` H1; Plan B cut-1 point Sun 11 Oct 6 PM IST |
| Schedule shifted 16 days | Hackathon "developed entirely during the Hackathon duration" rule unresolved | `NEEDS_HUMAN.md` H3; README date derived from git, never typed |
| No remote configured | Single-machine, no backup | `NEEDS_HUMAN.md` H2 |
| Pins are 2026-vintage targets | A pin may not resolve | §6.1 allows nearest released version, logged in `DECISIONS.md`, never an unpinned range |

### Checkpoint status

| Checkpoint | Shifted date | Status |
|---|---|---|
| 1 — 1 EUR SEPA + 1 USD ACH paid live | Wed 14 Oct | not started |
| 2 — full demo headless with tie-out | Tue 20 Oct | not started |
| 3 — full demo through the UI | Thu 22 Oct | not started |

### Commands run

```
git init -b main                       -> Initialized empty Git repository
git rev-parse --show-toplevel          -> C:/Users/vedan/Documents/Resources/Code/wiretight
uv --version                           -> uv 0.12.22
python --version                       -> Python 3.14.0
uv lock                                -> Resolved 70 packages (all §6.1 pins unchanged)
uv run pytest tests/unit               -> 82 passed
uv run ruff check app tests            -> All checks passed!
uv run mypy app                        -> Success: no issues found in 7 source files
```

Nothing has been built against the sandbox, submitted, or sent to anyone. No test result in this
file is estimated: every number above came from a command run on this commit.