"""
Trigger backends for a Microsoft 365 mailbox read through Microsoft Graph: polling by received time, and change
notifications (webhooks), where Graph calls an HTTPS address when mail arrives.
"""
from __future__ import annotations

import hmac
import json
import secrets
import threading
import urllib.parse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, List, Mapping, Optional

from je_mail_thunder.core.events import ATTACHMENT_RECEIVED, MESSAGE_RECEIVED, MailEvent
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers.base import DEFAULT_FOLDER
from je_mail_thunder.providers.microsoft_graph import MicrosoftGraphProvider
from je_mail_thunder.triggers.polling import PollingBackend
from je_mail_thunder.triggers.trigger import MailTriggerBackend
from je_mail_thunder.utils.exception.exceptions import MailThunderException, MailThunderTriggerException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

# One slot above the sibling action servers (9938 to 9945).
DEFAULT_WEBHOOK_PORT = 9946
# Graph lets a mail subscription live for a little under three days; an hour keeps a forgotten one short.
DEFAULT_LIFETIME_MINUTES = 60
# A subscription is renewed when it has less than this left.
RENEW_MARGIN = timedelta(minutes=10)
# A change notification names messages; it does not carry them.
MAX_NOTIFICATION_BYTES = 1024 * 1024
_TIMESTAMP = "%Y-%m-%dT%H:%M:%SZ"


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime(_TIMESTAMP)


class GraphPollingBackend(PollingBackend):
    """Polling that lets Graph do the filtering: after the first look it asks only for mail received since."""

    name = "graph-polling"

    def __init__(self, store: MicrosoftGraphProvider, *arguments, **options) -> None:
        """
        :param store: the Graph provider to ask
        :param arguments: as :class:`PollingBackend` takes them
        :param options: as :class:`PollingBackend` takes them
        :raises MailThunderTriggerException: the store is not a Graph provider
        """
        if not isinstance(store, MicrosoftGraphProvider):
            raise MailThunderTriggerException(
                f"a Graph trigger needs a MicrosoftGraphProvider, got {type(store).__name__}")
        super().__init__(store, *arguments, **options)
        self._newest: Optional[datetime] = None

    def _new_messages(self) -> List[MailMessage]:
        if self._newest is None:
            fresh = super()._new_messages()
        else:
            # "ge", with the ids already seen left out: two messages can arrive in the same second.
            found = self.store.get_messages(self.folder, limit=self._batch_limit,
                                            query=f"receivedDateTime ge {_stamp(self._newest)}")
            fresh = [message for message in found if message.message_id not in self._seen]
            fresh.reverse()
        dates = [message.date for message in fresh if message.date is not None]
        if dates:
            self._newest = max(dates + ([self._newest] if self._newest is not None else []))
        return fresh


class _NotificationHandler(BaseHTTPRequestHandler):
    """Answers Graph's validation request and takes its change notifications."""

    def _answer(self, status: int, body: bytes = b"") -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # pylint: disable=invalid-name  # reason: the name http.server calls
        """Graph posts both the validation request and the notifications."""
        token = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("validationToken")
        if token:
            # Graph checks that the address is ours by asking for its token back as plain text.
            self._answer(200, token[0].encode("utf-8"))
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_NOTIFICATION_BYTES:
            self._answer(400)
            return
        raw = self.rfile.read(length)
        # Graph wants its answer within seconds; the messages are fetched after it.
        self._answer(202)
        try:
            self.server.backend.handle_notification(json.loads(raw.decode("utf-8")))  # pylint: disable=no-member
        except (ValueError, MailThunderException) as error:
            mail_thunder_logger.error(f"graph-webhook trigger, notification ignored: {repr(error)}")

    def log_message(self, format, *args) -> None:  # pylint: disable=redefined-builtin  # reason: inherited name
        """Requests go to the MailThunder log instead of stderr."""
        mail_thunder_logger.info(f"graph-webhook trigger, {self.address_string()} {format % args}")


class _NotificationServer(ThreadingHTTPServer):
    """The listener of one webhook backend."""

    daemon_threads = True

    def __init__(self, address, backend: "GraphWebhookBackend") -> None:
        super().__init__(address, _NotificationHandler)
        self.backend = backend


