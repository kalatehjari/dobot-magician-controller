/* ===================== SHADING: hatch lines inside closed shapes (pure, unit-tested) =====================
   Works in the drawing's own units (the sketch: centred, longest side 1, y down like SVG). A shading
   target is a set of rings (closed polylines, first point not repeated) with a fill rule. Hatch lines
   run at an angle as seen on screen (0° = horizontal, 90° = vertical, 45° = rising to the right), a
   spacing apart, on one grid for the whole drawing, between the points where they cross the target's
   edges.
   Targets come either from the SVG's filled shapes (in paint order: a later shape hides the lines of
   the shapes under it; darker colours can get denser lines), or from every closed outline, where the
   outlines directly inside one cut holes in it, so nested shapes are shaded separately. */

function ringArea(r) {
  let a = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += r[j].x * r[i].y - r[i].x * r[j].y;
  return a / 2;
}
function ringBox(r) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of r) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; }
  return { x0, y0, x1, y1 };
}
const boxUnion = (a, b) => ({ x0: Math.min(a.x0, b.x0), y0: Math.min(a.y0, b.y0), x1: Math.max(a.x1, b.x1), y1: Math.max(a.y1, b.y1) });
const boxOverlap = (a, b) => a.x0 <= b.x1 && b.x0 <= a.x1 && a.y0 <= b.y1 && b.y0 <= a.y1;
const boxInside = (i, o) => i.x0 >= o.x0 && i.x1 <= o.x1 && i.y0 >= o.y0 && i.y1 <= o.y1;

// Is p inside these rings by the fill rule? (crossings of a ray to the right)
function pointInRings(p, rings, rule = 'evenodd') {
  let w = 0, n = 0;
  for (const r of rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const a = r[j], b = r[i];
    if ((a.y <= p.y) !== (b.y <= p.y)) {
      const x = a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y);
      if (x > p.x) { n++; w += b.y > a.y ? 1 : -1; }
    }
  }
  return rule === 'nonzero' ? w !== 0 : (n & 1) === 1;
}

// Open strokes that meet end to end (within eps) and close a loop, as point lists. Outlines are
// often drawn in several pieces; joined, they shade like one closed shape.
function chainLoops(strokes, eps) {
  const open = [];
  for (const s of strokes) if (s && s.length >= 2 && Math.hypot(s[0].x - s[s.length - 1].x, s[0].y - s[s.length - 1].y) > eps) open.push(s);
  if (open.length < 2) return [];
  const cell = p => `${Math.floor(p.x / eps)},${Math.floor(p.y / eps)}`, grid = new Map();
  const put = (p, i, end) => { const k = cell(p); if (!grid.has(k)) grid.set(k, []); grid.get(k).push({ i, end }); };
  open.forEach((s, i) => { put(s[0], i, 0); put(s[s.length - 1], i, 1); });
  const used = new Array(open.length).fill(false), loops = [];
  const near = p => {
    const gx = Math.floor(p.x / eps), gy = Math.floor(p.y / eps), out = [];
    for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (const c of grid.get(`${gx + dx},${gy + dy}`) || []) out.push(c);
    return out;
  };
  for (let i = 0; i < open.length; i++) {
    if (used[i]) continue;
    used[i] = true;
    let chain = open[i].slice();
    const start = chain[0];
    for (let guard = 0; guard < open.length; guard++) {
      const end = chain[chain.length - 1];
      if (chain.length > 3 && Math.hypot(end.x - start.x, end.y - start.y) <= eps) break;
      let next = null;
      for (const c of near(end)) {
        if (used[c.i]) continue;
        const s = open[c.i], q = c.end ? s[s.length - 1] : s[0];
        if (Math.hypot(q.x - end.x, q.y - end.y) <= eps) { next = c; break; }
      }
      if (!next) break;
      used[next.i] = true;
      const s = open[next.i];
      chain = chain.concat(next.end ? s.slice(0, -1).reverse() : s.slice(1));
    }
    const end = chain[chain.length - 1];
    if (chain.length > 3 && Math.hypot(end.x - start.x, end.y - start.y) <= eps) loops.push(chain);
  }
  return loops;
}

