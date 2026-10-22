"""Musical instruments for the 'music' category (used by gen_songs.py): western and Persian instruments
drawn as clean line drawings (front, side or top views)."""
import math, sys, os
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

def sym(half):
    """Closed outline from the right half (top centre to bottom centre, y down), mirrored."""
    right = spline(half, n=10)
    left = [(-x, y) for x, y in right[::-1]]
    return right + left[1:] + [right[0]]

def frets(y_nut, scale, y_end, n=24):
    ys = []
    for k in range(1, n + 1):
        y = y_nut + scale * (1 - 2 ** (-k / 12))
        if y >= y_end: break
        ys.append(y)
    return ys

def strings(xs0, y0, xs1, y1):
    return [[(a, y0), (b, y1)] for a, b in zip(xs0, xs1)]

def spread(n, w): return [(-w / 2 + w * i / (n - 1)) if n > 1 else 0 for i in range(n)]

def knob(cx, cy, rx, ry, side):
    """A tuning peg seen from the front: a shaft and an oval button on one side."""
    return [[(cx, cy), (cx + side * rx * 0.6, cy)], ellipse(cx + side * (rx * 0.6 + rx), cy, rx, ry, n=20)]

def head_plate(y0, y1, w0, w1):
    return [(-w0, y0), (-w1, y0 - (y0 - y1) * 0.2), (-w1 * 1.02, y1 + 8), (-w1 * 0.7, y1), (w1 * 0.7, y1), (w1 * 1.02, y1 + 8), (w1, y0 - (y0 - y1) * 0.2), (w0, y0), (-w0, y0)]

# ---------------------------------------------------------------- guitars and lutes
def acoustic_guitar():
    sc = Scene()
    body = sym([(0, 0), (95, 4), (140, 40), (150, 95), (128, 165), (118, 205), (140, 262), (185, 340), (192, 410), (165, 470), (95, 503), (0, 508)])
    sc.shape(body)
    sc.shape(rect(-27, -330, 54, 450))                         # fingerboard
    sc.lines([circle(0, 175, 46), circle(0, 175, 53), circle(0, 175, 60)])
    sc.shape(spline([(48, 210), (75, 230), (110, 285), (105, 330), (70, 318), (40, 265), (48, 210)], n=8))   # pickguard
    sc.shape(rect(-72, 378, 144, 24, 8))                      # bridge
    sc.line([(-52, 386), (52, 386)])
    for x in spread(6, 80): sc.shape(circle(x, 395, 3.2, n=10))
    for y in frets(-330, 716, 118): sc.line([(-27, y), (27, y)])
    sc.shape(head_plate(-330, -470, 26, 42))
    for k, y in enumerate((-365, -405, -445)):
        for side in (-1, 1):
            for P in knob(side * 42, y, 14, 8, side): sc.line(P)
            sc.line(circle(side * 22, y, 5, n=10))
    sc.lines(strings(spread(6, 34), -330, spread(6, 50), 386))
    return sc.render()

def ukulele():
    sc = Scene()
    body = sym([(0, 0), (70, 4), (104, 34), (110, 80), (92, 130), (88, 160), (110, 215), (130, 265), (122, 315), (80, 348), (0, 356)])
    sc.shape(body)
    sc.shape(rect(-24, -300, 48, 395))
    sc.lines([circle(0, 150, 38), circle(0, 150, 45)])
    sc.shape(rect(-50, 268, 100, 22, 8))
    sc.line([(-34, 275), (34, 275)])
    for y in frets(-300, 575, 92, 15): sc.line([(-24, y), (24, y)])
    sc.shape(head_plate(-300, -400, 24, 36))
    for y in (-335, -375):
        for side in (-1, 1):
            for P in knob(side * 36, y, 13, 8, side): sc.line(P)
            sc.line(circle(side * 19, y, 5, n=10))
    sc.lines(strings(spread(4, 26), -300, spread(4, 40), 275))
    return sc.render()

