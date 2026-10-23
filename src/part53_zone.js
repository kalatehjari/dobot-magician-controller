/* ===================== SAFE ZONE AND SAFETY-LOCK GEOMETRY (pure, unit-tested) =====================
   Safe zone: a polygon the user clicks on the paper map (robot mm). Drawings keep inside it, by the
   safety margin, as well as inside the green zone, and pen-up travel goes round inside it.
   Allowed area (for the safety lock and for travel): the green zone ∩ the safe polygon shrunk by the
   margin, as polygons ("rings"; a point is inside when it is inside an odd number of rings — Clipper
   gives outlines and holes, with the allowed side always on the left of each edge). */

const _orient = (ax, ay, bx, by, cx, cy) => (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);

function polySArea(P) {
  let a = 0;
  for (let i = 0, n = P.length; i < n; i++) { const p = P[i], q = P[(i + 1) % n]; a += p.x * q.y - q.x * p.y; }
  return a / 2;
}
const polyKeyOf = P => P.map(p => p.x.toFixed(2) + ',' + p.y.toFixed(2)).join(';');

// Do segments a–b and c–d meet (crossing or touching)?
function segsMeet(ax, ay, bx, by, cx, cy, dx, dy) {
  const d1 = _orient(cx, cy, dx, dy, ax, ay), d2 = _orient(cx, cy, dx, dy, bx, by);
  const d3 = _orient(ax, ay, bx, by, cx, cy), d4 = _orient(ax, ay, bx, by, dx, dy);
  if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return true;
  const on = (px, py, qx, qy, rx, ry) => Math.min(px, qx) - 1e-9 <= rx && rx <= Math.max(px, qx) + 1e-9 && Math.min(py, qy) - 1e-9 <= ry && ry <= Math.max(py, qy) + 1e-9;
  const e = 1e-9 * (1 + Math.abs(bx - ax) + Math.abs(by - ay) + Math.abs(dx - cx) + Math.abs(dy - cy)) ** 2;
  return (Math.abs(d1) <= e && on(cx, cy, dx, dy, ax, ay)) || (Math.abs(d2) <= e && on(cx, cy, dx, dy, bx, by)) ||
         (Math.abs(d3) <= e && on(ax, ay, bx, by, cx, cy)) || (Math.abs(d4) <= e && on(ax, ay, bx, by, dx, dy));
}

function pSegD2(px, py, ax, ay, bx, by) {
  const ex = bx - ax, ey = by - ay, L2 = ex * ex + ey * ey;
  let t = L2 > 0 ? ((px - ax) * ex + (py - ay) * ey) / L2 : 0;
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  const x = ax + t * ex - px, y = ay + t * ey - py;
  return x * x + y * y;
}
function segSegD2(ax, ay, bx, by, cx, cy, dx, dy) {
  if (segsMeet(ax, ay, bx, by, cx, cy, dx, dy)) return 0;
  return Math.min(pSegD2(ax, ay, cx, cy, dx, dy), pSegD2(bx, by, cx, cy, dx, dy), pSegD2(cx, cy, ax, ay, bx, by), pSegD2(dx, dy, ax, ay, bx, by));
}

// Can this polygon be a safe zone? '' if so, otherwise what is wrong.
function polyCheck(P, minArea = 100) {
  if (!Array.isArray(P) || P.length < 3) return 'needs at least 3 corners';
  if (!P.every(p => p && Number.isFinite(p.x) && Number.isFinite(p.y))) return 'has a corner that is not a number';
  const n = P.length;
  for (let i = 0; i < n; i++) if (Math.hypot(P[i].x - P[(i + 1) % n].x, P[i].y - P[(i + 1) % n].y) < 0.5) return 'has two corners on top of each other';
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    if (j === i + 1 || (i === 0 && j === n - 1)) continue;          // neighbouring edges share a corner
    const a = P[i], b = P[(i + 1) % n], c = P[j], d = P[(j + 1) % n];
    if (segsMeet(a.x, a.y, b.x, b.y, c.x, c.y, d.x, d.y)) return 'has edges that cross each other';
  }
  if (Math.abs(polySArea(P)) < minArea) return 'is too small';
  return '';
}

