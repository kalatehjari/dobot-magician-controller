/* ===================== SMART: WIRING ===================== */
function showWhen(cls, on) { document.querySelectorAll('.' + cls).forEach(el => { el.style.display = on ? '' : 'none'; }); }

function updateDanceSrcUI() {
  const src = $id('danceSrc').value;
  showWhen('src-file', src === 'file'); showWhen('src-metro', src === 'metro'); showWhen('src-mic', src === 'mic');
}

function updateImitUI() {
  const m = $id('imitMode').value;
  for (const k of ['hand', 'arm', 'air', 'teach']) showWhen('im-' + k, false);
  showWhen('im-' + m, true);
  if (m === 'air') drawAir();
}

renderMoveChips();
loadSmartPrefs();
renderReactTable();
renderCamStatus();
applyMirror();
updateDanceSrcUI();
updateImitUI();
for (const id of ['danceSize', 'danceEnergy', 'danceLatency', 'danceSpeed', 'imitSpan', 'imitSmooth']) {
  const out = $id(id + 'Val');
  if (out) out.textContent = $id(id).value;
  $id(id).addEventListener('input', () => {
    if (out) out.textContent = $id(id).value;
    if (id === 'imitSmooth') IM.filt.tune(parseFloat($id(id).value) || 1, 0.02);
    if (id === 'danceSpeed' && D.playing) smartSpeed(parseFloat($id(id).value), parseFloat($id(id).value) * 1.2);
    saveSmartPrefs();
  });
}

// Camera card
$id('btnCam').onclick = async () => {
  if (V.stream) {
    imitStop(); reactStop();
    for (const k in V.want) V.want[k].clear();
    V.keepCamera = false; cameraStop();
  } else {
    try { V.keepCamera = true; await cameraStart(); } catch (e) { log('Camera: ' + e.message, 'err'); }
  }
};
$id('camMirror').onchange = e => { V.mirror = e.target.checked; applyMirror(); };
$id('camOverlayToggle').onchange = e => {
  V.overlay = e.target.checked;
  if (!V.overlay) { const ov = $id('camOverlay'); ov.getContext('2d').clearRect(0, 0, ov.width, ov.height); }
};

// Dance
$id('danceFile').onchange = async e => {
  const f = e.target.files[0]; if (!f) return;
  $id('danceSrc').value = 'file'; updateDanceSrcUI();
  try { await danceLoadFile(f); } catch (err) { log('Could not read that audio file: ' + err.message, 'err'); setDanceInfo('Could not read that file.'); }
};
$id('danceSrc').onchange = () => { if (D.playing) danceStop(); updateDanceSrcUI(); drawDance(); };
$id('btnDance').onclick = () => (D.playing ? danceStop() : danceStart().catch(e => log('Dance failed: ' + e.message, 'err')));
$id('btnTap').onclick = tapTempo;
$id('btnDanceCentre').onclick = () => {
  if (!S.cmd) return log('Move the arm first, or connect.', 'warn');
  D.center = { x: S.cmd.x, y: S.cmd.y, z: S.cmd.z };
  log(`Dance centre set to X ${D.center.x.toFixed(0)} Y ${D.center.y.toFixed(0)} Z ${D.center.z.toFixed(0)}.`, 'ok');
};
$id('btnDanceCentreReset').onclick = () => { D.center = null; log('Dance centre: automatic (middle of the calibrated space).'); };

// Imitate
$id('btnImit').onclick = () => (IM.active ? imitStop() : imitStart());
$id('imitMode').onchange = () => { if (IM.active) { imitStop(); imitStart(); } updateImitUI(); };
$id('btnImitCal').onclick = () => { IM.wantCal = true; log('Hold your hand at a comfortable centre position — captured on the next frame.'); };
$id('btnAirClear').onclick = () => { IM.air.strokes = []; IM.air.cur = null; $id('airCount').textContent = '0 strokes'; drawAir(); };
$id('btnAirSend').onclick = airToPlotter;
$id('btnTeach').onclick = teachToggle;
$id('imitFacing').onchange = saveSmartPrefs;

// Reactions
$id('btnReact').onclick = () => (R.active ? reactStop() : reactStart());
$id('btnNeutral').onclick = () => { if (!R.active) return log('Start face reading first.', 'warn'); R.wantBase = true; log('Relax your face and look at the camera…'); };
$id('reactHands').onchange = async e => {
  saveSmartPrefs();
  if (!R.active) return;
  if (e.target.checked) { try { await visionRequire('gesture', 'react'); } catch (err) { log(err.message, 'err'); } }
  else visionRelease('gesture', 'react');
};
for (const id of ['reactSens', 'reactCooldown', 'reactAmp', 'reactLookGain', 'reactFace', 'reactLook']) {
  $id(id).addEventListener('change', () => {
    saveSmartPrefs();
    if (id === 'reactLook' && !$id(id).checked && M.owner === 'look at me') streamRelease('look at me');
  });
}

// Setup: self-test
$id('btnSelfTest').onclick = () => runSelfTest();

// Setup: offline model files
$id('modelFiles').onchange = e => loadLocalModels(e.target.files).catch(err => log(err.message, 'err'));

// Live redraw of the smart panels.
setInterval(() => {
  if ($id('tab-react').classList.contains('active')) drawEyes();
  if ($id('tab-imit').classList.contains('active') && IM.active && IM.mode === 'air') drawAir();
  if ($id('tab-dance').classList.contains('active') && !D.playing) drawDance();
  renderSmartActivity();
}, 150);
