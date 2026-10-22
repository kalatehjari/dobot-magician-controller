/* ===================== SMOOTH & QUIET MOTION: profiles, glide following, quiet-speed finder ===================== */
const motionProfile = () => MOTION_PROFILES[S.motion.profile] || MOTION_PROFILES.quiet;
const followGlide = () => S.motion.follow === 'glide';

// Every speed change goes through here (Dobot.setSpeed): the profile caps acceleration and speed, so
// dance, imitation and reactions are gentler in Quiet mode too.
function motionCaps(v, a) {
  const P = motionProfile();
  return { v: Math.min(v, P.speedCap), a: Math.min(a, P.accelCap) };
}

function syncMotionUI() {
  for (const id of ['mo-profile', 'plot-feel']) { const el = document.getElementById(id); if (el) el.value = S.motion.profile; }
  const f = document.getElementById('mo-follow'); if (f) f.value = S.motion.follow;
}

// Choosing a feel sets the speeds and accelerations (which can still be fine-tuned in Setup).
function applyProfile(name, announce = true) {
  const P = MOTION_PROFILES[name];
  if (!P) return;
  S.motion.profile = name;
  S.speed = { ...S.speed, ...P.speeds };
  const cp = document.getElementById('plot-cpacc'); if (cp) cp.value = P.cpAcc;
  const hop = document.getElementById('plot-hopmin'); if (hop) hop.value = P.hopMin;
  writeSetup(); saveSettings(); syncMotionUI();
  GL.paramsKey = '';
  if (S.dev && !S.running) S.dev.setSpeed(S.speed.live, S.speed.accel).catch(() => {});
  if (S.plot && S.plot.stats) renderPlotStats();
  if (announce) log(`Motion feel: ${P.label} — pen ${P.speeds.draw} mm/s, travel ${P.speeds.travel} mm/s, acceleration ${P.speeds.accel} mm/s².`, 'ok');
}

/* ----- glide: following along a smoothed path, sent as continuous-path moves ----- */
const GL = { owner: null, target: null, st: null, t: 0, sentAt: 0, last: null, sending: false, paramsKey: '' };

function glideLimits() {
  const P = motionProfile(), v = GL.owner === 'mouse' ? S.speed.live : S.speed.smart;
  return { vMax: Math.max(10, Math.min(v, P.speedCap)), aMax: P.glideAccel, omega: P.glideOmega, sendMs: P.sendMs };
}
function glideSet(owner, p) {
  if (!GL.st) {
    const b = S.cmd || S.pos;
    GL.st = { x: b.x, y: b.y, z: b.z, vx: 0, vy: 0, vz: 0 };
    GL.last = { x: b.x, y: b.y, z: b.z }; GL.t = performance.now(); GL.sentAt = 0;
  }
  GL.owner = owner; GL.target = { x: p.x, y: p.y, z: p.z };
}
// Let go: the reference brakes smoothly to a stop instead of halting on the spot.
function glideRelease(owner) {
  if (owner && GL.owner !== owner) return;
  GL.owner = null;
  if (GL.st) { const s = glideStopPoint(GL.st, glideLimits().aMax); GL.target = clampTarget(s.x, s.y, s.z); }
}
function glideReset() { Object.assign(GL, { owner: null, target: null, st: null, paramsKey: '' }); }

setInterval(async () => {
  if (!GL.st) return;
  if (!S.dev || S.running || S.alarm.length || M.seqBusy || cal.open || AC.open) { glideReset(); return; }
  const now = performance.now(), dt = Math.min(0.1, Math.max(0.005, (now - GL.t) / 1000)), lim = glideLimits();
  GL.t = now;
  const tgt = GL.target || GL.st;
  GL.st = glideStep(GL.st, tgt, dt, lim);
  const rest = Math.hypot(GL.st.vx, GL.st.vy, GL.st.vz) < 0.5 && Math.hypot(tgt.x - GL.st.x, tgt.y - GL.st.y, tgt.z - GL.st.z) < 0.3;
  if (GL.sending || now - GL.sentAt < lim.sendMs) return;
  const p = rest ? tgt : GL.st, d = Math.hypot(p.x - GL.last.x, p.y - GL.last.y, p.z - GL.last.z);
  if (d < (rest ? 0.05 : 0.4)) { if (rest && !GL.owner) glideReset(); return; }
  GL.sending = true;
  try {
    const key = `${lim.vMax}|${lim.aMax}`;
    if (GL.paramsKey !== key) { await S.dev.setCPParams(lim.aMax, lim.vMax, lim.aMax); GL.paramsKey = key; }
    if (await queueRoom(3)) {
      const c = clampTarget(p.x, p.y, p.z);
      await S.dev.cp(c.x, c.y, c.z, lim.vMax);
      S.cmd = c; GL.last = c; GL.sentAt = now;
      GL.sent = (GL.sent || 0) + 1;
    }
  } catch (e) { log('Glide move error: ' + e.message, 'err'); glideReset(); }
  finally { GL.sending = false; }
}, 30);
M.haltHooks.push(glideReset);

