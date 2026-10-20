# Corpus comparison

<!-- Written by make comparison (tools/visual/comparison.py). Do not edit by hand. -->

Each SVG of the corpus in four renderings: Chromium; resvg (resvg-py 0.5.0); WeasyPrint 70.0 alone; and WeasyPrint 70.0 with weasysvg. The WeasyPrint panels are PDFium rasterizations at 96 dpi; resvg renders the SVG at the width of the page. Every panel is cropped to the ink of the Chromium panel, so the four line up pixel for pixel. Each SVG has a reference: Chromium, resvg, both, or an English browser where headless Chromium matches no language. The verdicts compare weasysvg and WeasyPrint with that reference; they come from a visual review at full size, see [`verdicts.json`](verdicts.json). Click a panel for its full size. The interactive page, with large panels, your own browser and a swipe between renderers: <https://grigoriev.github.io/weasysvg/corpus/comparison.html>.

| Verdict | WeasyPrint 70.0 | WeasyPrint 70.0 with weasysvg |
|---|---|---|
| ⬆️ better than the reference | 0 | 1 |
| ✅ matches the reference | 41 | 108 |
| 🟡 close to the reference | 20 | 5 |
| ❌ differs from the reference | 54 | 1 |

References: Chromium 34, resvg 7, Chromium and resvg 73, an English browser 1.

