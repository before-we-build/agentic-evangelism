---
name: suno-tiktok-video
description: Prepare a full-song vertical MP4 from a downloaded Suno or user-selected local audio file and a sequence of images based on lyrical subideas, including embedded-lyrics extraction, reviewed word-timed karaoke by default, and Android Downloads media visibility. Use for requests to turn a downloaded song into a TikTok-ready video; does not publish it.
---

# Downloaded song → vertical video

[English](SKILL.md) · [Русский](SKILL.ru.md) · [Українська](SKILL.uk.md)

`SKILL.md` is the installed entrypoint; the other language files are translations of the same skill. Copying this folder supplies instructions and Python helpers, not image-generation access. You need Python 3, FFmpeg/ffprobe, and either a host with an actual built-in image tool or images supplied by the user.

Deliver an actual MP4 for the entire chosen song. Default to a **sequence of still images illustrating the song's subideas**, 1080 × 1920 (9:16), H.264/yuv420p video, AAC audio, and MP4 faststart. Use a single still only when explicitly requested. This is a slideshow, not generated animation. For songs with lyrics, reviewed word-timed karaoke is the default final deliverable, including with a requested single still. Omit it only when the user explicitly asks for no on-screen lyrics or the audio is instrumental. Motion effects and excerpts remain optional. Preserve the full audio. Do not reuse another song's religious imagery unless supported by the selected lyrics.

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

On this Android phone, after selecting and showing the audio path, size and mtime, start a fresh workspace from the installed skill directory with `python3 scripts/prepare_video.py --audio '/storage/emulated/0/Download/song.mp3' --slug song`. It rechecks file stability, extracts embedded lyrics without a network request, and prints the new workspace and `lyrics.json` paths. Use that workspace for reviewed timing, storyboard and artwork. Select the recording first; this command never guesses that similarly named files are the same recording.

Create the output directory first (`mkdir -p /absolute/workspace`). Run `python3 scripts/extract_lyrics.py --audio '/absolute/song.mp3' --output '/absolute/workspace/lyrics.json'` (scripts are relative to this skill). It records duration and all embedded lyric candidates, keeping raw text plus a cleaned version. Read the actual candidates; language suffixes on tags do not establish the language of their contents. If candidates disagree, resolve them before using one. If no lyrics exist, use user-supplied text or a clearly associated lyrics sidecar; ask for the text when none is available unless the recording is confirmed instrumental. Do not silently install speech recognition or invent a song narrative from its filename.

Read [references/storyboard.md](references/storyboard.md) to determine the song's visual policy (`visual_policy`, defaulting to `evangelical_baptist` or applying user overrides such as `interdenominational_unity`), classify song narrative mode (narrative with protagonist, worship/contemplative, mixed), establish art direction (`visual_bible`) and character sheet (`characters`), identify subideas, plan approximate scene durations, and write `storyboard.json`. Keep repeated sections in performance order and distinguish lyric content from your visual interpretation. Embedded lyrics can differ from what was actually sung. Scene times remain an editorial estimate, **not verified word, line, or chorus timestamps**; karaoke needs separate word timing. Explain this once to the user. Reuse an existing reviewed timing file for the same recording when available. Otherwise, `scripts/align_lyrics.py` uses the official Groq Python SDK to request word and segment timestamps and saves the unreviewed transcript separately. It only estimates scene cuts from segment starts; it does not match lyric lines to audio or render karaoke/subtitles. Check the transcript against the selected lyrics before using any word times. Before reporting the SDK unavailable, check project-provided virtual environments and secure key helpers as well as system Python. Audio transcription uploads the song to Groq and may incur charges; obtain any required cost authorization first. Supply the key securely through `GROQ_API_KEY`, never in chat or a command argument. A successful models-list request alone does not verify audio transcription.

### Default reviewed karaoke

