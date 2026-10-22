"""More shoes for gen_wear (same conventions as gen_wear_shoes.py: y up, ground at y = 0, toe to the
right, about 1000 long). Each function returns a Scene."""
import math
from gen_wear_kit import *
from gen_wear_shoes import lace_row, bow, block_heel, opening, upper_from, round_sole, dress_sole, cup_sole, vulc_sole, moc_stitch

def arch_bottom(h, toe=996, spring=22):
    """Underside of a high-heeled shoe: from the heel seat at height h down to the ball, toe lifted."""
    k = h / 404.0
    return C([(0, h), (110, h - 4 * k), (190, h - 19 * k), (280, h - 64 * k), (380, h - 144 * k), (470, h - 229 * k), (560, h - 309 * k),
              (640, max(4, h - 366 * k)), (720, 4), (800, 0), (880, 2), (950, spring * 0.45), (toe, spring)])

def stiletto_heel(sc, h, x0=8, w_top=200, tip=(84, 108)):
    k = h / 404.0
    g = G(J(C([(x0, h), (x0 + 22, h * 0.74), (tip[0] - 22, h * 0.4), (tip[0], 20), (tip[0] + 2, 0)], n=10), [(tip[1], 0)],
            C([(tip[1] + 2, 20), (tip[1] + 20, h * 0.37), (tip[1] + 52, h * 0.72), (w_top, h - 12 * k)], n=10)))
    sc.geom(g); sc.lines(clip([[(tip[0] - 20, 16), (tip[1] + 20, 16)]], g))
    return g

def lug_sole(sc, th=120, tt=110, s=60, lugs=True):
    bottom, top, g = cup_sole(th, tt, s)
    sc.geom(g)
    sc.lines(clip([par(bottom, 34)], g))
    if lugs:
        for x in range(70, 900, 60):
            sc.lines(clip([[(x, -4), (x + 14, 30)], [(x + 30, -4), (x + 16, 30)]], g, 1))
    return bottom, top, g

# ---------------------------------------------------------------- boots
def cowboy_boot():
    sc = Scene()
    bottom = dress_sole(110, (20, 210), 40, toe=1010)
    block_heel(sc, 20, 210, 110, lift=16, layers=(60,), slant=46, flare=2)
    sole = round_sole(bottom, 20)
    back = C([(22, 128), (12, 320), (18, 620), (40, 900)])
    topl = C([(40, 900), (120, 884), (215, 846), (300, 878), (390, 908)])
    front = C([(390, 908), (378, 700), (380, 500), (404, 390), (470, 310), (560, 260), (660, 222), (760, 186), (850, 146), (930, 104), (990, 70), (1022, 52)])
    upper = upper_from(J(back, topl, front), bottom, 12)
    opening(sc, C([(40, 900), (140, 922), (260, 924), (390, 912)]), C([(40, 860), (390, 860)]))
    for x in (60, 370): sc.shape(CC([(x - 22, 906), (x - 26, 990), (x, 1010), (x + 26, 990), (x + 22, 906)], n=6))
    sc.geom(upper)
    for d in (0, 16):
        sc.lines(clip([C([(70, 840 - d), (140, 700 - d), (215, 600 - d), (300, 700 - d), (350, 840 - d)])], upper, 6))
    sc.lines(clip([C([(130, 560), (215, 470), (300, 560)]), C([(160, 520), (215, 430), (270, 520)])], upper, 6))
    sc.lines(clip([C([(560, 262), (620, 200), (660, 120), (668, 70)])], upper))
    sc.lines(clip([par(bottom, 30)], upper))
    sc.geom(sole)
    return sc

def work_boot():
    sc = Scene()
    bottom, stop, sole = cup_sole(124, 112, 58)
    back = C([(26, 110), (16, 240), (20, 420), (44, 540)])
    topl = C([(44, 540), (150, 548), (260, 538), (330, 552)])
    throat = C([(330, 552), (380, 450), (440, 360), (520, 300), (620, 262)])
    vamp = C([(620, 262), (740, 236), (840, 216), (920, 196), (970, 168), (996, 132), (998, 110)])
    upper = upper_from(J(back, topl, throat, vamp), bottom, 40)
    opening(sc, C([(44, 540), (150, 566), (260, 562), (330, 566)]), C([(44, 500), (330, 500)]))
    sc.shape(J(C([(314, 560), (330, 600), (370, 610), (400, 584)]), [p for p in par(throat, 16) if p[1] < 590 and p[0] > 380], [(640, 270), (620, 240), (330, 520)]))
    sc.geom(upper)
    sc.lines(clip([par(topl, -30), par(topl, -40)], upper, 3))
    cap = C([(760, 236), (730, 190), (720, 150), (724, 118)])
    sc.lines(clip([cap, par(cap, 12)], upper))
    sc.lines(clip([C([(60, 520), (90, 380), (150, 260), (260, 150)])], upper))
    lace_row(sc, throat, 6, 0.06, 0.9, inset=20, over=18, r=6.5, lean=0.06, hooks=3)
    bow(sc, *at(par(throat, 4), 0.04)[0], s=1.0)
    sc.geom(sole)
    for x in range(70, 900, 56): sc.lines(clip([[(x, -4), (x + 18, 26)]], sole, 1))
    sc.lines(clip([par(bottom, 40)], sole))
    return sc

