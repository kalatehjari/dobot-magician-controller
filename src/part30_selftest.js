/* ===================== SELF-TEST (Setup → "Test camera features", or ?selftest=1) ===================== */
// Loads every vision model, runs the camera pipeline for 3 s, checks the beat tracker on a
// generated 120 BPM click track, the picture tracer, the geometry model and drawing placement. Uses the simulator, so the arm never moves.
async function runSelfTest() {
  const out = {
    secure: window.isSecureContext, serial: 'serial' in navigator,
    camera: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
    models: {}, frames: 0, fps: 0, beatBpm: 0, errors: [],
  };
  const btn = document.getElementById('btnSelfTest');
  const res = document.getElementById('selfTestResult');
  if (btn) btn.disabled = true;
  if (res) res.textContent = 'Testing… (loads the models, about 10–30 s the first time)';
  log('Self-test started.');
  try {
    if (!S.dev) await connectFlow(true);
    if (cal.open) closeWizard();
    if (AC.open) closeAutoCal();
    for (const kind of ['face', 'gesture', 'pose']) {
      const t0 = performance.now();
      try {
        await visionRequire(kind, 'selftest');
        out.models[kind] = `${V.delegate[kind]} in ${((performance.now() - t0) / 1000).toFixed(1)} s`;
      } catch (e) { out.models[kind] = 'FAILED: ' + e.message; out.errors.push(e.message); }
    }
    const f0 = V.framesTotal || 0;
    await sleep(3000);
    out.frames = (V.framesTotal || 0) - f0;
    out.fps = +(out.frames / 3).toFixed(1);
    const sr = 22050, x = new Float32Array(sr * 12);
    for (let tb = 0.3; tb < 11.7; tb += 0.5) {
      const i0 = Math.floor(tb * sr);
      for (let k = 0; k < 0.08 * sr; k++) x[i0 + k] += 0.8 * Math.exp(-k / (0.02 * sr)) * Math.sin(2 * Math.PI * 70 * k / sr);
    }
    out.beatBpm = +analyzeAudio(x, sr).bpm.toFixed(1);
    // picture tracer: a black disc should become one closed outline
    const cv = document.createElement('canvas'); cv.width = cv.height = 200;
    const c2 = cv.getContext('2d'); c2.fillStyle = '#fff'; c2.fillRect(0, 0, 200, 200);
    c2.fillStyle = '#000'; c2.beginPath(); c2.arc(100, 100, 50, 0, 7); c2.fill();
    const tr = traceImage({ data: c2.getImageData(0, 0, 200, 200).data, w: 200, h: 200 }, { mode: 'outline', detail: 6, smooth: 4 });
    out.tracer = tr.paths.length === 1 && tr.paths[0].closed ? 'ok' : `unexpected (${tr.paths.length} lines)`;
    // geometry model: simulated readings must validate and give a reachable working area
    const sim = new SimIO(), d = new Dobot(sim);
    const pA = await d.pose(); await d.home(); const pB = await d.pose();
    const v = validateModel([pA, pB]), L = v.ok ? autoLimits({ dR: v.dR, dZ: v.dZ }, -60, pB) : null;
    out.geometry = v.ok && L ? `ok (reach ${L.minR}–${L.maxR} mm)` : 'FAILED';
    // free placement: a turned square gets a size, and dragging it towards the base stops at the zone edge
    const skT = prepareSketch([[{ x: 0, y: 0 }, { x: 50, y: 0 }, { x: 50, y: 50 }, { x: 0, y: 50 }, { x: 0, y: 0 }]]);
    const zT = { rIn: 200, rOut: 300, thMin: -85, thMax: 85 }, PT = placementProbe(skT, 30, false), bT = bestPlacement(PT, zT);
    const cT = bT && constrainMove(PT, { x: bT.cx, y: bT.cy }, { x: 120, y: 0 }, bT.size * 0.8, zT);
    out.placement = bT && bT.size > 50 && probeFits(PT, cT.x, cT.y, bT.size * 0.8, zT) ? `ok (largest ${bT.size.toFixed(0)} mm)` : 'FAILED';
    if (out.tracer !== 'ok') out.errors.push('Picture tracer: ' + out.tracer);
    if (!L) out.errors.push('Geometry model check failed');
    if (!out.placement.startsWith('ok')) out.errors.push('Placement check failed');
  } catch (e) {
    out.errors.push(e.message);
  } finally {
    for (const kind of ['face', 'gesture', 'pose']) visionRelease(kind, 'selftest');
    if (btn) btn.disabled = false;
  }
  out.ok = !out.errors.length && out.frames > 0 && Math.abs(out.beatBpm - 120) < 2;
  const summary = `${out.ok ? 'All good' : 'Problems found'} — face: ${out.models.face}; hands: ${out.models.gesture}; body: ${out.models.pose}; ` +
    `camera ${out.fps} fps; beat tracker ${out.beatBpm} BPM (expected 120); picture tracer ${out.tracer}; geometry ${out.geometry}; placement ${out.placement}; ` +
    `USB serial ${out.serial ? 'available' : 'NOT available'}.`;
  if (res) res.textContent = summary;
  log('Self-test: ' + summary, out.ok ? 'ok' : 'err');
  document.title = 'SELFTEST:' + JSON.stringify(out);
  return out;
}

if (QS.get('selftest') === '1') setTimeout(runSelfTest, 500);
