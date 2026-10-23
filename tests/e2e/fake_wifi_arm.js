// A pretend Magician on Wi-Fi for the browser test: the app's own simulator (SimIO) answering the
// Dobot protocol as UDP messages, like the Wi-Fi module does on port 8899.
// node tests/e2e/fake_wifi_arm.js [port] [dropEvery]   (dropEvery: ignore every n-th message, to test resends)
const fs = require('fs'), vm = require('vm'), path = require('path'), dgram = require('dgram');
const port = +(process.argv[2] || 8899), dropEvery = +(process.argv[3] || 0);
const ctx = { console, Math, Float32Array, Float64Array, Int32Array, Uint8Array, Uint32Array, Array, Object, Number, JSON, Infinity, NaN, isFinite, Set, Map, Promise, DataView, setTimeout, Date, Error };
ctx.S = { limits: { minR: 170, maxR: 300, thMin: -87, thMax: 87, zMin: -80, zMax: 120, zUp: -60, zDown: -75 }, speed: { live: 100, accel: 100 }, gen: 0, model: null };
ctx.DEBUG = { frames: false }; ctx.log = () => {};
vm.createContext(ctx);
for (const f of ['part0_alarms.js', 'part1_protocol.js', 'part31_kinematics.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', '..', 'src', f), 'utf8'), ctx, { filename: f });
const sim = vm.runInContext('new SimIO()', ctx), sock = dgram.createSocket('udp4');
let n = 0, got = 0, ids = {};
sock.on('message', async (msg, rinfo) => {
  n++;
  if (dropEvery && n % dropEvery === 0) return;               // lost on the way
  const { frames } = ctx.parseFrames(new Uint8Array(msg));
  for (const f of frames) {
    got++; ids[f.id] = (ids[f.id] || 0) + 1;
    const reply = await sim.exchange(ctx.encodeFrame(f.id, f.ctrl, f.params));
    sock.send(Buffer.from(ctx.encodeFrame(reply.id, reply.ctrl, reply.params)), rinfo.port, rinfo.address);
  }
});
sock.bind(port, '127.0.0.1', () => console.log('fake Wi-Fi arm on udp 127.0.0.1:' + port));
setInterval(() => { try { fs.writeFileSync(process.env.FAKE_ARM_STATS || '/dev/null', JSON.stringify({ n, got, ids, ptp: sim.st.ptpCount, cp: sim.st.cpCount, x: sim.st.x, y: sim.st.y, z: sim.st.z })); } catch (e) {} }, 200);
