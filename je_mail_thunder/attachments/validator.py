"""
The check every outgoing attachment passes before the provider sees the message:
count -> existence -> size -> extension -> MIME type -> total size.
"""
from typing import Iterable

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.attachments.mime import file_extension
from je_mail_thunder.attachments.policy import AttachmentPolicy
from je_mail_thunder.utils.exception.exceptions import (
    AttachmentCountExceeded,
    AttachmentTooLarge,
    AttachmentTypeNotAllowed,
    MailThunderAttachmentException,
    TotalAttachmentSizeExceeded,
)
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger


def _checked_size(attachment: Attachment, policy: AttachmentPolicy) -> int:
    """One attachment against the per-file rules; returns its size."""
    size = attachment.size
    if policy.max_file_size is not None and size > policy.max_file_size:
        raise AttachmentTooLarge(attachment.filename, size, policy.max_file_size)
    if not policy.allows_extension(attachment.filename):
        raise AttachmentTypeNotAllowed(attachment.filename, "extension", file_extension(attachment.filename))
    if not policy.allows_mime_type(attachment.content_type):
        raise AttachmentTypeNotAllowed(attachment.filename, "MIME type", attachment.content_type)
    return size


def validate_attachments(attachments: Iterable[Attachment], policy: AttachmentPolicy) -> int:
    """
    Check a message's attachments against a policy.

    :param attachments: the attachments of one message
    :param policy: the limits to check against
    :return: the attachments' total size in bytes
    :raises AttachmentCountExceeded: more attachments than ``max_count``
    :raises AttachmentNotFound: a file to send does not exist
    :raises AttachmentTooLarge: one attachment is over ``max_file_size``
    :raises AttachmentTypeNotAllowed: an extension or MIME type is not allowed
    :raises TotalAttachmentSizeExceeded: together they are over ``max_total_size``
    """
    attachments = tuple(attachments)
    try:
        if policy.max_count is not None and len(attachments) > policy.max_count:
            raise AttachmentCountExceeded(len(attachments), policy.max_count)
        total = sum(_checked_size(attachment, policy) for attachment in attachments)
        if policy.max_total_size is not None and total > policy.max_total_size:
            raise TotalAttachmentSizeExceeded(total, policy.max_total_size)
    except MailThunderAttachmentException as error:
        mail_thunder_logger.error(f"validate_attachments, failed: {repr(error)}")
        raise
    return total
