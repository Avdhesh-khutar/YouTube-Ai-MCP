#!/usr/bin/env python3
"""Render cinematic YouTube videos from scene images and optional image-to-video clips.

Place scene images in assets/cinematic-scenes/ as scene-01.png, scene-02.png, ...
Optional matching scene-01.mp4 clips replace the still-image animation for those scenes.
This renderer does not generate AI images or videos; use a local/open-source image or
image-to-video tool to create the assets, then render them here.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from scripts.validate_scene_plan import ScenePlanError, validate_scene_plan
except ModuleNotFoundError:  # Support direct execution as a script
    from validate_scene_plan import ScenePlanError, validate_scene_plan

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENES = ROOT / "assets" / "cinematic-scenes"
DEFAULT_OUTPUT = ROOT / "dist-cinematic"
WIDTH, HEIGHT, FPS = 1280, 720, 30


def run(command: list[str]) -> None:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr[-4000:]}"
        )


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def render(scenes_dir: Path, output_dir: Path, seconds_per_scene: float = 5.0,
           scene_plan_path: Path | None = None, min_minutes: float = 8.0,
           max_minutes: float = 10.0) -> Path:
    if not ffmpeg_available():
        raise RuntimeError("FFmpeg is required. Install FFmpeg and retry.")
    images = sorted(
        p for p in scenes_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        and re.fullmatch(r"scene[-_]\d+", p.stem, flags=re.IGNORECASE)
    ) if scenes_dir.exists() else []
    if not images:
        raise RuntimeError(
            f"No scene images found in {scenes_dir}. Add scene-01.png, scene-02.png, etc."
        )

    planned_durations: dict[int, float] = {}
    if scene_plan_path is not None:
        try:
            plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
            validate_scene_plan(plan, min_minutes, max_minutes)
        except (OSError, json.JSONDecodeError, ScenePlanError) as exc:
            raise ValueError(f"Scene plan validation failed: {exc}") from exc
        for scene in plan["scenes"]:
            match = re.fullmatch(r"scene[-_](\\d+)", scene["scene_id"], re.IGNORECASE)
            if not match:
                raise ValueError(f"Scene plan ID must match scene-NN format: {scene['scene_id']}")
            number = int(match.group(1))
            if number in planned_durations:
                raise ValueError(f"Duplicate scene number in plan: {number}")
            planned_durations[number] = float(scene["duration_seconds"])
        image_numbers = {
            int(re.fullmatch(r"scene[-_](\\d+)", image.stem, re.IGNORECASE).group(1))
            for image in images
        }
        if image_numbers != set(planned_durations):
            missing_images = sorted(set(planned_durations) - image_numbers)
            missing_plan = sorted(image_numbers - set(planned_durations))
            raise ValueError(
                f"Scene plan/images do not match. Missing images for {missing_images}; "
                f"missing plan entries for {missing_plan}."
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    scene_rows = []
    for index, image in enumerate(images, start=1):
        clip = image.with_suffix(".mp4")
        segment = output_dir / f"segment-{index:03d}.mp4"
        scene_number = int(re.fullmatch(r"scene[-_](\\d+)", image.stem, re.IGNORECASE).group(1))
        duration = planned_durations.get(scene_number, max(2.0, seconds_per_scene))
        if clip.exists():
            # Use a prepared image-to-video clip when available; otherwise animate the still.
            run([
                "ffmpeg", "-y", "-i", str(clip), "-t", str(duration),
                "-an", "-vf",
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1,format=yuv420p",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                str(segment),
            ])
            motion = "image-to-video clip"
        else:
            frames = int(round(duration * FPS))
            run([
                "ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(image),
                "-vf",
                f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH*2}:{HEIGHT*2},"
                f"zoompan=z='min(zoom+0.0007,1.12)':d=1:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1,format=yuv420p",
                "-t", str(duration), "-an", "-c:v", "libx264",
                "-preset", "medium", "-crf", "20", str(segment),
            ])
            motion = "cinematic Ken Burns zoom"
        segments.append(segment)
        scene_rows.append({"scene": image.name, "motion": motion, "duration_seconds": duration})

    concat_file = output_dir / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in segments),
        encoding="utf-8",
    )
    silent_video = output_dir / "silent.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(silent_video),
    ])

    narration = scenes_dir / "voiceover.mp3"
    if not narration.exists():
        narration = scenes_dir / "voiceover.wav"
    captions = scenes_dir / "captions.srt"
    final_video = output_dir / "cinematic-video.mp4"
    if narration.exists():
        command = [
            "ffmpeg", "-y", "-i", str(silent_video), "-i", str(narration),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
        ]
        if captions.exists():
            command += ["-vf", f"subtitles={captions.as_posix()}"]
        command += ["-movflags", "+faststart", str(final_video)]
    else:
        command = ["ffmpeg", "-y", "-i", str(silent_video)]
        if captions.exists():
            command += ["-vf", f"subtitles={captions.as_posix()}"]
        command += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-an", "-movflags", "+faststart", str(final_video)]
    run(command)

    # Use the first scene as a clean, uncaptioned thumbnail source.
    thumbnail = output_dir / "thumbnail.jpg"
    run([
        "ffmpeg", "-y", "-i", str(images[0]), "-frames:v", "1",
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT}", "-q:v", "2", str(thumbnail),
    ])
    (output_dir / "render-report.json").write_text(
        json.dumps({
            "video": final_video.name,
            "resolution": f"{WIDTH}x{HEIGHT}",
            "fps": FPS,
            "scenes": scene_rows,
            "audio": narration.name if narration.exists() else None,
            "captions": captions.name if captions.exists() else None,
            "upload_enabled": False,
            "notes": "Review image rights, voice, captions, pacing, and thumbnail before any upload.",
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return final_video


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenes", type=Path, default=DEFAULT_SCENES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seconds-per-scene", type=float, default=5.0)
    parser.add_argument("--scene-plan", type=Path, help="Optional validated scene-plan JSON with per-scene durations")
    parser.add_argument("--min-minutes", type=float, default=8.0)
    parser.add_argument("--max-minutes", type=float, default=10.0)
    args = parser.parse_args()
    try:
        if not 2.0 <= args.seconds_per_scene <= 12.0:
            raise ValueError("--seconds-per-scene must be between 2 and 12")
        if args.min_minutes <= 0 or args.max_minutes < args.min_minutes:
            raise ValueError("duration range must satisfy 0 < min-minutes <= max-minutes")
        video = render(args.scenes, args.output, args.seconds_per_scene,
                       args.scene_plan, args.min_minutes, args.max_minutes)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Rendered review video: {video}")
    print("No upload or publishing was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
