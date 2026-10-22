"""Cars: the shared drawing engine for gen_cars.py — a rounded-path primitive, wheels, and a parametric
side-profile builder. Internally z points UP (x forward, front of the car at +x, ground at z = 0, front
axle at x = 0, rear axle at x = -WB); `flip()` turns the result into the library's y-down lines."""
import math, sys, os
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, MultiLineString, box
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

# ---------------------------------------------------------------- rounded paths
def _edge_pts(a, b, bulge):
    if not bulge: return [a, b]
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
    if L < 1e-9: return [a, b]
    nx, ny = dy / L, -dx / L            # right of travel = outward for a counter-clockwise outline (z up)
    m = ((a[0] + b[0]) / 2 + nx * 2 * bulge, (a[1] + b[1]) / 2 + ny * 2 * bulge)
    return quad(a, m, b, n=max(6, min(36, int(L / 35))))

def _cum(P):
    c = [0.0]
    for i in range(1, len(P)): c.append(c[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    return c

def _pt(P, c, d):
    if d <= 0: return P[0]
    if d >= c[-1]: return P[-1]
    i = int(np.searchsorted(c, d)); i = max(1, min(len(P) - 1, i))
    seg = c[i] - c[i - 1]; t = (d - c[i - 1]) / seg if seg > 0 else 0
    return (P[i - 1][0] + (P[i][0] - P[i - 1][0]) * t, P[i - 1][1] + (P[i][1] - P[i - 1][1]) * t)

def _tan(P, c, d):
    i = int(np.searchsorted(c, d)); i = max(1, min(len(P) - 1, i))
    dx, dy = P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]; L = math.hypot(dx, dy) or 1
    return (dx / L, dy / L)

def _sub(P, c, d0, d1):
    out = [_pt(P, c, d0)]
    out += [P[k] for k in range(len(P)) if d0 + 1e-9 < c[k] < d1 - 1e-9]
    out.append(_pt(P, c, d1))
    return out

def _isect(p, t, q, u):
    """Point where the ray p + s t meets the ray q - w u (s, w > 0), or None."""
    det = t[0] * u[1] - t[1] * u[0]
    if abs(det) < 1e-6: return None
    dx, dy = q[0] - p[0], q[1] - p[1]
    s = (dx * u[1] - dy * u[0]) / det
    w = (t[0] * dy - t[1] * dx) / det
    span = math.hypot(dx, dy)
    if s <= 0 or w <= 0 or s > 4 * span + 1 or w > 4 * span + 1: return None
    return (p[0] + s * t[0], p[1] + s * t[1])

def rpath(nodes, closed=True):
    """A smooth outline through corner nodes. Each node is (x, y[, r[, bulge]]): r = how far the corner is
    rounded off along both edges; bulge = how far the edge to the next node bows outwards (right of travel)."""
    N = []
    for n in nodes:
        n = list(n) + [0.0] * (4 - len(n))
        N.append(tuple(float(v) for v in n[:4]))
    k = len(N); ne = k if closed else k - 1
    E = [_edge_pts(N[i][:2], N[(i + 1) % k][:2], N[i][3]) for i in range(ne)]
    C = [_cum(e) for e in E]
    st = [0.0] * ne; en = [0.0] * ne
    for j in range(k):
        r = N[j][2]
        if r <= 0 or (not closed and (j == 0 or j == k - 1)): continue
        en[(j - 1) % ne if closed else j - 1] = r; st[j % ne] = r
    for i in range(ne):
        L = C[i][-1]
        if st[i] + en[i] > 0.96 * L and st[i] + en[i] > 0:
            f = 0.96 * L / (st[i] + en[i]); st[i] *= f; en[i] *= f
    out = []
    for i in range(ne):
        seg = _sub(E[i], C[i], st[i], C[i][-1] - en[i])
        out += seg if not out else seg[1:]
        j = (i + 1) % k
        if (closed or i + 1 < k - 1) and N[j][2] > 0:
            nx_ = (i + 1) % ne
            p_in = seg[-1]; t_in = _tan(E[i], C[i], C[i][-1] - en[i] - 1e-6)
            p_out = _pt(E[nx_], C[nx_], st[nx_]); t_out = _tan(E[nx_], C[nx_], st[nx_] + 1e-6)
            ctrl = _isect(p_in, t_in, p_out, t_out) or N[j][:2]
            rr = max(en[i], st[nx_])
            out += quad(p_in, ctrl, p_out, n=max(4, min(18, int(rr / 14))))[1:]
    if closed:
        if math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) > 1e-6: out.append(out[0])
        else: out[-1] = out[0]
    return out

