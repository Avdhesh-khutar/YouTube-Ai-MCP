#!/usr/bin/env python3
"""Generate a Hindi script package using a LOCAL Ollama model only.

Calls http://127.0.0.1:11434/api/chat. This script has no cloud fallback, does not
require an API key, and does not create images/audio/video or upload to YouTube.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from scripts.generate_hindi_script_package import validate_package


def generate(topic: str, model: str, target_minutes: int, timeout: int = 600) -> dict[str, Any]:
    if not 8 <= target_minutes <= 10:
        raise ValueError("target_minutes must be between 8 and 10")
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.6},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful Hindi documentary writer. Return only a JSON object "
                    "with title, description, narration, scenes. narration must be natural Hindi. "
                    "scenes must contain 12-24 objects with scene, narration_excerpt, image_prompt, "
                    "negative_prompt, duration_seconds. Do not claim web research was performed "
                    "or invent citations. Mark uncertain factual claims for later verification."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {topic}\nLanguage: Hindi (hi-IN). Duration: {target_minutes} minutes. "
                    "Draft enough narration for 8-10 minutes at a natural Hindi narration pace. "
                    "Provide 12-24 ordered cinematic 16:9 scene prompts. Return valid JSON only."
                ),
            },
        ],
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            envelope = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Local Ollama returned HTTP {exc.code}; check that it is running and the model exists.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Cannot reach local Ollama. Install/start Ollama and pull the model first.") from exc
    except TimeoutError as exc:
        raise RuntimeError("Local model timed out; try a smaller model or a longer timeout.") from exc
    try:
        package = json.loads(envelope["message"]["content"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Local model did not return the required JSON package.") from exc
    validate_package(package, target_minutes)
    package["provider"] = "ollama-local"
    package["paid_api_used"] = False
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--target-minutes", type=int, default=9)
    parser.add_argument("--output-dir", type=Path, default=Path("dist-cinematic"))
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if len(args.topic.strip()) < 4:
        parser.error("--topic must contain at least 4 characters")
    try:
        package = generate(args.topic.strip(), args.model, args.target_minutes, args.timeout)
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
    print(f"Saved local-model draft package to {args.output_dir.resolve()}")
    print("No cloud API, paid credits, media generation, or YouTube upload was used.")
    print("Fact-check the narration before use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
