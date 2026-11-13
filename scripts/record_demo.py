"""Capture demo frames with Playwright and render on the measured narration clock.

Run make_voiceover.py, make_vo_track.py, then this script. Static demo pages are
captured at 1920x1080 and encoded with exact frame counts: no browser startup,
click latency or accumulated sleeps can shift a scene relative to its narration.
The cold-open change is an explicit cue. All scenes retain the simulated badge.
"""

import json
import shutil

from demo_timeline import OUT, TIMELINE
from make_vo_track import run
from playwright.sync_api import sync_playwright


def main() -> None:
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    take = OUT / "raw-take"
    take.mkdir(exist_ok=True)
    final = OUT / "wiretight-demo.mp4"
    previous = OUT / "wiretight-demo-v1.mp4"
    if final.exists() and not previous.exists():
        shutil.copy2(final, previous)
    clips = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080},
                                device_scale_factor=1)
        page.goto("http://127.0.0.1:8765/?capture", wait_until="load")
        page.evaluate("document.fonts.ready")
        for scene in timeline:
            page.evaluate("s => { __wt.flip(s.flipped); __wt.go(s.frame); }", scene)
            page.wait_for_timeout(450)  # settle the cold-open CSS pop before capture
            assert "SIMULATED DEMO DATA" in page.locator("#badge").inner_text()
            assert page.locator("#badge").is_visible()
            assert page.evaluate("""() => [...document.querySelectorAll('#stage .frame *')]
                .every(e => { const r=e.getBoundingClientRect();
                    return r.right<=1920 && r.bottom<=1010 && r.left>=0 && r.top>=0; })""")
            scene["title"] = page.evaluate("__wt.title()")
            png = take / f"scene{scene['id']:02d}.png"
            page.screenshot(path=str(png))
            clip = take / f"scene{scene['id']:02d}.mp4"
            run(["ffmpeg", "-y", "-loop", "1", "-framerate", "25", "-i", str(png),
                 "-frames:v", str(scene["frames"]), "-c:v", "libx264", "-preset", "fast",
                 "-crf", "18", "-pix_fmt", "yuv420p", str(clip)])
            clips.append(f"file '{clip.as_posix()}'")
            print(f"{scene['start']:7.2f}s {scene['title']}", flush=True)
        browser.close()
    filelist = take / "concat.txt"
    filelist.write_text("\n".join(clips), encoding="utf-8")
    rendered = take / "wiretight-demo-v2.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(filelist),
         "-i", str(OUT / "wiretight-vo.wav"), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         str(rendered)])
    shutil.copy2(rendered, final)
    TIMELINE.write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {final}")


if __name__ == "__main__":
    main()
