"""Shoes for gen_wear: side (lateral) views drawn in y-up coordinates (ground at y = 0, toe to the
right, about 1000 long), plus top views, sole views and pairs. Each function returns a Scene."""
import math
from gen_wear_kit import *


# ---------------------------------------------------------------- shared parts
def lace_row(sc, edge, n, s0, s1, inset=22, over=24, r=7.0, lean=0.05, eyelets=True, hooks=0):
    """Eyelets just below the eyestay edge (edge runs from the collar to the toe) and the lace
    crossings going over the tongue. hooks: the top few are speed hooks instead of eyelets."""
    low = par(edge, -inset); top = par(edge, over)
    pts = []
    for i in range(n):
        s = s0 + (s1 - s0) * i / max(1, n - 1)
        e, t = at(low, s)
        q, _ = at(top, min(1, s + lean))
        pts.append(e)
        if i < hooks:
            nx, ny = normal(t)
            sc.line([(e[0] - t[0] * 6, e[1] - t[1] * 6), (e[0] + nx * 16 - t[0] * 4, e[1] + ny * 16 - t[1] * 4), (e[0] + nx * 22 + t[0] * 8, e[1] + ny * 22 + t[1] * 8)])
            sc.shape(circle(e[0], e[1], r * 0.8, n=12))
        sc.line([e, q])
    if eyelets:
        for i, e in enumerate(pts):
            if i >= hooks: sc.shape(circle(e[0], e[1], r, n=14))
    return pts


def bow(sc, x, y, s=1.0, flip=False):
    """A lace bow seen from the side: two loops and two tails from the knot at (x, y) (y-up)."""
    f = -1 if flip else 1
    loops = [CC([(x, y), (x - f * 30 * s, y + 26 * s), (x - f * 62 * s, y + 24 * s), (x - f * 58 * s, y + 4 * s), (x - f * 26 * s, y - 2 * s)], n=8),
             CC([(x, y), (x + f * 14 * s, y + 34 * s), (x + f * 42 * s, y + 44 * s), (x + f * 48 * s, y + 24 * s), (x + f * 22 * s, y + 6 * s)], n=8)]
    tails = [C([(x, y), (x - f * 12 * s, y - 34 * s), (x - f * 26 * s, y - 74 * s)], n=8),
             C([(x, y), (x + f * 10 * s, y - 30 * s), (x + f * 28 * s, y - 58 * s)], n=8)]
    for P in tails + loops: halo(sc, P, 5)
    sc.shape(circle(x, y, 8 * s, n=14))


def block_heel(sc, x0, x1, h, lift=12, layers=(), slant=6, flare=6):
    """A low block heel: back at x0, breast at x1, top at h (tucked under the sole)."""
    g = G(J([(x0, 0), (x0 - slant * 0.5, h * 0.5), (x0 - slant, h + 10)],
            C([(x1 + flare, h + 10), (x1 - 2, h * 0.55), (x1 - flare * 0.4, 0)], n=8)))
    sc.geom(g)
    for y in ((lift,) if lift else ()) + tuple(layers):
        sc.lines(clip([[(x0 - 30, y), (x1 + 30, y)]], g))
    return g


def sole_band(sc, bottom, t, front=None):
    """A sole of thickness t over the curve `bottom` (heel to toe). Returns (polygon, top curve)."""
    top = par(bottom, t)
    if front is None:
        front = [bottom[-1], top[-1]]
    g = G(J(bottom, front, top[::-1]))
    sc.geom(g)
    return g, top


def opening(sc, far, near_low):
    """The far side of the collar seen through the opening: a shape behind the upper whose top
    edge `far` shows above the near topline."""
    sc.shape(J(far, near_low[::-1]))


def upper_from(outline, bottom, lift=4.0):
    """The upper: the region under `outline` (heel to toe, ends inside the sole) and above the
    sole's bottom curve (lifted a little so the sole hides the join)."""
    big = G(J(outline, [(outline[-1][0], -3000), (outline[0][0], -3000)]))
    pb = par(bottom, lift)
    cut = G(J([(pb[0][0] - 400, pb[0][1])], pb, [(pb[-1][0] + 400, pb[-1][1]), (pb[-1][0] + 400, -4000), (pb[0][0] - 400, -4000)]))
    g = big.difference(cut)
    if g.geom_type == 'MultiPolygon': g = max(g.geoms, key=lambda q: q.area)
    return g


