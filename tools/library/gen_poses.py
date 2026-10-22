"""Poses: clothed, articulated figures in everyday, sport, work and leisure poses, front and side views.
Each figure is built from a skeleton (absolute limb angles in degrees: 0 = right, 90 = up, -90 = down),
limbs are chains of discs, clothes are shapes over the limbs, and a painter's scene hides what is behind.
Side views face right (mirror=True flips them). Drawn y-up, flipped at the end.
Usage: python3 -I gen_poses.py <out.json> [sheet.png]"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from shapely.geometry import Polygon, LineString, Point, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

R_ = math.radians
def V(a, L=1.0): return (math.cos(R_(a)) * L, math.sin(R_(a)) * L)
def ad(p, q, k=1.0): return (p[0] + q[0] * k, p[1] + q[1] * k)
def mid(p, q, t=0.5): return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
def P_(pts): return Polygon(pts).buffer(0)
def flipL(L): return [[(x, -y) for x, y in P] for P in L]
def disc(p, r): return Point(p).buffer(r, 16)

def chain(pts):
    """[(point, radius), ...] -> union of the hulls of consecutive discs (a smooth tapered limb)."""
    parts = [unary_union([disc(p, r), disc(q, s)]).convex_hull for (p, r), (q, s) in zip(pts, pts[1:])]
    return unary_union(parts)

def frame(origin, ang):
    """Local frame: v along the axis at `ang`, u to the right of it (forward for an upright side view)."""
    ax = V(ang); px = (ax[1], -ax[0])
    def f(u, v): return (origin[0] + px[0] * u + ax[0] * v, origin[1] + px[1] * u + ax[1] * v)
    return f
def loc(origin, ang, pts):
    f = frame(origin, ang); return [f(u, v) for u, v in pts]

def ell(c, rx, ry, ang=90, n=40):
    """Ellipse with ry along the axis `ang`."""
    return Polygon(loc(c, ang, [(rx * math.cos(t), ry * math.sin(t)) for t in [i * 2 * math.pi / n for i in range(n)]]))

BODY = {
    'm': dict(T=312, sw=94, hw=58, UA=165, FA=150, TH=248, SH=236, neck=50, hrx=50, hry=64, hip=0.55,
              ua=(28, 25, 21), fa=(22, 22, 16), th=(43, 40, 30), sh=(30, 32, 18)),
    'f': dict(T=300, sw=82, hw=66, UA=158, FA=142, TH=244, SH=230, neck=50, hrx=46, hry=61, hip=0.58,
              ua=(23, 20, 17), fa=(18, 18, 13), th=(46, 40, 27), sh=(27, 29, 15)),
}

def ik(root, target, L1, L2, bend=1):
    """Two-bone reach: angles (degrees) of the two segments from root to target; bend picks the side of the joint."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = max(1e-6, min(math.hypot(dx, dy), L1 + L2 - 1e-3))
    a = math.atan2(dy, dx)
    A = math.acos(max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    a1 = a + bend * A
    j = (root[0] + L1 * math.cos(a1), root[1] + L1 * math.sin(a1))
    a2 = math.atan2(target[1] - j[1], target[0] - j[0])
    return math.degrees(a1), math.degrees(a2)

def halfplane(origin, ang, off):
    """Everything beyond `off` along the direction `ang` from `origin`."""
    return P_(loc(origin, ang - 90, [(-off, -400), (-off, 400), (-off - 900, 400), (-off - 900, -400)])) if False else \
        P_(loc(origin, ang, [(-600, off), (600, off), (600, off + 900), (-600, off + 900)]))

# ---------------------------------------------------------------- the figure
class Figure:
    def __init__(self, p):
        self.p = p
        self.kind = p.get('kind', 'm'); B = self.B = dict(BODY[self.kind])
        self.view = p.get('view', 'F')
        self.top = p.get('top', 'tee'); self.bottom = p.get('bottom', 'trousers' if self.kind == 'm' else 'skirt')
        self.hair = p.get('hair', 'short' if self.kind == 'm' else 'bob')
        self.near = p.get('near', 'R')
        self.layers = {k: [] for k in ('back', 'between', 'hair_back', 'armL', 'armR', 'legL', 'legR', 'pelvis', 'skirt', 'neck', 'torso', 'head', 'hair', 'mid', 'front')}
        self.leg_geom, self.short_pieces = [], []
        self.joints()

    # ------------------------------------------------ skeleton
    def joints(self):
        p, B = self.p, self.B
        k = p.get('k', {})
        J = self.J = {}
        H = J['H'] = (0.0, 0.0)
        ta = self.ta = p.get('torso', 90)
        N = J['N'] = ad(H, V(ta, B['T']))
        f = frame(H, ta)
        if self.view == 'F':
            J['SL'], J['SR'] = f(-B['sw'] + 6, B['T'] - 34), f(B['sw'] - 6, B['T'] - 34)
            J['HL'], J['HR'] = f(-B['hw'] * B['hip'], -8), f(B['hw'] * B['hip'], -8)
        else:
            J['SL'] = J['SR'] = f(-4, B['T'] - 36)
            J['HL'] = J['HR'] = f(4, -6)
        ha = self.ha = p.get('head', ta)
        J['Ntop'] = ad(N, V(ha, B['neck']))
        J['C'] = ad(J['Ntop'], V(ha, B['hry'] - 6))
        for s in 'LR':
            a = p['arms'][s]
            if a[0] == 'ik':                      # ('ik', target, bend, hand angle)
                ua, fa = ik(J['S' + s], a[1], B['UA'] * k.get('ua' + s, 1.0), B['FA'] * k.get('fa' + s, 1.0), a[2])
                a = (ua, fa) + tuple(a[3:]); p['arms'][s] = a
            l = p['legs'][s]
            if l[0] == 'ik':
                th, sh = ik(J['H' + s], l[1], B['TH'] * k.get('th' + s, 1.0), B['SH'] * k.get('sh' + s, 1.0), l[2])
                p['legs'][s] = (th, sh) + tuple(l[3:])
        for s in 'LR':
            ua, fa, *rest = p['arms'][s]
            hand = rest[0] if rest else fa
            J['E' + s] = ad(J['S' + s], V(ua, B['UA'] * k.get('ua' + s, 1.0)))
            J['W' + s] = ad(J['E' + s], V(fa, B['FA'] * k.get('fa' + s, 1.0)))
            J['ha' + s] = hand
            J['P' + s] = ad(J['W' + s], V(hand, 36))      # palm centre
            th, sh, *rest = p['legs'][s]
            J['K' + s] = ad(J['H' + s], V(th, B['TH'] * k.get('th' + s, 1.0)))
            J['A' + s] = ad(J['K' + s], V(sh, B['SH'] * k.get('sh' + s, 1.0)))
            J['fa' + s] = rest[0] if rest else 0
            J['T' + s] = ad(J['A' + s], V(J['fa' + s], 95))   # toe

    # ------------------------------------------------ legs and feet
    def leg(self, s):
        B, J = self.B, self.J
        Hp, K, A = J['H' + s], J['K' + s], J['A' + s]
        tr = self.bottom in ('trousers', 'jeans')
        th, sh = B['th'], B['sh']
        if tr:
            th = (th[0] + 8, th[1] + 8, th[2] + 8); sh = (sh[0] + 7, sh[0] + 6, sh[0] + 3)
        g = chain([(Hp, th[0]), (mid(Hp, K, 0.42), th[1]), (K, th[2])]).union(chain([(K, sh[0]), (mid(K, A, 0.3), sh[1]), (A, sh[2])]))
        shoe = self.shoe(s)
        sa = self.p['legs'][s][1]
        out = []
        if tr:
            g = g.difference(halfplane(A, sa, 6))
            out += [('shape', shoe), ('shape', g)]
        else:
            out += [('shape', g)]
            if self.bottom == 'leggings':
                c = mid(K, A, 0.84); d = V(sa + 90)
                out += [('line', [ad(c, d, -44), ad(c, d, 44)], g)]
            out += [('shape', shoe)]
        if self.bottom == 'shorts':
            tha = self.p['legs'][s][0]
            piece = chain([(ad(Hp, V(tha, -30)), th[0] + 8), (mid(Hp, K, 0.5), th[1] + 8)]).difference(halfplane(Hp, tha, B['TH'] * 0.42))
            out += [('shape', piece)]
            self.short_pieces.append(piece)
        self.layers['leg' + s] += out
        self.leg_geom.append(g)

    def shoe(self, s):
        J = self.J; A = J['A' + s]
        heel = self.p.get('heels') and self.kind == 'f'
        fs = self.p.get('feet_side', {})
        if self.view == 'F' and not fs.get(s):
            sx = -1 if s == 'L' else 1
            sa = self.p['legs'][s][1] + 90
            pts = [(-20, 8), (-28, -14), (-30, -34), (-20, -46), (20, -46), (30, -34), (28, -14), (20, 8)]
            pts = [(u + sx * 9, v) for u, v in pts]
            return P_(loc(A, sa, pts))
        fa = J['fa' + s]
        sgn = 1
        if self.view == 'F': sgn = fs.get(s)
        if heel:
            pts = [(-20, 12), (-26, -16), (-22, -40), (-16, -52), (-10, -52), (-8, -34), (40, -42), (78, -48), (90, -42), (84, -30), (44, -16), (14, 4), (-6, 14)]
        else:
            pts = [(-22, 12), (-30, -16), (-30, -40), (-20, -50), (66, -50), (92, -46), (100, -34), (92, -22), (50, -12), (16, 6), (-6, 16)]
        return P_(loc(A, fa + 90, [(u * sgn, v) for u, v in pts]) if sgn == 1 else loc(A, fa - 90, [(-u, v) for u, v in pts]))

    # ------------------------------------------------ arms and hands
    def arm(self, s):
        B, J = self.B, self.J
        S, E, W = J['S' + s], J['E' + s], J['W' + s]
        hk = self.p.get('hands', {}).get(s, 'open')
        hand = self.hand(s, hk)
        long_ = self.top in ('long', 'jacket', 'coat', 'shirt')
        ua, fa = B['ua'], B['fa']
        if long_:
            ua = (ua[0] + 6, ua[1] + 7, ua[2] + 7); fa = (fa[0] + 7, fa[1] + 7, fa[2] + 8)
        g = chain([(S, ua[0]), (mid(S, E, 0.4), ua[1]), (E, ua[2])]).union(chain([(E, fa[0]), (mid(E, W, 0.25), fa[1]), (W, fa[2])]))
        fang = self.p['arms'][s][1]
        out = []
        if long_:
            g = g.difference(halfplane(W, fang, -4))
            out += [('shape', hand), ('shape', g)]
        else:
            out += [('shape', g.union(hand))]
            if self.top in ('tee', 'polo', 'tee_f', 'dress_s'):
                uang = self.p['arms'][s][0]
                sl = chain([(ad(S, V(uang, -14)), ua[0] + 6), (mid(S, E, 0.48), ua[1] + 6)]).difference(halfplane(S, uang, B['UA'] * 0.45))
                out += [('shape', sl)]
        self.layers['arm' + s] += out

    def hand(self, s, kind):
        J = self.J; W, a = J['W' + s], J['ha' + s]
        k = 0.92 if self.kind == 'f' else 1.0
        if kind == 'none':
            return Polygon()
        if kind == 'fist':
            return disc(ad(W, V(a, 18 * k)), 23 * k)
        if kind == 'glove':
            return disc(ad(W, V(a, 26)), 34)
        if kind == 'point':
            fist = disc(ad(W, V(a, 16 * k)), 21 * k)
            return fist.union(chain([(ad(W, V(a, 24 * k)), 8), (ad(W, V(a, 70 * k)), 7)]))
        thumb = self.p.get('thumb', {}).get(s, 1 if s == 'R' else -1)
        if kind == 'flat':
            return ell(ad(W, V(a, 36 * k)), 13 * k, 42 * k, a).union(disc(W, 15 * k))
        palm = ell(ad(W, V(a, 36 * k)), 20 * k, 40 * k, a)
        th = ell(ad(ad(W, V(a, 22 * k)), V(a - 90 * thumb, 15 * k)), 8 * k, 19 * k, a - 35 * thumb)
        return palm.union(th).union(disc(W, 15 * k))

    # ------------------------------------------------ hips, skirt
    def pelvis(self):
        B, J = self.B, self.J
        f = frame(J['H'], self.ta)
        add_ = 8 if self.bottom in ('trousers', 'jeans') else 2
        if self.view == 'F':
            pel = unary_union([disc(J['HL'], B['th'][0] + add_), disc(J['HR'], B['th'][0] + add_), disc(f(0, -50), 24),
                               disc(f(-B['hw'] - 4, 24), 14), disc(f(B['hw'] + 4, 24), 14)]).convex_hull
        else:
            r = 38 if self.kind == 'm' else 44
            pel = unary_union([disc(f(6, -6), B['th'][0] + add_), disc(f(-18, -6), r), disc(f(22, 18), 32), disc(f(-20, 26), 32)]).convex_hull
        self.pel = pel
        if self.bottom in ('trousers', 'jeans', 'leggings'):
            legs = unary_union(self.leg_geom + [pel])
            self.layers['pelvis'] += [('cut', pel), ('lines', lines_of(legs.boundary.intersection(pel.buffer(1))))]
        elif self.bottom == 'shorts':
            g = unary_union(self.short_pieces + [pel])
            self.layers['pelvis'] += [('cut', pel), ('lines', lines_of(g.boundary.intersection(pel.buffer(1))))]
        else:
            self.layers['pelvis'] += [('shape', pel)]
        if self.bottom == 'skirt' or self.top == 'dress':
            L = self.p.get('skirt', 0.86)
            flare = self.p.get('flare', 26)
            pts = [f(-B['hw'] + 2, 60), f(B['hw'] - 2, 60), f(-B['hw'] - 6, 10), f(B['hw'] + 6, 10)]
            for s in 'LR':
                Hp, K, A = J['H' + s], J['K' + s], J['A' + s]
                if L <= 1.0: c, ang = mid(Hp, K, L), self.p['legs'][s][0]
                else: c, ang = mid(K, A, L - 1.0), self.p['legs'][s][1]
                w = B['th'][2] + flare + (L - 0.5) * 30
                pts += [ad(c, V(ang + 90, w)), ad(c, V(ang - 90, w))]
            sk = MultiPolygon([P_([q, ad(q, (1, 0)), ad(q, (0, 1))]) for q in pts]).convex_hull.buffer(14, join_style=1).buffer(-14, join_style=1)
            self.layers['skirt'] += [('shape', sk)]
            self.skirt_g = sk

    # ------------------------------------------------ torso and clothes
    def torso(self):
        B, J, k = self.B, self.J, self.kind
        T, sw, hw = B['T'], B['sw'], B['hw']
        hem = -24 if self.top not in ('jacket', 'coat') else -80
        f = frame(J['H'], self.ta)
        if self.view == 'F':
            if k == 'm':
                half = [(0, T + 2), (24, T + 4), (62, T - 6), (sw + 2, T - 24), (sw + 4, T - 70), (sw - 8, T - 112), (sw - 12, T - 160),
                        (sw - 26, 70), (hw + 18, 0), (hw + 24, hem)]
            else:
                half = [(0, T + 2), (22, T + 4), (56, T - 6), (sw + 2, T - 24), (sw + 2, T - 66), (sw - 6, T - 104), (sw - 2, T - 140),
                        (sw - 22, 92), (hw + 6, 16), (hw + 20, hem)]
            if self.top == 'dress': half[-2:] = [(hw - 6, 50), (hw - 4, 40)]
            pts = half + [(-u, v) for u, v in half[::-1]]
            g = P_(loc(J['H'], self.ta, pts))
            out = [('shape', g)]
            nl = self.p.get('neck_line', 'v' if self.top in ('jacket', 'coat', 'shirt') else 'crew')
            if nl == 'crew':
                out += [('line', [f(-24, T + 4), f(-14, T - 12), f(0, T - 16), f(14, T - 12), f(24, T + 4)], None)]
            else:
                out += [('line', [f(-24, T + 4), f(0, T - 64), f(24, T + 4)], None)]
            if self.top in ('jacket', 'coat'):
                out += [('line', [f(0, T - 64), f(0, hem + 2)], g), ('line', [f(-24, T + 4), f(-44, T - 34), f(-4, T - 120)], g),
                        ('line', [f(24, T + 4), f(44, T - 34), f(4, T - 120)], g)]
                for v in (T - 170, T - 230): out += [('shape', disc(f(-10, v), 5))]
            elif self.top == 'shirt':
                out += [('line', [f(0, T - 64), f(0, hem + 2)], g)]
                for v in (T - 110, T - 170, T - 230): out += [('shape', disc(f(-8, v), 4))]
        else:
            if k == 'm':
                pts = [(-22, T + 8), (-46, T - 20), (-58, T - 90), (-55, T - 170), (-44, 70), (-50, 10), (-56, hem), (48, hem), (46, 30),
                       (42, 90), (50, 160), (57, T - 80), (44, T - 22), (26, T + 6)]
            else:
                pts = [(-20, T + 6), (-42, T - 18), (-50, T - 85), (-44, T - 150), (-34, 96), (-52, 30), (-58, hem), (46, hem), (42, 40),
                       (32, 100), (46, 150), (62, 192), (56, T - 60), (40, T - 18), (22, T + 4)]
            if self.top == 'dress': pts[5:8] = [(-46, 56), (-44, 40), (38, 40)]
            g = P_(loc(J['H'], self.ta, pts))
            out = [('shape', g), ('line', [f(24, T + 4), f(16, T - 12), f(2, T - 6)], g)]
            if self.top in ('jacket', 'coat'):
                out += [('line', [f(22, T - 10), f(38, T - 120), f(46, hem + 10)], g)]
        if self.p.get('belt'):
            band_ = P_(loc(J['H'], self.ta, [(-300, 34), (300, 34), (300, 58), (-300, 58)])).intersection(g)
            out += [('shape', band_)]
            if self.view == 'F':
                out += [('shape', P_(loc(J['H'], self.ta, [(-12, 34), (12, 34), (30, -30), (14, -32), (0, 30), (-14, -32), (-30, -30)])))]
        self.layers['torso'] += out
        self.torso_g = g
        if self.p.get('backpack'):
            if self.view == 'S':
                bp = P_(loc(J['H'], self.ta, [(-44, T - 34), (-98, T - 44), (-122, T - 100), (-124, 110), (-108, 56), (-46, 52)]))
                self.layers['torso'] += [('shape', bp), ('line', loc(J['H'], self.ta, [(-64, T - 160), (-118, T - 160)]), bp),
                                         ('line', loc(J['H'], self.ta, [(14, T - 18), (-12, T - 150), (-30, 100)]), g)]
            else:
                for sx in (-1, 1):
                    self.layers['torso'] += [('line', loc(J['H'], self.ta, [(sx * 40, T - 2), (sx * 48, T - 150), (sx * 60, 110)]), g)]

    def head(self):
        B, J = self.B, self.J
        C, N, Nt = J['C'], J['N'], J['Ntop']
        rx, ry = B['hrx'], B['hry']
        neck = chain([(ad(N, V(self.ha, -20)), 24 if self.kind == 'm' else 20), (ad(Nt, V(self.ha, 8)), 22 if self.kind == 'm' else 18)])
        self.layers['neck'] += [('shape', neck)]
        f = frame(C, self.ha)
        if self.view == 'F':
            hd = ell(C, rx, ry, self.ha)
            if self.hair in ('short', 'bald', 'buzz') and not self.p.get('hat') == 'helmet':
                self.layers['head'] += [('shape', ell(f(sx * (rx - 2), -4), 9, 17, self.ha)) for sx in (-1, 1)]
            self.layers['head'] += [('shape', hd)]
        else:
            hd = ell(f(-4, 0), rx * 1.06, ry, self.ha)
            nose = P_([f(rx * 0.86, 14), f(rx + 13, -14), f(rx * 0.86, -22)])
            chin = disc(f(rx * 0.52, -ry * 0.7), 18)
            hd = unary_union([hd, nose, chin])
            self.layers['head'] += [('shape', hd), ('line', spline([f(-8, 8), f(-16, 4), f(-17, -14), f(-8, -22)], n=6), None)]
        self.head_g = hd
        self.hair_parts()

    def hair_parts(self):
        B, J = self.B, self.J
        C = J['C']; rx, ry = B['hrx'], B['hry']; f = frame(C, self.ha)
        st = self.hair
        if st == 'bald': return
        big = ell(f(0, 6), rx + 7, ry + 6, self.ha)
        if self.view == 'F':
            if st in ('short', 'buzz'):
                hl = P_(loc(C, self.ha, [(-rx - 12, -16), (-rx + 6, 10), (-rx * 0.45, 30), (0, 28), (rx * 0.5, 36), (rx - 6, 14), (rx + 12, -16), (rx + 60, 300), (-rx - 60, 300)]))
                cap = big.intersection(hl)
                self.layers['hair'] += [('shape', cap), ('line', spline([f(-rx * 0.1, 30), f(rx * 0.3, ry * 0.6), f(rx * 0.9, ry * 0.45)], n=6), cap)]
                return
            if st == 'bob':
                back = ell(f(0, -4), rx + 16, ry + 12, self.ha).intersection(P_(loc(C, self.ha, [(-200, -60), (200, -60), (200, 200), (-200, 200)])))
            elif st == 'long':
                back = unary_union([ell(f(0, 2), rx + 14, ry + 8, self.ha), chain([(f(-rx - 2, -10), 20), (f(-rx - 12, -160), 26)]), chain([(f(rx + 2, -10), 20), (f(rx + 12, -160), 26)])]).convex_hull
            elif st == 'ponytail':
                back = chain([(f(rx - 8, 34), 18), (f(rx + 22, -30), 17), (f(rx + 26, -120), 10)])
            elif st == 'bun':
                back = disc(f(0, ry + 14), 28)
            else:
                back = None
            if back is not None: self.layers['hair_back'] += [('shape', back)]
            hl = P_(loc(C, self.ha, [(-rx - 14, -36), (-rx + 4, 0), (-rx * 0.5, 26), (0, 30), (rx * 0.5, 26), (rx - 4, 0), (rx + 14, -36), (rx + 60, 300), (-rx - 60, 300)]))
            cap = big.intersection(hl)
            self.layers['hair'] += [('shape', cap), ('line', [f(0, ry + 10), f(0, 32)], cap)]
            return
        # side view: cap over the top and back, the hairline curving over the ear
        hl = P_(loc(C, self.ha, [(rx * 0.7, ry * 0.62), (rx * 0.36, ry * 0.46), (rx * 0.12, ry * 0.2), (rx * 0.08, -ry * 0.2), (-rx * 0.16, 0.0),
                                  (-rx * 0.42, ry * 0.02), (-rx * 0.5, -ry * 0.34), (-rx * 0.96, -ry * 0.64), (-300, -300), (-300, 300), (300, 300)]))
        cap = big.intersection(hl)
        if st == 'bob':
            cap = cap.union(ell(f(-10, -6), rx + 10, ry + 6, self.ha).intersection(P_(loc(C, self.ha, [(-rx * 0.3, ry), (-rx * 0.35, -ry * 0.8), (-300, -ry * 0.8), (-300, 300)]))))
        if st == 'long':
            cap = cap.union(chain([(f(-rx * 0.6, 0), 30), (f(-rx * 0.9, -150), 28)]))
        if st == 'ponytail':
            self.layers['hair'] += [('shape', chain([(f(-rx * 0.8, ry * 0.4), 20), (f(-rx - 30, ry * 0.05), 18), (f(-rx - 40, -ry - 28), 9)]))]
        if st == 'bun':
            self.layers['hair'] += [('shape', disc(f(-rx * 0.85, ry * 0.52), 28))]
        self.layers['hair'] += [('shape', cap)]
        if st in ('long', 'bob', 'ponytail', 'bun'):
            self.layers['hair'] += [('line', spline([f(rx * 0.5, ry * 0.72), f(0, ry * 0.76), f(-rx * 0.6, ry * 0.32)], n=8), cap)]
        else:
            self.layers['hair'] += [('line', spline([f(rx * 0.4, ry * 0.7), f(-rx * 0.1, ry * 0.62), f(-rx * 0.6, ry * 0.2)], n=8), cap)]

    def hat(self):
        h = self.p.get('hat')
        if not h: return
        B, J = self.B, self.J; C = J['C']; rx, ry = B['hrx'], B['hry']; f = frame(C, self.ha)
        top = lambda v0: P_(loc(C, self.ha, [(-300, v0), (300, v0), (300, 300), (-300, 300)]))
        if h == 'cap':
            crown = ell(f(-2, 16), rx + 8, ry - 4, self.ha).intersection(top(16))
            if self.view == 'F':
                brim = ell(f(0, 18), rx + 14, 12, self.ha)
            else:
                brim = P_(loc(C, self.ha, [(rx * 0.5, 24), (rx + 44, 18), (rx + 42, 8), (rx * 0.4, 10)]))
            self.layers['hair'] += [('shape', crown), ('shape', brim)]
        elif h == 'sunhat':
            self.layers['hair'] += [('shape', ell(f(0, 30), rx + 70, 15, self.ha)), ('shape', ell(f(0, 46), rx + 6, 40, self.ha).intersection(top(30)))]
        elif h == 'helmet':
            g = ell(f(-2, 10), rx + 12, ry + 6, self.ha).intersection(top(0))
            self.layers['hair'] += [('shape', g), ('line', [f(-rx * 0.6, ry * 0.5), f(rx * 0.3, ry + 8)], g)]
        elif h == 'beanie':
            g = ell(f(0, 18), rx + 8, ry, self.ha).intersection(top(10))
            self.layers['hair'] += [('shape', g), ('shape', P_(loc(C, self.ha, [(-rx - 9, 10), (rx + 9, 10), (rx + 9, 34), (-rx - 9, 34)])))]
        elif h == 'chef':
            g = unary_union([disc(f(-26, ry + 28), 34), disc(f(26, ry + 28), 34), disc(f(0, ry + 46), 36), P_(loc(C, self.ha, [(-rx + 2, 18), (rx - 2, 18), (rx + 6, ry + 20), (-rx - 6, ry + 20)]))])
            self.layers['hair'] += [('shape', g), ('line', [f(-rx - 2, 40), f(rx + 2, 40)], g)]

    # ------------------------------------------------ assembly
    def build(self):
        for s in 'LR':
            self.leg(s); self.arm(s)
        self.pelvis(); self.torso(); self.head(); self.hat()
        for layer, item in self.p.get('props', []):
            self.layers[layer] += item(self.J, self.B, self)
        if self.view == 'F':
            order = ['back', 'between', 'hair_back', 'legL', 'legR', 'pelvis', 'skirt', 'neck', 'torso', 'head', 'hair', 'mid', 'armL', 'armR', 'front']
        else:
            fa, na = 'arm' + ('L' if self.near == 'R' else 'R'), 'arm' + self.near
            fl, nl = 'leg' + ('L' if self.near == 'R' else 'R'), 'leg' + self.near
            order = ['back', 'hair_back', fa, fl, 'between', 'pelvis', nl, 'skirt', 'neck', 'torso', 'head', 'hair', 'mid', na, 'front']
        order = self.p.get('order', order)
        geoms = [it[1] for name in order for it in self.layers[name] if it[0] in ('shape', 'cut', 'oline')]
        lowest = min(g.bounds[1] for g in geoms if not g.is_empty)
        dy = -lowest + self.p.get('air', 0)
        sc = Scene()
        for name in order:
            for it in self.layers[name]:
                kind = it[0]
                if kind == 'shape': sc.geom(affinity.translate(it[1], 0, dy))
                elif kind == 'cut': sc.cut(affinity.translate(it[1], 0, dy))
                elif kind == 'oline': sc.geom(affinity.translate(it[1], 0, dy), fill=False)
                elif kind == 'line':
                    P = [(x, y + dy) for x, y in it[1]]
                    if len(it) > 2 and it[2] is not None:
                        for Q in lines_of(LineString(P).intersection(affinity.translate(it[2], 0, dy).buffer(-3))): sc.line(Q)
                    else: sc.line(P)
                elif kind == 'lines':
                    for P in it[1]: sc.line([(x, y + dy) for x, y in P])
        if self.p.get('ground_line'):
            xs = [g.bounds[0] for g in geoms] + [g.bounds[2] for g in geoms]
            gl = self.p['ground_line'] if isinstance(self.p['ground_line'], tuple) else (min(xs) - 80, max(xs) + 80)
            sc.items.insert(0, ('line', LineString([(gl[0], 0), (gl[1], 0)]), False, True))
        L = sc.render()
        if self.p.get('mirror'): L = [[(-x, y) for x, y in P] for P in L]
        return flipL(L)

def figure(**p):
    return Figure(p).build()

# ---------------------------------------------------------------- props
def stick(a, b, r=6): return chain([(a, r), (b, r)])
def at_(J, at): return J[at] if isinstance(at, str) else at
def ytext(s, x, y, size, font='HersheySans1'):
    return [[(px, -py) for px, py in P] for P in text(s, x, -y, size, font)]

def ball(r=60, at='PR', off=(0, 0), kind='plain'):
    def f(J, B, F):
        c = ad(at_(J, at), off); g = disc(c, r)
        out = [('shape', g)]
        if kind == 'basket':
            out += [('line', [(c[0] - r, c[1]), (c[0] + r, c[1])], g), ('line', [(c[0], c[1] - r), (c[0], c[1] + r)], g),
                    ('line', arc(c[0] - r * 1.3, c[1], r, -0.9, 0.9, n=10), g), ('line', arc(c[0] + r * 1.3, c[1], r, math.pi - 0.9, math.pi + 0.9, n=10), g)]
        elif kind == 'soccer':
            out += [('shape', P_(regular(c[0], c[1], r * 0.36, 5)))]
            for i in range(5):
                t = math.pi / 2 + i * 2 * math.pi / 5
                out += [('line', [(c[0] + r * 0.36 * math.cos(t), c[1] + r * 0.36 * math.sin(t)), (c[0] + r * math.cos(t), c[1] + r * math.sin(t))], g)]
        elif kind == 'tennis':
            out += [('line', arc(c[0] - r * 1.15, c[1], r * 0.85, -0.85, 0.85, n=10), g), ('line', arc(c[0] + r * 1.15, c[1], r * 0.85, math.pi - 0.85, math.pi + 0.85, n=10), g)]
        elif kind == 'volley':
            out += [('line', arc(c[0], c[1] - r * 0.9, r * 1.2, 0.6, 2.55, n=12), g), ('line', arc(c[0] + r * 0.9, c[1] + r * 0.5, r * 1.1, 2.3, 3.9, n=12), g),
                    ('line', arc(c[0] - r * 0.9, c[1] + r * 0.5, r * 1.1, -0.75, 0.85, n=12), g)]
        return out
    return f

def racket(at='PR', ang=90, kind='tennis'):
    def f(J, B, F):
        p0 = at_(J, at); d = V(ang)
        L = 110 if kind == 'tennis' else 80
        c = ad(p0, d, L + 70)
        head = ell(c, 46 if kind == 'tennis' else 40, 66 if kind == 'tennis' else 50, ang); inner = head.buffer(-8)
        out = [('shape', stick(ad(p0, d, -30), ad(p0, d, L + 6), 9)), ('shape', head.difference(inner))]
        fr = frame(c, ang)
        for u in (-27, -9, 9, 27): out += [('line', [fr(u, -80), fr(u, 80)], inner)]
        for v in (-42, -21, 0, 21, 42): out += [('line', [fr(-60, v), fr(60, v)], inner)]
        return out
    return f

def bat(at='PR', ang=-90, kind='cricket'):
    def f(J, B, F):
        p0 = at_(J, at); d = V(ang); fr = frame(p0, ang)
        if kind == 'cricket':
            blade = P_([fr(-26, 120), fr(26, 120), fr(28, 380), fr(16, 396), fr(-16, 396), fr(-28, 380)])
            return [('shape', stick(fr(0, -50), fr(0, 124), 9)), ('shape', blade), ('line', [fr(0, 140), fr(0, 370)], blade)]
        g = chain([(fr(0, -40), 9), (fr(0, 120), 12), (fr(0, 330), 22)])
        return [('shape', g)]
    return f

def book(c=None, at=None, w=200, h=140, ang=0, open_=True, off=(0, 0)):
    def f(J, B, F):
        cc = ad(at_(J, at) if at else c, off); fr = frame(cc, ang + 90)
        if not open_:
            g = P_([fr(-w / 2, -h / 2), fr(w / 2, -h / 2), fr(w / 2, h / 2), fr(-w / 2, h / 2)])
            return [('shape', g), ('line', [fr(-w / 2 + 14, -h / 2), fr(-w / 2 + 14, h / 2)], g)]
        g = P_([fr(-w / 2, -h / 2 + 10), fr(0, -h / 2), fr(w / 2, -h / 2 + 10), fr(w / 2, h / 2 + 4), fr(0, h / 2 - 6), fr(-w / 2, h / 2 + 4)])
        out = [('shape', g), ('line', [fr(0, -h / 2), fr(0, h / 2 - 6)], None)]
        for i in range(4):
            v = h / 2 - 28 - i * 22
            out += [('line', [fr(-w / 2 + 16, v + 2), fr(-16, v - 2)], g), ('line', [fr(16, v - 2), fr(w / 2 - 16, v + 2)], g)]
        return out
    return f

def phone(at='PR', ang=90, off=(0, 0)):
    def f(J, B, F):
        c = ad(at_(J, at), off); g = Polygon(loc(c, ang, [(-17, -32), (17, -32), (17, 32), (-17, 32)])).buffer(5)
        return [('shape', g), ('line', loc(c, ang, [(-10, -22), (10, -22), (10, 24), (-10, 24), (-10, -22)]), None)]
    return f

def guitar(c, ang=15):
    def f(J, B, F):
        c0 = ad(J['H'], c); fr = frame(c0, ang + 90)   # u along the neck
        body = unary_union([disc(fr(0, 0), 92), disc(fr(118, 0), 70), P_([fr(0, -80), fr(118, -58), fr(118, 58), fr(0, 80)])])
        neck = P_([fr(170, -13), fr(470, -11), fr(470, 11), fr(170, 13)])
        head = P_([fr(466, -16), fr(540, -20), fr(546, 18), fr(466, 16)])
        out = [('shape', neck), ('shape', head), ('shape', body), ('shape', disc(fr(84, 0), 28)), ('shape', P_([fr(-38, -26), fr(-24, -26), fr(-24, 26), fr(-38, 26)]))]
        for v in (-6, 6): out += [('line', [fr(-30, v), fr(540, v)], None)]
        for u in (230, 290, 345, 395, 440): out += [('line', [fr(u, -12), fr(u, 12)], None)]
        return out
    return f

def umbrella(at='PR', top=640, w=420):
    def f(J, B, F):
        p0 = at_(J, at)
        tipx = p0[0]; ty = J['H'][1] + top
        shaft = stick((p0[0], p0[1] - 40), (tipx, ty + 20), 5)
        hook = LineString(arc(p0[0] - 22, p0[1] - 40, 22, math.pi, 2 * math.pi, n=10)).buffer(5)
        n = 6; pts = [(tipx - w / 2, ty - 120)]
        for i in range(n):
            x0 = tipx - w / 2 + i * w / n; x1 = x0 + w / n
            pts += arc((x0 + x1) / 2, ty - 120, w / n / 2, math.pi, 2 * math.pi, n=8)[1:]
        dome = spline([(tipx + w / 2, ty - 120), (tipx + w * 0.42, ty - 20), (tipx, ty + 20), (tipx - w * 0.42, ty - 20), (tipx - w / 2, ty - 120)], n=12)
        can = P_(pts[::-1] + dome)
        out = [('shape', hook), ('shape', shaft), ('shape', can)]
        for i in range(1, n):
            out += [('line', [(tipx, ty + 18), (tipx - w / 2 + i * w / n, ty - 122)], None)]
        out += [('shape', stick((tipx, ty + 18), (tipx, ty + 50), 4))]
        return out
    return f

def box_(c, w=200, h=160, ang=0, tape=True):
    def f(J, B, F):
        cc = ad(J['H'], c) if not isinstance(c, str) else J[c]
        g = P_(loc(cc, ang + 90, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]))
        out = [('shape', g)]
        if tape: out += [('line', loc(cc, ang + 90, [(-w / 2, h / 2 - 24), (w / 2, h / 2 - 24)]), None), ('line', loc(cc, ang + 90, [(0, h / 2), (0, h / 2 - 24)]), None)]
        return out
    return f

