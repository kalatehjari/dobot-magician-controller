"""City skylines: recognisable landmarks, filler buildings in depth layers, hills, water and the city's
name. Kit: gen_skylines_kit.py; landmarks: gen_skylines_lm.py.
Usage: python3 -I gen_skylines.py <out.json> [sheet.png]"""
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_skylines_kit import *
from gen_skylines_lm import *
from common import Item, save, sheet, export_size
TAU = 2 * math.pi

def layers(c, back=(60, 150), front=(22, 60), style='modern', fstyle=None, win=0.3, x0=0, x1=1000, back_w=(20, 44), front_w=(16, 34), skip=0.0):
    c.fill(3, x0, x1, h=back, w=back_w, style=style, win=win, skip=skip)
    c.fill(8, x0, x1, h=front, w=front_w, style=fstyle or style, win=win * 0.8, skip=skip)

def bg(c, g, x, s=1.0, z=0):
    c.put(g.at(x, 0, s), z)

def turbine(x, h, y=0.0):
    g = G()
    g.S(taper_box(3, 1.5, y, y + h, x))
    for k in range(3):
        a = PI / 2 + TAU * k / 3 + 0.3
        g.S(closed([(x, y + h), (x + math.cos(a - 0.08) * h * 0.4, y + h + math.sin(a - 0.08) * h * 0.4), (x + math.cos(a) * h * 0.45, y + h + math.sin(a) * h * 0.45), (x + math.cos(a + 0.06) * h * 0.1, y + h + math.sin(a + 0.06) * h * 0.1)]))
    g.S(circ(x, y + h, 2.2, 10))
    return g

CITIES = []
def city(f): CITIES.append(f); return f

@city
def paris():
    c = City('Paris', 1, water=True)
    c.lm(eiffel(), 300, 0.95)
    c.lm(notre_dame(), 640, 1.35)
    c.lm(arc_de_triomphe(), 860, 1.3)
    layers(c, back=(50, 110), front=(26, 50), style='paris', win=0.5)
    c.boat(rowboat(520, 1.2))
    return c

@city
def london():
    c = City('London', 2, water=True)
    c.lm(london_eye(), 120, 1.05)
    c.lm(westminster(), 380, 1.25)
    c.lm(big_ben(), 520, 1.6)
    c.lm(st_pauls(), 660, 1.05, z=4)
    c.lm(shard(), 790, 0.86)
    c.lm(gherkin(), 920, 0.8)
    layers(c, back=(50, 130), front=(24, 54), style='modern', fstyle='euro', win=0.3)
    c.boat(ferry(620, 1.0))
    return c

@city
def new_york():
    c = City('New York', 3, water=True)
    c.lm(one_wtc(), 170, 0.55)
    c.lm(empire_state(), 470, 0.66)
    c.lm(chrysler_like(), 610, 0.76)
    c.lm(brooklyn_bridge(), 790, 0.44, z=9)
    layers(c, back=(90, 210), front=(40, 110), style='tower', win=0.4)
    c.boat(ferry(330, 1.0))
    return c

@city
def tokyo():
    c = City('Tokyo', 4)
    bg(c, mount_fuji(900, 200), 680, 1.0)
    c.lm(skytree(), 290, 0.5)
    c.lm(tokyo_tower(), 600, 0.74)
    layers(c, back=(50, 140), front=(24, 60), style='modern', win=0.4)
    return c

@city
def dubai():
    c = City('Dubai', 5, water=True)
    c.lm(dubai_frame(), 90, 0.8)
    c.lm(emirates_towers(), 260, 0.62)
    c.lm(burj_khalifa(), 470, 0.38)
    c.lm(burj_al_arab(), 830, 0.72, z=6)
    layers(c, back=(60, 170), front=(26, 70), style='glass', fstyle='desert', win=0.3, x1=760)
    c.boat(dhow(680, 1.0))
    return c

