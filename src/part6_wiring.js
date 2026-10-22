/* ===================== WIRING & STARTUP ===================== */
const $id = id => document.getElementById(id);

document.querySelectorAll('nav button[data-tab]').forEach(b => b.onclick = () => showTab(b.dataset.tab));

$id('btnConnect').onclick = async () => {
  if (S.dev) return disconnect();
  await connectFlow(false);
};
$id('btnSim').onclick = async () => {
  if (S.dev) await disconnect();
  await connectFlow(true);
};
$id('btnStop').onclick = () => stopAll();
$id('btnCentre').onclick = () => { if (confirm('The arm will move to its factory centre (home) position. Make sure the area is clear. Continue?')) goHome(); };
$id('btnClearAlarm').onclick = () => clearAndRearm().catch(e => log(e.message, 'err'));
$id('btnCalibrate').onclick = () => openWizard();
$id('btnCalibrate2').onclick = () => openWizard();

// Setup tab
$id('btnSaveSetup').onclick = () => {
  try { readSetup(); log('Settings saved.', 'ok'); if (S.dev) S.dev.setSpeed(S.speed.live, S.speed.accel).catch(() => {}); drawAll(); }
  catch (e) { log(e.message, 'err'); }
};
$id('btnResetSetup').onclick = () => {
  S.limits = structuredClone(DEFAULTS.limits);
  S.speed = structuredClone((MOTION_PROFILES[S.motion.profile] || MOTION_PROFILES.quiet).speeds);
  writeSetup(); log('Defaults restored for the current motion feel (press Save to keep them).');
};
$id('btnSetPenDown').onclick = () => {
  if (!S.pos) return;
  const z = Math.round(S.pos.z * 10) / 10;
  if (S.model && S.model.ok) {                 // calibrated: recompute every limit for this paper height
    const L = autoLimits(S.model, z, { x: S.limits.homeX, y: S.limits.homeY, z: S.limits.homeZ });
    if (!L) return log('The arm cannot draw usefully at this height.', 'err');
    applyAutoLimits(L, true);
    return log(`Pen-down set to ${z} mm and limits recomputed for this paper height.`, 'ok');
  }
  $id('lim-zDown').value = z;
  log(`Pen-down height set to current Z ${z} — press Save to keep it.`, 'ok');
};
$id('btnSetPenUp').onclick = () => { $id('lim-zUp').value = S.pos.z.toFixed(1); log(`Pen-up height set to current Z ${S.pos.z.toFixed(1)} — press Save to keep it.`, 'ok'); };
$id('dbgFrames').onchange = e => { DEBUG.frames = e.target.checked; };

// Plotter tab
$id('plot-file').onchange = async e => {
  const f = e.target.files[0]; if (!f) return;
  await loadPlotFile(f);
  e.target.value = '';
};
$id('btnLoadText').onclick = async () => {
  const t = $id('plot-text').value.trim(); if (!t) return log('Paste SVG markup first.', 'warn');
  try { await loadSvgText(t, 'pasted SVG'); } catch (err) { log('SVG error: ' + err.message, 'err'); }
};
const dropZone = $id('plot-drop');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('hot'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('hot'));
dropZone.addEventListener('drop', async e => {
  e.preventDefault(); dropZone.classList.remove('hot');
  const f = e.dataTransfer.files[0]; if (!f) return;
  await loadPlotFile(f);
});
['plot-tol', 'plot-minlen', 'plot-join', 'plot-opt', 'plot-hopmax'].forEach(id => {
  $id(id).onchange = () => { if (S.plot.objects.length) buildPlot({ quiet: true }); };
});
$id('btnBuild').onclick = () => buildPlot({ reorder: true });
$id('btnDraw').onclick = () => drawPlotJob();
$id('btnExportOps').onclick = exportOps;

// Record tab
$id('btnRec').onclick = toggleRecord;
$id('btnWaypoint').onclick = () => {
  if (!S.rec.active) return log('Press Record take first, then add waypoints.', 'warn');
  S.rec.pts.push({ x: S.pos.x, y: S.pos.y, z: S.pos.z });
  drawRec();
};
$id('btnLearn').onclick = learn;
$id('btnPlayLearned').onclick = () => playLearned();
$id('btnClearTakes').onclick = () => { S.takes = []; S.learned = null; $id('learn-stats').textContent = ''; renderTakes(); drawRec(); };
$id('btnExportTakes').onclick = exportTakes;
$id('takes-file').onchange = async e => { const f = e.target.files[0]; if (f) { try { await importTakes(f); } catch (err) { log('Import failed: ' + err.message, 'err'); } } };

// Resize: redraw canvases at new size
window.addEventListener('resize', () => drawAll());
if ('ResizeObserver' in window) new ResizeObserver(() => drawAll()).observe(document.querySelector('main'));

// Startup
loadSetup();
renderTakes();
setLiveButton();
setConnected(false);
updatePoseReadout();
showTab('mouse');
log('Ready. Connect the Magician with USB, or press "Simulator" to try everything without hardware.');
