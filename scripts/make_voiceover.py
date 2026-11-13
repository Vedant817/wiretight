"""Generate a complete edge-tts clip per sentence, with explicit pause boundaries."""

import asyncio

import edge_tts
from demo_timeline import OUT, SEG, scenes, sentences, spoken_text


async def main() -> None:
    SEG.mkdir(parents=True, exist_ok=True)
    limit = asyncio.Semaphore(3)

    async def generate(scene: dict, index: int, text: str) -> None:
        name = f"v3-scene{scene['id']:02d}-sentence{index:02d}"
        async with limit:
            await edge_tts.Communicate(
                spoken_text(text), "en-US-AndrewNeural", rate="-8%", boundary="WordBoundary",
            ).save(str(SEG / f"{name}.mp3"), str(SEG / f"{name}.jsonl"))
        print(f"{name}: {spoken_text(text)}", flush=True)

    timeline = scenes()
    (OUT / "VO-v3-spoken.txt").write_text(
        "\n\n".join(spoken_text(s["text"]) for s in timeline) + "\n", encoding="utf-8",
    )
    await asyncio.gather(*(generate(scene, j, text) for scene in timeline
                           for j, text in enumerate(sentences(scene["text"]))))


if __name__ == "__main__":
    asyncio.run(main())
