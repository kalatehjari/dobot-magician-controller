/* ===================== AUTO-CALIBRATION (from the Magician's geometry) ===================== */
// 1. Read the arm's pose and joint angles, home it, read again (one small extra move if it was
//    already at home). 2. Check the readings fit the Magician geometry and measure the tool offsets.
// 3. Compute the reachable working area. 4. The user lowers the pen onto the paper — the only
//    manual step — and the limits are recomputed for that height.
const AC = { open: false, step: 'intro', busy: false, msg: '', home: null };

function acSet(step, msg = '') { AC.step = step; AC.msg = msg; renderAutoCal(); }

function openAutoCal() {
  if (!S.dev) return log('Connect or start the simulator first.', 'warn');
  if (S.running) return log('A job is running. Press STOP first.', 'warn');
  if (cal.open) closeWizard();
  AC.open = true;
  document.getElementById('autocal').hidden = false;
  acSet('intro');
}

function closeAutoCal() {
  AC.open = false;
  document.getElementById('autocal').hidden = true;
}

async function acHome() {
  await S.dev.home();
  await S.dev.drain(S.gen);
  await sleep(300);
  const al = await S.dev.alarms();
  if (al.length) { S.alarm = al; renderAlarm(); throw new Error('The arm reported an alarm while homing: ' + alarmText(al)); }
}

async function acMoveAndWait(x, y, z) {
  await S.dev.ptp(x, y, z, 0, 2);
  await S.dev.drain(S.gen);
  S.pos = await S.dev.pose(); S.cmd = { x: S.pos.x, y: S.pos.y, z: S.pos.z };
  const al = await S.dev.alarms();
  if (al.length) { S.alarm = al; renderAlarm(); throw new Error('Alarm: ' + alarmText(al)); }
}

function applyAutoLimits(L, penSet) {
  S.limits = { ...S.limits, ...L, penSet };
  writeSetup(); saveSettings(); drawAll();
}

async function autoCalMeasure() {
  if (AC.busy) return;
  AC.busy = true;
  try {
    if (S.alarm.length) throw new Error('Clear the alarm (red bar) first.');
    acSet('measuring', 'Reading the arm’s position and joint angles…');
    const poses = [await S.dev.pose()];
    acSet('measuring', 'Centring (homing) — the arm moves to its home position…');
    await acHome();
    const pB = await S.dev.pose();
    poses.push(pB);
    let v = validateModel(poses);
    if (!v.ok && v.spread < 3) {
      // Already at home: take a second reading after one small move.
      acSet('measuring', 'Taking a second reading (one small move)…');
      const o = estimateOffsets(pB), m0 = { dR: o.dR, dZ: o.dZ }, r = Math.hypot(pB.x, pB.y), th = pB.j1 * DEG;
      const pick = [[r, pB.z - 30], [r - 25, pB.z], [r + 25, pB.z], [r, pB.z + 25]]
        .find(([rr, zz]) => magReachable(rr * Math.cos(th), rr * Math.sin(th), zz, m0, 5));
      if (!pick) throw new Error('Could not find a safe position for a second reading.');
      await acMoveAndWait(pick[0] * Math.cos(th), pick[0] * Math.sin(th), pick[1]);
      poses.push(await S.dev.pose());
      v = validateModel(poses);
    }
    if (!v.ok) {
      const why = !v.plausible ? 'the tool offsets look implausible'
        : v.baseErr > 1.5 ? `the base angle is off by ${v.baseErr.toFixed(1)}°`
        : `readings differ by ${v.maxDev.toFixed(1)} mm`;
      throw new Error(`The joint readings don't match the Magician geometry (${why}). Use manual calibration instead.`);
    }
    S.model = { dR: +v.dR.toFixed(2), dZ: +v.dZ.toFixed(2), ok: true, maxDev: +v.maxDev.toFixed(2), at: new Date().toISOString() };
    AC.home = { x: pB.x, y: pB.y, z: pB.z };
    const L = autoLimits(S.model, null, AC.home);
    if (!L) throw new Error('Could not compute a working area from these readings.');
    applyAutoLimits(L, false);
    log(`Auto-calibration: geometry confirmed (within ${S.model.maxDev} mm); tool ${S.model.dR} mm out, ${S.model.dZ} mm up from the wrist.`, 'ok');
    acSet('measuring', 'Moving over the middle of the drawing area…');
    const midR = (L.minR + L.maxR) / 2;
    const target = magReachable(midR, 0, AC.home.z, S.model, 3) ? { x: midR, y: 0, z: AC.home.z } : AC.home;
    await acMoveAndWait(target.x, target.y, target.z);
    acSet('pen');
  } catch (e) {
    acSet('error', e.message);
    log('Auto-calibration: ' + e.message, 'err');
  } finally { AC.busy = false; }
}

