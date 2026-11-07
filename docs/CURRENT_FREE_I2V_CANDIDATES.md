# Current free image-to-video candidate review

Reviewed: 2026-10-31. This is a read-only review; no generation request was submitted and no GPU quota was intentionally consumed.

## Candidate A: NiftyVid / Wan 2.2 (best short proof-of-motion candidate)

- Demo: https://igorcsis.github.io/nifty-vid/
- Source: https://github.com/IgorCSIS/nifty-vid
- The project describes a browser-based still-image-to-MP4 workflow using a public Hugging Face Space running Wan 2.2. It says no signup or API key is needed.
- Published limits: 3.5-second default, hard cap 4.5 seconds, approximately 720p; the upstream Space may cold-start for 60–120 seconds and queue during busy periods.
- The NiftyVid application repository is MIT-licensed. That is separate from the underlying model license.
- The official Wan-AI Wan2.2-I2V-A14B model card identifies the model license as Apache-2.0 and describes image-to-video at 480p/720p. This is a useful license signal for the model, but it does not guarantee that every hosted Space, dependency, input asset, or generated result has identical terms. Review the exact upstream Space and model card before commercial use.
- This is suitable only for a small proof-of-motion clip, not a dependable long-form production backend.

## Candidate B: LTX-2.3 Fast Space

- Space: https://huggingface.co/spaces/ShaundeOoO/ltx-2.3-fast
- Its published `app.py` describes a Gradio API endpoint named `/generate`.
- Inputs include an image URL/upload, motion prompt, optional negative prompt, 720p/1080p choice, duration 5–10 seconds, seed, MP4/MKV output and optional generated audio.
- The implementation describes itself as a ComfyUI workflow executed inside a ZeroGPU Space and requests `size="xlarge"`.
- ZeroGPU documents `xlarge` as a 96GB RTX Pro 6000 Blackwell allocation costing 2× quota. That makes it a poor first choice for a tightly bounded free test.
- Public source code does not prove the Space is currently healthy, the endpoint is reachable, or a free request will succeed. The Space page/source inspected earlier showed a runtime error.
- Do not submit a job until the user explicitly approves using GPU quota.

Source code page: https://huggingface.co/spaces/ShaundeOoO/ltx-2.3-fast/blob/main/app.py

## Candidate C: LTX-2.3 Demo

- Space: https://huggingface.co/spaces/asifn269h/ltx-2-3-demo
- Its published notes say the 22B model needs substantial VRAM (A100 80GB / H100 class) and will not run on CPU or small/free GPU tiers.
- Not a safe assumption for a reliable free endpoint.

## ZeroGPU quota rules (important)

Hugging Face's current official documentation distinguishes:
- Unauthenticated requests: 2 minutes/day from a shared pool, with low queue priority.
- Free-account authenticated requests: 5 minutes/day from that account's personal quota.
- PRO: 40 minutes/day; paid credits can extend usage, but paid credits are prohibited for this project.
- `large` uses 1× quota; `xlarge` uses 2× quota.
- The quota resets 24 hours after first GPU use.
- If authenticated with an HF token, the request consumes that account's quota. Do not put a token in the repo or logs.
- Never use paid credits, silently switch providers, or assume a public Space means unlimited free generation.

Official documentation:
- https://huggingface.co/docs/hub/spaces-zerogpu
- https://huggingface.co/docs/hub/spaces-api-endpoints
- https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B

## Safe next steps

1. Use metadata/API-schema inspection only before any generation request.
2. Prefer a single 3–4 second NiftyVid proof-of-motion test over the LTX-2.3 xlarge candidate, if a quota-bounded test is explicitly approved.
3. Before any test, establish whether the public demo uses unauthenticated shared quota or an authenticated account quota; never enter an HF token unless the owner explicitly chooses that route.
4. Inspect the returned MP4 signature, duration, resolution, and playback; visually confirm that the subject actually moves.
5. Only after a real MP4 passes inspection should a concrete adapter be integrated.
6. Keep external generation calls out of CI. No paid fallback, no automatic quota retries, no public YouTube upload.

## Current status

No new generation request was submitted. No real MP4 has been generated through the repository's provider adapter, and no provider has passed the project's output acceptance gate. The current renderer remains a review renderer that can use supplied clips; it does not itself create AI images or image-to-video footage.
