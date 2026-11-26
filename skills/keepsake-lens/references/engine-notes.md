# Engine notes and headless capture

Use this when wiring Keepsake Lens into a specific engine, or when captures come out black, blank or early.

## Getting a pose (position + orientation)

| Engine | Position | Orientation | Forward axis (usual) |
|---|---|---|---|
| three.js | `obj.getWorldPosition(v)` | `obj.getWorldQuaternion(q)` → `[q.x,q.y,q.z,q.w]` | model-dependent; often `[0,0,1]` |
| Babylon.js | `mesh.getAbsolutePosition()` | `mesh.absoluteRotationQuaternion` | `[0,0,1]` |
| PlayCanvas | `entity.getPosition()` | `entity.getRotation()` | `[0,0,-1]` |
| raw WebGPU / WebGL | your own transform arrays | your own quaternion or yaw | whatever your meshes use |

Babylon is left-handed: if shots land behind the subject, negate the z of the forward axis.

## Setting the camera

- look-at cameras: use `shot.position` and `shot.target`.
- orbit cameras: `shot.yaw`, `shot.pitch`, `shot.distance` assume camera = target + d·(sin yaw, ·, cos yaw). If your orbit uses (cos yaw, ·, sin yaw), use `Math.PI / 2 - shot.yaw`.
- pause the simulation before capturing so the peak frame is held, then render two or three frames.

## Capturing inside the app (for shipping)

```js
renderer.render(scene, camera);                 // make sure the frame you want is drawn
canvas.toBlob(blob => album.add(blob), 'image/png');
```

- WebGL: create the context with `preserveDrawingBuffer: true`, or capture in the same task right after rendering.
- WebGPU: the canvas texture is only valid for the current frame — call `toBlob`/`toDataURL` right after submitting, or render into an offscreen texture and copy it to a 2D canvas.
- Hide the UI with a class on `<body>` while capturing, then restore it.

## Capturing headlessly (previews, tests, docs) with `scripts/capture.mjs`

Known pitfalls, all hit in practice:

- **WebGPU hidden in headless Chromium.** The script passes `--enable-unsafe-webgpu` and routes WebGPU through SwiftShader (software Vulkan), so it works without a GPU.
- **Black canvas in the screenshot.** Headless Chromium on Linux/Windows renders WebGPU but often doesn't present the canvas to the screenshot. Fixes: give the app an offscreen/test mode that renders to a texture and copies it into a 2D canvas (pass it with `--query`), or run with `--headed` under a virtual display (xvfb).
- **Start-up undoes the stage.** Large or slow pages may still be setting their first camera when `--ready` turns true. Pass `--settle 10000` (ms) so staging happens after start-up.
- **4K on a software GPU is slow.** A 3840×2560 frame can take a minute or more with SwiftShader; use `--wait 120000`–`180000`, run captures one at a time, and expect several minutes each. On a real GPU (`--headed`) it is much faster.
- **Screenshot too early.** WebGPU apps start asynchronously. Pass `--ready "window.app && app.ready"` and a `--wait` of 1–3 s so several frames render.
- **Software GPU is slow.** Keep captures at 1200×800 or so; don't run timing-sensitive tests alongside captures.
- **Errors during the moment.** The script prints page errors and exits with code 2 — a keepsake of a broken frame is worse than none. Fix the error, then re-capture.
- **The default view leaks in.** If the screenshot shows the default camera, the staging script threw before setting the camera. Check its errors.

## Review

`scripts/contact_sheet.py` flags BLANK? (no variation: black canvas, lost device) and BACKDROP? (mostly one flat colour: camera outside the world). Re-shoot anything flagged.
