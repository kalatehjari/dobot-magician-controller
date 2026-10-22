"""Clothing for gen_wear: front-view fashion flats (y down, centred on x = 0) and outfit flat-lays.
Each function returns a Scene."""
import math
from gen_wear_kit import *

def outline_top(nw=70, nd=0, sx=210, sy=50, cuff_out=(420, 640), cuff_in=(340, 690), arm=(250, 250), hem=(250, 700), sleeve=True, back_neck=0):
    """Closed outline of a top from its right half: back neck, shoulder, sleeve, side seam, hem."""
    half = [(0, back_neck), (nw, back_neck - 6)] + C([(nw, back_neck - 6), ((nw + sx) / 2, (back_neck + sy) / 2 - 8), (sx, sy)], n=6)[1:]
    if sleeve:
        half += C([(sx, sy), ((sx + cuff_out[0]) / 2 + 10, (sy + cuff_out[1]) / 2), cuff_out], n=8)[1:] + [cuff_in] + C([cuff_in, ((cuff_in[0] + arm[0]) / 2 + 4, (cuff_in[1] + arm[1]) / 2), arm], n=8)[1:]
    else:
        half += C([(sx, sy), (sx + 10, (sy + arm[1]) / 2), arm], n=6)[1:]
    half += C([arm, ((arm[0] + hem[0]) / 2 + 6, (arm[1] + hem[1]) / 2), hem], n=6)[1:] + [(0, hem[1])]
    return mirror_half(half)

def neckline(sc, g, nw=70, nd=70, band=16, back_neck=0, v=False):
    P = [(-nw, back_neck - 6), (0, nd), (nw, back_neck - 6)] if v else C([(-nw, back_neck - 6), (-nw * 0.6, nd * 0.75), (0, nd), (nw * 0.6, nd * 0.75), (nw, back_neck - 6)], n=8)
    sc.lines(clip([P] + ([par(P, band)] if band else []), g.buffer(1)))
    return P

def cuffs(sc, g, cuff_out, cuff_in, d=40):
    """A line across each sleeve, d above the cuff edge (towards the shoulder)."""
    for s in (-1, 1):
        a = (s * cuff_out[0], cuff_out[1]); b = (s * cuff_in[0], cuff_in[1])
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        if ny > 0: nx, ny = -nx, -ny
        ext = 0.3
        P = [(a[0] - dx * ext + nx * d, a[1] - dy * ext + ny * d), (b[0] + dx * ext + nx * d, b[1] + dy * ext + ny * d)]
        sc.lines(clip([P], g, 1))

def hem_band(sc, g, y, x=400):
    sc.lines(clip([[(-x, y), (x, y)]], g))

def buttons(sc, x, y0, y1, n, r=9):
    for k in range(n):
        y = y0 + (y1 - y0) * k / max(1, n - 1)
        sc.shape(circle(x, y, r, n=14)); sc.line(circle(x, y, r * 0.4, n=8))

def pocket(sc, x0, y0, w, h, flap=False, r=10):
    sc.shape(rect(x0, y0, w, h, r))
    if flap: sc.shape(G(J([(x0 - 4, y0 - 4), (x0 + w + 4, y0 - 4), (x0 + w + 4, y0 + h * 0.3), (x0 + w / 2, y0 + h * 0.4), (x0 - 4, y0 + h * 0.3)])))

# ---------------------------------------------------------------- tops and jackets
def hoodie():
    sc = Scene()
    sc.shape(mirror_half(C([(0, -230), (110, -215), (175, -140), (190, -40), (150, 40), (80, 60)], n=8) + [(0, 70)]))
    co, ci = (430, 690), (350, 730)
    g = G(outline_top(80, 0, 220, 70, co, ci, (255, 270), (255, 760), back_neck=20)); sc.geom(g)
    sc.line(C([(-80, 14), (-40, 60), (0, 74), (40, 60), (80, 14)], n=8))
    sc.line(C([(-150, 30), (-90, -40), (0, -70), (90, -40), (150, 30)], n=8))
    for s in (-1, 1):
        sc.line([(s * 30, 74), (s * 40, 260)]); sc.shape(rect(s * 40 - 6, 260, 12, 26, 4))
    sc.shape(G(J([(-150, 470), (150, 470)], C([(150, 470), (190, 560), (200, 650)], n=6), [(-200, 650)], C([(-200, 650), (-190, 560), (-150, 470)], n=6))))
    hem_band(sc, g, 700); cuffs(sc, g, co, ci, 45)
    return sc

