"""
The Microsoft Graph provider and its trigger backends, against a scripted transport: no request leaves the
machine except to the webhook listener on localhost.
"""
import base64
import json
import threading
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timedelta, timezone

import pytest

from je_mail_thunder.auth.oauth2 import OAuth2Auth
from je_mail_thunder.auth.password import PasswordAuth
from je_mail_thunder.auth.xoauth2 import XOAUTH2Auth
from je_mail_thunder.core.account import MailAccount, default_account
from je_mail_thunder.core.events import ATTACHMENT_RECEIVED, MESSAGE_RECEIVED
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers import http as http_module
from je_mail_thunder.providers import microsoft_graph
from je_mail_thunder.providers.base import MailSender, MailStore
from je_mail_thunder.providers.http import decode_json, https_request
from je_mail_thunder.providers.microsoft_graph import (
    GRAPH_ROOT,
    GRAPH_SCOPE,
    MicrosoftGraphProvider,
    graph_message,
    mail_message,
)
from je_mail_thunder.providers.registry import create_providers, registered_providers
from je_mail_thunder.triggers import graph as graph_triggers
from je_mail_thunder.triggers.factory import create_backend
from je_mail_thunder.triggers.graph import GraphPollingBackend, GraphWebhookBackend
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderAuthenticationException,
    MailThunderConnectionException,
    MailThunderProviderException,
    MailThunderSendException,
    MailThunderTriggerException,
)
from je_mail_thunder.utils.oauth2.oauth2 import OAuth2Settings, OAuth2TokenCache
from mail_fakes import RecordingStore

_USER = "someone@contoso.com"
_TOKEN = "graph-access-token-secret"
_AUTH = OAuth2Auth(OAuth2Settings(user=_USER, provider="microsoft", access_token=_TOKEN))
_MESSAGE = MailMessage(to="Reader <reader@example.com>", cc="copy@example.com", sender=_USER, subject="Hello",
                       text="plain", html="<b>rich</b>")


class _Graph:
    """A transport that records requests and answers them in order with ``(status, JSON)``."""

    def __init__(self, *answers):
        self.answers = deque(answers)
        self.requests = []

    def __call__(self, method, url, headers, body):
        payload = json.loads(body) if body and headers.get("Content-Type") == "application/json" else body
        self.requests.append((method, url.replace(GRAPH_ROOT, ""), headers, payload))
        status, answer = self.answers.popleft() if self.answers else (200, {})
        return status, (json.dumps(answer).encode("utf-8") if not isinstance(answer, bytes) else answer)

    def calls(self):
        return [(method, path) for method, path, _headers, _payload in self.requests]


def _provider(*answers, auth=_AUTH):
    transport = _Graph(*answers)
    return MicrosoftGraphProvider(MailAccount(provider="microsoft_graph", auth=auth), transport), transport


def _resource(identifier, subject="Report", has_attachments=False, received="2026-10-01T08:00:00Z"):
    return {"id": identifier, "subject": subject, "hasAttachments": has_attachments, "receivedDateTime": received,
            "from": {"emailAddress": {"address": "ci@example.com", "name": "CI"}},
            "toRecipients": [{"emailAddress": {"address": _USER, "name": _USER}}],
            "body": {"contentType": "html", "content": "<p>done</p>"},
            "internetMessageId": f"<{identifier}@example.com>"}


# --- the two message forms --------------------------------------------------------------------------------------

