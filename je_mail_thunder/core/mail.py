"""
The provider-agnostic mail API: one :class:`Mail` sends, reads, drafts and deletes mail, whatever the account's
provider is.
"""
import threading
from contextlib import contextmanager
from dataclasses import replace
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence, Tuple, Union

from je_mail_thunder.attachments.policy import DEFAULT_ATTACHMENT_POLICY, AttachmentPolicy
from je_mail_thunder.attachments.validator import validate_attachments
from je_mail_thunder.auth.base import Authentication
from je_mail_thunder.auth.oauth2 import OAuth2Auth
from je_mail_thunder.core.account import DEFAULT_PROVIDER, MailAccount, default_account
from je_mail_thunder.core.events import MESSAGE_SENT, MailEvent, failure_events
from je_mail_thunder.core.message import MailMessage, check_outgoing, message_from_fields
from je_mail_thunder.providers.base import DEFAULT_FOLDER, MailProvider, MailSender, MailStore
from je_mail_thunder.providers.registry import create_providers
from je_mail_thunder.templates.loader import TemplateLoader
from je_mail_thunder.templates.template import MailTemplate, RenderedTemplate
from je_mail_thunder.triggers.dispatcher import EventDispatcher
from je_mail_thunder.triggers.factory import create_backend
from je_mail_thunder.triggers.trigger import MailTriggerBackend, TriggerManager
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderException,
    MailThunderProviderException,
    MailThunderTriggerException,
)
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger


def _account_for(provider: Optional[str], auth: Optional[Authentication]) -> MailAccount:
    """The account a provider name and a login describe; OAuth2 settings that name a provider choose it."""
    if provider is None:
        preset = auth.settings.preset if isinstance(auth, OAuth2Auth) and auth.settings.token_url is None else None
        provider = preset.name if preset is not None else DEFAULT_PROVIDER
    return MailAccount(provider=provider, auth=auth)


