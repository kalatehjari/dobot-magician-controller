/* ===================== SMART: DANCE ===================== */
const D = {
  src: 'file', analysis: null, frames: [], idx: 0, playing: false, choreo: null,
  actx: null, mediaNode: null, micStream: null, micNode: null, analyser: null, tracker: null,
  pending: [], nextBeat: null, beatIdx: 0, metroStart: 0, timer: null, curMove: '', lastBeatFlash: 0,
  taps: [], trail: [], center: null, lastSongT: 0, fileName: '',
};

function danceSetting(id, def) { const v = parseFloat(document.getElementById(id).value); return Number.isFinite(v) ? v : def; }

function audioCtx() {
  if (!D.actx) D.actx = new (window.AudioContext || window.webkitAudioContext)();
  if (D.actx.state === 'suspended') D.actx.resume();
  return D.actx;
}

function enabledMoves() {
  return Array.from(document.querySelectorAll('#moveChips input:checked')).map(i => i.value);
}

function renderMoveChips() {
  const box = document.getElementById('moveChips');
  box.innerHTML = Object.entries(DANCE_MOVES).filter(([k]) => k !== 'freeze').map(([k, m]) =>
    `<label class="chipbox"><input type="checkbox" value="${k}" checked> ${m.label}</label>`).join('');
}

function danceCentre() {
  if (D.center) return D.center;
  const B = smartBox(S.limits);
  return { x: B.xMid, y: 0, z: B.zMid + 0.15 * B.zHalf };
}

// Amplitude (mm) from the size slider and energy, capped so moves stay inside the smart box.
function danceAmp(energy) {
  const B = smartBox(S.limits);
  const cap = Math.min(B.xHalf / 1.3, B.yHalf / 1.6, B.zHalf / 1.3);
  const base = danceSetting('danceSize', 30) * danceSetting('danceEnergy', 1);
  return Math.min(cap, base * (0.55 + 0.65 * energy));
}

function setDanceInfo(text) { document.getElementById('danceInfo').textContent = text; }

/* ----- music file: decode + analyse ----- */
async function danceLoadFile(file) {
  danceStop();
  const audio = document.getElementById('danceAudio');
  if (audio.dataset.url) URL.revokeObjectURL(audio.dataset.url);
  audio.dataset.url = URL.createObjectURL(file);
  audio.src = audio.dataset.url;
  D.fileName = file.name;
  setDanceInfo(`Analysing “${file.name}”…`);
  await sleep(30);
  const buf = await audioCtx().decodeAudioData(await file.arrayBuffer());
  const n = buf.length, mono = new Float32Array(n);
  for (let c = 0; c < buf.numberOfChannels; c++) { const ch = buf.getChannelData(c); for (let i = 0; i < n; i++) mono[i] += ch[i] / buf.numberOfChannels; }
  await sleep(10);
  const t0 = performance.now();
  D.analysis = analyzeAudio(mono, buf.sampleRate);
  const a = D.analysis;
  setDanceInfo(`${file.name}: ${a.bpm.toFixed(1)} BPM · ${a.beats.length} beats · ${(a.duration / 60).toFixed(1)} min · analysed in ${((performance.now() - t0) / 1000).toFixed(1)} s`);
  log(`Music analysed: ${a.bpm.toFixed(1)} BPM, ${a.beats.length} beats.`, 'ok');
  drawDance();
}

function buildFileTimeline() {
  const a = D.analysis;
  // Start segments on a bar line: drop the first beats before the detected bar phase.
  const beats = a.beats.slice(a.barPhase), energy = a.energy.slice(a.barPhase);
  D.choreo = new Choreographer({ seed: Math.floor(danceSetting('danceSeed', 7)), moves: enabledMoves() });
  D.frames = D.choreo.timeline(beats, energy);
  // energy per frame: the energy of the beat the frame belongs to
  let bi = 0;
  for (const f of D.frames) { while (bi < beats.length - 1 && beats[bi + 1] <= f.t) bi++; f.e = energy[bi] ?? 0.5; }
  D.idx = 0;
}

