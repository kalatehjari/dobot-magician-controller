// Unit tests: Bluetooth LE link (with a pretend module), Wi-Fi module setup frames, bridge links
// (run: node tests/unit/test_wireless.js)
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { console, Math, Float32Array, Float64Array, Int32Array, Uint8Array, Uint32Array, Array, Object, Number, JSON, String, Infinity, NaN, isFinite, Set, Map, Promise, DataView,
  ArrayBuffer, setTimeout, clearTimeout, Date, Error, TextEncoder, TextDecoder };
ctx.S = { limits: { minR: 170, maxR: 300, thMin: -87, thMax: 87, zMin: -80, zMax: 120, zUp: -60, zDown: -75 }, speed: { live: 100, accel: 100 }, gen: 0, model: null };
ctx.DEBUG = { frames: false }; ctx.log = () => {}; ctx.setConnected = () => {};
ctx.document = { getElementById: () => null };
vm.createContext(ctx);
const src = f => fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8');
for (const f of ['part0_alarms.js', 'part1_protocol.js', 'part31_kinematics.js']) vm.runInContext(src(f), ctx, { filename: f });
// part 56 without its page wiring (the lines after "connection choices")
vm.runInContext(src('part56_wireless.js').split('/* ---------- connection choices ---------- */')[0], ctx, { filename: 'part56_wireless.js' });
const E = c => vm.runInContext(c, ctx);
let fails = 0;
const t = (n, c, x = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n + (x ? '  ' + x : '')); if (!c) fails++; };

E(`
// a pretend Bluetooth module: takes writes in pieces, answers with the simulator, in pieces of 7 bytes
function fakeBle(opts = {}) {
  const sim = new SimIO(), writes = [], listeners = {}, rxL = [];
  let buf = new Uint8Array(0), notifying = false;
  const rx = { startNotifications: async () => { notifying = true; }, stopNotifications: async () => {}, addEventListener: (e, f) => rxL.push(f) };
  const deliver = bytes => { for (let i = 0; i < bytes.length; i += 7) { const v = bytes.slice(i, i + 7); const dv = new DataView(v.buffer); for (const f of rxL) f({ target: { value: dv } }); } };
  const onWrite = async part => {
    writes.push(part.length);
    const m = new Uint8Array(buf.length + part.length); m.set(buf); m.set(part, buf.length);
    const { frames, rest } = parseFrames(m); buf = rest;
    for (const f of frames) { const r = await sim.exchange(encodeFrame(f.id, f.ctrl, f.params)); if (notifying) setTimeout(() => deliver(encodeFrame(r.id, r.ctrl, r.params)), 2); }
  };
  const tx = { properties: { writeWithoutResponse: !opts.withResponse, write: true },
    writeValueWithoutResponse: async v => onWrite(new Uint8Array(v)), writeValueWithResponse: async v => onWrite(new Uint8Array(v)) };
  const svc = { getCharacteristic: async u => (u === DOBOT_BLE.notify ? rx : u === DOBOT_BLE.write ? tx : Promise.reject(new Error('no such characteristic'))) };
  const device = { name: 'Dobot-BLE', addEventListener: (e, f) => { listeners[e] = f; },
    gatt: { connect: async () => ({ getPrimaryService: async u => (u === DOBOT_BLE.service ? svc : Promise.reject(new Error('no such service'))) }), disconnect: () => listeners.gattserverdisconnected && listeners.gattserverdisconnected() } };
  return { device, sim, writes };
}
`);

