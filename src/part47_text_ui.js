/* ===================== PLOTTER: text =====================
   Text is an object on the paper like a drawing. The card shows the selected text and changes it as
   you type; with no text selected it holds the settings for the next "Add text" (remembered in this
   browser). Letter height is in millimetres; resizing text on the map changes it too. */
const TX = { tpl: { ...TEXT_DEFAULTS, angle: 0 }, timer: 0, built: false };
const $tx = id => document.getElementById(id);

function txLoad() {
  try {
    const v = JSON.parse(localStorage.getItem('magician-text') || 'null');
    if (v && typeof v === 'object') TX.tpl = { ...TX.tpl, ...v };
  } catch (e) {}
  if (!FONT_FAMILIES.some(f => f.key === TX.tpl.family)) TX.tpl.family = TEXT_DEFAULTS.family;
}
function txSave() { try { localStorage.setItem('magician-text', JSON.stringify(TX.tpl)); } catch (e) {} }

const selText = () => { const o = selObj(); return o && o.kind === 'text' ? o : null; };
function textSketch(lay) { const sk = prepareSketch(lay.strokes, null); sk.isText = true; return sk; }

// Lays the text out again with a change (text, font, style, letter height, alignment, spacing),
// keeping its start (the alignment point of the first line) where it is on the paper — or, when the
// alignment changes, its middle. Returns false if nothing drawable is left (the old lines stay).
function textApply(o, patch) {
  const t = { ...o.text, ...patch };
  const lay = textLayout(t);
  o.missing = lay.missing;
  o.text = t; o.label = textLabel(t.str);
  if (!lay.strokes.length) { o.textEmpty = true; return false; }
  o.textEmpty = false;
  const prev = o.sketch, pl = o.place, sk = textSketch(lay);
  const k = patch.height > 0 ? patch.height : pl.size / prev.srcBox.L, size = k * sk.srcBox.L;
  let cx = pl.cx, cy = pl.cy;
  if (!('align' in patch)) {
    const lin = placeLinear(pl.angle, pl.mirror);
    const uo = lin({ x: -prev.srcBox.cx / prev.srcBox.L, y: -prev.srcBox.cy / prev.srcBox.L });
    const un = lin({ x: -sk.srcBox.cx / sk.srcBox.L, y: -sk.srcBox.cy / sk.srcBox.L });
    const ax = pl.cx + pl.size * uo.x, ay = pl.cy + pl.size * uo.y;
    cx = ax - size * un.x; cy = ay - size * un.y;
  }
  o.sketch = sk; resetObjCaches(o);
  setPlaceFor(o, { ...pl, cx, cy, size });
  return true;
}
// After a resize: made-up bold keeps its second line 0.35 mm to the side at the new size.
function textRelayout(o) {
  if (o && o.kind === 'text' && fontResolve(o.text.family, o.text.style).fakeBold) textApply(o, { height: o.text.height });
}

// The fields → text settings.
function txFields() {
  const num = (id, d) => { const v = parseFloat($tx(id).value); return Number.isFinite(v) ? v : d; };
  return {
    str: $tx('tx-text').value,
    family: TX.tpl.family,
    style: $tx('tx-style').value,
    height: Math.min(200, Math.max(1, num('tx-height', TX.tpl.height))),
    angle: normAngle(num('tx-rot', 0)),
    align: $tx('tx-align').value,
    spacing: Math.min(2, Math.max(-0.3, num('tx-spacing', 0) / 100)),
    lineGap: Math.min(4, Math.max(0.5, num('tx-lines', 1))),
  };
}

