"""Leaves: botanical line drawings of leaves — simple, lobed, palmate and compound — with their veins,
including New Zealand natives (silver fern, kawakawa, harakeke, kōwhai, pōhutukawa) and a koru.
Usage: python3 -I gen_leaves.py <out.json> [sheet.png]"""
import math, sys, random, os
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

OUT = sys.argv[1]
SHEET = sys.argv[2] if len(sys.argv) > 2 else None

# ---------------------------------------------------------------- simple leaf: profile + margin + veins
def profile(kind, t):
    """Half-width of the blade (0…1 of the widest) at t (0 = base, 1 = tip)."""
    if kind == 'elliptic': return math.sin(math.pi * t) ** 0.75
    if kind == 'ovate': return math.sin(math.pi * t ** 0.72) ** 0.8
    if kind == 'obovate': return math.sin(math.pi * t ** 1.45) ** 0.75
    if kind == 'lanceolate': return math.sin(math.pi * t ** 0.85) ** 1.1
    if kind == 'linear': return min(1, 6 * t) * (1 - t) ** 0.35 if t < 1 else 0
    if kind == 'orbicular': return math.sqrt(max(0, 1 - (2 * t - 1) ** 2))
    if kind == 'cordate': return math.sin(math.pi * t ** 0.62) ** 0.9 * (1 + 0.25 * math.exp(-((t - 0.08) / 0.06) ** 2))
    if kind == 'deltoid': return (1 - t) ** 0.9 * min(1, t * 9)
    if kind == 'spatulate': return math.sin(math.pi * t ** 1.9) ** 0.6
    if kind == 'falcate': return math.sin(math.pi * t ** 0.9) ** 1.2
    return math.sin(math.pi * t)

def margin(kind, u, n, amp):
    """Teeth on the edge: u = position along the edge (0…1), n = number of teeth, amp = depth."""
    f = (u * n) % 1.0
    if kind == 'serrate': return -amp * (1 - f) ** 1.5                         # teeth pointing to the tip
    if kind == 'dentate': return -amp * abs(2 * f - 1)
    if kind == 'crenate': return amp * (abs(math.sin(math.pi * u * n)) - 1)
    if kind == 'undulate': return amp * math.sin(2 * math.pi * u * n)
    if kind == 'double': return -amp * (1 - f) ** 1.5 - amp * 0.5 * (1 - (u * n * 2) % 1.0) ** 1.5
    if kind == 'spiny': return -amp * abs(2 * f - 1) ** 0.5
    return 0.0

def simple_leaf(L=1000, W=0.32, kind='elliptic', edge='entire', teeth=24, amp=0.02, tip=0.0, petiole=0.12, veins=8, vein_angle=0.22,
                curve=0.0, asym=0.0, arcuate=False, base_lobes=0.0, n=160):
    """Returns (outline polygon, vein lines). The leaf points up: base at (0, 0), tip at (0, -L)."""
    W *= L
    def mid(t):        # the midrib may curve to one side
        return curve * L * math.sin(math.pi * t) * 0.5 * t
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        w = W * profile(kind, t)
        if tip and t > 1 - tip: w *= max(0.0, (1 - t) / tip) ** 0.6           # drawn-out tip
        if base_lobes and t < 0.2: w *= 1 + base_lobes * math.exp(-((t - 0.05) / 0.06) ** 2)
        e = margin(edge, t, teeth, amp * L) if 0.03 < t < 0.97 else 0
        y = -t * L; c = mid(t)
        right.append((c + max(0, w + e) * (1 + asym), y)); left.append((c - max(0, w + e) * (1 - asym), y))
    outline = right + left[::-1]
    poly = Polygon(outline).buffer(0)
    lines = [[(0, petiole * L), (mid(0), 0)] + [(mid(t), -t * L) for t in np.linspace(0, 0.98, 40)]]
    for k in range(veins):
        t0 = 0.1 + 0.8 * (k + 0.5) / veins
        for side in (1, -1):
            t1 = min(0.95, t0 + vein_angle) if not arcuate else t0 + (0.93 - t0) * 0.75
            w1 = W * profile(kind, t1) * (0.86 if not arcuate else 0.72)
            p0 = (mid(t0), -t0 * L); p2 = (mid(t1) + side * w1, -t1 * L); p1 = (mid(t0) + side * w1 * 0.55, -(t0 + (t1 - t0) * 0.25) * L)
            v = LineString(quad(p0, p1, p2, n=14)).intersection(poly.buffer(-L * 0.012))
            lines += lines_of(v)
    return poly, lines

