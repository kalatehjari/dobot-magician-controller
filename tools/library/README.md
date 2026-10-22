# Drawing library tools

How the app's drawing library (`src/part40_library_data.js`, 2 245 single-line drawings in 31 categories) was made. You only need these to rebuild or extend the library; the app itself has the data built in.

## Generators

One generator per family of drawings made for the library. Each writes a JSON list of drawings (pen lines, category, name) and, optionally, contact sheets that show what the pen would draw:

```sh
python3 gen_poses.py items/poses.json sheets/poses.png
```

| Generator | Drawings |
| --- | --- |
| `gen_poses.py` | male and female poses: articulated, clothed figures (front and side views, reaching with IK) with props |
| `gen_faces.py` | head-and-shoulders portraits: ages, hairstyles, beards, glasses, hats, hijab |
| `gen_flags.py` | 95 country flags with their colours (needs the `flag-icons` npm package) |
| `gen_songs.py` | sheet music of traditional and classical tunes (`gen_songs_data.py`) and instruments (`gen_songs_instr.py`) |
| `gen_skylines.py` | city skylines (`gen_skylines_kit.py`, `gen_skylines_lm.py` for the landmarks) |
| `gen_cars.py` | cars and sports cars (`gen_cars_lib.py`, `gen_cars_side.py`, `gen_cars_parts.py`) |
| `gen_wear.py` | shoes, clothing and outfits (`gen_wear_kit.py`, `gen_wear_shoes.py`, `gen_wear_shoes2.py`, `gen_wear_clothes.py`) |
| `gen_aircraft.py` | aircraft and army (vehicles, gear, insignia) |
| `gen_ants.py`, `gen_scifi.py`, `gen_leaves.py`, `gen_topo.py`, `gen_art.py` | ants, sci-fi, leaves, topography, art |
| `gen_constellations.py`, `gen_zodiac.py` | the 88 constellations (needs the `d3-celestial` data) and zodiac signs |
| `gen_tabler.py` | picks from the Tabler outline icons (needs the `@tabler/icons` package) |
| `gen_transport_extra.py` | locomotive, bus, bicycle, scooter, boats, cable car |

`common.py` is the shared kit: a painter's scene that hides lines behind filled shapes, splines, Hershey single-line lettering (`data/hersheytext.json`; drawings that use the SVG Hershey fonts read them from `HERSHEY_SVG_FONTS`, the `svg_fonts` folder of the `hersheytext` npm package) and contact sheets.

Requirements: Python 3 with `shapely`, `numpy` and `matplotlib`. The generators are deterministic: the same code gives the same drawings.

## Export

`export/export2.py <library folder> <app src folder>` builds the library folder (one SVG per drawing, `library.json`, `README.md`, `CREDITS.md`, licence files) and `part40_library_data.js` from:

- `export/items/*.json`: the generators' output;
- the Openclipart picks (`export/oca_picks.py`), traced the way the app reads SVG files: review lists in `export/review/`, traced strokes in `MAGICIAN_LIBRARY_WORK`, and the 1.2.0 library in `MAGICIAN_LIBRARY_V1` (Openclipart files come from the `openclipart-svg` 0.18 collection, public domain).

Simplification keeps every line's extreme points, so each drawing fills its 1000-unit box exactly; names are made unique within a category.

## Licences

The tools are MIT like the rest of this repository. Drawings made by the generators are public domain. Third-party data keeps its licence: Openclipart (public domain), Tabler Icons and flag-icons (MIT), d3-celestial (BSD 3-Clause) — see `export/licences/` — and the Hershey fonts (free use with acknowledgement: *The Hershey Fonts were originally created by Dr. A. V. Hershey while working at the U. S. National Bureau of Standards.*).
