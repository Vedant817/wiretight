# Wiretight — what only Vedant can do

Ordered by urgency. Everything else the agent does itself. Nothing here is a blocker for offline work;
the agent keeps building around whatever is outstanding.

---

## H1 — Airwallex **sandbox** keys (BLOCKS the entire day-1 spike)

**Status:** not started. No `.env` exists in the repo.

**Exact steps**

1. Sign up at `sandbox.airwallex.com` (free, no card). Name the business **exactly**
   `Sandbox Business` or `New Business Sandbox`, otherwise KYB stays "In review" and every call 403s.
2. Web app → **Account > Developer > API keys**. Copy the **Client ID** and **API key**.
3. Wait for the agent to create `.env.example` (first scaffold commit), then open `.env` yourself and
   fill in:
   ```
   AWX_CLIENT_ID=<paste>
   AWX_API_KEY=<paste>
   ```
4. **Never** paste a key into chat, an issue, a commit, or a fixture. `.env` is git-ignored.

**Why it blocks:** §9.5 has 30 day-1 checks (U1–U16, S-T1..S-T15, C-1..C-3, DA-1..DA-3) whose results
decide real behaviour: whether PAID→FAILED is live (U1), how fees appear in financial transactions
(U13/U14), the return identity (U15), whether a DE·EUR·LOCAL beneficiary creates (DA-1), and which
failure code the demo's failure beat uses (DA-2). Until then the code carries **⚠ unverified** labels
and contract tests are `pending-fixture`, which is honest but blocks Checkpoint 1.

**Deadline:** §9.1 Plan B says if keys have not arrived, cut 1 of §13.3 applies. Under the shifted
calendar (DECISIONS D-B01) that point is **Sun 11 Oct 2026, 6:00 PM IST**.

---

## H2 — Create and connect the public GitHub repo `wiretight`

**Status:** local repo initialised; **no remote configured**.

The agent ran `git init` here as instructed. Nothing is pushed. When you are ready:

```powershell
# create the empty public repo on GitHub, then:
git remote add origin <your-repo-url>
git push -u origin main
```

Until then all work is local-only and **there is no backup**. If this laptop fails, the build is lost.

---

## H3 — Decide the hackathon-rule question (blocking for SUBMISSION, not for the build)

**Status:** open risk raised by DECISIONS D-B01.

The build started **Fri 9 Oct 2026**, 16 days before the spec's sanctioned start of
**Sun 25 Oct 2026, 10:00 AM IST**. FINAL.md's standing rule was "no project code and no repo commits
before" that moment, and the README is supposed to state that all code was written from that date.

There is an unresolved HackerEarth rule — FINAL.md **OPEN-1 / OPEN-4** — that the boilerplate may say
*"Your hack must be developed entirely during the Hackathon duration."* That has never been checked,
because the rules tab is behind a login.

**What to do**

1. Log in to HackerEarth, open the **Rules** tab, and screenshot it.
2. Tell the agent the exact wording. The agent will then either (a) keep the early start and make the
   README state the true dates, or (b) if the rule is strict, tell the agent to rebase the history.

The agent will **not** write a development-period sentence into the README that git history
contradicts. It is derived from `git log`, so it is true either way.

---

## H4 — Idea-phase submission (Vedant only; agents never submit)

**Status:** not submitted. Target **Wed 21 Oct 2026**, deadline **Fri 23 Oct 2026, 11:59 PM IST**.

- Paste-ready text blocks: `docs/spec/FINAL.md` §3 (title, sub-line, track, tagline, 75-word, 210-word,
  550-word, tech stack, 6-slide outline).
- The bracketed `[STATUS ON THE DAY]` line must be filled **truthfully**.
- Screenshot every idea-form field and its character limit first (OPEN-1), since the form is unknown.

---

## H5 — Passkeys and policy signatures (Week 2, by Checkpoint 3 = Thu 22 Oct)

The agent cannot make a passkey gesture. When `make passkeys` exists:

```powershell
make passkeys                                  # Meera, Kabir, Arun (approvers) + Priya (ops)
make sign-policy POLICY=policy.demo.yaml        # two distinct approvers, from your laptop
make sign-policy POLICY=policy.example.yaml
```

These run on **localhost** and need the browser passkey sheet, which only a human can accept.

---

## H6 — Live demo takes, video, voiceover, submission (Vedant records; the agent never does)

At most **one live take per IST day** (§12.4), because the policy caps count Airwallex's own transfer
list and cannot be loosened.

| Take | Original | Shifted |
|---|---|---|
| #1 | Sun 8 Nov | **Fri 23 Oct 2026** |
| #2 | Tue 10 Nov | **Sun 25 Oct 2026** |
| #3 spare | Thu 12 Nov | **Tue 27 Oct 2026** |

The agent prepares `docs/demo-script.md`, `docs/video-shot-list.md` and a resettable
`make demo DEMO_MODE=replay` so Vedant can rehearse without touching the sandbox. Seed the sandbox
the **day before** the first take.

---

## H7 — Optional: webhook URL in the sandbox web app

Only worth doing if the day-1 spike (S-T8 / U4) shows webhooks actually fire for simulated transfers.
Polling is primary in any case; webhooks only ever enqueue a poll. Low priority.

---

## H8 — Rotate the sandbox API key before Demo Day

Revoking the key in the web app is also the ultimate stop for the kill switch (§4.9).