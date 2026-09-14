---
name: dual-image-pipeline
description: High-speed parallel image generation for vertical TikTok storyboards adapting to user resources across Antigravity (Gemini 3.1 Flash Image), Codex (GPT-Image 2.5), and zero-cost free generation (Pollinations FLUX) with automatic failover.
---

# Dual-Vendor & Financially Adaptive Image Pipeline

[English](SKILL.md) · [Русский](SKILL.ru.md) · [Українська](SKILL.uk.md)

`SKILL.md` is the installed entrypoint; the other language files are translations of the same skill. This skill accelerates storyboard image generation for TikTok videos by adapting to the creator's financial situation — running **Antigravity (Gemini 3.1 Flash Image)** and **Codex (GPT-Image 2.5)** in parallel when subscriptions exist, or falling back seamlessly to **100% free zero-cost generation** for low-income creators and church volunteers.

## Financial Adaptability Tiers

Christian ministry serves everyone regardless of budget. The pipeline detects available tools and operates across three tiers:

1. **Tier 1 (Full Dual Access — AGY + Codex)**: Runs concurrent parallel generation between Gemini 3.1 Flash Image (3–4 workers) and GPT-Image 2.5 Flare (1–2 workers). Delivers maximum speed (~15–20s per full video).
2. **Tier 2 (Single Access — AGY only or Codex only)**: Automatically routes the entire queue through the single available engine without demanding the missing tool.
3. **Tier 3 (Zero-Cost / No Subscriptions)**: For volunteers or churches without paid plans, generation routes automatically to **Pollinations.ai (FLUX.1)**. Requires zero API keys, zero accounts, and zero credit cards.

All tiers produce vertical images ($768 \times 1376$ or $1024 \times 1792$) scaled cleanly to Full HD $1080 \times 1920$ by `build_video.py`.

## Visual Policy and Style Anchoring

To ensure aesthetic consistency across scenes and engines:

- **Style Anchor**: A unified style block (`Visual Bible`) is prepended to every prompt, specifying artistic medium, camera optics, color temperature, and lighting (e.g. `cinematic 35mm photography, natural daylight, kodak portra tones, soft focus background`).
- **Default Visual Presentation**: Follows `evangelical_baptist` guidelines: Scripture, prayer, Christian fellowship, acts of service, and God's creation. Do not introduce halos, devotional icons, iconostases, onion domes, or later liturgical vestments. Explicit user overrides (such as `interdenominational_unity`) take precedence.

## Usage

Generate all storyboard scenes in parallel (auto-detects tier):

```sh
python3 scripts/generate.py --storyboard '/absolute/storyboard.json' --output-dir '/absolute/images'
```

Force 100% free zero-cost mode (no subscriptions required):

```sh
python3 scripts/generate.py --storyboard '/absolute/storyboard.json' --output-dir '/absolute/images' --free
```

Generate a single test image:

```sh
python3 scripts/generate.py --prompt 'Peaceful mountain valley at sunrise, wildflowers, soft golden morning light' --output '/absolute/scene-01.png' --aspect-ratio 9:16
```

Detailed vendor specifications, quotas, and free endpoints are documented in [references/providers.md](references/providers.md).
