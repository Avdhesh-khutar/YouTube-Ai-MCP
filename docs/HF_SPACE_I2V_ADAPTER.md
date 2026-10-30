# Hugging Face Space image-to-video adapter (experimental)

This is an opt-in adapter scaffold for public Gradio Spaces. It does not assume that any particular Space has a stable API, does not run during CI, does not call a paid fallback, and does not upload to YouTube.

## Before running

1. Open the chosen Space and click **Use via API**.
2. Confirm the endpoint accepts an input image and prompt, its license permits your intended use, and its interface does not require a paid subscription or credit purchase.
3. Check the endpoint's exact API name and input order. Do not assume all video Spaces share the same schema.
4. Only run the test if you accept consuming your available free GPU quota. A free account's ZeroGPU quota is limited (currently documented as 5 GPU minutes per day) and queue availability can vary.
5. Run the script in a trusted Python environment where `gradio_client` is installed. This does not require installing ComfyUI on the laptop, but the script itself needs a Python execution environment. Do not commit `HF_TOKEN`.

Official docs:
- https://huggingface.co/docs/hub/spaces-api-endpoints
- https://huggingface.co/docs/hub/spaces-zerogpu

## Inspected LTX 2.3 Studio schema (2026-10-30)

The user supplied the Space's OpenAPI schema. Its image-input endpoint is
`/run/handler_1` (Gradio client API name: `/handler_1`) with 17 positional
inputs:

| Position | OpenAPI field | Schema |
|---:|---|---|
| 0 | `param_0` | string |
| 1 | `param_1` | Fast / Balanced / Quality |
| 2–3 | `param_2`, `param_3` | number, 256–4096 |
| 4 | `param_4` | number, 1–30 |
| 5 | `param_5` | number, 8–30 |
| 6 | `param_6` | integer |
| 7 | `param_7` | boolean |
| 8 | `param_8` | ImageData |
| 9 | `param_9` | string |
| 10 | `param_10` | none / static / dolly-in / dolly-out / dolly-left / dolly-right / jib-up / jib-down |
| 11 | `param_11` | number, 0–1.5 |
| 12 | `param_12` | boolean |
| 13 | `param_13` | number, 0–1 |
| 14 | `param_14` | none / union / pose-control |
| 15 | `param_15` | number, 0–1 |
| 16 | `param_16` | boolean |

The schema confirms position 8 is the image and positions 0 and 9 are strings,
but does not expose their UI labels or the meaning/defaults of several controls.
The adapter therefore validates the 17-input shape, requires `__IMAGE__` at
position 8 and a `__PROMPT__` placeholder in position 0 or 9, and leaves all
other values explicit in the caller-provided JSON. Do not invent those values.
The text-to-video endpoint `/run/handler` is not used for image-to-video.

The video output is nested under `output_1.video` in the OpenAPI response.
Actual Gradio client return shape still needs a no-quota metadata inspection or
a single explicitly approved generation before production wiring can be claimed.

## Example

Install the client in the execution environment:

```bash
python -m pip install --upgrade gradio_client
```

Inspect the Space's **Use via API** page and supply the exact endpoint name and input array order. The JSON array uses placeholders:
- `__IMAGE__`: uploaded image
- `__PROMPT__`: motion prompt (place in the verified text input slot)
- `__DURATION__`: requested duration (only if the endpoint has a matching input)

```bash
python scripts/hf_space_i2v.py \
  --space OWNER/SPACE_NAME \
  --api-name /exact_endpoint_name \
  --image assets/cinematic-scenes/scene-01.png \
  --prompt "Slow cinematic camera push-in, subtle natural motion" \
  --duration 4 \
  --api-args-json '["__IMAGE__", "__PROMPT__", "__DURATION__"]' \
  --output dist-cinematic/scene-01.mp4 \
  --confirm-free-quota
```

The example endpoint name and argument order are placeholders, not a verified Space configuration. Replace them using the selected Space's API docs. Some Spaces return a result structure the adapter cannot automatically recognize; if so, stop and inspect the schema rather than making repeated requests.

## Current verification status

- The LTX 2.3 Studio image-input endpoint schema is documented and guarded by unit tests; no real API generation request has been made.
- No model or endpoint is yet marked production-ready.
- A valid output file signature is checked, but playback, duration, resolution, motion quality, and commercial license must still be checked.
- This adapter has no retry loop to avoid wasting quota.
- It is not wired into automatic CI or automatic video generation.
- YouTube upload remains a separate, manually approved, private-only step.
- Never set a Hugging Face token in source code or paste it into chat. Use a secret manager/environment variable only if the selected Space needs authentication.
