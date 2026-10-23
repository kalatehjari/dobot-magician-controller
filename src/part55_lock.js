/* ===================== SAFETY LOCK ===================== */
// Next to Centre (home). Once the arm has been centred (so its position is known), the lock keeps
// every arm movement inside the allowed area: the green zone at the paper height ∩ the safe zone
// (less the margin), and never more than 1 mm below the paper. Before a drawing, hover round, test
// square, replay or click-move starts, its whole path is checked; if it would leave the area, an
// alert offers to adjust it (nothing moves) or to trim it to the boundary. Following (mouse drag,
// hand, arm, face, dance) holds at the boundary at the first breach and asks once per session.
// Homing and calibration are not limited. Underneath, every move sent to the arm is checked again
// (and sent as a straight line, so the check covers its whole path); one that would leave is refused.

const LOCK = { on: false, floor: 0, last: null, bypass: 0, trimOK: new Set(), held: new Map(), asking: null, bad: null, badUntil: 0, refused: 0, pillT: 0 };
const $lk = id => document.getElementById(id);
S.homedAt = 0;

function lockBypassed() {
  return LOCK.bypass > 0 || (typeof AC !== 'undefined' && AC.open) || (typeof cal !== 'undefined' && cal.open) || (typeof QT !== 'undefined' && QT.running);
}
const lockActive = () => LOCK.on && !lockBypassed();
function lockRegion() { return allowedRegion(); }
function lockFloor() { return S.limits.zDown - 1; }

function lockRender() {
  const b = $lk('btnLock');
  if (!b) return;
  b.classList.toggle('on', LOCK.on);
  b.setAttribute('aria-pressed', LOCK.on ? 'true' : 'false');
  $lk('lockLabel').textContent = LOCK.on ? 'Safety lock: on' : 'Safety lock';
  b.title = LOCK.on ? 'The arm is kept inside the allowed area. Click to turn the lock off.' : 'Keep every arm movement inside the green zone and your safe zone (the arm is centred first).';
}
function lockPill(text) {
  const p = $lk('lockPill');
  if (!p) return;
  p.textContent = text; p.hidden = false;
  clearTimeout(LOCK.pillT); LOCK.pillT = setTimeout(() => { p.hidden = true; }, 2500);
}

// A dialog with buttons; resolves with the chosen value.
function lockDialog(title, text, buttons) {
  return new Promise(res => {
    const m = $lk('lockAsk');
    $lk('lkTitle').textContent = title;
    $lk('lkText').textContent = text;
    const row = $lk('lkBtns');
    row.innerHTML = '';
    for (const bt of buttons) {
      const e = document.createElement('button');
      e.textContent = bt.label; if (bt.primary) e.className = 'primary'; else if (bt.ghost) e.className = 'ghost';
      e.onclick = () => { m.hidden = true; LOCK.asking = null; res(bt.value); };
      row.appendChild(e);
    }
    LOCK.asking = title;
    m.hidden = false;
  });
}

function lockAreaText() {
  const R = lockRegion(), z = drawZone();
  return `${safePoly() ? 'the green zone and your safe zone' : 'the green zone'} (${(R.area / 100).toFixed(0)} cm², ${z.margin} mm margin), and no lower than ${lockFloor().toFixed(1)} mm`;
}
async function lockOn() {
  if (!S.dev) return log('Connect the arm (or start the simulator) first.', 'warn');
  if (S.running) return log('Wait until the job has finished.', 'warn');
  if (!S.homedAt) {
    const go = await lockDialog('Safety lock', 'The lock keeps every movement of the arm inside the allowed area: ' + lockAreaText() +
      '. It needs the arm centred (homed) first, so that its position is known. The arm moves to its home position now.',
      [{ label: 'Cancel', value: false, ghost: true }, { label: 'Centre and lock', value: true, primary: true }]);
    if (!go) return;
    await goHome();
    if (!S.homedAt) return log('The arm was not centred, so the safety lock stays off.', 'warn');
  }
  const R = lockRegion();
  if (R.empty) return log('The allowed area is empty (the safe zone does not overlap the green zone) — the lock stays off.', 'err');
  LOCK.on = true; LOCK.floor = lockFloor(); LOCK.last = null; LOCK.trimOK.clear(); LOCK.held.clear();
  lockRender(); drawAll();
  log('Safety lock on: every movement stays inside ' + lockAreaText() + '.', 'ok');
  const p = S.pos;
  if (!regionHas(R, p.x, p.y, 0.05)) log('The arm is outside the allowed area now; its next move must bring it straight in.', 'warn');
}
function lockOff(why) {
  if (!LOCK.on) return;
  LOCK.on = false; LOCK.trimOK.clear(); LOCK.held.clear(); LOCK.bad = null;
  lockRender(); drawAll();
  log('Safety lock off' + (why ? ` (${why})` : '') + '.', why ? 'warn' : '');
}
// The safe zone, margin or pen height changed: the area and floor follow.
function lockZoneChanged() {
  if (!LOCK.on) return;
  LOCK.floor = lockFloor();
  const R = lockRegion();
  if (R.empty) { lockOff('the allowed area became empty'); return; }
  log('Safety lock area updated: ' + lockAreaText() + '.');
}