def banjo():
    sc = Scene()
    sc.shape(circle(0, 0, 262, n=120))
    sc.line(circle(0, 0, 246, n=110))
    for k in range(24):
        a = TAU * k / 24
        c, s = math.cos(a), math.sin(a)
        sc.line([(246 * c, 246 * s), (262 * c, 262 * s)])
        sc.line(circle(254 * c, 254 * s, 4, n=8))
    sc.line(circle(0, 0, 226, n=110))
    sc.shape(poly([(-14, 236), (14, 236), (40, 120), (-40, 120)]))     # tailpiece
    sc.shape(rect(-46, 96, 92, 14, 4))                               # bridge
    sc.shape(rect(-24, -830, 48, 590))                               # neck over the pot
    for y in frets(-830, 1000, -250, 22): sc.line([(-24, y), (24, y)])
    for y in [-830 + 1000 * (1 - 2 ** (-k / 12)) for k in (3, 5, 7, 10, 12, 15)]:
        sc.line(circle(0, y + 22, 4, n=10))
    fifth_y = -830 + 1000 * (1 - 2 ** (-5 / 12))
    for P in knob(24, fifth_y, 12, 7, 1): sc.line(P)
    sc.shape(head_plate(-830, -960, 24, 40))
    for y in (-870, -920):
        for side in (-1, 1):
            for P in knob(side * 40, y, 13, 8, side): sc.line(P)
            sc.line(circle(side * 21, y, 5, n=10))
    xs_nut = spread(4, 28)
    sc.lines(strings(xs_nut, -830, spread(4, 44), 103))
    sc.line([(24, fifth_y), (22, 103)])
    sc.lines(strings(spread(5, 50), 103, spread(5, 22), 230))
    return sc.render()

def violin_body():
    return sym([(0, 0), (55, 4), (88, 22), (100, 56), (94, 92), (84, 112), (68, 124), (61, 152), (66, 182), (82, 198), (100, 207),
                (117, 238), (120, 282), (104, 326), (64, 350), (0, 357)])

def f_hole(side):
    s = side
    c = [(s * 40, 150), (s * 50, 175), (s * 44, 205), (s * 52, 232), (s * 58, 252)]
    A = spline(c, n=8); B = [(x + s * 3.2, y + 1.5) for x, y in A]
    return [A, B, circle(c[0][0] + s * 1.5, c[0][1] - 3, 5, n=10), circle(c[-1][0] + s * 1.5, c[-1][1] + 3, 5, n=10)]

