/* ===================== WIRELESS: BLUETOOTH AND WI-FI MODULES ===================== */
// The Magician's communication add-ons plug into the 10-pin port on the back of the base (one at a
// time, arm off while swapping). "Wireless 1" is Bluetooth LE: the same command frames go to
// characteristic …CDD2 and replies come back on …CDD1 (service 0003CDD0-0000-1000-8000-00805F9B0131,
// Dobot Communication Protocol). "Wireless 2" is Wi-Fi: the same frames as UDP messages on port 8899
// — a web page cannot send UDP, so a small bridge program on the computer passes them on (WebSocket
// ↔ UDP; tools/wifi-bridge/magician_wifi_bridge.py, also downloadable from the app). The Wi-Fi
// module's network settings are sent over USB once (commands 150–157).

const DOBOT_BLE = {
  service: '0003cdd0-0000-1000-8000-00805f9b0131',
  notify: '0003cdd1-0000-1000-8000-00805f9b0131',     // replies from the arm
  write: '0003cdd2-0000-1000-8000-00805f9b0131',      // commands to the arm
};
const WIFI_BRIDGE_PY = "%%WIFI_BRIDGE_PY%%";           // build.py puts the bridge program here
const $wl = id => document.getElementById(id);

// Frames come back in pieces (Bluetooth notifications, UDP datagrams): collect bytes, cut frames out,
// hand each reply to the request waiting for that command ID.
class FrameLink {
  constructor(timeoutMs) { this.buf = new Uint8Array(0); this.waiters = []; this.closed = false; this.timeoutMs = timeoutMs; }
  _onBytes(value) {
    const merged = new Uint8Array(this.buf.length + value.length);
    merged.set(this.buf); merged.set(value, this.buf.length);
    const { frames, rest } = parseFrames(merged);
    this.buf = rest.length > 4096 ? new Uint8Array(0) : rest;
    for (const f of frames) {
      const wi = this.waiters.findIndex(w => w.id === f.id);
      if (wi >= 0) { const [w] = this.waiters.splice(wi, 1); clearTimeout(w.timer); w.resolve(f); }
      else if (DEBUG.frames) log('<< ' + hexOf(encodeFrame(f.id, f.ctrl, f.params)), 'dim');
    }
  }
  _wait(id, ms) {
    let w;
    const p = new Promise((resolve, reject) => {
      w = { id, resolve, reject, timer: setTimeout(() => { this.waiters = this.waiters.filter(x => x !== w); reject(new Error('No reply from robot (command ' + id + ')')); }, ms) };
      this.waiters.push(w);
    });
    return { p, w };
  }
  // One request: sent, then its reply awaited; tries `tries` times (a lost message is sent again —
  // every move the app sends is to an absolute position, so a repeat is harmless).
  async exchange(frame, tries = 1) {
    const id = frame[3];
    for (let k = 0; ; k++) {
      if (this.closed) throw new Error('The wireless link is closed');
      const { p, w } = this._wait(id, this.timeoutMs);
      try { await this._send(frame); }
      catch (e) { clearTimeout(w.timer); this.waiters = this.waiters.filter(x => x !== w); throw e; }
      try { return await p; }
      catch (e) { if (k + 1 >= tries) throw e; }
    }
  }
}

