#!/usr/bin/env python3
"""Inspect a public Hugging Face Gradio Space API without running inference.

This is intentionally metadata-only: it fetches agents.md / OpenAPI metadata,
never uploads an image, submits a generation job, or consumes GPU quota.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def fetch_text(url: str, timeout: float = 15.0) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "YouTube-Ai-MCP-provider-inspector/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read(2_000_000)
        if len(body) >= 2_000_000:
            raise ValueError("Response too large; refusing to parse metadata.")
        if "text" not in content_type and "json" not in content_type:
            raise ValueError(f"Unexpected content type: {content_type}")
        return body.decode("utf-8", errors="replace")


def inspect_space(space_id: str) -> dict[str, Any]:
    if "/" not in space_id or space_id.startswith("/") or space_id.endswith("/"):
        raise ValueError("Space ID must look like 'owner/space-name'.")
    owner, name = space_id.split("/", 1)
    if not owner or not name or any(part in {"..", "."} for part in (owner, name)):
        raise ValueError("Invalid Space ID.")
    # IDs are URL path components; reject unexpected characters to avoid URL injection.
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if any(ch not in allowed for ch in owner + name):
        raise ValueError("Space ID contains unsupported characters.")

    base = f"https://huggingface.co/spaces/{owner}/{name}"
    api_base = f"https://{owner}-{name.replace('.', '-')}.hf.space"
    result: dict[str, Any] = {
        "space_id": space_id,
        "space_url": base,
        "inference_submitted": False,
        "gpu_quota_consumed": False,
        "warning": "Metadata-only check; this does not prove inference works or commercial-use rights.",
    }
    try:
        result["agents_md"] = fetch_text(f"{base}/agents.md")[:12000]
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        result["agents_md_error"] = str(exc)
    try:
        raw = fetch_text(f"{api_base}/gradio_api/openapi.json")
        spec = json.loads(raw)
        paths = spec.get("paths", {})
        if not isinstance(paths, dict):
            raise ValueError("OpenAPI paths field is missing or invalid.")
        result["openapi_url"] = f"{api_base}/gradio_api/openapi.json"
        result["openapi_paths"] = sorted(
            path for path in paths
            if isinstance(path, str) and any(word in path.lower() for word in
                                               ("predict", "call", "upload", "queue"))
        )[:80]
        result["openapi_title"] = spec.get("info", {}).get("title", "")
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        result["openapi_error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a Hugging Face Space API schema without running generation."
    )
    parser.add_argument("space_id", help="Public Space ID, e.g. owner/space-name")
    args = parser.parse_args()
    try:
        report = inspect_space(args.space_id)
    except (ValueError, urllib.error.URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if "openapi_paths" not in report and "agents_md" not in report:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
