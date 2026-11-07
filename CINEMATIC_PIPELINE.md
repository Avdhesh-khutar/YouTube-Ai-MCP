# Cinematic video pipeline (review-only)

This pipeline turns a sequence of AI-generated scene images into a 16:9 cinematic MP4. It applies slow camera movement to stills and uses a matching MP4 clip whenever one exists, so selected scenes can have true image-to-video animation.

## 1. Prepare the scene assets

Create `assets/cinematic-scenes/` and add at least two images named in order:

- `scene-01.png`
- `scene-02.png`
- `scene-03.png`

Use your preferred open-source image model locally (for example, a compatible Stable Diffusion/SDXL workflow) to create the images. Keep each scene visually consistent and use images you have rights to use. The renderer does not call a paid API or generate images itself. Each scene now gets a
subtle 0.45-second fade-in and fade-out at its boundaries; for a sequence of short motion
clips, fades are applied at the start and end of the scene rather than between every clip.

For scenes that should have actual AI motion, put a video beside its image with the same base name:

- `scene-02.png`
- `scene-02.mp4`

The MP4 clip replaces the still-image camera movement for that scene. Generate clips with a local/open-source image-to-video workflow where your hardware supports it; model requirements vary and may need a GPU. If a clip is absent, the still image receives a slow Ken Burns zoom. Do not expect a true moving subject from a still-only scene.

Optional files in the same directory:

- `voiceover.mp3` or `voiceover.wav`: narration track
- `background-music.mp3` or `background-music.wav`: optional music bed
- `captions.srt`: subtitles (UTF-8), burned in with bold white text, dark outline,
  subtle shadow, and a bottom-safe margin for mobile readability

If no narration or music is provided, the result is silent. When both narration and
background music are present, the renderer mixes music under the voice at a conservative
12% gain; narration remains the primary audio. Music loops to cover the timeline, fades
in over 2 seconds, and fades out over the final 2 seconds of the planned timeline. Use
music you have rights to use. Captions are burned in with a readable bold style when FFmpeg subtitle support is
available. This is styled line-level SRT captioning, not word-by-word kinetic karaoke
highlighting; the optional `scripts/align_hindi_captions.py` can request word timestamps from
faster-whisper and group them into short caption lines. This is speech-recognition
timing, not forced alignment, and Hindi spelling/punctuation still needs human review.

## 2. Render locally

For a reference-video-inspired animated title treatment, enable the optional motion-graphics
pass. It adds a short animated lower-third title at the beginning of each scene. The title
uses an explicit `title` in the scene plan when present, otherwise it derives a compact
title from that scene's narration:

```bash
python scripts/generate_cinematic_video.py --scene-plan dist-cinematic/scene-plan.json --motion-graphics
```

This pass requires an FFmpeg build with the `drawtext` filter (libfreetype). It is a
first editing layer, not a replacement for full kinetic typography or custom transitions.
For an optional music bed, add `background-music.mp3` (or WAV) beside the narration;
the renderer mixes it quietly beneath the voice. It is opt-in so existing render jobs
remain compatible.


Install FFmpeg, then run:

```bash
python scripts/generate_cinematic_video.py --seconds-per-scene 5
```

The output is in `dist-cinematic/`:

- `cinematic-video.mp4`
- `thumbnail.jpg` (first scene image, not a finished designed thumbnail)
- `render-report.json`

## Real FFmpeg smoke test in CI

The feature branch also runs a short, real FFmpeg render smoke test. It creates
disposable synthetic scene images, a test-tone WAV, and a tiny SRT file, renders
an MP4 with the actual renderer, probes the resulting streams with ffprobe, and
runs `scripts/check_cinematic_quality.py`. The workflow stores a short proof
artifact for 7 days.

This verifies that FFmpeg can execute the rendering/muxing/subtitle path and that
the quality-gate plumbing accepts a valid short test file. The synthetic tone is
not Hindi narration, the images are not AI-generated footage, and this short
test does not verify natural voice quality, real AI motion, or the 8–10 minute
full-length target. Those require real user-approved assets and separate review.

## 3. Render in GitHub Actions

After adding the assets to the feature branch, open **Actions → Cinematic video review package → Run workflow**. The workflow stores a review artifact for 7 days. It does not upload to YouTube.

