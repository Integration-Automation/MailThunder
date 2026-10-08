"""
How an account proves who it is, whatever the provider.

A mechanism overrides what it can do: :meth:`Authentication.login` for the SMTP and IMAP clients,
:meth:`Authentication.authorization` for HTTP APIs. Secrets never appear in a ``repr``, a log line or an exception
message from this package.
"""
from abc import ABC, abstractmethod

from je_mail_thunder.utils.exception.exceptions import MailThunderAuthenticationException


class Authentication(ABC):
    """One way of logging an account in."""

    def __init__(self, user: str) -> None:
        """
        :param user: the account's mail address
        :raises MailThunderAuthenticationException: there is no user
        """
        if not isinstance(user, str) or not user:
            raise MailThunderAuthenticationException("authentication needs the mail user")
        self.user = user

    @property
    @abstractmethod
    def mechanism(self) -> str:
        """The mechanism's name, for logs and error messages."""

    def login(self, client) -> None:
        """
        Log an SMTP or IMAP client in.

        :param client: a connected MailThunder SMTP or IMAP wrapper
        :raises MailThunderAuthenticationException: the mechanism has no mail server login
        """
        raise MailThunderAuthenticationException(
            f"{self.mechanism} authentication cannot log in {type(client).__name__}")

    def authorization(self) -> str:
        """
        :return: the value of the HTTP ``Authorization`` header
        :raises MailThunderAuthenticationException: the mechanism does not authorise HTTP requests
        """
        raise MailThunderAuthenticationException(f"{self.mechanism} authentication cannot authorise an HTTP request")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(user={self.user!r})"
