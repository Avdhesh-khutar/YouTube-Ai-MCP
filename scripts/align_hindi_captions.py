#!/usr/bin/env python3
"""Create speech-timed Hindi SRT captions from the final narration audio.

Optional dependency: faster-whisper. Uses word timestamps from the generated audio
and groups them into short readable caption lines. This is ASR-derived timing,
not forced alignment to the original script or phoneme-level alignment.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable


def srt_timestamp(seconds: float) -> str:
    value = max(0, round(seconds * 1000))
    hours, rest = divmod(value, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    whole, millis = divmod(rest, 1000)
    return f"{hours:02}:{minutes:02}:{whole:02},{millis:03}"


def segments_to_srt(segments: Iterable[object], min_duration: float = 0.25,
                    max_words: int = 7) -> str:
    """Group ASR word timestamps into short, readable speech-synced SRT lines."""
    if max_words < 1:
        raise ValueError("max_words must be at least 1.")
    segment_list = list(segments)
    timed_words: list[tuple[float, float, str]] = []
    for segment in segment_list:
        for word in getattr(segment, "words", None) or []:
            text = str(getattr(word, "word", "")).strip()
            start = float(getattr(word, "start", -1))
            end = float(getattr(word, "end", -1))
            if text and start >= 0 and end > start:
                timed_words.append((start, end, text))

    blocks = []
    previous_end = 0.0
    index = 0
    if timed_words:
        groups: list[list[tuple[float, float, str]]] = []
        current: list[tuple[float, float, str]] = []
        for word in timed_words:
            if current and (len(current) >= max_words or word[0] - current[-1][1] > 0.8):
                groups.append(current)
                current = []
            current.append(word)
        if current:
            groups.append(current)
        for group in groups:
            start = max(previous_end, group[0][0])
            end = max(item[1] for item in group)
            if end <= start:
                continue
            if end - start < min_duration:
                end = start + min_duration
            text = "".join(item[2] for item in group).strip()
            index += 1
            blocks.append(f"{index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{text}")
            previous_end = end
    else:
        # Fallback for ASR backends that provide only segment-level timestamps.
        for segment in segment_list:
            text = str(getattr(segment, "text", "")).strip()
            if not text:
                continue
            start = max(previous_end, float(getattr(segment, "start")))
            end = float(getattr(segment, "end"))
            if end <= start:
                continue
            if end - start < min_duration:
                end = start + min_duration
            index += 1
            blocks.append(f"{index}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{text}")
            previous_end = end
    if not blocks:
        raise ValueError("Speech recognizer returned no usable Hindi caption segments or words.")
    return "\n\n".join(blocks) + "\n"

def transcribe_to_srt(audio_path: Path, output_path: Path, model_size: str = "small",
                      compute_type: str = "int8", language: str = "hi") -> Path:
    if not audio_path.is_file():
        raise FileNotFoundError(f"Narration audio not found: {audio_path}")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Speech-timed captions need the optional faster-whisper package. "
            "Install it in the rendering environment; no package is installed automatically."
        ) from exc
    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    segments, info = model.transcribe(
        str(audio_path), language=language, vad_filter=True,
        word_timestamps=True, beam_size=5,
    )
    srt = segments_to_srt(segments)
    print(
        f"Speech-timed captions: {output_path} "
        f"(detected={info.language}, probability={info.language_probability:.2f})"
    )
    if info.language != language:
        raise RuntimeError(
            f"Expected language '{language}', recognizer detected '{info.language}'. "
            "No approved SRT was written; review the narration audio."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(srt, encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("captions.srt"))
    parser.add_argument("--model", default="small", choices=("tiny", "base", "small", "medium", "large-v3"))
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--language", default="hi")
    args = parser.parse_args()
    try:
        transcribe_to_srt(args.audio, args.output, args.model, args.compute_type, args.language)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Review Hindi spelling and punctuation before publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
