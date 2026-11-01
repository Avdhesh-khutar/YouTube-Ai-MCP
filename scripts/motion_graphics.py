"""Small, dependency-free helpers for animated scene title overlays.

The FFmpeg drawtext filter is applied per scene, so each title animates in at the
start of its scene instead of appearing as a static full-video caption.
"""
from __future__ import annotations

import re


def escape_drawtext(value: str) -> str:
    """Escape text for FFmpeg drawtext's filter-option parser."""
    # Keep titles compact and prevent user-provided text from injecting filter options.
    value = re.sub(r"\s+", " ", str(value)).strip()[:90]
    return (value.replace("\\", r"\\")
            .replace(":", r"\:")
            .replace("'", r"\'")
            .replace("%", r"\%")
            .replace(",", r"\,")
            .replace("[", r"\[")
            .replace("]", r"\]"))


def build_title_overlay_filter(title: str, duration: float) -> str:
    """Return a tasteful animated lower-third filter for one scene."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    safe_title = escape_drawtext(title)
    end = min(4.8, duration)
    fade_in = min(0.45, end / 4)
    fade_out_start = max(fade_in, end - 0.45)
    alpha = (
        f"if(lt(t,{fade_in:.3f}),t/{fade_in:.3f},"
        f"if(gt(t,{fade_out_start:.3f}),({end:.3f}-t)/0.45,1))"
    )
    return (
        "drawbox=x=0:y=ih-142:w=iw:h=142:color=black@0.48:t=fill:"
        f"enable='between(t,0,{end:.3f})',"
        "drawtext=text='" + safe_title + "':fontcolor=white:fontsize=42:"
        "x='80+if(lt(t,0.45), (1-t/0.45)*-55, 0)':y=h-96:"
        f"alpha='{alpha}':enable='between(t,0,{end:.3f})'"
    )


def title_for_scene(scene: dict, fallback: str) -> str:
    """Prefer an explicit short title; otherwise derive one from narration."""
    title = scene.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()[:90]
    narration = str(scene.get("narration", "")).strip()
    if narration:
        words = narration.split()
        return " ".join(words[:9]) + ("…" if len(words) > 9 else "")
    return fallback
