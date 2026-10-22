"""Skyline kit: groups of shapes in local y-up coordinates, placing landmarks into a city panorama,
generic filler buildings in depth layers, hills, trees, boats, water and the city name.

Local coordinates are y-up (height positive), x centred on the landmark, base at y = 0, roughly in
metres. A City works in world units: x 0…1000, ground at y = 0, y up; it flips to y-down at the end."""
import math, random, sys, os
import numpy as np
from shapely.geometry import Polygon, LineString, MultiLineString, Point
from shapely.ops import unary_union, linemerge
from shapely import affinity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Scene, text, text_width, export_size, lines_of, merge_lines, bezier, quad, spline, smooth

PI = math.pi
FONT = 'EMSReadability'

# ---------------------------------------------------------------- point-list helpers (y-up)
def R(x0, y0, x1, y1):
    """Closed rectangle."""
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]

def B(cx, w, y0, y1):
    """Closed box of width w centred on cx, from y0 up to y1."""
    return R(cx - w / 2, y0, cx + w / 2, y1)

def closed(P):
    P = list(P)
    return P if P[0] == P[-1] else P + [P[0]]

def sym(right, cx=0.0):
    """Closed symmetric outline from its right half, given from the bottom up (x measured from cx)."""
    right = [(cx + x, y) for x, y in right]
    left = [(2 * cx - x, y) for x, y in reversed(right)]
    if abs(right[-1][0] - cx) < 1e-9: left = left[1:]
    return closed(right + left)

def mirror(P, cx=0.0):
    return [(2 * cx - x, y) for x, y in P]

def earc(cx, cy, rx, ry, a0, a1, n=None):
    """Elliptical arc from angle a0 to a1 (radians, 0 = right, counter-clockwise, y up)."""
    n = n or max(6, int(abs(a1 - a0) * max(rx, ry) / 2.5) + 4)
    n = min(n, 72)
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

def dome(cx, y0, rx, ry, n=None):
    """Closed half-ellipse dome standing on y0."""
    return closed(earc(cx, y0, rx, ry, 0, PI, n))

def circ(cx, cy, r, n=None):
    return closed(earc(cx, cy, r, r, 0, 2 * PI, n or max(16, min(64, int(r * 1.2) + 12))))

def bez(p0, p1, p2, p3, n=16):
    return bezier(p0, p1, p2, p3, n)

def onion(cx, y0, w, h, bulge=1.75, neck=0.55, n=18):
    """Onion dome outline standing on y0 (closed): base width w, bulging out, pointed tip at y0 + h."""
    r = w / 2
    right = bez((r, y0), (bulge * r, y0 + neck * h), (0.0, y0 + 0.52 * h), (0, y0 + h), n)
    return sym(right, cx)

def pdome(cx, y0, w, h, bulge=1.25, n=16):
    """Pointed (Persian / ogival) dome standing on y0."""
    r = w / 2
    right = bez((r, y0), (bulge * r, y0 + 0.55 * h), (0.32 * r, y0 + 0.82 * h), (0, y0 + h), n)
    return sym(right, cx)

def arch(cx, y0, w, hs, kind='round', n=10, closed_=False):
    """Arch opening outline: up the left jamb to the springing (y0 + hs), over the top, down the right
    jamb. kind: round, pointed (gothic), flat, ogee, horseshoe."""
    r = w / 2; ys = y0 + hs
    if kind == 'round':
        top = earc(cx, ys, r, r, PI, 0, n)
    elif kind == 'pointed' or kind == 'gothic':
        k = 0.85; Rr = k * w; off = Rr - r
        at = math.acos(-off / Rr) if Rr > off else PI / 2
        left = [(cx + off + Rr * math.cos(a), ys + Rr * math.sin(a)) for a in np.linspace(PI, at, n)]
        top = left + [(2 * cx - x, y) for x, y in reversed(left[:-1])]
    elif kind == 'persian':
        k = 0.66; Rr = k * w; off = Rr - r
        at = math.acos(-off / Rr)
        left = [(cx + off + Rr * math.cos(a), ys + Rr * math.sin(a)) for a in np.linspace(PI, at, n)]
        top = left + [(2 * cx - x, y) for x, y in reversed(left[:-1])]
    elif kind == 'ogee':
        hh = r * 1.3
        left = bez((cx - r, ys), (cx - r, ys + hh * 0.55), (cx, ys + hh * 0.55), (cx, ys + hh), n)
        top = left + [(2 * cx - x, y) for x, y in reversed(left[:-1])]
    elif kind == 'horseshoe':
        top = earc(cx, ys, r * 1.08, r * 1.08, PI + 0.35, -0.35, n)
        top = [(cx - r, ys)] + top + [(cx + r, ys)]
    else:
        top = [(cx - r, ys), (cx + r, ys)]
    P = [(cx - r, y0)] + top + [(cx + r, y0)]
    return closed(P) if closed_ else P