def test_a_message_as_graph_takes_it(tmp_path):
    report = tmp_path / "report.txt"
    report.write_bytes(b"numbers")
    message = MailMessage(to=["Reader <reader@example.com>", "b@example.com"], bcc="hidden@example.com",
                          reply_to="replies@example.com", sender=_USER, subject="Hello", text="plain",
                          html="<b>rich</b>", attachments=[report], headers={"X-Run": "42"})
    resource = graph_message(message)
    assert resource["body"] == {"contentType": "HTML", "content": "<b>rich</b>"}
    assert resource["toRecipients"] == [{"emailAddress": {"address": "reader@example.com", "name": "Reader"}},
                                        {"emailAddress": {"address": "b@example.com"}}]
    assert resource["bccRecipients"][0]["emailAddress"]["address"] == "hidden@example.com"
    assert resource["replyTo"][0]["emailAddress"]["address"] == "replies@example.com"
    assert resource["internetMessageHeaders"] == [{"name": "X-Run", "value": "42"}]
    assert resource["attachments"] == [{"@odata.type": "#microsoft.graph.fileAttachment", "name": "report.txt",
                                        "contentType": "text/plain",
                                        "contentBytes": base64.b64encode(b"numbers").decode("ascii")}]
    assert "from" not in resource
    assert graph_message(message, sender_is_account=False)["from"] == {"emailAddress": {"address": _USER}}
    assert "attachments" not in graph_message(message, attachments=False)
    assert graph_message(MailMessage(to="a@example.com", text="only text"))["body"] == {
        "contentType": "Text", "content": "only text"}
    with pytest.raises(MailThunderProviderException, match="start with X-: \\['List-Id'\\]"):
        graph_message(MailMessage(to="a@example.com", headers={"List-Id": "x", "x-ok": "1"}))


def test_a_graph_message_as_a_mail_message():
    resource = _resource("AAMk=", has_attachments=True)
    resource["ccRecipients"] = [{"emailAddress": {"address": "copy@example.com", "name": "Copy"}}, {"emailAddress": {}}]
    attachments = [
        {"name": "../../evil.sh", "contentType": "text/x-sh", "contentBytes": base64.b64encode(b"echo").decode()},
        {"@odata.type": "#microsoft.graph.itemAttachment", "name": "meeting"},
        {"name": None, "contentBytes": base64.b64encode(b"x").decode()},
    ]
    message = mail_message(resource, attachments)
    assert (message.message_id, message.subject, message.sender) == ("AAMk=", "Report", "CI <ci@example.com>")
    assert (message.to, message.cc) == ((_USER,), ("Copy <copy@example.com>",))
    assert (message.html, message.text) == ("<p>done</p>", None)
    assert message.date == datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    assert dict(message.headers) == {"Message-ID": "<AAMk=@example.com>"}
    assert [(a.filename, a.content_type, a.read()) for a in message.attachments] == [
        ("evil.sh", "text/x-sh", b"echo"), ("attachment", "application/octet-stream", b"x")]
    plain = mail_message({"id": "1", "body": {"contentType": "text", "content": "hi"}, "receivedDateTime": "soon"})
    assert (plain.text, plain.html, plain.date, plain.sender, plain.subject) == ("hi", None, None, None, "")


# --- sending ----------------------------------------------------------------------------------------------------

def test_a_small_message_is_one_sendmail_request():
    provider, graph = _provider((202, {}))
    provider.send(_MESSAGE)
    ((method, path, headers, payload),) = graph.requests
    assert (method, path) == ("POST", "/me/sendMail")
    assert headers["Authorization"] == f"Bearer {_TOKEN}" and headers["Content-Type"] == "application/json"
    assert payload["saveToSentItems"] is True and payload["message"]["subject"] == "Hello"
    assert "from" not in payload["message"]
    assert isinstance(provider, MailSender) and isinstance(provider, MailStore) and provider.close() is None


def test_another_sender_is_named_in_the_message():
    provider, graph = _provider((202, {}))
    provider.send(MailMessage(to="a@example.com", sender="Team <team@contoso.com>", text="x"))
    assert graph.requests[0][3]["message"]["from"] == {
        "emailAddress": {"address": "team@contoso.com", "name": "Team"}}