/* ---------- Bluetooth LE (Web Bluetooth, Chrome / Edge) ---------- */
class BleIO extends FrameLink {
  constructor(device, chunk = 20) { super(3000); this.device = device; this.chunk = chunk; this.wchain = Promise.resolve(); }
  async open() {
    this.device.addEventListener('gattserverdisconnected', () => {
      if (this.closed) return;
      this.closed = true;
      for (const w of this.waiters.splice(0)) { clearTimeout(w.timer); w.reject(new Error('Bluetooth link lost')); }
      log('The Bluetooth link to the arm was lost.', 'err');
      S.dev = null; setConnected(false);
    });
    const server = await this.device.gatt.connect();
    const svc = await server.getPrimaryService(DOBOT_BLE.service);
    this.rx = await svc.getCharacteristic(DOBOT_BLE.notify);
    this.tx = await svc.getCharacteristic(DOBOT_BLE.write);
    this.rx.addEventListener('characteristicvaluechanged', ev => {
      const v = ev.target.value;
      this._onBytes(new Uint8Array(v.buffer, v.byteOffset, v.byteLength).slice());
    });
    await this.rx.startNotifications();
    const pr = this.tx.properties || {};
    this.noResp = !!pr.writeWithoutResponse;                     // faster when the module allows it
  }
  // Frames go out in pieces of `chunk` bytes (the smallest Bluetooth LE packet holds 20), in order.
  _send(frame) {
    const job = this.wchain.then(async () => {
      for (let i = 0; i < frame.length; i += this.chunk) {
        const part = frame.slice(i, i + this.chunk);
        if (this.noResp && this.tx.writeValueWithoutResponse) await this.tx.writeValueWithoutResponse(part);
        else if (this.tx.writeValueWithResponse) await this.tx.writeValueWithResponse(part);
        else await this.tx.writeValue(part);
      }
    });
    this.wchain = job.catch(() => {});
    return job;
  }
  exchange(frame) { return super.exchange(frame, 1); }
  async close() {
    this.closed = true;
    try { await this.rx.stopNotifications(); } catch (e) {}
    try { this.device.gatt.disconnect(); } catch (e) {}
  }
}

async function connectBle() {
  if (!navigator.bluetooth) throw new Error('Bluetooth is not available in this browser. Use Google Chrome or Microsoft Edge, and on a Mac allow Bluetooth for the browser (System Settings → Privacy & Security → Bluetooth).');
  // The module may not advertise the service, so every device is listed; the Magician's module is
  // usually the one named after Dobot.
  const device = await navigator.bluetooth.requestDevice({ acceptAllDevices: true, optionalServices: [DOBOT_BLE.service] });
  const io = new BleIO(device, Math.max(20, parseInt(($wl('ble-chunk') || {}).value, 10) || 20));
  try { await io.open(); }
  catch (e) { try { device.gatt.disconnect(); } catch (x) {} throw new Error(`${device.name || 'That device'} has no Magician Bluetooth service (${e.message}). Is the Wireless 1 module plugged in and the arm on?`); }
  S.dev = new Dobot(io);
  S.sim = false; S.link = 'Bluetooth';
}

/* ---------- Wi-Fi through the bridge (WebSocket ↔ UDP 8899) ---------- */
class BridgeIO extends FrameLink {
  constructor(url) { super(1200); this.url = url; }
  open() {
    return new Promise((resolve, reject) => {
      let ws;
      try { ws = new WebSocket(this.url); } catch (e) { reject(e); return; }
      ws.binaryType = 'arraybuffer';
      const t = setTimeout(() => { try { ws.close(); } catch (e) {} reject(new Error('the Wi-Fi bridge is not running')); }, 4000);
      ws.onopen = () => { clearTimeout(t); this.ws = ws; resolve(); };
      ws.onerror = () => { clearTimeout(t); reject(new Error('the Wi-Fi bridge is not running')); };
      ws.onmessage = ev => { if (ev.data instanceof ArrayBuffer) this._onBytes(new Uint8Array(ev.data)); };
      ws.onclose = () => {
        if (this.closed) return;
        this.closed = true;
        for (const w of this.waiters.splice(0)) { clearTimeout(w.timer); w.reject(new Error('Wi-Fi link lost')); }
        if (this.ws) { log('The Wi-Fi bridge closed the link (is the bridge still running?).', 'err'); S.dev = null; setConnected(false); }
      };
    });
  }
  async _send(frame) { if (!this.ws || this.ws.readyState !== 1) throw new Error('Wi-Fi link lost'); this.ws.send(frame); }
  exchange(frame) { return super.exchange(frame, 3); }
  async close() { this.closed = true; try { this.ws.close(); } catch (e) {} }
}

function wifiSettings() {
  let d = {};
  try { d = JSON.parse(localStorage.getItem('magician-wifi') || '{}') || {}; } catch (e) {}
  return d;
}
function wifiSaveSettings(patch) { try { localStorage.setItem('magician-wifi', JSON.stringify({ ...wifiSettings(), ...patch })); } catch (e) {} }
const isIPv4 = s => /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/.test(String(s || '').trim());

