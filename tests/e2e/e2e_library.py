"""Browser test for the drawing library: the category list (every category with at least 50
drawings), search, coloured flag thumbnails, loading every drawing into the Plotter (each must fit the
green zone), keeping the place of a re-picked drawing, downloads (flags keep their colours), drawing one
on the simulated arm, the library folder matching the app, credits, and SVG files the old reader got
wrong (no namespace, invisible shapes, <use> copies, nested viewports).
Runs the real app with the built-in simulator in headless Chromium.
Needs Python 3 and Playwright (pip install playwright; playwright install chromium).
Run from anywhere: python3 tests/e2e/e2e_library.py"""
import asyncio, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
SRV = tempfile.mkdtemp(prefix='magician-e2e-')
shutil.copy(ROOT / 'magician-smart-controller.html', f'{SRV}/app.html')
sys.path.insert(0, str(HERE)); from fixtures import write_images; write_images(f'{SRV}/img')
PORT = 8776
# The library folder (the plotter-library zip from the release, unpacked) is optional. With it, the test also
# checks that every file in it is the same drawing as in the app: unpack it as plotter-library/ at the
# repository root, or point MAGICIAN_LIBRARY at it.
LIBDIR = os.environ.get('MAGICIAN_LIBRARY') or str(ROOT / 'plotter-library')
HAVE_LIB = os.path.exists(os.path.join(LIBDIR, 'library.json'))
if HAVE_LIB: shutil.copytree(LIBDIR, f'{SRV}/library')
else: print(f'(no library folder at {LIBDIR}: the checks against the folder are skipped)')
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

