/* ===================== CENTRE & CALIBRATE WIZARD ===================== */
// While calibrating, the arm may travel further than the saved limits so the true ends can be found.
// This wider envelope still stops short of the base and of the table; the arm's own alarms remain active.
const CAL_ENVELOPE = { minR: 30, maxR: 360, zMin: -60, zMax: 200 };

const CAL_STEPS = [
  { id: 'centre', title: 'Centre the arm', text: 'The arm moves to its factory centre (home) position using its own reference sensors. Keep hands and objects clear first.' },
  { id: 'near', title: 'Closest point', text: 'Jog the tip to the closest point to the base you want to allow, with the arm folded in and clear of the base.' },
  { id: 'far', title: 'Farthest point forward', text: 'Jog the tip as far forward (away from the base) as you want to allow.' },
  { id: 'left', title: 'Far left', text: 'Jog the tip to the far left at mid reach.' },
  { id: 'right', title: 'Far right', text: 'Jog the tip to the far right at mid reach.' },
  { id: 'low', title: 'Lowest point', text: 'At mid reach, jog the tip down slowly until just before it would hit the table.' },
  { id: 'high', title: 'Highest point', text: 'Jog the tip up as high as you want to allow.' },
  { id: 'down', title: 'Pen-down height', text: 'Lower the tip until it just touches the paper. This is the drawing height.' },
  { id: 'up', title: 'Pen-up height', text: 'Raise the tip just clear of the paper. This is the travel height.' },
  { id: 'review', title: 'Review and apply', text: '' },
];

const cal = { step: 0, pts: {}, open: false };

// Wider clamp used only during calibration.
function envelopeClamp(x, y, z) {
  const E = CAL_ENVELOPE;
  let r = Math.hypot(x, y);
  if (r < 1e-6) { x = E.minR; y = 0; r = E.minR; }
  const rr = clamp(r, E.minR, E.maxR);
  return { x: x * rr / r, y: y * rr / r, z: clamp(z, E.zMin, E.zMax) };
}

function openWizard() {
  if (!S.dev) return log('Connect or start the simulator first.', 'warn');
  if (S.running) return log('A job is running. Press STOP first.', 'warn');
  cal.step = 0; cal.pts = {}; cal.open = true;
  S.calib = true;
  document.getElementById('wizard').hidden = false;
  renderWizard();
}

function closeWizard() {
  cal.open = false; S.calib = false;
  document.getElementById('wizard').hidden = true;
}

function captureNow() {
  const id = CAL_STEPS[cal.step].id;
  cal.pts[id] = { x: S.pos.x, y: S.pos.y, z: S.pos.z };
  log(`Captured ${CAL_STEPS[cal.step].title}: X ${S.pos.x.toFixed(1)} Y ${S.pos.y.toFixed(1)} Z ${S.pos.z.toFixed(1)}`, 'ok');
  cal.step++;
  renderWizard();
}

async function calibJog(d) {
  if (!S.dev || S.alarm.length || S.running) return;
  const step = parseFloat(document.getElementById('wiz-step').value) || 1;
  const base = S.pos;
  const t = envelopeClamp(base.x + d.x * step, base.y + d.y * step, base.z + d.z * step);
  S.cmd = t;
  try { await S.dev.ptp(t.x, t.y, t.z, 0, 2); }
  catch (e) { log('Jog failed: ' + e.message, 'err'); }
}

function computeCalibration() {
  const p = cal.pts, m = 5, angMargin = 2;
  const rNear = Math.hypot(p.near.x, p.near.y), rFar = Math.hypot(p.far.x, p.far.y);
  const thL = Math.atan2(p.left.y, p.left.x) * 180 / Math.PI;
  const thR = Math.atan2(p.right.y, p.right.x) * 180 / Math.PI;
  const L = {
    minR: Math.round(rNear + m), maxR: Math.round(rFar - m),
    thMin: Math.round(thR + angMargin), thMax: Math.round(thL - angMargin),
    zMin: Math.round(p.low.z + 2), zMax: Math.round(p.high.z - 2),
    zDown: Math.round(p.down.z * 10) / 10, zUp: Math.round(p.up.z * 10) / 10,
    homeX: S.limits.homeX, homeY: S.limits.homeY, homeZ: S.limits.homeZ,
  };
  const mid = (L.minR + L.maxR) / 2;
  const homeR = Math.hypot(L.homeX, L.homeY);
  if (homeR < L.minR || homeR > L.maxR) { L.homeX = Math.round(mid); L.homeY = 0; }
  L.homeZ = clamp(L.homeZ, L.zMin, L.zMax);
  return L;
}

