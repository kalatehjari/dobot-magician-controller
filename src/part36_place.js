/* ===================== FREE PLACEMENT ON THE PAPER (pure, unit-tested) ===================== */
// A drawing is placed by its centre (robot mm), its size (longest side, mm), a rotation (degrees,
// clockwise as seen on screen) and an optional left↔right mirror. Sketch "up" points away from the
// base (robot +X) and sketch "right" is robot −Y, so the preview matches the paper seen from behind
// the arm.
// The green zone is where the pen can reach at every height between pen-down and pen-up, less a
// safety margin: an annular sector {rIn ≤ r ≤ rOut, thMin ≤ θ ≤ thMax}. Every drawn line must lie in
// it, including the middle of long straight lines, which can cut in towards the base.

let SKETCH_SEQ = 0;
const RAD = Math.PI / 180;

function convexHull(pts) {
  const P = pts.map(p => ({ x: p.x, y: p.y })).sort((a, b) => a.x - b.x || a.y - b.y);
  if (P.length < 3) return P;
  const cr = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lo = [], up = [];
  for (const p of P) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
  for (let i = P.length - 1; i >= 0; i--) {
    const p = P[i];
    while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop();
    up.push(p);
  }
  lo.pop(); up.pop();
  return lo.concat(up);
}

// Squared shortest distance from the base (origin) to the segment a–b.
function segDist0Sq(ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
  let t = L2 > 0 ? -(ax * dx + ay * dy) / L2 : 0;
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  const x = ax + t * dx, y = ay + t * dy;
  return x * x + y * y;
}
const segDist0 = (ax, ay, bx, by) => Math.sqrt(segDist0Sq(ax, ay, bx, by));

// Normalises a drawing: centred on its bounding box, longest side = 1. Keeps fast stand-ins for the
// checks: the convex hull (exact for the outer edge and the side limits, which are convex) and a
// lightly simplified copy (within eps) for the inner edge, which is checked with eps extra clearance.
function prepareSketch(strokes, source) {
  const b = strokesBBox(strokes), L = Math.max(b.w, b.h) || 1;
  const unit = strokes.map(s => s.map(p => ({ x: (p.x - b.cx) / L, y: (p.y - b.cy) / L })));
  const all = [];
  for (const s of unit) for (const p of s) all.push(p);
  const eps = 0.002;
  return {
    id: ++SKETCH_SEQ, source: source || null, strokes: unit, w: b.w / L, h: b.h / L,
    srcBox: { cx: b.cx, cy: b.cy, L }, hull: convexHull(all), decim: unit.map(s => rdp(s, eps)), eps, points: all.length,
  };
}

// Linear part of a placement (mirror, rotation, sketch → robot axes) for a drawing of size 1.
function placeLinear(angleDeg, mirror) {
  const a = angleDeg * RAD, c = Math.cos(a), s = Math.sin(a), m = mirror ? -1 : 1;
  return p => { const x = p.x * m, y = p.y; return { x: -(x * s + y * c), y: -(x * c - y * s) }; };
}
function placeXform(pl) {
  const lin = placeLinear(pl.angle, pl.mirror), k = pl.size;
  return p => { const v = lin(p); return { x: pl.cx + k * v.x, y: pl.cy + k * v.y }; };
}
function placeInverse(pl) {
  const a = pl.angle * RAD, c = Math.cos(a), s = Math.sin(a), m = pl.mirror ? -1 : 1, k = pl.size || 1;
  return q => {
    const yr = (pl.cx - q.x) / k, xr = (pl.cy - q.y) / k;
    return { x: (xr * c + yr * s) * m, y: -xr * s + yr * c };
  };
}
// Corners of the drawing's own box (top-left, top-right, bottom-right, bottom-left), in robot mm.
function placeFrame(sk, pl) {
  const f = placeXform(pl), hw = sk.w / 2, hh = sk.h / 2;
  return [f({ x: -hw, y: -hh }), f({ x: hw, y: -hh }), f({ x: hw, y: hh }), f({ x: -hw, y: hh })];
}

