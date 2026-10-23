"""Browser test: safe zone (clicked polygon), pen height re-set and saved heights, Clear plotter,
Redraw with copies, and the safety lock (gates, trimming, following, the check under every move).
Runs the real app against the built-in kinematic simulator in headless Chromium.
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_zone.py"""
import asyncio, math, pathlib, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
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

# every move the app sends to the (simulated) arm, decoded
RECORD = """(() => { window.SENT = []; const io = S.dev.io, ex = io.exchange.bind(io);
  io.exchange = async f => { const fr = parseFrames(f).frames[0];
    if (fr.id === 84 || fr.id === 91) { const dv = new DataView(fr.params.buffer, fr.params.byteOffset, fr.params.byteLength);
      SENT.push({ id: fr.id, mode: fr.params[0], x: dv.getFloat32(1, true), y: dv.getFloat32(5, true), z: dv.getFloat32(9, true) }); }
    if (fr.id === 31) SENT.push({ home: true });
    return ex(f); }; return true; })()"""
# are the moves sent since mark all inside the allowed area (pen-up too)? starting from where the arm was
SENT_INSIDE = """([from, tol]) => { const R = allowedRegion(); let prev = from, bad = 0, n = 0, worst = 0;
  for (const c of SENT.slice(SENTMARK)) { if (c.home) { prev = null; continue; } n++;
    if (prev && !regionSegInside(R, prev.x, prev.y, c.x, c.y, tol)) { bad++; worst = Math.max(worst, lockDepth(R, prev, c, -1e9)); }
    prev = c; }
  return { n, bad, worst }; }"""
# exact: every pen-down line of the built path keeps the margin inside the safe polygon
IN_POLY = """(() => { const z = drawZone(), pp = z.pq; if (!pp || !S.plot.ops) return { ok: false, why: 'no zone or path' };
  let prev = S.plot.start, worst = Infinity, out = 0;
  for (const o of S.plot.ops) { if (o.pen && prev) { if (!polyHas(pp, o.x, o.y)) out++;
      for (let k = 0; k < pp.n; k++) worst = Math.min(worst, Math.sqrt(segSegD2(prev.x, prev.y, o.x, o.y, pp.e[4*k], pp.e[4*k+1], pp.e[4*k+2], pp.e[4*k+3]))); }
    prev = o; }
  return { ok: out === 0 && worst >= z.margin - 0.01, worst, out, margin: z.margin }; })()"""

