#!/usr/bin/env python3
"""Generate scene-based Hindi narration with a user-supplied Piper ONNX voice.

No model is downloaded automatically. The caller supplies a licensed model file
and its matching .onnx.json config. Piper CLI, FFmpeg and ffprobe must be present.
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
    ms = max(0, round(seconds * 1000))
    hours, rest = divmod(ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    whole, millis = divmod(rest, 1000)
    return f"{hours:02}:{minutes:02}:{whole:02},{millis:03}"


def prepare(plan_path: Path, model_path: Path, output_dir: Path,
            config_path: Path | None = None, min_minutes: float = 8,
            max_minutes: float = 10, min_speech_coverage: float = 0.20,
            piper_bin: str = "piper") -> tuple[Path, Path]:
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read scene plan: {exc}") from exc
    try:
        validate_scene_plan(plan, min_minutes, max_minutes)
    except ScenePlanError as exc:
        raise ValueError(f"Invalid scene plan: {exc}") from exc

    config_path = config_path or Path(str(model_path) + ".json")
    if not model_path.is_file():
        raise FileNotFoundError(f"Piper model not found: {model_path}")
    if not config_path.is_file():
        raise FileNotFoundError(f"Piper model config not found: {config_path}")
    piper = shutil.which(piper_bin)
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not piper or not ffmpeg or not ffprobe:
        raise RuntimeError("Piper narration needs the Piper CLI, FFmpeg and ffprobe installed.")

    output_dir.mkdir(parents=True, exist_ok=True)
    audio_parts: list[Path] = []
    caption_blocks: list[str] = []
    coverage: list[dict[str, object]] = []
    elapsed = 0.0

    with tempfile.TemporaryDirectory(prefix="piper-hindi-") as temp:
        temp_dir = Path(temp)
        for index, scene in enumerate(plan["scenes"], 1):
            text = str(scene["narration"]).strip()
            if not text:
                raise ValueError(f"Scene {scene['scene_id']} has empty narration.")
            duration = float(scene["duration_seconds"])
            wav = temp_dir / f"scene-{index:03d}.wav"
            generated = subprocess.run(
                [piper, "--model", str(model_path), "--config", str(config_path),
                 "--output_file", str(wav)],
                input=text, capture_output=True, text=True, check=False,
            )
            if generated.returncode != 0 or not wav.is_file() or wav.stat().st_size == 0:
                raise RuntimeError(
                    f"Piper failed for {scene['scene_id']}: {generated.stderr[-1000:]}"
                )
            measured = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(wav)],
                capture_output=True, text=True, check=False,
            )
            if measured.returncode != 0:
                raise RuntimeError(
                    f"ffprobe failed for {scene['scene_id']}: {measured.stderr[-500:]}"
                )
            try:
                speech_seconds = float(measured.stdout.strip())
            except ValueError as exc:
                raise RuntimeError(
                    f"Invalid speech duration for {scene['scene_id']}: {measured.stdout!r}"
                ) from exc
            if speech_seconds <= 0:
                raise RuntimeError(f"Piper produced non-positive duration for {scene['scene_id']}.")
            ratio = speech_seconds / duration if duration > 0 else 0.0
            if ratio < min_speech_coverage:
                raise ValueError(
                    f"Scene {scene['scene_id']} speech coverage is {ratio:.0%}; "
                    f"minimum is {min_speech_coverage:.0%}. Add narration or shorten the scene."
                )
            if speech_seconds > duration + 0.25:
                raise ValueError(
                    f"Scene {scene['scene_id']} narration ({speech_seconds:.1f}s) exceeds "
                    f"scene duration ({duration:.1f}s); shorten narration or extend scene."
                )
            padded = temp_dir / f"padded-{index:03d}.wav"
            pad_result = subprocess.run(
                [ffmpeg, "-y", "-i", str(wav), "-af", "apad", "-t", str(duration),
                 "-ac", "2", "-ar", "44100", str(padded)],
                capture_output=True, text=True, check=False,
            )
            if pad_result.returncode != 0 or not padded.is_file() or padded.stat().st_size == 0:
                raise RuntimeError(
                    f"Could not fit Piper audio to {scene['scene_id']}: {pad_result.stderr[-1000:]}"
                )
            audio_parts.append(padded)
            coverage.append({
                "scene_id": scene["scene_id"],
                "speech_seconds": round(speech_seconds, 3),
                "scene_seconds": duration,
                "speech_coverage": round(ratio, 4),
                "passes": True,
            })
            end = elapsed + duration
            caption_blocks.append(
                f"{index}\n{timestamp(elapsed)} --> {timestamp(end)}\n{text}"
            )
            elapsed = end

        concat = temp_dir / "concat.txt"
        concat.write_text(
            "".join(f"file '{part.as_posix()}'\n" for part in audio_parts),
            encoding="utf-8",
        )
        narration = output_dir / "voiceover.wav"
        joined = subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
             "-ac", "2", "-ar", "44100", str(narration)],
            capture_output=True, text=True, check=False,
        )
        if joined.returncode != 0 or not narration.is_file() or narration.stat().st_size == 0:
            raise RuntimeError(f"Could not join Piper narration: {joined.stderr[-1000:]}")

    subtitles = output_dir / "captions-scene-level.srt"
    subtitles.write_text("\n\n".join(caption_blocks) + "\n", encoding="utf-8")
    report = output_dir / "narration-coverage.json"
    report.write_text(json.dumps({
        "provider": "piper-cli",
        "model": str(model_path),
        "minimum_speech_coverage": min_speech_coverage,
        "scenes": coverage,
        "all_scenes_pass": all(item["passes"] for item in coverage),
        "note": "Scene-level captions only; use align_hindi_captions.py for audio-timed captions.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return narration, subtitles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-plan", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True,
                        help="Piper Hindi male ONNX model, e.g. hi_IN-rohan-medium.onnx")
    parser.add_argument("--model-config", type=Path,
                        help="Matching .onnx.json file; defaults to MODEL.onnx.json")
    parser.add_argument("--output", type=Path, default=Path("assets/cinematic-scenes"))
    parser.add_argument("--min-minutes", type=float, default=8)
    parser.add_argument("--max-minutes", type=float, default=10)
    parser.add_argument("--min-speech-coverage", type=float, default=0.20)
    args = parser.parse_args()
    try:
        audio, captions = prepare(
            args.scene_plan, args.model, args.output, args.model_config,
            args.min_minutes, args.max_minutes, args.min_speech_coverage,
        )
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Piper narration: {audio}")
    print(f"Scene-level captions: {captions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