def violin(with_bow=True):
    sc = Scene()
    body = violin_body()
    sc.shape(body)
    sc.line(lines_of(Polygon(body).buffer(-7, quad_segs=6))[0])
    for s in (-1, 1): sc.lines(f_hole(s))
    sc.shape(ellipse(-52, 318, 42, 26, 0.35, n=36))               # chin rest
    sc.shape(spline([(-17, 248), (17, 248), (14, 300), (8, 338), (-8, 338), (-14, 300), (-17, 248)], n=6))   # tailpiece
    sc.shape(spline([(-36, 214), (-20, 206), (0, 203), (20, 206), (36, 214), (36, 219), (0, 210), (-36, 219), (-36, 214)], n=4))   # bridge
    sc.shape(poly([(-11, -170), (11, -170), (19, 160), (0, 168), (-19, 160)]))   # fingerboard
    sc.shape(poly([(-11, -170), (11, -170), (11, -250), (-11, -250)]))           # pegbox
    for y in (-190, -228):
        for side in (-1, 1):
            for P in knob(side * 11, y + (side * 6), 12, 6, side): sc.line(P)
    sc.shape(circle(0, -268, 22, n=40))                                         # scroll
    sp = [(0 + 18 * (1 - t) * math.cos(TAU * 1.6 * t), -268 + 18 * (1 - t) * math.sin(TAU * 1.6 * t)) for t in np.linspace(0, 0.85, 40)]
    sc.line(sp)
    sc.lines(strings(spread(4, 13), -170, spread(4, 30), 209))
    sc.lines(strings(spread(4, 30), 209, spread(4, 20), 250))
    if with_bow:
        a, b = (235, -300), (185, 600)
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; nx, ny = -uy, ux
        stick = [(a[0] + ux * L * t + nx * 10 * math.sin(math.pi * t), a[1] + uy * L * t + ny * 10 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 30)]
        sc.shape(thick(stick, 7, cap='round'))
        hair = [(a[0] + ux * 25 - nx * 16, a[1] + uy * 25 - ny * 16), (b[0] - ux * 60 - nx * 16, b[1] - uy * 60 - ny * 16)]
        sc.line(hair)
        fx, fy = b[0] - ux * 60, b[1] - uy * 60
        frog = [(fx, fy), (fx - nx * 26, fy - ny * 26), (fx - nx * 26 + ux * 45, fy - ny * 26 + uy * 45), (fx + ux * 50, fy + uy * 50)]
        sc.shape(poly(frog))
        sc.shape(poly([(a[0], a[1]), (a[0] - nx * 18 + ux * 8, a[1] - ny * 18 + uy * 8), (a[0] - nx * 16 + ux * 28, a[1] - ny * 16 + uy * 28), (a[0] + ux * 20, a[1] + uy * 20)]))
    return sc.render()

def tar():
    sc = Scene()
    body = sym([(0, 0), (38, 5), (68, 30), (76, 72), (62, 116), (72, 136), (118, 176), (140, 232), (126, 300), (82, 345), (30, 366), (0, 370)])
    sc.shape(body)
    sc.line(lines_of(Polygon(body).buffer(-8, quad_segs=6))[0])
    sc.shape(poly([(-30, 275), (30, 275), (24, 292), (-24, 292)]))        # bridge on the skin
    sc.shape(rect(-18, -500, 36, 520))                                   # neck
    for y in frets(-500, 790, 5, 26): sc.line([(-18, y), (18, y)])
    sc.shape(poly([(-18, -500), (-26, -520), (-26, -640), (-12, -656), (12, -656), (26, -640), (26, -520), (18, -500)]))
    for y in (-545, -585, -625):
        for side in (-1, 1):
            for P in knob(side * 26, y, 13, 7, side): sc.line(P)
    sc.lines(strings(spread(6, 24), -500, spread(6, 44), 283))
    sc.lines(strings(spread(6, 44), 283, spread(6, 16), 366))
    return sc.render()

def setar():
    sc = Scene()
    body = sym([(0, 0), (28, 10), (52, 48), (64, 108), (58, 168), (38, 212), (0, 230)])
    sc.shape(body)
    for k, (x, y) in enumerate([(0, 60), (-14, 74), (14, 74), (0, 88), (-28, 88), (28, 88), (-14, 102), (14, 102), (0, 116)]):
        sc.line(circle(x, y, 3.2, n=8))
    sc.shape(poly([(-20, 180), (20, 180), (16, 192), (-16, 192)]))
    sc.shape(rect(-13, -560, 26, 575))
    for y in frets(-560, 740, 5, 25): sc.line([(-13, y), (13, y)])
    sc.shape(poly([(-13, -560), (-18, -580), (-18, -680), (-8, -692), (8, -692), (18, -680), (18, -580), (13, -560)]))
    for y, side in ((-605, -1), (-645, -1), (-605, 1), (-645, 1)):
        for P in knob(side * 18, y, 12, 6, side): sc.line(P)
    sc.lines(strings(spread(4, 16), -560, spread(4, 26), 186))
    sc.lines(strings(spread(4, 26), 186, spread(4, 10), 228))
    return sc.render()

