"""Landmarks for gen_skylines.py, in local y-up coordinates (metres, centred on x = 0, base at y = 0).
Each function returns a G (gen_skylines_kit) drawn back to front."""
import math, random
import numpy as np
from gen_skylines_kit import *
TAU = 2 * math.pi

# ---------------------------------------------------------------- reusable builders
def taper_box(w0, w1, y0, y1, cx=0.0):
    return closed([(cx - w0 / 2, y0), (cx + w0 / 2, y0), (cx + w1 / 2, y1), (cx - w1 / 2, y1)])

def pod_tower(h, w0, w1, pods, mast_w=3.0, mast_to=None, flare=None, bands=()):
    """Telecom tower: a tapered shaft, pods [(y0, y1, w, shape)], a mast to `mast_to` (default h).
    shape: 'disc' (rounded drum), 'sphere', 'cone' (inverted cone under a drum), 'bulb'."""
    g = G()
    top_y = max(p[1] for p in pods) if pods else h
    g.S(taper_box(w0, w1, 0, top_y))
    if flare:                                      # flared base legs
        fw, fh = flare
        g.S(closed([(-fw / 2, 0), (fw / 2, 0)] + bez((fw / 2, 0), (w0 / 2 + 2, fh * 0.2), (w0 / 2, fh * 0.6), (w0 / 2, fh), 10)[1:] +
                   bez((-w0 / 2, fh), (-w0 / 2, fh * 0.6), (-w0 / 2 - 2, fh * 0.2), (-fw / 2, 0), 10)[1:]))
    for y in bands: g.L([(-w0 / 2 + (w0 - w1) / 2 * y / top_y, y), (w0 / 2 - (w0 - w1) / 2 * y / top_y, y)])
    for y0, y1, w, shape in pods:
        hh = y1 - y0; r = w / 2
        if shape == 'sphere':
            g.S(circ(0, (y0 + y1) / 2, hh / 2, 40))
        elif shape == 'cone':
            g.S(closed([(-w1 / 2, y0), (w1 / 2, y0), (r, y0 + hh * 0.45), (r, y1), (-r, y1), (-r, y0 + hh * 0.45)]))
            g.L([(-r, y0 + hh * 0.7), (r, y0 + hh * 0.7)])
        elif shape == 'bulb':
            right = bez((w1 / 2, y0), (r * 1.25, y0 + hh * 0.35), (r * 0.95, y0 + hh * 0.85), (r * 0.35, y1), 14)
            g.S(sym([(x, y) for x, y in right]))
            g.L([(-r * 0.98, y0 + hh * 0.45), (r * 0.98, y0 + hh * 0.45)])
        else:
            g.S(closed(earc(-r + hh * 0.3, (y0 + y1) / 2, hh * 0.3, hh / 2, PI / 2, PI * 1.5, 6) + earc(r - hh * 0.3, (y0 + y1) / 2, hh * 0.3, hh / 2, -PI / 2, PI / 2, 6)))
            g.L([(-r + 2, (y0 + y1) / 2), (r - 2, (y0 + y1) / 2)])
    mt = mast_to or h
    g.S(taper_box(mast_w, mast_w * 0.4, top_y, mt))
    return g

def wheel(R, spokes=16, cabins=24, support='A', cab=None):
    """Observation wheel standing on y = 0 (hub at y = R + clearance)."""
    g = G(); cy = R + max(6.0, R * 0.12); cab = cab or max(2.5, R * 0.06)
    if support == 'A':
        for s in (-1, 1):
            g.S(closed([(s * R * 0.62 - R * 0.03, 0), (s * R * 0.62 + R * 0.03, 0), (R * 0.025 * s, cy + 1), (-R * 0.025 * s, cy - 1)]))
    else:
        g.S(closed([(R * 0.55, 0), (R * 0.65, 0), (R * 0.06, cy + 2), (-R * 0.02, cy)]))
    ring = circ(0, cy, R, 72); inner = circ(0, cy, R * 0.93, 72)
    g.L(ring); g.L(inner)
    for k in range(spokes):
        a = TAU * k / spokes
        g.L([(R * 0.06 * math.cos(a), cy + R * 0.06 * math.sin(a)), (R * 0.93 * math.cos(a), cy + R * 0.93 * math.sin(a))])
    g.S(circ(0, cy, R * 0.07, 16))
    for k in range(cabins):
        a = TAU * k / cabins
        x, y = (R + cab * 1.1) * math.cos(a), cy + (R + cab * 1.1) * math.sin(a)
        g.S(circ(x, y, cab, 10))
    return g

def catenary(p0, p1, sag, n=24):
    return pts_arc_through(p0, p1, sag, n)

def suspension(span, side, tower_h, deck_h, style='portal', sag=None, hanger=10.0, tw=8.0):
    """Suspension bridge centred on x = 0: main span between two towers, side spans to anchorages."""
    g = G(); half = span / 2; sag = sag if sag is not None else tower_h - deck_h - 4
    x_end = half + side
    g.S(R(-x_end, deck_h - 2.5, x_end, deck_h + 2.5))
    for s in (-1, 1):
        tx_ = s * half
        if style == 'portal':
            g.S(closed([(tx_ - tw / 2, 0), (tx_ + tw / 2, 0), (tx_ + tw * 0.35, tower_h), (tx_ - tw * 0.35, tower_h)]))
            for k in range(1, 4):
                y = deck_h + (tower_h - deck_h) * k / 4
                g.L([(tx_ - tw * 0.42, y), (tx_ + tw * 0.42, y)])
        elif style == 'gothic':
            g.S(closed([(tx_ - tw / 2, 0), (tx_ + tw / 2, 0), (tx_ + tw * 0.46, tower_h), (tx_ - tw * 0.46, tower_h)]))
            for dx in (-tw * 0.22, tw * 0.22):
                g.S(arch(tx_ + dx, deck_h + 1, tw * 0.26, (tower_h - deck_h) * 0.45, 'pointed', 10, True))
            g.L([(tx_ - tw * 0.5, tower_h - 3), (tx_ + tw * 0.5, tower_h - 3)])
        elif style == 'arch':
            g.S(R(tx_ - tw / 2, 0, tx_ + tw / 2, tower_h))
            g.S(arch(tx_, deck_h, tw * 0.45, (tower_h - deck_h) * 0.5, 'round', 10, True))
            g.L([(tx_ - tw / 2, tower_h - 3), (tx_ + tw / 2, tower_h - 3)])
        g.L(catenary((s * x_end, deck_h + 2), (tx_, tower_h - 1), -(tower_h - deck_h) * 0.12 * 0 + 6, 12) if s < 0 else catenary((tx_, tower_h - 1), (s * x_end, deck_h + 2), 6, 12))
    cab = catenary((-half, tower_h - 1), (half, tower_h - 1), sag, 40)
    g.L(cab)
    for x in np.arange(-half + hanger, half - hanger / 2, hanger):
        t = (x + half) / span; y = tower_h - 1 - 4 * sag * t * (1 - t)
        if y - deck_h > 3: g.L([(x, deck_h + 2.5), (x, y)])
    return g

def minaret(h, w, style='ottoman', cx=0.0):
    g = G()
    if style == 'ottoman':                               # slender pencil with balconies and a cone
        g.S(taper_box(w, w * 0.85, 0, h * 0.84, cx))
        for f in (0.5, 0.66, 0.8):
            g.S(R(cx - w * 0.75, h * f, cx + w * 0.75, h * f + w * 0.3))
        g.S(closed([(cx - w * 0.45, h * 0.84), (cx + w * 0.45, h * 0.84), (cx, h)]))
    elif style == 'persian':                             # cylinder with a muqarnas balcony and a small dome
        g.S(taper_box(w, w * 0.9, 0, h * 0.82, cx))
        g.S(closed([(cx - w * 0.45, h * 0.78), (cx + w * 0.45, h * 0.78), (cx + w * 0.75, h * 0.83), (cx + w * 0.75, h * 0.86), (cx - w * 0.75, h * 0.86), (cx - w * 0.75, h * 0.83)]))
        g.S(R(cx - w * 0.42, h * 0.86, cx + w * 0.42, h * 0.92))
        g.S(pdome(cx, h * 0.92, w * 0.84, h * 0.08))
    elif style == 'mughal':                              # tapering with balconies and a chhatri
        g.S(taper_box(w, w * 0.8, 0, h * 0.82, cx))
        for f in (0.32, 0.58, 0.82):
            g.S(R(cx - w * 0.7, h * f, cx + w * 0.7, h * f + w * 0.22))
        g.S(R(cx - w * 0.45, h * 0.84, cx + w * 0.45, h * 0.9))
        g.L([(cx - w * 0.2, h * 0.84), (cx - w * 0.2, h * 0.9)]); g.L([(cx + w * 0.2, h * 0.84), (cx + w * 0.2, h * 0.9)])
        g.S(onion(cx, h * 0.9, w * 0.9, h * 0.1, 1.3))
    return g

def gothic_tower(w, h, spire, cx=0.0, windows=True):
    """Square gothic tower with corner pinnacles and a spire."""
    g = G()
    g.S(R(cx - w / 2, 0, cx + w / 2, h))
    if windows:
        for f in (0.45, 0.72):
            g.L(arch(cx, h * f, w * 0.3, h * 0.12, 'pointed', 8, True))
    for s in (-1, 1):
        px = cx + s * w * 0.42
        g.S(closed([(px - w * 0.08, h), (px + w * 0.08, h), (px, h + spire * 0.22)]))
    if spire: g.S(closed([(cx - w * 0.36, h), (cx + w * 0.36, h), (cx, h + spire)]))
    return g

def church_dome(w, body_h, drum_h, dome_h, lantern=0.0, cx=0.0, columns=8, dome='round'):
    """Body block, a colonnaded drum, a dome and a lantern (St Paul's, St Peter's, Capitol...)."""
    g = G()
    if body_h: g.S(R(cx - w * 0.9, 0, cx + w * 0.9, body_h))
    dw = w * 0.62
    g.S(R(cx - dw / 2, body_h, cx + dw / 2, body_h + drum_h))
    for k in range(columns):
        x = cx - dw / 2 + dw * (k + 0.5) / columns
        g.L([(x, body_h + 2), (x, body_h + drum_h - 2)])
    y0 = body_h + drum_h
    g.S(R(cx - dw * 0.47, y0, cx + dw * 0.47, y0 + drum_h * 0.18))
    y0 += drum_h * 0.18
    if dome == 'pointed': g.S(pdome(cx, y0, dw * 0.94, dome_h, 1.2))
    else: g.S(dome_shape(cx, y0, dw * 0.47, dome_h))
    for k in (-0.5, 0.0, 0.5):
        g.L([(cx + k * dw * 0.47 * 0.85, y0 + 2), (cx + k * dw * 0.1, y0 + dome_h * 0.92)]) if k else g.L([(cx, y0 + 2), (cx, y0 + dome_h * 0.95)])
    if lantern:
        ly = y0 + dome_h * 0.97
        g.S(R(cx - dw * 0.08, ly, cx + dw * 0.08, ly + lantern * 0.6))
        g.S(closed([(cx - dw * 0.08, ly + lantern * 0.6), (cx + dw * 0.08, ly + lantern * 0.6), (cx, ly + lantern)]))
    return g

def dome_shape(cx, y0, r, h):
    return closed(earc(cx, y0, r, h, 0, PI, 30))

def stepped(levels, cx=0.0):
    """A stack of boxes [(w, h), ...] from the bottom."""
    g = G(); y = 0
    for w, h in levels:
        g.S(R(cx - w / 2, y, cx + w / 2, y + h)); y += h
    return g