@city
def sydney():
    c = City('Sydney', 6, water=True)
    c.lm(sydney_tower(), 470, 0.9, z=3)
    c.lm(opera_house(), 240, 1.3, z=6)
    c.lm(sydney_harbour_bridge(), 690, 0.52, z=7)
    layers(c, back=(60, 150), front=(26, 60), style='modern', win=0.3, x0=380, x1=620)
    c.boat(sailboat(470, 1.0)); c.boat(ferry(560, 0.9, True))
    return c

@city
def auckland():
    c = City('Auckland', 7, water=True)
    bg(c, rangitoto(460, 80), 770, 1.0)
    c.lm(sky_tower(), 330, 0.9)
    c.lm(auckland_bridge(), 740, 0.46, z=7)
    layers(c, back=(60, 150), front=(26, 66), style='modern', win=0.35, x1=560)
    for x, s, f in ((120, 1.1, False), (560, 0.9, True), (640, 1.0, False), (900, 0.8, True)): c.boat(sailboat(x, s, f))
    return c

@city
def wellington():
    c = City('Wellington', 8, water=True)
    hill = ridge(0, 1000, [(0, 110), (200, 170), (420, 130), (650, 190), (850, 150), (1000, 120)], rough=6, seed=8)
    c.hills(hill, z=0)
    for x, y in ((610, 186), (700, 188), (790, 168)): c.put(turbine(x, 44, y - 4), 1)
    c.lm(beehive(), 380, 1.7)
    c.lm(parliament_nz(), 560, 1.6)
    layers(c, back=(50, 130), front=(24, 58), style='modern', win=0.3)
    c.boat(ferry(780, 1.1))
    return c

@city
def christchurch():
    c = City('Christchurch', 9)
    hill = ridge(0, 1000, [(0, 70), (250, 130), (480, 100), (700, 150), (1000, 90)], rough=5, seed=9)
    c.hills(hill, z=0)
    c.lm(cathedral_spire(), 470, 2.1)
    c.lm(cardboard_cathedral(), 760, 2.4)
    layers(c, back=(40, 100), front=(22, 46), style='euro', win=0.3)
    for k, x in enumerate((60, 140, 860, 930)): c.front(tree_round(x, 46 + 8 * (k % 2), seed=k), 9)
    return c

@city
def tehran():
    c = City('Tehran', 10)
    bg(c, alborz(1000, 170), 500, 1.0)
    c.lm(azadi_tower(), 260, 2.6)
    c.lm(milad_tower(), 640, 0.72)
    layers(c, back=(40, 120), front=(22, 50), style='modern', fstyle='mideast', win=0.3)
    return c

@city
def isfahan():
    c = City('Isfahan', 11, water=True)
    c.lm(shah_mosque(), 360, 2.7, z=4)
    c.lm(lotfollah(), 680, 2.8, z=4)
    c.lm(ali_qapu(), 880, 2.5, z=4)
    c.fill(3, 0, 1000, h=(30, 70), w=(20, 40), style='mideast', win=0.4)
    c.lm(si_o_se_pol(17, 8.0), 500, 4.6, z=9)
    return c

@city
def moscow():
    c = City('Moscow', 12, water=True)
    c.lm(msu_tower(), 820, 1.05, z=2)
    c.lm(kremlin_wall(160), 230, 1.6, z=4, refl=False)
    c.lm(spasskaya(), 200, 2.6)
    c.lm(st_basils(), 470, 2.7)
    layers(c, back=(40, 110), front=(22, 48), style='euro', win=0.3, x0=600)
    return c

@city
def istanbul():
    c = City('Istanbul', 13, water=True)
    c.lm(hagia_sophia(), 270, 2.4)
    c.lm(blue_mosque(), 610, 2.4)
    c.lm(galata_tower(), 900, 2.4, z=4)
    layers(c, back=(30, 80), front=(20, 44), style='old', win=0.3)
    c.boat(ferry(450, 1.0, True)); c.boat(rowboat(760, 1.2))
    return c

