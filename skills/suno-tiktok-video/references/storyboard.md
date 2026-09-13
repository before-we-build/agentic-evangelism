# Lyrics → subideas → image sequence

[English](storyboard.md) · [Русский](storyboard.ru.md) · [Українська](storyboard.uk.md)

Read the extracted lyrics before planning art. Preserve the raw source, repeated verses/choruses and section cues. Remove non-sung production cues from the working text, not from the raw copy. Missing or conflicting text needs resolution; neither the song title nor musical style is a substitute for lyrics.

## Semantic analysis and song classification

Identify the central message, rhetorical structure, and successive main subideas (a contrast, concrete situation, question, response, emotional turn, or resolution). Merge adjacent lines expressing one idea; do not turn every line into an unrelated image.

Classify the song by narrative mode:
- **Narrative:** a specific protagonist or subject acts, with successive development of events or spiritual states (e.g. a pilgrim, prodigal son, trial of faith). Requires anchoring character identity.
- **Worship / contemplative:** praise, prayerful address, communal thanksgiving, or contemplation of God's creation dominate. The visual focus is on creation, light, symbolic space, prayerful gestures, or an impersonal silhouette.
- **Mixed:** personal testimony or lament shifts into corporate praise and joy (character appears in verses, expanding into communal or vast symbolic space in the chorus).

Separate literal lyrical meaning from chosen artistic metaphor. For example, "hope in the storm" is the lyric meaning, while "a boat on a nocturnal lake" or "a traveler on a mountain path" is the selected visual metaphor. For Christian content, distinguish biblical events from contemporary situations or allegories. Never portray artistic depictions as canonical scripture or verified historical facts.

## Character sheet (Character Anchor)

Identical brief phrasing does not guarantee an identical face in independent text-to-image generations, but a systematic Character Sheet maintains recognizable identity. Distinguish the **permanent anchor** from the **variable scene state**:

- **Permanent Anchor (invariant across all frames):**
  - Age bracket, face shape, skin tone.
  - Facial traits: 2–3 distinct features (e.g. straight nose, broad cheekbones, prominent brows).
  - Hair: color, length, texture, specific styling.
  - Silhouette and build.
  - Core wardrobe: cut, fabric, base color, and **one prominent contrast item** (e.g. deep navy tunic and an ochre scarf).
  - Simple distinct accessory (if story-appropriate).
- **Scene State (varies with the plot):** pose, emotion, action, rain-drenched fabric, direction of gaze.

Macro-attributes (silhouette, hairstyle, garment cut, and a prominent color accent) are far more reliable than micro-details: they remain identifiable in wide establishing shots and rapid mobile feed viewing. Formulate the anchor block and insert it verbatim into the prompts of all scenes featuring that character. Omit this block for scenes without the character.

## Art direction (Visual Bible)

A coherent visual style is defined by concrete physical choices rather than empty subjective buzzwords like "cinematic", "photorealistic", or "high quality". Specify:

- **Medium and texture:** e.g., realistic digital painting with delicate visible brushstrokes, or 35mm film still with natural organic grain.
- **Rendering of faces and surfaces:** matte finishes, natural human proportions, avoiding glossy plastic-like sheen.
- **Core palette and lighting:** muted earthy and slate-blue tones with warm ochre accents; gentle directional morning light and moderate contrast.
- **TikTok Safe Zone:** mobile interfaces obscure the top, right edge, and bottom third. Use the editorial heuristic bounding box `x=0.10…0.78`, `y=0.12…0.72` from the top-left corner. Position faces and primary gestures inside this safe area, keeping background space quiet at the bottom and right.

## Prompt formula

Every scene prompt is assembled from modular components in a consistent sequence:

```text
[Visual Bible / Overall Style Anchor]
→ [Character Anchor (if present in the scene)]
→ [Action & Emotional State]
→ [Setting, Time of Day & Lighting]
→ [Shot Size, Camera Angle & 9:16 Framing]
→ [Safe Zone / Interface Clearance]
→ [Negative Constraints: no text, no logos, no modern artifacts in ancient scenes]
```

## Shot variety and editing continuity

Use exact probed track duration D. Plan contiguous scenes covering 0 through D without gaps, audio edits, or claims of word synchronization. Initially distribute time across successive lyric sections (marked `editorial_estimate`).

Aim for visual changes about every 8–15 seconds (slower during contemplative prayers, more dynamic at climaxes).

**Editing rules for slideshows:**
1. **Never place more than two close-up face shots in a row.** A crossfade between two slightly differing AI-generated faces breaks the illusion of continuity.
2. **Alternate shot scales:** wide establishing shot → medium action → close-up emotional turn → detail shot (hands, road, book) → rear view / silhouette → resolving image.
3. Wide shots and rear angles maintain character recognition reliably through silhouette and wardrobe, giving the sequence a true cinematic feel.
4. For repeated choruses, return to a signature motif with an altered camera angle or lighting.