def tower(w, h, crown='flat', cx=0.0, taper=0.0, spire=0.0, bands=0, mullions=0):
    """A landmark skyscraper: optional taper, crown type and spire."""
    g = G(); wt = w * (1 - taper)
    if crown == 'round':
        g.S(closed([(cx - w / 2, 0), (cx + w / 2, 0), (cx + wt / 2, h - wt * 0.45)] + earc(cx, h - wt * 0.45, wt / 2, wt * 0.45, 0, PI, 16)[1:] + [(cx - wt / 2, h - wt * 0.45)]))
    elif crown == 'pyramid':
        g.S(closed([(cx - w / 2, 0), (cx + w / 2, 0), (cx + wt / 2, h * 0.8), (cx, h), (cx - wt / 2, h * 0.8)]))
    elif crown == 'slant':
        g.S(closed([(cx - w / 2, 0), (cx + w / 2, 0), (cx + wt / 2, h * 0.86), (cx - wt / 2, h)]))
    elif crown == 'notch':
        g.S(closed([(cx - w / 2, 0), (cx + w / 2, 0), (cx + wt / 2, h), (cx + wt * 0.15, h), (cx, h * 0.95), (cx - wt * 0.15, h), (cx - wt / 2, h)]))
    else:
        g.S(taper_box(w, wt, 0, h, cx))
    for k in range(1, bands + 1):
        y = h * k / (bands + 1); ww = w - (w - wt) * y / h
        g.L([(cx - ww / 2 + 1.5, y), (cx + ww / 2 - 1.5, y)])
    for k in range(1, mullions + 1):
        x = -w / 2 + w * k / (mullions + 1); xt = -wt / 2 + wt * k / (mullions + 1)
        g.L([(cx + x, 3), (cx + xt, h * 0.85)])
    if spire: g.L([(cx, h), (cx, h + spire)])
    return g

def mountain(x0, x1, ctrl, rough=6.0, seed=1, snow=None):
    g = G(); P = ridge(x0, x1, ctrl, rough=rough, seed=seed)
    g.S(P)
    if snow: g.LL(snowcap(P, snow, seed=seed))
    return g

# ---------------------------------------------------------------- landmarks
def eiffel():
    g = G()
    right = [(62, 0)] + bez((62, 0), (48, 22), (38, 42), (31, 57), 10)[1:] + [(33, 57), (33, 63), (24, 63)] + \
            bez((24, 63), (21, 80), (19, 96), (17, 112), 6)[1:] + [(19, 112), (19, 117), (13, 117)] + \
            bez((13, 117), (9, 170), (6, 230), (4, 272), 10)[1:] + [(6, 272), (6, 282), (3, 282), (3, 290), (1, 290), (1, 330), (0, 330)]
    body = sym(right)
    hole1 = [(-40, 0)] + bez((-40, 0), (-30, 30), (-10, 40), (0, 40), 8)[1:] + bez((0, 40), (10, 40), (30, 30), (40, 0), 8)[1:]
    hole2 = [(-16, 63), (16, 63), (0, 100)]
    g.S(body, holes=[closed(hole1), closed(hole2)])
    for y, w in ((57, 33), (112, 19)): g.L([(-w, y + 2.5), (w, y + 2.5)])
    g.LL(lattice(-12.5, 12.5, -4.6, 4.6, 125, 260, 6))
    g.LL(lattice(-28, 28, -21, 21, 66, 108, 2))
    return g

def arc_de_triomphe():
    g = G()
    g.S(R(-22, 0, 22, 50), holes=[arch(0, 0, 14.6, 20, 'round', 10, True)])
    g.L([(-22, 38), (22, 38)]); g.L([(-22, 44), (22, 44)])
    g.L(arch(-15, 0, 4, 10, 'round', 6)); g.L(arch(15, 0, 4, 10, 'round', 6))
    return g

def notre_dame():
    g = G()
    g.S(R(-22, 0, 22, 45))
    for s in (-1, 1):
        g.S(R(s * 13 - 7, 45, s * 13 + 7, 69))
        g.L(arch(s * 13, 52, 6, 9, 'pointed', 6, True))
    g.L(circ(0, 32, 6, 20)); g.L(R(-20, 44, 20, 46))
    for x in (-12, 0, 12): g.L(arch(x, 0, 6, 10, 'pointed', 6))
    g.S(R(-60, 0, -22, 32)); g.S(closed([(-62, 32), (-20, 32), (-41, 44)]))
    g.L([(-50, 44), (-50, 90)]); g.S(closed([(-53, 44), (-47, 44), (-50, 92)]))
    return g

def big_ben():
    g = G()
    g.S(R(-6, 0, 6, 60))
    g.S(R(-7, 60, 7, 75))
    g.L(circ(0, 67.5, 5, 24)); g.L([(0, 67.5), (0, 71)]); g.L([(0, 67.5), (2.6, 67.5)])
    g.S(R(-6, 75, 6, 82))
    for x in (-3, 0, 3): g.L(arch(x, 76, 2, 3, 'pointed', 4))
    g.S(closed([(-6.5, 82), (6.5, 82), (3, 92), (-3, 92)]))
    g.S(closed([(-3, 92), (3, 92), (0, 96)]))
    g.L([(0, 96), (0, 100)])
    for s in (-1, 1): g.L([(s * 6.5, 82), (s * 6.5, 86)])
    for k in range(1, 6): g.L([(-6, 10 * k), (6, 10 * k)])
    return g

def westminster(width=150):
    g = G()
    g.S(R(-width / 2, 0, width / 2, 24))
    for x in np.arange(-width / 2 + 6, width / 2, 12):
        g.S(closed([(x - 1.5, 24), (x + 1.5, 24), (x, 33)]))
        g.L([(x, 6), (x, 18)])
    g.S(R(width / 2 - 20, 0, width / 2, 98))
    g.S(closed([(width / 2 - 21, 98), (width / 2 + 1, 98), (width / 2 - 10, 104)]))
    for s in (-1, 1): g.S(closed([(width / 2 - 10 + s * 10, 98), (width / 2 - 10 + s * 9, 98), (width / 2 - 10 + s * 9.5, 108)]))
    g.L([(-10, 24), (-10, 58)]); g.S(closed([(-14, 24), (-6, 24), (-6, 52), (-10, 64), (-14, 52)]))
    return g

def st_pauls():
    g = church_dome(54, 30, 22, 26, lantern=16)
    for s in (-1, 1):
        g.S(R(s * 38 - 6, 30, s * 38 + 6, 56)); g.S(closed([(s * 38 - 6, 56), (s * 38 + 6, 56), (s * 38, 66)]))
    return g

def shard():
    g = G()
    g.S(closed([(-27, 0), (27, 0), (3, 290), (-3, 305)]))
    g.L([(-12, 0), (-1, 300)]); g.L([(14, 0), (2.5, 292)])
    g.L([(-4, 285), (5, 288)])
    return g

def gherkin():
    g = G()
    right = bez((15, 0), (32, 70), (25, 150), (0, 180), 18)
    g.S(sym(right))
    for k in range(-5, 6):
        g.L([(k * 5.5, 2), (k * 2.5, 175 - abs(k) * 6)])
    for y in (40, 80, 120, 150):
        ww = 0
        for (x, yy) in right:
            if yy >= y: ww = x; break
        g.L([(-ww + 1, y), (ww - 1, y)])
    return g

def tower_bridge():
    g = G()
    g.S(R(-125, 38, 125, 43))
    for s in (-1, 1):
        cx = s * 40
        g.S(R(cx - 10, 0, cx + 10, 55), holes=[arch(cx, 38, 9, 7, 'pointed', 8, True)])
        g.S(R(cx - 11, 55, cx + 11, 58))
        for dx in (-9, 9): g.S(closed([(cx + dx - 2, 58), (cx + dx + 2, 58), (cx + dx + 2, 62), (cx + dx, 68), (cx + dx - 2, 62)]))
        g.S(closed([(cx - 8, 58), (cx + 8, 58), (cx + 4, 66), (cx, 72), (cx - 4, 66)]))
        g.L(arch(cx, 44, 6, 6, 'pointed', 6))
    g.S(R(-30, 52, 30, 56)); g.S(R(-30, 47, 30, 50))
    for s in (-1, 1):
        g.L(catenary((s * 50, 52), (s * 120, 40), -6, 10))
    return g

def london_eye():
    return wheel(60, spokes=16, cabins=32, support='side', cab=3.4)

def brooklyn_bridge():
    return suspension(486, 150, 84, 40, style='gothic', hanger=14, tw=24)

def empire_state():
    g = G()
    g.S(stepped([(58, 60), (48, 180), (38, 40), (28, 30), (18, 20)]).ops[0][1])
    for (w, y0, y1) in ((48, 60, 240), (38, 240, 280), (28, 280, 310), (18, 310, 330)):
        g.S(R(-w / 2, y0, w / 2, y1))
    g.S(closed([(-9, 330), (9, 330), (6, 350), (-6, 350)]))
    g.S(closed([(-4, 350), (4, 350), (2.5, 375), (-2.5, 375)]))
    g.L([(0, 375), (0, 443)])
    for x in (-15, -5, 5, 15): g.L([(x, 66), (x, 236)])
    return g

def chrysler_like():
    g = G()
    g.S(R(-22, 0, 22, 200)); g.S(R(-16, 200, 16, 240))
    y = 240
    for k in range(5):
        w = 15 - k * 2.8
        g.S(closed([(-w, y)] + earc(0, y, w, 12 - k, PI, 0, 12)[1:] + [(w, y)]))
        y += 9 - k * 0.6
    g.S(closed([(-2, y), (2, y), (0, 319)]))
    for x in (-14, -7, 0, 7, 14): g.L([(x, 6), (x, 194)])
    return g

def one_wtc():
    g = G()
    g.S(closed([(-29, 0), (29, 0), (29, 60), (12, 417), (-12, 417), (-29, 60)]))
    g.L([(-29, 60), (12, 417)]); g.L([(29, 60), (-12, 417)])
    g.S(R(-8, 417, 8, 422)); g.L([(0, 422), (0, 541)])
    return g

def tokyo_tower():
    g = G()
    right = [(48, 0)] + bez((48, 0), (36, 40), (24, 100), (14, 150), 12)[1:] + [(18, 150), (18, 160), (11, 160)] + \
            bez((11, 160), (8, 200), (6, 230), (5, 250), 6)[1:] + [(8, 250), (8, 256), (4, 256), (2, 333), (0, 333)]
    body = sym(right)
    hole = [(-30, 0)] + bez((-30, 0), (-22, 25), (-8, 34), (0, 34), 8)[1:] + bez((0, 34), (8, 34), (22, 25), (30, 0), 8)[1:]
    g.S(body, holes=[closed(hole)])
    g.LL(lattice(-24, 24, -12, 12, 40, 140, 5))
    g.LL(lattice(-7, 7, -4, 4, 165, 245, 4))
    for y in (190, 220): g.L([(-6.5, y), (6.5, y)])
    return g

def skytree():
    g = G()
    g.S(closed([(-34, 0), (34, 0), (12, 340), (-12, 340)]))
    g.LL(lattice(-30, 30, -13, 13, 10, 330, 9))
    g.S(closed([(-12, 340), (12, 340), (18, 350), (18, 365), (-18, 365), (-18, 350)]))
    g.S(R(-9, 365, 9, 445)); g.S(closed([(-9, 445), (9, 445), (13, 450), (13, 460), (-13, 460), (-13, 450)]))
    g.S(taper_box(7, 3, 460, 634))
    return g

def mount_fuji(w=900, h=210):
    g = G()
    P = closed([(-w / 2, -20)] + bez((-w / 2, 0), (-w * 0.25, h * 0.3), (-w * 0.08, h * 0.85), (-w * 0.06, h), 16)[1:] +
               [(-w * 0.03, h * 0.98), (0, h * 1.0), (w * 0.03, h * 0.98)] +
               bez((w * 0.06, h), (w * 0.08, h * 0.85), (w * 0.25, h * 0.3), (w / 2, 0), 16)[1:] + [(w / 2, -20)])
    g.S(P)
    snow = [(-w * 0.135, h * 0.68), (-w * 0.1, h * 0.6), (-w * 0.07, h * 0.7), (-w * 0.04, h * 0.58), (0, h * 0.72), (w * 0.04, h * 0.6), (w * 0.08, h * 0.7), (w * 0.12, h * 0.62), (w * 0.14, h * 0.68)]
    g.L(snow)
    return g