def ankle_boot_heel():
    sc = Scene(); h = 170
    bottom = arch_bottom(h, 990, 24)
    block_heel(sc, 10, 200, h, lift=18, layers=(), slant=10, flare=20)
    sole = round_sole(bottom, 14)
    back = C([(10, h + 10), (2, h + 160), (10, h + 330), (30, h + 420)])
    topl = C([(30, h + 420), (150, h + 430), (290, h + 420)])
    front = C([(290, h + 420), (300, h + 300), (330, h + 170), (400, h + 40), (500, 190), (610, 140), (720, 110), (820, 92), (910, 74), (968, 54), (994, 30)])
    upper = upper_from(J(back, topl, front), bottom, 8)
    opening(sc, C([(30, h + 420), (150, h + 444), (290, h + 432)]), C([(30, h + 390), (290, h + 390)]))
    sc.geom(upper)
    sc.lines(clip([C([(120, h + 425), (128, h + 260), (150, h + 130)])], upper, 2))
    sc.shape(rect(116, h + 380, 22, 50, 6))
    sc.lines(clip([par(bottom, 26)], upper))
    sc.geom(sole)
    return sc

def knee_boot():
    sc = Scene(); h = 120
    bottom = arch_bottom(h, 992, 24)
    block_heel(sc, 12, 196, h, lift=16, layers=(), slant=8, flare=16)
    sole = round_sole(bottom, 14)
    back = C([(12, h + 10), (4, h + 200), (0, h + 500), (30, h + 780), (40, h + 1050), (36, h + 1200)])
    topl = C([(36, h + 1200), (200, h + 1230), (360, h + 1250)])
    front = C([(360, h + 1250), (366, h + 1000), (350, h + 760), (330, h + 520), (340, h + 330), (390, h + 180), (480, 210), (600, 150), (720, 112), (820, 92), (910, 72), (968, 50), (994, 28)])
    upper = upper_from(J(back, topl, front), bottom, 8)
    opening(sc, C([(36, h + 1200), (200, h + 1262), (360, h + 1262)]), C([(36, h + 1160), (360, h + 1160)]))
    sc.geom(upper)
    sc.lines(clip([C([(170, h + 1220), (180, h + 800), (190, h + 400), (220, h + 120)])], upper, 2))
    sc.lines(clip([par(bottom, 26)], upper))
    sc.geom(sole)
    return sc

def snow_boot():
    sc = Scene()
    bottom, stop, sole = cup_sole(150, 140, 60)
    back = C([(26, 140), (16, 300), (24, 480), (40, 600)])
    topl = C([(40, 600), (200, 606), (360, 600)])
    throat = C([(360, 600), (390, 470), (450, 370), (540, 310), (650, 280)])
    vamp = C([(650, 280), (760, 262), (860, 244), (934, 220), (982, 186), (998, 150)])
    upper = upper_from(J(back, topl, throat, vamp), bottom, 50)
    sc.geom(upper)
    for k in range(1, 4):
        sc.lines(clip([[(0, 140 + k * 95), (1000, 140 + k * 70)]], upper.difference(Polygon([(360, 600), (650, 280), (1000, 280), (1000, 700)])), 4))
    lace_row(sc, throat, 5, 0.06, 0.86, inset=20, over=18, r=6.5, lean=0.06, hooks=2)
    cuff = CC([(20, 560), (60, 640), (110, 610), (160, 650), (210, 612), (260, 652), (310, 614), (360, 648), (390, 590), (300, 560), (150, 556)], n=6)
    sc.shape(cuff)
    sc.geom(sole)
    for x in range(70, 920, 64): sc.lines(clip([[(x, -4), (x + 10, 40)]], sole, 1))
    sc.lines(clip([par(bottom, 46)], sole))
    return sc

def sheepskin_boot():
    sc = Scene()
    bottom = C([(60, 0), (500, 0), (800, 4), (900, 18), (960, 46)])
    sole = G(J(bottom, C([(960, 46), (990, 80), (980, 104)], n=6), C([(980, 104), (800, 90), (400, 86), (60, 86)]), C([(60, 86), (30, 50), (60, 0)], n=6)))
    back = C([(40, 80), (24, 250), (30, 480), (52, 640)])
    topl = C([(52, 640), (220, 650), (400, 640)])
    front = C([(400, 640), (404, 500), (420, 380), (480, 300), (600, 250), (740, 226), (860, 200), (946, 164), (990, 120), (988, 92)])
    upper = upper_from(J(back, topl, front), bottom, 50)
    sc.geom(upper)
    sc.lines(clip([C([(250, 640), (240, 420), (260, 200), (300, 90)]), C([(600, 250), (640, 160), (650, 90)])], upper, 3))
    sc.shape(CC([(40, 610), (80, 680), (140, 660), (200, 690), (260, 662), (320, 690), (380, 664), (420, 620), (330, 600), (150, 600)], n=6))
    sc.geom(sole)
    return sc

