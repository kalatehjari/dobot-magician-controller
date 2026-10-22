"""Browser test for shading: hatch lines inside closed shapes. Pattern, angle, spacing in mm at any
size, cross-hatch, angle per shape, filled shapes by colour (shapes on top hide lines, white stays
white, darker = closer), every closed shape vs every other level, outlines off, zig-zag joining, gap,
clicking shapes on the map, settings kept after reload, SVG download, and drawing on the simulated arm.
Runs the real app with the built-in simulator in headless Chromium.
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_shade.py"""
import asyncio, json, math, os, pathlib, re, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
sys.path.insert(0, str(HERE)); from fixtures import write_images; write_images(f'{SRV}/img')
PORT = 8779
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

FILLED = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120">'
          '<rect x="5" y="5" width="90" height="90" fill="#000"/>'
          '<circle cx="50" cy="50" r="20" fill="#fff"/>'
          '<rect x="105" y="5" width="90" height="90" fill="#808080"/>'
          '<path d="M110 102 L190 102 L150 117 Z" fill="none" stroke="#000"/></svg>')
SQUARE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="0" y="0" width="100" height="100" fill="none" stroke="#000"/></svg>'

# helpers run in the page: hatch segments of target i (in drawing units), their directions, and
# whether any hatch point falls inside a circle / rectangle (drawing units, from the SVG's own units)
HELP = """window.T = {
  toU: (x, y) => { const b = S.plot.sketch.srcBox; return { x: (x - b.cx) / b.L, y: (y - b.cy) / b.L }; },
  segs: (i) => { const c = SH.cache, out = []; c.strokes.forEach((s, k) => { if (i != null && c.owner[k] !== i) return; for (let j = 1; j < s.length; j++) out.push([s[j - 1], s[j]]); }); return out; },
  long: (i, min) => T.segs(i).filter(([a, b]) => Math.hypot(b.x - a.x, b.y - a.y) > min),
  angles: (i, min) => T.long(i, min).map(([a, b]) => { let d = Math.atan2(-(b.y - a.y), b.x - a.x) * 180 / Math.PI; d = ((d % 180) + 180) % 180; return Math.round(d) % 180; }),
  ownerAt: (x, y) => shadeTargetAt(SH.targets, T.toU(x, y)),
  pointsIn: (pred) => SH.cache.strokes.reduce((n, s) => n + s.filter(p => pred(p)).length, 0),
  segMidsIn: (pred) => T.segs().filter(([a, b]) => pred({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 })).length,
};"""