async function connectWifi() {
  const ip = ($wl('wf-armip').value || '').trim(), port = parseInt($wl('wf-bport').value, 10) || 8890;
  if (!isIPv4(ip)) throw new Error('Type the arm\'s Wi-Fi address first (Setup → Wireless, for example 192.168.1.50).');
  wifiSaveSettings({ armIp: ip, bridgePort: port });
  const io = new BridgeIO(`ws://127.0.0.1:${port}/?arm=${encodeURIComponent(ip)}&port=8899`);
  try { await io.open(); }
  catch (e) { throw new Error(`${e.message} — download it (Setup → Wireless → Wi-Fi), start it in Terminal with python3 magician_wifi_bridge.py, then connect again.`); }
  S.dev = new Dobot(io);
  S.sim = false; S.link = 'Wi-Fi';
  try { await S.dev.pose(); }
  catch (e) { await io.close(); S.dev = null; throw new Error(`the bridge is running, but the arm at ${ip} does not answer. Check the address, that the arm is on with the Wi-Fi module, and that it is on the same network.`); }
}

/* ---------- Wi-Fi module settings, sent over USB (Dobot protocol 150–157) ---------- */
const WIFI_CMD = { mode: 150, ssid: 151, password: 152, ip: 153, netmask: 154, gateway: 155, dns: 156, status: 157 };
const ipBytes = s => String(s).trim().split('.').map(n => parseInt(n, 10) & 255);
const cstr = s => { const b = new TextEncoder().encode(String(s)); const o = new Uint8Array(b.length + 1); o.set(b); return o; };
// The frames to set the module up (as [id, ctrl, params]), in order.
function wifiSetupFrames(cfg) {
  const out = [[WIFI_CMD.mode, 1, new Uint8Array([1])], [WIFI_CMD.ssid, 1, cstr(cfg.ssid)], [WIFI_CMD.password, 1, cstr(cfg.password)]];
  const dhcp = cfg.dhcp !== false;
  out.push([WIFI_CMD.ip, 1, new Uint8Array([dhcp ? 1 : 0, ...(dhcp ? [0, 0, 0, 0] : ipBytes(cfg.ip))])]);
  if (!dhcp) {
    out.push([WIFI_CMD.netmask, 1, new Uint8Array(ipBytes(cfg.netmask))]);
    out.push([WIFI_CMD.gateway, 1, new Uint8Array(ipBytes(cfg.gateway))]);
    out.push([WIFI_CMD.dns, 1, new Uint8Array(ipBytes(cfg.dns || cfg.gateway))]);
  }
  return out;
}
const cstrRead = b => new TextDecoder().decode(b.subarray(0, b.indexOf(0) >= 0 ? b.indexOf(0) : b.length));
async function wifiReadStatus(dev) {
  const r = {};
  const get = async id => (await dev.call(id, 0)).params;
  r.enabled = !!(await get(WIFI_CMD.mode))[0];
  r.ssid = cstrRead(await get(WIFI_CMD.ssid));
  const ip = await get(WIFI_CMD.ip);
  r.dhcp = !!ip[0]; r.ip = Array.from(ip.subarray(1, 5)).join('.');
  try { r.connected = !!(await get(WIFI_CMD.status))[0]; } catch (e) { r.connected = null; }
  return r;
}
async function wifiApply() {
  if (!S.dev || S.sim || S.link !== 'USB') return log('Connect the arm over USB first (with the Wi-Fi module plugged in), then send the settings.', 'warn');
  const cfg = { ssid: $wl('wf-ssid').value.trim(), password: $wl('wf-pass').value, dhcp: $wl('wf-dhcp').checked, ip: $wl('wf-ip').value, netmask: $wl('wf-mask').value, gateway: $wl('wf-gw').value, dns: $wl('wf-dns').value };
  if (!cfg.ssid) return log('Type the network name (SSID) first. The module uses 2.4 GHz networks.', 'warn');
  if (!cfg.dhcp && ![cfg.ip, cfg.netmask, cfg.gateway].every(isIPv4)) return log('For a fixed address, fill in the address, netmask and gateway (like 192.168.1.50, 255.255.255.0, 192.168.1.1).', 'warn');
  wifiSaveSettings({ ssid: cfg.ssid, dhcp: cfg.dhcp, ip: cfg.ip, netmask: cfg.netmask, gateway: cfg.gateway, dns: cfg.dns });
  const st = $wl('wf-status');
  try {
    st.textContent = 'Sending the settings…';
    for (const [id, ctrl, params] of wifiSetupFrames(cfg)) await S.dev.call(id, ctrl, params);
    st.textContent = 'Sent. The module is joining the network…';
    log(`Wi-Fi settings sent to the module: network "${cfg.ssid}", ${cfg.dhcp ? 'address from the router (DHCP)' : 'address ' + cfg.ip}.`, 'ok');
    let r = null;
    for (let i = 0; i < 10; i++) { await sleep(1500); r = await wifiReadStatus(S.dev); if (r.connected) break; }
    wifiShow(r);
  } catch (e) { st.textContent = 'Could not send the settings: ' + e.message; log('Wi-Fi setup: ' + e.message, 'err'); }
}
function wifiShow(r) {
  const st = $wl('wf-status');
  if (!r) { st.textContent = 'No answer from the module.'; return; }
  st.textContent = `Wi-Fi ${r.enabled ? 'on' : 'off'} · network "${r.ssid || '—'}" · ${r.connected === null ? 'connection unknown' : r.connected ? 'connected' : 'not connected (yet)'} · address ${r.ip}${r.dhcp ? ' (from the router)' : ''}`;
  if (r.connected && isIPv4(r.ip) && r.ip !== '0.0.0.0') { $wl('wf-armip').value = r.ip; wifiSaveSettings({ armIp: r.ip }); }
}
async function wifiStatus() {
  if (!S.dev || S.sim) return log('Connect the arm over USB first.', 'warn');
  try { wifiShow(await wifiReadStatus(S.dev)); } catch (e) { $wl('wf-status').textContent = 'No Wi-Fi module answers (' + e.message + '). Is it plugged in?'; }
}
function wifiDownloadBridge() {
  const text = WIFI_BRIDGE_PY.startsWith('%%') ? '# The bridge is in the repository: tools/wifi-bridge/magician_wifi_bridge.py\n' : WIFI_BRIDGE_PY;
  downloadText('magician_wifi_bridge.py', text, 'text/x-python');
  log('Saved magician_wifi_bridge.py. Start it in Terminal: python3 ~/Downloads/magician_wifi_bridge.py — then press Connect over Wi-Fi.', 'ok');
}