def low_sole(sc, h=80, hx=(20, 225), t=22, spring=50, flat=(620, 780), nose=14, layers=(44,), lift=14, heel=True):
    """Heel block plus a leather sole that curves down from the heel breast to the ball and lifts
    at the toe. Returns (bottom, top, sole polygon)."""
    x0, x1 = hx
    bottom = C([(x0 - 6, h), (x0 + 100, h), (x1 + 4, h - 2), (x1 + 90, h - 12), (x1 + 190, h * 0.5), (x1 + 290, h * 0.16), (flat[0], 2),
                ((flat[0] + flat[1]) / 2, 0), (flat[1], 4), (880, spring * 0.38), (945, spring * 0.76), (982, spring)])
    if heel: block_heel(sc, x0, x1, h, lift=lift, layers=layers)
    tp = par(bottom, t)
    front = C([(982, spring), (996, spring + nose * 0.7), tp[-1]], n=6)
    sole = G(J(bottom, front[1:-1], tp[::-1]))
    return bottom, tp, sole


def round_sole(bottom, t):
    """A sole of thickness t over `bottom`, with rounded ends."""
    return LineString(par(bottom, t / 2)).buffer(t / 2, cap_style=1, quad_segs=8)


def cup_sole(th=136, tt=96, s=68, xb=8, xc=60):
    """A sneaker sole (midsole + outsole): heel stack th, forefoot tt, toe spring s.
    Returns (bottom, top curve from toe to heel, polygon)."""
    bottom = C([(xc, 0), (300, 0), (560, 0), (720, 2), (830, s * 0.22), (908, s * 0.6), (958, s)])
    nose = C([(958, s), (986, s + 16), (998, s + 38)], n=6)
    top = C([(998, s + 38), (964, s + 46), (900, tt + 10), (760, tt), (560, tt), (400, tt + (th - tt) * 0.25), (250, tt + (th - tt) * 0.55),
             (100, tt + (th - tt) * 0.9), (xb + 14, th)])
    heel = C([(xb + 14, th), (xb, th * 0.82), (xb, th * 0.45), (xb + 20, th * 0.17), (xc, 0)])
    return bottom, top, G(J(bottom, nose, top, heel))


# ---------------------------------------------------------------- sneakers and sport shoes
def running_shoe():
    sc = Scene()
    bottom, stop, sole = cup_sole(136, 96, 68)
    heel_up = C([(24, 120), (14, 180), (14, 240), (24, 290), (44, 322)])
    collar = C([(44, 322), (84, 330), (132, 318), (185, 292), (236, 284), (284, 302), (322, 334)])
    throat = C([(322, 334), (420, 310), (520, 278), (610, 248), (690, 226)])
    vamp = C([(690, 226), (790, 206), (868, 186), (926, 166), (966, 146), (990, 124), (1000, 100), (996, 80)])
    upper = upper_from(J(heel_up, collar, throat, vamp), bottom, 30)
    sc.shape(rot(rect(24, 290, 40, 74, r=14), 0.14, 44, 330))
    opening(sc, C([(44, 322), (110, 338), (190, 318), (262, 312), (310, 330)]), C([(44, 300), (190, 270), (310, 300)]))
    tt = par(throat, 22)
    sc.shape(J(C([(300, 300), (296, 352), (310, 378), (346, 384), (374, 360)]), [p for p in tt if p[0] > 380], [(700, 236), (680, 200), (300, 300)]))
    sc.geom(upper)
    sc.lines(clip([par(collar, -16)], upper, 4))
    sc.lines(clip([par(throat, -44)], upper, 2))
    hc = C([(108, 328), (140, 260), (180, 190), (246, 128)])
    sc.lines(clip([hc, par(hc, -12)], upper))
    tc = C([(806, 204), (836, 168), (872, 138), (930, 118)])
    sc.lines(clip([tc, par(tc, 12)], upper))
    sc.lines(clip([C([(200, 152), (400, 142), (600, 138), (760, 142), (850, 152)])], upper, 4))
    lace_row(sc, throat, 6, 0.08, 0.9, inset=22, over=22, r=6.5, lean=0.05)
    bow(sc, *at(par(throat, 4), 0.1)[0], s=0.9)
    sc.geom(sole)
    sc.lines(clip([par(bottom, 22)], sole))
    sc.lines(clip([[(x, -5), (x, 30)] for x in range(110, 300, 46)] + [[(x, -5), (x + 2, 30)] for x in range(560, 800, 46)], sole))
    sc.lines(clip([C([(24, 84), (120, 100), (240, 84), (380, 66), (520, 60)])], sole, 2))
    return sc


def dress_sole(h=85, hx=(20, 225), spring=48, flat=(620, 780), toe=990):
    x0, x1 = hx
    return C([(x0 - 8, h), (x0 + 100, h), (x1 + 4, h - 2), (x1 + 90, h - 12), (x1 + 190, h * 0.52), (x1 + 290, h * 0.17), (flat[0], 2),
              ((flat[0] + flat[1]) / 2, 0), (flat[1], 4), (880, spring * 0.36), (945, spring * 0.74), (toe, spring)])


