"""Sci-fi: original spacecraft, saucers, stations, robots, aliens, astronauts and other science-fiction
scenes (no franchise designs, no weapons). Drawn y-up, flipped at the end.
Usage: python3 -I gen_scifi.py <out.json> [sheet.png]"""
import math, sys, random, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity

def flipL(L): return [[(x, -y) for x, y in P] for P in L]
def ell(cx, cy, rx, ry, rot=0.0, n=48): return Polygon(ellipse(cx, cy, rx, ry, rot, n))
def disc(cx, cy, r, n=36): return Polygon(circle(cx, cy, r, n))
def band(P, w, cap='round'): return thick(P, w, cap=cap)
def rr(x0, y0, x1, y1, r=0): return Polygon(rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0), r))
def sym_poly(half):
    """Closed polygon from a right half given top to bottom (x >= 0)."""
    return Polygon(half + [(-x, y) for x, y in half[::-1]]).buffer(0)
def clipL(L, g):
    out = []
    for P in L: out += lines_of(LineString(P).intersection(g))
    return out
def place(sc, dx=0, dy=0, s=1.0, rot=0.0, mirror=False):
    out = Scene()
    for kind, g, fill, outline in sc.items:
        h = affinity.scale(g, -1, 1, origin=(0, 0)) if mirror else g
        if rot: h = affinity.rotate(h, rot, origin=(0, 0))
        if s != 1: h = affinity.scale(h, s, s, origin=(0, 0))
        out.items.append((kind, affinity.translate(h, dx, dy), fill, outline))
    return out
def join(*scs):
    out = Scene()
    for s in scs: out.items += s.items
    return out
def stars_bg(sc, n, x0, y0, x1, y1, seed=1, avoid=None):
    r = rng(seed)
    for k in range(n):
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        if avoid is not None and avoid.buffer(20).contains(Point(x, y)): continue
        s = r.uniform(5, 11)
        sc.line([(x - s, y), (x + s, y)]); sc.line([(x, y - s), (x, y + s)])
def ytext(s, x, y, size, font='HersheySansMed'): return [[(px, -py) for px, py in P] for P in text(s, x, -y, size, font)]

# ---------------------------------------------------------------- rockets
def retro_rocket(h=600, w=110, fins=3, windows=3, stripes=True):
    sc = Scene()
    for s in (-1, 1):
        sc.shape(Polygon(spline([(s * w * 0.8, h * 0.28), (s * w * 1.9, h * 0.05), (s * w * 2.0, -h * 0.05), (s * w * 0.95, h * 0.08)], n=6) + [(s * w * 0.8, h * 0.28)]).buffer(0))
    body = sym_poly(spline([(0, h), (w * 0.5, h * 0.84), (w * 0.95, h * 0.55), (w, h * 0.3), (w * 0.82, h * 0.05)], n=10) + [(w * 0.55, 0)])
    sc.shape(body)
    if fins == 3: sc.shape(Polygon([(-8, h * 0.25), (8, h * 0.25), (6, -h * 0.08), (-6, -h * 0.08)]))
    sc.shape(sym_poly([(w * 0.55, 0), (w * 0.62, -h * 0.04), (w * 0.4, -h * 0.07)]))
    for k in range(windows):
        y = h * (0.62 - k * 0.14)
        sc.shape(disc(0, y, w * 0.28)); sc.line(circle(0, y, w * 0.19, 24))
    if stripes:
        for f in (0.78, 0.2):
            yy = h * f; ww = [p for p in spline([(0, h), (w * 0.5, h * 0.84), (w * 0.95, h * 0.55), (w, h * 0.3), (w * 0.82, h * 0.05)], n=10)]
            sc.lines(clipL([[(-w * 1.2, yy), (w * 1.2, yy)]], body.buffer(-2)))
    return sc

def smoke(sc, cx, y, w, seed=2, rows=2):
    r = rng(seed)
    for row in range(rows):
        n = 5 + row
        for k in range(n):
            x = cx - w / 2 + w * (k + 0.5) / n + r.uniform(-15, 15)
            sc.shape(disc(x, y - row * 60 + r.uniform(-10, 10), r.uniform(50, 80) * (1 - row * 0.15), 30))

def rocket_on_pad():
    sc = Scene()
    sc.shape(rr(-360, -40, 360, 0))
    tower = rr(-330, 0, -250, 760)
    sc.shape(tower)
    for y in range(40, 760, 80): sc.lines(clipL([[(-330, y), (-250, y + 80)], [(-250, y), (-330, y + 80)]], tower.buffer(-6)))
    for y in (300, 560): sc.shape(rr(-250, y, -120, y + 20))
    sc.items += place(retro_rocket(620, 100), 0, 60).items
    sc.shape(rr(-150, 0, 150, 30))
    return sc

def rocket_liftoff():
    sc = Scene()
    smoke(sc, 0, 60, 640, rows=2)
    sc.items += place(retro_rocket(560, 95, stripes=False), 0, 200).items
    for s in (-1, 0, 1): sc.shape(Polygon(spline([(s * 30 - 30, 190), (s * 40, 60), (s * 30 + 30, 190)], n=6) + [(s * 30 - 30, 190)]).buffer(0))
    sc.line([(-500, -60), (500, -60)])
    return sc

# ---------------------------------------------------------------- saucers
def saucer(R=360, dome=0.42, lights=10, legs=False, beam=False):
    sc = Scene()
    if beam:
        sc.shape(Polygon([(-R * 0.25, -40), (R * 0.25, -40), (R * 0.75, -650), (-R * 0.75, -650)]))
        for k in range(1, 5): sc.lines(clipL([[(-R, -40 - k * 130), (R, -40 - k * 130)]], Polygon([(-R * 0.25, -40), (R * 0.25, -40), (R * 0.75, -650), (-R * 0.75, -650)]).buffer(-8)))
    if legs:
        for s in (-1, 1):
            sc.shape(band([(s * R * 0.45, -10), (s * R * 0.75, -170)], 20)); sc.shape(ell(s * R * 0.78, -175, 60, 14))
    sc.shape(ell(0, -18, R * 0.4, 46))
    disc_ = sym_poly([(R * 0.55, 60), (R, 10), (R * 0.98, -6), (R * 0.6, -36)])
    sc.shape(disc_)
    sc.line(spline([(-R * 0.98, 4), (0, -12), (R * 0.98, 4)], n=10))
    for k in range(lights):
        t = (k + 0.5) / lights; x = -R * 0.85 + R * 1.7 * t
        y = -14 + 10 * (1 - (x / R) ** 2)
        sc.shape(disc(x, y, 13, 14))
    dm = sym_poly(spline([(0, 60 + R * dome), (R * 0.28, 50 + R * dome * 0.8), (R * 0.42, 60)], n=10) + [(R * 0.42, 56)])
    sc.shape(dm)
    sc.line(spline([(-R * 0.25, 60 + R * dome * 0.55), (-R * 0.1, 60 + R * dome * 0.85), (R * 0.05, 60 + R * dome * 0.93)], n=6))
    return sc

