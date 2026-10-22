/* ===================== SVG → STROKES (browser DOM) ===================== */
const SVG_NS = 'http://www.w3.org/2000/svg';

function ellipseD(cx, cy, rx, ry) {
  return `M${cx - rx} ${cy} A${rx} ${ry} 0 1 0 ${cx + rx} ${cy} A${rx} ${ry} 0 1 0 ${cx - rx} ${cy} Z`;
}

// Turns basic shapes into an equivalent <path> so one code path handles everything.
function primitiveToD(el) {
  const g = n => parseFloat(el.getAttribute(n) || '0') || 0;
  switch (el.localName.toLowerCase()) {
    case 'line': return `M${g('x1')} ${g('y1')} L${g('x2')} ${g('y2')}`;
    case 'polyline':
    case 'polygon': {
      const v = (el.getAttribute('points') || '').trim().split(/[\s,]+/).map(Number);
      if (v.length < 4) return '';
      let d = `M${v[0]} ${v[1]}`;
      for (let i = 2; i + 1 < v.length; i += 2) d += ` L${v[i]} ${v[i + 1]}`;
      return el.localName.toLowerCase() === 'polygon' ? d + ' Z' : d;
    }
    case 'rect': {
      const x = g('x'), y = g('y'), w = g('width'), h = g('height');
      if (!(w > 0 && h > 0)) return '';
      let rx = el.hasAttribute('rx') ? g('rx') : NaN, ry = el.hasAttribute('ry') ? g('ry') : NaN;
      if (isNaN(rx)) rx = isNaN(ry) ? 0 : ry;
      if (isNaN(ry)) ry = rx;
      rx = Math.min(Math.max(rx, 0), w / 2); ry = Math.min(Math.max(ry, 0), h / 2);
      if (!rx || !ry) return `M${x} ${y} H${x + w} V${y + h} H${x} Z`;
      return `M${x + rx} ${y} H${x + w - rx} A${rx} ${ry} 0 0 1 ${x + w} ${y + ry} V${y + h - ry} A${rx} ${ry} 0 0 1 ${x + w - rx} ${y + h}` +
        ` H${x + rx} A${rx} ${ry} 0 0 1 ${x} ${y + h - ry} V${y + ry} A${rx} ${ry} 0 0 1 ${x + rx} ${y} Z`;
    }
    case 'circle': return g('r') > 0 ? ellipseD(g('cx'), g('cy'), g('r'), g('r')) : '';
    case 'ellipse': return g('rx') > 0 && g('ry') > 0 ? ellipseD(g('cx'), g('cy'), g('rx'), g('ry')) : '';
    default: return '';
  }
}

