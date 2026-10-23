/* ===================== SMART: MOTION ARBITER ===================== */
// Every smart feature moves the arm through here. All targets pass clampTarget (calibrated limits),
// are blocked while an alarm is active or a job runs, are capped to maxStep mm per command (so a
// tracking glitch can't fling the arm), and never queue more than 2 moves ahead.
const M = {
  owner: null, target: null, opts: {}, sending: false,
  seqGen: 0, seqBusy: false, seqLabel: '',
  deadband: 1.5, maxStep: 45, haltHooks: [],
};

function smartCanMove() { return !!S.dev && !S.alarm.length && !S.running && !cal.open && !AC.open; }

async function queueRoom(max = 2) {
  const cur = await S.dev.queueIndex();
  return ((S.dev.lastAccepted - cur) | 0) < max;
}

// Continuous following (hand, arm, face). Latest target wins.
function streamTo(owner, p, opts = {}) {
  if (S.live) { S.live = false; setLiveButton(); }
  M.owner = owner; M.target = { x: p.x, y: p.y, z: p.z }; M.opts = opts;
}
function streamRelease(owner) {
  if (M.owner === owner) { M.owner = null; M.target = null; }
  if (typeof glideRelease === 'function') glideRelease(owner);
}

setInterval(async () => {
  if (M.sending || M.seqBusy || !M.target || !smartCanMove()) return;
  let t = clampTarget(M.target.x, M.target.y, M.target.z);
  if (typeof lockFollowTarget === 'function') t = lockFollowTarget(M.owner || 'smart', t);   // safety lock (part 55)
  if (typeof followGlide === 'function' && followGlide()) {        // smoothed, continuous following
    const db = M.opts.deadband ?? M.deadband;
    if (!GL.target || GL.owner !== M.owner || Math.hypot(t.x - GL.target.x, t.y - GL.target.y, t.z - GL.target.z) >= db) glideSet(M.owner, t);
    return;
  }
  const from = S.cmd || S.pos;
  const d = Math.hypot(t.x - from.x, t.y - from.y, t.z - from.z);
  if (d < (M.opts.deadband ?? M.deadband)) return;
  if (d > M.maxStep) {
    const k = M.maxStep / d;
    t = clampTarget(from.x + (t.x - from.x) * k, from.y + (t.y - from.y) * k, from.z + (t.z - from.z) * k);
    if (typeof lockFollowTarget === 'function') t = lockFollowTarget(M.owner || 'smart', t, true);
  }
  M.sending = true;
  try {
    if (await queueRoom(2)) { await S.dev.ptp(t.x, t.y, t.z, 0, M.opts.linear ? 2 : 1); S.cmd = t; }
  } catch (e) { log('Smart move error: ' + e.message, 'err'); }
  finally { M.sending = false; }
}, 66);

// Sends one move right now if the queue has room (used for beat-timed dance keyframes).
async function sendNow(p, mode = 1) {
  if (!smartCanMove() || M.sending || M.seqBusy) return false;
  M.sending = true;
  try {
    if (!(await queueRoom(2))) return false;
    let t = clampTarget(p.x, p.y, p.z);
    if (typeof lockFollowTarget === 'function') t = lockFollowTarget(M.owner || 'dance', t);
    await S.dev.ptp(t.x, t.y, t.z, p.r || 0, mode);
    S.cmd = t;
    return true;
  } catch (e) { log('Move error: ' + e.message, 'err'); return false; }
  finally { M.sending = false; }
}

// Plays a short scripted sequence (reaction, gesture response). Interrupts following while it runs.
async function playSequence(frames, label) {
  if (!smartCanMove() || M.seqBusy) return false;
  const gen = ++M.seqGen;
  M.seqBusy = true; M.seqLabel = label || '';
  renderSmartActivity();
  try {
    while (M.sending) await sleep(5);
    for (const f of frames) {
      if (gen !== M.seqGen || !smartCanMove()) return false;
      while (!(await queueRoom(2))) { await sleep(15); if (gen !== M.seqGen) return false; }
      let t = clampTarget(f.x, f.y, f.z);
      if (typeof lockFollowTarget === 'function') t = lockFollowTarget('reactions', t);
      await S.dev.ptp(t.x, t.y, t.z, f.r || 0, 1);
      S.cmd = t;
      await sleep(f.wait ?? 150);
    }
    return true;
  } catch (e) { log('Sequence error: ' + e.message, 'err'); return false; }
  finally {
    if (gen === M.seqGen) { M.seqBusy = false; M.seqLabel = ''; renderSmartActivity(); }
  }
}

function renderSmartActivity() {
  const el = document.getElementById('smartActivity');
  if (!el) return;
  el.textContent = M.seqBusy ? `Performing: ${M.seqLabel}` : M.owner ? `Following: ${M.owner}` : '';
  el.hidden = !el.textContent;
}

async function smartSpeed(v, a) {
  if (S.dev) { try { await S.dev.setSpeed(v, a); } catch (e) { log('Speed change failed: ' + e.message, 'err'); } }
}

// Stops every smart behaviour (dance, imitation, reactions, following).
function smartHalt() {
  M.seqGen++; M.seqBusy = false; M.target = null; M.owner = null;
  for (const fn of M.haltHooks) { try { fn(); } catch (e) { console.error(e); } }
  renderSmartActivity();
}

// STOP button, alarms and the Escape key all halt the smart features too.
const _stopAllBase = stopAll;
stopAll = async function () { smartHalt(); await _stopAllBase(); };
document.addEventListener('keydown', ev => {
  if (ev.key === 'Escape') { ev.preventDefault(); stopAll(); log('Escape pressed — everything stopped.', 'warn'); }
});
setInterval(() => { if (S.alarm.length && (M.target || M.seqBusy)) smartHalt(); }, 250);
