"""Topography: contour maps of made-up landscapes (islands, volcanoes, valleys, dunes, mesas…), drawn
like a survey map: evenly spaced contour lines, every fifth one doubled, some framed with a north
arrow and a scale bar. Usage: python3 -I gen_topo.py <out.json> [sheet.png]"""
import math, sys, os
import numpy as np
import contourpy
from scipy import ndimage
from shapely.geometry import LineString, Polygon, box as sbox, Point
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

OUT = sys.argv[1]
SHEET = sys.argv[2] if len(sys.argv) > 2 else None
N = 260                                       # grid cells across

def fractal(seed, beta=3.6, n=N):
    """Smooth random terrain: noise with a power-law spectrum (bigger beta = smoother)."""
    rg = np.random.default_rng(seed)
    kx = np.fft.fftfreq(n)[:, None]; ky = np.fft.fftfreq(n)[None, :]
    k = np.sqrt(kx * kx + ky * ky); k[0, 0] = 1
    spec = (rg.normal(size=(n, n)) + 1j * rg.normal(size=(n, n))) / k ** (beta / 2)
    spec[0, 0] = 0
    z = np.real(np.fft.ifft2(spec))
    return (z - z.min()) / (z.max() - z.min())

def grid(n=N):
    y, x = np.mgrid[0:n, 0:n] / (n - 1)
    return x, y

def warp(z, seed, amount=0.06):
    """Bends a height field sideways a little, so shapes are less regular."""
    n = z.shape[0]
    dx = (fractal(seed + 101, 3.6, n) - 0.5) * amount * n; dy = (fractal(seed + 202, 3.6, n) - 0.5) * amount * n
    yy, xx = np.mgrid[0:n, 0:n]
    return ndimage.map_coordinates(z, [np.clip(yy + dy, 0, n - 1), np.clip(xx + dx, 0, n - 1)], order=1)

def bump(x, y, cx, cy, r, h=1.0): return h * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * r * r))

def contours(z, levels, size=1000):
    g = contourpy.contour_generator(z=z, line_type='Separate')
    k = size / (z.shape[0] - 1)
    out = []
    for lv in levels:
        for seg in g.lines(lv):
            if len(seg) < 3: continue
            out.append([(float(p[0]) * k, float(p[1]) * k) for p in seg])
    return out

def doubled(P, d=4.0):
    """A second line beside an index contour, so it prints bolder."""
    ls = LineString(P)
    if ls.length < 3 * d: return []
    try:
        o = ls.parallel_offset(d, 'left', join_style=1)
    except Exception:
        return []
    return lines_of(o)

def rdp_xy(P, eps):
    if len(P) < 3: return P
    keep = [False] * len(P); keep[0] = keep[-1] = True; st = [(0, len(P) - 1)]
    while st:
        i0, i1 = st.pop(); a, b = P[i0], P[i1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
        bi, bd = -1, -1.0
        for i in range(i0 + 1, i1):
            q = P[i]; d = abs(dy * (q[0] - a[0]) - dx * (q[1] - a[1])) / L if L else math.hypot(q[0] - a[0], q[1] - a[1])
            if d > bd: bd, bi = d, i
        if bd > eps: keep[bi] = True; st += [(i0, bi), (bi, i1)]
    return [q for q, k in zip(P, keep) if k]

def plen(P): return sum(math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]) for i in range(1, len(P)))

