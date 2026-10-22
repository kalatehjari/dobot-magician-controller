"""Browser test for several objects on the paper and the text tool: adding drawings and text, choosing
one by clicking its lines, dragging, resizing and turning only that one, copy, delete, leave out, draw
only one, per-object shading, text editing (font, style, letter height, rotation, alignment, spacing,
missing letters, accents), drawing on the simulated arm and the layout SVG.
Runs the real app with the built-in simulator in headless Chromium.
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_objects.py"""
import asyncio, json, math, os, pathlib, re, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
sys.path.insert(0, str(HERE)); from fixtures import write_images; write_images(f'{SRV}/img')
PORT = 8782
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

async def drag(pg, a, b, steps=12):
    await pg.mouse.move(*a); await pg.mouse.down()
    for i in range(1, steps + 1):
        await pg.mouse.move(a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps)
        await asyncio.sleep(0.02)
    await pg.mouse.up(); await asyncio.sleep(0.35)

HELPERS = r"""
window.T = {
  scr(x, y) { const v = plotView(), r = plotCv.getBoundingClientRect(), [sx, sy] = v.toS(x, y); return [r.left + sx, r.top + sy]; },
  // a point on one of the object's own lines, far from every other object's lines
  linePt(id) {
    const o = objById(id), f = placeXform(o.place), v = plotView();
    let best = null, bd = -1;
    for (const s of o.sketch.strokes) for (let i = 0; i < s.length; i += Math.max(1, Math.floor(s.length / 12))) {
      const q = f(s[i]), [sx, sy] = v.toS(q.x, q.y);
      let dmin = Infinity;
      for (const p of S.plot.objects) if (p !== o) { const g = placeXform(p.place);
        for (const t of p.sketch.strokes) for (let j = 0; j < t.length; j += 2) { const w = g(t[j]), [ax, ay] = v.toS(w.x, w.y); dmin = Math.min(dmin, Math.hypot(ax - sx, ay - sy)); } }
      if (dmin > bd) { bd = dmin; best = q; }
    }
    return T.scr(best.x, best.y);
  },
  centre(id) { const o = objById(id); return T.scr(o.place.cx, o.place.cy); },
  corner(id, k) { const g = frameGeom(plotView(), objById(id)), r = plotCv.getBoundingClientRect(); return [r.left + g.fr[k][0], r.top + g.fr[k][1]]; },
  knob(id) { const g = frameGeom(plotView(), objById(id)), r = plotCv.getBoundingClientRect(); return [r.left + g.knob[0], r.top + g.knob[1]]; },
  // inside the green zone, at least 25 mm from every object's frame
  empty() {
    const z = drawZone();
    for (let r = z.rIn + 5; r < z.rOut - 5; r += 5) for (let a = -80; a <= 80; a += 4) {
      const x = r * Math.cos(a * RAD), y = r * Math.sin(a * RAD);
      if (!zoneHas(z, x, y)) continue;
      if (S.plot.objects.every(o => { const b = frameBox(o.sketch, o.place, 25); return x < b.x0 || x > b.x1 || y < b.y0 || y > b.y1; })) return T.scr(x, y);
    }
    return null;
  },
  boxes() { return S.plot.objects.map(o => frameBox(o.sketch, o.place, 0)); },
  overlapsWith(id) { const o = objById(id), b = frameBox(o.sketch, o.place, 0); return S.plot.objects.filter(p => p !== o && boxOverlapArea(b, frameBox(p.sketch, p.place, 0)) > 0).length; },
  // does a square (centre c, half-size h) touch any object's frame (the turned rectangle)?
  squareHits(c, h) {
    const inPoly = (P, q) => { let pos = 0, neg = 0; for (let i = 0; i < 4; i++) { const a = P[i], b = P[(i + 1) % 4], cr = (b.x - a.x) * (q.y - a.y) - (b.y - a.y) * (q.x - a.x); if (cr > 0) pos++; else if (cr < 0) neg++; } return !(pos && neg); };
    const sq = []; for (let i = 0; i < 40; i++) { const t = i / 10, k = Math.floor(t), f = t - k; const P = [[-h, -h], [h, -h], [h, h], [-h, h]], a = P[k], b = P[(k + 1) % 4]; sq.push({ x: c.x + a[0] + (b[0] - a[0]) * f, y: c.y + a[1] + (b[1] - a[1]) * f }); }
    return S.plot.objects.some(o => { const fr = placeFrame(o.sketch, o.place); return sq.some(q => inPoly(fr, q)) || fr.some(q => Math.abs(q.x - c.x) <= h && Math.abs(q.y - c.y) <= h); });
  },
  overlaps() { const B = T.boxes(); let n = 0; for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) if (boxOverlapArea(B[i], B[j]) > 0) n++; return n; },
  objs() { return S.plot.objects.map(o => ({ id: o.id, kind: o.kind, label: o.label, use: o.use, ok: o.placeOk, pl: o.place, text: o.text || null, missing: o.missing || [], pattern: o.shade.pattern })); },
  // every pen-down move inside the green zone, and ops current
  inside() { const z = drawZone(), ops = S.plot.ops; if (!ops) return { ok: false, why: 'no ops' }; let prev = S.plot.start, bad = 0;
    for (const o of ops) { if (o.pen) { const r = Math.hypot(o.x, o.y), th = Math.atan2(o.y, o.x) / RAD;
        if (r > z.rOut + 1e-6 || th < z.thMin - 1e-6 || th > z.thMax + 1e-6) bad++;
        if (segDist0(prev.x, prev.y, o.x, o.y) < z.rIn - 1e-6) bad++; } prev = o; }
    return { ok: bad === 0 && S.plot.opsVer === S.plot.placeVer, bad }; },
  // robot position of a text object's own origin (the alignment point of its first line)
  textOrigin(id) { const o = objById(id), sk = o.sketch, u = { x: -sk.srcBox.cx / sk.srcBox.L, y: -sk.srcBox.cy / sk.srcBox.L }; return placeXform(o.place)(u); },
  // pen-down ops points inside one object's frame
  opsIn(id) { const o = objById(id), inv = placeInverse(o.place); let n = 0; for (const p of S.plot.ops || []) if (p.pen) { const u = inv(p); if (Math.abs(u.x) <= o.sketch.w / 2 + 0.01 && Math.abs(u.y) <= o.sketch.h / 2 + 0.01) n++; } return n; },
};
"""

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
            await ev("localStorage.removeItem('magician-text'); localStorage.removeItem('magician-shade')")
            await pg.reload()
            ver = await ev("document.querySelector('.ver').textContent")
            check('version shows v1.4.0 or later', tuple(int(v) for v in ver.lstrip('v').split('.')) >= (1, 4, 0), ver)
            await ev(HELPERS)

            # calibrate in the simulator, so the green zone is a real one
            await pg.click('#btnSim'); await wait_for(ev, "!document.getElementById('autocal').hidden", 3000)
            await pg.click('[data-ac=start]'); await wait_for(ev, "AC.step === 'pen'", 15000)
            for _ in range(12):
                if await ev('S.pos.z') <= -58: break
                await pg.click('[data-dz="-10"]'); await wait_for(ev, '!AC.busy', 5000)
            await pg.click('[data-ac=paper]'); await wait_for(ev, "AC.step === 'done'", 10000)
            await pg.click('#autocalBody [data-ac=close]')
            await pg.click('#nav-plot'); await asyncio.sleep(0.3)

            # ---------- empty paper ----------
            st = await ev("({ count: document.getElementById('obj-count').textContent, dis: ['btnObjDup', 'btnObjDel', 'btnObjClear', 'pl-size', 'sh-pattern'].map(id => document.getElementById(id).disabled), mode: document.getElementById('tx-mode').textContent, fonts: document.querySelectorAll('#tx-fonts .tx-font').length, styles: document.getElementById('tx-style').options.length })")
            check('empty paper: nothing selected, controls off, 13 fonts with 4 styles', st['count'] == 'Nothing on the paper yet' and all(st['dis']) and st['mode'] == 'new text' and st['fonts'] == 13 and st['styles'] == 4, json.dumps(st))

            # ---------- two library drawings ----------
            ids = await ev("LIBRARY.filter(e => ['Cat', 'Owl', 'Sailboat'].includes(e.n)).map(e => e.i)")
            await pg.click(f'#lib-grid .lib-item[data-id="{ids[0]}"]'); await asyncio.sleep(0.4)
            o1 = (await ev('T.objs()'))[0]
            best = await ev('objTargets(selObj())[0].size')
            check('first drawing: 90 % of the largest, centred, selected', len(await ev('T.objs()')) == 1 and abs(o1['pl']['size'] - math.floor(best * 0.9)) < 1e-6 and abs(o1['pl']['cy']) < 1e-6 and await ev('S.plot.sel') == o1['id'],
                  f"{o1['label']} {o1['pl']['size']:.0f} mm")
            await pg.click(f'#lib-grid .lib-item[data-id="{ids[1]}"]'); await asyncio.sleep(0.4)
            objs = await ev('T.objs()')
            check('a second library drawing is added next to it, smaller, without overlapping', len(objs) == 2 and objs[1]['pl']['size'] < objs[0]['pl']['size'] and await ev('T.overlaps()') == 0 and await ev('S.plot.sel') == objs[1]['id'],
                  f"{objs[1]['label']} {objs[1]['pl']['size']:.0f} mm at ({objs[1]['pl']['cx']:.0f}, {objs[1]['pl']['cy']:.0f})")
            ins = await ev('T.inside()')
            check('the path has both, every line inside the zone', ins['ok'] and await ev('S.plot.drawnIds.length') == 2 and await ev(f"T.opsIn({objs[0]['id']}) > 20 && T.opsIn({objs[1]['id']}) > 20"))
            chips = await ev("[...document.querySelectorAll('#obj-list .obj-item')].map(r => ({ sel: r.classList.contains('sel'), name: r.querySelector('.obj-name span:nth-child(2)').textContent, use: r.querySelector('input').checked }))")
            check('the list shows both, the new one selected', [c['name'] for c in chips] == [objs[0]['label'], objs[1]['label']] and [c['sel'] for c in chips] == [False, True] and all(c['use'] for c in chips), json.dumps(chips))
            stats = await ev("document.getElementById('plot-stats').textContent")
            check('stats count both objects', stats.startswith('2 objects'), stats)

            # ---------- select by clicking its lines; move only that one ----------
            await pg.locator('#plotCanvas').scroll_into_view_if_needed(); await asyncio.sleep(0.3)
            a, bb = objs[0]['id'], objs[1]['id']
            pt = await ev(f'T.linePt({a})')
            await pg.mouse.click(*pt); await asyncio.sleep(0.3)
            sel = await ev('S.plot.sel'); pinfo = await ev("document.getElementById('pl-info').textContent")
            check('clicking the first drawing’s lines selects it', sel == a and pinfo.startswith(objs[0]['label']), pinfo[:60])
            check('the size box shows the selected drawing', abs(await ev("+document.getElementById('pl-sizeNum').value") - round(objs[0]['pl']['size'], 1)) < 0.06)
            before = {o['id']: o['pl'] for o in await ev('T.objs()')}
            await drag(pg, await ev(f'T.linePt({a})'), (pt[0] - 40, pt[1] - 25))
            after = {o['id']: o['pl'] for o in await ev('T.objs()')}
            moved = math.hypot(after[a]['cx'] - before[a]['cx'], after[a]['cy'] - before[a]['cy'])
            check('dragging moves only the selected drawing', moved > 5 and after[bb] == before[bb] and (await ev('T.inside()'))['ok'], f'{moved:.1f} mm')
            # resize with a corner and turn with the knob: only the selected one changes
            s0 = after[a]['size']; c = await ev(f'T.centre({a})'); k = await ev(f'T.corner({a}, 1)')
            await drag(pg, k, (c[0] + (k[0] - c[0]) * 0.75, c[1] + (k[1] - c[1]) * 0.75))
            s1 = (await ev(f'objById({a}).place'))['size']
            kn = await ev(f'T.knob({a})'); c = await ev(f'T.centre({a})')
            r = math.hypot(kn[0] - c[0], kn[1] - c[1])
            await drag(pg, kn, (c[0] + r * math.sin(math.radians(30)), c[1] - r * math.cos(math.radians(30))), steps=16)
            pa = await ev(f'objById({a}).place'); pb = await ev(f'objById({bb}).place')
            check('corner handle shrinks it, knob turns it — the other drawing stays as it was', s1 < s0 * 0.85 and abs(pa['angle'] - 30) < 3.5 and pb == before[bb], f"{s0:.0f} → {s1:.0f} mm, {pa['angle']:.1f}°")
            # clicking empty paper deselects
            e = await ev('T.empty()')
            await pg.mouse.click(*e); await asyncio.sleep(0.3)
            st = await ev("({ sel: S.plot.sel, dis: ['btnObjDup', 'btnObjDel', 'pl-size', 'pl-rotNum', 'sh-pattern'].map(id => document.getElementById(id).disabled), shade: document.getElementById('sh-stats').textContent })")
            check('clicking empty paper selects nothing, and the controls switch off', st['sel'] is None and all(st['dis']) and 'Select a drawing' in st['shade'], json.dumps(st))
            # select from the list
            await pg.click('#obj-list .obj-item:nth-child(2) .obj-name'); await asyncio.sleep(0.2)
            check('clicking a name in the list selects that object', await ev('S.plot.sel') == bb)

            # ---------- duplicate and delete ----------
            await pg.click('#btnObjDup'); await asyncio.sleep(0.5)
            objs = await ev('T.objs()'); cp = objs[-1]
            dd = {'n': len(objs), 'label': cp['label'], 'size': [cp['pl']['size'], objs[1]['pl']['size']], 'angle': [cp['pl']['angle'], objs[1]['pl']['angle']],
                  'sel': await ev('S.plot.sel') == cp['id'], 'ov': await ev(f"T.overlapsWith({cp['id']})"), 'inside': await ev('T.inside()')}
            check('Duplicate adds a copy with the same size and angle, selected, not overlapping', dd['n'] == 3 and dd['label'].endswith('(copy)') and abs(dd['size'][0] - dd['size'][1]) < 1e-9 and dd['angle'][0] == dd['angle'][1] and dd['sel'] and dd['ov'] == 0 and dd['inside']['ok'],
                  f"copy at ({cp['pl']['cx']:.0f}, {cp['pl']['cy']:.0f}) {json.dumps(dd)}")
            await pg.locator('#plotCanvas').focus(); await pg.keyboard.press('d'); await asyncio.sleep(0.5)
            n4 = len(await ev('T.objs()'))
            await pg.keyboard.press('Delete'); await asyncio.sleep(0.4)
            await pg.keyboard.press('Backspace'); await asyncio.sleep(0.4)
            objs = await ev('T.objs()')
            check('D copies, Delete and Backspace remove the selected object', n4 == 4 and len(objs) == 2 and [o['id'] for o in objs] == [a, bb] and (await ev('T.inside()'))['ok'], f'4 → {len(objs)}')
            await pg.click('#btnObjDel'); await asyncio.sleep(0.3)
            objs = await ev('T.objs()')
            check('the Delete button removes the selected one and selects the next', len(objs) == 1 and await ev('S.plot.sel') == objs[0]['id'])
            await pg.click(f'#lib-grid .lib-item[data-id="{ids[1]}"]'); await asyncio.sleep(0.4)
            await pg.click(f'#lib-grid .lib-item[data-id="{ids[1]}"]'); await asyncio.sleep(0.4)
            check('clicking the library drawing that is selected again keeps it (no second copy)', len(await ev('T.objs()')) == 2)
            check('the library grid marks the selected object’s drawing', await ev(f"document.querySelector('#lib-grid .lib-item.sel').dataset.id") == ids[1])

            # ---------- text ----------
            await pg.fill('#tx-text', 'Kia ora Māori ā ē ī ō ū'); await asyncio.sleep(0.2)
            await pg.click('#tx-fonts .tx-font[data-key=serif]')
            await pg.select_option('#tx-style', 'bolditalic')
            await pg.fill('#tx-height', '8'); await pg.press('#tx-height', 'Tab')
            await pg.fill('#tx-rot', '30'); await pg.press('#tx-rot', 'Tab')
            await pg.click('#btnTextAdd'); await asyncio.sleep(0.5)
            objs = await ev('T.objs()'); t = objs[-1]
            check('Add text puts it on the paper, selected, at 8 mm letters and turned 30°', t['kind'] == 'text' and await ev('S.plot.sel') == t['id'] and abs(t['text']['height'] - 8) < 1e-6 and abs(t['pl']['angle'] - 30) < 1e-9 and t['label'] == 'Kia ora Māori ā ē ī ō ū' and not t['missing'],
                  f"{t['label']} {t['text']['height']:.2f} mm, {t['pl']['angle']}°")
            info = await ev("({ file: fontResolve('serif', 'bolditalic').file, mode: document.getElementById('tx-mode').textContent, pat: selObj().shade.pattern, chip: document.querySelector('#obj-list .obj-item.sel .obj-meta').textContent })")
            check('real bold italic serif font, text starts unshaded, list shows the letter height', info['file'] == 'HersheySerifBoldItalic' and info['pat'] == 'off' and info['mode'].startswith('editing') and info['chip'] == '8.0 mm letters', json.dumps(info))
            check('text fits the zone and is in the path, clear of the drawings', (await ev('T.inside()'))['ok'] and await ev(f"S.plot.drawnIds.includes({t['id']}) && T.opsIn({t['id']}) > 50") and await ev(f"T.overlapsWith({t['id']})") == 0)
            # the cap height on the paper really is 8 mm: measure the 'K'
            capmm = await ev(f"""(() => {{ const o = objById({t['id']}), lay = textLayout(o.text); const K = fontGlyphs(lay.font.file).map.get('K');
                const ys = K.strokes.flat().map(p => p.y); return (Math.max(...ys) - Math.min(...ys)) * o.place.size / o.sketch.srcBox.L; }})()""")
            check('letter height = capital height in mm', abs(capmm - 8) < 0.05, f'{capmm:.3f} mm')
            # edit the text: label, lines and the start point stay put (centred text: middle of the first line)
            o0 = await ev(f"T.textOrigin({t['id']})"); sk0 = await ev('selObj().sketch.id')
            await pg.fill('#tx-text', 'Kia ora koutou'); await asyncio.sleep(0.6)
            o1 = await ev(f"T.textOrigin({t['id']})"); tt = await ev('T.objs()')
            tt = [x for x in tt if x['id'] == t['id']][0]
            check('typing changes the selected text on the map; its anchor stays put', tt['label'] == 'Kia ora koutou' and await ev('selObj().sketch.id') != sk0 and math.hypot(o1['x'] - o0['x'], o1['y'] - o0['y']) < 1e-6 and abs(tt['text']['height'] - 8) < 1e-6,
                  f"anchor moved {math.hypot(o1['x'] - o0['x'], o1['y'] - o0['y']):.2e} mm")
            # left alignment: the left end stays put when typing more
            await pg.select_option('#tx-align', 'left'); await asyncio.sleep(0.4)
            o2 = await ev(f"T.textOrigin({t['id']})")
            await pg.fill('#tx-text', 'Kia ora koutou katoa'); await asyncio.sleep(0.6)
            o3 = await ev(f"T.textOrigin({t['id']})"); pl3 = await ev(f"objById({t['id']}).place")
            check('left-aligned text grows to the right from a fixed start', math.hypot(o3['x'] - o2['x'], o3['y'] - o2['y']) < 1e-6 and (await ev('T.inside()'))['ok'])
            # letter height and rotation fields
            await pg.fill('#tx-height', '12'); await pg.press('#tx-height', 'Tab'); await asyncio.sleep(0.4)
            h12 = await ev(f"objById({t['id']}).text.height")
            await pg.fill('#tx-rot', '-15'); await pg.press('#tx-rot', 'Tab'); await asyncio.sleep(0.4)
            plr = await ev(f"objById({t['id']}).place")
            check('letter height and rotation boxes change the selected text', (abs(h12 - 12) < 1e-6 or h12 < 12) and abs(plr['angle'] + 15) < 1e-9 and (await ev('T.inside()'))['ok'], f'{h12:.2f} mm, {plr["angle"]}°')
            # resizing on the map changes the letter height shown in the card
            await pg.locator('#plotCanvas').scroll_into_view_if_needed(); await asyncio.sleep(0.2)
            c = await ev(f"T.centre({t['id']})"); k = await ev(f"T.corner({t['id']}, 2)")
            await drag(pg, k, (c[0] + (k[0] - c[0]) * 0.7, c[1] + (k[1] - c[1]) * 0.7))
            hh = await ev(f"objById({t['id']}).text.height"); fld = await ev("+document.getElementById('tx-height').value")
            check('dragging a corner of the text changes its letter height, and the card follows', hh < h12 * 0.8 and abs(fld - round(hh, 1)) < 0.06, f'{h12:.1f} → {hh:.2f} mm (card {fld})')
            # font and style changes
            await pg.click('#tx-fonts .tx-font[data-key=script]'); await asyncio.sleep(0.4)
            f1 = await ev("({ fam: selObj().text.family, file: textLayout(selObj().text).font.file, pressed: document.querySelector('#tx-fonts .tx-font[aria-pressed=true]').dataset.key })")
            await pg.select_option('#tx-style', 'regular'); await asyncio.sleep(0.4)
            f2 = await ev("textLayout(selObj().text).font.file")
            await pg.click('#tx-fonts .tx-font[data-key=tech]'); await pg.select_option('#tx-style', 'bold'); await asyncio.sleep(0.4)
            f3 = await ev("(() => { const r = fontResolve('tech', 'bold'); return { ...r, family: r.family.key, info: document.getElementById('tx-info').textContent }; })()")
            check('fonts and styles: script bold italic → Script medium slanted, regular → Script 1-stroke; Tech bold is made with a second line',
                  f1['fam'] == 'script' and f1['file'] == 'HersheyScriptMed' and f1['pressed'] == 'script' and f2 == 'HersheyScript1' and f3['fakeBold'] and 'second pen line' in f3['info'], f"{f1} {f2} {f3['info'][-80:]}")
            # made-up bold: the second line is 0.35 mm beside the first, whatever the size
            gap = await ev("""(() => { const o = selObj(), lay = textLayout(o.text), n = lay.strokes.length / 2, a = lay.strokes[0][0], b = lay.strokes[n][0];
                return Math.hypot(b.x - a.x, b.y - a.y) * o.place.size / o.sketch.srcBox.L; })()""")
            check('made-up bold: second pen line 0.35 mm from the first', abs(gap - 0.35) < 0.01, f'{gap:.3f} mm')
            # letters the font does not have, accents it does not have
            await pg.fill('#tx-text', 'ŁódźŻ ★ ő'); await asyncio.sleep(0.6)
            mi = await ev("({ missing: selObj().missing, info: document.getElementById('tx-info').textContent })")
            check('characters not in the font are listed; ł, ó, ź, Ż, ő are drawn with added accents', mi['missing'] == ['★'] and '★' in mi['info'], json.dumps(mi))
            # multi-line, line spacing and letter spacing
            await pg.fill('#tx-text', 'Line one\nLine two'); await asyncio.sleep(0.6)
            h1 = await ev('selObj().sketch.srcBox.L')
            await pg.fill('#tx-lines', '2'); await pg.press('#tx-lines', 'Tab'); await asyncio.sleep(0.4)
            box2 = await ev("(() => { const b = strokesBBox(textLayout(selObj().text).strokes); return b; })()")
            await pg.fill('#tx-lines', '1'); await pg.press('#tx-lines', 'Tab'); await asyncio.sleep(0.4)
            box1 = await ev("strokesBBox(textLayout(selObj().text).strokes)")
            await pg.fill('#tx-spacing', '50'); await pg.press('#tx-spacing', 'Tab'); await asyncio.sleep(0.4)
            boxs = await ev("strokesBBox(textLayout(selObj().text).strokes)")
            check('two lines; line spacing 2 makes the block taller, letter spacing 50 % wider', abs((box2['h'] - box1['h']) - 1.6) < 0.05 and boxs['w'] > box1['w'] * 1.3,
                  f"height {box1['h']:.2f} → {box2['h']:.2f}, width {box1['w']:.2f} → {boxs['w']:.2f} cap heights")
            # empty text keeps the old lines, with a note
            await pg.fill('#tx-text', ''); await asyncio.sleep(0.6)
            em = await ev("({ empty: selObj().textEmpty, n: selObj().sketch.strokes.length, info: document.getElementById('tx-info').textContent })")
            check('emptying the text keeps its last lines until you type again', em['empty'] and em['n'] > 0 and 'empty' in em['info'], em['info'][:70])
            await pg.fill('#tx-text', 'Hello'); await asyncio.sleep(0.6)

            # ---------- per-object shading ----------
            await pg.click('#obj-list .obj-item:nth-child(1) .obj-name'); await asyncio.sleep(0.2)
            await pg.select_option('#sh-pattern', 'lines'); await asyncio.sleep(0.6)
            sh = await ev("T.objs().map(o => o.pattern)")
            check('shading applies to the selected drawing only', sh == ['lines', 'off', 'off'], json.dumps(sh))
            n_sh = await ev("selObj().shCache.lines")
            await pg.click('#obj-list .obj-item:nth-child(2) .obj-name'); await asyncio.sleep(0.2)
            card = await ev("({ pat: document.getElementById('sh-pattern').value, forw: document.getElementById('sh-for').textContent })")
            check('selecting another drawing shows its own shading', card['pat'] == 'off' and objs[1]['label'] in card['forw'], json.dumps(card))
            await pg.click(f'#lib-grid .lib-item[data-id="{ids[2]}"]'); await asyncio.sleep(0.5)
            check('a new drawing starts with the shading used last', await ev('selObj().shade.pattern') == 'lines' and n_sh > 10)
            await pg.select_option('#sh-pattern', 'off'); await asyncio.sleep(0.3)
            ok = await ev('T.inside()')
            check('the path still fits with four objects', ok['ok'] and await ev('S.plot.drawnIds.length') == 4)

            # ---------- leave out, draw only one, draw ----------
            await pg.uncheck('#obj-list .obj-item:nth-child(1) input'); await asyncio.sleep(0.4)
            st = await ev("({ ids: S.plot.drawnIds, stats: document.getElementById('plot-stats').textContent, off: document.querySelector('#obj-list .obj-item:nth-child(1)').classList.contains('off') })")
            check('unticking leaves it out of the path (shown faded in the list)', a not in st['ids'] and len(st['ids']) == 3 and '(1 not drawn)' in st['stats'] and st['off'], st['stats'][:50])
            tid = t['id']
            await pg.click(f'#obj-list .obj-item:nth-child(3) .obj-name'); await asyncio.sleep(0.2)
            await pg.click('#btnObjOnly'); await asyncio.sleep(0.4)
            st = await ev("({ ids: S.plot.drawnIds, use: S.plot.objects.map(o => o.use) })")
            check('Draw only this ticks just the selected object', st['ids'] == [tid] and st['use'] == [False, False, True, False], json.dumps(st))
            jobs0 = await ev('S.paper.jobs.length')
            await pg.click('#btnDraw')
            await wait_for(ev, '!S.running && S.paper.jobs.length > ' + str(jobs0), 60000, 200)
            await wait_for(ev, '!S.running', 120000, 300)
            dj = await ev("(() => { const j = S.paper.jobs[S.paper.jobs.length - 1]; return { done: j && j.done, n: j && j.cmds.length }; })()")
            check('drawing the text alone on the simulated arm finishes', dj['done'] and dj['n'] > 50, json.dumps(dj))
            for i in (1, 2, 4):
                await pg.check(f'#obj-list .obj-item:nth-child({i}) input'); await asyncio.sleep(0.3)
            check('ticking them again puts all four back in the path', len(await ev('S.plot.drawnIds')) == 4)

            # ---------- hover round: check the paper ----------
            await ev("window.REC = []; (() => { const f = S.dev.ptp.bind(S.dev); S.dev.ptp = (x, y, z, r, m) => { REC.push({ x, y, z }); return f(x, y, z, r, m); }; })()")
            await pg.select_option('#plot-frame', 'box')
            await pg.click('#btnHoverRound'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 120000, 200)
            hr = await ev("""(() => { const zD = S.limits.zDown, zU = S.limits.zUp, zH = Math.min(zU, zD + 5);
                const round = REC.filter(c => Math.abs(c.z - zH) < 0.01), pen = S.plot.ops.filter(o => o.pen);
                const xs = round.map(c => c.x), ys = round.map(c => c.y), m = { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys) };
                const px = pen.map(o => o.x), py = pen.map(o => o.y);
                const gap = Math.min(Math.min(...px) - m.x0, m.x1 - Math.max(...px), Math.min(...py) - m.y0, m.y1 - Math.max(...py));
                const corners = [[m.x1, m.y1], [m.x1, m.y0], [m.x0, m.y0], [m.x0, m.y1]].every(([x, y]) => round.some(c => Math.hypot(c.x - x, c.y - y) < 0.01));
                return { n: REC.length, low: Math.min(...REC.map(c => c.z)) - zD, gap, corners, frame: !!PL.frame, lifted: REC[REC.length - 1].z >= zU - 0.01,
                         closed: Math.hypot(round[0].x - round[round.length - 1].x, round[0].y - round[round.length - 1].y) < 0.01, alarms: S.dev.io.st.alarms.size }; })()""")
            check('Hover round (box) goes round the corners of a box holding every line, 5 mm above the paper, never lower', hr['corners'] and hr['closed'] and -0.01 < hr['gap'] < 3.1 and hr['low'] > 4.9 and hr['lifted'] and hr['frame'] and hr['alarms'] == 0, json.dumps(hr))
            # one small object in the middle: the box keeps 3 mm clear of its lines
            await pg.click(f'#obj-list .obj-item:nth-child(3) .obj-name'); await pg.click('#btnObjOnly'); await asyncio.sleep(0.4)
            await ev('REC.length = 0')
            await pg.click('#btnHoverRound'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 120000, 200)
            g3 = await ev("""(() => { const zH = Math.min(S.limits.zUp, S.limits.zDown + 5), round = REC.filter(c => Math.abs(c.z - zH) < 0.01), pen = S.plot.ops.filter(o => o.pen);
                const xs = round.map(c => c.x), ys = round.map(c => c.y), px = pen.map(o => o.x), py = pen.map(o => o.y);
                return Math.min(Math.min(...px) - Math.min(...xs), Math.max(...xs) - Math.max(...px), Math.min(...py) - Math.min(...ys), Math.max(...ys) - Math.max(...py)); })()""")
            check('…3 mm clear of the lines when there is room', 2.9 < g3 < 3.1, f'{g3:.2f} mm')
            for i in (1, 2, 4):
                await pg.check(f'#obj-list .obj-item:nth-child({i}) input'); await asyncio.sleep(0.3)
            await ev('REC.length = 0')
            await pg.select_option('#plot-frame', 'outline')
            await pg.click('#btnHoverRound'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 120000, 200)
            ho = await ev("""(() => { const zH = Math.min(S.limits.zUp, S.limits.zDown + 5), round = REC.filter(c => Math.abs(c.z - zH) < 0.01);
                const inPoly = (P, q) => { let w = false; for (let i = 0, j = P.length - 1; i < P.length; j = i++) { const a = P[i], b = P[j]; if ((a.y > q.y) !== (b.y > q.y) && q.x < (b.x - a.x) * (q.y - a.y) / (b.y - a.y) + a.x) w = !w; } return w; };
                const pen = S.plot.ops.filter(o => o.pen), outside = pen.filter(p => !inPoly(round, p)).length;
                const z = drawZone(), core = round.every(c => Math.hypot(c.x, c.y) >= z.rIn - 0.5);
                return { n: round.length, outside, core, area: round.reduce((a, p, i) => { const q = round[(i + 1) % round.length]; return a + p.x * q.y - q.x * p.y; }, 0) / 2 }; })()""")
            check('Hover round (outline) follows the outside of the lines and keeps out of the reach-less middle', ho['outside'] == 0 and ho['core'] and ho['n'] >= 4, json.dumps(ho))

            # ---------- test square, layout SVG, export ----------
            spot = await ev("(() => { const z = drawZone(), c = testSquareSpot(z, 10); return !!c && !T.squareHits(c, 10); })()")
            check('the test square goes where it misses every object', spot)
            async with pg.expect_download() as dl:
                await pg.click('#btnLayoutSvg')
            path = await (await dl.value).path(); svg = open(path).read()
            check('Layout SVG has every object in millimetres', svg.count('<path data-name=') == 4 and 'mm"' in svg and 'Hello' in svg, f'{len(svg)} bytes')
            async with pg.expect_download() as dl:
                await pg.click('#btnExportOps')
            data = json.load(open(await (await dl.value).path()))
            check('Export path lists the objects drawn', len(data['objects']) == 4 and data['format'] == 'magician-ops-v1' and len(data['ops']) > 100, f"{[o['label'] for o in data['objects']]}")

            # ---------- re-tracing a picture replaces it ----------
            await pg.set_input_files('#plot-file', f'{SRV}/img/photo.jpg'); await asyncio.sleep(2.5)
            n5 = len(await ev('T.objs()')); tr = await ev('selObj().id')
            await ev("document.getElementById('tr-detail').value = 3; document.getElementById('tr-detail').dispatchEvent(new Event('input'))"); await asyncio.sleep(1.2)
            await pg.click('#btnTraceUse'); await asyncio.sleep(1.5)
            check('a picture is added once; Use these lines again replaces it', n5 == 5 and len(await ev('T.objs()')) == 5 and await ev('selObj().id') == tr)

            # ---------- undo a removal ----------
            before_ids = [o['id'] for o in await ev('T.objs()')]
            await pg.locator('#plotCanvas').focus(); await pg.keyboard.press('Delete'); await asyncio.sleep(0.4)
            st = await ev("({ n: S.plot.objects.length, undo: !document.getElementById('btnObjUndo').hidden })")
            await pg.click('#btnObjUndo'); await asyncio.sleep(0.4)
            check('Undo remove puts a deleted object back in its place in the list', st['n'] == len(before_ids) - 1 and st['undo'] and [o['id'] for o in await ev('T.objs()')] == before_ids and (await ev('T.inside()'))['ok'])

            # ---------- save a layout ----------
            saved_objs = await ev('T.objs()')
            async with pg.expect_download() as dl:
                await pg.click('#btnLayoutSave')
            lpath = str(OUT / 'layout_saved.json')
            await (await dl.value).save_as(lpath)
            lay = json.load(open(lpath))
            check('Save layout writes every object (drawings as lines, text as its settings)', lay['format'] == 'magician-layout-v1' and len(lay['objects']) == 5 and sum(1 for o in lay['objects'] if o['kind'] == 'text') == 1 and all(('strokes' in o) != (o['kind'] == 'text') for o in lay['objects']),
                  f"{os.path.getsize(lpath)} bytes")

            # ---------- remove all (two clicks), undo, remove again ----------
            await pg.click('#btnObjClear'); await asyncio.sleep(0.2)
            n6 = len(await ev('T.objs()')); lbl = await ev("document.getElementById('btnObjClear').textContent")
            await pg.click('#btnObjClear'); await asyncio.sleep(0.4)
            st = await ev("({ n: S.plot.objects.length, sel: S.plot.sel, ops: S.plot.ops, stats: document.getElementById('plot-stats').textContent, kept: localStorage.getItem('magician-paper') })")
            check('Remove all asks for a second click, then clears the paper', n6 == 5 and 'again' in lbl and st['n'] == 0 and st['sel'] is None and st['ops'] is None and st['kept'] is None, st['stats'])
            await pg.click('#btnObjUndo'); await asyncio.sleep(0.4)
            check('Undo brings everything back', [o['id'] for o in await ev('T.objs()')] == before_ids)
            await pg.click('#btnObjClear'); await pg.click('#btnObjClear'); await asyncio.sleep(0.4)

            # ---------- open the layout ----------
            await pg.set_input_files('#layout-file', lpath); await asyncio.sleep(0.8)
            back = await ev('T.objs()')
            same = len(back) == 5 and all(a['kind'] == b['kind'] and a['label'] == b['label'] and a['use'] == b['use'] and abs(a['pl']['cx'] - b['pl']['cx']) < 0.01 and abs(a['pl']['cy'] - b['pl']['cy']) < 0.01
                                          and abs(a['pl']['size'] - b['pl']['size']) < 0.05 and a['pl']['angle'] == b['pl']['angle'] and a['pattern'] == b['pattern'] for a, b in zip(back, saved_objs))
            check('Open layout puts the same objects back where they were', same and (await ev('T.inside()'))['ok'], f"{len(back)} objects")
            tb = [o for o in back if o['kind'] == 'text'][0]; ts = [o for o in saved_objs if o['kind'] == 'text'][0]
            check('text comes back as editable text with its font and style', tb['text']['family'] == ts['text']['family'] and tb['text']['style'] == ts['text']['style'] and tb['text']['str'] == ts['text']['str'])

            # ---------- the paper comes back after a reload ----------
            await asyncio.sleep(1.2)
            await pg.reload(); await asyncio.sleep(0.8)
            await ev(HELPERS)
            back2 = await ev('T.objs()')
            check('after a reload the paper is restored from this browser', len(back2) == 5 and [o['label'] for o in back2] == [o['label'] for o in saved_objs] and all(abs(a['pl']['cx'] - b['pl']['cx']) < 0.01 for a, b in zip(back2, saved_objs)))
            await pg.click('#nav-plot'); await asyncio.sleep(0.3)
            await pg.click('#btnObjClear'); await pg.click('#btnObjClear'); await asyncio.sleep(0.4)

            # ---------- remembered text settings ----------
            await pg.reload(); await asyncio.sleep(0.6)
            await pg.click('#nav-plot'); await asyncio.sleep(0.3)
            tpl = await ev("({ n: S.plot.objects.length, txt: document.getElementById('tx-text').value, font: document.querySelector('#tx-fonts .tx-font[aria-pressed=true]').dataset.key, style: document.getElementById('tx-style').value })")
            check('text settings are remembered in this browser; an emptied paper stays empty', tpl == {'n': 0, 'txt': 'Hello', 'font': 'tech', 'style': 'bold'}, json.dumps(tpl))

            # ---------- screenshots ----------
            await ev(HELPERS)
            await ev("libLoad(LIBRARY.find(e => e.n === 'Owl').i)"); await asyncio.sleep(0.3)
            await ev("libLoad(LIBRARY.find(e => e.n === 'Cat').i)"); await asyncio.sleep(0.3)
            await pg.fill('#tx-text', 'Hello from the Magician'); await pg.click('#tx-fonts .tx-font[data-key=allure]'); await pg.select_option('#tx-style', 'regular')
            await pg.fill('#tx-height', '9'); await pg.press('#tx-height', 'Tab'); await pg.fill('#tx-rot', '0'); await pg.press('#tx-rot', 'Tab')
            await pg.click('#btnTextAdd'); await asyncio.sleep(0.5)
            await pg.locator('#plotCanvas').scroll_into_view_if_needed(); await asyncio.sleep(0.3)
            card = pg.locator('#plotCanvas').locator('xpath=..')
            await card.screenshot(path=str(OUT / 'obj_card.png'))
            await pg.locator('#textCard').screenshot(path=str(OUT / 'text_card.png'))
            await pg.emulate_media(color_scheme='dark'); await ev('drawPlot()'); await asyncio.sleep(0.2)
            await card.screenshot(path=str(OUT / 'obj_card_dark.png'))
            await pg.locator('#textCard').screenshot(path=str(OUT / 'text_card_dark.png'))
            await pg.emulate_media(color_scheme='light')
            await pg.set_viewport_size({'width': 390, 'height': 900}); await asyncio.sleep(0.4); await ev('drawPlot()')
            await pg.locator('#textCard').screenshot(path=str(OUT / 'text_card_phone.png'))
            await card.screenshot(path=str(OUT / 'obj_card_phone.png'))
            overflow = await ev("document.documentElement.scrollWidth > window.innerWidth + 1")
            check('no sideways scrolling at phone width', not overflow)
            check('no page errors', not errors, '; '.join(errors[:3]))
            await b.close()
    finally:
        srv.terminate()
    bad = [n for n, ok in results if not ok]
    print(f'\n{len(results) - len(bad)}/{len(results)} passed' + (f' — FAILED: {bad}' if bad else ''))

asyncio.run(main())
