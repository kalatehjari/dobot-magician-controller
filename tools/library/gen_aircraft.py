"""Aircraft and army: side views, top views (planforms) and front views of aircraft, military
vehicles, ships, insignia and field gear. No standalone weapons, nothing being fired, no real insignia.
All drawing here is y-up (flipped at the end). Usage: python3 -I gen_aircraft.py <out.json> [sheet.png]"""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

def flipL(L): return [[(x, -y) for x, y in P] for P in L]
def ytext(s, x, y, size, font='HersheySansMed'): return [[(px, -py) for px, py in P] for P in text(s, x, -y, size, font)]
def poly_r(pts, r):
    """Polygon with corners rounded by r."""
    g = Polygon(pts).buffer(0)
    return g.buffer(-r, join_style=1).buffer(r, join_style=1) if r > 0 else g
def band(P, w, cap='flat'): return thick(P, w, cap=cap)
def ell(cx, cy, rx, ry, rot=0.0, n=None): return Polygon(ellipse(cx, cy, rx, ry, rot, n))
def disc(cx, cy, r, n=None): return Polygon(circle(cx, cy, r, n))

# ================================================================ aircraft builders
def fuselage(L, D, nose=0.12, tail=0.32, tail_up=0.35, nose_kind='round', belly=0.0):
    """Side outline of a fuselage, nose to the right (x = +L/2), centre line y = 0."""
    h = D / 2; xn = L / 2; xt = -L / 2
    if nose_kind == 'pointed':
        top = [(xt, h * (0.6 + tail_up)), (xt + L * tail, h), (xn - L * nose, h), (xn - L * nose * 0.4, h * 0.5), (xn, -h * 0.05)]
        bot = [(xn, -h * 0.05), (xn - L * nose * 0.5, -h * 0.75), (xn - L * nose, -h - belly), (xt + L * tail, -h - belly), (xt, h * (tail_up + 0.2))]
    else:
        top = [(xt, h * (0.6 + tail_up)), (xt + L * tail, h), (xn - L * nose, h), (xn - L * nose * 0.25, h * 0.7), (xn, -h * 0.1)]
        bot = [(xn, -h * 0.1), (xn - L * nose * 0.3, -h * 0.85), (xn - L * nose, -h - belly), (xt + L * tail, -h - belly), (xt, h * (tail_up + 0.2))]
    return spline(top + bot[1:-1] + [top[0]], closed=True, n=10, tension=0.35)

def windows(x0, x1, y, w=9, h=13, gap=24):
    out = []
    x = x0
    while x < x1:
        out.append(rect(x, y - h / 2, w, h, 4)); x += gap
    return out

def fin(sc, x_root, y_root, root_chord, tip_chord, height, sweep):
    sc.shape([(x_root, y_root), (x_root - sweep, y_root + height), (x_root - sweep - tip_chord, y_root + height), (x_root - root_chord, y_root), (x_root, y_root)])

def airfoil(x_le, y, chord, t, rot=0.0):
    pts = []
    for i in range(25):
        u = i / 24; xx = x_le - chord * u
        yy = t * (1.4 * math.sqrt(u) - 0.8 * u - 0.6 * u * u) * 1.0
        pts.append((xx, y + yy))
    for i in range(24, -1, -1):
        u = i / 24; xx = x_le - chord * u
        pts.append((xx, y - t * 0.25 * (1 - u) * math.sqrt(u) * 1.2))
    return Polygon(pts).buffer(0)

def nacelle(sc, x_front, y, length, r, pylon_to=None, fan=True):
    if pylon_to is not None: sc.shape([(x_front - length * 0.25, y + r * 0.6), (x_front - length * 0.75, y + r * 0.6), (x_front - length * 0.6, pylon_to), (x_front - length * 0.15, pylon_to)])
    sc.shape(poly_r([(x_front, y + r), (x_front - length, y + r * 0.75), (x_front - length, y - r * 0.75), (x_front, y - r)], r * 0.25))
    if fan: sc.line([(x_front - r * 0.25, y + r * 0.85), (x_front - r * 0.25, y - r * 0.85)])

def gear(sc, x, y_top, y_ground, r, twin=False):
    sc.shape(band([(x, y_top), (x, y_ground + r)], r * 0.35))
    for dx in ((-r * 1.1, r * 1.1) if twin else (0,)):
        sc.shape(disc(x + dx, y_ground + r, r, 20)); sc.line(circle(x + dx, y_ground + r, r * 0.45, 12))

def prop_side(sc, x, y, R, spinner=0.12):
    sc.shape(ell(x, y, R * 0.06, R, 0, 24))
    sc.shape(ell(x + R * 0.06, y, R * spinner * 1.2, R * spinner, 0, 16))

def airliner_side(L=640, D=62, eng=True, gear_=True, deck=False, four=False, tail_eng=False, ttail=False, prop=False, high_wing=False, door_rows=True):
    sc = Scene()
    # far-side engines/wing first (behind)
    wing_x = L * 0.08; wy = -D * 0.32 if not high_wing else D * 0.42
    sc.shape(airfoil(wing_x + 40, wy + 6, L * 0.28, 10))
    body = fuselage(L, D, 0.1, 0.3, 0.45)
    if deck:
        hump = spline([(L * 0.02, D * 0.4), (L * 0.18, D * 0.75), (L * 0.36, D * 0.62), (L * 0.46, D * 0.2)], n=10)
        sc.shape(Polygon(hump + [(L * 0.46, 0), (L * 0.02, 0)]).buffer(0))
    sc.shape(body)
    if deck: sc.lines(windows(L * 0.08, L * 0.36, D * 0.52, 7, 10, 20))
    sc.lines(windows(-L * 0.32, L * 0.36, D * 0.12, 8, 12, 20))
    for xd in (L * 0.38, L * 0.05, -L * 0.33):
        sc.line(rect(xd, -D * 0.3, 13, D * 0.62, 4))
    sc.line(spline([(L * 0.45, D * 0.3), (L * 0.47, D * 0.22), (L * 0.49, D * 0.1)], n=4))
    sc.line([(L * 0.43, D * 0.28), (L * 0.47, D * 0.28)])
    # tail
    if ttail:
        fin(sc, -L * 0.36, D * 0.4, L * 0.18, L * 0.08, D * 1.5, L * 0.12)
        sc.shape(ell(-L * 0.48, D * 1.9, L * 0.09, 6))
    else:
        fin(sc, -L * 0.3, D * 0.42, L * 0.2, L * 0.07, D * 1.5, L * 0.13)
        sc.shape(ell(-L * 0.42, D * 0.5, L * 0.09, 6))
    # near wing and engines
    sc.shape(airfoil(wing_x, wy, L * 0.3, 12))
    if prop:
        for k in range(2 if four else 1):
            ex = wing_x + 25 - k * 70
            sc.shape(poly_r([(ex, wy + 14), (ex - 70, wy + 10), (ex - 70, wy - 8), (ex, wy - 12)], 6))
            prop_side(sc, ex + 8, wy + 1, 42)
    elif tail_eng:
        nacelle(sc, -L * 0.2, D * 0.62, L * 0.14, D * 0.24)
    elif eng:
        for k in range(2 if four else 1):
            nacelle(sc, wing_x + 18 - k * 60 + L * 0.03, wy - D * 0.42, L * 0.12, D * 0.24, pylon_to=wy - 4)
    if gear_:
        gear(sc, L * 0.36, -D * 0.4, -D * 1.25, 8)
        gear(sc, wing_x - L * 0.1, -D * 0.45, -D * 1.25, 9, twin=True)
    return sc

def planform(L=600, fw=56, wing_y=40, root=150, span=560, sweep=110, tip=40, tail_span=200, tail_root=70, tail_sweep=50, tail_tip=28,
             engines=(), props=(), nose=0.12, canopy=None, fin_top=False, twin_boom=None, wing_kind='swept'):
    """Top view, nose up (+y)."""
    sc = Scene(); h = L / 2
    def wing_half(s, y_le, root_c, sp, sw, tip_c, w0):
        return [(s * w0, y_le), (s * sp / 2, y_le - sw), (s * sp / 2, y_le - sw - tip_c), (s * w0, y_le - root_c)]
    for s in (-1, 1):
        sc.shape(wing_half(s, wing_y, root, span, sweep, tip, fw * 0.4))
        sc.shape(wing_half(s, -h + tail_root + 30, tail_root, tail_span, tail_sweep, tail_tip, fw * 0.2))
    for (ex, ey, el, ew) in engines:
        for s in (-1, 1): sc.shape(poly_r([(s * ex - ew / 2, ey), (s * ex + ew / 2, ey), (s * ex + ew / 2, ey - el), (s * ex - ew / 2, ey - el)], ew * 0.35))
    for (px, py, pr) in props:
        for s in (-1, 1):
            if px == 0 and s == 1: continue
            sc.shape(ell(s * px, py, pr, pr * 0.07)); sc.shape(disc(s * px, py - 4, pr * 0.12, 12))
    out = spline([(0, h), (fw * 0.45, h - L * nose * 0.5), (fw / 2, h - L * nose), (fw / 2, -h * 0.4), (fw * 0.2, -h + 10), (0, -h), (-fw * 0.2, -h + 10), (-fw / 2, -h * 0.4), (-fw / 2, h - L * nose), (-fw * 0.45, h - L * nose * 0.5)], closed=True, n=8, tension=0.4)
    sc.shape(out)
    if canopy: sc.shape(ell(0, canopy[0], fw * 0.28, canopy[1]))
    else: sc.line(spline([(-fw * 0.3, h - L * nose * 0.8), (0, h - L * nose * 0.6), (fw * 0.3, h - L * nose * 0.8)], n=6))
    if fin_top: sc.shape(poly_r([(-5, -h + tail_root + 40), (5, -h + tail_root + 40), (5, -h + 4), (-5, -h + 4)], 2))
    return sc

