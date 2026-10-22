/* ===================== JOB RUNNER & TABS ===================== */
async function runJob(name, cmds, progressEl, opts = {}) {
  if (!S.dev) throw new Error('Not connected — connect or start the simulator first.');
  if (S.running) throw new Error('Another job is already running. Press STOP first.');
  if (!cmds.length) throw new Error('Nothing to run.');
  if (S.alarm.length) throw new Error('Alarm active — clear it first (red bar).');
  S.running = true;
  S.live = false; setLiveButton();
  log(`${name}: ${cmds.length} moves…`);
  S.paused = false; renderPause();
  if (typeof syncPlaceInputs === 'function') syncPlaceInputs();
  if (typeof renderObjectList === 'function') renderObjectList();
  if (typeof syncTextUI === 'function') syncTextUI();
  try {
    await S.dev.setSpeed(opts.speed ?? S.speed.draw, S.speed.accel);
    if (opts.before) await opts.before();
    await S.dev.runQueue(cmds, p => { if (progressEl) progressEl.style.width = (p * 100).toFixed(0) + '%'; }, opts.window ?? 8, opts.track || null);
    const last = cmds[cmds.length - 1];
    if (last.x !== undefined) S.cmd = { x: last.x, y: last.y, z: last.z };
    log(`${name}: finished.`, 'ok');
    return true;
  } catch (e) {
    if (e.message !== 'Stopped') log(`${name} stopped: ${e.message}`, 'warn');
    return false;
  } finally {
    await S.dev.setSpeed(S.speed.live, S.speed.accel).catch(() => {});
    S.running = false; S.paused = false; renderPause();
    if (typeof syncPlaceInputs === 'function') syncPlaceInputs();
    if (typeof renderObjectList === 'function') renderObjectList();
    if (typeof syncTextUI === 'function') syncTextUI();
    if (progressEl) setTimeout(() => progressEl.style.width = '0%', 800);
  }
}

function showTab(name) {
  for (const t of ['mouse', 'plot', 'rec', 'dance', 'imit', 'react', 'setup']) {
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
    document.getElementById('nav-' + t).classList.toggle('active', t === name);
  }
  if (name === 'imit' || name === 'react') placeCamera(name);
  if (name === 'imit') updateImitUI();
  if (name === 'plot' && typeof libEnsureGrid === 'function') libEnsureGrid();
  drawAll();
}

function drawAll() {
  if (document.getElementById('tab-mouse').classList.contains('active')) drawMouse();
  if (document.getElementById('tab-plot').classList.contains('active')) drawPlot();
  if (document.getElementById('tab-rec').classList.contains('active')) drawRec();
  if (document.getElementById('tab-dance').classList.contains('active')) drawDance();
  if (document.getElementById('tab-imit').classList.contains('active')) drawAir();
  if (document.getElementById('tab-react').classList.contains('active')) drawEyes();
}

/* ===================== PLOTTER ===================== */
const plotCv = document.getElementById('plotCanvas');

function plotOpt(id) { const el = document.getElementById(id); return el.type === 'checkbox' ? el.checked : el.value; }
const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const plotPad = () => Math.max(0, parseFloat(plotOpt('plot-tol')) || 0);   // simplification can shift a line this much

// Radial range usable between pen-down and pen-up heights. From the arm's geometry once
// auto-calibrated; otherwise the reach band in Setup.
function drawBand() {
  if (S.model && S.model.ok) {
    const b = reachBand(S.model, S.limits.zDown - 0.5, S.limits.zUp + 0.5, 2);
    if (b) return { minR: b.rIn, maxR: b.rOut, fromModel: true };
  }
  return { minR: S.limits.minR, maxR: S.limits.maxR, fromModel: false };
}

// The green zone: where a drawing may go. Reachable at every height between pen-down and pen-up,
// inside the base-angle limits, less the safety margin on every side.
function drawZone() {
  const b = drawBand(), L = S.limits, margin = Math.max(0, parseFloat(plotOpt('plot-margin')) || 0);
  const rIn = b.minR + margin, rOut = b.maxR - margin, dth = rIn > 0 ? margin / rIn / RAD : 0;
  return { rIn, rOut, thMin: L.thMin + dth, thMax: L.thMax - dth, margin, band: b, fromModel: b.fromModel };
}

// Largest upright rectangle in the green zone (the air-drawing area).
function plotRect() {
  const z = drawZone(), r = maxReachRect(z.rIn, z.rOut, 0);
  if (!(r.area > 0)) throw new Error('Reach area too small for this margin');
  return { cx: (r.x0 + r.x1) / 2, cy: 0, w: r.x1 - r.x0, h: 2 * r.h, label: 'largest rectangle' };
}

/* ----- objects on the paper -----
   S.plot.objects: every drawing and text placed on the paper, in the order they were added (a later
   one is on top when clicking). Each has its own normalised drawing (sketch), placement {cx, cy, size,
   angle, mirror}, shading settings and a "use" flag (drawn when Draw is pressed). S.plot.sel is the
   selected one's id: the placement, text and shading controls act on it. S.plot.sketch, .place,
   .placeOk and .label are the selected object's. */
let OBJ_SEQ = 0;
const PL = { drag: null, base: null, hover: null, lastHit: null, zt: 0, kt: 0, order: new Map(), frame: null };

function selObj() { const id = S.plot.sel; return id == null ? null : S.plot.objects.find(o => o.id === id) || null; }
function objById(id) { return S.plot.objects.find(o => o.id === id) || null; }
for (const k of ['sketch', 'place', 'placeOk', 'label']) {
  Object.defineProperty(S.plot, k, {
    get() { const o = selObj(); return o ? o[k] : (k === 'placeOk' ? true : null); },
    set(v) { const o = selObj(); if (o) o[k] = v; },
    enumerable: true, configurable: true,
  });
}
Object.defineProperty(S.plot, 'order', { get() { const o = selObj(); return o ? o.orderRef : null; }, enumerable: true, configurable: true });

function newObject(kind, sk, label, extra = {}) {
  const o = { id: ++OBJ_SEQ, kind, label: label || (kind === 'text' ? 'Text' : 'Drawing'), source: null, sketch: sk, place: null, placeOk: true,
              use: true, probe: null, probeKey: '', targets: null, targetsKey: '', orderRef: null, ...extra };
  if (typeof shadeInit === 'function') shadeInit(o);
  return o;
}
function resetObjCaches(o) {
  o.probe = null; o.probeKey = ''; o.targets = null; o.targetsKey = ''; o.orderRef = null;
  if (typeof shadeInit === 'function') { o.shT = null; o.shTkey = ''; o.shCache = null; o.shOv = new Map(); o.shOvVer = (o.shOvVer || 0) + 1; }
}