/* ---------- connection choices ---------- */
function wlInit() {
  const d = wifiSettings();
  if (d.armIp) $wl('wf-armip').value = d.armIp;
  if (d.bridgePort) $wl('wf-bport').value = d.bridgePort;
  if (d.ssid) $wl('wf-ssid').value = d.ssid;
  $wl('wf-dhcp').checked = d.dhcp !== false;
  for (const k of ['ip', 'netmask', 'gateway', 'dns']) if (d[k]) $wl({ ip: 'wf-ip', netmask: 'wf-mask', gateway: 'wf-gw', dns: 'wf-dns' }[k]).value = d[k];
  wlFixed();
  if (!navigator.bluetooth) $wl('ble-note').textContent = 'This browser has no Web Bluetooth — use Google Chrome or Microsoft Edge.';
}
function wlFixed() { $wl('wf-fixed').hidden = $wl('wf-dhcp').checked; }
async function wlConnect(mode) {
  try { $wl('connMenu').hidePopover(); } catch (e) {}
  if (S.dev) await disconnect();
  await connectFlow(mode);
}
$wl('connMenu').addEventListener('beforetoggle', ev => {          // open just under the ▾ button
  if (ev.newState !== 'open') return;
  const r = $wl('btnConnMore').getBoundingClientRect(), m = $wl('connMenu');
  Object.assign(m.style, { position: 'fixed', inset: 'auto', top: `${r.bottom + 4}px`, left: `${Math.max(8, r.right - 230)}px`, width: '230px' });
});
$wl('btnBle').onclick = () => wlConnect('ble');
$wl('btnWifi').onclick = () => wlConnect('wifi');
$wl('btnMenuBle').onclick = () => wlConnect('ble');
$wl('btnMenuWifi').onclick = () => { try { $wl('connMenu').hidePopover(); } catch (e) {} showTab('setup'); $wl('wirelessCard').scrollIntoView({ block: 'start' }); $wl('wf-armip').focus(); };
$wl('btnWfApply').onclick = () => wifiApply();
$wl('btnWfStatus').onclick = () => wifiStatus();
$wl('btnWfBridge').onclick = wifiDownloadBridge;
$wl('wf-dhcp').onchange = wlFixed;
wlInit();