def heli_side(L=420, cab=150, boom_y=40, tandem=False, skids=True, text_=None):
    sc = Scene()
    if tandem:
        body = poly_r([(-L / 2, -40), (L / 2, -40), (L / 2 + 10, 60), (L / 2 - 30, 110), (-L / 2, 110), (-L / 2 - 20, 40)], 25)
        sc.shape(body)
        sc.lines(windows(-L / 2 + 40, L / 2 - 60, 50, 14, 20, 32))
        for x, yb, top in ((L / 2 - 60, 110, 170), (-L / 2 + 20, 110, 210)):
            sc.shape(band([(x, yb), (x, top)], 16)); sc.shape(poly_r([(x - 30, top - 20), (x + 30, top - 20), (x + 26, top), (x - 26, top)], 6))
            sc.shape(band([(x - 260, top + 6), (x + 260, top + 6)], 7))
        sc.shape(poly_r([(-L / 2 + 10, 110), (-L / 2 + 120, 110), (-L / 2 + 120, 175), (-L / 2 + 30, 175)], 10))
        for x in (-L / 2 + 70, L / 2 - 80): gear(sc, x, -40, -100, 18)
        return sc
    sc.shape(band([(-cab * 0.2, boom_y), (-L, boom_y + 30)], 26))
    sc.shape([(-L, boom_y + 20), (-L - 30, boom_y + 110), (-L - 50, boom_y + 110), (-L - 30, boom_y + 10)])
    sc.shape(disc(-L - 20, boom_y + 60, 34, 24)); sc.line(circle(-L - 20, boom_y + 60, 6, 8))
    sc.shape(band([(-L + 40, boom_y + 26), (-L + 90, boom_y + 26)], 8))
    body = spline([(cab, 0), (cab * 0.95, 60), (cab * 0.5, 120), (-cab * 0.4, 125), (-cab * 0.7, 80), (-cab * 0.7, -10), (-cab * 0.2, -40), (cab * 0.6, -40)], closed=True, n=10, tension=0.4)
    sc.shape(body)
    sc.line(spline([(cab * 0.92, 40), (cab * 0.5, 110), (cab * 0.05, 110), (cab * 0.05, 30), (cab * 0.92, 40)], n=6, tension=0.3))
    sc.line(rect(-cab * 0.5, 0, cab * 0.4, 90, 8))
    sc.shape(poly_r([(-cab * 0.4, 120), (cab * 0.25, 120), (cab * 0.15, 150), (-cab * 0.35, 150)], 10))
    sc.shape(band([(0, 150), (0, 175)], 10))
    sc.shape(band([(-L * 0.9, 182), (L * 0.75, 182)], 7))
    sc.shape(disc(0, 180, 12, 12))
    if skids:
        for x in (cab * 0.45, -cab * 0.45): sc.shape(band([(x, -38), (x - 10, -80)], 8))
        sc.shape(band(spline([(-cab * 0.75, -82), (cab * 0.7, -82), (cab * 0.85, -65)], n=6), 9, cap='round'))
    if text_: sc.lines(ytext(text_, -cab * 0.05, -8, 26))
    return sc