/* ----- start / stop ----- */
async function danceStart() {
  if (D.playing) return;
  if (!S.dev) log('Not connected — dancing as a preview on screen only.', 'warn');
  if (S.running) return log('Another job is running. Press STOP first.', 'warn');
  D.src = document.getElementById('danceSrc').value;
  D.trail = []; D.pending = []; D.nextBeat = null; D.beatIdx = 0;
  D.choreo = new Choreographer({ seed: Math.floor(danceSetting('danceSeed', 7)), moves: enabledMoves() });
  if (D.src === 'file') {
    if (!D.analysis) return log('Choose a music file first.', 'warn');
    buildFileTimeline();
    const audio = document.getElementById('danceAudio');
    await audio.play();
  } else if (D.src === 'mic') {
    try { await micStart(); } catch (e) { return log('Microphone failed: ' + e.message, 'err'); }
  } else {
    D.metroStart = audioCtx().currentTime + 0.3;
  }
  D.playing = true;
  await smartSpeed(danceSetting('danceSpeed', 220), danceSetting('danceSpeed', 220) * 1.2);
  D.timer = setInterval(danceTick, 12);
  document.getElementById('btnDance').textContent = 'Stop dancing';
  document.getElementById('btnDance').classList.add('on');
  log(`Dancing (${D.src === 'file' ? 'music file' : D.src === 'mic' ? 'microphone' : 'metronome'}). Press Esc or STOP to halt.`, 'ok');
}

function danceStop(fromHalt) {
  if (!D.playing && !D.timer) return;
  D.playing = false;
  clearInterval(D.timer); D.timer = null;
  const audio = document.getElementById('danceAudio');
  if (!audio.paused) audio.pause();
  micStop();
  document.getElementById('btnDance').textContent = 'Start dancing';
  document.getElementById('btnDance').classList.remove('on');
  D.curMove = '';
  if (!fromHalt && S.dev) { smartSpeed(S.speed.live, S.speed.accel).then(() => sendNow(danceCentre())); }
  drawDance();
}
M.haltHooks.push(() => danceStop(true));

/* ----- microphone ----- */
async function micStart() {
  const ctx = audioCtx();
  D.micStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
  D.micNode = ctx.createMediaStreamSource(D.micStream);
  D.analyser = ctx.createAnalyser();
  D.analyser.fftSize = 2048; D.analyser.smoothingTimeConstant = 0;
  D.micNode.connect(D.analyser);
  D.tracker = new LiveBeatTracker();
  D.spec = new Float32Array(D.analyser.frequencyBinCount);
  D.wave = new Float32Array(D.analyser.fftSize);
  D.maxBin = Math.floor(8000 / (ctx.sampleRate / 2) * D.analyser.frequencyBinCount);
}

function micStop() {
  if (D.micStream) D.micStream.getTracks().forEach(t => t.stop());
  try { if (D.micNode) D.micNode.disconnect(); } catch (e) {}
  D.micStream = null; D.micNode = null; D.analyser = null;
}

function metronomeClick(at, accent) {
  if (!document.getElementById('danceClick').checked) return;
  const ctx = audioCtx(), o = ctx.createOscillator(), g = ctx.createGain();
  o.frequency.value = accent ? 1500 : 1000;
  g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(0.3, at + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, at + 0.06);
  o.connect(g).connect(ctx.destination); o.start(at); o.stop(at + 0.08);
}

