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

### Optional supplied avatar

To keep a chosen face instead of inventing one, set `characters[].avatar_image` to a user-supplied PNG, JPEG, or WebP file (absolute path or relative to `storyboard.json`). Keep the original in a private local workspace, outside the repository; do not commit personal likenesses. `assets[].character_ids` selects which avatars each image needs. An avatar is a reference for identity, not a finished scene: keep describing clothing, action, angle, setting, style, and framing in the prompt. Describe only visible traits that agree with the reference; do not invent a different face. This field is optional, and characters without it follow the existing text-anchor workflow.

After writing the storyboard, run `python3 scripts/avatar_refs.py --storyboard '/absolute/workspace/storyboard.json'` from this skill directory. It validates avatar files and prints absolute `reference_images` paths per asset. On Android Termux, run it in the same shell used for `prepare_video.py`; expect JSON with each asset ID and its paths. For the built-in `image_gen` tool, inspect each supplied avatar, then pass that asset's `reference_images` as `referenced_image_paths` on its anchor test and every dependent scene call. Do not also set `num_last_images_to_include`. Keep the same avatar as the identity source across angles; an optional generated style anchor may accompany it only if the tool accepts multiple references. If the active image tool cannot accept image references, do not silently fall back to a newly invented face: use supplied finished scene images or explain the limitation and ask how to proceed. Image reference improves consistency but does not guarantee an exact likeness; inspect the test scene and final faces.

## Art direction (Visual Bible)

A coherent visual style is defined by concrete physical choices rather than empty subjective buzzwords like "cinematic", "photorealistic", or "high quality". Specify:

- **Medium and texture:** e.g., realistic digital painting with delicate visible brushstrokes, or 35mm film still with natural organic grain.
- **Rendering of faces and surfaces:** matte finishes, natural human proportions, avoiding glossy plastic-like sheen.
- **Core palette and lighting:** muted earthy and slate-blue tones with warm ochre accents; gentle directional morning light and moderate contrast.
- **TikTok Safe Zone:** mobile interfaces obscure the top, right edge, and bottom third. Use the editorial heuristic bounding box `x=0.10…0.78`, `y=0.12…0.72` from the top-left corner. Position faces and primary gestures inside this safe area, keeping background space quiet at the bottom and right.

## Visual policy and confessional profiles (visual_policy)

To prevent unwanted religious artifacts while allowing intentional storytelling, the storyboard establishes a three-tier policy hierarchy:
```text
Project default (evangelical_baptist) → Song policy → Scene policy override
```
Switching or overriding a profile replaces its baseline rules rather than accumulating conflicting negative prompts.

### Supported profiles

- **`evangelical_baptist` (Default editorial profile):**
  - **Core themes:** Scripture reading and study, personal and congregational prayer, sincere worship, mutual care, family, and God's majestic creation, as supported by the selected lyrics.
  - **Excluded attributes:** Personal halos or luminous disks behind heads, devotional icons, gilded icon frames, iconostases, shrines, onion-domed church architecture, and later liturgical vestments (cassocks, chasubles, mitres, censers, rosaries).
  - **Reverence through natural light:** Use directional physical daylight from visible windows, sunrise/sunset, and natural shadows. Heads and backgrounds behind them must remain evenly illuminated without glowing auras. Never portray God the Father as a physical figure or depict light as magical personal holiness.
  - **Biblical narratives:** Preserve ancient first-century Judean/biblical settings (simple unadorned tunics, sandals, dusty roads), cleanly distinguished from later medieval/Byzantine ecclesiastical garb.
- **`interdenominational_unity` (Joint Christian prayer and unity):**
  - **Context:** Songs or scenes depicting believers from diverse Christian traditions (Orthodox, Catholic, Protestant / Baptist) coming together in prayer and fellowship.
  - **Composition & equality:** Semicircular gathering at the same ground level with equal visual prominence. Clergy stand among laity; participants exhibit quiet concentration, mutual respect, and humble prayer postures (bowed heads, folded or natural hands).
  - **Setting & symbols:** Neutral, bright space (simple meeting room opening onto a garden, nature, or courtyard); simple unadorned wooden cross and open Bible as shared Christian touchpoints. No single denominational sanctuary dominates.
  - **Targeted rules:** Halos, devotional icons, and icon-veneration actions remain strictly excluded. Do not depict divisive Eucharistic rituals or communion vessels. Deliberately requested traditional attire (e.g. a plain cassock with modest pectoral cross, a dark clerical shirt with white collar, an ordinary contemporary suit) is preserved and not filtered.
- **`christian_fellowship`:**
  - Warm Christian community, prayer, and service in ordinary contemporary clothes without emphasizing confessional symbols.
- **`custom`:**
  - Dedicated overrides with explicitly documented scope for specific historical or confessional narratives.

### Formulating constraints in prompts

When generating images directly in the terminal via an agent, the prompt should combine positive physical description with clear, targeted negative constraints:

1. **Positive physical description (Primary defense):**
   Explicitly describe the desired environment so the generator does not fill ambiguities with ecclesiastical defaults:
   - Instead of generic church interior → `plain uninterrupted white plaster walls, clear rectangular windows, simple wooden lectern`
   - Instead of generic religious dress → `ordinary contemporary clothing, charcoal cardigan over a light cotton shirt`
   - Instead of vague architectural style → `rectangular brick building with a simple pitched roof`
   - Instead of avoiding halos → `side-lit face against an evenly illuminated matte wall, natural shadows`
   - Instead of generic altar items → `the tabletop holds an open Bible and a drinking glass`

