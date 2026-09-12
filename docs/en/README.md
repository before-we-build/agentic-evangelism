# Start here

[Українська](../uk/README.md) · [Русский](../ru/README.md) · English

This project helps people prepare Christian songs, illustrations and videos with AI assistance. “Agentic” means the assistant can carry out several steps: find your audio file, read its lyrics, make a scene plan, prepare pictures and assemble a video. You choose the message, check the result and decide what to share.

The first working example is a complete song turned into a vertical video for TikTok. The pictures change during the music. It is a slideshow, not moving AI animation. Independent pictures are requested in parallel when the service allows it.

## What you need

- An Android phone, internet access and space for Linux tools, pictures and video. Keep several gigabytes free as a practical starting allowance, not a guaranteed requirement. Keep the phone charged during rendering.
- An account with access to Codex. Generating images needs a separately available image tool in the session; installing this repository does not unlock it. Check access and cost in your own account before paying for anything.
- A downloaded song that you are entitled to use, and its lyrics if they are not inside the audio file.

You do not need a computer, a GitHub account just to download this repository, LabelGrid, ADB, or programming knowledge for the main route. You will copy a few commands during setup. The guide explains where to paste them and how to know each step worked.

This phone route is for **Android with Termux and Ubuntu**. We have not tested an equivalent local setup on iPhone. An iPhone user can prepare text and pictures in a browser and use a phone video editor, but that is a separate manual workflow.

## Choose your next step

1. New to this? Follow [phone setup](phone-setup.md).
2. Codex already runs on your phone? Go to the repository step in that guide, then [make your first video](first-video.md).
3. Something failed? Find the message in [troubleshooting](troubleshooting.md).
4. Helping others or updating the project? Read [maintenance and evidence](maintenance.md).

## A few words used in the guide

| Word | Meaning here |
| --- | --- |
| Terminal | An app screen where you type or paste commands. |
| Termux | The Android app that provides that screen and basic tools. |
| Ubuntu / Linux | A working environment inside Termux, used to run the tools in this guide. It does not replace Android. |
| Codex | The AI assistant you give tasks to in ordinary language. |
| Skill | A folder of instructions and helpers that teaches the assistant a repeatable workflow. |
| Repository | The project folder and its copy on GitHub. |
| Render | Turn pictures and sound into a finished video file. |

## How we use AI for evangelism

Start from a message you can stand behind. Check Bible quotations against the translation you intend to use. Present interpretations as interpretations; do not pass invented statements off as Scripture, testimony or words from God. Ask a trusted church member or pastor to review material when you need help with its meaning.

Treat people as people: honest conversation, permission to disengage, no spam, impersonation or pressure. This repository prepares materials; it does not run automatic messages to strangers. Describe AI involvement honestly and check the audio, images and any people's likenesses before sharing. Publishing is a separate human decision.

These instructions are independent of OpenAI, Suno, TikTok and Termux; they are not an official endorsement by those services. The working phone experience and its limits are recorded in [maintenance](maintenance.md).
