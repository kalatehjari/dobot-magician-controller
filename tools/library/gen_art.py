"""Art: geometric and generative line art — spirographs, roses, Lissajous figures, harmonographs, string
art, mandalas, space-filling curves, fractals, mazes, flow fields, op art, guilloché rosettes and more.
Usage: python3 -I gen_art.py <out.json> [sheet.png]"""
import math, sys, random, os
import numpy as np
from shapely.geometry import LineString, Polygon, Point, box as sbox
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

OUT = sys.argv[1]
SHEET = sys.argv[2] if len(sys.argv) > 2 else None
items = []
def add(name, L, slug):
    L = [P for P in L if len(P) > 1]
    it = Item('art', name, L, author='Made for this library', source='generated', license='public domain'); it.slug = slug; items.append(it)

def polar(f, t0, t1, n): return [(f(t)[0], f(t)[1]) for t in np.linspace(t0, t1, n)]

# ---------------- spirographs
def trochoid(R, r, d, epi=False, n=None):
    g = math.gcd(int(R), int(r)); turns = int(r) // g
    n = n or 380 * turns
    out = []
    for t in np.linspace(0, 2 * math.pi * turns, n + 1):
        if epi: x = (R + r) * math.cos(t) - d * math.cos((R + r) / r * t); y = (R + r) * math.sin(t) - d * math.sin((R + r) / r * t)
        else: x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t); y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
        out.append((x, y))
    return [out]
for i, (R, r, d, epi) in enumerate([(96, 36, 52, False), (105, 63, 60, False), (120, 45, 70, False), (90, 25, 40, False), (100, 35, 60, False),
                                    (80, 48, 40, True), (60, 25, 45, True), (110, 30, 30, False), (96, 45, 80, False), (84, 32, 18, True)]):
    add(f'Spirograph {i + 1}', trochoid(R, r, d, epi), f'spirograph-{i + 1}')
# ---------------- roses
for i, (p, q) in enumerate([(5, 1), (7, 3), (6, 1), (4, 9)]):
    k = p / q; T = math.pi * (q if (p * q) % 2 else 2 * q)
    add(f'Rose curve {p}/{q}' if q > 1 else f'Rose with {p if p % 2 else 2 * p} petals', [polar(lambda t: (math.cos(k * t) * math.cos(t), math.cos(k * t) * math.sin(t)), 0, T, 1600)], f'rose-{i + 1}')
# ---------------- Lissajous
for i, (a, b, ph) in enumerate([(3, 2, math.pi / 2), (5, 4, math.pi / 4), (7, 6, math.pi / 3), (9, 8, math.pi / 2), (5, 3, 0.3)]):
    add(f'Lissajous {a}:{b}', [[(math.sin(a * t + ph), math.sin(b * t)) for t in np.linspace(0, 2 * math.pi, 2400)]], f'lissajous-{i + 1}')
# ---------------- harmonographs
for i in range(5):
    rg = np.random.default_rng(300 + i)
    f = [2 + rg.integers(0, 2) + rg.uniform(-0.012, 0.012) for _ in range(4)]
    p = rg.uniform(0, math.pi, 4); dmp = rg.uniform(0.002, 0.006, 4)
    t = np.linspace(0, 70, 4200); dmp = dmp * 2.2
    x = np.sin(f[0] * t + p[0]) * np.exp(-dmp[0] * t) + np.sin(f[1] * t + p[1]) * np.exp(-dmp[1] * t)
    y = np.sin(f[2] * t + p[2]) * np.exp(-dmp[2] * t) + np.sin(f[3] * t + p[3]) * np.exp(-dmp[3] * t)
    add(f'Harmonograph {i + 1}', [list(zip(x.tolist(), y.tolist()))], f'harmonograph-{i + 1}')
# ---------------- string art
def chords(n, mult, r=500):
    pts = [(r * math.cos(2 * math.pi * k / n - math.pi / 2), r * math.sin(2 * math.pi * k / n - math.pi / 2)) for k in range(n)]
    L = [circle(0, 0, r, n=240)]
    for k in range(n): L.append([pts[k], pts[(k * mult) % n]])
    return L
