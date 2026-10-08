"""
The provider-agnostic ``Mail`` API, its ``MT_mail_*`` actions and the bridge from the wrapper API.
"""
import json
import logging

import pytest

from je_mail_thunder import mail_instance
from je_mail_thunder.attachments.policy import DEFAULT_ATTACHMENT_POLICY, AttachmentPolicy
from je_mail_thunder.auth.password import PasswordAuth
from je_mail_thunder.auth.xoauth2 import XOAUTH2Auth
from je_mail_thunder.core import mail as mail_module
from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.core.compat import legacy_message, mail_from_wrappers
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers import registry
from je_mail_thunder.providers.imap import IMAPProvider
from je_mail_thunder.providers.smtp import SMTPProvider
from je_mail_thunder.utils.exception.exceptions import (
    AttachmentTooLarge,
    AttachmentTypeNotAllowed,
    MailThunderAuthenticationException,
    MailThunderMessageException,
    MailThunderProviderException,
)
from je_mail_thunder.utils.executor.action_executor import execute_action, executor
from je_mail_thunder.utils.oauth2.oauth2 import OAuth2Settings
from mail_fakes import FakeIMAPClient, FakeSMTPClient, RecordingSender, RecordingStore, stored_message

_USER = "someone@example.com"
_AUTH = PasswordAuth(_USER, "p4ss-word-secret")
_ENV_NAMES = ("mail_thunder_user", "mail_thunder_user_password", "mail_thunder_oauth2_provider",
              "mail_thunder_oauth2_refresh_token", "mail_thunder_oauth2_access_token",
              "mail_thunder_oauth2_token_url")


@pytest.fixture()
def clean_place(tmp_path, monkeypatch):
    """An empty cwd (no mail_thunder_content.json) and no credential variables."""
    monkeypatch.chdir(tmp_path)
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _mail(policy=None, messages=()):
    """A Mail on recording providers, with an account that supplies the default sender."""
    sender, store = RecordingSender(), RecordingStore(messages)
    return Mail(account=MailAccount(auth=_AUTH), providers=[sender, store], policy=policy), sender, store


# --- which account and providers --------------------------------------------------------------------------------

def test_building_a_mail_reads_and_connects_nothing(monkeypatch):
    def fail(*_arguments):
        raise AssertionError("looked up at construction")

    monkeypatch.setattr(mail_module, "default_account", fail)
    monkeypatch.setattr(mail_module, "create_providers", fail)
    assert Mail().policy is DEFAULT_ATTACHMENT_POLICY
    assert isinstance(mail_instance, Mail)


def test_the_default_account_is_gmail_or_the_oauth2_provider(clean_place, monkeypatch):
    assert Mail().account.provider == "google"
    monkeypatch.setenv("mail_thunder_user", _USER)
    monkeypatch.setenv("mail_thunder_oauth2_provider", "microsoft")
    monkeypatch.setenv("mail_thunder_oauth2_access_token", "token")
    mail = Mail()
    assert mail.account.provider == "microsoft"
    assert isinstance(mail.account.authentication(), XOAUTH2Auth)
    sender, store = mail.providers
    assert isinstance(sender, SMTPProvider) and isinstance(store, IMAPProvider)
    assert mail.providers is mail.providers


def test_a_provider_name_and_a_login_make_the_account():
    assert Mail(provider="Gmail").account == MailAccount(provider="google")
    assert Mail(provider="microsoft", auth=_AUTH).account == MailAccount(provider="microsoft", auth=_AUTH)
    assert Mail(auth=_AUTH).account.provider == "google"
    microsoft = XOAUTH2Auth(OAuth2Settings(user=_USER, provider="microsoft", access_token="token"))
    assert Mail(auth=microsoft).account.provider == "microsoft"
    custom = XOAUTH2Auth(OAuth2Settings(user=_USER, provider="microsoft", access_token="token",
                                        token_url="https://id.example.com/token"))
    assert Mail(auth=custom).account.provider == "google"


