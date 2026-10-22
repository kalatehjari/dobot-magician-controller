"""Songs: short engraved scores of public-domain melodies (category 'songs'), and musical instruments
(category 'music', from gen_songs_instr.py). Melodies are in gen_songs_data.py.
Usage: python3 -I gen_songs.py <out.json> [sheet.png]"""
import math, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from gen_songs_data import SONGS

S = 10.0                        # staff space
DUR = {'w': 4.0, 'h': 2.0, 'q': 1.0, 'e': 0.5, 's': 0.25}
LET = 'CDEFGAB'
SHARPS = [('F', 38), ('C', 35), ('G', 39), ('D', 36), ('A', 33), ('E', 37), ('B', 34)]
FLATS = [('B', 34), ('E', 37), ('A', 33), ('D', 36), ('G', 32), ('C', 35), ('F', 31)]
KEYS = {'C': 0, 'G': 1, 'D': 2, 'A': 3, 'E': 4, 'B': 5, 'F': -1, 'Bb': -2, 'Eb': -3, 'Ab': -4, 'Db': -5}

def ypos(d): return 40 - (d - 30) * 5          # diatonic step -> y (E4 on the bottom line)

# ---------------------------------------------------------------- parsing
TOK = re.compile(r'^(?:(r)|([A-G])([#bn]?)(\d))([whqes])(\.?)(~?)(\^?)$')
def parse(notes):
    bars = []
    for b in notes.split('|'):
        evs = []
        for t in b.split():
            m = TOK.match(t)
            if not m: raise ValueError('bad token ' + t)
            rest, L, acc, octv, dch, dot, tie, ferm = m.groups()
            dur = DUR[dch] * (1.5 if dot else 1)
            ev = {'rest': bool(rest), 'dur': dur, 'base': dch, 'dot': bool(dot), 'tie': bool(tie), 'ferm': bool(ferm)}
            if not rest:
                ev['d'] = int(octv) * 7 + LET.index(L); ev['letter'] = L; ev['acc'] = acc
            evs.append(ev)
        bars.append(evs)
    return bars

def check(title, time, bars):
    num, den = map(int, time.split('/')); full = num * 4 / den
    lens = [sum(e['dur'] for e in b) for b in bars]
    probs = []
    pick = full - lens[0] if lens[0] < full - 1e-9 else 0
    for i, L in enumerate(lens):
        if i == 0 and L <= full + 1e-9: continue
        if i == len(lens) - 1 and pick and abs(L - pick) < 1e-9: continue
        if abs(L - full) > 1e-9: probs.append(f'bar {i + 1} has {L} beats')
    if probs: raise ValueError(f'{title}: ' + '; '.join(probs))
    return full, pick > 0

# ---------------------------------------------------------------- glyphs (staff space S = 10, y down)
def head(x, y, kind):
    """Notehead: 'filled' (a spiral that ends on the outline, so a pen fills it in one line), 'half' or 'whole'."""
    if kind == 'whole':
        return [ellipse(x, y, 0.82 * S, 0.5 * S, 0, n=28), ellipse(x, y, 0.38 * S, 0.27 * S, math.radians(-50), n=16)]
    a = math.radians(-20); ca, sa = math.cos(a), math.sin(a); rx, ry = 0.64 * S, 0.45 * S
    if kind == 'half':
        return [ellipse(x, y, rx, ry, a, n=28)]
    P = []; turns = 2.3; n = int(turns * 14)
    for i in range(n + 1):
        t = i / n; r = 0.12 + 0.88 * t; th = TAU * turns * t
        u, v = rx * r * math.cos(th), ry * r * math.sin(th)
        P.append((x + u * ca - v * sa, y + u * sa + v * ca))
    for i in range(1, 25):
        th = TAU * turns + TAU * i / 24
        u, v = rx * math.cos(th), ry * math.sin(th)
        P.append((x + u * ca - v * sa, y + u * sa + v * ca))
    return [P]

def blob(x, y, r):
    return [circle(x, y, r, n=14), circle(x, y, r * 0.45, n=8)]

