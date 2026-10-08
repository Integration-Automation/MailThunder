"""
A small template language in the standard library, with the part of the Jinja2 syntax a mail needs:

* ``{{ user.name }}``, with filters: ``{{ name | upper }}``, ``{{ note | default("none") }}``;
* ``{% if failed > 0 %} ... {% elif skipped %} ... {% else %} ... {% endif %}``;
* ``{% for test in failures %} {{ loop.index }}. {{ test.name }} {% endfor %}``;
* ``{# a comment #}``.

A template only reads the context: it looks up mapping keys, sequence indexes and public attributes that are
not callable, and nothing in it is evaluated as Python. A ``{% ... %}`` tag alone on its line takes the line with
it, so block tags leave no blank lines in a text mail.
"""
from __future__ import annotations

import html
import re
from collections import ChainMap
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from je_mail_thunder.utils.exception.exceptions import (
    TemplateContextError,
    TemplateRenderError,
    TemplateSyntaxError,
)

# What one rendering may produce, so a loop over a large context cannot exhaust memory.
MAX_OUTPUT_CHARACTERS = 5 * 1024 * 1024
_TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.DOTALL)
_REST_OF_LINE = re.compile(r"[ \t]*(?:\r?\n|\Z)")
_SPACE = re.compile(r"\s*")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_NAME_START = re.compile(r"[A-Za-z_]\w*", re.ASCII)
_NAME_PART = re.compile(r"\.\w+", re.ASCII)
_SYMBOL = re.compile(r"[=!<>]=|[<>|(),]")
_LITERALS = {"true": True, "false": False, "none": None}
_COMPARISONS: Dict[str, Callable[[Any, Any], bool]] = {
    "==": lambda left, right: left == right,
    "!=": lambda left, right: left != right,
    "<": lambda left, right: left < right,
    "<=": lambda left, right: left <= right,
    ">": lambda left, right: left > right,
    ">=": lambda left, right: left >= right,
}
_UNDEFINED = object()
Token = Tuple[str, str]
# pylint: disable=too-few-public-methods  # reason: one small class per template construct, each with render()


class SafeText(str):
    """Text that is output as it is where other values are HTML-escaped (the ``safe`` filter)."""


_FILTERS: Dict[str, Callable[..., Any]] = {
    "upper": lambda value: str(value).upper(),
    "lower": lambda value: str(value).lower(),
    "title": lambda value: str(value).title(),
    "trim": lambda value: str(value).strip(),
    "length": len,
    "join": lambda value, separator=", ": str(separator).join(str(item) for item in value),
    "safe": SafeText,
}


def _string_end(source: str, start: int) -> int:
    """Where the quoted string that opens at ``start`` ends; -1 when none opens there or it is not closed."""
    quote = source[start]
    if quote not in "\"'":
        return -1
    position = start + 1
    while position < len(source):
        if source[position] == quote:
            return position + 1
        if source[position] != "\\":
            position += 1
            continue
        # A backslash takes the next character of its line with it, so an escaped quote does not close the string.
        if source[position + 1:position + 2] in ("", "\n"):
            return -1
        position += 2
    return -1


def _name_end(source: str, start: int) -> int:
    """Where the dotted name that begins at ``start`` ends; -1 when none begins there."""
    match = _NAME_START.match(source, start)
    if match is None:
        return -1
    end = match.end()
    part = _NAME_PART.match(source, end)
    while part is not None:
        end = part.end()
        part = _NAME_PART.match(source, end)
    return end


def _match_end(pattern: "re.Pattern[str]") -> Callable[[str, int], int]:
    """A reader that tells where ``pattern`` stops matching from a position; -1 when it does not match there."""

    def end_of(source: str, start: int) -> int:
        match = pattern.match(source, start)
        return -1 if match is None else match.end()

    return end_of


# Each kind of token with the function that finds its end, tried in this order.
_TOKEN_READERS: Tuple[Tuple[str, Callable[[str, int], int]], ...] = (
    ("string", _string_end),
    ("number", _match_end(_NUMBER)),
    ("name", _name_end),
    ("symbol", _match_end(_SYMBOL)),
)


def _token_at(source: str, position: int) -> Tuple[str, int]:
    """The kind of the token at ``position`` and where it ends; no kind when nothing there is a token."""
    for kind, reader in _TOKEN_READERS:
        end = reader(source, position)
        if end > position:
            return kind, end
    return "", position


