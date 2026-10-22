"""Ants: anatomically sensible ants (head with compound eyes and mandibles, elbowed antennae, mesosoma,
one or two waist nodes, gaster, three pairs of jointed legs on the mesosoma) in top, side and face views,
with species variants and scenes. Drawn y-up, flipped at the end.
Usage: python3 -I gen_ants.py <out.json> [sheet.png]"""
import math, sys, random, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity

def flipL(L): return [[(x, -y) for x, y in P] for P in L]
def ell(cx, cy, rx, ry, rot=0.0, n=40): return Polygon(ellipse(cx, cy, rx, ry, rot, n))
def disc(cx, cy, r, n=24): return Polygon(circle(cx, cy, r, n))
def seg(a, b, w0, w1=None):
    """A tapered limb segment from a (width w0) to b (width w1) with round ends."""
    w1 = w0 if w1 is None else w1
    return unary_union([LineString([a, b]).buffer(min(w0, w1) / 2, cap_style=1), Polygon([(a[0] + (b[1] - a[1]) / math.dist(a, b) * w0 / 2, a[1] - (b[0] - a[0]) / math.dist(a, b) * w0 / 2),
                        (b[0] + (b[1] - a[1]) / math.dist(a, b) * w1 / 2, b[1] - (b[0] - a[0]) / math.dist(a, b) * w1 / 2),
                        (b[0] - (b[1] - a[1]) / math.dist(a, b) * w1 / 2, b[1] + (b[0] - a[0]) / math.dist(a, b) * w1 / 2),
                        (a[0] - (b[1] - a[1]) / math.dist(a, b) * w0 / 2, a[1] + (b[0] - a[0]) / math.dist(a, b) * w0 / 2)]).buffer(0)])
def dirv(deg): a = math.radians(deg); return (math.sin(a), math.cos(a))     # 0 = forward (+y), 90 = right
def add(p, d, L): return (p[0] + d[0] * L, p[1] + d[1] * L)

SPECIES = {
    'garden':    dict(head=(46, 52), shape='round', mand='short', eye=0.22, nodes=1, meso=(30, 112), gaster=(62, 76), leg=1.0, spines=False, ant=1.0),
    'carpenter': dict(head=(58, 58), shape='heart', mand='short', eye=0.2, nodes=1, meso=(32, 120), gaster=(70, 84), leg=1.1, spines=False, ant=1.05),
    'wood':      dict(head=(50, 54), shape='heart', mand='short', eye=0.22, nodes=1, meso=(30, 116), gaster=(64, 78), leg=1.05, spines=False, ant=1.0),
    'fire':      dict(head=(44, 50), shape='square', mand='short', eye=0.16, nodes=2, meso=(26, 104), gaster=(56, 70), leg=0.95, spines=False, ant=0.95),
    'leafcutter':dict(head=(66, 60), shape='heart', mand='leaf', eye=0.16, nodes=2, meso=(30, 118), gaster=(48, 58), leg=1.25, spines=True, ant=1.15),
    'army':      dict(head=(54, 60), shape='square', mand='sickle', eye=0.0, nodes=2, meso=(26, 120), gaster=(50, 66), leg=1.25, spines=False, ant=0.9),
    'bullet':    dict(head=(48, 60), shape='square', mand='short', eye=0.16, nodes=1, meso=(32, 130), gaster=(56, 84), leg=1.1, spines=False, ant=1.0, node_big=True),
    'trapjaw':   dict(head=(44, 64), shape='long', mand='trap', eye=0.18, nodes=1, meso=(26, 116), gaster=(50, 66), leg=1.2, spines=False, ant=1.1),
    'bulldog':   dict(head=(52, 56), shape='round', mand='bulldog', eye=0.26, nodes=2, meso=(28, 130), gaster=(56, 80), leg=1.25, spines=False, ant=1.0),
    'weaver':    dict(head=(42, 52), shape='round', mand='short', eye=0.22, nodes=1, meso=(24, 132), gaster=(48, 62), leg=1.4, spines=False, ant=1.2),
    'honeypot':  dict(head=(42, 46), shape='round', mand='short', eye=0.22, nodes=1, meso=(26, 100), gaster=(150, 160), leg=1.0, spines=False, ant=1.0),
    'harvester': dict(head=(56, 58), shape='square', mand='short', eye=0.18, nodes=2, meso=(28, 112), gaster=(58, 72), leg=1.05, spines=True, ant=1.0),
    'crazy':     dict(head=(36, 42), shape='round', mand='short', eye=0.26, nodes=1, meso=(20, 104), gaster=(44, 56), leg=1.6, spines=False, ant=1.5),
    'acrobat':   dict(head=(44, 48), shape='round', mand='short', eye=0.2, nodes=2, meso=(26, 100), gaster=(64, 64), leg=1.0, spines=True, ant=1.0, heart=True),
    'turtle':    dict(head=(78, 70), shape='disc', mand='short', eye=0.14, nodes=2, meso=(40, 100), gaster=(68, 74), leg=0.9, spines=True, ant=0.8),
    'desert':    dict(head=(40, 50), shape='round', mand='short', eye=0.24, nodes=1, meso=(22, 120), gaster=(46, 58), leg=1.7, spines=False, ant=1.3),
    'soldier':   dict(head=(96, 96), shape='heart', mand='short', eye=0.12, nodes=2, meso=(30, 112), gaster=(56, 70), leg=1.0, spines=True, ant=0.9),
    'queen':     dict(head=(50, 54), shape='round', mand='short', eye=0.2, nodes=1, meso=(42, 150), gaster=(80, 120), leg=1.0, spines=False, ant=1.0),
    'pharaoh':   dict(head=(40, 48), shape='round', mand='short', eye=0.18, nodes=2, meso=(22, 104), gaster=(48, 62), leg=1.0, spines=False, ant=1.1),
    'argentine': dict(head=(40, 48), shape='round', mand='short', eye=0.2, nodes=1, meso=(22, 108), gaster=(50, 64), leg=1.2, spines=False, ant=1.2),
}

