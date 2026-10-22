/* ===================== 3D PRINTING: MESH FILES AND SLICER (pure functions, no page access) ===================== */
// Turns an STL (or OBJ) model into G-code for the Dobot Magician 3D-printing kit running Dobot's 3D-printer firmware
// (Marlin-style G-code over USB, 115200 baud). Defaults follow Dobot's own guide and profiles: 0.4 mm nozzle, 1.75 mm
// PLA at 200 °C with the fan on, 0.2 mm layers with a 0.35 mm first layer, 6 mm retraction at 60 mm/s, walls at 4 mm/s
// and infill at about twice that, at least two walls, and a circular plate centred at X0 Y0 with the plate surface at
// Z0 (Dobot's Cura profile: Ø80 mm, 150 mm high). Polygon work uses Clipper (part 48) in integer micrometres.

const P3_SC = 1000;                                   // Clipper units per millimetre
const P3_VERSION = '1.5.0';
const PRINT_DEFAULTS = {
  layerH: 0.2, firstH: 0.35, lineW: 0.45, firstW: 0.6, nozzle: 0.4, filament: 1.75, flow: 100,
  walls: 2, top: 4, bottom: 3, infill: 15, pattern: 'lines', seam: 'nearest',
  vWall: 4, vOuter: 4, vInfill: 8, vSolid: 6, vFirst: 4, vTravel: 50, vSupport: 8, vZ: 10,
  temp: 200, fan: true,
  retract: 6, vRetract: 60, retractMin: 1.5, zHop: 0,
  skirt: 1, skirtDist: 3, skirtMin: 150, brim: 0,
  support: 'off', supportAngle: 55, supportGap: 2.5, supportXY: 0.7,
  vase: false, minLayerTime: 10, minSpeed: 2,
  plateD: 80, maxH: 150,
  startCode: 'M106 ; fan on (Dobot start code)\nG91\nG0 Z5 F600 ; lift the nozzle off the plate while it heats\nG90\nM104 S{temp} ; heat the nozzle\nM109 S{temp} ; wait until it is hot\nG21 ; millimetres\nG90 ; absolute positions\nM82 ; absolute extrusion\nG92 E0 ; reset the extruder',
  endCode: 'M104 S0 ; heater off\nG91\nG1 E-1 F300\nG1 Z+3 E-5 F{travelF}\nG1 Y+50\nG90\nM107 ; fan off',
};
// Quality presets change only these fields; everything else keeps its value.
const PRINT_PRESETS = {
  normal: { label: 'Normal — 0.2 mm (Dobot default)', layerH: 0.2, walls: 2, top: 4, bottom: 3, infill: 15, vase: false },
  fine: { label: 'Fine — 0.15 mm', layerH: 0.15, walls: 3, top: 5, bottom: 4, infill: 15, vase: false },
  draft: { label: 'Draft — 0.3 mm', layerH: 0.3, walls: 2, top: 3, bottom: 2, infill: 10, vase: false },
  strong: { label: 'Strong — 0.2 mm, 3 walls, 30 % infill', layerH: 0.2, walls: 3, top: 5, bottom: 4, infill: 30, vase: false },
  vase: { label: 'Vase — one wall, spiral (Dobot vase profile)', layerH: 0.2, walls: 1, top: 0, bottom: 3, infill: 0, vase: true },
};
const P3_TYPES = ['travel', 'outer wall', 'inner wall', 'solid infill', 'infill', 'support', 'skirt / brim'];

/* ---------- reading files ---------- */
// Returns { tri: Float32Array (9 numbers per triangle), format }. Binary STL is recognised by its size, so binary
// files whose header starts with "solid" (common) still read correctly.
function meshParse(buf, name = '') {
  const u8 = new Uint8Array(buf);
  if (/\.obj$/i.test(name)) return { tri: objParse(new TextDecoder('latin1').decode(u8)), format: 'OBJ' };
  if (u8.length >= 84) {
    const n = new DataView(u8.buffer, u8.byteOffset, u8.byteLength).getUint32(80, true);
    if (84 + 50 * n === u8.length) return { tri: stlParseBinary(u8), format: 'binary STL' };
  }
  const head = new TextDecoder('latin1').decode(u8.subarray(0, Math.min(u8.length, 1024)));
  if (/^\s*solid\b/.test(head) && /facet|endsolid/.test(new TextDecoder('latin1').decode(u8.subarray(0, Math.min(u8.length, 4096)))))
    return { tri: stlParseAscii(new TextDecoder('latin1').decode(u8)), format: 'ASCII STL' };
  if (u8.length >= 134) return { tri: stlParseBinary(u8), format: 'binary STL' };
  throw new Error('This does not look like an STL or OBJ file.');
}
function stlParseBinary(u8) {
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const T = Math.min(dv.getUint32(80, true), Math.floor((u8.length - 84) / 50));
  const tri = new Float32Array(T * 9);
  for (let i = 0, o = 96; i < T; i++, o += 50) for (let k = 0; k < 9; k++) tri[i * 9 + k] = dv.getFloat32(o + k * 4, true);
  return tri;
}
function stlParseAscii(text) {
  const re = /vertex\s+(\S+)\s+(\S+)\s+(\S+)/g, v = [];
  let m;
  while ((m = re.exec(text))) v.push(+m[1], +m[2], +m[3]);
  return Float32Array.from(v.slice(0, v.length - v.length % 9));
}
// OBJ files are usually Y-up; they are turned so Y-up becomes Z-up. Faces with more corners are fanned.
function objParse(text) {
  const vs = [], out = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (line.startsWith('v ')) { const p = line.split(/\s+/); vs.push(+p[1], -(+p[3]), +p[2]); }
    else if (line.startsWith('f ')) {
      const ix = line.split(/\s+/).slice(1).map(t => { const k = parseInt(t, 10); return k < 0 ? vs.length / 3 + k : k - 1; });
      for (let j = 1; j + 1 < ix.length; j++) for (const k of [ix[0], ix[j], ix[j + 1]]) out.push(vs[3 * k], vs[3 * k + 1], vs[3 * k + 2]);
    }
  }
  return Float32Array.from(out.map(v => (Number.isFinite(v) ? v : 0)));
}
// Binary STL of a mesh (tests, and "download the placed model").
function meshToSTL(pos, idx, name = 'model') {
  const T = idx.length / 3, buf = new ArrayBuffer(84 + 50 * T), dv = new DataView(buf);
  const hdr = ('Magician Smart Controller ' + name).slice(0, 79);
  for (let i = 0; i < hdr.length; i++) dv.setUint8(i, hdr.charCodeAt(i) & 0x7f);
  dv.setUint32(80, T, true);
  for (let t = 0, o = 84; t < T; t++, o += 50) {
    const a = idx[3 * t], b = idx[3 * t + 1], c = idx[3 * t + 2];
    const n = triNormal(pos, a, b, c);
    [n[0], n[1], n[2], pos[3 * a], pos[3 * a + 1], pos[3 * a + 2], pos[3 * b], pos[3 * b + 1], pos[3 * b + 2], pos[3 * c], pos[3 * c + 1], pos[3 * c + 2]]
      .forEach((v, k) => dv.setFloat32(o + 4 * k, v, true));
  }
  return buf;
}
function triNormal(pos, a, b, c) {
  const ux = pos[3 * b] - pos[3 * a], uy = pos[3 * b + 1] - pos[3 * a + 1], uz = pos[3 * b + 2] - pos[3 * a + 2];
  const vx = pos[3 * c] - pos[3 * a], vy = pos[3 * c + 1] - pos[3 * a + 1], vz = pos[3 * c + 2] - pos[3 * a + 2];
  const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx, L = Math.hypot(nx, ny, nz) || 1;
  return [nx / L, ny / L, nz / L, L / 2];               // unit normal and the triangle's area
}

