#!/usr/bin/env python3
"""Builds the Persian single-line font for the plotter (src/part57_persian_font.js).

Source: Vazirmatn (Round Dots variant, Thin weight) by Saber Rastikerdar and the Vazirmatn Project
Authors, SIL Open Font License 1.1 (https://github.com/rastikerdar/vazirmatn). Every glyph the
Persian text needs (each letter in its isolated, initial, middle and final forms, the lam-alef
ligatures, marks, Persian and Latin digits, punctuation and Latin letters) is drawn, thinned to its
centre line and traced into pen lines. Round dots become small circles, and the strokes that join
letters end exactly at the joining point, so joined letters meet.

Get the font (npm package "vazirmatn", OFL):
    npm pack vazirmatn@33.0.3 && tar -xzf vazirmatn-33.0.3.tgz
Run:
    python3 tools/fonts/persian/build_persian_font.py package/Round-Dots/fonts/ttf/Vazirmatn-RD-Thin.ttf package/OFL.txt
Needs: fontTools, numpy, scikit-image (pip install fonttools numpy scikit-image).
"""
import argparse, json, math, pathlib, sys, unicodedata
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from skimage.morphology import skeletonize
from skimage.draw import polygon as fill_polygon
from skimage.measure import label

RES = 4.0          # font units per pixel
PAD = 8            # pixels round each glyph
CAP = 160          # FONT_CAP in the app: units per letter height
ROOT = pathlib.Path(__file__).resolve().parents[3]

# Persian text: Arabic-script letters (and the Persian ones), marks, digits, punctuation.
LETTERS = [c for c in range(0x0621, 0x064B) if unicodedata.category(chr(c)) == 'Lo'] + [0x067E, 0x0686, 0x0698, 0x06A9, 0x06AF, 0x06CC, 0x06C0, 0x06D2, 0x0671]
MARKS = [0x064B, 0x064C, 0x064D, 0x064E, 0x064F, 0x0650, 0x0651, 0x0652, 0x0654, 0x0655, 0x0670]
OTHER = [0x0640, 0x060C, 0x061B, 0x061F, 0x066A, 0x066B, 0x066C, 0x00AB, 0x00BB] + list(range(0x06F0, 0x06FA)) + list(range(0x0660, 0x066A)) + list(range(0x20, 0x7F))


class FlatPen(BasePen):
    """Outline → polygons (curves flattened)."""
    def __init__(self, gs):
        super().__init__(gs); self.contours = []; self.cur = []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for i in range(1, 9):
            t = i / 8; a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for i in range(1, 7):
            t = i / 6; a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    def _closePath(self):
        if len(self.cur) > 2: self.contours.append(self.cur)
        self.cur = []
    _endPath = _closePath


def rasterize(contours):
    xs = [p[0] for c in contours for p in c]; ys = [p[1] for c in contours for p in c]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W = int(math.ceil((x1 - x0) / RES)) + 2 * PAD + 1; H = int(math.ceil((y1 - y0) / RES)) + 2 * PAD + 1
    wind = np.zeros((H, W), np.int16)
    for c in contours:
        area = sum(c[i][0] * c[(i + 1) % len(c)][1] - c[(i + 1) % len(c)][0] * c[i][1] for i in range(len(c)))
        rr, cc = fill_polygon([(y1 - p[1]) / RES + PAD for p in c], [(p[0] - x0) / RES + PAD for p in c], (H, W))
        wind[rr, cc] += 1 if area > 0 else -1
    return wind != 0, (x0, y1)


def to_font(pt, org):
    r, c = pt
    return ((c - PAD) * RES + org[0], org[1] - (r - PAD) * RES)