def thick_bar(x0, y0, x1, y1, t):
    """A filled straight bar of thickness t from (x0, y0) to (x1, y1) (t grows downwards): outline + middle line."""
    out = [[(x0, y0), (x1, y1), (x1, y1 + t), (x0, y0 + t), (x0, y0)]]
    if abs(t) > 2.6: out.append([(x0, y0 + t / 2), (x1, y1 + t / 2)])
    return out

def sharp(x, y):
    out = [[(x - 2.2, y - 12), (x - 2.2, y + 13)], [(x + 2.2, y - 13), (x + 2.2, y + 12)]]
    for dy in (-4, 4):
        out += thick_bar(x - 5.2, y + dy - 0.2, x + 5.2, y + dy - 3.2, 2.6)
    return out

def flat(x, y):
    out = [[(x - 3, y - 17), (x - 3, y + 5)]]
    out.append(bezier((x - 3, y + 5), (x + 6, y), (x + 6, y - 7), (x - 3, y - 2), n=14))
    out.append(bezier((x - 3, y + 2.6), (x + 3.2, y - 1), (x + 3, y - 4.5), (x - 3, y - 0.8), n=10))
    return out

def natural(x, y):
    out = [[(x - 2.6, y - 13), (x - 2.6, y + 5)], [(x + 2.6, y - 5), (x + 2.6, y + 13)]]
    out += thick_bar(x - 2.6, y - 3.2 + 1.2, x + 2.6, y - 3.2 - 1.2, 2.4)
    out += thick_bar(x - 2.6, y + 3.8 + 1.2, x + 2.6, y + 3.8 - 1.2, 2.4)
    return out

ACC = {'#': sharp, 'b': flat, 'n': natural}

def treble_clef(x):
    L = glyph_lines('music', ';', 0, 0, 100)
    xs = [p[0] for P in L for p in P]; ys = [p[1] for P in L for p in P]
    k = 7.0 * S / (max(ys) - min(ys))
    return [[(x + (px - min(xs)) * k, -1.6 * S + (py - min(ys)) * k) for px, py in P] for P in L], (max(xs) - min(xs)) * k

def quarter_rest(x):
    return glyph_lines('music', '.', x, 2 * S, 3.0 * S)

def eighth_rest(x, n=1):
    out = []
    for k in range(n):
        cy = 1.3 * S + k * S; cx = x - 2.6 - k * 1.5
        out += blob(cx, cy, 1.9)
        out.append(quad((cx + 1.2, cy + 1.6), (cx + 3.5, cy + 1.6), (x + 3.6 - k * 1.5, cy - 1.0), n=6))
    out.append([(x + 3.6, 1.3 * S - 1.0), (x - 1.0 - (n - 1) * 3, 3.2 * S + (n - 1) * S)])
    return out

def rest(x, base, dot):
    if base == 'q': out = quarter_rest(x)
    elif base == 'e': out = eighth_rest(x, 1)
    elif base == 's': out = eighth_rest(x, 2)
    elif base == 'h': out = thick_bar(x - 6, 1.5 * S, x + 6, 1.5 * S, 0.5 * S) + [[(x - 6, 2 * S), (x + 6, 2 * S)]]
    else: out = thick_bar(x - 6, 1.0 * S, x + 6, 1.0 * S, 0.5 * S) + [[(x - 6, 1.0 * S), (x + 6, 1.0 * S)]]
    if dot: out += blob(x + 9, 1.5 * S, 1.5)
    return out

def fermata(x, y):
    return [arc(x, y, 7, math.pi, 2 * math.pi, n=14)] + blob(x, y - 1.8, 1.4)

def tie(x0, x1, y, below):
    s = 1 if below else -1; y0 = y + s * 0.75 * S; m = (x0 + x1) / 2
    a = quad((x0 + 2, y0), (m, y0 + s * 0.9 * S), (x1 - 2, y0), n=16)
    b = quad((x1 - 2, y0), (m, y0 + s * 0.55 * S), (x0 + 2, y0), n=16)
    return [a + b[1:]]