// Indexed mesh: vertices closer than 0.1 µm are merged (an open-addressing hash on the rounded coordinates, fast for
// millions of corners), triangles with a repeated corner are dropped.
function meshFromTris(tri, name = 'model') {
  const N = tri.length / 3;
  let cap = 16; while (cap < 2 * N) cap *= 2;
  const table = new Int32Array(cap).fill(-1), Q = new Float64Array(3 * N), pos = new Float32Array(3 * N), idx = new Uint32Array(N);
  let V = 0;
  for (let i = 0; i < N; i++) {
    const x = tri[3 * i], y = tri[3 * i + 1], z = tri[3 * i + 2];
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) throw new Error('The file has invalid numbers.');
    const qx = Math.round(x * 1e4), qy = Math.round(y * 1e4), qz = Math.round(z * 1e4);
    let h = (Math.imul(qx | 0, 73856093) ^ Math.imul(qy | 0, 19349663) ^ Math.imul(qz | 0, 83492791)) & (cap - 1), v;
    for (;;) {
      v = table[h];
      if (v < 0) { v = V++; table[h] = v; Q[3 * v] = qx; Q[3 * v + 1] = qy; Q[3 * v + 2] = qz; pos[3 * v] = x; pos[3 * v + 1] = y; pos[3 * v + 2] = z; break; }
      if (Q[3 * v] === qx && Q[3 * v + 1] === qy && Q[3 * v + 2] === qz) break;
      h = (h + 1) & (cap - 1);
    }
    idx[i] = v;
  }
  let n = 0;
  for (let t = 0; t < N / 3; t++) {
    const a = idx[3 * t], b = idx[3 * t + 1], c = idx[3 * t + 2];
    if (a !== b && b !== c && c !== a) { idx[3 * n] = a; idx[3 * n + 1] = b; idx[3 * n + 2] = c; n++; }
  }
  if (!n) throw new Error('The model has no triangles.');
  return { name, pos: pos.slice(0, 3 * V), idx: idx.slice(0, 3 * n) };
}
// How many triangles share each edge (open-addressing hash on vertex pairs). Returns { open, bad }.
function meshEdges(idx) {
  const T = idx.length / 3;
  let cap = 16; while (cap < 4 * T) cap *= 2;
  const A = new Int32Array(cap).fill(-1), B = new Int32Array(cap), C = new Uint8Array(cap), D = new Int8Array(cap);
  for (let t = 0; t < T; t++) for (let k = 0; k < 3; k++) {
    const u = idx[3 * t + k], w = idx[3 * t + (k + 1) % 3], a = u < w ? u : w, b = u < w ? w : u;
    let h = (Math.imul(a, 0x9e3779b1) ^ Math.imul(b, 0x85ebca6b)) & (cap - 1);
    while (A[h] >= 0 && !(A[h] === a && B[h] === b)) h = (h + 1) & (cap - 1);
    if (A[h] < 0) { A[h] = a; B[h] = b; }
    if (C[h] < 255) C[h]++;
    D[h] += u < w ? 1 : -1;                            // two neighbours that agree run the edge in opposite directions
  }
  let open = 0, bad = 0, flipped = 0;
  for (let h = 0; h < cap; h++) if (A[h] >= 0) { if (C[h] === 1) open++; else if (C[h] > 2) bad++; else if (D[h] !== 0) flipped++; }
  return { open, bad, flipped };
}

// Size, volume, surface and whether the surface is closed (every edge shared by exactly two triangles).
function meshInfo(mesh) {
  const { pos, idx } = mesh, V = pos.length / 3, T = idx.length / 3;
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < V; i++) for (let k = 0; k < 3; k++) { const v = pos[3 * i + k]; if (v < min[k]) min[k] = v; if (v > max[k]) max[k] = v; }
  let vol = 0, area = 0;
  for (let t = 0; t < T; t++) {
    const a = idx[3 * t], b = idx[3 * t + 1], c = idx[3 * t + 2];
    const ax = pos[3 * a], ay = pos[3 * a + 1], az = pos[3 * a + 2], bx = pos[3 * b], by = pos[3 * b + 1], bz = pos[3 * b + 2];
    const cx = pos[3 * c], cy = pos[3 * c + 1], cz = pos[3 * c + 2];
    vol += (ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)) / 6;
    const ux = bx - ax, uy = by - ay, uz = bz - az, vx = cx - ax, vy = cy - ay, vz = cz - az;
    area += Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) / 2;
  }
  const { open, bad, flipped } = meshEdges(idx);
  return { tris: T, verts: V, min, max, size: [max[0] - min[0], max[1] - min[1], max[2] - min[2]], volume: Math.abs(vol), area,
    inside: vol < 0, open, nonManifold: bad, flipped, closed: open === 0 && bad === 0, oriented: open === 0 && bad === 0 && flipped === 0, checked: true };
}

/* ---------- built-in models (procedural, closed surfaces) ---------- */
// Prism through stacked rings: ring(i) gives the outline [x,y,...] at height z(i); caps are fanned from a centre
// point (every outline here is star-shaped round the centre). hole(i), when given, is an inner outline with the
// same number of points, which makes a ring-shaped part with a hole.
function meshLoft(rings, zs, holes) {
  const pos = [], idx = [], n = rings[0].length / 2, L = rings.length;
  const add = (x, y, z) => { pos.push(x, y, z); return pos.length / 3 - 1; };
  const R = rings.map((r, i) => Array.from({ length: n }, (_, k) => add(r[2 * k], r[2 * k + 1], zs[i])));
  const H = holes ? holes.map((r, i) => Array.from({ length: n }, (_, k) => add(r[2 * k], r[2 * k + 1], zs[i]))) : null;
  for (let i = 0; i + 1 < L; i++) for (let k = 0; k < n; k++) {
    const k2 = (k + 1) % n;
    idx.push(R[i][k], R[i][k2], R[i + 1][k2], R[i][k], R[i + 1][k2], R[i + 1][k]);
    if (H) idx.push(H[i][k], H[i + 1][k2], H[i][k2], H[i][k], H[i + 1][k], H[i + 1][k2]);
  }
  if (H) {
    for (let k = 0; k < n; k++) {
      const k2 = (k + 1) % n;
      idx.push(R[0][k], H[0][k2], R[0][k2], R[0][k], H[0][k], H[0][k2]);
      idx.push(R[L - 1][k], R[L - 1][k2], H[L - 1][k2], R[L - 1][k], H[L - 1][k2], H[L - 1][k]);
    }
  } else {
    const c0 = add(0, 0, zs[0]), c1 = add(0, 0, zs[L - 1]);
    for (let k = 0; k < n; k++) { const k2 = (k + 1) % n; idx.push(c0, R[0][k2], R[0][k], c1, R[L - 1][k], R[L - 1][k2]); }
  }
  return { pos: Float32Array.from(pos), idx: Uint32Array.from(idx) };
}
function ringPts(n, rf, rot = 0) {                 // rf(angle in the ring's own frame, index) → radius; the ring is turned by rot
  const out = [];
  for (let k = 0; k < n; k++) { const u = 2 * Math.PI * k / n, a = rot + u, r = rf(u, k); out.push(r * Math.cos(a), r * Math.sin(a)); }
  return out;
}
const PRINT_SAMPLES = {
  cube: { label: 'Calibration cube 20 mm', make: () => meshLoft([[-10, -10, 10, -10, 10, 10, -10, 10], [-10, -10, 10, -10, 10, 10, -10, 10]], [0, 20]) },
  vase: { label: 'Round vase Ø40 × 60 mm (try the Vase preset)', make: () => {
    const zs = [], rs = [];
    for (let i = 0; i <= 30; i++) { const t = i / 30; zs.push(60 * t); rs.push(ringPts(120, () => 14 + 6 * Math.sin(Math.PI * (0.15 + 0.85 * t)) + 2 * t)); }
    return meshLoft(rs, zs);
  } },
  twist: { label: 'Twisted hexagon vase 50 mm', make: () => {
    const zs = [], rs = [];
    for (let i = 0; i <= 50; i++) { const t = i / 50; zs.push(50 * t); rs.push(ringPts(6 * 24, a => { const s = (a + Math.PI / 6) % (Math.PI / 3) - Math.PI / 6; return 17 * Math.cos(Math.PI / 6) / Math.cos(s); }, t * Math.PI / 2)); }
    return meshLoft(rs, zs);
  } },
  gear: { label: 'Spur gear Ø40 mm, 18 teeth', make: () => {
    const teeth = 18, n = teeth * 16, outer = ringPts(n, (a, k) => { const f = (k % 16) / 16; return f < 0.3 ? 20 : f < 0.45 ? 20 - (f - 0.3) / 0.15 * 3.5 : f < 0.8 ? 16.5 : 16.5 + (f - 0.8) / 0.2 * 3.5; });
    const hole = ringPts(n, () => 4);
    return meshLoft([outer, outer], [0, 8], [hole, hole]);
  } },
  pyramid: { label: 'Pyramid 30 mm (steep sides, no supports needed)', make: () => meshLoft([[-15, -15, 15, -15, 15, 15, -15, 15], [-0.6, -0.6, 0.6, -0.6, 0.6, 0.6, -0.6, 0.6]], [0, 22]) },
  bridge: { label: 'Arch bridge 40 mm (overhang test: try supports)', make: () => {
    // a block with an arch cut through it: outline in the XZ plane, extruded along Y
    const prof = [];
    prof.push([-20, 0], [-12, 0]);
    for (let i = 1; i < 24; i++) { const a = Math.PI - Math.PI * i / 24; prof.push([12 * Math.cos(a), 12 * Math.sin(a)]); }
    prof.push([12, 0], [20, 0], [20, 18], [-20, 18]);
    return meshExtrudeY(prof, 12);
  } },
  ball: { label: 'Ball Ø30 mm (round underside: try supports)', make: () => {
    const zs = [], rs = [];
    for (let i = 0; i <= 40; i++) { const a = -Math.PI / 2 + Math.PI * i / 40, r = Math.max(0.05, 15 * Math.cos(a)); zs.push(15 + 15 * Math.sin(a)); rs.push(ringPts(64, () => r)); }
    return meshLoft(rs, zs);
  } },
};
// Closed polygon in the XZ plane (counter-clockwise), extruded through depth d along Y. Sides are quads; the two caps
// are triangulated by ear clipping.
function meshExtrudeY(prof, d) {
  const pos = [], idx = [], n = prof.length;
  for (const [x, z] of prof) pos.push(x, -d / 2, z);
  for (const [x, z] of prof) pos.push(x, d / 2, z);
  for (let k = 0; k < n; k++) { const k2 = (k + 1) % n; idx.push(k, k2, n + k2, k, n + k2, n + k); }
  const tris = earClip(prof);
  for (const [a, b, c] of tris) idx.push(a, c, b, n + a, n + b, n + c);
  return { pos: Float32Array.from(pos), idx: Uint32Array.from(idx) };
}
function earClip(poly) {
  const V = poly.map((_, i) => i), out = [];
  const area2 = (a, b, c) => (poly[b][0] - poly[a][0]) * (poly[c][1] - poly[a][1]) - (poly[c][0] - poly[a][0]) * (poly[b][1] - poly[a][1]);
  const inside = (p, a, b, c) => area2(a, b, p) >= 0 && area2(b, c, p) >= 0 && area2(c, a, p) >= 0;
  let guard = 0;
  while (V.length > 3 && guard++ < 10000) {
    let cut = false;
    for (let i = 0; i < V.length; i++) {
      const a = V[(i + V.length - 1) % V.length], b = V[i], c = V[(i + 1) % V.length];
      if (area2(a, b, c) <= 1e-12) continue;
      if (V.some(p => p !== a && p !== b && p !== c && inside(p, a, b, c))) continue;
      out.push([a, b, c]); V.splice(i, 1); cut = true; break;
    }
    if (!cut) break;
  }
  if (V.length === 3) out.push(V.slice());
  return out;
}
function sampleMesh(kind) {
  const s = PRINT_SAMPLES[kind];
  if (!s) throw new Error('Unknown sample ' + kind);
  const m = s.make(), mesh = { name: s.label.replace(/ \(.*\)$/, ''), pos: m.pos, idx: m.idx };
  if (meshInfo(mesh).inside) for (let t = 0; t < mesh.idx.length; t += 3) { const q = mesh.idx[t + 1]; mesh.idx[t + 1] = mesh.idx[t + 2]; mesh.idx[t + 2] = q; }
  return mesh;
}