// The object turned for a rotation (size 1, centre 0) for the fit checks; cached per object.
function objProbe(o, angle = o.place.angle, mirror = o.place.mirror) {
  const key = `${o.sketch.id}|${angle}|${mirror ? 1 : 0}`;
  if (o.probeKey !== key) { o.probe = placementProbe(o.sketch, angle, mirror); o.probeKey = key; }
  return o.probe;
}
// Roomiest spots for the object at a rotation: [on the centre line, anywhere]. Cached.
function objTargets(o, angle = o.place.angle, mirror = o.place.mirror) {
  const z = drawZone(), pad = plotPad(), P = objProbe(o, angle, mirror), key = `${o.probeKey}|${zoneKey(z)}|${pad}`;
  if (o.targetsKey !== key) {
    o.targets = [bestPlacement(P, z, { centreLine: true, pad }), bestPlacement(P, z, { pad })];
    o.targetsKey = key;
  }
  return o.targets;
}
function plProbe() { const o = selObj(); return o ? objProbe(o) : null; }
function placeTargets() { const o = selObj(); return o ? objTargets(o) : [null, null]; }

// Placement asked for → the nearest one that fits (moved or, only if needed, shrunk).
function fitPlaceFor(o, want) {
  const w = { cx: want.cx, cy: want.cy, size: want.size, angle: want.angle, mirror: !!want.mirror };
  return fixPlacement(o.sketch, w, drawZone(), { pad: plotPad(), probe: objProbe(o, w.angle, w.mirror), targets: objTargets(o, w.angle, w.mirror) });
}
function fitPlace(want) { const o = selObj(); return o ? fitPlaceFor(o, want) : null; }

function setPlaceFor(o, pl) {
  o.place = { cx: pl.cx, cy: pl.cy, size: pl.size, angle: pl.angle, mirror: !!pl.mirror };
  S.plot.placeVer++;
  o.placeOk = probeFits(objProbe(o), pl.cx, pl.cy, pl.size, drawZone(), plotPad());
  if (o.kind === 'text' && o.text) o.text.height = pl.size / o.sketch.srcBox.L;     // letter height follows the size
  if (o === selObj()) {
    syncPlaceInputs();
    if (o.kind === 'text' && typeof syncTextUI === 'function') syncTextUI();
  }
}
function setPlace(pl) { const o = selObj(); if (o) setPlaceFor(o, pl); }

function defaultPlacement(sk) {
  const z = drawZone(), P = placementProbe(sk, 0, false), pad = plotPad();
  const b = bestPlacement(P, z, { centreLine: true, pad }) || bestPlacement(P, z, { pad });
  if (!b) return { cx: (z.rIn + z.rOut) / 2, cy: 0, size: 20, angle: 0, mirror: false };
  return { cx: b.cx, cy: b.cy, size: Math.max(5, Math.floor(b.size * 0.9)), angle: 0, mirror: false };
}

// Box (robot mm) round an object's frame, grown by `gap` on every side.
function frameBox(sk, pl, gap = 0) {
  const fr = placeFrame(sk, pl);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of fr) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; }
  return { x0: x0 - gap, y0: y0 - gap, x1: x1 + gap, y1: y1 + gap };
}
const boxOverlapArea = (a, b) => Math.max(0, Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0)) * Math.max(0, Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0));

// A spot in the green zone where the object fits at `size`, clear of the others if possible
// (3 mm apart), preferring the middle of the zone. {cx, cy, ov} — ov = overlap with the others (mm²).
function freeSpot(o, size, others, angle = 0, mirror = false) {
  const z = drawZone(), pad = plotPad(), P = objProbe(o, angle, mirror);
  if (!(z.rOut > z.rIn) || !(size > 0)) return null;
  const boxes = others.filter(x => x.place).map(x => frameBox(x.sketch, x.place, 3));
  const nR = 14, rs = (z.rOut - z.rIn) / nR, mid = (z.rIn + z.rOut) / 2;
  let best = null;
  for (let i = 0; i <= nR; i++) {
    const r = z.rIn + i * rs;
    for (let th = 0; th <= Math.max(Math.abs(z.thMin), Math.abs(z.thMax)); th += 4) {
      for (const a of th ? [th, -th] : [0]) {
        if (a < z.thMin || a > z.thMax) continue;
        const cx = r * Math.cos(a * RAD), cy = r * Math.sin(a * RAD);
        if (!probeFits(P, cx, cy, size, z, pad)) continue;
        const b = frameBox(o.sketch, { cx, cy, size, angle, mirror }, 0);
        let ov = 0;
        for (const q of boxes) ov += boxOverlapArea(b, q);
        const score = ov * 1000 + Math.abs(a) * 0.6 + Math.abs(r - mid) * 0.25;
        if (!best || score < best.score) best = { cx, cy, ov, score };
      }
    }
  }
  return best;
}

// Where a new object goes: the first drawing as big as the zone allows (as before); later ones
// smaller, in free space beside what is already there; text at its letter height.
function placeNew(o) {
  const others = S.plot.objects.filter(x => x !== o && x.place);
  if (o.kind === 'text') {
    const angle = o.text && Number.isFinite(o.text.angle) ? o.text.angle : 0, size = o.text.height * o.sketch.srcBox.L;
    const spot = freeSpot(o, size, others, angle);
    if (spot) return { cx: spot.cx, cy: spot.cy, size, angle, mirror: false };
    const t = objTargets(o, angle, false).filter(Boolean)[0], z = drawZone();
    return t ? { cx: t.cx, cy: t.cy, size, angle, mirror: false } : { cx: (z.rIn + z.rOut) / 2, cy: 0, size, angle, mirror: false };
  }
  if (!others.length) return defaultPlacement(o.sketch);
  const T = objTargets(o, 0, false).filter(Boolean), big = T.length ? Math.max(...T.map(t => t.size)) : 40;
  for (const f of [0.5, 0.38, 0.28, 0.2]) {
    const size = Math.max(10, Math.floor(big * f)), spot = freeSpot(o, size, others);
    if (spot && spot.ov === 0) return { cx: spot.cx, cy: spot.cy, size, angle: 0, mirror: false };
  }
  const size = Math.max(10, Math.floor(big * 0.4)), spot = freeSpot(o, size, others);
  return spot ? { cx: spot.cx, cy: spot.cy, size, angle: 0, mirror: false } : defaultPlacement(o.sketch);
}

function selectObject(id) {
  const o = id == null ? null : objById(id);
  const nid = o ? o.id : null;
  if (S.plot.sel === nid) return;
  S.plot.sel = nid;
  onSelectionChange();
}
// Everything that shows the selected object follows the selection.
function onSelectionChange() {
  syncPlaceInputs();
  if (typeof syncShadeUI === 'function') syncShadeUI();
  if (typeof syncTextUI === 'function') syncTextUI();
  if (typeof libSyncMark === 'function') libSyncMark();
  if (typeof renderObjectList === 'function') renderObjectList();
  drawPlot();
}

// Adds an object (selected), placed where asked or in free space, and rebuilds the path.
function addObject(o, pl) {
  S.plot.objects.push(o);
  S.plot.sel = o.id;
  setPlaceFor(o, pl || placeNew(o));
  onSelectionChange();
  return buildPlot();
}

