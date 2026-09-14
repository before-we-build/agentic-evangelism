# Image Generation Providers Reference

[English](providers.md) · [Русский](providers.ru.md) · [Українська](providers.uk.md)

This reference outlines technical specifications, native resolutions, concurrency rules, and failover behavior for the dual-vendor pipeline.

## 1. Antigravity (`agy` / Gemini Image)

- **Engine**: Gemini 3.1 Flash Image.
- **Native Resolution**:
  - Vertical (`9:16`): $768 \times 1376$ (~1.05 MP, divisible by 16/32 patch units).
  - Widescreen (`16:9`): $1376 \times 768$.
  - Square (`1:1`): $1024 \times 1024$.
- **Latency**: ~10–14 seconds per image.
- **Recommended Concurrency**: 3–4 parallel requests per batch.
- **Error Codes**:
  - `429 / RESOURCE_EXHAUSTED`: Rate limit or session concurrency reached. Triggers automatic transfer of pending scenes to the Codex pool.

## 2. OpenAI Codex (`codex` / GPT-Image 2.5)

- **Engine**: GPT-Image 2.5 Flare (speed-optimized) and Sunburst.
- **Native Resolution**:
  - Vertical (`9:16`): $1024 \times 1792$ (~1.83 MP).
  - Widescreen (`16:9`): $1792 \times 1024$.
  - Square (`1:1`): $1024 \times 1024$.
- **Latency**: ~12–18 seconds per image.
- **Recommended Concurrency**: 1–2 parallel requests per batch.
- **Error Codes**:
  - `429 / rate_limit_exceeded`: Rolling window or requests-per-minute ceiling hit. Triggers automatic transfer of pending scenes to the AGY pool.

## 3. High-Speed Parallel Dispatching

For a storyboard with $N$ scenes:
- Scenes are partitioned between pools: AGY handles batch $A$ (e.g. even indices) while Codex handles batch $B$ (odd indices).
- If either pool completes early, it pulls remaining work from the shared queue.
- If a vendor returns an unrecoverable rate limit, its queue is immediately drained into the healthy vendor.
- Output files are checked for valid image headers and written with unique paths matching the storyboard IDs.
