# Set up your phone once

[Українська](../uk/phone-setup.md) · [Русский](../ru/phone-setup.md) · English

You need an Android phone and internet. No computer is needed. If you are using a computer (Windows, Mac, or Linux), see the general [setup guide](setup.md). If Codex already works and can see the `suno-tiktok-video` skill, go to [making a video](first-video.md).

**How to follow the steps:** copy the text from a grey box, press and hold the screen in the right app → **Paste** → **Enter**. Wait for it to finish before moving on.

If you see `Do you want to continue? [Y/n]`, type `y` and press Enter to continue installing. If you see an error or an unclear question about replacing files, stop and open [help](help.md).

**A Suno subscription is optional.** You can use an authorized song recording and your own photos. If you need Suno: Free has restrictions, and the cheapest paid plan, Pro, costs around $10 for a month with monthly billing. [Start without unnecessary spending and understand Suno limits](costs.md).

## 1. Install Termux

Termux is the app where you will paste the commands below.

1. Open the [Termux download page](https://f-droid.org/en/packages/com.termux/).
2. Find **Download APK**, download the file and open it. You do not have to install F-Droid itself.
3. If Android asks for permission to install an app from your browser, allow this installation.
4. Open Termux and wait for it to get ready.

If Termux is already installed, do not uninstall it: it may contain your files. Keep a few gigabytes of free space and use Wi-Fi if you can.

## 2. Prepare Termux

**Where: in Termux.** Paste one box at a time.

Update the tools:

```sh
pkg update
pkg upgrade
```

Give Termux access to your phone's files:

```sh
termux-setup-storage
```

Tap **Allow** when Android asks. Check access:

```sh
ls ~/storage/downloads
```

**You should see:** a list of your downloads. If the folder is empty, the list will be empty. `Permission denied` means access is missing — do not continue yet.

## 3. Install Ubuntu

Ubuntu lets the video programs run inside Termux. It does not replace Android or require you to root your phone.

**Where: in the same Termux app.**

```sh
pkg install proot-distro
```

```sh
proot-distro list
```

If Ubuntu is already installed, skip the next box. Otherwise:

```sh
proot-distro install ubuntu
```

Wait for the download to finish. Then open Ubuntu:

```sh
proot-distro login ubuntu --bind /storage/emulated/0:/storage/emulated/0
```

**You are still in the Termux app, but Ubuntu now runs your commands.** Check:

```sh
cat /etc/os-release
```

**You should see:** the name Ubuntu. Enter all the following commands here, through step 7.

## 4. Install the video programs and Codex

**Where: in Termux with Ubuntu open.**

```sh
apt update
apt install nodejs npm git python3 ffmpeg ca-certificates
```

When installation finishes:

```sh
npm install -g @openai/codex
```

Check:

```sh
codex --version
```

**You should see:** `codex-cli` and a version number. If there is an error, do not reinstall everything — [ask for help](help.md).

If Codex later reports `bwrap: Can't get type of source /tmp/codex-bwrap-synthetic-mount-targets-...`, see the [tested PRoot workaround](troubleshooting.md#the-agent-reports-a-sandbox-or-bwrap-error). This is a sandbox startup error, not a reason to reinstall the video programs.

## 5. Sign in to your account

**Where: in Termux with Ubuntu open.**

```sh
codex login --device-auth
```

1. Open the link Codex shows you in the browser on this same phone.
2. Sign in to your ChatGPT account and enter the temporary code shown.
3. Return to Termux. Keep Termux open while you sign in.

Check that you are signed in:

```sh
codex login status
```

**You should see:** a message confirming that you are signed in. Do not send the code to anyone. If signing in with a code is unavailable, see [help](help.md).

## 6. Download the project

**Where: in Termux with Ubuntu open.**

```sh
mkdir -p ~/projects
cd ~/projects
```

```sh
git clone https://github.com/before-we-build/agentic-evangelism.git
```

If it says the `agentic-evangelism` folder already exists, do not delete it. Simply continue:

```sh
cd ~/projects/agentic-evangelism
```

Install the skill — a ready-made set of instructions for the assistant:

```sh
python3 scripts/install_skill.py
```

**You should see:** `Встановлено / Установлено / Installed` and the path to the skill. If a copy already exists, the program will leave it unchanged; [help explains what to do](help.md).

## 7. Open the assistant and check that everything is ready

In the same window, enter:

```sh
codex
```

Read the question about trusting the folder and granting permissions. You are now in **a conversation with Codex**. Send it this message:

> Check whether my phone is ready to make videos: can you see the suno-tiktok-video skill, my downloaded files, and the ffmpeg and ffprobe programs? Can you create and save pictures in this particular conversation? Do not generate anything or spend money yet. Explain in simple words what is ready and what is missing.

**You are ready when:** Codex can see the song in Downloads, run the video programs, and use either image generation or your own pictures. Installing the skill alone does not enable image generation.

👉 Next: **[make a video](first-video.md)**. You do not need to repeat the installation next time.

---

This method has been used on an Android phone, but the full process on a phone with nothing installed yet has not been tested. You may need help on another device. [Tested steps and official sources](maintenance.md) · [Technical guide for your helper](troubleshooting.md).
