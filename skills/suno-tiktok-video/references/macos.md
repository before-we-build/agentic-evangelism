# Prepare and verify video on macOS

[English](macos.md) · [Русский](macos.ru.md) · [Українська](macos.uk.md)

On macOS, commands are executed in Terminal (using zsh or bash).

## Downloads and file locations

The default song input is located in the user's Downloads directory:
- Path: `~/Downloads` (for example, `/Users/username/Downloads`).
- Resolved automatically by `platform_utils.py`.

## Tools and dependencies

Install Python 3 and FFmpeg using [Homebrew](https://brew.sh):

```sh
brew install python ffmpeg
```

Verify that tools and codecs are operational:

```sh
python3 scripts/doctor.py
```

## Running the pipeline

Build the video from a song and storyboard:

```sh
python3 scripts/build_video.py --audio "$HOME/Downloads/song.mp3" --storyboard "/absolute/workspace/storyboard.json" --output "$HOME/Downloads/TikTok_song.mp4"
```

## Availability and manual upload

The finished MP4 file is saved to your Downloads folder:
- Preview the video in QuickTime Player or Finder Spacebar preview.
- The skill does not publish automatically.
- To publish, open [tiktok.com/upload](https://www.tiktok.com/upload) in Safari or Chrome, choose your verified MP4 from Downloads, and complete your upload manually.
