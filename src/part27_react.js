/* ===================== SMART: FACE READING & REACTIONS ===================== */
const REACT_MAP = [
  { id: 'happy', when: 'You smile', does: 'happy', kind: 'face' },
  { id: 'surprised', when: 'You look surprised', does: 'surprised', kind: 'face' },
  { id: 'sad', when: 'You look sad', does: 'sad', kind: 'face' },
  { id: 'angry', when: 'You frown angrily', does: 'angry', kind: 'face' },
  { id: 'kiss', when: 'You pucker your lips', does: 'kiss', kind: 'face' },
  { id: 'wink', when: 'You wink', does: 'wink', kind: 'face' },
  { id: 'nod', when: 'You nod (yes)', does: 'nod', kind: 'face' },
  { id: 'shake', when: 'You shake your head (no)', does: 'shake', kind: 'face' },
  { id: 'greet', when: 'You come back into view', does: 'greet', kind: 'face' },
  { id: 'Thumb_Up', when: 'Thumbs up', does: 'celebrate', kind: 'hand' },
  { id: 'Thumb_Down', when: 'Thumbs down', does: 'sulk', kind: 'hand' },
  { id: 'Victory', when: 'Victory / peace sign', does: 'wave', kind: 'hand' },
  { id: 'ILoveYou', when: '“I love you” sign', does: 'heart', kind: 'hand' },
  { id: 'Closed_Fist', when: 'Fist', does: 'fistbump', kind: 'hand' },
  { id: 'Pointing_Up', when: 'Point up', does: 'lookup', kind: 'hand' },
];
const EXPR_LABELS = { happy: 'Happy', surprised: 'Surprised', sad: 'Sad', angry: 'Angry', kiss: 'Kiss' };

const R = {
  active: false, base: null, wantBase: false, on: Object.fromEntries(REACT_MAP.map(r => [r.id, true])),
  expr: new ExpressionTracker(350), wink: new WinkDetector(), head: new HeadGestureDetector(), gest: new StableLabel(350, 'None'),
  lastReact: 0, present: false, lastFaceT: 0, lostAt: 0, everSeen: false,
  lookFilt: new OneEuroVec(3, 0.8, 0.01), mood: 'neutral', moodUntil: 0, events: [],
  pose: null, blinkL: 0, blinkR: 0, gesture: 'None',
};

function rOpt(id) { const el = document.getElementById(id); return el.type === 'checkbox' ? el.checked : parseFloat(el.value); }

function renderReactTable() {
  const box = document.getElementById('reactTable');
  box.innerHTML = REACT_MAP.map(r => `<div class="rrow"><label><input type="checkbox" data-r="${r.id}" ${R.on[r.id] ? 'checked' : ''}> ${r.when}</label>
    <span class="muted">→ ${REACTIONS[r.does].label}</span><button data-try="${r.does}" class="ghost">Try</button></div>`).join('');
  box.querySelectorAll('[data-r]').forEach(cb => cb.onchange = () => { R.on[cb.dataset.r] = cb.checked; saveSmartPrefs(); });
  box.querySelectorAll('[data-try]').forEach(b => b.onclick = () => performReaction(b.dataset.try, 'Try'));
}

async function reactStart() {
  if (R.active) return;
  R.active = true;
  document.getElementById('btnReact').textContent = 'Stop face reading';
  document.getElementById('btnReact').classList.add('on');
  try {
    await visionRequire('face', 'react');
  } catch (e) { log(e.message, 'err'); reactStop(); return; }
  if (rOpt('reactHands')) {
    // Hand signs are optional: if that model can't load, face reading carries on without them.
    try { await visionRequire('gesture', 'react'); }
    catch (e) { log(e.message + ' Face reading continues without hand signs.', 'warn'); visionRelease('gesture', 'react'); }
  }
  if (S.dev) await smartSpeed(S.speed.smart, S.speed.smart * 1.2);
  else log('Not connected — reactions are shown on screen only.', 'warn');
  log('Face reading on. Try smiling, nodding, winking or a thumbs-up.', 'ok');
}

function reactStop(fromHalt) {
  if (!R.active) return;
  R.active = false;
  visionRelease('face', 'react'); visionRelease('gesture', 'react');
  if (M.owner === 'look at me') streamRelease('look at me');
  document.getElementById('btnReact').textContent = 'Start face reading';
  document.getElementById('btnReact').classList.remove('on');
  R.present = false;
  drawEyes();
  if (!fromHalt && S.dev) smartSpeed(S.speed.live, S.speed.accel);
}
M.haltHooks.push(() => reactStop(true));

function addReactEvent(text) {
  R.events.unshift(`${new Date().toLocaleTimeString()}  ${text}`);
  R.events = R.events.slice(0, 6);
  document.getElementById('reactEvents').innerHTML = R.events.map(e => `<div>${e}</div>`).join('');
}

