"""Generate complete scene narration with edge-tts, without fixed-slot cuts."""

import argparse
import asyncio

import edge_tts
from demo_timeline import SEG, scenes


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true",
                        help="reuse completed clips from this take")
    args = parser.parse_args()
    SEG.mkdir(parents=True, exist_ok=True)
    limit = asyncio.Semaphore(3)

    async def generate(scene: dict) -> None:
        out = SEG / f"scene{scene['id']:02d}.mp3"
        if args.resume and out.exists() and out.stat().st_size:
            return
        # Only TTS input is respelled; displayed terms and transcript stay intact.
        spoken = scene["text"].replace("tranche", "trahnsh")
        async with limit:
            await edge_tts.Communicate(spoken, "en-US-AndrewNeural", rate="-8%").save(str(out))
        print(f"{out.name}: {scene['text']}", flush=True)

    await asyncio.gather(*(generate(scene) for scene in scenes()))


if __name__ == "__main__":
    asyncio.run(main())
