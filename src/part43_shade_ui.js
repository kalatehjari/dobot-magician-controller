/* ===================== PLOTTER: shading controls =====================
   Every object on the paper has its own shading settings (o.shade); the card shows and changes the
   selected object's. A new drawing starts with the settings used last (remembered in this browser),
   text starts unshaded. Hatch lines are worked out in the object's own units for its size on the
   paper, so moving or turning it is instant; resizing recomputes them so the spacing stays the same
   in millimetres. A click on a shape of the selected object gives that shape its own shading. */
const SH = { last: { ...SHADE_DEFAULTS }, press: null, flash: null, timer: 0 };
// The selected object's shading (older code and the tests read these).
Object.defineProperties(SH, {
  st: { get() { const o = selObj(); return o ? o.shade : SH.last; } },
  ov: { get() { const o = selObj(); return o ? o.shOv : new Map(); } },
  cache: { get() { const o = selObj(); return o ? o.shCache : null; } },
  targets: { get() { const o = selObj(); return o ? o.shT : null; } },
});
const $sh = id => document.getElementById(id);

function shadeLoad() {
  try { const v = JSON.parse(localStorage.getItem('magician-shade') || 'null'); if (v && typeof v === 'object') SH.last = { ...SHADE_DEFAULTS, ...v }; } catch (e) {}
}
function shadeSave() { try { localStorage.setItem('magician-shade', JSON.stringify(SH.last)); } catch (e) {} }

// Shading state of a new object.
function shadeInit(o) {
  o.shade = { ...SH.last, ...(o.kind === 'text' ? { pattern: 'off' } : {}) };
  o.shOv = new Map(); o.shOvVer = 0; o.shT = null; o.shTkey = ''; o.shCache = null;
}
// A copy keeps the shading and the shapes set by hand.
function shadeCopy(from, to) {
  to.shade = { ...from.shade }; to.shOv = new Map(from.shOv); to.shOvVer = from.shOvVer;
  to.shT = from.shT; to.shTkey = from.shTkey; to.shCache = from.shCache;
}
const shadeOn = (o = selObj()) => !!o && o.shade.pattern !== 'off';

// Shading targets of an object (cached); shapes set by hand belong to one drawing and one mode.
function shadeTargetsFor(o) {
  const key = `${o.sketch.id}|${o.shade.which}`;
  if (o.shTkey !== key) {
    o.shT = shadeTargets(o.sketch, o.shade.which);
    if (o.shTkey && o.shOv.size) { o.shOv = new Map(); o.shOvVer++; }   // not on the first look (a layout just opened keeps them)
    o.shTkey = key;
  }
  return o.shT;
}

// Hatch lines for an object at `size` mm (cached); null when its shading is off.
function shadeFor(o, size) {
  if (!shadeOn(o)) return null;
  const T = shadeTargetsFor(o), ovs = [...o.shOv].map(([i, v]) => `${i}:${v}`).join(',');
  const key = `${o.shTkey}|${JSON.stringify(o.shade)}|${size.toFixed(2)}|${ovs}`;
  if (!o.shCache || o.shCache.key !== key) {
    const t0 = performance.now(), r = shadeDrawing(T, o.shade, size, o.shOv);
    o.shCache = { key, ...r, ms: performance.now() - t0, size };
  }
  return o.shCache;
}

function shadeDescribe(o, i) {
  const a = shadeAngles(i, o.shade, o.shOv.get(i) || 'auto');
  if (!a.length) return 'no shading';
  return a.length === 1 ? `lines at ${Math.round(a[0])}°` : `${a.length === 2 ? 'cross-hatched' : 'three directions'} (${a.map(v => Math.round(v) + '°').join(', ')})`;
}

function renderShadeStats() {
  const el = $sh('sh-stats'), o = selObj();
  $sh('btnShadeReset').disabled = !o || !o.shOv.size;
  $sh('btnShadeSvg').disabled = !o;
  if (!o) { el.textContent = S.plot.objects.length ? 'Select a drawing on the map (or in the list) to shade it.' : 'Load a drawing to shade its closed shapes.'; return; }
  if (!shadeOn(o)) { el.textContent = `Shading is off for ${o.label} — only its lines are drawn.`; return; }
  const c = shadeFor(o, o.place.size);
  if (!c.targets) { el.textContent = `${o.label} has no closed shapes to shade (only open lines).`; return; }
  const what = c.mode === 'filled' ? 'filled shapes' : 'closed shapes';
  const vd = S.speed.draw || 30;
  el.textContent = `${o.label}: ${c.shaded} of ${c.targets} ${what} shaded · ${c.lines} lines in ${c.strokes.length} pen strokes · ${(c.length / 1000).toFixed(2)} m of line (about ${(c.length / vd / 60).toFixed(1)} min at ${vd} mm/s)` +
    (o.shOv.size ? ` · ${o.shOv.size} shape${o.shOv.size > 1 ? 's' : ''} set by hand` : '') +
    (c.fallback ? ' · this drawing has no filled shapes, so every closed shape is used' : '');
}