def oxford():
    sc = Scene()
    bottom = dress_sole(85, (20, 225), 48)
    block_heel(sc, 20, 225, 85, lift=14, layers=(46,))
    sole = round_sole(bottom, 22)
    out = J(C([(22, 104), (8, 150), (8, 214), (20, 262), (38, 282)]), C([(38, 282), (110, 278), (190, 264), (250, 270), (300, 292)]))
    facing = C([(300, 292), (390, 276), (474, 250)])
    vamp = C([(474, 250), (570, 234), (670, 210), (770, 182), (860, 156), (926, 134), (966, 112), (988, 88), (994, 66)])
    upper = upper_from(J(out, facing, vamp), bottom, 12)
    opening(sc, C([(38, 282), (110, 294), (200, 282), (270, 286)]), C([(38, 250), (270, 250)]))
    sc.shape(J(C([(286, 276), (290, 300), (312, 312)]), [p for p in par(facing, 12) if p[0] > 316], [(490, 250), (480, 220), (290, 250)]))
    sc.geom(upper)
    sc.lines(clip([par(bottom, 32)], upper))
    sc.lines(clip([C([(300, 292), (318, 262), (360, 242), (452, 226), (482, 248)])], upper))
    sc.lines(clip([C([(470, 232), (430, 190), (404, 150), (394, 110)])], upper))
    cap = C([(796, 176), (774, 146), (768, 116), (776, 96)])
    sc.lines(clip([cap, par(cap, 12)], upper))
    sc.lines(clip([C([(74, 280), (96, 210), (140, 160), (232, 124)])], upper))
    lace_row(sc, facing, 4, 0.12, 0.86, inset=18, over=12, r=5.5, lean=0.08)
    sc.geom(sole)
    return sc


def chelsea_boot():
    sc = Scene()
    bottom = dress_sole(76, (20, 222), 48)
    block_heel(sc, 20, 222, 76, lift=13, layers=(42,))
    sole = round_sole(bottom, 22)
    back = C([(22, 100), (8, 200), (10, 360), (24, 520), (40, 610)])
    topl = C([(40, 610), (190, 616), (350, 606)])
    front = C([(350, 606), (356, 500), (372, 400), (420, 320), (500, 268), (600, 232), (700, 200), (790, 172), (870, 148), (930, 126), (968, 104), (988, 82), (994, 66)])
    upper = upper_from(J(back, topl, front), bottom, 12)
    sc.shape(rot(rect(24, 566, 46, 104, r=16), 0.06, 46, 610))
    opening(sc, C([(40, 610), (120, 626), (230, 630), (350, 614)]), C([(40, 580), (350, 580)]))
    sc.geom(upper)
    gus = G(C([(130, 660), (134, 530), (162, 420), (200, 370), (236, 420), (262, 530), (268, 660)], n=12)).intersection(upper)
    sc.geom(gus)
    for x in range(144, 262, 14):
        sc.lines(clip([[(x, 300), (x, 700)]], gus, 4))
    sc.lines(clip([par(topl, -16)], upper.difference(gus.buffer(6)), 4))
    sc.lines(clip([C([(590, 236), (556, 180), (536, 130), (530, 96)])], upper))
    sc.lines(clip([par(bottom, 32)], upper))
    sc.geom(sole)
    return sc


def stiletto():
    sc = Scene()
    heel = G(J(C([(8, 404), (30, 300), (62, 160), (84, 20), (86, 0)], n=10), [(108, 0)], C([(110, 20), (128, 150), (160, 290), (206, 392)], n=10)))
    sc.geom(heel)
    sc.lines(clip([[(60, 16), (130, 16)]], heel))
    bottom = C([(0, 404), (110, 400), (190, 385), (280, 340), (380, 260), (470, 175), (560, 95), (640, 38), (720, 8), (800, 0), (880, 2), (950, 10), (996, 22)])
    sole = round_sole(bottom, 14)
    collar = C([(0, 410), (-4, 450), (4, 504), (70, 498), (160, 468), (260, 414), (360, 344), (450, 272), (530, 218), (600, 196)])
    vamp = C([(600, 196), (680, 182), (770, 152), (860, 112), (930, 74), (978, 44), (1004, 26)])
    upper = upper_from(J(collar, vamp), bottom, 7)
    opening(sc, C([(4, 504), (80, 516), (170, 490), (260, 434), (330, 384)]), C([(4, 440), (330, 330)]))
    sc.geom(upper)
    sc.geom(sole)
    return sc