# ================================================================ aircraft items
def aircraft_items():
    A = []
    def add(name, sc, slug, flip=True):
        L = sc.render() if hasattr(sc, 'render') else sc
        A.append((name, flipL(L) if flip else L, slug))
    add('Wide-body airliner', airliner_side(700, 70), 'wide-body-airliner')
    add('Airliner seen from above', planform(600, 56, 70, 160, 560, 130, 36, 200, 70, 50, 26, engines=[(110, 70, 70, 26), (190, 40, 66, 24)][:1]), 'airliner-top-view')
    # front view of an airliner
    sc = Scene()
    for s in (-1, 1):
        sc.shape([(s * 30, -10), (s * 330, 22), (s * 330, 30), (s * 30, 10)])
        sc.shape(disc(s * 120, -30, 30, 28)); sc.line(circle(s * 120, -30, 20, 24)); sc.shape(disc(s * 120, -30, 6, 8))
        sc.shape([(s * 25, 70), (s * 130, 82), (s * 130, 88), (s * 25, 80)])
        gear(sc, s * 70, -40, -110, 12)
    sc.shape([(-5, 40), (5, 40), (3, 200), (-3, 200)])
    sc.shape(disc(0, 0, 42, 40))
    sc.line(spline([(-24, 10), (-10, 18), (0, 19), (10, 18), (24, 10)], n=6)); sc.line([(-24, 10), (24, 10)])
    gear(sc, 0, -42, -110, 10)
    add('Airliner, front view', sc, 'airliner-front')
    add('Regional jet with rear engines', airliner_side(460, 52, tail_eng=True, ttail=True), 'regional-jet')
    add('Turboprop airliner', airliner_side(480, 54, prop=True, four=False, high_wing=True), 'turboprop-airliner')
    add('Double-deck jumbo jet', airliner_side(720, 74, deck=True, four=True), 'jumbo-jet')
    # supersonic delta airliner
    sc = Scene(); L = 700
    sc.shape(Polygon([(40, -16), (-260, -18), (-300, -6), (-120, -4)]))
    body = spline([(-L / 2, 18), (-L * 0.3, 22), (L * 0.3, 20), (L * 0.42, 12), (L / 2, -14), (L * 0.44, -14), (L * 0.3, -22), (-L * 0.3, -22), (-L / 2, 4)], closed=True, n=10, tension=0.3)
    sc.shape(body); sc.lines(windows(-L * 0.3, L * 0.3, 2, 6, 8, 18))
    fin(sc, -L * 0.3, 18, 120, 40, 120, 70)
    sc.shape(Polygon([(80, -20), (-300, -24), (-320, -16), (-60, -8)]))
    for x in (-150, -230): sc.shape(poly_r([(x, -26), (x - 70, -26), (x - 70, -46), (x, -46)], 4))
    gear(sc, L * 0.35, -20, -90, 7); gear(sc, -150, -40, -90, 8, twin=True)
    add('Supersonic delta-wing airliner', sc, 'supersonic-airliner')
    # cargo plane with rear ramp
    sc = airliner_side(560, 80, prop=True, four=True, high_wing=True, ttail=True, gear_=False)
    sc.shape(poly_r([(-120, -60), (60, -60), (60, -40), (-120, -40)], 6))
    sc.line([(-200, -30), (-280, 20)])
    for x in (-60, -10, 40): gear(sc, x, -40, -90, 12)
    gear(sc, 230, -38, -90, 10)
    add('High-wing cargo plane', sc, 'cargo-plane')
    # seaplane on floats
    sc = Scene()
    body = fuselage(300, 50, 0.16, 0.36, 0.5)
    sc.shape(airfoil(40, 34, 90, 9)); sc.shape(body)
    sc.line(rect(10, -2, 60, 26, 6)); sc.line(rect(-50, -2, 50, 26, 6))
    fin(sc, -110, 18, 50, 24, 60, 30)
    sc.shape(ell(-130, 14, 34, 4))
    prop_side(sc, 155, 0, 40)
    for (a, b) in (((60, -24), (60, -70)), ((-20, -24), (-30, -70)), ((40, 30), (20, -20))): sc.shape(band([a, b], 6))
    sc.shape(spline([(150, -66), (130, -82), (-80, -86), (-120, -76), (-110, -66), (150, -66)], closed=True, n=8, tension=0.3))
    add('Seaplane on floats', sc, 'seaplane')
    # flying boat
    sc = Scene()
    hull = spline([(260, 40), (240, 70), (-200, 70), (-300, 90), (-310, 70), (-260, 10), (-50, -20), (60, -30), (200, -20), (270, 10)], closed=True, n=8, tension=0.35)
    sc.shape(hull); sc.lines(windows(-150, 180, 40, 8, 12, 26))
    sc.line([(60, -30), (40, 10)])
    sc.shape(band([(120, 70), (-60, 70)], 18)); sc.shape(band([(-60, 70), (60, 120)], 8))
    sc.shape(airfoil(120, 122, 160, 14))
    for x in (90, 20):
        sc.shape(poly_r([(x + 20, 128), (x - 60, 124), (x - 60, 112), (x + 20, 112)], 6)); prop_side(sc, x + 26, 120, 40)
    fin(sc, -250, 80, 70, 30, 90, 40); sc.shape(ell(-280, 90, 40, 5))
    sc.shape(band([(-60, 118), (-80, 60)], 5)); sc.shape(ell(-80, 50, 26, 10))
    add('Flying boat', sc, 'flying-boat')
    # light high-wing plane
    sc = Scene()
    sc.shape(airfoil(60, 52, 100, 10))
    body = spline([(-200, 30), (-80, 44), (40, 50), (100, 34), (130, 10), (125, -18), (60, -30), (-60, -24), (-200, 20)], closed=True, n=8, tension=0.35)
    sc.shape(body); sc.line(rect(10, 4, 50, 34, 8)); sc.line(rect(-50, 4, 50, 34, 8))
    sc.shape(band([(30, 46), (0, -10)], 6))
    fin(sc, -150, 30, 50, 26, 66, 30); sc.shape(ell(-180, 26, 32, 4))
    prop_side(sc, 138, 0, 40); gear(sc, 110, -24, -70, 10); gear(sc, -10, -26, -70, 12)
    add('Light high-wing plane', sc, 'light-high-wing-plane')
    # low-wing trainer with bubble canopy
    sc = Scene()
    body = spline([(-220, 26), (-60, 30), (80, 24), (130, 6), (128, -14), (60, -26), (-80, -22), (-220, 14)], closed=True, n=8, tension=0.35)
    sc.shape(airfoil(60, -14, 110, 10)); sc.shape(body)
    sc.shape(spline([(70, 26), (40, 56), (-30, 60), (-70, 30)], n=8) + [(70, 26)]); sc.line([(10, 58), (12, 28)])
    fin(sc, -170, 20, 56, 26, 70, 34); sc.shape(ell(-200, 18, 34, 4))
    prop_side(sc, 136, -4, 40); gear(sc, 110, -20, -66, 9); gear(sc, 20, -22, -66, 11)
    add('Low-wing trainer', sc, 'low-wing-trainer')
    # aerobatic biplane
    sc = Scene()
    sc.shape(airfoil(70, 70, 110, 10))
    body = spline([(-200, 20), (-60, 30), (60, 28), (110, 16), (115, -12), (50, -24), (-60, -20), (-200, 12)], closed=True, n=8, tension=0.35)
    sc.shape(body); sc.line(spline([(10, 28), (0, 44), (-30, 40)], n=4))
    sc.shape(airfoil(80, -18, 110, 10))
    for x in (20, -20): sc.shape(band([(x, -12), (x + 6, 70)], 6))
    sc.line([(20, 66), (-14, -12)])
    fin(sc, -165, 16, 50, 24, 60, 26); sc.shape(ell(-190, 16, 30, 4))
    prop_side(sc, 122, 2, 40); gear(sc, 70, -24, -66, 11); gear(sc, -185, 10, -40, 5)
    add('Aerobatic biplane', sc, 'aerobatic-biplane')
    # 1903-style flyer (top view)
    sc = Scene()
    for y in (0, 30):
        sc.shape(poly_r([(-320, y - 25), (320, y - 25), (320, y + 25), (-320, y + 25)], 18))
    for x in np.linspace(-290, 290, 10): sc.line([(x, -25), (x, 55)])
    sc.shape(poly_r([(-90, 250), (90, 250), (90, 280), (-90, 280)], 10))
    for s in (-1, 1): sc.line([(s * 30, 250), (s * 30, 25)])
    sc.shape(poly_r([(-60, -230), (60, -230), (60, -210), (-60, -210)], 6)); sc.shape(poly_r([(-5, -260), (5, -260), (5, -180), (-5, -180)], 3))
    for s in (-1, 1): sc.line([(s * 30, -210), (s * 30, -25)]); sc.shape(ell(s * 110, -40, 70, 6))
    sc.shape(disc(0, -10, 26, 16)); sc.line([(-40, 20), (40, 20)])
    add('Early biplane from above, 1903 style', sc, 'early-biplane-top')
    # 1909-style monoplane
    sc = Scene()
    sc.shape(airfoil(40, 40, 70, 8))
    for (a, b) in (((60, 30), (-200, 20)), ((60, -20), (-200, 14)), ((60, 30), (60, -20))): sc.shape(band([a, b], 6))
    for x in np.linspace(-170, 30, 7): sc.line([(x, 28 - (x + 170) * 0.0), (x + 20, -16)])
    sc.shape(poly_r([(60, 34), (100, 34), (100, -24), (60, -24)], 8)); prop_side(sc, 106, 6, 46)
    sc.line([(40, 40), (0, 80)]); sc.line([(0, 80), (-30, 40)]); sc.line([(20, 40), (40, -40)])
    fin(sc, -190, 16, 30, 20, 40, 10); sc.shape(ell(-200, 14, 26, 4))
    gear(sc, 70, -24, -70, 14); gear(sc, -190, 12, -40, 5)
    add('Monoplane of 1909', sc, 'monoplane-1909')
    add('Glider seen from above', planform(300, 26, 30, 50, 1000, 10, 22, 120, 30, 16, 16, nose=0.16, canopy=(110, 20)), 'glider-top')
    # hang glider, from below/front
    sc = Scene()
    sc.shape(Polygon([(0, 150), (420, 20), (380, 0), (0, 70), (-380, 0), (-420, 20)]))
    sc.line([(0, 150), (0, 70)])
    for s in (-1, 1): sc.line([(s * 80, 128), (s * 120, 30)]); sc.line([(s * 200, 90), (s * 200, 50)])
    sc.line([(0, 70), (-90, -110)]); sc.line([(0, 70), (90, -110)]); sc.line([(-90, -110), (90, -110)])
    sc.shape(band([(0, 70), (0, -40)], 6))
    sc.shape(ell(-20, -60, 60, 16, 0.1)); sc.shape(disc(40, -52, 16, 16))
    add('Hang glider', sc, 'hang-glider')
    # paraglider
    sc = Scene()
    canopy = spline([(-360, 260), (-250, 340), (0, 380), (250, 340), (360, 260), (300, 250), (0, 300), (-300, 250)], closed=True, n=10, tension=0.4)
    sc.shape(canopy)
    for k in range(-5, 6): sc.line([(k * 60, 300 - abs(k) * 6 + 10), (k * 66, 365 - abs(k) * 10)])
    for k in range(-5, 6): sc.line([(k * 58, 302 - abs(k) * 8), (0 + (8 if k > 0 else -8), 0)])
    sc.shape(poly_r([(-30, -10), (30, -10), (40, -60), (-40, -60)], 10)); sc.shape(disc(0, 20, 18, 16))
    add('Paraglider', sc, 'paraglider')
    # microlight trike
    sc = Scene()
    sc.shape(Polygon([(-380, 210), (380, 210), (300, 230), (0, 260), (-300, 230)]))
    sc.shape(band([(0, 210), (0, 40)], 8)); sc.line([(0, 200), (-120, 40)]); sc.line([(0, 200), (120, 40)]); sc.line([(-120, 40), (120, 40)])
    sc.shape(spline([(150, 0), (120, 40), (40, 50), (-60, 40), (-90, 0), (-40, -30), (100, -30)], closed=True, n=8, tension=0.4))
    prop_side(sc, -110, 20, 46)
    for x in (130, -60): gear(sc, x, -26, -80, 13)
    add('Microlight trike', sc, 'microlight')
    # autogyro
    sc = Scene()
    sc.shape(spline([(120, 0), (100, 40), (20, 50), (-80, 36), (-120, 10), (-60, -20), (80, -24)], closed=True, n=8, tension=0.4))
    sc.line(spline([(100, 38), (60, 48), (20, 48)], n=4))
    sc.shape(band([(-20, 48), (-30, 130)], 8)); sc.shape(band([(-330, 136), (280, 128)], 6)); sc.shape(disc(-30, 132, 8, 10))
    prop_side(sc, -128, 12, 38)
    sc.shape(band([(-60, 10), (-240, 30)], 8)); fin(sc, -220, 30, 40, 26, 60, 20)
    for x in (80, -20): gear(sc, x, -20, -70, 11)
    add('Autogyro', sc, 'autogyro')
    add('Helicopter', heli_side(), 'helicopter-side')
    add('Tandem-rotor helicopter', heli_side(460, tandem=True), 'tandem-rotor-helicopter')
    add('Air-ambulance helicopter', heli_side(400, text_='AMBULANCE'), 'air-ambulance-helicopter')
    # tiltrotor, from the front
    sc = Scene()
    sc.shape(band([(-300, 40), (300, 40)], 18))
    for s in (-1, 1):
        sc.shape(poly_r([(s * 300 - 22, 0), (s * 300 + 22, 0), (s * 300 + 22, 110), (s * 300 - 22, 110)], 12))
        sc.shape(ell(s * 300, 116, 240, 10)); sc.shape(disc(s * 300, 116, 12, 12))
    sc.shape(spline([(0, 80), (60, 60), (70, -20), (0, -50), (-70, -20), (-60, 60)], closed=True, n=8, tension=0.4))
    sc.line(spline([(-40, 40), (0, 56), (40, 40)], n=6)); sc.line([(-40, 40), (40, 40)])
    sc.shape(Polygon([(-8, 70), (8, 70), (5, 170), (-5, 170)]))
    gear(sc, 0, -50, -100, 12)
    add('Tiltrotor aircraft', sc, 'tiltrotor')
    # quadcopter from above
    sc = Scene()
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            sc.shape(band([(0, 0), (s1 * 200, s2 * 200)], 22))
            sc.line(circle(s1 * 200, s2 * 200, 120, 48)); sc.shape(disc(s1 * 200, s2 * 200, 24, 16))
            sc.shape(ell(s1 * 200, s2 * 200, 110, 9, s1 * s2 * 0.6))
    sc.shape(poly_r([(-90, -110), (90, -110), (90, 110), (-90, 110)], 40)); sc.line(circle(0, 80, 22, 16))
    add('Quadcopter drone from above', sc, 'quadcopter-top')
    add('Fixed-wing survey drone', planform(260, 30, 20, 50, 620, 16, 34, 0, 1, 1, 1, props=[(0, -136, 46)], nose=0.18), 'survey-drone')
    # modern airship
    sc = Scene()
    env = ell(0, 120, 330, 80, 0, 80)
    for s in (1,): fin(sc, -250, 120, 90, 50, 120, 50)
    sc.shape(env)
    sc.lines([[(x, 44 + 80 * (1 - math.sqrt(max(0, 1 - (x / 330) ** 2)))), (x, 196 - 80 * (1 - math.sqrt(max(0, 1 - (x / 330) ** 2))))] for x in (-200, -100, 0, 100, 200)])
    fin(sc, -240, 104, 90, 50, -90, 50)
    sc.shape(poly_r([(-70, 50), (90, 50), (80, 0), (-60, 0)], 16)); sc.lines(windows(-50, 70, 28, 10, 12, 24))
    for x in (-120, 110): sc.shape(band([(x, 50), (x, 20)], 6)); sc.shape(poly_r([(x - 20, 10), (x + 20, 10), (x + 20, 30), (x - 20, 30)], 8))
    add('Modern airship', sc, 'modern-airship')
    # hot-air balloon with zigzag stripes
    sc = Scene()
    env = spline([(0, 520), (190, 480), (260, 360), (230, 220), (120, 110), (60, 70), (-60, 70), (-120, 110), (-230, 220), (-260, 360), (-190, 480)], closed=True, n=10, tension=0.4)
    g = Polygon(env); sc.shape(g)
    zz = [(x, 330 + (30 if (i % 2) else -30)) for i, x in enumerate(range(-280, 300, 40))]
    sc.lines(clip_lines([zz, [(x, y + 70) for x, y in zz]], g))
    for x in (-150, -60, 60, 150): sc.lines(clip_lines([[(x * 0.35, 75), (x * 1.3, 360), (x * 0.9, 520)]], g))
    for s in (-1, 1): sc.line([(s * 55, 70), (s * 40, 10)])
    sc.shape(poly_r([(-45, -40), (45, -40), (40, 10), (-40, 10)], 6)); sc.lines([[(-45, -15), (45, -15)]])
    add('Hot-air balloon with zigzag stripes', sc, 'balloon-zigzag')
    # crop duster
    sc = Scene()
    sc.shape(airfoil(60, -14, 110, 10))
    body = spline([(-200, 26), (-60, 34), (50, 40), (100, 30), (126, 0), (110, -22), (50, -28), (-60, -22), (-200, 14)], closed=True, n=8, tension=0.35)
    sc.shape(body); sc.shape(spline([(30, 40), (10, 72), (-40, 74), (-60, 36)], n=6) + [(30, 40)])
    sc.shape(poly_r([(100, 32), (130, 32), (130, -26), (100, -26)], 10)); prop_side(sc, 136, 2, 44)
    fin(sc, -165, 20, 50, 24, 66, 30); sc.shape(ell(-190, 18, 30, 4))
    sc.shape(band([(80, -34), (-80, -34)], 5))
    for x in range(-70, 80, 25): sc.line([(x, -36), (x - 4, -46)])
    gear(sc, 70, -24, -76, 12); gear(sc, -190, 12, -40, 5)
    add('Crop duster', sc, 'crop-duster')
    # firefighting water bomber
    sc = Scene()
    hull = spline([(240, 30), (220, 60), (-180, 60), (-270, 80), (-280, 60), (-230, 10), (-40, -20), (60, -26), (190, -16), (250, 6)], closed=True, n=8, tension=0.35)
    sc.shape(airfoil(100, 82, 130, 12)); sc.shape(hull); sc.lines(windows(150, 210, 34, 10, 12, 22))
    for x in (90, 20): sc.shape(poly_r([(x + 20, 88), (x - 50, 84), (x - 50, 74), (x + 20, 72)], 6)); prop_side(sc, x + 26, 80, 36)
    fin(sc, -230, 70, 60, 26, 80, 34); sc.shape(ell(-260, 80, 36, 5))
    for k in range(6):
        y0 = -30 - k * 22; sc.line(spline([(40 - k * 8, y0), (0 - k * 16, y0 - 12), (-40 - k * 26, y0 - 8)], n=6))
    add('Firefighting water bomber', sc, 'water-bomber')
    # jet engine front view
    sc = Scene()
    sc.shape(disc(0, 0, 300, 90)); sc.line(circle(0, 0, 270, 90)); sc.line(circle(0, 0, 255, 90))
    for k in range(22):
        a = TAU * k / 22
        P = [(60 * math.cos(a), 60 * math.sin(a)), (160 * math.cos(a + 0.25), 160 * math.sin(a + 0.25)), (250 * math.cos(a + 0.35), 250 * math.sin(a + 0.35))]
        sc.line(spline(P, n=6))
    sc.shape(disc(0, 0, 60, 30)); sc.line(spline([(0, 0), (20, 25), (40, 20)], n=4))
    add('Jet engine, front view', sc, 'jet-engine-front')
    # solar-powered plane from above
    sc = planform(260, 24, 20, 70, 1000, 0, 70, 160, 40, 0, 40, props=[(150, 40, 38), (330, 40, 38)], nose=0.2)
    for x in range(-480, 490, 40): sc.line([(x, 18), (x, -48)])
    add('Solar-powered plane', sc, 'solar-plane')
    # human-powered plane
    sc = Scene()
    sc.shape(band([(-480, 120), (480, 120)], 14))
    sc.shape(spline([(60, 60), (40, 90), (-40, 92), (-70, 60), (-40, 20), (40, 20)], closed=True, n=8, tension=0.4))
    sc.shape(band([(-60, 60), (-300, 70)], 6)); fin(sc, -280, 70, 40, 24, 50, 10); sc.shape(ell(-300, 72, 30, 3))
    sc.shape(band([(0, 92), (0, 120)], 5)); prop_side(sc, 70, 60, 50)
    for s in (-1, 1): sc.line([(0, 120), (s * 300, 124)]); sc.line([(0, 30), (s * 200, 118)])
    gear(sc, 0, 20, -20, 10)
    add('Human-powered plane', sc, 'human-powered-plane')
    # ornithopter
    sc = Scene()
    for s in (-1, 1):
        wing = Polygon([(s * 20, 60), (s * 200, 160), (s * 360, 130), (s * 420, 60), (s * 300, 70), (s * 200, 40), (s * 100, 50)])
        sc.shape(wing)
        for k in range(1, 6): sc.line([(s * 20, 60), (s * (60 + k * 70), 160 - k * 18 + (20 if k > 3 else 0))])
    sc.shape(poly_r([(-60, -40), (60, -40), (60, 70), (-60, 70)], 20))
    sc.line(circle(0, 15, 28, 20)); sc.line([(-60, -10), (60, -10)])
    sc.shape(band([(0, -40), (0, -110)], 10)); sc.shape(Polygon([(-80, -110), (80, -110), (0, -160)]))
    add('Flying-machine sketch (ornithopter)', sc, 'ornithopter')
    # airport control tower
    sc = Scene()
    sc.shape(poly_r([(-40, 0), (40, 0), (30, 380), (-30, 380)], 4))
    sc.shape(Polygon([(-80, 380), (80, 380), (110, 420), (110, 470), (-110, 470), (-110, 420)]))
    sc.shape(Polygon([(-120, 470), (120, 470), (90, 490), (-90, 490)]))
    for x in range(-100, 101, 25): sc.line([(x, 422), (x * 1.0, 468)])
    sc.shape(band([(0, 490), (0, 560)], 5)); sc.shape(disc(0, 560, 8, 10))
    sc.shape(poly_r([(-200, 0), (200, 0), (200, 80), (-200, 80)], 4)); sc.lines(windows(-180, 180, 40, 18, 26, 36))
    add('Airport control tower', sc, 'control-tower')
    add('Single-engine plane from above', planform(330, 34, 50, 70, 520, 0, 50, 170, 46, 0, 36, props=[(0, 172, 50)], nose=0.1), 'single-engine-top')
    return A