def jumper():
    sc = Scene(); co, ci = (420, 680), (340, 720)
    g = G(outline_top(75, 0, 215, 60, co, ci, (250, 260), (250, 740))); sc.geom(g)
    neckline(sc, g, 75, 70, 20)
    hem_band(sc, g, 680); cuffs(sc, g, co, ci, 50)
    for s in (-1, 1): sc.lines(clip([C([(s * 215, 60), (s * 240, 160), (s * 250, 260)])], g, 0))
    for k in range(-2, 3): sc.lines(clip([[(k * 70, 690), (k * 70, 740)]], g, 2))
    return sc

def cardigan():
    sc = Scene(); co, ci = (420, 690), (340, 730)
    g = G(outline_top(80, 0, 215, 60, co, ci, (250, 260), (255, 760))); sc.geom(g)
    V_ = [(-80, -6), (0, 330), (80, -6)]
    sc.line(V_); sc.line([(-60, -6), (0, 290)]); sc.line([(60, -6), (0, 290)])
    sc.line([(0, 330), (0, 760)]); sc.line([(20, 300), (20, 760)])
    buttons(sc, 10, 360, 700, 5, 10)
    for s in (-1, 1): pocket(sc, s * 170 - 50, 520, 100, 110)
    hem_band(sc, g, 710); cuffs(sc, g, co, ci, 45)
    return sc

def blazer():
    sc = Scene(); co, ci = (410, 700), (330, 740)
    g = G(outline_top(70, 0, 230, 50, co, ci, (250, 260), (250, 780))); sc.geom(g)
    for s in (-1, 1):
        lap = G([(s * 70, -6), (s * 10, 380), (s * 40, 380), (s * 120, 200), (s * 160, 210), (s * 130, 150), (s * 100, 60)])
        sc.geom(lap)
    sc.line([(0, 380), (0, 780)])
    sc.line(C([(10, 380), (40, 600), (160, 780)]))
    sc.line(C([(-10, 380), (-40, 600), (-160, 780)]))
    buttons(sc, 20, 450, 560, 2, 11)
    for s in (-1, 1): sc.line([(s * 130, 560), (s * 220, 560)]); sc.line([(s * 130, 590), (s * 220, 590)])
    sc.line([(150, 250), (210, 250)])
    for s in (-1, 1):
        a = (s * co[0], co[1]); b = (s * ci[0], ci[1])
        for k in range(3): sc.shape(circle(a[0] + (b[0] - a[0]) * (0.3 + k * 0.15) - s * 30, a[1] + (b[1] - a[1]) * (0.3 + k * 0.15) - 40, 6, n=10))
    return sc

def trench_coat():
    sc = Scene(); co, ci = (430, 760), (350, 800)
    g = G(outline_top(70, 0, 230, 50, co, ci, (255, 260), (310, 1150))); sc.geom(g)
    for s in (-1, 1):
        sc.geom(G([(s * 70, -6), (s * 0, 300), (s * 70, 300), (s * 170, 190), (s * 210, 160), (s * 150, 110), (s * 110, 40)]))
        sc.geom(G([(s * 130, 40), (s * 230, 50), (s * 225, 85), (s * 130, 75)]))
    sc.line([(30, 300), (60, 1150)])
    for (x, y) in ((-60, 360), (60, 360), (-60, 450), (60, 450), (-60, 540), (60, 540)): sc.shape(circle(x, y, 11, n=14))
    sc.geom(G([(-270, 560), (270, 560), (272, 610), (-272, 610)]))
    sc.shape(rect(-40, 552, 80, 66, 8)); sc.line([(0, 552), (0, 618)])
    sc.line(C([(-30, 620), (-60, 700), (-50, 760)]))
    for s in (-1, 1): sc.line([(s * 140, 660), (s * 200, 820)])
    return sc

