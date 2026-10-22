/* ===================== 3D PRINTING: G-CODE LINK TO THE PRINTER, AND A SIMULATED PRINTER ===================== */
// Dobot's 3D-printer firmware takes Marlin-style G-code over the arm's USB serial port at 115200 baud (Dobot's guide
// sets up Repetier Host with "reset on connect: DTR low→high→low" and a 63-byte receive cache). Every line goes out
// with a line number and checksum ("N12 G1 X3 Y4*87"); the printer answers "ok" for each line, "Resend: n" when a
// line arrived damaged, and reports temperatures as "T:199.8 /200.0". By default one line is sent at a time and the
// next only after its "ok" (ping-pong), which can never overrun the printer's buffer.

function gcodeChecksum(s) { let c = 0; for (let i = 0; i < s.length; i++) c ^= s.charCodeAt(i) & 0xff; return c; }
function gcodeLine(n, cmd) { const s = 'N' + n + ' ' + cmd; return s + '*' + gcodeChecksum(s); }
// Strips comments and blank lines; keeps which file line each command came from (for the live view).
function gcodeCommands(text) {
  const cmds = [], src = [];
  text.split('\n').forEach((raw, i) => { const c = raw.replace(/;.*/, '').trim(); if (c) { cmds.push(c); src.push(i); } });
  return { cmds, src };
}
function parseTemps(line) {
  const m = /(?:^|\s)T:\s*(-?[\d.]+)(?:\s*\/\s*(-?[\d.]+))?/.exec(line);
  return m ? { t: +m[1], target: m[2] !== undefined ? +m[2] : null } : null;
}
const sleepMs = ms => new Promise(r => setTimeout(r, ms));

/* ---------- transport: the real USB serial port ---------- */
class GcodeSerial {
  constructor(port) { this.port = port; this.onLine = null; this.onClose = null; this.closed = false; this.buf = ''; }
  async open() {
    await this.port.open({ baudRate: 115200, dataBits: 8, stopBits: 1, parity: 'none', flowControl: 'none' });
    this.writer = this.port.writable.getWriter();
    this.reader = this.port.readable.getReader();
    this.enc = new TextEncoder(); this.dec = new TextDecoder();
    this._read();
  }
  async _read() {
    try {
      for (;;) {
        const { value, done } = await this.reader.read();
        if (done) break;
        this.buf += this.dec.decode(value, { stream: true });
        let k;
        while ((k = this.buf.search(/\r?\n/)) >= 0) {
          const line = this.buf.slice(0, k); this.buf = this.buf.slice(k + (this.buf[k] === '\r' ? 2 : 1));
          if (line.trim() && this.onLine) this.onLine(line.trim());
        }
      }
    } catch (e) { /* unplugged or closed */ }
    if (!this.closed) { this.closed = true; if (this.onClose) this.onClose(); }
  }
  write(text) { return this.writer.write(this.enc.encode(text)); }
  // DTR low → high → low, as Dobot's guide sets Repetier Host up: restarts the firmware.
  async reset() {
    try {
      await this.port.setSignals({ dataTerminalReady: false, requestToSend: false }); await sleepMs(120);
      await this.port.setSignals({ dataTerminalReady: true }); await sleepMs(120);
      await this.port.setSignals({ dataTerminalReady: false });
    } catch (e) { /* not every driver supports it; the firmware then simply keeps running */ }
  }
  async close() {
    this.closed = true;
    try { await this.reader.cancel(); } catch (e) {}
    try { this.reader.releaseLock(); } catch (e) {}
    try { this.writer.releaseLock(); } catch (e) {}
    try { await this.port.close(); } catch (e) {}
  }
}

