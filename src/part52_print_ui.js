/* ===================== 3D PRINTING: THE "3D PRINT" TAB ===================== */
// Model → placement on the plate → settings → slice → preview → print over USB (or the printer simulator).
// The arm and the printer use different firmware, so the printer has its own connection here.

const PS_FIELDS = {
  main: [['layerH', 'Layer height', 'mm', 0.05], ['firstH', 'First layer height', 'mm', 0.05], ['walls', 'Walls', '', 1], ['top', 'Top layers', '', 1],
    ['bottom', 'Bottom layers', '', 1], ['infill', 'Infill', '%', 5], ['temp', 'Nozzle temperature', '°C', 5]],
  speed: [['vWall', 'Inner walls', 'mm/s', 1], ['vOuter', 'Outer wall', 'mm/s', 1], ['vInfill', 'Infill', 'mm/s', 1], ['vSolid', 'Top and bottom', 'mm/s', 1],
    ['vFirst', 'First layer', 'mm/s', 1], ['vSupport', 'Supports', 'mm/s', 1], ['vTravel', 'Travel', 'mm/s', 5], ['vZ', 'Up and down', 'mm/s', 1],
    ['minLayerTime', 'Slowest layer time', 's', 1], ['minSpeed', 'But never slower than', 'mm/s', 0.5]],
  ext: [['lineW', 'Line width', 'mm', 0.05], ['firstW', 'First-layer line width', 'mm', 0.05], ['flow', 'Flow', '%', 1], ['retract', 'Retraction', 'mm', 0.5],
    ['vRetract', 'Retraction speed', 'mm/s', 5], ['retractMin', 'Retract for travel over', 'mm', 0.5], ['zHop', 'Lift for travel', 'mm', 0.1],
    ['skirt', 'Skirt loops', '', 1], ['skirtDist', 'Skirt distance', 'mm', 0.5], ['skirtMin', 'Skirt at least', 'mm', 10], ['brim', 'Brim loops', '', 1],
    ['supportAngle', 'Support overhangs past', '°', 5], ['supportGap', 'Support line spacing', 'mm', 0.5], ['supportXY', 'Support gap to model', 'mm', 0.1]],
  plate: [['plateD', 'Plate diameter', 'mm', 5], ['maxH', 'Tallest print', 'mm', 5], ['nozzle', 'Nozzle', 'mm', 0.1], ['filament', 'Filament', 'mm', 0.05]],
};
const P3S = {
  mesh: null, info: null, name: '', format: '', units: 1, pct: 100,
  place: { R: MAT3_I.slice(), rz: 0, x: 0, y: 0, mirror: false }, placed: null,
  settings: null, result: null, stale: true, sliceGen: 0, slicing: false,
  link: null, kind: null, jobResult: null, fan: false, follow: true, view: null,
};

/* ---------- settings ---------- */
function p3BuildForm() {
  for (const [grp, fields] of Object.entries(PS_FIELDS)) {
    $id('ps-' + grp).innerHTML = fields.map(([k, label, unit, step]) =>
      `<label class="f">${label}${unit ? ' (' + unit + ')' : ''}<input id="ps-${k}" type="number" step="${step}" min="${PRINT_LIMITS[k][0]}" max="${PRINT_LIMITS[k][1]}"></label>`).join('');
  }
  $id('pr-preset').innerHTML = Object.entries(PRINT_PRESETS).map(([k, p]) => `<option value="${k}">${p.label}</option>`).join('') + '<option value="custom">Custom</option>';
  $id('pr-sample').innerHTML = '<option value="">Choose a model…</option>' + Object.entries(PRINT_SAMPLES).map(([k, p]) => `<option value="${k}">${p.label}</option>`).join('');
  $id('pr-legend').innerHTML = [[1, 'outer wall'], [2, 'inner walls'], [3, 'top and bottom'], [4, 'infill'], [5, 'supports'], [6, 'skirt and brim'], [0, 'travel']]
    .map(([t, n]) => `<span class="chip"><i style="background:rgb(${P3_COLOURS[t].map(v => Math.round(v * 255)).join(',')})"></i>${n}</span>`).join('');
}
const PS_KEYS = Object.values(PS_FIELDS).flat().map(f => f[0]);
function p3WriteForm(s) {
  for (const k of PS_KEYS) $id('ps-' + k).value = s[k];
  $id('ps-support').value = s.support; $id('ps-pattern').value = s.pattern; $id('ps-seam').value = s.seam;
  $id('ps-vase').checked = !!s.vase; $id('ps-fan').checked = !!s.fan;
  $id('ps-startCode').value = s.startCode; $id('ps-endCode').value = s.endCode;
  p3PresetShown();
}
function p3FormValues() {
  const o = {};
  for (const k of PS_KEYS) o[k] = parseFloat($id('ps-' + k).value);
  Object.assign(o, { support: $id('ps-support').value, pattern: $id('ps-pattern').value, seam: $id('ps-seam').value,
    vase: $id('ps-vase').checked, fan: $id('ps-fan').checked, startCode: $id('ps-startCode').value, endCode: $id('ps-endCode').value });
  return o;
}
function p3PresetShown() {
  const v = p3FormValues();
  const hit = Object.entries(PRINT_PRESETS).find(([, p]) => Object.entries(p).every(([k, x]) => k === 'label' || v[k] === x));
  $id('pr-preset').value = hit ? hit[0] : 'custom';
}
function p3LoadSettings() {
  try { const j = JSON.parse(localStorage.getItem('magician-print-settings') || 'null'); if (j && j.v === 1) return { ...PRINT_DEFAULTS, ...j.s }; } catch (e) {}
  return { ...PRINT_DEFAULTS };
}
function p3SaveSettings() {
  try { const s = printSettings(p3FormValues()); localStorage.setItem('magician-print-settings', JSON.stringify({ v: 1, s })); p3Msg('Print settings saved in this browser.', 'ok'); }
  catch (e) { p3Msg(e.message, 'err'); }
}

