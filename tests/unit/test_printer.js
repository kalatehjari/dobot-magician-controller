// Unit tests for the G-code link and the simulated printer (node tests/unit/test_printer.js)
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { console, Math, Array, Object, Number, JSON, String, parseFloat, parseInt, isNaN, isFinite, Infinity, NaN, Error, RegExp,
  Float32Array, Float64Array, Uint32Array, Uint8Array, Int32Array, Map, Set, TextDecoder, TextEncoder, DataView, ArrayBuffer, Date, Promise,
  setTimeout, clearTimeout, setInterval, clearInterval, navigator: { userAgent: 'node', appName: 'Netscape' } };
ctx.self = ctx;
vm.createContext(ctx);
for (const f of ['part48_clipper.js', 'part49_slicer.js', 'part50_printer.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };

E(`
// a small print: the calibration cube at 30 % (6 mm), a few hundred lines
var SMALL = slicePrintSync(meshPlace(sampleMesh('cube'), { s: 0.3 }), { skirtMin: 20 }, { name: 'tiny cube' });
var JOB = gcodeCommands(SMALL.gcode).cmds;
var until = (f, ms = 20000) => new Promise((res, rej) => { const t0 = Date.now(); const k = setInterval(() => { if (f()) { clearInterval(k); res(true); } else if (Date.now() - t0 > ms) { clearInterval(k); rej(new Error('timeout')); } }, 5); });
var printWith = async (simOpts, linkOpts, during) => {
  const sim = new SimPrinter({ speed: 4000, ...simOpts }), link = new GcodeLink(sim, linkOpts), ev = [];
  link.onEvent = (type) => ev.push(type);
  await link.connect();
  const J = link.start(SMALL.gcode);
  if (during) await during(link, sim, J);
  await until(() => J.done, 60000);
  await until(() => sim.queue.length === 0 && !sim.block, 20000);
  const out = { sim, link, J, ev };
  await link.close();
  return out;
};
// what the printer carried out, minus the link's own polling and numbering
var jobTrace = sim => sim.trace.filter(c => c !== 'M105' && !/^M110/.test(c));
`);

(async () => {
  /* ---------- line format ---------- */
  const f = E(`[gcodeLine(1, 'G1 X10'), gcodeChecksum('N1 G1 X10'), gcodeCommands('; hi\\nG1 X1 ; move\\n\\n  M105  \\n').cmds.join('|'), JSON.stringify(parseTemps('ok T:199.8 /200.0 B:0.0 /0.0 @:127')), JSON.stringify(parseTemps(' T:25.3 E:0 W:?'))]`);
  const xor = [...'N1 G1 X10'].reduce((a, ch) => a ^ ch.charCodeAt(0), 0);
  t('lines get a number and an XOR checksum, as Marlin expects', f[0] === 'N1 G1 X10*' + xor && f[1] === xor, f[0]);
  t('comments and blank lines are not sent', f[2] === 'G1 X1|M105');
  t('temperatures are read from "ok" replies and from heating reports', f[3] === '{"t":199.8,"target":200}' && f[4] === '{"t":25.3,"target":null}');

  /* ---------- connecting ---------- */
  const c = await E(`(async () => {
    const sim = new SimPrinter({ speed: 2000 }), link = new GcodeLink(sim);
    await link.connect();
    const r = { numbered: link.numbered, temp: link.temp, lastN: sim.lastN, first: sim.trace.slice(0, 2) };
    await link.close(); return r;
  })()`);
  t('connect: restarts the firmware, renumbers lines (M110) and reads the temperature', c.numbered && c.temp !== null && c.first[0] === 'M110 N0' && c.first[1] === 'M105', JSON.stringify(c));

  /* ---------- a whole print ---------- */
  const p = await E(`(async () => {
    const { sim, link, J, ev } = await printWith({}, {});
    const tr = jobTrace(sim), same = tr.length === JOB.length && tr.every((c, i) => c === JOB[i]);
    const firstExt = sim.log.findIndex(m => m.ext), tempAtFirst = firstExt >= 0 ? sim.log[firstExt].t : 0;
    return { same, n: tr.length, want: JOB.length, cold: sim.coldBlocked, tempAtFirst, target: sim.target, fan: sim.fan, outside: sim.outside, acked: J.acked, ev: ev.join(','), resends: link.resends };
  })()`);
  t('the printer carries out every line of the G-code, once and in order', p.same, `${p.n} of ${p.want} lines`);
  t('it is hot before the first extrusion; nothing is extruded cold', p.cold === 0 && p.tempAtFirst > 195, p.tempAtFirst.toFixed(1) + ' °C');
  t('at the end the heater and fan are off', p.target === 0 && p.fan === 0);
  t('no move leaves the printable area', p.outside === 0);
  t('events: started, progress, done', /started.*progress.*done/.test(p.ev) && p.resends === 0, p.ev.slice(0, 60));

  /* ---------- damaged lines are sent again ---------- */
  const r = await E(`(async () => {
    const a = await printWith({ faultEvery: 7 }, {});
    const b = await printWith({ faultEvery: 5 }, { pingPong: false, budget: 63 });
    const ok = o => { const tr = jobTrace(o.sim); return tr.length === JOB.length && tr.every((c, i) => c === JOB[i]); };
    return { a: ok(a), ar: a.link.resends, b: ok(b), br: b.link.resends, bErr: b.link.errors };
  })()`);
  t('every 7th line damaged: each is asked for and sent again, nothing lost or doubled', r.a && r.ar > 20, r.ar + ' resends');
  t('streaming into the 63-byte buffer with every 5th line damaged: still exact', r.b && r.br > 20, r.br + ' resends');

  /* ---------- a lost "ok" ---------- */
  const w = await E(`(async () => {
    const o = await printWith({ dropOkAt: 40 }, { stallMs: 400 });
    const tr = jobTrace(o.sim);
    return { same: tr.length === JOB.length && tr.every((c, i) => c === JOB[i]), done: o.J.done && !o.J.error };
  })()`);
  t('a lost "ok": after a quiet spell the line is sent again; the firmware skips the copy', w.same && w.done);

  /* ---------- pause, resume, stop, emergency ---------- */
  const pr = await E(`(async () => {
    let zPaused = null, zBefore = null, parkSeen = false;
    const o = await printWith({}, {}, async (link, sim, J) => {
      await until(() => J.acked > JOB.length / 2);
      await link.pause();
      await until(() => sim.queue.length === 0);
      const L = sim.log;                                    // the park lift is the last move; the move before it is where the nozzle was
      zBefore = L[L.length - 2].z;
      zPaused = L[L.length - 1].z;
      parkSeen = sim.trace.filter(c => c !== 'M105').slice(-4).join('|');
      await link.resume();
    });
    const tr = jobTrace(o.sim), park = ['G91', 'G1 E-2 F1800', 'G1 Z5 F600', 'G90'], unpark = ['G91', 'G1 Z-5 F600', 'G1 E2 F1800', 'G90'];
    const k = tr.indexOf('G1 E-2 F1800') - 1;
    const rest = tr.slice(0, k).concat(tr.slice(k + 8));
    const same = rest.length === JOB.length && rest.every((c, i) => c === JOB[i]);
    return { lift: zPaused - zBefore, parkSeen, same, unpark: tr.slice(k + 4, k + 8).join('|') === unpark.join('|') };
  })()`);
  t('pause: the nozzle backs the filament off and lifts 5 mm', Math.abs(pr.lift - 5) < 1e-6 && pr.parkSeen === 'G91|G1 E-2 F1800|G1 Z5 F600|G90', `lift ${pr.lift}`);
  t('resume: back down, filament forward, and the print carries on exactly', pr.same && pr.unpark);
  const st = await E(`(async () => {
    const o = await printWith({}, {}, async (link, sim, J) => { await until(() => J.acked > 60); await link.cancel(); });
    return { cancelled: o.J.cancelled, tail: o.sim.trace.filter(c => c !== 'M105').slice(-5).join('|'), sent: o.J.next, total: JOB.length, target: o.sim.target };
  })()`);
  t('stop: nothing more of the print is sent; heater off, lift 10 mm, fan off', st.cancelled && st.tail === 'M104 S0|G91|G1 Z10 F600|G90|M107' && st.sent < st.total && st.target === 0, st.tail);
  const em = await E(`(async () => {
    const sim = new SimPrinter({ speed: 4000 }), link = new GcodeLink(sim); await link.connect();
    const J = link.start(SMALL.gcode); await until(() => J.acked > 30);
    await link.emergency();
    await until(() => J.done);
    await until(() => sim.boots >= 2 && sim.booting <= 0);
    await sleepMs(300);
    const after = sim.trace.slice(sim.trace.indexOf('M112') + 1);
    await link.send('M104 S0', 3000);
    const r = { err: J.error, killed: sim.trace.includes('M112') && sim.boots >= 2, after: after.join('|'), last: sim.trace[sim.trace.length - 1] };
    await link.close(); return r;
  })()`);
  t('emergency stop: M112 and a reset pulse; the job ends with an error', em.err === 'Emergency stop' && em.killed, JSON.stringify(em));
  t('after it nothing more of the print is sent; the link renumbers and commands work again', em.after === 'M110 N0' && em.last === 'M104 S0', em.after);
  const rs = await E(`(async () => {
    const sim = new SimPrinter({ speed: 4000 }), link = new GcodeLink(sim); await link.connect();
    const J = link.start(SMALL.gcode); await until(() => J.acked > 30);
    sim.reset();
    await until(() => J.done, 5000);
    const r = { err: J.error }; await link.close(); return r;
  })()`);
  t('if the printer restarts during a print, the print is stopped and reported', /restarted/.test(rs.err || ''), rs.err);
  const nf = await E(`(async () => {
    // a port that never answers
    const io = { onLine: null, onClose: null, open: async () => {}, reset: async () => {}, write: async () => {}, close: async () => {} };
    const link = new GcodeLink(io); link.connect = link.connect.bind(link);
    let msg = ''; const t0 = Date.now();
    try { await link.connect(); } catch (e) { msg = e.message; }
    await link.close(); return { msg, s: (Date.now() - t0) / 1000 };
  })()`);
  t('no answer at all: connecting fails with a hint about the 3D-printer firmware', /3D-printer firmware/.test(nf.msg), nf.msg + ` (${nf.s.toFixed(1)} s)`);

  console.log(fails ? `\n${fails} FAILED` : '\nall printer-link tests passed');
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