// A polygon ready for fast tests: edges as [ax, ay, bx, by] in one array, box, orientation, convexity.
function polyPrep(P) {
  const n = P.length, e = new Float64Array(4 * n);
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let i = 0; i < n; i++) {
    const a = P[i], b = P[(i + 1) % n];
    e[4 * i] = a.x; e[4 * i + 1] = a.y; e[4 * i + 2] = b.x; e[4 * i + 3] = b.y;
    if (a.x < minX) minX = a.x; if (a.x > maxX) maxX = a.x; if (a.y < minY) minY = a.y; if (a.y > maxY) maxY = a.y;
  }
  const sg = polySArea(P) >= 0 ? 1 : -1;
  let convex = n >= 3;
  for (let i = 0; i < n && convex; i++) {
    const a = P[i], b = P[(i + 1) % n], c = P[(i + 2) % n];
    if (sg * _orient(a.x, a.y, b.x, b.y, c.x, c.y) < -1e-9) convex = false;
  }
  return { P, n, e, minX, minY, maxX, maxY, sg, convex };
}

// Inside (even-odd)?
function polyHas(pp, x, y) {
  if (x < pp.minX || x > pp.maxX || y < pp.minY || y > pp.maxY) return false;
  const e = pp.e;
  let ins = false;
  for (let k = 0; k < pp.n; k++) {
    const ay = e[4 * k + 1], by = e[4 * k + 3];
    if ((ay > y) !== (by > y)) {
      const ax = e[4 * k], bx = e[4 * k + 2];
      if (x < ax + (y - ay) * (bx - ax) / (by - ay)) ins = !ins;
    }
  }
  return ins;
}
function polyEdgeD2(pp, x, y) {
  const e = pp.e;
  let d = Infinity;
  for (let k = 0; k < pp.n; k++) { const q = pSegD2(x, y, e[4 * k], e[4 * k + 1], e[4 * k + 2], e[4 * k + 3]); if (q < d) d = q; }
  return d;
}

// Placement check (part 36): does the drawing (probe P at centre cx, cy, size s) keep c mm inside the
// polygon? A convex polygon needs only the drawing's outline (convex hull); otherwise every simplified
// line is checked against the edges near it.
function polyClear(P, cx, cy, s, pp, c) {
  if (pp.convex) {
    const e = pp.e, sg = pp.sg;
    if (!P.hull.length) return polyHas(pp, cx, cy);
    for (const u of P.hull) {
      const x = cx + s * u.x, y = cy + s * u.y;
      for (let k = 0; k < pp.n; k++) {
        const ax = e[4 * k], ay = e[4 * k + 1], ex = e[4 * k + 2] - ax, ey = e[4 * k + 3] - ay, L = Math.hypot(ex, ey);
        if (L > 0 && sg * (ex * (y - ay) - ey * (x - ax)) / L < c) return false;
      }
    }
    return true;
  }
  const c2 = c * c, e = pp.e, n = pp.n, near = [];
  for (const ch of P.chunks) {
    const x0 = cx + s * ch.minX - c, x1 = cx + s * ch.maxX + c, y0 = cy + s * ch.minY - c, y1 = cy + s * ch.maxY + c;
    near.length = 0;
    for (let k = 0; k < n; k++) {
      const ax = e[4 * k], ay = e[4 * k + 1], bx = e[4 * k + 2], by = e[4 * k + 3];
      if ((ax > bx ? ax : bx) < x0 || (ax < bx ? ax : bx) > x1 || (ay > by ? ay : by) < y0 || (ay < by ? ay : by) > y1) continue;
      near.push(k);
    }
    const a = ch.a, px = cx + s * a[0], py = cy + s * a[1];
    if (!polyHas(pp, px, py)) return false;
    if (!near.length) continue;
    if (a.length === 2) { for (const k of near) if (pSegD2(px, py, e[4 * k], e[4 * k + 1], e[4 * k + 2], e[4 * k + 3]) < c2) return false; continue; }
    let qx = px, qy = py;
    for (let i = 2; i < a.length; i += 2) {
      const rx = cx + s * a[i], ry = cy + s * a[i + 1];
      for (const k of near) if (segSegD2(qx, qy, rx, ry, e[4 * k], e[4 * k + 1], e[4 * k + 2], e[4 * k + 3]) < c2) return false;
      qx = rx; qy = ry;
    }
  }
  return true;
}

