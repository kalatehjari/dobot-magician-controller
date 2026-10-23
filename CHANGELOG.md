# Changelog

## 1.6.0 — 2026-10-23

### Safe drawing zone
- **Draw safe zone:** click the corners of your paper (or any area) on the plotter map; click the first corner again or press Done to close it. Or pick a paper size (A6, A5, A4, A3, Letter), add a corner where the pen is now (move it there by hand or with Mouse control), drag corners to edit, undo, switch the zone off or remove it. It is kept in the browser. Crossing edges and tiny areas are refused.
- Nothing the pen does goes outside the zone: drawings are placed inside it (with the margin), Largest and dragging stop at its edge, and pen-up travel between lines, hover round and redraws go round inside it by the shortest way. Only centring (home) and calibration may leave it.

### Safety lock (next to Centre)
- Once the arm has been centred, the lock keeps every arm movement inside the allowed area — the green zone at paper height, inside the safe zone if there is one — and never more than 1 mm below the paper.
- Before a drawing, hover round, test square, replay or click-move starts, its whole path is checked. If it would leave the area, an alert says by how much and offers **Adjust it myself** (nothing moves) or **Trim to the boundary** (drawing lines keep only their parts inside and the pen lifts round the rest; other moves are pulled in to the boundary).
- Following (mouse drag, hand, arm, face, dance) holds at the boundary at the first breach and asks once: stop, or trim for the rest of the session. Keyboard nudges and the mouse wheel stop at the boundary.
- Underneath, every move sent to the arm is checked again and one that would leave is refused. A pill shows when the lock is trimming or holding; after reconnecting, the lock waits for the arm to be centred again.

### Paper height
- **Re-set pen height…** for a new sheet or paper at another height: lower the pen until it touches the paper, as in calibration; the rest of the calibration is kept.
- Save heights by name (a board, a notebook, card…) and switch between them with **Use**.

### Clear plotter and Redraw
- **Clear plotter** removes every drawing, picture and text from the paper and clears the red lines (Undo clear brings them back).
- **Redraw** draws again what has been drawn and is on the map — for duplicates and multiple copies (1–50). Between copies it can wait for a fresh sheet.

### Persian text
- A **Persian** switch in the Text tool: the text box writes right to left, and text is drawn in a new single-line Persian font made from Vazirmatn (SIL Open Font License), letter height = the height of alef.
- Letters take their isolated, initial, middle and final forms and join exactly; lam-alef is one letter; the half-space (zero-width non-joiner), zero-width joiner and tatweel work as in typing; vowel marks (fatha, kasra, damma, tanwin, shadda, sukun, hamza, superscript alef) sit over or under their letter.
- Lines run right to left with English words and numbers inside them left to right, and brackets mirrored (the Unicode bidirectional algorithm for a right-to-left paragraph, checked against a reference implementation on 2 000 random lines).
- **Persian digits** (on by default): 0–9 are drawn as ۰–۹, except inside English words such as MP3. Regular and bold; letter spacing keeps joined letters joined. Font credit and licence in Fonts and licences.

### Bluetooth and Wi-Fi (Dobot's Wireless 1 and Wireless 2 modules)
- ▾ next to **Connect USB** offers **Bluetooth (Wireless 1)** and **Wi-Fi (Wireless 2)…**, and Setup has a Wireless modules card; the connection pill shows the link in use.
- **Bluetooth (Wireless 1):** connects from Chrome or Edge with Web Bluetooth and sends the same commands as USB (service 0003CDD0-0000-1000-8000-00805F9B0131).
- **Wi-Fi (Wireless 2):** the module's network (name, password, automatic or fixed address) is sent once from Setup over USB, and its status can be read back. A web page cannot send the module's UDP messages, so a small bridge program (Python, no installs; download it from Setup) passes them on: start it, enter the arm's address and connect. Lost messages are asked for again.
- The Host module (USB host, for a gamepad or USB stick on the arm) works on the arm without a computer, so the app does not use it; Setup says so.

### Website
- The project has a website on GitHub Pages, https://kalatehjari.github.io/dobot-magician-controller/: a landing page (features, screenshots, getting started, 3D printing, safety, questions), and the app itself at [/app/](https://kalatehjari.github.io/dobot-magician-controller/app/) — the same file as the release download — so it can be used without downloading anything.
- Search engines: page title and description, canonical address, Open Graph and Twitter card with a social image, structured data (web application, source code, questions), a sitemap, a 404 page and an IndexNow key.
- `build.py` also writes the website copy of the app, `docs/app/index.html`; `tests/unit/test_site.js` checks the copy, links, pictures and tags.

