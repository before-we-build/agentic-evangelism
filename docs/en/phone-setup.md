# Set up an Android phone

[Українська](../uk/phone-setup.md) · [Русский](../ru/phone-setup.md) · English

You can do this on one phone. Keep this page in the browser and switch to Termux when asked. A split screen is convenient if your phone supports it.

The guide combines a working phone setup with installation steps reconstructed from current documentation. The saved sessions began after the original installation, so a clean installation from this guide has **not** been tested from beginning to end. See [what was verified](maintenance.md). Android/PRoot is a community route, not a promise of official Codex support.

## Before you start

Use Wi-Fi if possible; installing Linux and its tools downloads substantial data. Keep several gigabytes free and allow the phone time to finish. Do not delete an existing Termux installation to start over: its private files may contain your work and sign-in data.

Read each explanation, copy only the contents of its command box, paste into the named screen, then press Enter. Wait until the command finishes and the input prompt returns. If a command reports an error, stop there and use [troubleshooting](troubleshooting.md); do not paste the remaining steps over the error. Never type the decorative `$` or `#` from somebody else's terminal screenshot.

## 1. Install and open Termux

On the phone, open the [Termux F-Droid page](https://f-droid.org/en/packages/com.termux/), download its APK and open the download. Android may ask you to allow installation from that browser. Allow it only for this intended install. Open Termux and let its first setup finish. Use the same download source for Termux add-ons. [Termux installation instructions](https://github.com/termux/termux-app#installation).

**In Termux**, update its tool list:

```sh
pkg update
pkg upgrade
```

Read any confirmation before accepting it. A question such as `Do you want to continue? [Y/n]` is waiting for you: type `y` and press Enter to continue the installation you intended. For an unfamiliar configuration or replacement question, ask for help before choosing. Scrolling package messages are normal. Success: the command finishes and you can type again.

## 2. Give Termux access to Downloads

**In Termux**, run:

```sh
termux-setup-storage
```

Approve the Android file-access prompt, then check:

```sh
ls ~/storage/downloads
```

Success: you see filenames from the phone's Downloads folder, or an empty list if that folder is empty. A `Permission denied` message is not success. Do this in Termux, not inside Ubuntu. If an existing installation already lists the files, skip repeating storage setup.

## 3. Put Ubuntu inside Termux

**In Termux**, install the environment manager:

```sh
pkg install proot-distro
```

Check for an existing environment:

```sh
proot-distro list
```

If Ubuntu is already installed, use it; do not reset it. Otherwise install it:

```sh
proot-distro install ubuntu
```

This may take a while. Then enter Ubuntu and explicitly expose the phone's shared storage:

```sh
proot-distro login ubuntu --bind /storage/emulated/0:/storage/emulated/0
```

Success: the prompt changes. The word `root` here is the Linux environment's user; this setup does not require rooting Android. Ubuntu commands below belong in this new screen. Check:

```sh
cat /etc/os-release
ls /storage/emulated/0/Download
```

You should see Ubuntu information and your downloaded filenames. [PRoot-Distro instructions](https://github.com/termux/proot-distro#quick-start). The installed distribution version may differ from the recorded Ubuntu 26.04; do not replace an existing working environment merely to match it.

## 4. Install the working tools

**Inside Ubuntu**, run:

```sh
apt update
apt install nodejs npm git python3 ffmpeg ca-certificates
```

These provide the assistant launcher, project download, helper scripts and video encoder. Check each:

```sh
node --version
npm --version
python3 --version
ffmpeg -version
ffprobe -version
```

Success: version information appears. The recorded setup used Node 22.22.1. If the Codex install below reports an unsupported Node version, keep the error and ask for help updating Node in Ubuntu; updating Node in Termux would change a different environment.

## 5. Install Codex and sign in

**Inside Ubuntu**, install the official npm package used by this workflow:

```sh
npm install -g @openai/codex
codex --version
```

Success: Codex prints a version. The recorded version was 0.153.2; the command may install a newer release. [Codex CLI](https://developers.openai.com/codex/cli/).

Start sign-in:

```sh
codex login --device-auth
```

Open the displayed link in the browser **on this same phone**, sign in and enter the temporary code. You may need to enable device-code login in your account's security settings. Return to Termux and check:

```sh
codex login status
```

Device login depends on account settings. If unavailable, try `codex login` and open its displayed link on the phone. Never send someone the code or your `auth.json`. ChatGPT sign-in and API billing are different access methods; this route uses ChatGPT sign-in. [Official login guidance](https://developers.openai.com/codex/auth/).

## 6. Download this project and install its skill

**Inside Ubuntu**, put the project in private Linux storage. Keep finished videos in Android Downloads instead.

```sh
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/before-we-build/agentic-evangelism.git
cd agentic-evangelism
```

If `agentic-evangelism` already exists, enter it with `cd ~/projects/agentic-evangelism`; do not delete it or clone over it.

The next command copies the skill to Codex's user skill directory and refuses to overwrite an existing copy:

```sh
python3 scripts/install_skill.py
```

Success: an installed path ending in `suno-tiktok-video` appears. This copies workflow instructions, not an image-generation service. Modern Codex reads user skills from `~/.agents/skills`; some older installations use `~/.codex/skills`. If the skill is absent, see [troubleshooting](troubleshooting.md). [Local skill discovery](https://developers.openai.com/codex/skills/).

## 7. Start the assistant

**Inside Ubuntu**, from the project folder:

```sh
codex
```

Read the trust and permission prompts; approve this project only if you intend to let it work with these files. Inside **Codex**, type `/skills` and look for `suno-tiktok-video`. Then send this ordinary-language message:

> Check whether the suno-tiktok-video skill, ffmpeg, ffprobe and access to Android Downloads are available. Also check whether this session can actually generate and save images. Do not generate anything or spend money yet. Explain any missing part in simple words.

If images cannot be generated, ask for scene prompts, create the pictures in an image tool you already use, save them to Downloads, then explicitly ask Codex to use those files. See [first video](first-video.md). A fresh Codex installation may have different tools from the recorded session.

You are ready when the assistant can read Downloads, run the encoder and has either an available image tool or your chosen local pictures. ADB and LabelGrid are optional and are not needed to reach this point.

## Next time you open the phone

**Which screen am I in?** If you see a conversation with the assistant, you are in Codex; press Ctrl+C as prompted to return to the shell. At the shell, run `cat /etc/os-release`. If it says Ubuntu, you are already inside Ubuntu. If the file is absent, try `command -v pkg`: a path containing `com.termux` means you are in Termux. If neither matches, ask for help rather than entering another Linux environment blindly.

Open Termux. If you are already inside Ubuntu, skip the first command. Otherwise:

```sh
proot-distro login ubuntu --bind /storage/emulated/0:/storage/emulated/0
```

**Inside Ubuntu**:

```sh
cd ~/projects/agentic-evangelism
codex
```

`codex resume` lets you select an earlier conversation. To leave Codex, press Ctrl+C as prompted; Termux has a Ctrl key in its extra-key row. Type `exit` at the Ubuntu shell to return to Termux. You do not reinstall everything each time.

Continue with [your first video](first-video.md).
