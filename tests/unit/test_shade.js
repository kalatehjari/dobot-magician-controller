// Unit tests for shading: hatch lines inside closed shapes (run: node tests/unit/test_shade.js)
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { console, Math, Array, Object, Number, JSON, Infinity, NaN, isFinite, Set, Map, String, RegExp, parseFloat, Date };
vm.createContext(ctx);
for (const f of ['part2_geometry.js', 'part42_shade.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };
ctx.J = v => JSON.parse(JSON.stringify(v));

E(`
var sq = (x0, y0, x1, y1) => [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }, { x: x0, y: y0 }];
var segs = chains => { const out = []; for (const c of chains) for (let i = 1; i < c.length; i++) out.push([c[i - 1], c[i]]); return out; };
var inRect = (p, x0, y0, x1, y1, m = 1e-9) => p.x > x0 + m && p.x < x1 - m && p.y > y0 + m && p.y < y1 - m;
var mid = s => ({ x: (s[0].x + s[1].x) / 2, y: (s[0].y + s[1].y) / 2 });
var len = chains => segs(chains).reduce((a, s) => a + Math.hypot(s[1].x - s[0].x, s[1].y - s[0].y), 0);
`);

/* ---------- straight lines in a square ---------- */
{
  const r = E(`(() => { const T = outlineTargets([sq(0, 0, 1, 1)]);
    const a = hatchTarget(T[0], 0, 0.1, { join: false }), b = hatchTarget(T[0], 0, 0.1, { join: true });
    const ends = a.chains.every(c => c.length === 2 && Math.abs(Math.min(c[0].x, c[1].x)) < 1e-9 && Math.abs(Math.max(c[0].x, c[1].x) - 1) < 1e-9 && Math.abs(c[0].y - c[1].y) < 1e-12);
    const ys = a.chains.map(c => c[0].y).sort((p, q) => p - q);
    return { n: T.length, lines: a.chains.length, ends, ys, la: len(a.chains), nb: b.chains.length, lb: len(b.chains) }; })()`);
  t('a square gets 10 lines at 0.1 spacing, edge to edge', r.n === 1 && r.lines === 10 && r.ends && Math.abs(r.ys[0] - 0.05) < 1e-9 && Math.abs(r.ys[9] - 0.95) < 1e-9);
  t('zig-zag joining turns them into one pen stroke along the sides', r.nb === 1 && Math.abs(r.lb - (10 + 9 * 0.1)) < 1e-9, `${r.lines} strokes → ${r.nb}, ${r.la.toFixed(2)} → ${r.lb.toFixed(2)} long`);
  const v = E(`(() => { const T = outlineTargets([sq(0, 0, 1, 1)]); const a = hatchTarget(T[0], 90, 0.25, { join: false });
    return a.chains.map(c => [+c[0].x.toFixed(9), +c[1].x.toFixed(9), +Math.abs(c[1].y - c[0].y).toFixed(9)]).sort((p, q) => p[0] - q[0]); })()`);
  t('90° gives vertical lines', v.length === 4 && v.every(([x0, x1, h]) => x0 === x1 && h === 1) && v[0][0] === 0.125, JSON.stringify(v.map(q => q[0])));
  const d = E(`(() => { const T = outlineTargets([sq(0, 0, 1, 1)]); const a = hatchTarget(T[0], 45, 0.05, { join: false });
    const ok = a.chains.every(c => { const dx = c[1].x - c[0].x, dy = c[1].y - c[0].y; return Math.abs(Math.abs(dx) - Math.abs(dy)) < 1e-9 && dx * dy < 0; });
    const onEdge = p => Math.min(Math.abs(p.x), Math.abs(p.x - 1), Math.abs(p.y), Math.abs(p.y - 1)) < 1e-9;
    return { ok, edge: a.chains.every(c => onEdge(c[0]) && onEdge(c[1])), n: a.chains.length }; })()`);
  t('45° lines rise to the right on screen and end on the outline', d.ok && d.edge, `${d.n} lines`);
  const g = E(`(() => { const T = outlineTargets([sq(0, 0, 1, 1)]); const a = hatchTarget(T[0], 0, 0.1, { join: false, inset: 0.05 });
    const b = hatchTarget(T[0], 0, 0.1, { join: false, inset: 0.07 });
    return { ends: a.chains.every(c => Math.abs(Math.min(c[0].x, c[1].x) - 0.05) < 1e-9 && Math.abs(Math.max(c[0].x, c[1].x) - 0.95) < 1e-9), na: a.chains.length,
             nb: b.chains.length, top: Math.min(...b.chains.map(c => c[0].y)) }; })()`);
  t('a gap from the outline keeps line ends away from it', g.ends && g.na === 10);
  t('lines running close to an edge are left out too', g.nb === 8 && Math.abs(g.top - 0.15) < 1e-9, `with a 0.07 gap the first line is at ${g.top}`);
  const tri = E(`(() => { const T = outlineTargets([[{ x: 0, y: 1 }, { x: 1, y: 1 }, { x: 0.5, y: 0 }, { x: 0, y: 1 }]]); let worst = Infinity;
    for (const ang of [0, 20, 45, 70, 90, 135]) { const a = hatchTarget(T[0], ang, 0.03, { join: true, inset: 0.05 });
      for (const p of a.chains.flat()) { const e = [[{ x: 0, y: 1 }, { x: 1, y: 1 }], [{ x: 1, y: 1 }, { x: 0.5, y: 0 }], [{ x: 0.5, y: 0 }, { x: 0, y: 1 }]];
        for (const [u, v] of e) { const dx = v.x - u.x, dy = v.y - u.y, L2 = dx * dx + dy * dy, t = Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / L2)); worst = Math.min(worst, Math.hypot(u.x + t * dx - p.x, u.y + t * dy - p.y)); } } }
    return worst; })()`);
  t('the gap holds for slanted edges at any angle (at least 90 % of it)', tri >= 0.045, `closest point ${tri.toFixed(4)} from an edge for a 0.05 gap`);
}

/* ---------- holes and nesting ---------- */
{
  const r = E(`(() => { const T = outlineTargets([sq(0, 0, 1, 1), sq(0.3, 0.3, 0.7, 0.7)]);
    const a = hatchTarget(T[0], 30, 0.03, { join: true });
    const bad = segs(a.chains).filter(s => inRect(mid(s), 0.3, 0.3, 0.7, 0.7, 1e-6)).length;
    return { n: T.length, depth: T.map(x => x.depth), rings: T.map(x => x.rings.length), bad, chains: a.chains.length, lines: a.lines }; })()`);
  t('an outline inside another cuts a hole in it', r.n === 2 && r.depth.join() === '0,1' && r.rings.join() === '2,1');
  t('no line or zig-zag link crosses the hole', r.bad === 0, `${r.lines} lines in ${r.chains} pen strokes`);
  const n3 = E(`(() => { const T = outlineTargets([sq(0.2, 0.2, 0.8, 0.8), sq(0, 0, 1, 1), sq(0.4, 0.4, 0.6, 0.6)]);
    const all = shadeDrawing({ mode: 'all', list: T }, { ...SHADE_DEFAULTS, pattern: 'lines', angle: 0, spacing: 5 }, 100);
    const alt = shadeDrawing({ mode: 'alt', list: T }, { ...SHADE_DEFAULTS, pattern: 'lines', angle: 0, spacing: 5 }, 100);
    const inMid = res => segs(res.strokes).some(s => { const m = mid(s); return inRect(m, 0.2, 0.2, 0.8, 0.8, 1e-6) && !inRect(m, 0.4, 0.4, 0.6, 0.6, -1e-6); });
    return { depth: T.map(x => x.depth), all: all.shaded, alt: alt.shaded, allMid: inMid(all), altMid: inMid(alt) }; })()`);
  t('three nested squares are three levels', n3.depth.join() === '0,1,2');
  t('"every closed shape" shades all three; "every other level" leaves the middle ring empty', n3.all === 3 && n3.alt === 2 && n3.allMid && !n3.altMid);
  const open = E(`outlineTargets([[{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }], sq(2, 2, 3, 3)]).length`);
  t('open lines are not shaded as shapes', open === 1);
  const pieces = E(`(() => { const T = outlineTargets([[{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }], [{ x: 0, y: 1.001 }, { x: 0, y: 0.0005 }], [{ x: 1, y: 1 }, { x: 0.5, y: 1.2 }, { x: 0, y: 1.001 }]]);
    return { n: T.length, area: T.length ? +T[0].area.toFixed(3) : 0 }; })()`);
  t('an outline drawn in pieces that meet end to end is shaded as one shape', pieces.n === 1 && Math.abs(pieces.area - 1.1) < 0.01, `area ${pieces.area}`);
}

/* ---------- fill rules, paint order and tone ---------- */
{
  const r = E(`(() => {
    const star = []; for (let i = 0; i < 5; i++) { const a = -Math.PI / 2 + i * 4 * Math.PI / 5; star.push({ x: 0.5 + 0.5 * Math.cos(a), y: 0.5 + 0.5 * Math.sin(a) }); }
    star.push({ ...star[0] });
    const covers = rule => { const T = filledTargets([star], [{ from: 0, to: 1, fill: [0, 0, 0], alpha: 1, rule }]);
      const a = hatchTarget(T[0], 0, 0.02, { join: false });
      return a.chains.some(c => Math.abs(c[0].y - 0.51) < 0.011 && Math.min(c[0].x, c[1].x) < 0.5 && Math.max(c[0].x, c[1].x) > 0.5); };
    return { evenodd: covers('evenodd'), nonzero: covers('nonzero') }; })()`);
  t('a self-crossing star: even-odd leaves the middle empty, nonzero fills it', !r.evenodd && r.nonzero);
  const o = E(`(() => { const T = filledTargets([sq(0, 0, 1, 1), sq(0.4, 0.4, 0.6, 0.6)], [{ from: 0, to: 1, fill: [0, 0, 0], alpha: 1, rule: 'nonzero' }, { from: 1, to: 2, fill: [255, 255, 255], alpha: 1, rule: 'nonzero' }]);
    const a = hatchTarget(T[0], 20, 0.02, { join: true, occ: T[0].occ });
    return { occ: T[0].occ.length, top: T[1].occ.length, bad: segs(a.chains).filter(s => inRect(mid(s), 0.4, 0.4, 0.6, 0.6, 1e-6)).length, dark: T.map(x => +x.dark.toFixed(3)) }; })()`);
  t('a shape painted on top hides the lines underneath it', o.occ === 1 && o.top === 0 && o.bad === 0);
  t('fill darkness comes from the colour', o.dark[0] === 1 && o.dark[1] === 0);
  const tone = E(`(() => { const strokes = [sq(0, 0, 1, 1), sq(2, 0, 3, 1), sq(4, 0, 5, 1)];
    const shapes = [[0, 0, 0], [128, 128, 128], [250, 250, 250]].map((fill, i) => ({ from: i, to: i + 1, fill, alpha: 1, rule: 'nonzero' }));
    const T = { mode: 'filled', list: filledTargets(strokes, shapes) };
    const res = shadeDrawing(T, { ...SHADE_DEFAULTS, pattern: 'lines', angle: 0, spacing: 1, tone: true, join: false }, 50);
    const per = [0, 1, 2].map(i => res.owner.filter(o => o === i).length);
    const flat = shadeDrawing(T, { ...SHADE_DEFAULTS, pattern: 'lines', angle: 0, spacing: 1, tone: false, join: false }, 50);
    return { per, flat: [0, 1, 2].map(i => flat.owner.filter(o => o === i).length) }; })()`);
  t('darker colours get denser lines; near-white stays empty', tone.per[0] === 50 && Math.abs(tone.per[1] - 25) <= 1 && tone.per[2] === 0, `black ${tone.per[0]}, grey ${tone.per[1]}, white ${tone.per[2]} lines`);
  t('without tone every filled shape gets the same spacing (white still empty)', tone.flat[0] === 50 && tone.flat[1] === 50 && tone.flat[2] === 0);
}

/* ---------- concave shapes: links stay inside ---------- */
{
  const r = E(`(() => { const U = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0.7, y: 1 }, { x: 0.7, y: 0.3 }, { x: 0.3, y: 0.3 }, { x: 0.3, y: 1 }, { x: 0, y: 1 }, { x: 0, y: 0 }];
    const T = outlineTargets([U]); let bad = 0, chains = 0, lines = 0;
    for (const ang of [0, 33, 90, 135]) { const a = hatchTarget(T[0], ang, 0.04, { join: true }); chains += a.chains.length; lines += a.lines;
      bad += segs(a.chains).filter(s => inRect(mid(s), 0.3, 0.3, 0.7, 1.0, 0.012)).length; }
    return { bad, chains, lines }; })()`);
  t('zig-zag links never cut across the gap of a U shape', r.bad === 0, `${r.lines} lines in ${r.chains} pen strokes over 4 angles`);
  const circ = E(`(() => { const C = []; for (let i = 0; i <= 4000; i++) { const a = i / 4000 * 2 * Math.PI; C.push({ x: Math.cos(a) / 2, y: Math.sin(a) / 2 }); }
    const T = outlineTargets([C]); const t0 = Date.now(); const a = hatchTarget(T[0], 17, 0.002, { join: true }); const ms = Date.now() - t0;
    const off = segs(a.chains).filter(s => Math.hypot(mid(s).x, mid(s).y) > 0.5 + 1e-3).length;
    return { ms, lines: a.lines, chains: a.chains.length, off }; })()`);
  t('a 4000-point circle with 500 lines is quick, a few pen strokes, all inside', circ.ms < 400 && circ.chains <= 6 && circ.off === 0 && circ.lines >= 498, `${circ.lines} lines, ${circ.chains} stroke(s), ${circ.ms} ms`);
  const hole = E(`(() => { const C = (cx, cy, r, n) => { const p = []; for (let i = 0; i <= n; i++) { const a = i / n * 2 * Math.PI; p.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) }); } return p; };
    const T = outlineTargets([C(0, 0, 0.5, 600), C(0, 0, 0.2, 300)]);
    const a = hatchTarget(T[0], 60, 0.01, { join: true }), b = hatchTarget(T[0], 60, 0.01, { join: false });
    const inHole = segs(a.chains).filter(s => Math.hypot(mid(s).x, mid(s).y) < 0.2 - 1e-4).length;
    return { joined: a.chains.length, single: b.chains.length, inHole }; })()`);
  t('around a round hole the lines are linked along the hole\'s edge, never through it', hole.inHole === 0 && hole.joined <= 12 && hole.single > 100, `${hole.single} separate lines → ${hole.joined} pen strokes`);
  const gap = E(`(() => { const T = outlineTargets([sq(0, 0, 1, 1), sq(0.3, 0.3, 0.7, 0.7)]); const a = hatchTarget(T[0], 30, 0.03, { join: true, inset: 0.01 });
    return { bad: segs(a.chains).filter(s => inRect(mid(s), 0.3, 0.3, 0.7, 0.7, 1e-6) || !inRect(mid(s), 0, 0, 1, 1)).length, n: a.chains.length, lines: a.lines }; })()`);
  t('with a gap from the outline, links are short straight steps that stay inside', gap.bad === 0 && gap.n < gap.lines, `${gap.lines} lines in ${gap.n} pen strokes`);
  const under = E(`(() => { const T = filledTargets([sq(0, 0, 1, 1), sq(0.35, 0.2, 0.65, 0.8)], [{ from: 0, to: 1, fill: [0, 0, 0], alpha: 1, rule: 'nonzero' }, { from: 1, to: 2, fill: [255, 255, 255], alpha: 1, rule: 'nonzero' }]);
    const a = hatchTarget(T[0], 75, 0.02, { join: true, occ: T[0].occ }); const P = a.chains.flat();
    return { bad: segs(a.chains).filter(s => inRect(mid(s), 0.35, 0.2, 0.65, 0.8, 1e-6)).length + P.filter(p => inRect(p, 0.35, 0.2, 0.65, 0.8, 1e-6)).length, n: a.chains.length, lines: a.lines }; })()`);
  t('links never pass under a shape painted on top', under.bad === 0, `${under.lines} lines in ${under.n} pen strokes`);
}

/* ---------- angles ---------- */
{
  const st = E(`({ ...SHADE_DEFAULTS, pattern: 'lines', angle: 45 })`);
  const A = (i, over = {}, ov) => E(`shadeAngles(${i}, ${JSON.stringify({ ...st, ...over })}, ${JSON.stringify(ov || 'auto')})`);
  t('same angle for every shape by default', A(0)[0] === 45 && A(7)[0] === 45);
  t('alternate: neighbours at right angles', A(0, { vary: 'alt' })[0] === 45 && A(1, { vary: 'alt' })[0] === 135 && A(2, { vary: 'alt' })[0] === 45);
  t('turn 30° per shape', A(2, { vary: 'step30' })[0] === 105 && A(5, { vary: 'step30' })[0] === 15);
  const r1 = [0, 1, 2, 3, 4, 5].map(i => A(i, { vary: 'random', seed: 3 })[0]), r2 = [0, 1, 2, 3, 4, 5].map(i => A(i, { vary: 'random', seed: 3 })[0]), r3 = [0, 1, 2, 3, 4, 5].map(i => A(i, { vary: 'random', seed: 4 })[0]);
  t('random angles repeat for the same seed and change with a new one', JSON.stringify(r1) === JSON.stringify(r2) && JSON.stringify(r1) !== JSON.stringify(r3) && new Set(r1).size >= 3, r1.join(' '));
  t('cross-hatch and three directions', JSON.stringify(A(0, { pattern: 'cross' })) === '[45,135]' && JSON.stringify(A(0, { pattern: 'tri', angle: 0 })) === '[0,60,120]');
  t('a click override turns, cross-hatches or empties one shape', A(0, {}, 'r90')[0] === 135 && A(0, {}, 'cross').length === 2 && A(0, {}, 'off').length === 0);
  t('angles wrap to 0–180°', A(0, { angle: 170 }, 'r45')[0] === 35);
}

/* ---------- a whole drawing, sizes in mm, picking a shape ---------- */
{
  const r = E(`(() => { const T = shadeTargets({ strokes: [sq(-0.5, -0.5, 0.5, 0.5)] }, 'all');
    const st = { ...SHADE_DEFAULTS, pattern: 'lines', angle: 0, spacing: 2, join: false };
    const a = shadeDrawing(T, st, 100), b = shadeDrawing(T, st, 50);
    const gaps = a.strokes.map(c => c[0].y).sort((p, q) => p - q).slice(1).map((y, i, arr) => y - a.strokes.map(c => c[0].y).sort((p, q) => p - q)[i]);
    return { na: a.strokes.length, nb: b.strokes.length, gap: gaps[0] * 100, len: a.length, mode: T.mode }; })()`);
  t('spacing is in millimetres whatever the size', r.na === 50 && r.nb === 25 && Math.abs(r.gap - 2) < 1e-9, `100 mm → ${r.na} lines, 50 mm → ${r.nb}`);
  t('shaded length is reported in mm', Math.abs(r.len - 5000) < 1e-6);
  const fb = E(`shadeTargets({ strokes: [sq(0, 0, 1, 1)], shapes: [{ from: 0, to: 1, fill: null, alpha: 1, rule: 'nonzero' }] }, 'filled')`);
  t('"filled shapes" falls back to outlines when the SVG has no fills', fb.mode === 'all' && fb.fallback === true && fb.list.length === 1);
  const pick = E(`(() => { const T = shadeTargets({ strokes: [sq(0, 0, 1, 1), sq(0.3, 0.3, 0.7, 0.7)] }, 'all');
    const F = shadeTargets({ strokes: [sq(0, 0, 1, 1), sq(0.3, 0.3, 0.7, 0.7)], shapes: [{ from: 0, to: 1, fill: [0, 0, 0], alpha: 1, rule: 'nonzero' }, { from: 1, to: 2, fill: [90, 90, 90], alpha: 1, rule: 'nonzero' }] }, 'filled');
    return { inner: shadeTargetAt(T, { x: 0.5, y: 0.5 }), outer: shadeTargetAt(T, { x: 0.1, y: 0.5 }), none: shadeTargetAt(T, { x: 2, y: 2 }), top: shadeTargetAt(F, { x: 0.5, y: 0.5 }), innerDepth: T.list[shadeTargetAt(T, { x: 0.5, y: 0.5 })].depth }; })()`);
  t('clicking picks the innermost outline, or the top-most filled shape', pick.innerDepth === 1 && pick.outer !== pick.inner && pick.none === -1 && pick.top === 1);
  const ov = E(`(() => { const T = shadeTargets({ strokes: [sq(0, 0, 1, 1), sq(2, 0, 3, 1)] }, 'all'); const st = { ...SHADE_DEFAULTS, pattern: 'lines', angle: 0, spacing: 10, join: false };
    const m = new Map([[1, 'off']]); const a = shadeDrawing(T, st, 100, m), b = shadeDrawing(T, st, 100, new Map([[0, 'r90']]));
    const vert = b.strokes.filter((c, k) => b.owner[k] === 0).every(c => Math.abs(c[0].x - c[1].x) < 1e-9);
    return { a: [0, 1].map(i => a.owner.filter(o => o === i).length), vert }; })()`);
  t('per-shape choices: one shape left empty, another turned 90°', ov.a[0] > 0 && ov.a[1] === 0 && ov.vert);
}

console.log(fails ? `\n${fails} FAILED` : '\nall passed');
process.exit(fails ? 1 : 0);
