/* ===================== PERSIAN TEXT (pure, unit-tested) =====================
   Lays out Persian (and other Arabic-script) text in the single-line Persian font of part57. Each
   letter takes its isolated, initial, middle or final form from its neighbours (a zero-width
   non-joiner, the Persian half-space, keeps two letters apart; a zero-width joiner or tatweel joins
   them), lam + alef is drawn as the one lam-alef letter, and vowel marks sit over or under their
   letter. Lines run right to left, with English words and numbers inside them left to right: the
   Unicode bidirectional algorithm for a right-to-left paragraph without explicit embeddings (rules
   W1–W7, N1–N2, I2, L1, L2, and L4 for mirrored brackets), so the plotted text reads like the text
   box shows it. Units as in part45: letter height (alef) = 1, y down. */

const FA_FONT = 'PersianVazir';
const FA_LINE_PITCH = 2.2;          // baseline to baseline at line spacing 1: room for marks and the letters below the line
// [letter, isolated, final, initial, middle]: the presentation forms (letters that join only to the
// letter before them have two forms, hamza one).
const FA_FORM_LIST = [
  [0x0621, 0xFE80], [0x0622, 0xFE81, 0xFE82], [0x0623, 0xFE83, 0xFE84], [0x0624, 0xFE85, 0xFE86],
  [0x0625, 0xFE87, 0xFE88], [0x0626, 0xFE89, 0xFE8A, 0xFE8B, 0xFE8C], [0x0627, 0xFE8D, 0xFE8E],
  [0x0628, 0xFE8F, 0xFE90, 0xFE91, 0xFE92], [0x0629, 0xFE93, 0xFE94], [0x062A, 0xFE95, 0xFE96, 0xFE97, 0xFE98],
  [0x062B, 0xFE99, 0xFE9A, 0xFE9B, 0xFE9C], [0x062C, 0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0], [0x062D, 0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4],
  [0x062E, 0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8], [0x062F, 0xFEA9, 0xFEAA], [0x0630, 0xFEAB, 0xFEAC], [0x0631, 0xFEAD, 0xFEAE],
  [0x0632, 0xFEAF, 0xFEB0], [0x0633, 0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4], [0x0634, 0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8],
  [0x0635, 0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC], [0x0636, 0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0], [0x0637, 0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4],
  [0x0638, 0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8], [0x0639, 0xFEC9, 0xFECA, 0xFECB, 0xFECC], [0x063A, 0xFECD, 0xFECE, 0xFECF, 0xFED0],
  [0x0641, 0xFED1, 0xFED2, 0xFED3, 0xFED4], [0x0642, 0xFED5, 0xFED6, 0xFED7, 0xFED8], [0x0643, 0xFED9, 0xFEDA, 0xFEDB, 0xFEDC],
  [0x0644, 0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0], [0x0645, 0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4], [0x0646, 0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8],
  [0x0647, 0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC], [0x0648, 0xFEED, 0xFEEE], [0x0649, 0xFEEF, 0xFEF0, 0xFBE8, 0xFBE9],
  [0x064A, 0xFEF1, 0xFEF2, 0xFEF3, 0xFEF4], [0x0671, 0xFB50, 0xFB51], [0x067E, 0xFB56, 0xFB57, 0xFB58, 0xFB59],
  [0x0686, 0xFB7A, 0xFB7B, 0xFB7C, 0xFB7D], [0x0698, 0xFB8A, 0xFB8B], [0x06A9, 0xFB8E, 0xFB8F, 0xFB90, 0xFB91],
  [0x06AF, 0xFB92, 0xFB93, 0xFB94, 0xFB95], [0x06C0, 0xFBA4, 0xFBA5], [0x06CC, 0xFBFC, 0xFBFD, 0xFBFE, 0xFBFF],
  [0x06D2, 0xFBAE, 0xFBAF],
];
// Lam followed by one of these alefs is one letter: [alef, isolated lam-alef, final lam-alef].
const FA_LAM_ALEF = [[0x0622, 0xFEF5, 0xFEF6], [0x0623, 0xFEF7, 0xFEF8], [0x0625, 0xFEF9, 0xFEFA], [0x0627, 0xFEFB, 0xFEFC]];
const FA_MIRROR = { '(': ')', ')': '(', '[': ']', ']': '[', '{': '}', '}': '{', '<': '>', '>': '<', '«': '»', '»': '«', '‹': '›', '›': '‹' };
const FA_ZWNJ = '\u200C', FA_ZWJ = '\u200D';

