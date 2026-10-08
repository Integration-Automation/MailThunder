"""OAuth2 (XOAUTH2) login: settings, token refresh and cache, and the SMTP / IMAP exchanges against fake servers."""
import base64
import imaplib
import io
import json
import smtplib
import socketserver
import ssl
import threading
import urllib.error

import pytest

from je_mail_thunder.imap import imap_wrapper
from je_mail_thunder.imap.imap_wrapper import IMAPWrapper
from je_mail_thunder.smtp import smtp_wrapper
from je_mail_thunder.smtp.smtp_wrapper import SMTPClientMixin, SMTPStartTLSWrapper, SMTPWrapper
from je_mail_thunder.utils.exception.exceptions import MailThunderOAuth2Exception
from je_mail_thunder.utils.oauth2 import oauth2
from je_mail_thunder.utils.oauth2.oauth2 import (
    OAUTH2_PROVIDERS,
    OAuth2Settings,
    OAuth2TokenCache,
    refresh_access_token,
    xoauth2_string,
)
from je_mail_thunder.utils.save_mail_user_content.credentials import (
    configured_oauth2_provider,
    oauth2_settings_from_environ,
    resolve_oauth2_settings,
)

_USER = "someone@example.com"
_TOKEN = "access-token"
_REFRESH = "1//refresh-token"


def _settings(**overrides):
    values = {"user": _USER, "client_id": "client-1", "refresh_token": _REFRESH}
    values.update(overrides)
    return OAuth2Settings(**values)