async function acJog(dz) {
  if (AC.busy || !S.model) return;
  AC.busy = true;
  try {
    const p = await S.dev.pose();
    const z = p.z + dz;
    if (!magReachable(p.x, p.y, z, S.model, 1)) { acSet('pen', dz < 0 ? 'The arm cannot go any lower here.' : 'The arm cannot go any higher here.'); return; }
    await acMoveAndWait(p.x, p.y, z);
    acSet('pen');
  } catch (e) { acSet('error', e.message); }
  finally { AC.busy = false; }
}

async function acSetPaper() {
  if (AC.busy) return;
  AC.busy = true;
  try {
    const p = await S.dev.pose();
    const zPaper = Math.round(p.z * 10) / 10;
    const L = autoLimits(S.model, zPaper, AC.home || p);
    if (!L) throw new Error('The arm cannot draw usefully at this height. Raise the paper (or the pen) and try again.');
    applyAutoLimits(L, true);
    await acMoveAndWait(p.x, p.y, L.zUp);
    log(`Pen-down height set to ${zPaper} mm; pen-up ${L.zUp} mm. Limits updated for this paper height.`, 'ok');
    acSet('done');
  } catch (e) { acSet('error', e.message); }
  finally { AC.busy = false; }
}

function acSummary() {
  const L = S.limits, b = S.model ? reachBand(S.model, L.zDown - 0.5, L.zUp + 0.5, 2) : null;
  const sq = b ? fitRectForAspect(b.rIn, b.rOut, 6, 1) : null;
  return `<table class="sum">
    <tr><td>Geometry check</td><td>${S.model ? `matches within ${S.model.maxDev} mm` : '—'}</td></tr>
    <tr><td>Drawing reach</td><td>${b ? `${b.rIn}–${b.rOut} mm from the base` : '—'}</td></tr>
    <tr><td>Largest square drawing</td><td>${sq ? `${sq.w.toFixed(0)} × ${sq.w.toFixed(0)} mm` : '—'}</td></tr>
    <tr><td>Base angle</td><td>${L.thMin}° to ${L.thMax}°</td></tr>
    <tr><td>Pen down / up</td><td>${L.zDown} / ${L.zUp} mm</td></tr>
    <tr><td>Height range (smart modes)</td><td>${L.zMin} to ${L.zMax} mm</td></tr></table>`;
}

