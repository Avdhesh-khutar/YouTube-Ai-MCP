# Free image-to-video provider evaluation

Status: research-only; no provider is marked production-ready until a real request succeeds.

## User requirements

- Browser-first; do not install ComfyUI, Python, FFmpeg, or model weights on the user's laptop.
- Prefer $0; never buy credits or start a paid plan automatically.
- Image-to-video motion is preferred; scripted/animated explainer rendering is the fallback.
- Hindi male narration, subtitles aligned to narration, 8–10 minute final output.
- YouTube upload stays disabled by default; if later enabled with explicit approval, privacy must be `private`.

## Candidate: public Hugging Face Gradio Spaces

Hugging Face documents that public Gradio Spaces can be called through their generated API (see “Use via API” in the Space footer or `/gradio_api/openapi.json`). ZeroGPU documentation currently lists a free-account daily quota of 5 GPU minutes, shared by ZeroGPU Space calls and reset 24 hours after first usage. Queue time, demo availability, model license, and each Space's API schema vary.

Official references:
- https://huggingface.co/docs/hub/spaces-api-endpoints
- https://huggingface.co/docs/hub/spaces-zerogpu
- https://huggingface.co/docs/hub/spaces-overview

Important limits:
- This is a candidate integration route, not a promise of unlimited free generation.
- A public demo may sleep, queue, change, or disappear.
- A token does not increase the free quota; never hardcode tokens or put them in Git.
- The user must inspect the specific Space's license and API before using generated assets commercially.
- Do not call an external generation endpoint automatically during CI.
- Do not silently retry against a paid provider or use credits when the free quota is exhausted.
- Do not claim that an image-to-video API is verified until an end-to-end request returns a valid MP4 and the output is inspected.

## Integration design

Use the existing provider contract / renderer architecture rather than coupling the video pipeline to one demo:
1. A provider adapter accepts an image file or URL, a prompt, and bounded duration/resolution.
2. The adapter reports capability, quota/availability errors, and output metadata.
3. Validate the result as a non-empty MP4 before copying it into a scene workspace.
4. If the provider is unavailable, return an explicit `provider_unavailable` result. Do not label a still-image pan/zoom as generated video.
5. The existing renderer can still make a review video from supplied images and narration while marking those scenes as motion-card/animated stills.
6. Hindi narration should remain a separate TTS stage so image-to-video provider choice does not dictate voice quality.
7. Keep upload disabled by default; if separately approved, only PRIVATE upload is allowed.

## Verification checklist before calling this provider production-ready

- [ ] Select a currently running public image-to-video Space.
- [ ] Read its API schema, model license, input limits, and commercial-use terms.
- [ ] Confirm the request uses only the user's available free quota and does not trigger billing.
- [ ] Run one small manual test only after the user explicitly approves consuming free GPU quota.
- [ ] Verify returned MP4 signature, duration, resolution, and playback.
- [ ] Add mocked adapter tests for queue, quota exhaustion, timeout, invalid output, and success.
- [ ] Run CI without calling any external generation service.
- [ ] Confirm upload is still disabled and no public publish path is enabled.

## Honest current status

The repository's existing ComfyUI helper targets a ComfyUI server the user controls; it is not a Comfy Cloud adapter. This document does not implement or claim a verified Hugging Face image-to-video provider. Until the specific Space has been selected and manually tested, use the provider interface as a seam and the existing renderer as fallback.