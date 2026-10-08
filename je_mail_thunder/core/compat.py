"""
From the ``SMTPWrapper`` / ``IMAPWrapper`` API to the core mail API, so code written against the wrappers can
move over one call at a time. The wrappers themselves keep working as they are.
"""
from typing import Optional

from je_mail_thunder.attachments.policy import AttachmentPolicy
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers.imap import IMAPProvider
from je_mail_thunder.providers.smtp import SMTPProvider

# The headers of a wrapper's message_setting_dict that are fields of a MailMessage.
_FIELD_OF_HEADER = {
    "subject": "subject", "from": "sender", "to": "to", "cc": "cc", "bcc": "bcc", "reply-to": "reply_to",
}


def legacy_message(message_content: str, message_setting_dict: dict, attach_file: Optional[str] = None,
                   use_html: bool = False) -> MailMessage:
    """
    The message ``SMTPWrapper.create_message`` / ``create_message_with_attach`` build from the same arguments.

    :param message_content: Mail content
    :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
    :param attach_file: File path as str
    :param use_html: the content is HTML
    :return: the message, ready for :meth:`Mail.send <je_mail_thunder.core.mail.Mail.send>`
    :raises MailThunderMessageException: a value has the wrong type
    """
    message_fields = {"html" if use_html else "text": message_content}
    headers = {}
    for name, value in message_setting_dict.items():
        field_name = _FIELD_OF_HEADER.get(str(name).lower())
        if field_name is None:
            headers[name] = value
        else:
            message_fields[field_name] = value
    if attach_file is not None:
        message_fields["attachments"] = [attach_file]
    return MailMessage(headers=headers, **message_fields)


def mail_from_wrappers(smtp=None, imap=None, policy: Optional[AttachmentPolicy] = None) -> Mail:
    """
    A :class:`Mail` on wrappers that are already connected and logged in, such as ``smtp_instance`` and
    ``imap_instance`` after ``later_init()``. The wrappers stay the caller's: closing the ``Mail`` leaves them
    open, and each message needs its own ``sender``.

    :param smtp: an ``SMTPWrapper`` or ``SMTPStartTLSWrapper`` to send with
    :param imap: an ``IMAPWrapper`` to read with
    :param policy: what attachments are checked against before sending
    :return: the ``Mail``
    """
    providers = []
    if smtp is not None:
        providers.append(SMTPProvider(client=smtp))
    if imap is not None:
        providers.append(IMAPProvider(client=imap))
    return Mail(providers=providers, policy=policy)
