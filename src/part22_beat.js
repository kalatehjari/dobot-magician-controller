/* ===================== SMART: BEAT TRACKING (pure, unit-tested) ===================== */
// Offline: Ellis (2007) "Beat tracking by dynamic programming" — mel onset envelope, tempo from a
// perceptually weighted autocorrelation, then a DP search for beats that sit on onsets at a steady period.

function fftInPlace(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang), half = len >> 1;
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < half; k++) {
        const a = i + k, b = a + half;
        const br = re[b] * cr - im[b] * ci, bi = re[b] * ci + im[b] * cr;
        re[b] = re[a] - br; im[b] = im[a] - bi;
        re[a] += br; im[a] += bi;
        const ncr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = ncr;
      }
    }
  }
}

function melBank(nfft, sr, nMel, fMin = 30, fMax = sr / 2) {
  const mel = f => 2595 * Math.log10(1 + f / 700), inv = m => 700 * (10 ** (m / 2595) - 1);
  const m0 = mel(fMin), m1 = mel(fMax);
  const bins = Array.from({ length: nMel + 2 }, (_, i) => inv(m0 + (m1 - m0) * i / (nMel + 1)) * nfft / sr);
  const bank = [];
  for (let m = 1; m <= nMel; m++) {
    const l = bins[m - 1], c = bins[m], r = bins[m + 1], w = [];
    for (let k = Math.max(0, Math.floor(l)); k <= Math.min(nfft / 2, Math.ceil(r)); k++) {
      let v = 0;
      if (k >= l && k <= c) v = (k - l) / ((c - l) || 1);
      else if (k > c && k <= r) v = (r - k) / ((r - c) || 1);
      if (v > 0) w.push([k, v]);
    }
    bank.push(w);
  }
  return bank;
}

// Onset strength envelope (~86 frames/s). Returns {env, rate, offset} where frame f ≈ time f/rate + offset.
function onsetEnvelope(x, sr) {
  const factor = Math.max(1, Math.round(sr / 11025));
  const sr2 = sr / factor, n2 = Math.floor(x.length / factor);
  const y = new Float32Array(n2);
  for (let i = 0; i < n2; i++) { let s = 0; for (let k = 0; k < factor; k++) s += x[i * factor + k]; y[i] = s / factor; }
  const N = 512, hop = 128, nMel = 40;
  const win = Float64Array.from({ length: N }, (_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N));
  const bank = melBank(N, sr2, nMel);
  const frames = n2 >= N ? Math.floor((n2 - N) / hop) + 1 : 0;
  const raw = new Float64Array(frames);
  const re = new Float64Array(N), im = new Float64Array(N);
  let prev = new Float64Array(nMel), cur = new Float64Array(nMel);
  for (let f = 0; f < frames; f++) {
    for (let i = 0; i < N; i++) { re[i] = y[f * hop + i] * win[i]; im[i] = 0; }
    fftInPlace(re, im);
    for (let m = 0; m < nMel; m++) {
      let s = 0;
      for (const [k, w] of bank[m]) s += w * Math.hypot(re[k], im[k]);
      cur[m] = Math.max(-100, 20 * Math.log10(s + 1e-10));
    }
    if (f > 0) { let o = 0; for (let m = 0; m < nMel; m++) { const d = cur[m] - prev[m]; if (d > 0) o += d; } raw[f] = o; }
    const t = prev; prev = cur; cur = t;
  }
  const rate = sr2 / hop;
  // High-pass (remove slow trend: subtract a 1 s moving average), smooth (~20 ms), normalise by std.
  const w = Math.max(1, Math.round(rate)), env = new Float64Array(frames);
  let acc = 0;
  for (let i = 0; i < frames; i++) {
    acc += raw[i]; if (i >= w) acc -= raw[i - w];
    env[i] = Math.max(0, raw[i] - acc / Math.min(i + 1, w));
  }
  const sm = new Float64Array(frames);
  for (let i = 0; i < frames; i++) sm[i] = 0.25 * (env[i - 1] ?? env[i]) + 0.5 * env[i] + 0.25 * (env[i + 1] ?? env[i]);
  let mean = 0; for (const v of sm) mean += v; mean /= frames || 1;
  let sd = 0; for (const v of sm) sd += (v - mean) ** 2; sd = Math.sqrt(sd / (frames || 1)) || 1;
  for (let i = 0; i < frames; i++) sm[i] /= sd;
  return { env: sm, rate, offset: (N / 2) / sr2 };
}