// A polyline (closed or not) keeps c mm inside the polygon.
function polyLineClear(pp, pts, closed, c) {
  const c2 = c * c, e = pp.e, n = pts.length;
  for (const p of pts) if (!polyHas(pp, p.x, p.y)) return false;
  const m = closed ? n : n - 1;
  for (let i = 0; i < m; i++) {
    const a = pts[i], b = pts[(i + 1) % n];
    for (let k = 0; k < pp.n; k++) if (segSegD2(a.x, a.y, b.x, b.y, e[4 * k], e[4 * k + 1], e[4 * k + 2], e[4 * k + 3]) < c2) return false;
  }
  return true;
}

/* ---------- the allowed area ---------- */
// The green zone as a polygon (flat x, y): outer arc as chords (inside the circle), the inner arc a
// little further out so its chords stay clear of the base.
function zoneRingXY(z, stepDeg = 2) {
  const a0 = z.thMin, a1 = z.thMax, n = Math.max(2, Math.ceil((a1 - a0) / stepDeg)), out = [];
  for (let i = 0; i <= n; i++) { const a = (a0 + (a1 - a0) * i / n) * RAD; out.push(z.rOut * Math.cos(a), z.rOut * Math.sin(a)); }
  const rI = Math.max(1, z.rIn) / Math.cos(((a1 - a0) / n / 2) * RAD) + 0.02;
  for (let i = n; i >= 0; i--) { const a = (a0 + (a1 - a0) * i / n) * RAD; out.push(rI * Math.cos(a), rI * Math.sin(a)); }
  return out;
}
// Green zone z (with its margin) ∩ the safe polygon shrunk by the margin. Needs Clipper (part 48/49).
function regionBuild(z, poly) {
  let paths = [clPath(zoneRingXY(z))];
  if (poly && poly.length >= 3) {
    const P = polySArea(poly) >= 0 ? poly : poly.slice().reverse();
    let up = [clPath(P.flatMap(p => [p.x, p.y]))];
    if ((z.margin || 0) > 0) up = clOffset(up, -z.margin, true);
    paths = clInter(paths, up);
  }
  const rings = [];
  for (const path of paths) {
    const xy = clXY(path);
    if (xy.length < 6) continue;
    const P = [];
    for (let i = 0; i < xy.length; i += 2) P.push({ x: xy[i], y: xy[i + 1] });
    if (Math.abs(polySArea(P)) < 1) continue;
    rings.push(polyPrep(P));
  }
  let area = 0;
  for (const r of rings) area += polySArea(r.P);
  return { rings, area, empty: !rings.length };
}

function regionHas(R, x, y, tol = 0) {
  let ins = false;
  for (const pp of R.rings) if (polyHas(pp, x, y)) ins = !ins;
  if (ins || !(tol > 0)) return ins;
  const t2 = tol * tol;
  for (const pp of R.rings) if (polyEdgeD2(pp, x, y) <= t2) return true;
  return false;
}
function regionEdgeD2(R, x, y) { let d = Infinity; for (const pp of R.rings) d = Math.min(d, polyEdgeD2(pp, x, y)); return d; }

// Where segment a–b meets the area's edges, as positions 0…1 along it (with 0 and 1), sorted.
function regionCuts(R, ax, ay, bx, by) {
  const ts = [0, 1], dx = bx - ax, dy = by - ay, L = Math.hypot(dx, dy);
  if (!(L > 0)) return ts;
  for (const pp of R.rings) {
    const e = pp.e;
    for (let k = 0; k < pp.n; k++) {
      const cx = e[4 * k], cy = e[4 * k + 1], ex = e[4 * k + 2] - cx, ey = e[4 * k + 3] - cy;
      if (Math.max(cx, cx + ex) < Math.min(ax, bx) - 1e-9 || Math.min(cx, cx + ex) > Math.max(ax, bx) + 1e-9 ||
          Math.max(cy, cy + ey) < Math.min(ay, by) - 1e-9 || Math.min(cy, cy + ey) > Math.max(ay, by) + 1e-9) continue;
      const den = dx * ey - dy * ex;
      if (Math.abs(den) < 1e-12 * L * (Math.hypot(ex, ey) + 1e-12)) {
        if (Math.abs((cx - ax) * dy - (cy - ay) * dx) < 1e-9 * L) {          // on the same line: add the edge's ends
          for (const [px, py] of [[cx, cy], [cx + ex, cy + ey]]) { const t = ((px - ax) * dx + (py - ay) * dy) / (L * L); if (t > 0 && t < 1) ts.push(t); }
        }
        continue;
      }
      const t = ((cx - ax) * ey - (cy - ay) * ex) / den, u = ((cx - ax) * dy - (cy - ay) * dx) / den;
      if (t > 0 && t < 1 && u >= -1e-9 && u <= 1 + 1e-9) ts.push(t);
    }
  }
  return ts.sort((p, q) => p - q);
}
// Parts of segment a–b inside the area: [[t0, t1], …].
function regionSpans(R, ax, ay, bx, by, tol = 0.05) {
  const ts = regionCuts(R, ax, ay, bx, by), out = [];
  if (ts.length === 2 && Math.hypot(bx - ax, by - ay) < 1e-9) return regionHas(R, ax, ay, tol) ? [[0, 1]] : [];
  for (let i = 1; i < ts.length; i++) {
    const t0 = ts[i - 1], t1 = ts[i];
    if (t1 - t0 < 1e-9) continue;
    const m = (t0 + t1) / 2;
    if (!regionHas(R, ax + (bx - ax) * m, ay + (by - ay) * m, tol)) continue;
    const last = out[out.length - 1];
    if (last && Math.abs(last[1] - t0) < 1e-9) last[1] = t1; else out.push([t0, t1]);
  }
  return out;
}
function regionSegInside(R, ax, ay, bx, by, tol = 0.05) {
  if (!regionHas(R, ax, ay, tol) || !regionHas(R, bx, by, tol)) return false;
  const sp = regionSpans(R, ax, ay, bx, by, tol);
  return sp.length === 1 && sp[0][0] < 1e-9 && sp[0][1] > 1 - 1e-9;
}

