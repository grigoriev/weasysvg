"""The gaps of WeasyPrint that weasysvg covers, probed on WeasyPrint alone.

Each probe passes while the gap is there. When a new WeasyPrint closes one, its probe fails and names
the patch to remove, with its tests. Run them in a process of their own: make upstream.
"""

from __future__ import annotations

import re

from native import RED, WHITE, content, lost, near, pixel, render, still_broken, svg, text_matrices

ARABIC = "بعض النص"

# ---------------- conditional processing ----------------


def test_switch_draws_every_child() -> None:
    pdf, _ = render(svg('<switch><rect width="200" height="100" fill="red"/><rect width="200" height="100" fill="blue"/></switch>'))
    still_broken(near(pixel(pdf, 30, 30), (0, 0, 255)), "<switch>", "conditional.apply_conditionals")


def test_system_language_is_ignored() -> None:
    pdf, _ = render(svg('<rect width="200" height="100" fill="red" systemLanguage="xx"/>'))
    still_broken(near(pixel(pdf, 30, 30), RED), "systemLanguage", "conditional.apply_conditionals")


# ---------------- foreignObject ----------------


def test_foreign_object_draws_nothing() -> None:
    body = '<foreignObject width="200" height="100"><div xmlns="http://www.w3.org/1999/xhtml" style="background:red;height:100px">x</div></foreignObject>'
    pdf, _ = render(svg(body))
    still_broken(near(pixel(pdf, 30, 30), WHITE), "<foreignObject>", "foreign_object")


# ---------------- filters ----------------

BOX = '<rect x="20" y="20" width="60" height="40" fill="red" filter="url(#f)"/>'


def filtered(primitives: str) -> tuple[bytes, list[str]]:
    return render(svg(f'<defs><filter id="f" x="-50%" y="-50%" width="200%" height="200%">{primitives}</filter></defs>{BOX}', height=120))


def test_blur_is_dropped() -> None:
    pdf, _ = filtered('<feGaussianBlur stdDeviation="4"/>')
    still_broken(near(pixel(pdf, 13, 30), WHITE, 3), "feGaussianBlur", "filters (vector blur)")


def test_drop_shadow_is_dropped() -> None:
    pdf, _ = filtered('<feDropShadow dx="6" dy="6" stdDeviation="0" flood-color="black"/>')
    still_broken(near(pixel(pdf, 63, 48), WHITE, 3), "feDropShadow", "filters (layers)")


def test_color_matrix_is_dropped() -> None:
    pdf, _ = filtered('<feColorMatrix type="saturate" values="0"/>')
    still_broken(near(pixel(pdf, 30, 30), RED, 5), "feColorMatrix", "filters (recolor)")


def test_turbulence_is_dropped() -> None:
    pdf, _ = filtered('<feTurbulence baseFrequency="0.05"/>')
    still_broken(near(pixel(pdf, 30, 30), RED, 5), "feTurbulence", "filters._fe_turbulence, turbulence")


def test_arithmetic_composite_is_dropped() -> None:
    pdf, _ = filtered('<feFlood flood-color="blue"/><feComposite operator="arithmetic" in2="SourceGraphic" k2="1" k3="1"/>')
    still_broken(near(pixel(pdf, 13, 30), WHITE, 3), "feComposite arithmetic", "filters._arithmetic")


def test_css_drop_shadow_function_is_dropped() -> None:
    pdf, _ = render(svg('<rect x="20" y="20" width="60" height="40" fill="red" style="filter:drop-shadow(6px 6px 0 black)"/>', height=120))
    still_broken(near(pixel(pdf, 63, 48), WHITE, 3), "drop-shadow()", "filters._function_layers")


# ---------------- paint ----------------