def burj_khalifa():
    g = G()
    steps = [(70, 0), (62, 90), (52, 190), (44, 290), (36, 380), (28, 460), (20, 540), (14, 600)]
    right = []
    for i, (w, y) in enumerate(steps):
        y1 = steps[i + 1][1] if i + 1 < len(steps) else 640
        right += [(w / 2, y), (w / 2, y1)]
    right += [(5, 640), (2.5, 760), (0, 828)]
    g.S(sym(right))
    for (w, y) in steps[1:]: g.L([(-w / 2, y), (w / 2, y)])
    g.L([(0, 4), (0, 600)])
    return g

def burj_al_arab():
    g = G()
    sail = [(0, 0), (0, 300)] + bez((0, 300), (60, 260), (90, 150), (80, 0), 16)[1:]
    g.S(closed(sail))
    g.L(bez((6, 280), (55, 240), (75, 140), (68, 4), 14))
    g.S(R(-6, 0, 2, 321))
    g.S(closed([(2, 190), (28, 196), (28, 200), (2, 200)]))
    g.L(circ(18, 215, 10, 20))
    return g

def emirates_towers():
    g = G()
    for cx, h, w in ((-20, 355, 34), (22, 309, 30)):
        g.S(closed([(cx - w / 2, 0), (cx + w / 2, 0), (cx + w / 2, h * 0.86), (cx - w / 2, h)]))
        g.L([(cx, 4), (cx, h * 0.9)])
    return g

def dubai_frame():
    g = G()
    g.S(R(-50, 0, 50, 150), holes=[R(-38, 12, 38, 136)])
    g.L(R(-38, 12, 38, 136))
    return g

def opera_house():
    g = G()
    g.S(R(-120, 0, 110, 14))
    def shell(x0, w, h, lean=0.0):
        right = bez((x0, 14), (x0 + w * 0.15, 14 + h * 0.8), (x0 + w * 0.65 + lean, 14 + h * 1.02), (x0 + w, 14), 16)
        return closed(right)
    for (x0, w, h) in ((-110, 70, 44), (-80, 66, 60), (-50, 58, 66), (-20, 42, 50)):
        g.S(shell(x0, w, h))
        g.L(bez((x0 + w * 0.2, 16), (x0 + w * 0.3, 14 + h * 0.6), (x0 + w * 0.55, 14 + h * 0.8), (x0 + w * 0.7, 14 + h * 0.65), 10))
    for (x0, w, h) in ((20, 56, 40), (46, 50, 52), (72, 36, 34)):
        g.S(shell(x0, w, h))
    return g

def sydney_harbour_bridge():
    g = G(); span = 503 / 2
    top = [(x, 134 - 0.000 + (-134 + 95) * (x / span) ** 2) for x in np.linspace(-span, span, 41)]
    top = [(x, 95 + 39 * (1 - (x / span) ** 2)) for x in np.linspace(-span, span, 41)]
    bot = [(x, 10 + 108 * (1 - (x / span) ** 2)) for x in np.linspace(span, -span, 41)]
    g.S(closed(top + bot))
    for x in np.linspace(-span, span, 21)[1:-1]:
        g.L([(x, 10 + 108 * (1 - (x / span) ** 2)), (x, 95 + 39 * (1 - (x / span) ** 2))])
    g.S(R(-span - 120, 49, span + 120, 54))
    for x in np.linspace(-span + 30, span - 30, 12):
        yb = 10 + 108 * (1 - (x / span) ** 2)
        if yb > 56: g.L([(x, 54), (x, yb)])
    for s in (-1, 1):
        px = s * (span + 14)
        g.S(R(px - 12, 0, px + 12, 89)); g.S(R(px - 9, 89, px + 9, 95))
        g.L(R(px - 6, 60, px + 6, 80))
    return g

def sydney_tower():
    g = pod_tower(309, 8, 6, [(255, 280, 34, 'disc')], mast_w=4)
    g.S(R(-17, 280, 17, 283))
    for s in (-1, 1): g.L([(s * 4, 250), (s * 30, 0)])
    return g

def sky_tower():
    g = G()
    g.S(closed([(-18, 0), (-7, 30), (-6, 186), (6, 186), (7, 30), (18, 0)]))
    for s in (-1, 1): g.L([(s * 11, 0), (s * 6.5, 40)])
    g.S(closed([(-6, 182), (6, 182), (20, 192), (20, 214), (12, 220), (-12, 220), (-20, 214), (-20, 192)]))
    for y in (198, 206): g.L([(-20, y), (20, y)])
    g.S(closed([(-8, 220), (8, 220), (8, 232), (-8, 232)]))
    g.S(taper_box(5, 2, 232, 328))
    g.L([(-4, 260), (4, 260)])
    return g

def auckland_bridge():
    g = G(); L = 1020 / 2
    deck = [(x, 18 + 25 * max(0, 1 - abs(x) / L) ** 1.4) for x in np.linspace(-L, L, 41)]
    g.S(closed([(x, y + 3) for x, y in deck] + [(x, y) for x, y in deck[::-1]]))
    top = [(x, 43 + 18 * (1 - (x / 120) ** 2)) for x in np.linspace(-120, 120, 21)]
    base = [(x, 18 + 25 * max(0, 1 - abs(x) / L) ** 1.4 + 3) for x in np.linspace(120, -120, 21)]
    g.S(closed(top + base))
    for x in np.linspace(-108, 108, 13):
        g.L([(x, 18 + 25 * max(0, 1 - abs(x) / L) ** 1.4 + 3), (x, 43 + 18 * (1 - (x / 120) ** 2))])
    for x in np.linspace(-L + 60, L - 60, 9):
        y = 18 + 25 * max(0, 1 - abs(x) / L) ** 1.4
        g.S(taper_box(9, 6, -5, y, x))
    return g

def rangitoto(w=420, h=90):
    g = G()
    P = closed([(-w / 2, -10)] + bez((-w / 2, 0), (-w * 0.2, h * 0.55), (-w * 0.1, h), (0, h), 14)[1:] + bez((0, h), (w * 0.1, h), (w * 0.2, h * 0.55), (w / 2, 0), 14)[1:] + [(w / 2, -10)])
    g.S(P)
    g.L([(-w * 0.03, h * 0.995), (-w * 0.01, h * 1.04), (w * 0.02, h * 1.0)])
    return g

def beehive():
    g = G(); y = 0
    for k, (w, h) in enumerate(((78, 10), (74, 9), (70, 9), (66, 9), (61, 9), (55, 9), (48, 8), (40, 7), (30, 6))):
        g.S(R(-w / 2, y, w / 2, y + h))
        for x in np.arange(-w / 2 + 4, w / 2 - 2, 5): g.L([(x, y + 2), (x, y + h - 2)])
        y += h
    g.S(dome_shape(0, y, 15, 6))
    return g

def parliament_nz():
    g = G()
    g.S(R(-50, 0, 50, 26))
    for x in np.arange(-44, 46, 8): g.L([(x, 4), (x, 22)])
    g.S(R(-54, 26, 54, 30))
    g.S(R(-14, 30, 14, 36))
    return g

def cathedral_spire(w=24, h=40, spire=60, nave=50):
    g = G()
    g.S(R(-nave - w / 2, 0, -w / 2, 22)); g.S(closed([(-nave - w / 2 - 2, 22), (-w / 2, 22), (-w / 2, 32)]))
    for x in np.arange(-nave, -w / 2 - 4, 10): g.L(arch(x, 4, 4, 8, 'pointed', 6))
    g.add(gothic_tower(w, h, spire))
    return g

def cardboard_cathedral():
    g = G()
    g.S(closed([(-24, 0), (24, 0), (6, 24), (-6, 24)]))
    for k in range(1, 7):
        x = -24 + 48 * k / 7; xt = -6 + 12 * k / 7
        g.L([(x, 1), (xt, 23)])
    g.S(closed([(-6, 24), (6, 24), (0, 30)]))
    return g

def milad_tower():
    g = G()
    g.S(closed([(-60, 0), (60, 0), (60, 18), (40, 30), (-40, 30), (-60, 18)]))
    g.S(taper_box(26, 20, 30, 250))
    for y in (60, 120, 180): g.L([(-12.5 + (y - 30) / 220 * 3, y), (12.5 - (y - 30) / 220 * 3, y)])
    right = [(10, 246)] + bez((10, 246), (36, 256), (44, 272), (42, 286), 10)[1:] + bez((42, 286), (40, 300), (30, 312), (14, 318), 8)[1:] + [(0, 318)]
    g.S(sym(right))
    for y, w in ((272, 44), (290, 41.5), (303, 34)): g.L([(-w, y), (w, y)])
    g.S(closed([(-14, 318), (14, 318), (10, 326), (-10, 326)]))
    g.S(taper_box(8, 2.5, 326, 435))
    for y in (350, 380, 410): g.L([(-3, y), (3, y)])
    return g

def azadi_tower():
    g = G()
    right = [(32, 0)] + bez((32, 0), (26, 16), (20, 30), (17, 45), 10)[1:] + [(0, 45)]
    body = sym(right)
    hole = [(-12, 0)] + bez((-12, 0), (-12, 14), (-6, 22), (0, 25), 8)[1:] + bez((0, 25), (6, 22), (12, 14), (12, 0), 8)[1:]
    g.S(body, holes=[closed(hole)])
    g.L(closed([(-6, 30), (6, 30), (4, 38), (-4, 38)]))
    g.L(bez((-20, 4), (-15, 22), (-8, 30), (-4, 44), 8)); g.L(bez((20, 4), (15, 22), (8, 30), (4, 44), 8))
    g.S(R(-12, 45, 12, 49))
    return g

def alborz(w=1000, h=170, seed=4):
    g = G()
    P = ridge(-w / 2, w / 2, [(-w / 2, h * 0.35), (-w * 0.3, h * 0.6), (-w * 0.1, h * 0.5), (w * 0.08, h * 0.95), (w * 0.22, h * 0.55), (w * 0.4, h * 0.7), (w / 2, h * 0.4)], rough=10, seed=seed)
    g.S(P); g.LL(snowcap(P, h * 0.72, seed=seed, amp=7))
    return g

def shah_mosque():
    g = G()
    g.S(R(-70, 0, 70, 22))
    for x in np.arange(-62, 63, 14): g.L(arch(x, 3, 9, 10, 'persian', 6))
    g.S(R(-30, 22, 30, 56))                                    # drum and dome behind the portal
    g.S(pdome(0, 56, 58, 42, 1.32))
    g.L([(0, 98), (0, 104)])
    g.L([(-26, 50), (26, 50)])
    g.S(R(-24, 0, 24, 46)); g.L(arch(0, 0, 22, 26, 'persian', 12, True))
    g.S(R(-26, 46, 26, 49))
    for s in (-1, 1): g.add(minaret(64, 5, 'persian', cx=s * 36))
    return g

def lotfollah():
    g = G()
    g.S(R(-26, 0, 26, 24)); g.L(arch(0, 0, 14, 16, 'persian', 10, True))
    g.S(R(-20, 24, 20, 34)); g.S(pdome(0, 34, 40, 20, 1.2))
    g.L([(0, 54), (0, 58)])
    return g

def ali_qapu():
    g = G()
    g.S(R(-24, 0, 24, 30)); g.S(R(-18, 30, 18, 48))
    for x in np.arange(-16, 17, 8): g.L([(x, 30), (x, 44)])
    g.S(R(-21, 44, 21, 48)); g.S(R(-12, 48, 12, 56))
    g.L(arch(0, 0, 8, 10, 'persian', 6, True))
    return g