# ---------------------------------------------------------------- top (dorsal) view
def head_outline(sp, cx=0.0, cy=0.0):
    rx, ry = sp['head'][0], sp['head'][1]
    if sp['shape'] == 'heart':
        pts = [(0, -ry * 0.82), (rx * 0.5, -ry * 0.98), (rx * 0.95, -ry * 0.6), (rx, 0), (rx * 0.85, ry * 0.6), (rx * 0.45, ry * 0.95), (0, ry)]
    elif sp['shape'] == 'square':
        pts = [(0, -ry), (rx * 0.75, -ry * 0.98), (rx, -ry * 0.6), (rx, ry * 0.4), (rx * 0.8, ry * 0.85), (rx * 0.4, ry), (0, ry)]
    elif sp['shape'] == 'long':
        pts = [(0, -ry), (rx * 0.6, -ry * 0.95), (rx * 0.95, -ry * 0.5), (rx * 0.9, ry * 0.4), (rx * 0.6, ry * 0.9), (0, ry)]
    elif sp['shape'] == 'disc':
        pts = [(0, -ry), (rx * 0.7, -ry * 0.9), (rx, -ry * 0.3), (rx, ry * 0.3), (rx * 0.7, ry * 0.85), (0, ry * 0.95)]
    else:
        pts = [(0, -ry), (rx * 0.65, -ry * 0.9), (rx, -ry * 0.3), (rx * 0.92, ry * 0.4), (rx * 0.6, ry * 0.88), (0, ry)]
    half = spline(pts, n=6, tension=0.45)
    full = half + [(-x, y) for x, y in half[::-1][1:]]
    return Polygon([(cx + x, cy + y) for x, y in full]).buffer(0)

def mandibles(sp, cy, open_=0.0):
    rx, ry = sp['head']; out = []
    for s in (-1, 1):
        if sp['mand'] == 'trap':
            base = (s * rx * 0.22, cy + ry * 0.9)
            tip = (s * rx * (0.2 + open_ * 0.5), cy + ry * 2.1)
            out.append(seg(base, tip, 10, 7))
            out.append(Polygon([(tip[0], tip[1]), (tip[0] - s * 12, tip[1] - 4), (tip[0] - s * 4, tip[1] - 14)]))
        elif sp['mand'] == 'bulldog':
            P = spline([(s * rx * 0.4, cy + ry * 0.85), (s * rx * 0.62, cy + ry * 1.4), (s * rx * 0.45, cy + ry * 1.9), (s * rx * 0.08, cy + ry * 2.1)], n=8)
            g = LineString(P).buffer(6, cap_style=1)
            out.append(g)
        elif sp['mand'] == 'sickle':
            P = spline([(s * rx * 0.45, cy + ry * 0.85), (s * rx * 0.7, cy + ry * 1.4), (s * rx * 0.2, cy + ry * 1.75), (-s * rx * 0.25, cy + ry * 1.65)], n=8)
            out.append(LineString(P).buffer(5, cap_style=1))
        else:
            k = 0.62 if sp['mand'] == 'short' else 0.75
            P = [(s * rx * 0.55, cy + ry * 0.8), (s * rx * 0.62, cy + ry * (0.8 + k * 0.7)), (s * rx * 0.1, cy + ry * (0.8 + k)), (s * rx * 0.2, cy + ry * (0.8 + k * 0.6)), (s * rx * 0.3, cy + ry * 0.86)]
            out.append(Polygon(P).buffer(0))
    return out

def antenna(sp, cy, s, pose=0.0, scale=1.0):
    """Points of one antenna (top view): insertion, elbow, then the funiculus to the tip."""
    rx, ry = sp['head']; k = sp['ant'] * scale
    ins = (s * rx * 0.32, cy + ry * 0.55)
    elbow = (s * (rx * 1.25 + 18 * k), cy + ry * 0.05 - 10 * k + pose * 20)
    tip = (s * (rx * 1.6 + 70 * k), cy + ry * 1.2 + 120 * k + pose * 40)
    mid = (s * (rx * 1.6 + 50 * k), cy + ry * 0.6 + 50 * k)
    fun = spline([elbow, mid, tip], n=12)
    return ins, elbow, fun

def leg_points(base, angles, lens):
    """Joints of a leg: base (coxa), knee, ankle, tip; angles in degrees (0 forward, 90 right)."""
    p = [base]
    for a, L in zip(angles, lens):
        p.append(add(p[-1], dirv(a), L))
    return p

def legs_top(sp, meso_y0, meso_len, phase=0.0, spread=1.0):
    """Six legs (top view): list of (shapes) for femur/tibia/tarsus. phase shifts the tripod gait."""
    out = []
    mw = sp['meso'][0]; k = sp['leg']
    for i, (f, base_ang) in enumerate(((0.12, 38), (0.48, 92), (0.8, 140))):
        for s in (-1, 1):
            tri = (i % 2 == 0) == (s > 0)                            # tripod group
            d = (14 if tri else -14) * math.cos(phase * math.pi)
            y = meso_y0 - meso_len * f
            base = (s * mw * 0.75, y)
            a0 = base_ang + d
            angles = [s * (a0 - 15 * spread), s * (a0 + 25 if i < 2 else a0 + 10), s * (a0 + 40 if i == 0 else a0 + 20)]
            lens = [70 * k, 80 * k, 60 * k]
            P = leg_points(base, angles, lens)
            shapes = [seg(P[0], P[1], 13, 11), seg(P[1], P[2], 10, 7)]
            # tarsus: five small segments with claws
            ta = P[2]; dvec = ((P[3][0] - P[2][0]) / lens[2], (P[3][1] - P[2][1]) / lens[2])
            for t in range(5):
                a_ = add(ta, dvec, lens[2] * t / 5); b_ = add(ta, dvec, lens[2] * (t + 0.85) / 5)
                shapes.append(seg(a_, b_, 5.5, 4.5))
            tip = P[3]
            claw = [add(tip, (dvec[0] * 0.7 + dvec[1] * 0.7 * s, dvec[1] * 0.7 - dvec[0] * 0.7 * s), 8), tip, add(tip, (dvec[0] * 0.7 - dvec[1] * 0.7 * s, dvec[1] * 0.7 + dvec[0] * 0.7 * s), 8)]
            out.append((shapes, claw))
    return out

