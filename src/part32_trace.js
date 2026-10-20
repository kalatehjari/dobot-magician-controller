/* ===================== IMAGE → LINES (pure, unit-tested) ===================== */
// Three ways to turn a picture into pen strokes:
//   outline — the borders of dark shapes (logos, silhouettes, filled art): marching squares
//   centre  — one stroke down the middle of each line (sketches, handwriting): thinning + tracing
//   edges   — the edges in a photo: gradient magnitude, thinned and traced
// Controls: threshold (light/dark cut, auto = Otsu), detail (1–10: ignore specks, keep small
// features), curves (0–10: 0 keeps every corner, 10 rounds everything), invert.

function imageToGray(data, w, h) {
  const g = new Float32Array(w * h);
  for (let i = 0, p = 0; i < w * h; i++, p += 4) {
    const a = data[p + 3] / 255;
    g[i] = (0.299 * data[p] + 0.587 * data[p + 1] + 0.114 * data[p + 2]) * a + 255 * (1 - a);
  }
  return g;
}

function otsuThreshold(g) {
  const hist = new Float64Array(256);
  for (const v of g) hist[Math.max(0, Math.min(255, Math.round(v)))]++;
  const total = g.length;
  let sum = 0; for (let i = 0; i < 256; i++) sum += i * hist[i];
  let sumB = 0, wB = 0, best = 0, lo = 127, hi = 127;
  for (let i = 0; i < 256; i++) {
    wB += hist[i]; if (!wB) continue;
    const wF = total - wB; if (!wF) break;
    sumB += i * hist[i];
    const mB = sumB / wB, mF = (sum - sumB) / wF, between = wB * wF * (mB - mF) ** 2;
    if (between > best * (1 + 1e-9)) { best = between; lo = hi = i; }
    else if (between >= best * (1 - 1e-9)) hi = i;            // a tie: remember the whole plateau
  }
  return (lo + hi) / 2 + 0.5;                                  // middle of the gap between ink and paper
}

function boxBlur(src, w, h, r) {
  if (r < 1) return Float32Array.from(src);
  const tmp = new Float32Array(w * h), out = new Float32Array(w * h), n = 2 * r + 1;
  for (let y = 0; y < h; y++) {
    let acc = 0;
    for (let k = -r; k <= r; k++) acc += src[y * w + Math.min(w - 1, Math.max(0, k))];
    for (let x = 0; x < w; x++) {
      tmp[y * w + x] = acc / n;
      acc += src[y * w + Math.min(w - 1, x + r + 1)] - src[y * w + Math.max(0, x - r)];
    }
  }
  for (let x = 0; x < w; x++) {
    let acc = 0;
    for (let k = -r; k <= r; k++) acc += tmp[Math.min(h - 1, Math.max(0, k)) * w + x];
    for (let y = 0; y < h; y++) {
      out[y * w + x] = acc / n;
      acc += tmp[Math.min(h - 1, y + r + 1) * w + x] - tmp[Math.max(0, y - r) * w + x];
    }
  }
  return out;
}

// 1 = ink. Normally ink is darker than the threshold; invert for light lines on dark.
function binarize(g, t, invert) {
  const m = new Uint8Array(g.length);
  for (let i = 0; i < g.length; i++) m[i] = invert ? (g[i] > t ? 1 : 0) : (g[i] < t ? 1 : 0);
  return m;
}

// Removes ink specks smaller than minArea and fills holes smaller than minArea.
function cleanMask(mask, w, h, minArea) {
  const m = mask.slice(), seen = new Uint8Array(w * h), stack = [], comp = [];
  for (const target of [1, 0]) {
    seen.fill(0);
    for (let i = 0; i < w * h; i++) {
      if (seen[i] || m[i] !== target) continue;
      comp.length = 0; stack.length = 0; stack.push(i); seen[i] = 1;
      let border = false;
      while (stack.length) {
        const p = stack.pop(); comp.push(p);
        const x = p % w, y = (p / w) | 0;
        if (x === 0 || y === 0 || x === w - 1 || y === h - 1) border = true;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue;
          if (target === 0 && dx && dy) continue;                 // holes: 4-connected
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          const q = ny * w + nx;
          if (!seen[q] && m[q] === target) { seen[q] = 1; stack.push(q); }
        }
      }
      if (comp.length < minArea && (target === 1 || !border)) for (const p of comp) m[p] = 1 - target;
    }
  }
  return m;
}