def _tokens(source: str, line: int) -> List[Token]:
    """The tokens of an expression; anything that is not one is a syntax error."""
    found: List[Token] = []
    position = _SPACE.match(source).end()
    while position < len(source):
        kind, end = _token_at(source, position)
        if not kind:
            raise TemplateSyntaxError(f"cannot read {source[position:].strip()!r}", line)
        found.append((kind, source[position:end]))
        position = _SPACE.match(source, end).end()
    return found


def _step(value: Any, key: str) -> Any:
    """One part of a dotted name: a mapping key, a sequence index, or a public attribute that is not callable."""
    if isinstance(value, Mapping):
        return value.get(key, _UNDEFINED)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value[int(key)] if key.isdigit() and int(key) < len(value) else _UNDEFINED
    if key.startswith("_"):
        return _UNDEFINED
    attribute = getattr(value, key, _UNDEFINED)
    return _UNDEFINED if callable(attribute) else attribute


class _Operand:
    """A literal or a dotted name, with the filters applied to it."""

    def __init__(self, source: str, literal: Any = None, path: Tuple[str, ...] = ()) -> None:
        self.source = source
        self.literal = literal
        self.path = path
        self.filters: List[Tuple[str, Tuple[Any, ...]]] = []

    def value(self, context: Mapping[str, Any]) -> Any:
        """The operand's value in ``context``, or the undefined marker when its name is not there."""
        value = self.literal
        if self.path:
            value = context
            for key in self.path:
                value = _step(value, key)
                if value is _UNDEFINED:
                    break
        for name, arguments in self.filters:
            value = self._filtered(value, name, arguments)
        return value

    def _filtered(self, value: Any, name: str, arguments: Tuple[Any, ...]) -> Any:
        if name == "default":
            if value is not _UNDEFINED:
                return value
            return arguments[0] if arguments else ""
        if value is _UNDEFINED:
            return value
        try:
            return _FILTERS[name](value, *arguments)
        except (TypeError, ValueError) as error:
            raise TemplateRenderError(f"the filter {name!r} cannot be applied to {self.source!r}: {error}") from error

    def required(self, context: Mapping[str, Any]) -> Any:
        """The operand's value; a name the context does not hold is an error."""
        value = self.value(context)
        if value is _UNDEFINED:
            raise TemplateContextError([".".join(self.path)])
        return value


class _Condition:
    """``[not] operand [comparison operand]``; a name the context does not hold counts as false."""

    def __init__(self, negated: bool, left: _Operand, comparison: str = "", right: Optional[_Operand] = None) -> None:
        self.negated = negated
        self.left = left
        self.comparison = comparison
        self.right = right

    def holds(self, context: Mapping[str, Any]) -> bool:
        """True when the condition is met in ``context``."""
        left = self.left.value(context)
        left = None if left is _UNDEFINED else left
        if self.right is None:
            return bool(left) != self.negated
        right = self.right.value(context)
        try:
            result = _COMPARISONS[self.comparison](left, None if right is _UNDEFINED else right)
        except TypeError as error:
            raise TemplateRenderError(
                f"cannot compare {self.left.source!r} {self.comparison} {self.right.source!r}: {error}") from error
        return bool(result) != self.negated


class _Writer:
    """Collects the output and stops a rendering that grows past the limit."""

    def __init__(self, autoescape: bool) -> None:
        self.autoescape = autoescape
        self._parts: List[str] = []
        self._size = 0

    def write(self, text: str) -> None:
        """Add ``text`` to the output."""
        self._size += len(text)
        if self._size > MAX_OUTPUT_CHARACTERS:
            raise TemplateRenderError(f"the rendered template is over {MAX_OUTPUT_CHARACTERS} characters")
        self._parts.append(text)

    def text(self) -> str:
        """Everything written so far."""
        return "".join(self._parts)


class _Text:
    """Text between tags, output as it is."""

    def __init__(self, text: str) -> None:
        self.text = text

    def render(self, _context: Mapping[str, Any], writer: _Writer) -> None:
        """Write the text."""
        writer.write(self.text)


class _Output:
    """``{{ value }}``."""

    def __init__(self, operand: _Operand) -> None:
        self.operand = operand

    def render(self, context: Mapping[str, Any], writer: _Writer) -> None:
        """Write the value, HTML-escaped where the writer asks for it."""
        value = self.operand.required(context)
        text = "" if value is None else str(value)
        writer.write(html.escape(text) if writer.autoescape and not isinstance(value, SafeText) else text)


