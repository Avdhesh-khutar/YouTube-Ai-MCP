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
            max_minutes: float = 10, voice: str = "hi",
            min_speech_coverage: float = 0.20) -> tuple[Path, Path]:
    """Create voiceover and SRT; reject scenes where spoken audio is too short.

    min_speech_coverage is the fraction of each planned scene that must contain
    generated speech before padding. This guards against a long, mostly-silent file.
    """
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read scene plan: {exc}") from exc
    try:
        validate_scene_plan(plan, min_minutes, max_minutes)
    except ScenePlanError as exc:
        raise ValueError(f"Invalid scene plan: {exc}") from exc

    if not 0.0 <= min_speech_coverage <= 1.0:
        raise ValueError("Minimum speech coverage must be between 0 and 1.")
    speaker = shutil.which("espeak-ng") or shutil.which("espeak")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not speaker or not ffmpeg or not ffprobe:
        raise RuntimeError("Offline narration needs espeak-ng (or espeak), ffmpeg, and ffprobe installed.")
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files: list[Path] = []
    captions: list[str] = []
    coverage_rows: list[dict[str, object]] = []
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
            duration = float(scene["duration_seconds"])
            measured = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
                capture_output=True, text=True, check=False,
            )
            if measured.returncode != 0:
                raise RuntimeError(
                    f"ffprobe could not measure speech for {scene['scene_id']}: "
                    f"{measured.stderr[-500:]}"
                )
            try:
                spoken_seconds = float(measured.stdout.strip())
            except ValueError as exc:
                raise RuntimeError(f"Could not measure speech duration for {scene['scene_id']}: {measured.stderr[-500:]}") from exc
            coverage = spoken_seconds / duration if duration > 0 else 0.0
            if measured.returncode != 0 or coverage < min_speech_coverage:
                raise ValueError(
                    f"Scene {scene['scene_id']} has only {spoken_seconds:.1f}s of speech "
                    f"for {duration:.1f}s planned ({coverage:.0%} coverage); "
                    f"minimum is {min_speech_coverage:.0%}. Add narration text or shorten the scene. "
                    "Playback speed remains unchanged."
                )
            print(f"{scene['scene_id']}: {spoken_seconds:.1f}s speech / {duration:.1f}s scene ({coverage:.0%})")
            if spoken_seconds > duration + 0.25:
                raise ValueError(
                    f"Scene {scene['scene_id']} narration is {spoken_seconds:.1f}s but the "
                    f"scene is only {duration:.1f}s; audio would be cut off. Increase the "
                    "scene duration or shorten the narration. Playback speed remains unchanged."
                )
            coverage_rows.append({
                "scene_id": scene["scene_id"],
                "speech_seconds": round(spoken_seconds, 3),
                "scene_seconds": duration,
                "speech_coverage": round(coverage, 4),
                "minimum_required": min_speech_coverage,
                "passes": coverage >= min_speech_coverage,
            })
            padded_audio = temp_dir / f"padded-{index:03d}.wav"
            padded = subprocess.run(
                [ffmpeg, "-y", "-i", str(audio), "-af", "apad", "-t", str(duration),
                 "-ac", "2", "-ar", "44100", str(padded_audio)],
                capture_output=True, text=True, check=False,
            )
            if padded.returncode != 0 or not padded_audio.is_file() or padded_audio.stat().st_size == 0:
                raise RuntimeError(f"Could not fit narration to scene {scene['scene_id']}: {padded.stderr[-1000:]}")
            audio_files.append(padded_audio)
            end = elapsed + duration
            captions.append(
                f"{index}\n{timestamp(elapsed)} --> {timestamp(end)}\n{text}\n"
            )
            elapsed = end

        concat = temp_dir / "concat.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in audio_files), encoding="utf-8")
        narration = output_dir / "voiceover.wav"
        result = subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
             "-ac", "2", "-ar", "44100", str(narration)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0 or not narration.is_file() or narration.stat().st_size == 0:
            raise RuntimeError(f"Could not concatenate narration audio: {result.stderr[-1000:]}")
    subtitle_path = output_dir / "captions.srt"
    subtitle_path.write_text("\n".join(captions) + "\n", encoding="utf-8")
    coverage_report = output_dir / "narration-coverage.json"
    coverage_report.write_text(json.dumps({
        "voice": voice,
        "speech_rate_wpm": 145,
        "playback_speed_adjusted": False,
        "minimum_speech_coverage": min_speech_coverage,
        "scenes": coverage_rows,
        "all_scenes_pass": all(row["passes"] for row in coverage_rows),
        "note": "Coverage measures generated TTS duration before padding; subtitle timing is scene-level, not word-level alignment.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Narration coverage report: {coverage_report}")
    return narration, subtitle_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("assets/cinematic-scenes"))
    parser.add_argument("--min-minutes", type=float, default=8)
    parser.add_argument("--max-minutes", type=float, default=10)
    parser.add_argument("--voice", default="hi", help="eSpeak voice code (default: hi)")
    parser.add_argument("--min-speech-coverage", type=float, default=0.20,
                        help="Minimum fraction of each scene containing speech (default: 0.20)")
    args = parser.parse_args()
    try:
        narration, subtitles = prepare(args.scene_plan, args.output, args.min_minutes, args.max_minutes, args.voice, args.min_speech_coverage)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Narration: {narration}")
    print(f"Scene-level subtitles: {subtitles}")
    print("Note: subtitle timing follows planned scene boundaries; it is not word-level forced alignment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
