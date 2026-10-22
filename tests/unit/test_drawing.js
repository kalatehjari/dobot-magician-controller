// Unit tests: kinematics/auto-calibration, image tracing, drawing commands, protocol (run: node tests/unit/test_drawing.js)
const fs = require('fs'), vm = require('vm');
const ctx = { console, Math, Float32Array, Float64Array, Int32Array, Uint8Array, Uint8ClampedArray, Array, Object, Number, JSON, Infinity, NaN, isFinite, Set, Map, Promise, DataView, setTimeout };
ctx.S = { limits: { minR: 170, maxR: 300, thMin: -87, thMax: 87, zMin: -80, zMax: 120, zUp: -60, zDown: -75 }, speed: { live: 100, accel: 100 }, gen: 0, model: null };
ctx.DEBUG = { frames: false }; ctx.log = () => {}; ctx.setConnected = () => {};
vm.createContext(ctx);
for (const f of ['part0_alarms.js', 'part1_protocol.js', 'part2_geometry.js', 'part31_kinematics.js', 'part32_trace.js']) vm.runInContext(fs.readFileSync(require('path').join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };

/* ---------- kinematics ---------- */
{
  const r = E(`(() => { const m = { dR: 59.7, dZ: 0 }; let worst = 0, n = 0;
    for (let j2 = 0; j2 <= 85; j2 += 1) for (let j3 = -10; j3 <= 85; j3 += 1) { if (!magJointsOk({ j2, j3 })) continue; n++;
      const p = magFK(j2, j3, m), s = magIK(p.r, p.z, m); worst = Math.max(worst, s ? Math.hypot(s.j2 - j2, s.j3 - j3) : 99); }
    return { worst, n }; })()`);
  t('IK inverts FK over the whole joint range', r.worst < 1e-9, `${r.n} poses, worst ${r.worst.toExponential(1)}°`);
  const b = E('reachBand({ dR: 59.7, dZ: 0 }, -60, -60, 0)');
  t('reach at z = −60 matches the joint-grid envelope (≈177–322 mm)', Math.abs(b.rIn - 177) <= 2 && Math.abs(b.rOut - 322) <= 2, `${b.rIn}–${b.rOut} mm`);
  // offsets recovered from simulated readings
  const v = E(`(() => { const m = { dR: 61, dZ: -12.5 };
    const poses = [[0, 20, 25], [15, 40, 30], [-30, 10, 45]].map(([j1, j2, j3]) => { const p = magFK(j2, j3, m); return { x: p.r * Math.cos(j1 * DEG), y: p.r * Math.sin(j1 * DEG), z: p.z, j1, j2, j3 }; });
    return validateModel(poses); })()`);
  t('auto-calibration recovers the tool offsets', v.ok && Math.abs(v.dR - 61) < 1e-6 && Math.abs(v.dZ + 12.5) < 1e-6, `dR ${v.dR.toFixed(2)} dZ ${v.dZ.toFixed(2)}`);
  const bad = E(`(() => { const m = { dR: 61, dZ: 0 };
    const poses = [[0, 20, 25], [0, 50, 10]].map(([j1, j2, j3]) => { const p = magFK(j2, j3 + j2, m); return { x: p.r, y: 0, z: p.z, j1, j2, j3 }; });
    return validateModel(poses); })()`);
  t('a joint-angle convention mismatch is detected', !bad.ok, `deviation ${bad.maxDev.toFixed(1)} mm`);
  const same = E(`validateModel([{ x: 240, y: 0, z: 60, j1: 0, j2: 20, j3: 25 }, { x: 240.2, y: 0, z: 60, j1: 0, j2: 20.1, j3: 25 }])`);
  t('two nearly identical poses are not accepted as proof', !same.ok);
  const L = E(`autoLimits({ dR: 59.7, dZ: 0 }, -75, { x: 239, y: 0, z: 65 })`);
  t('auto limits put the paper at Z min and keep the pen-up above it', L.zDown === -75 && L.zMin <= -75 && L.zUp > L.zDown, JSON.stringify({ minR: L.minR, maxR: L.maxR, zMin: L.zMin, zMax: L.zMax }));
  const ok = E(`(() => { const m = { dR: 59.7, dZ: 0 }, L = autoLimits(m, -75, { x: 239, y: 0, z: 65 }); let bad = 0;
    for (let r = L.minR; r <= L.maxR; r += 5) for (let th = L.thMin; th <= L.thMax; th += 10) for (let z = L.zMin; z <= L.zMax; z += 5)
      if (!magReachable(r * Math.cos(th * DEG), r * Math.sin(th * DEG), z, m, 0)) bad++;
    return bad; })()`);
  t('every point inside the auto limits is reachable', ok === 0, `${ok} unreachable samples`);
  const L0 = E(`autoLimits({ dR: 59.7, dZ: 0 }, null, { x: 239, y: 0, z: 65 })`);
  t('before the pen height is set, the arm stays 20 mm below home or higher', L0.zMin >= 44, `zMin ${L0.zMin}`);
  const rect = E(`(() => { const m = { dR: 59.7, dZ: 0 }, b = reachBand(m, -75.5, -59.5, 2); return { b, sq: fitRectForAspect(b.rIn, b.rOut, 6, 1), wide: fitRectForAspect(b.rIn, b.rOut, 6, 2.5) }; })()`);
  const inside = rc => [[-1, -1], [-1, 1], [1, -1], [1, 1]].every(([a, c]) => E(`magReachable(${rc.cx + a * rc.w / 2}, ${rc.cy + c * rc.h / 2}, -75, { dR: 59.7, dZ: 0 }, 1)`));
  t('drawing area fitted to a square drawing is reachable', inside(rect.sq), `${rect.sq.h.toFixed(0)} × ${rect.sq.w.toFixed(0)} mm`);
  t('drawing area fitted to a wide drawing is reachable and wide', inside(rect.wide) && rect.wide.h / rect.wide.w > 2.4, `${rect.wide.h.toFixed(0)} × ${rect.wide.w.toFixed(0)} mm`);
  E('S.model = { dR: 59.7, dZ: 0, ok: true }');
  const c1 = E('clampTarget(120, 0, -75)'), c2 = E('clampTarget(400, 0, -75)');
  t('height-aware clamp pulls too-close points out to the reach limit', Math.abs(c1.x - E('reachAt(S.model, -75)[0]') - 1) < 1e-6, `→ ${c1.x.toFixed(1)} mm`);
  t('height-aware clamp pulls too-far points in', c2.x < 320 && E(`magReachable(${c2.x}, 0, -75, S.model, 1)`), `→ ${c2.x.toFixed(1)} mm`);
}

/* ---------- drawing commands ---------- */
{
  const ops = [{ x: 200, y: 0, pen: false }, { x: 200, y: 0, pen: true }, { x: 210, y: 0, pen: true }, { x: 210.2, y: 0, pen: true }, { x: 220, y: 0, pen: true }, { x: 220, y: 0, pen: false }];
  ctx.__ops = ops;
  const cmds = E(`plotCommands(__ops, { zUp: -60, zDown: -75 }, { x: 180, y: 0, z: -75 }, { cp: true, speed: 30 })`);
  const kinds = cmds.map(c => c.kind === 'cp' ? 'cp' : 'L' + c.mode + (c.z === -60 ? 'up' : 'down'));
  t('pen lifts first, travels and lowers with straight moves, draws with CP', JSON.stringify(kinds) === JSON.stringify(['L2up', 'L2up', 'L2down', 'cp', 'cp', 'L2up']), kinds.join(' '));
  t('tiny drawing segments are merged', cmds.filter(c => c.kind === 'cp').length === 2);
  const prec = E(`plotCommands(__ops, { zUp: -60, zDown: -75 }, null, { cp: false })`);
  t('precise mode uses straight moves for drawing', prec.every(c => c.kind !== 'cp'));
  const o = E(`orientStrokes([[{ x: 0, y: 0 }, { x: 10, y: 0 }]], 1, false)[0]`);
  t('rotate 90° turns a horizontal line vertical', Math.abs(o[0].x - o[1].x) < 1e-9 && Math.abs(o[1].y - o[0].y - 10) < 1e-9);
  const mi = E(`orientStrokes([[{ x: 0, y: 0 }, { x: 10, y: 0 }]], 0, true)[0]`);
  t('mirror flips left and right', mi[0].x > mi[1].x);
}

/* ---------- protocol ---------- */
(async () => {
  const sent = [];
  const cap = { exchange: async f => { const fr = E('parseFrames')(f).frames[0]; sent.push(fr); const reply = fr.id === 246 ? E('u32bytes')(0) : E('u32bytes')(sent.length); return E('parseFrames')(E('encodeFrame')(fr.id, fr.ctrl, reply)).frames[0]; } };
  ctx.__cap = cap;
  const d = E('new Dobot(__cap)');
  await d.cp(200, 10, -70, 30); await d.home(); await d.setCPParams(150, 30, 150);
  t('CP move: id 91, 17-byte payload, absolute mode', sent[0].id === 91 && sent[0].ctrl === 3 && sent[0].params.length === 17 && sent[0].params[0] === 1);
  t('home: id 31 with the official 4-byte reserved value', sent[1].id === 31 && sent[1].params.length === 4);
  t('CP parameters: id 90, 13 bytes, non-real-time', sent[2].id === 90 && sent[2].params.length === 13 && sent[2].params[12] === 0);
  // flow control polls the queue only when the window is full
  sent.length = 0;
  ctx.__d2 = E('new Dobot(__cap)');
  ctx.S.gen = 0;
  const N = 40; ctx.__cmds = Array.from({ length: N }, (_, i) => ({ x: 200 + i, y: 0, z: -70, kind: 'cp', v: 30 }));
  // with a capturing IO the queue never executes, so make index replies track sends
  let execIdx = 0;
  const cap2 = { exchange: async f => { const fr = E('parseFrames')(f).frames[0]; sent.push(fr);
    if (fr.id === 91) { execIdx++; return E('parseFrames')(E('encodeFrame')(91, 3, E('u32bytes')(execIdx))).frames[0]; }
    if (fr.id === 246) return E('parseFrames')(E('encodeFrame')(246, 0, E('u32bytes')(execIdx))).frames[0];
    return E('parseFrames')(E('encodeFrame')(fr.id, fr.ctrl, [])).frames[0]; } };
  ctx.__cap2 = cap2; ctx.__d2 = E('new Dobot(__cap2)');
  await E('__d2.runQueue(__cmds, null, 20)');
  const polls = sent.filter(f => f.id === 246).length;
  t('queue progress is polled only when needed', polls <= 3, `${polls} polls for ${N} moves (was ${N + 1})`);
  // simulator raises the limit alarm for unreachable targets
  const sim = E('new SimIO()'); ctx.__sim = sim; ctx.__d3 = E('new Dobot(__sim)');
  await E('__d3.ptp(120, 0, -75, 0, 2)');
  const al = await E('__d3.alarms()');
  t('simulator raises limit alarm 18 for an unreachable point', al.includes(18), JSON.stringify(al));
  await E('__d3.clearAlarms()');
  const p0 = await E('__d3.pose()'); await E('__d3.home()'); const p1 = await E('__d3.pose()');
  ctx.__poses = [p0, p1];
  const vv = E('validateModel(__poses)');
  t('simulator readings validate the geometry model', vv.ok && Math.abs(vv.dR - 59.7) < 0.01, `dR ${vv.dR.toFixed(2)}, spread ${vv.spread.toFixed(1)}°`);
  traceTests();
  console.log(fails ? `${fails} FAILED` : 'ALL PASS');
  process.exitCode = fails ? 1 : 0;
})();

/* ---------- image tracing ---------- */
function makeImg(w, h, paint) {
  const data = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const v = paint(x, y); const i = (y * w + x) * 4; data[i] = data[i + 1] = data[i + 2] = v; data[i + 3] = 255; }
  return { data, w, h };
}
function traceTests() {
  ctx.__img = makeImg(200, 200, (x, y) => (Math.hypot(x - 100, y - 100) < 50 || Math.hypot(x - 170, y - 30) < 1.6 ? 20 : 235));
  const r = E(`traceImage(__img, { mode: 'outline', detail: 5, smooth: 3 })`);
  const area = Math.abs(E(`polyArea(${JSON.stringify(r.paths[0] ? r.paths[0].pts : [])})`));
  t('outline: filled circle → one closed path', r.paths.length === 1 && r.paths[0].closed, `${r.paths.length} path(s)`);
  t('outline: circle area within 3%', Math.abs(area - Math.PI * 2500) / (Math.PI * 2500) < 0.03, `${area.toFixed(0)} vs ${(Math.PI * 2500).toFixed(0)} px²`);
  t('auto threshold (Otsu) lands between ink and paper', r.threshold > 20 && r.threshold < 235, `${r.threshold}`);
  ctx.__line = makeImg(200, 200, (x, y) => (x >= 20 && x <= 180 && Math.abs(y - 100) <= 3 ? 10 : 245));
  const c = E(`traceImage(__line, { mode: 'centre', detail: 6, smooth: 4 })`);
  const len = c.paths.reduce((s, p) => s + E(`polyLength(${JSON.stringify(p.pts)})`), 0);
  t('centre line: thick bar → single stroke down the middle', c.paths.length === 1 && Math.abs(len - 160) < 14 && c.paths[0].pts.every(p => Math.abs(p.y - 100) < 1.5), `${c.paths.length} stroke, ${len.toFixed(0)} px`);
  ctx.__L = makeImg(200, 200, (x, y) => ((x >= 40 && x <= 46 && y >= 30 && y <= 170) || (y >= 164 && y <= 170 && x >= 40 && x <= 160) ? 10 : 245));
  const cl = E(`traceImage(__L, { mode: 'centre', detail: 6, smooth: 2 })`);
  const lenL = cl.paths.reduce((s, p) => s + E(`polyLength(${JSON.stringify(p.pts)})`), 0);
  t('centre line: "L" shape → strokes along both arms', Math.abs(lenL - 254) < 25 && cl.paths.length <= 3, `${cl.paths.length} stroke(s), ${lenL.toFixed(0)} px (≈254)`);
  ctx.__rect = makeImg(200, 150, (x, y) => (x >= 40 && x < 160 && y >= 30 && y < 120 ? 60 : 230));
  const e = E(`traceImage(__rect, { mode: 'edges', detail: 7, smooth: 2 })`);
  const lenE = e.paths.reduce((s, p) => s + E(`polyLength(${JSON.stringify(p.pts)})`), 0);
  t('edges: rectangle photo → its outline (≈420 px)', Math.abs(lenE - 420) / 420 < 0.15, `${e.paths.length} stroke(s), ${lenE.toFixed(0)} px`);
  ctx.__sq = makeImg(600, 600, (x, y) => (x >= 100 && x < 500 && y >= 100 && y < 500 ? 0 : 255));
  const corner = smooth => { const q = E(`traceImage(__sq, { mode: 'outline', detail: 8, smooth: ${smooth} })`); return Math.min(...q.paths[0].pts.map(p => Math.hypot(p.x - 99.5, p.y - 99.5))); };
  const sharp = corner(0), round = corner(10);
  t('curves = 0 keeps square corners; curves = 10 rounds them visibly', sharp < 1.6 && round - sharp > 6, `corner gap ${sharp.toFixed(1)} px vs ${round.toFixed(1)} px (600 px picture)`);
  const mid = corner(4);
  t('medium curves keep the corners of a square (only gentle bends are smoothed)', mid < 1.6, `corner gap ${mid.toFixed(1)} px`);
  ctx.__inv = makeImg(120, 120, (x, y) => (Math.hypot(x - 60, y - 60) < 30 ? 240 : 15));
  const iv = E(`traceImage(__inv, { mode: 'outline', detail: 5, smooth: 3, invert: true })`);
  t('invert: light shape on dark background', iv.paths.length === 1, `${iv.paths.length} path(s)`);
  const svg = E(`pathsToSvg(traceImage(__img, { mode: 'outline', detail: 5, smooth: 3 }).paths, 200, 200)`);
  t('SVG export has one <path> per stroke', (svg.match(/<path /g) || []).length === r.paths.length && svg.startsWith('<svg'));
  ctx.__dots = makeImg(600, 400, (x, y) => ([[100, 100], [200, 150], [300, 300], [450, 120]].some(([cx, cy]) => Math.hypot(x - cx, y - cy) < 5) ? 0 : 255));
  const dotArea = sm => E(`traceImage(__dots, { mode: 'outline', detail: 9, smooth: ${sm} })`).paths.map(p => Math.abs(E(`polyArea(${JSON.stringify(p.pts)})`)));
  const a0 = dotArea(0), a10 = dotArea(10);
  t('maximum curves keep small dots at their size', a10.length === 4 && a10.every((a, i) => a > 0.85 * a0[i]), `areas ${a0.map(a => a.toFixed(0)).join('/')} → ${a10.map(a => a.toFixed(0)).join('/')} px²`);
  const big = makeImg(600, 450, (x, y) => (((x / 40) | 0) + ((y / 40) | 0)) % 2 ? 30 : 220);
  ctx.__big = big; const t0 = Date.now(); E(`traceImage(__big, { mode: 'centre', detail: 6, smooth: 5 })`); const ms = Date.now() - t0;
  t('a 600 × 450 image traces quickly', ms < 3000, `${ms} ms`);
}