def skeleton_strokes(skel, w):
    """Skeleton pixels → pen strokes (lists of (row, col)). Junction and end pixels that touch are one
    node; short side branches are dropped; the branches are then walked through the nodes as straight
    as possible, so a letter is drawn with as few pen lifts as it can be."""
    pts = set(map(tuple, np.argwhere(skel)))
    NB = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]
    nb = lambda p: [(p[0] + dr, p[1] + dc) for dr, dc in NB if (p[0] + dr, p[1] + dc) in pts]
    deg = {p: len(nb(p)) for p in pts}
    nodes = {p for p in pts if deg[p] != 2}
    cid, cpos = {}, []
    for p in sorted(nodes):
        if p in cid: continue
        k = len(cpos); cid[p] = k; stack, mem = [p], []
        while stack:
            q = stack.pop(); mem.append(q)
            for r in nb(q):
                if r in nodes and r not in cid: cid[r] = k; stack.append(r)
        cpos.append((sum(m[0] for m in mem) / len(mem), sum(m[1] for m in mem) / len(mem)))
    plen = lambda path: sum(math.dist(path[i - 1], path[i]) for i in range(1, len(path)))
    edges, used = [], set()
    for p in sorted(nodes):
        a = cid[p]
        for n in nb(p):
            if n in nodes or (p, n) in used: continue
            path, prev, cur = [cpos[a], n], p, n
            used.add((p, n)); used.add((n, p))
            while cur not in nodes:
                nx = [q for q in nb(cur) if q != prev and (cur, q) not in used]
                if not nx: break
                q = next((q for q in nx if q in nodes), nx[0])
                used.add((cur, q)); used.add((q, cur)); prev, cur = cur, q
                path.append(cur)
            if cur not in nodes: continue
            b = cid[cur]; path[-1] = cpos[b]
            if a == b and plen(path) < 2 * w: continue          # a tiny loop round a junction
            edges.append([a, b, path])
    loops = []
    for s in sorted(pts):                                        # rings with no ends or junctions (o, 0…)
        if s in nodes or any((s, n) in used for n in nb(s)): continue
        path, prev, cur = [s], None, s
        while True:
            nx = [q for q in nb(cur) if q != prev and (cur, q) not in used]
            if not nx: break
            used.add((cur, nx[0])); used.add((nx[0], cur)); prev, cur = cur, nx[0]; path.append(cur)
            if cur == s: break
        if len(path) > 3: loops.append(path)
    # drop short side branches (a free end on one side, a junction of 3+ on the other)
    for _ in range(4):
        cd = {}
        for a, b, _p in edges: cd[a] = cd.get(a, 0) + 1; cd[b] = cd.get(b, 0) + 1
        keep = [e for e in edges if not (e[0] != e[1] and min(cd[e[0]], cd[e[1]]) == 1 and max(cd[e[0]], cd[e[1]]) >= 3 and plen(e[2]) < 1.6 * w)]
        if len(keep) == len(edges): break
        edges = keep
    adj = {}
    for i, (a, b, _p) in enumerate(edges): adj.setdefault(a, []).append(i); adj.setdefault(b, []).append(i)
    left = set(range(len(edges)))
    free = lambda n: [i for i in adj.get(n, []) if i in left]
    def oriented(i, n):
        a, b, path = edges[i]
        return path if a == n else path[::-1]
    def heading(path):                                           # direction leaving path[0]
        acc, q = 0.0, path[-1]
        for k in range(1, len(path)):
            acc += math.dist(path[k - 1], path[k])
            if acc >= 1.5 * w: q = path[k]; break
        return math.atan2(q[0] - path[0][0], q[1] - path[0][1])
    turn = lambda h1, h2: abs((h2 - h1 + math.pi) % (2 * math.pi) - math.pi)
    strokes = []
    while left:
        cands = [n for n in adj if free(n)]
        odd = [n for n in cands if len(free(n)) % 2 == 1]
        node = min(odd or cands, key=lambda n: (cpos[n][1], cpos[n][0]))
        path, inc = None, None
        while True:
            fr = free(node)
            if not fr: break
            if inc is None: i = max(fr, key=lambda i: plen(edges[i][2]))
            else: i = min(fr, key=lambda i: turn(inc, heading(oriented(i, node))))
            left.discard(i)
            seg = oriented(i, node)
            path = list(seg) if path is None else path + list(seg[1:])
            back = heading(seg[::-1])
            inc = back + math.pi                                 # arriving direction
            a, b, _p = edges[i]
            node = b if node == a else a
        strokes.append(path)
    return strokes + loops


