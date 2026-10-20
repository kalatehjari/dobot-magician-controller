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

/* ----- placement state: S.plot.sketch (normalised drawing) + S.plot.place {cx, cy, size, angle, mirror} ----- */
const PL = { probe: null, probeKey: '', targets: null, targetsKey: '', base: null, drag: null, zt: 0, kt: 0 };

function plProbe() {
  const sk = S.plot.sketch, pl = S.plot.place, key = `${sk.id}|${pl.angle}|${pl.mirror ? 1 : 0}`;
  if (PL.probeKey !== key) { PL.probe = placementProbe(sk, pl.angle, pl.mirror); PL.probeKey = key; }
  return PL.probe;
}
// Roomiest spots for the current rotation: [on the centre line, anywhere]. Cached.
function placeTargets() {
  const z = drawZone(), pad = plotPad(), P = plProbe(), key = `${PL.probeKey}|${zoneKey(z)}|${pad}`;
  if (PL.targetsKey !== key) {
    PL.targets = [bestPlacement(P, z, { centreLine: true, pad }), bestPlacement(P, z, { pad })];
    PL.targetsKey = key;
  }
  return PL.targets;
}
// Placement asked for → the nearest one that fits (moved or, only if needed, shrunk).
function fitPlace(want) {
  const prev = S.plot.place;
  S.plot.place = { ...want, mirror: !!want.mirror };          // so the probe and targets are for this rotation
  try { return fixPlacement(S.plot.sketch, S.plot.place, drawZone(), { pad: plotPad(), probe: plProbe(), targets: placeTargets() }); }
  finally { S.plot.place = prev; }
}
function setPlace(pl) {
  S.plot.place = { cx: pl.cx, cy: pl.cy, size: pl.size, angle: pl.angle, mirror: !!pl.mirror };
  S.plot.placeVer++;
  S.plot.placeOk = probeFits(plProbe(), pl.cx, pl.cy, pl.size, drawZone(), plotPad());
  syncPlaceInputs();
}

function defaultPlacement(sk) {
  const z = drawZone(), P = placementProbe(sk, 0, false), pad = plotPad();
  const b = bestPlacement(P, z, { centreLine: true, pad }) || bestPlacement(P, z, { pad });
  if (!b) return { cx: (z.rIn + z.rOut) / 2, cy: 0, size: 20, angle: 0, mirror: false };
  return { cx: b.cx, cy: b.cy, size: Math.max(5, Math.floor(b.size * 0.9)), angle: 0, mirror: false };
}

// New drawing for the Plotter. opts.source: picture name, so re-tracing the same picture keeps its
// scale and position on the paper; opts.robotMm: strokes already in robot millimetres (air drawing).
function setDrawing(strokes, label, opts = {}) {
  const sketchStrokes = opts.robotMm ? strokes.map(s => s.map(p => ({ x: -p.y, y: -p.x }))) : strokes;
  const prev = S.plot.sketch, prevPl = S.plot.place;
  const sk = prepareSketch(sketchStrokes, opts.source || null);
  let pl;
  if (opts.robotMm) {
    pl = { cx: -sk.srcBox.cy, cy: -sk.srcBox.cx, size: sk.srcBox.L, angle: 0, mirror: false };
  } else if (opts.source && prev && prevPl && prev.source === opts.source) {
    const k = prevPl.size / prev.srcBox.L, d = placeLinear(prevPl.angle, prevPl.mirror)({ x: sk.srcBox.cx - prev.srcBox.cx, y: sk.srcBox.cy - prev.srcBox.cy });
    pl = { ...prevPl, cx: prevPl.cx + k * d.x, cy: prevPl.cy + k * d.y, size: k * sk.srcBox.L };
  } else {
    pl = defaultPlacement(sk);
  }
  S.plot.sketch = sk; S.plot.order = null; S.plot.ops = null; S.plot.label = label;
  setPlace(pl);
  return buildPlot();
}

async function loadSvgText(text, label) {
  const raw = svgToStrokes(text);
  if (!raw.length) throw new Error('No drawable outlines found in this SVG (text and fills-only shapes are not converted).');
  document.getElementById('plot-file-name').textContent = label;
  log(`Loaded ${label}: ${raw.length} raw strokes.`, 'ok');
  setDrawing(raw, label);
}