def si_o_se_pol(n=17, span=8.0):
    g = G(); L = n * span
    holes_lo = [arch(-L / 2 + span * (k + 0.5), 0, span * 0.62, 3.5, 'persian', 8, True) for k in range(n)]
    holes_hi = [arch(-L / 2 + span * (k + 0.5), 11, span * 0.4, 3.0, 'persian', 6, True) for k in range(n)]
    g.S(R(-L / 2, 0, L / 2, 17), holes=holes_lo + holes_hi)
    for h in holes_lo + holes_hi: g.L(h)
    g.L([(-L / 2, 10), (L / 2, 10)])
    return g

def st_basils():
    g = G()
    g.S(R(-34, 0, 34, 18))
    def drum_onion(cx, y0, w, dh, oh, stripes=True):
        gg = G()
        gg.S(R(cx - w * 0.45, y0, cx + w * 0.45, y0 + dh))
        gg.S(onion(cx, y0 + dh, w, oh, 1.6, 0.5))
        if stripes:
            for k in (-0.25, 0, 0.25): gg.L(bez((cx + k * w * 1.2, y0 + dh + 2), (cx + k * w * 1.5, y0 + dh + oh * 0.4), (cx + k * w * 0.4, y0 + dh + oh * 0.75), (cx, y0 + dh + oh * 0.97), 8))
        gg.L([(cx, y0 + dh + oh), (cx, y0 + dh + oh + 4)])
        return gg
    g.add(drum_onion(-28, 18, 11, 10, 14)); g.add(drum_onion(28, 18, 11, 10, 14))
    g.add(drum_onion(-15, 18, 13, 22, 16)); g.add(drum_onion(15, 18, 13, 22, 16))
    g.S(closed([(-7, 18), (7, 18), (5, 62), (-5, 62)]))
    g.S(closed([(-5, 62), (5, 62), (0, 82)]))
    g.S(onion(0, 80, 5, 6, 1.4)); g.L([(0, 86), (0, 90)])
    g.add(drum_onion(-6, 18, 9, 34, 11, False)); g.add(drum_onion(8, 18, 9, 30, 11, False))
    return g

def spasskaya():
    g = G()
    g.S(R(-8, 0, 8, 38)); g.L(arch(0, 0, 6, 8, 'round', 6, True))
    g.S(R(-6.5, 38, 6.5, 50)); g.L(circ(0, 44, 4.2, 18))
    g.S(R(-5, 50, 5, 56))
    g.S(closed([(-5, 56), (5, 56), (0, 72)]))
    g.L(closed([(0, 77), (1.2, 74.5), (4, 74.3), (1.8, 72.5), (2.6, 70), (0, 71.5), (-2.6, 70), (-1.8, 72.5), (-4, 74.3), (-1.2, 74.5)]))
    return g

def kremlin_wall(L=200):
    g = G(); P = [(-L / 2, 0), (-L / 2, 16)]
    for x in np.arange(-L / 2, L / 2, 6):
        P += [(x, 16), (x + 0.5, 19), (x + 1.5, 17.5), (x + 2.5, 19), (x + 3, 16), (x + 6, 16)]
    P += [(L / 2, 16), (L / 2, 0)]
    g.S(closed(P))
    return g

def msu_tower():
    g = stepped([(110, 40), (60, 40), (40, 60), (26, 30)])
    g.S(closed([(-10, 170), (10, 170), (0, 220)]))
    for s in (-1, 1): g.add(stepped([(24, 60), (14, 20)]).at(s * 70))
    return g

def hagia_sophia():
    g = G()
    g.S(R(-55, 0, 55, 30))
    for s in (-1, 1): g.S(dome_shape(s * 30, 30, 18, 12))
    g.S(R(-34, 30, 34, 40))
    for x in np.arange(-30, 31, 6): g.L(arch(x, 32, 3, 4, 'round', 4))
    g.S(dome_shape(0, 40, 32, 18))
    g.L([(0, 58), (0, 62)])
    for x in (-58, -46, 46, 58): g.add(minaret(70, 4, 'ottoman', cx=x))
    return g

def blue_mosque():
    g = G()
    g.S(R(-60, 0, 60, 22))
    for s in (-1, 1):
        g.S(dome_shape(s * 40, 22, 12, 8)); g.S(dome_shape(s * 22, 22, 14, 12))
    g.S(R(-28, 22, 28, 34))
    g.S(dome_shape(0, 34, 26, 20)); g.L([(0, 54), (0, 58)])
    for x in (-72, -60, 60, 72): g.add(minaret(64, 4, 'ottoman', cx=x))
    return g

def galata_tower():
    g = G()
    g.S(R(-9, 0, 9, 50)); g.S(R(-10, 50, 10, 54))
    for x in (-6, 0, 6): g.L(arch(x, 42, 3, 4, 'round', 4))
    g.S(closed([(-10.5, 54), (10.5, 54), (0, 67)])); g.L([(0, 67), (0, 70)])
    return g

def pyramids():
    g = G()
    for cx, b, h in ((-120, 160, 100), (40, 150, 96), (170, 70, 46)):
        g.S(closed([(cx - b / 2, 0), (cx + b / 2, 0), (cx, h)]))
        g.L([(cx, h), (cx + b * 0.12, 0)])
    return g

def cairo_tower():
    g = G()
    g.S(taper_box(12, 8, 0, 150))
    for k in range(10): g.L([(-5.5 + k * 0.1, 15 * k + 5), (5.5 - k * 0.1, 15 * k + 12)])
    g.S(closed([(-8, 150), (8, 150), (14, 158), (14, 168), (-14, 168), (-14, 158)]))
    g.S(taper_box(5, 2, 168, 187))
    return g

def mohammed_ali_mosque():
    g = G()
    g.S(R(-40, 0, 40, 20))
    for s in (-1, 1): g.S(dome_shape(s * 22, 20, 12, 9))
    g.S(R(-22, 20, 22, 30)); g.S(dome_shape(0, 30, 20, 18)); g.L([(0, 48), (0, 52)])
    for x in (-36, 36): g.add(minaret(82, 3.2, 'ottoman', cx=x))
    return g

def colosseum():
    g = G()
    P = [(-80, 0), (80, 0), (80, 44), (40, 48), (20, 40), (0, 36), (-80, 36)]
    holes = []
    for tier, (y0, h) in enumerate(((2, 9), (13, 9), (24, 8))):
        for x in np.arange(-74, 75, 10):
            top_here = 44 if x > 40 else 36 if x < 0 else 36 + (x / 40) * 8
            if y0 + h + 2 < top_here: holes.append(arch(x, y0, 6, h - 3, 'round', 6, True))
    g.S(closed(P), holes=holes)
    for y in (12, 23, 33): g.L([(-80, y), (80, y)])
    for hh in holes: g.L(hh)
    return g

def st_peters():
    g = church_dome(60, 34, 22, 30, lantern=20)
    for s in (-1, 1): g.S(dome_shape(s * 44, 34, 8, 10))
    return g

def vittoriano():
    g = G()
    g.S(R(-80, 0, 80, 20)); g.S(R(-70, 20, 70, 42))
    for x in np.arange(-64, 65, 8): g.L([(x, 22), (x, 40)])
    for s in (-1, 1): g.S(R(s * 70 - 10, 20, s * 70 + 10, 52))
    return g

def campanile():
    g = G()
    g.S(R(-6, 0, 6, 50))
    for x in (-3, 0, 3): g.L([(x, 4), (x, 46)])
    g.S(R(-6.5, 50, 6.5, 60))
    for x in (-3.5, 0, 3.5): g.L(arch(x, 51, 2.4, 5, 'round', 4))
    g.S(R(-6, 60, 6, 68))
    g.S(closed([(-6, 68), (6, 68), (0, 92)])); g.L([(0, 92), (0, 98)])
    return g

def salute():
    g = G()
    g.S(R(-30, 0, 30, 24)); g.S(closed([(-14, 24), (14, 24), (0, 34)]))
    g.S(R(-20, 24, 20, 36)); g.S(dome_shape(0, 36, 20, 18))
    g.S(R(-3, 54, 3, 60)); g.S(dome_shape(0, 60, 3, 3)); g.L([(0, 63), (0, 68)])
    g.S(R(22, 24, 34, 32)); g.S(dome_shape(28, 32, 7, 7))
    for s in (-1, 1): g.S(R(s * 26 - 2, 24, s * 26 + 2, 30))
    return g

def doges_palace(L=90):
    g = G(); h = 26
    holes = [arch(x, 0, 4, 4, 'pointed', 6, True) for x in np.arange(-L / 2 + 5, L / 2 - 2, 8)]
    holes += [arch(x, 9, 2.4, 3, 'pointed', 4, True) for x in np.arange(-L / 2 + 3, L / 2 - 1, 4)]
    g.S(R(-L / 2, 0, L / 2, h), holes=holes)
    for hh in holes: g.L(hh)
    for x in np.arange(-L / 2 + 6, L / 2, 15): g.L(R(x - 2, 17, x + 2, 22))
    return g

def leaning_tower():
    g = G()
    g.S(R(-8, 0, 8, 46))
    for k in range(6):
        y = 6 + k * 6.4
        g.L([(-8.6, y), (8.6, y)])
        for x in (-5, -1.5, 2, 5.5): g.L(arch(x, y - 5.5, 2, 3, 'round', 4))
    g.S(R(-6, 46, 6, 54))
    g = g.rot(-4, 0, 0)
    return g

def pisa_duomo():
    g = G()
    g.S(R(-45, 0, 45, 22)); g.S(closed([(-20, 22), (20, 22), (0, 34)]))
    for y in (8, 14): g.L([(-20, y), (20, y)])
    g.S(R(-10, 22, 10, 30)); g.S(dome_shape(0, 30, 10, 9))
    return g

def baptistery():
    g = G()
    g.S(R(-20, 0, 20, 24))
    for x in np.arange(-16, 17, 6.4): g.L(arch(x, 12, 3, 5, 'round', 4))
    g.S(dome_shape(0, 24, 20, 14)); g.S(R(-4, 38, 4, 44)); g.S(dome_shape(0, 44, 4, 4))
    return g

def sagrada_familia():
    g = G()
    g.S(R(-60, 0, 60, 40))
    def spire(cx, h, w):
        gg = G()
        right = [(w / 2, 0), (w / 2, h * 0.55)] + bez((w / 2, h * 0.55), (w * 0.46, h * 0.85), (w * 0.18, h * 0.97), (0, h), 10)[1:]
        gg.S(sym(right, cx))
        for y in np.arange(h * 0.2, h * 0.75, h * 0.1): gg.L([(cx - w / 2 + 1, y), (cx + w / 2 - 1, y)])
        gg.S(circ(cx, h + 2, 2, 10))
        return gg
    for cx, h, w in ((-52, 100, 11), (-38, 112, 12), (-24, 104, 11), (24, 104, 11), (38, 112, 12), (52, 100, 11)):
        g.add(spire(cx, h, w))
    g.add(spire(-8, 140, 14)); g.add(spire(8, 140, 14)); g.add(spire(0, 172, 18))
    return g

def torre_glories():
    g = G()
    right = [(18, 0), (18, 100)] + bez((18, 100), (18, 125), (12, 140), (0, 144), 12)[1:]
    g.S(sym(right))
    for y in range(12, 120, 12): g.L([(-17, y), (17, y)])
    return g

def puerta_alcala():
    g = G()
    g.S(R(-40, 0, 40, 22), holes=[arch(x, 0, 8 if x == 0 else 6, 9 if x == 0 else 7, 'round', 8, True) for x in (-24, -12, 0, 12, 24)])
    g.S(R(-12, 22, 12, 30)); g.S(closed([(-12, 30), (12, 30), (0, 35)]))
    for x in (-24, -12, 0, 12, 24): g.L(arch(x, 0, 8 if x == 0 else 6, 9 if x == 0 else 7, 'round', 8, True))
    return g