def smooth(s, k=2):
    if len(s) < 5: return s
    out = [s[0]]
    for i in range(1, len(s) - 1):
        lo, hi = max(0, i - k), min(len(s), i + k + 1)
        out.append((sum(p[0] for p in s[lo:hi]) / (hi - lo), sum(p[1] for p in s[lo:hi]) / (hi - lo)))
    out.append(s[-1])
    return out


def rdp(pts, eps):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-9
    i, dmax = 0, -1
    for k in range(1, len(pts) - 1):
        d = abs((pts[k][0] - a[0]) * dy - (pts[k][1] - a[1]) * dx) / L if math.hypot(dx, dy) > 1e-9 else math.dist(pts[k], a)
        if d > dmax: i, dmax = k, d
    if dmax <= eps: return [a, b]
    return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)


def glyph_lines(gs, name, stroke):
    pen = FlatPen(gs); gs[name].draw(pen)
    if not pen.contours: return []
    mask, org = rasterize(pen.contours)
    lab = label(mask, connectivity=2)
    w = stroke / RES
    lines = []
    for k in range(1, lab.max() + 1):
        comp = lab == k
        rows, cols = np.nonzero(comp)
        h, wd = rows.max() - rows.min() + 1, cols.max() - cols.min() + 1
        area = comp.sum()
        def dot():                                  # a small circle the size of the dot, less the pen line
            cy, cx = rows.mean(), cols.mean(); d = 2 * math.sqrt(area / math.pi)
            r = max(0.18 * d, d / 2 - w / 2)
            lines.append([to_font((cy + r * math.sin(2 * math.pi * i / 10), cx + r * math.cos(2 * math.pi * i / 10)), org) for i in range(11)])
        if max(h, wd) <= 3.6 * w and area >= 0.55 * h * wd and abs(h - wd) <= 0.35 * max(h, wd):   # a round dot
            dot(); continue
        sk = skeletonize(comp)
        paths = skeleton_strokes(sk, w) if sk.sum() >= 2 else []
        if not paths:                               # too small to have a centre line (the Arabic zero)
            dot(); continue
        for p in paths:
            f = [to_font(q, org) for q in p]
            lines.append(rdp(smooth(f), 2.5))
    return lines


def snap_joins(lines, adv, join_l, join_r, yc, stroke):
    """Ends of the joining strokes exactly at the joining point (x = 0 on the left, x = advance on the
    right, at the joining height), so neighbouring letters meet."""
    for side, x_edge in (('l', 0.0), ('r', float(adv))):
        if not (join_l if side == 'l' else join_r): continue
        best, bd = None, None
        for si, s in enumerate(lines):
            for ei in (0, len(s) - 1):
                x, y = s[ei]
                if abs(y - yc) > 1.6 * stroke: continue
                d = abs(x - x_edge)
                if d < 3.5 * stroke and (bd is None or d < bd): best, bd = (si, ei), d
        if best:
            si, ei = best
            s = lines[si]
            s[ei] = (x_edge, yc)
        else:                                       # no free end there: a short joining stroke
            near, nd = None, None
            for s in lines:
                for p in s:
                    if abs(p[1] - yc) > 1.6 * stroke: continue
                    d = abs(p[0] - x_edge)
                    if nd is None or d < nd: near, nd = p, d
            if near and nd < 4 * stroke: lines.append([near, (x_edge, yc)])
    return lines