def rain_boot():
    sc = Scene()
    bottom = C([(60, 0), (270, 0), (304, 9), (362, 14), (420, 9), (452, 0), (700, 4), (790, 22), (840, 48)])
    nose = C([(840, 48), (858, 76), (860, 100)], n=6)
    stop = C([(860, 100), (800, 92), (650, 88), (420, 90), (200, 94), (44, 98)])
    heel = C([(44, 98), (28, 76), (30, 32), (60, 0)])
    sole = G(J(bottom, nose, stop, heel))
    back = C([(46, 90), (34, 160), (28, 300), (38, 560), (48, 820), (54, 1010)])
    topl = C([(54, 1010), (240, 1016), (430, 1024)])
    front = C([(430, 1024), (426, 840), (418, 640), (416, 520), (440, 400), (500, 320), (590, 276), (690, 246), (770, 226), (826, 198), (856, 160), (866, 118), (862, 92)])
    upper = upper_from(J(back, topl, front), bottom, 40)
    opening(sc, C([(54, 1010), (180, 1032), (320, 1042), (430, 1032)]), C([(54, 960), (430, 960)]))
    sc.geom(upper)
    sc.lines(clip([par(topl, -60)], upper))
    sc.lines(clip([C([(40, 200), (300, 196), (520, 196), (640, 196)]), C([(640, 196), (700, 170), (740, 130), (750, 96)])], upper))
    sc.geom(sole)
    sc.lines(clip([par(bottom, 34)], sole))
    for x in list(range(96, 270, 56)) + list(range(470, 800, 56)):
        sc.lines(clip([[(x, -5), (x + 6, 36)]], sole, 1))
    return sc


def vulc_sole(t=80, s=40, xb=24, ribbed=0, foxing=None):
    """A flat vulcanised (canvas sneaker) sole of height t: (bottom, polygon)."""
    bottom = C([(xb + 18, 0), (400, 0), (820, 0), (910, 8), (962, s * 0.55), (990, s)])
    nose = C([(990, s), (1002, (s + t) / 2 + 4), (996, t + 6)], n=6)
    top = C([(996, t + 6), (960, t + 4), (800, t), (500, t), (200, t), (xb + 6, t)])
    heel = C([(xb + 6, t), (xb - 6, t * 0.62), (xb - 4, t * 0.22), (xb + 18, 0)])
    return bottom, top, G(J(bottom, nose, top, heel))


def high_top():
    sc = Scene()
    bottom, top, sole = vulc_sole(84, 44)
    back = C([(26, 70), (16, 160), (14, 300), (24, 440), (44, 540), (70, 584)])
    collar = C([(70, 584), (130, 580), (200, 568), (262, 574), (304, 592)])
    throat = C([(304, 592), (330, 520), (370, 430), (430, 344), (520, 280), (630, 236)])
    vamp = C([(630, 236), (730, 212), (830, 186), (906, 160), (956, 136), (988, 108), (998, 84)])
    upper = upper_from(J(back, collar, throat, vamp), bottom, 40)
    opening(sc, C([(70, 584), (140, 598), (220, 590), (290, 600)]), C([(70, 550), (290, 550)]))
    tt = par(throat, 24)
    sc.shape(J(C([(270, 560), (268, 616), (290, 640), (330, 642), (350, 616)]), [p for p in tt if p[1] < 600], [(650, 250), (630, 210), (300, 400)]))
    sc.geom(upper)
    sc.lines(clip([par(collar, -16)], upper, 4))
    sc.lines(clip([par(throat, -42)], upper, 2))
    sc.lines(clip([par(back, -30)], upper.difference(box(-50, -50, 2000, 100)), 2))
    sc.lines(clip([C([(612, 240), (580, 180), (560, 120), (556, 84)])], upper))
    cap = C([(790, 80), (810, 150), (860, 178), (930, 160)])
    sc.lines(clip([cap, par(cap, -14)], upper))
    lace_row(sc, throat, 8, 0.06, 0.92, inset=22, over=24, r=7, lean=0.045)
    bow(sc, *at(par(throat, 4), 0.07)[0], s=0.9)
    sc.geom(sole)
    sc.lines(clip([par(bottom, 30), par(bottom, 46)], sole, 0))
    return sc