/* ---------- messages ---------- */
function p3Msg(text, cls) {
  const el = $id('pr-msg');
  el.textContent = text; el.className = 'stats' + (cls === 'err' ? ' pr-err' : '');
  el.style.color = cls === 'err' ? 'var(--err)' : cls === 'warn' ? 'var(--warn)' : cls === 'ok' ? 'var(--ok)' : '';
  log('3D print: ' + text, cls);
}

/* ---------- model and placement ---------- */
async function p3LoadFile(file) {
  try {
    if (file.size > 300e6) throw new Error('This file is very large (over 300 MB).');
    $id('pr-file-name').textContent = 'reading ' + file.name + '…';
    await new Promise(r => setTimeout(r, 30));          // let the page show that before the work starts
    const p = meshParse(await file.arrayBuffer(), file.name);
    p3SetModel(meshFromTris(p.tri, file.name.replace(/\.[^.]+$/, '')), file.name, p.format);
  } catch (e) { $id('pr-file-name').textContent = 'could not read ' + file.name; p3Msg(e.message, 'err'); }
}
function p3SetModel(mesh, label, format) {
  P3S.mesh = mesh; P3S.info = meshInfo(mesh); P3S.name = mesh.name; P3S.format = format;
  P3S.place = { R: MAT3_I.slice(), rz: 0, x: 0, y: 0, mirror: false }; P3S.pct = 100;
  const big = Math.max(...P3S.info.size);
  $id('pr-file-name').textContent = label;
  p3InfoText();
  p3SyncPlaceInputs();
  p3Placed();
  const F = p3Fits();
  if (!F.ok) { p3Fit(); p3Msg(`${P3S.name} is larger than the printer takes, so it was scaled to ${P3S.pct} %.`, 'warn'); }
  else if (big * P3S.units < 3) p3Msg('This model is under 3 mm across. If it was made in inches or metres, change "Units in the file".', 'warn');
  else p3Msg(`${P3S.name} loaded.`, 'ok');
  p3Buttons();
}
function p3InfoText() {
  const i = P3S.info, u = P3S.units;
  if (!i) { $id('pr-info').textContent = ''; return; }
  $id('pr-info').innerHTML = `${P3S.format}: ${i.tris.toLocaleString()} triangles · ${i.size.map(v => (v * u).toFixed(1)).join(' × ')} mm as drawn · ${(i.volume * u ** 3 / 1000).toFixed(1)} cm³` +
    (i.closed && !i.flipped ? ' · closed surface ✓' + (i.inside ? ' (faces point inwards; it still prints)' : '')
      : i.closed ? ` · <span style="color:var(--warn)">closed, but ${i.flipped} edges join faces turned opposite ways — repair the STL if parts come out hollow</span>`
      : ` · <span style="color:var(--warn)">the surface has ${i.open} open and ${i.nonManifold} doubled edges — repair the STL if layers come out wrong</span>`);
}
function p3Scale() { return P3S.units * P3S.pct / 100; }
function p3Placed() {
  if (!P3S.mesh) return;
  P3S.placed = meshPlace(P3S.mesh, { ...P3S.place, s: p3Scale() });
  p3Invalidate();
  const F = p3Fits();
  if (P3S.view) { P3S.view.setMesh(P3S.placed, !F.ok, !!(P3S.info && P3S.info.inside)); P3S.view.draw(); }   // a mirror keeps the faces' sense (meshPlace)
  const P = P3S.placed, sz = [0, 1, 2].map(k => P.max[k] - P.min[k]);
  $id('pr-fit').innerHTML = `On the plate: ${sz.map(v => v.toFixed(1)).join(' × ')} mm` +
    (F.ok ? ` — fits ✓ (${F.rMax.toFixed(1)} of ${F.R} mm from the centre)` : `<span style="color:var(--err)"> — ${F.tall ? `too tall (${sz[2].toFixed(1)} mm, at most ${F.maxH} mm)` : `reaches ${F.rMax.toFixed(1)} mm from the centre; the plate is Ø${F.R * 2} mm`}. Scale it down or press Fit to plate.</span>`);
}
function p3PlateSettings() { const d = parseFloat($id('ps-plateD').value), h = parseFloat($id('ps-maxH').value); return { d: Number.isFinite(d) ? d : 80, h: Number.isFinite(h) ? h : 150 }; }
function p3Fits() {
  const P = P3S.placed, pl = p3PlateSettings();
  if (!P) return { ok: false };
  const R = pl.d / 2, tall = P.max[2] > pl.h + 1e-6, wide = P.rMax > R + 1e-6;
  return { ok: !tall && !wide, tall, wide, rMax: P.rMax, R, maxH: pl.h };
}
function p3Fit() {
  if (!P3S.mesh) return;
  const pl = p3PlateSettings(), P1 = meshPlace(P3S.mesh, { ...P3S.place, x: 0, y: 0, s: P3S.units }), v = p3FormValues();
  const room = 1 + (v.skirt > 0 ? v.skirtDist + 0.6 * v.skirt : 0) + 0.6 * (v.brim || 0);       // keep the skirt on the plate
  const k = Math.min((pl.d / 2 - room) / Math.max(1e-9, P1.rMax), pl.h / Math.max(1e-9, P1.max[2]));
  P3S.place.x = 0; P3S.place.y = 0;
  P3S.pct = Math.max(1, Math.floor(k * 100));
  p3SyncPlaceInputs(); p3Placed();
}
function p3SyncPlaceInputs() {
  $id('pr-scale').value = Math.min(400, Math.max(10, P3S.pct)); $id('pr-scaleNum').value = P3S.pct; $id('pr-scaleVal').textContent = P3S.pct + ' %';
  $id('pr-rot').value = P3S.place.rz; $id('pr-rotNum').value = P3S.place.rz; $id('pr-rotVal').textContent = P3S.place.rz + '°';
  $id('pr-x').value = P3S.place.x; $id('pr-y').value = P3S.place.y; $id('pr-mirror').checked = P3S.place.mirror;
}
function p3Invalidate() {
  P3S.sliceGen++;
  if (P3S.result) { P3S.result = null; if (P3S.view) P3S.view.setPath(null); }
  P3S.stale = true;
  $id('pr-sliceBar').style.width = '0%';
  $id('pr-stats').textContent = P3S.mesh ? 'Press Slice to make the G-code.' : '';
  $id('pr-warn').innerHTML = '';
  $id('pr-layer').disabled = true; $id('pr-layerVal').textContent = '—';
  p3Buttons();
}

