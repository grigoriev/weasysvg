# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `weasysvg.install()` patches WeasyPrint 70.x to render SVG close to Chromium: `<foreignObject>` with
  the list markers of Chromium and the white space of empty inline boxes collapsed as there,
  conditional processing, vector filter chains (blur, exact for a plain rect, color matrices and
  transfer functions included), masks set before the path, pattern and gradient fixes, `mix-blend-mode`, unclipped
  opacity groups, marker orientation, text baselines from font metrics, text-anchor per text chunk, filters, masks and clips on text, circles of the right length, dots of zero-length dashes in place in PDFium, negative dash offsets of odd dash arrays, decorations placed as in Chromium with underlines that skip the ink of the glyphs (laid out whole or character by character), font-size
  keywords, relative font sizes inherited as computed, `ex` from the x-height of the font, and Chromium font selection. No SVG content is rasterized: the PDF stays vector.
- `feTurbulence`, drawn as an image of the noise, and `feComposite` arithmetic.
- Arabic laid out one character at a time, on a path or down a column, takes its joining forms and runs
  right to left, numbers in it read left to right.
- Upright CJK in vertical text hangs from the vertical origin of its font (`VORG`, `vmtx`), as in Chromium
  and resvg, and `rotate` turns it about that point.
- Python 3.10 to 3.14 and PyPy 3.11, the versions WeasyPrint 70 supports.
- Upstream tracking for WeasyPrint upgrades (UPGRADING.md): probes of the gaps weasysvg covers, a
  snapshot of the internals it hooks, a bench baseline, and a weekly run against the newest WeasyPrint.
- A visual regression corpus of 115 SVGs with Chromium and resvg references, and a bench that
  compares weasysvg with Chromium.
- `corpus/COMPARISON.md` and the interactive `corpus/comparison.html` on GitHub Pages: every corpus SVG
  in Chromium, resvg, WeasyPrint alone and with weasysvg, each panel at 2x as lossless WebP, sharp when zoomed.
- Each corpus SVG names its reference (Chromium, resvg, both, or an English browser). The verdicts say
  whether a rendering is better than it, matches it, comes close or differs, and what differs, in a
  table with an icon per status. The comparison page shows the SVG in your own browser too, and a swipe
  between any two renderers.
- `make review`: the renderings of each corpus SVG compared region by region at twice the resolution of the
  references, with sheets of the cells that differ, to judge the verdicts at full size.
- The visual image has Trebuchet MS, the first font of Mermaid, as Safari has it: Mermaid labels fit their
  boxes in the references.
- `corpus/fonts`: the fonts the resvg tests ask for. The references, weasysvg, resvg and the browser panel of the comparison page all use them.
