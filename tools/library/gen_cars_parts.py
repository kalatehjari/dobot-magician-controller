"""Cars: small parts shared by the presets (roof racks, signs, luggage, people-free props). z up."""
import math
from gen_cars_lib import *

def top_z(g, x, shape=None):
    """Height of the body's upper outline at x."""
    s = shape if shape is not None else g.sil
    v = LineString([(x, -100), (x, 6000)]).intersection(s)
    if v.is_empty: return None
    return v.bounds[3]

def rails(x0, x1, g, h=60, t=45, feet=True):
    """Roof rails seen from the side: a bar following the roof, held on short feet."""
    xs = np.linspace(x0, x1, 14)
    zs = [top_z(g, x) for x in xs]
    pts = [(x, z + h) for x, z in zip(xs, zs)]
    bar = LineString(pts).buffer(t / 2, cap_style=1, quad_segs=6)
    out = [bar]
    if feet:
        for x, z in ((xs[0], zs[0]), (xs[-1], zs[-1])):
            out.append(rpoly([(x - 50, z - 30, 0), (x + 50, z - 30, 0), (x + 40, z + h, 10), (x - 40, z + h, 10)]))
    return unary_union(out)

def bars(xs, g, h=90, w=70):
    """Cross bars seen end-on: small feet with the bar section on top."""
    out = []
    for x in xs:
        z = top_z(g, x)
        out.append(rpoly([(x - w / 2 - 10, z - 20, 0), (x + w / 2 + 10, z - 20, 0), (x + w / 2, z + h, 12), (x - w / 2, z + h, 12)]))
    return out

def cable(a, b, sag=250, n=30):
    """A hanging cable between two points."""
    m = ((a[0] + b[0]) / 2, min(a[1], b[1]) - sag)
    return quad(a, m, b, n=n)
