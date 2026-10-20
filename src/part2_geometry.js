/* ===================== GEOMETRY & PATH OPTIMISATION (pure functions) ===================== */
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Keep a target inside the arm's reachable space. After auto-calibration the reach is taken from the
// Magician geometry at the target's height (part 31); before that, from the reach band in Setup.
// Height is always kept between Z min (the paper) and Z max, and the base angle inside its limits.
function clampTarget(x, y, z) {
  if (![x, y, z].every(Number.isFinite)) throw new Error('Invalid target');
  const L = S.limits;
  const th = clamp(Math.atan2(y, x) * 180 / Math.PI, L.thMin, L.thMax) * Math.PI / 180;
  let r = Math.hypot(x, y);
  z = clamp(z, L.zMin, L.zMax);
  const band = S.model && S.model.ok && typeof reachAt === 'function' ? reachAt(S.model, z) : null;
  if (band) {
    const T = reachTable(S.model);
    z = clamp(z, T.zLo, T.zHi);
    r = clamp(r < 1e-6 ? band[0] : r, band[0] + 1, band[1] - 1);
  } else {
    r = clamp(r < 1e-6 ? L.minR : r, L.minR, L.maxR);
  }
  return { x: r * Math.cos(th), y: r * Math.sin(th), z };
}

// Ramer–Douglas–Peucker simplification: removes points that deviate less than eps (mm).
function rdp(pts, eps) {
  if (pts.length < 3) return pts.slice();
  const keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    const A = pts[a], B = pts[b];
    const dx = B.x - A.x, dy = B.y - A.y, len = Math.hypot(dx, dy);
    let maxD = 0, idx = -1;
    for (let i = a + 1; i < b; i++) {
      const P = pts[i];
      const d = len === 0 ? Math.hypot(P.x - A.x, P.y - A.y)
                          : Math.abs(dy * (P.x - A.x) - dx * (P.y - A.y)) / len;
      if (d > maxD) { maxD = d; idx = i; }
    }
    if (maxD > eps && idx > 0) { keep[idx] = 1; stack.push([a, idx], [idx, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}

function polyLength(pts) {
  let L = 0;
  for (let i = 1; i < pts.length; i++) L += dist(pts[i - 1], pts[i]);
  return L;
}

// Largest axis-aligned rectangle in front of the base that stays inside the reachable annulus
// (with margin). Rectangle spans x in [a, x1], y in [-h, h]. Corners set the constraints:
// inner edge at x=a keeps r>=minR; far corners (x1,±h) keep r<=maxR.
function maxReachRect(minR, maxR, margin) {
  const a = minR + margin, b = maxR - margin;
  let best = { area: 0, x0: a, x1: a, h: 0 };
  for (let x1 = a + 1; x1 <= b; x1 += 0.5) {
    const h = Math.sqrt(b * b - x1 * x1);
    if (!(h > 0)) break;
    const area = (x1 - a) * 2 * h;
    if (area > best.area) best = { area, x0: a, x1, h };
  }
  return best;
}

// Orders strokes to minimise pen-up travel: nearest-neighbour start, then 2-opt improvement
// (a stroke can be reversed if that shortens travel). Respects a time budget.
function orderStrokes(strokes, start, budgetMs) {
  const items = strokes.map(p => ({ pts: p, rev: false }));
  const sp = e => e.rev ? e.pts[e.pts.length - 1] : e.pts[0];
  const ep = e => e.rev ? e.pts[0] : e.pts[e.pts.length - 1];

  const seq = [];
  const rem = items.slice();
  let cur = start;
  while (rem.length) {
    let bi = -1, bd = Infinity, brev = false;
    for (let i = 0; i < rem.length; i++) {
      const e = rem[i];
      const d1 = dist(cur, e.pts[0]), d2 = dist(cur, e.pts[e.pts.length - 1]);
      if (d1 < bd) { bd = d1; bi = i; brev = false; }
      if (d2 < bd) { bd = d2; bi = i; brev = true; }
    }
    const e = rem[bi];
    rem[bi] = rem[rem.length - 1]; rem.pop();
    e.rev = brev;
    seq.push(e);
    cur = ep(e);
  }

  const t0 = Date.now();
  const n = seq.length;
  let improved = true;
  while (improved && Date.now() - t0 < budgetMs) {
    improved = false;
    for (let i = 0; i < n - 1 && Date.now() - t0 < budgetMs; i++) {
      const prevEnd = i === 0 ? start : ep(seq[i - 1]);
      for (let j = i + 1; j < n; j++) {
        const nextStart = j === n - 1 ? null : sp(seq[j + 1]);
        const before = dist(prevEnd, sp(seq[i])) + (nextStart ? dist(ep(seq[j]), nextStart) : 0);
        const after  = dist(prevEnd, ep(seq[j])) + (nextStart ? dist(sp(seq[i]), nextStart) : 0);
        if (before - after > 1e-6) {
          // reverse segment i..j and flip each stroke's direction
          for (let a = i, b = j; a < b; a++, b--) { const t = seq[a]; seq[a] = seq[b]; seq[b] = t; }
          for (let k = i; k <= j; k++) seq[k].rev = !seq[k].rev;
          improved = true;
        }
      }
    }
  }
  return seq;
}

// Converts ordered strokes into pen operations: {x,y,pen}. pen=true means drawing.
// Strokes closer than joinTol to the current position are joined without lifting.
function buildOps(seq, start, joinTol) {
  const ops = [];
  let cur = start, down = false;
  for (const e of seq) {
    const pts = e.rev ? e.pts.slice().reverse() : e.pts;
    const s = pts[0];
    if (down && dist(cur, s) <= joinTol) {
      ops.push({ x: s.x, y: s.y, pen: true });
    } else {
      if (down) { ops.push({ x: cur.x, y: cur.y, pen: false }); down = false; }
      ops.push({ x: s.x, y: s.y, pen: false });   // travel, pen up
      ops.push({ x: s.x, y: s.y, pen: true });    // lower pen in place
      down = true;
    }
    for (let k = 1; k < pts.length; k++) ops.push({ x: pts[k].x, y: pts[k].y, pen: true });
    cur = pts[pts.length - 1];
  }
  if (down) ops.push({ x: cur.x, y: cur.y, pen: false });
  return ops;
}

function opsStats(ops, start) {
  let draw = 0, travel = 0, lifts = 0, prev = start, wasDown = false;
  for (const op of ops) {
    const d = dist(prev, op);
    if (op.pen) draw += d; else travel += d;
    if (op.pen && !wasDown) lifts++;
    wasDown = op.pen;
    prev = op;
  }
  return { draw, travel, lifts, moves: ops.length };
}

// Maps SVG-space strokes into robot space, scaled uniformly to fit rect {cx,cy,w,h}.
// Convention: sketch "up" = robot +X (away from base), sketch "right" = robot -Y (viewed from behind the arm).
function mapToRobot(strokes, rect) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const s of strokes) for (const p of s) {
    if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
  }
  const bw = maxX - minX, bh = maxY - minY;
  // rect.w is the robot-X extent (sketch vertical), rect.h the robot-Y extent (sketch horizontal).
  const sc = Math.min(bw > 0 ? rect.h / bw : Infinity, bh > 0 ? rect.w / bh : Infinity);
  if (!Number.isFinite(sc)) return [];
  const ux = (minX + maxX) / 2, uy = (minY + maxY) / 2;
  return strokes.map(s => s.map(p => ({
    x: rect.cx - (p.y - uy) * sc,
    y: rect.cy - (p.x - ux) * sc,
  })));
}

// Resamples a polyline (with z) to n points evenly spaced by arc length.
function resampleTake(pts, n) {
  if (!pts.length) return [];
  if (pts.length === 1) return Array.from({ length: n }, () => ({ ...pts[0] }));
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + dist(pts[i - 1], pts[i]));
  const total = cum[cum.length - 1];
  const out = [];
  let j = 0;
  for (let k = 0; k < n; k++) {
    const t = total * k / (n - 1);
    while (j < pts.length - 2 && cum[j + 1] < t) j++;
    const seg = cum[j + 1] - cum[j];
    const u = seg > 0 ? clamp((t - cum[j]) / seg, 0, 1) : 0;
    const a = pts[j], b = pts[j + 1];
    out.push({ x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u, z: a.z + (b.z - a.z) * u });
  }
  return out;
}