def slip_on():
    sc = Scene()
    bottom, top, sole = vulc_sole(70, 34)
    back = C([(28, 60), (16, 130), (20, 200), (40, 244)])
    collar = C([(40, 244), (120, 240), (220, 218), (320, 214), (390, 224), (430, 244), (470, 256)])
    vamp = C([(470, 256), (580, 246), (700, 214), (820, 180), (910, 148), (962, 120), (990, 94), (998, 72)])
    upper = upper_from(J(back, collar, vamp), bottom, 34)
    opening(sc, C([(40, 244), (130, 258), (240, 240), (330, 236), (420, 252)]), C([(40, 210), (420, 210)]))
    sc.geom(upper)
    sc.lines(clip([par(collar, -16)], upper, 4))
    for g0, g1 in (((372, 222), (400, 140)), ((400, 140), (432, 236))):
        sc.line([g0, g1])
    for y in (160, 180, 200):
        sc.lines(clip([[(380, y), (430, y + 6)]], G([(372, 222), (400, 140), (432, 236)]), 3))
    sc.lines(clip([par(vamp, -18)], upper.difference(box(-50, -50, 430, 1000)), 4))
    sc.lines(clip([par(bottom, 92)], upper))
    sc.geom(sole)
    sc.lines(clip([par(bottom, 26)], sole))
    sc.lines(clip([[(x, 30), (x, 64)] for x in range(60, 960, 18)], sole, 4))
    return sc


def platform_sneaker():
    sc = Scene()
    T = 180
    bottom = C([(30, 0), (400, 0), (850, 0), (930, 6), (975, 30), (994, 64)])
    nose = C([(994, 64), (1004, 120), (996, T + 10)], n=8)
    top = C([(996, T + 10), (960, T + 8), (800, T), (500, T), (200, T), (28, T)])
    heel = C([(28, T), (14, T * 0.7), (14, T * 0.3), (30, 0)])
    sole = G(J(bottom, nose, top, heel))
    b2 = [(x, y + T - 60) for x, y in C([(30, 0), (400, 0), (850, 0), (930, 6), (975, 30), (994, 64)])]
    back = C([(30, T - 10), (20, T + 70), (24, T + 160), (44, T + 214)])
    collar = C([(44, T + 214), (110, T + 214), (190, T + 188), (250, T + 190), (300, T + 214)])
    throat = C([(300, T + 214), (400, T + 196), (500, T + 166), (600, T + 138)])
    vamp = C([(600, T + 138), (700, T + 120), (800, T + 100), (880, T + 78), (944, T + 54), (980, T + 28), (994, T + 4)])
    upper = upper_from(J(back, collar, throat, vamp), b2, 40)
    opening(sc, C([(44, T + 214), (120, T + 226), (210, T + 206), (280, T + 214)]), C([(44, T + 190), (280, T + 190)]))
    tt = par(throat, 20)
    sc.shape(J(C([(270, T + 190), (272, T + 238), (300, T + 254), (330, T + 250)]), [p for p in tt if p[0] > 336], [(620, T + 150), (600, T + 120), (280, T + 170)]))
    sc.geom(upper)
    sc.lines(clip([par(collar, -15)], upper, 4))
    sc.lines(clip([par(throat, -40)], upper, 2))
    sc.lines(clip([C([(640, T + 136), (610, T + 90), (600, T + 20)])], upper))
    sc.lines(clip([C([(70, T + 214), (110, T + 120), (200, T + 40)])], upper))
    lace_row(sc, throat, 5, 0.1, 0.88, inset=20, over=20, r=6.5, lean=0.06)
    sc.geom(sole)
    for y in (46, 92, 138):
        sc.lines(clip([[(-10, y), (1100, y)]], sole, 0))
    return sc


def football_boot():
    sc = Scene()
    bottom = C([(30, 46), (200, 40), (420, 36), (620, 32), (800, 36), (920, 54), (994, 90)])
    plate = round_sole(bottom, 20)
    studs = []
    for x in (70, 190, 560, 690, 810, 920):
        (px, py), t = at(bottom, (x - 30) / 964)
        studs.append(G([(px - 26, py + 6), (px + 26, py + 6), (px + 16, py - 40 + (py - 40) * 0.0), (px - 16, py - 40)]))
    for g in studs: sc.geom(g)
    back = C([(34, 70), (22, 140), (28, 220), (50, 262)])
    collar = C([(50, 262), (120, 254), (196, 228), (262, 236), (306, 262)])
    throat = C([(306, 262), (420, 240), (540, 206), (650, 178)])
    vamp = C([(650, 178), (760, 158), (860, 136), (930, 114), (976, 94), (996, 78)])
    upper = upper_from(J(back, collar, throat, vamp), bottom, 10)
    opening(sc, C([(50, 262), (130, 270), (210, 250), (290, 262)]), C([(50, 236), (290, 236)]))
    tt = par(throat, 20)
    sc.shape(J(C([(282, 236), (284, 290), (314, 308), (350, 296)]), [p for p in tt if p[0] > 356], [(670, 190), (650, 160), (290, 220)]))
    sc.geom(upper)
    sc.lines(clip([par(collar, -15)], upper, 4))
    sc.lines(clip([par(throat, -38)], upper, 2))
    tc = C([(760, 160), (780, 120), (820, 86), (880, 66)])
    sc.lines(clip([tc, par(tc, 12)], upper))
    sc.lines(clip([C([(70, 260), (100, 170), (160, 100), (230, 60)])], upper))
    sc.lines(clip([C([(260, 60), (420, 74), (600, 70), (720, 80)])], upper, 4))
    lace_row(sc, throat, 6, 0.08, 0.9, inset=20, over=20, r=6, lean=0.05)
    flap = G(J(C([(300, 300), (340, 312), (420, 300), (520, 268), (590, 240)]), C([(590, 240), (580, 196), (540, 178)]), C([(540, 178), (440, 206), (360, 232), (300, 250)])))
    sc.geom(flap)
    sc.lines(clip([par(C([(540, 178), (440, 206), (360, 232), (300, 250)]), -12)], flap, 3))
    sc.geom(plate)
    return sc