// Placement → robot path. The stroke order is worked out once per drawing (it only depends on the
// drawing's own shape), so moving, turning or resizing it afterwards is instant.
function buildPlot(opts = {}) {
  const sk = S.plot.sketch;
  if (!sk) { log('Load a drawing first.', 'warn'); return false; }
  try {
    const tol = parseFloat(plotOpt('plot-tol')), minLen = parseFloat(plotOpt('plot-minlen'));
    const join = parseFloat(plotOpt('plot-join')), budget = parseFloat(plotOpt('plot-opt'));
    if (![tol, minLen, join, budget].every(Number.isFinite)) throw new Error('Check the optimisation values');
    const z = drawZone();
    const fixed = fitPlace(S.plot.place);
    if (!fixed) throw new Error('The drawing does not fit in the green zone at any size. Check the pen heights (Setup → Auto-calibrate) or lower the safety margin.');
    if (fixed.fixed) {
      setPlace(fixed);
      log(fixed.shrunk ? `Drawing made smaller (${fixed.size.toFixed(0)} mm) so it fits in the green zone.` : 'Drawing moved so it fits inside the green zone.', 'warn');
    }
    const pl = S.plot.place, f = placeXform(pl), okey = `${sk.id}|${budget}`;
    if (opts.reorder || !S.plot.order || S.plot.order.key !== okey) {
      const index = new Map(sk.strokes.map((s, i) => [s, i]));
      const seq0 = orderStrokes(sk.strokes, placeInverse(pl)(S.cmd || S.pos), budget);
      S.plot.order = { key: okey, seq: seq0.map(e => ({ i: index.get(e.pts), rev: e.rev })) };
    }
    const seq = [];
    for (const o of S.plot.order.seq) {
      const c = cleanStrokes([sk.strokes[o.i].map(f)], tol, minLen);
      if (c.length) seq.push({ pts: c[0], rev: o.rev });
    }
    if (!seq.length) throw new Error('Nothing left after simplification — lower the minimum length.');
    const start = { ...(S.cmd || S.pos) };
    const ops = buildOps(seq, start, join);
    const fr = placeFrame(sk, pl), xs = fr.map(p => p.x), ys = fr.map(p => p.y);
    S.plot.strokes = seq.map(e => e.pts); S.plot.ops = ops; S.plot.start = start;
    S.plot.rect = { cx: (Math.min(...xs) + Math.max(...xs)) / 2, cy: (Math.min(...ys) + Math.max(...ys)) / 2, w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
    S.plot.stats = opsStats(ops, start);
    S.plot.stats.count = seq.length;
    S.plot.stats.pointsBefore = sk.points;
    S.plot.stats.pointsAfter = seq.reduce((a, e) => a + e.pts.length, 0);
    S.plot.opsVer = S.plot.placeVer; S.plot.zoneKey = zoneKey(z);
    renderPlotStats();
    drawPlot();
    return true;
  } catch (e) {
    S.plot.ops = null;
    log('Build failed: ' + e.message, 'err');
    document.getElementById('plot-stats').textContent = e.message;
    drawPlot();
    return false;
  }
}

function renderPlotStats() {
  const s = S.plot.stats, pl = S.plot.place, sk = S.plot.sketch;
  if (!s || !pl || !sk) return;
  const turn = pl.angle ? `, turned ${+pl.angle.toFixed(1)}°` : '';
  document.getElementById('plot-stats').textContent =
    `${(sk.w * pl.size).toFixed(0)} × ${(sk.h * pl.size).toFixed(0)} mm${turn}${pl.mirror ? ', mirrored' : ''} · ${s.count} strokes · ${s.lifts} pen lifts · ` +
    `drawing ${s.draw.toFixed(0)} mm · travel ${s.travel.toFixed(0)} mm · est. ${estimateMinutes(s).toFixed(1)} min`;
}

function estimateMinutes(s) {
  const smooth = plotOpt('plot-motion') === 'smooth';
  const draw = (s.draw / (S.speed.draw || 30)) * (smooth ? 1.15 : 1.8);   // precise mode stops at points
  const travel = s.travel / (smooth ? (S.speed.travel || 100) : (S.speed.draw || 30));
  return (draw + travel + s.lifts * 0.8) / 60;
}

/* ----- plotter canvas ----- */
function plotView() { return viewOf(plotCv, Math.max(S.limits.maxR, drawBand().maxR)); }

// Screen positions of the drawing's frame (TL, TR, BR, BL), centre and rotate knob.
function frameGeom(v) {
  const sk = S.plot.sketch, pl = S.plot.place;
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
  const sk = S.plot.sketch, pl = S.plot.place;
  if (sk && pl) {
    if (S.plot.zoneKey && S.plot.zoneKey !== zoneKey(z) && !S.running && !PL.drag) {   // reach or margin changed
      clearTimeout(PL.zt); PL.zt = setTimeout(() => buildPlot(), 30);
    }
    const ink = cssVar('--ink'), muted = cssVar('--muted');
    if (S.plot.ops && S.plot.opsVer === S.plot.placeVer) drawOpsPaths(ctx, v, S.plot.ops, S.plot.start, ink, muted);
    else drawPreview(ctx, v, plProbe(), pl, S.plot.placeOk ? ink : cssVar('--err'));
    drawFrame(ctx, v, S.plot.placeOk !== false, !S.running);
  }
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

// Straight moves at one height that would pass closer to the base than the arm can reach there.
function coreCuts(cmds, start) {
  let n = 0, prev = start;
  for (const c of cmds) {
    if (c.x === undefined) continue;
    if (prev && Math.abs(c.z - prev.z) < 0.01) {
      const band = S.model && S.model.ok ? reachAt(S.model, c.z) : [S.limits.minR, S.limits.maxR];
      if (band && segDist0(prev.x, prev.y, c.x, c.y) < band[0] - 0.5) n++;
    }
    prev = c;
  }
  return n;
}

async function runDrawing(name, ops, start) {
  const smooth = plotOpt('plot-motion') === 'smooth';
  const planned = plotCommands(ops, S.limits, start, { cp: smooth, speed: S.speed.draw, core: drawZone().rIn });
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

// Where to draw the 20 mm test square: next to the drawing (as close as possible, so it is on the
// same sheet, but clear of it), or the middle of the green zone when no drawing is loaded.
function testSquareSpot(z, h) {
  if (!S.plot.sketch || !S.plot.place) {
    const c = { x: (z.rIn + z.rOut) / 2, y: 0 };
    return squareFits(z, c, h) ? c : null;
  }
  const pl = S.plot.place, fr = placeFrame(S.plot.sketch, pl), clear = h * Math.SQRT2 + 5;
  const outside = c => {                                     // distance from the frame, 0 if inside it
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
  const r0 = Math.hypot(fr[0].x - pl.cx, fr[0].y - pl.cy);
  for (let d = Math.max(clear, r0 * 0.5); d <= r0 + 160; d += 4) {
    for (let k = 0; k < 24; k++) {
      const a = Math.PI + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * Math.PI / 12;   // towards the base first, then round
      const c = { x: pl.cx + d * Math.cos(a), y: pl.cy + d * Math.sin(a) };
      if (outside(c) >= clear && squareFits(z, c, h)) return c;
    }
  }
  return null;
}

// A 20 mm square beside the drawing: checks pen pressure before the real drawing.
async function testSquare() {
  if (!penReady()) return;
  const z = drawZone(), h = 10, c = testSquareSpot(z, h);
  if (!c) return log('No free spot in the green zone for a 20 mm square — make the drawing smaller or check the pen heights.', 'err');
  const sq = [[c.x - h, c.y - h], [c.x - h, c.y + h], [c.x + h, c.y + h], [c.x + h, c.y - h], [c.x - h, c.y - h]].map(([x, y]) => ({ x, y }));
  const ops = buildOps([{ pts: sq, rev: false }], S.cmd || S.pos, 0.5);
  try { await runDrawing('Test square', ops, S.cmd || S.pos); } catch (e) { log(e.message, 'err'); }
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
  const data = { format: 'magician-ops-v1', units: 'mm', zUp: S.limits.zUp, zDown: S.limits.zDown, placement: S.plot.place, stats: S.plot.stats, ops: S.plot.ops.map(o => [+o.x.toFixed(3), +o.y.toFixed(3), o.pen ? 1 : 0]) };
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
