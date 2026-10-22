/* ===================== DRAWING LIBRARY (Plotter tab) =====================
   Ready-made single-line drawings in categories (LIBRARY, from part40_library_data.js). Picking one adds it
   to the paper exactly like an SVG file would, so sizing, placement, shading and drawing work the same.
   Thumbnails are drawn only when they scroll into view. */
const LIB = { cat: 'all', query: '', current: null, built: false, obs: null, cache: new Map(), byId: new Map() };
const LIB_B64 = (() => { const m = new Int8Array(128).fill(-1), s = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'; for (let i = 0; i < 64; i++) m[s.charCodeAt(i)] = i; return m; })();
for (const e of LIBRARY) LIB.byId.set(e.i, e);

// The drawing's lines: [[x, y, x, y, …], …] on its 0–1000 grid.
function libLines(e) {
  let L = LIB.cache.get(e.i);
  if (L) return L;
  const s = e.p, out = [];
  let i = 0, x = 0, y = 0;
  const vint = () => { let v = 0, sh = 0, d; do { d = LIB_B64[s.charCodeAt(i++)]; v += (d & 31) * 2 ** sh; sh += 5; } while (d & 32); return v; };
  const zz = v => (v % 2 ? -(v + 1) / 2 : v / 2);
  while (i < s.length) {
    const n = vint(), a = new Array(2 * n);
    for (let k = 0; k < n; k++) { x += zz(vint()); y += zz(vint()); a[2 * k] = x; a[2 * k + 1] = y; }
    out.push(a);
  }
  if (LIB.cache.size > 400) LIB.cache.delete(LIB.cache.keys().next().value);
  LIB.cache.set(e.i, out);
  return out;
}
function libPathD(lines) {
  let d = '';
  for (const a of lines) { d += 'M' + a[0] + ' ' + a[1]; for (let k = 2; k < a.length; k += 2) d += 'L' + a[k] + ' ' + a[k + 1]; }
  return d;
}
const libSource = e => LIBRARY_SOURCES[e.s] || LIBRARY_SOURCES[0];
const libAuthor = e => e.a || libSource(e).author || '';
const libCatName = k => (LIBRARY_CATS.find(c => c[0] === k) || [k, k])[1];

// The drawing as a standalone SVG file (100 mm on its longest side, 0.35 mm lines). Flags keep their colours.
function libSvg(e) {
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const p = 4, w = e.w + 2 * p, h = e.h + 2 * p, L = libLines(e), src = libSource(e), by = libAuthor(e);
  let body = '';
  if (e.f) {
    const used = new Set();
    for (const [col, a, b] of e.f) {
      for (let k = a; k < b; k++) used.add(k);
      body += `  <path d="${libPathD(L.slice(a, b))}" fill="${esc(col)}" fill-rule="evenodd" stroke="#000" stroke-width="3.5" stroke-linejoin="round"/>\n`;
    }
    const rest = L.filter((_, k) => !used.has(k));
    if (rest.length) body += `  <path d="${libPathD(rest)}" fill="none" stroke="#000" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>\n`;
  } else body = `  <path d="${libPathD(L)}" fill="none" stroke="#000" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>\n`;
  return `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="${w / 10}mm" height="${h / 10}mm" viewBox="${-p} ${-p} ${w} ${h}">\n` +
    `  <title>${esc(e.n)}</title>\n  <desc>Single-line drawing for pen plotters: ${esc(e.n)}${by ? ' by ' + esc(by) : ''} (${esc(src.name)}, ${esc(src.license)}).</desc>\n` + body + '</svg>\n';
}

function libMatches(e) {
  if (LIB.cat !== 'all' && e.c !== LIB.cat) return false;
  const q = LIB.query.trim().toLowerCase();
  if (!q) return true;
  const hay = `${e.n} ${libCatName(e.c)} ${libAuthor(e)} ${libSource(e).name}`.toLowerCase();
  return q.split(/\s+/).every(w => hay.includes(w));
}

function libThumb(b) {
  if (b.dataset.drawn) return;
  const e = LIB.byId.get(b.dataset.id);
  if (!e) return;
  b.dataset.drawn = '1';
  const L = libLines(e), t = `translate(${(1000 - e.w) / 2} ${(1000 - e.h) / 2})`;
  let fills = '';   // flags keep their colours in the grid too
  if (e.f) for (const [col, a, z] of e.f) if (/^#[0-9a-f]{3,8}$/i.test(col)) fills += `<path transform="${t}" style="fill:${col};fill-rule:evenodd;stroke:none" d="${libPathD(L.slice(a, z))}"/>`;
  b.querySelector('svg').innerHTML = fills + `<path transform="${t}" d="${libPathD(L)}"/>`;
}

function libEnsureGrid() {
  if (LIB.built) return;
  LIB.built = true;
  const sel = document.getElementById('lib-cat'), count = new Map();
  for (const e of LIBRARY) count.set(e.c, (count.get(e.c) || 0) + 1);
  const add = (v, t) => { const o = document.createElement('option'); o.value = v; o.textContent = t; sel.appendChild(o); };
  add('all', `All categories (${LIBRARY.length})`);
  for (const [k, name] of LIBRARY_CATS) if (count.get(k)) add(k, `${name} (${count.get(k)})`);
  sel.value = LIB.cat;
  const grid = document.getElementById('lib-grid'), frag = document.createDocumentFragment();
  LIB.obs = 'IntersectionObserver' in window ? new IntersectionObserver(es => { for (const x of es) if (x.isIntersecting) { libThumb(x.target); LIB.obs.unobserve(x.target); } }, { root: grid, rootMargin: '200px' }) : null;
  for (const e of LIBRARY) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'lib-item'; b.dataset.id = e.i;
    const by = libAuthor(e);
    b.title = `${e.n} — ${libCatName(e.c)}${by ? ', by ' + by : ''} (${libSource(e).name}). About ${(e.m / 1000).toFixed(1)} m of pen line at 100 mm.`;
    b.innerHTML = '<svg viewBox="-40 -40 1080 1080" aria-hidden="true"></svg><span></span>';
    b.querySelector('span').textContent = e.n;
    b.onclick = () => libLoad(e.i);
    frag.appendChild(b);
  }
  grid.appendChild(frag);
  libFilter();
}

function libFilter() {
  let n = 0;
  const grid = document.getElementById('lib-grid');
  for (const b of grid.children) {
    const show = libMatches(LIB.byId.get(b.dataset.id));
    b.hidden = !show;
    if (show) {
      n++;
      if (!b.dataset.drawn) { if (LIB.obs) LIB.obs.observe(b); else libThumb(b); }
    } else if (LIB.obs) LIB.obs.unobserve(b);
  }
  document.getElementById('lib-none').hidden = n > 0;
  const total = LIB.cat === 'all' ? LIBRARY.length : LIBRARY.filter(e => e.c === LIB.cat).length;
  document.getElementById('lib-count').textContent = n === total ? `${n} drawings` : `${n} of ${total} drawings`;
  grid.scrollTop = 0;
}

function libMark(id) {
  LIB.current = id;
  document.querySelectorAll('#lib-grid .lib-item.sel').forEach(b => { b.classList.remove('sel'); b.setAttribute('aria-pressed', 'false'); });
  if (id) {
    const b = document.querySelector(`#lib-grid .lib-item[data-id="${CSS.escape(id)}"]`);
    if (b) { b.classList.add('sel'); b.setAttribute('aria-pressed', 'true'); }
  }
  document.getElementById('btnLibSave').disabled = !id;
}

// A click adds the drawing to the paper as a new object (clicking the drawing that is selected on the
// paper again keeps it where it is).
function libLoad(id) {
  const e = LIB.byId.get(id);
  if (!e) return;
  try {
    document.getElementById('traceCard').hidden = true;
    const raw = svgToStrokes(libSvg(e));
    if (!raw.length) throw new Error('empty drawing');
    setDrawing(raw, e.n, { source: 'library:' + e.i });
    libMark(id);
    const by = libAuthor(e), src = libSource(e);
    document.getElementById('plot-file-name').textContent = `Library: ${e.n}${by ? ' — by ' + by : ''} (${src.name}, ${src.license})`;
    log(`Library drawing: ${e.n}${by ? ' by ' + by : ''}, about ${(e.m / 1000).toFixed(1)} m of line at 100 mm.`, 'ok');
  } catch (err) {
    log('Could not load that drawing: ' + err.message, 'err');
  }
}

// The grid marks the library drawing that is selected on the paper.
function libSyncMark() {
  const o = selObj(), id = o && o.source && o.source.startsWith('library:') ? o.source.slice(8) : null;
  if (id !== LIB.current) libMark(id);
}

function libCredits() {
  const box = document.querySelector('#lib-credits .lib-credit-body');
  if (box.childElementCount) return;
  const add = (tag, text, cls) => { const el = document.createElement(tag); el.textContent = text; if (cls) el.className = cls; box.appendChild(el); return el; };
  LIBRARY_SOURCES.forEach((src, si) => {
    const items = LIBRARY.filter(e => e.s === si);
    if (!items.length) return;
    add('h4', `${src.name} — ${items.length} drawing${items.length > 1 ? 's' : ''} · ${src.license}`);
    if (src.note) add('p', src.note);
    if (src.url) add('p', src.url, 'muted');
    if (src.k === 'openclipart') {
      const byAuthor = new Map();
      for (const e of items) { const a = libAuthor(e) || 'Artist not recorded'; if (!byAuthor.has(a)) byAuthor.set(a, []); byAuthor.get(a).push(e.n); }
      const ul = document.createElement('ul'); ul.className = 'lib-credit-list';
      for (const [a, names] of [...byAuthor].sort((p, q) => q[1].length - p[1].length || p[0].localeCompare(q[0]))) {
        const li = document.createElement('li'); li.textContent = `${a}: ${names.join(', ')}`; ul.appendChild(li);
      }
      box.appendChild(ul);
    }
    if (src.notice) add('pre', src.notice, 'tx-lic');
  });
}

document.getElementById('lib-search').addEventListener('input', e => { LIB.query = e.target.value; libFilter(); });
document.getElementById('lib-cat').addEventListener('change', e => { LIB.cat = e.target.value; libFilter(); });
document.getElementById('btnLibSave').onclick = () => {
  const e = LIB.byId.get(LIB.current);
  if (e) downloadText(e.i.split('/')[1] + '.svg', libSvg(e), 'image/svg+xml');
};
document.getElementById('lib-credits').addEventListener('toggle', ev => { if (ev.target.open) libCredits(); });
if (document.getElementById('tab-plot').classList.contains('active')) libEnsureGrid();