/* ---------- placing the model on the plate ---------- */
const MAT3_I = [1, 0, 0, 0, 1, 0, 0, 0, 1];
function mat3Mul(a, b) {
  const o = new Array(9);
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) o[3 * r + c] = a[3 * r] * b[c] + a[3 * r + 1] * b[3 + c] + a[3 * r + 2] * b[6 + c];
  return o;
}
function mat3Axis(ax, ay, az, ang) {                 // rotation by ang (radians) about a unit axis
  const c = Math.cos(ang), s = Math.sin(ang), t = 1 - c;
  return [t * ax * ax + c, t * ax * ay - s * az, t * ax * az + s * ay,
          t * ax * ay + s * az, t * ay * ay + c, t * ay * az - s * ax,
          t * ax * az - s * ay, t * ay * az + s * ax, t * az * az + c];
}
function mat3Turn(axis, deg) {                       // exact quarter turns stay exact
  const a = deg * Math.PI / 180, c = Math.round(Math.cos(a) * 1e12) / 1e12, s = Math.round(Math.sin(a) * 1e12) / 1e12;
  if (axis === 'x') return [1, 0, 0, 0, c, -s, 0, s, c];
  if (axis === 'y') return [c, 0, s, 0, 1, 0, -s, 0, c];
  return [c, -s, 0, s, c, 0, 0, 0, 1];
}
// place: { R: 3×3 turn (row-major), rz: extra turn about Z in degrees, s: scale, x, y: where the centre of the
// footprint goes, mirror: flip X }. The model always sits on the plate (lowest point at Z0).
function meshPlace(mesh, place) {
  const p = place || {};
  let M = mat3Mul(mat3Turn('z', p.rz || 0), p.R || MAT3_I);
  if (p.mirror) M = mat3Mul([-1, 0, 0, 0, 1, 0, 0, 0, 1], M);
  const s = p.s || 1, src = mesh.pos, V = src.length / 3, out = new Float32Array(src.length);
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < V; i++) {
    const x = src[3 * i], y = src[3 * i + 1], z = src[3 * i + 2];
    for (let k = 0; k < 3; k++) {
      const v = s * (M[3 * k] * x + M[3 * k + 1] * y + M[3 * k + 2] * z);
      out[3 * i + k] = v; if (v < min[k]) min[k] = v; if (v > max[k]) max[k] = v;
    }
  }
  const dx = (p.x || 0) - (min[0] + max[0]) / 2, dy = (p.y || 0) - (min[1] + max[1]) / 2, dz = -min[2];
  let rMax = 0;
  for (let i = 0; i < V; i++) {
    out[3 * i] += dx; out[3 * i + 1] += dy; out[3 * i + 2] += dz;
    const r = Math.hypot(out[3 * i], out[3 * i + 1]); if (r > rMax) rMax = r;
  }
  // a mirror flips the triangles inside out; swap two corners so normals keep pointing outwards
  let idx = mesh.idx;
  if (p.mirror) { idx = Uint32Array.from(idx); for (let t = 0; t < idx.length; t += 3) { const q = idx[t + 1]; idx[t + 1] = idx[t + 2]; idx[t + 2] = q; } }
  return { pos: out, idx, min: [min[0] + dx, min[1] + dy, 0], max: [max[0] + dx, max[1] + dy, max[2] + dz], rMax, M, s };
}
// The turn that puts the model's largest flat outside face on the plate.
function meshLayFlat(mesh, R) {
  const P = meshPlace(mesh, { R }), pos = P.pos, idx = mesh.idx, groups = new Map(), sg = meshInfo({ pos, idx }).inside ? -1 : 1;   // inside-out files
  for (let t = 0; t < idx.length / 3; t++) {
    const a = idx[3 * t], n = triNormal(pos, a, idx[3 * t + 1], idx[3 * t + 2]);
    if (n[3] < 1e-9) continue;
    n[0] *= sg; n[1] *= sg; n[2] *= sg;
    const d = n[0] * pos[3 * a] + n[1] * pos[3 * a + 1] + n[2] * pos[3 * a + 2];
    const key = Math.round(n[0] * 50) + ',' + Math.round(n[1] * 50) + ',' + Math.round(n[2] * 50) + ',' + Math.round(d * 20);
    const g = groups.get(key) || { area: 0, nx: 0, ny: 0, nz: 0, d };
    g.area += n[3]; g.nx += n[0] * n[3]; g.ny += n[1] * n[3]; g.nz += n[2] * n[3];
    groups.set(key, g);
  }
  const cands = [...groups.values()].sort((a, b) => b.area - a.area).slice(0, 24);
  const V = pos.length / 3;
  for (const g of cands) {
    const L = Math.hypot(g.nx, g.ny, g.nz); if (!L) continue;
    const nx = g.nx / L, ny = g.ny / L, nz = g.nz / L;
    let ext = -Infinity;
    for (let i = 0; i < V; i++) ext = Math.max(ext, nx * pos[3 * i] + ny * pos[3 * i + 1] + nz * pos[3 * i + 2]);
    if (ext - g.d > 0.05) continue;                    // not an outside face: part of the model lies beyond it
    // turn (nx,ny,nz) onto (0,0,-1)
    const dot = -nz, ax = -ny, ay = nx, az = 0, s = Math.hypot(ax, ay, az);   // axis n × (0,0,-1)
    let T;
    if (s < 1e-9) T = dot > 0 ? MAT3_I : mat3Turn('x', 180);
    else T = mat3Axis(ax / s, ay / s, az / s, Math.atan2(s, dot));
    return mat3Mul(T, R || MAT3_I).map(v => (Math.abs(v - Math.round(v)) < 1e-9 ? Math.round(v) : v));
  }
  return R || MAT3_I;
}

