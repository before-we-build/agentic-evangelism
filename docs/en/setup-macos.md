# Set up on macOS

[Українська](../uk/setup-macos.md) · [Русский](../ru/setup-macos.md) · English

Set up the required tools once on your Mac.

## 1. Install Homebrew, Python, and FFmpeg

Open Terminal and install Python, FFmpeg, and Git using [Homebrew](https://brew.sh):

```sh
brew install python ffmpeg git
```

## 2. Clone the repository

Clone the repository to your local computer:

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