def test_large_attachments_go_through_a_draft_and_an_upload_session(tmp_path, monkeypatch):
    monkeypatch.setattr(microsoft_graph, "MAX_INLINE_TOTAL_BYTES", 8)
    monkeypatch.setattr(microsoft_graph, "MAX_INLINE_ATTACHMENT_BYTES", 8)
    monkeypatch.setattr(microsoft_graph, "UPLOAD_CHUNK_BYTES", 10)
    small, big = tmp_path / "small.txt", tmp_path / "big.bin"
    small.write_bytes(b"12345")
    big.write_bytes(b"x" * 25)
    upload_url = "https://outlook.office.com/api/upload/session-1"
    provider, graph = _provider((201, {"id": "draft/1"}), (201, {}), (200, {"uploadUrl": upload_url}),
                                (200, {}), (200, {}), (201, {}), (202, {}))
    provider.send(MailMessage(to="a@example.com", sender=_USER, text="x", attachments=[small, big]))
    assert graph.calls() == [
        ("POST", "/me/messages"),
        ("POST", "/me/messages/draft%2F1/attachments"),
        ("POST", "/me/messages/draft%2F1/attachments/createUploadSession"),
        ("PUT", upload_url), ("PUT", upload_url), ("PUT", upload_url),
        ("POST", "/me/messages/draft%2F1/send"),
    ]
    assert "attachments" not in graph.requests[0][3]
    assert graph.requests[2][3] == {"AttachmentItem": {"attachmentType": "file", "name": "big.bin", "size": 25,
                                                       "contentType": "application/octet-stream"}}
    chunks = graph.requests[3:6]
    assert [request[2]["Content-Range"] for request in chunks] == [
        "bytes 0-9/25", "bytes 10-19/25", "bytes 20-24/25"]
    assert b"".join(request[3] for request in chunks) == b"x" * 25
    assert all("Authorization" not in request[2] for request in chunks)


def test_a_refused_upload_or_message_is_a_send_error(tmp_path, monkeypatch):
    monkeypatch.setattr(microsoft_graph, "MAX_INLINE_TOTAL_BYTES", 1)
    monkeypatch.setattr(microsoft_graph, "MAX_INLINE_ATTACHMENT_BYTES", 1)
    big = tmp_path / "big.bin"
    big.write_bytes(b"xx")
    message = MailMessage(to="a@example.com", sender=_USER, text="x", attachments=[big])
    provider, _graph = _provider((201, {"id": "d"}), (200, {"uploadUrl": "https://up.example.com/1"}), (507, {}))
    with pytest.raises(MailThunderSendException, match="refused the attachment 'big.bin' \\(HTTP 507\\)"):
        provider.send(message)
    provider, _graph = _provider((201, {}))
    with pytest.raises(MailThunderSendException, match="created no draft"):
        provider.send(message)
    provider, _graph = _provider((400, {"error": {"code": "ErrorInvalidRecipients", "message": "bad address"}}))
    with pytest.raises(MailThunderSendException, match="HTTP 400 ErrorInvalidRecipients: bad address"):
        provider.send(_MESSAGE)


def test_a_draft_is_created_in_the_drafts_folder_or_the_one_named():
    provider, graph = _provider((201, {"id": "draft-1"}), (201, {"id": "draft-2"}),
                                (200, {"value": [{"id": "folder/id=="}]}), (201, {"id": "draft-3"}),
                                (201, {"id": "draft-4"}))
    assert provider.create_draft(_MESSAGE) == "draft-1"
    assert provider.create_draft(_MESSAGE, folder="Sent Items") == "draft-2"
    assert provider.create_draft(_MESSAGE, folder="Bob's reports") == "draft-3"
    assert provider.create_draft(_MESSAGE, folder="Bob's reports") == "draft-4"
    assert graph.calls() == [
        ("POST", "/me/messages"),
        ("POST", "/me/mailFolders/sentitems/messages"),
        ("GET", "/me/mailFolders?%24filter=displayName+eq+%27Bob%27%27s+reports%27&%24top=1&%24select=id"),
        ("POST", "/me/mailFolders/folder%2Fid%3D%3D/messages"),
        ("POST", "/me/mailFolders/folder%2Fid%3D%3D/messages"),
    ]
    provider, _graph = _provider((200, {"value": []}))
    with pytest.raises(MailThunderProviderException, match="no folder 'Nowhere'"):
        provider.create_draft(_MESSAGE, folder="Nowhere")
    for bad in ("", "  ", None, 5):
        with pytest.raises(MailThunderProviderException, match="invalid folder name"):
            provider.folder_path(bad)