def ski_boot():
    sc = Scene()
    sole = G([(30, 0), (980, 0), (980, 70), (940, 70), (940, 100), (60, 100), (60, 70), (30, 70)])
    shell = G(J(C([(60, 100), (40, 300), (60, 520), (120, 760)]), C([(120, 760), (260, 790), (420, 770)]), C([(420, 770), (430, 600), (470, 460), (560, 380), (700, 330), (840, 300), (930, 250), (950, 180), (940, 100)])))
    sc.geom(shell)
    sc.lines(clip([C([(120, 760), (200, 560), (300, 420), (520, 360)])], shell, 4))
    for (x, y) in ((330, 700), (360, 560), (560, 400), (760, 330)):
        sc.shape(rect(x - 40, y - 14, 80, 28, 8)); sc.line([(x - 30, y), (x + 30, y)])
    sc.shape(rect(110, 740, 330, 50, 12))
    sc.geom(sole); sc.lines(clip([[(60, 40), (940, 40)]], sole))
    return sc

def wader():
    sc = Scene()
    bottom, stop, sole = cup_sole(110, 100, 50)
    back = C([(26, 100), (16, 300), (30, 700), (60, 1200), (80, 1500)])
    topl = C([(80, 1500), (240, 1530), (420, 1540)])
    front = C([(420, 1540), (440, 1200), (440, 900), (420, 620), (430, 420), (500, 300), (640, 250), (780, 226), (880, 204), (950, 176), (994, 136), (998, 110)])
    upper = upper_from(J(back, topl, front), bottom, 40)
    sc.geom(upper)
    sc.lines(clip([par(topl, -50)], upper))
    sc.shape(rect(230, 1470, 30, 200, 10)); sc.line(circle(245, 1690, 18, n=12))
    sc.lines(clip([C([(40, 600), (430, 640)]), C([(430, 420), (520, 280)])], upper, 3))
    sc.geom(sole)
    for x in range(70, 900, 60): sc.lines(clip([[(x, -4), (x + 14, 30)]], sole, 1))
    return sc

# ---------------------------------------------------------------- heels
def pump(h=300, kitten=False):
    sc = Scene()
    bottom = arch_bottom(h, 1004, 22)
    if kitten:
        g = G(J(C([(8, h), (30, h * 0.8), (70, h * 0.4), (96, 20), (98, 0)], n=8), [(120, 0)], C([(122, 20), (140, h * 0.5), (190, h - 6)], n=8)))
        sc.geom(g)
    else:
        stiletto_heel(sc, h, w_top=206)
    sole = round_sole(bottom, 14)
    collar = C([(0, h + 6), (-4, h + 60), (6, h + 110), (90, h + 98), (180, h + 64), (280, h + 8), (380, h - 64), (470, h - 136), (560, 180 if h > 200 else 150)])
    vamp = C([(560, 180 if h > 200 else 150), (640, 162), (730, 130), (820, 100), (900, 70), (962, 46), (1010, 26)])
    upper = upper_from(J(collar, vamp), bottom, 7)
    opening(sc, C([(6, h + 110), (100, h + 120), (200, h + 84), (300, h + 26)]), C([(6, h + 40), (300, h - 40)]))
    sc.geom(upper)
    sc.geom(sole)
    return sc

def wedge_sandal():
    sc = Scene(); h = 240
    bottom = arch_bottom(h, 1000, 20)
    wedge = G(J(bottom, [(1000, 20), (1000, 0), (0, 0)]))
    sc.geom(wedge)
    for y in (40, 80, 120, 160, 200): sc.lines(clip([[(0, y), (1000, y * 0.2)]], wedge, 4))
    sole = round_sole(bottom, 16); sc.geom(sole)
    sc.shape(G(J(C([(560, 120), (640, 190), (740, 200), (840, 160), (930, 100), (990, 50)]), C([(990, 50), (900, 70), (780, 110), (660, 120), (580, 100)]))))
    sc.shape(G(J(C([(240, h - 40), (300, 330), (380, 360), (440, 320), (470, 230)]), C([(470, 230), (420, 260), (360, 300), (300, 290), (260, h - 30)]))))
    sc.shape(G(J(C([(0, h + 20), (30, h + 150), (120, h + 170), (200, h + 150), (300, h + 140)]), C([(300, h + 110), (200, h + 120), (120, h + 140), (40, h + 120), (20, h + 10)]))))
    sc.shape(rect(176, h + 128, 40, 50, 6))
    return sc

