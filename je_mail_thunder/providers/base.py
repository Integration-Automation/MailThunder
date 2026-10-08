"""
What every mail provider offers, so the code that uses one does not depend on SMTP, IMAP or an HTTP API.

A provider is a :class:`MailSender`, a :class:`MailStore`, or both. Server errors reach the caller as
:class:`~je_mail_thunder.utils.exception.exceptions.MailThunderProviderException` or one of its subclasses.
"""
from abc import ABC, abstractmethod
from typing import Iterator, Optional

from je_mail_thunder.core.message import MailMessage

DEFAULT_FOLDER = "INBOX"


class MailProvider(ABC):
    """One way of reaching an account's mail. It holds a connection, so it is a context manager."""

    #: The provider's name, for logs and error messages.
    name = "provider"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def check(self) -> None:
        """
        Prove that the provider can do its work: reach its server and log in, without sending or reading mail.
        A provider with nothing to prove passes.

        :return: None
        :raises MailThunderException: the server cannot be reached, or refuses the login
        """

    @abstractmethod
    def close(self) -> None:
        """
        Close the connection, if there is one. The provider reconnects when it is used again.

        :return: None
        """


class MailSender(MailProvider):
    """A provider that sends mail."""

    @abstractmethod
    def send(self, message: MailMessage) -> None:
        """
        Send a message.

        :param message: a message that passed :func:`~je_mail_thunder.core.message.check_outgoing`
        :return: None
        :raises MailThunderSendException: the server did not take it for every recipient
        """


class MailStore(MailProvider):
    """A provider that reads and manages stored mail."""

    @abstractmethod
    def get_messages(self, folder: str = DEFAULT_FOLDER, limit: Optional[int] = None,
                     unread_only: bool = False, query: Optional[str] = None) -> Iterator[MailMessage]:
        """
        The messages of a folder, newest first, read one at a time.

        :param folder: the folder to read
        :param limit: stop after this many messages
        :param unread_only: skip messages that were already read
        :param query: a search in the provider's own syntax (IMAP ``SEARCH`` criteria, an API filter)
        :return: an iterator of messages
        """

    @abstractmethod
    def get_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> MailMessage:
        """
        :param message_id: a message's ``message_id``, as :meth:`get_messages` gave it
        :param folder: the folder it is in
        :return: the message
        :raises MailThunderProviderException: there is no such message
        """

    @abstractmethod
    def create_draft(self, message: MailMessage, folder: Optional[str] = None) -> Optional[str]:
        """
        Store a message as a draft instead of sending it.

        :param message: the draft
        :param folder: the drafts folder; the account's own by default
        :return: the draft's ``message_id`` when the server tells it, else ``None``
        """

    @abstractmethod
    def delete_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> None:
        """
        :param message_id: a message's ``message_id``, as :meth:`get_messages` gave it
        :param folder: the folder it is in
        :return: None
        """
