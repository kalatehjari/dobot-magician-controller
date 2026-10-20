/* ===================== SMART: CAMERA & VISION HUB ===================== */
// MediaPipe Tasks Vision, pinned to 0.10.35. The 1.x builds contain a usage-metrics endpoint
// (odml.pa.googleapis.com) with no opt-out; 0.10.35 has none. All video analysis runs inside Chrome —
// frames are never uploaded. Optional ?mpbase=…&modelbase=… lets you self-host the files.
const MP_VERSION = '0.10.35';
const QS = new URLSearchParams(location.search);
const MP_BASE = QS.get('mpbase') || `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}`;
const MODEL_BASE = QS.get('modelbase');
const MODEL_URLS = {
  face: MODEL_BASE ? MODEL_BASE + '/face_landmarker.task' : 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
  gesture: MODEL_BASE ? MODEL_BASE + '/gesture_recognizer.task' : 'https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task',
  pose: MODEL_BASE ? MODEL_BASE + '/pose_landmarker_lite.task' : 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
};
const MODEL_NAMES = { face: 'Face', gesture: 'Hands', pose: 'Body' };

const V = {
  stream: null, running: false, lib: null, fileset: null,
  tasks: { face: null, gesture: null, pose: null }, loading: {}, delegate: {}, status: { face: 'off', gesture: 'off', pose: 'off' },
  want: { face: new Set(), gesture: new Set(), pose: new Set() },
  handlers: { face: [], gesture: [], pose: [] }, last: { face: null, gesture: null, pose: null },
  lastVideoTime: -1, frames: 0, fps: 0, fpsT: 0, aspect: 4 / 3, mirror: true, overlay: true,
  localModels: {}, errors: 0,
};

function onVision(kind, fn) { V.handlers[kind].push(fn); }

function setVisionStatus(kind, s) { V.status[kind] = s; renderCamStatus(); }

function renderCamStatus() {
  const box = document.getElementById('camModels');
  if (!box) return;
  box.innerHTML = Object.keys(MODEL_NAMES).map(k => {
    const s = V.status[k];
    const cls = s.startsWith('ready') ? 'ok' : s === 'loading' ? 'busy' : s === 'error' ? 'bad' : '';
    return `<span class="chip ${cls}">${MODEL_NAMES[k]}: ${s}</span>`;
  }).join('');
  const btn = document.getElementById('btnCam');
  if (btn) { btn.textContent = V.stream ? 'Camera off' : 'Camera on'; btn.classList.toggle('on', !!V.stream); }
  const fps = document.getElementById('camFps');
  if (fps) fps.textContent = V.stream ? `${V.fps.toFixed(0)} fps` : 'camera off';
}

async function cameraStart() {
  if (V.stream) return;
  if (!(window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia))
    throw new Error('Camera is not available here. Open this file in Chrome or Edge.');
  V.stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }, audio: false });
  const video = document.getElementById('camVideo');
  video.srcObject = V.stream;
  video.muted = true; video.playsInline = true;
  await video.play();
  V.aspect = (video.videoWidth || 640) / (video.videoHeight || 480);
  V.running = true; V.lastVideoTime = -1;
  requestAnimationFrame(visionLoop);
  log('Camera on. Video stays on this computer.', 'ok');
  renderCamStatus();
}

function cameraStop() {
  V.running = false;
  if (V.stream) V.stream.getTracks().forEach(t => t.stop());
  V.stream = null;
  const video = document.getElementById('camVideo');
  if (video) video.srcObject = null;
  const ov = document.getElementById('camOverlay');
  if (ov) ov.getContext('2d').clearRect(0, 0, ov.width, ov.height);
  renderCamStatus();
}

async function loadVisionLib() {
  if (V.lib) return V.lib;
  V.lib = await import(MP_BASE + '/vision_bundle.mjs');
  V.fileset = await V.lib.FilesetResolver.forVisionTasks(MP_BASE + '/wasm');
  return V.lib;
}

async function ensureTask(kind) {
  if (V.tasks[kind]) return V.tasks[kind];
  if (V.loading[kind]) return V.loading[kind];
  setVisionStatus(kind, 'loading');
  V.loading[kind] = (async () => {
    const lib = await loadVisionLib();
    const Cls = { face: lib.FaceLandmarker, gesture: lib.GestureRecognizer, pose: lib.PoseLandmarker }[kind];
    const extra = kind === 'face' ? { numFaces: 1, outputFaceBlendshapes: true }
      : kind === 'gesture' ? { numHands: 1, minHandDetectionConfidence: 0.5 } : { numPoses: 1 };
    const asset = V.localModels[kind] ? { modelAssetBuffer: V.localModels[kind] } : { modelAssetPath: MODEL_URLS[kind] };
    let task = null, delegate = 'GPU';
    try {
      task = await Cls.createFromOptions(V.fileset, { baseOptions: { ...asset, delegate: 'GPU' }, runningMode: 'VIDEO', ...extra });
    } catch (e) {
      delegate = 'CPU';
      task = await Cls.createFromOptions(V.fileset, { baseOptions: { ...asset, delegate: 'CPU' }, runningMode: 'VIDEO', ...extra });
    }
    V.tasks[kind] = task; V.delegate[kind] = delegate;
    setVisionStatus(kind, `ready (${delegate})`);
    log(`${MODEL_NAMES[kind]} model ready (${delegate}).`, 'ok');
    return task;
  })();
  try { return await V.loading[kind]; }
  catch (e) { setVisionStatus(kind, 'error'); throw new Error(`${MODEL_NAMES[kind]} model failed to load: ${e.message || e}. Check the internet connection, or load local model files in Setup.`); }
  finally { V.loading[kind] = null; }
}

