"""Cars: the parametric side-profile builder (z up, front of the car to the right, front axle at x = 0,
rear axle at x = -WB). side(**params) returns (y-down polylines, geometry). Lengths are millimetres."""
import math
from gen_cars_lib import *

DEF = dict(
    WB=2600, FO=850, RO=750,                         # wheelbase, front and rear overhang (axle to tip)
    Rw=315, Rwr=None, rim=0.64, rimr=None, rims='5', rimsr=None, spin=0.3, lip=False, tread=0, treadr=None,
    clr=165, gap=40, gapr=None, arch='round', archr=None, arch_dz=0, arch_lip=0, flare=0, flare_lo=0.35,
    # front: chin (bumper bottom), nose (front tip), bonnet leading edge, cowl (windscreen base)
    chin_z=210, chin_dx=60, chin_r=60, chin_b=0,
    nose_z=500, nose_r=130, face_b=0,
    hood_z=760, hood_dx=170, hood_r=170, hood_b=20,
    cowl=-700, cowl_z=1000, cowl_r=40, ws_b=8, hdr=None,
    rake=32, H=1450, roof_fr=200, roof_b=25,
    # rear: 'hatch' | 'notch' (x of tail nodes measured forwards from the rear tip; roof_rx from the rear axle)
    tail='hatch', roof_rx=300, roof_rz=None, roof_rr=180, gl_b=10,
    deck_x=500, deck_z=1000, deck_r=80, deck_b=10,
    tail_x=60, tail_z=1000, tail_r=60, tf_b=0,
    bump_z=520, bump_r=110, rb_b=0,
    rbot_x=60, rbot_z=240, rbot_r=60,
    top=None,                                         # explicit outline nodes from the nose round to the rear bottom
    # glasshouse
    belt_f=980, belt_r=1010, belt=None, a_w=70, roof_t=70, dlo_r=45, dlo=None, no_glass=False,
    c_bot=None, c_top=None,                           # C-pillar front edge (x from the rear axle) at the belt and at the roof
    pillars=(),                                       # ((x_bottom, x_top, width), …) x from the front axle
    glass_upto=None, glass_from=None,
    # doors, lines, lights
    doors=(), door_bot=None, rear_arch_door=None, handles=(), sill=False, sill_z=None,
    lines=(), free_lines=(), outlines=(), head=None, tail_light=None, mirror=True, mirror_at=None, mirror_s=1.0,
    fuel=None, glare=False, ops=(), hook=None,
)

def P(**k):
    d = dict(DEF); d.update(k); return d

def side_of(a, b, inside):
    """Half-plane bounded by the line a-b that contains the point `inside`."""
    for s in (1, -1):
        h = hp(a, b, s)
        if h.contains(Point(inside)): return h
    return hp(a, b, 1)

class G:  # geometry handed to hooks
    pass