def cow(x, y, s=1.0):
    sc = Scene()
    body = rr(-90, 0, 90, 70, 26)
    sc.shape(Polygon([(80, 40), (130, 60), (150, 40), (140, 10), (100, 10)]))
    for lx in (-70, -40, 50, 75): sc.shape(rr(lx - 8, -60, lx + 8, 10, 4))
    sc.shape(body)
    sc.shape(ell(-30, 40, 30, 18)); sc.shape(ell(30, 20, 22, 14))
    sc.line([(-90, 50), (-130, 10)])
    sc.shape(ell(135, 50, 30, 22)); sc.line([(150, 70), (170, 90)]); sc.line([(130, 70), (120, 92)])
    return place(sc, x, y, s)

def saucer_cow():
    sc = saucer(360, beam=True)
    sc.items += cow(0, -560, 1.2).items
    sc.line([(-500, -660), (500, -660)])
    for x in (-400, -300, 320, 420): sc.line([(x, -660), (x + 6, -620)])
    return sc

def mothership():
    sc = Scene()
    big = saucer(520, 0.25, 18)
    sc.items += big.items
    for (x, y, s) in ((-520, 300, 0.22), (420, 330, 0.18), (520, -260, 0.2), (-380, -300, 0.16)):
        sc.items += place(saucer(360, 0.45, 6), x, y, s).items
    return sc

# ---------------------------------------------------------------- stations and ships
def ring_station():
    sc = Scene(); R = 420
    ring = disc(0, 0, R, 120).difference(disc(0, 0, R - 70, 120))
    for k in range(6):
        a = TAU * k / 6
        sc.shape(band([(70 * math.cos(a), 70 * math.sin(a)), ((R - 60) * math.cos(a), (R - 60) * math.sin(a))], 26))
    sc.shape(ring)
    for k in range(24):
        a = TAU * k / 24; sc.line([((R - 70) * math.cos(a), (R - 70) * math.sin(a)), (R * math.cos(a), R * math.sin(a))])
    sc.shape(disc(0, 0, 80, 40)); sc.line(circle(0, 0, 50, 30))
    sc.shape(band([(0, 80), (0, 160)], 30)); sc.shape(rr(-40, 160, 40, 190, 8))
    sc.items += place(shuttle_small(), 330, 520, 0.3, -30).items
    return sc

def shuttle_small():
    sc = Scene()
    sc.shape(Polygon([(-200, -40), (-60, -40), (200, -10), (240, 10), (200, 30), (-60, 40), (-200, 40)]))
    sc.shape(Polygon([(-200, -40), (-260, -120), (-120, -40)])); sc.shape(Polygon([(-200, 40), (-260, 120), (-120, 40)]))
    sc.line([(140, -6), (180, 10), (140, 24)])
    return sc

def modular_station():
    sc = Scene()
    for s in (-1, 1):
        for k in (1, 2):
            p = rr(s * (120 + (k - 1) * 260), -70, s * (360 + (k - 1) * 260), 70)
            sc.shape(p)
            for x in np.linspace(s * (120 + (k - 1) * 260), s * (360 + (k - 1) * 260), 7)[1:-1]: sc.line([(x, -70), (x, 70)])
            sc.line([(s * (120 + (k - 1) * 260), 0), (s * (360 + (k - 1) * 260), 0)])
    sc.shape(band([(-600, 0), (600, 0)], 26))
    for (x0, x1, h) in ((-110, 110, 90), (-60, 60, 60)):
        sc.shape(rr(x0, -h, x1, h, 30))
    sc.shape(rr(-50, 90, 50, 330, 30)); sc.shape(rr(-45, -90, 45, -300, 30))
    for y in (150, 240): sc.line([(-50, y), (50, y)])
    sc.shape(disc(0, 330, 40, 24)); sc.shape(rr(-150, 360, 150, 420, 6))
    for x in range(-130, 140, 40): sc.line([(x, 360), (x, 420)])
    return sc

def ship_side(kind):
    sc = Scene()
    if kind == 'sleek':
        sc.shape(Polygon([(-420, 30), (-460, 140), (-400, 140), (-300, 50)]))
        body = Polygon(spline([(520, 0), (300, 50), (-100, 80), (-420, 70), (-440, -20), (-100, -60), (300, -40)], closed=True, n=10, tension=0.35)).buffer(0)
        sc.shape(body)
        sc.shape(Polygon(spline([(250, 40), (180, 80), (60, 82), (40, 60)], n=8) + [(250, 40)]).buffer(0))
        for y in (-30, 20): sc.shape(rr(-500, y - 22, -430, y + 22, 10))
        sc.line(spline([(400, -10), (0, -30), (-400, -20)], n=8))
        sc.shape(Polygon([(-150, -50), (-350, -150), (-300, -150), (-60, -55)]))
    elif kind == 'heavy':
        sc.shape(rr(-500, -90, 300, 90, 10))
        sc.shape(Polygon([(300, 90), (520, 30), (520, -40), (300, -90)]))
        sc.shape(rr(-300, 90, 100, 170, 8)); sc.shape(rr(-200, 170, 0, 230, 8)); sc.lines([[(-180, 200), (-20, 200)]])
        for y in (-55, 0, 55): sc.shape(rr(-600, y - 30, -500, y + 30, 8)); sc.line(circle(-600, y, 22, 16))
        for x in range(-450, 300, 75): sc.line([(x, -90), (x, 90)])
        for x in range(-260, 100, 40): sc.line(rect(x, 120, 20, 20, 4))
    elif kind == 'hauler':
        sc.shape(rr(380, -60, 560, 80, 30)); sc.shape(Polygon(spline([(560, 60), (520, 120), (440, 120), (430, 80)], n=6) + [(560, 60)]).buffer(0))
        sc.shape(band([(-480, 0), (400, 0)], 30))
        for k in range(4):
            x = -420 + k * 200; sc.shape(rr(x, -110, x + 180, 110, 6))
            sc.lines([[(x + 10, y), (x + 170, y)] for y in (-60, 0, 60)])
        sc.shape(rr(-560, -80, -480, 80, 20))
        for y in (-40, 40): sc.line(circle(-570, y, 26, 18))
    elif kind == 'explorer':
        sc.shape(ell(0, 0, 520, 60))
        ring = ell(-120, 0, 70, 260).difference(ell(-120, 0, 40, 220))
        sc.shape(ring)
        sc.shape(Polygon(spline([(520, 0), (420, 50), (320, 60)], n=6) + [(320, -60), (420, -50)]).buffer(0))
        sc.lines(clipL([[(x, -70), (x, 70)] for x in range(-400, 400, 80)], ell(0, 0, 515, 56)))
        for y in (-30, 30): sc.shape(rr(-600, y - 20, -510, y + 20, 8))
    return sc

