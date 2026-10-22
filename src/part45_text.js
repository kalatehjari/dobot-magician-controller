/* ===================== TEXT TO PEN LINES (pure, unit-tested) =====================
   Lays out text in the single-line fonts of part44 (FONT_DATA). Units: cap height = 1, x right,
   y down; the origin is the first line's baseline at the alignment point (left end, middle or right
   end), so editing text keeps that point where it is on the paper. */

// Font families and the font file used for each style. Styles a family has no file for are made
// from the regular one: italic by slanting it 12°, bold by drawing every line a second time a
// little to the side.
const FONT_FAMILIES = [
  { key: 'sans', name: 'Sans', files: { regular: 'HersheySans1', bold: 'HersheySansMed' } },
  { key: 'serif', name: 'Serif', files: { regular: 'HersheySerifMed', italic: 'HersheySerifMedItalic', bold: 'HersheySerifBold', bolditalic: 'HersheySerifBoldItalic' } },
  { key: 'script', name: 'Script', files: { regular: 'HersheyScript1', bold: 'HersheyScriptMed' }, slanted: true },
  { key: 'readability', name: 'Readability', files: { regular: 'EMSReadability', italic: 'EMSReadabilityItalic' } },
  { key: 'nixish', name: 'Nixish', files: { regular: 'EMSNixish', italic: 'EMSNixishItalic' } },
  { key: 'tech', name: 'Tech', files: { regular: 'EMSTech' } },
  { key: 'osmotron', name: 'Osmotron', files: { regular: 'EMSOsmotron' } },
  { key: 'felix', name: 'Felix', files: { regular: 'EMSFelix' } },
  { key: 'allure', name: 'Allure (handwriting)', files: { regular: 'EMSAllure' }, slanted: true },
  { key: 'elfin', name: 'Elfin', files: { regular: 'EMSElfin' } },
  { key: 'gothic', name: 'Gothic English', files: { regular: 'HersheyGothEnglish' } },
  { key: 'gothicde', name: 'Gothic German', files: { regular: 'gothicger' } },
  { key: 'gothicit', name: 'Gothic Italian', files: { regular: 'gothicita' } },
];
const TEXT_STYLES = [['regular', 'Regular'], ['bold', 'Bold'], ['italic', 'Italic'], ['bolditalic', 'Bold italic']];
const TEXT_DEFAULTS = { str: 'Hello', family: 'sans', style: 'regular', height: 10, align: 'center', spacing: 0, lineGap: 1 };
const TEXT_SLANT = 12;              // degrees, for made-up italics
const TEXT_BOLD_MM = 0.35;          // second pen line this far to the side, for made-up bold
const TEXT_LINE_PITCH = 1.6;        // baseline to baseline at line spacing 1, in cap heights

const _B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const _B64V = (() => { const m = new Int8Array(128).fill(-1); for (let i = 0; i < 64; i++) m[_B64.charCodeAt(i)] = i; return m; })();
const _FONT_CACHE = new Map();

// Glyphs of one font file: char → { adv, strokes: [[{x, y}…]…], box }, in cap heights.
function fontGlyphs(file) {
  if (_FONT_CACHE.has(file)) return _FONT_CACHE.get(file);
  const f = FONT_DATA[file];
  if (!f) throw new Error('Unknown font ' + file);
  const s = f.data, out = new Map(), k = 1 / FONT_CAP;
  let i = 0;
  const vint = () => {
    let v = 0, sh = 0, d;
    do { d = _B64V[s.charCodeAt(i++)]; if (d < 0 || d === undefined) throw new Error('Bad font data'); v += (d & 31) * 2 ** sh; sh += 5; } while (d & 32);
    return v;
  };
  const zz = v => (v % 2 ? -(v + 1) / 2 : v / 2);
  while (i < s.length) {
    const ch = s[i++], adv = vint() * k, n = vint(), strokes = [];
    let x = 0, y = 0, x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (let j = 0; j < n; j++) {
      const m = vint(), pts = [];
      for (let q = 0; q < m; q++) {
        x += zz(vint()); y += zz(vint());
        const p = { x: x * k, y: y * k };
        pts.push(p);
        if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y;
      }
      strokes.push(pts);
    }
    out.set(ch, { adv, strokes, box: strokes.length ? { x0, y0, x1, y1 } : null });
  }
  const g = { map: out, xh: (f.x || FONT_CAP * 0.67) * k, name: f.name };
  _FONT_CACHE.set(file, g);
  return g;
}