def body_nodes(p):
    WB, FO, RO = p['WB'], p['FO'], p['RO']
    xf, xr, xra = FO, -WB - RO, -WB
    rfx = p['hdr'] if p['hdr'] is not None else p['cowl'] - (p['H'] - p['cowl_z']) / math.tan(math.radians(p['rake']))
    if p['top']:
        N = [(xf - p['chin_dx'], p['chin_z'], p['chin_r'], p['chin_b'])] + [tuple(n) for n in p['top']]
    else:
        N = [(xf - p['chin_dx'], p['chin_z'], p['chin_r'], p['chin_b']),
             (xf, p['nose_z'], p['nose_r'], p['face_b']),
             (xf - p['hood_dx'], p['hood_z'], p['hood_r'], p['hood_b'])]
        N += [tuple(n) for n in p.get('hood_extra', ())]
        N.append((p['cowl'], p['cowl_z'], p['cowl_r'], p['ws_b']))
        N.append((rfx, p['H'], p['roof_fr'], p['roof_b']))
        N += [tuple(n) for n in p.get('roof_extra', ())]
        rrz = p['roof_rz'] if p['roof_rz'] is not None else p['H'] - 20
        N.append((xra + p['roof_rx'], rrz, p['roof_rr'], p['gl_b']))
        N += [tuple(n) for n in p.get('gl_extra', ())]
        if p['tail'] == 'notch':
            N.append((xr + p['deck_x'], p['deck_z'], p['deck_r'], p['deck_b']))
        N += [tuple(n) for n in p.get('deck_extra', ())]
        N.append((xr + p['tail_x'], p['tail_z'], p['tail_r'], p['tf_b']))
        N.append((xr, p['bump_z'], p['bump_r'], p['rb_b']))
        N.append((xr + p['rbot_x'], p['rbot_z'], p['rbot_r']))
    Rw = p['Rw']; Rwr = p['Rwr'] or Rw
    Ra = Rw + p['gap']; Rar = Rwr + (p['gapr'] if p['gapr'] is not None else p['gap'])
    zb = p['rbot_z'] if not p['top'] else N[-1][1]
    N += [(xra - 0.8 * Rar, min(zb, Rwr + 0.3 * Rar), 0), (xra + 0.8 * Rar, p['clr'], 0), (-0.8 * Ra, p['clr'], 0),
          (0.8 * Ra, min(p['chin_z'], Rw + 0.3 * Ra), 0)]
    return N, rfx

def arch_shape(p, xc, R, kind, gap):
    zc = R + p['arch_dz']; Ra = R + gap
    if kind == 'round': return ring(xc, zc, Ra)
    if kind == 'flat': return ring(xc, zc, Ra).intersection(box(xc - 2 * Ra, -1e4, xc + 2 * Ra, zc + Ra * 0.82))
    if kind == 'square':
        return rpoly([(xc - Ra * 1.04, zc - Ra * 1.6, 0), (xc - Ra * 0.95, zc + Ra * 0.62, Ra * 0.42),
                      (xc + Ra * 0.95, zc + Ra * 0.62, Ra * 0.42), (xc + Ra * 1.04, zc - Ra * 1.6, 0)])
    if kind == 'oval': return ell(xc, zc, Ra * 1.12, Ra * 0.98)
    if kind == 'skirt': return ring(xc, zc, Ra).intersection(box(xc - 2 * Ra, -1e4, xc + 2 * Ra, zc - 0.05 * Ra))
    if kind == 'none': return Polygon()
    return ring(xc, zc, Ra)

def _geom(d):
    if hasattr(d, 'geom_type'): return d
    return rpoly(d)

def _do(sc, op, g):
    """ops: (stage, kind, data); kind: 'solid' (filled, outlined), 'outline' (lines only), 'cut' (white-out),
    'line' (one polyline), 'lines' (polylines), 'inbody' (polylines clipped to the body), 'fn' (callable)."""
    kind, d = op[1], op[2]
    if kind == 'solid': sc.geom(_geom(d))
    elif kind == 'outline': sc.geom(_geom(d), fill=False)
    elif kind == 'cut': sc.cut(_geom(d))
    elif kind == 'line': sc.line(d)
    elif kind == 'lines': sc.lines(d)
    elif kind == 'inbody': sc.lines(clip(d, g.body.buffer(-24)))
    elif kind == 'fn': d(sc, g)

