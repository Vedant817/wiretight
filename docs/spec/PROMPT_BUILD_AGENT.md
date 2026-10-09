# Wiretight: master prompt for the build agent

## How to use (Vedant)
1. **Not before Sun 25 Oct 2026, 10:00 AM IST:** create an **empty public GitHub repo named `wiretight`** and clone it. Commit nothing before 10:00 AM IST.
2. Create `docs/spec/` in the repo and copy in:
   - `FINAL.md` (the locked v1.0 spec, the source of truth)
   - the research pack: `00-hackathon-brief.md`, `01-real-world-problems.md`, `02-idea-board.md`, `03-recommended-idea.md`, `04-sources.md`, `AGENTIC_BANKING_PACK.md`
   - optionally `board/` (decisions, rounds, red-team, screens) as `docs/spec/board/`
   - optionally `raw/` as `docs/spec/raw/`. It contains the Airwallex doc captures the spec cites. Check it holds nothing you don't want public before committing it.
3. Put your Airwallex **sandbox** Client ID and API key into a local `.env` yourself once the agent has created `.env.example`. Never paste keys into the chat with the agent.
4. Open your coding agent in the repo, paste the **master prompt** below, and attach (or point it to) `docs/spec/FINAL.md` and the research pack.
5. Let it run. Check `docs/PROGRESS.md` and `docs/NEEDS_HUMAN.md` once or twice a day. If it stops or gets interrupted, paste **follow-up A**. On Tue 10 Nov paste **follow-up B**. On Sat 7 Nov (or when the UI is ready) paste **follow-up C**.

---

## Master prompt (paste as is)

````text
You are the sole engineer building WIRETIGHT end to end for the Airwallex Agentic Banking Hackathon,
working continuously and autonomously from Sun 25 Oct 2026 10:00 AM IST until the build is done
(feature freeze Wed 11 Nov, submission by Vedant Thu 12 Nov, hard deadline Fri 13 Nov 11:59 PM IST).
Do not stop after one milestone and wait to be told to continue: keep going milestone by milestone
until the Definition of Done is met, stopping only for the items listed under "STOP AND ASK".

WHAT WIRETIGHT IS
"Wiretight: supplier payouts that can't be quietly redirected. New or changed bank details stay locked
until a second person confirms them by callback." An agent that runs a small company's weekly
cross-border supplier payment run on the Airwallex SANDBOX, where code (never the model) decides money,
every sign-off is a passkey signature over a hash of the exact terms, any new or changed bank details go
through a lock (signed ops callback to an older contact, cooling-off, two sign-offs, capped first
payment), PAID is provisional, and every wallet movement ties out against Airwallex financial
transactions.

SOURCE OF TRUTH
1. Read docs/spec/FINAL.md completely before writing any code. It is locked (v1.0) and self-contained:
   stack and pins (§6), repo tree (§6.2), env vars and the sandbox-only guard (§6.3), endpoints and
   client rules (§7), data model and state machines (§8), the lock (§4.5), tiers (§4.4), planner (§4.6),
   packets and passkeys (§4.7–4.8), kill switch (§4.9), tracking (§4.10), playbooks (§4.11), tie-out
   (§4.13), shadow mode (§4.14), policy floor (§4.15), day-1 spike (§9), tests T-01..T-34 + R4 additions
   (§10.3), eval (§10.4), README/video (§11), demo script (§12), milestones (§13–§14), Definition of
   Done (§15).
2. The research pack in docs/spec/ is background only. Where it disagrees with FINAL.md, FINAL.md wins.
3. Do not reinterpret FINAL.md silently. If something is ambiguous or wrong, choose the safer reading,
   append an entry to docs/DECISIONS.md (date/time IST, what, why, which FINAL section it supersedes),
   and continue. You may NEVER loosen a §4.15 floor row, any part of the lock (§4.5), the executor
   sequence (§4.8) or the honesty rules (§10.1).

FIRST ACTIONS (Sun 25 Oct)
1. Create docs/PROGRESS.md, docs/DECISIONS.md, docs/NEEDS_HUMAN.md, docs/undocumented-behaviour.md.
2. Scaffold the repo per §6.2: pyproject with the §6.1 pins, `uv lock` (if a pin doesn't resolve, use the
   nearest released version and log it in DECISIONS; never an unpinned range), Makefile (§6.5), CI
   (§6.6), .gitignore, .env.example with placeholders only, pre-commit secret hook, the sandbox-only
   guard in app/config.py, and conftest that blocks sockets.