add('Cardioid string art', chords(200, 2), 'string-cardioid')
add('Nephroid string art', chords(200, 3), 'string-nephroid')
add('Times table 7', chords(160, 7), 'string-7')
def string_corner(n=28):
    L = []
    for k in range(n + 1):
        t = k / n
        L.append([(0, 1000 * t), (1000 * t, 1000)]); L.append([(1000, 1000 * (1 - t)), (1000 * (1 - t), 0)])
    return L
add('String art curves', string_corner(), 'string-curves')
# ---------------- mandalas
def mandala(seed, petals):
    rg = random.Random(seed); L = []
    rings = sorted(rg.sample(range(80, 480, 20), 5))
    for r in rings: L.append(circle(0, 0, r, n=200))
    for j, r in enumerate(rings[:-1]):
        r2 = rings[j + 1]; n = petals * (1 + j % 2)
        kind = rg.choice(['petal', 'arch', 'teeth', 'dots'])
        for k in range(n):
            a = 2 * math.pi * k / n; c, s_ = math.cos(a), math.sin(a)
            if kind == 'petal':
                P = [(r + (r2 - r) * u, (r2 - r) * 0.35 * math.sin(math.pi * u) * sg) for sg in (1, -1) for u in (np.linspace(0, 1, 18) if sg > 0 else np.linspace(1, 0, 18))]
            elif kind == 'arch':
                w = math.pi * r / n * 0.9
                P = [(r + (r2 - r) * 0.9 * math.sin(u), w * math.cos(u)) for u in np.linspace(0, math.pi, 20)]
            elif kind == 'teeth':
                w = math.pi * r / n
                P = [(r, -w * 0.9), (r2 * 0.97, 0), (r, w * 0.9)]
            else:
                rr = (r2 - r) * 0.28; P = circle((r + r2) / 2, 0, rr, n=14)
            L.append([(x * c - y * s_, x * s_ + y * c) for x, y in P])
    L += [circle(0, 0, 30, n=40)]
    for k in range(petals):
        a = 2 * math.pi * (k + 0.5) / petals
        L.append([(30 * math.cos(a), 30 * math.sin(a)), (rings[0] * math.cos(a), rings[0] * math.sin(a))])
    return L
for i, (sd, pt) in enumerate([(1, 12), (2, 16), (3, 10), (4, 20)]):
    add(f'Mandala {i + 1}', mandala(sd, pt), f'mandala-{i + 1}')
# ---------------- L-system curves and fractals
def lsys(axiom, rules, n, angle, start=0, draw='FG'):
    s = axiom
    for _ in range(n): s = ''.join(rules.get(c, c) for c in s)
    x = y = 0.0; a = math.radians(start); P = [(x, y)]; L = []; stack = []
    for c in s:
        if c in draw:
            x += math.cos(a); y += math.sin(a); P.append((x, y))
        elif c == 'f':
            x += math.cos(a); y += math.sin(a); L.append(P); P = [(x, y)]
        elif c == '+': a += math.radians(angle)
        elif c == '-': a -= math.radians(angle)
        elif c == '[': stack.append((x, y, a))
        elif c == ']':
            L.append(P); x, y, a = stack.pop(); P = [(x, y)]
    L.append(P)
    return [Q for Q in L if len(Q) > 1]
