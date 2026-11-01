#!/usr/bin/env python3
"""Validate a planned scene list before asset generation.

This checks structure and timing only. It does not assess factual accuracy,
visual quality, copyright, or whether narration actually matches the visuals.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class ScenePlanError(ValueError):
    """Invalid scene-plan data."""


def validate_scene_plan(data: object, min_minutes: float = 8.0,
                        max_minutes: float = 10.0) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ScenePlanError("scene plan must be a JSON object")
    if min_minutes <= 0 or max_minutes < min_minutes:
        raise ScenePlanError("duration range must satisfy 0 < min-minutes <= max-minutes")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ScenePlanError("scenes must be a non-empty list")

    ids: set[str] = set()
    total_seconds = 0
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ScenePlanError(f"scene {index} must be an object")
        scene_id = scene.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id.strip():
            raise ScenePlanError(f"scene {index} needs a non-empty scene_id")
        if scene_id in ids:
            raise ScenePlanError(f"duplicate scene_id: {scene_id}")
        ids.add(scene_id)
        for field in ("narration", "visual_prompt"):
            value = scene.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ScenePlanError(f"scene {scene_id} needs non-empty {field}")
        duration = scene.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise ScenePlanError(f"scene {scene_id} duration_seconds must be a number")
        if not float(duration).is_integer() or not 2 <= duration <= 120:
            raise ScenePlanError(f"scene {scene_id} duration_seconds must be a whole number from 2 to 120")
        total_seconds += int(duration)

    min_seconds, max_seconds = min_minutes * 60, max_minutes * 60
    if not min_seconds <= total_seconds <= max_seconds:
        raise ScenePlanError(
            f"scene plan totals {total_seconds}s; expected {min_seconds:g}-{max_seconds:g}s"
        )
    return {
        "valid": True,
        "scene_count": len(scenes),
        "total_duration_seconds": total_seconds,
        "target_duration_minutes": {"min": min_minutes, "max": max_minutes},
        "warning": "Structural/timing validation only; narration, factual accuracy, and visuals need review.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_plan", type=Path, help="JSON object containing scenes[]")
    parser.add_argument("--min-minutes", type=float, default=8.0)
    parser.add_argument("--max-minutes", type=float, default=10.0)
    args = parser.parse_args()
    try:
        data = json.loads(args.scene_plan.read_text(encoding="utf-8"))
        report = validate_scene_plan(data, args.min_minutes, args.max_minutes)
    except (OSError, json.JSONDecodeError, ScenePlanError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
