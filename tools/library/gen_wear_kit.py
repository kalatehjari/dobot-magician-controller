"""Drawing kit for gen_wear (shoes and clothing): curves, parallel lines, clipping, dashes, hatching,
eyelets, and moving whole scenes (so pairs and outfits can overlap correctly)."""
import math, sys, os
import numpy as np
from shapely.geometry import Polygon, LineString, MultiLineString, Point, box, MultiPolygon
from shapely.ops import unary_union, linemerge
from shapely import affinity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


# ---------------------------------------------------------------- curves
def C(pts, n=10, t=0.5):
    """Open smooth curve through the points."""
    return spline(pts, closed=False, n=n, tension=t)


def CC(pts, n=10, t=0.5):
    """Closed smooth curve through the points."""
    return spline(pts, closed=True, n=n, tension=t)


def J(*parts):
    """Joins point lists end to end (a repeated joint point is dropped)."""
    out = []
    for p in parts:
        p = list(p)
        if out and p and math.dist(out[-1], p[0]) < 1e-6: p = p[1:]
        out += p
    return out


def close(pts):
    pts = list(pts)
    return pts + [pts[0]] if math.dist(pts[0], pts[-1]) > 1e-6 else pts


def G(pts, holes=()):
    """Polygon from points (repaired if needed)."""
    g = Polygon(pts, [h for h in holes])
    if not g.is_valid: g = g.buffer(0)
    return g


def length(P):
    return sum(math.dist(P[i], P[i + 1]) for i in range(len(P) - 1))


def at(P, s):
    """Point and unit tangent at arc-length fraction s of polyline P."""
    tot = length(P); goal = max(0.0, min(1.0, s)) * tot; acc = 0.0
    for i in range(len(P) - 1):
        d = math.dist(P[i], P[i + 1])
        if acc + d >= goal or i == len(P) - 2:
            u = 0 if d == 0 else (goal - acc) / d
            x = P[i][0] + (P[i + 1][0] - P[i][0]) * u; y = P[i][1] + (P[i + 1][1] - P[i][1]) * u
            tx_, ty_ = (P[i + 1][0] - P[i][0]) / (d or 1), (P[i + 1][1] - P[i][1]) / (d or 1)
            return (x, y), (tx_, ty_)
        acc += d
    return P[-1], (1, 0)


def sub(P, s0, s1, n=None):
    """Part of the polyline between arc-length fractions s0 and s1."""
    ls = LineString(P); tot = ls.length
    a, b = sorted((s0, s1))
    from shapely.ops import substring
    g = substring(ls, a * tot, b * tot)
    out = list(g.coords) if g.geom_type == 'LineString' else [g.coords[0]]
    return out if s0 <= s1 else out[::-1]


def resample(P, step):
    tot = length(P); n = max(2, int(round(tot / step)))
    return [at(P, i / n)[0] for i in range(n + 1)]


def par(P, d):
    """Parallel curve at distance d: positive = to the left of the direction of travel."""
    if abs(d) < 1e-9: return list(P)
    g = LineString(P).offset_curve(d, quad_segs=8, join_style=1)
    L = lines_of(g)
    if not L: return []
    return max(L, key=lambda q: LineString(q).length)


def normal(t):
    return (-t[1], t[0])


# ---------------------------------------------------------------- clipping
def clip(lines, g, inset=0.0):
    """Parts of the lines inside polygon g (shrunk by inset)."""
    gg = g.buffer(-inset, join_style=1) if inset else g
    out = []
    for P in lines:
        if len(P) > 1: out += lines_of(LineString(P).intersection(gg))
    return [q for q in out if LineString(q).length > 1e-6]


def outside(lines, g):
    out = []
    for P in lines:
        if len(P) > 1: out += lines_of(LineString(P).difference(g))
    return [q for q in out if LineString(q).length > 1e-6]


def dashes(P, dash=14.0, gap=10.0, phase=0.0):
    """A dashed version of the polyline (stitching)."""
    ls = LineString(P); tot = ls.length; out = []
    from shapely.ops import substring
    s = phase
    while s < tot - 2:
        e = min(tot, s + dash)
        if e - s > dash * 0.45:
            g = substring(ls, s, e); out.append(list(g.coords))
        s += dash + gap
    return out


