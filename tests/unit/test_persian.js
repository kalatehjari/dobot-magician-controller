// Unit tests for Persian text: the single-line Persian font, letter forms, right-to-left order (run: node tests/unit/test_persian.js)
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { console, Math, Array, Object, Number, JSON, Infinity, NaN, isFinite, Set, Map, String, RegExp, parseFloat, Int8Array, Error };
vm.createContext(ctx);
for (const f of ['part2_geometry.js', 'part44_fonts_data.js', 'part45_text.js', 'part57_persian_font.js', 'part58_persian.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };
const hex = a => a.map(c => c.toString(16).toUpperCase()).join(' ');
E(`var box = L => { let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity; for (const s of L) for (const p of s) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); } return { x0, y0, x1, y1, w: x1 - x0, h: y1 - y0 }; };`);

/* ---------- the font ---------- */
{
  const r = E(`(() => { const G = fontGlyphs(FA_FONT), alef = G.map.get('ا').box, bad = [], nf = [];
    for (const [b, ...f] of FA_FORM_LIST) f.forEach((c, k) => { const ch = String.fromCharCode(c); if (!G.map.has(ch) && !(k === 0 && G.map.has(String.fromCharCode(b)))) bad.push(c); if (ch.normalize('NFKC') !== String.fromCharCode(b)) nf.push(c); });
    for (const [a, i, f] of FA_LAM_ALEF) for (const c of [i, f]) { const ch = String.fromCharCode(c); if (!G.map.has(ch)) bad.push(c); if (ch.normalize('NFKC') !== 'ل' + String.fromCharCode(a)) nf.push(c); }
    const marks = [...'\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0654\u0655\u0670'].filter(c => !G.map.has(c));
    const digits = [...'۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩0123456789'].filter(c => !G.map.has(c) || !G.map.get(c).strokes.length);
    const punct = [...'،؛؟«»٪.!?()'].filter(c => !G.map.has(c));
    return { n: G.map.size, top: alef.y0, bottom: alef.y1, bad, nf, marks, digits, punct, lic: FA_FONT_LICENCE }; })()`);
  t('the Persian font decodes (over 330 glyphs)', r.n > 330, `${r.n} glyphs`);
  t('letter height = alef: alef stands on the line and is one unit tall', Math.abs(r.bottom) < 0.04 && Math.abs(r.top + 1) < 0.03, `${r.top.toFixed(3)} … ${r.bottom.toFixed(3)}`);
  t('every letter form and lam-alef is in the font (an isolated form may be the letter itself)', !r.bad.length, hex(r.bad));
  t('each form is the form of its letter (Unicode decomposition)', !r.nf.length, hex(r.nf));
  t('vowel marks, Persian, Arabic and Latin digits, Persian punctuation are drawable', !r.marks.length && !r.digits.length && !r.punct.length, [...r.marks, ...r.digits, ...r.punct].join(' '));
  t('the font licence (SIL OFL 1.1, Vazirmatn) travels with it', /SIL OPEN FONT LICENSE Version 1\.1/i.test(r.lic) && /Vazirmatn/i.test(r.lic));
}

/* ---------- joined letters meet ---------- */
{
  const r = E(`(() => { const G = fontGlyphs(FA_FONT), j = FONT_DATA[FA_FONT].join / FONT_CAP, bad = [];
    const has = (g, x) => g.strokes.some(s => [s[0], s[s.length - 1]].some(p => Math.abs(p.x - x) < 1e-9 && Math.abs(p.y - j) < 1e-9));
    for (const [b, iso, fin, ini, med] of FA_FORM_LIST) {
      const chk = (c, l, r) => { if (!c) return; const g = G.map.get(String.fromCharCode(c)); if ((l && !has(g, 0)) || (r && !has(g, g.adv))) bad.push(c.toString(16)); };
      chk(fin, false, true); chk(ini, true, false); chk(med, true, true);
    }
    for (const [a, i, f] of FA_LAM_ALEF) { const g = G.map.get(String.fromCharCode(f)); if (!has(g, g.adv)) bad.push(f.toString(16)); }
    const tw = G.map.get('ـ'); if (!has(tw, 0) || !has(tw, tw.adv)) bad.push('640');
    return { bad, j }; })()`);
  t('joining strokes end exactly at the joining point on each joining side (final, initial, middle, tatweel)', !r.bad.length, r.bad.join(' '));
  t('letters join just above the line', r.j < 0 && r.j > -0.1, r.j.toFixed(3));
}

/* ---------- letter forms ---------- */
{
  const cases = [
    ['سلام', [0xFEB3, 0xFEFC, 0xFEE1]],
    ['کتاب\u200Cها', [0xFB90, 0xFE98, 0xFE8E, 0xFE8F, 0xFEEB, 0xFE8E]],       // half-space keeps کتاب and ها apart
    ['ب\u200D', [0xFE91]],                                                    // zero-width joiner: initial form on its own
    ['ـبـ', [0x0640, 0xFE92, 0x0640]],                                       // tatweel joins both sides
    ['بلا', [0xFE91, 0xFEFC]], ['لأ', [0xFEF7]], ['لا', [0xFEFB]], ['آلات', [0xFE81, 0xFEFB, 0xFE95]],
    ['پژوهش', [0xFB58, 0xFB8B, 0xFEED, 0xFEEB, 0xFEB6]],
    ['گفتگو', [0xFB94, 0xFED4, 0xFE98, 0xFB95, 0xFEEE]],
    ['مسئله', [0xFEE3, 0xFEB4, 0xFE8C, 0xFEE0, 0xFEEA]],
    ['چرا', [0xFB7C, 0xFEAE, 0xFE8D]],
    ['یی', [0xFBFE, 0xFBFD]], ['ییی', [0xFBFE, 0xFBFF, 0xFBFD]],
  ];
  const bad = [];
  for (const [w, want] of cases) {
    const got = E(`faShapeLine([...faPrepare(${JSON.stringify(w)}, false)]).map(c => (c.glyph || c.ch).codePointAt(0))`);
    if (JSON.stringify(got) !== JSON.stringify(want)) bad.push(`${w}: ${hex(got)} (want ${hex(want)})`);
  }
  t(`letter forms (isolated, initial, middle, final, lam-alef, ZWNJ, ZWJ, tatweel) — ${cases.length} words, checked against HarfBuzz`, !bad.length, bad.join('; '));
  const m = E(`faShapeLine([...faPrepare('ب\u064E\u0651', false)]).map(c => ({ g: c.glyph, marks: c.marks.join('') }))`);
  t('marks stay on their letter (one letter, two marks)', m.length === 1 && m[0].marks.length === 2, JSON.stringify(m));
  const p = E(`[faPrepare('\\uFEB3\\uFEFC\\uFEE1\\uFE81', false), faPrepare('ا\u0653', false), faPrepare('سال 1403 و MP3 و ۲.5', true), faPrepare('123 abc', true)]`);
  t('pasted presentation forms become letters again; alef + madda → آ', p[0] === 'سلامآ' && p[1] === 'آ', p.slice(0, 2).join(' | '));
  t('Persian digits: 0–9 become ۰–۹, except inside English (MP3)', p[2] === 'سال ۱۴۰۳ و MP3 و ۲.۵' && p[3] === '123 abc', p.slice(2).join(' | '));
}

/* ---------- right to left with English and numbers (checked against the Unicode bidi algorithm, python-bidi) ---------- */
{
  const cases = [
    ['abc سلام 123', '123 مالس abc'], ['سلام abc 123 def', 'abc 123 def مالس'], ['سال 1403 و MP3', 'MP3 و 1403 لاس'],
    ['قیمت 25% و 3.14 و 1,000', '1,000 و 3.14 و %25 تمیق'], ['1+2 سلام', 'مالس 1+2'], ['سلام 1+2', '2+1 مالس'],
    ['نسخه 1.6.0 آماده است', 'تسا هدامآ 1.6.0 هخسن'], ['Hi (there) سلام', 'مالس Hi (there)'], ['سلام (abc) خوب', 'بوخ )abc( مالس'],
    ['٣٤ و ١٢', '١٢ و ٣٤'], ['C++ و Python 3.12', 'Python 3.12 و ++C'], ['دمای -5 درجه', 'هجرد 5- یامد'], ['سلام   ', '   مالس'],
  ];
  const bad = [];
  for (const [s, want] of cases) {
    const got = E(`(() => { const a = [...${JSON.stringify(s)}], lv = faBidiLevels(a.map(faBidiClass), a); return faReorder(a, lv).join(''); })()`);
    if (got !== want) bad.push(`${s} → ${got} (want ${want})`);
  }
  t(`visual order of mixed lines (${cases.length} cases incl. numbers, signs, brackets, trailing spaces)`, !bad.length, bad.join('; '));
  const pairs = E(`faBracketPairs([...'a(b[c)d]e(f)'])`);
  t('bracket pairs (BD16): only properly nested pairs', JSON.stringify(pairs) === '[[1,5],[9,11]]', JSON.stringify(pairs));
}

/* ---------- layout ---------- */
{
  const r = E(`(() => { const G = fontGlyphs(FA_FONT);
    const L = textLayout({ str: 'سلام', lang: 'fa', align: 'right' });
    const b = box(L.strokes);
    const seam = faLayoutLine(G, 'سلام', {}).glyphs;            // visual: meem, lam-alef, seen (left to right)
    const j = FONT_DATA[FA_FONT].join / FONT_CAP, x = seam[2].x;
    const ends = (g) => g.strokes.flatMap(s => [s[0], s[s.length - 1]]).map(p => ({ x: p.x + g.x, y: p.y }));
    const meet = ends(seam[1]).some(p => Math.abs(p.x - x) < 1e-9 && Math.abs(p.y - j) < 1e-9) && ends(seam[2]).some(p => Math.abs(p.x - x) < 1e-9 && Math.abs(p.y - j) < 1e-9);
    const sp0 = textLayout({ str: 'سلام', lang: 'fa' }).strokes.length, sp1 = textLayout({ str: 'سلام', lang: 'fa', spacing: 0.2 }).strokes.length;
    const two = textLayout({ str: 'سلام\\nدنیا', lang: 'fa' });
    const bold = textLayout({ str: 'سلام', lang: 'fa', style: 'bold' }).strokes.length, ital = textLayout({ str: 'ا', lang: 'fa', style: 'italic' });
    const mir = faLayoutLine(G, '(سلام)', {}).glyphs, paren = G.map.get('(').strokes, close = G.map.get(')').strokes;
    const d1 = textLayout({ str: '123', lang: 'fa' }).strokes, d2 = textLayout({ str: '۱۲۳', lang: 'fa' }).strokes, d3 = textLayout({ str: '123', lang: 'fa', faDigits: false }).strokes;
    const miss = textLayout({ str: 'سلام 漢', lang: 'fa' }).missing;
    const latin = textLayout({ str: 'سلام', family: 'sans' });
    const mk = textLayout({ str: 'ا\u064E', lang: 'fa' }), mb = box(mk.strokes);
    return { b, w: L.width, missing: L.missing, meet, sp0, sp1, pitch: two.pitch, lines: two.lines, bold, italSlant: ital.font.fakeItalic, mirL: mir[0].strokes === paren, mirR: mir[mir.length - 1].strokes === close,
      digits: JSON.stringify(d1) === JSON.stringify(d2) && JSON.stringify(d1) !== JSON.stringify(d3), miss, latinMissing: latin.missing.length, font: L.font.family.name, markTop: mb.y0 };
  })()`);
  t('Persian text lays out right-aligned: ends at the alignment point, nothing missing', Math.abs(r.b.x1) < 0.2 && r.b.x0 < -2.5 && !r.missing.length, `x ${r.b.x0.toFixed(2)} … ${r.b.x1.toFixed(2)}, width ${r.w.toFixed(2)}`);
  t('joined letters meet: seen ends where lam-alef begins, at the joining height', r.meet);
  t('letter spacing keeps joined letters joined (a line bridges the gap)', r.sp1 === r.sp0 + 1, `${r.sp0} → ${r.sp1} lines`);
  t('two lines, wider line spacing for Persian (marks and letters below the line)', r.lines === 2 && Math.abs(r.pitch - 2.2) < 1e-9, `pitch ${r.pitch}`);
  t('bold doubles the pen lines; italic is not used for Persian', r.bold === 2 * r.sp0 && r.italSlant === false);
  t('brackets are mirrored in right-to-left text: (سلام) reads correctly', r.mirL && r.mirR);
  t('0–9 drawn as Persian digits, or as typed when that is off', r.digits);
  t('characters the font lacks are reported', r.miss.length === 1 && r.miss[0] === '漢', JSON.stringify(r.miss));
  t('Persian letters typed with Persian off are reported missing (the Latin fonts have none)', r.latinMissing === 4);
  t('a vowel mark sits above alef', r.markTop < -1.05, r.markTop.toFixed(3));
  t('the font is named for messages', r.font === 'Vazir (Persian)', r.font);
}

console.log(fails ? `\n${fails} FAILED` : '\nall Persian text tests passed');
process.exit(fails ? 1 : 0);