// Learns a repeated movement: averages several takes point-by-point (after arc-length alignment).
// Returns mean path plus per-point spread and an overall consistency score (mm RMS).
function learnTakes(takes, n) {
  const R = takes.map(t => resampleTake(t, n));
  const mean = Array.from({ length: n }, (_, i) => {
    const m = { x: 0, y: 0, z: 0 };
    for (const r of R) { m.x += r[i].x; m.y += r[i].y; m.z += r[i].z; }
    return { x: m.x / R.length, y: m.y / R.length, z: m.z / R.length };
  });
  const spread = mean.map((m, i) => {
    let s = 0;
    for (const r of R) s += (r[i].x - m.x) ** 2 + (r[i].y - m.y) ** 2;
    return Math.sqrt(s / R.length);
  });
  const rms = spread.reduce((a, b) => a + b * b, 0) / n;
  return { mean, spread, consistency: Math.sqrt(rms) };
}

/* ---------- Placement & motion planning for the plotter (pure, unit-tested) ---------- */
function strokesBBox(strokes) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const s of strokes) for (const p of s) {
    if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
  }
  return { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

// Rotate the sketch by quarter turns (clockwise as seen on screen) and/or mirror it left↔right.
function orientStrokes(strokes, quarterTurns, mirror) {
  const b = strokesBBox(strokes), q = ((Math.round(quarterTurns) % 4) + 4) % 4;
  return strokes.map(s => s.map(p => {
    let x = p.x - b.cx, y = p.y - b.cy;
    if (mirror) x = -x;
    for (let k = 0; k < q; k++) { const t = x; x = -y; y = t; }
    return { x, y };
  }));
}

// Pen operations → robot commands. Pen-up travel and pen lifts are straight (MOVL) moves so the pen
// keeps its height; pen-down drawing uses continuous-path (CP) moves when opts.cp is set, so the arm
// does not stop at every point. Very short drawing segments are merged (opts.minSeg mm).
// opts.core: radius (mm) the pen-up travel must stay outside; longer hops follow the arc around it.
function plotCommands(ops, L, start, opts = {}) {
  const cmds = [], zU = L.zUp, zD = L.zDown, minSeg = opts.minSeg ?? 0.4;
  if (start && start.z < zU - 0.5) cmds.push({ x: start.x, y: start.y, z: zU, mode: 2 });
  let prev = start ? { x: start.x, y: start.y, pen: false } : null, lastDrawn = null;
  for (let i = 0; i < ops.length; i++) {
    const op = ops[i], next = ops[i + 1];
    const same = prev && Math.hypot(op.x - prev.x, op.y - prev.y) < 0.01;
    if (!op.pen) {
      if (opts.core && prev && !prev.pen) for (const w of arcWaypoints(prev, op, opts.core)) cmds.push({ x: w.x, y: w.y, z: zU, mode: 2 });
      cmds.push({ x: op.x, y: op.y, z: zU, mode: 2 });                    // lift or travel
      lastDrawn = null;
    } else if (prev && !prev.pen && same) {
      cmds.push({ x: op.x, y: op.y, z: zD, mode: 2 });                    // lower the pen
      lastDrawn = op;
    } else {
      const midStroke = next && next.pen;
      if (lastDrawn && midStroke && Math.hypot(op.x - lastDrawn.x, op.y - lastDrawn.y) < minSeg) { prev = op; continue; }
      cmds.push(opts.cp ? { kind: 'cp', x: op.x, y: op.y, z: zD, v: opts.speed ?? 30 } : { x: op.x, y: op.y, z: zD, mode: 2 });
      lastDrawn = op;
    }
    prev = op;
  }
  return cmds;
}
