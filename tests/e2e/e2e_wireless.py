"""Browser test: Wi-Fi connection through the bridge (app → WebSocket → bridge → UDP → a pretend arm),
with lost messages; the bridge refusing other web pages; downloading the bridge; the connection menu.
The pretend arm is the app's own simulator answering UDP (fake_wifi_arm.js, needs Node.js).
Run from anywhere: python3 tests/e2e/e2e_wireless.py"""
import asyncio, base64, json, os, pathlib, shutil, socket, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
PORT, BRIDGE = 8781, 8891
STATS = os.path.join(SRV, 'arm.json')
results = []
def check(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f'  {extra}' if extra else ''), flush=True)

async def wait_for(ev, expr, timeout=20000, step=100):
    t0 = time.time()
    while (time.time() - t0) * 1000 < timeout:
        if await ev(expr): return True
        await asyncio.sleep(step / 1000)
    return False

def arm_stats():
    try: return json.load(open(STATS))
    except Exception: return {}

def start_arm(drop=0):
    env = dict(os.environ, FAKE_ARM_STATS=STATS)
    return subprocess.Popen(['node', str(HERE / 'fake_wifi_arm.js'), '8899', str(drop)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def handshake(origin):
    s = socket.create_connection(('127.0.0.1', BRIDGE), timeout=3)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f'GET /?arm=127.0.0.1 HTTP/1.1\r\nHost: 127.0.0.1:{BRIDGE}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
               f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nOrigin: {origin}\r\n\r\n').encode())
    r = s.recv(200).decode('latin-1'); s.close()
    return r.split('\r\n')[0]

async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '-d', SRV], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    arm = start_arm()
    bridge = subprocess.Popen([sys.executable, str(ROOT / 'tools' / 'wifi-bridge' / 'magician_wifi_bridge.py'), '--port', str(BRIDGE)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    await asyncio.sleep(1.0)
    try:
        check('the bridge refuses other web pages', '403' in handshake('https://evil.example'))
        check('it accepts the app (from a file, localhost or the project website)', all('101' in handshake(o) for o in ('null', 'http://localhost:8000', 'https://kalatehjari.github.io')))
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--no-sandbox'])
            ctx = await b.new_context(viewport={'width': 1280, 'height': 1100}, accept_downloads=True)
            pg = await ctx.new_page(); errors = []
            pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
            pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' and 'bridge' not in m.text.lower() and 'WebSocket connection' not in m.text else None)
            ev = pg.evaluate
            await pg.goto(f'http://localhost:{PORT}/app.html')
            await ev("localStorage.clear()"); await pg.reload()

            # the connection menu next to Connect USB
            await pg.click('#btnConnMore'); await asyncio.sleep(0.2)
            check('▾ next to Connect USB offers Bluetooth and Wi-Fi', await ev("document.getElementById('connMenu').matches(':popover-open')") and await pg.is_visible('#btnMenuBle') and await pg.is_visible('#btnMenuWifi'))
            await pg.click('#btnMenuWifi'); await asyncio.sleep(0.3)
            check('Wi-Fi… opens Setup at the wireless card', await ev("document.getElementById('tab-setup').classList.contains('active') && !document.getElementById('connMenu').matches(':popover-open')"))

            # download the bridge
            async with pg.expect_download() as dl:
                await pg.click('#btnWfBridge')
            d = await dl.value
            path = await d.path()
            same = open(path, encoding='utf-8').read() == (ROOT / 'tools' / 'wifi-bridge' / 'magician_wifi_bridge.py').read_text(encoding='utf-8')
            check('Download the Wi-Fi bridge: the program, byte for byte', d.suggested_filename == 'magician_wifi_bridge.py' and same)

            # no bridge on that port: a clear message
            await pg.fill('#wf-armip', '127.0.0.1'); await pg.fill('#wf-bport', '8899')
            await pg.click('#btnWifi'); await asyncio.sleep(4.8)
            msg = await ev("[...document.querySelectorAll('#log div')].slice(0, 3).map(d => d.textContent).join(' | ')")   # newest first
            check('without the bridge: says to start it', 'bridge' in msg and await ev('!S.dev'), msg[-140:])

            # connect through the bridge, calibrate and draw over Wi-Fi
            await pg.fill('#wf-bport', str(BRIDGE))
            await pg.click('#btnWifi')
            ok = await wait_for(ev, "!!S.dev && S.link === 'Wi-Fi'", 20000)
            check('Connect over Wi-Fi: connected through the bridge', ok and 'Wi-Fi' in await pg.inner_text('#pill'), await pg.inner_text('#pill'))
            await wait_for(ev, "!document.getElementById('autocal').hidden", 4000)
            await pg.click('[data-ac=start]')
            await wait_for(ev, "AC.step === 'pen' || AC.step === 'error'", 30000)
            for _ in range(12):
                if await ev('S.pos.z') <= -68: break
                await pg.click('[data-dz="-10"]'); await wait_for(ev, '!AC.busy', 8000)
            for _ in range(10):
                if await ev('S.pos.z') <= -71.5: break
                await pg.click('[data-dz="-0.5"]'); await wait_for(ev, '!AC.busy', 8000)
            await pg.click('[data-ac=paper]')
            done = await wait_for(ev, "AC.step === 'done'", 15000)
            check('auto-calibration over Wi-Fi', done and await ev("S.model && S.model.ok"), await ev("AC.msg || ''"))
            await pg.click('#autocalBody [data-ac=test]')            # draws the 20 mm test square
            await asyncio.sleep(0.5)
            fin = await wait_for(ev, '!S.running', 60000); await asyncio.sleep(0.6)
            st = arm_stats()
            check('the test square is drawn over Wi-Fi: the arm got every move', fin and st.get('cp', 0) + st.get('ptp', 0) > 20 and await ev("S.paper.jobs.some(j => j.done)"), f"{st.get('ptp')} PTP + {st.get('cp')} CP moves at the arm")

            # lost messages: every 9th one goes missing, the app asks again
            await ev("disconnect()"); await asyncio.sleep(0.4)
            arm.terminate(); arm.wait(); arm = start_arm(9); await asyncio.sleep(0.8)
            await ev("showTab('setup')")
            await pg.click('#btnWifi'); await wait_for(ev, "!!S.dev", 8000)
            if not await ev("document.getElementById('autocal').hidden"): await pg.click('#autocalBody [data-ac=keep]')
            t0 = time.time(); okn = await ev("(async () => { let ok = 0; for (let i = 0; i < 40; i++) { try { await S.dev.pose(); ok++; } catch (e) {} } return ok; })()")
            dt = time.time() - t0
            check('with one message in nine lost, every request still gets its answer', okn == 40, f'40 pose reads in {dt:.1f} s')
            await ev("disconnect()")
            out = ''
            bridge.terminate()
            try: out = bridge.communicate(timeout=3)[0]
            except Exception: pass
            check('the bridge reports the app connecting and the messages passed', 'App connected' in out and 'messages to the arm' in out, out.strip().splitlines()[-1] if out.strip() else '')
            check('no page errors', not errors, '; '.join(errors[:3]))
            await b.close()
    finally:
        for proc in (srv, arm, bridge):
            try: proc.terminate()
            except Exception: pass
    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks passed" + (f"; FAILED: {bad}" if bad else ''))
    sys.exit(1 if bad else 0)

asyncio.run(main())
