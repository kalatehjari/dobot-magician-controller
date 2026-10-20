/* ===================== SMART: IMITATE ===================== */
const IMIT_OWNERS = ['hand mirror', 'arm mirror', 'air drawing', 'teach by showing'];
function imitRelease() { if (IMIT_OWNERS.includes(M.owner)) streamRelease(M.owner); }

const IM = {
  mode: 'hand', active: false, cal: null, wantCal: false,
  filt: new OneEuroVec(3, 1.0, 0.02), pinch: new Hyst(0.35, 0.55), pinchOn: false,
  lastSeen: 0, frozen: false, fistSince: 0, gripState: null,
  air: { strokes: [], cur: null }, teach: { rec: false, pts: [], t0: 0, countdown: 0, lastT: 0 },
  status: '',
};

function imitOpt(id) { const el = document.getElementById(id); return el.type === 'checkbox' ? el.checked : el.value; }
function imitStatus(s) { if (s !== IM.status) { IM.status = s; document.getElementById('imitStatus').textContent = s; } }

function imitMapOpts() {
  return { facing: imitOpt('imitFacing') === 'facing', span: parseFloat(imitOpt('imitSpan')) || 0.5 };
}

async function imitStart() {
  if (IM.active) return;
  IM.mode = imitOpt('imitMode');
  if (!S.dev && IM.mode !== 'air') log('Not connected — tracking only, the arm will not move.', 'warn');
  IM.active = true; IM.frozen = false; IM.filt.reset(); IM.lastSeen = 0;
  const sm = parseFloat(imitOpt('imitSmooth')) || 1;
  IM.filt.tune(sm, 0.02);
  document.getElementById('btnImit').textContent = 'Stop imitating';
  document.getElementById('btnImit').classList.add('on');
  try {
    if (IM.mode === 'arm') await visionRequire('pose', 'imitate');
    else await visionRequire('gesture', 'imitate');
    await smartSpeed(S.speed.smart, S.speed.smart * 1.2);
    imitStatus(IM.mode === 'arm' ? 'Show your upper body and arm to the camera.' : 'Show one hand to the camera.');
    log(`Imitate: ${document.querySelector('#imitMode option:checked').textContent} started.`, 'ok');
  } catch (e) {
    log(e.message, 'err');
    imitStop();
  }
}

function imitStop(fromHalt) {
  if (!IM.active) return;
  IM.active = false;
  if (IM.teach.rec) teachStop(true);
  if (IM.mode === 'air' && IM.pinchOn && !fromHalt && S.cmd) streamTo('air drawing', { ...S.cmd, z: S.limits.zUp }, { linear: true });
  setTimeout(imitRelease, 400);
  visionRelease('gesture', 'imitate'); visionRelease('pose', 'imitate');
  IM.pinchOn = false;
  document.getElementById('btnImit').textContent = 'Start imitating';
  document.getElementById('btnImit').classList.remove('on');
  imitStatus('Stopped.');
  if (!fromHalt) smartSpeed(S.speed.live, S.speed.accel);
}
M.haltHooks.push(() => imitStop(true));

// Fist held for 0.6 s freezes / unfreezes the arm (an open hand is the normal tracking pose).
function imitFistToggle(gesture, tMs) {
  if (gesture === 'Closed_Fist') {
    if (!IM.fistSince) IM.fistSince = tMs;
    else if (tMs - IM.fistSince > 600 && IM.fistSince > 0) { IM.frozen = !IM.frozen; IM.fistSince = -1; log(IM.frozen ? 'Frozen (fist). Make a fist again to continue.' : 'Following again.', 'warn'); if (IM.frozen) imitRelease(); }
  } else IM.fistSince = 0;
}

async function applyPinchAction(on) {
  const act = imitOpt('imitPinch');
  if (!S.dev || act === 'none' || IM.gripState === on) return;
  IM.gripState = on;
  try { if (act === 'gripper') await S.dev.setGripper(on); else if (act === 'suction') await S.dev.setSuction(on); }
  catch (e) { log('Pinch action failed: ' + e.message, 'err'); }
}

