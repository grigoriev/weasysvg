# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Each SVG image is one Form XObject: an `<img>`, an inline `<svg>`, a CSS image and an `<image>` inside an
  SVG. Its `/BBox` is the viewport, and the page paints it with `Do` under the matrix that places it, so a
  PDF reader such as PDFBox or PyMuPDF finds each diagram with its size and position. WeasyPrint drew the
  operators straight into the page. The form is no transparency group: it renders as before. The same
  image drawn again at the same size, on the pages or within one group, reuses its form. The
  `form_xobject` argument of `install()` turns it off.
- An SVG background or list marker is clipped at its viewport, as in Chromium: content past it showed.
  An inline `<svg>` with `overflow: visible` still shows its overflow, and its form box grows to let it through.

### Fixed

- SVG text in the generic `monospace` family alone takes 13px as its medium size, as in Chromium and Firefox:
  MathJax writes accented letters as `<text font-family="monospace">` with no size, and they came out 1.23
  times too large. A size from a keyword reads the monospace table of Chromium (`large` is 16px), and a size
  relative to one (`2em`, `50%`, `smaller`) scales by 13/16 where the family turns monospace and back where
  it leaves. A family list (`monospace, serif`) and an absolute length keep their size.
- A tagged PDF (`pdf/ua-1`, `pdf/a-2a`) of an SVG with a `<foreignObject>` renders: WeasyPrint failed on
  the tags of its HTML, which belong to no box of the page. The Figure of the image marks the whole SVG.
- A hole in a blurred shape keeps its size: it grew by one sample on each side, so the ring of the lens in
  the OpenStreetMap logo came out thinner and its shadow lighter than in Chromium.
- The shapes of a theme-aware draw.io export are white, as in Chromium, not black. weasysvg reads the CSS of
  an SVG as Chromium does when it prints: `@supports` blocks apply when their condition holds, custom
  properties and `var()` substitute, also in presentation attributes, and `light-dark()` takes its light
  color. A value that `var()` makes invalid is unset, and an invalid color declaration or attribute is
  ignored, so the attribute or the parent value applies. WeasyPrint painted each of these black. The `css`
  argument of `install()` turns it off.

### Removed

- Python 3.10, which reaches its end of life in October 2026. Pillow 13.0.0 requires Python 3.11, and it
  fixes the vulnerabilities that Dependabot reports for Pillow 12.3.0 in the lock file.
- PyPy. No known user runs weasysvg on it, and its CI job took five minutes, the longest of all.

## [0.2.0] - 2026-10-21

### Added

- `paint-order` on shapes, markers, text and text decoration lines, as Chromium paints it: the stroke of
  the boxes in the OSI model from Wikimedia (`paint-order: stroke`) shows its outer half only. The
  `paint_order` argument of `install()` turns it off.

### Changed

- Text decoration lines take their thickness and place from the font tables, as WeasyPrint draws
  `text-decoration` on HTML text, so SVG text and HTML text in one PDF get the same lines. The underline and
  the overline run straight through the glyphs: WeasyPrint skips no ink. This departs from Chromium on
  purpose (a tenth of the font size, ink skipped) and matches resvg; `text-decoration-thickness: auto`
  allows both.

### Fixed

- A dash that runs through the start point of a closed shape is one dash, with its line join, as in
  Chromium. PDFium drew two dashes that met there: a light seam across the stroke and a notch on its
  outer edge, and no miter at the corner of a rectangle. Every dash keeps its place.
- A translucent stroke over a fill shows the fill under it, as in Chromium. WeasyPrint filled and stroked
  in one operator, a knockout object in PDF, so the stroke showed the white behind the shape.
- Text laid out one character at a time draws its decoration lines character by character, as Chromium,
  Safari and Firefox do: each character carries them over its advance and its letter-spacing, and the room
  `textLength`, `x` and `dx` add between characters stays bare. Text with several `y` or `dy` values gets its
  lines too, under each character on its own baseline. On a `textPath` the last character carries its
  letter-spacing as well.
- An arc of a zero radius in path data draws the straight line SVG asks for: WeasyPrint sent it off by the
  current point, which broke every slice of a Highcharts pie.
- The text after a child of a `<tspan>` is drawn: WeasyPrint dropped it, so `Don<wbr/>e` in a Polarion chart
  label read "Don".
- Text in a `<foreignObject>` sits on the line where Chromium and Safari put it: Blink rounds the font
  metrics to whole px and paints the baseline on a whole px. Mermaid labels sat up to 1 px lower.
- The noise of `feTurbulence` is computed at 2 px per CSS px: at 1 it came out blurred once printed or
  viewed at 2x.
