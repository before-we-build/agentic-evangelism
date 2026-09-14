---
name: dual-image-pipeline
description: High-speed parallel image generation for vertical TikTok storyboards combining Antigravity (Gemini 3.1 Flash Image) and Codex (GPT-Image 2.5) concurrently with automatic failover.
---

# Dual-Vendor High-Speed Image Pipeline

[English](SKILL.md) · [Русский](SKILL.ru.md) · [Українська](SKILL.uk.md)

`SKILL.md` is the installed entrypoint; the other language files are translations of the same skill. This skill accelerates storyboard image generation for TikTok videos by running **Antigravity (AGY / Gemini 3.1 Flash Image)** and **Codex (OpenAI GPT-Image 2.5)** in parallel, cutting batch generation time down to seconds.

## Architecture and Concurrency

When preparing vertical TikTok videos from a storyboard (e.g. via `suno-tiktok-video`), generating 8–12 scenes serially is the primary time bottleneck. The dual-vendor pipeline removes this bottleneck by dispatching tasks to two independent generation pools simultaneously:

1. **Antigravity Pool (`agy`)**: Dispatches concurrent calls to Gemini 3.1 Flash Image (optimal pool: 3–4 parallel jobs). Native 9:16 aspect ratio ($768 \times 1376$).
2. **Codex Pool (`codex`)**: Dispatches concurrent calls via Codex CLI / GPT-Image 2.5 Flare (optimal pool: 1–2 parallel jobs). Native 9:16 aspect ratio ($1024 \times 1792$).
3. **Automatic Failover**: If either vendor encounters rate limits (HTTP 429), quota exhaustion, or temporary API failures, the other vendor automatically absorbs pending jobs without stalling the pipeline.

Both native resolutions are scaled and padded seamlessly to Full HD $1080 \times 1920$ by `build_video.py`.

## Visual Policy and Style Anchoring

To prevent visual style drift when mixing two image engines across scenes:

- **Style Anchor**: A unified style block (`Visual Bible`) is prepended to every prompt, specifying artistic medium, camera optics, color temperature, and lighting (e.g. `cinematic 35mm photography, natural daylight, kodak portra tones, soft focus background`).
- **Default Visual Presentation**: Follows `evangelical_baptist` guidelines: Scripture, prayer, Christian fellowship, acts of service, and God's creation. Do not introduce halos, devotional icons, iconostases, onion domes, or later liturgical vestments. Explicit user overrides (such as `interdenominational_unity`) take precedence.

## Usage

Generate all storyboard scenes in parallel:

```sh
python3 scripts/generate.py --storyboard '/absolute/storyboard.json' --output-dir '/absolute/images'
```

Generate a single test image:

```sh
python3 scripts/generate.py --prompt 'Peaceful mountain valley at sunrise, wildflowers, soft golden morning light' --output '/absolute/scene-01.png' --aspect-ratio 9:16
```

Detailed vendor specifications, quotas, and error codes are documented in [references/providers.md](references/providers.md).