def clip_lines(L, g):
    out = []
    for P in L: out += lines_of(LineString(P).intersection(g))
    return out

# ================================================================ army builders
def tracks(sc, x0, x1, y0, h, wheels=5, r=None, sprocket='front'):
    """Track run seen from the side between x0 (rear) and x1 (front), bottom at y0."""
    r = r or h * 0.32
    loop = poly_r([(x0, y0), (x1, y0), (x1 + h * 0.4, y0 + h * 0.6), (x1, y0 + h), (x0, y0 + h), (x0 - h * 0.35, y0 + h * 0.55)], h * 0.3)
    sc.shape(loop)
    inner = loop.buffer(-h * 0.12, join_style=1)
    sc.line(lines_of(inner)[0])
    for k in range(wheels):
        x = x0 + (x1 - x0) * (k + 0.5) / wheels
        sc.shape(disc(x, y0 + r + h * 0.08, r, 24)); sc.line(circle(x, y0 + r + h * 0.08, r * 0.35, 12))
    for x in (x0 - h * 0.08, x1 + h * 0.1): sc.shape(disc(x, y0 + h * 0.58, h * 0.24, 20)); sc.line(circle(x, y0 + h * 0.58, h * 0.1, 10))
    for k in range(int((x1 - x0) / (h * 0.18))):
        x = x0 + k * h * 0.18; sc.line([(x, y0 + 2), (x, y0 + h * 0.1)])