def test_gradient_stroke_is_one_unit_wide() -> None:
    gradient = '<linearGradient id="p"><stop stop-color="red"/><stop offset="1" stop-color="red"/></linearGradient>'
    pdf, _ = render(svg(f'<defs>{gradient}</defs><rect x="20" y="20" width="100" height="60" fill="none" stroke="url(#p)" stroke-width="20"/>'))
    still_broken(near(pixel(pdf, 9, 37), WHITE, 3), "the width of gradient strokes", "paint.set_graphical_state")


def test_user_space_pattern_starts_at_the_box() -> None:
    pattern = '<pattern id="p" patternUnits="userSpaceOnUse" width="100" height="100"><rect width="50" height="100" fill="red"/></pattern>'
    pdf, _ = render(svg(f'<defs>{pattern}</defs><rect x="50" width="150" height="100" fill="url(#p)"/>'))
    still_broken(near(pixel(pdf, 45, 30), RED), "the pattern tile origin", "paint.draw_pattern (_pattern_origin)")


def test_pattern_x_moves_the_content_not_the_tile() -> None:
    # x="75" starts the tiles at 75: red from 75 to 125. WeasyPrint shifts the content inside a tile at 0,
    # so the red that crosses the tile edge at 100 is cut off
    pattern = '<pattern id="p" patternUnits="userSpaceOnUse" x="75" width="100" height="100"><rect width="50" height="100" fill="red"/></pattern>'
    pdf, _ = render(svg(f'<defs>{pattern}</defs><rect width="200" height="100" fill="url(#p)"/>'))
    still_broken(near(pixel(pdf, 82, 30), WHITE), "pattern x and y", "paint.draw_pattern (_pattern_origin)")


def test_rotated_gradient_leaves_the_shape_empty() -> None:
    gradient = '<linearGradient id="g" gradientTransform="rotate(45 100 50)"><stop stop-color="red"/><stop offset="1" stop-color="red"/></linearGradient>'
    pdf, _ = render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/>'))
    still_broken(not near(pixel(pdf, 10, 10), RED, 30), "the cell of a transformed gradient", "paint._gradient_cell")


def test_gradient_colors_mix_premultiplied() -> None:
    gradient = '<linearGradient id="g"><stop stop-color="white" stop-opacity="0"/><stop offset="1" stop-color="black"/></linearGradient>'
    pdf, _ = render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/>'))
    still_broken(near(pixel(pdf, 75, 37), (128, 128, 128), 15), "unpremultiplied gradient mixing", "paint (_visible_stops, interpolation exponent)")


def test_invalid_stop_opacity_loses_the_svg() -> None:
    gradient = '<linearGradient id="g"><stop stop-color="red" stop-opacity="abc"/><stop offset="1" stop-color="red"/></linearGradient>'
    _, errors = render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/>'))
    still_broken(lost(errors), "an invalid stop-opacity", "paint._visible_stops")


def test_radial_percentage_uses_the_full_diagonal() -> None:
    # r="50%" of the normalized diagonal reaches x=100 from the center at 100 on a 200 x 200 box:
    # WeasyPrint takes the full diagonal, so the red reaches beyond, to x=141
    gradient = '<radialGradient id="g" gradientUnits="userSpaceOnUse" cx="100" cy="100" r="50%"><stop offset="0.99" stop-color="red"/><stop offset="1" stop-color="white"/></radialGradient>'
    pdf, _ = render(svg(f'<defs>{gradient}</defs><rect width="200" height="200" fill="url(#g)"/>', height=200))
    still_broken(near(pixel(pdf, 90, 75), RED, 40), "radial r percentages", "paint._radial_percentages")


def test_gradient_stops_through_href_are_lost_on_second_use() -> None:
    defs = '<linearGradient id="base"><stop stop-color="red"/><stop offset="1" stop-color="red"/></linearGradient><linearGradient id="a" xlink:href="#base"/>'
    pdf, _ = render(svg(f'<defs>{defs}</defs><rect width="100" height="100" fill="url(#a)"/><rect x="100" width="100" height="100" fill="url(#a)"/>'))
    still_broken(not near(pixel(pdf, 120, 30), RED), "href stops used twice", "paint._materialized_override_iter")


