"""
What can happen to mail, in the same words for every provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, List, Mapping, Optional

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderAttachmentException,
    MailThunderAuthenticationException,
    MailThunderConnectionException,
    MailThunderException,
)

MESSAGE_RECEIVED = "message_received"
MESSAGE_SENT = "message_sent"
MESSAGE_FAILED = "message_failed"
ATTACHMENT_RECEIVED = "attachment_received"
ATTACHMENT_REJECTED = "attachment_rejected"
AUTHENTICATION_FAILED = "authentication_failed"
CONNECTION_FAILED = "connection_failed"
EVENT_NAMES = (
    MESSAGE_RECEIVED, MESSAGE_SENT, MESSAGE_FAILED, ATTACHMENT_RECEIVED, ATTACHMENT_REJECTED,
    AUTHENTICATION_FAILED, CONNECTION_FAILED,
)
#: Subscribing to this name receives every event.
ANY_EVENT = "*"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class MailEvent:  # pylint: disable=too-many-instance-attributes  # reason: one field per fact about an event
    """
    One thing that happened.

    :param name: one of :data:`EVENT_NAMES`
    :param message: the message it is about, when there is one
    :param attachment: the attachment it is about (``attachment_received``)
    :param error: the exception behind a failure
    :param provider: the name of the provider it happened on
    :param folder: the folder a received message is in
    :param timestamp: when it happened (UTC)
    :param metadata: anything else the source of the event knows
    """

    name: str
    message: Optional[MailMessage] = None
    attachment: Optional[Attachment] = None
    error: Optional[BaseException] = None
    provider: str = ""
    folder: str = ""
    timestamp: datetime = field(default_factory=_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # A frozen dataclass normalises its own fields through object.__setattr__.
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata or {})))

    def to_dict(self) -> dict:
        """
        :return: the event as JSON-ready values; the error is its ``repr``, the attachment its description
        """
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "folder": self.folder,
            "message": self.message.to_dict() if self.message is not None else None,
            "attachment": self.attachment.describe() if self.attachment is not None else None,
            "error": repr(self.error) if self.error is not None else None,
            "metadata": dict(self.metadata),
        }


def failure_events(error: MailThunderException, message: Optional[MailMessage] = None, provider: str = "",
                   sending: bool = False) -> List[MailEvent]:
    """
    The events a failed operation stands for: what went wrong, and for a send also ``message_failed``.

    :param error: what the operation raised
    :param message: the message that was being sent, when it got that far
    :param provider: the provider's name
    :param sending: the operation was a send or a draft
    :return: the events, the most specific first
    """
    events: List[MailEvent] = []
    for kind, name in ((MailThunderAuthenticationException, AUTHENTICATION_FAILED),
                       (MailThunderConnectionException, CONNECTION_FAILED),
                       (MailThunderAttachmentException, ATTACHMENT_REJECTED)):
        if isinstance(error, kind):
            events.append(MailEvent(name, message=message, error=error, provider=provider))
    if sending:
        events.append(MailEvent(MESSAGE_FAILED, message=message, error=error, provider=provider))
    return events
