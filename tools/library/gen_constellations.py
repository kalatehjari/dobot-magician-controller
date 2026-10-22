"""Constellations: the stick figures of all 88 constellations, stars sized by brightness, with the name.
Data: d3-celestial by Olaf Frohn (BSD 3-clause): constellation lines, star positions and brightness
(Hipparcos / XHIP catalogues). Usage: python3 -I gen_constellations.py <d3-celestial data dir> <out.json> [sheet.png]"""
import json, math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

DATA = sys.argv[1] if __name__ == '__main__' else os.environ.get('D3_CELESTIAL_DATA', 'node_modules/d3-celestial/data')
lines = json.load(open(f'{DATA}/constellations.lines.json'))['features']
names = {f['id']: f['properties'] for f in json.load(open(f'{DATA}/constellations.json'))['features']}
stars = json.load(open(f'{DATA}/stars.6.json'))['features']
starnames = json.load(open(f'{DATA}/starnames.json'))

def vec(ra, dec):
    a, d = math.radians(ra), math.radians(dec)
    return np.array([math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)])

SV = np.array([vec(*s['geometry']['coordinates']) for s in stars])
SMAG = np.array([s['properties']['mag'] for s in stars])
SCON = [starnames.get(str(s['id']), {}).get('c') for s in stars]

def project(c):
    """Stereographic projection centred on c, north up and east to the left (as the sky is seen)."""
    ra = math.atan2(c[1], c[0]); dec = math.asin(max(-1, min(1, c[2])))
    e = np.array([-math.sin(ra), math.cos(ra), 0.0])
    n = np.array([-math.sin(dec) * math.cos(ra), -math.sin(dec) * math.sin(ra), math.cos(dec)])
    def f(p):
        k = 2 / (1 + float(p @ c))
        return (-k * float(p @ e), -k * float(p @ n))        # screen: x right, y down
    return f

def star_shape(x, y, mag, scale):
    """Brighter stars are bigger: a five-pointed star for the brightest, rings for the rest."""
    if mag <= 1.2: return [star(x, y, 34 * scale, 14 * scale, 5)], 34 * scale
    if mag <= 2.2: return [circle(x, y, 20 * scale, n=28), circle(x, y, 7 * scale, n=12)], 20 * scale
    if mag <= 3.2: return [circle(x, y, 14 * scale, n=22)], 14 * scale
    if mag <= 4.2: return [circle(x, y, 10 * scale, n=16)], 10 * scale
    return [circle(x, y, 6.5 * scale, n=12)], 6.5 * scale

def build(cid, feats, label, label_size=42, upper=True):
    segs = [[vec(*p) for p in ln] for f in feats for ln in f['geometry']['coordinates']]
    pts = [p for s in segs for p in s]
    c = np.mean(pts, axis=0); c /= np.linalg.norm(c)
    P = project(c)
    # magnitude of every vertex: the nearest catalogue star
    mags = {}
    for p in pts:
        d = SV @ p; i = int(np.argmax(d))
        key = tuple(np.round(p, 6)); mags[key] = SMAG[i] if d[i] > math.cos(math.radians(0.3)) else 4.5
    xy = [[P(p) for p in s] for s in segs]
    allxy = [q for s in xy for q in s]
    xs = [q[0] for q in allxy]; ys = [q[1] for q in allxy]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1
    k = 1000 / span
    xy = [[(x * k, y * k) for x, y in s] for s in xy]
    scale = 1.0
    out, centres = [], {}
    for s, sv in zip(xy, segs):
        for (x, y), p in zip(s, sv):
            key = tuple(np.round(p, 6))
            centres[(round(x, 3), round(y, 3))] = mags[key]
    radius = {}
    for (x, y), m in centres.items():
        shp, r = star_shape(x, y, m, scale); out += shp; radius[(x, y)] = r
    # the figure's lines, stopping short of the stars
    for s in xy:
        for (x0, y0), (x1, y1) in zip(s, s[1:]):
            r0 = radius[(round(x0, 3), round(y0, 3))] + 11; r1 = radius[(round(x1, 3), round(y1, 3))] + 11
            L = math.hypot(x1 - x0, y1 - y0)
            if L <= r0 + r1 + 4: continue
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            out.append([(x0 + ux * r0, y0 + uy * r0), (x1 - ux * r1, y1 - uy * r1)])
    # other bright stars of the constellation (not on the figure) as small rings
    X0, X1, Y0, Y1 = min(xs) * k, max(xs) * k, min(ys) * k, max(ys) * k
    for i, con in enumerate(SCON):
        if con != cid or SMAG[i] > 5.2 or float(SV[i] @ c) < 0.5: continue
        x, y = P(SV[i]); x *= k; y *= k
        if not (X0 - 60 <= x <= X1 + 60 and Y0 - 60 <= y <= Y1 + 60): continue
        if any(math.hypot(x - cx, y - cy) < 40 for cx, cy in centres): continue
        shp, r = star_shape(x, y, max(SMAG[i], 3.3), scale); out += shp; centres[(round(x, 3), round(y, 3))] = SMAG[i]
    # name underneath, spaced capitals
    b = bbox(out)
    cap = 42
    if label:
        cap = label_size
        out += text(label.upper() if upper else label, (b[0] + b[2]) / 2, b[3] + 70 + cap, size=cap, font='HersheySans1', spacing=8 if upper else 2)
    return out

def features(cid):
    return [f for f in lines if f['id'] == cid]

def main(OUT, SHEET=None):
  items = []
  by_id = {}
  for f in lines: by_id.setdefault(f['id'], []).append(f)
  for cid in sorted(by_id, key=lambda c: names[c]['name']):
      feats = by_id[cid]
      nm = names[cid]['name']
      if cid == 'Ser' and len(feats) == 2:
          # Serpens is in two parts, either side of Ophiuchus: the head (west) and the tail (east)
          f0, f1 = feats
          ra0 = np.mean([p[0] for ln in f0['geometry']['coordinates'] for p in ln]); ra1 = np.mean([p[0] for ln in f1['geometry']['coordinates'] for p in ln])
          head, tail = (f0, f1) if ra0 < ra1 else (f1, f0)
          for part, lab, slug in ((head, 'Serpens Caput', 'serpens-caput'), (tail, 'Serpens Cauda', 'serpens-cauda')):
              it = Item('constellations', lab, build(cid, [part], lab), author='Olaf Frohn (d3-celestial); star data Hipparcos/XHIP',
                        source='d3-celestial', license='BSD-3-Clause', title=f'{lab} ({names[cid]["gen"] if "gen" in names[cid] else "Serpentis"})')
              it.slug = slug; items.append(it)
          continue
      it = Item('constellations', nm, build(cid, feats, nm), author='Olaf Frohn (d3-celestial); star data Hipparcos/XHIP',
                source='d3-celestial', license='BSD-3-Clause', title=f'{nm} — {names[cid].get("en", nm)}')
      it.slug = nm.lower().replace(' ', '-')
      items.append(it)
  save(items, OUT)
  if SHEET:
      for i in range(0, len(items), 48):
          sheet(items[i:i + 48], SHEET.replace('.png', f'_{i // 48}.png'), cols=8)


if __name__ == '__main__':
    main(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
