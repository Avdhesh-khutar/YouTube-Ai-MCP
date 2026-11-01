# Free-provider route for completing the cinematic pipeline

Reviewed on 2026-11-01. This document records practical alternatives and the integration decision. It does not claim that any third-party provider has been API-integrated or quality-approved.

## Decision summary

Use a **provider-agnostic, browser-assisted workflow** for the next milestone. Do not bind the Worker to a single free demo whose endpoint, quota, or availability can change without notice.

### Image-to-video candidates

| Candidate | What is verified from public information | Limitation / decision |
|---|---|---|
| NiftyVid (Wan 2.2) | Open-source browser app, no signup/API key claimed, public Hugging Face shared GPU; MP4 download; approximately 4.5-second clips | Owner already generated one 3.56-second sample. Technically playable, but visual review rejected it for subject drift/artifacts. Keep as first manual candidate, not production-approved. |
| Hugging Face Wan 2.2 / LTX Spaces | Public Space directory currently lists multiple image-to-video demos, including Wan 2.2 14B Fast and LTX variants | Shared ZeroGPU capacity, queue/quota and endpoint schemas vary. Inspect the exact Space API before wiring an adapter. |
| Wan2.Video public demos | Site advertises browser-based Wan/LTX image-to-video without signup, using public GPU queues | Third-party site; queue, privacy/retention, and quota are not guaranteed. Use only non-sensitive images and review terms before commercial use. |

Links:
- NiftyVid: https://igorcsis.github.io/nifty-vid/
- Hugging Face video Spaces: https://huggingface.co/spaces?category=video-generation
- Wan2.Video: https://wan2.video/

The current sample renderer already accepts scene-matched MP4s and normalizes them to 1280×720 at 30 fps. Do not loop a 3–5 second clip to pretend it covers a long scene; provide enough distinct motion clips or use a controlled still-image section explicitly labelled as such.

## Hindi narration candidates

### Preferred browser-first experiment: Indic TTS

The `indic-tts` project exposes Hindi synthesis in WebAssembly/ONNX, caches model assets in the browser, and documents CPU fallback. Its README lists a Hindi model and a simple browser JavaScript API. This is a better fit for a no-install browser workflow than requiring a local Piper CLI, but naturalness, male voice quality, long-script throughput, and commercial licensing must be listened to and verified before acceptance.

Repository: https://github.com/h2210316651/indic-tts

### Secondary browser candidate: Kokoro Web

Kokoro Web advertises local in-browser speech synthesis, no account, and Hindi among its languages. Text is limited to 2,000 characters per request, so long scripts need chunking. Confirm the available Hindi voice gender and pronunciation quality before choosing it.

Website: https://kokoroweb.app/

### Offline fallback

Keep the existing Piper adapter as a fallback when a compatible Hindi ONNX voice model and config are explicitly supplied. Do not silently fall back to eSpeak for a release-quality narration. eSpeak remains only a smoke-test voice.

## Integration architecture

1. Research and write a source-grounded Hindi script.
2. Split narration into paragraph chunks (roughly 1,500–1,800 characters each for browser TTS), preserving sentence boundaries.
3. Generate a short Hindi sample from Indic TTS and Kokoro Web; compare voice gender, naturalness, pronunciation, pacing, and clipping. Select only after listening.
4. Generate 12–24 scene images. Animate selected scenes with one of the public Wan/LTX demos; record provider, model/Space, date, clip duration, source image, and review result in the job manifest.
5. Reject motion clips with face/body drift, flicker, morphing, artifacts, or unwanted subject exits. Generate alternatives rather than repairing defects with zoom.
6. Join narration chunks, align Hindi captions to the actual audio, add licensed music at low gain, and render through the existing FFmpeg renderer.
7. Require 8–10 minute actual ffprobe duration, video/audio streams, readable captions, 720p/30fps minimum, and a manual full-playback review.
8. Keep upload disabled by default. If the owner later requests an upload, use only PRIVATE visibility and verify the result in YouTube Studio.

## Current blockers that cannot be bypassed honestly

- Public free GPU demos can queue, rate-limit, change endpoint schemas, or disappear. A public page is not a stable production API.
- The current NiftyVid sample is not visually acceptable as production footage.
- The connected Runway workspace has no available video or speech models, so it is not a free fallback.
- The repository has no verified Indic-TTS or Kokoro browser integration, no selected provider credentials/config, and no real end-to-end 8–10 minute acceptance run.
- The user prefers no local installation; therefore do not make local ComfyUI a prerequisite.

## Acceptance status

This route is a concrete implementation direction, **not a claim of completion**. A release can be marked complete only after the sample voice and motion clips are actually generated, listened to/watched, rendered into a full-length video, and quality-checked. No paid API, paid credits, public upload, production deploy, or main-branch change is authorized by this document.