function renderAutoCal() {
  const body = document.getElementById('autocalBody');
  if (!body) return;
  const L = S.limits;
  const steps = ['intro', 'measuring', 'pen', 'done'];
  const idx = Math.max(0, steps.indexOf(AC.step === 'error' ? 'measuring' : AC.step));
  const dots = steps.map((s, i) => `<span class="dot ${i < idx ? 'done' : i === idx ? 'cur' : ''}"></span>`).join('');
  let html = '';
  if (AC.step === 'intro') {
    const saved = S.model && S.model.ok && L.penSet;
    html = `<h3>Calibrate the arm</h3>
      <p class="muted">The app centres the arm (it moves to its home position), reads its joint angles and works out the reachable drawing area from the Magician's geometry. Then you lower the pen onto the paper — that's the only step you do by hand.</p>
      ${S.settingsMigrated ? '<div class="warnbox">Your old limits came from an earlier version and allowed positions the arm cannot reach. Please calibrate.</div>' : ''}
      ${saved ? `<div class="hint">Saved calibration: pen-down at ${L.zDown} mm, geometry checked ${new Date(S.model.at).toLocaleDateString()}.</div>` : ''}
      <div class="row"><button class="primary" data-ac="start">Start auto-calibration</button>
      ${saved ? '<button data-ac="keep">Use saved calibration</button>' : ''}
      <button class="ghost" data-ac="manual">Manual calibration…</button>
      <button class="ghost" data-ac="close">Not now</button></div>
      <div class="hint">Keep the space around the arm clear. Put paper under the arm, roughly in front of it.</div>`;
  } else if (AC.step === 'measuring') {
    html = `<h3>Measuring…</h3><p class="muted">${AC.msg}</p><div class="spinner"></div>`;
  } else if (AC.step === 'pen') {
    html = `<h3>Lower the pen onto the paper</h3>
      <p class="muted">Use the buttons until the pen tip just touches the paper, then press “This is the paper”. Go slowly near the paper.</p>
      <div class="pos">Pen height: <b>${S.pos.z.toFixed(1)} mm</b></div>
      <div class="jog">
        <button data-dz="-10">▼ 10 mm</button><button data-dz="-2">▼ 2 mm</button><button data-dz="-0.5">▼ 0.5 mm</button>
        <button data-dz="10">▲ 10 mm</button><button data-dz="2">▲ 2 mm</button><button data-dz="0.5">▲ 0.5 mm</button>
      </div>
      ${AC.msg ? `<div class="warnbox">${AC.msg}</div>` : ''}
      <div class="row"><button class="primary" data-ac="paper">This is the paper</button><button class="ghost" data-ac="close">Finish later</button></div>`;
  } else if (AC.step === 'done') {
    html = `<h3>Calibrated</h3>${acSummary()}
      <div class="hint">Every move is now checked against the arm's real reach at its height, so drawings stay where the arm can go.</div>
      <div class="row"><button class="primary" data-ac="test">Draw a test square</button><button data-ac="close">Close</button></div>`;
  } else if (AC.step === 'error') {
    html = `<h3>Calibration stopped</h3><div class="warnbox">${AC.msg}</div>
      <div class="row"><button class="primary" data-ac="start">Try again</button><button data-ac="manual">Manual calibration…</button><button class="ghost" data-ac="close">Close</button></div>`;
  }
  body.innerHTML = `<div class="dots">${dots}</div>${html}`;
}

document.getElementById('autocalBody').addEventListener('click', ev => {
  const dz = ev.target.closest('button[data-dz]');
  if (dz) return acJog(parseFloat(dz.dataset.dz));
  const b = ev.target.closest('button[data-ac]');
  if (!b) return;
  const a = b.dataset.ac;
  if (a === 'start') autoCalMeasure();
  else if (a === 'keep') { closeAutoCal(); log('Using the saved calibration.', 'ok'); }
  else if (a === 'manual') { closeAutoCal(); openWizard(); }
  else if (a === 'paper') acSetPaper();
  else if (a === 'test') { closeAutoCal(); showTab('plot'); testSquare(); }
  else if (a === 'close') closeAutoCal();
});

// Live check: the pose the arm reports should match the geometry model's prediction from its joints.
setInterval(() => {
  const el = document.getElementById('modelStatus');
  if (!el) return;
  if (!(S.model && S.model.ok)) { el.textContent = 'Not calibrated yet — limits are conservative defaults.'; return; }
  const p = S.pos;
  if (!S.dev || p.j2 === undefined) { el.textContent = `Calibrated: tool ${S.model.dR} mm out, ${S.model.dZ} mm up from the wrist.`; return; }
  const f = magFK(p.j2, p.j3, S.model), err = Math.hypot(Math.hypot(p.x, p.y) - f.r, p.z - f.z);
  el.textContent = `Calibrated: tool ${S.model.dR} mm out, ${S.model.dZ} mm up. Live geometry check: ${err.toFixed(1)} mm${err > 3 ? ' — re-calibrate (tool changed?)' : ''}.`;
}, 1000);
