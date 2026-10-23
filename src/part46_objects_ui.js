/* ===================== PLOTTER: objects on the paper (list, copy, delete) ===================== */
const OBJ = { clearArmed: 0, trash: [], saveTimer: 0, saveWarned: false, restoring: false };
const $ob = id => document.getElementById(id);

// The list above the map: tick = draw it, click = select it.
function renderObjectList() {
  const box = $ob('obj-list'), objs = S.plot.objects, so = selObj();
  box.textContent = '';
  for (const o of objs) {
    const row = document.createElement('div');
    row.className = 'obj-item' + (so === o ? ' sel' : '') + (o.use ? '' : ' off') + (o.placeOk === false ? ' bad' : '');
    const cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = o.use; cb.title = 'Draw this one when Draw is pressed';
    cb.setAttribute('aria-label', `Draw ${o.label}`);
    cb.disabled = S.running;
    cb.onchange = () => { o.use = cb.checked; buildPlot({ quiet: true }); };
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'obj-name'; b.setAttribute('aria-pressed', String(so === o));
    b.title = `${o.kind === 'text' ? 'Text' : 'Drawing'}: ${o.label} — click to select it`;
    const tag = document.createElement('span'); tag.className = 'obj-kind'; tag.textContent = o.kind === 'text' ? 'Aa' : '✎';
    tag.setAttribute('aria-hidden', 'true');
    const nm = document.createElement('span'); nm.textContent = o.label; nm.dir = 'auto';
    const meta = document.createElement('span'); meta.className = 'obj-meta';
    meta.textContent = o.place ? (o.kind === 'text' && o.text ? `${o.text.height.toFixed(1)} mm letters` : `${o.place.size.toFixed(0)} mm`) : '';
    b.append(tag, nm, meta);
    b.onclick = () => { selectObject(o.id); plotCv.focus({ preventScroll: true }); };
    row.append(cb, b);
    box.appendChild(row);
  }
  const n = objs.length;
  $ob('obj-count').textContent = n ? `${n} on the paper${so ? '' : ' — none selected'}` : 'Nothing on the paper yet';
  $ob('btnObjDup').disabled = !so || S.running;
  $ob('btnObjDel').disabled = !so || S.running;
  $ob('btnObjClear').disabled = !n || S.running;
  $ob('btnObjOnly').disabled = !so || S.running || n < 2;
  $ob('btnObjUndo').hidden = !OBJ.trash.length;
  $ob('btnObjUndo').disabled = S.running;
  $ob('btnLayoutSvg').disabled = !n;
  $ob('btnLayoutSave').disabled = !n;
  if (!OBJ.clearArmed) $ob('btnObjClear').textContent = 'Remove all';
}

// A copy of the selected object next to it (or wherever there is room), selected.
function duplicateSelected() {
  const o = selObj();
  if (!o || S.running) return;
  const c = newObject(o.kind, o.sketch, o.label.endsWith(' (copy)') ? o.label : `${o.label} (copy)`,
    { source: o.source, text: o.text ? { ...o.text } : undefined, missing: o.missing });
  if (typeof shadeCopy === 'function') shadeCopy(o, c);
  c.use = o.use;
  const pl = o.place, z = drawZone(), pad = plotPad(), P = objProbe(c, pl.angle, pl.mirror), others = S.plot.objects;
  const b0 = frameBox(o.sketch, pl), W = b0.y1 - b0.y0 + 4, H = b0.x1 - b0.x0 + 4;
  // beside it on screen first: right (robot −Y), left, below (towards the base), above, then diagonals
  const tries = [[0, -W], [0, W], [-H, 0], [H, 0], [-H, -W], [-H, W], [H, -W], [H, W]];
  let spot = null;
  for (const [dx, dy] of tries) {
    const cx = pl.cx + dx, cy = pl.cy + dy;
    if (!probeFits(P, cx, cy, pl.size, z, pad)) continue;
    const b = frameBox(o.sketch, { ...pl, cx, cy });
    if (others.every(x => !x.place || boxOverlapArea(b, frameBox(x.sketch, x.place, 3)) === 0)) { spot = { cx, cy }; break; }
  }
  if (!spot) { const f = freeSpot(c, pl.size, others, pl.angle, pl.mirror); if (f && f.ov === 0) spot = f; }
  if (!spot) {                                     // no free room: a little to the side, overlapping
    const m = constrainMove(P, { x: pl.cx, y: pl.cy }, { x: pl.cx - 8, y: pl.cy - 8 }, pl.size, z, pad);
    spot = { cx: m.x, cy: m.y, ov: 1 };
  }
  S.plot.objects.push(c);
  S.plot.sel = c.id;
  setPlaceFor(c, { ...pl, cx: spot.cx, cy: spot.cy });
  onSelectionChange();
  buildPlot({ quiet: true });
  log(`Copied ${o.label}${spot.ov > 0 ? ' — there was no free room, so the copy overlaps; drag it where you want it' : ''}.`, 'ok');
}

