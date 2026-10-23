#!/usr/bin/env python3
"""Generate scene images (and optional image-to-video clips) through a local ComfyUI API.

Requires ComfyUI running locally and API-format workflow JSON exported from ComfyUI.
No paid service or remote model is called by this script.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPTS = ROOT / "dist-cinematic" / "scene-prompts.json"
DEFAULT_SCENES = ROOT / "assets" / "cinematic-scenes"


def request_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach ComfyUI at {url}: {exc}") from exc


def replace_tokens(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: replace_tokens(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_tokens(v, replacements) for v in value]
    if isinstance(value, str):
        for token, replacement in replacements.items():
            value = value.replace(token, replacement)
    return value


def upload_image(base_url: str, path: Path) -> str:
    boundary = "----ComfyUI" + uuid.uuid4().hex
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n".encode(),
        data,
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request(base_url + "/upload/image", data=b"".join(parts), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ComfyUI image upload failed: {exc}") from exc
    return str(result.get("name", path.name))


def submit_and_wait(base_url: str, workflow: dict[str, Any], timeout: int) -> dict[str, Any]:
    response = request_json(base_url + "/prompt", {"prompt": workflow, "client_id": uuid.uuid4().hex})
    prompt_id = response.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI did not return prompt_id: {response}")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        history = request_json(base_url + "/history/" + urllib.parse.quote(str(prompt_id)))
        item = history.get(prompt_id)
        if item and item.get("outputs"):
            return item["outputs"]
        if item and item.get("status", {}).get("status_str") == "error":
            raise RuntimeError(f"ComfyUI workflow failed for prompt {prompt_id}")
        time.sleep(2)
    raise TimeoutError(f"ComfyUI generation timed out after {timeout}s (prompt {prompt_id})")


def download_outputs(base_url: str, outputs: dict[str, Any], destination: Path, allowed: set[str]) -> list[Path]:
    saved: list[Path] = []
    for node in outputs.values():
        for kind in ("images", "gifs", "videos"):
            for item in node.get(kind, []):
                filename = str(item.get("filename", ""))
                if not filename or Path(filename).suffix.lower() not in allowed:
                    continue
                query = urllib.parse.urlencode({
                    "filename": filename,
                    "subfolder": item.get("subfolder", ""),
                    "type": item.get("type", "output"),
                })
                url = base_url + "/view?" + query
                with urllib.request.urlopen(url, timeout=60) as response:
                    data = response.read()
                target = destination / Path(filename).name
                target.write_bytes(data)
                saved.append(target)
    return saved



def validate_prompts(prompts: Any) -> list[dict[str, Any]]:
    """Validate scene prompt records before making requests to ComfyUI."""
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("Prompt JSON must be a non-empty list of scene records.")
    validated: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, scene in enumerate(prompts, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene prompt {index} must be a JSON object.")
        number = scene.get("scene")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ValueError(f"Scene prompt {index} must have a positive integer 'scene'.")
        if number in seen:
            raise ValueError(f"Duplicate scene number: {number}.")
        if not isinstance(scene.get("image_prompt"), str) or not scene["image_prompt"].strip():
            raise ValueError(f"Scene {number} must have a non-empty 'image_prompt'.")
        negative = scene.get("negative_prompt", "")
        if not isinstance(negative, str):
            raise ValueError(f"Scene {number} 'negative_prompt' must be text.")
        seen.add(number)
        validated.append(scene)
    return validated

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8188")
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--image-workflow", type=Path, required=True, help="ComfyUI API-format workflow JSON with __POSITIVE_PROMPT__, __NEGATIVE_PROMPT__, and __OUTPUT_PREFIX__ tokens")
    parser.add_argument("--video-workflow", type=Path, help="Optional API workflow with same prompt tokens and a LoadImage node containing __INPUT_IMAGE__")
    parser.add_argument("--scenes-dir", type=Path, default=DEFAULT_SCENES)
    parser.add_argument("--animate-every", type=int, default=3, help="Animate every Nth scene when video workflow is supplied")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    if not args.prompts.is_file() or not args.image_workflow.is_file():
        parser.error("Prompt JSON and image workflow file must exist.")
    if args.animate_every < 1 or args.timeout < 30:
        parser.error("--animate-every must be >= 1 and --timeout must be >= 30 seconds.")
    base_url = args.base_url.rstrip("/")
    if request_json(base_url + "/system_stats") is None:
        raise RuntimeError("ComfyUI health check returned no response.")

    try:
        prompts = validate_prompts(json.loads(args.prompts.read_text(encoding="utf-8")))
        image_template = json.loads(args.image_workflow.read_text(encoding="utf-8"))
        video_template = json.loads(args.video_workflow.read_text(encoding="utf-8")) if args.video_workflow else None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(f"Invalid prompt/workflow JSON: {exc}")
    args.scenes_dir.mkdir(parents=True, exist_ok=True)
    generated = 0

    for scene in prompts:
        number = int(scene["scene"])
        image_path = args.scenes_dir / f"scene-{number:02d}.png"
        if not image_path.exists():
            workflow = replace_tokens(image_template, {
                "__POSITIVE_PROMPT__": str(scene["image_prompt"]),
                "__NEGATIVE_PROMPT__": str(scene.get("negative_prompt", "")),
                "__OUTPUT_PREFIX__": f"youtube_ai_mcp/scene-{number:02d}",
            })
            outputs = submit_and_wait(base_url, workflow, args.timeout)
            files = download_outputs(base_url, outputs, args.scenes_dir, {".png", ".jpg", ".jpeg", ".webp"})
            if not files:
                raise RuntimeError("Image workflow produced no downloadable image; ensure it has a SaveImage output node.")
            image_path.write_bytes(files[0].read_bytes())
            if files[0] != image_path:
                files[0].unlink(missing_ok=True)
            generated += 1
            print(f"Generated image: {image_path.name}")
        else:
            print(f"Keeping existing image: {image_path.name}")

        if video_template and number % args.animate_every == 0:
            video_path = image_path.with_suffix(".mp4")
            if video_path.exists():
                print(f"Keeping existing animation: {video_path.name}")
                continue
            uploaded_name = upload_image(base_url, image_path)
            workflow = replace_tokens(video_template, {
                "__POSITIVE_PROMPT__": str(scene["image_prompt"]),
                "__NEGATIVE_PROMPT__": str(scene.get("negative_prompt", "")),
                "__OUTPUT_PREFIX__": f"youtube_ai_mcp/scene-{number:02d}-motion",
                "__INPUT_IMAGE__": uploaded_name,
            })
            outputs = submit_and_wait(base_url, workflow, args.timeout)
            files = download_outputs(base_url, outputs, args.scenes_dir, {".mp4"})
            if not files:
                raise RuntimeError("Video workflow produced no video; configure an output node that saves MP4/WebM/GIF.")
            selected = files[0]
            if selected.suffix.lower() != ".mp4":
                video_path = selected
            else:
                selected.replace(video_path)
            print(f"Generated animation: {video_path.name}")

    print(f"Done. New images generated: {generated}. Assets saved in {args.scenes_dir}")
    print("This script does not upload or publish anything to YouTube.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