@city
def cairo():
    c = City('Cairo', 14, water=True)
    bg(c, pyramids(), 760, 1.0)
    c.lm(cairo_tower(), 280, 1.5)
    c.lm(mohammed_ali_mosque(), 500, 2.0)
    c.fill(3, 0, 620, h=(40, 110), w=(20, 40), style='desert', win=0.3)
    c.fill(8, 0, 1000, h=(18, 36), w=(16, 30), style='desert', win=0.3)
    c.boat(dhow(620, 1.1)); c.boat(dhow(860, 0.9, True))
    return c

@city
def rome():
    c = City('Rome', 15)
    c.lm(colosseum(), 300, 2.1)
    c.lm(vittoriano(), 580, 1.6, z=4)
    c.lm(st_peters(), 800, 1.8)
    layers(c, back=(30, 80), front=(20, 40), style='old', win=0.3)
    for k, x in enumerate((60, 120)): c.front(umbrella_pine(x, 80 + 10 * k, seed=k), 9)
    for x in (930, 960): c.front(cypress(x, 90), 9)
    return c

@city
def venice():
    c = City('Venice', 16, water=True)
    c.lm(campanile(), 300, 2.8)
    c.lm(doges_palace(), 450, 2.3)
    c.lm(salute(), 760, 2.6)
    layers(c, back=(30, 70), front=(20, 40), style='old', win=0.4)
    c.boat(gondola(160, 1.4)); c.boat(gondola(600, 1.2, True)); c.boat(gondola(900, 1.1))
    return c

@city
def pisa():
    c = City('Pisa', 17)
    c.lm(baptistery(), 140, 3.6)
    c.lm(pisa_duomo(), 420, 3.6)
    c.lm(leaning_tower(), 720, 4.6)
    c.fill(3, 0, 1000, h=(30, 70), w=(20, 40), style='old', win=0.2)
    for x in (880, 940): c.front(cypress(x, 110), 9)
    return c

@city
def barcelona():
    c = City('Barcelona', 18, water=True)
    hill = ridge(0, 300, [(0, 80), (120, 120), (300, 40)], rough=4, seed=18)
    c.hills(hill, z=0)
    c.lm(sagrada_familia(), 450, 1.6)
    c.lm(torre_glories(), 780, 1.6)
    layers(c, back=(40, 100), front=(22, 50), style='euro', win=0.3)
    for k, x in enumerate((60, 120, 930)): c.front(palm(x, 70 + 8 * k, seed=k), 9)
    c.boat(sailboat(600, 1.0))
    return c

@city
def madrid():
    c = City('Madrid', 19)
    c.lm(puerta_alcala(), 250, 2.7)
    c.lm(almudena(), 500, 1.9)
    c.lm(cuatro_torres(), 790, 0.95, z=4)
    layers(c, back=(40, 100), front=(22, 50), style='euro', win=0.3, x1=640)
    return c

@city
def lisbon():
    c = City('Lisbon', 20, water=True)
    c.lm(sao_jorge(), 320, 1.4, z=2)
    c.lm(belem_tower(), 130, 3.0, z=6)
    c.lm(bridge_25_abril(), 640, 0.42, z=7)
    c.fill(3, 180, 1000, h=(30, 80), w=(18, 36), style='old', win=0.3)
    c.boat(sailboat(520, 1.0)); c.boat(tall_ship(860, 0.9))
    return c

@city
def berlin():
    c = City('Berlin', 21, water=True)
    c.lm(brandenburg_gate(), 190, 3.1)
    c.lm(berlin_tv(), 440, 0.82)
    c.lm(berlin_cathedral(), 640, 1.6)
    c.lm(reichstag(), 860, 1.6)
    layers(c, back=(40, 110), front=(22, 50), style='euro', win=0.3)
    return c