def track_spike():
    sc = Scene()
    bottom = C([(40, 22), (200, 18), (380, 18), (540, 20), (700, 14), (840, 26), (930, 56), (990, 104)])
    sole = round_sole(bottom, 16)
    plate_c = sub(bottom, 0.5, 1.0)
    plate = round_sole(plate_c, 22)
    pins = []
    for s in (0.1, 0.3, 0.5, 0.7, 0.88):
        (px, py), t = at(plate_c, s); nx, ny = normal(t)
        pins.append(G([(px - t[0] * 12, py - t[1] * 12), (px + t[0] * 12, py + t[1] * 12), (px - nx * 34, py - ny * 34)]))
    for g in pins: sc.geom(g)
    back = C([(44, 30), (30, 90), (34, 150), (54, 184)])
    collar = C([(54, 184), (120, 178), (196, 160), (256, 166), (300, 184)])
    throat = C([(300, 184), (400, 172), (500, 152), (600, 136)])
    vamp = C([(600, 136), (700, 128), (800, 120), (880, 114), (944, 118), (984, 128), (1000, 116)])
    upper = upper_from(J(back, collar, throat, vamp), bottom, 8)
    opening(sc, C([(54, 184), (130, 194), (210, 178), (284, 186)]), C([(54, 160), (284, 160)]))
    tt = par(throat, 16)
    sc.shape(J(C([(280, 160), (282, 198), (306, 210), (330, 200)]), [p for p in tt if p[0] > 336], [(620, 146), (600, 120), (290, 150)]))
    sc.geom(upper)
    strap = G([(430, 200), (500, 186), (500, 10), (430, 10)]).intersection(upper)
    sc.geom(strap)
    sc.lines(clip([[(438, 0), (438, 400)], [(492, 0), (492, 400)]], strap, 0))
    sc.lines(clip([par(throat, -30)], upper.difference(strap.buffer(2)), 2))
    sc.lines(clip([C([(80, 182), (110, 110), (170, 50)])], upper))
    sc.lines(clip([C([(780, 122), (800, 80), (840, 52)])], upper))
    lace_row(sc, sub(throat, 0, 0.5), 3, 0.1, 0.9, inset=16, over=16, r=5, lean=0.1)
    lace_row(sc, throat, 3, 0.62, 0.95, inset=16, over=16, r=5, lean=0.04)
    sc.geom(sole)
    sc.geom(plate)
    return sc


def brogue():
    sc = Scene()
    bottom = dress_sole(85, (20, 225), 48)
    block_heel(sc, 20, 225, 85, lift=14, layers=(46,))
    sole = round_sole(bottom, 22)
    out = J(C([(22, 104), (8, 150), (8, 214), (20, 262), (38, 282)]), C([(38, 282), (110, 278), (190, 264), (250, 270), (300, 292)]))
    facing = C([(300, 292), (390, 276), (474, 250)])
    vamp = C([(474, 250), (570, 234), (670, 210), (770, 182), (860, 156), (926, 134), (966, 112), (988, 88), (994, 66)])
    upper = upper_from(J(out, facing, vamp), bottom, 12)
    opening(sc, C([(38, 282), (110, 294), (200, 282), (270, 286)]), C([(38, 250), (270, 250)]))
    sc.shape(J(C([(286, 276), (290, 300), (312, 312)]), [p for p in par(facing, 12) if p[0] > 316], [(490, 250), (480, 220), (290, 250)]))
    sc.geom(upper)
    sc.lines(clip([par(bottom, 32)], upper))
    seams = [C([(300, 292), (318, 262), (360, 242), (452, 226), (482, 248)]),
             C([(470, 232), (430, 190), (404, 150), (394, 110)]),
             C([(740, 192), (700, 166), (620, 140), (530, 120), (452, 104), (420, 98)]),
             C([(70, 280), (96, 210), (140, 160), (232, 124)])]
    for P in seams:
        sc.lines(clip([P], upper))
        sc.lines([c for c in dots_along(par(P, -13), 17, 4.2, 0.04, 0.96, n=8) if upper.buffer(-6).contains(Point(c[0]))])
    wing2 = par(seams[2], 13)
    sc.lines(clip([wing2], upper))
    lace_row(sc, facing, 4, 0.12, 0.86, inset=18, over=12, r=5.5, lean=0.08)
    sc.geom(sole)
    return sc


