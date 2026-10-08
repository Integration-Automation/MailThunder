"""
MailThunder Studio: what its API answers, and what its server lets through. The server is bound to a free
port on localhost and spoken to with ``urllib``; the mail behind it is on recording providers.
"""
import ipaddress
import json
import urllib.error
import urllib.request

import pytest

from je_mail_thunder import create_project_dir
from je_mail_thunder.attachments.policy import AttachmentPolicy
from je_mail_thunder.auth.password import PasswordAuth
from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.monitoring.audit import AuditLog
from je_mail_thunder.studio import __main__ as studio_main
from je_mail_thunder.studio.api import StudioApi
from je_mail_thunder.studio.page import INDEX_HTML, STUDIO_JS
from je_mail_thunder.studio.server import DEFAULT_PORT, SESSION_HEADER, StudioServer, start_studio
from je_mail_thunder.templates.loader import TemplateLoader
from je_mail_thunder.templates.template import MailTemplate
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderConnectionException,
    MailThunderMessageException,
    MailThunderStudioException,
    TemplateNotFound,
)
from mail_fakes import MADE_UP_PASSPHRASE, RecordingSender, RecordingStore, stored_message

_USER = "someone@example.com"
_PASSWORD = MADE_UP_PASSPHRASE


@pytest.fixture
def studio(tmp_path, monkeypatch):
    """A Studio API on recording providers, with its log and audit files in a temporary directory."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAIL_THUNDER_LOG_FILE", str(tmp_path / "mail.log"))
    sender, store = RecordingSender(), RecordingStore([stored_message("1", "Old")])
    loader = TemplateLoader([tmp_path / "templates"])
    loader.add(MailTemplate("report", subject="[{{ project }}] done", text="Passed: {{ passed }}",
                            html="<b>{{ passed }}</b>", variables={"project": {}, "passed": {"default": 0}}))
    mail = Mail(account=MailAccount(provider="google", auth=PasswordAuth(_USER, _PASSWORD)),
                providers=[sender, store], templates=loader)
    api = StudioApi(mail, project=str(tmp_path), audit=AuditLog(tmp_path / "audit.jsonl"))
    api.sender, api.store = sender, store
    return api


def _everything(api):
    """Every reading endpoint's answer, as one JSON text."""
    return json.dumps([route(None) for (method, _path), route in api.routes.items() if method == "GET"])


# --- the API ----------------------------------------------------------------------------------------------------

def test_the_dashboard_and_accounts_describe_the_account_without_its_secret(studio):
    dashboard = studio.dashboard()
    assert dashboard["account"] == {"provider": "google", "user": _USER, "mechanism": "password", "problem": None}
    assert dashboard["counts"]["templates"] == 1
    assert dashboard["counts"]["triggers"] == 0
    assert dashboard["counts"]["subscriptions"] == 2
    assert dashboard["health"] == []
    assert dashboard["recent"] == []
    accounts = studio.accounts()
    assert accounts["servers"] == {"smtp_host": "smtp.gmail.com", "smtp_port": 465, "smtp_starttls": False,
                                   "imap_host": "imap.gmail.com"}
    assert {"google", "microsoft_graph", "file"} <= set(accounts["registered_providers"])
    assert _PASSWORD not in _everything(studio)


def test_an_account_without_credentials_or_servers_is_shown_with_its_problem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("mail_thunder_user", "mail_thunder_user_password", "mail_thunder_oauth2_access_token",
                 "mail_thunder_oauth2_refresh_token", "mail_thunder_mail_provider"):
        monkeypatch.delenv(name, raising=False)
    api = StudioApi(Mail(account=MailAccount(provider="smtp")), audit=AuditLog(tmp_path / "audit.jsonl"))
    assert "no credentials" in api.dashboard()["account"]["problem"]
    assert api.accounts()["servers"] is None
    bare = StudioApi(Mail(providers=[RecordingSender()]), audit=AuditLog(tmp_path / "audit.jsonl"))
    assert bare.accounts()["account"]["provider"] is None
    assert bare.accounts()["servers"] is None
    assert StudioApi(audit=AuditLog(tmp_path / "audit.jsonl")).mail.account.provider == "google"


def test_sending_from_studio_goes_through_mail_and_into_the_audit_log(studio):
    sent = studio.send({"to": "qa@example.com", "subject": "Hello", "text": "body", "cc": "", "html": None})
    assert (sent["sender"], sent["to"], sent["subject"]) == (_USER, ["qa@example.com"], "Hello")
    templated = studio.send({"to": "qa@example.com", "template": "report", "context": {"project": "API"}})
    assert templated["subject"] == "[API] done"
    assert len(studio.sender.sent) == 2
    with pytest.raises(MailThunderMessageException):
        studio.send({"subject": "nobody"})
    with pytest.raises(MailThunderStudioException, match="unknown message fields \\['attachments'\\]"):
        studio.send({"to": "qa@example.com", "attachments": ["/etc/passwd"]})
    with pytest.raises(MailThunderStudioException, match="must be a JSON object"):
        studio.send(["to"])
    dashboard = studio.dashboard()
    assert [entry["event"] for entry in dashboard["recent"]] == ["message_sent", "message_sent", "message_failed"]
    assert dashboard["health"][0]["state"] == "healthy"