@city
def amsterdam():
    c = City('Amsterdam', 22, water=True)
    c.lm(westerkerk(), 640, 2.6, z=4)
    for x, seed in ((170, 3), (440, 4), (800, 5)): c.lm(canal_houses(9, seed), x, 2.9, z=6)
    c.fill(3, 0, 1000, h=(30, 70), w=(18, 34), style='euro', win=0.3)
    c.boat(rowboat(300, 1.6)); c.boat(ferry(620, 0.8))
    return c

@city
def prague():
    c = City('Prague', 23, water=True)
    hill = ridge(0, 560, [(0, 50), (200, 80), (420, 70), (560, 20)], rough=3, seed=23)
    c.hills(hill, z=0)
    c.lm(st_vitus(), 280, 2.1, y=64, z=1)
    c.lm(tyn_church(), 780, 2.4, z=4)
    c.fill(3, 520, 1000, h=(30, 80), w=(18, 34), style='old', win=0.3)
    c.lm(charles_bridge(260), 480, 2.4, z=8)
    return c

@city
def vienna():
    c = City('Vienna', 24)
    c.lm(karlskirche(), 180, 2.3)
    c.lm(st_stephens(), 440, 2.0)
    c.lm(riesenrad(), 800, 2.6)
    layers(c, back=(40, 100), front=(22, 50), style='euro', win=0.3)
    return c

@city
def budapest():
    c = City('Budapest', 25, water=True)
    hill = ridge(560, 1000, [(560, 40), (760, 90), (1000, 60)], rough=4, seed=25)
    c.hills(hill, z=0)
    c.lm(budapest_parliament(260), 330, 1.55)
    c.lm(chain_bridge(), 790, 0.98, z=7)
    c.fill(3, 0, 1000, h=(30, 70), w=(18, 34), style='euro', win=0.3)
    return c

@city
def athens():
    c = City('Athens', 26)
    c.lm(parthenon(), 360, 1.8, front=34)
    c.lm(lycabettus(), 820, 1.7, front=34)
    c.fill(8, 0, 1000, h=(16, 34), w=(14, 30), style='mideast', win=0.4)
    return c

@city
def agra():
    c = City('Agra', 27, water=True)
    c.lm(taj_mahal(), 500, 3.2)
    for k, x in enumerate((60, 120, 880, 940)): c.front(cypress(x, 80), 9)
    return c

@city
def mumbai():
    c = City('Mumbai', 28, water=True)
    c.lm(gateway_of_india(), 220, 3.0, z=6)
    c.lm(taj_hotel(), 450, 2.4)
    c.lm(sea_link(600), 790, 0.6, z=7)
    c.fill(3, 0, 650, h=(80, 200), w=(20, 40), style='tower', win=0.4)
    c.boat(dhow(620, 0.9, True))
    return c

@city
def bangkok():
    c = City('Bangkok', 29, water=True)
    c.lm(wat_arun(), 290, 3.1)
    c.lm(thai_roof(60, 26), 560, 2.6)
    c.lm(mahanakhon(), 820, 0.92)
    layers(c, back=(60, 170), front=(22, 50), style='modern', win=0.3, x0=640)
    c.boat(longtail(470, 1.1)); c.boat(longtail(700, 1.0, True))
    return c

@city
def singapore():
    c = City('Singapore', 30, water=True)
    c.lm(artscience(), 140, 2.6)
    c.lm(marina_bay_sands(), 400, 1.2)
    c.lm(esplanade(), 640, 2.0, z=6)
    c.lm(wheel(70, 16, 28, 'A', 4), 850, 1.05)
    c.fill(3, 0, 1000, h=(80, 200), w=(20, 40), style='glass', win=0.3)
    return c

@city
def kuala_lumpur():
    c = City('Kuala Lumpur', 31)
    c.lm(petronas(), 380, 0.68)
    c.lm(kl_tower(), 780, 0.7)
    layers(c, back=(60, 170), front=(22, 60), style='modern', win=0.35)
    return c

