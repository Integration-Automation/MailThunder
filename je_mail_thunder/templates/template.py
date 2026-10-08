"""
The mail template model: a subject, a text body and an HTML body that share one context, the variables they
need, and free metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple

from je_mail_thunder.templates.engine import CompiledTemplate
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderTemplateException,
    TemplateContextError,
    TemplateSyntaxError,
)

_PARTS = ("subject", "text", "html")
_REQUIRED = object()


@dataclass(frozen=True)
class TemplateVariable:
    """
    A variable a template declares.

    :param name: the variable's name in the context
    :param description: what it holds, for the people who fill it in
    :param default: the value used when the context has none; a variable without one is required
    """

    name: str
    description: str = ""
    default: Any = _REQUIRED

    @property
    def required(self) -> bool:
        """True when the context must hold the variable."""
        return self.default is _REQUIRED

    def to_dict(self) -> dict:
        """
        :return: the variable as JSON-ready values
        """
        described: Dict[str, Any] = {"name": self.name, "description": self.description, "required": self.required}
        if not self.required:
            described["default"] = self.default
        return described


@dataclass(frozen=True)
class RenderedTemplate:
    """What a template gave for one context; a part the template does not have is ``None``."""

    subject: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None

    def to_dict(self) -> dict:
        """
        :return: the three parts as a dict
        """
        return {"subject": self.subject, "text": self.text, "html": self.html}


def _declared(variables: Any) -> Tuple[TemplateVariable, ...]:
    """Variables from a list of names (all required) or a mapping of name to ``{"default", "description"}``."""
    if variables is None:
        return ()
    if isinstance(variables, Mapping):
        declared = []
        for name, details in variables.items():
            details = details if isinstance(details, Mapping) else {}
            declared.append(TemplateVariable(
                str(name), str(details.get("description", "")), details.get("default", _REQUIRED)))
        return tuple(declared)
    if isinstance(variables, (list, tuple)):
        return tuple(item if isinstance(item, TemplateVariable) else TemplateVariable(str(item)) for item in variables)
    raise MailThunderTemplateException("a template's variables are a list of names or a mapping of names to details")


@dataclass(frozen=True)
class MailTemplate:
    """
    A reusable mail: ``mail.send(to=..., template="test_report", context={...})``.

    :param name: the name it is loaded and sent by
    :param subject: the subject line's template
    :param text: the plain-text body's template
    :param html: the HTML body's template; the values it outputs are HTML-escaped
    :param variables: what the context must hold: a list of names, or a mapping of each name to
        ``{"description": ..., "default": ...}`` (a variable with a default is optional)
    :param metadata: anything else about the template (owner, purpose, ...)
    :raises TemplateSyntaxError: a part is not valid template syntax
    :raises MailThunderTemplateException: the template has no part at all, or its variables are malformed
    """

    name: str
    subject: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None
    variables: Tuple[TemplateVariable, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if all(getattr(self, part) is None for part in _PARTS):
            raise MailThunderTemplateException(f"the template {self.name!r} has no subject, text or html")
        compiled = {}
        for part in _PARTS:
            source = getattr(self, part)
            if source is not None:
                compiled[part] = self._compile(part, source)
        # A frozen dataclass normalises its own fields through object.__setattr__.
        object.__setattr__(self, "_compiled", compiled)
        object.__setattr__(self, "variables", _declared(self.variables))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata or {})))

    def _compile(self, part: str, source: Any) -> CompiledTemplate:
        try:
            return CompiledTemplate(source)
        except TemplateSyntaxError as error:
            raise TemplateSyntaxError(f"the template {self.name!r}, {part}: {error}") from error

    @classmethod
    def from_mapping(cls, name: str, values: Mapping[str, Any]) -> MailTemplate:
        """
        :param name: the template's name
        :param values: ``subject``, ``text``, ``html``, ``variables`` and ``metadata``, as a template file holds them
        :return: the template
        :raises MailThunderTemplateException: ``values`` is not a mapping, or holds another key
        """
        if not isinstance(values, Mapping):
            raise MailThunderTemplateException(f"the template {name!r} must be a JSON object")
        unknown = sorted(set(values) - set(_PARTS) - {"variables", "metadata"})
        if unknown:
            raise MailThunderTemplateException(f"the template {name!r} has the unknown keys {unknown}")
        return cls(name=name, **values)

    @property
    def referenced_variables(self) -> FrozenSet[str]:
        """Every name the three parts read from the context."""
        compiled: Dict[str, CompiledTemplate] = getattr(self, "_compiled")
        return frozenset().union(*(part.names for part in compiled.values()))

    def context_for(self, context: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        """
        The context a rendering uses: the declared defaults under the given values.

        :param context: the values for this mail
        :return: the complete context
        :raises TemplateContextError: declared variables without a default are missing (all of them are named)
        """
        if context is not None and not isinstance(context, Mapping):
            raise MailThunderTemplateException("a template's context is a mapping of names to values")
        complete = {variable.name: variable.default for variable in self.variables if not variable.required}
        complete.update(context or {})
        missing = [variable.name for variable in self.variables if variable.name not in complete]
        if missing:
            raise TemplateContextError(missing, self.name)
        return complete

    def render(self, context: Optional[Mapping[str, Any]] = None) -> RenderedTemplate:
        """
        :param context: the values for this mail
        :return: the subject (one line, trimmed), the text and the HTML
        :raises TemplateContextError: the context does not hold what the template needs
        :raises TemplateRenderError: a value does not fit what the template does with it
        """
        complete = self.context_for(context)
        compiled: Dict[str, CompiledTemplate] = getattr(self, "_compiled")
        rendered: Dict[str, str] = {}
        for part, template in compiled.items():
            try:
                rendered[part] = template.render(complete, autoescape=part == "html")
            except TemplateContextError as error:
                raise TemplateContextError(error.missing, self.name) from error
        if "subject" in rendered:
            rendered["subject"] = rendered["subject"].strip()
        return RenderedTemplate(**rendered)

    def to_dict(self) -> dict:
        """
        :return: the template as JSON-ready values, with the names it reads from the context
        """
        return {
            "name": self.name, "subject": self.subject, "text": self.text, "html": self.html,
            "variables": [variable.to_dict() for variable in self.variables],
            "referenced_variables": sorted(self.referenced_variables),
            "metadata": dict(self.metadata),
        }