/* ---------- cutting the mesh into layers ---------- */
// Layer k is printed with its top at z; the model is cut through the middle of each layer.
function layerHeights(height, s) {
  const out = [{ z: s.firstH, h: s.firstH, cut: Math.min(s.firstH / 2, height / 2) }];
  for (let top = s.firstH; ; ) {
    const cut = top + s.layerH / 2;
    if (cut >= height - 1e-9 || out.length > 20000) break;
    top += s.layerH;
    out.push({ z: top, h: s.layerH, cut });
  }
  return out;
}
// Cross-sections at the given heights. Each mesh edge that crosses a plane gives one point, so the segments of
// neighbouring triangles share points exactly and link into loops without guessing. A vertex lying exactly on a
// plane counts as below it, which keeps every crossing triangle at exactly two crossing edges.
function sliceMesh(pos, idx, cuts) {
  const T = idx.length / 3, zmin = new Float64Array(T), zmax = new Float64Array(T);
  for (let t = 0; t < T; t++) {
    const za = pos[3 * idx[3 * t] + 2], zb = pos[3 * idx[3 * t + 1] + 2], zc = pos[3 * idx[3 * t + 2] + 2];
    zmin[t] = Math.min(za, zb, zc); zmax[t] = Math.max(za, zb, zc);
  }
  const order = new Uint32Array(T).map((_, i) => i).sort((a, b) => zmin[a] - zmin[b]);
  const res = [];
  let active = [], ptr = 0;
  for (const z of cuts) {
    while (ptr < T && zmin[order[ptr]] <= z) active.push(order[ptr++]);
    active = active.filter(t => zmax[t] > z);
    res.push(sliceAt(pos, idx, active, z));
  }
  return res;
}
function sliceAt(pos, idx, tris, z) {
  const V = pos.length / 3, ptOf = new Map(), P = [], seg = [];
  const pt = (a, b) => {
    const u = a < b ? a : b, v = a < b ? b : a, key = u * V + v;
    let id = ptOf.get(key);
    if (id === undefined) {
      const zu = pos[3 * u + 2], t = (z - zu) / (pos[3 * v + 2] - zu);
      P.push(pos[3 * u] + t * (pos[3 * v] - pos[3 * u]), pos[3 * u + 1] + t * (pos[3 * v + 1] - pos[3 * u + 1]));
      id = P.length / 2 - 1; ptOf.set(key, id);
    }
    return id;
  };
  const dots = [];
  for (const t of tris) {
    const a = idx[3 * t], b = idx[3 * t + 1], c = idx[3 * t + 2];
    const ua = pos[3 * a + 2] > z, ub = pos[3 * b + 2] > z, uc = pos[3 * c + 2] > z, e = [];
    if (ua !== ub) e.push(pt(a, b));
    if (ub !== uc) e.push(pt(b, c));
    if (uc !== ua) e.push(pt(c, a));
    if (e.length === 2) {
      seg.push(e[0], e[1]);
      // which way round this piece should run: with the outside on its right (ẑ × normal), as a counter-clockwise outline
      const ux = pos[3 * b] - pos[3 * a], uy = pos[3 * b + 1] - pos[3 * a + 1], uz = pos[3 * b + 2] - pos[3 * a + 2];
      const vx = pos[3 * c] - pos[3 * a], vy = pos[3 * c + 1] - pos[3 * a + 1], vz = pos[3 * c + 2] - pos[3 * a + 2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz;
      dots.push((P[2 * e[1]] - P[2 * e[0]]) * -ny + (P[2 * e[1] + 1] - P[2 * e[0] + 1]) * nx);
    }
  }
  // link segments that share a point
  const nP = P.length / 2, nS = seg.length / 2, start = new Int32Array(nP + 1), adj = new Int32Array(seg.length), fill = new Int32Array(nP);
  for (const p of seg) start[p + 1]++;
  for (let i = 0; i < nP; i++) start[i + 1] += start[i];
  for (let s = 0; s < nS; s++) for (const p of [seg[2 * s], seg[2 * s + 1]]) adj[start[p] + fill[p]++] = s;
  const used = new Uint8Array(nS);
  const next = p => { for (let j = start[p]; j < start[p + 1]; j++) if (!used[adj[j]]) return adj[j]; return -1; };
  const loops = [], open = [];
  for (let s0 = 0; s0 < nS; s0++) {
    if (used[s0]) continue;
    used[s0] = 1;
    const fwd = [seg[2 * s0], seg[2 * s0 + 1]];
    let end = fwd[1], closed = false, vote = dots[s0];
    for (;;) {
      if (end === fwd[0]) { closed = true; break; }
      const n = next(end); if (n < 0) break;
      used[n] = 1;
      if (seg[2 * n] === end) { end = seg[2 * n + 1]; vote += dots[n]; } else { end = seg[2 * n]; vote -= dots[n]; }
      fwd.push(end);
    }
    let chain = fwd;
    if (closed) { chain.pop(); if (vote < 0) chain.reverse(); }
    else {
      const back = [];
      for (let st = fwd[0]; ;) { const n = next(st); if (n < 0) break; used[n] = 1; st = seg[2 * n] === st ? seg[2 * n + 1] : seg[2 * n]; back.push(st); }
      chain = back.reverse().concat(fwd);
    }
    const xy = new Array(2 * chain.length);
    for (let i = 0; i < chain.length; i++) { xy[2 * i] = P[2 * chain[i]]; xy[2 * i + 1] = P[2 * chain[i] + 1]; }
    (closed ? loops : open).push(xy);
  }
  let gaps = 0;
  if (open.length) { const j = joinChains(open, 1.0); loops.push(...j.loops); gaps = j.dropped; }
  return { loops, gaps };
}
// Joins open chains (a surface with holes) end to end when the gap is under tol mm; closes what is left if its ends
// are close. Returns the loops and how many chains had to be dropped.
function joinChains(chains, tol) {
  const loops = [];
  let dropped = 0;
  const pool = chains.filter(c => c.length >= 4);
  while (pool.length) {
    let c = pool.pop();
    for (;;) {
      const ex = c[c.length - 2], ey = c[c.length - 1];
      let best = -1, bd = Math.hypot(c[0] - ex, c[1] - ey), rev = false, self = true;
      for (let i = 0; i < pool.length; i++) {
        const o = pool[i], d1 = Math.hypot(o[0] - ex, o[1] - ey), d2 = Math.hypot(o[o.length - 2] - ex, o[o.length - 1] - ey);
        if (d1 < bd) { bd = d1; best = i; rev = false; self = false; }
        if (d2 < bd) { bd = d2; best = i; rev = true; self = false; }
      }
      if (bd > tol) { if (c.length >= 6 && Math.hypot(c[0] - ex, c[1] - ey) < 3 * tol) loops.push(c); else dropped++; break; }
      if (self) { loops.push(c); break; }
      let o = pool.splice(best, 1)[0];
      if (rev) { const r = []; for (let i = o.length - 2; i >= 0; i -= 2) r.push(o[i], o[i + 1]); o = r; }
      c = c.concat(o);
    }
  }
  return { loops, dropped };
}
// Drops points closer than tol to the line through their neighbours (Ramer–Douglas–Peucker on a closed loop).
function simplifyLoop(xy, tol) {
  const n = xy.length / 2;
  if (n <= 4) return xy;
  let far = 0, fd = -1;
  for (let i = 1; i < n; i++) { const d = Math.hypot(xy[2 * i] - xy[0], xy[2 * i + 1] - xy[1]); if (d > fd) { fd = d; far = i; } }
  const keep = new Uint8Array(n); keep[0] = keep[far] = 1;
  const rdp = (i0, i1) => {                            // indices mod n, i1 > i0
    let best = -1, bd = tol;
    const ax = xy[2 * (i0 % n)], ay = xy[2 * (i0 % n) + 1], bx = xy[2 * (i1 % n)], by = xy[2 * (i1 % n) + 1];
    const dx = bx - ax, dy = by - ay, L = Math.hypot(dx, dy);
    for (let i = i0 + 1; i < i1; i++) {
      const px = xy[2 * (i % n)], py = xy[2 * (i % n) + 1];
      const d = L < 1e-12 ? Math.hypot(px - ax, py - ay) : Math.abs(dx * (py - ay) - dy * (px - ax)) / L;
      if (d > bd) { bd = d; best = i; }
    }
    if (best >= 0) { keep[best % n] = 1; rdp(i0, best); rdp(best, i1); }
  };
  rdp(0, far); rdp(far, n);
  const out = [];
  for (let i = 0; i < n; i++) if (keep[i]) out.push(xy[2 * i], xy[2 * i + 1]);
  return out;
}

/* ---------- polygon helpers (Clipper paths in µm; regions are outer outlines plus holes, non-zero fill) ---------- */
function clPath(xy) { const p = []; for (let i = 0; i < xy.length; i += 2) p.push({ X: Math.round(xy[i] * P3_SC), Y: Math.round(xy[i + 1] * P3_SC) }); return p; }
function clXY(path) { const o = new Array(2 * path.length); for (let i = 0; i < path.length; i++) { o[2 * i] = path[i].X / P3_SC; o[2 * i + 1] = path[i].Y / P3_SC; } return o; }
function clRun(type, subj, clip, fill = CL.PolyFillType.pftNonZero) {
  const c = new CL.Clipper(), out = [];
  if (subj.length) c.AddPaths(subj, CL.PolyType.ptSubject, true);
  if (clip && clip.length) c.AddPaths(clip, CL.PolyType.ptClip, true);
  c.Execute(type, out, fill, fill);
  return out;
}
const clUnion = paths => (paths.length ? clRun(CL.ClipType.ctUnion, paths, null) : []);
const clDiff = (a, b) => (!a.length ? [] : !b || !b.length ? a : clRun(CL.ClipType.ctDifference, a, b));
const clInter = (a, b) => (!a.length || !b || !b.length ? [] : clRun(CL.ClipType.ctIntersection, a, b));
function clOffset(paths, mm, round = false) {
  if (!paths.length) return [];
  const co = new CL.ClipperOffset(3, 0.005 * P3_SC), out = [];
  co.AddPaths(paths, round ? CL.JoinType.jtRound : CL.JoinType.jtMiter, CL.EndType.etClosedPolygon);
  co.Execute(out, mm * P3_SC);
  return out;
}
function clArea(paths) { let a = 0; for (const p of paths) a += CL.Clipper.Area(p); return a / (P3_SC * P3_SC); }
// Separate islands: each is [outline, ...holes]. evenOdd: for raw cross-section loops (any orientation).
function clIslands(paths, evenOdd = false) {
  if (!paths.length) return [];
  const c = new CL.Clipper(), tree = new CL.PolyTree(), f = evenOdd ? CL.PolyFillType.pftEvenOdd : CL.PolyFillType.pftNonZero;
  c.AddPaths(paths, CL.PolyType.ptSubject, true);
  c.Execute(CL.ClipType.ctUnion, tree, f, f);
  const out = [];
  const walk = node => { for (const o of node.Childs()) { const isl = [o.Contour()]; for (const h of o.Childs()) { isl.push(h.Contour()); walk(h); } out.push(isl); } };
  walk(tree);
  return out;
}
// Keeps islands of at least minMM2; returns them flattened into one region.
function clKeepArea(paths, minMM2) { return clIslands(paths).filter(isl => clArea(isl) >= minMM2).flat(); }

/* ---------- float geometry for travel and fill decisions ---------- */
function polysIn(polys, x, y) {                     // even-odd point-in-polygon over float outlines [x,y,...]
  let inside = false;
  for (const P of polys) {
    for (let i = 0, j = P.length - 2; i < P.length; j = i, i += 2) {
      const yi = P[i + 1], yj = P[j + 1];
      if ((yi > y) !== (yj > y) && x < (P[j] - P[i]) * (y - yi) / (yj - yi) + P[i]) inside = !inside;
    }
  }
  return inside;
}
// Is (x,y) within eps of an outline edge? (Links between fill lines run along the edge of the area.)
function polysNear(polys, x, y, eps) {
  for (const P of polys) for (let i = 0, j = P.length - 2; i < P.length; j = i, i += 2) {
    const px = P[j], py = P[j + 1], ex = P[i] - px, ey = P[i + 1] - py, L2 = ex * ex + ey * ey;
    const u = L2 > 0 ? Math.max(0, Math.min(1, ((x - px) * ex + (y - py) * ey) / L2)) : 0;
    if ((px + u * ex - x) ** 2 + (py + u * ey - y) ** 2 <= eps * eps) return true;
  }
  return false;
}
// Does the segment a→b cross any outline edge strictly between t0 and t1 (fractions along a→b)?
function polysCross(polys, ax, ay, bx, by, t0 = 0, t1 = 1) {
  const dx = bx - ax, dy = by - ay;
  const x0 = Math.min(ax, bx), x1 = Math.max(ax, bx), y0 = Math.min(ay, by), y1 = Math.max(ay, by);
  for (const P of polys) {
    for (let i = 0, j = P.length - 2; i < P.length; j = i, i += 2) {
      const px = P[j], py = P[j + 1], qx = P[i], qy = P[i + 1];
      if ((px < x0 && qx < x0) || (px > x1 && qx > x1) || (py < y0 && qy < y0) || (py > y1 && qy > y1)) continue;
      const ex = qx - px, ey = qy - py, den = dx * ey - dy * ex;
      if (Math.abs(den) < 1e-15) continue;
      const t = ((px - ax) * ey - (py - ay) * ex) / den, u = ((px - ax) * dy - (py - ay) * dx) / den;
      if (t > t0 && t < t1 && u >= 0 && u <= 1) return true;
    }
  }
  return false;
}
// Fill lines: scan lines at angle deg (degrees), spacing sp mm, on a fixed grid so the same angle stacks from layer
// to layer. Returns segments [x0,y0,x1,y1] grouped by scan line.
function scanLines(polys, deg, sp) {
  const a = deg * Math.PI / 180, ca = Math.cos(a), sa = Math.sin(a);
  const E = [];                                         // edges in the turned frame: u along the line, v across
  let vmin = Infinity, vmax = -Infinity;
  for (const P of polys) for (let i = 0, j = P.length - 2; i < P.length; j = i, i += 2) {
    const u0 = P[j] * ca + P[j + 1] * sa, v0 = -P[j] * sa + P[j + 1] * ca, u1 = P[i] * ca + P[i + 1] * sa, v1 = -P[i] * sa + P[i + 1] * ca;
    E.push(u0, v0, u1, v1); vmin = Math.min(vmin, v0, v1); vmax = Math.max(vmax, v0, v1);
  }
  if (!E.length) return [];
  const k0 = Math.ceil(vmin / sp - 0.5), k1 = Math.floor(vmax / sp - 0.5), nk = k1 - k0 + 1;
  if (nk <= 0) return [];
  const rows = Array.from({ length: nk }, () => []);
  for (let e = 0; e < E.length; e += 4) {
    const v0 = E[e + 1], v1 = E[e + 3], lo = Math.min(v0, v1), hi = Math.max(v0, v1);
    for (let k = Math.max(k0, Math.ceil(lo / sp - 0.5)); k <= Math.min(k1, Math.floor(hi / sp - 0.5)); k++) {
      const v = (k + 0.5) * sp;
      if ((v0 <= v && v < v1) || (v1 <= v && v < v0)) rows[k - k0].push(E[e] + (v - v0) / (v1 - v0) * (E[e + 2] - E[e]));
    }
  }
  const out = [];
  for (let r = 0; r < nk; r++) {
    const xs = rows[r].sort((p, q) => p - q), v = (k0 + r + 0.5) * sp;
    for (let j = 0; j + 1 < xs.length; j += 2) {
      if (xs[j + 1] - xs[j] < 0.05) continue;
      out.push([xs[j] * ca - v * sa, xs[j] * sa + v * ca, xs[j + 1] * ca - v * sa, xs[j + 1] * sa + v * ca]);
    }
  }
  return out;
}
// Nearest-neighbour order for open fill segments; each next segment may be flipped. Consecutive segments are joined
// by a short extruded link when the link stays inside the area (zig-zag), which saves travel and retraction.
function orderSegments(segs, pos, link, polys) {
  const n = segs.length, used = new Uint8Array(n), out = [];
  let cx = pos.x, cy = pos.y, cur = null;
  for (let m = 0; m < n; m++) {
    let best = -1, bd = Infinity, flip = false;
    for (let i = 0; i < n; i++) {
      if (used[i]) continue;
      const s = segs[i], d0 = (s[0] - cx) ** 2 + (s[1] - cy) ** 2, d1 = (s[2] - cx) ** 2 + (s[3] - cy) ** 2;
      if (d0 < bd) { bd = d0; best = i; flip = false; }
      if (d1 < bd) { bd = d1; best = i; flip = true; }
    }
    used[best] = 1;
    const s = segs[best], ax = flip ? s[2] : s[0], ay = flip ? s[3] : s[1], bx = flip ? s[0] : s[2], by = flip ? s[1] : s[3];
    const d = Math.sqrt(bd);
    const mx = (cx + ax) / 2, my = (cy + ay) / 2;
    if (cur && d <= link && d > 1e-6 && (polysIn(polys, mx, my) || polysNear(polys, mx, my, 1e-4)) && !polysCross(polys, cx, cy, ax, ay, 0.02, 0.98)) cur.push(ax, ay, bx, by);
    else { cur = [ax, ay, bx, by]; out.push(cur); }
    cx = bx; cy = by;
  }
  return out;
}
function nearestVertex(xy, x, y) {
  let best = 0, bd = Infinity;
  for (let i = 0; i < xy.length; i += 2) { const d = (xy[i] - x) ** 2 + (xy[i + 1] - y) ** 2; if (d < bd) { bd = d; best = i / 2; } }
  return best;
}
function rotateLoop(xy, k) { return k ? xy.slice(2 * k).concat(xy.slice(0, 2 * k)) : xy.slice(); }
function loopLength(xy, closed = true) {
  let L = 0;
  for (let i = 2; i < xy.length; i += 2) L += Math.hypot(xy[i] - xy[i - 2], xy[i + 1] - xy[i - 1]);
  if (closed && xy.length >= 4) L += Math.hypot(xy[0] - xy[xy.length - 2], xy[1] - xy[xy.length - 1]);
  return L;
}
function hullXY(pts) {                                 // pts: [x,y,...]; returns the convex hull [x,y,...] counter-clockwise
  const P = [];
  for (let i = 0; i < pts.length; i += 2) P.push([pts[i], pts[i + 1]]);
  P.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (P.length < 3) return P.flat();
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], up = [];
  for (const p of P) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
  for (let i = P.length - 1; i >= 0; i--) { const p = P[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p); }
  return lo.slice(0, -1).concat(up.slice(0, -1)).flat();
}