function deleteObject(o) {
  const i = S.plot.objects.indexOf(o);
  if (i < 0 || S.running) return;
  if (typeof objTrash === 'function') objTrash([o]);
  S.plot.objects.splice(i, 1);
  if (S.plot.sel === o.id) { const nx = S.plot.objects[Math.min(i, S.plot.objects.length - 1)]; S.plot.sel = nx ? nx.id : null; }
  S.plot.placeVer++;
  log(`Removed ${o.label} from the paper.`);
  onSelectionChange();
  buildPlot({ quiet: true });
}

// New drawing for the Plotter: added as a new object. opts.source: picture name — the selected
// object from the same picture (or, with opts.update, any object from it) is replaced instead,
// keeping its scale and place; opts.robotMm: strokes already in robot millimetres (air drawing).
function setDrawing(strokes, label, opts = {}) {
  const sketchStrokes = opts.robotMm ? strokes.map(s => s.map(p => ({ x: -p.y, y: -p.x }))) : strokes;
  const sk = prepareSketch(sketchStrokes, opts.source || null);
  sk.shapes = !opts.robotMm && Array.isArray(strokes.shapes) ? strokes.shapes : null;   // fills, for shading
  const so = selObj();
  const same = opts.source ? (so && so.kind === 'drawing' && so.source === opts.source ? so
    : opts.update ? [...S.plot.objects].reverse().find(x => x.kind === 'drawing' && x.source === opts.source) : null) : null;
  if (same) {
    const prev = same.sketch, prevPl = same.place;
    const k = prevPl.size / prev.srcBox.L, d = placeLinear(prevPl.angle, prevPl.mirror)({ x: sk.srcBox.cx - prev.srcBox.cx, y: sk.srcBox.cy - prev.srcBox.cy });
    same.sketch = sk; same.label = label; resetObjCaches(same);
    S.plot.sel = same.id;
    setPlaceFor(same, { ...prevPl, cx: prevPl.cx + k * d.x, cy: prevPl.cy + k * d.y, size: k * sk.srcBox.L });
    onSelectionChange();
    return buildPlot();
  }
  const o = newObject('drawing', sk, label, { source: opts.source || null });
  const pl = opts.robotMm ? { cx: -sk.srcBox.cy, cy: -sk.srcBox.cx, size: sk.srcBox.L, angle: 0, mirror: false } : null;
  return addObject(o, pl);
}

async function loadSvgText(text, label) {
  const raw = svgToStrokes(text);
  if (!raw.length) throw new Error('No drawable outlines found in this SVG (text and fills-only shapes are not converted).');
  document.getElementById('plot-file-name').textContent = label;
  log(`Loaded ${label}: ${raw.length} raw strokes.`, 'ok');
  setDrawing(raw, label);
}

// Pen lines of one object in its own units (outlines and/or shading), in a good order. The order
// is worked out once per drawing (it only depends on the drawing's own shape), so moving, turning
// or resizing it afterwards is instant; copies of a drawing share it.
function objectOrder(o, budget, reorder) {
  const pl = o.place, shade = typeof shadeFor === 'function' ? shadeFor(o, pl.size) : null;
  const outlinesOn = !shade || o.shade.outline !== false;
  const all = shade ? (outlinesOn ? o.sketch.strokes : []).concat(shade.strokes) : o.sketch.strokes;
  if (!all.length) return null;
  const key = `${o.sketch.id}|${budget}|${shade ? shade.key + '|' + (outlinesOn ? 1 : 0) : 'plain'}`;
  let ord = PL.order.get(key);
  if (reorder || !ord) {
    const index = new Map(all.map((s, i) => [s, i]));
    const seq0 = orderStrokes(all, placeInverse(pl)(S.cmd || S.pos), budget);
    ord = { key, all, seq: seq0.map(e => ({ i: index.get(e.pts), rev: e.rev })) };
    PL.order.delete(key); PL.order.set(key, ord);
    while (PL.order.size > 40) PL.order.delete(PL.order.keys().next().value);
  }
  o.orderRef = ord;
  return ord;
}

// Objects one after another: always the nearest next one, drawn forwards or backwards.
function chainObjects(parts, start) {
  const rem = parts.map(p => {
    const a = p.seq[0], b = p.seq[p.seq.length - 1];
    return { ...p, first: a.rev ? a.pts[a.pts.length - 1] : a.pts[0], last: b.rev ? b.pts[0] : b.pts[b.pts.length - 1] };
  });
  const out = [], order = [];
  let cur = start;
  while (rem.length) {
    let bi = 0, bd = Infinity, brev = false;
    rem.forEach((p, i) => {
      const d1 = Math.hypot(cur.x - p.first.x, cur.y - p.first.y), d2 = Math.hypot(cur.x - p.last.x, cur.y - p.last.y);
      if (d1 < bd) { bd = d1; bi = i; brev = false; }
      if (d2 < bd) { bd = d2; bi = i; brev = true; }
    });
    const p = rem.splice(bi, 1)[0];
    if (brev) { for (let k = p.seq.length - 1; k >= 0; k--) out.push({ pts: p.seq[k].pts, rev: !p.seq[k].rev }); cur = p.first; }
    else { for (const e of p.seq) out.push(e); cur = p.last; }
    order.push(p.o.id);
  }
  return { seq: out, order };
}