function txInfo() {
  const o = selText(), t = o ? o.text : TX.tpl, fr = fontResolve(t.family, t.style), bits = [];
  const missing = o ? o.missing || [] : textLayout(t).missing;
  if (o) bits.push(o.textEmpty ? 'Type some text — the selected text is empty, so its old lines are kept.' : `Editing “${o.label}” — changes show on the map straight away. Add text makes another one.`);
  else bits.push(selObj() ? 'Add text puts new text on the paper (the selected object is a drawing).' : 'Type, choose a font, then Add text. Click text on the map to change it later.');
  if (fr.fakeBold || fr.fakeItalic) bits.push(`${fr.family.name} has no ${[fr.fakeBold && 'bold', fr.fakeItalic && 'italic'].filter(Boolean).join(' or ')} letters, so ${[fr.fakeBold && 'bold adds a second pen line beside each line', fr.fakeItalic && 'italic slants the letters'].filter(Boolean).join(' and ')}.`);
  if (missing.length) bits.push(`Not in this font (left out): ${missing.slice(0, 12).join(' ')}${missing.length > 12 ? ' …' : ''}`);
  $tx('tx-info').textContent = bits.join(' ');
  $tx('tx-info').style.color = missing.length || (o && o.textEmpty) ? 'var(--warn)' : '';
}

function txMarkFont(key) {
  document.querySelectorAll('#tx-fonts .tx-font').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.key === key)));
}

// Fields show the selected text, or the settings for new text.
function syncTextUI() {
  const o = selText(), t = o ? o.text : TX.tpl;
  const set = (id, v) => { const el = $tx(id); if (document.activeElement !== el && !el.dataset.typing) el.value = v; };
  set('tx-text', t.str);
  set('tx-style', t.style);
  set('tx-height', +(+t.height).toFixed(1));
  set('tx-rot', o ? +o.place.angle.toFixed(1) : +(t.angle || 0).toFixed(1));
  set('tx-align', t.align);
  set('tx-spacing', Math.round((t.spacing || 0) * 100));
  set('tx-lines', +(t.lineGap || 1).toFixed(2));
  txMarkFont(t.family);
  $tx('btnTextAdd').disabled = S.running;
  $tx('textCard').classList.toggle('editing', !!o);
  $tx('tx-mode').textContent = o ? `editing ${o.label}` : 'new text';
  txInfo();
}

// A field changed: the selected text follows it (letters laid out again shortly after typing stops).
function txChanged(patch, delay = 0) {
  const o = selText();
  TX.tpl = { ...TX.tpl, ...patch };
  txSave();
  if (!o || S.running) { txInfo(); txMarkFont(TX.tpl.family); return; }
  clearTimeout(TX.timer);
  const run = () => {
    const tpatch = { ...patch }; delete tpatch.angle;
    if (Object.keys(tpatch).length) textApply(o, tpatch);
    if ('angle' in patch) applyWant({ ...o.place, angle: normAngle(patch.angle) });
    buildPlot({ quiet: true });
    if (typeof renderObjectList === 'function') renderObjectList();
    txInfo(); txMarkFont(o.text.family);
  };
  if (delay) TX.timer = setTimeout(run, delay); else run();
}

function addText() {
  if (S.running) return;
  const t = txFields();
  if (!String(t.str).trim()) { $tx('tx-text').focus(); return log('Type some text first.', 'warn'); }
  const lay = textLayout(t);
  if (!lay.strokes.length) return log(`None of these characters are in ${fontFamily(t.family).name}.`, 'warn');
  TX.tpl = { ...TX.tpl, ...t }; txSave();
  const o = newObject('text', textSketch(lay), textLabel(t.str), { text: { ...t }, missing: lay.missing });
  addObject(o);
  if (o.text.height < t.height - 0.05) log(`Text made smaller (${o.text.height.toFixed(1)} mm letters) so it fits in the green zone.`, 'warn');
  log(`Text added: “${o.label}” in ${fontFamily(t.family).name}, ${o.text.height.toFixed(1)} mm letters.${lay.missing.length ? ' Left out (not in this font): ' + lay.missing.join(' ') : ''}`, 'ok');
}