def pts_arc_through(p0, p1, sag, n=16):
    """A parabolic curve from p0 to p1 hanging down by `sag` at the middle (negative sag bulges up)."""
    out = []
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t; y = p0[1] + (p1[1] - p0[1]) * t - 4 * sag * t * (1 - t)
        out.append((x, y))
    return out

def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

# ---------------------------------------------------------------- groups
def _poly(P, holes=()):
    g = Polygon(P, [list(h) for h in holes])
    if not g.is_valid: g = g.buffer(0)
    return g

class G:
    """Drawing operations in back-to-front order: filled shapes (hide what is behind them), plain
    lines and invisible cuts. `holes` remembers see-through openings, so fillers are kept out of them."""
    def __init__(self):
        self.ops = []; self.holes = []
    def S(self, P, holes=(), fill=True, outline=True):
        g = P if hasattr(P, 'geom_type') else _poly(P, holes)
        if not g.is_empty:
            self.ops.append(('S', g, fill, outline))
            for h in holes: self.holes.append(_poly(h))
        return g
    def L(self, P):
        P = [p for i, p in enumerate(P) if i == 0 or p != P[i - 1]]
        if len(P) > 1: self.ops.append(('L', LineString(P), False, True))
        return self
    def LL(self, Ls):
        for P in Ls: self.L(P)
        return self
    def cut(self, P):
        g = P if hasattr(P, 'geom_type') else _poly(P)
        self.ops.append(('S', g, True, False)); return self
    def hole(self, P):
        """Remember an opening (sky shows through) without drawing anything."""
        self.holes.append(_poly(P)); return self
    def add(self, *others):
        for o in others:
            self.ops += o.ops; self.holes += o.holes
        return self
    def T(self, m):
        out = G()
        out.ops = [(k, affinity.affine_transform(g, m), f, o) for k, g, f, o in self.ops]
        out.holes = [affinity.affine_transform(h, m) for h in self.holes]
        return out
    def at(self, x=0.0, y=0.0, s=1.0, sy=None):
        return self.T([s, 0, 0, s if sy is None else sy, x, y])
    def rot(self, deg, ox=0.0, oy=0.0):
        a = math.radians(deg); c, s = math.cos(a), math.sin(a)
        return self.T([c, -s, s, c, ox - c * ox + s * oy, oy - s * ox - c * oy])
    def mirror(self, ox=0.0):
        return self.T([-1, 0, 0, 1, 2 * ox, 0])
    def bounds(self):
        gs = [g for k, g, f, o in self.ops if k == 'S' and (f or o)] or [g for k, g, f, o in self.ops]
        if not gs: return (0, 0, 0, 0)
        b = np.array([g.bounds for g in gs])
        return b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()

def grp(*parts):
    g = G()
    for p in parts: g.add(p)
    return g