def test_an_account_excludes_a_provider_name_and_a_login():
    account = MailAccount(auth=_AUTH)
    assert Mail(account=account).account is account
    for extra in ({"provider": "google"}, {"auth": _AUTH}):
        with pytest.raises(MailThunderProviderException, match="not both"):
            Mail(account=account, **extra)


def test_an_unknown_provider_fails_when_it_is_first_used():
    mail = Mail(provider="nowhere", auth=_AUTH)
    with pytest.raises(MailThunderProviderException, match="unknown mail provider 'nowhere'"):
        mail.send(to="reader@example.com", text="x")


def test_a_registered_provider_is_what_mail_uses(monkeypatch):
    monkeypatch.setattr(registry, "_factories", dict(registry._factories))
    sender = RecordingSender()
    registry.register_provider("example", lambda _account: [sender])
    with Mail(provider="example", auth=_AUTH) as mail:
        mail.send(to="reader@example.com", subject="Hi", text="x")
        with pytest.raises(MailThunderProviderException, match="no configured provider can read mail"):
            list(mail.get_messages())
        for call in (lambda: mail.get_message("1"), lambda: mail.delete_message("1"),
                     lambda: mail.create_draft(to="reader@example.com")):
            with pytest.raises(MailThunderProviderException, match="no configured provider can"):
                call()
    assert len(sender.sent) == 1 and sender.closed == 1


def test_a_mail_that_can_only_read_cannot_send():
    mail = Mail(account=MailAccount(auth=_AUTH), providers=[RecordingStore()])
    with pytest.raises(MailThunderProviderException, match="no configured provider can send mail"):
        mail.send(to="reader@example.com", text="x")


# --- sending ----------------------------------------------------------------------------------------------------

def test_send_builds_the_message_and_fills_in_the_sender(tmp_path):
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF")
    mail, sender, _store = _mail()
    sent = mail.send(to="a@example.com, b@example.com", cc=["c@example.com"], subject="Report", text="plain",
                     html="<b>rich</b>", attachments=[str(report)], headers={"X-Run": "42"})
    assert sender.sent == [sent]
    assert (sent.sender, sent.to, sent.cc) == (_USER, ("a@example.com", "b@example.com"), ("c@example.com",))
    assert (sent.subject, sent.text, sent.html) == ("Report", "plain", "<b>rich</b>")
    assert sent.attachments[0].filename == "report.pdf"


def test_send_takes_a_ready_message_and_keeps_its_sender():
    mail, sender, _store = _mail()
    message = MailMessage(to="reader@example.com", sender="Reports <reports@example.com>", text="x")
    assert mail.send(message) is message
    assert sender.sent == [message]
    with pytest.raises(MailThunderProviderException, match="not both"):
        mail.send(message, subject="again")
    with pytest.raises(MailThunderProviderException, match="expected a MailMessage, got dict"):
        mail.send({"to": "reader@example.com"})


@pytest.mark.parametrize("message_fields, error", [
    ({"subject": "nobody"}, MailThunderMessageException),
    ({"to": "a@example.com; b@example.com"}, MailThunderMessageException),
    ({"to": "a@example.com", "recipient": "b@example.com"}, MailThunderMessageException),
    ({"to": "a@example.com", "subject": "x\r\nBcc: victim@example.com"}, MailThunderMessageException),
])
def test_a_message_that_cannot_be_sent_never_reaches_the_provider(message_fields, error):
    mail, sender, _store = _mail()
    with pytest.raises(error):
        mail.send(**message_fields)
    assert sender.sent == []


def test_attachments_are_checked_before_the_provider_sees_the_message(tmp_path):
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * 11)
    program = tmp_path / "setup.exe"
    program.write_bytes(b"MZ")
    mail, sender, store = _mail(policy=AttachmentPolicy(max_file_size=10, allowed_extensions={"bin", "pdf"}))
    with pytest.raises(AttachmentTooLarge):
        mail.send(to="reader@example.com", attachments=[big])
    with pytest.raises(AttachmentTypeNotAllowed):
        mail.send(to="reader@example.com", attachments=[program])
    with pytest.raises(AttachmentTypeNotAllowed):
        mail.create_draft(to="reader@example.com", attachments=[program])
    assert sender.sent == [] and store.drafts == []
    mail.policy = AttachmentPolicy()
    mail.send(to="reader@example.com", attachments=[big, program])
    assert len(sender.sent) == 1


