"""Browser test: free placement (size, any rotation, mirror, drag in the green zone, handles, keyboard),
pen-up travel around the base, live pen laser dot and red drawn lines. Runs the real app against the
built-in kinematic simulator in headless Chromium.
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_placement.py"""
import asyncio, json, math, pathlib, re, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
sys.path.insert(0, str(HERE)); from fixtures import write_images; write_images(f'{SRV}/img')
PORT = 8771
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

# exact check, in the page, that every pen-down line of the built path is inside the green zone
INSIDE = """(() => { const z = drawZone(), ops = S.plot.ops; let prev = S.plot.start, worst = Infinity, bad = 0;
  for (const o of ops) { if (o.pen) { const r = Math.hypot(o.x, o.y), th = Math.atan2(o.y, o.x) / RAD;
      if (r > z.rOut + 1e-6 || th < z.thMin - 1e-6 || th > z.thMax + 1e-6) bad++;
      const d = segDist0(prev.x, prev.y, o.x, o.y); worst = Math.min(worst, d); if (d < z.rIn - 1e-6) bad++; }
    prev = o; }
  return { bad, worst, rIn: z.rIn, ok: bad === 0 && S.plot.placeOk && S.plot.opsVer === S.plot.placeVer }; })()"""
CENTRE = """(() => { const v = plotView(), g = frameGeom(v), r = plotCv.getBoundingClientRect();
  return { c: [r.left + g.c[0], r.top + g.c[1]], knob: [r.left + g.knob[0], r.top + g.knob[1]], tr: [r.left + g.fr[1][0], r.top + g.fr[1][1]],
           base: [r.left + v.bx, r.top + v.by], k: v.k }; })()"""
# red pixels (laser colour) around a robot point on the plotter canvas
RED_AT = """([x, y, rad]) => { const v = plotView(), [sx, sy] = v.toS(x, y), d = window.devicePixelRatio || 1, c = plotCv.getContext('2d');
  const R = Math.round(rad * d), img = c.getImageData(Math.round(sx * d) - R, Math.round(sy * d) - R, 2 * R + 1, 2 * R + 1).data; let n = 0;
  for (let i = 0; i < img.length; i += 4) if (img[i] > 190 && img[i + 1] < 110 && img[i + 2] < 110 && img[i + 3] > 100) n++;
  return n; }"""

async def drag(pg, a, b, steps=12):
    await pg.mouse.move(*a); await pg.mouse.down()
    for i in range(1, steps + 1):
        await pg.mouse.move(a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps)
        await asyncio.sleep(0.02)
    await pg.mouse.up(); await asyncio.sleep(0.35)