def mary_jane():
    sc = Scene()
    bottom = dress_sole(60, (20, 200), 50)
    block_heel(sc, 20, 200, 60, lift=12, layers=(), slant=4, flare=4)
    sole = round_sole(bottom, 22)
    collar = C([(22, 80), (10, 140), (20, 200), (100, 196), (200, 170), (300, 150), (400, 150), (500, 166)])
    vamp = C([(500, 166), (600, 186), (700, 190), (800, 176), (880, 152), (944, 118), (984, 86), (996, 64)])
    upper = upper_from(J(collar, vamp), bottom, 12)
    opening(sc, C([(20, 200), (120, 214), (240, 190), (360, 172), (480, 180)]), C([(20, 150), (480, 140)]))
    sc.geom(upper)
    strap = G(J(C([(390, 300), (430, 230), (470, 160), (480, 120)]), C([(530, 130), (520, 170), (480, 240), (440, 310)])))
    sc.geom(strap); sc.shape(circle(452, 262, 12, n=14))
    sc.lines(clip([par(bottom, 32)], upper))
    sc.geom(sole)
    return sc

def ballet_flat():
    sc = Scene()
    bottom = C([(30, 22), (120, 10), (300, 2), (600, 0), (800, 2), (900, 10), (990, 30)])
    sole = round_sole(bottom, 18)
    collar = C([(30, 40), (14, 100), (30, 150), (130, 150), (260, 124), (400, 110), (520, 118)])
    vamp = C([(520, 118), (640, 140), (760, 140), (860, 120), (940, 88), (990, 54), (1000, 36)])
    upper = upper_from(J(collar, vamp), bottom, 10)
    opening(sc, C([(30, 150), (140, 162), (300, 132), (500, 126)]), C([(30, 100), (500, 90)]))
    sc.geom(upper)
    sc.lines(clip([par(J(collar, vamp), -14)], upper, 2))
    bow(sc, 560, 132, s=0.8)
    sc.geom(sole)
    return sc

def pointe_shoe():
    sc = Scene()
    bottom = C([(30, 20), (200, 6), (500, 0), (800, 4), (930, 16), (980, 30)])
    sole = round_sole(bottom, 14)
    collar = C([(30, 40), (12, 110), (30, 170), (160, 170), (300, 150), (440, 136), (560, 150)])
    vamp = C([(560, 150), (680, 172), (800, 168), (900, 150), (960, 120), (990, 80), (992, 40)])
    upper = upper_from(J(collar, vamp), bottom, 8)
    opening(sc, C([(30, 170), (160, 184), (320, 162), (540, 160)]), C([(30, 120), (540, 110)]))
    sc.geom(upper)
    sc.lines(clip([[(990, 30), (994, 150)], C([(820, 170), (850, 100), (860, 30)])], upper, 1))
    for P in (C([(200, 170), (260, 300), (380, 420), (430, 560)]), C([(230, 168), (180, 300), (120, 420), (60, 520)])):
        sc.shape(LineString(P).buffer(14, cap_style=2).exterior.coords[:])
    sc.geom(sole)
    return sc

def tap_shoe():
    sc = mary_jane()
    sc.shape(G(J(C([(700, -2), (780, -6), (880, 2), (960, 20), (990, 38)]), C([(990, 38), (940, 40), (840, 26), (720, 18)]))))
    sc.shape(rect(18, -14, 186, 22, 6))
    return sc

def mule():
    sc = Scene(); h = 140
    bottom = arch_bottom(h, 1000, 20)
    g = G(J(C([(10, h), (30, h * 0.6), (60, 20), (62, 0)], n=8), [(150, 0)], C([(152, 20), (170, h * 0.6), (200, h - 6)], n=8)))
    sc.geom(g)
    sole = round_sole(bottom, 14)
    upper = G(J(C([(470, 190), (520, 270), (620, 290), (740, 260), (860, 200), (940, 140), (998, 60)]), C([(998, 60), (900, 60), (760, 70), (620, 90), (500, 110)])))
    sc.geom(upper)
    sc.lines(clip([C([(520, 250), (640, 270), (760, 240), (880, 170)])], upper, 2))
    sc.geom(sole)
    return sc

def slingback():
    sc = Scene(); h = 220
    bottom = arch_bottom(h, 1004, 22)
    stiletto_heel(sc, h, w_top=200)
    sole = round_sole(bottom, 14)
    vamp = G(J(C([(500, 200), (560, 240), (660, 230), (760, 196), (860, 150), (950, 90), (1010, 30)]), C([(1010, 30), (900, 40), (760, 70), (640, 110), (520, 150)])))
    sc.geom(vamp)
    strap = LineString(C([(-6, h + 50), (60, h + 110), (160, h + 120), (240, h + 90), (300, h + 40)])).buffer(12, cap_style=2)
    sc.geom(strap); sc.shape(rect(150, h + 102, 30, 36, 6))
    sc.geom(sole)
    return sc

