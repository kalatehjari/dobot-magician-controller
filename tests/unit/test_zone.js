// Unit tests: safe-zone polygon, allowed area, routing inside it, safety-lock checks and trimming
// (run: node tests/unit/test_zone.js)
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { console, Math, Float32Array, Float64Array, Int32Array, Uint8Array, Uint32Array, Uint8ClampedArray, Array, Object, Number, JSON, String,
  Infinity, NaN, isFinite, isNaN, parseFloat, parseInt, Set, Map, Promise, DataView, ArrayBuffer, setTimeout, clearTimeout, Date, Error, RegExp,
  TextDecoder, TextEncoder, navigator: { userAgent: 'node', appName: 'Netscape' } };
ctx.self = ctx;
ctx.S = { limits: { minR: 170, maxR: 300, thMin: -87, thMax: 87, zMin: -80, zMax: 120, zUp: -60, zDown: -75 }, speed: { live: 100, accel: 100 }, gen: 0, model: null };
ctx.DEBUG = { frames: false }; ctx.log = () => {}; ctx.setConnected = () => {};
vm.createContext(ctx);
for (const f of ['part0_alarms.js', 'part1_protocol.js', 'part2_geometry.js', 'part31_kinematics.js', 'part36_place.js', 'part48_clipper.js', 'part49_slicer.js', 'part53_zone.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };

E(`
var ZONE = { rIn: 190, rOut: 300, thMin: -80, thMax: 80, margin: 4 };
var SQ = [{ x: 190, y: -60 }, { x: 290, y: -60 }, { x: 290, y: 60 }, { x: 190, y: 60 }];          // a convex safe zone
var ELL = [{ x: 200, y: -80 }, { x: 290, y: -80 }, { x: 290, y: 80 }, { x: 250, y: 80 }, { x: 250, y: -20 }, { x: 200, y: -20 }];   // an L
function rectStrokes(w, h) { return [[{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: 0, y: h }, { x: 0, y: 0 }]]; }
function wavy() { const s = []; for (let i = 0; i <= 120; i++) s.push({ x: i, y: 15 * Math.sin(i / 7) }); return [s, [{ x: 0, y: 40 }, { x: 120, y: 40 }]]; }
// exact: every original segment of the placed drawing keeps c from the polygon edges and is inside
function exactPoly(sk, pl, P, c) {
  const pp = polyPrep(P), f = placeXform(pl);
  let worst = Infinity;
  for (const s of sk.strokes) {
    const q = s.map(f);
    for (let i = 0; i < q.length; i++) {
      if (!polyHas(pp, q[i].x, q[i].y)) return { ok: false, worst: -1 };
      if (i) for (let k = 0; k < pp.n; k++) worst = Math.min(worst, Math.sqrt(segSegD2(q[i - 1].x, q[i - 1].y, q[i].x, q[i].y, pp.e[4 * k], pp.e[4 * k + 1], pp.e[4 * k + 2], pp.e[4 * k + 3])));
    }
  }
  return { ok: worst >= c - 1e-6, worst };
}
function zoneWith(P) { const z = { ...ZONE }; if (P) { z.poly = P; z.pq = polyPrep(P); z.polyKey = polyKeyOf(P); } return z; }
`);

/* ---------- polygon checks ---------- */
const pc = E(`[polyCheck(SQ), polyCheck(ELL), polyCheck([{x:0,y:0},{x:100,y:100},{x:100,y:0},{x:0,y:100}]), polyCheck([{x:0,y:0},{x:5,y:0},{x:5,y:5}]), polyCheck([{x:0,y:0},{x:1,y:1}])]`);
t('a square and an L can be safe zones; a bow tie, a tiny triangle and two points cannot', pc[0] === '' && pc[1] === '' && /cross/.test(pc[2]) && /small/.test(pc[3]) && /3 corners/.test(pc[4]), JSON.stringify(pc));
const conv = E(`[polyPrep(SQ).convex, polyPrep(ELL).convex, polyPrep(SQ.slice().reverse()).convex]`);
t('convexity is found either way round', conv[0] && !conv[1] && conv[2]);

/* ---------- placement inside the polygon ---------- */
const pl1 = E(`(() => {
  const sk = prepareSketch(wavy()), P = placementProbe(sk, 0, false), out = [];
  for (const Q of [SQ, ELL]) {
    const z = zoneWith(Q), b = bestPlacement(P, z, { pad: 0.15 });
    const ex = b ? exactPoly(sk, { cx: b.cx, cy: b.cy, size: b.size, angle: 0, mirror: false }, Q, z.margin) : null;
    out.push({ size: b && +b.size.toFixed(1), ok: !!(ex && ex.ok), worst: ex && +ex.worst.toFixed(2), fits: !!b && probeFits(P, b.cx, b.cy, b.size, z, 0.15) });
  }
  return out;
})()`);
t('largest placement in a square safe zone fits it, with the margin (exact check)', pl1[0].ok && pl1[0].fits && pl1[0].size > 80, JSON.stringify(pl1[0]));
t('largest placement in an L-shaped safe zone fits it, with the margin (exact check)', pl1[1].ok && pl1[1].fits && pl1[1].size > 40, JSON.stringify(pl1[1]));
const mc = E(`(() => {          // random placements: the fast check never says yes when the exact one says no
  const sk = prepareSketch(wavy()), z = zoneWith(ELL); let yes = 0, wrong = 0, n = 0;
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 400; i++) {
    const ang = Math.round(rnd() * 360 - 180), P = placementProbe(sk, ang, false), pl = { cx: 200 + rnd() * 90, cy: -80 + rnd() * 160, size: 10 + rnd() * 70, angle: ang, mirror: false };
    const f = probeFits(P, pl.cx, pl.cy, pl.size, z, 0.15); n++;
    if (f) { yes++; if (!exactPoly(sk, pl, ELL, z.margin).ok) wrong++; }
  }
  return { n, yes, wrong };
})()`);
t('random placements in the L: every one the fast check accepts is exactly inside', mc.wrong === 0 && mc.yes > 20, JSON.stringify(mc));
const fx = E(`(() => {
  const sk = prepareSketch(rectStrokes(40, 30)), P = placementProbe(sk, 30, false), z = zoneWith(ELL);
  const r = fixPlacement(sk, { cx: 220, cy: 40, size: 40, angle: 30, mirror: false }, z, { pad: 0.15, probe: P });   // asked for the L's notch
  return { r: r && { cx: +r.cx.toFixed(1), cy: +r.cy.toFixed(1), size: +r.size.toFixed(1), fixed: r.fixed }, ok: !!r && exactPoly(sk, r, ELL, z.margin).ok };
})()`);
t('a drawing asked for in the notch of the L is moved into the L', fx.ok && fx.r.fixed, JSON.stringify(fx.r));
const cm = E(`(() => {
  const sk = prepareSketch(rectStrokes(20, 20)), P = placementProbe(sk, 0, false), z = zoneWith(SQ);
  const c = constrainMove(P, { x: 240, y: 0 }, { x: 400, y: 0 }, 20, z, 0.15);
  return { x: +c.x.toFixed(2), ok: exactPoly(sk, { cx: c.x, cy: c.y, size: 20, angle: 0, mirror: false }, SQ, z.margin).ok };
})()`);
t('dragging out of the square stops at its edge, margin kept', cm.ok && cm.x > 270 && cm.x < 290, JSON.stringify(cm));
const sm = E(`(() => { const sk = prepareSketch(rectStrokes(20, 20)), P = placementProbe(sk, 0, false), z = zoneWith(SQ); return [maxSizeAt(P, 240, 0, z, 0.15), maxSizeAt(P, 240, 0, { ...ZONE }, 0.15)]; })()`);
t('the largest size at a spot is limited by the safe zone', sm[0] > 80 && sm[0] < sm[1] && sm[0] <= 100.1 - 8, sm.map(v => v.toFixed(1)).join(' < '));

/* ---------- the allowed area ---------- */
const rg = E(`(() => {
  const R0 = regionBuild(ZONE, null), R1 = regionBuild(ZONE, SQ), R2 = regionBuild(ZONE, ELL);
  const exact = Math.PI * (300 ** 2 - 190 ** 2) * 160 / 360;
  return { a0: R0.area, exact, a1: R1.area, a2: R2.area, rings: [R0.rings.length, R1.rings.length, R2.rings.length],
    pts: [regionHas(R1, 240, 0), regionHas(R1, 240, 57), regionHas(R1, 240, 55), regionHas(R2, 220, 40), regionHas(R2, 270, 40), regionHas(R0, 150, 0), regionHas(R0, 250, 0)] };
})()`);
t('green zone as a polygon: area within 0.5 % of the exact annular sector, a little inside it', rg.a0 < rg.exact && rg.a0 > rg.exact * 0.995, `${rg.a0.toFixed(0)} vs ${rg.exact.toFixed(0)} mm²`);
t('square ∩ zone, shrunk by the 4 mm margin: 92 × 112 mm', Math.abs(rg.a1 - 92 * 112) < 40, rg.a1.toFixed(0) + ' mm²');
t('points inside and outside the allowed area', rg.pts.join() === 'true,false,true,false,true,false,true', rg.pts.join());
const sp = E(`(() => { const R = regionBuild(ZONE, ELL);
  return { inLeg: regionSegInside(R, 260, -60, 280, 60), acrossNotch: regionSegInside(R, 220, -50, 270, 60),
           spans: regionSpans(R, 220, -50, 270, 60).map(s => s.map(v => +v.toFixed(3))), cuts: regionCuts(R, 220, -50, 270, 60).length }; })()`);
t('a move along the long leg of the L stays inside; one across the notch does not', sp.inLeg && !sp.acrossNotch && sp.spans.length === 2, JSON.stringify(sp.spans));

/* ---------- routing round inside ---------- */
const ro = E(`(() => {
  const U = [{ x: 195, y: -90 }, { x: 295, y: -90 }, { x: 295, y: 90 }, { x: 195, y: 90 }, { x: 195, y: 50 }, { x: 265, y: 50 }, { x: 265, y: -50 }, { x: 195, y: -50 }];   // a U open towards the base
  const R = regionBuild(ZONE, U), route = regionRouter(R), a = { x: 215, y: -70 }, b = { x: 215, y: 70 };
  const w = route(a, b), pts = [a, ...(w || []), b];
  let ok = true, len = 0;
  for (let i = 1; i < pts.length; i++) { if (!regionSegInside(R, pts[i - 1].x, pts[i - 1].y, pts[i].x, pts[i].y, 0.05)) ok = false; len += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y); }
  return { n: w && w.length, ok, len, direct: Math.hypot(a.x - b.x, a.y - b.y), straight: route({ x: 280, y: -70 }, { x: 280, y: 70 }).length };
})()`);
t('travel between the two arms of a U goes round inside it', ro.ok && ro.n >= 2 && ro.len > ro.direct + 50 && ro.len < 330, `${ro.n} corners, ${ro.len.toFixed(0)} mm (straight ${ro.direct.toFixed(0)} mm)`);
t('travel that can go straight does', ro.straight === 0);

/* ---------- safety lock ---------- */
const lk = E(`(() => {
  const R = regionBuild(ZONE, ELL), floor = -76, L = { zDown: -75, zUp: -60 };
  // a pen-down line that runs across the notch, and a travel move into the notch
  const cmds = [{ x: 220, y: -50, z: -60, mode: 2 }, { x: 220, y: -50, z: -75, mode: 2 }, { kind: 'cp', x: 270, y: 60, z: -75, v: 30 }, { x: 270, y: 60, z: -60, mode: 2 }, { x: 225, y: 50, z: -60, mode: 2 }];
  const start = { x: 270, y: -60, z: -50 };
  const before = lockCheckPath(cmds, start, R, floor);
  const trimmed = lockTrimPath(cmds, start, R, floor, { mode: 'draw', zDown: -75, zUp: -60, route: regionRouter(R) });
  const after = lockCheckPath(trimmed, start, R, floor);
  let drawn = 0, prev = start;           // pen-down length kept
  for (const c of trimmed) { if (c.x === undefined) continue; if (c.z <= -74.4 && prev.z <= -74.4) drawn += Math.hypot(c.x - prev.x, c.y - prev.y); prev = c; }
  const full = Math.hypot(50, 110), insideLen = regionSpans(R, 220, -50, 270, 60).reduce((a, s) => a + (s[1] - s[0]), 0) * full;
  const low = lockCheckPath([{ x: 250, y: -50, z: -80 }], { x: 260, y: -50, z: -60 }, R, floor);
  const lowT = lockTrimPath([{ x: 250, y: -50, z: -80 }], { x: 260, y: -50, z: -60 }, R, floor, { mode: 'move', zDown: -75, zUp: -60 });
  return { before: before.bad, worst: before.worst, after: after.ok, n: trimmed.length, drawn, insideLen, low: low.bad, lowZ: lowT[0].z };
})()`);
t('lock: a drawing line across the notch and a move into it are caught', lk.before === 2 && lk.worst > 10, `${lk.before} moves, up to ${lk.worst.toFixed(1)} mm outside`);
t('trim: the drawing keeps exactly its parts inside, lifts and goes round between them; the result passes', lk.after && Math.abs(lk.drawn - lk.insideLen) < 0.05, `${lk.drawn.toFixed(2)} of ${lk.insideLen.toFixed(2)} mm drawn, ${lk.n} moves`);
t('lock: going below the paper is caught, and trimming raises it to the floor', lk.low === 1 && lk.lowZ === -76);
const ent = E(`(() => { const R = regionBuild(ZONE, SQ), floor = -76;
  return [lockSegOk(R, { x: 160, y: 0, z: 0 }, { x: 240, y: 0, z: 0 }, floor), lockSegOk(R, { x: 160, y: 0, z: 0 }, { x: 160, y: 100, z: 0 }, floor),
          lockSegOk(R, { x: 240, y: 0, z: 0 }, { x: 320, y: 0, z: 0 }, floor)]; })()`);
t('after centring outside the zone, a move straight into it is allowed; moves that stay out or leave are not', ent.join() === 'true,false,false', ent.join());
const cl = E(`(() => { const R = regionBuild(ZONE, ELL), floor = -76, from = { x: 270, y: 0, z: -40 };
  const a = lockClampPoint(R, from, { x: 330, y: 0, z: -40 }, floor), b = lockClampPoint(R, from, { x: 215, y: 60, z: -90 }, floor);
  return { a, b, okA: lockSegOk(R, from, a, floor), okB: lockSegOk(R, from, b, floor) }; })()`);
t('following: a target outside is pulled to the edge, reachable in a straight move', cl.okA && cl.okB && cl.a.x < 287 && cl.a.x > 280 && cl.b.z === -76, JSON.stringify({ a: [cl.a.x.toFixed(1), cl.a.y.toFixed(1)], b: [cl.b.x.toFixed(1), cl.b.y.toFixed(1), cl.b.z] }));
const perf = E(`(() => { const R = regionBuild(ZONE, ELL), route = regionRouter(R), t0 = Date.now(); let n = 0;
  for (let i = 0; i < 200; i++) { const w = route({ x: 220, y: -50 }, { x: 270, y: 60 }); if (w) n++; } return { ms: Date.now() - t0, n }; })()`);
t('routing is quick (200 routes)', perf.n === 200 && perf.ms < 1500, perf.ms + ' ms');

console.log(fails ? `\n${fails} FAILED` : '\nall safe-zone and lock tests passed');
process.exit(fails ? 1 : 0);