def test_without_credentials_the_sender_cannot_be_filled_in(clean_place):
    sender = RecordingSender()
    mail = Mail(account=MailAccount(), providers=[sender])
    with pytest.raises(MailThunderAuthenticationException, match="no credentials"):
        mail.send(to="reader@example.com", text="x")
    assert mail.send(to="reader@example.com", sender=_USER, text="x").sender == _USER


def test_a_failure_is_logged_before_it_is_raised(caplog):
    mail, _sender, _store = _mail()
    with caplog.at_level(logging.INFO, logger="Mail Thunder"):
        with pytest.raises(MailThunderMessageException):
            mail.send(subject="nobody")
    assert [record.levelname for record in caplog.records if record.message.startswith("mail_send")] == [
        "INFO", "ERROR"]
    assert "at least one recipient" in caplog.text
    assert "p4ss-word-secret" not in caplog.text


# --- reading, drafting, deleting --------------------------------------------------------------------------------

def test_reading_is_lazy_and_passes_its_arguments_on():
    mail, _sender, store = _mail(messages=[stored_message("3"), stored_message("2"), stored_message("1")])
    reading = mail.get_messages("Archive", limit=2, unread_only=True, query="FROM ci")
    assert store.calls == []
    assert [message.message_id for message in reading] == ["3", "2"]
    assert store.calls == [("get_messages", "Archive", 2, True, "FROM ci")]
    assert mail.get_message("1", folder="Archive").message_id == "1"
    assert store.calls[-1] == ("get_message", "1", "Archive")


@pytest.mark.parametrize("limit", [-1, 1.5, "2", True])
def test_an_invalid_limit_fails_at_the_call(limit):
    mail, _sender, store = _mail()
    with pytest.raises(MailThunderProviderException, match="limit must be a whole number"):
        mail.get_messages(limit=limit)
    assert store.calls == []


def test_a_draft_is_checked_like_a_message_to_send():
    mail, sender, store = _mail()
    assert mail.create_draft(to="reader@example.com", subject="Draft", text="x", folder="My Drafts") == "draft-1"
    assert store.calls == [("create_draft", "My Drafts")]
    assert (store.drafts[0].sender, store.drafts[0].subject) == (_USER, "Draft")
    assert mail.create_draft(MailMessage(to="reader@example.com", sender=_USER)) == "draft-1"
    with pytest.raises(MailThunderMessageException, match="at least one recipient"):
        mail.create_draft(subject="nobody")
    assert sender.sent == [] and len(store.drafts) == 2


def test_delete_and_close():
    mail, sender, store = _mail(messages=[stored_message("1"), stored_message("2")])
    assert mail.delete_message("1", folder="Archive") is None
    assert store.calls == [("delete_message", "1", "Archive")] and list(store.messages) == ["2"]
    with mail as entered:
        assert entered is mail
    assert (sender.closed, store.closed) == (1, 1)
    Mail(provider="google", auth=_AUTH).close()


# --- the MT_mail_* actions --------------------------------------------------------------------------------------

@pytest.fixture()
def action_mail(monkeypatch):
    """``mail_instance`` on recording providers for the length of a test."""
    sender = RecordingSender()
    store = RecordingStore([stored_message("2", "Second"), stored_message("1", "First")])
    monkeypatch.setattr(mail_instance, "_account", MailAccount(auth=_AUTH))
    monkeypatch.setattr(mail_instance, "_providers", (sender, store))
    monkeypatch.setattr(mail_instance, "policy", AttachmentPolicy(max_count=1))
    return sender, store


def _only(record):
    (value,) = record.values()
    return value


def test_the_mail_actions_are_commands():
    for name in ("MT_mail_send", "MT_mail_create_draft", "MT_mail_get_messages", "MT_mail_get_message",
                 "MT_mail_delete_message", "MT_mail_close"):
        assert callable(executor.event_dict[name])


