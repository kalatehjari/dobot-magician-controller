/* ===================== PROTOCOL (verified against pydobot 1.3.2) ===================== */
const CMD = {
  POSE: 10, PTP_JOINT: 80, PTP_COORD: 81, PTP_JUMP: 82, PTP_COMMON: 83, PTP: 84,
  SUCTION: 62, GRIPPER: 63,
  Q_START: 240, Q_STOP: 241, Q_CLEAR: 245, Q_INDEX: 246,
};

// Frame: AA AA | len | id | ctrl | params... | checksum
// len = 2 + params.length ; checksum = (256 - (id+ctrl+params) mod 256) mod 256
function encodeFrame(id, ctrl, params) {
  const p = params || [];
  const len = 2 + p.length;
  const out = new Uint8Array(len + 4);
  out[0] = 0xAA; out[1] = 0xAA; out[2] = len; out[3] = id & 0xFF; out[4] = ctrl & 0xFF;
  let sum = (id + ctrl) & 0xFF;
  for (let i = 0; i < p.length; i++) { out[5 + i] = p[i] & 0xFF; sum = (sum + p[i]) & 0xFF; }
  out[len + 3] = (256 - sum) & 0xFF;
  return out;
}

// Splits a byte buffer into complete frames; returns leftover bytes.
function parseFrames(buf) {
  const frames = [];
  let i = 0;
  while (i < buf.length) {
    if (buf[i] !== 0xAA) { i++; continue; }
    if (i + 1 >= buf.length) break;
    if (buf[i + 1] !== 0xAA) { i++; continue; }
    if (i + 2 >= buf.length) break;
    const len = buf[i + 2];
    const total = len + 4;
    if (i + total > buf.length) break;
    const id = buf[i + 3], ctrl = buf[i + 4];
    const params = buf.slice(i + 5, i + 3 + len);
    let sum = 0;
    for (let k = i + 3; k < i + 3 + len; k++) sum += buf[k];
    const ok = ((sum + buf[i + 3 + len]) & 0xFF) === 0;
    frames.push({ id, ctrl, params, ok });
    i += total;
  }
  return { frames, rest: buf.slice(i) };
}

function hexOf(bytes) {
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join(' ').toUpperCase();
}

function f32bytes(arr) {
  const b = new Uint8Array(arr.length * 4);
  const dv = new DataView(b.buffer);
  arr.forEach((v, i) => dv.setFloat32(i * 4, v, true));
  return b;
}

function u32bytes(v) {
  const b = new Uint8Array(4);
  new DataView(b.buffer).setUint32(0, v >>> 0, true);
  return b;
}

/* ---------- Real USB serial transport (Web Serial API, Chrome/Edge) ---------- */
class SerialIO {
  constructor(port) {
    this.port = port;
    this.buf = new Uint8Array(0);
    this.waiters = [];
    this.closed = false;
  }
  async open() {
    await this.port.open({ baudRate: 115200, dataBits: 8, stopBits: 1, parity: 'none', flowControl: 'none' });
    this.writer = this.port.writable.getWriter();
    this.reader = this.port.readable.getReader();
    this._readLoop();
  }
  async _readLoop() {
    try {
      while (!this.closed) {
        const { value, done } = await this.reader.read();
        if (done) break;
        if (!value || !value.length) continue;
        const merged = new Uint8Array(this.buf.length + value.length);
        merged.set(this.buf); merged.set(value, this.buf.length);
        const { frames, rest } = parseFrames(merged);
        this.buf = rest;
        for (const f of frames) {
          const wi = this.waiters.findIndex(w => w.id === f.id);
          if (wi >= 0) {
            const [w] = this.waiters.splice(wi, 1);
            clearTimeout(w.timer);
            w.resolve(f);
          } else if (DEBUG.frames) log('<< ' + hexOf(encodeFrame(f.id, f.ctrl, f.params)), 'dim');
        }
      }
    } catch (e) {
      this.closed = true;
      log('Serial read error: ' + e.message, 'err');
      setConnected(false);
    }
  }
  exchange(frame) {
    const id = frame[3];
    return new Promise((resolve, reject) => {
      const w = { id, resolve, reject, timer: null };
      w.timer = setTimeout(() => {
        this.waiters = this.waiters.filter(x => x !== w);
        reject(new Error('No reply from robot (command ' + id + ')'));
      }, 1500);
      this.waiters.push(w);
      this.writer.write(frame).catch(e => { clearTimeout(w.timer); reject(e); });
    });
  }
  async close() {
    this.closed = true;
    try { await this.reader.cancel(); } catch (e) {}
    try { this.reader.releaseLock(); } catch (e) {}
    try { this.writer.releaseLock(); } catch (e) {}
    try { await this.port.close(); } catch (e) {}
  }
}

