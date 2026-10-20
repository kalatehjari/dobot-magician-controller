/* ===================== PLOTTER: placement controls, map handles, new sheet ===================== */
const $pl = id => document.getElementById(id);
const normAngle = a => { const r = ((((a + 180) % 360) + 360) % 360) - 180; return Math.abs(r) < 1e-9 ? 0 : +r.toFixed(3); };

function syncPlaceInputs() {
  const pl = S.plot.place, has = !!(S.plot.sketch && pl);
  for (const id of ['pl-size', 'pl-sizeNum', 'pl-rot', 'pl-rotNum', 'plot-mirror', 'btnRot90', 'btnPlCentre', 'btnPlLargest']) $pl(id).disabled = !has || S.running;
  if (!has) {
    $pl('pl-info').textContent = 'Load a drawing or a picture to place it on the paper.';
    $pl('pl-sizeVal').textContent = ''; $pl('pl-rotVal').textContent = '';
    return;
  }
  const sk = S.plot.sketch, z = drawZone(), T = placeTargets().filter(Boolean);
  const anyMax = T.length ? Math.max(...T.map(t => t.size)) : pl.size;
  const here = maxSizeAt(plProbe(), pl.cx, pl.cy, z, plotPad());
  const set = (id, v) => { const el = $pl(id); if (!el.dataset.typing) el.value = v; };   // never overwrite half-typed numbers
  $pl('pl-size').max = Math.max(10, Math.ceil(Math.max(anyMax, pl.size)));
  set('pl-size', Math.round(pl.size)); set('pl-sizeNum', +pl.size.toFixed(1));
  set('pl-rot', Math.round(pl.angle)); set('pl-rotNum', +pl.angle.toFixed(1));
  $pl('plot-mirror').checked = !!pl.mirror;
  $pl('pl-sizeVal').textContent = `${pl.size.toFixed(0)} mm (${(sk.w * pl.size).toFixed(0)} × ${(sk.h * pl.size).toFixed(0)})`;
  $pl('pl-rotVal').textContent = `${+pl.angle.toFixed(1)}°`;
  const info = $pl('pl-info');
  info.textContent = (S.plot.placeOk === false ? 'Does not fit here — ' : '') +
    `Centre X ${pl.cx.toFixed(0)}, Y ${pl.cy.toFixed(0)} mm · largest at this spot ${here.toFixed(0)} mm · largest anywhere ${anyMax.toFixed(0)} mm` +
    (z.fromModel ? '' : ' · green zone from the Setup limits (run Auto-calibrate for the real reach)');
  info.style.color = S.plot.placeOk === false ? 'var(--err)' : '';
}

// Try a placement; the nearest one that fits is used (moved towards free space, shrunk only if needed).
function applyWant(want) {
  if (!S.plot.sketch || S.running) return false;
  const r = fitPlace(want);
  if (!r) { S.plot.placeOk = false; syncPlaceInputs(); drawPlot(); return false; }
  setPlace(r); drawPlot();
  return true;
}
const startAdjust = () => { if (!PL.base && S.plot.place) PL.base = { ...S.plot.place }; };
const endAdjust = () => { if (!S.plot.place) return; PL.base = null; buildPlot(); };

// Middle of the green zone on the forward axis, keeping the size (made smaller only if it cannot fit there).
function centrePlace() {
  const pl = S.plot.place; if (!pl || S.running) return;
  const z = drawZone(), P = plProbe(), pad = plotPad(), xs = [];
  for (let x = z.rIn; x <= z.rOut; x += 0.5) if (probeFits(P, x, 0, pl.size, z, pad)) xs.push(x);
  if (xs.length) {
    const mid = (xs[0] + xs[xs.length - 1]) / 2, x = xs.reduce((b, v) => (Math.abs(v - mid) < Math.abs(b - mid) ? v : b), xs[0]);
    setPlace({ ...pl, cx: x, cy: 0 });
  } else {
    const t = placeTargets()[0];
    if (!t) return log('There is no room on the centre line — check the pen heights or lower the margin.', 'err');
    setPlace({ ...pl, cx: t.cx, cy: 0, size: Math.floor(t.size * 0.999 * 10) / 10 });
    log(`Made smaller (${S.plot.place.size.toFixed(0)} mm) to fit on the centre line.`, 'warn');
  }
  buildPlot();
}