def strappy_sandal():
    sc = Scene(); h = 300
    bottom = arch_bottom(h, 1000, 20)
    stiletto_heel(sc, h, w_top=196)
    sole = round_sole(bottom, 14); sc.geom(sole)
    for P in (C([(700, 30), (760, 110), (840, 120), (920, 80), (980, 40)]), C([(560, 110), (620, 200), (700, 210), (760, 150)]), C([(0, h + 80), (100, h + 120), (200, h + 110), (300, h + 70)])):
        sc.geom(LineString(P).buffer(13, cap_style=1))
    sc.geom(LineString(C([(300, h + 70), (380, 260), (480, 160)])).buffer(10))
    sc.shape(circle(210, h + 112, 12, n=14))
    return sc

def platform_heel():
    sc = Scene(); h = 340; pf = 70
    bottom = C([(0, h), (110, h - 4), (200, h - 30), (300, h - 90), (400, h - 170), (500, 190), (580, pf + 30), (640, pf), (760, pf - 4), (880, pf + 2), (960, pf + 14), (1000, pf + 26)])
    plat = G(J([(560, pf + 40), (640, pf)], C([(640, pf), (800, pf - 4), (960, pf + 14), (1004, pf + 26)]), [(1004, 10), (980, 0), (600, 0), (560, 30)]))
    sc.geom(plat); sc.lines(clip([[(560, pf / 2), (1010, pf / 2)]], plat, 3))
    sc.geom(G([(10, h), (210, h - 10), (180, 0), (40, 0)])); sc.lines(clip([[(0, 18), (230, 18)]], G([(10, h), (210, h - 10), (180, 0), (40, 0)])))
    collar = C([(0, h + 6), (-6, h + 70), (8, h + 120), (100, h + 110), (200, h + 70), (300, h + 10), (400, h - 70), (480, h - 110)])
    vamp = C([(480, h - 110), (560, 210), (660, 190), (760, 170), (860, 150), (940, 126), (1000, 96), (1012, 80)])
    upper = upper_from(J(collar, vamp), bottom, 7)
    opening(sc, C([(8, h + 120), (100, h + 130), (220, h + 92), (320, h + 30)]), C([(8, h + 50), (320, h - 20)]))
    sc.geom(upper)
    sc.geom(LineString(C([(0, h + 90), (100, h + 140), (220, h + 120), (330, h + 60)])).buffer(12))
    sc.geom(round_sole(bottom, 12))
    return sc

# ---------------------------------------------------------------- casual, sport and special
def clog():
    sc = Scene()
    sole = G([(20, 0), (960, 0), (990, 30), (990, 120), (20, 120), (0, 60)])
    sc.geom(sole)
    sc.lines(clip([[(0, 90), (1000, 90)]], sole))
    upper = G(J(C([(300, 120), (330, 260), (420, 330), (560, 350), (700, 330), (830, 280), (930, 210), (990, 140)]), [(990, 120), (300, 120)]))
    sc.geom(upper)
    for k in range(14):
        p, _ = at(C([(330, 140), (350, 250), (430, 312), (560, 330), (700, 312), (830, 262), (930, 196), (975, 140)]), k / 13)
        sc.shape(circle(p[0], p[1], 7, n=10))
    return sc

def wooden_clog():
    sc = Scene()
    body = G(J(C([(20, 0), (400, 0), (700, 10), (900, 40), (1010, 120), (1040, 200)]), C([(1040, 200), (980, 210), (880, 250), (720, 300), (540, 320), (380, 330), (200, 320), (60, 280), (10, 160), (20, 0)])))
    sc.geom(body)
    sc.shape(G(J(C([(80, 300), (100, 360), (200, 380), (340, 370)]), C([(340, 370), (330, 330), (200, 330), (90, 290)]))))
    sc.lines(clip([C([(540, 120), (600, 200), (660, 240)]), C([(600, 200), (560, 250)]), C([(600, 200), (650, 170)]), CC([(640, 250), (680, 280), (700, 240), (670, 220)], n=6)], body, 2))
    sc.lines(clip([[(260, 0), (260, 80)], [(140, 0), (140, 80)]], body))
    return sc

def espadrille():
    sc = Scene()
    sole = G(J(C([(40, 0), (500, 0), (900, 6), (990, 40)]), C([(990, 40), (1000, 70), (980, 90)], n=6), C([(980, 90), (700, 84), (300, 84), (40, 84)]), C([(40, 84), (20, 40), (40, 0)], n=6)))
    sc.geom(sole)
    for x in range(50, 980, 22): sc.lines(clip([[(x, 4), (x + 16, 40)], [(x + 16, 44), (x, 80)]], sole, 2))
    collar = C([(40, 84), (26, 150), (40, 200), (160, 196), (280, 170)])
    vamp = C([(280, 170), (400, 210), (540, 240), (680, 236), (800, 210), (900, 170), (960, 130), (990, 90)])
    upper = upper_from(J(collar, vamp), C([(20, 60), (1000, 60)]), 20)
    sc.geom(upper)
    sc.lines(clip([dashes(par(C([(30, 96), (990, 100)]), 0), 16, 10)[i] for i in range(len(dashes(C([(30, 96), (990, 100)]), 16, 10)))], upper, 2))
    return sc