const FA = (() => {
  const ch = c => (c ? String.fromCharCode(c) : '');
  const forms = new Map(), lamAlef = new Map();
  for (const [b, ...f] of FA_FORM_LIST) forms.set(ch(b), [0, 1, 2, 3].map(k => ch(f[k] || 0)));
  for (const [a, i, f] of FA_LAM_ALEF) lamAlef.set(ch(a), [ch(i), ch(f)]);
  return { forms, lamAlef };
})();

const faIsMark = ch => { const c = ch.charCodeAt(0); return (c >= 0x064B && c <= 0x065F) || c === 0x0670 || (c >= 0x0610 && c <= 0x061A) || (c >= 0x06D6 && c <= 0x06DC) || (c >= 0x06DF && c <= 0x06E4) || c === 0x06E7 || c === 0x06E8 || (c >= 0x06EA && c <= 0x06ED); };
const faMarkBelow = ch => { const c = ch.charCodeAt(0); return c === 0x0650 || c === 0x064D || c === 0x0655 || c === 0x0656 || c === 0x065C || c === 0x061A || c === 0x06E3 || c === 0x06ED; };
const faIsArabic = ch => { const c = ch.charCodeAt(0); return (c >= 0x0600 && c <= 0x06FF) || (c >= 0x0750 && c <= 0x077F) || (c >= 0xFB50 && c <= 0xFDFF) || (c >= 0xFE70 && c <= 0xFEFF); };

// How a character joins: D both sides, R only to the letter before it (alef, dal, reh, waw…),
// C joins both sides without being a letter (tatweel, zero-width joiner), T transparent (marks),
// U not at all (everything else, the zero-width non-joiner included).
function faJoining(ch) {
  if (ch === 'ـ' || ch === FA_ZWJ) return 'C';
  if (faIsMark(ch)) return 'T';
  const f = FA.forms.get(ch);
  return !f ? 'U' : f[2] ? 'D' : f[1] ? 'R' : 'U';
}

// Bidirectional character types (the ones that matter for Persian text with English and numbers in it).
function faBidiClass(ch) {
  const c = ch.codePointAt(0);
  if ((c >= 0x30 && c <= 0x39) || (c >= 0x06F0 && c <= 0x06F9) || c === 0xB2 || c === 0xB3 || c === 0xB9) return 'EN';
  if ((c >= 0x0660 && c <= 0x0669) || c === 0x066B || c === 0x066C || (c >= 0x0600 && c <= 0x0605) || c === 0x06DD) return 'AN';
  if (c === 0x2B || c === 0x2D || c === 0x2212) return 'ES';
  if (c === 0x23 || c === 0x24 || c === 0x25 || (c >= 0xA2 && c <= 0xA5) || c === 0xB0 || c === 0xB1 || c === 0x066A || c === 0x0609 || c === 0x060A || c === 0x2030 || c === 0x2031 || (c >= 0x20A0 && c <= 0x20CF)) return 'ET';
  if (c === 0x2C || c === 0x2E || c === 0x2F || c === 0x3A || c === 0xA0 || c === 0x060C || c === 0x202F) return 'CS';
  if (c === 0x20 || c === 0x09 || (c >= 0x2000 && c <= 0x200A)) return 'WS';
  if (faIsArabic(ch)) return faIsMark(ch) ? 'NSM' : (c === 0x06DE || c === 0x06E9) ? 'ON' : 'AL';
  if (/\p{M}/u.test(ch)) return 'NSM';
  return /\p{L}/u.test(ch) ? 'L' : 'ON';
}

const FA_BRACKETS = { '(': ')', '[': ']', '{': '}' };

