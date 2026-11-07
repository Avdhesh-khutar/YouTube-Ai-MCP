#!/usr/bin/env python3
"""Check whether a ComfyUI-compatible API endpoint is reachable.

Use a local ComfyUI URL or a provider-documented API base URL. This script does not
submit generation jobs, download assets, spend credits, or upload to YouTube.
Never pass API keys in the URL; this minimal checker is intended for endpoints that
do not require an authorization header.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit


def check_endpoint(base_url: str, timeout: int = 10) -> dict[str, object]:
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("Use HTTPS for remote endpoints; HTTP is allowed only for localhost.")
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Provide a clean API base URL without credentials, query, or fragment.")
    clean_base = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
    request = urllib.request.Request(clean_base + "/system_stats", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Endpoint response was not a JSON object.")
            return {"reachable": True, "status_code": response.status, "endpoint": clean_base,
                    "api_shape": "ComfyUI-compatible /system_stats", "generation_submitted": False}
    except urllib.error.HTTPError as exc:
        # Do not print response bodies; they may contain provider details.
        return {"reachable": False, "status_code": exc.code, "endpoint": clean_base,
                "error": "Endpoint returned an HTTP error; verify documented API path and authentication.",
                "generation_submitted": False}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"reachable": False, "endpoint": clean_base,
                "error": f"Could not verify endpoint ({type(exc).__name__}).",
                "generation_submitted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout must be between 1 and 60 seconds")
    try:
        report = check_endpoint(args.base_url, args.timeout)
    except ValueError as exc:
        print(json.dumps({"reachable": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["reachable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