# ---------------------------------------------------------------- generic elements (local y-up)
def window_rows(x0, x1, ys, step=12, ln=7, kind='v', skip=0.0, rng=None):
    """Short dashes for windows: kind 'v' vertical dashes (tall windows), 'h' horizontal dashes,
    'b' small boxes. ys: the baseline heights of the rows."""
    out = []
    n = int((x1 - x0) // step)
    if n < 1: return out
    off = x0 + ((x1 - x0) - (n - 1) * step) / 2
    for y in ys:
        for i in range(n):
            if rng and rng.random() < skip: continue
            x = off + i * step
            if kind == 'v': out.append([(x, y), (x, y + ln)])
            elif kind == 'h': out.append([(x - ln / 2, y), (x + ln / 2, y)])
            else: out.append(R(x - 2.6, y, x + 2.6, y + ln))
    return out

def spire_line(x, y0, h):
    return [(x, y0), (x, y0 + h)]

def finial(cx, y, h, ball=0.0):
    """A short spike with an optional ball (local units)."""
    g = G()
    if ball:
        g.S(circ(cx, y + ball, ball, 12))
        g.L([(cx, y + 2 * ball), (cx, y + 2 * ball + h)])
    else:
        g.L([(cx, y), (cx, y + h)])
    return g

def lattice(x0l, x0r, x1l, x1r, y0, y1, n):
    """X-bracing between two sloping edges, n panels from y0 to y1 (returns lines)."""
    out = []
    for i in range(n):
        ta, tb = i / n, (i + 1) / n
        ya, yb = y0 + (y1 - y0) * ta, y0 + (y1 - y0) * tb
        la, ra = x0l + (x1l - x0l) * ta, x0r + (x1r - x0r) * ta
        lb, rb = x0l + (x1l - x0l) * tb, x0r + (x1r - x0r) * tb
        out.append([(la, ya), (rb, yb)]); out.append([(ra, ya), (lb, yb)])
    return out

# ---------------------------------------------------------------- nature: hills, trees
def ridge(x0, x1, ctrl, rough=0.0, seed=1, base=-30, step=6.0, n_oct=4):
    """Mountain outline through control points [(x, h)] (spline) with optional fractal roughness;
    closed down to `base` (below the ground, hidden later)."""
    rng = random.Random(seed)
    xs = np.arange(x0, x1 + step, step)
    cx = [c[0] for c in ctrl]; ch = [c[1] for c in ctrl]
    sp = spline(ctrl, n=24)
    sx = np.array([p[0] for p in sp]); sh = np.array([p[1] for p in sp])
    order = np.argsort(sx)
    hs = np.interp(xs, sx[order], sh[order])
    if rough:
        noise = np.zeros_like(xs, dtype=float)
        for o in range(n_oct):
            k = 2 ** o; ph = rng.uniform(0, 100); ph2 = rng.uniform(0, 100)
            noise += (np.sin(xs / (90.0 / k) + ph) * 0.6 + np.sin(xs / (53.0 / k) + ph2) * 0.4) / k
        hs = hs + rough * noise * np.clip(hs / max(1, hs.max()), 0.2, 1)
    P = [(float(x), float(h)) for x, h in zip(xs, hs)]
    return closed([(x0, base)] + P + [(x1, base)])

def snowcap(P, line_h, seed=3, amp=8, period=18):
    """A jagged snow line across a mountain outline P (closed polygon) at height line_h: the part of
    a zigzag that lies inside the mountain."""
    rng = random.Random(seed)
    poly = _poly(P)
    x0, y0, x1, y1 = poly.bounds
    xs = np.arange(x0, x1, period / 2)
    Z = [(float(x), line_h + (amp if i % 2 else -amp * 0.4) + rng.uniform(-amp * 0.3, amp * 0.3)) for i, x in enumerate(xs)]
    g = LineString(Z).intersection(poly.buffer(-3))
    return [l for l in lines_of(g) if LineString(l).length > 14]

def tree_round(x, h=34, w=None, seed=0):
    rng = random.Random(seed); w = w or h * 0.7
    g = G()
    pts = []
    n = 9
    for i in range(n + 1):
        a = PI * 1.12 * i / n - 0.06 * PI
        r = 1 + rng.uniform(-0.08, 0.08)
        pts.append((x + w / 2 * r * math.cos(PI - a), h * 0.62 + h * 0.4 * r * math.sin(PI - a)))
    crown = spline(pts, n=5)
    crown = crown + [(x + w * 0.18, h * 0.3), (x - w * 0.18, h * 0.3)]
    g.S(closed(crown))
    g.L([(x, 0), (x, h * 0.3)])
    return g

def cypress(x, h=60, w=None):
    w = w or h * 0.2
    g = G()
    right = bez((w * 0.25, 0), (w * 0.95, h * 0.25), (w * 0.55, h * 0.75), (0, h), 14)
    g.S(sym([(0.0, 0.0)] + right[1:] if False else right, x))
    return g

def umbrella_pine(x, h=70, w=None, seed=0, lean=0.0):
    """Stone pine: a tall, slightly bent trunk and a flat, cloud-shaped crown."""
    rng = random.Random(seed); w = w or h * 1.15
    g = G()
    top = (x + lean * h, h * 0.78)
    crown = []
    n = 7
    for i in range(n + 1):        # bumpy top edge, left to right
        t = i / n; cx = top[0] - w / 2 + w * t
        crown.append((cx, h * (0.9 + 0.1 * math.sin(PI * t)) + rng.uniform(-2, 2)))
    under = [(top[0] + w / 2, h * 0.76), (top[0] + w * 0.25, h * 0.70), (top[0] - w * 0.25, h * 0.71), (top[0] - w / 2, h * 0.77)]
    P = spline([(top[0] - w / 2, h * 0.79)] + crown + [(top[0] + w / 2, h * 0.79)], n=5) + under
    g.S(closed(P))
    trunk = bez((x, 0), (x + lean * h * 0.2, h * 0.3), (top[0] - lean * h * 0.3, h * 0.55), (top[0], h * 0.72), 10)
    g.L(trunk)
    return g

def palm(x, h=60, lean=0.08, seed=0, fronds=7):
    """Palm tree: a curved trunk and arching fronds (single lines)."""
    rng = random.Random(seed)
    g = G()
    top = (x + lean * h, h)
    trunk = bez((x, 0), (x, h * 0.4), (x + lean * h * 0.6, h * 0.7), top, 12)
    g.L(trunk)
    for i in range(fronds):
        a = PI * (0.08 + 0.84 * i / (fronds - 1)) + rng.uniform(-0.08, 0.08)
        L = h * rng.uniform(0.36, 0.48)
        dx, dy = math.cos(a), math.sin(a)
        end = (top[0] + dx * L, top[1] + dy * L * 0.35 - L * 0.42)
        mid = (top[0] + dx * L * 0.55, top[1] + dy * L * 0.35 + L * 0.1)
        g.L(quad(top, mid, end, 8))
    return g

def bush_row(x0, x1, h=12, seed=0):
    rng = random.Random(seed); pts = [(x0, 0)]
    x = x0
    while x < x1:
        w = rng.uniform(10, 18); pts += earc(x + w / 2, 0, w / 2, h * rng.uniform(0.7, 1.1), PI, 0, 6)[1:]; x += w
    pts.append((pts[-1][0], 0))
    g = G(); g.S(closed(pts)); return g

# ---------------------------------------------------------------- boats (world units, on the waterline y = 0)
def sailboat(x, s=1.0, flip=False):
    g = G()
    hull = [(-22, 4), (24, 4), (16, -4), (-16, -4)]
    g.S(closed(hull))
    g.S(closed([(0, 6), (0, 52), (20, 8)]))
    g.S(closed([(-3, 8), (-3, 44), (-18, 8)]))
    g = g.at(0, 0, s)
    if flip: g = g.mirror()
    return g.at(x, 0)

def ferry(x, s=1.0, flip=False):
    g = G()
    g.S(closed([(-34, 6), (34, 6), (28, -4), (-30, -4)]))
    g.S(R(-22, 6, 20, 15)); g.S(R(-14, 15, 10, 23))
    g.S(R(-4, 23, 3, 32))
    g = g.at(0, 0, s)
    if flip: g = g.mirror()
    return g.at(x, 0)

def junk(x, s=1.0, flip=False):
    """Chinese junk: high stern, battened fan-shaped sails."""
    g = G()
    hull = bez((-34, 12), (-20, -6), (20, -6), (30, 6), 10) + [(36, 10), (28, 9), (-26, 6), (-36, 16)]
    g.S(closed(hull))
    for mx, h, w in ((-8, 62, 30), (16, 48, 24)):
        sail = [(mx - w * 0.15, 9), (mx - w * 0.2, h), (mx + w * 0.75, h * 0.86), (mx + w * 0.85, 9)]
        g.S(closed(sail))
        for k in range(1, 4):
            t = k / 4; y = 9 + (h - 9) * t
            g.L([(mx - w * 0.15 - w * 0.05 * t, y), (mx + w * 0.85 - w * 0.1 * t, 9 + (h * 0.86 - 9) * t)])
        g.L([(mx, 9), (mx, h + 6)])
    g = g.at(0, 0, s)
    if flip: g = g.mirror()
    return g.at(x, 0)

def dhow(x, s=1.0, flip=False, sail=True):
    """Dhow / felucca: a curved hull and a big triangular lateen sail on a slanted yard."""
    g = G()
    hull = [(-36, 10), (-26, -2), (20, -2), (34, 12), (24, 6), (-26, 6)]
    g.S(closed(hull))
    if sail:
        g.S(closed([(-24, 10), (32, 70), (8, 10)]))
        g.L([(0, 6), (2, 46)])
    g = g.at(0, 0, s)
    if flip: g = g.mirror()
    return g.at(x, 0)

def rowboat(x, s=1.0):
    g = G(); g.S(closed([(-14, 4), (14, 4), (9, -2), (-9, -2)])); return g.at(x, 0, s)

def gondola(x, s=1.0, flip=False):
    """Venetian gondola: long, low, curving up at both ends; the toothed iron prow piece."""
    g = G()
    top = bez((-46, 14), (-30, 3), (30, 3), (44, 18), 16)
    bot = bez((46, 18), (34, -3), (-34, -3), (-48, 13), 16)
    g.S(closed(top + bot))
    # the ferro: a vertical blade with teeth facing forward
    g.L([(44, 18), (47, 29), (44, 32)])
    for k in range(3): g.L([(45.5, 19.5 + 3 * k), (50, 19.5 + 3 * k)])
    g = g.at(0, 0, s)
    if flip: g = g.mirror()
    return g.at(x, 0)

def longtail(x, s=1.0, flip=False):
    g = G()
    g.S(closed(bez((-40, 10), (-26, -4), (20, -4), (38, 6), 12) + [(42, 12), (-36, 7)]))
    g.S(closed([(-16, 7), (-14, 15), (16, 15), (18, 7)]))
    g = g.at(0, 0, s)
    if flip: g = g.mirror()
    return g.at(x, 0)

def tall_ship(x, s=1.0, flip=False):
    """A small two-masted wooden ship (for old harbours)."""
    g = G()
    g.S(closed([(-40, 10), (40, 12), (30, -4), (-32, -4)]))
    for mx, h in ((-14, 58), (16, 66)):
        g.L([(mx, 10), (mx, h)])
        g.L([(mx - 12, h - 10), (mx + 12, h - 10)]); g.L([(mx - 15, h - 28), (mx + 15, h - 28)])
    g.L([(40, 12), (56, 26)])
    g = g.at(0, 0, s)
    if flip: g = g.mirror()
    return g.at(x, 0)

# ---------------------------------------------------------------- filler buildings (world, y-up)
def bldg(rng, x0, x1, h, style, win=0.3, roof=True):
    """One filler building over [x0, x1], height h, in a style. Returns a G in world units."""
    g = G(); w = x1 - x0; cx = (x0 + x1) / 2
    lines = []
    r = rng.random()
    if style in ('modern', 'tower', 'glass'):
        top = h
        if r < 0.22 and w > 26 and h > 70:                         # setback crown
            k = rng.uniform(0.55, 0.75); hs = rng.uniform(0.1, 0.18) * h
            P = [(x0, 0), (x1, 0), (x1, h - hs), (cx + w * k / 2, h - hs), (cx + w * k / 2, h), (cx - w * k / 2, h), (cx - w * k / 2, h - hs), (x0, h - hs)]
            g.S(closed(P))
        elif r < 0.34 and w > 18:                                   # slanted top
            d = rng.uniform(0.25, 0.6) * w
            P = [(x0, 0), (x1, 0), (x1, h - d), (x0, h)] if rng.random() < 0.5 else [(x0, 0), (x1, 0), (x1, h), (x0, h - d)]
            g.S(closed(P))
        elif r < 0.42 and w > 20 and h > 60:                        # pyramid cap
            ph = rng.uniform(0.3, 0.6) * w
            g.S(closed([(x0, 0), (x1, 0), (x1, h), (cx, h + ph), (x0, h)]))
            top = h + ph
        elif r < 0.5 and w > 22 and h > 70:                         # rounded top
            g.S(closed([(x0, 0), (x1, 0)] + earc(cx, h, w / 2, w * 0.35, 0, PI, 10) + [(x0, h)]))
        else:
            g.S(R(x0, 0, x1, h))
            if r > 0.86 and h > 50: g.L([(cx + rng.uniform(-0.2, 0.2) * w, h), (cx, h + rng.uniform(16, 34))])
            elif r > 0.78 and w > 22:                                 # small rooftop box
                bw = rng.uniform(0.3, 0.5) * w; bx = rng.uniform(x0 + 4, x1 - 4 - bw)
                g.S(R(bx, h - 1, bx + bw, h + rng.uniform(8, 12)))
        if rng.random() < win and w >= 22 and h > 40:
            k = rng.random()
            if k < 0.45:                                              # rows of short dashes
                ys = [h - 18 - 15 * i for i in range(rng.randint(2, 4)) if h - 18 - 15 * i > 10]
                lines += window_rows(x0 + 4, x1 - 4, ys, step=11, ln=6, kind='v')
            elif k < 0.75 and w >= 26:                                # a few vertical mullions
                n = 2 if w < 40 else 3
                for i in range(1, n + 1):
                    xx = x0 + w * i / (n + 1)
                    lines.append([(xx, 8), (xx, h - 10)])
            else:                                                     # floor bands near the top
                for i in range(rng.randint(2, 3)):
                    yy = h - 14 - 13 * i
                    if yy > 12: lines.append([(x0 + 4, yy), (x1 - 4, yy)])
    elif style in ('euro', 'paris', 'nordic', 'old'):
        kind = rng.random()
        if style == 'paris':                                          # mansard roof with chimneys
            mh = rng.uniform(9, 13)
            P = [(x0, 0), (x1, 0), (x1, h), (x1 - 4, h + mh), (x0 + 4, h + mh), (x0, h)]
            g.S(closed(P))
            for k in range(rng.randint(1, 2)):
                ch = rng.uniform(x0 + 8, x1 - 12)
                g.S(R(ch, h + mh - 2, ch + 5, h + mh + 7))
            if rng.random() < win + 0.2 and w > 22:
                lines += window_rows(x0 + 4, x1 - 4, [h - 16, h - 32], step=11, ln=8, kind='v')
                if rng.random() < 0.6: lines.append([(x0, h - 6), (x1, h - 6)])
        elif style == 'nordic' or kind < 0.45 and w < 40:             # front gable
            ph = rng.uniform(0.45, 0.75) * w
            g.S(closed([(x0, 0), (x1, 0), (x1, h), (cx, h + ph), (x0, h)]))
            if rng.random() < win and w > 18 and h > 30:
                lines += window_rows(x0 + 3, x1 - 3, [h - 16, h - 32], step=10, ln=8, kind='v')
        else:                                                         # side roof with a chimney
            ph = rng.uniform(10, 18)
            g.S(closed([(x0, 0), (x1, 0), (x1, h), (x1 - ph * 0.8, h + ph), (x0 + ph * 0.8, h + ph), (x0, h)]))
            if w > 26 and rng.random() < 0.7:
                ch = rng.uniform(x0 + ph, x1 - ph - 6)
                g.S(R(ch, h + ph - 3, ch + 5, h + ph + 6))
            if rng.random() < win and w > 22 and h > 30:
                lines += window_rows(x0 + 4, x1 - 4, [h - 16, h - 32], step=11, ln=8, kind='v')
    elif style in ('mideast', 'desert'):
        g.S(R(x0, 0, x1, h))
        if r < 0.22 and w > 24:
            g.S(dome(cx, h, w * 0.3, w * 0.26, 10))
        elif r < 0.4:
            g.S(R(x0 + w * 0.15, h - 1, x0 + w * 0.45, h + 8))
        if rng.random() < win and w > 20 and h > 24:
            n = int((w - 8) // 12)
            for i in range(n):
                xx = x0 + (w - (n - 1) * 12) / 2 + 12 * i
                lines.append(arch(xx, h - 22, 6, 7, 'round', 4))
    elif style == 'low':
        g.S(R(x0, 0, x1, h))
    else:
        g.S(R(x0, 0, x1, h))
    g.LL(lines)
    return g

# ---------------------------------------------------------------- the city
class City:
    def __init__(self, name, seed=0, water=False, top=330):
        self.name = name; self.rng = random.Random(seed); self.water = water
        self.parts = []; self.lms = []; self.blds = []
        self.refl = []          # (x, width) reflection anchors
        self.extra = []         # lines added after everything (in world coords)
        self.ground_x = (0, 1000)
    def put(self, g, z):
        self.parts.append((z, len(self.parts), g)); return g
    def lm(self, g, x, s=1.0, z=5, y=0.0, front=0.0, behind=None, refl=True, pad=6, sy=None):
        w = g.at(x, y, s, sy)
        self.put(w, z)
        x0, y0, x1, y1 = w.bounds()
        self.lms.append(dict(x0=x0, x1=x1, top=y1, z=z, holes=w.holes, front=front, behind=behind, pad=pad))
        if refl and self.water: self.refl.append((x, (x1 - x0)))
        return w
    def hills(self, P, z=0.0, lines=()):
        g = G(); g.S(P); g.LL(lines); self.put(g, z); return g
    def cap(self, z, x0, x1):
        c = 1e9
        for L in self.lms:
            if x1 < L['x0'] - L['pad'] or x0 > L['x1'] + L['pad']: continue
            if L['z'] > z:
                if L['behind'] is not None: c = min(c, L['behind'])
                for hp in L['holes']:
                    hx0, hy0, hx1, hy1 = hp.bounds
                    if x1 > hx0 - 3 and x0 < hx1 + 3: c = min(c, hy0 - 8)
            else:
                c = min(c, L['front'])
        return c
    def ok(self, x0, x1, h):
        """Keeps roof lines and walls of different buildings from running too close together."""
        for z, a0, a1, hh in self.blds:
            if a1 < x0 - 1 or a0 > x1 + 1: continue
            if abs(hh - h) < 9: return False
            for e in (a0, a1):
                for f in (x0, x1):
                    if 0.5 < abs(e - f) < 7: return False
        return True
    def fill(self, z, x0, x1, h=(40, 100), w=(18, 40), style='modern', gap=(-6, 6), win=0.3, prof=None, minh=14, skip=0.0):
        rng = self.rng
        x = x0 + rng.uniform(0, 6)
        while x < x1 - 8:
            bw = rng.uniform(*w)
            bx0, bx1 = x, min(x + bw, x1)
            if bx1 - bx0 < 10: break
            placed = False
            if rng.random() >= skip:
                for attempt in range(6):
                    bh = rng.uniform(*h) * (prof((bx0 + bx1) / 2) if prof else 1.0)
                    c = self.cap(z, bx0, bx1)
                    if c < minh: break
                    bh = min(bh, c)
                    if bh < minh: break
                    if self.ok(bx0, bx1, bh):
                        self.put(bldg(rng, bx0, bx1, bh, style, win), z)
                        self.blds.append((z, bx0, bx1, bh)); placed = True
                        break
                    bx1 = min(bx1 + rng.uniform(-3, 3), x1)
            x = bx1 + rng.uniform(*gap)
    def add_building(self, z, x0, x1, h, style='modern', win=0.0):
        self.put(bldg(self.rng, x0, x1, h, style, win), z); self.blds.append((z, x0, x1, h))
    def boat(self, g):
        self.put(g, 50)
    def front(self, g, z=40):
        self.put(g, z)
    def build(self, refl_n=None, size=30, spacing=None, label=None):
        sc = Scene()
        for z, i, g in sorted(self.parts, key=lambda t: (t[0], t[1])):
            if z >= 50: continue
            for k, geom, f, o in g.ops:
                sc.items.append(('shape' if k == 'S' else 'line', geom, f, o))
        gx0, gx1 = self.ground_x
        # hide everything below the ground or water line
        sc.items.append(('shape', Polygon(R(-200, -400, 1200, 0)), True, False))
        sc.items.append(('line', LineString([(gx0, 0), (gx1, 0)]), False, True))
        if self.water:
            rng = random.Random(len(self.name) * 7 + 3)
            for x, w in self.refl:
                for k, (dy, f) in enumerate(((-7, 0.55), (-14, 0.36), (-21, 0.2))):
                    ww = max(10, w * f + rng.uniform(-4, 4))
                    if k == 2 and w < 40: continue
                    xx = x + rng.uniform(-6, 6)
                    sc.items.append(('line', LineString([(xx - ww / 2, dy), (xx + ww / 2, dy)]), False, True))
            for i in range(refl_n if refl_n is not None else 5):
                xx = rng.uniform(40, 960); dy = rng.choice((-9, -17)); ww = rng.uniform(14, 30)
                sc.items.append(('line', LineString([(xx - ww / 2, dy), (xx + ww / 2, dy)]), False, True))
        for z, i, g in sorted(self.parts, key=lambda t: (t[0], t[1])):
            if z < 50: continue
            for k, geom, f, o in g.ops:
                sc.items.append(('shape' if k == 'S' else 'line', geom, f, o))
        L = sc.render()
        L = [[(x, -y) for x, y in P] for P in L]
        L = [P for P in L if LineString(P).length > 3.0]
        lab = (label or self.name).upper()
        sp = spacing if spacing is not None else (13 if len(lab) < 12 else 9)
        L += text(lab, 500, 64, size=size, font=FONT, spacing=sp)
        return L
