/* ===================== KINEMATICS & AUTO-CALIBRATION MATH (pure, unit-tested) ===================== */
// Dobot Magician geometry: rear arm 135 mm, forearm 147 mm; a parallelogram keeps the tool level.
// Joint angles as reported by the robot (degrees): j1 base (0 = +X axis), j2 rear arm from vertical
// (+ = leaning forward), j3 forearm from horizontal (+ = pointing down). z = 0 is the shoulder-axis
// height. The tool point is dR mm beyond the wrist horizontally and dZ mm above it; both depend on
// the tool fitted, so auto-calibration measures them from the robot's own readings.
// Joint limits: base ±90°, rear arm 0–85°, forearm −10–85°, and the elbow (angle between the arms)
// 40–155°, i.e. −65° ≤ j3 − j2 ≤ 50°, which keeps the forearm off the rear arm and the elbow up.
const MAG = { L2: 135, L3: 147, j1: [-90, 90], j2: [0, 85], j3: [-10, 85], d32: [-65, 50] };
const DEG = Math.PI / 180;

function magFK(j2, j3, m) {
  return {
    r: MAG.L2 * Math.sin(j2 * DEG) + MAG.L3 * Math.cos(j3 * DEG) + m.dR,
    z: MAG.L2 * Math.cos(j2 * DEG) - MAG.L3 * Math.sin(j3 * DEG) + m.dZ,
  };
}

// Inverse kinematics in the arm's vertical plane (elbow-up branch). Returns {j2, j3} or null.
function magIK(r, z, m) {
  const rw = r - m.dR, zw = z - m.dZ, L2 = MAG.L2, L3 = MAG.L3;
  const d2 = rw * rw + zw * zw, d = Math.sqrt(d2);
  if (d < 1e-6 || d > L2 + L3 || d < Math.abs(L2 - L3)) return null;
  const a = (L2 * L2 - L3 * L3 + d2) / (2 * d);
  const h = Math.sqrt(Math.max(0, L2 * L2 - a * a));
  const ux = rw / d, uz = zw / d;
  // Elbow candidates either side of the shoulder→wrist line; elbow-up = counter-clockwise side.
  const ex = a * ux - h * uz, ez = a * uz + h * ux;
  const j2 = Math.atan2(ex, ez) / DEG;
  const j3 = Math.atan2(-(zw - ez), rw - ex) / DEG;
  return { j2, j3 };
}

function magJointsOk(j, marginDeg = 0) {
  const m = marginDeg;
  return j.j2 >= MAG.j2[0] + m && j.j2 <= MAG.j2[1] - m &&
         j.j3 >= MAG.j3[0] + m && j.j3 <= MAG.j3[1] - m &&
         (j.j3 - j.j2) >= MAG.d32[0] + m && (j.j3 - j.j2) <= MAG.d32[1] - m;
}

// Can the tool reach (x, y, z)? Checks base angle, IK solution and every joint limit (with margin).
function magReachable(x, y, z, m, marginDeg = 0) {
  const th = Math.atan2(y, x) / DEG;
  if (th < MAG.j1[0] + marginDeg || th > MAG.j1[1] - marginDeg) return false;
  const j = magIK(Math.hypot(x, y), z, m);
  return !!j && magJointsOk(j, marginDeg);
}

// Tool offsets implied by one reading of pose + joint angles.
function estimateOffsets(p) {
  const w = magFK(p.j2, p.j3, { dR: 0, dZ: 0 });
  const r = Math.hypot(p.x, p.y);
  const baseErr = r > 30 ? Math.abs(((Math.atan2(p.y, p.x) / DEG - p.j1 + 540) % 360) - 180) : 0;
  return { dR: r - w.r, dZ: p.z - w.z, baseErr };
}

// The geometry model is confirmed when several different poses imply the same offsets.
function validateModel(poses, tolMm = 2.0) {
  const o = poses.map(estimateOffsets);
  const dR = o.reduce((s, v) => s + v.dR, 0) / o.length, dZ = o.reduce((s, v) => s + v.dZ, 0) / o.length;
  const maxDev = Math.max(...o.map(v => Math.hypot(v.dR - dR, v.dZ - dZ)));
  const baseErr = Math.max(...o.map(v => v.baseErr));
  let spread = 0;
  for (let i = 0; i < poses.length; i++) for (let k = i + 1; k < poses.length; k++)
    spread = Math.max(spread, Math.hypot(poses[i].j2 - poses[k].j2, poses[i].j3 - poses[k].j3));
  const plausible = dR > -20 && dR < 140 && dZ > -200 && dZ < 80;
  return { ok: poses.length >= 2 && spread >= 3 && maxDev <= tolMm && baseErr <= 1.5 && plausible, dR, dZ, maxDev, baseErr, spread, plausible };
}

