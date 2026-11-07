# Browser-only, free-only cinematic workflow

This guide is the source of truth for users who do not want to download or install
anything on Windows and do not want paid APIs, subscriptions, or credits.

## Important reality check

The repository does not yet provide a verified, fully automatic, end-to-end free
browser-only service that creates an 8–10 minute Hindi cinematic video from one topic.
The current orchestrator is a scaffold and must not be described as complete.

A browser-only workflow can keep code and project files on GitHub, but AI image/video
generation, long-form Hindi voiceover, rendering, storage, and YouTube upload each need
a working provider or execution environment. Free tiers may have quotas and change their
terms. Do not assume a service is free just because it opens in a browser.

## Rules

- Do not install Ollama, ComfyUI, Python, FFmpeg, or other software on the user's laptop.
- Do not ask the user to download model weights or media tools.
- Do not call paid APIs, use paid credits, enable billing, or silently fall back to paid
  services.
- Do not use Comfy Cloud or other credit-based cloud generation for the default workflow.
- Do not store credentials in repository files, commits, logs, or chat.
- Never publish publicly. Any eventual YouTube upload must explicitly set privacy to
  `private` and require owner approval.
- Do not merge the feature branch into `main` without the user's explicit approval.

## What works in the repository today

- GitHub-hosted source code and CI checks.
- A review-only cinematic render pipeline and workflow scaffold.
- A local Ollama script-generator option, which does require installing software and
  therefore is **not suitable for this user's browser-only setup**.
- Quality checks and a Private-only upload policy.

## What is still missing for true browser-only automation

1. A verified free research/script provider with documented current terms.
2. Free browser-accessible image and image-to-video generation with sufficient quota.
3. A Hindi voiceover provider that is free for the intended use.
4. A browser-hosted rendering environment that can handle a 8–10 minute video without
   local installation and without paid compute.
5. Secure YouTube OAuth setup and a tested Private-only upload adapter.
6. An end-to-end test with real assets, including duration, audio, subtitles, and privacy
   verification.

Until all of these are verified, the workflow must stop at the missing stage and explain
the blocker rather than pretending the video is complete or requesting payment.

## Current safe next step

Continue development in the GitHub feature branch and run CI checks. The user does not
need to install or download anything on Windows to review repository changes. Creating a
real final video still depends on finding a compatible free browser service for every
required generation/rendering stage.
