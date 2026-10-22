#!/usr/bin/env python3
"""Pre-upload quality gate for a cinematic video job.

Checks local files and basic media metadata. It never uploads, publishes, or calls
external services. FFprobe is optional; without it, media-stream checks are reported
as skipped rather than falsely passing.
"""
from __future__ import annotations

import argparse
import json
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


def check(video: Path, subtitles: Path | None, narration: Path | None,
          min_minutes: float = 8.0, max_minutes: float = 10.0) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"video": str(video), "checks": {}}
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
            details["stream_types"] = sorted(types)
            if "video" not in types:
                errors.append("Final file has no video stream.")
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
        if "-->" not in text:
            errors.append("Subtitle file has no SRT time ranges.")
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
