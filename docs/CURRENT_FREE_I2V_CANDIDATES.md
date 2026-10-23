# Current free image-to-video candidate review

Reviewed: 2026-10-23. This is a read-only review; no generation request was submitted and no GPU quota was intentionally consumed.

## Candidate A: LTX-2.3 Fast Space

- Space: https://huggingface.co/spaces/ShaundeOoO/ltx-2.3-fast
- Its published `app.py` describes a Gradio API endpoint named `/generate`.
- Inputs include an image URL/upload, motion prompt, optional negative prompt, 720p/1080p choice, duration 5–10 seconds, seed, MP4/MKV output and optional generated audio.
- The implementation describes itself as a ComfyUI workflow executed inside a ZeroGPU Space.
- This makes it the most promising candidate to inspect next, but public source code alone does not prove the Space is currently running, that the endpoint is reachable, or that free quota is available.
- Do not submit a job until the user explicitly approves using a small amount of their Hugging Face free GPU quota.
- Read the Space's model/license terms and check its current hardware/runtime first. Do not assume the Space's public API is an unlimited or guaranteed production service.

Source code page: https://huggingface.co/spaces/ShaundeOoO/ltx-2.3-fast/blob/main/app.py

## Candidate B: LTX-2.3 Demo

- Space: https://huggingface.co/spaces/asifn269h/ltx-2-3-demo
- It supports image-to-video and synchronized audio, but its published notes say the 22B model needs substantial VRAM (A100 80GB / H100 class) and will not run on CPU or small/free GPU tiers.
- Therefore it is not a safe assumption for a reliable free endpoint.

Source: https://huggingface.co/spaces/asifn269h/ltx-2-3-demo

## Free quota and API facts

Hugging Face's official ZeroGPU documentation currently lists 5 minutes of daily GPU quota for free accounts; the quota is shared across Space UI/API usage and resets 24 hours after first use. Once quota is exhausted, do not use paid credits or silently switch providers.

Official documentation:
- https://huggingface.co/docs/hub/spaces-zerogpu
- https://huggingface.co/docs/hub/spaces-api-endpoints

## Safe next implementation step

1. Run the repository's read-only discovery helper against the candidate:
   `python scripts/check_free_video_space.py ShaundeOoO/ltx-2.3-fast`
   This reads metadata and the API schema only; it does not submit generation.
2. Inspect current Space runtime and the API schema for the exact endpoint and input fields.
3. Ask the user before one short manual generation request, because a real call can consume daily GPU quota and may fail due to queue/model availability.
4. Only after a valid MP4 is returned and manually inspected, implement the concrete adapter. Keep API calls out of CI.
5. Never put HF tokens in source files/logs. Never enable automatic paid fallback. Keep YouTube upload disabled and public publishing prohibited.

## Status

Candidate selection is narrowed down but not yet runtime-verified. No real MP4 has been generated through this provider by the repository, and no adapter is being called in production yet. This is intentional until one user-approved, quota-bounded test succeeds.
