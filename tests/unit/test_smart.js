// Unit tests for the Smart Controller engines (run: node tests/unit/test_smart.js)
const fs = require('fs');
const vm = require('vm');
const ctx = { console, Math, Float32Array, Float64Array, Int32Array, Uint8Array, Array, Object, Number, JSON, Infinity, NaN, isFinite };
ctx.S = { limits: { minR: 100, maxR: 320, thMin: -90, thMax: 90, zMin: -30, zMax: 150, zUp: 30, zDown: 0 } };
vm.createContext(ctx);
for (const f of ['part2_geometry.js', 'part20_smart_math.js', 'part21_moves.js', 'part22_beat.js']) {
  vm.runInContext(fs.readFileSync(require('path').join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
}
const E = (code) => vm.runInContext(code, ctx);
let fails = 0;
const t = (name, cond, extra = '') => { console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra ? '  ' + extra : '')); if (!cond) fails++; };

/* ---- filters ---- */
{
  const f = E('new OneEuro(1.0, 0.0)');
  let seed = 3; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) - 0.5;
  const out = []; for (let i = 0; i < 300; i++) out.push(f.filter(10 + rnd() * 2, i / 30));
  const tail = out.slice(100); const m = tail.reduce((a, b) => a + b) / tail.length;
  const sd = Math.sqrt(tail.reduce((a, b) => a + (b - m) ** 2, 0) / tail.length);
  t('OneEuro smooths jitter', sd < 0.2 && Math.abs(m - 10) < 0.2, `sd=${sd.toFixed(3)} (input sd≈0.58)`);
  const g = E('new OneEuro(1.0, 0.05)'); let y = 0; for (let i = 0; i < 60; i++) y = g.filter(i < 5 ? 0 : 100, i / 30);
  t('OneEuro follows a step', y > 95, `y=${y.toFixed(1)}`);
  const h = E('new Hyst(0.35, 0.5)'); const seq = [0.8, 0.4, 0.3, 0.45, 0.55, 0.3].map(v => h.update(v));
  t('Hyst inverted (pinch) on/off', JSON.stringify(seq) === JSON.stringify([false, false, true, true, false, true]), JSON.stringify(seq));
  const sl = E("new StableLabel(300,'neutral')");
  const r1 = sl.update('happy', 0), r2 = sl.update('happy', 200), r3 = sl.update('happy', 320);
  t('StableLabel waits for hold time', r1 === null && r2 === null && r3 && r3.to === 'happy');
}

/* ---- expressions ---- */
{
  const sc = (bs, base) => E(`expressionScores(${JSON.stringify(bs)}, ${JSON.stringify(base || null)})`);
  const pick = (bs, base) => E(`pickExpression(expressionScores(${JSON.stringify(bs)}, ${JSON.stringify(base || null)}), EXPR_THRESHOLDS, 'neutral')`);
  t('smile → happy', pick({ mouthSmileLeft: 0.8, mouthSmileRight: 0.75, cheekSquintLeft: 0.3, cheekSquintRight: 0.3 }) === 'happy');
  t('jaw open + brows up + wide eyes → surprised', pick({ jawOpen: 0.7, browInnerUp: 0.7, eyeWideLeft: 0.5, eyeWideRight: 0.5 }) === 'surprised');
  t('frown + inner brows up → sad', pick({ mouthFrownLeft: 0.6, mouthFrownRight: 0.6, browInnerUp: 0.5 }) === 'sad');
  t('brows down + sneer → angry', pick({ browDownLeft: 0.7, browDownRight: 0.7, noseSneerLeft: 0.4, noseSneerRight: 0.4 }) === 'angry');
  t('pucker → kiss', pick({ mouthPucker: 0.8 }) === 'kiss');
  t('resting face → neutral', pick({ mouthSmileLeft: 0.1, mouthSmileRight: 0.1, browInnerUp: 0.1 }) === 'neutral');
  t('baseline removes a resting smile', pick({ mouthSmileLeft: 0.45, mouthSmileRight: 0.45 }, { mouthSmileLeft: 0.4, mouthSmileRight: 0.4 }) === 'neutral');
  const tr = E('new ExpressionTracker(350)'); let ev = null;
  for (let ms = 0; ms <= 600; ms += 33) { const r = tr.update({ mouthSmileLeft: 0.85, mouthSmileRight: 0.85 }, null, ms); if (r) ev = { ...r, ms }; }
  t('tracker fires happy once stable', ev && ev.to === 'happy' && ev.ms >= 350, ev ? `at ${ev.ms} ms` : '');
  const w = E('new WinkDetector()'); let wink = null;
  for (let ms = 0; ms <= 1000; ms += 33) { const closed = ms >= 100 && ms <= 400; const r = w.update(closed ? 0.9 : 0.05, 0.05, ms); if (r) wink = r; }
  t('left wink detected', wink === 'left');
  const w2 = E('new WinkDetector()'); let fake = null;
  for (let ms = 0; ms <= 1000; ms += 33) { const closed = ms >= 100 && ms <= 300; const r = w2.update(closed ? 0.9 : 0.05, closed ? 0.9 : 0.05, ms); if (r) fake = r; }
  t('normal blink is not a wink', fake === null);
}