// Marching squares: closed iso-lines of `field` at `iso`; inside = field < iso. The field is padded
// with "outside" so every contour closes. Coordinates are pixel centres.
function marchingSquares(field, w, h, iso) {
  const W = w + 2, H = h + 2;
  const val = (x, y) => (x <= 0 || y <= 0 || x >= W - 1 || y >= H - 1) ? iso + 1e3 : field[(y - 1) * w + (x - 1)];
  const nE = W * H * 2;
  const n1 = new Int32Array(nE).fill(-1), n2 = new Int32Array(nE).fill(-1);
  const px = new Float32Array(nE), py = new Float32Array(nE), has = new Uint8Array(nE);
  const hE = (x, y) => (y * W + x) * 2, vE = (x, y) => (y * W + x) * 2 + 1;
  const point = (id, x, y, va, vb, horiz) => {
    if (has[id]) return;
    const t = (iso - va) / ((vb - va) || 1e-9);
    if (horiz) { px[id] = x + t - 1; py[id] = y - 1; } else { px[id] = x - 1; py[id] = y + t - 1; }
    has[id] = 1;
  };
  const link = (a, b) => {
    if (n1[a] < 0) n1[a] = b; else n2[a] = b;
    if (n1[b] < 0) n1[b] = a; else n2[b] = a;
  };
  for (let y = 0; y < H - 1; y++) for (let x = 0; x < W - 1; x++) {
    const tl = val(x, y), tr = val(x + 1, y), br = val(x + 1, y + 1), bl = val(x, y + 1);
    const c = (tl < iso ? 8 : 0) | (tr < iso ? 4 : 0) | (br < iso ? 2 : 0) | (bl < iso ? 1 : 0);
    if (c === 0 || c === 15) continue;
    const T = hE(x, y), B = hE(x, y + 1), Lf = vE(x, y), R = vE(x + 1, y);
    point(T, x, y, tl, tr, true); point(B, x, y + 1, bl, br, true);
    point(Lf, x, y, tl, bl, false); point(R, x + 1, y, tr, br, false);
    const centreIn = (tl + tr + br + bl) / 4 < iso;
    switch (c) {
      case 1: case 14: link(Lf, B); break;
      case 2: case 13: link(B, R); break;
      case 3: case 12: link(Lf, R); break;
      case 4: case 11: link(T, R); break;
      case 6: case 9: link(T, B); break;
      case 7: case 8: link(Lf, T); break;
      case 5: if (centreIn) { link(Lf, T); link(B, R); } else { link(T, R); link(Lf, B); } break;
      case 10: if (centreIn) { link(T, R); link(Lf, B); } else { link(Lf, T); link(B, R); } break;
    }
  }
  const used = new Uint8Array(nE), loops = [];
  for (let s = 0; s < nE; s++) {
    if (used[s] || n1[s] < 0) continue;
    const pts = []; let prev = -1, cur = s;
    while (cur >= 0 && !used[cur]) {
      used[cur] = 1; pts.push({ x: px[cur], y: py[cur] });
      const nxt = n1[cur] !== prev ? n1[cur] : n2[cur];
      prev = cur; cur = nxt;
    }
    if (pts.length >= 3) loops.push(pts);
  }
  return loops;
}

