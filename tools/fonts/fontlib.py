"""Reads single-line SVG fonts (EMS / Hershey for Inkscape) and hersheytext JSON fonts into glyph strokes."""
import re, html, json, math

def _tokens(d):
    return re.findall(r'[MLCZmlcz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d)

def path_strokes(d, curve_seg=10):
    """M/L/C/Z absolute paths -> list of point lists (x, y in font units, y up)."""
    toks = _tokens(d); i = 0; cmd = None; cur = None; start = None; strokes = []; S = None
    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v
    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t):
            cmd = t; i += 1
            if cmd in 'Zz':
                if S and start and (S[-1] != start): S.append(start)
                cur = start
                continue
            continue
        if cmd == 'M':
            x, y = num(), num()
            if S and len(S) > 1: strokes.append(S)
            S = [(x, y)]; cur = start = (x, y); cmd = 'L'
        elif cmd == 'L':
            x, y = num(), num()
            if S is None: S = [cur] if cur else []
            S.append((x, y)); cur = (x, y)
        elif cmd == 'C':
            x1, y1, x2, y2, x, y = (num() for _ in range(6))
            p0 = cur
            for k in range(1, curve_seg + 1):
                tt = k / curve_seg; u = 1 - tt
                S.append((u**3 * p0[0] + 3 * u * u * tt * x1 + 3 * u * tt * tt * x2 + tt**3 * x,
                          u**3 * p0[1] + 3 * u * u * tt * y1 + 3 * u * tt * tt * y2 + tt**3 * y))
            cur = (x, y)
        else:
            raise ValueError('unsupported command ' + str(cmd))
    if S and len(S) > 1: strokes.append(S)
    return strokes

def read_svg_font(path):
    s = open(path, encoding='utf-8').read()
    meta = re.search(r'<metadata>(.*?)</metadata>', s, re.S)
    fadv = float(re.search(r'<font [^>]*horiz-adv-x="([\d.]+)"', s).group(1))
    glyphs = {}
    for g in re.findall(r'<glyph\b([^>]*)/?>', s, re.S):
        u = re.search(r'\bunicode="([^"]*)"', g)
        if not u: continue
        ch = html.unescape(u.group(1))
        if len(ch) != 1: continue
        adv = re.search(r'horiz-adv-x="([\d.]+)"', g)
        d = re.search(r'\bd="([^"]*)"', g)
        a, st = (float(adv.group(1)) if adv else fadv), (path_strokes(d.group(1)) if d else [])
        if ch in glyphs:
            # a second entry for the same character: the other half of the letter (ç in Script medium)
            # is merged; an alternative drawing of it (£, ¸) is ignored
            a0, s0 = glyphs[ch]
            def box(L):
                xs = [q[0] for t in L for q in t]; ys = [q[1] for t in L for q in t]
                return (min(xs), min(ys), max(xs), max(ys)) if xs else None
            b0, b1 = box(s0), box(st)
            if b0 and b1:
                ix = max(0, min(b0[2], b1[2]) - max(b0[0], b1[0])); iy = max(0, min(b0[3], b1[3]) - max(b0[1], b1[1]))
                ar = lambda b: max(1e-9, (b[2] - b[0]) * (b[3] - b[1]))
                if ix * iy / min(ar(b0), ar(b1)) < 0.3: glyphs[ch] = (max(a0, a), s0 + st)
        else:
            glyphs[ch] = (a, st)
    return {'meta': meta.group(1).strip() if meta else '', 'adv': fadv, 'glyphs': glyphs, 'yup': True}

def read_hershey_json(path, key):
    f = json.load(open(path))[key]
    glyphs = {}
    for i, c in enumerate(f['chars']):
        ch = chr(33 + i)
        segs, cur = [], []
        for tok in re.findall(r'[ML]|-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?', c['d']):
            if tok == 'M':
                if len(cur) > 1: segs.append(cur)
                cur = []
            elif tok == 'L': pass
            else:
                x, y = map(float, tok.split(',')); cur.append((x, -y))     # y down in the JSON -> y up
        if len(cur) > 1: segs.append(cur)
        glyphs[ch] = (c['o'] * 2, segs)
    glyphs[' '] = (16, [])
    return {'meta': f.get('name', key), 'adv': 16, 'glyphs': glyphs, 'yup': True}
