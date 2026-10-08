"""
The provider-agnostic mail API: one :class:`Mail` sends, reads, drafts and deletes mail, whatever the account's
provider is.
"""
import threading
from contextlib import contextmanager
from dataclasses import replace
from typing import Iterator, Optional, Sequence, Tuple

from je_mail_thunder.attachments.policy import DEFAULT_ATTACHMENT_POLICY, AttachmentPolicy
from je_mail_thunder.attachments.validator import validate_attachments
from je_mail_thunder.auth.base import Authentication
from je_mail_thunder.auth.oauth2 import OAuth2Auth
from je_mail_thunder.core.account import DEFAULT_PROVIDER, MailAccount, default_account
from je_mail_thunder.core.message import MailMessage, check_outgoing, message_from_fields
from je_mail_thunder.providers.base import DEFAULT_FOLDER, MailProvider, MailSender, MailStore
from je_mail_thunder.providers.registry import create_providers
from je_mail_thunder.utils.exception.exceptions import MailThunderException, MailThunderProviderException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger


@contextmanager
def _logged(operation: str) -> Iterator[None]:
    """Log the operation, and its failure before the caller sees it."""
    mail_thunder_logger.info(operation)
    try:
        yield
    except MailThunderException as error:
        mail_thunder_logger.error(f"{operation}, failed: {repr(error)}")
        raise


def _account_for(provider: Optional[str], auth: Optional[Authentication]) -> MailAccount:
    """The account a provider name and a login describe; OAuth2 settings that name a provider choose it."""
    if provider is None:
        preset = auth.settings.preset if isinstance(auth, OAuth2Auth) and auth.settings.token_url is None else None
        provider = preset.name if preset is not None else DEFAULT_PROVIDER
    return MailAccount(provider=provider, auth=auth)


