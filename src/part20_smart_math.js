/* ===================== SMART: FILTERS, FACE & HAND MATH (pure, unit-tested) ===================== */

// One Euro filter (Casiez et al., CHI 2012): adaptive low-pass. Low speed → strong smoothing (less jitter);
// high speed → cutoff rises with |velocity| (less lag). Tune: lower minCutoff = less jitter, higher beta = less lag.
class OneEuro {
  constructor(minCutoff = 1.0, beta = 0.0, dCutoff = 1.0) {
    this.minCutoff = minCutoff; this.beta = beta; this.dCutoff = dCutoff;
    this.reset();
  }
  reset() { this.x = null; this.dx = 0; this.t = null; }
  static alpha(cutoff, dt) {
    const tau = 1 / (2 * Math.PI * cutoff);
    return 1 / (1 + tau / dt);
  }
  filter(x, t) {           // t in seconds
    if (this.x === null || this.t === null) { this.x = x; this.t = t; this.dx = 0; return x; }
    const dt = Math.max(1e-3, t - this.t);
    this.t = t;
    const rawDx = (x - this.x) / dt;
    this.dx += OneEuro.alpha(this.dCutoff, dt) * (rawDx - this.dx);
    const cutoff = this.minCutoff + this.beta * Math.abs(this.dx);
    this.x += OneEuro.alpha(cutoff, dt) * (x - this.x);
    return this.x;
  }
}

class OneEuroVec {
  constructor(n, minCutoff, beta, dCutoff) { this.f = Array.from({ length: n }, () => new OneEuro(minCutoff, beta, dCutoff)); }
  filter(v, t) { return v.map((x, i) => this.f[i].filter(x, t)); }
  reset() { this.f.forEach(f => f.reset()); }
  tune(minCutoff, beta) { this.f.forEach(f => { f.minCutoff = minCutoff; f.beta = beta; }); }
}

// Two-threshold switch. If onAt > offAt it turns on when the value rises; otherwise when it falls.
class Hyst {
  constructor(onAt, offAt) { this.onAt = onAt; this.offAt = offAt; this.on = false; }
  update(v) {
    if (this.onAt >= this.offAt) {
      if (!this.on && v >= this.onAt) this.on = true;
      else if (this.on && v <= this.offAt) this.on = false;
    } else {
      if (!this.on && v <= this.onAt) this.on = true;
      else if (this.on && v >= this.offAt) this.on = false;
    }
    return this.on;
  }
}

// A label must persist for holdMs before it is accepted. Returns {from,to} when it changes.
class StableLabel {
  constructor(holdMs, initial = 'none') { this.holdMs = holdMs; this.current = initial; this.cand = null; this.since = 0; }
  update(label, tMs) {
    if (label === this.current) { this.cand = null; return null; }
    if (label !== this.cand) { this.cand = label; this.since = tMs; return null; }
    if (tMs - this.since >= this.holdMs) {
      const from = this.current;
      this.current = label; this.cand = null;
      return { from, to: label };
    }
    return null;
  }
}

/* ---------- Face: blendshapes → expressions ---------- */
function blendshapeMap(categories) {
  const m = {};
  for (const c of categories || []) m[c.categoryName] = c.score;
  return m;
}

// Scores 0..1 per expression from MediaPipe's 52 facial blendshapes. If a neutral-face baseline is
// given, each blendshape is measured relative to the person's own resting face.
function expressionScores(bs, base) {
  const g = n => {
    const v = bs[n] || 0, b = base ? (base[n] || 0) : 0;
    return clamp((v - b) / Math.max(0.2, 1 - b), 0, 1);
  };
  const avg = (a, b) => (g(a) + g(b)) / 2;
  const smile = avg('mouthSmileLeft', 'mouthSmileRight');
  const frown = avg('mouthFrownLeft', 'mouthFrownRight');
  const browDown = avg('browDownLeft', 'browDownRight');
  const browUp = Math.max(g('browInnerUp'), avg('browOuterUpLeft', 'browOuterUpRight'));
  const eyeWide = avg('eyeWideLeft', 'eyeWideRight');
  const jaw = g('jawOpen');
  const sneer = avg('noseSneerLeft', 'noseSneerRight');
  const pucker = g('mouthPucker');
  const press = avg('mouthPressLeft', 'mouthPressRight');
  const squint = avg('cheekSquintLeft', 'cheekSquintRight');
  const surpriseGate = (jaw > 0.25 || eyeWide > 0.35) ? 1 : 0.5;
  return {
    happy: clamp(smile * 0.85 + squint * 0.25, 0, 1),
    surprised: clamp(jaw * 0.45 + browUp * 0.35 + eyeWide * 0.3, 0, 1) * surpriseGate,
    sad: clamp(frown * 0.6 + g('browInnerUp') * 0.35 + press * 0.15 - smile * 0.5, 0, 1),
    angry: clamp(browDown * 0.7 + sneer * 0.35 + press * 0.1 - smile * 0.4, 0, 1),
    kiss: clamp(pucker - jaw * 0.4 - smile * 0.3, 0, 1),
  };
}