def starfighter_top():
    sc = Scene()
    for s in (-1, 1):
        sc.shape(Polygon([(s * 40, -100), (s * 360, -260), (s * 380, -220), (s * 120, 40)]))
        sc.shape(Polygon([(s * 330, -240), (s * 360, -320), (s * 390, -320), (s * 380, -220)]))
        sc.shape(rr(s * 60 - 30, -360, s * 60 + 30, -220, 10))
    body = sym_poly([(0, 460), (40, 300), (70, 0), (80, -300), (60, -360)])
    sc.shape(body)
    sc.shape(ell(0, 220, 34, 90)); sc.line([(0, 140), (0, 300)])
    sc.lines(clipL([[(-80, y), (80, y)] for y in (-100, -200)], body))
    return sc

def spaceplane():
    sc = Scene()
    sc.line([(-600, -110), (600, -110)])
    for x in range(-560, 600, 140): sc.line([(x, -110), (x + 60, -110)]) if False else None
    sc.shape(Polygon([(-300, 40), (-360, 200), (-300, 200), (-180, 50)]))
    body = Polygon(spline([(480, 0), (320, 50), (-200, 60), (-380, 50), (-390, -30), (-200, -50), (300, -40)], closed=True, n=10, tension=0.35)).buffer(0)
    sc.shape(Polygon([(200, -20), (-320, -60), (-330, -40), (-100, 10)]))
    sc.shape(body)
    sc.shape(Polygon(spline([(360, 26), (300, 60), (200, 62), (190, 40)], n=8) + [(360, 26)]).buffer(0))
    for x in (300, -200): sc.shape(band([(x, -40), (x, -90)], 10)); sc.shape(disc(x, -92, 18, 14))
    for y in (-10, 30): sc.shape(rr(-440, y - 18, -385, y + 18, 8))
    return sc

def lunar_lander():
    sc = Scene()
    for s in (-1, 1):
        sc.shape(band([(s * 150, 80), (s * 330, -160)], 18)); sc.shape(band([(s * 120, 20), (s * 300, -150)], 10))
        sc.shape(ell(s * 335, -170, 60, 14))
    sc.shape(Polygon([(-200, 0), (200, 0), (230, 40), (230, 160), (200, 200), (-200, 200), (-230, 160), (-230, 40)]))
    for x in (-150, -50, 50, 150): sc.line([(x, 10), (x, 190)])
    sc.shape(Polygon([(-60, 0), (60, 0), (90, -80), (-90, -80)]))
    sc.shape(Polygon([(-170, 200), (170, 200), (190, 300), (120, 400), (-120, 400), (-190, 300)]))
    sc.shape(Polygon([(-60, 280), (0, 340), (60, 280), (0, 250)])); sc.line(circle(0, 300, 18, 12))
    sc.shape(band([(120, 400), (160, 470)], 8)); sc.shape(ell(170, 490, 40, 14))
    sc.shape(rr(-150, 300, -100, 340, 6))
    sc.line(spline([(-600, -170), (-300, -190), (0, -175), (300, -190), (600, -170)], n=10))
    return sc

def moon_base():
    sc = Scene()
    ground = Polygon(spline([(-700, 0), (-400, 30), (-100, 10), (200, 40), (500, 20), (700, 30)], n=10) + [(700, -200), (-700, -200)]).buffer(0)
    for (x, r) in ((-350, 200), (60, 150), (360, 110)):
        d = ell(x, 10, r, r * 0.8).intersection(box(-800, 10, 800, 900))
        sc.shape(d)
        sc.lines(clipL([[(x - r, 10 + k), (x + r, 10 + k)] for k in (r * 0.3, r * 0.55)] + [[(x + k * r * 0.3, 10), (x + k * r * 0.15, 10 + r * 0.78)] for k in (-2, -1, 0, 1, 2)], d.buffer(-4)))
    sc.shape(band([(-150, 30), (-90, 30)], 30)); sc.shape(band([(210, 30), (250, 30)], 26))
    sc.shape(band([(560, 20), (560, 300)], 10)); sc.shape(Polygon([(560, 300), (640, 340), (600, 260)])); sc.shape(ell(560, 300, 70, 24, 0.5))
    sc.shape(ground)
    for (x, y, r) in ((-500, -80, 40), (200, -120, 30), (450, -70, 24)): sc.line(ellipse(x, y, r, r * 0.35, 0, 20))
    sc.line(circle(-450, 520, 120, 60)); sc.lines(clipL([spline([(-520, 600), (-450, 560), (-380, 560)], n=6)], disc(-450, 520, 118)))
    stars_bg(sc, 14, -700, 250, 700, 650, seed=3, avoid=disc(-450, 520, 125))
    return sc

def mars_rover():
    sc = Scene()
    for x in (-260, 0, 260):
        sc.shape(disc(x, 90, 90, 40)); sc.line(circle(x, 90, 40, 24))
        for k in range(10): a = TAU * k / 10; sc.line([(x + 60 * math.cos(a), 90 + 60 * math.sin(a)), (x + 88 * math.cos(a), 90 + 88 * math.sin(a))])
    sc.shape(band([(-260, 90), (-130, 230), (0, 90)], 16)); sc.shape(band([(-130, 230), (260, 90)], 16))
    sc.shape(rr(-320, 230, 320, 330, 10)); sc.shape(rr(-360, 330, 360, 350, 4))
    for x in range(-300, 320, 60): sc.line([(x, 240), (x, 320)])
    sc.shape(band([(220, 350), (220, 560)], 16)); sc.shape(rr(170, 560, 290, 620, 10)); sc.line(circle(205, 590, 16, 12)); sc.line(circle(255, 590, 16, 12))
    sc.shape(band([(-220, 350), (-260, 460)], 8)); sc.shape(ell(-270, 470, 60, 16, 0.4))
    sc.shape(band([(320, 260), (440, 200), (470, 120)], 12))
    sc.line([(-500, 0), (600, 0)])
    return sc