// Placements → robot path for every ticked object.
function buildPlot(opts = {}) {
  const objs = S.plot.objects;
  if (!objs.length) {
    S.plot.ops = null; S.plot.stats = null; S.plot.drawnIds = [];
    if (typeof paperAutosave === 'function') paperAutosave();
    document.getElementById('plot-stats').textContent = 'Load a drawing, a picture or add text to start.';
    if (!opts.quiet) log('Load a drawing first.', 'warn');
    if (typeof renderShadeStats === 'function') renderShadeStats();
    drawPlot();
    return false;
  }
  try {
    const tol = parseFloat(plotOpt('plot-tol')), minLen = parseFloat(plotOpt('plot-minlen'));
    const join = parseFloat(plotOpt('plot-join')), budget = parseFloat(plotOpt('plot-opt'));
    if (![tol, minLen, join, budget].every(Number.isFinite)) throw new Error('Check the optimisation values');
    const z = drawZone(), parts = [];
    for (const o of objs) {
      const fixed = fitPlaceFor(o, o.place);
      if (!fixed) {
        o.placeOk = false;
        if (o.use) log(`${o.label} does not fit in the green zone at any size. Check the pen heights (Setup → Auto-calibrate) or lower the safety margin.`, 'err');
        continue;
      }
      if (fixed.fixed) {
        setPlaceFor(o, fixed);
        log(fixed.shrunk ? `${o.label} made smaller (${fixed.size.toFixed(0)} mm) so it fits in the green zone.` : `${o.label} moved so it fits inside the green zone.`, 'warn');
      }
      if (!o.use) continue;
      const ord = objectOrder(o, budget, opts.reorder);
      if (!ord) continue;
      const f = placeXform(o.place), seq = [];
      for (const e of ord.seq) {
        const c = cleanStrokes([ord.all[e.i].map(f)], tol, minLen);
        if (c.length) seq.push({ pts: c[0], rev: e.rev });
      }
      if (seq.length) parts.push({ o, seq });
    }
    if (!parts.length) {
      throw new Error(!objs.some(o => o.use) ? 'Nothing to draw — tick at least one object in the list above the map.'
        : objs.some(o => o.use && o.placeOk !== false) ? 'Nothing left after simplification — lower the minimum length, or turn the outlines on.'
        : 'Nothing fits in the green zone. Check the pen heights (Setup → Auto-calibrate) or lower the safety margin.');
    }
    const start = { ...(S.cmd || S.pos) }, ch = chainObjects(parts, start), seq = ch.seq;
    const ops = buildOps(seq, start, join);
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of parts) for (const q of placeFrame(p.o.sketch, p.o.place)) { x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x); y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y); }
    S.plot.strokes = seq.map(e => e.pts); S.plot.ops = ops; S.plot.start = start; S.plot.drawnIds = ch.order;
    S.plot.rect = { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, w: x1 - x0, h: y1 - y0 };
    S.plot.stats = opsStats(ops, start);
    S.plot.stats.split = travelSplit(ops, start, hopSettings().hopMax);
    S.plot.stats.count = seq.length;
    S.plot.stats.objects = parts.length;
    S.plot.stats.pointsBefore = parts.reduce((a, p) => a + p.o.sketch.points, 0);
    S.plot.stats.pointsAfter = seq.reduce((a, e) => a + e.pts.length, 0);
    S.plot.opsVer = S.plot.placeVer; S.plot.zoneKey = zoneKey(z);
    if (typeof paperAutosave === 'function') paperAutosave();
    renderPlotStats();
    if (typeof renderShadeStats === 'function') renderShadeStats();
    if (typeof renderObjectList === 'function') renderObjectList();
    drawPlot();
    return true;
  } catch (e) {
    S.plot.ops = null; S.plot.drawnIds = [];
    if (typeof paperAutosave === 'function') paperAutosave();
    log('Build failed: ' + e.message, 'err');
    document.getElementById('plot-stats').textContent = e.message;
    if (typeof renderObjectList === 'function') renderObjectList();
    drawPlot();
    return false;
  }
}

function renderPlotStats() {
  const s = S.plot.stats;
  if (!s) return;
  const drawn = (S.plot.drawnIds || []).map(objById).filter(Boolean);
  let what;
  if (drawn.length === 1) {
    const o = drawn[0], pl = o.place, sk = o.sketch, turn = pl.angle ? `, turned ${+pl.angle.toFixed(1)}°` : '';
    what = `${(sk.w * pl.size).toFixed(0)} × ${(sk.h * pl.size).toFixed(0)} mm${turn}${pl.mirror ? ', mirrored' : ''}`;
  } else what = `${drawn.length} objects`;
  const skipped = S.plot.objects.length - drawn.length;
  document.getElementById('plot-stats').textContent =
    `${what}${skipped > 0 ? ` (${skipped} not drawn)` : ''} · ${s.count} strokes · ${s.lifts} pen lifts · ` +
    `drawing ${s.draw.toFixed(0)} mm · travel ${s.travel.toFixed(0)} mm · est. ${estimateMinutes(s).toFixed(1)} min`;
}

// Pen hops in smooth mode: gaps up to hopMax mm are low rounded hops at the pen speed; longer ones
// lift fully and travel at the travel speed.
function hopSettings() {
  const n = (id, d) => { const v = parseFloat(plotOpt(id)); return Number.isFinite(v) ? v : d; };
  return { hopMin: Math.max(1, n('plot-hopmin', 3)), hopMax: Math.max(0, n('plot-hopmax', 40)), maxSeg: 3 };
}

// Pen-up travel split into short hops and long jumps (for the time estimate).
function travelSplit(ops, start, hopMax) {
  let hops = 0, jumps = 0, jumpCount = 0, prev = start;
  for (const op of ops) {
    const d = Math.hypot(op.x - prev.x, op.y - prev.y);
    if (!op.pen && d > 0.01) { if (d <= hopMax) hops += d; else { jumps += d; jumpCount++; } }
    prev = op;
  }
  return { hops, jumps, jumpCount };
}

function estimateMinutes(s) {
  const smooth = plotOpt('plot-motion') === 'smooth', vd = S.speed.draw || 30, vt = S.speed.travel || 100;
  if (!smooth || !s.split) return ((s.draw / vd) * 1.8 + s.travel / vd + s.lifts * 0.8) / 60;   // precise mode stops at points
  const { hops, jumps, jumpCount } = s.split;
  return ((s.draw / vd) * 1.1 + (hops / vd) * 1.4 + jumps / vt + jumpCount * 1.2) / 60;
}

/* ----- plotter canvas ----- */
function plotView() { return viewOf(plotCv, Math.max(S.limits.maxR, drawBand().maxR)); }

// Screen positions of an object's frame (TL, TR, BR, BL), centre and rotate knob.
function frameGeom(v, o = selObj()) {
  const sk = o.sketch, pl = o.place;
  const fr = placeFrame(sk, pl).map(p => v.toS(p.x, p.y)), c = v.toS(pl.cx, pl.cy);
  const top = [(fr[0][0] + fr[1][0]) / 2, (fr[0][1] + fr[1][1]) / 2];
  const up = placeLinear(pl.angle, pl.mirror)({ x: 0, y: -1 });       // drawing "up", robot frame
  const ux = -up.y, uy = -up.x, ul = Math.hypot(ux, uy) || 1;          // → screen
  return { fr, c, top, knob: [top[0] + 26 * ux / ul, top[1] + 26 * uy / ul] };
}

function drawZoneShape(ctx, v, z) {
  if (!(z.rOut > z.rIn)) return;
  const a1 = -Math.PI / 2 - z.thMax * RAD, a0 = -Math.PI / 2 - z.thMin * RAD;   // screen angles of the side limits
  ctx.beginPath();
  ctx.arc(v.bx, v.by, z.rOut * v.k, a1, a0);
  ctx.arc(v.bx, v.by, Math.max(0, z.rIn) * v.k, a0, a1, true);
  ctx.closePath();
  ctx.fillStyle = cssVar('--zone'); ctx.fill();
  ctx.strokeStyle = cssVar('--zoneLine'); ctx.lineWidth = 1.5; ctx.stroke();
}

function drawOpsPaths(ctx, v, ops, start, ink, muted) {
  ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  ctx.strokeStyle = muted; ctx.lineWidth = 0.8; ctx.setLineDash([3, 3]); ctx.beginPath();
  let prev = start;
  for (const op of ops) {
    if (!op.pen) { const [x1, y1] = v.toS(prev.x, prev.y), [x2, y2] = v.toS(op.x, op.y); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); }
    prev = op;
  }
  ctx.stroke(); ctx.setLineDash([]);
  ctx.strokeStyle = ink; ctx.lineWidth = 1.4; ctx.beginPath();
  prev = start; let open = false;
  for (const op of ops) {
    if (op.pen) {
      if (!open) { const [x1, y1] = v.toS(prev.x, prev.y); ctx.moveTo(x1, y1); open = true; }
      const [x2, y2] = v.toS(op.x, op.y); ctx.lineTo(x2, y2);
    } else open = false;
    prev = op;
  }
  ctx.stroke();
}