/* ---------- slicing ---------- */
async function p3Slice() {
  if (!P3S.placed) return p3Msg('Load a model first.', 'warn');
  let s;
  try { s = printSettings(p3FormValues()); } catch (e) { return p3Msg(e.message, 'err'); }
  P3S.settings = s;
  const gen = ++P3S.sliceGen, placed = P3S.placed;
  P3S.slicing = true; p3Buttons();
  $id('pr-stats').textContent = 'Slicing…';
  const t0 = performance.now();
  try {
    const res = await slicePrintAsync(placed, s, { name: P3S.name }, f => { if (gen === P3S.sliceGen) $id('pr-sliceBar').style.width = (f * 100).toFixed(0) + '%'; });
    if (gen !== P3S.sliceGen) return;                  // the model or settings changed meanwhile
    P3S.result = res; P3S.stale = false;
    const st = res.stats;
    $id('pr-stats').innerHTML = `<b>${st.layers}</b> layers · about <b>${fmtDuration(st.time)}</b> of printing · <b>${(st.filament / 1000).toFixed(2)} m</b> of filament (${st.grams.toFixed(1)} g PLA) · ` +
      `${res.lines.toLocaleString()} lines of G-code · sliced in ${((performance.now() - t0) / 1000).toFixed(1)} s`;
    $id('pr-warn').innerHTML = res.warnings.map(w => `<div class="warnbox">${w.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</div>`).join('');
    const sl = $id('pr-layer');
    sl.max = st.layers - 1; sl.value = st.layers - 1; sl.disabled = false; P3S.follow = true;
    if (P3S.view) { P3S.view.setPath(res); P3S.view.layer = st.layers - 1; P3S.view.draw(); }
    p3LayerLabel();
    log(`3D print: sliced ${P3S.name} — ${st.layers} layers, about ${fmtDuration(st.time)}.`, 'ok');
  } catch (e) {
    if (gen === P3S.sliceGen) { $id('pr-stats').textContent = ''; p3Msg(e.message, 'err'); }
  } finally {
    if (gen === P3S.sliceGen) P3S.slicing = false;
    p3Buttons();
  }
}
function p3LayerLabel() {
  const R = P3S.result, v = +$id('pr-layer').value;
  $id('pr-layerVal').textContent = R ? `${v + 1} of ${R.layers.length} — Z ${R.layers[v].z.toFixed(2)} mm` : '—';
}
function p3Download(name, data, type) {
  const url = URL.createObjectURL(new Blob([data], { type }));
  const a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
const p3FileBase = () => (P3S.name || 'model').replace(/[^\w.-]+/g, '_').slice(0, 60) || 'model';

/* ---------- the printer ---------- */
async function p3Connect(sim) {
  if (P3S.link) return p3Disconnect();
  if (!sim && S.dev && !S.sim) return p3Msg('The arm is connected with its normal firmware. Press Disconnect at the top first: 3D printing uses the 3D-printer firmware.', 'warn');
  let io;
  try {
    if (sim) io = new SimPrinter({ speed: +$id('pr-simSpeed').value, plateR: p3PlateSettings().d / 2 });
    else {
      if (!('serial' in navigator)) throw new Error('Web Serial is not available here. Open this file in Google Chrome or Microsoft Edge.');
      io = new GcodeSerial(await navigator.serial.requestPort());
    }
  } catch (e) { return p3Msg(e.name === 'NotFoundError' ? 'No port chosen.' : e.message, 'warn'); }
  const link = new GcodeLink(io, { pingPong: !$id('pr-ahead').checked, budget: 63 });
  link.onEvent = p3OnEvent;
  P3S.link = link; P3S.kind = sim ? 'sim' : 'usb'; P3S.fan = false;
  $id('pr-pill').textContent = 'Connecting…'; $id('pr-pill').className = 'pill';
  p3Buttons();
  try {
    await link.connect();
    $id('pr-pill').textContent = sim ? 'Printer simulator' : 'Printer connected';
    $id('pr-pill').className = 'pill ' + (sim ? 'sim' : 'ok');
    p3Msg(sim ? 'Printer simulator ready — nothing is heated or moved.' : 'Printer connected over USB.', 'ok');
  } catch (e) {
    await link.close(); P3S.link = null;
    $id('pr-pill').textContent = 'Not connected'; $id('pr-pill').className = 'pill';
    p3Msg(e.message + (sim ? '' : ' Check that DobotStudio and Repetier Host are closed, and that the arm has the 3D-printer firmware.'), 'err');
  }
  p3Temp(); p3Buttons();
}
async function p3Disconnect() {
  const L = P3S.link;
  if (!L) return;
  if (L.job && !L.job.done && !confirm('A print is running. Disconnecting stops it. Disconnect?')) return;
  if (L.job && !L.job.done) await L.cancel().catch(() => {});
  else if ((L.target || 0) > 0) await L.send('M104 S0', 2000).catch(() => {});
  await L.close();
  P3S.link = null;
  $id('pr-pill').textContent = 'Not connected'; $id('pr-pill').className = 'pill';
  p3Msg('Printer disconnected.');
  p3Temp(); p3Buttons();
}
function p3OnEvent(type, data) {
  if (type === 'temp') return p3Temp();
  if (['done', 'stopped', 'error', 'closed'].includes(type)) p3Awake(false);
  if (type === 'progress' || type === 'started' || type === 'paused' || type === 'resumed') p3Progress();
  else if (type === 'done') { p3Progress(); p3Msg(`All of ${P3S.name} has been sent to the printer; it finishes the last moves and turns the heater off.`, 'ok'); }
  else if (type === 'stopped') { p3Progress(); p3Msg('Print stopped: heater off, nozzle lifted.', 'warn'); }
  else if (type === 'error') { p3Progress(); p3Msg(data.error, 'err'); }
  else if (type === 'message') { if (/Error|cold|Unknown|No answer/i.test(data)) log('Printer: ' + data, /Error/.test(data) ? 'err' : 'warn'); }
  else if (type === 'closed') { P3S.link = null; $id('pr-pill').textContent = 'Not connected'; $id('pr-pill').className = 'pill'; p3Msg('The printer was disconnected.', 'warn'); }
  p3Buttons();
}
function p3Temp() {
  const L = P3S.link, el = $id('pr-temp');
  if (!L || L.temp === null) { el.textContent = 'Nozzle — °C'; el.classList.remove('hot'); return; }
  el.textContent = `Nozzle ${L.temp.toFixed(0)}` + (L.target ? ` → ${L.target.toFixed(0)}` : '') + ' °C';
  el.classList.toggle('hot', L.temp > 50);
}
const p3Running = () => !!(P3S.link && P3S.link.job && !P3S.link.job.done);
async function p3Cmds(list, what) {
  const L = P3S.link;
  if (!L) return p3Msg('Connect the printer first.', 'warn');
  try { for (const c of list) await L.send(c, 0); if (what) p3Msg(what, 'ok'); }
  catch (e) { p3Msg(e.message, 'err'); }
}
function p3NeedHot() {
  const L = P3S.link;
  if (L && L.temp !== null && L.temp >= 170) return true;
  p3Msg('Heat the nozzle first: the firmware moves filament only above 170 °C.', 'warn');
  return false;
}

/* ---------- printing ---------- */
function p3StartDialog() {
  const R = P3S.result;
  if (!R || P3S.stale) return p3Msg('Slice the model first.', 'warn');
  if (!P3S.link) return p3Msg('Connect the printer (or the printer simulator) first.', 'warn');
  if (p3Running()) return;
  $id('prCheckSum').innerHTML = `<b>${P3S.name}</b>: ${R.stats.layers} layers, about ${fmtDuration(R.stats.time)} at ${R.settings.temp} °C, ${(R.stats.filament / 1000).toFixed(2)} m of filament.` +
    (P3S.kind === 'sim' ? ' <span class="muted">(simulator — nothing real is heated)</span>' : '');
  document.querySelectorAll('#prCheck .pr-check input').forEach(c => { c.checked = false; });
  $id('btnPrCheckGo').disabled = true;
  $id('prCheck').hidden = false;
}
// Keeps the screen (and so the computer) awake while a print is being sent, where the browser allows it.
async function p3Awake(on) {
  try {
    if (on && !P3S.wake && navigator.wakeLock) { P3S.wake = await navigator.wakeLock.request('screen'); P3S.wake.addEventListener('release', () => { P3S.wake = null; }); }
    else if (!on && P3S.wake) { await P3S.wake.release(); P3S.wake = null; }
  } catch (e) { /* not allowed here: the hint asks to keep the computer awake */ }
}
function p3Start() {
  $id('prCheck').hidden = true;
  const L = P3S.link, R = P3S.result;
  if (!L || !R) return;
  try {
    P3S.jobResult = R; P3S.follow = true;
    p3Awake(true);
    L.start(R.gcode, { name: P3S.name });
    p3Msg(`Printing ${P3S.name}: heating to ${R.settings.temp} °C first.`, 'ok');
  } catch (e) { p3Msg(e.message, 'err'); }
  p3Buttons();
}
function p3Progress() {
  const L = P3S.link, J = L && L.job, R = P3S.jobResult;
  if (!J || !R) return;
  const n = J.cmds.length, done = J.acked, line = done ? J.src[done - 1] : 0, Ls = R.layers;
  let li = 0, lo = 0, hi = Ls.length - 1;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (Ls[m].line <= line) { li = m; lo = m + 1; } else hi = m - 1; }
  const started = line >= Ls[0].line;
  const nextLine = li + 1 < Ls.length ? Ls[li + 1].line : R.lines, prevT = li ? Ls[li - 1].time : 0;
  const within = Math.max(0, Math.min(1, (line - Ls[li].line) / Math.max(1, nextLine - Ls[li].line)));
  const left = Math.max(0, R.stats.time - (prevT + (Ls[li].time - prevT) * within) * 1.1);
  const el = (Date.now() - J.t0 - J.pausedFor - (J.paused ? Date.now() - J.pauseT : 0)) / 1000;
  const pct = Math.round(100 * done / n);
  $id('pr-bar').style.width = pct + '%';
  let txt;
  if (J.error) txt = 'Stopped: ' + J.error;
  else if (J.cancelled) txt = `Stopped at layer ${li + 1} of ${Ls.length}.`;
  else if (J.done) txt = `Done: ${Ls.length} layers sent in ${fmtDuration((J.t1 - J.t0 - J.pausedFor) / 1000)}.`;
  else if (!started) txt = `Heating to ${R.settings.temp} °C…` + (L.temp !== null ? ` now ${L.temp.toFixed(0)} °C` : '');
  else txt = `${J.paused ? 'Paused at' : 'Layer'} ${li + 1} of ${Ls.length} · Z ${Ls[li].z.toFixed(2)} mm · ${pct} % sent · ${fmtDuration(el)} so far · about ${fmtDuration(left)} to go`;
  $id('pr-progress').textContent = txt;
  if (P3S.view && P3S.view.path === R) {
    const pl = R.preview.line;
    let k = 0, a = 0, b = pl.length - 1;
    while (a <= b) { const m = (a + b) >> 1; if (pl[m] <= line) { k = m + 1; a = m + 1; } else b = m - 1; }
    P3S.view.progressSeg = J.done && !J.error && !J.cancelled ? -1 : k;
    if (P3S.follow && started) { P3S.view.layer = li; $id('pr-layer').value = li; p3LayerLabel(); }
    if ($id('tab-print').classList.contains('active')) P3S.view.draw();
  }
}
function p3Buttons() {
  const L = P3S.link, ready = !!(L && L.ready), run = p3Running(), R = P3S.result && !P3S.stale;
  $id('btnPrConnect').textContent = L ? 'Disconnect printer' : 'Connect 3D printer (USB)';
  $id('btnPrConnect').classList.toggle('primary', !L);
  $id('btnPrSim').disabled = !!L;
  $id('pr-ahead').disabled = !!L;
  for (const id of ['btnPrHeat', 'btnPrCool', 'btnPrFan']) $id(id).disabled = !ready;
  for (const id of ['btnPrFeed', 'btnPrBack', 'btnPrZero']) $id(id).disabled = !ready || run;
  $id('btnPrFan').textContent = P3S.fan ? 'Fan off' : 'Fan on';
  $id('btnPrSlice').disabled = !P3S.mesh || P3S.slicing;
  $id('btnPrSlice').textContent = P3S.slicing ? 'Slicing…' : 'Slice';
  $id('btnPrStl').disabled = !P3S.placed;
  $id('btnPrGcode').disabled = !R;
  $id('btnPrStart').disabled = !R || !ready || run;
  $id('btnPrPause').disabled = !run;
  $id('btnPrPause').textContent = run && L.job.paused ? 'Resume' : 'Pause';
  $id('btnPrStop').disabled = !run;
}
function p3Draw() { if (P3S.view) { const pl = p3PlateSettings(); P3S.view.setPlate(pl.d, pl.h); P3S.view.draw(); } }

