#!/usr/bin/env python3
"""Pre-upload quality gate for a cinematic video job.

Checks local files and basic media metadata. It never uploads, publishes, or calls
external services. FFprobe is optional; without it, media-stream checks are reported
as skipped rather than falsely passing.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def probe(path: Path) -> dict[str, Any] | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
        text=True, capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError(f"ffprobe could not read {path.name}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def validate_srt(text: str) -> tuple[int, float, list[str]]:
    """Validate SRT timestamps, ordering, and non-empty caption text."""
    errors: list[str] = []
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]
    if not blocks:
        return 0, 0.0, ["Subtitle file contains no caption blocks."]
    timestamp = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")
    def millis(value: str) -> int | None:
        match = timestamp.fullmatch(value)
        if not match:
            return None
        hours, minutes, seconds, ms = map(int, match.groups())
        if minutes > 59 or seconds > 59:
            return None
        return ((hours * 60 + minutes) * 60 + seconds) * 1000 + ms
    previous_start = -1
    previous_end = -1
    last_end = 0
    for number, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        if len(lines) < 3 or not lines[0].strip().isdigit():
            errors.append(f"Caption block {number} must contain an index, time range, and text.")
            continue
        if int(lines[0].strip()) != number:
            errors.append(f"Caption block {number} has a non-sequential index.")
        parts = [part.strip() for part in lines[1].split("-->")]
        if len(parts) != 2:
            errors.append(f"Caption block {number} has an invalid time range.")
            continue
        start, end = millis(parts[0]), millis(parts[1])
        if start is None or end is None or end <= start:
            errors.append(f"Caption block {number} has invalid or reversed timestamps.")
            continue
        if start < previous_start:
            errors.append(f"Caption block {number} is out of chronological order.")
        if previous_end >= 0 and start < previous_end:
            errors.append(f"Caption block {number} overlaps the previous caption.")
        if not any(line.strip() for line in lines[2:]):
            errors.append(f"Caption block {number} has no text.")
        previous_start, previous_end, last_end = start, end, max(last_end, end)
    return len(blocks), last_end / 1000.0, errors


def check(video: Path, subtitles: Path | None, narration: Path | None = None,
          min_minutes: float = 8.0, max_minutes: float = 10.0) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"video": str(video), "checks": {}}
    media_duration: float | None = None
    if not video.is_file() or video.stat().st_size == 0:
        errors.append("Final video is missing or empty.")
    else:
        details["checks"]["video_file"] = "pass"
        metadata = probe(video)
        if metadata is None:
            warnings.append("ffprobe unavailable; duration/audio/video stream checks were skipped.")
            details["checks"]["media_probe"] = "skipped"
        else:
            streams = metadata.get("streams", [])
            types = {stream.get("codec_type") for stream in streams}
            try:
                duration = float(metadata.get("format", {}).get("duration", 0))
            except (TypeError, ValueError):
                duration = 0
            details["duration_seconds"] = duration
            media_duration = duration
            details["stream_types"] = sorted(types)
            video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
            if not video_streams:
                errors.append("Final file has no video stream.")
                details["checks"]["resolution"] = "fail"
            else:
                width = int(video_streams[0].get("width", 0) or 0)
                height = int(video_streams[0].get("height", 0) or 0)
                details["resolution"] = {"width": width, "height": height}
                if width < 1280 or height < 720:
                    errors.append(f"Video resolution {width}x{height} is below the 1280x720 minimum.")
                    details["checks"]["resolution"] = "fail"
                else:
                    details["checks"]["resolution"] = "pass"
            if "audio" not in types:
                errors.append("Final file has no audio stream.")
            if duration < min_minutes * 60 or duration > max_minutes * 60:
                errors.append(f"Duration {duration:.1f}s is outside {min_minutes:g}-{max_minutes:g} minutes.")
            details["checks"]["media_probe"] = "pass" if not errors else "fail"
    if subtitles is None or not subtitles.is_file() or subtitles.stat().st_size == 0:
        errors.append("Subtitle SRT is missing or empty.")
        details["checks"]["subtitles"] = "fail"
    else:
        text = subtitles.read_text(encoding="utf-8-sig").strip()
        count, caption_end, srt_errors = validate_srt(text)
        details["subtitle_count"] = count
        details["subtitle_end_seconds"] = caption_end
        if media_duration is not None and caption_end > media_duration + 0.5:
            srt_errors.append(
                f"Subtitles end at {caption_end:.1f}s, after video duration {media_duration:.1f}s."
            )
        if srt_errors:
            errors.extend(srt_errors)
            details["checks"]["subtitles"] = "fail"
        else:
            details["checks"]["subtitles"] = "pass"
    if narration is not None and (not narration.is_file() or narration.stat().st_size == 0):
        errors.append("Narration file was specified but is missing or empty.")
    details["checks"]["narration"] = (
        "pass" if narration is not None and narration.is_file() and narration.stat().st_size else
        "not_checked" if narration is None else "fail"
    )
    details["errors"] = errors
    details["warnings"] = warnings
    details["ready_for_owner_review"] = not errors
    details["upload_performed"] = False
    details["public_publish"] = False
    return details


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--subtitles", type=Path, required=True)
    parser.add_argument("--narration", type=Path)
    parser.add_argument("--min-minutes", type=float, default=8.0)
    parser.add_argument("--max-minutes", type=float, default=10.0)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.min_minutes <= 0 or args.max_minutes < args.min_minutes:
        parser.error("duration range must satisfy 0 < min-minutes <= max-minutes")
    try:
        report = check(args.video, args.subtitles, args.narration,
                       args.min_minutes, args.max_minutes)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["ready_for_owner_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