function zoneHas(z, x, y) {
  const r = Math.hypot(x, y), th = Math.atan2(y, x) / RAD;
  return r >= z.rIn && r <= z.rOut && th >= z.thMin && th <= z.thMax;
}
const zoneKey = z => [z.rIn, z.rOut, z.thMin, z.thMax].map(v => v.toFixed(2)).join('|') + (z.pq ? '|' + (z.margin || 0) + '|' + z.polyKey : '');
// Clearance from the edges of the safe-zone polygon (part 53): the margin, the simplification
// tolerance and the stand-in lines' error at this size.
const polyGap = (P, s, z, pad) => (z.margin || 0) + pad + P.eps * s;

// The drawing turned for one rotation (size 1, centre 0), reused while only position and size change.
// Lines are cut into short chunks with their own boxes, so the inner-edge check skips everything
// that is clearly away from the base.
function placementProbe(sk, angle, mirror) {
  const lin = placeLinear(angle, mirror), CH = 24, chunks = [];
  for (const s of sk.decim) {
    const pts = s.map(lin), n = pts.length;
    for (let i0 = 0; i0 < Math.max(1, n - 1); i0 += CH) {
      const i1 = Math.min(n - 1, i0 + CH), a = new Float64Array((i1 - i0 + 1) * 2);
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (let i = i0; i <= i1; i++) {
        const p = pts[i]; a[2 * (i - i0)] = p.x; a[2 * (i - i0) + 1] = p.y;
        if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x; if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
      }
      chunks.push({ a, minX, minY, maxX, maxY });
    }
  }
  return { angle, mirror, eps: sk.eps, hull: sk.hull.map(lin), chunks };
}

// Inner edge: every simplified line keeps eps × size (+ pad) more than rIn from the base.
function innerClear(P, cx, cy, s, z, pad = 0) {
  const R = z.rIn + P.eps * s + pad, R2 = R * R;
  for (const c of P.chunks) {
    const x0 = cx + s * c.minX, x1 = cx + s * c.maxX, y0 = cy + s * c.minY, y1 = cy + s * c.maxY;
    const px = x0 > 0 ? x0 : x1 < 0 ? x1 : 0, py = y0 > 0 ? y0 : y1 < 0 ? y1 : 0;
    if (px * px + py * py >= R2) continue;                 // the whole chunk is clear of the base
    const a = c.a;
    let ax = cx + s * a[0], ay = cy + s * a[1];
    if (a.length === 2) { if (ax * ax + ay * ay < R2) return false; continue; }
    for (let i = 2; i < a.length; i += 2) {
      const bx = cx + s * a[i], by = cy + s * a[i + 1];
      if (segDist0Sq(ax, ay, bx, by) < R2) return false;
      ax = bx; ay = by;
    }
  }
  return true;
}

// Does the drawing fit at centre (cx, cy) with size s? Outer edge and side limits from the hull,
// inner edge from the lines.
function probeFits(P, cx, cy, s, z, pad = 0) {
  if (!(s > 0) || ![cx, cy].every(Number.isFinite)) return false;
  const Ro2 = z.rOut * z.rOut + 1e-9;
  const a0 = z.thMin * RAD, a1 = z.thMax * RAD, d0x = Math.cos(a0), d0y = Math.sin(a0), d1x = Math.cos(a1), d1y = Math.sin(a1);
  for (const u of P.hull) {
    const x = cx + s * u.x, y = cy + s * u.y;
    if (x * x + y * y > Ro2) return false;
    if (d0x * y - d0y * x < -1e-9 || d1x * y - d1y * x > 1e-9) return false;
  }
  return innerClear(P, cx, cy, s, z, pad) && (!z.pq || polyClear(P, cx, cy, s, z.pq, polyGap(P, s, z, pad)));
}

