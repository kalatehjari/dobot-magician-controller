/* ===================== SVG → STROKES (browser DOM) ===================== */
const SVG_NS = 'http://www.w3.org/2000/svg';

function ellipseD(cx, cy, rx, ry) {
  return `M${cx - rx} ${cy} A${rx} ${ry} 0 1 0 ${cx + rx} ${cy} A${rx} ${ry} 0 1 0 ${cx - rx} ${cy} Z`;
}

// Turns basic shapes into an equivalent <path> so one code path handles everything.
function primitiveToD(el) {
  const g = n => parseFloat(el.getAttribute(n) || '0');
  switch (el.tagName.toLowerCase()) {
    case 'line': return `M${g('x1')} ${g('y1')} L${g('x2')} ${g('y2')}`;
    case 'polyline':
    case 'polygon': {
      const v = (el.getAttribute('points') || '').trim().split(/[\s,]+/).map(Number);
      if (v.length < 4) return '';
      let d = `M${v[0]} ${v[1]}`;
      for (let i = 2; i + 1 < v.length; i += 2) d += ` L${v[i]} ${v[i + 1]}`;
      return el.tagName.toLowerCase() === 'polygon' ? d + ' Z' : d;
    }
    case 'rect': {
      const x = g('x'), y = g('y'), w = g('width'), h = g('height');
      return `M${x} ${y} H${x + w} V${y + h} H${x} Z`;
    }
    case 'circle': return ellipseD(g('cx'), g('cy'), g('r'), g('r'));
    case 'ellipse': return ellipseD(g('cx'), g('cy'), g('rx'), g('ry'));
    default: return '';
  }
}

// Parses an SVG string into polylines in SVG user units, with all group transforms applied.
// Uses the browser's own geometry engine (getTotalLength / getPointAtLength), so every SVG
// path command (curves, arcs, relative moves) is handled correctly.
function svgToStrokes(svgText) {
  const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
  if (doc.getElementsByTagName('parsererror').length) throw new Error('This is not valid SVG');
  const root = doc.documentElement;
  if (root.nodeName.toLowerCase() !== 'svg') throw new Error('File has no <svg> root');

  // Overall size, used to choose sampling density.
  let dim = 1000;
  const vb = (root.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
  if (vb.length === 4 && vb[2] > 0) dim = Math.max(vb[2], vb[3]);

  // Hidden host so getPointAtLength works (needs layout context).
  const host = document.createElementNS(SVG_NS, 'svg');
  host.setAttribute('width', '1'); host.setAttribute('height', '1');
  host.style.cssText = 'position:absolute;left:-9999px;top:0;visibility:hidden';
  document.body.appendChild(host);
  try {
    const imported = document.importNode(root, true);
    imported.removeAttribute('viewBox');
    host.appendChild(imported);

    // Convert primitives in place (keeping parent transforms) into paths.
    const prims = Array.from(imported.querySelectorAll('line,polyline,polygon,rect,circle,ellipse'));
    for (const el of prims) {
      if (el.closest('defs,clipPath,mask,symbol,pattern,marker')) continue;
      const d = primitiveToD(el);
      if (!d) continue;
      const p = document.createElementNS(SVG_NS, 'path');
      p.setAttribute('d', d);
      const tr = el.getAttribute('transform');
      if (tr) p.setAttribute('transform', tr);
      el.parentNode.replaceChild(p, el);
    }

    const paths = Array.from(imported.querySelectorAll('path'))
      .filter(p => !p.closest('defs,clipPath,mask,symbol,pattern,marker,[display="none"]'));

    const strokes = [];
    for (const p of paths) {
      let L = 0;
      try { L = p.getTotalLength(); } catch (e) { continue; }
      if (!(L > 0)) continue;
      const ctm = p.getCTM();
      if (!ctm) continue;
      const scMax = Math.max(Math.hypot(ctm.a, ctm.b), Math.hypot(ctm.c, ctm.d)) || 1;

      // Sample at ~1/600 of the drawing size; cap for very long paths.
      const n = Math.min(8000, Math.max(2, Math.ceil(L / (dim / 600))));
      const step = L / n;
      const jump = step * scMax * 1.6;   // a larger gap means a new sub-path (moveto)

      let cur = [], prev = null;
      for (let i = 0; i <= n; i++) {
        const q = p.getPointAtLength(Math.min(L, i * step));
        const t = new DOMPoint(q.x, q.y).matrixTransform(ctm);
        const pt = { x: t.x, y: t.y };
        if (prev && dist(prev, pt) > jump) {
          if (cur.length > 1) strokes.push(cur);
          cur = [];
        }
        cur.push(pt);
        prev = pt;
      }
      if (cur.length > 1) strokes.push(cur);
    }
    return strokes;
  } finally {
    host.remove();
  }
}

// Cleans strokes: removes duplicate points, simplifies, drops strokes shorter than minLen.
function cleanStrokes(strokes, tol, minLen) {
  const out = [];
  for (const s of strokes) {
    const dedup = [s[0]];
    for (let i = 1; i < s.length; i++) if (dist(dedup[dedup.length - 1], s[i]) > 1e-6) dedup.push(s[i]);
    if (dedup.length < 2) continue;
    const simp = rdp(dedup, tol);
    if (polyLength(simp) < minLen) continue;
    out.push(simp);
  }
  return out;
}