def cuatro_torres():
    g = G()
    g.add(tower(48, 250, 'flat', cx=-90, bands=0))
    g.add(tower(46, 236, 'round', cx=-30, mullions=2))
    g.S(R(16, 0, 64, 230), holes=[R(26, 205, 54, 226)])
    g.add(tower(44, 249, 'slant', cx=100))
    return g

def almudena():
    return church_dome(40, 24, 14, 22, lantern=10)

def belem_tower():
    g = G()
    g.S(R(-22, 0, 22, 12)); g.S(R(-12, 12, 12, 34))
    for x in (-8, 0, 8): g.L(arch(x, 18, 4, 6, 'round', 5))
    g.S(R(-13, 34, 13, 37))
    for x in (-10, -4, 4, 10): g.S(R(x - 1.5, 37, x + 1.5, 40))
    g.S(R(-8, 37, 8, 44))
    for s in (-1, 1): g.S(onion(s * 19, 12, 5, 6, 1.3))
    return g

def bridge_25_abril():
    return suspension(1013, 300, 190, 70, style='portal', hanger=30, tw=16)

def sao_jorge():
    g = G()
    P = ridge(-140, 140, [(-140, 0), (-60, 46), (0, 60), (70, 44), (140, 0)], rough=0, seed=2)
    g.S(P)
    P2 = [(-40, 55)]
    for x in np.arange(-40, 40, 8): P2 += [(x, 70), (x + 3, 70), (x + 3, 74), (x + 5, 74), (x + 5, 70), (x + 8, 70)]
    P2 += [(40, 55)]
    g.S(closed(P2))
    for x in (-36, 0, 32): g.S(R(x - 6, 60, x + 6, 82))
    return g

def berlin_tv():
    return pod_tower(368, 30, 9, [(200, 232, 32, 'sphere')], mast_w=4.5, bands=(60, 120))

def brandenburg_gate():
    g = G()
    holes = [R(x - 3, 0, x + 3, 16) for x in (-21, -12, 0, 12, 21)]
    g.S(R(-31, 0, 31, 21), holes=[R(x - 3.4, 0, x + 3.4, 16) for x in (-21.5, -10.75, 0, 10.75, 21.5)])
    for x in (-27, -16, -5.4, 5.4, 16, 27): g.L([(x, 0), (x, 16)])
    g.S(R(-20, 21, 20, 26))
    return g

def reichstag():
    g = G()
    g.S(R(-70, 0, 70, 30))
    for s in (-1, 1): g.S(R(s * 62 - 8, 0, s * 62 + 8, 40))
    for x in np.arange(-16, 17, 8): g.L([(x, 4), (x, 26)])
    g.S(closed([(-18, 30), (18, 30), (0, 38)]))
    g.S(dome_shape(0, 30, 20, 20))
    for k in range(-3, 4): g.L([(k * 5.5, 31), (k * 2.5, 48)])
    for y in (36, 42): g.L([(-17, y), (17, y)])
    return g

def berlin_cathedral():
    g = church_dome(46, 30, 12, 24, lantern=12)
    for s in (-1, 1):
        g.S(R(s * 38 - 6, 30, s * 38 + 6, 48)); g.S(dome_shape(s * 38, 48, 6, 8))
    return g

def canal_houses(n=9, seed=3):
    rng = random.Random(seed); g = G(); x = -n * 9 / 2
    for i in range(n):
        w = rng.uniform(7.5, 10); h = rng.uniform(16, 24); kind = (i + seed) % 3
        if kind == 0:                                           # step gable
            st, d = w * 0.14, 2.6
            right = [(x + w, 0), (x + w, h)]
            for k in range(3): right += [(x + w - k * st, h + (k + 1) * d), (x + w - (k + 1) * st, h + (k + 1) * d)]
            left = [(2 * x + w - px, py) for px, py in reversed(right[2:])]
            g.S(closed([(x, 0)] + right + left + [(x, h)]))
        elif kind == 1:                                         # bell gable
            g.S(closed([(x, 0), (x + w, 0), (x + w, h)] + earc(x + w / 2, h, w / 2, w * 0.45, 0, PI, 10)[1:] + [(x, h)]))
        else:                                                   # spout gable
            g.S(closed([(x, 0), (x + w, 0), (x + w, h), (x + w / 2, h + w * 0.6), (x, h)]))
        for yy in (h * 0.3, h * 0.55, h * 0.8):
            for xx in (x + w * 0.3, x + w * 0.7): g.L([(xx, yy - 2), (xx, yy + 2)])
        x += w + 0.3
    return g

def westerkerk():
    g = G()
    g.S(R(-8, 0, 8, 40)); g.S(R(-6, 40, 6, 52)); g.S(R(-4.5, 52, 4.5, 62)); g.S(R(-3, 62, 3, 70))
    g.S(closed([(-3, 70), (3, 70), (0, 85)])); g.L([(0, 85), (0, 88)])
    for y in (46, 57): g.L(circ(0, y, 2.2, 12))
    return g

def charles_bridge(L=260):
    g = G()
    holes = [arch(x, 0, 18, 6, 'round', 10, True) for x in np.arange(-L / 2 + 16, L / 2 - 10, 26)]
    g.S(R(-L / 2, 0, L / 2, 14), holes=holes)
    for hh in holes: g.L(hh)
    g.S(R(L / 2 - 14, 0, L / 2, 40)); g.S(closed([(L / 2 - 15, 40), (L / 2 + 1, 40), (L / 2 - 7, 56)]))
    g.L(arch(L / 2 - 7, 14, 6, 8, 'pointed', 6, True))
    return g

def st_vitus():
    g = G()
    g.S(R(-60, 0, 80, 40))
    for x in np.arange(-50, 75, 14): g.S(closed([(x - 2, 40), (x + 2, 40), (x, 48)]))
    for s in (-1, 1): g.add(gothic_tower(12, 50, 30, cx=s * 9 - 40))
    g.add(gothic_tower(16, 70, 30, cx=50))
    return g

def tyn_church():
    g = G()
    g.S(R(-16, 0, 16, 34))
    for s in (-1, 1):
        cx = s * 9
        g.S(R(cx - 6, 34, cx + 6, 50))
        g.S(closed([(cx - 7, 50), (cx + 7, 50), (cx, 80)]))
        for dx in (-5, 5): g.S(closed([(cx + dx - 1.5, 50), (cx + dx + 1.5, 50), (cx + dx, 62)]))
    return g

def st_stephens():
    g = G()
    g.S(R(-40, 0, 60, 34)); g.S(closed([(-42, 34), (62, 34), (10, 64)]))
    for k in range(6): g.L([(-30 + k * 12, 36), (-20 + k * 12, 44)])
    g.S(closed([(30, 0), (48, 0), (48, 80), (44, 100), (40, 136), (39, 136), (34, 100), (30, 80)]))
    for y in (60, 80, 100): g.L([(30 + (y - 60) * 0.05, y), (48 - (y - 60) * 0.05, y)])
    return g

def riesenrad():
    return wheel(30, spokes=12, cabins=15, support='A', cab=2.8)

def karlskirche():
    g = church_dome(30, 22, 10, 20, lantern=10)
    for s in (-1, 1):
        g.S(R(s * 26 - 3.2, 0, s * 26 + 3.2, 44))
        for y in range(8, 42, 8): g.L(bez((s * 26 - 3.2, y), (s * 26, y + 2), (s * 26, y + 2), (s * 26 + 3.2, y + 4), 6))
        g.S(R(s * 26 - 4.5, 44, s * 26 + 4.5, 47))
    return g

def budapest_parliament(L=260):
    g = G()
    g.S(R(-L / 2, 0, L / 2, 30))
    for x in np.arange(-L / 2 + 8, L / 2, 16):
        g.S(closed([(x - 2, 30), (x + 2, 30), (x, 42)]))
        g.L(arch(x, 6, 5, 10, 'pointed', 6))
    g.S(R(-22, 30, 22, 50))
    g.S(closed([(-24, 50), (24, 50)] + earc(0, 50, 24, 26, 0, PI, 20)[1:]))
    g.S(closed([(-4, 74), (4, 74), (0, 96)]))
    for s in (-1, 1):
        g.S(R(s * 40 - 5, 30, s * 40 + 5, 60)); g.S(closed([(s * 40 - 6, 60), (s * 40 + 6, 60), (s * 40, 76)]))
    return g

def chain_bridge():
    return suspension(202, 100, 48, 14, style='arch', hanger=10, tw=22)

def parthenon():
    g = G()
    hill = ridge(-160, 160, [(-160, 0), (-110, 30), (-60, 44), (60, 44), (110, 30), (160, 0)], rough=3, seed=5)
    g.S(hill)
    y0 = 42
    g.S(R(-40, y0, 40, y0 + 2.5))
    holes = [R(x - 1.6, y0 + 2.5, x + 1.6, y0 + 14) for x in np.arange(-34, 35, 6.2)]
    g.S(R(-38, y0 + 2.5, 38, y0 + 17))
    for x in np.arange(-34, 35, 6.2): g.L([(x - 1.2, y0 + 2.5), (x - 1.2, y0 + 14)]); g.L([(x + 1.2, y0 + 2.5), (x + 1.2, y0 + 14)])
    g.L([(-38, y0 + 14), (38, y0 + 14)])
    g.S(closed([(-39, y0 + 17), (39, y0 + 17), (0, y0 + 24)]))
    return g

def lycabettus():
    g = G()
    P = closed([(-90, -10)] + bez((-90, 0), (-40, 30), (-14, 90), (0, 92), 12)[1:] + bez((0, 92), (14, 90), (40, 30), (90, 0), 12)[1:] + [(90, -10)])
    g.S(P); g.S(R(-4, 90, 4, 96)); g.S(dome_shape(0, 96, 3, 3))
    return g

def taj_mahal():
    g = G()
    g.S(R(-80, 0, 80, 6))
    for x in (-74, 74): g.add(minaret(44, 4.4, 'mughal', cx=x).at(0, 6))
    g.S(R(-34, 6, 34, 34))
    g.S(R(-12, 6, 12, 40)); g.L(arch(0, 8, 14, 18, 'persian', 10, True))
    for s in (-1, 1):
        for y in (9, 22): g.L(arch(s * 24, y, 7, 6, 'persian', 6, True))
        g.S(R(s * 24 - 6, 34, s * 24 + 6, 38)); g.S(onion(s * 24, 38, 10, 9, 1.4))
        g.L([(s * 24, 47), (s * 24, 50)])
    g.S(R(-15, 34, 15, 44))
    g.S(onion(0, 44, 34, 34, 1.35, 0.5))
    g.L([(0, 78), (0, 86)])
    return g

def gateway_of_india():
    g = G()
    g.S(R(-25, 0, 25, 26), holes=[arch(0, 0, 16, 12, 'persian', 10, True)])
    g.L(arch(0, 0, 16, 12, 'persian', 10, True))
    for s in (-1, 1):
        g.S(R(s * 20 - 5, 26, s * 20 + 5, 34)); g.S(dome_shape(s * 20, 34, 5, 5))
        g.L(arch(s * 18, 4, 4, 8, 'persian', 6, True))
    g.S(R(-12, 26, 12, 30))
    return g

def taj_hotel():
    g = G()
    g.S(R(-50, 0, 50, 36))
    for y in (8, 16, 24): g.LL(window_rows(-46, 46, [y], step=6, ln=4, kind='v'))
    g.S(R(-12, 36, 12, 42)); g.S(pdome(0, 42, 24, 18, 1.3))
    for s in (-1, 1): g.S(R(s * 44 - 5, 36, s * 44 + 5, 40)); g.S(pdome(s * 44, 40, 9, 8, 1.3))
    return g

