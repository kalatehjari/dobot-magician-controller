/* ===================== PLOTTER: SAFE ZONE, PAPER HEIGHT, CLEAR, REDRAW ===================== */
// The safe zone is a polygon clicked on the paper map (robot mm, kept in localStorage). Drawings
// stay inside it by the safety margin and pen-up travel goes round inside it (geometry in part 53).
// Homing and calibration are not limited by it.

const SZ = { mode: '', pts: [], cursor: null, drag: -1, undo: null, key: '', pq: null, Rkey: '', R: null, route: null };
const $sz = id => document.getElementById(id);
S.safe = { poly: null, on: false };

function szLoad() {
  try {
    const d = JSON.parse(localStorage.getItem('magician-safe-zone') || 'null');
    if (d && Array.isArray(d.poly) && !polyCheck(d.poly)) S.safe = { poly: d.poly.map(p => ({ x: +p.x, y: +p.y })), on: d.on !== false };
  } catch (e) {}
}
function szSave() { try { localStorage.setItem('magician-safe-zone', JSON.stringify(S.safe)); } catch (e) {} }

// The safe zone in use (null when there is none, or it is switched off).
function safePoly() { const s = S.safe; return s && s.on && s.poly && s.poly.length >= 3 ? s.poly : null; }
function safePrep(P) { const key = polyKeyOf(P); if (SZ.key !== key) { SZ.key = key; SZ.pq = polyPrep(P); } return { pq: SZ.pq, key }; }

// The allowed area (green zone ∩ safe zone, less the margin) and the router inside it, kept until the
// zone changes.
function allowedRegion() {
  const z = drawZone(), k = zoneKey(z);
  if (SZ.Rkey !== k || !SZ.R) { SZ.Rkey = k; SZ.R = regionBuild(z, z.poly || null); SZ.route = null; }
  return SZ.R;
}
function allowedRouter() { const R = allowedRegion(); if (!SZ.route) SZ.route = regionRouter(R); return SZ.route; }

// Pen-up travel a → b inside the allowed area: the corners to pass. From outside (the arm is away
// from the paper), first in by the shortest way.
function zoneTravel(a, b) {
  const R = allowedRegion(), route = allowedRouter(), w = [];
  if (R.empty) throw new Error('The safe zone and the green zone do not overlap — draw the safe zone inside the green zone.');
  let from = a;
  if (!regionHas(R, a.x, a.y, 0.05)) { const q = regionProject(R, a.x, a.y); if (q) { w.push(q); from = q; } }
  let to = b;
  if (!regionHas(R, b.x, b.y, 0.05)) to = regionProject(R, b.x, b.y) || b;
  const r = route(from, to);
  if (!r) throw new Error('There is no way between two parts of the drawing inside the safe zone — make the zone one piece round the drawing.');
  return w.concat(r);
}
// Travel router for drawing jobs: when a safe zone is drawn, or the safety lock is on.
function zoneTravelFor() { return safePoly() || (typeof LOCK !== 'undefined' && LOCK.on) ? zoneTravel : null; }

// Hover round (part 5): every step of the loop inside the allowed area?
function zoneLoopOk(path) {
  if (!zoneTravelFor()) return true;
  const R = allowedRegion();
  for (let i = 1; i < path.length; i++) if (!regionSegInside(R, path[i - 1].x, path[i - 1].y, path[i].x, path[i].y, 0.05)) return false;
  return path.length > 0 && regionHas(R, path[0].x, path[0].y, 0.05);
}
// The outline loop cut to the allowed area: the largest piece, as a closed loop of points.
function zoneHoverLoop(loop) {
  if (!zoneTravelFor() || !loop || loop.length < 3) return null;
  const R = allowedRegion(), area = [];
  for (const r of R.rings) area.push(clPath(r.P.flatMap(p => [p.x, p.y])));
  const L = polySArea(loop) >= 0 ? loop : loop.slice().reverse();
  const cut = clInter([clPath(L.flatMap(p => [p.x, p.y]))], clOffset(area, -0.3));
  let best = null, ba = 0;
  for (const c of cut) { const a = Math.abs(CL.Clipper.Area(c)); if (a > ba) { ba = a; best = c; } }
  if (!best) return null;
  const xy = clXY(best), out = [];
  for (let i = 0; i < xy.length; i += 2) out.push({ x: xy[i], y: xy[i + 1] });
  return out.length >= 3 ? out : null;
}
// Middle of the safe zone across (for Centre).
function zoneCentreY(z) {
  const P = z.poly || [];
  let a = 0, cy = 0;
  for (let i = 0; i < P.length; i++) { const p = P[i], q = P[(i + 1) % P.length], k = p.x * q.y - q.x * p.y; a += k; cy += (p.y + q.y) * k; }
  return Math.abs(a) > 1e-9 ? cy / (3 * a) : 0;
}