// As big as the green zone allows at this rotation. Stays on the centre line unless a spot off to
// the side is clearly roomier.
function largestPlace() {
  const pl = S.plot.place; if (!pl || S.running) return;
  const [line, any] = placeTargets();
  const t = line && (!any || line.size >= any.size * 0.97) ? line : any;
  if (!t) return log('There is no room in the green zone — check the pen heights or lower the margin.', 'err');
  setPlace({ ...pl, cx: t.cx, cy: t.cy, size: Math.floor(t.size * 0.999 * 10) / 10 });
  log(`Largest at this rotation: ${S.plot.place.size.toFixed(0)} mm${Math.abs(t.cy) > 15 ? ' — off to the side, where the green zone has more room (turn it 90° to keep it central)' : ''}.`, 'ok');
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
  const v = parseFloat(e.target.value);
  if (!(v >= 1) || !S.plot.place) return syncPlaceInputs();
  applyWant({ ...S.plot.place, size: v });
  if (S.plot.place.size < v - 0.05) log(`The largest that fits is ${S.plot.place.size.toFixed(0)} mm.`, 'warn');
  buildPlot();
});
$pl('pl-rot').addEventListener('input', e => { startAdjust(); if (PL.base) applyWant({ ...PL.base, angle: normAngle(+e.target.value) }); });
$pl('pl-rot').addEventListener('change', endAdjust);
$pl('pl-rotNum').addEventListener('change', e => {
  const v = parseFloat(e.target.value);
  if (!Number.isFinite(v) || !S.plot.place) return syncPlaceInputs();
  applyWant({ ...S.plot.place, angle: normAngle(v) }); buildPlot();
});
$pl('btnRot90').onclick = () => { if (S.plot.place) { applyWant({ ...S.plot.place, angle: normAngle(S.plot.place.angle + 90) }); buildPlot(); } };
$pl('plot-mirror').onchange = e => { if (S.plot.place) { applyWant({ ...S.plot.place, mirror: e.target.checked }); buildPlot(); } };
$pl('btnPlCentre').onclick = centrePlace;
$pl('btnPlLargest').onclick = largestPlace;
$pl('plot-margin').addEventListener('change', () => { PL.targetsKey = ''; if (S.plot.sketch) buildPlot(); else drawPlot(); });
$pl('btnNewSheet').onclick = () => {
  S.paper.jobs = S.paper.jobs.filter(j => j.active);
  drawPlot();
  log('New sheet — the red lines are cleared.');
};

/* ----- direct manipulation on the map ----- */
function plotHit(ev) {
  if (!S.plot.sketch || !S.plot.place || S.running) return null;
  const r = plotCv.getBoundingClientRect(), sx = ev.clientX - r.left, sy = ev.clientY - r.top, v = plotView(), g = frameGeom(v);
  if (Math.hypot(sx - g.knob[0], sy - g.knob[1]) <= 11) return { kind: 'rot', sx, sy, v, g };
  for (const [x, y] of g.fr) if (Math.abs(sx - x) <= 9 && Math.abs(sy - y) <= 9) return { kind: 'size', sx, sy, v, g };
  const w = v.toW(sx, sy), u = placeInverse(S.plot.place)(w), sk = S.plot.sketch, tol = 8 / (v.k * S.plot.place.size);
  if (Math.abs(u.x) <= sk.w / 2 + tol && Math.abs(u.y) <= sk.h / 2 + tol) return { kind: 'move', sx, sy, v, g, w };
  return null;
}