// Bracket pairs of a line (BD16): [opening index, closing index], by opening position.
function faBracketPairs(chars) {
  const stack = [], pairs = [];
  const close = new Map(Object.entries(FA_BRACKETS).map(([o, c]) => [c, o]));
  for (let i = 0; i < chars.length; i++) {
    const c = chars[i];
    if (FA_BRACKETS[c]) { if (stack.length >= 63) break; stack.push([c, i]); continue; }
    if (!close.has(c)) continue;
    for (let k = stack.length - 1; k >= 0; k--) {
      if (stack[k][0] !== close.get(c)) continue;
      pairs.push([stack[k][1], i]); stack.length = k; break;
    }
  }
  return pairs.sort((a, b) => a[0] - b[0]);
}

// Embedding levels of one line in a right-to-left paragraph (1 = right to left, 2 = left to right).
// chars (optional): the characters, for bracket pairs (N0).
function faBidiLevels(types, chars) {
  const n = types.length, t = types.slice();
  for (let i = 0; i < n; i++) if (t[i] === 'NSM') t[i] = i ? t[i - 1] : 'R';                           // W1
  let strong = 'R';
  for (let i = 0; i < n; i++) {                                                                        // W2
    if (t[i] === 'L' || t[i] === 'R' || t[i] === 'AL') strong = t[i];
    else if (t[i] === 'EN' && strong === 'AL') t[i] = 'AN';
  }
  for (let i = 0; i < n; i++) if (t[i] === 'AL') t[i] = 'R';                                          // W3
  for (let i = 1; i < n - 1; i++) {                                                                    // W4
    if (t[i] === 'ES' && t[i - 1] === 'EN' && t[i + 1] === 'EN') t[i] = 'EN';
    else if (t[i] === 'CS' && (t[i - 1] === 'EN' || t[i - 1] === 'AN') && t[i + 1] === t[i - 1]) t[i] = t[i - 1];
  }
  for (let i = 0; i < n; i++) if (t[i] === 'ET') {                                                     // W5
    let j = i; while (j < n && t[j] === 'ET') j++;
    if ((i > 0 && t[i - 1] === 'EN') || (j < n && t[j] === 'EN')) for (let k = i; k < j; k++) t[k] = 'EN';
    i = j - 1;
  }
  for (let i = 0; i < n; i++) if (t[i] === 'ES' || t[i] === 'ET' || t[i] === 'CS') t[i] = 'ON';        // W6
  strong = 'R';
  for (let i = 0; i < n; i++) {                                                                        // W7
    if (t[i] === 'L' || t[i] === 'R') strong = t[i];
    else if (t[i] === 'EN' && strong === 'L') t[i] = 'L';
  }
  const dir = x => (x === 'L' ? 'L' : x === 'R' || x === 'EN' || x === 'AN' ? 'R' : null);
  if (chars) for (const [o, c] of faBracketPairs(chars)) {                                              // N0
    let inside = null;
    for (let k = o + 1; k < c && inside !== 'R'; k++) inside = dir(t[k]) || inside;
    if (!inside) continue;
    let d = 'R';
    if (inside === 'L') { let k = o - 1; while (k >= 0 && !dir(t[k])) k--; d = k >= 0 ? dir(t[k]) : 'R'; }
    t[o] = t[c] = d;
  }
  for (let i = 0; i < n; i++) if (!dir(t[i])) {                                                        // N1, N2
    let j = i; while (j < n && !dir(t[j])) j++;
    const a = i > 0 ? dir(t[i - 1]) : 'R', b = j < n ? dir(t[j]) : 'R', d = a === b ? a : 'R';
    for (let k = i; k < j; k++) t[k] = d;
    i = j - 1;
  }
  const lv = t.map(x => (x === 'R' ? 1 : 2));                                                          // I2
  for (let i = n - 1; i >= 0 && types[i] === 'WS'; i--) lv[i] = 1;                                     // L1
  return lv;
}