/* ---------- Simulator: same frames, no hardware. Lets every feature be tested safely. ---------- */
// Kinematic: it keeps joint angles, uses the Magician geometry (part 31), homes to a real pose and
// raises the same limit alarm (code 18) as the arm when asked to go somewhere it cannot reach.
class SimIO {
  constructor() {
    this.m = { dR: 59.7, dZ: 0 };                     // simulated tool offsets (suction-cup style)
    this.homeJ = { j1: 0, j2: 20, j3: 25 };
    this.st = { j1: 10, j2: 35, j3: 30, r: 0, idx: 0, exec: 0, suction: 0, gripper: 0,
                alarms: new Set(), paused: false, pending: [], ptpCount: 0, cpCount: 0, cpParams: null };
    this._pose();
  }
  _pose() {
    const st = this.st, p = magFK(st.j2, st.j3, this.m);
    st.x = p.r * Math.cos(st.j1 * DEG); st.y = p.r * Math.sin(st.j1 * DEG); st.z = p.z;
  }
  _moveTo(x, y, z) {
    if (this.st.alarms.size) return false;
    const th = Math.atan2(y, x) / DEG, j = magIK(Math.hypot(x, y), z, this.m);
    if (th < MAG.j1[0] || th > MAG.j1[1] || !j || !magJointsOk(j, 0)) { this.st.alarms.add(18); return false; }
    Object.assign(this.st, { j1: th, j2: j.j2, j3: j.j3 });
    this._pose();
    return true;
  }
  _queue(fn) {                                         // executes now, or later if paused
    const st = this.st;
    st.idx++;
    const idx = st.idx;
    const run = () => { fn(); st.exec = idx; };
    if (st.paused) st.pending.push(run); else run();
    return u32bytes(idx);
  }
  async exchange(frame) {
    const f = parseFrames(frame).frames[0];
    const st = this.st;
    const dv = new DataView(f.params.buffer, f.params.byteOffset, f.params.byteLength);
    let params = new Uint8Array(0);
    switch (f.id) {
      case CMD.POSE: {
        params = new Uint8Array(32);
        const o = new DataView(params.buffer);
        [st.x, st.y, st.z, st.r, st.j1, st.j2, st.j3, st.r].forEach((v, i) => o.setFloat32(i * 4, v, true));
        break;
      }
      case CMD.PTP: {
        const mode = f.params[0];
        const x = dv.getFloat32(1, true), y = dv.getFloat32(5, true), z = dv.getFloat32(9, true), r = dv.getFloat32(13, true);
        st.ptpCount++;
        params = this._queue(() => { if (mode <= 2 || mode === 9) this._moveTo(x, y, z); st.r = r; });
        break;
      }
      case 91: {                                        // CP move: mode byte, x, y, z, velocity
        const absolute = f.params[0] === 1;
        let x = dv.getFloat32(1, true), y = dv.getFloat32(5, true), z = dv.getFloat32(9, true);
        st.cpCount++;
        params = this._queue(() => { if (!absolute) { x += st.x; y += st.y; z += st.z; } this._moveTo(x, y, z); });
        break;
      }
      case 90: st.cpParams = [dv.getFloat32(0, true), dv.getFloat32(4, true), dv.getFloat32(8, true), f.params[12]]; break;
      case 31: params = this._queue(() => { if (!st.alarms.size) { Object.assign(st, this.homeJ); this._pose(); } }); break;
      case 20: {
        if (f.ctrl === 0) { params = new Uint8Array(32); for (const c of st.alarms) params[c >> 3] |= 1 << (c & 7); }
        else st.alarms.clear();
        break;
      }
      case CMD.Q_STOP: st.paused = true; break;
      case CMD.Q_START: st.paused = false; for (const run of st.pending.splice(0)) run(); break;
      case CMD.Q_CLEAR: st.pending = []; st.exec = st.idx; break;
      case CMD.Q_INDEX: params = u32bytes(st.exec); break;
      case CMD.SUCTION: st.suction = f.params[1] || 0; break;
      case CMD.GRIPPER: st.gripper = f.params[1] || 0; break;
      default: break;
    }
    return parseFrames(encodeFrame(f.id, f.ctrl, params)).frames[0];
  }
  async close() {}
}

