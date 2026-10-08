"""
The connection of a provider that works through one of MailThunder's SMTP or IMAP wrappers.
"""
import time
from abc import abstractmethod
from typing import Callable, Optional, Tuple, Type

from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.providers.base import MailProvider
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderAuthenticationException,
    MailThunderConnectionException,
    MailThunderException,
    MailThunderProviderException,
)
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

# A connection idle for longer is asked for a sign of life before it is used: servers drop idle connections.
IDLE_CHECK_SECONDS = 30.0
# How long one answer from the server is waited for, so an automation run cannot hang on a silent server.
SOCKET_TIMEOUT_SECONDS = 60.0


class WrapperProvider(MailProvider):  # pylint: disable=too-few-public-methods  # reason: subclasses add them
    """
    A provider whose server is reached through a MailThunder wrapper.

    The connection is opened and logged in when first used, kept for the calls that follow, and replaced when
    the server dropped it while it sat idle. A provider given a client that is already connected (a wrapper its
    owner logged in) uses it as it is and never closes it.
    """

    #: Everything the wrapper raises for a server or network failure.
    _server_errors: Tuple[Type[Exception], ...] = (OSError,)

    def __init__(self, account: Optional[MailAccount] = None, client=None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        """
        :param account: whose mail, on which servers; needed unless ``client`` is given
        :param client: a wrapper that is already connected and logged in, used instead of connecting
        :param clock: the clock idle time is measured on
        :raises MailThunderProviderException: neither an account nor a client is given
        """
        if account is None and client is None:
            raise MailThunderProviderException(f"the {self.name} provider needs an account or a connected client")
        self._account = account
        self._client = client
        self._adopted = client is not None
        self._clock = clock
        self._used_at = clock()

    @abstractmethod
    def _connect(self):
        """Open a connection and return its wrapper, not logged in yet."""

    @abstractmethod
    def _ping(self, client) -> None:
        """Ask the server for a sign of life; raise one of ``_server_errors`` when there is none."""

    @abstractmethod
    def _disconnect(self, client, alive: bool) -> None:
        """End the session with the server; with ``alive`` False only the socket is left to close."""

    @abstractmethod
    def _is_lost(self, error: Exception) -> bool:
        """True when ``error`` means the connection is gone, False when the server answered with a refusal."""

    def _failure(self, action: str, error: Exception, refusal: Type[MailThunderException]) -> MailThunderException:
        """The exception to raise for a wrapper error; a lost connection is also forgotten."""
        if self._is_lost(error):
            self._drop(alive=False)
            return MailThunderConnectionException(f"the {self.name} connection was lost while {action}: {error!r}")
        return refusal(f"the {self.name} server refused {action}: {error!r}")

    def _drop(self, alive: bool = True) -> None:
        """Forget the connection; one this provider opened is closed, without a goodbye when it is dead."""
        if self._adopted or self._client is None:
            return
        client, self._client = self._client, None
        try:
            self._disconnect(client, alive)
        except self._server_errors as error:
            mail_thunder_logger.info(f"{self.name} provider, closing the connection: {error!r}")

    def _open(self) -> None:
        """Connect and log in; without credentials nothing is sent to the server."""
        authentication = self._account.authentication()
        try:
            self._client = self._connect()
        except self._server_errors as error:
            raise MailThunderConnectionException(f"cannot connect to the {self.name} server: {error!r}") from error
        connection = getattr(self._client, "sock", None)
        if connection is not None:
            connection.settimeout(SOCKET_TIMEOUT_SECONDS)
        try:
            authentication.login(self._client)
        except self._server_errors as error:
            failure = self._failure("the login", error, MailThunderAuthenticationException)
            self._drop()
            raise failure from error
        except Exception:
            # Whatever stopped the login, a connection that is not logged in is not kept for the next call.
            self._drop()
            raise
        mail_thunder_logger.info(f"{self.name} provider, logged in with {authentication.mechanism}")

    def _stale(self) -> bool:
        """True when a connection this provider opened sat idle and no longer answers."""
        if self._adopted or self._clock() - self._used_at < IDLE_CHECK_SECONDS:
            return False
        try:
            self._ping(self._client)
        except self._server_errors:
            return True
        return False

    def _live_client(self):
        """
        :return: the wrapper to talk to the server with, connected and logged in
        :raises MailThunderConnectionException: the server cannot be reached
        :raises MailThunderAuthenticationException: there are no credentials, or the server refused them
        """
        if self._client is not None and self._stale():
            mail_thunder_logger.info(f"{self.name} provider, the idle connection was dropped: reconnecting")
            self._drop(alive=False)
        if self._client is None:
            self._open()
        self._used_at = self._clock()
        return self._client

    def check(self) -> None:
        """
        Connect and log in, or prove that the connection that is open still answers.

        :return: None
        :raises MailThunderConnectionException: the server cannot be reached
        :raises MailThunderAuthenticationException: there are no credentials, or the server refused them
        """
        mail_thunder_logger.info(f"{self.name} provider, check")
        self._live_client()

    def close(self) -> None:
        """
        Close the connection this provider opened; a client it was given stays with its owner.

        :return: None
        """
        mail_thunder_logger.info(f"{self.name} provider, close")
        self._drop()