async def map_click(pg, ev, x, y, **kw):
    p = await ev(f"(() => {{ const v = plotView(), r = plotCv.getBoundingClientRect(), [sx, sy] = v.toS({x}, {y}); return [r.left + sx, r.top + sy]; }})()")
    await pg.mouse.click(p[0], p[1], **kw); await asyncio.sleep(0.08)
    return p

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
            await ev("localStorage.clear()"); await pg.reload()

            # ---------- calibrate on the simulator ----------
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
            await ev(RECORD)
            z = await ev('drawZone()')
            check('calibrated on the simulator; no safe zone yet', z['fromModel'] and 'poly' not in z and S_OK(await ev('S.homedAt > 0')), f"{z['rIn']:.0f}–{z['rOut']:.0f} mm")

            # ---------- draw a safe zone by clicking (an L: the notch is forbidden) ----------
            await pg.locator('#plotCanvas').scroll_into_view_if_needed(); await asyncio.sleep(0.2)
            ri, ro = z['rIn'], z['rOut']
            L = [(ri - 15, -70), (ro + 10, -70), (ro + 10, 75), (ri + 60, 75), (ri + 60, -10), (ri - 15, -10)]
            await pg.click('#btnSzDraw')
            check('drawing mode: Done, Cancel and Add pen position are offered', await ev("SZ.mode === 'draw' && !document.getElementById('btnSzDone').hidden && !document.getElementById('btnSzPen').hidden"))
            for (x, y) in L: await map_click(pg, ev, x, y)
            await map_click(pg, ev, *L[0])                       # the first corner again closes it
            sp = await ev('S.safe')
            check('clicked corners make the safe zone (6 corners, on)', sp['on'] and len(sp['poly']) == 6 and await ev('SZ.mode') == '', str([(round(q['x']), round(q['y'])) for q in sp['poly']]))
            check('it is kept for next time', await ev("JSON.parse(localStorage.getItem('magician-safe-zone')).poly.length === 6"))
            await pg.screenshot(path=str(OUT / 'zone-drawn.png'), full_page=False)

            # ---------- a drawing goes inside it ----------
            await pg.click('#tab-plot details summary')
            await pg.fill('#plot-text', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="5" y="5" width="90" height="90"/><circle cx="50" cy="50" r="30"/></svg>')
            await pg.click('#btnLoadText'); await asyncio.sleep(0.8)
            ip = await ev(IN_POLY)
            check('a new drawing is placed inside the safe zone, the margin kept', ip['ok'], f"closest {ip.get('worst', 0):.1f} mm to the edge (margin {ip.get('margin')})")
            await pg.click('#btnPlLargest'); await asyncio.sleep(0.8)
            ip = await ev(IN_POLY); big = await ev('S.plot.place.size')
            check('Largest: as big as the safe zone allows, still inside', ip['ok'] and big > 50, f'{big:.0f} mm, closest {ip["worst"]:.1f} mm')
            await pg.fill('#pl-sizeNum', '45'); await pg.press('#pl-sizeNum', 'Enter'); await asyncio.sleep(0.4)
            g = await ev("""(() => { const v = plotView(), r = plotCv.getBoundingClientRect(), [sx, sy] = v.toS(S.plot.place.cx, S.plot.place.cy), [bx, by] = v.toS(200, 60); return { c: [r.left + sx, r.top + sy], notch: [r.left + bx, r.top + by] }; })()""")
            await drag(pg, g['c'], g['notch'], steps=24)
            ip = await ev(IN_POLY)
            check('dragging it into the notch: it stops at the edge of the safe zone', ip['ok'], f"closest {ip['worst']:.1f} mm")

            # two objects either side of the notch: the pen travels round inside the zone
            await ev("""(() => { const o = selObj(); setPlaceFor(o, { ...o.place, cx: drawZone().rIn + 20, cy: -45, size: 25 }); })()""")
            await pg.click('#btnObjDup'); await asyncio.sleep(0.5)
            await ev("""(() => { const o = selObj(); setPlaceFor(o, { ...o.place, cx: drawZone().rIn + 85, cy: 50, size: 25 }); buildPlot(); })()""")
            await asyncio.sleep(0.5)
            ip = await ev(IN_POLY)
            check('two objects, both inside', ip['ok'] and await ev('S.plot.objects.length') == 2)
            await ev('window.SENTMARK = SENT.length')
            start = await ev('({ ...(S.cmd || S.pos) })')
            await pg.click('#btnDraw')
            await wait_for(ev, '!S.running', 30000); await asyncio.sleep(0.3)
            si = await ev(SENT_INSIDE, [start, 0.06])
            check('drawing: every move sent stays inside the allowed area (pen-up travel goes round the notch)', si['n'] > 20 and si['bad'] == 0, f"{si['n']} moves, {si['bad']} outside")
            red = await ev('S.paper.jobs.length && S.paper.jobs[S.paper.jobs.length - 1].done')
            check('the drawn lines are shown in red', red)

            # ---------- edit corners: drag one; the drawings follow ----------
            await pg.click('#btnSzEdit')
            p0 = await ev("S.safe.poly[2]")
            a = await map_click(pg, ev, p0['x'], p0['y'])          # (a click on a corner does nothing by itself)
            pt = await ev(f"(() => {{ const v = plotView(), r = plotCv.getBoundingClientRect(), [sx, sy] = v.toS({p0['x']} - 20, {p0['y']}); return [r.left + sx, r.top + sy]; }})()")
            await drag(pg, a, pt)
            await pg.click('#btnSzDone'); await asyncio.sleep(0.6)
            p1 = await ev("S.safe.poly[2]")
            check('Edit corners: dragging a corner moves it', abs(p1['x'] - (p0['x'] - 20)) < 1.5 and abs(p1['y'] - p0['y']) < 1.5, f"{p0['x']:.0f} → {p1['x']:.0f}")
            ip = await ev(IN_POLY)
            check('after the change every drawing still fits the zone', ip['ok'], f"closest {ip.get('worst', 0):.1f} mm")
            # a paper size makes a rectangle; Remove and Undo
            await pg.select_option('#sz-paper', 'A5'); await asyncio.sleep(0.5)
            pa = await ev("S.safe.poly")
            w = max(q['y'] for q in pa) - min(q['y'] for q in pa); h = max(q['x'] for q in pa) - min(q['x'] for q in pa)
            check('Paper size A5: a 210 × 148 mm rectangle in front of the arm', len(pa) == 4 and abs(w - 210) < 0.1 and abs(h - 148) < 0.1, f'{w:.0f} × {h:.0f} mm')
            await pg.click('#btnSzClear'); await asyncio.sleep(0.4)
            check('Remove zone: back to the green zone only', await ev("S.safe.poly === null && !drawZone().pq"))
            await pg.click('#btnSzUndo'); await asyncio.sleep(0.4)
            check('Undo puts the zone back', await ev("S.safe.poly && S.safe.poly.length === 4 && !!drawZone().pq"))
            await pg.uncheck('#sz-on'); await asyncio.sleep(0.3)
            check('Use safe zone off: kept, but not used', await ev("!!S.safe.poly && !S.safe.on && !drawZone().pq"))
            await pg.check('#sz-on'); await asyncio.sleep(0.3)

            # ---------- pen height: re-set by touching, save, use ----------
            z0 = await ev('S.limits.zDown')
            await pg.click('#btnPenReset')
            await wait_for(ev, "AC.step === 'pen'", 10000)
            pos = await ev('S.pos')
            check('Re-set pen height: the pen goes above the paper area, then the "lower the pen" step', await ev("AC.reset && AC.open") and pos['z'] > z0 + 5, f"Z {pos['z']:.1f}")
            await pg.fill('#ph-name', '')
            for _ in range(12):
                if await ev('S.pos.z') <= z0 + 8.5: break
                await pg.click('[data-dz="-2"]'); await wait_for(ev, '!AC.busy', 5000)
            for _ in range(20):
                if await ev('S.pos.z') <= z0 + 5.6: break
                await pg.click('[data-dz="-0.5"]'); await wait_for(ev, '!AC.busy', 5000)
            await pg.click('[data-ac=paper]')
            await wait_for(ev, "AC.step === 'done'", 10000)
            z1 = await ev('S.limits.zDown')
            check('a sheet 5.5 mm higher: pen down 5.5 mm higher, and the done step offers to save it', abs(z1 - (z0 + 5.5)) < 0.6 and await ev("!!document.getElementById('ac-phName')"), f'{z0} → {z1} mm')
            await pg.fill('#ac-phName', 'Board 5 mm'); await pg.click('[data-ac=phsave]')
            await pg.click('#autocalBody [data-ac=close]'); await asyncio.sleep(0.3)
            check('saved under its name', await ev("PH.list.length === 1 && PH.list[0].name === 'Board 5 mm'") and 'Board 5 mm' in await pg.inner_text('#ph-saved'))
            await ev("phApply(%s, 'test')" % z0); await asyncio.sleep(0.5)
            await pg.fill('#ph-name', 'Table'); await pg.click('#btnPhSave'); await asyncio.sleep(0.2)
            await pg.select_option('#ph-saved', '0'); await pg.click('#btnPhUse'); await asyncio.sleep(0.6)
            zu = await ev('[S.limits.zDown, S.limits.zUp, drawZone().fromModel]')
            check('Use a saved height: pen down at that height, zone from the geometry', abs(zu[0] - z1) < 0.01 and zu[1] > zu[0] and zu[2], str(zu))
            ip = await ev(IN_POLY)
            check('the drawings still fit at the new height', ip['ok'] or await ev("S.plot.objects.every(o => o.placeOk !== false)"))
            await pg.select_option('#ph-saved', '1'); await pg.click('#btnPhUse'); await asyncio.sleep(0.6)
            check('and back to the table height', abs(await ev('S.limits.zDown') - z0) < 0.01)

            # ---------- Redraw: two copies, waiting for a fresh sheet ----------
            await asyncio.sleep(0.3)
            await ev('buildPlot()'); await asyncio.sleep(0.4)
            await pg.click('#btnDraw'); await wait_for(ev, '!S.running', 30000)
            lines0 = await ev("S.paper.jobs.filter(j => j.done).length")
            drawn = await ev("S.paper.jobs.filter(j => j.done).reduce((a, j) => a + j.cmds.filter(c => c.z <= S.limits.zDown + 0.6).length, 0)")   # every sheet drawing shown in red
            await pg.fill('#rd-copies', '2')
            await ev('window.SENTMARK = SENT.length')
            await pg.click('#btnRedraw')
            ok_ask = await wait_for(ev, "!document.getElementById('rdAsk').hidden", 30000)
            jobs_mid = await ev("S.paper.jobs.length")
            check('Redraw ×2: the first copy is drawn, then it waits for a fresh sheet', ok_ask, await pg.inner_text('#rdAskText'))
            await pg.click('#btnRdGo')
            await wait_for(ev, "!S.running && document.getElementById('rdAsk').hidden", 30000); await asyncio.sleep(0.5)
            n_pen = await ev("""(() => { const z = S.limits.zDown + 0.6; return SENT.slice(SENTMARK).filter(c => !c.home && c.z <= z).length; })()""")
            check('both copies draw the same pen-down moves as what is shown in red', abs(n_pen - 2 * drawn) <= 8, f'{n_pen} pen-down moves sent; {lines0} drawings shown with {drawn}')
            check('the fresh sheet shows only the new copy in red', await ev("S.paper.jobs.filter(j => j.done).length") == 1 and await ev("PT.lastSheet.length") >= 1)
            await pg.fill('#rd-copies', '1'); await pg.uncheck('#rd-fresh')

            # ---------- Clear plotter ----------
            await pg.click('#btnPlotClear')
            check('Clear plotter asks for a second click', 'again' in (await pg.inner_text('#btnPlotClear')).lower())
            await pg.click('#btnPlotClear'); await asyncio.sleep(0.4)
            check('Clear plotter: no objects, no red lines', await ev("S.plot.objects.length === 0 && S.paper.jobs.length === 0"))
            check('Redraw can still draw the last sheet', not await pg.is_disabled('#btnRedraw') and 'last sheet' in await pg.inner_text('#rd-info'))
            await pg.click('#btnPlotUndo'); await asyncio.sleep(0.4)
            check('Undo clear brings the objects and the red lines back', await ev("S.plot.objects.length === 2 && S.paper.jobs.length >= 1"))

            # ---------- safety lock ----------
            await pg.click('#btnLock'); await asyncio.sleep(0.4)
            check('Safety lock: the arm was centred during calibration, so it turns on at once', await ev("LOCK.on") and 'on' in await pg.inner_text('#lockLabel'))
            R = await ev("(() => { const R = allowedRegion(); return { area: R.area, rings: R.rings.length }; })()")
            check('the allowed area is the green zone ∩ the safe zone, less the margin', R['rings'] >= 1 and R['area'] > 1000, f"{R['area'] / 100:.0f} cm²")
            # the arm into the middle of the area first (a click there: no question)
            await pg.click('#nav-mouse'); await asyncio.sleep(0.3)
            mid = await ev("(() => { const R = allowedRegion(); let best = null; for (let x = 150; x < 330; x += 2) for (let y = -120; y < 120; y += 2) if (regionHas(R, x, y) && regionEdgeD2(R, x, y) > (best ? best.d : 0)) best = { x, y, d: regionEdgeD2(R, x, y) }; return best; })()")
            async def mouse_click(x, y):
                q = await ev(f"(() => {{ const v = viewOf(mouseCv), r = mouseCv.getBoundingClientRect(), [sx, sy] = v.toS({x}, {y}); return [r.left + sx, r.top + sy]; }})()")
                await pg.mouse.click(q[0], q[1]); await asyncio.sleep(0.4)
            await pg.locator('#mouseCanvas').scroll_into_view_if_needed()
            await mouse_click(mid['x'], mid['y'])
            c0 = await ev('S.cmd')
            check('a click inside the area moves there, no question', abs(c0['x'] - mid['x']) < 0.6 and abs(c0['y'] - mid['y']) < 0.6 and await ev("document.getElementById('lockAsk').hidden"))
            far = (mid['x'], mid['y'] + 160)
            await mouse_click(*far)
            check('a click outside asks first: adjust or trim', not await ev("document.getElementById('lockAsk').hidden"), await pg.inner_text('#lkText'))
            await pg.click('#lkBtns button:has-text("Adjust")'); await asyncio.sleep(0.4)
            c1 = await ev('S.cmd')
            check('Adjust: the arm does not move', abs(c1['x'] - c0['x']) < 0.01 and abs(c1['y'] - c0['y']) < 0.01)
            await mouse_click(*far)
            await pg.click('#lkBtns button:has-text("Trim")'); await asyncio.sleep(0.5)
            c2 = await ev('S.cmd'); inside = await ev(f"regionHas(allowedRegion(), {c2['x']}, {c2['y']}, 0.1)"); de = await ev(f"Math.sqrt(regionEdgeD2(allowedRegion(), {c2['x']}, {c2['y']}))")
            check('Trim: the arm goes as far as the boundary and stops there', inside and de < 1.0 and c2['y'] > c0['y'] + 5, f"Y {c0['y']:.1f} → {c2['y']:.1f}, {de:.2f} mm from the edge")
            await pg.keyboard.press('ArrowLeft'); await asyncio.sleep(0.3)
            for _ in range(3): await pg.keyboard.press('Shift+ArrowLeft'); await asyncio.sleep(0.25)
            c3 = await ev('S.cmd')
            check('keyboard nudges stop at the boundary, without a question', await ev(f"regionHas(allowedRegion(), {c3['x']}, {c3['y']}, 0.1)") and await ev("document.getElementById('lockAsk').hidden"), f"Y {c3['y']:.1f}")
            await mouse_click(mid['x'], mid['y'])
            # under it all: a move straight to the arm outside the area is refused
            r = await ev("S.dev.ptp(400, 0, S.cmd.z, 0, 1).then(() => 'sent', e => e.message)")
            check('a move sent directly to the arm outside the area is refused', 'refused' in r and await ev("LOCK.refused >= 1"), r)
            # following: hold at the boundary, ask once, then trim for the session
            await ev("S.motion.follow = 'steps'")                  # plain steps: easier to follow in a test
            await pg.click('#btnLive'); await asyncio.sleep(0.2)
            q0 = await ev(f"(() => {{ const v = viewOf(mouseCv), r = mouseCv.getBoundingClientRect(), [sx, sy] = v.toS({mid['x']}, {mid['y']}); return [r.left + sx, r.top + sy]; }})()")
            q1 = await ev(f"(() => {{ const v = viewOf(mouseCv), r = mouseCv.getBoundingClientRect(), [sx, sy] = v.toS({mid['x']}, {mid['y'] + 150}); return [r.left + sx, r.top + sy]; }})()")
            await pg.mouse.move(*q0); await pg.mouse.down()
            for i in range(1, 21): await pg.mouse.move(q0[0] + (q1[0] - q0[0]) * i / 20, q0[1] + (q1[1] - q0[1]) * i / 20); await asyncio.sleep(0.06)
            await asyncio.sleep(0.6)
            asked = not await ev("document.getElementById('lockAsk').hidden")
            h = await ev('S.cmd'); held = await ev("LOCK.held.has('mouse')")
            check('live follow out of the area: the arm holds at the boundary and asks', asked and held and await ev(f"regionHas(allowedRegion(), {h['x']}, {h['y']}, 0.1)"), await pg.inner_text('#lkTitle'))
            await pg.mouse.up(); await asyncio.sleep(0.1)          # let go of the map, then answer
            await pg.click('#lkBtns button:has-text("Trim")'); await asyncio.sleep(0.3)
            await pg.mouse.move(*q1); await pg.mouse.down()
            for i in range(1, 11): await pg.mouse.move(q1[0], q1[1] - 8 * i); await asyncio.sleep(0.08)   # along the edge (screen up = robot +X)
            await asyncio.sleep(0.5)
            h2 = await ev('S.cmd')
            check('Trim for this session: it keeps following, along the boundary, without asking again',
                  await ev("LOCK.trimOK.has('mouse')") and await ev("document.getElementById('lockAsk').hidden") and await ev(f"regionHas(allowedRegion(), {h2['x']}, {h2['y']}, 0.1)") and abs(h2['x'] - h['x']) > 3,
                  f"X {h['x']:.1f} → {h2['x']:.1f}")
            await pg.mouse.up(); await asyncio.sleep(0.2)
            if not await ev("document.getElementById('lockAsk').hidden"): print('  (a dialog is open:', await pg.inner_text('#lkTitle'), '/', await pg.inner_text('#lkText'), ')')
            await pg.click('#btnLive'); await asyncio.sleep(0.3)
            check('turning live follow off ends the session', not await ev("LOCK.trimOK.has('mouse')"))
            # a replay that goes outside: asked, then trimmed
            await ev("S.takes.push({ name: 'out and back', use: true, pts: [0, 1, 2, 3, 4, 5, 6, 7, 8].map(i => ({ x: %f, y: %f + i * 25, z: S.limits.zUp + 10 })) }); renderTakes();" % (mid['x'], mid['y'] - 60))
            await ev('window.SENTMARK = SENT.length'); st = await ev('({ ...S.cmd })')
            await ev("void playTake(S.takes.length - 1)")
            ok_ask = await wait_for(ev, "!document.getElementById('lockAsk').hidden", 5000)
            check('a recorded take that goes outside: asked before it plays', ok_ask, await pg.inner_text('#lkText'))
            await pg.click('#lkBtns button:has-text("Trim")')
            await wait_for(ev, '!S.running', 20000); await asyncio.sleep(0.3)
            si = await ev(SENT_INSIDE, [st, 0.06])
            check('trimmed: every move of the replay stays inside', si['n'] >= 5 and si['bad'] == 0, f"{si['n']} moves")
            # a drawing line that runs outside the area: asked, then trimmed to its inside part
            await pg.click('#nav-plot'); await asyncio.sleep(0.3)
            await ev('window.SENTMARK = SENT.length'); st = await ev('({ ...S.cmd })')
            await ev(f"(() => {{ const ops = buildOps([{{ pts: [{{ x: {mid['x']}, y: {mid['y']} }}, {{ x: {mid['x']}, y: {mid['y'] + 140} }}], rev: false }}], S.cmd, 0.5); window.TESTRUN = runDrawing('Line out', ops, {{ ...S.cmd }}); }})()")
            ok_ask = await wait_for(ev, "!document.getElementById('lockAsk').hidden", 5000)
            await pg.screenshot(path=str(OUT / 'lock-ask.png'))
            check('a drawing line that leaves the area: asked, and shown in red on the map', ok_ask and await ev("!!LOCK.bad"))
            await pg.click('#lkBtns button:has-text("Trim")')
            await wait_for(ev, '!S.running', 20000); await asyncio.sleep(0.3)
            si = await ev(SENT_INSIDE, [st, 0.06])
            pen_y = await ev("(() => { const z = S.limits.zDown + 0.6, ys = SENT.slice(SENTMARK).filter(c => !c.home && c.z <= z).map(c => c.y); return [Math.min(...ys), Math.max(...ys)]; })()")
            edge_y = await ev(f"(() => {{ const R = allowedRegion(), sp = regionSpans(R, {mid['x']}, {mid['y']}, {mid['x']}, {mid['y'] + 140}); return {mid['y']} + 140 * sp[0][1]; }})()")
            check('trimmed: the pen draws only up to the boundary', si['bad'] == 0 and abs(pen_y[1] - edge_y) < 0.5, f"pen down from Y {pen_y[0]:.1f} to {pen_y[1]:.1f}; boundary at {edge_y:.1f}")
            # lock off: free again
            await pg.click('#btnLock'); await asyncio.sleep(0.3)
            check('Safety lock off', not await ev("LOCK.on"))
            r = await ev("S.dev.ptp(S.cmd.x, S.cmd.y + 60, S.cmd.z, 0, 2).then(() => 'sent', e => e.message)")
            check('with the lock off, moves outside the safe zone are allowed again (within reach)', r == 'sent')
            # after reconnecting the arm must be centred again before the lock goes on
            await ev("disconnect()"); await asyncio.sleep(0.3)
            await pg.click('#btnSim'); await asyncio.sleep(0.6)
            if not await ev("document.getElementById('autocal').hidden"): await pg.click('#autocalBody [data-ac=keep]')
            await ev(RECORD)
            await pg.click('#btnLock'); await asyncio.sleep(0.3)
            ask = await pg.inner_text('#lkText') if not await ev("document.getElementById('lockAsk').hidden") else ''
            check('not centred yet: the lock asks to centre the arm first', 'centred' in ask, ask[:80])
            await pg.click('#lkBtns button:has-text("Centre and lock")')
            await wait_for(ev, 'LOCK.on', 10000)
            check('Centre and lock: the arm is homed, then the lock is on', await ev("LOCK.on && S.homedAt > 0 && SENT.some(c => c.home)"))
            await pg.click('#btnLock')

            print('errors:', errors[:5])
            await b.close()
    finally:
        srv.terminate()
    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks passed" + (f"; FAILED: {bad}" if bad else ''))
    sys.exit(1 if bad else 0)

def S_OK(v): return bool(v)

asyncio.run(main())
