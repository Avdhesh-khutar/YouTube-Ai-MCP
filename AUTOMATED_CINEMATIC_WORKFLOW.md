# Fully automated cinematic YouTube workflow — implementation plan

## User defaults
- Language: Hindi
- Target duration: 8–10 minutes
- YouTube privacy: PRIVATE only
- Publishing: never public or scheduled without a separate explicit approval
- Repository safety: changes stay on the feature branch and draft PR; do not merge to main without owner approval.
- Secrets: never commit OAuth refresh tokens, API keys, or upload handoff tokens.

## Target experience
The owner submits a topic and optional audience/style. A single orchestrator should then:
1. Research the topic from reliable sources and retain source URLs/notes.
2. Produce a Hindi outline and narration targeting 8–10 minutes; flag uncertain claims.
3. Create a scene plan with per-scene narration, image prompt, motion prompt, and duration.
4. Generate scene images through a configured image provider.
5. Animate selected scenes through a configured image-to-video provider; use slow FFmpeg motion only as an explicit fallback.
6. Generate Hindi narration with a configured TTS provider and mix licensed/owned music and sound effects.
7. Generate Hindi SRT captions, preferably aligned to actual speech.
8. Render a 1280x720 or 1920x1080 MP4, loudness-normalized audio, transitions, thumbnail, title, description, and source/asset manifest.
9. Run automated checks (duration, file integrity, caption coverage, audio stream, thumbnail) and create a review package.
10. Upload only as PRIVATE using the existing YouTube OAuth integration after the configured approval policy is satisfied. Return the YouTube video ID/URL and metadata. Never change privacy to public.

## Required implementation stages
### Stage A — workflow contract and orchestration
- Add a validated config for language, duration, provider names, scene count, output directory, privacy status, and approval requirement.
- Add an orchestrator CLI that executes only configured stages, writes a resumable job manifest, records provider/model/source metadata, and stops with a clear error if a required provider or credential is missing.
- Keep generated media out of Git; store it in job workspace or short-lived private artifacts.

### Stage B — research and script
- Add a research adapter with citation/source capture and retry/rate-limit handling.
- Generate Hindi script + scene plan as structured JSON; validate total estimated narration length against the 8–10 minute target (roughly 1,000–1,300 Hindi words is only a starting estimate; actual speech duration must be measured).
- Do not present unsourced claims as verified facts.

### Stage C — media providers
- Add provider interfaces for image generation, image-to-video, Hindi TTS, and music/SFX. Select concrete providers only after API availability, terms, pricing, data handling, and output rights are checked.
- Comfy Cloud in the browser is not automatically an API endpoint for this repository. The existing ComfyUI adapter targets a reachable ComfyUI API with exported API-format workflows; hosted cloud access must be explicitly supported/configured before automation can call it.
- Local GPU generation is not available to a GitHub-hosted runner by default. Prefer a supported hosted API or a user-managed worker; enforce budgets and timeouts.
- If image-to-video fails, fall back only to a clearly reported still-image motion effect; never label that as generated video.

### Stage D — assembly and quality
- Use FFmpeg to assemble scenes, voiceover, licensed/owned music, transitions, and subtitles.
- Validate the final file with ffprobe; generate a designed thumbnail and metadata; keep an asset/source manifest.
- Include a review artifact before upload until the owner opts into a different policy.

### Stage E — private YouTube upload
- Reuse the existing OAuth-protected upload capability only from a trusted server-side runtime. Do not place OAuth tokens in the repository, workflow logs, client-side code, or chat.
- Upload privacy must be hard-coded/validated as `private`; title, description, category, and tags are passed as metadata.
- Avoid duplicate retries: persist job state and check upload status before retrying.
- Require OAuth re-consent if the upload scope is missing. Keep public publishing disabled.

## Acceptance criteria
- One topic starts a resumable end-to-end job without manually creating each scene.
- Output is Hindi, 8–10 minutes, with research notes, script, scene plan, generated visuals, narration, music/SFX, SRT, MP4, thumbnail, metadata, and a source/asset manifest.
- Job reports provider failures and costs/quotas clearly; no hidden paid calls.
- Upload is private, deduplicated, and returns the video ID; public publishing is impossible by default.
- Automated tests cover configuration validation, missing credentials, failed provider calls, render validation, and private-only upload policy.

## Important current state
The current cinematic PR is a scaffold: prompt planning, a ComfyUI API adapter, and FFmpeg assembly exist, but actual provider-backed research, image/video generation, TTS, music, orchestration, and automated upload are not yet a verified end-to-end system. Do not claim the complete pipeline works until provider integrations are configured and an 8–10 minute test run is reviewed.
