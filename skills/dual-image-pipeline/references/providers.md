# Image provider checks

[English](providers.md) · [Русский](providers.ru.md) · [Українська](providers.uk.md)

## Establish the actual access route

The built-in Codex `image_gen` tool is the default when present. Check the active host's actual tools. The local scheduler accounts for work but the host invokes that tool. A command candidate, login and successful help output alone do not verify image generation.

On the previously tested Android/PRoot host, `agy generate-image --help` returned general help. That observation does not establish a working image subcommand or prove that every AGY version lacks image tools. Current Antigravity documentation describes a generative image tool and a headless agent interface with tool events; verify the installed version and actual artifact-producing operation before configuring an adapter. [Models](https://antigravity.google/docs/models), [headless interface](https://antigravity.google/docs/cli/headless/).

Antigravity quotas depend on the plan and workload, with time windows and optional credit overages. Its documented `/usage` (`/quota`) opens an interactive quota panel; it is not a documented universal JSON status endpoint. In an existing AGY terminal session, enter `/usage` and expect the quota panel. Use only a supported read-only adapter or user-confirmed observations; do not scrape credentials or invent `agy quota --json`. [Plans](https://antigravity.google/docs/plans), [quota panel](https://antigravity.google/docs/cli/commands/usage/).

Codex image generation uses the subscription's general usage allowance; API-key access uses API billing. In an existing Codex terminal session, `/status` shows remaining usage information. `python3 scripts/generate.py --probe-codex` uses supported read-only account/status operations when available and removes account identifiers; it does not authorize or verify image generation. A usage percentage cannot establish a remaining image count or a parallel ceiling. [Codex usage and image billing](https://learn.chatgpt.com/docs/pricing).

API limits can independently constrain requests, images, tokens and spending, and may be shared at model, project or organization level. Read the actual account/model limits and response metadata. Respect `Retry-After` as a minimum, distinguish temporary overload from exhausted quota, and bound retries. Adapters must disable hidden automatic retries or account for them explicitly. [OpenAI API limits](https://developers.openai.com/api/docs/guides/rate-limits).

These sources were checked on 2026-09-15; refresh them before relying on changeable product terms. No numeric vendor concurrency defaults are embedded here. Pollinations or another external service requires its own verified operation, current access/cost evidence and existing authorization; no fallback endpoint is selected automatically.

## Route profiles and evidence

Keep account observations, route profiles and scheduler state in a private workspace outside the repository. Use a non-identifying alias for `quota_group`; do not store tokens, email addresses or account configuration. Profile format is `{"schema_version":1,"routes":[...]}`. Each route uses:

| Field | Meaning |
| --- | --- |
| `id`, `kind` | Stable ID; `host_tool`, `cli` or `local`. |
| `quota_group` | Shared accounting scope. Routes spending the same allowance use the same group and state file. |
| `image_capability`, `entitlement`, `authorized` | Actual image support, `verified` entitlement and task authorization. Required true/verified values must reflect evidence, not a desired state. |
| `subscription` | `{kind: subscription/api/local, plan: ...}`; a plan label never sets capacity. |
| `evidence` | `source` is `host_tool`, `provider_status`, `user_confirmed` or `authorized_smoke_test`; `checked_at` and `expires_at` are Unix seconds. Expired evidence blocks new dispatch. |
| `supports_references` | True only for a verified reference-capable route. |
| `limits` | `max_parallel`, `initial_parallel`; optional `requests_per_minute`, `requests_per_day`, `remaining_requests`, `reset_at`. Counts must be real request counts. |
| `limits.quota_windows` | Optional native observations: `used_percent`, `window_minutes`, `resets_at`. Exhausted windows block until fresh evidence; never translate percentages into image counts. |
| `cost` | `per_request` is a verified monetary upper bound per attempt; paid routes also need `budget_remaining`. Use one `currency` within a quota group. Unknown price blocks dispatch. |
| `overage_disabled`, `zero_cost_verified` | A zero-price subscription route needs verified `overage_disabled:true`; a zero-price API route needs `zero_cost_verified:true`. Included usage can still consume quota. |
| `command`, `timeout_seconds` | CLI/local adapter argument array and timeout. The command must implement the structured contract below. |

Use the tightest applicable shared allowance when one quota group covers several constraints. The scheduler enforces configured request-count, concurrency and monetary limits; it cannot infer token/credit consumption from a plan or promise to account for unrelated traffic outside the shared state. Refresh observations when other sessions use the same account. Native quota percentages remain observations, not a complete accounting model for variable-cost requests.

If the provider does not disclose concurrency, default to one and record an explicitly authorized bounded probe ceiling before increasing `max_parallel`. `initial_parallel` starts conservatively; successful work allows gradual growth within the ceiling, throttling reduces it. Do not reuse a stale successful run as permanent proof. A reset timestamp alone does not justify refilling an unknown allowance.

`status_source:"codex_app_server"` opts a route into supported Codex status refresh. Add `--refresh-codex-status` to `next`/`run` to refresh on that invocation. This does not create an automatic polling service, verify image capability, enable paid overages or bypass expired evidence.

## Plan, reserve, execute, record

Run the following from the directory containing this skill. On Android use the same Termux/PRoot shell where Python and the selected generator work. Replace `/private/...` with your private accessible paths. Expected outputs are JSON plans, leases and status reports.

```sh
python3 scripts/generate.py --discover
python3 scripts/generate.py --profiles /private/routes.json --plan
python3 scripts/generate.py --storyboard /private/song/storyboard.json --profiles /private/routes.json --state /private/image-shared.sqlite --run-id song --action next
```

`--discover` reports PATH candidates only; `--plan` checks eligibility and unknowns without calls or reservations. `next` reserves eligible work before generation. Keep the same state file for every process using the same quota and the same run ID when resuming the same storyboard. Separate state files cannot coordinate with one another.

Assets support `depends_on`, `reference_asset_ids`, `review_required`, `reviewed`, `review_token`, `allowed_routes`, `requires_references` and `affinity_group`. Model the anchor → transfer test → dependent scenes explicitly with `depends_on`; mark anchor/test `review_required:true`. Use `reference_asset_ids` to pass generated anchors to dependent calls; it also establishes dependencies. After inspecting an image, set that asset's `reviewed:true` and `review_token` equal to the exact `token` returned by `record`, then resume. The token binds review to that artifact; an old boolean cannot approve a new image. Keep recurring identities on a compatible route with `affinity_group`; reference requirements remain mandatory. Preserve `characters[].avatar_image` and `assets[].character_ids` when supplied.

`limits.remaining_checked_at` and `cost.budget_checked_at` identify independent balance snapshots. Refreshing quota percentages must not renew an old monetary budget. `--action status` reports scheduler state without dispatch. `--dry-run` uses a separate state file with the `.dry-run` suffix. By default outputs stay beside the storyboard so its relative paths remain valid; a custom output directory requires checking the exported storyboard paths before video assembly.

For every returned lease, launch exactly one matching host-tool call with its prompt and required references. Save the image, inspect it, and write the structured result to a private file, for example `{"status":"success","output":"/private/song/images/scene01.png"}`. Then record it with the job ID and lease token returned by `next`:

```sh
python3 scripts/generate.py --storyboard /private/song/storyboard.json --profiles /private/routes.json --state /private/image-shared.sqlite --run-id song --action record --job-id scene01 --token LEASE_TOKEN --result /private/result.json
```

The lease token is local scheduler data, not an API credential. Record completions immediately and call `next` again while other images are still running. Do not await an entire wave before refilling free capacity. Always await all started host calls before ending the execution scope.

Result statuses are `success`, `review_required`, `rate_limited`, `transient_error`, `quota_exhausted`, `unauthorized`, `permanent_error` or `ambiguous`; retryable results may include `retry_after` in seconds. A timeout or lost response can mean remote work succeeded. Keep ambiguous work for reconciliation; do not retry it blindly or repeat completed assets. Resume must preserve originals, and revisions need new paths/IDs rather than overwriting a successful output.

## Optional CLI adapters

`--action run --allow-external-cli` dispatches only eligible configured CLI/local adapters. Each command receives JSON on stdin with the prompt, `reference_images`, output path and job information, and returns JSON on stdout using the result contract above. General agent CLI output is not itself an image: verify the actual artifact. Adapters must honor reference inputs, respect host permissions, preserve output files and report provider failures accurately. Never implement a text-only fallback for an avatar-dependent scene.

Use `--dry-run` for offline scheduling checks only; its tiny placeholders are not deliverable artwork. Existing authorization may cover a route, but neither configuration flags nor copying this skill grant new service access, spending, publication or deletion rights.