- A blurred rect leaves no seam where its blurred edges meet its middle.
- The space that ends a text moves no anchor: `text-anchor="end"` put the text a space too far left.
- A wide arc in path data is drawn as curves of at most 90 degrees: WeasyPrint drew a half circle as one
  curve, which bulged the band of the flag of Brazil.
- `text-anchor` places each text chunk of SVG 2 as one: a chunk starts only at a character with an absolute
  `x` or `y`, and the text after a positioned `<tspan>` belongs to it. WeasyPrint anchored that text with the
  `<text>`, so the second line of a label in a Wikimedia OSI model diagram sat off its center.
- A blurred filled shape other than a plain rect fades as in Chromium: its coverage is blurred and drawn
  as a mesh of shaded triangles. The levels of the nearest edge left rings in the tail, made a shape
  thinner than a few deviations dark and sharp (the lens ring of the OpenStreetMap logo, the chest of
  Tux) and left white glints where the grown paint had holes (the Inkscape logo).
- The blurred edge of a plain rect follows the Gaussian to about one level of 255, its tail included:
  one shading over 8 deviations showed bands in PDFium, and the paint stopped at 2.15 deviations.
- Any blurred content made of paths fades as in Chromium: a group, a stroke, several shapes and colors.
  Its coverage per color is read back from the PDF operators, blurred and drawn as a mesh of shaded
  triangles, each color mixed in by its share. The levels of the nearest edge drew a mitered corner on a
  blurred square (resvg `filters-filter--on-the-root-svg`) and a stroke in steps with a hard inner edge.
  Text, images, gradients, patterns, masks, blend modes and dashes keep the levels.
- The gradient of a blurred shape pads past the box of the shape: the pattern WeasyPrint makes of it
  repeated there, which cut the shadow of the map in the OpenStreetMap logo with hard straight edges.

## [0.1.0] - 2026-10-21

### Added

- `weasysvg.install()` patches WeasyPrint 70.x to render SVG close to Chromium: `<foreignObject>` with
  the list markers of Chromium and the white space of empty inline boxes collapsed as there,
  conditional processing, vector filter chains (blur, exact for a plain rect, color matrices and
  transfer functions included), masks set before the path, pattern and gradient fixes, `mix-blend-mode`, unclipped
  opacity groups, marker orientation, text baselines from font metrics, text-anchor per text chunk, filters, masks and clips on text, circles of the right length, dots of zero-length dashes in place in PDFium, negative dash offsets of odd dash arrays, decorations placed as in Chromium with underlines that skip the ink of the glyphs (laid out whole or character by character), font-size
  keywords, relative font sizes inherited as computed, `ex` from the x-height of the font, and Chromium font selection. No SVG content is rasterized: the PDF stays vector.
- `feTurbulence`, drawn as an image of the noise, and `feComposite` arithmetic.
- `systemLanguage` reads the `lang` of the document where the image sits, else `install(language=...)`,
  `en` by default: a German document shows the German branch of a `<switch>`.
- Arabic laid out one character at a time, on a path or down a column, takes its joining forms and runs
  right to left, numbers in it read left to right.
- Upright CJK in vertical text hangs from the vertical origin of its font (`VORG`, `vmtx`), as in Chromium
  and resvg, and `rotate` turns it about that point.
- Python 3.10 to 3.14 and PyPy 3.11, the versions WeasyPrint 70 supports.
- Releases on PyPI (`pip install weasysvg`), with publish attestations, and on GitHub, with signed
  build provenance of the same files.
- Upstream tracking for WeasyPrint upgrades (UPGRADING.md): probes of the gaps weasysvg covers, a
  snapshot of the internals it hooks, a bench baseline, and a weekly run against the newest WeasyPrint.
- A visual regression corpus of 115 SVGs with Chromium and resvg references, and a bench that
  compares weasysvg with Chromium.
- `corpus/COMPARISON.md` and the interactive `corpus/comparison.html` on GitHub Pages: every corpus SVG
  in Chromium, resvg, WeasyPrint alone and with weasysvg, each panel at 2x as lossless WebP, sharp when zoomed.
- Each corpus SVG names its reference (Chromium, resvg, or both). The verdicts say
  whether a rendering is better than it, matches it, comes close or differs, and what differs, in a
  table with an icon per status. The comparison page shows the SVG in your own browser too, and a swipe
  between any two renderers.
- `make review`: the renderings of each corpus SVG compared region by region at twice the resolution of the
  references, with sheets of the cells that differ, to judge the verdicts at full size.
- The visual image has Trebuchet MS, the first font of Mermaid, as Safari has it: Mermaid labels fit their
  boxes in the references.
- Chromium prints the references with the Accept-Language list of a desktop Chrome in English
  (`en-US,en`): `systemLanguage` matches English as there.
- `corpus/fonts`: the fonts the resvg tests ask for. The references, weasysvg, resvg and the browser panel of the comparison page all use them.