/* ----- drawing and editing the zone on the map ----- */
const SZ_PAPERS = { A6: [105, 148], A5: [148, 210], A4: [210, 297], A3: [297, 420], Letter: [216, 279] };

function szInfo() {
  const el = $sz('sz-info'), s = S.safe, P = s.poly;
  const editing = !!SZ.mode;
  $sz('btnSzDraw').hidden = editing; $sz('btnSzEdit').hidden = editing || !P; $sz('btnSzClear').hidden = editing || !P;
  $sz('sz-paper').hidden = editing; $sz('sz-onWrap').hidden = editing || !P;
  $sz('btnSzDone').hidden = !editing; $sz('btnSzCancel').hidden = !editing; $sz('btnSzPen').hidden = SZ.mode !== 'draw';
  $sz('btnSzUndo').hidden = editing || !SZ.undo;
  $sz('sz-on').checked = !!(P && s.on);
  if (SZ.mode === 'draw') { el.textContent = `Click the corners on the map (${SZ.pts.length} so far) — or move the pen to a corner of the paper and press "Add pen position". Click the first corner again, double-click or press Enter to close; Backspace takes the last corner off.`; return; }
  if (SZ.mode === 'edit') { el.textContent = 'Drag a corner to move it. Drag a point on an edge to add a corner there; right-click a corner to remove it.'; return; }
  if (!P) { el.textContent = 'None — the green zone is the limit. Draw one round your paper, so the pen never leaves it.'; return; }
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of P) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
  el.textContent = s.on ? `${P.length} corners, ${(y1 - y0).toFixed(0)} × ${(x1 - x0).toFixed(0)} mm. Drawings keep the safety margin inside it, and the pen travels round inside it.`
    : `${P.length} corners — switched off, so the green zone is the limit.`;
}

function szApply(poly, on = true, msg) {
  SZ.undo = S.safe.poly ? { ...S.safe, poly: S.safe.poly.slice() } : { poly: null, on: false };
  S.safe = { poly, on: !!poly && on };
  szSave();
  for (const o of S.plot.objects) o.targetsKey = '';
  if (msg) log(msg, 'ok');
  szInfo();
  if (S.plot.objects.length) buildPlot({ quiet: true }); else drawPlot();
  if (typeof lockZoneChanged === 'function') lockZoneChanged();
}

function szStart(mode) {
  if (S.running) return log('Wait until the drawing has finished.', 'warn');
  SZ.mode = mode; SZ.drag = -1; SZ.cursor = null;
  SZ.pts = mode === 'edit' && S.safe.poly ? S.safe.poly.map(p => ({ ...p })) : [];
  plotCv.classList.add('sz-editing');
  szInfo(); drawPlot();
}
function szStop() { SZ.mode = ''; SZ.pts = []; SZ.drag = -1; plotCv.classList.remove('sz-editing'); szInfo(); drawPlot(); }

function szFinish() {
  const P = [];
  for (const p of SZ.pts) if (!P.length || Math.hypot(p.x - P[P.length - 1].x, p.y - P[P.length - 1].y) > 0.5) P.push(p);   // double-click leaves a duplicate
  while (P.length > 3 && Math.hypot(P[0].x - P[P.length - 1].x, P[0].y - P[P.length - 1].y) <= 0.5) P.pop();
  const bad = polyCheck(P);
  if (bad) return log(`This safe zone ${bad} — ${SZ.mode === 'draw' ? 'add or move corners' : 'move the corners'} and try again.`, 'err');
  const wasDraw = SZ.mode === 'draw';
  szStop();
  szApply(P.map(p => ({ x: +p.x.toFixed(2), y: +p.y.toFixed(2) })), true, wasDraw ? `Safe zone set: ${P.length} corners. Drawings keep inside it.` : 'Safe zone changed.');
  const R = allowedRegion();
  if (R.empty) log('The safe zone does not overlap the green zone, so nothing can be drawn — move it over the green zone.', 'err');
}