// Upper bound on the size at a centre, from the hull points: outer edge and side limits (exact), and
// the inner edge, which no drawing point may cross on the way out from the centre.
function hullSizeBound(P, cx, cy, z, pad = 0) {
  const Ro2 = z.rOut * z.rOut, cc = cx * cx + cy * cy, Ri = z.rIn + pad, Ri2 = Ri * Ri;
  if (cc > Ro2 || cc < Ri2) return 0;
  const a0 = z.thMin * RAD, a1 = z.thMax * RAD, d0x = Math.cos(a0), d0y = Math.sin(a0), d1x = Math.cos(a1), d1y = Math.sin(a1);
  const c0 = d0x * cy - d0y * cx, c1 = d1x * cy - d1y * cx;
  if (c0 < 0 || c1 > 0) return 0;
  let s = Infinity;
  for (const u of P.hull) {
    const uu = u.x * u.x + u.y * u.y;
    if (uu < 1e-18) continue;
    const cu = cx * u.x + cy * u.y;
    s = Math.min(s, (-cu + Math.sqrt(Math.max(0, cu * cu - uu * (cc - Ro2)))) / uu);
    if (cu < 0) { const disc = cu * cu - uu * (cc - Ri2); if (disc > 0) s = Math.min(s, (-cu - Math.sqrt(disc)) / uu); }
    const k0 = d0x * u.y - d0y * u.x; if (k0 < 0) s = Math.min(s, c0 / -k0);
    const k1 = d1x * u.y - d1y * u.x; if (k1 > 0) s = Math.min(s, -c1 / k1);
  }
  return Number.isFinite(s) ? s : 0;
}

// Distance from the base to the drawing's outline (its convex hull, filled) at size s; 0 if it covers the base.
function hullDist0(P, cx, cy, s) {
  const H = P.hull, n = H.length;
  if (!n) return Infinity;
  let best = Infinity, sign = 0, inside = n >= 3;
  for (let i = 0; i < n; i++) {
    const a = H[i], b = H[(i + 1) % n];
    const ax = cx + s * a.x, ay = cy + s * a.y, bx = cx + s * b.x, by = cy + s * b.y;
    const d = n === 1 ? ax * ax + ay * ay : segDist0Sq(ax, ay, bx, by);
    if (d < best) best = d;
    const cr = ax * by - ay * bx;
    if (cr !== 0) { const sg = cr > 0 ? 1 : -1; if (!sign) sign = sg; else if (sg !== sign) inside = false; }
  }
  return inside ? 0 : Math.sqrt(best);
}

// Largest size that fits at a given centre — and at every smaller size too. A drawing with a gap can
// fit large with the area round the base sitting inside the gap, yet not fit a little smaller, when
// one of its lines crosses that area; so the base area is kept outside the drawing's outline, which
// (unlike the lines alone) only ever gets closer to the base as the drawing grows.
function maxSizeAt(P, cx, cy, z, pad = 0) {
  let ub = Math.min(hullSizeBound(P, cx, cy, z, pad), 2000);
  if (!(ub > 0)) return 0;
  if (!innerClear(P, cx, cy, 0, z, pad)) return 0;
  if (z.pq) {
    if (!polyClear(P, cx, cy, 0, z.pq, polyGap(P, 0, z, pad))) return 0;
    ub = Math.min(ub, polyBoxBound(P, cx, cy, z.pq));
    if (!(ub > 0)) return 0;
  }
  let s = ub;
  if (!innerClear(P, cx, cy, ub, z, pad)) {
    let lo = 0, hi = ub;
    for (let it = 0; it < 30 && hi - lo > 0.02; it++) {
      const m = (lo + hi) / 2;
      if (innerClear(P, cx, cy, m, z, pad)) lo = m; else hi = m;
    }
    s = lo;
  }
  const R = t => z.rIn + P.eps * t + pad;
  if (hullDist0(P, cx, cy, s) < R(s)) {
    let lo = 0, hi = s;
    for (let it = 0; it < 30 && hi - lo > 0.02; it++) {
      const m = (lo + hi) / 2;
      if (hullDist0(P, cx, cy, m) >= R(m) && innerClear(P, cx, cy, m, z, pad)) lo = m; else hi = m;
    }
    s = lo;
  }
  if (z.pq && s > 0 && !polyClear(P, cx, cy, s, z.pq, polyGap(P, s, z, pad))) {   // the safe zone: the largest size that fits it
    let lo = 0, hi = s;
    for (let it = 0; it < 30 && hi - lo > 0.02; it++) {
      const m = (lo + hi) / 2;
      if (polyClear(P, cx, cy, m, z.pq, polyGap(P, m, z, pad)) && hullDist0(P, cx, cy, m) >= R(m) && innerClear(P, cx, cy, m, z, pad)) lo = m; else hi = m;
    }
    s = lo;
  }
  return s;
}

