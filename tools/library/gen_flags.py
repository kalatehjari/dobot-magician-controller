"""Flags: national flags as line drawings that keep their colours. Source: flag-icons (MIT licence,
(c) Panayiotis Lipiridis and contributors), flags/4x3/<code>.svg (viewBox 640x480).

Each SVG is painted in document order (painter's model) into a partition of the flag rectangle into
colour regions. Every region's outline rings (exterior and holes, closed) are the pen lines; a border
shared by two regions is drawn by both, so each region stays a closed outline that the app can fill.
fills = [['#rrggbb', a, b], ...]: lines[a:b] are the rings of one colour region (even-odd rule).

Usage: python3 -I gen_flags.py <flag-icons package dir> <out.json> [sheet.png]
  sheet.png -> <sheet>_<n>.png (pen lines) and <sheet>_colour_<n>.png (filled preview)"""
import json, math, os, re, sys
import xml.etree.ElementTree as ET
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, LinearRing, box
from shapely import affinity
import svgelements as se
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Item, save, sheet, export_size

W, H = 640.0, 480.0
FLAG = box(0, 0, W, H)
GRID = 0.01                      # precision grid for every overlay (640 scale)
OUTK = 1000.0 / W                # output scale: 1000 x 750
XLINK = '{http://www.w3.org/1999/xlink}href'

# ============================================================== which flags
# (code, name); names are the common English names
FLAGS = [
    # required
    ('nz', 'New Zealand'), ('ir', 'Iran'), ('au', 'Australia'), ('gb', 'United Kingdom'), ('us', 'United States'),
    ('ca', 'Canada'), ('fr', 'France'), ('de', 'Germany'), ('it', 'Italy'), ('jp', 'Japan'), ('cn', 'China'),
    ('in', 'India'), ('kr', 'South Korea'), ('br', 'Brazil'),
    # Europe
    ('ie', 'Ireland'), ('gb-eng', 'England'), ('gb-sct', 'Scotland'), ('nl', 'Netherlands'), ('be', 'Belgium'), ('ch', 'Switzerland'),
    ('at', 'Austria'), ('se', 'Sweden'), ('no', 'Norway'), ('dk', 'Denmark'), ('fi', 'Finland'), ('is', 'Iceland'), ('pl', 'Poland'),
    ('ua', 'Ukraine'), ('gr', 'Greece'), ('cz', 'Czechia'), ('hu', 'Hungary'), ('ro', 'Romania'), ('ee', 'Estonia'), ('ru', 'Russia'),
    ('tr', 'Türkiye'), ('eu', 'European Union'),
    # Asia and the Middle East
    ('vn', 'Vietnam'), ('th', 'Thailand'), ('id', 'Indonesia'), ('my', 'Malaysia'), ('ph', 'Philippines'), ('sg', 'Singapore'),
    ('pk', 'Pakistan'), ('bd', 'Bangladesh'), ('np', 'Nepal'), ('mn', 'Mongolia'), ('la', 'Laos'), ('lb', 'Lebanon'),
    ('ae', 'United Arab Emirates'), ('qa', 'Qatar'), ('kw', 'Kuwait'), ('jo', 'Jordan'),
    # Africa
    ('za', 'South Africa'), ('ng', 'Nigeria'), ('gh', 'Ghana'), ('eg', 'Egypt'), ('ma', 'Morocco'), ('tn', 'Tunisia'), ('dz', 'Algeria'),
    ('et', 'Ethiopia'), ('tz', 'Tanzania'), ('sn', 'Senegal'), ('cm', 'Cameroon'), ('bw', 'Botswana'), ('na', 'Namibia'),
    ('rw', 'Rwanda'), ('ug', 'Uganda'), ('cd', 'DR Congo'), ('so', 'Somalia'), ('mg', 'Madagascar'),
    # the Americas
    ('ar', 'Argentina'), ('cl', 'Chile'), ('co', 'Colombia'), ('pe', 'Peru'), ('ve', 'Venezuela'), ('uy', 'Uruguay'), ('cu', 'Cuba'),
    ('jm', 'Jamaica'), ('bs', 'Bahamas'), ('tt', 'Trinidad and Tobago'), ('pa', 'Panama'), ('cr', 'Costa Rica'), ('gl', 'Greenland'),
    # Oceania
    ('ws', 'Samoa'), ('to', 'Tonga'), ('ck', 'Cook Islands'), ('pg', 'Papua New Guinea'), ('sb', 'Solomon Islands'), ('vu', 'Vanuatu'),
    ('ki', 'Kiribati'), ('tv', 'Tuvalu'), ('fm', 'Micronesia'), ('mh', 'Marshall Islands'), ('nr', 'Nauru'), ('pw', 'Palau'),
]