/* ----- quiet-speed finder: listen to the arm at different speeds ----- */
const QT = { running: false, res: null, picks: null, sim: false, bars: [] };
const QT_DRAW = [15, 20, 25, 30, 35, 40, 50, 60], QT_TRAVEL = [60, 80, 100, 130];

async function openLevelMeter() {
  if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) throw new Error('This browser cannot use a microphone here.');
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const src = ctx.createMediaStreamSource(stream), hp = ctx.createBiquadFilter(), an = ctx.createAnalyser();
  hp.type = 'highpass'; hp.frequency.value = 150;                  // ignore room rumble below 150 Hz
  an.fftSize = 2048; src.connect(hp); hp.connect(an);
  const buf = new Float32Array(an.fftSize);
  const read = () => { an.getFloatTimeDomainData(buf); let s = 0; for (const x of buf) s += x * x; return Math.sqrt(s / buf.length); };
  return { read, stop: () => { stream.getTracks().forEach(t => t.stop()); ctx.close().catch(() => {}); } };
}

// The simulator makes no sound: a made-up curve (louder with speed, a resonance near 30 and 100 mm/s)
// lets the feature be tried; results are labelled as examples.
function qtSimulatedDb(v, kind) {
  return kind === 'draw' ? 3 + 0.06 * v + 6 * Math.exp(-(((v - 30) / 5) ** 2)) : 5 + 0.03 * v + 5 * Math.exp(-(((v - 100) / 12) ** 2));
}

function qtStatus(t) { document.getElementById('qtStatus').textContent = t; }

