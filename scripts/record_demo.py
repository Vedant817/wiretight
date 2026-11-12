"""One-shot helper: record the demo walkthrough headlessly with Playwright.

Steps through the demo page's 22 frames by clicking "Next" once per frame and
holding each frame for its script slot, with the context recording at
1920x1080. Closing the context flushes the webm; it lands in
demo/raw-recording.webm. ``--test`` runs a fast 1 s-per-frame pass for
pipeline verification only.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
URL = "http://127.0.0.1:8765/"
#: Per-frame hold, seconds. Order matches the demo page's FRAMES array.
#: Totals 272 s = 4:32, matching the VO track's slot lengths.
HOLDS: tuple[float, ...] = (
    10.0,  # 0  cold open (VOID flip fires at 5 s inside the page)
    8.0, 32.0,  #      title | stats (VO segment 1)
    12.0, 17.0,  #     persona | why now (VO segment 2)
    15.5,  # 5    rule + honesty note
    24.0,  # 6    run plan
    7.0,  # 7     the email
    12.0, 12.0,  #    incident diff | plan diff (VO segment 6)
    8.0, 8.0, 8.0,  #  requester blocked | Priya | rejected (VO segment 7)
    7.0,  # 13    transfer timeline
    13.0, 13.0,  #    recovery email | cooling-off (VO segment 9)
    12.0,  # 16   tranches
    6.0, 6.0,  #      tie-out | status board (VO segment 11)
    19.0,  # 19   architecture
    15.5,  # 20   business model
    7.0,  # 21    close
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="1 s per frame, pipeline check")
    args = parser.parse_args()
    holds = tuple(1.0 for _ in HOLDS) if args.test else HOLDS

    take_dir = ROOT / "demo" / "raw-take"
    shutil.rmtree(take_dir, ignore_errors=True)
    take_dir.mkdir(parents=True, exist_ok=True)
    final = ROOT / "demo" / "raw-recording.webm"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(take_dir),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.goto(URL, wait_until="load")
        page.wait_for_timeout(2000)
        for i, hold in enumerate(holds):
            if i > 0:
                page.click("#next")
            page.wait_for_timeout(int(hold * 1000))
        video = page.video
        assert video is not None
        raw_path = video.path()
        context.close()
        browser.close()

    src = Path(raw_path)
    shutil.move(str(src), final)
    print(f"saved {final} ({final.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