def ant_top(sp, phase=0.0, ant_pose=0.0, mand_open=0.0, wings=False, carry=None, legs=True, simple=False):
    """An ant from above, head up (+y), centred on the mesosoma. Returns a Scene."""
    sc = Scene()
    rx, ry = sp['head']; mw, ml = sp['meso']; gw, gl = sp['gaster']
    head_cy = ml * 0.5 + ry * 0.92
    meso_y0 = ml * 0.5
    # legs (behind everything)
    if legs:
        for shapes, claw in legs_top(sp, meso_y0, ml, phase):
            if simple:
                sc.shape(unary_union(shapes).buffer(1.5))
            else:
                for g in shapes: sc.shape(g)
                sc.line(claw)
    # antennae
    for s in (-1, 1):
        ins, elbow, fun = antenna(sp, head_cy, s, ant_pose * s)
        sc.shape(seg(ins, elbow, 8, 6))
        n = 11
        if simple:
            sc.shape(LineString(fun).buffer(4.5, cap_style=1)); continue
        for t in range(n):
            a_ = fun[int(t * (len(fun) - 1) / n)]; b_ = fun[int((t + 0.85) * (len(fun) - 1) / n)]
            w = 6 if t < n - 4 else 8.5
            sc.shape(seg(a_, b_, w, w))
    # wings (behind the body, over the legs)
    if wings:
        for s in (-1, 1):
            fw = Polygon(spline([(s * mw * 0.5, -ml * 0.05), (s * (mw + 60), -ml * 0.6), (s * (mw + 70), -ml * 1.7), (s * (mw + 30), -ml * 2.6), (s * mw * 0.6, -ml * 0.7)], closed=True, n=8, tension=0.4)).buffer(0)
            hw = Polygon(spline([(s * mw * 0.4, -ml * 0.4), (s * (mw + 30), -ml * 0.9), (s * (mw + 34), -ml * 1.8), (s * mw * 0.7, -ml * 1.3)], closed=True, n=8, tension=0.4)).buffer(0)
            sc.shape(hw); sc.shape(fw)
            sc.line([(s * mw * 0.6, -ml * 0.1), (s * (mw + 40), -ml * 1.2), (s * (mw + 50), -ml * 2.2)])
            sc.line([(s * (mw + 40), -ml * 1.2), (s * (mw + 10), -ml * 1.8)])
            sc.line(circle(s * (mw + 52), -ml * 0.85, 7, 10))
    # gaster and nodes
    y = -ml * 0.5
    node_w = mw * (0.75 if sp.get('node_big') else 0.55)
    for nidx in range(sp['nodes']):
        sc.shape(ell(0, y - 12, node_w, 14)); y -= 26
    gy = y - gl * 0.95
    if sp.get('heart'):
        g = Polygon(spline([(0, y - 6), (gw * 0.7, y - gl * 0.2), (gw, y - gl * 0.9), (gw * 0.6, y - gl * 1.7), (0, y - gl * 1.5), (-gw * 0.6, y - gl * 1.7), (-gw, y - gl * 0.9), (-gw * 0.7, y - gl * 0.2)], closed=True, n=8, tension=0.45)).buffer(0)
        sc.shape(g)
    else:
        g = ell(0, gy, gw, gl, 0, 60); sc.shape(g)
        for f in (0.45, 0.0, -0.45):
            yy = gy + gl * f; xw = gw * math.sqrt(max(0, 1 - f * f))
            sc.line(spline([(-xw * 0.96, yy), (0, yy - gl * 0.12), (xw * 0.96, yy)], n=8))
    # mesosoma
    mp = [(0, ml * 0.5 + 4), (mw * 0.9, ml * 0.42), (mw, ml * 0.15), (mw * 0.72, -ml * 0.05), (mw * 0.62, -ml * 0.3), (mw * 0.7, -ml * 0.45), (mw * 0.4, -ml * 0.55), (0, -ml * 0.56)]
    half = spline(mp, n=6, tension=0.45)
    meso = Polygon(half + [(-x, yy) for x, yy in half[::-1][1:]]).buffer(0)
    sc.shape(meso)
    sc.line(spline([(-mw * 0.8, ml * 0.25), (0, ml * 0.2), (mw * 0.8, ml * 0.25)], n=6))
    sc.line(spline([(-mw * 0.62, -ml * 0.12), (0, -ml * 0.16), (mw * 0.62, -ml * 0.12)], n=6))
    if sp['spines']:
        for s in (-1, 1): sc.shape(Polygon([(s * mw * 0.55, -ml * 0.4), (s * (mw * 0.6 + 16), -ml * 0.62), (s * mw * 0.35, -ml * 0.5)]))
    # head and mandibles
    if carry is not None: carry(sc, head_cy + ry, sp)
    for m in mandibles(sp, head_cy, mand_open): sc.shape(m)
    h = head_outline(sp, 0, head_cy); sc.shape(h)
    if sp['eye'] > 0:
        for s in (-1, 1):
            e = ell(s * rx * 0.86, head_cy + ry * 0.12, rx * sp['eye'] * 0.6, ry * sp['eye'], s * 0.2, 20)
            sc.shape(e); sc.line(ellipse(s * rx * 0.86, head_cy + ry * 0.12, rx * sp['eye'] * 0.3, ry * sp['eye'] * 0.55, s * 0.2, 12))
    for s in (-1, 1): sc.line(spline([(s * rx * 0.25, head_cy + ry * 0.75), (s * rx * 0.2, head_cy + ry * 0.2), (s * rx * 0.3, head_cy - ry * 0.3)], n=6))
    sc.line(spline([(-rx * 0.45, head_cy + ry * 0.82), (0, head_cy + ry * 0.7), (rx * 0.45, head_cy + ry * 0.82)], n=6))
    return sc