/* ---- head pose and nod/shake ---- */
{
  const face = (yawShift, pitchShift) => {
    const lm = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5, z: 0 }));
    lm[234] = { x: 0.4, y: 0.5 }; lm[454] = { x: 0.6, y: 0.5 }; lm[10] = { x: 0.5, y: 0.35 }; lm[152] = { x: 0.5, y: 0.65 };
    lm[33] = { x: 0.44, y: 0.45 }; lm[263] = { x: 0.56, y: 0.45 }; lm[1] = { x: 0.5 + yawShift, y: 0.5 + pitchShift };
    return lm;
  };
  ctx.__lm = face(0.03, 0); const hp = E('headPose(__lm, 4/3)');
  ctx.__lm = face(0, 0.03); const hp2 = E('headPose(__lm, 4/3)');
  t('head yaw sign', hp.yaw > 0.1 && Math.abs(hp.pitch) < 1e-9, `yaw=${hp.yaw.toFixed(3)}`);
  t('head pitch sign (looking down +)', hp2.pitch > 0.05 && Math.abs(hp2.yaw) < 1e-9, `pitch=${hp2.pitch.toFixed(3)}`);
  const run = (fn) => { const d = E('new HeadGestureDetector()'); let got = null; for (let ms = 0; ms <= 1400; ms += 33) { const [yw, pt] = fn(ms / 1000); const r = d.update(ms, yw, pt); if (r && !got) got = r; } return got; };
  t('nod detected', run(s => [0.005 * Math.sin(9 * s), 0.07 * Math.sin(2 * Math.PI * 2.2 * s)]) === 'nod');
  t('shake detected', run(s => [0.08 * Math.sin(2 * Math.PI * 2.0 * s), 0.004 * Math.sin(7 * s)]) === 'shake');
  t('slow look-down is not a nod', run(s => [0, 0.12 * s]) === null);
  t('tiny jitter ignored', run(s => [0.01 * Math.sin(40 * s), 0.01 * Math.cos(37 * s)]) === null);
}