/* ----- checks before a movement starts ----- */
// Drawings, hover round, test square, replays: the whole path. Returns the moves to run (maybe
// trimmed), or null when the user chose to adjust.
async function lockGate(name, cmds, start, mode = 'move') {
  if (!lockActive()) return cmds;
  const R = lockRegion(), floor = LOCK.floor, chk = lockCheckPath(cmds, start, R, floor);
  if (chk.ok) return cmds;
  LOCK.bad = { cmds, start, idx: chk.badIdx }; LOCK.badUntil = Infinity;
  if (typeof drawPlot === 'function') drawPlot();
  const ch = await lockDialog(`Safety lock: ${name}`,
    `${chk.bad} of ${chk.moves} moves would leave the allowed area (up to ${chk.worst.toFixed(1)} mm outside)${document.getElementById('tab-plot').classList.contains('active') ? ', shown in red on the map' : ''}. ` +
    (mode === 'draw' ? 'Trimming keeps only the lines inside the area and lifts the pen round the rest.' : 'Trimming pulls the moves in to the boundary.'),
    [{ label: 'Adjust it myself', value: 'adjust', ghost: true }, { label: 'Trim to the boundary', value: 'trim', primary: true }]);
  LOCK.badUntil = performance.now() + 4000; setTimeout(() => { if (performance.now() >= LOCK.badUntil) { LOCK.bad = null; if (typeof drawPlot === 'function') drawPlot(); } }, 4100);
  if (ch !== 'trim') { log(`${name}: not started — adjust it so it stays inside the allowed area, or turn the safety lock off.`, 'warn'); return null; }
  let out;
  try { out = lockTrimPath(cmds, start, R, floor, { mode, zDown: S.limits.zDown, zUp: S.limits.zUp, route: allowedRouter() }); }
  catch (e) { log(`${name}: could not be trimmed (${e.message}).`, 'err'); return null; }
  out = out.map(c => (c.x === undefined ? c : { ...c, ...clampTarget(c.x, c.y, c.z) }));
  const again = lockCheckPath(out, start, R, floor);
  if (!again.ok || !out.some(c => c.x !== undefined)) { log(`${name}: nothing is left inside the allowed area after trimming — adjust it instead.`, 'err'); return null; }
  log(`${name}: trimmed to the allowed area.`, 'warn');
  return out;
}
// Last check before moves are sent as a job (no questions): refuses a path that leaves.
function lockAssert(name, cmds, start) {
  if (!lockActive()) return;
  const chk = lockCheckPath(cmds, start, lockRegion(), LOCK.floor);
  if (!chk.ok) throw new Error(`${chk.bad} move(s) would leave the allowed area — the safety lock stopped ${name}`);
}

// One move (Mouse control clicks, buttons, nudges): small steps stop at the boundary; others ask.
const _lkMoveTo = moveTo;
moveTo = async function (x, y, z, opts = {}) {
  if (!lockActive() || opts.exempt || !S.dev) {
    if (opts.exempt) { LOCK.bypass++; try { return await _lkMoveTo(x, y, z); } finally { LOCK.bypass--; } }
    return _lkMoveTo(x, y, z);
  }
  const t = clampTarget(x, y, z), from = LOCK.last || S.cmd || S.pos, R = lockRegion();
  if (lockSegOk(R, from, t, LOCK.floor)) return _lkMoveTo(t.x, t.y, t.z);
  const q = lockClampPoint(R, from, t, LOCK.floor);
  const moved = !!q && Math.hypot(q.x - from.x, q.y - from.y, q.z - from.z) > 0.2;
  if (opts.small) {
    if (moved) { lockPill('Stopped at the boundary'); return _lkMoveTo(q.x, q.y, q.z); }
    lockPill('At the boundary'); log('Safety lock: at the boundary — that way is outside the allowed area.', 'warn');
    return;
  }
  const ch = await lockDialog('Safety lock: move', `This move would go ${lockDepth(R, from, t, LOCK.floor).toFixed(1)} mm outside the allowed area.` +
    (moved ? ' Trimming stops it at the boundary.' : ' The arm is already at the boundary in that direction.'),
    moved ? [{ label: 'Adjust it myself', value: 'adjust', ghost: true }, { label: 'Trim to the boundary', value: 'trim', primary: true }] : [{ label: 'OK', value: 'adjust', primary: true }]);
  if (ch === 'trim' && moved) return _lkMoveTo(q.x, q.y, q.z);
  log('Move not made (safety lock).', 'warn');
};

