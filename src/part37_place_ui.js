/* ===================== PLOTTER: placement controls, map handles, selection, new sheet ===================== */
const $pl = id => document.getElementById(id);
const normAngle = a => { const r = ((((a + 180) % 360) + 360) % 360) - 180; return Math.abs(r) < 1e-9 ? 0 : +r.toFixed(3); };

function syncPlaceInputs() {
  const o = selObj(), pl = o && o.place, has = !!pl;
  for (const id of ['pl-size', 'pl-sizeNum', 'pl-rot', 'pl-rotNum', 'plot-mirror', 'btnRot90', 'btnPlCentre', 'btnPlLargest']) $pl(id).disabled = !has || S.running;
  if (!has) {
    const n = S.plot.objects.length;
    $pl('pl-info').textContent = n ? `${n} object${n > 1 ? 's' : ''} on the paper — click one on the map (or in the list) to move, resize or turn it.`
      : 'Load a drawing or a picture, pick one from the library, or add text, to place it on the paper.';
    $pl('pl-info').style.color = '';
    $pl('pl-sizeVal').textContent = ''; $pl('pl-rotVal').textContent = '';
    return;
  }
  const sk = o.sketch, z = drawZone(), T = objTargets(o).filter(Boolean);
  const anyMax = T.length ? Math.max(...T.map(t => t.size)) : pl.size;
  const here = maxSizeAt(objProbe(o), pl.cx, pl.cy, z, plotPad());
  const set = (id, v) => { const el = $pl(id); if (!el.dataset.typing) el.value = v; };   // never overwrite half-typed numbers
  $pl('pl-size').max = Math.max(10, Math.ceil(Math.max(anyMax, pl.size)));
  set('pl-size', Math.round(pl.size)); set('pl-sizeNum', +pl.size.toFixed(1));
  set('pl-rot', Math.round(pl.angle)); set('pl-rotNum', +pl.angle.toFixed(1));
  $pl('plot-mirror').checked = !!pl.mirror;
  $pl('pl-sizeVal').textContent = `${pl.size.toFixed(0)} mm (${(sk.w * pl.size).toFixed(0)} × ${(sk.h * pl.size).toFixed(0)})`;
  $pl('pl-rotVal').textContent = `${+pl.angle.toFixed(1)}°`;
  const info = $pl('pl-info');
  info.textContent = (o.placeOk === false ? 'Does not fit here — ' : '') + `${bidiIsolate(o.label)}: ` +
    `centre X ${pl.cx.toFixed(0)}, Y ${pl.cy.toFixed(0)} mm · largest at this spot ${here.toFixed(0)} mm · largest anywhere ${anyMax.toFixed(0)} mm` +
    (z.fromModel ? '' : ' · green zone from the Setup limits (run Auto-calibrate for the real reach)');
  info.style.color = o.placeOk === false ? 'var(--err)' : '';
}

// Try a placement for the selected object; the nearest one that fits is used (moved towards free
// space, shrunk only if needed).
function applyWant(want) {
  const o = selObj();
  if (!o || S.running) return false;
  const r = fitPlaceFor(o, want);
  if (!r) { o.placeOk = false; syncPlaceInputs(); drawPlot(); return false; }
  setPlaceFor(o, r); drawPlot();
  return true;
}
const startAdjust = () => { const o = selObj(); if (!PL.base && o) PL.base = { ...o.place }; };
const endAdjust = () => { if (!selObj()) return; PL.base = null; afterResize(); buildPlot(); };
// Made-up bold text follows the letter height, so its lines are laid out again after a resize.
function afterResize() {
  const o = selObj();
  if (o && o.kind === 'text' && typeof textRelayout === 'function') textRelayout(o);
}

