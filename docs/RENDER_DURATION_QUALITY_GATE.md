# Render duration quality gate

The duration gate checks the **actual media file**, not the scene-plan total or render manifest.

## Run locally or in a compatible CI environment

After rendering a candidate MP4, run:

```bash
python scripts/verify_render_duration.py dist-cinematic/cinematic-video.mp4 --require-audio
```

The default accepted runtime is 480–600 seconds (8–10 minutes). To test another target window, supply `--min-seconds` and `--max-seconds`. The gate requires `ffprobe` to be installed and available on PATH.

The command checks that:
- the file exists and can be parsed by ffprobe;
- a video stream exists and has a codec plus non-zero width and height;
- actual container duration is within the configured range;
- an audio stream exists when `--require-audio` is supplied.

Example success output includes actual duration, codec, dimensions, and audio presence. A short valid MP4 (for example a 4-second AI-motion sample) intentionally fails the default 8–10 minute runtime gate; use a separate short-test window if validating a provider proof-of-motion clip.

## Important limitation

Passing this gate does **not** establish that the footage contains genuine AI-generated motion, that narration/captions are synchronized, or that the content is legally cleared. Those remain separate manual and automated acceptance checks. It also does not render, upload, or publish anything.

No AI provider is called by this check. No paid service or YouTube upload is involved.