def map_lines(z, n_levels=16, index_every=5, lo=None, hi=None, shape='square', frame=False, extras=True, seed=0, sigma=2.0, min_loop=70):
    z = ndimage.gaussian_filter(z, sigma) if sigma else z
    lo = z.min() if lo is None else lo; hi = z.max() if hi is None else hi
    step = (hi - lo) / (n_levels + 1)
    out = []
    for i in range(1, n_levels + 1):
        lv = lo + i * step
        C = contours(z, [lv])
        C = [rdp_xy(smooth(P, iters=1, corner_deg=170), 0.9) for P in C]
        # no tiny rings or scraps: they are noise, not landscape
        C = [P for P in C if plen(P) >= (min_loop if math.hypot(P[0][0] - P[-1][0], P[0][1] - P[-1][1]) < 2 else 40)]
        out += C
        if index_every and i % index_every == 0:
            for P in C: out += doubled(P)
    clip = None
    if shape == 'circle': clip = Point(500, 500).buffer(490, quad_segs=64)
    elif shape == 'square': clip = sbox(6, 6, 994, 994)
    if clip is not None:
        res = []
        for P in out:
            g = LineString(P).intersection(clip)
            res += lines_of(g)
        out = [P for P in res if len(P) > 1]
        if frame or shape == 'circle':
            out.append(list(clip.exterior.coords) if shape == 'circle' else rect(0, 0, 1000, 1000))
    if frame and shape != 'circle':
        out.append(rect(-14, -14, 1028, 1028))
    if extras and frame:
        # north arrow (top right) and a scale bar (bottom left), on a white patch
        sc = Scene()
        sc.lines(out)
        ax, ay = 920, 92
        sc.shape(Point(ax, ay).buffer(58, quad_segs=24), fill=True, outline=False)
        sc.shape([(ax, ay - 46), (ax + 17, ay + 30), (ax, ay + 18), (ax, ay - 46)], fill=False)
        sc.shape([(ax, ay - 46), (ax - 17, ay + 30), (ax, ay + 18), (ax, ay - 46)], fill=False)
        sc.lines(text('N', ax, ay + 62, 22, 'HersheySans1'))
        sc.shape(rect(46, 912, 240, 52), fill=True, outline=False)
        sc.shape(rect(60, 930, 200, 12), fill=False)
        sc.line([(110, 930), (110, 942)]); sc.line([(160, 930), (160, 942)]); sc.line([(210, 930), (210, 942)])
        sc.shape(rect(60, 930, 50, 12), fill=False); sc.shape(rect(160, 930, 50, 12), fill=False)
        sc.lines(text('0', 60, 958, 12, 'HersheySans1')); sc.lines(text('1 km', 262, 958, 12, 'HersheySans1'))
        out = sc.render()
    return out

x, y = grid()
R = lambda cx=0.5, cy=0.5: np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
items = []
def add(name, L, slug):
    it = Item('topography', name, L, author='Made for this library', source='generated', license='public domain', title=name + ' (made-up landscape)')
    it.slug = slug; items.append(it)

# islands
for i, (nm, beta, fall, lv, shape, frame) in enumerate([
        ('Island', 3.6, 1.0, 14, 'square', True), ('Rocky island', 3.2, 1.1, 16, 'square', False), ('Round island', 3.8, 1.3, 12, 'circle', False),
        ('Long island', 3.6, 1.0, 14, 'square', True), ('Twin islands', 3.6, 1.0, 14, 'square', False), ('Island with a bay', 3.5, 1.0, 15, 'square', True)]):
    s = 11 + i
    n = fractal(s, beta)
    if nm == 'Long island': fallz = 1 - np.clip(np.sqrt(((x - 0.5) / 0.48) ** 2 + ((y - 0.5) / 0.22) ** 2), 0, 1.4)
    elif nm == 'Twin islands': fallz = np.maximum(1 - R(0.32, 0.42) / 0.3, 1 - R(0.7, 0.62) / 0.26)
    elif nm == 'Island with a bay': fallz = (1 - R() / 0.45) - 0.9 * bump(x, y, 0.62, 0.7, 0.12)
    else: fallz = 1 - R() / 0.47
    z = warp(n * 0.55 + fallz * fall, s)
    add(nm, map_lines(z, lv, 4, lo=float(np.percentile(z, 52)), shape=shape, frame=frame), f'island-{i + 1}')
# volcanoes and craters
for i, (nm, rim, crater, lv) in enumerate([('Volcano', 0.36, 0.07, 16), ('Volcano with a crater lake', 0.34, 0.11, 18), ('Old crater', 0.3, 0.2, 14),
                                           ('Volcanic cone and vents', 0.33, 0.06, 16)]):
    s = 31 + i
    cone = np.clip(1 - R() / rim, 0, 1) ** 1.6
    pit = bump(x, y, 0.5, 0.5, crater, 0.55 if crater > 0.15 else 0.75)
    z = cone - pit + fractal(s, 3.4) * 0.1
    if 'vents' in nm: z += bump(x, y, 0.28, 0.66, 0.06, 0.25) + bump(x, y, 0.75, 0.3, 0.05, 0.2)
    if 'Old' in nm: z = np.clip(1 - np.abs(R() - 0.25) / 0.2, 0, 1) ** 1.3 + fractal(s, 3.4) * 0.12
    add(nm, map_lines(warp(z, s, 0.04), lv, 5, shape='circle' if i % 2 else 'square', frame=i % 2 == 0), f'volcano-{i + 1}')
