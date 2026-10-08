"""
Which events a handler wants: by sender, recipient, subject, body, attachments, time and metadata.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Optional, Union

from je_mail_thunder.attachments.mime import file_extension
from je_mail_thunder.core.events import MailEvent
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.utils.exception.exceptions import MailThunderTriggerException

Pattern = Union[str, "re.Pattern[str]"]


def _found(pattern: Optional[Pattern], texts: Iterable[Optional[str]]) -> bool:
    """True without a pattern, or when one of the texts holds it (any case), or matches the compiled pattern."""
    if pattern is None:
        return True
    for text in texts:
        if text is None:
            continue
        if isinstance(pattern, str):
            if pattern.casefold() in text.casefold():
                return True
        elif pattern.search(text):
            return True
    return False


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class MailFilter:
    """
    A filter matches an event when every rule it has matches. Text rules look for the text anywhere in the
    field, ignoring case, or apply a compiled regular expression.

    :param sender: in the sender's address
    :param recipient: in one of the ``to`` / ``cc`` / ``bcc`` addresses
    :param subject: in the subject
    :param body: in the text or the HTML body
    :param has_attachments: True for messages with attachments, False for messages without
    :param attachment_type: an extension (``"pdf"``) or a MIME type (``"image/*"``) one attachment must have
    :param since: the message is not older than this
    :param until: the message is not newer than this
    :param metadata: values the event's metadata must hold
    :param predicate: a function of the event that must return true
    """

    sender: Optional[Pattern] = None
    recipient: Optional[Pattern] = None
    subject: Optional[Pattern] = None
    body: Optional[Pattern] = None
    has_attachments: Optional[bool] = None
    attachment_type: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    predicate: Optional[Callable[[MailEvent], Any]] = None

    def __post_init__(self) -> None:
        # A frozen dataclass normalises its own fields through object.__setattr__.
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata or {})))

    @classmethod
    def of(cls, value: Any) -> MailFilter:
        """
        :param value: ``None`` (everything), a :class:`MailFilter`, a mapping of its rules, or a function of
            the event
        :return: the filter
        :raises MailThunderTriggerException: the value is none of these, or names an unknown rule
        """
        if value is None:
            return cls()
        if isinstance(value, MailFilter):
            return value
        if callable(value):
            return cls(predicate=value)
        if isinstance(value, Mapping):
            rules = {rule.name for rule in fields(cls)}
            unknown = sorted(set(value) - rules)
            if unknown:
                raise MailThunderTriggerException(f"unknown filter rules {unknown}; the rules are {sorted(rules)}")
            return cls(**value)
        raise MailThunderTriggerException(
            f"a filter is a mapping, a function or a MailFilter, not {type(value).__name__}")

    def _matches_attachments(self, event: MailEvent) -> bool:
        attachments = (event.attachment,) if event.attachment is not None else ()
        if event.message is not None:
            attachments += event.message.attachments
        if self.has_attachments is not None and bool(attachments) != self.has_attachments:
            return False
        if self.attachment_type is None:
            return True
        wanted = self.attachment_type.strip().lower()
        if "/" not in wanted:
            wanted = wanted if wanted.startswith(".") else "." + wanted
            return any(file_extension(attachment.filename) == wanted for attachment in attachments)
        prefix = wanted[:-1] if wanted.endswith("/*") else None
        return any(attachment.content_type.lower() == wanted
                   or (prefix is not None and attachment.content_type.lower().startswith(prefix))
                   for attachment in attachments)

    def _matches_time(self, event: MailEvent) -> bool:
        moment = event.message.date if event.message is not None and event.message.date is not None \
            else event.timestamp
        moment = _aware(moment)
        if self.since is not None and moment < _aware(self.since):
            return False
        return self.until is None or moment <= _aware(self.until)

    def matches(self, event: MailEvent) -> bool:
        """
        :param event: the event to test
        :return: True when every rule of the filter matches it
        """
        message = event.message if event.message is not None else MailMessage()
        return (
            _found(self.sender, (message.sender,))
            and _found(self.recipient, message.recipients)
            and _found(self.subject, (message.subject,))
            and _found(self.body, (message.text, message.html))
            and self._matches_attachments(event)
            and self._matches_time(event)
            and all(event.metadata.get(key) == value for key, value in self.metadata.items())
            and (self.predicate is None or bool(self.predicate(event)))
        )

    def describe(self) -> dict:
        """
        :return: the rules that are set, as JSON-ready text
        """
        described = {}
        for rule in fields(self):
            value = getattr(self, rule.name)
            if rule.name == "metadata":
                described.update({"metadata": dict(value)} if value else {})
            elif value is not None:
                described[rule.name] = getattr(value, "__name__", None) or str(getattr(value, "pattern", value))
        return described
