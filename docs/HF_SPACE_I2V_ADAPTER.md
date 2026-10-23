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

## Example

Install the client in the execution environment:

```bash
python -m pip install --upgrade gradio_client
```

Inspect the Space's **Use via API** page and supply the exact endpoint name and input array order. The JSON array uses placeholders:
- `__IMAGE__`: uploaded image
- `__PROMPT__`: motion prompt
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

- Adapter code is committed, but no real Space request has been made.
- No model or endpoint is yet marked production-ready.
- A valid output file signature is checked, but playback, duration, resolution, motion quality, and commercial license must still be checked.
- This adapter has no retry loop to avoid wasting quota.
- It is not wired into automatic CI or automatic video generation.
- YouTube upload remains a separate, manually approved, private-only step.
- Never set a Hugging Face token in source code or paste it into chat. Use a secret manager/environment variable only if the selected Space needs authentication.
