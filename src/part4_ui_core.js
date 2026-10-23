/* ===================== APP STATE & CONNECTION ===================== */
// Safe values until auto-calibration: a band every Magician tool reaches, kept well above the table.
const DEFAULTS = {
  limits: { minR: 200, maxR: 295, thMin: -85, thMax: 85, zMin: 0, zMax: 110, zUp: 30, zDown: 15, homeX: 240, homeY: 0, homeZ: 60, penSet: false },
  speed: { ...MOTION_PROFILES.quiet.speeds },
  motion: { profile: 'quiet', follow: 'glide' },
};
const SETTINGS_VERSION = 3;
const S = {
  dev: null, sim: false, gen: 0, running: false,
  pos: { x: 0, y: 0, z: 0, r: 0 },   // last polled real pose
  cmd: null,                         // last commanded target
  limits: structuredClone(DEFAULTS.limits),
  speed: structuredClone(DEFAULTS.speed),
  motion: structuredClone(DEFAULTS.motion),
  live: false, dragging: false, target: null, lastKey: '', sending: false,
  polling: false, nudgeBusy: false, alarm: [], calib: false, tick: 0,
  rec: { active: false, pts: [] },
  takes: [], learned: null,
  plot: { objects: [], sel: null, strokes: null, ops: null, start: null, stats: null, placeVer: 0, opsVer: -1, drawnIds: [] },
  paper: { jobs: [] },               // what has been drawn on the current sheet (shown in red)
  lastPoll: 0,
  model: null,                       // geometry calibration {dR, dZ, ok, maxDev} — see part 31
  paused: false,
};
const DEBUG = { frames: false };

function log(msg, cls) {
  const box = document.getElementById('log');
  const d = document.createElement('div');
  d.className = cls || '';
  d.textContent = new Date().toLocaleTimeString() + '  ' + msg;
  box.prepend(d);
  while (box.childElementCount > 300) box.lastChild.remove();
}

function setConnected(on) {
  const pill = document.getElementById('pill');
  const btn = document.getElementById('btnConnect');
  if (on) {
    pill.textContent = S.sim ? 'Simulator' : S.link && S.link !== 'USB' ? `Connected · ${S.link}` : 'Connected';
    pill.className = 'pill ' + (S.sim ? 'sim' : 'ok');
    btn.textContent = 'Disconnect';
  } else {
    pill.textContent = 'Not connected';
    pill.className = 'pill';
    btn.textContent = 'Connect USB';
  }
}

function updatePoseReadout() {
  const p = S.pos;
  document.getElementById('pose').textContent =
    `X ${p.x.toFixed(1)}  Y ${p.y.toFixed(1)}  Z ${p.z.toFixed(1)}  R ${Math.hypot(p.x, p.y).toFixed(1)} mm`;
}

/* ----- settings (saved per browser; safe fallback if storage is blocked) ----- */
function readSetup() {
  const v = id => parseFloat(document.getElementById(id).value);
  const L = {
    minR: v('lim-minR'), maxR: v('lim-maxR'), zMin: v('lim-zMin'), zMax: v('lim-zMax'),
    zUp: v('lim-zUp'), zDown: v('lim-zDown'), homeX: v('home-x'), homeY: v('home-y'), homeZ: v('home-z'),
    thMin: v('lim-thMin'), thMax: v('lim-thMax'),
  };
  const sp = { live: v('spd-live'), accel: v('spd-accel'), draw: v('spd-draw'), travel: v('spd-travel'), smart: v('spd-smart') };
  if (Object.values(L).some(x => !Number.isFinite(x)) || Object.values(sp).some(x => !Number.isFinite(x))) {
    throw new Error('Setup has an empty or non-numeric field');
  }
  if (!(L.minR > 0 && L.minR < L.maxR)) throw new Error('Need 0 < min reach < max reach');
  if (!(L.zMin < L.zMax)) throw new Error('Need Z min < Z max');
  if (!(L.thMin < L.thMax)) throw new Error('Need base angle min < max');
  if (L.zUp > L.zMax || L.zUp < L.zMin || L.zDown > L.zMax || L.zDown < L.zMin) throw new Error('Pen heights must lie within Z range');
  if (Math.hypot(L.homeX, L.homeY) < L.minR || Math.hypot(L.homeX, L.homeY) > L.maxR) throw new Error('Home point is outside the reachable area');
  // A pen-down height typed or captured here counts as user-defined.
  L.penSet = !!S.limits.penSet || L.zDown !== S.limits.zDown;
  L.bandHeight = S.limits.bandHeight;
  S.limits = L; S.speed = sp;
  saveSettings();
}