// A feature asks for a model; the camera starts if needed.
async function visionRequire(kind, who) {
  V.want[kind].add(who);
  await cameraStart();
  await ensureTask(kind);
}

// A feature no longer needs a model; the camera turns off when nothing needs it.
function visionRelease(kind, who) {
  V.want[kind].delete(who);
  if (!Object.values(V.want).some(s => s.size) && !V.keepCamera) cameraStop();
}

function visionLoop() {
  if (!V.running) return;
  const video = document.getElementById('camVideo');
  if (video.readyState >= 2 && video.currentTime !== V.lastVideoTime) {
    V.lastVideoTime = video.currentTime;
    const ts = performance.now();
    for (const kind of ['face', 'gesture', 'pose']) {
      if (!V.want[kind].size || !V.tasks[kind]) { V.last[kind] = null; continue; }
      try {
        const res = kind === 'face' ? V.tasks.face.detectForVideo(video, ts)
          : kind === 'gesture' ? V.tasks.gesture.recognizeForVideo(video, ts)
          : V.tasks.pose.detectForVideo(video, ts);
        V.last[kind] = res;
        for (const fn of V.handlers[kind]) { try { fn(res, ts); } catch (e) { console.error(e); } }
      } catch (e) {
        if (++V.errors <= 3) log(`Vision error (${kind}): ${e.message}`, 'err');
      }
    }
    if (V.overlay) drawOverlay(video);
    V.frames++; V.framesTotal = (V.framesTotal || 0) + 1;
    if (ts - V.fpsT > 1000) { V.fps = V.frames * 1000 / (ts - V.fpsT); V.frames = 0; V.fpsT = ts; renderCamStatus(); }
  }
  requestAnimationFrame(visionLoop);
}

const HAND_LINKS = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12], [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]];
const FACE_OUTLINE = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10];

function drawOverlay(video) {
  const ov = document.getElementById('camOverlay');
  const W = video.videoWidth || 640, H = video.videoHeight || 480;
  if (ov.width !== W || ov.height !== H) { ov.width = W; ov.height = H; }
  const ctx = ov.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  ctx.lineWidth = 2;
  const f = V.last.face;
  if (f && f.faceLandmarks && f.faceLandmarks[0]) {
    const lm = f.faceLandmarks[0];
    ctx.strokeStyle = 'rgba(96,165,250,0.9)';
    ctx.beginPath();
    FACE_OUTLINE.forEach((i, k) => { const p = lm[i]; k ? ctx.lineTo(p.x * W, p.y * H) : ctx.moveTo(p.x * W, p.y * H); });
    ctx.stroke();
    ctx.fillStyle = 'rgba(96,165,250,0.9)';
    for (const i of [33, 263, 1, 61, 291, 13, 14, 159, 386]) { const p = lm[i]; ctx.beginPath(); ctx.arc(p.x * W, p.y * H, 2.5, 0, 7); ctx.fill(); }
  }
  const g = V.last.gesture;
  if (g && g.landmarks && g.landmarks[0]) {
    const lm = g.landmarks[0];
    ctx.strokeStyle = IM.pinchOn ? 'rgba(251,191,36,0.95)' : 'rgba(74,222,128,0.9)';
    ctx.beginPath();
    for (const [a, b] of HAND_LINKS) { ctx.moveTo(lm[a].x * W, lm[a].y * H); ctx.lineTo(lm[b].x * W, lm[b].y * H); }
    ctx.stroke();
    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath(); ctx.arc(lm[8].x * W, lm[8].y * H, 6, 0, 7); ctx.fill();
  }
  const p = V.last.pose;
  if (p && p.landmarks && p.landmarks[0]) {
    const lm = p.landmarks[0];
    ctx.strokeStyle = 'rgba(244,114,182,0.9)'; ctx.lineWidth = 4;
    ctx.beginPath();
    for (const [a, b] of [[11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24]]) {
      if ((lm[a].visibility ?? 1) < 0.5 || (lm[b].visibility ?? 1) < 0.5) continue;
      ctx.moveTo(lm[a].x * W, lm[a].y * H); ctx.lineTo(lm[b].x * W, lm[b].y * H);
    }
    ctx.stroke();
  }
}

// The single camera card is moved into whichever smart tab is visible.
function placeCamera(tab) {
  const slot = document.getElementById('camSlot-' + tab);
  const card = document.getElementById('camCard');
  if (!slot || !card || card.parentElement === slot) return;
  slot.appendChild(card);
  const video = document.getElementById('camVideo');
  if (V.stream && video.paused) video.play().catch(() => {});
}

function applyMirror() {
  for (const id of ['camVideo', 'camOverlay']) document.getElementById(id).classList.toggle('mirror', V.mirror);
}

// Offline option: load .task files picked by the user (names must contain face / gesture / pose).
async function loadLocalModels(files) {
  let n = 0;
  for (const f of files) {
    const name = f.name.toLowerCase();
    const kind = name.includes('face') ? 'face' : name.includes('gesture') ? 'gesture' : name.includes('pose') ? 'pose' : null;
    if (!kind) continue;
    V.localModels[kind] = new Uint8Array(await f.arrayBuffer());
    if (V.tasks[kind]) { try { V.tasks[kind].close(); } catch (e) {} V.tasks[kind] = null; setVisionStatus(kind, 'off'); }
    n++;
  }
  log(n ? `Using ${n} local model file(s).` : 'No model files recognised — names must contain face, gesture or pose.', n ? 'ok' : 'warn');
}
