"""
The SMTP and IMAP providers: when they connect, how they log in, what they send to the server, and which
MailThunder exception each failure becomes. No server is contacted except a fake SMTP server on localhost.
"""
import imaplib
import smtplib
import socketserver
import threading

import pytest

from je_mail_thunder.auth.password import PasswordAuth
from je_mail_thunder.auth.xoauth2 import XOAUTH2Auth
from je_mail_thunder.core.account import MailAccount, MailServers
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers import imap as imap_provider
from je_mail_thunder.providers import smtp as smtp_provider
from je_mail_thunder.providers.base import MailProvider, MailSender, MailStore
from je_mail_thunder.providers.imap import IMAPProvider, mailbox_name
from je_mail_thunder.providers.registry import (
    create_providers,
    register_provider,
    registered_providers,
    smtp_and_imap_providers,
)
from je_mail_thunder.providers.session import IDLE_CHECK_SECONDS, SOCKET_TIMEOUT_SECONDS
from je_mail_thunder.providers.smtp import SMTPProvider
from je_mail_thunder.smtp.smtp_wrapper import SMTPClientMixin
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderAuthenticationException,
    MailThunderConnectionException,
    MailThunderProviderException,
    MailThunderSendException,
)
from je_mail_thunder.utils.oauth2.oauth2 import OAuth2Settings
from mail_fakes import IMAP_ABORT, IMAP_ERROR, FakeIMAPClient, FakeSMTPClient

_USER = "someone@example.com"
_PASSWORD = "p4ss-word-secret"
_AUTH = PasswordAuth(_USER, _PASSWORD)
_ACCOUNT = MailAccount(provider="google", auth=_AUTH)
_MESSAGE = MailMessage(to="reader@example.com", sender=_USER, subject="Hello", text="body")


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture()
def smtp_clients(monkeypatch):
    """Every SMTP wrapper the provider builds, in order, as ``(wrapper name, client)``."""
    built = []

    def recorder(name):
        def build(host, port):
            client = FakeSMTPClient(host, port)
            built.append((name, client))
            return client
        return build

    monkeypatch.setattr(smtp_provider, "SMTPWrapper", recorder("SMTPWrapper"))
    monkeypatch.setattr(smtp_provider, "SMTPStartTLSWrapper", recorder("SMTPStartTLSWrapper"))
    return built


@pytest.fixture()
def imap_clients(monkeypatch):
    """Every IMAP wrapper the provider builds, in order."""
    built = []

    def build(host):
        client = FakeIMAPClient(host)
        built.append(client)
        return client

    monkeypatch.setattr(imap_provider, "IMAPWrapper", build)
    return built