def astronaut(pose='float'):
    sc = Scene()
    pack = rr(-140, 60, 140, 380, 30)
    sc.shape(pack)
    arms = {'float': [(-140, 300, -300, 380, -330, 250), (140, 300, 300, 230, 380, 330)], 'flag': [(-140, 300, -260, 200, -200, 90), (140, 300, 270, 380, 330, 480)]}[pose]
    for (x0, y0, x1, y1, x2, y2) in arms:
        sc.shape(band([(x0, y0), (x1, y1)], 90)); sc.shape(band([(x1, y1), (x2, y2)], 80)); sc.shape(disc(x2, y2, 50, 24))
    legs = {'float': [(-60, 20, -150, -200, -120, -380), (60, 20, 180, -170, 260, -330)], 'flag': [(-60, 20, -90, -200, -100, -400), (60, 20, 110, -190, 140, -400)]}[pose]
    for (x0, y0, x1, y1, x2, y2) in legs:
        sc.shape(band([(x0, y0), (x1, y1)], 100)); sc.shape(band([(x1, y1), (x2, y2)], 92)); sc.shape(rr(x2 - 70, y2 - 50, x2 + 70, y2 + 20, 20))
        sc.line([(x1 - 50, y1), (x1 + 50, y1)])
    torso = rr(-130, 0, 130, 360, 50); sc.shape(torso)
    sc.shape(rr(-70, 120, 70, 250, 14)); sc.lines([[(-50, 160), (50, 160)], [(-50, 200), (50, 200)]]); sc.line(circle(30, 140, 10, 10))
    sc.shape(rr(-130, 0, 130, 40, 10))
    sc.shape(disc(0, 470, 130, 50)); sc.shape(ell(0, 470, 95, 75, 0, 40))
    sc.line(spline([(-60, 500), (-30, 530), (10, 535)], n=6))
    if pose == 'float':
        sc.line(spline([(140, 180), (400, 120), (520, -100), (700, -200)], n=14))
    else:
        sc.shape(band([(330, 480), (330, -420)], 14)); sc.shape(rr(340, 200, 640, 400, 4))
        sc.line([(-600, -420), (700, -420)])
    return sc

def space_helmet():
    sc = Scene()
    sc.shape(rr(-320, -260, 320, -120, 40)); sc.lines([[(-300, -190), (300, -190)]])
    h = disc(0, 120, 320, 90); sc.shape(h)
    v = ell(0, 140, 230, 180, 0, 60); sc.shape(v)
    sc.line(spline([(-150, 220), (-90, 280), (0, 300)], n=8)); sc.line(spline([(-120, 160), (-80, 200)], n=4))
    for s in (-1, 1): sc.shape(rr(s * 330 - 30, 60, s * 330 + 30, 180, 14))
    sc.shape(rr(-80, 390, 80, 430, 10))
    return sc

# ---------------------------------------------------------------- robots
def robot_boxy():
    sc = Scene()
    for s in (-1, 1):
        sc.shape(band([(s * 170, 280), (s * 280, 120), (s * 290, -20)], 50)); sc.shape(Polygon([(s * 290 - 40, -20), (s * 290 + 40, -20), (s * 290 + 60, -90), (s * 290 + 20, -60), (s * 290 - 20, -60), (s * 290 - 60, -90)]))
        sc.shape(rr(s * 70 - 45, -320, s * 70 + 45, -40)); sc.shape(rr(s * 70 - 80, -380, s * 70 + 80, -320, 14))
    body = rr(-180, -60, 180, 320, 20); sc.shape(body)
    sc.shape(rr(-120, 20, 120, 220, 10))
    for k, x in enumerate((-70, 0, 70)): sc.line(circle(x, 170, 26, 20)); sc.line([(x, 170), (x + 18 * math.cos(k * 2), 170 + 18 * math.sin(k * 2))])
    for x in (-80, -40, 0, 40, 80): sc.line(rect(x - 12, 50, 24, 60, 4))
    sc.shape(rr(-40, 320, 40, 350))
    head = rr(-140, 350, 140, 560, 24); sc.shape(head)
    for s in (-1, 1): sc.shape(disc(s * 60, 470, 36, 24)); sc.line(circle(s * 60, 470, 16, 14))
    sc.shape(rr(-70, 380, 70, 410, 6)); sc.lines([[(x, 380), (x, 410)] for x in (-35, 0, 35)])
    sc.shape(band([(0, 560), (0, 650)], 8)); sc.shape(disc(0, 660, 20, 16))
    for s in (-1, 1): sc.shape(rr(s * 140, 430, s * 170, 500, 6))
    return sc

def android():
    sc = Scene()
    for s in (-1, 1):
        sc.shape(band([(s * 120, 330), (s * 180, 140), (s * 190, -30)], 46)); sc.shape(ell(s * 192, -60, 30, 44))
        sc.shape(band([(s * 60, -20), (s * 70, -280), (s * 75, -520)], 60)); sc.shape(ell(s * 85, -540, 60, 24))
        sc.line([(s * 70 - 28, -280), (s * 70 + 28, -280)]); sc.line([(s * 180 - 22, 140), (s * 180 + 22, 140)])
    torso = Polygon(spline([(0, 360), (150, 340), (130, 120), (90, -40), (0, -60), (-90, -40), (-130, 120), (-150, 340)], closed=True, n=8, tension=0.4)).buffer(0)
    sc.shape(torso)
    sc.line(spline([(-120, 260), (0, 220), (120, 260)], n=8)); sc.line([(0, 220), (0, -40)]); sc.line(circle(0, 250, 22, 16))
    sc.shape(band([(0, 360), (0, 420)], 40))
    head = ell(0, 520, 100, 130, 0, 50); sc.shape(head)
    sc.shape(Polygon(spline([(-80, 540), (0, 560), (80, 540), (70, 500), (-70, 500)], closed=True, n=6, tension=0.4)).buffer(0))
    sc.line(spline([(-30, 440), (0, 432), (30, 440)], n=6)); sc.line([(-100, 520), (-120, 520)]); sc.line([(100, 520), (120, 520)])
    return sc

def helper_robot():
    sc = Scene()
    sc.shape(rr(-170, -80, 170, 20, 40))
    for x in (-110, 0, 110): sc.shape(disc(x, -30, 40, 24)); sc.line(circle(x, -30, 14, 10))
    body = Polygon(spline([(0, 380), (180, 330), (200, 100), (150, 20), (0, 10), (-150, 20), (-200, 100), (-180, 330)], closed=True, n=8, tension=0.45)).buffer(0)
    sc.shape(body)
    sc.shape(rr(-90, 120, 90, 230, 30)); sc.lines([[(-60, 160), (60, 160)], [(-60, 190), (20, 190)]])
    for s in (-1, 1):
        sc.shape(band([(s * 190, 260), (s * 300, 330), (s * 330, 440)], 24)); sc.shape(Polygon([(s * 330 - 30, 440), (s * 330 + 30, 440), (s * 360, 500), (s * 330, 470), (s * 300, 500)]))
    head = ell(0, 470, 150, 110, 0, 50); sc.shape(head)
    vis = ell(0, 470, 110, 66, 0, 40); sc.shape(vis)
    for s in (-1, 1): sc.line(spline([(s * 60 - 22, 470), (s * 60, 495), (s * 60 + 22, 470)], n=6))
    sc.line(spline([(-30, 440), (0, 428), (30, 440)], n=6))
    sc.shape(band([(0, 580), (0, 640)], 8)); sc.shape(disc(0, 650, 16, 12))
    return sc

