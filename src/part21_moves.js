/* ===================== SMART: DANCE MOVES, CHOREOGRAPHY, REACTIONS (pure, unit-tested) ===================== */

// Small seeded random generator so a choreography can be replayed exactly.
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Each move: length in beats, keyframes per beat (steps), and f(p) → [dx, dy, dz, dr] in units of the
// amplitude. p is the position inside the move in beats. Axes: x = away from base, y = robot left, z = up.
const DANCE_MOVES = {
  sway:     { label: 'Sway', tiers: ['low', 'mid'], beats: 2, steps: 1, f: p => [0, p < 1 ? 1 : -1, 0, 0] },
  nod:      { label: 'Nod', tiers: ['low'], beats: 1, steps: 2, f: p => (p % 1) < 0.5 ? [0.4, 0, -0.7, 0] : [0, 0, 0, 0] },
  wave:     { label: 'Wave', tiers: ['low', 'mid'], beats: 2, steps: 4, f: p => [0.1, Math.cos(Math.PI * p), Math.abs(Math.sin(2 * Math.PI * p)) * 0.6 - 0.2, 0] },
  circle:   { label: 'Circle', tiers: ['low', 'mid'], beats: 2, steps: 4, f: p => [0, Math.sin(Math.PI * p), Math.cos(Math.PI * p) * 0.8, 0] },
  bounce:   { label: 'Bounce', tiers: ['mid'], beats: 1, steps: 2, f: p => (p % 1) < 0.5 ? [0, 0, -1, 0] : [0, 0, 0.35, 0] },
  figure8:  { label: 'Figure 8', tiers: ['mid'], beats: 4, steps: 4, f: p => { const a = Math.PI * p / 2; return [0, Math.sin(a), Math.sin(2 * a) * 0.6, 0]; } },
  twist:    { label: 'Twist', tiers: ['mid'], beats: 2, steps: 2, f: p => { const s = Math.floor(p * 2) % 2 ? -1 : 1; return [0, 0.4 * s, 0, s]; } },
  shimmy:   { label: 'Shimmy', tiers: ['mid', 'high'], beats: 1, steps: 4, f: p => [0, Math.floor(p * 4) % 2 ? -0.35 : 0.35, 0.1, 0] },
  robot:    { label: 'Robot', tiers: ['high'], beats: 4, steps: 1, f: p => [[0, 1, 0], [0, 1, 1], [0, -1, 1], [0, -1, 0]][Math.floor(p) % 4].concat(0) },
  pump:     { label: 'Pump', tiers: ['high'], beats: 1, steps: 2, f: p => (p % 1) < 0.5 ? [1, 0, 0.2, 0] : [-0.2, 0, 0, 0] },
  disco:    { label: 'Disco point', tiers: ['high'], beats: 2, steps: 1, f: p => p < 1 ? [0.5, -1, 1, 0] : [0, 1, -0.6, 0] },
  headbang: { label: 'Head bang', tiers: ['high'], beats: 1, steps: 2, f: p => (p % 1) < 0.5 ? [0.6, 0, -1, 0] : [-0.2, 0, 0.6, 0] },
  spin:     { label: 'Side sweep', tiers: ['mid', 'high'], beats: 4, steps: 2, f: p => { const a = Math.sin(Math.PI * p / 2); return [-0.3 * Math.abs(a), 1.6 * a, 0.2, 0]; } },
  freeze:   { label: 'Freeze', tiers: [], beats: 2, steps: 1, f: () => [0, 0, 0.5, 0] },
};

class Choreographer {
  constructor(opts = {}) {
    this.rand = mulberry32(opts.seed ?? 7);
    this.enabled = (opts.moves || Object.keys(DANCE_MOVES)).filter(m => DANCE_MOVES[m]);
    this.segBeats = opts.segBeats ?? 8;      // two bars of 4/4
    this.last = null; this.current = null; this.segStart = 0;
  }
  pickMove(energy) {
    if (energy < 0.08) return 'freeze';
    const tier = energy < 0.33 ? 'low' : energy < 0.66 ? 'mid' : 'high';
    let pool = this.enabled.filter(m => m !== 'freeze' && DANCE_MOVES[m].tiers.includes(tier));
    if (!pool.length) pool = this.enabled.filter(m => m !== 'freeze');
    if (!pool.length) pool = ['sway'];
    let pick = pool[Math.floor(this.rand() * pool.length)];
    if (pool.length > 1 && pick === this.last) pick = pool[(pool.indexOf(pick) + 1) % pool.length];
    this.last = pick;
    return pick;
  }
  // Keyframes for one beat: [{t, o:[dx,dy,dz,dr], move}], t in the same clock as tStart.
  beatFrames(beatIdx, tStart, dur, energy) {
    if (this.current === null || beatIdx < this.segStart || beatIdx - this.segStart >= this.segBeats) {
      this.current = this.pickMove(energy);
      this.segStart = beatIdx;
    }
    const mv = DANCE_MOVES[this.current];
    const local = (beatIdx - this.segStart) % mv.beats;
    const out = [];
    for (let k = 0; k < mv.steps; k++) {
      out.push({ t: tStart + dur * k / mv.steps, o: mv.f(local + k / mv.steps), move: this.current });
    }
    return out;
  }
  // Whole song: beat times (s) and per-beat energy (0..1) → keyframes.
  timeline(beats, energies) {
    const frames = [];
    for (let i = 0; i < beats.length; i++) {
      const dur = i + 1 < beats.length ? beats[i + 1] - beats[i] : (i > 0 ? beats[i] - beats[i - 1] : 0.5);
      frames.push(...this.beatFrames(i, beats[i], dur, energies[i] ?? 0.5));
    }
    return frames;
  }
}

