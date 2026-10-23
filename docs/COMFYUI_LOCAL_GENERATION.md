# Local ComfyUI scene generation

This helper runs against a ComfyUI instance that you control. GitHub Actions does not host the models, and this repository does not bundle model weights or a ready-made workflow.

## Prerequisites

- Python 3.10 or newer.
- ComfyUI installed and running on a machine with a compatible model.
- A working image workflow exported in **API format** from that ComfyUI installation.
- Optional: a working image-to-video workflow and its required custom nodes/models.

Do not expose an unauthenticated ComfyUI port to the public internet. Use the local default URL unless you have deliberately configured a protected private endpoint.

## Prepare prompts

Generate the validated scene prompt file with the existing planner/orchestrator, or provide a JSON list like:

```json
[
  {
    "scene": 1,
    "image_prompt": "A historically grounded wide view of an ancient Indian stepwell at sunrise",
    "negative_prompt": "text, watermark, blurry, distorted architecture"
  },
  {
    "scene": 2,
    "image_prompt": "Close-up of stone carvings at the same stepwell, warm morning light",
    "negative_prompt": "text, watermark, blurry"
  }
]
```

Save it as `dist-cinematic/scene-prompts.json` or pass another path with `--prompts`. Use a separate scene record for every planned scene.

## Configure the image workflow

In ComfyUI, load a workflow that is already known to generate a valid PNG, then export it using the API-format workflow option. In the exported JSON, put these exact placeholders in the corresponding text/filename inputs:

- `__POSITIVE_PROMPT__` — positive prompt text input.
- `__NEGATIVE_PROMPT__` — negative prompt text input.
- `__OUTPUT_PREFIX__` — Save Image filename prefix.

The Save Image node should create PNG files with a basename starting with the prefix's scene name, for example `scene-01_00001_.png`. The helper expects exactly one matching PNG for each scene. If the workflow saves extra images or uses a different prefix, update the workflow so each prompt yields one unambiguous output.

## Generate images locally

Start ComfyUI, then run from the repository root:

```bash
python scripts/comfyui_generate_assets.py \
  --base-url http://127.0.0.1:8188 \
  --prompts dist-cinematic/scene-prompts.json \
  --image-workflow /path/to/image-workflow-api.json
```

The helper checks ComfyUI availability, validates prompt records and workflow placeholders, waits for each job, checks output file signatures, and saves selected scene images to `assets/cinematic-scenes/scene-01.png`, `scene-02.png`, etc. Existing scene images are kept and skipped; remove an image intentionally if you want that scene regenerated.

## Optional image-to-video workflow

A video workflow must contain the same three placeholders plus `__INPUT_IMAGE__` in its Load Image node. It must generate MP4 output whose filename prefix starts with the requested scene prefix, e.g. `scene-03-motion`. After testing the workflow independently in ComfyUI, run:

```bash
python scripts/comfyui_generate_assets.py \
  --prompts dist-cinematic/scene-prompts.json \
  --image-workflow /path/to/image-workflow-api.json \
  --video-workflow /path/to/video-workflow-api.json \
  --animate-every 3
```

Video generation is optional and depends on the model, workflow and custom nodes installed locally. It is not guaranteed by this script alone.

## Render and verify

Once at least two scene images exist, render a review video:

```bash
python scripts/generate_cinematic_video.py
python scripts/check_cinematic_quality.py --help
```

Use the quality-check command options documented by the script in your checkout and inspect the video, thumbnail, narration, captions and render report manually. The GitHub Actions cinematic workflow only renders supplied scene images; it does not run ComfyUI or create AI images.

## Safety and status

- This helper never uploads or publishes to YouTube.
- Keep model files and private credentials out of Git.
- Do not describe generation as verified until it has run successfully against your actual local ComfyUI workflow and model.