function szAddPoint(w) { SZ.pts.push({ x: w.x, y: w.y }); szInfo(); drawPlot(); }

function szPaper(name) {
  const d = SZ_PAPERS[name];
  if (!d) return;
  const z = drawZone(), cx = (z.rIn + z.rOut) / 2, w = d[0] / 2, h = d[1] / 2;     // long side across the arm
  szApply([{ x: cx - w, y: -h }, { x: cx + w, y: -h }, { x: cx + w, y: h }, { x: cx - w, y: h }], true,
    `Safe zone: an ${name} sheet (${d[0]} × ${d[1]} mm) centred in front of the arm. Drag its corners (Edit corners) to where the paper really is.`);
}

const szScreen = (ev) => { const r = plotCv.getBoundingClientRect(); return { sx: ev.clientX - r.left, sy: ev.clientY - r.top }; };
function szVertexAt(v, sx, sy, pts, px = 9) {
  let best = -1, bd = px;
  pts.forEach((p, i) => { const [x, y] = v.toS(p.x, p.y), d = Math.hypot(x - sx, y - sy); if (d <= bd) { bd = d; best = i; } });
  return best;
}
function szEdgeAt(v, sx, sy, pts, px = 7) {
  for (let i = 0; i < pts.length; i++) {
    const [ax, ay] = v.toS(pts[i].x, pts[i].y), [bx, by] = v.toS(pts[(i + 1) % pts.length].x, pts[(i + 1) % pts.length].y);
    if (Math.sqrt(pSegD2(sx, sy, ax, ay, bx, by)) <= px) return i;
  }
  return -1;
}

