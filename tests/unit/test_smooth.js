// Unit tests for smooth & quiet motion: continuous drawing plan, rounded pen hops, glide follower,
// quiet-speed analysis (run: node tests/unit/test_smooth.js)
const fs = require('fs'), vm = require('vm');
const ctx = { console, Math, Float32Array, Float64Array, Int32Array, Uint8Array, Array, Object, Number, JSON, Infinity, NaN, isFinite, Set, Map, Promise, DataView, setTimeout, Date };
ctx.S = { limits: { minR: 170, maxR: 300, thMin: -87, thMax: 87, zMin: -80, zMax: 120, zUp: -45, zDown: -60 }, speed: { live: 100, accel: 100 }, gen: 0, model: null };
ctx.DEBUG = { frames: false }; ctx.log = () => {}; ctx.setConnected = () => {};
vm.createContext(ctx);
for (const f of ['part0_alarms.js', 'part1_protocol.js', 'part2_geometry.js', 'part31_kinematics.js', 'part36_place.js', 'part38_smooth.js'])
  vm.runInContext(fs.readFileSync(require('path').join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };

E(`
// a drawing with a long line, a curve, close-together strokes (short hops) and one far-away stroke
function demoOps() {
  const strokes = [[{ x: 230, y: -40 }, { x: 230, y: 40 }]], circ = [];
  for (let i = 0; i <= 60; i++) { const a = i / 60 * 2 * Math.PI; circ.push({ x: 260 + 12 * Math.cos(a), y: 12 * Math.sin(a) }); }
  strokes.push(circ);
  for (let k = 0; k < 6; k++) strokes.push([{ x: 280, y: -20 + k * 6 }, { x: 290, y: -20 + k * 6 }]);
  strokes.push([{ x: 210, y: 150 }, { x: 220, y: 150 }]);
  const seq = orderStrokes(strokes, { x: 240, y: 0 }, 200);
  return buildOps(seq, { x: 240, y: 0 }, 0.5);
}
var L = { zUp: -45, zDown: -60 };
function turnDeg(p, q, r) {           // direction change at q, degrees (3-D)
  const a = [q.x - p.x, q.y - p.y, q.z - p.z], b = [r.x - q.x, r.y - q.y, r.z - q.z];
  const na = Math.hypot(...a), nb = Math.hypot(...b);
  if (na < 1e-9 || nb < 1e-9) return 0;
  return Math.acos(Math.max(-1, Math.min(1, (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (na * nb)))) * 180 / Math.PI;
}
`);

/* ---------- continuous drawing plan ---------- */
{
  const r = E(`(() => {
    const ops = demoOps(), start = { x: 240, y: 0, z: -20 };
    const c = plotCommands(ops, L, start, { cp: true, continuous: true, speed: 25, core: 190 });
    const old = plotCommands(ops, L, start, { cp: true, speed: 25, core: 190 });
    const stops = cs => cs.filter(q => q.kind !== 'cp').length;
    let longest = 0, prev = start, below = 0;
    for (const q of c) { if (q.kind === 'cp' && Math.abs(q.z - L.zDown) < 1e-9 && Math.abs(prev.z - L.zDown) < 1e-9) longest = Math.max(longest, Math.hypot(q.x - prev.x, q.y - prev.y)); if (q.z < L.zDown - 1e-9) below++; prev = q; }
    // drawn geometry: every pen-down point of the plan lies on the original drawing
    const segs = []; let p0 = start; for (const op of ops) { if (op.pen && p0.pen) segs.push([p0, op]); p0 = op; }
    const near = q => segs.some(([a, b]) => { const dx = b.x - a.x, dy = b.y - a.y, L2 = dx * dx + dy * dy; const u = L2 ? Math.max(0, Math.min(1, ((q.x - a.x) * dx + (q.y - a.y) * dy) / L2)) : 0; return Math.hypot(a.x + u * dx - q.x, a.y + u * dy - q.y) < 1e-6; });
    const off = c.filter(q => Math.abs(q.z - L.zDown) < 1e-9).filter(q => !near(q)).length;
    let cuts = 0; for (let i = 1; i < c.length; i++) if (c[i].z <= L.zUp + 0.6 && c[i - 1].z <= L.zUp + 0.6 && segDist0(c[i - 1].x, c[i - 1].y, c[i].x, c[i].y) < 190) cuts++;
    return { n: c.length, stops: stops(c), oldStops: stops(old), longest, below, off, cuts };
  })()`);
  t('drawing runs as one continuous path: far fewer full stops', r.stops <= 4 && r.oldStops >= 15, `${r.oldStops} → ${r.stops} point-to-point moves`);
  t('lines are cut into even pieces of at most 3 mm', r.longest <= 3 + 1e-9, `longest ${r.longest.toFixed(2)} mm`);
  t('the pen never goes below the paper and every pen-down point is on the drawing', r.below === 0 && r.off === 0);
  t('no move cuts across the base', r.cuts === 0);
}

/* ---------- rounded pen hops ---------- */
{
  const r = E(`(() => {
    const a = { x: 250, y: 0, z: -60 }, b = { x: 258, y: 6, z: -60 }, d = Math.hypot(8, 6), h = hopHeight(d, 3, 15);
    const p = [a, ...hopPath(a, b, -60, h, 0)];
    let maxTurn = 0; for (let i = 1; i < p.length - 1; i++) maxTurn = Math.max(maxTurn, turnDeg(p[i - 1], p[i], p[i + 1]));
    const top = Math.max(...p.map(q => q.z));
    const take = p[1], land = p[p.length - 2];
    return { h, top, maxTurn, take, land, end: p[p.length - 1], minZ: Math.min(...p.map(q => q.z)), n: p.length,
      hShort: hopHeight(2, 3, 15), hLong: hopHeight(80, 3, 15) };
  })()`);
  t('short hops stay low, long ones lift fully', Math.abs(r.hShort - 3.6) < 1e-9 && r.hLong === 15 && Math.abs(r.top - (-60 + r.h)) < 1e-6, `2 mm → ${r.hShort} mm, 10 mm → ${r.h.toFixed(1)} mm, 80 mm → ${r.hLong} mm`);
  t('the pen leaves and lands vertically (no smudge)', r.take.x === 250 && r.take.y === 0 && r.take.z > -60 && r.land.x === 258 && r.land.y === 6 && r.end.z === -60);
  t('the hop is rounded: no direction change sharper than 60°', r.maxTurn <= 60, `sharpest turn ${r.maxTurn.toFixed(0)}° (the old lift–travel–lower had 90° corners)`);
  t('the hop never dips below the paper', r.minZ >= -60);
  const around = E(`(() => { const a = { x: 125, y: 210, z: -60 }, b = { x: 125, y: -210, z: -60 };
    const p = [a, ...hopPath(a, b, -60, 10, 200)]; let m = Infinity; for (let i = 1; i < p.length; i++) m = Math.min(m, segDist0(p[i - 1].x, p[i - 1].y, p[i].x, p[i].y)); return m; })()`);
  t('a hop across the base goes around it', around >= 200, `closest ${around.toFixed(1)} mm`);
}

/* ---------- glide follower ---------- */
{
  const r = E(`(() => {
    const lim = { vMax: 90, aMax: 140, omega: 5 }, dt = 0.03, tgt = { x: 300, y: 60, z: -20 };
    let s = { x: 240, y: 0, z: 0, vx: 0, vy: 0, vz: 0 }, aMax = 0, vMax = 0, over = 0, steps = 0;
    const d0 = Math.hypot(60, 60, -20);
    for (; steps < 400; steps++) {
      const n = glideStep(s, tgt, dt, lim);
      aMax = Math.max(aMax, Math.hypot(n.vx - s.vx, n.vy - s.vy, n.vz - s.vz) / dt);
      vMax = Math.max(vMax, Math.hypot(n.vx, n.vy, n.vz));
      const along = ((n.x - 240) * 60 + (n.y - 0) * 60 + (n.z - 0) * -20) / d0;
      over = Math.max(over, along - d0);
      s = n;
      if (Math.hypot(tgt.x - s.x, tgt.y - s.y, tgt.z - s.z) < 0.2 && Math.hypot(s.vx, s.vy, s.vz) < 0.5) break;
    }
    // stop point: braking from full speed ends where predicted
    let b = { x: 0, y: 0, z: 0, vx: 90, vy: 0, vz: 0 }; const stop = glideStopPoint(b, 140);
    return { aMax, vMax, over, secs: steps * dt, stopX: stop.x };
  })()`);
  t('glide keeps acceleration and speed within the limits', r.aMax <= 140 + 1e-6 && r.vMax <= 90 + 1e-6, `peak ${r.aMax.toFixed(0)} mm/s², ${r.vMax.toFixed(0)} mm/s`);
  t('glide arrives without overshooting', r.over < 0.3 && r.secs < 2.5, `overshoot ${r.over.toFixed(2)} mm, settled in ${r.secs.toFixed(2)} s`);
  t('braking point from 90 mm/s at 140 mm/s² is v²/2a', Math.abs(r.stopX - 90 * 90 / 280) < 1e-9, `${r.stopX.toFixed(1)} mm`);
  const jit = E(`(() => { const lim = { vMax: 90, aMax: 140, omega: 5 }; let s = { x: 250, y: 0, z: 0, vx: 0, vy: 0, vz: 0 }, seed = 5, sumT = 0, sumR = 0, n = 0;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647 - 0.5;
    for (let i = 0; i < 400; i++) { const tg = { x: 250 + rnd() * 2, y: rnd() * 2, z: 0 }; s = glideStep(s, tg, 0.03, lim);
      if (i > 50) { sumT += (tg.x - 250) ** 2 + tg.y ** 2; sumR += (s.x - 250) ** 2 + s.y ** 2; n++; } }
    return { target: Math.sqrt(sumT / n), arm: Math.sqrt(sumR / n) }; })()`);
  t('a target that jitters by ±1 mm is smoothed to a fraction of that', jit.arm < 0.35 * jit.target, `jitter ${jit.target.toFixed(2)} mm RMS → arm ${jit.arm.toFixed(2)} mm RMS (before the 0.4 mm send threshold)`);
}

/* ---------- quiet-speed analysis ---------- */
{
  t('loudness is the median level in dB above the room', Math.abs(E('levelDb([0.1, 0.2, 10, 0.2, 0.2], 0.1)') - 20 * Math.log10(2)) < 1e-9);
  t('quietest pick prefers the faster of nearly equal speeds', E(`pickQuiet([{ v: 15, db: 3.9 }, { v: 20, db: 4.3 }, { v: 25, db: 6.7 }, { v: 30, db: 10.8 }])`) === 20);
  t('quietest pick avoids a resonance', E(`pickQuiet([{ v: 60, db: 6.8 }, { v: 80, db: 7.7 }, { v: 100, db: 13 }, { v: 130, db: 8.9 }])`) === 80);
  t('no usable measurement → no pick', E(`pickQuiet([{ v: 15, db: NaN }])`) === null);
}

/* ---------- profiles ---------- */
{
  const p = E('MOTION_PROFILES');
  t('quiet profile is gentler than balanced, balanced gentler than fast',
    p.quiet.speeds.accel < p.balanced.speeds.accel && p.balanced.speeds.accel < p.fast.speeds.accel && p.quiet.cpAcc < p.balanced.cpAcc && p.quiet.accelCap < p.balanced.accelCap && p.quiet.speeds.draw < p.balanced.speeds.draw);
}

console.log(fails ? `\n${fails} FAILED` : '\nall passed');
process.exit(fails ? 1 : 0);
