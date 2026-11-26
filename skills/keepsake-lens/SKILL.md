---
name: keepsake-lens
description: Turns the best moment of a session in a 3D or canvas world (a game, simulation, diorama or interactive scene) into a keepsake postcard — it logs real in-world moments, scores them, picks the day's best, frames a camera shot that faces the characters (not their backs), captures the canvas with the UI hidden, and composes a captioned postcard with stamp and postmark. Use this skill whenever someone wants a daily recap, highlight, photo mode, postcard, "moment of the day", end-of-level or end-of-session snapshot, shareable screenshot, album or memory feature for a Three.js, Babylon.js, PlayCanvas, WebGPU, WebGL or canvas project, or asks to make screenshots of characters "facing the camera" — even if they never say "postcard".
---

# Keepsake Lens

Make the one picture from a session that a player would actually keep: the right moment, framed so you can see faces, captioned with what really happened.

The skill has four stages. Each has a script or a reference file; read the reference only when you reach that stage.

1. **Log moments** — record notable events from the world's own logic (`scripts/keepsake.js`, `references/moment-scoring.md`)
2. **Pick the keepsake** — score and choose, with variety across days (`scripts/keepsake.js`)
3. **Frame and capture** — a face-on, valid camera shot with the UI hidden (`scripts/keepsake.js`, `scripts/capture.mjs`, `references/framing.md`, `references/engine-notes.md`)
4. **Compose the postcard** — photo, caption, stamp, postmark (`scripts/compose_postcard.py`, `references/postcard-style.md`)

Then review with `scripts/contact_sheet.py` before showing anyone.

## Stage 1 — Log moments from the world, not from guesses

A keepsake is only honest if it shows something that happened. So moments come from hooks in the world's logic (a catch landed, a rescue finished, a level cleared, a record broken), never from inventing events after the fact.

- Find the places in the code where meaningful things are decided (state machine transitions, event emitters, achievement checks). Add one `lens.record({...})` call at each.
- Each moment carries: `type`, `t` (world time), `subjects` (entity ids to frame), `at` (world position), `rarity` 0–1, `intensity` 0–1, `first` (first time ever), and `facts` (plain values the caption may use: names, counts, weights, places).
- Record at the peak, not the start: the frame where the fish breaks the surface, the surfer mid-wave, the rescuer kneeling beside the swimmer. Keep a short `snapshot` callback per type if the peak is later than the event.

Read `references/moment-scoring.md` for weights, rarity, firsts and how to keep the log small.

## Stage 2 — Pick the keepsake

Call `lens.pickBest({ since, avoidTypes })` at the trigger (dusk, end of level, end of session, on demand). It scores every moment, boosts firsts, rare things and moments with several characters, gives golden-hour light a small bonus, and avoids repeating yesterday's type so the album stays varied. Return the top moment plus one runner-up so the player can swap.

## Stage 3 — Frame faces, then capture

Most "bad screenshots" are the camera behind the character. Use `KeepsakeLens.faceOnCamera(pose, opts)`:

- It reads the subject's **facing direction from its orientation** (quaternion or yaw), places the camera **in front** of them with a three-quarter side offset (default 0.45 rad), at a chosen distance, pitch and lift, and returns both `{position, target}` (look-at cameras) and `{yaw, pitch, distance}` (orbit cameras).
- Pass `isValid(position)` so it rejects shots the renderer can't make: outside the world bounds, inside water or walls, behind scenery. It tries other offsets automatically.
- When a moment has several people (a rescuer and the person rescued), pass the others in `include`: the camera aims at the middle of the group and backs off until everyone fits, so the shot is centred on them.
- Pass nearby bystanders in `avoid` (with `avoidRadius` for their size) so the shot leaves them out. If every angle shows someone, the helper returns the shot showing fewest and reports `bystanders`; then pick another moment, or crop with the postcard's `focus`/`zoom`.
- For subjects lying down or swimming face-down, use the **head axis** instead of the front axis and shoot at the surface from in front (`useHeadAxis: true`). For someone bent over, lower the pitch so the face is under the brim.
- Match `fov` to your camera, or group shots come out too tight.

Capture inside the app for shipping (render a frame, then `canvas.toBlob`). For previews, tests and docs, use `scripts/capture.mjs` (Playwright): it serves the project, enables WebGPU headlessly, runs a staging script that sets the moment and camera, hides every element except the canvas, waits for frames, and saves the PNG.

Read `references/framing.md` before choosing angles, and `references/engine-notes.md` for Three.js / Babylon / raw WebGPU hooks and headless pitfalls (black canvas, early screenshots, software GPU).

## Stage 4 — Compose the postcard

`python3 scripts/compose_postcard.py spec.json` builds a card laid out like a real postcard: 1800×1200 by default, or 3840×2560 (4K) with `"scale": 2.1333` — capture the photo at 4K too (`capture.mjs --size 3840x2560`) so it is scaled down, never up. On the left: the photo (graded to the time of day, cropped around the subject with `focus`/`zoom`), then a small tag, an italic headline, a date line and a short message. A divider runs down the middle. On the right: a "POST CARD" heading, a stamp in the world's colours with a postmark over its corner, and handwritten address lines. Give every card something of its own so an album never looks samey: a `motif` (surf, slide, rescue, reef, star) drives the stamp illustration and a round corner sticker with a short `badge` ("Personal Best", "Hero", "+2 Species"), and an `accent` colour runs through the tag, sticker, tape and kicker. Headings and address lines get a capital on every word. See `assets/example-spec.json`.

Write the caption from `facts` only. If a fact isn't logged, leave it out rather than inventing it. Read `references/postcard-style.md` for tone, length and layout rules.

## Review before showing

Run `python3 scripts/contact_sheet.py out/*.png -o sheet.png` and look at it. Check every shot for:

- faces visible (not backs, not hidden under a hat brim or behind props)
- the subjects centred, with all of each person visible (nobody cut in half)
- no stray bystanders, feet or poles poking into the frame
- no UI, panels, cursors or debug text
- not blank, not the backdrop outside the world (the sheet flags near-uniform images)
- caption matches what the picture shows

Re-shoot any that fail with a different offset, lower pitch or later peak frame. One honest, well-framed card beats four weak ones.

## Shipping it in the app

- Trigger once per in-world day or session end; show the card in a modal with "Keep" and "Share".
- Keep an album (IndexedDB or the app's save) of `{ id, moment, imageDataURL, caption }`, newest first, capped (e.g. 60).
- Never auto-post anywhere; sharing is the player's choice.
- Label any example or mock-up card as such when presenting it before the feature exists.
