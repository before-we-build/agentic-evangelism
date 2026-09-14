---
name: suno-tiktok-video
description: Prepare a full-song vertical MP4 from a downloaded Suno or user-selected local audio file and a sequence of images based on lyrical subideas, including embedded-lyrics extraction and Android Downloads media visibility. Use for requests to turn a downloaded song into a TikTok-ready video; does not publish it.
---

# Downloaded song → vertical video

[English](SKILL.md) · [Русский](SKILL.ru.md) · [Українська](SKILL.uk.md)

`SKILL.md` is the installed entrypoint; the other language files are translations of the same skill. Copying this folder supplies instructions and Python helpers, not image-generation access. You need Python 3, FFmpeg/ffprobe, and either a host with an actual built-in image tool or images supplied by the user.

Deliver an actual MP4 for the entire chosen song. Default to a **sequence of still images illustrating the song's subideas**, 1080 × 1920 (9:16), H.264/yuv420p video, AAC audio, and MP4 faststart. Use a single still only when explicitly requested. This is a slideshow, not generated animation. Word timing, ASR, karaoke, subtitles, motion effects and excerpts are optional; do not enable them by default. Preserve the full audio. Do not reuse another song's religious imagery unless supported by the selected lyrics.

## Select the song

Apply these self-contained selection rules. If the user explicitly supplies a local workflow, read it as an optional override consistent with their request; no private configuration file is required:

- Default input is discovered via `platform_utils.py`:
  - **Android:** `~/storage/downloads` → `/storage/emulated/0/Download` in Termux (inside PRoot, use the shared path if accessible).
  - **Windows:** `%USERPROFILE%\Downloads` or resolved via Win32 Known Folder `FOLDERID_Downloads`.
  - **macOS:** `~/Downloads`.
  - **Linux:** `xdg-user-dir DOWNLOAD` or `~/Downloads`.
  - Else use the user's Downloads directory or an explicit path.
- An explicit song selection takes precedence over recency. For “latest”, sort by mtime; do not guess from names alone.
- List audio paths, sizes and timezone-aware mtimes, excluding hidden, empty, temporary, or still-changing files. Recheck file size and mtime after a short interval (`platform_utils.check_file_stability`).
- Show the selected full path, filename, byte size, and mtime before any upload. When multiple candidates plausibly fit, show them and ask once; prepare unrelated image work while waiting.
- Search other formats of the chosen song. Prefer WAV > FLAC > MP3 > M4A only for verified versions of the same recording. Similar titles and `(1)` do not establish identity.
- Confirm audio with ffprobe. File names and mtimes do not prove Suno origin, authorship, or rights. Retain user-provided provenance; do not invent it.

## Extract lyrics and plan the visual story

Create the output directory first (`mkdir -p /absolute/workspace`). Run `python3 scripts/extract_lyrics.py --audio '/absolute/song.mp3' --output '/absolute/workspace/lyrics.json'` (scripts are relative to this skill). It records duration and all embedded lyric candidates, keeping raw text plus a cleaned version. Read the actual candidates; language suffixes on tags do not establish the language of their contents. If candidates disagree, resolve them before using one. If no lyrics exist, use user-supplied text or a clearly associated lyrics sidecar; ask for the text when none is available. Do not silently install speech recognition or invent a song narrative from its filename.

Read [references/storyboard.md](references/storyboard.md) to determine the song's visual policy (`visual_policy`, defaulting to `evangelical_baptist` or applying user overrides such as `interdenominational_unity`), classify song narrative mode (narrative with protagonist, worship/contemplative, mixed), establish art direction (`visual_bible`) and character sheet (`characters`), identify subideas, plan approximate scene durations, and write `storyboard.json`. Keep repeated sections in performance order and distinguish lyric content from your visual interpretation. Embedded lyrics can differ from what was actually sung. In this default workflow, scene times are an editorial estimate, **not verified word, line, or chorus timestamps**. Explain this once to the user. For exact singing alignment, optionally run `python3 scripts/align_lyrics.py --audio '/absolute/song.mp3' --storyboard '/absolute/workspace/storyboard.json'` using a zero-cost Groq API key (`GROQ_API_KEY`) to snap scene transitions to neural Whisper Large-v3 timestamps.

## Prepare images

If the host exposes a built-in image generation tool, use it with the available `dual-image-pipeline` skill. That tool is a separate host capability; installing this skill does not enable it. For high-speed storyboard generation across scenes, `dual-image-pipeline` runs Antigravity and Codex concurrently with automatic failover. If unavailable or persistently failing, explain the limitation and obtain explicit consent before a separate API/CLI workflow, installation, or potentially paid fallback. User-supplied images are another option. Do not request API secrets in chat.

Create a distinct image per main subidea; alternate related views for long passages. Assemble prompts using the modular formula:
`[Scene Subject & Action] + [Character Anchor] + [Visual Bible: medium, palette, surface] + [Setting, Wardrobe & Physical Lighting] + [Shot Scale 9:16] + [Safe Zone: x=0.10…0.78, y=0.12…0.72] + [Applicable Constraints compiled for target tool]`.
For narrative songs, inject the character's exact anchor (silhouette, hairstyle, core wardrobe, and vivid contrast color accent) verbatim across all their scenes. Do not place more than two close-up face shots in a row; alternate wide establishing shots, medium angles, details, and rear views to ensure cinematic transitions. Reuse the signature motif for repeated choruses. Every scene must point to a saved image, and every main subidea must have an image. Do not fall back silently to one image for the full song if generation is incomplete.

