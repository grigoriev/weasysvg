"""The CSS of an SVG as Chromium reads it when it prints: @supports, custom properties, var() and light-dark().

Touches:
- ``svg.css.find_stylesheets_rules``: the rules inside an ``@supports`` whose condition holds apply.
  WeasyPrint skipped every ``@supports`` block.
- ``svg.css.parse_declarations``, also as ``svg.parse_declarations``: custom properties (``--name``) are
  kept, with their name as written. A color declaration that is invalid when parsed is dropped, so the
  presentation attribute or an earlier rule still applies, as in Chromium. WeasyPrint dropped every name
  that starts with "-", and wrote any value over the attribute: fill: foo painted black.
- ``svg.Node.cascade``: after the cascade, the computed values. A custom property substitutes its var()
  and inherits that result. Every other property, presentation attributes included, then substitutes its
  var(). A value that cannot be substituted is invalid at computed-value time: the property is unset,
  inherited or initial, and the presentation attribute does not come back. An invalid color presentation
  attribute is unset too, as Chromium ignores it. light-dark() in a color takes its first color,
  currentcolor in any case takes the color, and initial, inherit, unset and revert apply.

The color scheme is light: a PDF has no dark mode, and Chromium prints in the light scheme whatever
``color-scheme`` asks for. draw.io 29 writes its theme that way: the fill of each shape is
``var(--ge-adaptive-bg, #ffffff)``, the root sets that property to ``light-dark(#ffffff, ...)`` inside
``@supports (color: light-dark(#000, #fff))``. WeasyPrint read the var() as a color, failed, and painted
every shape black. Measured with Playwright, Chromium 156.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Iterator
from typing import Any

import cssselect2
import tinycss2
from tinycss2.color5 import parse_color
from weasyprint import svg as wp_svg
from weasyprint.css.tokens import InvalidValues, remove_whitespace
from weasyprint.css.validation.expanders import EXPANDERS
from weasyprint.css.validation.properties import validate_non_shorthand
from weasyprint.svg import css as wp_css

PAINTS = frozenset(("fill", "stroke"))
COLOR_PROPERTIES = PAINTS | frozenset(("color", "stop-color", "flood-color", "lighting-color"))
# Not inherited in CSS; WeasyPrint lists stop-color alone among them
NOT_INHERITED_COLORS = frozenset(("stop-color", "flood-color", "lighting-color"))
PAINT_KEYWORDS = frozenset(("none", "context-fill", "context-stroke"))
WIDE_KEYWORDS = frozenset(("initial", "inherit", "unset", "revert", "revert-layer"))
# Without a user style sheet, revert rolls back to the user agent: as unset for these properties
UNSET_KEYWORDS = frozenset(("unset", "revert", "revert-layer"))
SPACE = frozenset(("whitespace", "comment"))
PARENS = "() block"
# Attributes that hold text, not a CSS value: var() in them stays as written
NOT_PROPERTIES = frozenset(("content", "href", "id", "class", "style", "lang"))

_ORIGINAL_FIND_RULES = wp_css.find_stylesheets_rules
_ORIGINAL_CASCADE: list[Callable[[Any, Any], None]] = [wp_svg.Node.cascade]

Lookup = Callable[[str], "list[Any] | None"]


class Invalid(Exception):  # noqa: N818
    """A var() with no value and no fallback: its declaration is invalid at computed-value time."""


class _Syntax(Exception):  # noqa: N818
    """An @supports condition that does not parse: the whole rule is ignored."""


# ---------------- tokens ----------------


def _significant(tokens: Iterable[Any]) -> list[Any]:
    return [token for token in tokens if token.type not in SPACE]


def _ident(token: Any) -> str | None:
    return str(token.lower_value) if token.type == "ident" else None


def _stripped(tokens: list[Any]) -> list[Any]:
    """tokens without the white space and comments at either end."""
    start, end = 0, len(tokens)
    while start < end and tokens[start].type in SPACE:
        start += 1
    while end > start and tokens[end - 1].type in SPACE:
        end -= 1
    return tokens[start:end]


def _split_commas(tokens: list[Any]) -> list[list[Any]]:
    parts: list[list[Any]] = [[]]
    for token in tokens:
        if token.type == "literal" and token.value == ",":
            parts.append([])
        else:
            parts[-1].append(token)
    return parts


def _serialize(tokens: list[Any]) -> str:
    return str(tinycss2.serialize(tokens)).strip()


def _has_var(value: object) -> bool:
    # WeasyPrint keeps a few objects among the attributes, such as the tree a <use> draws
    return isinstance(value, str) and "var(" in value.lower()


# ---------------- light-dark() ----------------


def _light(tokens: list[Any]) -> list[Any]:
    result = []
    for token in tokens:
        if token.type != "function":
            result.append(token)
            continue
        arguments = _light(token.arguments)
        parts = _split_commas(arguments)
        if token.lower_name == "light-dark" and len(parts) == 2 and all(_significant(part) for part in parts):
            result.extend(_stripped(parts[0]))
            continue
        function = copy.copy(token)
        function.arguments = arguments
        result.append(function)
    return result


def light(value: str) -> str:
    """value with each light-dark(a, b) replaced by a: printing uses the light color scheme."""
    if "light-dark" not in value.lower():
        return value
    return _serialize(_light(tinycss2.parse_component_value_list(value)))


# ---------------- validity ----------------


def _valid_color(token: Any) -> bool:
    return parse_color(token) is not None


def _valid_paint(tokens: list[Any]) -> bool:
    """<paint>: none, a color, context-fill, context-stroke, or a URL with an optional none or color after it."""
    if not tokens:
        return False
    first, rest = tokens[0], tokens[1:]
    if first.type == "url" or (first.type == "function" and first.lower_name == "url"):
        return not rest or (len(rest) == 1 and (_ident(rest[0]) == "none" or _valid_color(rest[0])))
    return not rest and (_ident(first) in PAINT_KEYWORDS or _valid_color(first))


def valid(name: str, value: str) -> bool:
    """Whether value parses for the color property name; a value with var() parses until it is substituted."""
    if _has_var(value):
        return True
    tokens = _significant(tinycss2.parse_component_value_list(value))
    if len(tokens) == 1 and _ident(tokens[0]) in WIDE_KEYWORDS:
        return True
    if name in PAINTS:
        return _valid_paint(tokens)
    return len(tokens) == 1 and _valid_color(tokens[0])


def parse_declarations(content: Any) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """The declarations of a rule or a style attribute, as WeasyPrint reads them, with custom properties kept.

    A color declaration that is invalid when parsed is dropped, as Chromium drops it.
    """
    normal: list[tuple[str, str]] = []
    important: list[tuple[str, str]] = []
    for declaration in tinycss2.parse_blocks_contents(content):
        if declaration.type != "declaration":
            continue
        custom = declaration.name.startswith("--")
        if declaration.name.startswith("-") and not custom:
            continue
        name = declaration.name if custom else declaration.lower_name
        value = _serialize(declaration.value)
        if name in COLOR_PROPERTIES and not valid(name, value):
            continue
        (important if declaration.important else normal).append((name, value))
    return normal, important


# ---------------- @supports ----------------


def _supported_declaration(content: list[Any]) -> bool:
    """( <declaration> ): Chromium supports the property with that value. Else general-enclosed: false."""
    declaration = tinycss2.parse_one_declaration(content)
    if declaration.type != "declaration":
        return False
    if declaration.name.startswith("--"):
        return True
    name = declaration.lower_name
    if name in COLOR_PROPERTIES:
        return valid(name, _serialize(declaration.value))
    tokens = remove_whitespace(declaration.value)
    if not tokens:
        return False
    # The validators of WeasyPrint for HTML: a property it cannot apply counts as unsupported
    validator = EXPANDERS.get(name, validate_non_shorthand)
    try:
        list(validator(tokens, name, None))
    except InvalidValues:
        return False
    return True


def _supported_selector(arguments: list[Any]) -> bool:
    try:
        return bool(cssselect2.compile_selector_list(arguments))
    except cssselect2.SelectorError:
        return False


def _in_parens(token: Any) -> bool:
    if token.type == "function":
        # selector() is the only function Chromium and weasysvg both know; any other is general-enclosed
        return token.lower_name == "selector" and _supported_selector(token.arguments)
    if token.type != PARENS:
        raise _Syntax
    inner = _significant(token.content)
    if inner and (inner[0].type in (PARENS, "function") or _ident(inner[0]) == "not"):
        try:
            return _condition(inner)
        except _Syntax:
            return False
    return _supported_declaration(token.content)


def _condition(tokens: list[Any]) -> bool:
    """<supports-condition>: not one, or several joined by and, or by or, never both."""
    if not tokens:
        raise _Syntax
    if _ident(tokens[0]) == "not":
        if len(tokens) != 2:
            raise _Syntax
        return not _in_parens(tokens[1])
    results = [_in_parens(tokens[0])]
    operator = None
    rest = tokens[1:]
    while rest:
        word = _ident(rest[0])
        if len(rest) < 2 or word not in ("and", "or") or operator not in (None, word):
            raise _Syntax
        operator = word
        results.append(_in_parens(rest[1]))
        rest = rest[2:]
    return any(results) if operator == "or" else all(results)


def supports(prelude: list[Any]) -> bool:
    """Whether the condition of an @supports rule holds; a condition that does not parse never does."""
    try:
        return _condition(_significant(prelude))
    except _Syntax:
        return False


def find_stylesheets_rules(tree: Any, stylesheet_rules: Iterable[Any], url: Any, font_config: Any, url_fetcher: Any) -> Iterator[Any]:
    """The rules of WeasyPrint, with those of each @supports block whose condition holds."""
    for rule in stylesheet_rules:
        if rule.type == "at-rule" and rule.lower_at_keyword == "supports":
            if rule.content is not None and supports(rule.prelude):
                rules = tinycss2.parse_rule_list(rule.content, skip_comments=True, skip_whitespace=True)
                yield from find_stylesheets_rules(tree, rules, url, font_config, url_fetcher)
        else:
            yield from _ORIGINAL_FIND_RULES(tree, [rule], url, font_config, url_fetcher)


# ---------------- var() ----------------


def _var(function: Any, lookup: Lookup) -> list[Any]:
    """The tokens a var() stands for: the custom property, else the fallback."""
    name, *rest = _significant(function.arguments) or [None]
    if name is None or name.type != "ident" or not name.value.startswith("--"):
        raise Invalid
    fallback = None
    if rest:
        if not (rest[0].type == "literal" and rest[0].value == ","):
            raise Invalid
        comma = next(index for index, token in enumerate(function.arguments) if token is rest[0])
        fallback = _stripped(function.arguments[comma + 1 :])
    value = lookup(name.value)
    if value is not None:
        return value
    if fallback is None:
        raise Invalid
    return substitute(fallback, lookup)


def substitute(tokens: list[Any], lookup: Lookup) -> list[Any]:
    """tokens with each var() replaced, in functions and blocks too; raises Invalid when one cannot be."""
    result = []
    for token in tokens:
        if token.type == "function" and token.lower_name == "var":
            result.extend(_var(token, lookup))
        elif token.type == "function":
            function = copy.copy(token)
            function.arguments = substitute(token.arguments, lookup)
            result.append(function)
        elif token.type in (PARENS, "[] block"):
            block = copy.copy(token)
            block.content = substitute(token.content, lookup)
            result.append(block)
        else:
            result.append(token)
    return result


class _CustomProperties:
    """The custom properties of one element, with their var() substituted on demand.

    An inherited property comes substituted from the parent. A property in a cycle, or with a var() that
    cannot be substituted, is invalid: it neither applies nor inherits.
    """

    def __init__(self, attrib: dict[str, str]) -> None:
        self.attrib = attrib
        self.done: dict[str, list[Any] | None] = {}
        self.resolving: list[str] = []
        self.cyclic: set[str] = set()

    def _substituted(self, name: str, tokens: list[Any]) -> list[Any] | None:
        self.resolving.append(name)
        try:
            return substitute(tokens, self.lookup)
        except Invalid:
            return None
        finally:
            self.resolving.pop()

    def lookup(self, name: str) -> list[Any] | None:
        if name in self.done:
            return self.done[name]
        if name not in self.attrib:
            return None
        if name in self.resolving:
            self.cyclic.update(self.resolving[self.resolving.index(name) :])
            return None
        raw = self.attrib[name]
        tokens: list[Any] | None = tinycss2.parse_component_value_list(raw)
        if _has_var(raw):
            tokens = self._substituted(name, tokens or [])
        if name in self.cyclic:
            tokens = None
        self.done[name] = tokens
        return tokens


def _custom_properties(attrib: dict[str, str]) -> Lookup:
    """Substitute the var() of each custom property of attrib in place, and return the lookup of their tokens.

    An invalid one is removed. The others are read as they are, when a var() asks for them.
    """
    properties = _CustomProperties(attrib)
    for name in [name for name, value in attrib.items() if name.startswith("--") and _has_var(value)]:
        tokens = properties.lookup(name)
        if tokens is None:
            del attrib[name]
        else:
            attrib[name] = _serialize(tokens)
    return properties.lookup


# ---------------- computed values ----------------


def _inherited(name: str) -> bool:
    return name not in wp_svg.NOT_INHERITED_ATTRIBUTES and name not in NOT_INHERITED_COLORS


def _unset(parent: Any, child: Any, name: str, inherit: bool | None = None) -> None:
    """The inherited value of the property when it inherits (or inherit asks for it), else the initial one."""
    inherited = parent.attrib.get(name) if parent is not None else None
    if inherited is not None and (_inherited(name) if inherit is None else inherit):
        child.attrib[name] = inherited
    else:
        child.attrib.pop(name, None)


def _computed_color(parent: Any, child: Any, name: str) -> None:
    value = child.attrib[name]
    keyword = value.strip().lower()
    if keyword == "initial":
        del child.attrib[name]
    elif keyword in ("inherit", *UNSET_KEYWORDS):
        _unset(parent, child, name, inherit=True if keyword == "inherit" else None)
    elif not valid(name, value := light(value)):
        _unset(parent, child, name)
    elif value.lower() == "currentcolor":
        # currentcolor in color itself is the inherited color
        if name == "color":
            _unset(parent, child, name, inherit=True)
        else:
            child.attrib[name] = child.attrib.get("color", "black")
    else:
        child.attrib[name] = value


def _property(name: str) -> bool:
    """Whether the attribute can hold a CSS value; data-*, aria-* and namespaced attributes, such as the
    foreignObject stash, hold text."""
    return not (name.startswith(("--", "data-", "aria-", "{")) or name in NOT_PROPERTIES)


def compute(parent: Any, child: Any) -> None:
    """The computed values of child, once the cascade has written its attributes; parent is None at the root."""
    lookup = _custom_properties(child.attrib)
    for name in [name for name, value in child.attrib.items() if _property(name) and _has_var(value)]:
        try:
            child.attrib[name] = _serialize(substitute(tinycss2.parse_component_value_list(child.attrib[name]), lookup))
        except Invalid:
            _unset(parent, child, name)
    # color first: the other colors read it for currentcolor
    for name in ("color", *sorted(COLOR_PROPERTIES - {"color"})):
        if name in child.attrib:
            _computed_color(parent, child, name)


def cascade(self: Any, child: Any) -> None:
    """The cascade of WeasyPrint, then the computed values of child."""
    _ORIGINAL_CASCADE[0](self, child)
    compute(None if self is child else self, child)


def install() -> None:
    # Once per process: a second wrap would call the cascade of text, which calls this one
    if wp_css.parse_declarations is parse_declarations:
        return
    _ORIGINAL_CASCADE[0] = wp_svg.Node.cascade
    wp_svg.Node.cascade = cascade
    wp_css.find_stylesheets_rules = find_stylesheets_rules
    wp_css.parse_declarations = parse_declarations
    wp_svg.parse_declarations = parse_declarations