def gladiator():
    sc = Scene()
    sole = round_sole(C([(30, 30), (300, 20), (700, 18), (990, 30)]), 30)
    sc.geom(sole)
    sc.geom(LineString([(40, 50), (40, 700)]).buffer(16, cap_style=2))
    for k, y in enumerate((140, 240, 340, 440, 540, 640)):
        sc.geom(LineString(C([(30, y), (200, y + 20 - k * 4), (360, y - 10 - k * 8)])).buffer(12, cap_style=1))
    for P in (C([(560, 46), (640, 120), (760, 130), (880, 90), (960, 50)]), C([(380, 60), (420, 200), (400, 300)])):
        sc.geom(LineString(P).buffer(14, cap_style=1))
    return sc

def slider():
    sc = Scene()
    bed = round_sole(C([(30, 40), (300, 30), (700, 26), (990, 40)]), 50); sc.geom(bed)
    strap = G(J(C([(380, 70), (430, 220), (560, 270), (720, 240), (800, 140), (820, 70)]), [(820, 70), (380, 70)]))
    sc.geom(strap); sc.lines(clip([C([(440, 90), (480, 200), (580, 236), (700, 214), (770, 120)])], strap, 6))
    return sc

def slipper():
    sc = Scene()
    sole = round_sole(C([(30, 20), (300, 6), (700, 4), (960, 20)]), 36); sc.geom(sole)
    upper = G(J(C([(30, 40), (20, 160), (60, 260), (180, 280), (300, 230), (440, 240), (600, 280), (760, 270), (880, 220), (960, 140), (990, 60)]), [(990, 40), (30, 40)]))
    sc.geom(upper)
    sc.shape(CC([(20, 230), (60, 300), (130, 290), (200, 310), (270, 280), (330, 260), (300, 220), (180, 230), (60, 200)], n=6))
    sc.shape(circle(700, 310, 50, n=24)); sc.line(circle(700, 310, 25, n=14))
    return sc

def baby_shoe():
    sc = Scene()
    sole = round_sole(C([(60, 30), (300, 10), (700, 10), (930, 40)]), 40); sc.geom(sole)
    upper = G(J(C([(60, 60), (30, 250), (80, 420), (260, 440), (420, 420), (580, 380), (760, 330), (900, 240), (960, 120), (950, 50)]), [(950, 50), (60, 50)]))
    sc.geom(upper)
    strap = G(J(C([(330, 520), (390, 420), (440, 300), (470, 180)]), C([(560, 190), (520, 320), (460, 450), (420, 540)])))
    sc.geom(strap)
    sc.lines(clip([C([(80, 400), (260, 420), (420, 400)]), C([(700, 340), (760, 240), (790, 120)])], upper, 4))
    for k in range(3): sc.shape(circle(560 + k * 90, 210 + (k - 1) ** 2 * 20, 22, n=14))
    return sc

def climbing_shoe():
    sc = Scene()
    bottom = C([(40, 40), (200, 10), (450, 0), (700, 6), (860, 30), (960, 70), (1010, 110)])
    sole = round_sole(bottom, 30); sc.geom(sole)
    upper = upper_from(J(C([(40, 60), (20, 200), (60, 320), (180, 340), (300, 320)]), C([(300, 320), (420, 300), (560, 270), (700, 240), (840, 200), (950, 150), (1000, 120)])), bottom, 10)
    sc.geom(upper)
    rand = G(J(C([(40, 60), (40, 110), (300, 80), (600, 90), (840, 130), (980, 120)]), [(1000, 100)], bottom[::-1]))
    sc.geom(rand)
    for x0, x1 in ((330, 420), (470, 560)):
        st = G([(x0, 360), (x0 + 30, 380), (x1 + 60, 120), (x1 + 20, 100)]); sc.geom(st)
    sc.shape(G(J(C([(30, 300), (10, 380), (60, 400), (90, 330)]), [(90, 310)])))
    return sc

def bowling_shoe():
    sc = Scene()
    bottom = dress_sole(50, (20, 200), 40)
    block_heel(sc, 20, 200, 50, lift=10, layers=(), slant=2, flare=4)
    sole = round_sole(bottom, 20)
    out = J(C([(22, 70), (10, 150), (14, 220), (36, 270)]), C([(36, 270), (120, 268), (220, 254), (300, 268)]))
    facing = C([(300, 268), (390, 250), (480, 226)])
    vamp = C([(480, 226), (600, 210), (720, 190), (830, 160), (920, 124), (974, 88), (994, 60)])
    upper = upper_from(J(out, facing, vamp), bottom, 10)
    opening(sc, C([(36, 270), (120, 284), (230, 272), (300, 280)]), C([(36, 240), (300, 240)]))
    sc.geom(upper)
    saddle = G(J(C([(250, 300), (300, 240), (360, 150), (380, 60)]), C([(560, 60), (540, 160), (500, 230), (480, 300)]))).intersection(upper)
    sc.geom(saddle)
    sc.lines(clip([C([(330, 220), (360, 140), (370, 70)])], saddle, 6))
    lace_row(sc, facing, 4, 0.12, 0.86, inset=16, over=12, r=5.5, lean=0.08)
    sc.lines(clip([par(bottom, 30)], upper))
    sc.lines(ztext_y('3', 120, 140, 70))
    sc.geom(sole)
    return sc