def encode(lines, scale):
    """FONT_DATA strokes: base-64 varints, zig-zag deltas, y down, cap height = CAP."""
    B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    def vint(v):
        out = ''
        while True:
            d = v & 31; v >>= 5
            if v: out += B64[d | 32]
            else: out += B64[d]; return out
    zz = lambda v: 2 * v if v >= 0 else -2 * v - 1
    s, x, y = vint(len(lines)), 0, 0
    for ln in lines:
        pts = []
        for (fx, fy) in ln:
            q = (round(fx * scale), round(-fy * scale))
            if not pts or q != pts[-1]: pts.append(q)
        if len(pts) == 1: pts.append(pts[0])
        s += vint(len(pts))
        for (qx, qy) in pts:
            s += vint(zz(qx - x)) + vint(zz(qy - y)); x, y = qx, qy
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('font'); ap.add_argument('licence')
    ap.add_argument('--out', default=str(ROOT / 'src' / 'part57_persian_font.js')); ap.add_argument('--preview', default='')
    a = ap.parse_args()
    f = TTFont(a.font); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    alef = gs[cmap[0x0627]]
    from fontTools.pens.boundsPen import BoundsPen
    def bounds(n): bp = BoundsPen(gs); gs[n].draw(bp); return bp.bounds
    ah = bounds(cmap[0x0627])[3]                      # alef height = the letter height
    tb = bounds(cmap[0x0640]); yc = (tb[1] + tb[3]) / 2; stroke = tb[3] - tb[1]
    ab = bounds(cmap[0x0627]); stroke = min(stroke, ab[2] - ab[0])
    scale = CAP / ah
    # every code point → glyph, and for the joining forms which sides join
    want = {}
    for c in LETTERS + MARKS + OTHER:
        if c in cmap: want[c] = (cmap[c], False, False)
    for c in range(0xFB50, 0xFEFD):
        d = unicodedata.decomposition(chr(c)) if 0xFB50 <= c <= 0xFDFF or 0xFE70 <= c <= 0xFEFF else ''
        if not d.startswith('<') or c not in cmap: continue
        tag, base = d.split(' ', 1)
        bases = [int(b, 16) for b in base.split()]
        if not all(b in LETTERS for b in bases): continue
        jl = tag in ('<initial>', '<medial>'); jr = tag in ('<final>', '<medial>')
        want[c] = (cmap[c], jl, jr)
    data, n = '', 0
    preview = {}
    for c, (gname, jl, jr) in sorted(want.items()):
        ch = chr(c)
        adv = gs[gname].width
        if ch == ' ':
            data += ch + vint_s(round(adv * scale)) + 'A'; n += 1; continue
        lines = glyph_lines(gs, gname, stroke)
        if unicodedata.combining(ch):
            pass
        elif jl or jr or c == 0x0640:
            lines = snap_joins(lines, adv, jl or c == 0x0640, jr or c == 0x0640, yc, stroke)
        data += ch + vint_s(round(adv * scale)) + encode(lines, scale); n += 1
        preview[c] = (lines, adv)
    lic = pathlib.Path(a.licence).read_text(encoding='utf-8')
    js = ('/* ===================== PERSIAN SINGLE-LINE FONT (generated by tools/fonts/persian/build_persian_font.py — do not edit) =====================\n'
          '   Centre lines of Vazirmatn (Round Dots, Thin) by Saber Rastikerdar and the Vazirmatn Project Authors,\n'
          '   SIL Open Font License 1.1 (licence text below, FA_FONT_LICENCE). Keys are characters: letters in their\n'
          '   presentation forms (isolated, initial, middle, final), the lam-alef ligatures, marks, digits, punctuation\n'
          '   and Latin. Letter height = the height of alef; y down; joining strokes end at x = 0 / advance at y = join. */\n'
          f'FONT_DATA.PersianVazir = {json.dumps({"name": "Vazir (single-line Persian)", "group": "persian", "x": round(bounds(cmap[0x0628])[3] * scale), "join": round(-yc * scale), "data": data}, ensure_ascii=False)};\n'
          f'const FA_FONT_LICENCE = {json.dumps(lic, ensure_ascii=False)};\n')
    pathlib.Path(a.out).write_text(js, encoding='utf-8')
    print(f'{n} glyphs, {len(data)} characters of data → {a.out} (alef {ah:.0f} units, stroke {stroke:.0f}, join at {yc:.0f})')
    if a.preview:
        json.dump({str(k): [[list(p) for p in ln] for ln in v[0]] for k, v in preview.items()}, open(a.preview, 'w'))


def vint_s(v):
    B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    out = ''
    while True:
        d = v & 31; v >>= 5
        if v: out += B64[d | 32]
        else: out += B64[d]; return out


if __name__ == '__main__':
    main()
