#!/usr/bin/env python3
"""Inspect a public Hugging Face Gradio Space without running a generation job.

This discovery helper is intentionally read-only: it does not submit prompts,
consume GPU quota, request a token, or call any paid provider.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def get_json(url: str, timeout: float = 15.0) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "YouTube-Ai-MCP-free-provider-check/1.0",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def inspect_space(space_id: str) -> int:
    if "/" not in space_id or space_id.startswith("/") or space_id.endswith("/"):
        print("ERROR: use owner/space-name format, for example owner/demo")
        return 2

    metadata_url = "https://huggingface.co/api/spaces/" + space_id
    try:
        _, metadata = get_json(metadata_url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not read Space metadata: {exc}")
        return 1

    if not isinstance(metadata, dict):
        print("ERROR: unexpected Space metadata response")
        return 1

    runtime = metadata.get("runtime") or {}
    print(f"Space: {space_id}")
    print(f"URL: https://huggingface.co/spaces/{space_id}")
    print(f"SDK: {metadata.get('sdk', 'unknown')}")
    print(f"Runtime stage: {runtime.get('stage', 'unknown')}")
    print(f"Hardware: {runtime.get('hardware', 'unknown')}")
    print(f"Private: {metadata.get('private', 'unknown')}")
    print("No generation request was submitted; no GPU quota was intentionally consumed.")

    # Gradio Spaces expose OpenAPI for supported API endpoints. This read-only
    # check may fail on non-Gradio Spaces, sleeping Spaces, or custom deployments.
    subdomain = metadata.get("subdomain")
    candidates = []
    if subdomain:
        candidates.append(f"https://{subdomain}.hf.space/gradio_api/openapi.json")
    candidates.append(f"https://{space_id.replace('/', '-')}.hf.space/gradio_api/openapi.json")

    for schema_url in candidates:
        try:
            _, schema = get_json(schema_url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue
        if not isinstance(schema, dict):
            continue
        paths = schema.get("paths") or {}
        endpoints = sorted(
            path for path, methods in paths.items()
            if isinstance(methods, dict)
            and any(method.lower() in {"post", "get"} for method in methods)
        )
        print(f"API schema: {schema_url}")
        if endpoints:
            print("Discovered API paths:")
            for endpoint in endpoints:
                print(f"  - {endpoint}")
        else:
            print("API schema found, but no GET/POST paths were identified.")
        print("IMPORTANT: endpoint discovery does not prove image-to-video capability,")
        print("free quota, commercial-use permission, or that the endpoint will stay online.")
        return 0

    print("API schema: not reachable (Space may be sleeping, non-Gradio, or have no public API).")
    print("Open the Space page and check its 'Use via API' section manually.")
    print("No generation request was submitted.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "space_id",
        nargs="?",
        default="asifn269h/ltx-2-3-demo",
        help="Hugging Face Space ID in owner/name form (default: asifn269h/ltx-2-3-demo)",
    )
    args = parser.parse_args()
    return inspect_space(args.space_id)


if __name__ == "__main__":
    sys.exit(main())
