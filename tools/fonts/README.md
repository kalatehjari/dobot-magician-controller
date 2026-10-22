# Font tools

How the text tool's single-line fonts (`src/part44_fonts_data.js`) were made.

```sh
python3 build_fonts.py <hersheytext package dir> src/part44_fonts_data.js <OFL.txt>
```

- `build_fonts.py` reads the single-line SVG fonts and the Hershey JSON fonts from the `hersheytext` npm package (Evil Mad Scientist; MIT), scales every character each font has to the same cap height (measured from flat capitals, so swashes do not count), and writes them compactly (one string per font: per glyph its advance and pen lines as base-64 delta varints). The last argument is a copy of the SIL Open Font License 1.1 text, which goes into the credits shown in the app.
- `fontlib.py` reads both font formats into pen lines.
- `analyse_fonts.py` and `metrics_check.py` list which characters each font has and check cap height and baseline.

Fonts: Hershey Sans, Serif, Script and Gothic (Dr. A. V. Hershey, U.S. National Bureau of Standards) and the EMS fonts Readability, Nixish, Tech, Osmotron, Felix, Allure and Elfin (Sheldon B. Michaels; SIL Open Font License 1.1).