def wheel_(sc, x, y, R, rim=0.55):
    sc.shape(disc(x, y, R, 32)); sc.line(circle(x, y, R * rim, 24)); sc.shape(disc(x, y, R * 0.16, 12))
    for k in range(6):
        a = TAU * k / 6; sc.line(circle(x + R * rim * 0.65 * math.cos(a), y + R * rim * 0.65 * math.sin(a), R * 0.05, 6))

def tank(kind='modern'):
    sc = Scene()
    if kind == 'wwi':
        P = [(-260, 0), (220, 0), (300, 90), (260, 170), (-240, 170), (-300, 80)]
        sc.shape(poly_r(P, 30)); sc.line(lines_of(poly_r(P, 30).buffer(-22, join_style=1))[0])
        for x in range(-230, 240, 36): sc.shape(disc(x, 20, 6, 8))
        sc.shape(poly_r([(-60, 80), (40, 80), (40, 150), (-60, 150)], 6)); sc.line(rect(-40, 100, 60, 30, 4))
        sc.shape(poly_r([(-140, 170), (60, 170), (40, 220), (-120, 220)], 10))
        for x in range(-120, 50, 30): sc.line(circle(x, 195, 4, 6))
        return sc
    if kind == 'light':
        tracks(sc, -200, 170, 0, 90, wheels=4)
        sc.shape(Polygon([(-230, 80), (210, 80), (250, 110), (220, 150), (-220, 150)]))
        sc.shape(Polygon([(-90, 150), (80, 150), (60, 210), (-80, 210)]))
        sc.shape(band([(70, 185), (290, 185)], 10)); sc.shape(disc(-30, 214, 12, 10))
        return sc
    if kind == 'ww2':
        tracks(sc, -230, 200, 0, 100, wheels=5)
        sc.shape(Polygon([(-260, 90), (230, 90), (280, 130), (250, 170), (-250, 175), (-270, 140)]))
        sc.shape(spline([(-110, 172), (-120, 230), (-60, 262), (60, 258), (100, 210), (90, 172)], n=8) + [(-110, 172)])
        sc.shape(band([(90, 215), (330, 215)], 14)); sc.shape(disc(-20, 268, 18, 14))
        sc.lines([[(x, 100), (x, 165)] for x in (-150, -40, 70, 180)])
        return sc
    tracks(sc, -260, 220, 0, 100, wheels=6)
    sc.shape(Polygon([(-300, 95), (260, 95), (320, 130), (300, 160), (-290, 165)]))
    sc.shape(Polygon([(-190, 165), (90, 165), (150, 185), (130, 235), (-210, 240), (-230, 200)]))
    sc.shape(band([(140, 210), (430, 210)], 12)); sc.shape(poly_r([(250, 200), (300, 200), (300, 220), (250, 220)], 4))
    sc.shape(poly_r([(-120, 240), (-60, 240), (-60, 262), (-120, 262)], 6)); sc.line([(-170, 240), (-170, 320)])
    sc.lines([[(-280, 130), (280, 130)]])
    return sc

def tank_front():
    sc = Scene()
    for s in (-1, 1): sc.shape(poly_r([(s * 160 - 50, 0), (s * 160 + 50, 0), (s * 160 + 50, 110), (s * 160 - 50, 110)], 12))
    sc.shape(Polygon([(-220, 80), (220, 80), (200, 150), (-200, 150)]))
    sc.shape(Polygon([(-120, 150), (120, 150), (100, 230), (-100, 230)]))
    sc.shape(disc(0, 190, 16, 16)); sc.line(circle(0, 190, 8, 10))
    sc.shape(poly_r([(-60, 230), (-20, 230), (-20, 248), (-60, 248)], 4))
    for s in (-1, 1): sc.lines([[(s * 160 - 40, y), (s * 160 + 40, y)] for y in range(14, 100, 16)])
    return sc

def truck(kind='canvas'):
    sc = Scene(); R = 52
    if kind == 'canvas':
        sc.shape(poly_r([(-330, 60), (60, 60), (60, 90), (-330, 90)], 6))
        sc.shape(spline([(-330, 90), (-330, 230), (-300, 250), (40, 250), (60, 230), (60, 90)], n=8) + [(-330, 90)])
        for x in (-250, -150, -50): sc.line([(x, 92), (x - 6, 246)])
        sc.shape(poly_r([(70, 60), (200, 60), (200, 120), (170, 210), (70, 210)], 10))
        sc.line(rect(90, 140, 70, 55, 6)); sc.shape(poly_r([(200, 60), (250, 60), (250, 120), (200, 120)], 8))
        for x in (-260, -150, 160): wheel_(sc, x, R, R)
    elif kind == 'ambulance':
        sc.shape(poly_r([(-320, 50), (60, 50), (60, 260), (-320, 260)], 12))
        sc.lines(ytext('AMBULANCE', -110, 140, 34)); sc.line(rect(-300, 80, 60, 150, 6))
        sc.shape(poly_r([(70, 50), (200, 50), (200, 110), (170, 200), (70, 200)], 10)); sc.line(rect(90, 130, 70, 55, 6))
        sc.shape(poly_r([(200, 50), (240, 50), (240, 110), (200, 110)], 8))
        for x in (-220, 150): wheel_(sc, x, R, R)
    elif kind == 'jeep':
        sc.shape(Polygon([(-200, 50), (190, 50), (200, 100), (180, 120), (40, 125), (-210, 125), (-220, 90)]))
        sc.shape(band([(30, 125), (10, 210)], 8)); sc.line([(14, 200), (26, 132)])
        sc.shape(poly_r([(-160, 125), (-100, 125), (-100, 160), (-160, 160)], 10))
        sc.shape(spline([(-205, 60), (-210, 118), (-170, 128)], n=4) + [(-205, 60)])
        sc.shape(disc(-235, 95, 50, 24)); sc.line(circle(-235, 95, 24, 16))
        sc.lines([[(-60, 60), (-60, 120)], [(150, 112), (190, 112)]])
        sc.lines(clip_lines([star(-70 + 30, 88, 22, 9)], box(-300, 0, 300, 300)))
        for x in (-130, 120): wheel_(sc, x, 48, 48)
    elif kind == 'halftrack':
        tracks(sc, -280, -50, 0, 80, wheels=3)
        sc.shape(poly_r([(-320, 70), (60, 70), (60, 190), (-320, 190)], 8))
        sc.shape(Polygon([(60, 70), (230, 70), (230, 140), (110, 160), (60, 190)]))
        sc.shape(band([(70, 190), (110, 240)], 6)); wheel_(sc, 150, 50, 50)
    elif kind == 'apc8':
        sc.shape(Polygon([(-330, 70), (250, 70), (330, 140), (280, 220), (-320, 230), (-340, 150)]))
        sc.shape(poly_r([(-120, 230), (20, 230), (10, 270), (-110, 270)], 8)); sc.shape(band([(10, 255), (110, 255)], 8))
        for x in (-250, -150, 60, 160): wheel_(sc, x, 55, 55)
        sc.lines([[(-300, 150), (260, 150)], [(-250, 200), (-250, 160)]])
    elif kind == 'apc_tracked':
        tracks(sc, -250, 200, 0, 90, wheels=5)
        sc.shape(Polygon([(-280, 85), (230, 85), (300, 150), (260, 200), (-280, 205)]))
        sc.shape(poly_r([(-80, 205), (40, 205), (30, 235), (-70, 235)], 8)); sc.line(rect(-250, 110, 60, 70, 6))
    elif kind == 'amphibious':
        sc.shape(spline([(-300, 60), (240, 60), (330, 140), (300, 170), (-310, 170), (-330, 120)], closed=True, n=6, tension=0.3))
        sc.shape(poly_r([(-100, 170), (120, 170), (100, 240), (-80, 240)], 12)); sc.line(rect(-60, 190, 120, 34, 6))
        for x in (-200, -60, 140): wheel_(sc, x, 50, 50)
        sc.lines([[(-310, 110), (320, 110)]])
    return sc