def test_mask_is_set_inside_the_path() -> None:
    mask = '<mask id="m"><rect width="200" height="100" fill="white"/></mask>'
    pdf, _ = render(svg(f'<defs>{mask}</defs><rect width="100" height="100" fill="red" mask="url(#m)"/>'))
    inside = False
    for stream in content(pdf).split("\n"):
        operator = stream.rsplit(" ", 1)[-1]
        if operator == "re":
            inside = True
        elif operator == "gs" and inside:
            break
        elif operator in ("f", "n", "S", "B"):
            inside = False
    still_broken(inside, "the place of the mask state", "_core (early mask)")


def test_mask_content_units_are_ignored() -> None:
    mask = '<mask id="m" maskContentUnits="objectBoundingBox"><rect width="0.5" height="1" fill="white"/></mask>'
    pdf, _ = render(svg(f'<defs>{mask}</defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'))
    still_broken(not near(pixel(pdf, 30, 30), RED), "maskContentUnits", "paint.paint_mask")


def test_self_referencing_mask_loses_the_svg() -> None:
    mask = '<mask id="m"><rect width="100" height="100" fill="white" mask="url(#m)"/></mask>'
    pdf, errors = render(svg(f'<defs>{mask}</defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'))
    still_broken(lost(errors) or not near(pixel(pdf, 30, 30), RED), "a mask that references itself", "paint.paint_mask (_ACTIVE_MASKS)")


def test_blend_mode_is_ignored() -> None:
    body = '<rect width="200" height="100" fill="red"/><rect width="200" height="100" fill="blue" style="mix-blend-mode:multiply"/>'
    pdf, _ = render(svg(body))
    still_broken(near(pixel(pdf, 30, 30), (0, 0, 255), 20), "mix-blend-mode", "paint.blend_mode, _core")


def test_empty_fill_paints_nothing() -> None:
    pdf, _ = render(svg('<rect width="200" height="100" fill=""/>'))
    still_broken(near(pixel(pdf, 30, 30), WHITE), 'fill=""', "paint.drop_empty_presentation")


def test_clip_rule_is_ignored() -> None:
    clip = '<clipPath id="c"><path d="M0 0H200V100H0Z M50 25H150V75H50Z" clip-rule="evenodd"/></clipPath>'
    pdf, _ = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    still_broken(near(pixel(pdf, 75, 37), RED), "clip-rule", "paint.complex_clip")


def test_clip_child_with_a_clip_drops_its_sibling() -> None:
    clip = '<clipPath id="c"><rect width="50" height="50"/><rect x="100" width="100" height="100" clip-path="url(#d)"/></clipPath><clipPath id="d"><circle cx="150" cy="50" r="30"/></clipPath>'
    pdf, _ = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    still_broken(not near(pixel(pdf, 15, 15), RED), "clip-path on clip children", "paint.complex_clip")


def test_text_in_a_clip_path_paints_black() -> None:
    clip = '<clipPath id="c"><text x="10" y="80" font-size="80" font-weight="bold">II</text></clipPath>'
    pdf, _ = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    colors = {pixel(pdf, x, 40) for x in range(0, 150, 2)}
    still_broken(any(near(color, (0, 0, 0), 60) for color in colors), "text in a clip path", "paint.complex_clip")


def test_bounding_box_clip_works_on_rects_only() -> None:
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath>'
    pdf, _ = render(svg(f'<defs>{clip}</defs><circle cx="100" cy="50" r="50" fill="red" clip-path="url(#c)"/>'))
    still_broken(near(pixel(pdf, 56, 30), WHITE), "objectBoundingBox clips on any element", "paint.complex_clip")


def test_link_has_no_bounding_box() -> None:
    # A clip in objectBoundingBox units on an <a> keeps nothing: WeasyPrint has no box for it
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="1" height="1"/></clipPath>'
    pdf, _ = render(svg(f'<defs>{clip}</defs><a clip-path="url(#c)"><rect width="200" height="100" fill="red"/></a>'))
    still_broken(near(pixel(pdf, 56, 30), WHITE), "the bounding box of <a>", "_core.bounding_box_a")