function saveSettings() {
  try { localStorage.setItem('magician-settings', JSON.stringify({ v: SETTINGS_VERSION, limits: S.limits, speed: S.speed, model: S.model, motion: S.motion })); } catch (e) {}
}

function writeSetup() {
  const set = (id, val) => { document.getElementById(id).value = val; };
  set('lim-minR', S.limits.minR); set('lim-maxR', S.limits.maxR);
  set('lim-zMin', S.limits.zMin); set('lim-zMax', S.limits.zMax);
  set('lim-zUp', S.limits.zUp); set('lim-zDown', S.limits.zDown);
  set('lim-thMin', S.limits.thMin); set('lim-thMax', S.limits.thMax);
  set('home-x', S.limits.homeX); set('home-y', S.limits.homeY); set('home-z', S.limits.homeZ);
  set('spd-live', S.speed.live); set('spd-accel', S.speed.accel); set('spd-draw', S.speed.draw); set('spd-travel', S.speed.travel); set('spd-smart', S.speed.smart);
}

function loadSetup() {
  try {
    const saved = JSON.parse(localStorage.getItem('magician-settings') || 'null');
    if (saved && saved.v === SETTINGS_VERSION) {
      S.limits = { ...DEFAULTS.limits, ...saved.limits };
      S.speed = { ...DEFAULTS.speed, ...saved.speed };
      S.model = saved.model || null;
      if (saved.motion) S.motion = { ...DEFAULTS.motion, ...saved.motion };
      else { S.speed = { ...S.speed, ...MOTION_PROFILES.quiet.speeds }; S.motionMigrated = true; }   // first start after the update
    } else if (saved) {
      // Older versions allowed 100–320 mm, which the arm cannot reach at table height. Keep speeds only.
      S.speed = { ...DEFAULTS.speed, ...saved.speed, draw: DEFAULTS.speed.draw };
      S.settingsMigrated = true;
    }
  } catch (e) {}
  writeSetup();
}

/* ----- connection ----- */
async function connectSerial() {
  if (!('serial' in navigator)) throw new Error('Web Serial is not available here. Open this file in Google Chrome or Microsoft Edge.');
  // No vendor filter: show every serial device so the arm's USB-serial chip is never hidden.
  const port = await navigator.serial.requestPort();
  const io = new SerialIO(port);
  await io.open();
  S.dev = new Dobot(io);
  S.sim = false; S.link = 'USB';
}

async function connectSim() {
  S.dev = new Dobot(new SimIO());
  S.sim = true; S.link = 'Simulator';
}

// mode: false / 'usb' (USB cable), true / 'sim' (simulator), 'ble' (Bluetooth module), 'wifi' (Wi-Fi module via the bridge).
async function connectFlow(mode) {
  readSetup();
  const simulate = mode === true || mode === 'sim';
  try {
    if (simulate) await connectSim();
    else if (mode === 'ble') await connectBle();
    else if (mode === 'wifi') await connectWifi();
    else await connectSerial();
    await S.dev.init();
    S.pos = await S.dev.pose();
    S.cmd = { ...S.pos };
    updatePoseReadout();
    setConnected(true);
    S.alarm = await S.dev.alarms();
    renderAlarm();
    if (S.alarm.length) log('Alarm present: ' + alarmText(S.alarm) + '. Use the red bar to clear it.', 'err');
    log(simulate ? 'Simulator started — no hardware is moved.' : `Connected to Magician over ${S.link}.`, 'ok');
    openAutoCal();   // centre the arm, measure it, then the user sets the pen height
  } catch (e) {
    S.dev = null;
    setConnected(false);
    log('Connection failed: ' + e.message, 'err');
  }
}

async function disconnect() {
  await stopAll();
  try { if (S.dev && S.dev.io && S.dev.io.close) await S.dev.io.close(); } catch (e) {}
  S.dev = null; S.live = false; S.alarm = []; renderAlarm(); setLiveButton();
  setConnected(false);
  log('Disconnected.');
}

/* Background pose polling + recording sampler (one timer, never overlaps). Faster while a job runs,
   so the pen on the Plotter map moves smoothly. */
