"""
Trigger backends for an IMAP mailbox: polling that asks only for UIDs above the last one seen, and IDLE, where
the server says when something arrived instead of being asked.
"""
from __future__ import annotations

from typing import List, Optional

from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers.imap import IMAPProvider
from je_mail_thunder.triggers.polling import PollingBackend
from je_mail_thunder.utils.exception.exceptions import MailThunderException, MailThunderTriggerException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

# Servers end an IDLE after about half an hour; a shorter one also bounds how late a missed notice is caught.
DEFAULT_IDLE_SECONDS = 300.0


class IMAPPollingBackend(PollingBackend):
    """Polling that lets the server do the filtering: after the first look it searches ``UID <last + 1>:*``."""

    name = "imap-polling"

    def __init__(self, store: IMAPProvider, *arguments, **options) -> None:
        """
        :param store: the IMAP provider to ask
        :param arguments: as :class:`PollingBackend` takes them
        :param options: as :class:`PollingBackend` takes them
        :raises MailThunderTriggerException: the store is not an IMAP provider
        """
        if not isinstance(store, IMAPProvider):
            raise MailThunderTriggerException(f"an IMAP trigger needs an IMAPProvider, got {type(store).__name__}")
        super().__init__(store, *arguments, **options)
        self._last_uid: Optional[int] = None

    def _new_messages(self) -> List[MailMessage]:
        if self._last_uid is None:
            fresh = super()._new_messages()
        else:
            # "n:*" always answers with the newest message, even when its UID is below n.
            found = self.store.get_messages(self.folder, query=f"UID {self._last_uid + 1}:*")
            fresh = [message for message in found if int(message.message_id) > self._last_uid]
            fresh.reverse()
        self._last_uid = max([self._last_uid or 0] + [int(message.message_id) for message in fresh])
        return fresh


class IMAPIdleBackend(IMAPPollingBackend):
    """
    Waits in IMAP ``IDLE`` between two looks, so new mail is reported when the server announces it. It needs a
    connection of its own: nothing else can use a connection that is idling.
    """

    name = "imap-idle"

    def __init__(self, store: IMAPProvider, *arguments, **options) -> None:
        """
        :param store: an IMAP provider used by nothing else
        :param arguments: as :class:`PollingBackend` takes them
        :param options: as :class:`PollingBackend` takes them; ``interval`` is the longest one IDLE lasts
            (300 seconds by default)
        """
        options.setdefault("interval", DEFAULT_IDLE_SECONDS)
        super().__init__(store, *arguments, **options)

    def wait(self, seconds: float) -> None:
        """
        Idle until the server reports a change, the time is up or the backend is stopped. A server without
        ``IDLE``, or a failure while idling, falls back to sleeping.

        :param seconds: the longest to wait
        :return: None
        """
        try:
            with self._lock:
                self.store.idle(self.folder, timeout=seconds, should_stop=self._stopping.is_set)
        except MailThunderException as error:
            mail_thunder_logger.error(f"{self.name} trigger, idle failed: {repr(error)}")
            super().wait(min(seconds, self.retry_seconds))