def test_the_send_action_answers_with_the_message(action_mail, tmp_path):
    sender, _store = action_mail
    report = tmp_path / "report.txt"
    report.write_bytes(b"data")
    sent = _only(execute_action([["MT_mail_send", {
        "to": "reader@example.com", "subject": "Report", "html": "<b>done</b>", "attachments": [str(report)]}]]))
    assert json.loads(json.dumps(sent))["attachments"] == [
        {"filename": "report.txt", "content_type": "text/plain", "size": 4}]
    assert (sent["sender"], sent["to"], sent["subject"]) == (_USER, ["reader@example.com"], "Report")
    assert sender.sent[0].html == "<b>done</b>"


def test_a_refused_action_is_recorded_not_sent(action_mail, tmp_path):
    sender, _store = action_mail
    first, second = tmp_path / "a.txt", tmp_path / "b.txt"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    record = _only(execute_action([["MT_mail_send", {
        "to": "reader@example.com", "attachments": [str(first), str(second)]}]]))
    assert "AttachmentCountExceeded" in record
    assert "MailThunderMessageException" in _only(execute_action([["MT_mail_send", {"subject": "nobody"}]]))
    assert sender.sent == []


def test_the_reading_actions_answer_with_json_ready_messages(action_mail):
    _sender, store = action_mail
    record = execute_action({"mail_thunder": [
        ["MT_mail_get_messages", {"folder": "INBOX", "limit": 1}],
        ["MT_mail_get_message", {"message_id": "1"}],
        ["MT_mail_create_draft", {"to": "reader@example.com", "subject": "Draft", "folder": "Drafts"}],
        ["MT_mail_delete_message", {"message_id": "1"}],
        ["MT_mail_close"],
    ]})
    listed, one, draft, deleted, closed = record.values()
    assert [message["subject"] for message in json.loads(json.dumps(listed))] == ["Second"]
    assert (one["message_id"], one["subject"]) == ("1", "First")
    assert (draft, deleted, closed) == ("draft-1", None, None)
    assert list(store.messages) == ["2"] and store.closed == 1


# --- from the wrapper API ---------------------------------------------------------------------------------------

def test_wrapper_arguments_become_a_message(tmp_path):
    report = tmp_path / "report.html"
    report.write_bytes(b"<h1>ok</h1>")
    message = legacy_message(
        "<p>done</p>", {"Subject": "Report", "FROM": "me@example.com", "To": "a@example.com, b@example.com",
                        "cc": "c@example.com", "Reply-To": "replies@example.com", "X-Run": "42"},
        attach_file=str(report), use_html=True)
    assert (message.subject, message.sender, message.html, message.text) == (
        "Report", "me@example.com", "<p>done</p>", None)
    assert (message.to, message.cc, message.reply_to) == (
        ("a@example.com", "b@example.com"), ("c@example.com",), ("replies@example.com",))
    assert dict(message.headers) == {"X-Run": "42"}
    assert message.attachments[0].filename == "report.html"
    plain = legacy_message("hello", {"Subject": "s", "To": "a@example.com", "From": "me@example.com"})
    assert (plain.text, plain.html, plain.attachments) == ("hello", None, ())


def test_a_mail_on_connected_wrappers_leaves_them_to_their_owner():
    smtp, imap = FakeSMTPClient(), FakeIMAPClient()
    with mail_from_wrappers(smtp=smtp, imap=imap, policy=AttachmentPolicy(max_count=0)) as mail:
        assert mail.account is None and mail.policy.max_count == 0
        mail.send(legacy_message("hello", {"Subject": "s", "To": "a@example.com", "From": "me@example.com"}))
        assert [message.message_id for message in mail.get_messages(limit=1)] == ["3"]
        with pytest.raises(MailThunderMessageException, match="needs a sender"):
            mail.send(to="a@example.com", text="no sender")
    assert smtp.calls == [("send_message",)]
    assert smtp.sent[0]["From"] == "me@example.com"
    assert imap.named("login") == [] and imap.named("logout") == []
    assert mail_from_wrappers(smtp=smtp).providers[0].name == "smtp"
    with pytest.raises(MailThunderProviderException, match="no configured provider can send mail"):
        mail_from_wrappers().send(to="a@example.com", sender="me@example.com")
