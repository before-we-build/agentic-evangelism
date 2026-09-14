# Prepare and verify video on Linux

[English](linux.md) · [Русский](linux.ru.md) · [Українська](linux.uk.md)

On Linux (desktop, workstation, or server), commands are executed in Bash or Zsh.

## Downloads and file locations

The default song input is located in the user's Downloads directory:
- Determined via `xdg-user-dir DOWNLOAD` or standard `~/Downloads`.
- Resolved automatically by `platform_utils.py`.
- On headless servers without a Downloads folder, pass explicit `--audio` and `--output` paths.

## Tools and dependencies

Install Python 3 and FFmpeg using your distribution's package manager:

- **Ubuntu / Debian:**
  ```sh
  sudo apt update && sudo apt install -y python3 ffmpeg
  ```
- **Fedora:**
  ```sh
  sudo dnf install -y python3 ffmpeg
  ```
  *(Note: on Fedora, verify that the package provides full `libx264` and `aac` codecs, rather than restricted `ffmpeg-free`).*
- **Arch Linux:**
  ```sh
  sudo pacman -Syu python ffmpeg
  ```

Verify tools and codecs:

```sh
python3 scripts/doctor.py
```

## Running the pipeline

Build the video from a song and storyboard:

```sh
python3 scripts/build_video.py --audio "$HOME/Downloads/song.mp3" --storyboard "/absolute/workspace/storyboard.json" --output "$HOME/Downloads/TikTok_song.mp4"
```

## Availability and manual upload

The finished MP4 file is saved to your selected output directory:
- On desktop Linux: open your browser and navigate to [tiktok.com/upload](https://www.tiktok.com/upload) to upload manually.
- On a remote or headless server: copy the verified MP4 to your personal computer or phone using `scp`, SFTP, or your preferred transfer method.
- The skill does not publish automatically.
