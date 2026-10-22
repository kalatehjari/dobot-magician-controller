import sys, statistics, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontlib import read_svg_font, read_hershey_json
SRC = sys.argv[1]
names = ['HersheySans1','HersheyScript1','HersheyScriptMed','HersheyGothEnglish','EMSReadability','EMSNixish','EMSTech','EMSOsmotron','EMSAllure','EMSFelix','EMSElfin']
def ext(F, chars):
    t, b = [], []
    for ch in chars:
        g = F['glyphs'].get(ch)
        if not g or not g[1]: continue
        ys = [p[1] for s in g[1] for p in s]; t.append(max(ys)); b.append(min(ys))
    return statistics.median(b), statistics.median(t)
for n in names + ['gothicger', 'gothicita']:
    F = read_svg_font(f'{SRC}/svg_fonts/{n}.svg') if not n.startswith('gothic') else read_hershey_json(f'{SRC}/hersheytext.json', n)
    cb, ct = ext(F, 'BDEFHIKLMNPRTUVWXZ'); lb, lt = ext(F, 'xzvwmnruaceos'); ab, at = ext(F, 'bdhkl'); db, dt = ext(F, 'gpqy')
    d1 = ext(F, '1234567890')
    print(f'{n:20s} caps {cb:7.1f}..{ct:6.1f}  lower {lb:7.1f}..{lt:6.1f}  asc ..{at:6.1f}  desc {db:7.1f}  digits {d1[0]:7.1f}..{d1[1]:6.1f}')
