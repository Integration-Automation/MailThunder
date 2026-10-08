"""
The trigger backend every provider can use: ask the store for its newest messages and report the ones that were
not there at the last look.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from je_mail_thunder.core.events import ATTACHMENT_RECEIVED, MESSAGE_RECEIVED, MailEvent
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers.base import DEFAULT_FOLDER, MailStore
from je_mail_thunder.triggers.trigger import MailTriggerBackend
from je_mail_thunder.utils.exception.exceptions import MailThunderTriggerException

# How many message ids a backend remembers as already reported.
SEEN_LIMIT = 2000
DEFAULT_BATCH_LIMIT = 50


class PollingBackend(MailTriggerBackend):  # pylint: disable=too-many-instance-attributes  # reason: its settings
    """
    Emits ``message_received`` (and ``attachment_received`` for each attachment) for the messages that arrived
    since the last look. The first look only notes what is already there, unless ``include_existing`` is set.
    """

    name = "polling"

    def __init__(self, store: MailStore, folder: str = DEFAULT_FOLDER, interval: float = 60.0,
                 include_existing: bool = False, batch_limit: int = DEFAULT_BATCH_LIMIT,
                 lock: Optional[threading.RLock] = None) -> None:
        """
        :param store: the provider to ask
        :param folder: the folder to watch
        :param interval: seconds between two looks while the backend runs
        :param include_existing: also report the messages found at the first look
        :param batch_limit: the most messages one look reads; more than that arriving between two looks are missed
        :param lock: held while the store is asked, when the store is shared with other callers
        :raises MailThunderTriggerException: the store cannot read mail, or the limit is not a positive number
        """
        super().__init__(interval)
        if not isinstance(store, MailStore):
            raise MailThunderTriggerException(f"a polling trigger needs a MailStore, got {type(store).__name__}")
        if isinstance(batch_limit, bool) or not isinstance(batch_limit, int) or batch_limit <= 0:
            raise MailThunderTriggerException("a trigger's batch limit is a positive whole number")
        self.store = store
        self.folder = folder
        self._include_existing = include_existing
        self._batch_limit = batch_limit
        self._lock = lock if lock is not None else threading.RLock()
        self._seen: Deque[Optional[str]] = deque(maxlen=SEEN_LIMIT)
        self._primed = False
        #: True when the store was made for this backend, which then closes it when it stops.
        self.owns_store = False

    def _new_messages(self) -> List[MailMessage]:
        """The messages that were not there at the last look, oldest first."""
        fresh: List[MailMessage] = []
        for message in self.store.get_messages(self.folder, limit=self._batch_limit):
            if message.message_id in self._seen:
                break
            fresh.append(message)
        fresh.reverse()
        return fresh

    def _report(self, message: MailMessage) -> int:
        self._emit(MailEvent(MESSAGE_RECEIVED, message=message, provider=self.store.name, folder=self.folder))
        for attachment in message.attachments:
            self._emit(MailEvent(ATTACHMENT_RECEIVED, message=message, attachment=attachment,
                                 provider=self.store.name, folder=self.folder))
        return 1 + len(message.attachments)

    def poll(self) -> int:
        """
        Look once.

        :return: how many events were emitted
        :raises MailThunderProviderException: the store could not be read
        """
        with self._lock:
            fresh = self._new_messages()
        report = self._primed or self._include_existing
        self._primed = True
        emitted = 0
        for message in fresh:
            self._seen.append(message.message_id)
            if report:
                emitted += self._report(message)
        return emitted

    def close(self) -> None:
        """
        Close the store when it was made for this backend.

        :return: None
        """
        if self.owns_store:
            self.store.close()

    def describe(self) -> dict:
        """
        :return: the backend's name, folder, provider, interval and state
        """
        return {**super().describe(), "folder": self.folder, "provider": self.store.name}
