// Runs every unit test file and summarises (run: node tests/unit/run_all.js, or npm test)
const { spawnSync } = require('child_process'), path = require('path');
let bad = 0;
for (const f of ['test_protocol.js', 'test_smart.js', 'test_drawing.js', 'test_placement.js']) {
  const r = spawnSync(process.execPath, [path.join(__dirname, f)], { encoding: 'utf8' });
  const out = (r.stdout || '') + (r.stderr || '');
  const pass = (out.match(/^PASS /gm) || []).length, fail = (out.match(/^FAIL /gm) || []).length;
  console.log(`${f.padEnd(20)} ${pass} passed${fail ? `, ${fail} FAILED` : ''}`);
  if (fail || r.status) { bad++; console.log(out); }
}
console.log(bad ? `\n${bad} file(s) with failures` : '\nall unit tests passed');
process.exit(bad ? 1 : 0);