// Middle of the green zone on the forward axis, keeping the size (made smaller only if it cannot fit there).
function centrePlace() {
  const o = selObj(), pl = o && o.place; if (!pl || S.running) return;
  const z = drawZone(), P = objProbe(o), pad = plotPad(), xs = [];
  const cy0 = z.pq ? zoneCentreY(z) : 0;                 // with a safe zone: across its middle
  for (let x = z.rIn; x <= z.rOut; x += 0.5) if (probeFits(P, x, cy0, pl.size, z, pad)) xs.push(x);
  if (xs.length) {
    const mid = (xs[0] + xs[xs.length - 1]) / 2, x = xs.reduce((b, v) => (Math.abs(v - mid) < Math.abs(b - mid) ? v : b), xs[0]);
    setPlaceFor(o, { ...pl, cx: x, cy: cy0 });
  } else if (z.pq) {
    const t = objTargets(o)[1];
    if (!t) return log('There is no room for it in the safe zone — make it smaller or the zone bigger.', 'err');
    setPlaceFor(o, { ...pl, cx: t.cx, cy: t.cy, size: Math.min(pl.size, Math.floor(t.size * 0.999 * 10) / 10) });
    if (o.place.size < pl.size) { log(`Made smaller (${o.place.size.toFixed(0)} mm) to fit in the safe zone.`, 'warn'); afterResize(); }
  } else {
    const t = objTargets(o)[0];
    if (!t) return log('There is no room on the centre line — check the pen heights or lower the margin.', 'err');
    setPlaceFor(o, { ...pl, cx: t.cx, cy: 0, size: Math.floor(t.size * 0.999 * 10) / 10 });
    log(`Made smaller (${o.place.size.toFixed(0)} mm) to fit on the centre line.`, 'warn');
    afterResize();
  }
  buildPlot();
}

// As big as the green zone allows at this rotation. Stays on the centre line unless a spot off to
// the side is clearly roomier.
function largestPlace() {
  const o = selObj(), pl = o && o.place; if (!pl || S.running) return;
  const [line, any] = objTargets(o);
  const t = line && (!any || line.size >= any.size * 0.97) ? line : any;
  if (!t) return log('There is no room in the green zone — check the pen heights or lower the margin.', 'err');
  setPlaceFor(o, { ...pl, cx: t.cx, cy: t.cy, size: Math.floor(t.size * 0.999 * 10) / 10 });
  log(`Largest at this rotation: ${o.place.size.toFixed(0)} mm${Math.abs(t.cy) > 15 ? ' — off to the side, where the green zone has more room (turn it 90° to keep it central)' : ''}.`, 'ok');
  afterResize();
  buildPlot();
}

/* ----- controls ----- */
for (const id of ['pl-sizeNum', 'pl-rotNum']) {
  $pl(id).addEventListener('input', e => { e.target.dataset.typing = '1'; });
  $pl(id).addEventListener('change', e => { delete e.target.dataset.typing; });
  $pl(id).addEventListener('blur', e => { delete e.target.dataset.typing; syncPlaceInputs(); });
}
$pl('pl-size').addEventListener('input', e => { startAdjust(); if (PL.base) applyWant({ ...PL.base, size: +e.target.value }); });
$pl('pl-size').addEventListener('change', endAdjust);
$pl('pl-sizeNum').addEventListener('change', e => {
  const v = parseFloat(e.target.value), o = selObj();
  if (!(v >= 1) || !o) return syncPlaceInputs();
  applyWant({ ...o.place, size: v });
  if (o.place.size < v - 0.05) log(`The largest that fits is ${o.place.size.toFixed(0)} mm.`, 'warn');
  afterResize();
  buildPlot();
});
$pl('pl-rot').addEventListener('input', e => { startAdjust(); if (PL.base) applyWant({ ...PL.base, angle: normAngle(+e.target.value) }); });
$pl('pl-rot').addEventListener('change', endAdjust);
$pl('pl-rotNum').addEventListener('change', e => {
  const v = parseFloat(e.target.value), o = selObj();
  if (!Number.isFinite(v) || !o) return syncPlaceInputs();
  applyWant({ ...o.place, angle: normAngle(v) }); buildPlot();
});
$pl('btnRot90').onclick = () => { const o = selObj(); if (o) { applyWant({ ...o.place, angle: normAngle(o.place.angle + 90) }); buildPlot(); } };
$pl('plot-mirror').onchange = e => { const o = selObj(); if (o) { applyWant({ ...o.place, mirror: e.target.checked }); buildPlot(); } };
$pl('btnPlCentre').onclick = centrePlace;
$pl('btnPlLargest').onclick = largestPlace;
$pl('plot-margin').addEventListener('change', () => {
  for (const o of S.plot.objects) o.targetsKey = '';
  if (S.plot.objects.length) buildPlot({ quiet: true }); else drawPlot();
});
$pl('btnNewSheet').onclick = () => {
  S.paper.jobs = S.paper.jobs.filter(j => j.active);
  drawPlot();
  log('New sheet — the red lines are cleared.');
};