class Mail:  # pylint: disable=too-many-instance-attributes  # reason: the parts of the API hang off it by name
    """
    An account's mail, without the caller knowing whether SMTP, IMAP or an HTTP API is behind it.

    Nothing connects until the first operation, and the connections are kept for the ones that follow. It is a
    context manager; one instance serialises the calls of the threads that share it.

    ``events`` is the dispatcher its events go through (:meth:`on` subscribes to it) and ``triggers`` holds the
    backends that watch for new mail (:meth:`watch` adds one).
    """

    def __init__(self, provider: Optional[str] = None, auth: Optional[Authentication] = None,
                 account: Optional[MailAccount] = None, policy: Optional[AttachmentPolicy] = None,
                 providers: Optional[Sequence[MailProvider]] = None,
                 templates: Optional[TemplateLoader] = None) -> None:
        """
        :param provider: a registered provider name (``"google"``, ``"microsoft"``, ...); without one, the
            provider the OAuth2 settings name (those of ``auth``, else of the content file or the environment),
            else Gmail
        :param auth: how the account logs in; by default what the content file or the environment holds
        :param account: the whole account, instead of ``provider`` and ``auth``
        :param policy: what attachments are checked against before sending; 25 MiB of any type by default
        :param providers: ready providers to use instead of the ones the account's provider name stands for
        :param templates: where ``send(template=...)`` finds its templates; by default the project's
            ``mail/templates`` directory, then the shared one
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
        self.templates = templates if templates is not None else TemplateLoader()
        self.events = EventDispatcher()
        self.triggers = TriggerManager(self.events.emit)
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

    @contextmanager
    def _operation(self, name: str, sending: bool = False) -> Iterator[dict]:
        """
        Log the operation; when it fails, log that, emit the events the failure stands for, and raise it. The
        operation notes the ``message`` and the ``provider`` it got to in the dict it is given.
        """
        mail_thunder_logger.info(name)
        attempt: dict = {}
        try:
            yield attempt
        except MailThunderException as error:
            mail_thunder_logger.error(f"{name}, failed: {repr(error)}")
            for event in failure_events(error, attempt.get("message"), attempt.get("provider", ""), sending):
                self.events.emit(event)
            raise

    def on(self, event: str, handler: Optional[Callable[[MailEvent], Any]] = None, **options):
        """
        Call a handler when an event happens:
        ``mail.on("message_received", handle, filter={"subject": "[TEST]"})``. Without a handler it is a
        decorator: ``@mail.on("message_failed")``.

        :param event: ``message_received``, ``message_sent``, ``message_failed``, ``attachment_received``,
            ``attachment_rejected``, ``authentication_failed``, ``connection_failed``, or ``"*"`` for all
        :param handler: called with the :class:`~je_mail_thunder.core.events.MailEvent`
        :param options: ``filter``: a mapping of filter rules (``sender``, ``recipient``, ``subject``, ``body``,
            ``has_attachments``, ``attachment_type``, ``since``, ``until``, ``metadata``), a function of the
            event, or a :class:`~je_mail_thunder.triggers.filter.MailFilter`
        :return: the subscription (``mail.events.off(subscription)`` ends it), or the decorator
        :raises MailThunderTriggerException: the event or a filter rule is unknown
        """
        unknown = sorted(set(options) - {"filter"})
        if unknown:
            raise MailThunderTriggerException(f"unknown options {unknown}; on() takes a filter")
        if handler is not None:
            return self.events.on(event, handler, options.get("filter"))

        def subscribe(function):
            self.events.on(event, function, options.get("filter"))
            return function

        return subscribe

    def _watch_store(self) -> Tuple[MailStore, bool]:
        """A store for a trigger: one with a connection of its own when the account can provide it."""
        if not self._uses_given_providers and self.account is not None:
            for provider in create_providers(self.account):
                if isinstance(provider, MailStore):
                    return provider, True
        return self._provider(MailStore, "read mail"), False

    def watch(self, folder: str = DEFAULT_FOLDER, idle: bool = False, start: bool = True,
              **options) -> MailTriggerBackend:
        """
        Watch a folder: every new message becomes a ``message_received`` event, and each of its attachments an
        ``attachment_received`` event. The mail that is already there is not reported.

        :param folder: the folder to watch
        :param idle: let the server announce new mail (IMAP ``IDLE``) instead of asking at intervals
        :param start: watch on a background thread from now on; with False, ``mail.triggers.poll()`` looks once
        :param options: ``interval`` (seconds between two looks, 60 by default), ``include_existing`` (also
            report what is already there) and ``batch_limit`` (messages read per look, 50 by default)
        :return: the trigger backend, also kept in ``triggers``
        :raises MailThunderTriggerException: ``idle`` is asked where the watcher cannot have its own connection
        """
        with self._operation("mail_watch"):
            store, owned = self._watch_store()
            if not owned:
                if idle:
                    raise MailThunderTriggerException("idle needs a connection of its own: give Mail an account")
                options["lock"] = self._lock
            backend = create_backend(store, folder, idle, **options)
            backend.owns_store = owned
            self.triggers.add(backend)
            if start:
                backend.start()
            return backend

    def render(self, template: Union[str, MailTemplate], context: Optional[Mapping[str, Any]] = None
               ) -> RenderedTemplate:
        """
        Render a template without sending anything, to see what ``send(template=...)`` would send.

        :param template: a template's name, looked up in ``templates``, or a :class:`MailTemplate`
        :param context: the values for this mail
        :return: the rendered subject, text and HTML
        :raises MailThunderTemplateException: the template is not found, not valid, or the context lacks a variable
        """
        with self._operation("mail_render"):
            loaded = template if isinstance(template, MailTemplate) else self.templates.load(template)
            return loaded.render(context)

    def _templated(self, message_fields: dict) -> dict:
        """Message fields with ``template`` and ``context`` replaced by what the template renders."""
        fields = dict(message_fields)
        template, context = fields.pop("template", None), fields.pop("context", None)
        if template is None:
            if context is not None:
                raise MailThunderProviderException("a context needs the template it is for")
            return fields
        for part, rendered in self.render(template, context).to_dict().items():
            if rendered is not None:
                # A field given beside the template wins over what the template renders.
                fields.setdefault(part, rendered)
        return fields

    def _outgoing(self, message: Optional[MailMessage], message_fields: dict) -> MailMessage:
        """The message to send or draft: complete, valid, and within the attachment policy."""
        if message is not None and message_fields:
            raise MailThunderProviderException("give a MailMessage or message fields, not both")
        message_fields = self._templated(message_fields)
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
            ``attachments``, ``sender``, ``reply_to``, ``headers``; or ``template`` (a name or a
            :class:`MailTemplate`) and ``context``, which render the subject and the bodies
        :return: the message as it was sent (the account's user as ``sender`` when none was given)
        :raises MailThunderMessageException: no recipient, or an address, subject or header that is not valid
        :raises MailThunderAttachmentException: an attachment is missing or breaks the policy
        :raises MailThunderTemplateException: the template is not found or cannot be rendered with the context
        :raises MailThunderProviderException: the provider could not connect, log in or send
        """
        with self._operation("mail_send", sending=True) as attempt:
            with self._lock:
                message = attempt["message"] = self._outgoing(message, message_fields)
                sender = self._provider(MailSender, "send mail")
                attempt["provider"] = sender.name
                sender.send(message)
        self.events.emit(MailEvent(MESSAGE_SENT, message=message, provider=sender.name))
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
        with self._operation("mail_create_draft", sending=True) as attempt:
            with self._lock:
                message = attempt["message"] = self._outgoing(message, message_fields)
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
        with self._operation(f"mail_get_messages, folder: {folder!r}, limit: {limit}"):
            if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
                raise MailThunderProviderException("limit must be a whole number of at least 0")
        return self._read(folder, limit, unread_only, query)

    def _read(self, folder: str, limit: Optional[int], unread_only: bool,
              query: Optional[str]) -> Iterator[MailMessage]:
        """The iterator :meth:`get_messages` returns; the provider is first asked when it is read."""
        with self._operation("mail_get_messages, reading"), self._lock:
            yield from self._provider(MailStore, "read mail").get_messages(folder, limit, unread_only, query)

    def get_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> MailMessage:
        """
        :param message_id: a message's ``message_id``, as :meth:`get_messages` gave it
        :param folder: the folder it is in
        :return: the message
        :raises MailThunderProviderException: there is no such message, or the provider failed
        """
        with self._operation(f"mail_get_message, folder: {folder!r}"), self._lock:
            return self._provider(MailStore, "read mail").get_message(message_id, folder)

    def delete_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> None:
        """
        :param message_id: a message's ``message_id``, as :meth:`get_messages` gave it
        :param folder: the folder it is in
        :return: None
        :raises MailThunderProviderException: there is no such message, or the provider failed
        """
        with self._operation(f"mail_delete_message, folder: {folder!r}"), self._lock:
            self._provider(MailStore, "delete mail").delete_message(message_id, folder)

    def close(self) -> None:
        """
        Stop the triggers and close the providers' connections. The next operation connects again.

        :return: None
        """
        self.triggers.stop()
        with self._operation("mail_close"), self._lock:
            for provider in self._providers or ():
                provider.close()


# The Mail the MT_mail_* actions use: the account of the content file or the environment. Building it reads
# nothing and connects to nothing.
mail_instance = Mail()
