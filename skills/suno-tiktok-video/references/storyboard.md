# Lyrics → subideas → image sequence

[English](storyboard.md) · [Русский](storyboard.ru.md) · [Українська](storyboard.uk.md)

Read the extracted lyrics before planning art. Preserve the raw source, repeated verses/choruses and section cues. Remove non-sung production cues from the working text, not from the raw copy. Missing or conflicting text needs resolution; neither the song title nor musical style is a substitute for lyrics.

## Semantic plan

Identify the central message and the successive main subideas (a contrast, concrete situation, question, response, emotional turn, or resolution). Merge adjacent lines expressing one idea; do not turn every line into an unrelated image. Give subideas stable IDs and a short supporting excerpt or line reference. Separate actual lyrical meaning from artistic metaphor. Do not invent theology, political actors or plot events absent from the text.

Each main subidea gets a distinct image. Repeated refrains can reuse their associated images; preserve their occurrence in the planned sequence rather than deduplicating the lyrics. Use a coherent palette, visual style and recurring motifs. Longer passages can alternate a few related compositions to avoid one image lasting a minute. Asset count and scene count differ: one saved image may appear more than once.

## Approximate pacing without lyric timestamps

Use exact probed track duration D. Plan contiguous scenes covering 0 through D, without gaps, audio edits or claims of word synchronization. Initially distribute time across successive lyric sections in proportion to their text length (or syllable estimates if readily available), allowing explicit estimated intro/outro/instrumental portions where supported. This is a rough editorial allocation: delivery speed, long notes, repeats and instrumental breaks can make it wrong. Mark it `editorial_estimate`; never claim to have heard or verified boundaries unless actually checked against audio.

As a creative starting point, aim for visual changes about every 8–15 seconds, slower for contemplative passages and faster for energetic passages. This range is a **local editing heuristic**, not a measured TikTok optimum or a hard limit. Divide long estimated sections into related views/reuse of that subidea's art; do not require a newly generated image for every change. Keep the first frame immediately legible and emotionally relevant. No unrelated teaser, delayed blank title card, flashing or gratuitous cuts. Let the final scene resolve the song's central image. Do not add advertising CTAs or shorten the full song automatically.

Before generation, summarize duration, main subideas, unique image count, scene count and approximate pacing. Proceed within the user's authorized request; do not introduce a new approval gate for the storyboard. For unusually large asset counts or explicit time/cost constraints, adapt the plan and disclose the tradeoff.

## Evidence scope

Checked 2026-09-12:
- [TikTok Creative Best Practices](https://ads.tiktok.com/business/en/blog/creative-best-practices-top-performing-ads): vertical composition, UI safe space, early hook and stimulating visual structure.
- [TikTok performance-ad guidance](https://ads-useast2a.tiktok.com/resources/help/article/creative-best-practices?lang=en): prioritize the opening six seconds and evaluate creative performance.

These are **advertising recommendations**. Applying them to a full-length organic music slideshow is an editorial inference, not evidence that a specific cut interval or image count will improve retention. Do not transplant ad length limits or claim guaranteed engagement. Refresh sources when making new current platform claims.

## Storyboard file

Save one JSON file next to the art. Example for a hypothetical 20-second track (replace with actual duration/text/paths):

```json
{
  "timing_basis": "editorial_estimate_no_lyric_alignment",
  "lyrics_source": "lyrics.json",
  "central_message": "Hope during uncertainty",
  "subideas": [
    {"id": "uncertainty", "summary": "A moment of doubt", "evidence": "working-text lines 1–4"},
    {"id": "hope", "summary": "A hopeful response", "evidence": "working-text lines 5–8"}
  ],
  "assets": [
    {"image": "art/01.png", "subidea_id": "uncertainty", "prompt": "Actual complete generation prompt"},
    {"image": "art/02.png", "subidea_id": "hope", "prompt": "Actual complete generation prompt"}
  ],
  "scenes": [
    {"subidea_id": "uncertainty", "image": "art/01.png", "duration_seconds": 8.0},
    {"subidea_id": "hope", "image": "art/02.png", "duration_seconds": 12.0}
  ]
}
```

Renderer consumes `scenes[].image` and `scenes[].duration_seconds`; the other fields provide semantic traceability for the agent and user. Paths are absolute or relative to this JSON file. Scene start is the sum of preceding durations. Adjust the final duration to make the sum equal D. Verify each subidea has saved art and the sequence covers each intended occurrence. Do not describe this approximate timeline as subtitles or karaoke.
