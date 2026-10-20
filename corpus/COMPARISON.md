# Corpus comparison

<!-- Written by make comparison (tools/visual/comparison.py). Do not edit by hand. -->

Each SVG of the corpus in four renderings: Chromium, the reference; resvg (resvg-py 0.5.0); WeasyPrint 70.0 alone; and WeasyPrint 70.0 with weasysvg. The WeasyPrint panels are PDFium rasterizations at 96 dpi; resvg renders the SVG at the width of the page. Every panel is cropped to the ink of the Chromium reference, so the four line up pixel for pixel. The verdicts come from a visual review, see [`verdicts.json`](verdicts.json). Click a panel for its full size.

| Verdict | WeasyPrint 70.0 | WeasyPrint 70.0 with weasysvg |
|---|---|---|
| same as Chromium | 40 | 108 |
| minor difference | 10 | 7 |
| other font only | 11 | 0 |
| broken | 54 | 0 |

- [Diagrams from kroki and mermaid.ink](#diagrams-from-kroki-and-mermaidink) (29)
- [draw.io](#drawio) (6)
- [foreignObject](#foreignobject) (2)
- [Wikimedia Commons](#wikimedia-commons) (14)
- [resvg feature tests](#resvg-feature-tests) (64)

## Diagrams from kroki and mermaid.ink

### diagrams__kroki-blockdiag

[`diagrams/kroki-blockdiag.svg`](svg/diagrams/kroki-blockdiag.svg). WeasyPrint: minor, weasysvg: **same**. Checked at full size in PDFium, cairo and Quartz: the shadows are blurred, as in Chromium. The thumbnail is too small to show it.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-blockdiag.png"><img src="render/chromium/diagrams__kroki-blockdiag.png" width="200" alt="diagrams__kroki-blockdiag in Chromium"></a> | <a href="render/resvg/diagrams__kroki-blockdiag.png"><img src="render/resvg/diagrams__kroki-blockdiag.png" width="200" alt="diagrams__kroki-blockdiag in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-blockdiag.png"><img src="render/weasyprint/diagrams__kroki-blockdiag.png" width="200" alt="diagrams__kroki-blockdiag in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-blockdiag.png"><img src="render/weasysvg/diagrams__kroki-blockdiag.png" width="200" alt="diagrams__kroki-blockdiag in weasysvg"></a> |

### diagrams__kroki-bpmn

[`diagrams/kroki-bpmn.svg`](svg/diagrams/kroki-bpmn.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-bpmn.png"><img src="render/chromium/diagrams__kroki-bpmn.png" width="200" alt="diagrams__kroki-bpmn in Chromium"></a> | <a href="render/resvg/diagrams__kroki-bpmn.png"><img src="render/resvg/diagrams__kroki-bpmn.png" width="200" alt="diagrams__kroki-bpmn in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-bpmn.png"><img src="render/weasyprint/diagrams__kroki-bpmn.png" width="200" alt="diagrams__kroki-bpmn in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-bpmn.png"><img src="render/weasysvg/diagrams__kroki-bpmn.png" width="200" alt="diagrams__kroki-bpmn in weasysvg"></a> |

### diagrams__kroki-c4plantuml

[`diagrams/kroki-c4plantuml.svg`](svg/diagrams/kroki-c4plantuml.svg). WeasyPrint: font, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-c4plantuml.png"><img src="render/chromium/diagrams__kroki-c4plantuml.png" width="200" alt="diagrams__kroki-c4plantuml in Chromium"></a> | <a href="render/resvg/diagrams__kroki-c4plantuml.png"><img src="render/resvg/diagrams__kroki-c4plantuml.png" width="200" alt="diagrams__kroki-c4plantuml in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-c4plantuml.png"><img src="render/weasyprint/diagrams__kroki-c4plantuml.png" width="200" alt="diagrams__kroki-c4plantuml in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-c4plantuml.png"><img src="render/weasysvg/diagrams__kroki-c4plantuml.png" width="200" alt="diagrams__kroki-c4plantuml in weasysvg"></a> |

### diagrams__kroki-d2-arch

[`diagrams/kroki-d2-arch.svg`](svg/diagrams/kroki-d2-arch.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-d2-arch.png"><img src="render/chromium/diagrams__kroki-d2-arch.png" width="200" alt="diagrams__kroki-d2-arch in Chromium"></a> | <a href="render/resvg/diagrams__kroki-d2-arch.png"><img src="render/resvg/diagrams__kroki-d2-arch.png" width="200" alt="diagrams__kroki-d2-arch in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-d2-arch.png"><img src="render/weasyprint/diagrams__kroki-d2-arch.png" width="200" alt="diagrams__kroki-d2-arch in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-d2-arch.png"><img src="render/weasysvg/diagrams__kroki-d2-arch.png" width="200" alt="diagrams__kroki-d2-arch in weasysvg"></a> |

### diagrams__kroki-d2

[`diagrams/kroki-d2.svg`](svg/diagrams/kroki-d2.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-d2.png"><img src="render/chromium/diagrams__kroki-d2.png" width="200" alt="diagrams__kroki-d2 in Chromium"></a> | <a href="render/resvg/diagrams__kroki-d2.png"><img src="render/resvg/diagrams__kroki-d2.png" width="200" alt="diagrams__kroki-d2 in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-d2.png"><img src="render/weasyprint/diagrams__kroki-d2.png" width="200" alt="diagrams__kroki-d2 in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-d2.png"><img src="render/weasysvg/diagrams__kroki-d2.png" width="200" alt="diagrams__kroki-d2 in weasysvg"></a> |

### diagrams__kroki-erd

[`diagrams/kroki-erd.svg`](svg/diagrams/kroki-erd.svg). WeasyPrint: minor, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-erd.png"><img src="render/chromium/diagrams__kroki-erd.png" width="200" alt="diagrams__kroki-erd in Chromium"></a> | <a href="render/resvg/diagrams__kroki-erd.png"><img src="render/resvg/diagrams__kroki-erd.png" width="200" alt="diagrams__kroki-erd in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-erd.png"><img src="render/weasyprint/diagrams__kroki-erd.png" width="200" alt="diagrams__kroki-erd in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-erd.png"><img src="render/weasysvg/diagrams__kroki-erd.png" width="200" alt="diagrams__kroki-erd in weasysvg"></a> |

### diagrams__kroki-excalidraw

[`diagrams/kroki-excalidraw.svg`](svg/diagrams/kroki-excalidraw.svg). WeasyPrint: font, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-excalidraw.png"><img src="render/chromium/diagrams__kroki-excalidraw.png" width="200" alt="diagrams__kroki-excalidraw in Chromium"></a> | <a href="render/resvg/diagrams__kroki-excalidraw.png"><img src="render/resvg/diagrams__kroki-excalidraw.png" width="200" alt="diagrams__kroki-excalidraw in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-excalidraw.png"><img src="render/weasyprint/diagrams__kroki-excalidraw.png" width="200" alt="diagrams__kroki-excalidraw in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-excalidraw.png"><img src="render/weasysvg/diagrams__kroki-excalidraw.png" width="200" alt="diagrams__kroki-excalidraw in weasysvg"></a> |

### diagrams__kroki-graphviz

[`diagrams/kroki-graphviz.svg`](svg/diagrams/kroki-graphviz.svg). WeasyPrint: font, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-graphviz.png"><img src="render/chromium/diagrams__kroki-graphviz.png" width="200" alt="diagrams__kroki-graphviz in Chromium"></a> | <a href="render/resvg/diagrams__kroki-graphviz.png"><img src="render/resvg/diagrams__kroki-graphviz.png" width="200" alt="diagrams__kroki-graphviz in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-graphviz.png"><img src="render/weasyprint/diagrams__kroki-graphviz.png" width="200" alt="diagrams__kroki-graphviz in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-graphviz.png"><img src="render/weasysvg/diagrams__kroki-graphviz.png" width="200" alt="diagrams__kroki-graphviz in weasysvg"></a> |

### diagrams__kroki-mermaid-er

[`diagrams/kroki-mermaid-er.svg`](svg/diagrams/kroki-mermaid-er.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-mermaid-er.png"><img src="render/chromium/diagrams__kroki-mermaid-er.png" width="200" alt="diagrams__kroki-mermaid-er in Chromium"></a> | <a href="render/resvg/diagrams__kroki-mermaid-er.png"><img src="render/resvg/diagrams__kroki-mermaid-er.png" width="200" alt="diagrams__kroki-mermaid-er in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-mermaid-er.png"><img src="render/weasyprint/diagrams__kroki-mermaid-er.png" width="200" alt="diagrams__kroki-mermaid-er in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-mermaid-er.png"><img src="render/weasysvg/diagrams__kroki-mermaid-er.png" width="200" alt="diagrams__kroki-mermaid-er in weasysvg"></a> |

### diagrams__kroki-mermaid-mindmap

[`diagrams/kroki-mermaid-mindmap.svg`](svg/diagrams/kroki-mermaid-mindmap.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-mermaid-mindmap.png"><img src="render/chromium/diagrams__kroki-mermaid-mindmap.png" width="200" alt="diagrams__kroki-mermaid-mindmap in Chromium"></a> | <a href="render/resvg/diagrams__kroki-mermaid-mindmap.png"><img src="render/resvg/diagrams__kroki-mermaid-mindmap.png" width="200" alt="diagrams__kroki-mermaid-mindmap in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-mermaid-mindmap.png"><img src="render/weasyprint/diagrams__kroki-mermaid-mindmap.png" width="200" alt="diagrams__kroki-mermaid-mindmap in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-mermaid-mindmap.png"><img src="render/weasysvg/diagrams__kroki-mermaid-mindmap.png" width="200" alt="diagrams__kroki-mermaid-mindmap in weasysvg"></a> |

### diagrams__kroki-mermaid-state

[`diagrams/kroki-mermaid-state.svg`](svg/diagrams/kroki-mermaid-state.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-mermaid-state.png"><img src="render/chromium/diagrams__kroki-mermaid-state.png" width="200" alt="diagrams__kroki-mermaid-state in Chromium"></a> | <a href="render/resvg/diagrams__kroki-mermaid-state.png"><img src="render/resvg/diagrams__kroki-mermaid-state.png" width="200" alt="diagrams__kroki-mermaid-state in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-mermaid-state.png"><img src="render/weasyprint/diagrams__kroki-mermaid-state.png" width="200" alt="diagrams__kroki-mermaid-state in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-mermaid-state.png"><img src="render/weasysvg/diagrams__kroki-mermaid-state.png" width="200" alt="diagrams__kroki-mermaid-state in weasysvg"></a> |

### diagrams__kroki-nomnoml

[`diagrams/kroki-nomnoml.svg`](svg/diagrams/kroki-nomnoml.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-nomnoml.png"><img src="render/chromium/diagrams__kroki-nomnoml.png" width="200" alt="diagrams__kroki-nomnoml in Chromium"></a> | <a href="render/resvg/diagrams__kroki-nomnoml.png"><img src="render/resvg/diagrams__kroki-nomnoml.png" width="200" alt="diagrams__kroki-nomnoml in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-nomnoml.png"><img src="render/weasyprint/diagrams__kroki-nomnoml.png" width="200" alt="diagrams__kroki-nomnoml in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-nomnoml.png"><img src="render/weasysvg/diagrams__kroki-nomnoml.png" width="200" alt="diagrams__kroki-nomnoml in weasysvg"></a> |

### diagrams__kroki-pikchr

[`diagrams/kroki-pikchr.svg`](svg/diagrams/kroki-pikchr.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-pikchr.png"><img src="render/chromium/diagrams__kroki-pikchr.png" width="200" alt="diagrams__kroki-pikchr in Chromium"></a> | <a href="render/resvg/diagrams__kroki-pikchr.png"><img src="render/resvg/diagrams__kroki-pikchr.png" width="200" alt="diagrams__kroki-pikchr in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-pikchr.png"><img src="render/weasyprint/diagrams__kroki-pikchr.png" width="200" alt="diagrams__kroki-pikchr in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-pikchr.png"><img src="render/weasysvg/diagrams__kroki-pikchr.png" width="200" alt="diagrams__kroki-pikchr in weasysvg"></a> |

### diagrams__kroki-plantuml-activity

[`diagrams/kroki-plantuml-activity.svg`](svg/diagrams/kroki-plantuml-activity.svg). WeasyPrint: minor, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-plantuml-activity.png"><img src="render/chromium/diagrams__kroki-plantuml-activity.png" width="200" alt="diagrams__kroki-plantuml-activity in Chromium"></a> | <a href="render/resvg/diagrams__kroki-plantuml-activity.png"><img src="render/resvg/diagrams__kroki-plantuml-activity.png" width="200" alt="diagrams__kroki-plantuml-activity in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-plantuml-activity.png"><img src="render/weasyprint/diagrams__kroki-plantuml-activity.png" width="200" alt="diagrams__kroki-plantuml-activity in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-plantuml-activity.png"><img src="render/weasysvg/diagrams__kroki-plantuml-activity.png" width="200" alt="diagrams__kroki-plantuml-activity in weasysvg"></a> |

### diagrams__kroki-plantuml-sequence

[`diagrams/kroki-plantuml-sequence.svg`](svg/diagrams/kroki-plantuml-sequence.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-plantuml-sequence.png"><img src="render/chromium/diagrams__kroki-plantuml-sequence.png" width="200" alt="diagrams__kroki-plantuml-sequence in Chromium"></a> | <a href="render/resvg/diagrams__kroki-plantuml-sequence.png"><img src="render/resvg/diagrams__kroki-plantuml-sequence.png" width="200" alt="diagrams__kroki-plantuml-sequence in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-plantuml-sequence.png"><img src="render/weasyprint/diagrams__kroki-plantuml-sequence.png" width="200" alt="diagrams__kroki-plantuml-sequence in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-plantuml-sequence.png"><img src="render/weasysvg/diagrams__kroki-plantuml-sequence.png" width="200" alt="diagrams__kroki-plantuml-sequence in weasysvg"></a> |

### diagrams__kroki-structurizr

[`diagrams/kroki-structurizr.svg`](svg/diagrams/kroki-structurizr.svg). WeasyPrint: font, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-structurizr.png"><img src="render/chromium/diagrams__kroki-structurizr.png" width="200" alt="diagrams__kroki-structurizr in Chromium"></a> | <a href="render/resvg/diagrams__kroki-structurizr.png"><img src="render/resvg/diagrams__kroki-structurizr.png" width="200" alt="diagrams__kroki-structurizr in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-structurizr.png"><img src="render/weasyprint/diagrams__kroki-structurizr.png" width="200" alt="diagrams__kroki-structurizr in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-structurizr.png"><img src="render/weasysvg/diagrams__kroki-structurizr.png" width="200" alt="diagrams__kroki-structurizr in weasysvg"></a> |

### diagrams__kroki-svgbob

[`diagrams/kroki-svgbob.svg`](svg/diagrams/kroki-svgbob.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-svgbob.png"><img src="render/chromium/diagrams__kroki-svgbob.png" width="200" alt="diagrams__kroki-svgbob in Chromium"></a> | <a href="render/resvg/diagrams__kroki-svgbob.png"><img src="render/resvg/diagrams__kroki-svgbob.png" width="200" alt="diagrams__kroki-svgbob in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-svgbob.png"><img src="render/weasyprint/diagrams__kroki-svgbob.png" width="200" alt="diagrams__kroki-svgbob in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-svgbob.png"><img src="render/weasysvg/diagrams__kroki-svgbob.png" width="200" alt="diagrams__kroki-svgbob in weasysvg"></a> |

### diagrams__kroki-vegalite

[`diagrams/kroki-vegalite.svg`](svg/diagrams/kroki-vegalite.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-vegalite.png"><img src="render/chromium/diagrams__kroki-vegalite.png" width="200" alt="diagrams__kroki-vegalite in Chromium"></a> | <a href="render/resvg/diagrams__kroki-vegalite.png"><img src="render/resvg/diagrams__kroki-vegalite.png" width="200" alt="diagrams__kroki-vegalite in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-vegalite.png"><img src="render/weasyprint/diagrams__kroki-vegalite.png" width="200" alt="diagrams__kroki-vegalite in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-vegalite.png"><img src="render/weasysvg/diagrams__kroki-vegalite.png" width="200" alt="diagrams__kroki-vegalite in weasysvg"></a> |

### diagrams__kroki-wavedrom

[`diagrams/kroki-wavedrom.svg`](svg/diagrams/kroki-wavedrom.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__kroki-wavedrom.png"><img src="render/chromium/diagrams__kroki-wavedrom.png" width="200" alt="diagrams__kroki-wavedrom in Chromium"></a> | <a href="render/resvg/diagrams__kroki-wavedrom.png"><img src="render/resvg/diagrams__kroki-wavedrom.png" width="200" alt="diagrams__kroki-wavedrom in resvg"></a> | <a href="render/weasyprint/diagrams__kroki-wavedrom.png"><img src="render/weasyprint/diagrams__kroki-wavedrom.png" width="200" alt="diagrams__kroki-wavedrom in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__kroki-wavedrom.png"><img src="render/weasysvg/diagrams__kroki-wavedrom.png" width="200" alt="diagrams__kroki-wavedrom in weasysvg"></a> |

### diagrams__mermaid-ink-class

[`diagrams/mermaid-ink-class.svg`](svg/diagrams/mermaid-ink-class.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-class.png"><img src="render/chromium/diagrams__mermaid-ink-class.png" width="200" alt="diagrams__mermaid-ink-class in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-class.png"><img src="render/resvg/diagrams__mermaid-ink-class.png" width="200" alt="diagrams__mermaid-ink-class in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-class.png"><img src="render/weasyprint/diagrams__mermaid-ink-class.png" width="200" alt="diagrams__mermaid-ink-class in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-class.png"><img src="render/weasysvg/diagrams__mermaid-ink-class.png" width="200" alt="diagrams__mermaid-ink-class in weasysvg"></a> |

### diagrams__mermaid-ink-er

[`diagrams/mermaid-ink-er.svg`](svg/diagrams/mermaid-ink-er.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-er.png"><img src="render/chromium/diagrams__mermaid-ink-er.png" width="200" alt="diagrams__mermaid-ink-er in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-er.png"><img src="render/resvg/diagrams__mermaid-ink-er.png" width="200" alt="diagrams__mermaid-ink-er in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-er.png"><img src="render/weasyprint/diagrams__mermaid-ink-er.png" width="200" alt="diagrams__mermaid-ink-er in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-er.png"><img src="render/weasysvg/diagrams__mermaid-ink-er.png" width="200" alt="diagrams__mermaid-ink-er in weasysvg"></a> |

### diagrams__mermaid-ink-flowchart

[`diagrams/mermaid-ink-flowchart.svg`](svg/diagrams/mermaid-ink-flowchart.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-flowchart.png"><img src="render/chromium/diagrams__mermaid-ink-flowchart.png" width="200" alt="diagrams__mermaid-ink-flowchart in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-flowchart.png"><img src="render/resvg/diagrams__mermaid-ink-flowchart.png" width="200" alt="diagrams__mermaid-ink-flowchart in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-flowchart.png"><img src="render/weasyprint/diagrams__mermaid-ink-flowchart.png" width="200" alt="diagrams__mermaid-ink-flowchart in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-flowchart.png"><img src="render/weasysvg/diagrams__mermaid-ink-flowchart.png" width="200" alt="diagrams__mermaid-ink-flowchart in weasysvg"></a> |

### diagrams__mermaid-ink-gantt

[`diagrams/mermaid-ink-gantt.svg`](svg/diagrams/mermaid-ink-gantt.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-gantt.png"><img src="render/chromium/diagrams__mermaid-ink-gantt.png" width="200" alt="diagrams__mermaid-ink-gantt in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-gantt.png"><img src="render/resvg/diagrams__mermaid-ink-gantt.png" width="200" alt="diagrams__mermaid-ink-gantt in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-gantt.png"><img src="render/weasyprint/diagrams__mermaid-ink-gantt.png" width="200" alt="diagrams__mermaid-ink-gantt in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-gantt.png"><img src="render/weasysvg/diagrams__mermaid-ink-gantt.png" width="200" alt="diagrams__mermaid-ink-gantt in weasysvg"></a> |

### diagrams__mermaid-ink-gitgraph

[`diagrams/mermaid-ink-gitgraph.svg`](svg/diagrams/mermaid-ink-gitgraph.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-gitgraph.png"><img src="render/chromium/diagrams__mermaid-ink-gitgraph.png" width="200" alt="diagrams__mermaid-ink-gitgraph in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-gitgraph.png"><img src="render/resvg/diagrams__mermaid-ink-gitgraph.png" width="200" alt="diagrams__mermaid-ink-gitgraph in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-gitgraph.png"><img src="render/weasyprint/diagrams__mermaid-ink-gitgraph.png" width="200" alt="diagrams__mermaid-ink-gitgraph in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-gitgraph.png"><img src="render/weasysvg/diagrams__mermaid-ink-gitgraph.png" width="200" alt="diagrams__mermaid-ink-gitgraph in weasysvg"></a> |

### diagrams__mermaid-ink-journey

[`diagrams/mermaid-ink-journey.svg`](svg/diagrams/mermaid-ink-journey.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-journey.png"><img src="render/chromium/diagrams__mermaid-ink-journey.png" width="200" alt="diagrams__mermaid-ink-journey in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-journey.png"><img src="render/resvg/diagrams__mermaid-ink-journey.png" width="200" alt="diagrams__mermaid-ink-journey in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-journey.png"><img src="render/weasyprint/diagrams__mermaid-ink-journey.png" width="200" alt="diagrams__mermaid-ink-journey in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-journey.png"><img src="render/weasysvg/diagrams__mermaid-ink-journey.png" width="200" alt="diagrams__mermaid-ink-journey in weasysvg"></a> |

### diagrams__mermaid-ink-mindmap

[`diagrams/mermaid-ink-mindmap.svg`](svg/diagrams/mermaid-ink-mindmap.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-mindmap.png"><img src="render/chromium/diagrams__mermaid-ink-mindmap.png" width="200" alt="diagrams__mermaid-ink-mindmap in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-mindmap.png"><img src="render/resvg/diagrams__mermaid-ink-mindmap.png" width="200" alt="diagrams__mermaid-ink-mindmap in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-mindmap.png"><img src="render/weasyprint/diagrams__mermaid-ink-mindmap.png" width="200" alt="diagrams__mermaid-ink-mindmap in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-mindmap.png"><img src="render/weasysvg/diagrams__mermaid-ink-mindmap.png" width="200" alt="diagrams__mermaid-ink-mindmap in weasysvg"></a> |

### diagrams__mermaid-ink-pie

[`diagrams/mermaid-ink-pie.svg`](svg/diagrams/mermaid-ink-pie.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-pie.png"><img src="render/chromium/diagrams__mermaid-ink-pie.png" width="200" alt="diagrams__mermaid-ink-pie in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-pie.png"><img src="render/resvg/diagrams__mermaid-ink-pie.png" width="200" alt="diagrams__mermaid-ink-pie in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-pie.png"><img src="render/weasyprint/diagrams__mermaid-ink-pie.png" width="200" alt="diagrams__mermaid-ink-pie in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-pie.png"><img src="render/weasysvg/diagrams__mermaid-ink-pie.png" width="200" alt="diagrams__mermaid-ink-pie in weasysvg"></a> |

### diagrams__mermaid-ink-sequence

[`diagrams/mermaid-ink-sequence.svg`](svg/diagrams/mermaid-ink-sequence.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-sequence.png"><img src="render/chromium/diagrams__mermaid-ink-sequence.png" width="200" alt="diagrams__mermaid-ink-sequence in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-sequence.png"><img src="render/resvg/diagrams__mermaid-ink-sequence.png" width="200" alt="diagrams__mermaid-ink-sequence in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-sequence.png"><img src="render/weasyprint/diagrams__mermaid-ink-sequence.png" width="200" alt="diagrams__mermaid-ink-sequence in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-sequence.png"><img src="render/weasysvg/diagrams__mermaid-ink-sequence.png" width="200" alt="diagrams__mermaid-ink-sequence in weasysvg"></a> |

### diagrams__mermaid-ink-state

[`diagrams/mermaid-ink-state.svg`](svg/diagrams/mermaid-ink-state.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/diagrams__mermaid-ink-state.png"><img src="render/chromium/diagrams__mermaid-ink-state.png" width="200" alt="diagrams__mermaid-ink-state in Chromium"></a> | <a href="render/resvg/diagrams__mermaid-ink-state.png"><img src="render/resvg/diagrams__mermaid-ink-state.png" width="200" alt="diagrams__mermaid-ink-state in resvg"></a> | <a href="render/weasyprint/diagrams__mermaid-ink-state.png"><img src="render/weasyprint/diagrams__mermaid-ink-state.png" width="200" alt="diagrams__mermaid-ink-state in WeasyPrint"></a> | <a href="render/weasysvg/diagrams__mermaid-ink-state.png"><img src="render/weasysvg/diagrams__mermaid-ink-state.png" width="200" alt="diagrams__mermaid-ink-state in weasysvg"></a> |

## draw.io

### drawio__connect-shapes

[`drawio/connect-shapes.svg`](svg/drawio/connect-shapes.svg). WeasyPrint: minor, weasysvg: **same**. Remote GIFs are blocked in all three renderings (policy).

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__connect-shapes.png"><img src="render/chromium/drawio__connect-shapes.png" width="200" alt="drawio__connect-shapes in Chromium"></a> | <a href="render/resvg/drawio__connect-shapes.png"><img src="render/resvg/drawio__connect-shapes.png" width="200" alt="drawio__connect-shapes in resvg"></a> | <a href="render/weasyprint/drawio__connect-shapes.png"><img src="render/weasyprint/drawio__connect-shapes.png" width="200" alt="drawio__connect-shapes in WeasyPrint"></a> | <a href="render/weasysvg/drawio__connect-shapes.png"><img src="render/weasysvg/drawio__connect-shapes.png" width="200" alt="drawio__connect-shapes in weasysvg"></a> |

### drawio__flowchart.drawio

[`drawio/flowchart.drawio.svg`](svg/drawio/flowchart.drawio.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__flowchart.drawio.png"><img src="render/chromium/drawio__flowchart.drawio.png" width="200" alt="drawio__flowchart.drawio in Chromium"></a> | <a href="render/resvg/drawio__flowchart.drawio.png"><img src="render/resvg/drawio__flowchart.drawio.png" width="200" alt="drawio__flowchart.drawio in resvg"></a> | <a href="render/weasyprint/drawio__flowchart.drawio.png"><img src="render/weasyprint/drawio__flowchart.drawio.png" width="200" alt="drawio__flowchart.drawio in WeasyPrint"></a> | <a href="render/weasysvg/drawio__flowchart.drawio.png"><img src="render/weasysvg/drawio__flowchart.drawio.png" width="200" alt="drawio__flowchart.drawio in weasysvg"></a> |

### drawio__infographic

[`drawio/infographic.svg`](svg/drawio/infographic.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__infographic.png"><img src="render/chromium/drawio__infographic.png" width="200" alt="drawio__infographic in Chromium"></a> | <a href="render/resvg/drawio__infographic.png"><img src="render/resvg/drawio__infographic.png" width="200" alt="drawio__infographic in resvg"></a> | <a href="render/weasyprint/drawio__infographic.png"><img src="render/weasyprint/drawio__infographic.png" width="200" alt="drawio__infographic in WeasyPrint"></a> | <a href="render/weasysvg/drawio__infographic.png"><img src="render/weasysvg/drawio__infographic.png" width="200" alt="drawio__infographic in weasysvg"></a> |

### drawio__infographic2

[`drawio/infographic2.svg`](svg/drawio/infographic2.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__infographic2.png"><img src="render/chromium/drawio__infographic2.png" width="200" alt="drawio__infographic2 in Chromium"></a> | <a href="render/resvg/drawio__infographic2.png"><img src="render/resvg/drawio__infographic2.png" width="200" alt="drawio__infographic2 in resvg"></a> | <a href="render/weasyprint/drawio__infographic2.png"><img src="render/weasyprint/drawio__infographic2.png" width="200" alt="drawio__infographic2 in WeasyPrint"></a> | <a href="render/weasysvg/drawio__infographic2.png"><img src="render/weasysvg/drawio__infographic2.png" width="200" alt="drawio__infographic2 in weasysvg"></a> |

### drawio__notion-template.drawio

[`drawio/notion-template.drawio.svg`](svg/drawio/notion-template.drawio.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__notion-template.drawio.png"><img src="render/chromium/drawio__notion-template.drawio.png" width="200" alt="drawio__notion-template.drawio in Chromium"></a> | <a href="render/resvg/drawio__notion-template.drawio.png"><img src="render/resvg/drawio__notion-template.drawio.png" width="200" alt="drawio__notion-template.drawio in resvg"></a> | <a href="render/weasyprint/drawio__notion-template.drawio.png"><img src="render/weasyprint/drawio__notion-template.drawio.png" width="200" alt="drawio__notion-template.drawio in WeasyPrint"></a> | <a href="render/weasysvg/drawio__notion-template.drawio.png"><img src="render/weasysvg/drawio__notion-template.drawio.png" width="200" alt="drawio__notion-template.drawio in weasysvg"></a> |

### drawio__svgfile

[`drawio/svgfile.svg`](svg/drawio/svgfile.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/drawio__svgfile.png"><img src="render/chromium/drawio__svgfile.png" width="200" alt="drawio__svgfile in Chromium"></a> | <a href="render/resvg/drawio__svgfile.png"><img src="render/resvg/drawio__svgfile.png" width="200" alt="drawio__svgfile in resvg"></a> | <a href="render/weasyprint/drawio__svgfile.png"><img src="render/weasyprint/drawio__svgfile.png" width="200" alt="drawio__svgfile in WeasyPrint"></a> | <a href="render/weasysvg/drawio__svgfile.png"><img src="render/weasysvg/drawio__svgfile.png" width="200" alt="drawio__svgfile in weasysvg"></a> |

## foreignObject

### fo__mdn-foreignobject

[`fo/mdn-foreignobject.svg`](svg/fo/mdn-foreignobject.svg). WeasyPrint: broken, weasysvg: **minor**. No scrollbar on the overflow:auto box, so text reflows into that width; harmless in print.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/fo__mdn-foreignobject.png"><img src="render/chromium/fo__mdn-foreignobject.png" width="200" alt="fo__mdn-foreignobject in Chromium"></a> | <a href="render/resvg/fo__mdn-foreignobject.png"><img src="render/resvg/fo__mdn-foreignobject.png" width="200" alt="fo__mdn-foreignobject in resvg"></a> | <a href="render/weasyprint/fo__mdn-foreignobject.png"><img src="render/weasyprint/fo__mdn-foreignobject.png" width="200" alt="fo__mdn-foreignobject in WeasyPrint"></a> | <a href="render/weasysvg/fo__mdn-foreignobject.png"><img src="render/weasysvg/fo__mdn-foreignobject.png" width="200" alt="fo__mdn-foreignobject in weasysvg"></a> |

### fo__rich-html

[`fo/rich-html.svg`](svg/fo/rich-html.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/fo__rich-html.png"><img src="render/chromium/fo__rich-html.png" width="200" alt="fo__rich-html in Chromium"></a> | <a href="render/resvg/fo__rich-html.png"><img src="render/resvg/fo__rich-html.png" width="200" alt="fo__rich-html in resvg"></a> | <a href="render/weasyprint/fo__rich-html.png"><img src="render/weasyprint/fo__rich-html.png" width="200" alt="fo__rich-html in WeasyPrint"></a> | <a href="render/weasysvg/fo__rich-html.png"><img src="render/weasysvg/fo__rich-html.png" width="200" alt="fo__rich-html in weasysvg"></a> |

## Wikimedia Commons

### real__wm-Bitmap_VS_SVG

[`real/wm-Bitmap_VS_SVG.svg`](svg/real/wm-Bitmap_VS_SVG.svg). WeasyPrint: broken, weasysvg: **same**. Shows &#x27;Raster&#x27;/&#x27;Vector&#x27; via switch, spec-correct for English; Chromium shows no heading.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Bitmap_VS_SVG.png"><img src="render/chromium/real__wm-Bitmap_VS_SVG.png" width="200" alt="real__wm-Bitmap_VS_SVG in Chromium"></a> | <a href="render/resvg/real__wm-Bitmap_VS_SVG.png"><img src="render/resvg/real__wm-Bitmap_VS_SVG.png" width="200" alt="real__wm-Bitmap_VS_SVG in resvg"></a> | <a href="render/weasyprint/real__wm-Bitmap_VS_SVG.png"><img src="render/weasyprint/real__wm-Bitmap_VS_SVG.png" width="200" alt="real__wm-Bitmap_VS_SVG in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Bitmap_VS_SVG.png"><img src="render/weasysvg/real__wm-Bitmap_VS_SVG.png" width="200" alt="real__wm-Bitmap_VS_SVG in weasysvg"></a> |

### real__wm-Flag_of_Brazil

[`real/wm-Flag_of_Brazil.svg`](svg/real/wm-Flag_of_Brazil.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Flag_of_Brazil.png"><img src="render/chromium/real__wm-Flag_of_Brazil.png" width="200" alt="real__wm-Flag_of_Brazil in Chromium"></a> | <a href="render/resvg/real__wm-Flag_of_Brazil.png"><img src="render/resvg/real__wm-Flag_of_Brazil.png" width="200" alt="real__wm-Flag_of_Brazil in resvg"></a> | <a href="render/weasyprint/real__wm-Flag_of_Brazil.png"><img src="render/weasyprint/real__wm-Flag_of_Brazil.png" width="200" alt="real__wm-Flag_of_Brazil in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Flag_of_Brazil.png"><img src="render/weasysvg/real__wm-Flag_of_Brazil.png" width="200" alt="real__wm-Flag_of_Brazil in weasysvg"></a> |

### real__wm-Flag_of_Switzerland

[`real/wm-Flag_of_Switzerland.svg`](svg/real/wm-Flag_of_Switzerland.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Flag_of_Switzerland.png"><img src="render/chromium/real__wm-Flag_of_Switzerland.png" width="200" alt="real__wm-Flag_of_Switzerland in Chromium"></a> | <a href="render/resvg/real__wm-Flag_of_Switzerland.png"><img src="render/resvg/real__wm-Flag_of_Switzerland.png" width="200" alt="real__wm-Flag_of_Switzerland in resvg"></a> | <a href="render/weasyprint/real__wm-Flag_of_Switzerland.png"><img src="render/weasyprint/real__wm-Flag_of_Switzerland.png" width="200" alt="real__wm-Flag_of_Switzerland in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Flag_of_Switzerland.png"><img src="render/weasysvg/real__wm-Flag_of_Switzerland.png" width="200" alt="real__wm-Flag_of_Switzerland in weasysvg"></a> |

### real__wm-Flag_of_the_United_Kingdom

[`real/wm-Flag_of_the_United_Kingdom.svg`](svg/real/wm-Flag_of_the_United_Kingdom.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Flag_of_the_United_Kingdom.png"><img src="render/chromium/real__wm-Flag_of_the_United_Kingdom.png" width="200" alt="real__wm-Flag_of_the_United_Kingdom in Chromium"></a> | <a href="render/resvg/real__wm-Flag_of_the_United_Kingdom.png"><img src="render/resvg/real__wm-Flag_of_the_United_Kingdom.png" width="200" alt="real__wm-Flag_of_the_United_Kingdom in resvg"></a> | <a href="render/weasyprint/real__wm-Flag_of_the_United_Kingdom.png"><img src="render/weasyprint/real__wm-Flag_of_the_United_Kingdom.png" width="200" alt="real__wm-Flag_of_the_United_Kingdom in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Flag_of_the_United_Kingdom.png"><img src="render/weasysvg/real__wm-Flag_of_the_United_Kingdom.png" width="200" alt="real__wm-Flag_of_the_United_Kingdom in weasysvg"></a> |

### real__wm-Git-logo

[`real/wm-Git-logo.svg`](svg/real/wm-Git-logo.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Git-logo.png"><img src="render/chromium/real__wm-Git-logo.png" width="200" alt="real__wm-Git-logo in Chromium"></a> | <a href="render/resvg/real__wm-Git-logo.png"><img src="render/resvg/real__wm-Git-logo.png" width="200" alt="real__wm-Git-logo in resvg"></a> | <a href="render/weasyprint/real__wm-Git-logo.png"><img src="render/weasyprint/real__wm-Git-logo.png" width="200" alt="real__wm-Git-logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Git-logo.png"><img src="render/weasysvg/real__wm-Git-logo.png" width="200" alt="real__wm-Git-logo in weasysvg"></a> |

### real__wm-Inkscape_Logo

[`real/wm-Inkscape_Logo.svg`](svg/real/wm-Inkscape_Logo.svg). WeasyPrint: minor, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Inkscape_Logo.png"><img src="render/chromium/real__wm-Inkscape_Logo.png" width="200" alt="real__wm-Inkscape_Logo in Chromium"></a> | <a href="render/resvg/real__wm-Inkscape_Logo.png"><img src="render/resvg/real__wm-Inkscape_Logo.png" width="200" alt="real__wm-Inkscape_Logo in resvg"></a> | <a href="render/weasyprint/real__wm-Inkscape_Logo.png"><img src="render/weasyprint/real__wm-Inkscape_Logo.png" width="200" alt="real__wm-Inkscape_Logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Inkscape_Logo.png"><img src="render/weasysvg/real__wm-Inkscape_Logo.png" width="200" alt="real__wm-Inkscape_Logo in weasysvg"></a> |

### real__wm-Kubernetes_logo_without_workmark

[`real/wm-Kubernetes_logo_without_workmark.svg`](svg/real/wm-Kubernetes_logo_without_workmark.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Kubernetes_logo_without_workmark.png"><img src="render/chromium/real__wm-Kubernetes_logo_without_workmark.png" width="200" alt="real__wm-Kubernetes_logo_without_workmark in Chromium"></a> | <a href="render/resvg/real__wm-Kubernetes_logo_without_workmark.png"><img src="render/resvg/real__wm-Kubernetes_logo_without_workmark.png" width="200" alt="real__wm-Kubernetes_logo_without_workmark in resvg"></a> | <a href="render/weasyprint/real__wm-Kubernetes_logo_without_workmark.png"><img src="render/weasyprint/real__wm-Kubernetes_logo_without_workmark.png" width="200" alt="real__wm-Kubernetes_logo_without_workmark in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Kubernetes_logo_without_workmark.png"><img src="render/weasysvg/real__wm-Kubernetes_logo_without_workmark.png" width="200" alt="real__wm-Kubernetes_logo_without_workmark in weasysvg"></a> |

### real__wm-OSI_Model_v1

[`real/wm-OSI_Model_v1.svg`](svg/real/wm-OSI_Model_v1.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-OSI_Model_v1.png"><img src="render/chromium/real__wm-OSI_Model_v1.png" width="200" alt="real__wm-OSI_Model_v1 in Chromium"></a> | <a href="render/resvg/real__wm-OSI_Model_v1.png"><img src="render/resvg/real__wm-OSI_Model_v1.png" width="200" alt="real__wm-OSI_Model_v1 in resvg"></a> | <a href="render/weasyprint/real__wm-OSI_Model_v1.png"><img src="render/weasyprint/real__wm-OSI_Model_v1.png" width="200" alt="real__wm-OSI_Model_v1 in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-OSI_Model_v1.png"><img src="render/weasysvg/real__wm-OSI_Model_v1.png" width="200" alt="real__wm-OSI_Model_v1 in weasysvg"></a> |

### real__wm-Openstreetmap_logo

[`real/wm-Openstreetmap_logo.svg`](svg/real/wm-Openstreetmap_logo.svg). WeasyPrint: broken, weasysvg: **minor**. Handle and ferrules drawn: the rotated gradient cells cover the shapes. The blurred shadow of the lens ring is a little darker than in Chromium.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Openstreetmap_logo.png"><img src="render/chromium/real__wm-Openstreetmap_logo.png" width="200" alt="real__wm-Openstreetmap_logo in Chromium"></a> | <a href="render/resvg/real__wm-Openstreetmap_logo.png"><img src="render/resvg/real__wm-Openstreetmap_logo.png" width="200" alt="real__wm-Openstreetmap_logo in resvg"></a> | <a href="render/weasyprint/real__wm-Openstreetmap_logo.png"><img src="render/weasyprint/real__wm-Openstreetmap_logo.png" width="200" alt="real__wm-Openstreetmap_logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Openstreetmap_logo.png"><img src="render/weasysvg/real__wm-Openstreetmap_logo.png" width="200" alt="real__wm-Openstreetmap_logo in weasysvg"></a> |

### real__wm-Python-logo-notext

[`real/wm-Python-logo-notext.svg`](svg/real/wm-Python-logo-notext.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Python-logo-notext.png"><img src="render/chromium/real__wm-Python-logo-notext.png" width="200" alt="real__wm-Python-logo-notext in Chromium"></a> | <a href="render/resvg/real__wm-Python-logo-notext.png"><img src="render/resvg/real__wm-Python-logo-notext.png" width="200" alt="real__wm-Python-logo-notext in resvg"></a> | <a href="render/weasyprint/real__wm-Python-logo-notext.png"><img src="render/weasyprint/real__wm-Python-logo-notext.png" width="200" alt="real__wm-Python-logo-notext in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Python-logo-notext.png"><img src="render/weasysvg/real__wm-Python-logo-notext.png" width="200" alt="real__wm-Python-logo-notext in weasysvg"></a> |

### real__wm-SVG_Logo

[`real/wm-SVG_Logo.svg`](svg/real/wm-SVG_Logo.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-SVG_Logo.png"><img src="render/chromium/real__wm-SVG_Logo.png" width="200" alt="real__wm-SVG_Logo in Chromium"></a> | <a href="render/resvg/real__wm-SVG_Logo.png"><img src="render/resvg/real__wm-SVG_Logo.png" width="200" alt="real__wm-SVG_Logo in resvg"></a> | <a href="render/weasyprint/real__wm-SVG_Logo.png"><img src="render/weasyprint/real__wm-SVG_Logo.png" width="200" alt="real__wm-SVG_Logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-SVG_Logo.png"><img src="render/weasysvg/real__wm-SVG_Logo.png" width="200" alt="real__wm-SVG_Logo in weasysvg"></a> |

### real__wm-Simple_Periodic_Table_Chart-blocks

[`real/wm-Simple_Periodic_Table_Chart-blocks.svg`](svg/real/wm-Simple_Periodic_Table_Chart-blocks.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Simple_Periodic_Table_Chart-blocks.png"><img src="render/chromium/real__wm-Simple_Periodic_Table_Chart-blocks.png" width="200" alt="real__wm-Simple_Periodic_Table_Chart-blocks in Chromium"></a> | <a href="render/resvg/real__wm-Simple_Periodic_Table_Chart-blocks.png"><img src="render/resvg/real__wm-Simple_Periodic_Table_Chart-blocks.png" width="200" alt="real__wm-Simple_Periodic_Table_Chart-blocks in resvg"></a> | <a href="render/weasyprint/real__wm-Simple_Periodic_Table_Chart-blocks.png"><img src="render/weasyprint/real__wm-Simple_Periodic_Table_Chart-blocks.png" width="200" alt="real__wm-Simple_Periodic_Table_Chart-blocks in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Simple_Periodic_Table_Chart-blocks.png"><img src="render/weasysvg/real__wm-Simple_Periodic_Table_Chart-blocks.png" width="200" alt="real__wm-Simple_Periodic_Table_Chart-blocks in weasysvg"></a> |

### real__wm-Tux

[`real/wm-Tux.svg`](svg/real/wm-Tux.svg). WeasyPrint: minor, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Tux.png"><img src="render/chromium/real__wm-Tux.png" width="200" alt="real__wm-Tux in Chromium"></a> | <a href="render/resvg/real__wm-Tux.png"><img src="render/resvg/real__wm-Tux.png" width="200" alt="real__wm-Tux in resvg"></a> | <a href="render/weasyprint/real__wm-Tux.png"><img src="render/weasyprint/real__wm-Tux.png" width="200" alt="real__wm-Tux in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Tux.png"><img src="render/weasysvg/real__wm-Tux.png" width="200" alt="real__wm-Tux in weasysvg"></a> |

### real__wm-Wikimedia-logo

[`real/wm-Wikimedia-logo.svg`](svg/real/wm-Wikimedia-logo.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/real__wm-Wikimedia-logo.png"><img src="render/chromium/real__wm-Wikimedia-logo.png" width="200" alt="real__wm-Wikimedia-logo in Chromium"></a> | <a href="render/resvg/real__wm-Wikimedia-logo.png"><img src="render/resvg/real__wm-Wikimedia-logo.png" width="200" alt="real__wm-Wikimedia-logo in resvg"></a> | <a href="render/weasyprint/real__wm-Wikimedia-logo.png"><img src="render/weasyprint/real__wm-Wikimedia-logo.png" width="200" alt="real__wm-Wikimedia-logo in WeasyPrint"></a> | <a href="render/weasysvg/real__wm-Wikimedia-logo.png"><img src="render/weasysvg/real__wm-Wikimedia-logo.png" width="200" alt="real__wm-Wikimedia-logo in weasysvg"></a> |

## resvg feature tests

### resvg__filters-feColorMatrix--type=luminanceToAlpha

[`resvg/filters-feColorMatrix--type=luminanceToAlpha.svg`](svg/resvg/filters-feColorMatrix--type=luminanceToAlpha.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feColorMatrix--type=luminanceToAlpha.png"><img src="render/chromium/resvg__filters-feColorMatrix--type=luminanceToAlpha.png" width="200" alt="resvg__filters-feColorMatrix--type=luminanceToAlpha in Chromium"></a> | <a href="render/resvg/resvg__filters-feColorMatrix--type=luminanceToAlpha.png"><img src="render/resvg/resvg__filters-feColorMatrix--type=luminanceToAlpha.png" width="200" alt="resvg__filters-feColorMatrix--type=luminanceToAlpha in resvg"></a> | <a href="render/weasyprint/resvg__filters-feColorMatrix--type=luminanceToAlpha.png"><img src="render/weasyprint/resvg__filters-feColorMatrix--type=luminanceToAlpha.png" width="200" alt="resvg__filters-feColorMatrix--type=luminanceToAlpha in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feColorMatrix--type=luminanceToAlpha.png"><img src="render/weasysvg/resvg__filters-feColorMatrix--type=luminanceToAlpha.png" width="200" alt="resvg__filters-feColorMatrix--type=luminanceToAlpha in weasysvg"></a> |

### resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values

[`resvg/filters-feColorMatrix--type=matrix-with-non-normalized-values.svg`](svg/resvg/filters-feColorMatrix--type=matrix-with-non-normalized-values.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png"><img src="render/chromium/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png" width="200" alt="resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values in Chromium"></a> | <a href="render/resvg/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png"><img src="render/resvg/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png" width="200" alt="resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values in resvg"></a> | <a href="render/weasyprint/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png"><img src="render/weasyprint/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png" width="200" alt="resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png"><img src="render/weasysvg/resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values.png" width="200" alt="resvg__filters-feColorMatrix--type=matrix-with-non-normalized-values in weasysvg"></a> |

### resvg__filters-feComposite--operator=arithmetic-with-large-k1-4

[`resvg/filters-feComposite--operator=arithmetic-with-large-k1-4.svg`](svg/resvg/filters-feComposite--operator=arithmetic-with-large-k1-4.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png"><img src="render/chromium/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png" width="200" alt="resvg__filters-feComposite--operator=arithmetic-with-large-k1-4 in Chromium"></a> | <a href="render/resvg/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png"><img src="render/resvg/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png" width="200" alt="resvg__filters-feComposite--operator=arithmetic-with-large-k1-4 in resvg"></a> | <a href="render/weasyprint/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png"><img src="render/weasyprint/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png" width="200" alt="resvg__filters-feComposite--operator=arithmetic-with-large-k1-4 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png"><img src="render/weasysvg/resvg__filters-feComposite--operator=arithmetic-with-large-k1-4.png" width="200" alt="resvg__filters-feComposite--operator=arithmetic-with-large-k1-4 in weasysvg"></a> |

### resvg__filters-feComposite--operator=over

[`resvg/filters-feComposite--operator=over.svg`](svg/resvg/filters-feComposite--operator=over.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feComposite--operator=over.png"><img src="render/chromium/resvg__filters-feComposite--operator=over.png" width="200" alt="resvg__filters-feComposite--operator=over in Chromium"></a> | <a href="render/resvg/resvg__filters-feComposite--operator=over.png"><img src="render/resvg/resvg__filters-feComposite--operator=over.png" width="200" alt="resvg__filters-feComposite--operator=over in resvg"></a> | <a href="render/weasyprint/resvg__filters-feComposite--operator=over.png"><img src="render/weasyprint/resvg__filters-feComposite--operator=over.png" width="200" alt="resvg__filters-feComposite--operator=over in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feComposite--operator=over.png"><img src="render/weasysvg/resvg__filters-feComposite--operator=over.png" width="200" alt="resvg__filters-feComposite--operator=over in weasysvg"></a> |

### resvg__filters-feDropShadow--hsla-color

[`resvg/filters-feDropShadow--hsla-color.svg`](svg/resvg/filters-feDropShadow--hsla-color.svg). WeasyPrint: minor, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feDropShadow--hsla-color.png"><img src="render/chromium/resvg__filters-feDropShadow--hsla-color.png" width="200" alt="resvg__filters-feDropShadow--hsla-color in Chromium"></a> | <a href="render/resvg/resvg__filters-feDropShadow--hsla-color.png"><img src="render/resvg/resvg__filters-feDropShadow--hsla-color.png" width="200" alt="resvg__filters-feDropShadow--hsla-color in resvg"></a> | <a href="render/weasyprint/resvg__filters-feDropShadow--hsla-color.png"><img src="render/weasyprint/resvg__filters-feDropShadow--hsla-color.png" width="200" alt="resvg__filters-feDropShadow--hsla-color in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feDropShadow--hsla-color.png"><img src="render/weasysvg/resvg__filters-feDropShadow--hsla-color.png" width="200" alt="resvg__filters-feDropShadow--hsla-color in weasysvg"></a> |

### resvg__filters-feDropShadow--with-percent-offset

[`resvg/filters-feDropShadow--with-percent-offset.svg`](svg/resvg/filters-feDropShadow--with-percent-offset.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feDropShadow--with-percent-offset.png"><img src="render/chromium/resvg__filters-feDropShadow--with-percent-offset.png" width="200" alt="resvg__filters-feDropShadow--with-percent-offset in Chromium"></a> | <a href="render/resvg/resvg__filters-feDropShadow--with-percent-offset.png"><img src="render/resvg/resvg__filters-feDropShadow--with-percent-offset.png" width="200" alt="resvg__filters-feDropShadow--with-percent-offset in resvg"></a> | <a href="render/weasyprint/resvg__filters-feDropShadow--with-percent-offset.png"><img src="render/weasyprint/resvg__filters-feDropShadow--with-percent-offset.png" width="200" alt="resvg__filters-feDropShadow--with-percent-offset in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feDropShadow--with-percent-offset.png"><img src="render/weasysvg/resvg__filters-feDropShadow--with-percent-offset.png" width="200" alt="resvg__filters-feDropShadow--with-percent-offset in weasysvg"></a> |

### resvg__filters-feFlood--seagreen

[`resvg/filters-feFlood--seagreen.svg`](svg/resvg/filters-feFlood--seagreen.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feFlood--seagreen.png"><img src="render/chromium/resvg__filters-feFlood--seagreen.png" width="200" alt="resvg__filters-feFlood--seagreen in Chromium"></a> | <a href="render/resvg/resvg__filters-feFlood--seagreen.png"><img src="render/resvg/resvg__filters-feFlood--seagreen.png" width="200" alt="resvg__filters-feFlood--seagreen in resvg"></a> | <a href="render/weasyprint/resvg__filters-feFlood--seagreen.png"><img src="render/weasyprint/resvg__filters-feFlood--seagreen.png" width="200" alt="resvg__filters-feFlood--seagreen in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feFlood--seagreen.png"><img src="render/weasysvg/resvg__filters-feFlood--seagreen.png" width="200" alt="resvg__filters-feFlood--seagreen in weasysvg"></a> |

### resvg__filters-feFlood--with-opacity-on-target-element

[`resvg/filters-feFlood--with-opacity-on-target-element.svg`](svg/resvg/filters-feFlood--with-opacity-on-target-element.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feFlood--with-opacity-on-target-element.png"><img src="render/chromium/resvg__filters-feFlood--with-opacity-on-target-element.png" width="200" alt="resvg__filters-feFlood--with-opacity-on-target-element in Chromium"></a> | <a href="render/resvg/resvg__filters-feFlood--with-opacity-on-target-element.png"><img src="render/resvg/resvg__filters-feFlood--with-opacity-on-target-element.png" width="200" alt="resvg__filters-feFlood--with-opacity-on-target-element in resvg"></a> | <a href="render/weasyprint/resvg__filters-feFlood--with-opacity-on-target-element.png"><img src="render/weasyprint/resvg__filters-feFlood--with-opacity-on-target-element.png" width="200" alt="resvg__filters-feFlood--with-opacity-on-target-element in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feFlood--with-opacity-on-target-element.png"><img src="render/weasysvg/resvg__filters-feFlood--with-opacity-on-target-element.png" width="200" alt="resvg__filters-feFlood--with-opacity-on-target-element in weasysvg"></a> |

### resvg__filters-feGaussianBlur--small-stdDeviation

[`resvg/filters-feGaussianBlur--small-stdDeviation.svg`](svg/resvg/filters-feGaussianBlur--small-stdDeviation.svg). WeasyPrint: minor, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feGaussianBlur--small-stdDeviation.png"><img src="render/chromium/resvg__filters-feGaussianBlur--small-stdDeviation.png" width="200" alt="resvg__filters-feGaussianBlur--small-stdDeviation in Chromium"></a> | <a href="render/resvg/resvg__filters-feGaussianBlur--small-stdDeviation.png"><img src="render/resvg/resvg__filters-feGaussianBlur--small-stdDeviation.png" width="200" alt="resvg__filters-feGaussianBlur--small-stdDeviation in resvg"></a> | <a href="render/weasyprint/resvg__filters-feGaussianBlur--small-stdDeviation.png"><img src="render/weasyprint/resvg__filters-feGaussianBlur--small-stdDeviation.png" width="200" alt="resvg__filters-feGaussianBlur--small-stdDeviation in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feGaussianBlur--small-stdDeviation.png"><img src="render/weasysvg/resvg__filters-feGaussianBlur--small-stdDeviation.png" width="200" alt="resvg__filters-feGaussianBlur--small-stdDeviation in weasysvg"></a> |

### resvg__filters-feGaussianBlur--stdDeviation=0-5

[`resvg/filters-feGaussianBlur--stdDeviation=0-5.svg`](svg/resvg/filters-feGaussianBlur--stdDeviation=0-5.svg). WeasyPrint: broken, weasysvg: **minor**. Blurred along x as well: the vector blur uses the mean of the two deviations.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feGaussianBlur--stdDeviation=0-5.png"><img src="render/chromium/resvg__filters-feGaussianBlur--stdDeviation=0-5.png" width="200" alt="resvg__filters-feGaussianBlur--stdDeviation=0-5 in Chromium"></a> | <a href="render/resvg/resvg__filters-feGaussianBlur--stdDeviation=0-5.png"><img src="render/resvg/resvg__filters-feGaussianBlur--stdDeviation=0-5.png" width="200" alt="resvg__filters-feGaussianBlur--stdDeviation=0-5 in resvg"></a> | <a href="render/weasyprint/resvg__filters-feGaussianBlur--stdDeviation=0-5.png"><img src="render/weasyprint/resvg__filters-feGaussianBlur--stdDeviation=0-5.png" width="200" alt="resvg__filters-feGaussianBlur--stdDeviation=0-5 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feGaussianBlur--stdDeviation=0-5.png"><img src="render/weasysvg/resvg__filters-feGaussianBlur--stdDeviation=0-5.png" width="200" alt="resvg__filters-feGaussianBlur--stdDeviation=0-5 in weasysvg"></a> |

### resvg__filters-feOffset--complex-transform

[`resvg/filters-feOffset--complex-transform.svg`](svg/resvg/filters-feOffset--complex-transform.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feOffset--complex-transform.png"><img src="render/chromium/resvg__filters-feOffset--complex-transform.png" width="200" alt="resvg__filters-feOffset--complex-transform in Chromium"></a> | <a href="render/resvg/resvg__filters-feOffset--complex-transform.png"><img src="render/resvg/resvg__filters-feOffset--complex-transform.png" width="200" alt="resvg__filters-feOffset--complex-transform in resvg"></a> | <a href="render/weasyprint/resvg__filters-feOffset--complex-transform.png"><img src="render/weasyprint/resvg__filters-feOffset--complex-transform.png" width="200" alt="resvg__filters-feOffset--complex-transform in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feOffset--complex-transform.png"><img src="render/weasysvg/resvg__filters-feOffset--complex-transform.png" width="200" alt="resvg__filters-feOffset--complex-transform in weasysvg"></a> |

### resvg__filters-feOffset--fractional-offset

[`resvg/filters-feOffset--fractional-offset.svg`](svg/resvg/filters-feOffset--fractional-offset.svg). WeasyPrint: minor, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feOffset--fractional-offset.png"><img src="render/chromium/resvg__filters-feOffset--fractional-offset.png" width="200" alt="resvg__filters-feOffset--fractional-offset in Chromium"></a> | <a href="render/resvg/resvg__filters-feOffset--fractional-offset.png"><img src="render/resvg/resvg__filters-feOffset--fractional-offset.png" width="200" alt="resvg__filters-feOffset--fractional-offset in resvg"></a> | <a href="render/weasyprint/resvg__filters-feOffset--fractional-offset.png"><img src="render/weasyprint/resvg__filters-feOffset--fractional-offset.png" width="200" alt="resvg__filters-feOffset--fractional-offset in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feOffset--fractional-offset.png"><img src="render/weasysvg/resvg__filters-feOffset--fractional-offset.png" width="200" alt="resvg__filters-feOffset--fractional-offset in weasysvg"></a> |

### resvg__filters-feTurbulence--baseFrequency=0.01

[`resvg/filters-feTurbulence--baseFrequency=0.01.svg`](svg/resvg/filters-feTurbulence--baseFrequency=0.01.svg). WeasyPrint: broken, weasysvg: **same**. Noise is drawn as an image over the filter region: it has no vector form.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feTurbulence--baseFrequency=0.01.png"><img src="render/chromium/resvg__filters-feTurbulence--baseFrequency=0.01.png" width="200" alt="resvg__filters-feTurbulence--baseFrequency=0.01 in Chromium"></a> | <a href="render/resvg/resvg__filters-feTurbulence--baseFrequency=0.01.png"><img src="render/resvg/resvg__filters-feTurbulence--baseFrequency=0.01.png" width="200" alt="resvg__filters-feTurbulence--baseFrequency=0.01 in resvg"></a> | <a href="render/weasyprint/resvg__filters-feTurbulence--baseFrequency=0.01.png"><img src="render/weasyprint/resvg__filters-feTurbulence--baseFrequency=0.01.png" width="200" alt="resvg__filters-feTurbulence--baseFrequency=0.01 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feTurbulence--baseFrequency=0.01.png"><img src="render/weasysvg/resvg__filters-feTurbulence--baseFrequency=0.01.png" width="200" alt="resvg__filters-feTurbulence--baseFrequency=0.01 in weasysvg"></a> |

### resvg__filters-feTurbulence--type=invalid

[`resvg/filters-feTurbulence--type=invalid.svg`](svg/resvg/filters-feTurbulence--type=invalid.svg). WeasyPrint: broken, weasysvg: **same**. Noise is drawn as an image over the filter region: it has no vector form.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-feTurbulence--type=invalid.png"><img src="render/chromium/resvg__filters-feTurbulence--type=invalid.png" width="200" alt="resvg__filters-feTurbulence--type=invalid in Chromium"></a> | <a href="render/resvg/resvg__filters-feTurbulence--type=invalid.png"><img src="render/resvg/resvg__filters-feTurbulence--type=invalid.png" width="200" alt="resvg__filters-feTurbulence--type=invalid in resvg"></a> | <a href="render/weasyprint/resvg__filters-feTurbulence--type=invalid.png"><img src="render/weasyprint/resvg__filters-feTurbulence--type=invalid.png" width="200" alt="resvg__filters-feTurbulence--type=invalid in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-feTurbulence--type=invalid.png"><img src="render/weasysvg/resvg__filters-feTurbulence--type=invalid.png" width="200" alt="resvg__filters-feTurbulence--type=invalid in weasysvg"></a> |

### resvg__filters-filter--in=SourceAlpha

[`resvg/filters-filter--in=SourceAlpha.svg`](svg/resvg/filters-filter--in=SourceAlpha.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-filter--in=SourceAlpha.png"><img src="render/chromium/resvg__filters-filter--in=SourceAlpha.png" width="200" alt="resvg__filters-filter--in=SourceAlpha in Chromium"></a> | <a href="render/resvg/resvg__filters-filter--in=SourceAlpha.png"><img src="render/resvg/resvg__filters-filter--in=SourceAlpha.png" width="200" alt="resvg__filters-filter--in=SourceAlpha in resvg"></a> | <a href="render/weasyprint/resvg__filters-filter--in=SourceAlpha.png"><img src="render/weasyprint/resvg__filters-filter--in=SourceAlpha.png" width="200" alt="resvg__filters-filter--in=SourceAlpha in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-filter--in=SourceAlpha.png"><img src="render/weasysvg/resvg__filters-filter--in=SourceAlpha.png" width="200" alt="resvg__filters-filter--in=SourceAlpha in weasysvg"></a> |

### resvg__filters-filter--on-the-root-svg

[`resvg/filters-filter--on-the-root-svg.svg`](svg/resvg/filters-filter--on-the-root-svg.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-filter--on-the-root-svg.png"><img src="render/chromium/resvg__filters-filter--on-the-root-svg.png" width="200" alt="resvg__filters-filter--on-the-root-svg in Chromium"></a> | <a href="render/resvg/resvg__filters-filter--on-the-root-svg.png"><img src="render/resvg/resvg__filters-filter--on-the-root-svg.png" width="200" alt="resvg__filters-filter--on-the-root-svg in resvg"></a> | <a href="render/weasyprint/resvg__filters-filter--on-the-root-svg.png"><img src="render/weasyprint/resvg__filters-filter--on-the-root-svg.png" width="200" alt="resvg__filters-filter--on-the-root-svg in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-filter--on-the-root-svg.png"><img src="render/weasysvg/resvg__filters-filter--on-the-root-svg.png" width="200" alt="resvg__filters-filter--on-the-root-svg in weasysvg"></a> |

### resvg__filters-filter-functions--blur-function-two-values

[`resvg/filters-filter-functions--blur-function-two-values.svg`](svg/resvg/filters-filter-functions--blur-function-two-values.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-filter-functions--blur-function-two-values.png"><img src="render/chromium/resvg__filters-filter-functions--blur-function-two-values.png" width="200" alt="resvg__filters-filter-functions--blur-function-two-values in Chromium"></a> | <a href="render/resvg/resvg__filters-filter-functions--blur-function-two-values.png"><img src="render/resvg/resvg__filters-filter-functions--blur-function-two-values.png" width="200" alt="resvg__filters-filter-functions--blur-function-two-values in resvg"></a> | <a href="render/weasyprint/resvg__filters-filter-functions--blur-function-two-values.png"><img src="render/weasyprint/resvg__filters-filter-functions--blur-function-two-values.png" width="200" alt="resvg__filters-filter-functions--blur-function-two-values in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-filter-functions--blur-function-two-values.png"><img src="render/weasysvg/resvg__filters-filter-functions--blur-function-two-values.png" width="200" alt="resvg__filters-filter-functions--blur-function-two-values in weasysvg"></a> |

### resvg__filters-filter-functions--drop-shadow-function-comma-separated

[`resvg/filters-filter-functions--drop-shadow-function-comma-separated.svg`](svg/resvg/filters-filter-functions--drop-shadow-function-comma-separated.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png"><img src="render/chromium/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png" width="200" alt="resvg__filters-filter-functions--drop-shadow-function-comma-separated in Chromium"></a> | <a href="render/resvg/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png"><img src="render/resvg/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png" width="200" alt="resvg__filters-filter-functions--drop-shadow-function-comma-separated in resvg"></a> | <a href="render/weasyprint/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png"><img src="render/weasyprint/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png" width="200" alt="resvg__filters-filter-functions--drop-shadow-function-comma-separated in WeasyPrint"></a> | <a href="render/weasysvg/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png"><img src="render/weasysvg/resvg__filters-filter-functions--drop-shadow-function-comma-separated.png" width="200" alt="resvg__filters-filter-functions--drop-shadow-function-comma-separated in weasysvg"></a> |

### resvg__masking-clipPath--clip-path-on-children

[`resvg/masking-clipPath--clip-path-on-children.svg`](svg/resvg/masking-clipPath--clip-path-on-children.svg). WeasyPrint: broken, weasysvg: **same**. The clip path becomes a soft mask: each child keeps its own clip-path and clip-rule.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__masking-clipPath--clip-path-on-children.png"><img src="render/chromium/resvg__masking-clipPath--clip-path-on-children.png" width="200" alt="resvg__masking-clipPath--clip-path-on-children in Chromium"></a> | <a href="render/resvg/resvg__masking-clipPath--clip-path-on-children.png"><img src="render/resvg/resvg__masking-clipPath--clip-path-on-children.png" width="200" alt="resvg__masking-clipPath--clip-path-on-children in resvg"></a> | <a href="render/weasyprint/resvg__masking-clipPath--clip-path-on-children.png"><img src="render/weasyprint/resvg__masking-clipPath--clip-path-on-children.png" width="200" alt="resvg__masking-clipPath--clip-path-on-children in WeasyPrint"></a> | <a href="render/weasysvg/resvg__masking-clipPath--clip-path-on-children.png"><img src="render/weasysvg/resvg__masking-clipPath--clip-path-on-children.png" width="200" alt="resvg__masking-clipPath--clip-path-on-children in weasysvg"></a> |

### resvg__masking-clipPath--on-a-horizontal-line

[`resvg/masking-clipPath--on-a-horizontal-line.svg`](svg/resvg/masking-clipPath--on-a-horizontal-line.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__masking-clipPath--on-a-horizontal-line.png"><img src="render/chromium/resvg__masking-clipPath--on-a-horizontal-line.png" width="200" alt="resvg__masking-clipPath--on-a-horizontal-line in Chromium"></a> | <a href="render/resvg/resvg__masking-clipPath--on-a-horizontal-line.png"><img src="render/resvg/resvg__masking-clipPath--on-a-horizontal-line.png" width="200" alt="resvg__masking-clipPath--on-a-horizontal-line in resvg"></a> | <a href="render/weasyprint/resvg__masking-clipPath--on-a-horizontal-line.png"><img src="render/weasyprint/resvg__masking-clipPath--on-a-horizontal-line.png" width="200" alt="resvg__masking-clipPath--on-a-horizontal-line in WeasyPrint"></a> | <a href="render/weasysvg/resvg__masking-clipPath--on-a-horizontal-line.png"><img src="render/weasysvg/resvg__masking-clipPath--on-a-horizontal-line.png" width="200" alt="resvg__masking-clipPath--on-a-horizontal-line in weasysvg"></a> |

### resvg__masking-mask--invalid-child

[`resvg/masking-mask--invalid-child.svg`](svg/resvg/masking-mask--invalid-child.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__masking-mask--invalid-child.png"><img src="render/chromium/resvg__masking-mask--invalid-child.png" width="200" alt="resvg__masking-mask--invalid-child in Chromium"></a> | <a href="render/resvg/resvg__masking-mask--invalid-child.png"><img src="render/resvg/resvg__masking-mask--invalid-child.png" width="200" alt="resvg__masking-mask--invalid-child in resvg"></a> | <a href="render/weasyprint/resvg__masking-mask--invalid-child.png"><img src="render/weasyprint/resvg__masking-mask--invalid-child.png" width="200" alt="resvg__masking-mask--invalid-child in WeasyPrint"></a> | <a href="render/weasysvg/resvg__masking-mask--invalid-child.png"><img src="render/weasysvg/resvg__masking-mask--invalid-child.png" width="200" alt="resvg__masking-mask--invalid-child in weasysvg"></a> |

### resvg__masking-mask--recursive-on-self

[`resvg/masking-mask--recursive-on-self.svg`](svg/resvg/masking-mask--recursive-on-self.svg). WeasyPrint: broken, weasysvg: **same**. mask on a &lt;mask&gt; is ignored, as in Chromium; gradient colors mix unpremultiplied.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__masking-mask--recursive-on-self.png"><img src="render/chromium/resvg__masking-mask--recursive-on-self.png" width="200" alt="resvg__masking-mask--recursive-on-self in Chromium"></a> | <a href="render/resvg/resvg__masking-mask--recursive-on-self.png"><img src="render/resvg/resvg__masking-mask--recursive-on-self.png" width="200" alt="resvg__masking-mask--recursive-on-self in resvg"></a> | <a href="render/weasyprint/resvg__masking-mask--recursive-on-self.png"><img src="render/weasyprint/resvg__masking-mask--recursive-on-self.png" width="200" alt="resvg__masking-mask--recursive-on-self in WeasyPrint"></a> | <a href="render/weasysvg/resvg__masking-mask--recursive-on-self.png"><img src="render/weasysvg/resvg__masking-mask--recursive-on-self.png" width="200" alt="resvg__masking-mask--recursive-on-self in weasysvg"></a> |

### resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect

[`resvg/paint-servers-linearGradient--attributes-via-xlink-href-from-rect.svg`](svg/resvg/paint-servers-linearGradient--attributes-via-xlink-href-from-rect.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png"><img src="render/chromium/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png" width="200" alt="resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png"><img src="render/resvg/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png" width="200" alt="resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png"><img src="render/weasyprint/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png" width="200" alt="resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png"><img src="render/weasysvg/resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect.png" width="200" alt="resvg__paint-servers-linearGradient--attributes-via-xlink-href-from-rect in weasysvg"></a> |

### resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1

[`resvg/paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.svg`](svg/resvg/paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png"><img src="render/chromium/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png" width="200" alt="resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1 in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png"><img src="render/resvg/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png" width="200" alt="resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1 in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png"><img src="render/weasyprint/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png" width="200" alt="resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png"><img src="render/weasysvg/resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1.png" width="200" alt="resvg__paint-servers-linearGradient--stops-via-xlink-href-complex-order-1 in weasysvg"></a> |

### resvg__paint-servers-pattern--nested-objectBoundingBox

[`resvg/paint-servers-pattern--nested-objectBoundingBox.svg`](svg/resvg/paint-servers-pattern--nested-objectBoundingBox.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-pattern--nested-objectBoundingBox.png"><img src="render/chromium/resvg__paint-servers-pattern--nested-objectBoundingBox.png" width="200" alt="resvg__paint-servers-pattern--nested-objectBoundingBox in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-pattern--nested-objectBoundingBox.png"><img src="render/resvg/resvg__paint-servers-pattern--nested-objectBoundingBox.png" width="200" alt="resvg__paint-servers-pattern--nested-objectBoundingBox in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-pattern--nested-objectBoundingBox.png"><img src="render/weasyprint/resvg__paint-servers-pattern--nested-objectBoundingBox.png" width="200" alt="resvg__paint-servers-pattern--nested-objectBoundingBox in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-pattern--nested-objectBoundingBox.png"><img src="render/weasysvg/resvg__paint-servers-pattern--nested-objectBoundingBox.png" width="200" alt="resvg__paint-servers-pattern--nested-objectBoundingBox in weasysvg"></a> |

### resvg__paint-servers-pattern--text-child

[`resvg/paint-servers-pattern--text-child.svg`](svg/resvg/paint-servers-pattern--text-child.svg). WeasyPrint: font, weasysvg: **same**. Tiles start at the user space origin, patternTransform included. Glyph antialiasing differs slightly.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-pattern--text-child.png"><img src="render/chromium/resvg__paint-servers-pattern--text-child.png" width="200" alt="resvg__paint-servers-pattern--text-child in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-pattern--text-child.png"><img src="render/resvg/resvg__paint-servers-pattern--text-child.png" width="200" alt="resvg__paint-servers-pattern--text-child in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-pattern--text-child.png"><img src="render/weasyprint/resvg__paint-servers-pattern--text-child.png" width="200" alt="resvg__paint-servers-pattern--text-child in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-pattern--text-child.png"><img src="render/weasysvg/resvg__paint-servers-pattern--text-child.png" width="200" alt="resvg__paint-servers-pattern--text-child in weasysvg"></a> |

### resvg__paint-servers-radialGradient--fr=0.2

[`resvg/paint-servers-radialGradient--fr=0.2.svg`](svg/resvg/paint-servers-radialGradient--fr=0.2.svg). WeasyPrint: broken, weasysvg: **minor**. Gradient matches reference except one white pixel at the exact center (possibly a PDFium artifact of the fr focal circle).

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-radialGradient--fr=0.2.png"><img src="render/chromium/resvg__paint-servers-radialGradient--fr=0.2.png" width="200" alt="resvg__paint-servers-radialGradient--fr=0.2 in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-radialGradient--fr=0.2.png"><img src="render/resvg/resvg__paint-servers-radialGradient--fr=0.2.png" width="200" alt="resvg__paint-servers-radialGradient--fr=0.2 in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-radialGradient--fr=0.2.png"><img src="render/weasyprint/resvg__paint-servers-radialGradient--fr=0.2.png" width="200" alt="resvg__paint-servers-radialGradient--fr=0.2 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-radialGradient--fr=0.2.png"><img src="render/weasysvg/resvg__paint-servers-radialGradient--fr=0.2.png" width="200" alt="resvg__paint-servers-radialGradient--fr=0.2 in weasysvg"></a> |

### resvg__paint-servers-radialGradient--gradientTransform-via-href

[`resvg/paint-servers-radialGradient--gradientTransform-via-href.svg`](svg/resvg/paint-servers-radialGradient--gradientTransform-via-href.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__paint-servers-radialGradient--gradientTransform-via-href.png"><img src="render/chromium/resvg__paint-servers-radialGradient--gradientTransform-via-href.png" width="200" alt="resvg__paint-servers-radialGradient--gradientTransform-via-href in Chromium"></a> | <a href="render/resvg/resvg__paint-servers-radialGradient--gradientTransform-via-href.png"><img src="render/resvg/resvg__paint-servers-radialGradient--gradientTransform-via-href.png" width="200" alt="resvg__paint-servers-radialGradient--gradientTransform-via-href in resvg"></a> | <a href="render/weasyprint/resvg__paint-servers-radialGradient--gradientTransform-via-href.png"><img src="render/weasyprint/resvg__paint-servers-radialGradient--gradientTransform-via-href.png" width="200" alt="resvg__paint-servers-radialGradient--gradientTransform-via-href in WeasyPrint"></a> | <a href="render/weasysvg/resvg__paint-servers-radialGradient--gradientTransform-via-href.png"><img src="render/weasysvg/resvg__paint-servers-radialGradient--gradientTransform-via-href.png" width="200" alt="resvg__paint-servers-radialGradient--gradientTransform-via-href in weasysvg"></a> |

### resvg__painting-marker--on-ArcTo

[`resvg/painting-marker--on-ArcTo.svg`](svg/resvg/painting-marker--on-ArcTo.svg). WeasyPrint: broken, weasysvg: **same**. Start and end markers follow the arc tangents, as in Chromium.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-marker--on-ArcTo.png"><img src="render/chromium/resvg__painting-marker--on-ArcTo.png" width="200" alt="resvg__painting-marker--on-ArcTo in Chromium"></a> | <a href="render/resvg/resvg__painting-marker--on-ArcTo.png"><img src="render/resvg/resvg__painting-marker--on-ArcTo.png" width="200" alt="resvg__painting-marker--on-ArcTo in resvg"></a> | <a href="render/weasyprint/resvg__painting-marker--on-ArcTo.png"><img src="render/weasyprint/resvg__painting-marker--on-ArcTo.png" width="200" alt="resvg__painting-marker--on-ArcTo in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-marker--on-ArcTo.png"><img src="render/weasysvg/resvg__painting-marker--on-ArcTo.png" width="200" alt="resvg__painting-marker--on-ArcTo in weasysvg"></a> |

### resvg__painting-marker--orient=auto-on-M-C-C-4

[`resvg/painting-marker--orient=auto-on-M-C-C-4.svg`](svg/resvg/painting-marker--orient=auto-on-M-C-C-4.svg). WeasyPrint: broken, weasysvg: **same**. The mid marker bisects the cusp with the angle wrap of Chromium and points right.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-marker--orient=auto-on-M-C-C-4.png"><img src="render/chromium/resvg__painting-marker--orient=auto-on-M-C-C-4.png" width="200" alt="resvg__painting-marker--orient=auto-on-M-C-C-4 in Chromium"></a> | <a href="render/resvg/resvg__painting-marker--orient=auto-on-M-C-C-4.png"><img src="render/resvg/resvg__painting-marker--orient=auto-on-M-C-C-4.png" width="200" alt="resvg__painting-marker--orient=auto-on-M-C-C-4 in resvg"></a> | <a href="render/weasyprint/resvg__painting-marker--orient=auto-on-M-C-C-4.png"><img src="render/weasyprint/resvg__painting-marker--orient=auto-on-M-C-C-4.png" width="200" alt="resvg__painting-marker--orient=auto-on-M-C-C-4 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-marker--orient=auto-on-M-C-C-4.png"><img src="render/weasysvg/resvg__painting-marker--orient=auto-on-M-C-C-4.png" width="200" alt="resvg__painting-marker--orient=auto-on-M-C-C-4 in weasysvg"></a> |

### resvg__painting-mix-blend-mode--screen

[`resvg/painting-mix-blend-mode--screen.svg`](svg/resvg/painting-mix-blend-mode--screen.svg). WeasyPrint: broken, weasysvg: **same**. Gradient colors mix unpremultiplied, as in Chromium.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-mix-blend-mode--screen.png"><img src="render/chromium/resvg__painting-mix-blend-mode--screen.png" width="200" alt="resvg__painting-mix-blend-mode--screen in Chromium"></a> | <a href="render/resvg/resvg__painting-mix-blend-mode--screen.png"><img src="render/resvg/resvg__painting-mix-blend-mode--screen.png" width="200" alt="resvg__painting-mix-blend-mode--screen in resvg"></a> | <a href="render/weasyprint/resvg__painting-mix-blend-mode--screen.png"><img src="render/weasyprint/resvg__painting-mix-blend-mode--screen.png" width="200" alt="resvg__painting-mix-blend-mode--screen in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-mix-blend-mode--screen.png"><img src="render/weasysvg/resvg__painting-mix-blend-mode--screen.png" width="200" alt="resvg__painting-mix-blend-mode--screen in weasysvg"></a> |

### resvg__painting-mix-blend-mode--xor

[`resvg/painting-mix-blend-mode--xor.svg`](svg/resvg/painting-mix-blend-mode--xor.svg). WeasyPrint: minor, weasysvg: **same**. Gradient colors mix unpremultiplied, as in Chromium.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-mix-blend-mode--xor.png"><img src="render/chromium/resvg__painting-mix-blend-mode--xor.png" width="200" alt="resvg__painting-mix-blend-mode--xor in Chromium"></a> | <a href="render/resvg/resvg__painting-mix-blend-mode--xor.png"><img src="render/resvg/resvg__painting-mix-blend-mode--xor.png" width="200" alt="resvg__painting-mix-blend-mode--xor in resvg"></a> | <a href="render/weasyprint/resvg__painting-mix-blend-mode--xor.png"><img src="render/weasyprint/resvg__painting-mix-blend-mode--xor.png" width="200" alt="resvg__painting-mix-blend-mode--xor in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-mix-blend-mode--xor.png"><img src="render/weasysvg/resvg__painting-mix-blend-mode--xor.png" width="200" alt="resvg__painting-mix-blend-mode--xor in weasysvg"></a> |

### resvg__painting-paint-order--duplicates

[`resvg/painting-paint-order--duplicates.svg`](svg/resvg/painting-paint-order--duplicates.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-paint-order--duplicates.png"><img src="render/chromium/resvg__painting-paint-order--duplicates.png" width="200" alt="resvg__painting-paint-order--duplicates in Chromium"></a> | <a href="render/resvg/resvg__painting-paint-order--duplicates.png"><img src="render/resvg/resvg__painting-paint-order--duplicates.png" width="200" alt="resvg__painting-paint-order--duplicates in resvg"></a> | <a href="render/weasyprint/resvg__painting-paint-order--duplicates.png"><img src="render/weasyprint/resvg__painting-paint-order--duplicates.png" width="200" alt="resvg__painting-paint-order--duplicates in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-paint-order--duplicates.png"><img src="render/weasysvg/resvg__painting-paint-order--duplicates.png" width="200" alt="resvg__painting-paint-order--duplicates in weasysvg"></a> |

### resvg__painting-paint-order--invalid

[`resvg/painting-paint-order--invalid.svg`](svg/resvg/painting-paint-order--invalid.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-paint-order--invalid.png"><img src="render/chromium/resvg__painting-paint-order--invalid.png" width="200" alt="resvg__painting-paint-order--invalid in Chromium"></a> | <a href="render/resvg/resvg__painting-paint-order--invalid.png"><img src="render/resvg/resvg__painting-paint-order--invalid.png" width="200" alt="resvg__painting-paint-order--invalid in resvg"></a> | <a href="render/weasyprint/resvg__painting-paint-order--invalid.png"><img src="render/weasyprint/resvg__painting-paint-order--invalid.png" width="200" alt="resvg__painting-paint-order--invalid in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-paint-order--invalid.png"><img src="render/weasysvg/resvg__painting-paint-order--invalid.png" width="200" alt="resvg__painting-paint-order--invalid in weasysvg"></a> |

### resvg__painting-stroke-dasharray--0-n-with-round-caps

[`resvg/painting-stroke-dasharray--0-n-with-round-caps.svg`](svg/resvg/painting-stroke-dasharray--0-n-with-round-caps.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-stroke-dasharray--0-n-with-round-caps.png"><img src="render/chromium/resvg__painting-stroke-dasharray--0-n-with-round-caps.png" width="200" alt="resvg__painting-stroke-dasharray--0-n-with-round-caps in Chromium"></a> | <a href="render/resvg/resvg__painting-stroke-dasharray--0-n-with-round-caps.png"><img src="render/resvg/resvg__painting-stroke-dasharray--0-n-with-round-caps.png" width="200" alt="resvg__painting-stroke-dasharray--0-n-with-round-caps in resvg"></a> | <a href="render/weasyprint/resvg__painting-stroke-dasharray--0-n-with-round-caps.png"><img src="render/weasyprint/resvg__painting-stroke-dasharray--0-n-with-round-caps.png" width="200" alt="resvg__painting-stroke-dasharray--0-n-with-round-caps in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-stroke-dasharray--0-n-with-round-caps.png"><img src="render/weasysvg/resvg__painting-stroke-dasharray--0-n-with-round-caps.png" width="200" alt="resvg__painting-stroke-dasharray--0-n-with-round-caps in weasysvg"></a> |

### resvg__painting-stroke-dasharray--odd-count

[`resvg/painting-stroke-dasharray--odd-count.svg`](svg/resvg/painting-stroke-dasharray--odd-count.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__painting-stroke-dasharray--odd-count.png"><img src="render/chromium/resvg__painting-stroke-dasharray--odd-count.png" width="200" alt="resvg__painting-stroke-dasharray--odd-count in Chromium"></a> | <a href="render/resvg/resvg__painting-stroke-dasharray--odd-count.png"><img src="render/resvg/resvg__painting-stroke-dasharray--odd-count.png" width="200" alt="resvg__painting-stroke-dasharray--odd-count in resvg"></a> | <a href="render/weasyprint/resvg__painting-stroke-dasharray--odd-count.png"><img src="render/weasyprint/resvg__painting-stroke-dasharray--odd-count.png" width="200" alt="resvg__painting-stroke-dasharray--odd-count in WeasyPrint"></a> | <a href="render/weasysvg/resvg__painting-stroke-dasharray--odd-count.png"><img src="render/weasysvg/resvg__painting-stroke-dasharray--odd-count.png" width="200" alt="resvg__painting-stroke-dasharray--odd-count in weasysvg"></a> |

### resvg__shapes-path--M-H-H-implicit

[`resvg/shapes-path--M-H-H-implicit.svg`](svg/resvg/shapes-path--M-H-H-implicit.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__shapes-path--M-H-H-implicit.png"><img src="render/chromium/resvg__shapes-path--M-H-H-implicit.png" width="200" alt="resvg__shapes-path--M-H-H-implicit in Chromium"></a> | <a href="render/resvg/resvg__shapes-path--M-H-H-implicit.png"><img src="render/resvg/resvg__shapes-path--M-H-H-implicit.png" width="200" alt="resvg__shapes-path--M-H-H-implicit in resvg"></a> | <a href="render/weasyprint/resvg__shapes-path--M-H-H-implicit.png"><img src="render/weasyprint/resvg__shapes-path--M-H-H-implicit.png" width="200" alt="resvg__shapes-path--M-H-H-implicit in WeasyPrint"></a> | <a href="render/weasysvg/resvg__shapes-path--M-H-H-implicit.png"><img src="render/weasysvg/resvg__shapes-path--M-H-H-implicit.png" width="200" alt="resvg__shapes-path--M-H-H-implicit in weasysvg"></a> |

### resvg__shapes-path--M-T

[`resvg/shapes-path--M-T.svg`](svg/resvg/shapes-path--M-T.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__shapes-path--M-T.png"><img src="render/chromium/resvg__shapes-path--M-T.png" width="200" alt="resvg__shapes-path--M-T in Chromium"></a> | <a href="render/resvg/resvg__shapes-path--M-T.png"><img src="render/resvg/resvg__shapes-path--M-T.png" width="200" alt="resvg__shapes-path--M-T in resvg"></a> | <a href="render/weasyprint/resvg__shapes-path--M-T.png"><img src="render/weasyprint/resvg__shapes-path--M-T.png" width="200" alt="resvg__shapes-path--M-T in WeasyPrint"></a> | <a href="render/weasysvg/resvg__shapes-path--M-T.png"><img src="render/weasysvg/resvg__shapes-path--M-T.png" width="200" alt="resvg__shapes-path--M-T in weasysvg"></a> |

### resvg__structure-style--class-selector

[`resvg/structure-style--class-selector.svg`](svg/resvg/structure-style--class-selector.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-style--class-selector.png"><img src="render/chromium/resvg__structure-style--class-selector.png" width="200" alt="resvg__structure-style--class-selector in Chromium"></a> | <a href="render/resvg/resvg__structure-style--class-selector.png"><img src="render/resvg/resvg__structure-style--class-selector.png" width="200" alt="resvg__structure-style--class-selector in resvg"></a> | <a href="render/weasyprint/resvg__structure-style--class-selector.png"><img src="render/weasyprint/resvg__structure-style--class-selector.png" width="200" alt="resvg__structure-style--class-selector in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-style--class-selector.png"><img src="render/weasysvg/resvg__structure-style--class-selector.png" width="200" alt="resvg__structure-style--class-selector in weasysvg"></a> |

### resvg__structure-style--iD-selector

[`resvg/structure-style--iD-selector.svg`](svg/resvg/structure-style--iD-selector.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-style--iD-selector.png"><img src="render/chromium/resvg__structure-style--iD-selector.png" width="200" alt="resvg__structure-style--iD-selector in Chromium"></a> | <a href="render/resvg/resvg__structure-style--iD-selector.png"><img src="render/resvg/resvg__structure-style--iD-selector.png" width="200" alt="resvg__structure-style--iD-selector in resvg"></a> | <a href="render/weasyprint/resvg__structure-style--iD-selector.png"><img src="render/weasyprint/resvg__structure-style--iD-selector.png" width="200" alt="resvg__structure-style--iD-selector in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-style--iD-selector.png"><img src="render/weasysvg/resvg__structure-style--iD-selector.png" width="200" alt="resvg__structure-style--iD-selector in weasysvg"></a> |

### resvg__structure-switch--single-child

[`resvg/structure-switch--single-child.svg`](svg/resvg/structure-switch--single-child.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-switch--single-child.png"><img src="render/chromium/resvg__structure-switch--single-child.png" width="200" alt="resvg__structure-switch--single-child in Chromium"></a> | <a href="render/resvg/resvg__structure-switch--single-child.png"><img src="render/resvg/resvg__structure-switch--single-child.png" width="200" alt="resvg__structure-switch--single-child in resvg"></a> | <a href="render/weasyprint/resvg__structure-switch--single-child.png"><img src="render/weasyprint/resvg__structure-switch--single-child.png" width="200" alt="resvg__structure-switch--single-child in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-switch--single-child.png"><img src="render/weasysvg/resvg__structure-switch--single-child.png" width="200" alt="resvg__structure-switch--single-child in weasysvg"></a> |

### resvg__structure-switch--with-attributes

[`resvg/structure-switch--with-attributes.svg`](svg/resvg/structure-switch--with-attributes.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-switch--with-attributes.png"><img src="render/chromium/resvg__structure-switch--with-attributes.png" width="200" alt="resvg__structure-switch--with-attributes in Chromium"></a> | <a href="render/resvg/resvg__structure-switch--with-attributes.png"><img src="render/resvg/resvg__structure-switch--with-attributes.png" width="200" alt="resvg__structure-switch--with-attributes in resvg"></a> | <a href="render/weasyprint/resvg__structure-switch--with-attributes.png"><img src="render/weasyprint/resvg__structure-switch--with-attributes.png" width="200" alt="resvg__structure-switch--with-attributes in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-switch--with-attributes.png"><img src="render/weasysvg/resvg__structure-switch--with-attributes.png" width="200" alt="resvg__structure-switch--with-attributes in weasysvg"></a> |

### resvg__structure-symbol--with-transform

[`resvg/structure-symbol--with-transform.svg`](svg/resvg/structure-symbol--with-transform.svg). WeasyPrint: same, weasysvg: **same**. Matches Chromium (SVG 2 applies symbol transform); the SVG 1.1 reference ignores it.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-symbol--with-transform.png"><img src="render/chromium/resvg__structure-symbol--with-transform.png" width="200" alt="resvg__structure-symbol--with-transform in Chromium"></a> | <a href="render/resvg/resvg__structure-symbol--with-transform.png"><img src="render/resvg/resvg__structure-symbol--with-transform.png" width="200" alt="resvg__structure-symbol--with-transform in resvg"></a> | <a href="render/weasyprint/resvg__structure-symbol--with-transform.png"><img src="render/weasyprint/resvg__structure-symbol--with-transform.png" width="200" alt="resvg__structure-symbol--with-transform in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-symbol--with-transform.png"><img src="render/weasysvg/resvg__structure-symbol--with-transform.png" width="200" alt="resvg__structure-symbol--with-transform in weasysvg"></a> |

### resvg__structure-symbol--with-viewBox-and-custom-use-size

[`resvg/structure-symbol--with-viewBox-and-custom-use-size.svg`](svg/resvg/structure-symbol--with-viewBox-and-custom-use-size.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-symbol--with-viewBox-and-custom-use-size.png"><img src="render/chromium/resvg__structure-symbol--with-viewBox-and-custom-use-size.png" width="200" alt="resvg__structure-symbol--with-viewBox-and-custom-use-size in Chromium"></a> | <a href="render/resvg/resvg__structure-symbol--with-viewBox-and-custom-use-size.png"><img src="render/resvg/resvg__structure-symbol--with-viewBox-and-custom-use-size.png" width="200" alt="resvg__structure-symbol--with-viewBox-and-custom-use-size in resvg"></a> | <a href="render/weasyprint/resvg__structure-symbol--with-viewBox-and-custom-use-size.png"><img src="render/weasyprint/resvg__structure-symbol--with-viewBox-and-custom-use-size.png" width="200" alt="resvg__structure-symbol--with-viewBox-and-custom-use-size in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-symbol--with-viewBox-and-custom-use-size.png"><img src="render/weasysvg/resvg__structure-symbol--with-viewBox-and-custom-use-size.png" width="200" alt="resvg__structure-symbol--with-viewBox-and-custom-use-size in weasysvg"></a> |

### resvg__structure-systemLanguage--on-clipPath

[`resvg/structure-systemLanguage--on-clipPath.svg`](svg/resvg/structure-systemLanguage--on-clipPath.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-systemLanguage--on-clipPath.png"><img src="render/chromium/resvg__structure-systemLanguage--on-clipPath.png" width="200" alt="resvg__structure-systemLanguage--on-clipPath in Chromium"></a> | <a href="render/resvg/resvg__structure-systemLanguage--on-clipPath.png"><img src="render/resvg/resvg__structure-systemLanguage--on-clipPath.png" width="200" alt="resvg__structure-systemLanguage--on-clipPath in resvg"></a> | <a href="render/weasyprint/resvg__structure-systemLanguage--on-clipPath.png"><img src="render/weasyprint/resvg__structure-systemLanguage--on-clipPath.png" width="200" alt="resvg__structure-systemLanguage--on-clipPath in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-systemLanguage--on-clipPath.png"><img src="render/weasysvg/resvg__structure-systemLanguage--on-clipPath.png" width="200" alt="resvg__structure-systemLanguage--on-clipPath in weasysvg"></a> |

### resvg__structure-systemLanguage--on-defs

[`resvg/structure-systemLanguage--on-defs.svg`](svg/resvg/structure-systemLanguage--on-defs.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-systemLanguage--on-defs.png"><img src="render/chromium/resvg__structure-systemLanguage--on-defs.png" width="200" alt="resvg__structure-systemLanguage--on-defs in Chromium"></a> | <a href="render/resvg/resvg__structure-systemLanguage--on-defs.png"><img src="render/resvg/resvg__structure-systemLanguage--on-defs.png" width="200" alt="resvg__structure-systemLanguage--on-defs in resvg"></a> | <a href="render/weasyprint/resvg__structure-systemLanguage--on-defs.png"><img src="render/weasyprint/resvg__structure-systemLanguage--on-defs.png" width="200" alt="resvg__structure-systemLanguage--on-defs in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-systemLanguage--on-defs.png"><img src="render/weasysvg/resvg__structure-systemLanguage--on-defs.png" width="200" alt="resvg__structure-systemLanguage--on-defs in weasysvg"></a> |

### resvg__structure-transform--scale-without-Y

[`resvg/structure-transform--scale-without-Y.svg`](svg/resvg/structure-transform--scale-without-Y.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-transform--scale-without-Y.png"><img src="render/chromium/resvg__structure-transform--scale-without-Y.png" width="200" alt="resvg__structure-transform--scale-without-Y in Chromium"></a> | <a href="render/resvg/resvg__structure-transform--scale-without-Y.png"><img src="render/resvg/resvg__structure-transform--scale-without-Y.png" width="200" alt="resvg__structure-transform--scale-without-Y in resvg"></a> | <a href="render/weasyprint/resvg__structure-transform--scale-without-Y.png"><img src="render/weasyprint/resvg__structure-transform--scale-without-Y.png" width="200" alt="resvg__structure-transform--scale-without-Y in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-transform--scale-without-Y.png"><img src="render/weasysvg/resvg__structure-transform--scale-without-Y.png" width="200" alt="resvg__structure-transform--scale-without-Y in weasysvg"></a> |

### resvg__structure-transform--skewY

[`resvg/structure-transform--skewY.svg`](svg/resvg/structure-transform--skewY.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-transform--skewY.png"><img src="render/chromium/resvg__structure-transform--skewY.png" width="200" alt="resvg__structure-transform--skewY in Chromium"></a> | <a href="render/resvg/resvg__structure-transform--skewY.png"><img src="render/resvg/resvg__structure-transform--skewY.png" width="200" alt="resvg__structure-transform--skewY in resvg"></a> | <a href="render/weasyprint/resvg__structure-transform--skewY.png"><img src="render/weasyprint/resvg__structure-transform--skewY.png" width="200" alt="resvg__structure-transform--skewY in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-transform--skewY.png"><img src="render/weasysvg/resvg__structure-transform--skewY.png" width="200" alt="resvg__structure-transform--skewY in weasysvg"></a> |

### resvg__structure-use--with-size

[`resvg/structure-use--with-size.svg`](svg/resvg/structure-use--with-size.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-use--with-size.png"><img src="render/chromium/resvg__structure-use--with-size.png" width="200" alt="resvg__structure-use--with-size in Chromium"></a> | <a href="render/resvg/resvg__structure-use--with-size.png"><img src="render/resvg/resvg__structure-use--with-size.png" width="200" alt="resvg__structure-use--with-size in resvg"></a> | <a href="render/weasyprint/resvg__structure-use--with-size.png"><img src="render/weasyprint/resvg__structure-use--with-size.png" width="200" alt="resvg__structure-use--with-size in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-use--with-size.png"><img src="render/weasysvg/resvg__structure-use--with-size.png" width="200" alt="resvg__structure-use--with-size in weasysvg"></a> |

### resvg__structure-use--xlink-to-svg-element-with-rect

[`resvg/structure-use--xlink-to-svg-element-with-rect.svg`](svg/resvg/structure-use--xlink-to-svg-element-with-rect.svg). WeasyPrint: same, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__structure-use--xlink-to-svg-element-with-rect.png"><img src="render/chromium/resvg__structure-use--xlink-to-svg-element-with-rect.png" width="200" alt="resvg__structure-use--xlink-to-svg-element-with-rect in Chromium"></a> | <a href="render/resvg/resvg__structure-use--xlink-to-svg-element-with-rect.png"><img src="render/resvg/resvg__structure-use--xlink-to-svg-element-with-rect.png" width="200" alt="resvg__structure-use--xlink-to-svg-element-with-rect in resvg"></a> | <a href="render/weasyprint/resvg__structure-use--xlink-to-svg-element-with-rect.png"><img src="render/weasyprint/resvg__structure-use--xlink-to-svg-element-with-rect.png" width="200" alt="resvg__structure-use--xlink-to-svg-element-with-rect in WeasyPrint"></a> | <a href="render/weasysvg/resvg__structure-use--xlink-to-svg-element-with-rect.png"><img src="render/weasysvg/resvg__structure-use--xlink-to-svg-element-with-rect.png" width="200" alt="resvg__structure-use--xlink-to-svg-element-with-rect in weasysvg"></a> |

### resvg__text-dominant-baseline--auto

[`resvg/text-dominant-baseline--auto.svg`](svg/resvg/text-dominant-baseline--auto.svg). WeasyPrint: font, weasysvg: **same**. Noto Sans is not installed: serif, as in Chromium. resvg draws sans.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-dominant-baseline--auto.png"><img src="render/chromium/resvg__text-dominant-baseline--auto.png" width="200" alt="resvg__text-dominant-baseline--auto in Chromium"></a> | <a href="render/resvg/resvg__text-dominant-baseline--auto.png"><img src="render/resvg/resvg__text-dominant-baseline--auto.png" width="200" alt="resvg__text-dominant-baseline--auto in resvg"></a> | <a href="render/weasyprint/resvg__text-dominant-baseline--auto.png"><img src="render/weasyprint/resvg__text-dominant-baseline--auto.png" width="200" alt="resvg__text-dominant-baseline--auto in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-dominant-baseline--auto.png"><img src="render/weasysvg/resvg__text-dominant-baseline--auto.png" width="200" alt="resvg__text-dominant-baseline--auto in weasysvg"></a> |

### resvg__text-dominant-baseline--reset-size

[`resvg/text-dominant-baseline--reset-size.svg`](svg/resvg/text-dominant-baseline--reset-size.svg). WeasyPrint: font, weasysvg: **same**. Noto Sans is not installed: serif, as in Chromium. resvg draws sans.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-dominant-baseline--reset-size.png"><img src="render/chromium/resvg__text-dominant-baseline--reset-size.png" width="200" alt="resvg__text-dominant-baseline--reset-size in Chromium"></a> | <a href="render/resvg/resvg__text-dominant-baseline--reset-size.png"><img src="render/resvg/resvg__text-dominant-baseline--reset-size.png" width="200" alt="resvg__text-dominant-baseline--reset-size in resvg"></a> | <a href="render/weasyprint/resvg__text-dominant-baseline--reset-size.png"><img src="render/weasyprint/resvg__text-dominant-baseline--reset-size.png" width="200" alt="resvg__text-dominant-baseline--reset-size in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-dominant-baseline--reset-size.png"><img src="render/weasysvg/resvg__text-dominant-baseline--reset-size.png" width="200" alt="resvg__text-dominant-baseline--reset-size in weasysvg"></a> |

### resvg__text-letter-spacing--0

[`resvg/text-letter-spacing--0.svg`](svg/resvg/text-letter-spacing--0.svg). WeasyPrint: font, weasysvg: **same**. Noto Sans is not installed: serif, as in Chromium. resvg draws sans.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-letter-spacing--0.png"><img src="render/chromium/resvg__text-letter-spacing--0.png" width="200" alt="resvg__text-letter-spacing--0 in Chromium"></a> | <a href="render/resvg/resvg__text-letter-spacing--0.png"><img src="render/resvg/resvg__text-letter-spacing--0.png" width="200" alt="resvg__text-letter-spacing--0 in resvg"></a> | <a href="render/weasyprint/resvg__text-letter-spacing--0.png"><img src="render/weasyprint/resvg__text-letter-spacing--0.png" width="200" alt="resvg__text-letter-spacing--0 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-letter-spacing--0.png"><img src="render/weasysvg/resvg__text-letter-spacing--0.png" width="200" alt="resvg__text-letter-spacing--0 in weasysvg"></a> |

### resvg__text-letter-spacing--on-Arabic

[`resvg/text-letter-spacing--on-Arabic.svg`](svg/resvg/text-letter-spacing--on-Arabic.svg). WeasyPrint: broken, weasysvg: **minor**. Letters joined, right to left, in the fallback font of Chromium. letter-spacing widens the spaces only; PDFium shows half of it (it drops the shift before the first glyph of a TJ array), Quartz all of it.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-letter-spacing--on-Arabic.png"><img src="render/chromium/resvg__text-letter-spacing--on-Arabic.png" width="200" alt="resvg__text-letter-spacing--on-Arabic in Chromium"></a> | <a href="render/resvg/resvg__text-letter-spacing--on-Arabic.png"><img src="render/resvg/resvg__text-letter-spacing--on-Arabic.png" width="200" alt="resvg__text-letter-spacing--on-Arabic in resvg"></a> | <a href="render/weasyprint/resvg__text-letter-spacing--on-Arabic.png"><img src="render/weasyprint/resvg__text-letter-spacing--on-Arabic.png" width="200" alt="resvg__text-letter-spacing--on-Arabic in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-letter-spacing--on-Arabic.png"><img src="render/weasysvg/resvg__text-letter-spacing--on-Arabic.png" width="200" alt="resvg__text-letter-spacing--on-Arabic in weasysvg"></a> |

### resvg__text-text--nested

[`resvg/text-text--nested.svg`](svg/resvg/text-text--nested.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-text--nested.png"><img src="render/chromium/resvg__text-text--nested.png" width="200" alt="resvg__text-text--nested in Chromium"></a> | <a href="render/resvg/resvg__text-text--nested.png"><img src="render/resvg/resvg__text-text--nested.png" width="200" alt="resvg__text-text--nested in resvg"></a> | <a href="render/weasyprint/resvg__text-text--nested.png"><img src="render/weasyprint/resvg__text-text--nested.png" width="200" alt="resvg__text-text--nested in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-text--nested.png"><img src="render/weasysvg/resvg__text-text--nested.png" width="200" alt="resvg__text-text--nested in weasysvg"></a> |

### resvg__text-text--x-and-y-with-less-values-than-characters

[`resvg/text-text--x-and-y-with-less-values-than-characters.svg`](svg/resvg/text-text--x-and-y-with-less-values-than-characters.svg). WeasyPrint: font, weasysvg: **same**. Noto Sans is not installed: serif, as in Chromium. resvg draws sans.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-text--x-and-y-with-less-values-than-characters.png"><img src="render/chromium/resvg__text-text--x-and-y-with-less-values-than-characters.png" width="200" alt="resvg__text-text--x-and-y-with-less-values-than-characters in Chromium"></a> | <a href="render/resvg/resvg__text-text--x-and-y-with-less-values-than-characters.png"><img src="render/resvg/resvg__text-text--x-and-y-with-less-values-than-characters.png" width="200" alt="resvg__text-text--x-and-y-with-less-values-than-characters in resvg"></a> | <a href="render/weasyprint/resvg__text-text--x-and-y-with-less-values-than-characters.png"><img src="render/weasyprint/resvg__text-text--x-and-y-with-less-values-than-characters.png" width="200" alt="resvg__text-text--x-and-y-with-less-values-than-characters in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-text--x-and-y-with-less-values-than-characters.png"><img src="render/weasysvg/resvg__text-text--x-and-y-with-less-values-than-characters.png" width="200" alt="resvg__text-text--x-and-y-with-less-values-than-characters in weasysvg"></a> |

### resvg__text-text-decoration--line-through

[`resvg/text-text-decoration--line-through.svg`](svg/resvg/text-text-decoration--line-through.svg). WeasyPrint: broken, weasysvg: **same**. Noto Sans is not installed: serif, as in Chromium. resvg draws sans.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-text-decoration--line-through.png"><img src="render/chromium/resvg__text-text-decoration--line-through.png" width="200" alt="resvg__text-text-decoration--line-through in Chromium"></a> | <a href="render/resvg/resvg__text-text-decoration--line-through.png"><img src="render/resvg/resvg__text-text-decoration--line-through.png" width="200" alt="resvg__text-text-decoration--line-through in resvg"></a> | <a href="render/weasyprint/resvg__text-text-decoration--line-through.png"><img src="render/weasyprint/resvg__text-text-decoration--line-through.png" width="200" alt="resvg__text-text-decoration--line-through in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-text-decoration--line-through.png"><img src="render/weasysvg/resvg__text-text-decoration--line-through.png" width="200" alt="resvg__text-text-decoration--line-through in weasysvg"></a> |

### resvg__text-text-decoration--style-resolving-3

[`resvg/text-text-decoration--style-resolving-3.svg`](svg/resvg/text-text-decoration--style-resolving-3.svg). WeasyPrint: broken, weasysvg: **same**. Noto Sans is not installed: serif, as in Chromium. resvg draws sans.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-text-decoration--style-resolving-3.png"><img src="render/chromium/resvg__text-text-decoration--style-resolving-3.png" width="200" alt="resvg__text-text-decoration--style-resolving-3 in Chromium"></a> | <a href="render/resvg/resvg__text-text-decoration--style-resolving-3.png"><img src="render/resvg/resvg__text-text-decoration--style-resolving-3.png" width="200" alt="resvg__text-text-decoration--style-resolving-3 in resvg"></a> | <a href="render/weasyprint/resvg__text-text-decoration--style-resolving-3.png"><img src="render/weasyprint/resvg__text-text-decoration--style-resolving-3.png" width="200" alt="resvg__text-text-decoration--style-resolving-3 in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-text-decoration--style-resolving-3.png"><img src="render/weasysvg/resvg__text-text-decoration--style-resolving-3.png" width="200" alt="resvg__text-text-decoration--style-resolving-3 in weasysvg"></a> |

### resvg__text-textPath--with-invalid-path-and-xlink-href

[`resvg/text-textPath--with-invalid-path-and-xlink-href.svg`](svg/resvg/text-textPath--with-invalid-path-and-xlink-href.svg). WeasyPrint: broken, weasysvg: **same**. Neither the path attribute nor the href resolves: nothing is drawn, as in Chromium.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-textPath--with-invalid-path-and-xlink-href.png"><img src="render/chromium/resvg__text-textPath--with-invalid-path-and-xlink-href.png" width="200" alt="resvg__text-textPath--with-invalid-path-and-xlink-href in Chromium"></a> | <a href="render/resvg/resvg__text-textPath--with-invalid-path-and-xlink-href.png"><img src="render/resvg/resvg__text-textPath--with-invalid-path-and-xlink-href.png" width="200" alt="resvg__text-textPath--with-invalid-path-and-xlink-href in resvg"></a> | <a href="render/weasyprint/resvg__text-textPath--with-invalid-path-and-xlink-href.png"><img src="render/weasyprint/resvg__text-textPath--with-invalid-path-and-xlink-href.png" width="200" alt="resvg__text-textPath--with-invalid-path-and-xlink-href in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-textPath--with-invalid-path-and-xlink-href.png"><img src="render/weasysvg/resvg__text-textPath--with-invalid-path-and-xlink-href.png" width="200" alt="resvg__text-textPath--with-invalid-path-and-xlink-href in weasysvg"></a> |

### resvg__text-textPath--with-underline

[`resvg/text-textPath--with-underline.svg`](svg/resvg/text-textPath--with-underline.svg). WeasyPrint: broken, weasysvg: **minor**. Text follows the path and the underline has the position and thickness of Chromium; it does not skip the descender of the g (no skip-ink).

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-textPath--with-underline.png"><img src="render/chromium/resvg__text-textPath--with-underline.png" width="200" alt="resvg__text-textPath--with-underline in Chromium"></a> | <a href="render/resvg/resvg__text-textPath--with-underline.png"><img src="render/resvg/resvg__text-textPath--with-underline.png" width="200" alt="resvg__text-textPath--with-underline in resvg"></a> | <a href="render/weasyprint/resvg__text-textPath--with-underline.png"><img src="render/weasyprint/resvg__text-textPath--with-underline.png" width="200" alt="resvg__text-textPath--with-underline in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-textPath--with-underline.png"><img src="render/weasysvg/resvg__text-textPath--with-underline.png" width="200" alt="resvg__text-textPath--with-underline in weasysvg"></a> |

### resvg__text-tspan--mixed

[`resvg/text-tspan--mixed.svg`](svg/resvg/text-tspan--mixed.svg). WeasyPrint: font, weasysvg: **same**. Noto Sans is not installed: serif, as in Chromium. resvg draws sans.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-tspan--mixed.png"><img src="render/chromium/resvg__text-tspan--mixed.png" width="200" alt="resvg__text-tspan--mixed in Chromium"></a> | <a href="render/resvg/resvg__text-tspan--mixed.png"><img src="render/resvg/resvg__text-tspan--mixed.png" width="200" alt="resvg__text-tspan--mixed in resvg"></a> | <a href="render/weasyprint/resvg__text-tspan--mixed.png"><img src="render/weasyprint/resvg__text-tspan--mixed.png" width="200" alt="resvg__text-tspan--mixed in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-tspan--mixed.png"><img src="render/weasysvg/resvg__text-tspan--mixed.png" width="200" alt="resvg__text-tspan--mixed in weasysvg"></a> |

### resvg__text-tspan--only-with-y

[`resvg/text-tspan--only-with-y.svg`](svg/resvg/text-tspan--only-with-y.svg). WeasyPrint: font, weasysvg: **same**. Noto Sans is not installed: serif, as in Chromium. resvg draws sans.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-tspan--only-with-y.png"><img src="render/chromium/resvg__text-tspan--only-with-y.png" width="200" alt="resvg__text-tspan--only-with-y in Chromium"></a> | <a href="render/resvg/resvg__text-tspan--only-with-y.png"><img src="render/resvg/resvg__text-tspan--only-with-y.png" width="200" alt="resvg__text-tspan--only-with-y in resvg"></a> | <a href="render/weasyprint/resvg__text-tspan--only-with-y.png"><img src="render/weasyprint/resvg__text-tspan--only-with-y.png" width="200" alt="resvg__text-tspan--only-with-y in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-tspan--only-with-y.png"><img src="render/weasysvg/resvg__text-tspan--only-with-y.png" width="200" alt="resvg__text-tspan--only-with-y in weasysvg"></a> |

### resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor

[`resvg/text-writing-mode--tb-with-negative-dy-and-text-anchor.svg`](svg/resvg/text-writing-mode--tb-with-negative-dy-and-text-anchor.svg). WeasyPrint: broken, weasysvg: **same**.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png"><img src="render/chromium/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png" width="200" alt="resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor in Chromium"></a> | <a href="render/resvg/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png"><img src="render/resvg/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png" width="200" alt="resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor in resvg"></a> | <a href="render/weasyprint/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png"><img src="render/weasyprint/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png" width="200" alt="resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png"><img src="render/weasysvg/resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor.png" width="200" alt="resvg__text-writing-mode--tb-with-negative-dy-and-text-anchor in weasysvg"></a> |

### resvg__text-writing-mode--tb-with-rotate

[`resvg/text-writing-mode--tb-with-rotate.svg`](svg/resvg/text-writing-mode--tb-with-rotate.svg). WeasyPrint: broken, weasysvg: **minor**. Vertical: CJK upright, Latin and Arabic sideways, each turned by rotate. The test marks the result as undefined; the run is longer than in Chromium.

| Chromium | resvg | WeasyPrint | weasysvg |
|---|---|---|---|
| <a href="render/chromium/resvg__text-writing-mode--tb-with-rotate.png"><img src="render/chromium/resvg__text-writing-mode--tb-with-rotate.png" width="200" alt="resvg__text-writing-mode--tb-with-rotate in Chromium"></a> | <a href="render/resvg/resvg__text-writing-mode--tb-with-rotate.png"><img src="render/resvg/resvg__text-writing-mode--tb-with-rotate.png" width="200" alt="resvg__text-writing-mode--tb-with-rotate in resvg"></a> | <a href="render/weasyprint/resvg__text-writing-mode--tb-with-rotate.png"><img src="render/weasyprint/resvg__text-writing-mode--tb-with-rotate.png" width="200" alt="resvg__text-writing-mode--tb-with-rotate in WeasyPrint"></a> | <a href="render/weasysvg/resvg__text-writing-mode--tb-with-rotate.png"><img src="render/weasysvg/resvg__text-writing-mode--tb-with-rotate.png" width="200" alt="resvg__text-writing-mode--tb-with-rotate in weasysvg"></a> |