def ztext_y(s, x, y, size):
    return [[(px, -py) for px, py in P] for P in text(s, x, -y, size, 'HersheySansMed')]

def roller_skate():
    sc = Scene()
    for cx in (200, 800): sc.shape(circle(cx, 90, 90, n=36)); sc.line(circle(cx, 90, 40, n=20))
    sc.geom(G([(100, 160), (900, 160), (900, 210), (100, 210)]))
    for cx in (200, 800): sc.geom(G([(cx - 60, 160), (cx + 60, 160), (cx + 20, 100), (cx - 20, 100)]))
    sc.shape(G([(940, 150), (1000, 110), (1010, 150), (980, 200), (930, 200)]))
    bottom = C([(60, 230), (400, 226), (700, 226), (940, 236)])
    sole = round_sole(bottom, 24); sc.geom(sole)
    back = C([(60, 240), (40, 400), (50, 560), (80, 680)])
    topl = C([(80, 680), (200, 690), (320, 676)])
    throat = C([(320, 676), (350, 560), (400, 470), (480, 400), (600, 350)])
    vamp = C([(600, 350), (720, 330), (840, 306), (920, 280), (960, 250)])
    upper = upper_from(J(back, topl, throat, vamp), bottom, 10)
    opening(sc, C([(80, 680), (200, 704), (320, 690)]), C([(80, 650), (320, 650)]))
    sc.geom(upper)
    lace_row(sc, throat, 7, 0.06, 0.92, inset=18, over=16, r=6, lean=0.06)
    bow(sc, *at(par(throat, 4), 0.05)[0], s=0.9)
    return sc

def moccasin():
    sc = Scene()
    bottom = C([(30, 20), (200, 6), (600, 0), (850, 6), (960, 30), (990, 60)])
    sole = round_sole(bottom, 24); sc.geom(sole)
    out = C([(30, 40), (14, 140), (30, 220), (140, 230), (280, 210), (400, 220)])
    vamp = C([(400, 220), (540, 250), (680, 244), (800, 214), (900, 170), (960, 120), (994, 70)])
    upper = upper_from(J(out, vamp), bottom, 14)
    opening(sc, C([(30, 220), (150, 240), (300, 222), (400, 232)]), C([(30, 180), (400, 180)]))
    sc.geom(upper)
    U = C([(420, 200), (520, 250), (700, 250), (850, 196), (920, 140)])
    moc_stitch(sc, U, upper, step=16, a=7)
    sc.lines(clip([par(out, -14)], upper, 2))
    bow(sc, 380, 214, s=0.8)
    return sc

def sport_sandal():
    sc = Scene()
    bottom, stop, sole = cup_sole(110, 100, 50)
    sc.geom(sole)
    for x in range(70, 900, 56): sc.lines(clip([[(x, -4), (x + 16, 32)]], sole, 1))
    for P in (C([(620, 100), (700, 200), (820, 220), (930, 170), (980, 110)]), C([(320, 110), (380, 260), (470, 300), (560, 260), (600, 110)]), C([(30, 130), (60, 300), (160, 340), (300, 320), (380, 270)])):
        sc.geom(LineString(P).buffer(20, cap_style=2))
    for (x, y) in ((470, 300), (160, 340)): sc.shape(rect(x - 24, y - 18, 48, 36, 8)); sc.line([(x - 10, y - 18), (x - 10, y + 18)])
    return sc

def basketball_shoe():
    sc = Scene()
    bottom, stop, sole = cup_sole(120, 96, 60)
    back = C([(24, 110), (14, 260), (20, 440), (44, 560), (80, 610)])
    collar = C([(80, 610), (150, 606), (230, 590), (300, 610)])
    throat = C([(300, 610), (330, 520), (380, 430), (450, 350), (560, 280), (680, 236)])
    vamp = C([(680, 236), (800, 210), (900, 180), (960, 150), (994, 110)])
    upper = upper_from(J(back, collar, throat, vamp), bottom, 34)
    opening(sc, C([(80, 610), (160, 630), (300, 622)]), C([(80, 580), (300, 580)]))
    sc.geom(upper)
    strap = G(J(C([(40, 520), (180, 500), (330, 470), (400, 440)]), C([(400, 380), (330, 410), (180, 440), (40, 460)])))
    sc.geom(strap.intersection(upper.buffer(10)))
    sc.lines(clip([C([(140, 150), (300, 200), (440, 220)]), C([(780, 210), (820, 160), (860, 140)])], upper, 4))
    lace_row(sc, throat, 6, 0.1, 0.9, inset=20, over=18, r=6.5, lean=0.06)
    sc.geom(sole)
    sc.lines(clip([par(bottom, 30)], sole))
    return sc