async function quietSpeedTest() {
  if (QT.running) return;
  if (!S.dev) return log('Connect the arm (or start the simulator) first.', 'warn');
  if (S.running || S.alarm.length) return log('Wait until the arm is free and no alarm is shown.', 'warn');
  QT.running = true; QT.sim = S.sim; QT.res = { draw: [], travel: [] }; QT.picks = null;
  const btn = document.getElementById('btnQuietTest'); btn.disabled = true;
  document.getElementById('qtApply').hidden = true;
  const gen = S.gen; let meter = null, samples = [], sampler = 0;
  try {
    if (!QT.sim) {
      qtStatus('Asking for the microphone…');
      try { meter = await openLevelMeter(); }
      catch (e) { throw new Error('No microphone available (' + e.message + '). Connect a webcam or headset microphone, or choose a Motion feel by ear.'); }
      sampler = setInterval(() => samples.push({ t: performance.now(), rms: meter.read() }), 25);
    }
    // a 60 mm line in the air above the middle of the green zone
    const z0 = drawZone(), x = (z0.rIn + z0.rOut) / 2;
    let zT = Math.min(S.limits.zMax, S.limits.zUp + 10);
    const reach = z => !(S.model && S.model.ok) || [-30, 30].every(y => magReachable(x, y, z, S.model, 1));
    if (!reach(zT)) zT = S.limits.zUp;
    if (!reach(zT)) throw new Error('The test line is outside the reach — run Auto-calibrate first.');
    const A = { x, y: -30, z: zT }, B = { x, y: 30, z: zT };
    S.running = true; glideReset();
    const P = motionProfile(), cpAcc = parseFloat(plotOpt('plot-cpacc')) || P.cpAcc;
    await S.dev.setSpeed(60, S.speed.accel);
    await S.dev.ptp(A.x, A.y, A.z, 0, 2); await S.dev.drain(gen);
    let bg = 1;
    if (!QT.sim) {
      qtStatus('Listening to the room (keep quiet for 2 seconds)…');
      const t0 = performance.now(); await sleep(1800);
      const s = samples.filter(q => q.t > t0 + 300).map(q => q.rms).sort((p, q) => p - q);
      bg = Math.max(1e-6, s[Math.floor(s.length / 2)] || 1e-6);
    }
    let from = A, to = B;
    const pass = async (kind, v) => {
      if (gen !== S.gen) throw new Error('Stopped');
      qtStatus(`Testing ${kind === 'draw' ? 'drawing' : 'travel'} speed ${v} mm/s…`);
      const t0 = performance.now();
      if (kind === 'draw') {
        await S.dev.setCPParams(cpAcc, v, cpAcc);
        const pts = [...splitSegment(from, to, 3), to];
        for (const p of pts) {
          while (((S.dev.lastAccepted - await S.dev.queueIndex()) | 0) >= 20) { await sleep(10); if (gen !== S.gen) throw new Error('Stopped'); }
          await S.dev.cp(p.x, p.y, p.z, v);
        }
      } else {
        await S.dev.setSpeed(v, S.speed.accel);
        await S.dev.ptp(to.x, to.y, to.z, 0, 2);
      }
      await S.dev.drain(gen);
      const t1 = performance.now(), T = t1 - t0;
      const db = QT.sim ? qtSimulatedDb(v, kind) : levelDb(samples.filter(q => q.t >= t0 + 0.25 * T && q.t <= t1 - 0.25 * T).map(q => q.rms), bg);
      QT.res[kind].push({ v, db, secs: T / 1000 });
      [from, to] = [to, from];
      drawQuietChart();
      await sleep(QT.sim ? 30 : 400);                     // let the arm settle so passes don't overlap
    };
    for (const v of QT_DRAW) await pass('draw', v);
    for (const v of QT_TRAVEL) await pass('travel', v);
    QT.picks = { draw: pickQuiet(QT.res.draw), travel: pickQuiet(QT.res.travel) };
    drawQuietChart();
    document.getElementById('qtPick').textContent = `Picked: drawing ${QT.picks.draw} mm/s, travel ${QT.picks.travel} mm/s — the quietest, or within 1 dB of it but faster` + (QT.sim ? ' (simulator: example numbers, not a real measurement)' : '');
    document.getElementById('qtApply').hidden = false;
    qtStatus(QT.sim ? 'Done (simulator — no real sound was measured).' : 'Done. Lower bars are quieter.');
    log(`Quiet-speed test: drawing ${QT.picks.draw} mm/s and travel ${QT.picks.travel} mm/s were the quietest${QT.sim ? ' (simulated)' : ''}.`, 'ok');
  } catch (e) {
    qtStatus(e.message === 'Stopped' ? 'Stopped.' : e.message);
    if (e.message !== 'Stopped') log('Quiet-speed test: ' + e.message, 'err');
  } finally {
    clearInterval(sampler); if (meter) meter.stop();
    if (S.running && QT.running) { S.running = false; if (S.dev) S.dev.setSpeed(S.speed.live, S.speed.accel).catch(() => {}); }
    QT.running = false; btn.disabled = false;
  }
}

