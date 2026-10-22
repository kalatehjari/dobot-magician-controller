"""Builds the big plotter library (v2): every category, the app's embedded copy and the SVG folder.
Sources: the first 100 drawings (Openclipart), more Openclipart picks (oca_picks.py), Tabler icons, and the
generated categories (items/*.json).
Usage: python3 -I export2.py <out folder> <app source folder>"""
import html, json, math, os, re, sys, shutil, unicodedata, importlib.util
from collections import Counter, OrderedDict

OUT, APP = sys.argv[1:3]
# inputs: items/*.json (from the generators) and review/ (Openclipart review sheets) beside this script; traced Openclipart
# strokes in MAGICIAN_LIBRARY_WORK; the 1.2.0 library folder in MAGICIAN_LIBRARY_V1
V2 = os.path.dirname(os.path.abspath(__file__)); W = os.environ.get('MAGICIAN_LIBRARY_WORK', os.path.join(V2, 'work'))

CATS = [('animals', 'Animals'), ('cars', 'Cars'), ('nature', 'Nature'), ('leaves', 'Leaves'), ('signs', 'Signs'), ('zodiac', 'Zodiac'),
        ('emojis', 'Emojis'), ('femalepose', 'Female poses'), ('malepose', 'Male poses'), ('faces', 'Faces'), ('objects', 'Objects'),
        ('skylines', 'City skylines'), ('topography', 'Topography'), ('sports', 'Sports'), ('clothing', 'Clothing and outfits'), ('shoes', 'Shoes'),
        ('sportscars', 'Sports cars'), ('ants', 'Ants'), ('aircraft', 'Aircraft'), ('army', 'Army'), ('constellations', 'Constellations'),
        ('flags', 'Flags'), ('technology', 'Technology'), ('art', 'Art'), ('phones', 'Phones and electronics'), ('music', 'Music'),
        ('songs', 'Songs'), ('scifi', 'Sci-fi'), ('food', 'Food and drink'), ('places', 'Places and buildings'), ('transport', 'Boats, trains and more')]
CATNAME = dict(CATS)

SOURCES = OrderedDict([
  ('openclipart', {'name': 'Openclipart', 'license': 'Public domain', 'url': 'https://openclipart.org',
                   'note': 'Artists release their work into the public domain (Creative Commons Public Domain Dedication). From the openclipart-svg 0.18 collection, which keeps each artist\'s name and title in the file.'}),
  ('generated', {'name': 'Made for this library', 'license': 'Public domain', 'author': 'Made for this library',
                 'note': 'Drawn by program for this library (shapes, curves, maps, figures, music and lettering). Free to use for anything.'}),
  ('tabler-icons', {'name': 'Tabler Icons', 'license': 'MIT', 'author': 'Paweł Kuna (Tabler Icons)', 'url': 'https://tabler.io/icons', 'notice': 'tabler'}),
  ('d3-celestial', {'name': 'd3-celestial', 'license': 'BSD 3-Clause', 'author': 'Olaf Frohn (d3-celestial)', 'url': 'https://github.com/ofrohn/d3-celestial', 'notice': 'celestial',
                    'note': 'Constellation lines and star positions and brightness (from the Hipparcos and XHIP catalogues).'}),
  ('flag-icons', {'name': 'flag-icons', 'license': 'MIT', 'author': 'flag-icons contributors', 'url': 'https://github.com/lipis/flag-icons', 'notice': 'flagicons'}),
  ('hershey', {'name': 'Hershey fonts', 'license': 'Hershey fonts licence (free use with acknowledgement)', 'author': 'A. V. Hershey',
               'note': 'The Hershey Fonts were originally created by Dr. A. V. Hershey while working at the U. S. National Bureau of Standards.'}),
])

