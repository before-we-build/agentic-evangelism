# Make a finished video visible on Android

[English](android.md) · [Русский](android.ru.md) · [Українська](android.uk.md)

## Scan from Termux without ADB

After saving the verified MP4 in shared Downloads, run this on the phone in Termux or Ubuntu/PRoot with the Termux path mounted. Replace the sample basename with the actual short ASCII filename:

```sh
/data/data/com.termux/files/usr/bin/am broadcast --user 0 \
  -a android.intent.action.MEDIA_SCANNER_SCAN_FILE \
  -d file:///storage/emulated/0/Download/TikTok_song.mp4
```

The example uses Android owner profile `0`; use the actual profile on another setup. The Termux `am` wrapper must exist. On this phone, omitting `--user 0` caused an `INTERACT_ACROSS_USERS` permission error. For filenames with spaces or non-ASCII characters, construct a percent-encoded file URI (for example with Python `Path.as_uri()`) and pass it as one argument.

Expected output: `Broadcast sent without waiting for result`. This confirms only that Android accepted the scan request. Wait briefly, close and reopen TikTok’s picker, and check Videos or Downloads for the exact filename. On 2026-09-14, the user confirmed that `TikTok_Blazhenni.mp4` was visible there after this request on the project phone. This confirms picker visibility, not the time of indexing or a guarantee for other devices. If nobody checks the picker, report indexing as unconfirmed.

Android [deprecated this broadcast action from API 29](https://developer.android.com/reference/android/content/Intent#ACTION_MEDIA_SCANNER_SCAN_FILE); check the result on each device. Do not install tools or change permissions merely to scan one file.

## Optional ADB fallback

Use only an authorized connected device. Run `adb devices`; choose the intended device explicitly with `-s SERIAL`. If multiple devices are available and the target is unclear, ask. Do not reuse a historical wireless address: it changes.

Verify the file on the phone, not only inside PRoot. These examples assume the simple ASCII filename produced by the skill:

```sh
adb -s SERIAL shell ls -l /storage/emulated/0/Download/TikTok_peace.mp4
adb -s SERIAL shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///storage/emulated/0/Download/TikTok_peace.mp4
adb -s SERIAL shell content query --uri content://media/external/video/media --projection _id:_display_name:relative_path --where "\"_display_name='TikTok_peace.mp4'\""
```

Broadcast success alone does not prove indexing. Confirm a query row with the intended name and `relative_path=Download/`. For custom names, correctly quote Android shell arguments and encode file URIs; do not interpolate arbitrary filenames into shell code. Simple ASCII output names avoid this fragile step.

Broadcast support and permissions can vary by Android version. If the query initially returns no row, allow a short delay and retry once. If still absent, report that indexing is unconfirmed and inspect the reported error; do not loop indefinitely or change system permissions.

If the file is indexed but the picker remains stale: close and reopen the picker, choose Videos or Browse → internal storage → Download, and search the exact filename. Ask the user which picker they see only if these steps do not resolve it. If neither route confirms visibility, use the device's Files app to locate/open the MP4 and then reopen the picker. Neither a MediaStore row nor picker visibility proves upload or publication.

Observed lesson: filesystem presence and valid codecs are insufficient evidence of picker visibility. A short filename makes discovery easier; scanning provides the Android library entry. A Cyrillic filename alone does not establish the cause of a visibility issue.