// Loudness per speed: one bar per tested speed, dB above the room's background; the picked speed in
// each group (quietest, or within 1 dB of it but faster) is drawn solid and labelled.
function drawQuietChart() {
  const cv = document.getElementById('qtCanvas');
  cv.hidden = false;
  const ctx = setupCanvas(cv), W = cv.clientWidth, H = cv.clientHeight;
  const ink = cssVar('--ink'), muted = cssVar('--muted'), line = cssVar('--line'), acc = cssVar('--accent');
  const groups = [['draw', 'Drawing speed (mm/s)'], ['travel', 'Travel speed (mm/s)']];
  const all = [...QT.res.draw, ...QT.res.travel].filter(r => Number.isFinite(r.db));
  const top = Math.max(6, ...all.map(r => r.db)) * 1.15, pad = { l: 44, r: 12, t: 16, b: 38 };
  const n = QT_DRAW.length + QT_TRAVEL.length + 1, slot = (W - pad.l - pad.r) / n, bw = Math.max(6, Math.min(22, slot * 0.5));
  const y = db => H - pad.b - Math.max(0, db) / top * (H - pad.t - pad.b);
  ctx.font = '11px system-ui'; ctx.strokeStyle = line; ctx.fillStyle = muted; ctx.lineWidth = 1;
  for (let g = 0; g <= top; g += top > 18 ? 6 : 3) {
    ctx.beginPath(); ctx.moveTo(pad.l, y(g)); ctx.lineTo(W - pad.r, y(g)); ctx.stroke();
    ctx.fillText(`${g} dB`, 4, y(g) + 4);
  }
  QT.bars = [];
  let i = 0;
  for (const [kind, title] of groups) {
    const list = kind === 'draw' ? QT_DRAW : QT_TRAVEL, x0 = pad.l + i * slot;
    list.forEach((v, j) => {
      const r = QT.res[kind].find(q => q.v === v), cx = pad.l + (i + j + 0.5) * slot;
      ctx.fillStyle = muted; ctx.textAlign = 'center'; ctx.fillText(String(v), cx, H - pad.b + 14);
      if (!r || !Number.isFinite(r.db)) return;
      const pick = QT.picks && QT.picks[kind] === v, top2 = y(r.db), base = y(0), rad = Math.min(4, bw / 2, base - top2);
      ctx.fillStyle = acc; ctx.globalAlpha = pick ? 1 : 0.35;
      ctx.beginPath(); ctx.moveTo(cx - bw / 2, base); ctx.lineTo(cx - bw / 2, top2 + rad); ctx.quadraticCurveTo(cx - bw / 2, top2, cx - bw / 2 + rad, top2);
      ctx.lineTo(cx + bw / 2 - rad, top2); ctx.quadraticCurveTo(cx + bw / 2, top2, cx + bw / 2, top2 + rad); ctx.lineTo(cx + bw / 2, base); ctx.closePath(); ctx.fill();
      ctx.globalAlpha = 1;
      if (pick) { ctx.fillStyle = ink; ctx.fillText('pick', cx, top2 - 5); }
      QT.bars.push({ kind, v, r, x0: cx - slot / 2, x1: cx + slot / 2 });
    });
    ctx.fillStyle = muted; ctx.textAlign = 'center';
    ctx.fillText(title, x0 + list.length * slot / 2, H - 6);
    i += list.length + 1;
  }
  ctx.textAlign = 'left';
}

document.getElementById('qtCanvas').addEventListener('pointermove', ev => {
  const r = ev.target.getBoundingClientRect(), x = ev.clientX - r.left, b = QT.bars.find(q => x >= q.x0 && x < q.x1), out = document.getElementById('qtHover');
  out.hidden = !b;
  if (b) out.textContent = `${b.kind === 'draw' ? 'Drawing' : 'Travel'} at ${b.v} mm/s: ${b.r.db.toFixed(1)} dB above the room · one pass took ${b.r.secs.toFixed(1)} s`;
});
document.getElementById('qtCanvas').addEventListener('pointerleave', () => { document.getElementById('qtHover').hidden = true; });

/* ----- wiring ----- */
document.getElementById('mo-profile').onchange = e => applyProfile(e.target.value);
document.getElementById('plot-feel').onchange = e => applyProfile(e.target.value);
document.getElementById('mo-follow').onchange = e => {
  S.motion.follow = e.target.value; saveSettings();
  if (!followGlide()) glideReset();
  log(followGlide() ? 'Following glides along a smoothed path.' : 'Following moves point to point.', 'ok');
};
document.getElementById('btnQuietTest').onclick = () => quietSpeedTest();
document.getElementById('btnQtUse').onclick = () => {
  if (!QT.picks) return;
  S.speed.draw = QT.picks.draw; S.speed.travel = QT.picks.travel;
  writeSetup(); saveSettings();
  if (S.plot && S.plot.stats) renderPlotStats();
  log(`Using the quietest speeds: pen ${S.speed.draw} mm/s, travel ${S.speed.travel} mm/s.`, 'ok');
};
syncMotionUI();
{ const P = motionProfile(), cp = document.getElementById('plot-cpacc'), hop = document.getElementById('plot-hopmin'); cp.value = P.cpAcc; hop.value = P.hopMin; }
if (S.motionMigrated) log('Motion is now set to Quiet & smooth: gentler acceleration, lower speeds, continuous drawing and gliding. Change it in Setup → Smooth & quiet motion.', 'ok');