plotCv.addEventListener('pointerdown', ev => {
  if (!SZ.mode) return;
  ev.preventDefault(); ev.stopImmediatePropagation();
  const { sx, sy } = szScreen(ev), v = plotView(), w = v.toW(sx, sy);
  if (SZ.mode === 'draw') {
    if (ev.button !== 0) return;
    if (SZ.pts.length >= 3 && szVertexAt(v, sx, sy, [SZ.pts[0]], 10) === 0) return szFinish();
    szAddPoint(w);
    return;
  }
  const i = szVertexAt(v, sx, sy, SZ.pts);
  if (ev.button === 2) {
    if (i >= 0 && SZ.pts.length > 3) { SZ.pts.splice(i, 1); drawPlot(); }
    return;
  }
  if (i >= 0) SZ.drag = i;
  else {
    const e = szEdgeAt(v, sx, sy, SZ.pts);
    if (e >= 0) { SZ.pts.splice(e + 1, 0, { x: w.x, y: w.y }); SZ.drag = e + 1; }
  }
  if (SZ.drag >= 0) { try { plotCv.setPointerCapture(ev.pointerId); } catch (e) {} }
  drawPlot();
}, true);
plotCv.addEventListener('pointermove', ev => {
  if (!SZ.mode) return;
  ev.stopImmediatePropagation();
  const { sx, sy } = szScreen(ev), v = plotView(), w = v.toW(sx, sy);
  SZ.cursor = w;
  if (SZ.mode === 'edit' && SZ.drag >= 0) SZ.pts[SZ.drag] = { x: w.x, y: w.y };
  plotCv.style.cursor = SZ.mode === 'draw' ? 'crosshair' : szVertexAt(v, sx, sy, SZ.pts) >= 0 ? 'move' : szEdgeAt(v, sx, sy, SZ.pts) >= 0 ? 'copy' : 'default';
  drawPlot();
}, true);
plotCv.addEventListener('pointerup', ev => { if (!SZ.mode) return; ev.stopImmediatePropagation(); SZ.drag = -1; }, true);
plotCv.addEventListener('dblclick', ev => { if (SZ.mode === 'draw') { ev.preventDefault(); ev.stopImmediatePropagation(); szFinish(); } }, true);
plotCv.addEventListener('contextmenu', ev => { if (SZ.mode) ev.preventDefault(); }, true);
plotCv.addEventListener('pointerleave', () => { if (SZ.mode) { SZ.cursor = null; drawPlot(); } });
document.addEventListener('keydown', ev => {
  if (!SZ.mode || /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
  if (ev.key === 'Enter') { ev.preventDefault(); szFinish(); }
  else if (ev.key === 'Backspace' && SZ.mode === 'draw') { ev.preventDefault(); SZ.pts.pop(); szInfo(); drawPlot(); }
  else if (ev.key === 'Escape') szStop();            // Escape also stops the arm, as everywhere
}, true);

// The safe zone on the map: outside it darker, its edge in the accent colour; while editing, the
// corners and the line to the pointer.
function zoneOverlay(ctx, v, z) {
  const P = SZ.mode ? SZ.pts : S.safe.poly, on = !!(SZ.mode || safePoly());
  if (P && P.length >= (SZ.mode === 'draw' ? 1 : 3)) {
    ctx.save();
    const path = () => { ctx.beginPath(); P.forEach((p, i) => { const [x, y] = v.toS(p.x, p.y); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); };
    if (on && P.length >= 3 && SZ.mode !== 'draw') {
      ctx.beginPath(); ctx.rect(0, 0, plotCv.clientWidth, plotCv.clientHeight);
      P.forEach((p, i) => { const [x, y] = v.toS(p.x, p.y); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
      ctx.closePath();
      ctx.fillStyle = 'rgba(100,110,125,0.16)'; ctx.fill('evenodd');
    }
    path();
    if (SZ.mode !== 'draw' && P.length >= 3) ctx.closePath();
    ctx.strokeStyle = cssVar('--accent'); ctx.lineWidth = on ? 2 : 1.2;
    if (!on) ctx.setLineDash([5, 4]);
    ctx.stroke(); ctx.setLineDash([]);
    if (SZ.mode === 'draw' && SZ.cursor && P.length) {
      const [ax, ay] = v.toS(P[P.length - 1].x, P[P.length - 1].y), [bx, by] = v.toS(SZ.cursor.x, SZ.cursor.y);
      ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke(); ctx.setLineDash([]);
    }
    if (SZ.mode) {
      ctx.fillStyle = cssVar('--panel');
      P.forEach((p, i) => {
        const [x, y] = v.toS(p.x, p.y);
        ctx.beginPath(); i === 0 && SZ.mode === 'draw' ? ctx.arc(x, y, 7, 0, 2 * Math.PI) : ctx.rect(x - 5, y - 5, 10, 10);
        ctx.fill(); ctx.stroke();
      });
    }
    ctx.restore();
  }
  if (typeof lockOverlay === 'function') lockOverlay(ctx, v);
}

$sz('btnSzDraw').onclick = () => szStart('draw');
$sz('btnSzEdit').onclick = () => szStart('edit');
$sz('btnSzDone').onclick = () => (SZ.mode ? szFinish() : null);
$sz('btnSzCancel').onclick = () => { szStop(); log('Safe zone left as it was.'); };
$sz('btnSzPen').onclick = () => {
  if (!S.dev) return log('Connect the arm (or the simulator) first, then move the pen to a corner of the paper.', 'warn');
  szAddPoint({ x: S.pos.x, y: S.pos.y });
  log(`Corner added at the pen: X ${S.pos.x.toFixed(1)}, Y ${S.pos.y.toFixed(1)} mm.`);
};
$sz('btnSzClear').onclick = () => { szApply(null, false, 'Safe zone removed — the green zone is the limit again. (Undo puts it back.)'); };
$sz('btnSzUndo').onclick = () => { const u = SZ.undo; if (!u) return; SZ.undo = null; S.safe = u; szSave(); for (const o of S.plot.objects) o.targetsKey = ''; szInfo(); if (S.plot.objects.length) buildPlot({ quiet: true }); else drawPlot(); if (typeof lockZoneChanged === 'function') lockZoneChanged(); log('Safe zone put back.'); };
$sz('sz-on').onchange = e => { if (S.safe.poly) szApply(S.safe.poly, e.target.checked, e.target.checked ? 'Safe zone on.' : 'Safe zone off — the green zone is the limit.'); };
$sz('sz-paper').onchange = e => { const v = e.target.value; e.target.value = ''; if (v) szPaper(v); };

/* ----- paper height: re-set the pen for a new sheet, or a sheet at another height ----- */
// Saved heights: [{ name, z }] (pen-down Z in mm), so a sheet on a board can be picked again later.
const PH = { list: [] };
function phLoad() { try { const a = JSON.parse(localStorage.getItem('magician-paper-heights') || '[]'); PH.list = Array.isArray(a) ? a.filter(h => h && h.name && Number.isFinite(h.z)) : []; } catch (e) { PH.list = []; } }
function phSave() { try { localStorage.setItem('magician-paper-heights', JSON.stringify(PH.list)); } catch (e) {} }
function phRender() {
  const L = S.limits, sel = $sz('ph-saved'), cur = sel.value;
  $sz('ph-now').textContent = L.penSet ? `Pen down at ${L.zDown.toFixed(1)} mm, up at ${L.zUp.toFixed(1)} mm` : 'Pen height not set yet';
  sel.innerHTML = '<option value="">Saved heights…</option>' + PH.list.map((h, i) => `<option value="${i}">${h.name.replace(/[<&]/g, '')} — ${h.z.toFixed(1)} mm</option>`).join('');
  if (cur && PH.list[+cur]) sel.value = cur;
  $sz('btnPhUse').disabled = $sz('btnPhDel').disabled = !sel.value;
  $sz('btnPhSave').disabled = !L.penSet;
}
// New pen-down height: the limits for that height (from the geometry once calibrated), then the
// zone, placements and lock area follow.
function phApply(zPaper, label) {
  if (S.running) return log('Wait until the drawing has finished.', 'warn');
  let L;
  if (S.model && S.model.ok) {
    L = autoLimits(S.model, zPaper, S.pos);
    if (!L) return log(`The arm cannot draw usefully at ${zPaper} mm. Check the height.`, 'err');
  } else {
    const d = zPaper - S.limits.zDown;
    L = { zDown: zPaper, zUp: Math.min(S.limits.zMax, zPaper + Math.max(5, S.limits.zUp - S.limits.zDown)), zMin: Math.min(S.limits.zMin, zPaper - 1) };
    if (Math.abs(d) > 40) return log('That is far from the current height — calibrate first (Setup → Auto-calibrate).', 'warn');
  }
  S.limits = { ...S.limits, ...L, penSet: true };
  writeSetup(); saveSettings();
  log(`Pen height: ${label} — pen down at ${S.limits.zDown} mm, up at ${S.limits.zUp} mm. The green zone is updated for this height.`, 'ok');
  phRender();
  for (const o of S.plot.objects) o.targetsKey = '';
  drawAll();
  if (typeof lockZoneChanged === 'function') lockZoneChanged();
}
// Re-set by touching the new paper: the pen goes above the middle of the allowed area, then the
// calibration dialog's last step (lower it until it touches, "This is the paper").
async function phReset() {
  if (!S.dev) return log('Connect the arm (or start the simulator) first.', 'warn');
  if (S.running) return log('A job is running. Press STOP first.', 'warn');
  if (!(S.model && S.model.ok)) { log('The arm is not calibrated yet — doing the full calibration (it ends with the pen height).', 'warn'); return openAutoCal(); }
  try {
    const R = allowedRegion(), z = drawZone();
    let c = { x: (z.rIn + z.rOut) / 2, y: z.pq ? zoneCentreY(z) : 0 };
    if (!R.empty && !regionHas(R, c.x, c.y)) { let best = null; for (const r of R.rings) for (const p of r.P) if (!best || Math.hypot(p.x - c.x, p.y - c.y) < Math.hypot(best.x - c.x, best.y - c.y)) best = p; if (best) c = regionProject(R, best.x + (c.x - best.x) * 0.1, best.y + (c.y - best.y) * 0.1) || c; }
    const zAbove = Math.min(S.limits.zMax, Math.max(S.limits.zUp, S.limits.zDown + 25));
    AC.open = true;                             // calibration: the safety lock lets these moves through
    document.getElementById('autocal').hidden = false;
    AC.reset = true; acSet('measuring', 'Moving the pen above the middle of the paper area…');
    await acMoveAndWait(c.x, c.y, zAbove);
    acSet('pen');
  } catch (e) { acSet('error', e.message); }
}
function phSaveCurrent() {
  const name = ($sz('ph-name').value || '').trim().slice(0, 40);
  if (!S.limits.penSet) return log('Set the pen height first.', 'warn');
  if (!name) { $sz('ph-name').focus(); return log('Type a name for this height first (for example "Table" or "Board 18 mm").', 'warn'); }
  const z = S.limits.zDown, i = PH.list.findIndex(h => h.name.toLowerCase() === name.toLowerCase());
  if (i >= 0) PH.list[i].z = z; else PH.list.push({ name, z });
  phSave(); $sz('ph-name').value = ''; phRender();
  $sz('ph-saved').value = String(i >= 0 ? i : PH.list.length - 1); phRender();
  log(`Saved the paper height "${name}" (${z.toFixed(1)} mm).`, 'ok');
}
$sz('btnPenReset').onclick = phReset;
$sz('btnPhSave').onclick = phSaveCurrent;
$sz('ph-name').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); phSaveCurrent(); } });
$sz('ph-saved').onchange = phRender;
$sz('btnPhUse').onclick = () => { const h = PH.list[+$sz('ph-saved').value]; if (h) phApply(h.z, `"${h.name}"`); };
$sz('btnPhDel').onclick = () => { const i = +$sz('ph-saved').value, h = PH.list[i]; if (!h) return; PH.list.splice(i, 1); phSave(); $sz('ph-saved').value = ''; phRender(); log(`Removed the saved height "${h.name}".`); };