// Visual order (L2): reverse every run at level ≥ k, from the highest level down to 1.
function faReorder(items, levels) {
  const seq = items.map((it, i) => ({ it, lv: levels[i] }));
  const top = Math.max(1, ...levels);
  for (let k = top; k >= 1; k--) {
    for (let i = 0; i < seq.length;) {
      if (seq[i].lv < k) { i++; continue; }
      let j = i; while (j < seq.length && seq[j].lv >= k) j++;
      for (let a = i, b = j - 1; a < b; a++, b--) { const x = seq[a]; seq[a] = seq[b]; seq[b] = x; }
      i = j;
    }
  }
  return seq.map(s => s.it);
}

// What the user typed, ready to shape: composed (alef + madda → آ), letters pasted as presentation
// forms back to plain letters, and optionally 0–9 as Persian digits — except in English words (MP3).
function faPrepare(str, digits) {
  let s = String(str || '').normalize('NFC');
  s = s.replace(/[ﭐ-ﯿﺀ-ﻼ]/g, c => { const d = c.normalize('NFKC'); return d.length <= 2 ? d : c; });
  if (!digits || !/[0-9]/.test(s)) return s;
  const a = [...s], strong = c => { const b = /[0-9]/.test(c) ? '' : faBidiClass(c); return b === 'L' ? 'L' : b === 'AL' ? 'R' : null; };
  let before = null;
  for (let i = 0; i < a.length; i++) {
    const st = strong(a[i]);
    if (st) { before = st; continue; }
    if (!/[0-9]/.test(a[i])) continue;
    let j = i; while (j < a.length && /[0-9.,]/.test(a[j])) j++;
    let side = before;
    for (let k = j; k < a.length && !side; k++) side = strong(a[k]);
    if (side !== 'L') for (let k = i; k < j; k++) if (/[0-9]/.test(a[k])) a[k] = String.fromCharCode(0x06F0 + a[k].charCodeAt(0) - 48);
    i = j - 1;
  }
  return a.join('');
}

// One line, logical order → clusters: { ch (for the direction), glyph char or null, marks, joins to
// the next / previous letter in reading order }.
function faShapeLine(chars) {
  const n = chars.length, jt = chars.map(faJoining), prevJ = new Array(n), nextJ = new Array(n);
  let last = -1;
  for (let i = 0; i < n; i++) { prevJ[i] = last; if (jt[i] !== 'T') last = i; }
  last = -1;
  for (let i = n - 1; i >= 0; i--) { nextJ[i] = last; if (jt[i] !== 'T') last = i; }
  const toNext = i => jt[i] === 'D' || jt[i] === 'C', toPrev = i => jt[i] === 'D' || jt[i] === 'R' || jt[i] === 'C';
  const linkPrev = i => prevJ[i] >= 0 && toPrev(i) && toNext(prevJ[i]);
  const linkNext = i => nextJ[i] >= 0 && toNext(i) && toPrev(nextJ[i]);
  const out = [], eaten = new Set();
  for (let i = 0; i < n; i++) {
    const ch = chars[i];
    if (eaten.has(i)) continue;
    if (jt[i] === 'T') {                                     // a mark: on the letter before it
      const base = out[out.length - 1];
      if (base && !base.space) base.marks.push(ch); else out.push({ ch, glyph: ch, marks: [], jp: false, jn: false, mark: true });
      continue;
    }
    if (ch === FA_ZWNJ || ch === FA_ZWJ) continue;           // they only change how the neighbours join
    const f = FA.forms.get(ch), lp = linkPrev(i);
    if (ch === 'ل' && nextJ[i] >= 0 && FA.lamAlef.has(chars[nextJ[i]])) {
      eaten.add(nextJ[i]);
      out.push({ ch, glyph: FA.lamAlef.get(chars[nextJ[i]])[lp ? 1 : 0], marks: [], jp: lp, jn: false });
      continue;
    }
    if (f) {
      const ln = linkNext(i);
      out.push({ ch, glyph: (lp && ln ? f[3] : lp ? f[1] : ln ? f[2] : f[0]) || f[0], marks: [], jp: lp, jn: ln });
      continue;
    }
    if (ch === 'ـ') { out.push({ ch, glyph: ch, marks: [], jp: lp, jn: linkNext(i) }); continue; }
    out.push({ ch, glyph: null, marks: [], jp: false, jn: false, space: ch === ' ' || ch === '\t' });
  }
  return out;
}

