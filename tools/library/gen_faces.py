"""Faces: line-art head-and-shoulders portraits of fictional people (front views and profiles), with
varied ages, hairstyles, facial hair, accessories and expressions. Drawn y-up (eyes at y = 0, chin near
y = -300), flipped at the end. Usage: python3 -I gen_faces.py <out.json> [sheet.png]"""
import math, sys, random, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from shapely.geometry import Polygon, LineString, Point, box, MultiPolygon
from shapely.ops import unary_union

def flipL(L): return [[(x, -y) for x, y in P] for P in L]
def P_(pts): return Polygon(pts).buffer(0)
def sym_closed(half):
    """Closed outline from the right half (top centre to bottom centre)."""
    return half + [(-x, y) for x, y in half[::-1][1:]]
def clipL(L, g):
    out = []
    for P in L:
        if len(P) > 1: out += lines_of(LineString(P).intersection(g))
    return out
def lerp_curve(A, B, t):
    n = min(len(A), len(B))
    A = resample_n(A, n); B = resample_n(B, n)
    return [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(A, B)]
def resample_n(P, n):
    L = LineString(P); return [tuple(L.interpolate(L.length * i / (n - 1)).coords[0]) for i in range(n)]

# ================================================================ front view
def face_outline(kind='f', jaw=1.0, chin=1.0, length=1.0):
    if kind in ('c', 'b'):
        half = [(0, 280), (165, 262), (228, 160), (242, 30), (232, -90), (190, -195), (110, -258), (0, -275)]
    else:
        half = [(0, 300), (150, 286), (214, 205), (230, 85), (228, -20), (214, -110), (190 * jaw, -195), (128 * jaw, -255), (60 * chin, -296 * length), (0, -306 * length)]
    pts = spline(half, n=8, tension=0.45)
    return sym_closed(pts)

def eye(sc, cx, cy, s=1.0, side=1, wink=False, look=(0, 0), lashes=False, age=0.0, child=False):
    w = 46 * s; h = 20 * s * (1.25 if child else 1.0)
    inner = (cx - side * w, cy - 2); outer = (cx + side * w, cy + 4)
    if wink:
        sc.line(spline([inner, (cx, cy - h * 0.6), outer], n=8))
        sc.line(spline([(cx - side * w * 0.8, cy + h * 0.6), (cx, cy + h * 1.0), (cx + side * w * 0.9, cy + h * 0.7)], n=6))
        return
    up = spline([inner, (cx - side * w * 0.45, cy + h * 1.05), (cx + side * w * 0.35, cy + h * 1.1), outer], n=10)
    lo = spline([outer, (cx + side * w * 0.4, cy - h * 0.7), (cx - side * w * 0.4, cy - h * 0.75), inner], n=10)
    shape = P_(up + lo[1:])
    ir = 20 * s * (1.25 if child else 1.0)
    ic = (cx + look[0] * 10 * s, cy + 2 + look[1] * 6 * s)
    iris = Polygon(circle(ic[0], ic[1], ir, 30)).intersection(shape)
    sc.shape(shape, fill=True)
    sc.lines(lines_of(iris.boundary))
    pup = Polygon(circle(ic[0], ic[1], ir * 0.45, 20)).intersection(shape)
    if not pup.is_empty:
        sc.lines(lines_of(pup.boundary)); sc.lines(clipL([circle(ic[0], ic[1], ir * 0.22, 12)], shape))
    sc.line(up)
    sc.line(spline([(cx - side * w * 0.85, cy + h * 1.0), (cx - side * w * 0.2, cy + h * 1.85), (cx + side * w * 0.55, cy + h * 1.75), (cx + side * w * 1.02, cy + h * 0.9)], n=8))
    if lashes:
        for k in range(3):
            t = 0.62 + k * 0.14; p, _ = at_curve(up, t)
            sc.line([p, (p[0] + side * (8 + 4 * k) * s, p[1] + 10 * s)])
    if age > 0.4:
        for k in range(3): sc.line([(cx + side * (w + 8), cy + 4 - k * 9), (cx + side * (w + 26 + k * 3), cy + 10 - k * 13)])
        sc.line(spline([(cx - side * w * 0.6, cy - h * 1.3), (cx, cy - h * 1.7), (cx + side * w * 0.7, cy - h * 1.3)], n=6))

def at_curve(P, t):
    L = LineString(P); q = L.interpolate(L.length * t); return (q.x, q.y), None

def brow(sc, cx, cy, s=1.0, side=1, raise_=0.0, frown=0.0, thick=10, kind='arched'):
    a = (cx - side * 52 * s, cy - 4 + frown * 10)
    m = (cx + side * 4 * s, cy + 14 * s + raise_ * 18)
    b = (cx + side * 60 * s, cy - 2 * s + raise_ * 6)
    top = spline([a, m, b], n=10)
    bot = spline([(b[0] - side * 6, b[1] - thick * 0.25), (m[0], m[1] - thick), (a[0] + side * 4, a[1] - thick * 0.9)], n=10)
    sc.shape(P_(top + bot + [top[0]]))