## Important quality and safety limits

- This is a rendering pipeline, not a one-click generative AI service. Image generation and image-to-video generation happen separately with your chosen local model/tool.
- GitHub-hosted runners do not provide a dependable GPU for open-source video generation; generate the assets locally, then render the final cut in Actions.
- Review the output for visual glitches, scene continuity, Hindi pronunciation, caption timing, music rights, and thumbnail readability.
- No upload or public publishing is implemented or enabled by this workflow. Do not add upload secrets or publishing steps without explicit approval.


## 0. Turn a Hindi script into image prompts

Copy `assets/cinematic-scenes/script.example.txt` to `assets/cinematic-scenes/script.txt` and edit it with your own narration. Then run:

```bash
python scripts/plan_cinematic_scenes.py --max-scenes 12
```

It creates `dist-cinematic/scene-prompts.md` and `scene-prompts.json`. Each scene has a visual prompt and negative prompt. These are prompt drafts, not generated images. Use them in your local image model and export each image in scene order.

Suggested local-first workflow:
1. Generate scene images with a local Stable Diffusion/SDXL-compatible UI or workflow.
2. For 2–4 key scenes, optionally generate image-to-video clips with a compatible local video model (hardware needs vary).
3. Add a reviewed voice-over and matching SRT subtitles.
4. Run the cinematic renderer and inspect the MP4 before considering any upload.

The GitHub Actions runner is for rendering, not GPU-based image/video generation. Do not put model credentials or private tokens into the repository.

### Speech-timed Hindi captions (optional)

After preparing `voiceover.wav` (or `voiceover.mp3`), install the optional
`faster-whisper` dependency in the rendering environment and run:

```bash
python scripts/align_hindi_captions.py --audio assets/cinematic-scenes/voiceover.wav --output assets/cinematic-scenes/captions.srt --language hi --model small --compute-type int8
```

The recognizer requests word timestamps and groups them into short readable SRT
lines. The output path is the same `captions.srt` consumed by the renderer.
CPU runtime and memory depend on model size and audio duration; on an 8 GB
machine, start with `tiny` or `base` if `small` is too heavy. This step is
optional and is not run automatically in GitHub Actions. Always review Hindi
recognition, punctuation, and timing against the audio before publishing.



## 4. Generate assets with local ComfyUI (open-source-first)

The optional `scripts/comfyui_generate_assets.py` adapter connects to a ComfyUI server you run yourself (default `http://127.0.0.1:8188`). It does not call a paid cloud API. Install ComfyUI and the model/workflow nodes you choose separately; model size and GPU/VRAM needs vary.

1. Start ComfyUI locally and confirm its web UI opens.
2. In ComfyUI, build an image workflow with a text-positive prompt input, a negative prompt input, and a Save Image output. Export it in **API format**.
3. In that exported JSON, replace the actual positive text field with the literal `__POSITIVE_PROMPT__`, negative text field with `__NEGATIVE_PROMPT__`, and the Save Image filename prefix with `__OUTPUT_PREFIX__`.
4. Prepare a Hindi script at `assets/cinematic-scenes/script.txt`, then create prompts:
   ```bash
   python scripts/plan_cinematic_scenes.py --max-scenes 8
   ```
5. Generate the scene images:
   ```bash
   python scripts/comfyui_generate_assets.py --image-workflow workflows/comfyui-image-api.json
   ```

For selected scenes with real motion, export a separate ComfyUI API-format image-to-video workflow. Its Load Image node's image input must be the literal `__INPUT_IMAGE__`; also use the same prompt and output-prefix tokens described above. Then run:

```bash
python scripts/comfyui_generate_assets.py --image-workflow workflows/comfyui-image-api.json --video-workflow workflows/comfyui-video-api.json --animate-every 3
```

This attempts animation for every third scene. Confirm your chosen video workflow saves MP4 files. ComfyUI custom nodes and output schemas vary, so the exported workflow must be tested with your installed models. The adapter will report an error rather than silently claiming success when no output image/video is returned.

**Important:** The ComfyUI API workflow JSON files are model/node-specific and are not included in the repository. Do not commit large model weights or secrets. If ComfyUI runs on your own computer, run this script on that computer; a GitHub-hosted runner cannot reach your `127.0.0.1`.
