#!/usr/bin/env python3
"""Verify a rendered MP4 has readable streams and the requested real runtime.

This gate checks the media file itself with ffprobe; it does not infer duration
from a scene plan or render manifest. It never uploads or modifies the input.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


class MediaCheckError(RuntimeError):
    """Raised when the rendered media does not satisfy the acceptance gate."""


def probe_media(path: Path, ffprobe: str = "ffprobe") -> dict:
    if not path.is_file():
        raise MediaCheckError(f"Video file not found: {path}")
    executable = shutil.which(ffprobe)
    if executable is None:
        raise MediaCheckError(f"ffprobe executable not found: {ffprobe}")
    result = subprocess.run(
        [executable, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise MediaCheckError(f"ffprobe could not read media: {result.stderr[-2000:]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaCheckError("ffprobe returned invalid JSON") from exc
    streams = data.get("streams")
    if not isinstance(streams, list) or not any(s.get("codec_type") == "video" for s in streams):
        raise MediaCheckError("Media has no readable video stream")
    video = next(s for s in streams if s.get("codec_type") == "video")
    if not video.get("codec_name") or int(video.get("width") or 0) <= 0 or int(video.get("height") or 0) <= 0:
        raise MediaCheckError("Video stream must include a codec and non-zero dimensions")
    try:
        duration = float(data["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaCheckError("Media duration is missing or invalid") from exc
    if duration <= 0:
        raise MediaCheckError("Media duration must be greater than zero")
    return {
        "duration_seconds": duration,
        "video_codec": video["codec_name"],
        "width": int(video["width"]),
        "height": int(video["height"]),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def verify(path: Path, min_seconds: float = 480.0, max_seconds: float = 600.0,
           require_audio: bool = False, ffprobe: str = "ffprobe") -> dict:
    if min_seconds <= 0 or max_seconds < min_seconds:
        raise ValueError("duration bounds must satisfy 0 < min-seconds <= max-seconds")
    info = probe_media(path, ffprobe)
    if not min_seconds <= info["duration_seconds"] <= max_seconds:
        raise MediaCheckError(
            f"Actual runtime {info['duration_seconds']:.3f}s is outside "
            f"the allowed {min_seconds:.3f}–{max_seconds:.3f}s range"
        )
    if require_audio and not info["has_audio"]:
        raise MediaCheckError("Audio is required but no audio stream was found")
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Rendered MP4 to inspect")
    parser.add_argument("--min-seconds", type=float, default=480.0)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--ffprobe", default="ffprobe", help="ffprobe executable name/path")
    args = parser.parse_args()
    try:
        info = verify(args.video, args.min_seconds, args.max_seconds, args.require_audio, args.ffprobe)
    except (MediaCheckError, ValueError) as exc:
        print(f"QUALITY GATE FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"quality_gate": "passed", **info}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