/* ----- direct manipulation on the map ----- */
// The object whose lines are nearest the point (within a few pixels); otherwise the selected object
// if the point is inside its frame, else the smallest frame the point is in.
function objectAt(w, v) {
  const tolPx = 7;
  let best = null, bd = Infinity;
  for (const o of S.plot.objects) {
    const pl = o.place;
    if (!pl || !(pl.size > 0)) continue;
    const P = objProbe(o), s = pl.size, ux = (w.x - pl.cx) / s, uy = (w.y - pl.cy) / s, tol = tolPx / (v.k * s);
    for (const c of P.chunks) {
      if (ux < c.minX - tol || ux > c.maxX + tol || uy < c.minY - tol || uy > c.maxY + tol) continue;
      const a = c.a;
      for (let i = 0; i < a.length; i += 2) {
        let d;
        if (i + 2 < a.length) {
          const ax = a[i], ay = a[i + 1], ex = a[i + 2] - ax, ey = a[i + 3] - ay, L2 = ex * ex + ey * ey;
          const t = L2 > 0 ? Math.max(0, Math.min(1, ((ux - ax) * ex + (uy - ay) * ey) / L2)) : 0;
          d = Math.hypot(ax + t * ex - ux, ay + t * ey - uy);
        } else if (a.length === 2) d = Math.hypot(a[0] - ux, a[1] - uy);
        else continue;
        const px = d * v.k * s;
        if (px < bd || (px <= bd + 0.5 && o.id === S.plot.sel)) { bd = Math.min(bd, px); best = o; }
      }
    }
  }
  if (best && bd <= tolPx) return best;
  const inFrame = o => {
    if (!o.place) return false;
    const u = placeInverse(o.place)(w), tol = 6 / (v.k * o.place.size);
    return Math.abs(u.x) <= o.sketch.w / 2 + tol && Math.abs(u.y) <= o.sketch.h / 2 + tol;
  };
  const so = selObj();
  if (so && inFrame(so)) return so;
  let small = null, sa = Infinity;
  for (const o of S.plot.objects) {
    if (!inFrame(o)) continue;
    const a = o.sketch.w * o.sketch.h * o.place.size * o.place.size;
    if (a < sa) { sa = a; small = o; }
  }
  return small;
}

// What the pointer is on: the selected object's rotate knob or corner handles, or an object.
function plotHit(ev) {
  if (!S.plot.objects.length || S.running) return null;
  const r = plotCv.getBoundingClientRect(), sx = ev.clientX - r.left, sy = ev.clientY - r.top, v = plotView(), w = v.toW(sx, sy);
  const so = selObj();
  if (so && so.place) {
    const g = frameGeom(v, so);
    if (Math.hypot(sx - g.knob[0], sy - g.knob[1]) <= 11) return { kind: 'rot', obj: so, wasSel: true, sx, sy, v, g };
    for (const [x, y] of g.fr) if (Math.abs(sx - x) <= 9 && Math.abs(sy - y) <= 9) return { kind: 'size', obj: so, wasSel: true, sx, sy, v, g };
  }
  const o = objectAt(w, v);
  if (!o) return { kind: 'none', obj: null, wasSel: false, sx, sy, v, w };
  return { kind: 'move', obj: o, wasSel: o === so, sx, sy, v, g: frameGeom(v, o), w };
}

plotCv.addEventListener('pointerdown', ev => {
  const h = plotHit(ev);
  PL.lastHit = h;
  if (!h) return;
  if (h.kind === 'none') { selectObject(null); return; }
  ev.preventDefault();
  plotCv.focus({ preventScroll: true });
  try { plotCv.setPointerCapture(ev.pointerId); } catch (e) {}
  if (!h.wasSel) selectObject(h.obj.id);
  const pl = h.obj.place;
  PL.base = { ...pl };
  PL.drag = { ...h, a0: Math.atan2(h.sy - h.g.c[1], h.sx - h.g.c[0]), d0: Math.hypot(h.sx - h.g.c[0], h.sy - h.g.c[1]),
              grab: h.w ? { x: h.w.x - pl.cx, y: h.w.y - pl.cy } : null, ver: S.plot.placeVer };
});

