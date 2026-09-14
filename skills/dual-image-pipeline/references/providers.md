# Image provider checks

[English](providers.md) · [Русский](providers.ru.md) · [Українська](providers.uk.md)

The built-in Codex `image_gen` tool is the default when present. It is separate from `scripts/generate.py`. Check its availability through the host's actual tools before planning a batch.

On the tested Android/PRoot host, `agy --version` works but `agy generate-image --help` shows only the general AGY help; that does not establish an image subcommand. The legacy script's default macOS Codex executable path is absent, and `codex exec -o` writes the agent's last message rather than a PNG. A bare CLI binary or login is not proof of image-generation capability.

Pollinations is an external service. Do not assume that an old endpoint, model name, quota, or price still applies. Verify current terms from the provider before any authorized live CLI request. `--dry-run` creates tiny placeholder images for testing only. No provider is automatically substituted in the default built-in workflow.