/* ----- the scheduler: runs every 12 ms ----- */
function danceTick() {
  if (!D.playing) return;
  const lat = danceSetting('danceLatency', 150) / 1000;
  let now, due = null;
  if (D.src === 'file') {
    const audio = document.getElementById('danceAudio');
    now = audio.currentTime;
    if (audio.ended) { danceStop(); return; }
    if (audio.paused) return;
    if (now + 0.5 < D.lastSongT) {                  // user seeked backwards
      D.idx = D.frames.findIndex(f => f.t - lat > now); if (D.idx < 0) D.idx = D.frames.length;
    }
    D.lastSongT = now;
    while (D.idx < D.frames.length && D.frames[D.idx].t - lat <= now) { due = D.frames[D.idx]; D.idx++; }
    if (due && now - (due.t - lat) > 0.25) due = null;   // too late (after a seek forward): skip
  } else {
    const ctx = audioCtx(); now = ctx.currentTime;
    if (D.src === 'mic') {
      D.analyser.getFloatFrequencyData(D.spec);
      D.analyser.getFloatTimeDomainData(D.wave);
      let s = 0; for (const v of D.wave) s += v * v;
      D.tracker.push(D.spec, now, Math.sqrt(s / D.wave.length), D.maxBin);
    }
    const bpm = D.src === 'mic' ? D.tracker.bpm : danceSetting('danceBpm', 110);
    const ready = D.src === 'metro' || (bpm > 0 && D.tracker.confidence > 1.1);
    if (ready) {
      const P = 60 / bpm;
      if (D.nextBeat === null) D.nextBeat = D.src === 'mic' ? D.tracker.nextBeatAfter(now) : D.metroStart;
      while (D.nextBeat !== null && D.nextBeat < now + 0.35) {
        const energy = D.src === 'mic' ? D.tracker.energy : danceSetting('danceMetroEnergy', 0.6);
        for (const f of D.choreo.beatFrames(D.beatIdx, D.nextBeat, P, energy)) D.pending.push({ ...f, e: energy });
        if (D.src === 'metro') metronomeClick(D.nextBeat, D.beatIdx % 4 === 0);
        D.beatIdx++;
        D.nextBeat = D.src === 'mic' ? (D.tracker.nextBeatAfter(D.nextBeat + P * 0.5) ?? D.nextBeat + P) : D.nextBeat + P;
      }
    }
    while (D.pending.length && D.pending[0].t - lat <= now) due = D.pending.shift();
    if (D.src === 'mic' && performance.now() - (D.lastInfo || 0) > 300) {
      D.lastInfo = performance.now();
      setDanceInfo(ready ? `Microphone: ${D.tracker.bpm.toFixed(1)} BPM · confidence ${D.tracker.confidence.toFixed(2)} · energy ${(D.tracker.energy * 100).toFixed(0)}%`
        : `Listening… ${D.tracker.bpm ? D.tracker.bpm.toFixed(0) + ' BPM?' : 'no steady beat yet'}`);
    }
  }
  if (due) {
    const C = danceCentre(), target = danceTarget(due.o, C, danceAmp(due.e ?? 0.5));
    D.curMove = DANCE_MOVES[due.move] ? DANCE_MOVES[due.move].label : due.move;
    D.trail.push({ y: target.y - C.y, z: target.z - C.z, t: performance.now() });
    if (D.trail.length > 40) D.trail.shift();
    D.lastBeatFlash = performance.now();
    sendNow(target, 1);
  }
  if (performance.now() - (D.lastDraw || 0) > 50) { D.lastDraw = performance.now(); drawDance(); }
}

function tapTempo() {
  const t = performance.now() / 1000;
  D.taps = D.taps.filter(x => t - x < 3).concat(t);
  if (D.taps.length >= 3) {
    const d = D.taps.slice(1).map((x, i) => x - D.taps[i]).sort((a, b) => a - b);
    const bpm = 60 / d[Math.floor(d.length / 2)];
    if (bpm >= 40 && bpm <= 220) {
      document.getElementById('danceBpm').value = bpm.toFixed(1);
      document.getElementById('danceSrc').value = 'metro';
      if (D.playing && D.src === 'metro') { D.metroStart = audioCtx().currentTime + 60 / bpm; D.nextBeat = null; D.pending = []; }
      setDanceInfo(`Tap tempo: ${bpm.toFixed(1)} BPM`);
    }
  }
}

