---
name: dual-image-pipeline
description: Coordinate consistent TikTok storyboard illustrations through an actually available image tool, using anchor-first review and bounded parallel batches. Does not provide image generation or guarantee two vendors.
---

# Parallel storyboard images

[English](SKILL.md) · [Русский](SKILL.ru.md) · [Українська](SKILL.uk.md)

This skill organizes independent scene illustrations. Check which image tool the host actually exposes. In Codex, follow the installed `imagegen` skill and use the built-in `image_gen` tool by default. Installing this folder does not install a generation service, authorize an external API, or guarantee access to two providers.

Define one visual bible and stable character description. Generate and inspect a style anchor, then a test scene from another angle. Once approved, dispatch independent assets in bounded parallel batches. In Codex code mode, use one `tools.image_gen__imagegen({prompt})` call per asset inside `Promise.allSettled(assets.map(...))`. Give every asset a stable ID before dispatch; record its prompt, tool, result and saved path by ID rather than completion order. Inspect each image, keep successes, and retry only failures. Record the actual route in `storyboard.json` (for example `generation_mode: built_in_imagegen`) and the asset IDs in each submitted batch, so later reviews can verify how the images were made. Concurrent submission does not guarantee that the remote service processes requests at the same time or at a fixed speed.

Follow the song's visual policy, defaulting to `evangelical_baptist`: Scripture, prayer, fellowship, service and creation as the lyrics support. Exclude halos, devotional icons, iconostases, onion domes and unrequested vestments. Respect explicit choices such as `interdenominational_unity`. Save the final images with the storyboard, not only in the generator's default directory.

`scripts/generate.py` is an optional legacy CLI route, not the built-in Codex image tool. Its `--dry-run` writes tiny test images, not usable artwork. Live CLI mode requires `--allow-external-cli` and explicit authorization for the selected external service; `--free` selects Pollinations and `--allow-free-fallback` permits it after another provider fails. Verify each provider's actual image command, network access and current costs before opting in. An `agy` or `codex` binary alone does not prove image-generation access. [Provider notes](references/providers.md) explain these limits; they are not a price list.