function validateCalibration(L) {
  if (!(L.minR > 0 && L.minR + 20 < L.maxR)) throw new Error('Reach range is too small or inverted.');
  if (!(L.thMin < L.thMax)) throw new Error('Left/right angles are inverted — check that Far left was on the left.');
  if (!(L.zMin < L.zMax)) throw new Error('Lowest point must be below highest point.');
  if (L.zDown < L.zMin || L.zDown > L.zMax) throw new Error('Pen-down height is outside the Z range.');
  if (L.zUp < L.zMin || L.zUp > L.zMax) throw new Error('Pen-up height is outside the Z range.');
  if (L.zUp <= L.zDown) throw new Error('Pen-up must be higher than pen-down.');
}

function applyCalibration(L) {
  validateCalibration(L);
  S.limits = { ...L, penSet: true };
  writeSetup();
  saveSettings();
  log('Calibration saved. The arm will now refuse moves outside these limits.', 'ok');
  closeWizard();
  drawAll();
}

function renderWizard() {
  const body = document.getElementById('wizBody');
  const step = CAL_STEPS[cal.step];
  const dots = CAL_STEPS.map((s, i) => `<span class="dot ${i < cal.step ? 'done' : i === cal.step ? 'cur' : ''}"></span>`).join('');
  let content = '';
  if (step.id === 'centre') {
    content = `<div class="row"><button class="primary" data-act="centre">Centre arm now</button>
      <button data-act="skipCentre" class="ghost">Already centred — next</button></div>`;
  } else if (step.id === 'review') {
    try {
      const L = computeCalibration();
      validateCalibration(L);
      content = `<table class="sum"><tr><td>Reach</td><td>${L.minR} – ${L.maxR} mm from base</td></tr>
        <tr><td>Base angle</td><td>${L.thMin}° to ${L.thMax}° (negative = right)</td></tr>
        <tr><td>Height</td><td>${L.zMin} – ${L.zMax} mm</td></tr>
        <tr><td>Pen down / up</td><td>${L.zDown} / ${L.zUp} mm</td></tr>
        <tr><td>Home point</td><td>${L.homeX}, ${L.homeY}, ${L.homeZ}</td></tr></table>
        <div class="hint">Margins of 5 mm (reach), 2° (angle) and 2 mm (height) are kept inside the points you captured.</div>
        <div class="row"><button class="primary" data-act="apply">Save &amp; apply</button>
        <button data-act="back" class="ghost">Back</button></div>`;
    } catch (e) {
      content = `<div class="warnbox">${e.message}</div><div class="row"><button data-act="restart">Start again</button>
        <button data-act="back" class="ghost">Back</button></div>`;
    }
  } else {
    content = `<div class="jog">
        <button data-d="0,1,0">Y+ left</button>
        <button data-d="1,0,0">X+ away</button>
        <button data-d="0,-1,0">Y- right</button>
        <button data-d="-1,0,0">X- in</button>
        <button data-d="0,0,1">Z+ up</button>
        <button data-d="0,0,-1">Z- down</button>
      </div>
      <div class="row"><label class="f">Step (mm)<select id="wiz-step"><option value="0.5">0.5</option><option value="1" selected>1</option><option value="5">5</option><option value="10">10</option></select></label>
      <button class="primary" data-act="capture">Capture this point</button>
      <button data-act="back" class="ghost" ${cal.step <= 1 ? 'disabled' : ''}>Back</button></div>`;
  }
  body.innerHTML = `<div class="dots">${dots}</div>
    <h3>${step.title}</h3><p class="muted">${step.text}</p>
    <div class="pos muted">Current: X ${S.pos.x.toFixed(1)} · Y ${S.pos.y.toFixed(1)} · Z ${S.pos.z.toFixed(1)}</div>
    ${content}
    <div class="row" style="margin-top:12px"><button data-act="cancel" class="ghost">Cancel calibration</button></div>`;
}

async function wizardAction(act, dataset) {
  if (act === 'centre') { await goHome(); if (S.alarm.length === 0) { cal.step++; } }
  else if (act === 'skipCentre') cal.step++;
  else if (act === 'capture') captureNow();
  else if (act === 'back') { cal.step = Math.max(0, cal.step - 1); }
  else if (act === 'restart') { cal.step = 1; cal.pts = {}; }
  else if (act === 'apply') { try { applyCalibration(computeCalibration()); } catch (e) { log(e.message, 'err'); } return; }
  else if (act === 'cancel') { closeWizard(); log('Calibration cancelled — saved limits unchanged.'); return; }
  renderWizard();
}

document.getElementById('wizBody').addEventListener('click', ev => {
  const jog = ev.target.closest('button[data-d]');
  if (jog) {
    const [x, y, z] = jog.dataset.d.split(',').map(Number);
    calibJog({ x, y, z });
    return;
  }
  const act = ev.target.closest('button[data-act]');
  if (act) wizardAction(act.dataset.act, act.dataset);
});