/* ---------- transport: a simulated printer (Marlin behaviour, no hardware) ---------- */
// Checks line numbers and checksums like the firmware, buffers 16 moves, heats and cools, refuses cold extrusion,
// and keeps the path it printed so the tests and the live view can check it. speed: simulated seconds per real second.
class SimPrinter {
  constructor(opts = {}) {
    this.speed = opts.speed || 100;
    this.faultEvery = opts.faultEvery || 0;            // damage every n-th received line (tests the resend logic)
    this.dropOkAt = opts.dropOkAt || 0;                 // lose the "ok" of this received line once (tests the watchdog)
    this.trace = [];                                    // every command carried out, in order
    this.plateR = opts.plateR || 40;
    this.onLine = null; this.onClose = null; this.closed = false;
    this.log = [];                                      // everything executed, for tests: {cmd, x, y, z, e, t}
    this.temp = 22; this.target = 0; this.fan = 0; this.zSaved = 0; this.beeps = 0;
    this.out = []; this.replies = 0;                    // replies waiting to be delivered
    // the simulation follows real elapsed time (× speed), so it keeps pace even when the browser slows timers down
    this.lastT = Date.now();
    this.timer = setInterval(() => this._step(), 20);
    this._boot();
  }
  _boot() {
    this.boots = (this.boots || 0) + 1;
    this.inbuf = ''; this.lastN = 0; this.queue = []; this.block = null; this.killed = false; this.booting = 0.4;
    this.pos = { x: 0, y: 0, z: 30, e: 0 }; this.rel = false; this.relE = false; this.f = 1200; this.received = 0;
    this.target = 0; this.fan = 0; this.moves = 0; this.coldBlocked = 0; this.outside = 0; this.executedLines = 0;
  }
  async open() {}
  async reset() { this._boot(); }
  async close() { this.closed = true; clearInterval(this.timer); }
  write(text) {
    if (this.closed) return Promise.resolve();
    // like Marlin's emergency parser: M112 acts the moment it arrives, even while the printer is busy
    if (this.booting <= 0 && !this.killed && /(^|\n)\s*(N\d+\s+)?M112\b/i.test(text)) { this._kill(); return Promise.resolve(); }
    this.inbuf += text; this._step(); this._drain();
    return Promise.resolve();
  }
  _kill() { this.trace.push('M112'); this.killed = true; this.queue = []; this.block = null; this.target = 0; this.inbuf = ''; this._say('Error:Printer halted. kill() called!'); }
  _step() {
    const now = Date.now(), dt = Math.min(5, (now - this.lastT) / 1000) * this.speed;
    this.lastT = now;
    if (dt > 0) this._tick(dt);
  }
  // replies arrive a moment later, like over a cable (as a microtask: browsers slow timers in background pages)
  _say(line) {
    if (line === 'ok' && this.dropOkAt && this.received === this.dropOkAt) { this.dropOkAt = 0; return; }
    this.out.push(line);
    if (!this._sched) {
      this._sched = true;
      const deliver = () => { this._sched = false; const o = this.out.splice(0); for (const l of o) if (this.onLine && !this.closed) this.onLine(l); };
      // every 200th reply goes through a timer, so a fast simulated print still lets the page draw
      if (++this.replies % 200 === 0) setTimeout(deliver, 0); else Promise.resolve().then(deliver);
    }
  }
  // At 1000× and faster the simulation jumps ahead instead of waiting for real time: tests and the self-test then
  // finish quickly even where the browser slows timers down (hidden or headless pages).
  get fast() { return this.speed >= 1000; }
  _drain() {
    while (!this.block && this.booting <= 0 && !this.killed) {
      const k = this.inbuf.indexOf('\n'); if (k < 0) return;
      const raw = this.inbuf.slice(0, k).trim(); this.inbuf = this.inbuf.slice(k + 1);
      if (raw) this._line(raw);
    }
  }
  _line(raw) {
    this.received++;
    let cmd = raw;
    if (/^N\d+/.test(raw)) {
      const m = /^N(\d+)\s*(.*?)\*(\d+)\s*$/.exec(raw);
      const damaged = this.faultEvery && this.received % this.faultEvery === 0;
      if (!m) { this._say('Error:No Checksum with line number, Last Line: ' + this.lastN); this._say('Resend: ' + (this.lastN + 1)); this._say('ok'); return; }
      const n = +m[1], body = raw.slice(0, raw.lastIndexOf('*'));
      if (damaged || gcodeChecksum(body) !== +m[3]) { this._say('Error:checksum mismatch, Last Line: ' + this.lastN); this._say('Resend: ' + (this.lastN + 1)); this._say('ok'); return; }
      if (!/^M110\b/.test(m[2]) && n !== this.lastN + 1) { this._say('Error:Line Number is not Last Line Number+1, Last Line: ' + this.lastN); this._say('Resend: ' + (this.lastN + 1)); this._say('ok'); return; }
      this.lastN = n; cmd = m[2];
      if (/^M110\b/.test(cmd)) { const q = /N(\d+)/.exec(cmd.slice(4)); this.lastN = q ? +q[1] : n; }
    }
    this._exec(cmd.replace(/;.*/, '').trim());
  }
  _exec(cmd) {
    const [c, ...words] = cmd.split(/\s+/), P = {};
    for (const w of words) if (w) P[w[0].toUpperCase()] = parseFloat(w.slice(1));
    this.executedLines++; this.trace.push(cmd);
    switch (c.toUpperCase()) {
      case 'G0': case 'G1': {
        const p = this.pos, n = { ...p };
        for (const a of ['X', 'Y', 'Z']) if (a in P) n[a.toLowerCase()] = this.rel ? p[a.toLowerCase()] + P[a] : P[a];
        if ('E' in P) n.e = this.rel || this.relE ? p.e + P.E : P.E;
        if ('F' in P && P.F > 0) this.f = P.F;
        if (n.e > p.e + 1e-9 && this.temp < 170) { this.coldBlocked++; this._say('echo: cold extrusion prevented'); n.e = p.e; }
        const d = Math.hypot(n.x - p.x, n.y - p.y, n.z - p.z), de = Math.abs(n.e - p.e);
        const dur = Math.max(d, de) / (this.f / 60);
        if (Math.hypot(n.x, n.y) > this.plateR + 60 || n.z < -0.05) this.outside++;
        this.queue.push({ to: n, dur, ext: n.e > p.e + 1e-9 && d > 0 });
        this.pos = n; this.moves++;
        this.log.push({ cmd: c, x: n.x, y: n.y, z: n.z, e: n.e, t: this.temp, ext: n.e > p.e + 1e-9 && d > 0 });
        if (this.queue.length >= 16) {
          if (this.fast) this._tick(this.queue[0].dur + 1e-9);   // jump to when the oldest move is done
          else { this.block = { kind: 'queue' }; return; }
        }
        break;
      }
      case 'G4': if (this.fast) { this._tick((P.P || 0) / 1000 + (P.S || 0) + this.queue.reduce((a, m) => a + m.dur, 0)); break; }
        this.block = { kind: 'dwell', left: (P.P || 0) / 1000 + (P.S || 0) }; return;
      case 'G28': this.queue.push({ to: { ...this.pos, x: 0, y: 0, z: 30 }, dur: 2 }); this.pos = { ...this.pos, x: 0, y: 0, z: 30 }; break;
      case 'G90': this.rel = false; break;
      case 'G91': this.rel = true; break;
      case 'G92': for (const a of ['X', 'Y', 'Z', 'E']) if (a in P) this.pos[a.toLowerCase()] = P[a]; break;
      case 'G21': case 'M84': case 'M117': break;
      case 'M82': this.relE = false; break;
      case 'M83': this.relE = true; break;
      case 'M104': this.target = P.S || 0; break;
      case 'M109':
        this.target = P.S || 0;
        if (this.target > 0 && this.fast) { for (let k = 0; k < 2000 && Math.abs(this.temp - this.target) >= 2; k++) this._tick(1); this._say(` T:${this.temp.toFixed(1)} E:0 W:?`); break; }
        if (this.target > 0) { this.block = { kind: 'heat', report: 0 }; return; }
        break;
      case 'M105': if (this.dropOkAt && this.received === this.dropOkAt) { this.dropOkAt = 0; return; } this._say(`ok T:${this.temp.toFixed(1)} /${this.target.toFixed(1)} B:0.0 /0.0 @:${this.target > this.temp ? 127 : 0}`); return;
      case 'M106': this.fan = 'S' in P ? P.S : 255; break;
      case 'M107': this.fan = 0; break;
      case 'M110': break;
      case 'M112': this.trace.pop(); this._kill(); return;
      case 'M400': if (this.fast) { this._tick(this.queue.reduce((a, m) => a + m.dur, 0) + 1e-9); break; } this.block = { kind: 'finish' }; return;
      case 'M415': this.zSaved = this.pos.z; this.pos.z = 0; this.beeps++; this._say('echo:Z zero saved'); break;
      default: this._say(`echo:Unknown command: "${cmd}"`);
    }
    this._say('ok');
  }
  _tick(dt) {
    if (this.closed) return;
    if (this.booting > 0) { this.booting -= dt; if (this.booting <= 0) { this._say('start'); this._say('echo: Simulated Dobot 3D printer — no hardware'); this._drain(); } return; }
    // heater: first-order towards the target (about 2 minutes to 200 °C), cooling towards room temperature
    const T = this.target > 0 ? this.target : 22, tau = this.target > this.temp ? 25 : 90;
    this.temp += (T - this.temp) * Math.min(1, dt / tau);
    // planner: run queued moves
    let left = dt;
    while (left > 0 && this.queue.length) {
      const m = this.queue[0];
      if (m.dur > left) { m.dur -= left; left = 0; break; }
      left -= m.dur; this.queue.shift(); this.done = (this.done || 0) + 1;
    }
    const b = this.block;
    if (!b || this.killed) return;
    let free = false;
    if (b.kind === 'queue') free = this.queue.length < 16;
    else if (b.kind === 'finish') free = this.queue.length === 0;
    else if (b.kind === 'dwell') { b.left -= dt; free = b.left <= 0 && this.queue.length === 0; }
    else if (b.kind === 'heat') {
      b.report += dt;
      if (b.report >= 1) { b.report = 0; this._say(` T:${this.temp.toFixed(1)} E:0 W:?`); }
      free = Math.abs(this.temp - this.target) < 2;
    }
    if (free) { this.block = null; this._say('ok'); this._drain(); }
  }
}

