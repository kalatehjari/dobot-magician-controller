"""Shared drawing tools for the generated library categories.

Coordinates: x right, y down (like SVG), any unit; every item is normalised later (longest side
1000 units = 100 mm). A drawing is a list of polylines [(x, y), ...].

Scene: shapes added back to front; render() removes the parts of outlines hidden behind filled
shapes in front (exact, with shapely), so overlapping parts look solid like a real drawing."""
import json, math, random, re, os
import numpy as np
from shapely.geometry import Polygon, LineString, MultiLineString, MultiPolygon, GeometryCollection, LinearRing, Point
from shapely.ops import unary_union, linemerge
from shapely import affinity

TAU = 2 * math.pi

# ---------------------------------------------------------------- primitives (lists of points)
def circle(cx, cy, r, n=None, a0=0.0):
    n = n or max(24, int(r * 2.2) + 16)
    return [(cx + r * math.cos(a0 + TAU * i / n), cy + r * math.sin(a0 + TAU * i / n)) for i in range(n + 1)]

def ellipse(cx, cy, rx, ry, rot=0.0, n=None):
    n = n or max(28, int((rx + ry) * 1.2) + 20)
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for i in range(n + 1):
        t = TAU * i / n; x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out

def arc(cx, cy, r, a0, a1, n=None, ry=None):
    ry = r if ry is None else ry
    n = n or max(6, int(abs(a1 - a0) * max(r, ry) / 3) + 4)
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

def rect(x, y, w, h, r=0.0):
    if r <= 0: return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    r = min(r, w / 2, h / 2); P = []
    for cx, cy, a in ((x + w - r, y + r, -math.pi / 2), (x + w - r, y + h - r, 0), (x + r, y + h - r, math.pi / 2), (x + r, y + r, math.pi)):
        P += arc(cx, cy, r, a, a + math.pi / 2, n=8)
    return P + [P[0]]

def poly(*pts, close=True):
    P = list(pts[0]) if len(pts) == 1 and isinstance(pts[0], (list, tuple)) and pts[0] and isinstance(pts[0][0], (list, tuple)) else list(pts)
    return P + [P[0]] if close and P[0] != P[-1] else P

def regular(cx, cy, r, n, rot=-math.pi / 2):
    return [(cx + r * math.cos(rot + TAU * i / n), cy + r * math.sin(rot + TAU * i / n)) for i in range(n + 1)]

def star(cx, cy, r1, r2, n=5, rot=-math.pi / 2):
    P = []
    for i in range(2 * n):
        r = r1 if i % 2 == 0 else r2; a = rot + math.pi * i / n
        P.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return P + [P[0]]