function syncShadeUI(stats = true) {
  const o = selObj(), st = o ? o.shade : SH.last, on = !!o && st.pattern !== 'off';
  $sh('sh-pattern').value = st.pattern;
  $sh('sh-pattern').disabled = !o || S.running;
  for (const id of ['sh-angle', 'sh-angleNum']) if (!$sh(id).dataset.typing) $sh(id).value = Math.round(st.angle);
  $sh('sh-angleVal').textContent = `${Math.round(st.angle)}°`;
  $sh('sh-spacing').value = st.spacing; $sh('sh-vary').value = st.vary; $sh('sh-which').value = st.which;
  $sh('sh-tone').checked = !!st.tone; $sh('sh-outline').checked = st.outline !== false; $sh('sh-join').checked = st.join !== false;
  $sh('sh-inset').value = st.inset;
  for (const id of ['sh-angle', 'sh-angleNum', 'sh-spacing', 'sh-vary', 'sh-which', 'sh-outline', 'sh-join', 'sh-inset']) $sh(id).disabled = !on;
  document.querySelectorAll('#shadeCard .sh-quick').forEach(b => { b.disabled = !on; b.setAttribute('aria-pressed', String(on && Math.round(st.angle) === +b.dataset.a)); });
  $sh('sh-tone').disabled = !on || st.which !== 'filled';
  $sh('btnShadeRandom').disabled = !on || st.vary !== 'random';
  $sh('sh-for').textContent = o ? `for ${o.label}` : '';
  if (stats) renderShadeStats();
}

// A setting changed: the selected object gets it (and it is remembered for new drawings), then the
// path is rebuilt (straight away, or shortly after while a slider moves).
function shadeSet(patch, delay = 0) {
  const o = selObj();
  if (!o) { syncShadeUI(); return; }
  o.shade = { ...o.shade, ...patch };
  SH.last = { ...o.shade };
  shadeSave();
  clearTimeout(SH.timer);
  const build = !S.running;
  syncShadeUI(!build);                                   // the stats follow the rebuild
  if (!build) return;
  if (delay) SH.timer = setTimeout(() => buildPlot(), delay); else buildPlot();
}