onVision('gesture', (res, tMs) => {
  if (!IM.active || IM.mode === 'arm') return;
  const lm = res.landmarks && res.landmarks[0];
  const tSec = tMs / 1000;
  if (!lm) {
    if (IM.lastSeen && tMs - IM.lastSeen > 400) {
      if (IM.mode === 'air' && IM.pinchOn) { IM.pinchOn = false; airEndStroke(); if (imitOpt('imitLivePen') && S.cmd) streamTo('air drawing', { ...S.cmd, z: S.limits.zUp }, { linear: true }); }
      else imitRelease();
      IM.lastSeen = 0; IM.filt.reset();
      imitStatus('Hand lost — holding position.');
    }
    return;
  }
  IM.lastSeen = tMs;
  const g = res.gestures && res.gestures[0] && res.gestures[0][0];
  imitFistToggle(g && g.score > 0.6 ? g.categoryName : '', tMs);
  const m = handMetrics(lm, V.aspect);
  if (!IM.cal || IM.wantCal) { IM.cal = { cx: m.cx, cy: m.cy, palm: m.palm }; IM.wantCal = false; IM.filt.reset(); log('Hand centre set.', 'ok'); }
  const wasPinch = IM.pinchOn;
  IM.pinchOn = IM.pinch.update(m.pinch);
  if (IM.frozen) { imitStatus('Frozen — make a fist for 0.6 s to continue.'); return; }
  if (IM.mode === 'air') return airFrame(m, tSec, wasPinch);
  const raw = mapHandFront(m, IM.cal, S.limits, imitMapOpts());
  const [x, y, z] = IM.filt.filter([raw.x, raw.y, raw.z], tSec);
  const target = clampTarget(x, y, z);
  if (IM.pinchOn !== wasPinch) applyPinchAction(IM.pinchOn);
  if (IM.mode === 'teach') teachFrame(target, tMs);
  if (IM.mode === 'hand' || imitOpt('imitTeachFollow')) streamTo(IM.mode === 'teach' ? 'teach by showing' : 'hand mirror', target);
  imitStatus(`Hand → X ${target.x.toFixed(0)} Y ${target.y.toFixed(0)} Z ${target.z.toFixed(0)}${IM.pinchOn ? ' · pinch' : ''}`);
});

onVision('pose', (res, tMs) => {
  if (!IM.active || IM.mode !== 'arm') return;
  const lm = res.landmarks && res.landmarks[0], wl = res.worldLandmarks && res.worldLandmarks[0];
  const raw = lm ? mapArmPose(lm, wl, imitOpt('imitSide'), S.limits, { ...imitMapOpts(), aspect: V.aspect }) : null;
  if (!raw) {
    if (IM.lastSeen && tMs - IM.lastSeen > 500) { imitRelease(); IM.lastSeen = 0; IM.filt.reset(); imitStatus('Arm not visible — holding position.'); }
    return;
  }
  IM.lastSeen = tMs;
  const [x, y, z] = IM.filt.filter([raw.x, raw.y, raw.z], tMs / 1000);
  const target = clampTarget(x, y, z);
  streamTo('arm mirror', target);
  imitStatus(`Arm → X ${target.x.toFixed(0)} Y ${target.y.toFixed(0)} Z ${target.z.toFixed(0)} (visibility ${(raw.vis * 100).toFixed(0)}%)`);
});

/* ----- air drawing ----- */
function airRect() { try { return plotRect(); } catch (e) { const B = smartBox(S.limits); return { cx: B.xMid, cy: 0, w: B.xHalf, h: B.yHalf * 2 }; } }

function airFrame(m, tSec, wasPinch) {
  const p = mapHandToRect(m, IM.cal, airRect(), imitMapOpts());
  const [x, y] = IM.filt.filter([p.x, p.y, 0], tSec);
  const c = clampTarget(x, y, S.limits.zUp);
  IM.air.cursor = { x: c.x, y: c.y };
  if (IM.pinchOn && !wasPinch) IM.air.cur = [{ x: c.x, y: c.y }];
  if (IM.pinchOn && IM.air.cur) {
    const last = IM.air.cur[IM.air.cur.length - 1];
    if (dist(last, c) >= 1) IM.air.cur.push({ x: c.x, y: c.y });
  }
  if (!IM.pinchOn && wasPinch) airEndStroke();
  if (imitOpt('imitLivePen') && S.dev) streamTo('air drawing', { x: c.x, y: c.y, z: IM.pinchOn ? S.limits.zDown : S.limits.zUp }, { linear: true });
  imitStatus(IM.pinchOn ? 'Drawing (pinch)… release to lift the pen.' : 'Pen up — pinch thumb and index finger to draw.');
  drawAir();
}

function airEndStroke() {
  if (IM.air.cur && IM.air.cur.length > 1) IM.air.strokes.push(IM.air.cur);
  IM.air.cur = null;
  document.getElementById('airCount').textContent = `${IM.air.strokes.length} stroke(s)`;
  drawAir();
}