def kamancheh():
    sc = Scene()
    sc.shape(circle(0, 0, 122, n=90))
    sc.line(circle(0, 0, 100, n=80))
    sc.shape(poly([(-14, 118), (14, 118), (7, 320), (-7, 320)]))           # spike
    sc.shape(circle(0, 334, 16, n=24))
    sc.shape(poly([(-16, 45), (16, 45), (10, 58), (-10, 58)]))             # bridge
    sc.shape(rect(-15, -560, 30, 450))                                    # neck
    for y in (-150, -160, -420, -430): sc.line([(-15, y), (15, y)])
    sc.shape(poly([(-15, -560), (-22, -575), (-22, -660), (-10, -672), (10, -672), (22, -660), (22, -575), (15, -560)]))
    for y, side in ((-595, -1), (-635, -1), (-595, 1), (-635, 1)):
        for P in knob(side * 22, y, 15, 7, side): sc.line(P)
    sc.shape(spline([(0, -672), (14, -690), (8, -715), (0, -735), (-8, -715), (-14, -690), (0, -672)], n=6))   # finial
    sc.lines(strings(spread(4, 18), -556, spread(4, 26), 50))
    sc.lines(strings(spread(4, 26), 50, spread(4, 10), 120))
    # curved bow on the right
    bow = [(260 + 60 * math.sin(math.pi * t), -420 + 820 * t) for t in np.linspace(0, 1, 40)]
    sc.shape(thick(bow, 7))
    sc.line([(262, -400), (262, 380)])
    sc.shape(rect(254, 360, 26, 46, 6))
    return sc.render()

def santur():
    sc = Scene()
    W0, W1, H = 900, 380, 300                    # long front edge, short back edge, depth (top view)
    tl, tr, br, bl = (-W1 / 2, 0), (W1 / 2, 0), (W0 / 2, H), (-W0 / 2, H)
    sc.shape(poly([tl, tr, br, bl]))
    inner = Polygon([tl, tr, br, bl]).buffer(-16, join_style=2)
    sc.line(lines_of(inner)[0])
    for cx in (-120, 120): sc.lines([circle(cx, 205, 26, n=30), circle(cx, 205, 18, n=24)])
    n = 18
    for i in range(n):
        y = 28 + (H - 56) * i / (n - 1)
        xl = -W1 / 2 - (W0 - W1) / 2 * y / H + 20; xr = -xl
        sc.line([(xl, y), (xr, y)])
        sc.line(circle(xr - 10, y, 3.2, n=8))
        bx = (-40 - 120 * (i % 2)) if i < n else 0
        bx = -60 + 150 * (i / (n - 1)) if i % 2 == 0 else 170 - 140 * (i / (n - 1))
        sc.shape(rect(bx - 6, y - 5, 12, 10, 3))
    for k, ang in enumerate((-0.15, 0.12)):
        x0 = -260 + 160 * k
        stick = [(x0, H + 70), (x0 + 330 * math.cos(ang), H + 70 + 330 * math.sin(ang))]
        sc.shape(thick(stick, 6))
        ex, ey = stick[1]
        sc.shape(ellipse(ex + 6, ey, 14, 8, ang, n=20))
    return sc.render()

def daf():
    sc = Scene()
    sc.shape(circle(0, 0, 470, n=180))
    sc.line(circle(0, 0, 430, n=170))
    n = 30
    for rr, off in ((400, 0), (372, 0.5)):
        for k in range(n):
            a = TAU * (k + off) / n
            sc.shape(circle(rr * math.cos(a), rr * math.sin(a), 17, n=16))
    sc.line(circle(0, 0, 330, n=140))
    return sc.render()