// While an object is being dragged, its last hatch lines move with it (exact again on release).
function shadePreview(ctx, v, o, color) {
  const c = o.shCache;
  if (!shadeOn(o) || !c || !c.key.startsWith(`${o.sketch.id}|`)) return;
  const f = placeXform(o.place);
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = 0.8; ctx.globalAlpha = 0.6; ctx.beginPath();
  for (const s of c.strokes) s.forEach((p, i) => { const q = f(p), [x, y] = v.toS(q.x, q.y); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.stroke(); ctx.restore();
}

// The shape just clicked lights up for a moment.
function shadeOverlay(ctx, v) {
  const fl = SH.flash, o = selObj();
  if (!fl || !o || o.id !== fl.id || performance.now() > fl.until || !o.shT || !o.shT.list[fl.i]) return;
  const f = placeXform(o.place);
  ctx.save(); ctx.strokeStyle = cssVar('--accent'); ctx.lineWidth = 3; ctx.globalAlpha = 0.75; ctx.lineJoin = 'round'; ctx.beginPath();
  for (const r of o.shT.list[fl.i].rings) { r.forEach((p, i) => { const q = f(p), [x, y] = v.toS(q.x, q.y); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.closePath(); }
  ctx.stroke(); ctx.restore();
}

// The selected object as it will be plotted (lines and shading), as an SVG at its size on the paper.
function shadeSvgText(o = selObj()) {
  const sk = o.sketch, pl = o.place, c = shadeFor(o, pl.size), outl = !c || o.shade.outline ? sk.strokes : [];
  const W = sk.w * pl.size, H = sk.h * pl.size, mm = p => `${((p.x + sk.w / 2) * pl.size).toFixed(2)} ${((p.y + sk.h / 2) * pl.size).toFixed(2)}`;
  const d = list => list.filter(s => s.length > 1).map(s => 'M' + s.map(mm).join(' L')).join('');
  const esc = s => String(s || 'drawing').replace(/[<>&"]/g, ch => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[ch]));
  return `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="${W.toFixed(2)}mm" height="${H.toFixed(2)}mm" viewBox="0 0 ${W.toFixed(2)} ${H.toFixed(2)}">\n` +
    `  <title>${esc(o.label)}${c ? ' (shaded)' : ''}</title>\n  <g fill="none" stroke="#000" stroke-width="0.35" stroke-linecap="round" stroke-linejoin="round">\n` +
    (outl.length ? `    <path id="outlines" d="${d(outl)}"/>\n` : '') + (c && c.strokes.length ? `    <path id="shading" d="${d(c.strokes)}"/>\n` : '') + '  </g>\n</svg>\n';
}

/* ----- controls ----- */
$sh('sh-pattern').onchange = e => shadeSet({ pattern: e.target.value });
$sh('sh-angle').addEventListener('input', e => { $sh('sh-angleNum').value = e.target.value; shadeSet({ angle: +e.target.value }, 180); });
$sh('sh-angleNum').addEventListener('input', e => { e.target.dataset.typing = '1'; });
$sh('sh-angleNum').addEventListener('change', e => {
  delete e.target.dataset.typing;
  const v = parseFloat(e.target.value);
  if (Number.isFinite(v)) shadeSet({ angle: norm180(v) }); else syncShadeUI();
});
$sh('sh-angleNum').addEventListener('blur', e => { delete e.target.dataset.typing; syncShadeUI(); });
document.querySelectorAll('#shadeCard .sh-quick').forEach(b => { b.onclick = () => shadeSet({ angle: +b.dataset.a }); });
$sh('sh-spacing').addEventListener('change', e => {
  const v = parseFloat(e.target.value);
  if (v >= 0.3 && v <= 30) shadeSet({ spacing: v });
  else { log('Line spacing must be between 0.3 and 30 mm.', 'warn'); syncShadeUI(); }
});
$sh('sh-vary').onchange = e => shadeSet({ vary: e.target.value });
$sh('sh-which').onchange = e => shadeSet({ which: e.target.value });
$sh('sh-tone').onchange = e => shadeSet({ tone: e.target.checked });
$sh('sh-outline').onchange = e => shadeSet({ outline: e.target.checked });
$sh('sh-join').onchange = e => shadeSet({ join: e.target.checked });
$sh('sh-inset').addEventListener('change', e => {
  const v = parseFloat(e.target.value);
  if (v >= 0 && v <= 5) shadeSet({ inset: v }); else { log('Gap from outline must be between 0 and 5 mm.', 'warn'); syncShadeUI(); }
});
$sh('btnShadeRandom').onclick = () => shadeSet({ seed: (SH.st.seed || 1) + 1 });
$sh('btnShadeReset').onclick = () => {
  const o = selObj(); if (!o) return;
  o.shOv = new Map(); o.shOvVer++; syncShadeUI(); buildPlot();
  log(`Shape choices cleared — every shape of ${o.label} follows the shading settings again.`);
};
$sh('btnShadeSvg').onclick = () => {
  const o = selObj(); if (!o) return;
  const name = String(o.label || 'drawing').replace(/\.[^.]+$/, '').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-') || 'drawing';
  downloadText(`${name}${shadeOn(o) ? '-shaded' : ''}.svg`, shadeSvgText(o), 'image/svg+xml');
};

/* ----- click a shape of the selected object on the map ----- */
plotCv.addEventListener('pointerdown', ev => {
  const h = PL.lastHit;                                   // worked out before the click selected anything
  SH.press = h && h.kind === 'move' && h.wasSel ? { x: ev.clientX, y: ev.clientY, id: h.obj.id } : null;
});
plotCv.addEventListener('pointerup', ev => {
  const p = SH.press, o = selObj(); SH.press = null;
  if (!p || !o || o.id !== p.id || !shadeOn(o) || S.running) return;
  if (Math.hypot(ev.clientX - p.x, ev.clientY - p.y) > 4) return;          // that was a drag
  const r = plotCv.getBoundingClientRect(), v = plotView(), w = v.toW(ev.clientX - r.left, ev.clientY - r.top);
  const T = shadeTargetsFor(o), i = shadeTargetAt(T, placeInverse(o.place)(w));
  if (i < 0) return;
  const cur = o.shOv.get(i) || 'auto', nx = SHADE_OVERRIDES[(SHADE_OVERRIDES.indexOf(cur) + 1) % SHADE_OVERRIDES.length];
  if (nx === 'auto') o.shOv.delete(i); else o.shOv.set(i, nx);
  o.shOvVer++;
  SH.flash = { id: o.id, i, until: performance.now() + 900 };
  buildPlot();
  setTimeout(() => { if (!PL.drag) drawPlot(); }, 950);
  log(`${o.label}, shape ${i + 1}: ${nx === 'auto' ? 'back to the shading settings — ' : ''}${shadeDescribe(o, i)}.`);
});

shadeLoad();
syncShadeUI();