# ---------------------------------------------------------------- side (lateral) view
def ant_side(sp, phase=0.0, raise_gaster=0.0, wings=False, carry=None, head_up=0.0):
    """An ant from the side, head to the right, standing on y = 0."""
    sc = Scene()
    rx, ry = sp['head']; mw, ml = sp['meso']; gw, gl = sp['gaster']; k = sp['leg']
    body_y = 95 * k
    # far legs (drawn first, thinner), then near legs at the end
    def leg(base, which, far=False):
        dx = {0: 50, 1: 10, 2: -40}[which] * k
        sh = (16 if (which % 2 == 0) != far else -16) * math.cos(phase * math.pi) * k
        knee = (base[0] + dx * 0.6 + sh * 0.5 + (20 if which == 0 else -10 if which == 2 else 0) * k, base[1] + 26 * k)
        foot = (base[0] + dx * 1.6 + sh, 6)
        knee = (knee[0], max(knee[1], base[1] + 10))
        w = 0.8 if far else 1.0
        shapes = [seg(base, knee, 12 * w, 10 * w), seg(knee, foot, 9 * w, 6 * w)]
        d = 1 if which < 2 else -1
        for t in range(5): shapes.append(seg((foot[0] + d * t * 9, 4), (foot[0] + d * (t + 0.8) * 9, 3), 5 * w, 4 * w))
        return shapes
    mx0 = 0.0
    bases = [(mx0 + ml * 0.35, body_y - 12), (mx0 + ml * 0.02, body_y - 14), (mx0 - ml * 0.32, body_y - 10)]
    for i, b in enumerate(bases):
        for g in leg((b[0] - 8, b[1] + 4), i, far=True): sc.shape(g)
    # gaster and nodes (left)
    nx = -ml * 0.5
    node_shapes = []
    for nidx in range(sp['nodes']):
        nh = 34 if (sp.get('node_big') or nidx == 0) else 26
        node_shapes.append(Polygon(spline([(nx - 2, body_y - 6), (nx - 6, body_y + nh * 0.6), (nx - 16, body_y + nh), (nx - 26, body_y + nh * 0.55), (nx - 28, body_y - 4)], n=6) + [(nx - 2, body_y - 6)]).buffer(0))
        nx -= 26
    ga = math.radians(10 + raise_gaster)
    gcx = nx - gl * 0.9 * math.cos(ga); gcy = body_y + 6 + gl * 0.9 * math.sin(ga) * 0.6
    gas = ell(gcx, gcy, gl, gw * 0.85, -ga * 0.6 if raise_gaster < 30 else -ga * 0.9, 60)
    sc.shape(gas)
    for f in (-0.4, 0.0, 0.4):
        c, s = math.cos(-ga * 0.6), math.sin(-ga * 0.6)
        x = gcx + gl * f * c; y = gcy + gl * f * s
        sc.lines(clip_l([[(x - 30 * s - 2, y - 80), (x + 30 * s + 2, y + 80)]], gas.buffer(-3)))
    for g in node_shapes: sc.shape(g)
    # mesosoma profile
    mp = spline([(ml * 0.5, body_y + 10), (ml * 0.45, body_y + mw * 1.1), (ml * 0.2, body_y + mw * 1.35), (-ml * 0.05, body_y + mw * 1.0), (-ml * 0.25, body_y + mw * 0.95),
                 (-ml * 0.5, body_y + mw * 0.7), (-ml * 0.52, body_y), (ml * 0.1, body_y - 20), (ml * 0.45, body_y - 8)], closed=True, n=8, tension=0.45)
    meso = Polygon(mp).buffer(0); sc.shape(meso)
    sc.lines(clip_l([[(ml * 0.12, body_y + mw * 1.6), (ml * 0.1, body_y - 30)], [(-ml * 0.2, body_y + mw * 1.4), (-ml * 0.22, body_y - 30)]], meso.buffer(-3)))
    if sp['spines']: sc.shape(Polygon([(-ml * 0.42, body_y + mw * 0.8), (-ml * 0.62, body_y + mw * 1.3), (-ml * 0.5, body_y + mw * 0.7)]))
    if wings:
        fw = Polygon(spline([(-ml * 0.0, body_y + mw * 1.2), (-ml * 0.8, body_y + mw * 1.9), (-ml * 2.1, body_y + mw * 2.0), (-ml * 2.4, body_y + mw * 1.6), (-ml * 1.0, body_y + mw * 1.2)], closed=True, n=8, tension=0.4)).buffer(0)
        sc.shape(fw); sc.line([(-ml * 0.1, body_y + mw * 1.3), (-ml * 1.2, body_y + mw * 1.75), (-ml * 2.2, body_y + mw * 1.75)])
    # head
    hcx = ml * 0.5 + rx * 0.78; hcy = body_y + mw * 1.0 + head_up
    hd = ell(hcx, hcy, ry * 0.95, rx * 0.9 if sp['shape'] != 'disc' else rx * 0.5, math.radians(-20 + head_up * 0.3), 40)
    if carry is not None: carry(sc, (hcx + ry * 0.9, hcy - rx * 0.5), sp)
    # mandible
    if sp['mand'] == 'trap':
        sc.shape(seg((hcx + ry * 0.8, hcy - rx * 0.3), (hcx + ry * 2.1, hcy - rx * 0.4), 9, 7))
    elif sp['mand'] in ('bulldog', 'sickle'):
        sc.shape(LineString(spline([(hcx + ry * 0.7, hcy - rx * 0.45), (hcx + ry * 1.4, hcy - rx * 0.6), (hcx + ry * 1.9, hcy - rx * 0.4)], n=8)).buffer(5.5, cap_style=1))
    else:
        sc.shape(Polygon([(hcx + ry * 0.7, hcy - rx * 0.3), (hcx + ry * 1.25, hcy - rx * 0.55), (hcx + ry * 1.15, hcy - rx * 0.75), (hcx + ry * 0.6, hcy - rx * 0.65)]))
    sc.shape(hd)
    if sp['eye'] > 0:
        sc.shape(ell(hcx + ry * 0.1, hcy + rx * 0.15, ry * sp['eye'], rx * sp['eye'] * 0.8, 0, 20))
    # antenna: scape up and forward, funiculus forward and down
    ins = (hcx + ry * 0.55, hcy + rx * 0.35); a_ = sp['ant']
    elbow = (ins[0] - 10 * a_, ins[1] + 70 * a_)
    fun = spline([elbow, (elbow[0] + 70 * a_, elbow[1] + 40 * a_), (elbow[0] + 140 * a_, elbow[1] - 10 * a_)], n=12)
    sc.shape(seg(ins, elbow, 8, 6))
    for t in range(11):
        p_ = fun[int(t * (len(fun) - 1) / 11)]; q_ = fun[int((t + 0.85) * (len(fun) - 1) / 11)]
        sc.shape(seg(p_, q_, 6 if t < 7 else 8, 6 if t < 7 else 8))
    # near legs
    for i, b in enumerate(bases):
        for g in leg(b, i): sc.shape(g)
    return sc