function fontFamily(key) { return FONT_FAMILIES.find(f => f.key === key) || FONT_FAMILIES[0]; }

// Font file and made-up effects for a family and style.
function fontResolve(familyKey, style) {
  const fam = fontFamily(familyKey), F = fam.files;
  const wantB = style === 'bold' || style === 'bolditalic', wantI = style === 'italic' || style === 'bolditalic';
  let file = F[style], fakeB = false, fakeI = false;
  if (!file) {
    if (wantB && wantI) {
      if (F.bold) { file = F.bold; fakeI = true; }
      else if (F.italic) { file = F.italic; fakeB = true; }
      else { file = F.regular; fakeB = fakeI = true; }
    } else if (wantB) { file = F.regular; fakeB = true; }
    else if (wantI) { file = F.regular; fakeI = true; }
    else file = F.regular;
  }
  return { file, fakeBold: fakeB, fakeItalic: fakeI, family: fam };
}

// Typographic characters the fonts lack, drawn with ones they have.
const TEXT_SUBST = { '‘': "'", '’': "'", '‚': ',', '′': "'", '″': '"', '„': '"', '…': '...', '−': '-', '‐': '-', '‑': '-', '‒': '-', ' ': ' ', ' ': ' ', ' ': ' ', '•': '·', 'ı': 'i', '“': '"', '”': '"', '«': '<<', '»': '>>', '‹': '<', '›': '>', '–': '-', '—': '--', 'Đ': 'Ð' };
// Letters with a bar or slash through them, drawn as the plain letter plus that line.
const TEXT_STROKED = { 'ł': ['l', 'slash'], 'Ł': ['L', 'slash'], 'đ': ['d', 'bar'], 'ħ': ['h', 'bar'], 'Ħ': ['H', 'bar'], 'ŧ': ['t', 'mid'], 'Ŧ': ['T', 'mid'], 'ƶ': ['z', 'mid'], 'Ƶ': ['Z', 'mid'], 'Ø': ['O', 'diag'], 'ø': ['o', 'diag'] };