// Marks over or under their letter: centred on it, clear of its top (or bottom) and of each other;
// shadda goes on first so a vowel sits on top of it.
function faMarkStrokes(G, base, marks, missing) {
  const b = base.box || { x0: 0, x1: base.adv, y0: -G.xh, y1: 0 };
  const cx = (b.x0 + b.x1) / 2, out = [];
  let top = b.y0, bottom = b.y1;
  const order = marks.slice().sort((p, q) => (q === '\u0651') - (p === '\u0651'));
  for (const m of order) {
    const g = G.map.get(m);
    if (!g || !g.box) { missing.add(m); continue; }
    const below = faMarkBelow(m), gap = 0.07, dx = cx - (g.box.x0 + g.box.x1) / 2;
    const dy = below ? bottom + gap - g.box.y0 : top - gap - g.box.y1;
    for (const s of g.strokes) out.push(s.map(p => ({ x: p.x + dx, y: p.y + dy })));
    if (below) bottom = g.box.y1 + dy; else top = g.box.y0 + dy;
  }
  return out;
}

// One line of Persian text → pen lines laid out left to right from x = 0 (cap heights, baseline y = 0).
// opts: { spaceAdv, sp (extra space between letters), digits (0–9 as Persian digits), missing (Set) }.
function faLayoutLine(G, line, opts = {}) {
  const sp = Number.isFinite(opts.sp) ? opts.sp : 0, spaceAdv = opts.spaceAdv || 0.3, missing = opts.missing || new Set();
  const cl = faShapeLine([...faPrepare(line, opts.digits)]);
  cl.forEach((c, i) => { c.idx = i; });
  const levels = faBidiLevels(cl.map(c => faBidiClass(c.ch)), cl.map(c => c.ch));
  cl.forEach((c, i) => { c.lv = levels[i]; });
  const vis = faReorder(cl, levels), join = (FONT_DATA[FA_FONT].join || 0) / FONT_CAP;
  const glyphs = [];
  let x = 0, chars = 0, prev = null;
  for (const c of vis) {
    let g = null;
    if (c.glyph) { const m = G.map.get(c.glyph) || G.map.get(c.ch); g = m ? { adv: m.adv, strokes: m.strokes, box: m.box } : null; }
    else { const ch = c.lv % 2 && FA_MIRROR[c.ch] ? FA_MIRROR[c.ch] : c.ch; g = textGlyph(G, ch, spaceAdv); if (g && !g.box) g.box = null; }
    if (prev) {
      const linked = prev.c.idx === c.idx + 1 && c.jn && prev.c.jp;     // this letter joins the one to its right
      if (linked && sp > 0) glyphs.push({ x: x - sp, strokes: [[{ x: 0, y: join }, { x: sp, y: join }]] });
    }
    if (!g) { missing.add(c.ch); glyphs.push({ x, strokes: [] }); x += spaceAdv + sp; prev = { c }; continue; }
    if (c.mark) g = { ...g, adv: Math.max(g.adv, (g.box ? g.box.x1 : 0) + 0.05) };      // a mark with no letter under it
    let strokes = g.strokes;
    if (c.marks.length) strokes = strokes.concat(faMarkStrokes(G, { adv: g.adv, box: g.box || boxOfStrokes(g.strokes) }, c.marks, missing));
    glyphs.push({ x, strokes });
    x += g.adv + sp; prev = { c };
    if (!c.space) chars++;
  }
  return { glyphs, width: glyphs.length ? x - sp : 0, chars };
}

function boxOfStrokes(strokes) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const s of strokes) for (const p of s) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; }
  return Number.isFinite(x0) ? { x0, y0, x1, y1 } : null;
}

// The Persian font and its made-up bold (italic is not used for Persian).
function faResolve(style) {
  return { file: FA_FONT, fakeBold: style === 'bold' || style === 'bolditalic', fakeItalic: false, family: { key: 'persian', name: 'Vazir (Persian)', files: { regular: FA_FONT } } };
}