/* ---------- settings ---------- */
const PRINT_LIMITS = {
  layerH: [0.05, 0.32], firstH: [0.1, 0.5], lineW: [0.3, 0.8], firstW: [0.3, 1.0], nozzle: [0.2, 1.0], filament: [1.5, 3.0], flow: [50, 150],
  walls: [0, 8], top: [0, 30], bottom: [0, 30], infill: [0, 100],
  vWall: [1, 60], vOuter: [1, 60], vInfill: [1, 80], vSolid: [1, 80], vFirst: [1, 40], vTravel: [5, 150], vSupport: [1, 80], vZ: [1, 30],
  temp: [170, 250], retract: [0, 15], vRetract: [5, 100], retractMin: [0, 20], zHop: [0, 5],
  skirt: [0, 8], skirtDist: [0.5, 20], skirtMin: [0, 2000], brim: [0, 30], supportAngle: [20, 85], supportGap: [1, 10], supportXY: [0.2, 3],
  minLayerTime: [0, 120], minSpeed: [0.5, 20], plateD: [20, 200], maxH: [1, 150],
};
// Fills in defaults, checks every number and applies what vase mode needs (one wall, no infill, no top).
function printSettings(src) {
  const s = { ...PRINT_DEFAULTS, ...(src || {}) };
  for (const [k, [lo, hi]] of Object.entries(PRINT_LIMITS)) {
    const v = +s[k];
    if (!Number.isFinite(v)) throw new Error(`Setting "${k}" is not a number.`);
    if (v < lo - 1e-9 || v > hi + 1e-9) throw new Error(`Setting "${k}" must be between ${lo} and ${hi} (it is ${v}).`);
    s[k] = v;
  }
  for (const k of ['walls', 'top', 'bottom', 'skirt', 'brim']) s[k] = Math.round(s[k]);
  if (s.layerH > 0.8 * s.nozzle + 1e-9) throw new Error(`Layers can be at most 80 % of the nozzle (${(0.8 * s.nozzle).toFixed(2)} mm).`);
  if (!['lines', 'grid'].includes(s.pattern)) s.pattern = 'lines';
  if (!['off', 'plate', 'all'].includes(s.support)) s.support = 'off';
  if (!['nearest', 'rear'].includes(s.seam)) s.seam = 'nearest';
  s.vase = !!s.vase; s.fan = !!s.fan;
  if (s.vase) { s.walls = 1; s.top = 0; s.infill = 0; }
  return s;
}