// Nearest point inside the area (a little in from the edge), for a point outside it.
function regionProject(R, x, y, inset = 0.3) {
  if (regionHas(R, x, y)) return { x, y };
  let best = null, bd = Infinity;
  for (const pp of R.rings) {
    const e = pp.e;
    for (let k = 0; k < pp.n; k++) {
      const ax = e[4 * k], ay = e[4 * k + 1], ex = e[4 * k + 2] - ax, ey = e[4 * k + 3] - ay, L2 = ex * ex + ey * ey;
      let t = L2 > 0 ? ((x - ax) * ex + (y - ay) * ey) / L2 : 0;
      t = t < 0 ? 0 : t > 1 ? 1 : t;
      const qx = ax + t * ex, qy = ay + t * ey, d = (qx - x) ** 2 + (qy - y) ** 2;
      if (d < bd) { bd = d; best = { qx, qy, ex, ey, L: Math.sqrt(L2) }; }
    }
  }
  if (!best) return null;
  if (best.L > 0) {
    const p = { x: best.qx - best.ey / best.L * inset, y: best.qy + best.ex / best.L * inset };   // left of the edge = inside
    if (regionHas(R, p.x, p.y)) return p;
  }
  for (let i = 0; i < 16; i++) {                       // at a corner: try round it
    const a = i * Math.PI / 8, p = { x: best.qx + inset * Math.cos(a), y: best.qy + inset * Math.sin(a) };
    if (regionHas(R, p.x, p.y)) return p;
  }
  return { x: best.qx, y: best.qy };
}