// Upper bound on the size from the safe zone's box: the outline's corners are points of the drawing.
function polyBoxBound(P, cx, cy, pp) {
  let s = Infinity;
  for (const u of P.hull) {
    if (u.x > 1e-12) s = Math.min(s, (pp.maxX - cx) / u.x); else if (u.x < -1e-12) s = Math.min(s, (pp.minX - cx) / u.x);
    if (u.y > 1e-12) s = Math.min(s, (pp.maxY - cy) / u.y); else if (u.y < -1e-12) s = Math.min(s, (pp.minY - cy) / u.y);
  }
  return Number.isFinite(s) ? Math.max(0, s) : 2000;
}

// Largest size for this rotation, and where it goes. centreLine keeps the centre on the arm's
// forward axis (y = 0). A coarse polar grid ranked by the cheap hull bound, then a pattern search.
function bestPlacement(P, z, opts = {}) {
  const pad = opts.pad || 0, nR = 18, rs = (z.rOut - z.rIn) / nR;
  if (!(rs > 0)) return null;
  const phis = [0];
  if (!opts.centreLine) {
    for (let a = 3; a <= z.thMax - 1; a += 3) phis.push(a);
    for (let a = -3; a >= z.thMin + 1; a -= 3) phis.push(a);
  }
  const cands = [], pq = z.pq;
  const add = (cx, cy, ph) => {
    if (pq && !polyHas(pq, cx, cy)) return;
    let ub = hullSizeBound(P, cx, cy, z, pad);
    if (pq && ub > 0) ub = Math.min(ub, polyBoxBound(P, cx, cy, pq));
    if (ub > 0) cands.push({ cx, cy, ub, ph });
  };
  for (const ph of phis) for (let i = 0; i <= nR; i++) {
    const r = z.rIn + i * rs;
    add(r * Math.cos(ph * RAD), r * Math.sin(ph * RAD), ph);
  }
  if (pq) {                                  // a grid over the safe zone, so a small zone has candidates too
    const n = 14, dx = (pq.maxX - pq.minX) / n, dy = (pq.maxY - pq.minY) / n;
    for (let i = 0; i <= n; i++) {
      const cx = pq.minX + i * dx;
      if (opts.centreLine) { add(cx, 0, 0); continue; }
      for (let j = 0; j <= n; j++) { const cy = pq.minY + j * dy; add(cx, cy, Math.atan2(cy, cx) / RAD); }
    }
  }
  cands.sort((a, b) => b.ub - a.ub || Math.abs(a.ph) - Math.abs(b.ph));
  let best = null;
  for (const c of cands) {
    if (best && c.ub <= best.size + 1e-6) break;
    const s = maxSizeAt(P, c.cx, c.cy, z, pad);
    if (s > 0 && (!best || s > best.size + 1e-6)) best = { cx: c.cx, cy: c.cy, size: s };
  }
  if (!best) return null;
  const dirs = opts.centreLine ? [[1, 0], [-1, 0]]
    : [[1, 0], [-1, 0], [0, 1], [0, -1], [0.7071, 0.7071], [0.7071, -0.7071], [-0.7071, 0.7071], [-0.7071, -0.7071]];
  let step = rs / 2;
  for (let guard = 0; step > 0.05 && guard < 600; guard++) {
    let moved = false;
    for (const [dx, dy] of dirs) {
      const cx = best.cx + dx * step, cy = best.cy + dy * step, s = maxSizeAt(P, cx, cy, z, pad);
      if (s > best.size + 1e-4) { best = { cx, cy, size: s }; moved = true; break; }
    }
    if (!moved) step /= 2;
  }
  return best;
}

// Furthest point from a (fits) towards b along the straight line, using fits(x, y).
function walkToward(a, b, fits, iters = 22) {
  let lo = 0, hi = 1;
  if (fits(b.x, b.y)) return { x: b.x, y: b.y };
  for (let it = 0; it < iters; it++) {
    const m = (lo + hi) / 2;
    if (fits(a.x + (b.x - a.x) * m, a.y + (b.y - a.y) * m)) lo = m; else hi = m;
  }
  return { x: a.x + (b.x - a.x) * lo, y: a.y + (b.y - a.y) * lo };
}

