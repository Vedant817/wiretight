"""Scene boundaries in the unchanged VO transcript; shared by media helpers."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo"
SEG = OUT / "vo-segments"
TIMELINE = OUT / "timeline.json"
PAUSE = 0.7
SENTENCE_PAUSE = 0.3
FINAL_HOLD = 2.5


def sentences(text: str) -> list[str]:
    """Split at sentence punctuation, preserving every word and question mark."""
    return re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)


def spoken_text(text: str) -> str:
    """Pronunciation/wording overrides apply only to synthesized speech."""
    return text.replace("Halden", "Hall-den").replace("capped tranche", "capped payment")

# Segment, page frame, text that starts this scene (None means segment start).
CUES = (
    (0, 0, None), (0, 0, "Then the bank details changed."),
    (1, 1, None), (1, 2, "In AFP's 2026 survey"),
    (2, 3, None), (2, 4, "Why now?"),
    (3, 5, None), (4, 6, None), (5, 7, None),
    (6, 8, None), (6, 9, "Only this payment is blocked."),
    (7, 10, None), (7, 11, "Someone else calls"), (7, 12, "The request is rejected,"),
    (8, 13, None), (9, 14, None), (9, 15, "Same lock:"),
    (10, 16, None), (11, 17, None), (11, 18, "Then a journal export"),
    (12, 19, None), (13, 20, None), (14, 21, None),
)


def scenes() -> list[dict]:
    text = (OUT / "VO.txt").read_text(encoding="utf-8")
    parts = re.split(r"^Segment (\d+) \(slot [^)]+\):\s*$", text, flags=re.MULTILINE)
    paragraphs = {int(parts[i]): " ".join(parts[i + 1].split())
                  for i in range(1, len(parts), 2)}
    result = []
    for i, (segment, frame, cue) in enumerate(CUES):
        paragraph = paragraphs[segment]
        start = paragraph.index(cue) if cue else 0
        end = len(paragraph)
        if i + 1 < len(CUES) and CUES[i + 1][0] == segment:
            end = paragraph.index(CUES[i + 1][2])
        result.append({"id": i, "segment": segment, "frame": frame,
                       "text": paragraph[start:end].strip(), "flipped": i > 0})
    # Fail before generation if a boundary drops or repeats any words.
    for segment, paragraph in paragraphs.items():
        assert " ".join(s["text"] for s in result if s["segment"] == segment) == paragraph
    return result