def spider_robot():
    sc = Scene()
    for k, (a, L) in enumerate(((150, 1.0), (115, 1.1), (70, 1.1), (35, 1.0))):
        for s in (-1, 1):
            aa = math.radians(a)
            k1 = (s * 220 * math.cos(aa) * L * 0.0 + s * 160, 60)
            knee = (s * (200 + 240 * L * abs(math.cos(aa)) + 60), 260 - k * 10)
            foot = (s * (280 + 330 * L * abs(math.cos(aa)) + 30 * k), -120)
            base = (s * 120, 40 + (k - 1.5) * 30)
            sc.shape(band([base, knee], 26)); sc.shape(band([knee, foot], 18)); sc.shape(disc(*knee, 22, 16))
    body = ell(0, 60, 230, 130, 0, 60); sc.shape(body)
    sc.lines(clipL([spline([(-230, 60), (0, 20), (230, 60)], n=10)], body.buffer(-3)))
    head = ell(0, 160, 130, 70, 0, 40); sc.shape(head)
    for x in (-60, -20, 20, 60): sc.shape(disc(x, 175, 14, 12))
    return sc

def robot_dog():
    sc = Scene()
    for (x0, x1) in ((-260, -230), (200, 230)):
        for dz, w in ((0, 1.0),):
            sc.shape(band([(x0, 60), (x0 - 30, -120), (x0 + 10, -300)], 46)); sc.shape(rr(x0 - 30, -330, x0 + 60, -300, 12)); sc.shape(disc(x0 - 30, -120, 30, 16))
    sc.shape(band([(-240, 50), (-210, -110), (-250, -300)], 40)); sc.shape(band([(220, 50), (250, -110), (210, -300)], 40))
    body = rr(-330, 0, 330, 160, 60); sc.shape(body)
    sc.lines([[(-100, 10), (-100, 150)], [(100, 10), (100, 150)]])
    sc.shape(band([(300, 140), (380, 260)], 50))
    head = Polygon([(340, 220), (520, 230), (560, 180), (540, 140), (360, 150)]); sc.shape(head)
    sc.shape(Polygon([(360, 230), (390, 320), (420, 230)])); sc.shape(disc(470, 200, 16, 12))
    sc.shape(band([(-330, 120), (-420, 230)], 18))
    sc.line([(-600, -330), (650, -330)])
    return sc

def mech_walker():
    sc = Scene()
    for s in (-1, 1):
        hip = (s * 140, 300); knee = (s * 260, 80); ankle = (s * 180, -180)
        sc.shape(band([hip, knee], 80)); sc.shape(band([knee, ankle], 70)); sc.shape(disc(*knee, 56, 24))
        sc.shape(Polygon([(ankle[0] - 120, -220), (ankle[0] + 140, -220), (ankle[0] + 100, -170), (ankle[0] - 80, -170)]))
    sc.shape(rr(-220, 260, 220, 360, 20))
    cock = Polygon(spline([(-260, 360), (-280, 520), (-120, 620), (160, 620), (300, 520), (280, 360)], n=8) + [(-260, 360)]).buffer(0); sc.shape(cock)
    sc.shape(Polygon(spline([(60, 560), (240, 520), (250, 440), (60, 430)], closed=True, n=6, tension=0.3)).buffer(0))
    sc.lines([[(-200, 420), (-40, 420)], [(-200, 470), (-40, 470)]])
    sc.shape(band([(-120, 620), (-140, 720)], 10)); sc.shape(disc(-140, 730, 16, 12))
    sc.line([(-600, -220), (600, -220)])
    return sc

# ---------------------------------------------------------------- aliens and space
def cute_alien():
    sc = Scene()
    for s in (-1, 1):
        sc.shape(band([(s * 50, 380), (s * 120, 560)], 14)); sc.shape(disc(s * 125, 575, 30, 20))
        sc.shape(band([(s * 110, 120), (s * 230, 200)], 40)); sc.shape(disc(s * 240, 205, 34, 20))
        sc.shape(band([(s * 60, -10), (s * 80, -150)], 50)); sc.shape(ell(s * 95, -165, 60, 26))
    body = Polygon(spline([(0, 220), (130, 180), (140, 40), (100, -30), (0, -40), (-100, -30), (-140, 40), (-130, 180)], closed=True, n=8, tension=0.45)).buffer(0); sc.shape(body)
    sc.line(circle(0, 80, 20, 14))
    head = ell(0, 330, 200, 150, 0, 60); sc.shape(head)
    for s in (-1, 1):
        sc.shape(ell(s * 80, 350, 56, 70, 0, 30)); sc.shape(ell(s * 80 + 12, 330, 26, 34, 0, 20)); sc.line(circle(s * 80 + 20, 360, 10, 10))
    sc.line(spline([(-50, 250), (0, 225), (50, 250)], n=8))
    return sc

def tentacle_alien():
    sc = Scene()
    for k in range(6):
        a = -150 + k * 60
        P = spline([(a * 0.5, 0), (a * 0.9, -150), (a * 1.3 + 30 * math.sin(k), -300), (a * 1.1 + 60 * math.cos(k), -430)], n=12)
        sc.shape(LineString(P).buffer(34, cap_style=1))
        for t in (0.35, 0.6, 0.8):
            p = P[int(t * (len(P) - 1))]; sc.line(circle(p[0], p[1], 8, 8))
    head = Polygon(spline([(0, 520), (220, 450), (260, 200), (180, 40), (0, 0), (-180, 40), (-260, 200), (-220, 450)], closed=True, n=8, tension=0.45)).buffer(0); sc.shape(head)
    e = disc(0, 260, 90, 40); sc.shape(e); sc.shape(disc(10, 250, 40, 20)); sc.line(circle(30, 280, 12, 10))
    for (x, y) in ((-150, 380), (150, 360), (-60, 450), (100, 460)): sc.line(circle(x, y, 18, 12))
    return sc

def grey_alien_head():
    sc = Scene()
    sc.shape(band([(0, -350), (0, -150)], 120))
    head = Polygon(spline([(0, 420), (250, 360), (300, 160), (200, -80), (0, -200), (-200, -80), (-300, 160), (-250, 360)], closed=True, n=10, tension=0.45)).buffer(0); sc.shape(head)
    for s in (-1, 1):
        eye = Polygon(spline([(s * 30, 120), (s * 150, 210), (s * 230, 140), (s * 170, 40), (s * 60, 40)], closed=True, n=8, tension=0.45)).buffer(0)
        sc.shape(eye)
        sc.lines(clipL([[(s * 20, 100 + k), (s * 240, 160 + k)] for k in (-40, -10, 20)], eye.buffer(-8)))
    sc.line([(-14, -40), (-6, -36)]); sc.line([(14, -40), (6, -36)]); sc.line(spline([(-40, -110), (0, -116), (40, -110)], n=6))
    return sc