def sea_link(L=600):
    g = G()
    g.S(R(-L / 2, 18, L / 2, 21))
    for cx in (-40, 40):
        g.S(closed([(cx - 4, 0), (cx + 4, 0), (cx + 1.5, 120), (cx - 1.5, 120)]))
        for k in range(1, 8):
            y = 120 - k * 9
            g.L([(cx, y), (cx - 25 - k * 15, 21)]); g.L([(cx, y), (cx + 25 + k * 15, 21)])
    for x in np.arange(-L / 2 + 20, L / 2, 50): g.L([(x, 0), (x, 18)])
    return g

def wat_arun():
    g = G()
    g.S(R(-50, 0, 50, 8))
    def prang(cx, h, w):
        gg = G()
        right = [(w / 2, 0), (w * 0.42, h * 0.25), (w * 0.36, h * 0.3), (w * 0.3, h * 0.55), (w * 0.25, h * 0.6)] + bez((w * 0.25, h * 0.6), (w * 0.24, h * 0.8), (w * 0.12, h * 0.9), (0.02, h * 0.92), 8)[1:]
        gg.S(sym(right, cx))
        for f in (0.25, 0.42, 0.55, 0.7): gg.L([(cx - w * (0.5 - f * 0.4), h * f), (cx + w * (0.5 - f * 0.4), h * f)])
        gg.L([(cx, h * 0.92), (cx, h)])
        return gg
    for s in (-1, 1): g.add(prang(s * 34, 30, 14).at(0, 8))
    g.add(prang(0, 72, 46).at(0, 8))
    return g

def thai_roof(w=60, h=24, cx=0.0):
    g = G()
    g.S(R(cx - w * 0.4, 0, cx + w * 0.4, h * 0.45))
    for k, (ww, yy, hh) in enumerate(((w, h * 0.45, h * 0.3), (w * 0.75, h * 0.65, h * 0.3))):
        g.S(closed([(cx - ww / 2, yy), (cx + ww / 2, yy), (cx + ww * 0.1, yy + hh * 1.3), (cx - ww * 0.1, yy + hh * 1.3)]))
        for s in (-1, 1): g.L(bez((cx + s * ww / 2, yy), (cx + s * ww * 0.56, yy + 1), (cx + s * ww * 0.58, yy + 3), (cx + s * ww * 0.55, yy + 5), 5))
    g.S(closed([(cx - 4, h * 0.65 + h * 0.39), (cx + 4, h * 0.65 + h * 0.39), (cx, h * 1.5)]))
    return g

def mahanakhon():
    g = G(); rng = random.Random(7)
    right = [(16, 0)]; y = 0.0
    while y < 300:
        y2 = min(314, y + rng.uniform(14, 24)); w = 16 - (y / 314) * 4 - (rng.uniform(2, 6) if 60 < y < 290 and rng.random() < 0.6 else 0)
        right += [(w, y), (w, y2)]; y = y2
    g.S(closed([(-16, 0)] + right[1:] + [(-12, 314)]))
    for yy in range(20, 300, 20): g.L([(-15, yy), (6, yy)])
    return g

def marina_bay_sands():
    g = G()
    for cx in (-60, 0, 60):
        g.S(closed([(cx - 14, 0), (cx + 12, 0), (cx + 12, 190), (cx - 6, 190)]))
        g.L([(cx - 10, 4), (cx - 3, 188)])
    g.S(closed([(-100, 190), (95, 190), (110, 196), (-100, 196)]))
    g.L([(-96, 192), (100, 192)])
    return g

def artscience():
    g = G()
    for k, ang in enumerate((-60, -35, -10, 15, 40, 65)):
        a = math.radians(ang)
        tip = (30 * math.sin(a), 22 + 18 * math.cos(a))
        g.S(closed([(math.sin(a) * 6 - 5, 6), tip, (math.sin(a) * 6 + 5, 6)]))
    g.S(R(-12, 0, 12, 8))
    return g

def esplanade():
    g = G()
    for cx, w in ((-30, 50), (30, 40)):
        g.S(closed(earc(cx, 0, w / 2, 26 if w == 50 else 22, 0, PI, 20)))
        for k in range(-3, 4): g.L([(cx + k * w / 8, 1), (cx + k * w / 18, 24 if w == 50 else 20)])
    return g

def petronas():
    g = G()
    def one(cx):
        gg = G()
        levels = [(46, 0, 180), (40, 180, 260), (34, 260, 320), (26, 320, 355), (18, 355, 375), (10, 375, 385)]
        for w, y0, y1 in levels:
            gg.S(R(cx - w / 2, y0, cx + w / 2, y1))
            gg.L([(cx, y0 + 4), (cx, y1 - 2)])
        gg.S(closed([(cx - 4, 385), (cx + 4, 385), (cx + 1, 420), (cx - 1, 420)]))
        gg.L([(cx, 420), (cx, 452)])
        return gg
    g.add(one(-40)); g.add(one(40))
    g.S(R(-17, 170, 17, 176)); g.L([(-17, 150), (0, 170)]); g.L([(17, 150), (0, 170)])
    return g

def kl_tower():
    return pod_tower(421, 14, 10, [(276, 304, 40, 'bulb')], mast_w=4, flare=(50, 30))

def ifc2():
    g = G()
    g.S(closed([(-30, 0), (30, 0), (30, 330), (24, 350), (18, 370), (12, 388), (-12, 388), (-18, 370), (-24, 350), (-30, 330)]))
    for x in (-12, 12): g.L([(x, 4), (x, 380)])
    for s in (-1, 1): g.L([(s * 12, 388), (s * 14, 412)])
    return g

def bank_of_china():
    g = G()
    g.S(closed([(-26, 0), (26, 0), (26, 230), (12, 300), (0, 315), (-26, 250)]))
    for (y0, y1) in ((0, 80), (80, 160), (160, 240)):
        g.L([(-26, y0), (26, y1)]); g.L([(26, y0), (-26, y1)])
    g.L([(0, 315), (-2, 367)]); g.L([(4, 312), (4, 360)])
    return g

def icc():
    return tower(52, 484, 'slant', taper=0.12, mullions=3)

def victoria_peak(w=1000, h=150):
    g = G()
    P = ridge(-w / 2, w / 2, [(-w / 2, h * 0.4), (-w * 0.28, h * 0.85), (-w * 0.05, h * 0.65), (w * 0.2, h), (w * 0.38, h * 0.7), (w / 2, h * 0.45)], rough=6, seed=8)
    g.S(P); return g

def oriental_pearl():
    g = G()
    for s in (-1, 1): g.S(closed([(s * 32 - 4, 0), (s * 32 + 4, 0), (s * 3 + 2, 100), (s * 3 - 2, 100)]))
    g.S(R(-6, 0, 6, 300))
    g.S(circ(0, 92, 25, 40))
    g.L([(-25, 92), (25, 92)])
    g.S(R(-4, 120, 4, 250))
    for y in (150, 180, 210): g.S(circ(0, y, 6, 14))
    g.S(circ(0, 265, 14, 30))
    g.S(R(-4, 280, 4, 300)); g.S(circ(0, 305, 5, 14))
    g.S(taper_box(3.5, 1.5, 310, 468))
    for s in (-1, 1): g.L([(s * 24, 0), (s * 4, 76)])
    return g

def shanghai_tower():
    g = G()
    right = bez((40, 0), (37, 300), (28, 500), (19, 612), 20) + [(17, 632), (0, 632)]
    g.S(sym(right))
    g.L(bez((-30, 10), (-10, 200), (12, 420), (17, 625), 20))
    return g

def swfc():
    g = G()
    g.S(closed([(-29, 0), (29, 0), (24, 492), (-24, 492)]), holes=[closed([(-14, 448), (14, 448), (16, 476), (-16, 476)])])
    g.L(closed([(-14, 448), (14, 448), (16, 476), (-16, 476)]))
    g.L([(-29, 0), (24, 492)])
    return g

def jin_mao():
    g = G(); y = 0
    for k in range(12):
        w = 52 - k * 3.2; h = 30 - k * 1.2
        g.S(closed([(-w / 2, y), (w / 2, y), (w / 2 - 1.5, y + h), (-w / 2 + 1.5, y + h)]))
        y += h
    g.S(closed([(-8, y), (8, y), (0, y + 50)]))
    g.L([(0, y + 50), (0, 420)])
    return g

def temple_of_heaven():
    g = G()
    for k, (w, h) in enumerate(((90, 5), (76, 5), (62, 5))): g.S(R(-w / 2, k * 5, w / 2, k * 5 + h))
    y = 15
    for k, (w, h, rh) in enumerate(((40, 8, 7), (34, 6, 6), (26, 6, 9))):
        g.S(R(-w * 0.42, y, w * 0.42, y + h))
        for x in np.linspace(-w * 0.36, w * 0.36, 7): g.L([(x, y), (x, y + h)])
        y += h
        g.S(closed([(-w / 2 - 3, y), (w / 2 + 3, y), (w * 0.3, y + rh), (-w * 0.3, y + rh)]))
        y += rh
    g.S(closed([(-4, y), (4, y), (0, y + 6)])); g.S(circ(0, y + 8, 2, 10))
    return g

def cctv():
    g = G()
    P = [(-60, 0), (-30, 0), (-30, 150), (20, 150), (20, 70), (60, 70), (60, 234), (-60, 234)]
    g.S(closed([(-60, 0), (-30, 0), (-30, 165), (30, 175), (30, 80), (60, 80), (60, 234), (-60, 210)]))
    g.L([(-60, 0), (-60, 210)])
    for k in range(5): g.L([(-60, 40 * k), (-30, 40 * k + 30)])
    return g

def pagoda(h=60, tiers=7, w=24):
    g = G(); y = 0
    for k in range(tiers):
        ww = w * (1 - k * 0.07); hh = h / (tiers + 1.5)
        g.S(R(-ww * 0.32, y, ww * 0.32, y + hh * 0.6))
        g.S(closed([(-ww / 2, y + hh * 0.6), (ww / 2, y + hh * 0.6), (ww * 0.3, y + hh), (-ww * 0.3, y + hh)]))
        y += hh
    g.S(closed([(-2, y), (2, y), (0, y + h * 0.15)]))
    return g

def namsan_tower():
    g = G()
    hill = closed([(-200, -10)] + bez((-200, 0), (-110, 40), (-40, 90), (0, 92), 14)[1:] + bez((0, 92), (40, 90), (110, 40), (200, 0), 14)[1:] + [(200, -10)])
    g.S(hill)
    t = pod_tower(150, 9, 7, [(110, 124, 22, 'disc'), (126, 134, 18, 'disc')], mast_w=3, mast_to=236 - 92)
    g.add(t.at(0, 90))
    return g

def lotte_tower():
    g = G()
    right = bez((34, 0), (33, 250), (22, 450), (8, 540), 18) + [(3, 555), (0, 555)]
    g.S(sym(right))
    g.L([(0, 4), (0, 540)])
    return g

def gyeongbokgung():
    g = G()
    g.S(R(-40, 0, 40, 14))
    for x in np.arange(-34, 35, 8.5): g.L([(x, 0), (x, 12)])
    g.S(closed([(-50, 14), (50, 14), (36, 20), (-36, 20)]))
    g.S(R(-30, 20, 30, 26)); g.S(closed([(-40, 26), (40, 26), (24, 34), (-24, 34)]))
    for s in (-1, 1): g.L(bez((s * 50, 14), (s * 53, 15), (s * 54, 17), (s * 52, 19), 4))
    return g

def taipei_101():
    g = G()
    g.S(closed([(-30, 0), (30, 0), (25, 90), (-25, 90)]))
    y = 90
    for k in range(8):
        g.S(closed([(-19, y), (19, y), (24, y + 34), (-24, y + 34)]))
        y += 34
    g.S(R(-15, y, 15, y + 18)); g.S(R(-9, y + 18, 9, y + 30))
    g.S(taper_box(4, 1.5, y + 30, 508))
    for s in (-1, 1): g.L(circ(s * 22, 100, 4, 14))
    return g

