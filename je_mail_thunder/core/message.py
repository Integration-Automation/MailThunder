"""
The message every provider sends and returns, independent of SMTP, IMAP or an HTTP API.
"""
from __future__ import annotations

import email.policy
import os
import re
from dataclasses import dataclass, field, fields
from datetime import datetime
from types import MappingProxyType
from typing import Any, Iterable, List, Mapping, Optional, Tuple, Union

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.utils.exception.exceptions import MailThunderMessageException

Addresses = Union[str, Iterable[str], None]

_ADDRESS_FIELDS = ("to", "cc", "bcc", "reply_to")
_HEADER_NAME = re.compile(r"[A-Za-z0-9-]+")
_LINE_BREAK = re.compile(r"[\r\n\x00]")
# Headers the message's own fields and the MIME structure write; a custom header may not replace them.
_RESERVED_HEADERS = frozenset({
    "subject", "from", "to", "cc", "bcc", "reply-to", "content-type", "content-transfer-encoding", "mime-version",
})
# What the standard library's address parser raises on input it cannot handle.
_PARSE_ERRORS = (ValueError, IndexError, AttributeError, TypeError)


def parse_addresses(value: str) -> Optional[Tuple[str, ...]]:
    """
    The addresses in one header value.

    :param value: ``user@host``, ``Name <user@host>``, or several separated by commas
    :return: each address on its own (``Name <user@host>`` or ``user@host``), or ``None`` when ``value`` is not a
        valid address list
    """
    if _LINE_BREAK.search(value):
        return None
    try:
        header = email.policy.default.header_factory("To", value)
        addresses = header.addresses
    except _PARSE_ERRORS:
        return None
    if header.defects or any(not address.username or not address.domain for address in addresses):
        return None
    return tuple(str(address) for address in addresses)


def _address_tuple(name: str, value: Any) -> Tuple[str, ...]:
    """Addresses as given by a caller or a mail header; text that is not an address list is kept as it is."""
    if value is None:
        return ()
    entries = [value] if isinstance(value, str) or not isinstance(value, Iterable) else list(value)
    addresses: List[str] = []
    for entry in entries:
        if not isinstance(entry, str):
            raise MailThunderMessageException(f"{name} must be an address or a list of addresses")
        parsed = parse_addresses(entry)
        if parsed is None and entry.strip():
            addresses.append(entry.strip())
        addresses.extend(parsed or ())
    return tuple(addresses)


def _optional_text(name: str, value: Any) -> Optional[str]:
    if value is not None and not isinstance(value, str):
        raise MailThunderMessageException(f"the message's {name} must be text")
    return value