def ground_box(at='PR', w=300, extra=90):
    def f(J, B, F):
        y0 = min(J['AL'][1], J['AR'][1]) - 50
        x0 = J[at][0] + 34; h = J[at][1] - y0 + extra
        g = P_([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)])
        return [('shape', g), ('line', [(x0, y0 + h - 34), (x0 + w, y0 + h - 34)], None), ('line', [(x0 + w / 2, y0 + h), (x0 + w / 2, y0 + h - 34)], None)]
    return f

def barbell(span=330, plates=2):
    def f(J, B, F):
        a, b = J['PL'], J['PR']; c = mid(a, b); ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        fr = frame(c, ang - 90)
        out = [('shape', stick(fr(-span - 40, 0), fr(span + 40, 0), 7))]
        for sx in (-1, 1):
            for i in range(plates):
                u = sx * (span - 30 + i * 30)
                out += [('shape', P_([fr(u - 13, -90 + i * 16), fr(u + 13, -90 + i * 16), fr(u + 13, 90 - i * 16), fr(u - 13, 90 - i * 16)]))]
            out += [('shape', P_([fr(sx * (span - 54), -14), fr(sx * (span - 44), -14), fr(sx * (span - 44), 14), fr(sx * (span - 54), 14)]))]
        return out
    return f

