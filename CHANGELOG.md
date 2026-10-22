# Changelog

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
