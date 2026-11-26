# Postcard style

Use this when writing captions and choosing the card's look.

## Words

- **Title** (2–5 words): the moment as a headline, warm and specific. "Lena to the rescue", "Kai's longest ride", "A legendary tuna". No exclamation spam; one is fine for joy.
- **Meta line** (caps, short): `DAY 4 · 18:05 · CHOPPY SEA` — day, time, and one condition or place, all from the world state.
- **Note** (one or two sentences, ≤ 25 words): what happened, who was there, one detail that makes it theirs. Facts only — names, counts, weights, places that were logged.
- **Tag** (optional, ≤ 3 words): why it was picked — "Moment of the day", "First ever", "New record", "Brave moment".
- **Badge** (≤ 2 words, on the corner sticker): the card's one stand-out fact — "Personal Best", "3 Rides", "Hero", "+2 Species". From logged facts only.
- **Capitals**: headings and address lines get a capital on every word ("Lena To The Rescue"); the message stays a normal sentence so it reads easily.
- **Address lines** (four): a playful addressee and the place, e.g. "To: Future Me", "C/O The Keepsake Box", the place, the day. The kicker under POST CARD defaults to "Wish You Were Here".

Write templates per moment type and fill them with `KeepsakeLens.caption(moment, templates)`. Clauses whose facts are missing are dropped, so a template can be rich without ever inventing anything.

## Look

A 3:2 card, like a 6×4 postcard, on a simple grid:

- **left column** — the photo in a white border with a soft shadow, cropped around the subjects (`focus`, `zoom`); under it, on one baseline rhythm: a small spaced-capitals tag in the accent colour, the italic serif headline, a spaced-capitals date line, and the message (up to three lines)
- **divider** — a thin rule down the middle, like the back of a real postcard
- **right column** — "POST CARD" in spaced capitals with a small kicker line under it; the stamp top-right in the world's own colours with a one-word label; the postmark (world name, day, year) overlapping the stamp's corner with wavy cancellation lines; four ruled address lines in a handwritten-style italic, lined up with the message block
- **one thing of its own per card**: `motif` sets the stamp illustration (surfboard, slide, lifebuoy, fish, star) and the corner sticker's icon; `accent` colours the tag, sticker, washi tape and kicker. Vary them by moment type so every card in an album stands out.
- **sharpness**: capture at the card's resolution or above (4K captures for `scale` 2.1333) so the photo is only ever scaled down; the composer warns if it has to upscale.
- photo graded to the time of day: `warmth` 0.8–1 at golden hour, 0.2–0.4 midday, −0.2 underwater or at night
- paper-coloured card with light grain and a thin rounded edge; a small footer naming the feature

Keep the layout consistent across a whole album; vary only photo, words, stamp colours and warmth.

## Honesty

- If you present cards before the feature exists, say they are mock-ups built from real captures.
- Never caption something the picture doesn't show, and never show a picture from a different moment than the caption describes.