/* ---- hands, arm pose, mapping ---- */
{
  const hand = (cx, cy, scale, pinch) => {
    const lm = Array.from({ length: 21 }, () => ({ x: cx, y: cy }));
    lm[0] = { x: cx, y: cy + 0.12 * scale }; lm[9] = { x: cx, y: cy }; lm[5] = { x: cx - 0.04 * scale, y: cy + 0.02 }; lm[17] = { x: cx + 0.05 * scale, y: cy + 0.03 };
    lm[4] = { x: cx - 0.05 * scale, y: cy - 0.02 }; lm[8] = pinch ? { x: cx - 0.045 * scale, y: cy - 0.025 } : { x: cx - 0.02 * scale, y: cy - 0.15 * scale };
    return lm;
  };
  ctx.__h = hand(0.5, 0.5, 1, false); const m0 = E('handMetrics(__h, 4/3)');
  ctx.__h = hand(0.5, 0.5, 1, true); const mp = E('handMetrics(__h, 4/3)');
  t('pinch ratio small when pinching', mp.pinch < 0.35 && m0.pinch > 0.6, `open=${m0.pinch.toFixed(2)} pinch=${mp.pinch.toFixed(2)}`);
  const cal = { cx: 0.5, cy: 0.5, palm: m0.palm };
  ctx.__cal = cal;
  ctx.__h = hand(0.35, 0.5, 1, false); const right = E('mapHandFront(handMetrics(__h,4/3), __cal, S.limits, {})');
  ctx.__h = hand(0.5, 0.35, 1, false); const up = E('mapHandFront(handMetrics(__h,4/3), __cal, S.limits, {})');
  ctx.__h = hand(0.5, 0.5, 1.4, false); const near = E('mapHandFront(handMetrics(__h,4/3), __cal, S.limits, {})');
  ctx.__h = hand(0.5, 0.5, 1, false); const mid = E('mapHandFront(handMetrics(__h,4/3), __cal, S.limits, {})');
  t('hand to your right → robot +Y (facing you)', right.y > 40 && Math.abs(right.z - mid.z) < 1e-6, `y=${right.y.toFixed(0)}`);
  t('hand up → robot higher', up.z > mid.z + 30, `z=${up.z.toFixed(0)} vs ${mid.z.toFixed(0)}`);
  t('hand toward camera → reach forward', near.x > mid.x + 20, `x=${near.x.toFixed(0)} vs ${mid.x.toFixed(0)}`);
  const inBounds = [right, up, near, mid].every(p => { const c = E(`clampTarget(${p.x},${p.y},${p.z})`); return Math.hypot(c.x - p.x, c.y - p.y, c.z - p.z) < 1e-6; });
  t('hand targets stay inside limits', inBounds);
  ctx.__rect = { cx: 200, cy: 0, w: 140, h: 360 };
  ctx.__h = hand(0.5, 0.5, 1, false); const c0 = E('mapHandToRect(handMetrics(__h,4/3), __cal, __rect, {})');
  ctx.__h = hand(0.3, 0.5, 1, false); const cR = E('mapHandToRect(handMetrics(__h,4/3), __cal, __rect, {})');
  t('air-draw: finger right → sketch right (robot -Y)', cR.y < c0.y - 20, `${c0.y.toFixed(0)} → ${cR.y.toFixed(0)}`);
  const pose = (wx, wy, wz) => {
    const lm = Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, visibility: 1 }));
    const wl = Array.from({ length: 33 }, () => ({ x: 0, y: 0, z: 0 }));
    lm[12] = { x: 0.45, y: 0.4, visibility: 1 }; lm[14] = { x: 0.45 + (wx - 0.45) / 2, y: 0.4 + (wy - 0.4) / 2, visibility: 1 }; lm[16] = { x: wx, y: wy, visibility: 1 };
    wl[12] = { x: 0, y: 0, z: 0 }; wl[14] = { x: 0.15, y: 0, z: wz / 2 }; wl[16] = { x: 0.3, y: 0, z: wz };
    return [lm, wl];
  };
  [ctx.__p, ctx.__w] = pose(0.25, 0.4, 0); const aR = E("mapArmPose(__p, __w, 'right', S.limits, {})");
  [ctx.__p, ctx.__w] = pose(0.45, 0.15, 0); const aUp = E("mapArmPose(__p, __w, 'right', S.limits, {})");
  [ctx.__p, ctx.__w] = pose(0.45, 0.55, -0.25); const aFwd = E("mapArmPose(__p, __w, 'right', S.limits, {})");
  t('arm out to your right → robot +Y', aR.y > 50, `y=${aR.y.toFixed(0)}`);
  t('arm raised → robot high', aUp.z > 90, `z=${aUp.z.toFixed(0)}`);
  t('arm toward camera → reach forward', aFwd.x > 260, `x=${aFwd.x.toFixed(0)}`);
}

/* ---- choreography and reactions ---- */
{
  const res = E(`(() => { const c = new Choreographer({ seed: 11 }); const beats = Array.from({length: 64}, (_, i) => i * 0.5);
    const en = beats.map((_, i) => i < 16 ? 0.2 : i < 40 ? 0.5 : 0.9); return c.timeline(beats, en); })()`);
  let mono = true, bounded = true; for (let i = 1; i < res.length; i++) if (res[i].t < res[i - 1].t) mono = false;
  for (const f of res) if (f.o.some(v => Math.abs(v) > 1.61)) bounded = false;
  const lowMoves = new Set(res.filter(f => f.t < 8).map(f => f.move)), highMoves = new Set(res.filter(f => f.t >= 20).map(f => f.move));
  t('choreography times increase', mono, `${res.length} keyframes`);
  t('choreography offsets bounded', bounded);
  t('calm music → calm moves', [...lowMoves].every(m => E(`DANCE_MOVES['${m}'].tiers.includes('low')`)), [...lowMoves].join(','));
  t('loud music → energetic moves', [...highMoves].every(m => E(`DANCE_MOVES['${m}'].tiers.includes('high')`)), [...highMoves].join(','));
  const again = E(`(() => { const c = new Choreographer({ seed: 11 }); const beats = Array.from({length: 64}, (_, i) => i * 0.5);
    const en = beats.map((_, i) => i < 16 ? 0.2 : i < 40 ? 0.5 : 0.9); return c.timeline(beats, en).map(f=>f.move).join(); })()`);
  t('same seed → same dance', again === res.map(f => f.move).join());
  const names = E('Object.keys(REACTIONS)');
  let allOk = true;
  for (const n of names) { const fr = E(`reactionFrames('${n}', {x:200,y:0,z:60}, 30)`); const last = fr[fr.length - 1];
    if (!fr.length || Math.hypot(last.x - 200, last.y, last.z - 60) > 1e-6 || fr.some(f => !(f.wait > 0))) allOk = false; }
  t('every reaction returns to where it started', allOk, `${names.length} reactions`);
}