add('Hilbert curve', lsys('A', {'A': '+BF-AFA-FB+', 'B': '-AF+BFB+FA-'}, 5, 90), 'hilbert')
add('Dragon curve', lsys('FX', {'X': 'X+YF+', 'Y': '-FX-Y'}, 12, 90), 'dragon')
add('Koch snowflake', lsys('F--F--F', {'F': 'F+F--F+F'}, 4, 60), 'koch')
add('Sierpinski arrowhead', lsys('A', {'A': 'B-A-B', 'B': 'A+B+A'}, 7, 60, draw='AB'), 'sierpinski')
add('Gosper curve', lsys('A', {'A': 'A-B--B+A++AA+B-', 'B': '+A-BB--B-A++A+B'}, 4, 60, draw='AB'), 'gosper')
add('Lévy C curve', lsys('F', {'F': '+F--F+'}, 12, 45), 'levy')
add('Moore curve', lsys('LFL+F+LFL', {'L': '-RF+LFL+FR-', 'R': '+LF-RFR-FL+'}, 4, 90), 'moore')
add('Quadratic Koch island', lsys('F+F+F+F', {'F': 'F+F-F-FF+F+F-F'}, 2, 90), 'koch-island')
add('Fractal tree', lsys('X', {'X': 'F[+X][-X]FX', 'F': 'FF'}, 6, 25.7, start=-90), 'fractal-tree')
add('Fractal plant', lsys('X', {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'}, 5, 22.5, start=-75), 'fractal-plant')
add('Pentaplexity', lsys('F++F++F++F++F', {'F': 'F++F++F+++++F-F++F'}, 3, 36), 'pentaplexity')
# ---------------- mazes
def maze(w, h, seed, cell=40):
    rg = random.Random(seed); seen = [[False] * h for _ in range(w)]; walls = set()
    for x in range(w):
        for y in range(h): walls |= {('h', x, y), ('v', x, y)}
    stack = [(0, 0)]; seen[0][0] = True
    while stack:
        x, y = stack[-1]
        nb = [(x + dx, y + dy, dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= x + dx < w and 0 <= y + dy < h and not seen[x + dx][y + dy]]
        if not nb: stack.pop(); continue
        nx, ny, dx, dy = rg.choice(nb)
        if dx == 1: walls.discard(('v', x + 1, y))
        elif dx == -1: walls.discard(('v', x, y))
        elif dy == 1: walls.discard(('h', x, y + 1))
        else: walls.discard(('h', x, y))
        seen[nx][ny] = True; stack.append((nx, ny))
    L = []
    for kind, x, y in walls:
        if kind == 'h' and not (y == 0 and x == 0): L.append([(x * cell, y * cell), ((x + 1) * cell, y * cell)])
        if kind == 'v' and not (x == 0 and y == 0): L.append([(x * cell, y * cell), (x * cell, (y + 1) * cell)])
    L.append([(0, h * cell), ((w - 1) * cell, h * cell)])          # bottom edge, with the exit at the right
    L.append([(w * cell, 0), (w * cell, h * cell)])
    return merge_lines(L)
add('Maze', maze(20, 20, 7), 'maze-square')
add('Small maze', maze(12, 12, 11), 'maze-small')
def circular_maze(rings=9, seed=5):
    rg = random.Random(seed); L = []
    cells = []                                              # (ring, index) with count per ring
    counts = [1] + [6 * 2 ** min(3, int(math.log2(r + 1))) for r in range(1, rings + 1)]
    seen = {(0, 0)}; stack = [(0, 0)]; open_ = set()
    def nbrs(r, i):
        out = []
        n = counts[r]
        if r > 0:
            out += [(r, (i + 1) % n), (r, (i - 1) % n)]
            pn = counts[r - 1]; out.append((r - 1, i * pn // n))
        if r < rings:
            nn = counts[r + 1]; k = nn // n if r > 0 else nn
            base = i * nn // n if r > 0 else 0
            out += [(r + 1, (base + j) % nn) for j in range(k)]
        return out
    while stack:
        c = stack[-1]
        nb = [q for q in nbrs(*c) if q not in seen]
        if not nb: stack.pop(); continue
        q = rg.choice(nb); seen.add(q); open_.add(frozenset((c, q))); stack.append(q)
    R0 = 46
    for r in range(1, rings + 1):
        n = counts[r]; rad = R0 * r
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            inner = (r - 1, i * counts[r - 1] // n) if r > 1 else (0, 0)
            if frozenset(((r, i), inner)) not in open_: L.append(arc(0, 0, rad, a0, a1, n=max(3, int(12 * (a1 - a0) * r / 3))))
            if frozenset(((r, i), (r, (i - 1) % n))) not in open_: L.append([(rad * math.cos(a0), rad * math.sin(a0)), ((rad + R0) * math.cos(a0), (rad + R0) * math.sin(a0))])
    L.append(arc(0, 0, R0 * (rings + 1), 0.15, 2 * math.pi, n=300))
    return merge_lines(L)
add('Round maze', circular_maze(), 'maze-round')
# ---------------- Truchet tiles
def truchet(n, seed, kind='arc'):
    rg = random.Random(seed); s = 1000 / n; L = []
    for i in range(n):
        for j in range(n):
            x, y = i * s, j * s; flip = rg.random() < 0.5
            if kind == 'arc':
                if flip: L += [arc(x, y, s / 2, 0, math.pi / 2, n=10), arc(x + s, y + s, s / 2, math.pi, 1.5 * math.pi, n=10)]
                else: L += [arc(x + s, y, s / 2, math.pi / 2, math.pi, n=10), arc(x, y + s, s / 2, 1.5 * math.pi, 2 * math.pi, n=10)]
            else:
                L.append([(x, y), (x + s, y + s)] if flip else [(x + s, y), (x, y + s)])
    return merge_lines(L)
add('Truchet tiles', truchet(14, 3), 'truchet')
add('Ten-print maze', truchet(20, 9, 'line'), 'ten-print')
# ---------------- flow fields
def flow(seed, n_lines=150, steps=110):
    """Streamlines of a swirling, divergence-free flow (curl of smooth noise), so lines never bunch up."""
    rg = np.random.default_rng(seed); M = 96
    k = np.sqrt(np.add.outer(np.fft.fftfreq(M) ** 2, np.fft.fftfreq(M) ** 2)); k[0, 0] = 1
    psi = np.real(np.fft.ifft2((rg.normal(size=(M, M)) + 1j * rg.normal(size=(M, M))) / k ** 2.2))
    gy, gx = np.gradient(psi)
    vx, vy = gy, -gx
    mag = np.sqrt(vx * vx + vy * vy) + 1e-12
    L = []; occ = np.zeros((100, 100), dtype=bool)
    for _ in range(n_lines * 4):
        if len(L) >= n_lines: break
        x, y = rg.uniform(20, 980, 2)
        if occ[int(y / 10), int(x / 10)]: continue
        P = [(x, y)]; cells = set()
        for _ in range(steps):
            i, j = int(y / 1000 * (M - 1)), int(x / 1000 * (M - 1))
            x += 6 * vx[i, j] / mag[i, j]; y += 6 * vy[i, j] / mag[i, j]
            if not (0 <= x < 1000 and 0 <= y < 1000): break
            c = (int(y / 10), int(x / 10))
            if occ[c] and c not in cells: break
            cells.add(c); P.append((x, y))
        if len(P) > 12:
            L.append(P)
            for c in cells: occ[c] = True
    return L
for i in range(3): add(f'Flow field {i + 1}', flow(40 + i), f'flow-{i + 1}')
# ---------------- op art and moiré
def wave_lines(n=46, amp=60):
    L = []
    for k in range(n + 1):
        y0 = k * 1000 / n
        L.append([(x, y0 + amp * math.exp(-((x - 500) ** 2 + (y0 - 500) ** 2) / 60000) * math.sin(x / 28)) for x in np.linspace(0, 1000, 160)])
    return L
add('Op art waves', wave_lines(), 'op-waves')
def bulge(n=40):
    L = []
    for k in range(n + 1):
        t = k / n * 2 - 1
        L.append([(500 + 500 * u, 500 + 500 * t * (1 - 0.35 * math.exp(-(u * u + t * t) * 2.2))) for u in np.linspace(-1, 1, 120)])
        L.append([(500 + 500 * t * (1 - 0.35 * math.exp(-(u * u + t * t) * 2.2)), 500 + 500 * u) for u in np.linspace(-1, 1, 120)])
    return L
add('Bulging grid', bulge(), 'op-bulge')
add('Moiré circles', [circle(400, 500, r, n=120) for r in range(20, 400, 14)] + [circle(600, 500, r, n=120) for r in range(20, 400, 14)], 'moire')
def square_spiral(n=60):
    L = []; s = 1000
    for k in range(n):
        a = math.radians(k * 4.5); h = s / 2 * (0.955 ** k)
        L.append([(h * math.cos(a + math.pi / 4 + q * math.pi / 2) * math.sqrt(2), h * math.sin(a + math.pi / 4 + q * math.pi / 2) * math.sqrt(2)) for q in range(5)])
    return L
add('Twisting squares', square_spiral(), 'twisting-squares')
# ---------------- guilloché rosettes
for i, (a, b, c, k) in enumerate([(1, 0.18, 0.06, 12), (1, 0.12, 0.1, 9), (1, 0.22, 0.04, 16)]):
    L = []
    nst = 6 if i != 1 else 8
    for j in range(nst):
        ph = 2 * math.pi * j / nst / k
        L.append([((a + b * math.sin(k * t + ph * k) + c * math.sin(3 * k * t)) * math.cos(t), (a + b * math.sin(k * t + ph * k) + c * math.sin(3 * k * t)) * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 700)])
    add(f'Guilloché rosette {i + 1}', L, f'guilloche-{i + 1}')
# ---------------- spirals
add('Archimedean spiral', [[(t * math.cos(t), t * math.sin(t)) for t in np.linspace(0, 30 * math.pi, 3000)]], 'spiral-archimedean')
add('Golden spiral', [[(math.exp(0.3063 * t) * math.cos(t), math.exp(0.3063 * t) * math.sin(t)) for t in np.linspace(0, 6 * math.pi, 900)]] +
    [[(math.exp(0.3063 * t) * math.cos(t + math.pi), math.exp(0.3063 * t) * math.sin(t + math.pi)) for t in np.linspace(0, 6 * math.pi, 900)]], 'spiral-golden')
add('Sunflower seeds', [circle(math.sqrt(k) * 30 * math.cos(k * 2.39996), math.sqrt(k) * 30 * math.sin(k * 2.39996), 4 + math.sqrt(k) * 0.55, n=10) for k in range(1, 300)], 'phyllotaxis')
# ---------------- circle packing, Voronoi, isometric cubes, star tiling, interference
def packing(seed, n=260):
    rg = random.Random(seed); C = []
    for _ in range(6000):
        x, y = rg.uniform(0, 1000), rg.uniform(0, 1000)
        r = min([x, y, 1000 - x, 1000 - y] + [math.hypot(x - cx, y - cy) - cr - 4 for cx, cy, cr in C])
        if r > 6: C.append((x, y, min(r, 160)))
        if len(C) >= n: break
    return [circle(x, y, r, n=max(12, int(r * 0.8))) for x, y, r in C]
add('Circle packing', packing(2), 'circle-packing')
def voronoi(seed, n=60):
    from scipy.spatial import Voronoi
    rg = np.random.default_rng(seed); P = rg.uniform(0, 1000, (n, 2))
    V = Voronoi(np.vstack([P, [[-3000, -3000], [4000, -3000], [-3000, 4000], [4000, 4000]]]))
    clip = sbox(0, 0, 1000, 1000); L = []
    for reg in V.regions:
        if not reg or -1 in reg: continue
        poly = Polygon([V.vertices[i] for i in reg]).intersection(clip)
        if not poly.is_empty: L += lines_of(poly.buffer(-7))
    return L
add('Voronoi cells', voronoi(4), 'voronoi')
def cubes(n=7):
    L = []; s = 1000 / n; h = s * math.sqrt(3) / 2
    for i in range(-1, n + 2):
        for j in range(-1, int(n * 1.2) + 2):
            cx = i * 2 * h + (j % 2) * h; cy = j * 1.5 * s
            top = [(cx, cy - s), (cx + h, cy - s / 2), (cx, cy), (cx - h, cy - s / 2), (cx, cy - s)]
            L += [top, [(cx - h, cy - s / 2), (cx - h, cy + s / 2), (cx, cy + s), (cx + h, cy + s / 2), (cx + h, cy - s / 2)], [(cx, cy), (cx, cy + s)]]
    clip = sbox(0, 0, 1000, 1000)
    return [Q for P in L for Q in lines_of(LineString(P).intersection(clip))]
add('Tumbling blocks', cubes(), 'tumbling-blocks')
def star_tiling(n=4):
    L = []; s = 1000 / n
    for i in range(n):
        for j in range(n):
            cx, cy = (i + 0.5) * s, (j + 0.5) * s
            L.append(star(cx, cy, s * 0.5, s * 0.5 * 0.6, 8, rot=math.pi / 8))
            L.append(rect(i * s, j * s, s, s))
            L.append(regular(cx, cy, s * 0.21, 8, rot=math.pi / 8))
    return L
add('Eight-point star tiles', star_tiling(), 'star-tiles')
def interference():
    L = []
    for k in range(1, 26):
        r = k * 38
        L.append(arc(300, 1000, r, math.pi, 2 * math.pi, n=120)); L.append(arc(700, 1000, r, math.pi, 2 * math.pi, n=120))
    clip = sbox(0, 0, 1000, 1000)
    return [Q for P in L for Q in lines_of(LineString(P).intersection(clip))]
add('Ripples meeting', interference(), 'ripples')

save(items, OUT)
print(len(items), 'art pieces')
if SHEET:
    for i in range(0, len(items), 64):
        sheet(items[i:i + 64], SHEET.replace('.png', f'_{i // 64}.png'), cols=8)