def derby():
    sc = Scene()
    bottom = C([(16, 0), (230, 0), (250, 12), (300, 20), (420, 16), (520, 4), (560, 0), (800, 2), (900, 18), (958, 40), (988, 62)])
    sole = LineString(par(bottom, 22)).buffer(22, cap_style=1, quad_segs=8)
    back = C([(22, 50), (10, 120), (10, 190), (22, 250), (42, 280)])
    collar = C([(42, 280), (110, 280), (190, 262), (256, 268), (310, 296)])
    facing = C([(310, 296), (400, 284), (500, 258)])
    vamp = C([(500, 258), (600, 246), (700, 224), (800, 196), (884, 164), (944, 132), (978, 104), (992, 76)])
    upper = upper_from(J(back, collar, facing, vamp), bottom, 24)
    opening(sc, C([(42, 280), (120, 294), (210, 282), (290, 292)]), C([(42, 250), (290, 250)]))
    sc.shape(J(C([(296, 280), (298, 312), (326, 322)]), [p for p in par(facing, 14) if p[0] > 330], [(520, 262), (510, 230), (300, 250)]))
    sc.geom(upper)
    q = C([(500, 258), (512, 222), (500, 170), (470, 120), (440, 80)])
    sc.lines(clip([q, par(q, 12)], upper))
    sc.lines(clip([par(back, -26)], upper.difference(box(-100, -100, 2000, 60)), 3))
    sc.lines(clip([par(collar, -14)], upper, 3))
    sc.lines(clip([par(bottom, 54)], upper))
    lace_row(sc, facing, 5, 0.1, 0.88, inset=18, over=14, r=6, lean=0.07)
    bow(sc, *at(par(facing, 4), 0.1)[0], s=0.8)
    sc.geom(sole)
    sc.lines(clip([par(bottom, 16)], sole))
    for x in range(50, 980, 40):
        if 236 < x < 540: continue
        sc.lines(clip([[(x, -10), (x, 16)]], sole, 0))
    return sc


def moc_stitch(sc, P, region, step=15, a=6):
    """A raised moccasin seam: the seam line with short stitches across it."""
    sc.lines(clip([P], region))
    sc.lines([q for q in ticks(P, step, -a, a, 0.02, 0.98) if region.buffer(-3).contains(Point(q[0])) and region.buffer(-3).contains(Point(q[1]))])


def loafer():
    sc = Scene()
    bottom = dress_sole(72, (20, 220), 46)
    block_heel(sc, 20, 220, 72, lift=13, layers=(40,))
    sole = round_sole(bottom, 22)
    back = C([(22, 92), (8, 150), (10, 200), (26, 238), (44, 250)])
    collar = C([(44, 250), (120, 246), (220, 226), (320, 222), (410, 236), (470, 258)])
    vamp = C([(470, 258), (560, 256), (660, 236), (760, 206), (850, 176), (920, 148), (962, 120), (988, 92), (994, 66)])
    upper = upper_from(J(back, collar, vamp), bottom, 12)
    opening(sc, C([(44, 250), (130, 262), (240, 244), (340, 240), (440, 256)]), C([(44, 220), (440, 220)]))
    sc.geom(upper)
    apron = C([(480, 236), (600, 216), (720, 186), (830, 152), (910, 124), (958, 104), (982, 86)])
    moc_stitch(sc, apron, upper)
    strap = G(J(C([(462, 300), (470, 250), (476, 206)], n=6), C([(476, 206), (540, 198), (612, 186)], n=8), C([(612, 186), (606, 230), (604, 290)], n=6), [(604, 320), (462, 320)])).intersection(upper)
    sc.geom(strap)
    sc.lines(clip([par(C([(476, 206), (540, 198), (612, 186)], n=8), 10)], strap, 0))
    slot = J(C([(506, 242), (536, 232), (568, 236)], n=8), C([(568, 236), (538, 246), (506, 242)], n=8))
    sc.shape(slot)
    sc.lines(clip([C([(70, 250), (96, 190), (140, 146), (230, 116)])], upper))
    sc.lines(clip([par(bottom, 32)], upper))
    sc.geom(sole)
    return sc


