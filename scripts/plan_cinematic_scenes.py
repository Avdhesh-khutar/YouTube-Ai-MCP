#!/usr/bin/env python3
"""Create scene-by-scene cinematic image prompts from a narration script.

This is a deterministic prompt planner, not an AI image generator. Feed the prompts
to a local/open-source image model such as an SDXL workflow, then save outputs as
assets/cinematic-scenes/scene-01.png, scene-02.png, etc.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRIPT = ROOT / "assets" / "cinematic-scenes" / "script.txt"
DEFAULT_OUTPUT = ROOT / "dist-cinematic"


def split_scenes(text: str, max_scenes: int) -> list[str]:
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        for sentence in re.split(r"(?<=[.!?।])\s+", paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if chunks and len(chunks[-1]) < 100:
                chunks[-1] += " " + sentence
            else:
                chunks.append(sentence)
    if len(chunks) > max_scenes:
        chunks = [
            " ".join(chunks[round(i * len(chunks) / max_scenes):round((i + 1) * len(chunks) / max_scenes)])
            for i in range(max_scenes)
        ]
    return chunks


def build_prompt(index: int, narration: str) -> dict[str, str | int]:
    prompt = (
        "Create one photorealistic cinematic documentary film still for a Hindi YouTube video. "
        "16:9 landscape composition, realistic lighting, detailed environment, natural human anatomy, "
        "subtle atmospheric depth, premium film color grading, strong visual storytelling, "
        "clear subject separation, no text, no letters, no logos, no watermark. "
        f"Scene {index} should visually communicate this narration idea: {narration}"
    )
    negative = (
        "text, typography, subtitles, watermark, logo, low resolution, blurry, oversaturated, "
        "plastic skin, distorted face, extra fingers, malformed hands, duplicate people, artifacts"
    )
    return {"scene": index, "narration": narration, "image_prompt": prompt, "negative_prompt": negative}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-scenes", type=int, default=12)
    args = parser.parse_args()
    if not args.script.is_file():
        parser.error(f"Script not found: {args.script}. Add a Hindi narration at that path or pass --script.")
    if not 2 <= args.max_scenes <= 40:
        parser.error("--max-scenes must be between 2 and 40")
    text = args.script.read_text(encoding="utf-8").strip()
    if len(text) < 80:
        parser.error("Narration script must contain at least 80 characters.")
    scenes = [build_prompt(i, line) for i, line in enumerate(split_scenes(text, args.max_scenes), 1)]
    args.output.mkdir(parents=True, exist_ok=True)
    json_path = args.output / "scene-prompts.json"
    md_path = args.output / "scene-prompts.md"
    json_path.write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    sections = ["# Cinematic scene prompts", "", "Generate each image with your chosen local/open-source model. Save images as assets/cinematic-scenes/scene-01.png, etc.", ""]
    for item in scenes:
        sections += [
            f"## Scene {item['scene']}", "",
            f"**Narration idea:** {item['narration']}", "",
            "**Image prompt:**", str(item["image_prompt"]), "",
            "**Negative prompt:**", str(item["negative_prompt"]), "",
        ]
    md_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"Created {len(scenes)} scene prompts:")
    print(md_path)
    print(json_path)
    print("No images, video, or uploads were generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