def dumbbell(at='PR', ang=0):
    def f(J, B, F):
        c = J[at]; fr = frame(c, ang - 90)
        out = [('shape', stick(fr(-60, 0), fr(60, 0), 8))]
        for sx in (-1, 1):
            out += [('shape', Polygon(regular(*fr(sx * 64, 0), 34, 6)).buffer(3)), ('shape', Polygon(regular(*fr(sx * 82, 0), 30, 6)).buffer(3))]
        return out
    return f

def skateboard():
    def f(J, B, F):
        y = min(J['AL'][1], J['AR'][1]) - 50
        x0 = min(J['AL'][0], J['AR'][0]) - 70; x1 = max(J['TL'][0], J['TR'][0]) + 50
        deck = P_(spline([(x0 - 40, y + 30), (x0, y), (x1, y), (x1 + 40, y + 30), (x1 + 34, y + 36), (x1 - 4, y - 14), (x0 + 4, y - 14), (x0 - 34, y + 36)], closed=True, n=6, tension=0.4))
        out = [('shape', deck)]
        for x in (x0 + 50, x1 - 50):
            out += [('shape', P_([(x - 12, y - 14), (x + 12, y - 14), (x + 8, y - 30), (x - 8, y - 30)])), ('shape', disc((x - 22, y - 46), 20)), ('shape', disc((x + 22, y - 46), 20))]
        return out
    return f