// SVG path data → polylines in the path's own units. Curves and arcs are cut into straight pieces no
// longer than `step`. Follows the SVG rules (implicit repeats, relative commands, S/T reflections,
// arc radius correction); on malformed data it keeps what was read so far, like a browser does.
function pathDataToPolylines(d, step) {
  const out = [], n = d.length;
  let i = 0, cur = null, x = 0, y = 0, sx = 0, sy = 0, lc = null, lq = null;
  step = step > 0 ? step : 1;
  const skip = () => { while (i < n) { const c = d.charCodeAt(i); if (c === 32 || c === 44 || c === 9 || c === 10 || c === 13 || c === 12) i++; else break; } };
  const numRe = /[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/y;
  const num = () => { skip(); numRe.lastIndex = i; const m = numRe.exec(d); if (!m) throw new Error('number expected'); i = numRe.lastIndex; return parseFloat(m[0]); };
  const flag = () => { skip(); const c = d[i]; if (c === '0' || c === '1') { i++; return c === '1'; } throw new Error('flag expected'); };
  const more = () => { skip(); if (i >= n) return false; const c = d[i]; return (c >= '0' && c <= '9') || c === '-' || c === '+' || c === '.'; };
  const flush = () => { if (cur && cur.length > 1) out.push(cur); cur = null; };
  const begin = () => { if (!cur) cur = [{ x, y }]; };
  const moveTo = (px, py) => { flush(); x = sx = px; y = sy = py; cur = [{ x, y }]; };
  const lineTo = (px, py) => { begin(); cur.push({ x: px, y: py }); x = px; y = py; };
  const cubic = (x1, y1, x2, y2, px, py) => {
    const len = Math.hypot(x1 - x, y1 - y) + Math.hypot(x2 - x1, y2 - y1) + Math.hypot(px - x2, py - y2);
    const k = Math.min(1000, Math.max(1, Math.ceil(len / step))), x0 = x, y0 = y;
    begin();
    for (let j = 1; j <= k; j++) {
      const t = j / k, u = 1 - t, a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, e = t * t * t;
      cur.push({ x: a * x0 + b * x1 + c * x2 + e * px, y: a * y0 + b * y1 + c * y2 + e * py });
    }
    x = px; y = py;
  };
  const quad = (x1, y1, px, py) => cubic(x + 2 / 3 * (x1 - x), y + 2 / 3 * (y1 - y), px + 2 / 3 * (x1 - px), py + 2 / 3 * (y1 - py), px, py);
  const arc = (rx, ry, phi, fa, fs, px, py) => {
    if (x === px && y === py) return;
    rx = Math.abs(rx); ry = Math.abs(ry);
    if (!rx || !ry) { lineTo(px, py); return; }
    const cp = Math.cos(phi * Math.PI / 180), sp = Math.sin(phi * Math.PI / 180);
    const dx = (x - px) / 2, dy = (y - py) / 2, x1 = cp * dx + sp * dy, y1 = -sp * dx + cp * dy;
    const lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry);
    if (lam > 1) { rx *= Math.sqrt(lam); ry *= Math.sqrt(lam); }
    const den = rx * rx * y1 * y1 + ry * ry * x1 * x1;
    let co = den ? Math.sqrt(Math.max(0, (rx * rx * ry * ry - den) / den)) : 0;
    if (fa === fs) co = -co;
    const cxp = co * rx * y1 / ry, cyp = -co * ry * x1 / rx;
    const cx = cp * cxp - sp * cyp + (x + px) / 2, cy = sp * cxp + cp * cyp + (y + py) / 2;
    const ang = (ux, uy, vx, vy) => Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
    const ux = (x1 - cxp) / rx, uy = (y1 - cyp) / ry, vx = (-x1 - cxp) / rx, vy = (-y1 - cyp) / ry;
    const t1 = ang(1, 0, ux, uy);
    let dt = ang(ux, uy, vx, vy);
    if (!fs && dt > 0) dt -= 2 * Math.PI; else if (fs && dt < 0) dt += 2 * Math.PI;
    const k = Math.min(1000, Math.max(2, Math.ceil(Math.abs(dt) * Math.max(rx, ry) / step)));
    begin();
    for (let j = 1; j < k; j++) {
      const t = t1 + dt * j / k, ex = rx * Math.cos(t), ey = ry * Math.sin(t);
      cur.push({ x: cp * ex - sp * ey + cx, y: sp * ex + cp * ey + cy });
    }
    cur.push({ x: px, y: py });
    x = px; y = py;
  };
  try {
    while (true) {
      skip();
      if (i >= n) break;
      const ch = d[i];
      if (!/[a-zA-Z]/.test(ch)) throw new Error('command expected');
      i++;
      const rel = ch >= 'a', C = ch.toUpperCase();
      if (C === 'Z') {
        if (cur) { if (cur.length) lineTo(sx, sy); flush(); }
        x = sx; y = sy; lc = lq = null;
        continue;
      }
      let first = true;
      do {
        const ox = rel ? x : 0, oy = rel ? y : 0;
        let nlc = null, nlq = null;
        switch (C) {
          case 'M': { const px = num() + ox, py = num() + oy; if (first) moveTo(px, py); else lineTo(px, py); break; }
          case 'L': { const px = num() + ox, py = num() + oy; lineTo(px, py); break; }
          case 'H': lineTo(num() + ox, y); break;
          case 'V': lineTo(x, num() + oy); break;
          case 'C': { const x1 = num() + ox, y1 = num() + oy, x2 = num() + ox, y2 = num() + oy, px = num() + ox, py = num() + oy; cubic(x1, y1, x2, y2, px, py); nlc = { x: x2, y: y2 }; break; }
          case 'S': { const x2 = num() + ox, y2 = num() + oy, px = num() + ox, py = num() + oy, x1 = lc ? 2 * x - lc.x : x, y1 = lc ? 2 * y - lc.y : y; cubic(x1, y1, x2, y2, px, py); nlc = { x: x2, y: y2 }; break; }
          case 'Q': { const x1 = num() + ox, y1 = num() + oy, px = num() + ox, py = num() + oy; quad(x1, y1, px, py); nlq = { x: x1, y: y1 }; break; }
          case 'T': { const px = num() + ox, py = num() + oy, x1 = lq ? 2 * x - lq.x : x, y1 = lq ? 2 * y - lq.y : y; quad(x1, y1, px, py); nlq = { x: x1, y: y1 }; break; }
          case 'A': { const rx = num(), ry = num(), phi = num(), fa = flag(), fs = flag(), px = num() + ox, py = num() + oy; arc(rx, ry, phi, fa, fs, px, py); break; }
          default: throw new Error('unknown command ' + ch);
        }
        lc = nlc; lq = nlq; first = false;
      } while (more());
    }
  } catch (e) { /* malformed data: keep what was read */ }
  flush();
  return out;
}

