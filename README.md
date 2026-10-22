# weasysvg

[![CI](https://github.com/grigoriev/weasysvg/actions/workflows/ci.yml/badge.svg)](https://github.com/grigoriev/weasysvg/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/grigoriev/weasysvg/badge)](https://scorecard.dev/viewer/?uri=github.com/grigoriev/weasysvg)
[![Release](https://img.shields.io/github/v/release/grigoriev/weasysvg)](https://github.com/grigoriev/weasysvg/releases)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/grigoriev/weasysvg/blob/main/LICENSE)

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

weasysvg runs on CPython 3.11 to 3.14.

Install it from PyPI:

```sh
pip install weasysvg
```

weasysvg depends on WeasyPrint only. Every SVG feature it adds stays vector in the PDF, blur included.
The one exception is the noise of `feTurbulence`: it has no vector form, so it is an image, computed in
Python.

WeasyPrint needs Pango, see its
[installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).

### Verify

The build of each release has signed provenance on GitHub, and the GitHub release carries its bundle.
PyPI and the GitHub release hold the same files, so verify a file from either with
`gh attestation verify <file> --repo grigoriev/weasysvg`. On PyPI each file also has a publish
attestation (PEP 740): it ties the upload to `release.yml` of this repository.

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
| `conditional_processing` | `True` | `<switch>`, `requiredExtensions`, `systemLanguage` |
| `foreign_object` | `True` | `<foreignObject>` content laid out by WeasyPrint |
| `filters` | `True` | filter chains, `drop-shadow()` and `blur()` |
| `paint` | `True` | gradients, patterns and masks |
| `blend` | `True` | `mix-blend-mode` (needs `paint`) |
| `text` | `True` | text baselines, decorations, font-size keywords |
| `fonts` | `True` | font family selection as Chromium does it |
| `fetch_cache` | `True` | one fetch per URL and SVG |
| `markers` | `True` | marker orientation as in Chromium |
| `paint_order` | `True` | `paint-order` of shapes and text |
| `form_xobject` | `True` | each SVG image as one Form XObject, its BBox the viewport |
| `css` | `True` | `@supports`, custom properties, `var()` and `light-dark()` in the light color scheme |
| `language` | `"en"` | the language `systemLanguage` reads where the document has no `lang` |

weasysvg targets WeasyPrint 70.x and warns on any other major version: it patches internals that
change between releases.

## Features

| Area | What weasysvg adds |
|---|---|
| `<foreignObject>` | The XHTML inside is laid out as a WeasyPrint document and drawn in place. The SVG stylesheet still matches it. All objects of one SVG share one layout run. Tables taller than their rows grow their rows, as browsers do. Disc, circle and square list markers are the shapes Chromium paints, placed from the ascent of the font. Lines take the font metrics rounded to whole px and the baseline on a whole px, as in Chromium and Safari: a Mermaid label no longer sits up to 1 px low. |
| Conditional processing | `<switch>` draws its first matching child. `requiredExtensions` and `systemLanguage` hide elements, so draw.io no longer draws both the label and its fallback. XHTML counts as supported only with `foreign_object` on; without it the fallback wins. `systemLanguage` reads the `lang` of the element that holds the image (`<html lang="de">`), else the `language` of `install()`, and matches as Chromium does with the Accept-Language list of that language (`de-CH` reads `de-CH,de`). An SVG from CSS (`background-image`, `list-style-image`, `content: url()`) reads `language`. |
| Filters | `feGaussianBlur`, `feOffset`, `feFlood`, `feDropShadow`, `feMerge`, `feBlend` normal, `feComposite` over, in and arithmetic, `feColorMatrix`, `feComponentTransfer`, `primitiveUnits="objectBoundingBox"`, and the CSS `drop-shadow()` and `blur()` functions, all in vector. `feTurbulence` noise is an image. A blur is a soft mask: exact for a plain rect, as the product of two Gaussian profiles, a mesh of shaded triangles through the blurred coverage for another filled shape, and in steps through the profile for the rest. A color matrix or transfer function recolors each fill, stroke and gradient stop. |
| Masks and clips | A mask is set before the path starts, so viewers apply it. `maskContentUnits`, the region of an `objectBoundingBox` mask, self-referencing masks, and `mask` on a `<mask>` ignored as in Chromium. A clip path with `clip-rule="evenodd"`, text, `<use>` or clipped children becomes a soft mask. |
| Gradients and patterns | Tiles start at the user space origin, `patternTransform` moves the tile origin too, patterns used twice, a gradient cell that covers the shape under any `gradientTransform`, colors mixed unpremultiplied as in Chromium, radial `r` and `fr` percentages, `href` stops used twice, a gradient cell that Quartz and Splash do not drop. |
| Blending and opacity | `mix-blend-mode` as an isolated group. Opacity groups are no longer clipped to the bounding box, which cut off shifted text. |
| Text | Vertical `writing-mode` (`tb`, `vertical-rl`): CJK upright from the vertical origin of the font (`VORG`, `vmtx`), other scripts sideways, `rotate` about the origin of each glyph as in resvg. `textPath` (SVG 2 `path` attribute, `href`, `startOffset`, `text-anchor`, `<tspan>` inside, decorations). A run with one position at most is laid out whole, so Arabic joins, bidi orders and kerning and ligatures apply; laid out one character at a time, on a path or down a column, Arabic in one text node still takes its joining forms and runs right to left; `letter-spacing` skips cursive scripts. `dominant-baseline` and `alignment-baseline` from real font metrics, `text-decoration` placed and sized from the font tables as WeasyPrint draws it on HTML text, through the glyphs (on purpose not as Chromium, which draws a tenth of the font size and skips the ink; resvg reads the font too), text laid out one character at a time (`textLength`, `x`, `y`, `dx`, `dy` lists) carries the lines under each character on its own baseline and leaves the room added between characters bare, font-size keywords, the 13px default of the generic `monospace` alone as in Chromium (keyword sizes from its table, relative sizes scaled by 13/16), a relative font size inherited as computed and `ex` from the x-height of the font, nested `<text>` ignored, the text after a child of a `<tspan>` drawn (`Don<wbr/>e` in a Polarion chart label), `text-anchor` per text chunk. A filter, mask or clip on text uses the box of the text as drawn. |
| Fonts | A CSS family list resolves to one family as Chromium on Linux does, with its metric-compatible replacements (Arial to Liberation Sans). A character the family lacks comes from the sans-serif list, as in Chromium. |
| Markers | `orient="auto"` follows the tangents of lines, curves and arcs, and a mid marker bisects its vertex with the angle wrap of Chromium. |
| Paint order | `paint-order` (`normal` or any order of `fill`, `stroke` and `markers`, attribute or CSS, inherited) on shapes, their markers, text and its decoration lines, as in Chromium. Each paint is a pass of its own in one graphics state, inside the opacity group, mask, filter and clip of the element. An invalid value is ignored, so the parent value inherits. A translucent stroke over a fill shows the fill under it: WeasyPrint painted both as one knockout object, which showed the backdrop. |
| Presentation attributes | An empty attribute such as `fill=""` is ignored, as in browsers. |
| CSS | `@supports` rules apply when their condition holds (declarations, `not`, `and`, `or`, `selector()`). Custom properties inherit, and `var()` substitutes with its fallbacks, in `style`, in stylesheets and in presentation attributes. A value that `var()` makes invalid is unset: inherited or initial, never the attribute. An invalid color declaration or attribute is ignored, as in Chromium, where WeasyPrint painted black. The SVG renders in the light color scheme, as Chromium prints it: `light-dark()` takes its light color, whatever `color-scheme` asks for, and `prefers-color-scheme: dark` never matches. A theme-aware draw.io export keeps its white shapes. |
| Dashes | A dash that runs through the start point of a closed shape is one dash with its line join, as in Chromium: PDFium drew two, with a seam across the stroke. A dash of length 0 under a round or square cap keeps its place, and a negative offset of an odd array counts back from its whole period. |
| Output structure | Each SVG image is one Form XObject (`/Subtype /Form`, no transparency group): an `<img>`, an inline `<svg>`, a CSS image, an `<image>` inside an SVG (a form inside the form). Its `/BBox` is the viewport, `[0 0 width height]` after CSS sizing, in the space the page paints it in with `Do`. A reader of the PDF finds each diagram, its size and its place: PDFBox `PDFormXObject`, PyMuPDF `get_xobjects()` and `get_bboxlog()`. The box clips, as Chromium clips an image; an inline `<svg>` with `overflow: visible` gets a box wide enough for its overflow. The same image drawn again at the same size, on the pages or within one group, reuses its form. In a tagged PDF the Figure of the image marks the `Do`. |
| Path data | An arc of a zero radius draws a straight line to its end, as SVG says: Highcharts closes each slice of a pie with one. An arc wider than 90 degrees is drawn as curves of 90 degrees at most: WeasyPrint drew up to half a circle as one curve, which bulged by 1.8 % of its radius. |

## How it compares to Chromium

The bench in [`tools/visual`](https://github.com/grigoriev/weasysvg/tree/main/tools/visual) renders a corpus of 117 SVGs. The corpus holds draw.io,
Mermaid, PlantUML, Graphviz, D2 and BPMN diagrams, real-world files from Wikimedia Commons, and tests of
the resvg suite. Every SVG has a reference: Chromium, resvg, or both where they agree (68 SVGs). For the resvg tests the expected
image of the resvg suite decides between Chromium and resvg where they differ. `make review` compares the
renderings at twice the resolution of the panels, in an 8 x 8 grid, and a look at each cell that differs
gives the verdict:

| Verdict | WeasyPrint 70 | WeasyPrint 70 with weasysvg |
|---|---|---|
| ⬆️ better than the reference | 0 | 1 |
| ✅ matches the reference | 39 | 111 |
| 🟡 close to the reference | 22 | 5 |
| ❌ differs from the reference | 56 | 0 |

Of the 36 diagrams from draw.io, kroki and mermaid.ink, 31 match the reference and 5 are close.
Each verdict says what differs. The verdicts are in [`corpus/verdicts.json`](https://github.com/grigoriev/weasysvg/blob/main/corpus/verdicts.json). The [comparison page](https://grigoriev.github.io/weasysvg/corpus/comparison.html)
shows every SVG in Chromium, your own browser, resvg, WeasyPrint alone and WeasyPrint with weasysvg, in a row,
with the reference marked and a swipe between any two of them, as GitHub compares images;
[`corpus/COMPARISON.md`](https://github.com/grigoriev/weasysvg/blob/main/corpus/COMPARISON.md) holds the same in the repository.

## Known gaps

- On a `textPath` and in vertical text each character is laid out alone. Arabic takes its joining forms,
  but loses the forms and ligatures some fonts pick from the whole word (Amiri): such a word runs longer.
- On a `textPath` and in vertical text, joining and right-to-left order stop at the edge of a `<tspan>`: an
  Arabic word split by one falls apart there.
- Vertical text draws no decoration lines.
- The text after a child of a nested `<tspan>` is drawn as a `<tspan>` of its own, which counts as a sibling for
  structural selectors (`:last-child`, `:nth-child`, `+`). WeasyPrint does the same for the children of a `<text>`.
- A plain rect is blurred exactly. A filled shape without stroke or markers is blurred from its coverage,
  sampled on a grid of a third of a deviation, within some 3 levels of 255. Anything else (strokes, text,
  groups, a grid past its limits) is blurred in levels by the distance to its nearest edge, which knows
  nothing of the far edge: a shape thinner than about two deviations comes out darker and sharper than in
  Chromium, and the tail shows steps.
- Lighting, morphology, convolution and displacement have no vector form: the element draws
  unfiltered, with a warning.
- `feComposite` arithmetic needs one input to be a flood of the whole filter region, or both inputs to
  be the same. A translucent result composites over the value of the formula on nothing.
- Except on a plain rect or a filled shape, a blur with two different deviations uses their mean.

## Development

Tests and the bench run in Docker, since WeasyPrint needs Pango. See [CONTRIBUTING.md](https://github.com/grigoriev/weasysvg/blob/main/CONTRIBUTING.md).

```sh
make lint     # ruff and mypy, on the host
make test     # pytest with coverage, in Docker
make visual   # the visual bench, report in tools/visual/out/report.html
make comparison # corpus/COMPARISON.md, the renderings of every SVG side by side
make upstream # probes of the WeasyPrint gaps and of the hooked internals
```

weasysvg supports the latest WeasyPrint major only. [UPGRADING.md](https://github.com/grigoriev/weasysvg/blob/main/UPGRADING.md) describes how a new one
is taken: which patches it makes redundant, which internals changed, what renders worse.

## Contributing

See [CONTRIBUTING.md](https://github.com/grigoriev/weasysvg/blob/main/CONTRIBUTING.md). Report vulnerabilities privately, see [SECURITY.md](https://github.com/grigoriev/weasysvg/blob/main/SECURITY.md).

## Disclaimer

This software is provided "as is", without warranty of any kind, as the LICENSE states. Use
it at your own risk. Sergey Grigoriev is not liable for damage from its use, as far as the law
allows. It is published free of charge, outside of any commercial offering, with no
obligation to support it. Security reports are welcome, see [SECURITY.md](https://github.com/grigoriev/weasysvg/blob/main/SECURITY.md).

## License

MIT, see [LICENSE](https://github.com/grigoriev/weasysvg/blob/main/LICENSE). The test corpus keeps the licenses of its sources, see
[corpus/SOURCES.md](https://github.com/grigoriev/weasysvg/blob/main/corpus/SOURCES.md).