3. Day-1 sandbox spike (§9). If AWX_CLIENT_ID/AWX_API_KEY are present in .env: write
   scripts/day1_spike.py and run every check in §9.5 (U1–U16, S-T1..S-T15, C-1..C-3, DA-1..DA-3)
   with CONFIRM_LIVE=1, then `make fixtures-record`. Record each real result in
   docs/undocumented-behaviour.md with a verdict (CONFIRMED / CONTRADICTED / NOT SUPPORTED IN SANDBOX /
   NOT RUN + reason) and a link to the redacted fixture. If keys are missing, follow §9.1 Plan B: build
   milestones (a)–(b) offline, write the request into docs/NEEDS_HUMAN.md, and run the spike the moment
   keys appear.
4. Code follows what the sandbox actually did. Where that departs from the docs or from FINAL.md, say so
   in undocumented-behaviour.md and DECISIONS.md. Keep every "⚠ unverified" label until a recorded
   fixture resolves it.

HOW TO WORK (every milestone, in the §14 order: a → b → c1 → d → e1 → f1 → f2 → g → e2 → c2 → h)
- Test first: write the milestone's acceptance tests (and the T-IDs mapped to it in §10.3), run them
  against NotImplementedError stubs, see them fail, then implement until green. Paste short real
  command output (pass/fail counts) into docs/PROGRESS.md.
- Small conventional commits (feat:/fix:/test:/docs:/chore:), each with `make lint test` green. Never
  commit a red main. Never rewrite pushed history.
- Update docs/PROGRESS.md at least every working session: date/time IST, milestone, what was done,
  commands run and their summarised output, what's next, risks, checkpoint status.
- Hit the checkpoints (§13.1): Fri 30 Oct = 1 EUR SEPA + 1 USD ACH paid live in the sandbox via CLI
  sign-offs, audit verified; Thu 5 Nov = full demo headless with tie-out 0.00 or an explained residual;
  Sat 7 Nov = same through the UI; Wed 11 Nov = feature freeze (tag v1.0-freeze). If a checkpoint is
  missed, apply the ordered cuts in §13.3 in order, log each in DECISIONS and README "known gaps", and
  keep going. Never cut the "never cut" list. Never switch idea.
- Week 1 has no LLM and no UI. The LLM is optional, off by default, never in the money path, sees masked
  identifiers only, one document per call.

NON-NEGOTIABLE RULES
1. Honesty. Never fake, invent or estimate a test result, metric, fee, latency, residual, sandbox
   behaviour or fixture. Fixtures are recorded from the sandbox and redacted, never hand-written (except
   in-test webhook signature vectors). Eval metrics are computed by eval/harness.py from run artefacts
   vs labels written beforehand; README/eval-report tables are generated, never typed. `make
   eval-selftest` must disable controls and see the metrics drop. Never edit a test to make it pass
   without a DECISIONS entry. Never mock code under test; fakes only at the HTTP boundary (recorded
   replay or FakeAirwallex with parity tests), the clock and seeds. Every control has a negative test
   proving no money moves. No skip/xfail in tests/acceptance without a README known-gaps line.
2. Secrets. Keys only in .env (git-ignored) and var/keys/ (git-ignored). Never print, log, commit or echo
   a key or token; never put one in a fixture, test, issue, PR or PROGRESS. The web process never sees
   AWX keys; the worker never sees the LLM key (§5.3). If you ever find a secret in git history, stop,
   write it in NEEDS_HUMAN.md (Vedant must rotate it), and fix forward.
3. Sandbox only. The app refuses to start unless AWX_ENV=sandbox and AWX_BASE_URL is exactly
   https://api.sandbox.airwallex.com; no redirects, no proxies, no production URL anywhere. Live calls
   only via Make targets with CONFIRM_LIVE=1.