# --- reading and deleting ---------------------------------------------------------------------------------------

def test_messages_come_a_page_at_a_time_newest_first():
    next_link = GRAPH_ROOT + "/me/mailFolders/inbox/messages?$skip=2"
    provider, graph = _provider(
        (200, {"value": [_resource("3"), _resource("2", has_attachments=True)], "@odata.nextLink": next_link}),
        (200, {"value": [{"name": "r.pdf", "contentType": "application/pdf",
                          "contentBytes": base64.b64encode(b"%PDF").decode()}]}),
        (200, {"value": [_resource("1")]}))
    reading = provider.get_messages(unread_only=True, query="from/emailAddress/address eq 'ci@example.com'")
    assert graph.requests == []
    first = next(reading)
    assert (first.message_id, first.sender, first.attachments) == ("3", "CI <ci@example.com>", ())
    assert len(graph.requests) == 1
    rest = list(reading)
    assert [message.message_id for message in rest] == ["2", "1"]
    assert rest[0].attachments[0].filename == "r.pdf"
    method, path, _headers, _payload = graph.requests[0]
    assert method == "GET" and path.startswith("/me/mailFolders/inbox/messages?")
    query = urllib.parse.parse_qs(path.split("?", 1)[1])
    assert query["$orderby"] == ["receivedDateTime desc"] and query["$top"] == ["25"]
    assert query["$filter"] == ["receivedDateTime ge 1900-01-01T00:00:00Z and isRead eq false and "
                                "(from/emailAddress/address eq 'ci@example.com')"]
    assert graph.calls()[1:] == [
        ("GET", "/me/messages/2/attachments"), ("GET", "/me/mailFolders/inbox/messages?$skip=2")]


def test_a_limit_stops_the_reading_and_sizes_the_page():
    provider, graph = _provider((200, {"value": [_resource("3"), _resource("2")], "@odata.nextLink": "ignored"}))
    assert [message.message_id for message in provider.get_messages("Archive", limit=1)] == ["3"]
    assert "%24top=1" in graph.requests[0][1] and "/me/mailFolders/archive/messages" in graph.requests[0][1]
    assert list(provider.get_messages(limit=0)) == [] and len(graph.requests) == 1


def test_a_next_link_outside_graph_is_not_followed():
    provider, graph = _provider((200, {"value": [_resource("1")], "@odata.nextLink": "https://evil.example.com/next"}))
    reading = provider.get_messages()
    assert next(reading).message_id == "1"
    with pytest.raises(MailThunderProviderException, match="stays on graph.microsoft.com"):
        next(reading)
    assert len(graph.requests) == 1


def test_one_message_by_id_and_its_deletion():
    provider, graph = _provider((200, _resource("AAMk/a+b=")), (204, b""), (404, {"error": {
        "code": "ErrorItemNotFound", "message": "The specified object was not found in the store."}}))
    assert provider.get_message("AAMk/a+b=").subject == "Report"
    assert provider.delete_message("AAMk/a+b=") is None
    assert graph.calls()[0][1].startswith("/me/messages/AAMk%2Fa%2Bb%3D?%24select=id%2Csubject")
    assert graph.calls()[1] == ("DELETE", "/me/messages/AAMk%2Fa%2Bb%3D")
    with pytest.raises(MailThunderProviderException, match="HTTP 404 ErrorItemNotFound"):
        provider.get_message("gone")
    for bad in ("", " ", None, 5):
        with pytest.raises(MailThunderProviderException, match="message id is text"):
            provider.get_message(bad)


