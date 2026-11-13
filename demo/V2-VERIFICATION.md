# Wiretight demo v2 verification

Local render: 2026-11-13. Duration **247.72 seconds (4:07.72)**. 1920x1080, 25 fps, H.264 / AAC. Both stream durations match; 6193 video frames.

The original v1 is preserved as `demo/wiretight-demo-v1.mp4` (SHA-256 `8e989c78e127511df585f52ce800c21209c2ce5f3815c7d3086534b7074fd8ec`). Both MP4 files and capture intermediates are ignored by Git.

Playwright captures all 22 static demo pages (23 cues including the cold-open change). ffmpeg encodes those captures using measured complete edge-tts clip durations, rounded to 25 fps boundaries. This replaces real-time clicking and its accumulated timing drift. Each scene appears at the start of its own narration; the normal pause is 0.4 seconds plus at most 0.04 seconds of frame rounding. Only the final scene adds a 2.5-second hold.

The transcript is preserved verbatim across scene clips, checked before generation. The Why now? phrase is included in full. TTS input alone respells tranche as trahnsh. Source/assumption/repository footnotes and tags increased from 13px to 16px. The title developer note is removed; the persistent SIMULATED DEMO DATA badge is checked on every capture. Real seed/core calculations and mock labels remain intact.

## Validation

- ffprobe: H.264 1920x1080 25 fps, AAC; both streams 247.720000 s.
- Full video/audio decode plus `silencedetect=noise=-40dB:d=2.5`: only 245.172-247.723 s (2.55052 s), the final card hold. No decode errors. Detector end extends about 3 ms beyond container duration due to decoded AAC samples.
- All 23 Playwright captures: badge text and visibility, content bounds within the 1080p canvas. Title and dense fingerprint frame visually inspected.
- Focused existing tests: 62 passed (offline guarantees, callback rules, lock). Ruff and git diff whitespace checks passed.
- TestSprite: no Wiretight project configured; no hosted TestSprite run. Shared preview snapshot timed out twice; capture and checks used local Playwright. No live provider or executor acceptance is claimed.
- The pronunciation change is a TTS respelling; no independent listening review was performed.

## Scene starts

| Start | Scene |
|---|---|
| 0:00.00 | Cold open |
| 0:02.36 | Cold open - bank details changed / VOID |
| 0:06.44 | Title |
| 0:16.84 | Problem - the numbers |
| 0:48.56 | Who it is for |
| 0:59.80 | Why now |
| 1:19.68 | The rule |
| 1:36.20 | The run and the plan |
| 2:01.72 | The email |
| 2:07.12 | The lock fires (1 of 2) |
| 2:14.08 | Plan diff - surgical |
| 2:22.52 | Rule 3 - requester cannot confirm |
| 2:25.60 | Priya calls the number on file |
| 2:32.68 | Request rejected, real invoice paid |
| 2:41.48 | The payout comes back |
| 2:45.56 | The genuine request (2 of 2) |
| 2:54.08 | Cooling-off, sign-offs, cap |
| 3:01.72 | Tranche 1 out, tranche 2 held |
| 3:13.52 | Tie-out |
| 3:22.56 | Status board |
| 3:24.92 | Architecture |
| 3:44.68 | Business model |
| 4:00.96 | Close |

## Reproduce

Start the demo server with `DEMO_MODE=video` and `python -m app.demo.server --port 8765`. With the local environment containing Playwright, edge-tts and ffmpeg, run:

```powershell
.\.venv\Scripts\python.exe scripts\make_voiceover.py
.\.venv\Scripts\python.exe scripts\make_vo_track.py
.\.venv\Scripts\python.exe scripts\record_demo.py
ffprobe -v error -show_streams -show_format demo\wiretight-demo.mp4
ffmpeg -hide_banner -i demo\wiretight-demo.mp4 -af silencedetect=noise=-40dB:d=2.5 -f null NUL
```

The legacy slot annotations in VO.txt are historical; demo/timeline.json is the measured v2 clock. Generated screenshots, clips and raw verification output are under ignored demo/raw-take/.