def ship(kind):
    sc = Scene()
    if kind == 'carrier':
        hull = Polygon([(-480, 0), (420, 0), (520, 70), (500, 90), (-500, 90), (-500, 40)])
        sc.shape(hull); sc.shape(band([(-510, 90), (510, 90)], 10))
        sc.shape(Polygon([(80, 95), (200, 95), (190, 180), (110, 180)])); sc.lines(windows(110, 180, 160, 10, 10, 20))
        sc.shape(band([(150, 180), (150, 240)], 6)); sc.line([(130, 220), (170, 220)])
        for x in (-380, -250, -120): sc.shape(Polygon([(x, 95), (x + 50, 95), (x + 60, 102), (x - 10, 102)]))
        sc.lines([[(x, 20), (x, 70)] for x in range(-420, 400, 120)])
    elif kind == 'carrier_top':
        deck = Polygon([(-80, -480), (80, -480), (120, -350), (120, 380), (60, 480), (-60, 480), (-120, 360), (-120, -300)])
        sc.shape(deck)
        sc.lines([[(-80, -420), (100, 380)], [(-60, -420), (120, 360)]])
        sc.lines([[(0, -470), (0, -200)]]); sc.lines([[(-100, y), (100, y)] for y in (-120, 250)])
        sc.shape(poly_r([(70, -60), (115, -60), (115, 80), (70, 80)], 8))
        for (x, y) in ((-40, -300), (-60, 300), (-40, 160)):
            sc.shape(Polygon([(x, y + 34), (x + 6, y + 10), (x + 30, y), (x + 6, y - 6), (x + 4, y - 24), (x - 4, y - 24), (x - 6, y - 6), (x - 30, y), (x - 6, y + 10)]))
    elif kind == 'frigate':
        sc.shape(Polygon([(-420, 10), (330, 10), (440, 80), (-430, 70)]))
        sc.shape(Polygon([(-250, 70), (120, 70), (100, 150), (-200, 150)]))
        sc.shape(poly_r([(-60, 150), (60, 150), (50, 200), (-50, 200)], 6))
        sc.shape(Polygon([(-10, 200), (10, 200), (4, 300), (-4, 300)])); sc.lines([[(-30, 260), (30, 260)], [(-20, 285), (20, 285)]])
        sc.shape(poly_r([(-180, 150), (-120, 150), (-130, 200), (-170, 200)], 6))
        sc.shape(poly_r([(170, 76), (230, 76), (225, 100), (175, 100)], 8))
        sc.lines(windows(-200, 80, 110, 10, 10, 26)); sc.lines([[(-420, 40), (400, 40)]])
    elif kind == 'submarine':
        hull = spline([(-460, 40), (-200, 70), (300, 70), (420, 40), (440, 0), (400, -40), (300, -60), (-200, -60), (-440, -10)], closed=True, n=8, tension=0.35)
        sc.shape(hull); sc.shape(poly_r([(40, 66), (160, 66), (150, 160), (60, 160)], 10))
        sc.shape(band([(70, 130), (40, 130)], 8)); sc.shape(band([(140, 130), (175, 130)], 8))
        for x in (90, 115): sc.shape(band([(x, 160), (x, 210)], 5))
        sc.shape(Polygon([(-440, 0), (-500, 70), (-470, 70), (-410, 20)])); sc.shape(Polygon([(-440, -10), (-500, -70), (-470, -70), (-410, -20)]))
        sc.lines([[(-400, 0), (430, 0)]])
        sc.lines(clip_lines([[(-500, -30), (500, -30)]], box(-600, -200, 600, -28)))
    elif kind == 'patrol':
        sc.shape(Polygon([(-260, 10), (200, 10), (300, 70), (-270, 60)]))
        sc.shape(Polygon([(-150, 60), (110, 60), (80, 130), (-120, 130)])); sc.lines(windows(-110, 70, 100, 14, 18, 30))
        sc.shape(band([(0, 130), (0, 210)], 6)); sc.lines([[(-20, 190), (20, 190)]]); sc.shape(disc(0, 214, 8, 10))
        sc.lines([[(-260, 35), (250, 35)]])
    elif kind == 'landing':
        sc.shape(Polygon([(-300, 0), (220, 0), (240, 30), (240, 110), (-300, 110)]))
        sc.shape(Polygon([(240, 30), (330, 10), (330, 30), (250, 110)])); sc.lines([[(250, 50), (320, 25)]])
        sc.shape(poly_r([(-300, 110), (-180, 110), (-180, 190), (-300, 190)], 8)); sc.lines(windows(-280, -200, 160, 14, 16, 30))
        sc.lines([[(-300, 40), (230, 40)]])
    elif kind == 'hovercraft':
        sc.shape(spline([(-330, 50), (330, 50), (360, 20), (330, -20), (-330, -20), (-360, 20)], closed=True, n=6, tension=0.3))
        for x in range(-300, 320, 40): sc.line([(x, -18), (x, 46)])
        sc.shape(poly_r([(-260, 50), (200, 50), (230, 140), (-230, 140)], 20)); sc.lines(windows(-200, 180, 100, 14, 22, 34))
        for x in (-200, -60):
            sc.shape(poly_r([(x - 60, 140), (x + 60, 140), (x + 60, 260), (x - 60, 260)], 40))
            sc.line(circle(x, 200, 44, 24)); sc.shape(disc(x, 200, 8, 8))
        sc.shape(Polygon([(-300, 140), (-280, 280), (-250, 280), (-250, 140)]))
    return sc


def chevrons(n=3, rocker=1, w=300, gap=70):
    sc = Scene()
    for k in range(n):
        y = k * gap
        sc.shape(Polygon([(-w / 2, y), (0, y + 120), (w / 2, y), (w / 2, y + 36), (0, y + 156), (-w / 2, y + 36)]))
    for k in range(rocker):
        y = -50 - k * gap
        arcp = [(x, y - 60 * (1 - (x / (w / 2)) ** 2) * -1) for x in np.linspace(-w / 2, w / 2, 21)]
        sc.shape(band(arcp, 34))
    return sc

def medal(kind='round'):
    sc = Scene()
    sc.shape(Polygon([(-80, 400), (80, 400), (80, 180), (0, 140), (-80, 180)]))
    for x in (-40, 0, 40): sc.line([(x, 400), (x, 160 + abs(x) * 0.5)])
    sc.shape(poly_r([(-90, 400), (90, 400), (90, 430), (-90, 430)], 6))
    sc.shape(band([(0, 150), (0, 110)], 14))
    if kind == 'round':
        sc.shape(disc(0, 30, 90, 48)); sc.line(circle(0, 30, 74, 40)); sc.shape(Polygon(star(0, 30, 50, 20)))
    elif kind == 'cross':
        arms = unary_union([Polygon([(-24, 120), (24, 120), (60, 30), (24, -60), (-24, -60), (-60, 30)]).buffer(0),
                            Polygon([(-110, 54), (110, 54), (110, 6), (-110, 6)])])
        g = unary_union([Polygon([(-30, 110), (30, 110), (14, 40), (30, -50), (-30, -50), (-14, 40)]), Polygon([(-100, 60), (-30, 46), (30, 46), (100, 60), (100, 0), (30, 14), (-30, 14), (-100, 0)])])
        sc.shape(g); sc.shape(disc(0, 30, 26, 20))
    else:
        sc.shape(Polygon(star(0, 20, 110, 46))); sc.line(Polygon(star(0, 20, 110, 46)).buffer(-12).exterior.coords[:]); sc.shape(disc(0, 20, 30, 20))
    return sc

def dog_tags():
    sc = Scene()
    sc.line(spline([(-60, 420), (-200, 300), (-180, 120), (-40, 40)], n=12)); sc.line(spline([(60, 420), (200, 300), (180, 120), (40, 40)], n=12))
    for k in range(30):
        t = k / 29; x = -60 + 120 * t; sc.line(circle(x, 420 + 10 * math.sin(math.pi * t), 5, 6))
    for (cx, cy, a) in ((-40, -60, 0.15), (40, -90, -0.2)):
        g = Polygon(rot(rect(cx - 70, cy - 110, 140, 220, 30), a, cx, cy)); sc.shape(g)
        sc.line(circle(cx + 50 * math.sin(a), cy + 90, 8, 10))
        for k in range(4): sc.lines(clip_lines([[(cx - 50, cy + 40 - k * 30), (cx + 40, cy + 40 - k * 30)]], g.buffer(-20)))
    return sc

