# Wiretight v3 verification

Local render on 2026-11-13. **247.96 seconds (4:07.96)**; H.264 1920x1080 at 25fps, AAC. Both streams 247.960000s; 6199 video frames.

Full decode plus ffmpeg `silencedetect=noise=-40dB:d=2.5` found only the final hold: **245.438-247.979s (2.54044s)**. AAC decoded padding accounts for the detector end beyond the container duration. No decode errors.

## Requested changes

| Item | Confirmation | Capture / audio evidence |
|---|---|---|
| 1 | Role chips stacked above titles; all 23 captures checked for text intersections and bounds. No intersections above the 2px tolerance; visual contact-sheet review of every capture and full-size architecture review. | scene20.png (page 20/22); all scene00.png-scene22.png |
| 2 | Closing line is exactly branch demo/video · all data synthetic; no URL. Every rendered scene asserted to contain no placeholder text. | scene22.png (page 22/22) |
| 3 | Why now? is its own complete sentence clip before Airwallex exposes balances. Generated TTS word metadata contains both Why and now; clip is included at 0:59.880 in the final audio. | scene05.png; v3-scene05-sentence00.mp3/.jsonl |
| 4 | Used the approved alternative: The first capped payment goes out. Displayed tranche terminology is unchanged. TTS word metadata confirms the full replacement sentence. | scene17.png; v3-scene17-sentence00.mp3/.jsonl |
| 5 | Measured sentence clips: 0.300s inserted between sentences within a scene; 0.700-0.740s between scenes (25fps rounding). Final hold 2.5s. Total 247.96s, below 4:45. | All captures; demo/timeline.json contains each sentence time and pause |
| 6 | Hall-den in the spoken input only. Halden remains unchanged on screen and in the source data. | scene07.png; v3-scene07-sentence00.mp3/.jsonl; demo/VO-v3-spoken.txt |

All captures and detailed layout/ffprobe/silence logs are in ignored `demo/raw-take-v3/`. Sentence clips and generated word timestamps are in ignored `demo/vo-segments/`. Screenshots were captured by Playwright, reviewed in six contact sheets, and assembled by ffmpeg with the measured narration clock. The simulation badge text and intentional demo timing / mocked API response chips are unchanged.

## Preserved media

- v1: demo/wiretight-demo-v1.mp4; SHA-256 8e989c78e127511df585f52ce800c21209c2ce5f3815c7d3086534b7074fd8ec.
- v2: demo/wiretight-demo-v2.mp4; SHA-256 953ce6567546328da2325f2e37dfed406e605dd10fcece756867ab178b7c8e40.
- Both preserved versions were checked byte-for-byte by hash; all MP4 files remain ignored by Git.

## Scene/capture list

| Start | Scene | Screenshot |
|---|---|---|
| 0:00.00 | Cold open | scene00.png |
| 0:02.60 | Cold open | scene01.png |
| 0:06.72 | Title | scene02.png |
| 0:17.20 | Problem - the numbers | scene03.png |
| 0:48.60 | Who it is for | scene04.png |
| 0:59.88 | Why now | scene05.png |
| 1:19.64 | The rule | scene06.png |
| 1:36.16 | The run and the plan | scene07.png |
| 2:01.24 | The email | scene08.png |
| 2:06.72 | The lock fires (1 of 2) | scene09.png |
| 2:13.72 | Plan diff - surgical | scene10.png |
| 2:22.20 | Rule 3 - requester cannot confirm | scene11.png |
| 2:25.48 | Priya calls the number on file | scene12.png |
| 2:32.64 | Request rejected, real invoice paid | scene13.png |
| 2:41.68 | The payout comes back | scene14.png |
| 2:45.80 | The genuine request (2 of 2) | scene15.png |
| 2:54.36 | Cooling-off, sign-offs, cap | scene16.png |
| 3:02.24 | Tranche 1 out, tranche 2 held | scene17.png |
| 3:13.88 | Tie-out | scene18.png |
| 3:23.00 | Status board | scene19.png |
| 3:25.60 | Architecture | scene20.png |
| 3:45.28 | Business model | scene21.png |
| 4:01.44 | Close | scene22.png |

## Checks and limits

- Ruff: passed for all changed Python files. Git diff whitespace check: passed.
- All 23 captures passed no-placeholder, badge visibility, content bounds and text intersection checks. All scene/sentence timing and preserved-version hash assertions passed.
- Word metadata confirms emitted TTS text; it is not an independent listening review. An optional local ASR check was stopped after slow dependency downloads; no independent transcript or listening verdict is claimed.
- No hosted TestSprite run; this repository has no configured TestSprite project. No live Airwallex/provider/executor acceptance is claimed.

## Reproduce

Start the labelled demo server with DEMO_MODE=video and python -m app.demo.server --port 8765. Then run scripts/make_voiceover.py, scripts/make_vo_track.py, scripts/record_demo.py using the existing virtual environment. The first step now generates each sentence separately. demo/timeline.json is the measured clock; VO.txt slot annotations are historical.