@city
def hong_kong():
    c = City('Hong Kong', 32, water=True)
    bg(c, victoria_peak(1000, 150), 500, 1.0)
    c.lm(ifc2(), 300, 0.72)
    c.lm(bank_of_china(), 520, 0.8)
    c.lm(icc(), 820, 0.6)
    layers(c, back=(90, 210), front=(40, 110), style='tower', win=0.4)
    c.boat(junk(150, 1.3)); c.boat(ferry(660, 1.0))
    return c

@city
def shanghai():
    c = City('Shanghai', 33, water=True)
    c.lm(oriental_pearl(), 260, 0.63)
    c.lm(jin_mao(), 820, 0.68)
    c.lm(shanghai_tower(), 560, 0.5)
    c.lm(swfc(), 690, 0.6)
    layers(c, back=(80, 190), front=(30, 80), style='glass', win=0.3)
    c.boat(ferry(420, 0.9))
    return c

@city
def beijing():
    c = City('Beijing', 34)
    hill = ridge(0, 1000, [(0, 60), (300, 110), (600, 80), (1000, 120)], rough=6, seed=34)
    c.hills(hill, z=0)
    c.lm(temple_of_heaven(), 240, 3.2)
    c.lm(cctv(), 600, 0.95)
    c.lm(pagoda(60, 7, 24), 860, 2.6)
    layers(c, back=(50, 140), front=(22, 50), style='modern', win=0.3)
    return c

@city
def seoul():
    c = City('Seoul', 35, water=True)
    hill = ridge(0, 1000, [(0, 90), (220, 150), (520, 120), (800, 170), (1000, 100)], rough=8, seed=35)
    c.hills(hill, z=0)
    c.lm(namsan_tower(), 290, 1.2, z=2)
    c.lm(gyeongbokgung(), 540, 2.3)
    c.lm(lotte_tower(), 790, 0.55)
    layers(c, back=(50, 130), front=(22, 50), style='modern', win=0.3, x0=430)
    return c

@city
def taipei():
    c = City('Taipei', 36)
    hill = ridge(0, 1000, [(0, 120), (300, 170), (600, 140), (1000, 180)], rough=8, seed=36)
    c.hills(hill, z=0)
    c.lm(taipei_101(), 520, 0.6)
    c.lm(thai_roof(50, 22), 200, 2.2)
    layers(c, back=(50, 130), front=(22, 50), style='modern', win=0.3)
    return c

@city
def toronto():
    c = City('Toronto', 37, water=True)
    c.lm(cn_tower(), 400, 0.58)
    c.lm(rogers_centre(), 590, 1.0, z=6)
    c.fill(3, 0, 1000, h=(80, 200), w=(20, 42), style='glass', win=0.35)
    c.fill(8, 680, 1000, h=(30, 80), w=(16, 34), style='modern', win=0.3)
    c.boat(sailboat(150, 1.1)); c.boat(sailboat(820, 1.0, True))
    return c

@city
def seattle():
    c = City('Seattle', 38, water=True)
    bg(c, rainier(800, 200), 700, 1.0)
    c.lm(space_needle(), 260, 1.6)
    c.lm(tower(38, 295, 'notch', mullions=2), 600, 1.0)
    layers(c, back=(60, 170), front=(24, 60), style='modern', win=0.3, x0=380)
    c.boat(ferry(820, 1.1, True))
    return c

@city
def san_francisco():
    c = City('San Francisco', 39, water=True)
    c.hills(ridge(560, 760, [(560, 0), (660, 40), (760, 0)], rough=0, seed=39), z=1)
    c.lm(coit_tower(), 660, 2.2, y=36, z=2)
    c.lm(transamerica(), 780, 1.0)
    c.lm(salesforce(), 900, 0.85)
    c.fill(3, 700, 1000, h=(60, 160), w=(18, 36), style='modern', win=0.3)
    c.lm(golden_gate(), 300, 0.31, z=7)
    c.boat(sailboat(560, 1.0))
    return c