def surfboard():
    def f(J, B, F):
        y = min(J['AL'][1], J['AR'][1]) - 50
        x0 = min(J['AL'][0], J['AR'][0]) - 200; x1 = max(J['TL'][0], J['TR'][0]) + 220
        g = P_(spline([(x0, y - 6), (x0 + 80, y), (x1 - 120, y), (x1, y - 14), (x1 - 100, y - 40), (x0 + 80, y - 40), (x0 + 10, y - 28)], closed=True, n=8, tension=0.4))
        out = [('shape', g), ('line', [(x0 + 70, y - 20), (x1 - 90, y - 20)], g)]
        for i in range(5):
            xx = x0 - 160 + i * (x1 - x0 + 320) / 5
            out += [('line', spline([(xx, y - 70), (xx + 50, y - 40), (xx + 110, y - 70), (xx + 170, y - 86)], n=8), None)]
        return out
    return f

def broom(a_at='PL', b_at='PR', length=820, kind='broom'):
    def f(J, B, F):
        a, b = J[a_at], J[b_at]; d = (b[0] - a[0], b[1] - a[1]); L = math.hypot(*d); d = (d[0] / L, d[1] / L)
        top = ad(a, d, -110); end = ad(a, d, length)
        out = [('shape', stick(top, end, 9))]
        ang = math.degrees(math.atan2(d[1], d[0])); fr = frame(end, ang)
        if kind == 'broom':
            head = P_([fr(-34, -10), fr(34, -10), fr(80, 150), fr(-80, 150)])
            out += [('shape', head)] + [('line', [fr(u * 0.4, 30), fr(u, 146)], head) for u in range(-70, 80, 20)]
        elif kind == 'spade':
            head = P_([fr(-46, -6), fr(46, -6), fr(44, 150), fr(0, 186), fr(-44, 150)])
            out += [('shape', head), ('shape', stick(fr(-30, -150 - L), fr(30, -150 - L), 8)) if False else ('shape', disc(top, 14))]
        return out
    return f

def rod(at='PR', ang=50, L=620, drop=None):
    def f(J, B, F):
        p0 = J[at]; tip = ad(p0, V(ang), L)
        g = chain([(ad(p0, V(ang), -50), 10), (tip, 3)])
        y_end = min(J['AL'][1], J['AR'][1]) - 50 + (drop or 0)
        line_ = spline([tip, (tip[0] + 60, (tip[1] + y_end) / 2), (tip[0] + 90, y_end + 20)], n=12)
        out = [('shape', g), ('line', line_, None), ('shape', disc(ad(p0, V(ang), 40), 16))]
        x = tip[0] + 90
        for i in range(3): out += [('line', spline([(x - 170 + i * 120, y_end + 16), (x - 140 + i * 120, y_end + 30), (x - 100 + i * 120, y_end + 16)], n=6), None)]
        return out
    return f

def mic(at='PR', ang=80):
    def f(J, B, F):
        p0 = J[at]; d = V(ang)
        head = disc(ad(p0, d, 120), 30)
        out = [('shape', chain([(ad(p0, d, -40), 11), (ad(p0, d, 90), 15)])), ('shape', head)]
        c = ad(p0, d, 120)
        out += [('line', [(c[0] - 30, c[1] + k), (c[0] + 30, c[1] + k)], head) for k in (-14, 0, 14)]
        return out
    return f

def cup(at='PR', off=(0, 30)):
    def f(J, B, F):
        c = ad(J[at], off)
        g = P_([(c[0] - 30, c[1] - 40), (c[0] + 30, c[1] - 40), (c[0] + 36, c[1] + 40), (c[0] - 36, c[1] + 40)])
        lid = P_([(c[0] - 40, c[1] + 40), (c[0] + 40, c[1] + 40), (c[0] + 36, c[1] + 54), (c[0] - 36, c[1] + 54)])
        out = [('shape', g), ('shape', lid), ('line', [(c[0] - 33, c[1] - 6), (c[0] + 33, c[1] - 6)], g)]
        for k in (-14, 6): out += [('line', spline([(c[0] + k, c[1] + 64), (c[0] + k + 12, c[1] + 86), (c[0] + k, c[1] + 108), (c[0] + k + 10, c[1] + 128)], n=8), None)]
        return out
    return f

def bag(at='PR', w=130, h=150, kind='shopping'):
    def f(J, B, F):
        p0 = J[at]
        top = p0[1] - 40
        if kind == 'shopping':
            g = P_([(p0[0] - w / 2, top - h), (p0[0] + w / 2, top - h), (p0[0] + w / 2, top), (p0[0] - w / 2, top)])
            handle = LineString(arc(p0[0], top, 34, 0, math.pi, n=10)).buffer(4)
            return [('shape', handle), ('shape', g), ('line', [(p0[0] - w / 2 + 14, top - 22), (p0[0] + w / 2 - 14, top - 22)], g)]
        if kind == 'handbag':
            g = P_(spline([(p0[0] - 70, top - 10), (p0[0] + 70, top - 10), (p0[0] + 84, top - 110), (p0[0] - 84, top - 110)], closed=True, n=4, tension=0.3))
            handle = LineString(arc(p0[0], top - 10, 46, 0, math.pi, n=12)).buffer(5)
            return [('shape', handle), ('shape', g), ('line', [(p0[0] - 76, top - 40), (p0[0] + 76, top - 40)], g), ('shape', disc((p0[0], top - 40), 8))]
        if kind == 'briefcase':
            g = P_([(p0[0] - 110, top - 140), (p0[0] + 110, top - 140), (p0[0] + 110, top - 10), (p0[0] - 110, top - 10)]).buffer(6)
            handle = LineString([(p0[0] - 30, top - 10), (p0[0] - 30, top + 22), (p0[0] + 30, top + 22), (p0[0] + 30, top - 10)]).buffer(6)
            return [('shape', handle), ('shape', g), ('line', [(p0[0] - 116, top - 50), (p0[0] + 116, top - 50)], g)]
        return []
    return f

def walking_stick(at='PR', ang=-80):
    def f(J, B, F):
        p0 = J[at]; y_end = min(J['AL'][1], J['AR'][1]) - 50
        d = V(ang); L = (p0[1] - y_end) / max(0.2, -d[1])
        return [('shape', stick(ad(p0, d, -40), ad(p0, d, L), 8))]
    return f

def chair(kind='chair'):
    def f(J, B, F):
        H = J['H']; floor = min(J['AL'][1], J['AR'][1]) - 50
        seat_y = H[1] - (46 if F.kind == 'm' else 50)
        x0, x1 = H[0] - 90, H[0] + 110
        out = [('shape', P_([(x0, seat_y - 22), (x1, seat_y - 22), (x1, seat_y), (x0, seat_y)]))]
        if kind == 'chair':
            out += [('shape', P_([(x0 - 6, seat_y), (x0 + 16, seat_y), (x0 + 6, seat_y + 340), (x0 - 18, seat_y + 340)]))]
            out += [('shape', P_([(x0 - 14, seat_y + 180), (x0 + 6, seat_y + 180), (x0 + 6, seat_y + 300), (x0 - 18, seat_y + 300)]))]
        for x in ((x0 + 6, x1 - 16) if kind == 'chair' else (x0 + 20, x1 - 30)):
            out += [('shape', P_([(x, floor), (x + 16, floor), (x + 16, seat_y - 22), (x, seat_y - 22)]))]
        if kind == 'stool':
            out += [('line', [(x0 + 36, floor + 120), (x1 - 30, floor + 120)], None)]
        return out
    return f

def ladder(x_off=110, below=320, above=150):
    def f(J, B, F):
        H = J['H']; x = H[0] + x_off
        y0 = min(J['AL'][1], J['AR'][1]) - 50 - below; y1 = max(J['PL'][1], J['PR'][1]) + above
        out = [('shape', stick((x - 30, y0 + 6), (x - 30, y1), 6)), ('shape', stick((x + 30, y0 + 6), (x + 30, y1), 6))]
        foot = min(J['AL'][1], J['AR'][1]) - 50
        y = foot - 8
        while y > y0 + 20: y -= 80
        y += 80
        while y < y1 - 20:
            out += [('shape', stick((x - 30, y), (x + 30, y), 5))]; y += 80
        return out
    return f