function performReaction(does, why) {
  const rx = REACTIONS[does];
  if (!rx) return;
  R.mood = does; R.moodUntil = performance.now() + 2500;
  addReactEvent(`${why} → ${rx.label}`);
  if (!S.dev) return;
  const C = S.cmd ? { x: S.cmd.x, y: S.cmd.y, z: S.cmd.z } : danceCentre();
  playSequence(reactionFrames(does, C, rOpt('reactAmp') || 30), rx.label);
}

// Returns false only when the reaction is blocked for now (cooldown or busy), so the caller can retry.
function trigger(id) {
  const row = REACT_MAP.find(r => r.id === id);
  if (!row || !R.on[id]) return true;
  if (row.kind === 'face' && !rOpt('reactFace')) return true;
  if (row.kind === 'hand' && (!rOpt('reactHands') || IM.active)) return true;
  const now = performance.now();
  if (now - R.lastReact < (rOpt('reactCooldown') || 2.5) * 1000 || M.seqBusy) return false;
  R.lastReact = now;
  performReaction(row.does, row.when);
  return true;
}

onVision('face', (res, tMs) => {
  if (!R.active) return;
  const lm = res.faceLandmarks && res.faceLandmarks[0];
  if (!lm) {
    if (R.present && tMs - R.lastFaceT > 1500) {
      R.present = false; R.lostAt = tMs;
      R.expr.stable.current = 'neutral'; R.expr.stable.cand = null; R.exprHandled = false;   // new episode when you return
      if (M.owner === 'look at me') streamRelease('look at me');
    }
    updateExprPanel(null);
    return;
  }
  const comingBack = !R.present && R.everSeen && tMs - R.lastFaceT > 3000;   // away for 3 s or more
  R.present = true; R.everSeen = true; R.lastFaceT = tMs;
  const cats = res.faceBlendshapes && res.faceBlendshapes[0] ? res.faceBlendshapes[0].categories : [];
  const bs = blendshapeMap(cats);
  if (R.wantBase) { R.base = { ...bs }; R.wantBase = false; log('Neutral face captured — expressions are now measured relative to it.', 'ok'); }
  const ev = R.expr.update(bs, R.base, tMs, rOpt('reactSens') || 1);
  const hp = headPose(lm, V.aspect);
  R.pose = hp; R.blinkL = bs.eyeBlinkLeft || 0; R.blinkR = bs.eyeBlinkRight || 0;
  const head = R.head.update(tMs, hp.yaw, hp.pitch);
  const wink = R.wink.update(R.blinkL, R.blinkR, tMs);
  if (comingBack) trigger('greet');
  // Each expression episode gets one reaction; if the cooldown blocks it, it is retried while it lasts.
  if (ev) R.exprHandled = false;
  if (R.expr.current !== 'neutral' && !R.exprHandled) R.exprHandled = trigger(R.expr.current);
  if (head) trigger(head);
  if (wink) trigger('wink');
  if (rOpt('reactLook') && !M.seqBusy && S.dev) {
    const B = smartBox(S.limits), gain = rOpt('reactLookGain') || 1;
    const yN = clamp((0.5 - hp.cx) * 2.2 * gain, -1, 1), zN = clamp((0.5 - hp.cy) * 2.2 * gain, -1, 1);
    const [x, y, z] = R.lookFilt.filter([B.xMid, yN * B.yHalf * 0.8, B.zMid + zN * B.zHalf * 0.7], tMs / 1000);
    streamTo('look at me', { x, y, z });
  }
  updateExprPanel(R.expr.scores);
});

onVision('gesture', (res, tMs) => {
  if (!R.active) return;
  const g = res.gestures && res.gestures[0] && res.gestures[0][0];
  R.gesture = g && g.score > 0.6 ? g.categoryName : 'None';
  const ev = R.gest.update(R.gesture, tMs);
  if (ev && ev.to !== 'None') trigger(ev.to);
});

function updateExprPanel(scores) {
  const now = performance.now();
  if (now - (R.lastPanel || 0) < 80) return;
  R.lastPanel = now;
  const box = document.getElementById('exprBars');
  if (!scores) { box.innerHTML = '<div class="muted">No face in view.</div>'; drawEyes(); return; }
  box.innerHTML = Object.keys(EXPR_LABELS).map(k => {
    const v = scores[k] || 0, cur = R.expr.current === k;
    return `<div class="bar-row ${cur ? 'cur' : ''}"><span>${EXPR_LABELS[k]}</span><div class="mbar"><div style="width:${(v * 100).toFixed(0)}%"></div></div></div>`;
  }).join('') + `<div class="muted" style="margin-top:6px">Reading: <b>${R.expr.current}</b> · head yaw ${R.pose.yaw.toFixed(2)} pitch ${R.pose.pitch.toFixed(2)} · hand: ${R.gesture.replace('_', ' ')}</div>`;
  drawEyes();
}

