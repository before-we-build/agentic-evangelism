# Set up on Windows

[Українська](../uk/setup-windows.md) · [Русский](../ru/setup-windows.md) · English

Set up the required tools once on your Windows PC.

## 1. Install Python and FFmpeg

Open PowerShell or Command Prompt (Terminal) and install Python and FFmpeg using `winget`:

```sh
winget install Python.Python.3.12
```

```sh
winget install Gyan.FFmpeg
```

Restart your terminal window after installation so that the newly added commands are available in your `PATH`.

## 2. Clone the repository

Download the repository with the skills:

```sh
git clone https://github.com/before-we-build/agentic-evangelism.git
cd agentic-evangelism
```

## 3. Verify environment readiness

Run the diagnostic doctor tool to check that Python, FFmpeg, and the required codecs are detected:

```sh
python skills/suno-tiktok-video/scripts/doctor.py
```

**You should see:** `Overall Ready: YES`.

Next step: [Make your first video](first-video.md).