def tombak():
    sc = Scene()
    half = [(0, 0), (150, 0), (152, 22), (140, 90), (104, 168), (60, 226), (42, 262), (44, 318), (66, 372), (82, 398), (78, 412), (0, 412)]
    pts = spline(half, n=10)
    outline = pts + [(-x, y) for x, y in pts[::-1]][1:]
    sc.shape(outline + [outline[0]])
    sc.shape(ellipse(0, 0, 150, 26, n=80))
    sc.line(ellipse(0, 0, 138, 21, n=70))
    G = Polygon(outline)
    for y in (40, 52, 270, 282, 380):
        seg = LineString([(-200, y), (200, y)]).intersection(G)
        for P in lines_of(seg):
            (x0, _), (x1, _) = P[0], P[-1]
            sc.line([(x0 + (x1 - x0) * t, y + 10 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 16)])
    return sc.render()

def ney():
    L = []
    a = math.radians(-58); c, s = math.cos(a), math.sin(a)
    def R(P): return [(x * c - y * s, x * s + y * c) for x, y in P]
    tube = rect(0, -11, 900, 22)
    L.append(R(tube))
    for x in (120, 240, 360, 480, 600, 720): L += [R([(x, -11), (x, 11)]), R([(x + 7, -11), (x + 7, 11)])]
    L.append(R(poly([(900, -11), (950, -9), (950, 9), (900, 11)])))
    L.append(R([(925, -10), (925, 10)]))
    for x in (520, 560, 600, 640, 680): L.append(R(ellipse(x + 25, 0, 7, 5, n=12)))
    return L

# ---------------------------------------------------------------- other instruments
def harp():
    sc = Scene()
    col = [(-160, 960), (-160, 90)]
    sc.shape(rect(-200, 950, 360, 50, 8))                         # base
    for x in (-150, -110, 60, 100): sc.line([(x, 1000), (x, 1012)])
    sb_bot, sb_top = (-120, 945), (330, 175)
    def band(a, b, w0, w1, n=20):
        dx, dy = b[0] - a[0], b[1] - a[1]; Ln = math.hypot(dx, dy); nx, ny = -dy / Ln, dx / Ln
        P = [(a[0] + dx * t + nx * (w0 + (w1 - w0) * t), a[1] + dy * t + ny * (w0 + (w1 - w0) * t)) for t in np.linspace(0, 1, n)]
        Q = [(a[0] + dx * t - nx * (w0 + (w1 - w0) * t) * 0.3, a[1] + dy * t - ny * (w0 + (w1 - w0) * t) * 0.3) for t in np.linspace(1, 0, n)]
        return P + Q + [P[0]]
    sc.shape(band(sb_bot, sb_top, 70, 24))                         # soundbox
    sc.line([sb_bot, sb_top])
    neck_c = [(-160, 90), (-60, 40), (60, 110), (180, 150), (300, 120), (345, 150)]
    neck = spline(neck_c, n=10)
    sc.shape(thick(neck, 36))
    for i in range(1, 28):
        t = i / 28.0
        x = -150 + (sb_top[0] - 25 - (-150)) * t
        Ly = LineString(neck).interpolate(t * LineString(neck).length)
        yt = 130 + 0 * t
        top = [p for p in neck if abs(p[0] - x) < 1e9]
        ny_ = min(neck, key=lambda p: abs(p[0] - x))[1] + 18
        u = (x - sb_bot[0]) / (sb_top[0] - sb_bot[0])
        yb = sb_bot[1] + (sb_top[1] - sb_bot[1]) * u
        if yb - ny_ > 30 and x > -140: sc.line([(x, ny_), (x, yb)])
    sc.shape(rect(-178, 95, 36, 860, 6))                           # column
    sc.shape(spline([(-182, 95), (-200, 60), (-185, 25), (-160, 15), (-135, 25), (-120, 60), (-138, 95)], n=6))   # crown
    sc.line([(-178, 140), (-142, 140)]); sc.line([(-178, 910), (-142, 910)])
    return sc.render()

