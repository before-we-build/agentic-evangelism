# When something does not work

[Українська](../uk/troubleshooting.md) · [Русский](../ru/troubleshooting.md) · English

This detailed reference is for someone helping with setup. If you are new here, start with [quick help](help.md).

Start with the exact error and the screen where it happened: Android, Termux, Ubuntu or Codex. Copy a short error message, not an entire private session or configuration. Hide login codes, tokens, email addresses and personal filenames before asking for public help.

## The command is not found

`pkg` and `termux-setup-storage` belong in **Termux**. `apt`, the installed `ffmpeg` and this guide's `codex` belong in **Ubuntu**. If you are inside Ubuntu and need Termux, leave Codex first, then type `exit` at the Ubuntu shell. Enter Ubuntu again with:

```sh
proot-distro login ubuntu --bind /storage/emulated/0:/storage/emulated/0
```

If `codex` is still missing inside Ubuntu, check the npm installation step. If an npm engine/version error appears, record `node --version` and the error before trying a different installer. Do not run downloaded repair scripts from an unknown source.

## Codex sign-in does not finish

Keep the terminal open while signing in in the browser on the same phone. A temporary code can expire; run the login command again for a fresh one. If device-code login is not allowed, check your account settings or use the ordinary `codex login` browser flow. Never paste credentials into a chat. [Login reference](https://developers.openai.com/codex/auth/).

## Downloads is missing or permission is denied

In Android settings, check Termux's file permission. Run `termux-setup-storage` in Termux if access has not been granted. Re-enter Ubuntu using the storage bind command above and check:

```sh
ls /storage/emulated/0/Download
```

The guide uses this full path directly. A convenience link such as `~/storage/downloads` is optional, not a requirement. Do not recreate or overwrite an existing folder to force a path match.

## The skill is not listed

Restart Codex and check `/skills`. The installer defaults to `~/.agents/skills/suno-tiktok-video`. An older installation may use another directory. Ask Codex which directory it actually loads. If it explicitly uses `~/.codex/skills`, leave Codex and run inside the project:

```sh
python3 scripts/install_skill.py --destination ~/.codex/skills
```

Do not install duplicate copies in different locations just to try everything. If the installer reports an existing copy, it has deliberately left that copy alone. Compare the folders, then use the [backup-preserving update commands](maintenance.md) with `--update` and the selected `--skill`, or use the repository's explicit `skills/suno-tiktok-video/SKILL.md` path for this task. Restart Codex after updating. Copying the skill cannot add an unavailable image tool.

## The agent reports a sandbox or bwrap error

On the recorded Android ARM64 phone, Ubuntu under Termux/PRoot and Codex CLI 0.154.0 repeatedly produced `bwrap: Can't get type of source /tmp/codex-bwrap-synthetic-mount-targets-0: No such file or directory`. The requested command had not started. The directory was visible to `ls`, but `bwrap` could not bind it by its virtual `/tmp` path; binding the same directory by its real PRoot rootfs path succeeded. This locates the failure at the PRoot path translation and `bwrap` boundary on that phone. It does not prove that every PRoot installation has the same problem.

**Where: at the Ubuntu shell inside Termux, after leaving Codex.** Test the same sandbox settings without changing your Codex configuration:

```sh
rootfs=$(readlink -f /proc/self/root)
TMPDIR="$rootfs/tmp" codex sandbox -c sandbox_mode=workspace-write -c sandbox_workspace_write.exclude_slash_tmp=true -- /bin/true
echo $?
```

**Expected:** the sandbox command prints nothing, and `echo $?` prints `0`. On the recorded phone this test and temporary-file creation succeeded. If it fails, save the short new error text; do not assume it is the same cause.

To start a new Codex conversation with these settings, use this command in the same Ubuntu shell:

```sh
rootfs=$(readlink -f /proc/self/root)
TMPDIR="$rootfs/tmp" codex -c sandbox_workspace_write.exclude_slash_tmp=true
```

**Expected:** Codex opens normally. Repeat this command for later sessions, or have a helper make a reviewed launcher in `~/.local/bin/codex` that supplies the same two settings and calls the real Codex binary. On the recorded phone such a launcher was installed and verified with `codex sandbox`; a full fresh-phone installation and every interactive workflow have not been tested. Check `command -v codex` before assuming that a launcher is being used. Do not make unrestricted access the default. If a managed environment forbids this setup, stop and ask its administrator.

## The render stopped or the output already exists

Keep the original song and earlier video. Use a new output filename; the helper refuses overwrite intentionally. Ask the assistant to check free space, file access, the audio format and whether all scene durations add up to the exact song length. Every referenced image must exist. An incomplete MP4 is not a finished deliverable.

Keep Termux open during a long render. If Android repeatedly stops it in the background, review the phone's battery settings for Termux. Menu names vary by manufacturer. A hot phone may need time to cool; do not keep restarting multiple renders.

## Video exists in Files but not in TikTok

First open the MP4 from **Files → Downloads**. Close and reopen TikTok's picker, select Videos or Browse/Downloads, and search its exact filename. A short filename helps finding it; Cyrillic names were not proven to cause the recorded problem.

If that does not work, request a scan without ADB. On the phone, run the command below in Termux or Ubuntu/PRoot with the Termux path mounted, replacing `TikTok_song.mp4` with your actual output filename:

```sh
/data/data/com.termux/files/usr/bin/am broadcast --user 0 \
  -a android.intent.action.MEDIA_SCANNER_SCAN_FILE \
  -d file:///storage/emulated/0/Download/TikTok_song.mp4
```

Expected output: `Broadcast sent without waiting for result`. Wait briefly, reopen TikTok's picker, and look under Videos or Downloads. On the project phone the user confirmed that `TikTok_Blazhenni.mp4` was visible after this request. The response alone does not confirm indexing; if the file is still absent, use Files or the optional ADB route below. See the [Android skill reference](../../skills/suno-tiktok-video/references/android.md) for filenames needing an encoded URI.

ADB is an optional fallback for a phone already connected to it. The following advanced route was also used on the project phone; another Android version may behave differently.

### Optional: connect the phone to itself with ADB

Android 11 or later provides wireless debugging. Use a trusted Wi-Fi network. Open **Settings → About phone** and tap **Build number** repeatedly until developer options are enabled; some manufacturers place it under Software information. Open **Developer options → Wireless debugging**, enable it and choose **Pair device with pairing code**. Names vary. [Android ADB instructions](https://developer.android.com/tools/adb#wireless-android11-command-line).

Keep the pairing dialog visible using split screen with Termux. Switching away closed it in the recorded attempt and caused `connection refused`.

**Inside Ubuntu**, install ADB if needed:

```sh
apt update
apt install adb
```

The next commands are templates, not text to paste unchanged. Take `PHONE_ADDRESS` and `PAIR_PORT` from the **pairing-code dialog** and substitute them below. Enter the pairing code only in the local terminal when asked:

```sh
adb pair PHONE_ADDRESS:PAIR_PORT
```

After successful pairing, return to the **main Wireless debugging screen**. Its IP address and port provide `PHONE_ADDRESS` and `CONNECT_PORT` for the next command. This connection port is different from the pairing port:

```sh
adb connect PHONE_ADDRESS:CONNECT_PORT
adb devices
```

Success: your device appears with status `device`. Use the identifier displayed by `adb devices` as `SERIAL` below. Never copy an old address from someone else's instructions. If more than one device appears, choose your intended phone explicitly.

### Optional: scan and verify one finished file

For a file actually named `TikTok_song.mp4`, replace `SERIAL` and run:

```sh
adb -s SERIAL shell ls -l /storage/emulated/0/Download/TikTok_song.mp4
adb -s SERIAL shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///storage/emulated/0/Download/TikTok_song.mp4
adb -s SERIAL shell content query --uri content://media/external/video/media --projection _id:_display_name:relative_path --where "\"_display_name='TikTok_song.mp4'\""
```

Use your real output filename consistently in all three commands. Ask the assistant to prepare correct quoting if it contains spaces or special characters. Broadcast success alone is not confirmation: the final query must show the filename and `relative_path=Download/`. If absent, wait briefly and try the query once more. If still absent, report indexing as unconfirmed and use Files; do not change system permissions blindly.

Reopen the picker after a successful scan. Turn off Wireless debugging when you are finished with it. Indexing does not mean the video was uploaded or published.
