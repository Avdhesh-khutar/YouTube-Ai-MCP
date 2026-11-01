#!/usr/bin/env python3
"""Opt-in adapter for a public Hugging Face Gradio image-to-video Space.

This script does not call any provider unless explicitly executed. It never uploads
to YouTube and does not purchase credits. API arguments are Space-specific: inspect
the Space's "Use via API" page before supplying --api-args-json.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".m4v"}
VIDEO_SIGNATURES = (b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x1cftyp",
                    b"\x00\x00\x00\x20ftyp", b"\x1aE\xdf\xa3")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", required=True, help="Public Gradio Space, e.g. owner/space-name")
    parser.add_argument("--api-name", required=True, help="Exact endpoint name from the Space's Use via API page")
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--api-args-json", required=True,
        help='JSON array in endpoint input order; use "__IMAGE__", "__PROMPT__", "__DURATION__" placeholders',
    )
    parser.add_argument("--duration", type=int, default=4, help="Requested clip duration, if the endpoint accepts it")
    parser.add_argument("--confirm-free-quota", action="store_true",
                        help="Required acknowledgement: this request may consume free GPU quota")
    return parser.parse_args()


def resolve_args(raw: Any, image: Path, prompt: str, duration: int) -> Any:
    if raw == "__IMAGE__":
        from gradio_client import handle_file
        return handle_file(str(image.resolve()))
    if raw == "__PROMPT__":
        return prompt
    if raw == "__DURATION__":
        return duration
    if isinstance(raw, list):
        return [resolve_args(x, image, prompt, duration) for x in raw]
    if isinstance(raw, dict):
        return {k: resolve_args(v, image, prompt, duration) for k, v in raw.items()}
    return raw


def validate_endpoint_args(api_name: str, raw_args: Any) -> None:
    """Fail closed for the inspected LTX Studio image-to-video endpoint."""
    if api_name not in {"handler_1", "/handler_1"}:
        return
    if not isinstance(raw_args, list) or len(raw_args) != 17:
        raise ValueError("LTX Studio /handler_1 requires exactly 17 positional inputs.")
    if raw_args[8] != "__IMAGE__":
        raise ValueError("LTX Studio /handler_1 input 8 must be the __IMAGE__ placeholder.")
    if "__PROMPT__" not in (raw_args[0], raw_args[9]):
        raise ValueError("Place __PROMPT__ in the verified text-input slot (param_0 or param_9).")
    # Other positions are deliberately caller-supplied: the schema exposes types,
    # but not the UI labels/semantics needed to safely invent their values.


def find_video_path(value: Any) -> Path | None:
    if isinstance(value, str):
        path = Path(value)
        if path.suffix.lower() in VIDEO_SUFFIXES and path.is_file():
            return path
        # Never fetch arbitrary URLs returned by a provider.
        return None
    if isinstance(value, dict):
        for key in ("video", "path", "name", "output"):
            found = find_video_path(value.get(key))
            if found:
                return found
        for item in value.values():
            found = find_video_path(item)
            if found:
                return found
    if isinstance(value, (tuple, list)):
        for item in value:
            found = find_video_path(item)
            if found:
                return found
    return None


def validate_video(path: Path, *, require_playable: bool = False) -> None:
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError("Output must use a recognized video extension (.mp4, .webm, .mov, .m4v).")
    if not path.is_file() or path.stat().st_size < 16:
        raise ValueError("Provider output is missing or empty; no valid video was produced.")
    with path.open("rb") as file:
        header = file.read(16)
    if not any(header.startswith(sig) for sig in VIDEO_SIGNATURES):
        raise ValueError("Provider output does not have a recognized MP4/WebM video signature.")

    if require_playable:
        # A file signature alone can be faked or truncated. For real provider output,
        # require ffprobe to confirm a readable video stream before reporting success.
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=codec_name,width,height",
                    "-of", "json", str(path),
                ],
                check=True, capture_output=True, text=True, timeout=20,
            )
        except FileNotFoundError as exc:
            raise ValueError("ffprobe is required to verify playable output. Install FFmpeg or run in a runner that includes ffprobe.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or "").strip()[:500]
            raise ValueError(f"ffprobe could not read the generated video: {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ValueError("ffprobe timed out while checking generated video.") from exc
        try:
            payload = json.loads(result.stdout)
            streams = payload.get("streams", [])
        except (json.JSONDecodeError, AttributeError) as exc:
            raise ValueError("ffprobe returned invalid stream metadata.") from exc
        if not streams or not streams[0].get("codec_name") or not streams[0].get("width") or not streams[0].get("height"):
            raise ValueError("Output has no readable video stream; it will not be reported as a successful clip.")


def main() -> int:
    args = parse_args()
    if not args.confirm_free_quota:
        print("Stopped: add --confirm-free-quota only after checking the Space and accepting its free quota use.", file=sys.stderr)
        return 2
    if not args.image.is_file():
        print(f"Input image not found: {args.image}", file=sys.stderr)
        return 2
    if not args.prompt.strip():
        print("Prompt must not be empty.", file=sys.stderr)
        return 2
    if args.duration < 1 or args.duration > 10:
        print("Duration must be between 1 and 10 seconds for this initial test adapter.", file=sys.stderr)
        return 2
    if args.output.suffix.lower() not in VIDEO_SUFFIXES:
        print("Output path must end with a recognized video extension (.mp4, .webm, .mov, .m4v).", file=sys.stderr)
        return 2
    if args.output.resolve() == args.image.resolve():
        print("Output path must not overwrite the source image.", file=sys.stderr)
        return 2

    try:
        raw_args = json.loads(args.api_args_json)
    except json.JSONDecodeError as exc:
        print(f"--api-args-json must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(raw_args, list):
        print("--api-args-json must be a JSON array in the exact endpoint input order.", file=sys.stderr)
        return 2
    try:
        validate_endpoint_args(args.api_name, raw_args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        from gradio_client import Client
        token = os.environ.get("HF_TOKEN") or None
        client = Client(args.space, token=token)
        endpoint_args = [resolve_args(item, args.image, args.prompt, args.duration) for item in raw_args]
        result = client.predict(*endpoint_args, api_name=args.api_name)
        video = find_video_path(result)
        if video is None:
            raise ValueError("No local video file found in the endpoint result. Inspect the Space API output schema; no output was saved.")
        validate_video(video, require_playable=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video, args.output)
        validate_video(args.output, require_playable=True)
        print(json.dumps({"status": "success", "output": str(args.output), "bytes": args.output.stat().st_size}))
        return 0
    except Exception as exc:
        print(f"Image-to-video request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("No paid fallback was attempted; no YouTube upload was performed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