def alien_plant():
    sc = Scene()
    sc.shape(Polygon(spline([(-200, 0), (-140, 60), (140, 60), (200, 0)], n=8) + [(200, -40), (-200, -40)]).buffer(0))
    for k, (a, L) in enumerate(((-40, 520), (-10, 640), (20, 560), (50, 420), (-70, 380))):
        aa = math.radians(a)
        P = spline([(k * 20 - 40, 40), (k * 20 - 40 + math.sin(aa) * L * 0.4 + 30, L * 0.45), (math.sin(aa) * L, L)], n=12)
        sc.shape(LineString(P).buffer(16, cap_style=1))
        x, y = P[-1]
        sc.shape(ell(x, y + 50, 50, 70, -aa, 30)); sc.lines(clipL([[(x - 60, y + 30), (x + 60, y + 30)], [(x - 60, y + 70), (x + 60, y + 70)]], ell(x, y + 50, 46, 66, -aa, 30)))
    return sc

def alien_landscape():
    sc = Scene()
    sc.shape(disc(-300, 520, 150, 60)); sc.shape(disc(-90, 600, 70, 36))
    sc.lines(clipL([[(-440, 500), (-160, 560)], [(-400, 440), (-180, 470)]], disc(-300, 520, 146)))
    far = Polygon([(-700, 100)] + [(x, 200 + 120 * math.sin(x / 90) + 60 * math.cos(x / 41)) for x in range(-700, 701, 25)] + [(700, 100)]).buffer(0)
    sc.shape(far)
    near = Polygon([(-700, -100)] + [(x, 40 + 50 * math.sin(x / 140 + 1)) for x in range(-700, 701, 25)] + [(700, -100)]).buffer(0)
    sc.shape(near)
    for (x, h) in ((-500, 260), (320, 340), (520, 220)):
        sc.shape(band([(x, 30), (x + 20, h)], 14)); sc.shape(disc(x + 20, h + 30, 40, 24))
        for a in (-0.8, 0.8): sc.shape(band([(x + 10, h * 0.6), (x + 10 + 80 * math.sin(a), h * 0.6 + 60)], 8)); sc.shape(disc(x + 10 + 80 * math.sin(a), h * 0.6 + 70, 16, 12))
    stars_bg(sc, 12, -700, 380, 700, 700, seed=7, avoid=disc(-300, 520, 160).union(disc(-90, 600, 80)))
    return sc

def ringed_planet():
    sc = Scene()
    back = ell(0, 0, 560, 140, -0.25, 90).difference(ell(0, 0, 420, 100, -0.25, 90)).difference(box(-700, -40, 700, 400).intersection(Polygon([(-700, -300), (700, 60), (700, 400), (-700, 400)])))
    sc.shape(ell(0, 0, 560, 140, -0.25, 90).difference(ell(0, 0, 420, 100, -0.25, 90)))
    p = disc(0, 0, 300, 90); sc.shape(p)
    sc.lines(clipL([spline([(-320, y - 60), (0, y), (320, y - 60)], n=10) for y in (-120, -20, 80, 170)], p.buffer(-3)))
    front = ell(0, 0, 560, 140, -0.25, 90).difference(ell(0, 0, 420, 100, -0.25, 90)).intersection(Polygon([(-700, -400), (700, -400), (700, -60), (-700, 260)]))
    sc.shape(front)
    sc.line(ellipse(0, 0, 490, 120, -0.25, 90))
    for (x, y, r) in ((480, 330, 50), (-520, -300, 34)): sc.shape(disc(x, y, r, 24)); sc.line(circle(x + r * 0.3, y + r * 0.2, r * 0.25, 10))
    return sc

def black_hole():
    sc = Scene()
    for k in range(8):
        f = 1 - k * 0.09
        sc.line(ellipse(0, 0, 560 * f, 140 * f, 0, 80))
    sc.shape(disc(0, 0, 160, 60))
    halo = disc(0, 0, 200, 60).difference(disc(0, 0, 170, 60)); sc.line(circle(0, 0, 200, 60))
    sc.shape(ell(0, 0, 560, 140, 0, 80).intersection(box(-700, -400, 700, -10)).difference(disc(0, 0, 162, 60)).union(disc(0, 0, 0.1)))
    for k in range(4):
        f = 1 - k * 0.12
        sc.lines(clipL([ellipse(0, 0, 540 * f, 130 * f, 0, 80)], box(-700, -400, 700, -12)))
    return sc

def wormhole():
    sc = Scene()
    for k in range(14):
        f = 1 - k * 0.068
        cx = 30 * k; cy = 10 * k
        sc.line(ellipse(cx, cy, 520 * f, 300 * f, 0.1 * k, 80))
    for k in range(10):
        a = TAU * k / 10
        sc.line(spline([(520 * math.cos(a), 300 * math.sin(a)), (300 * math.cos(a + 0.4) + 150, 170 * math.sin(a + 0.4) + 50), (390, 130)], n=12))
    return sc

def time_machine():
    sc = Scene()
    sc.shape(rr(-400, -40, 400, 0, 10))
    for s in (-1, 1): sc.shape(band([(s * 300, 0), (s * 280, 140)], 16))
    sc.shape(rr(-320, 140, 320, 180, 10))
    wheel = disc(-120, 520, 300, 100); sc.shape(wheel)
    for k in range(16):
        a = TAU * k / 16; sc.line([(-120 + 60 * math.cos(a), 520 + 60 * math.sin(a)), (-120 + 290 * math.cos(a), 520 + 290 * math.sin(a))])
    sc.line(circle(-120, 520, 270, 90)); sc.shape(disc(-120, 520, 60, 30))
    sc.shape(rr(-80, 180, 200, 230, 14))
    sc.shape(Polygon(spline([(-60, 230), (-80, 420), (0, 460), (60, 420), (40, 230)], n=8) + [(-60, 230)]).buffer(0))
    sc.shape(rr(150, 180, 330, 420, 20)); sc.line(circle(240, 340, 50, 30)); sc.line([(240, 340), (270, 380)])
    for k, x in enumerate((180, 220, 260, 300)): sc.shape(disc(x, 230, 12, 10))
    sc.shape(band([(300, 420), (340, 520)], 10)); sc.shape(disc(345, 530, 20, 12))
    return sc

def hover_car():
    sc = Scene()
    body = Polygon(spline([(-420, 40), (-380, 140), (-100, 180), (100, 290), (300, 280), (430, 150), (460, 60), (380, 10), (-380, 0)], closed=True, n=8, tension=0.4)).buffer(0)
    sc.shape(body)
    sc.shape(Polygon(spline([(-60, 180), (100, 270), (290, 262), (380, 160)], n=8) + [(-60, 180)]).buffer(0))
    sc.line(spline([(-400, 90), (0, 110), (440, 90)], n=8))
    for x in (-280, 260):
        sc.shape(ell(x, -10, 110, 36, 0, 30)); sc.line(ellipse(x, -10, 60, 18, 0, 20))
        for k in range(3): sc.line([(x - 60 + k * 60, -60), (x - 70 + k * 60, -140)])
    sc.shape(rr(-460, 80, -400, 160, 14))
    return sc

