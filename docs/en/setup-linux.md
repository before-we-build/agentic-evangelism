# Set up on Linux

[Українська](../uk/setup-linux.md) · [Русский](../ru/setup-linux.md) · English

Set up the required tools once on your Linux system (Ubuntu, Debian, or other distributions).

## 1. Install Python, FFmpeg, and Git

On Ubuntu or Debian, run:

```sh
sudo apt update && sudo apt install -y python3 ffmpeg git
```

*(On Fedora, use `sudo dnf install -y python3 ffmpeg git`; on Arch Linux, use `sudo pacman -Syu python ffmpeg git`)*.

## 2. Clone the repository

Clone the repository to your local computer or server:

```sh
git clone https://github.com/before-we-build/agentic-evangelism.git
cd agentic-evangelism
```

## 3. Verify environment readiness

Run the diagnostic doctor tool:

```sh
python3 skills/suno-tiktok-video/scripts/doctor.py
```

**You should see:** `Overall Ready: YES`.

Next step: [Make your first video](first-video.md).
