"""Browser test for smooth & quiet motion: profiles and their caps on every speed command, continuous
drawing (few full stops), glide following (continuous-path moves, arrives without overshoot), steps
fallback, the quiet-speed finder (simulated sound) and settings migration. Records the real command
frames the app sends to the simulated arm.
Runs the real app with the built-in simulator in headless Chromium.
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_smooth.py"""
import asyncio, json, math, pathlib, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
sys.path.insert(0, str(HERE)); from fixtures import write_images; write_images(f'{SRV}/img')
PORT = 8775
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

HOOK = """(() => { window.__frames = []; const io = S.dev.io, orig = io.exchange.bind(io);
  io.exchange = async f => { const id = f[3];
    if ([80, 81, 84, 90, 91].includes(id)) { const n = f[2] - 2, off = (id === 84 || id === 91) ? 1 : 0, dv = new DataView(f.buffer, f.byteOffset + 5, n), fl = [];
      for (let i = off; i + 4 <= n; i += 4) fl.push(+dv.getFloat32(i, true).toFixed(3));
      window.__frames.push({ id, t: performance.now(), fl }); }
    return orig(f); }; return true; })()"""
COUNT = "(() => ({ ptp: window.__frames.filter(f => f.id === 84).length, cp: window.__frames.filter(f => f.id === 91).length }))()"