setInterval(async () => {
  if (!S.dev || S.polling) return;
  const now = performance.now();
  if (now - S.lastPoll < (S.running ? 50 : 140)) return;
  S.lastPoll = now;
  S.polling = true;
  try {
    S.pos = await S.dev.pose();
    updatePoseReadout();
    if (typeof paperTick === 'function') paperTick();
    if (++S.tick % 4 === 0) await checkAlarms();
    if (S.rec.active) {
      const last = S.rec.pts[S.rec.pts.length - 1];
      const moved = !last || Math.hypot(S.pos.x - last.x, S.pos.y - last.y) > 0.3 || Math.abs(S.pos.z - last.z) > 0.3;
      if (moved) S.rec.pts.push({ x: S.pos.x, y: S.pos.y, z: S.pos.z });
      document.getElementById('recCount').textContent = S.rec.pts.length + ' points';
    }
    drawAll();
  } catch (e) { /* transient read errors are ignored while polling */ }
  S.polling = false;
}, 25);

/* ===================== MOUSE CONTROL ===================== */
const mouseCv = document.getElementById('mouseCanvas');

// Maps the robot's (x,y) plane to the canvas. Base sits at bottom-centre; forward is up.
// R: radius to fit (default: the outer reach in Setup).
function viewOf(cv, R = S.limits.maxR) {
  const W = cv.clientWidth, H = cv.clientHeight, pad = 24;
  // Floor keeps radii positive when the canvas is hidden (zero size).
  const k = Math.max(1e-3, Math.min((W - 2 * pad) / (2 * (R + 10)), (H - 2 * pad) / (R + 20)));
  const bx = W / 2, by = H - pad - 10 * k;
  return {
    W, H, k, bx, by, R,
    toS: (x, y) => [bx - y * k, by - x * k],
    toW: (sx, sy) => ({ x: (by - sy) / k, y: (bx - sx) / k }),
  };
}

function setupCanvas(cv) {
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
  }
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return ctx;
}

// Background: reach annulus (front half), grid, base marker. opts.band = false leaves out the band.
function drawBase(cv, v, ctx, opts = {}) {
  const css = getComputedStyle(document.documentElement);
  const ink = css.getPropertyValue('--muted').trim(), line = css.getPropertyValue('--line').trim();
  const fill = css.getPropertyValue('--reach').trim(), acc = css.getPropertyValue('--accent').trim();
  const GR = v.R || S.limits.maxR;
  ctx.strokeStyle = line; ctx.lineWidth = 1;
  for (let g = -Math.floor(GR / 50) * 50; g <= GR; g += 50) {
    const [x1, y1] = v.toS(0, g), [x2, y2] = v.toS(GR + 10, g);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  }
  for (let g = 0; g <= GR; g += 50) {
    const [x1, y1] = v.toS(g, -GR), [x2, y2] = v.toS(g, GR);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  }
  if (opts.band === false) {
    ctx.fillStyle = ink; ctx.font = '12px system-ui';
    ctx.fillText('base', v.bx + 6, v.by + 14);
    ctx.beginPath(); ctx.arc(v.bx, v.by, 4, 0, 2 * Math.PI); ctx.fill();
    ctx.fillText('forward +X', v.bx + 8, v.by - 6);
    return;
  }
  // reachable band
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.arc(v.bx, v.by, S.limits.maxR * v.k, Math.PI, 2 * Math.PI);
  ctx.arc(v.bx, v.by, S.limits.minR * v.k, 2 * Math.PI, Math.PI, true);
  ctx.closePath(); ctx.fill();
  ctx.strokeStyle = acc; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.arc(v.bx, v.by, S.limits.maxR * v.k, Math.PI, 2 * Math.PI); ctx.stroke();
  ctx.beginPath(); ctx.arc(v.bx, v.by, S.limits.minR * v.k, Math.PI, 2 * Math.PI); ctx.stroke();
  ctx.fillStyle = ink; ctx.font = '12px system-ui';
  ctx.fillText('base', v.bx + 6, v.by + 14);
  ctx.beginPath(); ctx.arc(v.bx, v.by, 4, 0, 2 * Math.PI); ctx.fill();
  ctx.fillText('forward +X', v.bx + 8, v.by - 8 - 4 * 0 - 14 * 0 - 6);
}