# ============================================================== affine matrices (a, b, c, d, e, f)
# x' = a x + c y + e,  y' = b x + d y + f   (SVG convention)
IDM = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

def mul(P, C):
    """P after C."""
    return (P[0] * C[0] + P[2] * C[1], P[1] * C[0] + P[3] * C[1], P[0] * C[2] + P[2] * C[3], P[1] * C[2] + P[3] * C[3],
            P[0] * C[4] + P[2] * C[5] + P[4], P[1] * C[4] + P[3] * C[5] + P[5])

def parse_tf(s):
    m = se.Matrix(s)
    return (m.a, m.b, m.c, m.d, m.e, m.f)

def apply_m(M, pts):
    pts = np.asarray(pts, float)
    return np.column_stack([M[0] * pts[:, 0] + M[2] * pts[:, 1] + M[4], M[1] * pts[:, 0] + M[3] * pts[:, 1] + M[5]])

def geom_m(M, g):
    return affinity.affine_transform(g, [M[0], M[2], M[1], M[3], M[4], M[5]])

def smax(M):
    """Largest singular value: how much the matrix can stretch a length."""
    a, b, c, d = M[:4]
    t = a * a + b * b + c * c + d * d; det = a * d - b * c
    return math.sqrt(max(1e-18, (t + math.sqrt(max(0.0, t * t - 4 * det * det))) / 2))

# ============================================================== small parsers
def num(v, default=0.0):
    if v is None: return default
    m = re.match(r'\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)', str(v))
    return float(m.group(1)) if m else default

def length(v):
    v = str(v).strip()
    if v.endswith('pt'): return num(v) * 4 / 3
    if v.endswith('mm'): return num(v) * 96 / 25.4
    return num(v)

def local(tag):
    return tag.split('}')[-1] if isinstance(tag, str) else ''

def props(el):
    d = {k: v for k, v in el.attrib.items() if '}' not in k}
    if 'style' in d:
        for part in d.pop('style').split(';'):
            if ':' in part:
                k, v = part.split(':', 1); d[k.strip()] = v.strip()
    return d

def ref_id(v):
    m = re.search(r'#([^)\s\'"]+)', v or '')
    return m.group(1) if m else None

INHERITED = {'fill': 'black', 'fill-rule': 'nonzero', 'fill-opacity': '1', 'stroke': 'none', 'stroke-width': '1',
             'stroke-linecap': 'butt', 'stroke-linejoin': 'miter', 'stroke-miterlimit': '4', 'stroke-opacity': '1',
             'color': 'black', 'visibility': 'visible', 'clip-rule': 'nonzero'}
SKIP = {'defs', 'clipPath', 'marker', 'linearGradient', 'radialGradient', 'title', 'desc', 'metadata', 'symbol', 'style',
        'mask', 'pattern', 'text', 'image', 'filter', 'stop'}
SHAPES = {'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon'}
CAPS = {'butt': 'flat', 'round': 'round', 'square': 'square'}
JOINS = {'miter': 'mitre', 'miter-clip': 'mitre', 'arcs': 'mitre', 'round': 'round', 'bevel': 'bevel'}