/* ----- clear the plotter: every object and every red line ----- */
const PT = { clearArmed: 0, cleared: null, lastSheet: [], copies: null };
function clearPlotter() {
  if (S.running) return log('Stop the drawing first.', 'warn');
  const b = $sz('btnPlotClear');
  if (!S.plot.objects.length && !S.paper.jobs.length && !PL.frame) return log('The plotter is already clear.');
  if (!PT.clearArmed) {
    PT.clearArmed = setTimeout(() => { PT.clearArmed = 0; b.textContent = 'Clear plotter'; b.classList.remove('on'); }, 3500);
    b.textContent = 'Click again to clear everything'; b.classList.add('on');
    return;
  }
  clearTimeout(PT.clearArmed); PT.clearArmed = 0; b.textContent = 'Clear plotter'; b.classList.remove('on');
  PT.cleared = { objects: S.plot.objects.slice(), sel: S.plot.sel, jobs: S.paper.jobs.slice() };
  if (S.paper.jobs.length) PT.lastSheet = S.paper.jobs.slice();
  const n = S.plot.objects.length, j = S.paper.jobs.length;
  S.plot.objects = []; S.plot.sel = null; S.plot.placeVer++;
  S.paper.jobs = []; PL.frame = null;
  const fn = document.getElementById('plot-file-name'); if (fn) fn.textContent = 'no file loaded';
  onSelectionChange();
  buildPlot({ quiet: true });
  $sz('btnPlotUndo').hidden = false;
  redrawInfo();
  log(`Plotter cleared: ${n} object${n === 1 ? '' : 's'} and ${j ? 'the drawn lines' : 'no drawn lines'} removed (Undo clear puts them back; Redraw can still draw the last sheet again).`);
}
function undoClearPlotter() {
  const c = PT.cleared;
  if (!c || S.running) return;
  PT.cleared = null;
  S.plot.objects = c.objects.concat(S.plot.objects); S.plot.sel = c.sel; S.plot.placeVer++;
  S.paper.jobs = c.jobs.concat(S.paper.jobs);
  $sz('btnPlotUndo').hidden = true;
  onSelectionChange();
  buildPlot({ quiet: true });
  redrawInfo();
  log('Plotter put back as it was.', 'ok');
}
$sz('btnPlotClear').onclick = clearPlotter;
$sz('btnPlotUndo').onclick = undoClearPlotter;
// New sheet keeps what was drawn, so Redraw can draw it on the fresh sheet (this runs before the
// New sheet handler of part 37 clears the red lines).
$sz('btnNewSheet').addEventListener('click', () => { const keep = S.paper.jobs.filter(j => !j.active && (j.done || j.k > 0)); if (keep.length) PT.lastSheet = keep; setTimeout(redrawInfo, 0); }, true);