def test_checking_the_account_asks_every_provider(studio, monkeypatch):
    def down():
        raise MailThunderConnectionException("cannot connect")

    monkeypatch.setattr(studio.store, "check", down)
    health = {status["provider"]: status["state"] for status in studio.check_accounts()["health"]}
    assert health == {"recording-sender": "healthy", "recording-store": "degraded"}


def test_templates_are_listed_and_rendered_without_sending(studio, tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "broken.json").write_text("{not json", encoding="utf-8")
    listed = studio.templates()
    assert listed["directories"] == [str(tmp_path / "templates")]
    by_name = {template["name"]: template for template in listed["templates"]}
    assert by_name["report"]["referenced_variables"] == ["passed", "project"]
    assert "not valid JSON" in by_name["broken"]["error"]
    assert studio.render_template({"name": "report", "context": {"project": "API", "passed": 3}}) == {
        "subject": "[API] done", "text": "Passed: 3", "html": "<b>3</b>"}
    with pytest.raises(TemplateNotFound):
        studio.render_template({"name": "absent"})
    assert studio.sender.sent == []


def test_triggers_are_shown_and_can_be_polled(studio):
    studio.mail.on("message_received", print, filter={"subject": "[TEST]"})
    studio.mail.watch("INBOX", start=False)
    shown = studio.triggers()
    assert len(shown["events"]) == 7
    assert shown["backends"][0]["folder"] == "INBOX"
    assert shown["subscriptions"][-1]["filter"] == {"subject": "[TEST]"}
    assert studio.poll_triggers() == {"emitted": 0, "events": []}
    studio.store.messages = {"2": stored_message("2", "[TEST] new"), **studio.store.messages}
    polled = studio.poll_triggers()
    assert polled["emitted"] == 1
    assert polled["events"][0]["message"]["subject"] == "[TEST] new"
    assert len(studio.mail.events.subscriptions) == 3


def test_the_policy_can_be_read_and_replaced(studio):
    assert studio.policies() == {"max_file_size": 25 * 1024 * 1024, "max_total_size": 25 * 1024 * 1024,
                                 "max_count": None, "allowed_extensions": None, "allowed_mime_types": None}
    replaced = studio.set_policy({"max_count": 2, "allowed_extensions": ["PDF", "html"], "max_file_size": None})
    assert replaced == {"max_file_size": None, "max_total_size": None, "max_count": 2,
                        "allowed_extensions": [".html", ".pdf"], "allowed_mime_types": None}
    assert studio.mail.policy == AttachmentPolicy(max_count=2, allowed_extensions={"pdf", "html"})
    with pytest.raises(MailThunderStudioException, match="unknown policy fields \\['max_size'\\]"):
        studio.set_policy({"max_size": 1})


def test_projects_logs_and_settings(studio, tmp_path):
    assert studio.projects()["layer"] is None
    assert "no mail layer" in studio.projects()["problem"]
    create_project_dir(project_path=str(tmp_path), parent_name="Demo")
    studio.project = str(tmp_path / "Demo")
    assert studio.projects() == {"problem": None, "layer": {
        "directory": str(tmp_path / "Demo" / "mail"), "config": True, "triggers": True, "templates": ["test_report"]}}
    (tmp_path / "mail.log").write_text("\n".join(f"line {number}" for number in range(300)), encoding="utf-8")
    studio.send({"to": "qa@example.com", "subject": "Logged", "text": "x"})
    logs = studio.logs({"lines": "2"})
    assert logs["lines"] == ["line 298", "line 299"]
    assert logs["log_file"] == str(tmp_path / "mail.log")
    assert [entry["subject"] for entry in logs["audit"]] == ["Logged"]
    assert len(studio.logs()["lines"]) == 200
    assert len(studio.logs({"lines": "many"})["lines"]) == 200
    assert len(studio.logs({"lines": 99999})["lines"]) == 300
    settings = studio.settings()
    assert settings["audit_file"] == str(tmp_path / "audit.jsonl")
    assert settings["project_directory"].endswith("Demo")
    assert settings["working_directory"] == str(tmp_path)
    assert settings["version"]


# --- the server -------------------------------------------------------------------------------------------------

@pytest.fixture
def server(studio):
    running = StudioServer(studio, "127.0.0.1", 0)
    running.serve_in_background()
    yield running
    running.stop()