// Zhang–Suen thinning: reduces ink to 1-pixel-wide centre lines.
function thinMask(mask, w, h) {
  const m = mask.slice();
  for (let x = 0; x < w; x++) { m[x] = 0; m[(h - 1) * w + x] = 0; }
  for (let y = 0; y < h; y++) { m[y * w] = 0; m[y * w + w - 1] = 0; }
  const del = [];
  let changed = true;
  while (changed) {
    changed = false;
    for (let step = 0; step < 2; step++) {
      del.length = 0;
      for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
        const i = y * w + x;
        if (!m[i]) continue;
        const p2 = m[i - w], p3 = m[i - w + 1], p4 = m[i + 1], p5 = m[i + w + 1], p6 = m[i + w], p7 = m[i + w - 1], p8 = m[i - 1], p9 = m[i - w - 1];
        const B = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9;
        if (B < 2 || B > 6) continue;
        const seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2];
        let A = 0; for (let k = 0; k < 8; k++) if (!seq[k] && seq[k + 1]) A++;
        if (A !== 1) continue;
        if (step === 0 ? (p2 && p4 && p6) || (p4 && p6 && p8) : (p2 && p4 && p8) || (p2 && p6 && p8)) continue;
        del.push(i);
      }
      for (const i of del) m[i] = 0;
      if (del.length) changed = true;
    }
  }
  return m;
}

// Follows a 1-pixel skeleton into polylines. m-adjacency (diagonal only when no 4-neighbour path)
// stops staircase corners from looking like junctions.
function traceSkeleton(sk, w, h) {
  const on = i => i >= 0 && i < w * h && sk[i] === 1;
  const nb = i => {
    const x = i % w, y = (i / w) | 0, out = [];
    const N = y > 0 && on(i - w), S_ = y < h - 1 && on(i + w), E = x < w - 1 && on(i + 1), Wt = x > 0 && on(i - 1);
    if (N) out.push(i - w); if (S_) out.push(i + w); if (E) out.push(i + 1); if (Wt) out.push(i - 1);
    if (y > 0 && x > 0 && on(i - w - 1) && !N && !Wt) out.push(i - w - 1);
    if (y > 0 && x < w - 1 && on(i - w + 1) && !N && !E) out.push(i - w + 1);
    if (y < h - 1 && x > 0 && on(i + w - 1) && !S_ && !Wt) out.push(i + w - 1);
    if (y < h - 1 && x < w - 1 && on(i + w + 1) && !S_ && !E) out.push(i + w + 1);
    return out;
  };
  const deg = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) if (sk[i]) deg[i] = nb(i).length;
  const visited = new Set(), key = (a, b) => (a < b ? a * (w * h) + b : b * (w * h) + a);
  const walk = (a, b) => {
    const pts = [a, b]; visited.add(key(a, b));
    let prev = a, cur = b;
    while (deg[cur] === 2) {
      const n = nb(cur).find(q => q !== prev && !visited.has(key(cur, q)));
      if (n === undefined) break;
      visited.add(key(cur, n)); pts.push(n); prev = cur; cur = n;
    }
    return pts;
  };
  const paths = [];
  for (const pass of [0, 1]) {
    for (let i = 0; i < w * h; i++) {
      if (!sk[i] || (pass === 0 ? deg[i] === 2 : deg[i] !== 2)) continue;
      for (const n of nb(i)) if (!visited.has(key(i, n))) paths.push(walk(i, n));
    }
  }
  return paths.map(p => p.map(i => ({ x: i % w, y: (i / w) | 0 })));
}

function sobelMagnitude(g, w, h) {
  const out = new Float32Array(w * h);
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x;
    const gx = -g[i - w - 1] - 2 * g[i - 1] - g[i + w - 1] + g[i - w + 1] + 2 * g[i + 1] + g[i + w + 1];
    const gy = -g[i - w - 1] - 2 * g[i - w] - g[i - w + 1] + g[i + w - 1] + 2 * g[i + w] + g[i + w + 1];
    out[i] = Math.hypot(gx, gy);
  }
  return out;
}

function polyArea(pts) {
  let a = 0;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) a += (pts[j].x + pts[i].x) * (pts[j].y - pts[i].y);
  return a / 2;
}

function closedRdp(pts, eps) {
  if (pts.length < 4) return pts.slice();
  let far = 0, fd = -1;
  for (let i = 1; i < pts.length; i++) { const d = dist(pts[0], pts[i]); if (d > fd) { fd = d; far = i; } }
  const a = rdp(pts.slice(0, far + 1), eps), b = rdp(pts.slice(far).concat([pts[0]]), eps);
  return a.slice(0, -1).concat(b.slice(0, -1));
}