// Closed outlines as rings (no repeated end point): strokes whose ends meet (within eps), and loops
// made of several pieces that meet end to end.
function closedRings(strokes, eps = 0.002) {
  const out = [];
  const add = (s, i) => {
    if (!s || s.length < 3) return;
    const a = s[0], b = s[s.length - 1];
    if (Math.hypot(a.x - b.x, a.y - b.y) > eps) return;
    const pts = Math.hypot(a.x - b.x, a.y - b.y) < 1e-12 ? s.slice(0, -1) : s.slice();
    if (pts.length < 3) return;
    const area = Math.abs(ringArea(pts));
    if (!(area > 1e-7)) return;
    out.push({ pts, area, box: ringBox(pts), stroke: i });
  };
  strokes.forEach(add);
  for (const loop of chainLoops(strokes, Math.max(eps, 0.0025))) add(loop, -1);
  return out;
}

function ringCentroid(r) {
  let a = 0, cx = 0, cy = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const f = r[j].x * r[i].y - r[i].x * r[j].y;
    a += f; cx += (r[j].x + r[i].x) * f; cy += (r[j].y + r[i].y) * f;
  }
  if (Math.abs(a) < 1e-15) { const b = ringBox(r); return { x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2 }; }
  return { x: cx / (3 * a), y: cy / (3 * a) };
}

// Every closed outline becomes a target: the inside of the ring minus the rings directly inside it.
// depth 0 = outermost. Targets are numbered by depth, then top to bottom, left to right.
function outlineTargets(strokes, eps = 0.002) {
  const rings = closedRings(strokes, eps);
  const bySize = rings.map((_, i) => i).sort((a, b) => rings[a].area - rings[b].area);
  for (let ii = 0; ii < bySize.length; ii++) {
    const r = rings[bySize[ii]], s1 = r.pts[0], s2 = r.pts[Math.floor(r.pts.length / 2)];
    r.parent = -1;
    for (let jj = ii + 1; jj < bySize.length; jj++) {              // only bigger rings, smallest first
      const q = rings[bySize[jj]];
      if (q.area <= r.area || !boxInside(r.box, q.box)) continue;
      if (pointInRings(s1, [q.pts]) && pointInRings(s2, [q.pts])) { r.parent = bySize[jj]; break; }
    }
  }
  const depth = i => { let d = 0; for (let k = rings[i].parent; k >= 0 && d < 1000; k = rings[k].parent) d++; return d; };
  const kids = rings.map(() => []);
  rings.forEach((r, i) => { if (r.parent >= 0) kids[r.parent].push(i); });
  const T = rings.map((r, i) => ({
    rings: [r.pts, ...kids[i].map(k => rings[k].pts)], rule: 'evenodd', depth: depth(i), box: r.box,
    area: r.area - kids[i].reduce((a, k) => a + rings[k].area, 0), c: ringCentroid(r.pts), dark: null, occ: [], stroke: r.stroke,
  }));
  T.sort((a, b) => a.depth - b.depth || a.c.y - b.c.y || a.c.x - b.c.x);
  return T;
}

// Filled shapes of an SVG (from svgToStrokes' shape list): every subpath of a filled shape is part of
// its fill, closed or not, as in SVG. Near-white or invisible fills are kept (they still hide what is
// under them) but marked light. Each target lists the shapes painted over it.
function colourDark(rgb, alpha) {
  if (!rgb) return 0.5 * Math.min(1, alpha);
  const lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255;
  return Math.max(0, Math.min(1, (1 - lum) * Math.min(1, alpha)));
}
function filledTargets(strokes, shapes) {
  const T = [];
  (shapes || []).forEach((sh, k) => {
    if (!sh || !sh.fill || !(sh.alpha > 0.02)) return;
    const rings = [];
    for (let i = sh.from; i < sh.to; i++) {
      const s = strokes[i];
      if (!s || s.length < 2) continue;
      const a = s[0], b = s[s.length - 1];
      const pts = Math.hypot(a.x - b.x, a.y - b.y) < 1e-12 ? s.slice(0, -1) : s;
      if (pts.length >= 2) rings.push(pts);
    }
    if (!rings.length) return;
    let box = ringBox(rings[0]), area = 0, cx = 0, cy = 0;
    for (const r of rings) { box = boxUnion(box, ringBox(r)); const a = Math.abs(ringArea(r)); area += a; const c = ringCentroid(r); cx += c.x * a; cy += c.y * a; }
    if (!(area > 1e-9)) return;
    T.push({ rings, rule: sh.rule === 'evenodd' ? 'evenodd' : 'nonzero', depth: 0, box, area, c: { x: cx / area, y: cy / area },
             dark: colourDark(sh.fill, sh.alpha), z: k, occ: [] });
  });
  for (const t of T) t.occ = T.filter(o => o.z > t.z && boxOverlap(o.box, t.box));
  return T;
}