// Largest reachable radial interval at height z (joint margin in degrees), or null.
function radialInterval(m, z, marginDeg = 2) {
  let best = null, cur = null;
  for (let r = 20; r <= 440; r += 1) {
    const j = magIK(r, z, m);
    if (j && magJointsOk(j, marginDeg)) { if (!cur) cur = [r, r]; else cur[1] = r; }
    else if (cur) { if (!best || cur[1] - cur[0] > best[1] - best[0]) best = cur; cur = null; }
  }
  if (cur && (!best || cur[1] - cur[0] > best[1] - best[0])) best = cur;
  return best;
}

// Widest radial interval [rIn, rOut] reachable at EVERY height in [zLo, zHi].
function reachBand(m, zLo, zHi, marginDeg = 2) {
  let rIn = -Infinity, rOut = Infinity;
  const steps = Math.max(2, Math.ceil((zHi - zLo) / 2));
  for (let s = 0; s <= steps; s++) {
    const best = radialInterval(m, zLo + (zHi - zLo) * s / steps, marginDeg);
    if (!best) return null;
    rIn = Math.max(rIn, best[0]); rOut = Math.min(rOut, best[1]);
    if (rOut - rIn < 10) return null;
  }
  return { rIn, rOut };
}

// Reach per millimetre of height, cached per tool model. Used by the safety clamp.
const REACH = { key: '', rows: null, zLo: 0, zHi: 0 };
function reachTable(m, marginDeg = 2) {
  const key = `${m.dR.toFixed(2)},${m.dZ.toFixed(2)},${marginDeg}`;
  if (REACH.key === key) return REACH;
  const rows = new Map();
  let zLo = Infinity, zHi = -Infinity;
  for (let z = -220; z <= 260; z++) {
    const b = radialInterval(m, z, marginDeg);
    if (b && b[1] - b[0] >= 4) { rows.set(z, b); zLo = Math.min(zLo, z); zHi = Math.max(zHi, z); }
  }
  Object.assign(REACH, { key, rows, zLo, zHi });
  return REACH;
}
function reachAt(m, z) {
  const T = reachTable(m);
  return T.rows.get(Math.round(clamp(z, T.zLo, T.zHi))) || null;
}

// Limits for the app from the geometry. zPaper = pen-down height (null until the user sets it;
// then everything stays at least 20 mm below the home height to keep clear of the table).
function autoLimits(m, zPaper, home) {
  const zLo = zPaper == null ? Math.round(home.z - 20) : zPaper - 0.5;
  let pick = null;
  for (let H = 120; H >= 20 && !pick; H -= 5) {
    const b = reachBand(m, zLo, zLo + H, 2);
    if (b && b.rOut - b.rIn >= 110) pick = { H, ...b };
  }
  for (let H = 20; H >= 5 && !pick; H -= 5) {
    const b = reachBand(m, zLo, zLo + H, 2);
    if (b) pick = { H, ...b };
  }
  if (!pick) return null;
  const minR = Math.ceil(pick.rIn + 3), maxR = Math.floor(pick.rOut - 3);
  const zMin = Math.round(zLo * 10) / 10, zMax = Math.floor(zLo + pick.H);
  const zDown = zPaper == null ? zMin + 10 : zPaper;
  return {
    minR, maxR, thMin: MAG.j1[0] + 3, thMax: MAG.j1[1] - 3, zMin, zMax,
    zDown, zUp: Math.min(zMax, Math.round((zDown + 15) * 10) / 10),
    homeX: Math.round((minR + maxR) / 2), homeY: 0, homeZ: Math.round(zMin + pick.H * 0.6),
    bandHeight: pick.H,
  };
}

// Largest rectangle with a given aspect (sketch width / sketch height) inside the reach band.
// Sketch "up" points away from the base (robot +X), sketch width runs along robot Y.
// The near edge sits on the inner radius; the far corners touch the outer radius.
function fitRectForAspect(minR, maxR, margin, aspect, thMaxDeg = 90) {
  const a = minR + margin, b = maxR - margin;
  if (!(b > a) || !(aspect > 0)) return null;
  // (a + w)^2 + (aspect*w/2)^2 = b^2  →  solve for w (robot-X extent)
  const A = 1 + aspect * aspect / 4, B = 2 * a, C = a * a - b * b;
  let w = (-B + Math.sqrt(B * B - 4 * A * C)) / (2 * A);
  let h = aspect * w;
  // keep the corners inside the base-angle limit
  const maxHalf = Math.tan(Math.min(thMaxDeg, 89) * DEG) * a;
  if (h / 2 > maxHalf) { h = 2 * maxHalf; w = h / aspect; }
  return { cx: a + w / 2, cy: 0, w, h };
}