// Shortest way between two points inside the area: straight if it stays inside, otherwise round the
// corners that turn inwards (moved `inset` mm inside). Returns the corners to pass (maybe none), or
// null if there is no way inside.
function regionRouter(R, inset = 0.4) {
  const V = [];
  for (const pp of R.rings) {
    const P = pp.P, n = P.length;
    for (let i = 0; i < n; i++) {
      const a = P[(i + n - 1) % n], b = P[i], c = P[(i + 1) % n];
      if (_orient(a.x, a.y, b.x, b.y, c.x, c.y) >= -1e-9) continue;            // a right turn: the corner points inwards
      const l1 = Math.hypot(b.x - a.x, b.y - a.y) || 1, l2 = Math.hypot(c.x - b.x, c.y - b.y) || 1;
      let nx = -(b.y - a.y) / l1 - (c.y - b.y) / l2, ny = (b.x - a.x) / l1 + (c.x - b.x) / l2;
      const nl = Math.hypot(nx, ny);
      if (nl < 1e-9) continue;
      nx /= nl; ny /= nl;
      const v = { x: b.x + nx * inset, y: b.y + ny * inset };
      if (regionHas(R, v.x, v.y)) V.push(v);
    }
  }
  const vis = (a, b) => regionSegInside(R, a.x, a.y, b.x, b.y, 0.02);
  let G = null;
  const graph = () => {
    G = V.map(() => []);
    for (let i = 0; i < V.length; i++) for (let j = i + 1; j < V.length; j++) {
      if (!vis(V[i], V[j])) continue;
      const d = Math.hypot(V[i].x - V[j].x, V[i].y - V[j].y);
      G[i].push([j, d]); G[j].push([i, d]);
    }
  };
  const route = (a, b) => {
    if (vis(a, b)) return [];
    if (!G) graph();
    const N = V.length, A = N, B = N + 1, D = new Float64Array(N + 2).fill(Infinity), prev = new Int32Array(N + 2).fill(-1), done = new Uint8Array(N + 2);
    const toB = new Float64Array(N).fill(-1), fromA = [];
    for (let i = 0; i < N; i++) {
      if (vis(a, V[i])) fromA.push([i, Math.hypot(a.x - V[i].x, a.y - V[i].y)]);
      if (vis(V[i], b)) toB[i] = Math.hypot(b.x - V[i].x, b.y - V[i].y);
    }
    D[A] = 0;
    for (;;) {
      let u = -1, du = Infinity;
      for (let i = 0; i < N + 2; i++) if (!done[i] && D[i] < du) { du = D[i]; u = i; }
      if (u < 0 || u === B) break;
      done[u] = 1;
      const nb = u === A ? fromA : G[u];
      for (const [j, w] of nb) if (D[u] + w < D[j]) { D[j] = D[u] + w; prev[j] = u; }
      if (u < N && toB[u] >= 0 && D[u] + toB[u] < D[B]) { D[B] = D[u] + toB[u]; prev[B] = u; }
    }
    if (!Number.isFinite(D[B])) return null;
    const path = [];
    for (let k = prev[B]; k >= 0 && k !== A; k = prev[k]) path.push(V[k]);
    return path.reverse();
  };
  route.corners = V;
  return route;
}

/* ---------- checking and trimming movements (the safety lock) ---------- */
// One move a→b: inside the area all the way and not below the floor. A move that starts outside (the
// arm was outside when the lock went on) is fine if it comes straight in and stays in.
function lockSegOk(R, a, b, floor) {
  if (!(b.z >= floor - 1e-6)) return false;
  if (!a) return regionHas(R, b.x, b.y, 0.05);
  if (regionHas(R, a.x, a.y, 0.05)) return regionSegInside(R, a.x, a.y, b.x, b.y, 0.05);
  const sp = regionSpans(R, a.x, a.y, b.x, b.y, 0.05);
  return sp.length === 1 && sp[0][1] > 1 - 1e-9;
}
// How far a move goes outside (mm, the most), or below the floor.
function lockDepth(R, a, b, floor) {
  let d = Math.max(0, floor - b.z);
  const A = a || b;
  for (let k = 0; k <= 16; k++) {
    const t = k / 16, x = A.x + (b.x - A.x) * t, y = A.y + (b.y - A.y) * t;
    if (!regionHas(R, x, y)) d = Math.max(d, Math.sqrt(regionEdgeD2(R, x, y)));
  }
  return d;
}
// A planned path ({x, y, z} moves, or {pause}) from start: which moves break the boundary.
function lockCheckPath(cmds, start, R, floor) {
  let prev = start ? { x: start.x, y: start.y, z: start.z } : null, bad = 0, worst = 0, first = -1, moves = 0;
  const badIdx = [];
  for (let i = 0; i < cmds.length; i++) {
    const c = cmds[i];
    if (c.x === undefined) continue;
    moves++;
    if (!lockSegOk(R, prev, c, floor)) {
      bad++; if (first < 0) first = i;
      if (badIdx.length < 2000) badIdx.push(i);
      worst = Math.max(worst, lockDepth(R, prev, c, floor));
    }
    prev = c;
  }
  return { ok: !bad, bad, worst, first, moves, badIdx };
}