def _request(server, path, method="GET", body=None, token=True, host=None):
    headers = {"Host": host} if host else {}
    if token:
        headers[SESSION_HEADER] = server.token if token is True else token
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}{path}", data=data, method=method,
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310 - the test's own server
            return response.status, response.read().decode("utf-8"), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8"), dict(error.headers)


def test_the_page_and_its_assets_are_served_with_strict_headers(server):
    status, body, headers = _request(server, "/", token=False)
    assert status == 200
    assert body == INDEX_HTML
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert "script-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Cache-Control"] == "no-store"
    assert _request(server, "/studio.js", token=False)[1] == STUDIO_JS
    assert _request(server, "/studio.css", token=False)[2]["Content-Type"] == "text/css; charset=utf-8"
    assert "innerHTML" not in STUDIO_JS
    assert "<script src=\"/studio.js\">" in INDEX_HTML
    assert server.url == f"http://127.0.0.1:{server.server_address[1]}/#token={server.token}"
    assert DEFAULT_PORT == 9947
    assert len(server.token) >= 32


def test_the_api_needs_the_token_and_the_right_host(server):
    assert _request(server, "/api/dashboard")[0] == 200
    for token in (False, "guess", server.token + "x"):
        status, body, _headers = _request(server, "/api/dashboard", token=token)
        assert status == 403
        assert "token" in json.loads(body)["message"]
    for path in ("/", "/api/dashboard"):
        status, body, _headers = _request(server, path, host="evil.example.com")
        assert status == 403
        assert "not the one" in json.loads(body)["message"]
    assert _request(server, "/api/dashboard", host=f"localhost:{server.server_address[1]}")[0] == 200
    assert _request(server, "/api/nothing")[0] == 404
    assert _request(server, "/api/send")[0] == 404
    assert _request(server, "/etc/passwd", token=False)[0] == 404


@pytest.mark.parametrize("host", ["", str(ipaddress.IPv4Address(0)), "::", "192.0.2.10", "studio.example.com"])
def test_studio_serves_only_loopback_addresses(studio, host):
    with pytest.raises(MailThunderStudioException, match="plain HTTP"):
        StudioServer(studio, host, 0)


def test_an_address_studio_does_not_have_is_not_echoed_back(server):
    status, body, _headers = _request(server, "/api/<script>alert(1)</script>")
    assert status == 404
    assert json.loads(body)["error"] == "NotFound"
    assert "script" not in body


def test_the_api_over_http(server, studio):
    status, body, _headers = _request(server, "/api/send", "POST",
                                      {"to": "qa@example.com", "subject": "報表", "text": "body"})
    assert status == 200
    assert json.loads(body)["subject"] == "報表"
    assert len(studio.sender.sent) == 1
    status, body, _headers = _request(server, "/api/send", "POST", {"subject": "nobody"})
    assert status == 400
    assert json.loads(body)["error"] == "MailThunderMessageException"
    status, body, _headers = _request(server, "/api/templates/render", "POST", {"name": "report", "context": ["x"]})
    assert status == 400
    assert "context is a mapping" in json.loads(body)["message"]
    assert json.loads(_request(server, "/api/logs?lines=1")[1])["audit"][0]["event"] == "message_failed"
    assert json.loads(_request(server, "/api/policies", "POST", {"max_count": 3})[1])["max_count"] == 3
    assert _PASSWORD not in _request(server, "/api/accounts")[1]


def test_a_request_body_must_be_small_json(server):
    port, token = server.server_address[1], server.token

    def post(data, length=None):
        headers = {SESSION_HEADER: token}
        if length is not None:
            headers["Content-Length"] = length
        request = urllib.request.Request(f"http://127.0.0.1:{port}/api/send", data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310 - the test's own server
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    assert post(b"{not json") == 400
    assert post(b"[1, 2]") == 400
    assert post(b"{}", "nonsense") == 400
    assert post(b"{}", str(2 * 1024 * 1024)) == 400


def test_start_studio_and_the_command_line(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAIL_THUNDER_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("MAIL_THUNDER_FILE_PROVIDER_DIR", str(tmp_path / "outbox"))
    running = start_studio(host="127.0.0.1", port=0, project=str(tmp_path))
    try:
        assert _request(running, "/api/settings")[0] == 200
        assert running.api.project == str(tmp_path)
    finally:
        running.stop()
    create_project_dir(project_path=str(tmp_path), parent_name="Demo")
    created = studio_main.create_server(["--host", "127.0.0.1", "--port", "0", "--no-browser",
                                         "--project", str(tmp_path / "Demo")])
    try:
        assert created.open_browser is False
        assert created.api.mail.account.provider == "file"
        assert created.api.projects()["layer"]["templates"] == ["test_report"]
    finally:
        created.server_close()
    plain = studio_main.create_server(["--host", "127.0.0.1", "--port", "0"])
    try:
        assert plain.open_browser is True
        assert plain.api.project is None
    finally:
        plain.server_close()