@dataclass(frozen=True)
class MailMessage:  # pylint: disable=too-many-instance-attributes  # reason: one field per part of a message
    """
    One mail message.

    :param subject: the subject line
    :param to: who it is for: an address, several separated by commas, or a list
    :param cc: who gets a copy, given like ``to``
    :param bcc: who gets a copy the other recipients do not see, given like ``to``
    :param sender: the ``From`` address; the account's user when a message is sent without one
    :param reply_to: where replies go, given like ``to``
    :param text: the plain-text body
    :param html: the HTML body; with ``text`` too, the message carries both as alternatives
    :param attachments: files to send (paths or :class:`Attachment`), or the files that arrived
    :param headers: further headers; a received message has ``Message-ID``, ``In-Reply-To`` and ``References``
    :param message_id: the provider's identifier of a stored message (an IMAP UID, an API id)
    :param date: when a received message was sent
    :raises MailThunderMessageException: a field has the wrong type
    """

    subject: str = ""
    to: Tuple[str, ...] = ()
    cc: Tuple[str, ...] = ()
    bcc: Tuple[str, ...] = ()
    sender: Optional[str] = None
    reply_to: Tuple[str, ...] = ()
    text: Optional[str] = None
    html: Optional[str] = None
    attachments: Tuple[Attachment, ...] = ()
    headers: Mapping[str, str] = field(default_factory=dict)
    message_id: Optional[str] = None
    date: Optional[datetime] = None

    def __post_init__(self) -> None:
        # A frozen dataclass normalises its own fields through object.__setattr__.
        for name in _ADDRESS_FIELDS:
            object.__setattr__(self, name, _address_tuple(name, getattr(self, name)))
        for name in ("subject", "sender", "text", "html"):
            object.__setattr__(self, name, _optional_text(name, getattr(self, name)))
        object.__setattr__(self, "subject", self.subject or "")
        attachments = () if self.attachments is None else self.attachments
        if isinstance(attachments, (str, os.PathLike, Attachment)) or not isinstance(attachments, Iterable):
            attachments = [attachments]
        object.__setattr__(self, "attachments", tuple(Attachment.of(source) for source in attachments))
        headers = {} if self.headers is None else self.headers
        if not isinstance(headers, Mapping):
            raise MailThunderMessageException("the message's headers must be a mapping of names to values")
        object.__setattr__(self, "headers", MappingProxyType(dict(headers)))

    @property
    def recipients(self) -> Tuple[str, ...]:
        """Everyone the message is delivered to: ``to``, ``cc`` and ``bcc``."""
        return self.to + self.cc + self.bcc

    def to_dict(self) -> dict:
        """
        :return: the message as JSON-ready values, for action records; attachments are described, not included
        """
        return {
            "message_id": self.message_id,
            "subject": self.subject,
            "sender": self.sender,
            "to": list(self.to),
            "cc": list(self.cc),
            "bcc": list(self.bcc),
            "reply_to": list(self.reply_to),
            "date": self.date.isoformat() if self.date is not None else None,
            "text": self.text,
            "html": self.html,
            "attachments": [attachment.describe() for attachment in self.attachments],
            "headers": dict(self.headers),
        }


MESSAGE_FIELDS = frozenset(message_field.name for message_field in fields(MailMessage))


def message_from_fields(message_fields: Mapping[str, Any]) -> MailMessage:
    """
    A message from keyword fields, as :meth:`Mail.send <je_mail_thunder.core.mail.Mail.send>` and the
    ``MT_mail_*`` actions take them.

    :param message_fields: :class:`MailMessage` field names and their values
    :return: the message
    :raises MailThunderMessageException: a name is not a message field, or a value has the wrong type
    """
    unknown = sorted(set(message_fields) - MESSAGE_FIELDS)
    if unknown:
        raise MailThunderMessageException(f"unknown message fields {unknown}; the fields are {sorted(MESSAGE_FIELDS)}")
    return MailMessage(**message_fields)


def _check_header(name: Any, value: Any) -> None:
    if not isinstance(name, str) or not _HEADER_NAME.fullmatch(name):
        raise MailThunderMessageException(f"invalid header name {name!r}")
    if name.lower() in _RESERVED_HEADERS:
        raise MailThunderMessageException(f"the header {name!r} is set by the message's own fields")
    if not isinstance(value, str) or _LINE_BREAK.search(value):
        raise MailThunderMessageException(f"the header {name!r} needs a one-line text value")


def check_outgoing(message: MailMessage) -> None:
    """
    Refuse a message that cannot be sent as it is, before anything reaches a server.

    :param message: the message about to be sent or stored as a draft
    :raises MailThunderMessageException: no recipient, no sender, an address that is not valid, or a subject or
        header that would break out of its header line
    """
    if not message.recipients:
        raise MailThunderMessageException("a message needs at least one recipient (to, cc or bcc)")
    if not message.sender:
        raise MailThunderMessageException("a message needs a sender")
    for address in (message.sender,) + message.recipients + message.reply_to:
        parsed = parse_addresses(address)
        if parsed is None or len(parsed) != 1:
            raise MailThunderMessageException(
                f"invalid address {address!r}: use user@host or Name <user@host>, separated by commas")
    if _LINE_BREAK.search(message.subject):
        raise MailThunderMessageException("the subject must be one line")
    for name, value in message.headers.items():
        _check_header(name, value)
