# Wiretight: Airwallex Agentic Banking Hackathon package

> **Wiretight: supplier payouts that can't be quietly redirected.**
> *New or changed bank details stay locked until a second person confirms them by callback.*

This package holds everything decided before the build: the locked spec, the master prompt for the coding agent that builds it, the research behind it, and the board's full deliberation. **Nothing has been built, run against a live Airwallex sandbox, submitted or sent.** Every API behaviour is from Airwallex's docs or the hackathon guide and is marked ⚠ unverified where a live check is needed.

## Read in this order
| # | File | What it is |
|---|---|---|
| 1 | `README.md` | This index: dates, your action list, the file map |
| 2 | `FINAL.md` | **The locked spec (v1.0), the single source of truth.** The idea, evidence, paste-ready idea-phase application text (§3), product rules, the lock, policy floor, architecture, stack and pins, repo tree, env vars, Airwallex setup and endpoints, data model, day-1 spike, tests T-01..T-34 (+ R4 additions), 20-scenario eval, README and video rules, demo script, milestones, Definition of Done |
| 3 | `PROMPT_BUILD_AGENT.md` | How to start the build + the paste-ready master prompt for the coding agent, and 3 follow-ups (resume, pre-freeze audit, demo-video prep) |
| 4 | `board/round4-redteam.md` | The final red-team (Judge, Compliance & Risk, Staff Engineer): findings, fixes, score before and after |
| 5 | `board/DECISIONS.md` | The board's decision log D0–D10 (past project names redacted in this copy) |
| 6 | `00-hackathon-brief.md` | Hackathon rules, dates, prizes, judging signals, starter kits |
| 7 | `01-real-world-problems.md` | Real operator pains with cited numbers |
| 8 | `02-idea-board.md` · `03-recommended-idea.md` · `04-sources.md` | The ideas scored, the original recommended spec, all sources |
| 9 | `AGENTIC_BANKING_PACK.md` | Files 00–04 in one document |
| 10 | `board/` | Round 0–2 memos per role, the Round 1 shortlist, `SPEC-v1.md`, `names.md`, the v0.1 draft of FINAL, and 4 screen wireframes (`round2/screen-*.png`) |
| 11 | `raw/` | Raw evidence captures (Airwallex doc extracts, hackathon pages, reports) cited by the board |

**A note on names:** the research pack and board files written before the rename (D9) use the old working name "Countersign". The project is **Wiretight**. Where an older file disagrees with `FINAL.md`, `FINAL.md` wins.

## Key dates (IST)
| When | What |
|---|---|
| **Wed 21 Oct** | Target: submit the idea application |
| **Fri 23 Oct, 11:59 PM** | Idea application deadline |
| **Sun 25 Oct, 10:00 AM** | Accepted teams notified; build phase starts; first commit allowed |
| Fri 30 Oct | Checkpoint 1: live money path in the sandbox |
| Thu 5 Nov | Checkpoint 2: full demo headless, with tie-out |
| Sat 7 Nov | Checkpoint 3: full demo through the UI |
| Sun 8 / Tue 10 / Thu 12 Nov (mornings) | Live demo takes (max one per day) |
| **Wed 11 Nov** | Feature freeze |
| **Thu 12 Nov** | Video + you submit on HackerEarth |
| **Fri 13 Nov, 11:59 PM** | Hard submission deadline (Fri is buffer only) |
| Sun 15 Nov · Thu 19 Nov | Finalists · Demo Day, San Francisco (remote optional) |

## Your action list (from FINAL §0.2)
**Before the idea deadline**
1. Log in to HackerEarth and read the event's **rules tab**. Look for "Your hack must be developed entirely during the Hackathon duration". Screenshot every **idea-form field and its character limit**.
2. **Submit the idea application** using `FINAL.md` §3, pasting the block that fits each field. Fill the one bracketed "status on the day" line truthfully. Target Wed 21 Oct.
3. **Create the Airwallex sandbox account** at `sandbox.airwallex.com` (free, no card). Name the business exactly `Sandbox Business` or `New Business Sandbox` so KYB auto-approves. Get the Client ID and API key from **Account > Developer > API keys**. Keep them out of chat and out of any repo.

**Build phase (from Sun 25 Oct, 10:00 AM IST)**

4. Create the **empty public repo `wiretight`**. Put `FINAL.md` and the research pack under `docs/spec/`. Start your coding agent with the master prompt in `PROMPT_BUILD_AGENT.md`.
5. Put the sandbox keys into the repo's local `.env` yourself.
6. By Sat 7 Nov: `make passkeys` (register Meera, Kabir, Arun, Priya on your laptop) and `make sign-policy`.
7. Optional: configure a webhook URL in the sandbox web app, only if the agent's day-1 spike says it's worth it.
8. Live takes (one per IST day), the video and voiceover, then **submit on HackerEarth on Thu 12 Nov** (zip + public repo link + video).
9. Check the repo's `docs/NEEDS_HUMAN.md` daily. Rotate the sandbox API key before Demo Day.

**Standing rules:** no project code or commits before Sun 25 Oct, 10:00 AM IST. No agent contacts anyone or submits anything. Any outside contact (Airwallex devhelp, Discord, partner Slack) is your call.

## Package contents
```
wiretight-package/
├─ README.md  PROMPT_BUILD_AGENT.md  FINAL.md
├─ 00-hackathon-brief.md  01-real-world-problems.md  02-idea-board.md  03-recommended-idea.md  04-sources.md
├─ AGENTIC_BANKING_PACK.md
├─ board/  DECISIONS.md  STATUS.md  ROUND1-SHORTLIST.md  SPEC-v1.md  FINAL-v0.1-draft.md  round4-redteam.md
│          round0/  round1/  round2/ (memos, names.md, screen-1..4 PNGs)
└─ raw/    evidence captures
```