def flag(x, y, up, n=1):
    out = []
    for k in range(n):
        if up:
            y0 = y + k * 0.8 * S
            out.append(bezier((x, y0), (x + 0.4 * S, y0 + 1.1 * S), (x + 1.4 * S, y0 + 1.5 * S), (x + 0.8 * S, y0 + 2.9 * S), n=12))
            out.append(bezier((x, y0 + 0.35 * S), (x + 0.4 * S, y0 + 1.25 * S), (x + 1.1 * S, y0 + 1.7 * S), (x + 0.8 * S, y0 + 2.9 * S), n=10))
        else:
            y0 = y - k * 0.8 * S
            out.append(bezier((x, y0), (x + 0.4 * S, y0 - 1.1 * S), (x + 1.4 * S, y0 - 1.5 * S), (x + 0.8 * S, y0 - 2.9 * S), n=12))
            out.append(bezier((x, y0 - 0.35 * S), (x + 0.4 * S, y0 - 1.25 * S), (x + 1.1 * S, y0 - 1.7 * S), (x + 0.8 * S, y0 - 2.9 * S), n=10))
    return out

# ---------------------------------------------------------------- layout
def note_width(ev):
    w = S * (1.55 + 1.55 * ev['dur'] ** 0.6)
    if ev.get('acc_draw'): w += 1.25 * S
    if ev['dot']: w += 0.5 * S
    return w

def key_list(key):
    n = KEYS[key]
    return [(L, '#', d) for L, d in SHARPS[:n]] if n > 0 else [(L, 'b', d) for L, d in FLATS[:-n]]

def mark_accidentals(bars, key):
    base = {L: a for L, a, _ in key_list(key)}
    for b in bars:
        state = {}
        for ev in b:
            if ev['rest']: continue
            want = ev['acc'] or ''
            if want == 'n': want = ''
            k = (ev['letter'], ev['d'])
            cur = state.get(k, base.get(ev['letter'], ''))
            ev['acc_draw'] = None
            if want != cur: ev['acc_draw'] = want or 'n'
            state[k] = want

def beam_groups(bar, time):
    """Lists of indices of beamed notes: eighths and shorter, within one beat (a dotted quarter in x/8)."""
    num, den = map(int, time.split('/'))
    beat = 1.5 if den == 8 and num % 3 == 0 else 1.0
    if time in ('2/4', '4/4'): beat = 2.0            # eighths beamed by half bar
    groups, cur, t, cur_beat = [], [], 0.0, None
    for i, ev in enumerate(bar):
        b = int(t / beat + 1e-9)
        short = ev['dur'] < 1.0 - 1e-9 and ev['base'] in 'es' and not ev['rest']
        if not short or b != cur_beat:
            if len(cur) > 1: groups.append(cur)
            cur = []
        if short:
            cur.append(i); cur_beat = b
        t += ev['dur']
        if not short: cur_beat = None
    if len(cur) > 1: groups.append(cur)
    return groups

def system_prefix(key, with_time, time):
    """Width and lines of clef, key signature (and time signature) at x = 0."""
    out, w = treble_clef(0.5 * S)
    x = 0.5 * S + w + 0.8 * S
    for L, a, d in key_list(key):
        out += ACC[a](x, ypos(d)); x += 1.0 * S
    if key_list(key): x += 0.5 * S
    if with_time:
        num, den = time.split('/')
        wn = max(text_width(num, 1.9 * S, 'HersheySerifBold'), text_width(den, 1.9 * S, 'HersheySerifBold'))
        out += text(num, x + wn / 2, 1.95 * S, 1.9 * S, 'HersheySerifBold')
        out += text(den, x + wn / 2, 3.95 * S, 1.9 * S, 'HersheySerifBold')
        x += wn + 1.0 * S
    return out, x + 0.8 * S