def puffer_jacket():
    sc = Scene(); co, ci = (440, 680), (350, 730)
    g = G(outline_top(90, 0, 230, 70, co, ci, (270, 260), (275, 740), back_neck=-20)); sc.geom(g)
    sc.geom(G(J(C([(-100, -26), (-110, 60), (0, 80), (110, 60), (100, -26)], n=8), [(100, -60), (-100, -60)])))
    sc.line([(0, 70), (0, 740)])
    for y in range(160, 720, 100): sc.lines(clip([C([(-460, y + 30), (-250, y), (0, y + 10), (250, y), (460, y + 30)], n=8)], g, 1))
    for s in (-1, 1): sc.line([(s * 150, 470), (s * 190, 600)])
    cuffs(sc, g, co, ci, 30)
    return sc

def denim_jacket():
    sc = Scene(); co, ci = (420, 660), (345, 700)
    g = G(outline_top(70, 0, 215, 50, co, ci, (250, 250), (250, 640))); sc.geom(g)
    for s in (-1, 1):
        sc.geom(G([(s * 70, -6), (s * 10, 60), (s * 60, 120), (s * 140, 70), (s * 120, 20)]))
        sc.line(C([(s * 20, 200), (s * 120, 180), (s * 230, 200)], n=6))
        pocket(sc, s * 140 - 50, 230, 100, 100, flap=True)
        sc.lines(clip([[(s * 100, 330), (s * 120, 590)]], g))
    sc.line([(0, 60), (0, 640)])
    buttons(sc, 15, 120, 520, 5, 10)
    sc.geom(G([(-250, 580), (250, 580), (250, 640), (-250, 640)]))
    for s in (-1, 1): buttons(sc, s * 200, 610, 610, 1, 8)
    cuffs(sc, g, co, ci, 40)
    return sc

def raincoat():
    sc = Scene(); co, ci = (430, 760), (350, 800)
    sc.shape(mirror_half(C([(0, -260), (120, -240), (190, -160), (200, -40), (150, 40), (90, 60)], n=8) + [(0, 60)]))
    g = G(outline_top(90, 0, 230, 60, co, ci, (260, 260), (300, 1020), back_neck=20)); sc.geom(g)
    sc.line(C([(-150, 30), (-90, -60), (0, -90), (90, -60), (150, 30)], n=8))
    sc.line([(0, 60), (0, 1020)]); sc.line([(24, 60), (24, 1020)])
    for y in range(160, 960, 120): sc.shape(rect(-14, y, 52, 18, 6))
    for s in (-1, 1): pocket(sc, s * 170 - 60, 560, 120, 140, flap=True)
    cuffs(sc, g, co, ci, 30)
    return sc

def poncho():
    sc = Scene()
    g = G([(0, -20), (500, 380), (0, 760), (-500, 380)]); sc.geom(g)
    sc.line(circle(0, 30, 70, n=36)); sc.line(circle(0, 30, 90, n=36))
    for t in range(1, 40):
        f = t / 40
        for P in ([(500 * f, 380 + 380 * f), (500 * f - 8, 380 + 380 * f + 50)], [(-500 * f, 380 + 380 * f), (-500 * f + 8, 380 + 380 * f + 50)]): sc.line(P)
    for k in (1, 2, 3):
        sc.lines(clip([[(-500, 380 + k * 70), (0, 760 + k * 0 - 0), (500, 380 + k * 70)]], g.buffer(-10)))
    return sc

def polo_shirt():
    sc = Scene(); co, ci = (380, 300), (320, 360)
    g = G(outline_top(70, 0, 215, 50, co, ci, (245, 250), (245, 720))); sc.geom(g)
    for s in (-1, 1): sc.geom(G([(s * 70, -6), (s * 4, 40), (s * 70, 140), (s * 150, 90), (s * 110, 10)]))
    sc.shape(rect(-22, 40, 44, 200, 6)); buttons(sc, 0, 80, 200, 3, 7)
    cuffs(sc, g, co, ci, 30)
    return sc