/* ----- the hatch itself ----- */

// Edges of a set of rings in the frame where hatch lines are horizontal, bucketed by line (height s).
// Each edge remembers its ring and position, so a zig-zag link can follow the outline exactly.
function edgeIndex(rings, toF, s, own) {
  const E = [], R = [];
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  rings.forEach((ring, r) => {
    const P = ring.map(toF);
    R.push(P);
    for (let i = 0; i < P.length; i++) {
      const a = P[i], b = P[(i + 1) % P.length];
      if (a.x === b.x && a.y === b.y) continue;
      E.push({ ax: a.x, ay: a.y, bx: b.x, by: b.y, ymin: Math.min(a.y, b.y), ymax: Math.max(a.y, b.y), dir: b.y > a.y ? 1 : -1, r, i, own });
      x0 = Math.min(x0, a.x); x1 = Math.max(x1, a.x); y0 = Math.min(y0, a.y); y1 = Math.max(y1, a.y);
    }
  });
  if (!E.length) return { E, B: [], R, k0: 0, k1: -1, s, box: { x0: 0, y0: 0, x1: 0, y1: 0 } };
  const k0 = Math.floor(y0 / s), k1 = Math.floor(y1 / s), B = [];
  for (let k = k0; k <= k1; k++) B.push([]);
  for (const e of E) for (let k = Math.floor(e.ymin / s); k <= Math.floor(e.ymax / s); k++) B[k - k0].push(e);
  return { E, B, R, k0, k1, s, box: { x0, y0, x1, y1 } };
}
const bucketOf = (ix, k) => (k < ix.k0 || k > ix.k1 ? [] : ix.B[k - ix.k0]);

// Inside spans of the horizontal line y (fill rule applied), left to right: [{ a, b, ea, eb }] where
// ea/eb are the edges the span starts and ends on.
function spansAt(ix, y, rule) {
  const X = [];
  for (const e of bucketOf(ix, Math.floor(y / ix.s))) {
    if (e.ay === e.by || !(e.ymin <= y && y < e.ymax)) continue;
    X.push({ x: e.ax + (y - e.ay) * (e.bx - e.ax) / (e.by - e.ay), e });
  }
  X.sort((p, q) => p.x - q.x);
  const out = [];
  if (rule === 'nonzero') {
    let w = 0, st = null;
    for (const c of X) { const was = w; w += c.e.dir; if (was === 0 && w !== 0) st = c; else if (was !== 0 && w === 0 && c.x > st.x) out.push({ a: st.x, b: c.x, ea: st.e, eb: c.e }); }
  } else for (let i = 0; i + 1 < X.length; i += 2) if (X[i + 1].x > X[i].x) out.push({ a: X[i].x, b: X[i + 1].x, ea: X[i].e, eb: X[i + 1].e });
  return out;
}
// Spans of A not covered by spans of B (new ends lie on B's edges).
function subtractSpans(A, Bs) {
  if (!Bs.length) return A;
  const out = [];
  for (const s of A) {
    let a = s.a, ea = s.ea;
    for (const c of Bs) {
      if (a >= s.b) break;
      if (c.b <= a || c.a >= s.b) continue;
      if (c.a > a) out.push({ a, b: c.a, ea, eb: c.ea });
      if (c.b > a) { a = c.b; ea = c.eb; }
    }
    if (a < s.b) out.push({ a, b: s.b, ea, eb: s.eb });
  }
  return out;
}
const inSpans = (sp, x, tol = 0) => sp.some(s => x >= s.a - tol && x <= s.b + tol);