def segments_of(tag, p):
    try:
        if tag == 'path': return list(se.Path(p.get('d', '')).segments())
        if tag == 'rect':
            w, h = length(p.get('width', 0)), length(p.get('height', 0))
            if w <= 0 or h <= 0: return []
            rx, ry = p.get('rx'), p.get('ry')
            rx = length(rx) if rx is not None else None; ry = length(ry) if ry is not None else None
            if rx is None: rx = ry or 0.0
            if ry is None: ry = rx
            return list(se.Rect(length(p.get('x', 0)), length(p.get('y', 0)), w, h, rx, ry).segments())
        if tag == 'circle':
            r = length(p.get('r', 0))
            return list(se.Circle(length(p.get('cx', 0)), length(p.get('cy', 0)), r).segments()) if r > 0 else []
        if tag == 'ellipse':
            rx, ry = length(p.get('rx', 0)), length(p.get('ry', 0))
            return list(se.Ellipse(length(p.get('cx', 0)), length(p.get('cy', 0)), rx, ry).segments()) if rx > 0 and ry > 0 else []
        if tag == 'line':
            return list(se.Path(f"M{p.get('x1', 0)} {p.get('y1', 0)}L{p.get('x2', 0)} {p.get('y2', 0)}").segments())
        if tag in ('polyline', 'polygon'):
            v = [float(t) for t in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', p.get('points', ''))]
            if len(v) < 4: return []
            d = 'M' + ' '.join(f'{v[i]} {v[i + 1]}' for i in range(0, len(v) - 1, 2)) + ('z' if tag == 'polygon' else '')
            return list(se.Path(d).segments())
    except Exception as ex:
        print('  segment error', tag, ex)
    return []

def sample(segs, scale, step=0.9):
    """Subpaths [(points ndarray (local units), closed)]; curves sampled about every `step` device units."""
    subs, cur = [], None
    def flush(closed):
        nonlocal cur
        if cur is not None and len(cur) > 1:
            subs.append((np.array(cur, float), closed))
        cur = None
    for seg in segs:
        if isinstance(seg, se.Move):
            flush(False); cur = [(seg.end.x, seg.end.y)]
        elif isinstance(seg, se.Close):
            if cur is not None:
                if math.hypot(cur[-1][0] - cur[0][0], cur[-1][1] - cur[0][1]) < 1e-6: cur[-1] = cur[0]
                else: cur.append(cur[0])
            flush(True)
        elif isinstance(seg, se.Line):
            if cur is None: cur = [(seg.start.x, seg.start.y)]
            cur.append((seg.end.x, seg.end.y))
        else:
            if cur is None: cur = [(seg.start.x, seg.start.y)]
            q = seg.npoint(np.linspace(0, 1, 17))
            L = float(np.hypot(*np.diff(q, axis=0).T).sum()) * scale
            n = int(min(1500, max(4, math.ceil(L / step))))
            cur.extend(map(tuple, seg.npoint(np.linspace(0, 1, n + 1)[1:])))
    flush(False)
    return subs

def vertices(segs):
    out = []
    for seg in segs:
        if seg.end is not None: out.append((seg.end.x, seg.end.y))
    return out

# ============================================================== geometry of a painted shape
def ring_area(r):
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))

def winding(px, py, r):
    x0, y0, x1, y1 = r[:-1, 0], r[:-1, 1], r[1:, 0], r[1:, 1]
    left = (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0)
    up = (y0 <= py) & (y1 > py) & (left > 0)
    down = (y0 > py) & (y1 <= py) & (left < 0)
    return int(up.sum()) - int(down.sum())

def fill_area(rings, rule):
    """Exact fill of a set of (device) rings with the even-odd or non-zero rule."""
    R = []
    for r in rings:
        r = np.asarray(r, float)
        if len(r) < 3: continue
        gap = float(np.hypot(*(r[0] - r[-1])))
        if gap > 1e-6: r = np.vstack([r, r[:1]])
        elif gap > 0: r = r.copy(); r[-1] = r[0]
        if len(r) < 4 or abs(ring_area(r)) < 1e-9: continue
        R.append(r)
    if not R: return Polygon()
    if len(R) == 1:
        g = Polygon(R[0])
        if g.is_valid: return g
    noded = shapely.union_all([LineString(r) for r in R])
    faces = shapely.get_parts(shapely.polygonize(shapely.get_parts(noded)))
    keep = []
    for f in faces:
        if f.is_empty or f.area < 1e-9: continue
        pt = f.representative_point()
        w = sum(winding(pt.x, pt.y, r) for r in R)
        if (w % 2 != 0) if rule == 'evenodd' else (w != 0): keep.append(f)
    return shapely.union_all(keep) if keep else Polygon()

