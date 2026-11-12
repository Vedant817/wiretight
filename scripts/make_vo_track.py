"""One-shot helper: pad each VO segment to its script slot and concatenate.

Slot lengths come from the recording timeline (segments group the demo page's
sub-frames); total 288.5 s = 4:48.5, inside the 4:55 cap. Output:
demo/wiretight-vo.wav (mono 44.1 kHz) and demo/wiretight-vo.mp3.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEG = ROOT / "demo" / "vo-segments"
OUT = ROOT / "demo"
# segment -> slot seconds (matches the recording timeline; total 277 s = 4:37,
# under the 4:55 cap. Segment 5 and 8 are short beats in the script's cut list.)
SLOTS: dict[int, float] = {
    0: 10.0, 1: 40.0, 2: 29.0, 3: 15.5, 4: 24.0, 5: 7.0, 6: 24.0, 7: 24.0,
    8: 7.0, 9: 26.0, 10: 12.0, 11: 12.0, 12: 19.0, 13: 15.5, 14: 7.0,
}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def main() -> None:
    list_file = OUT / "vo-list.txt"
    lines: list[str] = []
    total = 0.0
    for seg, slot in SLOTS.items():
        src = SEG / f"seg{seg:02d}.mp3"
        padded = SEG / f"seg{seg:02d}p.wav"
        run([
            "ffmpeg", "-y", "-i", str(src),
            "-af", f"aresample=44100,apad=whole_dur={slot}",
            "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(padded),
        ])
        lines.append(f"file '{padded.as_posix()}'")
        total += slot
    list_file.write_text("\n".join(lines), encoding="utf-8")
    wav = OUT / "wiretight-vo.wav"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:a", "pcm_s16le", str(wav),
    ])
    mp3 = OUT / "wiretight-vo.mp3"
    run([
        "ffmpeg", "-y", "-i", str(wav),
        "-c:a", "libmp3lame", "-b:a", "128k", str(mp3),
    ])
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(wav)], capture_output=True, text=True,
    ).stdout.strip()
    print(f"slots total {total:.1f}s; vo.wav duration {probe}s")


if __name__ == "__main__":
    main()
