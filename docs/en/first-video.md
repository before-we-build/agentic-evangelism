# Make your first video

[Українська](../uk/first-video.md) · [Русский](../ru/first-video.md) · English

Finish [phone setup](phone-setup.md) first. This page starts with Codex running inside Ubuntu and the skill visible.

## 1. Save the song on your phone

Download the chosen audio from Suno or another source you are entitled to use. Use the service's Download action; wait until the download finishes. Open Android **Files → Downloads** and make sure the song is there. Download controls and available formats depend on your account. The skill does not create a Suno account or download a song from a private link.

Remember the filename. If you have several versions, specify which one you want. A newer file is not necessarily a better version, and its date does not prove where it came from. Keep the original audio.

## 2. Give Codex the task

Paste this into **Codex**, not the Ubuntu command prompt. Replace the example filename with yours:

> Use $suno-tiktok-video. My song is “My song.mp3” in Android Downloads. Make a vertical 1080×1920 video for the complete song, with several still illustrations following the lyrics. Generate independent pictures in parallel. Show which audio file you selected. Read the embedded lyrics; if absent, ask me for the text. Keep image changes approximate, without karaoke or subtitles. Save a new MP4 to Downloads with a short filename. Check the finished video and its Android visibility. Do not publish it.

If you know you want the most recent download, you can say “use the latest completed audio in Downloads.” The assistant should show the full path, size and modification time. If two files plausibly match, it should ask you to choose.

The assistant will read the lyrics, explain the main visual ideas, make pictures, assemble the full song and check the MP4. The song stays complete; the default has simple cuts between still pictures. Scene timings are editorial estimates, not verified word or chorus timestamps.

## 3. If the assistant needs something

**No lyrics inside the audio:** paste the lyrics you actually used, or give a matching local text file. Do not ask it to guess the verses from the title.

**No image tool in this session:** ask for one image prompt per main idea. Generate those pictures in an image tool you already have access to, download them, then explicitly tell Codex which files to use. Ask it to inspect them before montage. This manual handoff is a supported way to supply pictures; it is not automatic built-in generation. API generation is a separate optional route with separate setup and possible charges; the skill should not silently switch to it.

You can also use your own existing pictures without signing up for an image service. In Android Files, copy the chosen pictures to Downloads; long-press each copy and choose Rename, for example `scene-01.jpg` and `scene-02.jpg`. Keep its real extension: renaming a PNG to JPG does not convert it. Then send Codex this message, using your actual filenames:

> Use my existing pictures in Downloads: scene-01.jpg first, then scene-02.jpg. Inspect both and tell me whether they cover the song's main ideas. If more pictures are needed, tell me what is missing before building. Use these files instead of generating images, preserve the complete song, and save a new vertical MP4 in Downloads. Do not publish it.

Name every chosen picture in the message. The skill can reuse a suitable picture for a repeated chorus. This option needs your pictures; new AI illustrations still require access to a separate image service.

**A permission prompt:** read the concrete action and path. Reading your selected song, saving pictures and building the requested local video are part of the task. A new payment, publishing or deletion is a separate decision. Do not enable unrestricted device access merely to dismiss a message.

**A picture is unsuitable:** say exactly what needs changing. For example: “Keep the warm colours, but remove the invented lettering; this picture should show helping a neighbour.” Tell the assistant any preferences for how religious subjects should be illustrated before generation.

## 4. Watch the result

Open **Files → Downloads → the new MP4**. Watch the start, the end and several picture changes; listen through the song. Check the faces, hands, symbols, meaning and audio. The encoder check cannot decide whether an illustration expresses your faith accurately.

The result should include a full-song MP4, the extracted lyrics, a scene-plan JSON file and the pictures. JSON is a text file for the assistant; you do not need to edit it by hand. The assistant should report duration, size, number of pictures and scenes, and the check result.

## 5. Choose whether to share

In TikTok, open the upload picker, select **Videos** or **Downloads**, and find the exact MP4 filename. If it is missing, close and reopen the picker. The [troubleshooting guide](troubleshooting.md) explains the optional Android indexing step.

Preview the entire selected file before posting. Review the platform's current account limits and disclosure options at upload time. State AI involvement honestly; do not describe generated illustrations as documentary footage. The skill prepares a local video and does not publish it for you.

You can ask for revisions in ordinary language: “Change only the third picture; keep the full audio and save another version.” Keep the earlier result until you have checked the replacement.
