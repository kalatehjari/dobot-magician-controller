// Unit tests for the plotter fonts and text layout (run: node tests/unit/test_text.js)
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { console, Math, Array, Object, Number, JSON, Infinity, NaN, isFinite, Set, Map, String, RegExp, parseFloat, Int8Array, Error };
vm.createContext(ctx);
for (const f of ['part2_geometry.js', 'part44_fonts_data.js', 'part45_text.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };
E(`var box = L => { let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity; for (const s of L) for (const p of s) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); } return { x0, y0, x1, y1, w: x1 - x0, h: y1 - y0 }; };`);

/* ---------- font data ---------- */
{
  const r = E(`(() => { const out = {}; for (const f of FONT_FAMILIES) for (const file of Object.values(f.files)) {
      const G = fontGlyphs(file), med = a => a.sort((p, q) => p - q)[a.length >> 1];
      const caps = [...'BDEFHIKLMNPRTUVWXZ'].map(c => box(G.map.get(c).strokes));
      out[file] = { n: G.map.size, top: med(caps.map(b => b.y0)), bottom: med(caps.map(b => b.y1)), xh: G.xh, digits: [...'0123456789'].every(c => G.map.has(c)) }; }
    return out; })()`);
  const files = Object.keys(r);
  t('20 font files decode', files.length === 20, files.join(' '));
  t('every font has the printable ASCII letters and digits', files.every(f => r[f].n >= 95 && r[f].digits));
  t('Latin-1 accented letters in the 18 SVG fonts', files.filter(f => r[f].n >= 187).length === 18);
  t('capitals stand on the baseline and are one cap height tall (median, within 6 %)', files.every(f => Math.abs(r[f].bottom) < 0.06 && Math.abs(r[f].top + 1) < 0.06),
    files.filter(f => !(Math.abs(r[f].bottom) < 0.06 && Math.abs(r[f].top + 1) < 0.06)).map(f => `${f} ${r[f].top.toFixed(2)}…${r[f].bottom.toFixed(2)}`).join(', '));
  t('x-height between 0.4 and 0.85 of the cap height', files.every(f => r[f].xh > 0.4 && r[f].xh < 0.85));
  const lic = E(`({ ofl: FONT_CREDITS.ofl.startsWith('SIL OPEN FONT LICENSE Version 1.1') && FONT_CREDITS.ofl.includes('DISCLAIMER'), ems: Object.keys(FONT_CREDITS.ems).length, hershey: /Hershey/.test(FONT_CREDITS.hershey) && /James Hurt/.test(FONT_CREDITS.hershey) })`);
  t('licence texts travel with the fonts (OFL 1.1, 9 EMS notices, Hershey acknowledgements)', lic.ofl && lic.ems === 9 && lic.hershey);
}

/* ---------- styles ---------- */
{
  const r = E(`['sans', 'serif', 'tech', 'readability', 'script'].map(k => ['regular', 'bold', 'italic', 'bolditalic'].map(s => { const f = fontResolve(k, s); return f.file + (f.fakeBold ? '+B' : '') + (f.fakeItalic ? '+I' : ''); }))`);
  t('serif has four real styles', r[1].join() === 'HersheySerifMed,HersheySerifBold,HersheySerifMedItalic,HersheySerifBoldItalic');
  t('sans bold is the medium font; italic slants it', r[0].join() === 'HersheySans1,HersheySansMed,HersheySans1+I,HersheySansMed+I');
  t('a font with one style makes up bold and italic', r[2].join() === 'EMSTech,EMSTech+B,EMSTech+I,EMSTech+B+I');
  t('readability: real italic, made-up bold', r[3].join() === 'EMSReadability,EMSReadability+B,EMSReadabilityItalic,EMSReadabilityItalic+B');
  t('an unknown family falls back to Sans', E(`fontResolve('nope', 'regular').file`) === 'HersheySans1');
}

/* ---------- layout ---------- */
{
  const r = E(`(() => {
    const L = textLayout({ str: 'HI', family: 'sans', align: 'left' }), C = textLayout({ str: 'HI', family: 'sans', align: 'center' }), R = textLayout({ str: 'HI', family: 'sans', align: 'right' });
    return { l: box(L.strokes), c: box(C.strokes), r: box(R.strokes), w: L.width }; })()`);
  t('left alignment starts at the origin (plus the letter’s side bearing), on the baseline', Math.abs(r.l.y1) < 0.02 && r.l.x0 >= -0.01 && r.l.x0 < 0.5, `starts ${r.l.x0.toFixed(2)}`);
  t('centre alignment is centred on the origin', Math.abs((r.c.x0 + r.c.x1) / 2) < 0.15);
  t('right alignment ends at the origin', r.r.x1 <= 0.01 && r.r.x1 > -0.3);
  const sp = E(`(() => { const a = textLayout({ str: 'ABCD', align: 'left' }), b = textLayout({ str: 'ABCD', align: 'left', spacing: 0.5 }); return [a.width, b.width]; })()`);
  t('letter spacing adds that much between letters', Math.abs(sp[1] - sp[0] - 1.5) < 1e-9, `${sp[0].toFixed(3)} → ${sp[1].toFixed(3)}`);
  const ln = E(`(() => { const a = textLayout({ str: 'A\\nB', align: 'left' }), b = textLayout({ str: 'A\\nB', align: 'left', lineGap: 2 }), c = textLayout({ str: 'A\\r\\nB\\rC', align: 'left' }); return [box(a.strokes).h, box(b.strokes).h, a.lines, c.lines]; })()`);
  t('lines are 1.6 cap heights apart; line spacing 2 doubles it', Math.abs(ln[0] - 2.6) < 0.05 && Math.abs(ln[1] - 4.2) < 0.05 && ln[2] === 2, ln.slice(0, 2).map(v => v.toFixed(2)).join(' → '));
  t('Windows and old Mac line ends both start new lines', ln[3] === 3);
  const it = E(`(() => { const a = textLayout({ str: 'I', family: 'tech', align: 'left' }), b = textLayout({ str: 'I', family: 'tech', style: 'italic', align: 'left' });
    const top = s => s.reduce((m, p) => p.y < m.y ? p : m), bot = s => s.reduce((m, p) => p.y > m.y ? p : m);
    const sa = a.strokes[0], sb = b.strokes[0]; return { a: top(sa).x - bot(sa).x, b: (top(sb).x - bot(sb).x) / (bot(sb).y - top(sb).y), base: bot(sb).x - bot(sa).x }; })()`);
  t('made-up italic slants 12°, pivoting on the baseline', Math.abs(it.b - (it.a + Math.tan(12 * Math.PI / 180))) < 0.02 && Math.abs(it.base) < 0.02, `slope ${it.b.toFixed(3)}`);
  const bd = E(`(() => { const a = textLayout({ str: 'Hi', family: 'tech', height: 10 }), b = textLayout({ str: 'Hi', family: 'tech', style: 'bold', height: 10 }), c = textLayout({ str: 'Hi', family: 'tech', style: 'bold', height: 35 });
    const n = a.strokes.length, d = (L, i) => Math.hypot(L.strokes[i + n][0].x - L.strokes[i][0].x, L.strokes[i + n][0].y - L.strokes[i][0].y); return { n, nb: b.strokes.length, d10: d(b, 0) * 10, d35: d(c, 0) * 35 }; })()`);
  t('made-up bold: every line twice, 0.35 mm apart at any letter height', bd.nb === 2 * bd.n && Math.abs(bd.d10 - 0.35) < 1e-6 && Math.abs(bd.d35 - 0.35) < 1e-6, `${bd.d10.toFixed(3)} / ${bd.d35.toFixed(3)} mm`);
}

/* ---------- characters ---------- */
{
  const r = E(`(() => {
    const one = (s, fam = 'sans') => textLayout({ str: s, family: fam, align: 'left' });
    const a = one('a'), am = one('ā'), i = one('i'), im = one('ī'), O = one('O'), Om = one('Ō');
    const bA = box(a.strokes), bAm = box(am.strokes), bO = box(O.strokes), bOm = box(Om.strokes);
    const dotless = im.strokes.length === i.strokes.length;          // the dot of i is replaced by the macron
    return { macron: am.strokes.length === a.strokes.length + 1 && bAm.y0 < bA.y0 - 0.05 && am.missing.length === 0, cap: bOm.y0 < bO.y0 - 0.05 && bOm.y0 > -1.5,
      dotless, nbsp: one('a b').width === one('a b').width, quotes: one('‘x’').missing.length === 0 && one('ł Ł đ ħ').missing.length === 0,
      ell: one('…').strokes.length === one('...').strokes.length, nfkd: one('ﬁ').strokes.length === one('fi').strokes.length,
      star: JSON.stringify(one('a★b☃').missing), gothic: one('“é”', 'gothicde').missing.length, tab: one('a\\tb').width > one('a b').width };
  })()`);
  t('ā: the letter with a macron drawn above it', r.macron);
  t('Ō: the macron sits above the capital', r.cap);
  t('ī: the macron replaces the dot', r.dotless);
  t('no-break spaces, curly quotes and barred letters (ł đ ħ) are drawn', r.nbsp && r.quotes);
  t('… is three dots; the ﬁ ligature is f and i', r.ell && r.nfkd);
  t('characters no font has are reported, once each', r.star === '["★","☃"]', r.star);
  t('Gothic German (ASCII only) still writes “é” with made-up quotes and accent', r.gothic === 0);
  t('a tab is four spaces', r.tab);
  const lab = E(`[textLabel('  \\n Hello there '), textLabel(''), textLabel('A very long line of text that goes on and on')]`);
  t('object names: first line, trimmed and shortened', lab[0] === 'Hello there' && lab[1] === 'Text' && lab[2].length === 24 && lab[2].endsWith('…'), JSON.stringify(lab));
}

/* ---------- every family writes a sample ---------- */
{
  const r = E(`FONT_FAMILIES.map(f => { const L = textLayout({ str: 'Quick brown fox 123 éàü ÅØ ñç Māori', family: f.key, style: 'bolditalic' }); return [f.key, L.strokes.length, L.missing.join('')]; })`);
  t('all 13 families write accented sample text in bold italic with nothing missing', r.length === 13 && r.every(x => x[1] > 20 && x[2] === ''), r.filter(x => x[2]).map(x => x.join(':')).join(' '));
  const ms = E(`(() => { const t0 = Date.now(); for (let i = 0; i < 200; i++) textLayout({ str: 'The quick brown fox jumps over the lazy dog ' + i, family: 'serif', style: 'bold' }); return Date.now() - t0; })()`);
  t('layout is fast (200 sentences)', ms < 400, `${ms} ms`);
}

console.log(fails ? `\n${fails} FAILED` : '\nall passed');
process.exitCode = fails ? 1 : 0;
