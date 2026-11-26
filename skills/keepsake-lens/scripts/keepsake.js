/*
 * keepsake.js — moment log, keepsake picker and face-on camera framing.
 * Engine-agnostic, dependency-free. Works as a <script>, an ES import (via the global) or in Node (module.exports).
 *
 *   const lens = KeepsakeLens.create({ weights: { rescue: 1.0, rareCatch: 1.2 } });
 *   lens.record({ type: 'rescue', t: 812.4, subjects: ['lena', 'tom'], at: [x, y, z], rarity: 0.4, intensity: 0.8,
 *                 facts: { rescuer: 'Lena', swimmer: 'Old Tom', place: 'the beach' } });
 *   const best = lens.pickBest({ since: dayStart });           // -> { moment, score, runnerUp }
 *   const shot = KeepsakeLens.faceOnCamera({ p: [x, y, z], q: [qx, qy, qz, qw] }, { distance: 0.3, isValid });
 *   const text = KeepsakeLens.caption(best.moment, templates);  // facts only, never invented
 */
(function (root) {
  'use strict';

  // ---- small vector helpers -------------------------------------------------------------------
  const v3 = {
    add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
    sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
    scale: (a, s) => [a[0] * s, a[1] * s, a[2] * s],
    len: a => Math.hypot(a[0], a[1], a[2]),
    norm: a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; },
  };
  // rotate vector v by unit quaternion q = [x, y, z, w]
  function rotate(q, v) {
    const [x, y, z, w] = q;
    const cx = y * v[2] - z * v[1] + w * v[0], cy = z * v[0] - x * v[2] + w * v[1], cz = x * v[1] - y * v[0] + w * v[2];
    return [v[0] + 2 * (y * cz - z * cy), v[1] + 2 * (z * cx - x * cz), v[2] + 2 * (x * cy - y * cx)];
  }

  // ---- defaults ---------------------------------------------------------------------------------
  const DEFAULT_WEIGHTS = {
    // how much a moment of this type is worth before rarity, firsts and people are considered
    legendary: 1.5, rareCatch: 1.2, rescue: 1.0, record: 1.0, discovery: 1.1, levelClear: 0.9,
    stunt: 0.8, social: 0.7, scenic: 0.5, catch: 0.4, default: 0.5,
  };

  function create(options = {}) {
    const weights = Object.assign({}, DEFAULT_WEIGHTS, options.weights || {});
    const maxMoments = options.maxMoments || 200;           // keep the log small; old low-score moments fall off
    const goldenHour = options.goldenHour || null;          // (t) => 0..1 how "golden" the light is at world time t
    const moments = [];
    let history = [];                                       // types picked on previous days, newest last

    function score(m, ctx = {}) {
      const base = weights[m.type] !== undefined ? weights[m.type] : weights.default;
      let s = base * (0.6 + 0.8 * clamp01(m.rarity)) * (0.7 + 0.6 * clamp01(m.intensity));
      if (m.first) s += 0.35;                                          // first time ever is always special
      const people = (m.subjects || []).length;
      if (people >= 2) s += 0.12 * Math.min(3, people - 1);            // moments with several characters read better
      if (goldenHour) s += 0.15 * clamp01(goldenHour(m.t));            // a little bonus for lovely light
      const recent = history.slice(-3);
      if (recent.includes(m.type)) s *= 0.75 - 0.1 * (recent.lastIndexOf(m.type) === recent.length - 1 ? 1 : 0);   // variety across days
      if (ctx.avoidTypes && ctx.avoidTypes.includes(m.type)) s *= 0.5;
      return s;
    }

    function record(m) {
      if (!m || !m.type) throw new Error('KeepsakeLens.record: a moment needs a type');
      const entry = Object.assign({ id: 'm' + (moments.length + 1) + '-' + Math.round((m.t || 0) * 10), t: 0, subjects: [], rarity: 0, intensity: 0.5, first: false, facts: {} }, m);
      moments.push(entry);
      if (moments.length > maxMoments) {                                // drop the weakest, not the oldest
        let worst = 0, ws = Infinity;
        for (let i = 0; i < moments.length; i++) { const s = score(moments[i]); if (s < ws) { ws = s; worst = i; } }
        moments.splice(worst, 1);
      }
      return entry;
    }

    function pickBest(ctx = {}) {
      const pool = moments.filter(m => (ctx.since === undefined || m.t >= ctx.since) && (ctx.until === undefined || m.t <= ctx.until));
      if (!pool.length) return null;
      const ranked = pool.map(m => ({ moment: m, score: score(m, ctx) })).sort((a, b) => b.score - a.score);
      const best = ranked[0];
      // runner-up of a different type when possible, so the player has a real alternative
      const runnerUp = ranked.slice(1).find(r => r.moment.type !== best.moment.type) || ranked[1] || null;
      return { moment: best.moment, score: best.score, runnerUp: runnerUp ? runnerUp.moment : null, ranked };
    }

    function commit(picked) { if (picked && picked.moment) { history.push(picked.moment.type); history = history.slice(-10); } }

    return {
      record, pickBest, commit, score,
      get moments() { return moments.slice(); },
      clear(since) { for (let i = moments.length - 1; i >= 0; i--) if (since === undefined || moments[i].t >= since) moments.splice(i, 1); },
      toJSON() { return { moments: moments.slice(), history: history.slice() }; },
      load(data) { moments.length = 0; (data && data.moments || []).forEach(m => moments.push(m)); history = (data && data.history || []).slice(); },
    };
  }

  // ---- face-on framing ----------------------------------------------------------------------------
  /*
   * pose: { p: [x,y,z], q?: [x,y,z,w], yaw?: radians }   (yaw = heading in the x–z plane, measured with atan2(z, x))
   * opts: {
   *   distance: 0.3, pitch: 0.2 (radians above horizontal, negative = from below), lift: 0 (aim point above p),
   *   offset: 0.45 (three-quarter turn), frontAxis: [1,0,0] (the model's "forward" in local space),
   *   useHeadAxis: false (use headAxis instead, for lying / swimming subjects), headAxis: [0,1,0],
   *   up: [0,1,0], isValid: (position) => true, tryOffsets: [0.45, -0.45, 0.9, -0.9, 0, 1.3, -1.3], tryDistances: [1, 0.75, 0.55],
   *   include: [[x,y,z], …] (others who must be in the shot: aims at the group's centre and backs off to fit them),
   *   avoid: [[x,y,z], …] (bystanders to keep out of frame), avoidRadius: 0.05 (their size, in world units), fov: 0.8 (vertical, radians — match your camera), aspect: 1.5, margin: 1.35
   * }
   * returns { position, target, yaw, pitch, distance, offset, front, bystanders } or null if no valid shot exists.
   * The orbit `yaw` uses the convention camera = target + distance * (sin yaw, ., cos yaw); convert if your camera differs.
   */
  function faceOnCamera(pose, opts = {}) {
    const distance = opts.distance !== undefined ? opts.distance : 0.3;
    const pitch = opts.pitch !== undefined ? opts.pitch : 0.2;
    const lift = opts.lift || 0;
    const isValid = opts.isValid || (() => true);
    let f;
    if (pose.q) f = rotate(pose.q, opts.useHeadAxis ? (opts.headAxis || [0, 1, 0]) : (opts.frontAxis || [1, 0, 0]));
    else f = [Math.cos(pose.yaw || 0), 0, Math.sin(pose.yaw || 0)];
    const heading = Math.atan2(f[2], f[0]);                     // where the face points, in the x–z plane
    // frame a group: aim at the middle of the subject and everyone in `include`, and back off until they all fit
    const pts = [pose.p].concat(opts.include || []);
    const c = pts.reduce((acc, q) => [acc[0] + q[0] / pts.length, acc[1] + q[1] / pts.length, acc[2] + q[2] / pts.length], [0, 0, 0]);
    const target = [c[0], c[1] + lift, c[2]];
    const fov = opts.fov || 0.8, aspect = opts.aspect || 1.5, margin = opts.margin || 1.35;
    const spread = Math.max(0.0001, ...pts.map(q => Math.hypot(q[0] - c[0], q[2] - c[2]))), tall = Math.max(0, ...pts.map(q => Math.abs(q[1] - c[1])));
    const halfH = Math.atan(Math.tan(fov / 2) * aspect);
    const fitDist = pts.length > 1 ? Math.max(spread / Math.tan(halfH), tall / Math.tan(fov / 2)) * margin : 0;
    const baseDist = Math.max(distance, fitDist);
    // bystanders to keep out of the picture: a candidate that would show any of them is skipped (or, if all do, the one showing fewest wins)
    const avoid = opts.avoid || [];
    const shows = (position) => avoid.filter(a2 => {
      const v = v3.sub(a2, position), d = v3.len(v); if (d > baseDist * 4) return false;
      const fwd = v3.norm(v3.sub(target, position)), n = v3.norm(v);
      const right = v3.norm([fwd[2], 0, -fwd[0]]), up = [0, 1, 0];
      const x = n[0] * right[0] + n[2] * right[2], y = n[1] * up[1] - fwd[1] * 0, z = n[0] * fwd[0] + n[1] * fwd[1] + n[2] * fwd[2];
      const pad = Math.atan((opts.avoidRadius !== undefined ? opts.avoidRadius : 0.05) / Math.max(d, 1e-6));   // a body has size: count partial appearances at the frame edge too
      return z > 0 && Math.abs(Math.atan2(x, z)) < halfH + pad && Math.abs(Math.atan2(n[1] - fwd[1], z)) < fov / 2 + pad;
    }).length;
    let fallback = null;
    const offsets = opts.tryOffsets || [opts.offset !== undefined ? opts.offset : 0.45, -(opts.offset !== undefined ? opts.offset : 0.45), 0.9, -0.9, 0, 1.3, -1.3];
    // try each side offset at the requested distance, then come in closer (near walls or the edge of the world)
    for (const k of opts.tryDistances || [1, 0.75, 0.55]) {
      const d = baseDist * k;
      for (const off of offsets) {
        const a = heading + off, cp = Math.cos(pitch);
        const position = [target[0] + Math.cos(a) * cp * d, target[1] + Math.sin(pitch) * d, target[2] + Math.sin(a) * cp * d];
        if (!isValid(position, target)) continue;
        // orbit yaw for cameras placed at target + d * (sin yaw, ., cos yaw):  sin yaw = cos a, cos yaw = sin a
        const shot = { position, target, yaw: Math.PI / 2 - a, pitch, distance: d, offset: off, front: f, bystanders: shows(position) };
        if (!shot.bystanders) return shot;
        if (!fallback || shot.bystanders < fallback.bystanders) fallback = shot;
      }
    }
    return fallback;   // null if no face-on shot is possible here: pick another moment or the runner-up
  }

  // is the face actually turned towards the camera? (dot > 0.25 ≈ within ~75°)
  function facesCamera(pose, camPos, opts = {}) {
    const f = pose.q ? rotate(pose.q, opts.useHeadAxis ? (opts.headAxis || [0, 1, 0]) : (opts.frontAxis || [1, 0, 0])) : [Math.cos(pose.yaw || 0), 0, Math.sin(pose.yaw || 0)];
    const toCam = v3.norm(v3.sub(camPos, pose.p));
    const fh = v3.norm([f[0], 0, f[2]]), th = v3.norm([toCam[0], 0, toCam[2]]);
    return fh[0] * th[0] + fh[2] * th[2] > (opts.minDot !== undefined ? opts.minDot : 0.25);
  }

  // ---- captions from facts only -------------------------------------------------------------------
  /*
   * templates: { [type]: { title: 'Lena to the rescue', note: '{swimmer} got into trouble; {rescuer} towed them in and checked them over.' } }
   * Placeholders that have no fact are removed together with their clause, so nothing is invented.
   */
  function caption(m, templates = {}, extra = {}) {
    const tpl = templates[m.type] || templates.default || { title: titleCase(m.type), note: '' };
    const facts = Object.assign({}, m.facts || {}, extra);
    const fill = s => (s || '').split(/(?<=[.;!?])\s+/).map(clause => {
      let missing = false;
      const out = clause.replace(/\{(\w+)\}/g, (_, k) => { if (facts[k] === undefined || facts[k] === null || facts[k] === '') { missing = true; return ''; } return String(facts[k]); });
      return missing ? '' : out;
    }).filter(Boolean).join(' ').trim();
    return { title: fill(tpl.title) || titleCase(m.type), note: fill(tpl.note), meta: fill(tpl.meta || '') };
  }

  function clamp01(x) { return Math.max(0, Math.min(1, +x || 0)); }
  function titleCase(s) { return String(s).replace(/([A-Z])/g, ' $1').replace(/^./, c => c.toUpperCase()).trim(); }

  const api = { create, faceOnCamera, facesCamera, caption, rotate, DEFAULT_WEIGHTS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.KeepsakeLens = api;
})(typeof window !== 'undefined' ? window : globalThis);
