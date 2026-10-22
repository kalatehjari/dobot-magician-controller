// Unit tests: free placement (size, any rotation, mirror, position) inside the green zone,
// travel routing around the base, pen-progress projection (run: node tests/unit/test_placement.js)
const fs = require('fs'), vm = require('vm');
const ctx = { console, Math, Float32Array, Float64Array, Int32Array, Uint8Array, Uint8ClampedArray, Array, Object, Number, JSON, Infinity, NaN, isFinite, Set, Map, Promise, DataView, setTimeout, Date };
ctx.S = { limits: { minR: 170, maxR: 300, thMin: -87, thMax: 87, zMin: -80, zMax: 120, zUp: -60, zDown: -75 }, speed: { live: 100, accel: 100 }, gen: 0, model: null };
ctx.DEBUG = { frames: false }; ctx.log = () => {}; ctx.setConnected = () => {};
vm.createContext(ctx);
for (const f of ['part0_alarms.js', 'part1_protocol.js', 'part2_geometry.js', 'part31_kinematics.js', 'part36_place.js']) vm.runInContext(fs.readFileSync(require('path').join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };

// test drawings (SVG-style units, y down)
E(`
var ZONE = { rIn: 200, rOut: 309, thMin: -86, thMax: 86 };
function rectStrokes(w, h) { return [[{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: 0, y: h }, { x: 0, y: 0 }]]; }
function blob() {   // wavy line, a circle and an L: asymmetric, open and closed lines
  const s = [], wave = [], circ = [];
  for (let i = 0; i <= 200; i++) wave.push({ x: i, y: 20 + 12 * Math.sin(i / 9) });
  for (let i = 0; i <= 120; i++) { const a = i / 120 * 2 * Math.PI; circ.push({ x: 150 + 30 * Math.cos(a), y: 90 + 30 * Math.sin(a) }); }
  s.push(wave, circ, [{ x: 10, y: 60 }, { x: 10, y: 140 }, { x: 80, y: 140 }]);
  return s;
}
// exact check of every original segment against the zone
function exactInZone(strokes, z) {
  let worst = Infinity;
  for (const s of strokes) for (let i = 0; i < s.length; i++) {
    const p = s[i], r = Math.hypot(p.x, p.y), th = Math.atan2(p.y, p.x) / RAD;
    if (r > z.rOut + 1e-6 || th < z.thMin - 1e-6 || th > z.thMax + 1e-6) return { ok: false, why: 'outer/side', p };
    if (i) { const d = segDist0(s[i - 1].x, s[i - 1].y, p.x, p.y); worst = Math.min(worst, d); if (d < z.rIn - 1e-6) return { ok: false, why: 'inner', d }; }
  }
  return { ok: true, worst };
}
function placed(sk, pl) { const f = placeXform(pl); return sk.strokes.map(s => s.map(f)); }
`);

/* ---------- transform ---------- */
{
  const r = E(`(() => {
    const raw = blob(), sk = prepareSketch(raw), L = Math.max(sk.srcBox.L);
    const rect = { cx: 250, cy: 10, w: 90, h: 90 };
    const a = mapToRobot(raw, rect), b = placed(sk, { cx: 250, cy: 10, size: 90, angle: 0, mirror: false });
    let d0 = 0; a.forEach((s, i) => s.forEach((p, j) => { d0 = Math.max(d0, Math.hypot(p.x - b[i][j].x, p.y - b[i][j].y)); }));
    const a90 = mapToRobot(orientStrokes(raw, 1, false), rect), b90 = placed(sk, { cx: 250, cy: 10, size: 90, angle: 90, mirror: false });
    let d90 = 0; a90.forEach((s, i) => s.forEach((p, j) => { d90 = Math.max(d90, Math.hypot(p.x - b90[i][j].x, p.y - b90[i][j].y)); }));
    const am = mapToRobot(orientStrokes(raw, 0, true), rect), bm = placed(sk, { cx: 250, cy: 10, size: 90, angle: 0, mirror: true });
    let dm = 0; am.forEach((s, i) => s.forEach((p, j) => { dm = Math.max(dm, Math.hypot(p.x - bm[i][j].x, p.y - bm[i][j].y)); }));
    return { d0, d90, dm };
  })()`);
  t('placement at 0° matches the v3 mapping (sketch up = away from the base)', r.d0 < 1e-9, r.d0.toExponential(1));
  t('90° is a clockwise quarter turn, as before', r.d90 < 1e-9, r.d90.toExponential(1));
  t('mirror flips left↔right, as before', r.dm < 1e-9, r.dm.toExponential(1));
  const inv = E(`(() => { const sk = prepareSketch(blob()); let worst = 0;
    for (const pl of [{ cx: 240, cy: -30, size: 77, angle: 33.3, mirror: false }, { cx: 210, cy: 90, size: 140, angle: -121, mirror: true }]) {
      const f = placeXform(pl), g = placeInverse(pl);
      for (const s of sk.strokes) for (const p of s) { const q = g(f(p)); worst = Math.max(worst, Math.hypot(q.x - p.x, q.y - p.y)); } }
    return worst; })()`);
  t('robot → drawing inverse is exact (used for handles and the pen start)', inv < 1e-12, inv.toExponential(1));
  const size = E(`(() => { const sk = prepareSketch(blob()), pl = { cx: 250, cy: 0, size: 120, angle: 47, mirror: false };
    const fr = placeFrame(sk, pl); return { long: Math.max(Math.hypot(fr[1].x - fr[0].x, fr[1].y - fr[0].y), Math.hypot(fr[2].x - fr[1].x, fr[2].y - fr[1].y)) }; })()`);
  t('size = the drawing’s longest side in mm, at any rotation', Math.abs(size.long - 120) < 1e-9, size.long.toFixed(6));
  const rot = E(`(() => { const sk = prepareSketch([[{ x: 0, y: 0 }, { x: 100, y: 0 }]]);
    const s = placed(sk, { cx: 250, cy: 0, size: 100, angle: 30, mirror: false })[0];
    return Math.atan2(-(s[1].x - s[0].x), -(s[1].y - s[0].y)) * 180 / Math.PI; })()`);
  // a sketch-horizontal line, turned 30° clockwise as seen on screen (screen x = −robot y, screen y = −robot x)
  t('free rotation: a horizontal line turned 30° clockwise on the preview', Math.abs(rot - 30) < 1e-9, rot.toFixed(3) + '°');
}

/* ---------- hull & distances ---------- */
{
  const h = E(`convexHull([{x:0,y:0},{x:10,y:0},{x:10,y:10},{x:0,y:10},{x:5,y:5},{x:2,y:7},{x:10,y:5}]).length`);
  t('convex hull keeps only the corners', h === 4, `${h} points`);
  t('distance from the base to a segment', Math.abs(E('segDist0(-5, 10, 5, 10)') - 10) < 1e-12 && Math.abs(E('segDist0(10, 0, 20, 0)') - 10) < 1e-12);
}

/* ---------- fit checks ---------- */
{
  const r = E(`(() => { const sk = prepareSketch(blob()); let tested = 0, yes = 0, wrong = 0, seed = 7;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (let k = 0; k < 3000; k++) {
      const pl = { cx: 150 + rnd() * 180, cy: -200 + rnd() * 400, size: 20 + rnd() * 140, angle: -180 + rnd() * 360, mirror: rnd() < 0.5 };
      const P = placementProbe(sk, pl.angle, pl.mirror);
      tested++;
      if (probeFits(P, pl.cx, pl.cy, pl.size, ZONE)) { yes++; if (!exactInZone(placed(sk, pl), ZONE).ok) wrong++; }
    }
    return { tested, yes, wrong }; })()`);
  t('a placement accepted as fitting is inside the zone for every line (3000 random placements)', r.wrong === 0 && r.yes > 100, `${r.yes} accepted, ${r.wrong} wrong`);
  const tight = E(`(() => { const sk = prepareSketch(blob()), P = placementProbe(sk, 20, false), s = maxSizeAt(P, 255, 15, ZONE);
    return { s, ok: probeFits(P, 255, 15, s, ZONE), over: probeFits(P, 255, 15, s * 1.02, ZONE) }; })()`);
  t('largest size at a spot fits, 2 % more does not', tight.ok && !tight.over && tight.s > 50, `${tight.s.toFixed(1)} mm`);
}

/* ---------- largest placement ---------- */
{
  const r = E(`(() => { const sk = prepareSketch(rectStrokes(150, 100)), P = placementProbe(sk, 0, false);
    const b = bestPlacement(P, ZONE, { centreLine: true }), f = fitRectForAspect(ZONE.rIn, ZONE.rOut, 0, 1.5, ZONE.thMax);
    return { b, f }; })()`);
  t('largest landscape drawing on the centre line = v3’s largest box', Math.abs(r.b.size - r.f.h) / r.f.h < 0.006 && Math.abs(r.b.cx - r.f.cx) < 1.5 && Math.abs(r.b.cy) < 1e-9,
    `${r.b.size.toFixed(1)} vs ${r.f.h.toFixed(1)} mm, centre ${r.b.cx.toFixed(1)} vs ${r.f.cx.toFixed(1)}`);
  const tall = E(`(() => { const sk = prepareSketch(rectStrokes(40, 200)), P = placementProbe(sk, 0, false);
    return { line: bestPlacement(P, ZONE, { centreLine: true }), any: bestPlacement(P, ZONE) }; })()`);
  t('a tall drawing gets bigger off to the side, where the zone runs along it', tall.any.size > tall.line.size * 1.2 && Math.abs(tall.any.cy) > 50,
    `centre line ${tall.line.size.toFixed(0)} mm, anywhere ${tall.any.size.toFixed(0)} mm at y ${tall.any.cy.toFixed(0)}`);
  const exact = E(`(() => { const sk = prepareSketch(blob()), out = [];
    for (const angle of [0, 37, 90, -150]) { const P = placementProbe(sk, angle, false), b = bestPlacement(P, ZONE);
      out.push(exactInZone(placed(sk, { ...b, angle, mirror: false }), ZONE).ok); }
    return out; })()`);
  t('largest placements at several rotations are inside the zone', exact.every(Boolean), JSON.stringify(exact));
}

/* ---------- a drawing with a gap facing the base ---------- */
{
  // a wide Π open towards the base: at its largest the area round the base sits between the legs without
  // touching a line, but smaller a leg crosses it — the largest size must hold at every smaller size too
  const r = E(`(() => { const sk = prepareSketch([[{ x: 0, y: 150 }, { x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 150 }]]);
    const P = placementProbe(sk, 0, false), b = bestPlacement(P, ZONE, { centreLine: true }), out = [];
    for (const k of [0.3, 0.5, 0.7, 0.8, 0.9, 1]) out.push(probeFits(P, b.cx, b.cy, b.size * k, ZONE));
    const f = fixPlacement(sk, { cx: b.cx, cy: b.cy, size: b.size * 0.75, angle: 0, mirror: false }, ZONE);
    return { size: b.size, out, f }; })()`);
  t('largest size for a drawing with a gap also fits at every smaller size (was not so at 70–80 %)', r.out.every(Boolean), `${r.size.toFixed(0)} mm: ${JSON.stringify(r.out)}`);
  t('…so a smaller size at the same spot is accepted as it is', r.f && !r.f.fixed);
}

/* ---------- fixing and dragging ---------- */
{
  const r = E(`(() => { const sk = prepareSketch(blob());
    const far = fixPlacement(sk, { cx: 120, cy: 0, size: 80, angle: 15, mirror: false }, ZONE);
    const huge = fixPlacement(sk, { cx: 250, cy: 0, size: 900, angle: 15, mirror: false }, ZONE);
    const fine = fixPlacement(sk, { cx: 255, cy: 0, size: 60, angle: 0, mirror: false }, ZONE);
    const P = placementProbe(sk, 15, false);
    return { far, huge, fine, farOk: exactInZone(placed(sk, far), ZONE).ok, hugeOk: exactInZone(placed(sk, huge), ZONE).ok,
             any: bestPlacement(P, ZONE).size };
  })()`);
  t('a drawing placed over the base is moved out just far enough, same size', r.farOk && r.far.size === 80 && r.far.fixed && Math.hypot(r.far.cx - 120, r.far.cy) < 140, `centre now ${r.far.cx.toFixed(0)}, ${r.far.cy.toFixed(0)}`);
  t('a drawing too big for the zone is shrunk to the largest that fits', r.hugeOk && r.huge.shrunk && r.huge.size <= r.any + 1e-6, `${r.huge.size.toFixed(0)} mm (largest ${r.any.toFixed(0)})`);
  t('a drawing that already fits is left alone', !r.fine.fixed && r.fine.cx === 255 && r.fine.size === 60);
  const d = E(`(() => { const sk = prepareSketch(blob()), P = placementProbe(sk, 0, false), z = ZONE, size = 60;
    let c = { x: 255, y: 0 }; const steps = [];
    for (let i = 0; i < 40; i++) { c = constrainMove(P, c, { x: c.x - 6, y: c.y }, size, z); steps.push(probeFits(P, c.x, c.y, size, z)); }
    const fits = (x, y) => probeFits(P, x, y, size, z), from = { x: 255, y: 0 }, to = { x: 150, y: 120 };
    const straight = walkToward(from, to, fits), slid = constrainMove(P, from, to, size, z);
    const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
    return { allFit: steps.every(Boolean), end: c, gain: dist(straight, to) - dist(slid, to), slidFits: fits(slid.x, slid.y), toFits: fits(to.x, to.y) };
  })()`);
  t('dragging towards the base stops at the zone edge', d.allFit && Math.hypot(d.end.x, d.end.y) > 200, `stopped at r = ${Math.hypot(d.end.x, d.end.y).toFixed(0)} mm`);
  t('…and slides along the edge with the rest of the move', !d.toFits && d.slidFits && d.gain > 5, `${d.gain.toFixed(1)} mm closer to the pointer than stopping dead`);
}

/* ---------- pen-up travel around the base ---------- */
{
  const r = E(`(() => { const a = { x: 250 * Math.cos(1.05), y: 250 * Math.sin(1.05) }, b = { x: 250 * Math.cos(-1.05), y: 250 * Math.sin(-1.05) };
    const w = arcWaypoints(a, b, 200), pts = [a, ...w, b]; let worst = Infinity;
    for (let i = 1; i < pts.length; i++) worst = Math.min(worst, segDist0(pts[i - 1].x, pts[i - 1].y, pts[i].x, pts[i].y));
    const none = arcWaypoints({ x: 250, y: -20 }, { x: 260, y: 30 }, 200).length;
    const ops = [{ x: a.x, y: a.y, pen: false }, { x: a.x, y: a.y, pen: true }, { x: a.x + 3, y: a.y, pen: true }, { x: a.x + 3, y: a.y, pen: false },
                 { x: b.x, y: b.y, pen: false }, { x: b.x, y: b.y, pen: true }, { x: b.x + 3, y: b.y, pen: true }, { x: b.x + 3, y: b.y, pen: false }];
    const cmds = plotCommands(ops, S.limits, { x: 250, y: 0, z: -60 }, { cp: true, core: 200 });
    let cut = 0; for (let i = 1; i < cmds.length; i++) if (segDist0(cmds[i - 1].x, cmds[i - 1].y, cmds[i].x, cmds[i].y) < 200) cut++;
    const plain = plotCommands(ops, S.limits, { x: 250, y: 0, z: -60 }, { cp: true });
    let cut0 = 0; for (let i = 1; i < plain.length; i++) if (segDist0(plain[i - 1].x, plain[i - 1].y, plain[i].x, plain[i].y) < 200) cut0++;
    return { n: w.length, worst, none, cut, cut0 }; })()`);
  t('a pen-up hop across the base follows the arc instead', r.n >= 20 && r.worst >= 200 && r.none === 0, `${r.n} waypoints, closest ${r.worst.toFixed(1)} mm`);
  t('drawing commands never cut across the base (was ' + r.cut0 + ' straight hop)', r.cut === 0 && r.cut0 >= 1);
}

/* ---------- pen progress ---------- */
{
  const p = E(`projectOnSeg3({ x: 0, y: 0, z: 0 }, { x: 10, y: 0, z: 0 }, { x: 4, y: 1, z: 0 })`);
  t('pen position projects onto the planned line', Math.abs(p.t - 0.4) < 1e-12 && Math.abs(p.d - 1) < 1e-12);
}

/* ---------- speed ---------- */
{
  const r = E(`(() => { const s = []; let x = 0, y = 0, seed = 3; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (let k = 0; k < 400; k++) { const st = []; x = rnd() * 600; y = rnd() * 400; for (let i = 0; i < 50; i++) { x += rnd() * 6 - 3; y += rnd() * 6 - 3; st.push({ x, y }); } s.push(st); }
    const t0 = Date.now(), sk = prepareSketch(s), t1 = Date.now(), P = placementProbe(sk, 25, false), b = bestPlacement(P, ZONE), t2 = Date.now();
    const pl = { ...b, angle: 25, mirror: false }; let c = { x: b.cx, y: b.cy }; const t3 = Date.now();
    for (let i = 0; i < 30; i++) c = constrainMove(P, c, { x: c.x + 5, y: c.y - 5 }, b.size * 0.8, ZONE);
    const t4 = Date.now();
    return { pts: sk.points, prep: t1 - t0, best: t2 - t1, drag: (t4 - t3) / 30, size: b.size }; })()`);
  t('20 000-point drawing: largest placement found quickly', r.best < 600, `prepare ${r.prep} ms, largest ${r.best} ms, size ${r.size.toFixed(0)} mm`);
  t('dragging stays smooth (< 8 ms per pointer move)', r.drag < 8, `${r.drag.toFixed(2)} ms per move`);
}

console.log(fails ? `\n${fails} FAILED` : '\nall passed');
process.exit(fails ? 1 : 0);