/* ---------- supports ---------- */
// Areas of layer i that stick out further than the support angle allows over layer i-1 need holding up. Support goes
// down from there, one empty layer below the model and one above anything it stands on, and keeps supportXY away
// from the model's sides. 'plate': only columns that reach the plate.
function supportRegions(R, layers, s) {
  const L = R.length, S = new Array(L).fill(null).map(() => []);
  if (s.support === 'off' || L < 3) return S;
  const over = new Array(L).fill(null).map(() => []), grown = R.map(r => clOffset(r, s.supportXY, true));
  for (let i = 1; i < L; i++) {
    if (!R[i].length) continue;
    const d = layers[i].h * Math.tan(s.supportAngle * Math.PI / 180);
    over[i] = clKeepArea(clDiff(R[i], clOffset(R[i - 1], d)), 0.4);
  }
  let need = [];
  const close = 0.6;                                   // closes the thin gaps between the overhang rings of successive layers
  for (let i = L - 1; i >= 0; i--) {
    if (i + 2 < L && over[i + 2].length) need = clOffset(clOffset(clUnion(need.concat(over[i + 2])), close, true), -close, true);
    if (!need.length) continue;
    need = clDiff(need, grown[i]);
    S[i] = i > 0 ? clDiff(need, grown[i - 1]) : need;
  }
  if (s.support === 'plate') {
    let below = [];
    for (let i = 0; i < L; i++) {
      if (below.length && S[i].length) S[i] = clDiff(S[i], below);
      if (R[i].length) below = clUnion(below.concat(grown[i]));
    }
  }
  for (let i = 0; i < L; i++) if (S[i].length) S[i] = clKeepArea(S[i], 1.5);
  return S;
}

/* ---------- G-code writer ---------- */
const fmt = (v, d = 3) => { const r = +v.toFixed(d); return (Object.is(r, -0) ? 0 : r).toString(); };
function gcodeOut(s) {
  const G = [], segP = [], segT = [], segL = [];
  const st = { x: 0, y: 0, z: 0, e: 0, f: -1, ret: false, resetE: true, known: false, time: 0, fil: 0, type: -1, layer: 0 };
  const fa = Math.PI * (s.filament / 2) ** 2, flow = s.flow / 100;
  const F = v => { const f = Math.round(v * 60); if (f === st.f) return ''; st.f = f; return ' F' + f; };
  const seg = (x0, y0, z0, x1, y1, z1, t) => { segP.push(x0, y0, z0, x1, y1, z1); segT.push(t); segL.push(G.length - 1); };
  const o = {
    G, st,
    line(l) { G.push(l); },
    retract() {
      if (st.ret || s.retract <= 0) return;
      st.e -= s.retract; G.push('G1 E' + fmt(st.e, 5) + F(s.vRetract)); st.ret = true; st.time += s.retract / s.vRetract;
    },
    unretract() {
      if (!st.ret) return;
      st.e += s.retract; G.push('G1 E' + fmt(st.e, 5) + F(s.vRetract)); st.ret = false; st.time += s.retract / s.vRetract;
    },
    z(z) {
      if (st.known && Math.abs(z - st.z) < 1e-6) return;
      G.push('G0 Z' + fmt(z) + F(s.vZ)); st.time += Math.abs(z - st.z) / s.vZ; st.z = z;
    },
    travel(x, y, combOK) {
      const d = Math.hypot(x - st.x, y - st.y);
      if (st.known && d < 1e-4) return;
      const ret = st.known && !st.ret && d > s.retractMin && !combOK;
      if (ret) o.retract();
      const hop = ret && s.zHop > 0 && st.known;
      if (hop) { G.push('G0 Z' + fmt(st.z + s.zHop) + F(s.vZ)); st.time += s.zHop / s.vZ; }
      G.push('G0 X' + fmt(x) + ' Y' + fmt(y) + F(s.vTravel));
      if (st.known) seg(st.x, st.y, st.z, x, y, st.z, 0);
      st.time += d / s.vTravel;
      if (hop) { G.push('G0 Z' + fmt(st.z) + F(s.vZ)); st.time += s.zHop / s.vZ; }
      st.x = x; st.y = y; st.known = true;
    },
    extrude(x, y, w, h, v, type, z) {
      o.unretract();
      if (st.resetE) { G.push('G92 E0'); st.e = 0; st.resetE = false; }
      const zz = z === undefined ? st.z : z, d = Math.hypot(x - st.x, y - st.y, zz - st.z);
      if (d < 1e-5) return;
      const de = d * w * h * flow / fa;
      st.e += de; st.fil += de; st.time += d / v;
      if (type !== st.type) { G.push(';TYPE:' + ['TRAVEL', 'WALL-OUTER', 'WALL-INNER', 'SKIN', 'FILL', 'SUPPORT', 'SKIRT'][type]); st.type = type; }
      G.push('G1 X' + fmt(x) + ' Y' + fmt(y) + (z === undefined ? '' : ' Z' + fmt(zz)) + ' E' + fmt(st.e, 5) + F(v));
      seg(st.x, st.y, st.z, x, y, zz, type);
      st.x = x; st.y = y; st.z = zz;
    },
    preview() {
      return { pos: Float32Array.from(segP), type: Uint8Array.from(segT), line: Uint32Array.from(segL) };
    },
  };
  return o;
}

