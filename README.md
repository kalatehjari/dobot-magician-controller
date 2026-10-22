# Dobot Magician Controller

Control a **Dobot Magician** robot arm straight from your browser over USB — no Dobot software needed. Open one HTML file in Chrome or Edge, plug the arm in, and draw, write, move, record, dance and react.

![Placing a traced picture inside the arm's drawing zone](docs/placement.png)

## Features

- **Plotter**
  - Draws **SVG** files, or turns **pictures** (PNG, JPG, WEBP, GIF, BMP) into lines: outlines for shapes, single centre lines for line art and text, or edges for photos. Threshold, detail and curve smoothing are adjustable, and the lines can be downloaded as SVG.
  - **Free placement:** set the size in millimetres, turn the drawing to any angle, mirror it, and drag, resize or rotate it on the map. The **green zone** shows where the pen can reach at drawing height, and every line is kept inside it.
  - **Optimised path:** strokes are ordered to cut pen-up travel (nearest neighbour + 2-opt), joined where they touch and simplified. Pen-up hops that would cross the unreachable area near the base go around it.
  - **Drawing library:** 2 245 ready-made single-line drawings in 31 categories — animals, cars and sports cars, male and female poses, faces, flags (in colour), city skylines, songs as sheet music, constellations, zodiac, leaves, topography, aircraft, army, ants, sci-fi, clothing, shoes, signs, emojis, objects, technology, phones and electronics, music, art and more. Choose a category or search, click a drawing to add it to the paper, or download it as SVG. The same drawings come as a folder of SVG files with the release.
  - **Several objects on one sheet:** drawings, pictures and text each keep their own size, place, turn and shading. Copy, delete, choose which ones to draw, save and open layouts, and export the whole sheet as one SVG.
  - **Text:** 13 single-line fonts (Hershey and EMS) in up to four styles; letter height in millimetres, rotation, alignment, spacing, several lines and accented letters.
  - **Shading:** hatch lines inside closed shapes — lines, cross-hatch or three directions, at any angle and spacing in millimetres, a different angle per shape, closer lines for darker colours, and zig-zag joining so the pen lifts less. Click a shape on the map to give it its own shading.
  - **Hover round:** before drawing, the pen goes once round the outside of everything (a box or the outline) just above the paper, so you can check the paper is in the right place.
  - **Quiet, smooth motion:** the whole drawing runs as one continuous path with low, rounded pen hops instead of stopping at every lift. Choose Quiet & smooth, Balanced or Fast; a quiet-speed finder listens with the microphone and picks the quietest speeds. A precise stop-at-every-point mode, pause and resume, and a 20 mm test square are there too.
  - **Live view:** the pen shows as a red laser dot, and finished lines turn red as the arm draws them.
- **Mouse control** — click or drag on a map of the reach to move the arm; keyboard nudges; pen up/down, suction cup and gripper.
- **Record & learn** — record movements, average several takes into one smooth learned movement, and replay it.
- **Dance** — finds the beat in a song file, from the microphone or a metronome, and dances to it.
- **Imitate** — the arm mirrors your hand or arm through the webcam (following glides smoothly instead of jumping); draw in the air with a pinch; teach a movement by showing it.
- **Face & reactions** — reads expressions, winks, nods, head shakes and hand signs, reacts to them, and can follow your face.
- **Auto-calibration** — centres the arm, checks its joint readings against the Magician's geometry, measures the tool offset and works out the reachable area at every height. The only manual step is lowering the pen onto the paper.
- **Safety** — every target is kept inside the reachable space, alarms are shown and can be cleared, and **STOP** (or Esc) halts everything.
- **Simulator** — try every feature without hardware.

| Live drawing | Picture to lines |
| --- | --- |
| ![The pen as a red laser dot, finished lines in red](docs/live-drawing.png) | ![Tracing a line drawing into single lines](docs/picture-to-lines.png) |
| **Drawing library** | **Several objects and text** |
| ![The drawing library showing flags in colour](docs/drawing-library.png) | ![Two library drawings and a line of text on one sheet](docs/objects-and-text.png) |
| **Text tool** | **Shading** |
| ![Thirteen single-line fonts](docs/text-tool.png) | ![Shading settings: pattern, angle, spacing, angle per shape](docs/shading.png) |

## Quick start

1. Download `magician-smart-controller.html` from the [latest release](../../releases/latest) (or from this repository).
2. Open it in **Google Chrome** or **Microsoft Edge** on a desktop computer. Safari and Firefox do not support Web Serial.
3. Switch the Magician on and plug it in with USB. Click **Connect USB** and pick the arm's serial port.
4. The calibration dialog opens. Click **Start auto-calibration**, lower the pen onto the paper with the ▼ buttons, then click **This is the paper**.
5. Open **Plotter**, pick a drawing from the library, drop in an SVG or a picture, or type some text. Place it in the green zone, press **Hover round** to check the paper, and click **Draw**.

No arm at hand? Click **Simulator** instead of Connect USB.

If the arm does not appear in the port list, check the cable and that the arm is switched on; some computers also need a driver for the arm's USB-serial chip.

## Requirements

- A desktop browser with Web Serial: Chrome or Edge.
- For the camera features: a webcam and an internet connection the first time, to download the vision models (Google MediaPipe). Camera images are processed in the browser and are not uploaded.

## Safety

- Keep hands and objects clear of the arm. In the Dance, Imitate and Face tabs the arm moves by itself.
- **STOP** (or Esc) halts motion and clears the arm's command queue. If the arm's red light comes on, use the red bar to clear the alarm.
- The software limits help but are not a substitute for watching the arm.

## How it works

- **USB:** the page talks to the arm through the browser's Web Serial API at 115 200 baud, using the Magician's binary protocol: frames `AA AA len id ctrl params checksum`, commands queued in the arm's 32-slot buffer and paced by its queue index.
- **Commands used:** 10 pose · 20 alarms · 31 home · 80/81/83 speed · 84 point-to-point move · 90/91 continuous path · 62/63 suction and gripper · 240/241/245/246 queue start, pause, clear and index.
- **Geometry:** rear arm 135 mm, forearm 147 mm, with the Magician's joint limits. Auto-calibration confirms the joint conventions on your arm (two poses must agree within 2 mm) and measures the tool offset; the reachable area at each height follows from that.
- **Placement:** a drawing is placed by centre, size, angle and mirror. A fast check (convex hull for the outer edge and side limits, short line chunks for the inner edge) keeps it inside the zone while you drag, and finds the largest size that fits — one that also fits at every smaller size.
- **Smooth motion:** strokes are cut into short continuous-path moves and short gaps become rounded hops, so the arm's controller can look ahead instead of stopping; speed and acceleration are capped for every command.
- **Drawing library:** each drawing is stored on a 0–1000 grid as base-64 delta runs (about 3 MB for all 2 245). Sources: [Openclipart](https://openclipart.org) (public domain), [Tabler Icons](https://tabler.io/icons) (MIT), [d3-celestial](https://github.com/ofrohn/d3-celestial) star data (BSD 3-Clause), [flag-icons](https://github.com/lipis/flag-icons) (MIT), Hershey lettering, and drawings made by program for this project (`tools/library`). The app shows the credits and licence texts (Plotter → Drawing library → Credits and licences).
- **Text:** single-line Hershey and EMS fonts, encoded compactly (`tools/fonts`).
- **One file:** the app is a single self-contained HTML page built from the files in `src/`.

## Project layout

```
magician-smart-controller.html   the app (built; open this file)
build.py                         joins src/ into the app
src/                             source, one file per feature (build order in build.py)
tests/unit/                      Node.js tests, no dependencies
tests/e2e/                       browser tests (Playwright + the built-in simulator)
tools/library/                   how the drawing library was made (generators, export)
tools/fonts/                     how the single-line fonts were made
docs/                            screenshots
```

## Building and testing

```sh
python3 build.py                     # rebuilds magician-smart-controller.html from src/
node tests/unit/run_all.js           # unit tests (or: npm test)

pip install playwright && playwright install chromium
python3 tests/e2e/e2e_drawing.py     # calibration, tracing, smooth drawing, pause
python3 tests/e2e/e2e_placement.py   # placement, dragging, live pen and red lines
python3 tests/e2e/e2e_smooth.py      # motion profiles, continuous drawing, glide following
python3 tests/e2e/e2e_shade.py       # shading
python3 tests/e2e/e2e_objects.py     # several objects, text tool, layouts
python3 tests/e2e/e2e_library.py     # drawing library: every drawing loads and fits
```

`e2e_library.py` also compares the library folder with the app when the folder from the release is unpacked as `plotter-library/` at the repository root (or `MAGICIAN_LIBRARY` points at it).

The app also has a built-in self-test: **Setup → Test camera features**, or open the file with `?selftest=1`. It loads the vision models, checks the camera, the beat tracker, the picture tracer, the geometry model, placement, smooth motion, the drawing library, shading, text and several objects, all with the simulator so the arm does not move.

## Status

Version 1.4.0 (see the [changelog](CHANGELOG.md)). The app is tested with the built-in kinematic simulator (unit and browser tests) and with the self-test in Chrome on macOS. Testing on a physical arm is limited so far; auto-calibration checks the arm's joint conventions live and stops if they do not match. If something does not work with your arm, please open an issue.

## Acknowledgements

- Protocol details were cross-checked against the open-source `pydobot` library and Dobot's `DobotDllType.py`.
- Vision uses [Google MediaPipe](https://github.com/google-ai-edge/mediapipe) Tasks Vision (Apache-2.0), loaded at runtime.
- Drawing library: the Openclipart artists (credited in the app and in the library's `CREDITS.md`), Tabler Icons by Paweł Kuna, d3-celestial by Olaf Frohn, and the flag-icons contributors.
- Fonts: the Hershey fonts by Dr. A. V. Hershey (U.S. National Bureau of Standards), the EMS fonts by Sheldon B. Michaels (SIL Open Font License 1.1), and their SVG versions by Windell H. Oskay (Evil Mad Scientist, `hersheytext`).

## Licence

[MIT](LICENSE).

This project is not affiliated with or endorsed by Dobot. "Dobot" and "Magician" are trademarks of their respective owner.
