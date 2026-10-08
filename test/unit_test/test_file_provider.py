"""
The providers added beside Gmail and Microsoft 365: the app-password presets, and the file provider that keeps
mail on disk instead of sending it.
"""
import pytest

from je_mail_thunder.auth.password import AppPasswordAuth
from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers.file import FileProvider
from je_mail_thunder.providers.imap import IMAPProvider
from je_mail_thunder.providers.registry import create_providers, registered_providers
from je_mail_thunder.providers.smtp import SMTPProvider
from je_mail_thunder.triggers.polling import PollingBackend
from je_mail_thunder.utils.exception.exceptions import MailThunderProviderException

_AUTH = AppPasswordAuth("someone@example.com", "abcd efgh ijkl mnop")


@pytest.mark.parametrize("name, smtp_host, port, starttls, imap_host", [
    ("yahoo", "smtp.mail.yahoo.com", 465, False, "imap.mail.yahoo.com"),
    ("icloud", "smtp.mail.me.com", 587, True, "imap.mail.me.com"),
    ("zoho", "smtp.zoho.com", 465, False, "imap.zoho.com"),
    ("fastmail", "smtp.fastmail.com", 465, False, "imap.fastmail.com"),
])
def test_the_app_password_providers(name, smtp_host, port, starttls, imap_host):
    account = MailAccount(provider=name.upper(), auth=_AUTH)
    servers = account.resolved_servers
    assert (servers.smtp_host, servers.port, servers.smtp_starttls, servers.imap_host) == (
        smtp_host, port, starttls, imap_host)
    sender, store = create_providers(account)
    assert isinstance(sender, SMTPProvider) and isinstance(store, IMAPProvider)
    assert name in registered_providers()


def _mail(directory):
    provider = FileProvider(directory)
    return Mail(account=MailAccount(provider="file", auth=_AUTH), providers=[provider]), provider


def test_the_file_provider_keeps_what_would_be_sent(tmp_path):
    report = tmp_path / "report.txt"
    report.write_bytes(b"numbers")
    mail, provider = _mail(tmp_path / "outbox")
    mail.send(to="qa@example.com", bcc="hidden@example.com", subject="Nightly 報表", text="plain", html="<b>rich</b>",
              attachments=[report])
    draft_id = mail.create_draft(to="qa@example.com", subject="Later", text="draft")
    (sent,) = mail.get_messages("Sent")
    assert (sent.subject, sent.sender, sent.to, sent.bcc) == (
        "Nightly 報表", "someone@example.com", ("qa@example.com",), ("hidden@example.com",))
    assert (sent.text.strip(), sent.html.strip()) == ("plain", "<b>rich</b>")
    assert [(a.filename, a.read()) for a in sent.attachments] == [("report.txt", b"numbers")]
    assert mail.get_message(draft_id, folder="Drafts").subject == "Later"
    assert sorted(path.name for path in (tmp_path / "outbox").iterdir()) == ["Drafts", "Sent"]
    assert (tmp_path / "outbox" / "Sent" / f"{sent.message_id}.eml").is_file()
    assert provider.close() is None and provider.check() is None


def test_the_file_provider_reads_newest_first_and_deletes(tmp_path):
    mail, provider = _mail(tmp_path)
    for number in range(3):
        provider.create_draft(MailMessage(to="a@example.com", sender="b@example.com", subject=f"Report {number}"),
                              folder="INBOX")
    (tmp_path / "INBOX" / "dropped in by hand.eml").write_bytes(b"Subject: ignored\r\n\r\nx")
    (tmp_path / "INBOX" / "by-hand.eml").write_bytes(b"Subject: Weekly summary\r\nFrom: ci@example.com\r\n\r\nx")
    subjects = [message.subject for message in mail.get_messages()]
    assert subjects == ["Weekly summary", "Report 2", "Report 1", "Report 0"]
    assert [message.subject for message in mail.get_messages(limit=2, unread_only=True)] == subjects[:2]
    assert [message.subject for message in mail.get_messages(query="REPORT", limit=2)] == ["Report 2", "Report 1"]
    assert list(mail.get_messages("Empty")) == []
    newest = next(mail.get_messages(query="report")).message_id
    mail.delete_message(newest)
    assert [message.subject for message in mail.get_messages(query="report")] == ["Report 1", "Report 0"]
    with pytest.raises(MailThunderProviderException, match="no message"):
        mail.get_message(newest)


@pytest.mark.parametrize("message_id", ["../Sent/x", "a/b", "", ".hidden", "a b", None, 5, "x..y"])
def test_a_file_provider_message_id_is_never_a_path(message_id, tmp_path):
    (tmp_path / "Sent").mkdir()
    (tmp_path / "Sent" / "x.eml").write_bytes(b"Subject: outside\r\n\r\nx")
    provider = FileProvider(tmp_path)
    for call in (provider.get_message, provider.delete_message):
        with pytest.raises(MailThunderProviderException, match="is a file name"):
            call(message_id, "INBOX")
    assert (tmp_path / "Sent" / "x.eml").is_file()


def test_a_folder_stays_inside_the_directory_and_failures_are_provider_errors(tmp_path):
    provider = FileProvider(tmp_path / "outbox")
    message = MailMessage(to="a@example.com", sender="b@example.com", subject="x")
    provider.create_draft(message, folder="../../escape")
    assert (tmp_path / "outbox" / "escape").is_dir() and not (tmp_path / "escape").exists()
    for folder in ("", "  ", None):
        with pytest.raises(MailThunderProviderException, match="invalid folder name"):
            provider.get_message("x", folder)
    blocker = tmp_path / "a-file"
    blocker.write_bytes(b"")
    with pytest.raises(MailThunderProviderException, match="cannot be created"):
        FileProvider(blocker).check()
    with pytest.raises(MailThunderProviderException, match="cannot be created"):
        FileProvider(blocker).send(message)


def test_the_registered_file_provider_takes_its_directory_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MAIL_THUNDER_FILE_PROVIDER_DIR", raising=False)
    assert "file" in registered_providers()
    (provider,) = create_providers(MailAccount(provider="file"))
    assert isinstance(provider, FileProvider) and str(provider.directory) == "mail_outbox"
    monkeypatch.setenv("MAIL_THUNDER_FILE_PROVIDER_DIR", str(tmp_path / "dry-run"))
    with Mail(provider="file", auth=_AUTH) as mail:
        mail.send(to="qa@example.com", subject="Dry run", text="x")
    assert len(list((tmp_path / "dry-run" / "Sent").glob("*.eml"))) == 1


def test_a_trigger_sees_mail_dropped_into_the_inbox(tmp_path):
    provider = FileProvider(tmp_path)
    backend = PollingBackend(provider)
    events = []
    backend.bind(events.append)
    assert backend.poll() == 0
    provider.create_draft(MailMessage(to="a@example.com", sender="ci@example.com", subject="Arrived"), folder="INBOX")
    assert backend.poll() == 1
    assert (events[0].name, events[0].message.subject, events[0].provider) == ("message_received", "Arrived", "file")