/* ----- robot eyes: look at you, show the robot's mood (or mirror yours) ----- */
function drawEyes() {
  const cv = document.getElementById('eyesCanvas');
  if (!cv || !document.getElementById('tab-react').classList.contains('active')) return;
  const ctx = setupCanvas(cv), W = cv.clientWidth, H = cv.clientHeight;
  const css = getComputedStyle(document.documentElement);
  const ink = css.getPropertyValue('--ink').trim(), panel = css.getPropertyValue('--panel').trim(), acc = css.getPropertyValue('--accent').trim();
  const now = performance.now();
  let mood = now < R.moodUntil ? R.mood : (R.present ? R.expr.current : 'sleepy');
  if (mood === 'celebrate' || mood === 'greet' || mood === 'wave') mood = 'happy';
  if (mood === 'sulk') mood = 'sad';
  const gx = R.pose ? clamp((R.pose.cx - 0.5) * 2, -1, 1) : 0;      // pupils follow you (mirrored view)
  const gy = R.pose ? clamp((R.pose.cy - 0.5) * 2, -1, 1) : 0;
  const ew = Math.min(W / 5, H / 1.6), eh = ew * 1.1, cy = H / 2;
  const blinking = R.present && R.blinkL > 0.6 && R.blinkR > 0.6;
  for (const side of [-1, 1]) {
    const cx = W / 2 + side * ew * 0.85;
    ctx.save(); ctx.translate(cx, cy);
    ctx.lineWidth = 4; ctx.strokeStyle = ink; ctx.fillStyle = panel;
    const closedLine = () => { ctx.beginPath(); ctx.moveTo(-ew / 2, 0); ctx.lineTo(ew / 2, 0); ctx.stroke(); };
    if (mood === 'happy') { ctx.beginPath(); ctx.arc(0, eh * 0.15, ew * 0.42, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke(); }
    else if (mood === 'kiss' || blinking || (mood === 'wink' && side === -1)) closedLine();
    else if (mood === 'sleepy') { ctx.beginPath(); ctx.arc(0, 0, ew * 0.42, Math.PI * 0.1, Math.PI * 0.9); ctx.stroke(); }
    else {
      const big = mood === 'surprised' ? 1.2 : 1;
      ctx.beginPath(); ctx.ellipse(0, 0, ew / 2 * big, eh / 2 * big, 0, 0, 7); ctx.fill(); ctx.stroke();
      const pr = ew * (mood === 'surprised' ? 0.13 : 0.18);
      const px = -gx * ew * 0.22, py = gy * eh * 0.2;
      ctx.fillStyle = mood === 'heart' ? '#e11d48' : ink;
      if (mood === 'heart') { ctx.font = `${pr * 3}px system-ui`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('♥', px, py); }
      else { ctx.beginPath(); ctx.arc(px, py, pr, 0, 7); ctx.fill(); }
      if (mood === 'sad' || mood === 'angry') {             // eyelid: droops outward (sad) or inward (angry)
        const tilt = (mood === 'sad' ? -1 : 1) * side;
        ctx.fillStyle = panel; ctx.beginPath();
        ctx.moveTo(-ew * 0.6, -eh * 0.6); ctx.lineTo(ew * 0.6, -eh * 0.6);
        ctx.lineTo(ew * 0.6, -eh * 0.1 + tilt * eh * 0.18); ctx.lineTo(-ew * 0.6, -eh * 0.1 - tilt * eh * 0.18); ctx.closePath(); ctx.fill();
        ctx.beginPath(); ctx.moveTo(-ew * 0.55, -eh * 0.1 - tilt * eh * 0.18); ctx.lineTo(ew * 0.55, -eh * 0.1 + tilt * eh * 0.18); ctx.stroke();
      }
    }
    ctx.restore();
  }
  ctx.fillStyle = acc; ctx.font = '13px system-ui'; ctx.textAlign = 'center';
  ctx.fillText(now < R.moodUntil ? (REACTIONS[R.mood] ? REACTIONS[R.mood].label : R.mood) : R.present ? `I see you · ${R.expr.current}` : R.active ? 'Looking for you…' : 'Face reading is off', W / 2, H - 10);
  ctx.textAlign = 'start';
}

/* ----- preferences (remembered in this browser) ----- */
function saveSmartPrefs() {
  const ids = ['reactSens', 'reactCooldown', 'reactAmp', 'reactLookGain', 'reactFace', 'reactHands', 'reactLook', 'danceSize', 'danceEnergy', 'danceLatency', 'danceSpeed', 'imitSpan', 'imitSmooth', 'imitFacing'];
  const p = { on: R.on };
  for (const id of ids) { const el = document.getElementById(id); if (el) p[id] = el.type === 'checkbox' ? el.checked : el.value; }
  try { localStorage.setItem('magician-smart', JSON.stringify(p)); } catch (e) {}
}

function loadSmartPrefs() {
  let p = null;
  try { p = JSON.parse(localStorage.getItem('magician-smart') || 'null'); } catch (e) {}
  if (!p) return;
  if (p.on) Object.assign(R.on, p.on);
  for (const [id, v] of Object.entries(p)) {
    const el = document.getElementById(id);
    if (!el || id === 'on') continue;
    if (el.type === 'checkbox') el.checked = !!v; else el.value = v;
  }
}
