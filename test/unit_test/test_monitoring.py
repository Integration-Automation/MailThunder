"""
What listens to mail events: the audit log, provider health and the webhook forwarder; and the providers'
connection check they rely on.
"""
import hashlib
import hmac
import json
import threading
from datetime import datetime, timezone

import pytest

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.auth.password import PasswordAuth
from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.core.events import (
    ATTACHMENT_REJECTED,
    AUTHENTICATION_FAILED,
    CONNECTION_FAILED,
    MESSAGE_FAILED,
    MESSAGE_RECEIVED,
    MESSAGE_SENT,
    MailEvent,
)
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.monitoring import audit as audit_module
from je_mail_thunder.monitoring.audit import AuditLog, audit_entry, default_audit_file
from je_mail_thunder.monitoring.health import ProviderHealth
from je_mail_thunder.providers import smtp as smtp_provider
from je_mail_thunder.providers.smtp import SMTPProvider
from je_mail_thunder.triggers.dispatcher import EventDispatcher
from je_mail_thunder.triggers.webhook import WebhookForwarder, sign, webhook_payload
from je_mail_thunder.utils.exception.exceptions import (
    AttachmentTooLarge,
    MailThunderAuthenticationException,
    MailThunderConnectionException,
    MailThunderMessageException,
    MailThunderSendException,
    MailThunderTriggerException,
)
from mail_fakes import FakeSMTPClient, RecordingSender, RecordingStore

_CONFIDENTIAL_BODY = "the quarterly numbers are confidential"
_MESSAGE = MailMessage(
    subject="Q3 report", to="qa@example.com", cc="lead@example.com", bcc="audit@example.com",
    sender="ci@example.com", text=_CONFIDENTIAL_BODY, html=f"<p>{_CONFIDENTIAL_BODY}</p>",
    attachments=[Attachment(filename="q3.pdf", content_type="application/pdf", content=b"%PDF-secret-bytes")],
    headers={"Message-ID": "<1@example.com>"}, message_id="42")
_WHEN = datetime(2026, 10, 8, 9, 30, tzinfo=timezone.utc)


def _event(name=MESSAGE_SENT, **fields):
    values = {"message": _MESSAGE, "provider": "smtp", "timestamp": _WHEN}
    values.update(fields)
    return MailEvent(name, **values)


# --- the audit log ----------------------------------------------------------------------------------------------

def test_an_audit_entry_holds_the_facts_and_never_the_content():
    entry = audit_entry(_event(folder="INBOX", metadata={"run": 7}))
    assert entry == {
        "timestamp": "2026-10-08T09:30:00+00:00", "event": "message_sent", "provider": "smtp", "folder": "INBOX",
        "message_id": "42", "internet_message_id": "<1@example.com>", "sender": "ci@example.com",
        "to": ["qa@example.com"], "cc": ["lead@example.com"], "bcc": ["audit@example.com"],
        "attachments": [{"filename": "q3.pdf", "content_type": "application/pdf", "size": 17}],
        "subject": "Q3 report", "metadata": {"run": "7"},
    }
    serialised = json.dumps(entry)
    assert _CONFIDENTIAL_BODY not in serialised
    assert "secret-bytes" not in serialised
    assert "subject" not in audit_entry(_event(), subjects=False)
    failed = audit_entry(_event(MESSAGE_FAILED, message=None, error=MailThunderSendException("refused by server"),
                                attachment=_MESSAGE.attachments[0]))
    assert failed["error"] == {"type": "MailThunderSendException", "message": "refused by server"}
    assert failed["attachment"]["filename"] == "q3.pdf"
    assert "sender" not in failed


def test_the_audit_log_appends_one_line_per_event(tmp_path):
    log = AuditLog(tmp_path / "audit" / "mail.jsonl")
    assert log.entries() == []
    log.record(_event())
    log.record(_event(MESSAGE_FAILED, error=MailThunderConnectionException("down"),
                      message=MailMessage(subject="報表\nwith a line break", to="a@example.com")))
    lines = log.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(json.loads(line) for line in lines)
    assert [entry["event"] for entry in log.entries()] == ["message_sent", "message_failed"]
    assert log.entries()[1]["subject"] == "報表\nwith a line break"
    assert [entry["event"] for entry in log.entries(limit=1)] == ["message_failed"]
    with open(log.path, "a", encoding="utf-8") as audit_file:
        audit_file.write("not json\n")
    assert len(log.entries(limit=None)) == 2