def tank_top():
    sc = Scene()
    half = [(0, 0), (90, -10)] + C([(90, -10), (130, -20), (160, -16)], n=4)[1:] + C([(160, -16), (180, 120), (230, 240), (240, 300)], n=8)[1:] + C([(240, 300), (250, 500), (240, 700)], n=6)[1:] + [(0, 700)]
    g = G(mirror_half(half)); sc.geom(g)
    sc.line(C([(-90, -10), (-50, 120), (0, 150), (50, 120), (90, -10)], n=8))
    for s in (-1, 1): sc.line(par(C([(s * 160, -16), (s * 180, 120), (s * 230, 240), (s * 240, 300)], n=8), 14 * s))
    return sc

# ---------------------------------------------------------------- dresses and skirts
def dress(kind):
    sc = Scene()
    if kind == 'a-line':
        half = [(0, 0), (70, -6), (130, 0), (180, 160), (170, 260)] + C([(170, 260), (190, 380), (230, 560), (330, 900)], n=8)[1:] + [(0, 920)]
        g = G(mirror_half(half)); sc.geom(g)
        neckline(sc, g, 70, 80, 0); sc.line([(-170, 260), (170, 260)])
        for x in (-140, -50, 50, 140): sc.lines(clip([[(x * 0.6, 270), (x * 1.6, 910)]], g))
    elif kind == 'wrap':
        half = [(0, 0), (80, -6), (190, 30), (330, 260), (280, 300), (190, 220), (185, 300), (180, 390)] + C([(180, 390), (230, 600), (300, 940)], n=8)[1:] + [(0, 960)]
        g = G(mirror_half(half)); sc.geom(g)
        sc.line([(-80, -6), (60, 380)]); sc.line([(80, -6), (-30, 300)])
        sc.line([(-180, 390), (180, 390)])
        sc.geom(G([(150, 380), (210, 380), (240, 560), (200, 580)]))
        sc.line(C([(60, 400), (120, 640), (200, 950)]))
    elif kind == 'maxi':
        half = [(0, 40), (60, 30), (100, -60), (110, -60), (110, 40), (190, 120), (200, 300)] + C([(200, 300), (260, 700), (340, 1320)], n=8)[1:] + [(0, 1340)]
        g = G(mirror_half(half)); sc.geom(g)
        sc.line([(-200, 300), (200, 300)])
        for x in (-200, -100, 0, 100, 200): sc.lines(clip([C([(x * 0.6, 310), (x * 0.9 + 20, 800), (x * 1.5, 1330)])], g))
        sc.line(C([(-110, 40), (0, 120), (110, 40)]))
    else:   # sundress
        half = [(0, 70), (80, 40), (120, -40), (130, -40), (140, 60), (200, 140), (200, 260)] + C([(200, 260), (280, 480), (380, 760)], n=8)[1:] + [(0, 780)]
        g = G(mirror_half(half)); sc.geom(g)
        sc.line(C([(-140, 60), (-70, 120), (0, 80), (70, 120), (140, 60)], n=8))
        sc.line([(-200, 260), (200, 260)])
        for k in range(-4, 5): sc.lines(clip([C([(k * 40, 270), (k * 60, 500), (k * 84, 770)])], g, 2))
        bow(sc, 0, 250)
    return sc

def bow(sc, x, y, s=1.0):
    for f in (-1, 1):
        sc.shape(CC([(x, y), (x + f * 50 * s, y - 30 * s), (x + f * 60 * s, y + 20 * s), (x + f * 10 * s, y + 6 * s)], n=6))
        sc.shape(G([(x + f * 6 * s, y + 6 * s), (x + f * 30 * s, y + 70 * s), (x + f * 44 * s, y + 60 * s), (x + f * 14 * s, y)]))
    sc.shape(circle(x, y + 2, 12 * s, n=12))