// Fast preview while the drawing is being moved, turned or resized.
function drawPreview(ctx, v, P, pl, color) {
  ctx.strokeStyle = color; ctx.lineWidth = 1.4; ctx.lineJoin = 'round'; ctx.beginPath();
  for (const c of P.chunks) {
    const a = c.a;
    for (let i = 0; i < a.length; i += 2) {
      const [x, y] = v.toS(pl.cx + pl.size * a[i], pl.cy + pl.size * a[i + 1]);
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
  }
  ctx.stroke();
}

// A light dotted frame round an object the pointer is over (click to select it).
function drawHoverFrame(ctx, v, o) {
  const g = frameGeom(v, o);
  ctx.save(); ctx.strokeStyle = cssVar('--accent'); ctx.globalAlpha = 0.55; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
  ctx.beginPath(); g.fr.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.stroke();
  ctx.restore();
}

function drawFrame(ctx, v, ok, handles) {
  const g = frameGeom(v), col = ok ? cssVar('--accent') : cssVar('--err');
  ctx.strokeStyle = col; ctx.lineWidth = 1.2; ctx.setLineDash([5, 4]);
  ctx.beginPath(); g.fr.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.stroke();
  ctx.setLineDash([]);
  if (!handles) return;
  ctx.beginPath();
  ctx.moveTo(g.c[0] - 5, g.c[1]); ctx.lineTo(g.c[0] + 5, g.c[1]); ctx.moveTo(g.c[0], g.c[1] - 5); ctx.lineTo(g.c[0], g.c[1] + 5);
  ctx.moveTo(g.top[0], g.top[1]); ctx.lineTo(g.knob[0], g.knob[1]);
  ctx.stroke();
  ctx.fillStyle = cssVar('--panel'); ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.arc(g.knob[0], g.knob[1], 6, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
  for (const [x, y] of g.fr) { ctx.fillRect(x - 4.5, y - 4.5, 9, 9); ctx.strokeRect(x - 4.5, y - 4.5, 9, 9); }
}

// What has been drawn on this sheet, in red: finished jobs in full, the running one up to the pen.
function drawPaper(ctx, v) {
  if (!S.paper.jobs.length) return;
  ctx.save();
  ctx.strokeStyle = cssVar('--laser'); ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath();
  for (const job of S.paper.jobs) {
    const last = job.done ? job.cmds.length - 1 : Math.min(job.k, job.cmds.length - 1);
    let pen = false;
    for (let j = 0; j <= last; j++) {
      const a = j ? job.cmds[j - 1] : job.start, b = job.cmds[j];
      if (!(Math.abs(a.z - job.zD) < 0.6 && Math.abs(b.z - job.zD) < 0.6)) { pen = false; continue; }
      const partial = !job.done && j === job.k;
      if (partial && !(job.t > 0)) break;
      const ex = partial ? a.x + (b.x - a.x) * job.t : b.x, ey = partial ? a.y + (b.y - a.y) * job.t : b.y;
      if (!pen) { const [sx, sy] = v.toS(a.x, a.y); ctx.moveTo(sx, sy); pen = true; }
      const [tx, ty] = v.toS(ex, ey); ctx.lineTo(tx, ty);
    }
  }
  ctx.stroke();
  ctx.restore();
}

// The pen as a red laser dot: bright with a glow when down on the paper, dimmer when lifted.
function drawLaser(ctx, v, p, withLabel) {
  if (!p || ![p.x, p.y].every(Number.isFinite)) return;
  const [sx, sy] = v.toS(p.x, p.y), down = S.limits.penSet && p.z <= S.limits.zDown + 2;
  const R = down ? 17 : 12, g = ctx.createRadialGradient(sx, sy, 0, sx, sy, R);
  g.addColorStop(0, down ? 'rgba(255,30,30,0.75)' : 'rgba(255,30,30,0.40)');
  g.addColorStop(0.45, down ? 'rgba(255,30,30,0.28)' : 'rgba(255,30,30,0.14)');
  g.addColorStop(1, 'rgba(255,30,30,0)');
  ctx.save();
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(sx, sy, R, 0, 2 * Math.PI); ctx.fill();
  ctx.fillStyle = '#ff1f1f'; ctx.beginPath(); ctx.arc(sx, sy, down ? 4 : 3, 0, 2 * Math.PI); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.beginPath(); ctx.arc(sx, sy, 1.4, 0, 2 * Math.PI); ctx.fill();
  if (withLabel) { ctx.fillStyle = cssVar('--laser'); ctx.font = '11px system-ui'; ctx.fillText(down ? 'pen down' : 'pen up', sx + 11, sy - 9); }
  ctx.restore();
}

function drawPlot() {
  const ctx = setupCanvas(plotCv), v = plotView(), z = drawZone();
  drawBase(plotCv, v, ctx, { band: false });
  drawZoneShape(ctx, v, z);
  const objs = S.plot.objects;
  if (objs.length) {
    if (S.plot.zoneKey && S.plot.zoneKey !== zoneKey(z) && !S.running && !PL.drag) {   // reach or margin changed
      clearTimeout(PL.zt); PL.zt = setTimeout(() => buildPlot({ quiet: true }), 30);
    }
    const ink = cssVar('--ink'), muted = cssVar('--muted'), err = cssVar('--err');
    const built = !!S.plot.ops && S.plot.opsVer === S.plot.placeVer, inPath = new Set(built ? S.plot.drawnIds : []);
    if (built) drawOpsPaths(ctx, v, S.plot.ops, S.plot.start, ink, muted);
    for (const o of objs) {                              // the rest: fast previews (also while dragging)
      if (!o.place || inPath.has(o.id)) continue;
      const col = !o.use ? muted : o.placeOk === false ? err : ink;
      ctx.save();
      if (!o.use) { ctx.setLineDash([4, 3]); ctx.globalAlpha = 0.8; }
      drawPreview(ctx, v, objProbe(o), o.place, col);
      ctx.restore();
      if (o.use && typeof shadePreview === 'function') shadePreview(ctx, v, o, col);
    }
    const so = selObj(), hv = PL.hover != null ? objById(PL.hover) : null;
    if (hv && hv !== so && !PL.drag && !S.running) drawHoverFrame(ctx, v, hv);
    if (so && so.place) {
      drawFrame(ctx, v, so.placeOk !== false, !S.running);
      if (typeof shadeOverlay === 'function') shadeOverlay(ctx, v);
    }
  }
  drawHoverFrame2(ctx, v);
  drawPaper(ctx, v);
  if (S.dev) drawLaser(ctx, v, S.pos, !S.running);
}

/* ----- drawing jobs ----- */
function penReady() {
  if (S.limits.penSet) return true;
  log('Set the pen-down height first: Setup → Auto-calibrate, or lower the pen to the paper and press “Pen-down = current Z”.', 'warn');
  return false;
}

function unreachableCount(cmds) {
  if (!(S.model && S.model.ok)) return 0;
  return cmds.filter(c => !magReachable(c.x, c.y, c.z, S.model, 0.5)).length;
}

// Straight moves that would pass closer to the base than the arm can reach: moves between the pen
// heights are checked against the drawing band, level moves elsewhere against the reach at that height.
function coreCuts(cmds, start) {
  const zLo = S.limits.zDown - 0.6, zHi = S.limits.zUp + 0.6, band = drawBand();
  let n = 0, prev = start;
  for (const c of cmds) {
    if (c.x === undefined) continue;
    if (prev) {
      let rMin = null;
      if (c.z >= zLo && c.z <= zHi && prev.z >= zLo && prev.z <= zHi) rMin = band.minR;
      else if (Math.abs(c.z - prev.z) < 0.01) { const b = S.model && S.model.ok ? reachAt(S.model, c.z) : [S.limits.minR]; rMin = b ? b[0] : null; }
      if (rMin != null && segDist0(prev.x, prev.y, c.x, c.y) < rMin - 0.5) n++;
    }
    prev = c;
  }
  return n;
}

async function runDrawing(name, ops, start) {
  const smooth = plotOpt('plot-motion') === 'smooth';
  const planned = plotCommands(ops, S.limits, start, { cp: smooth, continuous: smooth, speed: S.speed.draw, core: drawZone().rIn, ...hopSettings() });
  const bad = unreachableCount(planned);       // check first, so nothing is silently squashed
  if (bad) return log(`${bad} point(s) are outside the arm's reach at pen height. Keep the drawing inside the green zone; if the arm is far away, press Centre (home) first.`, 'err');
  const cuts = coreCuts(planned, start);
  if (cuts) return log(`${cuts} move(s) would pass too close to the base. Move the drawing further from the base.`, 'err');
  const cmds = planned.map(c => ({ ...c, ...clampTarget(c.x, c.y, c.z) }));
  const cpAcc = parseFloat(plotOpt('plot-cpacc')) || 150;
  const job = { name, cmds, start: { x: start.x, y: start.y, z: start.z }, zD: S.limits.zDown, idx: new Array(cmds.length).fill(0),
                sent: 0, ke: 0, k: 0, t: 0, active: true, done: false };
  const bar = document.getElementById('plot-bar');
  const ok = await runJob(name, cmds, null, {
    window: smooth ? 20 : 8,
    speed: smooth ? S.speed.travel : S.speed.draw,
    track: job,
    before: async () => {
      if (smooth) await S.dev.setCPParams(cpAcc, S.speed.draw, cpAcc);
      S.paper.jobs.push(job);
      if (S.paper.jobs.length > 40) S.paper.jobs.shift();
    },
  });
  job.active = false;
  if (ok) { job.done = true; job.k = cmds.length; }
  bar.style.width = ok ? '100%' : bar.style.width;
  setTimeout(() => { if (!S.running) bar.style.width = '0%'; }, 900);
  drawPlot();
}

// Follows the running job: commands the arm has executed (queue index) and the live pen position
// (projected onto the planned path) decide how much is painted red. Called after every pose read.
function paperTick() {
  const job = S.paper.jobs[S.paper.jobs.length - 1];
  if (!job || !job.active || !S.dev || !job.sent) return;
  const exec = S.dev.lastExec;
  if (exec !== undefined) while (job.ke < job.sent && ((job.idx[job.ke] - exec) | 0) <= 0) job.ke++;
  const lo = Math.max(job.k, job.ke - 12), hi = Math.min(job.sent - 1, job.ke + 1);
  let best = null;
  for (let j = lo; j <= hi; j++) {
    const r = projectOnSeg3(j ? job.cmds[j - 1] : job.start, job.cmds[j], S.pos);
    if (!best || r.d < best.d - 0.05 || (r.d <= best.d + 0.05 && j > best.j)) best = { ...r, j };
  }
  if (best && best.d < 4 && (best.j > job.k || (best.j === job.k && best.t > job.t))) { job.k = best.j; job.t = best.t; }
  else if (job.k < job.ke - 12) { job.k = job.ke - 12; job.t = 0; }
  const bar = document.getElementById('plot-bar');
  if (bar) bar.style.width = (100 * Math.min(1, (job.k + job.t) / job.cmds.length)).toFixed(1) + '%';
}

async function drawPlotJob() {
  if (!S.plot.ops) return log('Load a drawing first.', 'warn');
  if (!penReady()) return;
  if (S.plot.opsVer !== S.plot.placeVer && !buildPlot()) return;
  try { await runDrawing('Plot', S.plot.ops, S.cmd || S.pos); } catch (e) { log(e.message, 'err'); }
}

// Does a square of half-size h centred at c lie in the green zone (edges included)?
function squareFits(z, c, h) {
  const pts = [[-h, -h], [-h, h], [h, h], [h, -h]].map(([a, b]) => ({ x: c.x + a, y: c.y + b }));
  return pts.every(p => zoneHas(z, p.x, p.y)) && pts.every((p, i) => { const q = pts[(i + 1) % 4]; return segDist0(p.x, p.y, q.x, q.y) >= z.rIn; });
}

// Where to draw the 20 mm test square: beside the objects on the paper (as close as possible, so it is
// on the same sheet, but clear of every one of them), or the middle of the green zone when the paper is empty.
function testSquareSpot(z, h) {
  const objs = S.plot.objects.filter(o => o.place);
  if (!objs.length) {
    const c = { x: (z.rIn + z.rOut) / 2, y: 0 };
    return squareFits(z, c, h) ? c : null;
  }
  const frames = objs.map(o => placeFrame(o.sketch, o.place)), clear = h * Math.SQRT2 + 5;
  const outside1 = (fr, c) => {                              // distance from a frame, 0 if inside it
    let pos = 0, neg = 0, d = Infinity;
    for (let i = 0; i < 4; i++) {
      const a = fr[i], b = fr[(i + 1) % 4], ex = b.x - a.x, ey = b.y - a.y, L2 = ex * ex + ey * ey;
      const cr = ex * (c.y - a.y) - ey * (c.x - a.x);
      if (cr > 0) pos++; else if (cr < 0) neg++;
      const t = L2 > 0 ? clamp(((c.x - a.x) * ex + (c.y - a.y) * ey) / L2, 0, 1) : 0;
      d = Math.min(d, Math.hypot(a.x + t * ex - c.x, a.y + t * ey - c.y));
    }
    return pos && neg ? d : 0;
  };
  const outside = c => Math.min(...frames.map(fr => outside1(fr, c)));
  const so = selObj(), ref = so && so.place ? so : objs[objs.length - 1], pl = ref.place, fr0 = placeFrame(ref.sketch, pl);
  const r0 = Math.hypot(fr0[0].x - pl.cx, fr0[0].y - pl.cy);
  for (let d = Math.max(clear, r0 * 0.5); d <= r0 + 160; d += 4) {
    for (let k = 0; k < 24; k++) {
      const a = Math.PI + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * Math.PI / 12;   // towards the base first, then round
      const c = { x: pl.cx + d * Math.cos(a), y: pl.cy + d * Math.sin(a) };
      if (outside(c) >= clear && squareFits(z, c, h)) return c;
    }
  }
  for (let r = z.rIn + h * 1.5; r <= z.rOut - h * 1.5; r += 4) {   // anywhere free in the zone
    for (let th = 0; th <= 90; th += 3) for (const a of th ? [th, -th] : [0]) {
      const c = { x: r * Math.cos(a * RAD), y: r * Math.sin(a * RAD) };
      if (outside(c) >= clear && squareFits(z, c, h)) return c;
    }
  }
  return null;
}

// A 20 mm square beside the drawing: checks pen pressure before the real drawing.
async function testSquare() {
  if (!penReady()) return;
  const z = drawZone(), h = 10, c = testSquareSpot(z, h);
  if (!c) return log('No free spot in the green zone for a 20 mm square — make the drawings smaller or check the pen heights.', 'err');
  const sq = [[c.x - h, c.y - h], [c.x - h, c.y + h], [c.x + h, c.y + h], [c.x + h, c.y - h], [c.x - h, c.y - h]].map(([x, y]) => ({ x, y }));
  const ops = buildOps([{ pts: sq, rev: false }], S.cmd || S.pos, 0.5);
  try { await runDrawing('Test square', ops, S.cmd || S.pos); } catch (e) { log(e.message, 'err'); }
}

// The hover round: the pen goes once round the outside of everything that will be drawn, held just
// above the paper, to check the paper is in the right place. 'box': round the corners of a rectangle
// (square to the paper) that holds every line; 'outline': tight round the outside of the lines.
// The round keeps `margin` mm outside the lines, and never cuts across the unreachable middle.
function hoverRoundLoop(shape, margin = 3) {
  const pts = (S.plot.ops || []).filter(o => o.pen);
  if (pts.length < 2) return null;
  const zH = S.limits.penSet ? Math.min(S.limits.zUp, S.limits.zDown + 5) : S.limits.zUp;
  const reach = (x, y) => S.model && S.model.ok ? magReachable(x, y, zH, S.model, 0.5) : (() => { const c = clampTarget(x, y, zH); return Math.hypot(c.x - x, c.y - y) < 0.5; })();
  const core = drawZone().rIn;
  // closed loop → robot moves, with arcs round the base where a straight line would cut too close
  const route = loop => {
    const out = [];
    for (let i = 0; i <= loop.length; i++) {
      const a = loop[(i + loop.length - 1) % loop.length], b = loop[i % loop.length];
      if (i) for (const w of arcWaypoints(a, b, core)) out.push(w);
      out.push(b);
    }
    return out;
  };
  const ok = path => path.every((p, i) => {
    if (!reach(p.x, p.y)) return false;
    if (!i) return true;
    const a = path[i - 1], n = Math.ceil(Math.hypot(p.x - a.x, p.y - a.y) / 5);
    for (let k = 1; k < n; k++) if (!reach(a.x + (p.x - a.x) * k / n, a.y + (p.y - a.y) * k / n)) return false;
    return true;
  });
  const tries = [];
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of pts) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; }
  const box = m => [{ x: x1 + m, y: y1 + m }, { x: x1 + m, y: y0 - m }, { x: x0 - m, y: y0 - m }, { x: x0 - m, y: y1 + m }];   // screen: top-left, top-right, bottom-right, bottom-left
  const hull = convexHull(pts), cx = hull.reduce((a, p) => a + p.x, 0) / hull.length, cy = hull.reduce((a, p) => a + p.y, 0) / hull.length;
  const outline = m => hull.map(p => { const d = Math.hypot(p.x - cx, p.y - cy) || 1; return { x: p.x + m * (p.x - cx) / d, y: p.y + m * (p.y - cy) / d }; });
  const ms = [margin, margin * 2 / 3, margin / 3, 0];          // a smaller margin before giving up on the shape
  if (shape === 'box') for (const m of ms) tries.push(['box', box(m)]);
  for (const m of ms) tries.push(['outline', outline(m)]);
  for (const [kind, loop] of tries) {
    const path = route(loop);
    if (ok(path)) return { kind, loop, path, z: zH, fellBack: kind !== shape };
  }
  return null;
}

