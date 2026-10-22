# Cinematic video pipeline (review-only)

This pipeline turns a sequence of AI-generated scene images into a 16:9 cinematic MP4. It applies slow camera movement to stills and uses a matching MP4 clip whenever one exists, so selected scenes can have true image-to-video animation.

## 1. Prepare the scene assets

Create `assets/cinematic-scenes/` and add at least two images named in order:

- `scene-01.png`
- `scene-02.png`
- `scene-03.png`

Use your preferred open-source image model locally (for example, a compatible Stable Diffusion/SDXL workflow) to create the images. Keep each scene visually consistent and use images you have rights to use. The renderer does not call a paid API or generate images itself.

For scenes that should have actual AI motion, put a video beside its image with the same base name:

- `scene-02.png`
- `scene-02.mp4`

The MP4 clip replaces the still-image camera movement for that scene. Generate clips with a local/open-source image-to-video workflow where your hardware supports it; model requirements vary and may need a GPU. If a clip is absent, the still image receives a slow Ken Burns zoom. Do not expect a true moving subject from a still-only scene.

Optional files in the same directory:

- `voiceover.mp3` or `voiceover.wav`: narration track
- `captions.srt`: subtitles (UTF-8)

If no narration is provided, the result is silent. Add a reviewed Hindi voice-over before publishing. Captions are burned in when FFmpeg subtitle support is available.

## 2. Render locally

Install FFmpeg, then run:

```bash
python scripts/generate_cinematic_video.py --seconds-per-scene 5
```

The output is in `dist-cinematic/`:

- `cinematic-video.mp4`
- `thumbnail.jpg` (first scene image, not a finished designed thumbnail)
- `render-report.json`

## 3. Render in GitHub Actions

After adding the assets to the feature branch, open **Actions → Cinematic video review package → Run workflow**. The workflow stores a review artifact for 7 days. It does not upload to YouTube.

## Important quality and safety limits

- This is a rendering pipeline, not a one-click generative AI service. Image generation and image-to-video generation happen separately with your chosen local model/tool.
- GitHub-hosted runners do not provide a dependable GPU for open-source video generation; generate the assets locally, then render the final cut in Actions.
- Review the output for visual glitches, scene continuity, Hindi pronunciation, caption timing, music rights, and thumbnail readability.
- No upload or public publishing is implemented or enabled by this workflow. Do not add upload secrets or publishing steps without explicit approval.


## 0. Turn a Hindi script into image prompts

Save your narration as UTF-8 text at `assets/cinematic-scenes/script.txt`, then run:

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
