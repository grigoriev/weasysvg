# weasysvg

[![CI](https://github.com/grigoriev/weasysvg/actions/workflows/ci.yml/badge.svg)](https://github.com/grigoriev/weasysvg/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/grigoriev/weasysvg/badge)](https://scorecard.dev/viewer/?uri=github.com/grigoriev/weasysvg)
[![Release](https://img.shields.io/github/v/release/grigoriev/weasysvg)](https://github.com/grigoriev/weasysvg/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=grigoriev_weasysvg&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=grigoriev_weasysvg)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=grigoriev_weasysvg&metric=coverage)](https://sonarcloud.io/summary/new_code?id=grigoriev_weasysvg)

A plugin for [WeasyPrint](https://weasyprint.org) 70.x that renders SVG natively, close to Chromium.

## Why?

WeasyPrint draws SVG as vector graphics, but it lacks `<foreignObject>` and has gaps in filters, masks,
blending and text. Diagram tools depend on these: draw.io and Mermaid put their labels in
`<foreignObject>`, D2 masks its edge labels, and many tools draw shadows with filters. Services that
turn HTML into PDF therefore rasterize SVG in a headless Chromium first.

weasysvg closes these gaps inside WeasyPrint. The SVG stays vector, text stays selectable, and the
service needs no browser.

## Installation

weasysvg runs on CPython 3.10 to 3.14 and on PyPy 3.11, as WeasyPrint 70 does. On PyPy a C compiler
must be present: zopfli, which WeasyPrint needs, has no PyPy wheel and builds from source.

The package is not on PyPI yet. Install a release from GitHub:

```sh
pip install "weasysvg @ git+https://github.com/grigoriev/weasysvg@v0.1.0"
```

weasysvg depends on WeasyPrint only. Every SVG feature it adds stays vector in the PDF, blur included.
The one exception is the noise of `feTurbulence`: it has no vector form, so it is an image, computed in
Python.

WeasyPrint needs Pango, see its
[installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).

### Verify

GitHub releases carry a signed provenance bundle. Verify a downloaded file with
`gh attestation verify <file> --repo grigoriev/weasysvg`.

## Usage

Call `install()` once, before the first rendering:

```python
import weasyprint
import weasysvg

weasysvg.install()
weasyprint.HTML("report.html").write_pdf("report.pdf")
```

`install()` patches WeasyPrint in place, for the whole process. It is idempotent, and it returns the
names of the installed features. Each feature can be turned off:

```python
weasysvg.install(filters=False, fonts=False)
```

| Argument | Default | Effect |
|---|---|---|
| `conditional_processing` | `True` | `<switch>`, `requiredExtensions`, `systemLanguage` (as Chromium in `en-US`) |
| `foreign_object` | `True` | `<foreignObject>` content laid out by WeasyPrint |
| `filters` | `True` | filter chains, `drop-shadow()` and `blur()` |
| `paint` | `True` | gradients, patterns and masks |
| `blend` | `True` | `mix-blend-mode` (needs `paint`) |
| `text` | `True` | text baselines, decorations, font-size keywords |
| `fonts` | `True` | font family selection as Chromium does it |
| `fetch_cache` | `True` | one fetch per URL and SVG |
| `markers` | `True` | marker orientation as in Chromium |

weasysvg targets WeasyPrint 70.x and warns on any other major version: it patches internals that
change between releases.

## Features

| Area | What weasysvg adds |
|---|---|
| `<foreignObject>` | The XHTML inside is laid out as a WeasyPrint document and drawn in place. The SVG stylesheet still matches it. All objects of one SVG share one layout run. Tables taller than their rows grow their rows, as browsers do. |
| Conditional processing | `<switch>` draws its first matching child. `requiredExtensions` and `systemLanguage` hide elements, so draw.io no longer draws both the label and its fallback. XHTML counts as supported only with `foreign_object` on; without it the fallback wins. |
| Filters | `feGaussianBlur`, `feOffset`, `feFlood`, `feDropShadow`, `feMerge`, `feBlend` normal, `feComposite` over, in and arithmetic, `feColorMatrix`, `feComponentTransfer`, `primitiveUnits="objectBoundingBox"`, and the CSS `drop-shadow()` and `blur()` functions, all in vector. `feTurbulence` noise is an image. A blur is a soft mask that steps through the Gaussian profile of the edge. A color matrix or transfer function recolors each fill, stroke and gradient stop. |
| Masks and clips | A mask is set before the path starts, so viewers apply it. `maskContentUnits`, the region of an `objectBoundingBox` mask, self-referencing masks, and `mask` on a `<mask>` ignored as in Chromium. A clip path with `clip-rule="evenodd"`, text, `<use>` or clipped children becomes a soft mask. |
| Gradients and patterns | Tiles start at the user space origin, `patternTransform` moves the tile origin too, patterns used twice, a gradient cell that covers the shape under any `gradientTransform`, colors mixed unpremultiplied as in Chromium, radial `r` and `fr` percentages, `href` stops used twice, a gradient cell that Quartz and Splash do not drop. |
| Blending and opacity | `mix-blend-mode` as an isolated group. Opacity groups are no longer clipped to the bounding box, which cut off shifted text. |
| Text | Vertical `writing-mode` (`tb`, `vertical-rl`): CJK upright, other scripts sideways. `textPath` (SVG 2 `path` attribute, `href`, `startOffset`, `text-anchor`, `<tspan>` inside, decorations). A run with one position at most is laid out whole, so Arabic joins, bidi orders and kerning and ligatures apply; `letter-spacing` skips cursive scripts. `dominant-baseline` and `alignment-baseline` from real font metrics, `text-decoration` placed and sized as in Chromium, font-size keywords, nested `<text>` ignored. |
| Fonts | A CSS family list resolves to one family as Chromium on Linux does, with its metric-compatible replacements (Arial to Liberation Sans). A character the family lacks comes from the sans-serif list, as in Chromium. |
| Markers | `orient="auto"` follows the tangents of lines, curves and arcs, and a mid marker bisects its vertex with the angle wrap of Chromium. |
| Presentation attributes | An empty attribute such as `fill=""` is ignored, as in browsers. |

## How it compares to Chromium

The bench in [`tools/visual`](tools/visual) renders a corpus of 115 SVGs and compares each result with
Chromium. The corpus holds draw.io, Mermaid, PlantUML, Graphviz, D2 and BPMN diagrams, real-world
files from Wikimedia Commons, and tests of the resvg suite. Each pair carries a verdict from a visual
review:

| Verdict | WeasyPrint 70 | WeasyPrint 70 with weasysvg |
|---|---|---|
| same as Chromium | 40 | 109 |
| minor difference | 10 | 6 |
| other font only | 11 | 0 |
| broken | 54 | 0 |

All 35 diagrams from draw.io, kroki and mermaid.ink render the same as in Chromium. The remaining
differences are in the resvg feature tests, one Wikimedia file, and the MDN `<foreignObject>` example,
which has no scrollbar for `overflow: auto` (print has no use for one). The verdicts are in
[`corpus/verdicts.json`](corpus/verdicts.json). The [comparison page](https://grigoriev.github.io/weasysvg/corpus/comparison.html)
shows every SVG in Chromium, your own browser, resvg, WeasyPrint alone and WeasyPrint with weasysvg, in a row,
with a swipe between any two of them, as GitHub compares images; [`corpus/COMPARISON.md`](corpus/COMPARISON.md) holds the same in the repository.

## Known gaps

- On a `textPath` each character is laid out alone, so Arabic does not join there. Underlines skip no ink.
- A blur treats every point by its distance to the nearest edge: sharp corners and thin filled shapes
  come out a little darker than in Chromium.
- Lighting, morphology, convolution and displacement have no vector form: the element draws
  unfiltered, with a warning.
- `feComposite` arithmetic needs one input to be a flood of the whole filter region, or both inputs to
  be the same. A translucent result composites over the value of the formula on nothing.
- A blur with two different deviations uses their mean.
- `overflow: auto` inside a `<foreignObject>` shows no scrollbar, so text reflows into the full width.

## Development

Tests and the bench run in Docker, since WeasyPrint needs Pango. See [CONTRIBUTING.md](CONTRIBUTING.md).

```sh
make lint     # ruff and mypy, on the host
make test     # pytest with coverage, in Docker
make visual   # the visual bench, report in tools/visual/out/report.html
make comparison # corpus/COMPARISON.md, the renderings of every SVG side by side
make upstream # probes of the WeasyPrint gaps and of the hooked internals
```

weasysvg supports the latest WeasyPrint major only. [UPGRADING.md](UPGRADING.md) describes how a new one
is taken: which patches it makes redundant, which internals changed, what renders worse.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Report vulnerabilities privately, see [SECURITY.md](SECURITY.md).

## Disclaimer

This software is provided "as is", without warranty of any kind, as the LICENSE states. Use
it at your own risk. Sergey Grigoriev is not liable for damage from its use, as far as the law
allows. It is published free of charge, outside of any commercial offering, with no
obligation to support it. Security reports are welcome, see [SECURITY.md](SECURITY.md).

## License

MIT, see [LICENSE](LICENSE). The test corpus keeps the licenses of its sources, see
[corpus/SOURCES.md](corpus/SOURCES.md).