def draw_system(bars, key, time, first, last, width, oy):
    """One staff with its bars, stretched to `width`. Returns lines (y offset oy)."""
    out, x0 = system_prefix(key, first, time)
    nat = [sum(note_width(ev) for ev in b) + 1.2 * S for b in bars]
    k = (width - x0) / sum(nat)
    x = x0; heads = []
    for bi, b in enumerate(bars):
        bw = nat[bi] * k; xs = x + 0.9 * S * k
        pos = []
        for ev in b:
            w = note_width(ev) * k
            hx = xs + (1.25 * S if ev.get('acc_draw') else 0) + 0.65 * S
            pos.append(hx); xs += w
        groups = beam_groups(b, time)
        in_group = {i: g for g in groups for i in g}
        for i, ev in enumerate(b):
            hx = pos[i]
            if ev['rest']:
                out += rest(hx, ev['base'], ev['dot']); continue
            y = ypos(ev['d'])
            kind = 'whole' if ev['base'] == 'w' else 'half' if ev['base'] == 'h' else 'filled'
            out += head(hx, y, kind)
            if ev.get('acc_draw'): out += ACC[ev['acc_draw']](hx - 1.75 * S, y)
            for ly in range(-10, int(y) - 1, -10):           # ledger lines above
                out.append([(hx - 1.05 * S, ly), (hx + 1.05 * S, ly)])
            for ly in range(50, int(y) + 1, 10):             # and below
                out.append([(hx - 1.05 * S, ly), (hx + 1.05 * S, ly)])
            if ev['dot']:
                dy = y if int(round(y)) % 10 == 5 else y - 5
                out += blob(hx + 1.25 * S, dy, 1.45)
            ev['_x'], ev['_y'] = hx, y
            if ev['ferm']: out += fermata(hx, min(-1.0 * S, y - 1.5 * S))
            if kind != 'whole' and i not in in_group:
                up = ev['d'] < 34
                if up: sx, sy0, sy1 = hx + 0.6 * S, y - 0.15 * S, y - 3.5 * S
                else: sx, sy0, sy1 = hx - 0.6 * S, y + 0.15 * S, y + 3.5 * S
                out.append([(sx, sy0), (sx, sy1)])
                if ev['base'] in 'es': out += flag(sx, sy1, up, 1 if ev['base'] == 'e' else 2)
            ev['_up'] = ev['d'] < 34
        for g in groups:
            out += draw_beam([b[i] for i in g], pos=[pos[i] for i in g])
        x += bw
        bx = x
        if bi == len(bars) - 1 and last:
            out.append([(bx - 0.75 * S, 0), (bx - 0.75 * S, 4 * S)])
            out += [[(bx - 0.45 * S, 0), (bx, 0), (bx, 4 * S), (bx - 0.45 * S, 4 * S), (bx - 0.45 * S, 0)], [(bx - 0.22 * S, 0), (bx - 0.22 * S, 4 * S)]]
        else:
            out.append([(bx, 0), (bx, 4 * S)])
    for ly in range(0, 41, 10):
        out.append([(0, ly), (width, ly)])
    return [[(px, py + oy) for px, py in P] for P in out]

def draw_beam(evs, pos):
    ds = [e['d'] for e in evs]
    up = sum(ds) / len(ds) < 34
    ys = [ypos(d) for d in ds]
    sxs = [p + (0.6 * S if up else -0.6 * S) for p in pos]
    dx = sxs[-1] - sxs[0] or 1
    slope = max(-1.0 * S, min(1.0 * S, ys[-1] - ys[0])) / dx * 0.6
    if up: y0 = min(y - 3.4 * S - slope * (sx - sxs[0]) for y, sx in zip(ys, sxs))
    else: y0 = max(y + 3.4 * S - slope * (sx - sxs[0]) for y, sx in zip(ys, sxs))
    by = lambda sx: y0 + slope * (sx - sxs[0])
    t = 0.48 * S * (1 if up else -1)
    out = []
    for e, sx, y in zip(evs, sxs, ys):
        out.append([(sx, y + (-0.15 * S if up else 0.15 * S)), (sx, by(sx))])
    out += thick_bar(sxs[0], by(sxs[0]), sxs[-1], by(sxs[-1]), t)
    # second beams for sixteenths: joined runs, or a stub towards the neighbour
    off = 0.78 * S * (1 if up else -1)
    i = 0; n = len(evs)
    while i < n:
        if evs[i]['base'] == 's':
            j = i
            while j + 1 < n and evs[j + 1]['base'] == 's': j += 1
            if j > i: xa, xb = sxs[i], sxs[j]
            else:
                stub = 1.1 * S
                if i == n - 1: xa, xb = sxs[i] - stub, sxs[i]
                else: xa, xb = sxs[i], sxs[i] + stub
            out += thick_bar(xa, by(xa) + off, xb, by(xb) + off, t * 0.92)
            i = j + 1
        else: i += 1
    for e in evs: e['_up'] = up
    return out

