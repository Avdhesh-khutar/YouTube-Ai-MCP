# AI-motion integration status

## Verified status

- The renderer accepts a real scene clip named alongside its source image (for example, `scene-02.png` and `scene-02.mp4`).
- If no matching clip exists, the renderer uses a Ken Burns zoom on the still image. This is not AI-generated motion.
- `scripts/hf_space_i2v.py` is an opt-in adapter for a public Hugging Face Gradio Space whose exact API endpoint and input schema must be inspected first.
- The NiftyVid browser demo is a separate candidate and its custom browser/Worker flow has not been integrated with the Gradio adapter.
- No provider is configured in `config/cinematic-workflow.example.json`.
- YouTube upload is disabled by default in the example config.
- A green CI run proves code/tests passed; it does not prove a real AI-generated MP4 was returned.

## Real clip acceptance gate

Do not mark AI-motion complete until all checks pass:

1. A non-sensitive source image was used with a provider that was confirmed to be free for the test.
2. The provider returned an actual video file, not a URL that the adapter cannot safely resolve or a still image.
3. The saved output passes `ffprobe` and has a readable video stream with codec and non-zero dimensions.
4. Playback confirms motion in the scene content, not only a zoom/pan effect.
5. The motion is reviewed for warping, flicker, sudden cuts, and subject morphing.
6. The matching scene renderer uses the MP4 and the render report identifies it as an image-to-video clip.
7. No paid fallback or YouTube upload was used.

## Manual free-browser test

Candidate: [NiftyVid](https://igorcsis.github.io/nifty-vid/). Check current availability and terms in the browser before use; free public GPU availability can change.

Prompt for a 3–4 second initial test:

`Cinematic natural movement: camera slowly pushes forward; tree leaves sway gently in a light breeze; subtle mist drifts in the background; realistic physics, stable subject, no scene cuts or morphing, preserve the original composition.`

Use only a non-sensitive image. Do not enter payment details, API tokens, or private credentials. If the demo is unavailable or fails, record the test as blocked rather than switching to a paid provider.

## Current blocker

A real browser-generated MP4 was provided in the conversation and inspected locally on 2026-10-30. The file was not committed to the repository; this is a manual artifact check, not CI verification. Observed metadata: H.264 video, 832×480, duration 3.5625 seconds, file size 3,168,744 bytes. Four sampled frames showed substantial pixel changes between timestamps, so the clip is not a single identical still frame. This does not by itself prove natural/acceptable motion quality, and the file has not yet been run through this repository's scene renderer.

Current evidence:
- NiftyVid generated a downloadable short MP4: PASS.
- Container/codec/duration readable with ffprobe: PASS.
- Sampled frames vary over time: PASS (basic temporal-change check only).
- Human review for warping/flicker/subject morphing: PENDING.
- Matching-scene renderer integration and render-report verification: PENDING.
- Full 480–600 second video generation: NOT VERIFIED.

Therefore, the manual short-clip generation test is successful, but image-to-video integration and the end-to-end 8–10 minute cinematic pipeline remain incomplete. Do not claim full automation is complete.


## Duration mismatch to resolve before end-to-end claims

The current scene-plan model allows long narration scenes (for example, 120 seconds), while the shortlisted public image-to-video demos typically return only a few seconds per generated clip. The current renderer trims an available matching MP4 to the planned scene duration but does not extend a shorter clip to fill that duration; FFmpeg can therefore produce a segment shorter than the manifest's declared duration. The render report currently records planned duration, not independently probed output duration.

This is a real integration gap, not a cosmetic issue. Before claiming an 8–10 minute cinematic render, implementation must do both:

1. Probe each input clip and the final MP4 with ffprobe; report actual durations separately from planned durations and fail quality checks if the final runtime falls outside the requested 480–600 second range.
2. Support multiple short motion clips per long narration scene (or explicitly create a timeline of short scenes with aligned narration/subtitles). Do not freeze a 3–4 second clip for the remaining minutes or silently loop it as if it were continuous natural motion.

Until this is implemented and tested with real clips, a valid MP4 file alone is not proof that the full-length cinematic workflow works.