def test_clip_cycle_loses_the_svg() -> None:
    clip = '<clipPath id="c"><rect width="50" height="50" clip-path="url(#c)"/></clipPath>'
    _, errors = render(svg(f'<defs>{clip}</defs><rect width="100" height="100" fill="red" clip-path="url(#c)"/>'))
    still_broken(lost(errors), "clip-path cycles", "_core._draw_node (_ACTIVE_CLIPS)")


def test_negative_offset_of_an_odd_dash_array_uses_half_the_period() -> None:
    # 10 5 3 repeats to a period of 36: an offset of -5 starts 31 into it, WeasyPrint says 13
    style = 'fill="none" stroke="black" stroke-dasharray="10 5 3" stroke-dashoffset="-5"'
    pdf, _ = render(svg(f'<path d="M 0 50 H 200" {style}/>'))
    still_broken(bool(re.search(r"\] 13 d", content(pdf))), "the dash offset of an odd array", "paint._reset_dashes")


def test_circle_outline_is_too_long() -> None:
    # The control point of a quarter circle sits at 1 / sqrt(pi) of the radius, not 0.5523
    pdf, _ = render(svg('<circle cx="100" cy="50" r="40"/>'))
    curves = re.findall(r"((?:-?[\d.]+ ){6})c\b", content(pdf))
    still_broken(bool(curves) and abs(float(curves[0].split()[1]) - 72.57) < 0.01, "the arc constant of circles", "paint.ellipse")


# ---------------- opacity group ----------------


def test_opacity_group_clips_anchored_text() -> None:
    pdf, _ = render(svg('<text x="100" y="60" font-size="40" text-anchor="end" opacity="0.5">WWWW</text>'))
    still_broken(near(pixel(pdf, 15, 35), WHITE, 3), "the box of opacity groups", "_core (opacity group)")


# ---------------- markers ----------------


def test_mid_marker_at_a_cusp_points_down() -> None:
    marker = '<marker id="m" refX="10" refY="10" markerWidth="20" markerHeight="20" orient="auto" markerUnits="userSpaceOnUse"><path d="M 20 10 L 10 16 V 4 Z" fill="blue"/></marker>'
    body = f'<defs>{marker}</defs><path d="M 20 90 C 60 80 70 60 70 20 C 70 60 80 80 120 90" fill="none" stroke="black" marker-mid="url(#m)"/>'
    pdf, _ = render(svg(body, height=120))
    still_broken(pixel(pdf, 57, 15) != (0, 0, 255), "marker orientation", "markers")


# ---------------- text ----------------


def test_font_size_keyword_gives_zero() -> None:
    pdf, _ = render(svg('<text x="10" y="50" font-size="large">Text</text>'))
    sizes = [float(value) for value in re.findall(r" ([\d.]+) Tf", content(pdf))]
    still_broken(not sizes or max(sizes) < 1, "font-size keywords", "text.cascade")


def test_relative_font_size_applies_twice() -> None:
    pdf, _ = render(svg('<g font-size="2em"><text x="10" y="50">Text</text></g>'))
    sizes = [float(value) for value in re.findall(r" ([\d.]+) Tf", content(pdf))]
    still_broken(sizes == [64], "font-size inherited as computed", "text.cascade")


def test_ex_is_half_the_em() -> None:
    pdf, _ = render(svg('<text x="10" y="50" font-family="Liberation Sans" font-size="4ex">Text</text>'))
    sizes = [float(value) for value in re.findall(r" ([\d.]+) Tf", content(pdf))]
    still_broken(sizes == [32], "ex from the x-height of the font", "text.ex_restyle")


