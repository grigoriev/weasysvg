"""The WeasyPrint internals weasysvg replaces or relies on, and a fingerprint of each.

Usage: hooks.py           write upstream/hooks.json for the installed WeasyPrint
       hooks.py --check   list the internals whose code changed since the snapshot

A fingerprint hashes the source of the definition, read from its file, without comments and white
space: layout leaves it alone, it reads the same on every Python version, and the patches of weasysvg in
the running process do not change it. A changed fingerprint names the
patches to review; it does not say they broke.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import io
import json
import sys
import textwrap
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "upstream" / "hooks.json"

# module:qualified.name -> what in weasysvg depends on it
HOOKS: dict[str, str] = {
    "weasyprint.images:RasterImage": "filters._draw_image draws the pixels of feTurbulence through it",
    "weasyprint.images:SVGImage.__init__": "_core: tree passes and fetcher wrappers run before it",
    "weasyprint.html:handle_element": "conditional.handle_element: the lang of the element an image belongs to",
    "weasyprint.images:SVGImage.draw": "conditional.svgimage_draw: nested SVGs are built while it draws",
    "weasyprint.images:get_image_from_uri": "conditional.get_image_from_uri: a cache read by key alone, keyed by URL",
    "weasyprint.document:Document._build_layout_context": "conditional.install: the partial of original_get_image_from_uri",
    "weasyprint.svg:SVG.__init__": "_core, paint: svg.paths, svg.masks, svg.filters, cursor state",
    "weasyprint.svg:SVG.draw_node": "_core._draw_node and _draw_with_effects mirror its order of effects",
    "weasyprint.svg:SVG.set_graphical_state": "paint.set_graphical_state",
    "weasyprint.svg:SVG.draw_markers": "markers.vertices writes the form it reads",
    "weasyprint.svg:Node.cascade": "text.cascade; restylers cascade children before they change a node",
    "weasyprint.svg:Node.__iter__": "restylers rely on cached children",
    "weasyprint.svg:Node.override_iter": "paint._materialized_override_iter",
    "weasyprint.svg:Node.text_children": "text.drop_invalid_rotate: rotate parsed during the cascade; text.keep_nested_tails: the tails of a <tspan> it drops",
    "weasyprint.svg:Node.tag": "clip paths, masks and the root are retagged <g> while they draw",
    "weasyprint.svg:TAGS": "markers, text, foreign_object and paint register drawing functions",
    "weasyprint.svg:NOT_INHERITED_ATTRIBUTES": "paint adds mix-blend-mode and isolation",
    "weasyprint.svg.defs:draw_gradient": "paint.draw_gradient, filters._recolored_gradient",
    "weasyprint.svg.defs:draw_pattern": "paint.draw_pattern",
    "weasyprint.svg.defs:paint_mask": "paint.paint_mask replaces it",
    "weasyprint.svg.bounding_box:BOUNDING_BOX_METHODS": "_core gives <a> a box (bounding_box_a)",
    "weasyprint.svg.bounding_box:bounding_box_g": "_core.bounding_box_a for an <a> around shapes",
    "weasyprint.svg.defs:use": "restylers and clips walk <use> trees",
    "weasyprint.svg.defs:apply_filters": "_core removes filter before draw_node applies it",
    "weasyprint.svg.utils:color": "filters._color recolors through it",
    "weasyprint.svg.utils:alpha_value": "paint._visible_stops, filters",
    "weasyprint.svg.utils:transform": "paint gradient and pattern matrices",
    "weasyprint.svg.text:text": "text._draw_run, textpath, vertical repeat its positioning; text.chunk_boxes undoes its box merge; text.recorded_draw_first_line reads the matrix it passes for each character",
    "weasyprint.svg.text:TextBox": "glyphs.show, text._draw_run",
    "weasyprint.svg.path:path": "markers rebuild the vertices it leaves",
    "weasyprint.svg.shapes:circle": "paint.ellipse replaces it",
    "weasyprint.svg.shapes:ellipse": "paint.ellipse replaces it",
    "weasyprint.svg.shapes:line": "markers",
    "weasyprint.svg.shapes:polyline": "markers",
    "weasyprint.svg.shapes:polygon": "markers",
    "weasyprint.svg.bounding_box:is_valid_bounding_box": "filters, paint",
    "weasyprint.layout.table:table_layout": "foreign_object._table_layout",
    "weasyprint.draw:draw_page": "foreign_object draws its pages into the SVG stream",
    "weasyprint.formatting_structure.build:element_to_box": "foreign_object._element_to_box drops empty inline boxes",
    "weasyprint.formatting_structure.build:marker_to_box": "foreign_object._marker_to_box draws symbol markers as Chromium does",
    "weasyprint.draw.text:draw_first_line": "glyphs.show, text._draw_run; text.carried_shifts moves the shifts of its TJ arrays; ink.run_glyphs places glyphs as it does; text.recorded_draw_first_line wraps it for the whole process",
    "weasyprint.text.fonts:get_pango_font_key": "ink.run_glyphs reads the size of each run",
    "weasyprint.text.fonts:get_hb_object_data": "ink.run_glyphs reads the font file of each run",
    "weasyprint.text.fonts:get_pango_font_hb_face": "ink.run_glyphs reads the HarfBuzz face of each run",
    "weasyprint.draw.text:draw_emojis": "text._draw_run",
    "weasyprint.text.line_break:split_first_line": "glyphs, text, textpath, vertical",
    "weasyprint.text.line_break:Layout.setup": "text._track sets attributes after it",
    "weasyprint.text.line_break:Layout.set_text": "text._track sets attributes after it",
    "weasyprint.text.line_break:Layout.reactivate": "text._track runs again after it",
    "weasyprint.pdf.stream:Stream.add_group": "_core._add_group keeps the absolute matrix; _core.measure_text removes its scratch group from _resources; _core, filters, paint groups",
    "weasyprint.pdf.stream:Stream.set_alpha_state": "filters blur masks, paint clip masks",
    "weasyprint.pdf.stream:Stream.add_pattern": "paint._scaled_add_pattern; _core._add_pattern keeps the absolute matrix",
    "weasyprint.pdf.stream:Stream.create_interpolation_function": "paint._scaled_add_pattern forces its exponent n to 1",
    "weasyprint.pdf.stream:Stream.clone": "groups start with an identity ctm",
    "weasyprint.css:ComputedStyle.__missing__": "fonts._computed_families, called through COMPUTER_FUNCTIONS",
    "weasyprint.css:AnonymousStyle.__missing__": "fonts._computed_families, called through COMPUTER_FUNCTIONS",
    "weasyprint.urls:URLFetcherResponse": "fetch.CachingFetcher",
}


def _names(node: ast.AST) -> list[str]:
    """The names a top-level node defines: a function, a class, or the targets of an assignment."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    else:
        return []
    return [target.id for target in targets if isinstance(target, ast.Name)]