def headgear(kind):
    sc = Scene()
    if kind == 'field_cap':
        sc.shape(spline([(-200, 0), (-210, 120), (-120, 200), (100, 210), (200, 130), (210, 0)], n=10) + [(-200, 0)])
        sc.shape(spline([(-30, 0), (180, 10), (330, -40), (300, -60), (100, -40), (-30, -20)], closed=True, n=6, tension=0.35))
        sc.lines([[(-200, 40), (200, 40)]]); sc.lines(clip_lines([[(-180, 200 - k * 0), (-150, 0)] for k in (0,)], box(-300, -100, 300, 300)))
    elif kind == 'beret':
        sc.shape(spline([(-260, 40), (-280, 120), (-150, 200), (80, 210), (280, 140), (300, 60), (200, 30), (0, 20)], closed=True, n=8, tension=0.4))
        sc.shape(poly_r([(-230, -20), (230, -20), (230, 40), (-230, 40)], 20)); sc.lines([[(-220, 10), (220, 10)]])
        sc.shape(Polygon([(-150, 60), (-90, 60), (-90, 130), (-120, 150), (-150, 130)])); sc.line(circle(-120, 100, 14, 12))
    elif kind == 'ww2':
        sc.shape(spline([(-300, 0), (-240, 150), (0, 230), (240, 150), (300, 0)], n=10) + [(-300, 0)])
        sc.shape(spline([(-330, 0), (330, 0), (320, -20), (-320, -20)], closed=True, n=4, tension=0.2))
        sc.line(spline([(-200, 0), (-120, -120), (0, -150), (120, -120), (200, 0)], n=10))
    elif kind == 'modern':
        sc.shape(spline([(-260, -20), (-250, 140), (-100, 240), (100, 240), (250, 140), (270, -20), (200, -40), (180, 30), (-200, 30), (-220, -40)], closed=True, n=8, tension=0.35))
        sc.line(spline([(-250, 80), (0, 120), (250, 80)], n=8))
        sc.shape(poly_r([(-200, 40), (200, 40), (200, 110), (-200, 110)], 30)); sc.lines([[(0, 40), (0, 110)]])
        sc.line(circle(-100, 75, 28, 16)); sc.line(circle(100, 75, 28, 16))
    return sc

def boot_military():
    import gen_wear_shoes2 as S2
    from gen_wear_kit import s_flip
    return S2.work_boot()

def canteen():
    sc = Scene()
    sc.shape(spline([(-150, 0), (-180, 200), (-120, 360), (120, 360), (180, 200), (150, 0)], n=10) + [(-150, 0)])
    sc.shape(poly_r([(-200, -40), (200, -40), (180, 120), (-180, 120)], 30)); sc.lines([[(-190, 80), (190, 80)]])
    sc.shape(poly_r([(-50, 360), (50, 360), (50, 420), (-50, 420)], 12)); sc.line(spline([(50, 400), (120, 420), (140, 380)], n=6))
    sc.lines([[(-140, 200), (140, 200)]])
    return sc

def mess_tin():
    sc = Scene()
    sc.shape(spline([(-260, 0), (-270, 150), (-180, 200), (180, 200), (270, 150), (260, 0)], n=10) + [(-260, 0)])
    sc.line(spline([(-240, 40), (-245, 140), (-170, 176), (170, 176), (245, 140), (240, 40)], n=10))
    sc.shape(poly_r([(260, 80), (520, 100), (520, 130), (260, 120)], 10)); sc.line(circle(500, 115, 8, 8))
    return sc

def field_radio():
    sc = Scene()
    sc.shape(poly_r([(-200, 0), (200, 0), (200, 360), (-200, 360)], 20))
    sc.shape(poly_r([(-170, 220), (170, 220), (170, 330), (-170, 330)], 10))
    for k, x in enumerate((-120, -40, 40, 120)): sc.line(circle(x, 280, 22, 16)); sc.line([(x, 280), (x + 14 * math.cos(k), 280 + 14 * math.sin(k))])
    sc.shape(poly_r([(-170, 40), (170, 40), (170, 190), (-170, 190)], 10))
    for x in range(-150, 160, 30): sc.line([(x, 60), (x, 170)])
    sc.shape(band([(150, 360), (190, 400), (330, 900)], 6)); sc.shape(disc(330, 900, 8, 8))
    sc.line(spline([(-200, 120), (-300, 140), (-320, 260), (-260, 300)], n=8)); sc.shape(poly_r([(-300, 290), (-220, 300), (-230, 360), (-300, 350)], 16))
    return sc

def ridge_tent():
    sc = Scene()
    sc.shape(Polygon([(-450, 0), (-300, 0), (-80, 360), (-240, 360)]))
    sc.shape(Polygon([(-300, 0), (300, 0), (0, 380)]))
    sc.shape(Polygon([(-120, 0), (0, 0), (0, 300)])); sc.line([(0, 0), (0, 380)])
    sc.line([(0, 380), (-160, 380)]); sc.lines([[(-300, 0), (-420, -10)], [(300, 0), (420, -10)], [(0, 380), (0, 420)]])
    for x in (-420, 420): sc.line([(x, -10), (x, 20)])
    sc.line([(0, 380), (380, 0)])
    return sc

def camo_panel():
    sc = Scene(); g = box(-400, -300, 400, 300)
    sc.shape(g)
    r = rng(5)
    for k in range(18):
        cx, cy = r.uniform(-380, 380), r.uniform(-280, 280)
        pts = [(cx + r.uniform(40, 110) * math.cos(a), cy + r.uniform(30, 90) * math.sin(a)) for a in np.linspace(0, TAU, 9)[:-1]]
        P = spline(pts, closed=True, n=6, tension=0.4)
        sc.lines(clip_lines([P], g))
    return sc

def sandbags():
    sc = Scene()
    for row in range(5):
        y = row * 70; off = 60 if row % 2 else 0
        for k in range(6 - (row > 2)):
            x = -330 + off + k * 120 + (row > 2) * 60
            sc.shape(spline([(x, y), (x + 115, y + 2), (x + 120, y + 40), (x + 112, y + 72), (x, y + 70), (x - 6, y + 36)], closed=True, n=5, tension=0.4))
    return sc

def watchtower():
    sc = Scene()
    for s in (-1, 1): sc.shape(band([(s * 140, 0), (s * 90, 500)], 18))
    for y in (120, 260, 400): sc.shape(band([(-140 + y * 0.1, y), (140 - y * 0.1, y)], 12))
    for (a, b) in (((-140, 0), (115, 250)), ((140, 0), (-115, 250)), ((-115, 250), (95, 480)), ((115, 250), (-95, 480))): sc.line([a, b])
    sc.shape(poly_r([(-150, 500), (150, 500), (150, 620), (-150, 620)], 4)); sc.lines(windows(-130, 130, 590, 40, 40, 60))
    sc.shape(Polygon([(-190, 620), (190, 620), (0, 720)]))
    sc.shape(band([(130, 640), (210, 690)], 6)); sc.shape(Polygon([(200, 680), (250, 700), (250, 730), (200, 720)]))
    return sc

def bugle():
    sc = Scene()
    P = spline([(-300, 0), (100, 0), (200, 60), (200, 160), (100, 200), (-200, 200), (-260, 140), (-200, 90), (100, 90)], n=14)
    sc.shape(band(P, 18, cap='round'))
    sc.shape(Polygon(spline([(100, 76), (300, 40), (420, 10), (440, 150), (300, 120), (100, 104)], n=8)))
    sc.line(ell(440, 80, 20, 70).exterior.coords[:])
    sc.shape(poly_r([(-330, -14), (-280, -14), (-280, 14), (-330, 14)], 6))
    sc.line(spline([(-100, 200), (-60, 300), (60, 310), (120, 200)], n=8))
    return sc

def side_drum():
    sc = Scene()
    sc.shape(poly_r([(-260, 0), (260, 0), (260, 300), (-260, 300)], 8))
    for y in (20, 280): sc.shape(poly_r([(-270, y - 20), (270, y - 20), (270, y + 20), (-270, y + 20)], 6))
    xs = np.linspace(-240, 240, 9)
    for k in range(len(xs) - 1): sc.line([(xs[k], 40), (xs[k + 1], 260)]); sc.line([(xs[k + 1], 40), (xs[k], 260)])
    for k in range(len(xs) - 1): sc.shape(poly_r([((xs[k] + xs[k + 1]) / 2 - 10, 230), ((xs[k] + xs[k + 1]) / 2 + 10, 230), ((xs[k] + xs[k + 1]) / 2 + 10, 255), ((xs[k] + xs[k + 1]) / 2 - 10, 255)], 4))
    for s in (-1, 1): sc.shape(band([(s * 80, 330), (s * 300, 560)], 14, cap='round'))
    return sc