async function hoverRound() {
  if (!S.dev) return log('Connect or start the simulator first.', 'warn');
  if (!S.plot.objects.some(o => o.use)) return log('Put something on the paper first (and tick it).', 'warn');
  if (S.plot.opsVer !== S.plot.placeVer || !S.plot.ops) { if (!buildPlot({ quiet: true })) return; }
  const shape = plotOpt('plot-frame') === 'outline' ? 'outline' : 'box';
  const r = hoverRoundLoop(shape);
  if (!r) return log('There is no way round these drawings that the arm can reach — move them a little away from the edges of the green zone.', 'err');
  if (r.fellBack) log('The corners of the box are out of the arm\'s reach, so the round follows the outline of the drawings instead.', 'warn');
  const start = S.cmd || S.pos, z = r.z, core = drawZone().rIn, cmds = [];
  if (start.z < z - 0.5) cmds.push({ x: start.x, y: start.y, z, mode: 2 });
  for (const w of arcWaypoints(start, r.path[0], core)) cmds.push({ x: w.x, y: w.y, z: Math.max(z, start.z), mode: 2 });
  cmds.push({ x: r.path[0].x, y: r.path[0].y, z, mode: 2 });
  for (const p of r.path.slice(1)) cmds.push({ x: p.x, y: p.y, z, mode: 2 });
  cmds.push({ x: r.path[0].x, y: r.path[0].y, z: Math.max(z, S.limits.zUp), mode: 2 });   // lift at the end
  PL.frame = { path: r.path, until: Infinity };
  drawPlot();
  const lenMm = r.path.reduce((a, p, i) => a + (i ? Math.hypot(p.x - r.path[i - 1].x, p.y - r.path[i - 1].y) : 0), 0);
  log(`Hover round (${r.kind === 'box' ? 'box' : 'outline'}, ${lenMm.toFixed(0)} mm, ${(z - S.limits.zDown).toFixed(0)} mm above the paper): watch that the pen stays over the paper.`);
  try { await runJob('Hover round', cmds, document.getElementById('plot-bar'), { speed: Math.min(S.speed.travel || 60, 60) }); }
  catch (e) { log(e.message, 'err'); }
  finally { PL.frame.until = performance.now() + 5000; setTimeout(() => drawPlot(), 5100); drawPlot(); }
}

