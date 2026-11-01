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
    from scripts.motion_graphics import build_title_overlay_filter, title_for_scene
except ModuleNotFoundError:  # Support direct execution as a script
    from validate_scene_plan import ScenePlanError, validate_scene_plan
    from motion_graphics import build_title_overlay_filter, title_for_scene

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


def probe_duration(path: Path) -> float:
    """Read actual media duration using ffprobe; fail closed on unreadable files."""
    executable = shutil.which("ffprobe")
    if executable is None:
        raise RuntimeError("ffprobe is required to verify actual media duration.")
    result = subprocess.run(
        [executable, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True, capture_output=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"ffprobe could not read {path.name}: {result.stderr[-2000:]}")
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"ffprobe returned invalid duration for {path.name}") from exc
    if duration <= 0:
        raise RuntimeError(f"Media duration must be positive: {path.name}")
    return duration


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def render(scenes_dir: Path, output_dir: Path, seconds_per_scene: float = 5.0,
           scene_plan_path: Path | None = None, min_minutes: float = 8.0,
           max_minutes: float = 10.0, motion_graphics: bool = False) -> Path:
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
    planned_titles: dict[int, str] = {}
    if scene_plan_path is not None:
        try:
            plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
            validate_scene_plan(plan, min_minutes, max_minutes)
        except (OSError, json.JSONDecodeError, ScenePlanError) as exc:
            raise ValueError(f"Scene plan validation failed: {exc}") from exc
        for scene in plan["scenes"]:
            match = re.fullmatch(r"scene[-_](\d+)", scene["scene_id"], re.IGNORECASE)
            if not match:
                raise ValueError(f"Scene plan ID must match scene-NN format: {scene['scene_id']}")
            number = int(match.group(1))
            if number in planned_durations:
                raise ValueError(f"Duplicate scene number in plan: {number}")
            planned_durations[number] = float(scene["duration_seconds"])
            planned_titles[number] = title_for_scene(scene, f"Scene {number:02d}")
        image_numbers = {
            int(re.fullmatch(r"scene[-_](\d+)", image.stem, re.IGNORECASE).group(1))
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
        segment = output_dir / f"segment-{index:03d}.mp4"
        scene_number = int(re.fullmatch(r"scene[-_](\d+)", image.stem, re.IGNORECASE).group(1))
        duration = planned_durations.get(scene_number, max(2.0, seconds_per_scene))
        title_filter = ""
        if motion_graphics:
            scene_title = planned_titles.get(scene_number, image.stem.replace("-", " "))
            title_filter = "," + build_title_overlay_filter(scene_title, duration)

        # Numbered short clips form a timeline for one long narration scene:
        # scene-01-clip-001.mp4, scene-01-clip-002.mp4, ...
        clip_pattern = re.compile(
            rf"{re.escape(image.stem)}-clip[-_](\d+)", re.IGNORECASE
        )
        clip_sequence = sorted(
            (p for p in scenes_dir.iterdir()
             if p.is_file() and p.suffix.lower() == ".mp4"
             and clip_pattern.fullmatch(p.stem)),
            key=lambda p: int(clip_pattern.fullmatch(p.stem).group(1)),
        )
        legacy_clip = image.with_suffix(".mp4")
        if not clip_sequence and legacy_clip.exists():
            clip_sequence = [legacy_clip]

        if clip_sequence:
            clip_durations = [(clip, probe_duration(clip)) for clip in clip_sequence]
            available_duration = sum(value for _, value in clip_durations)
            if available_duration + 0.05 < duration:
                raise RuntimeError(
                    f"AI-motion timeline for {image.stem} provides only "
                    f"{available_duration:.2f}s across {len(clip_sequence)} clip(s), "
                    f"but the scene plans {duration:.2f}s. Add more numbered clips; "
                    "the renderer will not freeze or silently loop footage."
                )
            remaining = duration
            rendered_clips = []
            for clip_index, (clip, source_duration) in enumerate(clip_durations, start=1):
                if remaining <= 0.05:
                    break
                take = min(source_duration, remaining)
                clip_segment = output_dir / (
                    f"segment-{index:03d}-motion-{clip_index:03d}.mp4"
                )
                run([
                    "ffmpeg", "-y", "-i", str(clip), "-t", f"{take:.6f}",
                    "-an", "-vf",
                    f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                    f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1,format=yuv420p{title_filter}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    str(clip_segment),
                ])
                segments.append(clip_segment)
                rendered_clips.append({
                    "file": clip.name,
                    "source_duration_seconds": source_duration,
                    "used_duration_seconds": take,
                })
                remaining -= take
            scene_rows.append({
                "scene": image.name,
                "motion": "image-to-video clip sequence",
                "planned_duration_seconds": duration,
                "source_clips": rendered_clips,
                "source_clip_duration_seconds": available_duration,
            })
        else:
            run([
                "ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(image),
                "-vf",
                f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH*2}:{HEIGHT*2},"
                f"zoompan=z='min(zoom+0.0007,1.12)':d=1:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1,format=yuv420p{title_filter}",
                "-t", str(duration), "-an", "-c:v", "libx264",
                "-preset", "medium", "-crf", "20", str(segment),
            ])
            segments.append(segment)
            scene_rows.append({
                "scene": image.name,
                "motion": "cinematic Ken Burns zoom",
                "planned_duration_seconds": duration,
                "source_clip_duration_seconds": None,
            })

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
    music = scenes_dir / "background-music.mp3"
    if not music.exists():
        music = scenes_dir / "background-music.wav"
    final_video = output_dir / "cinematic-video.mp4"
    timeline_duration = sum(row["planned_duration_seconds"] for row in scene_rows)
    command = ["ffmpeg", "-y", "-i", str(silent_video)]
    if narration.exists():
        command += ["-i", str(narration)]
    if music.exists():
        command += ["-stream_loop", "-1", "-i", str(music)]
    if narration.exists() and music.exists():
        command += [
            "-filter_complex",
            "[1:a]volume=1.0[voice];[2:a]volume=0.12,afade=t=in:st=0:d=2[bed];"
            "[voice][bed]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v:0", "-map", "[a]",
        ]
    elif narration.exists():
        command += ["-map", "0:v:0", "-map", "1:a:0"]
    elif music.exists():
        command += ["-map", "0:v:0", "-map", "1:a:0", "-t", f"{timeline_duration:.3f}"]
    else:
        command += ["-map", "0:v:0", "-an"]
    if captions.exists():
        subtitle_path = captions.as_posix().replace("\\", "\\\\").replace(":", "\\:")
        subtitle_style = (
            "FontName=Arial,FontSize=26,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00101010,BackColour=&H80000000,"
            "Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=42"
        )
        command += ["-vf", f"subtitles='{subtitle_path}':force_style='{subtitle_style}'"]
    command += ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    if narration.exists() or music.exists():
        command += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    command += ["-movflags", "+faststart", str(final_video)]
    run(command)
    actual_duration = probe_duration(final_video)
    if scene_plan_path is not None:
        minimum_seconds = min_minutes * 60
        maximum_seconds = max_minutes * 60
        tolerance_seconds = 1.0
        if not (minimum_seconds - tolerance_seconds <= actual_duration <= maximum_seconds + tolerance_seconds):
            raise RuntimeError(
                f"Final video is {actual_duration:.2f}s; expected "
                f"{minimum_seconds:.0f}–{maximum_seconds:.0f}s for the validated "
                "scene plan. Check narration length and scene timeline; no upload was performed."
            )

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
            "planned_duration_seconds": sum(row["planned_duration_seconds"] for row in scene_rows),
            "actual_duration_seconds": actual_duration,
            "duration_difference_seconds": actual_duration - sum(row["planned_duration_seconds"] for row in scene_rows),
            "scenes": scene_rows,
            "audio": narration.name if narration.exists() else None,
            "background_music": music.name if music.exists() else None,
            "background_music_gain": 0.12 if music.exists() else None,
            "captions": captions.name if captions.exists() else None,
            "motion_graphics_enabled": motion_graphics,
            "upload_enabled": False,
            "notes": "Actual duration is probed from the final MP4. Review image rights, voice, captions, pacing, and thumbnail before any upload.",
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
    parser.add_argument(
        "--motion-graphics", action="store_true",
        help="Add animated scene-title lower thirds (requires FFmpeg drawtext support).",
    )
    args = parser.parse_args()
    try:
        if not 2.0 <= args.seconds_per_scene <= 12.0:
            raise ValueError("--seconds-per-scene must be between 2 and 12")
        if args.min_minutes <= 0 or args.max_minutes < args.min_minutes:
            raise ValueError("duration range must satisfy 0 < min-minutes <= max-minutes")
        video = render(args.scenes, args.output, args.seconds_per_scene,
                       args.scene_plan, args.min_minutes, args.max_minutes,
                       args.motion_graphics)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Rendered review video: {video}")
    print("No upload or publishing was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