def bezier(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        out.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return out

def quad(p0, p1, p2, n=16):
    return [((1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]

def spline(pts, closed=False, n=10, tension=0.5):
    """Smooth Catmull-Rom curve through the points."""
    P = list(pts)
    if closed:
        if P[0] == P[-1]: P = P[:-1]
        ext = [P[-1]] + P + [P[0], P[1]]
    else:
        ext = [P[0]] + P + [P[-1]]
    out = []
    segs = len(P) if closed else len(P) - 1
    for i in range(segs):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            def c(a, b, cc, d):
                m1 = tension * (cc - a); m2 = tension * (d - b)
                return (2 * t3 - 3 * t2 + 1) * b + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * cc + (t3 - t2) * m2
            out.append((c(p0[0], p1[0], p2[0], p3[0]), c(p0[1], p1[1], p2[1], p3[1])))
    out.append(out[0] if closed else P[-1])
    return out

def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

# ---------------------------------------------------------------- transforms
def tx(P, dx=0.0, dy=0.0): return [(x + dx, y + dy) for x, y in P]
def sc(P, s, sy=None, ox=0.0, oy=0.0):
    sy = s if sy is None else sy
    return [(ox + (x - ox) * s, oy + (y - oy) * sy) for x, y in P]
def rot(P, a, ox=0.0, oy=0.0):
    c, s = math.cos(a), math.sin(a)
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in P]
def mirx(P, ox=0.0): return [(2 * ox - x, y) for x, y in P]
def miry(P, oy=0.0): return [(x, 2 * oy - y) for x, y in P]
def tx_all(L, dx=0.0, dy=0.0): return [tx(P, dx, dy) for P in L]
def sc_all(L, s, sy=None, ox=0.0, oy=0.0): return [sc(P, s, sy, ox, oy) for P in L]
def rot_all(L, a, ox=0.0, oy=0.0): return [rot(P, a, ox, oy) for P in L]
def mirx_all(L, ox=0.0): return [mirx(P, ox) for P in L]

# ---------------------------------------------------------------- shapely helpers
def to_poly(P):
    g = Polygon(P)
    if not g.is_valid: g = g.buffer(0)
    return g

def thick(P, w, cap='round', join='round'):
    """Outline of a thick line (a capsule for 2 points): a polygon."""
    caps = {'round': 1, 'flat': 2, 'square': 3}; joins = {'round': 1, 'mitre': 2, 'bevel': 3}
    return LineString(P).buffer(w / 2, cap_style=caps[cap], join_style=joins[join], quad_segs=8)

def lines_of(g):
    """Polylines from any shapely geometry (outlines for polygons)."""
    out = []
    if g is None or g.is_empty: return out
    t = g.geom_type
    if t == 'Polygon':
        out.append(list(g.exterior.coords)); out += [list(r.coords) for r in g.interiors]
    elif t in ('LineString', 'LinearRing'):
        out.append(list(g.coords))
    elif t in ('MultiPolygon', 'MultiLineString', 'GeometryCollection'):
        for h in g.geoms: out += lines_of(h)
    return [p for p in out if len(p) > 1]

def merge_lines(L):
    """Joins line pieces that meet end to end (after hidden-line removal)."""
    if not L: return []
    m = linemerge(MultiLineString([LineString(p) for p in L if len(p) > 1]))
    return lines_of(m)

class Scene:
    """Painter's model: add shapes back to front. Filled shapes hide what is behind them."""
    def __init__(self):
        self.items = []
    def shape(self, P, fill=True, outline=True, holes=()):
        g = P if hasattr(P, 'geom_type') else Polygon(P, [h for h in holes])
        if not g.is_valid: g = g.buffer(0)
        self.items.append(('shape', g, fill, outline)); return g
    def geom(self, g, fill=True, outline=True):
        if not g.is_valid: g = g.buffer(0)
        self.items.append(('shape', g, fill, outline)); return g
    def line(self, P):
        if len(P) > 1: self.items.append(('line', LineString(P), False, True))
    def lines(self, L):
        for P in L: self.line(P)
    def cut(self, P):
        """An invisible filled shape: hides what is behind (a white-out)."""
        g = P if hasattr(P, 'geom_type') else to_poly(P)
        self.items.append(('shape', g, True, False))
    def render(self):
        out, cover = [], None
        for kind, g, fill, outline in reversed(self.items):
            if outline:
                vis = g.boundary if kind == 'shape' else g
                if cover is not None and not vis.is_empty: vis = vis.difference(cover)
                out += lines_of(vis)
            if fill and kind == 'shape':
                cover = g if cover is None else cover.union(g)
        return merge_lines(out)

# ---------------------------------------------------------------- Hershey single-line text
_HF = None
def _fonts():
    global _HF
    if _HF is None:
        _HF = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'hersheytext.json')))
    return _HF

def _glyph(font, ch):
    chars = _fonts()[font]['chars']
    i = ord(ch) - 33
    if ch == ' ' or i < 0 or i >= len(chars): return [], 8 if font != 'astrology' else 10
    c = chars[i]; segs, cur = [], []
    for tok in re.findall(r'[ML]|-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?', c['d']):
        if tok == 'M':
            if len(cur) > 1: segs.append(cur)
            cur = []
        elif tok == 'L': pass
        else:
            x, y = map(float, tok.split(',')); cur.append((x, y))
    if len(cur) > 1: segs.append(cur)
    return segs, c['o'] * 2