/* ---------- planning and writing ---------- */
// Generator: yields progress (0–1) and leaves the result in out.result. Run it with slicePrintSync (tests) or
// slicePrintAsync (the page, so it stays responsive).
function* slicePrintSteps(placed, settings, out, meta = {}) {
  const s = printSettings(settings), warn = [];
  const height = placed.max[2] - placed.min[2], R0 = s.plateD / 2;
  if (!(height > 0.05)) throw new Error('The model is flat: it has no height to print.');
  if (height > s.maxH + 1e-6) throw new Error(`The model is ${height.toFixed(1)} mm tall; the printer takes at most ${s.maxH} mm. Scale it down.`);
  if (placed.rMax > R0 + 1e-6) throw new Error(`The model reaches ${placed.rMax.toFixed(1)} mm from the plate centre; the plate is Ø${s.plateD} mm. Scale it down or move it.`);
  const layers = layerHeights(height, s), L = layers.length;
  // Closed, consistently oriented surfaces: loops are oriented, and overlapping bodies merge (non-zero filling).
  // Otherwise even-odd filling, which needs no orientation (but makes the overlap of two bodies a hole).
  const E = meshEdges(placed.idx), oriented = E.open === 0 && E.bad === 0 && E.flipped === 0;
  if (!oriented && E.flipped) warn.push(`Some of the model's faces point inwards (${E.flipped} edges disagree); where parts overlap they may print hollow. Repairing the STL helps.`);
  // 1. cross-sections
  const R = new Array(L), islandsOf = new Array(L);
  {
    const { pos, idx } = placed, T = idx.length / 3, zmin = new Float64Array(T), zmax = new Float64Array(T);
    for (let t = 0; t < T; t++) {
      const za = pos[3 * idx[3 * t] + 2], zb = pos[3 * idx[3 * t + 1] + 2], zc = pos[3 * idx[3 * t + 2] + 2];
      zmin[t] = Math.min(za, zb, zc); zmax[t] = Math.max(za, zb, zc);
    }
    const order = new Uint32Array(T).map((_, i) => i).sort((a, b) => zmin[a] - zmin[b]);
    let active = [], ptr = 0, gaps = 0, empty = 0;
    for (let i = 0; i < L; i++) {
      const z = layers[i].cut;
      while (ptr < T && zmin[order[ptr]] <= z) active.push(order[ptr++]);
      active = active.filter(t => zmax[t] > z);
      const c = sliceAt(pos, idx, active, z);
      gaps += c.gaps;
      const paths = c.loops.map(l => clPath(simplifyLoop(l, 0.01))).filter(p => p.length >= 3);
      const isl = clIslands(paths, !oriented).filter(p => clArea(p) > 0.02);
      islandsOf[i] = isl; R[i] = isl.flat();
      if (!isl.length) empty++;
      if (i % 4 === 0) yield 0.3 * i / L;
    }
    if (gaps) warn.push(`The model's surface has gaps (${gaps} open edges on cuts); some walls may be missing. Repairing the STL helps.`);
    if (empty === L) throw new Error('Nothing to print: the model has no closed cross-sections (is it a surface without thickness?).');
    if (!islandsOf[0].length) warn.push('The model does not touch the plate on the first layer.');
  }
  // 2. supports
  const SUP = supportRegions(R, layers, s);
  yield 0.4;
  if (s.support === 'off') {
    // tell the user when large areas hang in the air
    let hang = 0;
    for (let i = 2; i < L; i++) {
      if (!R[i].length) continue;
      const d = layers[i].h * Math.tan(60 * Math.PI / 180);
      hang += Math.max(0, clArea(clDiff(R[i], clOffset(R[i - 1], d))));
      if (hang > 25) break;
    }
    if (hang > 25) warn.push('Parts of the model hang in the air with nothing below them. Turn the model, or switch on supports.');
  }
  // 3. layer by layer: plan the paths, then write them
  const W = gcodeOut(s), body = [], layerInfo = [];
  let pos = { x: 0, y: 0 }, prevZ = 0;
  const vaseFrom = s.vase ? Math.min(s.bottom, L) : Infinity;
  for (let i = 0; i < L; i++) {
    const Ly = layers[i], first = i === 0, w = first ? s.firstW : s.lineW, h = Ly.h;
    const vF = v => (first ? Math.min(v, s.vFirst) : v);
    const paths = [];
    const add = (xy, closed, type, v, comb, extra) => { paths.push({ xy, closed, type, v, w, h, comb, ...extra }); pos = closed ? { x: xy[0], y: xy[1] } : { x: xy[xy.length - 2], y: xy[xy.length - 1] }; };
    const addLoop = (xy, type, v, comb, seamRear) => {
      const k = seamRear ? (() => { let b = 0; for (let j = 2; j < xy.length; j += 2) if (xy[j + 1] > xy[2 * b + 1] + 1e-6) b = j / 2; return b; })() : nearestVertex(xy, pos.x, pos.y);
      add(rotateLoop(xy, k), true, type, v, comb);
    };
    const isl = islandsOf[i];
    if (i >= vaseFrom) {
      // vase: one continuous outer wall rising through the layer
      let best = null, ba = 0;
      for (const I of isl) { const a = clArea(I); if (a > ba) { ba = a; best = I; } }
      if (isl.length > 1 && i === vaseFrom) warn.push('Vase mode prints only the largest part of each layer.');
      if (best) {
        const loops = clOffset([best[0]], -w / 2).filter(p => CL.Clipper.Area(p) > 0);
        let lp = null, la = 0;
        for (const p of loops) { const a = CL.Clipper.Area(p); if (a > la) { la = a; lp = p; } }
        if (lp) { const xy = clXY(lp); paths.push({ xy: rotateLoop(xy, nearestVertex(xy, pos.x, pos.y)), closed: true, type: 1, v: s.vOuter, w, h, spiral: [prevZ, Ly.z] }); pos = { x: paths[0].xy[0], y: paths[0].xy[1] }; }
      }
    } else {
      // first layer: skirt and brim
      if (first) {
        const outers = isl.map(I => I[0]);
        const brim = [];
        for (let k = 0; k < s.brim; k++) brim.push(clUnion(clOffset(outers, w / 2 + k * w, true)));
        let hullPts = [];
        for (const p of outers.concat(brim.length ? brim[brim.length - 1] : [], SUP[0])) for (const q of p) hullPts.push(q.X / P3_SC, q.Y / P3_SC);
        const skirtLoops = [];
        if (s.skirt > 0 && hullPts.length >= 6) {
          const hull = clPath(hullXY(hullPts));
          let total = 0;
          for (let k = 0; k < 8 && (k < s.skirt || total < s.skirtMin); k++) {
            const off = clOffset([hull], s.skirtDist + w / 2 + k * w, true);
            for (const p of off) total += loopLength(clXY(p));
            skirtLoops.unshift(off);
          }
          const reach = Math.max(...skirtLoops[0].flatMap(p => p.map(q => Math.hypot(q.X, q.Y) / P3_SC)));
          if (reach > R0 + 0.5) warn.push(`The skirt reaches ${reach.toFixed(1)} mm from the plate centre, past the Ø${s.plateD} mm plate.`);
        }
        for (const ring of skirtLoops) for (const p of ring) addLoop(clXY(p), 6, s.vFirst, null);
        for (let k = brim.length - 1; k >= 0; k--) for (const p of brim[k]) addLoop(clXY(p), 6, s.vFirst, null);
      }
      // supports
      if (SUP[i].length) {
        const polys = SUP[i].map(clXY);
        for (const c of orderSegments(scanLines(polys, 0, s.supportGap), pos, 1.6 * s.supportGap, polys)) add(c, false, 5, vF(s.vSupport), polys);
      }
      // solid where the layer is exposed above or below
      let solidRegion = [];
      if (s.top + s.bottom > 0) {
        if (i - s.bottom < 0 || (s.top > 0 && i + s.top >= L)) solidRegion = R[i];
        else {
          let cov = null;
          for (let k = 1; k <= s.top && (!cov || cov.length); k++) cov = cov ? clInter(cov, R[i + k]) : R[i + k];
          for (let k = 1; k <= s.bottom && (!cov || cov.length); k++) cov = cov ? clInter(cov, R[i - k]) : R[i - k];
          solidRegion = clDiff(R[i], cov || []);
        }
      }
      // islands, nearest first
      const todo = isl.slice();
      while (todo.length) {
        let bi = 0, bd = Infinity;
        todo.forEach((I, j) => { for (const q of I[0]) { const d = (q.X / P3_SC - pos.x) ** 2 + (q.Y / P3_SC - pos.y) ** 2; if (d < bd) { bd = d; bi = j; } } });
        const I = todo.splice(bi, 1)[0];
        const comb = clOffset(I, -w / 2).map(clXY);
        // walls, innermost first
        const walls = [];
        for (let k = 0; k < s.walls; k++) {
          let off = clOffset(I, -(w / 2 + k * w));
          if (!off.length && k === 0) off = clOffset(I, -0.3 * w);           // thin part: squeeze one wall in
          if (!off.length) break;
          walls.push(off);
        }
        for (let k = walls.length - 1; k >= 0; k--) {
          const loops = walls[k].map(clXY), done = new Uint8Array(loops.length);
          for (let m = 0; m < loops.length; m++) {
            let bj = -1, bdd = Infinity;
            loops.forEach((xy, j) => { if (done[j]) return; const v = nearestVertex(xy, pos.x, pos.y), d = (xy[2 * v] - pos.x) ** 2 + (xy[2 * v + 1] - pos.y) ** 2; if (d < bdd) { bdd = d; bj = j; } });
            done[bj] = 1;
            addLoop(loops[bj], k === 0 ? 1 : 2, vF(k === 0 ? s.vOuter : s.vWall), comb, s.seam === 'rear' && k === 0);
          }
        }
        // infill
        const fillArea = walls.length ? clOffset(I, -(walls.length * w) + 0.15 * w) : s.walls === 0 ? clOffset(I, -w / 2) : [];
        if (!fillArea.length) continue;
        let solid = solidRegion.length ? clKeepArea(clInter(fillArea, clOffset(solidRegion, w)), w * w) : [];
        const sparse = solid.length ? clKeepArea(clDiff(fillArea, solid), w * w) : fillArea;
        const ang = i % 2 ? -45 : 45;
        if (solid.length) {
          const polys = solid.map(clXY);
          for (const c of orderSegments(scanLines(polys, ang, w), pos, 2.2 * w, polys)) add(c, false, 3, vF(s.vSolid), comb);
        }
        if (sparse.length && s.infill > 0) {
          const polys = sparse.map(clXY);
          const sp = (s.pattern === 'grid' ? 2 : 1) * w * 100 / s.infill;
          let segs = scanLines(polys, ang, sp);
          if (s.pattern === 'grid') segs = scanLines(polys, 45, sp).concat(scanLines(polys, -45, sp));
          for (const c of orderSegments(segs, pos, 1.8 * sp, polys)) add(c, false, s.infill >= 99 ? 3 : 4, vF(s.infill >= 99 ? s.vSolid : s.vInfill), comb);
        }
      }
    }
    // slow down short layers so each has time to cool
    let tE = 0, tT = 0, px = W.st.x, py = W.st.y;
    for (const p of paths) { tT += Math.hypot(p.xy[0] - px, p.xy[1] - py) / s.vTravel; tE += loopLength(p.xy, p.closed) / p.v; px = p.closed ? p.xy[0] : p.xy[p.xy.length - 2]; py = p.closed ? p.xy[1] : p.xy[p.xy.length - 1]; }
    let k = 1;
    if (s.minLayerTime > 0 && tE > 0 && tE + tT < s.minLayerTime) k = tE / Math.max(1e-6, s.minLayerTime - tT);
    // write the layer
    const line0 = W.G.length;
    W.line(`;LAYER:${i}`);
    W.line(`;Z:${fmt(Ly.z)}`);
    if (i > 0 && !(i > vaseFrom)) W.retract();      // retract on layer change (not inside the vase spiral)
    W.st.resetE = true;
    if (first && paths.length) { W.travel(paths[0].xy[0], paths[0].xy[1], true); }   // over the start point first, then down
    if (paths.length && !paths[0].spiral) W.z(Ly.z);
    let lastComb = null;
    for (const p of paths) {
      const v = Math.max(Math.min(p.v, s.minSpeed), p.v * k);
      const sx = p.xy[0], sy = p.xy[1];
      const combOK = p.comb && p.comb === lastComb && !polysCross(p.comb, W.st.x, W.st.y, sx, sy);
      if (p.spiral) {
        const gap = Math.hypot(sx - W.st.x, sy - W.st.y);
        if (W.st.known && gap < 2 * p.w && !W.st.ret) { if (gap > 1e-4) W.extrude(sx, sy, p.w, p.h, v, p.type, p.spiral[0]); }   // carry on round
        else if (!W.st.known || gap > 1e-4) { W.retract(); W.z(p.spiral[0]); W.travel(sx, sy, false); }
        const n = p.xy.length / 2, total = loopLength(p.xy, true);
        let run = 0;
        for (let j = 1; j <= n; j++) {
          const x = p.xy[2 * (j % n)], y = p.xy[2 * (j % n) + 1];
          run += Math.hypot(x - p.xy[2 * (j - 1)], y - p.xy[2 * (j - 1) + 1]);
          W.extrude(x, y, p.w, p.h, v, p.type, p.spiral[0] + (p.spiral[1] - p.spiral[0]) * run / total);
        }
      } else {
        W.travel(sx, sy, combOK);
        for (let j = 2; j < p.xy.length; j += 2) W.extrude(p.xy[j], p.xy[j + 1], p.w, p.h, v, p.type);
        if (p.closed) W.extrude(sx, sy, p.w, p.h, v, p.type);
      }
      lastComb = p.comb || null;
    }
    layerInfo.push({ z: Ly.z, h, line: line0, time: W.st.time, paths: paths.length });
    prevZ = Ly.z;
    if (i % 2 === 0) yield 0.4 + 0.55 * (i + 1) / L;
  }
  W.retract();
  // assemble: header, start code, body, end code
  const travelF = Math.round(s.vTravel * 60);
  const fill = t => t.replace(/\{temp\}/g, fmt(s.temp, 0)).replace(/\{travelF\}/g, travelF).replace(/\{travel_speed\}/g, travelF);
  let start = fill(s.startCode).split('\n');
  if (!s.fan) start = start.filter(l => !/^\s*M106\b/i.test(l)).concat(['M107 ; fan off']);
  const end = fill(s.endCode).split('\n');
  const time = W.st.time * 1.1, filMM = W.st.fil, vol = filMM * Math.PI * (s.filament / 2) ** 2, grams = vol * 1.24 / 1000;
  // header comments in plain ASCII (some tools mind other characters); comments are never sent to the printer
  const hdr = [
    `; Magician Smart Controller ${P3_VERSION} - G-code for the Dobot Magician 3D-printing kit (Dobot 3D-printer firmware)`,
    `; Model: ${(meta.name || 'model').replace(/[^\x20-\x7e]/g, '?')} - ${fmt(placed.max[0] - placed.min[0], 1)} x ${fmt(placed.max[1] - placed.min[1], 1)} x ${fmt(height, 1)} mm`,
    `; Layers: ${L} x ${s.layerH} mm (first ${s.firstH} mm); walls ${s.walls}; top ${s.top}, bottom ${s.bottom}; infill ${s.infill} % ${s.pattern}; supports ${s.support}${s.vase ? '; vase mode' : ''}`,
    `; Nozzle ${s.nozzle} mm, filament ${s.filament} mm, ${s.temp} C, flow ${s.flow} %; speeds: walls ${s.vWall}/${s.vOuter}, infill ${s.vInfill}, solid ${s.vSolid}, first layer ${s.vFirst}, travel ${s.vTravel} mm/s`,
    `; Retraction ${s.retract} mm at ${s.vRetract} mm/s; round plate ${s.plateD} mm across, centred at X0 Y0, top of the plate at Z0`,
    `; Print time about ${Math.round(time / 60)} min; filament ${fmt(filMM / 1000, 2)} m (${fmt(grams, 1)} g PLA)`,
    ';FLAVOR:RepRap', `;TIME:${Math.round(time)}`, `;Filament used: ${fmt(filMM / 1000, 3)}m`, `;Layer height: ${s.layerH}`, `;LAYER_COUNT:${L}`,
  ];
  const off = hdr.length + start.length;
  const G = hdr.concat(start, W.G, [';END'], end);
  const pv = W.preview();
  for (let j = 0; j < pv.line.length; j++) pv.line[j] += off;
  const LI = layerInfo.map((l, j) => ({ ...l, line: l.line + off }));
  // where each layer's moves start in the preview
  let sp = 0;
  for (let j = 0; j < LI.length; j++) {
    const nextLine = j + 1 < LI.length ? LI[j + 1].line : Infinity;
    LI[j].seg0 = sp;
    while (sp < pv.line.length && pv.line[sp] < nextLine) sp++;
    LI[j].seg1 = sp;
  }
  out.result = {
    gcode: G.join('\n') + '\n', lines: G.length, layers: LI, preview: pv, settings: s, warnings: warn,
    stats: { time, filament: filMM, volume: vol, grams, layers: L, height, size: [placed.max[0] - placed.min[0], placed.max[1] - placed.min[1], height] },
  };
  yield 1;
}
function slicePrintSync(placed, settings, meta) { const out = {}; for (const _ of slicePrintSteps(placed, settings, out, meta)); return out.result; }
async function slicePrintAsync(placed, settings, meta, onProgress) {
  const out = {};
  let t = Date.now();
  for (const f of slicePrintSteps(placed, settings, out, meta)) {
    if (Date.now() - t > 25) { if (onProgress) onProgress(f); await new Promise(r => setTimeout(r, 0)); t = Date.now(); }
  }
  if (onProgress) onProgress(1);
  return out.result;
}
// "1 h 05 min", "12 min", "40 s"
function fmtDuration(sec) {
  sec = Math.max(0, Math.round(sec));
  if (sec < 60) return sec + ' s';
  const m = Math.round(sec / 60);
  return m < 60 ? m + ' min' : Math.floor(m / 60) + ' h ' + String(m % 60).padStart(2, '0') + ' min';
}