async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '-d', SRV], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(0.8)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--no-sandbox'])
            ctx = await b.new_context(viewport={'width': 1280, 'height': 1300}, accept_downloads=True)
            pg = await ctx.new_page(); errors = []
            pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
            pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
            ev = pg.evaluate
            await pg.goto(f'http://localhost:{PORT}/app.html')
            await ev("localStorage.removeItem('magician-shade')"); await pg.reload()
            ver = await ev("document.querySelector('.ver').textContent")
            check('version shows v1.3.0 or later', tuple(int(v) for v in ver.lstrip('v').split('.')) >= (1, 3, 0), ver)
            await pg.click('#btnSim'); await wait_for(ev, "!document.getElementById('autocal').hidden", 3000)
            await pg.click('[data-ac=start]'); await wait_for(ev, "AC.step === 'pen'", 15000)
            for _ in range(12):
                if await ev('S.pos.z') <= -58: break
                await pg.click('[data-dz="-10"]'); await wait_for(ev, '!AC.busy', 5000)
            await pg.click('[data-ac=paper]'); await wait_for(ev, "AC.step === 'done'", 10000)
            await pg.click('#autocalBody [data-ac=close]')
            await pg.click('#nav-plot'); await asyncio.sleep(0.3)
            await ev(HELP)

            # ---------- defaults ----------
            st = await ev("({ pat: document.getElementById('sh-pattern').value, dis: document.getElementById('sh-angle').disabled, txt: document.getElementById('sh-stats').textContent })")
            check('shading starts off, its controls greyed out', st['pat'] == 'off' and st['dis'])

            # ---------- filled shapes by colour ----------
            await pg.click('#tab-plot details summary')
            await pg.fill('#plot-text', FILLED); await pg.click('#btnLoadText'); await asyncio.sleep(0.5)
            plain = await ev('S.plot.stats.draw')
            await pg.select_option('#sh-pattern', 'lines'); await asyncio.sleep(0.3)
            await pg.fill('#sh-angleNum', '0'); await pg.press('#sh-angleNum', 'Enter'); await asyncio.sleep(0.3)
            await pg.select_option('#sh-which', 'filled'); await asyncio.sleep(0.3)
            r = await ev("""(() => { const c = SH.cache, blk = T.ownerAt(20, 20), gry = T.ownerAt(150, 50), tri = T.ownerAt(150, 108);
              const cen = T.toU(50, 50), rr = 19.5 / S.plot.sketch.srcBox.L;
              return { mode: c.mode, targets: c.targets, blk, gry, tri, nb: T.segs(blk).length, ng: T.segs(gry).length,
                inCircle: T.segMidsIn(p => Math.hypot(p.x - cen.x, p.y - cen.y) < rr) + T.pointsIn(p => Math.hypot(p.x - cen.x, p.y - cen.y) < rr),
                tone: document.getElementById('sh-tone').disabled, draw: S.plot.stats.draw }; })()""")
            check('"Filled shapes in the SVG" finds the three filled shapes (not the outlined triangle)', r['mode'] == 'filled' and r['targets'] == 3 and r['tri'] == -1)
            check('the white circle on top keeps the black square\'s lines out of it', r['inCircle'] == 0 and r['nb'] > 0)
            check('the grey square is shaded and drawing grew', r['ng'] > 0 and r['draw'] > plain * 3, f"{plain:.0f} → {r['draw']:.0f} mm of pen line")
            await pg.check('#sh-tone'); await asyncio.sleep(0.3)
            t2 = await ev("(() => { const blk = T.ownerAt(20, 20), gry = T.ownerAt(150, 50); return { b: T.long(blk, 0.01).length, g: T.long(gry, 0.01).length }; })()")
            check('darker colours get closer lines (grey ≈ half as many as black)', t2['b'] > 0 and 0.35 < t2['g'] / t2['b'] < 0.65, f"black {t2['b']} lines, grey {t2['g']}")
            await pg.uncheck('#sh-tone'); await pg.select_option('#sh-which', 'all'); await asyncio.sleep(0.3)
            a = await ev("(() => ({ mode: SH.cache.mode, targets: SH.cache.targets, tri: T.segs(T.ownerAt(150, 108)).length, circ: T.segs(T.ownerAt(50, 50)).length, tone: document.getElementById('sh-tone').disabled }))()")
            check('"Every closed shape" also shades the outlined triangle and the circle', a['mode'] == 'all' and a['tri'] > 0 and a['circ'] > 0 and a['tone'], f"{a['targets']} shapes")
            await pg.select_option('#sh-which', 'alt'); await asyncio.sleep(0.3)
            alt = await ev("T.segs(T.ownerAt(50, 50)).length")
            check('"Every other level" leaves the circle inside the square empty', alt == 0)
            await pg.select_option('#sh-which', 'all'); await asyncio.sleep(0.2)

            # ---------- angles (lines only, without the zig-zag links along the outlines) ----------
            await pg.uncheck('#sh-join'); await asyncio.sleep(0.3)
            ang = await ev("[...new Set(T.angles(null, 0.03))]")
            check('0° gives horizontal lines', ang == [0], f'{ang}')
            await pg.click('#shadeCard .sh-quick[data-a="90"]'); await asyncio.sleep(0.3)
            ang = await ev("[...new Set(T.angles(null, 0.03))]")
            check('the 90° quick button gives vertical lines', ang == [90] and await ev("document.querySelector('#shadeCard .sh-quick[data-a=\"90\"]').getAttribute('aria-pressed')") == 'true', f'{ang}')
            await pg.fill('#sh-angleNum', '30'); await pg.press('#sh-angleNum', 'Enter'); await asyncio.sleep(0.3)
            ang = await ev("[...new Set(T.angles(null, 0.03))]")
            check('any angle can be typed (30°)', ang == [30] and await ev("document.getElementById('sh-angle').value") == '30', f'{ang}')
            await pg.select_option('#sh-pattern', 'cross'); await asyncio.sleep(0.3)
            ang = sorted(await ev("[...new Set(T.angles(null, 0.03))]"))
            check('cross-hatch: two directions at right angles', ang == [30, 120], f'{ang}')
            await pg.select_option('#sh-pattern', 'tri'); await asyncio.sleep(0.3)
            ang = sorted(await ev("[...new Set(T.angles(null, 0.03))]"))
            check('three directions, 60° apart', ang == [30, 90, 150], f'{ang}')
            await pg.select_option('#sh-pattern', 'lines'); await pg.select_option('#sh-vary', 'alt'); await asyncio.sleep(0.3)
            per = await ev("SH.targets.list.map((_, i) => [...new Set(T.angles(i, 0.02))]).filter(v => v.length)")
            check('alternate: shapes next to each other get crossing directions', any(v == [30] for v in per) and any(v == [120] for v in per), f'{per}')
            await pg.select_option('#sh-vary', 'random'); await asyncio.sleep(0.3)
            r1 = await ev("SH.targets.list.map((_, i) => shadeAngles(i, SH.st)[0])")
            await pg.click('#btnShadeRandom'); await asyncio.sleep(0.3)
            r2 = await ev("SH.targets.list.map((_, i) => shadeAngles(i, SH.st)[0])")
            check('random angles, and Shuffle deals new ones', r1 != r2, f'{r1} → {r2}')
            await pg.select_option('#sh-vary', 'same'); await pg.check('#sh-join'); await asyncio.sleep(0.2)

            # ---------- spacing is millimetres on the paper ----------
            await pg.fill('#plot-text', SQUARE); await pg.click('#btnLoadText'); await asyncio.sleep(0.4)
            await pg.fill('#sh-angleNum', '0'); await pg.press('#sh-angleNum', 'Enter')
            await pg.fill('#sh-spacing', '2'); await pg.press('#sh-spacing', 'Enter'); await asyncio.sleep(0.3)
            async def spacing_mm():
                return await ev("""(() => { const f = placeXform(S.plot.place), L = T.long(null, 0.05).map(([a, b]) => [f(a), f(b)]);
                  const [p, q] = L[0], dx = q.x - p.x, dy = q.y - p.y, n = Math.hypot(dx, dy), nx = -dy / n, ny = dx / n;
                  const off = L.map(([a]) => a.x * nx + a.y * ny).sort((u, v) => u - v), gaps = off.slice(1).map((v, i) => v - off[i]).filter(g => g > 0.01);
                  return { min: Math.min(...gaps), max: Math.max(...gaps), n: L.length, size: S.plot.place.size }; })()""")
            for size in ('80', '50'):
                await pg.fill('#pl-sizeNum', size); await pg.press('#pl-sizeNum', 'Enter'); await asyncio.sleep(0.4)
                sp = await spacing_mm()
                check(f'line spacing stays 2 mm on the paper at {size} mm', abs(sp['min'] - 2) < 0.02 and abs(sp['max'] - 2) < 0.02, f"{sp['n']} lines, gaps {sp['min']:.3f}–{sp['max']:.3f} mm")

            # ---------- joining, outlines, gap ----------
            j1 = await ev('({ lifts: S.plot.stats.lifts, strokes: SH.cache.strokes.length, lines: SH.cache.lines })')
            await pg.uncheck('#sh-join'); await asyncio.sleep(0.3)
            j0 = await ev('({ lifts: S.plot.stats.lifts, strokes: SH.cache.strokes.length })')
            check('zig-zags save pen lifts', j1['strokes'] <= 2 and j0['strokes'] == j1['lines'] and j0['lifts'] > j1['lifts'] + 10, f"{j0['lifts']} → {j1['lifts']} pen lifts")
            await pg.check('#sh-join'); await pg.uncheck('#sh-outline'); await asyncio.sleep(0.3)
            o = await ev('({ all: S.plot.order.all.length, sh: SH.cache.strokes.length, ok: !!S.plot.ops })')
            check('with outlines off only the shading is drawn', o['ok'] and o['all'] == o['sh'])
            await pg.check('#sh-outline')
            await pg.fill('#sh-inset', '1'); await pg.press('#sh-inset', 'Enter'); await asyncio.sleep(0.3)
            g = await ev("""(() => { const f = placeXform(S.plot.place), fr = placeFrame(S.plot.sketch, S.plot.place), xs = fr.map(p => p.x), ys = fr.map(p => p.y);
              let m = Infinity; for (const s of SH.cache.strokes) for (const p of s) { const q = f(p); m = Math.min(m, q.x - Math.min(...xs), Math.max(...xs) - q.x, q.y - Math.min(...ys), Math.max(...ys) - q.y); } return m; })()""")
            check('a 1 mm gap keeps the lines 1 mm inside the outline', 0.999 < g < 1.05, f'closest {g:.3f} mm')
            await pg.fill('#sh-inset', '0'); await pg.press('#sh-inset', 'Enter'); await asyncio.sleep(0.2)

            # ---------- click shapes on the map ----------
            await ev('S.plot.objects = []; S.plot.sel = null; onSelectionChange()')   # a fresh copy on an empty sheet
            await pg.fill('#plot-text', FILLED); await pg.click('#btnLoadText'); await asyncio.sleep(0.4)
            await pg.locator('#plotCanvas').scroll_into_view_if_needed(); await asyncio.sleep(0.3)
            async def screen_of(x, y):
                return await ev(f"""(() => {{ const u = T.toU({x}, {y}), q = placeXform(S.plot.place)(u), v = plotView(), [sx, sy] = v.toS(q.x, q.y), r = plotCv.getBoundingClientRect(); return [r.left + sx, r.top + sy]; }})()""")
            gx, gy = await screen_of(150, 50)
            gi = await ev('T.ownerAt(150, 50)')
            await pg.mouse.click(gx, gy); await asyncio.sleep(0.4)
            c1 = await ev(f"({{ ov: SH.ov.get({gi}), n: SH.ov.size, ang: [...new Set(T.angles({gi}, 0.02))], log: [...document.querySelectorAll('#log div')].pop().textContent }})")
            check('clicking a shape on the map turns its lines 45°', c1['ov'] == 'r45' and c1['n'] == 1 and c1['ang'] == [45], json.dumps(c1))
            await pg.mouse.click(gx, gy); await asyncio.sleep(0.3)
            await pg.mouse.click(gx, gy); await asyncio.sleep(0.3)
            await pg.mouse.click(gx, gy); await asyncio.sleep(0.3)
            c2 = await ev(f"({{ ov: SH.ov.get({gi}), ang: [...new Set(T.angles({gi}, 0.02))].sort((a, b) => a - b) }})")
            check('more clicks: 90°, 135°, then cross-hatched', c2['ov'] == 'cross' and c2['ang'] == [0, 90], f'{c2}')
            await pg.mouse.click(gx, gy); await asyncio.sleep(0.3)
            c3 = await ev(f"({{ ov: SH.ov.get({gi}), n: T.segs({gi}).length, other: T.segs(T.ownerAt(20, 20)).length }})")
            check('next click leaves that shape empty; the others keep their lines', c3['ov'] == 'off' and c3['n'] == 0 and c3['other'] > 0)
            await pg.mouse.click(gx, gy); await asyncio.sleep(0.3)
            check('one more click returns it to the settings', await ev(f'!SH.ov.has({gi}) && T.segs({gi}).length > 0'))
            await pg.mouse.click(gx, gy); await asyncio.sleep(0.3)
            check('Reset shape choices is offered once a shape is set by hand', await ev("!document.getElementById('btnShadeReset').disabled"))
            before = await ev('S.plot.place')
            await pg.mouse.move(gx, gy); await pg.mouse.down()
            for i in range(1, 9): await pg.mouse.move(gx + 5 * i, gy); await asyncio.sleep(0.02)
            await pg.mouse.up(); await asyncio.sleep(0.4)
            after = await ev('S.plot.place')
            check('dragging still moves the drawing and does not change shapes', abs(after['cy'] - before['cy']) > 5 and await ev(f"SH.ov.get({gi})") == 'r45')
            await pg.click('#btnShadeReset'); await asyncio.sleep(0.3)
            check('Reset clears the hand-set shapes', await ev('SH.ov.size === 0 && document.getElementById("btnShadeReset").disabled'))

            # ---------- a library drawing, then download, remember, draw ----------
            await pg.click('#lib-grid .lib-item[data-id="art/heart-tiles"]'); await asyncio.sleep(0.5)
            await pg.select_option('#sh-vary', 'step30'); await asyncio.sleep(0.3)
            h = await ev("({ shaded: SH.cache.shaded, targets: SH.cache.targets, txt: document.getElementById('sh-stats').textContent, dirs: new Set(T.angles(null, 0.01)).size })")
            check('the heart tiles: every heart shaded, at turning angles', h['shaded'] == h['targets'] == 54 and h['dirs'] >= 5, h['txt'])
            async with pg.expect_download() as dl_info:
                await pg.click('#btnShadeSvg')
            dl = await dl_info.value
            txt = open(await dl.path()).read()
            check('Download SVG with shading saves outlines and shading as pen paths in mm', dl.suggested_filename == 'Heart-tiles-shaded.svg' and 'id="shading"' in txt and 'id="outlines"' in txt and re.search(r'width="[\d.]+mm"', txt), dl.suggested_filename)
            st_saved = await ev("JSON.parse(localStorage.getItem('magician-shade'))")
            await pg.reload(); await asyncio.sleep(0.5)
            st_back = await ev("({ pat: document.getElementById('sh-pattern').value, vary: document.getElementById('sh-vary').value, sp: document.getElementById('sh-spacing').value, st: SH.st })")
            check('shading settings are remembered after a reload', st_back['pat'] == 'lines' and st_back['vary'] == 'step30' and st_back['st'] == st_saved)
            await pg.click('#btnSim'); await asyncio.sleep(0.5)
            if await ev("!document.getElementById('autocal').hidden"): await ev("closeAutoCal()")
            await pg.click('#nav-plot'); await asyncio.sleep(0.3); await ev(HELP)
            await pg.click('#lib-grid .lib-item[data-id="objects/balloons"]'); await asyncio.sleep(0.5)
            ok = await ev('!!S.plot.ops && SH.cache.lines > 0')
            await ev("S.limits.penSet = true")
            await pg.click('#btnDraw'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 90000)
            job = await ev('(() => { const j = S.paper.jobs[S.paper.jobs.length - 1]; return j ? { done: j.done, n: j.cmds.length } : null; })()')
            check('a shaded drawing draws to the end on the simulated arm', ok and job and job['done'], json.dumps(job))

            # ---------- look ----------
            await ev("document.querySelector('header').style.position = 'relative'")
            await (await pg.query_selector('#shadeCard')).screenshot(path=str(OUT / 'shade_card.png'))
            await pg.emulate_media(color_scheme='dark'); await asyncio.sleep(0.2)
            await (await pg.query_selector('#shadeCard')).screenshot(path=str(OUT / 'shade_card_dark.png'))
            await pg.emulate_media(color_scheme='light')
            await pg.set_viewport_size({'width': 390, 'height': 900}); await asyncio.sleep(0.3)
            check('the shading card fits a phone-width screen', await ev("document.documentElement.scrollWidth <= window.innerWidth + 1"))
            await (await pg.query_selector('#shadeCard')).screenshot(path=str(OUT / 'shade_card_phone.png'))
            check('no page errors', not errors, '; '.join(errors[:3]))
            await b.close()
    finally:
        srv.terminate()
    bad = [n for n, ok in results if not ok]
    print(f'\n{len(results) - len(bad)}/{len(results)} passed' + (f'; FAILED: {bad}' if bad else ''))
    sys.exit(1 if bad else 0)

asyncio.run(main())
