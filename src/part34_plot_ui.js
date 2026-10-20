/* ===================== PLOTTER UI: pictures → lines, drawing controls ===================== */
const TR = { bitmap: null, name: '', result: null, timer: null };

function isSvgFile(f) { return /svg/i.test(f.type) || /\.svg$/i.test(f.name); }

// Any file dropped or picked in the Plotter: SVG is used directly, pictures go to the tracer.
async function loadPlotFile(f) {
  try {
    if (isSvgFile(f)) {
      document.getElementById('traceCard').hidden = true;
      await loadSvgText(await f.text(), f.name);
    } else {
      await loadPicture(f);
    }
  } catch (err) { log('Could not open that file: ' + err.message, 'err'); }
}

async function loadPicture(f) {
  let bmp;
  try { bmp = await createImageBitmap(f); }
  catch (e) { throw new Error('This browser cannot read that picture format. Try PNG, JPG, WEBP, GIF or BMP.'); }
  TR.bitmap = bmp; TR.name = f.name.replace(/\.[^.]+$/, '');
  document.getElementById('traceCard').hidden = false;
  document.getElementById('plot-file-name').textContent = `${f.name} (${bmp.width} × ${bmp.height}) — converted to lines below`;
  retrace(true);
}

function traceOpts() {
  const g = id => document.getElementById(id);
  return {
    mode: g('tr-mode').value,
    threshold: g('tr-auto').checked ? null : parseFloat(g('tr-thr').value),
    detail: parseFloat(g('tr-detail').value),
    smooth: parseFloat(g('tr-curve').value),
    invert: g('tr-invert').checked,
    size: parseInt(g('tr-res').value, 10) || 600,
  };
}

// Draws the picture at the chosen resolution and traces it (debounced while sliders move).
function retrace(useNow) {
  clearTimeout(TR.timer);
  TR.timer = setTimeout(() => {
    if (!TR.bitmap) return;
    const o = traceOpts();
    const k = Math.min(1, o.size / Math.max(TR.bitmap.width, TR.bitmap.height));
    const w = Math.max(8, Math.round(TR.bitmap.width * k)), h = Math.max(8, Math.round(TR.bitmap.height * k));
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    const c2 = cv.getContext('2d', { willReadFrequently: true });
    c2.fillStyle = '#fff'; c2.fillRect(0, 0, w, h);
    c2.drawImage(TR.bitmap, 0, 0, w, h);
    const t0 = performance.now();
    TR.result = traceImage({ data: c2.getImageData(0, 0, w, h).data, w, h }, o);
    const pts = TR.result.paths.reduce((a, p) => a + p.pts.length, 0);
    if (o.threshold === null) { document.getElementById('tr-thr').value = Math.round(TR.result.threshold); }
    document.getElementById('tr-thrVal').textContent = Math.round(TR.result.threshold) + (o.threshold === null ? ' (auto)' : '');
    document.getElementById('tr-stats').textContent =
      `${TR.result.paths.length} lines · ${pts} points · ${w} × ${h} px · ${((performance.now() - t0) / 1000).toFixed(2)} s`;
    drawTracePreview();
    if (useNow === true) useTrace();
  }, useNow === true ? 0 : 160);
}

function drawTracePreview() {
  const cv = document.getElementById('traceCanvas');
  if (!cv || !TR.result) return;
  const ctx = setupCanvas(cv), W = cv.clientWidth, H = cv.clientHeight;
  const { w, h } = TR.result, k = Math.min((W - 16) / w, (H - 16) / h), ox = (W - w * k) / 2, oy = (H - h * k) / 2;
  ctx.globalAlpha = 0.22; ctx.drawImage(TR.bitmap, ox, oy, w * k, h * k); ctx.globalAlpha = 1;
  const css = getComputedStyle(document.documentElement);
  ctx.strokeStyle = css.getPropertyValue('--accent').trim(); ctx.lineWidth = 1.4; ctx.lineJoin = 'round';
  for (const p of TR.result.paths) {
    ctx.beginPath();
    p.pts.forEach((q, i) => (i ? ctx.lineTo(ox + q.x * k, oy + q.y * k) : ctx.moveTo(ox + q.x * k, oy + q.y * k)));
    if (p.closed) ctx.closePath();
    ctx.stroke();
  }
}

function useTrace() {
  if (!TR.result || !TR.result.paths.length) return log('No lines found — lower the detail threshold or change the mode.', 'warn');
  setDrawing(pathsToStrokes(TR.result.paths), TR.name, { source: `${TR.name}|${TR.bitmap.width}x${TR.bitmap.height}` });
  log(`Picture converted: ${TR.result.paths.length} lines. Check the preview, then Draw.`, 'ok');
}

function downloadTraceSvg() {
  if (!TR.result) return;
  downloadText(`${TR.name || 'drawing'}-lines.svg`, pathsToSvg(TR.result.paths, TR.result.w, TR.result.h), 'image/svg+xml');
}

/* ----- wiring ----- */
for (const id of ['tr-mode', 'tr-detail', 'tr-curve', 'tr-invert', 'tr-res', 'tr-auto']) {
  document.getElementById(id).addEventListener('input', () => retrace());
  document.getElementById(id).addEventListener('change', () => retrace());
}
document.getElementById('tr-thr').addEventListener('input', () => { document.getElementById('tr-auto').checked = false; retrace(); });
for (const [id, out] of [['tr-detail', 'tr-detailVal'], ['tr-curve', 'tr-curveVal']]) {
  const upd = () => { document.getElementById(out).textContent = document.getElementById(id).value; };
  document.getElementById(id).addEventListener('input', upd); upd();
}
document.getElementById('btnTraceUse').onclick = useTrace;
document.getElementById('btnTraceSvg').onclick = downloadTraceSvg;
document.getElementById('btnPause').onclick = togglePause;
document.getElementById('btnTestSquare').onclick = () => testSquare();
document.getElementById('btnAutoCal').onclick = () => openAutoCal();
document.getElementById('plot-motion').onchange = () => { if (S.plot.stats) renderPlotStats(); };
for (const [id, key] of [['plot-speed', 'draw'], ['plot-travel', 'travel']]) {
  const el = document.getElementById(id);
  el.value = S.speed[key];
  el.addEventListener('change', () => {
    const v = parseFloat(el.value);
    if (!(v >= 5 && v <= 300)) { el.value = S.speed[key]; return log('Speed must be between 5 and 300 mm/s.', 'warn'); }
    S.speed[key] = v; writeSetup(); saveSettings();
    if (S.plot.stats) renderPlotStats();
  });
}
renderPause();

// Keep the Plotter's speed boxes in step with Setup.
const _writeSetupBase = writeSetup;
writeSetup = function () {
  _writeSetupBase();
  const a = document.getElementById('plot-speed'), b = document.getElementById('plot-travel');
  if (a) a.value = S.speed.draw;
  if (b) b.value = S.speed.travel;
};
if (S.settingsMigrated) log('Settings from an earlier version were reset: the old reach limits allowed positions the arm cannot reach. Please run Auto-calibrate after connecting.', 'warn');
