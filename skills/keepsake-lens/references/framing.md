# Framing: faces, not backs

Use this before choosing camera angles. It encodes the mistakes that make keepsake shots look wrong.

## The rule

The camera goes **in front of the subject**, turned a little to one side (a three-quarter view), so the face and body read clearly. Work out "in front" from the subject's **orientation**, never from guesswork or from where the camera happened to be.

```js
const pose = { p: entity.position, q: entity.quaternion };      // or { p, yaw }
const shot = KeepsakeLens.faceOnCamera(pose, {
  distance: 0.3, pitch: 0.2, lift: 0.03, offset: 0.45,
  frontAxis: [1, 0, 0],                                          // your models' forward axis (+x, -z in three.js, +z in Babylon…)
  isValid: pos => insideWorld(pos) && !insideWater(pos) && clearLine(pos, pose.p),
});
camera.position.set(...shot.position); camera.lookAt(...shot.target);
```

Check with `KeepsakeLens.facesCamera(pose, camPos)` after any manual tweak.

## Know your forward axis

Engines and models differ: three.js models usually face +z or −z, Babylon +z, many hand-built models +x. Get it once from the model (look at where the face or nose is) and pass it as `frontAxis`. If shots consistently show backs, the axis is flipped.

## Per-pose adjustments

| Subject | What to do |
|---|---|
| standing, walking | offset ±0.45, pitch 0.1–0.2, lift to chest height |
| sitting or riding (slide, kayak, board) | in front and slightly below the direction of travel, pitch 0.25–0.35 |
| bent over or kneeling (helping someone) | lower the pitch (0.05–0.15) so the face is visible under a hat brim; include the person they help in the foreground |
| lying down, swimming face-down | use `useHeadAxis: true` and shoot from in front of the head, near the surface |
| moving fast | frame ahead of them, with space in the direction they're going |
| group (rescuer + rescued, friends) | pass the others in `include`; the camera aims at the group's centre and backs off to fit everyone, with all of each person visible |

## Shots the renderer can't make

Reject them in `isValid` so the helper tries another offset:

- **outside the world** — beyond the scene's bounds the background is a flat backdrop. Keep the camera inside, or aim so the world fills the frame.
- **inside water, walls or terrain** — many renderers draw nothing useful from inside a volume (no water surface from below, back-face-culled walls). Shoot from above the surface instead.
- **behind scenery** — cast a ray from camera to subject; if it hits something solid first, try another offset.
- **too close** — near-plane clipping cuts faces. Keep distance at least ~3× the subject's head size.

## Bystanders

Busy scenes put other characters right next to the moment (sunbathers beside a rescue, a crowd at a finish line). Pass their positions in `avoid`, with `avoidRadius` set to about their size (a lying body is long; count partial appearances at the frame edge). Add tall props that cut through pictures (parasol poles, lamp posts) as two points, low and high.

If every angle still shows someone, the helper returns the least crowded shot with `bystanders > 0`. Then: choose a different moment, try the other side (`tryOffsets` with negative values first), frame tighter, or crop with the postcard's `focus`/`zoom`. Don't remove people from a real keepsake; for a staged documentation sample, say that it was staged.

Report what the helper chose from a staging script with `console.log('keepsake: ' + JSON.stringify(shot))` — `capture.mjs` prints those lines.

## Light

Prefer moments with good light (golden hour) and keep the sun roughly behind the camera or to the side, so faces aren't in shadow. If a face is dark, rotate the offset towards the sun.

## Composition

- subject a little off-centre (rule of thirds), facing into the frame
- horizon level unless the moment is chaotic
- leave the top-left area fairly calm: the postcard puts its tag there
- crop is 1380×760 on the card (about 16:9): stage at that aspect or wider