# Latin-1 single-line fonts (the same ones the app's text tool uses), with accents composed when missing
# the svg_fonts folder of the hersheytext npm package (MIT); set HERSHEY_SVG_FONTS to its path
SVG_FONT_DIR = os.environ.get('HERSHEY_SVG_FONTS', 'node_modules/hersheytext/svg_fonts')
_SF = {}
def _svgfont(name):
    if name in _SF: return _SF[name]
    import statistics, sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fonts'))
    from fontlib import read_svg_font
    F = read_svg_font(f'{SVG_FONT_DIR}/{name}.svg')
    def ext(chars):
        t, b = [], []
        for ch in chars:
            g = F['glyphs'].get(ch)
            if not g or not g[1]: continue
            ys = [p[1] for st in g[1] for p in st]; t.append(max(ys)); b.append(min(ys))
        return b, t
    cb, ct = ext('BDEFHIKLMNPRTUVWXZ'); lb, lt = ext('xzvwmnruaceos')
    base = statistics.median(cb + lb); cap = statistics.median(ct) - base
    G = {ch: (adv / cap, [[(x / cap, (base - y) / cap) for x, y in st] for st in strokes]) for ch, (adv, strokes) in F['glyphs'].items()}
    _SF[name] = G
    return G

def _compose(G, ch):
    import unicodedata
    if ch in G: return G[ch]
    d = unicodedata.normalize('NFD', ch)
    if len(d) > 1 and d[0] in G:
        adv, st = G[d[0]]; st = list(st)
        xs = [p[0] for s in st for p in s] or [0, adv]; ys = [p[1] for s in st for p in s] or [-0.7]
        cx, top = (min(xs) + max(xs)) / 2, min(min(ys), -1 if d[0].isupper() else -0.68)
        for m in d[1:]:
            o = ord(m); y1 = top - 0.12
            if o == 0x308: st += [circle(cx - 0.11, y1 - 0.05, 0.035, n=8), circle(cx + 0.11, y1 - 0.05, 0.035, n=8)]
            elif o == 0x301: st.append([(cx - 0.06, y1), (cx + 0.09, y1 - 0.13)])
            elif o == 0x300: st.append([(cx + 0.06, y1), (cx - 0.09, y1 - 0.13)])
            elif o == 0x304: st.append([(cx - 0.16, y1 - 0.06), (cx + 0.16, y1 - 0.06)])
            elif o == 0x302: st.append([(cx - 0.14, y1), (cx, y1 - 0.13), (cx + 0.14, y1)])
            elif o == 0x30A: st.append(circle(cx, y1 - 0.08, 0.07, n=12))
        return adv, st
    return G.get('?', (0.5, []))

def text(s, x=0.0, y=0.0, size=10.0, font='HersheySans1', align='center', spacing=0.0):
    """Text as pen lines; size = cap height; (x, y) = baseline anchor. Fonts: the app's SVG font
    names (HersheySans1, HersheySerifMed, EMSReadability…) or the old Hershey JSON names (futural…)."""
    if font in ('futural', 'futuram', 'timesr', 'timesrb', 'timesi', 'scripts', 'scriptc', 'gothiceng', 'gothicger', 'gothicita', 'astrology', 'music', 'cursive', 'markers', 'symbolic'):
        glyphs, width = [], 0.0
        for ch in s:
            segs, w = _glyph(font, ch)
            glyphs.append((segs, width)); width += w + spacing * 21 / max(size, 1e-9)
        k = size / 21.0
        x0 = x - (width * k / 2 if align == 'center' else width * k if align == 'right' else 0)
        return [[(x0 + (px + off) * k, y + (py - 22) * k) for px, py in P] for segs, off in glyphs for P in segs]
    G = _svgfont(font)
    glyphs, width = [], 0.0
    for ch in s:
        if ch == ' ': glyphs.append(([], width)); width += G.get(' ', (0.3, []))[0] + spacing / size; continue
        adv, st = _compose(G, ch)
        glyphs.append((st, width)); width += adv + spacing / size
    x0 = x - (width * size / 2 if align == 'center' else width * size if align == 'right' else 0)
    return [[(x0 + (px + off) * size, y + py * size) for px, py in P] for st, off in glyphs for P in st]

def text_width(s, size=10.0, font='HersheySans1', spacing=0.0):
    L = text(s, 0, 0, size, font, 'left', spacing)
    if not L: return 0.0
    xs = [p[0] for P in L for p in P]
    return max(xs) - min(xs)

def glyph_lines(font, ch, cx=0.0, cy=0.0, size=100.0):
    """One glyph centred at (cx, cy), longest side `size`."""
    segs, _ = _glyph(font, ch)
    xs = [p[0] for s in segs for p in s]; ys = [p[1] for s in segs for p in s]
    if not xs: return []
    w, h = max(xs) - min(xs), max(ys) - min(ys); k = size / max(w, h, 1e-9)
    mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return [[(cx + (px - mx) * k, cy + (py - my) * k) for px, py in s] for s in segs]