function deleteSelected() { const o = selObj(); if (o) deleteObject(o); }

// Two clicks: the first arms the button for a few seconds.
function clearAllObjects() {
  if (S.running || !S.plot.objects.length) return;
  const b = $ob('btnObjClear');
  if (!OBJ.clearArmed) {
    OBJ.clearArmed = setTimeout(() => { OBJ.clearArmed = 0; b.textContent = 'Remove all'; b.classList.remove('on'); }, 3500);
    b.textContent = 'Click again to remove all'; b.classList.add('on');
    return;
  }
  clearTimeout(OBJ.clearArmed); OBJ.clearArmed = 0; b.textContent = 'Remove all'; b.classList.remove('on');
  const n = S.plot.objects.length;
  objTrash(S.plot.objects.slice());
  S.plot.objects = []; S.plot.sel = null; S.plot.placeVer++;
  document.getElementById('plot-file-name').textContent = 'no file loaded';
  onSelectionChange();
  buildPlot({ quiet: true });
  log(`Removed all ${n} object${n > 1 ? 's' : ''} from the paper.`);
}

// Untick everything except the selected object (e.g. to add one more thing to a sheet already drawn).
function drawOnlySelected() {
  const so = selObj();
  if (!so || S.running) return;
  for (const o of S.plot.objects) o.use = o === so;
  buildPlot({ quiet: true });
  log(`Only ${so.label} will be drawn — tick the others in the list to draw them again.`);
}

