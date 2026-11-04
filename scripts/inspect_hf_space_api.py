#!/usr/bin/env python3
"""Inspect a public Hugging Face Gradio Space API schema without running a job.

This performs one metadata GET only. It does not submit a prediction, consume GPU
quota intentionally, download model assets, or require an HF token.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def space_openapi_url(space: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", space):
        raise ValueError("Space must use the owner/name format.")
    owner, name = space.split("/", 1)
    host = f"{owner.replace('_', '-')}-{name.replace('_', '-')}.hf.space"
    return f"https://{host}/gradio_api/openapi.json"


def summarize_schema(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("OpenAPI response must be a JSON object.")
    paths = payload.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise ValueError("No OpenAPI paths found; this Space may not expose a Gradio API.")
    endpoints = []
    for path, methods in sorted(paths.items()):
        if not isinstance(methods, dict):
            continue
        for method, operation in sorted(methods.items()):
            if method.lower() not in {"get", "post", "put", "delete"} or not isinstance(operation, dict):
                continue
            body = operation.get("requestBody", {})
            content = body.get("content", {}) if isinstance(body, dict) else {}
            media = content.get("application/json", {}) if isinstance(content, dict) else {}
            endpoints.append({
                "method": method.upper(),
                "path": path,
                "operation_id": operation.get("operationId"),
                "summary": operation.get("summary") or operation.get("description"),
                "request_schema": media.get("schema") if isinstance(media, dict) else None,
            })
    if not endpoints:
        raise ValueError("OpenAPI document contains no supported HTTP operations.")
    return {"openapi": payload.get("openapi"), "title": payload.get("info", {}).get("title"),
            "endpoints": endpoints}


def fetch_schema(url: str, timeout: int = 15) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "youtube-ai-mcp-metadata-inspector/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise ValueError(f"Metadata endpoint returned HTTP {response.status}.")
            raw = response.read(2_000_001)
    except HTTPError as exc:
        raise ValueError(f"Metadata endpoint returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise ValueError(f"Could not reach metadata endpoint: {exc}") from exc
    if len(raw) > 2_000_000:
        raise ValueError("OpenAPI response exceeded the 2 MB safety limit.")
    try:
        return summarize_schema(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Metadata endpoint did not return valid UTF-8 JSON.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", required=True, help="Public Space in owner/name format")
    args = parser.parse_args()
    try:
        url = space_openapi_url(args.space)
        result = fetch_schema(url)
    except ValueError as exc:
        print(f"Inspection failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"space": args.space, "metadata_url": url, **result}, indent=2))
    print("Metadata only: no prediction was submitted and no GPU generation was requested.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