/* ---------- Command layer ---------- */
class Dobot {
  constructor(io) {
    this.io = io;
    this.chain = Promise.resolve();   // serialises all requests (one in flight at a time)
    this.lastAccepted = 0;            // last queued-command index the robot accepted
  }
  call(id, ctrl, params) {
    const frame = encodeFrame(id, ctrl, params || []);
    if (DEBUG.frames) log('>> ' + hexOf(frame), 'dim');
    const p = this.chain.then(() => this.io.exchange(frame));
    this.chain = p.catch(() => {});
    return p;
  }
  async init() {
    await this.call(CMD.Q_START, 1);
    await this.call(CMD.Q_CLEAR, 1);
    await this.setSpeed(S.speed.live, S.speed.accel);
  }
  // Speed for both motion types. Command 83 takes percentage ratios (kept at 100 %); 81 sets
  // straight-line (MOVL) speed in mm/s and mm/s²; 80 sets joint (MOVJ) speed in °/s and °/s².
  async setSpeed(v, a) {
    const vel = Math.min(320, Math.max(5, v)), acc = Math.min(400, Math.max(5, a));
    const jv = Math.min(320, Math.max(20, vel * 0.6)), ja = Math.min(320, Math.max(20, acc * 0.6));
    await this.call(CMD.PTP_COMMON, 3, f32bytes([100, 100]));
    await this.call(CMD.PTP_COORD, 3, f32bytes([vel, vel, acc, acc]));
    await this.call(CMD.PTP_JOINT, 3, f32bytes([jv, jv, jv, jv, ja, ja, ja, ja]));
  }
  // Queued PTP move. mode 2 = MOVL (straight line in Cartesian space). Returns queue index.
  async ptp(x, y, z, r = 0, mode = 2) {
    const p = new Uint8Array(17);
    const dv = new DataView(p.buffer);
    p[0] = mode;
    dv.setFloat32(1, x, true); dv.setFloat32(5, y, true);
    dv.setFloat32(9, z, true); dv.setFloat32(13, r, true);
    const res = await this.call(CMD.PTP, 3, p);
    if (res.params.length < 4) throw new Error('Unexpected reply to move command');
    const idx = new DataView(res.params.buffer, res.params.byteOffset, 4).getUint32(0, true);
    this.lastAccepted = idx;
    return idx;
  }
  async queueIndex() {
    const r = await this.call(CMD.Q_INDEX, 0);
    this.lastExec = new DataView(r.params.buffer, r.params.byteOffset, 4).getUint32(0, true);   // also feeds the live drawing view
    return this.lastExec;
  }
  // Pose: x, y, z, r and the four joint angles (degrees).
  async pose() {
    const r = await this.call(CMD.POSE, 0);
    const dv = new DataView(r.params.buffer, r.params.byteOffset, r.params.byteLength);
    const f = i => (r.params.byteLength >= (i + 1) * 4 ? dv.getFloat32(i * 4, true) : 0);
    return { x: f(0), y: f(1), z: f(2), r: f(3), j1: f(4), j2: f(5), j3: f(6), j4: f(7) };
  }
  // Alarm bitmask: 32 bytes, bit k of byte i = alarm (i*8+k). ID 20, ctrl 0 = read.
  async alarms() {
    const r = await this.call(20, 0);
    const codes = [];
    for (let i = 0; i < r.params.length; i++) {
      const b = r.params[i];
      if (!b) continue;
      for (let k = 0; k < 8; k++) if (b & (1 << k)) codes.push(i * 8 + k);
    }
    return codes;
  }
  // Clears all alarms. ID 20, ctrl 1.
  async clearAlarms() { await this.call(20, 1); }
  // Homing (centres the arm on its reference sensors). ID 31, ctrl 3 (queued), one reserved
  // 4-byte value (official HOMECmd {float temp}).
  async home() {
    const r = await this.call(31, 3, new Uint8Array(4));
    const idx = new DataView(r.params.buffer, r.params.byteOffset, 4).getUint32(0, true);
    this.lastAccepted = idx;
    return idx;
  }
  // Continuous-path move (official CPCmd): mode 1 = absolute, then x, y, z, velocity (mm/s).
  // Consecutive CP moves are blended without stopping, which is what smooth drawing needs.
  async cp(x, y, z, v) {
    const p = new Uint8Array(17);
    const dv = new DataView(p.buffer);
    p[0] = 1;
    dv.setFloat32(1, x, true); dv.setFloat32(5, y, true); dv.setFloat32(9, z, true); dv.setFloat32(13, v, true);
    const res = await this.call(91, 3, p);
    if (res.params.length < 4) throw new Error('Unexpected reply to CP move');
    const idx = new DataView(res.params.buffer, res.params.byteOffset, 4).getUint32(0, true);
    this.lastAccepted = idx;
    return idx;
  }
  // CP planner (official CPParams): planned acceleration, junction (corner) speed, actual
  // acceleration — non-real-time mode.
  async setCPParams(planAcc, junctionVel, acc) {
    const p = new Uint8Array(13);
    const dv = new DataView(p.buffer);
    dv.setFloat32(0, planAcc, true); dv.setFloat32(4, junctionVel, true); dv.setFloat32(8, acc, true); p[12] = 0;
    await this.call(90, 1, p);
  }
  async pauseQueue() { await this.call(CMD.Q_STOP, 1); }
  async resumeQueue() { await this.call(CMD.Q_START, 1); }
  async setSuction(on) { await this.call(CMD.SUCTION, 3, new Uint8Array([1, on ? 1 : 0])); }
  async setGripper(on) { await this.call(CMD.GRIPPER, 3, new Uint8Array([1, on ? 1 : 0])); }
  // Wait until every accepted command has been executed.
  async drain(gen) {
    for (;;) {
      if (gen !== S.gen) throw new Error('Stopped');
      const cur = await this.queueIndex();
      if (((this.lastAccepted - cur) | 0) <= 0) return;
      await sleep(40);
    }
  }
  // Runs {x,y,z[,mode][,kind:'cp',v]} moves or {pause:ms}, keeping at most `window` commands in
  // the robot's 32-slot queue. The executed index is only polled when the window is full.
  // track (optional) receives each command's queue index, so the screen can follow the drawing.
  async runQueue(cmds, onProgress, window = 8, track = null) {
    const gen = S.gen;
    let exec = await this.queueIndex();
    for (let i = 0; i < cmds.length; i++) {
      const c = cmds[i];
      if (gen !== S.gen) throw new Error('Stopped');
      if (c.pause != null) {
        await this.drain(gen);
        await sleep(c.pause);
        exec = await this.queueIndex();
      } else {
        while (((this.lastAccepted - exec) | 0) >= window) {
          await sleep(15);
          if (gen !== S.gen) throw new Error('Stopped');
          exec = await this.queueIndex();
        }
        if (c.kind === 'cp') await this.cp(c.x, c.y, c.z, c.v);
        else await this.ptp(c.x, c.y, c.z, 0, c.mode ?? 2);
      }
      if (track) { track.idx[i] = this.lastAccepted; track.sent = i + 1; }
      if (onProgress && (i % 10 === 0 || i === cmds.length - 1)) onProgress((i + 1) / cmds.length);
    }
    await this.drain(gen);
  }
}

/* Emergency stop: halts motion, clears the queue, re-arms the queue for next use. */
async function stopAll() {
  S.gen++;                      // invalidates any running job
  S.running = false;
  S.target = null;
  if (!S.dev) return;
  try {
    await S.dev.call(CMD.Q_STOP, 1);
    await S.dev.call(CMD.Q_CLEAR, 1);
    await S.dev.call(CMD.Q_START, 1);
    log('STOP sent — motion halted, queue cleared.', 'warn');
  } catch (e) { log('Stop failed: ' + e.message, 'err'); }
}

/* Clears alarms and re-arms the command queue so motion can resume. */
async function clearAndRearm() {
  if (!S.dev) return;
  await S.dev.clearAlarms();
  await S.dev.call(CMD.Q_STOP, 1);
  await S.dev.call(CMD.Q_CLEAR, 1);
  await S.dev.call(CMD.Q_START, 1);
  S.alarm = await S.dev.alarms();
  log(S.alarm.length ? 'Alarm still active: ' + alarmText(S.alarm) : 'Alarms cleared — arm re-armed.', S.alarm.length ? 'err' : 'ok');
}
function alarmText(codes) {
  return codes.map(c => (ALARM_NAMES[c] || ('code ' + c))).join(', ');
}
