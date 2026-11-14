"""Measure complete sentence clips and write the shared narration/scene clock."""

import json
import math
import subprocess

from demo_timeline import (
    FINAL_HOLD,
    OUT,
    PAUSE,
    SEG,
    SENTENCE_PAUSE,
    TIMELINE,
    scenes,
    sentences,
    spoken_text,
)


def run(args: list[str]) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def main() -> None:
    timeline = scenes()
    files = []
    start = 0.0
    for i, scene in enumerate(timeline):
        sentence_list = sentences(scene["text"])
        clock = 0.0
        scene["sentences"] = []
        for j, text in enumerate(sentence_list):
            name = f"v3-scene{i:02d}-sentence{j:02d}"
            src = SEG / f"{name}.mp3"
            speech = SEG / f"{name}-speech.wav"
            # Trim boundary silence only. All spoken samples remain uncut.
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(src),
                    "-af",
                    "silenceremove=start_periods=1:start_threshold=-60dB,"
                    "areverse,silenceremove=start_periods=1:start_threshold=-60dB,areverse",
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    str(speech),
                ]
            )
            duration = float(
                run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "csv=p=0",
                        str(speech),
                    ]
                ).strip()
            )
            last_sentence = j == len(sentence_list) - 1
            last_scene = i == len(timeline) - 1
            pause = (FINAL_HOLD if last_scene else PAUSE) if last_sentence else SENTENCE_PAUSE
            total = duration + pause
            if last_sentence:
                total = math.ceil((clock + total) * 25) / 25 - clock
            padded = SEG / f"{name}p.wav"
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(speech),
                    "-af",
                    f"apad,atrim=duration={total}",
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    str(padded),
                ]
            )
            files.append(f"file '{padded.as_posix()}'")
            scene["sentences"].append(
                {
                    "text": spoken_text(text),
                    "start": round(start + clock, 6),
                    "speech_duration": duration,
                    "pause": total - duration,
                    "clip": src.name,
                }
            )
            clock += total
        scene.update(start=round(start, 3), duration=round(clock, 3), frames=round(clock * 25))
        start += clock
    assert start < 285, f"Narration exceeds 4:45: {start}"
    TIMELINE.write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    filelist = SEG / "v3-concat.txt"
    filelist.write_text("\n".join(files), encoding="utf-8")
    wav = OUT / "wiretight-vo.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(filelist),
            "-c:a",
            "pcm_s16le",
            str(wav),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(OUT / "wiretight-vo.mp3"),
        ]
    )
    print(f"{len(timeline)} scene cues; {start:.2f}s total; timeline: {TIMELINE}")


if __name__ == "__main__":
    main()