plotCv.addEventListener('pointerdown', ev => {
  const h = plotHit(ev);
  if (!h) return;
  ev.preventDefault();
  plotCv.focus({ preventScroll: true });
  try { plotCv.setPointerCapture(ev.pointerId); } catch (e) {}
  PL.base = { ...S.plot.place };
  PL.drag = { ...h, a0: Math.atan2(h.sy - h.g.c[1], h.sx - h.g.c[0]), d0: Math.hypot(h.sx - h.g.c[0], h.sy - h.g.c[1]),
              grab: h.w ? { x: h.w.x - S.plot.place.cx, y: h.w.y - S.plot.place.cy } : null };
});

plotCv.addEventListener('pointermove', ev => {
  const r = plotCv.getBoundingClientRect(), sx = ev.clientX - r.left, sy = ev.clientY - r.top;
  if (!PL.drag) {
    const h = plotHit(ev);
    plotCv.style.cursor = !h ? 'default' : h.kind === 'move' ? 'move' : h.kind === 'size' ? 'nwse-resize' : 'grab';
    return;
  }
  const d = PL.drag, base = PL.base, z = drawZone(), pad = plotPad();
  if (d.kind === 'move') {
    const w = d.v.toW(sx, sy), pl = S.plot.place;
    const c = constrainMove(plProbe(), { x: pl.cx, y: pl.cy }, { x: w.x - d.grab.x, y: w.y - d.grab.y }, pl.size, z, pad);
    setPlace({ ...pl, cx: c.x, cy: c.y });
  } else if (d.kind === 'size') {
    const want = Math.max(5, base.size * Math.hypot(sx - d.g.c[0], sy - d.g.c[1]) / Math.max(1, d.d0));
    const cap = maxSizeAt(plProbe(), base.cx, base.cy, z, pad);
    setPlace({ ...base, size: Math.max(Math.min(5, cap), Math.min(want, cap * 0.999)) });
  } else {
    let a = base.angle + (Math.atan2(sy - d.g.c[1], sx - d.g.c[0]) - d.a0) / RAD;
    if (ev.shiftKey) a = Math.round(a / 15) * 15;
    else { const q = Math.round(a / 90) * 90; if (Math.abs(a - q) < 3) a = q; }   // gentle snap to square angles
    applyWant({ ...base, angle: normAngle(a) });
    return;
  }
  drawPlot();
});

const endPlotDrag = () => { if (!PL.drag) return; PL.drag = null; PL.base = null; buildPlot(); };
plotCv.addEventListener('pointerup', endPlotDrag);
plotCv.addEventListener('pointercancel', endPlotDrag);
plotCv.addEventListener('lostpointercapture', endPlotDrag);

plotCv.addEventListener('keydown', ev => {
  const pl = S.plot.place;
  if (!pl || S.running) return;
  const big = ev.shiftKey, step = big ? 10 : 1;
  const mv = { ArrowUp: [step, 0], ArrowDown: [-step, 0], ArrowLeft: [0, step], ArrowRight: [0, -step] }[ev.key];
  if (mv) {
    const c = constrainMove(plProbe(), { x: pl.cx, y: pl.cy }, { x: pl.cx + mv[0], y: pl.cy + mv[1] }, pl.size, drawZone(), plotPad());
    setPlace({ ...pl, cx: c.x, cy: c.y });
  } else if (ev.key === '+' || ev.key === '=') applyWant({ ...pl, size: pl.size + step });
  else if (ev.key === '-' || ev.key === '_') applyWant({ ...pl, size: Math.max(5, pl.size - step) });
  else if (ev.key === ']' || ev.key === '}') applyWant({ ...pl, angle: normAngle(pl.angle + (big ? 15 : 1)) });
  else if (ev.key === '[' || ev.key === '{') applyWant({ ...pl, angle: normAngle(pl.angle - (big ? 15 : 1)) });
  else return;
  ev.preventDefault();
  drawPlot();
  clearTimeout(PL.kt); PL.kt = setTimeout(() => buildPlot(), 350);
});

syncPlaceInputs();