// Parses SVG text; files that forgot the SVG namespace (common in older clip art and hand-written
// files) are read as SVG anyway.
function parseSvgDoc(svgText) {
  const parse = t => new DOMParser().parseFromString(t, 'image/svg+xml');
  const bad = doc => doc.getElementsByTagName('parsererror').length > 0;
  let doc = parse(svgText);
  if (!bad(doc) && doc.documentElement.localName === 'svg' && doc.documentElement.namespaceURI === SVG_NS) return doc;
  const head = svgText.match(/<svg\b[^>]*>/i);
  if (head) {
    let tag = head[0];
    if (!/\sxmlns\s*=/.test(tag)) tag = tag.replace(/^<svg\b/i, `<svg xmlns="${SVG_NS}"`);
    if (/xlink:/.test(svgText) && !/\sxmlns:xlink\s*=/.test(tag)) tag = tag.replace(/^<svg\b/i, '<svg xmlns:xlink="http://www.w3.org/1999/xlink"');
    const fixed = parse(svgText.replace(head[0], tag));
    if (!bad(fixed) && fixed.documentElement.localName === 'svg' && fixed.documentElement.namespaceURI === SVG_NS) return fixed;
  }
  if (bad(doc)) throw new Error('This is not valid SVG');
  throw new Error('File has no <svg> root');
}

// <use> copies (a shape drawn again elsewhere) become real groups, so their outlines are drawn too.
function expandUses(root) {
  const XL = 'http://www.w3.org/1999/xlink';
  for (let pass = 0; pass < 4; pass++) {
    const uses = Array.from(root.querySelectorAll('use')).filter(u => !u.closest('defs,clipPath,mask,symbol,pattern,marker'));
    if (!uses.length) return;
    for (const u of uses) {
      const href = u.getAttribute('href') || u.getAttributeNS(XL, 'href') || '';
      let ref = null;
      try { ref = href.startsWith('#') ? root.querySelector('#' + CSS.escape(href.slice(1))) : null; } catch (e) { ref = null; }
      const g = document.createElementNS(SVG_NS, 'g');
      for (const a of Array.from(u.attributes))
        if (!['href', 'xlink:href', 'x', 'y', 'width', 'height', 'transform', 'id'].includes(a.name)) g.setAttribute(a.name, a.value);
      const x = parseFloat(u.getAttribute('x') || '0') || 0, y = parseFloat(u.getAttribute('y') || '0') || 0;
      g.setAttribute('transform', `${u.getAttribute('transform') || ''} translate(${x} ${y})`);
      if (ref && !ref.contains(u)) {
        let c;
        if (ref.localName === 'symbol') {
          c = document.createElementNS(SVG_NS, 'g');
          for (const ch of Array.from(ref.childNodes)) c.appendChild(ch.cloneNode(true));
        } else c = ref.cloneNode(true);
        c.removeAttribute('id');
        c.querySelectorAll('[id]').forEach(e => e.removeAttribute('id'));
        g.appendChild(c);
      }
      u.parentNode.replaceChild(g, u);
    }
  }
}