- [Diagrams from kroki and mermaid.ink](#diagrams-from-kroki-and-mermaidink) (29)
- [draw.io](#drawio) (6)
- [foreignObject](#foreignobject) (2)
- [Wikimedia Commons](#wikimedia-commons) (14)
- [resvg feature tests](#resvg-feature-tests) (64)

## Diagrams from kroki and mermaid.ink

### diagrams__kroki-blockdiag

[`diagrams/kroki-blockdiag.svg`](svg/diagrams/kroki-blockdiag.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: boxes, arrows and the blurred shadows. |
| 🟡 | WeasyPrint | **close to the reference** | Shadows are hard offset copies instead of blurred ones. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-blockdiag.png"><img src="render/chromium/diagrams__kroki-blockdiag.png" width="200" alt="diagrams__kroki-blockdiag in Chromium"></a> | <a href="render/resvg/diagrams__kroki-blockdiag.png"><img src="render/resvg/diagrams__kroki-blockdiag.png" width="200" alt="diagrams__kroki-blockdiag in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-blockdiag.png"><img src="render/weasyprint/diagrams__kroki-blockdiag.png" width="200" alt="diagrams__kroki-blockdiag in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-blockdiag.png"><img src="render/weasysvg/diagrams__kroki-blockdiag.png" width="200" alt="diagrams__kroki-blockdiag in weasysvg"></a> |

### diagrams__kroki-bpmn

[`diagrams/kroki-bpmn.svg`](svg/diagrams/kroki-bpmn.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-bpmn.png"><img src="render/chromium/diagrams__kroki-bpmn.png" width="200" alt="diagrams__kroki-bpmn in Chromium"></a> | <a href="render/resvg/diagrams__kroki-bpmn.png"><img src="render/resvg/diagrams__kroki-bpmn.png" width="200" alt="diagrams__kroki-bpmn in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-bpmn.png"><img src="render/weasyprint/diagrams__kroki-bpmn.png" width="200" alt="diagrams__kroki-bpmn in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-bpmn.png"><img src="render/weasysvg/diagrams__kroki-bpmn.png" width="200" alt="diagrams__kroki-bpmn in weasysvg"></a> |

### diagrams__kroki-c4plantuml

[`diagrams/kroki-c4plantuml.svg`](svg/diagrams/kroki-c4plantuml.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches, fonts included. |
| 🟡 | WeasyPrint | **close to the reference** | Same drawing in another font. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-c4plantuml.png"><img src="render/chromium/diagrams__kroki-c4plantuml.png" width="200" alt="diagrams__kroki-c4plantuml in Chromium"></a> | <a href="render/resvg/diagrams__kroki-c4plantuml.png"><img src="render/resvg/diagrams__kroki-c4plantuml.png" width="200" alt="diagrams__kroki-c4plantuml in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-c4plantuml.png"><img src="render/weasyprint/diagrams__kroki-c4plantuml.png" width="200" alt="diagrams__kroki-c4plantuml in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-c4plantuml.png"><img src="render/weasysvg/diagrams__kroki-c4plantuml.png" width="200" alt="diagrams__kroki-c4plantuml in weasysvg"></a> |

### diagrams__kroki-d2-arch

[`diagrams/kroki-d2-arch.svg`](svg/diagrams/kroki-d2-arch.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg ignores the @font-face fonts the SVG embeds and falls back to a serif. |
| ✅ | weasysvg | **matches the reference** | Matches, with the embedded fonts. |
| ❌ | WeasyPrint | **differs from the reference** | Nothing but a black rectangle: the SVG is lost. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-d2-arch.png"><img src="render/chromium/diagrams__kroki-d2-arch.png" width="200" alt="diagrams__kroki-d2-arch in Chromium"></a> | <a href="render/resvg/diagrams__kroki-d2-arch.png"><img src="render/resvg/diagrams__kroki-d2-arch.png" width="200" alt="diagrams__kroki-d2-arch in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-d2-arch.png"><img src="render/weasyprint/diagrams__kroki-d2-arch.png" width="200" alt="diagrams__kroki-d2-arch in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-d2-arch.png"><img src="render/weasysvg/diagrams__kroki-d2-arch.png" width="200" alt="diagrams__kroki-d2-arch in weasysvg"></a> |

### diagrams__kroki-d2

[`diagrams/kroki-d2.svg`](svg/diagrams/kroki-d2.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg ignores the embedded @font-face fonts. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | Two black bars instead of the diagram. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-d2.png"><img src="render/chromium/diagrams__kroki-d2.png" width="200" alt="diagrams__kroki-d2 in Chromium"></a> | <a href="render/resvg/diagrams__kroki-d2.png"><img src="render/resvg/diagrams__kroki-d2.png" width="200" alt="diagrams__kroki-d2 in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-d2.png"><img src="render/weasyprint/diagrams__kroki-d2.png" width="200" alt="diagrams__kroki-d2 in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-d2.png"><img src="render/weasysvg/diagrams__kroki-d2.png" width="200" alt="diagrams__kroki-d2 in weasysvg"></a> |

### diagrams__kroki-erd

[`diagrams/kroki-erd.svg`](svg/diagrams/kroki-erd.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg draws the sans-serif labels in a serif. |
| ✅ | weasysvg | **matches the reference** | Matches, underlined keys included. |
| 🟡 | WeasyPrint | **close to the reference** | The key fields name and id lose their underline; the font differs. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-erd.png"><img src="render/chromium/diagrams__kroki-erd.png" width="200" alt="diagrams__kroki-erd in Chromium"></a> | <a href="render/resvg/diagrams__kroki-erd.png"><img src="render/resvg/diagrams__kroki-erd.png" width="200" alt="diagrams__kroki-erd in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-erd.png"><img src="render/weasyprint/diagrams__kroki-erd.png" width="200" alt="diagrams__kroki-erd in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-erd.png"><img src="render/weasysvg/diagrams__kroki-erd.png" width="200" alt="diagrams__kroki-erd in weasysvg"></a> |

### diagrams__kroki-excalidraw

[`diagrams/kroki-excalidraw.svg`](svg/diagrams/kroki-excalidraw.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg ignores the embedded hand-drawn font. |
| ✅ | weasysvg | **matches the reference** | Matches, hand-drawn font included. |
| 🟡 | WeasyPrint | **close to the reference** | Wider gap between the words. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-excalidraw.png"><img src="render/chromium/diagrams__kroki-excalidraw.png" width="200" alt="diagrams__kroki-excalidraw in Chromium"></a> | <a href="render/resvg/diagrams__kroki-excalidraw.png"><img src="render/resvg/diagrams__kroki-excalidraw.png" width="200" alt="diagrams__kroki-excalidraw in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-excalidraw.png"><img src="render/weasyprint/diagrams__kroki-excalidraw.png" width="200" alt="diagrams__kroki-excalidraw in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-excalidraw.png"><img src="render/weasysvg/diagrams__kroki-excalidraw.png" width="200" alt="diagrams__kroki-excalidraw in weasysvg"></a> |

### diagrams__kroki-graphviz

[`diagrams/kroki-graphviz.svg`](svg/diagrams/kroki-graphviz.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| 🟡 | WeasyPrint | **close to the reference** | Same drawing in another font. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-graphviz.png"><img src="render/chromium/diagrams__kroki-graphviz.png" width="200" alt="diagrams__kroki-graphviz in Chromium"></a> | <a href="render/resvg/diagrams__kroki-graphviz.png"><img src="render/resvg/diagrams__kroki-graphviz.png" width="200" alt="diagrams__kroki-graphviz in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-graphviz.png"><img src="render/weasyprint/diagrams__kroki-graphviz.png" width="200" alt="diagrams__kroki-graphviz in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-graphviz.png"><img src="render/weasysvg/diagrams__kroki-graphviz.png" width="200" alt="diagrams__kroki-graphviz in weasysvg"></a> |

### diagrams__kroki-mermaid-er

[`diagrams/kroki-mermaid-er.svg`](svg/diagrams/kroki-mermaid-er.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: every label is missing. |
| ✅ | weasysvg | **matches the reference** | Matches, labels included. |
| ❌ | WeasyPrint | **differs from the reference** | All labels are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-mermaid-er.png"><img src="render/chromium/diagrams__kroki-mermaid-er.png" width="200" alt="diagrams__kroki-mermaid-er in Chromium"></a> | <a href="render/resvg/diagrams__kroki-mermaid-er.png"><img src="render/resvg/diagrams__kroki-mermaid-er.png" width="200" alt="diagrams__kroki-mermaid-er in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-mermaid-er.png"><img src="render/weasyprint/diagrams__kroki-mermaid-er.png" width="200" alt="diagrams__kroki-mermaid-er in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-mermaid-er.png"><img src="render/weasysvg/diagrams__kroki-mermaid-er.png" width="200" alt="diagrams__kroki-mermaid-er in weasysvg"></a> |

### diagrams__kroki-mermaid-mindmap

[`diagrams/kroki-mermaid-mindmap.svg`](svg/diagrams/kroki-mermaid-mindmap.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: every label is missing. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | All labels are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-mermaid-mindmap.png"><img src="render/chromium/diagrams__kroki-mermaid-mindmap.png" width="200" alt="diagrams__kroki-mermaid-mindmap in Chromium"></a> | <a href="render/resvg/diagrams__kroki-mermaid-mindmap.png"><img src="render/resvg/diagrams__kroki-mermaid-mindmap.png" width="200" alt="diagrams__kroki-mermaid-mindmap in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-mermaid-mindmap.png"><img src="render/weasyprint/diagrams__kroki-mermaid-mindmap.png" width="200" alt="diagrams__kroki-mermaid-mindmap in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-mermaid-mindmap.png"><img src="render/weasysvg/diagrams__kroki-mermaid-mindmap.png" width="200" alt="diagrams__kroki-mermaid-mindmap in weasysvg"></a> |

### diagrams__kroki-mermaid-state

[`diagrams/kroki-mermaid-state.svg`](svg/diagrams/kroki-mermaid-state.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: every label is missing. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | All labels are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-mermaid-state.png"><img src="render/chromium/diagrams__kroki-mermaid-state.png" width="200" alt="diagrams__kroki-mermaid-state in Chromium"></a> | <a href="render/resvg/diagrams__kroki-mermaid-state.png"><img src="render/resvg/diagrams__kroki-mermaid-state.png" width="200" alt="diagrams__kroki-mermaid-state in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-mermaid-state.png"><img src="render/weasyprint/diagrams__kroki-mermaid-state.png" width="200" alt="diagrams__kroki-mermaid-state in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-mermaid-state.png"><img src="render/weasysvg/diagrams__kroki-mermaid-state.png" width="200" alt="diagrams__kroki-mermaid-state in weasysvg"></a> |

### diagrams__kroki-nomnoml

[`diagrams/kroki-nomnoml.svg`](svg/diagrams/kroki-nomnoml.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg draws no text at all here. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-nomnoml.png"><img src="render/chromium/diagrams__kroki-nomnoml.png" width="200" alt="diagrams__kroki-nomnoml in Chromium"></a> | <a href="render/resvg/diagrams__kroki-nomnoml.png"><img src="render/resvg/diagrams__kroki-nomnoml.png" width="200" alt="diagrams__kroki-nomnoml in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-nomnoml.png"><img src="render/weasyprint/diagrams__kroki-nomnoml.png" width="200" alt="diagrams__kroki-nomnoml in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-nomnoml.png"><img src="render/weasysvg/diagrams__kroki-nomnoml.png" width="200" alt="diagrams__kroki-nomnoml in weasysvg"></a> |

### diagrams__kroki-pikchr

[`diagrams/kroki-pikchr.svg`](svg/diagrams/kroki-pikchr.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | All text is missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-pikchr.png"><img src="render/chromium/diagrams__kroki-pikchr.png" width="200" alt="diagrams__kroki-pikchr in Chromium"></a> | <a href="render/resvg/diagrams__kroki-pikchr.png"><img src="render/resvg/diagrams__kroki-pikchr.png" width="200" alt="diagrams__kroki-pikchr in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-pikchr.png"><img src="render/weasyprint/diagrams__kroki-pikchr.png" width="200" alt="diagrams__kroki-pikchr in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-pikchr.png"><img src="render/weasysvg/diagrams__kroki-pikchr.png" width="200" alt="diagrams__kroki-pikchr in weasysvg"></a> |

### diagrams__kroki-plantuml-activity

[`diagrams/kroki-plantuml-activity.svg`](svg/diagrams/kroki-plantuml-activity.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg draws the underline under &#x27;waiting&#x27; through the descenders; Chromium skips their ink. |
| 🟡 | weasysvg | **close to the reference** | The underline under &#x27;waiting&#x27; runs whole: the text has a textLength, so it is laid out character by character and skips no ink. Chromium cuts it under each glyph. |
| 🟡 | WeasyPrint | **close to the reference** | The underline under &#x27;waiting&#x27; is missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-plantuml-activity.png"><img src="render/chromium/diagrams__kroki-plantuml-activity.png" width="200" alt="diagrams__kroki-plantuml-activity in Chromium"></a> | <a href="render/resvg/diagrams__kroki-plantuml-activity.png"><img src="render/resvg/diagrams__kroki-plantuml-activity.png" width="200" alt="diagrams__kroki-plantuml-activity in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-plantuml-activity.png"><img src="render/weasyprint/diagrams__kroki-plantuml-activity.png" width="200" alt="diagrams__kroki-plantuml-activity in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-plantuml-activity.png"><img src="render/weasysvg/diagrams__kroki-plantuml-activity.png" width="200" alt="diagrams__kroki-plantuml-activity in weasysvg"></a> |

### diagrams__kroki-plantuml-sequence

[`diagrams/kroki-plantuml-sequence.svg`](svg/diagrams/kroki-plantuml-sequence.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-plantuml-sequence.png"><img src="render/chromium/diagrams__kroki-plantuml-sequence.png" width="200" alt="diagrams__kroki-plantuml-sequence in Chromium"></a> | <a href="render/resvg/diagrams__kroki-plantuml-sequence.png"><img src="render/resvg/diagrams__kroki-plantuml-sequence.png" width="200" alt="diagrams__kroki-plantuml-sequence in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-plantuml-sequence.png"><img src="render/weasyprint/diagrams__kroki-plantuml-sequence.png" width="200" alt="diagrams__kroki-plantuml-sequence in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-plantuml-sequence.png"><img src="render/weasysvg/diagrams__kroki-plantuml-sequence.png" width="200" alt="diagrams__kroki-plantuml-sequence in weasysvg"></a> |

### diagrams__kroki-structurizr

[`diagrams/kroki-structurizr.svg`](svg/diagrams/kroki-structurizr.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-structurizr.png"><img src="render/chromium/diagrams__kroki-structurizr.png" width="200" alt="diagrams__kroki-structurizr in Chromium"></a> | <a href="render/resvg/diagrams__kroki-structurizr.png"><img src="render/resvg/diagrams__kroki-structurizr.png" width="200" alt="diagrams__kroki-structurizr in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-structurizr.png"><img src="render/weasyprint/diagrams__kroki-structurizr.png" width="200" alt="diagrams__kroki-structurizr in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-structurizr.png"><img src="render/weasysvg/diagrams__kroki-structurizr.png" width="200" alt="diagrams__kroki-structurizr in weasysvg"></a> |

### diagrams__kroki-svgbob

[`diagrams/kroki-svgbob.svg`](svg/diagrams/kroki-svgbob.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-svgbob.png"><img src="render/chromium/diagrams__kroki-svgbob.png" width="200" alt="diagrams__kroki-svgbob in Chromium"></a> | <a href="render/resvg/diagrams__kroki-svgbob.png"><img src="render/resvg/diagrams__kroki-svgbob.png" width="200" alt="diagrams__kroki-svgbob in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-svgbob.png"><img src="render/weasyprint/diagrams__kroki-svgbob.png" width="200" alt="diagrams__kroki-svgbob in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-svgbob.png"><img src="render/weasysvg/diagrams__kroki-svgbob.png" width="200" alt="diagrams__kroki-svgbob in weasysvg"></a> |

### diagrams__kroki-vegalite

[`diagrams/kroki-vegalite.svg`](svg/diagrams/kroki-vegalite.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-vegalite.png"><img src="render/chromium/diagrams__kroki-vegalite.png" width="200" alt="diagrams__kroki-vegalite in Chromium"></a> | <a href="render/resvg/diagrams__kroki-vegalite.png"><img src="render/resvg/diagrams__kroki-vegalite.png" width="200" alt="diagrams__kroki-vegalite in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-vegalite.png"><img src="render/weasyprint/diagrams__kroki-vegalite.png" width="200" alt="diagrams__kroki-vegalite in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-vegalite.png"><img src="render/weasysvg/diagrams__kroki-vegalite.png" width="200" alt="diagrams__kroki-vegalite in weasysvg"></a> |

### diagrams__kroki-wavedrom

[`diagrams/kroki-wavedrom.svg`](svg/diagrams/kroki-wavedrom.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg drops the lane labels and the fills of the data cells. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-wavedrom.png"><img src="render/chromium/diagrams__kroki-wavedrom.png" width="200" alt="diagrams__kroki-wavedrom in Chromium"></a> | <a href="render/resvg/diagrams__kroki-wavedrom.png"><img src="render/resvg/diagrams__kroki-wavedrom.png" width="200" alt="diagrams__kroki-wavedrom in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-wavedrom.png"><img src="render/weasyprint/diagrams__kroki-wavedrom.png" width="200" alt="diagrams__kroki-wavedrom in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-wavedrom.png"><img src="render/weasysvg/diagrams__kroki-wavedrom.png" width="200" alt="diagrams__kroki-wavedrom in weasysvg"></a> |

### diagrams__mermaid-ink-class

[`diagrams/mermaid-ink-class.svg`](svg/diagrams/mermaid-ink-class.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: every label is missing. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | All labels are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-class.png"><img src="render/chromium/diagrams__mermaid-ink-class.png" width="200" alt="diagrams__mermaid-ink-class in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-class.png"><img src="render/resvg/diagrams__mermaid-ink-class.png" width="200" alt="diagrams__mermaid-ink-class in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-class.png"><img src="render/weasyprint/diagrams__mermaid-ink-class.png" width="200" alt="diagrams__mermaid-ink-class in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-class.png"><img src="render/weasysvg/diagrams__mermaid-ink-class.png" width="200" alt="diagrams__mermaid-ink-class in weasysvg"></a> |

### diagrams__mermaid-ink-er

[`diagrams/mermaid-ink-er.svg`](svg/diagrams/mermaid-ink-er.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: every label is missing. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | All labels are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-er.png"><img src="render/chromium/diagrams__mermaid-ink-er.png" width="200" alt="diagrams__mermaid-ink-er in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-er.png"><img src="render/resvg/diagrams__mermaid-ink-er.png" width="200" alt="diagrams__mermaid-ink-er in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-er.png"><img src="render/weasyprint/diagrams__mermaid-ink-er.png" width="200" alt="diagrams__mermaid-ink-er in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-er.png"><img src="render/weasysvg/diagrams__mermaid-ink-er.png" width="200" alt="diagrams__mermaid-ink-er in weasysvg"></a> |

### diagrams__mermaid-ink-flowchart

[`diagrams/mermaid-ink-flowchart.svg`](svg/diagrams/mermaid-ink-flowchart.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: every label is missing. |
| 🟡 | weasysvg | **close to the reference** | The label Car sits 3 px right of where Chromium puts it; the rest matches. |
| ❌ | WeasyPrint | **differs from the reference** | All labels are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-flowchart.png"><img src="render/chromium/diagrams__mermaid-ink-flowchart.png" width="200" alt="diagrams__mermaid-ink-flowchart in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-flowchart.png"><img src="render/resvg/diagrams__mermaid-ink-flowchart.png" width="200" alt="diagrams__mermaid-ink-flowchart in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-flowchart.png"><img src="render/weasyprint/diagrams__mermaid-ink-flowchart.png" width="200" alt="diagrams__mermaid-ink-flowchart in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-flowchart.png"><img src="render/weasysvg/diagrams__mermaid-ink-flowchart.png" width="200" alt="diagrams__mermaid-ink-flowchart in weasysvg"></a> |

### diagrams__mermaid-ink-gantt

[`diagrams/mermaid-ink-gantt.svg`](svg/diagrams/mermaid-ink-gantt.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| 🟡 | WeasyPrint | **close to the reference** | The axis dates lose their year: 01-05 instead of 2014-01-05. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-gantt.png"><img src="render/chromium/diagrams__mermaid-ink-gantt.png" width="200" alt="diagrams__mermaid-ink-gantt in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-gantt.png"><img src="render/resvg/diagrams__mermaid-ink-gantt.png" width="200" alt="diagrams__mermaid-ink-gantt in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-gantt.png"><img src="render/weasyprint/diagrams__mermaid-ink-gantt.png" width="200" alt="diagrams__mermaid-ink-gantt in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-gantt.png"><img src="render/weasysvg/diagrams__mermaid-ink-gantt.png" width="200" alt="diagrams__mermaid-ink-gantt in weasysvg"></a> |

### diagrams__mermaid-ink-gitgraph

[`diagrams/mermaid-ink-gitgraph.svg`](svg/diagrams/mermaid-ink-gitgraph.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-gitgraph.png"><img src="render/chromium/diagrams__mermaid-ink-gitgraph.png" width="200" alt="diagrams__mermaid-ink-gitgraph in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-gitgraph.png"><img src="render/resvg/diagrams__mermaid-ink-gitgraph.png" width="200" alt="diagrams__mermaid-ink-gitgraph in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-gitgraph.png"><img src="render/weasyprint/diagrams__mermaid-ink-gitgraph.png" width="200" alt="diagrams__mermaid-ink-gitgraph in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-gitgraph.png"><img src="render/weasysvg/diagrams__mermaid-ink-gitgraph.png" width="200" alt="diagrams__mermaid-ink-gitgraph in weasysvg"></a> |

### diagrams__mermaid-ink-journey

[`diagrams/mermaid-ink-journey.svg`](svg/diagrams/mermaid-ink-journey.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | The title has fill=&quot;&quot;, which browsers ignore: it takes #333 from the CSS of the root, as in Chromium. resvg draws it black. |
| ✅ | weasysvg | **matches the reference** | Matches, the title sized 4ex from the x-height of the font, as in Chromium. |
| ❌ | WeasyPrint | **differs from the reference** | The title, with fill=&quot;&quot;, and the labels of the two sections are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-journey.png"><img src="render/chromium/diagrams__mermaid-ink-journey.png" width="200" alt="diagrams__mermaid-ink-journey in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-journey.png"><img src="render/resvg/diagrams__mermaid-ink-journey.png" width="200" alt="diagrams__mermaid-ink-journey in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-journey.png"><img src="render/weasyprint/diagrams__mermaid-ink-journey.png" width="200" alt="diagrams__mermaid-ink-journey in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-journey.png"><img src="render/weasysvg/diagrams__mermaid-ink-journey.png" width="200" alt="diagrams__mermaid-ink-journey in weasysvg"></a> |

### diagrams__mermaid-ink-mindmap

[`diagrams/mermaid-ink-mindmap.svg`](svg/diagrams/mermaid-ink-mindmap.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: every label is missing. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | All labels are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-mindmap.png"><img src="render/chromium/diagrams__mermaid-ink-mindmap.png" width="200" alt="diagrams__mermaid-ink-mindmap in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-mindmap.png"><img src="render/resvg/diagrams__mermaid-ink-mindmap.png" width="200" alt="diagrams__mermaid-ink-mindmap in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-mindmap.png"><img src="render/weasyprint/diagrams__mermaid-ink-mindmap.png" width="200" alt="diagrams__mermaid-ink-mindmap in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-mindmap.png"><img src="render/weasysvg/diagrams__mermaid-ink-mindmap.png" width="200" alt="diagrams__mermaid-ink-mindmap in weasysvg"></a> |

### diagrams__mermaid-ink-pie

[`diagrams/mermaid-ink-pie.svg`](svg/diagrams/mermaid-ink-pie.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-pie.png"><img src="render/chromium/diagrams__mermaid-ink-pie.png" width="200" alt="diagrams__mermaid-ink-pie in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-pie.png"><img src="render/resvg/diagrams__mermaid-ink-pie.png" width="200" alt="diagrams__mermaid-ink-pie in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-pie.png"><img src="render/weasyprint/diagrams__mermaid-ink-pie.png" width="200" alt="diagrams__mermaid-ink-pie in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-pie.png"><img src="render/weasysvg/diagrams__mermaid-ink-pie.png" width="200" alt="diagrams__mermaid-ink-pie in weasysvg"></a> |

### diagrams__mermaid-ink-sequence

[`diagrams/mermaid-ink-sequence.svg`](svg/diagrams/mermaid-ink-sequence.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-sequence.png"><img src="render/chromium/diagrams__mermaid-ink-sequence.png" width="200" alt="diagrams__mermaid-ink-sequence in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-sequence.png"><img src="render/resvg/diagrams__mermaid-ink-sequence.png" width="200" alt="diagrams__mermaid-ink-sequence in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-sequence.png"><img src="render/weasyprint/diagrams__mermaid-ink-sequence.png" width="200" alt="diagrams__mermaid-ink-sequence in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-sequence.png"><img src="render/weasysvg/diagrams__mermaid-ink-sequence.png" width="200" alt="diagrams__mermaid-ink-sequence in weasysvg"></a> |

### diagrams__mermaid-ink-state

[`diagrams/mermaid-ink-state.svg`](svg/diagrams/mermaid-ink-state.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: every label is missing. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | All labels are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-state.png"><img src="render/chromium/diagrams__mermaid-ink-state.png" width="200" alt="diagrams__mermaid-ink-state in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-state.png"><img src="render/resvg/diagrams__mermaid-ink-state.png" width="200" alt="diagrams__mermaid-ink-state in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-state.png"><img src="render/weasyprint/diagrams__mermaid-ink-state.png" width="200" alt="diagrams__mermaid-ink-state in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-state.png"><img src="render/weasysvg/diagrams__mermaid-ink-state.png" width="200" alt="diagrams__mermaid-ink-state in weasysvg"></a> |

## draw.io

### drawio__connect-shapes

[`drawio/connect-shapes.svg`](svg/drawio/connect-shapes.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg draws the labels in a serif. |
| ✅ | weasysvg | **matches the reference** | Matches, the underlines of the links skip the ink as in Chromium. The remote GIFs are blocked in every rendering, by policy. |
| 🟡 | WeasyPrint | **close to the reference** | The links lose their underline. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__connect-shapes.png"><img src="render/chromium/drawio__connect-shapes.png" width="200" alt="drawio__connect-shapes in Chromium"></a> | <a href="render/resvg/drawio__connect-shapes.png"><img src="render/resvg/drawio__connect-shapes.png" width="200" alt="drawio__connect-shapes in resvg"></a> | <a href="render/weasyprint/drawio__connect-shapes.png"><img src="render/weasyprint/drawio__connect-shapes.png" width="200" alt="drawio__connect-shapes in WeasyPrint"></a> | <a href="render/weasysvg/drawio__connect-shapes.png"><img src="render/weasysvg/drawio__connect-shapes.png" width="200" alt="drawio__connect-shapes in weasysvg"></a> |

### drawio__flowchart.drawio

[`drawio/flowchart.drawio.svg`](svg/drawio/flowchart.drawio.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg ignores the switch with requiredFeatures and shows the fallback text &#x27;Text is not SVG&#x27;. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | Labels are cut to &#x27;Lamp...&#x27; and the fallback text &#x27;Text is not SVG&#x27; shows. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__flowchart.drawio.png"><img src="render/chromium/drawio__flowchart.drawio.png" width="200" alt="drawio__flowchart.drawio in Chromium"></a> | <a href="render/resvg/drawio__flowchart.drawio.png"><img src="render/resvg/drawio__flowchart.drawio.png" width="200" alt="drawio__flowchart.drawio in resvg"></a> | <a href="render/weasyprint/drawio__flowchart.drawio.png"><img src="render/weasyprint/drawio__flowchart.drawio.png" width="200" alt="drawio__flowchart.drawio in WeasyPrint"></a> | <a href="render/weasysvg/drawio__flowchart.drawio.png"><img src="render/weasysvg/drawio__flowchart.drawio.png" width="200" alt="drawio__flowchart.drawio in weasysvg"></a> |

### drawio__infographic

[`drawio/infographic.svg`](svg/drawio/infographic.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg shows raw HTML source in place of the foreignObject text. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | Most text is missing, raw HTML shows. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__infographic.png"><img src="render/chromium/drawio__infographic.png" width="200" alt="drawio__infographic in Chromium"></a> | <a href="render/resvg/drawio__infographic.png"><img src="render/resvg/drawio__infographic.png" width="200" alt="drawio__infographic in resvg"></a> | <a href="render/weasyprint/drawio__infographic.png"><img src="render/weasyprint/drawio__infographic.png" width="200" alt="drawio__infographic in WeasyPrint"></a> | <a href="render/weasysvg/drawio__infographic.png"><img src="render/weasysvg/drawio__infographic.png" width="200" alt="drawio__infographic in weasysvg"></a> |

### drawio__infographic2

[`drawio/infographic2.svg`](svg/drawio/infographic2.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg shows &#x27;Not supported by viewer&#x27; fallbacks. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | &#x27;Not supported by viewer&#x27; fallbacks show in large orange type. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__infographic2.png"><img src="render/chromium/drawio__infographic2.png" width="200" alt="drawio__infographic2 in Chromium"></a> | <a href="render/resvg/drawio__infographic2.png"><img src="render/resvg/drawio__infographic2.png" width="200" alt="drawio__infographic2 in resvg"></a> | <a href="render/weasyprint/drawio__infographic2.png"><img src="render/weasyprint/drawio__infographic2.png" width="200" alt="drawio__infographic2 in WeasyPrint"></a> | <a href="render/weasysvg/drawio__infographic2.png"><img src="render/weasysvg/drawio__infographic2.png" width="200" alt="drawio__infographic2 in weasysvg"></a> |

### drawio__notion-template.drawio

[`drawio/notion-template.drawio.svg`](svg/drawio/notion-template.drawio.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg shows the fallback &#x27;Click Here to...&#x27;. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | Shows the fallback &#x27;Click Here to...&#x27;. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__notion-template.drawio.png"><img src="render/chromium/drawio__notion-template.drawio.png" width="200" alt="drawio__notion-template.drawio in Chromium"></a> | <a href="render/resvg/drawio__notion-template.drawio.png"><img src="render/resvg/drawio__notion-template.drawio.png" width="200" alt="drawio__notion-template.drawio in resvg"></a> | <a href="render/weasyprint/drawio__notion-template.drawio.png"><img src="render/weasyprint/drawio__notion-template.drawio.png" width="200" alt="drawio__notion-template.drawio in WeasyPrint"></a> | <a href="render/weasysvg/drawio__notion-template.drawio.png"><img src="render/weasysvg/drawio__notion-template.drawio.png" width="200" alt="drawio__notion-template.drawio in weasysvg"></a> |

### drawio__svgfile

[`drawio/svgfile.svg`](svg/drawio/svgfile.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg shows &#x27;Not supported by viewer&#x27; fallbacks. |
| 🟡 | weasysvg | **close to the reference** | One AsciiMath label breaks its line at another word. |
| ❌ | WeasyPrint | **differs from the reference** | Fallback texts in place of the labels. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__svgfile.png"><img src="render/chromium/drawio__svgfile.png" width="200" alt="drawio__svgfile in Chromium"></a> | <a href="render/resvg/drawio__svgfile.png"><img src="render/resvg/drawio__svgfile.png" width="200" alt="drawio__svgfile in resvg"></a> | <a href="render/weasyprint/drawio__svgfile.png"><img src="render/weasyprint/drawio__svgfile.png" width="200" alt="drawio__svgfile in WeasyPrint"></a> | <a href="render/weasysvg/drawio__svgfile.png"><img src="render/weasysvg/drawio__svgfile.png" width="200" alt="drawio__svgfile in weasysvg"></a> |

## foreignObject

### fo__mdn-foreignobject

[`fo/mdn-foreignobject.svg`](svg/fo/mdn-foreignobject.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject: the box stays empty. |
| ⬆️ | weasysvg | **better than the reference** | Better for print: no scrollbar for overflow: auto, which paper cannot scroll. The text takes the full width of the box, and one more line shows. |
| ❌ | WeasyPrint | **differs from the reference** | The box is empty. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/fo__mdn-foreignobject.png"><img src="render/chromium/fo__mdn-foreignobject.png" width="200" alt="fo__mdn-foreignobject in Chromium"></a> | <a href="render/resvg/fo__mdn-foreignobject.png"><img src="render/resvg/fo__mdn-foreignobject.png" width="200" alt="fo__mdn-foreignobject in resvg"></a> | <a href="render/weasyprint/fo__mdn-foreignobject.png"><img src="render/weasyprint/fo__mdn-foreignobject.png" width="200" alt="fo__mdn-foreignobject in WeasyPrint"></a> | <a href="render/weasysvg/fo__mdn-foreignobject.png"><img src="render/weasysvg/fo__mdn-foreignobject.png" width="200" alt="fo__mdn-foreignobject in weasysvg"></a> |

### fo__rich-html

[`fo/rich-html.svg`](svg/fo/rich-html.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg has no foreignObject. |
| ✅ | weasysvg | **matches the reference** | Matches: heading, list with its markers, table and the rotated paragraph. |
| ❌ | WeasyPrint | **differs from the reference** | All HTML content is missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/fo__rich-html.png"><img src="render/chromium/fo__rich-html.png" width="200" alt="fo__rich-html in Chromium"></a> | <a href="render/resvg/fo__rich-html.png"><img src="render/resvg/fo__rich-html.png" width="200" alt="fo__rich-html in resvg"></a> | <a href="render/weasyprint/fo__rich-html.png"><img src="render/weasyprint/fo__rich-html.png" width="200" alt="fo__rich-html in WeasyPrint"></a> | <a href="render/weasysvg/fo__rich-html.png"><img src="render/weasysvg/fo__rich-html.png" width="200" alt="fo__rich-html in weasysvg"></a> |

## Wikimedia Commons

### real__wm-Bitmap_VS_SVG

[`real/wm-Bitmap_VS_SVG.svg`](svg/real/wm-Bitmap_VS_SVG.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | an English browser | Chromium of the references ran with no English language: the switch has no fallback child, so it drew no title. An English browser shows Raster and Vector, as weasysvg does (see the browser panel). |
| ✅ | weasysvg | **matches the reference** | Matches an English browser: Raster and Vector titles. |
| ❌ | WeasyPrint | **differs from the reference** | All translations of the titles are drawn on top of each other. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Bitmap_VS_SVG.png"><img src="render/chromium/real__wm-Bitmap_VS_SVG.png" width="200" alt="real__wm-Bitmap_VS_SVG in Chromium"></a> | <a href="render/resvg/real__wm-Bitmap_VS_SVG.png"><img src="render/resvg/real__wm-Bitmap_VS_SVG.png" width="200" alt="real__wm-Bitmap_VS_SVG in resvg"></a> | <a href="render/weasyprint/real__wm-Bitmap_VS_SVG.png"><img src="render/weasyprint/real__wm-Bitmap_VS_SVG.png" width="200" alt="real__wm-Bitmap_VS_SVG in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Bitmap_VS_SVG.png"><img src="render/weasysvg/real__wm-Bitmap_VS_SVG.png" width="200" alt="real__wm-Bitmap_VS_SVG in weasysvg"></a> |

### real__wm-Flag_of_Brazil

[`real/wm-Flag_of_Brazil.svg`](svg/real/wm-Flag_of_Brazil.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Flag_of_Brazil.png"><img src="render/chromium/real__wm-Flag_of_Brazil.png" width="200" alt="real__wm-Flag_of_Brazil in Chromium"></a> | <a href="render/resvg/real__wm-Flag_of_Brazil.png"><img src="render/resvg/real__wm-Flag_of_Brazil.png" width="200" alt="real__wm-Flag_of_Brazil in resvg"></a> | <a href="render/weasyprint/real__wm-Flag_of_Brazil.png"><img src="render/weasyprint/real__wm-Flag_of_Brazil.png" width="200" alt="real__wm-Flag_of_Brazil in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Flag_of_Brazil.png"><img src="render/weasysvg/real__wm-Flag_of_Brazil.png" width="200" alt="real__wm-Flag_of_Brazil in weasysvg"></a> |

### real__wm-Flag_of_Switzerland

[`real/wm-Flag_of_Switzerland.svg`](svg/real/wm-Flag_of_Switzerland.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Flag_of_Switzerland.png"><img src="render/chromium/real__wm-Flag_of_Switzerland.png" width="200" alt="real__wm-Flag_of_Switzerland in Chromium"></a> | <a href="render/resvg/real__wm-Flag_of_Switzerland.png"><img src="render/resvg/real__wm-Flag_of_Switzerland.png" width="200" alt="real__wm-Flag_of_Switzerland in resvg"></a> | <a href="render/weasyprint/real__wm-Flag_of_Switzerland.png"><img src="render/weasyprint/real__wm-Flag_of_Switzerland.png" width="200" alt="real__wm-Flag_of_Switzerland in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Flag_of_Switzerland.png"><img src="render/weasysvg/real__wm-Flag_of_Switzerland.png" width="200" alt="real__wm-Flag_of_Switzerland in weasysvg"></a> |

### real__wm-Flag_of_the_United_Kingdom

[`real/wm-Flag_of_the_United_Kingdom.svg`](svg/real/wm-Flag_of_the_United_Kingdom.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Flag_of_the_United_Kingdom.png"><img src="render/chromium/real__wm-Flag_of_the_United_Kingdom.png" width="200" alt="real__wm-Flag_of_the_United_Kingdom in Chromium"></a> | <a href="render/resvg/real__wm-Flag_of_the_United_Kingdom.png"><img src="render/resvg/real__wm-Flag_of_the_United_Kingdom.png" width="200" alt="real__wm-Flag_of_the_United_Kingdom in resvg"></a> | <a href="render/weasyprint/real__wm-Flag_of_the_United_Kingdom.png"><img src="render/weasyprint/real__wm-Flag_of_the_United_Kingdom.png" width="200" alt="real__wm-Flag_of_the_United_Kingdom in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Flag_of_the_United_Kingdom.png"><img src="render/weasysvg/real__wm-Flag_of_the_United_Kingdom.png" width="200" alt="real__wm-Flag_of_the_United_Kingdom in weasysvg"></a> |

### real__wm-Git-logo

[`real/wm-Git-logo.svg`](svg/real/wm-Git-logo.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Git-logo.png"><img src="render/chromium/real__wm-Git-logo.png" width="200" alt="real__wm-Git-logo in Chromium"></a> | <a href="render/resvg/real__wm-Git-logo.png"><img src="render/resvg/real__wm-Git-logo.png" width="200" alt="real__wm-Git-logo in resvg"></a> | <a href="render/weasyprint/real__wm-Git-logo.png"><img src="render/weasyprint/real__wm-Git-logo.png" width="200" alt="real__wm-Git-logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Git-logo.png"><img src="render/weasysvg/real__wm-Git-logo.png" width="200" alt="real__wm-Git-logo in weasysvg"></a> |

### real__wm-Inkscape_Logo

[`real/wm-Inkscape_Logo.svg`](svg/real/wm-Inkscape_Logo.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg fills some shapes black instead of their gradients. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Inkscape_Logo.png"><img src="render/chromium/real__wm-Inkscape_Logo.png" width="200" alt="real__wm-Inkscape_Logo in Chromium"></a> | <a href="render/resvg/real__wm-Inkscape_Logo.png"><img src="render/resvg/real__wm-Inkscape_Logo.png" width="200" alt="real__wm-Inkscape_Logo in resvg"></a> | <a href="render/weasyprint/real__wm-Inkscape_Logo.png"><img src="render/weasyprint/real__wm-Inkscape_Logo.png" width="200" alt="real__wm-Inkscape_Logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Inkscape_Logo.png"><img src="render/weasysvg/real__wm-Inkscape_Logo.png" width="200" alt="real__wm-Inkscape_Logo in weasysvg"></a> |

### real__wm-Kubernetes_logo_without_workmark

[`real/wm-Kubernetes_logo_without_workmark.svg`](svg/real/wm-Kubernetes_logo_without_workmark.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Kubernetes_logo_without_workmark.png"><img src="render/chromium/real__wm-Kubernetes_logo_without_workmark.png" width="200" alt="real__wm-Kubernetes_logo_without_workmark in Chromium"></a> | <a href="render/resvg/real__wm-Kubernetes_logo_without_workmark.png"><img src="render/resvg/real__wm-Kubernetes_logo_without_workmark.png" width="200" alt="real__wm-Kubernetes_logo_without_workmark in resvg"></a> | <a href="render/weasyprint/real__wm-Kubernetes_logo_without_workmark.png"><img src="render/weasyprint/real__wm-Kubernetes_logo_without_workmark.png" width="200" alt="real__wm-Kubernetes_logo_without_workmark in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Kubernetes_logo_without_workmark.png"><img src="render/weasysvg/real__wm-Kubernetes_logo_without_workmark.png" width="200" alt="real__wm-Kubernetes_logo_without_workmark in weasysvg"></a> |

### real__wm-OSI_Model_v1

[`real/wm-OSI_Model_v1.svg`](svg/real/wm-OSI_Model_v1.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg drops the second line of every label. |
| ✅ | weasysvg | **matches the reference** | Matches: every label and its lines are centered as in Chromium. |
| ❌ | WeasyPrint | **differs from the reference** | All translations of every label are drawn on top of each other. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-OSI_Model_v1.png"><img src="render/chromium/real__wm-OSI_Model_v1.png" width="200" alt="real__wm-OSI_Model_v1 in Chromium"></a> | <a href="render/resvg/real__wm-OSI_Model_v1.png"><img src="render/resvg/real__wm-OSI_Model_v1.png" width="200" alt="real__wm-OSI_Model_v1 in resvg"></a> | <a href="render/weasyprint/real__wm-OSI_Model_v1.png"><img src="render/weasyprint/real__wm-OSI_Model_v1.png" width="200" alt="real__wm-OSI_Model_v1 in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-OSI_Model_v1.png"><img src="render/weasysvg/real__wm-OSI_Model_v1.png" width="200" alt="real__wm-OSI_Model_v1 in weasysvg"></a> |

### real__wm-Openstreetmap_logo

[`real/wm-Openstreetmap_logo.svg`](svg/real/wm-Openstreetmap_logo.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| 🟡 | weasysvg | **close to the reference** | The shadow of the lens ring is darker and sharper than in Chromium: the ring is a filled shape thinner than two deviations, and the levels of a blur know only the nearest edge. |
| ❌ | WeasyPrint | **differs from the reference** | No shadows, and the handle is a flat dark shape. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Openstreetmap_logo.png"><img src="render/chromium/real__wm-Openstreetmap_logo.png" width="200" alt="real__wm-Openstreetmap_logo in Chromium"></a> | <a href="render/resvg/real__wm-Openstreetmap_logo.png"><img src="render/resvg/real__wm-Openstreetmap_logo.png" width="200" alt="real__wm-Openstreetmap_logo in resvg"></a> | <a href="render/weasyprint/real__wm-Openstreetmap_logo.png"><img src="render/weasyprint/real__wm-Openstreetmap_logo.png" width="200" alt="real__wm-Openstreetmap_logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Openstreetmap_logo.png"><img src="render/weasysvg/real__wm-Openstreetmap_logo.png" width="200" alt="real__wm-Openstreetmap_logo in weasysvg"></a> |

### real__wm-Python-logo-notext

[`real/wm-Python-logo-notext.svg`](svg/real/wm-Python-logo-notext.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Python-logo-notext.png"><img src="render/chromium/real__wm-Python-logo-notext.png" width="200" alt="real__wm-Python-logo-notext in Chromium"></a> | <a href="render/resvg/real__wm-Python-logo-notext.png"><img src="render/resvg/real__wm-Python-logo-notext.png" width="200" alt="real__wm-Python-logo-notext in resvg"></a> | <a href="render/weasyprint/real__wm-Python-logo-notext.png"><img src="render/weasyprint/real__wm-Python-logo-notext.png" width="200" alt="real__wm-Python-logo-notext in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Python-logo-notext.png"><img src="render/weasysvg/real__wm-Python-logo-notext.png" width="200" alt="real__wm-Python-logo-notext in weasysvg"></a> |

### real__wm-SVG_Logo

[`real/wm-SVG_Logo.svg`](svg/real/wm-SVG_Logo.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-SVG_Logo.png"><img src="render/chromium/real__wm-SVG_Logo.png" width="200" alt="real__wm-SVG_Logo in Chromium"></a> | <a href="render/resvg/real__wm-SVG_Logo.png"><img src="render/resvg/real__wm-SVG_Logo.png" width="200" alt="real__wm-SVG_Logo in resvg"></a> | <a href="render/weasyprint/real__wm-SVG_Logo.png"><img src="render/weasyprint/real__wm-SVG_Logo.png" width="200" alt="real__wm-SVG_Logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-SVG_Logo.png"><img src="render/weasysvg/real__wm-SVG_Logo.png" width="200" alt="real__wm-SVG_Logo in weasysvg"></a> |

### real__wm-Simple_Periodic_Table_Chart-blocks

[`real/wm-Simple_Periodic_Table_Chart-blocks.svg`](svg/real/wm-Simple_Periodic_Table_Chart-blocks.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: each number and symbol is centered in its cell. |
| ❌ | WeasyPrint | **differs from the reference** | All translations of every label are drawn on top of each other. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Simple_Periodic_Table_Chart-blocks.png"><img src="render/chromium/real__wm-Simple_Periodic_Table_Chart-blocks.png" width="200" alt="real__wm-Simple_Periodic_Table_Chart-blocks in Chromium"></a> | <a href="render/resvg/real__wm-Simple_Periodic_Table_Chart-blocks.png"><img src="render/resvg/real__wm-Simple_Periodic_Table_Chart-blocks.png" width="200" alt="real__wm-Simple_Periodic_Table_Chart-blocks in resvg"></a> | <a href="render/weasyprint/real__wm-Simple_Periodic_Table_Chart-blocks.png"><img src="render/weasyprint/real__wm-Simple_Periodic_Table_Chart-blocks.png" width="200" alt="real__wm-Simple_Periodic_Table_Chart-blocks in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Simple_Periodic_Table_Chart-blocks.png"><img src="render/weasysvg/real__wm-Simple_Periodic_Table_Chart-blocks.png" width="200" alt="real__wm-Simple_Periodic_Table_Chart-blocks in weasysvg"></a> |

### real__wm-Tux

[`real/wm-Tux.svg`](svg/real/wm-Tux.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches, the blurred shading of the feet included. |
| 🟡 | WeasyPrint | **close to the reference** | The soft shading under the feet is missing: hard edges instead. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Tux.png"><img src="render/chromium/real__wm-Tux.png" width="200" alt="real__wm-Tux in Chromium"></a> | <a href="render/resvg/real__wm-Tux.png"><img src="render/resvg/real__wm-Tux.png" width="200" alt="real__wm-Tux in resvg"></a> | <a href="render/weasyprint/real__wm-Tux.png"><img src="render/weasyprint/real__wm-Tux.png" width="200" alt="real__wm-Tux in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Tux.png"><img src="render/weasysvg/real__wm-Tux.png" width="200" alt="real__wm-Tux in weasysvg"></a> |

### real__wm-Wikimedia-logo

[`real/wm-Wikimedia-logo.svg`](svg/real/wm-Wikimedia-logo.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Wikimedia-logo.png"><img src="render/chromium/real__wm-Wikimedia-logo.png" width="200" alt="real__wm-Wikimedia-logo in Chromium"></a> | <a href="render/resvg/real__wm-Wikimedia-logo.png"><img src="render/resvg/real__wm-Wikimedia-logo.png" width="200" alt="real__wm-Wikimedia-logo in resvg"></a> | <a href="render/weasyprint/real__wm-Wikimedia-logo.png"><img src="render/weasyprint/real__wm-Wikimedia-logo.png" width="200" alt="real__wm-Wikimedia-logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Wikimedia-logo.png"><img src="render/weasysvg/real__wm-Wikimedia-logo.png" width="200" alt="real__wm-Wikimedia-logo in weasysvg"></a> |

## resvg feature tests

### resvg__filters-feColorMatrix--type=luminanceToAlpha

[`resvg/filters-feColorMatrix--type=luminanceToAlpha.svg`](svg/resvg/filters-feColorMatrix--type=luminanceToAlpha.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The filter is dropped: the rainbow gradient shows in color. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feColorMatrix--type=luminanceToAlpha.png"><img src="render/chromium/resvg__filters-feColorMatrix--type=luminanceToAlpha.png" width="200" alt="resvg__filters-feColorMatrix--type=luminanceToAlpha in Chromium"></a> | <a href="render/resvg/resvg__filters-feColorMatrix--type=luminanceToAlpha.png"><img src="render/resvg/resvg__filters-feColorMatrix--type=luminanceToAlpha.png" width="200" alt="resvg__filters-feColorMatrix--type=luminanceToAlpha in resvg"></a> | <a href="render/weasyprint/resvg__filters-feColorMatrix--type=luminanceToAlpha.png"><img src="render/weasyprint/resvg__filters-feColorMatrix--type=luminanceToAlpha.png" width="200" alt="resvg__filters-feColorMatrix--type=luminanceToAlpha in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feColorMatrix--type=luminanceToAlpha.png"><img src="render/weasysvg/resvg__filters-feColorMatrix--type=luminanceToAlpha.png" width="200" alt="resvg__filters-feColorMatrix--type=luminanceToAlpha in weasysvg"></a> |

### resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values

[`resvg/filters-feColorMatrix--type=matrix-with-non-normalized-values.svg`](svg/resvg/filters-feColorMatrix--type=matrix-with-non-normalized-values.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The filter is dropped: the rainbow gradient shows in color. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png"><img src="render/chromium/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png" width="200" alt="resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values in Chromium"></a> | <a href="render/resvg/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png"><img src="render/resvg/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png" width="200" alt="resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values in resvg"></a> | <a href="render/weasyprint/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png"><img src="render/weasyprint/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png" width="200" alt="resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png"><img src="render/weasysvg/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png" width="200" alt="resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values in weasysvg"></a> |

### resvg__filters-feComposite--operator=arithmetic-with-large-k1-4

[`resvg/filters-feComposite--operator=arithmetic-with-large-k1-4.svg`](svg/resvg/filters-feComposite--operator=arithmetic-with-large-k1-4.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The filter is dropped: a plain green square. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png"><img src="render/chromium/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png" width="200" alt="resvg__filters-feComposite--operator=arithmetic-with-large-k1-4 in Chromium"></a> | <a href="render/resvg/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png"><img src="render/resvg/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png" width="200" alt="resvg__filters-feComposite--operator=arithmetic-with-large-k1-4 in resvg"></a> | <a href="render/weasyprint/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png"><img src="render/weasyprint/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png" width="200" alt="resvg__filters-feComposite--operator=arithmetic-with-large-k1-4 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png"><img src="render/weasysvg/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png" width="200" alt="resvg__filters-feComposite--operator=arithmetic-with-large-k1-4 in weasysvg"></a> |

### resvg__filters-feComposite--operator=over

[`resvg/filters-feComposite--operator=over.svg`](svg/resvg/filters-feComposite--operator=over.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The filter is dropped: a plain green square. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feComposite--operator=over.png"><img src="render/chromium/resvg__filters-feComposite--operator=over.png" width="200" alt="resvg__filters-feComposite--operator=over in Chromium"></a> | <a href="render/resvg/resvg__filters-feComposite--operator=over.png"><img src="render/resvg/resvg__filters-feComposite--operator=over.png" width="200" alt="resvg__filters-feComposite--operator=over in resvg"></a> | <a href="render/weasyprint/resvg__filters-feComposite--operator=over.png"><img src="render/weasyprint/resvg__filters-feComposite--operator=over.png" width="200" alt="resvg__filters-feComposite--operator=over in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feComposite--operator=over.png"><img src="render/weasysvg/resvg__filters-feComposite--operator=over.png" width="200" alt="resvg__filters-feComposite--operator=over in weasysvg"></a> |

### resvg__filters-feDropShadow--hsla-color

[`resvg/filters-feDropShadow--hsla-color.svg`](svg/resvg/filters-feDropShadow--hsla-color.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: the blue glow. |
| ❌ | WeasyPrint | **differs from the reference** | No shadow. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feDropShadow--hsla-color.png"><img src="render/chromium/resvg__filters-feDropShadow--hsla-color.png" width="200" alt="resvg__filters-feDropShadow--hsla-color in Chromium"></a> | <a href="render/resvg/resvg__filters-feDropShadow--hsla-color.png"><img src="render/resvg/resvg__filters-feDropShadow--hsla-color.png" width="200" alt="resvg__filters-feDropShadow--hsla-color in resvg"></a> | <a href="render/weasyprint/resvg__filters-feDropShadow--hsla-color.png"><img src="render/weasyprint/resvg__filters-feDropShadow--hsla-color.png" width="200" alt="resvg__filters-feDropShadow--hsla-color in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feDropShadow--hsla-color.png"><img src="render/weasysvg/resvg__filters-feDropShadow--hsla-color.png" width="200" alt="resvg__filters-feDropShadow--hsla-color in weasysvg"></a> |

### resvg__filters-feDropShadow--with-percent-offset

[`resvg/filters-feDropShadow--with-percent-offset.svg`](svg/resvg/filters-feDropShadow--with-percent-offset.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | No shadow. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feDropShadow--with-percent-offset.png"><img src="render/chromium/resvg__filters-feDropShadow--with-percent-offset.png" width="200" alt="resvg__filters-feDropShadow--with-percent-offset in Chromium"></a> | <a href="render/resvg/resvg__filters-feDropShadow--with-percent-offset.png"><img src="render/resvg/resvg__filters-feDropShadow--with-percent-offset.png" width="200" alt="resvg__filters-feDropShadow--with-percent-offset in resvg"></a> | <a href="render/weasyprint/resvg__filters-feDropShadow--with-percent-offset.png"><img src="render/weasyprint/resvg__filters-feDropShadow--with-percent-offset.png" width="200" alt="resvg__filters-feDropShadow--with-percent-offset in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feDropShadow--with-percent-offset.png"><img src="render/weasysvg/resvg__filters-feDropShadow--with-percent-offset.png" width="200" alt="resvg__filters-feDropShadow--with-percent-offset in weasysvg"></a> |

### resvg__filters-feFlood--seagreen

[`resvg/filters-feFlood--seagreen.svg`](svg/resvg/filters-feFlood--seagreen.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | resvg | Chromium rounds the filter region out to whole pixels: the flood reaches a pixel further. resvg and the expected image of the resvg suite keep the region of the spec. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | A black square instead of the seagreen flood. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feFlood--seagreen.png"><img src="render/chromium/resvg__filters-feFlood--seagreen.png" width="200" alt="resvg__filters-feFlood--seagreen in Chromium"></a> | <a href="render/resvg/resvg__filters-feFlood--seagreen.png"><img src="render/resvg/resvg__filters-feFlood--seagreen.png" width="200" alt="resvg__filters-feFlood--seagreen in resvg"></a> | <a href="render/weasyprint/resvg__filters-feFlood--seagreen.png"><img src="render/weasyprint/resvg__filters-feFlood--seagreen.png" width="200" alt="resvg__filters-feFlood--seagreen in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feFlood--seagreen.png"><img src="render/weasysvg/resvg__filters-feFlood--seagreen.png" width="200" alt="resvg__filters-feFlood--seagreen in weasysvg"></a> |

### resvg__filters-feFlood--with-opacity-on-target-element

[`resvg/filters-feFlood--with-opacity-on-target-element.svg`](svg/resvg/filters-feFlood--with-opacity-on-target-element.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | Grey and dark green instead of the pale flood. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feFlood--with-opacity-on-target-element.png"><img src="render/chromium/resvg__filters-feFlood--with-opacity-on-target-element.png" width="200" alt="resvg__filters-feFlood--with-opacity-on-target-element in Chromium"></a> | <a href="render/resvg/resvg__filters-feFlood--with-opacity-on-target-element.png"><img src="render/resvg/resvg__filters-feFlood--with-opacity-on-target-element.png" width="200" alt="resvg__filters-feFlood--with-opacity-on-target-element in resvg"></a> | <a href="render/weasyprint/resvg__filters-feFlood--with-opacity-on-target-element.png"><img src="render/weasyprint/resvg__filters-feFlood--with-opacity-on-target-element.png" width="200" alt="resvg__filters-feFlood--with-opacity-on-target-element in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feFlood--with-opacity-on-target-element.png"><img src="render/weasysvg/resvg__filters-feFlood--with-opacity-on-target-element.png" width="200" alt="resvg__filters-feFlood--with-opacity-on-target-element in weasysvg"></a> |

### resvg__filters-feGaussianBlur--small-stdDeviation

[`resvg/filters-feGaussianBlur--small-stdDeviation.svg`](svg/resvg/filters-feGaussianBlur--small-stdDeviation.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| 🟡 | WeasyPrint | **close to the reference** | Not blurred; the blur is small. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feGaussianBlur--small-stdDeviation.png"><img src="render/chromium/resvg__filters-feGaussianBlur--small-stdDeviation.png" width="200" alt="resvg__filters-feGaussianBlur--small-stdDeviation in Chromium"></a> | <a href="render/resvg/resvg__filters-feGaussianBlur--small-stdDeviation.png"><img src="render/resvg/resvg__filters-feGaussianBlur--small-stdDeviation.png" width="200" alt="resvg__filters-feGaussianBlur--small-stdDeviation in resvg"></a> | <a href="render/weasyprint/resvg__filters-feGaussianBlur--small-stdDeviation.png"><img src="render/weasyprint/resvg__filters-feGaussianBlur--small-stdDeviation.png" width="200" alt="resvg__filters-feGaussianBlur--small-stdDeviation in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feGaussianBlur--small-stdDeviation.png"><img src="render/weasysvg/resvg__filters-feGaussianBlur--small-stdDeviation.png" width="200" alt="resvg__filters-feGaussianBlur--small-stdDeviation in weasysvg"></a> |

### resvg__filters-feGaussianBlur--stdDeviation=0-5

[`resvg/filters-feGaussianBlur--stdDeviation=0-5.svg`](svg/resvg/filters-feGaussianBlur--stdDeviation=0-5.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: blurred along y only, the left and right edges stay sharp. |
| ❌ | WeasyPrint | **differs from the reference** | Not blurred at all. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feGaussianBlur--stdDeviation=0-5.png"><img src="render/chromium/resvg__filters-feGaussianBlur--stdDeviation=0-5.png" width="200" alt="resvg__filters-feGaussianBlur--stdDeviation=0-5 in Chromium"></a> | <a href="render/resvg/resvg__filters-feGaussianBlur--stdDeviation=0-5.png"><img src="render/resvg/resvg__filters-feGaussianBlur--stdDeviation=0-5.png" width="200" alt="resvg__filters-feGaussianBlur--stdDeviation=0-5 in resvg"></a> | <a href="render/weasyprint/resvg__filters-feGaussianBlur--stdDeviation=0-5.png"><img src="render/weasyprint/resvg__filters-feGaussianBlur--stdDeviation=0-5.png" width="200" alt="resvg__filters-feGaussianBlur--stdDeviation=0-5 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feGaussianBlur--stdDeviation=0-5.png"><img src="render/weasysvg/resvg__filters-feGaussianBlur--stdDeviation=0-5.png" width="200" alt="resvg__filters-feGaussianBlur--stdDeviation=0-5 in weasysvg"></a> |

### resvg__filters-feOffset--complex-transform

[`resvg/filters-feOffset--complex-transform.svg`](svg/resvg/filters-feOffset--complex-transform.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg offsets in the wrong space; Chromium matches the expected image of the resvg suite. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The offset is taken in the wrong space: the shape lands lower and larger. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feOffset--complex-transform.png"><img src="render/chromium/resvg__filters-feOffset--complex-transform.png" width="200" alt="resvg__filters-feOffset--complex-transform in Chromium"></a> | <a href="render/resvg/resvg__filters-feOffset--complex-transform.png"><img src="render/resvg/resvg__filters-feOffset--complex-transform.png" width="200" alt="resvg__filters-feOffset--complex-transform in resvg"></a> | <a href="render/weasyprint/resvg__filters-feOffset--complex-transform.png"><img src="render/weasyprint/resvg__filters-feOffset--complex-transform.png" width="200" alt="resvg__filters-feOffset--complex-transform in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feOffset--complex-transform.png"><img src="render/weasysvg/resvg__filters-feOffset--complex-transform.png" width="200" alt="resvg__filters-feOffset--complex-transform in weasysvg"></a> |

### resvg__filters-feOffset--fractional-offset

[`resvg/filters-feOffset--fractional-offset.svg`](svg/resvg/filters-feOffset--fractional-offset.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | resvg | Chromium rounds the filter region out to whole pixels. resvg and the expected image of the resvg suite keep the region of the spec. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| 🟡 | WeasyPrint | **close to the reference** | The offset square is not clipped to the filter region: it covers the frame. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feOffset--fractional-offset.png"><img src="render/chromium/resvg__filters-feOffset--fractional-offset.png" width="200" alt="resvg__filters-feOffset--fractional-offset in Chromium"></a> | <a href="render/resvg/resvg__filters-feOffset--fractional-offset.png"><img src="render/resvg/resvg__filters-feOffset--fractional-offset.png" width="200" alt="resvg__filters-feOffset--fractional-offset in resvg"></a> | <a href="render/weasyprint/resvg__filters-feOffset--fractional-offset.png"><img src="render/weasyprint/resvg__filters-feOffset--fractional-offset.png" width="200" alt="resvg__filters-feOffset--fractional-offset in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feOffset--fractional-offset.png"><img src="render/weasysvg/resvg__filters-feOffset--fractional-offset.png" width="200" alt="resvg__filters-feOffset--fractional-offset in weasysvg"></a> |

### resvg__filters-feTurbulence--baseFrequency=0.01

[`resvg/filters-feTurbulence--baseFrequency=0.01.svg`](svg/resvg/filters-feTurbulence--baseFrequency=0.01.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | A black square instead of the noise. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feTurbulence--baseFrequency=0.01.png"><img src="render/chromium/resvg__filters-feTurbulence--baseFrequency=0.01.png" width="200" alt="resvg__filters-feTurbulence--baseFrequency=0.01 in Chromium"></a> | <a href="render/resvg/resvg__filters-feTurbulence--baseFrequency=0.01.png"><img src="render/resvg/resvg__filters-feTurbulence--baseFrequency=0.01.png" width="200" alt="resvg__filters-feTurbulence--baseFrequency=0.01 in resvg"></a> | <a href="render/weasyprint/resvg__filters-feTurbulence--baseFrequency=0.01.png"><img src="render/weasyprint/resvg__filters-feTurbulence--baseFrequency=0.01.png" width="200" alt="resvg__filters-feTurbulence--baseFrequency=0.01 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feTurbulence--baseFrequency=0.01.png"><img src="render/weasysvg/resvg__filters-feTurbulence--baseFrequency=0.01.png" width="200" alt="resvg__filters-feTurbulence--baseFrequency=0.01 in weasysvg"></a> |

### resvg__filters-feTurbulence--type=invalid

[`resvg/filters-feTurbulence--type=invalid.svg`](svg/resvg/filters-feTurbulence--type=invalid.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | A black square instead of the noise. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feTurbulence--type=invalid.png"><img src="render/chromium/resvg__filters-feTurbulence--type=invalid.png" width="200" alt="resvg__filters-feTurbulence--type=invalid in Chromium"></a> | <a href="render/resvg/resvg__filters-feTurbulence--type=invalid.png"><img src="render/resvg/resvg__filters-feTurbulence--type=invalid.png" width="200" alt="resvg__filters-feTurbulence--type=invalid in resvg"></a> | <a href="render/weasyprint/resvg__filters-feTurbulence--type=invalid.png"><img src="render/weasyprint/resvg__filters-feTurbulence--type=invalid.png" width="200" alt="resvg__filters-feTurbulence--type=invalid in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feTurbulence--type=invalid.png"><img src="render/weasysvg/resvg__filters-feTurbulence--type=invalid.png" width="200" alt="resvg__filters-feTurbulence--type=invalid in weasysvg"></a> |

### resvg__filters-filter--in=SourceAlpha

[`resvg/filters-filter--in=SourceAlpha.svg`](svg/resvg/filters-filter--in=SourceAlpha.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: the blurred black silhouette. |
| ❌ | WeasyPrint | **differs from the reference** | The filter is dropped: the green square. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-filter--in=SourceAlpha.png"><img src="render/chromium/resvg__filters-filter--in=SourceAlpha.png" width="200" alt="resvg__filters-filter--in=SourceAlpha in Chromium"></a> | <a href="render/resvg/resvg__filters-filter--in=SourceAlpha.png"><img src="render/resvg/resvg__filters-filter--in=SourceAlpha.png" width="200" alt="resvg__filters-filter--in=SourceAlpha in resvg"></a> | <a href="render/weasyprint/resvg__filters-filter--in=SourceAlpha.png"><img src="render/weasyprint/resvg__filters-filter--in=SourceAlpha.png" width="200" alt="resvg__filters-filter--in=SourceAlpha in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-filter--in=SourceAlpha.png"><img src="render/weasysvg/resvg__filters-filter--in=SourceAlpha.png" width="200" alt="resvg__filters-filter--in=SourceAlpha in weasysvg"></a> |

### resvg__filters-filter--on-the-root-svg

[`resvg/filters-filter--on-the-root-svg.svg`](svg/resvg/filters-filter--on-the-root-svg.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| 🟡 | weasysvg | **close to the reference** | The blurred square has mitered corners, not round ones: a blur of anything but a plain rect is drawn in levels. |
| ❌ | WeasyPrint | **differs from the reference** | Not blurred. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-filter--on-the-root-svg.png"><img src="render/chromium/resvg__filters-filter--on-the-root-svg.png" width="200" alt="resvg__filters-filter--on-the-root-svg in Chromium"></a> | <a href="render/resvg/resvg__filters-filter--on-the-root-svg.png"><img src="render/resvg/resvg__filters-filter--on-the-root-svg.png" width="200" alt="resvg__filters-filter--on-the-root-svg in resvg"></a> | <a href="render/weasyprint/resvg__filters-filter--on-the-root-svg.png"><img src="render/weasyprint/resvg__filters-filter--on-the-root-svg.png" width="200" alt="resvg__filters-filter--on-the-root-svg in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-filter--on-the-root-svg.png"><img src="render/weasysvg/resvg__filters-filter--on-the-root-svg.png" width="200" alt="resvg__filters-filter--on-the-root-svg in weasysvg"></a> |

### resvg__filters-filter-functions--blur-function-two-values

[`resvg/filters-filter-functions--blur-function-two-values.svg`](svg/resvg/filters-filter-functions--blur-function-two-values.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: an invalid blur() leaves the element unfiltered. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-filter-functions--blur-function-two-values.png"><img src="render/chromium/resvg__filters-filter-functions--blur-function-two-values.png" width="200" alt="resvg__filters-filter-functions--blur-function-two-values in Chromium"></a> | <a href="render/resvg/resvg__filters-filter-functions--blur-function-two-values.png"><img src="render/resvg/resvg__filters-filter-functions--blur-function-two-values.png" width="200" alt="resvg__filters-filter-functions--blur-function-two-values in resvg"></a> | <a href="render/weasyprint/resvg__filters-filter-functions--blur-function-two-values.png"><img src="render/weasyprint/resvg__filters-filter-functions--blur-function-two-values.png" width="200" alt="resvg__filters-filter-functions--blur-function-two-values in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-filter-functions--blur-function-two-values.png"><img src="render/weasysvg/resvg__filters-filter-functions--blur-function-two-values.png" width="200" alt="resvg__filters-filter-functions--blur-function-two-values in weasysvg"></a> |

### resvg__filters-filter-functions--drop-shadow-function-comma-separated

[`resvg/filters-filter-functions--drop-shadow-function-comma-separated.svg`](svg/resvg/filters-filter-functions--drop-shadow-function-comma-separated.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: the invalid function is ignored. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png"><img src="render/chromium/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png" width="200" alt="resvg__filters-filter-functions--drop-shadow-function-comma-separated in Chromium"></a> | <a href="render/resvg/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png"><img src="render/resvg/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png" width="200" alt="resvg__filters-filter-functions--drop-shadow-function-comma-separated in resvg"></a> | <a href="render/weasyprint/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png"><img src="render/weasyprint/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png" width="200" alt="resvg__filters-filter-functions--drop-shadow-function-comma-separated in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png"><img src="render/weasysvg/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png" width="200" alt="resvg__filters-filter-functions--drop-shadow-function-comma-separated in weasysvg"></a> |

### resvg__masking-clipPath--clip-path-on-children

[`resvg/masking-clipPath--clip-path-on-children.svg`](svg/resvg/masking-clipPath--clip-path-on-children.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | Only the small center piece shows. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__masking-clipPath--clip-path-on-children.png"><img src="render/chromium/resvg__masking-clipPath--clip-path-on-children.png" width="200" alt="resvg__masking-clipPath--clip-path-on-children in Chromium"></a> | <a href="render/resvg/resvg__masking-clipPath--clip-path-on-children.png"><img src="render/resvg/resvg__masking-clipPath--clip-path-on-children.png" width="200" alt="resvg__masking-clipPath--clip-path-on-children in resvg"></a> | <a href="render/weasyprint/resvg__masking-clipPath--clip-path-on-children.png"><img src="render/weasyprint/resvg__masking-clipPath--clip-path-on-children.png" width="200" alt="resvg__masking-clipPath--clip-path-on-children in WeasyPrint"></a> | <a href="render/weasysvg/resvg__masking-clipPath--clip-path-on-children.png"><img src="render/weasysvg/resvg__masking-clipPath--clip-path-on-children.png" width="200" alt="resvg__masking-clipPath--clip-path-on-children in weasysvg"></a> |

### resvg__masking-clipPath--on-a-horizontal-line

[`resvg/masking-clipPath--on-a-horizontal-line.svg`](svg/resvg/masking-clipPath--on-a-horizontal-line.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__masking-clipPath--on-a-horizontal-line.png"><img src="render/chromium/resvg__masking-clipPath--on-a-horizontal-line.png" width="200" alt="resvg__masking-clipPath--on-a-horizontal-line in Chromium"></a> | <a href="render/resvg/resvg__masking-clipPath--on-a-horizontal-line.png"><img src="render/resvg/resvg__masking-clipPath--on-a-horizontal-line.png" width="200" alt="resvg__masking-clipPath--on-a-horizontal-line in resvg"></a> | <a href="render/weasyprint/resvg__masking-clipPath--on-a-horizontal-line.png"><img src="render/weasyprint/resvg__masking-clipPath--on-a-horizontal-line.png" width="200" alt="resvg__masking-clipPath--on-a-horizontal-line in WeasyPrint"></a> | <a href="render/weasysvg/resvg__masking-clipPath--on-a-horizontal-line.png"><img src="render/weasysvg/resvg__masking-clipPath--on-a-horizontal-line.png" width="200" alt="resvg__masking-clipPath--on-a-horizontal-line in weasysvg"></a> |

### resvg__masking-mask--invalid-child

[`resvg/masking-mask--invalid-child.svg`](svg/resvg/masking-mask--invalid-child.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: nothing is drawn. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__masking-mask--invalid-child.png"><img src="render/chromium/resvg__masking-mask--invalid-child.png" width="200" alt="resvg__masking-mask--invalid-child in Chromium"></a> | <a href="render/resvg/resvg__masking-mask--invalid-child.png"><img src="render/resvg/resvg__masking-mask--invalid-child.png" width="200" alt="resvg__masking-mask--invalid-child in resvg"></a> | <a href="render/weasyprint/resvg__masking-mask--invalid-child.png"><img src="render/weasyprint/resvg__masking-mask--invalid-child.png" width="200" alt="resvg__masking-mask--invalid-child in WeasyPrint"></a> | <a href="render/weasysvg/resvg__masking-mask--invalid-child.png"><img src="render/weasysvg/resvg__masking-mask--invalid-child.png" width="200" alt="resvg__masking-mask--invalid-child in weasysvg"></a> |

### resvg__masking-mask--recursive-on-self

[`resvg/masking-mask--recursive-on-self.svg`](svg/resvg/masking-mask--recursive-on-self.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The SVG is lost: blank. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__masking-mask--recursive-on-self.png"><img src="render/chromium/resvg__masking-mask--recursive-on-self.png" width="200" alt="resvg__masking-mask--recursive-on-self in Chromium"></a> | <a href="render/resvg/resvg__masking-mask--recursive-on-self.png"><img src="render/resvg/resvg__masking-mask--recursive-on-self.png" width="200" alt="resvg__masking-mask--recursive-on-self in resvg"></a> | <a href="render/weasyprint/resvg__masking-mask--recursive-on-self.png"><img src="render/weasyprint/resvg__masking-mask--recursive-on-self.png" width="200" alt="resvg__masking-mask--recursive-on-self in WeasyPrint"></a> | <a href="render/weasysvg/resvg__masking-mask--recursive-on-self.png"><img src="render/weasysvg/resvg__masking-mask--recursive-on-self.png" width="200" alt="resvg__masking-mask--recursive-on-self in weasysvg"></a> |

### resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect

[`resvg/paint-servers-linearGradient--attributes-via-xlink-href-from-rect.svg`](svg/resvg/paint-servers-linearGradient--attributes-via-xlink-href-from-rect.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png"><img src="render/chromium/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png" width="200" alt="resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png"><img src="render/resvg/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png" width="200" alt="resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png"><img src="render/weasyprint/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png" width="200" alt="resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png"><img src="render/weasysvg/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png" width="200" alt="resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect in weasysvg"></a> |

### resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1

[`resvg/paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.svg`](svg/resvg/paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png"><img src="render/chromium/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png" width="200" alt="resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1 in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png"><img src="render/resvg/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png" width="200" alt="resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1 in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png"><img src="render/weasyprint/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png" width="200" alt="resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png"><img src="render/weasysvg/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png" width="200" alt="resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1 in weasysvg"></a> |

### resvg__paint-servers-pattern--nested-objectBoundingBox

[`resvg/paint-servers-pattern--nested-objectBoundingBox.svg`](svg/resvg/paint-servers-pattern--nested-objectBoundingBox.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | resvg | Chromium shifts the tiles of the inner pattern; resvg matches the expected image of the resvg suite. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The inner pattern is shrunk to small fragments. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-pattern--nested-objectBoundingBox.png"><img src="render/chromium/resvg__paint-servers-pattern--nested-objectBoundingBox.png" width="200" alt="resvg__paint-servers-pattern--nested-objectBoundingBox in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-pattern--nested-objectBoundingBox.png"><img src="render/resvg/resvg__paint-servers-pattern--nested-objectBoundingBox.png" width="200" alt="resvg__paint-servers-pattern--nested-objectBoundingBox in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-pattern--nested-objectBoundingBox.png"><img src="render/weasyprint/resvg__paint-servers-pattern--nested-objectBoundingBox.png" width="200" alt="resvg__paint-servers-pattern--nested-objectBoundingBox in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-pattern--nested-objectBoundingBox.png"><img src="render/weasysvg/resvg__paint-servers-pattern--nested-objectBoundingBox.png" width="200" alt="resvg__paint-servers-pattern--nested-objectBoundingBox in weasysvg"></a> |

### resvg__paint-servers-pattern--text-child

[`resvg/paint-servers-pattern--text-child.svg`](svg/resvg/paint-servers-pattern--text-child.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | resvg | Chromium prints a pattern as a low-resolution image, so its text is blurred; resvg matches the expected image of the resvg suite. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| 🟡 | WeasyPrint | **close to the reference** | The text tiles are spaced differently, in another font. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-pattern--text-child.png"><img src="render/chromium/resvg__paint-servers-pattern--text-child.png" width="200" alt="resvg__paint-servers-pattern--text-child in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-pattern--text-child.png"><img src="render/resvg/resvg__paint-servers-pattern--text-child.png" width="200" alt="resvg__paint-servers-pattern--text-child in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-pattern--text-child.png"><img src="render/weasyprint/resvg__paint-servers-pattern--text-child.png" width="200" alt="resvg__paint-servers-pattern--text-child in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-pattern--text-child.png"><img src="render/weasysvg/resvg__paint-servers-pattern--text-child.png" width="200" alt="resvg__paint-servers-pattern--text-child in weasysvg"></a> |

### resvg__paint-servers-radialGradient--fr=0.2

[`resvg/paint-servers-radialGradient--fr=0.2.svg`](svg/resvg/paint-servers-radialGradient--fr=0.2.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | resvg | Chromium leaves a white pixel at the focal center; resvg matches the expected image of the resvg suite. |
| ✅ | weasysvg | **matches the reference** | Matches: the gray levels agree within 2 of 255. |
| 🟡 | WeasyPrint | **close to the reference** | The gradient is cut to a square with dark corners. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-radialGradient--fr=0.2.png"><img src="render/chromium/resvg__paint-servers-radialGradient--fr=0.2.png" width="200" alt="resvg__paint-servers-radialGradient--fr=0.2 in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-radialGradient--fr=0.2.png"><img src="render/resvg/resvg__paint-servers-radialGradient--fr=0.2.png" width="200" alt="resvg__paint-servers-radialGradient--fr=0.2 in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-radialGradient--fr=0.2.png"><img src="render/weasyprint/resvg__paint-servers-radialGradient--fr=0.2.png" width="200" alt="resvg__paint-servers-radialGradient--fr=0.2 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-radialGradient--fr=0.2.png"><img src="render/weasysvg/resvg__paint-servers-radialGradient--fr=0.2.png" width="200" alt="resvg__paint-servers-radialGradient--fr=0.2 in weasysvg"></a> |

### resvg__paint-servers-radialGradient--gradientTransform-via-href

[`resvg/paint-servers-radialGradient--gradientTransform-via-href.svg`](svg/resvg/paint-servers-radialGradient--gradientTransform-via-href.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg ignores a gradientTransform inherited through href; Chromium matches the expected image of the resvg suite. |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The lower two squares are missing. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-radialGradient--gradientTransform-via-href.png"><img src="render/chromium/resvg__paint-servers-radialGradient--gradientTransform-via-href.png" width="200" alt="resvg__paint-servers-radialGradient--gradientTransform-via-href in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-radialGradient--gradientTransform-via-href.png"><img src="render/resvg/resvg__paint-servers-radialGradient--gradientTransform-via-href.png" width="200" alt="resvg__paint-servers-radialGradient--gradientTransform-via-href in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-radialGradient--gradientTransform-via-href.png"><img src="render/weasyprint/resvg__paint-servers-radialGradient--gradientTransform-via-href.png" width="200" alt="resvg__paint-servers-radialGradient--gradientTransform-via-href in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-radialGradient--gradientTransform-via-href.png"><img src="render/weasysvg/resvg__paint-servers-radialGradient--gradientTransform-via-href.png" width="200" alt="resvg__paint-servers-radialGradient--gradientTransform-via-href in weasysvg"></a> |

### resvg__painting-marker--on-ArcTo

[`resvg/painting-marker--on-ArcTo.svg`](svg/resvg/painting-marker--on-ArcTo.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | The path is one arc, so by the spec it has no middle vertex, as Chromium draws it. resvg, Safari and the resvg suite split the arc into curves and put a marker-mid where they meet. |
| ✅ | weasysvg | **matches the reference** | Matches: a start and an end marker. |
| ❌ | WeasyPrint | **differs from the reference** | The markers point the wrong way. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-marker--on-ArcTo.png"><img src="render/chromium/resvg__painting-marker--on-ArcTo.png" width="200" alt="resvg__painting-marker--on-ArcTo in Chromium"></a> | <a href="render/resvg/resvg__painting-marker--on-ArcTo.png"><img src="render/resvg/resvg__painting-marker--on-ArcTo.png" width="200" alt="resvg__painting-marker--on-ArcTo in resvg"></a> | <a href="render/weasyprint/resvg__painting-marker--on-ArcTo.png"><img src="render/weasyprint/resvg__painting-marker--on-ArcTo.png" width="200" alt="resvg__painting-marker--on-ArcTo in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-marker--on-ArcTo.png"><img src="render/weasysvg/resvg__painting-marker--on-ArcTo.png" width="200" alt="resvg__painting-marker--on-ArcTo in weasysvg"></a> |

### resvg__painting-marker--orient=auto-on-M-C-C-4

[`resvg/painting-marker--orient=auto-on-M-C-C-4.svg`](svg/resvg/painting-marker--orient=auto-on-M-C-C-4.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg | At the cusp the two tangents are opposite, so their bisector can point either way: undefined by the spec. Chromium, resvg and the resvg suite point left, Safari right. |
| ✅ | weasysvg | **matches the reference** | Matches: the middle marker at the cusp points left. |
| ❌ | WeasyPrint | **differs from the reference** | The start marker points down instead of along the curve. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-marker--orient=auto-on-M-C-C-4.png"><img src="render/chromium/resvg__painting-marker--orient=auto-on-M-C-C-4.png" width="200" alt="resvg__painting-marker--orient=auto-on-M-C-C-4 in Chromium"></a> | <a href="render/resvg/resvg__painting-marker--orient=auto-on-M-C-C-4.png"><img src="render/resvg/resvg__painting-marker--orient=auto-on-M-C-C-4.png" width="200" alt="resvg__painting-marker--orient=auto-on-M-C-C-4 in resvg"></a> | <a href="render/weasyprint/resvg__painting-marker--orient=auto-on-M-C-C-4.png"><img src="render/weasyprint/resvg__painting-marker--orient=auto-on-M-C-C-4.png" width="200" alt="resvg__painting-marker--orient=auto-on-M-C-C-4 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-marker--orient=auto-on-M-C-C-4.png"><img src="render/weasysvg/resvg__painting-marker--orient=auto-on-M-C-C-4.png" width="200" alt="resvg__painting-marker--orient=auto-on-M-C-C-4 in weasysvg"></a> |

### resvg__painting-mix-blend-mode--screen

[`resvg/painting-mix-blend-mode--screen.svg`](svg/resvg/painting-mix-blend-mode--screen.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The blend mode is ignored: the colors are plain over. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-mix-blend-mode--screen.png"><img src="render/chromium/resvg__painting-mix-blend-mode--screen.png" width="200" alt="resvg__painting-mix-blend-mode--screen in Chromium"></a> | <a href="render/resvg/resvg__painting-mix-blend-mode--screen.png"><img src="render/resvg/resvg__painting-mix-blend-mode--screen.png" width="200" alt="resvg__painting-mix-blend-mode--screen in resvg"></a> | <a href="render/weasyprint/resvg__painting-mix-blend-mode--screen.png"><img src="render/weasyprint/resvg__painting-mix-blend-mode--screen.png" width="200" alt="resvg__painting-mix-blend-mode--screen in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-mix-blend-mode--screen.png"><img src="render/weasysvg/resvg__painting-mix-blend-mode--screen.png" width="200" alt="resvg__painting-mix-blend-mode--screen in weasysvg"></a> |

### resvg__painting-mix-blend-mode--xor

[`resvg/painting-mix-blend-mode--xor.svg`](svg/resvg/painting-mix-blend-mode--xor.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | The blend is ignored. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-mix-blend-mode--xor.png"><img src="render/chromium/resvg__painting-mix-blend-mode--xor.png" width="200" alt="resvg__painting-mix-blend-mode--xor in Chromium"></a> | <a href="render/resvg/resvg__painting-mix-blend-mode--xor.png"><img src="render/resvg/resvg__painting-mix-blend-mode--xor.png" width="200" alt="resvg__painting-mix-blend-mode--xor in resvg"></a> | <a href="render/weasyprint/resvg__painting-mix-blend-mode--xor.png"><img src="render/weasyprint/resvg__painting-mix-blend-mode--xor.png" width="200" alt="resvg__painting-mix-blend-mode--xor in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-mix-blend-mode--xor.png"><img src="render/weasysvg/resvg__painting-mix-blend-mode--xor.png" width="200" alt="resvg__painting-mix-blend-mode--xor in weasysvg"></a> |

### resvg__painting-paint-order--duplicates

[`resvg/painting-paint-order--duplicates.svg`](svg/resvg/painting-paint-order--duplicates.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-paint-order--duplicates.png"><img src="render/chromium/resvg__painting-paint-order--duplicates.png" width="200" alt="resvg__painting-paint-order--duplicates in Chromium"></a> | <a href="render/resvg/resvg__painting-paint-order--duplicates.png"><img src="render/resvg/resvg__painting-paint-order--duplicates.png" width="200" alt="resvg__painting-paint-order--duplicates in resvg"></a> | <a href="render/weasyprint/resvg__painting-paint-order--duplicates.png"><img src="render/weasyprint/resvg__painting-paint-order--duplicates.png" width="200" alt="resvg__painting-paint-order--duplicates in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-paint-order--duplicates.png"><img src="render/weasysvg/resvg__painting-paint-order--duplicates.png" width="200" alt="resvg__painting-paint-order--duplicates in weasysvg"></a> |

### resvg__painting-paint-order--invalid

[`resvg/painting-paint-order--invalid.svg`](svg/resvg/painting-paint-order--invalid.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-paint-order--invalid.png"><img src="render/chromium/resvg__painting-paint-order--invalid.png" width="200" alt="resvg__painting-paint-order--invalid in Chromium"></a> | <a href="render/resvg/resvg__painting-paint-order--invalid.png"><img src="render/resvg/resvg__painting-paint-order--invalid.png" width="200" alt="resvg__painting-paint-order--invalid in resvg"></a> | <a href="render/weasyprint/resvg__painting-paint-order--invalid.png"><img src="render/weasyprint/resvg__painting-paint-order--invalid.png" width="200" alt="resvg__painting-paint-order--invalid in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-paint-order--invalid.png"><img src="render/weasysvg/resvg__painting-paint-order--invalid.png" width="200" alt="resvg__painting-paint-order--invalid in weasysvg"></a> |

### resvg__painting-stroke-dasharray--0-n-with-round-caps

[`resvg/painting-stroke-dasharray--0-n-with-round-caps.svg`](svg/resvg/painting-stroke-dasharray--0-n-with-round-caps.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: each dot in its place. |
| 🟡 | WeasyPrint | **close to the reference** | The dots on the bottom and left sides sit up to 1 unit off: PDFium moves dashes of length 0 along the path. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-stroke-dasharray--0-n-with-round-caps.png"><img src="render/chromium/resvg__painting-stroke-dasharray--0-n-with-round-caps.png" width="200" alt="resvg__painting-stroke-dasharray--0-n-with-round-caps in Chromium"></a> | <a href="render/resvg/resvg__painting-stroke-dasharray--0-n-with-round-caps.png"><img src="render/resvg/resvg__painting-stroke-dasharray--0-n-with-round-caps.png" width="200" alt="resvg__painting-stroke-dasharray--0-n-with-round-caps in resvg"></a> | <a href="render/weasyprint/resvg__painting-stroke-dasharray--0-n-with-round-caps.png"><img src="render/weasyprint/resvg__painting-stroke-dasharray--0-n-with-round-caps.png" width="200" alt="resvg__painting-stroke-dasharray--0-n-with-round-caps in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-stroke-dasharray--0-n-with-round-caps.png"><img src="render/weasysvg/resvg__painting-stroke-dasharray--0-n-with-round-caps.png" width="200" alt="resvg__painting-stroke-dasharray--0-n-with-round-caps in weasysvg"></a> |

### resvg__painting-stroke-dasharray--odd-count

[`resvg/painting-stroke-dasharray--odd-count.svg`](svg/resvg/painting-stroke-dasharray--odd-count.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| 🟡 | WeasyPrint | **close to the reference** | The dashes drift along the circle: WeasyPrint draws it a little too large. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-stroke-dasharray--odd-count.png"><img src="render/chromium/resvg__painting-stroke-dasharray--odd-count.png" width="200" alt="resvg__painting-stroke-dasharray--odd-count in Chromium"></a> | <a href="render/resvg/resvg__painting-stroke-dasharray--odd-count.png"><img src="render/resvg/resvg__painting-stroke-dasharray--odd-count.png" width="200" alt="resvg__painting-stroke-dasharray--odd-count in resvg"></a> | <a href="render/weasyprint/resvg__painting-stroke-dasharray--odd-count.png"><img src="render/weasyprint/resvg__painting-stroke-dasharray--odd-count.png" width="200" alt="resvg__painting-stroke-dasharray--odd-count in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-stroke-dasharray--odd-count.png"><img src="render/weasysvg/resvg__painting-stroke-dasharray--odd-count.png" width="200" alt="resvg__painting-stroke-dasharray--odd-count in weasysvg"></a> |

### resvg__shapes-path--M-H-H-implicit

[`resvg/shapes-path--M-H-H-implicit.svg`](svg/resvg/shapes-path--M-H-H-implicit.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__shapes-path--M-H-H-implicit.png"><img src="render/chromium/resvg__shapes-path--M-H-H-implicit.png" width="200" alt="resvg__shapes-path--M-H-H-implicit in Chromium"></a> | <a href="render/resvg/resvg__shapes-path--M-H-H-implicit.png"><img src="render/resvg/resvg__shapes-path--M-H-H-implicit.png" width="200" alt="resvg__shapes-path--M-H-H-implicit in resvg"></a> | <a href="render/weasyprint/resvg__shapes-path--M-H-H-implicit.png"><img src="render/weasyprint/resvg__shapes-path--M-H-H-implicit.png" width="200" alt="resvg__shapes-path--M-H-H-implicit in WeasyPrint"></a> | <a href="render/weasysvg/resvg__shapes-path--M-H-H-implicit.png"><img src="render/weasysvg/resvg__shapes-path--M-H-H-implicit.png" width="200" alt="resvg__shapes-path--M-H-H-implicit in weasysvg"></a> |

### resvg__shapes-path--M-T

[`resvg/shapes-path--M-T.svg`](svg/resvg/shapes-path--M-T.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__shapes-path--M-T.png"><img src="render/chromium/resvg__shapes-path--M-T.png" width="200" alt="resvg__shapes-path--M-T in Chromium"></a> | <a href="render/resvg/resvg__shapes-path--M-T.png"><img src="render/resvg/resvg__shapes-path--M-T.png" width="200" alt="resvg__shapes-path--M-T in resvg"></a> | <a href="render/weasyprint/resvg__shapes-path--M-T.png"><img src="render/weasyprint/resvg__shapes-path--M-T.png" width="200" alt="resvg__shapes-path--M-T in WeasyPrint"></a> | <a href="render/weasysvg/resvg__shapes-path--M-T.png"><img src="render/weasysvg/resvg__shapes-path--M-T.png" width="200" alt="resvg__shapes-path--M-T in weasysvg"></a> |

### resvg__structure-style--class-selector

[`resvg/structure-style--class-selector.svg`](svg/resvg/structure-style--class-selector.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-style--class-selector.png"><img src="render/chromium/resvg__structure-style--class-selector.png" width="200" alt="resvg__structure-style--class-selector in Chromium"></a> | <a href="render/resvg/resvg__structure-style--class-selector.png"><img src="render/resvg/resvg__structure-style--class-selector.png" width="200" alt="resvg__structure-style--class-selector in resvg"></a> | <a href="render/weasyprint/resvg__structure-style--class-selector.png"><img src="render/weasyprint/resvg__structure-style--class-selector.png" width="200" alt="resvg__structure-style--class-selector in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-style--class-selector.png"><img src="render/weasysvg/resvg__structure-style--class-selector.png" width="200" alt="resvg__structure-style--class-selector in weasysvg"></a> |

### resvg__structure-style--iD-selector

[`resvg/structure-style--iD-selector.svg`](svg/resvg/structure-style--iD-selector.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-style--iD-selector.png"><img src="render/chromium/resvg__structure-style--iD-selector.png" width="200" alt="resvg__structure-style--iD-selector in Chromium"></a> | <a href="render/resvg/resvg__structure-style--iD-selector.png"><img src="render/resvg/resvg__structure-style--iD-selector.png" width="200" alt="resvg__structure-style--iD-selector in resvg"></a> | <a href="render/weasyprint/resvg__structure-style--iD-selector.png"><img src="render/weasyprint/resvg__structure-style--iD-selector.png" width="200" alt="resvg__structure-style--iD-selector in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-style--iD-selector.png"><img src="render/weasysvg/resvg__structure-style--iD-selector.png" width="200" alt="resvg__structure-style--iD-selector in weasysvg"></a> |

### resvg__structure-switch--single-child

[`resvg/structure-switch--single-child.svg`](svg/resvg/structure-switch--single-child.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-switch--single-child.png"><img src="render/chromium/resvg__structure-switch--single-child.png" width="200" alt="resvg__structure-switch--single-child in Chromium"></a> | <a href="render/resvg/resvg__structure-switch--single-child.png"><img src="render/resvg/resvg__structure-switch--single-child.png" width="200" alt="resvg__structure-switch--single-child in resvg"></a> | <a href="render/weasyprint/resvg__structure-switch--single-child.png"><img src="render/weasyprint/resvg__structure-switch--single-child.png" width="200" alt="resvg__structure-switch--single-child in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-switch--single-child.png"><img src="render/weasysvg/resvg__structure-switch--single-child.png" width="200" alt="resvg__structure-switch--single-child in weasysvg"></a> |

### resvg__structure-switch--with-attributes

[`resvg/structure-switch--with-attributes.svg`](svg/resvg/structure-switch--with-attributes.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ❌ | WeasyPrint | **differs from the reference** | Red: the switch is ignored and every child draws. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-switch--with-attributes.png"><img src="render/chromium/resvg__structure-switch--with-attributes.png" width="200" alt="resvg__structure-switch--with-attributes in Chromium"></a> | <a href="render/resvg/resvg__structure-switch--with-attributes.png"><img src="render/resvg/resvg__structure-switch--with-attributes.png" width="200" alt="resvg__structure-switch--with-attributes in resvg"></a> | <a href="render/weasyprint/resvg__structure-switch--with-attributes.png"><img src="render/weasyprint/resvg__structure-switch--with-attributes.png" width="200" alt="resvg__structure-switch--with-attributes in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-switch--with-attributes.png"><img src="render/weasysvg/resvg__structure-switch--with-attributes.png" width="200" alt="resvg__structure-switch--with-attributes in weasysvg"></a> |

### resvg__structure-symbol--with-transform

[`resvg/structure-symbol--with-transform.svg`](svg/resvg/structure-symbol--with-transform.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | The resvg suite follows SVG 1.1, where a symbol has no transform; SVG 2 and browsers apply it. |
| ✅ | weasysvg | **matches the reference** | Matches Chromium: skewed as SVG 2 says. |
| ✅ | WeasyPrint | **matches the reference** | Matches Chromium. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-symbol--with-transform.png"><img src="render/chromium/resvg__structure-symbol--with-transform.png" width="200" alt="resvg__structure-symbol--with-transform in Chromium"></a> | <a href="render/resvg/resvg__structure-symbol--with-transform.png"><img src="render/resvg/resvg__structure-symbol--with-transform.png" width="200" alt="resvg__structure-symbol--with-transform in resvg"></a> | <a href="render/weasyprint/resvg__structure-symbol--with-transform.png"><img src="render/weasyprint/resvg__structure-symbol--with-transform.png" width="200" alt="resvg__structure-symbol--with-transform in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-symbol--with-transform.png"><img src="render/weasysvg/resvg__structure-symbol--with-transform.png" width="200" alt="resvg__structure-symbol--with-transform in weasysvg"></a> |

### resvg__structure-symbol--with-viewBox-and-custom-use-size

[`resvg/structure-symbol--with-viewBox-and-custom-use-size.svg`](svg/resvg/structure-symbol--with-viewBox-and-custom-use-size.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-symbol--with-viewBox-and-custom-use-size.png"><img src="render/chromium/resvg__structure-symbol--with-viewBox-and-custom-use-size.png" width="200" alt="resvg__structure-symbol--with-viewBox-and-custom-use-size in Chromium"></a> | <a href="render/resvg/resvg__structure-symbol--with-viewBox-and-custom-use-size.png"><img src="render/resvg/resvg__structure-symbol--with-viewBox-and-custom-use-size.png" width="200" alt="resvg__structure-symbol--with-viewBox-and-custom-use-size in resvg"></a> | <a href="render/weasyprint/resvg__structure-symbol--with-viewBox-and-custom-use-size.png"><img src="render/weasyprint/resvg__structure-symbol--with-viewBox-and-custom-use-size.png" width="200" alt="resvg__structure-symbol--with-viewBox-and-custom-use-size in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-symbol--with-viewBox-and-custom-use-size.png"><img src="render/weasysvg/resvg__structure-symbol--with-viewBox-and-custom-use-size.png" width="200" alt="resvg__structure-symbol--with-viewBox-and-custom-use-size in weasysvg"></a> |

### resvg__structure-systemLanguage--on-clipPath

[`resvg/structure-systemLanguage--on-clipPath.svg`](svg/resvg/structure-systemLanguage--on-clipPath.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-systemLanguage--on-clipPath.png"><img src="render/chromium/resvg__structure-systemLanguage--on-clipPath.png" width="200" alt="resvg__structure-systemLanguage--on-clipPath in Chromium"></a> | <a href="render/resvg/resvg__structure-systemLanguage--on-clipPath.png"><img src="render/resvg/resvg__structure-systemLanguage--on-clipPath.png" width="200" alt="resvg__structure-systemLanguage--on-clipPath in resvg"></a> | <a href="render/weasyprint/resvg__structure-systemLanguage--on-clipPath.png"><img src="render/weasyprint/resvg__structure-systemLanguage--on-clipPath.png" width="200" alt="resvg__structure-systemLanguage--on-clipPath in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-systemLanguage--on-clipPath.png"><img src="render/weasysvg/resvg__structure-systemLanguage--on-clipPath.png" width="200" alt="resvg__structure-systemLanguage--on-clipPath in weasysvg"></a> |

### resvg__structure-systemLanguage--on-defs

[`resvg/structure-systemLanguage--on-defs.svg`](svg/resvg/structure-systemLanguage--on-defs.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | resvg | Chromium draws nothing; systemLanguage on defs does not hide what is defined there, so the gradient square shows, as in the resvg suite. |
| ✅ | weasysvg | **matches the reference** | Matches the resvg suite: the gradient square. |
| ✅ | WeasyPrint | **matches the reference** | Matches the resvg suite. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-systemLanguage--on-defs.png"><img src="render/chromium/resvg__structure-systemLanguage--on-defs.png" width="200" alt="resvg__structure-systemLanguage--on-defs in Chromium"></a> | <a href="render/resvg/resvg__structure-systemLanguage--on-defs.png"><img src="render/resvg/resvg__structure-systemLanguage--on-defs.png" width="200" alt="resvg__structure-systemLanguage--on-defs in resvg"></a> | <a href="render/weasyprint/resvg__structure-systemLanguage--on-defs.png"><img src="render/weasyprint/resvg__structure-systemLanguage--on-defs.png" width="200" alt="resvg__structure-systemLanguage--on-defs in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-systemLanguage--on-defs.png"><img src="render/weasysvg/resvg__structure-systemLanguage--on-defs.png" width="200" alt="resvg__structure-systemLanguage--on-defs in weasysvg"></a> |

### resvg__structure-transform--scale-without-Y

[`resvg/structure-transform--scale-without-Y.svg`](svg/resvg/structure-transform--scale-without-Y.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-transform--scale-without-Y.png"><img src="render/chromium/resvg__structure-transform--scale-without-Y.png" width="200" alt="resvg__structure-transform--scale-without-Y in Chromium"></a> | <a href="render/resvg/resvg__structure-transform--scale-without-Y.png"><img src="render/resvg/resvg__structure-transform--scale-without-Y.png" width="200" alt="resvg__structure-transform--scale-without-Y in resvg"></a> | <a href="render/weasyprint/resvg__structure-transform--scale-without-Y.png"><img src="render/weasyprint/resvg__structure-transform--scale-without-Y.png" width="200" alt="resvg__structure-transform--scale-without-Y in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-transform--scale-without-Y.png"><img src="render/weasysvg/resvg__structure-transform--scale-without-Y.png" width="200" alt="resvg__structure-transform--scale-without-Y in weasysvg"></a> |

### resvg__structure-transform--skewY

[`resvg/structure-transform--skewY.svg`](svg/resvg/structure-transform--skewY.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-transform--skewY.png"><img src="render/chromium/resvg__structure-transform--skewY.png" width="200" alt="resvg__structure-transform--skewY in Chromium"></a> | <a href="render/resvg/resvg__structure-transform--skewY.png"><img src="render/resvg/resvg__structure-transform--skewY.png" width="200" alt="resvg__structure-transform--skewY in resvg"></a> | <a href="render/weasyprint/resvg__structure-transform--skewY.png"><img src="render/weasyprint/resvg__structure-transform--skewY.png" width="200" alt="resvg__structure-transform--skewY in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-transform--skewY.png"><img src="render/weasysvg/resvg__structure-transform--skewY.png" width="200" alt="resvg__structure-transform--skewY in weasysvg"></a> |

### resvg__structure-use--with-size

[`resvg/structure-use--with-size.svg`](svg/resvg/structure-use--with-size.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-use--with-size.png"><img src="render/chromium/resvg__structure-use--with-size.png" width="200" alt="resvg__structure-use--with-size in Chromium"></a> | <a href="render/resvg/resvg__structure-use--with-size.png"><img src="render/resvg/resvg__structure-use--with-size.png" width="200" alt="resvg__structure-use--with-size in resvg"></a> | <a href="render/weasyprint/resvg__structure-use--with-size.png"><img src="render/weasyprint/resvg__structure-use--with-size.png" width="200" alt="resvg__structure-use--with-size in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-use--with-size.png"><img src="render/weasysvg/resvg__structure-use--with-size.png" width="200" alt="resvg__structure-use--with-size in weasysvg"></a> |

### resvg__structure-use--xlink-to-svg-element-with-rect

[`resvg/structure-use--xlink-to-svg-element-with-rect.svg`](svg/resvg/structure-use--xlink-to-svg-element-with-rect.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-use--xlink-to-svg-element-with-rect.png"><img src="render/chromium/resvg__structure-use--xlink-to-svg-element-with-rect.png" width="200" alt="resvg__structure-use--xlink-to-svg-element-with-rect in Chromium"></a> | <a href="render/resvg/resvg__structure-use--xlink-to-svg-element-with-rect.png"><img src="render/resvg/resvg__structure-use--xlink-to-svg-element-with-rect.png" width="200" alt="resvg__structure-use--xlink-to-svg-element-with-rect in resvg"></a> | <a href="render/weasyprint/resvg__structure-use--xlink-to-svg-element-with-rect.png"><img src="render/weasyprint/resvg__structure-use--xlink-to-svg-element-with-rect.png" width="200" alt="resvg__structure-use--xlink-to-svg-element-with-rect in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-use--xlink-to-svg-element-with-rect.png"><img src="render/weasysvg/resvg__structure-use--xlink-to-svg-element-with-rect.png" width="200" alt="resvg__structure-use--xlink-to-svg-element-with-rect in weasysvg"></a> |

### resvg__text-dominant-baseline--auto

[`resvg/text-dominant-baseline--auto.svg`](svg/resvg/text-dominant-baseline--auto.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches, in the Noto Sans the test asks for. |
| 🟡 | WeasyPrint | **close to the reference** | The word is wider: WeasyPrint lays the letters out one by one, without kerning. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-dominant-baseline--auto.png"><img src="render/chromium/resvg__text-dominant-baseline--auto.png" width="200" alt="resvg__text-dominant-baseline--auto in Chromium"></a> | <a href="render/resvg/resvg__text-dominant-baseline--auto.png"><img src="render/resvg/resvg__text-dominant-baseline--auto.png" width="200" alt="resvg__text-dominant-baseline--auto in resvg"></a> | <a href="render/weasyprint/resvg__text-dominant-baseline--auto.png"><img src="render/weasyprint/resvg__text-dominant-baseline--auto.png" width="200" alt="resvg__text-dominant-baseline--auto in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-dominant-baseline--auto.png"><img src="render/weasysvg/resvg__text-dominant-baseline--auto.png" width="200" alt="resvg__text-dominant-baseline--auto in weasysvg"></a> |

### resvg__text-dominant-baseline--reset-size

[`resvg/text-dominant-baseline--reset-size.svg`](svg/resvg/text-dominant-baseline--reset-size.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches, in the Noto Sans the test asks for. |
| 🟡 | WeasyPrint | **close to the reference** | The word is wider: WeasyPrint lays the letters out one by one, without kerning. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-dominant-baseline--reset-size.png"><img src="render/chromium/resvg__text-dominant-baseline--reset-size.png" width="200" alt="resvg__text-dominant-baseline--reset-size in Chromium"></a> | <a href="render/resvg/resvg__text-dominant-baseline--reset-size.png"><img src="render/resvg/resvg__text-dominant-baseline--reset-size.png" width="200" alt="resvg__text-dominant-baseline--reset-size in resvg"></a> | <a href="render/weasyprint/resvg__text-dominant-baseline--reset-size.png"><img src="render/weasyprint/resvg__text-dominant-baseline--reset-size.png" width="200" alt="resvg__text-dominant-baseline--reset-size in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-dominant-baseline--reset-size.png"><img src="render/weasysvg/resvg__text-dominant-baseline--reset-size.png" width="200" alt="resvg__text-dominant-baseline--reset-size in weasysvg"></a> |

### resvg__text-letter-spacing--0

[`resvg/text-letter-spacing--0.svg`](svg/resvg/text-letter-spacing--0.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches, in the Noto Sans the test asks for. |
| 🟡 | WeasyPrint | **close to the reference** | The word is a little wider. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-letter-spacing--0.png"><img src="render/chromium/resvg__text-letter-spacing--0.png" width="200" alt="resvg__text-letter-spacing--0 in Chromium"></a> | <a href="render/resvg/resvg__text-letter-spacing--0.png"><img src="render/resvg/resvg__text-letter-spacing--0.png" width="200" alt="resvg__text-letter-spacing--0 in resvg"></a> | <a href="render/weasyprint/resvg__text-letter-spacing--0.png"><img src="render/weasyprint/resvg__text-letter-spacing--0.png" width="200" alt="resvg__text-letter-spacing--0 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-letter-spacing--0.png"><img src="render/weasysvg/resvg__text-letter-spacing--0.png" width="200" alt="resvg__text-letter-spacing--0 in weasysvg"></a> |

### resvg__text-letter-spacing--on-Arabic

[`resvg/text-letter-spacing--on-Arabic.svg`](svg/resvg/text-letter-spacing--on-Arabic.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: letter-spacing widens the spaces only. |
| ❌ | WeasyPrint | **differs from the reference** | The letters are not joined and stand apart. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-letter-spacing--on-Arabic.png"><img src="render/chromium/resvg__text-letter-spacing--on-Arabic.png" width="200" alt="resvg__text-letter-spacing--on-Arabic in Chromium"></a> | <a href="render/resvg/resvg__text-letter-spacing--on-Arabic.png"><img src="render/resvg/resvg__text-letter-spacing--on-Arabic.png" width="200" alt="resvg__text-letter-spacing--on-Arabic in resvg"></a> | <a href="render/weasyprint/resvg__text-letter-spacing--on-Arabic.png"><img src="render/weasyprint/resvg__text-letter-spacing--on-Arabic.png" width="200" alt="resvg__text-letter-spacing--on-Arabic in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-letter-spacing--on-Arabic.png"><img src="render/weasysvg/resvg__text-letter-spacing--on-Arabic.png" width="200" alt="resvg__text-letter-spacing--on-Arabic in weasysvg"></a> |

### resvg__text-text--nested

[`resvg/text-text--nested.svg`](svg/resvg/text-text--nested.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: a text inside a text draws nothing. |
| ❌ | WeasyPrint | **differs from the reference** | The nested text draws, in red. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-text--nested.png"><img src="render/chromium/resvg__text-text--nested.png" width="200" alt="resvg__text-text--nested in Chromium"></a> | <a href="render/resvg/resvg__text-text--nested.png"><img src="render/resvg/resvg__text-text--nested.png" width="200" alt="resvg__text-text--nested in resvg"></a> | <a href="render/weasyprint/resvg__text-text--nested.png"><img src="render/weasyprint/resvg__text-text--nested.png" width="200" alt="resvg__text-text--nested in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-text--nested.png"><img src="render/weasysvg/resvg__text-text--nested.png" width="200" alt="resvg__text-text--nested in weasysvg"></a> |

### resvg__text-text--x-and-y-with-less-values-than-characters

[`resvg/text-text--x-and-y-with-less-values-than-characters.svg`](svg/resvg/text-text--x-and-y-with-less-values-than-characters.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| ✅ | WeasyPrint | **matches the reference** | Matches. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-text--x-and-y-with-less-values-than-characters.png"><img src="render/chromium/resvg__text-text--x-and-y-with-less-values-than-characters.png" width="200" alt="resvg__text-text--x-and-y-with-less-values-than-characters in Chromium"></a> | <a href="render/resvg/resvg__text-text--x-and-y-with-less-values-than-characters.png"><img src="render/resvg/resvg__text-text--x-and-y-with-less-values-than-characters.png" width="200" alt="resvg__text-text--x-and-y-with-less-values-than-characters in resvg"></a> | <a href="render/weasyprint/resvg__text-text--x-and-y-with-less-values-than-characters.png"><img src="render/weasyprint/resvg__text-text--x-and-y-with-less-values-than-characters.png" width="200" alt="resvg__text-text--x-and-y-with-less-values-than-characters in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-text--x-and-y-with-less-values-than-characters.png"><img src="render/weasysvg/resvg__text-text--x-and-y-with-less-values-than-characters.png" width="200" alt="resvg__text-text--x-and-y-with-less-values-than-characters in weasysvg"></a> |

### resvg__text-text-decoration--line-through

[`resvg/text-text-decoration--line-through.svg`](svg/resvg/text-text-decoration--line-through.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg and the resvg suite take the thickness and place of the line from the font, Chromium a tenth of the font size: text-decoration-thickness auto allows both. weasysvg follows Chromium. |
| ✅ | weasysvg | **matches the reference** | Matches, the line-through included. |
| ❌ | WeasyPrint | **differs from the reference** | No line-through. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-text-decoration--line-through.png"><img src="render/chromium/resvg__text-text-decoration--line-through.png" width="200" alt="resvg__text-text-decoration--line-through in Chromium"></a> | <a href="render/resvg/resvg__text-text-decoration--line-through.png"><img src="render/resvg/resvg__text-text-decoration--line-through.png" width="200" alt="resvg__text-text-decoration--line-through in resvg"></a> | <a href="render/weasyprint/resvg__text-text-decoration--line-through.png"><img src="render/weasyprint/resvg__text-text-decoration--line-through.png" width="200" alt="resvg__text-text-decoration--line-through in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-text-decoration--line-through.png"><img src="render/weasysvg/resvg__text-text-decoration--line-through.png" width="200" alt="resvg__text-text-decoration--line-through in weasysvg"></a> |

### resvg__text-text-decoration--style-resolving-3

[`resvg/text-text-decoration--style-resolving-3.svg`](svg/resvg/text-text-decoration--style-resolving-3.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg and the resvg suite take the thickness and place of the line from the font, Chromium a tenth of the font size: text-decoration-thickness auto allows both. weasysvg follows Chromium. |
| ✅ | weasysvg | **matches the reference** | Matches, the line-through included. |
| ❌ | WeasyPrint | **differs from the reference** | No line-through. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-text-decoration--style-resolving-3.png"><img src="render/chromium/resvg__text-text-decoration--style-resolving-3.png" width="200" alt="resvg__text-text-decoration--style-resolving-3 in Chromium"></a> | <a href="render/resvg/resvg__text-text-decoration--style-resolving-3.png"><img src="render/resvg/resvg__text-text-decoration--style-resolving-3.png" width="200" alt="resvg__text-text-decoration--style-resolving-3 in resvg"></a> | <a href="render/weasyprint/resvg__text-text-decoration--style-resolving-3.png"><img src="render/weasyprint/resvg__text-text-decoration--style-resolving-3.png" width="200" alt="resvg__text-text-decoration--style-resolving-3 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-text-decoration--style-resolving-3.png"><img src="render/weasysvg/resvg__text-text-decoration--style-resolving-3.png" width="200" alt="resvg__text-text-decoration--style-resolving-3 in weasysvg"></a> |

### resvg__text-textPath--with-invalid-path-and-xlink-href

[`resvg/text-textPath--with-invalid-path-and-xlink-href.svg`](svg/resvg/text-textPath--with-invalid-path-and-xlink-href.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches: no text. |
| ❌ | WeasyPrint | **differs from the reference** | Text drawn at the top. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-textPath--with-invalid-path-and-xlink-href.png"><img src="render/chromium/resvg__text-textPath--with-invalid-path-and-xlink-href.png" width="200" alt="resvg__text-textPath--with-invalid-path-and-xlink-href in Chromium"></a> | <a href="render/resvg/resvg__text-textPath--with-invalid-path-and-xlink-href.png"><img src="render/resvg/resvg__text-textPath--with-invalid-path-and-xlink-href.png" width="200" alt="resvg__text-textPath--with-invalid-path-and-xlink-href in resvg"></a> | <a href="render/weasyprint/resvg__text-textPath--with-invalid-path-and-xlink-href.png"><img src="render/weasyprint/resvg__text-textPath--with-invalid-path-and-xlink-href.png" width="200" alt="resvg__text-textPath--with-invalid-path-and-xlink-href in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-textPath--with-invalid-path-and-xlink-href.png"><img src="render/weasysvg/resvg__text-textPath--with-invalid-path-and-xlink-href.png" width="200" alt="resvg__text-textPath--with-invalid-path-and-xlink-href in weasysvg"></a> |

### resvg__text-textPath--with-underline

[`resvg/text-textPath--with-underline.svg`](svg/resvg/text-textPath--with-underline.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | resvg and the resvg suite draw a thinner underline, from the font, through the descenders; Chromium a tenth of the font size, skipping the ink. |
| ✅ | weasysvg | **matches the reference** | Matches: the underline breaks around the descenders, as in Chromium. |
| ❌ | WeasyPrint | **differs from the reference** | No text on the path. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-textPath--with-underline.png"><img src="render/chromium/resvg__text-textPath--with-underline.png" width="200" alt="resvg__text-textPath--with-underline in Chromium"></a> | <a href="render/resvg/resvg__text-textPath--with-underline.png"><img src="render/resvg/resvg__text-textPath--with-underline.png" width="200" alt="resvg__text-textPath--with-underline in resvg"></a> | <a href="render/weasyprint/resvg__text-textPath--with-underline.png"><img src="render/weasyprint/resvg__text-textPath--with-underline.png" width="200" alt="resvg__text-textPath--with-underline in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-textPath--with-underline.png"><img src="render/weasysvg/resvg__text-textPath--with-underline.png" width="200" alt="resvg__text-textPath--with-underline in weasysvg"></a> |

### resvg__text-tspan--mixed

[`resvg/text-tspan--mixed.svg`](svg/resvg/text-tspan--mixed.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| 🟡 | WeasyPrint | **close to the reference** | The words are wider: WeasyPrint lays the letters out one by one, without kerning. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-tspan--mixed.png"><img src="render/chromium/resvg__text-tspan--mixed.png" width="200" alt="resvg__text-tspan--mixed in Chromium"></a> | <a href="render/resvg/resvg__text-tspan--mixed.png"><img src="render/resvg/resvg__text-tspan--mixed.png" width="200" alt="resvg__text-tspan--mixed in resvg"></a> | <a href="render/weasyprint/resvg__text-tspan--mixed.png"><img src="render/weasyprint/resvg__text-tspan--mixed.png" width="200" alt="resvg__text-tspan--mixed in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-tspan--mixed.png"><img src="render/weasysvg/resvg__text-tspan--mixed.png" width="200" alt="resvg__text-tspan--mixed in weasysvg"></a> |

### resvg__text-tspan--only-with-y

[`resvg/text-tspan--only-with-y.svg`](svg/resvg/text-tspan--only-with-y.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium and resvg |  |
| ✅ | weasysvg | **matches the reference** | Matches. |
| 🟡 | WeasyPrint | **close to the reference** | The word is wider: WeasyPrint lays the letters out one by one, without kerning. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-tspan--only-with-y.png"><img src="render/chromium/resvg__text-tspan--only-with-y.png" width="200" alt="resvg__text-tspan--only-with-y in Chromium"></a> | <a href="render/resvg/resvg__text-tspan--only-with-y.png"><img src="render/resvg/resvg__text-tspan--only-with-y.png" width="200" alt="resvg__text-tspan--only-with-y in resvg"></a> | <a href="render/weasyprint/resvg__text-tspan--only-with-y.png"><img src="render/weasyprint/resvg__text-tspan--only-with-y.png" width="200" alt="resvg__text-tspan--only-with-y in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-tspan--only-with-y.png"><img src="render/weasysvg/resvg__text-tspan--only-with-y.png" width="200" alt="resvg__text-tspan--only-with-y in weasysvg"></a> |

### resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor

[`resvg/text-writing-mode--tb-with-negative-dy-and-text-anchor.svg`](svg/resvg/text-writing-mode--tb-with-negative-dy-and-text-anchor.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | Chromium | SVG 2 anchors a text chunk by the extent of its glyph positions, dy included; Chromium does, and matches the expected image of the resvg suite. resvg anchors by the advance. |
| ✅ | weasysvg | **matches the reference** | Matches: each column is anchored with B moved up. |
| ❌ | WeasyPrint | **differs from the reference** | Laid out horizontally. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png"><img src="render/chromium/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png" width="200" alt="resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor in Chromium"></a> | <a href="render/resvg/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png"><img src="render/resvg/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png" width="200" alt="resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor in resvg"></a> | <a href="render/weasyprint/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png"><img src="render/weasyprint/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png" width="200" alt="resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png"><img src="render/weasysvg/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png" width="200" alt="resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor in weasysvg"></a> |

### resvg__text-writing-mode--tb-with-rotate

[`resvg/text-writing-mode--tb-with-rotate.svg`](svg/resvg/text-writing-mode--tb-with-rotate.svg)

| | Renderer | Verdict | What |
|---|---|---|---|
| 📌 | Reference | resvg | The test is undefined behavior; the resvg suite shows its expected result. |
| ❌ | weasysvg | **differs from the reference** | The Arabic word is not shaped: its letters stand apart in isolated forms, so the column runs longer. |
| ❌ | WeasyPrint | **differs from the reference** | Laid out horizontally. |

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-writing-mode--tb-with-rotate.png"><img src="render/chromium/resvg__text-writing-mode--tb-with-rotate.png" width="200" alt="resvg__text-writing-mode--tb-with-rotate in Chromium"></a> | <a href="render/resvg/resvg__text-writing-mode--tb-with-rotate.png"><img src="render/resvg/resvg__text-writing-mode--tb-with-rotate.png" width="200" alt="resvg__text-writing-mode--tb-with-rotate in resvg"></a> | <a href="render/weasyprint/resvg__text-writing-mode--tb-with-rotate.png"><img src="render/weasyprint/resvg__text-writing-mode--tb-with-rotate.png" width="200" alt="resvg__text-writing-mode--tb-with-rotate in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-writing-mode--tb-with-rotate.png"><img src="render/weasysvg/resvg__text-writing-mode--tb-with-rotate.png" width="200" alt="resvg__text-writing-mode--tb-with-rotate in weasysvg"></a> |