(async () => {
  const b = await E(`(async () => {
    const f = fakeBle(), io = new BleIO(f.device, 20); await io.open();
    const dev = new Dobot(io);
    const p0 = await dev.pose();
    const idx = await dev.ptp(220, 30, 20, 0, 2);
    const many = await Promise.all([dev.queueIndex(), dev.pose(), dev.alarms()]);
    const p1 = await dev.pose();
    return { p0x: p0.x, idx, n: many.length, x: p1.x, y: p1.y, maxPiece: Math.max(...f.writes), pieces: f.writes.length, ptp: f.sim.st.ptpCount };
  })()`);
  t('Bluetooth: pose, a move and several requests at once work through the module', b.ptp === 1 && Math.abs(b.x - 220) < 0.01 && Math.abs(b.y - 30) < 0.01 && b.n === 3, JSON.stringify({ x: b.x, y: b.y }));
  t('Bluetooth: frames go out in pieces of at most 20 bytes, replies come back in pieces', b.maxPiece <= 20 && b.pieces > 6, `${b.pieces} pieces, largest ${b.maxPiece} bytes`);
  const b2 = await E(`(async () => { const f = fakeBle({ withResponse: true }), io = new BleIO(f.device, 20); await io.open(); const dev = new Dobot(io); await dev.ptp(230, -10, 10, 0, 2); const p = await dev.pose(); return { x: p.x, noResp: io.noResp }; })()`);
  t('Bluetooth: a module that only takes writes with a response works too', Math.abs(b2.x - 230) < 0.01 && b2.noResp === false);
  const b3 = await E(`(async () => { const f = fakeBle(), io = new BleIO(f.device, 20); await io.open(); const dev = new Dobot(io); await dev.pose(); f.device.gatt.disconnect(); let msg = ''; try { await dev.pose(); } catch (e) { msg = e.message; } return msg; })()`);
  t('Bluetooth: when the link drops, requests fail instead of hanging', /closed|lost/i.test(b3), b3);
  const b4 = await E(`(async () => { const f = fakeBle(); f.device.gatt.connect = async () => ({ getPrimaryService: async () => { throw new Error('No Services matching UUID'); } }); const io = new BleIO(f.device); try { await io.open(); return 'opened'; } catch (e) { return e.message; } })()`);
  t('Bluetooth: a device without the Magician service is reported', /UUID/.test(b4), b4);

  /* ---------- Wi-Fi module setup frames (Dobot protocol 150–157) ---------- */
  const w = E(`(() => {
    const hex = a => Array.from(a, v => v.toString(16).padStart(2, '0')).join(' ');
    const dh = wifiSetupFrames({ ssid: 'home', password: 'pw1', dhcp: true }).map(([id, c, p]) => hex(encodeFrame(id, c, p)));
    const st = wifiSetupFrames({ ssid: 'lab', password: 'x', dhcp: false, ip: '192.168.1.50', netmask: '255.255.255.0', gateway: '192.168.1.1', dns: '8.8.8.8' }).map(([id, c, p]) => [id, c, Array.from(p)]);
    return { dh, st };
  })()`);
  // header AA AA, length = 2 + params, id, ctrl (rw 1, not queued), params, checksum = -(sum of id..params) & 255
  t('Wi-Fi on: AA AA 03 96 01 01 68', w.dh[0] === 'aa aa 03 96 01 01 68', w.dh[0]);
  t('network name and password as text ending in 0 (151, 152)', w.dh[1] === 'aa aa 07 97 01 68 6f 6d 65 00 bf' && w.dh[2] === 'aa aa 06 98 01 70 77 31 00 4f', w.dh[1] + ' | ' + w.dh[2]);
  t('address from the router: 153 with dhcp = 1', w.dh[3] === 'aa aa 07 99 01 01 00 00 00 00 65' && w.dh.length === 4, w.dh[3]);
  t('fixed address: 153 dhcp 0 + 4 bytes, then netmask 154, gateway 155, DNS 156',
    JSON.stringify(w.st.slice(3)) === JSON.stringify([[153, 1, [0, 192, 168, 1, 50]], [154, 1, [255, 255, 255, 0]], [155, 1, [192, 168, 1, 1]], [156, 1, [8, 8, 8, 8]]]));
  const rs = await E(`(async () => {
    // a pretend arm answering the Wi-Fi reads
    const dev = { call: async (id, ctrl) => ({ params: { 150: new Uint8Array([1]), 151: new TextEncoder().encode('home\\0'), 153: new Uint8Array([1, 192, 168, 1, 77]), 157: new Uint8Array([1]) }[id] }) };
    return await wifiReadStatus(dev);
  })()`);
  t('reading the module: on, network, address from the router, connected', rs.enabled && rs.ssid === 'home' && rs.dhcp && rs.ip === '192.168.1.77' && rs.connected, JSON.stringify(rs));
  t('addresses are checked', E(`[isIPv4('192.168.1.50'), isIPv4('192.168.1.256'), isIPv4('10.0.0'), isIPv4(' 10.0.0.1 ')].join()`) === 'true,false,false,true');

  /* ---------- a lost message is sent again (Wi-Fi) ---------- */
  const lo = await E(`(async () => {
    class Lossy extends FrameLink { constructor() { super(60); this.sim = new SimIO(); this.n = 0; }
      async _send(frame) { this.n++; if (this.n % 3 === 0) return; const f = parseFrames(frame).frames[0]; const r = await this.sim.exchange(encodeFrame(f.id, f.ctrl, f.params)); setTimeout(() => this._onBytes(encodeFrame(r.id, r.ctrl, r.params)), 1); }
      exchange(frame) { return super.exchange(frame, 3); } }
    const io = new Lossy(), dev = new Dobot(io);
    let ok = 0; for (let i = 0; i < 12; i++) { await dev.pose(); ok++; }
    await dev.ptp(240, 20, 0, 0, 2); const p = await dev.pose();
    return { ok, sent: io.n, x: p.x };
  })()`);
  t('Wi-Fi: with every third message lost, each request is sent again until it is answered', lo.ok === 12 && Math.abs(lo.x - 240) < 0.01 && lo.sent > 14, `${lo.sent} messages for 14 requests`);

  console.log(fails ? `\n${fails} FAILED` : '\nall wireless tests passed');
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