def cn_tower():
    g = G()
    for s in (-1, 1): g.S(closed([(s * 30 - 5, 0), (s * 30 + 5, 0), (s * 6 + 2, 110), (s * 6 - 2, 110)]))
    g.S(taper_box(18, 10, 0, 330))
    g.S(closed([(-5, 326), (5, 326), (28, 336), (30, 352), (24, 362), (-24, 362), (-30, 352), (-28, 336)]))
    for y in (344,): g.L([(-29.5, y), (29.5, y)])
    g.S(taper_box(9, 8, 362, 447))
    g.S(closed([(-8, 444), (8, 444), (11, 450), (8, 457), (-8, 457), (-11, 450)]))
    g.S(taper_box(5, 1.5, 457, 553))
    return g

def rogers_centre():
    g = G()
    g.S(closed([(-100, 0), (100, 0), (100, 28)] + earc(0, 28, 100, 34, 0, PI, 30)[1:] + [(-100, 28)]))
    for k in range(-3, 4): g.L([(k * 26, 30 + 34 * math.sqrt(max(0, 1 - (k * 26 / 100) ** 2)) - 1), (k * 26, 28)])
    return g

def space_needle():
    g = G()
    for s in (-1, 1):
        g.L(bez((s * 22, 0), (s * 6, 60), (s * 3, 80), (s * 10, 150), 12))
        g.L(bez((s * 16, 0), (s * 3, 60), (s * 1, 80), (s * 6, 150), 12))
    g.S(R(-6, 0, 6, 150))
    for y in (60, 120): g.L([(-6, y), (6, y)])
    g.S(closed([(-10, 140), (10, 140), (34, 150), (32, 156), (-32, 156), (-34, 150)]))
    g.S(closed([(-30, 156), (30, 156), (12, 166), (-12, 166)]))
    g.S(R(-4, 166, 4, 170)); g.L([(0, 170), (0, 184)])
    return g

def rainier(w=800, h=200):
    g = G()
    P = ridge(-w / 2, w / 2, [(-w / 2, h * 0.08), (-w * 0.25, h * 0.35), (-w * 0.08, h * 0.88), (0, h), (w * 0.1, h * 0.9), (w * 0.28, h * 0.32), (w / 2, h * 0.06)], rough=4, seed=12)
    g.S(P); g.LL(snowcap(P, h * 0.6, seed=12, amp=8))
    return g

def golden_gate():
    g = suspension(1280, 343, 227, 67, style='portal', hanger=40, tw=22)
    return g

def transamerica():
    g = G()
    g.S(closed([(-27, 0), (27, 0), (3.5, 212), (0, 260), (-3.5, 212)]))
    for s in (-1, 1): g.S(closed([(s * 12, 140), (s * 18, 140), (s * 8, 190), (s * 5, 190)]))
    for y in (40, 80, 120, 160): g.L([(-27 + y * 0.11, y), (27 - y * 0.11, y)])
    return g

def coit_tower():
    g = G()
    g.S(R(-6, 0, 6, 64))
    for x in (-3, 0, 3): g.L([(x, 6), (x, 60)])
    g.S(R(-7, 58, 7, 61))
    for x in (-4.5, 0, 4.5): g.L(arch(x, 61, 2.6, 2.5, 'round', 4))
    return g

def salesforce():
    return tower(48, 326, 'round', taper=0.12, mullions=3)

def willis():
    g = G()
    for (cx, w, h) in ((-30, 20, 270), (-10, 20, 442), (10, 20, 412), (30, 20, 360), (-20, 20, 340), (20, 20, 380)):
        g.S(R(cx - w / 2, 0, cx + w / 2, h))
    g.S(R(-20, 0, 20, 442))
    for s in (-1, 1): g.L([(s * 7, 442), (s * 7, 527)])
    for k in range(1, 6): g.L([(-19, k * 70), (19, k * 70)])
    return g

def hancock():
    g = G()
    g.S(closed([(-40, 0), (40, 0), (26, 344), (-26, 344)]))
    for (y0, y1) in ((0, 86), (86, 172), (172, 258), (258, 344)):
        w0 = 40 - 14 * y0 / 344; w1 = 40 - 14 * y1 / 344
        g.L([(-w0, y0), (w1, y1)]); g.L([(w0, y0), (-w1, y1)])
        g.L([(-w1, y1), (w1, y1)])
    for s in (-1, 1): g.L([(s * 8, 344), (s * 8, 457)])
    return g

def marina_city():
    g = G()
    for cx in (-24, 24):
        g.S(R(cx - 16, 0, cx + 16, 179))
        for y in range(54, 176, 9):
            g.L(bez((cx - 16, y), (cx - 8, y - 3), (cx + 8, y - 3), (cx + 16, y), 6))
    return g

def capitol():
    g = G()
    g.S(R(-110, 0, 110, 26))
    for x in np.arange(-100, 101, 10): g.L([(x, 4), (x, 22)])
    for s in (-1, 1): g.S(closed([(s * 70 - 18, 26), (s * 70 + 18, 26), (s * 70, 32)]))
    g.S(closed([(-22, 26), (22, 26), (0, 34)]))
    g.add(church_dome(46, 34, 20, 26, lantern=18, columns=12))
    return g

def washington_monument():
    g = G()
    g.S(closed([(-8.4, 0), (8.4, 0), (5.2, 152), (0, 169), (-5.2, 152)]))
    return g

def lincoln_memorial():
    g = G()
    g.S(R(-40, 0, 40, 6)); g.S(R(-36, 6, 36, 24))
    for x in np.arange(-32, 33, 5.8): g.L([(x - 1, 6), (x - 1, 22)]); g.L([(x + 1, 6), (x + 1, 22)])
    g.S(R(-37, 24, 37, 30)); g.S(R(-30, 30, 30, 34))
    return g

def strat():
    g = G()
    for s in (-1, 1): g.S(closed([(s * 16 - 4, 0), (s * 16 + 4, 0), (s * 5 + 2, 120), (s * 5 - 2, 120)]))
    g.S(taper_box(14, 10, 0, 250))
    g.S(closed([(-6, 246), (6, 246), (22, 258), (24, 270), (20, 284), (-20, 284), (-24, 270), (-22, 258)]))
    for y in (264, 276): g.L([(-23.5, y), (23.5, y)])
    g.S(R(-12, 284, 12, 296)); g.S(taper_box(5, 2, 296, 350))
    return g

def luxor_pyramid():
    g = G(); g.S(closed([(-90, 0), (90, 0), (0, 106)]))
    for y in (26, 52, 78): g.L([(-90 + y * 0.85, y), (90 - y * 0.85, y)])
    return g

def high_roller():
    return wheel(76, spokes=14, cabins=28, support='A', cab=4)

def curved_tower(w=50, h=200, cx=0.0, bend=20):
    g = G()
    g.S(closed([(cx - w / 2, 0), (cx + w / 2, 0)] + bez((cx + w / 2, 0), (cx + w / 2 + bend, h * 0.4), (cx + w / 2 + bend, h * 0.7), (cx + w / 2 - 6, h), 12)[1:] +
               [(cx - w / 2 + 2, h)] + bez((cx - w / 2 + 2, h), (cx - w / 2 + bend * 0.7, h * 0.7), (cx - w / 2 + bend * 0.7, h * 0.4), (cx - w / 2, 0), 12)[1:]))
    for y in range(20, int(h) - 10, 22): g.L([(cx - w / 2 + bend * 0.5 * math.sin(PI * y / h) + 1, y), (cx + w / 2 + bend * math.sin(PI * y / h) * 0.9 - 2, y)])
    return g

def sugarloaf():
    g = G()
    P1 = closed([(-130, -10)] + bez((-130, 0), (-110, 140), (-60, 200), (-20, 200), 16)[1:] + bez((-20, 200), (20, 196), (40, 120), (70, 0), 16)[1:] + [(70, -10)])
    P2 = closed([(-260, -10)] + bez((-260, 0), (-240, 60), (-200, 90), (-170, 90), 10)[1:] + bez((-170, 90), (-140, 88), (-110, 50), (-90, 0), 10)[1:] + [(-90, -10)])
    g.S(P2); g.S(P1)
    g.L(catenary((-170, 92), (-30, 200), 12, 14))
    g.S(R(-108, 128 + 4, -100, 140))
    return g

def corcovado(w=500, h=240):
    g = G()
    P = ridge(-w / 2, w / 2, [(-w / 2, h * 0.2), (-w * 0.25, h * 0.5), (-w * 0.05, h * 0.92), (0, h), (w * 0.04, h * 0.9), (w * 0.2, h * 0.55), (w / 2, h * 0.25)], rough=4, seed=21)
    g.S(P); return g

def obelisco():
    g = G(); g.S(closed([(-3.5, 0), (3.5, 0), (2.6, 62), (0, 67.5), (-2.6, 62)])); g.L(R(-0.8, 54, 0.8, 57)); return g

def congreso_ba():
    return church_dome(50, 24, 14, 22, lantern=12)

def puente_mujer():
    g = G()
    g.S(R(-80, 6, 80, 9))
    g.S(closed([(-6, 9), (0, 9), (40, 74), (36, 76)]))
    for k in range(1, 8): g.L([(36 - k * 4.8, 74 - k * 8.5), (-6 - k * 9, 9)])
    return g

def torre_latino():
    g = G()
    g.S(R(-18, 0, 18, 140))
    for y0, w, h in ((140, 28, 12), (152, 20, 10), (162, 12, 6)): g.S(R(-w / 2, y0, w / 2, y0 + h))
    g.L([(0, 168), (0, 182)])
    for k in range(1, 7): g.L([(-17, k * 20), (17, k * 20)])
    return g

def bellas_artes():
    g = G()
    g.S(R(-60, 0, 60, 26))
    for x in np.arange(-50, 51, 10): g.L(arch(x, 4, 5, 10, 'round', 6))
    g.S(R(-16, 26, 16, 34)); g.S(onion(0, 34, 30, 30, 1.1, 0.6))
    for s in (-1, 1): g.S(dome_shape(s * 40, 26, 9, 9))
    return g

def popocatepetl(w=700, h=220):
    g = G()
    P = closed([(-w / 2, -10)] + bez((-w / 2, 0), (-w * 0.2, h * 0.5), (-w * 0.08, h * 0.95), (-w * 0.04, h), 12)[1:] + [(w * 0.04, h)] + bez((w * 0.04, h), (w * 0.08, h * 0.95), (w * 0.2, h * 0.5), (w / 2, 0), 12)[1:] + [(w / 2, -10)])
    g.S(P); g.LL(snowcap(P, h * 0.7, seed=31, amp=8))
    return g

def table_mountain(w=1000, h=170):
    g = G()
    P = closed([(-w / 2, -10), (-w / 2, h * 0.3)] + bez((-w / 2, h * 0.3), (-w * 0.4, h * 0.5), (-w * 0.33, h * 0.95), (-w * 0.28, h), 8)[1:] +
               [(w * 0.12, h * 1.0)] + bez((w * 0.12, h), (w * 0.18, h * 0.9), (w * 0.22, h * 0.6), (w * 0.27, h * 0.55), 8)[1:] +
               bez((w * 0.27, h * 0.55), (w * 0.33, h * 0.85), (w * 0.37, h * 0.92), (w * 0.4, h * 0.8), 8)[1:] + [(w / 2, h * 0.2), (w / 2, -10)])
    g.S(P)
    for x in np.arange(-w * 0.25, w * 0.12, 26): g.L([(x, h - 1), (x + 4, h * 0.82)])
    return g