function drawMouse() {
  const ctx = setupCanvas(mouseCv);
  const v = viewOf(mouseCv);
  drawBase(mouseCv, v, ctx);
  const css = getComputedStyle(document.documentElement);
  const acc = css.getPropertyValue('--accent').trim(), warn = css.getPropertyValue('--warn').trim();
  if (S.cmd) {
    const [sx, sy] = v.toS(S.cmd.x, S.cmd.y);
    ctx.strokeStyle = warn; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(sx, sy, 8, 0, 2 * Math.PI); ctx.stroke();
  }
  if (S.dev && typeof drawLaser === 'function') drawLaser(ctx, v, S.pos, true);
  else { const [px, py] = v.toS(S.pos.x, S.pos.y); ctx.fillStyle = acc; ctx.beginPath(); ctx.arc(px, py, 6, 0, 2 * Math.PI); ctx.fill(); }
}

// Sends a move, clamped to limits. Keeps S.cmd in sync with what was actually commanded.
async function moveTo(x, y, z) {
  const t = clampTarget(x, y, z);
  if (S.alarm.length) throw new Error('Alarm active — clear it first (red bar).');
  S.cmd = t;
  if (!S.dev) { log('Not connected — connect or start the simulator first.', 'warn'); return; }
  await S.dev.ptp(t.x, t.y, t.z, 0, 2);
}

function setLiveButton() {
  const b = document.getElementById('btnLive');
  b.textContent = S.live ? 'Live follow: ON' : 'Live follow: OFF';
  b.classList.toggle('on', S.live);
}

// Live follow: streams the latest cursor target at a steady rate, never more than 2 moves queued.
// With "Glide" following the target goes to the smoothed continuous-path follower instead.
setInterval(async () => {
  if (!S.dev || !S.live || !S.target || S.sending || S.running || S.alarm.length) return;
  if (typeof followGlide === 'function' && followGlide()) {
    let t = clampTarget(S.target.x, S.target.y, S.target.z);
    if (typeof lockFollowTarget === 'function') t = lockFollowTarget('mouse', t);
    if (!GL.target || Math.hypot(t.x - GL.target.x, t.y - GL.target.y, t.z - GL.target.z) > 0.3 || GL.owner !== 'mouse') glideSet('mouse', t);
    return;
  }
  const key = S.target.x.toFixed(1) + ',' + S.target.y.toFixed(1) + ',' + S.target.z.toFixed(1);
  if (key === S.lastKey) return;
  S.sending = true;
  try {
    const cur = await S.dev.queueIndex();
    if (((S.dev.lastAccepted - cur) | 0) < 2) {
      let t = clampTarget(S.target.x, S.target.y, S.target.z);
      if (typeof lockFollowTarget === 'function') t = lockFollowTarget('mouse', t);   // safety lock: hold at the boundary
      await S.dev.ptp(t.x, t.y, t.z, 0, 2);
      S.cmd = t; S.lastKey = key;
    }
  } catch (e) { log('Live move error: ' + e.message, 'err'); }
  S.sending = false;
}, 60);

function mouseToWorld(ev) {
  const r = mouseCv.getBoundingClientRect();
  return viewOf(mouseCv).toW(ev.clientX - r.left, ev.clientY - r.top);
}

mouseCv.addEventListener('pointermove', ev => {
  const w = mouseToWorld(ev);
  const base = S.cmd || S.pos;
  document.getElementById('hover').textContent = `cursor  x ${w.x.toFixed(1)}  y ${w.y.toFixed(1)}  (Z ${base.z.toFixed(1)})`;
  if (S.dragging && S.live) S.target = { x: w.x, y: w.y, z: (S.cmd || S.pos).z };
});
mouseCv.addEventListener('pointerdown', async ev => {
  const w = mouseToWorld(ev);
  const z = (S.cmd || S.pos).z;
  if (S.live) {
    S.dragging = true; S.target = { x: w.x, y: w.y, z };
    mouseCv.setPointerCapture(ev.pointerId);
  } else {
    try { await moveTo(w.x, w.y, z); } catch (e) { log(e.message, 'err'); }
  }
});
mouseCv.addEventListener('pointerup', () => { S.dragging = false; });
mouseCv.addEventListener('wheel', async ev => {
  ev.preventDefault();
  const base = S.cmd || S.pos;
  const dz = ev.deltaY < 0 ? 1 : -1;
  try { await moveTo(base.x, base.y, base.z + dz, { small: true }); } catch (e) { log(e.message, 'err'); }
}, { passive: false });