def floating_city():
    sc = Scene()
    rock = Polygon(spline([(-450, 0), (-300, -150), (-150, -330), (0, -450), (120, -320), (300, -160), (450, 0)], n=10)).buffer(0)
    sc.shape(rock)
    for (x0, x1) in ((-300, -200), (60, 120)): sc.lines([[(x, -60), (x - 10, -600)] for x in (x0, (x0 + x1) / 2, x1)])
    for (x, w, h, kind) in ((-360, 70, 180, 'dome'), (-260, 80, 320, 'spire'), (-150, 90, 240, 'flat'), (-30, 100, 420, 'spire'), (90, 80, 280, 'dome'), (200, 90, 200, 'flat'), (310, 70, 260, 'spire')):
        sc.shape(rr(x - w / 2, 0, x + w / 2, h))
        if kind == 'dome': sc.shape(ell(x, h, w / 2, w * 0.45).intersection(box(-1e4, h, 1e4, 1e4)))
        elif kind == 'spire': sc.shape(Polygon([(x - w * 0.3, h), (x + w * 0.3, h), (x, h + w * 1.3)]))
        sc.lines([[(x - w / 2 + 12, y), (x + w / 2 - 12, y)] for y in range(40, int(h) - 20, 50)])
    sc.line([(-450, 0), (450, 0)])
    for (x, y) in ((-600, 300), (560, 420), (520, -200)): sc.line(spline([(x - 60, y), (x - 20, y + 30), (x + 20, y + 10), (x + 60, y + 30)], n=8))
    return sc

def dyson_sphere():
    sc = Scene()
    sc.shape(disc(0, 0, 160, 60))
    for k in range(16):
        a = TAU * k / 16; sc.line([(190 * math.cos(a), 190 * math.sin(a)), (240 * math.cos(a), 240 * math.sin(a))])
    R = 420
    shell = disc(0, 0, R, 120).difference(disc(0, 0, R - 18, 120))
    for a in np.linspace(0, math.pi, 7)[1:-1]:
        sc.line(ellipse(0, 0, R * abs(math.cos(a)) + 0.1, R, 0, 80))
    for y in np.linspace(-R, R, 9)[1:-1]:
        w = math.sqrt(R * R - y * y); sc.line([(-w, y), (w, y)])
    sc.line(circle(0, 0, R, 120))
    return sc

def space_elevator():
    sc = Scene()
    earth = disc(0, -700, 500, 140).intersection(box(-1000, -1300, 1000, -300)); sc.shape(earth)
    sc.lines(clipL([spline([(-400, -300), (-200, -360), (-100, -420), (100, -380)], n=10), spline([(100, -260), (250, -300), (380, -400)], n=8)], earth))
    sc.line([(0, -200), (0, 600)]); sc.line([(14, -200), (14, 600)])
    sc.shape(rr(-30, 120, 44, 180, 10))
    st = rr(-200, 600, 220, 700, 30); sc.shape(st); sc.shape(disc(7, 650, 160, 50).intersection(box(-300, 700, 300, 900)).union(rr(-60, 700, 74, 760, 10)))
    for x in (-300, 320): sc.shape(rr(x - 80, 620, x + 80, 680, 6)); sc.line([(x - 80, 650), (x + 80, 650)])
    sc.shape(band([(-220, 650), (-220, 650)], 2))
    stars_bg(sc, 14, -600, -100, 600, 800, seed=11, avoid=box(-320, -300, 340, 800))
    return sc

def teleporter():
    sc = Scene()
    sc.shape(ell(0, 0, 360, 80, 0, 60)); sc.line(ellipse(0, 0, 290, 60, 0, 60))
    sc.shape(ell(0, -30, 360, 80, 0, 60).difference(ell(0, 0, 360, 80, 0, 60)))
    beam = Polygon([(-280, 0), (280, 0), (280, 640), (-280, 640)])
    for x in range(-260, 280, 65): sc.line([(x, 30), (x, 620)])
    sc.shape(ell(0, 680, 360, 80, 0, 60))
    for (x, y) in ((-150, 200), (120, 300), (-60, 450), (180, 520), (40, 120)):
        sc.line([(x - 18, y), (x + 18, y)]); sc.line([(x, y - 18), (x, y + 18)])
    return sc

def cryo_pod():
    sc = Scene()
    pod = Polygon(spline([(0, 650), (230, 560), (260, 0), (230, -560), (0, -650), (-230, -560), (-260, 0), (-230, 560)], closed=True, n=10, tension=0.45)).buffer(0)
    sc.shape(pod)
    win = Polygon(spline([(0, 520), (150, 440), (160, 40), (0, -40), (-160, 40), (-150, 440)], closed=True, n=8, tension=0.45)).buffer(0); sc.shape(win)
    sc.lines(clipL([[(-200, 300), (60, 520)], [(-200, 200), (120, 470)]], win.buffer(-10)))
    sc.shape(rr(-120, -300, 120, -120, 20)); sc.lines([[(-90, -170), (90, -170)], [(-90, -210), (40, -210)]])
    sc.line(circle(70, -250, 18, 12))
    for y in (-450, -380): sc.line([(-200, y), (200, y)])
    sc.shape(rr(-300, -700, 300, -650, 10))
    return sc

def cyborg_profile():
    sc = Scene()
    head = Polygon(spline([(300, 0), (280, 200), (150, 380), (-80, 420), (-250, 300), (-300, 80), (-260, -120), (-200, -300), (-60, -360), (60, -260), (120, -200), (180, -140), (220, -60)], closed=True, n=8, tension=0.4)).buffer(0)
    sc.shape(band([(-140, -300), (-150, -560)], 160))
    sc.shape(head)
    plate = head.intersection(box(-400, -100, 20, 500))
    sc.line(spline([(20, 420), (10, 200), (40, 60), (-20, -120), (-160, -260)], n=10))
    for (a, b) in (((-60, 300), (-200, 300)), ((-60, 220), (-140, 150)), ((-100, 100), (-260, 100)), ((-50, -20), (-200, -80))):
        sc.line([a, b]); sc.shape(disc(b[0], b[1], 12, 10))
    sc.shape(disc(120, 140, 30, 20)); sc.line(circle(120, 140, 12, 10))
    sc.line(spline([(200, -150), (240, -170), (260, -200)], n=4))
    return sc

def solar_sail():
    sc = Scene()
    for k in range(4):
        a = TAU * k / 4 + math.pi / 4
        tri = Polygon([(0, 0), (500 * math.cos(a - 0.4), 500 * math.sin(a - 0.4)), (500 * math.cos(a + 0.4), 500 * math.sin(a + 0.4))])
        sc.shape(tri)
        sc.lines(clipL([[(0, 0), (520 * math.cos(a), 520 * math.sin(a))]] + [[(r * math.cos(a - 0.4), r * math.sin(a - 0.4)), (r * math.cos(a + 0.4), r * math.sin(a + 0.4))] for r in (150, 300)], tri.buffer(1)))
    sc.shape(disc(0, 0, 50, 30)); sc.line(circle(0, 0, 25, 16))
    return sc

