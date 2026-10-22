"""Shoes and clothing: side views of shoes, boots, heels and sandals (with soles, heels, laces,
eyelets and stitching), top views, sole views and pairs; front-view fashion flats of clothes and
outfit flat-lays.
Usage: python3 -I gen_wear.py <out.json> [sheet.png] [only-slug-substring]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_wear_kit import *
import gen_wear_shoes as SH

OUT = sys.argv[1]
SHEET = sys.argv[2] if len(sys.argv) > 2 else None
ONLY = sys.argv[3] if len(sys.argv) > 3 else None

items = []


def add(cat, name, scene_or_lines, slug, yup=False):
    if ONLY and ONLY not in slug: return
    if isinstance(scene_or_lines, Scene):
        sc = s_flip(scene_or_lines) if yup else scene_or_lines
        L = sc.render()
    else:
        L = scene_or_lines
        if yup: L = [[(x, -y) for x, y in P] for P in L]
    L = finish(fit(L, 1000))
    it = Item(cat, name, L, author='Made for this library', source='generated', license='public domain')
    it.slug = slug
    items.append(it)


def shoe(name, fn, slug, sx=0.92):
    """Side views are drawn about 1000 long; squeezing them a little reads better as a shoe."""
    if sx != 1: fn = s_scale(fn, sx, 1.0)
    add('shoes', name, fn, slug, yup=True)


# ---------------------------------------------------------------- shoes
shoe('Running shoe', SH.running_shoe(), 'running-shoe')
shoe('Oxford shoe', SH.oxford(), 'oxford-shoe')
shoe('Chelsea boot', SH.chelsea_boot(), 'chelsea-boot')
shoe('Stiletto', SH.stiletto(), 'stiletto')
shoe('Rain boot', SH.rain_boot(), 'rain-boot')
shoe('High-top sneaker', SH.high_top(), 'high-top-sneaker')
shoe('Slip-on canvas shoe', SH.slip_on(), 'slip-on-canvas-shoe')
shoe('Platform sneaker', SH.platform_sneaker(), 'platform-sneaker')
shoe('Football boot with studs', SH.football_boot(), 'football-boot')
shoe('Track spike', SH.track_spike(), 'track-spike')
shoe('Brogue', SH.brogue(), 'brogue')
shoe('Derby shoe', SH.derby(), 'derby-shoe')
shoe('Penny loafer', SH.loafer(), 'penny-loafer')
shoe('Double monk strap shoe', SH.monk_strap(), 'monk-strap-shoe')
shoe('Boat shoe', SH.boat_shoe(), 'boat-shoe')

import gen_wear_shoes2 as S2
import gen_wear_clothes as CL

shoe('Cowboy boot', S2.cowboy_boot(), 'cowboy-boot')
shoe('Work boot', S2.work_boot(), 'work-boot')
shoe('Ankle boot with a block heel', S2.ankle_boot_heel(), 'ankle-boot-heel')
shoe('Knee-high boot', S2.knee_boot(), 'knee-high-boot')
shoe('Snow boot', S2.snow_boot(), 'snow-boot')
shoe('Sheepskin boot', S2.sheepskin_boot(), 'sheepskin-boot')
shoe('Ski boot', S2.ski_boot(), 'ski-boot')
shoe('Fishing wader', S2.wader(), 'fishing-wader')
shoe('Court shoe (pump)', S2.pump(300), 'court-shoe')
shoe('Kitten heel', S2.pump(150, kitten=True), 'kitten-heel')
shoe('Wedge sandal', S2.wedge_sandal(), 'wedge-sandal')
shoe('Mary Jane shoe', S2.mary_jane(), 'mary-jane')
shoe('Ballet flat', S2.ballet_flat(), 'ballet-flat')
shoe('Ballet pointe shoe', S2.pointe_shoe(), 'pointe-shoe')
shoe('Tap shoe', S2.tap_shoe(), 'tap-shoe')
shoe('Mule', S2.mule(), 'mule')
shoe('Slingback heel', S2.slingback(), 'slingback')
shoe('Strappy heeled sandal', S2.strappy_sandal(), 'strappy-sandal')
shoe('Platform heel', S2.platform_heel(), 'platform-heel')
shoe('Clog', S2.clog(), 'clog')
shoe('Dutch wooden clog', S2.wooden_clog(), 'wooden-clog')
shoe('Espadrille', S2.espadrille(), 'espadrille')
shoe('Gladiator sandal', S2.gladiator(), 'gladiator-sandal')
shoe('Slider', S2.slider(), 'slider')
shoe('Slipper', S2.slipper(), 'slipper')
shoe("Baby's first shoe", S2.baby_shoe(), 'baby-shoe')
shoe('Climbing shoe', S2.climbing_shoe(), 'climbing-shoe')
shoe('Bowling shoe', S2.bowling_shoe(), 'bowling-shoe')
shoe('Quad roller skate', S2.roller_skate(), 'roller-skate')
shoe('Moccasin', S2.moccasin(), 'moccasin')
shoe('Sport sandal', S2.sport_sandal(), 'sport-sandal')
shoe('Basketball shoe', S2.basketball_shoe(), 'basketball-shoe')
shoe('Desert boot', S2.desert_boot(), 'desert-boot')
shoe('Riding boot', S2.riding_boot(), 'riding-boot')
shoe('Trainer sole from below', S2.sole_view(), 'trainer-sole', sx=1)
shoe('Pair of trainers from above', S2.pair_from_above(), 'trainers-from-above', sx=1)

def wear(name, sc, slug):
    add('clothing', name, sc, slug)

wear('Hoodie', CL.hoodie(), 'hoodie')
wear('Jumper', CL.jumper(), 'jumper')
wear('Cardigan', CL.cardigan(), 'cardigan')
wear('Blazer', CL.blazer(), 'blazer')
wear('Trench coat', CL.trench_coat(), 'trench-coat')
wear('Puffer jacket', CL.puffer_jacket(), 'puffer-jacket')
wear('Denim jacket', CL.denim_jacket(), 'denim-jacket')
wear('Hooded raincoat', CL.raincoat(), 'raincoat')
wear('Poncho', CL.poncho(), 'poncho')
wear('Polo shirt', CL.polo_shirt(), 'polo-shirt')
wear('Tank top', CL.tank_top(), 'tank-top')
wear('A-line dress', CL.dress('a-line'), 'a-line-dress')
wear('Wrap dress', CL.dress('wrap'), 'wrap-dress')
wear('Maxi dress', CL.dress('maxi'), 'maxi-dress')
wear('Sundress', CL.dress('sun'), 'sundress')
wear('Pleated skirt', CL.skirt('pleated'), 'pleated-skirt')
wear('Pencil skirt', CL.skirt('pencil'), 'pencil-skirt')
wear('Jeans', CL.trousers('jeans'), 'jeans')
wear('Cargo trousers', CL.trousers('cargo'), 'cargo-trousers')
wear('Dungarees', CL.dungarees(), 'dungarees')
wear('Jumpsuit', CL.jumpsuit(), 'jumpsuit')
wear('Two-piece suit', CL.two_piece_suit(), 'two-piece-suit')
wear('Waistcoat', CL.waistcoat(), 'waistcoat')
wear('Kimono', CL.kimono(), 'kimono')
wear('Apron', CL.apron(), 'apron')
wear('Pyjamas', CL.pyjamas(), 'pyjamas')
wear('Bathrobe', CL.bathrobe(), 'bathrobe')
wear('Knitted scarf', CL.scarf(), 'scarf')
wear('Pair of gloves', CL.gloves(), 'gloves')
wear('Belt', CL.belt(), 'belt')
wear('Baby onesie', CL.onesie(), 'onesie')
wear('Casual outfit flat-lay', CL.outfit('casual'), 'outfit-casual')
wear('Smart outfit flat-lay', CL.outfit('smart'), 'outfit-smart')
wear('Dress outfit flat-lay', CL.outfit('dress'), 'outfit-dress')

save(items, OUT)
if SHEET:
    for c in ('shoes', 'clothing'):
        sub_ = [i for i in items if i.cat == c]
        for k in range(0, len(sub_), 48):
            sheet(sub_[k:k + 48], SHEET.replace('.png', f'_{c}_{k // 48}.png'), cols=8, cell=2.4)