def clip_l(L, g):
    out = []
    for P in L: out += lines_of(LineString(P).intersection(g))
    return out

# ---------------------------------------------------------------- face view
def ant_face(sp):
    sc = Scene(); rx, ry = 200 * sp['head'][0] / 50, 200 * sp['head'][1] / 50
    for s in (-1, 1):
        ins = (s * rx * 0.28, ry * 0.25); elbow = (s * rx * 0.9, ry * 1.25)
        sc.shape(seg(ins, elbow, 26, 22))
        fun = spline([elbow, (s * rx * 1.5, ry * 1.4), (s * rx * 2.0, ry * 0.9)], n=12)
        for t in range(11):
            a_ = fun[int(t * (len(fun) - 1) / 11)]; b_ = fun[int((t + 0.85) * (len(fun) - 1) / 11)]
            sc.shape(seg(a_, b_, 20 if t < 7 else 28, 20 if t < 7 else 28))
    for s in (-1, 1):
        P = [(s * rx * 0.5, -ry * 0.7), (s * rx * 0.55, -ry * 1.2), (s * rx * 0.08, -ry * 1.5), (s * rx * 0.18, -ry * 1.25), (s * rx * 0.1, -ry * 1.15), (s * rx * 0.2, -ry * 1.05), (s * rx * 0.25, -ry * 0.8)]
        sc.shape(Polygon(P).buffer(0))
    h = Polygon(spline([(0, ry * 0.85), (rx * 0.6, ry * 1.0), (rx, ry * 0.4), (rx * 0.95, -ry * 0.4), (rx * 0.55, -ry * 0.85), (0, -ry * 0.9), (-rx * 0.55, -ry * 0.85), (-rx * 0.95, -ry * 0.4), (-rx, ry * 0.4), (-rx * 0.6, ry * 1.0)], closed=True, n=8, tension=0.45)).buffer(0)
    sc.shape(h)
    for s in (-1, 1):
        e = ell(s * rx * 0.88, ry * 0.05, rx * 0.16, ry * 0.3, 0, 30); sc.shape(e)
        for k in range(1, 4): sc.lines(clip_l([[(s * rx * 0.88 - 60, ry * 0.05 - 60 + k * 30), (s * rx * 0.88 + 60, ry * 0.05 - 60 + k * 30)]], e.buffer(-4)))
        sc.line(spline([(s * rx * 0.2, ry * 0.3), (s * rx * 0.25, -ry * 0.2), (s * rx * 0.4, -ry * 0.55)], n=6))
        sc.shape(disc(s * rx * 0.28, ry * 0.25, 18, 16))
    sc.line(spline([(-rx * 0.5, -ry * 0.62), (0, -ry * 0.75), (rx * 0.5, -ry * 0.62)], n=8))
    sc.line([(0, ry * 0.75), (0, ry * 0.1)])
    return sc

# ---------------------------------------------------------------- scenes and props
def place(sc, dx=0.0, dy=0.0, s=1.0, rot=0.0, mirror=False):
    out = Scene()
    for kind, g, fill, outline in sc.items:
        h = g
        if mirror: h = affinity.scale(h, -1, 1, origin=(0, 0))
        if rot: h = affinity.rotate(h, rot, origin=(0, 0))
        if s != 1: h = affinity.scale(h, s, s, origin=(0, 0))
        out.items.append((kind, affinity.translate(h, dx, dy), fill, outline))
    return out

def join(*scs):
    out = Scene()
    for s in scs: out.items += s.items
    return out

def leaf_piece(sc, y, sp):
    P = [(-60, y + 10), (40, y + 20), (130, y + 140), (90, y + 260), (-20, y + 300), (-110, y + 190), (-120, y + 80)]
    g = Polygon(spline(P, closed=True, n=6, tension=0.3)).buffer(0); sc.shape(g)
    sc.lines(clip_l([[(-40, y + 20), (0, y + 160), (40, y + 290)], [(0, y + 160), (90, y + 120)], [(0, y + 160), (-90, y + 200)], [(10, y + 220), (70, y + 230)]], g.buffer(-4)))

def crumb(sc, y, sp):
    g = Polygon([(-50, y + 10), (60, y + 6), (80, y + 90), (20, y + 130), (-60, y + 100)]).buffer(0); sc.shape(g)
    for (x, yy) in ((-10, 50), (30, 80), (-30, 90), (40, 40)): sc.line(circle(x, y + yy, 5, 6))

def seed(sc, y, sp):
    g = ell(0, y + 40, 32, 46); sc.shape(g); sc.line(spline([(0, y + 0), (6, y + 40), (0, y + 84)], n=6))

def sugar(sc, y, sp):
    sc.shape(Polygon([(-50, y + 10), (50, y + 10), (50, y + 110), (-50, y + 110)])); sc.line([(-50, y + 10), (-30, y + 30), (70, y + 30)]); sc.line([(-30, y + 30), (-30, y + 130)])
    sc.shape(Polygon([(-50, y + 110), (50, y + 110), (70, y + 130), (-30, y + 130)])); sc.shape(Polygon([(50, y + 10), (70, y + 30), (70, y + 130), (50, y + 110)]))