def grand_piano():
    sc = Scene()
    outline = spline([(0, 900), (0, 60), (40, 4), (140, -6), (240, 40), (305, 170), (365, 330), (470, 520), (560, 650), (600, 760), (600, 900)], n=10)
    case = outline + [(0, 900)]
    sc.shape(case)
    inner = Polygon(case).buffer(-14, join_style=1)
    sc.line(lines_of(inner)[0])
    plate = Polygon(case).buffer(-40, join_style=1).difference(box(-10, 760, 620, 1000))
    sc.line(lines_of(plate)[0])
    for (x, y) in ((90, 200), (200, 330), (300, 470), (420, 600), (120, 520), (260, 660)): sc.line(circle(x, y, 22, n=20))
    G = plate
    for i in range(22):
        x0 = 60 + i * 24
        seg = LineString([(x0, 740), (x0 - 40 - i * 4, 0)]).intersection(G)
        for P in lines_of(seg): sc.line(P)
    sc.shape(rect(100, 770, 400, 46, 6))                          # music desk
    sc.shape(rect(-24, 880, 648, 110, 4))                         # keyboard area
    kx0, kx1, ky0, ky1 = 4, 596, 900, 985
    n = 36; w = (kx1 - kx0) / n
    sc.line([(kx0, ky0), (kx1, ky0)])
    for i in range(1, n): sc.line([(kx0 + i * w, ky0), (kx0 + i * w, ky1)])
    for i in range(n):
        if i % 7 in (0, 1, 3, 4, 5):
            bx = kx0 + (i + 1) * w - w * 0.3
            sc.shape(rect(bx, ky0, w * 0.6, 52))
    return sc.render()

def accordion():
    sc = Scene()
    sc.shape(rect(0, 0, 150, 560, 10))
    sc.shape(rect(470, 0, 160, 560, 10))
    for i in range(16):
        x = 150 + i * 20
        sc.line([(x, 20), (x, 540)])
    top = [(150 + i * 10, 20 if i % 2 == 0 else 0) for i in range(33)]
    bot = [(150 + i * 10, 540 if i % 2 == 0 else 560) for i in range(33)]
    sc.line(top); sc.line(bot)
    sc.shape(rect(18, 30, 100, 500, 4))
    n = 17; h = 500 / n
    for i in range(1, n): sc.line([(18, 30 + i * h), (118, 30 + i * h)])
    for i in range(n):
        if i % 7 in (0, 1, 3, 4, 5) and i < n - 1:
            sc.shape(rect(18, 30 + (i + 1) * h - h * 0.32, 58, h * 0.64))
    for r in range(12):
        for cidx in range(6):
            sc.line(circle(500 + cidx * 20 + (r % 2) * 10, 60 + r * 38, 6, n=10))
    sc.line([(130, 40), (130, 520)]); sc.line([(610, 40), (610, 520)])
    return sc.render()

def xylophone():
    sc = Scene()
    n = 12
    for i in range(n):
        x = i * 52; Lb = 420 - i * 20; y0 = (420 - Lb) / 2
        sc.shape(rect(x, y0, 40, Lb, 8))
        for f in (0.22, 0.78): sc.line(circle(x + 20, y0 + Lb * f, 4, n=10))
    for f in (0.22, 0.78):
        sc.line([(-10, 420 * f), ((n - 1) * 52 + 50, (420 - (420 - (n - 1) * 20)) / 2 + (420 - (n - 1) * 20) * f)])
    for k, (x0, y0, x1, y1) in enumerate(((120, 560, 420, 330), (480, 560, 230, 300))):
        sc.shape(thick([(x0, y0), (x1, y1)], 9))
        sc.shape(circle(x1, y1, 22, n=24))
    return sc.render()