class _If:
    """``{% if %}`` with its ``{% elif %}`` branches and its ``{% else %}``."""

    def __init__(self, branches: List[Tuple[_Condition, list]], otherwise: list) -> None:
        self.branches = branches
        self.otherwise = otherwise

    def render(self, context: Mapping[str, Any], writer: _Writer) -> None:
        """Render the first branch whose condition holds, else the ``else`` part."""
        for condition, body in self.branches:
            if condition.holds(context):
                _render(body, context, writer)
                return
        _render(self.otherwise, context, writer)


class _For:
    """``{% for name in items %}``; the body also sees ``loop.index``, ``first``, ``last`` and ``length``."""

    def __init__(self, name: str, items: _Operand, body: list) -> None:
        self.name = name
        self.items = items
        self.body = body

    def render(self, context: Mapping[str, Any], writer: _Writer) -> None:
        """Render the body once per item."""
        items = self.items.required(context)
        if isinstance(items, (str, bytes)) or not isinstance(items, (Sequence, Mapping, set, frozenset)):
            raise TemplateRenderError(f"{self.items.source!r} is not a list to loop over")
        items = list(items)
        for index, item in enumerate(items):
            loop = {"index": index + 1, "first": index == 0, "last": index == len(items) - 1, "length": len(items)}
            _render(self.body, ChainMap({self.name: item, "loop": loop}, context), writer)


def _render(nodes: list, context: Mapping[str, Any], writer: _Writer) -> None:
    for node in nodes:
        node.render(context, writer)


def _stands_alone(source: str, tag: "re.Match[str]") -> bool:
    """True for a block tag with nothing but spaces around it on its line."""
    if not tag.group().startswith("{%"):
        return False
    line_start = source.rfind("\n", 0, tag.start()) + 1
    return not source[line_start:tag.start()].strip(" \t") and _REST_OF_LINE.match(source, tag.end()) is not None


def _pieces(source: str) -> List[Tuple[str, str, int]]:
    """
    The template as ``(kind, content, line)``: ``text``, or the inside of a ``{{``, ``{%`` or ``{#`` tag.
    A block tag alone on its line takes the whole line with it, so it leaves no blank line in the mail.
    """
    pieces: List[Tuple[str, str, int]] = []
    position = 0
    line = 1
    for tag in _TAG.finditer(source):
        text_end, next_position = tag.start(), tag.end()
        if _stands_alone(source, tag):
            text_end = source.rfind("\n", 0, tag.start()) + 1
            next_position = _REST_OF_LINE.match(source, tag.end()).end()
        pieces.append(("text", source[position:max(text_end, position)], line))
        line += source.count("\n", position, tag.start())
        pieces.append((tag.group()[:2], tag.group()[2:-2].strip(), line))
        line += source.count("\n", tag.start(), next_position)
        position = next_position
    pieces.append(("text", source[position:], line))
    return pieces