def test_nested_text_is_drawn() -> None:
    pdf, _ = render(svg('<text x="10" y="40">A<text x="10" y="80">B</text></text>'))
    still_broken(len(text_matrices(pdf)) > 1, "nested <text>", "text.drop_nested_text")


def test_baseline_uses_a_fixed_ascent() -> None:
    pdf, _ = render(svg('<text x="10" y="50" font-size="100" dominant-baseline="text-before-edge">X</text>', height=200))
    still_broken(any(abs(matrix[5] - 130) < 1 for matrix in text_matrices(pdf)), "dominant-baseline from font metrics", "text.baseline_shift")


def test_text_decoration_is_dropped() -> None:
    pdf, _ = render(svg('<text x="10" y="50" font-size="40" text-decoration="underline">Text</text>'))
    still_broken(" re" not in content(pdf).split("BT", 1)[-1], "text-decoration", "text._decorate")


def test_text_chunk_is_anchored_with_its_parent() -> None:
    # A tspan with its own x starts a chunk, but its width moves the anchor of the chunk before it too
    shift = re.compile(r"1 0 0 1 (-[\d.]+) 0 cm")
    chunked, _ = render(svg('<text x="50" y="40" font-size="20" text-anchor="middle"><tspan>1</tspan><tspan x="50" dy="25">H</tspan></text>', height=120))
    alone, _ = render(svg('<text x="50" y="40" font-size="20" text-anchor="middle">1</text><text x="50" y="65" font-size="20" text-anchor="middle">H</text>', height=120))
    still_broken(sorted(shift.findall(content(chunked))) != sorted(shift.findall(content(alone))), "text-anchor per text chunk", "text.chunk_boxes")


def test_text_is_laid_out_one_character_at_a_time() -> None:
    pdf, _ = render(svg(f'<text x="10" y="50" font-size="20">{ARABIC}</text>'))
    still_broken(len(text_matrices(pdf)) >= len(ARABIC.replace(" ", "")), "whole-run text layout", "text._draw_run")


def test_text_path_is_drawn_on_the_baseline() -> None:
    body = '<text><textPath path="M 10 80 C 50 0 150 0 190 80">Curved</textPath></text>'
    pdf, _ = render(svg(body))
    still_broken(all(abs(matrix[1]) < 1e-6 for matrix in text_matrices(pdf)), "textPath", "textpath")


def test_vertical_text_is_drawn_horizontally() -> None:
    pdf, _ = render(svg('<text x="50" y="20" writing-mode="tb">AB</text>', height=120))
    matrices = text_matrices(pdf)
    still_broken(all(abs(matrix[1]) < 1e-6 for matrix in matrices), "vertical writing-mode", "vertical")


def test_invalid_rotate_loses_the_svg() -> None:
    _, errors = render(svg('<text x="10" y="50" rotate="10 abc">AB</text>'))
    still_broken(lost(errors), "an invalid rotate list", "text.drop_invalid_rotate")


def test_unknown_family_falls_back_to_sans() -> None:
    # Chromium draws an unknown family with Times New Roman (Liberation Serif), Pango with DejaVu Sans
    pdf, _ = render(svg('<text x="10" y="50" font-family="NoSuchFont">Text</text>'))
    still_broken(b"Liberation-Serif" not in pdf, "Chromium font selection", "fonts.resolve_families")


def test_space_after_an_empty_inline_starts_a_line() -> None:
    import pypdfium2 as pdfium
    import weasyprint

    def first_x(body: str) -> float:
        pdf = weasyprint.HTML(string=f"<style>@page{{size:200px 40px;margin:0}} p{{margin:0}}</style><p>{body}</p>").write_pdf()
        textpage = pdfium.PdfDocument(pdf)[0].get_textpage()
        return float(next(textpage.get_charbox(index)[0] for index in range(textpage.count_chars()) if textpage.get_text_range(index, 1).strip()))

    still_broken(first_x("<i></i> Car") > first_x("Car") + 1, "space after an empty inline at the start of a line", "foreign_object._element_to_box")