// A placement that fits, as close as possible to the one asked for: same rotation; the same spot if
// it fits there; otherwise moved towards the roomiest spot just far enough; smaller only if it cannot
// fit anywhere at that size. targets: optional precomputed [bestPlacement centreLine, bestPlacement].
function fixPlacement(sk, pl, z, opts = {}) {
  const pad = opts.pad || 0;
  const P = opts.probe || placementProbe(sk, pl.angle, pl.mirror);
  if (probeFits(P, pl.cx, pl.cy, pl.size, z, pad)) return { ...pl, fixed: false };
  const targets = (opts.targets || [bestPlacement(P, z, { centreLine: true, pad }), bestPlacement(P, z, { pad })]).filter(Boolean);
  if (!targets.length) return null;
  const anyMax = Math.max(...targets.map(t => t.size));
  const size = Math.max(0.5, Math.min(pl.size, anyMax * 0.999));
  for (const t of targets) {
    if (t.size < size || !probeFits(P, t.cx, t.cy, size, z, pad)) continue;
    let lo = 0, hi = 1;                       // walk from the asked-for centre: fits at hi, not at lo
    for (let it = 0; it < 30; it++) {
      const m = (lo + hi) / 2;
      if (probeFits(P, pl.cx + (t.cx - pl.cx) * m, pl.cy + (t.cy - pl.cy) * m, size, z, pad)) hi = m; else lo = m;
    }
    return { ...pl, cx: pl.cx + (t.cx - pl.cx) * hi, cy: pl.cy + (t.cy - pl.cy) * hi, size, fixed: true, shrunk: size < pl.size - 1e-6 };
  }
  return null;
}

// Dragging: go as far towards the pointer as the zone allows, then slide along the zone's edge
// (along the arc, or straight towards/away from the base) for the rest of the move.
function constrainMove(P, from, to, size, z, pad = 0) {
  const fits = (x, y) => probeFits(P, x, y, size, z, pad);
  if (fits(to.x, to.y)) return { x: to.x, y: to.y };
  if (!fits(from.x, from.y)) return { x: from.x, y: from.y };
  const p1 = walkToward(from, to, fits);
  const rx = to.x - p1.x, ry = to.y - p1.y, rl = Math.hypot(rx, ry);
  let best = p1, bd = rl;
  if (rl < 1e-6) return best;
  // slide: the rest of the move, turned by up to ±90° so it runs along whatever edge stopped it
  for (const deg of [15, -15, 30, -30, 45, -45, 60, -60, 75, -75, 90, -90]) {
    const a = deg * RAD, c = Math.cos(a), s = Math.sin(a), k = Math.cos(a);   // shorter as it turns away
    const q = walkToward(p1, { x: p1.x + (rx * c - ry * s) * k, y: p1.y + (rx * s + ry * c) * k }, fits, 14);
    const d = Math.hypot(to.x - q.x, to.y - q.y);
    if (d < bd - 1e-6) { best = q; bd = d; }
  }
  return best;
}

// Pen-up moves are straight lines. One that would cut across the unreachable area near the base is
// split into short steps that follow the arc instead (radius and angle change evenly).
function arcWaypoints(a, b, core, maxStepDeg = 4) {
  if (!(core > 0) || segDist0(a.x, a.y, b.x, b.y) >= core) return [];
  const ra = Math.hypot(a.x, a.y), rb = Math.hypot(b.x, b.y), ta = Math.atan2(a.y, a.x), tb = Math.atan2(b.y, b.x);
  const n = Math.max(2, Math.ceil(Math.abs(tb - ta) / (maxStepDeg * RAD)));
  const out = [];
  for (let i = 1; i < n; i++) {
    const t = i / n, r = Math.max(core + 0.5, ra + (rb - ra) * t), th = ta + (tb - ta) * t;
    out.push({ x: r * Math.cos(th), y: r * Math.sin(th) });
  }
  return out;
}

// Closest point on segment a–b (3-D) to p: distance and position along the segment (0…1).
function projectOnSeg3(a, b, p) {
  const dx = b.x - a.x, dy = b.y - a.y, dz = (b.z ?? 0) - (a.z ?? 0), L2 = dx * dx + dy * dy + dz * dz;
  let t = L2 > 0 ? ((p.x - a.x) * dx + (p.y - a.y) * dy + ((p.z ?? 0) - (a.z ?? 0)) * dz) / L2 : 1;
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  return { t, d: Math.hypot(a.x + t * dx - p.x, a.y + t * dy - p.y, (a.z ?? 0) + t * dz - (p.z ?? 0)) };
}