def ties(systems_evs, oy_of):
    """Ties between consecutive notes (same system)."""
    out = []
    for evs, oy in systems_evs:
        for a, b in zip(evs, evs[1:]):
            if a.get('tie') and not a['rest'] and '_x' in a and '_x' in b:
                out += [[(px, py + oy) for px, py in P] for P in tie(a['_x'], b['_x'], a['_y'], below=a['_up'])]
    return out

def balance(widths, n):
    """Split bars into n consecutive systems with the most even total widths."""
    best = None
    def rec(start, k, acc):
        nonlocal best
        if k == 1:
            parts = acc + [list(range(start, len(widths)))]
            if not parts[-1]: return
            m = max(sum(widths[i] for i in p) for p in parts)
            if best is None or m < best[0]: best = (m, parts)
            return
        for end in range(start + 1, len(widths) - k + 2):
            rec(end, k - 1, acc + [list(range(start, end))])
    rec(0, n, [])
    return best[1]

def score(title, credit, key, time, notes, max_w=560.0):
    bars = parse(notes)
    check(title, time, bars)
    mark_accidentals(bars, key)
    widths = [sum(note_width(ev) for ev in b) + 1.2 * S for b in bars]
    pre_first = system_prefix(key, True, time)[1]; pre = system_prefix(key, False, time)[1]
    total = sum(widths)
    n = 1
    while (total + pre * n) / n > max_w and n < len(bars): n += 1
    n = max(n, 2) if len(bars) >= 2 else 1
    parts = balance(widths, n)
    width = max(sum(widths[i] for i in p) + (pre_first if si == 0 else pre) for si, p in enumerate(parts))
    width = max(width, 330.0)
    out = []; sys_evs = []
    oy = 0.0; tops = []
    for si, p in enumerate(parts):
        bs = [bars[i] for i in p]
        out += draw_system(bs, key, time, si == 0, si == len(parts) - 1, width, oy)
        sys_evs.append(([ev for b in bs for ev in b], oy))
        lo = min(min((ypos(ev['d']) for b in bs for ev in b if not ev['rest']), default=0), 0)
        hi = max(max((ypos(ev['d']) for b in bs for ev in b if not ev['rest']), default=40), 40)
        tops.append((oy + lo, oy + hi))
        oy += 10.5 * S
    out += ties(sys_evs, None)
    # title and credit above the first system, clear of its highest note
    top = min(tops[0][0] - 3.6 * S, -2.0 * S)
    out += text(credit, width, top, 0.85 * S, 'HersheySans1', align='right')
    out += text(title, width / 2, top - 1.8 * S, 2.0 * S, 'HersheySerifMed', align='center')
    return out

def slug(t):
    import unicodedata
    s = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return 'song-' + re.sub(r'[^a-z0-9]+', '-', s).strip('-')

if __name__ == '__main__':
    OUT = sys.argv[1]; SHEET = sys.argv[2] if len(sys.argv) > 2 else None
    items = []
    for title, credit, key, time, notes in SONGS:
        L = score(title, credit, key, time, notes)
        it = Item('songs', title, L, title=f'{title} — {credit}'); it.slug = slug(title); items.append(it)
    try:
        import gen_songs_instr as GI
        items += GI.items()
    except ImportError:
        pass
    save(items, OUT)
    P = sorted(export_size(i.lines)[0] for i in items)
    from collections import Counter
    print(Counter(i.cat for i in items), 'points median', P[len(P) // 2], 'max', P[-1])
    if SHEET:
        for i in range(0, len(items), 30):
            sheet(items[i:i + 30], SHEET.replace('.png', f'_{i // 30}.png'), cols=5, cell=3.0)
