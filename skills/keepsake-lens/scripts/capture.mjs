#!/usr/bin/env node
/*
 * capture.mjs — capture a clean keepsake frame from a WebGPU / WebGL / canvas page with Playwright.
 *
 *   node capture.mjs --root ./my-game --page index.html --stage stage.js --out shot.png \
 *        [--query offscreen] [--size 1200x800] [--settle 0] [--wait 2500] [--ready "window.app && app.ready"] [--keep "#hud .title"] [--headed]
 *
 * --root    folder to serve (the page and its assets)          --page   page inside the root (default index.html)
 * --stage   a JS file evaluated in the page once it is ready. It should put the world in the moment
 *           (advance time, trigger the event, pause) and set the camera — e.g. with KeepsakeLens.faceOnCamera.
 *           It may be async. The KeepsakeLens library is injected first as window.KeepsakeLens.
 * --ready   a JS expression that is true once the app has started (default: a canvas exists)
 * --keep    CSS selectors to leave visible; everything else that isn't a canvas (or contains one) is hidden
 * --settle  ms to wait after --ready and before staging, so the app's own start-up (first camera, resize) can't undo the stage
 * --wait    ms to wait after staging so several frames render (WebGPU apps start asynchronously)
 * --query   extra query string for the page (e.g. an offscreen/test mode)
 *
 * Exit code 0 on success; 2 if the page logged errors (the frame is still saved); 3 if the staging script threw (nothing saved).
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith('--')) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]);
  return acc;
}, []));
const root = path.resolve(args.root || '.');
const pageName = args.page || 'index.html';
const out = path.resolve(args.out || 'keepsake.png');
const [W, H] = String(args.size || '1200x800').split('x').map(Number);
const wait = +(args.wait || 2500);
const here = path.dirname(fileURLToPath(import.meta.url));

// Playwright: from PLAYWRIGHT_PATH, the project, or a global install
async function loadPlaywright() {
  const tries = [process.env.PLAYWRIGHT_PATH, 'playwright', 'playwright-core'].filter(Boolean);
  for (const t of tries) {
    try { return await import(t.endsWith('.mjs') || t.startsWith('/') ? pathToFileURL(t).href : t); } catch (e) { /* try next */ }
  }
  console.error('Playwright not found. Install it (npm i -D playwright && npx playwright install chromium) or set PLAYWRIGHT_PATH to its index.mjs.');
  process.exit(1);
}
const { chromium } = await loadPlaywright();

const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.wasm': 'application/wasm', '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(root)) { res.writeHead(403); return res.end(); }
  fs.readFile(p, (err, data) => {
    if (err) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); res.end(data);
  });
}).listen(0);
const port = server.address().port;

// WebGPU in headless Chromium: enable it and route it through SwiftShader so it works without a GPU (CI, containers).
const gpuArgs = ['--enable-unsafe-webgpu', '--enable-features=Vulkan', '--use-angle=vulkan', '--use-vulkan=swiftshader', '--use-webgpu-adapter=swiftshader', '--disable-vulkan-surface', '--ignore-gpu-blocklist'];
const browser = await chromium.launch({ headless: !args.headed, args: gpuArgs });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); else if (m.text().startsWith('keepsake:')) console.log(m.text()); });   // staging scripts can report with console.log('keepsake: …')

await page.addInitScript({ path: path.join(here, 'keepsake.js') });
await page.goto(`http://localhost:${port}/${pageName}${args.query ? '?' + args.query : ''}`);
await page.waitForFunction(args.ready || "!!document.querySelector('canvas')", null, { timeout: 60000 });

if (args.settle) await page.waitForTimeout(+args.settle);   // let the app finish its own start-up (initial camera, resize) before staging
if (args.stage) {
  const stage = fs.readFileSync(path.resolve(args.stage), 'utf8');
  try {
    await page.evaluate(async src => { const fn = new Function('return (async () => {' + src + '\n})()'); await fn(); }, stage);
  } catch (e) {
    console.error('staging script failed: ' + String(e.message || e).split('\n')[0]);
    await browser.close(); server.close(); process.exit(3);
  }
}

// hide everything that is not a canvas or an ancestor of one (or explicitly kept)
await page.evaluate(keep => {
  const canvases = [...document.querySelectorAll('canvas')];
  const kept = keep ? [...document.querySelectorAll(keep)] : [];
  document.querySelectorAll('body *').forEach(el => {
    if (canvases.some(c => el === c || el.contains(c))) return;
    if (kept.some(k => el === k || el.contains(k) || k.contains(el))) return;
    el.style.visibility = 'hidden';
  });
  document.body.style.cursor = 'none';
}, typeof args.keep === 'string' ? args.keep : '');

await page.waitForTimeout(wait);
await page.screenshot({ path: out });
await browser.close(); server.close();

if (errors.length) { console.error('page errors:\n  ' + errors.slice(0, 10).join('\n  ')); console.log(out); process.exit(2); }
console.log(out);