def easel(x_off=330, canvas_h=300):
    def f(J, B, F):
        H = J['H']; floor = min(J['AL'][1], J['AR'][1]) - 50; x = H[0] + x_off
        top = floor + 760
        out = [('shape', stick((x - 70, floor + 4), (x, top), 7)), ('shape', stick((x + 70, floor + 4), (x, top), 7)), ('shape', stick((x + 110, floor + 30), (x, top - 40), 6))]
        cv = P_([(x - 120, top - 120 - canvas_h), (x + 120, top - 120 - canvas_h), (x + 120, top - 120), (x - 120, top - 120)])
        out += [('shape', P_([(x - 130, top - 132 - canvas_h), (x + 130, top - 132 - canvas_h), (x + 130, top - 112 - canvas_h), (x - 130, top - 112 - canvas_h)])), ('shape', cv)]
        out += [('line', spline([(x - 100, top - 280), (x - 40, top - 230), (x + 20, top - 260), (x + 100, top - 200)], n=10), cv),
                ('line', circle(x + 50, top - 180, 26, 14), cv), ('line', [(x - 110, top - 330), (x - 60, top - 300), (x - 20, top - 334), (x + 40, top - 296), (x + 110, top - 330)], cv)]
        return out
    return f

def brush(at='PR', ang=30, L=140):
    def f(J, B, F):
        p0 = J[at]; d = V(ang)
        return [('shape', chain([(ad(p0, d, -30), 6), (ad(p0, d, L), 5)])), ('shape', chain([(ad(p0, d, L), 7), (ad(p0, d, L + 30), 2)]))]
    return f

def palette(at='PL'):
    def f(J, B, F):
        c = ad(J[at], (40, 10)); g = ell(c, 70, 50, 90).difference(disc(ad(c, (-30, -10)), 12))
        return [('shape', g)] + [('line', circle(c[0] + dx, c[1] + dy, 9, 10), g) for dx, dy in ((10, 26), (36, 10), (34, -18), (4, -28))]
    return f

def camera(at='PR', off=(30, 40)):
    def f(J, B, F):
        c = ad(J[at], off)
        g = P_([(c[0] - 34, c[1] - 30), (c[0] + 34, c[1] - 30), (c[0] + 34, c[1] + 30), (c[0] - 34, c[1] + 30)]).buffer(6)
        lens = P_([(c[0] + 34, c[1] - 22), (c[0] + 74, c[1] - 22), (c[0] + 74, c[1] + 22), (c[0] + 34, c[1] + 22)])
        return [('shape', g), ('shape', P_([(c[0] - 20, c[1] + 30), (c[0] + 6, c[1] + 30), (c[0] + 2, c[1] + 44), (c[0] - 16, c[1] + 44)])), ('shape', lens), ('line', [(c[0] + 66, c[1] - 22), (c[0] + 66, c[1] + 22)], None)]
    return f

def jump_rope(over=True):
    def f(J, B, F):
        a, b = J['PL'], J['PR']; C = J['C']
        if over:
            pts = spline([a, (a[0] - 120, C[1] + 60), (C[0], C[1] + 230), (b[0] + 120, C[1] + 60), b], n=16)
        else:
            y = min(J['AL'][1], J['AR'][1]) - 90
            pts = spline([a, (a[0] - 90, y + 200), (C[0], y), (b[0] + 90, y + 200), b], n=16)
        out = [('shape', LineString(pts).buffer(4))]
        for p, s in ((a, -1), (b, 1)):
            out += [('shape', stick(ad(p, (0, -20)), ad(p, (0, 50)), 10))]
        return out
    return f

def hoop_part(front=True, c=(0, 90), rx=240, ry=42, tilt=6):
    def f(J, B, F):
        cc = ad(J['H'], c)
        outer = Polygon(ellipse(cc[0], cc[1], rx, ry, math.radians(tilt), 80)); ring = outer.difference(Polygon(ellipse(cc[0], cc[1], rx - 12, ry - 9, math.radians(tilt), 80)))
        hp = P_(loc(cc, 90 + tilt, [(-600, 0), (600, 0), (600, -400), (-600, -400)])) if front else P_(loc(cc, 90 + tilt, [(-600, 0), (600, 0), (600, 400), (-600, 400)]))
        return [('shape', ring.intersection(hp))]
    return f

def pompom(at='PR'):
    def f(J, B, F):
        c = ad(J[at], (0, 10)); r = rng(int(abs(c[0])) + 3)
        g = unary_union([disc((c[0] + 42 * math.cos(t), c[1] + 42 * math.sin(t)), 22) for t in [i * 2 * math.pi / 11 for i in range(11)]] + [disc(c, 46)])
        out = [('shape', g)]
        for i in range(9):
            t = r.uniform(0, 2 * math.pi); out += [('line', [(c[0] + 12 * math.cos(t), c[1] + 12 * math.sin(t)), (c[0] + 48 * math.cos(t), c[1] + 48 * math.sin(t))], g)]
        return out
    return f

def laptop(c, ang=0):
    def f(J, B, F):
        cc = ad(J['H'], c); fr = frame(cc, ang + 90)
        base = P_([fr(-120, 0), fr(120, 0), fr(120, 16), fr(-120, 16)])
        scr = P_(loc(fr(118, 10), ang + 104, [(-7, 0), (7, 0), (7, 190), (-7, 190)]))
        return [('shape', scr), ('shape', base)]
    return f

def watering_can(at='PR'):
    def f(J, B, F):
        p0 = J[at]; c = ad(p0, (40, -70))
        body = P_([(c[0] - 60, c[1] - 70), (c[0] + 60, c[1] - 70), (c[0] + 50, c[1] + 50), (c[0] - 50, c[1] + 50)])
        spout = P_([(c[0] + 50, c[1] - 30), (c[0] + 180, c[1] + 40), (c[0] + 186, c[1] + 28), (c[0] + 56, c[1] - 56)])
        rose = P_([(c[0] + 176, c[1] + 50), (c[0] + 206, c[1] + 22), (c[0] + 200, c[1] + 10), (c[0] + 170, c[1] + 36)])
        handle = LineString(arc(c[0] - 10, c[1] + 50, 52, 0.2, math.pi - 0.2, n=12)).buffer(7)
        out = [('shape', handle), ('shape', spout), ('shape', rose), ('shape', body)]
        for k in range(6):
            x = c[0] + 214 + (k % 3) * 16; y = c[1] + 4 - k * 36
            out += [('line', [(x, y), (x + 8, y - 20)], None)]
        return out
    return f

def plant_pot(x_off=380, scale=1.0, at='H'):
    def f(J, B, F):
        floor = min(J['AL'][1], J['AR'][1]) - 50; x = J[at][0] + x_off; s = scale
        pot = P_([(x - 60 * s, floor), (x + 60 * s, floor), (x + 74 * s, floor + 110 * s), (x - 74 * s, floor + 110 * s)])
        rim = P_([(x - 82 * s, floor + 104 * s), (x + 82 * s, floor + 104 * s), (x + 82 * s, floor + 130 * s), (x - 82 * s, floor + 130 * s)])
        out = []
        for ang, L in ((60, 170), (90, 210), (120, 160), (40, 120), (140, 120)):
            base = (x, floor + 128 * s); tip = ad(base, V(ang, L * s))
            leaf = P_(spline([base, ad(mid(base, tip), V(ang + 90, 34 * s)), tip, ad(mid(base, tip), V(ang - 90, 34 * s))], closed=True, n=6, tension=0.45))
            out += [('shape', leaf), ('line', [base, tip], leaf)]
        return out + [('shape', pot), ('shape', rim)]
    return f

def bicycle(saddle, bar, crank, wheel_r=180):
    def f(J, B, F):
        H = J['H']
        sd, br, ck = ad(H, saddle), ad(H, bar), ad(H, crank)
        rear, front = (ck[0] - 330, ck[1] + 20), (ck[0] + 370, ck[1] + 20)
        out = []
        for c in (rear, front):
            ring = disc(c, wheel_r).difference(disc(c, wheel_r - 18))
            out += [('shape', ring), ('shape', disc(c, 14))]
            for i in range(8):
                t = i * math.pi / 8
                out += [('line', [(c[0] + (wheel_r - 18) * math.cos(t), c[1] + (wheel_r - 18) * math.sin(t)), (c[0] - (wheel_r - 18) * math.cos(t), c[1] - (wheel_r - 18) * math.sin(t))], None)]
        seat_top = (sd[0] - 6, sd[1] - 34)
        head_top = (br[0] - 40, br[1] - 60); head_bot = (front[0] - 70, front[1] + 150)
        for a, b in ((ck, seat_top), (ck, head_bot), (seat_top, head_top), (head_bot, head_top), (rear, ck), (rear, seat_top), (front, head_bot)):
            out += [('shape', stick(a, b, 9))]
        out += [('shape', stick(head_top, (br[0] - 10, br[1]), 9)), ('shape', stick((br[0] - 20, br[1]), (br[0] + 20, br[1] - 10), 10))]
        out += [('shape', P_(spline([(sd[0] - 60, sd[1] - 20), (sd[0] + 50, sd[1] - 14), (sd[0] + 30, sd[1] - 38), (sd[0] - 50, sd[1] - 40)], closed=True, n=4, tension=0.4)))]
        out += [('shape', disc(ck, 34))]
        return out
    return f

def pedal(at='AR'):
    def f(J, B, F):
        a = J[at]; return [('shape', P_([(a[0] - 30, a[1] - 60), (a[0] + 40, a[1] - 60), (a[0] + 40, a[1] - 48), (a[0] - 30, a[1] - 48)]))]
    return f

def crank_arm(crank, at='AR'):
    def f(J, B, F):
        c = ad(J['H'], crank); a = J[at]
        return [('shape', stick(c, (a[0] + 6, a[1] - 54), 8))]
    return f

def skis():
    def f(J, B, F):
        out = []
        for s in 'LR':
            a = J['A' + s]; y = a[1] - 52
            g = P_(spline([(a[0] - 300, y), (a[0] + 330, y), (a[0] + 400, y + 40), (a[0] + 390, y + 46), (a[0] + 320, y + 12), (a[0] - 300, y + 12)], n=6, tension=0.3))
            out += [('shape', g)]
        return out
    return f

def ski_pole(at='PR', ang=-120):
    def f(J, B, F):
        p0 = J[at]; floor = min(J['AL'][1], J['AR'][1]) - 40
        d = V(ang); L = (p0[1] - floor) / max(0.2, -d[1])
        end = ad(p0, d, L)
        return [('shape', stick(ad(p0, d, -30), end, 6)), ('shape', ell(ad(end, d, -40), 30, 6, ang))]
    return f

def tray(at='PR'):
    def f(J, B, F):
        p0 = ad(J[at], (0, 22))
        plate = P_([(p0[0] - 130, p0[1]), (p0[0] + 130, p0[1]), (p0[0] + 122, p0[1] + 14), (p0[0] - 122, p0[1] + 14)])
        out = [('shape', plate)]
        for x in (-70, 10, 80):
            g = P_([(p0[0] + x - 18, p0[1] + 14), (p0[0] + x + 18, p0[1] + 14), (p0[0] + x + 24, p0[1] + 110), (p0[0] + x - 24, p0[1] + 110)])
            out += [('shape', g), ('line', [(p0[0] + x - 22, p0[1] + 80), (p0[0] + x + 22, p0[1] + 80)], g)]
        return out
    return f

def baton(at='PR', ang=70):
    def f(J, B, F):
        p0 = J[at]; return [('shape', chain([(ad(p0, V(ang), -10), 6), (ad(p0, V(ang), 170), 3)]))]
    return f

def pillow(off=(0, 0)):
    def f(J, B, F):
        C = J['C']; c = ad(C, off)
        g = P_(spline([(c[0] - 130, c[1] - 60), (c[0] + 120, c[1] - 66), (c[0] + 130, c[1] - 10), (c[0] - 120, c[1] - 6)], closed=True, n=6, tension=0.4))
        return [('shape', g)]
    return f

def mattress(pad=120):
    def f(J, B, F):
        xs = [J[k][0] for k in ('C', 'AL', 'AR', 'H')]; low = min(J['H'][1] - 60, J['AL'][1] - 50, J['C'][1] - 66)
        g = P_([(min(xs) - pad - 120, low - 70), (max(xs) + pad, low - 70), (max(xs) + pad, low), (min(xs) - pad - 120, low)])
        return [('shape', g)]
    return f

def zzz(off=(60, 120)):
    def f(J, B, F):
        c = ad(J['C'], off); out = []
        for i, (dx, dy, s) in enumerate(((0, 0, 50), (60, 70, 70), (140, 160, 90))):
            out += [('line', P, None) for P in ytext('Z', c[0] + dx, c[1] + dy, s, 'HersheySans1')]
        return out
    return f