# ---------------------------------------------------------------- items
class Item:
    def __init__(self, cat, name, lines, author='Made for this library', title='', source='generated', fills=None, license='public domain'):
        self.cat, self.name, self.lines, self.author, self.title, self.source, self.fills, self.license = cat, name, lines, author, title or name, source, fills, license

def bbox(L):
    xs = [p[0] for P in L for p in P]; ys = [p[1] for P in L for p in P]
    return min(xs), min(ys), max(xs), max(ys)

def rng(seed): return random.Random(seed)

# ---------------------------------------------------------------- saving and contact sheets
def item_dict(it):
    L = [P for P in it.lines if len(P) > 1]
    d = {'cat': it.cat, 'name': it.name, 'author': it.author, 'title': it.title, 'source': it.source, 'license': it.license,
         'strokes': [[[round(x, 2), round(y, 2)] for x, y in P] for P in L]}
    if it.fills: d['fills'] = it.fills
    if getattr(it, 'slug', None): d['slug'] = it.slug
    if getattr(it, 'tags', None): d['tags'] = it.tags
    return d

def save(items, path):
    json.dump([item_dict(i) for i in items], open(path, 'w'))
    print('saved', len(items), 'items to', path)

def sheet(items, path, cols=8, cell=2.2, title=None):
    """Contact sheet: every item in a grid, numbered, as the pen would draw it."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    n = len(items); rows = max(1, (n + cols - 1) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * cell, rows * cell * 1.08))
    axes = np.array(axes).reshape(-1)
    for ax in axes: ax.axis('off')
    for i, it in enumerate(items):
        ax = axes[i]
        L = it['strokes'] if isinstance(it, dict) else it.lines
        name = it['name'] if isinstance(it, dict) else it.name
        for P in L:
            if len(P) > 1:
                xs = [p[0] for p in P]; ys = [p[1] for p in P]
                ax.plot(xs, ys, '-', color='k', lw=0.55)
        ax.set_aspect('equal'); ax.invert_yaxis()
        npts = sum(len(P) for P in L)
        ax.set_title(f'{i}: {name[:26]}\n{len(L)} lines {npts} pts', fontsize=7)
    if title: fig.suptitle(title, fontsize=11)
    plt.tight_layout(); plt.savefig(path, dpi=72); plt.close(fig)
    print('sheet', path)

# ---------------------------------------------------------------- text along a circle
def text_arc(s, cx, cy, r, mid_deg=0.0, size=40.0, font='HersheySans1', spacing=0.0, bottom=False):
    """Letters along a circle (baseline radius r). Top text reads clockwise with letters standing
    outwards; bottom=True reads left to right along the bottom with letters standing inwards."""
    L = text(s, 0, 0, size, font, 'left', spacing)
    if not L: return []
    xs = [p[0] for P in L for p in P]; w = max(xs) + min(0, min(xs))
    span = w / r; th0 = math.radians(mid_deg)
    out = []
    for P in L:
        Q = []
        for px, py in P:
            if not bottom:
                th = th0 - span / 2 + px / r; rho = r - py
            else:
                th = th0 + math.pi + span / 2 - px / r; rho = r + py
            Q.append((cx + rho * math.sin(th), cy - rho * math.cos(th)))
        out.append(Q)
    return out

# ---------------------------------------------------------------- SVG files (icons) to polylines
def svg_lines(src, step=None, skip_unstroked=True):
    """Polylines from an SVG file or text (svgelements): every visible shape's outline, transforms applied.
    step: curve sampling distance in SVG units (default: 1/200 of the picture's size)."""
    import svgelements as se, io
    doc = se.SVG.parse(io.StringIO(src) if src.lstrip().startswith('<') else src, reify=True)
    shapes = [e for e in doc.elements() if isinstance(e, se.Shape)]
    out = []
    bb = doc.bbox()
    size = max(bb[2] - bb[0], bb[3] - bb[1]) if bb else 24
    st = step or size / 200
    for e in shapes:
        stroke = e.stroke if e.stroke is not None else None
        fill = e.fill if e.fill is not None else None
        has_stroke = stroke is not None and stroke.value is not None and stroke.alpha != 0 and str(stroke) != 'none'
        has_fill = fill is not None and fill.value is not None and fill.alpha != 0 and str(fill) != 'none'
        if skip_unstroked and not has_stroke and not has_fill: continue
        p = se.Path(e) if not isinstance(e, se.Path) else e
        cur = []
        for seg in p.segments():
            if isinstance(seg, se.Move):
                if len(cur) > 1: out.append(cur)
                cur = [(seg.end.x, seg.end.y)]
            elif isinstance(seg, se.Close):
                if cur and seg.end is not None: cur.append((seg.end.x, seg.end.y))
                if len(cur) > 1: out.append(cur)
                cur = [cur[-1]] if cur else []
            elif isinstance(seg, se.Line):
                if not cur: cur = [(seg.start.x, seg.start.y)]
                cur.append((seg.end.x, seg.end.y))
            else:
                L = seg.length(error=1e-3) if hasattr(seg, 'length') else 1
                n = max(2, int(math.ceil(L / st)))
                if not cur: cur = [(seg.start.x, seg.start.y)]
                for k in range(1, n + 1):
                    q = seg.point(k / n); cur.append((q.x, q.y))
        if len(cur) > 1: out.append(cur)
    return [[(float(x), float(y)) for x, y in P] for P in out if len(P) > 1]

def smooth(P, iters=3, corner_deg=55, closed=None):
    """Chaikin corner cutting that keeps real corners (turns sharper than corner_deg) sharp."""
    if len(P) < 3: return list(P)
    if closed is None: closed = math.hypot(P[0][0] - P[-1][0], P[0][1] - P[-1][1]) < 1e-6
    pts = list(P[:-1]) if closed else list(P)
    for _ in range(iters):
        n = len(pts)
        def sharp(i):
            if not closed and (i == 0 or i == n - 1): return True
            a, b, c = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
            v1 = (b[0] - a[0], b[1] - a[1]); v2 = (c[0] - b[0], c[1] - b[1])
            l1, l2 = math.hypot(*v1), math.hypot(*v2)
            if l1 < 1e-9 or l2 < 1e-9: return False
            cosang = max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))
            return math.degrees(math.acos(cosang)) > corner_deg
        out = []
        for i in range(n if closed else n - 1):
            a, b = pts[i], pts[(i + 1) % n]
            if sharp(i): out.append(a)
            q = (0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]); r = (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])
            out += [q, r]
        if not closed: out.append(pts[-1])
        pts = out
    if closed: pts.append(pts[0])
    return pts