/* ----- visual ----- */
function drawDance() {
  const cv = document.getElementById('danceCanvas');
  if (!cv || !document.getElementById('tab-dance').classList.contains('active')) return;
  const ctx = setupCanvas(cv);
  const W = cv.clientWidth, H = cv.clientHeight;
  const css = getComputedStyle(document.documentElement);
  const acc = css.getPropertyValue('--accent').trim(), muted = css.getPropertyValue('--muted').trim(), line = css.getPropertyValue('--line').trim(), ink = css.getPropertyValue('--ink').trim();
  // left: front view of the moves (y → horizontal, z → vertical), with trail
  const half = Math.min(W * 0.45, H) / 2 - 10, cx = Math.min(W * 0.45, H) / 2 + 6, cy = H / 2;
  ctx.strokeStyle = line; ctx.strokeRect(cx - half, cy - half, half * 2, half * 2);
  ctx.fillStyle = muted; ctx.font = '11px system-ui'; ctx.fillText('front view (robot facing you)', cx - half, cy - half - 4 < 10 ? 10 : cy - half - 4);
  const amp = Math.max(1, danceAmp(1) * 1.7);
  const now = performance.now();
  D.trail.forEach((p, i) => {
    const a = (i + 1) / D.trail.length;
    ctx.fillStyle = `rgba(37,99,235,${0.15 + 0.6 * a})`;
    ctx.beginPath(); ctx.arc(cx - (p.y / amp) * half, cy - (p.z / amp) * half, 3 + 4 * a, 0, 7); ctx.fill();
  });
  const flash = Math.max(0, 1 - (now - D.lastBeatFlash) / 250);
  ctx.strokeStyle = acc; ctx.lineWidth = 2 + 6 * flash;
  ctx.beginPath(); ctx.arc(cx, cy, 10 + 18 * flash, 0, 7); ctx.stroke(); ctx.lineWidth = 1;
  // right: song energy and beats, or the live onset envelope
  const x0 = Math.min(W * 0.45, H) + 20, w = W - x0 - 10;
  if (w < 60) return;
  ctx.fillStyle = ink; ctx.font = '13px system-ui';
  ctx.fillText(D.playing ? `Move: ${D.curMove || '…'}` : 'Ready', x0, 18);
  if (D.src === 'file' && D.analysis) {
    const a = D.analysis, dur = a.duration || 1, audio = document.getElementById('danceAudio');
    ctx.strokeStyle = acc; ctx.beginPath();
    a.beats.forEach((b, i) => { const x = x0 + (b / dur) * w, y = H - 12 - a.energy[i] * (H - 70); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke();
    ctx.fillStyle = muted; ctx.fillText(`${a.bpm.toFixed(1)} BPM · energy over the song`, x0, 36);
    const px = x0 + (audio.currentTime / dur) * w;
    ctx.strokeStyle = ink; ctx.beginPath(); ctx.moveTo(px, 44); ctx.lineTo(px, H - 8); ctx.stroke();
  } else if (D.src === 'mic' && D.tracker && D.tracker.env.length) {
    const env = D.tracker.env, mx = Math.max(...env) || 1;
    ctx.strokeStyle = acc; ctx.beginPath();
    env.forEach((v, i) => { const x = x0 + (i / env.length) * w, y = H - 12 - (v / mx) * (H - 70); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke();
    ctx.fillStyle = muted; ctx.fillText('live onsets (last 8 s)', x0, 36);
  } else {
    ctx.fillStyle = muted; ctx.fillText(D.src === 'metro' ? `Metronome ${danceSetting('danceBpm', 110)} BPM` : 'Load a song, use the microphone, or tap a tempo.', x0, 36);
  }
}
