"""Browser test: Persian text in the Text tool — the switch, the right-to-left text box, adding and
editing Persian text, English and numbers inside it, Persian digits, switching off and on with text
selected, remembering the setting, saving it with the layout, and drawing it on the simulator.
Runs the real app against the built-in kinematic simulator in headless Chromium.
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_persian.py"""
import asyncio, json, pathlib, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
PORT = 8783
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

HELPERS = r"""
window.T = {
  objs() { return S.plot.objects.map(o => ({ id: o.id, kind: o.kind, label: o.label, text: o.text || null, missing: o.missing || [], n: o.sketch.strokes.length })); },
  inside() { const z = drawZone(), ops = S.plot.ops; if (!ops) return { ok: false, why: 'no ops' }; let prev = S.plot.start, bad = 0;
    for (const o of ops) { if (o.pen) { const r = Math.hypot(o.x, o.y), th = Math.atan2(o.y, o.x) / RAD;
        if (r > z.rOut + 1e-6 || th < z.thMin - 1e-6 || th > z.thMax + 1e-6) bad++;
        if (segDist0(prev.x, prev.y, o.x, o.y) < z.rIn - 1e-6) bad++; } prev = o; }
    return { ok: bad === 0 && S.plot.opsVer === S.plot.placeVer, bad }; },
  textOrigin(id) { const o = objById(id), sk = o.sketch, u = { x: -sk.srcBox.cx / sk.srcBox.L, y: -sk.srcBox.cy / sk.srcBox.L }; return placeXform(o.place)(u); },
  ui() { const ta = document.getElementById('tx-text'), vis = [...document.querySelectorAll('#tx-fonts .tx-font')].filter(b => !b.hidden);
    return { dir: ta.dir, lang: ta.lang, ph: ta.placeholder, digitsShown: !document.getElementById('tx-fadigits-wrap').hidden, on: document.getElementById('tx-fa').checked,
      fonts: vis.map(b => b.dataset.key), pressed: (document.querySelector('#tx-fonts .tx-font[aria-pressed=true]') || {}).dataset?.key,
      noItalic: [...document.getElementById('tx-style').options].filter(o => o.disabled).map(o => o.value), align: document.getElementById('tx-align').value,
      info: document.getElementById('tx-info').textContent }; },
};
"""

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
            await ev("localStorage.clear()"); await pg.reload()
            await ev(HELPERS)

            # calibrate on the simulator, so the green zone is a real one
            await pg.click('#btnSim'); await wait_for(ev, "!document.getElementById('autocal').hidden", 3000)
            await pg.click('[data-ac=start]'); await wait_for(ev, "AC.step === 'pen'", 15000)
            for _ in range(12):
                if await ev('S.pos.z') <= -68: break
                await pg.click('[data-dz="-10"]'); await wait_for(ev, '!AC.busy', 5000)
            for _ in range(10):
                if await ev('S.pos.z') <= -71.5: break
                await pg.click('[data-dz="-0.5"]'); await wait_for(ev, '!AC.busy', 5000)
            await pg.click('[data-ac=paper]'); await wait_for(ev, "AC.step === 'done'", 10000)
            await pg.click('#autocalBody [data-ac=close]')
            await pg.click('#nav-plot'); await asyncio.sleep(0.3)
            await pg.locator('#textCard').scroll_into_view_if_needed()

            # ---------- the switch ----------
            sw = await ev("(() => { const el = document.getElementById('tx-fa'); return { role: el.getAttribute('role'), fb: el.classList.contains('sw-fb'), native: 'switch' in HTMLInputElement.prototype, checked: el.checked, label: el.closest('label').textContent.trim() }; })()")
            check('a Persian switch in the Text card, announced as a switch, off at first', (sw['native'] or (sw['role'] == 'switch' and sw['fb'])) and not sw['checked'] and 'Persian' in sw['label'], json.dumps(sw, ensure_ascii=False))
            await pg.locator('#textCard').screenshot(path=str(OUT / 'persian-card-off.png'))
            await pg.click('label.tx-switch:has(#tx-fa)'); await asyncio.sleep(0.3)
            ui = await ev('T.ui()')
            check('switched on: the text box writes right to left in Persian, Persian digits offered', ui['on'] and ui['dir'] == 'rtl' and ui['lang'] == 'fa' and ui['digitsShown'] and 'متن' in ui['ph'], json.dumps(ui, ensure_ascii=False)[:160])
            check('only the Persian font is shown (pressed), italic is off, alignment kept at centre', ui['fonts'] == ['persian'] and ui['pressed'] == 'persian' and sorted(ui['noItalic']) == ['bolditalic', 'italic'] and ui['align'] == 'center')
            fb = await ev("getComputedStyle(document.getElementById('tx-fa')).backgroundColor")
            check('the switch shows on (accent colour)', fb not in ('rgba(0, 0, 0, 0)', 'transparent'), fb)

            # ---------- add Persian text ----------
            await pg.fill('#tx-text', 'سلام دنیا ۱۴۰۵')
            await pg.click('#btnTextAdd'); await asyncio.sleep(0.6)
            objs = await ev('T.objs()'); t = objs[-1]
            last = await ev("document.querySelector('#log div').textContent")              # newest first
            want = await ev("textLayout({ str: 'سلام دنیا ۱۴۰۵', lang: 'fa' }).strokes.length")
            check('Add text: a Persian text object in the Persian font, nothing left out', t['kind'] == 'text' and t['text']['lang'] == 'fa' and not t['missing'] and t['n'] == want and 'Vazir (Persian)' in last, last[:90])
            ins = await ev('T.inside()')
            check('it is in the drawing path, every line inside the green zone', ins['ok'] and await ev(f"S.plot.drawnIds.includes({t['id']})"))
            lbl = await ev("(() => { const n = document.querySelector('#obj-list .obj-item.sel .obj-name span:nth-child(2)'); return { text: n.textContent, dir: n.dir }; })()")
            check('the object list shows its Persian label (direction from the text)', lbl['text'] == 'سلام دنیا ۱۴۰۵' and lbl['dir'] == 'auto', json.dumps(lbl, ensure_ascii=False))

            # ---------- editing: English and numbers inside, alignment ----------
            o0 = await ev(f"T.textOrigin({t['id']})")
            await pg.fill('#tx-text', 'ربات Dobot مدل 2026 (آزمایش)'); await asyncio.sleep(0.6)
            ed = await ev(f"(() => {{ const o = objById({t['id']}); return {{ str: o.text.str, missing: o.missing, n: o.sketch.strokes.length, want: textLayout(o.text).strokes.length }}; }})()")
            o1 = await ev(f"T.textOrigin({t['id']})")
            check('typing changes the selected text; English and numbers inside are drawn too', ed['str'].startswith('ربات Dobot') and not ed['missing'] and ed['n'] == ed['want'], json.dumps(ed, ensure_ascii=False))
            check('editing keeps the text\'s start point where it was', abs(o1['x'] - o0['x']) < 0.05 and abs(o1['y'] - o0['y']) < 0.05)
            dg = await ev("(() => { const a = textLayout({ str: '2026', lang: 'fa' }).strokes, b = textLayout({ str: '۲۰۲۶', lang: 'fa' }).strokes, c = textLayout({ str: '2026', lang: 'fa', faDigits: false }).strokes; return { persian: JSON.stringify(a) === JSON.stringify(b), latin: JSON.stringify(a) !== JSON.stringify(c) }; })()")
            n_on = await ev(f"objById({t['id']}).sketch.strokes.length")
            await pg.click('label.tx-switch:has(#tx-fadigits)'); await asyncio.sleep(0.4)
            dd = await ev(f"(() => {{ const o = objById({t['id']}); return {{ fd: o.text.faDigits, same: JSON.stringify(o.sketch.strokes.length) }}; }})()")
            check('Persian digits: 2026 is drawn as ۲۰۲۶; switching it off draws 2026 as typed', dg['persian'] and dg['latin'] and dd['fd'] is False, json.dumps(dd))
            await pg.click('label.tx-switch:has(#tx-fadigits)'); await asyncio.sleep(0.3)
            await pg.select_option('#tx-align', 'right'); await asyncio.sleep(0.4)
            await pg.select_option('#tx-style', 'bold'); await asyncio.sleep(0.4)
            bo = await ev(f"(() => {{ const o = objById({t['id']}); return {{ style: o.text.style, align: o.text.align, n: o.sketch.strokes.length }}; }})()")
            check('right alignment and bold work for Persian (bold: a second pen line)', bo['style'] == 'bold' and bo['align'] == 'right' and bo['n'] == 2 * n_on, json.dumps(bo))
            await pg.select_option('#tx-style', 'regular'); await asyncio.sleep(0.3)

            # ---------- switching off and on with the text selected ----------
            await pg.click('label.tx-switch:has(#tx-fa)'); await asyncio.sleep(0.5)
            off = await ev(f"(() => {{ const o = objById({t['id']}); return {{ lang: o.text.lang, align: o.text.align, missing: o.missing.length, ui: T.ui() }}; }})()")
            check('switching Persian off: the text box is left to right again, Persian letters are reported missing with a hint', off['lang'] == 'en' and off['align'] == 'left' and off['missing'] > 5 and off['ui']['dir'] == 'ltr' and 'switch Persian on' in off['ui']['info'] and len(off['ui']['fonts']) == 13, json.dumps({k: off[k] for k in ('lang', 'align', 'missing')}))
            await pg.click('label.tx-switch:has(#tx-fa)'); await asyncio.sleep(0.5)
            on = await ev(f"(() => {{ const o = objById({t['id']}); return {{ lang: o.text.lang, align: o.text.align, missing: o.missing.length }}; }})()")
            check('and on again: Persian, right aligned, nothing missing', on['lang'] == 'fa' and on['align'] == 'right' and on['missing'] == 0, json.dumps(on))
            await pg.locator('#textCard').screenshot(path=str(OUT / 'persian-card-on.png'))

            # ---------- remembered, and saved with the layout ----------
            lay = await ev("JSON.parse(JSON.stringify(S.plot.objects.map(o => o.text || null)))")
            rt = await ev("layoutObjects(JSON.parse(JSON.stringify(layoutData()))).map(o => ({ lang: o.text && o.text.lang, n: o.sketch.strokes.length }))")
            check('a saved layout keeps the text Persian', any(x and x.get('lang') == 'fa' for x in lay) and any(r['lang'] == 'fa' and r['n'] > 10 for r in rt), json.dumps(rt))

            # ---------- draw it on the simulator ----------
            await pg.screenshot(path=str(OUT / 'persian-map.png'), full_page=False)
            jobs0 = await ev('S.paper.jobs.length')
            await pg.click('#btnDraw')
            await wait_for(ev, '!S.running && S.paper.jobs.length > ' + str(jobs0), 120000, 200)
            dj = await ev("(() => { const j = S.paper.jobs[S.paper.jobs.length - 1]; return { done: j && j.done, n: j && j.cmds.length }; })()")
            check('Draw: the Persian text is drawn on the simulator', dj['done'] and dj['n'] > 50, json.dumps(dj))
            await pg.locator('#plotCanvas').screenshot(path=str(OUT / 'persian-drawn.png'))

            await pg.reload(); await asyncio.sleep(0.5)
            await ev(HELPERS)
            rem = await ev('T.ui()')
            check('after reloading, Persian is still on for new text', rem['on'] and rem['dir'] == 'rtl', json.dumps({k: rem[k] for k in ('on', 'dir')}))
            check('no page errors', not errors, '; '.join(errors[:3]))
            await b.close()
    finally:
        srv.terminate()
    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks passed" + (f"; FAILED: {bad}" if bad else ''))
    sys.exit(1 if bad else 0)

asyncio.run(main())
