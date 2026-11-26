# Moment scoring

Use this when deciding what to record and how much each kind of moment is worth.

## What counts as a moment

A moment is a change a player would tell a friend about. Good sources, in rough order of value:

| Type (suggested id) | Examples | Default weight |
|---|---|---|
| `legendary` | the rarest thing in the world happening at all | 1.5 |
| `rareCatch` / `discovery` | rare item, creature, place or secret found | 1.2 / 1.1 |
| `rescue` | one character saving or helping another | 1.0 |
| `record` | personal best: longest, biggest, fastest, highest | 1.0 |
| `levelClear` | finishing a level, quest or day goal | 0.9 |
| `stunt` | a jump, a slide, a combo, a trick | 0.8 |
| `social` | characters meeting, celebrating, sharing | 0.7 |
| `scenic` | a lovely view with no event (sunset, storm) | 0.5 |
| `catch` | everyday success | 0.4 |

Rename or add types freely; pass `weights` to `KeepsakeLens.create`.

## Fields that move the score

- `rarity` 0–1: how unusual this is in the world (1 = once in many sessions). Tie it to real odds when the game has them.
- `intensity` 0–1: how dramatic it was (a near-miss, a big wave, a heavy fish, a long fall).
- `first`: true the first time this kind of thing ever happens for the player. Firsts get +0.35.
- `subjects`: everyone who should be in the frame. Two or more characters add up to +0.36.
- golden-hour light: pass `goldenHour: t => 0..1` so evening moments get a small bonus.
- variety: types picked on the last three days score lower, so the album doesn't fill with one kind of card. Call `lens.commit(picked)` after showing a keepsake.

## When to record

Record at the **peak frame**, where the picture is best:

- a catch → when the fish clears the water, not when the line bites
- a rescue → when the rescuer is beside the swimmer on the sand, checking on them
- a ride or stunt → mid-ride, at speed, not at the start
- a discovery → when the thing is lifted or opened

If the peak happens later than the logic event, record the moment when the event happens and keep a per-type "peak" rule in the staging step (advance to the peak before framing).

## Keep the log small

The log keeps at most `maxMoments` (default 200) and drops the weakest when full. Clear it at the start of each in-world day (`lens.clear()`), or keep a day's worth and store only the picked keepsake in the album.

## Never invent

Moments come from the world's own logic. Don't add a moment because it would make a nicer card, and don't upgrade facts (a 2 kg fish stays 2 kg). Captions use only `facts` that were logged.