def skirt(kind):
    sc = Scene()
    if kind == 'pleated':
        g = G([(-200, 0), (200, 0), (380, 600), (-380, 600)]); sc.geom(g)
        sc.geom(G([(-205, 0), (205, 0), (210, 60), (-210, 60)]))
        for k in range(-7, 8):
            sc.lines(clip([[(k * 26, 60), (k * 50, 600)]], g))
        sc.line(C([(-380, 600), (-290, 610), (-200, 600), (-100, 610), (0, 600), (100, 610), (200, 600), (290, 610), (380, 600)], n=4))
    else:  # pencil
        half = [(0, 0), (200, 0)] + C([(200, 0), (240, 200), (230, 500), (200, 760)], n=8)[1:] + [(0, 760)]
        g = G(mirror_half(half)); sc.geom(g)
        sc.line([(-210, 60), (210, 60)])
        sc.line([(0, 600), (0, 760)])
        for s in (-1, 1): sc.line([(s * 110, 60), (s * 115, 260)])
    return sc

# ---------------------------------------------------------------- trousers
def trousers(kind):
    sc = Scene()
    W, L, rise = 220, 1050, 300
    hem_out = {'jeans': 200, 'cargo': 210, 'chinos': 190}[kind]
    half = [(0, 0), (W, 0)] + C([(W, 0), (W + 20, 200), (W + 5, 500), (hem_out + 10, L)], n=8)[1:] + [(36, L)] + C([(36, L), (30, 700), (0, rise)], n=8)[1:]
    g = G(mirror_half(half)); sc.geom(g)
    sc.line([(-W - 2, 60), (W + 2, 60)])
    for x in (-180, -60, 60, 180): sc.shape(rect(x - 8, -4, 16, 72, 3))
    sc.shape(circle(0, 30, 10, n=12))
    sc.line(C([(0, 60), (40, 70), (50, 200), (20, 260)]))
    for s in (-1, 1):
        sc.line(C([(s * 110, 60), (s * 140, 130), (s * W, 160)], n=6))
        if kind == 'jeans':
            sc.lines(clip([par(C([(s * 110, 60), (s * 140, 130), (s * W, 160)], n=6), 14 * s)], g))
        if kind == 'cargo':
            pocket(sc, s * (W - 10) - 70, 520, 140, 170, flap=True)
        sc.line([(s * (hem_out - 70), L - 40), (s * (hem_out + 8), L - 40)]) if kind != 'chinos' else None
    return sc

def dungarees():
    sc = Scene()
    sc.geom(G(J([(-150, 0), (150, 0)], [(160, 330), (-160, 330)])))
    for s in (-1, 1):
        sc.geom(LineString([(s * 120, 10), (s * 170, -260)]).buffer(22, cap_style=2))
        sc.shape(rect(s * 118 - 26, 0, 52, 40, 6)); sc.shape(circle(s * 118, 20, 9, n=12))
    sc.shape(rect(-90, 80, 180, 140, 10)); sc.line([(0, 80), (0, 220)])
    W, L = 240, 1100
    half = [(0, 330), (W, 330)] + C([(W, 330), (W + 15, 600), (W - 10, L)], n=8)[1:] + [(W - 190, L)] + C([(W - 190, L), (40, 800), (0, 620)], n=8)[1:]
    g = G(mirror_half(half)); sc.geom(g)
    for s in (-1, 1): sc.line(C([(s * 100, 340), (s * 150, 420), (s * W, 440)], n=6))
    sc.line([(-W, 1060), (W, 1060)])
    return sc

def jumpsuit():
    sc = Scene()
    co, ci = (330, 300), (270, 350)
    top = outline_top(70, 0, 200, 50, co, ci, (230, 250), (235, 480))
    sc.geom(G(top))
    half = [(0, 470), (240, 470)] + C([(240, 470), (260, 700), (250, 1000), (240, 1300)], n=8)[1:] + [(50, 1300)] + C([(50, 1300), (40, 1000), (0, 760)], n=8)[1:]
    g = G(mirror_half(half)); sc.geom(g)
    sc.geom(G([(-245, 460), (245, 460), (245, 510), (-245, 510)]))
    sc.line(C([(-70, -6), (0, 160), (70, -6)], n=6)); sc.line([(0, 160), (0, 460)])
    buttons(sc, 0, 220, 420, 3, 8)
    return sc