/* ---- beat tracking ---- */
function synthTrack(bpm, secs, sr, seed) {
  const x = new Float32Array(Math.floor(secs * sr)); let s = seed;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647) * 2 - 1;
  const beat = 60 / bpm, start = 0.37;
  const truth = [];
  for (let tb = start; tb < secs - 0.3; tb += beat) {
    truth.push(tb);
    const i0 = Math.floor(tb * sr);
    for (let k = 0; k < 0.12 * sr; k++) { const env = Math.exp(-k / (0.025 * sr)); x[i0 + k] += 0.8 * env * Math.sin(2 * Math.PI * (60 + 90 * Math.exp(-k / (0.01 * sr))) * k / sr); }
    const j0 = Math.floor((tb + beat / 2) * sr);
    for (let k = 0; k < 0.04 * sr && j0 + k < x.length; k++) x[j0 + k] += 0.15 * Math.exp(-k / (0.006 * sr)) * rnd();
  }
  for (let i = 0; i < x.length; i++) x[i] += 0.01 * rnd();
  return { x, truth };
}
for (const [bpm, seed] of [[120, 5], [92, 9], [140, 21]]) {
  const sr = 44100, { x, truth } = synthTrack(bpm, 25, sr, seed);
  ctx.__x = x; const t0 = Date.now();
  const a = E('analyzeAudio(__x, 44100)'); const ms = Date.now() - t0;
  const errs = a.beats.filter(b => b > 1 && b < 24).map(b => Math.min(...truth.map(tt => Math.abs(tt - b))));
  errs.sort((p, q) => p - q); const med = errs[Math.floor(errs.length / 2)];
  t(`beat tracker ${bpm} BPM`, Math.abs(a.bpm - bpm) / bpm < 0.02 && med < 0.03, `found ${a.bpm.toFixed(1)} BPM, median beat error ${(med * 1000).toFixed(0)} ms, ${ms} ms to analyse`);
}
{
  const tr = E('new LiveBeatTracker()'); const bpm = 100, P = 60 / bpm, rate = 60;
  const spec = new Float32Array(256);
  for (let i = 0; i < rate * 9; i++) {
    const tt = i / rate; const since = ((tt - 0.2) % P + P) % P;
    spec.fill(-80); if (since < 3 / rate) for (let k = 0; k < 256; k++) spec[k] = -25 - k * 0.05;
    tr.push(spec, tt, since < 0.1 ? 0.3 : 0.05, 256);
  }
  const now = 9; const nb = tr.nextBeatAfter(now); const trueNext = 0.2 + Math.ceil((now - 0.2) / P) * P;
  t('live tracker tempo', Math.abs(tr.bpm - bpm) < 3, `bpm=${tr.bpm.toFixed(1)}`);
  t('live tracker predicts next beat', nb !== null && Math.abs(nb - trueNext) < 0.05, `pred ${nb && nb.toFixed(3)} vs ${trueNext.toFixed(3)}`);
}

console.log(fails ? `${fails} FAILED` : 'ALL PASS');
process.exitCode = fails ? 1 : 0;

/* ---- energy scale (added after the browser review) ---- */
{
  const sr = 22050, secs = 24, x = new Float32Array(sr * secs);
  // 12 s quiet (−14 dB) then 12 s loud, same 120 BPM pattern
  for (let tb = 0.3; tb < secs - 0.3; tb += 0.5) {
    const g = tb < 12 ? 0.2 : 1.0, i0 = Math.floor(tb * sr);
    for (let k = 0; k < 0.1 * sr; k++) x[i0 + k] += g * 0.8 * Math.exp(-k / (0.025 * sr)) * Math.sin(2 * Math.PI * 80 * k / sr);
  }
  ctx.__x2 = x;
  const a = E('analyzeAudio(__x2, 22050)');
  const quiet = a.energy.filter((_, i) => a.beats[i] > 2 && a.beats[i] < 10), loud = a.energy.filter((_, i) => a.beats[i] > 14 && a.beats[i] < 22);
  const mean = v => v.reduce((p, q) => p + q, 0) / v.length, spread = v => Math.max(...v) - Math.min(...v);
  t('steady loudness → steady energy', spread(loud) < 0.1, `loud spread ${spread(loud).toFixed(3)}`);
  t('quiet section scores lower than loud section', mean(quiet) < 0.35 && mean(loud) > 0.9, `quiet ${mean(quiet).toFixed(2)} vs loud ${mean(loud).toFixed(2)}`);
}
console.log(fails ? `${fails} FAILED (after energy tests)` : 'ALL PASS (including energy tests)');
