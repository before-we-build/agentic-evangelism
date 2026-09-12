# Maintenance and evidence

[Українська](../uk/maintenance.md) · [Русский](../ru/maintenance.md) · English

## What this repository contains

Human guides live in `docs/en`, `docs/ru` and `docs/uk`. The root README is a three-language entry page. Each guide has the same filename in all three folders. The skill lives in `skills/suno-tiktok-video`; `SKILL.md` is the executable English entrypoint, with Russian and Ukrainian reading copies. Those copies describe the same workflow, not three different skills. Reference documents also have translations. Python identifiers and shell commands stay unchanged across languages.

`scripts/install_skill.py` installs only the skill folder. It does not install third-party tools, change permissions, edit account configuration or publish anything. It refuses an existing destination. Pass `--destination PATH` only when you know the skill directory used by your Codex installation.

## What was actually checked

The maintainer requested a review of local Codex session history on 12 September 2026. Only relevant technical stages were used; raw sessions, account settings, tokens, device identifiers, personal songs and images are not included here.

| Evidence | Result and limit |
| --- | --- |
| Available sessions from 4 September 2026 onward | Linux and Codex were already installed. Their initial installation and first login were not recovered. |
| Phone environment observed in September | Android ARM64, Termux, Ubuntu 26.04 under PRoot; Node 22.22.1 and Codex 0.153.2. These are recorded versions, not universal minimum requirements. |
| 9 September: ADB | ADB installed inside Ubuntu; wireless pairing without a computer. Split screen kept the pairing dialog alive. |
| 12 September: storage | Android Downloads was readable; a Linux shortcut to it was created. The guide can use the full Android path instead. |
| 12 September: media tools | FFmpeg installed in Ubuntu; full-song video encoding, audio/video decoding checks and MediaStore query succeeded. |
| 12 September: visual workflow | Six generated still pictures, eleven scenes and a complete 122.2-second 1080×1920 MP4 were produced on the phone. H.264 video, AAC audio and Android indexing were checked. Image changes were approximate; lyric alignment was not verified. |
| Parallel generation | Independent built-in requests were launched together; no controlled speed comparison was run, and a service may queue requests internally. |
| Image access | The recorded session had a built-in image tool. Fresh installations and other accounts may not have it. |
| Sandbox | A local `bwrap` failure occurred. A general fix or unrestricted-mode requirement was not established. |

The initial installation route is reconstructed from documentation and the observed working environment. We have not repeated a full clean-phone install. Updating this table requires actual test evidence; a successful syntax check is not a successful Android installation.

## Sources for setup

Checked on 12 September 2026. Services and package versions can change; prefer the current official page when a step differs.

- [Termux installation](https://github.com/termux/termux-app#installation) and [F-Droid download](https://f-droid.org/en/packages/com.termux/).
- [PRoot-Distro](https://github.com/termux/proot-distro): installation, login and storage binding.
- [Codex CLI](https://developers.openai.com/codex/cli/) and [CLI reference](https://developers.openai.com/codex/cli/reference/).
- [Codex authentication](https://developers.openai.com/codex/auth/).
- [Local Codex skills](https://developers.openai.com/codex/skills/).
- [Android wireless ADB](https://developer.android.com/tools/adb#wireless-android11-command-line).

The video helpers were copied from the maintainer's working `suno-tiktok-video` skill. The public instructions remove dependencies on a personal LabelGrid workflow and helper path; the private workflow is not shipped. Parallel generation, complete-audio preservation, no-overwrite behavior, image inspection and final validation remain part of the skill. The separate built-in `imagegen` skill/service is not redistributed here.

## Change something without breaking another language

1. Describe the change and its user-visible effect.
2. Update the English, Russian and Ukrainian guide peers together, including commands and caveats. Do the same for skill and reference translations.
3. Run local checks from the repository root:

```sh
python3 scripts/check_docs.py
python3 -m unittest discover -s tests -v
```

4. For a media-helper change, also run a short generated-audio/scene smoke test with FFmpeg and inspect the result. Keep test media outside the tracked files.
5. Review `git diff` and `git status --short` before publishing. Commit only intended project files. Do not add your Codex home directory, session exports, account files or phone backups.

The automated documentation check verifies file peers and local file links; it cannot certify translation quality, theology or service availability. The tests check the installer and selected helper behavior without external accounts or image-generation charges.

## Contribute or keep your copy current

For suggestions, open a GitHub issue with the relevant guide step, language, phone/Android version if useful, and a short sanitized error. Never attach authentication files or a full private session. A small proposed correction is useful even if you cannot program.

To update an unchanged local checkout, leave Codex, enter the repository folder inside Ubuntu, and run:

```sh
git status --short
```

No output means there are no listed local edits. If it lists edits you want to keep, ask for help preserving them before continuing. When the checkout is unchanged, run:

```sh
git pull --ff-only
```

Updating the checkout does not overwrite an installed skill; compare and update that copy separately. Automatic posting, distribution accounts and bulk outreach are outside this starter workflow.