@pytest.fixture()
def no_credentials(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("mail_thunder_user", "mail_thunder_user_password", "mail_thunder_oauth2_refresh_token",
                 "mail_thunder_oauth2_access_token"):
        monkeypatch.delenv(name, raising=False)


# --- the interfaces and the registry ----------------------------------------------------------------------------

def test_the_providers_fill_their_roles():
    assert issubclass(SMTPProvider, MailSender) and not issubclass(SMTPProvider, MailStore)
    assert issubclass(IMAPProvider, MailStore) and not issubclass(IMAPProvider, MailSender)
    assert issubclass(MailSender, MailProvider) and issubclass(MailStore, MailProvider)
    with pytest.raises(TypeError):
        MailSender()  # pylint: disable=abstract-class-instantiated  # reason: the point of the test


def test_the_known_accounts_get_an_smtp_sender_and_an_imap_store():
    assert set(registered_providers()) >= {"google", "microsoft", "smtp"}
    for name in ("google", "gmail", "microsoft", "smtp"):
        sender, store = create_providers(MailAccount(provider=name, auth=_AUTH))
        assert isinstance(sender, SMTPProvider) and isinstance(store, IMAPProvider)


def test_an_unknown_provider_names_the_known_ones():
    with pytest.raises(MailThunderProviderException, match="unknown mail provider 'nowhere'.*google"):
        create_providers(MailAccount(provider="nowhere"))


def test_a_registered_factory_serves_its_name(monkeypatch):
    from je_mail_thunder.providers import registry
    monkeypatch.setattr(registry, "_factories", dict(registry._factories))
    seen = []

    def factory(account):
        seen.append(account)
        return [SMTPProvider(account)]

    register_provider(" Example ", factory)
    account = MailAccount(provider="EXAMPLE", auth=_AUTH)
    (sender,) = create_providers(account)
    assert isinstance(sender, SMTPProvider) and seen == [account]
    assert "example" in registered_providers()
    for name, bad_factory in (("", factory), (None, factory), ("x", "not callable")):
        with pytest.raises(MailThunderProviderException):
            register_provider(name, bad_factory)
    assert smtp_and_imap_providers(account)[0].name == "smtp"


def test_a_provider_needs_an_account_or_a_client():
    for provider in (SMTPProvider, IMAPProvider):
        with pytest.raises(MailThunderProviderException, match="needs an account or a connected client"):
            provider()


# --- the account's servers --------------------------------------------------------------------------------------

def test_the_presets_and_their_ports():
    google = MailAccount(provider="Gmail").resolved_servers
    microsoft = MailAccount(provider="microsoft").resolved_servers
    assert (google.smtp_host, google.port, google.smtp_starttls, google.imap_host) == (
        "smtp.gmail.com", 465, False, "imap.gmail.com")
    assert (microsoft.smtp_host, microsoft.port, microsoft.smtp_starttls, microsoft.imap_host) == (
        "smtp.office365.com", 587, True, "outlook.office365.com")
    assert MailServers(smtp_host="mail.example.com").port == 465
    assert MailServers(smtp_host="mail.example.com", smtp_starttls=True).port == 587
    assert MailServers(smtp_host="mail.example.com", smtp_port=2525).port == 2525


def test_a_generic_account_needs_its_servers():
    with pytest.raises(MailThunderProviderException, match="has no known servers"):
        _ = MailAccount(provider="smtp").resolved_servers
    servers = MailServers(smtp_host="mail.example.com", imap_host="imap.example.com")
    assert MailAccount(provider="smtp", servers=servers).resolved_servers is servers
    for name in ("", None, 5):
        with pytest.raises(MailThunderProviderException):
            MailAccount(provider=name)


def test_an_account_without_credentials_says_where_to_put_them(no_credentials):
    with pytest.raises(MailThunderAuthenticationException, match="mail_thunder_content.json"):
        MailAccount().authentication()
    assert MailAccount(auth=_AUTH).authentication() is _AUTH


# --- SMTP -------------------------------------------------------------------------------------------------------

def test_smtp_connects_on_first_use_and_keeps_the_connection(smtp_clients):
    provider = SMTPProvider(_ACCOUNT)
    assert smtp_clients == []
    provider.send(_MESSAGE)
    provider.send(_MESSAGE)
    ((wrapper, client),) = smtp_clients
    assert (wrapper, client.host, client.port) == ("SMTPWrapper", "smtp.gmail.com", 465)
    assert client.calls == [("login", _USER, _PASSWORD), ("send_message",), ("send_message",)]
    assert client.sent[0]["Subject"] == "Hello"


def test_smtp_uses_starttls_and_xoauth2_when_the_account_says_so(smtp_clients):
    auth = XOAUTH2Auth(OAuth2Settings(user=_USER, provider="microsoft", access_token="token"))
    SMTPProvider(MailAccount(provider="microsoft", auth=auth)).send(_MESSAGE)
    ((wrapper, client),) = smtp_clients
    assert (wrapper, client.host, client.port) == ("SMTPStartTLSWrapper", "smtp.office365.com", 587)
    assert client.calls[0] == ("oauth2_login", _USER, "token")


def test_smtp_close_quits_and_the_next_send_reconnects(smtp_clients):
    with SMTPProvider(_ACCOUNT) as provider:
        provider.send(_MESSAGE)
    provider.close()
    assert smtp_clients[0][1].calls[-1] == ("quit",)
    provider.send(_MESSAGE)
    assert len(smtp_clients) == 2


def test_smtp_asks_an_idle_connection_for_a_sign_of_life(smtp_clients):
    clock = _Clock()
    provider = SMTPProvider(_ACCOUNT, clock=clock)
    provider.send(_MESSAGE)
    clock.now += IDLE_CHECK_SECONDS - 1
    provider.send(_MESSAGE)
    first = smtp_clients[0][1]
    assert ("noop",) not in first.calls
    clock.now += IDLE_CHECK_SECONDS + 1
    provider.send(_MESSAGE)
    assert first.calls[-2:] == [("noop",), ("send_message",)] and len(smtp_clients) == 1


@pytest.mark.parametrize("dead", ["raises", "bad status"])
def test_smtp_replaces_a_connection_the_server_dropped_while_idle(dead, smtp_clients):
    clock = _Clock()
    provider = SMTPProvider(_ACCOUNT, clock=clock)
    provider.send(_MESSAGE)
    first = smtp_clients[0][1]
    if dead == "raises":
        first.fail["noop"] = smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
    else:
        first.noop_status = 421
    clock.now += IDLE_CHECK_SECONDS + 1
    provider.send(_MESSAGE)
    assert first.calls[-1] == ("close",)
    assert len(first.sent) == 1 and len(smtp_clients[1][1].sent) == 1


def test_smtp_does_not_connect_without_credentials(smtp_clients, no_credentials):
    with pytest.raises(MailThunderAuthenticationException, match="no credentials"):
        SMTPProvider(MailAccount()).send(_MESSAGE)
    assert smtp_clients == []


def test_smtp_cannot_connect(monkeypatch):
    def unreachable(_host, _port):
        raise OSError("network is unreachable")

    monkeypatch.setattr(smtp_provider, "SMTPWrapper", unreachable)
    with pytest.raises(MailThunderConnectionException, match="cannot connect to the smtp server"):
        SMTPProvider(_ACCOUNT).send(_MESSAGE)


def test_smtp_without_a_host_is_a_provider_error():
    account = MailAccount(provider="smtp", auth=_AUTH, servers=MailServers(imap_host="imap.example.com"))
    with pytest.raises(MailThunderProviderException, match="no SMTP server"):
        SMTPProvider(account).send(_MESSAGE)


def test_smtp_a_refused_login_is_an_authentication_error_and_hangs_up(monkeypatch):
    client = FakeSMTPClient()
    client.fail["login"] = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
    monkeypatch.setattr(smtp_provider, "SMTPWrapper", lambda host, port: client)
    provider = SMTPProvider(_ACCOUNT)
    with pytest.raises(MailThunderAuthenticationException, match="the smtp server refused the login") as raised:
        provider.send(_MESSAGE)
    assert _PASSWORD not in str(raised.value)
    assert client.calls[-1] == ("quit",) and client.sent == []


def test_smtp_a_connection_lost_during_the_login_is_a_connection_error(monkeypatch):
    client = FakeSMTPClient()
    client.fail["login"] = smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
    monkeypatch.setattr(smtp_provider, "SMTPWrapper", lambda host, port: client)
    with pytest.raises(MailThunderConnectionException, match="lost while the login"):
        SMTPProvider(_ACCOUNT).send(_MESSAGE)
    assert client.calls[-1] == ("close",)


def test_smtp_a_login_that_fails_for_any_reason_does_not_keep_the_connection(smtp_clients):
    token_errors = iter([MailThunderAuthenticationException("the token endpoint refused the refresh")])

    class _Auth(PasswordAuth):
        def login(self, client):
            for error in token_errors:
                raise error
            super().login(client)

    provider = SMTPProvider(MailAccount(auth=_Auth(_USER, _PASSWORD)))
    with pytest.raises(MailThunderAuthenticationException, match="token endpoint"):
        provider.send(_MESSAGE)
    assert smtp_clients[0][1].calls == [("quit",)]
    provider.send(_MESSAGE)
    assert len(smtp_clients) == 2 and len(smtp_clients[1][1].sent) == 1


def test_smtp_every_recipient_refused(smtp_clients):
    provider = SMTPProvider(_ACCOUNT)
    provider.send(_MESSAGE)
    client = smtp_clients[0][1]
    client.fail["send_message"] = smtplib.SMTPRecipientsRefused({"reader@example.com": (550, b"no such user")})
    with pytest.raises(MailThunderSendException, match="refused every recipient") as raised:
        provider.send(_MESSAGE)
    assert raised.value.refused == {"reader@example.com": (550, b"no such user")}


def test_smtp_some_recipients_refused_is_reported_after_the_send(smtp_clients):
    provider = SMTPProvider(_ACCOUNT)
    provider.send(_MESSAGE)
    client = smtp_clients[0][1]
    client.refused = {"gone@example.com": (550, b"no such user")}
    with pytest.raises(MailThunderSendException, match="was sent, but the smtp server refused 1") as raised:
        provider.send(_MESSAGE)
    assert raised.value.refused == {"gone@example.com": (550, b"no such user")}
    assert len(client.sent) == 2


def test_smtp_a_refused_message_keeps_the_connection(smtp_clients):
    provider = SMTPProvider(_ACCOUNT)
    provider.send(_MESSAGE)
    client = smtp_clients[0][1]
    client.fail["send_message"] = smtplib.SMTPDataError(552, b"message too large")
    with pytest.raises(MailThunderSendException, match="the smtp server refused the message") as raised:
        provider.send(_MESSAGE)
    assert raised.value.refused == {}
    provider.send(_MESSAGE)
    assert len(smtp_clients) == 1


@pytest.mark.parametrize("error", [
    smtplib.SMTPServerDisconnected("Connection unexpectedly closed"), ConnectionResetError("reset"),
])
def test_smtp_a_connection_lost_while_sending_is_not_sent_again(error, smtp_clients):
    provider = SMTPProvider(_ACCOUNT)
    provider.send(_MESSAGE)
    first = smtp_clients[0][1]
    first.fail["send_message"] = error
    with pytest.raises(MailThunderConnectionException, match="lost while the message"):
        provider.send(_MESSAGE)
    assert len(smtp_clients) == 1 and first.calls[-1] == ("close",)
    provider.send(_MESSAGE)
    assert len(smtp_clients) == 2


def test_smtp_a_given_client_is_used_as_it_is_and_never_closed(smtp_clients):
    client = FakeSMTPClient()
    clock = _Clock()
    provider = SMTPProvider(client=client, clock=clock)
    clock.now += IDLE_CHECK_SECONDS + 1
    provider.send(_MESSAGE)
    provider.close()
    provider.send(_MESSAGE)
    assert client.calls == [("send_message",), ("send_message",)] and smtp_clients == []
    client.fail["send_message"] = smtplib.SMTPServerDisconnected("gone")
    with pytest.raises(MailThunderConnectionException):
        provider.send(_MESSAGE)
    assert ("close",) not in client.calls and ("quit",) not in client.calls


class _SMTPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), _SMTPHandler)
        self.envelopes = []

    def __enter__(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.shutdown()
        self.server_close()


class _SMTPHandler(socketserver.StreamRequestHandler):
    """Enough SMTP to take one message: EHLO, MAIL, RCPT, DATA, NOOP, QUIT."""

    def _send(self, line):
        self.wfile.write(line.encode("ascii") + b"\r\n")

    def _data(self):
        self._send("354 go ahead")
        lines = []
        for raw in self.rfile:
            if raw == b".\r\n":
                break
            lines.append(raw)
        return b"".join(lines)

    def handle(self):
        self._send("220 fake ESMTP")
        sender, recipients = None, []
        for raw in self.rfile:
            line = raw.decode("ascii").strip()
            verb = line.split(":")[0].split(" ")[0].upper()
            if verb == "EHLO":
                self._send("250 fake")
            elif verb == "MAIL":
                sender = line.split(":", 1)[1].split(" ")[0].strip("<>")
                self._send("250 OK")
            elif verb == "RCPT":
                recipients.append(line.split(":", 1)[1].strip("<>"))
                self._send("250 OK")
            elif verb == "DATA":
                self.server.envelopes.append((sender, recipients, self._data()))
                self._send("250 queued")
            elif verb == "QUIT":
                self._send("221 bye")
                return
            else:
                self._send("250 OK")


class _PlainSMTP(SMTPClientMixin, smtplib.SMTP):
    """The wrapper's mixin on plain SMTP, so the exchange can be checked without TLS."""

    def __init__(self, port):
        super().__init__("127.0.0.1", port)
        self.login_state = False


def test_smtp_what_reaches_the_server(tmp_path):
    report = tmp_path / "report.txt"
    report.write_bytes(b"numbers")
    message = MailMessage(to="reader@example.com", cc="copy@example.com", bcc="hidden@example.com", sender=_USER,
                          subject="Nightly 報表", text="plain", html="<b>rich</b>", attachments=[report])
    with _SMTPServer() as server:
        client = _PlainSMTP(server.server_address[1])
        SMTPProvider(client=client).send(message)
        client.quit()
    ((sender, recipients, data),) = server.envelopes
    assert sender == _USER
    assert sorted(recipients) == ["copy@example.com", "hidden@example.com", "reader@example.com"]
    assert b"hidden@example.com" not in data
    assert b"To: reader@example.com" in data and b"Cc: copy@example.com" in data
    assert b'filename="report.txt"' in data and b"multipart/alternative" in data


def test_a_new_connection_gets_a_socket_timeout(monkeypatch):
    timeouts = []

    class _Socket:
        def settimeout(self, seconds):
            timeouts.append(seconds)

    client = FakeSMTPClient()
    client.sock = _Socket()
    monkeypatch.setattr(smtp_provider, "SMTPWrapper", lambda host, port: client)
    SMTPProvider(_ACCOUNT).send(_MESSAGE)
    assert timeouts == [SOCKET_TIMEOUT_SECONDS]


# --- IMAP -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("folder, expected", [
    ("INBOX", '"INBOX"'),
    ("[Gmail]/Sent Mail", '"[Gmail]/Sent Mail"'),
    ("Q&A", '"Q&-A"'),
    ("收件匣", '"&ZTZO9lMj-"'),
    ("台北/~peter", '"&U,BTFw-/~peter"'),
    ('say "hi"\\now', '"say \\"hi\\"\\\\now"'),
])
def test_folder_names_are_modified_utf7_in_a_quoted_string(folder, expected):
    assert mailbox_name(folder) == expected