Review the Groq transcript against the embedded or user-supplied lyrics, unless an existing timing file has already been reviewed. Remove hallucinated words and do not display unverified text. Create a separate timing JSON with `lines`, each containing `start`, `end`, and `words` with `text`, `start`, and `end`; times are seconds. Mark any interpolated word times as approximate in the timing file. After building the no-text base MP4 as an intermediate, run `python3 scripts/render_karaoke.py --video '/absolute/base.mp4' --timing '/absolute/reviewed-timing.json' --output '/absolute/karaoke.mp4'`. The helper burns progressive word highlighting into a new MP4, copies its audio stream, verifies dimensions and duration, and refuses to overwrite the original. Use `--ass-output '/absolute/karaoke.ass' --ass-only` to inspect the subtitle track before encoding. Review representative frames and timing by listening; ASR timestamps alone do not establish accurate karaoke. Deliver the karaoke MP4 as the default final video. If missing lyrics, timing, or required authorization prevents it, keep the base MP4 as a draft and explain the blocker instead of presenting a no-text video as the completed request.

## Prepare images

If the host exposes a built-in image tool, read the installed `imagegen` and `dual-image-pipeline` skills. Use `image_gen` with the dual skill's reviewed anchors and adaptive parallel queue. Its `scripts/generate.py` reserves and records work for host tools and can run explicitly configured CLI adapters; it cannot itself call the built-in tool. Verify actual routes, subscription/API access, shared quotas and spending authorization. Apply existing authorization; seek additional consent only for a new service, installation or cost outside it. Do not infer two active providers from an installed skill or CLI. If no eligible route is available, use supplied images or explain what access is missing. Do not request secrets in chat.

Create a distinct image per main subidea; alternate related views for long passages. Assemble prompts using the modular formula:
`[Scene Subject & Action] + [Character Anchor] + [Visual Bible: medium, palette, surface] + [Setting, Wardrobe & Physical Lighting] + [Shot Scale 9:16] + [Safe Zone: x=0.10…0.78, y=0.12…0.72] + [Applicable Constraints compiled for target tool]`.
For narrative songs, inject the character's exact anchor (silhouette, hairstyle, core wardrobe, and vivid contrast color accent) verbatim across all their scenes. Do not place more than two close-up face shots in a row; alternate wide establishing shots, medium angles, details, and rear views to ensure cinematic transitions. Reuse the signature motif for repeated choruses. Every scene must point to a saved image, and every main subidea must have an image. Do not fall back silently to one image for the full song if generation is incomplete.

Apply constraints based on the active scene policy: use explicit positive physical descriptions (`plain plaster walls`, `ordinary sweater`) combined with targeted exclusions (`no halos, no devotional icons, no onion domes, no unrequested vestments`). For `interdenominational_unity` scenes, preserve deliberately requested traditional attire (e.g. simple cassock or clerical collar) while strictly excluding halos and icon veneration. Request portrait 9:16 art grounded in the selected lyrics, with important details clear of bottom/right overlays and no text unless requested. Inspect each image against the active visual policy. For supplied local images, view them first. Preserve the actual prompts and accessible artwork copies alongside the storyboard. Explain that pictures change through the song but are individually still. Follow the dual-image-pipeline skill's fallback requirements if generation fails.