// Tempo: autocorrelation weighted by a log-Gaussian around centreBpm (perceptual preference).
function estimateTempo(env, rate, opts = {}) {
  const minBpm = opts.minBpm ?? 60, maxBpm = opts.maxBpm ?? 200, centre = opts.centreBpm ?? 120, oct = opts.sigmaOct ?? 1.0;
  const minLag = Math.max(1, Math.floor(rate * 60 / maxBpm)), maxLag = Math.ceil(rate * 60 / minBpm);
  const n = env.length, sc = [];
  let best = -Infinity, bestI = -1;
  for (let lag = minLag; lag <= maxLag && lag < n - 1; lag++) {
    let s = 0;
    for (let i = lag; i < n; i++) s += env[i] * env[i - lag];
    s /= (n - lag);
    const bpm = 60 * rate / lag;
    const v = s * Math.exp(-0.5 * (Math.log2(bpm / centre) / oct) ** 2);
    sc.push(v);
    if (v > best) { best = v; bestI = sc.length - 1; }
  }
  if (bestI < 0) return { bpm: 0, period: 0, confidence: 0 };
  let lag = minLag + bestI;
  if (bestI > 0 && bestI < sc.length - 1) {          // parabolic peak refinement
    const a = sc[bestI - 1], b = sc[bestI], c = sc[bestI + 1], den = a - 2 * b + c;
    if (den < 0) lag += 0.5 * (a - c) / den;
  }
  const mean = sc.reduce((p, q) => p + q, 0) / sc.length;
  return { bpm: 60 * rate / lag, period: lag, confidence: mean > 0 ? best / mean : 0 };
}

// Ellis DP: C(t) = O(t) + max over τ in [t-2P, t-P/2] of { C(τ) − α·ln((t−τ)/P)² }.
function dpBeats(env, period, alpha = 400) {
  const n = env.length;
  if (!n || !(period > 0)) return [];
  const C = new Float64Array(n), P = new Int32Array(n).fill(-1);
  const lo = Math.max(1, Math.round(period / 2)), hi = Math.round(period * 2);
  const pen = new Float64Array(hi + 1);
  for (let d = 1; d <= hi; d++) pen[d] = -alpha * Math.log(d / period) ** 2;
  for (let t = 0; t < n; t++) {
    let best = -Infinity, arg = -1;
    for (let d = lo; d <= hi; d++) {
      const tau = t - d;
      if (tau < 0) break;
      const v = C[tau] + pen[d];
      if (v > best) { best = v; arg = tau; }
    }
    if (arg >= 0) { C[t] = env[t] + best; P[t] = arg; } else C[t] = env[t];
  }
  let end = n - 1, bv = -Infinity;
  for (let t = Math.max(0, n - Math.round(period)); t < n; t++) if (C[t] > bv) { bv = C[t]; end = t; }
  const beats = [];
  for (let t = end; t >= 0; t = P[t]) { beats.push(t); if (P[t] < 0) break; }
  return beats.reverse();
}

// Full analysis of a decoded song (mono samples). Returns beat times (s), bpm, per-beat energy 0..1,
// and which beat starts a bar (best of 4 phases by onset strength).
function analyzeAudio(x, sr, opts = {}) {
  const { env, rate, offset } = onsetEnvelope(x, sr);
  const tempo = estimateTempo(env, rate, { minBpm: opts.minBpm ?? 70, maxBpm: opts.maxBpm ?? 180 });
  const frames = dpBeats(env, tempo.period, opts.alpha ?? 400);
  const beats = frames.map(f => f / rate + offset);
  // RMS energy per beat, scaled by the track's 10th–95th percentile.
  const rms = beats.map((b, i) => {
    const a = Math.max(0, Math.floor(b * sr)), e = Math.min(x.length, Math.floor((beats[i + 1] ?? b + 60 / (tempo.bpm || 120)) * sr));
    let s = 0; for (let k = a; k < e; k++) s += x[k] * x[k];
    return Math.sqrt(s / Math.max(1, e - a));
  });
  // Loudness on a decibel scale: the loud parts of the song (95th percentile) = 1, 18 dB quieter = 0,
  // then smoothed over 4 beats so the energy follows sections, not single hits.
  const sorted = rms.slice().sort((p, q) => p - q);
  const hi = sorted[Math.min(sorted.length - 1, Math.floor(0.95 * (sorted.length - 1)))] || 1e-9;
  const raw = rms.map(v => clamp((20 * Math.log10((v + 1e-9) / hi) + 18) / 18, 0, 1));
  const energy = raw.map((_, i) => { let s = 0, n = 0; for (let k = i - 2; k <= i + 1; k++) if (k >= 0 && k < raw.length) { s += raw[k]; n++; } return s / n; });
  let barPhase = 0, bestS = -Infinity;
  for (let ph = 0; ph < 4; ph++) {
    let s = 0; for (let i = ph; i < frames.length; i += 4) s += env[frames[i]] || 0;
    if (s > bestS) { bestS = s; barPhase = ph; }
  }
  return { bpm: tempo.bpm, confidence: tempo.confidence, beats, energy, barPhase, env, rate, offset, duration: x.length / sr };
}