const EXPR_THRESHOLDS = { happy: 0.45, surprised: 0.45, sad: 0.32, angry: 0.38, kiss: 0.5 };

// Picks the expression with the largest margin over its threshold. The current expression is kept
// until it falls below 75% of its threshold (hysteresis), so the label doesn't flicker.
function pickExpression(scores, th, current) {
  let best = 'neutral', bestMargin = 0;
  for (const k of Object.keys(scores)) {
    const t = th[k] ?? 0.5;
    const enter = k === current ? t * 0.75 : t;
    const margin = scores[k] - enter;
    if (margin > bestMargin) { bestMargin = margin; best = k; }
  }
  return best;
}

class ExpressionTracker {
  constructor(holdMs = 350) { this.stable = new StableLabel(holdMs, 'neutral'); this.th = { ...EXPR_THRESHOLDS }; this.scores = {}; }
  update(bs, base, tMs, sensitivity = 1) {
    this.scores = expressionScores(bs, base);
    const th = {};
    for (const k in this.th) th[k] = clamp(this.th[k] / sensitivity, 0.05, 0.95);
    const label = pickExpression(this.scores, th, this.stable.current);
    return this.stable.update(label, tMs);   // {from,to} or null
  }
  get current() { return this.stable.current; }
}

// One eye closed while the other stays open for 0.12–1.2 s = wink. Both closed = ordinary blink.
class WinkDetector {
  constructor() { this.state = 'open'; this.start = 0; this.coolUntil = 0; }
  update(blinkL, blinkR, tMs) {
    const cL = blinkL > 0.55, cR = blinkR > 0.55, oL = blinkL < 0.35, oR = blinkR < 0.35;
    if (this.state === 'open') {
      if (cL && oR) { this.state = 'L'; this.start = tMs; }
      else if (cR && oL) { this.state = 'R'; this.start = tMs; }
      else if (cL && cR) this.state = 'blink';
      return null;
    }
    if (this.state === 'blink') { if (oL && oR) this.state = 'open'; return null; }
    if ((this.state === 'L' && cR) || (this.state === 'R' && cL)) { this.state = 'blink'; return null; }
    const stillClosed = this.state === 'L' ? cL : cR;
    if (stillClosed) return null;
    const side = this.state === 'L' ? 'left' : 'right';
    const d = tMs - this.start;
    this.state = 'open';
    if (d >= 120 && d <= 1200 && tMs >= this.coolUntil) { this.coolUntil = tMs + 1000; return side; }
    return null;
  }
}

/* ---------- Face: head pose & nod/shake ---------- */
// Head orientation from face-mesh landmarks (indices: 1 nose tip, 234/454 face sides, 10 forehead,
// 152 chin, 33/263 outer eye corners). aspect = video width / height, to measure in square units.
function headPose(lm, aspect = 4 / 3) {
  const P = i => ({ x: lm[i].x * aspect, y: lm[i].y });
  const nose = P(1), L = P(234), R = P(454), top = P(10), chin = P(152), eL = P(33), eR = P(263);
  const faceW = Math.hypot(R.x - L.x, R.y - L.y) || 1e-6;
  const faceH = Math.hypot(chin.x - top.x, chin.y - top.y) || 1e-6;
  const yaw = (nose.x - (L.x + R.x) / 2) / faceW;     // + nose toward image right
  const pitch = (nose.y - (top.y + chin.y) / 2) / faceH; // + looking down
  const roll = Math.atan2(eR.y - eL.y, eR.x - eL.x);
  return { yaw, pitch, roll, cx: (L.x + R.x) / 2 / aspect, cy: (top.y + chin.y) / 2, size: faceW / aspect };
}

// Detects a "yes" nod (pitch swings) or "no" shake (yaw swings) within a short window.
class HeadGestureDetector {
  constructor(opts = {}) { this.win = opts.windowMs ?? 1300; this.amp = opts.amp ?? 0.03; this.buf = []; this.coolUntil = 0; }
  _swings(key) {
    const vals = this.buf.map(b => b[key]);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    let level = 0, changes = 0, lo = Infinity, hi = -Infinity;
    for (const v0 of vals) {
      const v = v0 - mean;
      lo = Math.min(lo, v); hi = Math.max(hi, v);
      const lv = v > this.amp ? 1 : v < -this.amp ? -1 : level;
      if (lv !== level) { if (level !== 0) changes++; level = lv; }
    }
    return { changes, p2p: hi - lo };
  }
  update(tMs, yaw, pitch) {
    this.buf.push({ t: tMs, yaw, pitch });
    while (this.buf.length && tMs - this.buf[0].t > this.win) this.buf.shift();
    if (tMs < this.coolUntil || this.buf.length < 8) return null;
    const p = this._swings('pitch'), y = this._swings('yaw');
    if (p.changes >= 2 && p.p2p > 2 * this.amp && p.p2p > 1.6 * y.p2p) { this.coolUntil = tMs + 1500; this.buf = []; return 'nod'; }
    if (y.changes >= 2 && y.p2p > 2 * this.amp && y.p2p > 1.6 * p.p2p) { this.coolUntil = tMs + 1500; this.buf = []; return 'shake'; }
    return null;
  }
}