# ---------------------------------------------------------------- geometry
def rdp(pts, eps):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts) - 1)]
    while stack:
        i0, i1 = stack.pop(); a, b = pts[i0], pts[i1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
        best, bi = -1, 0
        for i in range(i0 + 1, i1):
            p = pts[i]
            d = abs(dy * (p[0] - a[0]) - dx * (p[1] - a[1])) / L if L else math.hypot(p[0] - a[0], p[1] - a[1])
            if d > best: best, bi = d, i
        if best > eps: keep[bi] = True; stack += [(i0, bi), (bi, i1)]
    return [p for p, k in zip(pts, keep) if k]

def rdp_keep_extremes(pts, eps):
    """RDP that never drops a stroke's leftmost, rightmost, top or bottom point, so the drawing keeps its exact box."""
    if len(pts) < 3: return pts
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cut = sorted({0, len(pts) - 1, xs.index(min(xs)), xs.index(max(xs)), ys.index(min(ys)), ys.index(max(ys))})
    out = [pts[0]]
    for a, b in zip(cut, cut[1:]):
        out += rdp(pts[a:b + 1], eps)[1:]
    return out

def plen(s): return sum(math.hypot(s[i][0] - s[i - 1][0], s[i][1] - s[i - 1][1]) for i in range(1, len(s)))

def order(strokes):
    """Nearest-neighbour stroke order (strokes may be reversed); strokes that continue exactly where the
    previous one ended are joined, so the pen lifts less often. Uses a grid for big drawings."""
    left = list(range(len(strokes))); out = []; cur = (0, 0); used = [False] * len(strokes)
    cell = 40; grid = {}
    for i, s in enumerate(strokes):
        for e in (s[0], s[-1]): grid.setdefault((int(e[0] // cell), int(e[1] // cell)), []).append(i)
    remaining = len(strokes)
    while remaining:
        best = None; r = 0
        cx, cy = int(cur[0] // cell), int(cur[1] // cell)
        while best is None or r <= best[0] / cell + 1:
            for gx in range(cx - r, cx + r + 1):
                for gy in range(cy - r, cy + r + 1):
                    if max(abs(gx - cx), abs(gy - cy)) != r: continue
                    for i in grid.get((gx, gy), ()):
                        if used[i]: continue
                        s = strokes[i]
                        d0 = math.hypot(s[0][0] - cur[0], s[0][1] - cur[1]); d1 = math.hypot(s[-1][0] - cur[0], s[-1][1] - cur[1])
                        if best is None or d0 < best[0]: best = (d0, i, False)
                        if d1 < best[0]: best = (d1, i, True)
            r += 1
            if r > 60 and best is None:      # nothing near: fall back to a full scan
                for i in range(len(strokes)):
                    if used[i]: continue
                    s = strokes[i]
                    d0 = math.hypot(s[0][0] - cur[0], s[0][1] - cur[1]); d1 = math.hypot(s[-1][0] - cur[0], s[-1][1] - cur[1])
                    if best is None or d0 < best[0]: best = (d0, i, False)
                    if d1 < best[0]: best = (d1, i, True)
                break
        _, i, rev = best; used[i] = True; remaining -= 1
        s = strokes[i][::-1] if rev else strokes[i]
        if out and math.hypot(out[-1][-1][0] - s[0][0], out[-1][-1][1] - s[0][1]) <= 1: out[-1] = out[-1] + (s[1:] if tuple(s[0]) == tuple(out[-1][-1]) else s)
        else: out.append(list(s))
        cur = out[-1][-1]
    return out

def normalise(S, eps=0.6, keep_order=False):
    """Longest side 1000 units, simplified, integer points; returns (strokes, w, h, kept) where kept lists
    the input index of every surviving stroke (used to keep colour fills pointing at the right strokes)."""
    S0 = [[(float(x), float(y)) for x, y in s] for s in S]
    use = [i for i, s in enumerate(S0) if len(s) > 1]
    for _ in range(4):           # tiny strokes that vanish when rounded must not set the box
        xs = [p[0] for i in use for p in S0[i]]; ys = [p[1] for i in use for p in S0[i]]
        if not xs: return [], 0, 0, []
        x0, y0 = min(xs), min(ys); k = 1000 / max(max(xs) - x0, max(ys) - y0, 1e-9)
        out, kept = [], []
        for i in use:
            s = rdp_keep_extremes([((x - x0) * k, (y - y0) * k) for x, y in S0[i]], eps)
            s = [(round(x), round(y)) for x, y in s]
            s = [p for j, p in enumerate(s) if j == 0 or p != s[j - 1]]
            if len(s) > 1: out.append(s); kept.append(i)
        if kept == use: break
        use = kept
    if not out: return [], 0, 0, []
    if not keep_order: out = order(out)
    w = max(p[0] for s in out for p in s); h = max(p[1] for s in out for p in s)
    return out, w, h, kept

def remap_fills(fills, kept):
    """Fill ranges refer to input stroke indices; move them onto the strokes that survived."""
    new = {old: i for i, old in enumerate(kept)}
    out = []
    for col, a, b in fills:
        idx = [new[j] for j in range(a, b) if j in new]
        if idx: out.append([col, min(idx), max(idx) + 1])
    return out or None

B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
def varint(v):
    out = ''
    while True:
        d = v & 31; v >>= 5
        if v: out += B64[32 + d]
        else: return out + B64[d]
def zz(v): return (v << 1) if v >= 0 else ((-v << 1) - 1)
def encode(S):
    parts, px, py = [], 0, 0
    for s in S:
        parts.append(varint(len(s)))
        for x, y in s: parts.append(varint(zz(x - px)) + varint(zz(y - py))); px, py = x, y
    return ''.join(parts)

def path_d(S):
    return ''.join('M' + ' L'.join(f'{x} {y}' for x, y in s) for s in S)

def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'drawing'

def clean_title(t):
    t = html.unescape(t or '')
    t = re.sub(r'\(?\s*(e-?mail:?\s*)?[\w.+-]+@[\w-]+(\.[\w-]+)+\s*\)?', '', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip()
    return {'mo': 'Mo'}.get(t, t)

# ---------------------------------------------------------------- collect
entries = []
def add(cat, name, strokes, source, author, title='', origin='', license='', fills=None, eps=0.6, slug=None):
    if cat not in CATNAME: raise ValueError('unknown category ' + cat)
    S, w, h, kept = normalise(strokes, eps=eps, keep_order=bool(fills))
    if not S: print('  empty:', cat, name); return
    if fills: fills = remap_fills(fills, kept)
    entries.append({'cat': cat, 'name': name, 'S': S, 'w': w, 'h': h, 'source': source, 'author': author or SOURCES[source].get('author', ''),
                    'title': title or name, 'origin': origin, 'license': license or SOURCES[source]['license'], 'fills': fills, 'slug': slug or slugify(name)})

# 1) the first 100 drawings, in their new categories
REMAP = {'animals': 'animals', 'birds': 'animals', 'bugs': 'animals', 'plants': 'nature', 'food': 'food', 'places': 'places', 'science': 'technology',
         'tools': 'objects', 'music': 'music', 'fun': 'objects', 'patterns': 'art'}
SPECIAL = {'transport/airliner': 'aircraft', 'transport/light-aircraft': 'aircraft', 'transport/rocket': 'scifi', 'transport/little-car': 'cars',
           'plants/maple-leaf': 'leaves', 'science/saturn': 'nature', 'tools/hiking-boot': 'shoes'}
OLD = os.environ.get('MAGICIAN_LIBRARY_V1', os.path.join(V2, 'plotter-library-v1'))
def parse_rel_d(d):
    S = []
    for m in re.finditer(r'M(-?\d+) (-?\d+)l([^M]*)', d):
        x, y = int(m.group(1)), int(m.group(2)); s = [(x, y)]
        nums = [int(v) for v in re.findall(r'-?\d+', m.group(3))]
        for i in range(0, len(nums) - 1, 2): x += nums[i]; y += nums[i + 1]; s.append((x, y))
        S.append(s)
    return S
for e in json.load(open(f'{OLD}/library.json')):
    svg = open(f"{OLD}/{e['file']}").read()
    d = re.search(r' d="([^"]+)"', svg).group(1)
    cat = SPECIAL.get(e['id']) or ('transport' if e['cat'] == 'transport' else REMAP[e['cat']])
    add(cat, e['name'], parse_rel_d(d), 'openclipart', e['author'] if e['author'] != 'unknown' else 'Artist not recorded', clean_title(e['title']), e['source'], eps=0.3,
        slug=e['id'].split('/')[1])

# 2) more Openclipart picks
spec = importlib.util.spec_from_file_location('picks', f'{V2}/oca_picks.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
traced = {r['path']: r for f in ['traced.json', 'traced2.json'] for r in json.load(open(f'{W}/{f}'))}
for group, picks in m.PICKS.items():
    idx = {r['i']: r for r in json.load(open(f'{V2}/review/{group}.json'))}
    for i, cat, name in picks:
        r = idx[i]; t = traced[r['path']]
        S = [list(zip(s[0::2], s[1::2])) for s in t['strokes']]
        S = [s for s in S if len(s) > 1]
        author = clean_title(t.get('creator')) or 'Artist not recorded'
        add(cat, name, S, 'openclipart', author, clean_title(t.get('title')) or name, r['path'], eps=1.0)

# 3) generated and icon sets
GEN_ORDER = ['tabler.json']   # icons go after the pictures of the same category
files = sorted(f for f in os.listdir(f'{V2}/items') if f.endswith('.json'))
for f in [x for x in files if x not in GEN_ORDER] + [x for x in GEN_ORDER if x in files]:
    for it in json.load(open(f'{V2}/items/{f}')):
        src = it.get('source', 'generated')
        if src not in SOURCES: src = 'generated'
        add(it['cat'], it['name'], it['strokes'], src, it.get('author'), it.get('title', ''), it.get('origin', ''), it.get('license', ''),
            fills=it.get('fills'), eps=0.8, slug=it.get('slug'))

# order: by category (CATS order), keeping the order within each category (pictures first, icons last)
rank = {k: i for i, (k, _) in enumerate(CATS)}
entries.sort(key=lambda e: rank[e['cat']])

# names are unique within a category: icons that share a picture's name say so, and any other repeats are numbered
def _dupes(): return Counter((e['cat'], e['name']) for e in entries)
d = _dupes()
for e in entries:
    if d[(e['cat'], e['name'])] > 1 and e['source'] == 'tabler-icons': e['name'] += ' (icon)'
d = _dupes(); nth = Counter()
for e in entries:
    k = (e['cat'], e['name'])
    if d[k] > 1:
        nth[k] += 1
        if nth[k] > 1: e['name'] = f"{e['name']} {nth[k]}"
seen = Counter()
for e in entries:
    base = e['slug'][:48]; seen[(e['cat'], base)] += 1
    e['id'] = f"{e['cat']}/{base}" + (f"-{seen[(e['cat'], base)]}" if seen[(e['cat'], base)] > 1 else '')
    e['len'] = round(sum(plen(s) for s in e['S']) / 10)
    e['lines'] = len(e['S'])

# ---------------------------------------------------------------- app data
def short_author(e):
    a = e['author']; d = SOURCES[e['source']].get('author')
    return None if a == d else a
SRC_KEYS = list(SOURCES)
js_items = []
for e in entries:
    o = {'i': e['id'], 'c': e['cat'], 'n': e['name'], 's': SRC_KEYS.index(e['source']), 'w': e['w'], 'h': e['h'], 'l': e['lines'], 'm': e['len'], 'p': encode(e['S'])}
    a = short_author(e)
    if a: o['a'] = a
    if e['fills']: o['f'] = e['fills']
    js_items.append(json.dumps(o, ensure_ascii=False, separators=(',', ':')))
notices = {k: open(f'{V2}/licences/{k}.txt').read() for k in ('tabler', 'celestial', 'flagicons') if os.path.exists(f'{V2}/licences/{k}.txt')}
src_js = [{'k': k, 'name': v['name'], 'license': v['license'], 'url': v.get('url', ''), 'author': v.get('author', ''), 'note': v.get('note', ''),
           'notice': notices.get(v.get('notice', ''), '')} for k, v in SOURCES.items()]
js = ['/* ===================== DRAWING LIBRARY DATA (generated by library/v2/export2.py — do not edit) =====================',
      f'   {len(entries)} single-line drawings in {len(CATS)} categories. Points on a 0–1000 grid (longest side 1000), stored as',
      '   base-64 delta runs: per line its point count, then (dx, dy) zig-zag varints from the previous point. */',
      'const LIBRARY_CATS = ' + json.dumps([[k, n] for k, n in CATS], ensure_ascii=False) + ';',
      'const LIBRARY_SOURCES = ' + json.dumps(src_js, ensure_ascii=False, separators=(',', ':')) + ';',
      'const LIBRARY = [', ',\n'.join(js_items), '];', '']
open(os.path.join(APP, 'part40_library_data.js'), 'w').write('\n'.join(js))

# ---------------------------------------------------------------- folder
if os.path.exists(OUT): shutil.rmtree(OUT)
for k, _ in CATS: os.makedirs(os.path.join(OUT, k), exist_ok=True)
def svg_text(e):
    pad = 4; w, h = e['w'] + 2 * pad, e['h'] + 2 * pad
    src = SOURCES[e['source']]
    desc = f"Single-line drawing for pen plotters. {e['name']} — {src['name']} ({src['license']})" + (f", by {e['author']}" if e['author'] else '') + \
           (f"; original: {e['title']}" if e['title'] and e['title'] != e['name'] else '') + (f"; source file: {e['origin']}" if e['origin'] else '') + '.'
    body = []
    if e['fills']:
        used = set()
        for col, a, b in e['fills']:
            used.update(range(a, b))
            body.append(f'  <path d="{path_d(e["S"][a:b])}" fill="{col}" fill-rule="evenodd" stroke="#000" stroke-width="3.5" stroke-linejoin="round"/>')
        rest = [s for i, s in enumerate(e['S']) if i not in used]
        if rest: body.append(f'  <path d="{path_d(rest)}" fill="none" stroke="#000" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        body.append(f'  <path d="{path_d(e["S"])}" fill="none" stroke="#000" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{w / 10:g}mm" height="{h / 10:g}mm" viewBox="{-pad} {-pad} {w} {h}">\n'
            f'  <title>{html.escape(e["name"])}</title>\n  <desc>{html.escape(desc)}</desc>\n' + '\n'.join(body) + '\n</svg>\n')
for e in entries:
    e['file'] = e['id'] + '.svg'
    open(os.path.join(OUT, e['file']), 'w').write(svg_text(e))
json.dump([{'id': e['id'], 'category': CATNAME[e['cat']], 'name': e['name'], 'file': e['file'], 'source': SOURCES[e['source']]['name'], 'license': e['license'],
            'author': e['author'], 'title': e['title'], 'origin': e['origin'], 'lines': e['lines'], 'length_mm_at_100mm': e['len']} for e in entries],
          open(os.path.join(OUT, 'library.json'), 'w'), indent=1, ensure_ascii=False)
for k, t in notices.items(): open(os.path.join(OUT, f'LICENSE-{k}.txt'), 'w').write(t)

# ---------------------------------------------------------------- README and CREDITS
def md(s): return str(s).replace('|', '\\|')
cnt = Counter(e['cat'] for e in entries)
by_src = Counter(e['source'] for e in entries)
lens = sorted(e['len'] for e in entries)
def mlen(v): return f'{v / 1000:.1f} m'
R = ['# Plotter drawing library', '',
     f'{len(entries)} ready-to-draw line drawings in {len(CATS)} categories for the Dobot Magician (or any pen plotter). Every file is an SVG made of pen lines: '
     'no text and no hidden shapes. Flags also keep their colours as fills, so they look right on screen; the pen draws their outlines. '
     'Each drawing is 100 mm on its longest side with 0.35 mm lines, so it opens at a sensible size in any editor and is easy to resize.', '',
     '## Use them', '',
     '- **Magician Smart Controller:** Plotter tab → *Drawing library*. Choose a category or search (names, categories and artists), click a drawing, '
     'then size, turn and place it in the green zone as usual. The same drawings are built into the app.',
     '- **Any other tool:** open or drop a file from the folders below (Inkscape, vpype, AxiDraw, a laser cutter in line mode, and so on).', '',
     '## What is inside', '']
for k, n in CATS:
    names = [e['name'] for e in entries if e['cat'] == k]
    R.append(f'- **{n}** ({cnt[k]}, folder `{k}/`): ' + ', '.join(names[:10]) + (', …' if len(names) > 10 else ''))
R += ['', f'Half of the drawings need less than {mlen(lens[len(lens) // 2])} of pen line at 100 mm; most need between {mlen(lens[len(lens) // 10])} and {mlen(lens[len(lens) * 9 // 10])}. '
      'At the quiet drawing speed of 25 mm/s a metre of line takes about 40 seconds, plus the pen lifts; at 150 mm every line is 1.5 times longer.', '',
      '## Where they come from', '']
for k, v in SOURCES.items():
    if not by_src[k]: continue
    line = f"- **{v['name']}** ({by_src[k]} drawings) — {v['license']}."
    if v.get('url'): line += f" {v['url']}"
    if v.get('note'): line += ' ' + v['note']
    if v.get('notice'): line += f" Licence text: `LICENSE-{v['notice']}.txt`."
    R.append(line)
R += ['', 'Drawings made for this library are generated by program (shapes, curves, maps, figures, vehicles, skylines, sheet music of traditional and classical '
      'tunes, lettering). Brand names, logos and real people were left out.', '',
      '## Licence', '',
      'Openclipart drawings are in the public domain, and the pen-line versions here (mechanical conversions) are offered on the same terms. Drawings made for this '
      'library are public domain too. Tabler Icons and flag-icons drawings are under the MIT licence and d3-celestial star data under the BSD 3-Clause licence: '
      'keep the matching `LICENSE-*.txt` file with them when you share them. The Hershey fonts licence asks for this acknowledgement: '
      '*The Hershey Fonts were originally created by Dr. A. V. Hershey while working at the U. S. National Bureau of Standards.*', '',
      'Credits for every drawing are in [CREDITS.md](CREDITS.md); `library.json` lists every file with its category, source, licence, artist, original title and '
      'source file, its number of pen lines and its pen length in mm at 100 mm.', '']
open(os.path.join(OUT, 'README.md'), 'w').write('\n'.join(R))
C = ['# Credits', '', 'Thank you to everyone whose work is in this library. Drawings are listed by source; file paths are relative to this folder.', '']
for k, v in SOURCES.items():
    items = [e for e in entries if e['source'] == k]
    if not items: continue
    C += [f"## {v['name']} — {len(items)} drawings · {v['license']}", '']
    if v.get('note'): C += [v['note'], '']
    if v.get('url'): C += [v['url'], '']
    if k == 'generated':
        per = Counter(e['cat'] for e in items)
        C += ['By category: ' + ', '.join(f'{CATNAME[c]} {per[c]}' for c, _ in CATS if per[c]) + '.', '']
        continue
    C += ['| File | Name | Original title | Artist | Source file |', '|---|---|---|---|---|']
    for e in items:
        C.append(f"| `{e['file']}` | {md(e['name'])} | {md(e['title'])} | {md(e['author'])} | {('`' + md(e['origin']) + '`') if e['origin'] else ''} |")
    C.append('')
open(os.path.join(OUT, 'CREDITS.md'), 'w').write('\n'.join(C))
c = Counter(e['cat'] for e in entries)
print(len(entries), 'drawings; app data', os.path.getsize(os.path.join(APP, 'part40_library_data.js')), 'bytes')
for k, n in CATS: print(f'{c[k]:4d}  {n}' + ('   <-- fewer than 50' if c[k] < 50 else ''))
json.dump({'counts': {k: c[k] for k, _ in CATS}}, open(f'{V2}/export_counts.json', 'w'))