# mountains, ridges and peaks
for i, (nm, beta, lv) in enumerate([('Mountains', 3.5, 18), ('Rolling hills', 4.2, 12), ('High peaks', 3.3, 20), ('Foothills', 3.8, 14),
                                    ('Twin peaks', 3.8, 18), ('Long ridge', 3.8, 18), ('Mountain saddle', 3.8, 16), ('Peak in the hills', 3.7, 18)]):
    s = 51 + i
    n = fractal(s, beta)
    if nm == 'Twin peaks': n = n * 0.4 + bump(x, y, 0.35, 0.45, 0.14) + bump(x, y, 0.66, 0.56, 0.12, 0.85)
    if nm == 'Long ridge': n = n * 0.4 + np.exp(-((y - 0.5 - 0.12 * np.sin(x * 5)) ** 2) / 0.02)
    if nm == 'Mountain saddle': n = n * 0.3 + bump(x, y, 0.25, 0.5, 0.15) + bump(x, y, 0.75, 0.5, 0.15) + 0.35 * np.exp(-((y - 0.5) ** 2) / 0.01)
    if nm == 'Peak in the hills': n = n * 0.6 + bump(x, y, 0.55, 0.45, 0.1, 1.0)
    add(nm, map_lines(warp(n, s), lv, 5, frame=i % 3 == 0, shape='circle' if i % 4 == 3 else 'square'), f'mountain-{i + 1}')
# valleys, canyons, rivers
for i, (nm, w, depth, lv) in enumerate([('River valley', 0.08, 0.6, 16), ('Deep canyon', 0.035, 1.0, 20), ('Winding gorge', 0.05, 0.8, 18),
                                        ('Broad valley', 0.16, 0.5, 14), ('Glacial valley', 0.12, 0.7, 16)]):
    s = 71 + i
    path_y = 0.5 + 0.18 * np.sin(x * (3 + i) + i) + 0.05 * np.sin(x * 11 + i)
    d = np.abs(y - path_y)
    prof = np.exp(-(d ** 2) / (2 * w * w)) if nm != 'Glacial valley' else np.clip(1 - (d / (w * 1.8)) ** 2, 0, 1)
    z = fractal(s, 3.6) * 0.6 + y * 0.15 - depth * prof
    add(nm, map_lines(warp(z, s, 0.03), lv, 5, frame=i % 2 == 1), f'valley-{i + 1}')
# mesas, terraces, plateaus
for i, (nm, steps, lv) in enumerate([('Mesa', 3, 18), ('Terraced hill', 6, 18), ('Plateau', 2, 16), ('Stepped cliffs', 5, 20)]):
    s = 81 + i
    base = fractal(s, 3.6) * 0.5 + (1 - R() / 0.5) * 0.8
    q = np.floor(base * steps) / steps
    z = ndimage.gaussian_filter(q, 2.2) + base * 0.08
    add(nm, map_lines(z, lv, 5, frame=i % 2 == 0), f'mesa-{i + 1}')
# dunes and waves of sand
for i, (nm, k, amp, lv) in enumerate([('Sand dunes', 7, 0.06, 6), ('Barchan dunes', 6, 0.1, 10), ('Rippled sand', 11, 0.03, 4)]):
    s = 91 + i
    u = x + amp * np.sin(y * 7 + i) + 0.04 * (fractal(s, 3.4) - 0.5)
    ph = (u * k) % 1.0
    prof = np.where(ph < 0.75, ph / 0.75, (1 - ph) / 0.25)      # gentle windward slope, steep lee face
    z = prof * (0.6 + 0.4 * fractal(s + 5, 3.5)) + 0.3 * fractal(s + 9, 3.0)
    if nm == 'Barchan dunes':
        z = np.zeros_like(x)
        rg = np.random.default_rng(s)
        for _ in range(16):
            cx, cy, r = rg.uniform(0.12, 0.88), rg.uniform(0.12, 0.88), rg.uniform(0.06, 0.12)
            dd = np.sqrt(((x - cx) / r) ** 2 + ((y - cy) / (r * 0.8)) ** 2)
            z += np.clip(1 - dd, 0, 1) ** 1.3 * (1 - 0.6 * np.clip((x - cx) / r + 0.3, 0, 1))
    add(nm, map_lines(z, lv, 0, frame=i == 0, sigma=1.5), f'dunes-{i + 1}')