### Other
- Self-test: also checks Persian text, the safe zone and safety lock, and the Wi-Fi set-up messages.
- Tests: `test_zone.js`, `test_wireless.js`, `test_persian.js`; browser tests `e2e_zone.py`, `e2e_wireless.py` (through the real bridge to a pretend arm on UDP, with lost messages) and `e2e_persian.py`.

## 1.5.0 — 2026-10-23

### 3D printing (new tab)
- For Dobot's 3D-printing kit with Dobot's 3D-printer firmware. The printer has its own connection in the tab (the arm and the printer use different firmware), and a printer simulator.
- Models: STL (binary — also with a "solid" header — or ASCII) and OBJ files, or seven built-in models (calibration cube, round vase, twisted vase, gear, pyramid, arch bridge, ball). Units (mm, cm, inches, metres); size, volume and whether the surface is closed. Models larger than the plate are scaled to fit.
- Placement: scale, turn on the plate, tip a quarter turn over X or Y, lay flat on the largest outside face, mirror, move, fit to the plate (leaving room for the skirt), reset; download the placed model as STL.
- Slicer: layers cut through their middles with exact edge linking; walls (innermost first), solid top and bottom wherever the part is open above or below, lines or grid infill on a fixed grid with zig-zag links, supports only from the plate or everywhere (overhangs past an angle, one empty layer above and below, a gap to the sides), skirt with a minimum length, brim, retraction only when the nozzle leaves the part, optional lift, seam nearest or at the back, slower layers so small parts can cool, vase mode (one spiral wall over a solid bottom), overlapping bodies merged. Presets: Normal (Dobot default), Fine, Draft, Strong, Vase.
- Dobot's defaults: 0.4 mm nozzle, 1.75 mm filament at 200 °C with the fan on, 0.2 mm layers with a 0.35 mm first layer, walls at 4 mm/s, infill at 8 mm/s, the first layer at 4 mm/s, 6 mm retraction at 60 mm/s, a Ø80 mm plate centred at X0 Y0 and 150 mm of height; Dobot's start (fan on) and end G-code (heater off, back off, lift, move away, fan off), editable.
- Preview in WebGL: the model on the plate (red when it does not fit), then every printed line by kind, in 3D or one layer at a time, with travel moves if wanted.
- Printing from the page: heat, heater off, feed and retract filament (only when hot), fan, save the nozzle height (M415); a start checklist; G-code sent with line numbers and checksums, one line per "ok" or ahead into the 63-byte buffer; damaged lines resent; a silent printer asked again; renumbering after a restart; live progress (layer, time so far and left) with the preview following the print; pause (filament backed off, nozzle lifted 5 mm) and resume; stop (heater off, nozzle lifted); the red STOP halts the printer (M112 and a reset). The screen is kept awake while printing.
- Download the G-code to print from Repetier Host or Cura.
- Self-test: slices a cube and prints it on the printer simulator with damaged lines.

