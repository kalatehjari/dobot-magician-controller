"""Zodiac: the 12 signs as symbols (Tabler icons, MIT), engraved symbols (Hershey), their constellations
(d3-celestial, BSD-3), medallions with names and dates, and three zodiac wheels.
Usage: python3 -I gen_zodiac.py <tabler outline icon dir> <out.json> [sheet.png]"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import gen_constellations as GC

ICONS, OUT = sys.argv[1], sys.argv[2]
SHEET = sys.argv[3] if len(sys.argv) > 3 else None

SIGNS = [  # name, Tabler icon, Hershey astrology glyph index (None: drawn here), constellation id, dates, element
    ('Aries', 'aries', 31, 'Ari', '21 March – 19 April', 'Fire'),
    ('Taurus', 'taurus', 58, 'Tau', '20 April – 20 May', 'Earth'),
    ('Gemini', 'gemini', 60, 'Gem', '21 May – 20 June', 'Air'),
    ('Cancer', 'cancer', 61, 'Cnc', '21 June – 22 July', 'Water'),
    ('Leo', 'leo', 62, 'Leo', '23 July – 22 August', 'Fire'),
    ('Virgo', 'virgo', 63, 'Vir', '23 August – 22 September', 'Earth'),
    ('Libra', 'libra', None, 'Lib', '23 September – 22 October', 'Air'),
    ('Scorpio', 'scorpio', 90, 'Sco', '23 October – 21 November', 'Water'),
    ('Sagittarius', 'sagittarius', 91, 'Sgr', '22 November – 21 December', 'Fire'),
    ('Capricorn', 'capricorn', 92, 'Cap', '22 December – 19 January', 'Earth'),
    ('Aquarius', 'aquarius', 93, 'Aqr', '20 January – 18 February', 'Air'),
    ('Pisces', 'pisces', 0, 'Psc', '19 February – 20 March', 'Water'),
]
TABLER = dict(author='Paweł Kuna (Tabler Icons)', source='tabler-icons', license='MIT')
OWN = dict(author='Made for this library', source='generated', license='public domain')

def fit(L, cx, cy, size):
    """Scales and centres lines so the longest side is `size`."""
    x0, y0, x1, y1 = bbox(L); k = size / max(x1 - x0, y1 - y0, 1e-9)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    return [[(cx + (x - mx) * k, cy + (y - my) * k) for x, y in P] for P in L]

def icon(name):
    return svg_lines(f'{ICONS}/zodiac-{name}.svg')

def libra_engraved(cx, cy, s):
    """Libra in the three-line engraved style of the Hershey glyphs: a beam with a raised arch (an
    omega with flat feet) over a straight line."""
    out = []
    ya, r, yb = cy - 0.18 * s, 0.25 * s, cy - 0.05 * s
    t = math.asin((yb - ya) / r)
    for d in (-0.03, 0, 0.03):
        top = arc(cx, ya + d * s, r, math.pi - t, 2 * math.pi + t, n=48)
        out.append([(cx - 0.55 * s, yb + d * s)] + top + [(cx + 0.55 * s, yb + d * s)])
        out.append([(cx - 0.55 * s, cy + 0.15 * s + d * s), (cx + 0.55 * s, cy + 0.15 * s + d * s)])
    return out

def hershey_symbol(idx):
    if idx is None: return libra_engraved(0, 0, 1000)
    return [smooth(P, iters=3, corner_deg=50) for P in glyph_lines('astrology', chr(33 + idx), 0, 0, 1000)]

def four_star(x, y, r):
    return [[(x, y - r), (x + r * 0.25, y - r * 0.25), (x + r, y), (x + r * 0.25, y + r * 0.25), (x, y + r), (x - r * 0.25, y + r * 0.25), (x - r, y), (x - r * 0.25, y - r * 0.25), (x, y - r)]]

items = []
def add(L, name, slug, meta, title=''):
    it = Item('zodiac', name, L, title=title or name, **meta); it.slug = slug; items.append(it)

# 1) symbols, clean single lines
for nm, ic, hx, cid, dates, el in SIGNS:
    add(fit(icon(ic), 500, 500, 1000), f'{nm} symbol', f'{nm.lower()}-symbol', TABLER, f'{nm} (Tabler icon zodiac-{ic})')
# 2) engraved symbols
for nm, ic, hx, cid, dates, el in SIGNS:
    add(fit(hershey_symbol(hx), 500, 500, 1000), f'{nm} engraved', f'{nm.lower()}-engraved', OWN if hx is None else
        dict(author='A. V. Hershey (Hershey fonts)', source='hershey', license='Hershey fonts (free use with acknowledgement)'), f'{nm}, engraved symbol')
# 3) constellations with their symbol
for nm, ic, hx, cid, dates, el in SIGNS:
    L = GC.build(cid, GC.features(cid), nm, label_size=46)
    b = bbox(L)
    sym = fit(icon(ic), (b[0] + b[2]) / 2, b[1] - 130, 150)
    add(L + sym, f'{nm} constellation', f'{nm.lower()}-constellation',
        dict(author='Olaf Frohn (d3-celestial); Tabler Icons', source='d3-celestial', license='BSD-3-Clause; MIT'), f'The constellation of {nm} with its sign')
# 4) medallions: double ring, name above, dates below, the symbol in the middle
for nm, ic, hx, cid, dates, el in SIGNS:
    L = [circle(0, 0, 500, n=160), circle(0, 0, 476, n=150), circle(0, 0, 330, n=120)]
    L += text_arc(nm.upper(), 0, 0, 372, 0, size=62, font='HersheySerifMed', spacing=14)
    L += text_arc(dates, 0, 0, 404, 0, size=34, font='HersheySans1', spacing=2, bottom=True)
    L += four_star(-403, 0, 22) + four_star(403, 0, 22)
    L += fit(icon(ic), 0, 0, 380)
    L += text(el.upper(), 0, 228, size=30, font='HersheySans1', spacing=8)
    add(L, f'{nm} medallion', f'{nm.lower()}-medallion', dict(author='Made for this library (symbol: Tabler Icons)', source='generated', license='public domain; symbol MIT'), f'{nm} medallion with its dates')

# 5) wheels
def wheel(kind):
    L = [circle(0, 0, 500, n=200), circle(0, 0, 300, n=140)]
    if kind != 'plain': L.append(circle(0, 0, 400, n=170))
    for i in range(12):
        a = math.radians(i * 30 - 15)
        L.append([(300 * math.sin(a), -300 * math.cos(a)), (500 * math.sin(a), -500 * math.cos(a))])
    for i, (nm, ic, hx, cid, dates, el) in enumerate(SIGNS):
        a = math.radians(i * 30)
        if kind == 'names':
            L += fit(icon(ic), 350 * math.sin(a), -350 * math.cos(a), 70)
            low = 90 < i * 30 < 270                     # names on the lower half read the right way up
            L += text_arc(nm.upper(), 0, 0, 438 if not low else 462, i * 30 if not low else i * 30 - 180, size=22, font='HersheySans1', spacing=3, bottom=low)
        elif kind == 'engraved':
            L += fit(hershey_symbol(hx), 450 * math.sin(a), -450 * math.cos(a), 70)
            L += fit(icon(ic), 350 * math.sin(a), -350 * math.cos(a), 60)
        else:
            L += fit(icon(ic), 400 * math.sin(a), -400 * math.cos(a), 110)
    # the sun in the middle
    L.append(circle(0, 0, 95, n=60))
    for k in range(16):
        a = 2 * math.pi * k / 16; r0, r1 = 120, 250 if k % 2 == 0 else 190
        L.append([(r0 * math.cos(a), r0 * math.sin(a)), (r1 * math.cos(a), r1 * math.sin(a))])
    return L
add(wheel('names'), 'Zodiac wheel with names', 'wheel-names', dict(author='Made for this library (symbols: Tabler Icons)', source='generated', license='public domain; symbols MIT'))
add(wheel('engraved'), 'Zodiac wheel, two rings', 'wheel-engraved', dict(author='Made for this library (Hershey and Tabler symbols)', source='generated', license='public domain; symbols MIT'))
add(wheel('plain'), 'Zodiac wheel', 'wheel', dict(author='Made for this library (symbols: Tabler Icons)', source='generated', license='public domain; symbols MIT'))

save(items, OUT)
if SHEET:
    for i in range(0, len(items), 56):
        sheet(items[i:i + 56], SHEET.replace('.png', f'_{i // 56}.png'), cols=8)