def water(y_off=0, span=(-700, 700), n=7):
    def f(J, B, F):
        H = J['H']; y = H[1] + y_off; out = []
        x = H[0] + span[0]
        w = (span[1] - span[0]) / n
        for i in range(n):
            out += [('line', spline([(x + i * w, y), (x + i * w + w * 0.25, y + 22), (x + i * w + w * 0.5, y), (x + i * w + w * 0.75, y - 18), (x + (i + 1) * w, y)], n=6), None)]
        return out
    return f

def wall(x_off=-90, h=1150):
    def f(J, B, F):
        floor = min(J['AL'][1], J['AR'][1]) - 50; x = J['H'][0] + x_off
        g = P_([(x - 160, floor), (x, floor), (x, floor + h), (x - 160, floor + h)])
        out = [('shape', g)]
        for i, y in enumerate(range(int(floor) + 70, int(floor + h), 70)):
            out += [('line', [(x - 160, y), (x, y)], None)]
            xx = x - 40 if i % 2 else x - 110
            out += [('line', [(xx, y - 70), (xx, y)], None)]
        return out
    return f

def kite(at='PR'):
    def f(J, B, F):
        p0 = J[at]; c = (p0[0] + 330, p0[1] + 520)
        g = P_([(c[0], c[1] + 120), (c[0] + 80, c[1]), (c[0], c[1] - 160), (c[0] - 80, c[1])])
        out = [('line', spline([p0, (p0[0] + 160, p0[1] + 220), c], n=12), None), ('shape', g), ('line', [(c[0], c[1] + 120), (c[0], c[1] - 160)], g), ('line', [(c[0] - 80, c[1]), (c[0] + 80, c[1])], g)]
        tail = spline([(c[0], c[1] - 160), (c[0] - 40, c[1] - 240), (c[0] + 20, c[1] - 320), (c[0] - 30, c[1] - 400)], n=12)
        out += [('line', tail, None)]
        for t in (0.3, 0.6, 0.9):
            q = tail[int(t * (len(tail) - 1))]; out += [('shape', P_([(q[0] - 14, q[1] + 8), (q[0] + 14, q[1] - 8), (q[0] + 14, q[1] + 8), (q[0] - 14, q[1] - 8)]).convex_hull)]
        return out
    return f

def violin(d=-10):
    def f(J, B, F):
        base = ad(J['C'], (6, -92)); u = V(d); n = V(d + 90)
        p = lambda s, t=0: (base[0] + u[0] * s + n[0] * t, base[1] + u[1] * s + n[1] * t)
        body = unary_union([ell(p(50), 52, 62, d), ell(p(150), 42, 48, d), P_([p(50, -38), p(150, -30), p(150, 30), p(50, 38)])])
        neck = P_([p(190, -8), p(318, -6), p(318, 6), p(190, 8)])
        out = [('shape', neck), ('shape', disc(p(330), 13)), ('shape', body),
               ('line', [p(84, -20), p(104, -14)], body), ('line', [p(84, 20), p(104, 14)], body), ('shape', P_([p(64, -16), p(70, -16), p(70, 16), p(64, 16)]))]
        for t in (-4, 4): out += [('line', [p(66, t), p(326, t)], None)]
        return out
    return f

def bow_stick(at='PR', ang=150, L=420):
    def f(J, B, F):
        p0 = J[at]; return [('shape', stick(ad(p0, V(ang), -40), ad(p0, V(ang), L), 4))]
    return f

def mat(pad=160):
    def f(J, B, F):
        xs = [J[k][0] for k in J if k[0] in 'PATKHC' and isinstance(J[k], tuple)]
        floor = min(g for g in [J['AL'][1] - 50, J['AR'][1] - 50])
        return []
    return f


# ---------------------------------------------------------------- the poses
HANG_F = lambda: {'L': (-97, -93), 'R': (-83, -87)}
STAND_F = lambda: {'L': (-94, -92), 'R': (-86, -88)}
STAND_S = lambda: {'L': (-93, -90, 0), 'R': (-87, -90, 0)}
HANG_S = lambda: {'L': (-86, -80), 'R': (-94, -88)}
WALK_S = lambda: {'L': (-110, -124, -26), 'R': (-70, -94, 12)}
WALK_ARMS = lambda: {'L': (-70, -52), 'R': (-110, -100)}
RUN_S = lambda: {'L': (-125, -165, -60), 'R': (-20, -100, -10)}
RUN_ARMS = lambda: {'L': (-45, 60, 70), 'R': (-130, -55, -60)}
FISTS = lambda: {'L': 'fist', 'R': 'fist'}

def bike_pose(kind):
    B = BODY[kind]
    crank = (70, -440)
    near_ped, far_ped = (crank[0] + 80, crank[1] - 40), (crank[0] - 80, crank[1] + 40)
    p = dict(kind=kind, view='S', torso=52, head=70, top='tee', bottom='shorts' if kind == 'm' else 'leggings', hat='helmet',
             arms={'L': ('ik', (330, 40), -1, 0, ), 'R': ('ik', (336, 30), -1, 0)}, hands=FISTS(),
             legs={'L': ('ik', (far_ped[0] - 10, far_ped[1] + 50), 1, -12), 'R': ('ik', (near_ped[0] - 10, near_ped[1] + 50), 1, -6)},
             props=[('between', bicycle((0, -46), (340, 34), crank)), ('between', crank_arm(crank, 'AL')), ('between', pedal('AL')),
                    ('mid', crank_arm(crank, 'AR')), ('mid', pedal('AR'))])
    if kind == 'f': p['hair'] = 'ponytail'
    return p