2. **Targeted negative constraints block:**
   Append a specific constraints block to the prompt without using overbroad words:
   - *Halos:* `no halos, no luminous rings around heads, no gold disks behind heads`
   - *Devotional art:* `no devotional icons, no icon panels, no iconostases, no gilded icon frames, no shrines`
   - *Architecture:* `no onion domes, no Eastern Orthodox church domes, no three-bar Orthodox crosses`
   - *Later vestments:* `no unrequested cassocks, chasubles, phelonions, bishop's mitres, klobuks, or embroidered vestments`
   - *Ritual objects:* `no censers, thuribles, reliquaries, rosaries, or votive candles before icons`
   *(Do not use blunt stop-words like `cross`, `robes`, `candles`, `washing`, which break biblical narratives like Golgotha, ancient tunics, lamps, foot-washing, or baptism).*

### Example: Interdenominational joint prayer prompt

```text
Respectful realistic digital painting with delicate visible brushwork, matte surfaces, natural human proportions, muted earth tones and soft morning daylight.
An imagined contemporary interdenominational Christian prayer gathering: eight adult Orthodox, Catholic and Protestant Christians, including Baptist believers, praying together for peace and unity in Christ.
The group includes women and men of different ages, skin tones and cultural backgrounds. Most wear modest everyday clothing. One Orthodox priest wears a plain dark cassock and a modest pectoral cross. One Catholic priest wears a simple dark clerical shirt with a white collar. A Baptist participant wears an ordinary jacket without clerical insignia.
They stand together in a gentle semicircle at the same ground level, with equal visual prominence. Heads are slightly bowed; hands rest naturally or are loosely clasped. Quiet concentration, mutual respect and a shared sense of hope. The clergy stand among the other believers.
A bright, simple community room with plain walls and large windows opening onto a garden. A small unadorned wooden cross on the rear wall. An open Bible rests on a plain side table, its pages angled so that no writing is legible.
Medium-wide group composition at eye level, vertical 9:16. Safe zone x=0.10–0.78, y=0.12–0.72. Leave quiet visual space along the bottom and right edges.
Scene constraints: no halos or luminous rings around heads; no icons, religious statues, domed architecture, ornate vestments, mitres, incense; no kissing or bowing toward religious images; no Eucharistic vessels or communion ritual; no text or logos. Explicitly described cassock, clerical collar and modest pectoral cross remain visible.
```

## Prompt formula

Every scene prompt is assembled from modular components in a consistent sequence:

```text
[Scene Subject & Action]
+ [Character Anchor (if present in the scene, verbatim)]
+ [Visual Bible: medium, palette, surface finish]
+ [Concrete Setting, Period, Wardrobe & Physical Lighting]
+ [Shot Scale, Camera Angle & 9:16 Framing]
+ [Safe Zone / Interface Clearance: x=0.10…0.78, y=0.12…0.72]
+ [Applicable Constraints compiled for target tool]
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
    "visual_policy": {
      "profile": "evangelical_baptist",
      "revision": 1,
      "source": "repository_default",
      "positive_markers": [
        "scripture_reading",
        "ordinary_believers",
        "simple_meeting_spaces",
        "mutual_care",
        "creation"
      ],
      "excluded_features": [
        "personal_halos",
        "devotional_icons",
        "iconostases",
        "onion_domed_churches",
        "later_liturgical_vestments"
      ]
    },
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
      "prompt": "Realistic digital painting, delicate visible brushwork, matte surfaces, muted slate-blue palette, soft diffused lighting. A man around 40 years old, olive skin, angular face, broad cheekbones, straight nose, short dark wavy hair with grey at the temples, short neat beard, lean athletic build. Matte navy blue mid-thigh traveler jacket, warm ochre scarf, dark brown trousers. He pauses on a rocky path looking ahead with quiet reflection. Medium three-quarter shot, vertical 9:16 composition, subject centered left, clean negative space at bottom and right for interface, plain evenly lit background behind head, no text, no halos."
    },
    {
      "id": "a02",
      "subidea_id": "s02",
      "image": "art/02.png",
      "character_ids": ["traveler_01"],
      "shot": "wide_rear",
      "action": "Continues walking forward toward the breaking sunlight",
      "setting": "The same mountain trail as morning sunbeams pierce through mist",
      "prompt": "Realistic digital painting, delicate visible brushwork, matte surfaces, warm golden and ochre accents, soft directional morning light. A man around 40 years old, olive skin, angular face, broad cheekbones, straight nose, short dark wavy hair with grey at the temples, short neat beard, lean athletic build. Matte navy blue mid-thigh traveler jacket, warm ochre scarf, dark brown trousers. Walking forward along a mountain ridge. Wide rear shot from behind, morning sunlight illuminating the valley ahead. Vertical 9:16 composition, figure in lower-middle left, clean bottom safe zone, no text, no halos."
    }
  ],
  "scenes": [
    {"subidea_id": "s01", "image": "art/01.png", "duration_seconds": 8.0},
    {"subidea_id": "s02", "image": "art/02.png", "duration_seconds": 12.0}
  ]
}
```

The `build_video.py` helper directly consumes `scenes[].image` and `scenes[].duration_seconds`; the extended fields provide semantic, stylistic, and character traceability for the agent and user. Paths are absolute or relative to this JSON file. Scene start is the sum of preceding durations. Adjust the final duration to make the sum equal probed audio duration D within 0.15s. Verify each subidea has saved art and the sequence covers each intended occurrence. Do not describe this approximate timeline as subtitles or karaoke.

To opt in for the example character, add `"avatar_image": "avatars/traveler.png"` to that character after placing the supplied file beside the storyboard. Omit the field to retain text-only character generation. The `skills/dual-image-pipeline/scripts/generate.py` scheduler routes avatar-linked assets only to verified `supports_references:true` routes; configured CLI adapters must actually pass the references to their image tool. Unsupported routes remain ineligible for those assets.
