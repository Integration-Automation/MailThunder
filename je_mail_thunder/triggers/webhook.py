"""
Mail events as outgoing webhooks: a handler that posts each event it is given to an HTTPS address, so another
system hears about mail without importing MailThunder.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import queue
import threading
from typing import Any, Dict, Optional

from je_mail_thunder.core.events import MailEvent
from je_mail_thunder.providers.http import Transport, https_request
from je_mail_thunder.utils.exception.exceptions import MailThunderException, MailThunderTriggerException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

SIGNATURE_HEADER = "X-MailThunder-Signature"
EVENT_HEADER = "X-MailThunder-Event"
# Events waiting to be posted; past this, new ones are dropped rather than held in memory without end.
DEFAULT_QUEUE_SIZE = 1000
_STOP = object()


def webhook_payload(event: MailEvent, bodies: bool = False) -> Dict[str, Any]:
    """
    An event as the JSON a webhook receives.

    :param event: what happened
    :param bodies: include the text and HTML of the message; left out by default
    :return: JSON-ready values; attachments are described, never included
    """
    payload = event.to_dict()
    if not bodies and payload["message"] is not None:
        payload["message"] = {key: value for key, value in payload["message"].items() if key not in ("text", "html")}
    return payload


def sign(secret: str, body: bytes) -> str:
    """
    :param secret: the secret shared with the receiver
    :param body: the request body
    :return: ``sha256=<hex HMAC-SHA256 of the body>``, the value of the signature header
    """
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


class WebhookForwarder:
    """
    An event handler that posts events to a URL: ``mail.on("*", WebhookForwarder("https://example.com/hook"))``.

    Events are queued and posted in order by one daemon thread, so a slow receiver never delays a send. With a
    ``secret``, every request carries ``X-MailThunder-Signature: sha256=<HMAC of the body>`` for the receiver
    to check.
    """

    def __init__(self, url: str, secret: Optional[str] = None, bodies: bool = False,
                 queue_size: int = DEFAULT_QUEUE_SIZE, transport: Transport = https_request) -> None:
        """
        :param url: the ``https`` address to post to
        :param secret: signs each request, so the receiver can tell it came from here
        :param bodies: include message bodies in the payload
        :param queue_size: how many events may wait to be posted
        :param transport: sends one HTTPS request (replaceable for tests or a proxy-aware client)
        :raises MailThunderTriggerException: the address is not ``https``
        """
        if not isinstance(url, str) or not url.startswith("https://"):
            raise MailThunderTriggerException("a webhook is posted to an https address")
        self._url = url
        self._secret = secret
        self._bodies = bodies
        self._transport = transport
        self._queue: "queue.Queue[Any]" = queue.Queue(maxsize=queue_size)
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def __call__(self, event: MailEvent) -> None:
        """
        Queue an event for posting.

        :param event: what happened
        :return: None
        """
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            mail_thunder_logger.error(f"webhook_forwarder, queue full: the event {event.name!r} was dropped")
            return
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._work, name="mail-thunder-webhook", daemon=True)
                self._thread.start()

    def deliver(self, event: MailEvent) -> int:
        """
        Post one event now, on the calling thread.

        :param event: what happened
        :return: the receiver's HTTP status
        :raises MailThunderTriggerException: the receiver answered with an error status
        :raises MailThunderConnectionException: the receiver could not be reached
        """
        body = json.dumps(webhook_payload(event, self._bodies), ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8", EVENT_HEADER: event.name}
        if self._secret:
            headers[SIGNATURE_HEADER] = sign(self._secret, body)
        status, _ = self._transport("POST", self._url, headers, body)
        if status >= 400:
            raise MailThunderTriggerException(f"the webhook answered HTTP {status} to the event {event.name!r}")
        return status

    def _work(self) -> None:
        while True:
            event = self._queue.get()
            try:
                if event is _STOP:
                    return
                self.deliver(event)
            except MailThunderException as error:
                mail_thunder_logger.error(f"webhook_forwarder, not delivered: {repr(error)}")
            finally:
                self._queue.task_done()

    def flush(self) -> None:
        """
        Wait until every queued event has been posted or given up.

        :return: None
        """
        self._queue.join()

    def close(self) -> None:
        """
        Post what is queued, then end the thread.

        :return: None
        """
        with self._lock:
            thread, self._thread = self._thread, None
        if thread is not None and thread.is_alive():
            self._queue.put(_STOP)
            thread.join()
