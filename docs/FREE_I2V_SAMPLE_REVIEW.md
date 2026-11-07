# Free image-to-video sample: review and handoff

## Sample inspected (owner-provided, 2026-11-01)

A manually generated MP4 from the public NiftyVid browser demo was inspected locally.

| Check | Result |
|---|---|
| Container / codec | MP4 / H.264 |
| Duration | 3.5625 seconds |
| Frame size | 832 × 480 |
| Frame rate | 16 fps |
| File size | 913,321 bytes |
| Audio | None |
| Readability | ffprobe successfully read the video stream |
| Motion | Frame-to-frame scene motion is present; this is not only a Ken Burns still-image zoom |

### Visual review outcome

**Not approved as a production-quality clip yet.** The sampled frames show the woman moving out of frame, while the man has little meaningful movement. A conspicuous bright/orange artifact appears on the man's chest in later frames, and the woman's body/appearance changes between samples. These are visible generative artifacts and subject-consistency failures.

This is a successful technical proof that a free browser demo can return a playable moving MP4. It is not evidence that the provider is reliable, that its terms/quota are guaranteed, or that the output meets the cinematic quality bar. Do not use this clip in a published video without a fresh owner review.

## How to hand off an approved clip to the renderer

Keep the original source image and its generated clip together in the scene directory:

- `assets/cinematic-scenes/scene-01.png`
- `assets/cinematic-scenes/scene-01.mp4`

For multiple short clips that form one scene timeline, use:

- `scene-01-clip-001.mp4`
- `scene-01-clip-002.mp4`
- and so on.

Run the renderer:

```bash
python scripts/generate_cinematic_video.py \
  --scenes assets/cinematic-scenes \
  --output dist-cinematic \
  --scene-plan assets/cinematic-scenes/scene-plan.json
```

The renderer probes each clip, scales/crops it to 1280×720 at 30 fps, and records the source clip names in `render-report.json`. It fails rather than silently freezing or looping footage when the supplied clips are shorter than the scene's planned duration. The original clip is not modified.

## Acceptance gate before production

1. Confirm the provider is still free for the intended use and check its current quota and license/terms.
2. Generate a fresh clip and inspect several frames plus full playback.
3. Reject clips with face/body morphing, flicker, anomalous objects, unwanted exits from frame, or camera motion that contradicts the scene.
4. Ensure enough unique clips cover the planned scene duration; do not loop a short clip to fake duration.
5. Render at 1280×720/30 fps (or higher source quality) and inspect the final output.
6. Keep natural Hindi narration, speech-aligned captions, licensed music, thumbnail and the 8–10 minute duration as separate release gates.
7. Never enable public upload. Any YouTube upload remains private-only and requires explicit owner approval.

## Current project status

The renderer can already consume and normalize real image-to-video clips. The remaining gap is not MP4 transcoding: it is a dependable, verified free generation provider and a quality-approved sequence of clips, plus natural Hindi narration and a complete end-to-end 8–10 minute run. No provider API is configured by this sample, no paid fallback was attempted, and no upload was performed.