// Even spacing along a polyline (step in pixels), keeping both ends.
function resamplePolyline(pts, step) {
  const out = [pts[0]];
  let carry = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i], L = dist(a, b);
    let t = step - carry;
    while (t <= L) { out.push({ x: a.x + (b.x - a.x) * t / L, y: a.y + (b.y - a.y) * t / L }); t += step; }
    carry = L - (t - step);
  }
  const last = pts[pts.length - 1];
  if (dist(out[out.length - 1], last) > 1e-6) out.push(last);
  return out;
}

// Gaussian smoothing along the path, radius sigma (px). Corners with an interior angle below
// cornerDeg stay sharp: the path is split there and each run is smoothed with its ends pinned.
function smoothPath(pts, closed, sigma, cornerDeg) {
  if (sigma < 0.3 || pts.length < 3) return pts;
  const n = pts.length, sharp = [], D = Math.max(3, sigma / 2);
  // The angle at a vertex is measured between points about D px away along the path, so a
  // slightly chamfered right angle still counts as one 90° corner.
  const along = (i, dir) => {
    let j = i, acc = 0;
    for (let s = 0; s < n; s++) {
      const nj = closed ? (j + dir + n) % n : j + dir;
      if (nj < 0 || nj >= n) break;
      acc += dist(pts[j], pts[nj]); j = nj;
      if (acc >= D) break;
    }
    return pts[j];
  };
  for (let i = 0; i < n; i++) {
    if (!closed && (i === 0 || i === n - 1)) { sharp.push(i); continue; }
    const a = along(i, -1), b = pts[i], c = along(i, 1);
    const v1x = a.x - b.x, v1y = a.y - b.y, v2x = c.x - b.x, v2y = c.y - b.y;
    const ang = Math.acos(clamp((v1x * v2x + v1y * v2y) / ((Math.hypot(v1x, v1y) * Math.hypot(v2x, v2y)) || 1), -1, 1)) * 180 / Math.PI;
    if (ang < cornerDeg) sharp.push(i);
  }
  const step = Math.max(0.75, sigma / 3), k = Math.ceil(2.5 * sigma / step);
  const w = Array.from({ length: 2 * k + 1 }, (_, i) => Math.exp(-0.5 * ((i - k) * step / sigma) ** 2));
  const smoothRun = (run, cyclic) => {
    const R = resamplePolyline(run, step), m = R.length, out = [];
    for (let i = 0; i < m; i++) {
      if (!cyclic && (i === 0 || i === m - 1)) { out.push(R[i]); continue; }
      let sx = 0, sy = 0, sw = 0;
      const reach = cyclic ? k : Math.min(k, i, m - 1 - i);      // shrink the window near pinned ends
      for (let j = -reach; j <= reach; j++) {
        const q = R[cyclic ? (i + j + m) % m : i + j], wt = w[j + k];
        sx += q.x * wt; sy += q.y * wt; sw += wt;
      }
      out.push({ x: sx / sw, y: sy / sw });
    }
    return out;
  };
  if (closed && !sharp.length) return smoothRun(pts.concat([pts[0]]), true).slice(0, -1);
  // runs between consecutive sharp vertices (closed paths wrap around)
  const order = closed ? sharp.concat([sharp[0] + n]) : sharp;
  const out = [];
  for (let s = 0; s < order.length - 1; s++) {
    const run = [];
    for (let i = order[s]; i <= order[s + 1]; i++) run.push(pts[i % n]);
    const sm = run.length > 2 ? smoothRun(run, false) : run;
    out.push(...(s ? sm.slice(1) : sm));
  }
  return closed ? out.slice(0, -1) : out;
}

const DETAIL = {
  minArea: [200, 120, 70, 40, 24, 14, 8, 5, 3, 2],
  tol: [3, 2.4, 1.9, 1.5, 1.2, 0.95, 0.75, 0.6, 0.45, 0.35],
  minLen: [40, 30, 22, 16, 12, 9, 7, 5, 4, 3],
};