def two_piece_suit():
    sc = s_scale(blazer(), 0.9)
    tr = s_move(s_scale(trousers('chinos'), 0.82), 700, 80)
    return s_join(tr, sc)

def waistcoat():
    sc = Scene()
    half = [(0, 0), (110, -10), (180, 20)] + C([(180, 20), (210, 140), (230, 300)], n=6)[1:] + C([(230, 300), (240, 500), (230, 640)], n=6)[1:] + [(80, 700), (0, 650)]
    g = G(mirror_half(half)); sc.geom(g)
    sc.line([(-110, -10), (0, 350), (110, -10)])
    sc.line([(0, 350), (0, 650)])
    buttons(sc, 10, 380, 610, 4, 9)
    for s in (-1, 1): sc.line([(s * 100, 470), (s * 190, 460)]); sc.line([(s * 120, 200), (s * 190, 195)])
    return sc

def kimono():
    sc = Scene()
    half = [(0, 0), (90, -10), (260, 30), (560, 40), (580, 420), (300, 440), (280, 460)] + C([(280, 460), (290, 800), (300, 1150)], n=6)[1:] + [(0, 1150)]
    g = G(mirror_half(half)); sc.geom(g)
    sc.line([(-90, -10), (60, 560)]); sc.line([(90, -10), (-30, 470)])
    sc.line([(60, 560), (100, 1150)])
    sc.geom(G([(-290, 470), (290, 470), (292, 620), (-292, 620)]))
    sc.line([(-290, 545), (290, 545)])
    for s in (-1, 1): sc.line([(s * 280, 40), (s * 280, 440)])
    return sc

def apron():
    sc = Scene()
    g = G(J([(-150, 0), (150, 0)], C([(150, 0), (170, 200), (260, 280)], n=6), [(280, 900), (-280, 900)], C([(-260, 280), (-170, 200), (-150, 0)], n=6))); sc.geom(g)
    sc.line(C([(-150, 0), (-80, -200), (0, -260), (80, -200), (150, 0)], n=8))
    for s in (-1, 1): sc.line(C([(s * 260, 290), (s * 380, 320), (s * 420, 420), (s * 400, 520)], n=8))
    pocket(sc, -150, 450, 300, 180)
    sc.line([(0, 450), (0, 630)])
    return sc

def pyjamas():
    co, ci = (400, 640), (330, 680)
    top = Scene(); g = G(outline_top(70, 0, 210, 50, co, ci, (240, 250), (245, 700))); top.geom(g)
    for s in (-1, 1): top.geom(G([(s * 70, -6), (s * 6, 110), (s * 60, 160), (s * 150, 90), (s * 110, 10)]))
    top.line([(0, 110), (0, 700)]); buttons(top, 10, 180, 620, 5, 8)
    top.lines(clip([par(outline_top(70, 0, 210, 50, co, ci, (240, 250), (245, 700)), -16)], g, 2))
    pocket(top, -170, 230, 90, 90)
    bot = Scene()
    W, L = 220, 950
    half = [(0, 0), (W, 0)] + C([(W, 0), (W + 25, 400), (W + 40, L)], n=8)[1:] + [(W - 160, L)] + C([(W - 160, L), (30, 500), (0, 300)], n=8)[1:]
    gb = G(mirror_half(half)); bot.geom(gb); bot.line([(-W, 50), (W, 50)])
    for s in (-1, 1): bot.line([(s * 30, 0), (s * 40, 140)])
    return s_join(s_move(bot, 560, 80), top)