def stroke_area(subs, w, cap, join, ml):
    parts = []
    for pts, closed in subs:
        keep = [0] + [i for i in range(1, len(pts)) if np.hypot(*(pts[i] - pts[i - 1])) > 1e-9]
        pts = pts[keep]
        if len(pts) < 2: continue
        js, ml = JOINS.get(join, 'mitre'), max(1.0, ml)
        if closed and len(pts) >= 4:
            g = LinearRing(pts).buffer(w / 2, join_style=js, mitre_limit=ml, quad_segs=8)
        else:
            g = LineString(pts).buffer(w / 2, cap_style=CAPS.get(cap, 'flat'), join_style=js, mitre_limit=ml, quad_segs=8)
        parts.append(g)
    return shapely.union_all(parts) if parts else Polygon()

# ============================================================== SVG walker: painted shapes in order
class FlagSVG:
    def __init__(self, path):
        self.root = ET.parse(path).getroot()
        self.ids = {e.get('id'): e for e in self.root.iter() if e.get('id')}
        self.paints = []          # (geometry in 640x480, '#rrggbb', alpha)
        st = dict(INHERITED); st['_op'] = 1.0
        self.walk(self.root, IDM, st, FLAG, self.paints)

    def colour(self, v, s):
        v = (v or '').strip()
        if v.startswith('url('):
            return self.gradient_colour(ref_id(v))
        if v == 'currentColor': v = s.get('color', 'black')
        if v in ('', 'none', 'transparent'): return None
        try:
            c = se.Color(v)
        except Exception:
            return None
        if c.value is None: return None
        return c.hex[:7].lower()

    def gradient_colour(self, gid):
        g, stops, seen = self.ids.get(gid), [], set()
        while g is not None and not stops and gid not in seen:
            seen.add(gid)
            stops = [e for e in g if local(e.tag) == 'stop']
            if not stops:
                gid = ref_id(g.get(XLINK) or g.get('href')); g = self.ids.get(gid)
        if not stops: return None
        cols = []
        for e in stops:
            p = props(e); c = se.Color(p.get('stop-color', 'black'))
            cols.append((c.red, c.green, c.blue))
        r, gg, b = (int(round(sum(c[i] for c in cols) / len(cols))) for i in range(3))
        return f'#{r:02x}{gg:02x}{b:02x}'

    def emit(self, out, g, col, a, clip):
        if g is None or g.is_empty: return
        g = shapely.intersection(g, clip if clip is not None else FLAG, grid_size=GRID)
        g = shapely.union_all([p for p in shapely.get_parts(g) if p.geom_type == 'Polygon'])
        if not g.is_empty and g.area > 1e-6: out.append((g, col, a))

    def style(self, el, st):
        p = props(el); s = dict(st)
        for k in INHERITED:
            if k in p and p[k] != 'inherit': s[k] = p[k]
        if 'opacity' in p: s['_op'] = st['_op'] * num(p['opacity'], 1.0)
        return p, s

    def clip_geom(self, cp, M):
        p = props(cp)
        Mc = mul(M, parse_tf(p['transform'])) if 'transform' in p else M
        tmp = []; s = dict(INHERITED); s['_op'] = 1.0
        for ch in cp: self.walk(ch, Mc, s, None, tmp, clipmode=True)
        return shapely.union_all([g for g, c, a in tmp], grid_size=GRID) if tmp else Polygon()

    def walk(self, el, M, st, clip, out, clipmode=False, depth=0):
        tag = local(el.tag)
        if tag in SKIP or depth > 60: return
        p, s = self.style(el, st)
        if p.get('display') == 'none' or s.get('visibility') == 'hidden': return
        M2 = mul(M, parse_tf(p['transform'])) if 'transform' in p else M
        if 'clip-path' in p and not clipmode:
            cid = ref_id(p['clip-path'])
            if cid in self.ids:
                cg = self.clip_geom(self.ids[cid], M2)
                clip = shapely.intersection(clip, cg, grid_size=GRID) if clip is not None else cg
                if clip.is_empty: return
        if tag in ('svg', 'g', 'a', 'switch'):
            for ch in el: self.walk(ch, M2, s, clip, out, clipmode, depth + 1)
        elif tag == 'use':
            rid = ref_id(el.get(XLINK) or el.get('href'))
            if rid in self.ids:
                M3 = mul(M2, (1, 0, 0, 1, length(p.get('x', 0)), length(p.get('y', 0))))
                self.walk(self.ids[rid], M3, s, clip, out, clipmode, depth + 1)
        elif tag in SHAPES:
            self.shape(el, tag, p, M2, s, clip, out, clipmode)

    def shape(self, el, tag, p, M, s, clip, out, clipmode):
        segs = segments_of(tag, p)
        if not segs: return
        subs = sample(segs, smax(M))
        if not subs: return
        if clipmode:
            g = fill_area([apply_m(M, pts) for pts, closed in subs], s.get('clip-rule', 'nonzero'))
            if not g.is_empty: out.append((g, None, 1.0))
            return
        fill = s['fill']
        if fill != 'none':
            col = self.colour(fill, s); a = s['_op'] * num(s['fill-opacity'], 1.0)
            if col and a > 0.004:
                self.emit(out, fill_area([apply_m(M, pts) for pts, closed in subs], s['fill-rule']), col, a, clip)
        stroke, sw = s['stroke'], length(s['stroke-width'])
        if stroke != 'none' and sw > 0:
            col = self.colour(stroke, s); a = s['_op'] * num(s['stroke-opacity'], 1.0)
            if col and a > 0.004:
                g = stroke_area(subs, sw, s['stroke-linecap'], s['stroke-linejoin'], num(s['stroke-miterlimit'], 4.0))
                self.emit(out, geom_m(M, g), col, a, clip)
        for key in ('marker-start', 'marker-mid', 'marker-end'):
            mid = ref_id(p.get(key))
            if mid in self.ids: self.markers(self.ids[mid], key, segs, M, sw, clip, out)

    def markers(self, mk, key, segs, M, sw, clip, out):
        mp = props(mk)
        mw, mh = length(mp.get('markerWidth', 3)), length(mp.get('markerHeight', 3))
        k = sw if mp.get('markerUnits', 'strokeWidth') == 'strokeWidth' else 1.0
        V = vertices(segs)
        V = V[:1] if key == 'marker-start' else V[-1:] if key == 'marker-end' else V[1:-1]
        st = dict(INHERITED); st['_op'] = 1.0
        _, st = self.style(self.root, st); _, st = self.style(mk, st)
        vb = [num(t) for t in mp['viewBox'].replace(',', ' ').split()] if 'viewBox' in mp else None
        for vx, vy in V:
            Mm = mul(mul(M, (1, 0, 0, 1, vx, vy)), (k, 0, 0, k, 0, 0))
            mclip = geom_m(Mm, box(0, 0, mw, mh))
            mclip = shapely.intersection(mclip, clip, grid_size=GRID) if clip is not None else mclip
            if vb:
                q = min(mw / vb[2], mh / vb[3])
                Mm = mul(Mm, (q, 0, 0, q, -vb[0] * q, -vb[1] * q))
            Mm = mul(Mm, (1, 0, 0, 1, -num(mp.get('refX', 0)), -num(mp.get('refY', 0))))
            for ch in mk: self.walk(ch, Mm, st, mclip, out)