async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '-d', SRV], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(0.8)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--no-sandbox'])
            ctx = await b.new_context(viewport={'width': 1280, 'height': 1300})
            pg = await ctx.new_page(); errors = []
            pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
            pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
            ev = pg.evaluate
            await pg.goto(f'http://localhost:{PORT}/app.html')
            check('version tag is shown', re.search(r'v\d+\.\d+', await pg.inner_text('header h1')))

            # ---------- calibrate (simulator) ----------
            await pg.click('#btnSim')
            await wait_for(ev, "!document.getElementById('autocal').hidden", 3000)
            await pg.click('[data-ac=start]')
            await wait_for(ev, "AC.step === 'pen' || AC.step === 'error'", 15000)
            for _ in range(12):
                if await ev('S.pos.z') <= -68: break
                await pg.click('[data-dz="-10"]'); await wait_for(ev, '!AC.busy', 5000)
            for _ in range(10):
                if await ev('S.pos.z') <= -71.5: break
                await pg.click('[data-dz="-0.5"]'); await wait_for(ev, '!AC.busy', 5000)
            await pg.click('[data-ac=paper]')
            await wait_for(ev, "AC.step === 'done'", 10000)
            await pg.click('#autocalBody [data-ac=close]')
            await pg.click('#nav-plot'); await asyncio.sleep(0.3)
            z = await ev('drawZone()')
            check('green zone comes from the arm geometry at pen height', z['fromModel'] and z['rOut'] - z['rIn'] > 90, f"{z['rIn']:.0f}–{z['rOut']:.0f} mm, ±{z['thMax']:.1f}°")
            green = await ev("""(() => { const z = drawZone(), v = plotView(), r = (z.rIn + z.rOut) / 2, a = 70 * RAD, [sx, sy] = v.toS(r * Math.cos(a), r * Math.sin(a));
                const d = window.devicePixelRatio || 1, px = plotCv.getContext('2d').getImageData(Math.round(sx * d), Math.round(sy * d), 1, 1).data;
                return [px[0], px[1], px[2], px[3]]; })()""")
            check('the zone is drawn in green', green[1] > green[0] + 5 and green[1] > green[2], str(green))

            # ---------- load an SVG: default placement ----------
            await pg.click('#tab-plot details summary')
            await pg.fill('#plot-text', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 100"><rect x="5" y="5" width="150" height="90"/><path d="M20 80 L80 20 L140 80"/><circle cx="40" cy="40" r="12"/></svg>')
            await pg.click('#btnLoadText'); await asyncio.sleep(0.6)
            ins = await ev(INSIDE); pl = await ev('S.plot.place'); best = await ev('placeTargets()[0].size')
            check('a new drawing is centred and sized to 90 % of the largest', ins['ok'] and abs(pl['cy']) < 1e-6 and abs(pl['size'] - math.floor(best * 0.9)) < 1e-6,
                  f"{pl['size']:.0f} mm of {best:.0f} mm, every line inside (closest to base {ins['worst']:.1f} mm, zone from {ins['rIn']:.1f})")

            # ---------- size ----------
            await pg.fill('#pl-sizeNum', '1000'); await pg.press('#pl-sizeNum', 'Enter'); await asyncio.sleep(0.4)
            s_big = await ev('S.plot.place.size'); anymax = await ev('Math.max(...placeTargets().filter(Boolean).map(t => t.size))')
            ins = await ev(INSIDE)
            check('asking for 1000 mm gives the largest that fits', ins['ok'] and s_big <= anymax + 1e-6 and s_big > anymax * 0.98, f'{s_big:.1f} mm (largest {anymax:.1f})')
            await pg.fill('#pl-sizeNum', '80'); await pg.press('#pl-sizeNum', 'Enter'); await asyncio.sleep(0.4)
            check('size in mm is exact', abs(await ev('S.plot.place.size') - 80) < 1e-9 and (await ev(INSIDE))['ok'],
                  await pg.inner_text('#pl-sizeVal'))
            sl = await ev("""(() => { const el = document.getElementById('pl-size'); el.value = 120; el.dispatchEvent(new Event('input')); el.dispatchEvent(new Event('change')); return S.plot.place.size; })()""")
            await asyncio.sleep(0.3)
            check('the size slider resizes it', abs(sl - 120) < 1e-9 and (await ev(INSIDE))['ok'], f'{sl} mm')

            # ---------- free rotation ----------
            await pg.fill('#pl-rotNum', '37'); await pg.press('#pl-rotNum', 'Enter'); await asyncio.sleep(0.4)
            ang = await ev('S.plot.place.angle'); ins = await ev(INSIDE)
            edge = await ev("""(() => { const fr = placeFrame(S.plot.sketch, S.plot.place), dx = fr[1].x - fr[0].x, dy = fr[1].y - fr[0].y;
                return Math.atan2(-dx, -dy) / RAD; })()""")   # top edge direction on screen (screen x = −y, screen y = −x)
            check('any rotation: 37° clockwise, still inside the zone', abs(ang - 37) < 1e-9 and abs(edge - 37) < 1e-6 and ins['ok'], f'top edge at {edge:.2f}°')
            await pg.screenshot(path=str(OUT / 'rotated.png'), full_page=True)
            await ev("""(() => { const el = document.getElementById('pl-rot'); el.value = -90; el.dispatchEvent(new Event('input')); el.dispatchEvent(new Event('change')); })()""")
            await asyncio.sleep(0.3)
            check('rotation slider turns it', abs(await ev('S.plot.place.angle') + 90) < 1e-9 and (await ev(INSIDE))['ok'])
            await pg.click('#btnRot90'); await asyncio.sleep(0.3)
            a90 = await ev('S.plot.place.angle')
            check('↻ 90° button turns it a quarter clockwise', abs(a90) < 1e-9 and (await ev(INSIDE))['ok'], f'−90° → {a90}°')
            await pg.check('#plot-mirror'); await asyncio.sleep(0.3)
            check('mirror', await ev('S.plot.place.mirror') and (await ev(INSIDE))['ok'])
            await pg.uncheck('#plot-mirror'); await asyncio.sleep(0.3)

            # ---------- drag to move ----------
            await pg.fill('#pl-sizeNum', '70'); await pg.press('#pl-sizeNum', 'Enter')
            await pg.click('#btnPlCentre'); await asyncio.sleep(0.3)
            g = await ev(CENTRE); before = await ev('S.plot.place')
            await drag(pg, g['c'], (g['c'][0] + 90, g['c'][1]))
            after = await ev('S.plot.place'); ins = await ev(INSIDE)
            check('dragging the drawing moves it on the paper (90 px right = robot −Y)', ins['ok'] and abs((after['cy'] - before['cy']) + 90 / g['k']) < 0.6 and abs(after['cx'] - before['cx']) < 0.6,
                  f"moved {after['cy'] - before['cy']:.1f} mm (expected {-90 / g['k']:.1f})")
            g = await ev(CENTRE)
            await drag(pg, g['c'], g['base'], steps=20)
            after2 = await ev('S.plot.place'); ins = await ev(INSIDE)
            r2 = math.hypot(after2['cx'], after2['cy'])
            check('dragging onto the base: it stops at the edge of the green zone', ins['ok'] and r2 > z['rIn'], f"centre now {r2:.0f} mm from the base, closest line {ins['worst']:.1f} mm")
            g = await ev(CENTRE)
            await drag(pg, g['c'], (g['c'][0] + 2000, g['c'][1] - 2000), steps=20)
            check('dragging far outside keeps it inside', (await ev(INSIDE))['ok'])

            # ---------- handles ----------
            await pg.click('#btnPlCentre'); await asyncio.sleep(0.3)
            s0 = await ev('S.plot.place.size'); g = await ev(CENTRE)
            out = lambda g, px: (g['tr'][0] + px * (g['tr'][0] - g['c'][0]) / math.hypot(g['tr'][0] - g['c'][0], g['tr'][1] - g['c'][1]),
                                 g['tr'][1] + px * (g['tr'][1] - g['c'][1]) / math.hypot(g['tr'][0] - g['c'][0], g['tr'][1] - g['c'][1]))
            await drag(pg, g['tr'], out(g, 30))
            s1 = await ev('S.plot.place.size')
            check('dragging a corner outwards makes it bigger', s1 > s0 + 5 and (await ev(INSIDE))['ok'], f'{s0:.0f} → {s1:.0f} mm')
            g = await ev(CENTRE)
            await drag(pg, g['tr'], out(g, 800))
            s2 = await ev('S.plot.place.size'); here = await ev('maxSizeAt(plProbe(), S.plot.place.cx, S.plot.place.cy, drawZone(), plotPad())')
            check('…and stops at the largest that fits there', (await ev(INSIDE))['ok'] and s2 > s1 and s2 >= here * 0.99, f'{s2:.0f} mm (largest here {here:.0f})')
            await pg.fill('#pl-sizeNum', '70'); await pg.press('#pl-sizeNum', 'Enter'); await asyncio.sleep(0.3)
            g = await ev(CENTRE); a0 = await ev('S.plot.place.angle')
            cx, cy = g['c']; kx, ky = g['knob']; rr = math.hypot(kx - cx, ky - cy); ka = math.atan2(ky - cy, kx - cx)
            pts = [(cx + rr * math.cos(ka + math.radians(d)), cy + rr * math.sin(ka + math.radians(d))) for d in range(0, 61, 5)]
            await pg.mouse.move(kx, ky); await pg.mouse.down()
            for q in pts: await pg.mouse.move(*q); await asyncio.sleep(0.03)
            await pg.mouse.up(); await asyncio.sleep(0.4)
            a1 = await ev('S.plot.place.angle')
            turned = (a1 - a0 + 540) % 360 - 180
            check('dragging the round knob turns it (60° clockwise)', abs(turned - 60) < 1.5 and (await ev(INSIDE))['ok'], f'{a0:.1f}° → {a1:.1f}° ({turned:+.1f}°)')

            # ---------- keyboard ----------
            await pg.focus('#plotCanvas'); p0 = await ev('S.plot.place')
            for _ in range(3): await pg.keyboard.press('ArrowUp')
            await pg.keyboard.press('Shift+ArrowLeft'); await pg.keyboard.press(']'); await pg.keyboard.press('+')
            await asyncio.sleep(0.6)
            p1 = await ev('S.plot.place')
            check('keyboard: arrows move it, ] turns it, + makes it bigger', abs(p1['cx'] - p0['cx'] - 3) < 1e-6 and abs(p1['cy'] - p0['cy'] - 10) < 1e-6 and abs(p1['angle'] - p0['angle'] - 1) < 1e-6 and abs(p1['size'] - p0['size'] - 1) < 1e-6 and (await ev(INSIDE))['ok'],
                  f"Δx {p1['cx'] - p0['cx']:.1f} Δy {p1['cy'] - p0['cy']:.1f} Δangle {p1['angle'] - p0['angle']:.1f} Δsize {p1['size'] - p0['size']:.1f}")

            # ---------- centre / largest ----------
            await pg.click('#btnPlCentre'); await asyncio.sleep(0.3)
            check('Centre puts it on the forward axis', abs(await ev('S.plot.place.cy')) < 1e-9 and (await ev(INSIDE))['ok'])
            await pg.fill('#pl-rotNum', '0'); await pg.press('#pl-rotNum', 'Enter'); await asyncio.sleep(0.3)
            await pg.click('#btnPlLargest'); await asyncio.sleep(0.4)
            big = await ev('S.plot.place.size'); t = await ev('placeTargets()[0].size')
            check('Largest makes it as big as the zone allows', abs(big - math.floor(t * 0.999 * 10) / 10) < 1e-6 and (await ev(INSIDE))['ok'], f'{big:.1f} mm')
            await pg.fill('#plot-margin', '12'); await pg.press('#plot-margin', 'Enter'); await asyncio.sleep(0.5)
            check('a larger safety margin shrinks the zone and the drawing is refitted', (await ev(INSIDE))['ok'] and await ev('S.plot.place.size') < big, f"{await ev('S.plot.place.size'):.1f} mm")
            await pg.fill('#plot-margin', '6'); await pg.press('#plot-margin', 'Enter'); await asyncio.sleep(0.4)
            await pg.screenshot(path=str(OUT / 'plot.png'), full_page=True)

            # ---------- live pen + red drawn lines ----------
            await pg.fill('#pl-sizeNum', '90'); await pg.press('#pl-sizeNum', 'Enter')
            await pg.fill('#pl-rotNum', '20'); await pg.press('#pl-rotNum', 'Enter'); await asyncio.sleep(0.4)
            # the simulator moves instantly, so hold its queue after 8 pen moves, like a real arm part-way through
            await ev("""(() => { const io = S.dev.io, orig = io.exchange.bind(io); let n = 0;
                io.exchange = async f => { if (f[3] === 91 && ++n === 8) io.st.paused = true; return orig(f); }; })()""")
            await pg.click('#btnDraw')
            if not await wait_for(ev, 'S.running && S.dev.io.st.paused', 5000, 20):
                print('DEBUG log:', (await pg.inner_text('#log'))[:600])
            await pg.click('#btnPause'); await asyncio.sleep(0.6)
            job = await ev('(() => { const j = S.paper.jobs[S.paper.jobs.length - 1]; return { k: j.k, t: j.t, n: j.cmds.length, active: j.active, ke: j.ke }; })()')
            check('while drawing, progress follows the arm', job['active'] and 3 < job['k'] < job['n'] - 3, json.dumps(job))
            await asyncio.sleep(0.3)
            laser = await ev(RED_AT, [await ev('S.pos.x'), await ev('S.pos.y'), 4])
            check('the pen shows as a red laser dot', laser >= 12, f'{laser} red pixels at the pen')
            seg = await ev("""(() => { const j = S.paper.jobs[S.paper.jobs.length - 1]; let best = null;
                for (let i = 1; i < j.k; i++) { const a = j.cmds[i - 1], b = j.cmds[i];
                  if (Math.abs(a.z - j.zD) < 0.5 && Math.abs(b.z - j.zD) < 0.5 && Math.hypot(b.x - a.x, b.y - a.y) > 3 && Math.hypot((a.x + b.x) / 2 - S.pos.x, (a.y + b.y) / 2 - S.pos.y) > 12) best = [(a.x + b.x) / 2, (a.y + b.y) / 2]; }
                return best; })()""")
            red_done = await ev(RED_AT, [seg[0], seg[1], 2]) if seg else 0
            todo = await ev("""(() => { const j = S.paper.jobs[S.paper.jobs.length - 1];
                for (let i = j.cmds.length - 1; i > j.k + 3; i--) { const a = j.cmds[i - 1], b = j.cmds[i];
                  if (Math.abs(a.z - j.zD) < 0.5 && Math.abs(b.z - j.zD) < 0.5 && Math.hypot(b.x - a.x, b.y - a.y) > 3) return [(a.x + b.x) / 2, (a.y + b.y) / 2]; }
                return null; })()""")
            red_todo = await ev(RED_AT, [todo[0], todo[1], 1]) if todo else -1
            check('drawn lines are red; lines still to draw are not', red_done >= 3 and red_todo == 0, f'{red_done} red px on a drawn line, {red_todo} on a line still to draw')
            await pg.screenshot(path=str(OUT / 'drawing.png'), full_page=False, clip={'x': 0, 'y': 0, 'width': 1280, 'height': 1300})
            await pg.click('#btnPause'); await wait_for(ev, '!S.running', 60000)
            done = await ev('(() => { const j = S.paper.jobs[S.paper.jobs.length - 1]; return { done: j.done, k: j.k, n: j.cmds.length }; })()')
            red_end = await ev(RED_AT, [todo[0], todo[1], 2]) if todo else 0
            check('when finished, the whole drawing is red', done['done'] and red_end >= 3 and await ev('S.dev.io.st.alarms.size') == 0, f'{red_end} red px on the last line')
            await pg.click('#btnTestSquare'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 30000)
            check('earlier drawings stay red on the same sheet', await ev('S.paper.jobs.length') == 2 and await ev('S.paper.jobs.every(j => j.done)'))
            sq = await ev("""(() => { const j = S.paper.jobs[1], pl = S.plot.place, inv = placeInverse(pl), sk = S.plot.sketch;
                const pts = j.cmds.filter(c => Math.abs(c.z - j.zD) < 0.5);
                const clear = pts.every(p => { const u = inv(p); return Math.abs(u.x) > sk.w / 2 || Math.abs(u.y) > sk.h / 2; });
                const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
                return { clear, w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys),
                         gap: Math.hypot((Math.max(...xs) + Math.min(...xs)) / 2 - pl.cx, (Math.max(...ys) + Math.min(...ys)) / 2 - pl.cy) }; })()""")
            check('the test square goes beside the drawing, not on top of it', sq['clear'] and abs(sq['w'] - 20) < 0.01 and abs(sq['h'] - 20) < 0.01 and sq['gap'] < 120,
                  f"{sq['w']:.0f} × {sq['h']:.0f} mm, {sq['gap']:.0f} mm from the drawing's centre")
            await asyncio.sleep(0.3)
            await pg.screenshot(path=str(OUT / 'done.png'), full_page=True)
            await pg.click('#btnNewSheet'); await asyncio.sleep(0.3)
            check('New sheet clears the red lines', await ev('S.paper.jobs.length') == 0 and await ev(RED_AT, [todo[0], todo[1], 2]) == 0)

            # ---------- pen-up travel goes around the base ----------
            await pg.fill('#plot-text', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 40"><rect x="0" y="5" width="30" height="30"/><rect x="370" y="5" width="30" height="30"/></svg>')
            await pg.click('#btnLoadText'); await asyncio.sleep(0.5)
            ok = await ev("""(() => { applyWant({ cx: 125, cy: 0, size: 440, angle: 0, mirror: false }); buildPlot(); return S.plot.place; })()""")
            plan = await ev("""(() => { const c = plotCommands(S.plot.ops, S.limits, S.plot.start, { cp: true, core: drawZone().rIn });
                const naive = plotCommands(S.plot.ops, S.limits, S.plot.start, { cp: true });
                return { cuts: coreCuts(c, S.plot.start), naive: coreCuts(naive, S.plot.start), n: c.length, n0: naive.length }; })()""")
            check('two shapes either side of the base: allowed, the pen-up hop follows the arc', abs(ok['cx'] - 125) < 1e-6 and (await ev(INSIDE))['ok'] and plan['cuts'] == 0 and plan['naive'] >= 1 and plan['n'] > plan['n0'],
                  f"straight hop would cut {plan['naive']}×; arc adds {plan['n'] - plan['n0']} waypoints")
            await pg.click('#btnDraw'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 30000)
            check('…and it draws without a limit alarm', await ev('S.dev.io.st.alarms.size') == 0 and await ev('S.paper.jobs.length') == 1 and await ev('S.paper.jobs[0].done'))

            # ---------- re-tracing a picture keeps it where it is ----------
            await pg.set_input_files('#plot-file', f'{SRV}/img/shapes.png')
            await wait_for(ev, 'TR.result && S.plot.ops', 10000); await asyncio.sleep(0.4)
            await pg.focus('#plotCanvas')
            for _ in range(4): await pg.keyboard.press('Shift+ArrowRight')
            await asyncio.sleep(0.6)
            m0 = await ev('(() => { const pl = S.plot.place, sk = S.plot.sketch, f = placeXform(pl); const u = { x: (100 - sk.srcBox.cx) / sk.srcBox.L, y: (100 - sk.srcBox.cy) / sk.srcBox.L }; return { p: f(u), k: pl.size / sk.srcBox.L }; })()')
            await pg.fill('#tr-detail', '9'); await pg.dispatch_event('#tr-detail', 'input'); await asyncio.sleep(0.6)
            await pg.click('#btnTraceUse'); await asyncio.sleep(0.6)
            m1 = await ev('(() => { const pl = S.plot.place, sk = S.plot.sketch, f = placeXform(pl); const u = { x: (100 - sk.srcBox.cx) / sk.srcBox.L, y: (100 - sk.srcBox.cy) / sk.srcBox.L }; return { p: f(u), k: pl.size / sk.srcBox.L }; })()')
            check('re-tracing the same picture keeps its position and scale on the paper', abs(m0['k'] - m1['k']) < 1e-9 and math.hypot(m0['p']['x'] - m1['p']['x'], m0['p']['y'] - m1['p']['y']) < 1e-6,
                  f"{m0['k']:.4f} mm/px, pixel (100,100) at {m1['p']['x']:.1f}, {m1['p']['y']:.1f}")

            await pg.click('#nav-mouse'); await asyncio.sleep(0.4)
            mouse_red = await ev("""(() => { const cv = document.getElementById('mouseCanvas'), v = viewOf(cv), [sx, sy] = v.toS(S.pos.x, S.pos.y), d = window.devicePixelRatio || 1;
                const img = cv.getContext('2d').getImageData(Math.round(sx * d) - 3, Math.round(sy * d) - 3, 7, 7).data; let n = 0;
                for (let i = 0; i < img.length; i += 4) if (img[i] > 190 && img[i + 1] < 110 && img[i + 2] < 110) n++; return n; })()""")
            check('the Mouse tab shows the same red laser dot', mouse_red >= 8, f'{mouse_red} red px')
            real = [e for e in errors if 'favicon' not in e]
            check('no page errors', not real, ' | '.join(real[:4]))
            await b.close()
    finally:
        srv.terminate()
    fails = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fails)}/{len(results)} passed" + (f"; FAILED: {fails}" if fails else ''))

asyncio.run(main())