@pytest.mark.parametrize("folder", ["", None, 5, "INBOX\r\nA1 DELETE INBOX", "tab\there", "nul\x00"])
def test_a_folder_name_cannot_carry_a_second_command(folder):
    with pytest.raises(MailThunderProviderException, match="invalid folder name"):
        mailbox_name(folder)


def test_imap_reads_newest_first_without_marking_as_read(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    assert imap_clients == []
    messages = list(provider.get_messages())
    (client,) = imap_clients
    assert client.host == "imap.gmail.com"
    assert [message.message_id for message in messages] == ["3", "2", "1"]
    assert (messages[0].subject, messages[0].sender, messages[0].text.strip()) == (
        "Report 3", "Sender <sender@example.com>", "Body 3")
    assert client.calls[:3] == [
        ("login", _USER, _PASSWORD), ("select", '"INBOX"', True), ("uid", "SEARCH", None, "ALL")]
    assert client.calls[3] == ("uid", "FETCH", "3", "(BODY.PEEK[])")
    assert len(client.named("select")) == 1


def test_imap_reads_lazily_and_stops_at_the_limit(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    reading = provider.get_messages(limit=2)
    assert imap_clients == []
    assert next(reading).message_id == "3"
    fetches = [call for call in imap_clients[0].calls if call[:2] == ("uid", "FETCH")]
    assert len(fetches) == 1
    assert [message.message_id for message in reading] == ["2"]
    assert list(provider.get_messages(limit=0)) == []


def test_imap_search_criteria(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    list(provider.get_messages(unread_only=True, query='FROM "ci@example.com"', limit=0))
    list(provider.get_messages(query="SUBJECT 報表", limit=0))
    list(provider.get_messages(unread_only=True, limit=0))
    searches = [call[2:] for call in imap_clients[0].calls if call[:2] == ("uid", "SEARCH")]
    assert searches == [
        (None, 'UNSEEN FROM "ci@example.com"'),
        ("CHARSET", "UTF-8", "SUBJECT 報表".encode("utf-8")),
        (None, "UNSEEN"),
    ]
    with pytest.raises(MailThunderProviderException, match="must be one line"):
        list(provider.get_messages(query="ALL\r\nA1 DELETE INBOX"))


def test_imap_skips_a_message_that_vanished_between_search_and_fetch(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    reading = provider.get_messages()
    assert next(reading).message_id == "3"
    del imap_clients[0].mailbox[2]
    assert [message.message_id for message in reading] == ["1"]


def test_imap_get_message_by_uid(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    assert provider.get_message("2").subject == "Report 2"
    assert provider.get_message(1, folder="Archive").subject == "Report 1"
    assert imap_clients[0].named("select") == [("select", '"INBOX"', True), ("select", '"Archive"', True)]
    with pytest.raises(MailThunderProviderException, match="no message 9 in the folder 'Archive'"):
        provider.get_message("9", folder="Archive")
    for bad in ("1:*", "1 (FLAGS)", "", "２", True, None):
        with pytest.raises(MailThunderProviderException, match="is a UID"):
            provider.get_message(bad)


def test_imap_a_draft_goes_to_the_folder_flagged_drafts(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    assert provider.create_draft(_MESSAGE) == "42"
    client = imap_clients[0]
    assert client.named("append") == [("append", '"[Gmail]/Drafts"', "\\Draft")]
    assert b"Subject: Hello\r\n" in client.appended[0] and b"\r\nbody\r\n" in client.appended[0]


def test_imap_the_drafts_folder_can_be_named(imap_clients):
    servers = MailServers(smtp_host="mail.example.com", imap_host="imap.example.com", drafts_folder="草稿")
    provider = IMAPProvider(MailAccount(provider="smtp", auth=_AUTH, servers=servers))
    provider.create_draft(_MESSAGE)
    provider.create_draft(_MESSAGE, folder="Other Drafts")
    client = imap_clients[0]
    assert client.host == "imap.example.com"
    assert [call[1] for call in client.named("append")] == ['"&g0l6Pw-"', '"Other Drafts"']
    assert client.named("list") == []


def test_imap_without_a_flagged_folder_the_draft_goes_to_drafts(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    list(provider.get_messages(limit=0))
    client = imap_clients[0]
    client.folders = [b'(\\HasNoChildren) "/" "INBOX"', (b"literal", b"name")]
    client.append_answer = [b"Append completed."]
    assert provider.create_draft(_MESSAGE) is None
    assert client.named("append") == [("append", '"Drafts"', "\\Draft")]


def test_imap_delete_expunges_only_that_message_with_uidplus(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    provider.delete_message("2")
    client = imap_clients[0]
    assert client.calls[1:] == [
        ("select", '"INBOX"', False),
        ("uid", "STORE", "2", "+FLAGS", "(\\Deleted)"),
        ("uid", "EXPUNGE", "2"),
    ]
    assert sorted(client.mailbox) == [1, 3]
    with pytest.raises(MailThunderProviderException, match="no message 2 in the folder 'INBOX'"):
        provider.delete_message("2")
    with pytest.raises(MailThunderProviderException, match="is a UID"):
        provider.delete_message("1:*")


def test_imap_delete_without_uidplus_expunges_the_folder(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    list(provider.get_messages(limit=0))
    client = imap_clients[0]
    client.capabilities = ("IMAP4REV1",)
    provider.delete_message("1")
    assert client.calls[-1] == ("expunge",)


def test_imap_reopens_the_folder_only_when_it_has_to(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    provider.get_message("1")
    provider.get_message("2")
    provider.delete_message("1")
    provider.get_message("2")
    provider.get_message("2", folder="Archive")
    assert imap_clients[0].named("select") == [
        ("select", '"INBOX"', True), ("select", '"INBOX"', False), ("select", '"Archive"', True)]


def test_imap_deleting_while_reading_keeps_the_reading_on_its_folder(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    reading = provider.get_messages(folder="INBOX")
    assert next(reading).message_id == "3"
    provider.get_message("1", folder="Archive")
    assert next(reading).message_id == "2"
    assert [call[1] for call in imap_clients[0].named("select")] == ['"INBOX"', '"Archive"', '"INBOX"']


def test_imap_a_refusal_is_a_provider_error_with_the_servers_words(imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    list(provider.get_messages(limit=0))
    imap_clients[0].refuse.add("select")
    with pytest.raises(MailThunderProviderException, match="refused opening the folder 'Nope': refused by the fake"):
        provider.get_message("1", folder="Nope")
    imap_clients[0].refuse.clear()
    imap_clients[0].fail["uid"] = IMAP_ERROR("command SEARCH illegal in state AUTH")
    with pytest.raises(MailThunderProviderException, match="the imap server refused the search"):
        list(provider.get_messages())
    assert len(imap_clients) == 1


@pytest.mark.parametrize("error", [IMAP_ABORT("socket error: EOF"), ConnectionResetError("reset")])
def test_imap_a_lost_connection_is_replaced_on_the_next_call(error, imap_clients):
    provider = IMAPProvider(_ACCOUNT)
    provider.get_message("1")
    first = imap_clients[0]
    first.fail["uid"] = error
    with pytest.raises(MailThunderConnectionException, match="the imap connection was lost"):
        provider.get_message("1")
    assert first.calls[-1] == ("shutdown",)
    assert provider.get_message("1").subject == "Report 1"
    assert len(imap_clients) == 2
    assert imap_clients[1].named("select") == [("select", '"INBOX"', True)]


def test_imap_an_idle_connection_that_died_is_replaced(imap_clients):
    clock = _Clock()
    provider = IMAPProvider(_ACCOUNT, clock=clock)
    provider.get_message("1")
    clock.now += IDLE_CHECK_SECONDS + 1
    provider.get_message("1")
    assert imap_clients[0].named("noop") == [("noop",)] and len(imap_clients) == 1
    imap_clients[0].refuse.add("noop")
    clock.now += IDLE_CHECK_SECONDS + 1
    provider.get_message("1")
    assert len(imap_clients) == 2


def test_imap_a_refused_login_is_an_authentication_error(monkeypatch):
    client = FakeIMAPClient()
    client.fail["login"] = IMAP_ERROR("[AUTHENTICATIONFAILED] Invalid credentials (Failure)")
    monkeypatch.setattr(imap_provider, "IMAPWrapper", lambda host: client)
    with pytest.raises(MailThunderAuthenticationException, match="the imap server refused the login") as raised:
        IMAPProvider(_ACCOUNT).get_message("1")
    assert _PASSWORD not in str(raised.value)
    assert client.calls[-1] == ("logout",)


def test_imap_cannot_connect_and_missing_host(monkeypatch):
    def unreachable(_host):
        raise imaplib.IMAP4.error("could not connect")

    monkeypatch.setattr(imap_provider, "IMAPWrapper", unreachable)
    with pytest.raises(MailThunderConnectionException, match="cannot connect to the imap server"):
        IMAPProvider(_ACCOUNT).get_message("1")
    account = MailAccount(provider="smtp", auth=_AUTH, servers=MailServers(smtp_host="mail.example.com"))
    with pytest.raises(MailThunderProviderException, match="no IMAP server"):
        IMAPProvider(account).get_message("1")


def test_imap_close_logs_out_and_a_given_client_stays_open(imap_clients):
    with IMAPProvider(_ACCOUNT) as provider:
        provider.get_message("1")
    assert imap_clients[0].calls[-1] == ("logout",)
    given = FakeIMAPClient()
    adopted = IMAPProvider(client=given)
    adopted.get_message("1")
    adopted.get_message("2")
    adopted.close()
    assert given.named("login") == [] and given.named("logout") == []
    assert len(given.named("select")) == 2
    assert adopted.create_draft(_MESSAGE) == "42"