# --- authorisation and errors -----------------------------------------------------------------------------------

@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_token_is_an_authentication_error(status):
    provider, _graph = _provider((status, {"error": {"code": "InvalidAuthenticationToken", "message": "expired"}}))
    with pytest.raises(MailThunderAuthenticationException, match="refused the token") as raised:
        provider.send(_MESSAGE)
    assert _TOKEN not in str(raised.value)


def test_a_password_cannot_log_in_to_graph_and_an_answer_that_is_not_json_is_empty():
    provider, graph = _provider(auth=PasswordAuth(_USER, "p4ss-word-secret"))
    with pytest.raises(MailThunderAuthenticationException, match="password authentication cannot authorise"):
        provider.get_message("1")
    assert graph.requests == []
    provider, _graph = _provider((500, b"<html>Bad Gateway</html>"))
    with pytest.raises(MailThunderProviderException, match="refused the request \\(HTTP 500\\)"):
        provider.get_message("1")


def test_the_token_is_asked_for_with_the_graph_scopes_unless_the_settings_say_otherwise(monkeypatch):
    forms = []

    def post(_url, form, _timeout):
        forms.append(form.get("scope"))
        return {"access_token": f"token-{len(forms)}", "expires_in": 3600}

    monkeypatch.setattr("je_mail_thunder.utils.oauth2.oauth2.oauth2_token_cache",
                        OAuth2TokenCache(post=post, clock=lambda: 0.0))
    settings = OAuth2Settings(user=_USER, provider="microsoft", client_id="c", refresh_token="r")
    provider, graph = _provider(auth=XOAUTH2Auth(settings))
    provider.get_message("1")
    provider.get_message("2")
    assert forms == [GRAPH_SCOPE]
    assert [request[2]["Authorization"] for request in graph.requests] == ["Bearer token-1", "Bearer token-1"]
    custom = OAuth2Settings(user=_USER, provider="microsoft", client_id="c", refresh_token="r", scope="custom.scope")
    provider, _graph = _provider(auth=OAuth2Auth(custom))
    provider.get_message("1")
    assert forms == [GRAPH_SCOPE, "custom.scope"]


def test_graph_is_a_registered_provider_and_can_be_the_default(tmp_path, monkeypatch):
    assert "microsoft_graph" in registered_providers()
    (provider,) = create_providers(MailAccount(provider="Microsoft_Graph", auth=_AUTH))
    assert isinstance(provider, MicrosoftGraphProvider)
    monkeypatch.chdir(tmp_path)
    for name in ("mail_thunder_mail_provider", "mail_thunder_oauth2_access_token", "mail_thunder_oauth2_refresh_token"):
        monkeypatch.delenv(name, raising=False)
    assert default_account().provider == "google"
    monkeypatch.setenv("mail_thunder_mail_provider", " microsoft_graph ")
    assert default_account().provider == "microsoft_graph"
    (tmp_path / "mail_thunder_content.json").write_text(json.dumps({"mail_provider": "smtp"}), encoding="utf-8")
    assert default_account().provider == "smtp"
    (tmp_path / "mail_thunder_content.json").write_text(json.dumps({"mail_provider": 5}), encoding="utf-8")
    assert default_account().provider == "microsoft_graph"


def test_mail_sends_and_reads_through_graph():
    provider, graph = _provider((202, {}), (200, {"value": [_resource("1")]}))
    with Mail(account=MailAccount(provider="microsoft_graph", auth=_AUTH), providers=[provider]) as mail:
        sent = mail.send(to="reader@example.com", subject="Report", html="<b>ok</b>")
        assert [message.subject for message in mail.get_messages(limit=5)] == ["Report"]
    assert sent.sender == _USER and graph.calls()[0] == ("POST", "/me/sendMail")


# --- the HTTPS client -------------------------------------------------------------------------------------------