def nose(sc, s=1.0, child=False, wide=1.0, bridge=True):
    k = 0.8 if child else 1.0
    y = -128 * k * s
    sc.line(spline([(-30 * wide * s, y + 6), (-44 * wide * s, y - 4), (-32 * wide * s, y - 18), (-12 * s, y - 12)], n=8))
    sc.line(spline([(30 * wide * s, y + 6), (44 * wide * s, y - 4), (32 * wide * s, y - 18), (12 * s, y - 12)], n=8))
    sc.line(spline([(-12 * s, y - 12), (0, y - 16), (12 * s, y - 12)], n=6))
    if bridge: sc.line(spline([(-22 * s, 30), (-20 * s, -40), (-28 * s, y + 20)], n=8))

def mouth(sc, kind='closed', s=1.0, w=70, y=-200, full=1.0, child=False):
    w = w * s * (0.8 if child else 1.0); y = y * (0.92 if child else 1.0)
    if kind == 'o':
        sc.shape(Polygon(ellipse(0, y - 4, 24 * s, 32 * s, 0, 30)))
        sc.line(ellipse(0, y - 4, 14 * s, 20 * s, 0, 20)); return
    if kind == 'laugh':
        top = spline([(-w, y + 6), (-w * 0.5, y + 2), (0, y + 4), (w * 0.5, y + 2), (w, y + 6)], n=10)
        bot = spline([(w, y + 6), (w * 0.6, y - 40 * s), (0, y - 56 * s), (-w * 0.6, y - 40 * s), (-w, y + 6)], n=10)
        sc.shape(P_(top + bot[1:]))
        sc.line(spline([(-w * 0.82, y - 4), (0, y - 10), (w * 0.82, y - 4)], n=8))
        sc.line(spline([(-w * 0.45, y - 38 * s), (0, y - 30 * s), (w * 0.45, y - 38 * s)], n=8))
        for sgn in (-1, 1): sc.line(spline([(sgn * (w + 8), y + 30), (sgn * (w + 18), y + 6), (sgn * (w + 6), y - 20)], n=6))
        return
    lift = {'closed': 0, 'smile': 14, 'grin': 18, 'line': 0, 'smirk': 0, 'sad': -10}.get(kind, 0) * s
    ml = spline([(-w, y + lift), (-w * 0.45, y - (4 if kind in ('smile', 'grin') else 0)), (0, y - 2), (w * 0.45, y - (4 if kind in ('smile', 'grin') else 0)), (w, y + (lift if kind != 'smirk' else 16 * s))], n=12)
    sc.line(ml)
    if kind == 'line': return
    up = spline([(-w * 0.85, y + 4 + lift * 0.6), (-w * 0.35, y + 16 * full * s), (-w * 0.12, y + 22 * full * s), (0, y + 16 * full * s), (w * 0.12, y + 22 * full * s), (w * 0.35, y + 16 * full * s), (w * 0.85, y + 4 + lift * 0.6)], n=8)
    sc.line(up)
    sc.line(spline([(-w * 0.55, y - 16 * full * s), (0, y - 26 * full * s), (w * 0.55, y - 16 * full * s)], n=10))
    if kind == 'grin':
        sc.line(spline([(-w * 0.75, y - 4), (0, y - 12), (w * 0.75, y - 4)], n=8))
    if kind in ('smile', 'grin'):
        for sgn in (-1, 1): sc.line(spline([(sgn * (w + 6), y + 36), (sgn * (w + 16), y + 14), (sgn * (w + 10), y - 6)], n=6))

def ear(sc, side=1, cx=None, s=1.0):
    x = side * (cx if cx is not None else 226)
    g = P_(spline([(x - side * 6, 30), (x + side * 26, 40), (x + side * 40, 0), (x + side * 32, -70), (x + side * 10, -120), (x - side * 8, -110)], n=8))
    sc.shape(g)
    sc.line(spline([(x + side * 4, 16), (x + side * 24, 18), (x + side * 26, -30), (x + side * 12, -60)], n=8))
    return g

def body(sc, neck_w=105, sh=420, collar='crew', kind='f', y0=-250):
    for s in (-1, 1):
        pass
    neck = P_([(-neck_w, y0), (neck_w, y0), (neck_w * 1.1, -470), (-neck_w * 1.1, -470)])
    sc.shape(neck)
    sc.line([(-neck_w * 0.6, -330), (-neck_w * 0.9, -380)])
    sh_y = -530 if kind != 'm' else -520
    torso = P_(spline([(-sh, -800), (-sh, sh_y - 60), (-sh * 0.8, sh_y), (-neck_w * 1.4, -440), (0, -450), (neck_w * 1.4, -440), (sh * 0.8, sh_y), (sh, sh_y - 60), (sh, -800)], n=8))
    sc.shape(torso)
    if collar == 'crew':
        sc.line(spline([(-neck_w * 1.35, -446), (0, -500), (neck_w * 1.35, -446)], n=10))
        sc.line(spline([(-neck_w * 1.45, -440), (0, -520), (neck_w * 1.45, -440)], n=10))
    elif collar == 'v':
        sc.line([(-neck_w * 1.3, -444), (0, -620), (neck_w * 1.3, -444)])
    elif collar == 'shirt':
        for s in (-1, 1):
            sc.shape(P_([(s * neck_w * 1.25, -430), (s * 10, -540), (s * neck_w * 1.9, -560), (s * neck_w * 1.75, -450)]))
        sc.line([(0, -540), (0, -800)]); sc.line(circle(0, -600, 8, 10)); sc.line(circle(0, -700, 8, 10))
    elif collar == 'turtle':
        sc.shape(P_(spline([(-neck_w * 1.2, -340), (0, -360), (neck_w * 1.2, -340), (neck_w * 1.35, -470), (0, -490), (-neck_w * 1.35, -470)], closed=False, n=6)))
        for k in range(-3, 4): sc.line([(k * neck_w * 0.3, -350), (k * neck_w * 0.33, -480)])
    elif collar == 'hoodie':
        sc.shape(P_(spline([(-neck_w * 2.2, -420), (-neck_w * 1.4, -360), (0, -470), (neck_w * 1.4, -360), (neck_w * 2.2, -420), (neck_w * 1.6, -560), (0, -580), (-neck_w * 1.6, -560)], closed=True, n=6)))
        for s in (-1, 1): sc.line([(s * 40, -560), (s * 46, -720)])
    return torso

