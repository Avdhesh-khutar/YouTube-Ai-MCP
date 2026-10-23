# Free image-to-video provider evaluation

Status: research-only; no provider is production-ready until a real request succeeds and its output is inspected.

## User requirements

- Browser-first; do not install ComfyUI, Python, FFmpeg, or model weights on the user's laptop.
- Prefer $0; never buy credits or start a paid plan automatically.
- Image-to-video motion is preferred; scripted/animated explainer rendering is the fallback.
- Hindi male narration, subtitles aligned to narration, 8–10 minute final output.
- YouTube upload stays disabled by default; if later enabled with explicit approval, privacy must be `private`.

## API route

Hugging Face documents that public Gradio Spaces can be called through their generated API (Space footer “Use via API” or `/gradio_api/openapi.json`). Current documentation lists a free-account ZeroGPU quota of 5 GPU minutes per 24 hours after first usage. Queue time, model, and each Space's API schema vary.

Official references:
- https://huggingface.co/docs/hub/spaces-api-endpoints
- https://huggingface.co/docs/hub/spaces-zerogpu
- https://huggingface.co/docs/hub/spaces-overview

## Candidate to inspect: LTX 2.3 Studio

- Space: https://huggingface.co/spaces/techfreakworm/LTX2.3-Studio
- Its README advertises image-to-video input (image + prompt) and MP4 output, with optional audio.
- The Space's API schema, current queue/health, exact duration/resolution limits, license implications for generated output, and one real API request have **not** been verified for this project.
- The underlying LTX-2.3 model is large; do not assume every free GPU instance can serve it successfully.
- Before integrating, open the Space, click “Use via API”, and check the image input and prompt fields. Do not submit a generation job until the user explicitly approves spending free GPU quota.

Alternative candidates listed by the Hugging Face directory include Lightricks' LTX 2.3 Distilled and community Wan2.2 I2V Spaces. They are alternatives to inspect, not verified working endpoints.

## Important limits

- This is a candidate integration route, not unlimited free generation.
- A public demo may sleep, queue, change, or disappear.
- A token does not increase free quota; never hardcode tokens or put them in Git.
- Check the specific model and Space license before commercial use on YouTube.
- Do not call an external generation endpoint automatically during CI.
- Do not silently retry against a paid provider or use credits when free quota is exhausted.
- Do not claim that an image-to-video API is verified until a real request returns a valid MP4 and the output is inspected.

## Integration design

Use the existing provider contract / renderer architecture rather than coupling the pipeline to one demo:
1. An adapter accepts an image file or URL, a prompt, and bounded duration/resolution.
2. It reports capability, quota/availability errors, and output metadata.
3. Validate the result as a non-empty MP4 before copying it into a scene workspace.
4. If unavailable, return an explicit `provider_unavailable` result. Do not label still-image pan/zoom as generated video.
5. The existing renderer can make a review video from supplied images and narration while marking those scenes as motion-card/animated stills.
6. Keep Hindi narration separate from the video provider.
7. Keep YouTube upload disabled by default; if separately approved, only PRIVATE upload is allowed.

## Verification checklist

- [ ] Inspect the candidate Space's API schema, input limits, and current availability.
- [ ] Read the model and Space licenses and commercial-use terms.
- [ ] Confirm the request uses only the user's free quota and cannot trigger billing.
- [ ] Run one small manual test only after the user explicitly approves consuming free GPU quota.
- [ ] Verify returned MP4 signature, duration, resolution, and playback.
- [ ] Add mocked adapter tests for queue, quota exhaustion, timeout, invalid output, and success.
- [ ] Run CI without calling external generation services.
- [ ] Confirm upload is still disabled and no public publish path is enabled.

## Honest current status

The repository's existing ComfyUI helper targets a ComfyUI server the user controls; it is not a Comfy Cloud adapter. This document identifies a candidate but does not implement or claim a verified Hugging Face image-to-video provider. Until a specific Space has been manually tested, use the provider interface as a seam and the existing renderer as fallback.