def rank_set():
    sc = Scene()
    for i, n in enumerate((1, 2, 3)):
        x = -330 + i * 230
        for k in range(n):
            y = 180 + k * 50
            sc.shape(Polygon([(x - 80, y), (x, y + 80), (x + 80, y), (x + 80, y + 24), (x, y + 104), (x - 80, y + 24)]))
    for k in range(2): sc.shape(Polygon(star(-300 + k * 120, -40, 50, 20)))
    for k in range(3): sc.shape(poly_r([(-30 + k * 0, -100 + k * 50 - 60), (170, -100 + k * 50 - 60), (170, -100 + k * 50 - 30), (-30, -100 + k * 50 - 30)], 6))
    sc.shape(spline([(260, -120), (330, -40), (300, 40), (260, 70), (220, 40), (190, -40)], closed=True, n=6, tension=0.4)); sc.line([(260, -110), (262, 60)])
    return sc

def stars_row(n=4):
    sc = Scene()
    for k in range(n): sc.shape(Polygon(star(k * 260, 0, 110, 44)))
    return sc

def army_items():
    A = []
    def add(name, sc, slug):
        A.append((name, flipL(sc.render()), slug))
    add('Rhomboid tank of the First World War', tank('wwi'), 'tank-wwi')
    add('Second World War tank', tank('ww2'), 'tank-ww2')
    add('Main battle tank', tank('modern'), 'main-battle-tank')
    add('Light tank', tank('light'), 'light-tank')
    add('Tank, front view', tank_front(), 'tank-front')
    add('Eight-wheeled armoured carrier', truck('apc8'), 'armoured-carrier-8x8')
    add('Tracked armoured carrier', truck('apc_tracked'), 'tracked-carrier')
    add('Army truck with a canvas cover', truck('canvas'), 'army-truck')
    add('Military jeep', truck('jeep'), 'military-jeep')
    add('Half-track', truck('halftrack'), 'half-track')
    add('Amphibious vehicle', truck('amphibious'), 'amphibious-vehicle')
    add('Military ambulance', truck('ambulance'), 'military-ambulance')
    # bridge-layer and recovery vehicle on tank chassis
    sc = Scene(); tracks(sc, -260, 220, 0, 100, wheels=6)
    sc.shape(Polygon([(-300, 95), (260, 95), (320, 130), (300, 160), (-290, 165)]))
    sc.shape(Polygon([(-330, 170), (330, 170), (310, 230), (-310, 230)])); sc.lines([[(x, 175), (x + 30, 225)] for x in range(-300, 300, 60)])
    add('Bridge-layer', sc, 'bridge-layer')
    sc = Scene(); tracks(sc, -260, 220, 0, 100, wheels=6)
    sc.shape(Polygon([(-300, 95), (260, 95), (320, 130), (300, 160), (-290, 165)]))
    sc.shape(poly_r([(-60, 165), (120, 165), (120, 250), (-60, 250)], 10))
    sc.shape(band([(-200, 170), (-80, 400)], 20)); sc.line([(-80, 400), (-60, 250)]); sc.line([(-80, 400), (-120, 260)])
    sc.line([(-120, 260), (-130, 230), (-115, 220), (-105, 232)])
    sc.shape(Polygon([(230, 100), (340, 40), (350, 60), (250, 120)]))
    add('Armoured recovery vehicle', sc, 'recovery-vehicle')
    # aircraft
    sc = Scene(); L = 500
    sc.shape(Polygon([(80, -10), (-120, -12), (-160, -4), (-20, 0)]))
    body = spline([(-L / 2, 20), (-L * 0.2, 24), (L * 0.2, 26), (L * 0.42, 10), (L / 2, 0), (L * 0.4, -10), (L * 0.1, -22), (-L * 0.4, -20), (-L / 2, 0)], closed=True, n=8, tension=0.35)
    sc.shape(body); sc.shape(spline([(L * 0.3, 20), (L * 0.2, 46), (L * 0.04, 46), (-L * 0.02, 24)], n=8) + [(L * 0.3, 20)])
    sc.shape(Polygon([(-L * 0.36, 20), (-L * 0.46, 120), (-L * 0.5, 120), (-L * 0.5, 16)]))
    sc.shape(Polygon([(-L * 0.4, 0), (-L * 0.52, 0), (-L * 0.52, 8), (-L * 0.4, 8)]))
    sc.shape(poly_r([(L * 0.12, -20), (-L * 0.1, -20), (-L * 0.1, -2), (L * 0.12, -6)], 4))
    sc.shape(Polygon([(-L / 2 + 6, -8), (-L / 2 - 20, -10), (-L / 2 - 20, 14), (-L / 2 + 6, 12)]))
    add('Fighter jet', sc, 'fighter-jet-side')
    sc = planform(520, 50, 20, 230, 380, 170, 20, 180, 80, 60, 20, nose=0.22, canopy=(150, 40))
    add('Fighter jet from above', sc, 'fighter-jet-top')
    sc = Scene()
    sc.shape(Polygon([(0, 260), (520, -60), (480, -110), (340, -40), (240, -120), (120, -40), (0, -120), (-120, -40), (-240, -120), (-340, -40), (-480, -110), (-520, -60)]))
    sc.line(spline([(-60, 140), (0, 180), (60, 140)], n=6)); sc.lines([[(-60, 140), (60, 140)]])
    add('Flying-wing aircraft from above', sc, 'flying-wing')
    add('Military transport plane from above', planform(560, 70, 60, 120, 640, 20, 70, 260, 90, 30, 40, props=[(140, 90, 50), (260, 84, 50)], engines=[(140, 80, 70, 28), (260, 74, 70, 28)], nose=0.08, fin_top=True), 'transport-plane-top')
    sc = heli_side(430)
    add('Military utility helicopter', sc, 'military-helicopter')
    sc = Scene()
    sc.shape(airfoil(40, -10, 100, 10))
    body = spline([(-220, 20), (-60, 30), (60, 26), (110, 14), (115, -10), (60, -24), (-60, -20), (-220, 10)], closed=True, n=8, tension=0.35)
    sc.shape(body); sc.shape(spline([(20, 26), (0, 50), (-50, 48), (-70, 26)], n=6) + [(20, 26)]); sc.line([(-20, 48), (-22, 28)])
    fin(sc, -180, 18, 50, 26, 66, 26); sc.shape(ell(-200, 16, 32, 4))
    sc.shape(poly_r([(110, 20), (135, 20), (135, -18), (110, -18)], 10)); prop_side(sc, 140, 2, 44)
    gear(sc, 50, -22, -66, 11); gear(sc, -200, 10, -36, 5)
    add('Propeller fighter of the 1940s', sc, 'propeller-fighter-1940s')
    sc = planform(240, 26, 10, 50, 760, 0, 30, 140, 30, 30, 24, props=[(0, -126, 40)], nose=0.24)
    add('Reconnaissance drone from above', sc, 'recon-drone')
    add('Aircraft carrier', ship('carrier'), 'aircraft-carrier')
    add('Aircraft carrier from above', ship('carrier_top'), 'aircraft-carrier-top')
    add('Frigate', ship('frigate'), 'frigate')
    add('Submarine on the surface', ship('submarine'), 'submarine-surfaced')
    add('Patrol boat', ship('patrol'), 'patrol-boat')
    add('Landing craft', ship('landing'), 'landing-craft')
    add('Hovercraft', ship('hovercraft'), 'hovercraft')
    add('Rank insignia', rank_set(), 'rank-insignia')
    add("Sergeant's chevrons", chevrons(3, 1), 'sergeant-chevrons')
    add("General's four stars", stars_row(4), 'four-stars')
    add('Medal with a cross', medal('cross'), 'medal-cross')
    add('Star medal', medal('star'), 'medal-star')
    add('Round medal with a ribbon', medal('round'), 'medal-round')
    add('Dog tags on a chain', dog_tags(), 'dog-tags')
    add('Field cap', headgear('field_cap'), 'field-cap')
    add('Beret with a badge', headgear('beret'), 'beret')
    add('Helmet of the 1940s', headgear('ww2'), 'helmet-1940s')
    add('Modern combat helmet', headgear('modern'), 'combat-helmet')
    add('Canteen in its cover', canteen(), 'canteen')
    add('Mess tin', mess_tin(), 'mess-tin')
    add('Field radio', field_radio(), 'field-radio')
    add('Ridge tent', ridge_tent(), 'ridge-tent')
    add('Camouflage pattern', camo_panel(), 'camouflage-pattern')
    add('Sandbag wall', sandbags(), 'sandbag-wall')
    add('Watchtower', watchtower(), 'watchtower')
    add('Bugle', bugle(), 'bugle')
    add('Military side drum', side_drum(), 'side-drum')
    return A

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    items = []
    for cat, lst in (('aircraft', aircraft_items()), ('army', army_items())):
        for name, L, slug in lst:
            it = Item(cat, name, L); it.slug = slug; items.append(it)
    save(items, OUT)
    from collections import Counter
    P = sorted(export_size(i.lines)[0] for i in items)
    print(Counter(i.cat for i in items), 'median', P[len(P) // 2], 'max', P[-1])
    if SHEET:
        for i in range(0, len(items), 42):
            sheet(items[i:i + 42], SHEET.replace('.png', f'_{i // 42}.png'), cols=7, cell=2.4)
