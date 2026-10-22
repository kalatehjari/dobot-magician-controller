"""Cars and sports cars: side views from the parametric profile engine (gen_cars_side.py), plus front,
rear and top views drawn here. Generic designs only (no badges, logos or model names).
Usage: python3 -I gen_cars.py <out.json> [sheet.png]"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_cars_side import *
from gen_cars_parts import *

def V(base, **k):
    d = dict(base); d.update(k); return d

def car(p):
    L, g = side(**p)
    return L

# ---------------------------------------------------------------- accessories (ops)
def roof_items(fn): return ('front', 'fn', fn)

def roof_box(x0, x1, h, label=None, size=110, r=40, z_off=40):
    def f(sc, g):
        z0 = min(top_z(g, x0), top_z(g, x1)) + z_off
        sc.geom(rpoly([(x0, z0, 0), (x1, z0, 0), (x1 - 40, z0 + h, r), (x0 + 40, z0 + h, r)]))
        for b in bars([x0 + 60, x1 - 60], g, h=z_off, w=50): sc.geom(b)
        if label: sc.lines(ztext(label, (x0 + x1) / 2, z0 + h / 2 - size / 2, size, 'HersheySans1'))
    return roof_items(f)

def light_bar(x0, x1):
    def f(sc, g):
        z0 = top_z(g, (x0 + x1) / 2) + 20
        sc.geom(rpoly([(x0, z0, 0), (x1, z0, 0), (x1 - 30, z0 + 120, 40), (x0 + 30, z0 + 120, 40)]))
        sc.line([((x0 + x1) / 2, z0 + 10), ((x0 + x1) / 2, z0 + 110)])
    return roof_items(f)

def door_text(s, x, z, size=150):
    return ('front', 'lines', ztext(s, x, z, size, 'HersheySansMed'))

def stripe(pts, w=60):
    return ('body', 'fn', lambda sc, g: sc.lines(clip(lines_of(LineString(pts).buffer(w / 2, cap_style=2)), g.body.buffer(-20))))

def surfboard(xf, xr, lift=120):
    """A board on roof bars; xf > xr (front, rear of the roof)."""
    def f(sc, g):
        bf, br = xf - 300, xr + 300
        zf, zr = top_z(g, bf) + lift, top_z(g, br) + lift
        for b in bars([bf, br], g, h=lift - 30, w=50): sc.geom(b)
        P = rpoly([(xf + 500, zf + 40, 80), (xf + 200, zf, 0), (xr - 200, zr, 60), (xr - 300, zr + 80, 40), (xf + 200, zf + 90, 0)])
        sc.geom(P); sc.line([(xf + 100, zf + 45), (xr - 150, zr + 40)])
    return roof_items(f)

def luggage(x0, x1, rack=70):
    def f(sc, g):
        z = max(top_z(g, x0), top_z(g, x1)) + rack
        sc.geom(rails(x0, x1, g, h=rack, t=40))
        x = x1 + 60
        for w, h in ((520, 300), (420, 220), (360, 340)):
            if x + w > x0: break
            sc.geom(rpoly([(x, z + 15, 0), (x + w, z + 15, 0), (x + w, z + 15 + h, 30), (x, z + 15 + h, 30)]))
            sc.line([(x + w / 2, z + 15), (x + w / 2, z + 15 + h)])
            x += w + 30
    return roof_items(f)

def ladder_rack(x0, x1, h=90):
    def f(sc, g):
        z = max(top_z(g, x0), top_z(g, x1)) + h
        sc.geom(rails(x0, x1, g, h=h - 20, t=36))
        sc.geom(zbox(x0 - 200, z, x1 + 100, z + 70)); sc.geom(zbox(x0 - 200, z + 70, x1 + 100, z + 140, 0))
        for x in np.arange(x1 + 100, x0, 300): sc.line([(x, z + 4), (x, z + 66)])
    return roof_items(f)

def charger(x, z_top=1500):
    def f(sc, g):
        sc.geom(rpoly([(x - 160, 0, 0), (x + 160, 0, 0), (x + 160, z_top, 60), (x - 160, z_top, 60)]))
        sc.geom(zbox(x - 100, z_top - 420, x + 100, z_top - 180, 30), fill=False)
        sc.line(circle(x, z_top - 100, 40, n=12))
        port = (g.xra - 200, 950)
        sc.line(cable((x - 160, z_top - 600), port, sag=380))
    return ('back', 'fn', f)

# ---------------------------------------------------------------- everyday cars (side views)
SALOON = dict(WB=2800, FO=950, RO=1050, Rw=330, rim=0.68, clr=145,
    chin_z=190, chin_dx=110, chin_r=80, nose_z=540, nose_r=170, hood_z=770, hood_dx=210, hood_r=220, hood_b=18,
    cowl=-480, cowl_z=1000, cowl_r=60, hdr=-1340, H=1445, roof_fr=320, roof_b=45,
    tail='notch', roof_rx=330, roof_rz=1415, roof_rr=330, gl_b=30, deck_x=620, deck_z=1085, deck_r=140, deck_b=8,
    tail_x=30, tail_z=1065, tail_r=50, bump_z=640, bump_r=170, rbot_x=110, rbot_z=290,
    belt=[(-600, 985), (-2000, 1030), (-2700, 1075)], c_bot=60, c_top=330, roof_t=75, a_w=80,
    pillars=((-1590, -1640, 95),), doors=((-480, -470, -20), (-1560, -1590, 0)), rear_arch_door=(80, 55, 150),
    handles=((-1380, 900), (-2300, 935)), lines=([(600, 730), (-1000, 880), (-3000, 950), (-3790, 960)],),
    head=dict(pts=[(-300, 1000), (520, 1000), (520, 830), (300, 690), (-300, 690)]),
    tail_light=dict(pts=[(-300, 1200), (360, 1200), (360, 990), (180, 940), (-300, 940)]))
HATCH5 = dict(WB=2630, FO=860, RO=760, Rw=320, rim=0.66, clr=150,
    chin_z=200, chin_dx=90, nose_z=550, nose_r=160, hood_z=800, hood_dx=190, hood_r=200, hood_b=15,
    cowl=-430, cowl_z=1010, hdr=-1240, H=1470, roof_fr=280, roof_b=30,
    tail='hatch', roof_rx=-260, roof_rz=1440, roof_rr=200, gl_b=15, tail_x=120, tail_z=1030, tail_r=70, bump_z=600, rbot_z=280,
    belt=[(-600, 1000), (-2000, 1030), (-2650, 1060)], c_bot=230, c_top=-20, roof_t=75, a_w=80,
    pillars=((-1480, -1530, 95),), doors=((-440, -440, -20), (-1450, -1470, 0)), rear_arch_door=(240, 55, 170),
    handles=((-1270, 910), (-2140, 935)), lines=([(560, 760), (-1200, 900), (-3000, 950), (-3400, 960)],),
    head=dict(pts=[(-300, 1000), (460, 1000), (460, 840), (280, 700), (-300, 700)]),
    tail_light=dict(pts=[(-300, 1200), (260, 1200), (260, 970), (-300, 920)]))
HATCH3 = dict(WB=2500, FO=780, RO=640, Rw=305, rim=0.62, rims='steel', clr=150,
    chin_z=210, chin_dx=80, nose_z=540, nose_r=150, hood_z=790, hood_dx=170, hood_r=180, hood_b=15,
    cowl=-420, cowl_z=990, hdr=-1200, H=1430, roof_fr=260, roof_b=25,
    tail='hatch', roof_rx=-170, roof_rz=1400, roof_rr=180, gl_b=10, tail_x=90, tail_z=1000, tail_r=70, bump_z=580, rbot_z=280,
    belt=[(-600, 990), (-1800, 1020), (-2400, 1060)], dlo_r=60, c_bot=200, c_top=-60, roof_t=75, a_w=80,
    pillars=((-1700, -1820, 80),), doors=((-430, -440, -20), (-1720, -1760, 0)), handles=((-1560, 905),),
    head=dict(pts=[(-300, 1000), (420, 1000), (420, 840), (260, 720), (-300, 720)]),
    tail_light=dict(pts=[(-300, 1200), (230, 1200), (230, 960), (-300, 900)]))
ESTATE = V(SALOON, tail='hatch', RO=1080, roof_rx=-700, roof_rz=1450, roof_rr=160, gl_b=4, tail_x=80, tail_z=1300, tail_r=90,
    bump_z=620, c_bot=-650, c_top=-760, glass_upto=None, pillars=((-1590, -1640, 95), (-2600, -2580, 80)),
    tail_light=dict(pts=[(-300, 1250), (200, 1250), (200, 960), (-300, 940)]))
CROSSOVER = V(HATCH5, Rw=360, rim=0.62, rims='twin5', clr=210, chin_z=280, nose_z=660, hood_z=900, cowl_z=1110, H=1620, hdr=-1280,
    roof_rz=1590, tail_z=1130, bump_z=700, rbot_z=360, belt=[(-600, 1110), (-2000, 1140), (-2650, 1170)], flare=60, flare_lo=0.2,
    handles=((-1270, 1020), (-2140, 1045)), lines=([(560, 860), (-1200, 1000), (-3400, 1050)],),
    head=dict(pts=[(-300, 1110), (460, 1110), (460, 950), (280, 820), (-300, 820)]),
    tail_light=dict(pts=[(-300, 1320), (260, 1320), (260, 1080), (-300, 1030)]))
SUV = dict(WB=2900, FO=900, RO=1000, Rw=390, rim=0.6, rims='6', clr=230, arch='square', gap=50,
    chin_z=330, chin_dx=80, chin_r=50, nose_z=820, nose_r=120, hood_z=1100, hood_dx=150, hood_r=140, hood_b=10,
    cowl=-560, cowl_z=1240, cowl_r=40, hdr=-1300, H=1860, roof_fr=200, roof_b=10,
    tail='hatch', roof_rx=-950, roof_rz=1850, roof_rr=120, gl_b=0, tail_x=40, tail_z=1700, tail_r=100, bump_z=760, bump_r=80, rbot_x=60, rbot_z=380,
    belt=[(-600, 1250), (-3600, 1270)], c_bot=-880, c_top=-930, roof_t=80, a_w=90, dlo_r=40,
    pillars=((-1700, -1710, 100), (-2950, -2950, 90)), doors=((-560, -560, -10), (-1690, -1690, 0)), rear_arch_door=(300, 60, 200),
    handles=((-1500, 1150), (-2500, 1160)), sill=True, sill_z=330,
    head=dict(pts=[(-300, 1200), (420, 1200), (420, 1000), (-300, 1000)]),
    tail_light=dict(pts=[(-300, 1550), (160, 1550), (160, 1150), (-300, 1150)]),
    ops=(('front', 'fn', lambda sc, g: sc.geom(rails(-1300, -3500, g, h=70, t=40))),))
OFFROADER = dict(WB=2500, FO=760, RO=900, Rw=400, rim=0.56, rims='steel', tread=0, clr=280, arch='square', gap=60, flare=70, flare_lo=0.1,
    chin_z=380, chin_dx=40, chin_r=30, nose_z=950, nose_r=50, hood_z=1150, hood_dx=60, hood_r=50, hood_b=0,
    cowl=-500, cowl_z=1200, cowl_r=20, hdr=-760, H=1950, roof_fr=60, roof_b=0,
    tail='hatch', roof_rx=-1300, roof_rz=1950, roof_rr=60, gl_b=0, tail_x=0, tail_z=1900, tail_r=60, bump_z=500, bump_r=40, rbot_x=0, rbot_z=420,
    belt=[(-600, 1220), (-3400, 1220)], c_bot=-1180, c_top=-1180, roof_t=90, a_w=110, dlo_r=20,
    pillars=((-1500, -1500, 110), (-2500, -2500, 100)), doors=((-500, -500, 0), (-1480, -1480, 0)), door_bot=420,
    handles=((-1350, 1120), (-2350, 1120)),
    head=dict(pts=[(-60, 1120), (200, 1120), (200, 880), (-60, 880)]), tail_light=dict(pts=[(-60, 1500), (140, 1500), (140, 1200), (-60, 1200)]),
    ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(g.xr - 320, 900, 90), (g.xr + 10, 900, 40), (g.xr + 10, 1700, 40), (g.xr - 320, 1700, 90)])), sc.lines([[(g.xr - 300, z), (g.xr - 20, z)] for z in (1000, 1100, 1500, 1600)]))),))
def pickup(cab='single'):
    WB = 3200 if cab == 'single' else 3600
    cab_back = -1700 if cab == 'single' else -2450
    top = [(820, 900, 80, 0), (700, 1120, 120, 10), (-560, 1260, 40, 8), (-1250, 1850, 140, 10), (cab_back + 120, 1860, 80, 0),
           (cab_back, 1820, 40, 0), (cab_back, 1300, 0, 0), (-WB - 1150, 1300, 30, 0), (-WB - 1200, 1260, 30, 0), (-WB - 1200, 600, 60, 0), (-WB - 1120, 420, 40, 0)]
    pillars = ((-1450, -1450, 100),) if cab == 'single' else ((-1500, -1520, 100),)
    doors = ((-560, -560, -10), (cab_back + 40, cab_back + 40, 0)) if cab == 'single' else ((-560, -560, -10), (-1490, -1490, 0), (cab_back + 40, cab_back + 40, 0))
    return dict(WB=WB, FO=880, RO=1200, Rw=400, rim=0.6, rims='6', tread=0, clr=260, arch='square', gap=55, flare=40, flare_lo=0.15,
        chin_z=360, chin_dx=60, chin_r=50, top=top, H=1860, hdr=-1250, cowl=-560, cowl_z=1260,
        belt=[(-600, 1300), (cab_back, 1300)], c_bot=cab_back + WB + 60, c_top=cab_back + WB + 110, roof_t=80, a_w=90, dlo_r=40,
        pillars=pillars, doors=doors, door_bot=380, handles=((-1250, 1210),) if cab == 'single' else ((-1300, 1210), (-2250, 1210)),
        head=dict(pts=[(-300, 1110), (380, 1110), (380, 930), (-300, 930)]), tail_light=dict(pts=[(-60, 1250), (130, 1250), (130, 900), (-60, 900)]),
        lines=([(cab_back - 40, 1290), (-WB - 1160, 1290)],),
        mirror_at=(-700, 1330))
PANEL_VAN = dict(WB=3400, FO=820, RO=1100, Rw=350, rim=0.6, rims='steel', clr=190,
    chin_z=280, chin_dx=60, top=[(820, 760, 90, 0), (650, 1080, 150, 10), (-200, 1330, 60, 8), (-900, 2350, 220, 10), (-4300, 2400, 120, 0), (-4500, 2330, 60, 0), (-4500, 450, 60, 0), (-4420, 300, 40, 0)],
    H=2400, hdr=-900, cowl=-200, cowl_z=1330, belt=[(-600, 1330), (-1700, 1350)], glass_upto=-1500, c_bot=None, c_top=None, roof_t=90, a_w=110, dlo_r=50,
    doors=((-200, -230, -10), (-1450, -1450, 0)), handles=((-1300, 1250),), free_lines=([(-1600, 2050), (-3900, 2050)],),
    head=dict(pts=[(-300, 1020), (330, 1020), (330, 860), (-300, 860)]), tail_light=dict(pts=[(-60, 1300), (120, 1300), (120, 900), (-60, 900)]))
MPV = dict(WB=3000, FO=950, RO=950, Rw=340, rim=0.64, rims='7', clr=160,
    chin_z=230, chin_dx=80, top=[(950, 600, 140, 0), (720, 900, 200, 15), (-300, 1100, 80, 10), (-900, 1760, 260, 20), (-3600, 1770, 200, 10), (-3880, 1600, 120, 0), (-3950, 650, 100, 0), (-3860, 300, 50, 0)],
    H=1770, hdr=-900, cowl=-300, cowl_z=1100, belt=[(-600, 1100), (-3800, 1130)], c_bot=-750, c_top=-560, roof_t=80, a_w=90, dlo_r=50,
    pillars=((-1350, -1420, 100), (-2650, -2700, 100)), doors=((-300, -320, -10), (-1350, -1360, 0), (-2650, -2650, 0)),
    handles=((-1200, 1030), (-1500, 1030)), free_lines=([(-1400, 1180), (-3500, 1180)],),
    head=dict(pts=[(-300, 1000), (520, 1000), (520, 840), (-300, 760)]), tail_light=dict(pts=[(-300, 1500), (140, 1500), (140, 1050), (-300, 1050)]))
MICRO = dict(WB=1850, FO=480, RO=350, Rw=270, rim=0.6, rims='cap', clr=150,
    chin_z=200, chin_dx=40, top=[(480, 520, 120, 0), (380, 850, 160, 10), (-150, 1000, 60, 5), (-700, 1560, 220, 10), (-1950, 1560, 180, 0), (-2200, 1300, 80, 0), (-2200, 450, 80, 0), (-2120, 280, 40, 0)],
    H=1560, hdr=-700, cowl=-150, cowl_z=1000, belt=[(-600, 1000), (-2100, 1020)], c_bot=-40, c_top=-50, roof_t=70, a_w=80, dlo_r=50,
    doors=((-150, -150, -10), (-1500, -1500, 0)), handles=((-1350, 940),), head=dict(pts=[(-200, 840), (330, 840), (330, 690), (-200, 690)]),
    tail_light=dict(pts=[(-60, 1200), (120, 1200), (120, 950), (-60, 950)]))
KEI_TRUCK = dict(WB=1900, FO=400, RO=700, Rw=270, rim=0.6, rims='steel', clr=180,
    chin_z=250, chin_dx=30, top=[(400, 500, 60, 0), (380, 1100, 120, 0), (250, 1800, 140, 0), (-750, 1800, 80, 0), (-800, 1750, 40, 0), (-800, 900, 0, 0), (-2600, 900, 20, 0), (-2600, 450, 30, 0), (-2550, 320, 30, 0)],
    H=1800, hdr=250, cowl=380, cowl_z=1100, belt=[(-600, 1150), (500, 1150)], glass_upto=-720, c_bot=None, c_top=None, roof_t=70, a_w=60, dlo_r=40,
    doors=((370, 330, -10), (-760, -760, 0)), door_bot=400, handles=((-600, 1050),), head=dict(pts=[(-40, 760), (60, 760), (60, 560), (-40, 560)]),
    tail_light=dict(pts=[(-40, 860), (120, 860), (120, 640), (-40, 640)]), mirror_at=(330, 1250),
    free_lines=([(-800, 1180), (-2600, 1180)], [(-800, 1180), (-800, 900)], [(-2600, 1180), (-2600, 900)]) + tuple([(x, 900), (x, 1180)] for x in (-1400, -2000)))

# vintage cars: bodies with separate wings (fenders), running boards and lamps
def fenders(WB, Rw, front_x0=650, rear_x1=None, board_z=420, sweep=True):
    def f(sc, g):
        R = Rw + 90
        fx = 0; rx = -WB
        sc.geom(rpoly([(fx + R * 1.15, Rw * 0.9, 120), (fx + R * 0.5, Rw + R * 0.95, 220), (fx - R * 0.6, Rw + R * 0.85, 160), (fx - R * 1.3, board_z + 60, 60), (fx - R * 1.3, board_z, 0), (fx - R * 0.8, board_z, 0)]))
        sc.geom(rpoly([(rx + R * 1.2, board_z + 60, 60), (rx + R * 0.6, Rw + R * 0.9, 200), (rx - R * 0.7, Rw + R * 0.8, 180), (rx - R * 1.25, Rw * 0.7, 100), (rx - R * 1.0, Rw * 0.7, 0), (rx + R * 1.2, board_z, 0)]))
        sc.geom(zbox(fx - R * 1.3, board_z - 30, rx + R * 1.2, board_z + 40))
    return ('mid', 'fn', f)

def lamp(x, z, r=130):
    return ('front', 'fn', lambda sc, g: (sc.geom(ell(x, z, r * 0.55, r)), sc.line(ellipse(x + 10, z, r * 0.35, r * 0.7, n=20))))

def vintage_1910():
    WB, Rw = 2600, 420
    top = [(700, 900, 40, 0), (640, 1250, 40, 0), (-600, 1300, 40, 0), (-760, 1700, 20, 0), (-820, 1700, 20, 0), (-900, 1350, 40, 0), (-1500, 1450, 80, 0),
           (-2000, 2150, 120, 0), (-3100, 2200, 120, 0), (-3200, 1900, 60, 0), (-3300, 1350, 60, 0), (-3300, 800, 60, 0), (-3200, 650, 40, 0)]
    return dict(WB=WB, FO=700, RO=700, Rw=Rw, Rwr=420, rim=0.5, rims='artillery', clr=520, arch='none', gap=40,
        chin_z=800, chin_dx=0, chin_r=20, top=top, H=2200, hdr=-1500, cowl=-600, cowl_z=1300, no_glass=True, mirror=False,
        free_lines=([(-1500, 1450), (-1960, 2120)], [(-2500, 2180), (-2700, 1450)], [(-2050, 2160), (-2350, 1400)]) + tuple([(x, 1330), (x, 1200)] for x in np.arange(100, 600, 80)),
        ops=(fenders(WB, Rw, board_z=600), lamp(760, 1150, 110), ('front', 'line', [(-600, 1300), (-760, 1700)])))

def tourer_1920():
    WB, Rw = 3200, 420
    top = [(900, 800, 60, 0), (850, 1280, 60, 0), (-700, 1330, 40, 0), (-850, 1720, 20, 0), (-900, 1720, 20, 0), (-980, 1360, 40, 0), (-3700, 1380, 60, 0),
           (-4050, 1200, 120, 0), (-4100, 800, 80, 0), (-3950, 650, 40, 0)]
    return dict(WB=WB, FO=900, RO=900, Rw=Rw, rim=0.5, rims='wire', clr=480, arch='none',
        chin_z=700, chin_dx=0, chin_r=20, top=top, H=1720, hdr=-850, cowl=-700, cowl_z=1330, no_glass=True, mirror=False,
        free_lines=tuple([(x, 1300), (x, 1120)] for x in np.arange(-500, 700, 100)) + ([(-2200, 1360), (-2200, 1100)], [(-1300, 1360), (-1300, 1000)]),
        ops=(fenders(WB, Rw, board_z=560), lamp(980, 1180, 120), ('front', 'fn', lambda sc, g: (sc.geom(ring(-WB - 1000, 1100, 420)), sc.line(circle(-WB - 1000, 1100, 220))))))

def saloon_1930():
    WB, Rw = 3000, 400
    top = [(900, 800, 80, 0), (850, 1250, 100, 10), (-600, 1350, 80, 0), (-1100, 1900, 220, 20), (-3200, 1950, 300, 20), (-3800, 1500, 300, 30), (-3950, 900, 120, 0), (-3850, 650, 40, 0)]
    return dict(WB=WB, FO=900, RO=950, Rw=Rw, rim=0.55, rims='whitewall', clr=420, arch='none',
        chin_z=700, chin_dx=0, top=top, H=1950, hdr=-1100, cowl=-600, cowl_z=1350, belt=[(-600, 1360), (-3500, 1400)], c_bot=-500, c_top=-180, roof_t=90, a_w=90, dlo_r=60,
        pillars=((-1700, -1750, 90),), doors=((-620, -620, 0), (-1720, -1720, 0)), door_bot=650, handles=((-1550, 1250), (-1900, 1250)), mirror=False,
        free_lines=tuple([(x, 1240), (x, 1080)] for x in np.arange(-400, 700, 110)),
        ops=(fenders(WB, Rw, board_z=560), lamp(950, 1200, 140)))

FINS_1950 = dict(WB=3100, FO=1100, RO=1500, Rw=360, rim=0.6, rims='whitewall', clr=170, arch='skirt', archr='skirt', gap=60,
    chin_z=260, chin_dx=60, top=[(1100, 650, 120, 0), (1050, 900, 120, 0), (-700, 980, 80, 0), (-1000, 1400, 150, 10), (-2400, 1420, 200, 10), (-3000, 1000, 120, 0),
                               (-4400, 1050, 40, 0), (-4650, 1250, 20, 0), (-4600, 700, 80, 0), (-4500, 350, 50, 0)],
    H=1420, hdr=-1000, cowl=-700, cowl_z=980, belt=[(-600, 990), (-3000, 1000)], c_bot=-100, c_top=500, roof_t=70, a_w=90, dlo_r=40,
    pillars=((-1800, -1800, 70),), doors=((-700, -700, 0), (-2100, -2100, 0)), handles=((-1950, 900),),
    lines=([(1000, 780), (-4500, 800)], [(-1000, 560), (-3400, 560), (-3000, 800)]),
    head=dict(pts=[(-60, 880), (120, 880), (120, 700), (-60, 700)]), tail_light=dict(pts=[(-40, 1200), (300, 1100), (300, 950), (-40, 950)]))
COMPACT_1960 = dict(WB=2400, FO=750, RO=850, Rw=300, rim=0.58, rims='cap', clr=170,
    chin_z=250, chin_dx=40, top=[(750, 520, 60, 0), (740, 800, 60, 0), (-500, 860, 40, 0), (-750, 1380, 60, 0), (-2100, 1380, 60, 0), (-2400, 900, 40, 0), (-3250, 880, 40, 0), (-3250, 400, 50, 0), (-3180, 300, 40, 0)],
    H=1380, hdr=-750, cowl=-500, cowl_z=860, belt=[(-600, 870), (-2400, 890)], c_bot=-0, c_top=300, roof_t=60, a_w=60, dlo_r=30,
    pillars=((-1500, -1500, 60),), doors=((-500, -500, 0), (-1520, -1520, 0)), handles=((-1400, 800),),
    lines=([(740, 640), (-3250, 660)],), head=dict(pts=[(-40, 780), (60, 780), (60, 560), (-40, 560)]), tail_light=dict(pts=[(-40, 860), (80, 860), (80, 640), (-40, 640)]))
WAGON_1970 = dict(WB=3000, FO=1050, RO=1350, Rw=340, rim=0.6, rims='steel', clr=180,
    chin_z=260, chin_dx=60, top=[(1050, 560, 80, 0), (1020, 880, 80, 0), (-650, 960, 40, 0), (-1050, 1450, 80, 0), (-4200, 1470, 60, 0), (-4330, 1350, 40, 0), (-4350, 400, 60, 0), (-4250, 300, 40, 0)],
    H=1470, hdr=-1050, cowl=-650, cowl_z=960, belt=[(-600, 980), (-4300, 990)], c_bot=-1150, c_top=-1180, roof_t=70, a_w=80, dlo_r=30,
    pillars=((-1800, -1800, 80), (-3100, -3100, 80)), doors=((-650, -650, 0), (-1800, -1800, 0)), rear_arch_door=(300, 50, 150), handles=((-1650, 900), (-2800, 900)),
    outlines=([(800, 900, 0), (-4250, 900, 0), (-4250, 420, 0), (800, 420, 0)],), lines=([(800, 860), (-4250, 860)], [(800, 460), (-4250, 460)]),
    head=dict(pts=[(-40, 820), (80, 820), (80, 600), (-40, 600)]), tail_light=dict(pts=[(-40, 900), (80, 900), (80, 700), (-40, 700)]),
    ops=(('front', 'fn', lambda sc, g: sc.geom(rails(-1300, -4000, g, h=60, t=36))),))
CAMPER = dict(WB=2400, FO=500, RO=1300, Rw=330, rim=0.6, rims='cap', clr=200,
    chin_z=300, chin_dx=20, top=[(500, 550, 120, 0), (550, 1300, 260, 20), (300, 1950, 300, 10), (-3500, 1950, 300, 10), (-3700, 1400, 200, 0), (-3700, 450, 80, 0), (-3620, 320, 40, 0)],
    H=1950, hdr=300, cowl=520, cowl_z=1300, belt=[(-600, 1330), (600, 1330), (-3700, 1330)], c_bot=-900, c_top=-950, roof_t=90, a_w=80, dlo_r=60,
    pillars=((-450, -450, 120), (-1500, -1500, 100), (-2400, -2400, 100)), doors=((380, 380, 0), (-450, -450, 0)), handles=((-300, 1200),),
    lines=([(500, 1100), (-3700, 1100)],), head=dict(pts=[(0, 950), (120, 950), (120, 780), (0, 780)]), tail_light=dict(pts=[(-40, 1000), (80, 1000), (80, 800), (-40, 800)]),
    ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(-400, 1950, 0), (-3300, 1950, 0), (-3200, 2250, 60), (-500, 2250, 60)])), sc.lines([[(x, 1980), (x, 2220)] for x in np.arange(-700, -3100, -400)]))),))
ICE_CREAM = V(PANEL_VAN, ops=(('front', 'fn', lambda sc, g: (sc.geom(zbox(-3000, 1350, -1900, 2050, 40), fill=False), sc.geom(zbox(-3050, 1300, -1850, 1350)),
    sc.geom(Polygon([(-2500, 2430), (-2350, 2430), (-2425, 2150)])), sc.geom(Point(-2425, 2520).buffer(130)), sc.lines(ztext('ICE CREAM', -2450, 1500, 160, 'HersheySansMed')))),))
def tow_truck():
    p = V(PANEL_VAN, top=[(820, 760, 90, 0), (650, 1080, 150, 10), (-200, 1330, 60, 8), (-900, 2350, 220, 10), (-1700, 2380, 80, 0), (-1800, 2300, 40, 0), (-1800, 1000, 0, 0),
                          (-4500, 1000, 30, 0), (-4500, 450, 60, 0), (-4420, 300, 40, 0)], free_lines=(), glass_upto=-1600, rims='6', Rw=380)
    def boom(sc, g):
        sc.geom(LineString([(-2200, 1050), (-4200, 2100)]).buffer(110, cap_style=2))
        sc.geom(zbox(-2400, 1000, -2000, 1400, 20))
        sc.line([(-4200, 2100), (-4200, 1300)])
        sc.line([(-4200, 1300), (-4280, 1180), (-4200, 1060), (-4120, 1150)])
        sc.geom(zbox(-1750, 2380, -1250, 2480, 40))
    p['ops'] = (('front', 'fn', boom),)
    return p
BUGGY = dict(WB=2100, FO=600, RO=550, Rw=360, Rwr=420, rim=0.55, rims='steel', tread=8, clr=320, arch='none',
    chin_z=450, chin_dx=20, top=[(600, 650, 120, 0), (400, 950, 200, 10), (-500, 1050, 40, 0), (-900, 1000, 40, 0), (-2300, 1000, 60, 0), (-2650, 800, 80, 0), (-2650, 550, 60, 0), (-2550, 450, 40, 0)],
    H=1050, hdr=-500, cowl=-500, cowl_z=1050, no_glass=True, mirror=False,
    ops=(('front', 'fn', lambda sc, g: sc.geom(LineString([(-1100, 1000), (-1000, 1900), (-1900, 1900), (-2000, 1000)]).buffer(40, join_style=1))),
         ('front', 'fn', lambda sc, g: sc.geom(LineString([(-500, 1050), (-700, 1500)]).buffer(30))),))
GOLF_CART = dict(WB=1650, FO=350, RO=400, Rw=230, rim=0.55, rims='cap', clr=150, arch='none',
    chin_z=200, chin_dx=20, top=[(350, 500, 80, 0), (300, 750, 100, 0), (-500, 800, 40, 0), (-700, 900, 20, 0), (-1900, 900, 40, 0), (-2050, 700, 40, 0), (-2050, 350, 40, 0)],
    H=900, hdr=-500, cowl=-500, cowl_z=800, no_glass=True, mirror=False,
    ops=(('front', 'fn', lambda sc, g: (sc.geom(zbox(-400, 1850, -1950, 1950, 30)), sc.geom(LineString([(-450, 800), (-450, 1850)]).buffer(30)),
          sc.geom(LineString([(-1900, 900), (-1900, 1850)]).buffer(30)), sc.geom(zbox(-1500, 900, -1100, 1350, 60)), sc.geom(zbox(-1980, 950, -1700, 1600, 40)))),))
GO_KART = dict(WB=1050, FO=350, RO=250, Rw=140, Rwr=150, rim=0.5, rims='kart', clr=40, arch='none',
    chin_z=80, chin_dx=10, top=[(350, 130, 30, 0), (300, 200, 30, 0), (-300, 230, 20, 0), (-1300, 230, 20, 0), (-1300, 100, 20, 0)],
    H=230, hdr=-300, cowl=-300, cowl_z=230, no_glass=True, mirror=False,
    ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(-600, 230, 0), (-900, 230, 0), (-950, 620, 60), (-820, 640, 40), (-750, 300, 30)])),
          sc.geom(LineString([(-150, 230), (-350, 560)]).buffer(18)), sc.geom(ell(-360, 570, 130, 30, 0.6)), sc.geom(zbox(-1250, 230, -1000, 420, 30)))),))
LIMO = V(SALOON, WB=4300, RO=1100, pillars=((-1590, -1640, 95), (-2900, -2950, 95)), doors=((-480, -470, -20), (-1560, -1590, 0), (-2880, -2900, 0)),
    rear_arch_door=(80, 55, 150), handles=((-1380, 900), (-2700, 920), (-3800, 935)), belt=[(-600, 985), (-3500, 1030), (-4200, 1075)],
    lines=([(600, 730), (-1000, 880), (-4500, 950), (-5290, 960)],), rims='multi')
CONVERTIBLE = V(SALOON, WB=2700, H=1180, hdr=-700, roof_fr=40, roof_b=0, roof_rx=-400, roof_rz=1100, roof_rr=60, gl_b=0, no_glass=True,
    deck_x=900, deck_z=1060, tail_z=1050, pillars=(), doors=((-480, -470, -20), (-1700, -1700, 0)), rear_arch_door=None, handles=((-1550, 900),),
    ops=(('front', 'fn', lambda sc, g: (sc.geom(LineString([(-480, 1000), (-760, 1300), (-900, 1290)]).buffer(28)), sc.geom(zbox(-1700, 1000, -1350, 1250, 80), fill=False),
          sc.geom(zbox(-2300, 1000, -1950, 1250, 80), fill=False), sc.geom(rpoly([(-2600, 1000, 0), (-3300, 1000, 0), (-3200, 1150, 60), (-2700, 1150, 60)])))),))
COUPE = V(SALOON, WB=2700, H=1380, hdr=-1250, roof_rx=200, roof_rz=1350, roof_rr=500, deck_x=500, deck_z=1060, c_bot=-150, c_top=420,
    pillars=(), doors=((-480, -470, -20), (-1950, -1990, 0)), rear_arch_door=None, handles=((-1800, 920),),
    belt=[(-600, 985), (-2000, 1020), (-2600, 1060)])

# ---------------------------------------------------------------- sports cars (side views): explicit outlines
def sports(top, H, WB=2650, FO=1000, RO=1050, Rw=340, Rwr=None, rim=0.72, rims='5', clr=110, cowl=-600, cowl_z=880, hdr=None,
           belt=None, c_bot=None, c_top=None, roof_t=60, a_w=70, doors=None, handles=None, head=None, tail=None, ops=(), lines=(),
           no_glass=False, chin=(90, 160), pillars=(), flare=0, arch='round', gap=30, mirror=True, mirror_at=None, free_lines=(), dlo_r=40, outlines=(), **k):
    d = dict(WB=WB, FO=FO, RO=RO, Rw=Rw, Rwr=Rwr, rim=rim, rims=rims, clr=clr, chin_z=chin[1], chin_dx=chin[0], top=top, H=H,
             hdr=hdr if hdr is not None else cowl - 700, cowl=cowl, cowl_z=cowl_z, belt=belt or [(-600, cowl_z + 20), (-WB - RO, cowl_z + 80)],
             c_bot=c_bot, c_top=c_top, roof_t=roof_t, a_w=a_w, doors=doors or ((cowl, cowl - 30, -10), (cowl - 1250, cowl - 1250, 0)),
             handles=handles or ((cowl - 1100, cowl_z - 80),), head=head, tail_light=tail, ops=ops, lines=lines, no_glass=no_glass,
             pillars=pillars, flare=flare, arch=arch, gap=gap, mirror=mirror, mirror_at=mirror_at, free_lines=free_lines, dlo_r=dlo_r, outlines=outlines)
    d.update(k)
    return d

def wing(x0, x1, z, post=250, chord=420):
    def f(sc, g):
        sc.geom(rpoly([(x0, z, 30), (x1, z + 30, 30), (x1 - 20, z + 120, 30), (x0 + 30, z + 90, 30)]))
        sc.geom(zbox(x1 - 40, z - 80, x1 + 30, z + 200, 10))
        for x in (x0 + 120, x1 - 160):
            base = top_z(g, x) or z - post
            sc.geom(LineString([(x, base - 20), (x + 40, z + 20)]).buffer(28))
    return ('front', 'fn', f)

def number_roundel(x, z, n, r=260):
    return ('front', 'fn', lambda sc, g: (sc.geom(ring(x, z, r), fill=False), sc.lines(ztext(str(n), x, z - r * 0.45, r * 0.9, 'HersheySansMed'))))

def scoop(x, z, w=500, h=160):
    return ('front', 'fn', lambda sc, g: sc.geom(rpoly([(x - w / 2, z - 30, 0), (x + w / 2, z - 30, 0), (x + w / 2 - 60, z + h, 40), (x - w / 2 + 60, z + h * 0.8, 40)])))

def side_vents(x, z, n=4, w=420, dz=55):
    return ('front', 'lines', [[(x - w / 2 + i * 25, z - i * dz), (x + w / 2 + i * 25, z - i * dz)] for i in range(n)])

WEDGE = [(1000, 450, 40, 0), (950, 560, 60, 0), (-400, 900, 60, 0), (-1300, 1130, 140, 5), (-2300, 1130, 120, 0), (-3500, 1000, 60, 0), (-3700, 980, 30, 0), (-3700, 500, 60, 0), (-3600, 300, 40, 0)]
GT = [(1050, 420, 120, 0), (900, 680, 220, 20), (-700, 880, 80, 5), (-1500, 1280, 260, 20), (-2600, 1230, 380, 30), (-3500, 900, 200, 10), (-3700, 780, 80, 0), (-3720, 450, 80, 0), (-3600, 300, 40, 0)]
ROADSTER50 = [(1000, 450, 160, 0), (900, 820, 260, 30), (-800, 900, 60, 0), (-1000, 1150, 20, 0), (-1080, 1150, 20, 0), (-1200, 900, 40, 0), (-2300, 920, 120, 0), (-3200, 900, 260, 30), (-3550, 600, 120, 0), (-3450, 330, 50, 0)]
HYPER = [(1050, 380, 60, 0), (980, 520, 160, 15), (-300, 860, 100, 10), (-1100, 1150, 260, 15), (-2200, 1120, 300, 10), (-3550, 960, 80, 0), (-3650, 900, 30, 0), (-3650, 450, 60, 0), (-3550, 280, 40, 0)]
MUSCLE = [(1100, 500, 60, 0), (1080, 900, 60, 0), (-900, 980, 40, 0), (-1500, 1360, 160, 10), (-2400, 1340, 200, 5), (-3600, 1000, 60, 0), (-4100, 990, 40, 0), (-4120, 500, 60, 0), (-4000, 330, 40, 0)]

def sportscars():
    S = []
    def add(name, p, slug): S.append((name, p, slug))
    add('Wedge mid-engine supercar', sports(WEDGE, 1130, cowl=-500, cowl_z=860, hdr=-1300, belt=[(-600, 900), (-3700, 1000)], c_bot=-400, c_top=-100,
        doors=((-480, -520, -10), (-2100, -2150, 0)), handles=((-1900, 820),), rims='5', rim=0.72, Rwr=360,
        head=dict(pts=[(-300, 600), (200, 600), (200, 520), (-300, 500)]), tail=dict(pts=[(-40, 960), (200, 960), (200, 820), (-40, 820)]),
        ops=(side_vents(-2400, 780, 4),)), 'wedge-supercar')
    add('Retro wedge with pop-up headlights', sports(WEDGE, 1100, cowl=-500, cowl_z=860, hdr=-1300, belt=[(-600, 900), (-3700, 1000)], c_bot=-500, c_top=-200, rims='turbine',
        doors=((-480, -520, -10), (-2100, -2150, 0)), handles=((-1900, 820),),
        ops=(('front', 'fn', lambda sc, g: sc.geom(rpoly([(150, 580, 0), (650, 520, 0), (600, 700, 30), (180, 760, 30)]))),),
        tail=dict(pts=[(-40, 960), (120, 960), (120, 760), (-40, 760)], lines=[[(0, 900), (120, 900)], [(0, 840), (120, 840)]])), 'retro-wedge')
    add('Long-bonnet grand tourer', sports(GT, 1280, cowl=-700, cowl_z=880, hdr=-1500, belt=[(-600, 900), (-3700, 960)], c_bot=-700, c_top=-50, rims='wire', rim=0.7,
        doors=((-700, -720, -10), (-2000, -2050, 0)), handles=((-1850, 830),), head=dict(pts=[(-300, 640), (180, 640), (180, 480), (-300, 480)]),
        tail=dict(pts=[(-40, 860), (220, 860), (220, 700), (-40, 700)]), ops=(side_vents(-150, 660, 3, w=300),)), 'long-bonnet-gt')
    add('1950s roadster', sports(ROADSTER50, 1150, cowl=-800, cowl_z=900, hdr=-1000, no_glass=True, rims='wire', rim=0.66, Rw=330, clr=150,
        doors=((-850, -870, -10), (-1950, -1950, 0)), handles=((-1800, 820),), head=dict(pts=[(-40, 760), (120, 760), (120, 560), (-40, 560)]),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(LineString([(-1250, 920), (-1500, 1050), (-1650, 1060)]).buffer(30)), sc.geom(ell(-1750, 1000, 160, 90)))),)), 'roadster-1950s')
    add('1960s grand tourer', sports([(1000, 480, 140, 0), (950, 760, 200, 15), (-700, 900, 60, 5), (-1300, 1250, 200, 10), (-2100, 1240, 600, 20), (-3500, 820, 120, 0), (-3600, 720, 40, 0), (-3600, 420, 60, 0), (-3500, 320, 40, 0)],
        1250, cowl=-700, cowl_z=900, hdr=-1300, rims='wire', rim=0.68, Rw=330, belt=[(-600, 920), (-3500, 900)], c_bot=-300, c_top=300,
        doors=((-700, -720, -10), (-1900, -1950, 0)), handles=((-1750, 840),), head=dict(pts=[(-60, 780), (150, 780), (150, 560), (-60, 560)]),
        tail=dict(pts=[(-40, 760), (150, 760), (150, 640), (-40, 640)]), ops=(side_vents(-150, 700, 3, w=260),)), 'gt-1960s')
    add('Targa with the roof panel off', sports(GT, 1250, cowl=-650, cowl_z=880, hdr=-1350, rims='5', belt=[(-600, 900), (-3700, 960)], c_bot=-250, c_top=-220, rim=0.72,
        doors=((-650, -670, -10), (-1950, -2000, 0)), handles=((-1800, 830),), head=dict(pts=[(-300, 640), (180, 640), (180, 480), (-300, 480)]),
        ops=(('front', 'cut', zbox(-1700, 1180, -2100, 1300)), ('front', 'fn', lambda sc, g: sc.geom(rpoly([(-2050, 920, 0), (-2400, 920, 0), (-2400, 1240, 60), (-2100, 1260, 60)])))),
        tail=dict(pts=[(-40, 860), (220, 860), (220, 700), (-40, 700)])), 'targa')
    S_CONV = sports([(1000, 450, 140, 0), (930, 700, 200, 15), (-700, 860, 60, 5), (-1300, 1180, 200, 10), (-2400, 1150, 400, 20), (-3400, 880, 160, 0), (-3550, 760, 40, 0), (-3550, 420, 60, 0), (-3450, 300, 40, 0)],
        1180, cowl=-700, cowl_z=860, hdr=-1300, rims='twin5', belt=[(-600, 880), (-3500, 900)], c_bot=-250, c_top=200, rim=0.72,
        doors=((-700, -720, -10), (-1950, -2000, 0)), handles=((-1800, 800),), head=dict(pts=[(-300, 640), (180, 640), (180, 500), (-300, 500)]),
        tail=dict(pts=[(-40, 840), (200, 840), (200, 700), (-40, 700)]))
    add('Convertible sports car, roof up', V(S_CONV, outlines=([(-1300, 1170, 0), (-2400, 1140, 0), (-2400, 900, 0), (-1300, 900, 0)],)), 'convertible-roof-up')
    add('Convertible sports car, roof down', V(S_CONV, top=[(1000, 450, 140, 0), (930, 700, 200, 15), (-700, 860, 60, 5), (-3400, 880, 160, 0), (-3550, 760, 40, 0), (-3550, 420, 60, 0), (-3450, 300, 40, 0)],
        H=880, hdr=-700, no_glass=True, ops=(('front', 'fn', lambda sc, g: (sc.geom(LineString([(-700, 860), (-1000, 1150), (-1150, 1150)]).buffer(26)),
            sc.geom(rpoly([(-1500, 880, 0), (-1800, 880, 0), (-1780, 1130, 60), (-1560, 1140, 60)])), sc.geom(rpoly([(-2300, 880, 0), (-2900, 880, 0), (-2800, 1000, 60), (-2350, 1000, 60)])))),)), 'convertible-roof-down')
    add('Hypercar with a big rear wing', sports(HYPER, 1150, cowl=-400, cowl_z=840, hdr=-1150, Rw=355, Rwr=375, rims='lock', rim=0.74, belt=[(-600, 880), (-3600, 980)], c_bot=-500, c_top=-50,
        doors=((-380, -420, -10), (-2000, -2050, 0)), handles=((-1800, 800),), head=dict(pts=[(-200, 560), (240, 560), (240, 470), (-200, 450)]),
        tail=dict(pts=[(-40, 900), (150, 900), (150, 820), (-40, 820)]), ops=(wing(-3800, -3000, 1450), side_vents(-2300, 700, 3, w=500, dz=70))), 'hypercar-wing')
    add('Electric hypercar', sports(HYPER, 1120, cowl=-400, cowl_z=840, hdr=-1150, Rw=350, rims='aero', rim=0.76, belt=[(-600, 880), (-3600, 960)], c_bot=-450, c_top=-100,
        doors=((-380, -420, -10), (-2000, -2050, 0)), handles=(), mirror_at=(-450, 930), mirror_s=0.7,
        head=dict(pts=[(-500, 520), (250, 540), (250, 500), (-500, 490)]), tail=dict(pts=[(-40, 930), (500, 920), (500, 890), (-40, 900)])), 'electric-hypercar')
    add('GT race car with a number', sports(GT, 1250, cowl=-650, cowl_z=880, hdr=-1350, Rw=360, rims='gt3', rim=0.76, clr=80, belt=[(-600, 900), (-3700, 960)], c_bot=-250, c_top=-50, flare=70,
        doors=((-650, -670, -10), (-1950, -2000, 0)), handles=(), chin=(60, 120),
        head=dict(pts=[(-300, 640), (180, 640), (180, 480), (-300, 480)]), ops=(wing(-3900, -3200, 1400), number_roundel(-1350, 650, 27), ('front', 'line', [(1060, 150), (700, 150)]))), 'gt-race-car')
    add('Le Mans-style prototype', sports([(1100, 300, 60, 0), (1000, 480, 200, 10), (-200, 760, 60, 0), (-900, 1080, 260, 10), (-1800, 1060, 200, 0), (-2600, 1150, 40, 0), (-3700, 1150, 60, 0), (-3800, 950, 40, 0), (-3800, 400, 40, 0), (-3700, 250, 40, 0)],
        1100, cowl=-300, cowl_z=780, hdr=-950, WB=2800, Rw=345, rims='lock', rim=0.76, clr=70, arch='round', gap=20, belt=[(-600, 820), (-1900, 840)], glass_from=-200, glass_upto=-1800,
        doors=((-300, -330, -10), (-1700, -1700, 0)), handles=(), head=dict(pts=[(-300, 450), (200, 450), (200, 400), (-300, 380)]), mirror_at=(-150, 820),
        ops=(wing(-3900, -3100, 1300), number_roundel(-2400, 650, 8), ('front', 'fn', lambda sc, g: sc.geom(rpoly([(-1700, 1050, 0), (-3200, 1150, 0), (-3200, 1400, 40), (-2400, 1200, 40)]))))), 'le-mans-prototype')
    add('Rally car with a roof scoop', sports([(900, 500, 60, 0), (850, 820, 120, 10), (-500, 960, 40, 0), (-1200, 1420, 120, 5), (-2200, 1420, 100, 0), (-2600, 1300, 60, 0), (-2900, 1000, 60, 0), (-3100, 960, 40, 0), (-3100, 450, 60, 0), (-3000, 330, 40, 0)],
        1420, WB=2500, FO=900, RO=600, Rw=330, rims='steel', rim=0.62, clr=200, cowl=-500, cowl_z=960, hdr=-1200, belt=[(-600, 990), (-3000, 1030)], c_bot=200, c_top=-50, flare=50,
        doors=((-500, -500, -10), (-1700, -1700, 0)), handles=((-1550, 900),), head=dict(pts=[(-40, 800), (100, 800), (100, 620), (-40, 620)]),
        ops=(scoop(-1500, 1430, 400, 150), number_roundel(-1100, 650, 4), wing(-3200, -2600, 1300, chord=300),
             ('front', 'fn', lambda sc, g: (sc.geom(zbox(-2850, 120, -2750, 520)), sc.geom(zbox(-150, 120, -50, 520)))),
             ('front', 'fn', lambda sc, g: [sc.geom(ring(x, 760, 90), fill=False) for x in (870, 870)]))), 'rally-car')
    add('Drag racer', sports([(1800, 250, 40, 0), (1700, 330, 40, 0), (-1500, 650, 100, 0), (-2000, 1050, 120, 0), (-2600, 1050, 80, 0), (-2900, 800, 60, 0), (-3300, 800, 40, 0), (-3300, 450, 40, 0), (-3200, 300, 40, 0)],
        1050, WB=3000, FO=1800, RO=300, Rw=200, Rwr=520, rim=0.5, rims='5', rimsr='dish', clr=60, cowl=-1500, cowl_z=650, hdr=-2000, no_glass=True, mirror=False, arch='none',
        doors=((-1500, -1500, 0), (-1500, -1500, 0)), handles=(), ops=(wing(-3700, -3100, 1700), ('front', 'fn', lambda sc, g: sc.geom(LineString([(-3300, 300), (-4400, 200)]).buffer(25))),
        ('front', 'fn', lambda sc, g: sc.geom(ring(-4400, 180, 70))), ('front', 'fn', lambda sc, g: sc.geom(rpoly([(-1600, 650, 0), (-2000, 650, 0), (-1950, 1100, 80), (-1700, 1150, 60)]))))), 'drag-racer')
    add('Hot rod with an exposed engine', sports([(900, 600, 40, 0), (850, 800, 40, 0), (-200, 820, 40, 0), (-600, 1000, 20, 0), (-700, 1350, 60, 0), (-2000, 1350, 80, 0), (-2300, 1000, 60, 0), (-2900, 950, 60, 0), (-3000, 600, 60, 0), (-2900, 420, 40, 0)],
        1350, WB=2500, FO=900, RO=500, Rw=330, Rwr=420, rim=0.55, rims='dish', clr=200, cowl=-600, cowl_z=1000, hdr=-700, arch='none', belt=[(-600, 1040), (-2400, 1040)], c_bot=500, c_top=550,
        doors=((-600, -600, 0), (-1700, -1700, 0)), handles=((-1550, 960),),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(-450, 800, 0), (500, 800, 0), (480, 1150, 60), (-430, 1150, 60)])), sc.lines([[(x, 830), (x, 1120)] for x in range(-350, 450, 100)]),
             sc.geom(zbox(-200, 1150, 200, 1350, 40)), [sc.geom(LineString([(x, 850), (x - 300, 500)]).buffer(30)) for x in (-200, 0)], sc.geom(ring(870, 900, 110), fill=False))),)), 'hot-rod')
    add('Muscle car with stripes', sports(MUSCLE, 1360, WB=2800, FO=1100, RO=1300, Rw=350, rims='5', rim=0.66, cowl=-900, cowl_z=980, hdr=-1500, belt=[(-600, 1000), (-4100, 1020)], c_bot=-200, c_top=300,
        doors=((-900, -900, 0), (-2150, -2150, 0)), handles=((-2000, 920),), head=dict(pts=[(-40, 860), (100, 860), (100, 640), (-40, 640)]),
        ops=(scoop(-200, 990, 600, 120), stripe([(1100, 600), (-4100, 700)], 90), stripe([(1100, 760), (-4100, 860)], 40))), 'muscle-car')
    add('Drift car with wide arches', sports([(1050, 400, 60, 0), (1000, 600, 120, 10), (-600, 880, 60, 0), (-1300, 1280, 200, 10), (-2400, 1280, 200, 5), (-3400, 960, 80, 0), (-3600, 940, 40, 0), (-3650, 450, 60, 0), (-3550, 280, 40, 0)],
        1280, Rw=345, rims='multi', rim=0.74, clr=70, flare=110, flare_lo=0.05, cowl=-600, cowl_z=880, hdr=-1300, belt=[(-600, 900), (-3600, 980)], c_bot=-300, c_top=100,
        doors=((-600, -620, -10), (-1900, -1950, 0)), handles=((-1750, 830),), head=dict(pts=[(-300, 560), (200, 560), (200, 470), (-300, 470)]),
        ops=(wing(-3800, -3100, 1350), ('front', 'line', [(1060, 160), (600, 160)]))), 'drift-car')
    add('Shooting brake', sports([(1050, 420, 120, 0), (900, 680, 220, 20), (-700, 880, 80, 5), (-1500, 1280, 260, 20), (-3400, 1260, 160, 0), (-3700, 950, 120, 0), (-3720, 450, 80, 0), (-3600, 300, 40, 0)],
        1280, cowl=-700, cowl_z=880, hdr=-1500, belt=[(-600, 900), (-3700, 940)], c_bot=-900, c_top=-1050, rims='twin5', rim=0.72, pillars=((-2000, -2050, 90),),
        doors=((-700, -720, -10), (-2000, -2050, 0)), handles=((-1850, 830),), head=dict(pts=[(-300, 640), (180, 640), (180, 480), (-300, 480)]),
        tail=dict(pts=[(-40, 900), (160, 900), (160, 720), (-40, 720)])), 'shooting-brake')
    add('Track-day car with a roll hoop', sports([(900, 420, 60, 0), (850, 600, 100, 10), (-700, 820, 40, 0), (-2900, 900, 120, 0), (-3200, 700, 60, 0), (-3200, 400, 40, 0), (-3100, 280, 40, 0)],
        900, WB=2400, FO=900, RO=800, Rw=320, rims='gt3', rim=0.72, clr=90, cowl=-700, cowl_z=820, hdr=-800, no_glass=True, mirror=False,
        doors=((-700, -700, 0), (-700, -700, 0)), handles=(),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(LineString([(-1500, 880), (-1600, 1350), (-2000, 1350), (-2100, 880)]).buffer(40, join_style=1)),
             sc.geom(LineString([(-700, 820), (-950, 1050)]).buffer(25)), sc.geom(ell(-1800, 1000, 170, 90)))), wing(-3500, -2900, 1150))), 'track-day-car')
    add('Open-wheel race car', sports([(1600, 250, 40, 0), (1500, 400, 60, 0), (-300, 600, 60, 0), (-700, 820, 40, 0), (-1500, 900, 120, 0), (-2600, 650, 60, 0), (-3200, 600, 40, 0), (-3200, 300, 40, 0)],
        900, WB=3500, FO=1600, RO=500, Rw=330, Rwr=345, rims='lock', rim=0.62, clr=40, arch='none', no_glass=True, mirror=False, cowl=-700, cowl_z=820, hdr=-700,
        doors=((-700, -700, 0), (-700, -700, 0)), handles=(),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(1500, 80, 20), (2100, 80, 20), (2100, 330, 20), (1500, 300, 20)])), sc.geom(ell(-1000, 980, 150, 130)), sc.line(ellipse(-960, 990, 100, 40, n=16)))),
             wing(-4000, -3300, 1100))), 'open-wheel-race-car')
    add('1950s racing roadster', sports([(1000, 450, 160, 0), (900, 760, 260, 30), (-800, 860, 60, 0), (-1300, 860, 40, 0), (-2000, 1150, 200, 0), (-2400, 1100, 200, 0), (-3300, 860, 260, 30), (-3550, 600, 120, 0), (-3450, 330, 50, 0)],
        1150, cowl=-800, cowl_z=860, hdr=-1300, no_glass=True, rims='wire', rim=0.66, Rw=330, clr=130, mirror=False, doors=((-800, -800, 0), (-800, -800, 0)), handles=(),
        ops=(number_roundel(-500, 560, 22), ('front', 'fn', lambda sc, g: sc.geom(LineString([(-1050, 870), (-1200, 1000)]).buffer(25))))), 'racing-roadster-1950s')
    add('1970s fastback coupe', sports([(1050, 500, 60, 0), (1030, 760, 60, 0), (-700, 900, 40, 0), (-1300, 1280, 140, 5), (-1900, 1290, 300, 10), (-3400, 960, 60, 0), (-3650, 940, 30, 0), (-3650, 450, 60, 0), (-3550, 320, 40, 0)],
        1290, cowl=-700, cowl_z=900, hdr=-1300, rims='slot', rim=0.64, belt=[(-600, 920), (-3600, 960)], c_bot=-300, c_top=350, Rw=330,
        doors=((-700, -700, 0), (-2000, -2000, 0)), handles=((-1850, 840),), head=dict(pts=[(-40, 720), (120, 720), (120, 560), (-40, 560)]),
        ops=(('front', 'lines', [[(-2200 - i * 90, 1200 - i * 40), (-2600 - i * 90, 1000 - i * 40)] for i in range(5)]),)), 'fastback-1970s')
    add('Small modern roadster', sports([(900, 480, 120, 0), (820, 700, 200, 15), (-700, 860, 60, 5), (-850, 1120, 20, 0), (-950, 1120, 20, 0), (-1100, 880, 40, 0), (-2900, 900, 200, 10), (-3100, 700, 80, 0), (-3100, 420, 60, 0), (-3000, 300, 40, 0)],
        1120, WB=2300, FO=900, RO=800, Rw=315, rims='6', rim=0.7, clr=120, cowl=-700, cowl_z=860, hdr=-900, no_glass=True,
        doors=((-700, -720, -10), (-1700, -1700, 0)), handles=((-1550, 800),), head=dict(pts=[(-200, 640), (180, 640), (180, 520), (-200, 520)]),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(ell(-1600, 960, 180, 110)), sc.geom(LineString([(-1800, 900), (-1950, 1080)]).buffer(30)))),)), 'small-roadster')
    add('Mid-engine targa, 1970s', sports([(950, 450, 60, 0), (900, 600, 80, 0), (-500, 870, 60, 0), (-1200, 1130, 120, 0), (-1900, 1140, 60, 0), (-2000, 1120, 0, 0), (-3300, 1000, 60, 0), (-3500, 980, 30, 0), (-3500, 450, 60, 0), (-3400, 300, 40, 0)],
        1140, cowl=-500, cowl_z=870, hdr=-1200, rims='4', rim=0.66, belt=[(-600, 900), (-3500, 990)], c_bot=-100, c_top=550, Rw=330,
        doors=((-500, -520, -10), (-2000, -2000, 0)), handles=((-1850, 820),), head=dict(pts=[(-300, 600), (200, 600), (200, 520), (-300, 500)]),
        ops=(('front', 'cut', zbox(-1300, 1060, -1850, 1200)), ('front', 'line', [(-1850, 1140), (-3000, 1020)]))), 'mid-engine-targa-1970s')
    add('Front-engine coupe, 1960s', sports([(1150, 480, 160, 0), (1050, 760, 250, 20), (-900, 900, 60, 5), (-1400, 1230, 200, 10), (-2200, 1220, 400, 20), (-3300, 860, 120, 0), (-3450, 760, 40, 0), (-3450, 420, 60, 0), (-3350, 320, 40, 0)],
        1230, WB=2500, FO=1150, RO=950, cowl=-900, cowl_z=900, hdr=-1400, rims='wire', rim=0.66, belt=[(-600, 920), (-3400, 900)], c_bot=-200, c_top=350, Rw=330,
        doors=((-900, -900, 0), (-2000, -2000, 0)), handles=((-1850, 840),), head=dict(pts=[(-60, 780), (180, 780), (180, 560), (-60, 560)]),
        ops=(side_vents(-100, 720, 3, w=250), ('front', 'fn', lambda sc, g: sc.geom(rpoly([(-200, 800, 0), (400, 760, 0), (380, 830, 30), (-180, 860, 30)]), fill=False)))), 'front-engine-coupe-1960s')
    add('Gullwing coupe with doors open', sports(GT, 1250, cowl=-650, cowl_z=880, hdr=-1350, rims='5', rim=0.7, belt=[(-600, 900), (-3700, 960)], c_bot=-250, c_top=-50, glass_from=-1600,
        doors=((-650, -670, -10), (-1900, -1950, 0)), handles=(), head=dict(pts=[(-300, 640), (180, 640), (180, 480), (-300, 480)]),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(-700, 1260, 40), (-1900, 1270, 40), (-1950, 2100, 120), (-800, 2150, 120)])), sc.geom(rpoly([(-850, 1500, 40), (-1750, 1500, 40), (-1780, 1950, 80), (-900, 1990, 80)]), fill=False))),)), 'gullwing-coupe')
    add('Scissor-door supercar', sports(WEDGE, 1130, cowl=-500, cowl_z=860, hdr=-1300, belt=[(-600, 900), (-3700, 1000)], c_bot=-400, c_top=-100, rims='7', rim=0.72, Rwr=360,
        doors=((-480, -520, -10), (-480, -520, 0)), handles=(),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(-500, 900, 40), (-900, 950, 40), (-1200, 2300, 80), (-700, 2350, 60)])), sc.geom(rpoly([(-650, 1300, 30), (-900, 1330, 30), (-1050, 2050, 50), (-780, 2080, 40)]), fill=False))),
             side_vents(-2400, 780, 4)), head=dict(pts=[(-300, 600), (200, 600), (200, 520), (-300, 500)])), 'scissor-door-supercar')
    add('Speedster with a low windscreen', sports([(1000, 450, 160, 0), (900, 760, 260, 30), (-800, 860, 60, 0), (-1000, 940, 10, 0), (-1080, 940, 10, 0), (-1300, 880, 40, 0), (-2100, 1050, 200, 0), (-2600, 1050, 200, 0), (-3300, 860, 260, 30), (-3550, 600, 120, 0), (-3450, 330, 50, 0)],
        1050, cowl=-800, cowl_z=860, hdr=-1000, no_glass=True, rims='cap', rim=0.6, Rw=320, clr=140, mirror=False, doors=((-800, -820, -10), (-1900, -1900, 0)), handles=((-1750, 780),),
        head=dict(pts=[(-60, 760), (120, 760), (120, 580), (-60, 580)])), 'speedster')
    add('Barchetta race car', sports([(1000, 420, 160, 0), (900, 720, 260, 30), (-800, 820, 60, 0), (-2400, 900, 200, 0), (-3300, 820, 260, 30), (-3550, 580, 120, 0), (-3450, 320, 50, 0)],
        900, cowl=-800, cowl_z=820, hdr=-800, no_glass=True, rims='wire', rim=0.66, Rw=330, clr=120, mirror=False, doors=((-800, -800, 0), (-800, -800, 0)), handles=(),
        ops=(number_roundel(-1400, 560, 5), ('front', 'fn', lambda sc, g: sc.geom(ell(-1900, 960, 220, 90))))), 'barchetta')
    add('Boxy rally hatch with a wing', sports([(800, 500, 40, 0), (780, 820, 60, 0), (-400, 940, 40, 0), (-1000, 1400, 80, 0), (-2300, 1400, 80, 0), (-2900, 1060, 40, 0), (-2950, 450, 40, 0), (-2850, 330, 40, 0)],
        1400, WB=2350, FO=800, RO=600, Rw=320, rims='8', rim=0.64, clr=180, cowl=-400, cowl_z=940, hdr=-1000, flare=80, flare_lo=0.05, belt=[(-600, 960), (-2900, 990)], c_bot=200, c_top=-100,
        doors=((-400, -400, 0), (-1600, -1600, 0)), handles=((-1450, 880),), head=dict(pts=[(-40, 800), (120, 800), (120, 620), (-40, 620)]),
        ops=(wing(-3100, -2500, 1500), number_roundel(-1000, 650, 9))), 'boxy-rally-hatch')
    add('Time-attack car', sports([(1200, 250, 20, 0), (1100, 330, 40, 0), (1000, 560, 120, 10), (-600, 880, 60, 0), (-1300, 1280, 200, 10), (-2400, 1280, 200, 5), (-3400, 960, 80, 0), (-3600, 940, 40, 0), (-3650, 450, 60, 0), (-3550, 280, 40, 0)],
        1280, Rw=345, rims='mesh', rim=0.74, clr=60, flare=120, flare_lo=0.05, cowl=-600, cowl_z=880, hdr=-1300, belt=[(-600, 900), (-3600, 980)], c_bot=-300, c_top=100,
        doors=((-600, -620, -10), (-1900, -1950, 0)), handles=(), head=dict(pts=[(-300, 560), (200, 560), (200, 470), (-300, 470)]),
        ops=(wing(-4000, -3100, 1700), ('front', 'fn', lambda sc, g: sc.geom(zbox(800, 180, 1450, 230))))), 'time-attack-car')
    add('Land speed record car', sports([(3000, 300, 300, 0), (2500, 600, 600, 0), (-2000, 750, 300, 0), (-2600, 1050, 120, 0), (-3200, 1050, 60, 0), (-4800, 850, 200, 0), (-5000, 600, 100, 0), (-4800, 300, 60, 0)],
        1050, WB=5000, FO=3000, RO=0, Rw=330, rims='aero', rim=0.8, clr=150, arch='skirt', cowl=-2000, cowl_z=750, hdr=-2600, no_glass=True, mirror=False,
        doors=((-2000, -2000, 0), (-2000, -2000, 0)), handles=(),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(-3800, 900, 0), (-5000, 900, 0), (-5100, 2000, 60), (-4600, 2000, 60)])), sc.geom(ell(-2700, 1000, 330, 130)))),)), 'land-speed-car')
    add('Electric roadster', sports([(900, 420, 120, 0), (850, 620, 220, 15), (-600, 830, 60, 5), (-800, 1100, 20, 0), (-900, 1100, 20, 0), (-1050, 870, 40, 0), (-2900, 900, 200, 10), (-3150, 700, 80, 0), (-3150, 420, 60, 0), (-3050, 300, 40, 0)],
        1100, WB=2350, FO=900, RO=850, Rw=320, rims='aero', rim=0.72, clr=110, cowl=-600, cowl_z=830, hdr=-850, no_glass=True,
        doors=((-600, -620, -10), (-1700, -1700, 0)), handles=(), head=dict(pts=[(-400, 600), (220, 600), (220, 560), (-400, 560)]),
        tail=dict(pts=[(-40, 880), (600, 880), (600, 850), (-40, 850)]), ops=(('front', 'fn', lambda sc, g: sc.geom(ell(-1600, 930, 180, 110))),)), 'electric-roadster')
    add('Hybrid supercar', sports([(1050, 400, 60, 0), (950, 560, 260, 20), (-400, 880, 120, 15), (-1200, 1160, 300, 15), (-2100, 1150, 200, 10), (-2800, 1100, 300, 20), (-3550, 900, 60, 0), (-3650, 860, 30, 0), (-3650, 450, 60, 0), (-3550, 280, 40, 0)],
        1160, cowl=-400, cowl_z=860, hdr=-1200, Rw=350, rims='twin5', rim=0.74, belt=[(-600, 900), (-3600, 960)], c_bot=-600, c_top=-150,
        doors=((-400, -440, -10), (-2000, -2050, 0)), handles=(), head=dict(pts=[(-300, 560), (240, 580), (240, 500), (-300, 480)]),
        ops=(('front', 'fn', lambda sc, g: sc.geom(rpoly([(-2000, 500, 60), (-2700, 650, 60), (-2700, 900, 60), (-2100, 820, 60)]), fill=False)),)), 'hybrid-supercar')
    add('Modern muscle car', sports(MUSCLE, 1380, WB=2800, FO=1000, RO=1200, Rw=360, rims='10', rim=0.72, clr=120, cowl=-900, cowl_z=1000, hdr=-1600, belt=[(-600, 1020), (-4000, 1040)], c_bot=-300, c_top=250,
        doors=((-900, -900, 0), (-2150, -2150, 0)), handles=((-2000, 940),), head=dict(pts=[(-200, 860), (150, 860), (150, 700), (-200, 700)]),
        ops=(scoop(-100, 1010, 500, 90), side_vents(-200, 650, 3, w=200))), 'modern-muscle-car')
    add('Fastback with racing stripes', sports([(1050, 500, 60, 0), (1030, 780, 60, 0), (-700, 900, 40, 0), (-1300, 1280, 140, 5), (-1900, 1290, 300, 10), (-3400, 960, 60, 0), (-3650, 940, 30, 0), (-3650, 450, 60, 0), (-3550, 320, 40, 0)],
        1290, cowl=-700, cowl_z=900, hdr=-1300, rims='5', rim=0.68, belt=[(-600, 920), (-3600, 960)], c_bot=-300, c_top=350, Rw=340,
        doors=((-700, -700, 0), (-2000, -2000, 0)), handles=((-1850, 840),), head=dict(pts=[(-40, 720), (120, 720), (120, 560), (-40, 560)]),
        ops=(stripe([(1050, 420), (-3650, 420)], 70), stripe([(1050, 560), (-3650, 560)], 70))), 'fastback-stripes')
    add('Hillclimb special', sports([(1500, 250, 40, 0), (1400, 380, 60, 0), (-300, 560, 60, 0), (-600, 780, 40, 0), (-1400, 860, 120, 0), (-2400, 620, 60, 0), (-3000, 560, 40, 0), (-3000, 300, 40, 0)],
        860, WB=3200, FO=1500, RO=500, Rw=320, Rwr=340, rims='5', rim=0.62, clr=60, arch='none', no_glass=True, mirror=False, cowl=-600, cowl_z=780, hdr=-600,
        doors=((-600, -600, 0), (-600, -600, 0)), handles=(),
        ops=(('front', 'fn', lambda sc, g: (sc.geom(rpoly([(1300, 600, 20), (2000, 680, 20), (2000, 800, 20), (1300, 720, 20)])), sc.geom(LineString([(1500, 380), (1650, 640)]).buffer(25)), sc.geom(ell(-900, 920, 150, 130)))),
             wing(-4000, -3300, 1500))), 'hillclimb-special')
    add('Pace car with a light bar', sports(GT, 1250, cowl=-650, cowl_z=880, hdr=-1350, rims='twin5', rim=0.72, belt=[(-600, 900), (-3700, 960)], c_bot=-250, c_top=-50,
        doors=((-650, -670, -10), (-1950, -2000, 0)), handles=((-1800, 830),), head=dict(pts=[(-300, 640), (180, 640), (180, 480), (-300, 480)]),
        ops=(light_bar(-1500, -2400), stripe([(1050, 450), (-3700, 520)], 60))), 'pace-car')
    add('Bubble-canopy concept car', sports([(1100, 380, 160, 0), (900, 620, 300, 20), (-500, 800, 100, 0), (-1400, 1250, 500, 20), (-2600, 1150, 500, 20), (-3300, 900, 300, 10), (-3600, 700, 120, 0), (-3500, 350, 60, 0)],
        1250, cowl=-500, cowl_z=800, hdr=-1400, rims='aero', rim=0.76, arch='skirt', belt=[(-600, 820), (-3400, 860)], c_bot=-700, c_top=-500, mirror=False,
        doors=((-500, -500, 0), (-500, -500, 0)), handles=(), lines=([(1000, 500), (-3500, 600)],)), 'bubble-concept-car')
    return S

# ---------------------------------------------------------------- front, rear and top views
def front_view(W=1900, H=1300, roof_w=1300, belt=900, clr=150, tyre_w=260, Rw=330, grille='wide', lights='slim', ws_top=None, wing_=False, scoop_=False, low=False, name=None, bars=None):
    """A car seen from the front (x right, z up, centre x = 0)."""
    sc = Scene()
    for s in (-1, 1):
        sc.shape(rpoly([(s * (W / 2 - tyre_w - 20), 0, 40), (s * (W / 2 - 20), 0, 40), (s * (W / 2 - 20), Rw * 1.5, 40), (s * (W / 2 - tyre_w - 20), Rw * 1.5, 40)]))
    body_r = [(W / 2, clr + 120, 60), (W / 2 + 30, belt * 0.55, 160), (W / 2 - 10, belt, 120), (roof_w / 2 + 60, belt + 40, 60), (roof_w / 2 - 60, H, 120)]
    nodes = [(-x, z, r) for x, z, r in body_r] [::-1]
    poly = [(x, z, r) for x, z, r in body_r] + [(-x, z, r) for x, z, r in body_r[::-1]] + [(-W / 2 + 120, clr, 40), (W / 2 - 120, clr, 40)]
    sc.shape(rpoly(poly[::-1]))
    wt = ws_top or H - 80
    sc.shape(rpoly([(-(W / 2 - 90), belt + 30, 30), ((W / 2 - 90), belt + 30, 30), (roof_w / 2 - 80, wt, 60), (-(roof_w / 2 - 80), wt, 60)]), fill=False)
    for s in (-1, 1):
        sc.shape(rpoly([(s * (W / 2 - 40), belt + 40, 30), (s * (W / 2 + 160), belt + 60, 40), (s * (W / 2 + 150), belt + 180, 40), (s * (W / 2 - 40), belt + 160, 30)]))
        if lights == 'slim': sc.shape(rpoly([(s * (W / 2 - 80), belt * 0.68, 30), (s * (W / 2 - 420), belt * 0.66, 30), (s * (W / 2 - 400), belt * 0.6, 20), (s * (W / 2 - 90), belt * 0.56, 30)]), fill=False)
        elif lights == 'round':
            sc.shape(Point(s * (W / 2 - 230), belt * 0.62).buffer(110), fill=False); sc.line(circle(s * (W / 2 - 230), belt * 0.62, 60))
        else: sc.shape(rpoly([(s * (W / 2 - 80), belt * 0.72, 20), (s * (W / 2 - 380), belt * 0.72, 20), (s * (W / 2 - 380), belt * 0.52, 20), (s * (W / 2 - 80), belt * 0.52, 20)]), fill=False)
    gw = {'wide': W * 0.55, 'narrow': W * 0.3, 'big': W * 0.62, 'none': 0}[grille]
    if gw:
        gz0, gz1 = clr + 140, belt * (0.5 if grille != 'big' else 0.62)
        sc.shape(rpoly([(-gw / 2, gz0, 50), (gw / 2, gz0, 50), (gw / 2, gz1, 50), (-gw / 2, gz1, 50)]), fill=False)
        for k in range(1, 4):
            z = gz0 + (gz1 - gz0) * k / 4
            sc.lines(clip([[(-gw / 2, z), (gw / 2, z)]], rpoly([(-gw / 2, gz0, 50), (gw / 2, gz0, 50), (gw / 2, gz1, 50), (-gw / 2, gz1, 50)]).buffer(-20)))
    if scoop_: sc.shape(rpoly([(-260, belt - 10, 0), (260, belt - 10, 0), (200, belt + 90, 30), (-200, belt + 90, 30)]))
    if wing_:
        sc.shape(rpoly([(-W / 2 + 60, H + 160, 20), (W / 2 - 60, H + 160, 20), (W / 2 - 60, H + 240, 20), (-W / 2 + 60, H + 240, 20)]))
        for s in (-1, 1): sc.shape(rpoly([(s * (W / 2 - 40), H - 100, 10), (s * (W / 2 - 100), H - 100, 10), (s * (W / 2 - 100), H + 300, 10), (s * (W / 2 - 40), H + 300, 10)]))
    if bars: sc.shape(rpoly([(-bars, H + 20, 20), (bars, H + 20, 20), (bars - 40, H + 120, 30), (-bars + 40, H + 120, 30)]))
    return flip(sc.render())

def rear_view(W=1900, H=1300, roof_w=1300, belt=950, clr=150, tyre_w=260, Rw=330, exhausts=2, lights='bar', wing_=False, plate=True):
    sc = Scene()
    for s in (-1, 1):
        sc.shape(rpoly([(s * (W / 2 - tyre_w - 20), 0, 40), (s * (W / 2 - 20), 0, 40), (s * (W / 2 - 20), Rw * 1.5, 40), (s * (W / 2 - tyre_w - 20), Rw * 1.5, 40)]))
    body_r = [(W / 2, clr + 120, 60), (W / 2 + 30, belt * 0.55, 160), (W / 2 - 10, belt, 120), (roof_w / 2 + 60, belt + 40, 60), (roof_w / 2 - 60, H, 120)]
    poly = [(x, z, r) for x, z, r in body_r] + [(-x, z, r) for x, z, r in body_r[::-1]] + [(-W / 2 + 120, clr, 40), (W / 2 - 120, clr, 40)]
    sc.shape(rpoly(poly[::-1]))
    sc.shape(rpoly([(-(W / 2 - 110), belt + 50, 30), ((W / 2 - 110), belt + 50, 30), (roof_w / 2 - 90, H - 100, 60), (-(roof_w / 2 - 90), H - 100, 60)]), fill=False)
    if lights == 'bar':
        sc.shape(rpoly([(-(W / 2 - 60), belt * 0.8, 30), (W / 2 - 60, belt * 0.8, 30), (W / 2 - 60, belt * 0.72, 30), (-(W / 2 - 60), belt * 0.72, 30)]), fill=False)
    else:
        for s in (-1, 1):
            for k in (0, 1): sc.shape(Point(s * (W / 2 - 200 - k * 230), belt * 0.72).buffer(85), fill=False)
    if plate: sc.shape(rpoly([(-260, belt * 0.38, 15), (260, belt * 0.38, 15), (260, belt * 0.56, 15), (-260, belt * 0.56, 15)]), fill=False)
    for k in range(exhausts):
        x = (-1 if k % 2 == 0 else 1) * (W * 0.3 + (k // 2) * 140)
        sc.shape(Point(x, clr + 90).buffer(60), fill=False); sc.line(circle(x, clr + 90, 30, n=12))
    if wing_:
        sc.shape(rpoly([(-W / 2 + 60, H + 160, 20), (W / 2 - 60, H + 160, 20), (W / 2 - 60, H + 240, 20), (-W / 2 + 60, H + 240, 20)]))
        for s in (-1, 1): sc.shape(rpoly([(s * 380, belt + 20, 10), (s * 330, belt + 20, 10), (s * 330, H + 170, 10), (s * 380, H + 170, 10)]))
    return flip(sc.render())

def top_view(L=4600, W=1850, nose=0.16, tail=0.08, cab0=0.38, cab1=0.78, ws=0.3, rw=0.86, open_top=False, stripes=False):
    """A car seen from above (front at the top)."""
    sc = Scene(); h = L / 2
    for s in (-1, 1):
        for z in (h - L * 0.2, -h + L * 0.2):
            sc.shape(rpoly([(s * W / 2 - 120, z - 330, 40), (s * W / 2 + 40, z - 330, 40), (s * W / 2 + 40, z + 330, 40), (s * W / 2 - 120, z + 330, 40)]))
    right = [(W * 0.32, h, 300), (W / 2, h - L * nose, 300), (W / 2, -h + L * tail, 300), (W * 0.36, -h, 300)]
    sc.shape(rpoly(right + [(-x, z, r) for x, z, r in right[::-1]]))
    z_ws0 = h - L * ws; z_c0 = h - L * cab0; z_c1 = h - L * cab1; z_rw = h - L * rw
    if open_top:
        sc.shape(rpoly([(-W * 0.36, z_c0, 120), (W * 0.36, z_c0, 120), (W * 0.36, z_c1, 120), (-W * 0.36, z_c1, 120)]), fill=False)
        for s in (-1, 1): sc.shape(rpoly([(s * W * 0.06, z_c0 - 200, 80), (s * W * 0.3, z_c0 - 200, 80), (s * W * 0.3, z_c0 - 800, 80), (s * W * 0.06, z_c0 - 800, 80)]), fill=False)
        sc.line([(-W * 0.42, z_ws0), (W * 0.42, z_ws0)])
    else:
        sc.shape(rpoly([(-W * 0.42, z_ws0, 80), (W * 0.42, z_ws0, 80), (W * 0.36, z_c0, 60), (-W * 0.36, z_c0, 60)]), fill=False)
        sc.shape(rpoly([(-W * 0.36, z_c0, 60), (W * 0.36, z_c0, 60), (W * 0.36, z_c1, 60), (-W * 0.36, z_c1, 60)]))
        sc.shape(rpoly([(-W * 0.36, z_c1, 60), (W * 0.36, z_c1, 60), (W * 0.4, z_rw, 80), (-W * 0.4, z_rw, 80)]), fill=False)
    for s in (-1, 1):
        sc.shape(rpoly([(s * W * 0.46, z_ws0 - 40, 30), (s * (W / 2 + 150), z_ws0 - 80, 30), (s * (W / 2 + 150), z_ws0 - 200, 30), (s * W * 0.46, z_ws0 - 200, 30)]))
        sc.shape(rpoly([(s * W * 0.2, h - 60, 30), (s * W * 0.44, h - L * nose * 0.4, 30), (s * W * 0.44, h - L * nose * 0.7, 30), (s * W * 0.2, h - 200, 30)]), fill=False)
    if stripes:
        for s in (-1, 1): sc.lines(clip([[(s * 160, h), (s * 160, -h)], [(s * 300, h), (s * 300, -h)]], rpoly(right + [(-x, z, r) for x, z, r in right[::-1]]).buffer(-30)))
    return flip(sc.render())

def rally_lamps():
    out = []
    for x in (-450, -150, 150, 450):
        out += [[(px, -pz) for px, pz in circle(x, 1040, 110, n=24)], [(px, -pz) for px, pz in circle(x, 1040, 60, n=16)]]
    return out

def openwheel_top():
    sc = Scene()
    for s in (-1, 1):
        for z, w, l in ((1700, 330, 680), (-1800, 400, 720)):
            sc.shape(rpoly([(s * 820 - w / 2, z - l / 2, 60), (s * 820 + w / 2, z - l / 2, 60), (s * 820 + w / 2, z + l / 2, 60), (s * 820 - w / 2, z + l / 2, 60)]))
        sc.shape(LineString([(s * 150, 1600), (s * 700, 1700)]).buffer(25)); sc.shape(LineString([(s * 250, -1700), (s * 650, -1800)]).buffer(25))
    sc.shape(rpoly([(-900, 2300, 30), (900, 2300, 30), (900, 2550, 30), (-900, 2550, 30)]))
    body = [(0, 2500, 60), (180, 1800, 200), (300, 300, 300), (560, -200, 200), (560, -1200, 300), (350, -1900, 200), (0, -2000, 60)]
    sc.shape(rpoly(body + [(-x, z, r) for x, z, r in body[::-1][1:-1]]))
    sc.shape(rpoly([(-500, -2100, 30), (500, -2100, 30), (500, -2450, 30), (-500, -2450, 30)]))
    sc.shape(Polygon(ellipse(0, -100, 200, 380, n=40)), fill=False)
    sc.line(circle(0, -50, 120, n=24))
    return flip(sc.render())

def openwheel_front():
    sc = Scene()
    for s in (-1, 1):
        sc.shape(rpoly([(s * 820 - 165, 0, 40), (s * 820 + 165, 0, 40), (s * 820 + 165, 660, 40), (s * 820 - 165, 660, 40)]))
        sc.shape(LineString([(s * 150, 300), (s * 660, 330)]).buffer(22)); sc.shape(LineString([(s * 150, 420), (s * 660, 380)]).buffer(22))
    sc.shape(rpoly([(-950, 60, 20), (950, 60, 20), (950, 180, 20), (-950, 180, 20)]))
    for s in (-1, 1): sc.shape(rpoly([(s * 960, 40, 10), (s * 900, 40, 10), (s * 900, 360, 10), (s * 960, 360, 10)]))
    sc.shape(rpoly([(-160, 180, 40), (160, 180, 40), (220, 600, 60), (120, 780, 60), (-120, 780, 60), (-220, 600, 60)]))
    sc.shape(Point(0, 900).buffer(160)); sc.line([(-150, 920), (150, 920)])
    sc.shape(rpoly([(-260, 1050, 40), (260, 1050, 40), (200, 1150, 40), (-200, 1150, 40)]))
    sc.shape(rpoly([(-700, 1300, 20), (700, 1300, 20), (700, 1380, 20), (-700, 1380, 20)]))
    for s in (-1, 1): sc.shape(rpoly([(s * 720, 700, 10), (s * 660, 700, 10), (s * 660, 1420, 10), (s * 720, 1420, 10)]))
    return flip(sc.render())


# ---------------------------------------------------------------- hand-built: vintage cars, buggy, golf cart (z up)
def band(path, w):
    return LineString(path).buffer(w / 2, cap_style=2, join_style=1)

def mudguards(sc, xf, xr, R, board_z, front_reach=1.2, rear_reach=1.15, w=70):
    f = spline([(xf + R * front_reach, R * 0.9), (xf + R * 0.75, R + R * 0.85), (xf - R * 0.2, R + R * 1.05), (xf - R * 1.05, R * 1.2), (xf - R * 1.5, board_z + 40)], n=10)
    r = spline([(xr + R * 1.5, board_z + 40), (xr + R * 0.95, R * 1.35), (xr, R + R * 1.05), (xr - R * 0.8, R + R * 0.75), (xr - R * rear_reach, R * 0.8)], n=10)
    sc.geom(band(f, w)); sc.geom(band(r, w))
    sc.geom(zbox(xf - R * 1.5, board_z - 25, xr + R * 1.5, board_z + 35))

def vintage(kind):
    sc = Scene()
    if kind == '1910':
        R, WB = 420, 2500; xf, xr = 0, -WB
        wheel(sc, xf, R, R, rim=0.42, style='artillery'); wheel(sc, xr, R, R, rim=0.42, style='artillery', spin=0.3)
        sc.geom(rpoly([(560, 820, 30), (700, 840, 30), (700, 1420, 40), (560, 1420, 40)]))                     # radiator
        sc.lines([[(590, z), (670, z)] for z in range(880, 1400, 60)])
        sc.geom(rpoly([(560, 820, 0), (-500, 860, 0), (-500, 1300, 30), (560, 1340, 30)]))                     # bonnet
        sc.lines([[(x, 900), (x, 1250)] for x in range(-400, 500, 90)])
        sc.geom(rpoly([(-500, 700, 40), (-2900, 700, 120), (-3050, 1100, 200), (-2950, 1500, 160), (-2500, 1520, 60), (-2400, 1300, 40), (-1700, 1300, 40), (-1650, 1700, 60), (-1300, 1700, 60), (-1200, 1300, 40), (-500, 1300, 0)]))
        sc.geom(band([(-500, 1300), (-620, 1900)], 40))                                                     # windscreen frame
        sc.line([(-520, 1400), (-610, 1860)])
        top = [(-1400, 1700), (-1600, 2350), (-2200, 2450), (-2800, 2300), (-3000, 1500)]
        sc.geom(band(spline(top, n=10), 50))
        for a, b in (((-1650, 2360), (-2000, 1520)), ((-2250, 2440), (-2300, 1520)), ((-2850, 2280), (-2700, 1520))): sc.line([a, b])
        sc.geom(Point(760, 1100).buffer(110)); sc.line(circle(780, 1100, 60))
        mudguards(sc, xf, xr, R, 700)
        sc.geom(rpoly([(-1200, 1100, 30), (-1150, 1700, 60), (-1000, 1750, 40), (-1050, 1100, 30)]))           # steering column
        sc.line(ellipse(-1080, 1760, 160, 40, n=20))
    elif kind == '1920':
        R, WB = 400, 3100; xf, xr = 0, -WB
        wheel(sc, xf, R, R, rim=0.5, style='wire'); wheel(sc, xr, R, R, rim=0.5, style='wire', spin=0.3)
        sc.geom(rpoly([(820, 700, 30), (960, 720, 30), (960, 1330, 60), (820, 1330, 60)]))
        sc.lines([[(850, z), (930, z)] for z in range(760, 1300, 60)])
        sc.geom(rpoly([(820, 700, 0), (-800, 720, 0), (-800, 1300, 40), (820, 1330, 40)]))
        sc.lines([[(x, 830), (x, 1180)] for x in range(-600, 700, 100)])
        sc.geom(rpoly([(-800, 620, 40), (-3700, 640, 160), (-3900, 900, 200), (-3800, 1280, 120), (-800, 1300, 0)]))
        sc.lines([[(-2100, 700), (-2100, 1280)], [(-1300, 700), (-1300, 1280)]])
        sc.geom(Polygon(rect(-2000, 1050, 120, 50, 20)), fill=False)
        sc.geom(band([(-800, 1300), (-900, 1720)], 40)); sc.line([(-820, 1380), (-890, 1680)])
        sc.geom(rpoly([(-2900, 1250, 80), (-3700, 1280, 120), (-3650, 1500, 120), (-3000, 1480, 120)]))           # folded hood
        sc.lines([[(-3000 - k * 160, 1300), (-3050 - k * 160, 1470)] for k in range(4)])
        sc.geom(ring(xr - 1020, 1050, 380)); sc.line(circle(xr - 1020, 1050, 220)); sc.line(circle(xr - 1020, 1050, 60))
        sc.geom(Point(1080, 1050).buffer(120)); sc.line(circle(1100, 1050, 70))
        mudguards(sc, xf, xr, R, 560)
    else:                                                                                                    # 1930s saloon
        R, WB = 380, 3000; xf, xr = 0, -WB
        wheel(sc, xf, R, R, rim=0.56, style='whitewall'); wheel(sc, xr, R, R, rim=0.56, style='whitewall', spin=0.3)
        body = rpoly([(900, 650, 100), (950, 1150, 160), (-500, 1250, 80), (-900, 1850, 260), (-2900, 1900, 300), (-3700, 1350, 300), (-3950, 800, 160), (-3800, 620, 40)])
        sc.geom(body)
        win = rpoly([(-650, 1300, 60), (-1000, 1760, 120), (-2700, 1780, 160), (-3200, 1320, 60)])
        sc.geom(win, fill=False)
        sc.geom(zbox(-1750, 1300, -1850, 1800))
        sc.lines([[(-500, 650), (-650, 1300)], [(-1800, 650), (-1800, 1300)], [(-2900, 650), (-3200, 1320)]])
        sc.lines([[(x, 900), (x, 1150)] for x in range(-300, 800, 110)])
        for hx in (-1650, -1950): sc.geom(capsule((hx - 60, 1200), (hx + 60, 1200), 30), fill=False)
        mudguards(sc, xf, xr, R, 600, front_reach=1.4, rear_reach=1.4, w=150)
        sc.geom(ell(1000, 1180, 110, 150)); sc.line(ellipse(1020, 1180, 60, 90, n=16))
    return flip(sc.render())

def beach_buggy():
    sc = Scene(); R1, R2, WB = 330, 420, 2100
    wheel(sc, 0, R1, R1, rim=0.55, style='steel'); wheel(sc, -WB, R2, R2, rim=0.5, style='steel', spin=0.4)
    body = rpoly([(700, 500, 160), (500, 900, 300), (-600, 950, 100), (-1100, 820, 60), (-2200, 820, 80), (-2700, 650, 160), (-2700, 420, 60), (-2400, 400, 0),
                  (-2400 + 30, R2 + 260, 200), (-1700, R2 + 220, 200), (-1400, 400, 0), (-600, 400, 0), (-500, R1 + 200, 160), (450, R1 + 160, 160), (700, 400, 60)])
    sc.geom(body)
    sc.geom(band([(-1300, 820), (-1350, 1700), (-2000, 1700), (-2050, 820)], 70))
    sc.geom(band([(-600, 950), (-760, 1300)], 35))
    sc.geom(rpoly([(-1400, 820, 0), (-1700, 820, 0), (-1750, 1300, 80), (-1500, 1330, 60)]))
    sc.geom(Point(-2750, 760).buffer(70)); sc.geom(ell(300, 860, 90, 50, 0.2))
    return flip(sc.render())

def golf_cart():
    sc = Scene(); R, WB = 230, 1650
    wheel(sc, 0, R, R, rim=0.55, style='cap'); wheel(sc, -WB, R, R, rim=0.55, style='cap', spin=0.4)
    sc.geom(rpoly([(380, 260, 60), (380, 700, 160), (-300, 760, 60), (-450, 420, 40), (-2050, 420, 40), (-2050, 260, 40)]))
    sc.geom(rpoly([(-700, 420, 40), (-1500, 420, 40), (-1500, 700, 60), (-700, 700, 60)]))
    sc.geom(rpoly([(-1350, 700, 40), (-1500, 700, 40), (-1600, 1250, 60), (-1450, 1260, 60)]))
    for x0, x1 in ((-350, -450), (-1900, -1900)): sc.geom(band([(x0, 600), (x1, 1820)], 50))
    sc.geom(rpoly([(-200, 1800, 40), (-2050, 1800, 40), (-2050, 1900, 40), (-200, 1900, 40)]))
    sc.geom(band([(-300, 760), (-480, 1150)], 30)); sc.geom(ell(-480, 1160, 120, 30, -0.4))
    sc.geom(rpoly([(-1980, 420, 40), (-2250, 420, 40), (-2300, 1250, 60), (-2030, 1250, 60)]))
    for x in (-2230, -2160, -2080): sc.line([(x, 1250), (x - 30, 1450)])
    sc.line([(-2160, 1450), (-2120, 1480)])
    return flip(sc.render())

# ---------------------------------------------------------------- the lists
def everyday():
    C = []
    def add(name, L, slug): C.append((name, L, slug))
    add('Modern saloon', car(SALOON), 'modern-saloon')
    add('Five-door hatchback', car(HATCH5), 'five-door-hatchback')
    add('Three-door hatchback', car(HATCH3), 'three-door-hatchback')
    add('Estate car', car(ESTATE), 'estate-car')
    add('Compact crossover', car(CROSSOVER), 'compact-crossover')
    add('Large SUV with roof rails', car(SUV), 'large-suv')
    add('Boxy off-roader with a spare wheel', car(OFFROADER), 'boxy-off-roader')
    add('Single-cab pickup', car(pickup('single')), 'single-cab-pickup')
    add('Double-cab pickup', car(pickup('double')), 'double-cab-pickup')
    add('Panel van', car(PANEL_VAN), 'panel-van')
    add('Van with a ladder rack', car(V(PANEL_VAN, ops=(ladder_rack(-1500, -3900),))), 'van-ladder-rack')
    add('Minivan', car(MPV), 'minivan')
    add('City microcar', car(MICRO), 'city-microcar')
    add('Kei truck', car(KEI_TRUCK), 'kei-truck')
    add('Electric hatch at a charging post', car(V(HATCH5, rims='aero', ops=(charger(-3900),))), 'electric-hatch-charging')
    add('Taxi', car(V(SALOON, ops=(roof_box(-1150, -1750, 230, 'TAXI', size=120, r=40),))), 'taxi')
    add('Police car', car(V(SALOON, ops=(light_bar(-1100, -1900), door_text('POLICE', -1500, 560, 150)), lines=())), 'police-car')
    add('Limousine', car(LIMO), 'limousine')
    add('Convertible with the roof down', car(CONVERTIBLE), 'convertible-roof-down')
    add('Two-door coupe', car(COUPE), 'two-door-coupe')
    add('Car of the 1910s', vintage('1910'), 'car-1910s')
    add('1920s tourer', vintage('1920'), 'tourer-1920s')
    add('1930s saloon', vintage('1930'), 'saloon-1930s')
    add('1950s car with tail fins', car(FINS_1950), 'tail-fins-1950s')
    add('1960s compact car', car(COMPACT_1960), 'compact-1960s')
    add('1970s station wagon', car(WAGON_1970), 'station-wagon-1970s')
    add('Camper van with a pop-up roof', car(CAMPER), 'camper-van')
    add('Ice-cream van', car(ICE_CREAM), 'ice-cream-van')
    add('Tow truck', car(tow_truck()), 'tow-truck')
    add('Beach buggy', beach_buggy(), 'beach-buggy')
    add('Golf cart', golf_cart(), 'golf-cart')
    add('Go-kart', car(GO_KART), 'go-kart')
    add('Car with luggage on the roof', car(V(HATCH5, ops=(luggage(-500, -2500),))), 'car-roof-luggage')
    add('Estate car with a surfboard', car(V(ESTATE, ops=(surfboard(-1500, -3300),))), 'estate-surfboard')
    add('Hatchback, front view', front_view(1800, 1480, 1250, 950, grille='narrow', lights='slim'), 'hatchback-front')
    add('SUV, front view', front_view(2000, 1850, 1500, 1250, clr=220, Rw=390, tyre_w=290, grille='big', lights='square', bars=600), 'suv-front')
    add('Saloon, rear view', rear_view(1850, 1450, 1300, 1050, exhausts=2, lights='bar'), 'saloon-rear')
    add('Car seen from above', top_view(4700, 1850), 'car-top-view')
    add('Pickup, front view', front_view(2050, 1900, 1650, 1300, clr=260, Rw=400, tyre_w=300, grille='big', lights='square'), 'pickup-front')
    add('1960s compact, front view', front_view(1650, 1380, 1300, 860, clr=170, Rw=300, tyre_w=200, grille='wide', lights='round'), 'compact-1960s-front')
    add('Minivan, rear view', rear_view(1900, 1780, 1600, 1100, exhausts=1, lights='round'), 'minivan-rear')
    return C

def sporty():
    S = [(n, car(p), s) for n, p, s in sportscars()]
    S.append(('Supercar, front view', front_view(2050, 1130, 1150, 700, clr=110, Rw=340, tyre_w=320, grille='wide', lights='slim', low=True), 'supercar-front'))
    S.append(('Supercar, rear view', rear_view(2050, 1130, 1150, 760, clr=110, Rw=340, tyre_w=320, exhausts=4, lights='bar', wing_=True), 'supercar-rear'))
    S.append(('Supercar seen from above', top_view(4500, 2000, nose=0.2, tail=0.06, cab0=0.36, cab1=0.62, ws=0.26, rw=0.78), 'supercar-top'))
    S.append(('Grand tourer, front view', front_view(1950, 1300, 1250, 820, clr=130, Rw=340, tyre_w=290, grille='narrow', lights='round', scoop_=True), 'gt-front'))
    S.append(('Roadster seen from above', top_view(4000, 1750, nose=0.22, tail=0.1, cab0=0.42, cab1=0.62, ws=0.36, open_top=True), 'roadster-top'))
    S.append(('Muscle car seen from above', top_view(4900, 1900, nose=0.1, tail=0.06, cab0=0.42, cab1=0.7, ws=0.36, rw=0.82, stripes=True), 'muscle-car-top'))
    S.append(('Race car with a wing, rear view', rear_view(2000, 1250, 1200, 780, clr=90, Rw=360, tyre_w=330, exhausts=2, lights='round', wing_=True, plate=False), 'race-car-rear'))
    S.append(('Open-wheel race car from above', openwheel_top(), 'open-wheel-top'))
    S.append(('Open-wheel race car, front view', openwheel_front(), 'open-wheel-front'))
    S.append(('Rally car with spotlights, front view', front_view(1850, 1420, 1300, 950, clr=200, Rw=330, tyre_w=230, grille='narrow', lights='round', bars=None) + rally_lamps(), 'rally-car-front'))
    S.append(('Classic GT, rear view', rear_view(1800, 1250, 1200, 820, clr=140, Rw=330, tyre_w=240, exhausts=4, lights='round'), 'classic-gt-rear'))
    return S

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    items = []
    for cat, lst in (('cars', everyday()), ('sportscars', sporty())):
        for name, L, slug in lst:
            it = Item(cat, name, L); it.slug = slug; items.append(it)
    save(items, OUT)
    from collections import Counter
    P = sorted(export_size(i.lines)[0] for i in items)
    print(Counter(i.cat for i in items), 'median', P[len(P) // 2], 'max', P[-1])
    if SHEET:
        for i in range(0, len(items), 36):
            sheet(items[i:i + 36], SHEET.replace('.png', f'_{i // 36}.png'), cols=6, cell=2.8)
