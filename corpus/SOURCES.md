# Corpus sources and licenses

The corpus is test data for the visual regression bench. It is not part of the weasysvg package.
Each file keeps the license of its source, listed below. The MIT license of this repository does not
cover these files.

The reference PNGs in `reference/` are renderings of the SVG of the same name. A rendering carries the
license and the attribution of its SVG. `make references` prints `reference/chromium/` again with the
headless Chromium of Playwright, in the visual image.

| Path | Files | Source | License |
|---|---|---|---|
| `svg/drawio/` | 6 | [jgraph/drawio-diagrams](https://github.com/jgraph/drawio-diagrams), `diagrams/`, commit `380ac88` | Apache-2.0, see [licenses/drawio-diagrams-LICENSE.txt](licenses/drawio-diagrams-LICENSE.txt) |
| `svg/resvg/` | 64 | [linebender/resvg](https://github.com/linebender/resvg) `crates/resvg/tests/tests/`, commit `054ccf3` | MIT (dual Apache-2.0 or MIT), see [licenses/resvg-LICENSE-MIT.txt](licenses/resvg-LICENSE-MIT.txt) |
| `reference/resvg/` | 64 | the reference PNGs of the same resvg tests | as above |
| `fonts/` | 9 | the fonts the resvg tests ask for, from `crates/resvg/tests/fonts/` of the same commit: Amiri, M+ 1p, Noto Sans (regular, bold, italic), Noto Serif, Noto Mono, Noto Sans Devanagari, Source Sans Pro | SIL Open Font License 1.1, see the license files next to them |
| `svg/diagrams/kroki-*` | 10 | rendered by [kroki.io](https://kroki.io) from diagram sources written for this corpus: `bpmn`, `excalidraw`, `d2-arch`, `svgbob`, `plantuml-sequence`, `plantuml-activity`, `graphviz`, `blockdiag`, `pikchr`, `structurizr` | MIT, as this repository |
| `svg/diagrams/mermaid-ink-*`, `svg/diagrams/kroki-mermaid-*` | 13 | rendered by [mermaid.ink](https://mermaid.ink) and kroki.io from examples of the Mermaid documentation (`packages/mermaid/src/docs/`), some shortened or extended | MIT, see [licenses/mermaid-LICENSE.txt](licenses/mermaid-LICENSE.txt) ([mermaid-js/mermaid](https://github.com/mermaid-js/mermaid) commit `6d8921f`) |
| `svg/diagrams/kroki-d2.svg` | 1 | kroki.io, from the first example of the D2 sequence diagram tour, [terrastruct/d2-docs](https://github.com/terrastruct/d2-docs) `static/d2/sequence-diagrams-1.d2`, commit `5530a5e` | BSD-3-Clause, see [licenses/d2-docs-LICENSE.txt](licenses/d2-docs-LICENSE.txt) |
| `svg/diagrams/kroki-c4plantuml.svg` | 1 | kroki.io, adapted from the basic sample of the [plantuml-stdlib/C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) README, commit `f998c46` | MIT, see [licenses/C4-PlantUML-LICENSE.txt](licenses/C4-PlantUML-LICENSE.txt) |
| `svg/diagrams/kroki-nomnoml.svg` | 1 | kroki.io, shortened from the Pirate sample of the nomnoml home page, [skanaar/nomnoml](https://github.com/skanaar/nomnoml) `index.html`, commit `acc00ce` | MIT, see [licenses/nomnoml-LICENSE.txt](licenses/nomnoml-LICENSE.txt) |
| `svg/diagrams/kroki-vegalite.svg` | 1 | kroki.io, shortened from the simple bar chart example, [vega/vega-lite](https://github.com/vega/vega-lite) `examples/specs/bar.vl.json`, commit `85fab8d` | BSD-3-Clause, see [licenses/vega-lite-LICENSE.txt](licenses/vega-lite-LICENSE.txt) |
| `svg/diagrams/kroki-wavedrom.svg` | 1 | kroki.io, shortened from the WaveDrom tutorial, [wavedrom/wavedrom.github.io](https://github.com/wavedrom/wavedrom.github.io) `tutorial.html`, commit `41b69e3` | MIT, see [licenses/wavedrom.github.io-LICENSE.txt](licenses/wavedrom.github.io-LICENSE.txt) |
| `svg/diagrams/kroki-erd.svg` | 1 | kroki.io, from the example of [BurntSushi/erd](https://github.com/BurntSushi/erd) `erd.cabal`, without the `state` column, commit `d18075d` | Unlicense, which requires no notice |
| `svg/fo/mdn-foreignobject.svg` | 1 | the `<foreignObject>` example of [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/foreignObject) | CC0-1.0 (MDN code samples) |
| `svg/fo/rich-html.svg` | 1 | written for this corpus | MIT, as this repository |
| `svg/text/monospace-default-size.svg` | 1 | written for this corpus | MIT, as this repository |
| `svg/real/wm-*` | 14 | Wikimedia Commons, one file each, see below | per file |

Fonts embedded by the generators: the D2 diagrams (`kroki-d2*`) carry subsets of Source Sans Pro, and
the Excalidraw diagram carries Virgil. Both fonts are under the SIL Open Font License 1.1, which allows
bundling them with other files when the copyright notice and the license come along. Subsetting can drop
both from the font, so they are here:

- Source Sans Pro: Copyright 2010-2024 Adobe, with Reserved Font Name 'Source'. See
  [licenses/SourceSansPro-OFL.txt](licenses/SourceSansPro-OFL.txt), from
  [adobe-fonts/source-sans](https://github.com/adobe-fonts/source-sans) commit `87b37a2`.
- Virgil: Copyright (c) 2021 - Present, Ellinor Rapp, with Reserved Font Name Virgil. See
  [licenses/Virgil-OFL.txt](licenses/Virgil-OFL.txt), from
  [excalidraw/virgil](https://github.com/excalidraw/virgil) commit `3d4c829`.

## Wikimedia Commons

The files are unchanged copies. The SHA-1 of each file matches the current version on Commons
(checked 2026-10-19). Each name is `wm-` plus the Commons file name.

| File | Author | License |
|---|---|---|
| [Bitmap VS SVG.svg](https://commons.wikimedia.org/wiki/File:Bitmap_VS_SVG.svg) | Yug, modifications by Cfaerber et al. | [CC BY-SA 2.5](https://creativecommons.org/licenses/by-sa/2.5) |
| [Flag of Brazil.svg](https://commons.wikimedia.org/wiki/File:Flag_of_Brazil.svg) | Raimundo Teixeira Mendes | Public domain |
| [Flag of Switzerland.svg](https://commons.wikimedia.org/wiki/File:Flag_of_Switzerland.svg) | vector: Marc Mongenet; credits: -xfi-, Zscout370 | Public domain |
| [Flag of the United Kingdom.svg](https://commons.wikimedia.org/wiki/File:Flag_of_the_United_Kingdom.svg) | vector: Yaddah | Public domain |
| [Git-logo.svg](https://commons.wikimedia.org/wiki/File:Git-logo.svg) | Jason Long | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) |
| [Inkscape Logo.svg](https://commons.wikimedia.org/wiki/File:Inkscape_Logo.svg) | Andrew Michael Fitzsimon | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) |
| [Kubernetes logo without workmark.svg](https://commons.wikimedia.org/wiki/File:Kubernetes_logo_without_workmark.svg) | Google, Inc. | Public domain |
| [OSI Model v1.svg](https://commons.wikimedia.org/wiki/File:OSI_Model_v1.svg) | Offnfopt | Public domain |
| [Openstreetmap logo.svg](https://commons.wikimedia.org/wiki/File:Openstreetmap_logo.svg) | Ken Vermette, based on OpenStreetMap-Logo-2006.svg | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) |
| [Python-logo-notext.svg](https://commons.wikimedia.org/wiki/File:Python-logo-notext.svg) | www.python.org | Public domain |
| [SVG Logo.svg](https://commons.wikimedia.org/wiki/File:SVG_Logo.svg) | W3C SVG Logo, designer Harvey Rayner | Public domain, attribution requested |
| [Simple Periodic Table Chart-blocks.svg](https://commons.wikimedia.org/wiki/File:Simple_Periodic_Table_Chart-blocks.svg) | Double sharp, based on Simple Periodic Table Chart-en.svg by Offnfopt | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| [Tux.svg](https://commons.wikimedia.org/wiki/File:Tux.svg) | Larry Ewing (lewing@isc.tamu.edu) and The GIMP, Simon Budig, Garrett LeSage | Free with attribution; the notice of Simon Budig is in [licenses/Tux-README.txt](licenses/Tux-README.txt) |
| [Wikimedia-logo.svg](https://commons.wikimedia.org/wiki/File:Wikimedia-logo.svg) | Zscout370, modifications by Dbenbenn; logo design by Neolux | Public domain |

Several of these files are logos. Their trademarks stay with their owners; the corpus uses them as test
images only.

## Left out

- `Docker container engine logo.svg`: the file is gone from Wikimedia Commons, so its license cannot be
  checked.
- `Ghostscript Tiger.svg`: AGPL. A copyleft license is more than "redistribution with attribution".
