#!/usr/bin/env python3
"""Prepare offline Hindi narration and scene-level SRT captions from a validated scene plan.

Requires espeak-ng (or espeak) and ffmpeg. Captions are aligned to each rendered
scene's planned time, not forced-aligned to phoneme/word timestamps.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from scripts.validate_scene_plan import ScenePlanError, validate_scene_plan
except ModuleNotFoundError:
    from validate_scene_plan import ScenePlanError, validate_scene_plan


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, rem = divmod(milliseconds, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def prepare(plan_path: Path, output_dir: Path, min_minutes: float = 8,
            max_minutes: float = 10, voice: str = "hi") -> tuple[Path, Path]:
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read scene plan: {exc}") from exc
    try:
        validate_scene_plan(plan, min_minutes, max_minutes)
    except ScenePlanError as exc:
        raise ValueError(f"Invalid scene plan: {exc}") from exc

    speaker = shutil.which("espeak-ng") or shutil.which("espeak")
    ffmpeg = shutil.which("ffmpeg")
    if not speaker or not ffmpeg:
        raise RuntimeError("Offline narration needs espeak-ng (or espeak) and ffmpeg installed.")
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files: list[Path] = []
    captions: list[str] = []
    elapsed = 0.0
    with tempfile.TemporaryDirectory(prefix="hindi-narration-") as temp:
        temp_dir = Path(temp)
        for index, scene in enumerate(plan["scenes"], 1):
            text = str(scene["narration"]).strip()
            if not text:
                raise ValueError(f"Scene {scene['scene_id']} has empty narration.")
            audio = temp_dir / f"part-{index:03d}.wav"
            result = subprocess.run(
                [speaker, "-v", voice, "-s", "145", "-w", str(audio), text],
                capture_output=True, text=True, check=False,
            )
            if result.returncode != 0 or not audio.is_file() or audio.stat().st_size == 0:
                raise RuntimeError(f"Offline TTS failed for {scene['scene_id']}: {result.stderr[-500:]}")
            audio_files.append(audio)
            end = elapsed + float(scene["duration_seconds"])
            captions.append(
                f"{index}\\n{timestamp(elapsed)} --> {timestamp(end)}\\n{text}\\n"
            )
            elapsed = end

        concat = temp_dir / "concat.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\\n" for p in audio_files), encoding="utf-8")
        narration = output_dir / "voiceover.wav"
        result = subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
             "-ac", "2", "-ar", "44100", str(narration)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0 or not narration.is_file() or narration.stat().st_size == 0:
            raise RuntimeError(f"Could not concatenate narration audio: {result.stderr[-1000:]}")
    subtitle_path = output_dir / "captions.srt"
    subtitle_path.write_text("\\n".join(captions) + "\\n", encoding="utf-8")
    return narration, subtitle_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("assets/cinematic-scenes"))
    parser.add_argument("--min-minutes", type=float, default=8)
    parser.add_argument("--max-minutes", type=float, default=10)
    parser.add_argument("--voice", default="hi", help="eSpeak voice code (default: hi)")
    args = parser.parse_args()
    try:
        narration, subtitles = prepare(args.scene_plan, args.output, args.min_minutes, args.max_minutes, args.voice)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Narration: {narration}")
    print(f"Scene-level subtitles: {subtitles}")
    print("Note: subtitle timing follows planned scene boundaries; it is not word-level forced alignment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