def metronome():
    sc = Scene()
    sc.shape(rect(-170, 520, 340, 40, 6))
    sc.shape(poly([(-150, 520), (150, 520), (50, 0), (-50, 0)]))
    sc.line([(-115, 480), (115, 480), (40, 60), (-40, 60), (-115, 480)])
    for i in range(12):
        y = 100 + i * 28
        sc.line([(-6, y), (6, y)])
    piv = (0, 450); a = math.radians(14)
    top = (piv[0] + math.sin(a) * 520, piv[1] - math.cos(a) * 520)
    sc.line([piv, top])
    wx, wy = piv[0] + math.sin(a) * 260, piv[1] - math.cos(a) * 260
    sc.shape(tx(rot(poly([(-22, -16), (22, -16), (28, 16), (-28, 16)]), a), wx, wy))
    sc.shape(circle(*piv, 12, n=16))
    sc.shape(rect(150, 380, 40, 14, 4)); sc.shape(ellipse(205, 387, 16, 26, n=20))
    return sc.render()

def tuning_fork():
    path = [(-34, 0), (-34, 470), *arc(0, 470, 34, math.pi, 0, n=16)[1:], (34, 0)]
    g = thick(path, 22, cap='flat').union(thick([(0, 500), (0, 760)], 18, cap='flat')).union(Point(0, 772).buffer(17))
    return lines_of(g)

def triangle_inst():
    sc = Scene()
    A, B, C = (0, 0), (300, 520), (-300, 520)
    p0 = (C[0] + (A[0] - C[0]) * 0.1, C[1] + (A[1] - C[1]) * 0.1)
    p1 = (C[0] + (B[0] - C[0]) * 0.04, C[1])
    sc.shape(thick([p0, A, B, p1], 16, cap='round', join='round'))
    sc.line([(0, -8), (-22, -110), (0, -150), (22, -110), (0, -8)])
    sc.shape(thick([(160, 700), (420, 330)], 10))
    sc.shape(thick([(160, 700), (120, 757)], 22))
    return sc.render()

def tambourine():
    sc = Scene()
    rx, ry, d = 300, 105, 70
    side = [(-rx, 0)] + [(rx * math.cos(t), d + ry * math.sin(t)) for t in np.linspace(math.pi, 0, 60)] + [(rx, 0)]
    sc.shape(poly([(rx * math.cos(t), ry * math.sin(t)) for t in np.linspace(0, math.pi, 60)] + side[::-1]))
    for k, t in enumerate(np.linspace(math.pi * 0.85, math.pi * 0.15, 5)):
        x = rx * math.cos(t); y = ry * math.sin(t) + d / 2
        sc.shape(rect(x - 30, y - 20, 60, 40, 6))
        sc.shape(ellipse(x - 12, y, 15, 15, n=20)); sc.shape(ellipse(x + 12, y, 15, 15, n=20))
        sc.line([(x - 28, y), (x + 28, y)])
    sc.shape(ellipse(0, 0, rx, ry, n=100))
    sc.line(ellipse(0, 0, rx - 14, ry - 6, n=100))
    return sc.render()

def snare_drum():
    sc = Scene()
    rx, ry, h = 300, 95, 230
    sc.shape(poly([(-rx, 0)] + [(rx * math.cos(t), h + ry * math.sin(t)) for t in np.linspace(math.pi, 0, 60)] + [(rx, 0)]))
    sc.line([(rx * math.cos(t), h - 14 + ry * math.sin(t)) for t in np.linspace(math.pi, 0, 60)])
    sc.line([(rx * math.cos(t), 16 + ry * math.sin(t)) for t in np.linspace(math.pi, 0, 60)])
    for t in np.linspace(math.pi * 0.92, math.pi * 0.08, 6):
        x = rx * math.cos(t); y0 = 16 + ry * math.sin(t); y1 = h - 14 + ry * math.sin(t)
        sc.shape(rect(x - 7, y0 + 30, 14, y1 - y0 - 60, 5))
        sc.line([(x, y0), (x, y0 + 30)]); sc.line([(x, y1 - 30), (x, y1)])
    sc.shape(ellipse(0, 0, rx, ry, n=100))
    sc.line(ellipse(0, 0, rx - 16, ry - 7, n=100))
    for (x0, y0, x1, y1) in ((-260, -170, 160, 40), (-150, 80, 250, -150)):
        st = thick([(x0, y0), (x1, y1)], 14)
        sc.shape(st); sc.shape(circle(x1, y1, 9, n=12))
    return sc.render()