def side_leaf(sc, p, sp):
    x, y = p
    g = Polygon(spline([(x, y), (x + 40, y + 100), (x + 10, y + 260), (x - 60, y + 300), (x - 110, y + 200), (x - 60, y + 60)], closed=True, n=6, tension=0.35)).buffer(0)
    sc.shape(g); sc.lines(clip_l([[(x - 10, y + 10), (x - 40, y + 160), (x - 50, y + 290)]], g.buffer(-3)))

def egg_cluster():
    sc = Scene(); r = rng(3)
    for k in range(14):
        a = r.uniform(0, TAU); d = r.uniform(0, 120)
        sc.shape(ell(d * math.cos(a), d * math.sin(a) * 0.8, 22, 32, r.uniform(-0.8, 0.8), 20))
    return sc

def larva(x=0, y=0, s=1.0):
    """A C-shaped grub with segment lines and a small head."""
    sc = Scene()
    spine = [(70 * math.cos(a), 70 * math.sin(a)) for a in np.linspace(math.radians(200), math.radians(-60), 30)]
    g = LineString(spine).buffer(38, cap_style=1); sc.shape(g)
    for k in range(1, 9):
        a = math.radians(200) + (math.radians(-60) - math.radians(200)) * k / 9
        c, s_ = math.cos(a), math.sin(a)
        sc.lines(clip_l([[(c * 20, s_ * 20), (c * 120, s_ * 120)]], g.buffer(-4)))
    hx, hy = 70 * math.cos(math.radians(-60)), 70 * math.sin(math.radians(-60))
    sc.shape(disc(hx + 20, hy - 25, 22, 16))
    return place(sc, x, y, s)

def pupa(x=0, y=0, s=1.0, cocoon=True):
    sc = Scene()
    g = ell(0, 0, 60, 130, 0, 40); sc.shape(g)
    if cocoon:
        sc.lines(clip_l([[(-60, -60), (60, -40)], [(-60, 10), (60, 30)], [(-60, 70), (60, 80)]], g.buffer(-4)))
        sc.shape(disc(0, -128, 10, 10))
    else:
        sc.lines(clip_l([[(-40, 60), (40, 60)], [(-50, 20), (50, 20)], [(0, 130), (0, -130)]], g.buffer(-4)))
    return place(sc, x, y, s)

def tunnel_scene():
    """An ant colony in cross-section: ground with grass, tunnels and chambers with ants and brood."""
    sc = Scene(); W = 1200
    soil = box(-W / 2, -700, W / 2, 0)
    tunnels = [LineString(spline([(-60, 0), (-80, -150), (-260, -260), (-300, -430), (-180, -560)], n=10)).buffer(26),
               LineString(spline([(-80, -150), (100, -230), (260, -380), (380, -520)], n=10)).buffer(24),
               LineString(spline([(260, -380), (120, -500), (-40, -560)], n=10)).buffer(22)]
    chambers = [ell(-300, -300, 120, 60), ell(130, -240, 110, 52), ell(-120, -580, 130, 58), ell(400, -560, 120, 56)]
    holes = unary_union(tunnels + chambers)
    soil_g = soil.difference(holes)
    sc.shape(soil_g)
    r = rng(9)
    for k in range(60):
        x, y = r.uniform(-W / 2 + 20, W / 2 - 20), r.uniform(-680, -20)
        if not holes.buffer(20).contains(Point(x, y)): sc.line(circle(x, y, r.uniform(3, 7), 8))
    for k in range(40):
        x = -W / 2 + k * 30 + r.uniform(-6, 6); h = r.uniform(30, 70)
        sc.line([(x, 0), (x + r.uniform(-14, 14), h)])
    sm = SPECIES['garden']
    for (x, y, a) in ((-300, -300, 90), (130, -240, -80), (-180, -560, 60)):
        sc.items += place(ant_top(sm, simple=True), x, y, 0.32, a).items
    for (x, y) in ((-160, -580), (-100, -560), (-60, -590)): sc.items += pupa(x, y, 0.28).items
    for (x, y) in ((360, -560), (420, -545), (450, -575)): sc.items += larva(x, y, 0.4).items
    for (x, y) in ((70, -250), (110, -230), (160, -255)): sc.shape(ell(x, y, 8, 12))
    return sc

def anthill():
    sc = Scene(); r = rng(4)
    mound = Polygon(spline([(-500, 0), (-320, 120), (-120, 260), (0, 290), (130, 255), (330, 110), (500, 0)], n=10) + [(500, -10), (-500, -10)]).buffer(0)
    sc.shape(mound)
    for k in range(140):
        x = r.uniform(-450, 450); y = r.uniform(5, 280)
        if mound.buffer(-12).contains(Point(x, y)):
            a = r.uniform(0, math.pi); L = r.uniform(10, 26)
            sc.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))])
    sc.shape(ell(10, 286, 40, 14))
    sm = SPECIES['wood']
    for (x, y, a) in ((-200, 150, 30), (180, 140, -40), (40, 210, 10)):
        sc.items += place(ant_top(sm, simple=True), x, y, 0.22, a).items
    sc.line([(-560, 0), (560, 0)])
    return sc

def trail_twig(n=4):
    sc = Scene()
    twig = LineString(spline([(-600, -40), (-200, 10), (200, -10), (600, 30)], n=12)).buffer(30)
    sc.shape(twig)
    sc.shape(LineString([(-100, 0), (-180, -160)]).buffer(16)); sc.shape(LineString([(300, 0), (380, 170)]).buffer(14))
    sm = SPECIES['garden']
    for i in range(n):
        x = -450 + i * 300
        sc.items += place(ant_top(sm, phase=i * 0.5, simple=True), x, 0, 0.28, -90).items
    return sc

def line_of_ants(sp, n=5, wavy=True):
    sc = Scene()
    for i in range(n):
        x = -500 + i * 250; y = 60 * math.sin(i * 1.2) if wavy else 0
        sc.items += place(ant_top(sp, phase=i * 0.5, simple=True), x, y, 0.42, -90 + (10 if i % 2 else -10)).items
    return sc