class _Parser:
    """Turns template text into nodes, and notes which names it reads from the context."""

    def __init__(self, source: str) -> None:
        self._pieces = _pieces(source)
        self._position = 0
        self._line = 1
        self._loop_names: List[str] = []
        self.names: Set[str] = set()

    def parse(self) -> list:
        """The nodes of the whole template."""
        nodes, _ = self._block(())
        return nodes

    def _block(self, enders: Tuple[str, ...]) -> Tuple[list, str]:
        """Nodes up to one of the ``enders`` tags (returned with its arguments), or to the end of the text."""
        nodes: list = []
        while self._position < len(self._pieces):
            kind, piece, self._line = self._pieces[self._position]
            self._position += 1
            if kind == "{{":
                nodes.append(_Output(self._operand(_tokens(piece, self._line))))
            elif kind == "{%":
                word, _, rest = piece.partition(" ")
                if word in enders:
                    return nodes, piece
                nodes.append(self._statement(word, rest.strip()))
            elif kind == "text" and piece:
                nodes.append(_Text(piece))
        if enders:
            raise TemplateSyntaxError(f"missing {{% {enders[-1]} %}}", self._line)
        return nodes, ""

    def _statement(self, word: str, rest: str):
        if word == "if":
            return self._if(rest)
        if word == "for":
            return self._for(rest)
        raise TemplateSyntaxError(f"unknown tag {word!r}", self._line)

    def _if(self, rest: str) -> _If:
        branches: List[Tuple[_Condition, list]] = []
        otherwise: list = []
        condition = self._condition(rest)
        while True:
            body, ender = self._block(("elif", "else", "endif"))
            branches.append((condition, body))
            word, _, arguments = ender.partition(" ")
            if word == "elif":
                condition = self._condition(arguments)
                continue
            if word == "else":
                otherwise, _ = self._block(("endif",))
            return _If(branches, otherwise)

    def _for(self, rest: str) -> _For:
        parts = rest.split(None, 2)
        if len(parts) != 3 or parts[1] != "in" or _NAME_START.fullmatch(parts[0]) is None:
            raise TemplateSyntaxError("a loop is written: for item in items", self._line)
        name = parts[0]
        items = self._operand(_tokens(parts[2], self._line))
        self._loop_names.append(name)
        body, _ = self._block(("endfor",))
        self._loop_names.pop()
        return _For(name, items, body)

    def _condition(self, source: str) -> _Condition:
        tokens = _tokens(source, self._line)
        negated = bool(tokens) and tokens[0] == ("name", "not")
        tokens = tokens[1:] if negated else tokens
        split = next((index for index, token in enumerate(tokens) if token[1] in _COMPARISONS), None)
        if split is None:
            return _Condition(negated, self._operand(tokens))
        return _Condition(negated, self._operand(tokens[:split]), tokens[split][1], self._operand(tokens[split + 1:]))

    def _operand(self, tokens: List[Token]) -> _Operand:
        if not tokens or tokens[0][0] == "symbol":
            raise TemplateSyntaxError("a value is missing", self._line)
        operand = self._value(tokens[0])
        position = 1
        while position < len(tokens):
            position = self._filter(operand, tokens, position)
        return operand

    def _value(self, token: Token) -> _Operand:
        kind, text = token
        if kind == "string":
            return _Operand(text, literal=text[1:-1].replace("\\" + text[0], text[0]))
        if kind == "number":
            return _Operand(text, literal=float(text) if "." in text else int(text))
        if text in _LITERALS:
            return _Operand(text, literal=_LITERALS[text])
        path = tuple(text.split("."))
        if path[0] not in self._loop_names and path[0] != "loop":
            self.names.add(path[0])
        return _Operand(text, path=path)

    def _literal(self, token: Token) -> Any:
        kind, text = token
        if kind == "symbol" or (kind == "name" and text not in _LITERALS):
            raise TemplateSyntaxError(
                f"a filter argument is a text, a number, true, false or none, not {text!r}", self._line)
        return self._value(token).literal

    def _filter(self, operand: _Operand, tokens: List[Token], position: int) -> int:
        """Read ``| name`` or ``| name(arguments)`` at ``position``; return the position after it."""
        if tokens[position] != ("symbol", "|") or position + 1 >= len(tokens) or tokens[position + 1][0] != "name":
            raise TemplateSyntaxError(f"cannot read {tokens[position][1]!r} in {operand.source!r}", self._line)
        name = tokens[position + 1][1]
        if name != "default" and name not in _FILTERS:
            raise TemplateSyntaxError(f"unknown filter {name!r}; the filters are {sorted([*_FILTERS, 'default'])}",
                                      self._line)
        position += 2
        arguments: List[Any] = []
        if position < len(tokens) and tokens[position] == ("symbol", "("):
            closing = next((index for index in range(position, len(tokens)) if tokens[index] == ("symbol", ")")), None)
            if closing is None:
                raise TemplateSyntaxError(f"the filter {name!r} is missing its )", self._line)
            arguments = [self._literal(token) for token in tokens[position + 1:closing] if token[1] != ","]
            position = closing + 1
        operand.filters.append((name, tuple(arguments)))
        return position


class CompiledTemplate:
    """Template text parsed once and rendered as often as needed."""

    def __init__(self, source: str) -> None:
        """
        :param source: the template text
        :raises TemplateSyntaxError: the text is not valid template syntax
        """
        if not isinstance(source, str):
            raise TemplateSyntaxError("a template is text")
        parser = _Parser(source)
        self._nodes = parser.parse()
        #: The names the template reads from the context (loop variables are not among them).
        self.names = frozenset(parser.names)

    def render(self, context: Optional[Mapping[str, Any]] = None, autoescape: bool = False) -> str:
        """
        :param context: the values the template's names stand for
        :param autoescape: HTML-escape every value that is output, except one marked with the ``safe`` filter
        :return: the rendered text
        :raises TemplateContextError: the template outputs a name the context does not hold
        :raises TemplateRenderError: a value does not fit what the template does with it
        """
        writer = _Writer(autoescape)
        _render(self._nodes, context or {}, writer)
        return writer.text()


def render_string(source: str, context: Optional[Mapping[str, Any]] = None, autoescape: bool = False) -> str:
    """
    Parse and render template text in one step.

    :param source: the template text
    :param context: the values the template's names stand for
    :param autoescape: HTML-escape the values that are output
    :return: the rendered text
    """
    return CompiledTemplate(source).render(context, autoescape)