async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '-d', SRV], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(0.8)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--no-sandbox'])
            ctx = await b.new_context(viewport={'width': 1280, 'height': 1100})
            pg = await ctx.new_page(); errors = []
            pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
            pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
            ev = pg.evaluate
            await pg.goto(f'http://localhost:{PORT}/app.html')

            # ---------- defaults ----------
            st = await ev("({ m: S.motion, s: S.speed, ver: document.querySelector('.ver').textContent, sel: document.getElementById('mo-profile').value, feel: document.getElementById('plot-feel').value, cp: document.getElementById('plot-cpacc').value })")
            check('new installs start Quiet & smooth with gliding', st['m'] == {'profile': 'quiet', 'follow': 'glide'} and st['s']['draw'] == 25 and st['s']['accel'] == 60 and st['sel'] == 'quiet' and st['feel'] == 'quiet' and st['cp'] == '70', json.dumps(st['s']))
            check('version shows v1.1.0 or later', tuple(int(v) for v in st['ver'].lstrip('v').split('.')) >= (1, 1, 0), st['ver'])

            # ---------- calibrate in the simulator ----------
            await pg.click('#btnSim'); await wait_for(ev, "!document.getElementById('autocal').hidden", 3000)
            await pg.click('[data-ac=start]'); await wait_for(ev, "AC.step === 'pen'", 15000)
            for _ in range(12):
                if await ev('S.pos.z') <= -58: break
                await pg.click('[data-dz="-10"]'); await wait_for(ev, '!AC.busy', 5000)
            await pg.click('[data-ac=paper]'); await wait_for(ev, "AC.step === 'done'", 10000)
            await pg.click('#autocalBody [data-ac=close]')
            await ev(HOOK)

            # ---------- caps on every speed command ----------
            await ev('S.dev.setSpeed(300, 400)'); await asyncio.sleep(0.2)
            f81 = await ev("window.__frames.filter(f => f.id === 81).pop().fl")
            f80 = await ev("window.__frames.filter(f => f.id === 80).pop().fl")
            check('Quiet caps speed and acceleration on every speed command', f81 == [130, 130, 70, 70] and f80[4] <= 42.01, f'straight moves {f81}, joints {f80[0]}°/s, {f80[4]}°/s²')
            await pg.click('#nav-setup'); await pg.select_option('#mo-profile', 'fast'); await asyncio.sleep(0.3)
            await ev('S.dev.setSpeed(300, 400)'); await asyncio.sleep(0.2)
            f81b = await ev("window.__frames.filter(f => f.id === 81).pop().fl")
            spd = await ev('S.speed')
            check('Fast lets the arm go faster and sets fast speeds', f81b == [300, 300, 400, 400] and spd['draw'] == 50 and await ev("document.getElementById('plot-feel').value") == 'fast', f'{f81b}')
            await pg.click('#nav-plot'); await pg.select_option('#plot-feel', 'quiet'); await asyncio.sleep(0.3)
            check('the Plotter feel selector switches the whole app back to Quiet', await ev("S.motion.profile") == 'quiet' and await ev("document.getElementById('mo-profile').value") == 'quiet' and await ev('S.speed.draw') == 25)

            # ---------- continuous drawing ----------
            await pg.click('#nav-plot'); await pg.click('#tab-plot details summary')
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120">' + ''.join(f'<rect x="{10 + 22 * i}" y="10" width="14" height="14"/>' for i in range(8)) +
                   '<circle cx="40" cy="80" r="25"/><path d="M90 60 L190 110"/></svg>')
            await pg.fill('#plot-text', svg); await pg.click('#btnLoadText'); await asyncio.sleep(0.6)
            await ev('window.__frames = []')
            await pg.click('#btnDraw'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 60000)
            c = await ev(COUNT)
            cpp = await ev("window.__frames.filter(f => f.id === 90).pop().fl")
            job = await ev('(() => { const j = S.paper.jobs[S.paper.jobs.length - 1]; return { done: j.done, n: j.cmds.length }; })()')
            check('smooth drawing is one continuous path: almost no full stops', c['ptp'] <= 4 and c['cp'] > 150 and job['done'] and await ev('S.dev.io.st.alarms.size') == 0, f"{c['cp']} continuous moves, {c['ptp']} point-to-point")
            check('continuous-path settings follow the feel (gentle acceleration, pen speed)', cpp == [70, 25, 70], f'planned acc {cpp[0]}, speed {cpp[1]}, acc {cpp[2]}')
            hop = await ev("""(() => { const j = S.paper.jobs[S.paper.jobs.length - 1], zD = j.zD; let ups = 0, lowHops = 0, maxZ = -1e9;
                for (const c of j.cmds) maxZ = Math.max(maxZ, c.z);
                for (let i = 1; i < j.cmds.length; i++) { const a = j.cmds[i - 1], b = j.cmds[i]; if (Math.abs(a.z - zD) < 0.01 && b.z > zD + 0.5) ups++; }
                return { ups, top: maxZ - zD }; })()""")
            check('pen hops between nearby strokes are low', hop['ups'] >= 8, f"{hop['ups']} hops, highest {hop['top']:.1f} mm above the paper")
            await pg.select_option('#plot-motion', 'precise')
            await ev('window.__frames = []')
            await pg.click('#btnDraw'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 60000)
            c2 = await ev(COUNT)
            check('precise mode still stops at every point (for comparison)', c2['cp'] == 0 and c2['ptp'] > 40, f"{c2['ptp']} point-to-point moves")
            await pg.select_option('#plot-motion', 'smooth')
            await pg.screenshot(path=str(OUT / 'smooth_plot.png'), full_page=True)

            # ---------- glide following (mouse) ----------
            await pg.click('#nav-mouse'); await asyncio.sleep(0.3)
            await pg.click('#btnLive')
            box = await pg.locator('#mouseCanvas').bounding_box()
            pA = await ev("(() => { const v = viewOf(mouseCv), r = mouseCv.getBoundingClientRect(), [sx, sy] = v.toS(230, 60); return [r.left + sx, r.top + sy]; })()")
            pB = await ev("(() => { const v = viewOf(mouseCv), r = mouseCv.getBoundingClientRect(), [sx, sy] = v.toS(270, -60); return [r.left + sx, r.top + sy]; })()")
            await ev('window.__frames = []')
            await pg.mouse.move(*pA); await pg.mouse.down()
            for i in range(1, 31):
                await pg.mouse.move(pA[0] + (pB[0] - pA[0]) * i / 30, pA[1] + (pB[1] - pA[1]) * i / 30); await asyncio.sleep(0.03)
            await pg.mouse.up()
            await wait_for(ev, '!GL.st || (Math.hypot(GL.st.vx, GL.st.vy) < 0.5)', 6000)
            await asyncio.sleep(0.6)
            c3 = await ev(COUNT); tgt = await ev('S.target'); pos = await ev('S.pos')
            gaps = await ev("""(() => { const cp = window.__frames.filter(f => f.id === 91); let mx = 0; for (let i = 1; i < cp.length; i++) mx = Math.max(mx, Math.hypot(cp[i].fl[0] - cp[i - 1].fl[0], cp[i].fl[1] - cp[i - 1].fl[1])); return { mx, n: cp.length }; })()""")
            check('mouse following glides: continuous-path moves only', c3['cp'] >= 10 and c3['ptp'] == 0, f"{c3['cp']} continuous moves")
            check('the glide path is fine-grained (no big jumps between moves)', gaps['mx'] <= 80 * 0.09 * 1.8 + 1, f"largest step {gaps['mx']:.1f} mm")
            check('the arm ends exactly where the mouse let go', math.hypot(pos['x'] - tgt['x'], pos['y'] - tgt['y']) < 1.0, f"{math.hypot(pos['x'] - tgt['x'], pos['y'] - tgt['y']):.2f} mm off")
            await ev("(() => { const el = document.getElementById('mo-follow'); el.value = 'steps'; el.dispatchEvent(new Event('change')); })()"); await asyncio.sleep(0.2)
            await ev('window.__frames = []')
            await pg.mouse.move(*pB); await pg.mouse.down()
            for i in range(1, 16):
                await pg.mouse.move(pB[0] + (pA[0] - pB[0]) * i / 15, pB[1] + (pA[1] - pB[1]) * i / 15); await asyncio.sleep(0.04)
            await pg.mouse.up(); await asyncio.sleep(0.8)
            c4 = await ev(COUNT)
            check('Steps following moves point to point instead', c4['ptp'] >= 3 and c4['cp'] == 0, f"{c4['ptp']} point-to-point moves")
            await ev("(() => { const el = document.getElementById('mo-follow'); el.value = 'glide'; el.dispatchEvent(new Event('change')); })()"); await pg.click('#btnLive'); await asyncio.sleep(0.3)

            # ---------- glide for smart features ----------
            await ev('window.__frames = []')
            await ev("streamTo('test', { x: 250, y: 50, z: 40 })"); await asyncio.sleep(2.5); await ev("streamRelease('test')"); await asyncio.sleep(0.8)
            c5 = await ev(COUNT); p5 = await ev('S.pos')
            check('hand / arm / face following glides too', c5['cp'] >= 8 and c5['ptp'] == 0 and math.hypot(p5['x'] - 250, p5['y'] - 50, p5['z'] - 40) < 1.5, f"{c5['cp']} continuous moves, ended {math.hypot(p5['x'] - 250, p5['y'] - 50, p5['z'] - 40):.2f} mm from the target")

            # ---------- quiet-speed finder (simulated sound) ----------
            await pg.click('#nav-setup'); await asyncio.sleep(0.3)
            await pg.click('#btnQuietTest'); await asyncio.sleep(0.3)
            await wait_for(ev, '!QT.running', 30000)
            picks = await ev('QT.picks'); n = await ev('QT.res.draw.length + QT.res.travel.length')
            check('quiet-speed finder tests every speed and avoids the resonances', picks == {'draw': 20, 'travel': 80} and n == 12, json.dumps(picks))
            bars = await ev("""(() => { const cv = document.getElementById('qtCanvas'), d = window.devicePixelRatio || 1, c = cv.getContext('2d'), img = c.getImageData(0, 0, cv.width, cv.height).data; let n = 0;
                for (let i = 0; i < img.length; i += 4) if (img[i + 2] > 200 && img[i] < 80 && img[i + 3] > 200) n++; return n; })()""")
            check('the loudness chart is drawn', not await ev("document.getElementById('qtCanvas').hidden") and bars > 200, f'{bars} bar pixels')
            await pg.click('#btnQtUse'); await asyncio.sleep(0.3)
            check('“Use these speeds” sets the pen and travel speeds', await ev('S.speed.draw') == 20 and await ev('S.speed.travel') == 80 and await ev("document.getElementById('plot-speed').value") == '20')
            await pg.locator('#qtCanvas').scroll_into_view_if_needed()
            await pg.screenshot(path=str(OUT / 'smooth_setup.png'), full_page=True)
            real = [e for e in errors if 'favicon' not in e]
            check('no page errors', not real, ' | '.join(real[:4]))

            # ---------- upgrade from the previous version ----------
            pg2 = await ctx.new_page()
            await pg2.add_init_script("localStorage.setItem('magician-settings', JSON.stringify({ v: 3, limits: { minR: 200, maxR: 295, thMin: -85, thMax: 85, zMin: 0, zMax: 110, zUp: 30, zDown: 15, homeX: 240, homeY: 0, homeZ: 60, penSet: true }, speed: { live: 140, accel: 120, draw: 35, travel: 100, smart: 160 }, model: null }))")
            await pg2.goto(f'http://localhost:{PORT}/app.html'); await asyncio.sleep(0.5)
            m2 = await pg2.evaluate('({ m: S.motion, s: S.speed, lim: S.limits.penSet })'); log2 = await pg2.inner_text('#log')
            check('after the update, saved settings switch to Quiet & smooth (limits kept)', m2['m']['profile'] == 'quiet' and m2['s']['accel'] == 60 and m2['s']['draw'] == 25 and m2['lim'] and 'Quiet & smooth' in log2, json.dumps(m2['s']))
            await b.close()
    finally:
        srv.terminate()
    fails = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fails)}/{len(results)} passed" + (f"; FAILED: {fails}" if fails else ''))

asyncio.run(main())
