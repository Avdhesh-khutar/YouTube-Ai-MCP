"""Dependency-free FFmpeg motion-graphics presets for explainer videos."""
from __future__ import annotations

import re


def escape_drawtext(value: str) -> str:
    """Escape text for FFmpeg drawtext's filter-option parser."""
    value = re.sub(r"\s+", " ", str(value)).strip()
    escaped = (value.replace("\\", r"\\")
               .replace(":", r"\:")
               .replace("'", r"\'")
               .replace("%", r"\%")
               .replace(",", r"\,")
               .replace("[", r"\[")
               .replace("]", r"\]"))
    return escaped[:90]


def _duration(value: float) -> float:
    if value <= 0:
        raise ValueError("duration must be positive")
    return float(value)


def build_title_overlay_filter(title: str, duration: float) -> str:
    """Animated lower-third title, retained for backwards compatibility."""
    duration = _duration(duration)
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


def build_explainer_overlay_filter(
    title: str,
    subtitle: str,
    duration: float,
    scene_number: int = 1,
    scene_count: int = 1,
) -> str:
    """Build a multi-layer explainer overlay with animated entrance and progress."""
    duration = _duration(duration)
    if scene_number < 1 or scene_count < scene_number:
        raise ValueError("scene_number and scene_count must satisfy 1 <= number <= count")
    title_text = escape_drawtext(title)
    subtitle_text = escape_drawtext(subtitle)
    reveal_end = min(1.0, duration / 3)
    title_y = "h*0.68+if(lt(t,0.65),(1-t/0.65)*42,0)"
    filters = [
        "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.12:t=fill",
        "drawbox=x=70:y=h*0.61:w=9:h=150:color=0xF5B942@1:t=fill:"
        f"enable='between(t,0,{duration:.3f})'",
        "drawbox=x=70:y=h*0.61:w='if(lt(t,0.55),0,210)':h=4:"
        "color=0xF5B942@1:t=fill:enable='between(t,0,1.2)'",
        "drawtext=text='" + title_text + "':fontcolor=white:fontsize=54:"
        "font='DejaVu Sans':x=104:y='" + title_y + "':"
        f"alpha='min(1,t/{reveal_end:.3f})':enable='between(t,0,{duration:.3f})'",
        "drawtext=text='" + subtitle_text + "':fontcolor=white@0.88:fontsize=27:"
        "font='DejaVu Sans':x=106:y=h*0.68+76:"
        f"alpha='min(1,max(0,(t-0.25)/0.55))':enable='between(t,0,{duration:.3f})'",
        "drawtext=text='" + f"{scene_number:02d} / {scene_count:02d}" + "':"
        "fontcolor=white@0.78:fontsize=22:x=w-tw-72:y=58:"
        f"enable='between(t,0,{duration:.3f})'",
        "drawbox=x=0:y=h-8:w=iw:h=8:color=white@0.22:t=fill",
        f"drawbox=x=0:y=h-8:w='iw*min(1,t/{duration:.3f})':h=8:"
        "color=0xF5B942@1:t=fill",
    ]
    return ",".join(filters)


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
