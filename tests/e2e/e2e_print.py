"""Browser test for 3D printing: loading STL/OBJ files, units, placement (scale, turn, tip, lay flat, fit,
move), settings and presets, slicing and the preview, G-code and placed-STL downloads, the printer simulator
(heat, feed, nozzle height, fan), printing with the start checklist, live progress, pause/resume, stop, the
red STOP, sending ahead into the 63-byte buffer, credits, and the tab's layout on a phone and in dark mode.
Runs the real app with the built-in printer simulator in headless Chromium (WebGL through SwiftShader).
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_print.py"""
import asyncio, json, math, os, pathlib, re, shutil, struct, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = str(HERE / 'out'); os.makedirs(OUT, exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
PORT = 8791
results = []
def check(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f'  {extra}' if extra else ''), flush=True)

async def wait_for(pg, expr, timeout=20000, step=100):
    t0 = time.time()
    while (time.time() - t0) * 1000 < timeout:
        if await pg.evaluate(expr): return True
        await asyncio.sleep(step / 1000)
    return False

# ---- test files ----
def box_tris(x0, y0, z0, x1, y1, z1):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return [(v[a], v[b], v[c]) for a, b, c in f]
def write_stl(path, tris, header=b'test box'):
    with open(path, 'wb') as fh:
        fh.write(header.ljust(80, b' ')); fh.write(struct.pack('<I', len(tris)))
        for t in tris:
            fh.write(struct.pack('<3f', 0, 0, 0))
            for p in t: fh.write(struct.pack('<3f', *p))
            fh.write(b'\0\0')
def write_ascii(path, tris):
    with open(path, 'w') as fh:
        fh.write('solid tetra\n')
        for t in tris:
            fh.write(' facet normal 0 0 0\n  outer loop\n')
            for p in t: fh.write('   vertex %g %g %g\n' % p)
            fh.write('  endloop\n endfacet\n')
        fh.write('endsolid tetra\n')
FILES = tempfile.mkdtemp(prefix='magician-print-files-')
write_stl(f'{FILES}/box.stl', box_tris(0, 0, 0, 30, 20, 10), b'solid box exported by a CAD program')   # binary despite "solid"
write_stl(f'{FILES}/big.stl', box_tris(0, 0, 0, 200, 200, 50))
write_stl(f'{FILES}/inch.stl', box_tris(0, 0, 0, 1, 0.8, 0.5))
tet = [(0, 0, 0), (25, 0, 0), (0, 25, 0), (0, 0, 25)]
write_ascii(f'{FILES}/tetra.stl', [(tet[0], tet[2], tet[1]), (tet[0], tet[1], tet[3]), (tet[1], tet[2], tet[3]), (tet[0], tet[3], tet[2])])
with open(f'{FILES}/bad.stl', 'w') as fh: fh.write('this is not a model')

