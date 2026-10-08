"""
Between :class:`MailMessage` and the RFC 5322 / MIME form the SMTP and IMAP providers exchange with a server.
"""
from datetime import datetime
from email import message_from_bytes
from email import policy
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import List, Optional

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.attachments.mime import DEFAULT_CONTENT_TYPE, safe_filename
from je_mail_thunder.core.message import MailMessage

# What a received message keeps besides its own fields: the identifiers that tie a conversation together.
_KEPT_HEADERS = ("Message-ID", "In-Reply-To", "References")
# MIME does not allow these types the base64 encoding attachments are sent in (RFC 2046 5.2.1), so a
# saved message (.eml) goes out as a plain file.
_CONTAINER_TYPES = frozenset({"message", "multipart"})
# What the standard library raises on a header or body it cannot decode.
_DECODE_ERRORS = (ValueError, LookupError, IndexError, AttributeError, TypeError)


def to_email_message(message: MailMessage) -> EmailMessage:
    """
    Build the MIME message a server is sent.

    :param message: a message that passed :func:`~je_mail_thunder.core.message.check_outgoing`
    :return: the message with its bodies as alternatives and its attachments read from disk
    :raises AttachmentNotFound: a file to attach cannot be read
    """
    email_message = EmailMessage()
    email_message["Subject"] = message.subject
    if message.sender:
        email_message["From"] = message.sender
    for header, addresses in (("To", message.to), ("Cc", message.cc), ("Bcc", message.bcc),
                              ("Reply-To", message.reply_to)):
        if addresses:
            email_message[header] = ", ".join(addresses)
    for name, value in message.headers.items():
        email_message[name] = value
    if message.html is not None and message.text is not None:
        email_message.set_content(message.text)
        email_message.add_alternative(message.html, subtype="html")
    elif message.html is not None:
        email_message.set_content(message.html, subtype="html")
    else:
        email_message.set_content(message.text or "")
    for attachment in message.attachments:
        main_type, _, sub_type = attachment.content_type.partition("/")
        if main_type in _CONTAINER_TYPES or not sub_type:
            main_type, sub_type = DEFAULT_CONTENT_TYPE.split("/")
        email_message.add_attachment(
            attachment.read(), maintype=main_type, subtype=sub_type, filename=attachment.filename)
    return email_message


def _header_text(email_message: EmailMessage, name: str) -> Optional[str]:
    try:
        value = email_message[name]
    except _DECODE_ERRORS:
        return None
    return None if value is None else str(value)


def _header_values(email_message: EmailMessage, name: str) -> List[str]:
    try:
        return [str(value) for value in email_message.get_all(name, [])]
    except _DECODE_ERRORS:
        return []


def _body(email_message: EmailMessage, subtype: str) -> Optional[str]:
    try:
        part = email_message.get_body(preferencelist=(subtype,))
        return None if part is None else part.get_content()
    except _DECODE_ERRORS:
        return None


def _date(email_message: EmailMessage) -> Optional[datetime]:
    value = _header_text(email_message, "Date")
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except _DECODE_ERRORS:
        return None


def _attachment(part: EmailMessage) -> Attachment:
    content = part.get_payload(decode=True)
    if content is None:
        # An attached message (message/rfc822) is a container: its content is the message inside.
        content = b"".join(inner.as_bytes() for inner in part.iter_parts())
    return Attachment(
        filename=safe_filename(part.get_filename()), content_type=part.get_content_type(), content=content)


def _attachments(email_message: EmailMessage) -> List[Attachment]:
    try:
        return [_attachment(part) for part in email_message.iter_attachments()]
    except _DECODE_ERRORS:
        return []


def from_email_message(email_message: EmailMessage, message_id: Optional[str] = None) -> MailMessage:
    """
    Read a parsed MIME message. Headers and parts that cannot be decoded are left out instead of failing the
    whole message, since its content is whatever a stranger sent.

    :param email_message: a message parsed with ``email.policy.default``
    :param message_id: the provider's identifier of the message
    :return: the message, with attachment names made safe to write to disk
    """
    headers = {}
    for name in _KEPT_HEADERS:
        value = _header_text(email_message, name)
        if value is not None:
            headers[name] = value
    return MailMessage(
        subject=_header_text(email_message, "Subject") or "",
        to=_header_values(email_message, "To"),
        cc=_header_values(email_message, "Cc"),
        bcc=_header_values(email_message, "Bcc"),
        sender=_header_text(email_message, "From"),
        reply_to=_header_values(email_message, "Reply-To"),
        text=_body(email_message, "plain"),
        html=_body(email_message, "html"),
        attachments=_attachments(email_message),
        headers=headers,
        message_id=message_id,
        date=_date(email_message),
    )


def parse_message(raw: bytes, message_id: Optional[str] = None) -> MailMessage:
    """
    :param raw: a message as a server stores it
    :param message_id: the provider's identifier of the message
    :return: the message
    """
    return from_email_message(message_from_bytes(raw, policy=policy.default), message_id)