def asteroid_miner():
    sc = Scene()
    ast = Polygon(spline([(-150, 0), (-50, 220), (150, 260), (330, 160), (380, -40), (250, -230), (0, -240), (-140, -150)], closed=True, n=6, tension=0.3)).buffer(0)
    sc.shape(ast)
    for (x, y, r) in ((60, 80, 40), (200, -60, 30), (0, -120, 22), (260, 120, 26)): sc.line(circle(x, y, r, 20))
    sc.shape(band([(-160, 20), (-400, 60)], 30)); sc.shape(Polygon([(-150, -20), (-150, 60), (-100, 20)]))
    sc.shape(rr(-700, -20, -400, 140, 30)); sc.shape(Polygon(spline([(-400, 120), (-360, 170), (-300, 160)], n=4) + [(-400, 120)]).buffer(0))
    for y in (10, 110): sc.shape(rr(-760, y - 20, -700, y + 20, 8))
    sc.shape(rr(-640, 140, -460, 200, 8))
    return sc

def terraform_dome():
    sc = Scene()
    ground = Polygon([(-700, -150)] + [(x, -20 + 20 * math.sin(x / 80)) for x in range(-700, 701, 25)] + [(700, -150)]).buffer(0)
    dome = ell(0, -10, 420, 380).intersection(box(-500, -10, 500, 500))
    sc.shape(dome)
    for (x, h) in ((-200, 160), (-60, 220), (100, 180), (230, 130)):
        sc.shape(band([(x, -10), (x, h * 0.6)], 14)); sc.shape(disc(x, h * 0.6 + 50, 60, 24))
    for a in np.linspace(0.3, 2.84, 6): sc.lines(clipL([[(0, -10), (440 * math.cos(a), -10 + 400 * math.sin(a))]], dome.buffer(-6)))
    sc.line(ellipse(0, 120, 300, 40, 0, 50)) if False else None
    sc.shape(ground)
    for (x, r) in ((-560, 30), (520, 22)): sc.line(ellipse(x, -70, r, r * 0.35, 0, 16))
    sc.line(circle(500, 500, 90, 40)); stars_bg(sc, 10, -700, 300, 700, 650, seed=13, avoid=disc(500, 500, 100))
    return sc

def ufo_city():
    sc = Scene()
    for (x, w, h) in ((-560, 100, 200), (-450, 90, 300), (-340, 120, 240), (-200, 90, 380), (-90, 110, 280), (40, 100, 340), (160, 90, 220), (270, 110, 300), (400, 90, 260), (520, 100, 180)):
        sc.shape(rr(x - w / 2, 0, x + w / 2, h))
        for y in range(40, int(h) - 20, 50): sc.line([(x - w / 2 + 14, y), (x + w / 2 - 14, y)])
    sc.items += place(saucer(360, 0.42, 8), 80, 560, 0.75).items
    sc.line([(-640, 0), (640, 0)])
    return sc

def scifi_items():
    A = []
    def add(name, sc, slug): A.append((name, flipL(sc.render()), slug))
    add('Retro rocket on a launch pad', rocket_on_pad(), 'rocket-launch-pad')
    add('Rocket lifting off', rocket_liftoff(), 'rocket-lift-off')
    add('Retro rocket', retro_rocket(), 'retro-rocket')
    add('Flying saucer', saucer(), 'flying-saucer')
    add('Flying saucer beaming up a cow', saucer_cow(), 'saucer-beaming-cow')
    add('Saucer on landing legs', saucer(360, 0.5, 8, legs=True), 'saucer-landing-legs')
    add('Mothership with small saucers', mothership(), 'mothership')
    add('Ring-shaped space station', ring_station(), 'ring-space-station')
    add('Modular space station', modular_station(), 'modular-space-station')
    add('Sleek starship', ship_side('sleek'), 'sleek-starship')
    add('Heavy starship', ship_side('heavy'), 'heavy-starship')
    add('Space cargo hauler', ship_side('hauler'), 'cargo-hauler')
    add('Explorer ship with a ring', ship_side('explorer'), 'explorer-ship')
    add('Starfighter from above', starfighter_top(), 'starfighter-top')
    add('Spaceplane', spaceplane(), 'spaceplane')
    add('Shuttle craft', shuttle_small(), 'shuttle-craft')
    add('Lunar lander', lunar_lander(), 'lunar-lander')
    add('Moon base with domes', moon_base(), 'moon-base')
    add('Mars rover', mars_rover(), 'mars-rover')
    add('Astronaut floating on a tether', astronaut('float'), 'astronaut-floating')
    add('Astronaut planting a flag', astronaut('flag'), 'astronaut-flag')
    add('Space helmet', space_helmet(), 'space-helmet')
    add('Boxy retro robot', robot_boxy(), 'boxy-robot')
    add('Humanoid android', android(), 'android')
    add('Helper robot on wheels', helper_robot(), 'helper-robot')
    add('Spider robot', spider_robot(), 'spider-robot')
    add('Robot dog', robot_dog(), 'robot-dog')
    add('Giant walking machine', mech_walker(), 'walking-machine')
    add('Cute alien', cute_alien(), 'cute-alien')
    add('Tentacled alien', tentacle_alien(), 'tentacled-alien')
    add('Big-eyed alien head', grey_alien_head(), 'big-eyed-alien')
    add('Alien plant', alien_plant(), 'alien-plant')
    add('Alien landscape with two moons', alien_landscape(), 'alien-landscape')
    add('Ringed planet with moons', ringed_planet(), 'ringed-planet')
    add('Black hole', black_hole(), 'black-hole')
    add('Wormhole', wormhole(), 'wormhole')
    add('Victorian time machine', time_machine(), 'time-machine')
    add('Hover car', hover_car(), 'hover-car')
    add('Floating city', floating_city(), 'floating-city')
    add('Dyson sphere', dyson_sphere(), 'dyson-sphere')
    add('Space elevator', space_elevator(), 'space-elevator')
    add('Teleporter pad', teleporter(), 'teleporter')
    add('Cryo pod', cryo_pod(), 'cryo-pod')
    add('Cyborg in profile', cyborg_profile(), 'cyborg-profile')
    add('Solar sail', solar_sail(), 'solar-sail')
    add('Asteroid mining ship', asteroid_miner(), 'asteroid-miner')
    add('Terraforming dome', terraform_dome(), 'terraforming-dome')
    add('Flying saucer over a city', ufo_city(), 'saucer-over-city')
    return A

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    items = []
    for name, L, slug in scifi_items():
        it = Item('scifi', name, L); it.slug = slug; items.append(it)
    save(items, OUT)
    P = sorted(export_size(i.lines)[0] for i in items)
    print(len(items), 'sci-fi; median', P[len(P) // 2], 'max', P[-1])
    if SHEET:
        for i in range(0, len(items), 30):
            sheet(items[i:i + 30], SHEET.replace('.png', f'_{i // 30}.png'), cols=6, cell=2.6)
