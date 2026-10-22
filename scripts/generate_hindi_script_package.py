#!/usr/bin/env python3
"""Generate a Hindi script and scene-prompt package via an OpenAI-compatible API.

This command makes a paid/external request only when explicitly run with the required
environment variables. It does not browse the web, generate media, or upload anything.
Keep API keys in environment/secret manager; never pass them as CLI arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing environment variable: {name}")
    return value


def call_chat_api(base_url: str, api_key: str, model: str, topic: str,
                  target_minutes: int, timeout: int = 120) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    if not base_url.startswith("https://"):
        raise ValueError("CINEMATIC_LLM_BASE_URL must use HTTPS.")
    url = base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"
    system = (
        "You are a careful Hindi documentary writer. Return ONLY valid JSON with keys "
        "title, description, narration, scenes. narration must be in natural Hindi and "
        "suitable for the requested duration; scenes must be an array of 12-24 objects, "
        "each with scene, narration_excerpt, image_prompt, negative_prompt, duration_seconds. "
        "Do not invent factual citations or claim web research was performed. Mark uncertain "
        "claims in the narration for later fact-checking. Use cinematic, respectful visuals."
    )
    user = (
        f"Topic: {topic}\nLanguage: Hindi (hi-IN)\nTarget duration: {target_minutes} minutes. "
        "Write an engaging documentary-style draft. Provide enough narration for the target "
        "duration (roughly 120-140 Hindi words per minute, adjust naturally). Make scene "
        "narration excerpts cover the script in order. Image prompts should be descriptive "
        "and suitable for a cinematic 16:9 composition. Return JSON only."
    )
    payload = {
        "model": model,
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            envelope = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Do not expose response body; providers may echo sensitive request details.
        raise RuntimeError(f"LLM API returned HTTP {exc.code}; verify provider, model, and account limits.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM API request failed ({type(exc).__name__}).") from exc
    try:
        content = envelope["choices"][0]["message"]["content"]
        package = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Provider response was not valid JSON in the expected chat-completions format.") from exc
    validate_package(package, target_minutes)
    return package


def validate_package(package: dict[str, Any], target_minutes: int) -> None:
    for key in ("title", "description", "narration", "scenes"):
        if key not in package:
            raise ValueError(f"Generated package is missing required field: {key}")
    if not isinstance(package["narration"], str) or len(package["narration"].strip()) < 300:
        raise ValueError("Narration is too short; refusing to save an incomplete script.")
    scenes = package["scenes"]
    if not isinstance(scenes, list) or not 12 <= len(scenes) <= 24:
        raise ValueError("Scene plan must contain between 12 and 24 scenes.")
    required_scene_keys = {"scene", "narration_excerpt", "image_prompt", "negative_prompt", "duration_seconds"}
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict) or not required_scene_keys.issubset(scene):
            raise ValueError(f"Scene {index} is missing required fields.")
        if not str(scene["image_prompt"]).strip():
            raise ValueError(f"Scene {index} has an empty image prompt.")
        try:
            duration = int(scene["duration_seconds"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Scene {index} duration must be an integer.") from exc
        if not 2 <= duration <= 90:
            raise ValueError(f"Scene {index} duration must be 2-90 seconds.")
        scene["scene"] = index
        scene["duration_seconds"] = duration
    package["language"] = "hi-IN"
    package["target_duration_minutes"] = target_minutes
    package["fact_check_status"] = "needs_human_or_source-backed_verification"
    package["media_generated"] = False
    package["youtube_upload_performed"] = False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("dist-cinematic"))
    parser.add_argument("--target-minutes", type=int, default=9)
    args = parser.parse_args()
    if len(args.topic.strip()) < 4:
        parser.error("--topic must contain at least 4 characters")
    if not 8 <= args.target_minutes <= 10:
        parser.error("--target-minutes must be between 8 and 10")
    try:
        package = call_chat_api(
            required_env("CINEMATIC_LLM_BASE_URL"),
            required_env("CINEMATIC_LLM_API_KEY"),
            required_env("CINEMATIC_LLM_MODEL"),
            args.topic.strip(), args.target_minutes,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "script-package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "script-hi.txt").write_text(package["narration"].strip() + "\n", encoding="utf-8")
    (args.output_dir / "scene-prompts.json").write_text(
        json.dumps(package["scenes"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Draft package saved to: {args.output_dir.resolve()}")
    print("Includes a Hindi script and scene prompts; facts still need source-backed checking.")
    print("No images/video/audio generated and no YouTube upload performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