// True when the shape would not show on screen: hidden, fully transparent, or with neither a fill
// nor an outline (construction lines, invisible frames). Those are not drawn by the pen either.
function shapeHidden(el, top) {
  const cs = getComputedStyle(el);
  const noFill = cs.fill === 'none' || parseFloat(cs.fillOpacity) === 0;
  const noStroke = cs.stroke === 'none' || parseFloat(cs.strokeOpacity) === 0 || parseFloat(cs.strokeWidth) === 0;
  if (noFill && noStroke) return true;
  if (cs.visibility === 'hidden' || cs.visibility === 'collapse') return true;
  for (let e = el; e && e !== top.parentNode; e = e.parentNode) {
    const s = getComputedStyle(e);
    if (s.display === 'none' || parseFloat(s.opacity) === 0) return true;
  }
  return false;
}

// Average colour of a gradient's stops (over white), following href to inherited stops.
function gradientRGB(top, id, depth = 0) {
  let g = null;
  try { g = top.querySelector('#' + CSS.escape(id)); } catch (e) { return null; }
  if (!g || depth > 4) return null;
  const stops = Array.from(g.querySelectorAll('stop'));
  if (!stops.length) {
    const h = g.getAttribute('href') || g.getAttributeNS('http://www.w3.org/1999/xlink', 'href') || '';
    return h.startsWith('#') ? gradientRGB(top, h.slice(1), depth + 1) : null;
  }
  let r = 0, gr = 0, b = 0, n = 0;
  for (const st of stops) {
    const cs = getComputedStyle(st), m = (cs.stopColor || '').match(/rgba?\(([^)]*)\)/);
    if (!m) continue;
    const v = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat);
    let a = parseFloat(cs.stopOpacity); if (!Number.isFinite(a)) a = 1;
    if (v.length > 3 && Number.isFinite(v[3])) a *= v[3];
    r += v[0] * a + 255 * (1 - a); gr += v[1] * a + 255 * (1 - a); b += v[2] * a + 255 * (1 - a); n++;
  }
  return n ? [r / n, gr / n, b / n] : null;
}

// How a shape is filled: colour [r, g, b] (null = no fill), opacity (including its groups') and
// fill rule. Gradients count as their average colour; patterns as mid grey.
function svgPaint(el, top) {
  const cs = getComputedStyle(el);
  let alpha = parseFloat(cs.fillOpacity); if (!Number.isFinite(alpha)) alpha = 1;
  for (let e = el; e && e !== top.parentNode; e = e.parentNode) { const o = parseFloat(getComputedStyle(e).opacity); if (Number.isFinite(o)) alpha *= o; }
  const f = cs.fill || 'none';
  let rgb = null;
  const u = f.match(/url\(\s*["']?[^"')]*#([^"')\s]+)["']?\s*\)/);
  if (u) rgb = gradientRGB(top, u[1]) || [128, 128, 128];
  else if (f !== 'none') {
    const m = f.match(/rgba?\(([^)]*)\)/);
    if (m) { const v = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat); rgb = v.slice(0, 3); if (v.length > 3 && Number.isFinite(v[3])) alpha *= v[3]; }
  }
  return { fill: rgb, alpha: Math.max(0, Math.min(1, alpha)), rule: cs.fillRule === 'evenodd' ? 'evenodd' : 'nonzero' };
}

