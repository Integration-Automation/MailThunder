"""
What the SMTP and IMAP wrappers guard: the attachment policy before a send, file names that are safe to write for
exported mail, and a TLS connection that verifies who it reaches.
"""
import imaplib
import smtplib
import ssl

import pytest

from je_mail_thunder.attachments.policy import DEFAULT_ATTACHMENT_POLICY, AttachmentPolicy
from je_mail_thunder.imap.imap_wrapper import IMAPWrapper
from je_mail_thunder.smtp.smtp_wrapper import SMTPStartTLSWrapper, SMTPWrapper
from je_mail_thunder.utils.tls.tls_context import verified_client_context

_SETTINGS = {"Subject": "Report", "From": "me@example.com", "To": "you@example.com"}


def test_the_tls_context_verifies_the_certificate_and_the_host_name():
    context = verified_client_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    assert verified_client_context() is not context


def test_smtp_over_implicit_tls_verifies_the_server(monkeypatch):
    monkeypatch.setattr(smtplib.SMTP, "connect", lambda self, host, port, source_address=None: (220, b"ok"))
    client = SMTPWrapper("smtp.example.com")
    assert client.context.verify_mode == ssl.CERT_REQUIRED
    assert client.context.check_hostname is True


def test_imap_verifies_the_server(monkeypatch):
    monkeypatch.setattr(imaplib.IMAP4, "__init__", lambda self, host="", port=993, timeout=None: None)
    client = IMAPWrapper("imap.example.com")
    assert client.ssl_context.verify_mode == ssl.CERT_REQUIRED
    assert client.ssl_context.check_hostname is True


def _smtp(wrapper=SMTPWrapper):
    """A wrapper that is not connected and records what it is asked to send."""
    smtp = wrapper.__new__(wrapper)
    smtp.sent = []
    smtp.send_message = smtp.sent.append
    return smtp


@pytest.mark.parametrize("wrapper", [SMTPWrapper, SMTPStartTLSWrapper])
def test_the_wrappers_check_attachments_against_the_default_policy(wrapper, tmp_path):
    report = tmp_path / "report.txt"
    report.write_bytes(b"numbers")
    smtp = _smtp(wrapper)
    assert smtp.attachment_policy is DEFAULT_ATTACHMENT_POLICY
    smtp.create_message_with_attach_and_send("body", _SETTINGS, str(report))
    assert len(smtp.sent) == 1 and smtp.sent[0]["Subject"] == "Report"


def test_an_attachment_the_policy_refuses_is_not_sent(tmp_path):
    report = tmp_path / "setup.exe"
    report.write_bytes(b"MZ" * 8)
    smtp = _smtp()
    smtp.attachment_policy = AttachmentPolicy(max_file_size=4)
    assert smtp.create_message_with_attach_and_send("body", _SETTINGS, str(report)) is None
    smtp.attachment_policy = AttachmentPolicy(allowed_extensions={"pdf"})
    smtp.create_message_with_attach_and_send("body", _SETTINGS, str(report))
    smtp.attachment_policy = DEFAULT_ATTACHMENT_POLICY
    smtp.create_message_with_attach_and_send("body", _SETTINGS, str(tmp_path / "missing.txt"))
    assert smtp.sent == []


def test_the_check_can_be_turned_off(tmp_path):
    report = tmp_path / "setup.exe"
    report.write_bytes(b"MZ" * 8)
    smtp = _smtp()
    smtp.attachment_policy = None
    smtp.create_message_with_attach_and_send("body", _SETTINGS, str(report))
    assert len(smtp.sent) == 1
    assert SMTPWrapper.attachment_policy is DEFAULT_ATTACHMENT_POLICY


@pytest.mark.parametrize("subject, expected", [
    ("Re: hello", "Re_ hello"),
    ("FW: a/b\\c?", "c_"),
    ("../../etc/passwd", "passwd"),
    ('say "hi" <now>|*', "say _hi_ _now___"),
    ("line\r\nbreak\ttab", "line__break_tab"),
    ("NUL", "_NUL"),
    ("...", "_"),
    ("", "mail"),
    (None, "mail"),
])
def test_a_subject_becomes_a_file_name_every_platform_can_write(subject, expected):
    assert IMAPWrapper._sanitize_subject_as_filename(subject) == expected


def test_exported_mail_keeps_its_body_whatever_the_subject_holds(tmp_path, monkeypatch):
    """On Windows ``open("Re: hello0", "w")`` wrote into an alternate data stream and left an empty ``Re``."""
    monkeypatch.chdir(tmp_path)
    imap = IMAPWrapper.__new__(IMAPWrapper)
    mails = [
        {"SUBJECT": "Re: hello", "BODY": "first"},
        {"SUBJECT": "Re: hello", "BODY": b"second"},
        {"SUBJECT": "../../outside", "BODY": "third"},
        {"SUBJECT": None, "BODY": "fourth"},
    ]
    imap.mail_content_list = lambda search_str="ALL", charset=None: mails
    assert imap.output_all_mail_as_file() == mails
    written = {path.name: path.read_text(encoding="utf-8") for path in tmp_path.iterdir()}
    assert written == {"Re_ hello0": "first", "Re_ hello1": "second", "outside0": "third", "mail0": "fourth"}
    assert not (tmp_path.parent / "outside0").exists()
