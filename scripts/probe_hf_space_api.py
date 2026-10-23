#!/usr/bin/env python3
"""Inspect a public Hugging Face Gradio Space API without running inference.

This makes only metadata GET requests; it does not submit a generation job,
consume ZeroGPU quota, download media, or spend credits.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def fetch_json(url: str, timeout: float) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "YouTube-Ai-MCP-HF-Space-Probe/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = response.status
        payload = json.loads(response.read().decode("utf-8"))
    return status, payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a public Hugging Face Space and its Gradio API schema without running a model."
    )
    parser.add_argument("space", help="Space ID, e.g. owner/space-name")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    space = args.space.strip().strip("/")
    if space.count("/") != 1 or any(part in {"", ".", ".."} for part in space.split("/")):
        parser.error("space must be an owner/space-name identifier")

    api_url = f"https://huggingface.co/api/spaces/{space}"
    try:
        _, metadata = fetch_json(api_url, args.timeout)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"Space metadata unavailable: {exc}", file=sys.stderr)
        return 2

    runtime = metadata.get("runtime") or {}
    print(f"Space: {space}")
    print(f"SDK: {metadata.get('sdk', 'unknown')}")
    print(f"Stage: {runtime.get('stage', 'unknown')}")
    print(f"Hardware: {runtime.get('hardware', 'not reported')}")
    print(f"Public URL: https://huggingface.co/spaces/{space}")

    if metadata.get("sdk") != "gradio":
        print("This Space does not report the Gradio SDK; this probe cannot inspect a Gradio API.")
        return 1

    # The Space subdomain is the owner and Space name joined with a hyphen.
    # If the slug cannot be resolved, the caller should use the Space's own
    # "Use via API" footer link, which is the source of truth.
    owner, name = space.split("/", 1)
    subdomain = f"https://{owner}-{name}.hf.space"
    schema_url = f"{subdomain}/gradio_api/openapi.json"
    try:
        _, schema = fetch_json(schema_url, args.timeout)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"Could not fetch guessed OpenAPI URL: {exc}", file=sys.stderr)
        print("No inference was submitted. Open the Space and use its 'Use via API' link to find the exact API schema.")
        return 1

    paths = schema.get("paths") or {}
    print(f"OpenAPI schema: {schema_url}")
    print("Available API paths:")
    found = False
    for path, methods in sorted(paths.items()):
        for method, detail in sorted((methods or {}).items()):
            if method.lower() not in {"get", "post", "put", "delete"}:
                continue
            found = True
            summary = detail.get("summary") or detail.get("operationId") or ""
            print(f"  {method.upper():6} {path} {summary}".rstrip())
    if not found:
        print("  (No HTTP operation paths were listed.)")

    print("Safety: metadata/schema only; no GPU inference, quota consumption, billing, or uploads occurred.")
    print("Review the Space README, model license, API input schema, and commercial-use terms before use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
