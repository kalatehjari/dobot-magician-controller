"""Browser test: auto-calibration, picture tracing, smooth (CP) drawing, pause, reach checks, settings
migration. Runs the real app against the built-in kinematic simulator in headless Chromium.
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_drawing.py"""
import asyncio, json, pathlib, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
sys.path.insert(0, str(HERE)); from fixtures import write_images; write_images(f'{SRV}/img')
PORT = 8770
results = []
def check(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f'  {extra}' if extra else ''), flush=True)

async def wait_for(ev, expr, timeout=20000, step=150):
    t0 = time.time()
    while (time.time() - t0) * 1000 < timeout:
        if await ev(expr): return True
        await asyncio.sleep(step / 1000)
    return False

async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '-d', SRV], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(0.8)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--no-sandbox'])
            ctx = await b.new_context(viewport={'width': 1280, 'height': 1100}, accept_downloads=True)
            pg = await ctx.new_page(); errors = []
            pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
            pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
            ev = pg.evaluate
            await pg.goto(f'http://localhost:{PORT}/app.html')

            # ---------- auto-calibration ----------
            await pg.click('#btnSim')
            check('auto-calibration opens when connecting', await wait_for(ev, "!document.getElementById('autocal').hidden", 3000))
            await pg.click('[data-ac=start]')
            ok = await wait_for(ev, "AC.step === 'pen' || AC.step === 'error'", 15000)
            step = await ev('AC.step'); model = await ev('S.model')
            check('arm homed, readings checked, geometry confirmed', ok and step == 'pen' and model and model['ok'], json.dumps(model))
            check('tool offset measured (simulator uses 59.7 mm)', model and abs(model['dR'] - 59.7) < 0.05)
            check('before the pen is set, the arm stays high', await ev('S.limits.zMin') > 40 and not await ev('S.limits.penSet'), f"zMin {await ev('S.limits.zMin')}")
            for _ in range(12):                                     # lower the pen to z ≈ −70
                if await ev('S.pos.z') <= -68: break
                await pg.click('[data-dz="-10"]'); await wait_for(ev, '!AC.busy', 5000)
            for _ in range(10):
                if await ev('S.pos.z') <= -71.5: break
                await pg.click('[data-dz="-0.5"]'); await wait_for(ev, '!AC.busy', 5000)
            z_paper = await ev('S.pos.z')
            await pg.click('[data-ac=paper]')
            await wait_for(ev, "AC.step === 'done' || AC.step === 'error'", 10000)
            L = await ev('S.limits')
            check('pen-down set by the user, limits recomputed for that height', await ev("AC.step") == 'done' and L['penSet'] and abs(L['zDown'] - z_paper) < 0.11 and L['zMin'] <= L['zDown'],
                  json.dumps({k: L[k] for k in ['minR', 'maxR', 'zMin', 'zMax', 'zDown', 'zUp']}))
            summary = await pg.inner_text('#autocalBody')
            check('summary shows the largest square drawing', 'Largest square drawing' in summary, summary.replace('\n', ' | ')[:180])
            await pg.screenshot(path=str(OUT / 'autocal.png'))
            cp0 = await ev('S.dev.io.st.cpCount')
            await pg.click('[data-ac=test]')
            await wait_for(ev, 'S.running', 3000); await wait_for(ev, '!S.running', 30000)
            al = await ev('S.dev.io.st.alarms.size')
            check('test square drawn with smooth (CP) moves, no limit alarm', await ev('S.dev.io.st.cpCount') - cp0 >= 4 and al == 0, f"{await ev('S.dev.io.st.cpCount') - cp0} CP moves")

            # ---------- pictures → lines ----------
            await pg.set_input_files('#plot-file', f'{SRV}/img/shapes.png')
            await wait_for(ev, 'TR.result && S.plot.ops', 10000)
            n_shapes = await ev('TR.result.paths.length')
            check('PNG opens in “Picture to lines” and is traced', not await ev("document.getElementById('traceCard').hidden") and n_shapes >= 4, f'{n_shapes} lines')
            check('specks are ignored at the default detail', n_shapes <= 8, f'{n_shapes} lines (4 shapes + 1 hole expected)')
            await pg.screenshot(path=str(OUT / 'trace_shapes.png'), full_page=True)
            await pg.select_option('#tr-res', '900'); await pg.fill('#tr-detail', '10'); await pg.dispatch_event('#tr-detail', 'input'); await asyncio.sleep(0.8)
            n_hi = await ev('TR.result.paths.length')
            check('high detail + high resolution keeps the specks too', n_hi > n_shapes + 20, f'{n_shapes} → {n_hi} lines')
            await pg.select_option('#tr-res', '600'); await pg.fill('#tr-detail', '6'); await pg.dispatch_event('#tr-detail', 'input'); await asyncio.sleep(0.6)
            async with pg.expect_download() as dl:
                await pg.click('#btnTraceSvg')
            path = await (await dl.value).path(); svg = open(path).read()
            check('Download SVG gives a valid SVG of the lines', svg.startswith('<svg') and svg.count('<path ') == await ev('TR.result.paths.length'))
            await pg.set_input_files('#plot-file', f'{SRV}/img/sketch.png')
            await pg.select_option('#tr-mode', 'centre'); await asyncio.sleep(0.6)
            n_sk = await ev('TR.result.paths.length'); open_paths = await ev('TR.result.paths.every(p => !p.closed)')
            check('line drawing traced as single centre lines', open_paths and 3 <= n_sk <= 14, f'{n_sk} lines')
            await pg.click('#btnTraceUse'); await asyncio.sleep(0.5)
            await pg.screenshot(path=str(OUT / 'trace_sketch.png'), full_page=True)
            cp1, ptp1 = await ev('S.dev.io.st.cpCount'), await ev('S.dev.io.st.ptpCount')
            await pg.click('#btnDraw'); await wait_for(ev, 'S.running', 3000); await wait_for(ev, '!S.running', 60000)
            cps = await ev('S.dev.io.st.cpCount') - cp1
            check('sketch drawn smoothly without leaving the reach', cps > 20 and await ev('S.dev.io.st.alarms.size') == 0, f'{cps} CP moves, {await ev("S.dev.io.st.ptpCount") - ptp1} straight moves')
            await pg.set_input_files('#plot-file', f'{SRV}/img/photo.jpg')
            await pg.select_option('#tr-mode', 'edges'); await asyncio.sleep(0.8)
            n_ph = await ev('TR.result.paths.length')
            check('JPG photo traced by its edges', n_ph >= 2, f'{n_ph} lines')
            await pg.fill('#tr-curve', '0'); await pg.dispatch_event('#tr-curve', 'input'); await asyncio.sleep(0.6)
            pts0 = await ev('TR.result.paths.reduce((a, p) => a + p.pts.length, 0)')
            await pg.fill('#tr-curve', '10'); await pg.dispatch_event('#tr-curve', 'input'); await asyncio.sleep(0.6)
            pts10 = await ev('TR.result.paths.reduce((a, p) => a + p.pts.length, 0)')
            check('curve slider changes the lines', pts0 != pts10, f'{pts0} → {pts10} points')
            await pg.uncheck('#tr-auto'); await pg.fill('#tr-thr', '60'); await pg.dispatch_event('#tr-thr', 'input'); await asyncio.sleep(0.6)
            check('manual threshold is applied', abs(await ev('TR.result.threshold') - 60) < 0.01)

            # ---------- precise mode, pause / resume ----------
            await pg.select_option('#tr-mode', 'outline'); await pg.check('#tr-auto'); await asyncio.sleep(0.6)
            await pg.click('#btnTraceUse'); await asyncio.sleep(0.5)
            await pg.select_option('#plot-motion', 'precise')
            ptp2, cp2 = await ev('S.dev.io.st.ptpCount'), await ev('S.dev.io.st.cpCount')
            await pg.click('#btnDraw'); await wait_for(ev, 'S.running', 3000)
            await pg.click('#btnPause'); await asyncio.sleep(0.3)
            e1 = await ev('S.dev.io.st.exec'); await asyncio.sleep(0.8); e2 = await ev('S.dev.io.st.exec')
            check('Pause stops the arm mid-drawing', await ev('S.paused') and e1 == e2 and await ev('S.running'))
            await pg.click('#btnPause'); await wait_for(ev, '!S.running', 60000)
            check('Resume finishes the drawing', not await ev('S.running') and await ev('S.dev.io.st.alarms.size') == 0)
            check('precise mode draws with straight moves only', await ev('S.dev.io.st.cpCount') == cp2 and await ev('S.dev.io.st.ptpCount') > ptp2)
            await pg.select_option('#plot-motion', 'smooth')

            # ---------- placement controls ----------
            r0 = await ev('S.plot.rect')
            await pg.click('#btnRot90'); await asyncio.sleep(0.6)
            r1 = await ev('S.plot.rect')
            check('rotating 90° turns the drawing area around', abs((r0['h'] / r0['w']) - (r1['w'] / r1['h'])) < 0.05, f"{r0['h']:.0f}×{r0['w']:.0f} → {r1['h']:.0f}×{r1['w']:.0f} mm")
            await pg.fill('#pl-rotNum', '0'); await pg.press('#pl-rotNum', 'Enter'); await asyncio.sleep(0.4)
            moved = await ev("(() => { applyWant({ ...S.plot.place, cx: 130, cy: 0 }); buildPlot(); return S.plot.place; })()")
            check('a drawing put over the base is moved back into the reach', moved['cx'] > 150 and await ev('S.plot.placeOk'), f"centre X {moved['cx']:.0f} mm")
            await pg.click('#btnPlLargest'); await asyncio.sleep(0.5)
            fits = await ev("""S.plot.ops.every(o => magReachable(o.x, o.y, S.limits.zDown, S.model, 1) && magReachable(o.x, o.y, S.limits.zUp, S.model, 1))""")
            check('the largest drawing is fully reachable at pen height', fits, f"{(await ev('S.plot.rect'))['h']:.0f} × {(await ev('S.plot.rect'))['w']:.0f} mm")
            # an unreachable move from a smart feature is clamped, not attempted
            await ev('streamTo("test", { x: 120, y: 0, z: S.limits.zDown + 5 })'); await asyncio.sleep(1.0); await ev('streamRelease("test")')
            check('smart moves are kept inside the real reach', await ev('S.dev.io.st.alarms.size') == 0)
            await pg.click('#nav-plot'); await asyncio.sleep(0.3)
            await pg.screenshot(path=str(OUT / 'plot.png'), full_page=True)
            await pg.click('#nav-setup'); await asyncio.sleep(1.2)
            status = await pg.inner_text('#modelStatus')
            check('Setup shows the live geometry check', 'Live geometry check' in status, status)
            await pg.screenshot(path=str(OUT / 'setup.png'), full_page=True)
            real = [e for e in errors if 'favicon' not in e]
            check('no page errors', not real, ' | '.join(real[:4]))

            # ---------- migration of old settings ----------
            pg2 = await ctx.new_page(); err2 = []
            pg2.on('pageerror', lambda e: err2.append(str(e)))
            await pg2.add_init_script("localStorage.setItem('magician-settings', JSON.stringify({ limits: { minR: 100, maxR: 320, zMin: -30, zMax: 150, zUp: 30, zDown: 0, homeX: 200, homeY: 0, homeZ: 60, thMin: -90, thMax: 90 }, speed: { live: 140, accel: 120, draw: 60, smart: 160 } }))")
            await pg2.goto(f'http://localhost:{PORT}/app.html')
            await asyncio.sleep(0.5)
            lim = await pg2.evaluate('S.limits'); sp = await pg2.evaluate('S.speed'); logtxt = await pg2.inner_text('#log')
            check('old unsafe limits are replaced; speeds are kept', lim['minR'] == 200 and lim['maxR'] == 295 and not lim['penSet'] and sp['live'] == 140 and 'reset' in logtxt, json.dumps({'minR': lim['minR'], 'maxR': lim['maxR'], 'live': sp['live']}))
            await b.close()
    finally:
        srv.terminate()
    fails = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fails)}/{len(results)} passed" + (f"; FAILED: {fails}" if fails else ''))

asyncio.run(main())