def test_only_https_is_requested_and_an_error_status_is_an_answer(monkeypatch):
    with pytest.raises(MailThunderProviderException, match="only requested over https"):
        https_request("GET", "http://graph.microsoft.com/v1.0/me", {})
    seen = []

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, _limit):
            return b'{"ok": true}'

    def urlopen(request, timeout):
        seen.append(
            (request.get_method(), request.full_url, request.get_header("Authorization"), request.data, timeout))
        return _Response()

    monkeypatch.setattr(http_module.urllib.request, "urlopen", urlopen)
    assert https_request("POST", "https://graph.microsoft.com/v1.0/me", {"Authorization": "Bearer t"}, b"{}") == (
        200, b'{"ok": true}')
    assert seen == [("POST", "https://graph.microsoft.com/v1.0/me", "Bearer t", b"{}", 60.0)]

    def refused(request, timeout):
        import io
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many", {}, io.BytesIO(b'{"error": {}}'))

    monkeypatch.setattr(http_module.urllib.request, "urlopen", refused)
    assert https_request("GET", "https://graph.microsoft.com/v1.0/me", {}) == (429, b'{"error": {}}')

    def unreachable(request, timeout):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(http_module.urllib.request, "urlopen", unreachable)
    with pytest.raises(MailThunderConnectionException, match="could not be reached: URLError"):
        https_request("GET", "https://graph.microsoft.com/v1.0/me", {})
    assert (decode_json(b""), decode_json(b"not json"), decode_json(b"[1]")) == ({}, {}, [1])


# --- trigger backends -------------------------------------------------------------------------------------------

def test_graph_polling_asks_for_what_was_received_since_the_last_look():
    provider, graph = _provider(
        (200, {"value": [_resource("2", received="2026-10-01T08:00:05Z"), _resource("1")]}),
        (200, {"value": [_resource("3", "New", received="2026-10-01T08:00:05Z"),
                         _resource("2", received="2026-10-01T08:00:05Z")]}),
        (200, {"value": []}))
    backend = create_backend(provider, "INBOX", batch_limit=10)
    assert type(backend) is GraphPollingBackend and backend.name == "graph-polling"
    events = []
    backend.bind(events.append)
    assert backend.poll() == 0
    assert backend.poll() == 1 and events[0].message.subject == "New" and events[0].provider == "microsoft_graph"
    assert backend.poll() == 0
    filters = [urllib.parse.parse_qs(path.split("?", 1)[1])["$filter"][0] for _method, path in graph.calls()]
    assert filters[0] == "receivedDateTime ge 1900-01-01T00:00:00Z"
    assert filters[1] == filters[2] == (
        "receivedDateTime ge 1900-01-01T00:00:00Z and (receivedDateTime ge 2026-10-01T08:00:05Z)")
    with pytest.raises(MailThunderTriggerException, match="needs a MicrosoftGraphProvider"):
        GraphPollingBackend(RecordingStore())


def _webhook(*answers, **options):
    provider, graph = _provider(*answers)
    backend = GraphWebhookBackend(provider, "https://hooks.example.com/mail", host="127.0.0.1", port=0, **options)
    events = []
    backend.bind(events.append)
    return backend, graph, events


