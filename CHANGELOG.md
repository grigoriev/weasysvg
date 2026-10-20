# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `weasysvg.install()` patches WeasyPrint 70.x to render SVG close to Chromium: `<foreignObject>`,
  conditional processing, vector filter chains (blur, exact for a plain rect, color matrices and
  transfer functions included), masks set before the path, pattern and gradient fixes, `mix-blend-mode`, unclipped
  opacity groups, marker orientation, text baselines from font metrics, text-anchor per text chunk, filters, masks and clips on text, circles of the right length, dots of zero-length dashes in place in PDFium, negative dash offsets of odd dash arrays, decorations placed as in Chromium, font-size
  keywords, and Chromium font selection. No SVG content is rasterized: the PDF stays vector.
- `feTurbulence`, drawn as an image of the noise, and `feComposite` arithmetic.
- Python 3.10 to 3.14 and PyPy 3.11, the versions WeasyPrint 70 supports.
- Upstream tracking for WeasyPrint upgrades (UPGRADING.md): probes of the gaps weasysvg covers, a
  snapshot of the internals it hooks, a bench baseline, and a weekly run against the newest WeasyPrint.
- A visual regression corpus of 115 SVGs with Chromium and resvg references, and a bench that
  compares weasysvg with Chromium.
- `corpus/COMPARISON.md` and the interactive `corpus/comparison.html` on GitHub Pages: every corpus SVG
  in Chromium, resvg, WeasyPrint alone and with weasysvg.
- Each corpus SVG names its reference (Chromium, resvg, both, or an English browser). The verdicts say
  whether a rendering is better than it, matches it, comes close or differs, and what differs, in a
  table with an icon per status. The comparison page shows the SVG in your own browser too, and a swipe
  between any two renderers.
- `make review`: the renderings of each corpus SVG compared region by region at twice the resolution of the
  panels, with sheets of the cells that differ, to judge the verdicts at full size.
- `corpus/fonts`: the fonts the resvg tests ask for. The references, weasysvg and resvg all use them.