// Does segment P→Q cross edge e (touching at P or Q does not count)?
function crossesEdge(px, py, qx, qy, e) {
  const o = (ax, ay, bx, by, cx, cy) => (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
  const L = Math.hypot(qx - px, qy - py) * Math.hypot(e.bx - e.ax, e.by - e.ay), eps = 1e-9 * L;
  const d1 = o(e.ax, e.ay, e.bx, e.by, px, py), d2 = o(e.ax, e.ay, e.bx, e.by, qx, qy);
  const d3 = o(px, py, qx, qy, e.ax, e.ay), d4 = o(px, py, qx, qy, e.bx, e.by);
  return ((d1 > eps && d2 < -eps) || (d1 < -eps && d2 > eps)) && ((d3 > eps && d4 < -eps) || (d3 < -eps && d4 > eps));
}

// Path along a ring from P (on edge iA) to Q (on edge iB), the shorter way round, if not longer
// than cap: the corner points in between.
function ringWalk(R, P, iA, Q, iB, cap) {
  const n = R.length, at = (i) => R[((i % n) + n) % n];
  const par = (p, i) => { const a = at(i), b = at(i + 1), dx = b.x - a.x, dy = b.y - a.y; return ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy || 1); };
  const walk = step => {
    if (iA === iB && (step > 0 ? par(Q, iA) >= par(P, iA) : par(Q, iA) <= par(P, iA))) return { pts: [], len: Math.hypot(Q.x - P.x, Q.y - P.y) };
    const pts = []; let prev = P, len = 0, i = iA;
    for (let guard = 0; guard <= n; guard++) {
      const v = step > 0 ? at(i + 1) : at(i);
      len += Math.hypot(v.x - prev.x, v.y - prev.y); pts.push(v); prev = v;
      if (len > cap) return null;
      i = ((i + step) % n + n) % n;
      if (i === iB) { len += Math.hypot(Q.x - prev.x, Q.y - prev.y); return len <= cap ? { pts, len } : null; }
    }
    return null;
  };
  const f = walk(1), b = walk(-1);
  return !f ? b : !b ? f : (f.len <= b.len ? f : b);
}

