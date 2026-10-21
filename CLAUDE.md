# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/claude-code) when working with this repository.

## Project Overview

weasysvg is a plugin for WeasyPrint 70.x that renders SVG natively and close to Chromium. One
`weasysvg.install()` call monkeypatches WeasyPrint internals for the whole process. Everything stays
vector in the PDF: weasysvg rasterizes no SVG content. The one image it makes is the noise of
`feTurbulence`, computed in Python. resvg serves only as a reference in the corpus.

## Tech Stack

- **Python**: 3.10+ and PyPy 3.11, as WeasyPrint 70 supports them (the target services run 3.14)
- **Package Manager**: uv
- **Build Backend**: hatchling, `src/` layout
- **Linting/Formatting**: ruff, line length 240
- **Type Checking**: mypy (strict mode); WeasyPrint has no types, so its objects are `Any`
- **Testing**: pytest with pytest-cov, in Docker (WeasyPrint needs Pango)

## Common Commands

```bash
uv sync --all-extras    # install dependencies
make lint               # ruff check, ruff format --check, mypy src tests tools
make test               # pytest with coverage in Docker (Dockerfile.test, stage "test")
make visual             # visual bench in Docker (stage "visual"), report in tools/visual/out/report.html
make upstream           # gap probes and hook snapshot, WeasyPrint alone (upstream/)
make hooks              # write upstream/hooks.json for the installed WeasyPrint
make visual-baseline    # write corpus/baseline.json, weasysvg and WeasyPrint alone
make visual-check       # compare with corpus/baseline.json, fails when weasysvg got worse
make comparison         # write corpus/COMPARISON.md, corpus/comparison.html (GitHub Pages), panels in corpus/render
uv build                # wheel and sdist
```

## Architecture

`src/weasysvg/`, one module per feature. `install()` in `__init__.py` calls each module's `install()`
once.

- `_core.py`: the two shared hooks. `images.SVGImage.__init__` runs the tree passes on the parsed
  XML (conditional 10, nested_text 15, invalid_rotate 16, nested_tails 17, empty_presentation 20, zero_radius_arcs 20, foreign_object 30) and wraps the URL
  fetcher. `svg.SVG.draw_node` combines filter, mask, blend and the opacity group in CSS order.
  A node that holds text and has a filter, mask or clip is drawn once into a scratch group first
  (`measure_text`): WeasyPrint knows the box of a text only after drawing it. The text box is kept
  where `text-anchor` moved it (`text.anchored`).
- `conditional.py`: `<switch>`, `requiredExtensions`, `systemLanguage`.
- `foreign_object.py`: stashes the XHTML in an attribute, lays all objects of one SVG out as one
  WeasyPrint document (one page each), draws each page into the SVG stream. Also patches
  `layout.block.table_layout` inside a foreignObject.
- `filters.py`: evaluates a filter chain into vector layers. A blur is a luminosity soft mask built in
  levels: the shapes grown by a stroke outside, bands along the edge inside (`RESTYLE`). Color matrices
  and transfer functions recolor every parsed color (`RECOLOR`). feComposite arithmetic with a constant
  input is a recolor too. `turbulence.py` computes the noise of feTurbulence as an image layer.
- `paint.py`: gradients, patterns, masks, `mix-blend-mode`.
- `pathdata.py`: path data as segments with tangents and points along them.
- `markers.py`: marker angles from `pathdata`, rebuilt into `node.vertices` after WeasyPrint draws a shape.
- `text.py`, `fonts.py`: SVG text, Chromium font selection.
- `textpath.py`: characters placed along a `pathdata.Polyline`, for `<textPath>` and its `<tspan>`.
- `vertical.py`: vertical `writing-mode`, characters placed down the y axis.
- `glyphs.py`: characters drawn one at a time at their own origin and angle, for the two above.
- `fetch.py`: one fetch per URL and SVG.

Every patch keeps a reference to the original WeasyPrint function and restores the attributes it
changes on a node: WeasyPrint walks `<use>` targets, gradients and patterns more than once.