VISIBLE = "[...document.querySelectorAll('#lib-grid .lib-item')].filter(b => !b.hidden).map(b => b.querySelector('span').textContent)"
NUMS = re.compile(r'-?\d+(?:\.\d+)?')
def d_numbers(svg_text):
    return [float(v) for d in re.findall(r' d="([^"]+)"', svg_text) for v in NUMS.findall(d)]

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
            N = await ev('LIBRARY.length')
            ver = await ev("document.querySelector('.ver').textContent")
            check('version shows v1.4.0', ver == 'v1.4.0', ver)

            # calibrate in the simulator, so the green zone is a real one
            await pg.click('#btnSim'); await wait_for(ev, "!document.getElementById('autocal').hidden", 3000)
            await pg.click('[data-ac=start]'); await wait_for(ev, "AC.step === 'pen'", 15000)
            for _ in range(12):
                if await ev('S.pos.z') <= -58: break
                await pg.click('[data-dz="-10"]'); await wait_for(ev, '!AC.busy', 5000)
            await pg.click('[data-ac=paper]'); await wait_for(ev, "AC.step === 'done'", 10000)
            await pg.click('#autocalBody [data-ac=close]')

            # ---------- gallery and categories ----------
            check('the gallery is only built when the Plotter is opened', await ev("document.querySelectorAll('#lib-grid .lib-item').length") == 0)
            await pg.click('#nav-plot'); await asyncio.sleep(0.5)
            n = await ev("document.querySelectorAll('#lib-grid .lib-item').length")
            opts = await ev("[...document.querySelectorAll('#lib-cat option')].map(o => [o.value, o.textContent])")
            counts = {v: int(re.search(r'\((\d+)\)$', t).group(1)) for v, t in opts}
            check(f'{N} drawings in the gallery, all listed under "All categories"', n == N and opts[0][0] == 'all' and counts['all'] == N and
                  (not HAVE_LIB or len(json.load(open(os.path.join(LIBDIR, 'library.json')))) == N), opts[0][1])
            asked = ['animals', 'cars', 'nature', 'leaves', 'signs', 'zodiac', 'emojis', 'femalepose', 'malepose', 'faces', 'objects', 'skylines', 'topography', 'sports',
                     'clothing', 'shoes', 'sportscars', 'ants', 'aircraft', 'army', 'constellations', 'flags', 'technology', 'art', 'phones', 'music', 'songs', 'scifi']
            short = [f'{k} {counts.get(k, 0)}' for k in asked if counts.get(k, 0) < 50]
            check('the category list offers every requested category with at least 50 drawings', not short and len(opts) >= 29, ', '.join(short) or f'{len(opts) - 1} categories')
            check('every category in the list has at least 50', all(c >= 50 for v, c in counts.items()), ', '.join(f'{v} {c}' for v, c in counts.items() if c < 50))
            check('count reads the total', await ev("document.getElementById('lib-count').textContent") == f'{N} drawings')
            await pg.select_option('#lib-cat', 'flags'); await asyncio.sleep(0.6)
            vis = await ev(VISIBLE)
            check('Flags shows only the flags', len(vis) == counts['flags'] and 'New Zealand' in vis and 'Iran' in vis and await ev("document.getElementById('lib-count').textContent") == f"{counts['flags']} drawings", f'{len(vis)}: {", ".join(vis[:6])}…')
            await wait_for(ev, "!!document.querySelector('#lib-grid .lib-item[data-id=\"flags/flag-nz\"]').dataset.drawn", 5000)
            col = await ev("""(() => { const b = document.querySelector('#lib-grid .lib-item[data-id="flags/flag-nz"]'); if (!b.dataset.drawn) libThumb(b);
              return [...b.querySelectorAll('path')].map(p => p.style.fill).filter(Boolean); })()""")
            check('flag thumbnails keep their colours', len(col) >= 2 and any('rgb' in c or '#' in c for c in col), ', '.join(col[:4]))
            await pg.select_option('#lib-cat', 'malepose'); await asyncio.sleep(0.3)
            vis = await ev(VISIBLE)
            check('Male poses lists the new poses', counts['malepose'] >= 50 and 'Riding a bicycle' in vis and 'Push-up' in vis, f'{len(vis)} poses')
            await pg.select_option('#lib-cat', 'all'); await asyncio.sleep(0.2)
            await pg.fill('#lib-search', 'tehran'); await asyncio.sleep(0.2)
            vis = await ev(VISIBLE)
            check('search "tehran" finds the Tehran skyline', 'Tehran' in vis, ', '.join(vis))
            await pg.fill('#lib-search', 'ode to joy'); vis = await ev(VISIBLE)
            check('search finds a song by its title', 'Ode to Joy' in vis, ', '.join(vis))
            await pg.fill('#lib-search', 'skylines paris'); vis = await ev(VISIBLE)
            check('search words can match the category name too', vis == ['Paris'], ', '.join(vis))
            await pg.fill('#lib-search', 'gerald'); vis = await ev(VISIBLE)
            check('search also finds an artist\'s drawings', len(vis) >= 10 and 'Harp' in vis, f'{len(vis)} by Gerald G.')
            await pg.fill('#lib-search', 'zzzz'); await asyncio.sleep(0.1)
            check('no match shows a friendly message', await ev("!document.getElementById('lib-none').hidden") and await ev(VISIBLE) == [])
            await pg.fill('#lib-search', ''); await asyncio.sleep(0.1)
            check('clearing the search shows all again', len(await ev(VISIBLE)) == N)

            # ---------- pick one ----------
            await pg.click('#lib-grid .lib-item[data-id="animals/lion"]'); await asyncio.sleep(0.5)
            st = await ev("({ name: document.getElementById('plot-file-name').textContent, ops: !!S.plot.ops, label: S.plot.label, size: S.plot.place.size, sel: document.querySelector('#lib-grid .lib-item.sel')?.dataset.id, save: document.getElementById('btnLibSave').disabled })")
            check('clicking a drawing loads it into the Plotter, ready to draw', st['ops'] and st['label'] == 'Lion' and st['name'].startswith('Library: Lion — by Architetto Francesco Rollandin'), st['name'])
            check('it is placed large on the paper and marked as chosen', st['size'] >= 60 and st['sel'] == 'animals/lion' and not st['save'], f"{st['size']:.0f} mm")
            async with pg.expect_download() as dl_info:
                await pg.click('#btnLibSave')
            dl = await dl_info.value
            text = open(await dl.path()).read()
            check('Download SVG saves the drawing, the same lines as the library folder', dl.suggested_filename == 'lion.svg' and '<svg xmlns=' in text and
                  (not HAVE_LIB or d_numbers(text) == d_numbers(open(f'{LIBDIR}/animals/lion.svg').read())))

            # re-picking the same drawing keeps where it was put; a new one starts in the middle
            await ev("setPlace({ ...S.plot.place, cx: S.plot.place.cx + 8, size: S.plot.place.size * 0.8 }); buildPlot()")
            moved = await ev('S.plot.place')
            await pg.click('#lib-grid .lib-item[data-id="animals/lion"]'); await asyncio.sleep(0.3)
            again = await ev('S.plot.place')
            check('picking the same drawing again keeps its size and place', abs(again['cx'] - moved['cx']) < 1e-6 and abs(again['size'] - moved['size']) < 1e-6)
            await pg.click('#lib-grid .lib-item[data-id="animals/owl"]'); await asyncio.sleep(0.3)
            check('a different drawing gets its own default place', abs(await ev('S.plot.place.size') - moved['size']) > 1 and await ev('S.plot.label') == 'Owl')

            # a flag downloads with its colours
            await ev("S.plot.objects = []; S.plot.sel = null; onSelectionChange()")
            await ev("libLoad('flags/flag-nz')"); await asyncio.sleep(0.3)
            async with pg.expect_download() as dl_info:
                await pg.click('#btnLibSave')
            dl = await dl_info.value
            text = open(await dl.path()).read()
            fills = re.findall(r'fill="(#[0-9a-fA-F]{6})"', text)
            check('a downloaded flag keeps its colours and matches the folder', dl.suggested_filename == 'flag-nz.svg' and len(set(fills)) >= 3 and
                  (not HAVE_LIB or d_numbers(text) == d_numbers(open(f'{LIBDIR}/flags/flag-nz.svg').read())), ', '.join(sorted(set(fills))))
            check('the flag loads into the Plotter as lines', await ev("S.plot.label === 'New Zealand' && !!S.plot.ops && S.plot.strokes.length > 5"))

            # ---------- every drawing ----------
            bad, small, ms = [], [], []
            for start in range(0, N, 250):
                r = await ev("""([a, z]) => { const out = { bad: [], ms: [], small: [] };
                  for (const e of LIBRARY.slice(a, z)) { S.plot.objects = []; S.plot.sel = null;          // each one on an empty sheet
                    const t0 = performance.now(); libLoad(e.i); out.ms.push(performance.now() - t0);
                    if (!S.plot.ops || S.plot.label !== e.n || S.plot.strokes.length < 1) out.bad.push(e.i);
                    else if (S.plot.place.size < 60) out.small.push(e.i + ' ' + S.plot.place.size.toFixed(0)); }
                  return out; }""", [start, start + 250])
                bad += r['bad']; small += r['small']; ms += r['ms']
            ms.sort()
            check(f'all {N} drawings load, fit the green zone and are ready to draw', not bad, ', '.join(bad[:8]))
            check('each one is placed at 60 mm or larger by default', not small, ', '.join(small[:8]))
            check('loading is quick', ms[-1] < 2500, f"median {ms[len(ms) // 2]:.0f} ms, slowest {ms[-1]:.0f} ms (includes path planning)")
            logs_bad = await ev("[...document.querySelectorAll('#log .err')].map(e => e.textContent)")
            check('no errors were logged', not logs_bad, '; '.join(logs_bad[:3]))

            # ---------- the folder matches the app ----------
            if HAVE_LIB:
                folder = await ev("""(async () => { const out = { bad: [], n: 0 }; const L = await (await fetch('library/library.json')).json();
                  const nums = t => [...t.matchAll(/ d="([^"]+)"/g)].map(m => m[1]).join(' ').match(/-?\\d+(?:\\.\\d+)?/g).join(',');
                  for (const f of L) { out.n++; const txt = await (await fetch('library/' + f.file)).text(); const e = LIBRARY.find(x => x.i === f.id);
                    if (!e || f.lines !== e.l || f.name !== e.n || nums(txt) !== nums(libSvg(e)) || svgToStrokes(txt).length < 1) out.bad.push(f.file); }
                  return out; })()""")
                check('every file in the library folder is the same drawing as in the app', folder['n'] == N and not folder['bad'], ', '.join(folder['bad'][:5]))
            else:
                print('SKIP every file in the library folder is the same drawing as in the app  (no library folder)')

            # ---------- credits ----------
            await pg.click('#lib-credits summary'); await asyncio.sleep(0.3)
            cred = await ev("document.querySelector('#lib-credits .lib-credit-body').textContent")
            check('credits list every source with its licence and the MIT/BSD notices', all(s in cred for s in ('Openclipart', 'Tabler Icons', 'd3-celestial', 'flag-icons', 'Hershey', 'Made for this library'))
                  and cred.count('Permission is hereby granted') >= 2 and 'Redistribution and use' in cred)
            await pg.click('#lib-credits summary')

            # ---------- draw one on the simulated arm ----------
            await ev("S.plot.objects = []; S.plot.sel = null; onSelectionChange()")
            await pg.click('#lib-grid .lib-item[data-id="food/soup"]'); await asyncio.sleep(0.4)
            await pg.click('#btnDraw'); await wait_for(ev, 'S.running', 3000, 20); await wait_for(ev, '!S.running', 60000)
            job = await ev('(() => { const j = S.paper.jobs[S.paper.jobs.length - 1]; return j ? { done: j.done, n: j.cmds.length, label: j.label || null } : null; })()')
            check('a library drawing draws to the end on the simulated arm', job and job['done'], json.dumps(job))

            # ---------- other sources clear the choice ----------
            await pg.click('#tab-plot details summary')
            await pg.fill('#plot-text', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>')
            await pg.click('#btnLoadText'); await asyncio.sleep(0.4)
            check('loading another SVG clears the library choice', await ev("!document.querySelector('#lib-grid .lib-item.sel') && document.getElementById('btnLibSave').disabled && S.plot.label === 'pasted SVG'"))

            # ---------- SVG reader fixes ----------
            cases = await ev(r"""(() => { const r = {}, box = st => { let a = Infinity, b = Infinity, c = -Infinity, d = -Infinity; for (const s of st) for (const p of s) { a = Math.min(a, p.x); b = Math.min(b, p.y); c = Math.max(c, p.x); d = Math.max(d, p.y); } return [a, b, c, d].map(v => Math.round(v * 10) / 10); };
              r.noNs = svgToStrokes('<svg width="100" height="100"><path d="M10 10 L90 90"/><rect x="5" y="5" width="20" height="10"/></svg>').length;
              r.invisible = svgToStrokes('<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="500" height="500" fill="none" stroke="none"/><circle cx="50" cy="50" r="10"/><path d="M0 0 L9 9" style="fill:none;stroke:none"/><path d="M0 0 L5 5" stroke="#000" stroke-opacity="0" fill="none"/></svg>').length;
              r.hiddenGroup = svgToStrokes('<svg xmlns="http://www.w3.org/2000/svg"><g style="display:none"><path d="M0 0 L100 0"/></g><g visibility="hidden"><path d="M0 9 L100 9"/></g><g opacity="0"><path d="M0 7 L100 7"/></g><path d="M0 50 L50 50"/></svg>').length;
              r.use = box(svgToStrokes('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><path id="p" d="M0 0 L10 0"/></defs><use xlink:href="#p" x="100" y="20"/><use href="#p" transform="translate(0 50)"/></svg>'));
              r.symbol = svgToStrokes('<svg xmlns="http://www.w3.org/2000/svg"><symbol id="s"><circle cx="5" cy="5" r="4"/></symbol><use href="#s" x="30"/><use href="#s" x="60"/></svg>').length;
              r.round = svgToStrokes('<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="100" height="60" rx="10"/></svg>')[0].length;
              r.nested = box(svgToStrokes('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"><svg x="100" y="100" width="200" height="200" viewBox="0 0 10 10"><path d="M0 0 L10 10"/></svg></svg>'));
              r.noXlinkNs = svgToStrokes('<svg width="50" height="50"><defs><path id="q" d="M0 0 L10 10"/></defs><use xlink:href="#q" x="5"/></svg>').length;
              let big = 'M0 0'; for (let i = 1; i <= 20000; i++) big += ` L${i % 2 ? 10 : 0} ${i * 0.05}`;
              let t0 = performance.now(); r.bigN = svgToStrokes('<svg xmlns="http://www.w3.org/2000/svg"><path d="' + big + '"/></svg>')[0].length; r.bigMs = Math.round(performance.now() - t0);
              let curvy = 'M0 0'; for (let i = 0; i < 3000; i++) curvy += ` c 2 -4 6 -4 8 0`;
              t0 = performance.now(); r.curvyN = svgToStrokes('<svg xmlns="http://www.w3.org/2000/svg"><path fill="none" stroke="#000" d="' + curvy + '"/></svg>').length; r.curvyMs = Math.round(performance.now() - t0);
              return r; })()""")
            check('SVG files without the SVG namespace load', cases['noNs'] == 2, f"{cases['noNs']} strokes")
            check('invisible shapes are skipped (no fill and no outline, or fully transparent)', cases['invisible'] == 1, f"{cases['invisible']} stroke")
            check('hidden or transparent groups are skipped', cases['hiddenGroup'] == 1, f"{cases['hiddenGroup']} stroke")
            check('<use> copies are drawn where they are placed', cases['use'] == [0, 20, 110, 50], f"{cases['use']}")
            check('symbols used twice are drawn twice', cases['symbol'] == 2)
            check('rounded rectangles keep their rounded corners', cases['round'] > 20, f"{cases['round']} points")
            check('nested viewports are scaled correctly', cases['nested'] == [100, 100, 300, 300], f"{cases['nested']}")
            check('files using xlink without declaring it still load', cases['noXlinkNs'] == 1)
            check('a 20 000-segment path reads fast', cases['bigN'] == 20001 and cases['bigMs'] < 1000, f"{cases['bigMs']} ms")
            check('3 000 curves read fast', cases['curvyN'] == 1 and cases['curvyMs'] < 1000, f"{cases['curvyMs']} ms")

            # ---------- look ----------
            await pg.select_option('#lib-cat', 'flags'); await asyncio.sleep(0.5)
            await pg.evaluate("document.querySelector('header').style.position = 'relative'")
            card = await pg.query_selector('#libCard')
            await card.screenshot(path=str(OUT / 'lib_card_light.png'))
            await pg.emulate_media(color_scheme='dark'); await asyncio.sleep(0.2)
            await card.screenshot(path=str(OUT / 'lib_card_dark.png'))
            await pg.emulate_media(color_scheme='light')
            await pg.select_option('#lib-cat', 'femalepose'); await asyncio.sleep(0.5)
            await card.screenshot(path=str(OUT / 'lib_card_poses.png'))
            await pg.set_viewport_size({'width': 390, 'height': 900}); await asyncio.sleep(0.3)
            await card.screenshot(path=str(OUT / 'lib_card_phone.png'))
            wide = await ev("document.documentElement.scrollWidth <= window.innerWidth + 1")
            check('the library fits a phone-width screen without sideways scrolling', wide)
            await pg.set_viewport_size({'width': 1280, 'height': 1100})

            check('no page errors', not errors, '; '.join(errors[:3]))
            await b.close()
    finally:
        srv.terminate()
    bad = [n for n, ok in results if not ok]
    print(f'\n{len(results) - len(bad)}/{len(results)} passed' + (f'; FAILED: {bad}' if bad else ''))
    sys.exit(1 if bad else 0)

asyncio.run(main())
