# Prepare and verify video on Windows

[English](windows.md) · [Русский](windows.ru.md) · [Українська](windows.uk.md)

On Windows, run commands in PowerShell, Command Prompt (CMD), Git Bash, or WSL.

## Downloads and file locations

The default song input is located in the user's Downloads folder:
- Resolved automatically via `platform_utils.py` using Windows Known Folder `FOLDERID_Downloads`.
- Fallback path: `%USERPROFILE%\Downloads` (for example, `C:\Users\<username>\Downloads`).
- If you use WSL, access Windows Downloads via `/mnt/c/Users/<username>/Downloads`.

## Paths and encoding

- When passing paths containing spaces or non-ASCII characters in PowerShell or CMD, surround them in quotes.
- In Python scripts, paths are handled via `pathlib.Path`, which works with both forward slashes and backslashes.
- FFmpeg and ffprobe output is read using explicit UTF-8 encoding.

## Running the pipeline

Verify tools before rendering:

```sh
python scripts/doctor.py
```

Build the video from a song and storyboard:

```sh
python scripts/build_video.py --audio "C:\Users\username\Downloads\song.mp3" --storyboard "C:\workspace\storyboard.json" --output "C:\Users\username\Downloads\TikTok_song.mp4"
```

## Availability and manual upload

The finished, verified MP4 file is saved to your selected output path (by default, your Downloads folder).

- The skill does not publish or upload videos automatically.
- Open your browser and navigate to [tiktok.com/upload](https://www.tiktok.com/upload).
- Click **Select video** and choose the generated MP4 from your Downloads folder.
- Add your description, review the preview, and publish manually.
