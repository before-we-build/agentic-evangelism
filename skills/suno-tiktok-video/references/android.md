# Make a finished video visible on Android

[English](android.md) · [Русский](android.ru.md) · [Українська](android.uk.md)

Use only an authorized connected device. Run `adb devices`; choose the intended device explicitly with `-s SERIAL`. If multiple devices are available and the target is unclear, ask. Do not reuse a historical wireless address: it changes.

Verify the file on the phone, not only inside PRoot. These examples assume the simple ASCII filename produced by the skill:

```sh
adb -s SERIAL shell ls -l /storage/emulated/0/Download/TikTok_peace.mp4
adb -s SERIAL shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///storage/emulated/0/Download/TikTok_peace.mp4
adb -s SERIAL shell content query --uri content://media/external/video/media --projection _id:_display_name:relative_path --where "\"_display_name='TikTok_peace.mp4'\""
```

Broadcast success alone does not prove indexing. Confirm a query row with the intended name and `relative_path=Download/`. For custom names, correctly quote Android shell arguments and encode file URIs; do not interpolate arbitrary filenames into shell code. Simple ASCII output names avoid this fragile step.

Broadcast support and permissions can vary by Android version. If the query initially returns no row, allow a short delay and retry once. If still absent, report that indexing is unconfirmed and inspect the reported error; do not loop indefinitely or change system permissions.

If the file is indexed but the picker remains stale: close and reopen the picker, choose Videos or Browse → internal storage → Download, and search the exact filename. Ask the user which picker they see only if these steps do not resolve it. If no ADB access exists, use the device's Files app to locate/open the MP4 and then reopen the picker. Do not claim publication or upload success from a MediaStore row.

Observed lesson: filesystem presence and valid codecs are insufficient evidence of picker visibility. A short filename makes discovery easier; scanning provides the Android library entry. A Cyrillic filename alone does not establish the cause of a visibility issue.