# ============================================================== painter's model -> colour regions
def blend(under, over, a):
    u = [int(under[i:i + 2], 16) for i in (1, 3, 5)]; o = [int(over[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{int(round(a * oo + (1 - a) * uu)):02x}' for uu, oo in zip(u, o))

def paint(paints):
    """Colour -> visible region (MultiPolygon). Consecutive opaque shapes of one colour are painted together."""
    groups = []
    for g, col, a in paints:
        if groups and groups[-1][1] == col and a >= 0.999 and groups[-1][2] >= 0.999: groups[-1][0].append(g)
        else: groups.append(([g], col, a))
    regions = {}
    for gs, col, a in groups:
        G = shapely.union_all(gs, grid_size=GRID)
        if G.is_empty: continue
        if a >= 0.999:
            for k in list(regions):
                if k != col and regions[k].intersects(G):
                    regions[k] = shapely.difference(regions[k], G, grid_size=GRID)
            regions[col] = shapely.union(regions[col], G, grid_size=GRID) if col in regions else G
        else:
            new, covered = {}, []
            for k in list(regions):
                if regions[k].intersects(G):
                    ov = shapely.intersection(regions[k], G, grid_size=GRID)
                    if ov.is_empty: continue
                    regions[k] = shapely.difference(regions[k], G, grid_size=GRID)
                    new.setdefault(blend(k, col, a), []).append(ov); covered.append(ov)
            rest = shapely.difference(G, shapely.union_all(covered, grid_size=GRID), grid_size=GRID) if covered else G
            if not rest.is_empty: new.setdefault(blend('#ffffff', col, a), []).append(rest)
            for k, L in new.items():
                regions[k] = shapely.union_all(([regions[k]] if k in regions else []) + L, grid_size=GRID)
    return {k: v for k, v in regions.items() if not v.is_empty}

# ============================================================== clean-up
def polys(g):
    return [p for p in shapely.get_parts(g) if p.geom_type == 'Polygon' and not p.is_empty and p.area > 1e-9]

def lab(h):
    rgb = []
    for i in (1, 3, 5):
        c = int(h[i:i + 2], 16) / 255
        rgb.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = rgb
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047; y = 0.2126 * r + 0.7152 * g + 0.0722 * b; z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return (116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z)))

def delta_e(c1, c2):
    a, b = lab(c1), lab(c2)
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

def merge_colours(regions, limit):
    """Merges colours that are clearly the same (Lab distance below `limit`) into the bigger one."""
    cols = sorted(regions, key=lambda k: -regions[k].area)
    alias = {}
    for i, c in enumerate(cols):
        for d in cols[:i]:
            if d not in alias and delta_e(c, d) < limit:
                alias[c] = d; break
    out = {}
    for c in cols:
        t = alias.get(c, c)
        out[t] = shapely.union(out[t], regions[c], grid_size=GRID) if t in out else regions[c]
    return out, alias

def is_small(p, min_area, thin):
    if p.area < min_area: return True
    return p.buffer(-thin, join_style='mitre').is_empty

def absorb_small(faces, min_area, thin):
    """faces: list [geometry, colour]; colour None = unpainted. Small or thin faces go to the neighbour
    with the longest shared border."""
    merged = 0
    while True:
        small = sorted((i for i, (g, c) in enumerate(faces) if is_small(g, min_area, thin)), key=lambda i: faces[i][0].area)
        if not small: break
        tree = shapely.STRtree([g for g, c in faces])
        gone, grown = set(), set()
        for i in small:
            if i in grown: continue          # it took in a neighbour this round: look at it again next round
            g = faces[i][0]
            best, bl = None, 0.0
            for j in tree.query(g.buffer(0.05)):
                if j == i or j in gone: continue
                L = shapely.intersection(g.boundary, faces[j][0].buffer(0.02)).length
                if L > bl + 1e-9: best, bl = j, L
            if best is None: continue
            faces[best][0] = shapely.union(faces[best][0], g, grid_size=GRID)
            gone.add(i); grown.add(best); merged += 1
        if not gone: break
        faces[:] = [f for k, f in enumerate(faces) if k not in gone]
    return merged

def regions_to_faces(regions, with_bg=True):
    faces = [[p, c] for c, g in regions.items() for p in polys(g)]
    if with_bg:
        painted = shapely.union_all([g for g in regions.values()], grid_size=GRID)
        faces += [[p, None] for p in polys(shapely.difference(FLAG, painted, grid_size=GRID))]
    return faces

def renode(faces):
    """The same faces rebuilt from one noded set of borders, so that neighbours share exactly the same
    vertices (a valid coverage)."""
    lines = shapely.union_all([g.boundary for g, c in faces], grid_size=GRID)
    tree = shapely.STRtree([g for g, c in faces])
    out = []
    for p in shapely.get_parts(shapely.polygonize(shapely.get_parts(lines))):
        if p.is_empty or p.area < 1e-9: continue
        pt = p.representative_point()
        js = tree.query(pt, predicate='intersects')
        if len(js) == 0: js = tree.query(p, predicate='intersects')
        if len(js) == 0: continue
        j = max(js, key=lambda j: shapely.intersection(faces[j][0], p).area) if len(js) > 1 else js[0]
        out.append([p, faces[j][1]])
    return out

def faces_to_regions(faces):
    by = {}
    for g, c in faces: by.setdefault(c, []).append(g)
    return {c: shapely.union_all(L, grid_size=GRID) for c, L in by.items()}

def clean(regions, merge_de=4.0, min_area=4.0, thin=0.55, tol=0.4, report=None):
    report = report if report is not None else {}
    regions, alias = merge_colours(regions, merge_de)
    report['merged_colours'] = alias
    faces = regions_to_faces(regions)
    report['specks'] = absorb_small(faces, min_area, thin)
    regions = faces_to_regions(faces)
    faces = renode(regions_to_faces(regions, with_bg=False))   # the unpainted part (colour None) is in there too
    # simplify every shared border once, so neighbouring regions keep matching edges
    arr = np.array([g for g, c in faces], dtype=object)
    ok = bool(shapely.coverage_is_valid(arr))
    report['coverage_valid'] = ok
    if ok:
        simp = shapely.coverage_simplify(arr, tol)
    else:
        simp = [shapely.simplify(g, tol, preserve_topology=True) for g in arr]
    faces = [[shapely.make_valid(g) if not g.is_valid else g, c] for g, (_, c) in zip(simp, faces)]
    faces = [[p, c] for g, c in faces for p in polys(g)]
    report['specks2'] = absorb_small(faces, min_area, thin)
    return faces_to_regions(faces)

# ============================================================== regions -> item
def order_rings(rings):
    """Nearest-neighbour order (rings may start anywhere)."""
    if len(rings) < 3: return rings
    left = list(range(len(rings))); out = []; cur = np.array([0.0, 0.0])
    while left:
        best = None
        for i in left:
            d = np.hypot(*(rings[i][:-1] - cur).T); k = int(np.argmin(d))
            if best is None or d[k] < best[0]: best = (d[k], i, k)
        _, i, k = best; left.remove(i)
        r = rings[i][:-1]; r = np.vstack([r[k:], r[:k], r[k:k + 1]])
        out.append(r); cur = r[-1]
    return out

def build(code, name, regions):
    order = sorted((c for c in regions if c is not None), key=lambda c: -regions[c].area)
    lines, fills = [], []
    for c in order:
        rings = []
        for p in polys(regions[c]):
            rings.append(np.array(p.exterior.coords)); rings += [np.array(r.coords) for r in p.interiors]
        rings = order_rings(rings)
        a = len(lines)
        lines += [[(round(float(x) * OUTK, 2), round(float(y) * OUTK, 2)) for x, y in r] for r in rings]
        fills.append([c, a, len(lines)])
    it = Item('flags', name, lines, author='flag-icons contributors', source='flag-icons', license='MIT',
              title=f'flag-icons “{code}”', fills=fills)
    it.slug = f'flag-{code}'
    return it

def flag_item(pkg, code, name, report=None, **kw):
    paints = FlagSVG(os.path.join(pkg, 'flags', '4x3', f'{code}.svg')).paints
    regions = paint(paints)
    regions = clean(regions, report=report, **kw)
    return build(code, name, regions)

# ============================================================== checking
def export_lines(lines):
    """The lines as the library exporter stores them: longest side 1000, RDP 0.8, whole units."""
    from common import _rdp
    S = [P for P in lines if len(P) > 1]
    xs = [p[0] for P in S for p in P]; ys = [p[1] for P in S for p in P]
    x0, y0 = min(xs), min(ys); k = 1000 / max(max(xs) - x0, max(ys) - y0, 1e-9)
    out = []
    for P in S:
        Q = _rdp([((x - x0) * k, (y - y0) * k) for x, y in P], 0.8)
        Q = [(round(x), round(y)) for x, y in Q]
        out.append([p for i, p in enumerate(Q) if i == 0 or p != Q[i - 1]])
    return out

def evenodd(rings):
    g = Polygon()
    for r in rings:
        if len(r) < 4: continue
        p = Polygon(r)
        if not p.is_valid: p = shapely.make_valid(p)
        g = shapely.symmetric_difference(g, p)
    return g

def patch_of(g, **kw):
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    from shapely.geometry.polygon import orient
    V, C = [], []
    for p in polys(g):
        p = orient(p, 1.0)
        for r in [p.exterior] + list(p.interiors):
            xy = list(r.coords); V += xy; C += [Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY]
    return PathPatch(Path(V, C), **kw) if V else None

def preview(items, path, cols=8, cell=2.2, exported=True, lw=0.35):
    """Colour sheet: every fill range filled with its colour (even-odd), all lines stroked in black."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    n = len(items); rows = max(1, (n + cols - 1) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * cell, rows * cell * 0.86))
    axes = np.array(axes).reshape(-1)
    for ax in axes: ax.axis('off')
    for i, it in enumerate(items):
        ax = axes[i]
        L = export_lines(it.lines) if exported else it.lines
        for col, a, b in it.fills:
            pp = patch_of(evenodd(L[a:b]), facecolor=col, edgecolor='none')
            if pp is not None: ax.add_patch(pp)
        for P in L:
            ax.plot([p[0] for p in P], [p[1] for p in P], '-', color='k', lw=lw)
        ax.set_aspect('equal'); ax.autoscale_view(); ax.invert_yaxis()
        pts, nl = export_size(it.lines)
        ax.set_title(f'{i}: {it.name[:24]}\n{nl} lines {pts} pts', fontsize=7)
    plt.tight_layout(); plt.savefig(path, dpi=72 if cell < 3 else 100); plt.close(fig)
    print('preview', path)

def check(it):
    """Problems that would break the fills after export: lines that collapse, ranges that do not cover all lines."""
    probs = []
    E = export_lines(it.lines)
    for i, P in enumerate(E):
        if len(set(P)) < 3: probs.append(f'line {i} collapses to {len(set(P))} points')
    cov = []
    for col, a, b in it.fills:
        if not re.fullmatch(r'#[0-9a-f]{6}', col): probs.append(f'bad colour {col}')
        cov += list(range(a, b))
    if cov != list(range(len(it.lines))): probs.append('fill ranges do not cover the lines in order')
    for P in it.lines:
        if P[0] != P[-1]: probs.append('open line'); break
    return probs

# ============================================================== main
if __name__ == '__main__':
    import time
    PKG, OUT = sys.argv[1], sys.argv[2]
    SHEET = sys.argv[3] if len(sys.argv) > 3 else None
    items = []
    for code, name in FLAGS:
        t = time.time(); rep = {}
        it = flag_item(PKG, code, name, report=rep)
        pts, nl = export_size(it.lines)
        probs = check(it)
        print(f'{code:4s} {name:24s} {nl:4d} lines {pts:5d} pts  {len(it.fills)} colours  {time.time() - t:5.2f}s  {rep}' + (f'  PROBLEMS {probs}' if probs else ''))
        items.append(it)
    save(items, OUT)
    P = sorted(export_size(i.lines)[0] for i in items)
    print(f'{len(items)} flags; points median {P[len(P) // 2]}, max {P[-1]}')
    if SHEET:
        for i in range(0, len(items), 40):
            sheet(items[i:i + 40], SHEET.replace('.png', f'_{i // 40}.png'), cols=8)
            preview(items[i:i + 40], SHEET.replace('.png', f'_colour_{i // 40}.png'), cols=8)
