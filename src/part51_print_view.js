/* ===================== 3D PRINTING: PREVIEW (WebGL; falls back to a flat top view) ===================== */
// Shows the plate, the model before slicing, and after slicing every printed line coloured by kind, up to a chosen
// layer — in 3D (drag to turn, wheel to zoom) or as one layer seen from above. During a print the part already sent
// to the printer is drawn in colour and the rest in grey.

const P3_COLOURS = [[0.62, 0.65, 0.70], [0.86, 0.15, 0.15], [0.96, 0.62, 0.04], [0.15, 0.39, 0.92], [0.09, 0.64, 0.29], [0.58, 0.20, 0.92], [0.55, 0.37, 0.24]];
const m4 = {
  persp(fov, asp, n, f) { const t = 1 / Math.tan(fov / 2); return [t / asp, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) / (n - f), -1, 0, 0, 2 * f * n / (n - f), 0]; },
  ortho(l, r, b, t, n, f) { return [2 / (r - l), 0, 0, 0, 0, 2 / (t - b), 0, 0, 0, 0, -2 / (f - n), 0, -(r + l) / (r - l), -(t + b) / (t - b), -(f + n) / (f - n), 1]; },
  look(e, c, u) {
    const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    const nrm = a => { const L = Math.hypot(...a) || 1; return a.map(v => v / L); }, dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const z = nrm(sub(e, c)), x = nrm(cr(u, z)), y = cr(z, x);
    return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1];
  },
  mul(a, b) { const o = new Array(16); for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; },
};