// Hatch one target: lines at angle (degrees) and spacing s (drawing units), with an optional gap
// from the outline (inset), zig-zag joining (join), and the shapes painted on top (occ). Lines are
// joined by following the outline (or, with a gap, by a short straight link that stays inside).
function hatchTarget(t, angleDeg, s, opts = {}) {
  const th = angleDeg * Math.PI / 180, c = Math.cos(th), sn = Math.sin(th);
  const toF = p => ({ x: p.x * c - p.y * sn, y: p.x * sn + p.y * c });          // lines become horizontal
  const back = (x, y) => ({ x: x * c + y * sn, y: -x * sn + y * c });
  const inset = Math.max(0, opts.inset || 0), minLen = Math.max(0, opts.minLen || 0), join = opts.join !== false;
  const own = edgeIndex(t.rings, toF, s, true);
  const occ = (opts.occ || []).map(o => ({ ix: edgeIndex(o.rings, toF, s, false), rule: o.rule }));
  if (!own.E.length) return { chains: [], lines: 0, length: 0 };
  const visible = y => {
    let sp = spansAt(own, y, t.rule);
    for (const o of occ) if (sp.length && y >= o.ix.box.y0 && y <= o.ix.box.y1) sp = subtractSpans(sp, spansAt(o.ix, y, o.rule));
    return sp;
  };
  const underOcc = (x, y) => occ.some(o => y >= o.ix.box.y0 && y <= o.ix.box.y1 && spansAt(o.ix, y, o.rule).some(q => x > q.a + 1e-9 && x < q.b - 1e-9));
  // A gap from the outline: a point of a line is kept only if the points `inset` away from it (along
  // the line, across it and diagonally) are all inside, which keeps it about that far from every edge.
  const erode = (sp, r) => sp.map(q => ({ a: q.a + r, b: q.b - r, ea: null, eb: null })).filter(q => q.b > q.a);
  const meet = (A, B) => {
    const out = [];
    for (let i = 0, j = 0; i < A.length && j < B.length;) {
      const a = Math.max(A[i].a, B[j].a), b = Math.min(A[i].b, B[j].b);
      if (b > a) out.push({ a, b, ea: null, eb: null });
      if (A[i].b < B[j].b) i++; else j++;
    }
    return out;
  };
  const lines = [];
  const kA = Math.ceil(own.box.y0 / s - 0.5), kB = Math.floor(own.box.y1 / s - 0.5);
  for (let k = kA; k <= kB; k++) {
    const y = (k + 0.5) * s;
    let sp = visible(y);
    if (inset > 0) {
      const d = inset * (1 - 1e-6), h = d / Math.SQRT2;          // (a hair less, so a line exactly `inset` from an edge stays)
      sp = erode(sp, inset);
      for (const [dy, r] of [[-d, 0], [d, 0], [-h, h], [h, h]]) if (sp.length) sp = meet(sp, erode(visible(y + dy), r));
    }
    sp = sp.filter(q => q.b - q.a > Math.max(minLen, 1e-12));
    if (sp.length) lines.push({ k, y, sp });
  }
  const walkCap = opts.walkCap || 8 * s, stepCap = 3 * s + 2 * inset;
  // Link from the end of a line (x1, y1 on edge e1) to the start of the next (x2, y2 on edge e2):
  // corner points to pass through, or null when the pen should lift instead.
  const link = (x1, y1, e1, x2, y2, e2, k) => {
    if (e1 && e2 && e1.own && e2.own && e1.r === e2.r) {
      const w = ringWalk(own.R[e1.r], { x: x1, y: y1 }, e1.i, { x: x2, y: y2 }, e2.i, walkCap);
      if (w && !w.pts.some(p => underOcc(p.x, p.y)) && !underOcc((x1 + x2) / 2, (y1 + y2) / 2)) return w.pts;
    }
    if (Math.abs(x2 - x1) > stepCap) return null;
    for (const ix of [own, ...occ.map(o => o.ix)]) for (const kk of [k - 1, k]) for (const e of bucketOf(ix, kk)) if (crossesEdge(x1, y1, x2, y2, e)) return null;
    for (const f of [0.25, 0.5, 0.75]) {
      const x = x1 + f * (x2 - x1), y = y1 + f * (y2 - y1);
      if (!inSpans(spansAt(own, y, t.rule), x, 1e-9) || underOcc(x, y)) return null;
    }
    return [];
  };
  const done = [];
  let open = [];
  for (const L of lines) {
    const used = new Array(L.sp.length).fill(false), next = [];
    for (const ch of open) {
      if (!join || ch.k !== L.k - 1) { done.push(ch); continue; }
      let best = -1, bd = Infinity;
      for (let j = 0; j < L.sp.length; j++) {
        if (used[j]) continue;
        const d = Math.abs((ch.right ? L.sp[j].b : L.sp[j].a) - ch.x);
        if (d < bd) { bd = d; best = j; }
      }
      if (best < 0) { done.push(ch); continue; }
      const q = L.sp[best], sx = ch.right ? q.b : q.a, se = ch.right ? q.eb : q.ea, ex = ch.right ? q.a : q.b, ee = ch.right ? q.ea : q.eb;
      const via = link(ch.x, ch.y, ch.e, sx, L.y, se, L.k);
      if (!via) { done.push(ch); continue; }
      used[best] = true;
      for (const p of via) ch.pts.push(p.x, p.y);
      ch.pts.push(sx, L.y, ex, L.y); ch.x = ex; ch.y = L.y; ch.e = ee; ch.right = !ch.right; ch.k = L.k;
      next.push(ch);
    }
    for (let j = 0; j < L.sp.length; j++) {
      if (used[j]) continue;
      const q = L.sp[j], right = (L.k & 1) === 0;
      next.push(right ? { pts: [q.a, L.y, q.b, L.y], x: q.b, y: L.y, e: q.eb, right, k: L.k } : { pts: [q.b, L.y, q.a, L.y], x: q.a, y: L.y, e: q.ea, right, k: L.k });
    }
    open = next;
  }
  done.push(...open);
  let length = 0;
  const chains = done.map(ch => {
    const P = [];
    for (let i = 0; i < ch.pts.length; i += 2) {
      const p = back(ch.pts[i], ch.pts[i + 1]);
      if (!P.length || Math.hypot(p.x - P[P.length - 1].x, p.y - P[P.length - 1].y) > 1e-12) P.push(p);
    }
    for (let i = 1; i < P.length; i++) length += Math.hypot(P[i].x - P[i - 1].x, P[i].y - P[i - 1].y);
    return P;
  }).filter(P => P.length > 1);
  return { chains, lines: lines.reduce((a, L) => a + L.sp.length, 0), length };
}

