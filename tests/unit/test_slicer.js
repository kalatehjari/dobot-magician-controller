// Unit tests for 3D printing: mesh files, placement, slicing, walls/skins/infill/supports, G-code (node tests/unit/test_slicer.js)
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { console, Math, Array, Object, Number, JSON, String, parseFloat, parseInt, isNaN, isFinite, Infinity, NaN, Error, RegExp,
  Float32Array, Float64Array, Uint32Array, Uint8Array, Int32Array, Map, Set, TextDecoder, TextEncoder, DataView, ArrayBuffer, Date, setTimeout, Promise,
  navigator: { userAgent: 'node', appName: 'Netscape' } };
ctx.self = ctx;
vm.createContext(ctx);
for (const f of ['part48_clipper.js', 'part49_slicer.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };
const near = (a, b, tol) => Math.abs(a - b) <= tol;

// G-code reader: follows positions, extrusion, feed rates and modes the way the firmware would.
ctx.analyse = function analyse(gcode) {
  const st = { x: 0, y: 0, z: 0, e: 0, f: 0, rel: false };
  const out = { moves: [], cmds: [], retracts: 0, unretracts: 0, extrudeWhileRetracted: 0, time: 0, fil: 0, temps: [], fanOn: -1, layerMarks: [], lines: 0, firstExtrude: -1, badNumbers: 0 };
  let retracted = false, layer = -1;
  gcode.split('\n').forEach((raw, ln) => {
    const lm = raw.match(/^;LAYER:(\d+)/); if (lm) { layer = +lm[1]; out.layerMarks.push(layer); }
    const line = raw.replace(/;.*/, '').trim(); if (!line) return;
    out.lines++;
    const [cmd, ...words] = line.split(/\s+/), P = {};
    for (const w of words) { const v = parseFloat(w.slice(1)); if (!Number.isFinite(v)) out.badNumbers++; P[w[0].toUpperCase()] = v; }
    out.cmds.push(cmd);
    if (cmd === 'G90') st.rel = false; else if (cmd === 'G91') st.rel = true;
    else if (cmd === 'G92') { if ('E' in P) st.e = P.E; }
    else if (cmd === 'M104' || cmd === 'M109') out.temps.push([cmd, P.S, ln]);
    else if (cmd === 'M106' && out.fanOn < 0) out.fanOn = ln;
    else if (cmd === 'G0' || cmd === 'G1') {
      if ('F' in P) st.f = P.F;
      const nx = 'X' in P ? (st.rel ? st.x + P.X : P.X) : st.x, ny = 'Y' in P ? (st.rel ? st.y + P.Y : P.Y) : st.y;
      const nz = 'Z' in P ? (st.rel ? st.z + P.Z : P.Z) : st.z, ne = 'E' in P ? (st.rel ? st.e + P.E : P.E) : st.e;
      const d = Math.hypot(nx - st.x, ny - st.y, nz - st.z), de = ne - st.e, v = st.f / 60;
      if (d < 1e-9 && de) {                                   // pure extruder move: retract or prime
        if (de < 0) { out.retracts++; retracted = true; out.retractLens = (out.retractLens || []).concat(-de); }
        else { out.unretracts++; retracted = false; }
        out.time += Math.abs(de) / v;
      } else if (d > 0) {
        if (de > 1e-9) { if (retracted) out.extrudeWhileRetracted++; out.fil += de; if (out.firstExtrude < 0) out.firstExtrude = ln; }
        out.moves.push({ x0: st.x, y0: st.y, z0: st.z, x: nx, y: ny, z: nz, de, d, v, layer, ln, rel: st.rel });
        out.time += d / v;
      }
      Object.assign(st, { x: nx, y: ny, z: nz, e: ne });
    }
  });
  return out;
};
ctx.gget = (r, li, type) => { const L = r.layers[li], o = []; for (let j = L.seg0; j < L.seg1; j++) if (type === undefined || r.preview.type[j] === type) o.push(Array.from(r.preview.pos.slice(6 * j, 6 * j + 6))); return o; };

/* ---------- files ---------- */
{
  const r = E(`(() => {
    const m = sampleMesh('cube'), buf = meshToSTL(m.pos, m.idx, 'cube'), p = meshParse(buf, 'cube.stl'), m2 = meshFromTris(p.tri), i = meshInfo(m2);
    // binary file whose header starts with "solid" (many programs write that)
    const b2 = new Uint8Array(buf.slice(0)); 'solid exported'.split('').forEach((ch, k) => b2[k] = ch.charCodeAt(0));
    const p2 = meshParse(b2.buffer, 'x.stl');
    // ASCII STL of the same triangles
    let txt = 'solid cube\\n';
    for (let k = 0; k < p.tri.length; k += 9) { txt += ' facet normal 0 0 0\\n  outer loop\\n'; for (let j = 0; j < 9; j += 3) txt += '   vertex ' + p.tri[k + j] + ' ' + p.tri[k + j + 1] + ' ' + p.tri[k + j + 2] + '\\n'; txt += '  endloop\\n endfacet\\n'; }
    txt += 'endsolid cube\\n';
    const p3 = meshParse(new TextEncoder().encode(txt).buffer, 'cube.stl'), i3 = meshInfo(meshFromTris(p3.tri));
    let bad = ''; try { meshParse(new TextEncoder().encode('hello world').buffer, 'a.stl'); } catch (e) { bad = e.message; }
    return { fmt: p.format, tris: i.tris, vol: i.volume, closed: i.closed, f2: p2.format, n2: p2.tri.length / 9, f3: p3.format, vol3: i3.volume, closed3: i3.closed, bad };
  })()`);
  t('binary STL: written and read back, closed, volume 8000 mm³', r.fmt === 'binary STL' && r.tris === 16 && Math.abs(r.vol - 8000) < 1e-6 && r.closed, JSON.stringify(r).slice(0, 120));
  t('binary STL with a "solid" header is still read as binary', r.f2 === 'binary STL' && r.n2 === 16);
  t('ASCII STL reads to the same closed solid', r.f3 === 'ASCII STL' && Math.abs(r.vol3 - 8000) < 1e-6 && r.closed3);
  t('a file that is not a model is refused with a message', /STL or OBJ/.test(r.bad), r.bad);
  const o = E(`(() => {
    // a 10 (x) × 30 (y, up) × 20 (z) box in OBJ, with quads and negative indices
    const v = [[0,0,0],[10,0,0],[10,30,0],[0,30,0],[0,0,20],[10,0,20],[10,30,20],[0,30,20]];
    let s = v.map(p => 'v ' + p.join(' ')).join('\\n') + '\\n';
    const f = [[1,4,3,2],[5,6,7,8],[1,2,6,5],[2,3,7,6],[3,4,8,7],[4,1,5,8]];
    s += f.map(q => 'f ' + q.map(k => (k - 9) + '/1/1').join(' ')).join('\\n') + '\\n';
    const p = meshParse(new TextEncoder().encode(s).buffer, 'box.obj'), m = meshFromTris(p.tri), i = meshInfo(m);
    return { fmt: p.format, tris: i.tris, size: i.size, vol: i.volume, closed: i.closed };
  })()`);
  t('OBJ: quads are split, negative indices work, Y-up becomes Z-up', o.fmt === 'OBJ' && o.tris === 12 && near(o.size[2], 30, 1e-9) && near(o.size[1], 20, 1e-9) && near(o.vol, 6000, 1e-6) && o.closed, JSON.stringify(o));
  const h = E(`(() => { const m = sampleMesh('cube'); const idx = m.idx.slice(3); const i = meshInfo({ pos: m.pos, idx }); return { closed: i.closed, open: i.open }; })()`);
  t('a missing triangle is found (open surface, 3 open edges)', !h.closed && h.open === 3);
  const sm = E(`Object.keys(PRINT_SAMPLES).map(k => { const i = meshInfo(sampleMesh(k)); return [k, i.closed, i.inside, i.volume]; })`);
  t('every built-in model is a closed solid with outward faces', sm.every(s => s[1] && !s[2] && s[3] > 1000), sm.map(s => s[0] + ' ' + s[3].toFixed(0)).join(', '));
}

/* ---------- placement ---------- */
{
  const r = E(`(() => {
    const m = meshFromTris(meshParse(meshToSTL(sampleMesh('bridge').pos, sampleMesh('bridge').idx)).tri);
    const a = meshPlace(m, {}), b = meshPlace(m, { R: mat3Turn('x', 90) }), c = meshPlace(m, { s: 0.5, x: 5, y: -3 }), d = meshPlace(m, { mirror: true });
    const sz = P => [0, 1, 2].map(k => +(P.max[k] - P.min[k]).toFixed(6));
    return { a: sz(a), amin: a.min, b: sz(b), c: sz(c), cc: [(c.min[0] + c.max[0]) / 2, (c.min[1] + c.max[1]) / 2, c.min[2]], dIn: meshInfo({ pos: d.pos, idx: d.idx }).inside, dVol: meshInfo({ pos: d.pos, idx: d.idx }).volume, rMax: a.rMax };
  })()`);
  t('the model is centred on the plate and stands on it', near(r.amin[2], 0, 1e-6) && near(r.amin[0], -20, 1e-5) && r.a.join() === '40,12,18', JSON.stringify(r.a));
  t('a quarter turn about X swaps depth and height', r.b.join() === '40,18,12');
  t('scale and position', r.c.join() === '20,6,9' && near(r.cc[0], 5, 1e-6) && near(r.cc[1], -3, 1e-6) && near(r.cc[2], 0, 1e-9));
  t('a mirrored model keeps its faces pointing outwards', !r.dIn && near(r.dVol, 5933, 1));
  t('distance from the plate centre is measured', near(r.rMax, Math.hypot(20, 6), 1e-4), r.rMax.toFixed(3));
  const f = E(`(() => {
    const m = sampleMesh('pyramid');
    const R = meshLayFlat(m, mat3Turn('x', 180)), P = meshPlace(m, { R });   // upside down → back on its base
    let base = 0; for (let i = 0; i < P.pos.length; i += 3) if (Math.abs(P.pos[i + 2]) < 1e-6) base++;
    const c = sampleMesh('cube'), R2 = meshLayFlat(c, mat3Axis(1, 0, 0, 0.5)), P2 = meshPlace(c, { R: R2 });
    const R3 = meshLayFlat(c, mat3Axis(0.6, 0.8, 0, 2.2)), P3 = meshPlace(c, { R: R3 });
    const sz = P => [0, 1, 2].map(k => +(P.max[k] - P.min[k]).toFixed(4));
    return { base, h: P.max[2], s2: sz(P2), s3: sz(P3) };
  })()`);
  t('lay flat: an upside-down pyramid goes back onto its square base', f.base >= 4 && near(f.h, 22, 1e-4), JSON.stringify(f));
  t('lay flat: a tilted cube stands on a face again', f.s2[2] === 20 && f.s3[2] === 20, f.s2 + ' / ' + f.s3);
}

/* ---------- cutting ---------- */
{
  const r = E(`(() => {
    const L = layerHeights(20, printSettings({}));
    const m = sampleMesh('cube'), P = meshPlace(m, {});
    const c = sliceMesh(P.pos, P.idx, [5, 0, 20, 10]);        // 0 and 20 are exactly on vertices
    const g = sampleMesh('gear'), G = meshPlace(g, {}), cg = sliceMesh(G.pos, G.idx, [4]);
    const isl = clIslands(cg[0].loops.map(clPath), true);
    return { n: L.length, z0: L[0].z, last: L[L.length - 1].z, cut0: L[0].cut, l5: c[0].loops.length, a5: clArea(c[0].loops.map(clPath)), p5: c[0].loops[0].length / 2,
      l0: c[1].loops.length, l20: c[2].loops.length, gi: isl.length, gh: isl[0] ? isl[0].length - 1 : -1, ga: clArea(isl.flat()), gaps: cg[0].gaps };
  })()`);
  t('layer heights: 0.35 mm first layer, then 0.2 mm, the last one inside the model', r.n === 99 && near(r.z0, 0.35, 1e-9) && near(r.last, 19.95, 1e-6) && near(r.cut0, 0.175, 1e-9), `${r.n} layers, last ${r.last}`);
  t('a cut through the cube is one closed 20 × 20 square', r.l5 === 1 && near(Math.abs(r.a5), 400, 1e-6) && r.p5 >= 4);
  t('cuts exactly through vertices give a clean loop or nothing', r.l0 === 1 && r.l20 === 0, `${r.l0} at z=0, ${r.l20} at z=20`);
  t('a cut through the gear: one island with one hole and the right area', r.gi === 1 && r.gh === 1 && r.gaps === 0, `area ${r.ga.toFixed(1)}`);
  const s = E(`(() => {
    const sq = clPath([0, 0, 20, 0, 20, 20, 0, 20]), o = clOffset([sq], -0.225), a = clArea(o);
    const nested = clIslands([clPath([0, 0, 30, 0, 30, 30, 0, 30]), clPath([5, 5, 25, 5, 25, 25, 5, 25]), clPath([10, 10, 20, 10, 20, 20, 10, 20])], true);
    const lines = scanLines([[0, 0, 10, 0, 10, 10, 0, 10]], 0, 1);
    const ord = orderSegments(lines, { x: 0, y: 0 }, 2.2, [[0, 0, 10, 0, 10, 10, 0, 10]]);
    return { a, nested: nested.map(i => i.length).sort().reverse(), nl: lines.length, l0: lines[0], ord: ord.length, ordPts: ord[0].length / 2 };
  })()`);
  t('offsetting a 20 mm square inwards by half a line', near(s.a, 19.55 * 19.55, 1e-3), s.a.toFixed(4));
  t('nested outlines become an island with a hole and an island inside the hole', s.nested.join() === '2,1');
  t('scan lines on a fixed grid, edge to edge', s.nl === 10 && near(s.l0[1], 0.5, 1e-9) && near(Math.min(s.l0[0], s.l0[2]), 0, 1e-9) && near(Math.max(s.l0[0], s.l0[2]), 10, 1e-9));
  t('zig-zag ordering joins neighbouring lines into one path', s.ord === 1 && s.ordPts === 20);
}

/* ---------- overlapping and inside-out bodies ---------- */
{
  const r = E(`(() => {
    const c = sampleMesh('cube'), two = (dx) => { const pos = [], idx = []; for (const d of [0, dx]) { const b = pos.length / 3; for (let i = 0; i < c.pos.length; i += 3) pos.push(c.pos[i] + d, c.pos[i + 1], c.pos[i + 2]); for (const k of c.idx) idx.push(k + b); } return { pos: Float32Array.from(pos), idx: Uint32Array.from(idx) }; };
    const area = (mesh) => { const P = meshPlace(mesh, {}), res = slicePrintSync(P, { top: 0, bottom: 0, infill: 0, walls: 1, skirt: 0 }, {});
      const isl = res.layers.length; return { warn: res.warnings, n: isl }; };
    // cross-section areas straight from the cutter + islands, as the slicer builds them
    const cut = (mesh, evenOdd) => { const P = meshPlace(mesh, {}), cs = sliceMesh(P.pos, P.idx, [10])[0]; const isl = clIslands(cs.loops.map(clPath), evenOdd); return { n: isl.length, a: clArea(isl.flat()) }; };
    const ov = two(10), inv = { pos: c.pos, idx: Uint32Array.from(c.idx).map((v, i, a) => i % 3 === 1 ? a[i + 1] : i % 3 === 2 ? a[i - 1] : v) };
    const infoOv = meshInfo(ov), infoInv = meshInfo(inv);
    const res = slicePrintSync(meshPlace(ov, {}), {}, {});
    let maxX = -Infinity, minX = Infinity, inner = 0;
    for (const g of gget(res, 50, 1)) { maxX = Math.max(maxX, g[0]); minX = Math.min(minX, g[0]); if (Math.abs(g[0]) < 14 && Math.abs(g[3]) < 14 && Math.abs(g[1]) < 9.7 && Math.abs(g[4]) < 9.7) inner++; }
    const nOuter = (() => { const L = res.layers[50]; let n = 0; for (let j = L.seg0; j < L.seg1; j++) if (res.preview.type[j] === 1) n++; return n; })();
    return { ovNZ: cut(ov, false), ovEO: cut(ov, true), oriented: infoOv.oriented, inv: cut(inv, false), invOriented: infoInv.oriented, invInside: infoInv.inside, warn: res.warnings, minX, maxX, nOuter, inner };
  })()`);
  t('two overlapping cubes merge into one 30 × 20 outline (not a hole where they overlap)', r.oriented && r.ovNZ.n === 1 && near(r.ovNZ.a, 600, 1e-6) && r.ovEO.n === 2, `non-zero ${r.ovNZ.a.toFixed(1)} mm², even-odd ${r.ovEO.a.toFixed(1)} mm²`);
  t('…and their walls go round the outside only', near(r.minX, -15 + 0.225, 0.01) && near(r.maxX, 15 - 0.225, 0.01) && r.inner === 0 && !r.warn.length, `${r.minX.toFixed(3)} … ${r.maxX.toFixed(3)}, ${r.inner} inside`);
  t('an inside-out model still slices as a solid', r.inv.n === 1 && near(r.inv.a, 400, 1e-6) && r.invInside && r.invOriented, r.inv.a.toFixed(1));
}

/* ---------- settings ---------- */
{
  const r = E(`(() => {
    const out = {};
    const tryS = o => { try { printSettings(o); return 'ok'; } catch (e) { return e.message; } };
    out.d = printSettings({});
    out.badTemp = tryS({ temp: 150 }); out.badLayer = tryS({ layerH: 0.38 }); out.nan = tryS({ infill: 'x' });
    out.vase = printSettings({ vase: true, walls: 3, infill: 20, top: 5 });
    return out;
  })()`);
  t('defaults follow Dobot: 0.2/0.35 mm layers, 200 °C, 6 mm retraction at 60 mm/s, walls 4 mm/s, infill 8 mm/s, Ø80 plate, 150 mm',
    r.d.layerH === 0.2 && r.d.firstH === 0.35 && r.d.temp === 200 && r.d.retract === 6 && r.d.vRetract === 60 && r.d.vWall === 4 && r.d.vInfill === 8 && r.d.plateD === 80 && r.d.maxH === 150 && r.d.walls >= 2 && r.d.fan);
  t('settings out of range are refused with a reason', /between 170 and 250/.test(r.badTemp) && /between|80 %/.test(r.badLayer) && /not a number/.test(r.nan), r.badTemp + ' | ' + r.badLayer);
  t('vase mode: one wall, no infill, no top', r.vase.walls === 1 && r.vase.infill === 0 && r.vase.top === 0);
}

/* ---------- the calibration cube, end to end ---------- */
{
  const r = E(`(() => {
    const m = sampleMesh('cube'), P = meshPlace(m, {}), res = slicePrintSync(P, {}, { name: m.name }), A = analyse(res.gcode.split(';END')[0]);
    const s = res.settings, fa = Math.PI * 0.875 * 0.875;
    // extrusion per mm for each move must match its line width × height
    let badRate = 0, maxR = 0, zDown = 0, lastZ = 0;
    let started = false;
    for (const mv of A.moves) {
      if (mv.de > 0) started = true;
      if (!started) continue;
      if (mv.de > 0) {
        const first = mv.layer === 0, rate = (first ? s.firstW * s.firstH : s.lineW * s.layerH) / fa;
        if (Math.abs(mv.de / mv.d - rate) > 2e-3 * rate + 2e-6 / mv.d) badRate++;
        maxR = Math.max(maxR, Math.hypot(mv.x, mv.y));
      }
      if (mv.layer >= 0 && !mv.rel) { if (mv.z < lastZ - 1e-9) zDown++; lastZ = mv.z; }
    }
    const L50 = gget(res, 50, 1), xs = L50.flatMap(g => [g[0], g[3]]);
    const firstCmds = A.cmds.slice(0, 12).join(' ');
    const end = res.gcode.split(';END')[1].trim().split('\\n').map(l => l.replace(/;.*/, '').trim()).join('|');
    // where moves are slow enough: walls at 4 mm/s, first layer at most 4 mm/s, infill 8
    const v = { wall: new Set(), first: new Set(), fill: new Set() };
    for (const mv of A.moves) if (mv.de > 0) (mv.layer === 0 ? v.first : v.wall).add(Math.round(mv.v * 100) / 100);
    return { stats: res.stats, warn: res.warnings, A: { retracts: A.retracts, unretracts: A.unretracts, ewr: A.extrudeWhileRetracted, fil: A.fil, time: A.time, temps: A.temps, fanOn: A.fanOn, firstExtrude: A.firstExtrude, marks: A.layerMarks.length, bad: A.badNumbers, rl: [...new Set(A.retractLens.map(x => +x.toFixed(4)))] },
      badRate, maxR, zDown, maxX: Math.max(...xs.map(Math.abs)), firstCmds, end, ascii: /^[\\x09\\x0a\\x0d\\x20-\\x7e]*$/.test(res.gcode), speedsFirst: [...v.first].sort((a, b) => a - b), speeds: [...v.wall].sort((a, b) => a - b), lines: res.lines };
  })()`);
  const A = r.A;
  t('slices to 99 layers with a time and filament estimate', r.stats.layers === 99 && r.stats.time > 3000 && r.stats.filament > 500 && !r.warn.length, `${(r.stats.time / 60).toFixed(0)} min, ${(r.stats.filament / 1000).toFixed(2)} m, ${r.stats.grams.toFixed(1)} g, ${r.lines} lines`);
  t('start: fan on, heat to 200 °C and wait before anything is extruded', /^M106 G91 G0 G90 M104 M109/.test(r.firstCmds) && A.temps[0][1] === 200 && A.temps[1][0] === 'M109' && A.temps[1][2] < A.firstExtrude && A.fanOn >= 0, r.firstCmds);
  t('end: Dobot end code (heater off, back off, lift, move away, fan off)', r.end === 'M104 S0|G91|G1 E-1 F300|G1 Z+3 E-5 F3000|G1 Y+50|G90|M107', r.end);
  t('every extrusion uses the right amount of filament for its line', r.badRate === 0, `${r.badRate} wrong`);
  t('everything stays on the Ø80 mm plate', r.maxR < 40, r.maxR.toFixed(2) + ' mm');
  t('layers only go up', r.zDown === 0);
  t('retractions are 6 mm and always undone before extruding again', A.rl.length === 1 && A.rl[0] === 6 && A.ewr === 0 && Math.abs(A.retracts - A.unretracts) <= 1, `${A.retracts} retracts`);
  t('one ;LAYER mark per layer, no broken numbers', A.marks === 99 && A.bad === 0);
  t('the G-code is plain ASCII', r.ascii);
  t('outer wall sits half a line inside the outline', near(r.maxX, 10 - 0.225, 0.01), r.maxX.toFixed(4));
  t('filament total matches the G-code', near(A.fil, r.stats.filament, 1e-3 * r.stats.filament), A.fil.toFixed(1) + ' vs ' + r.stats.filament.toFixed(1));
  t('time estimate matches the moves in the G-code (+10 % allowance)', near(r.stats.time, A.time * 1.1, 0.01 * r.stats.time), `${(r.stats.time / 60).toFixed(1)} vs ${(A.time * 1.1 / 60).toFixed(1)} min`);
  t('walls at 4 mm/s, infill at 8, solid at 6; first layer at most 4 mm/s', r.speeds.includes(4) && r.speeds.includes(8) && r.speeds.includes(6) && Math.max(...r.speeds) <= 8 && Math.max(...r.speedsFirst) <= 4, 'speeds ' + r.speeds.join(',') + ' first ' + r.speedsFirst.join(','));
}

/* ---------- filling: solid layers cover, sparse layers have the set density, 100 % fills the volume ---------- */
{
  const r = E(`(() => {
    const m = sampleMesh('cube'), P = meshPlace(m, {}), res = slicePrintSync(P, {}, {});
    const cover = (li) => {                                     // rasterise this layer's extrusion at 0.05 mm
      const g = 0.05, n = Math.round(20 / g), grid = new Uint8Array(n * n), w = li === 0 ? res.settings.firstW : res.settings.lineW;
      for (const s of gget(res, li)) {
        if (s[6] === undefined) {}
      }
      const L = res.layers[li];
      for (let j = L.seg0; j < L.seg1; j++) {
        if (!res.preview.type[j]) continue;
        const p = res.preview.pos, x0 = p[6 * j], y0 = p[6 * j + 1], x1 = p[6 * j + 3], y1 = p[6 * j + 4], len = Math.hypot(x1 - x0, y1 - y0);
        const steps = Math.ceil(len / (g / 2)) + 1;
        for (let k = 0; k <= steps; k++) {
          const x = x0 + (x1 - x0) * k / steps, y = y0 + (y1 - y0) * k / steps, r = w / 2;
          for (let gx = Math.floor((x - r + 10) / g); gx <= Math.floor((x + r + 10) / g); gx++) for (let gy = Math.floor((y - r + 10) / g); gy <= Math.floor((y + r + 10) / g); gy++) {
            if (gx < 0 || gy < 0 || gx >= n || gy >= n) continue;
            const cx = gx * g + g / 2 - 10, cy = gy * g + g / 2 - 10;
            if ((cx - x) ** 2 + (cy - y) ** 2 <= r * r) grid[gy * n + gx] = 1;
          }
        }
      }
      let c = 0; for (const v of grid) c += v; return c / (n * n);
    };
    // scan lines only (at ±45°), not the short links along the walls
    const sparseLen = gget(res, 50, 4).filter(s => Math.abs(Math.abs(s[3] - s[0]) - Math.abs(s[4] - s[1])) < 1e-3).reduce((a, s) => a + Math.hypot(s[3] - s[0], s[4] - s[1]), 0);
    const solid100 = slicePrintSync(P, { infill: 100 }, {});
    return { top: cover(98), bottom: cover(1), first: cover(0), mid: cover(50), sparseLen, vol100: solid100.stats.volume };
  })()`);
  t('top and bottom layers are filled solid', r.top > 0.985 && r.bottom > 0.985 && r.first > 0.985, `top ${(100 * r.top).toFixed(1)} %, bottom ${(100 * r.bottom).toFixed(1)} %, first ${(100 * r.first).toFixed(1)} %`);
  const inner = (20 - 4 * 0.45) ** 2, dens = r.sparseLen * 0.45 / inner;
  t('middle layers: two walls and about 15 % infill', near(dens, 0.15, 0.03) && r.mid < 0.5, `infill ${(100 * dens).toFixed(1)} %, covered ${(100 * r.mid).toFixed(1)} %`);
  t("at 100 % infill the plastic laid down equals the cube's volume", r.vol100 / 8000 > 0.97 && r.vol100 / 8000 < 1.08, (r.vol100 / 8000).toFixed(3));
}

/* ---------- travel: no retraction inside the part, retraction when leaving it ---------- */
{
  const r = E(`(() => {
    const m = sampleMesh('cube'), res = slicePrintSync(meshPlace(m, {}), {}, {}), A = analyse(res.gcode);
    // count retractions between the ;LAYER:50 and ;LAYER:51 marks
    const lines = res.gcode.split('\\n'), a = lines.indexOf(';LAYER:50'), b = lines.indexOf(';LAYER:51');
    const ret = lines.slice(a, b).filter(l => /^G1 E[-\\d.]+ F3600$/.test(l)).length;
    return { ret };
  })()`);
  t('inside one part the nozzle travels without retracting (only the layer change retracts)', r.ret <= 2, r.ret + ' retract/prime moves on layer 50');
  const r2 = E(`(() => {
    // two cubes 20 mm apart: every jump between them retracts
    const c = sampleMesh('cube'), pos = [], idx = [];
    for (const dx of [-15, 15]) { const b = pos.length / 3; for (let i = 0; i < c.pos.length; i += 3) pos.push(c.pos[i] * 0.4 + dx, c.pos[i + 1] * 0.4, c.pos[i + 2] * 0.4); for (const k of c.idx) idx.push(k + b); }
    const res = slicePrintSync(meshPlace({ pos: Float32Array.from(pos), idx: Uint32Array.from(idx) }, {}), {}, {}), A = analyse(res.gcode);
    let jumps = 0, unret = 0;
    const lines = res.gcode.split('\\n'); let lastX = null, retracted = false, longDry = 0;
    for (const mv of A.moves) if (mv.de <= 0 && Math.abs(mv.x - mv.x0) > 20) jumps++;
    return { jumps, retracts: A.retracts, ewr: A.extrudeWhileRetracted, layers: res.stats.layers };
  })()`);
  t('two separate parts: the jumps between them retract', r2.jumps > 0 && r2.retracts >= r2.jumps && r2.ewr === 0, `${r2.jumps} jumps, ${r2.retracts} retractions over ${r2.layers} layers`);
}

/* ---------- holes, seams, brim, skirt ---------- */
{
  const r = E(`(() => {
    const g = sampleMesh('gear'), res = slicePrintSync(meshPlace(g, {}), { brim: 4, seam: 'rear' }, {});
    const L = 20, segs = gget(res, L, 1), radii = segs.map(s => Math.hypot(s[0], s[1]));
    const holeWall = radii.filter(r => r < 6).length, minR = Math.min(...radii);
    const first = gget(res, 0, 6), firstR = first.map(s => Math.hypot(s[0], s[1]));
    // the first outer-wall move of each layer starts at the rear (largest y) of its loop
    const lines = res.gcode.split('\\n');
    return { holeWall, minR, skirtMax: Math.max(...firstR), brimMin: Math.min(...firstR), skirtLen: first.reduce((a, s) => a + Math.hypot(s[3] - s[0], s[4] - s[1]), 0) };
  })()`);
  t("the gear's hole gets its own wall, half a line from the hole", r.holeWall > 10 && near(r.minR, 4 + 0.225, 0.02), r.minR.toFixed(3));
  t('brim loops touch the part and the skirt goes round them', r.brimMin < 20.5 && r.skirtMax > 20 + 4 * 0.6 + 3, `brim from ${r.brimMin.toFixed(2)} mm, skirt to ${r.skirtMax.toFixed(2)} mm`);
  t('skirt and brim together prime at least 150 mm of line', r.skirtLen >= 150, r.skirtLen.toFixed(0) + ' mm');
  const s = E(`(() => {
    const m = sampleMesh('cube'), res = slicePrintSync(meshPlace(m, {}), { seam: 'rear' }, {});
    let ok = 0, n = 0;
    for (let li = 5; li < 95; li += 7) { const w = gget(res, li, 1); if (!w.length) continue; n++; if (w[0][1] > 9.7) ok++; }
    return { ok, n };
  })()`);
  t('rear seam: outer walls start at the back of the model', s.ok === s.n && s.n > 5, `${s.ok}/${s.n}`);
}

/* ---------- supports ---------- */
{
  const r = E(`(() => {
    const b = meshPlace(sampleMesh('bridge'), {});
    const all = slicePrintSync(b, { support: 'all' }, {}), off = slicePrintSync(b, {}, {});
    let n = 0, outside = 0, inModel = 0;
    for (let li = 0; li < all.layers.length; li++) for (const s of gget(all, li, 5)) {
      n++;
      const x = (s[0] + s[3]) / 2, z = s[2];
      if (Math.abs(x) > 12) outside++;
      if (Math.hypot(x, z) > 12 - 0.15 && z < 18) inModel++;           // inside the arch's solid part
    }
    const ball = slicePrintSync(meshPlace(sampleMesh('ball'), {}), { support: 'plate' }, {});
    return { n, outside, inModel, warnOff: off.warnings.join(' '), warnAll: all.warnings.join(' '), ball0: gget(ball, 0, 5).length, ballTop: gget(ball, ball.layers.length - 1, 5).length };
  })()`);
  t('supports fill the arch opening and stay out of the model', r.n > 100 && r.outside === 0 && r.inModel === 0, `${r.n} support moves, ${r.outside} outside the arch, ${r.inModel} in the model`);
  t('without supports, hanging parts are pointed out', /hang in the air/.test(r.warnOff) && !/hang/.test(r.warnAll));
  t('a ball on supports from the plate: support starts on the first layer', r.ball0 > 0 && r.ballTop === 0);
}

/* ---------- vase mode ---------- */
{
  const r = E(`(() => {
    const res = slicePrintSync(meshPlace(sampleMesh('vase'), {}), PRINT_PRESETS.vase, {}), A = analyse(res.gcode);
    const B = res.settings.bottom;
    let zBack = 0, lastZ = -1, spiralMoves = 0, retr = 0;
    const lines = res.gcode.split('\\n'), from = lines.indexOf(';LAYER:' + (B + 1)), to = lines.indexOf(';LAYER:' + (res.layers.length - 1));
    for (let k = from; k < to; k++) { if (/^G1 E/.test(lines[k])) retr++; }
    for (const mv of A.moves) if (mv.layer > B && mv.de > 0) { spiralMoves++; if (mv.z < lastZ - 1e-9) zBack++; lastZ = mv.z; }
    const w = gget(res, 40), types = new Set(w.map(s => s[6] === undefined ? -1 : 0));
    let walls40 = 0; const L = res.layers[40]; for (let j = L.seg0; j < L.seg1; j++) if (res.preview.type[j] === 1) walls40++;
    return { spiralMoves, zBack, retr, bottomSolid: gget(res, 1, 3).length, inf40: gget(res, 40, 4).length + gget(res, 40, 3).length, inner40: gget(res, 40, 2).length, walls40, zEnd: lastZ, h: res.stats.height };
  })()`);
  t('vase: the wall rises continuously, never stepping down', r.spiralMoves > 1000 && r.zBack === 0 && near(r.zEnd, r.h, 0.25), `${r.spiralMoves} moves, ends at ${r.zEnd.toFixed(2)} of ${r.h}`);
  t('vase: no retraction once the spiral starts', r.retr === 0, r.retr + ' retractions');
  t('vase: solid bottom, then a single wall with no infill', r.bottomSolid > 10 && r.inf40 === 0 && r.inner40 === 0 && r.walls40 > 50);
}

/* ---------- refusing what cannot print ---------- */
{
  const r = E(`(() => {
    const m = sampleMesh('cube'), msg = f => { try { f(); return 'ok'; } catch (e) { return e.message; } };
    return {
      wide: msg(() => slicePrintSync(meshPlace(m, { s: 3 }), {}, {})),
      tall: msg(() => slicePrintSync(meshPlace(m, {}), { maxH: 10 }, {})),
      flat: msg(() => slicePrintSync(meshPlace({ pos: Float32Array.from([0, 0, 0, 10, 0, 0, 0, 10, 0]), idx: Uint32Array.from([0, 1, 2]) }, {}), {}, {})),
      sheet: msg(() => slicePrintSync(meshPlace({ pos: Float32Array.from([0, 0, 0, 10, 0, 0, 0, 0, 10]), idx: Uint32Array.from([0, 1, 2]) }, {}), {}, {})),
      bigPlate: msg(() => slicePrintSync(meshPlace(m, { s: 3 }), { plateD: 100 }, {})),
    };
  })()`);
  t('too wide for the plate: refused, with the size', /plate is Ø80/.test(r.wide), r.wide);
  t('too tall: refused', /at most 10 mm/.test(r.tall), r.tall);
  t('flat or open sheets: refused', /flat/.test(r.flat) && /Nothing to print/.test(r.sheet), r.sheet);
  t('a larger plate setting lets a larger model through', r.bigPlate === 'ok', r.bigPlate);
}

/* ---------- same input, same G-code; speed ---------- */
{
  const r = E(`(() => {
    const m = sampleMesh('twist'), P = meshPlace(m, {});
    const a = slicePrintSync(P, {}, { name: 'x' }).gcode, b = slicePrintSync(P, {}, { name: 'x' }).gcode;
    // a fine ball: 80 000 triangles
    const zs = [], rs = [];
    for (let i = 0; i <= 200; i++) { const t = -Math.PI / 2 + Math.PI * i / 200, r = Math.max(0.05, 18 * Math.cos(t)); zs.push(18 + 18 * Math.sin(t)); rs.push(ringPts(200, () => r)); }
    const big = meshLoft(rs, zs), t0 = Date.now();
    const res = slicePrintSync(meshPlace({ pos: big.pos, idx: big.idx }, {}), {}, {});
    return { same: a === b, tris: big.idx.length / 3, ms: Date.now() - t0, layers: res.stats.layers };
  })()`);
  t('slicing is deterministic', r.same);
  t('an 80 000-triangle model slices in reasonable time', r.ms < 60000, `${r.tris} triangles, ${r.layers} layers in ${(r.ms / 1000).toFixed(1)} s`);
}

/* ---------- async slicing reports progress ---------- */
(async () => {
  const r = await E(`(async () => { const p = []; const res = await slicePrintAsync(meshPlace(sampleMesh('gear'), {}), {}, {}, f => p.push(f)); return { n: p.length, last: p[p.length - 1], mono: p.every((v, i) => !i || v >= p[i - 1]), layers: res.stats.layers }; })()`);
  t('slicing in the page reports rising progress up to 100 %', r.n >= 2 && r.last === 1 && r.mono && r.layers === 39, `${r.n} updates`);
  t('durations read naturally', E(`[fmtDuration(40), fmtDuration(720), fmtDuration(3900)].join('|')`) === '40 s|12 min|1 h 05 min');
  console.log(fails ? `\n${fails} FAILED` : '\nall slicer tests passed');
  process.exit(fails ? 1 : 0);
})();