class _Post:
    """A fake token endpoint: records each form and answers from a list."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, url, form, timeout):
        self.calls.append((url, dict(form), timeout))
        return self.answers.pop(0)


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


# --- settings ---------------------------------------------------------------------------------------------------

def test_the_xoauth2_string_is_the_sasl_format():
    assert xoauth2_string("a@b.c", "tok") == "user=a@b.c\x01auth=Bearer tok\x01\x01"


def test_the_provider_presets():
    assert set(OAUTH2_PROVIDERS) == {"google", "microsoft"}
    google, microsoft = OAUTH2_PROVIDERS["google"], OAUTH2_PROVIDERS["microsoft"]
    assert (google.smtp_host, google.smtp_port, google.smtp_starttls, google.imap_host) == (
        "smtp.gmail.com", 465, False, "imap.gmail.com")
    assert (microsoft.smtp_host, microsoft.smtp_port, microsoft.smtp_starttls, microsoft.imap_host) == (
        "smtp.office365.com", 587, True, "outlook.office365.com")
    assert "offline_access" in microsoft.scope


def test_endpoints_per_provider_and_tenant():
    assert _settings().endpoint == "https://oauth2.googleapis.com/token"
    assert _settings(provider="microsoft", tenant="contoso.onmicrosoft.com").endpoint == (
        "https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/token")
    assert _settings(provider="other", token_url="https://id.example.com/token").endpoint == (
        "https://id.example.com/token")


@pytest.mark.parametrize(("overrides", "message"), [
    ({"user": ""}, "needs the mail user"),
    ({"client_id": None}, "needs an access_token, or a client_id and a refresh_token"),
    ({"refresh_token": None}, "needs an access_token, or a client_id and a refresh_token"),
    ({"provider": "yahoo"}, "unknown OAuth2 provider 'yahoo'"),
    ({"tenant": "common/../evil"}, "invalid OAuth2 tenant"),
    ({"token_url": "http://id.example.com/token"}, "must use https"),
    ({"client_id": 12345}, "'client_id' must be a string"),
])
def test_invalid_settings_are_refused(overrides, message):
    with pytest.raises(MailThunderOAuth2Exception, match=message):
        _settings(**overrides)


def test_an_access_token_alone_is_enough_and_secrets_stay_out_of_repr():
    settings = OAuth2Settings(user=_USER, access_token=_TOKEN, client_secret="s3cret", refresh_token=_REFRESH)
    text = repr(settings)
    for secret in (_TOKEN, "s3cret", _REFRESH):
        assert secret not in text
    assert _USER in text


# --- refresh and cache ------------------------------------------------------------------------------------------

def test_refresh_posts_the_form_and_returns_the_token_with_its_expiry():
    post = _Post({"access_token": _TOKEN, "expires_in": 3599, "token_type": "Bearer"})
    clock = _Clock()
    token = refresh_access_token(_settings(client_secret="s3cret"), post, clock)
    assert token.value == _TOKEN
    assert token.expires_at == 1000.0 + 3599
    url, form, timeout = post.calls[0]
    assert url == "https://oauth2.googleapis.com/token"
    assert form == {"grant_type": "refresh_token", "client_id": "client-1", "refresh_token": _REFRESH,
                    "client_secret": "s3cret", "scope": "https://mail.google.com/"}
    assert timeout == oauth2.TOKEN_TIMEOUT_SECONDS


def test_a_custom_endpoint_sends_only_its_own_scope():
    post = _Post({"access_token": _TOKEN})
    refresh_access_token(_settings(provider="x", token_url="https://id.example.com/t"), post, _Clock())
    assert "scope" not in post.calls[0][1]
    refresh_access_token(_settings(provider="x", token_url="https://id.example.com/t", scope="mail"),
                         _Post({"access_token": _TOKEN}), _Clock())


def test_an_answer_without_a_token_names_the_error_but_not_the_secrets():
    post = _Post({"error": "invalid_grant", "error_description": "Token has been expired or revoked."})
    settings = _settings(client_secret="s3cret")
    clock = _Clock()
    with pytest.raises(MailThunderOAuth2Exception) as raised:
        refresh_access_token(settings, post, clock)
    message = str(raised.value)
    assert "invalid_grant: Token has been expired or revoked." in message
    assert _REFRESH not in message
    assert "s3cret" not in message


def test_the_cache_reuses_a_fresh_token_and_refreshes_near_expiry():
    clock = _Clock()
    post = _Post({"access_token": "first", "expires_in": 600}, {"access_token": "second", "expires_in": 600})
    cache = OAuth2TokenCache(post, clock)
    settings = _settings()
    assert cache.access_token(settings) == "first"
    clock.now += 600 - oauth2.REFRESH_MARGIN_SECONDS - 1
    assert cache.access_token(settings) == "first"
    clock.now += 2
    assert cache.access_token(settings) == "second"
    assert len(post.calls) == 2
    cache.clear()
    with pytest.raises(IndexError):
        cache.access_token(settings)


def test_a_given_access_token_is_used_without_a_refresh():
    post = _Post()
    assert OAuth2TokenCache(post, _Clock()).access_token(OAuth2Settings(user=_USER, access_token=_TOKEN)) == _TOKEN
    assert post.calls == []


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def test_post_form_sends_an_https_form_and_reads_json(monkeypatch):
    seen = {}

    def urlopen(request, timeout):
        seen.update(url=request.full_url, body=request.data, method=request.get_method(), timeout=timeout,
                    content_type=request.get_header("Content-type"))
        return _Response(json.dumps({"access_token": _TOKEN}).encode("utf-8"))

    monkeypatch.setattr(oauth2.urllib.request, "urlopen", urlopen)
    assert oauth2._post_form("https://id.example.com/t", {"a": "1 2"}, 5) == {"access_token": _TOKEN}
    assert seen == {"url": "https://id.example.com/t", "body": b"a=1+2", "method": "POST", "timeout": 5,
                    "content_type": "application/x-www-form-urlencoded"}
    with pytest.raises(MailThunderOAuth2Exception, match="must use https"):
        oauth2._post_form("http://id.example.com/t", {}, 5)


def test_post_form_turns_http_and_network_errors_into_oauth2_errors(monkeypatch):
    def refused(request, timeout):
        body = io.BytesIO(json.dumps({"error": "invalid_client"}).encode("utf-8"))
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, body)

    monkeypatch.setattr(oauth2.urllib.request, "urlopen", refused)
    with pytest.raises(MailThunderOAuth2Exception, match=r"HTTP 401\): invalid_client"):
        oauth2._post_form("https://id.example.com/t", {"refresh_token": _REFRESH}, 5)

    def unreachable(request, timeout):
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(oauth2.urllib.request, "urlopen", unreachable)
    with pytest.raises(MailThunderOAuth2Exception, match="could not be used: URLError"):
        oauth2._post_form("https://id.example.com/t", {}, 5)


# --- where the settings come from -------------------------------------------------------------------------------

_ENV_NAMES = ("mail_thunder_user", "mail_thunder_user_password") + tuple(
    f"mail_thunder_oauth2_{name}" for name in ("provider", "client_id", "client_secret", "refresh_token",
                                                 "access_token", "tenant", "token_url", "scope"))


@pytest.fixture
def clean_place(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _write_content(directory, content):
    (directory / "mail_thunder_content.json").write_text(json.dumps(content), encoding="utf-8")


def test_no_oauth2_settings_anywhere(clean_place):
    assert resolve_oauth2_settings() is None
    assert configured_oauth2_provider() is None


def test_the_content_file_block_wins_and_takes_the_file_user(clean_place, monkeypatch):
    _write_content(clean_place, {"user": _USER, "oauth2": {"provider": "microsoft", "client_id": "c",
                                                           "refresh_token": _REFRESH}})
    monkeypatch.setenv("mail_thunder_oauth2_access_token", "env-token")
    settings = resolve_oauth2_settings()
    assert (settings.user, settings.provider, settings.refresh_token) == (_USER, "microsoft", _REFRESH)
    assert configured_oauth2_provider() is OAUTH2_PROVIDERS["microsoft"]


def test_the_environment_is_used_without_a_file_block(clean_place, monkeypatch):
    _write_content(clean_place, {"user": "file@example.com", "password": "p"})
    monkeypatch.setenv("mail_thunder_user", _USER)
    monkeypatch.setenv("mail_thunder_oauth2_client_id", "c")
    monkeypatch.setenv("mail_thunder_oauth2_refresh_token", _REFRESH)
    monkeypatch.setenv("mail_thunder_oauth2_provider", "google")
    settings = resolve_oauth2_settings()
    assert (settings.user, settings.client_id, settings.provider) == (_USER, "c", "google")


def test_environment_without_a_token_means_no_oauth2():
    assert oauth2_settings_from_environ({"mail_thunder_user": _USER, "mail_thunder_oauth2_client_id": "c"}) is None


def test_invalid_settings_raise_but_do_not_choose_a_server(clean_place):
    _write_content(clean_place, {"user": _USER, "oauth2": {"provider": "microsoft", "refresh_token": _REFRESH}})
    with pytest.raises(MailThunderOAuth2Exception):
        resolve_oauth2_settings()
    assert configured_oauth2_provider() is None
    _write_content(clean_place, {"user": _USER, "oauth2": "not an object"})
    with pytest.raises(MailThunderOAuth2Exception, match="must be a JSON object"):
        resolve_oauth2_settings()


def test_a_custom_endpoint_keeps_the_default_servers(clean_place):
    _write_content(clean_place, {"user": _USER, "oauth2": {"provider": "microsoft", "access_token": _TOKEN,
                                                           "token_url": "https://id.example.com/t"}})
    assert configured_oauth2_provider() is None


# --- fake servers -----------------------------------------------------------------------------------------------

class _FakeServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, handler, accept):
        super().__init__(("127.0.0.1", 0), handler)
        self.accept = accept
        self.received = []

    def __enter__(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.shutdown()
        self.server_close()

    @property
    def port(self):
        return self.server_address[1]


_ERROR_CHALLENGE = base64.b64encode(b'{"status":"401","schemes":"Bearer","scope":"https://mail.google.com/"}')


class _SMTPHandler(socketserver.StreamRequestHandler):
    """EHLO, AUTH XOAUTH2 (accepted or refused with an error challenge) and QUIT."""

    def _send(self, line):
        self.wfile.write(line.encode("ascii") + b"\r\n")

    def handle(self):
        self._send("220 fake ESMTP")
        for raw in self.rfile:
            line = raw.decode("ascii").strip()
            verb = line.split(" ")[0].upper()
            if verb == "EHLO":
                self._send("250-fake")
                self._send("250 AUTH XOAUTH2")
            elif verb == "AUTH":
                self.server.received.append(base64.b64decode(line.split(" ")[2]).decode("utf-8"))
                if self.server.accept:
                    self._send("235 2.7.0 Accepted")
                else:
                    self._send("334 " + _ERROR_CHALLENGE.decode("ascii"))
                    self.server.received.append(self.rfile.readline().decode("ascii").strip())
                    self._send("535 5.7.8 Username and Password not accepted")
            elif verb == "QUIT":
                self._send("221 bye")
                return
            else:
                self._send("250 OK")


class _PlainSMTP(SMTPClientMixin, smtplib.SMTP):
    """The mixin on plain SMTP, so the exchange can be checked without TLS."""

    def __init__(self, port):
        super().__init__("127.0.0.1", port)
        self.login_state = False


def test_smtp_xoauth2_login_sends_the_sasl_string():
    with _FakeServer(_SMTPHandler, accept=True) as server:
        client = _PlainSMTP(server.port)
        client.oauth2_login(_USER, _TOKEN)
        client.quit()
    assert server.received == [xoauth2_string(_USER, _TOKEN)]


def test_smtp_refused_token_answers_the_challenge_empty_and_raises():
    with _FakeServer(_SMTPHandler, accept=False) as server:
        client = _PlainSMTP(server.port)
        with pytest.raises(smtplib.SMTPAuthenticationError):
            client.oauth2_login(_USER, _TOKEN)
        client.quit()
    assert server.received == [xoauth2_string(_USER, _TOKEN), ""]


def test_smtp_try_to_login_prefers_oauth2(clean_place, monkeypatch):
    _write_content(clean_place, {"user": _USER, "password": "unused", "oauth2": {"access_token": _TOKEN}})
    with _FakeServer(_SMTPHandler, accept=True) as server:
        client = _PlainSMTP(server.port)
        client.login = lambda *args: pytest.fail("the password login must not run")
        assert client.try_to_login_with_env_or_content() is True
        assert client.login_state is True
        client.quit()
    assert server.received == [xoauth2_string(_USER, _TOKEN)]


def test_smtp_try_to_login_reports_bad_oauth2_settings(clean_place):
    _write_content(clean_place, {"user": _USER, "oauth2": {"provider": "google", "client_id": "c"}})
    client = SMTPWrapper.__new__(SMTPWrapper)
    assert client.try_to_login_with_env_or_content() is False


class _IMAPHandler(socketserver.StreamRequestHandler):
    """CAPABILITY, AUTHENTICATE XOAUTH2 (accepted or refused) and LOGOUT."""

    def _send(self, line):
        self.wfile.write(line.encode("ascii") + b"\r\n")

    def _authenticate(self, tag):
        self._send("+ ")
        self.server.received.append(base64.b64decode(self.rfile.readline().strip()).decode("utf-8"))
        if self.server.accept:
            self._send(f"{tag} OK AUTHENTICATE completed")
            return
        self._send("+ " + _ERROR_CHALLENGE.decode("ascii"))
        self.server.received.append(self.rfile.readline().decode("ascii").strip())
        self._send(f"{tag} NO [AUTHENTICATIONFAILED] Invalid credentials")

    def handle(self):
        self._send("* OK fake IMAP4rev1 ready")
        for raw in self.rfile:
            tag, _, rest = raw.decode("ascii").strip().partition(" ")
            command = rest.split(" ")[0].upper()
            if command == "CAPABILITY":
                self._send("* CAPABILITY IMAP4rev1 AUTH=XOAUTH2")
                self._send(f"{tag} OK CAPABILITY completed")
            elif command == "AUTHENTICATE":
                self._authenticate(tag)
            elif command == "LOGOUT":
                self._send("* BYE")
                self._send(f"{tag} OK LOGOUT completed")
                return
            else:
                self._send(f"{tag} BAD unknown")


def _imap_login(server, user, token):
    client = imaplib.IMAP4("127.0.0.1", server.port)
    try:
        return IMAPWrapper.oauth2_login(client, user, token)
    finally:
        client.logout()


def test_imap_xoauth2_login_sends_the_sasl_string():
    with _FakeServer(_IMAPHandler, accept=True) as server:
        status, _ = _imap_login(server, _USER, _TOKEN)
    assert status == "OK"
    assert server.received == [xoauth2_string(_USER, _TOKEN)]


def test_imap_refused_token_answers_the_challenge_empty_and_raises():
    with _FakeServer(_IMAPHandler, accept=False) as server:
        with pytest.raises(imaplib.IMAP4.error, match="AUTHENTICATIONFAILED"):
            _imap_login(server, _USER, _TOKEN)
    assert server.received == [xoauth2_string(_USER, _TOKEN), ""]


def test_imap_try_to_login_prefers_oauth2_and_logs_bad_settings(clean_place):
    _write_content(clean_place, {"user": _USER, "password": "unused", "oauth2": {"access_token": _TOKEN}})
    imap = IMAPWrapper.__new__(IMAPWrapper)
    calls = []
    imap.oauth2_login = lambda user, token: calls.append((user, token))
    imap.login = lambda *args: pytest.fail("the password login must not run")
    assert imap.try_to_login_with_env_or_content() is None
    assert calls == [(_USER, _TOKEN)]
    _write_content(clean_place, {"user": _USER, "oauth2": {"client_id": "c"}})
    assert imap.try_to_login_with_env_or_content() is None


# --- STARTTLS and the default clients ---------------------------------------------------------------------------

def test_starttls_is_refused_when_the_server_does_not_offer_it():
    with _FakeServer(_SMTPHandler, accept=True) as server:
        with pytest.raises(smtplib.SMTPNotSupportedError):
            SMTPStartTLSWrapper("127.0.0.1", server.port)


def test_starttls_upgrades_with_a_verifying_context(monkeypatch):
    contexts = []
    monkeypatch.setattr(smtplib.SMTP, "connect", lambda self, host, port, source_address=None: (220, b"ok"))
    monkeypatch.setattr(smtplib.SMTP, "starttls", lambda self, context=None: contexts.append(context))
    client = SMTPStartTLSWrapper()
    assert client.login_state is False
    assert isinstance(client, smtplib.SMTP)
    assert not isinstance(client, smtplib.SMTP_SSL)
    (context,) = contexts
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED


@pytest.mark.parametrize(("provider", "expected"), [
    (None, ("SMTPWrapper", (), "IMAPWrapper", ())),
    ("google", ("SMTPWrapper", ("smtp.gmail.com", 465), "IMAPWrapper", ("imap.gmail.com",))),
    ("microsoft", ("SMTPStartTLSWrapper", ("smtp.office365.com", 587), "IMAPWrapper", ("outlook.office365.com",))),
])
def test_the_default_clients_follow_the_oauth2_provider(provider, expected, monkeypatch):
    built = []

    def recorder(name):
        return lambda *args: built.append((name, args)) or name

    monkeypatch.setattr(smtp_wrapper, "SMTPWrapper", recorder("SMTPWrapper"))
    monkeypatch.setattr(smtp_wrapper, "SMTPStartTLSWrapper", recorder("SMTPStartTLSWrapper"))
    monkeypatch.setattr(imap_wrapper, "IMAPWrapper", recorder("IMAPWrapper"))
    preset = OAUTH2_PROVIDERS.get(provider) if provider else None
    monkeypatch.setattr(smtp_wrapper, "configured_oauth2_provider", lambda: preset)
    monkeypatch.setattr(imap_wrapper, "configured_oauth2_provider", lambda: preset)
    smtp_wrapper.default_smtp_client()
    imap_wrapper.default_imap_client()
    assert built == [(expected[0], expected[1]), (expected[2], expected[3])]
