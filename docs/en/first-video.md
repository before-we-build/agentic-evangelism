# Make a video for a song

[Українська](../uk/first-video.md) · [Русский](../ru/first-video.md) · English

You set up your phone [once](phone-setup.md). After that, repeat only the steps below for each new song.

**A Suno subscription is optional.** You can use an authorized song recording and your own photos. If you need Suno: Free has restrictions, and the cheapest paid plan, Pro, costs around $10 for a month with monthly billing. [Start without unnecessary spending and understand Suno limits](costs.md).

## 1. Download the song

Save audio from Suno or another source you have permission to use. Wait for the download to finish. If you are creating a song from scratch — from a Scripture verse and commentary to music — see the [music generation guide](music-generation.md).

Open **Files → Downloads**. Find the song and note its filename. Do not delete the original. If you have several versions, choose the one you want.

## 2. Open Codex

If you have just finished setup and the conversation with Codex is already open, go to step 3.

<details>
<summary>How to reopen Codex after a break</summary>

Otherwise, open **Termux**. If a conversation with Codex is already open there, you can also go to step 3.

If you see a normal command prompt, check:

```sh
cat /etc/os-release
```

If the answer includes **Ubuntu**, skip the next box. If the file is not found, open Ubuntu:

```sh
proot-distro login ubuntu --bind /storage/emulated/0:/storage/emulated/0
```

Open the project folder and the assistant, one box at a time:

```sh
cd ~/projects/agentic-evangelism
```

```sh
codex
```

**You should see:** a place to type a request to the assistant. If you see an error, open [help](help.md).

</details>

## 3. Ask for a video

Copy the message below **into your conversation with Codex**. Replace `My song.mp3` with your file's actual name:

> Use $suno-tiktok-video. My song “My song.mp3” is in Downloads. Make a video for the whole song, with pictures based on its meaning. If you need lyrics or pictures, explain what I should do. Save the video in Downloads. Do not publish it.

Codex should show you the file and explain which pictures it will prepare. If it asks for the lyrics, send them. If it asks you to choose between versions, name the one you want.

When a permission request appears, read the action and filename. Allow only what is needed for your video. If anything is unclear, ask for an explanation.

The pictures will be still, and they will change roughly with the meaning of the song, without matching the words exactly. Transitions between pictures are smooth crossfades by default. If you prefer sharp cuts without fades, you can ask for simple cuts (`--transition none`). The whole song will play.

**Tip for style and characters:** If your song is story-driven or you prefer a specific art style, specify it in your request, for example:
> Create illustrations in a unified realistic digital painting style. The protagonist is a traveler around 40 years old in a navy jacket and ochre scarf; keep his appearance and clothing consistent across all scenes featuring him.

<details>
<summary>No image generation? Use your own pictures</summary>

Save the pictures you want in **Downloads**. In the Files app, you can press and hold a file → **Rename** and give it a simple name such as `scene-01.jpg` or `scene-02.jpg`. Keep the real file extension: do not change `.png` to `.jpg`.

Send Codex a message with the actual names of all the pictures you chose:

> For this song, use my pictures from Downloads: scene-01.jpg first, then scene-02.jpg. Look at them. If the song needs other scenes to convey its meaning, tell me. Do not generate new pictures. Save a video for the whole song in Downloads, and do not publish anything.

New AI illustrations require access to an image generation service. If Codex does not have access, it can prepare descriptions for another service you use. A separate paid method will not be enabled without your consent.

</details>

## 4. Watch the result

Open **Files → Downloads → the new MP4**. Codex will tell you the finished file's name.

Watch the video and listen to the whole song. Check the lyrics, Bible quotations, faces, hands and what the pictures show. AI can make mistakes; do not present an invented scene as a real event or testimony.

If you do not like something, you could write:

> Change the third picture so it shows someone helping their neighbour. Keep the rest and the whole song. Make a new version of the file.

Keep the old version until you have watched the new one.

## 5. Share when you are ready

Open YouTube, TikTok or Instagram, choose the video upload option and select your MP4. Check that the service accepts its length, and watch the preview before publishing. Be honest about the use of AI.

If the video is in Files but missing from the selection window, close and reopen that window and look under **Videos / Downloads**. [More tips](help.md).

You publish it yourself. In this task, Codex only prepares the file. You can ask for the next song in the same conversation.
