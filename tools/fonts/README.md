# Font tools

How the text tool's single-line fonts (`src/part44_fonts_data.js`) were made.

```sh
python3 build_fonts.py <hersheytext package dir> src/part44_fonts_data.js <OFL.txt>
```

- `build_fonts.py` reads the single-line SVG fonts and the Hershey JSON fonts from the `hersheytext` npm package (Evil Mad Scientist; MIT), scales every character each font has to the same cap height (measured from flat capitals, so swashes do not count), and writes them compactly (one string per font: per glyph its advance and pen lines as base-64 delta varints). The last argument is a copy of the SIL Open Font License 1.1 text, which goes into the credits shown in the app.
- `fontlib.py` reads both font formats into pen lines.
- `analyse_fonts.py` and `metrics_check.py` list which characters each font has and check cap height and baseline.

Fonts: Hershey Sans, Serif, Script and Gothic (Dr. A. V. Hershey, U.S. National Bureau of Standards) and the EMS fonts Readability, Nixish, Tech, Osmotron, Felix, Allure and Elfin (Sheldon B. Michaels; SIL Open Font License 1.1).

## Persian font

`persian/build_persian_font.py` makes the single-line Persian font (`src/part57_persian_font.js`) from Vazirmatn (Round Dots, Thin) by Saber Rastikerdar and the Vazirmatn Project Authors (SIL Open Font License 1.1):

```sh
npm pack vazirmatn@33.0.3 && tar -xzf vazirmatn-33.0.3.tgz
python3 tools/fonts/persian/build_persian_font.py package/Round-Dots/fonts/ttf/Vazirmatn-RD-Thin.ttf package/OFL.txt
```

Every glyph Persian text needs — each letter in its isolated, initial, middle and final forms (the Unicode Arabic presentation forms), the lam-alef ligatures, vowel marks, Persian, Arabic and Latin digits, punctuation and Latin letters — is drawn at 4 font units per pixel, thinned to its centre line (scikit-image) and traced: junction pixels that touch become one node, short side branches are dropped, and the branches are walked through the nodes as straight as possible, so most letters are one or two pen lines. Round dots become small circles. The joining strokes of initial, middle and final forms end exactly at the joining point (x = 0 or the advance, at the height of the tatweel's centre line), so joined letters meet. Letter height = the height of alef. Needs fontTools, numpy and scikit-image; add `--preview file.json` to save the traced lines for a contact sheet.
