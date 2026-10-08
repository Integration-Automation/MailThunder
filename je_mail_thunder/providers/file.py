"""
Mail kept as ``.eml`` files in a directory instead of being sent: a provider for dry runs and tests.

``send`` writes into ``<directory>/Sent``, ``create_draft`` into ``<directory>/Drafts``, and the reading calls
list the files of a folder, so a message dropped into ``<directory>/INBOX`` is "received". Nothing leaves the
machine and no login is needed.
"""
from __future__ import annotations

import os
import re
import secrets
import time
from email import policy
from pathlib import Path
from typing import Iterator, Optional, Union

from je_mail_thunder.attachments.mime import safe_filename
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.core.rfc822 import parse_message, to_email_message
from je_mail_thunder.providers.base import DEFAULT_FOLDER, MailSender, MailStore
from je_mail_thunder.utils.exception.exceptions import MailThunderProviderException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

PROVIDER_NAME = "file"
#: Environment variable that names the directory of the registered ``file`` provider.
DIRECTORY_ENV = "MAIL_THUNDER_FILE_PROVIDER_DIR"
DEFAULT_DIRECTORY = "mail_outbox"
SENT_FOLDER = "Sent"
DRAFTS_FOLDER = "Drafts"
_SUFFIX = ".eml"
_MESSAGE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class FileProvider(MailSender, MailStore):
    """Stores messages as ``.eml`` files; the newest file of a folder is its newest message."""

    name = PROVIDER_NAME

    def __init__(self, directory: Optional[Union[str, "os.PathLike[str]"]] = None) -> None:
        """
        :param directory: where the folders are kept; ``$MAIL_THUNDER_FILE_PROVIDER_DIR``, else ``mail_outbox``
            under the working directory
        """
        self.directory = Path(directory or os.environ.get(DIRECTORY_ENV, "").strip() or DEFAULT_DIRECTORY)
        self._last_stamp = 0

    def close(self) -> None:
        """
        Nothing is kept open.

        :return: None
        """

    def check(self) -> None:
        """
        :return: None
        :raises MailThunderProviderException: the directory cannot be created
        """
        self._folder(SENT_FOLDER, create=True)

    def _folder(self, folder: str, create: bool = False) -> Path:
        if not isinstance(folder, str) or not folder.strip():
            raise MailThunderProviderException(f"invalid folder name {folder!r}")
        path = self.directory / safe_filename(folder)
        if create:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                raise MailThunderProviderException(f"the folder {str(path)!r} cannot be created: {error!r}") from error
        return path

    def _file(self, message_id: object, folder: str) -> Path:
        if not isinstance(message_id, str) or not _MESSAGE_ID.fullmatch(message_id) or ".." in message_id:
            raise MailThunderProviderException(f"a file provider message id is a file name, not {message_id!r}")
        path = self._folder(folder) / (message_id + _SUFFIX)
        if not path.is_file():
            raise MailThunderProviderException(f"no message {message_id} in the folder {folder!r}")
        return path

    def _store(self, message: MailMessage, folder: str) -> str:
        # Time first, so the names sort in the order the messages were stored. The clock can stand still
        # between two messages (about 16 ms on Windows), so a stamp is never reused by this provider.
        self._last_stamp = max(self._last_stamp + 1, time.time_ns())
        message_id = f"{self._last_stamp:020d}-{secrets.token_hex(4)}"
        target = self._folder(folder, create=True) / (message_id + _SUFFIX)
        try:
            with open(target, "wb") as stored:
                stored.write(to_email_message(message).as_bytes(policy=policy.SMTP))
        except OSError as error:
            raise MailThunderProviderException(
                f"the message cannot be written to {str(target)!r}: {error!r}") from error
        return message_id

    def send(self, message: MailMessage) -> None:
        """
        Write the message into the ``Sent`` folder instead of sending it.

        :param message: a message that passed :func:`~je_mail_thunder.core.message.check_outgoing`
        :return: None
        :raises MailThunderProviderException: the file cannot be written
        """
        mail_thunder_logger.info(f"file provider, send: kept as {self._store(message, SENT_FOLDER)}")

    def create_draft(self, message: MailMessage, folder: Optional[str] = None) -> Optional[str]:
        """
        :param message: the draft
        :param folder: the folder to keep it in; ``Drafts`` by default
        :return: the draft's id
        """
        return self._store(message, folder or DRAFTS_FOLDER)

    def get_messages(self, folder: str = DEFAULT_FOLDER, limit: Optional[int] = None,
                     unread_only: bool = False, query: Optional[str] = None) -> Iterator[MailMessage]:
        """
        The messages of a folder, newest first.

        :param folder: the folder to read
        :param limit: stop after this many messages
        :param unread_only: has no effect: files have no read state
        :param query: text that must be in the subject (any case)
        :return: an iterator of messages whose ``message_id`` is the file's name without ``.eml``
        """
        mail_thunder_logger.info(f"file provider, get_messages: folder {folder!r}, unread_only {unread_only}")
        directory = self._folder(folder)
        names = []
        if directory.is_dir():
            # A file whose name is not a message id (a space, a dot in front) is not listed.
            names = sorted((entry.name for entry in directory.glob("*" + _SUFFIX)
                            if _MESSAGE_ID.fullmatch(entry.name[:-len(_SUFFIX)])), reverse=True)
        count = 0
        for name in names:
            if limit is not None and count >= limit:
                return
            message = self.get_message(name[:-len(_SUFFIX)], folder)
            if query and query.casefold() not in message.subject.casefold():
                continue
            count += 1
            yield message

    def get_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> MailMessage:
        """
        :param message_id: the file's name without ``.eml``
        :param folder: the folder it is in
        :return: the message
        :raises MailThunderProviderException: the folder holds no such message
        """
        path = self._file(message_id, folder)
        with open(path, "rb") as stored:
            return parse_message(stored.read(), message_id)

    def delete_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> None:
        """
        :param message_id: the file's name without ``.eml``
        :param folder: the folder it is in
        :return: None
        :raises MailThunderProviderException: the folder holds no such message
        """
        self._file(message_id, folder).unlink()