## Testing

- `tests/helpers.py` renders an SVG through an `<img>` data URL with uncompressed streams. `render()`
  fails when a `gs` operator appears inside path construction.
- Assert on PDF operators (`streams()`, `content()`), extracted text (`text_of()`) and PDFium pixels
  (`pixel()`, 72 dpi, so CSS px times 0.75).
- Coverage is 100% of lines. One branch cannot be reached: `conditional.py` (a failing element whose
  parent no longer holds it).

## Visual regression bench

`tools/visual/bench.py` renders `corpus/svg`, compares with `corpus/reference/chromium` and writes a
report. It is a dev tool, not a CI gate. `corpus/verdicts.json` holds the reference and the visual
verdicts per SVG (schema in CONTRIBUTING.md). `make references` reprints the Chromium references in the
visual image, which has the fonts of `corpus/fonts` and Trebuchet MS. Judge a rendering zoomed in, never from a thumbnail:
`make review` writes sheets of the cells that differ, at 2x, from the PDFs (rules in CONTRIBUTING.md).

**Never judge a rendering with poppler.** Splash drops WeasyPrint gradients and cairo drops soft masks.
Use PDFium (`tools/visual/imaging.py`), and check a disputed case in Quartz (macOS Preview).

Every corpus file needs a cleared license and an entry in `corpus/SOURCES.md`. Never reformat corpus
files: pre-commit excludes them.

## Upstream tracking

weasysvg supports the latest WeasyPrint major only; UPGRADING.md is the procedure for a new one.
A new patch for a WeasyPrint gap needs a probe in `upstream/test_gaps.py` that shows the gap on WeasyPrint
alone, and its hooked internals in `HOOKS` of `tools/upstream/hooks.py` (then `make hooks`). The probes
run in a process of their own: `tests/helpers.py` installs weasysvg on import.

## Code Style

- Strict mypy typing; WeasyPrint objects are `Any`.
- Comments say why a patch exists, with the browser behavior it copies.
- No em-dashes, American spelling.

## Review focus

- A patch must restore every attribute, tag and stream method it changes, also on an exception
  (`try`/`finally`). A leak shows as wrong output on the second `<use>` of the same element.
- No graphics state (`gs`) between path construction and its paint operator: viewers ignore it.
- Untrusted SVG: `foreignObject` content must not reach files or URLs outside the URL fetcher of the
  caller. A blur draws its element up to 3 * MAX_STEPS + 2 times: keep the step count capped. Pixels
  computed in Python (turbulence, recolored images) count against MAX_PIXEL_WORK per SVG.
- WeasyPrint internals change between majors: a new hook needs a test that fails when the hooked
  function changes shape.
- A rendering change updates `corpus/verdicts.json`, `corpus/COMPARISON.md` (`make comparison`) and, for
  a new gap or a fixed one, the README.

## CI/CD

- **CI** (`ci.yml`): actionlint and zizmor; tests on Python 3.10 to 3.14 and PyPy 3.11 with Pango and fonts from apt;
  SonarCloud; build.
- **Scorecard** (`scorecard.yml`): OpenSSF Scorecard, weekly and on push to main.
- **Release** (`release.yml`): on `v*` tags, tests, one build with signed provenance, then PyPI
  through Trusted Publishing (`pypi` environment), then a GitHub release with the wheel, the sdist
  and the provenance bundle.
- Every action is pinned by SHA, `${{ }}` values reach `run:` through `env:`, checkouts use
  `persist-credentials: false`.

## Release Process

1. Add each change under `## [Unreleased]` in `CHANGELOG.md`, in the pull request that makes it.
2. Run the **Bump Version & Release** workflow with `patch`, `minor` or `major`. It writes the
   version to `pyproject.toml`, cuts the changelog, commits, tags `vX.Y.Z` and pushes.
3. The tag triggers `release.yml`, which publishes to PyPI and creates the GitHub release.