# ---------------------------------------------------------------- hair (front view)
def below_region(half, depth=-1000, n=10, tension=0.45):
    """Region under a symmetric curve: `half` runs from the top centre to its right end; the region
    drops straight down from both ends to `depth`, so it removes everything below the hairline."""
    pts = spline(half, n=n, tension=tension)
    ex, ey = pts[-1]
    return P_(pts + [(ex, depth), (-ex, depth)] + [(-x, y) for x, y in pts[::-1]])

def drop_slivers(g, min_area=400):
    if g.is_empty: return g
    parts = [p for p in getattr(g, 'geoms', [g]) if p.area >= min_area]
    return unary_union(parts) if parts else g

def scallop(g, step=34, r=20, pred=None):
    """Bumpy, curly outline: small discs along the boundary (only where pred(x, y) holds)."""
    if g.is_empty: return g
    ring = LineString(g.exterior.coords) if g.geom_type == 'Polygon' else LineString(max(g.geoms, key=lambda p: p.area).exterior.coords)
    discs = []
    n = max(8, int(ring.length / step))
    for i in range(n):
        p = ring.interpolate(ring.length * i / n)
        if pred is None or pred(p.x, p.y): discs.append(Point(p.x, p.y).buffer(r, 8))
    return unary_union([g] + discs) if discs else g

def hair_region(outline_half, hairline_half):
    out = sym_closed(spline(outline_half, n=10, tension=0.45))
    return P_(out), below_region(hairline_half)

def strands(g, curves, n=14, shift=(0, 0)):
    """Flowing hair lines: curves between the first and last guide curves, clipped to the hair shape."""
    A, B = curves
    out = []
    for i in range(1, n):
        C = lerp_curve(A, B, i / n)
        out += clipL([C], g.buffer(-6))
    return out