// Parses an SVG string into polylines in SVG user units, with all transforms applied. Shapes that
// are invisible in the picture are skipped; <use> copies are drawn. The browser supplies styles and
// transforms; the outlines themselves are read from the path data, so even large files load fast.
// The result also lists, in paint order, which strokes belong to which shape and how that shape is
// filled (strokes.shapes: [{ from, to, fill, alpha, rule }]), for shading.
function svgToStrokes(svgText) {
  const root = parseSvgDoc(svgText).documentElement;

  // Off-screen host so computed styles and transforms work (needs a layout context). It is
  // see-through rather than visibility:hidden, so each shape's own visibility can still be read.
  const host = document.createElementNS(SVG_NS, 'svg');
  host.setAttribute('width', '1'); host.setAttribute('height', '1');
  host.style.cssText = 'position:absolute;left:-9999px;top:0;opacity:0;pointer-events:none';
  document.body.appendChild(host);
  try {
    const imported = document.importNode(root, true);
    imported.removeAttribute('viewBox');
    imported.querySelectorAll('script,foreignObject').forEach(e => e.remove());
    host.appendChild(imported);
    expandUses(imported);

    // Convert primitives in place (keeping their styles and transforms) into paths.
    const prims = Array.from(imported.querySelectorAll('line,polyline,polygon,rect,circle,ellipse'));
    for (const el of prims) {
      if (el.closest('defs,clipPath,mask,symbol,pattern,marker')) continue;
      const d = primitiveToD(el);
      const p = document.createElementNS(SVG_NS, 'path');
      p.setAttribute('d', d);
      for (const a of Array.from(el.attributes))
        if (!['d', 'x', 'y', 'width', 'height', 'rx', 'ry', 'cx', 'cy', 'r', 'x1', 'y1', 'x2', 'y2', 'points'].includes(a.name)) p.setAttribute(a.name, a.value);
      el.parentNode.replaceChild(p, el);
    }

    const paths = Array.from(imported.querySelectorAll('path'))
      .filter(p => !p.closest('defs,clipPath,mask,symbol,pattern,marker') && !shapeHidden(p, imported));

    // Transform of each shape into the drawing's own units (nested <svg> viewports included).
    const rootInv = (() => { try { const m = imported.getScreenCTM(); return m ? m.inverse() : null; } catch (e) { return null; } })();
    const matrixOf = p => {
      try { const s = p.getScreenCTM(); if (rootInv && s) return rootInv.multiply(s); } catch (e) { /* fall back */ }
      return p.getCTM();
    };

    // Curve detail: pieces of about 1/1000 of the whole drawing.
    let dim = 0;
    try { const bb = imported.getBBox(); dim = Math.max(bb.width, bb.height); } catch (e) { dim = 0; }
    if (!(dim > 0)) {
      const vb = (root.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
      dim = vb.length === 4 && vb[2] > 0 ? Math.max(vb[2], vb[3]) : 1000;
    }
    const step = dim / 1000;

    const strokes = [], shapes = [];
    for (const p of paths) {
      const m = matrixOf(p);
      if (!m) continue;
      const sc = Math.max(Math.hypot(m.a, m.b), Math.hypot(m.c, m.d)) || 1, from = strokes.length;
      for (const poly of pathDataToPolylines(p.getAttribute('d') || '', step / sc)) {
        const s = poly.map(q => ({ x: m.a * q.x + m.c * q.y + m.e, y: m.b * q.x + m.d * q.y + m.f }));
        if (s.every(q => Number.isFinite(q.x) && Number.isFinite(q.y))) strokes.push(s);
      }
      if (strokes.length > from) shapes.push({ from, to: strokes.length, ...svgPaint(p, imported) });
    }
    Object.defineProperty(strokes, 'shapes', { value: shapes, enumerable: false });
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
