# Creating Christian Songs: From Scripture to Music

[Українська](../uk/music-generation.md) · [Русский](../ru/music-generation.md) · English

This guide explains how to go from a Scripture verse that touches the heart to a finished song audio file using popular AI music generators (Suno, Udio, and others). The resulting audio can then be turned into a video using the [video creation guide](first-video.md).

---

## 1. The Spiritual and Creative Path (5 Steps)

A true Christian song does not begin with an arbitrary prompt; it grows out of the living work of God's Word:

1. **Living Word (Spark):** Start with a Scripture verse that moved your heart, opened up with fresh depth, or stirred holy awe ("heart burning within", Luke 24:32).
2. **Theological Depth (Roots):** Look to trusted teachers of the faith (Charles Spurgeon, John Bunyan, Matthew Henry) to ground your experience in sound doctrine and understand the biblical context.
3. **Poetry (Wings):** Frame the truth as a psalm or hymn with clear verses and an uplifting chorus of praise.
4. **Music:** Generate melody and vocals in a suitable style using an AI music generator.
5. **Human Review:** Listen to the resulting track yourself, checking lyric clarity and pronunciation.

---

## 2. How to Prepare Lyrics for a Song

You can ask an AI assistant (such as Codex or ChatGPT) to help compose lyrics:

> "The verse [insert Scripture reference, e.g., Romans 8:38-39] deeply touched my heart. Look up how Charles Spurgeon (or other faithful commentators) explained this passage. Based on this truth, help write Christian song lyrics: 2 verses, a chorus, and a bridge. Use clear, reverent language suitable for young people."

### Song Structure Tags
Music generators best understand lyrics when structured with standard section tags:

```text
[Verse 1]
Opening verse lines: story, reflection, soul's question.

[Chorus]
Chorus: core biblical truth, climax, praise to Christ.

[Verse 2]
Second verse: deepening theme, resting on God's promise.

[Chorus]
Chorus repeat.

[Bridge]
Bridge: spiritual turning point, elevation, or quiet prayer.

[Outro]
Ending: fading words of thanksgiving.
```

---

## 3. Guide to Popular Music Generators

### Suno (suno.com)
The most practical service for full songs with verses, choruses, and clear vocals.

1. Visit **suno.com** (from phone or desktop) and sign in.
2. Click **Create** in the menu.
3. Turn on the **Custom** toggle:
   * Paste your prepared lyrics with tags (`[Verse]`, `[Chorus]`, etc.) into **Lyrics**.
   * Enter your desired musical style in **Style of Music** (see examples below).
   * Enter the song title in **Title**.
4. Click **Create** (two variations will be generated).
5. Listen to both variations. If a song stops prematurely, click `...` next to the track → **Extend** to continue.
6. **How to download:** click `...` on the chosen track → **Download** → **Audio** (saved to your Downloads folder).

**Style of Music Prompt Examples for Suno:**
* *Acoustic worship:* `acoustic worship, warm male vocal, acoustic guitar, soft piano, reverent hymn, uplifting chorus`
* *Solemn choir:* `majestic church choir, choral hymn, orchestra, strings, reverent, solemn worship`
* *Contemporary Christian (CCM):* `contemporary Christian music, passionate female vocals, melodic electric guitar, ambient pads, driving drums`
* *Quiet prayerful hymn:* `prayerful devotional, soft acoustic piano, gentle cello, intimate vocals, peaceful`

---

### Udio (udio.com)
Known for rich harmonies, organic vocals, and step-by-step section expansion.

1. Visit **udio.com** and sign in.
2. Select **Custom** mode in the prompt bar.
3. Paste your lyrics.
4. In the prompt/style field, enter: `Christian worship, acoustic gospel hymn, rich choral harmonies, emotive, spiritual`.
5. Click **Create**. Udio generates a snippet (typically 32 seconds).
6. Use **Extend** ("Add Section Before" for intro, "Add Section After" for continuation, and "Add Outro" for conclusion) to assemble the full song.
7. Once the full song is ready, click `...` → **Download** → save the audio file to Downloads.

---

### AIVA (aiva.ai)
Suited for instrumental, symphonic, and choral classical compositions (e.g., for meditative Scripture reading or prayer pauses).

1. Create an account on **aiva.ai**.
2. Select a composition profile: *Symphonic Fantasy*, *Choral*, or *Ambient*.
3. Generate the composition and export as MP3.

---

### Mubert (mubert.com) and Soundraw (soundraw.io)
Great for creating quiet ambient or acoustic background soundtracks. If you need instrumental accompaniment for reading Scripture aloud, these are convenient options.

---

## 4. Licenses and Attribution

* **Free Tiers (Free):** Suno and Udio on free tiers permit non-commercial use and require attribution. Our video build script automatically detects generator metadata and adds a clean, subtle attribution badge in the opening seconds.
* **Paid Plans (Pro / Premier):** grant commercial rights. The intro badge can be omitted during video creation using `--license commercial`.
* **Honest Publishing:** when posting to social media (YouTube, TikTok, Instagram), enable the platform's standard "AI-generated content" disclosure.

---

## 5. Reviewing the Track Before Making a Video

Before building the video, always review the audio personally:
* ensure the words are clearly enunciated and faithful to Scripture;
* check that there are no severe audio glitches;
* ensure the song reaches a natural conclusion.

Once your audio file is ready in **Downloads**, proceed to assembling your video: **[Video Creation Guide](first-video.md)**.