def monk_strap():
    sc = Scene()
    bottom = dress_sole(85, (20, 225), 48)
    block_heel(sc, 20, 225, 85, lift=14, layers=(46,))
    sole = round_sole(bottom, 22)
    back = C([(22, 104), (8, 150), (8, 214), (20, 262), (38, 282)])
    collar = C([(38, 282), (110, 278), (190, 264), (260, 272), (330, 300), (400, 304)])
    vamp = C([(400, 304), (480, 286), (570, 252), (670, 216), (770, 186), (860, 158), (926, 134), (966, 112), (988, 88), (994, 66)])
    upper = upper_from(J(back, collar, vamp), bottom, 12)
    opening(sc, C([(38, 282), (110, 294), (200, 282), (300, 300)]), C([(38, 250), (300, 250)]))
    sc.geom(upper)
    sc.lines(clip([par(bottom, 32)], upper))
    cap = C([(796, 176), (774, 146), (768, 116), (776, 96)])
    sc.lines(clip([cap, par(cap, 12)], upper))
    sc.lines(clip([C([(330, 300), (360, 240), (420, 190), (470, 150), (520, 120)])], upper))
    sc.lines(clip([C([(74, 280), (96, 210), (140, 160), (232, 124)])], upper))
    for k in range(2):
        a = (500 + 46 * k, 330 - 26 * k); b = (330 + 40 * k, 228 - 40 * k)
        d = (b[0] - a[0], b[1] - a[1]); n_ = math.hypot(*d); u = (d[0] / n_, d[1] / n_)
        tail = (b[0] + u[0] * 64, b[1] + u[1] * 64)
        band = thick([a, tail], 34, cap='flat').intersection(upper.buffer(40))
        band = band.intersection(G([(0, 0), (2000, 0), (2000, 2000), (0, 2000)])).difference(G(J(par(C([(38, 282), (110, 278), (190, 264), (260, 272), (330, 300), (400, 304), (480, 286), (570, 252)]), 0), [(600, 2000), (0, 2000)])))
        sc.geom(band)
        ang = math.degrees(math.atan2(u[1], u[0]))
        fr = affinity.rotate(G(rect(-22, -30, 44, 60, r=8)), ang, origin=(0, 0)); fr = affinity.translate(fr, *b)
        hole = affinity.rotate(G(rect(-9, -17, 18, 34, r=3)), ang, origin=(0, 0)); hole = affinity.translate(hole, *b)
        sc.geom(fr); sc.geom(hole)
        sc.line([(b[0] - u[0] * 6, b[1] - u[1] * 6), (b[0] + u[0] * 14, b[1] + u[1] * 14)])
    sc.geom(sole)
    return sc


def boat_shoe():
    sc = Scene()
    bottom = C([(40, 0), (400, 0), (800, 0), (900, 10), (958, 30), (990, 54)])
    nose = C([(990, 54), (1002, 72), (996, 90)], n=6)
    top = C([(996, 90), (960, 88), (800, 82), (500, 82), (200, 84), (26, 86)])
    heel = C([(26, 86), (12, 60), (16, 20), (40, 0)])
    sole = G(J(bottom, nose, top, heel))
    back = C([(28, 70), (14, 140), (18, 210), (38, 256)])
    collar = C([(38, 256), (120, 254), (220, 234), (320, 232), (400, 246), (460, 268)])
    vamp = C([(460, 268), (560, 264), (660, 240), (760, 210), (850, 178), (920, 148), (964, 120), (990, 96), (998, 76)])
    upper = upper_from(J(back, collar, vamp), bottom, 40)
    opening(sc, C([(38, 256), (130, 270), (240, 252), (340, 250), (430, 264)]), C([(38, 226), (430, 226)]))
    sc.geom(upper)
    apron = C([(470, 244), (600, 226), (720, 196), (830, 162), (910, 132), (958, 110), (986, 90)])
    moc_stitch(sc, apron, upper)
    lc = par(collar, -14)
    sc.lines(clip([lc], upper.difference(box(330, -100, 2000, 1000)), 3))
    for s in (0.25, 0.5, 0.72):
        (x, y), _ = at(lc, s); sc.shape(circle(x, y, 6, n=12))
    sc.lines(clip([C([(100, 254), (120, 180), (170, 120), (240, 96)])], upper))
    for x in (370, 420):
        sc.shape(circle(x, 222 + (x - 370) * 0.3, 6, n=12))
    bow(sc, 336, 236, s=0.8, flip=True)
    sc.geom(sole)
    sc.lines(clip([par(bottom, 40)], sole))
    return sc