def hair_front(style, sc_back, sc_front, kind='f', seed=0):
    r = rng(seed)
    if style in ('none', 'bald'):
        return
    if style == 'buzz':
        g = P_(sym_closed(spline([(0, 318), (165, 300), (226, 210), (236, 110)], n=8)) )
        hl = below_region([(0, 215), (120, 205), (200, 170), (236, 110)], n=8)
        cap = drop_slivers(g.difference(hl))
        sc_front.shape(cap)
        for k in range(110):
            x, y = r.uniform(-230, 230), r.uniform(150, 320)
            if cap.buffer(-8).contains(Point(x, y)): sc_front.line([(x, y), (x + r.uniform(-4, 4), y + 7)])
        return
    if style in ('short', 'side_part', 'crop', 'fringe', 'pixie', 'curly_short', 'grey_curls'):
        top = {'short': 360, 'side_part': 380, 'crop': 350, 'fringe': 370, 'pixie': 370, 'curly_short': 400, 'grey_curls': 385}[style]
        side = {'short': 40, 'side_part': 30, 'crop': 50, 'fringe': 10, 'pixie': -20, 'curly_short': 20, 'grey_curls': -40}[style]
        outer = [(0, top), (180, top - 30), (250, top - 130), (258, 120), (244, side)]
        if style == 'fringe':
            hl = [(0, 110), (120, 120), (205, 150), (238, side)]
        elif style == 'pixie':
            hl = [(0, 150), (90, 120), (190, 160), (232, side)]
        else:
            hl = [(0, 205), (130, 200), (205, 165), (236, side)]
        g, h = hair_region(outer, hl)
        cap = drop_slivers(g.difference(h))
        if style in ('curly_short', 'grey_curls'):
            cap = drop_slivers(scallop(g, 32, 17, lambda x, y: y > side + 30).difference(h))
            sc_front.shape(cap)
            for k in range(70 if style == 'curly_short' else 55):
                x, y = r.uniform(-260, 260), r.uniform(0, top)
                if cap.buffer(-14).contains(Point(x, y)):
                    rr_ = r.uniform(12, 22); sc_front.line(arc(x, y, rr_, r.uniform(0, 6), r.uniform(0, 6) + 4.5, n=10))
            return
        sc_front.shape(cap)
        px = 70 if style == 'side_part' else 0
        if style == 'side_part':
            RA = spline([(px, top - 8), (180, top - 36), (250, top - 130), (258, 120), (244, side)], n=12)
            RB = spline([(px, 212), (130, 200), (205, 165), (236, side)], n=12)
            LA = spline([(px, top - 8), (-60, top - 16), (-180, top - 32), (-250, top - 130), (-258, 120), (-244, side)], n=12)
            LB = spline([(px, 214), (-130, 200), (-205, 165), (-236, side)], n=12)
            for A, B, m in ((RA, RB, 4), (LA, LB, 6)):
                for i in range(1, m + 1):
                    sc_front.lines(clipL([lerp_curve(A, B, i / (m + 1))], cap.buffer(-6)))
            sc_front.line(clipL([[(px, top + 20), (px - 10, 180)]], cap)[0] if clipL([[(px, top + 20), (px - 10, 180)]], cap) else [(px, top), (px, top - 1)])
        else:
            for k in range(-6, 7):
                x0 = k * 34
                C = spline([(x0 * 0.3, top), (x0 * 0.8, top - 60), (x0 * 1.15, 200), (x0 * 1.3 + (20 if style == 'fringe' else 0), 120)], n=10)
                sc_front.lines(clipL([C], cap.buffer(-6)))
        return
    if style in ('long', 'wavy', 'bob', 'braids', 'ponytail', 'bun', 'pigtails', 'tied_back', 'long_m', 'puff'):
        top = 380 if style != 'puff' else 330
        if style == 'bob':
            outer_back = [(0, top), (200, top - 40), (280, 160), (290, -60), (270, -170), (220, -190)]
        elif style in ('long', 'wavy', 'long_m'):
            outer_back = [(0, top), (210, top - 40), (285, 150), (300, -150), (320, -420), (300, -560), (200, -580)]
        elif style in ('ponytail', 'bun', 'tied_back', 'puff', 'braids', 'pigtails'):
            outer_back = [(0, top), (190, top - 30), (250, 200), (252, 60), (240, 0)]
        g_back = P_(sym_closed(spline(outer_back, n=10, tension=0.45)) + [])
        face_hole = P_(face_outline(kind))
        hl = [(0, 215), (120, 205), (210, 150), (236, 20)] if style not in ('ponytail', 'bun', 'tied_back', 'puff', 'pigtails', 'braids') else [(0, 225), (130, 215), (215, 150), (238, 30)]
        part = 0
        hl_poly = below_region(hl)
        back = g_back.difference(face_hole.buffer(2))
        # hair behind the shoulders goes to the back scene; the part around the face to the front
        front_cap = drop_slivers(g_back.intersection(box(-400, 0, 400, 600)).difference(hl_poly))
        if style in ('long', 'wavy', 'bob', 'long_m'):
            sc_back.shape(back)
            sides = back.intersection(box(-400, -700, 400, 60))
            if style == 'wavy':
                for k in range(1, 7):
                    for sgn in (-1, 1):
                        x0 = sgn * (232 + k * 9)
                        C = [(x0 + sgn * 8 * math.sin(y / 45 + k), y) for y in range(60, -580, -14)]
                        sc_back.lines(clipL([C], sides.buffer(-5)))
            else:
                for k in range(1, 5):
                    for sgn in (-1, 1):
                        x0 = sgn * (230 + k * (13 if style != 'bob' else 10))
                        C = spline([(x0, 60), (x0 + sgn * 10, -200), (x0 + sgn * 6 - sgn * k * 4, -560)], n=10)
                        sc_back.lines(clipL([C], sides.buffer(-5)))
        if style in ('ponytail', 'tied_back'):
            pt = P_(spline([(30, top - 10), (170, top + 40), (250, top - 60), (240, top - 200), (200, top - 330), (220, top - 420), (180, top - 380), (180, top - 250), (150, top - 120), (40, top - 40)], n=8))
            sc_back.shape(pt)
            for k in range(1, 6): sc_back.lines(clipL([spline([(60 + k * 20, top), (230 - k * 4, top - 120), (195 + k * 3, top - 380)], n=10)], pt.buffer(-5)))
        if style == 'bun':
            bun = Polygon(circle(0, top + 70, 95, 40)); sc_front.shape(bun)
            for k in range(4): sc_front.line(arc(0, top + 70, 30 + k * 18, 0.4 + k, 4.6 + k, n=12))
        if style == 'puff':
            puff = scallop(Polygon(ellipse(0, top + 150, 215, 175, 0, 60)), 40, 24)
            sc_back.shape(puff)
            for k in range(70):
                x, y = r.uniform(-230, 230), r.uniform(top - 20, top + 330)
                if puff.buffer(-18).contains(Point(x, y)): sc_back.line(arc(x, y, r.uniform(12, 20), r.uniform(0, 6), r.uniform(0, 6) + 4.5, n=10))
            sc_back.shape(P_(spline([(-150, top - 14), (0, top + 6), (150, top - 14), (146, top + 22), (0, top + 42), (-146, top + 22)], closed=True, n=6, tension=0.4)))
        if style == 'pigtails':
            for sgn in (-1, 1):
                tail = P_(spline([(sgn * 230, 200), (sgn * 330, 160), (sgn * 400, -20), (sgn * 380, -200), (sgn * 340, -60), (sgn * 280, 80)], closed=True, n=8, tension=0.4))
                sc_back.shape(tail); sc_back.shape(Polygon(circle(sgn * 250, 190, 24, 16)))
                for k in range(1, 5): sc_back.lines(clipL([spline([(sgn * (250 + k * 15), 190), (sgn * (340 + k * 8), 60), (sgn * (360 + k * 4), -140)], n=8)], tail.buffer(-4)))
        if style == 'braids':
            for sgn in (-1, 1):
                for k in range(9):
                    y = 40 - k * 62
                    bead = P_(ellipse(sgn * 262 + sgn * (6 if k % 2 else -6), y, 30, 38, sgn * 0.4 * (1 if k % 2 else -1), 20))
                    sc_back.shape(bead)
                sc_back.shape(Polygon(circle(sgn * 262, -540, 16, 12)))
        sc_front.shape(front_cap)
        if style in ('long', 'wavy', 'long_m', 'bob'):
            A = spline([(0, top - 4), (150, top - 40), (230, 200), (238, 60)], n=12)
            B = spline([(0, 222), (110, 210), (200, 160), (236, 40)], n=12)
            for sgn in (-1, 1):
                for C in [lerp_curve(A, B, t) for t in (0.22, 0.47, 0.72)]:
                    sc_front.lines(clipL([[(sgn * x, y) for x, y in C]], front_cap.buffer(-5)))
            sc_front.line([(0, top), (0, 228)])
        else:
            A = spline([(0, top - 4), (150, top - 30), (215, 200), (240, 60)], n=12)
            B = spline([(0, 232), (120, 222), (205, 165), (238, 40)], n=12)
            for sgn in (-1, 1):
                for C in [lerp_curve(A, B, t) for t in (0.2, 0.42, 0.64, 0.86)]:
                    sc_front.lines(clipL([[(sgn * x, y) for x, y in C]], front_cap.buffer(-5)))
        return
    if style == 'afro':
        g = P_(spline([(0, 520), (230, 470), (380, 300), (400, 80), (330, -100), (240, -60), (236, 60), (130, 200), (0, 220), (-130, 200), (-236, 60), (-240, -60), (-330, -100), (-400, 80), (-380, 300), (-230, 470)], closed=True, n=8, tension=0.45))
        g = scallop(g, 40, 24, lambda x, y: abs(x) > 250 or y > 300)
        sc_back.shape(g)
        for k in range(95):
            x, y = r.uniform(-400, 400), r.uniform(-100, 520)
            if g.buffer(-16).contains(Point(x, y)):
                sc_back.line(arc(x, y, r.uniform(12, 20), r.uniform(0, 6), r.uniform(0, 6) + 4.8, n=10))
        return
    if style == 'curly_long':
        g = P_(spline([(0, 440), (230, 400), (330, 220), (350, -100), (330, -380), (230, -420), (236, 60), (130, 210), (0, 225), (-130, 210), (-236, 60), (-230, -420), (-330, -380), (-350, -100), (-330, 220), (-230, 400)], closed=True, n=8, tension=0.45))
        g = scallop(g, 38, 22, lambda x, y: abs(x) > 252 or y > 260)
        sc_back.shape(g)
        for k in range(110):
            x, y = r.uniform(-350, 350), r.uniform(-420, 440)
            if g.buffer(-15).contains(Point(x, y)): sc_back.line(arc(x, y, r.uniform(11, 18), r.uniform(0, 6), r.uniform(0, 6) + 4.8, n=10))

