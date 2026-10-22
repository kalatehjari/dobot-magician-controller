/* ===================== SMOOTH & QUIET MOTION: planning maths (pure, unit-tested) ===================== */
// Stepper noise and jerky motion come mostly from hard acceleration, stop-and-go moves and speeds at
// which the motors resonate. The Magician's continuous-path (CP) planner blends consecutive CP moves
// without stopping, but any point-to-point (PTP) move in between breaks that lookahead. Hence:
// gentle accelerations (profiles), drawings as one continuous CP stream with low rounded pen hops,
// and a smoothed reference path for live following ("glide").

const MOTION_PROFILES = {
  quiet: {
    label: 'Quiet & smooth', speeds: { live: 80, accel: 60, draw: 25, travel: 70, smart: 110 },
    cpAcc: 70, accelCap: 70, speedCap: 130, glideAccel: 140, glideOmega: 5, sendMs: 90, hopMin: 3,
  },
  balanced: {
    label: 'Balanced', speeds: { live: 120, accel: 120, draw: 35, travel: 100, smart: 160 },
    cpAcc: 150, accelCap: 200, speedCap: 220, glideAccel: 300, glideOmega: 7, sendMs: 70, hopMin: 3,
  },
  fast: {
    label: 'Fast', speeds: { live: 180, accel: 200, draw: 50, travel: 150, smart: 220 },
    cpAcc: 250, accelCap: 400, speedCap: 320, glideAccel: 600, glideOmega: 10, sendMs: 50, hopMin: 4,
  },
};

// Points strictly between a and b, so no piece is longer than maxLen (mm). Even pieces keep the
// arm's continuous-path speed steady along long straight lines.
function splitSegment(a, b, maxLen) {
  const d = Math.hypot(b.x - a.x, b.y - a.y, (b.z ?? 0) - (a.z ?? 0)), n = Math.max(1, Math.ceil(d / maxLen)), out = [];
  for (let j = 1; j < n; j++) {
    const t = j / n;
    out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: (a.z ?? 0) + ((b.z ?? 0) - (a.z ?? 0)) * t });
  }
  return out;
}

// Pen-up hop height for a hop of d mm: low for short hops (less up-and-down, less noise), full
// pen-up height for long ones.
function hopHeight(d, hopMin, hMax) { return Math.min(hMax, Math.max(hopMin, hopMin + 0.3 * d)); }

// A rounded pen hop from a to b (both on the paper at zD): a short vertical take-off, a smooth
// quarter-sine rise, flight at zD + h, a matching descent and a vertical touch-down, so the pen never
// drags and the direction never changes abruptly. The route bends around the base when a straight hop
// would pass through the unreachable core. Returns the points after a, ending at b.
function hopPath(a, b, zD, h, core = 0, step = 2.5) {
  const lift = Math.min(1, h), rise = Math.max(0, h - lift);
  const route = [{ x: a.x, y: a.y }, ...arcWaypoints(a, b, core), { x: b.x, y: b.y }];
  const cum = [0];
  for (let i = 1; i < route.length; i++) cum.push(cum[i - 1] + Math.hypot(route[i].x - route[i - 1].x, route[i].y - route[i - 1].y));
  const D = cum[cum.length - 1];
  if (D < 2) {                                             // tiny hop: up, over, down
    const m = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    return [{ x: a.x, y: a.y, z: zD + lift }, { x: m.x, y: m.y, z: zD + h }, { x: b.x, y: b.y, z: zD + lift }, { x: b.x, y: b.y, z: zD }];
  }
  const ramp = Math.min(D / 2, Math.max(1.5, rise * 1.2));
  const zAt = s => { const u = Math.min(s, D - s); return u >= ramp ? zD + h : zD + lift + rise * Math.sin((Math.PI / 2) * (u / ramp)); };
  const posAt = s => {
    let i = 1;
    while (i < cum.length - 1 && cum[i] < s) i++;
    const seg = cum[i] - cum[i - 1], u = seg > 0 ? (s - cum[i - 1]) / seg : 0;
    return { x: route[i - 1].x + (route[i].x - route[i - 1].x) * u, y: route[i - 1].y + (route[i].y - route[i - 1].y) * u };
  };
  const ss = new Set(), add = s => { if (s > 1e-6 && s < D - 1e-6) ss.add(+s.toFixed(4)); };
  for (let k = 1; k <= 5; k++) { add(ramp * k / 5); add(D - ramp * k / 5); }
  const flight = Math.max(0, D - 2 * ramp), nF = Math.ceil(flight / step);
  for (let k = 1; k < nF; k++) add(ramp + flight * k / nF);
  for (const c of cum) add(c);
  const out = [{ x: a.x, y: a.y, z: zD + lift }];
  for (const s of [...ss].sort((p, q) => p - q)) { const p = posAt(s); out.push({ x: p.x, y: p.y, z: zAt(s) }); }
  out.push({ x: b.x, y: b.y, z: zD + lift }, { x: b.x, y: b.y, z: zD });
  return out;
}

// One step of the "glide" follower: moves a reference point towards the target with limited speed
// and acceleration, braking in time so it never overshoots, and easing in exponentially at the end.
// st = {x, y, z, vx, vy, vz}; lim = {vMax, aMax, omega}; dt in seconds.
function glideStep(st, tgt, dt, lim) {
  const dx = tgt.x - st.x, dy = tgt.y - st.y, dz = tgt.z - st.z, dist = Math.hypot(dx, dy, dz);
  let wx = 0, wy = 0, wz = 0;
  if (dist > 1e-6) {
    const vm = Math.min(lim.vMax, Math.sqrt(2 * lim.aMax * dist) * 0.92, lim.omega * dist);
    wx = dx / dist * vm; wy = dy / dist * vm; wz = dz / dist * vm;
  }
  let ax = (wx - st.vx) / dt, ay = (wy - st.vy) / dt, az = (wz - st.vz) / dt;
  const an = Math.hypot(ax, ay, az);
  if (an > lim.aMax) { const k = lim.aMax / an; ax *= k; ay *= k; az *= k; }
  const vx = st.vx + ax * dt, vy = st.vy + ay * dt, vz = st.vz + az * dt;
  return { x: st.x + (st.vx + vx) / 2 * dt, y: st.y + (st.vy + vy) / 2 * dt, z: st.z + (st.vz + vz) / 2 * dt, vx, vy, vz };
}

// Where a gliding reference comes to rest if it brakes as hard as allowed from now on.
function glideStopPoint(st, aMax) {
  const v = Math.hypot(st.vx, st.vy, st.vz);
  if (v < 1e-6) return { x: st.x, y: st.y, z: st.z };
  const k = v / (2 * aMax);
  return { x: st.x + st.vx * k, y: st.y + st.vy * k, z: st.z + st.vz * k };
}

// Loudness of a set of microphone RMS samples, in dB above the background level (median based).
function levelDb(samples, bg) {
  const v = samples.filter(Number.isFinite).sort((p, q) => p - q);
  if (!v.length || !(bg > 0)) return NaN;
  return 20 * Math.log10(Math.max(1e-12, v[Math.floor(v.length / 2)]) / bg);
}

// The quietest speed: the fastest one within tolDb of the quietest measurement.
function pickQuiet(results, tolDb = 1) {
  const ok = results.filter(r => Number.isFinite(r.db));
  if (!ok.length) return null;
  const min = Math.min(...ok.map(r => r.db));
  return ok.filter(r => r.db <= min + tolDb).reduce((b, r) => (r.v > b.v ? r : b)).v;
}
