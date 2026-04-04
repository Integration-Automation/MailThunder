from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
import os
import tempfile

from je_mail_thunder.smtp.smtp_wrapper import SMTPWrapper


def test_create_message_returns_email_message():
    msg = SMTPWrapper.create_message(
        "Hello World",
        {"Subject": "Test", "From": "a@b.com", "To": "c@d.com"},
    )
    assert isinstance(msg, EmailMessage)
    assert msg["Subject"] == "Test"
    assert msg["From"] == "a@b.com"
    assert msg["To"] == "c@d.com"


def test_create_message_content():
    msg = SMTPWrapper.create_message("body text", {"Subject": "s"})
    assert "body text" in msg.get_content()


def test_create_message_with_attach_text_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("file content")
        f.flush()
        tmp_path = f.name
    try:
        msg = SMTPWrapper.create_message_with_attach(
            "msg body",
            {"Subject": "attach test", "From": "a@b.com", "To": "c@d.com"},
            tmp_path,
        )
        assert isinstance(msg, MIMEMultipart)
        assert msg["Subject"] == "attach test"
        payloads = msg.get_payload()
        assert len(payloads) >= 2
    finally:
        os.unlink(tmp_path)


def test_create_message_with_attach_html():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write("<h1>Hello</h1>")
        f.flush()
        tmp_path = f.name
    try:
        msg = SMTPWrapper.create_message_with_attach(
            "<p>html body</p>",
            {"Subject": "html test"},
            tmp_path,
            use_html=True,
        )
        assert isinstance(msg, MIMEMultipart)
        payloads = msg.get_payload()
        assert any("html" in str(p.get_content_type()) for p in payloads)
    finally:
        os.unlink(tmp_path)


def test_create_message_with_attach_binary_file():
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(b"\x00\x01\x02\x03")
        f.flush()
        tmp_path = f.name
    try:
        msg = SMTPWrapper.create_message_with_attach(
            "binary attachment",
            {"Subject": "bin test"},
            tmp_path,
        )
        assert isinstance(msg, MIMEMultipart)
    finally:
        os.unlink(tmp_path)
