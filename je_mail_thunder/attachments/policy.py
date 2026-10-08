"""
What a message may carry: how many attachments, how large, and of which types.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Optional

from je_mail_thunder.attachments.mime import file_extension
from je_mail_thunder.utils.exception.exceptions import MailThunderAttachmentException

MEBIBYTE = 1024 * 1024
_LIMIT_NAMES = ("max_file_size", "max_total_size", "max_count")
_TYPE_SET_NAMES = ("allowed_extensions", "allowed_mime_types")


def _normalized_extension(extension: str) -> str:
    extension = extension.strip().lower()
    return extension if extension.startswith(".") else "." + extension


def _normalized_set(name: str, values: object, normalize) -> FrozenSet[str]:
    if isinstance(values, str) or not isinstance(values, Iterable):
        raise MailThunderAttachmentException(f"the attachment policy's {name} must be a collection of strings")
    chosen = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise MailThunderAttachmentException(f"the attachment policy's {name} must hold non-empty strings")
        chosen.add(normalize(value))
    return frozenset(chosen)


@dataclass(frozen=True)
class AttachmentPolicy:
    """
    The limits attachments are checked against before a message reaches the provider. ``None`` lifts a limit.

    :param max_file_size: bytes one attachment may have
    :param max_total_size: bytes all attachments of a message may have together
    :param max_count: attachments a message may carry
    :param allowed_extensions: the only extensions accepted (``"pdf"`` or ``".pdf"``, any case)
    :param allowed_mime_types: the only MIME types accepted; ``"image/*"`` accepts every image type
    :raises MailThunderAttachmentException: a limit is negative or not a whole number, or a type set is not a
        collection of strings
    """

    max_file_size: Optional[int] = None
    max_total_size: Optional[int] = None
    max_count: Optional[int] = None
    allowed_extensions: Optional[FrozenSet[str]] = None
    allowed_mime_types: Optional[FrozenSet[str]] = None

    def __post_init__(self) -> None:
        for name in _LIMIT_NAMES:
            limit = getattr(self, name)
            if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
                raise MailThunderAttachmentException(
                    f"the attachment policy's {name} must be a whole number of at least 0")
        normalizers = (_normalized_extension, lambda mime_type: mime_type.strip().lower())
        for name, normalize in zip(_TYPE_SET_NAMES, normalizers):
            values = getattr(self, name)
            if values is not None:
                # A frozen dataclass normalises its own fields through object.__setattr__.
                object.__setattr__(self, name, _normalized_set(name, values, normalize))

    def allows_extension(self, filename: str) -> bool:
        """
        :param filename: an attachment's file name
        :return: True when its last extension is allowed (always, without ``allowed_extensions``)
        """
        return self.allowed_extensions is None or file_extension(filename) in self.allowed_extensions

    def allows_mime_type(self, content_type: str) -> bool:
        """
        :param content_type: an attachment's MIME type
        :return: True when it, or its ``<main type>/*``, is allowed (always, without ``allowed_mime_types``)
        """
        if self.allowed_mime_types is None:
            return True
        content_type = content_type.strip().lower()
        wildcard = content_type.split("/", 1)[0] + "/*"
        return content_type in self.allowed_mime_types or wildcard in self.allowed_mime_types


# What :class:`~je_mail_thunder.core.mail.Mail` checks against unless it is given another policy: 25 MiB, the
# message size Gmail and Microsoft 365 accept, and any type.
DEFAULT_ATTACHMENT_POLICY = AttachmentPolicy(max_file_size=25 * MEBIBYTE, max_total_size=25 * MEBIBYTE)