// Converts a keyframe offset into an absolute target around the dance centre.
function danceTarget(o, C, amp) {
  return { x: C.x + o[0] * amp, y: C.y + o[1] * amp, z: C.z + o[2] * amp * 0.8, r: (o[3] || 0) * 25 };
}

// Reactions: [dx, dy, dz, dr, waitMs] in units of the amplitude, played around the current position.
function heartFrames(n = 16) {
  const out = [];
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * 2 * Math.PI;
    const hx = 16 * Math.sin(t) ** 3;
    const hy = 13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t);
    out.push([0, (hx / 17) * 1.2, (hy / 17) * 1.2, 0, 110]);
  }
  out.push([0, 0, 0, 0, 250]);
  return out;
}

const REACTIONS = {
  happy:     { label: 'Happy wiggle', frames: [[0, 0.6, 0.3, 0, 140], [0, -0.6, 0.3, 0, 140], [0, 0.6, 0.3, 0, 140], [0, -0.6, 0.3, 0, 140], [0, 0, 0.6, 0, 180], [0, 0, 0, 0, 250]] },
  surprised: { label: 'Startle', frames: [[-1.2, 0, 0.8, 0, 180], [-1.2, 0, 0.8, 0, 500], [0, 0, 0, 0, 600]] },
  sad:       { label: 'Droop', frames: [[0.3, 0, -0.9, 0, 700], [0.3, 0, -0.9, 0, 900], [0, 0, 0, 0, 900]] },
  angry:     { label: 'Back away', frames: [[-1.2, 0, -0.2, 0, 300], [-1.2, 0.15, -0.2, 0, 90], [-1.2, -0.15, -0.2, 0, 90], [-1.2, 0.15, -0.2, 0, 90], [-1.2, 0, -0.2, 0, 600], [0, 0, 0, 0, 700]] },
  kiss:      { label: 'Lean in', frames: [[1, 0, 0.3, 0, 350], [1, 0, 0.3, 0, 300], [0, 0, 0, 0, 450]] },
  wink:      { label: 'Wink back', frames: [[0, 0.5, -0.4, 1, 200], [0, 0, 0, 0, 250]] },
  nod:       { label: 'Nod yes', frames: [[0.3, 0, -0.6, 0, 160], [0, 0, 0.2, 0, 160], [0.3, 0, -0.6, 0, 160], [0, 0, 0, 0, 220]] },
  shake:     { label: 'Shake no', frames: [[0, 0.6, 0, 0, 150], [0, -0.6, 0, 0, 150], [0, 0.6, 0, 0, 150], [0, -0.6, 0, 0, 150], [0, 0, 0, 0, 200]] },
  greet:     { label: 'Hello bow', frames: [[0.6, 0, -0.6, 0, 350], [0, 0, 0.3, 0, 350], [0, 0, 0, 0, 250]] },
  celebrate: { label: 'Celebrate', frames: [[0, 0, -0.8, 0, 130], [0, 0, 0.5, 0, 130], [0, 0, -0.8, 0, 130], [0, 0, 0.5, 0, 130], [0, 0.8, 0.8, 0, 160], [0, 0, 1, 0, 160], [0, -0.8, 0.8, 0, 160], [0, 0, 0, 0, 250]] },
  sulk:      { label: 'Sulk', frames: [[-0.4, 0, -1, 0, 900], [-0.4, 0.2, -1, 0, 500], [0, 0, 0, 0, 900]] },
  wave:      { label: 'Wave hello', frames: [[0, 0, 1, 0, 200], [0, 0.7, 1, 0, 160], [0, -0.7, 1, 0, 160], [0, 0.7, 1, 0, 160], [0, -0.7, 1, 0, 160], [0, 0, 0, 0, 300]] },
  heart:     { label: 'Draw a heart', frames: heartFrames() },
  fistbump:  { label: 'Fist bump', frames: [[1.3, 0, 0, 0, 220], [1.3, 0, 0, 0, 150], [0, 0, 0, 0, 350]] },
  lookup:    { label: 'Look up', frames: [[0, 0, 1.3, 0, 300], [0, 0, 1.3, 0, 600], [0, 0, 0, 0, 400]] },
};

// Absolute frames for a reaction around centre C with amplitude amp (mm).
function reactionFrames(name, C, amp) {
  const r = REACTIONS[name];
  if (!r) return [];
  return r.frames.map(([dx, dy, dz, dr, wait]) => ({ x: C.x + dx * amp, y: C.y + dy * amp, z: C.z + dz * amp, r: dr * 20, wait }));
}
