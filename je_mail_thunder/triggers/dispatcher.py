"""
Who is told about which event: handlers subscribe to an event name, with a filter, and the dispatcher calls the
ones an event matches.
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass
from typing import Any, Callable, List, Tuple

from je_mail_thunder.core.events import ANY_EVENT, EVENT_NAMES, MailEvent
from je_mail_thunder.triggers.filter import MailFilter
from je_mail_thunder.utils.exception.exceptions import MailThunderTriggerException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

Handler = Callable[[MailEvent], Any]
_identifiers = itertools.count(1)


@dataclass(frozen=True)
class Subscription:
    """A handler, the event it listens for and the filter the event must pass."""

    identifier: int
    event: str
    handler: Handler
    mail_filter: MailFilter

    def describe(self) -> dict:
        """
        :return: the subscription as JSON-ready values (the handler by its name)
        """
        name = getattr(self.handler, "__qualname__", None) or type(self.handler).__name__
        return {"id": self.identifier, "event": self.event, "handler": name, "filter": self.mail_filter.describe()}


class EventDispatcher:
    """Calls the handlers subscribed to an event. Safe to share between threads."""

    def __init__(self) -> None:
        self._subscriptions: List[Subscription] = []
        self._lock = threading.Lock()

    def on(self, event: str, handler: Handler, mail_filter: Any = None) -> Subscription:
        """
        :param event: an event name (``core.events.EVENT_NAMES``), or ``"*"`` for every event
        :param handler: called with the :class:`MailEvent`
        :param mail_filter: what the event must match: a mapping of rules, a function or a :class:`MailFilter`
        :return: the subscription, to give to :meth:`off`
        :raises MailThunderTriggerException: the event name is unknown, or the handler cannot be called
        """
        if event != ANY_EVENT and event not in EVENT_NAMES:
            raise MailThunderTriggerException(f"unknown event {event!r}; the events are {list(EVENT_NAMES)}")
        if not callable(handler):
            raise MailThunderTriggerException("an event handler must be callable")
        subscription = Subscription(next(_identifiers), event, handler, MailFilter.of(mail_filter))
        with self._lock:
            self._subscriptions.append(subscription)
        return subscription

    def off(self, subscription: Subscription) -> bool:
        """
        :param subscription: what :meth:`on` returned
        :return: True when it was subscribed
        """
        with self._lock:
            if subscription in self._subscriptions:
                self._subscriptions.remove(subscription)
                return True
        return False

    @property
    def subscriptions(self) -> Tuple[Subscription, ...]:
        """The current subscriptions, in the order they were made."""
        with self._lock:
            return tuple(self._subscriptions)

    def emit(self, event: MailEvent) -> int:
        """
        Call every handler subscribed to the event whose filter it passes. A handler that raises is logged and
        does not stop the others, nor the operation that caused the event.

        :param event: what happened
        :return: how many handlers were called
        """
        called = 0
        for subscription in self.subscriptions:
            if subscription.event not in (event.name, ANY_EVENT):
                continue
            try:
                if not subscription.mail_filter.matches(event):
                    continue
                called += 1
                subscription.handler(event)
            except Exception as error:  # pylint: disable=broad-exception-caught  # reason: a handler is caller code
                mail_thunder_logger.error(
                    f"event_dispatcher, the handler of {event.name!r} failed: {repr(error)}")
        return called