def two_ants_touching():
    sm = SPECIES['wood']
    a = place(ant_top(sm, ant_pose=0.4, simple=True), -260, 0, 0.6, -70)
    b = place(ant_top(sm, ant_pose=0.4, phase=0.5, simple=True), 260, 0, 0.6, 70)
    return join(a, b)

def ant_bridge():
    sc = Scene()
    for s in (-1, 1): sc.shape(Polygon([(s * 330, -300), (s * 700, -300), (s * 700, 40), (s * 330, 40)]))
    sm = SPECIES['weaver']
    for i in range(4):
        x = -270 + i * 180
        sc.items += place(ant_top(sm, phase=i * 0.5, simple=True), x, 40 - 30 * math.sin(math.pi * (i + 0.5) / 4), 0.36, -90).items
    sc.items += place(ant_top(sm, simple=True), 540, 120, 0.3, -100).items
    return sc

def ant_on_leaf():
    sc = Scene()
    leaf = Polygon(spline([(-600, 0), (-300, 200), (200, 220), (600, 0), (200, -220), (-300, -200)], closed=True, n=10, tension=0.4)).buffer(0)
    sc.shape(leaf); sc.line([(-640, 0), (560, 0)])
    for x in range(-400, 500, 160):
        sc.lines(clip_l([[(x, 0), (x + 120, 180)], [(x, 0), (x + 120, -180)]], leaf.buffer(-10)))
    sc.items += place(ant_top(SPECIES['garden']), 120, 60, 0.5, -60).items
    return sc

def dew_drop():
    sc = Scene()
    sc.shape(Polygon([(-700, -80), (700, -80), (700, -40), (-700, -40)]))
    sc.shape(Polygon(spline([(-120, -40), (-130, 60), (-60, 150), (60, 150), (130, 60), (120, -40)], n=10) + [(-120, -40)]))
    sc.line(spline([(-70, 60), (-50, 110), (-10, 128)], n=6)); sc.line(circle(40, 110, 10, 10))
    sc.items += place(ant_side(SPECIES['garden']), 300, -40, 0.8, 0, True).items
    return sc

def ant_farm():
    sc = Scene()
    frame = Polygon([(-500, -400), (500, -400), (500, 400), (-500, 400)])
    inner = Polygon([(-460, -360), (460, -360), (460, 300), (-460, 300)])
    sc.shape(frame.difference(inner))
    sand = Polygon([(-460, -360), (460, -360), (460, 200), (300, 220), (0, 190), (-300, 230), (-460, 200)])
    tunnels = unary_union([LineString(spline([(-200, 210), (-220, 0), (-100, -150), (60, -260)], n=10)).buffer(22), LineString(spline([(240, 200), (200, 40), (60, -60), (-100, -150)], n=10)).buffer(20),
                           ell(60, -260, 90, 44), ell(200, 40, 70, 36)])
    sc.shape(sand.difference(tunnels))
    for (x, y, a) in ((-210, 60, 10), (60, -260, 90), (190, 40, -60)): sc.items += place(ant_top(SPECIES['garden'], simple=True), x, y, 0.26, a).items
    sc.shape(Polygon([(-520, 400), (520, 400), (520, 440), (-520, 440)]))
    return sc

def life_cycle():
    sc = Scene()
    sc.items += place(egg_cluster(), -380, 280, 0.5).items
    sc.items += larva(380, 280, 1.2).items
    sc.items += pupa(380, -260, 1.0).items
    sc.items += place(ant_top(SPECIES['garden'], simple=True), -380, -260, 0.45, 0).items
    for (a, b) in (((-220, 300), (220, 300)), ((400, 160), (400, -100)), ((220, -280), (-220, -280)), ((-400, -100), (-400, 160))):
        sc.line([a, b]); d = (b[0] - a[0], b[1] - a[1]); L = math.hypot(*d); u = (d[0] / L, d[1] / L)
        sc.line([(b[0] - u[0] * 30 - u[1] * 16, b[1] - u[1] * 30 + u[0] * 16), b, (b[0] - u[0] * 30 + u[1] * 16, b[1] - u[1] * 30 - u[0] * 16)])
    return sc

def cartoon_ant():
    sc = Scene()
    for (a, b, c) in (((-60, -40), (-150, -150), (-170, -250)), ((60, -40), (150, -150), (130, -250)), ((-40, 120), (-160, 60), (-260, 120))):
        sc.shape(seg(a, b, 18)); sc.shape(seg(b, c, 16)); sc.shape(ell(c[0], c[1] - 8, 26, 14))
    sc.shape(seg((40, 120), (150, 230), 18)); sc.shape(seg((150, 230), (180, 350), 16)); sc.shape(disc(185, 362, 22))
    sc.shape(ell(-30, -140, 110, 130, 0.3, 50))
    sc.shape(ell(0, 30, 70, 80, 0.1, 40))
    for s in (-1, 1): sc.shape(seg((s * 30, 380), (s * 90, 520), 10)); sc.shape(disc(s * 95, 530, 20))
    h = ell(0, 290, 140, 120, 0, 60); sc.shape(h)
    for s in (-1, 1):
        sc.shape(ell(s * 50, 310, 40, 52, 0, 30)); sc.shape(disc(s * 50 + 10, 300, 18)); sc.line(circle(s * 50 + 16, 312, 6, 8))
    sc.line(spline([(-60, 230), (0, 200), (60, 230)], n=8))
    return sc

def silhouette(sp):
    return ant_top(sp)