class GraphWebhookBackend(MailTriggerBackend):  # pylint: disable=too-many-instance-attributes  # reason: settings
    """
    Lets Graph say when mail arrives. Graph posts a change notification to ``notification_url``, a public HTTPS
    address that must reach this backend's listener (a reverse proxy or a tunnel in front of ``host:port``).
    The backend keeps the subscription alive while it runs and removes it when it stops.
    """

    name = "graph-webhook"

    def __init__(self, store: MicrosoftGraphProvider, notification_url: str, folder: str = DEFAULT_FOLDER,
                 host: str = "localhost", port: int = DEFAULT_WEBHOOK_PORT,
                 lifetime_minutes: int = DEFAULT_LIFETIME_MINUTES) -> None:
        """
        :param store: the Graph provider of the mailbox
        :param notification_url: the public ``https`` address Graph posts to
        :param folder: the folder to watch
        :param host: the address the listener binds; ``localhost`` unless the proxy is on another machine
        :param port: the port the listener binds
        :param lifetime_minutes: how long each subscription lasts before it is renewed
        :raises MailThunderTriggerException: the store is not a Graph provider, or the address is not ``https``
        """
        super().__init__(interval=60.0)
        if not isinstance(store, MicrosoftGraphProvider):
            raise MailThunderTriggerException(
                f"a Graph trigger needs a MicrosoftGraphProvider, got {type(store).__name__}")
        if not isinstance(notification_url, str) or not notification_url.startswith("https://"):
            raise MailThunderTriggerException("Graph only posts notifications to an https address")
        self.store = store
        self.folder = folder
        self._notification_url = notification_url
        self._address = (host, port)
        self._lifetime = timedelta(minutes=lifetime_minutes)
        self._client_state = secrets.token_urlsafe(32)
        self._subscription_id: Optional[str] = None
        self._expires: Optional[datetime] = None
        self._server: Optional[_NotificationServer] = None

    def _expiration(self) -> datetime:
        return datetime.now(timezone.utc) + self._lifetime

    def subscribe(self) -> str:
        """
        Ask Graph to post a notification for every message created in the folder.

        :return: the subscription's id
        :raises MailThunderProviderException: Graph refused, for instance because it could not validate the address
        """
        expires = self._expiration()
        answer = self.store.call("POST", "/subscriptions", {
            "changeType": "created",
            "notificationUrl": self._notification_url,
            "resource": f"me/mailFolders('{self.store.folder_path(self.folder)}')/messages",
            "expirationDateTime": _stamp(expires),
            "clientState": self._client_state,
        })
        self._subscription_id, self._expires = answer.get("id"), expires
        mail_thunder_logger.info(f"graph-webhook trigger, subscribed until {_stamp(expires)}")
        return self._subscription_id

    def unsubscribe(self) -> None:
        """
        Remove the subscription, if there is one.

        :return: None
        """
        subscription, self._subscription_id, self._expires = self._subscription_id, None, None
        if subscription:
            self.store.call("DELETE", "/subscriptions/" + urllib.parse.quote(subscription, safe=""))

    def poll(self) -> int:
        """
        Keep the subscription alive: create it when there is none, renew it when it is about to expire. The
        events themselves come from Graph's notifications.

        :return: 0
        """
        if self._subscription_id is None:
            self.subscribe()
        elif self._expires - datetime.now(timezone.utc) < RENEW_MARGIN:
            expires = self._expiration()
            self.store.call("PATCH", "/subscriptions/" + urllib.parse.quote(self._subscription_id, safe=""),
                            {"expirationDateTime": _stamp(expires)})
            self._expires = expires
        return 0

    def handle_notification(self, payload: Mapping[str, Any]) -> int:
        """
        Turn a change notification into events. An entry that does not carry this backend's secret and
        subscription id is ignored: anyone can post to a public address.

        :param payload: the JSON body Graph posted
        :return: how many events were emitted
        """
        emitted = 0
        for entry in (payload.get("value") or ()) if isinstance(payload, Mapping) else ():
            state = str(entry.get("clientState", ""))
            if not hmac.compare_digest(state.encode("utf-8"), self._client_state.encode("utf-8")) \
                    or entry.get("subscriptionId") != self._subscription_id:
                mail_thunder_logger.error("graph-webhook trigger, a notification with the wrong secret was ignored")
                continue
            message = self.store.get_message(str((entry.get("resourceData") or {}).get("id", "")))
            self._emit(MailEvent(MESSAGE_RECEIVED, message=message, provider=self.store.name, folder=self.folder))
            for attachment in message.attachments:
                self._emit(MailEvent(ATTACHMENT_RECEIVED, message=message, attachment=attachment,
                                     provider=self.store.name, folder=self.folder))
            emitted += 1 + len(message.attachments)
        return emitted

    def start(self) -> None:
        """
        Open the listener, then keep a subscription alive on a daemon thread.

        :return: None
        """
        if self._server is None:
            self._server = _NotificationServer(self._address, self)
            threading.Thread(target=self._server.serve_forever, name="mail-thunder-graph-webhook-http",
                             daemon=True).start()
        super().start()

    def close(self) -> None:
        """
        Remove the subscription and close the listener.

        :return: None
        """
        try:
            self.unsubscribe()
        except MailThunderException as error:
            mail_thunder_logger.error(f"graph-webhook trigger, the subscription was not removed: {repr(error)}")
        server, self._server = self._server, None
        if server is not None:
            server.shutdown()
            server.server_close()

    def describe(self) -> dict:
        """
        :return: the backend's name, folder, state and whether Graph is subscribed (never the secret)
        """
        return {**super().describe(), "folder": self.folder, "provider": self.store.name,
                "subscribed": self._subscription_id is not None,
                "listening": f"{self._address[0]}:{self._address[1]}"}