def rpoly(nodes):
    g = Polygon(rpath(nodes))
    return g if g.is_valid else g.buffer(0)

def biggest(g):
    if g.geom_type == 'MultiPolygon': return max(g.geoms, key=lambda q: q.area)
    if g.geom_type == 'GeometryCollection':
        P = [q for q in g.geoms if q.geom_type == 'Polygon']
        return max(P, key=lambda q: q.area) if P else Polygon()
    return g

def rounded(g, r):
    """Round the convex corners of a polygon (morphological opening)."""
    if r <= 0 or g.is_empty: return g
    h = g.buffer(-r, join_style=1, quad_segs=6).buffer(r, join_style=1, quad_segs=6)
    return h if not h.is_empty else g

def hp(a, b, side=1, big=1e5):
    """Half-plane to the left (side=1) or right (side=-1) of the line a→b (z up), as a big polygon."""
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    nx, ny = -uy * side, ux * side
    p0 = (a[0] - ux * big, a[1] - uy * big); p1 = (a[0] + ux * big, a[1] + uy * big)
    return Polygon([p0, p1, (p1[0] + nx * big, p1[1] + ny * big), (p0[0] + nx * big, p0[1] + ny * big)])

def flip(L):
    return [[(x, -z) for x, z in P] for P in L]

def clip(L, g):
    """Lines (list of polylines) clipped to the inside of g."""
    out = []
    for P in L:
        if len(P) < 2: continue
        out += lines_of(LineString(P).intersection(g))
    return [q for q in out if len(q) > 1]

def ext(P, d0, d1=None):
    """Polyline extended at its ends by d0 (start) and d1 (end)."""
    d1 = d0 if d1 is None else d1
    a, b = P[0], P[1]; L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    s = (a[0] - (b[0] - a[0]) / L * d0, a[1] - (b[1] - a[1]) / L * d0)
    a, b = P[-1], P[-2]; L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    e = (a[0] - (b[0] - a[0]) / L * d1, a[1] - (b[1] - a[1]) / L * d1)
    return [s] + list(P) + [e]

def ring(cx, cy, r, n=None):
    return Polygon(circle(cx, cy, r, n=n or max(36, int(r / 6))))

def ell(cx, cy, rx, ry, rot=0.0, n=None):
    return Polygon(ellipse(cx, cy, rx, ry, rot, n=n or max(36, int((rx + ry) / 8))))

def capsule(a, b, w):
    return LineString([a, b]).buffer(w / 2, cap_style=1, quad_segs=8)

# ---------------------------------------------------------------- wheels
def _window(cx, cz, r1, r2, a0, a1, w, rr):
    """Opening between two spokes: an annular sector from radius r1 to r2 between the angles a0..a1,
    with straight sides kept w/2 off the spoke centre lines, corners rounded by rr."""
    sect = Polygon([(cx, cz)] + [(cx + r2 * 1.2 * math.cos(a0 + (a1 - a0) * i / 24), cz + r2 * 1.2 * math.sin(a0 + (a1 - a0) * i / 24)) for i in range(25)])
    g = sect.intersection(ring(cx, cz, r2)).difference(ring(cx, cz, r1))
    for a in (a0, a1):
        g = g.difference(capsule((cx, cz), (cx + r2 * 1.3 * math.cos(a), cz + r2 * 1.3 * math.sin(a)), w))
    g = biggest(g)
    return rounded(g, rr)