def ticks(P, step, d0, d1, s0=0.0, s1=1.0, slant=0.0):
    """Short strokes across a curve, from offset d0 to d1 (positive = left of travel), every `step` units."""
    tot = length(P) * (s1 - s0); n = max(1, int(tot / step))
    out = []
    for i in range(n + 1):
        s = s0 + (s1 - s0) * (i + 0.5) / (n + 1)
        (x, y), t = at(P, s); nx, ny = normal(t)
        out.append([(x + nx * d0 + t[0] * slant * d0, y + ny * d0 + t[1] * slant * d0), (x + nx * d1 + t[0] * slant * d1, y + ny * d1 + t[1] * slant * d1)])
    return out


def hatch(g, step, ang_deg=45.0, offset=0.0):
    """Parallel lines filling polygon g, `step` apart (for dark panels)."""
    if g.is_empty: return []
    a = math.radians(ang_deg); c, s = math.cos(a), math.sin(a)
    x0, y0, x1, y1 = g.bounds; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; R = math.hypot(x1 - x0, y1 - y0)
    out = []
    k = -R + offset % step
    while k <= R:
        p = (cx - s * k, cy + c * k)
        seg = [(p[0] - c * R, p[1] - s * R), (p[0] + c * R, p[1] + s * R)]
        out += lines_of(LineString(seg).intersection(g))
        k += step
    return out


def dots_along(P, step, r, s0=0.0, s1=1.0, n=10):
    """Little circles along a curve (perforations, rivets, studs)."""
    tot = length(P) * (s1 - s0); m = max(1, int(tot / step))
    return [circle(*at(P, s0 + (s1 - s0) * i / m)[0], r, n=n) for i in range(m + 1)]


# ---------------------------------------------------------------- scenes
def halo(sc, P, w=6.0):
    """A line that hides what is behind it within w units (a white gap either side)."""
    if len(P) < 2: return
    sc.cut(LineString(P).buffer(w, cap_style=1))
    sc.line(P)


def ring(sc, cx, cy, r, w=None, n=None):
    """A small circle that hides what is behind it (an eyelet, a button)."""
    sc.shape(circle(cx, cy, r, n=n or max(12, int(r * 1.6) + 8)))


def _map(sc, f):
    out = Scene()
    for kind, g, fill, outline in sc.items:
        out.items.append((kind, f(g), fill, outline))
    return out


def s_flip(sc):
    """y -> -y (draw in y-up, store in y-down)."""
    return _map(sc, lambda g: affinity.scale(g, 1, -1, origin=(0, 0)))


def s_mirror(sc, ox=0.0):
    return _map(sc, lambda g: affinity.scale(g, -1, 1, origin=(ox, 0)))


def s_move(sc, dx=0.0, dy=0.0):
    return _map(sc, lambda g: affinity.translate(g, dx, dy))


def s_scale(sc, s, sy=None, origin=(0, 0)):
    return _map(sc, lambda g: affinity.scale(g, s, s if sy is None else sy, origin=origin))


def s_rot(sc, deg, origin=(0, 0)):
    return _map(sc, lambda g: affinity.rotate(g, deg, origin=origin))


def s_join(*scs):
    """One scene from several (the first is at the back)."""
    out = Scene()
    for s in scs: out.items += s.items
    return out


def s_bounds(sc):
    gs = [g for _, g, _, _ in sc.items]
    return unary_union([g if g.geom_type != 'LineString' else g.buffer(0.01) for g in gs]).bounds


def fit(L, size=1000.0):
    """Lines moved and scaled so the longest side is `size`, top-left at (0, 0)."""
    x0, y0, x1, y1 = bbox(L); k = size / max(x1 - x0, y1 - y0, 1e-9)
    return [[((x - x0) * k, (y - y0) * k) for x, y in P] for P in L]


def finish(L, min_len=4.0):
    """Drops degenerate bits, rounds a little, removes repeated points."""
    out = []
    for P in L:
        Q = [P[0]]
        for p in P[1:]:
            if math.dist(p, Q[-1]) > 1e-3: Q.append(p)
        if len(Q) > 1 and length(Q) >= min_len: out.append([(float(x), float(y)) for x, y in Q])
    return out


def mirror_half(half, cx=0.0):
    """A symmetric closed outline from its right half (from the top centre round to the bottom centre)."""
    left = [(2 * cx - x, y) for x, y in reversed(half)]
    pts = J(half, left)
    return close(pts)


def sym(L, cx=0.0):
    """Lines plus their mirror images about x = cx."""
    return list(L) + [[(2 * cx - x, y) for x, y in P] for P in L]