def poses():
    M, F = [], []
    m = lambda name, slug, **p: M.append((name, slug, dict(kind='m', **p)))
    f = lambda name, slug, **p: F.append((name, slug, dict(kind='f', **p)))
    # ---------------- men: everyday
    m('Standing with hands in pockets', 'man-hands-in-pockets', view='F', arms={'L': (-104, -64), 'R': (-76, -116)}, legs=STAND_F(), hands={'L': 'none', 'R': 'none'}, top='long', bottom='jeans')
    m('Hands on hips', 'man-hands-on-hips', view='F', arms={'L': (-140, -40, -20), 'R': (-40, -140, -160)}, legs={'L': (-98, -94), 'R': (-82, -86)}, hands=FISTS())
    m('Arms crossed', 'man-arms-crossed', view='F', arms={'L': (-95, 15), 'R': (-85, 165)}, legs=STAND_F(), hands=FISTS(), top='shirt')
    m('Waving hello', 'man-waving', view='F', arms={'L': (-97, -93), 'R': (20, 95, 95)}, legs=STAND_F())
    m('Pointing the way', 'man-pointing', view='S', arms={'L': (-88, -84), 'R': (6, 4, 4)}, legs=STAND_S(), hands={'R': 'point'}, top='jacket')
    m('Thinking', 'man-thinking', view='F', arms={'L': (-100, 5), 'R': (-100, 100, 95)}, k={'uaR': 0.6}, legs=STAND_F(), hands=FISTS(), top='long')
    m('Shrugging', 'man-shrugging', view='F', head=97, arms={'L': (-118, -165, 175), 'R': (-62, -15, 5)}, legs=STAND_F(), hands={'L': 'flat', 'R': 'flat'})
    m('Celebrating a win', 'man-celebrating', view='F', arms={'L': (125, 105), 'R': (55, 75)}, legs={'L': (-102, -96), 'R': (-78, -84)}, hands=FISTS())
    m('Star jump', 'man-star-jump', view='F', arms={'L': (140, 135), 'R': (40, 45)}, legs={'L': (-118, -116), 'R': (-62, -64)}, air=60, top='tank', bottom='shorts')
    m('On the phone', 'man-on-the-phone', view='F', arms={'L': (-104, -64), 'R': (-40, 115, 110)}, k={'uaR': 0.6}, hands={'L': 'none', 'R': 'fist'}, legs=STAND_F(), top='shirt',
      props=[('front', phone('PR', 100, (0, 6)))])
    m('Reading a book', 'man-reading-standing', view='F', arms={'L': (-105, 50), 'R': (-75, 130)}, legs=STAND_F(), props=[('front', book(at='N', off=(0, -60), w=230, h=150))])
    m('Carrying shopping bags', 'man-shopping-bags', view='F', arms={'L': (-101, -97), 'R': (-79, -83)}, legs=STAND_F(), hands=FISTS(), top='long',
      props=[('front', bag('PL')), ('front', bag('PR'))])
    m('Taking a selfie', 'man-selfie', view='F', arms={'L': (-140, -40, -20), 'R': (30, 45, 60)}, hands={'L': 'fist', 'R': 'fist'}, legs=STAND_F(), props=[('front', phone('PR', 80, (4, 20)))])
    m('Stretching overhead', 'man-stretch-overhead', view='F', arms={'L': (100, 62, 40), 'R': (80, 118, 140)}, legs=STAND_F(), top='tank', bottom='shorts', hands=FISTS())
    m('Side stretch', 'man-side-stretch', view='F', torso=76, head=72, arms={'L': (98, 20, 10), 'R': (-70, -78)}, legs={'L': (-100, -96), 'R': (-80, -84)}, top='tank', bottom='shorts')
    # ---------------- men: walking, running, jumping
    m('Businessman walking', 'man-businessman-walking', view='S', top='jacket', arms={'L': (-66, -44), 'R': (-94, -90, -90)}, hands={'R': 'fist'}, legs=WALK_S(),
      props=[('front', bag('PR', kind='briefcase'))])
    m('Running', 'man-running', view='S', torso=80, top='tee', bottom='shorts', arms=RUN_ARMS(), legs=RUN_S(), hands=FISTS())
    m('Tuck jump', 'man-tuck-jump', view='S', torso=100, arms={'L': (60, 100), 'R': (50, 90)}, legs={'L': (35, -100, -60), 'R': (25, -108, -60)}, hands=FISTS(), air=140, top='tank', bottom='shorts')
    m('Marching', 'man-marching', view='S', arms={'L': (-20, 10, 10), 'R': (-140, -130)}, legs={'L': (-92, -90, 0), 'R': (0, -90, 0)}, hands=FISTS(), top='jacket', hat='cap')
    m('Hiking with a backpack', 'man-hiking', view='S', torso=84, backpack=True, arms={'L': (-70, -52), 'R': (-60, -30, -60)}, hands={'R': 'fist'}, legs=WALK_S(), hat='cap', top='long',
      props=[('mid', walking_stick('PR', -80))])
    # ---------------- men: sport
    m('Kicking a ball', 'man-kicking-ball', view='S', torso=100, arms={'L': (-20, -5), 'R': (-150, -165)}, legs={'L': (-95, -92, 0), 'R': (-35, -15, -10)}, top='tee', bottom='shorts',
      props=[('front', ball(62, 'TR', (60, 10), 'soccer'))])
    m('Throwing a ball', 'man-throwing', view='S', torso=100, arms={'L': (5, 15), 'R': (170, 100, 100)}, hands={'R': 'fist'}, legs={'L': (-65, -95, 10), 'R': (-125, -110, -20)}, top='tee',
      props=[('front', ball(30, 'PR', (0, 10), 'tennis'))])
    m('Basketball shot', 'man-basketball', view='S', torso=92, arms={'L': (66, 86, 100), 'R': (76, 100, 110)}, legs={'L': (-92, -100, -60), 'R': (-88, -96, -60)}, air=40, top='tank', bottom='shorts',
      props=[('front', ball(64, 'PR', (-6, 80), 'basket'))])
    m('Tennis forehand', 'man-tennis', view='S', torso=92, arms={'L': (-150, -170), 'R': (-20, 0, 20)}, hands={'R': 'fist'}, legs={'L': (-60, -100, 0), 'R': (-120, -95, 0)}, top='tee', bottom='shorts',
      props=[('mid', racket('PR', 20))])
    m('Cricket batsman', 'man-cricket', view='S', torso=66, head=78, arms={'L': ('ik', (150, -10), -1, -80), 'R': ('ik', (140, -30), -1, -80)}, hands=FISTS(), legs={'L': (-68, -100, 0), 'R': (-106, -84, 0)},
      hat='helmet', top='long', props=[('front', bat('PR', -78))])
    m('Boxing stance', 'man-boxing', view='S', torso=85, arms={'L': (-40, 55, 60), 'R': (-70, 72, 80)}, hands={'L': 'glove', 'R': 'glove'}, legs={'L': (-70, -95, 0), 'R': (-110, -92, -15)}, top='tank', bottom='shorts')
    m('Karate kick', 'man-karate', view='S', torso=112, arms={'L': (-40, 30), 'R': (-120, -10)}, hands=FISTS(), legs={'L': (-92, -90, 0), 'R': (10, 18, 20)}, top='long', bottom='trousers', belt=True, hair='short')
    m('Skateboarding', 'man-skateboarding', view='S', torso=80, arms={'L': (-165, -160), 'R': (-25, -5)}, legs={'L': (-120, -82, 0), 'R': (-62, -106, 0)}, top='tee', bottom='jeans', hat='cap',
      props=[('front', skateboard())])
    m('Surfing', 'man-surfing', view='S', torso=70, head=80, arms={'L': (175, 185), 'R': (-5, 10)}, legs={'L': (-130, -78, 0), 'R': (-50, -112, 0)}, top='tank', bottom='shorts', hair='short',
      props=[('front', surfboard())])
    m('Skiing', 'man-skiing', view='S', torso=58, head=75, arms={'L': (-50, -40, -20), 'R': (-60, -30, -10)}, hands=FISTS(), legs={'L': (-42, -112, 0), 'R': (-36, -118, 0)}, top='coat', hat='helmet',
      props=[('front', skis()), ('back', ski_pole('PL', -125)), ('mid', ski_pole('PR', -120))])
    m('Swimming', 'man-swimming', view='S', torso=0, head=0, arms={'L': (80, 10, 0), 'R': (4, 4, 4)}, legs={'L': (178, 175, 175), 'R': (184, 186, 186)}, top='none_', bottom='shorts', hat='helmet',
      props=[('back', water(16, (-700, 700)))])
    m('Diving', 'man-diving', view='S', torso=-58, head=-58, arms={'L': (-56, -56, -56), 'R': (-60, -60, -60)}, legs={'L': (124, 124, 124), 'R': (120, 120, 120)}, top='none_', bottom='shorts', hat='helmet', air=200,
      props=[('back', water(-640, (-200, 700)))])
    m('Riding a bicycle', 'man-cycling', **{k: v for k, v in bike_pose('m').items() if k != 'kind'})
    m('Push-up', 'man-push-up', view='S', torso=25, head=15, arms={'L': (-90, -90, 0), 'R': (-90, -90, 0)}, legs={'L': (205, 205, -80), 'R': (205, 205, -80)}, hands={'L': 'flat', 'R': 'flat'}, top='tank', bottom='shorts', ground_line=True)
    m('Sit-up', 'man-sit-up', view='S', torso=130, head=120, arms={'L': (35, 35), 'R': (40, 40)}, legs={'L': (45, -45, 0), 'R': (40, -50, 0)}, top='tank', bottom='shorts', ground_line=True)
    m('Squat', 'man-squat', view='S', torso=62, head=80, arms={'L': (-5, 0), 'R': (0, 0)}, legs={'L': (-12, -102, 0), 'R': (-6, -96, 0)}, top='tank', bottom='shorts', ground_line=True)
    m('Lunge', 'man-lunge', view='S', torso=90, arms={'L': (-96, -90), 'R': (-90, -86)}, legs={'L': (-118, -172, -70), 'R': (-14, -90, 0)}, top='tank', bottom='shorts', ground_line=True)
    m('Lifting a barbell', 'man-barbell', view='F', arms={'L': (105, 95), 'R': (75, 85)}, legs={'L': (-102, -96), 'R': (-78, -84)}, hands=FISTS(), top='tank', bottom='shorts', props=[('front', barbell())])
    m('Dumbbell curl', 'man-dumbbell', view='F', arms={'L': (-97, -93), 'R': (-85, 80)}, legs=STAND_F(), hands=FISTS(), top='tank', bottom='shorts', props=[('front', dumbbell('PL', 0)), ('front', dumbbell('PR', 0))])
    m('Downward dog', 'man-downward-dog', view='S', torso=-35, head=-60, arms={'L': (-55, -55, 0), 'R': (-52, -52, 0)}, legs={'L': (-125, -120, 0), 'R': (-122, -118, 0)}, hands={'L': 'flat', 'R': 'flat'}, top='tank', bottom='shorts', ground_line=True)
    # ---------------- men: work and leisure
    m('Carrying a box', 'man-carrying-box', view='S', torso=96, arms={'L': (-60, 5), 'R': (-66, 0, 0)}, legs={'L': (-95, -90, 0), 'R': (-85, -88, 0)}, top='tee', props=[('mid', box_('PR', 220, 180) if False else box_((150, 150), 220, 190))])
    m('Pushing a heavy box', 'man-pushing-box', view='S', torso=40, head=30, arms={'L': (5, 8, 10), 'R': (10, 10, 10)}, hands={'L': 'flat', 'R': 'flat'}, legs={'L': (-132, -150, -30), 'R': (-70, -122, 0)}, top='tee',
      props=[('front', ground_box('PR', 300, 90))])
    m('Pulling a rope', 'man-pulling-rope', view='S', torso=122, head=100, arms={'L': (-2, 0), 'R': (-6, -4)}, hands=FISTS(), legs={'L': (-62, -80, 0), 'R': (-76, -96, 0)}, top='tee',
      props=[('front', lambda J, B, F: [('shape', LineString(spline([ad(J['PL'], (-160, -50)), J['PL'], J['PR'], ad(J['PR'], (420, -40))], n=16)).buffer(7))])])
    m('Sitting on a chair', 'man-sitting', view='S', torso=96, arms={'L': (-72, -2), 'R': (-76, -6)}, legs={'L': (0, -90, 0), 'R': (4, -92, 0)}, top='shirt', props=[('back', chair())])
    m('Kneeling on one knee', 'man-kneeling', view='S', torso=92, arms={'L': (-95, -90), 'R': (-50, -20, -30)}, legs={'L': (-90, 182, -110), 'R': (2, -92, 0)}, top='jacket')
    m('Lying down reading', 'man-lying-reading', view='S', torso=28, head=40, arms={'L': (-100, 5, 15), 'R': (-95, 10, 15)}, legs={'L': (182, 122, 30), 'R': (178, 100, 20)}, top='tee',
      props=[('front', book(at='PR', off=(50, 50), w=160, h=110, ang=20))])
    m('Sleeping', 'man-sleeping', view='S', torso=180, head=180, arms={'L': (-2, 0), 'R': (2, 0)}, legs={'L': (-1, 0, 90), 'R': (1, 0, 90)}, top='long', bottom='trousers',
      props=[('back', pillow((-30, -40))), ('back', mattress()), ('front', zzz((40, 140)))])
    m('Playing the guitar', 'man-guitar', view='S', torso=92, arms={'L': (-20, 12, 20), 'R': (-80, -25, -40)}, legs=STAND_S(), top='tee', props=[('mid', guitar((60, 80), 18))])
    m('Conducting', 'man-conducting', view='S', torso=95, arms={'L': (25, 75, 90), 'R': (30, 60)}, hands={'R': 'fist'}, legs=STAND_S(), top='jacket', props=[('front', baton('PR', 70))])
    m('Photographer', 'man-photographer', view='S', torso=90, arms={'L': (-35, 100), 'R': (-45, 97)}, hands=FISTS(), legs={'L': (-80, -92, 0), 'R': (-100, -90, 0)}, top='long', props=[('front', camera('PR', (20, 50)))])
    m('Holding an umbrella', 'man-umbrella', view='S', torso=88, arms={'L': (-88, -84), 'R': (-50, 75)}, hands={'R': 'fist'}, legs=WALK_S(), top='coat', props=[('front', umbrella('PR'))])
    m('Juggling', 'man-juggling', view='F', arms={'L': (-95, 160, 150), 'R': (-85, 20, 30)}, k={'faL': 0.5, 'faR': 0.5}, legs=STAND_F(), hands={'L': 'flat', 'R': 'flat'},
      props=[('front', ball(26, (-150, 560), (0, 0))), ('front', ball(26, (0, 680), (0, 0))), ('front', ball(26, (150, 540), (0, 0)))])
    m('Bowing', 'man-bowing', view='S', torso=35, head=22, arms={'L': (-90, -88), 'R': (-92, -90)}, legs={'L': (-94, -90, 0), 'R': (-90, -90, 0)}, top='jacket')
    m('Sweeping the floor', 'man-sweeping', view='S', torso=80, arms={'L': ('ik', (160, 120), -1, -45), 'R': ('ik', (230, -40), -1, -60)}, hands=FISTS(), legs={'L': (-100, -90, 0), 'R': (-70, -94, 0)}, top='tee',
      props=[('mid', broom('PL', 'PR', 760))])
    m('Fishing', 'man-fishing', view='S', torso=92, arms={'L': (-55, 15, 30), 'R': (-62, 22, 40)}, hands=FISTS(), legs=STAND_S(), hat='cap', top='long', props=[('front', rod('PR', 52, 640, -40))])
    m('Climbing a ladder', 'man-ladder', view='S', torso=88, arms={'L': (55, 85), 'R': (25, 65)}, hands=FISTS(), legs={'L': (-90, -92, 0), 'R': (-30, -102, 0)}, top='tee', props=[('back', ladder(150, 260, 120))])
    m('Tying a shoelace', 'man-tying-shoelace', view='S', torso=35, head=10, arms={'L': (-82, -88, -60), 'R': (-80, -85, -60)}, legs={'L': (-90, 182, -110), 'R': (2, -95, 0)}, top='tee')
    m('Waiter with a tray', 'man-waiter', view='S', torso=92, arms={'L': (-94, -88), 'R': (-55, 75, 0)}, hands={'R': 'flat'}, legs=STAND_S(), top='shirt', props=[('front', tray('PR'))])
    m('Painting at an easel', 'man-painter', view='S', torso=88, arms={'L': (-70, 10), 'R': (-15, 35, 30)}, hands={'R': 'fist'}, legs=STAND_S(), top='long',
      props=[('back', easel(380)), ('mid', palette('PL')), ('front', brush('PR', 30))])
    m('Leaning on a wall', 'man-leaning-wall', view='S', torso=97, arms={'L': (-104, -64), 'R': (-108, -60)}, hands={'L': 'none', 'R': 'none'}, legs={'L': (-100, -92, 0), 'R': (-78, -106, 0)}, top='long', bottom='jeans',
      props=[('back', wall(-70))])
    m('Flying a kite', 'man-kite', view='S', torso=95, head=110, arms={'L': (-88, -84), 'R': (20, 50, 50)}, hands={'R': 'fist'}, legs=STAND_S(), top='tee', props=[('front', kite('PR'))])
    m('Chef tasting the soup', 'man-chef-tasting', view='S', torso=88, head=80, arms={'L': (-60, 10), 'R': ('ik', (150, 250), -1, 150)}, hands={'R': 'fist'}, legs=STAND_S(), top='long', hat='chef',
      props=[('front', lambda J, B, F: [('shape', stick(ad(J['PR'], V(150, -30)), ad(J['PR'], V(150, 90)), 5)), ('shape', ell(ad(J['PR'], V(150, 112)), 14, 24, 150))])])

    # ---------------- women
    f('Walking with a handbag', 'woman-handbag', view='S', hair='long', heels=True, top='tee_f', arms={'L': (-70, -52), 'R': (-94, -90, -90)}, hands={'R': 'fist'},
      legs={'L': (-108, -122, -24), 'R': (-72, -94, 10)}, props=[('front', bag('PR', kind='handbag'))])
    f('Jogging', 'woman-jogging', view='S', torso=82, hair='ponytail', top='tank', bottom='leggings', arms=RUN_ARMS(), legs=RUN_S(), hands=FISTS())
    f('Jumping for joy', 'woman-jumping-joy', view='S', torso=95, hair='bob', top='tee_f', bottom='shorts', arms={'L': (70, 85), 'R': (55, 75)}, legs={'L': (-110, -150, -60), 'R': (-60, -125, -50)}, air=140)
    f('Skipping rope', 'woman-skipping', view='F', hair='ponytail', top='tank', bottom='shorts', arms={'L': (-112, -150, -150), 'R': (-68, -30, -30)}, hands=FISTS(),
      legs={'L': (-92, -92), 'R': (-88, -88)}, air=50, props=[('front', jump_rope(True))])
    f('Hula hoop', 'woman-hula-hoop', view='F', hair='bun', top='tank', bottom='shorts', arms={'L': (110, 80), 'R': (70, 100)}, legs={'L': (-96, -92), 'R': (-84, -88)},
      props=[('back', hoop_part(False)), ('front', hoop_part(True))])
    f('Tennis serve', 'woman-tennis-serve', view='S', torso=100, hair='ponytail', top='tank', skirt=0.6, arms={'L': (80, 92), 'R': (100, 60, 60)}, hands={'R': 'fist'},
      legs={'L': (-82, -96, -20), 'R': (-100, -98, -30)}, props=[('mid', racket('PR', 60)), ('front', ball(22, 'PL', (10, 140), 'tennis'))])
    f('Volleyball spike', 'woman-volleyball', view='S', torso=100, hair='ponytail', top='tank', bottom='shorts', arms={'L': (60, 75), 'R': (120, 70)},
      legs={'L': (-110, -140, -60), 'R': (-70, -120, -50)}, air=180, props=[('front', ball(52, 'PR', (60, 70), 'volley'))])
    f('Basketball dribble', 'woman-basketball', view='S', torso=72, head=80, hair='ponytail', top='tank', bottom='shorts', arms={'L': (-30, -10), 'R': (-70, -75, -80)},
      legs={'L': (-62, -110, 0), 'R': (-118, -96, -10)}, props=[('front', ball(54, 'PR', (10, -120), 'basket'))])
    f('Football kick', 'woman-football', view='S', torso=100, hair='ponytail', top='tee_f', bottom='shorts', arms={'L': (-20, -5), 'R': (-150, -165)},
      legs={'L': (-95, -92, 0), 'R': (-35, -15, -10)}, props=[('front', ball(58, 'TR', (56, 10), 'soccer'))])
    f('Swimming', 'woman-swimming', view='S', torso=0, head=0, top='tank', bottom='shorts', hair='bald', hat='helmet', arms={'L': (80, 10, 0), 'R': (4, 4, 4)},
      legs={'L': (178, 175, 175), 'R': (184, 186, 186)}, props=[('back', water(16, (-700, 700)))])
    f('Riding a bicycle', 'woman-cycling', **{k: v for k, v in bike_pose('f').items() if k != 'kind'})
    f('Working on a laptop', 'woman-laptop', view='S', torso=96, hair='bob', top='long', bottom='trousers', arms={'L': ('ik', (150, 40), -1, 0), 'R': ('ik', (170, 30), -1, 0)},
      legs={'L': (0, -90, 0), 'R': (4, -92, 0)}, props=[('back', chair()), ('mid', laptop((150, 6), 0))])
    f('Holding a coffee', 'woman-coffee', view='F', hair='long', top='long', bottom='trousers', arms={'L': (-101, -97, -95), 'R': (-85, 80, 95)}, k={'uaR': 0.8, 'faR': 0.8}, hands={'L': 'fist', 'R': 'fist'},
      legs=STAND_F(), props=[('front', cup('PR', (0, 10))), ('front', bag('PL', kind='handbag'))])
    f('Painting at an easel', 'woman-painter', view='S', hair='bun', top='long', skirt=1.2, arms={'L': (-70, 10), 'R': (-15, 35, 30)}, hands={'R': 'fist'}, legs=STAND_S(),
      props=[('back', easel(380)), ('mid', palette('PL')), ('front', brush('PR', 30))])
    f('Playing the violin', 'woman-violin', view='S', head=80, hair='bun', top='dress', skirt=1.35, arms={'L': ('ik', (290, 290), -1, 20), 'R': ('ik', (150, 250), -1, 40)}, hands={'L': 'fist', 'R': 'fist'}, legs=STAND_S(),
      props=[('mid', violin(-10)), ('front', bow_stick('PR', 140, 380))])
    f('Singing', 'woman-singing', view='F', hair='long', top='dress', skirt=1.4, arms={'L': (-150, -170, -175), 'R': (-95, 100, 100)}, k={'uaR': 0.55}, hands={'R': 'fist'},
      legs=STAND_F(), props=[('front', mic('PR', 95))])
    f('Watering plants', 'woman-watering', view='S', torso=92, hair='ponytail', top='tee_f', bottom='trousers', arms={'L': (-88, -84), 'R': (-40, -10, -10)}, hands={'R': 'fist'}, legs=STAND_S(), hat='sunhat',
      props=[('front', watering_can('PR')), ('back', plant_pot(300, 1.0, 'PR'))])
    f('Yoga: downward dog', 'woman-yoga-downward-dog', view='S', torso=-35, head=-60, hair='bun', top='tank', bottom='leggings', arms={'L': (-55, -55, 0), 'R': (-52, -52, 0)},
      legs={'L': (-125, -120, 0), 'R': (-122, -118, 0)}, hands={'L': 'flat', 'R': 'flat'}, ground_line=True)
    f('Yoga: cobra', 'woman-yoga-cobra', view='S', torso=36, head=70, hair='bun', top='tank', bottom='leggings', arms={'L': (-94, -90, 0), 'R': (-90, -90, 0)}, hands={'L': 'flat', 'R': 'flat'},
      legs={'L': (182, 180, 180), 'R': (178, 180, 180)}, ground_line=True)
    f('Yoga: bridge', 'woman-yoga-bridge', view='S', torso=218, head=180, hair='bun', top='tank', bottom='leggings', arms={'L': (-30, -2, 0), 'R': (-28, 0, 0)}, hands={'L': 'flat', 'R': 'flat'},
      legs={'L': (8, -95, 0), 'R': (4, -93, 0)}, ground_line=True)
    f('Yoga: chair pose', 'woman-yoga-chair', view='S', torso=68, head=75, hair='bun', top='tank', bottom='leggings', arms={'L': (72, 74), 'R': (68, 70)},
      legs={'L': (-38, -112, 0), 'R': (-34, -108, 0)}, ground_line=True)
    f('Cheerleader', 'woman-cheerleader', view='F', hair='ponytail', top='tank', skirt=0.55, arms={'L': (135, 125), 'R': (45, 55)}, hands=FISTS(), legs={'L': (-98, -94), 'R': (-82, -86)},
      props=[('front', pompom('PL')), ('front', pompom('PR'))])
    f('Flamenco dancer', 'woman-flamenco', view='F', hair='bun', top='dress', skirt=1.7, flare=90, heels=True, arms={'L': (115, 30, 0), 'R': (-140, -40, -20)}, hands={'R': 'fist'},
      legs={'L': (-96, -92), 'R': (-80, -86)})
    f('Lying down reading', 'woman-lying-reading', view='S', torso=28, head=40, hair='long', top='tee_f', bottom='trousers', arms={'L': (-100, 5, 15), 'R': (-95, 10, 15)},
      legs={'L': (182, 112, 30), 'R': (178, 95, 20)}, props=[('front', book(at='PR', off=(50, 50), w=160, h=110, ang=20))])
    f('Tai chi', 'woman-tai-chi', view='F', hair='bun', top='long', bottom='trousers', arms={'L': (175, 172, 172), 'R': (-20, -70, -90)}, hands={'R': 'fist'}, legs={'L': (-118, -96), 'R': (-62, -84)})
    f('Taking a selfie', 'woman-selfie', view='F', hair='long', top='tee_f', bottom='skirt', arms={'L': (-140, -40, -20), 'R': (30, 45, 60)}, hands=FISTS(), legs=STAND_F(), props=[('front', phone('PR', 80, (4, 20)))])
    f('Student with a backpack', 'woman-student', view='S', hair='ponytail', backpack=True, top='tee_f', bottom='jeans', arms={'L': (-70, -52), 'R': (-80, 40, 60)}, legs={'L': (-108, -122, -24), 'R': (-72, -94, 10)},
      props=[('front', book(at='PR', off=(-20, -10), w=40, h=170, ang=0, open_=False))])
    f('Cartwheel', 'woman-cartwheel', view='F', torso=-90, head=-90, hair='ponytail', top='tank', bottom='leggings', arms={'L': (-68, -68, -85), 'R': (-112, -112, -95)}, hands={'L': 'flat', 'R': 'flat'},
      legs={'L': (55, 58), 'R': (125, 122)}, ground_line=True)
    f('Gardening', 'woman-gardening', view='S', torso=70, head=50, hair='bob', top='tee_f', bottom='trousers', arms={'L': (-70, -60, -60), 'R': (-62, -50, -40)}, hands=FISTS(),
      legs={'L': (-92, 180, -110), 'R': (-88, 178, -110)}, hat='sunhat', props=[('back', plant_pot(330, 0.8))])
    f('Carrying shopping bags', 'woman-shopping', view='F', hair='bob', top='long', bottom='skirt', heels=True, arms={'L': (-101, -97), 'R': (-79, -83)}, hands=FISTS(), legs=STAND_F(),
      props=[('front', bag('PL')), ('front', bag('PR'))])
    f('Holding an umbrella', 'woman-umbrella', view='S', torso=88, hair='bob', top='coat', bottom='trousers', arms={'L': (-88, -84), 'R': (-50, 75)}, hands={'R': 'fist'},
      legs={'L': (-108, -122, -24), 'R': (-72, -94, 10)}, props=[('front', umbrella('PR'))])
    f('Sitting on a chair', 'woman-sitting', view='S', torso=96, hair='long', top='tee_f', skirt=0.95, flare=4, arms={'L': (-72, -2), 'R': (-76, -6)}, legs={'L': (0, -90, 0), 'R': (4, -92, 0)},
      props=[('back', chair())])
    f('Kneeling to tie a shoelace', 'woman-tying-shoelace', view='S', torso=35, head=10, hair='ponytail', top='tee_f', bottom='leggings', arms={'L': (-82, -88, -60), 'R': (-80, -85, -60)},
      legs={'L': (-90, 182, -110), 'R': (2, -95, 0)})
    f('Waving goodbye', 'woman-waving-goodbye', view='S', hair='bob', top='coat', bottom='trousers', arms={'L': (-88, -84), 'R': (40, 100, 100)}, legs=STAND_S())
    f('Flying a kite', 'woman-kite', view='S', torso=95, head=110, hair='long', top='tee_f', bottom='shorts', arms={'L': (-88, -84), 'R': (20, 50, 50)}, hands={'R': 'fist'}, legs=STAND_S(),
      props=[('front', kite('PR'))])
    f('Fitness stretch', 'woman-fitness-stretch', view='F', torso=76, head=72, hair='ponytail', top='tank', bottom='leggings', arms={'L': (98, 20, 10), 'R': (-70, -78)}, legs={'L': (-100, -96), 'R': (-80, -84)})
    return M, F

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    only = sys.argv[3] if len(sys.argv) > 3 else None
    M, F = poses()
    items = []
    for cat, L in (('malepose', M), ('femalepose', F)):
        for name, slug, p in L:
            if only and only not in slug: continue
            try:
                lines = figure(**p)
            except Exception as e:
                print('FAILED', slug, repr(e)); raise
            it = Item(cat, name, lines); it.slug = slug; items.append(it)
    save(items, OUT)
    P = sorted(export_size(i.lines)[0] for i in items)
    print(len([i for i in items if i.cat == 'malepose']), 'male,', len([i for i in items if i.cat == 'femalepose']), 'female; median', P[len(P) // 2], 'max', P[-1])
    if SHEET:
        for i in range(0, len(items), 20):
            sheet(items[i:i + 20], SHEET.replace('.png', f'_{i // 20}.png'), cols=5, cell=3.0)