def bathrobe():
    sc = Scene(); co, ci = (430, 760), (340, 800)
    g = G(outline_top(80, 0, 230, 60, co, ci, (260, 270), (290, 1100))); sc.geom(g)
    for sg in (-1, 1): sc.geom(LineString(C([(sg * 95, -6), (sg * 80, 200), (0, 430)], n=8)).buffer(34, cap_style=2))
    sc.line([(0, 420), (60, 1100)])
    sc.geom(G([(-270, 540), (270, 540), (272, 590), (-272, 590)]))
    for x, d in ((-30, -1), (30, 1)): sc.geom(LineString(C([(x, 590), (x + d * 40, 760), (x + d * 30, 880)])).buffer(18, cap_style=2))
    for s in (-1, 1): pocket(sc, s * 180 - 60, 640, 120, 140)
    cuffs(sc, g, co, ci, 60)
    return sc

def scarf():
    sc = Scene()
    P = C([(0, 0), (60, 200), (20, 420), (80, 640), (40, 860)], n=10)
    g = LineString(P).buffer(80, cap_style=2); sc.geom(g)
    for y in range(40, 860, 60): sc.lines(clip([[(-200, y), (300, y + 10)]], g, 2))
    for k in range(-3, 4):
        x = 40 + k * 22; sc.line([(x, 860), (x + 4, 960)]); x0 = k * 22; sc.line([(x0, 0), (x0 - 4, -100)])
    return sc

def gloves():
    def glove(cx, flip=1):
        sc = Scene()
        palm = CC([(0, 0), (150, -10), (190, -200), (200, -380), (120, -430), (0, -420), (-60, -360), (-60, -200), (-40, -20)], n=8)
        g = G(palm)
        fingers = [(-40, -380, 70, 230, -0.08), (35, -420, 70, 270, -0.02), (110, -410, 66, 250, 0.04), (175, -360, 60, 200, 0.12)]
        shapes = [g]
        for x, y, w, l, a in fingers:
            P = [(x - w / 2, y + 30), (x - w / 2 + math.sin(a) * -l, y - l), (x + w / 2 + math.sin(a) * -l, y - l), (x + w / 2, y + 30)]
            shapes.append(LineString([(x, y + 20), (x - math.sin(a) * l, y - l + w / 2)]).buffer(w / 2, cap_style=1))
        shapes.append(LineString([(-50, -200), (-180, -330)]).buffer(36, cap_style=1))
        hand = unary_union(shapes)
        sc.geom(hand)
        sc.geom(G([(-50, 0), (160, -10), (180, 140), (-60, 150)]))
        sc.lines(clip([[(-80, 40), (200, 30)], [(-80, 80), (200, 70)], [(-80, 120), (200, 110)]], G([(-50, 0), (160, -10), (180, 140), (-60, 150)]), 3))
        return s_move(s_mirror(sc, 0) if flip < 0 else sc, cx, 0)
    return s_join(glove(-260, -1), glove(260, 1))

def belt():
    sc = Scene()
    strap = LineString(C([(-500, 40), (-200, 0), (200, 10), (520, 60)])).buffer(30, cap_style=2); sc.geom(strap)
    for x in range(160, 480, 60): sc.shape(circle(x, 30 + (x - 160) * 0.12, 8, n=10))
    buck = G([(-560, -20), (-460, -20), (-460, 110), (-560, 110)], [[(-545, -5), (-475, -5), (-475, 95), (-545, 95)]]); sc.geom(buck)
    sc.line([(-560, 45), (-470, 45)])
    sc.lines(clip([dashes(C([(-450, 20), (-200, -18), (200, -8), (500, 40)]), 14, 10)[i] for i in range(0)], strap))
    return sc

def onesie():
    sc = Scene(); co, ci = (330, 300), (270, 350)
    top = outline_top(60, 0, 180, 40, co, ci, (200, 230), (200, 460)); sc.geom(G(top))
    half = [(0, 450), (200, 450)] + C([(200, 450), (230, 560), (220, 700)], n=6)[1:] + [(60, 700)] + C([(60, 700), (40, 640), (0, 620)], n=6)[1:]
    sc.geom(G(mirror_half(half)))
    sc.line(C([(-60, -6), (0, 60), (60, -6)], n=6))
    buttons(sc, 0, 640, 640, 1, 9); buttons(sc, -40, 650, 650, 1, 9); buttons(sc, 40, 650, 650, 1, 9)
    return sc