def cape_stadium():
    g = G(); g.S(closed(earc(0, 0, 70, 30, 0, PI, 30)))
    for k in range(-4, 5): g.L([(k * 14, 1), (k * 14 * 0.92, 30 * math.sqrt(max(0, 1 - (k * 14 / 70) ** 2)) - 1)])
    return g

def kingdom_centre():
    g = G()
    right = [(32, 0), (32, 180)] + bez((32, 180), (30, 240), (22, 280), (12, 302), 12)[1:] + [(0, 302)]
    hole = [(-20, 200)] + bez((-20, 200), (-18, 250), (-10, 278), (0, 282), 10)[1:] + bez((0, 282), (10, 278), (18, 250), (20, 200), 10)[1:]
    g.S(sym(right), holes=[closed(hole)])
    g.L(closed(hole)); g.S(R(-20, 196, 20, 202))
    return g

def faisaliyah():
    g = G()
    g.S(closed([(-26, 0), (26, 0), (2, 267), (-2, 267)]))
    g.L([(-26, 0), (0, 200)]); g.L([(26, 0), (0, 200)])
    g.S(circ(0, 200, 11, 24))
    return g

def doha_tower():
    return tower(46, 238, 'round', mullions=2)

def tornado_tower():
    g = G()
    right = bez((24, 0), (16, 80), (16, 120), (26, 195), 14)
    g.S(sym(right));
    for k in range(4): g.L([(-22 + k * 2, k * 50), (22 - k * 2, k * 50 + 50)])
    return g

def burj_doha():
    g = G()
    right = [(22, 0), (22, 170)] + bez((22, 170), (21, 210), (14, 232), (4, 238), 10)[1:] + [(0, 238)]
    g.S(sym(right))
    g.L([(0, 238), (0, 252)])
    return g

def museum_islamic_art():
    g = G()
    g.S(R(-40, 0, 40, 12)); g.S(R(-26, 12, 26, 26)); g.S(R(-16, 26, 16, 38)); g.S(R(-8, 38, 8, 46))
    g.L(arch(0, 30, 6, 4, 'round', 6))
    return g

def edinburgh_castle():
    g = G()
    rock = closed([(-160, -10), (-160, 30), (-100, 70), (-40, 92), (40, 96), (100, 70), (160, 20), (160, -10)])
    g.S(rock)
    P = [(-90, 80)]
    for x in np.arange(-90, 90, 9): P += [(x, 104), (x + 4, 104), (x + 4, 108), (x + 6, 108), (x + 6, 104), (x + 9, 104)]
    P += [(90, 80)]
    g.S(closed(P))
    for x, w, h in ((-60, 22, 128), (-10, 30, 122), (40, 18, 132)): g.S(R(x - w / 2, 90, x + w / 2, h))
    g.S(closed([(20, 122), (60, 122), (40, 140)]))
    return g

def scott_monument():
    g = G()
    g.S(closed([(-10, 0), (10, 0), (8, 30), (6, 38), (4.5, 50), (2.5, 61), (0, 61), (-2.5, 61), (-4.5, 50), (-6, 38), (-8, 30)]))
    g.L(arch(0, 0, 9, 12, 'pointed', 8, True))
    for y in (30, 38, 50): g.L([(-8, y), (8, y)])
    for s in (-1, 1): g.S(closed([(s * 9 - 1.5, 30), (s * 9 + 1.5, 30), (s * 9, 42)]))
    return g

def arthurs_seat(w=500, h=110):
    g = G()
    P = ridge(-w / 2, w / 2, [(-w / 2, 0), (-w * 0.3, h * 0.4), (-w * 0.1, h * 0.85), (0, h), (w * 0.06, h * 0.82), (w * 0.2, h * 0.7), (w * 0.35, h * 0.6), (w / 2, 0)], rough=3, seed=41)
    g.S(P); return g

def vor_frelsers():
    g = G()
    g.S(R(-7, 0, 7, 50)); g.S(R(-6, 50, 6, 56))
    pts = []
    for i in range(80):
        t = i / 79; y = 56 + 34 * t; r = 6 * (1 - t) + 0.6
        pts.append((r * math.sin(TAU * 4 * t), y))
    g.S(closed([(-6, 56), (6, 56), (0.8, 90), (-0.8, 90)]))
    g.L(pts)
    g.L([(0, 90), (0, 95)])
    return g

def nyhavn_houses(n=10, seed=5):
    rng = random.Random(seed); g = G(); x = -n * 9 / 2
    for i in range(n):
        w = rng.uniform(7, 10); h = rng.uniform(14, 20)
        if i % 2: g.S(closed([(x, 0), (x + w, 0), (x + w, h), (x + w / 2, h + w * 0.55), (x, h)]))
        else: g.S(closed([(x, 0), (x + w, 0), (x + w, h), (x + w - 1.5, h + 4), (x + 1.5, h + 4), (x, h)]))
        for yy in (h * 0.35, h * 0.65):
            for xx in (x + w * 0.3, x + w * 0.7): g.L([(xx, yy - 1.6), (xx, yy + 1.6)])
        x += w + 0.4
    return g

def christiansborg():
    g = G()
    g.S(R(-40, 0, 40, 28))
    g.S(R(-6, 28, 6, 60)); g.S(R(-4, 60, 4, 70)); g.S(closed([(-4, 70), (4, 70), (0, 106)]))
    for y in (40, 52): g.L(circ(0, y, 2.6, 12))
    return g

def stockholm_city_hall():
    g = G()
    g.S(R(-60, 0, 60, 28)); g.S(closed([(-62, 28), (62, 28), (50, 36), (-50, 36)]))
    g.S(R(40, 0, 56, 96)); g.S(R(42, 96, 54, 102))
    g.S(closed([(43, 102), (53, 102), (51, 106), (48, 106 + 0), (45, 106)])); g.L([(48, 106), (48, 112)])
    for x in (44, 48, 52): g.L(circ(x, 114, 1.3, 8))
    for y in range(20, 92, 14): g.L([(44, 0 + y), (44, y + 8)]); g.L([(52, y), (52, y + 8)])
    return g

def riddarholm():
    g = G()
    g.S(R(-30, 0, 20, 26)); g.S(closed([(-32, 26), (22, 26), (-5, 36)]))
    g.S(R(12, 0, 26, 50))
    g.S(closed([(12, 50), (26, 50), (19, 90)]))
    for k in range(1, 5): g.L([(12 + k * 1.75, 50 + k * 10), (26 - k * 1.75, 50 + k * 10)])
    return g

def peter_paul():
    g = G()
    g.S(R(-40, 0, 20, 26)); g.S(R(10, 0, 30, 46)); g.S(R(13, 46, 27, 56)); g.S(R(15, 56, 25, 64))
    g.S(closed([(16, 64), (24, 64), (21, 100), (19, 100)]))
    g.L([(20, 100), (20, 122)])
    g.S(dome_shape(-25, 26, 8, 8)); g.L([(-25, 34), (-25, 40)])
    return g

def st_isaacs():
    g = church_dome(48, 34, 16, 26, lantern=14)
    for s in (-1, 1): g.S(R(s * 38 - 5, 34, s * 38 + 5, 44)); g.S(dome_shape(s * 38, 44, 5, 6))
    return g

def savior_on_blood():
    g = G()
    g.S(R(-24, 0, 24, 28))
    for cx, w, dh, oh in ((-18, 8, 8, 9), (18, 8, 8, 9), (-8, 9, 18, 10), (8, 9, 16, 10)):
        g.S(R(cx - w * 0.45, 28, cx + w * 0.45, 28 + dh)); g.S(onion(cx, 28 + dh, w, oh, 1.6, 0.5)); g.L([(cx, 28 + dh + oh), (cx, 28 + dh + oh + 3)])
    g.S(R(-5, 28, 5, 58)); g.S(closed([(-5, 58), (5, 58), (0, 74)])); g.S(onion(0, 72, 5, 6, 1.4)); g.L([(0, 78), (0, 82)])
    return g

def admiralty_spire():
    g = G(); g.S(R(-60, 0, 60, 20)); g.S(R(-10, 20, 10, 36)); g.S(R(-7, 36, 7, 46)); g.S(dome_shape(0, 46, 7, 5))
    g.S(closed([(-2, 51), (2, 51), (0, 72)])); return g

def eureka():
    g = G(); g.S(R(-22, 0, 22, 280)); g.S(R(-22, 230, 22, 280))
    g.L([(-22, 230), (22, 230)])
    g.L([(22, 280), (22, 297)])
    for x in (-11, 0, 11): g.L([(x, 4), (x, 226)])
    return g

def flinders_station():
    g = G()
    g.S(R(-80, 0, 80, 20))
    for x in np.arange(-70, 71, 14): g.L(arch(x, 4, 7, 9, 'round', 6))
    g.S(R(-12, 20, 12, 30)); g.S(dome_shape(0, 30, 12, 14))
    g.S(R(70, 0, 82, 44)); g.L(circ(76, 36, 3.6, 14)); g.S(closed([(69, 44), (83, 44), (76, 52)]))
    return g

def arts_centre_spire():
    g = G()
    g.S(R(-20, 0, 20, 18))
    g.S(closed([(-14, 18), (14, 18), (0, 162)]))
    for k in range(1, 12): g.L([(-14 + k * 1.2, 18 + k * 12), (14 - k * 1.2, 18 + k * 12)])
    g.L([(-14, 18)] + [(-14 + k * 1.2 + (2.4 if k % 2 else 0), 18 + k * 12) for k in range(1, 12)])
    return g

def oslo_opera():
    g = G()
    g.S(closed([(-90, 0), (90, 0), (90, 10), (30, 26), (20, 40), (-10, 40), (-20, 26), (-90, 6)]))
    g.L([(-20, 26), (30, 26)])
    for x in np.arange(-6, 18, 6): g.L([(x, 27), (x, 39)])
    return g

def oslo_city_hall():
    g = G()
    g.S(R(-40, 0, 40, 30))
    for s in (-1, 1): g.S(R(s * 20 - 12, 0, s * 20 + 12, 66 if s < 0 else 63))
    for s in (-1, 1):
        for y in range(10, 60, 7): g.L([(s * 20 - 8, y), (s * 20 + 8, y)])
    g.S(R(-17, 66, -3, 69))
    return g

def holmenkollen(w=500, h=120):
    g = G()
    P = ridge(-w / 2, w / 2, [(-w / 2, h * 0.2), (-w * 0.2, h * 0.5), (0, h * 0.8), (w * 0.25, h * 0.6), (w / 2, h * 0.25)], rough=4, seed=51)
    g.S(P)
    g.S(closed([(-10, h * 0.78), (-4, h * 0.78), (40, h * 1.2), (36, h * 1.24)]))
    return g

def helsinki_cathedral():
    g = G()
    g.S(R(-40, 0, 40, 22))
    for x in np.arange(-14, 15, 4.6): g.L([(x, 3), (x, 18)])
    g.S(closed([(-17, 22), (17, 22), (0, 28)]))
    g.S(R(-12, 22, 12, 40)); g.S(dome_shape(0, 40, 13, 16)); g.S(R(-2, 56, 2, 60)); g.L([(0, 60), (0, 66)])
    for s in (-1, 1):
        g.S(R(s * 30 - 4, 22, s * 30 + 4, 32)); g.S(dome_shape(s * 30, 32, 4, 5))
    return g

def uspenski():
    g = G()
    g.S(R(-26, 0, 26, 24)); g.S(closed([(-28, 24), (28, 24), (0, 34)]))
    g.S(R(-7, 24, 7, 44)); g.S(onion(0, 44, 12, 12, 1.5, 0.5)); g.L([(0, 56), (0, 62)])
    for s in (-1, 1): g.S(R(s * 16 - 3, 24, s * 16 + 3, 32)); g.S(onion(s * 16, 32, 6, 6, 1.4)); g.L([(s * 16, 38), (s * 16, 41)])
    return g