function airToPlotter() {
  if (!IM.air.strokes.length) return log('Draw something first (pinch to draw).', 'warn');
  document.getElementById('plot-file-name').textContent = `air drawing (${IM.air.strokes.length} strokes)`;
  showTab('plot');
  setDrawing(IM.air.strokes.map(s => s.map(p => ({ x: p.x, y: p.y }))), 'air drawing', { robotMm: true });
  log('Air drawing sent to the Plotter. Check the preview, then press Draw.', 'ok');
}

function drawAir() {
  const cv = document.getElementById('airCanvas');
  if (!cv || !document.getElementById('tab-imit').classList.contains('active')) return;
  const ctx = setupCanvas(cv), v = viewOf(cv);
  drawBase(cv, v, ctx);
  const css = getComputedStyle(document.documentElement);
  const ink = css.getPropertyValue('--ink').trim(), acc = css.getPropertyValue('--accent').trim(), warn = css.getPropertyValue('--warn').trim();
  const r = airRect();
  ctx.strokeStyle = acc; ctx.setLineDash([4, 4]);
  ctx.beginPath();
  [[r.cx - r.w / 2, r.cy - r.h / 2], [r.cx + r.w / 2, r.cy - r.h / 2], [r.cx + r.w / 2, r.cy + r.h / 2], [r.cx - r.w / 2, r.cy + r.h / 2]].forEach((c, i) => { const [sx, sy] = v.toS(c[0], c[1]); i ? ctx.lineTo(sx, sy) : ctx.moveTo(sx, sy); });
  ctx.closePath(); ctx.stroke(); ctx.setLineDash([]);
  const strokeLine = (pts, color) => { ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath(); pts.forEach((p, i) => { const [sx, sy] = v.toS(p.x, p.y); i ? ctx.lineTo(sx, sy) : ctx.moveTo(sx, sy); }); ctx.stroke(); };
  IM.air.strokes.forEach(s => strokeLine(s, ink));
  if (IM.air.cur) strokeLine(IM.air.cur, warn);
  if (IM.air.cursor) { const [sx, sy] = v.toS(IM.air.cursor.x, IM.air.cursor.y); ctx.fillStyle = IM.pinchOn ? warn : acc; ctx.beginPath(); ctx.arc(sx, sy, 5, 0, 7); ctx.fill(); }
}

/* ----- teach by showing ----- */
function teachToggle() {
  if (IM.teach.rec || IM.teach.countdown) return teachStop();
  if (!IM.active || IM.mode !== 'teach') { document.getElementById('imitMode').value = 'teach'; imitStop(); imitStart(); }
  IM.teach.countdown = 3;
  const btn = document.getElementById('btnTeach');
  const step = () => {
    if (!IM.teach.countdown) return;
    btn.textContent = `Starting in ${IM.teach.countdown}…`;
    if (--IM.teach.countdown === 0) {
      IM.teach.rec = true; IM.teach.pts = []; IM.teach.t0 = performance.now();
      btn.textContent = 'Stop recording'; btn.classList.add('on');
      log('Recording your hand movement…');
      setTimeout(() => { if (IM.teach.rec) teachStop(); }, 30000);
    } else setTimeout(step, 1000);
  };
  step();
}

function teachFrame(target, tMs) {
  if (!IM.teach.rec || tMs - IM.teach.lastT < 100) return;
  IM.teach.lastT = tMs;
  const last = IM.teach.pts[IM.teach.pts.length - 1];
  if (!last || Math.hypot(target.x - last.x, target.y - last.y, target.z - last.z) > 0.5) IM.teach.pts.push({ x: target.x, y: target.y, z: target.z });
  document.getElementById('teachCount').textContent = `${IM.teach.pts.length} points`;
}

function teachStop(silent) {
  const btn = document.getElementById('btnTeach');
  IM.teach.countdown = 0;
  btn.textContent = 'Record a movement'; btn.classList.remove('on');
  if (!IM.teach.rec) return;
  IM.teach.rec = false;
  if (IM.teach.pts.length >= 2) {
    const n = S.takes.filter(t => t.name.startsWith('Shown')).length + 1;
    S.takes.push({ name: 'Shown ' + n, pts: IM.teach.pts, use: true });
    renderTakes();
    if (!silent) log(`Saved your movement as “Shown ${n}” in Record & learn (${IM.teach.pts.length} points).`, 'ok');
  } else if (!silent) log('Too short — move your hand while recording.', 'warn');
  IM.teach.pts = [];
}