@city
def chicago():
    c = City('Chicago', 40, water=True)
    c.lm(willis(), 380, 0.6)
    c.lm(marina_city(), 560, 1.2)
    c.lm(hancock(), 740, 0.66)
    layers(c, back=(80, 200), front=(30, 80), style='tower', win=0.4)
    c.boat(sailboat(160, 1.1)); c.boat(sailboat(920, 0.9, True))
    return c

@city
def washington():
    c = City('Washington DC', 41, water=True)
    c.lm(lincoln_memorial(), 170, 2.2)
    c.lm(washington_monument(), 480, 1.75)
    c.lm(capitol(), 810, 1.4)
    for k, x in enumerate((300, 350, 610, 650)): c.front(tree_round(x, 40, seed=k), 9)
    return c

@city
def las_vegas():
    c = City('Las Vegas', 42)
    hill = ridge(0, 1000, [(0, 60), (250, 100), (520, 70), (800, 120), (1000, 70)], rough=8, seed=42)
    c.hills(hill, z=0)
    c.lm(strat(), 170, 0.85)
    c.lm(curved_tower(50, 190), 360, 1.0)
    c.lm(luxor_pyramid(), 560, 1.4)
    c.lm(high_roller(), 820, 1.3)
    c.fill(3, 0, 1000, h=(60, 140), w=(20, 40), style='modern', win=0.3)
    for k, x in enumerate((280, 460, 680)): c.front(palm(x, 60, seed=k), 9)
    return c

@city
def rio():
    c = City('Rio de Janeiro', 43, water=True)
    bg(c, corcovado(500, 240), 260, 1.0)
    c.lm(sugarloaf(), 760, 1.25, z=1)
    c.fill(3, 0, 560, h=(30, 90), w=(16, 34), style='modern', win=0.3)
    for k, x in enumerate((60, 140, 420, 500)): c.front(palm(x, 60 + 10 * (k % 2), seed=k), 9)
    c.boat(sailboat(620, 1.0))
    return c

@city
def buenos_aires():
    c = City('Buenos Aires', 44, water=True)
    c.lm(congreso_ba(), 180, 2.3)
    c.lm(obelisco(), 420, 4.0)
    c.lm(puente_mujer(), 760, 2.0, z=7)
    c.fill(3, 0, 1000, h=(50, 130), w=(18, 36), style='modern', win=0.3)
    c.fill(8, 0, 560, h=(22, 50), w=(16, 30), style='euro', win=0.3)
    return c

@city
def mexico_city():
    c = City('Mexico City', 45)
    bg(c, popocatepetl(560, 220), 718, 1.0)
    c.lm(torre_latino(), 330, 1.6)
    c.lm(bellas_artes(), 560, 2.0)
    layers(c, back=(40, 110), front=(22, 50), style='modern', win=0.3)
    return c

@city
def cape_town():
    c = City('Cape Town', 46, water=True)
    bg(c, table_mountain(1000, 180), 500, 1.0)
    c.lm(cape_stadium(), 800, 1.6, z=6)
    c.fill(3, 0, 1000, h=(30, 90), w=(18, 36), style='modern', win=0.3)
    c.boat(sailboat(300, 1.0)); c.boat(ferry(560, 0.9))
    return c

@city
def riyadh():
    c = City('Riyadh', 47)
    c.lm(kingdom_centre(), 400, 1.0)
    c.lm(faisaliyah(), 720, 1.05)
    layers(c, back=(40, 120), front=(20, 44), style='modern', fstyle='desert', win=0.3)
    return c

@city
def doha():
    c = City('Doha', 48, water=True)
    c.lm(burj_doha(), 300, 1.15)
    c.lm(doha_tower(), 470, 1.2)
    c.lm(tornado_tower(), 630, 1.3)
    c.lm(museum_islamic_art(), 860, 2.4, z=6)
    c.fill(3, 0, 760, h=(80, 200), w=(18, 36), style='glass', win=0.3)
    c.boat(dhow(120, 1.1)); c.boat(dhow(720, 1.0, True))
    return c

