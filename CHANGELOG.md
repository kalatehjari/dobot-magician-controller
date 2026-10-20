# Changelog

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