def test_a_webhook_subscription_is_created_renewed_and_removed(monkeypatch):
    backend, graph, _events = _webhook((201, {"id": "sub/1"}), (200, {}), (204, b""))
    assert backend.poll() == 0
    method, path, _headers, payload = graph.requests[0]
    assert (method, path) == ("POST", "/subscriptions")
    assert payload["changeType"] == "created" and payload["notificationUrl"] == "https://hooks.example.com/mail"
    assert payload["resource"] == "me/mailFolders('inbox')/messages" and len(payload["clientState"]) >= 32
    expires = datetime.strptime(payload["expirationDateTime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert timedelta(minutes=58) < expires - datetime.now(timezone.utc) <= timedelta(minutes=60)
    assert backend.poll() == 0 and len(graph.requests) == 1
    monkeypatch.setattr(graph_triggers, "RENEW_MARGIN", timedelta(minutes=61))
    assert backend.poll() == 0
    assert graph.calls()[1] == ("PATCH", "/subscriptions/sub%2F1") and "expirationDateTime" in graph.requests[1][3]
    described = backend.describe()
    assert described["subscribed"] is True and described["listening"] == "127.0.0.1:0"
    assert payload["clientState"] not in json.dumps(described)
    backend.close()
    backend.close()
    assert graph.calls()[2] == ("DELETE", "/subscriptions/sub%2F1") and len(graph.requests) == 3


def test_a_notification_needs_the_secret_and_the_subscription_id():
    backend, graph, events = _webhook(
        (201, {"id": "sub-1"}), (200, _resource("m1", has_attachments=True)),
        (200, {"value": [{"name": "r.pdf", "contentBytes": base64.b64encode(b"%PDF").decode()}]}))
    backend.subscribe()
    secret = graph.requests[0][3]["clientState"]
    forged = {"value": [{"subscriptionId": "sub-1", "clientState": "guess", "resourceData": {"id": "m1"}},
                        {"subscriptionId": "other", "clientState": secret, "resourceData": {"id": "m1"}},
                        {"subscriptionId": "sub-1", "resourceData": {"id": "m1"}}]}
    assert backend.handle_notification(forged) == 0 and len(graph.requests) == 1
    assert backend.handle_notification(["not", "an", "object"]) == 0
    genuine = {"value": [{"subscriptionId": "sub-1", "clientState": secret, "resourceData": {"id": "m1"}}]}
    assert backend.handle_notification(genuine) == 2
    assert [(event.name, event.message.message_id) for event in events] == [
        (MESSAGE_RECEIVED, "m1"), (ATTACHMENT_RECEIVED, "m1")]


@pytest.mark.parametrize("arguments", [
    (RecordingStore(), "https://hooks.example.com/mail"), (None, "https://hooks.example.com/mail"),
])
def test_a_webhook_needs_a_graph_provider(arguments):
    with pytest.raises(MailThunderTriggerException, match="needs a MicrosoftGraphProvider"):
        GraphWebhookBackend(*arguments)


def test_a_webhook_needs_an_https_address():
    provider, _graph = _provider()
    for address in ("http://hooks.example.com/mail", "", None):
        with pytest.raises(MailThunderTriggerException, match="https address"):
            GraphWebhookBackend(provider, address)


def _post(port, path, body=b"", headers=None):
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, method="POST", headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310 - the test's own listener
            return response.status, response.read(), response.headers.get("Content-Type")
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers.get("Content-Type")


def test_the_listener_answers_the_validation_and_takes_notifications():
    backend, graph, events = _webhook((201, {"id": "sub-1"}), (200, _resource("m1")), (204, b""))
    arrived = threading.Event()
    backend.bind(lambda event: (events.append(event), arrived.set()))
    backend.start()
    try:
        port = backend._server.server_address[1]
        assert _post(port, "/?validationToken=abc%20123") == (200, b"abc 123", "text/plain; charset=utf-8")
        deadline = datetime.now() + timedelta(seconds=5)
        while not graph.requests and datetime.now() < deadline:
            threading.Event().wait(0.01)
        secret = graph.requests[0][3]["clientState"]
        genuine = json.dumps({"value": [{"subscriptionId": "sub-1", "clientState": secret,
                                         "resourceData": {"id": "m1"}}]}).encode("utf-8")
        assert _post(port, "/", genuine)[0] == 202
        assert arrived.wait(5) and events[0].message.message_id == "m1"
        assert _post(port, "/", b"not json")[0] == 202
        assert _post(port, "/")[0] == 400
        assert _post(port, "/", b"x", {"Content-Length": "nonsense"})[0] == 400
    finally:
        backend.stop()
    assert backend.running is False and backend._server is None
    assert graph.calls()[-1] == ("DELETE", "/subscriptions/sub-1")