/* ---------- Live (microphone) tracker ---------- */
// Fed with analyser spectra at display rate. Every 0.5 s re-estimates tempo over the last 8 s and the
// beat phase (comb of the period aligned to recent onsets), then predicts upcoming beats.
class LiveBeatTracker {
  constructor(opts = {}) {
    this.history = opts.historySec ?? 8; this.rate = opts.rate ?? 60;
    this.env = []; this.times = []; this.prev = null;
    this.bpm = 0; this.lastBeat = null; this.confidence = 0;
    this.energy = 0; this.peak = 1e-4; this.lastEst = -1; this.pending = null;
  }
  push(specDb, t, rms, maxBin) {
    const nb = Math.min(specDb.length, maxBin ?? specDb.length);
    let flux = 0;
    if (this.prev) for (let k = 1; k < nb; k++) { const d = specDb[k] - this.prev[k]; if (d > 0 && specDb[k] > -100) flux += d * (k < nb / 4 ? 1.5 : 1); }
    this.prev = Float32Array.from(specDb.subarray ? specDb.subarray(0, nb) : specDb.slice(0, nb));
    this.env.push(flux); this.times.push(t);
    while (this.times.length && t - this.times[0] > this.history) { this.times.shift(); this.env.shift(); }
    this.peak = Math.max(rms, this.peak * 0.9995);
    this.energy = 0.92 * this.energy + 0.08 * clamp(rms / this.peak, 0, 1);
    if (t - this.lastEst >= 0.5 && t - this.times[0] > 4) { this.lastEst = t; this._estimate(t); }
  }
  _estimate(now) {
    const t0 = this.times[0], n = Math.floor((now - t0) * this.rate);
    if (n < this.rate * 3) return;
    const u = new Float64Array(n);
    for (let i = 0, j = 0; i < n; i++) {                 // resample onto a uniform grid
      const ti = t0 + i / this.rate;
      while (j < this.times.length - 2 && this.times[j + 1] < ti) j++;
      u[i] = this.env[j];
    }
    let mean = 0; for (const v of u) mean += v; mean /= n;
    let sd = 0; for (const v of u) sd += (v - mean) ** 2; sd = Math.sqrt(sd / n) || 1;
    for (let i = 0; i < n; i++) u[i] = Math.max(0, (u[i] - mean) / sd);
    const tp = estimateTempo(u, this.rate, { minBpm: 70, maxBpm: 180 });
    if (!(tp.bpm > 0)) return;
    const P = tp.period;
    let bestPh = 0, bestS = -Infinity;
    for (let ph = 0; ph < Math.ceil(P); ph++) {           // phase: comb aligned to the newest onsets
      let s = 0, w = 1;
      for (let k = 0; ; k++) { const idx = Math.round(n - 1 - ph - k * P); if (idx < 0) break; s += u[idx] * w; w *= 0.85; }
      if (s > bestS) { bestS = s; bestPh = ph; }
    }
    const beat = now - bestPh / this.rate;
    if (this.bpm && Math.abs(tp.bpm - this.bpm) / this.bpm < 0.08) this.bpm = 0.7 * this.bpm + 0.3 * tp.bpm;
    else if (this.pending && Math.abs(tp.bpm - this.pending) / this.pending < 0.08) { this.bpm = tp.bpm; this.pending = null; }
    else if (!this.bpm) this.bpm = tp.bpm;
    else this.pending = tp.bpm;
    this.lastBeat = beat;
    this.confidence = tp.confidence;
  }
  nextBeatAfter(t) {
    if (!this.bpm || this.lastBeat === null) return null;
    const P = 60 / this.bpm;
    let b = this.lastBeat;
    if (b > t) while (b - P > t) b -= P; else while (b <= t) b += P;
    return b;
  }
}