def ants_items():
    A = []
    def add_(name, sc, slug): A.append((name, flipL(sc.render()), slug))
    S = SPECIES
    add_('Black garden ant', ant_top(S['garden']), 'black-garden-ant')
    add_('Carpenter ant', place(ant_top(S['carpenter'], phase=0.4), 0, 0, 1, -35), 'carpenter-ant')
    add_('Red wood ant', place(ant_top(S['wood'], phase=0.8, ant_pose=0.5), 0, 0, 1, 50), 'red-wood-ant')
    add_('Fire ant', place(ant_top(S['fire'], phase=0.2), 0, 0, 1, -90), 'fire-ant')
    add_('Leafcutter ant carrying a leaf', ant_top(S['leafcutter'], carry=leaf_piece, phase=0.3), 'leafcutter-carrying-leaf')
    add_('Army ant with sickle jaws', ant_top(S['army'], phase=0.6), 'army-ant')
    add_('Bullet ant', place(ant_top(S['bullet'], phase=0.1), 0, 0, 1, 20), 'bullet-ant')
    add_('Trap-jaw ant', ant_top(S['trapjaw'], mand_open=0.6), 'trap-jaw-ant')
    add_('Bulldog ant', ant_top(S['bulldog'], phase=0.5), 'bulldog-ant')
    add_('Weaver ant', place(ant_top(S['weaver'], phase=0.3), 0, 0, 1, 90), 'weaver-ant')
    add_('Honeypot ant', ant_top(S['honeypot']), 'honeypot-ant')
    add_('Harvester ant with a seed', ant_top(S['harvester'], carry=seed), 'harvester-ant-seed')
    add_('Crazy ant with long legs', ant_top(S['crazy'], phase=0.7), 'crazy-ant')
    add_('Acrobat ant', ant_top(S['acrobat']), 'acrobat-ant')
    add_('Turtle ant', ant_top(S['turtle']), 'turtle-ant')
    add_('Desert ant', place(ant_top(S['desert'], phase=0.4), 0, 0, 1, -60), 'desert-ant')
    add_('Soldier ant with a big head', ant_top(S['soldier']), 'soldier-ant')
    add_('Queen ant with wings', ant_top(S['queen'], wings=True), 'queen-ant-wings')
    add_('Winged male ant', ant_top(dict(S['pharaoh'], head=(34, 38), gaster=(40, 60), meso=(30, 120)), wings=True), 'winged-male-ant')
    add_('Pharaoh ants', join(place(ant_top(S['pharaoh'], phase=0.9, simple=True), -260, 0, 0.6, 20), place(ant_top(S['pharaoh'], phase=0.3, simple=True), 220, 80, 0.6, -30)), 'pharaoh-ants')
    add_('Argentine ant', place(ant_top(S['argentine'], phase=0.2), 0, 0, 1, 130), 'argentine-ant')
    add_('Worker ant from the side', ant_side(S['garden']), 'worker-ant-side')
    add_('Carpenter ant from the side', ant_side(S['carpenter'], phase=0.5), 'carpenter-ant-side')
    add_('Fire ant from the side', ant_side(S['fire'], phase=0.3), 'fire-ant-side')
    add_('Bulldog ant from the side', ant_side(S['bulldog'], phase=0.6), 'bulldog-ant-side')
    add_('Trap-jaw ant from the side', ant_side(S['trapjaw']), 'trap-jaw-ant-side')
    add_('Acrobat ant raising its gaster', ant_side(S['acrobat'], raise_gaster=55), 'acrobat-ant-side')
    add_('Desert ant running', ant_side(S['desert'], phase=0.8, raise_gaster=25), 'desert-ant-side')
    add_('Queen ant from the side', ant_side(S['queen'], wings=True), 'queen-ant-side')
    add_('Leafcutter ant with a leaf, side view', ant_side(S['leafcutter'], carry=lambda sc, p, sp: side_leaf(sc, p, sp), head_up=20), 'leafcutter-side')
    add_('Honeypot ant from the side', ant_side(S['honeypot']), 'honeypot-ant-side')
    add_('Ant face close-up', ant_face(S['wood']), 'ant-face')
    add_('Soldier ant face', ant_face(dict(S['soldier'], head=(70, 66))), 'soldier-ant-face')
    add_('Ant eggs', egg_cluster(), 'ant-eggs')
    add_('Ant larva', larva(0, 0, 3), 'ant-larva')
    add_('Ant cocoon', pupa(0, 0, 3), 'ant-cocoon')
    add_('Ant pupa', pupa(0, 0, 3, cocoon=False), 'ant-pupa')
    add_('Ant life cycle', life_cycle(), 'ant-life-cycle')
    add_('Ant colony underground', tunnel_scene(), 'ant-colony')
    add_('Anthill', anthill(), 'anthill')
    add_('Ant trail along a twig', trail_twig(), 'ant-trail-twig')
    add_('Ants marching in a line', line_of_ants(S['army'], 5), 'ants-marching')
    add_('Two ants touching antennae', two_ants_touching(), 'ants-touching-antennae')
    add_('Ant carrying a crumb', ant_top(S['garden'], carry=crumb), 'ant-carrying-crumb')
    add_('Ant carrying a sugar cube', ant_top(S['argentine'], carry=sugar), 'ant-sugar-cube')
    add_('Weaver ants forming a bridge', ant_bridge(), 'ant-bridge')
    add_('Ant on a leaf', ant_on_leaf(), 'ant-on-a-leaf')
    add_('Ant drinking a dew drop', dew_drop(), 'ant-dew-drop')
    add_('Ant farm', ant_farm(), 'ant-farm')
    add_('Cartoon ant waving', cartoon_ant(), 'cartoon-ant')
    parts = [g for kind, g, fill, outline in ant_top(S['carpenter'], simple=True).items if kind == 'shape']
    sil = Scene(); sil.shape(unary_union([g.buffer(3) for g in parts]))
    add_('Ant silhouette', sil, 'ant-silhouette')
    add_('Ants of three sizes', join(place(ant_top(S['soldier'], simple=True), -420, 0, 0.6), place(ant_top(S['garden'], simple=True), 0, 0, 0.6), place(ant_top(S['pharaoh'], simple=True), 330, 0, 0.45)), 'ants-three-sizes')
    return A

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    items = []
    for name, L, slug in ants_items():
        it = Item('ants', name, L); it.slug = slug; items.append(it)
    save(items, OUT)
    P = sorted(export_size(i.lines)[0] for i in items)
    print(len(items), 'ants; median', P[len(P) // 2], 'max', P[-1])
    if SHEET:
        for i in range(0, len(items), 30):
            sheet(items[i:i + 30], SHEET.replace('.png', f'_{i // 30}.png'), cols=6, cell=2.6)