// Font buttons, each showing its name in its own letters.
function txBuildFonts() {
  if (TX.built) return;
  TX.built = true;
  const box = $tx('tx-fonts'), frag = document.createDocumentFragment();
  for (const f of FONT_FAMILIES) {
    const lay = textLayout({ str: f.name.replace(/ \(.*\)$/, ''), family: f.key, style: 'regular', align: 'left' });
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const s of lay.strokes) for (const p of s) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
    const d = lay.strokes.map(s => 'M' + s.map(p => `${(p.x * 100).toFixed(0)} ${(p.y * 100).toFixed(0)}`).join('L')).join('');
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'tx-font'; b.dataset.key = f.key;
    b.title = `${f.name} — styles: ${Object.keys(f.files).map(k => (TEXT_STYLES.find(s => s[0] === k) || [0, k])[1].toLowerCase()).join(', ')}`;
    b.setAttribute('aria-label', f.name);
    const pad = 12, vb = `${(x0 * 100 - pad).toFixed(0)} ${(y0 * 100 - pad).toFixed(0)} ${((x1 - x0) * 100 + 2 * pad).toFixed(0)} ${((y1 - y0) * 100 + 2 * pad).toFixed(0)}`;
    b.innerHTML = `<svg viewBox="${vb}" aria-hidden="true" preserveAspectRatio="xMidYMid meet"><path d="${d}"/></svg>`;
    b.onclick = () => txChanged({ family: f.key });
    frag.appendChild(b);
  }
  box.appendChild(frag);
  const sel = $tx('tx-style');
  for (const [k, name] of TEXT_STYLES) { const op = document.createElement('option'); op.value = k; op.textContent = name; sel.appendChild(op); }
}

function txCredits() {
  const box = $tx('tx-credit-body');
  if (box.childElementCount) return;
  const add = (tag, text, cls) => { const el = document.createElement(tag); el.textContent = text; if (cls) el.className = cls; box.appendChild(el); return el; };
  add('p', 'Hershey fonts (Sans, Serif, Script, the three Gothic fonts): the Hershey Fonts were originally created by Dr. A. V. Hershey while working at the U. S. National Bureau of Standards. The format of the Font data in this distribution was originally created by James Hurt, Cognition, Inc., 900 Technology Park Drive, Billerica, MA 01821. SVG versions by Windell H. Oskay (Evil Mad Scientist Laboratories) and James T (hersheytext, MIT licence). The notice that comes with them:');
  add('pre', FONT_CREDITS.hershey, 'tx-lic');
  add('p', 'EMS fonts (Readability, Nixish, Tech, Osmotron, Felix, Allure, Elfin): single-line versions of open fonts, licensed under the SIL Open Font License 1.1. Converted here to pen lines (coordinates rounded) — that copy is under the same licence.');
  for (const [k, meta] of Object.entries(FONT_CREDITS.ems)) add('pre', meta, 'tx-lic');
  add('pre', FONT_CREDITS.ofl, 'tx-lic');
}

/* ----- wiring ----- */
$tx('tx-text').addEventListener('input', () => txChanged({ str: $tx('tx-text').value }, 160));
$tx('tx-style').onchange = () => txChanged({ style: $tx('tx-style').value });
$tx('tx-align').onchange = () => txChanged({ align: $tx('tx-align').value });
for (const [id, key, conv, lo, hi, msg] of [
  ['tx-height', 'height', v => v, 1, 200, 'Letter height must be between 1 and 200 mm.'],
  ['tx-rot', 'angle', v => normAngle(v), -360, 360, 'Rotation must be a number of degrees.'],
  ['tx-spacing', 'spacing', v => v / 100, -30, 200, 'Letter spacing must be between −30 and 200 %.'],
  ['tx-lines', 'lineGap', v => v, 0.5, 4, 'Line spacing must be between 0.5 and 4.'],
]) {
  const el = $tx(id);
  el.addEventListener('input', () => { el.dataset.typing = '1'; });
  el.addEventListener('change', () => {
    delete el.dataset.typing;
    const v = parseFloat(el.value);
    if (!(v >= lo && v <= hi)) { log(msg, 'warn'); syncTextUI(); return; }
    txChanged({ [key]: conv(v) });
  });
  el.addEventListener('blur', () => { delete el.dataset.typing; });
}
$tx('btnTextAdd').onclick = addText;
$tx('tx-credits').addEventListener('toggle', ev => { if (ev.target.open) txCredits(); });

txLoad();
txBuildFonts();
syncTextUI();