async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '-d', SRV], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.7)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            ctx = await b.new_context(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
            pg = await ctx.new_page(); errors = []
            pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
            pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
            dialogs = []
            def on_dialog(d):
                dialogs.append(d.message); asyncio.ensure_future(d.accept())
            pg.on('dialog', on_dialog)
            await pg.goto(f'http://localhost:{PORT}/app.html')
            await pg.click('#nav-print')
            check('the 3D print tab opens with a WebGL preview', await pg.evaluate("document.getElementById('tab-print').classList.contains('active') && !!P3S.view.gl"))
            check('nothing to print yet: slice and start are off', await pg.evaluate("$id('btnPrSlice').disabled && $id('btnPrStart').disabled && $id('btnPrGcode').disabled"))
            check('defaults are Dobot\'s (0.2 mm layers, 200 °C, Ø80 plate)', await pg.evaluate("$id('ps-layerH').value === '0.2' && $id('ps-temp').value === '200' && $id('ps-plateD').value === '80' && $id('pr-preset').value === 'normal'"))

            # ---- files ----
            await pg.set_input_files('#pr-file', f'{FILES}/box.stl'); await asyncio.sleep(0.4)
            info = await pg.inner_text('#pr-info')
            check('binary STL with a "solid" header loads: 12 triangles, 30 × 20 × 10 mm, closed', '12 triangles' in info and '30.0 × 20.0 × 10.0' in info and 'closed' in info, info)
            fit = await pg.inner_text('#pr-fit')
            check('it fits the plate', 'fits' in fit, fit)
            await pg.set_input_files('#pr-file', f'{FILES}/tetra.stl'); await asyncio.sleep(0.4)
            info = await pg.inner_text('#pr-info')
            check('ASCII STL loads', 'ASCII STL' in info and '4 triangles' in info, info)
            await pg.set_input_files('#pr-file', f'{FILES}/bad.stl'); await asyncio.sleep(0.4)
            check('a file that is not a model gives a message', 'does not look like' in await pg.inner_text('#pr-msg'))
            await pg.set_input_files('#pr-file', f'{FILES}/big.stl'); await asyncio.sleep(0.4)
            msg = await pg.inner_text('#pr-msg'); pct = await pg.evaluate('P3S.pct')
            check('a 200 mm model is scaled down to fit, and the user is told', pct < 30 and 'scaled' in msg and 'fits' in await pg.inner_text('#pr-fit'), f'{pct} % — {msg}')
            await pg.set_input_files('#pr-file', f'{FILES}/inch.stl'); await asyncio.sleep(0.4)
            check('a tiny model hints at the units', 'inches' in await pg.inner_text('#pr-msg'))
            await pg.select_option('#pr-units', '25.4'); await asyncio.sleep(0.3)
            fit = await pg.inner_text('#pr-fit')
            check('units: inches make it 25.4 × 20.3 × 12.7 mm', '25.4 × 20.3 × 12.7' in fit, fit)
            await pg.select_option('#pr-units', '1')

            # ---- placement ----
            await pg.select_option('#pr-sample', 'bridge'); await asyncio.sleep(0.3)
            check('a ready-made model loads', 'Arch bridge' in await pg.inner_text('#pr-file-name'))
            await pg.click('#btnPrTipX'); await asyncio.sleep(0.2)
            check('tip over X: the bridge lies on its side (40 × 18 × 12)', '40.0 × 18.0 × 12.0' in await pg.inner_text('#pr-fit'))
            await pg.click('#btnPrFlat'); await asyncio.sleep(0.2)
            sz = await pg.evaluate("[0,1,2].map(k => +(P3S.placed.max[k] - P3S.placed.min[k]).toFixed(1))")
            check('lay flat: it lies on its largest flat face', sz[2] in (12.0, 18.0), str(sz))
            await pg.click('#btnPrReset'); await asyncio.sleep(0.2)
            await pg.fill('#pr-scaleNum', '150'); await pg.dispatch_event('#pr-scaleNum', 'change'); await asyncio.sleep(0.2)
            check('scale 150 %', '60.0 × 18.0 × 27.0' in await pg.inner_text('#pr-fit'))
            await pg.fill('#pr-x', '25'); await pg.dispatch_event('#pr-x', 'change'); await asyncio.sleep(0.2)
            fit = await pg.inner_text('#pr-fit')
            check('moved past the plate edge: shown as not fitting', 'reaches' in fit and await pg.evaluate('P3S.view.bad'), fit)
            await pg.click('#btnPrSlice'); await asyncio.sleep(0.6)
            check('slicing a model that does not fit is refused with the reason', 'plate is Ø80' in await pg.inner_text('#pr-msg'))
            await pg.click('#btnPrFit'); await asyncio.sleep(0.2)
            check('fit to plate: centred and as large as fits', 'fits' in await pg.inner_text('#pr-fit') and await pg.evaluate('P3S.place.x === 0 && P3S.pct > 100'), str(await pg.evaluate('P3S.pct')))
            await pg.fill('#pr-rotNum', '90'); await pg.dispatch_event('#pr-rotNum', 'change'); await asyncio.sleep(0.2)
            sz = await pg.evaluate("[0,1].map(k => +(P3S.placed.max[k] - P3S.placed.min[k]).toFixed(1))")
            check('turn on the plate by 90°', sz[0] < sz[1], str(sz))

            # ---- settings ----
            await pg.select_option('#pr-preset', 'vase'); await asyncio.sleep(0.2)
            check('vase preset: one wall, no infill, no top, vase ticked', await pg.evaluate("$id('ps-walls').value === '1' && $id('ps-infill').value === '0' && $id('ps-top').value === '0' && $id('ps-vase').checked"))
            await pg.select_option('#pr-preset', 'normal'); await asyncio.sleep(0.2)
            check('normal preset restores walls, infill and top', await pg.evaluate("$id('ps-walls').value === '2' && $id('ps-infill').value === '15' && !$id('ps-vase').checked"))
            await pg.fill('#ps-layerH', '0.25'); await pg.dispatch_event('#ps-layerH', 'change'); await asyncio.sleep(0.1)
            check('changing a value shows Custom', await pg.evaluate("$id('pr-preset').value === 'custom'"))
            await pg.fill('#ps-temp', '300'); await pg.dispatch_event('#ps-temp', 'change')
            await pg.click('#btnPrSlice'); await asyncio.sleep(0.4)
            check('an impossible setting is refused with the allowed range', 'between 170 and 250' in await pg.inner_text('#pr-msg'))
            await pg.click('#btnPrDefaults'); await asyncio.sleep(0.2)

            # ---- slicing a small cube ----
            await pg.select_option('#pr-sample', 'cube'); await asyncio.sleep(0.2)
            await pg.fill('#pr-scaleNum', '30'); await pg.dispatch_event('#pr-scaleNum', 'change'); await asyncio.sleep(0.2)
            await pg.click('#btnPrSlice')
            ok = await wait_for(pg, '!!P3S.result && !P3S.slicing', 30000)
            stats = await pg.inner_text('#pr-stats')
            check('slicing: layers, time and filament shown', ok and re.search(r'\d+ layers', stats) and 'filament' in stats, stats)
            check('the layer slider covers every layer', await pg.evaluate("+$id('pr-layer').max === P3S.result.layers.length - 1 && !$id('pr-layer').disabled"))
            await pg.fill('#pr-layer', '5'); await pg.dispatch_event('#pr-layer', 'input'); await asyncio.sleep(0.2)
            check('choosing a layer shows its height', 'Z 1.35 mm' in await pg.inner_text('#pr-layerVal'), await pg.inner_text('#pr-layerVal'))
            await pg.click('#pr-vLayer'); await asyncio.sleep(0.2)
            await (await pg.query_selector('#prCanvas')).screenshot(path=f'{OUT}/print_layer_view.png')
            await pg.click('#pr-v3d')
            async with pg.expect_download() as dl:
                await pg.click('#btnPrGcode')
            d = await dl.value; path = await d.path(); g = open(path).read()
            check('G-code download: named after the model, with heating, layers and the Dobot end code',
                  d.suggested_filename.endswith('.gcode') and 'M109 S200' in g and ';LAYER_COUNT:' in g and 'G1 Y+50' in g and g.count(';LAYER:') == await pg.evaluate('P3S.result.layers.length'), d.suggested_filename)
            async with pg.expect_download() as dl:
                await pg.click('#btnPrStl')
            d = await dl.value; data = open(await d.path(), 'rb').read()
            n = struct.unpack('<I', data[80:84])[0]
            check('placed STL download: binary STL of the scaled model', d.suggested_filename.endswith('-placed.stl') and len(data) == 84 + 50 * n and n == 16, f'{n} triangles')
            check('start needs a printer first', await pg.evaluate("$id('btnPrStart').disabled"))

            # ---- printer simulator ----
            await pg.select_option('#pr-simSpeed', '100')        # real-time paced (× 100), so there is time to pause and stop
            await pg.click('#btnPrSim')
            ok = await wait_for(pg, "!!(P3S.link && P3S.link.ready && P3S.link.temp !== null)", 15000)
            check('printer simulator connects and reports the nozzle temperature', ok and 'simulator' in (await pg.inner_text('#pr-pill')).lower() and '°C' in await pg.inner_text('#pr-temp'), await pg.inner_text('#pr-temp'))
            await pg.click('#btnPrFeed'); await asyncio.sleep(0.2)
            check('feeding filament is refused while cold', 'Heat the nozzle first' in await pg.inner_text('#pr-msg'))
            await pg.click('#btnPrHeat')
            ok = await wait_for(pg, 'P3S.link.temp > 195', 20000)
            check('heat: the nozzle reaches 200 °C', ok, await pg.inner_text('#pr-temp'))
            await pg.click('#btnPrFeed'); await asyncio.sleep(0.5)
            check('hot: 10 mm of filament is fed', await pg.evaluate("P3S.link.io.trace.filter(c => c !== 'M105').slice(-3).join('|') === 'G91|G1 E10 F100|G90'"))
            await pg.click('#btnPrZero'); await asyncio.sleep(0.5)
            check('save nozzle height: explains the unlock button, then sends M415 (beep)', any('unlock' in m for m in dialogs) and await pg.evaluate('P3S.link.io.beeps === 1'))
            await pg.click('#btnPrFan'); await asyncio.sleep(0.3)
            check('fan on/off', await pg.evaluate("P3S.link.io.fan === 255 && $id('btnPrFan').textContent === 'Fan off'"))
            await pg.click('#btnPrFan'); await asyncio.sleep(0.2)
            await pg.click('#btnPrCool'); await asyncio.sleep(0.3)
            check('heater off', await pg.evaluate('P3S.link.io.target === 0'))

            # ---- printing ----
            await pg.click('#btnPrStart'); await asyncio.sleep(0.2)
            check('start shows the checklist; printing waits until every item is ticked', await pg.evaluate("!$id('prCheck').hidden && $id('btnPrCheckGo').disabled"))
            boxes = await pg.query_selector_all('#prCheck .pr-check input')
            for k, bx in enumerate(boxes):
                await bx.check()
                if k < len(boxes) - 1:
                    still = await pg.evaluate("$id('btnPrCheckGo').disabled")
            check('…and then allows it', await pg.evaluate("!$id('btnPrCheckGo').disabled") and still)
            await pg.click('#btnPrCheckGo')
            ok = await wait_for(pg, "/Heating|Layer/.test($id('pr-progress').textContent)", 5000, 20)
            check('printing starts by heating', ok, await pg.inner_text('#pr-progress'))
            ok = await wait_for(pg, "/^Layer \\d+ of/.test($id('pr-progress').textContent)", 30000, 50)
            check('live progress: layer, per cent, time so far and to go', ok and 'to go' in await pg.inner_text('#pr-progress'), await pg.inner_text('#pr-progress'))
            check('the preview follows the print', await pg.evaluate('P3S.view.progressSeg > 0'))
            await pg.click('#btnPrPause')
            ok = await wait_for(pg, "P3S.link.job.paused && P3S.link.io.queue.length === 0 && P3S.link.io.trace.filter(c => c !== 'M105').slice(-4).join('|') === 'G91|G1 E-2 F1800|G1 Z5 F600|G90'", 10000, 50)
            check('pause: filament backed off and the nozzle lifted', ok and await pg.inner_text('#btnPrPause') == 'Resume')
            acked = await pg.evaluate('P3S.link.job.acked'); await asyncio.sleep(0.5)
            check('while paused nothing more is sent', await pg.evaluate('P3S.link.job.acked') == acked)
            await pg.click('#btnPrPause')
            ok = await wait_for(pg, 'P3S.link.job.done', 60000, 100)
            prog = await pg.inner_text('#pr-progress')
            check('resume, then the whole print goes through', ok and prog.startswith('Done'), prog)
            same = await pg.evaluate("""(() => { const want = gcodeCommands(P3S.jobResult.gcode).cmds, park = ['G91','G1 E-2 F1800','G1 Z5 F600','G90','G91','G1 Z-5 F600','G1 E2 F1800','G90'];
              let tr = P3S.link.io.trace.filter(c => c !== 'M105' && !/^M110/.test(c));
              const k = tr.lastIndexOf('G1 Z-5 F600'); tr = tr.slice(tr.indexOf('M106', tr.indexOf('M106') + 1)); return null; })()""")
            got = await pg.evaluate("""(() => { const want = gcodeCommands(P3S.jobResult.gcode).cmds;
              const tr = P3S.link.io.trace.filter(c => c !== 'M105' && !/^M110/.test(c)), i = tr.indexOf(want[0], tr.length - want.length - 10);
              let rest = tr.slice(tr.length - want.length - 8);
              const k = rest.indexOf('G1 E-2 F1800') - 1; if (k >= 0) rest = rest.slice(0, k).concat(rest.slice(k + 8));
              return { n: rest.length, want: want.length, same: rest.length === want.length && rest.every((c, j) => c === want[j]) }; })()""")
            check('the printer received exactly the G-code (plus the pause moves)', got['same'], json.dumps(got))
            ok = await wait_for(pg, 'P3S.link.io.queue.length === 0', 10000)
            check('at the end the simulated heater and fan are off', await pg.evaluate('P3S.link.io.target === 0 && P3S.link.io.fan === 0 && P3S.link.io.coldBlocked === 0'))
            check('buttons after the print: start again possible, pause and stop off', await pg.evaluate("!$id('btnPrStart').disabled && $id('btnPrPause').disabled && $id('btnPrStop').disabled"))

            # stop
            await pg.click('#btnPrStart'); await asyncio.sleep(0.1)
            for bx in await pg.query_selector_all('#prCheck .pr-check input'): await bx.check()
            await pg.click('#btnPrCheckGo')
            await wait_for(pg, "/^Layer \\d+ of/.test($id('pr-progress').textContent)", 30000, 50)
            await pg.click('#btnPrStop')
            ok = await wait_for(pg, "P3S.link.job.cancelled && P3S.link.io.trace.filter(c => c !== 'M105').slice(-5).join('|') === 'M104 S0|G91|G1 Z10 F600|G90|M107'", 10000, 50)
            check('stop print: confirmed, heater off, nozzle lifted', ok and 'Stopped' in await pg.inner_text('#pr-progress'), await pg.inner_text('#pr-progress'))
            # the red STOP
            await pg.click('#btnPrStart'); await asyncio.sleep(0.1)
            for bx in await pg.query_selector_all('#prCheck .pr-check input'): await bx.check()
            await pg.click('#btnPrCheckGo')
            await wait_for(pg, "/^Layer \\d+ of/.test($id('pr-progress').textContent)", 30000, 50)
            await pg.click('#btnStop')
            ok = await wait_for(pg, "P3S.link.job.error === 'Emergency stop' && P3S.link.io.trace.includes('M112')", 5000, 50)
            check('the red STOP halts the printer at once (M112 and a reset)', ok and 'halted' in await pg.inner_text('#pr-msg'), await pg.inner_text('#pr-msg'))
            await asyncio.sleep(0.6)
            # after the restart the link renumbers and still works
            ok = await wait_for(pg, "P3S.link && P3S.link.io.boots >= 2", 5000)
            await pg.click('#btnPrCool'); await asyncio.sleep(0.6)
            after = await pg.evaluate("(() => { const t = P3S.link.io.trace; return t.slice(t.lastIndexOf('M112') + 1).filter(c => c !== 'M105'); })()")
            check('after the emergency nothing more of the print is sent; commands work again', ok and after == ['M110 N0', 'M104 S0'], str(after))
            # out of date after a change
            await pg.fill('#ps-infill', '20'); await pg.dispatch_event('#ps-infill', 'change'); await asyncio.sleep(0.2)
            check('a changed setting needs a new slice before printing', await pg.evaluate("$id('btnPrStart').disabled && $id('btnPrGcode').disabled") and 'Press Slice' in await pg.inner_text('#pr-stats'))
            await pg.click('#btnPrConnect'); await asyncio.sleep(0.4)
            check('disconnect the printer', await pg.evaluate('!P3S.link') and 'Not connected' in await pg.inner_text('#pr-pill'))

            # ---- sending ahead into the 63-byte buffer ----
            await pg.click('#btnPrSlice'); await wait_for(pg, '!!P3S.result && !P3S.slicing', 30000)
            await pg.check('#pr-ahead')
            await pg.select_option('#pr-simSpeed', '1000')       # × 1000 jumps ahead: the whole print in a moment
            await pg.click('#btnPrSim')
            await wait_for(pg, "!!(P3S.link && P3S.link.ready)", 15000)
            check('send-ahead option reaches the link', await pg.evaluate('P3S.link.pingPong === false && P3S.link.budget === 63 && $id("pr-ahead").disabled'))
            await pg.click('#btnPrStart'); await asyncio.sleep(0.1)
            for bx in await pg.query_selector_all('#prCheck .pr-check input'): await bx.check()
            await pg.click('#btnPrCheckGo')
            ok = await wait_for(pg, 'P3S.link.job && P3S.link.job.done', 60000, 100)
            got = await pg.evaluate("""(() => { const want = gcodeCommands(P3S.jobResult.gcode).cmds, tr = P3S.link.io.trace.filter(c => c !== 'M105' && !/^M110/.test(c));
              return tr.length === want.length && tr.every((c, j) => c === want[j]); })()""")
            check('sending ahead: the whole print arrives exactly', ok and got)
            await pg.click('#btnPrConnect'); await asyncio.sleep(0.3); await pg.uncheck('#pr-ahead')
            cred = await pg.inner_text('#pr-credit-body') if await pg.evaluate("$id('pr-credits').open = true") else ''
            check('credits name Clipper with its Boost licence and the JSBN licence', 'Boost Software License' in cred and 'Tom Wu' in cred and 'Angus Johnson' in cred)

            # ---- look ----
            await pg.select_option('#pr-sample', 'ball'); await asyncio.sleep(0.2)
            await pg.select_option('#ps-support', 'plate')
            await pg.click('#btnPrSlice'); await wait_for(pg, '!!P3S.result && !P3S.slicing', 30000)
            sup = await pg.evaluate("Array.from(P3S.result.preview.type).filter(t => t === 5).length")
            check('supports from the plate under the ball', sup > 100, f'{sup} support moves')
            card = await pg.query_selector('#tab-print')
            await pg.evaluate("window.scrollTo(0, 0)")
            await card.screenshot(path=f'{OUT}/print_tab.png')
            await pg.evaluate("document.documentElement.dataset.theme = 'dark'; P3S.view.draw()")
            await (await pg.query_selector('#prCanvas')).screenshot(path=f'{OUT}/print_view_dark.png')
            await pg.evaluate("document.documentElement.dataset.theme = 'light'")
            phone = await ctx.new_page()
            await phone.set_viewport_size({'width': 390, 'height': 844})
            await phone.goto(f'http://localhost:{PORT}/app.html'); await phone.click('#nav-print'); await asyncio.sleep(0.3)
            over = await phone.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            await (await phone.query_selector('#tab-print')).screenshot(path=f'{OUT}/print_tab_phone.png')
            check('phone width: no sideways scrolling on the 3D print tab', over <= 0, f'{over}px')
            check('no page errors', not errors, '; '.join(errors[:3]))
            await b.close()
    finally:
        srv.terminate()
    bad = [n for n, c in results if not c]
    print(f'\n{len(results) - len(bad)}/{len(results)} passed' + (' — FAILED: ' + '; '.join(bad) if bad else ''))
    sys.exit(1 if bad else 0)

asyncio.run(main())