def wheel(sc, cx, cz, R, rim=0.64, style='5', spin=0.0, hub=None, tread=0, lip=False, front=True, tyre=True, scale=None):
    """A wheel seen from the side: tyre (outer ring + rim edge) and a rim design.
    styles: '5','6','7' (n-spoke alloy), 'twin5' (split spokes), 'multi' (fine spokes), 'mesh',
    'steel' (pressed steel with holes), 'cap' (plain hubcap), 'wire', 'artillery' (wooden spokes),
    'dish' (deep dish), 'slot' (slotted), 'aero' (closed disc), 'turbine', 'lock' (centre-lock racing),
    'kart' (small solid), 'none'."""
    s = scale or R / 315.0                       # detail sizes follow the wheel size
    Rr = R * rim
    out = ring(cx, cz, R, n=max(48, int(R / 5)))
    if tread:
        # chunky off-road tread: blocks around the outside
        n = tread; pts = []
        for i in range(n * 8):
            a = spin + TAU * i / (n * 8)
            k = (i // 4) % 2
            rr = R if k == 0 else R - 22 * s
            pts.append((cx + rr * math.cos(a), cz + rr * math.sin(a)))
        out = Polygon(pts + [pts[0]])
    sc.shape(out if out.geom_type == 'Polygon' else biggest(out))
    if not tyre: return
    lines = [circle(cx, cz, Rr, n=max(36, int(Rr / 5)))]
    hub = hub if hub is not None else 0.2
    if style in ('5', '6', '7', '4', '8', '10'):
        n = int(style); r1 = Rr * (hub + 0.1); r2 = Rr * 0.86
        w = Rr * (0.24 if n <= 5 else 0.19 if n <= 7 else 0.14)
        for i in range(n):
            a0 = spin + TAU * i / n + math.pi / 2; a1 = a0 + TAU / n
            g = _window(cx, cz, r1, r2, a0, a1, w, Rr * 0.05)
            if not g.is_empty: lines += lines_of(g)
        lines.append(circle(cx, cz, Rr * hub))
    elif style == 'twin5':
        n = 10; r1 = Rr * (hub + 0.1); r2 = Rr * 0.86
        for i in range(5):
            a0 = spin + TAU * i / 5 + math.pi / 2
            g = _window(cx, cz, r1, r2, a0, a0 + TAU / 5, Rr * 0.3, Rr * 0.05)
            if not g.is_empty: lines += lines_of(g)
            lines.append([(cx + r1 * 0.9 * math.cos(a0), cz + r1 * 0.9 * math.sin(a0)), (cx + Rr * 0.97 * math.cos(a0), cz + Rr * 0.97 * math.sin(a0))])
        lines.append(circle(cx, cz, Rr * hub))
    elif style in ('multi', 'mesh'):
        n = 12 if style == 'multi' else 16
        r1 = Rr * (hub + 0.06)
        for i in range(n):
            a = spin + TAU * i / n
            lines.append([(cx + r1 * math.cos(a), cz + r1 * math.sin(a)), (cx + Rr * 0.94 * math.cos(a), cz + Rr * 0.94 * math.sin(a))])
        if style == 'mesh':
            lines.append(circle(cx, cz, Rr * 0.6))
        lines.append(circle(cx, cz, Rr * hub))
    elif style == 'steel':
        lines.append(circle(cx, cz, Rr * 0.82))
        for i in range(6):
            a = spin + TAU * i / 6
            lines.append(circle(cx + Rr * 0.6 * math.cos(a), cz + Rr * 0.6 * math.sin(a), Rr * 0.1, n=14))
        lines.append(circle(cx, cz, Rr * 0.34))
    elif style == 'cap':
        lines.append(circle(cx, cz, Rr * 0.8))
        lines.append(circle(cx, cz, Rr * 0.32))
    elif style == 'whitewall':
        lines.append(circle(cx, cz, R - (R - Rr) * 0.45))
        lines.append(circle(cx, cz, Rr * 0.72))
        lines.append(circle(cx, cz, Rr * 0.25))
    elif style == 'wire':
        r1 = Rr * 0.22
        lines.append(circle(cx, cz, Rr * 0.88))
        for i in range(16):
            a = spin + TAU * i / 16
            lines.append([(cx + r1 * math.cos(a), cz + r1 * math.sin(a)), (cx + Rr * 0.88 * math.cos(a + 0.18), cz + Rr * 0.88 * math.sin(a + 0.18))])
        lines.append(circle(cx, cz, r1))
        lines.append(regular(cx, cz, r1 * 0.6, 3, rot=spin))
    elif style == 'artillery':
        n = 10; r1 = Rr * 0.26
        for i in range(n):
            a = spin + TAU * i / n
            ca, sa = math.cos(a), math.sin(a); px, py = -sa, ca
            w0, w1 = Rr * 0.06, Rr * 0.045
            lines.append([(cx + r1 * ca + w0 * px, cz + r1 * sa + w0 * py), (cx + Rr * 0.97 * ca + w1 * px, cz + Rr * 0.97 * sa + w1 * py)])
            lines.append([(cx + r1 * ca - w0 * px, cz + r1 * sa - w0 * py), (cx + Rr * 0.97 * ca - w1 * px, cz + Rr * 0.97 * sa - w1 * py)])
        lines.append(circle(cx, cz, r1))
        lines.append(circle(cx, cz, r1 * 0.5))
    elif style == 'dish':
        lines.append(circle(cx, cz, Rr * 0.7))
        n = 5; r1 = Rr * 0.2; r2 = Rr * 0.62
        for i in range(n):
            a0 = spin + TAU * i / n + math.pi / 2
            g = _window(cx, cz, r1, r2, a0, a0 + TAU / n, Rr * 0.2, Rr * 0.04)
            if not g.is_empty: lines += lines_of(g)
        lines.append(circle(cx, cz, Rr * 0.12))
    elif style == 'slot':
        for i in range(5):
            a = spin + TAU * i / 5 + math.pi / 2
            lines += lines_of(capsule((cx + Rr * 0.38 * math.cos(a), cz + Rr * 0.38 * math.sin(a)), (cx + Rr * 0.72 * math.cos(a), cz + Rr * 0.72 * math.sin(a)), Rr * 0.2))
        lines.append(circle(cx, cz, Rr * 0.18))
    elif style == 'aero':
        lines.append(circle(cx, cz, Rr * 0.86))
        for i in range(5):
            a = spin + TAU * i / 5
            P = [(cx + r * math.cos(a + 0.9 * (r / Rr - 0.25)), cz + r * math.sin(a + 0.9 * (r / Rr - 0.25))) for r in np.linspace(Rr * 0.25, Rr * 0.8, 10)]
            lines.append(P)
        lines.append(circle(cx, cz, Rr * 0.2))
    elif style == 'turbine':
        n = 9; r1 = Rr * 0.22
        for i in range(n):
            a = spin + TAU * i / n
            P = [(cx + r * math.cos(a + 0.7 * (r - r1) / Rr), cz + r * math.sin(a + 0.7 * (r - r1) / Rr)) for r in np.linspace(r1, Rr * 0.92, 10)]
            lines.append(P)
        lines.append(circle(cx, cz, r1))
    elif style == 'lock':
        n = 6; r1 = Rr * 0.28; r2 = Rr * 0.86
        for i in range(n):
            a0 = spin + TAU * i / n + math.pi / 2
            g = _window(cx, cz, r1, r2, a0, a0 + TAU / n, Rr * 0.16, Rr * 0.04)
            if not g.is_empty: lines += lines_of(g)
        lines.append(regular(cx, cz, Rr * 0.15, 6, rot=spin))
    elif style == 'kart':
        lines.append(circle(cx, cz, Rr * 0.45))
    elif style == 'gt3':                          # flat 5-spoke race wheel with big centre nut
        n = 5; r1 = Rr * 0.3; r2 = Rr * 0.88
        for i in range(n):
            a0 = spin + TAU * i / n + math.pi / 2
            g = _window(cx, cz, r1, r2, a0, a0 + TAU / n, Rr * 0.3, Rr * 0.06)
            if not g.is_empty: lines += lines_of(g)
        lines.append(regular(cx, cz, Rr * 0.17, 6, rot=spin))
    if lip:
        lines.append(circle(cx, cz, Rr - max(40 * s, (R - Rr) * 0.3)))
    for P in lines: sc.line(P)

def tyre_only(sc, cx, cz, R, rim=0.6):
    sc.shape(ring(cx, cz, R)); sc.line(circle(cx, cz, R * rim))

def ztext(s, x, z, size, font='HersheySans1', align='center', spacing=0.0):
    """Text in z-up coordinates: (x, z) = baseline anchor, size = cap height."""
    return [[(px, -py) for px, py in P] for P in text(s, x, -z, size, font, align, spacing)]

def zbox(x0, z0, x1, z1, r=0.0):
    return Polygon(rect(min(x0, x1), min(z0, z1), abs(x1 - x0), abs(z1 - z0), r))