### Other
- The build stops when two source files declare the same top-level name (it happened once in development: a second `convexHull` replaced the plotter's).
- Third-party code: Clipper 6.4.2 (Boost Software License 1.0) with JSBN; licences in the source and in the app.

## 1.4.0 — 2026-10-23

### Several objects on one sheet
- Drawings, library pictures, traced pictures and text are separate objects, each with its own size, place, turn, mirror and shading. Click one on the map to select it; drag, resize and turn only that one.
- Object list: tick what to draw, Duplicate (D), Delete, Draw only this, Undo remove (Ctrl/⌘+Z), Remove all. New objects go into free space beside what is already there.
- Save layout / Open layout… (everything on the paper as a file) and Layout SVG (the whole sheet in millimetres).

### Text
- Text tool with 13 single-line fonts: Hershey Sans, Serif, Script, Gothic English, German and Italian; EMS Readability, Nixish, Tech, Osmotron, Felix, Allure (handwriting) and Elfin — in Regular, Bold, Italic and Bold italic where the font has them.
- Letter height in millimetres, rotation, alignment, letter and line spacing, several lines; accented letters a font lacks (ā, ł, ő…) are drawn with the accent added. Font credits and licences in the app.

### Hover round
- Before drawing, the pen goes once round everything that will be drawn, about 5 mm above the paper: round a box that holds it all, or along the outline. Its path shows dashed on the map.

### Drawing library: 2 245 drawings in 31 categories
- A Category list (with counts) replaces the theme buttons; search covers names, categories, artists and sources. Every category has at least 50 drawings: animals, cars, nature, leaves, signs, zodiac, emojis, female poses, male poses, faces, objects, city skylines, topography, sports, clothing and outfits, shoes, sports cars, ants, aircraft, army, constellations, flags, technology, art, phones and electronics, music, songs, sci-fi, food and drink, places and buildings, boats, trains and more.
- Flags keep their colours in the grid and in downloaded SVGs; the pen draws their outlines.
- New drawings made by program (`tools/library`): articulated, clothed figures in everyday, sport, work and yoga poses; portraits; country flags; songs engraved as sheet music and instruments (including Persian instruments); city skylines; cars and sports cars; shoes and clothing; aircraft and army; ants; sci-fi; leaves; topography; constellations; vehicles. More pictures from Openclipart (public domain) and icons from Tabler Icons (MIT); star data from d3-celestial (BSD 3-Clause); flags from flag-icons (MIT).
- Names are unique within a category; every drawing fills its 0–1000 box exactly.

### Fixes
- Placement: the largest size at a spot now also fits at every smaller size. Before, a drawing with a gap facing the base could get a default size that did not fit (the area round the base sat inside the gap at the largest size, but a line crossed it a little smaller).

## 1.3.0 — 2026-10-22

### Shading
- Hatch lines inside closed shapes: Lines, Cross-hatch or Three directions; any angle (turns with the drawing); spacing in millimetres on the paper, exact at any size; a different angle per shape (alternate, turn 30°/45°/60° per shape, random); every closed shape, every other level (holes stay empty) or the SVG's filled shapes, where shapes on top hide the ones below and darker colours can get closer lines; outlines on or off; zig-zag joining along the outline; a gap from the outline; Download SVG with shading.
- Click a shape on the map to give it its own shading (turn its lines, cross-hatch it or leave it empty).
- The SVG reader keeps each shape's fill colour, opacity and fill rule.

### Faster
- Stroke ordering uses a grid of stroke ends: 5 000 strokes in about 70 ms instead of 4.5 s.

## 1.2.0 — 2026-10-21

### Drawing library
- 100 ready-made single-line drawings from Openclipart (public domain) in 12 themes, with thumbnails, search, click to load and Download SVG; artists credited in the app.

### SVG reader
- Path data is parsed directly instead of being sampled through the browser: big files load in a fraction of a second instead of tens of seconds.
- Skips invisible shapes, draws `<use>` copies and symbols, reads files without the SVG namespace, keeps rounded rectangles and scales nested viewports correctly.

## 1.1.0 — 2026-10-21

### Smooth and quiet motion
- Motion feel: Quiet & smooth (default), Balanced or Fast. Sets speeds and accelerations and caps every speed command, so dancing, imitation and reactions are gentler too.
- Continuous drawing: the whole drawing streams as one continuous path; short gaps become low, rounded pen hops instead of full stops; detours round the base are one smooth arc.
- Glide following: mouse and camera following move smoothly with limited speed and acceleration instead of jumping from point to point (Steps keeps the old behaviour).
- Quiet-speed finder: moves the arm in the air at several speeds, listens with the microphone and picks the quietest ones.

## 1.0.0 — 2026-10-21

First public release (internal build 4).

### Plotter
- SVG drawing, and pictures (PNG, JPG, WEBP, GIF, BMP) converted to lines: outline, centre-line and edge modes with adjustable threshold, detail and curves; download the lines as SVG.
- Free placement: size in millimetres, any rotation, mirror; drag, resize and rotate on the map; Centre and Largest buttons; adjustable safety margin.
- Green zone: the area the pen can reach at drawing height, from auto-calibration. Every line is kept inside it.
- Optimised stroke order, joining and simplification; pen-up travel routed around the base.
- Smooth continuous-path drawing or precise mode; pause and resume; 20 mm test square placed beside the drawing.
- Live view: red laser dot for the pen; finished lines turn red as they are drawn and stay until "New sheet".

### Calibration and safety
- Auto-calibration from the arm's own joint readings and the Magician geometry; the user only sets the pen-down height. Manual calibration as a fallback.
- Height-aware reach limits, alarm display and clearing, STOP and Esc.

### Other tabs
- Mouse control, record and learn, dance (song file, microphone, metronome), imitate (hand and arm mirror, air drawing, teach by showing), face and reactions.
- Built-in simulator and self-test.