def _definitions(tree: ast.Module, qualified: str) -> list[ast.AST]:
    """Every definition of the last name, a property getter and its setter included."""
    scope: ast.AST = tree
    *outer, last = qualified.split(".")
    for part in outer:
        found = next((node for node in ast.iter_child_nodes(scope) if part in _names(node)), None)
        if found is None:
            raise LookupError(qualified)
        scope = found
    nodes = [node for node in ast.iter_child_nodes(scope) if last in _names(node)]
    if not nodes:
        raise LookupError(qualified)
    return nodes


def _source(source: str, node: ast.AST) -> str:
    """The source of a definition with its decorators: @property turned @cached_property matters."""
    decorators = [ast.get_source_segment(source, decorator) or "" for decorator in getattr(node, "decorator_list", [])]
    return "".join(f"@{decorator}\n" for decorator in decorators) + textwrap.dedent(ast.get_source_segment(source, node) or "")


def fingerprint(target: str) -> str:
    """The hash of the source of target, or "missing" when the module or the name is gone."""
    module, qualified = target.split(":")
    spec = importlib.util.find_spec(module)
    if spec is None or spec.origin is None:
        return "missing"
    source = Path(spec.origin).read_text()
    try:
        nodes = _definitions(ast.parse(source), qualified)
    except LookupError:
        return "missing"
    return hashlib.sha256(_bare("\n".join(_source(source, node) for node in nodes)).encode()).hexdigest()[:16]


def _bare(code: str) -> str:
    """The code without comments and without any white space."""
    lines = code.splitlines(keepends=True)
    for token in sorted(tokenize.generate_tokens(io.StringIO(code).readline), key=lambda item: item.start, reverse=True):
        if token.type == tokenize.COMMENT:
            row, column = token.start
            lines[row - 1] = lines[row - 1][:column] + lines[row - 1][token.end[1] :]
    return "".join("".join(lines).split())


def snapshot() -> dict[str, object]:
    import weasyprint

    return {"weasyprint": weasyprint.__version__, "hooks": {target: {"fingerprint": fingerprint(target), "used_by": used_by} for target, used_by in HOOKS.items()}}


def changes(saved: dict[str, object]) -> list[str]:
    """One line per internal that changed, appeared or disappeared since the snapshot."""
    hooks = saved["hooks"]
    assert isinstance(hooks, dict)
    out = []
    for target, used_by in HOOKS.items():
        before = hooks.get(target, {}).get("fingerprint")
        now = fingerprint(target)
        if before is None:
            out.append(f"{target}: not in the snapshot, run tools/upstream/hooks.py")
        elif now != before:
            out.append(f"{target}: {'gone' if now == 'missing' else 'changed'} since WeasyPrint {saved['weasyprint']}; review {used_by}")
    out += [f"{target}: in the snapshot, no longer hooked" for target in hooks if target not in HOOKS]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare with the snapshot instead of writing it")
    args = parser.parse_args()
    if args.check:
        found = changes(json.loads(SNAPSHOT.read_text()))
        print("\n".join(found) or "no change")
        return 1 if found else 0
    SNAPSHOT.write_text(json.dumps(snapshot(), indent=1) + "\n")
    print(f"wrote {SNAPSHOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
