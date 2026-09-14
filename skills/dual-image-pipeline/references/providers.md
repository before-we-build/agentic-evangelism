# Image Generation Providers Reference

[English](providers.md) · [Русский](providers.ru.md) · [Українська](providers.uk.md)

This reference outlines technical specifications, native resolutions, concurrency rules, and failover behavior for the financially adaptive pipeline.

## 1. Antigravity (`agy` / Gemini Image)

- **Engine**: Gemini 3.1 Flash Image.
- **Native Resolution**:
  - Vertical (`9:16`): $768 \times 1376$ (~1.05 MP, divisible by 16/32 patch units).
  - Widescreen (`16:9`): $1376 \times 768$.
  - Square (`1:1`): $1024 \times 1024$.
- **Latency**: ~10–14 seconds per image.
- **Recommended Concurrency**: 3–4 parallel requests per batch.
- **Error Codes**:
  - `429 / RESOURCE_EXHAUSTED`: Rate limit or session concurrency reached. Triggers automatic transfer of pending scenes to Codex or the Free tier.

## 2. OpenAI Codex (`codex` / GPT-Image 2.5)

- **Engine**: GPT-Image 2.5 Flare (speed-optimized) and Sunburst.
- **Native Resolution**:
  - Vertical (`9:16`): $1024 \times 1792$ (~1.83 MP).
  - Widescreen (`16:9`): $1792 \times 1024$.
  - Square (`1:1`): $1024 \times 1024$.
- **Latency**: ~12–18 seconds per image.
- **Recommended Concurrency**: 1–2 parallel requests per batch.
- **Error Codes**:
  - `429 / rate_limit_exceeded`: Rolling window or requests-per-minute ceiling hit. Triggers automatic transfer of pending scenes to AGY or the Free tier.

## 3. Zero-Cost Community Tier (`free` / Pollinations FLUX)

- **Engine**: FLUX.1 via Pollinations.ai open endpoint.
- **Cost**: **$0** (zero subscriptions, zero API keys, no credit card required).
- **Native Resolution**:
  - Vertical (`9:16`): $768 \times 1376$.
  - Widescreen (`16:9`): $1376 \times 768$.
  - Square (`1:1`): $1024 \times 1024$.
- **Latency**: ~15–25 seconds per image.
- **Recommended Concurrency**: 1–2 parallel requests.
- **Purpose**: Ensures that church volunteers, youth, and low-income creators can produce full TikTok videos for ministry at zero cost.

## 4. Financially Adaptive Dispatching

For a storyboard with $N$ scenes:
- **Tier 1 (Dual)**: Scenes are partitioned between pools: AGY handles batch $A$ while Codex handles batch $B$.
- **Tier 2 (Single)**: All scenes route to the single configured tool (`agy` or `codex`).
- **Tier 3 (Zero-cost)**: Automatically activated if neither paid engine is present, or explicitly selected via `--free`.
- If a vendor encounters rate limits, its tasks fall over gracefully to the next tier.
- Output files are checked for valid image headers and written with unique paths matching the storyboard IDs.
