"""
The attachment model shared by every provider: a file to send, or one that arrived with a message.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, Union

from je_mail_thunder.attachments.mime import DEFAULT_CONTENT_TYPE, guess_content_type, safe_filename
from je_mail_thunder.utils.exception.exceptions import AttachmentNotFound, MailThunderAttachmentException

AttachmentSource = Union[str, "os.PathLike[str]", "Attachment"]


@dataclass(frozen=True)
class Attachment:
    """
    A file that goes with a message.

    One to send names a ``path``, read only when the message is handed to the provider. One that arrived holds
    its bytes in ``content`` and a ``filename`` already made safe to write to disk.
    """

    filename: str
    content_type: str = DEFAULT_CONTENT_TYPE
    path: Optional[str] = None
    content: Optional[bytes] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.filename, str) or not self.filename:
            raise MailThunderAttachmentException("an attachment needs a file name")
        if self.path is None and self.content is None:
            raise MailThunderAttachmentException(f"attachment {self.filename!r} needs a path or its content")

    @classmethod
    def from_path(cls, path: Union[str, "os.PathLike[str]"], filename: Optional[str] = None,
                  content_type: Optional[str] = None) -> Attachment:
        """
        An attachment to send.

        :param path: the file to attach
        :param filename: the name the recipient sees; the file's own name by default
        :param content_type: its MIME type; guessed from the name by default
        :return: the attachment (the file is not opened yet)
        """
        location = os.fspath(path)
        name = filename or os.path.basename(location)
        return cls(filename=name, content_type=content_type or guess_content_type(name), path=location)

    @classmethod
    def of(cls, source: AttachmentSource) -> Attachment:
        """
        :param source: an :class:`Attachment`, or the path of a file to attach
        :return: the attachment
        :raises MailThunderAttachmentException: ``source`` is neither
        """
        if isinstance(source, Attachment):
            return source
        if isinstance(source, (str, os.PathLike)):
            return cls.from_path(source)
        raise MailThunderAttachmentException(
            f"an attachment must be a path or an Attachment, got {type(source).__name__}")

    @property
    def size(self) -> int:
        """
        The attachment's size in bytes.

        :raises AttachmentNotFound: the file to send does not exist or is not a regular file
        """
        if self.content is not None:
            return len(self.content)
        if not os.path.isfile(self.path):
            raise AttachmentNotFound(self.path)
        return os.path.getsize(self.path)

    def read(self) -> bytes:
        """
        :return: the attachment's bytes
        :raises AttachmentNotFound: the file to send does not exist or cannot be read
        """
        if self.content is not None:
            return self.content
        try:
            with open(self.path, "rb") as attached_file:
                return attached_file.read()
        except OSError as error:
            raise AttachmentNotFound(self.path) from error

    def save(self, directory: Union[str, "os.PathLike[str]"]) -> str:
        """
        Write the attachment into ``directory`` under a name that cannot leave it.

        :param directory: an existing directory
        :return: the path written
        :raises MailThunderAttachmentException: the name would land outside ``directory``
        """
        root = os.path.abspath(os.fspath(directory))
        target = os.path.abspath(os.path.join(root, safe_filename(self.filename)))
        if os.path.commonpath([root, target]) != root:
            raise MailThunderAttachmentException(f"attachment {self.filename!r} would be written outside {root!r}")
        with open(target, "wb") as saved_file:
            saved_file.write(self.read())
        return target

    def describe(self) -> dict:
        """
        :return: the name, type and size, for logs and action records (never the content)
        """
        return {"filename": self.filename, "content_type": self.content_type, "size": self.size}
