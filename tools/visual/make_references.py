"""Turn Chromium PDFs into the reference PNGs of the corpus, and record where each one sits on the page.

Usage: make_references.py <dir with <name>.pdf printed by Chromium>

Each PDF is rasterized with PDFium at 96 dpi and cropped to its ink plus a small margin. The crop box goes
into corpus/index.json, so the bench can put the reference back on a page of the same size.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from imaging import ink_box, padded, raster

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"


def main(pdfs: Path) -> None:
    index_path = CORPUS / "index.json"
    index = json.loads(index_path.read_text())
    out = CORPUS / "reference" / "chromium"
    out.mkdir(parents=True, exist_ok=True)
    for item in index:
        image = raster(pdfs / f"{item['name']}.pdf")
        box = ink_box([image]) if image is not None else None
        if image is None or box is None:
            item["reference_box"] = None
            print(f"{item['name']}: no reference")
            continue
        box = padded(box, image.size)
        image.crop(box).save(out / f"{item['name']}.png", optimize=True)
        item["reference_box"] = list(box)
        item["page_size"] = list(image.size)
    index_path.write_text(json.dumps(index, indent=1) + "\n")
    print(f"{len(index)} references")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