Before generation, summarize duration, main subideas, unique image count, scene count and approximate pacing. Proceed within the user's authorized request; do not introduce a new approval gate for the storyboard. For unusually large asset counts or explicit time/cost constraints, adapt the plan and disclose the tradeoff.

## Evidence scope

Checked 2026-09-12:
- [TikTok Creative Best Practices](https://ads.tiktok.com/business/en/blog/creative-best-practices-top-performing-ads): vertical composition, UI safe space, early hook and stimulating visual structure.
- [TikTok performance-ad guidance](https://ads-useast2a.tiktok.com/resources/help/article/creative-best-practices?lang=en): prioritize the opening six seconds and evaluate creative performance.

These are **advertising recommendations**. Applying them to a full-length organic music slideshow is an editorial inference, not evidence that a specific cut interval or image count will improve retention. Do not transplant ad length limits or claim guaranteed engagement. Refresh sources when making new current platform claims.

## Storyboard file (storyboard.json)

Save one JSON file next to the art. Example for a hypothetical 20-second track (replace with actual duration/text/paths):

```json
{
  "schema_version": 2,
  "timing_basis": "editorial_estimate_no_lyric_alignment",
  "lyrics_source": "lyrics.json",
  "central_message": "Hope during uncertainty",
  "narrative_mode": "mixed",
  "visual_bible": {
    "id": "style_01",
    "revision": 1,
    "anchor_text": "Realistic digital painting, delicate visible brushwork, matte surfaces, muted slate-blue and earthy palette, warm ochre accents, soft directional lighting.",
    "safe_zone": {
      "important_content_box": [0.10, 0.12, 0.78, 0.72]
    }
  },
  "characters": [
    {
      "id": "traveler_01",
      "depiction": "fictional_contemporary_metaphor",
      "revision": 1,
      "anchor_text": "A man around 40 years old, olive skin, angular face, broad cheekbones, straight nose, short dark wavy hair with grey at the temples, short neat beard, lean athletic build.",
      "wardrobe_text": "Matte navy blue mid-thigh traveler jacket, warm ochre scarf, dark brown trousers."
    }
  ],
  "subideas": [
    {
      "id": "s01",
      "summary": "A moment of doubt and seeking the path",
      "evidence": "working-text lines 1–4",
      "visual_interpretation": "Traveler pauses at a misty mountain crossroad"
    },
    {
      "id": "s02",
      "summary": "Morning hope and renewed trust in God",
      "evidence": "working-text lines 5–8",
      "visual_interpretation": "First morning rays illuminate the trail ahead"
    }
  ],
  "assets": [
    {
      "id": "a01",
      "subidea_id": "s01",
      "image": "art/01.png",
      "character_ids": ["traveler_01"],
      "shot": "medium_three_quarter",
      "action": "Pauses and gazes ahead with thoughtful contemplation",
      "setting": "Damp rocky path in early morning mountain mist",
      "prompt": "Realistic digital painting, delicate visible brushwork, matte surfaces, muted slate-blue palette, soft diffused lighting. A man around 40 years old, olive skin, angular face, broad cheekbones, short dark wavy hair with grey, short neat beard, matte navy blue jacket, warm ochre scarf. He pauses on a rocky path looking ahead with quiet reflection. Medium three-quarter shot, vertical 9:16 composition, subject centered left, clean negative space at bottom and right for interface, no text."
    },
    {
      "id": "a02",
      "subidea_id": "s02",
      "image": "art/02.png",
      "character_ids": ["traveler_01"],
      "shot": "wide_rear",
      "action": "Continues walking forward toward the breaking sunlight",
      "setting": "The same mountain trail as morning sunbeams pierce through mist",
      "prompt": "Realistic digital painting, delicate visible brushwork, matte surfaces, warm golden and ochre accents, soft directional morning light. A lean man in a navy jacket and warm ochre scarf walking forward along a mountain ridge. Wide rear shot from behind, morning sunlight illuminating the valley ahead. Vertical 9:16 composition, figure in lower-middle left, clean bottom safe zone, no text."
    }
  ],
  "scenes": [
    {"subidea_id": "s01", "image": "art/01.png", "duration_seconds": 8.0},
    {"subidea_id": "s02", "image": "art/02.png", "duration_seconds": 12.0}
  ]
}
```

The `build_video.py` helper directly consumes `scenes[].image` and `scenes[].duration_seconds`; the extended fields provide semantic, stylistic, and character traceability for the agent and user. Paths are absolute or relative to this JSON file. Scene start is the sum of preceding durations. Adjust the final duration to make the sum equal probed audio duration D within 0.15s. Verify each subidea has saved art and the sequence covers each intended occurrence. Do not describe this approximate timeline as subtitles or karaoke.
