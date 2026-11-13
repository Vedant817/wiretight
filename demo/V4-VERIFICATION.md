# Wiretight v4 verification

**Duration: 241.32 seconds (4:01.32)**. 1920x1080, 25fps H.264 video / AAC audio. Both streams 241.320000s; 6033 video frames.

Full decode and ffmpeg silencedetect (-40dB, minimum 2.5s): only **238.798-241.323s (2.52444s)**, the final hold. The detector includes about 3ms of decoded AAC padding beyond container duration. No decode errors.

## Presentation and narration changes

- Top-right badge removed. Disclosure chips for timing, API responses, synthetic emails and fixtures removed. Assumption/pricing notes remain.
- Exact small grey footer on all 23 captures: `Synthetic company data · Airwallex API responses simulated · cooling-off shortened for recording`.
- Deleted the requested voice sentence and its screen banner. Retained the rule screen because its rule narration remains. Timings recalculated from sentence clips, with no empty slot.
- Closing line: `all data synthetic`; no URL or branch name.
- Removed the displayed transfer ID containing the forbidden term; underlying identifiers, fixtures, calculations and code names are unchanged.
- V3 role-chip layout, pronunciation fixes and 0.3s sentence / 0.7s scene pauses remain. Existing edge-tts sentence clips reused after matching their emitted word metadata to the v4 spoken script; the deleted sentence is excluded from the audio concat.

## Requested term search

Case-insensitive expression: `demo|mock|simulated`. The recorder writes visible DOM text at the same moment as each PNG capture, as `demo/raw-take-v4/scene00.txt` through `scene22.txt`. The scan uses these rendered-text snapshots, not OCR of PNG files.

- Rendered captures: 23 matches, all exactly the required footer (one per capture).
- Rendered capture hits outside footer: **none**.
- VO-v4-spoken.txt hits: **none**.
- Detailed evidence: ignored `demo/raw-take-v4/rendered-text-grep.log` and `text-scan.json`.

## Capture evidence

| Change | Capture |
|---|---|
| No badge; exact footer | All scene00.png-scene22.png |
| Rule screen without removed banner | scene06.png |
| Cooling-off without timing chip | scene16.png |
| Recovery payout without response chip or internal transfer ID | scene17.png |
| Architecture layout retained; no response chip | scene20.png |
| Closing line | scene22.png |

All 23 captures passed footer equality/visibility, absence of badge, no-placeholder, content-bounds and text-overlap checks. Rule, cooling-off, architecture and closing captures visually inspected. Ruff and git diff whitespace checks passed. No independent listening review or hosted TestSprite run was performed. No live-provider acceptance is claimed.

## Preservation

V3 is saved as `demo/wiretight-demo-v3.mp4`, SHA-256 `9b37f346bdd2863f447a929103b8209b587f00d44a900f43e14dfd839f0b7af0`, verified equal to the pre-edit video. V1 and V2 are retained. All MP4 files and raw captures remain ignored by Git.

## Scene starts

| Start | Scene | Capture |
|---|---|---|
| 0:00.00 | Cold open | scene00.png |
| 0:02.60 | Cold open | scene01.png |
| 0:06.72 | Title | scene02.png |
| 0:17.20 | Problem - the numbers | scene03.png |
| 0:48.60 | Who it is for | scene04.png |
| 0:59.88 | Why now | scene05.png |
| 1:19.64 | The rule | scene06.png |
| 1:29.52 | The run and the plan | scene07.png |
| 1:54.60 | The email | scene08.png |
| 2:00.08 | The lock fires (1 of 2) | scene09.png |
| 2:07.08 | Plan diff - surgical | scene10.png |
| 2:15.56 | Rule 3 - requester cannot confirm | scene11.png |
| 2:18.84 | Priya calls the number on file | scene12.png |
| 2:26.00 | Request rejected, real invoice paid | scene13.png |
| 2:35.04 | The payout comes back | scene14.png |
| 2:39.16 | The genuine request (2 of 2) | scene15.png |
| 2:47.72 | Cooling-off, sign-offs, cap | scene16.png |
| 2:55.60 | Tranche 1 out, tranche 2 held | scene17.png |
| 3:07.24 | Tie-out | scene18.png |
| 3:16.36 | Status board | scene19.png |
| 3:18.96 | Architecture | scene20.png |
| 3:38.64 | Business model | scene21.png |
| 3:54.80 | Close | scene22.png |