def side(**k):
    p = P(**k)
    WB, FO, RO, Rw = p['WB'], p['FO'], p['RO'], p['Rw']
    Rwr = p['Rwr'] or Rw
    xf, xr, xra = FO, -WB - RO, -WB
    nodes, rfx = body_nodes(p)
    sil = rpoly(nodes)
    gapr = p['gapr'] if p['gapr'] is not None else p['gap']
    archF = arch_shape(p, 0, Rw, p['arch'], p['gap'])
    archR = arch_shape(p, xra, Rwr, p['archr'] or p['arch'], gapr)
    body = biggest(sil.difference(archF).difference(archR))
    g = G(); g.p = p; g.sil = sil; g.body = body; g.rfx = rfx; g.xf, g.xr, g.xra = xf, xr, xra
    g.archF, g.archR = archF, archR
    sc = Scene(); g.sc = sc
    stage = lambda s: [_do(sc, op, g) for op in p['ops'] if op[0] == s]
    stage('back')
    # ---- wheels (behind the body)
    wheel(sc, 0, Rw, Rw, rim=p['rim'], style=p['rims'], spin=p['spin'], lip=p['lip'], tread=p['tread'])
    wheel(sc, xra, Rwr, Rwr, rim=p['rimr'] or p['rim'], style=p['rimsr'] or p['rims'], spin=p['spin'] + 0.4, lip=p['lip'],
          tread=p['treadr'] if p['treadr'] is not None else p['tread'])
    stage('mid')
    # ---- body
    sc.geom(body)
    if p['flare']:
        for a, xc, R in ((archF, 0, Rw), (archR, xra, Rwr)):
            if a.is_empty: continue
            band = a.buffer(p['flare'], join_style=1).difference(a)
            band = biggest(band.intersection(box(xc - 3 * R, R - R * p['flare_lo'], xc + 3 * R, 5000)))
            if not band.is_empty: sc.geom(band)
    if p['arch_lip']:
        for a in (archF, archR):
            if a.is_empty: continue
            sc.lines(clip(lines_of(a.buffer(p['arch_lip'], join_style=1).exterior), body.buffer(-8)))
    # ---- glasshouse
    bf = (p['cowl'], p['belt_f']); br = (xra + (p['c_bot'] if p['c_bot'] is not None else p['roof_rx'] - 300), p['belt_r'])
    if p['belt']:
        BL = sorted(p['belt'])
        def belt_z(x): return float(np.interp(x, [q[0] for q in BL], [q[1] for q in BL]))
    else:
        def belt_z(x):
            t = (x - br[0]) / (bf[0] - br[0]) if bf[0] != br[0] else 0
            return br[1] + (bf[1] - br[1]) * t
    g.belt_z = belt_z
    if p['dlo']:
        dlo = _geom(p['dlo'])
    elif p['no_glass']:
        dlo = Polygon()
    else:
        inner = sil.buffer(-p['roof_t'], join_style=1)
        xs = [xr - 500] + ([q[0] for q in BL] if p['belt'] else []) + [xf + 500]
        above = Polygon([(x, belt_z(x)) for x in sorted(xs)] + [(xf + 500, 9000), (xr - 500, 9000)])
        dlo = inner.intersection(above)
        a0 = (p['cowl'] - p['a_w'], p['cowl_z']); a1 = (rfx - p['a_w'], p['H'])   # A-pillar: windscreen line moved back
        dlo = dlo.intersection(side_of(a0, a1, (a0[0] - 800, a0[1])))
        if p['c_top'] is not None:
            c0 = (xra + p['c_bot'], belt_z(xra + p['c_bot'])); c1 = (xra + p['c_top'], p['H'])
            dlo = dlo.intersection(side_of(c0, c1, (c0[0] + 800, c0[1])))
        if p['glass_upto'] is not None: dlo = dlo.intersection(box(p['glass_upto'], -1e4, 1e4, 1e4))
        if p['glass_from'] is not None: dlo = dlo.intersection(box(-1e4, -1e4, p['glass_from'], 1e4))
        dlo = rounded(biggest(dlo), p['dlo_r'])
    g.dlo = dlo
    wins = dlo
    for pl in p['pillars']:
        xb, xt, w = pl[:3]
        band = LineString([(xb, belt_z(xb) - 400), (xt, p['H'] + 400)]).buffer(w / 2, cap_style=2)
        wins = wins.difference(band)
    W = [rounded(q, p['dlo_r'] * 0.6) for q in (wins.geoms if hasattr(wins, 'geoms') else [wins]) if q.area > 2000]
    W.sort(key=lambda q: -q.centroid.x)
    g.windows = W
    for q in W: sc.geom(q, fill=False)
    # ---- doors
    dbot = p['door_bot'] if p['door_bot'] is not None else p['clr'] + 70
    g.dbot = dbot
    door_x = []
    for d in p['doors']:
        xt, xb = d[0], d[1]; bend = d[2] if len(d) > 2 else 0
        zt = d[3] if len(d) > 3 else belt_z(xt)
        sc.line(quad((xt, zt), ((xt + xb) / 2 + bend, (zt + dbot) / 2), (xb, dbot), n=10)); door_x.append(xb)
    if p['rear_arch_door'] is not None:
        # the rear door's back edge: down from the belt, then round the front of the rear wheel arch
        xt, off, xm = p['rear_arch_door']
        Ra = Rwr + gapr + off; zc = Rwr + p['arch_dz']
        a_top = math.acos(max(-0.95 * Ra, min(0.95 * Ra, xm)) / Ra)
        ang_end = math.asin(max(-1, min(1, (dbot - zc) / Ra)))
        Pd = [(xra + xt, belt_z(xra + xt))] + arc(xra, zc, Ra, a_top, ang_end, n=16)
        sc.line(Pd); door_x.append(Pd[-1][0])
    if len(door_x) >= 2:
        sc.line([(min(door_x), dbot), (max(door_x), dbot)])
    if p['sill']:
        sz = p['sill_z'] or p['clr'] + 60
        sc.lines(clip([[(xra, sz), (0, sz)]], body.buffer(-24)))
    for h in p['handles']:
        hx, hz = h[:2]; hw = h[2] if len(h) > 2 else 140
        sc.geom(capsule((hx - hw / 2, hz), (hx + hw / 2, hz), 38), fill=False)
    # ---- lines and lights
    for L in p['lines']: sc.lines(clip([L], body.buffer(-28)))
    for L in p['free_lines']: sc.line(L)
    for nodes in p['outlines']:
        sh = _geom(nodes).intersection(body.buffer(-20))
        for q in (sh.geoms if hasattr(sh, 'geoms') else [sh]):
            if q.geom_type == 'Polygon' and q.area > 500: sc.geom(q, fill=False)
    for key, x0, sgn in (('head', xf, -1), ('tail_light', xr, 1)):
        lt = p[key]
        if not lt: continue
        for pts in [lt['pts']] + list(lt.get('more', [])):
            sh = Polygon([(x0 + sgn * a, z) for a, z in pts]).buffer(0)
            sh = rounded(sh.intersection(sil.buffer(-lt.get('inset', 28))), lt.get('r', 25))
            sh = biggest(sh)
            if not sh.is_empty: sc.geom(sh, fill=False)
        for L in lt.get('lines', []):
            sc.lines(clip([[(x0 + sgn * a, z) for a, z in L]], sil.buffer(-lt.get('inset', 28) - 10)))
    if p['fuel']:
        fx, fz = p['fuel']; sc.geom(Polygon(rect(xra + fx - 70, fz - 70, 140, 140, 30)), fill=False)
    stage('body')
    # ---- mirror (in front of the window frame)
    if p['mirror']:
        mx, mz = p['mirror_at'] if p['mirror_at'] else (p['cowl'] - p['a_w'] - 60, belt_z(p['cowl']) + 40)
        s = p['mirror_s']
        sc.geom(rpoly([(mx - 90 * s, mz - 20 * s, 30 * s), (mx + 150 * s, mz - 10 * s, 40 * s), (mx + 140 * s, mz + 130 * s, 50 * s), (mx - 60 * s, mz + 120 * s, 40 * s)]))
    if p['glare']:
        for q in W[:1]:
            c = q.centroid; x0, y0, x1, y1 = q.bounds
            for d in (0, 70):
                sc.lines(clip([[(c.x - 160 + d, y0), (c.x + 60 + d, y1)]], q.buffer(-45)))
    stage('front')
    if p['hook']: p['hook'](sc, g)
    return flip(sc.render()), g