def desert_boot():
    sc = Scene()
    bottom = C([(30, 0), (400, 0), (800, 2), (930, 18), (990, 40)])
    sole = G(J(bottom, C([(990, 40), (1000, 64), (990, 80)], n=6), C([(990, 80), (700, 76), (300, 76), (30, 76)]), C([(30, 76), (14, 40), (30, 0)], n=6)))
    sc.geom(sole)
    sc.lines(clip([C([(20, 30), (200, 36), (400, 30), (600, 36), (800, 30), (1000, 36)])], sole, 2))
    back = C([(30, 76), (20, 220), (30, 380), (50, 460)])
    topl = C([(50, 460), (160, 466), (270, 456)])
    facing = C([(270, 456), (320, 380), (380, 320), (460, 280)])
    vamp = C([(460, 280), (580, 246), (700, 216), (820, 186), (920, 150), (980, 110), (992, 80)])
    upper = upper_from(J(back, topl, facing, vamp), C([(20, 60), (1000, 60)]), 16)
    opening(sc, C([(50, 460), (160, 480), (270, 470)]), C([(50, 430), (270, 430)]))
    sc.geom(upper)
    sc.lines(clip([C([(260, 430), (300, 300), (340, 200), (360, 90)])], upper, 2))
    lace_row(sc, facing, 3, 0.12, 0.85, inset=16, over=12, r=6, lean=0.08)
    bow(sc, *at(par(facing, 4), 0.1)[0], s=0.8)
    return sc

def riding_boot():
    sc = Scene()
    bottom = dress_sole(70, (20, 210), 44)
    block_heel(sc, 20, 210, 70, lift=12, layers=(40,), slant=6, flare=4)
    sole = round_sole(bottom, 22)
    back = C([(22, 90), (10, 300), (10, 600), (30, 900), (40, 1120)])
    topl = C([(40, 1120), (200, 1150), (370, 1180)])
    front = C([(370, 1180), (370, 950), (350, 700), (360, 480), (400, 350), (480, 280), (600, 240), (720, 206), (830, 172), (920, 132), (972, 100), (994, 70)])
    upper = upper_from(J(back, topl, front), bottom, 12)
    opening(sc, C([(40, 1120), (200, 1180), (370, 1192)]), C([(40, 1080), (370, 1080)]))
    sc.geom(upper)
    sc.lines(clip([par(topl, -40), C([(30, 300), (120, 260), (250, 250), (380, 300)])], upper, 3))
    sc.geom(sole)
    return sc

# ---------------------------------------------------------------- other views
def sole_view():
    """A trainer's sole seen from below (toe at the top)."""
    sc = Scene()
    out = CC([(0, 1000), (130, 960), (190, 820), (200, 640), (170, 470), (150, 330), (170, 160), (110, 20), (0, 0), (-110, 20), (-170, 160), (-150, 330), (-170, 470), (-200, 640), (-190, 820), (-130, 960)], n=10)
    g = G(out); sc.geom(g)
    sc.line(par(out, -24) if par(out, -24) else out)
    for y in range(560, 940, 40): sc.lines(clip([[(-200, y), (0, y + 30), (200, y)]], g.buffer(-40)))
    for y in range(80, 330, 40): sc.lines(clip([[(-200, y + 30), (0, y), (200, y + 30)]], g.buffer(-40)))
    sc.line(circle(0, 720, 70, n=28)); sc.line(circle(0, 720, 40, n=20))
    sc.lines(clip([[(-200, 450), (200, 450)], [(-200, 400), (200, 400)]], g.buffer(-30)))
    return sc

def shoe_top(cx=0.0, mirror=False, laces=True):
    sc = Scene()
    out = CC([(0, 1000), (120, 960), (180, 820), (190, 640), (160, 480), (140, 320), (150, 160), (100, 30), (0, 0), (-100, 30), (-150, 160), (-140, 320), (-160, 480), (-190, 640), (-170, 820), (-120, 960)], n=10)
    g = G(out); sc.geom(g)
    sc.shape(CC([(0, 360), (90, 330), (100, 200), (70, 90), (0, 70), (-70, 90), (-100, 200), (-90, 330)], n=8))
    sc.line(C([(0, 380), (80, 350), (95, 230)]))
    if laces:
        for k in range(5):
            y = 420 + k * 55
            sc.line([(-70, y), (70, y + 30)]); sc.line([(70, y), (-70, y + 30)])
            for s in (-1, 1): sc.shape(circle(s * 75, y, 9, n=10))
        bow(sc, 0, 420, s=1.1, flip=False)
    sc.line(C([(-150, 720), (0, 780), (150, 720)]))
    if mirror: sc = s_mirror(sc, 0)
    return s_move(sc, cx, 0)

def pair_from_above():
    return s_join(shoe_top(-250, False), shoe_top(250, True))