# lakes, archipelagos, atolls, coasts
specials = [
    ('Lake in the hills', lambda s: fractal(s, 3.0) * 0.7 - 0.6 * bump(x, y, 0.5, 0.52, 0.16), 16),
    ('Archipelago', lambda s: fractal(s, 3.4), 10),
    ('Atoll', lambda s: np.clip(1 - np.abs(R() - 0.33) / 0.08, 0, 1) * 0.8 + fractal(s, 2.6) * 0.3, 8),
    ('Fjord coast', lambda s: x * 0.9 + fractal(s, 3.4) * 0.6 - 0.5 * np.exp(-((y - 0.45 - 0.1 * np.sin(x * 9)) ** 2) / 0.003) * (x > 0.3), 18),
    ('Peninsula', lambda s: (1 - np.clip(np.abs(y - 0.5 - 0.08 * np.sin(x * 6)) / 0.25, 0, 1)) / (1 + np.exp(-(x - 0.25) * 18)) * 0.9 + x * 0.25 + fractal(s, 3.4) * 0.35, 12),
    ('Headlands and coves', lambda s: x + 0.25 * np.sin(y * 18) * fractal(s, 3.2) + fractal(s + 1, 2.8) * 0.4, 16),
    ('Basin', lambda s: R() * 1.4 + fractal(s, 3.0) * 0.4, 16),
    ('Ridge and lake', lambda s: fractal(s, 3.0) * 0.5 + np.exp(-((x - 0.3) ** 2) / 0.02) - 0.5 * bump(x, y, 0.7, 0.55, 0.12), 16),
    ('Hilltop fort earthworks', lambda s: bump(x, y, 0.5, 0.5, 0.24) + 0.08 * np.cos(R() * 60) * (R() < 0.3) + fractal(s, 3.4) * 0.15, 18),
    ('Meandering river', lambda s: fractal(s, 3.8) * 0.5 + y * 0.25 - 0.45 * np.exp(-((y - 0.5 - 0.22 * np.sin(x * 9) * np.cos(x * 2)) ** 2) / 0.0025), 14),
    ('Glacier cirque', lambda s: 1 - np.clip(R(0.5, 0.95) / 0.75, 0, 1) ** 0.6 + fractal(s, 2.8) * 0.2 + y * 0.2, 18),
    ('Escarpment', lambda s: 1 / (1 + np.exp(-(x - 0.5 - 0.1 * np.sin(y * 6)) * 25)) + fractal(s, 2.8) * 0.3, 16),
    ('Karst hills', lambda s: sum(bump(x, y, cx, cy, 0.05, 1) for cx, cy in np.random.default_rng(s).uniform(0.1, 0.9, (22, 2))) + fractal(s, 3.0) * 0.2, 12),
    ('Spur and gullies', lambda s: (1 - y) * 0.8 + 0.15 * np.sin(x * 25 + fractal(s, 3.0) * 4) * y + fractal(s + 3, 3.0) * 0.2, 18),
    ('Caldera', lambda s: np.clip(1 - np.abs(R() - 0.28) / 0.22, 0, 1) ** 1.1 + bump(x, y, 0.52, 0.5, 0.05, 0.5) + fractal(s, 2.8) * 0.12, 18),
    ('Highland moor', lambda s: fractal(s, 4.0) + fractal(s + 7, 3.0) * 0.08, 14),
    ('Volcanic island', lambda s: np.clip(1 - R() / 0.42, 0, 1) ** 1.4 + bump(x, y, 0.5, 0.5, 0.04, -0.25) + fractal(s, 3.4) * 0.12, 16),
    ('Mountain tarn', lambda s: fractal(s, 3.6) * 0.5 + bump(x, y, 0.45, 0.5, 0.3, 0.9) - 0.5 * bump(x, y, 0.5, 0.45, 0.06), 18),
    ('Two valleys', lambda s: fractal(s, 3.7) * 0.6 - 0.5 * np.exp(-((y - 0.3 - 0.08 * np.sin(x * 7)) ** 2) / 0.004) - 0.5 * np.exp(-((y - 0.72 + 0.08 * np.sin(x * 5)) ** 2) / 0.004), 16),
    ('Ice cap', lambda s: np.clip(1 - R() / 0.48, 0, 1) ** 0.5 + fractal(s, 3.9) * 0.15, 14),
    ('Rift valley', lambda s: fractal(s, 3.7) * 0.4 + 1 / (1 + np.exp(-(np.abs(x - 0.5 - 0.05 * np.sin(y * 7)) - 0.14) * 40)), 16),
    ('Valley junction', lambda s: fractal(s, 3.0) * 0.6 - 0.6 * np.exp(-((y - 0.5) ** 2) / 0.006) * (x < 0.55) - 0.6 * np.exp(-((x - 0.55) ** 2) / 0.006) - 0.6 * np.exp(-((y - x + 0.05) ** 2) / 0.006) * (x > 0.55), 16),
]
for i, (nm, fz, lv) in enumerate(specials):
    s = 101 + i
    z = warp(fz(s), s, 0.035)
    lo = float(np.percentile(z, 45)) if nm in ('Archipelago', 'Atoll') else None
    add(nm, map_lines(z, lv, 5 if lv >= 14 else 4, lo=lo, frame=i % 3 == 1, shape='circle' if i % 5 == 4 else 'square', sigma=2.5), f'land-{i + 1}')

save(items, OUT)
print(len(items), 'maps')
if SHEET:
    for i in range(0, len(items), 56):
        sheet(items[i:i + 56], SHEET.replace('.png', f'_{i // 56}.png'), cols=8)