/* ---------- Hands & body → robot targets ---------- */
// Hand size (palm) and pinch ratio (thumb tip to index tip, relative to palm) from 21 hand landmarks.
function handMetrics(lm, aspect = 4 / 3) {
  const P = i => ({ x: lm[i].x * aspect, y: lm[i].y });
  const d = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const palm = (d(P(0), P(9)) + d(P(5), P(17))) / 2 || 1e-6;
  return { palm, pinch: d(P(4), P(8)) / palm, cx: lm[9].x, cy: lm[9].y, tipX: lm[8].x, tipY: lm[8].y };
}

// The box the smart modes move in, derived from the calibrated limits (stays well inside them).
function smartBox(L) {
  const xMid = (L.minR + L.maxR) / 2, xHalf = (L.maxR - L.minR) / 2 * 0.8;
  const thHalf = Math.min(Math.abs(L.thMin), Math.abs(L.thMax), 60) * Math.PI / 180;
  const yHalf = Math.max(20, xMid * Math.sin(thHalf) * 0.8);
  const zMid = (L.zMin + L.zMax) / 2, zHalf = (L.zMax - L.zMin) / 2 * 0.8;
  return { xMid, xHalf, yHalf, zMid, zHalf };
}

// Hand mirror. Raw camera coordinates (not mirrored). When the robot faces you, moving your hand to
// your right moves the tip to your right (robot +Y); up = up; hand toward the camera = reach toward you.
function mapHandFront(m, cal, L, opts = {}) {
  const B = smartBox(L);
  const half = (opts.span ?? 0.5) / 2;
  const ux = (cal.cx - m.cx) / half;
  const uy = (cal.cy - m.cy) / half;
  const depth = cal.palm > 0 ? (m.palm / cal.palm - 1) / (opts.depthGain ?? 0.6) : 0;
  const side = opts.facing === false ? -1 : 1;
  return {
    x: B.xMid + clamp(depth, -1, 1) * B.xHalf,
    y: clamp(ux, -1, 1) * side * B.yHalf,
    z: B.zMid + clamp(uy, -1, 1) * B.zHalf,
  };
}

// Air drawing: index fingertip → point in the plotter's drawing area. Same orientation as the
// Plotter preview (sketch right = robot -Y, sketch up = robot +X). Uniform scale keeps circles round.
function mapHandToRect(m, cal, rect, opts = {}) {
  const span = opts.span ?? 0.5;
  const k = Math.min(rect.w, rect.h);
  const u = clamp((cal.cx - m.tipX) / span, -0.5, 0.5);   // user's right +
  const v = clamp((cal.cy - m.tipY) / span, -0.5, 0.5);   // up +
  return { x: rect.cx + v * k, y: rect.cy - u * k };
}

// Arm mirror from body pose (33 landmarks). Your shoulder→wrist direction steers the tip:
// sideways = left/right, up/down = height, wrist toward the camera = reach forward.
function mapArmPose(lm, wl, side, L, opts = {}) {
  const [iS, iE, iW] = side === 'left' ? [11, 13, 15] : [12, 14, 16];
  const s = lm && lm[iS], e = lm && lm[iE], w = lm && lm[iW];
  if (!s || !e || !w) return null;
  const vis = Math.min(s.visibility ?? 1, e.visibility ?? 1, w.visibility ?? 1);
  if (vis < 0.5) return null;
  const aspect = opts.aspect ?? 4 / 3;
  const d = (a, b) => Math.hypot((a.x - b.x) * aspect, a.y - b.y);
  const len = d(s, e) + d(e, w) || 1e-6;
  const hx = ((w.x - s.x) * aspect) / len;   // + toward image right (your left)
  const hy = (s.y - w.y) / len;              // + wrist above shoulder
  let depth = 0;
  if (wl && wl[iS] && wl[iE] && wl[iW]) {
    const D = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
    const wlen = D(wl[iS], wl[iE]) + D(wl[iE], wl[iW]) || 1e-6;
    depth = (wl[iS].z - wl[iW].z) / wlen;   // + wrist nearer the camera than the shoulder
  }
  const B = smartBox(L);
  const sideSign = opts.facing === false ? -1 : 1;
  return {
    x: B.xMid + clamp(depth * 1.6, -1, 1) * B.xHalf,
    y: clamp(-hx, -1, 1) * sideSign * B.yHalf,
    z: B.zMid + clamp(hy, -1, 1) * B.zHalf,
    vis,
  };
}