// Accents for letters a font does not have (ā, ł…): the base letter with the mark drawn on.
function _markStrokes(mark, cx, top, bottom, upper) {
  const w = 0.32, h = 0.13, gap = upper ? 0.1 : 0.12, y1 = top - gap, y0 = y1 - h, d = 0.035;
  const dot = (x, y) => [{ x: x - d, y }, { x: x + d, y }, { x, y: y - d }, { x, y: y + d }, { x: x - d, y }];
  switch (mark) {
    case 0x0304: case 0x0305: return [[{ x: cx - w / 2, y: y1 - h / 2 }, { x: cx + w / 2, y: y1 - h / 2 }]];        // macron
    case 0x0301: return [[{ x: cx - 0.06, y: y1 }, { x: cx + 0.09, y: y0 }]];                                         // acute
    case 0x0300: return [[{ x: cx + 0.06, y: y1 }, { x: cx - 0.09, y: y0 }]];                                         // grave
    case 0x030B: return [[{ x: cx - 0.13, y: y1 }, { x: cx - 0.01, y: y0 }], [{ x: cx + 0.04, y: y1 }, { x: cx + 0.16, y: y0 }]];
    case 0x0302: return [[{ x: cx - 0.14, y: y1 }, { x: cx, y: y0 }, { x: cx + 0.14, y: y1 }]];                     // circumflex
    case 0x030C: return [[{ x: cx - 0.14, y: y0 }, { x: cx, y: y1 }, { x: cx + 0.14, y: y0 }]];                     // caron
    case 0x0306: { const a = []; for (let i = 0; i <= 8; i++) { const t = Math.PI * i / 8; a.push({ x: cx - 0.14 * Math.cos(t), y: y0 + h * Math.sin(t) }); } return [a]; }   // breve
    case 0x0303: { const a = []; for (let i = 0; i <= 12; i++) { const t = i / 12; a.push({ x: cx - w / 2 + w * t, y: y1 - h / 2 - 0.05 * Math.sin(t * 2 * Math.PI) }); } return [a]; }   // tilde
    case 0x0308: return [dot(cx - 0.11, y1 - 0.05), dot(cx + 0.11, y1 - 0.05)];                                      // diaeresis
    case 0x0307: return [dot(cx, y1 - 0.05)];                                                                        // dot above
    case 0x030A: { const a = []; for (let i = 0; i <= 12; i++) { const t = 2 * Math.PI * i / 12; a.push({ x: cx + 0.07 * Math.cos(t), y: y1 - 0.08 + 0.07 * Math.sin(t) }); } return [a]; }   // ring
    case 0x0327: return [[{ x: cx, y: bottom }, { x: cx + 0.02, y: bottom + 0.1 }, { x: cx + 0.1, y: bottom + 0.14 }, { x: cx + 0.06, y: bottom + 0.23 }, { x: cx - 0.06, y: bottom + 0.24 }]];   // cedilla
    case 0x0328: return [[{ x: cx + 0.08, y: bottom }, { x: cx - 0.02, y: bottom + 0.12 }, { x: cx + 0.03, y: bottom + 0.22 }, { x: cx + 0.13, y: bottom + 0.21 }]];   // ogonek
    case 0x0323: return [dot(cx, bottom + 0.12)];                                                                    // dot below
    case 0x0331: return [[{ x: cx - w / 2, y: bottom + 0.14 }, { x: cx + w / 2, y: bottom + 0.14 }]];               // macron below
    default: return null;
  }
}

// Several characters drawn one after another as one (… → ..., ﬁ → fi).
function _stringGlyph(G, str, spaceAdv) {
  let x = 0; const strokes = [];
  for (const c of str) {
    const p = textGlyph(G, c, spaceAdv);
    if (!p) return null;
    for (const s of p.strokes) strokes.push(s.map(q => ({ x: q.x + x, y: q.y })));
    x += p.adv;
  }
  return { adv: x, strokes };
}

// One character: its pen lines (cap heights, origin on the baseline at its left edge) and advance.
function textGlyph(G, ch, spaceAdv) {
  if (ch === ' ' || ch === '\t') { const g = G.map.get(' '); return { adv: (g ? g.adv : spaceAdv) * (ch === '\t' ? 4 : 1), strokes: [] }; }
  const g = G.map.get(ch);
  if (g) return { adv: g.adv, strokes: g.strokes };
  const sub = TEXT_SUBST[ch];
  if (sub !== undefined && sub !== ch) { const r = _stringGlyph(G, sub, spaceAdv); if (r) return r; }
  const sk = TEXT_STROKED[ch];
  if (sk && G.map.has(sk[0])) {
    const base = G.map.get(sk[0]), b = base.box || { x0: 0, x1: base.adv, y0: -1, y1: 0 }, cx = (b.x0 + b.x1) / 2;
    const line = sk[1] === 'diag' ? [{ x: b.x0 - 0.04, y: b.y1 + 0.04 }, { x: b.x1 + 0.04, y: b.y0 - 0.04 }]
      : sk[1] === 'slash' ? [{ x: cx - 0.16, y: -0.3 }, { x: cx + 0.16, y: -0.62 }]
      : sk[1] === 'bar' ? [{ x: cx - 0.13, y: -0.78 }, { x: cx + 0.17, y: -0.78 }] : [{ x: cx - 0.16, y: (b.y0 + b.y1) / 2 }, { x: cx + 0.16, y: (b.y0 + b.y1) / 2 }];
    return { adv: base.adv, strokes: base.strokes.concat([line]) };
  }
  const nfd = ch.normalize('NFD');
  if (nfd.length > 1 && G.map.has(nfd[0])) {
    const b0 = nfd[0], base = G.map.get(b0), upper = b0 !== b0.toLowerCase();
    const marks = [...nfd.slice(1)].map(c => c.charCodeAt(0)), above = marks.some(m => m !== 0x0327 && m !== 0x0328 && m !== 0x0323 && m !== 0x0331);
    let strokes = base.strokes;
    if ((b0 === 'i' || b0 === 'j') && above) strokes = strokes.filter(s => !s.every(p => p.y < -G.xh * 1.02));   // ī: no dot under the macron
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity;
    for (const s of strokes) for (const p of s) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; }
    if (!Number.isFinite(x0)) { x0 = 0; x1 = base.adv; y0 = -G.xh; }
    let sx = 0, n = 0;                                    // middle of the top of the letter (follows a slant)
    for (const s of strokes) for (const p of s) if (p.y <= y0 + 0.25 * (0 - y0)) { sx += p.x; n++; }
    const cxTop = n ? sx / n : (x0 + x1) / 2, cxBot = (x0 + x1) / 2, top = Math.min(y0, upper ? -1 : -G.xh);
    const out = strokes.slice();
    for (const m of marks) {
      const below = m === 0x0327 || m === 0x0328 || m === 0x0323 || m === 0x0331;
      const ms = _markStrokes(m, below ? cxBot : cxTop, top, 0, upper);
      if (!ms) return null;
      out.push(...ms);
    }
    return { adv: base.adv, strokes: out };
  }
  const nfkd = ch.normalize('NFKD');
  if (nfkd !== ch) return _stringGlyph(G, nfkd, spaceAdv);
  return null;
}

