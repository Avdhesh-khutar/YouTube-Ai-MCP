"""Provider contract for the Hindi cinematic workflow.

Concrete adapters must implement these methods and return paths/structured data.
This module deliberately contains no network clients and makes no paid API calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    excerpt: str


@dataclass(frozen=True)
class Scene:
    scene_id: str
    narration: str
    visual_prompt: str
    duration_seconds: int


class ResearchProvider(Protocol):
    def research(self, topic: str, language: str) -> Sequence[ResearchSource]: ...


class ScriptProvider(Protocol):
    def write_script(self, topic: str, sources: Sequence[ResearchSource], language: str,
                     target_minutes: int) -> str: ...


class ScenePlanner(Protocol):
    def plan_scenes(self, script: str, language: str,
                    target_minutes: int) -> Sequence[Scene]: ...


class ImageProvider(Protocol):
    def generate_image(self, prompt: str, output_path: Path) -> Path: ...


class ImageToVideoProvider(Protocol):
    def animate_image(self, image_path: Path, prompt: str, output_path: Path,
                      duration_seconds: int) -> Path: ...


class VoiceProvider(Protocol):
    def synthesize(self, text: str, output_path: Path, language: str) -> Path: ...


class MusicProvider(Protocol):
    def create_or_select_licensed_track(self, mood: str, output_path: Path) -> Path: ...


class SubtitleProvider(Protocol):
    def align(self, narration: str, audio_path: Path, output_path: Path) -> Path: ...


class VideoRenderer(Protocol):
    def render(self, scene_assets: Sequence[Path], voiceover: Path,
               music: Path | None, subtitles: Path, output_path: Path) -> Path: ...


class PrivateYouTubeUploader(Protocol):
    """Implementations must hard-code privacy_status='private' at the API boundary."""

    def upload_private(self, video_path: Path, title: str, description: str,
                       tags: Sequence[str]) -> str: ...