plotCv.addEventListener('pointermove', ev => {
  const r = plotCv.getBoundingClientRect(), sx = ev.clientX - r.left, sy = ev.clientY - r.top;
  if (!PL.drag) {
    const h = plotHit(ev);
    plotCv.style.cursor = !h || h.kind === 'none' ? 'default' : h.kind === 'move' ? (h.wasSel ? 'move' : 'pointer') : h.kind === 'size' ? 'nwse-resize' : 'grab';
    const hv = h && h.obj && !h.wasSel ? h.obj.id : null;
    if (hv !== PL.hover) { PL.hover = hv; drawPlot(); }
    return;
  }
  const d = PL.drag, base = PL.base, z = drawZone(), pad = plotPad(), o = selObj();
  if (!o || o !== d.obj) return;
  if (d.kind === 'move') {
    const w = d.v.toW(sx, sy), pl = o.place;
    const c = constrainMove(objProbe(o), { x: pl.cx, y: pl.cy }, { x: w.x - d.grab.x, y: w.y - d.grab.y }, pl.size, z, pad);
    setPlaceFor(o, { ...pl, cx: c.x, cy: c.y });
  } else if (d.kind === 'size') {
    const want = Math.max(5, base.size * Math.hypot(sx - d.g.c[0], sy - d.g.c[1]) / Math.max(1, d.d0));
    const cap = maxSizeAt(objProbe(o), base.cx, base.cy, z, pad);
    setPlaceFor(o, { ...base, size: Math.max(Math.min(5, cap), Math.min(want, cap * 0.999)) });
  } else {
    let a = base.angle + (Math.atan2(sy - d.g.c[1], sx - d.g.c[0]) - d.a0) / RAD;
    if (ev.shiftKey) a = Math.round(a / 15) * 15;
    else { const q = Math.round(a / 90) * 90; if (Math.abs(a - q) < 3) a = q; }   // gentle snap to square angles
    applyWant({ ...base, angle: normAngle(a) });
    return;
  }
  drawPlot();
});

plotCv.addEventListener('pointerleave', () => { if (!PL.drag && PL.hover != null) { PL.hover = null; drawPlot(); } });

const endPlotDrag = () => {
  if (!PL.drag) return;
  const d = PL.drag; PL.drag = null; PL.base = null;
  if (S.plot.placeVer === d.ver && S.plot.ops && S.plot.opsVer === S.plot.placeVer) { drawPlot(); return; }   // a click: nothing moved
  if (d.kind === 'size') afterResize();
  buildPlot();
};
plotCv.addEventListener('pointerup', endPlotDrag);
plotCv.addEventListener('pointercancel', endPlotDrag);
plotCv.addEventListener('lostpointercapture', endPlotDrag);

plotCv.addEventListener('keydown', ev => {
  const o = selObj(), pl = o && o.place;
  if (!pl || S.running) return;
  const big = ev.shiftKey, step = big ? 10 : 1;
  const mv = { ArrowUp: [step, 0], ArrowDown: [-step, 0], ArrowLeft: [0, step], ArrowRight: [0, -step] }[ev.key];
  if (mv) {
    const c = constrainMove(objProbe(o), { x: pl.cx, y: pl.cy }, { x: pl.cx + mv[0], y: pl.cy + mv[1] }, pl.size, drawZone(), plotPad());
    setPlaceFor(o, { ...pl, cx: c.x, cy: c.y });
  } else if (ev.key === '+' || ev.key === '=') applyWant({ ...pl, size: pl.size + step });
  else if (ev.key === '-' || ev.key === '_') applyWant({ ...pl, size: Math.max(5, pl.size - step) });
  else if (ev.key === ']' || ev.key === '}') applyWant({ ...pl, angle: normAngle(pl.angle + (big ? 15 : 1)) });
  else if (ev.key === '[' || ev.key === '{') applyWant({ ...pl, angle: normAngle(pl.angle - (big ? 15 : 1)) });
  else return;
  ev.preventDefault();
  drawPlot();
  clearTimeout(PL.kt); PL.kt = setTimeout(() => { if (/[-+=_]/.test(ev.key)) afterResize(); buildPlot(); }, 350);
});

syncPlaceInputs();
