# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `weasysvg.install()` patches WeasyPrint 70.x to render SVG close to Chromium: `<foreignObject>`,
  conditional processing, vector filter chains with an optional resvg raster fallback, masks set
  before the path, pattern and gradient fixes, `mix-blend-mode`, unclipped opacity groups, text
  baselines and decorations from font metrics, font-size keywords, and Chromium font selection.
- The optional `resvg` extra rasterizes the filters that PDF cannot express.
- Python 3.10 to 3.14 and PyPy 3.11, the versions WeasyPrint 70 supports.
- A visual regression corpus of 115 SVGs with Chromium and resvg references, and a bench that
  compares weasysvg with Chromium.
