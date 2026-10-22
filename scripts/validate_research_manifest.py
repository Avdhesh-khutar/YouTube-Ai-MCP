#!/usr/bin/env python3
"""Validate a source-grounded research manifest before scripting.

This validates provenance structure only; it does not independently verify that
a source supports a claim. Human/provider fact-checking is still required.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


class ManifestError(ValueError):
    pass


def validate_manifest(data: object) -> dict:
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    sources = data.get("sources")
    claims = data.get("claims")
    if not isinstance(sources, list) or not sources:
        raise ManifestError("sources must be a non-empty list")
    if not isinstance(claims, list) or not claims:
        raise ManifestError("claims must be a non-empty list")

    source_ids: set[str] = set()
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise ManifestError(f"source {index} must be an object")
        source_id = source.get("id")
        title = source.get("title")
        url = source.get("url")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ManifestError(f"source {index} needs a non-empty id")
        if source_id in source_ids:
            raise ManifestError(f"duplicate source id: {source_id}")
        source_ids.add(source_id)
        if not isinstance(title, str) or not title.strip():
            raise ManifestError(f"source {source_id} needs a title")
        if not isinstance(url, str):
            raise ManifestError(f"source {source_id} needs an HTTPS URL")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ManifestError(f"source {source_id} needs a valid HTTPS URL without credentials")

    claim_ids: set[str] = set()
    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            raise ManifestError(f"claim {index} must be an object")
        claim_id = claim.get("id")
        text = claim.get("text")
        refs = claim.get("source_ids")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ManifestError(f"claim {index} needs a non-empty id")
        if claim_id in claim_ids:
            raise ManifestError(f"duplicate claim id: {claim_id}")
        claim_ids.add(claim_id)
        if not isinstance(text, str) or not text.strip():
            raise ManifestError(f"claim {claim_id} needs text")
        if not isinstance(refs, list) or not refs:
            raise ManifestError(f"claim {claim_id} must cite at least one source_id")
        unknown = [ref for ref in refs if not isinstance(ref, str) or ref not in source_ids]
        if unknown:
            raise ManifestError(f"claim {claim_id} references unknown source id(s): {unknown}")
        if claim.get("status", "needs_review") not in {"verified", "needs_review", "disputed"}:
            raise ManifestError(f"claim {claim_id} has invalid status")
        # A claim cannot be marked verified merely by including a URL. Require
        # an explicit reviewer/provider verification note for that status.
        if claim.get("status") == "verified" and not (
            isinstance(claim.get("verification_note"), str)
            and claim["verification_note"].strip()
        ):
            raise ManifestError(f"verified claim {claim_id} needs verification_note")

    return {
        "valid": True,
        "source_count": len(sources),
        "claim_count": len(claims),
        "verified_claim_count": sum(c.get("status", "needs_review") == "verified" for c in claims),
        "warning": "Structural validation only; citation relevance and factual accuracy are not independently verified.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON file with sources[] and claims[]")
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = validate_manifest(data)
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
