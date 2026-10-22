import re, html, json, sys, math, collections
SRC = sys.argv[1]
files = ['HersheySans1','HersheySansMed','HersheySerifMed','HersheySerifMedItalic','HersheySerifBold','HersheySerifBoldItalic',
         'HersheyScript1','HersheyScriptMed','HersheyGothEnglish','EMSReadability','EMSReadabilityItalic','EMSNixish','EMSNixishItalic',
         'EMSTech','EMSOsmotron','EMSAllure','EMSFelix','EMSElfin']
tot_pts = 0; cmds = collections.Counter()
for f in files:
    s = open(f'{SRC}/{f}.svg', encoding='utf-8').read()
    fadv = float(re.search(r'<font [^>]*horiz-adv-x="([\d.]+)"', s).group(1))
    glyphs = re.findall(r'<glyph\b([^>]*)/>', s, re.S)
    npts = 0; nstrokes = 0; maxd = 0; H = None
    for g in glyphs:
        u = re.search(r'unicode="([^"]*)"', g); d = re.search(r'\bd="([^"]*)"', g)
        if not d: continue
        for c in re.findall(r'[A-Za-z]', d.group(1)): cmds[c] += 1
        nums = re.findall(r'-?[\d.]+(?:e-?\d+)?', d.group(1))
        npts += len(nums) // 2
        nstrokes += d.group(1).count('M')
        ch = html.unescape(u.group(1)) if u else None
        if ch == 'H':
            ys = [float(v) for v in nums[1::2]]; H = (min(ys), max(ys))
    tot_pts += npts
    print(f'{f:24s} glyphs {len(glyphs):3d} pts {npts:6d} strokes {nstrokes:5d} adv {fadv} H {H}')
print('total points', tot_pts, 'commands', dict(cmds))