/* ---------- wiring ---------- */
p3BuildForm();
{
  const esc = t => t.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  $id('pr-credit-body').innerHTML = `<p>Slicing uses <b>Clipper</b> by Angus Johnson (polygon clipping and offsetting), in Timo's JavaScript translation with Tom Wu's JSBN big integers. Built-in models are made for this app (public domain). Print defaults follow Dobot's Magician user guide and Dobot's printing tips.</p>` +
    `<pre class="tx-lic">${esc(CLIPPER_LICENCES.clipper)}</pre><pre class="tx-lic">${esc(CLIPPER_LICENCES.jsbn)}</pre>`;
}
P3S.settings = p3LoadSettings();
p3WriteForm(P3S.settings);
P3S.view = new PrintView($id('prCanvas'));
$id('pr-file').onchange = async e => { const f = e.target.files[0]; if (f) await p3LoadFile(f); e.target.value = ''; };
{
  const dz = $id('pr-drop');
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('hot'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('hot'));
  dz.addEventListener('drop', async e => { e.preventDefault(); dz.classList.remove('hot'); const f = e.dataTransfer.files[0]; if (f) await p3LoadFile(f); });
}
$id('pr-sample').onchange = e => { const k = e.target.value; if (!k) return; $id('pr-units').value = '1'; P3S.units = 1; p3SetModel(sampleMesh(k), PRINT_SAMPLES[k].label, 'built-in model'); e.target.value = ''; };
$id('pr-units').onchange = e => { P3S.units = +e.target.value; p3InfoText(); if (P3S.mesh) { p3Placed(); if (!p3Fits().ok) p3Msg('At this size the model does not fit: press Fit to plate or scale it down.', 'warn'); } };
const p3Pct = v => { if (!Number.isFinite(v) || v <= 0) return; P3S.pct = Math.round(v); p3SyncPlaceInputs(); p3Placed(); };
$id('pr-scale').oninput = e => p3Pct(+e.target.value);
$id('pr-scaleNum').onchange = e => p3Pct(+e.target.value);
const p3Rz = v => { if (!Number.isFinite(v)) return; P3S.place.rz = Math.max(-180, Math.min(180, Math.round(v))); p3SyncPlaceInputs(); p3Placed(); };
$id('pr-rot').oninput = e => p3Rz(+e.target.value);
$id('pr-rotNum').onchange = e => p3Rz(+e.target.value);
$id('pr-mirror').onchange = e => { P3S.place.mirror = e.target.checked; p3Placed(); };
$id('pr-x').onchange = e => { const v = +e.target.value; if (Number.isFinite(v)) { P3S.place.x = v; p3Placed(); } };
$id('pr-y').onchange = e => { const v = +e.target.value; if (Number.isFinite(v)) { P3S.place.y = v; p3Placed(); } };
$id('btnPrTipX').onclick = () => { if (!P3S.mesh) return; P3S.place.R = mat3Mul(mat3Turn('x', 90), P3S.place.R); p3Placed(); };
$id('btnPrTipY').onclick = () => { if (!P3S.mesh) return; P3S.place.R = mat3Mul(mat3Turn('y', 90), P3S.place.R); p3Placed(); };
$id('btnPrFlat').onclick = () => { if (!P3S.mesh) return; P3S.place.R = meshLayFlat(P3S.mesh, P3S.place.R); p3Placed(); };
$id('btnPrFit').onclick = () => p3Fit();
$id('btnPrReset').onclick = () => { if (!P3S.mesh) return; P3S.place = { R: MAT3_I.slice(), rz: 0, x: 0, y: 0, mirror: false }; P3S.pct = 100; p3SyncPlaceInputs(); p3Placed(); };
$id('btnPrStl').onclick = () => { if (P3S.placed) p3Download(p3FileBase() + '-placed.stl', meshToSTL(P3S.placed.pos, P3S.placed.idx, P3S.name), 'model/stl'); };
$id('pr-v3d').onclick = () => { P3S.view.mode = '3d'; $id('pr-v3d').classList.add('on'); $id('pr-vLayer').classList.remove('on'); P3S.view.draw(); };
$id('pr-vLayer').onclick = () => { P3S.view.mode = 'layer'; $id('pr-vLayer').classList.add('on'); $id('pr-v3d').classList.remove('on'); P3S.view.draw(); };
$id('pr-layer').oninput = e => { P3S.view.layer = +e.target.value; P3S.follow = p3Running() && +e.target.value >= +e.target.max; p3LayerLabel(); P3S.view.draw(); };
$id('pr-travel').onchange = e => { P3S.view.travel = e.target.checked; P3S.view.draw(); };
// settings: any change makes the slice out of date
document.querySelectorAll('#tab-print input[id^="ps-"], #tab-print select[id^="ps-"], #tab-print textarea[id^="ps-"]').forEach(el => el.addEventListener('change', () => {
  if (el.id === 'ps-vase' && el.checked) { $id('ps-walls').value = 1; $id('ps-top').value = 0; $id('ps-infill').value = 0; }
  p3PresetShown();
  if (el.id === 'ps-plateD' || el.id === 'ps-maxH') { p3Draw(); if (P3S.mesh) p3Placed(); }
  else p3Invalidate();
}));
$id('pr-preset').onchange = e => {
  const p = PRINT_PRESETS[e.target.value]; if (!p) return;
  const v = p3FormValues(); for (const [k, x] of Object.entries(p)) if (k !== 'label') v[k] = x;
  p3WriteForm(v); p3Invalidate();
};
$id('btnPrSlice').onclick = () => p3Slice();
$id('btnPrSaveSet').onclick = () => p3SaveSettings();
$id('btnPrDefaults').onclick = () => { p3WriteForm({ ...PRINT_DEFAULTS }); p3Invalidate(); p3Draw(); if (P3S.mesh) p3Placed(); p3Msg('Dobot defaults restored (press Save settings to keep them).'); };
$id('btnPrGcode').onclick = () => { if (P3S.result && !P3S.stale) p3Download(p3FileBase() + '.gcode', P3S.result.gcode, 'text/x-gcode'); };
// printer
$id('btnPrConnect').onclick = () => p3Connect(false);
$id('btnPrSim').onclick = () => p3Connect(true);
$id('btnPrHeat').onclick = () => {
  const t = parseFloat($id('pr-heatTo').value);
  if (!(t >= 170 && t <= 250)) return p3Msg('Choose 170–250 °C (PLA: about 200 °C).', 'warn');
  p3Cmds(['M104 S' + t], `Heating the nozzle to ${t} °C.`);
};
$id('btnPrCool').onclick = () => p3Cmds(['M104 S0'], 'Heater off.');
$id('btnPrFan').onclick = () => { P3S.fan = !P3S.fan; p3Cmds([P3S.fan ? 'M106' : 'M107'], P3S.fan ? 'Fan on.' : 'Fan off.'); p3Buttons(); };
$id('btnPrFeed').onclick = () => { if (p3NeedHot()) p3Cmds(['G91', 'G1 E10 F100', 'G90'], 'Feeding 10 mm of filament.'); };
$id('btnPrBack').onclick = () => { if (p3NeedHot()) p3Cmds(['G91', 'G1 E-10 F300', 'G90'], 'Pulled the filament back 10 mm.'); };
$id('btnPrZero').onclick = () => {
  if (!confirm('Hold the unlock button on the forearm and lower the nozzle until it just touches the tape on the plate (about a sheet of paper\'s thickness), let go, then press OK to save this as the nozzle height (Z zero).')) return;
  p3Cmds(['M415'], 'Nozzle height saved (Z zero). The arm beeps to confirm.');
};
$id('btnPrStart').onclick = () => p3StartDialog();
document.querySelectorAll('#prCheck .pr-check input').forEach(c => c.addEventListener('change', () => {
  $id('btnPrCheckGo').disabled = ![...document.querySelectorAll('#prCheck .pr-check input')].every(x => x.checked);
}));
$id('btnPrCheckNo').onclick = () => { $id('prCheck').hidden = true; };
$id('btnPrCheckGo').onclick = () => p3Start();
$id('btnPrPause').onclick = async () => {
  const L = P3S.link; if (!p3Running()) return;
  try { if (L.job.paused) { await L.resume(); p3Msg('Printing again.', 'ok'); } else { const p = L.pause(); p3Buttons(); await p; p3Msg('Paused: the nozzle lifts once the moves already sent are done. It stays hot.', 'warn'); } }
  catch (e) { p3Msg(e.message, 'err'); }
  p3Buttons(); p3Progress();
};
$id('btnPrStop').onclick = () => { if (p3Running() && confirm('Stop the print? The heater turns off and the nozzle lifts.')) P3S.link.cancel().then(p3Buttons); };
// the red STOP at the top halts a running print at once
$id('btnStop').addEventListener('click', () => {
  if (!p3Running()) return;
  P3S.link.emergency().then(() => { p3Msg('Printer halted (M112 and a reset). Connect again before printing.', 'err'); p3Buttons(); });
});
// the arm and the printer cannot share the USB port
{
  const armConnect = $id('btnConnect').onclick;
  $id('btnConnect').onclick = e => (P3S.link && P3S.kind === 'usb' && !S.dev ? log('Disconnect the 3D printer first (3D print tab): it uses the same USB port with another firmware.', 'warn') : armConnect(e));
}
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && p3Running()) p3Awake(true); });
window.addEventListener('beforeunload', e => {
  const L = P3S.link;
  if (!L) return;
  if (p3Running()) { e.preventDefault(); e.returnValue = ''; return; }
  if ((L.target || 0) > 0) try { const w = L.io.write('M104 S0\n'); if (w && w.catch) w.catch(() => {}); } catch (err) {}
});
p3Buttons();