/* ----- following: hold at the boundary, ask once per session ----- */
function lockFollowTarget(owner, t, quiet = false) {
  if (!lockActive() || !t) return t;
  const R = lockRegion(), from = LOCK.last || S.cmd || S.pos;
  if (LOCK.held.has(owner)) return LOCK.held.get(owner);
  if (lockSegOk(R, from, t, LOCK.floor)) return t;
  const q = lockClampPoint(R, from, t, LOCK.floor) || { ...from };
  if (quiet || LOCK.trimOK.has(owner)) { if (!quiet) lockPill('Trimming to the safety zone'); return q; }
  LOCK.held.set(owner, q);
  const who = owner === 'mouse' ? 'Live follow (mouse)' : owner === 'dance' ? 'Dancing' : owner === 'reactions' ? 'The face reactions' : `Following (${owner})`;
  lockDialog('Safety lock: boundary reached', `${who} reached the edge of the allowed area. The arm is holding at the boundary.`,
    [{ label: 'Stop following', value: 'stop', ghost: true }, { label: 'Trim for this session', value: 'trim', primary: true }]).then(ch => {
    LOCK.held.delete(owner);
    if (ch === 'trim') { LOCK.trimOK.add(owner); log(`${who}: moves outside the allowed area are trimmed to the boundary until it stops.`, 'warn'); return; }
    if (owner === 'mouse') { S.live = false; S.target = null; setLiveButton(); if (typeof glideRelease === 'function') glideRelease('mouse'); }
    else smartHalt();
    log(`${who} stopped at the safety boundary.`, 'warn');
  });
  return q;
}
function lockEndSession(owner) {
  if (owner) { LOCK.trimOK.delete(owner); LOCK.held.delete(owner); return; }
  for (const k of [...LOCK.trimOK]) if (k !== 'mouse') LOCK.trimOK.delete(k);
  for (const k of [...LOCK.held.keys()]) if (k !== 'mouse') LOCK.held.delete(k);
}
const _lkHalt = smartHalt;
smartHalt = function () { lockEndSession(null); return _lkHalt.apply(this, arguments); };
const _lkRelease = streamRelease;
streamRelease = function (owner) { lockEndSession(owner); return _lkRelease.apply(this, arguments); };
document.getElementById('btnLive').addEventListener('click', () => { setTimeout(() => { if (!S.live) lockEndSession('mouse'); }, 0); });

/* ----- underneath: every move sent to the arm ----- */
function lockGuard(x, y, z) {
  const from = LOCK.last || S.pos, to = { x, y, z };
  if (lockSegOk(lockRegion(), from, to, LOCK.floor)) return;
  LOCK.refused++;
  log(`Safety lock: a move to X ${x.toFixed(1)}, Y ${y.toFixed(1)}, Z ${z.toFixed(1)} would leave the allowed area — not sent.`, 'err');
  throw new Error('the safety lock refused a move outside the allowed area');
}
const _lkPtp = Dobot.prototype.ptp, _lkCp = Dobot.prototype.cp, _lkHome = Dobot.prototype.home;
Dobot.prototype.ptp = async function (x, y, z, r = 0, mode = 2) {
  if (lockActive()) { lockGuard(x, y, z); mode = 2; }                // straight lines, so the check covers the path
  const idx = await _lkPtp.call(this, x, y, z, r, mode);
  LOCK.last = { x, y, z };
  return idx;
};
Dobot.prototype.cp = async function (x, y, z, v) {
  if (lockActive()) lockGuard(x, y, z);
  const idx = await _lkCp.call(this, x, y, z, v);
  LOCK.last = { x, y, z };
  return idx;
};
Dobot.prototype.home = async function () {                            // centring: always allowed
  const idx = await _lkHome.call(this);
  LOCK.last = null; S.homedAt = Date.now();
  return idx;
};
const _lkStop = stopAll;
stopAll = async function () { LOCK.last = null; return _lkStop.apply(this, arguments); };
const _lkSetConn = setConnected;
setConnected = function (on) { if (!on) { S.homedAt = 0; lockOff(S.dev ? '' : 'disconnected'); } return _lkSetConn.apply(this, arguments); };

/* ----- on the map: the allowed area while locked, and what would leave it ----- */
function lockOverlay(ctx, v) {
  if (LOCK.on) {
    const R = lockRegion();
    ctx.save(); ctx.strokeStyle = cssVar('--danger'); ctx.lineWidth = 1.4; ctx.setLineDash([7, 4]);
    for (const r of R.rings) { ctx.beginPath(); r.P.forEach((p, i) => { const [x, y] = v.toS(p.x, p.y); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.closePath(); ctx.stroke(); }
    ctx.restore();
  }
  const b = LOCK.bad;
  if (b && performance.now() < LOCK.badUntil) {
    ctx.save(); ctx.strokeStyle = cssVar('--danger'); ctx.lineWidth = 3.5; ctx.lineCap = 'round'; ctx.beginPath();
    const prevOf = i => { for (let k = i - 1; k >= 0; k--) if (b.cmds[k].x !== undefined) return b.cmds[k]; return b.start; };
    for (const i of b.idx) { const a = prevOf(i), c = b.cmds[i]; if (!a) continue; const [x0, y0] = v.toS(a.x, a.y), [x1, y1] = v.toS(c.x, c.y); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); }
    ctx.stroke(); ctx.restore();
  }
}

document.getElementById('btnLock').onclick = () => (LOCK.on ? lockOff() : lockOn().catch(e => log('Safety lock: ' + e.message, 'err')));
lockRender();