document.getElementById('btnLive').onclick = () => {
  if (!S.dev) { log('Connect or start the simulator first.', 'warn'); return; }
  S.live = !S.live; S.target = null; S.lastKey = ''; setLiveButton();
  if (!S.live && typeof glideRelease === 'function') glideRelease('mouse');
  S.dev.setSpeed(S.speed.live, S.speed.accel).catch(() => {});
};

// Keyboard nudges: arrows = X/Y, PageUp/PageDown = Z. Shift = 10 mm, Alt = 0.1 mm.
document.addEventListener('keydown', async ev => {
  if (!document.getElementById('tab-mouse').classList.contains('active')) return;
  if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
  const step = ev.shiftKey ? 10 : ev.altKey ? 0.1 : 1;
  const d = { x: 0, y: 0, z: 0 };
  if (ev.key === 'ArrowUp') d.x = step; else if (ev.key === 'ArrowDown') d.x = -step;
  else if (ev.key === 'ArrowLeft') d.y = step; else if (ev.key === 'ArrowRight') d.y = -step;
  else if (ev.key === 'PageUp') d.z = step; else if (ev.key === 'PageDown') d.z = -step;
  else return;
  ev.preventDefault();
  if (S.nudgeBusy || !S.dev) return;
  S.nudgeBusy = true;
  const base = S.cmd || S.pos;
  try { await moveTo(base.x + d.x, base.y + d.y, base.z + d.z, { small: true }); }
  catch (e) { log(e.message, 'err'); }
  S.nudgeBusy = false;
});

document.getElementById('btnPenUp').onclick = () => withBase(b => moveTo(b.x, b.y, S.limits.zUp));
document.getElementById('btnPenDown').onclick = () => withBase(b => moveTo(b.x, b.y, S.limits.zDown));
document.getElementById('btnHome').onclick = () => moveTo(S.limits.homeX, S.limits.homeY, S.limits.homeZ, { exempt: true }).catch(e => log(e.message, 'err'));
document.getElementById('zSlider').oninput = e => document.getElementById('zVal').textContent = e.target.value;
document.getElementById('zSlider').onchange = e => withBase(b => moveTo(b.x, b.y, parseFloat(e.target.value)));
document.getElementById('btnSuction').onclick = async e => {
  if (!S.dev) return log('Not connected.', 'warn');
  S.suctionOn = !S.suctionOn; await S.dev.setSuction(S.suctionOn);
  e.target.textContent = S.suctionOn ? 'Suction: ON' : 'Suction: OFF';
};
document.getElementById('btnGripper').onclick = async e => {
  if (!S.dev) return log('Not connected.', 'warn');
  S.gripOn = !S.gripOn; await S.dev.setGripper(S.gripOn);
  e.target.textContent = S.gripOn ? 'Gripper: close' : 'Gripper: open';
};

function withBase(fn) {
  const b = S.cmd || S.pos;
  Promise.resolve(fn({ x: b.x, y: b.y, z: b.z })).catch(e => log(e.message, 'err'));
}

/* ===================== ALARMS, CENTRE ===================== */
async function checkAlarms() {
  const codes = await S.dev.alarms();
  const changed = codes.join() !== S.alarm.join();
  S.alarm = codes;
  if (changed) {
    renderAlarm();
    if (codes.length) {
      S.gen++; S.running = false;   // halt any running job immediately
      log('ALARM: ' + alarmText(codes) + '. Motion stopped. Check the arm, then clear.', 'err');
    }
  }
}

function renderAlarm() {
  const bar = document.getElementById('alarmBar');
  if (!S.alarm.length) { bar.hidden = true; return; }
  document.getElementById('alarmText').textContent = 'ALARM: ' + alarmText(S.alarm) + '. All motion is blocked.';
  bar.hidden = false;
}

async function goHome() {
  if (!S.dev) return log('Connect or start the simulator first.', 'warn');
  if (S.alarm.length) return log('Alarm active — clear it first (red bar).', 'err');
  if (S.running) return log('A job is running. Press STOP first.', 'warn');
  S.running = true;
  try {
    await S.dev.home();
    await S.dev.drain(S.gen);
    S.pos = await S.dev.pose();
    S.cmd = { ...S.pos };
    updatePoseReadout();
    log('Centred at factory home position.', 'ok');
  } catch (e) {
    log('Centre failed: ' + e.message, 'err');
  } finally {
    S.running = false;
  }
}