// Trims a planned path to the area. mode 'draw': lines with the pen down (both ends within 0.6 mm of
// zDown) keep only their parts inside, and between the parts the pen lifts to zUp and travels round
// inside. Every other move (and every move in mode 'move') is pulled in: a point outside goes to the
// nearest point inside, and the way there goes round inside. Heights below the floor are raised.
// opts: { mode, zDown, zUp, route } (route: from regionRouter).
function lockTrimPath(cmds, start, R, floor, opts) {
  const mode = opts.mode || 'move', zU = opts.zUp, penZ = (opts.zDown ?? -Infinity) + 0.6, route = opts.route || regionRouter(R);
  const out = [], lerp = (a, b, t) => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
  const far = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z) > 0.01;
  let cur = start ? { x: start.x, y: start.y, z: start.z } : null, prev = cur;
  // from cur (anywhere) to p (inside) at height z, staying inside: in first if outside, then round
  const travel = (p, z) => {
    if (!cur) { out.push({ x: p.x, y: p.y, z, mode: 2 }); cur = { x: p.x, y: p.y, z }; return; }
    if (Math.abs(cur.z - z) > 0.01) { out.push({ x: cur.x, y: cur.y, z, mode: 2 }); cur = { ...cur, z }; }
    if (!regionHas(R, cur.x, cur.y, 0.05)) { const q = regionProject(R, cur.x, cur.y); out.push({ x: q.x, y: q.y, z, mode: 2 }); cur = { x: q.x, y: q.y, z }; }
    for (const w of route(cur, p) || []) out.push({ x: w.x, y: w.y, z, mode: 2 });
    out.push({ x: p.x, y: p.y, z, mode: 2 });
    cur = { x: p.x, y: p.y, z };
  };
  const like = (c, p) => c.kind === 'cp' ? { kind: 'cp', x: p.x, y: p.y, z: p.z, v: c.v } : { x: p.x, y: p.y, z: p.z, mode: c.mode ?? 2 };
  for (const c0 of cmds) {
    if (c0.x === undefined) { out.push(c0); continue; }
    const c = { ...c0, z: Math.max(c0.z, floor) };
    if (!prev) {
      const q = regionHas(R, c.x, c.y, 0.05) ? c : { ...regionProject(R, c.x, c.y), z: c.z };
      out.push(like(c, q)); cur = { x: q.x, y: q.y, z: q.z }; prev = c; continue;
    }
    if (cur && !far(cur, prev) && lockSegOk(R, cur, c, floor)) { out.push(c); cur = { x: c.x, y: c.y, z: c.z }; prev = c; continue; }
    if (mode === 'draw' && prev.z <= penZ && c.z <= penZ) {
      for (const [t0, t1] of regionSpans(R, prev.x, prev.y, c.x, c.y, 0.05)) {
        const A = lerp(prev, c, t0), B = lerp(prev, c, t1);
        if (!cur || far(cur, A)) { travel(A, Math.max(zU, A.z)); out.push(like(c, A)); cur = A; }
        out.push(like(c, B)); cur = B;
      }
    } else {
      const q = regionHas(R, c.x, c.y, 0.05) ? { x: c.x, y: c.y, z: c.z } : { ...regionProject(R, c.x, c.y), z: c.z };
      if (!cur) { out.push(like(c, q)); cur = q; }
      else if (far(cur, q)) {
        if (!lockSegOk(R, cur, q, floor)) {
          const z = Math.max(cur.z, q.z);
          if (Math.abs(cur.z - z) > 0.01) { out.push({ x: cur.x, y: cur.y, z, mode: 2 }); cur = { ...cur, z }; }
          if (!regionHas(R, cur.x, cur.y, 0.05)) { const p = regionProject(R, cur.x, cur.y); out.push({ x: p.x, y: p.y, z, mode: 2 }); cur = { x: p.x, y: p.y, z }; }
          for (const w of route(cur, q) || []) out.push({ x: w.x, y: w.y, z, mode: 2 });
        }
        out.push(like(c, q)); cur = q;
      }
    }
    prev = c;
  }
  return out;
}

// For following (mouse, hand, face, dance): the nearest allowed target, reached in a straight move
// from `from` (as far towards it as stays inside).
function lockClampPoint(R, from, t, floor) {
  const q0 = regionHas(R, t.x, t.y, 0.05) ? { x: t.x, y: t.y } : regionProject(R, t.x, t.y);
  if (!q0) return null;
  const q = { x: q0.x, y: q0.y, z: Math.max(t.z, floor) };
  if (!from || lockSegOk(R, from, q, floor)) return q;
  let lo = 0, hi = 1;
  for (let i = 0; i < 24; i++) {
    const m = (lo + hi) / 2, p = { x: from.x + (q.x - from.x) * m, y: from.y + (q.y - from.y) * m, z: from.z + (q.z - from.z) * m };
    if (lockSegOk(R, from, p, floor)) lo = m; else hi = m;
  }
  return { x: from.x + (q.x - from.x) * lo, y: from.y + (q.y - from.y) * lo, z: Math.max(floor, from.z + (q.z - from.z) * lo) };
}