class Mail:
    """
    An account's mail, without the caller knowing whether SMTP, IMAP or an HTTP API is behind it.

    Nothing connects until the first operation, and the connections are kept for the ones that follow. It is a
    context manager; one instance serialises the calls of the threads that share it.
    """

    def __init__(self, provider: Optional[str] = None, auth: Optional[Authentication] = None,
                 account: Optional[MailAccount] = None, policy: Optional[AttachmentPolicy] = None,
                 providers: Optional[Sequence[MailProvider]] = None) -> None:
        """
        :param provider: a registered provider name (``"google"``, ``"microsoft"``, ...); without one, the
            provider the OAuth2 settings name (those of ``auth``, else of the content file or the environment),
            else Gmail
        :param auth: how the account logs in; by default what the content file or the environment holds
        :param account: the whole account, instead of ``provider`` and ``auth``
        :param policy: what attachments are checked against before sending; 25 MiB of any type by default
        :param providers: ready providers to use instead of the ones the account's provider name stands for
        :raises MailThunderProviderException: ``account`` is given together with ``provider`` or ``auth``
        """
        if account is not None and (provider is not None or auth is not None):
            raise MailThunderProviderException("give Mail an account, or a provider and auth, not both")
        if account is None and (provider is not None or auth is not None):
            account = _account_for(provider, auth)
        self._account = account
        self._providers: Optional[Tuple[MailProvider, ...]] = None if providers is None else tuple(providers)
        self._uses_given_providers = providers is not None
        self.policy = policy if policy is not None else DEFAULT_ATTACHMENT_POLICY
        self._lock = threading.RLock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def account(self) -> Optional[MailAccount]:
        """
        The account in use; the default one is worked out from the content file or the environment on first use.
        ``None`` only for a ``Mail`` built from ready providers without an account.
        """
        if self._account is None and not self._uses_given_providers:
            self._account = default_account()
        return self._account

    @property
    def providers(self) -> Tuple[MailProvider, ...]:
        """The providers in use, built (not connected) on first use."""
        if self._providers is None:
            self._providers = create_providers(self.account)
        return self._providers

    def _provider(self, role: type, operation: str):
        for provider in self.providers:
            if isinstance(provider, role):
                return provider
        raise MailThunderProviderException(f"no configured provider can {operation}")

    def _outgoing(self, message: Optional[MailMessage], message_fields: dict) -> MailMessage:
        """The message to send or draft: complete, valid, and within the attachment policy."""
        if message is not None and message_fields:
            raise MailThunderProviderException("give a MailMessage or message fields, not both")
        if message is None:
            message = message_from_fields(message_fields)
        if not isinstance(message, MailMessage):
            raise MailThunderProviderException(f"expected a MailMessage, got {type(message).__name__}")
        if message.sender is None and self.account is not None:
            message = replace(message, sender=self.account.authentication().user)
        check_outgoing(message)
        validate_attachments(message.attachments, self.policy)
        return message

    def send(self, message: Optional[MailMessage] = None, **message_fields) -> MailMessage:
        """
        Send a message: ``mail.send(to="a@example.com", subject="Report", text="...", attachments=["r.pdf"])``.

        :param message: a ready :class:`MailMessage`, or
        :param message_fields: its fields: ``to``, ``cc``, ``bcc``, ``subject``, ``text``, ``html``,
            ``attachments``, ``sender``, ``reply_to``, ``headers``
        :return: the message as it was sent (the account's user as ``sender`` when none was given)
        :raises MailThunderMessageException: no recipient, or an address, subject or header that is not valid
        :raises MailThunderAttachmentException: an attachment is missing or breaks the policy
        :raises MailThunderProviderException: the provider could not connect, log in or send
        """
        with _logged("mail_send"), self._lock:
            message = self._outgoing(message, message_fields)
            self._provider(MailSender, "send mail").send(message)
            return message

    def create_draft(self, message: Optional[MailMessage] = None, folder: Optional[str] = None,
                     **message_fields) -> Optional[str]:
        """
        Store a message as a draft instead of sending it. It is checked exactly like a message to send.

        :param message: a ready :class:`MailMessage`, or
        :param message_fields: its fields, as :meth:`send` takes them
        :param folder: the drafts folder; the account's own by default
        :return: the draft's ``message_id`` when the provider reports it, else ``None``
        :raises MailThunderException: as :meth:`send`
        """
        with _logged("mail_create_draft"), self._lock:
            message = self._outgoing(message, message_fields)
            return self._provider(MailStore, "store drafts").create_draft(message, folder)

    def get_messages(self, folder: str = DEFAULT_FOLDER, limit: Optional[int] = None,
                     unread_only: bool = False, query: Optional[str] = None) -> Iterator[MailMessage]:
        """
        The messages of a folder, newest first. They are fetched one at a time as the iterator is read, so a
        large mailbox is never held in memory; reading a message does not mark it as read.

        :param folder: the folder to read
        :param limit: stop after this many messages
        :param unread_only: skip messages that were already read
        :param query: a search in the provider's own syntax (IMAP ``SEARCH`` criteria)
        :return: an iterator of :class:`MailMessage`
        :raises MailThunderProviderException: ``limit`` is not a whole number of at least 0, or the provider
            could not connect, log in or read
        """
        with _logged(f"mail_get_messages, folder: {folder!r}, limit: {limit}"):
            if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
                raise MailThunderProviderException("limit must be a whole number of at least 0")
        return self._read(folder, limit, unread_only, query)

    def _read(self, folder: str, limit: Optional[int], unread_only: bool,
              query: Optional[str]) -> Iterator[MailMessage]:
        """The iterator :meth:`get_messages` returns; the provider is first asked when it is read."""
        with _logged("mail_get_messages, reading"), self._lock:
            yield from self._provider(MailStore, "read mail").get_messages(folder, limit, unread_only, query)

    def get_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> MailMessage:
        """
        :param message_id: a message's ``message_id``, as :meth:`get_messages` gave it
        :param folder: the folder it is in
        :return: the message
        :raises MailThunderProviderException: there is no such message, or the provider failed
        """
        with _logged(f"mail_get_message, folder: {folder!r}"), self._lock:
            return self._provider(MailStore, "read mail").get_message(message_id, folder)

    def delete_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> None:
        """
        :param message_id: a message's ``message_id``, as :meth:`get_messages` gave it
        :param folder: the folder it is in
        :return: None
        :raises MailThunderProviderException: there is no such message, or the provider failed
        """
        with _logged(f"mail_delete_message, folder: {folder!r}"), self._lock:
            self._provider(MailStore, "delete mail").delete_message(message_id, folder)

    def close(self) -> None:
        """
        Close the providers' connections. The next operation connects again.

        :return: None
        """
        with _logged("mail_close"), self._lock:
            for provider in self._providers or ():
                provider.close()


# The Mail the MT_mail_* actions use: the account of the content file or the environment. Building it reads
# nothing and connects to nothing.
mail_instance = Mail()
