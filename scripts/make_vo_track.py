"""Measure speech clips, append short pauses, and write the shared scene clock."""

import json
import math
import subprocess

from demo_timeline import FINAL_HOLD, OUT, PAUSE, SEG, TIMELINE, scenes


def run(args: list[str]) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def main() -> None:
    timeline = scenes()
    files = []
    start = 0.0
    for i, scene in enumerate(timeline):
        src = SEG / f"scene{i:02d}.mp3"
        speech = SEG / f"scene{i:02d}-speech.wav"
        # Trim only boundary silence. Never cut speech to fit an allotted slot.
        run(["ffmpeg", "-y", "-i", str(src), "-af",
             "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,"
             "areverse,silenceremove=start_periods=1:start_threshold=-50dB:"
             "start_silence=0.05,areverse", "-ar", "48000", "-ac", "1", str(speech)])
        duration = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", str(speech)]).strip())
        pause = FINAL_HOLD if i == len(timeline) - 1 else PAUSE
        # Round up to 25fps boundaries so audio and visuals share exact cuts.
        frames = math.ceil((duration + pause) * 25)
        total = frames / 25
        padded = SEG / f"scene{i:02d}p.wav"
        run(["ffmpeg", "-y", "-i", str(speech), "-af", f"apad,atrim=duration={total}",
             "-ar", "48000", "-ac", "1", str(padded)])
        files.append(f"file '{padded.as_posix()}'")
        scene.update(start=round(start, 3), speech_duration=duration, duration=total,
                     frames=frames)
        start += total
    assert start < 300, f"Narration exceeds five minutes: {start}"
    TIMELINE.write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    filelist = SEG / "concat.txt"
    filelist.write_text("\n".join(files), encoding="utf-8")
    wav = OUT / "wiretight-vo.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(filelist),
         "-c:a", "pcm_s16le", str(wav)])
    run(["ffmpeg", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "128k",
         str(OUT / "wiretight-vo.mp3")])
    print(f"{len(timeline)} scene cues; {start:.2f}s total; timeline: {TIMELINE}")


if __name__ == "__main__":
    main()
