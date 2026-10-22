// Unit tests for the SVG path reader and the drawing library data (run: node tests/unit/test_library.js)
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { console, Math, Array, Object, Number, JSON, Infinity, NaN, isFinite, Set, Map, String, RegExp, parseFloat };
vm.createContext(ctx);
for (const f of ['part2_geometry.js', 'part3_svg.js', 'part40_library_data.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };
const P = (d, step = 0.5) => E(`pathDataToPolylines(${JSON.stringify(d)}, ${step})`);
const near = (p, x, y, tol = 1e-6) => Math.abs(p.x - x) < tol && Math.abs(p.y - y) < tol;
const last = s => s[s.length - 1];

/* ---------- path commands ---------- */
{
  const a = P('M10 10 L90 10 L90 90 Z');
  t('lines and close: one closed outline back to the start', a.length === 1 && a[0].length === 4 && near(last(a[0]), 10, 10));
  const b = P('M10,10 l80,0 0,80 -80,0z');
  t('relative lines with implicit repeats', b.length === 1 && near(b[0][2], 90, 90) && near(b[0][3], 10, 90) && near(last(b[0]), 10, 10));
  const c = P('M10 50 H90 V90 h-80 v-40');
  t('horizontal and vertical lines', near(c[0][1], 90, 50) && near(c[0][2], 90, 90) && near(c[0][3], 10, 90) && near(c[0][4], 10, 50));
  const m = P('M10 10 20 20 30 10');
  t('extra pairs after a move are lines', m.length === 1 && m[0].length === 3 && near(m[0][2], 30, 10));
  const sub = P('M10 10 L20 20 M30 30 L40 40 z m5 5 l10 0');
  t('every move starts a new stroke; a relative move after z starts at the subpath start', sub.length === 3 && near(sub[2][0], 35, 35) && near(sub[2][1], 45, 35));
  const z2 = P('M 50 50 m 10 10 l 20 0 z l 0 20');
  t('a line after z continues from the closed subpath start', z2.length === 2 && near(z2[1][0], 60, 60) && near(z2[1][1], 60, 80));
}
/* ---------- curves ---------- */
{
  const cub = P('M10 80 C 40 10, 65 10, 95 80 S 150 150, 180 80');
  const s = cub[0], mid = s[Math.round((s.length - 1) / 4)];
  t('cubic and smooth cubic end exactly at their end points', near(last(s), 180, 80) && s.some(p => near(p, 95, 80)));
  // the reflected control point makes the curve symmetric: lowest point of the S part mirrors the C part's highest point
  const ys = s.map(p => p.y), top = Math.min(...ys), bot = Math.max(...ys);
  t('smooth cubic reflects the previous control point', Math.abs((80 - top) - (bot - 80)) < 0.5, `rise ${(80 - top).toFixed(2)}, fall ${(bot - 80).toFixed(2)}`);
  const rel = P('m10 80 c30-70 55-70 85 0 s55 70 85 0');
  t('relative cubic curves give the same shape', rel[0].length === s.length && rel[0].every((p, i) => near(p, s[i].x, s[i].y, 1e-9)));
  const q = P('M10 80 Q 52.5 10, 95 80 T 180 80');
  const qy = q[0].map(p => p.y);
  t('quadratic and smooth quadratic curves', near(last(q[0]), 180, 80) && Math.abs((80 - Math.min(...qy)) - (Math.max(...qy) - 80)) < 0.5 && Math.abs(Math.min(...qy) - 45) < 0.3);
  // the straight pieces follow the true curve closely (checked against 2000 exact points of the first cubic)
  const B = u => { const v = 1 - u; return { x: v * v * v * 10 + 3 * v * v * u * 40 + 3 * v * u * u * 65 + u * u * u * 95, y: v * v * v * 80 + 3 * v * v * u * 10 + 3 * v * u * u * 10 + u * u * u * 80 }; };
  const segD = (p, a, b) => { const dx = b.x - a.x, dy = b.y - a.y, L2 = dx * dx + dy * dy, u = L2 ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2)) : 0; return Math.hypot(a.x + u * dx - p.x, a.y + u * dy - p.y); };
  let gap = 0; for (let k = 0; k <= 2000; k++) { const p = B(k / 2000); let best = Infinity; for (let i = 1; i < s.length; i++) best = Math.min(best, segD(p, s[i - 1], s[i])); gap = Math.max(gap, best); }
  t('curves are cut finely: never more than a tenth of the step from the true curve', gap < 0.05, `largest gap ${gap.toFixed(4)} (step 0.5)`);
}
/* ---------- arcs ---------- */
{
  const r = P('M50 100 A50 50 0 1 0 150 100 A50 50 0 1 0 50 100 Z', 0.5)[0];
  const dev = Math.max(...r.map(p => Math.abs(Math.hypot(p.x - 100, p.y - 100) - 50)));
  t('a circle made of two arcs stays on the circle', dev < 1e-9 && near(last(r), 50, 100));
  const glued = P('M10 10a40 20 30 1110 10'), spaced = P('M10 10a40 20 30 1 1 10 10');
  t('arc flags without separators are read like spaced ones', glued[0].length === spaced[0].length && near(last(glued[0]), 20, 20));
  const small = P('M10 10a5 5 0 0 1 100 0')[0];
  const ymin = Math.min(...small.map(p => p.y));
  t('an arc radius that is too small is scaled up to a half circle', near(last(small), 110, 10) && Math.abs(ymin - (10 - 50)) < 0.01, `top at y=${ymin.toFixed(2)}`);
  const sweep = P('M80 80 A45 45 0 0 0 125 125')[0], sweep1 = P('M80 80 A45 45 0 0 1 125 125')[0];
  const side = s => s[Math.floor(s.length / 2)];
  t('sweep flag picks the side of the arc', side(sweep).x < side(sweep1).x && side(sweep).y > side(sweep1).y);
  const flat = P('M0 0 A0 10 0 0 1 50 0')[0];
  t('an arc with a zero radius is a straight line', flat.length === 2 && near(flat[1], 50, 0));
}
/* ---------- number syntax and errors ---------- */
{
  const g = P('M.5.5L10.5.5.5 10.5')[0];
  t('numbers glued with dots', g.length === 3 && near(g[1], 10.5, 0.5) && near(g[2], 0.5, 10.5));
  const e = P('M1e1 1e1L9e1 1E1 9.0e+1 9.0e1')[0];
  t('exponents', near(e[0], 10, 10) && near(e[1], 90, 10) && near(e[2], 90, 90));
  const n = P('M10-10L-10 20-30-40')[0];
  t('minus signs separate numbers', near(n[0], 10, -10) && near(n[1], -10, 20) && near(n[2], -30, -40));
  const bad = P('M0 0 L100 0 L100 100 X 0 100');
  t('malformed data keeps what was read before the error', bad.length === 1 && bad[0].length === 3);
  t('empty or garbage data gives no strokes', P('').length === 0 && P('hello').length === 0 && P('M10 10').length === 0);
}
/* ---------- the library ---------- */
{
  const L = E('LIBRARY'), C = E('LIBRARY_CATS'), SRC = E('LIBRARY_SOURCES');
  const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  const decode = s => {           // independent reader for the stored lines (count, then zig-zag deltas)
    let i = 0, x = 0, y = 0; const out = [];
    const vint = () => { let v = 0, sh = 0, d; do { d = B64.indexOf(s[i++]); if (d < 0) throw new Error('bad character'); v += (d & 31) * 2 ** sh; sh += 5; } while (d & 32); return v; };
    const zz = v => (v % 2 ? -(v + 1) / 2 : v / 2);
    while (i < s.length) { const n = vint(), a = []; for (let k = 0; k < n; k++) { x += zz(vint()); y += zz(vint()); a.push([x, y]); } out.push(a); }
    return out;
  };
  const per = new Map(); for (const e of L) per.set(e.c, (per.get(e.c) || 0) + 1);
  t('over 2000 drawings with unique ids', L.length > 2000 && new Set(L.map(e => e.i)).size === L.length, `${L.length} drawings`);
  const asked = ['animals', 'cars', 'nature', 'leaves', 'signs', 'zodiac', 'emojis', 'femalepose', 'malepose', 'faces', 'objects', 'skylines', 'topography', 'sports',
                 'clothing', 'shoes', 'sportscars', 'ants', 'aircraft', 'army', 'constellations', 'flags', 'technology', 'art', 'phones', 'music', 'songs', 'scifi'];
  t('every requested category is there with at least 50 drawings', asked.every(k => C.some(c => c[0] === k) && per.get(k) >= 50),
    asked.filter(k => !(per.get(k) >= 50)).map(k => `${k} ${per.get(k) || 0}`).join(', ') || `${C.length} categories`);
  t('every category in the list has drawings and every drawing has a known category', C.every(([k]) => per.get(k) >= 50) && L.every(e => C.some(([k]) => k === e.c)),
    C.filter(([k]) => !(per.get(k) >= 50)).map(([k]) => `${k} ${per.get(k) || 0}`).join(', '));
  const names = new Map(); let dupName = [];
  for (const e of L) { const k = e.c + '|' + e.n; if (names.has(k)) dupName.push(e.n); names.set(k, 1); }
  t('names are unique within each category', !dupName.length, dupName.slice(0, 5).join(', '));
  let worst = 0, worstId = '', badBox = [], badCount = [], badLen = [], badFill = [], badCode = [];
  for (const e of L) {
    let S;
    try { S = decode(e.p); } catch (err) { badCode.push(e.i); continue; }
    if (S.length !== e.l || S.some(s => s.length < 2)) badCount.push(e.i);
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, len = 0;
    for (const s of S) { for (const [x, y] of s) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); } for (let i = 1; i < s.length; i++) len += Math.hypot(s[i][0] - s[i - 1][0], s[i][1] - s[i - 1][1]); }
    if (x0 !== 0 || y0 !== 0 || x1 !== e.w || y1 !== e.h || Math.max(e.w, e.h) !== 1000) badBox.push(e.i);
    if (Math.abs(len / 10 - e.m) > 1) badLen.push(e.i);
    if (e.m > worst) { worst = e.m; worstId = e.i; }
    if (e.f && !(Array.isArray(e.f) && e.f.every(([col, a, b]) => /^#[0-9a-f]{6}$/i.test(col) && Number.isInteger(a) && Number.isInteger(b) && a >= 0 && a < b && b <= S.length))) badFill.push(e.i);
  }
  t('every drawing decodes cleanly', !badCode.length, badCode.slice(0, 5).join(' '));
  t('every drawing reads back as its stated number of pen lines', !badCount.length, badCount.slice(0, 5).join(' '));
  t('every drawing fills a 1000-unit box exactly (longest side = 100 mm)', !badBox.length, badBox.slice(0, 5).join(' '));
  t('stated pen length matches the lines', !badLen.length, badLen.slice(0, 5).join(' '));
  t('no drawing is a monster: longest is under 15 m of line at 100 mm', worst < 15000, `${(worst / 1000).toFixed(1)} m (${worstId})`);
  t('colour fills point at real lines and use plain colours', !badFill.length && L.filter(e => e.f).length >= 95, badFill.slice(0, 5).join(' ') || `${L.filter(e => e.f).length} coloured drawings`);
  t('every flag keeps its colours', L.filter(e => e.c === 'flags').every(e => e.f && e.f.length >= 1));
  t('every drawing has a source with a licence, and credits its maker', L.every(e => SRC[e.s] && SRC[e.s].license && e.n && (e.a || SRC[e.s].author)));
  t('MIT and BSD sources carry their licence text', SRC.filter(s => /MIT|BSD/.test(s.license)).every(s => s.notice && s.notice.length > 200), SRC.filter(s => /MIT|BSD/.test(s.license)).map(s => s.name).join(', '));
  t('no e-mail addresses are stored', !L.some(e => /@/.test(`${e.a || ''} ${e.n}`)));
}

console.log(fails ? `\n${fails} FAILED` : '\nall passed');
process.exit(fails ? 1 : 0);
