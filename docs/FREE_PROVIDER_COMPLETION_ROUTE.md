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

### New candidate: Pocket TTS Hindi (small browser CPU model)

A current Hugging Face research checkpoint, `saryps-labs/pocket-tts-hindi`, provides Hindi streaming TTS with prompt-based voice cloning. The BF16 weights are about 219 MB; its selectively quantized native ONNX bundle is about 240 MB. The model card documents male-labelled voice examples and reports CPU benchmarks on a server-class EPYC machine, not a typical phone. It is not a 106 MB browser model, and the supplied ONNX instructions require native build tooling rather than a turnkey browser app. Treat it as a promising free model for a hosted/browser demo only if the demo actually supports it; otherwise it conflicts with the no-install preference.

Model: https://huggingface.co/saryps-labs/pocket-tts-hindi
License: CC BY 4.0 for the Hindi weights; attribution and upstream component notices are required. The model is an early research release, and voice cloning requires consent. Long-form, accent, number, and naturalness evaluation remains necessary.

Demo candidate (not confirmed to use this exact checkpoint): https://prasadtts.vercel.app

### Preferred browser-first experiment: Indic TTS

The `indic-tts` project exposes Hindi synthesis in WebAssembly/ONNX, caches model assets in the browser, and documents CPU fallback. Its README lists a Hindi model and a simple browser JavaScript API. This is a better fit for a no-install browser workflow than requiring a local Piper CLI, but naturalness, male voice quality, long-script throughput, and commercial licensing must be listened to and verified before acceptance.

Repository: https://github.com/h2210316651/indic-tts

### Alternative: Svāra TTS WebGPU

A public Hugging Face Space/repository advertises 19 Indian languages with male/female voice choices, including Hindi. However, its language model is approximately 1.95 GB plus a codec model and uses WebGPU; this is likely too heavy for some phones and low-memory devices. Keep it as a quality comparison on capable browsers, not the default.

Repository: https://github.com/shreyaskarnik/svara-tts-webgpu

### Secondary browser candidate: Kokoro Web

Kokoro Web advertises local in-browser speech synthesis, no account, and Hindi among its languages. Text is limited to 2,000 characters per request, so long scripts need chunking. Confirm the available Hindi voice gender and pronunciation quality before choosing it.

Website: https://kokoroweb.app/

### Offline fallback

Keep the existing Piper adapter as a fallback when a compatible Hindi ONNX voice model and config are explicitly supplied. Do not silently fall back to eSpeak for a release-quality narration. eSpeak remains only a smoke-test voice.

## Updated shortlist after further research

1. **Pocket TTS Hindi int4** — first lightweight browser sample; ~106 MB model pack; test male prompt and listen for naturalness.
2. **Indic TTS / Piper Pratham** — second sample; browser ONNX/WASM, but verify whether the available Hindi voice meets the requested deep male tone.
3. **Svāra WebGPU** — quality comparison only on capable devices; large ~1.95 GB model.
4. **NiftyVid Wan 2.2 / Wan2.Video public Space** — short motion clips; use only after visual review. These are demos, not stable backend contracts.

For image-to-video, Wan2.Video currently advertises Wan 2.2 14B and LTX public-GPU demos without signup, but explicitly warns about shared queue and usage limits. Its Wan S2V page says image+audio can create a talking/performance clip, but it is also a public demo, not a production API. These are manual test candidates only until their Gradio API schemas and terms are verified.

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


## Additional public-source notes (2026-11-01)

- NiftyVid source README confirms Wan 2.2, a 4.5-second cap, shared Hugging Face Space, cold starts/queues, and MIT license for the NiftyVid app itself. That app license does not grant blanket rights to generated assets or upstream model terms.
- Wan2.Video describes public-GPU queue limits and advises against sensitive uploads; do not rely on it as an uptime-guaranteed backend.
- Hugging Face Space APIs commonly use queue-based Gradio endpoints; the exact Space schema must be read from its own API page before coding an adapter. Do not hardcode a guessed endpoint.
- Indic TTS README documents Hindi support via Piper Pratham, ONNX Runtime WebAssembly, local generation and MIT package license. The model voice and underlying model terms still need separate confirmation.
- Pocket TTS Hindi int4 model card describes an approximately 106 MB CPU/browser model and male/female prompt examples. Listening and commercial-use checks remain required.
- Svāra TTS WebGPU repository documents Hindi male/female voices but a roughly 1.95 GB language model; this is not the low-memory default.


## Correction to earlier Pocket TTS sizing (2026-11-01)

An updated direct model-card review supersedes the earlier ~106 MB estimate. The current `saryps-labs/pocket-tts-hindi` release is 219 MB BF16 weights; its selective INT8 ONNX bundle is about 240 MB. It is an early research release, not a turnkey 106 MB browser package. Hindi weights are CC BY 4.0; attribution is required. CPU benchmarks were measured on an EPYC server and should not be extrapolated to an 8 GB laptop or Android phone. Male-labelled examples exist, but the requested deep male timbre still needs a listening test.

Hugging Face's current Spaces API documentation describes queue-based Gradio endpoints and indicates daily ZeroGPU quotas of 2 minutes unauthenticated and 5 minutes for free accounts. These quotas are shared/plan-specific and can change; do not treat them as a guaranteed number of successful clips. Public Spaces can be invoked via their documented API, but inspect the exact Space's `Use via API` schema before passing any inputs.
