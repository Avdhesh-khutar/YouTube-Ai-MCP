# Free-only cinematic workflow policy

The cinematic pipeline must not require paid APIs, subscriptions, paid credits, or
billing-enabled cloud services. Do not add a provider that can incur charges.

## Preferred free stack

- Research: manual/source-backed research using public sources; any automated web
  provider must be reviewed for usage limits and terms before integration.
- Script drafting: locally hosted open-source language model through Ollama, if the
  user's computer has enough RAM/VRAM. No paid cloud LLM fallback.
- Images: local ComfyUI with models the user is legally allowed to download/use.
- Image-to-video: local open-source ComfyUI-compatible workflow only; skip animation
  when hardware cannot run it rather than falling back to paid cloud credits.
- Hindi voiceover: locally installed open-source TTS with Hindi support; verify voice
  quality and license before selecting a model.
- Music: original user-created audio or verified free-to-use/royalty-free tracks whose
  license permits the intended YouTube use.
- Subtitles/rendering: local open-source tools such as FFmpeg and subtitle utilities.
- Upload: existing YouTube API integration only after the user configures OAuth securely;
  do not use paid third-party upload services. YouTube upload itself must remain Private.

## Mandatory safeguards

- No paid API endpoints, paid fallback providers, subscription upsells, or credit-based
  generation services in the default workflow.
- No billing-enabled cloud calls.
- Never ask the user to paste secrets in chat or commit them to Git.
- Never enable public publishing; upload privacy must be hard-coded/enforced as private.
- If hardware, model license, Hindi quality, or a provider's free status is uncertain,
  pause that stage and explain the constraint. Do not silently switch to a paid service.
- Before downloading a large model, report its approximate size and ask the user to
  check disk space and hardware.
- Free-tier terms and quotas can change; verify current terms before any remote integration.

## Honest capability boundary

A free-only pipeline may run more slowly, produce lower-quality motion, or require
manual setup depending on the user's computer. The repo must not claim fully automatic
end-to-end generation until every stage has an implemented adapter and has passed an
end-to-end test on real assets.
