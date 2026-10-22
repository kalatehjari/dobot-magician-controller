#!/usr/bin/env python3
"""Builds the single-file app: joins the scripts in src/ (in this order) into src/part7_shell.html and
writes magician-smart-controller.html at the repository root. No dependencies: python3 build.py"""
import collections, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / 'src'
ORDER = [
    'part0_alarms.js',
    'part1_protocol.js',
    'part2_geometry.js',
    'part31_kinematics.js',
    'part36_place.js',
    'part38_smooth.js',
    'part42_shade.js',
    'part44_fonts_data.js',
    'part45_text.js',
    'part32_trace.js',
    'part3_svg.js',
    'part4_ui_core.js',
    'part5_plotter_record.js',
    'part8_calibrate.js',
    'part33_autocal.js',
    'part20_smart_math.js',
    'part21_moves.js',
    'part22_beat.js',
    'part23_vision.js',
    'part24_motion.js',
    'part25_dance.js',
    'part26_imitate.js',
    'part27_react.js',
    'part6_wiring.js',
    'part28_smart_wiring.js',
    'part30_selftest.js',
    'part34_plot_ui.js',
    'part37_place_ui.js',
    'part39_smooth_ui.js',
    'part40_library_data.js',
    'part41_library_ui.js',
    'part43_shade_ui.js',
    'part46_objects_ui.js',
    'part47_text_ui.js',
    'part48_clipper.js',
    'part49_slicer.js',
    'part50_printer.js',
    'part51_print_view.js',
    'part52_print_ui.js',
]

# every part shares one global scope: a name declared at the top level of two parts silently replaces the first
tops = collections.defaultdict(list)
for name in ORDER:
    for m in re.finditer(r'^(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)|^(?:const|let|var|class)\s+([A-Za-z_$][\w$]*)',
                         (SRC / name).read_text(encoding='utf-8'), re.M):
        tops[m.group(1) or m.group(2)].append(name)
clash = {k: v for k, v in tops.items() if len(v) > 1}
if clash:
    raise SystemExit(f'names declared in more than one part: {clash}')

js = '\n'.join((SRC / name).read_text(encoding='utf-8') for name in ORDER)
shell = (SRC / 'part7_shell.html').read_text(encoding='utf-8')
assert shell.count('<script>\n</script>') == 1, 'the shell must contain exactly one empty <script> block'
html = shell.replace('<script>\n</script>', '<script>\n' + js + '\n</script>')
out = ROOT / 'magician-smart-controller.html'
out.write_text(html, encoding='utf-8', newline='\n')

# sanity checks: every element the script looks up exists, and no id is used twice
ids = re.findall(r'id="([^"]+)"', html)
dups = [k for k, v in collections.Counter(ids).items() if v > 1]
refs = set(re.findall(r"(?:getElementById|\$id|\$pl)\('([^']+)'\)", js))
# ps-… inputs of the print settings are made by p3BuildForm (part 52), so they are not in the shell
made = re.compile(r'ps-(?!(?:support|pattern|seam|vase|fan|startCode|endCode|main|speed|ext|plate)$)\w+')
missing = sorted(r for r in refs if r not in set(ids) and not made.fullmatch(r))
print(f'built {out.name}: {len(html.encode())} bytes; duplicate ids: {dups or "none"}; missing ids: {missing or "none"}')
if dups or missing:
    raise SystemExit(1)
