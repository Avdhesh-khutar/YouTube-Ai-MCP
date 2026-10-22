#!/usr/bin/env python3
"""Resumable orchestration scaffold for private-first Hindi cinematic videos.

This module deliberately does not invent provider APIs. It validates a topic and
configuration, writes a job manifest and research/script/scene-plan handoff files,
and reports which configured production stages still need provider adapters.
It never uploads or publishes videos by itself.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.validate_research_manifest import ManifestError, validate_manifest
    from scripts.validate_scene_plan import ScenePlanError, validate_scene_plan
except ModuleNotFoundError:  # Support direct execution as `python scripts/orchestrate...`
    from validate_research_manifest import ManifestError, validate_manifest
    from validate_scene_plan import ScenePlanError, validate_scene_plan

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "cinematic-workflow.example.json"
DEFAULT_JOBS = ROOT / "jobs"


class WorkflowError(RuntimeError):
    """Actionable workflow configuration or execution error."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"Configuration not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"Expected a JSON object in {path}")
    return value


def validate_config(config: dict[str, Any]) -> None:
    if config.get("language") != "hi-IN":
        raise WorkflowError("This starter currently supports the Hindi default only (language=hi-IN).")
    duration = config.get("target_duration_minutes", {})
    try:
        low, high = int(duration["min"]), int(duration["max"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkflowError("target_duration_minutes must contain integer min and max values.") from exc
    if low < 1 or high < low or high > 60:
        raise WorkflowError("Duration must satisfy 1 <= min <= max <= 60.")
    upload = config.get("workflow", {}).get("youtube_upload", {})
    if upload.get("privacy_status") != "private":
        raise WorkflowError("Safety policy: youtube_upload.privacy_status must be 'private'.")
    if upload.get("allow_public_publish") is not False:
        raise WorkflowError("Safety policy: allow_public_publish must be false.")
    security = config.get("security", {})
    if security.get("never_commit_secrets") is not True:
        raise WorkflowError("Safety policy: never_commit_secrets must be true.")
    if security.get("never_log_secrets") is not True:
        raise WorkflowError("Safety policy: never_log_secrets must be true.")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u0900-\u097f]+", "-", value.strip().lower()).strip("-")
    return (slug or "cinematic-video")[:64]


def create_job(topic: str, config_path: Path, jobs_dir: Path,
               research_manifest_path: Path | None = None,
               scene_plan_path: Path | None = None) -> Path:
    topic = topic.strip()
    if len(topic) < 4:
        raise WorkflowError("Please provide a topic with at least 4 characters.")
    config = read_json(config_path)
    validate_config(config)
    research_data: dict[str, Any] | None = None
    if research_manifest_path is not None:
        try:
            research_data = read_json(research_manifest_path)
            validate_manifest(research_data)
            research_topic = research_data.get("topic")
            if not isinstance(research_topic, str) or research_topic.strip() != topic:
                raise WorkflowError("research manifest topic must exactly match the requested video topic")
        except (WorkflowError, ManifestError) as exc:
            raise WorkflowError(f"Research manifest validation failed: {exc}") from exc
    scene_plan_data: dict[str, Any] | None = None
    if scene_plan_path is not None:
        try:
            scene_plan_data = read_json(scene_plan_path)
            duration = config["target_duration_minutes"]
            validate_scene_plan(scene_plan_data, float(duration["min"]), float(duration["max"]))
        except (WorkflowError, ScenePlanError) as exc:
            raise WorkflowError(f"Scene plan validation failed: {exc}") from exc

    job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    job_dir = jobs_dir / f"{slugify(topic)}-{job_id}"
    job_dir.mkdir(parents=True, exist_ok=False)
    (job_dir / "input.json").write_text(
        json.dumps({"topic": topic, "language": "Hindi", "target_duration_minutes": config["target_duration_minutes"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (job_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "job_id": job_id,
        "topic": topic,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "planning_scaffold",
        "language": "Hindi",
        "target_duration_minutes": config["target_duration_minutes"],
        "upload": {"enabled": bool(config["workflow"]["youtube_upload"].get("enabled")), "privacy_status": "private", "public_publish": False, "requires_owner_approval": True},
        "stages": [
            {"name": name, "status": "blocked_provider_unconfigured"}
            for name in (
                "research", "script", "scene_planning", "image_generation",
                "image_to_video", "voiceover", "music_and_sfx", "subtitles",
                "render", "thumbnail_and_metadata", "quality_checks", "private_youtube_upload"
            )
        ],
        "notes": [
            "This is an orchestration scaffold, not a completed end-to-end run.",
            "Provider integrations are not configured; no paid API is called.",
            "YouTube upload is not executed by this command. Public publishing is disabled."
        ]
    }
    (job_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # A supplied manifest must pass structural provenance checks before job creation.
    # Without one, create an explicitly empty handoff rather than inventing research.
    research_payload = research_data or {
        "topic": topic,
        "sources": [],
        "claims": [],
        "instructions": "Add HTTPS source records and link every factual claim to source_ids. Keep status as needs_review until the claim is checked against its cited source. Structural validation does not establish factual accuracy."
    }
    (job_dir / "research-manifest.json").write_text(
        json.dumps(research_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (job_dir / "NEXT_STEPS.md").write_text(
        "# Job handoff\n\n"
        f"**Topic:** {topic}\n\n"
        "This job folder is ready for provider adapters. The current command does not fabricate research, scripts, images, narration, or a video. "
        "Configure and test the provider adapters before expecting an end-to-end result.\n\n"
        "## Required next integrations\n"
        "- Research provider with source URLs and a source manifest\n"
        "- Hindi script and scene-plan generator with duration validation\n"
        "- Image and image-to-video providers\n"
        "- Hindi TTS and licensed music/SFX\n"
        "- SRT generation/alignment and FFmpeg rendering\n"
        "- Designed thumbnail, metadata, QA, and deduplicated private-only YouTube upload\n",
        encoding="utf-8",
    )
    return job_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a resumable job workspace for the private-first Hindi cinematic workflow.")
    parser.add_argument("--topic", required=True, help="Video topic in Hindi or English")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Workflow JSON configuration")
    parser.add_argument("--research-manifest", type=Path, help="Optional source-backed research JSON; validated before job creation")
    parser.add_argument("--scene-plan", type=Path, help="Optional scene-plan JSON; validated against configured duration before job creation")
    parser.add_argument("--jobs-dir", type=Path, default=DEFAULT_JOBS, help="Output directory for job workspaces")
    args = parser.parse_args()
    try:
        job_dir = create_job(args.topic, args.config, args.jobs_dir, args.research_manifest, args.scene_plan)
    except WorkflowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Job workspace created: {job_dir}")
    print(f"Manifest: {job_dir / 'manifest.json'}")
    print(f"Handoff: {job_dir / 'NEXT_STEPS.md'}")
    print("Status: scaffold only; provider integrations are not configured.")
    print("Safety: no secrets read, no API calls, no upload, public publishing disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