def harmonica():
    sc = Scene()
    sc.shape(rect(0, 0, 640, 150, 20))
    sc.line([(14, 40), (626, 40)]); sc.line([(14, 110), (626, 110)])
    for i in range(10):
        sc.shape(rect(44 + i * 56, 58, 34, 34, 5))
    for x in (24, 616):
        for y in (20, 130): sc.line(circle(x, y, 6, n=10))
    return sc.render()

def lyre():
    sc = Scene()
    sc.shape(spline([(-170, 560), (170, 560), (190, 640), (100, 700), (-100, 700), (-190, 640), (-170, 560)], n=8))
    for s in (-1, 1):
        arm = spline([(s * 130, 590), (s * 230, 430), (s * 200, 230), (s * 150, 120), (s * 210, 20), (s * 260, -10)], n=10)
        sc.shape(thick(arm, 30))
    sc.shape(rect(-200, 90, 400, 30, 12))
    for i in range(7):
        x = -105 + i * 35
        sc.line([(x, 120), (x, 600)])
        sc.line(circle(x, 105, 6, n=10))
    sc.line(circle(0, 640, 28, n=24))
    return sc.render()

def music_stand():
    sc = Scene()
    sc.shape(poly([(-210, -20), (210, -20), (230, 300), (-230, 300)]))
    sc.shape(rect(-245, 300, 490, 26, 6))
    for x in range(-150, 151, 100): sc.line([(x, 20), (x, 260)])
    sc.shape(rect(-9, 326, 18, 470))
    sc.shape(rect(-16, 560, 32, 40, 6))
    for (x1, y1) in ((-260, 1000), (260, 1000), (0, 970)):
        sc.shape(thick([(0, 790), (x1, y1)], 14))
    return sc.render()

def items():
    out = []
    def add(name, L, slug):
        it = Item('music', name, [P for P in L if len(P) > 1]); it.slug = slug; out.append(it)
    add('Violin and bow', violin(True), 'violin-and-bow')
    add('Acoustic guitar', acoustic_guitar(), 'acoustic-guitar')
    add('Ukulele', ukulele(), 'ukulele')
    add('Banjo', banjo(), 'banjo')
    add('Harp', harp(), 'harp')
    add('Grand piano from above', grand_piano(), 'grand-piano-top')
    add('Accordion', accordion(), 'accordion')
    add('Xylophone and mallets', xylophone(), 'xylophone')
    add('Metronome', metronome(), 'metronome')
    add('Tuning fork', tuning_fork(), 'tuning-fork')
    add('Triangle and beater', triangle_inst(), 'triangle')
    add('Tambourine', tambourine(), 'tambourine')
    add('Snare drum and sticks', snare_drum(), 'snare-drum')
    add('Harmonica', harmonica(), 'harmonica')
    add('Lyre', lyre(), 'lyre')
    add('Music stand', music_stand(), 'music-stand')
    add('Tar (Persian lute)', tar(), 'tar')
    add('Setar (Persian lute)', setar(), 'setar')
    add('Kamancheh and bow', kamancheh(), 'kamancheh')
    add('Santur and mezrabs', santur(), 'santur')
    add('Daf (frame drum)', daf(), 'daf')
    add('Tombak (goblet drum)', tombak(), 'tombak')
    add('Ney (reed flute)', ney(), 'ney')
    return out

if __name__ == '__main__':
    its = items()
    for it in its: print(it.name, export_size(it.lines))
    sheet(its, sys.argv[1], cols=6, cell=2.6)
