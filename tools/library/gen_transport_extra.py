"""A few more vehicles for 'Boats, trains and more': steam locomotive, double-decker bus, road bicycle,
kick scooter, rowing boat, canoe with a paddler and a cable car. Drawn y-up, flipped at the end.
Usage: python3 -I gen_transport_extra.py <out.json> [sheet.png]"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from gen_poses import Figure, bicycle, stick, disc, chain, P_, ad, V, flipL
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

def rbox(x0, y0, x1, y1, r=0):
    g = box(x0, y0, x1, y1)
    return g.buffer(-r, join_style=1).buffer(r, join_style=1) if r else g

def wheel(sc, c, r, spokes=8, hub=0.18):
    sc.geom(disc(c, r))
    sc.line(circle(c[0], c[1], r * 0.82, 40))
    sc.geom(disc(c, r * hub))
    for i in range(spokes):
        t = i * math.pi * 2 / spokes
        sc.line([(c[0] + r * hub * math.cos(t), c[1] + r * hub * math.sin(t)), (c[0] + r * 0.82 * math.cos(t), c[1] + r * 0.82 * math.sin(t))])

def locomotive():
    sc = Scene()
    sc.geom(rbox(-80, 120, 640, 165, 6))                                   # frame
    sc.geom(rbox(-40, 165, 150, 430, 8))                                   # cab
    sc.geom(rbox(-70, 420, 180, 450, 6))                                   # cab roof
    sc.geom(rbox(10, 300, 100, 390, 10)); sc.line([(55, 300), (55, 390)])  # window
    sc.geom(rbox(150, 170, 560, 330, 70))                                  # boiler
    for x in (250, 350, 450): sc.line([(x, 172), (x, 328)])
    sc.geom(rbox(540, 165, 600, 335, 20))                                  # smokebox door
    sc.geom(disc((572, 250), 22))
    sc.geom(P_([(470, 320), (510, 320), (520, 420), (460, 420)]))          # chimney
    sc.geom(rbox(448, 410, 532, 440, 8))
    sc.geom(unary_union([disc((330, 340), 34), box(296, 320, 364, 340)]))   # dome
    sc.geom(P_([(600, 120), (680, 30), (690, 30), (690, 120)]))            # cow catcher
    for x in range(612, 690, 20): sc.line([(x, 120), (x + 6, 34)])
    sc.geom(rbox(560, 110, 610, 150, 4))                                   # buffer beam
    for c, r in (((90, 90), 82), ((270, 90), 82), ((450, 90), 82)):
        wheel(sc, c, r, 10)
    for c in ((570, 50), (650, 50)): wheel(sc, c, 42, 6, 0.26)
    pins = [(90 + 40, 90), (270 + 40, 90), (450 + 40, 90)]
    sc.geom(LineString(pins).buffer(9))                                    # coupling rod
    sc.geom(LineString([pins[1], (560, 150)]).buffer(8))                   # connecting rod
    sc.geom(rbox(520, 135, 610, 175, 8))                                   # cylinder
    # tender
    sc.geom(rbox(-420, 120, -90, 360, 10)); sc.geom(rbox(-430, 350, -80, 372, 4))
    sc.line([(-400, 300), (-110, 300)])
    for x in (-360, -150): wheel(sc, (x, 60), 58, 8)
    sc.geom(rbox(-100, 128, -70, 150, 3))
    # smoke
    for k, (dx, dy, r) in enumerate(((10, 520, 46), (-60, 600, 60), (-170, 660, 74), (-310, 690, 86))):
        sc.line(circle(490 + dx, dy, r, 36))
    return sc

def double_decker():
    sc = Scene()
    body = rbox(-560, 70, 560, 760, 40)
    sc.geom(body)
    sc.line([(-560, 420), (560, 420)]); sc.line([(-560, 130), (560, 130)])
    for row, (y0, y1) in enumerate(((470, 660), (190, 380))):
        x = -520
        while x < 420:
            w = 150
            if row == 1 and x > 300: break
            sc.geom(rbox(x, y0, x + w, y1, 12)); x += w + 24
    sc.geom(rbox(400, 140, 520, 400, 8)); sc.line([(460, 140), (460, 400)])  # door
    sc.geom(rbox(480, 680, 560, 740, 8)); sc.geom(rbox(-520, 680, 380, 740, 10))   # destination board
    for t in ytext('CITY CENTRE', -70, 696, 34, 'HersheySans1'): sc.line(t)
    for c in ((-360, 90), (330, 90)):
        sc.geom(disc(c, 92)); sc.geom(disc(c, 52)); sc.geom(disc(c, 16))
    sc.geom(rbox(540, 160, 576, 230, 8))
    return sc

def ytext(s, x, y, size, font):
    return [[(px, -py) for px, py in P] for P in text(s, x, -y, size, font)]

def road_bike():
    sc = Scene()
    J = {'H': (0.0, 0.0)}
    for kind, g, *rest in bicycle((0, -46), (340, 34), (70, -440))(J, None, None):
        if kind == 'shape': sc.geom(g)
        elif kind == 'line': sc.line(g)
    for c, a in (((70, -440), -40), ((70, -440), 140)):
        p = ad(c, V(a, 90)); sc.geom(stick(c, p, 8)); sc.geom(P_([(p[0] - 32, p[1] - 8), (p[0] + 32, p[1] - 8), (p[0] + 32, p[1] + 8), (p[0] - 32, p[1] + 8)]))
    return sc

def kick_scooter():
    sc = Scene()
    for c in ((-300, 60), (300, 60)):
        sc.geom(disc(c, 60)); sc.geom(disc(c, 14))
    sc.geom(rbox(-320, 90, 220, 130, 18))
    sc.geom(P_([(-330, 100), (-300, 100), (-290, 150), (-340, 150)]))
    sc.geom(stick((300, 60), (250, 780), 14)); sc.geom(stick((220, 110), (262, 300), 12))
    sc.geom(stick((180, 790), (320, 790), 16))
    for x in (180, 320): sc.geom(rbox(x - 22, 776, x + 22, 804, 10))
    return sc

def rowing_boat():
    sc = Scene()
    for i in range(6):
        x = -780 + i * 300
        sc.line(spline([(x, 40), (x + 75, 64), (x + 150, 40), (x + 225, 16), (x + 300, 40)], n=8))
    hull = P_(spline([(-520, 260), (-440, 120), (-200, 40), (220, 40), (470, 120), (560, 280), (500, 250), (-460, 240)], closed=True, n=8, tension=0.4))
    sc.geom(hull)
    sc.line(spline([(-470, 210), (-180, 196), (220, 196), (520, 236)], n=12))
    for x in (-500, -200, 100, 400): pass
    sc.geom(rbox(-160, 220, -40, 250, 6)); sc.geom(rbox(160, 220, 280, 250, 6))
    for (a, b) in (((-60, 260), (-640, -30)), ((60, 260), (640, -30))):
        sc.geom(stick(a, b, 8))
        d = (b[0] - a[0], b[1] - a[1]); L = math.hypot(*d); u = (d[0] / L, d[1] / L)
        sc.geom(Polygon(ellipse(b[0] - u[0] * 60, b[1] - u[1] * 60, 80, 26, math.atan2(u[1], u[0]), 30)))
    sc.geom(disc((-60, 262), 14)); sc.geom(disc((60, 262), 14))
    return sc

def canoe():
    """A paddler kneeling in a canoe, built with the pose engine."""
    p = dict(kind='m', view='S', torso=88, head=88, top='tee', bottom='trousers', hat='cap',
             arms={'L': ('ik', (150, 240), -1, -60), 'R': ('ik', (110, -20), -1, -100)}, hands={'L': 'fist', 'R': 'fist'},
             legs={'L': (-90, 182, -110), 'R': (-80, 178, -110)})
    def boat(J, B, F_):
        knee_y = min(J['KL'][1], J['KR'][1]) + 96
        hull = P_(spline([(-640, knee_y + 140), (-580, knee_y - 60), (-300, knee_y - 172), (300, knee_y - 172), (580, knee_y - 60), (660, knee_y + 150), (600, knee_y + 110), (-580, knee_y + 100)], closed=True, n=8, tension=0.4))
        return [('shape', hull), ('line', spline([(-600, knee_y + 114), (-200, knee_y + 70), (200, knee_y + 70), (630, knee_y + 124)], n=12), hull)]
    def paddle(J, B, F_):
        a, b = J['PL'], J['PR']; d = (b[0] - a[0], b[1] - a[1]); L = math.hypot(*d); u = (d[0] / L, d[1] / L)
        top = ad(a, u, -60); end = ad(a, u, 640)
        out = [('shape', stick(top, end, 8)), ('shape', stick(ad(top, (-30, 0)), ad(top, (30, 0)), 8))]
        out.append(('shape', Polygon(ellipse(end[0] + u[0] * 70, end[1] + u[1] * 70, 34, 100, math.atan2(u[1], u[0]) - math.pi / 2, 30))))
        return out
    def waves(J, B, F_):
        y = min(J['KL'][1], J['KR'][1]) - 20; out = []
        for i in range(6):
            x = -900 + i * 320
            out.append(('line', spline([(x, y), (x + 80, y + 24), (x + 160, y), (x + 240, y - 20), (x + 320, y)], n=8), None))
        return out
    p['props'] = [('back', waves), ('mid', boat), ('front', paddle)]
    p['order'] = ['back', 'hair_back', 'armL', 'legL', 'between', 'pelvis', 'legR', 'skirt', 'mid', 'neck', 'torso', 'head', 'hair', 'armR', 'front']
    return Figure(p).build()

def cable_car():
    sc = Scene()
    sc.line([(-800, 860), (800, 700)]); sc.line([(-800, 820), (800, 660)])
    hanger_top = (0, 780)
    sc.geom(rbox(-70, 770, 70, 800, 10))
    for c in ((-40, 800), (40, 792)): sc.geom(disc(c, 22))
    sc.geom(stick((0, 770), (0, 560), 10)); sc.geom(stick((0, 560), (-120, 480), 8)); sc.geom(stick((0, 560), (120, 480), 8))
    cab = rbox(-300, 60, 300, 480, 50); sc.geom(cab)
    sc.geom(rbox(-320, 460, 320, 500, 14)); sc.geom(rbox(-320, 40, 320, 80, 14))
    for x in (-260, -120, 20, 160):
        sc.geom(rbox(x, 230, x + 110, 420, 12))
    sc.line([(-300, 200), (300, 200)])
    return sc

ITEMS = [('Steam locomotive', locomotive, 'steam-locomotive'), ('Double-decker bus', double_decker, 'double-decker-bus'),
         ('Road bicycle', road_bike, 'road-bicycle'), ('Kick scooter', kick_scooter, 'kick-scooter'), ('Rowing boat', rowing_boat, 'rowing-boat'),
         ('Canoe', None, 'canoe'), ('Cable car', cable_car, 'cable-car')]

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    items = []
    for name, fn, slug in ITEMS:
        L = canoe() if fn is None else flipL(fn().render())
        it = Item('transport', name, L); it.slug = slug; items.append(it)
    save(items, OUT)
    if SHEET: sheet(items, SHEET, cols=4, cell=3.2)