Apply constraints based on the active scene policy: use explicit positive physical descriptions (`plain plaster walls`, `ordinary sweater`) combined with targeted exclusions (`no halos, no devotional icons, no onion domes, no unrequested vestments`). For `interdenominational_unity` scenes, preserve deliberately requested traditional attire (e.g. simple cassock or clerical collar) while strictly excluding halos and icon veneration. Request portrait 9:16 art grounded in the selected lyrics, with important details clear of bottom/right overlays and no text unless requested. Inspect each image against the active visual policy. For supplied local images, view them first. Preserve the actual prompts and accessible artwork copies alongside the storyboard. Explain that pictures change through the song but are individually still. Follow the dual-image-pipeline skill's fallback requirements if generation fails.

### Anchor First pipeline and parallel generation

Before launching the full asset batch, use the **Anchor First with transfer test** approach:
1. Generate and inspect an **anchor concept shot** (Character Sheet / Style Anchor).
2. Generate **one test scene** from a different angle (e.g. medium shot or rear view) to confirm visual continuity.
3. When the tool supports image inputs (Image-to-Image / Subject Reference), feed the verified anchor into all dependent scene calls. In text-only mode, consistency is driven by identical style and character anchor blocks.

After verifying the anchors, launch independent tool calls concurrently, one per distinct asset. Submit a small set (such as six images) together when permitted; use bounded batches for larger sets. Assign each request a stable `id` from `assets` and retain its exact compiled prompt before launch. In code mode, await all calls with `Promise.allSettled` (or equivalent), inspect every outcome, and map saved paths by ID rather than completion order. Report individual completions as they arrive; keep base64 image payloads out of text logs. Preserve successful images and retry only failed requests. Build the video only after every required asset has been saved and inspected and storyboard paths are checked.

## Build and verify

Check tools first with `python3 scripts/doctor.py`. Reuse installed tools; installation follows host permissions. Run the bundled helper with appropriate paths and a fresh output filename:

```sh
python3 scripts/build_video.py --audio '/absolute/song.mp3' --storyboard '/absolute/storyboard.json' --output '/absolute/output/TikTok_song_02.mp4'
```

For an explicitly requested single-image video, replace `--storyboard` with `--image '/absolute/artwork.png'`. Never pass both.

The helper preserves complete images with padding if needed, rounds scene boundaries to video frames, rejects incomplete timeline coverage, refuses overwrite, checks stable audio, and encodes the full song. It automatically detects popular AI music generators (Suno, Udio, Mubert, AIVA, Boomy, Soundraw, Meta MusicGen, YuE), manages license requirements (`--license free` by default; pass `--license commercial` or `--attribution none` to omit), renders a subtle 3.5-second intro attribution badge in the TikTok safe zone, writes clean container metadata, and prints recommended post captions with platform AI disclosure reminders. It checks codecs, dimensions and durations, decodes the finished file for errors, and only then copies the verified MP4 to its destination. Progress, temporary files and verification JSON are printed. Scene lengths must be positive and sum to audio duration within 0.15 seconds; use the probed duration, not a rounded display value.

Before accepting output, inspect representative frames including a scene change and confirm that the images follow the storyboard. Technical verification does not validate lyric timing. Do not crop/normalize audio, add fades or trim the song unless requested. Default transitions are smooth crossfades (`--transition fade`, 0.75 s); pass `--transition none` for simple cuts.

Use a clean filename without problematic characters for the target platform. On failure, inspect and correct the cause; an incomplete destination is not ready. Preserve it and retry with a fresh filename. Never delete inputs or previous outputs. Current TikTok account/upload limits require current official verification if relevant; advertising duration recommendations do not limit full-song posts.

## Platform delivery and media availability

Read the platform reference for your operating system:
- **Android:** [references/android.md](references/android.md) — scan through Termux `am` without ADB, then check TikTok's picker; an existing ADB connection can query MediaStore as a fallback.
- **Windows:** [references/windows.md](references/windows.md) — Downloads folder location, path quoting, and manual upload.
- **macOS:** [references/macos.md](references/macos.md) — Homebrew tools, QuickTime preview, and manual upload.
- **Linux:** [references/linux.md](references/linux.md) — Distribution packages, XDG Downloads, and manual upload.

## Finish and permissions

Report the actual saved path, filename, duration, size, number of images/scenes, and verification result. Link the storyboard (with prompts) and lyrics extraction output; describe the scene timing as approximate. Confirm local preparation separately from any upload outcome.

Creating the selected local video/artwork and updating local media indexing are preparation steps within the request, subject to host permissions. The skill never posts or publishes videos automatically. Uploading to TikTok, publishing, distributing, takedowns, and deletion need their own applicable authorization and are performed manually by the user. Never bypass disabled tools. Disclose AI use honestly when describing origin or filling a platform disclosure; do not invent copyright or authorship. Do not ask for tokens in chat.
