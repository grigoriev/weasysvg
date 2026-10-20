# Contributing

Issues and pull requests are welcome.

## Build and test

WeasyPrint needs Pango. macOS has none, so the tests and the bench run in Docker (`Dockerfile.test`).
Lint and type checks run on the host.

```sh
uv sync --all-extras                # install the dependencies
make lint                           # ruff check, ruff format --check, mypy
make test                           # pytest with coverage, in Docker
make test BASE=python:3.10-slim-trixie  # the same on the lowest supported Python
make test BASE=pypy:3.11-slim-trixie    # the same on PyPy
make visual                         # the visual bench, in Docker
make upstream                       # probes of the WeasyPrint gaps and hooked internals
make visual-check                   # the bench against corpus/baseline.json
make comparison                     # corpus/COMPARISON.md, corpus/comparison.html, panels in corpus/render
uv build                            # wheel and sdist
```

On Linux with Pango installed, `uv run pytest --cov` works without Docker.

A patch for a WeasyPrint gap comes with a probe in `upstream/test_gaps.py` and its hooked internals in
`tools/upstream/hooks.py`. [UPGRADING.md](UPGRADING.md) describes how a new WeasyPrint is taken.

CI runs actionlint, zizmor, ruff, mypy, the tests on Python 3.10 to 3.14 and PyPy 3.11, and SonarCloud for every pull
request.

## Visual regression bench

The unit tests check the PDF structure. The bench checks what it looks like:

1. `make visual` renders every SVG of `corpus/svg` through WeasyPrint and weasysvg, in the page the
   references were made from.
2. It rasterizes each PDF with PDFium at 96 dpi and compares it with the Chromium reference in
   `corpus/reference/chromium`. The mismatch is the share of the drawing that differs, in percent.
3. It writes `tools/visual/out/report.html`: Chromium, weasysvg and the resvg reference side by side,
   worst first.

`make visual ARGS="--only drawio"` renders the names that contain `drawio`. The bench is a dev tool, not
a CI gate. The mismatch guides the eye; the verdicts in `corpus/verdicts.json` are the judgment. Update
a verdict when a change makes a rendering better or worse.

A change that alters a rendering or a verdict also runs `make comparison` and commits
`corpus/COMPARISON.md`, `corpus/comparison.html` and `corpus/render`. The page shows each SVG in Chromium, resvg (rendered by
resvg-py of the `visual` extra), WeasyPrint alone and WeasyPrint with weasysvg.

Never judge a rendering with poppler (`pdftoppm`, Evince, Okular). Its Splash backend drops WeasyPrint
gradients, and its cairo backend drops soft masks that PDFium and Quartz apply. Use PDFium, which is the
PDF engine of Chrome, and check a disputed case in Quartz (macOS Preview).

A new corpus file needs a license that allows redistribution, and an entry in `corpus/SOURCES.md`.
`make references` prints the Chromium references again: the headless Chromium of Playwright, in English,
with the fonts of `corpus/fonts`. Run it after adding an SVG or a font, and after a Playwright upgrade.

Each entry of `corpus/verdicts.json` names a reference: `chromium`, `resvg`, `both` where they agree,
or `browser` where headless Chromium matches no `systemLanguage`. `reference_why` says why one renderer
is wrong. `verdict` and `native_verdict` are `same`, `close` or `differs` against that reference, and
`what` and `native_what` say what differs. Judge at full size, zoomed in, never from a thumbnail.

## Pull requests

1. Branch from the default branch as `type/description`, for example `fix/empty-title`.
2. Keep one change per pull request. New behavior comes with tests; a bug fix adds a test that
   fails without it.
3. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/) without a
   scope: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`, `test: ...`, `build: ...`,
   `ci: ...`, `chore: ...`.
4. Sign your commits. The default branch accepts verified signatures only.
5. Add an entry under `## [Unreleased]` in `CHANGELOG.md`, written for users: the release notes
   quote it. Update the README when behavior or configuration changes.

Pull requests are squash-merged once all required checks are green.

## Releases

A maintainer runs the Bump Version workflow. It moves the Unreleased entries into a versioned
section, tags the release, and the Release workflow publishes it with signed build provenance.