class PrintView {
  constructor(cv) {
    this.cv = cv; this.mode = '3d'; this.az = -2.2; this.el = 0.55; this.zoom = 1; this.layer = -1; this.travel = false;
    this.plateD = 80; this.maxH = 150; this.mesh = null; this.path = null; this.progressSeg = -1; this.bad = false;
    try { this.gl = cv.getContext('webgl', { antialias: true, alpha: false }); } catch (e) { this.gl = null; }
    if (this.gl) this._initGL();
    this._bindInput();
  }
  _initGL() {
    const gl = this.gl;
    const prog = (vs, fs) => {
      const p = gl.createProgram();
      for (const [type, src] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
        const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        gl.attachShader(p, s);
      }
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
      return p;
    };
    this.pMesh = prog(
      'attribute vec3 aP; attribute vec3 aN; uniform mat4 uM; varying vec3 vN; void main(){ vN = aN; gl_Position = uM * vec4(aP, 1.0); }',
      'precision mediump float; varying vec3 vN; uniform vec3 uC; uniform float uA; void main(){ vec3 n = normalize(vN); float d = 0.35 + 0.5 * max(dot(n, normalize(vec3(0.4, -0.5, 0.8))), 0.0) + 0.15 * max(dot(n, normalize(vec3(-0.6, 0.7, 0.3))), 0.0); gl_FragColor = vec4(uC * d, uA); }');
    this.pLine = prog(
      'attribute vec3 aP; attribute float aT; uniform mat4 uM; uniform vec3 uCol[7]; uniform float uDim; uniform float uTravel; uniform float uGrey; uniform vec3 uBg; uniform float uFade; varying vec4 vC;' +
      'void main(){ int t = int(aT + 0.5); vec3 c = uCol[0]; for (int k = 1; k < 7; k++) if (k == t) c = uCol[k];' +
      ' float a = (t == 0) ? uTravel : 1.0; c = mix(mix(c, vec3(0.72), uGrey) * uDim, uBg, uFade); vC = vec4(c, a); gl_Position = uM * vec4(aP, 1.0); }',
      'precision mediump float; varying vec4 vC; void main(){ if (vC.a < 0.5) discard; gl_FragColor = vec4(vC.rgb, 1.0); }');
    this.pFlat = prog('attribute vec3 aP; uniform mat4 uM; void main(){ gl_Position = uM * vec4(aP, 1.0); }',
      'precision mediump float; uniform vec4 uC; void main(){ gl_FragColor = uC; }');
    this.bPlate = gl.createBuffer(); this.bRim = gl.createBuffer(); this.bGrid = gl.createBuffer();
    this._plateGeom();
  }
  _plateGeom() {
    if (!this.gl) return;
    const gl = this.gl, R = this.plateD / 2, disc = [0, 0, -0.02], rim = [], grid = [];
    for (let k = 0; k <= 96; k++) { const a = 2 * Math.PI * k / 96; disc.push(R * Math.cos(a), R * Math.sin(a), -0.02); }
    for (let k = 0; k < 96; k++) { const a = 2 * Math.PI * k / 96, b = 2 * Math.PI * (k + 1) / 96; rim.push(R * Math.cos(a), R * Math.sin(a), 0, R * Math.cos(b), R * Math.sin(b), 0); }
    for (let g = -Math.floor(R / 10) * 10; g <= R; g += 10) { const h = Math.sqrt(Math.max(0, R * R - g * g)); grid.push(g, -h, -0.01, g, h, -0.01, -h, g, -0.01, h, g, -0.01); }
    gl.bindBuffer(gl.ARRAY_BUFFER, this.bPlate); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(disc), gl.STATIC_DRAW); this.nPlate = disc.length / 3;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.bRim); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(rim), gl.STATIC_DRAW); this.nRim = rim.length / 3;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.bGrid); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(grid), gl.STATIC_DRAW); this.nGrid = grid.length / 3;
  }
  setPlate(d, h) { if (d !== this.plateD || h !== this.maxH) { this.plateD = d; this.maxH = h; this._plateGeom(); } }
  // placed: meshPlace() result; bad: shown red (does not fit)
  setMesh(placed, bad, insideOut) {
    this.mesh = placed; this.bad = !!bad;
    if (!this.gl || !placed) return;
    const gl = this.gl, { pos, idx } = placed, T = idx.length / 3, out = new Float32Array(T * 18), sg = insideOut ? -1 : 1;
    for (let t = 0; t < T; t++) {
      const a = idx[3 * t], b = idx[3 * t + 1], c = idx[3 * t + 2], n = triNormal(pos, a, b, c);
      [a, b, c].forEach((v, k) => { const o = 18 * t + 6 * k; out[o] = pos[3 * v]; out[o + 1] = pos[3 * v + 1]; out[o + 2] = pos[3 * v + 2]; out[o + 3] = sg * n[0]; out[o + 4] = sg * n[1]; out[o + 5] = sg * n[2]; });
    }
    if (!this.bMesh) this.bMesh = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.bMesh); gl.bufferData(gl.ARRAY_BUFFER, out, gl.STATIC_DRAW); this.nMesh = T * 3;
  }
  // result: slicer output, or null
  setPath(result) {
    this.path = result; this.progressSeg = -1;
    if (!this.gl || !result) return;
    const gl = this.gl, pv = result.preview, n = pv.type.length, ty = new Uint8Array(2 * n);
    for (let j = 0; j < n; j++) ty[2 * j] = ty[2 * j + 1] = pv.type[j];
    if (!this.bPath) { this.bPath = gl.createBuffer(); this.bType = gl.createBuffer(); }
    gl.bindBuffer(gl.ARRAY_BUFFER, this.bPath); gl.bufferData(gl.ARRAY_BUFFER, pv.pos, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.bType); gl.bufferData(gl.ARRAY_BUFFER, ty, gl.STATIC_DRAW);
    this.nSeg = n;
  }
  // how far the model reaches from the plate centre (the views frame the model, not only the plate)
  _reach() {
    const m = this.mesh;
    if (!m) return this.plateD / 2;
    return Math.max(8, Math.abs(m.min[0]), Math.abs(m.max[0]), Math.abs(m.min[1]), Math.abs(m.max[1]));
  }
  _matrix(W, H) {
    const R = this.plateD / 2, top = this.path ? this.path.stats.height : this.mesh ? this.mesh.max[2] : 20;
    if (this.mode === 'layer') {
      const s = Math.min(R + 4, this._reach() * 1.15 + 3) / this.zoom, a = W / H, cx = this.panX || 0, cy = this.panY || 0;
      const z = this.path && this.layer >= 0 ? this.path.layers[this.layer].z : top;
      return m4.mul(m4.ortho(cx - s * Math.max(1, a), cx + s * Math.max(1, a), cy - s * Math.max(1, 1 / a), cy + s * Math.max(1, 1 / a), -10, 400), m4.look([0, 0, z + 100], [0, 0, z], [0, 1, 0]));
    }
    const fit = Math.max(R * 0.75, this._reach()), tz = Math.min(top, 80) * 0.3, d = (fit * 3.3 + top * 0.9) / this.zoom;
    const eye = [d * Math.cos(this.el) * Math.cos(this.az), d * Math.cos(this.el) * Math.sin(this.az), tz + d * Math.sin(this.el)];
    return m4.mul(m4.persp(40 * Math.PI / 180, W / H, Math.max(1, d / 50), d * 4), m4.look(eye, [0, 0, tz], [0, 0, 1]));
  }
  draw() {
    const cv = this.cv, dpr = window.devicePixelRatio || 1, W = Math.max(1, cv.clientWidth), H = Math.max(1, cv.clientHeight);
    if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
    if (!this.gl) return this._draw2d(W, H, dpr);
    const gl = this.gl, M = this._matrix(W, H), css = getComputedStyle(document.documentElement);
    const dark = (css.getPropertyValue('--bg').trim() || '#fff').toLowerCase() < '#5';
    gl.viewport(0, 0, cv.width, cv.height);
    const bg = dark ? [0.09, 0.10, 0.13] : [0.97, 0.97, 0.98];
    gl.clearColor(bg[0], bg[1], bg[2], 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    // plate
    gl.useProgram(this.pFlat);
    const aPf = gl.getAttribLocation(this.pFlat, 'aP'), uMf = gl.getUniformLocation(this.pFlat, 'uM'), uCf = gl.getUniformLocation(this.pFlat, 'uC');
    gl.uniformMatrix4fv(uMf, false, M);
    const flat = (buf, n, mode, col) => { gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.enableVertexAttribArray(aPf); gl.vertexAttribPointer(aPf, 3, gl.FLOAT, false, 0, 0); gl.uniform4fv(uCf, col); gl.drawArrays(mode, 0, n); };
    flat(this.bPlate, this.nPlate, gl.TRIANGLE_FAN, dark ? [0.17, 0.19, 0.24, 1] : [0.88, 0.90, 0.93, 1]);
    flat(this.bGrid, this.nGrid, gl.LINES, dark ? [0.24, 0.27, 0.33, 1] : [0.80, 0.83, 0.87, 1]);
    flat(this.bRim, this.nRim, gl.LINES, dark ? [0.38, 0.65, 0.98, 1] : [0.15, 0.39, 0.92, 1]);
    gl.disableVertexAttribArray(aPf);
    const showPath = this.path && this.bPath;
    if (showPath) {
      gl.useProgram(this.pLine);
      const aP = gl.getAttribLocation(this.pLine, 'aP'), aT = gl.getAttribLocation(this.pLine, 'aT'), U = n => gl.getUniformLocation(this.pLine, n);
      gl.uniformMatrix4fv(U('uM'), false, M);
      gl.uniform3fv(U('uCol'), new Float32Array(P3_COLOURS.flat()));
      gl.uniform1f(U('uTravel'), this.travel ? 1 : 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.bPath); gl.enableVertexAttribArray(aP); gl.vertexAttribPointer(aP, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.bType); gl.enableVertexAttribArray(aT); gl.vertexAttribPointer(aT, 1, gl.UNSIGNED_BYTE, false, 0, 0);
      const L = this.path.layers, li = this.layer < 0 ? L.length - 1 : Math.min(this.layer, L.length - 1);
      gl.uniform3fv(U('uBg'), bg);
      const range = (a, b, dim, grey, fade = 0) => { if (b > a) { gl.uniform1f(U('uDim'), dim); gl.uniform1f(U('uGrey'), grey); gl.uniform1f(U('uFade'), fade); gl.drawArrays(gl.LINES, 2 * a, 2 * (b - a)); } };
      const end = L[li].seg1, cur0 = L[li].seg0, p = this.progressSeg;
      if (this.mode === 'layer') {
        if (li > 0) range(L[li - 1].seg0, L[li - 1].seg1, 1, 0.3, 0.72);
        if (p >= 0) { range(cur0, Math.min(end, Math.max(cur0, p)), 1, 0); range(Math.max(cur0, p), end, 0.9, 0.85); }
        else range(cur0, end, 1, 0);
      } else if (p >= 0) {
        // printing: what has been sent in colour, the rest of the print in light grey above it
        const all = this.nSeg;
        range(0, Math.min(p, all), 0.85, 0); range(Math.min(p, all), all, 1, 0.9, 0.35);
      } else { range(0, cur0, 0.78, 0); range(cur0, end, 1, 0); }
      gl.disableVertexAttribArray(aP); gl.disableVertexAttribArray(aT);
    } else if (this.mesh && this.bMesh) {
      gl.useProgram(this.pMesh);
      const aP = gl.getAttribLocation(this.pMesh, 'aP'), aN = gl.getAttribLocation(this.pMesh, 'aN');
      gl.uniformMatrix4fv(gl.getUniformLocation(this.pMesh, 'uM'), false, M);
      gl.uniform3fv(gl.getUniformLocation(this.pMesh, 'uC'), this.bad ? [0.92, 0.30, 0.28] : [0.45, 0.62, 0.92]);
      gl.uniform1f(gl.getUniformLocation(this.pMesh, 'uA'), 1);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.bMesh);
      gl.enableVertexAttribArray(aP); gl.vertexAttribPointer(aP, 3, gl.FLOAT, false, 24, 0);
      gl.enableVertexAttribArray(aN); gl.vertexAttribPointer(aN, 3, gl.FLOAT, false, 24, 12);
      gl.drawArrays(gl.TRIANGLES, 0, this.nMesh);
      gl.disableVertexAttribArray(aP); gl.disableVertexAttribArray(aN);
    }
  }
  // No WebGL: a flat view from above with canvas 2D
  _draw2d(W, H, dpr) {
    const ctx = this.cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    const R = this.plateD / 2, k = Math.min(W, H) / (2 * R + 12) * this.zoom, cx = W / 2, cy = H / 2, X = x => cx + x * k, Y = y => cy - y * k;
    ctx.strokeStyle = cssVar('--accent'); ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, R * k, 0, 2 * Math.PI); ctx.stroke();
    if (this.path) {
      const L = this.path.layers, li = this.layer < 0 ? L.length - 1 : Math.min(this.layer, L.length - 1), pv = this.path.preview;
      for (let j = L[li].seg0; j < L[li].seg1; j++) {
        const t = pv.type[j]; if (!t && !this.travel) continue;
        const c = P3_COLOURS[t]; ctx.strokeStyle = `rgb(${c.map(v => Math.round(v * 255)).join(',')})`; ctx.lineWidth = t ? 1.2 : 0.5;
        ctx.beginPath(); ctx.moveTo(X(pv.pos[6 * j]), Y(pv.pos[6 * j + 1])); ctx.lineTo(X(pv.pos[6 * j + 3]), Y(pv.pos[6 * j + 4])); ctx.stroke();
      }
    } else if (this.mesh) {
      const P = this.mesh.pos, hull = [];
      for (let i = 0; i < P.length; i += 3) hull.push(P[i], P[i + 1]);
      const h = hullXY(hull);
      ctx.fillStyle = this.bad ? 'rgba(220,38,38,.35)' : 'rgba(37,99,235,.3)'; ctx.beginPath();
      for (let i = 0; i < h.length; i += 2) (i ? ctx.lineTo : ctx.moveTo).call(ctx, X(h[i]), Y(h[i + 1]));
      ctx.closePath(); ctx.fill();
    }
  }
  _bindInput() {
    const cv = this.cv;
    let drag = null;
    cv.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY, az: this.az, el: this.el, px: this.panX || 0, py: this.panY || 0 }; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove', e => {
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (this.mode === 'layer') { const s = Math.min(this.plateD / 2 + 4, this._reach() * 1.15 + 3) / this.zoom * 2 / Math.max(1, Math.min(cv.clientWidth, cv.clientHeight)); this.panX = drag.px - dx * s; this.panY = drag.py + dy * s; }
      else { this.az = drag.az - dx * 0.01; this.el = Math.max(-0.2, Math.min(1.5, drag.el + dy * 0.01)); }
      this.draw();
    });
    cv.addEventListener('pointerup', () => { drag = null; });
    cv.addEventListener('wheel', e => { e.preventDefault(); this.zoom = Math.max(0.4, Math.min(12, this.zoom * Math.exp(-e.deltaY * 0.0015))); this.draw(); }, { passive: false });
    cv.addEventListener('dblclick', () => { this.az = -2.2; this.el = 0.55; this.zoom = 1; this.panX = this.panY = 0; this.draw(); });
  }
}