If the user supplies an avatar for a recurring person, set optional `characters[].avatar_image` in the storyboard and link that person through each relevant `assets[].character_ids`. See [the avatar workflow](references/storyboard.md#optional-supplied-avatar). Resolve and validate references with `python3 scripts/avatar_refs.py --storyboard '/absolute/workspace/storyboard.json'`; inspect the avatar, pass the listed paths as `referenced_image_paths` to `image_gen` for each linked asset, and review the first different-angle test. Without an avatar, keep the current text-anchor flow. The scheduler permits avatar-linked assets only on routes with verified `supports_references:true`; a CLI adapter must actually pass those references to its image tool.

### Anchor First pipeline and parallel generation

Before launching the full asset batch, use the **Anchor First with transfer test** approach:
1. Generate and inspect an **anchor concept shot** (Character Sheet / Style Anchor).
2. Generate **one test scene** from a different angle (e.g. medium shot or rear view) to confirm visual continuity.
3. When the tool supports image inputs (Image-to-Image / Subject Reference), feed the verified anchor into all dependent scene calls. In text-only mode, consistency is driven by identical style and character anchor blocks.

After reviewing the anchors, use the `dual-image-pipeline` scheduler: keep expiring evidence of actual image access, distinguish subscription and API billing, and share accounting for routes using the same allowance. Encode anchor/test dependencies and review gates; dispatch one call per ready asset within the current parallel, request-rate, quota and budget limits. Reserve work before each host call, record every result as it arrives and immediately refill eligible free slots while other calls continue. Use all verified compatible routes; unknown concurrency starts at one and may grow only to an explicitly allowed ceiling. Assign a stable `assets[].id` and retain exact prompts and references; map saved paths by ID. Await every started call before ending the execution scope, without imposing whole-wave barriers. Keep base64 out of logs. Preserve successes, respect retry delays and reduced concurrency after throttling, and reconcile ambiguous timeouts before resubmitting. Report missing quota information honestly. Build the video only after every required asset has been saved and inspected and storyboard paths are checked.

### Dynamic Video Generation & Google Flow Probing

Before finalizing storyboard visuals into a purely static slideshow, probe the environment with `python3 scripts/flow_probe.py`:
- **Zero-friction detection**: Checks `http://127.0.0.1:18999/api/health` (< 800ms) without prompting the user.
- **Intent recognition**: If the user has Google Flow (`labs.google/fx/tools/flow`) open in Chrome or the local server is connected with active extension polling, the skill detects clear intent for dynamic video scenes rather than static images.
- **Hybrid Image-to-Video (I2V)**: To preserve character continuity and strict adherence to the visual policy (`evangelical_baptist`: no unrequested halos or devotional icons), the verified static anchor frame is fed into Google Flow as the start frame (`imageToVideo`) with restrained cinematic camera prompts.
- **Resilient retries**: Transient failures (unusual activity, temporary queue congestion) trigger automatic exponential backoff retries (up to 3–5 attempts).
- **Graceful degradation**: If the probe reveals an offline server, suspended session, or persistent timeout, the pipeline seamlessly builds a static slideshow without blocking the user with unnecessary questions. Storyboard scenes support mixed assets (`video` or `image`), normalized by `build_video.py` to 1080×1920 25fps with smooth transitions.

## Build and verify

On this Android phone, after reviewing the storyboard, artwork and word timing, run `python3 scripts/finish_video.py --audio '/storage/emulated/0/Download/song.mp3' --storyboard '/tmp/song-video/storyboard.json' --timing '/tmp/song-video/reviewed-timing.json' --workspace '/tmp/song-video' --slug song` from the installed skill directory. Keep the storyboard, timing and copied artwork together in the workspace. This chooses fresh filenames, saves a base draft in the workspace and a karaoke MP4 in Downloads, fully decodes the final MP4, and requests Android media scanning when Termux `am` is available. It never uploads, publishes, deletes, transcribes or spends money. The agent still checks lyrics against the recording and inspects representative frames. Use the individual helpers below on other platforms, for instrumental/no-text videos, or for custom build options.

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

Report the final karaoke MP4 path, filename, duration, size, number of images/scenes, and verification result. Link the storyboard (with prompts), lyrics extraction, and reviewed timing file; describe estimated scene timing and any interpolated word timing as approximate. For an explicit no-karaoke request or instrumental song, report that exception. Confirm local preparation separately from any upload outcome.

Creating the selected local video/artwork and updating local media indexing are preparation steps within the request, subject to host permissions. The skill never posts or publishes videos automatically. Uploading to TikTok, publishing, distributing, takedowns, and deletion need their own applicable authorization and are performed manually by the user. Never bypass disabled tools. Disclose AI use honestly when describing origin or filling a platform disclosure; do not invent copyright or authorship. Do not ask for tokens in chat.
