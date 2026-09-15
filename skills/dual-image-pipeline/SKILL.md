---
name: dual-image-pipeline
description: Coordinate consistent storyboard illustrations through verified image routes, using reviewed anchors, shared quota accounting, and an adaptive parallel queue. Does not provide image generation or guarantee two vendors.
---

# Parallel storyboard images

[English](SKILL.md) · [Русский](SKILL.ru.md) · [Українська](SKILL.uk.md)

This skill organizes independent scene illustrations. Check which image tool the host actually exposes. In Codex, follow the installed `imagegen` skill and use the built-in `image_gen` tool by default. Installing this folder does not install a generation service, authorize an external API, or guarantee access to two providers.

Define one visual bible and stable character description. Generate and inspect a style anchor, then a test scene from another angle. These are review dependencies: a saved file alone does not release dependent scenes. Give every asset a stable ID; preserve its exact prompt, references, route, attempts, review result and saved path by ID. After review, keep all eligible routes busy with ready assets. Save usable artwork alongside the storyboard and retain successful results when resuming.

## Adaptive concurrency plan

Build a route inventory before generation. Verify the actual image operation, access entitlement and existing task authorization. Distinguish a consumer subscription, a separately billed API and a local generator. A binary, login or plan name alone does not establish image access or a concurrent-request limit. Use non-mutating status checks where available; record missing information explicitly. A live smoke test spends resources and must fit the existing authorization. Read [provider checks and executable workflow](references/providers.md) when preparing profiles or running the scheduler.

For each route record dated, expiring evidence of access, subscription type, image/reference capability and applicable limits. Keep simultaneous requests, requests per time window, remaining quota and money as separate constraints. Routes drawing from the same account or project allowance share one quota group and one scheduler state, including across processes. Unknown quota is not unlimited; unknown cost is not zero. Do not convert a usage percentage or a plan name into an invented image count.

Use the documented or host-authorized parallel ceiling. If capacity is unknown, start with one request and increase gradually after successful work only up to an explicitly allowed probe ceiling. A successful request shows that level worked once; it does not establish the vendor's maximum. Fill each newly free slot immediately when dependencies, quotas, budget and cooldown allow. A slow AGY request must not hold up ready work on an available Codex route. Prefer routes that preserve required references and character consistency; spare slots do not justify dropping those requirements.

On temporary throttling, honor the provider's retry delay, lower concurrency and use bounded retries with backoff. Exhausted quota, lost entitlement and permanent errors require a different disposition from transient errors. An interrupted or timed-out request may already have generated an image: reconcile its outcome before resubmission. Do not activate an unverified route or spend on a new fallback to fill idle capacity. Keep successful images and resume only unfinished eligible IDs.

## Execute and review

`scripts/generate.py` provides the local scheduler and an optional CLI-adapter runner. Inspect a profile with `--profiles /private/routes.json --plan`; inspect installed command candidates with `--discover`. These checks do not generate images. `--probe-codex` reads sanitized account and usage information where supported; it does not verify an image route or derive image counts from usage percentages.

For host tools, use the scheduler's `--action next` / `--action record` workflow described in the reference. Reserve work before calling `image_gen`, record each outcome immediately, then refill available capacity. In code mode, maintain a bounded set of active calls with `Promise.race` or a worker pool; await every started call before the execution scope ends. `Promise.allSettled` may collect the final outcomes, but must not impose a whole-wave barrier before free slots receive more work. Call `tools.image_gen__imagegen` once per leased asset and pass the actual required references. The Python helper cannot invoke the host tool itself.

For a verified external CLI adapter, `--action run --allow-external-cli` runs the configured command with structured input and output. The profile must also record entitlement, authorization and current evidence; a command-line flag does not grant them. There is no automatic AGY, Codex or free-service image endpoint. `--dry-run` is an offline scheduler test that creates tiny placeholders, not usable artwork.

Inspect every image. Release reviewed dependencies only after visual continuity and the song's visual policy pass review; preserve originals and use fresh files for revisions. Record actual providers and concurrency changes in generation metadata. Concurrent submission measures local scheduling, not simultaneous execution inside a vendor. Report completed/reviewed assets, retries, waiting reasons and unknown limits without claiming globally optimal speed.

Follow the song's visual policy, defaulting to `evangelical_baptist`: Scripture, prayer, fellowship, service and creation as the lyrics support. Exclude halos, devotional icons, iconostases, onion domes and unrequested vestments. Respect explicit choices such as `interdenominational_unity`. Save the final images with the storyboard, not only in the generator's default directory.