// Everything on the paper as one SVG, in millimetres, as seen on the map (the base at the bottom).
function layoutSvgText() {
  const objs = S.plot.objects.filter(o => o.place), paths = [];
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const o of objs) {
    const f = placeXform(o.place), c = typeof shadeFor === 'function' ? shadeFor(o, o.place.size) : null;
    const lines = (!c || o.shade.outline !== false ? o.sketch.strokes : []).concat(c ? c.strokes : []);
    const d = [];
    for (const s of lines) {
      if (s.length < 2) continue;
      d.push('M' + s.map(p => { const q = f(p), X = -q.y, Y = -q.x; x0 = Math.min(x0, X); x1 = Math.max(x1, X); y0 = Math.min(y0, Y); y1 = Math.max(y1, Y); return `${X.toFixed(2)} ${Y.toFixed(2)}`; }).join(' L'));
    }
    const esc = String(o.label).replace(/[<>&"]/g, ch => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[ch]));
    if (d.length) paths.push(`    <path data-name="${esc}"${o.use ? '' : ' opacity="0.35"'} d="${d.join('')}"/>`);
  }
  if (!paths.length) return null;
  const m = 5, W = x1 - x0 + 2 * m, H = y1 - y0 + 2 * m;
  return `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="${W.toFixed(2)}mm" height="${H.toFixed(2)}mm" viewBox="${(x0 - m).toFixed(2)} ${(y0 - m).toFixed(2)} ${W.toFixed(2)} ${H.toFixed(2)}">\n` +
    `  <title>Plotter layout (${objs.length} object${objs.length > 1 ? 's' : ''})</title>\n  <g fill="none" stroke="#000" stroke-width="0.35" stroke-linecap="round" stroke-linejoin="round">\n${paths.join('\n')}\n  </g>\n</svg>\n`;
}

/* ----- undo a removal ----- */
// What was removed, with where it was in the list, so Undo puts it back as it was.
function objTrash(list) {
  OBJ.trash.push(list.map(o => ({ o, at: S.plot.objects.indexOf(o) })));
  if (OBJ.trash.length > 20) OBJ.trash.shift();
}
function undoRemove() {
  const last = OBJ.trash.pop();
  if (!last || S.running) { if (last) OBJ.trash.push(last); return; }
  for (const { o, at } of last.slice().sort((a, b) => a.at - b.at)) S.plot.objects.splice(Math.min(Math.max(0, at), S.plot.objects.length), 0, o);
  S.plot.sel = last[last.length - 1].o.id; S.plot.placeVer++;
  onSelectionChange();
  buildPlot({ quiet: true });
  log(`Put back ${last.length === 1 ? last[0].o.label : last.length + ' objects'}.`, 'ok');
}

/* ----- layouts: save to a file, open, and keep the paper in this browser ----- */
const LAYOUT_Q = 20000;                 // stroke points stored to 1/20000 of the drawing's size
function layoutData() {
  return {
    format: 'magician-layout-v1', app: (document.querySelector('.ver') || {}).textContent || '', saved: new Date().toISOString(),
    objects: S.plot.objects.map(o => {
      const d = { kind: o.kind, label: o.label, source: o.source || null, use: o.use, place: o.place, shade: o.shade, ov: [...o.shOv] };
      if (o.kind === 'text') d.text = { ...o.text };
      else {
        const b = o.sketch.srcBox;
        d.box = b;
        d.strokes = o.sketch.strokes.map(st => { const a = []; for (const p of st) a.push(Math.round(p.x * LAYOUT_Q), Math.round(p.y * LAYOUT_Q)); return a; });
        if (o.sketch.shapes) d.shapes = o.sketch.shapes;
      }
      return d;
    }),
  };
}
// Objects from a saved layout (bad entries are skipped). Returns the new objects (not yet on the paper).
function layoutObjects(data) {
  if (!data || data.format !== 'magician-layout-v1' || !Array.isArray(data.objects)) throw new Error('This is not a Magician layout file.');
  const num = v => (typeof v === 'number' && Number.isFinite(v) ? v : null), out = [];
  for (const d of data.objects) {
    try {
      const pl = d.place || {}, place = { cx: num(pl.cx), cy: num(pl.cy), size: num(pl.size), angle: num(pl.angle) || 0, mirror: !!pl.mirror };
      if (place.cx === null || place.cy === null || !(place.size > 0)) continue;
      let o;
      if (d.kind === 'text') {
        const t = { ...TEXT_DEFAULTS, ...(d.text || {}) };
        t.str = String(t.str || ''); t.height = num(t.height) > 0 ? t.height : TEXT_DEFAULTS.height;
        const lay = textLayout(t);
        if (!lay.strokes.length) continue;
        o = newObject('text', textSketch(lay), textLabel(t.str), { text: t, missing: lay.missing });
        place.size = t.height * o.sketch.srcBox.L;
      } else {
        const b = d.box || { cx: 0, cy: 0, L: 1 }, L = num(b.L) > 0 ? b.L : 1, cx = num(b.cx) || 0, cy = num(b.cy) || 0;
        const strokes = (d.strokes || []).filter(a => Array.isArray(a) && a.length >= 2).map(a => {
          const st = [];
          for (let i = 0; i + 1 < a.length; i += 2) if (Number.isFinite(a[i]) && Number.isFinite(a[i + 1])) st.push({ x: cx + a[i] / LAYOUT_Q * L, y: cy + a[i + 1] / LAYOUT_Q * L });
          return st;
        }).filter(st => st.length);
        if (!strokes.length) continue;
        const sk = prepareSketch(strokes, d.source || null);
        sk.shapes = Array.isArray(d.shapes) ? d.shapes : null;
        o = newObject('drawing', sk, String(d.label || 'Drawing').slice(0, 80), { source: d.source || null });
      }
      o.label = String(d.label || o.label).slice(0, 80);
      o.use = d.use !== false;
      if (d.shade && typeof d.shade === 'object') o.shade = { ...SHADE_DEFAULTS, ...d.shade };
      if (Array.isArray(d.ov)) o.shOv = new Map(d.ov.filter(e => Array.isArray(e) && Number.isInteger(e[0]) && SHADE_OVERRIDES.includes(e[1])));
      o.place = place;
      out.push(o);
    } catch (e) { /* skip that one */ }
  }
  return out;
}
function layoutAdd(objs, replace) {
  if (replace) S.plot.objects = [];
  for (const o of objs) { S.plot.objects.push(o); setPlaceFor(o, o.place); }
  S.plot.sel = objs.length ? objs[objs.length - 1].id : (S.plot.objects.length ? S.plot.sel : null);
  onSelectionChange();
  buildPlot({ quiet: true });
}

// The paper is kept in this browser (a moment after each change) and comes back after a reload.
function paperSaveNow() {
  clearTimeout(OBJ.saveTimer); OBJ.saveTimer = 0;
  try {
    if (!S.plot.objects.length) { localStorage.removeItem('magician-paper'); return; }
    const txt = JSON.stringify(layoutData());
    if (txt.length > 2.5e6) {
      localStorage.removeItem('magician-paper');
      if (!OBJ.saveWarned) { OBJ.saveWarned = true; log('The paper is too big to keep in this browser — use Save layout to keep it.', 'warn'); }
      return;
    }
    localStorage.setItem('magician-paper', txt);
  } catch (e) {}
}
function paperAutosave() {
  if (OBJ.restoring) return;
  clearTimeout(OBJ.saveTimer);
  if (!S.plot.objects.length) { paperSaveNow(); return; }
  OBJ.saveTimer = setTimeout(paperSaveNow, 800);
}
window.addEventListener('pagehide', () => { if (OBJ.saveTimer) paperSaveNow(); });
function paperRestore() {
  let data = null;
  try { data = JSON.parse(localStorage.getItem('magician-paper') || 'null'); } catch (e) {}
  if (!data || !Array.isArray(data.objects) || !data.objects.length) return;
  try {
    OBJ.restoring = true;
    const objs = layoutObjects(data);
    if (objs.length) {
      layoutAdd(objs, true);
      log(`The paper from last time is back: ${objs.length} object${objs.length > 1 ? 's' : ''} (Remove all to start afresh).`);
    }
  } catch (e) { /* an old or broken copy: ignore it */ }
  finally { OBJ.restoring = false; }
}

$ob('btnObjUndo').onclick = undoRemove;
$ob('btnLayoutSave').onclick = () => {
  if (!S.plot.objects.length) return;
  downloadText(`plotter-layout-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(layoutData()));
  log(`Layout saved: ${S.plot.objects.length} object${S.plot.objects.length > 1 ? 's' : ''}.`, 'ok');
};
$ob('btnLayoutOpen').onclick = () => $ob('layout-file').click();
$ob('layout-file').onchange = async e => {
  const f = e.target.files[0]; e.target.value = '';
  if (!f) return;
  try {
    const objs = layoutObjects(JSON.parse(await f.text()));
    if (!objs.length) throw new Error('No drawings or text in it.');
    layoutAdd(objs, false);
    log(`Opened ${f.name}: ${objs.length} object${objs.length > 1 ? 's' : ''} added to the paper.`, 'ok');
  } catch (err) { log('Could not open that layout: ' + err.message, 'err'); }
};

$ob('btnObjDup').onclick = duplicateSelected;
$ob('btnObjDel').onclick = deleteSelected;
$ob('btnObjClear').onclick = clearAllObjects;
$ob('btnObjOnly').onclick = drawOnlySelected;
$ob('btnLayoutSvg').onclick = () => { const t = layoutSvgText(); if (t) downloadText('plotter-layout.svg', t, 'image/svg+xml'); };

// Map shortcuts: Delete / Backspace removes the selected object, D (or Ctrl/⌘+D) copies it,
// Ctrl/⌘+Z puts back what was removed.
plotCv.addEventListener('keydown', ev => {
  if (S.running) return;
  if ((ev.key === 'z' || ev.key === 'Z') && (ev.ctrlKey || ev.metaKey) && !ev.shiftKey) { ev.preventDefault(); undoRemove(); return; }
  if (!selObj()) return;
  if (ev.key === 'Delete' || ev.key === 'Backspace') { ev.preventDefault(); deleteSelected(); }
  else if ((ev.key === 'd' || ev.key === 'D') && !ev.altKey) { ev.preventDefault(); duplicateSelected(); }
});

renderObjectList();
setTimeout(paperRestore, 0);           // after every part of the page has started
