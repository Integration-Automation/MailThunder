"""
Trigger backends: what watches a mailbox and turns what happens there into events.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Tuple

from je_mail_thunder.core.events import MailEvent, failure_events
from je_mail_thunder.utils.exception.exceptions import MailThunderException, MailThunderTriggerException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

Emit = Callable[[MailEvent], Any]


def _ignore(_event: MailEvent) -> None:
    """Where a backend's events go until it is bound to a dispatcher."""


class MailTriggerBackend(ABC):
    """
    One way of noticing new mail. A backend is bound to the function that takes its events, then either asked
    to look once (:meth:`poll`) or left running on a daemon thread (:meth:`start` / :meth:`stop`).
    """

    #: The backend's name, for logs and for the events it emits.
    name = "backend"
    #: Seconds to wait after a look that failed before looking again.
    retry_seconds = 30.0

    def __init__(self, interval: float = 60.0) -> None:
        """
        :param interval: seconds between two looks while the backend runs
        :raises MailThunderTriggerException: the interval is not a positive number
        """
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
            raise MailThunderTriggerException("a trigger interval is a positive number of seconds")
        self.interval = float(interval)
        self._emit: Emit = _ignore
        self._stopping = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def bind(self, emit: Emit) -> None:
        """
        :param emit: called with every event the backend notices
        :return: None
        """
        self._emit = emit

    @abstractmethod
    def poll(self) -> int:
        """
        Look once and emit an event for everything that is new.

        :return: how many events were emitted
        """

    def wait(self, seconds: float) -> None:
        """
        What the backend does between two looks: sleep, unless it has a better way of waiting.

        :param seconds: the longest it may wait
        :return: None
        """
        self._stopping.wait(seconds)

    def close(self) -> None:
        """
        Release what the backend holds once it has stopped.

        :return: None
        """

    def run(self) -> None:
        """
        Look, wait, and look again until :meth:`stop`. A look that fails is logged, reported as an
        ``authentication_failed`` or ``connection_failed`` event when it is one, and tried again later.

        :return: None
        """
        while not self._stopping.is_set():
            delay = self.interval
            try:
                self.poll()
            except MailThunderException as error:
                mail_thunder_logger.error(f"{self.name} trigger, failed: {repr(error)}")
                for event in failure_events(error, provider=self.name):
                    self._emit(event)
                delay = self.retry_seconds
            if not self._stopping.is_set():
                self.wait(delay)

    @property
    def running(self) -> bool:
        """True while the backend's thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """
        Run the backend on a daemon thread; nothing happens when it already runs.

        :return: None
        """
        if self.running:
            return
        mail_thunder_logger.info(f"{self.name} trigger, start")
        self._stopping.clear()
        self._thread = threading.Thread(target=self.run, name=f"mail-thunder-{self.name}", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """
        Ask the thread to end, wait for it, and release what the backend holds.

        :param timeout: seconds to wait for the thread
        :return: None
        """
        mail_thunder_logger.info(f"{self.name} trigger, stop")
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout)
        self._thread = None
        self.close()

    def describe(self) -> dict:
        """
        :return: the backend's name, interval and state, as JSON-ready values
        """
        return {"name": self.name, "interval": self.interval, "running": self.running}


class TriggerManager:
    """The trigger backends of one :class:`~je_mail_thunder.core.mail.Mail`."""

    def __init__(self, emit: Emit) -> None:
        """
        :param emit: where the backends send their events
        """
        self._emit = emit
        self._backends: List[MailTriggerBackend] = []

    @property
    def backends(self) -> Tuple[MailTriggerBackend, ...]:
        """The backends, in the order they were added."""
        return tuple(self._backends)

    def add(self, backend: MailTriggerBackend) -> MailTriggerBackend:
        """
        :param backend: a backend; its events go to this manager's dispatcher
        :return: the backend
        :raises MailThunderTriggerException: it is not a trigger backend
        """
        if not isinstance(backend, MailTriggerBackend):
            raise MailThunderTriggerException(f"expected a MailTriggerBackend, got {type(backend).__name__}")
        backend.bind(self._emit)
        self._backends.append(backend)
        return backend

    def remove(self, backend: MailTriggerBackend) -> None:
        """
        Stop a backend and forget it.

        :param backend: a backend that was added
        :return: None
        """
        if backend in self._backends:
            self._backends.remove(backend)
            backend.stop()

    def poll(self) -> int:
        """
        Ask every backend to look once.

        :return: how many events were emitted
        """
        return sum(backend.poll() for backend in self._backends)

    def start(self) -> None:
        """
        Start every backend that is not running.

        :return: None
        """
        for backend in self._backends:
            backend.start()

    def stop(self) -> None:
        """
        Stop every backend.

        :return: None
        """
        for backend in self._backends:
            backend.stop()