// The hover round's path on the map (dashed), while it runs and for a few seconds after.
function drawHoverFrame2(ctx, v) {
  const f = PL.frame;
  if (!f || performance.now() > f.until) return;
  ctx.save(); ctx.strokeStyle = cssVar('--warn'); ctx.lineWidth = 1.6; ctx.setLineDash([6, 4]); ctx.beginPath();
  f.path.forEach((p, i) => { const [x, y] = v.toS(p.x, p.y); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.stroke(); ctx.restore();
}

async function togglePause() {
  if (!S.running || !S.dev) return;
  try {
    if (S.paused) { await S.dev.resumeQueue(); S.paused = false; log('Resumed.'); }
    else { await S.dev.pauseQueue(); S.paused = true; log('Paused — the arm stops after the current move. Press Resume to continue.', 'warn'); }
  } catch (e) { log('Pause failed: ' + e.message, 'err'); }
  renderPause();
}

function renderPause() {
  const b = document.getElementById('btnPause');
  if (!b) return;
  b.disabled = !S.running;
  b.textContent = S.paused ? 'Resume' : 'Pause';
  b.classList.toggle('on', !!S.paused);
}

// Export the optimised path as JSON (robot-space mm, pen flag per move) for reuse.
function exportOps() {
  if (!S.plot.ops) return log('Build the path first.', 'warn');
  const objects = (S.plot.drawnIds || []).map(objById).filter(Boolean).map(o => ({ label: o.label, kind: o.kind, placement: o.place, ...(o.text ? { text: o.text } : {}) }));
  const data = { format: 'magician-ops-v1', units: 'mm', zUp: S.limits.zUp, zDown: S.limits.zDown, placement: objects.length === 1 ? objects[0].placement : null, objects,
                 stats: S.plot.stats, ops: S.plot.ops.map(o => [+o.x.toFixed(3), +o.y.toFixed(3), o.pen ? 1 : 0]) };
  downloadText('plot-ops.json', JSON.stringify(data));
}

function downloadText(name, text, type = 'application/json') {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

/* ===================== RECORD & LEARN ===================== */
const recCv = document.getElementById('recCanvas');

function renderTakes() {
  const box = document.getElementById('takeList');
  box.innerHTML = '';
  if (!S.takes.length) { box.innerHTML = '<div class="muted">No takes yet. Press Record, then drive the arm with the Mouse tab, arrow keys or Z slider.</div>'; return; }
  S.takes.forEach((t, i) => {
    const row = document.createElement('div');
    row.className = 'take';
    row.innerHTML = `<label><input type="checkbox" ${t.use ? 'checked' : ''}> <b>${t.name}</b> <span class="muted">${t.pts.length} pts</span></label>
      <span><button data-play="${i}">Play</button> <button data-del="${i}" class="ghost">Delete</button></span>`;
    row.querySelector('input').onchange = e => { t.use = e.target.checked; };
    row.querySelector('[data-play]').onclick = () => playTake(i);
    row.querySelector('[data-del]').onclick = () => { S.takes.splice(i, 1); renderTakes(); drawRec(); };
    box.appendChild(row);
  });
}

function toggleRecord() {
  const btn = document.getElementById('btnRec');
  if (!S.dev) return log('Connect or start the simulator first.', 'warn');
  if (!S.rec.active) {
    S.rec = { active: true, pts: [] };
    btn.textContent = 'Stop recording'; btn.classList.add('on');
    log('Recording… move the arm now.');
  } else {
    S.rec.active = false;
    btn.textContent = 'Record take'; btn.classList.remove('on');
    if (S.rec.pts.length >= 2) {
      S.takes.push({ name: 'Take ' + (S.takes.length + 1), pts: S.rec.pts, use: true });
      log(`Saved ${S.rec.pts.length} points as Take ${S.takes.length}.`, 'ok');
    } else log('Take too short — move the arm while recording.', 'warn');
    S.rec.pts = [];
    document.getElementById('recCount').textContent = '';
    renderTakes(); drawRec();
  }
}

async function playTake(i) {
  const t = S.takes[i];
  const cmds = [{ x: t.pts[0].x, y: t.pts[0].y, z: S.limits.zUp }];
  for (const p of t.pts) { const c = clampTarget(p.x, p.y, p.z); cmds.push({ x: c.x, y: c.y, z: c.z }); }
  await runJob('Play ' + t.name, cmds, document.getElementById('rec-bar'));
}

function learn() {
  const used = S.takes.filter(t => t.use);
  if (used.length < 2) return log('Select at least two takes to learn a repeated movement.', 'warn');
  const n = Math.max(20, parseInt(document.getElementById('rec-samples').value, 10) || 120);
  const L = learnTakes(used.map(t => t.pts), n);
  S.learned = { ...L, takes: used.length };
  const maxSpread = Math.max(...L.spread);
  document.getElementById('learn-stats').textContent =
    `Learned from ${used.length} takes · ${n} samples · consistency ${L.consistency.toFixed(2)} mm RMS · widest spread ${maxSpread.toFixed(2)} mm`;
  log(`Learned movement from ${used.length} takes (${L.consistency.toFixed(2)} mm RMS spread).`, 'ok');
  drawRec();
}

async function playLearned() {
  if (!S.learned) return log('Learn from takes first.', 'warn');
  const reps = Math.max(1, parseInt(document.getElementById('rec-reps').value, 10) || 1);
  const pause = Math.max(0, parseInt(document.getElementById('rec-pause').value, 10) || 0);
  const m = S.learned.mean;
  const cmds = [];
  for (let r = 0; r < reps; r++) {
    cmds.push({ x: m[0].x, y: m[0].y, z: S.limits.zUp });
    for (const p of m) { const c = clampTarget(p.x, p.y, p.z); cmds.push({ x: c.x, y: c.y, z: c.z }); }
    if (r < reps - 1 && pause > 0) cmds.push({ pause });
  }
  await runJob(`Learned movement ×${reps}`, cmds, document.getElementById('rec-bar'));
}

function exportTakes() {
  downloadText('takes.json', JSON.stringify({ format: 'magician-takes-v1', limits: S.limits, takes: S.takes }));
}

async function importTakes(file) {
  const data = JSON.parse(await file.text());
  if (data.format !== 'magician-takes-v1' || !Array.isArray(data.takes)) throw new Error('Not a takes file');
  S.takes = data.takes.map(t => ({ name: t.name, pts: t.pts, use: true }));
  renderTakes(); learn();
}

function drawRec() {
  const ctx = setupCanvas(recCv);
  const v = viewOf(recCv);
  drawBase(recCv, v, ctx);
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue('--muted').trim(), acc = css.getPropertyValue('--accent').trim();
  const warn = css.getPropertyValue('--warn').trim();
  const line = (pts, color, width) => {
    if (!pts.length) return;
    ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.beginPath();
    pts.forEach((p, i) => { const [sx, sy] = v.toS(p.x, p.y); i ? ctx.lineTo(sx, sy) : ctx.moveTo(sx, sy); });
    ctx.stroke();
  };
  S.takes.forEach(t => { if (t.use) line(t.pts, muted, 1); });
  const live = S.rec.active ? S.rec.pts : [];
  line(live, warn, 1.5);
  if (S.learned) {
    const m = S.learned.mean;
    // spread band: a translucent circle at intervals, radius = local spread
    ctx.fillStyle = 'rgba(37,99,235,0.15)';
    m.forEach((p, i) => {
      if (i % 4) return;
      const [sx, sy] = v.toS(p.x, p.y);
      ctx.beginPath(); ctx.arc(sx, sy, Math.max(2, S.learned.spread[i] * v.k), 0, 2 * Math.PI); ctx.fill();
    });
    line(m, acc, 2.5);
  }
}

// Learned/recorded paths are robot-space points; the arm's current pose is shown on Mouse tab.