/* ----- a whole drawing ----- */

const SHADE_DEFAULTS = { pattern: 'off', angle: 45, spacing: 2, vary: 'same', which: 'all', tone: false, outline: true, join: true, inset: 0, seed: 1 };
const SHADE_OVERRIDES = ['auto', 'r45', 'r90', 'r135', 'cross', 'off'];   // a click on a shape steps through these

function shadeRand(seed, i) { const v = Math.sin((i + 1) * 12.9898 + seed * 78.233) * 43758.5453; return v - Math.floor(v); }
const norm180 = a => ((a % 180) + 180) % 180;

// Angles (degrees) for target i. An override from a click turns that shape's lines, cross-hatches it
// or leaves it empty.
function shadeAngles(i, st, ov = 'auto') {
  if (ov === 'off') return [];
  let a = st.angle;
  if (st.vary === 'alt') a += (i % 2) * 90;
  else if (/^step(\d+)$/.test(st.vary)) a += i * parseFloat(st.vary.slice(4));
  else if (st.vary === 'random') a += Math.floor(shadeRand(st.seed, i) * 12) * 15;
  a += { r45: 45, r90: 90, r135: 135 }[ov] || 0;
  const pat = ov === 'cross' ? 'cross' : st.pattern;
  const set = pat === 'cross' ? [a, a + 90] : pat === 'tri' ? [a, a + 60, a + 120] : [a];
  return set.map(v => +norm180(v).toFixed(6));
}

// Which shapes get lines: 'filled' uses the SVG's fills (falls back to outlines when there are none),
// 'all' every closed outline, 'alt' every other nesting level (holes stay empty).
function shadeTargets(sk, which) {
  if (which === 'filled') {
    const T = filledTargets(sk.strokes, sk.shapes);
    if (T.length) return { mode: 'filled', list: T, fallback: false };
  }
  return { mode: which === 'alt' ? 'alt' : 'all', list: outlineTargets(sk.strokes), fallback: which === 'filled' };
}

// Hatch lines for a drawing of `size` mm (spacing and gap are in mm). overrides: Map(target index → state).
function shadeDrawing(T, st, size, overrides = new Map()) {
  const strokes = [], owner = [];
  let lines = 0, length = 0, shaded = 0;
  T.list.forEach((t, i) => {
    const ov = overrides.get(i) || 'auto';
    if (ov === 'auto') {
      if (T.mode === 'alt' && t.depth % 2) return;
      if (T.mode === 'filled' && t.dark < 0.08) return;
    }
    const angles = shadeAngles(i, st, ov);
    if (!angles.length) return;
    let s = st.spacing / size;
    if (T.mode === 'filled' && st.tone && t.dark != null) s /= Math.max(0.15, t.dark);
    let any = false;
    for (const a of angles) {
      const r = hatchTarget(t, a, s, { inset: (st.inset || 0) / size, join: st.join, occ: t.occ, minLen: 0.3 / size });
      for (const ch of r.chains) { strokes.push(ch); owner.push(i); }
      lines += r.lines; length += r.length; if (r.chains.length) any = true;
    }
    if (any) shaded++;
  });
  return { strokes, owner, lines, length: length * size, shaded, targets: T.list.length, mode: T.mode, fallback: T.fallback };
}

// The target under point p (drawing units): the innermost outline, or the top-most filled shape.
function shadeTargetAt(T, p) {
  let best = -1;
  T.list.forEach((t, i) => {
    if (p.x < t.box.x0 || p.x > t.box.x1 || p.y < t.box.y0 || p.y > t.box.y1) return;
    if (!pointInRings(p, t.rings, t.rule)) return;
    if (best < 0) { best = i; return; }
    const b = T.list[best];
    if (T.mode === 'filled' ? t.z > b.z : t.area < b.area) best = i;
  });
  return best;
}