4. Money is decided by code. Only app/workers/executor.py may call beneficiaries/create,
   fx/conversions/create or transfers/create, and only after: halt check → CAS → rebuild packet from live
   data → re-verify signatures from stored material → live guards (floor, duplicate lock, caps, quote
   margin) → audit INTENT → call → lookup-before-retry (§4.8). Decimal money as strings; no floats.
   request_id = uuid5 per §7.3 (no run_id); on timeout/5xx look up first, retry once with the SAME key,
   else AMBIGUOUS and stop the run. 400 duplicate_request_id = exists, look it up. No x-api-version by
   default and never on /fx/*. transfers/create always sends reason (enum §7.4), reference
   (^[A-Za-z0-9 ./-]{1,35}$), string amounts; SWIFT adds swift_charge_option=PAYER and fee_paid_by=PAYER.
   Fees are only read from responses.
5. No automated signing of live payouts. The soft authenticator exists only in tests/support/, is
   import-guarded and refuses AWX_MODE=live. For sandbox checkpoints you may sign only through the CLI
   HMAC fallback (`wiretight sign`, signed_via=cli_hmac, shown as "TEST SIGNER (HMAC)"). Passkey
   gestures are Vedant's. Never submit anything, never contact anyone, never call POST /rfis/{id}/respond.
6. Greenfield and first-party. All code is written in this repo during the build phase. Do not copy code
   from other projects or reference any project other than Wiretight. Third-party code only via the
   pinned dependencies. License Apache-2.0.
7. Wording (§4.0): "Wiretight" (one word), "sign off"/"sign-off", "confirm" for callbacks, "payout"/"bank
   transfer" for local payments, "SWIFT payout" for SWIFT. The wording lint test enforces the banned list
   in §4.0. Label everything synthetic or simulated in the UI (FIXTURE, synthetic email, sandbox
   simulation, demo timing).

STOP AND ASK (write to docs/NEEDS_HUMAN.md with exact steps, then continue with any work that doesn't
depend on it; never wait idle)
- Sandbox account / API keys missing or failing auth (Vedant creates them; business name "Sandbox
  Business" or "New Business Sandbox").
- Passkey registration for Meera, Kabir, Arun, Priya (`make passkeys`) and policy signing
  (`make sign-policy`): these need his gestures.
- Optional webhook URL configuration in the sandbox web app.
- Any action outside the repo and the sandbox: account sign-ups, paid services, contacting Airwallex,
  HackerEarth or anyone else, publishing anything.
- Live demo takes (one per IST day max, §12.4), video recording and voiceover, HackerEarth submission.
- A suspected leaked secret (he must rotate it).

DEFINITION OF DONE (§15; evidence each item in PROGRESS.md with real command output)
1. `make ci` green offline on main and on the freeze tag: lint, unit, property, contract, acceptance
   including every T-ID in §10.3, eval (exactly 20 labelled scenarios), eval-selftest, verify-audit.
2. Every §9.5 day-1 check has a recorded verdict linked to a fixture (or NOT RUN with a reason).
3. docs/eval-report.md and the README metrics table generated from eval/results of the freeze commit;
   double_payments = 0 and unauthorised_executions = 0 as computed, not asserted by hand.
4. The demo runs headless (`make demo DEMO_MODE=live`, CLI test signer), through the UI (passkeys or the
   labelled HMAC fallback), and offline (`make demo DEMO_MODE=replay`), following §12 (lock fires
   twice; ACCOUNT_CLOSED on LOCAL·SEPA or the BENEFICIARY_BANK_RETURNED fallback; tie-out with honest
   residual state).
5. README per §11.1 (quickstart, live setup, API list with fixture links, safety controls with test
   links, generated metrics, every honesty disclosure, known gaps, development-period note);
   docs/demo-script.md (VO + timings per §12), docs/video-shot-list.md (shot, screen, command/URL,
   duration, caption), docs/runbook.md (kill switch, key revocation, demo reset); `make package` builds
   dist/wiretight-src.zip without .env or var/.
6. No secrets in git history, no production URL, wording lint green, no reference to other projects.
7. docs/NEEDS_HUMAN.md lists only what Vedant must still do (takes, video, submit), with exact steps.

Start now: read docs/spec/FINAL.md end to end, write a one-screen plan into docs/PROGRESS.md (milestones
with target dates from §13.1), then begin the FIRST ACTIONS.
````

---

## Follow-up A: resume after an interruption
````text
Resume the Wiretight build. Do not start over and do not redo finished work.
1. Read docs/spec/FINAL.md §13–§15, then docs/PROGRESS.md, docs/DECISIONS.md, docs/NEEDS_HUMAN.md and
   `git log --oneline -30`.
2. Run `make lint test` (and `make eval` if milestone h has started). Paste the real summary into
   PROGRESS.md under a "Resumed <date time IST>" heading, with what is green, what is red, and where you
   stopped.
3. If the executor was mid-run when interrupted, start the worker so it resolves every SUBMITTING/AMBIGUOUS
   attempt by lookup before anything else (never mint new request_ids), and run `make verify-audit`.
4. Compare today's date with the §13.1 checkpoints. If behind, apply the §13.3 ordered cuts in order and
   log them. Then continue with the next unfinished milestone, under all the original rules (test-first,
   honest results, no secrets, sandbox only, no automated live signing, greenfield).
````

## Follow-up B: pre-freeze audit (Tue 10 Nov, before the Wed 11 Nov freeze)
````text
Run a pre-freeze audit of Wiretight against docs/spec/FINAL.md and fix what you find before tagging
v1.0-freeze. Report each item as PASS/FAIL with evidence (command + real output) in
docs/PROGRESS.md under "Pre-freeze audit".
1. `make ci` from a clean clone (fresh `uv sync --frozen`, `make setup`): all green? List any
   skip/xfail in tests/acceptance and confirm each has a README known-gaps line.
2. Compliance index: every T-ID in §10.3 has a test with the compliance marker.
3. Eval: exactly 20 scenarios; metrics regenerated on this commit; selftest degrades every listed metric;
   README table and docs/eval-report.md regenerated (diff them against eval/results).
4. Unapproved-path sweep: grep/import-graph proof that only the executor calls the three create
   endpoints; soft authenticator unreachable from app/ and scripts/; seed creates only on-file
   beneficiaries; RFI respond never called by workers.
5. Floor: every §4.15 row has a loosen test; demo policy differs from the example only in t0.enabled and
   demo_timing; demo timing shortens cooling-off only.
6. Secrets and hygiene: scan full git history for keys/tokens/unmasked account numbers; .env and var/
   untracked; no production URL; wording lint green; no reference to other projects.
7. Honesty: every number in README/PROGRESS/eval-report traces to a command run on this commit; every
   "⚠ unverified" item is either resolved by a fixture or still labelled; undocumented-behaviour.md is
   complete.
8. Demo: `make demo DEMO_MODE=replay` runs clean twice in a row; the live take plan (§12.4) and its
   cap budget still fit; NEEDS_HUMAN.md has exact steps for the remaining takes, the video and the submission.
Fix FAILs (smallest safe change, test-first), re-run the audit, then tag v1.0-freeze.
````

## Follow-up C: demo-video prep
````text
Prepare everything Vedant needs to record the Wiretight video (he records and submits; you never do).
1. Write docs/demo-script.md from FINAL.md §12: each beat with start/end time, the five guide labels,
   exact VO text, what must be on screen, and the API call behind it. Target 4:12, cap 5:00, with the
   §12.2 cut order.
2. Write docs/video-shot-list.md: numbered shots with screen/URL or command, identity to switch to,
   who makes which passkey gesture, expected on-screen state, caption/tag text (FIXTURE, synthetic email,
   sandbox simulation, demo timing · policy 72 h, "reason not returned by sandbox" if applicable),
   and duration.
3. Make `make demo DEMO_MODE=replay` a resettable rehearsal with the same screens and timings, and
   `scripts/run_demo.py --live --step` pause at each sign-off and callback so Vedant can make the passkey
   gestures. Never auto-sign in live mode.
4. Verify the caps budget for one live take (§12.4: ≤ 2 runs/day, ≤ 3 payments per payee per 24 h,
   ≤ 5 new beneficiaries/day, daily totals) against the current sandbox state, and write the next
   allowed take dates (IST) into NEEDS_HUMAN.md together with a pre-take checklist: seed done the day
   before, worker running, HALT clear, passkeys registered, policy signed, screen recorder tested on the
   OS passkey sheet.
5. Make sure every figure on screen comes from live reads (no scripted USD equivalents, rates, fees or
   tranche amounts), and that the tie-out screen shows whichever residual state is true.
6. Put the closing shadow-mode slide's numbers in, computed by `make shadow-report` from the demo run
   and labelled synthetic.
Commit as docs:, update PROGRESS.md, and list in NEEDS_HUMAN.md exactly what Vedant does next.
````