# ---------------------------------------------------------------- outfit flat-lays
def tshirt():
    sc = Scene(); co, ci = (380, 300), (320, 360)
    g = G(outline_top(70, 0, 215, 50, co, ci, (245, 250), (245, 720))); sc.geom(g)
    neckline(sc, g, 70, 70, 16); cuffs(sc, g, co, ci, 26)
    return sc

def cap():
    sc = Scene()
    sc.geom(G(J(C([(-200, 0), (-190, -150), (-90, -240), (0, -255), (90, -240), (190, -150), (200, 0)], n=8), [(-200, 0)])))
    sc.geom(G(J(C([(-210, -10), (-100, 60), (100, 60), (210, -10)], n=8), C([(210, -10), (100, 10), (-100, 10), (-210, -10)], n=8))))
    for x in (-110, 0, 110): sc.line(C([(x * 0.1, -255), (x * 0.6, -150), (x, 0)]))
    sc.shape(circle(0, -255, 14, n=12))
    return sc

def sneaker_top():
    import gen_wear_shoes2 as S2
    return s_flip(s_scale(S2.shoe_top(0, False), 0.55))

def heel_side():
    import gen_wear_shoes2 as S2
    return s_flip(s_scale(S2.pump(300), 0.45))

def handbag():
    sc = Scene()
    sc.geom(G(J([(-200, 0), (200, 0)], C([(200, 0), (240, 150), (250, 300)], n=6), [(-250, 300)], C([(-250, 300), (-240, 150), (-200, 0)], n=6))))
    sc.line(C([(-120, 0), (-100, -150), (0, -200), (100, -150), (120, 0)], n=8)); sc.line(C([(-90, 0), (-75, -125), (0, -165), (75, -125), (90, 0)], n=8))
    sc.line([(-210, 70), (210, 70)]); sc.shape(rect(-24, 60, 48, 40, 6))
    return sc

def watch():
    sc = Scene()
    sc.geom(LineString([(0, -260), (0, 260)]).buffer(40, cap_style=2))
    sc.shape(circle(0, 0, 90, n=40)); sc.line(circle(0, 0, 72, n=36))
    sc.line([(0, 0), (0, -50)]); sc.line([(0, 0), (34, 10)])
    for k in range(12):
        a = TAU * k / 12; sc.line([(62 * math.cos(a), 62 * math.sin(a)), (70 * math.cos(a), 70 * math.sin(a))])
    return sc

def outfit(kind):
    if kind == 'casual':
        return s_join(s_move(s_scale(trousers('jeans'), 0.6), 330, 120), s_move(s_scale(tshirt(), 0.62), -170, 0),
                      s_move(sneaker_top(), 520, 520), s_move(s_scale(cap(), 0.6), -280, 640))
    if kind == 'smart':
        shirt = Scene(); co, ci = (400, 640), (330, 680)
        g = G(outline_top(70, 0, 210, 50, co, ci, (240, 250), (245, 720))); shirt.geom(g)
        for s in (-1, 1): shirt.geom(G([(s * 70, -6), (s * 6, 60), (s * 70, 130), (s * 130, 70), (s * 100, 10)]))
        shirt.line([(0, 60), (0, 720)]); buttons(shirt, 10, 120, 640, 6, 7); cuffs(shirt, g, co, ci, 50)
        return s_join(s_move(s_scale(trousers('chinos'), 0.6), 360, 100), s_move(s_scale(shirt, 0.6), -200, 0),
                      s_move(s_scale(watch(), 0.6), -320, 620), s_move(s_flip(s_scale(__import__('gen_wear_shoes').oxford(), 0.32)), 140, 720))
    # dress
    return s_join(s_move(s_scale(dress('a-line'), 0.62), -120, 0), s_move(heel_side(), 220, 640), s_move(s_scale(handbag(), 0.6), 360, 260))
