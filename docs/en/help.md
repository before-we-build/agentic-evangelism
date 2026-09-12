# Something is not working

[Українська](../uk/help.md) · [Русский](../ru/help.md) · English

Do not restart the installation or delete files. First, find your situation below.

| What happened | What to do |
| --- | --- |
| Text keeps scrolling on the screen | The program may still be installing. Wait for the command prompt to return. |
| It stopped at `[Y/n]` | This is a question. Type `y` and press Enter if you agree to continue this particular installation. |
| `Permission denied` when accessing Downloads | In Android settings, check that Termux has permission to access files. See setup step 2. |
| `command not found` | You may have pasted the command in the wrong place. `pkg` works in Termux; `apt` works inside Ubuntu. Do not reinstall everything. |
| Signing in with a code does not work | The code may have expired. Try a fresh code or ask for help with the regular `codex login` sign-in. You may need to enable sign-in by code in ChatGPT settings. |
| Codex cannot see the skill | Type `/skills` in the conversation. If `suno-tiktok-video` is missing, restart Codex. If that does not help, show setup step 6 to your helper. |
| It says the skill already exists | The existing copy was left unchanged. If it appears in `/skills`, you can continue. Otherwise, ask someone to help check its location. |
| Codex cannot create pictures | Use your own pictures: video step 3 explains how. Installing the skill alone does not enable image generation. |
| The video failed to build, or the file already exists | Keep the original. Ask Codex to explain the error and use a new filename for the result. |
| The video is in Files but missing from TikTok | Open it in Files, then close and reopen the selection window in TikTok. Search for the exact filename under Videos or Downloads. |

## How to ask for help

If Codex works, write to it. If it will not start yet, show this message to the person helping you set up:

> I am setting up my phone using the agentic-evangelism guide. I stopped at step __. I currently have __ open. The screen says: __. Explain one next action in simple words. Do not delete my files or turn off all protections.

Fill in the blanks. You can show a screenshot of the error, but hide passwords, sign-in codes and personal details first. Do not send your whole conversation history or account settings files.

**For the person helping:** [technical guide](troubleshooting.md). It covers checking the environment and installed skill, `bwrap` errors, and an optional ADB connection. ADB is not needed for ordinary video creation.

[Back to setup](phone-setup.md) · [Back to making a video](first-video.md)
