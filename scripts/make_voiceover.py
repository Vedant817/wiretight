"""One-shot helper: generate the demo voiceover per segment with edge-tts.

Writes one mp3 per segment into demo/vo-segments/ named segNN.mp3, using the
paragraphs from demo/VO.txt (the text after "Segment N (...):" lines).
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import edge_tts

VOICE = "en-US-AndrewNeural"
RATE = "+0%"
ROOT = Path(__file__).resolve().parent.parent
VO_TEXT = ROOT / "demo" / "VO.txt"
OUT_DIR = ROOT / "demo" / "vo-segments"


async def main() -> None:
    text = VO_TEXT.read_text(encoding="utf-8")
    parts = re.split(r"^Segment (\d+) \(slot [^)]+\):\s*$", text, flags=re.MULTILINE)
    # parts: [preamble, "0", paragraph0, "1", paragraph1, ...]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(1, len(parts), 2):
        seg = int(parts[i])
        paragraph = " ".join(parts[i + 1].split())
        if not paragraph:
            continue
        out = OUT_DIR / f"seg{seg:02d}.mp3"
        tts = edge_tts.Communicate(paragraph, VOICE, rate=RATE)
        await tts.save(str(out))
        print(f"seg{seg:02d}: {out.name} ({len(paragraph)} chars)")


if __name__ == "__main__":
    asyncio.run(main())
