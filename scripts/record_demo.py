"""Capture demo frames with Playwright and render on the measured narration clock.

Run make_voiceover.py, make_vo_track.py, then this script. Static demo pages are
captured at 1920x1080 and encoded with exact frame counts: no browser startup,
click latency or accumulated sleeps can shift a scene relative to its narration.
The cold-open change is an explicit cue. All scenes retain the disclosure footer.
"""

import json
import re
import shutil

from demo_timeline import OUT, TIMELINE
from make_vo_track import run
from playwright.sync_api import sync_playwright


def main() -> None:
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    take = OUT / "raw-take-v4"
    take.mkdir(exist_ok=True)
    final = OUT / "wiretight-demo.mp4"
    previous = OUT / "wiretight-demo-v3.mp4"
    if final.exists() and not previous.exists():
        shutil.copy2(final, previous)
    clips = []
    layout_checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080},
                                device_scale_factor=1)
        page.goto("http://127.0.0.1:8765/?capture", wait_until="load")
        page.evaluate("document.fonts.ready")
        for scene in timeline:
            page.evaluate("s => { __wt.flip(s.flipped); __wt.go(s.frame); }", scene)
            page.wait_for_timeout(450)  # settle the cold-open CSS pop before capture
            footer = ("Synthetic company data · Airwallex API responses simulated · "
                      "cooling-off shortened for recording")
            assert page.locator("#cap").inner_text() == footer
            assert page.locator("#cap").is_visible()
            assert page.locator("#badge").count() == 0
            rendered_text = page.locator("body").inner_text()
            (take / f"scene{scene['id']:02d}.txt").write_text(rendered_text, encoding="utf-8")
            assert not re.search("demo|mock|simulated", rendered_text.replace(footer, ""), re.I)
            assert "placeholder" not in page.locator("body").inner_text().lower()
            assert page.evaluate("""() => [...document.querySelectorAll('#stage .frame *')]
                .every(e => { const r=e.getBoundingClientRect();
                    return r.right<=1920 && r.bottom<=1010 && r.left>=0 && r.top>=0; })""")
            scene["title"] = page.evaluate("__wt.title()")
            overlaps = page.evaluate("""() => {
                const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
                const boxes=[];
                while(walker.nextNode()) {
                    const n=walker.currentNode;
                    const tag=n.parentElement.tagName;
                    if(!n.textContent.trim() || ['SCRIPT','STYLE'].includes(tag))
                        continue;
                    const range=document.createRange(); range.selectNodeContents(n);
                    for(const r of range.getClientRects()) if(r.width>0 && r.height>0)
                        boxes.push({text:n.textContent.trim(),x:r.x,y:r.y,
                                    right:r.right,bottom:r.bottom});
                }
                const hits=[];
                for(let i=0;i<boxes.length;i++) for(let j=i+1;j<boxes.length;j++) {
                    const a=boxes[i],b=boxes[j];
                    if(Math.min(a.right,b.right)-Math.max(a.x,b.x)>2 &&
                       Math.min(a.bottom,b.bottom)-Math.max(a.y,b.y)>2)
                        hits.push({a,b});
                }
                return hits;
            }""")
            layout_checks.append({"scene": scene["id"], "title": scene["title"],
                                  "overlaps": overlaps})
            (take / "layout-checks.json").write_text(
                json.dumps(layout_checks, indent=2) + "\n", encoding="utf-8",
            )
            png = take / f"scene{scene['id']:02d}.png"
            page.screenshot(path=str(png))
            print(f"{scene['start']:7.2f}s {scene['title']}", flush=True)
        browser.close()
    assert not any(c["overlaps"] for c in layout_checks), f"Text overlap: {take}/layout-checks.json"
    for scene in timeline:
        png = take / f"scene{scene['id']:02d}.png"
        clip = take / f"scene{scene['id']:02d}.mp4"
        run(["ffmpeg", "-y", "-loop", "1", "-framerate", "25", "-i", str(png),
             "-frames:v", str(scene["frames"]), "-c:v", "libx264", "-preset", "fast",
             "-crf", "18", "-pix_fmt", "yuv420p", str(clip)])
        clips.append(f"file '{clip.as_posix()}'")
    filelist = take / "concat.txt"
    filelist.write_text("\n".join(clips), encoding="utf-8")
    rendered = take / "wiretight-demo-v4.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(filelist),
         "-i", str(OUT / "wiretight-vo.wav"), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         str(rendered)])
    shutil.copy2(rendered, final)
    TIMELINE.write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {final}")


if __name__ == "__main__":
    main()