def test_the_audit_log_follows_a_mail_and_survives_a_file_it_cannot_write(tmp_path, caplog):
    log = AuditLog(tmp_path / "mail.jsonl", subjects=False)
    mail = Mail(account=MailAccount(auth=PasswordAuth("ci@example.com", "p4ss-word-secret")),
                providers=[RecordingSender()])
    subscription = log.attach(mail.events)
    mail.send(to="qa@example.com", subject="Confidential", text=_CONFIDENTIAL_BODY)
    with pytest.raises(MailThunderMessageException):
        mail.send(subject="nobody")
    entries = log.entries()
    assert [entry["event"] for entry in entries] == ["message_sent", "message_failed"]
    assert "subject" not in entries[0]
    assert entries[1]["error"]["type"] == "MailThunderMessageException"
    assert "p4ss-word-secret" not in log.path.read_text(encoding="utf-8")
    assert mail.events.off(subscription)
    blocked = AuditLog(tmp_path / "mail.jsonl" / "below-a-file.jsonl")
    blocked.record(_event())
    assert "cannot be written" in caplog.text


def test_the_audit_log_rotates_and_has_a_default_place(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_module, "ROTATE_AT_BYTES", 200)
    log = AuditLog(tmp_path / "mail.jsonl")
    for _ in range(3):
        log.record(_event())
    assert (tmp_path / "mail.jsonl.1").is_file()
    assert len(log.entries()) == 1
    monkeypatch.setenv("MAIL_THUNDER_AUDIT_FILE", str(tmp_path / "elsewhere.jsonl"))
    assert default_audit_file() == tmp_path / "elsewhere.jsonl"
    assert AuditLog().path == tmp_path / "elsewhere.jsonl"
    monkeypatch.delenv("MAIL_THUNDER_AUDIT_FILE")
    assert default_audit_file().parts[-3:] == (".je_mail_thunder", "audit", "mail_audit.jsonl")


# --- provider health --------------------------------------------------------------------------------------------

def test_health_follows_successes_and_failures():
    health = ProviderHealth(failure_threshold=2)
    assert health.status("smtp")["state"] == "unknown"
    assert health.report() == []
    health.record(_event(MESSAGE_SENT))
    health.record(_event(MESSAGE_RECEIVED, provider="imap"))
    assert health.status("smtp")["state"] == "healthy"
    health.record(_event(CONNECTION_FAILED, error=MailThunderConnectionException("smtp down")))
    status = health.status("smtp")
    assert (status["state"], status["failures"], status["consecutive_failures"]) == ("degraded", 1, 1)
    assert status["last_error"] == "MailThunderConnectionException: smtp down"
    assert status["last_failure"] == "2026-10-08T09:30:00+00:00"
    assert status["last_success"] is not None
    health.record(_event(AUTHENTICATION_FAILED, error=MailThunderAuthenticationException("refused")))
    assert health.status("smtp")["state"] == "down"
    health.record(_event(MESSAGE_SENT))
    recovered = health.status("smtp")
    assert (recovered["state"], recovered["successes"], recovered["consecutive_failures"]) == ("healthy", 2, 0)
    assert [status["provider"] for status in health.report()] == ["imap", "smtp"]
    assert json.dumps(health.report())


def test_only_the_providers_own_failures_count_and_each_counts_once():
    health = ProviderHealth()
    for event in (
        _event(ATTACHMENT_REJECTED, error=AttachmentTooLarge("a.bin", 2, 1)),
        _event(MESSAGE_FAILED, error=AttachmentTooLarge("a.bin", 2, 1)),
        _event(MESSAGE_FAILED, error=MailThunderMessageException("no recipient")),
        _event(MESSAGE_FAILED, error=MailThunderConnectionException("already counted as connection_failed")),
        _event(MESSAGE_SENT, provider=""),
    ):
        health.record(event)
    assert health.report() == []
    health.record(_event(MESSAGE_FAILED, error=MailThunderSendException("refused")))
    health.record(_event(CONNECTION_FAILED, error=None))
    assert health.status("smtp")["failures"] == 2
    assert ProviderHealth(failure_threshold=0).status("x")["state"] == "unknown"


def test_health_follows_a_mail_and_can_ask_the_providers(monkeypatch):
    sender, store = RecordingSender(), RecordingStore()
    mail = Mail(account=MailAccount(auth=PasswordAuth("ci@example.com", "p4ss-word-secret")),
                providers=[sender, store])
    health = ProviderHealth()
    health.attach(mail.events)
    mail.send(to="qa@example.com", subject="x", text="y")
    assert health.status("recording-sender")["state"] == "healthy"

    def down():
        raise MailThunderConnectionException("cannot connect")

    monkeypatch.setattr(store, "check", down)
    report = health.probe(mail.providers)
    assert [(status["provider"], status["state"]) for status in report] == [
        ("recording-sender", "healthy"), ("recording-store", "degraded")]
    assert health.status("recording-sender")["successes"] == 2