@city
def edinburgh():
    c = City('Edinburgh', 49)
    bg(c, arthurs_seat(360, 110), 780, 1.2)
    c.lm(edinburgh_castle(), 280, 1.6, z=2)
    c.lm(scott_monument(), 600, 3.6)
    c.fill(3, 460, 1000, h=(30, 80), w=(18, 34), style='old', win=0.3)
    c.fill(8, 440, 1000, h=(20, 44), w=(16, 30), style='old', win=0.3)
    return c

@city
def copenhagen():
    c = City('Copenhagen', 50, water=True)
    c.lm(nyhavn_houses(10, 5), 270, 3.0, z=6)
    c.lm(vor_frelsers(), 640, 3.0)
    c.lm(christiansborg(), 860, 2.3)
    c.fill(3, 0, 1000, h=(30, 70), w=(18, 34), style='euro', win=0.3)
    c.boat(rowboat(220, 1.8)); c.boat(sailboat(520, 0.9))
    return c

@city
def stockholm():
    c = City('Stockholm', 51, water=True)
    c.lm(stockholm_city_hall(), 330, 2.4)
    c.lm(riddarholm(), 760, 2.6)
    c.fill(3, 0, 1000, h=(30, 80), w=(18, 34), style='nordic', win=0.3)
    c.boat(ferry(560, 1.0)); c.boat(sailboat(900, 0.9, True))
    return c

@city
def st_petersburg():
    c = City('St Petersburg', 52, water=True)
    c.lm(peter_paul(), 220, 2.4)
    c.lm(st_isaacs(), 520, 2.0)
    c.lm(savior_on_blood(), 790, 2.6)
    c.fill(3, 0, 1000, h=(30, 70), w=(20, 40), style='euro', win=0.3)
    c.boat(tall_ship(400, 0.9))
    return c

@city
def melbourne():
    c = City('Melbourne', 53, water=True)
    c.lm(flinders_station(), 240, 1.8, z=6)
    c.lm(eureka(), 520, 1.0)
    c.lm(arts_centre_spire(), 760, 1.6)
    c.fill(3, 0, 1000, h=(60, 180), w=(18, 38), style='modern', win=0.3)
    c.boat(rowboat(640, 1.6)); c.boat(rowboat(900, 1.3))
    return c

@city
def oslo():
    c = City('Oslo', 54, water=True)
    bg(c, holmenkollen(600, 120), 720, 1.1)
    c.lm(oslo_opera(), 280, 2.2)
    c.lm(oslo_city_hall(), 640, 2.4)
    c.fill(3, 400, 1000, h=(30, 80), w=(18, 34), style='nordic', win=0.3)
    c.boat(sailboat(480, 1.0)); c.boat(ferry(880, 0.9, True))
    return c

@city
def helsinki():
    c = City('Helsinki', 55, water=True)
    c.lm(helsinki_cathedral(), 330, 3.2)
    c.lm(uspenski(), 700, 3.0)
    c.fill(3, 0, 1000, h=(30, 70), w=(18, 34), style='nordic', win=0.3)
    c.boat(ferry(520, 1.2)); c.boat(sailboat(880, 0.9))
    return c

def make(f):
    c = f()
    L = c.build()
    return c.name, L

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
    items = []
    for f in CITIES:
        if only and f.__name__ not in only: continue
        name, L = make(f)
        it = Item('skylines', name, L); it.slug = 'skyline-' + f.__name__.replace('_', '-'); items.append(it)
        print(f'{name:16s}', export_size(L))
    if not only: save(items, OUT)
    if SHEET:
        for i in range(0, len(items), 20):
            sheet(items[i:i + 20], SHEET.replace('.png', f'_{i // 20}.png'), cols=4, cell=3.6)
