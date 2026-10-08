"""
The HTTP server of MailThunder Studio: one page, its script and style, and a JSON API over
:class:`~je_mail_thunder.studio.api.StudioApi`. Standard library only.

It is a local tool. It binds ``localhost`` unless told otherwise, every API request must carry the token that
was printed when the server started, and a request whose ``Host`` is not the address it was started on is
refused, so a web page open in the same browser cannot reach it.
"""
from __future__ import annotations

import hmac
import json
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional, Tuple

from je_mail_thunder.core.mail import Mail
from je_mail_thunder.studio.api import StudioApi
from je_mail_thunder.studio.page import INDEX_HTML, STUDIO_CSS, STUDIO_JS
from je_mail_thunder.utils.exception.exceptions import MailThunderException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

# One slot above the Graph webhook listener (9946).
DEFAULT_PORT = 9947
SESSION_HEADER = "X-MailThunder-Token"
MAX_REQUEST_BYTES = 1024 * 1024
_ASSETS = {
    "/": ("text/html; charset=utf-8", INDEX_HTML),
    "/studio.css": ("text/css; charset=utf-8", STUDIO_CSS),
    "/studio.js": ("text/javascript; charset=utf-8", STUDIO_JS),
}
_SECURITY_HEADERS = (
    ("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Cache-Control", "no-store"),
)
_LOCAL_NAMES = ("localhost", "127.0.0.1", "[::1]")


class _StudioHandler(BaseHTTPRequestHandler):
    """Serves the page and answers the API."""

    server: "StudioServer"

    def _answer(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in _SECURITY_HEADERS:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: Any) -> None:
        self._answer(status, "application/json; charset=utf-8", json.dumps(value, ensure_ascii=False).encode("utf-8"))

    def _refusal(self) -> Optional[Tuple[int, str]]:
        """Why this request is not served, if it is not."""
        if self.headers.get("Host", "") not in self.server.allowed_hosts:
            return 403, "this address is not the one MailThunder Studio was started on"
        if self.path.split("?", 1)[0].startswith("/api/"):
            given = self.headers.get(SESSION_HEADER, "")
            if not hmac.compare_digest(given.encode("utf-8"), self.server.token.encode("utf-8")):
                return 403, "the request does not carry the Studio token"
        return None

    def _payload(self) -> Any:
        """The JSON body of a POST, or the query of a GET."""
        if self.command == "GET":
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            return {name: values[-1] for name, values in query.items()}
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 0 <= length <= MAX_REQUEST_BYTES:
            raise ValueError("the request body is missing or too large")
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def _serve(self) -> None:
        refusal = self._refusal()
        if refusal is not None:
            self._json(refusal[0], {"error": "Forbidden", "message": refusal[1]})
            return
        path = urllib.parse.urlsplit(self.path).path
        if self.command == "GET" and path in _ASSETS:
            content_type, text = _ASSETS[path]
            self._answer(200, content_type, text.encode("utf-8"))
            return
        route = self.server.api.routes.get((self.command, path))
        if route is None:
            self._json(404, {"error": "NotFound", "message": f"there is no {self.command} {path}"})
            return
        try:
            self._json(200, route(self._payload()))
        except MailThunderException as error:
            self._json(400, {"error": type(error).__name__, "message": str(error)})
        except (ValueError, TypeError) as error:
            self._json(400, {"error": "BadRequest", "message": str(error)})

    def do_GET(self) -> None:  # pylint: disable=invalid-name  # reason: the name http.server calls
        """Serve the page, its assets and the reading half of the API."""
        self._serve()

    def do_POST(self) -> None:  # pylint: disable=invalid-name  # reason: the name http.server calls
        """Serve the acting half of the API."""
        self._serve()

    def log_message(self, format, *args) -> None:  # pylint: disable=redefined-builtin  # reason: inherited name
        """Requests go to the MailThunder log instead of stderr."""
        mail_thunder_logger.info(f"studio, {self.address_string()} {format % args}")


class StudioServer(ThreadingHTTPServer):
    """MailThunder Studio on one address. It is a context manager; ``shutdown()`` or leaving the block ends it."""

    daemon_threads = True

    def __init__(self, api: StudioApi, host: str = "localhost", port: int = DEFAULT_PORT) -> None:
        """
        :param api: what the pages show and do
        :param host: the address to bind; anything but ``localhost`` exposes the mailbox to that network
        :param port: the port to bind; 0 picks a free one
        """
        super().__init__((host, port), _StudioHandler)
        self.api = api
        self.token = secrets.token_urlsafe(32)
        bound_port = self.server_address[1]
        self.allowed_hosts = frozenset(f"{name}:{bound_port}" for name in _LOCAL_NAMES + (host,))
        self.host = host
        #: Whether the command line should open the page in a browser once the server is up.
        self.open_browser = False

    @property
    def url(self) -> str:
        """The address to open: the token travels in the fragment, which browsers do not send to any server."""
        return f"http://{self.host}:{self.server_address[1]}/#token={self.token}"

    def serve_in_background(self) -> threading.Thread:
        """
        :return: the daemon thread the server now runs on
        """
        thread = threading.Thread(target=self.serve_forever, name="mail-thunder-studio", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        """
        Stop serving, close the socket and close the ``Mail``.

        :return: None
        """
        self.shutdown()
        self.server_close()
        self.api.mail.close()


def start_studio(mail: Optional[Mail] = None, host: str = "localhost", port: int = DEFAULT_PORT,
                 project: Optional[str] = None) -> StudioServer:
    """
    Start MailThunder Studio on a daemon thread.

    :param mail: the ``Mail`` to show and use; ``Mail()`` by default
    :param host: the address to bind; ``localhost`` unless the mailbox should be reachable from elsewhere
    :param port: the port to bind
    :param project: the project directory the Projects page describes
    :return: the running server; ``server.url`` is the address to open and ``server.stop()`` ends it
    """
    server = StudioServer(StudioApi(mail, project), host, port)
    server.serve_in_background()
    mail_thunder_logger.info(f"studio, serving on {host}:{server.server_address[1]}")
    return server
