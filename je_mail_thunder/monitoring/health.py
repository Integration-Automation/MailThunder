"""
Provider health: whether each provider is doing its work, worked out from the mail events and, on request, from
asking the provider to connect.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from je_mail_thunder.core.events import (
    ANY_EVENT,
    AUTHENTICATION_FAILED,
    CONNECTION_FAILED,
    MESSAGE_FAILED,
    MESSAGE_RECEIVED,
    MESSAGE_SENT,
    MailEvent,
)
from je_mail_thunder.providers.base import MailProvider
from je_mail_thunder.triggers.dispatcher import EventDispatcher, Subscription
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderException,
    MailThunderProviderException,
    MailThunderSendException,
)

UNKNOWN, HEALTHY, DEGRADED, DOWN = "unknown", "healthy", "degraded", "down"
DEFAULT_FAILURE_THRESHOLD = 3


@dataclass
class _Record:
    """What is known about one provider."""

    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_error: str = ""


def _is_provider_failure(event: MailEvent) -> bool:
    """
    A failure of the provider itself. A refused attachment or a message without a recipient is the caller's
    mistake, and a failed send whose reason already arrived as its own event is not counted twice.
    """
    if event.name in (AUTHENTICATION_FAILED, CONNECTION_FAILED):
        return True
    return event.name == MESSAGE_FAILED and isinstance(event.error, MailThunderSendException)


class ProviderHealth:
    """
    Counts what each provider did and how it ended. A provider is ``healthy`` after a success, ``degraded``
    after a failure, ``down`` after ``failure_threshold`` failures in a row, and ``unknown`` before anything
    happened. Safe to share between threads.
    """

    def __init__(self, failure_threshold: int = DEFAULT_FAILURE_THRESHOLD) -> None:
        """
        :param failure_threshold: failures in a row after which a provider counts as down
        """
        self._threshold = max(1, int(failure_threshold))
        self._records: Dict[str, _Record] = {}
        self._lock = threading.Lock()

    def attach(self, dispatcher: EventDispatcher) -> Subscription:
        """
        Follow the events of a dispatcher: ``health.attach(mail.events)``.

        :param dispatcher: a :class:`~je_mail_thunder.core.mail.Mail`'s ``events``
        :return: the subscription
        """
        return dispatcher.on(ANY_EVENT, self.record)

    def _note(self, provider: str, error: Optional[BaseException], moment: datetime) -> None:
        with self._lock:
            record = self._records.setdefault(provider, _Record())
            if error is None:
                record.successes += 1
                record.consecutive_failures = 0
                record.last_success = moment
            else:
                record.failures += 1
                record.consecutive_failures += 1
                record.last_failure = moment
                record.last_error = f"{type(error).__name__}: {error}"

    def record(self, event: MailEvent) -> None:
        """
        Take one event into account. Events without a provider name, and failures that are not the provider's,
        change nothing.

        :param event: what happened
        :return: None
        """
        if not event.provider:
            return
        if event.name in (MESSAGE_SENT, MESSAGE_RECEIVED):
            self._note(event.provider, None, event.timestamp)
        elif _is_provider_failure(event):
            self._note(event.provider, event.error or MailThunderProviderException(event.name), event.timestamp)

    def probe(self, providers: Iterable[MailProvider]) -> List[dict]:
        """
        Ask each provider to prove it can reach its server and log in, and record the answers.

        :param providers: the providers to check, e.g. ``mail.providers``
        :return: :meth:`report` after the checks
        """
        for provider in providers:
            try:
                provider.check()
            except MailThunderException as error:
                self._note(provider.name, error, datetime.now(timezone.utc))
            else:
                self._note(provider.name, None, datetime.now(timezone.utc))
        return self.report()

    def _state(self, record: _Record) -> str:
        if record.consecutive_failures >= self._threshold:
            return DOWN
        if record.consecutive_failures:
            return DEGRADED
        return HEALTHY if record.successes else UNKNOWN

    def status(self, provider: str) -> dict:
        """
        :param provider: a provider's name
        :return: its state and counters, as JSON-ready values (``unknown`` for a provider nothing is known of)
        """
        with self._lock:
            record = self._records.get(provider, _Record())
            return {
                "provider": provider, "state": self._state(record), "successes": record.successes,
                "failures": record.failures, "consecutive_failures": record.consecutive_failures,
                "last_success": record.last_success.isoformat() if record.last_success else None,
                "last_failure": record.last_failure.isoformat() if record.last_failure else None,
                "last_error": record.last_error,
            }

    def report(self) -> List[dict]:
        """
        :return: the status of every provider that was seen, by name
        """
        with self._lock:
            names = sorted(self._records)
        return [self.status(name) for name in names]