/* ---------- the protocol ---------- */
class GcodeLink {
  constructor(io, opts = {}) {
    this.io = io; this.pingPong = opts.pingPong !== false; this.budget = opts.budget || 63; this.numbered = opts.numbered !== false;
    this.stallMs = opts.stallMs || 20000;
    this.n = 0; this.inflight = []; this.hist = new Map(); this.q = []; this.replay = null; this.resendFrom = null;
    this.temp = null; this.target = null; this.ready = false; this.lastRx = Date.now(); this.lastTx = 0;
    this.job = null; this.onEvent = null; this.closed = false; this.rx = []; this.errors = 0; this.resends = 0;
    io.onLine = l => this._rx(l);
    io.onClose = () => { this.closed = true; this._fail('The printer was disconnected.'); this._emit('closed'); };
    this.watch = setInterval(() => this._watchdog(), Math.min(1000, this.stallMs / 4));
  }
  _emit(type, data) { if (this.onEvent) try { this.onEvent(type, data); } catch (e) { console.error(e); } }
  // Restarts the firmware, waits for it, resets line numbers and checks it answers.
  async connect() {
    await this.io.open();
    this._gotStart = false;
    await this.io.reset();
    for (let k = 0; k < 40 && !this._gotStart; k++) await sleepMs(100);     // up to 4 s for "start"
    this.ready = true;
    this.inflight = []; this.q = []; this.n = 0;
    try {
      if (this.numbered) await this.send('M110 N0', 3000, true);
      await this.send('M105', 3000);
    } catch (e) {
      if (!this.numbered) throw e;
      // firmware without line numbers: try plain commands
      this.numbered = false; this.inflight = []; this.q = [];
      await this.send('M105', 3000);
    }
    this._emit('ready');
  }
  // Sends one command (ahead of any print job); resolves on its "ok".
  send(cmd, timeout = 0, isM110 = false) {
    return new Promise((resolve, reject) => {
      const item = { cmd, resolve, reject, isM110 };
      if (timeout) item.timer = setTimeout(() => { this.q = this.q.filter(x => x !== item); reject(new Error('No answer from the printer to ' + cmd + '. Is the Dobot 3D-printer firmware on the arm?')); }, timeout);
      this.q.push(item); this._pump();
    });
  }
  _line(item) {
    if (!this.numbered) return item.cmd;
    if (item.isM110) { this.n = 0; this.ackedN = 0; return gcodeLine(0, 'M110 N0'); }
    if (item.resync) return gcodeLine(this.n, 'M110 N' + this.n);              // the next line expected is n + 1
    item.num = ++this.n; return gcodeLine(item.num, item.cmd);
  }
  _pump() {
    if (!this.ready || this.closed) return;
    if (this.resendFrom !== null) {
      if (this.inflight.length) return;                 // every line in flight still gets its own "ok"
      const from = this.resendFrom; this.resendFrom = null;
      this.replay = [];
      // the firmware asks for a line it had already accepted, or one we no longer have: renumber, never replay old lines
      if (from <= this.n && (from <= (this.ackedN || 0) || !this.hist.has(from))) this.q.unshift({ cmd: 'M110', resync: true });
      else for (let k = from; k <= this.n; k++) if (this.hist.has(k)) this.replay.push(this.hist.get(k));
    }
    for (;;) {
      let item, text;
      if (this.replay && this.replay.length) { item = this.replay[0]; text = item.text; }
      else {
        this.replay = null;
        item = this.q[0] || this._jobItem();
        if (!item) return;
        text = null;
      }
      const len = (text || item.cmd).length + 12;
      const busy = this.inflight.reduce((a, x) => a + x.len, 0);
      if (this.inflight.length && (this.pingPong || busy + len > this.budget)) return;
      if (text) this.replay.shift();
      else {
        if (item === this.q[0]) this.q.shift();
        else { this.job.next++; if (/^G91\b/i.test(item.cmd)) this.job.rel = true; else if (/^G90\b/i.test(item.cmd)) this.job.rel = false; }
        text = this._line(item);
        item.text = text;
        if (item.num) { this.hist.set(item.num, item); if (this.hist.size > 400) this.hist.delete(this.hist.keys().next().value); }
      }
      item.len = text.length + 1;
      this.inflight.push(item);
      this.lastTx = Date.now();
      this.io.write(text + '\n').catch(e => this._fail('Could not write to the printer: ' + e.message));
    }
  }
  _jobItem() {
    const J = this.job;
    if (!J || J.done || J.paused || J.stopping || J.next >= J.cmds.length) return null;   // a stopped or failed print sends nothing more
    return { cmd: J.cmds[J.next], job: J, index: J.next };
  }
  _rx(line) {
    this.lastRx = Date.now();
    this.rx.push(line); if (this.rx.length > 200) this.rx.shift();
    const T = parseTemps(line);
    if (T) { this.temp = T.t; if (T.target !== null) this.target = T.target; this._emit('temp', T); }
    if (/^start\b/i.test(line)) {
      this._gotStart = true;
      if (this.ready) {
        // the firmware restarted (reset, emergency stop, power): any print is over, and line numbers start again
        if (this.job && !this.job.done) this._fail('The printer restarted; the print was stopped.');
        for (const it of this.inflight) if (it.reject && !it.job) it.reject(new Error('The printer restarted.'));
        this.inflight = []; this.replay = null; this.resendFrom = null; this.hist.clear(); this.ackedN = 0;
        if (this.numbered) this.q.unshift({ cmd: 'M110 N0', isM110: true });
        this._pump();
      }
      return;
    }
    const rs = /^(?:Resend|rs)[:\s]\s*N?(\d+)/i.exec(line);
    if (rs) { const n = +rs[1]; this.resends++; this.resendFrom = this.resendFrom === null ? n : Math.min(this.resendFrom, n); return; }
    if (/^ok\b/i.test(line)) {
      const it = this.inflight.shift();
      if (it) {
        if (it.timer) clearTimeout(it.timer);
        if (it.num && !(this.resendFrom !== null && it.num >= this.resendFrom)) this.ackedN = Math.max(this.ackedN || 0, it.num);
        if (it.resolve && !(this.resendFrom !== null && it.num >= this.resendFrom)) it.resolve(line);
        if (it.job && !(this.resendFrom !== null && it.num >= this.resendFrom)) {
          const J = it.job; J.acked = Math.max(J.acked, it.index + 1);
          if (J.acked >= J.cmds.length && !J.done) { J.done = true; J.t1 = Date.now(); this._emit('done', J); }
          else if (Date.now() - (J.lastEmit || 0) > 150) { J.lastEmit = Date.now(); this._emit('progress', J); }
        }
      }
      this._pump();
      return;
    }
    if (/^Error:/i.test(line)) {
      this.errors++;
      if (/halted|kill|stopped/i.test(line)) this._fail('The printer stopped: ' + line.replace(/^Error:/i, ''));
      this._emit('message', line);
      return;
    }
    if (/^(echo|\/\/)/i.test(line)) this._emit('message', line);
  }
  _watchdog() {
    if (this.closed || !this.ready) return;
    // temperature every 3 s (not while the firmware is busy heating: it reports by itself then)
    const heating = this.inflight.some(i => /^M1[09]9\b/i.test(i.cmd));
    if (!heating && Date.now() - (this.lastPoll || 0) > 3000 && !this.q.some(i => i.cmd === 'M105') && !this.inflight.some(i => i.cmd === 'M105')) {
      this.lastPoll = Date.now(); this.send('M105').catch(() => {});
    }
    if (!this.inflight.length || /^(M109|M190|G28|G4|M400)\b/i.test(this.inflight[0].cmd)) return;
    // a lost "ok" would stall everything: after 20 s of silence ask again for the line in flight (line numbers make
    // this safe: the firmware skips a line it already has and asks for the next one)
    if (Date.now() - this.lastRx > this.stallMs && Date.now() - this.lastTx > this.stallMs && this.numbered && this.inflight[0].num) {
      const n = this.inflight[0].num;
      this.inflight = []; this.resendFrom = n; this._emit('message', `No answer for ${Math.round(this.stallMs / 1000)} s — sending again from line ${n}`);
      this.lastTx = Date.now(); this._pump();
    }
  }
  _fail(msg) {
    const J = this.job;
    if (J && !J.done) { J.done = true; J.error = msg; this._emit('error', J); }
    for (const it of this.q.splice(0)) { if (it.timer) clearTimeout(it.timer); if (it.reject) it.reject(new Error(msg)); }
  }
  // Print job: G-code text. Comments are not sent.
  start(gcode, meta = {}) {
    if (this.job && !this.job.done) throw new Error('A print is already running.');
    const { cmds, src } = gcodeCommands(gcode);
    this.job = { cmds, src, next: 0, acked: 0, paused: false, t0: Date.now(), meta, done: false, pausedFor: 0 };
    this._emit('started', this.job);
    this._pump();
    return this.job;
  }
  // Pause: stop feeding the print, then (after the moves already sent) pull the filament back 2 mm and lift 5 mm.
  async pause() {
    const J = this.job; if (!J || J.done || J.paused) return;
    J.paused = true; J.pauseT = Date.now(); this._emit('paused', J);
    for (const c of ['G91', 'G1 E-2 F1800', 'G1 Z5 F600', J.rel ? 'G91' : 'G90']) await this.send(c);
  }
  async resume() {
    const J = this.job; if (!J || J.done || !J.paused) return;
    for (const c of ['G91', 'G1 Z-5 F600', 'G1 E2 F1800', J.rel ? 'G91' : 'G90']) await this.send(c);
    J.pausedFor += Date.now() - J.pauseT; J.paused = false; this._emit('resumed', J); this._pump();
  }
  // Stop the print: nothing more of it is sent; heater off, nozzle lifted 10 mm, fan off.
  async cancel() {
    const J = this.job; if (!J || J.done) return;
    J.stopping = true; J.done = true; J.cancelled = true; this._emit('stopped', J);
    for (const c of ['M104 S0', 'G91', 'G1 Z10 F600', 'G90', 'M107']) await this.send(c).catch(() => {});
  }
  // Emergency: M112 straight away, then a reset pulse, which halts the firmware.
  async emergency() {
    if (this.job && !this.job.done) { this.job.done = true; this.job.error = 'Emergency stop'; this._emit('error', this.job); }
    this.q = []; this.inflight = [];
    try { await this.io.write('M112\n'); } catch (e) {}
    try { await this.io.reset(); } catch (e) {}
  }
  async close() { clearInterval(this.watch); this.closed = true; try { await this.io.close(); } catch (e) {} }
}