// Main entry: {data, w, h} (RGBA) → {paths:[{pts, closed}], threshold, w, h}.
function traceImage(img, opts = {}) {
  const { w, h } = img, mode = opts.mode || 'outline';
  const d = clamp(Math.round(opts.detail ?? 6), 1, 10) - 1, s = clamp(opts.smooth ?? 5, 0, 10);
  const gray = imageToGray(img.data, w, h);
  let threshold, raw = [];
  if (mode === 'edges') {
    const mag = sobelMagnitude(boxBlur(gray, w, h, 1), w, h);
    let mx = 0; for (const v of mag) if (v > mx) mx = v;
    const scaled = Float32Array.from(mag, v => (v / (mx || 1)) * 255);
    threshold = opts.threshold ?? otsuThreshold(scaled);
    const edge = cleanMask(binarize(scaled, threshold, true), w, h, DETAIL.minArea[d]);
    raw = traceSkeleton(thinMask(edge, w, h), w, h).map(p => ({ pts: p, closed: false }));
  } else {
    threshold = opts.threshold ?? otsuThreshold(gray);
    const mask = cleanMask(binarize(boxBlur(gray, w, h, d < 3 ? 1 : 0), threshold, !!opts.invert), w, h, DETAIL.minArea[d]);
    if (mode === 'centre') {
      raw = traceSkeleton(thinMask(mask, w, h), w, h).map(p => ({ pts: p, closed: false }));
    } else {
      const field = boxBlur(Float32Array.from(mask, v => (v ? 0 : 255)), w, h, 1);
      // Specks were already removed by pixel count in cleanMask; only drop degenerate outlines here.
      raw = marchingSquares(field, w, h, 127.5)
        .filter(p => Math.abs(polyArea(p)) >= 0.4)
        .map(p => ({ pts: p, closed: true }));
    }
  }
  const sigma = s * 2.0 * Math.max(w, h) / 600;    // smoothing radius scales with the picture (max ≈ 3.3 %)
  const corner = 150 - s * 11;                       // 0: keep every corner … 10: keep only spikes
  const paths = [];
  for (const p of raw) {
    let pts = p.closed ? closedRdp(p.pts, DETAIL.tol[d]) : rdp(p.pts, DETAIL.tol[d]);
    if (pts.length < 2) continue;
    // Cap the radius per line so small shapes (dots, the inside of an "o") keep their size:
    // on a closed loop sigma ≤ 5 % of the perimeter shrinks a circle by about 5 % or less.
    const per = polyLength(p.closed ? pts.concat([pts[0]]) : pts);
    pts = smoothPath(pts, p.closed, Math.min(sigma, (p.closed ? 0.05 : 0.1) * per), corner);
    pts = p.closed ? closedRdp(pts, 0.2) : rdp(pts, 0.2);
    const len = polyLength(p.closed ? pts.concat([pts[0]]) : pts);
    if (len < (p.closed ? Math.min(2, DETAIL.minLen[d]) : DETAIL.minLen[d])) continue;
    paths.push({ pts, closed: p.closed });
  }
  return { paths, threshold, w, h };
}

function pathsToSvg(paths, w, h) {
  const f = v => (Math.round(v * 10) / 10).toString();
  const body = paths.map(p => {
    const d = p.pts.map((q, i) => `${i ? 'L' : 'M'}${f(q.x)} ${f(q.y)}`).join(' ') + (p.closed ? ' Z' : '');
    return `<path d="${d}"/>`;
  }).join('\n');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">\n` +
    `<g fill="none" stroke="#000" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">\n${body}\n</g>\n</svg>\n`;
}

// Strokes for the plotter (closed outlines get their first point repeated so they close on paper).
function pathsToStrokes(paths) {
  return paths.map(p => (p.closed ? p.pts.concat([p.pts[0]]) : p.pts).map(q => ({ x: q.x, y: q.y })));
}