BEARD_PTS = {
    'goatee': [(0, -232), (42, -234), (62, -262), (56, -318), (28, -360), (0, -372), (-28, -360), (-56, -318), (-62, -262), (-42, -234)],
    'short': [(0, -232), (92, -234), (178, -168), (214, -60), (228, -10), (240, -20), (238, -150), (196, -282), (110, -352), (0, -372),
              (-110, -352), (-196, -282), (-238, -150), (-240, -20), (-228, -10), (-214, -60), (-178, -168), (-92, -234)],
    'full': [(0, -232), (96, -236), (186, -160), (216, -50), (228, -6), (246, -20), (252, -190), (200, -360), (90, -470), (0, -500),
             (-90, -470), (-200, -360), (-252, -190), (-246, -20), (-228, -6), (-216, -50), (-186, -160), (-96, -236)],
}
MOUTH_HOLE = Polygon(ellipse(0, -208, 84, 32, 0, 36))

def beard(sc, kind, seed=1, part='under'):
    """part='under' is drawn before the mouth (the beard with a hole for the lips); part='over' after it (the moustache)."""
    r = rng(seed)
    if part == 'over':
        if kind in ('moustache', 'full', 'short', 'goatee'):
            w = 1.0 if kind != 'goatee' else 0.82
            m = P_(spline([(0, -164), (44 * w, -158), (92 * w, -182), (106 * w, -212), (66 * w, -194), (0, -186), (-66 * w, -194), (-106 * w, -212), (-92 * w, -182), (-44 * w, -158)], closed=True, n=6, tension=0.4))
            sc.shape(m)
            for sgn in (-1, 1):
                for k in range(4):
                    x0 = sgn * (14 + k * 20 * w); sc.line([(x0, -168 - k * 2), (x0 + sgn * 10, -184 - k * 4)])
        return
    if kind == 'stubble':
        g = P_(face_outline('m', 1.08)).intersection(box(-400, -400, 400, -150)).difference(Polygon(ellipse(0, -205, 95, 50, 0, 30)))
        for k in range(150):
            x, y = r.uniform(-230, 230), r.uniform(-320, -150)
            if g.buffer(-8).contains(Point(x, y)): sc.line([(x, y), (x + 2, y - 4)])
        return
    if kind not in BEARD_PTS: return
    g = P_(spline(BEARD_PTS[kind], closed=True, n=8, tension=0.4))
    g = scallop(g, 30, 14, lambda x, y: y < -250)
    g = g.difference(MOUTH_HOLE)
    sc.shape(g)
    # hair strokes: a jittered grid, each stroke running down and in towards the chin
    inner = g.buffer(-12)
    step = 30 if kind == 'full' else 32
    for gy in range(-240, -500, -step):
        for gx in range(-250, 260, step):
            x, y = gx + r.uniform(-9, 9) + (step / 2 if (gy // step) % 2 else 0), gy + r.uniform(-9, 9)
            if not inner.contains(Point(x, y)): continue
            a = math.atan2(-560 - y, -x * 0.55)          # towards a point below the chin
            L = r.uniform(16, 26)
            bend = r.uniform(-4, 4)
            p1 = (x + math.cos(a) * L, y + math.sin(a) * L)
            mid = ((x + p1[0]) / 2 + bend, (y + p1[1]) / 2)
            sc.line([(x, y), mid, p1])

def glasses(sc, kind='round', y=4):
    if kind == 'sun_on_head':
        for s in (-1, 1): sc.shape(P_(rect(s * 30 if s > 0 else -150, 300, 120, 60, 26)))
        sc.line([(-30, 330), (30, 330)]); return
    for s in (-1, 1):
        if kind == 'round': ring = Polygon(circle(s * 92, y, 62, 40))
        else: ring = P_(rect(s * 92 - 70, y - 48, 140, 96, 24))
        sc.shape(ring.difference(ring.buffer(-7)))
        sc.line(spline([(s * (92 + (62 if kind == 'round' else 70)), y + 10), (s * 200, y + 18), (s * 232, y + 6)], n=6))
    sc.line(spline([(-30, y + 8), (0, y + 18), (30, y + 8)], n=6))

def hat(sc, kind):
    if kind == 'beanie':
        g = P_(spline([(-262, 170), (-250, 360), (-120, 470), (120, 470), (250, 360), (262, 170)], n=10) + [(262, 170), (-262, 170)])
        sc.shape(g)
        band_ = P_([(-266, 160), (266, 160), (266, 240), (-266, 240)]); sc.shape(band_)
        for x in range(-240, 260, 28): sc.line([(x, 166), (x, 234)])
        sc.shape(Polygon(circle(0, 500, 48, 28)))
    elif kind == 'sunhat':
        brim = Polygon(ellipse(0, 250, 520, 110, 0, 80)); crown = P_(spline([(-220, 260), (-200, 420), (0, 470), (200, 420), (220, 260)], n=10) + [(220, 260)])
        sc.shape(brim); sc.shape(crown); sc.shape(P_([(-214, 270), (214, 270), (210, 320), (-210, 320)]))
    elif kind == 'cap':
        sc.shape(P_(spline([(-250, 230), (-240, 380), (0, 450), (240, 380), (250, 230)], n=10) + [(250, 230)]))
        sc.shape(P_(spline([(-270, 240), (0, 200), (270, 240), (220, 160), (0, 130), (-220, 160)], closed=True, n=8, tension=0.4)))

def headphones(sc):
    sc.shape(LineString(spline([(-262, 60), (-250, 360), (0, 450), (250, 360), (262, 60)], n=14)).buffer(16))
    for s in (-1, 1):
        sc.shape(P_(rect(s * 262 - 40, -70, 80, 150, 36))); sc.line(rect(s * 262 - 22, -40, 44, 90, 20))

def hijab(sc_back, sc_front):
    outer = P_(spline([(0, 420), (230, 380), (320, 180), (330, -150), (380, -420), (480, -620), (0, -700), (-480, -620), (-380, -420), (-330, -150), (-320, 180), (-230, 380)], closed=True, n=8, tension=0.45))
    face = P_(spline([(0, 250), (170, 225), (225, 100), (225, -110), (180, -230), (80, -300), (0, -315), (-80, -300), (-180, -230), (-225, -110), (-225, 100), (-170, 225)], closed=True, n=8, tension=0.45))
    sc_front.shape(outer.difference(face))
    sc_front.lines(clipL([spline([(-300, 300), (-280, -100), (-120, -380), (200, -560)], n=10), spline([(230, 200), (300, -120), (380, -420)], n=10)], outer.difference(face).buffer(-6)))

def bow(sc, x=150, y=320, s=1.0):
    for sgn in (-1, 1):
        sc.shape(P_([(x + sgn * 6 * s, y - 12 * s), (x + sgn * 44 * s, y - 84 * s), (x + sgn * 26 * s, y - 78 * s), (x + sgn * 14 * s, y - 96 * s), (x - sgn * 4 * s, y - 18 * s)]))
    for sgn in (-1, 1):
        sc.shape(P_(spline([(x, y), (x + sgn * 64 * s, y + 52 * s), (x + sgn * 92 * s, y + 8 * s), (x + sgn * 70 * s, y - 46 * s)], closed=True, n=8, tension=0.4)))
        sc.line(spline([(x + sgn * 22 * s, y + 6 * s), (x + sgn * 52 * s, y + 18 * s), (x + sgn * 70 * s, y + 8 * s)], n=6))
    sc.shape(Polygon(ellipse(x, y, 20 * s, 25 * s, 0, 16)))

def headband(sc):
    band_ = LineString(spline([(-258, 130), (-214, 262), (0, 342), (214, 262), (258, 130)], n=12)).buffer(19, cap_style=2)
    sc.shape(band_)

def earrings(sc, kind='stud'):
    for s in (-1, 1):
        if kind == 'hoop': sc.line(circle(s * 238, -150, 26, 20))
        else: sc.shape(Polygon(circle(s * 238, -122, 10, 12)))

def wrinkles(sc, age):
    if age < 0.4: return
    for k in range(3): sc.line(spline([(-110 + k * 10, 150 + k * 22), (0, 160 + k * 24), (110 - k * 10, 150 + k * 22)], n=8))
    for s in (-1, 1):
        sc.line(spline([(s * 50, -110), (s * 82, -170), (s * 88, -220)], n=8))
        if age > 0.6: sc.line(spline([(s * 120, -230), (s * 130, -280), (s * 110, -300)], n=6))

def portrait(spec):
    """spec: dict(kind f/m/c/b, jaw, chin, length, hair, beard, glasses, hat, mouth, brows, wink, age, collar, earrings, headphones, hijab, seed, look, lashes)"""
    k = spec.get('kind', 'f'); child = k in ('c', 'b')
    sb = Scene(); sf = Scene(); s = Scene()
    seed = spec.get('seed', 0)
    if spec.get('hijab'):
        body(s, 105, 400 if k != 'm' else 440, 'crew', k)
        hijab(sb, sf)
    else:
        hair_front(spec.get('hair', 'short'), sb, sf, k, seed)
        torso = body(s, 95 if child else 105, 340 if child else (440 if k == 'm' else 400), spec.get('collar', 'crew'), k)
    out = Scene(); out.items += sb.items + s.items
    if not spec.get('hijab'):
        for side in (-1, 1): ear(out, side)
    fo = P_(face_outline(k, spec.get('jaw', 1.0), spec.get('chin', 1.0), spec.get('length', 1.0)))
    out.shape(fo)
    sc = out
    ey = -30 if child else 0
    look = spec.get('look', (0, 0))
    raise_ = 1.0 if spec.get('mouth') == 'o' else spec.get('raise', 0.0)
    for side in (-1, 1):
        brow(sc, side * 92, ey + 62, 1.0, side, raise_, spec.get('frown', 0.0), 12 if k == 'm' else 9)
        eye(sc, side * 92, ey, 1.0 if not child else 1.12, side, wink=(spec.get('wink') and side == 1), look=look, lashes=spec.get('lashes', k == 'f'), age=spec.get('age', 0), child=child)
    nose(sc, 1.0 if not child else 0.8, child, spec.get('nose_w', 1.0), bridge=not child)
    wrinkles(sc, spec.get('age', 0))
    if spec.get('beard'): beard(sc, spec['beard'], seed, 'under')
    mouth(sc, spec.get('mouth', 'closed'), 1.0, 66 if k != 'm' else 72, -205, spec.get('lips', 1.0 if k == 'f' else 0.75), child)
    if spec.get('beard'): beard(sc, spec['beard'], seed, 'over')
    if child and spec.get('freckles'):
        r = rng(seed)
        for s_ in (-1, 1):
            for j in range(6): sc.line(circle(s_ * (112 + r.uniform(-28, 28)), ey - 98 + r.uniform(-16, 16), 4, 6))
    sc.items += sf.items
    if spec.get('glasses'): glasses(sc, spec['glasses'], ey + 4)
    if spec.get('hat'): hat(sc, spec['hat'])
    if spec.get('headphones'): headphones(sc)
    if spec.get('earrings'): earrings(sc, spec['earrings'])
    if spec.get('headband'): headband(sc)
    if spec.get('bow'): bow(sc, *spec['bow'])
    return sc

# ================================================================ the list
def faces_items():
    F = []
    def add(name, sc, slug): F.append((name, flipL(sc.render()), slug))
    add('Woman with a bun and round glasses', portrait(dict(kind='f', hair='bun', glasses='round', mouth='smile', seed=1)), 'woman-bun-round-glasses')
    add('Laughing child with curls', portrait(dict(kind='c', hair='curly_short', mouth='laugh', seed=2, freckles=True)), 'laughing-child-curls')
    add('Man with a short beard', portrait(dict(kind='m', jaw=1.08, hair='side_part', beard='short', mouth='closed', collar='shirt', seed=3)), 'man-short-beard')
    add('Elderly woman with grey curls', portrait(dict(kind='f', hair='grey_curls', age=0.8, mouth='smile', glasses='rect', seed=4, collar='v')), 'elderly-woman-curls')
    add('Young man with a buzz cut', portrait(dict(kind='m', jaw=1.1, hair='buzz', mouth='closed', collar='crew', seed=5)), 'young-man-buzz-cut')
    add('Woman with long straight hair', portrait(dict(kind='f', hair='long', mouth='smile', seed=6, earrings='stud')), 'woman-long-hair')
    add('Woman with a wavy bob', portrait(dict(kind='f', hair='bob', mouth='closed', seed=7, collar='turtle')), 'woman-bob')
    add('Man with an afro', portrait(dict(kind='m', jaw=1.05, hair='afro', mouth='smile', seed=8, collar='crew')), 'man-afro')
    add('Woman with braids', portrait(dict(kind='f', hair='braids', mouth='smile', seed=9)), 'woman-braids')
    add('Man with glasses and a moustache', portrait(dict(kind='m', jaw=1.05, hair='short', beard='moustache', glasses='rect', mouth='closed', collar='shirt', seed=10)), 'man-glasses-moustache')
    add('Teenager with headphones', portrait(dict(kind='m', jaw=0.98, hair='fringe', headphones=True, mouth='smirk', collar='hoodie', seed=11)), 'teen-headphones')
    add('Smiling woman in a hijab', portrait(dict(kind='f', hijab=True, mouth='smile', seed=12)), 'woman-hijab')
    add('Elderly man with a full beard', portrait(dict(kind='m', jaw=1.05, hair='bald', beard='full', age=0.8, mouth='closed', seed=13, collar='shirt')), 'elderly-man-beard')
    add('Girl with pigtails', portrait(dict(kind='c', hair='pigtails', mouth='grin', seed=14, freckles=True)), 'girl-pigtails')
    add('Boy with a fringe', portrait(dict(kind='c', hair='fringe', mouth='smile', seed=15)), 'boy-fringe')
    add('Woman with a pixie cut and hoops', portrait(dict(kind='f', hair='pixie', earrings='hoop', mouth='smile', seed=16, collar='v')), 'woman-pixie-hoops')
    add('Man with stubble in a beanie', portrait(dict(kind='m', jaw=1.08, hair='short', hat='beanie', beard='stubble', mouth='closed', seed=17, collar='hoodie')), 'man-beanie-stubble')
    add('Woman in a sun hat', portrait(dict(kind='f', hair='long', hat='sunhat', mouth='smile', seed=18)), 'woman-sun-hat')
    add('Woman with a ponytail', portrait(dict(kind='f', hair='ponytail', mouth='closed', seed=19, look=(0.5, 0))), 'woman-ponytail')
    add('Man with long hair', portrait(dict(kind='m', jaw=1.04, hair='long_m', beard='goatee', mouth='closed', seed=20)), 'man-long-hair')
    add('Surprised man', portrait(dict(kind='m', jaw=1.06, hair='crop', mouth='o', seed=21)), 'surprised-man')
    add('Winking woman', portrait(dict(kind='f', hair='wavy', wink=True, mouth='smirk', seed=22)), 'winking-woman')
    add('Thoughtful man with a goatee', portrait(dict(kind='m', jaw=1.06, hair='side_part', beard='goatee', mouth='line', look=(-0.6, 0.6), seed=23, collar='turtle')), 'thoughtful-man-goatee')
    add('Woman with sunglasses on her head', portrait(dict(kind='f', hair='long', glasses='sun_on_head', mouth='closed', seed=24)), 'woman-sunglasses-head')
    add('Grandmother with glasses', portrait(dict(kind='f', hair='bun', glasses='round', age=0.9, mouth='smile', seed=25, collar='crew')), 'grandmother-glasses')
    add('Baby', portrait(dict(kind='b', hair='none', mouth='smile', seed=26)), 'baby-face')
    add('Man with curly hair', portrait(dict(kind='m', jaw=1.05, hair='curly_short', mouth='smile', seed=27)), 'man-curly-hair')
    add('Woman with an afro puff', portrait(dict(kind='f', hair='puff', mouth='smile', earrings='hoop', seed=28)), 'woman-afro-puff')
    add('Woman with long curly hair', portrait(dict(kind='f', hair='curly_long', mouth='grin', seed=29)), 'woman-long-curly')
    add('Serious man with a crew cut', portrait(dict(kind='m', jaw=1.12, hair='crop', mouth='line', frown=0.6, seed=30, collar='shirt')), 'serious-man')
    add('Man in a cap with a short beard', portrait(dict(kind='m', jaw=1.08, hair='short', hat='cap', beard='short', mouth='smile', seed=31, collar='crew')), 'man-cap-beard')
    add('Girl with a hair bow', portrait(dict(kind='c', hair='bob', bow=(140, 300, 0.9), mouth='smile', seed=32, freckles=True)), 'girl-hair-bow')
    add('Man with a man bun and a full beard', portrait(dict(kind='m', jaw=1.06, hair='bun', beard='full', mouth='closed', seed=33, collar='v')), 'man-bun-beard')
    add('Woman with a headband', portrait(dict(kind='f', hair='long', headband=True, mouth='smile', seed=34, earrings='hoop')), 'woman-headband')
    add('Grandfather with glasses and a moustache', portrait(dict(kind='m', jaw=1.06, hair='side_part', age=0.9, glasses='rect', beard='moustache', mouth='smile', seed=35, collar='shirt')), 'grandfather-moustache')
    add('Boy in a cap', portrait(dict(kind='c', hair='fringe', hat='cap', mouth='grin', seed=36, freckles=True)), 'boy-cap')
    add('Woman with a bob and round glasses', portrait(dict(kind='f', hair='bob', glasses='round', mouth='closed', seed=37, collar='v')), 'woman-bob-glasses')
    add('Smiling man with a full beard', portrait(dict(kind='m', jaw=1.06, hair='short', beard='full', mouth='smile', seed=38, collar='crew')), 'man-full-beard')
    return F

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    items = []
    for name, L, slug in faces_items():
        it = Item('faces', name, L); it.slug = slug; items.append(it)
    save(items, OUT)
    P = sorted(export_size(i.lines)[0] for i in items)
    print(len(items), 'faces; median', P[len(P) // 2], 'max', P[-1])
    if SHEET:
        for i in range(0, len(items), 20):
            sheet(items[i:i + 20], SHEET.replace('.png', f'_{i // 20}.png'), cols=5, cell=3.0)