def test_a_provider_check_connects_and_logs_in_without_sending(monkeypatch):
    client = FakeSMTPClient()
    monkeypatch.setattr(smtp_provider, "SMTPWrapper", lambda host, port: client)
    provider = SMTPProvider(MailAccount(auth=PasswordAuth("ci@example.com", "p4ss-word-secret")))
    assert provider.check() is None
    assert provider.check() is None
    assert client.calls == [("login", "ci@example.com", "p4ss-word-secret")]
    assert client.sent == []
    assert RecordingSender().check() is None


# --- the webhook forwarder --------------------------------------------------------------------------------------

class _Receiver:
    """A transport that keeps what it is posted and answers with a status."""

    def __init__(self, status=200):
        self.status = status
        self.posts = []
        self.posted = threading.Event()

    def __call__(self, method, url, headers, body):
        self.posts.append((method, url, headers, body))
        self.posted.set()
        return self.status, b""


def test_a_webhook_payload_describes_the_event_without_bodies():
    payload = webhook_payload(_event())
    assert payload["name"] == "message_sent"
    assert payload["message"]["subject"] == "Q3 report"
    assert "text" not in payload["message"]
    assert "html" not in payload["message"]
    assert payload["message"]["attachments"] == [{"filename": "q3.pdf", "content_type": "application/pdf", "size": 17}]
    assert _CONFIDENTIAL_BODY not in json.dumps(payload)
    assert webhook_payload(_event(), bodies=True)["message"]["text"] == _CONFIDENTIAL_BODY
    assert webhook_payload(MailEvent(CONNECTION_FAILED))["message"] is None


def test_an_event_is_posted_signed_and_in_order():
    receiver = _Receiver()
    forwarder = WebhookForwarder("https://hooks.example.com/mail", secret="shared-secret", transport=receiver)
    dispatcher = EventDispatcher()
    dispatcher.on("*", forwarder)
    dispatcher.emit(_event(MESSAGE_SENT))
    dispatcher.emit(_event(MESSAGE_RECEIVED))
    forwarder.flush()
    forwarder.close()
    forwarder.close()
    assert [post[2]["X-MailThunder-Event"] for post in receiver.posts] == ["message_sent", "message_received"]
    method, url, headers, body = receiver.posts[0]
    assert (method, url, headers["Content-Type"]) == (
        "POST", "https://hooks.example.com/mail", "application/json; charset=utf-8")
    expected = "sha256=" + hmac.new(b"shared-secret", body, hashlib.sha256).hexdigest()
    assert headers["X-MailThunder-Signature"] == expected == sign("shared-secret", body)
    assert json.loads(body)["message"]["subject"] == "Q3 report"
    assert _CONFIDENTIAL_BODY.encode() not in body
    assert dispatcher.subscriptions[0].describe()["handler"] == "WebhookForwarder"


def test_a_webhook_without_a_secret_is_not_signed_and_a_failure_is_logged(caplog):
    refusing = _Receiver(status=500)
    forwarder = WebhookForwarder("https://hooks.example.com/mail", bodies=True, transport=refusing)
    event = _event()
    with pytest.raises(MailThunderTriggerException, match="answered HTTP 500 to the event 'message_sent'"):
        forwarder.deliver(event)
    assert "X-MailThunder-Signature" not in refusing.posts[0][2]
    assert _CONFIDENTIAL_BODY.encode() in refusing.posts[0][3]
    forwarder(_event())
    forwarder.flush()
    forwarder.close()
    assert "not delivered" in caplog.text
    assert WebhookForwarder("https://hooks.example.com/mail", transport=_Receiver(204)).deliver(_event()) == 204


def test_a_full_queue_drops_events_and_only_https_is_posted_to(caplog):
    release = threading.Event()

    def slow(method, url, headers, body):
        release.wait(5)
        return 200, b""

    forwarder = WebhookForwarder("https://hooks.example.com/mail", queue_size=1, transport=slow)
    for _ in range(4):
        forwarder(_event())
    release.set()
    forwarder.close()
    assert "queue full" in caplog.text
    for address in ("http://hooks.example.com/mail", "", None):
        with pytest.raises(MailThunderTriggerException, match="https address"):
            WebhookForwarder(address)