# ---------------------------------------------------------------- size after export (what the app will store)
def _rdp(pts, eps):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts) - 1)]
    while stack:
        i0, i1 = stack.pop(); a, b = pts[i0], pts[i1]; dx, dy = b[0] - a[0], b[1] - a[1]; Ln = math.hypot(dx, dy)
        best, bi = -1, 0
        for i in range(i0 + 1, i1):
            p = pts[i]
            d = abs(dy * (p[0] - a[0]) - dx * (p[1] - a[1])) / Ln if Ln else math.hypot(p[0] - a[0], p[1] - a[1])
            if d > best: best, bi = d, i
        if best > eps: keep[bi] = True; stack += [(i0, bi), (bi, i1)]
    return [p for p, k in zip(pts, keep) if k]

def export_size(lines, eps=0.8):
    """(points, lines) the drawing will have in the app: longest side scaled to 1000 units, simplified
    (Douglas-Peucker, 0.8 units) and rounded to whole units, as the library exporter does."""
    S = [P for P in lines if len(P) > 1]
    if not S: return 0, 0
    xs = [p[0] for P in S for p in P]; ys = [p[1] for P in S for p in P]
    x0, y0 = min(xs), min(ys); k = 1000 / max(max(xs) - x0, max(ys) - y0, 1e-9)
    n = m = 0
    for P in S:
        Q = _rdp([((x - x0) * k, (y - y0) * k) for x, y in P], eps)
        Q = [(round(x), round(y)) for x, y in Q]
        Q = [p for i, p in enumerate(Q) if i == 0 or p != Q[i - 1]]
        if len(Q) > 1: n += len(Q); m += 1
    return n, m