/* ----- redraw: draw again what has been drawn (more copies, or over the same lines) ----- */
// The moves of the drawn jobs (only the part drawn, for a stopped one), from the first pen-down move.
function redrawMoves(jobs) {
  const L = S.limits, penZ = L.zDown + 0.6, out = [];
  for (const j of jobs) {
    const n = j.done ? j.cmds.length : Math.min(j.cmds.length, j.k + 1);
    let first = -1;
    for (let i = 0; i < n; i++) if (j.cmds[i].x !== undefined && j.cmds[i].z <= penZ) { first = i; break; }
    if (first < 0) continue;
    const head = j.cmds[first], lift = Math.max(L.zUp, head.z);
    out.push({ travelTo: { x: head.x, y: head.y, z: lift } });
    for (let i = first; i < n; i++) out.push(j.cmds[i]);
    const last = j.cmds[n - 1];
    if (last.x !== undefined && last.z < L.zUp - 0.5) out.push({ x: last.x, y: last.y, z: L.zUp, mode: 2 });
  }
  return out;
}
// Planned moves from the arm's position: lift, travel to each part (round inside the safe zone /
// round the base), lower and draw.
function redrawPlan(jobs, start) {
  const L = S.limits, route = zoneTravelFor(), core = drawZone().rIn, cmds = [];
  let at = { ...start };
  for (const c of redrawMoves(jobs)) {
    if (c.travelTo) {
      const t = c.travelTo;
      if (at.z < t.z - 0.5) { cmds.push({ x: at.x, y: at.y, z: t.z, mode: 2 }); at = { ...at, z: t.z }; }
      for (const w of route ? route(at, t) : arcWaypoints(at, t, core)) cmds.push({ x: w.x, y: w.y, z: t.z, mode: 2 });
      cmds.push({ x: t.x, y: t.y, z: t.z, mode: 2 }); at = { ...t };
      continue;
    }
    cmds.push({ ...c }); if (c.x !== undefined) at = { x: c.x, y: c.y, z: c.z };
  }
  return cmds;
}
function redrawSource() {
  const shown = S.paper.jobs.filter(j => !j.active && (j.done || j.k > 0));
  if (shown.length) return { jobs: shown, fromSheet: 'shown' };
  if (PT.lastSheet.length) return { jobs: PT.lastSheet, fromSheet: 'last' };
  return null;
}
function redrawInfo() {
  const s = redrawSource(), el = $sz('rd-info');
  if (!el) return;
  $sz('btnRedraw').disabled = !s || S.running;
  el.textContent = !s ? 'Nothing drawn yet.' : s.fromSheet === 'shown' ? `Draws again the ${s.jobs.length === 1 ? 'red lines' : `red lines of ${s.jobs.length} drawings`} on the map.` : 'Draws the last sheet again (its lines were cleared from the map).';
}
async function redraw() {
  if (!S.dev) return log('Connect the arm (or start the simulator) first.', 'warn');
  if (S.running) return log('A job is running.', 'warn');
  if (!penReady()) return;
  const src = redrawSource();
  if (!src) return log('Nothing has been drawn on this sheet yet — draw something first.', 'warn');
  const copies = Math.max(1, Math.min(50, parseInt($sz('rd-copies').value, 10) || 1)), fresh = $sz('rd-fresh').checked;
  const jobs = src.jobs.slice(), smooth = jobs.some(j => j.cmds.some(c => c.kind === 'cp'));
  for (let k = 1; k <= copies; k++) {
    if (k > 1 && fresh) {
      const go = await redrawAsk(k - 1, copies);
      if (!go) { log(`Redraw stopped after copy ${k - 1} of ${copies}.`, 'warn'); break; }
      PT.lastSheet = S.paper.jobs.filter(j => !j.active && (j.done || j.k > 0));
      S.paper.jobs = S.paper.jobs.filter(j => j.active);           // a fresh sheet: the red lines start again
      drawPlot();
    }
    const start = { ...(S.cmd || S.pos) };
    let planned;
    try { planned = redrawPlan(jobs, start); } catch (e) { log(e.message, 'err'); break; }
    if (!planned.length) { log('There is nothing to draw again.', 'warn'); break; }
    const ok = await runPlannedDrawing(copies > 1 ? `Redraw ${k} of ${copies}` : 'Redraw', planned, start, smooth);
    if (!ok) break;
  }
  redrawInfo();
}
// Between copies: wait for a fresh sheet.
function redrawAsk(done, total) {
  return new Promise(res => {
    const m = $sz('rdAsk');
    $sz('rdAskText').textContent = `Copy ${done} of ${total} is drawn. Take it out, put a fresh sheet in the same place, then press Continue.`;
    m.hidden = false;
    const fin = v => { m.hidden = true; $sz('btnRdGo').onclick = $sz('btnRdStop').onclick = null; res(v); };
    $sz('btnRdGo').onclick = () => fin(true);
    $sz('btnRdStop').onclick = () => fin(false);
  });
}
$sz('btnRedraw').onclick = () => redraw().catch(e => log('Redraw: ' + e.message, 'err'));
setInterval(redrawInfo, 1000);

szLoad(); phLoad();
szInfo(); phRender(); redrawInfo();
