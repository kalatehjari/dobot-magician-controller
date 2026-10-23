/* ===================== SELF-TEST (Setup → "Test camera features", or ?selftest=1) ===================== */
// Loads every vision model, runs the camera pipeline for 3 s, checks the beat tracker on a
// generated 120 BPM click track, the picture tracer, the geometry model, drawing placement, the drawing library, shading, text, several objects
// and 3D printing (slice, then print on the simulated printer). Uses the simulators, so nothing moves or heats.
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
    // smooth motion: a rounded hop never drops below the paper and the glide follower keeps its limits
    const hp = hopPath({ x: 250, y: 0 }, { x: 262, y: 5 }, -60, 6, 0), lim = { vMax: 90, aMax: 140, omega: 5 };
    let g = { x: 250, y: 0, z: 0, vx: 0, vy: 0, vz: 0 }, aPk = 0;
    for (let k = 0; k < 150; k++) { const n = glideStep(g, { x: 300, y: 40, z: 0 }, 0.03, lim); aPk = Math.max(aPk, Math.hypot(n.vx - g.vx, n.vy - g.vy, n.vz - g.vz) / 0.03); g = n; }
    out.smooth = hp.every(q => q.z >= -60 - 1e-9) && hp[hp.length - 1].z === -60 && aPk <= 140 + 1e-6 && Math.hypot(g.x - 300, g.y - 40) < 1 ? 'ok' : 'FAILED';
    // drawing library: every drawing decodes; every 25th goes the whole way (SVG reader, placement in a typical zone);
    // the requested categories have at least 50 drawings each
    const zL = { rIn: 180, rOut: 300, thMin: -85, thMax: 85 }, cats = new Map(), libBad = [];
    let libMin = Infinity;
    LIBRARY.forEach((e, k) => {
      cats.set(e.c, (cats.get(e.c) || 0) + 1);
      const Lk = libLines(e);
      if (Lk.length !== e.l || Lk.some(a => a.length < 4)) { libBad.push(e.n); return; }
      if (k % 25) return;
      const st = svgToStrokes(libSvg(e)), b = st.length === e.l ? bestPlacement(placementProbe(prepareSketch(st), 0, false), zL) : null;
      if (!b || b.size < 60) libBad.push(e.n); else libMin = Math.min(libMin, b.size);
    });
    const thin = LIBRARY_CATS.filter(([k]) => !['food', 'places', 'transport'].includes(k) && (cats.get(k) || 0) < 50).map(c => c[1]);
    out.library = !libBad.length && !thin.length ? `ok (${LIBRARY.length} drawings in ${cats.size} categories; samples fit at ${libMin.toFixed(0)} mm or more)`
      : 'FAILED: ' + [...libBad.slice(0, 6), ...thin.map(t => t + ' has fewer than 50')].join(', ');
    if (!out.library.startsWith('ok')) out.errors.push('Library check failed');
    // shading: a square with a square hole gets lines all round the hole, joined into zig-zags, none in the hole
    const sqS = (h) => [{ x: -h, y: -h }, { x: h, y: -h }, { x: h, y: h }, { x: -h, y: h }, { x: -h, y: -h }];
    const shR = shadeDrawing(shadeTargets({ strokes: [sqS(0.5), sqS(0.2)] }, 'alt'), { ...SHADE_DEFAULTS, pattern: 'lines', angle: 30, spacing: 2 }, 100);
    const inHole = shR.strokes.some(c => c.some((p, i) => i && Math.abs((p.x + c[i - 1].x) / 2) < 0.199 && Math.abs((p.y + c[i - 1].y) / 2) < 0.199));
    out.shading = shR.lines > 30 && !inHole && shR.strokes.length < shR.lines / 4 ? `ok (${shR.lines} lines in ${shR.strokes.length} pen strokes)` : 'FAILED';
    if (!out.shading.startsWith('ok')) out.errors.push('Shading check failed');
    // text: every font writes accented sample text (macrons drawn on), in every style
    const txBad = [];
    for (const f of FONT_FAMILIES) for (const [style] of TEXT_STYLES) {
      const L = textLayout({ str: 'Kia ora Māori — 123 éü', family: f.key, style });
      if (L.strokes.length < 10 || L.missing.length) txBad.push(`${f.name} ${style}`);
    }
    out.text = !txBad.length ? `ok (${FONT_FAMILIES.length} fonts × ${TEXT_STYLES.length} styles)` : 'FAILED: ' + txBad.join(', ');
    if (txBad.length) out.errors.push('Text check failed');
    // Persian text: letters join (seen meets lam-alef at the joining point), numbers and English inside stay left to right
    try {
      const Lfa = textLayout({ str: 'سلام دنیا ۱۴۰۵ (Dobot)', lang: 'fa' }), G = fontGlyphs(FA_FONT), seam = faLayoutLine(G, 'سلام', {}).glyphs;
      const j = FONT_DATA[FA_FONT].join / FONT_CAP, x = seam[2].x;
      const meets = g => g.strokes.some(s => [s[0], s[s.length - 1]].some(q => Math.abs(q.x + g.x - x) < 1e-9 && Math.abs(q.y - j) < 1e-9));
      const order = faReorder([...'سلام 12 abc'], faBidiLevels([...'سلام 12 abc'].map(faBidiClass), [...'سلام 12 abc'])).join('');
      out.persian = Lfa.strokes.length > 20 && !Lfa.missing.length && meets(seam[1]) && meets(seam[2]) && order === 'abc 12 مالس' ? `ok (${Lfa.strokes.length} pen lines)` : 'FAILED';
    } catch (e) { out.persian = 'FAILED: ' + e.message; }
    if (!out.persian.startsWith('ok')) out.errors.push('Persian text check failed');
    // safe zone and safety lock: a drawing line across the notch of an L-shaped zone is caught, then trimmed to its parts inside
    try {
      const Z = { rIn: 190, rOut: 300, thMin: -80, thMax: 80, margin: 4 }, P = [{ x: 200, y: -80 }, { x: 290, y: -80 }, { x: 290, y: 80 }, { x: 250, y: 80 }, { x: 250, y: -20 }, { x: 200, y: -20 }];
      const R = regionBuild(Z, P), floor = -76, start = { x: 270, y: -60, z: -50 };
      const cmds = [{ x: 220, y: -50, z: -60, mode: 2 }, { x: 220, y: -50, z: -75, mode: 2 }, { kind: 'cp', x: 270, y: 60, z: -75, v: 30 }, { x: 270, y: 60, z: -60, mode: 2 }];
      const before = lockCheckPath(cmds, start, R, floor), trimmed = lockTrimPath(cmds, start, R, floor, { mode: 'draw', zDown: -75, zUp: -60, route: regionRouter(R) });
      out.zone = !polyCheck(P) && before.bad > 0 && lockCheckPath(trimmed, start, R, floor).ok ? `ok (${before.bad} move${before.bad === 1 ? '' : 's'} caught, the trimmed path passes)` : 'FAILED';
    } catch (e) { out.zone = 'FAILED: ' + e.message; }
    if (!out.zone.startsWith('ok')) out.errors.push('Safe zone / lock check failed');
    // wireless: the Wi-Fi set-up messages encode and read back exactly
    try {
      const fr = wifiSetupFrames({ ssid: 'Lab net', password: 'pass-1234', dhcp: false, ip: '192.168.1.50', netmask: '255.255.255.0', gateway: '192.168.1.1' });
      const back = parseFrames(new Uint8Array(fr.flatMap(([id, c, q]) => [...encodeFrame(id, c, q)]))).frames;
      const same = back.length === fr.length && back.every((f, i) => f.id === fr[i][0] && f.params.length === fr[i][2].length && f.params.every((b, k) => b === fr[i][2][k]));
      out.wireless = same ? `ok (${fr.length} Wi-Fi set-up messages)` : 'FAILED';
    } catch (e) { out.wireless = 'FAILED: ' + e.message; }
    if (!out.wireless.startsWith('ok')) out.errors.push('Wireless check failed');
    // several objects: a second drawing finds free room beside the first (the paper itself is not touched)
    const sqO = [[{ x: 0, y: 0 }, { x: 40, y: 0 }, { x: 40, y: 40 }, { x: 0, y: 40 }, { x: 0, y: 0 }]];
    const oA = newObject('drawing', prepareSketch(sqO), 'self-test A'), oB = newObject('drawing', prepareSketch(sqO), 'self-test B');
    oA.place = defaultPlacement(oA.sketch);
    const fs = freeSpot(oB, oA.place.size * 0.5, [oA]);
    out.objects = fs && fs.ov === 0 && probeFits(objProbe(oB, 0, false), fs.cx, fs.cy, oA.place.size * 0.5, drawZone(), plotPad()) ? 'ok' : 'FAILED';
    if (out.objects !== 'ok') out.errors.push('Objects check failed');
    // 3D printing: slice a small cube and print it on the simulated printer; it must receive exactly the G-code
    try {
      const pr = slicePrintSync(meshPlace(sampleMesh('cube'), { s: 0.3 }), { skirtMin: 20 }, { name: 'self-test cube' });
      const want = gcodeCommands(pr.gcode).cmds, sim = new SimPrinter({ speed: 5000, faultEvery: 23 }), link = new GcodeLink(sim);
      await link.connect();
      const J = link.start(pr.gcode);
      for (let k = 0; k < 600 && !J.done; k++) await sleep(25);
      const tr = sim.trace.filter(c => c !== 'M105' && !/^M110/.test(c));
      const same = J.done && !J.error && tr.length === want.length && tr.every((c, i) => c === want[i]);
      await link.close();
      out.print3d = same && pr.stats.layers === 29 && sim.coldBlocked === 0 ? `ok (${pr.stats.layers} layers, ${want.length} lines sent, ${link.resends} resent)` : 'FAILED';
    } catch (e) { out.print3d = 'FAILED: ' + e.message; }
    if (!out.print3d.startsWith('ok')) out.errors.push('3D printing check failed');
    if (out.smooth !== 'ok') out.errors.push('Smooth motion check failed');
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
    `camera ${out.fps} fps; beat tracker ${out.beatBpm} BPM (expected 120); picture tracer ${out.tracer}; geometry ${out.geometry}; placement ${out.placement}; smooth motion ${out.smooth}; library ${out.library}; shading ${out.shading}; text ${out.text}; Persian ${out.persian}; safe zone ${out.zone}; wireless ${out.wireless}; objects ${out.objects}; 3D printing ${out.print3d}; ` +
    `USB serial ${out.serial ? 'available' : 'NOT available'}.`;
  if (res) res.textContent = summary;
  log('Self-test: ' + summary, out.ok ? 'ok' : 'err');
  document.title = 'SELFTEST:' + JSON.stringify(out);
  return out;
}

if (QS.get('selftest') === '1') setTimeout(runSelfTest, 500);