def heart_leaf(L=1000, W=0.42, asym=0.0, edge='entire', teeth=30, amp=0.012, tip=0.2, lobe=0.12, veins=5, petiole=0.15, sinus=0.05):
    """A heart-shaped (cordate) leaf: rounded lobes either side of the stalk, pointed tip; veins fan
    out from where the stalk joins."""
    W *= L
    def half(side):
        k = 1 + side * asym
        ctl = [(0, -sinus * L), (0.22 * W * k, lobe * L * 0.8), (0.7 * W * k, lobe * L * 0.55), (W * k, -0.22 * L), (0.82 * W * k, -0.55 * L),
               (0.42 * W * k, -0.8 * L), (0.1 * W * k, -(1 - tip * 0.3) * L), (0, -L)]
        pts = spline(ctl, n=14)
        return [(side * x, y) for x, y in pts]
    right, left = half(1), half(-1)
    outline = right + left[::-1]
    if edge != 'entire':                           # teeth: push points inwards along the normal
        tot = [0.0]
        for i in range(1, len(outline)): tot.append(tot[-1] + math.hypot(outline[i][0] - outline[i - 1][0], outline[i][1] - outline[i - 1][1]))
        out = []
        for i, (x, y) in enumerate(outline):
            a, b = outline[max(0, i - 1)], outline[min(len(outline) - 1, i + 1)]
            nx, ny = (b[1] - a[1]), -(b[0] - a[0]); nl = math.hypot(nx, ny) or 1
            u = tot[i] / tot[-1]
            d = margin(edge, u, teeth, amp * L) if 0.02 < u < 0.98 else 0
            out.append((x - d * nx / nl, y - d * ny / nl))
        outline = out
    poly = Polygon(outline).buffer(0)
    lines = [[(0, petiole * L), (0, -sinus * L)] + [(0, -t * L) for t in np.linspace(sinus, 0.97, 30)]]
    base = (0, -sinus * L); inner = poly.buffer(-L * 0.012)
    nv = max(1, veins // 2)
    for k in range(nv):
        a = math.radians(24 + (112 - 24) * k / max(1, nv - 1))      # from near the midrib down into the lobes
        for side in (1, -1):
            d = (side * math.sin(a), -math.cos(a))
            ray = LineString([base, (base[0] + d[0] * 3 * L, base[1] + d[1] * 3 * L)])
            hit = ray.intersection(poly.boundary)
            pts = [hit] if hit.geom_type == 'Point' else list(getattr(hit, 'geoms', []))
            if not pts: continue
            rs = [math.hypot(q.x - base[0], q.y - base[1]) for q in pts]
            rs = [r for r in rs if r > 0.06 * L]            # the stalk joins on the outline itself
            if not rs: continue
            r = min(rs)
            bend = math.radians(-14 if a < math.radians(95) else 10) * side   # upper veins arch towards the tip, lower ones droop
            c, s_ = math.cos(bend), math.sin(bend)
            cd = (d[0] * c - d[1] * s_, d[0] * s_ + d[1] * c)
            end = (base[0] + d[0] * r * 0.86, base[1] + d[1] * r * 0.86)
            c1 = (base[0] + cd[0] * r * 0.5, base[1] + cd[1] * r * 0.5)
            lines += lines_of(LineString(quad(base, c1, end, n=18)).intersection(inner))
    return poly, lines

def leaf_lines(poly, veins, extra=()):
    L = lines_of(poly)
    return L + [v for v in veins if len(v) > 1] + list(extra)

# ---------------------------------------------------------------- palmate (maple-like) leaves
def palmate(lobes=5, depth=0.55, spread=200, lobe_w=0.32, teeth=7, amp=0.035, sharp=True, petiole=0.3, round_tips=False, R=500):
    """Lobes radiating from the base, with a vein to each tip."""
    angs = np.radians(np.linspace(-spread / 2, spread / 2, lobes)) - math.pi / 2
    pts = []
    N = 720
    for i in range(N):
        th = -math.pi / 2 - math.radians(spread / 2 + 40) + i / N * math.radians(spread + 80)
        r = R * (1 - depth)
        for k, a in enumerate(angs):
            d = (th - a)
            g = math.exp(-(d / (lobe_w * (1.15 if 0 < k < lobes - 1 else 1))) ** 2) * (1 - 0.18 * abs(k - (lobes - 1) / 2) / max(1, (lobes - 1) / 2))
            r = max(r, R * (1 - depth) + R * depth * (g if round_tips else g ** 0.7))
        f = (i * teeth * lobes / N) % 1.0
        r += -R * amp * (1 - f) ** 1.6 if teeth else 0
        pts.append((r * math.cos(th), r * math.sin(th)))
    pts.append((0, R * 0.08)); pts.append(pts[0])
    poly = Polygon(pts).buffer(0)
    veins = [[(0, R * petiole), (0, 0)]]
    for a in angs:
        tip = [(0, 0)] + [(t * R * 0.93 * math.cos(a), t * R * 0.93 * math.sin(a)) for t in np.linspace(0.1, 1, 12)]
        veins += lines_of(LineString(tip).intersection(poly.buffer(-R * 0.02)))
        for t in (0.35, 0.6):            # side veins of each lobe
            bx, by = t * R * 0.93 * math.cos(a), t * R * 0.93 * math.sin(a)
            for s in (1, -1):
                b2 = a + s * 0.55
                v = LineString([(bx, by), (bx + 0.28 * R * math.cos(b2), by + 0.28 * R * math.sin(b2))]).intersection(poly.buffer(-R * 0.02))
                veins += lines_of(v)
    return poly, veins

# ---------------------------------------------------------------- compound leaves
def place(poly, veins, x, y, ang, s):
    """A leaflet (pointing up from (0,0)) moved to (x, y), turned ang radians and scaled s."""
    P = affinity.translate(affinity.rotate(affinity.scale(poly, s, s, origin=(0, 0)), ang, origin=(0, 0), use_radians=True), x, y)
    V = [[(x + s * (px * math.cos(ang) - py * math.sin(ang)), y + s * (px * math.sin(ang) + py * math.cos(ang))) for px, py in v] for v in veins]
    return P, V

def pinnate(n_pairs=5, leaflet=None, spacing=150, length=None, terminal=True, droop=0.0, alt=False, leaf_scale=1.0, taper=0.2):
    lf = leaflet or simple_leaf(L=300, W=0.3, kind='elliptic', veins=5, petiole=0.08)
    length = length or spacing * (n_pairs + 1)
    sc = Scene()
    rach = [(0, 120)] + [(droop * 200 * math.sin(math.pi * t / 2), -t * length) for t in np.linspace(0, 1, 30)]
    sc.line(rach)
    parts = []
    for k in range(n_pairs):
        t = (k + 0.6) / (n_pairs + 0.6)
        y = -t * length; x = droop * 200 * math.sin(math.pi * t / 2)
        s = leaf_scale * (1 - taper * t)
        for side in (1, -1):
            if alt and side == -1: y2 = y - spacing * 0.45
            else: y2 = y
            ang = side * math.radians(62 - 18 * t)
            parts.append(place(*lf, x, y2, ang, s))
    if terminal: parts.append(place(*lf, droop * 200, -length, 0, leaf_scale * (1 - taper * 0.9)))
    for P, V in parts:
        sc.geom(P); sc.lines(V)
    return sc.render()

def palmate_compound(n=7, leaflet_L=420, spread=210, W=0.24, edge='serrate'):
    sc = Scene(); sc.line([(0, 380), (0, 0)])
    for k in range(n):
        a = math.radians(-spread / 2 + spread * k / (n - 1))
        L = leaflet_L * (1 - 0.35 * abs(k - (n - 1) / 2) / ((n - 1) / 2))
        P, V = simple_leaf(L=L, W=W, kind='obovate', edge=edge, teeth=30, amp=0.012, veins=9, petiole=0.0)
        P, V = place(P, V, 0, 0, a, 1)
        sc.geom(P); sc.lines(V)
    return sc.render()

def fern(length=1000, pinnae=22, width=0.36, crenate=True, silver=False):
    """A fern frond: pinnae along the stem, each drawn as a narrow leaflet with a scalloped edge."""
    sc = Scene()
    stem = [(0, 140)] + [(30 * math.sin(t * 2.2), -t * length) for t in np.linspace(0, 1, 60)]
    sc.line(stem)
    for k in range(pinnae):
        t = (k + 0.5) / pinnae
        y = -t * length; x = 30 * math.sin(t * 2.2)
        pl = length * width * math.sin(math.pi * (0.12 + 0.88 * t) ** 0.85) * (1 - t * 0.3)
        if silver: pl = length * width * (1 - t) ** 0.8 * min(1, 4 * t + 0.35)
        for side in (1, -1):
            a = side * math.radians(68 - 22 * t)
            P, V = simple_leaf(L=pl, W=0.2, kind='lanceolate', edge='crenate' if crenate else 'entire', teeth=max(4, int(pl / 28)), amp=0.05, veins=0, petiole=0.0, n=60)
            P, V = place(P, V, x, y, a, 1)
            sc.geom(P); sc.lines(V)
    return sc.render()

def koru(turns=2.4):
    """An unfurling fern frond: a spiral that opens into a stem, with little leaflets on the way."""
    L = []
    th = np.linspace(0, turns * 2 * math.pi, 400)
    r = 40 * np.exp(0.19 * th)
    sp = [(float(rr * math.cos(t)), float(rr * math.sin(t))) for rr, t in zip(r, th)]
    end = sp[-1]
    stem = sp + [(end[0] + 20, end[1] + k * 22) for k in range(1, 18)]
    L.append(stem)
    inner = [(float(0.82 * rr * math.cos(t)), float(0.82 * rr * math.sin(t))) for rr, t in zip(r[60:], th[60:])]
    L.append(inner)
    for i in range(90, 400, 22):
        x, y = sp[i]; nx, ny = sp[min(i + 1, len(sp) - 1)]
        a = math.atan2(ny - y, nx - x) + math.pi / 2; s = 0.12 * r[i]
        L.append([(x, y), (x + s * math.cos(a), y + s * math.sin(a))])
    return L

def monstera(R=480, seed=3):
    rg = random.Random(seed)
    P, V = heart_leaf(L=2 * R, W=0.5, veins=0, petiole=0.12, lobe=0.14)
    cuts = []
    for k in range(7):
        t = 0.2 + 0.095 * k
        for side in (1, -1):
            y0 = -t * 2 * R
            if rg.random() < 0.85:                                   # a slit from the edge towards the middle
                cuts.append(LineString([(side * R * 0.3, y0), (side * R * 1.3, y0 - R * 0.25)]).buffer(20 + rg.uniform(0, 10), cap_style=1))
            if rg.random() < 0.8:                                    # a hole between slits, near the midrib
                h = affinity.rotate(affinity.scale(Point(0, 0).buffer(40, quad_segs=12), 1.0, 0.45), side * 20)
                cuts.append(affinity.translate(h, side * R * 0.17, y0 - R * 0.11))
    leaf = P.difference(unary_union(cuts))
    veins = [[(0, 0.24 * R), (0, -1.88 * R)]]
    return lines_of(leaf) + veins

def ginkgo(R=480):
    pts = [(0, 0)]
    for a in np.linspace(math.radians(-150), math.radians(-30), 80):
        notch = 0.12 * math.exp(-((a + math.pi / 2) / 0.07) ** 2)
        wav = 0.025 * math.sin(a * 40)
        r = R * (1 - notch + wav)
        pts.append((r * math.cos(a), r * math.sin(a)))
    pts.append((0, 0))
    poly = Polygon(pts).buffer(0)
    veins = [[(0, 0), (0.95 * R * math.cos(a), 0.95 * R * math.sin(a))] for a in np.linspace(math.radians(-145), math.radians(-35), 22)]
    veins = [q for v in veins for q in lines_of(LineString(v).intersection(poly.buffer(-12)))]
    return lines_of(poly) + veins + [[(0, 0), (0, 300)]]

def harakeke(n=9):
    """New Zealand flax: a fan of long blades from the base, each with a fold down the middle."""
    sc = Scene(); L = []
    for k in range(n):
        a = math.radians(-58 + 116 * k / (n - 1)) + 0.05 * math.sin(k * 3)
        ln = 900 * (0.6 + 0.4 * math.cos(a * 1.1))
        bend = 0.25 * a
        centre = [(math.sin(a + bend * t) * ln * t, -math.cos(a + bend * t) * ln * t) for t in np.linspace(0, 1, 40)]
        w = 26
        left = []; right = []
        for i, (x, y) in enumerate(centre):
            t = i / 39; ang = a + bend * t; ww = w * (1 - t) ** 0.4 if t < 1 else 0
            nx, ny = math.cos(ang), math.sin(ang)
            left.append((x - nx * ww, y - ny * ww)); right.append((x + nx * ww, y + ny * ww))
        poly = Polygon(left + right[::-1]).buffer(0)
        sc.geom(poly); sc.line(centre[2:-3])
    sc.geom(Polygon([(-70, 0), (70, 0), (50, 60), (-50, 60)]))
    return sc.render()

def palm_frond(n=26, length=1000):
    L = [[(0, 120)] + [(80 * t * t, -t * length) for t in np.linspace(0, 1, 50)]]
    for k in range(n):
        t = (k + 1) / (n + 1); x, y = 80 * t * t, -t * length
        ln = length * 0.42 * math.sin(math.pi * (0.2 + 0.8 * t)) ** 0.7
        for side in (1, -1):
            a = side * math.radians(55 - 20 * t)
            p2 = (x + math.sin(a) * ln, y - math.cos(a) * ln + ln * 0.25)
            ctl = (x + math.sin(a) * ln * 0.5, y - math.cos(a) * ln * 0.6)
            c = quad((x, y), ctl, p2, n=12)
            wid = 9
            L.append(c); L.append([(px + wid * side * 0.3, py + wid) for px, py in c[2:]])
    return L

def fan_palm(n=17, R=480):
    L = []
    angs = np.linspace(math.radians(-170), math.radians(-10), n)
    for a in angs:
        tip = (R * math.cos(a), R * math.sin(a))
        L.append([(0.18 * R * math.cos(a), 0.18 * R * math.sin(a)), tip])
        for s in (-1, 1):
            b = a + s * math.radians(160 / n / 2)
            L.append([(0.18 * R * math.cos(b), 0.18 * R * math.sin(b)), (R * 0.82 * math.cos(b), R * 0.82 * math.sin(b)), (tip[0] * 0.98, tip[1] * 0.98)])
    L.append(arc(0, 0, 0.18 * R, math.radians(-175), math.radians(-5), n=40))
    L.append([(0, 0), (0, 0.6 * R)])
    return L

def pair(kind='ovate', edge='serrate', n_pairs=3):
    """A sprig: pairs of leaves on a stem, plus one at the top (mint, basil…)."""
    sc = Scene(); stem = [(0, 300), (0, -820)]
    sc.line(stem)
    for k in range(n_pairs):
        y = 150 - k * 300; s = 1 - 0.18 * k
        for side in (1, -1):
            P, V = simple_leaf(L=420, W=0.38, kind=kind, edge=edge, teeth=16, amp=0.025, veins=5, petiole=0.08)
            P, V = place(P, V, 0, y, side * math.radians(58), s)
            sc.geom(P); sc.lines(V)
    P, V = simple_leaf(L=380, W=0.34, kind=kind, edge=edge, teeth=14, amp=0.025, veins=4, petiole=0.0)
    P, V = place(P, V, 0, -770, 0, 0.6); sc.geom(P); sc.lines(V)
    return sc.render()

# ---------------------------------------------------------------- the leaves
items = []
def add(name, L, slug=None):
    it = Item('leaves', name, [P for P in L if len(P) > 1], author='Made for this library', source='generated', license='public domain')
    it.slug = slug or name.lower().replace(' ', '-'); items.append(it)

S = lambda **k: leaf_lines(*simple_leaf(**k))
add('Beech leaf', S(W=0.3, kind='elliptic', edge='undulate', teeth=9, amp=0.012, veins=9, vein_angle=0.16))
add('Birch leaf', S(W=0.36, kind='ovate', edge='double', teeth=16, amp=0.02, veins=7, tip=0.12))
add('Willow leaf', S(W=0.12, kind='lanceolate', edge='serrate', teeth=40, amp=0.005, veins=12, vein_angle=0.12, curve=0.12))
add('Eucalyptus leaf', S(W=0.14, kind='falcate', edge='entire', veins=10, vein_angle=0.1, curve=0.5, tip=0.15, arcuate=True))
add('Bay leaf', S(W=0.24, kind='elliptic', edge='undulate', teeth=5, amp=0.006, veins=8, vein_angle=0.18))
add('Magnolia leaf', S(W=0.3, kind='obovate', veins=10, vein_angle=0.2))
add('Chestnut leaf', S(W=0.2, kind='lanceolate', edge='spiny', teeth=18, amp=0.03, veins=16, vein_angle=0.1, tip=0.1))
add('Elm leaf', S(W=0.33, kind='ovate', edge='double', teeth=18, amp=0.022, veins=12, vein_angle=0.14, asym=0.12, tip=0.1))
add('Linden leaf', leaf_lines(*heart_leaf(W=0.44, asym=0.08, edge='serrate', teeth=34, amp=0.012, veins=7)))
add('Poplar leaf', S(W=0.45, kind='deltoid', edge='crenate', teeth=18, amp=0.018, veins=5, tip=0.08))
add('Aspen leaf', S(W=0.5, kind='orbicular', edge='crenate', teeth=16, amp=0.02, veins=5))
add('Holly leaf', S(W=0.3, kind='elliptic', edge='spiny', teeth=5, amp=0.11, veins=6))
add('Hosta leaf', S(W=0.38, kind='ovate', veins=7, vein_angle=0.38, arcuate=True, tip=0.1))
add('Dogwood leaf', S(W=0.33, kind='elliptic', veins=5, vein_angle=0.45, arcuate=True, tip=0.12))
add('Kawakawa leaf', leaf_lines(*heart_leaf(W=0.5, lobe=0.16, veins=7, tip=0.12)))
add('Pōhutukawa leaf', S(W=0.28, kind='elliptic', veins=9, vein_angle=0.14, petiole=0.08))
add('Heart-shaped leaf', leaf_lines(*heart_leaf(W=0.46, lobe=0.12, veins=5, tip=0.3)))
add('Grass blades', [q for k in range(7) for q in lines_of(Polygon([(math.sin(a) * 900 * t + 260 * (a) * t * t - 0.3 * 40 * (1 - t), -math.cos(a) * 900 * t * (0.75 + 0.25 * math.cos(3 * a)) ) for a in [math.radians(-36 + 12 * k)] for t in np.linspace(0, 1, 40)] + [(math.sin(a) * 900 * t + 260 * a * t * t + 0.3 * 40 * (1 - t), -math.cos(a) * 900 * t * (0.75 + 0.25 * math.cos(3 * a))) for a in [math.radians(-36 + 12 * k)] for t in np.linspace(1, 0, 40)]).buffer(0))])
add('Spoon-shaped leaf', S(W=0.3, kind='spatulate', veins=6, vein_angle=0.15))
add('Serrated oval leaf', S(W=0.32, kind='elliptic', edge='serrate', teeth=22, amp=0.02, veins=8, tip=0.06))
add('Begonia leaf', leaf_lines(*heart_leaf(W=0.42, asym=0.3, edge='dentate', teeth=26, amp=0.014, veins=7, lobe=0.16, tip=0.25)))
add('Banana leaf', S(W=0.24, kind='elliptic', edge='entire', veins=34, vein_angle=0.05, petiole=0.15))
add('Lily pad', lines_of(Point(0, 0).buffer(480, quad_segs=48).difference(Polygon([(0, 0), (100, -500), (-100, -500)])))
    + [[(0, 0), (455 * math.cos(a), 455 * math.sin(a))] for a in np.linspace(math.radians(-66), math.radians(246), 13)])
add('Lotus leaf', [circle(0, 0, 480, n=200), circle(0, 0, 30, n=20)] + [[(30 * math.cos(a), 30 * math.sin(a)), (470 * math.cos(a), 470 * math.sin(a))] for a in np.linspace(0, 2 * math.pi, 15)[:-1]])
# lobed
def oak(lobes=5, depth=0.42, W=0.38, round_=True):
    P, V = simple_leaf(W=W, kind='obovate', veins=0, petiole=0.08)
    pts = []
    n = 300
    for i in range(n + 1):
        t = i / n
        w = W * 1000 * profile('obovate', t)
        f = math.cos(2 * math.pi * t * lobes) if round_ else (2 * abs((t * lobes) % 1 - 0.5))
        w *= 1 - depth * (0.5 + 0.5 * f) * (0.4 + 0.6 * math.sin(math.pi * t))
        pts.append((w, -t * 1000))
    outline = pts + [(-x, y) for x, y in pts[::-1]]
    poly = Polygon(outline).buffer(0)
    veins = [[(0, 80), (0, -980)]]
    for k in range(lobes):
        t = (k + 0.1) / lobes
        for side in (1, -1):
            w = W * 1000 * profile('obovate', t) * 0.8
            veins += lines_of(LineString([(0, -t * 1000 + 60), (side * w, -t * 1000)]).intersection(poly.buffer(-12)))
    return lines_of(poly) + veins
add('Oak leaf', oak(5, 0.45))
add('Red oak leaf', oak(4, 0.55, W=0.42, round_=False))
add('White oak leaf', oak(6, 0.5, W=0.36))
add('Maple leaf', leaf_lines(*palmate(5, 0.55, 210, 0.32, teeth=5, amp=0.04)))
add('Sugar maple leaf', leaf_lines(*palmate(5, 0.62, 220, 0.28, teeth=3, amp=0.06)))
add('Japanese maple leaf', leaf_lines(*palmate(7, 0.75, 250, 0.2, teeth=12, amp=0.02)))
add('Sweetgum leaf', leaf_lines(*palmate(5, 0.72, 240, 0.2, teeth=14, amp=0.012)))
add('Lime-green heart leaf', leaf_lines(*heart_leaf(W=0.36, lobe=0.08, veins=5, tip=0.4, edge='crenate', teeth=26, amp=0.01)))
add('Plane tree leaf', leaf_lines(*palmate(5, 0.5, 200, 0.33, teeth=4, amp=0.05)))
add('Ivy leaf', leaf_lines(*palmate(5, 0.35, 190, 0.38, teeth=0, amp=0, round_tips=True)))
add('Grape leaf', leaf_lines(*palmate(5, 0.4, 200, 0.36, teeth=10, amp=0.03)))
add('Fig leaf', leaf_lines(*palmate(5, 0.7, 210, 0.26, teeth=0, amp=0, round_tips=True)))
add('Three-lobed leaf', leaf_lines(*palmate(3, 0.5, 140, 0.4, teeth=8, amp=0.025)))
add('Monstera leaf', monstera())
add('Ginkgo leaf', ginkgo())
# compound
lf = lambda **k: simple_leaf(L=300, petiole=0.05, **k)
add('Ash leaf', pinnate(5, lf(W=0.25, kind='lanceolate', edge='serrate', teeth=18, amp=0.012, veins=5), spacing=150, droop=0.2))
add('Rowan leaf', pinnate(7, lf(W=0.24, kind='elliptic', edge='serrate', teeth=16, amp=0.02, veins=4), spacing=115, droop=0.15, taper=0.05))
add('Kōwhai leaf', pinnate(14, lf(W=0.42, kind='obovate', veins=0), spacing=62, leaf_scale=0.42, droop=0.35, taper=0.3))
add('Rose leaf', pinnate(2, lf(W=0.36, kind='ovate', edge='serrate', teeth=16, amp=0.025, veins=5), spacing=230, leaf_scale=1.05))
add('Walnut leaf', pinnate(4, lf(W=0.3, kind='elliptic', veins=6), spacing=170))
add('Horse chestnut leaf', palmate_compound(7))
add('Lupin leaf', palmate_compound(9, leaflet_L=380, spread=300, W=0.14, edge='entire'))
def trifoliate(edge='entire', kind='obovate', notch=False):
    sc = Scene(); sc.line([(0, 380), (0, 0)])
    for a in (-75, 0, 75):
        P, V = simple_leaf(L=430, W=0.42, kind=kind, edge=edge, teeth=16, amp=0.02, veins=5, petiole=0.0)
        if notch: P = P.difference(Polygon([(0, -330), (-40, -440), (40, -440)]))
        P, V = place(P, V, 0, 0, math.radians(a), 1)
        sc.geom(P); sc.lines(V)
    return sc.render()
add('Clover leaf', trifoliate(notch=True))
add('Strawberry leaf', trifoliate('serrate', 'ovate'))
add('Fern frond', fern())
add('Silver fern (ponga)', fern(pinnae=26, width=0.34, silver=True))
add('Koru', koru())
add('Harakeke (flax)', harakeke())
add('Palm frond', palm_frond())
add('Fan palm leaf', fan_palm())
add('Mint sprig', pair('ovate', 'serrate'))
add('Basil sprig', pair('ovate', 'entire'))
add('Olive sprig', pair('lanceolate', 'entire', 4))

save(items, OUT)
print(len(items), 'leaves')
if SHEET:
    for i in range(0, len(items), 64):
        sheet(items[i:i + 64], SHEET.replace('.png', f'_{i // 64}.png'), cols=8)