// Text → pen lines. p: { str, family, style, height (mm; for made-up bold), align, spacing (extra
// space between letters, cap heights), lineGap (line spacing, 1 = normal) }.
function textLayout(p) {
  const st = { ...TEXT_DEFAULTS, ...p };
  const fr = fontResolve(st.family, st.style), G = fontGlyphs(fr.file);
  const spaceAdv = 0.3, lines = String(st.str || '').replace(/\r\n?/g, '\n').split('\n');
  const pitch = TEXT_LINE_PITCH * (st.lineGap > 0 ? st.lineGap : 1), sp = Number.isFinite(st.spacing) ? st.spacing : 0;
  const slant = fr.fakeItalic ? Math.tan(TEXT_SLANT * Math.PI / 180) : 0;
  const strokes = [], missing = new Set(), widths = [];
  let chars = 0;
  lines.forEach((line, li) => {
    const glyphs = [];
    let x = 0;
    for (const ch of line) {
      const g = textGlyph(G, ch, spaceAdv);
      if (!g) { missing.add(ch); glyphs.push({ x, strokes: [] }); x += spaceAdv + sp; continue; }
      glyphs.push({ x, strokes: g.strokes });
      x += g.adv + sp; chars++;
    }
    const w = glyphs.length ? x - sp : 0;
    widths.push(w);
    const x0 = st.align === 'left' ? 0 : st.align === 'right' ? -w : -w / 2, yb = li * pitch;
    for (const g of glyphs) for (const s of g.strokes) {
      strokes.push(s.map(q => ({ x: x0 + g.x + q.x - slant * q.y, y: yb + q.y })));
    }
  });
  if (fr.fakeBold && strokes.length) {
    const h = st.height > 0 ? st.height : 10, d = Math.min(0.12, Math.max(0.002, TEXT_BOLD_MM / h)) / Math.SQRT2;   // 0.35 mm, less only for tiny letters
    const n = strokes.length;
    for (let i = 0; i < n; i++) strokes.push(strokes[i].map(q => ({ x: q.x + d, y: q.y - d })));
  }
  return { strokes, missing: [...missing], lines: lines.length, chars, width: Math.max(0, ...widths), pitch, font: fr };
}

// A label for the object list: the first line, shortened.
function textLabel(str) {
  const s = String(str || '').split(/\r?\n/).find(l => l.trim()) || '';
  const t = s.trim();
  return t ? (t.length > 24 ? t.slice(0, 23) + '…' : t) : 'Text';
}
