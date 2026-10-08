"""
The provider-independent message: how its fields are normalised, what is refused before sending, and its
RFC 5322 form.
"""
import json
from datetime import datetime, timezone
from email import message_from_bytes
from email import policy

import pytest

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.core.message import MailMessage, check_outgoing, message_from_fields, parse_addresses
from je_mail_thunder.core.rfc822 import parse_message, to_email_message
from je_mail_thunder.utils.exception.exceptions import MailThunderMessageException

_SENDER = "sender@example.com"


def _message(**message_fields):
    values = {"to": "reader@example.com", "sender": _SENDER, "subject": "Hello", "text": "body"}
    values.update(message_fields)
    return MailMessage(**values)


def _round_trip(message):
    """The message as a server would hand it back."""
    return message_from_bytes(to_email_message(message).as_bytes(), policy=policy.default)


@pytest.mark.parametrize("value, expected", [
    ("a@example.com", ("a@example.com",)),
    ("a@example.com, Doe <d@example.com>", ("a@example.com", "Doe <d@example.com>")),
    ('"Doe, John" <j@example.com>', ('"Doe, John" <j@example.com>',)),
    ("陳 <chen@example.com>", ("陳 <chen@example.com>",)),
    ("undisclosed-recipients:;", ()),
    ("", ()),
])
def test_addresses_are_split_one_per_entry(value, expected):
    assert parse_addresses(value) == expected


@pytest.mark.parametrize("value", [
    "not an address", "no-domain", "a@example.com; b@example.com", "a@", "@example.com", "a b@example.com",
    "a@example.com\r\nBcc: victim@example.com", "<a@example.com",
])
def test_text_that_is_not_an_address_list_is_none(value):
    assert parse_addresses(value) is None


def test_recipients_are_normalised_to_tuples():
    message = MailMessage(to="a@example.com, b@example.com", cc=["c@example.com"], bcc=("d@example.com",))
    assert message.to == ("a@example.com", "b@example.com")
    assert message.cc == ("c@example.com",)
    assert message.recipients == ("a@example.com", "b@example.com", "c@example.com", "d@example.com")
    assert MailMessage().recipients == ()


def test_attachments_are_given_as_paths_or_attachments(tmp_path):
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF")
    ready = Attachment(filename="notes.txt", content=b"notes")
    message = MailMessage(attachments=[str(report), ready])
    assert [attachment.filename for attachment in message.attachments] == ["report.pdf", "notes.txt"]
    assert MailMessage(attachments=report).attachments[0].path == str(report)


def test_headers_are_copied_and_read_only():
    given = {"X-Run": "42"}
    message = MailMessage(headers=given)
    given["X-Run"] = "changed"
    assert message.headers["X-Run"] == "42"
    with pytest.raises(TypeError):
        message.headers["X-New"] = "1"


@pytest.mark.parametrize("message_fields", [
    {"to": 5}, {"to": ["a@example.com", None]}, {"subject": 7}, {"text": b"bytes"}, {"html": ["<p>"]},
    {"sender": ("a@example.com",)}, {"headers": [("X-Run", "1")]},
])
def test_a_field_of_the_wrong_type_is_refused(message_fields):
    with pytest.raises(MailThunderMessageException):
        MailMessage(**message_fields)


def test_unknown_fields_are_named():
    with pytest.raises(MailThunderMessageException, match="unknown message fields \\['body', 'recipient'\\]"):
        message_from_fields({"recipient": "a@example.com", "body": "x"})
    assert message_from_fields({"to": "a@example.com"}).to == ("a@example.com",)


def test_to_dict_is_json_ready(tmp_path):
    report = tmp_path / "report.txt"
    report.write_text("data", encoding="utf-8")
    message = _message(attachments=[report], headers={"X-Run": "42"}, message_id="7",
                       date=datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc))
    as_dict = json.loads(json.dumps(message.to_dict()))
    assert as_dict["to"] == ["reader@example.com"]
    assert as_dict["date"] == "2026-10-01T08:00:00+00:00"
    assert as_dict["attachments"] == [{"filename": "report.txt", "content_type": "text/plain", "size": 4}]
    assert as_dict["headers"] == {"X-Run": "42"}
    assert as_dict["message_id"] == "7"


def test_a_complete_message_passes_the_check():
    check_outgoing(_message(cc="Copy <copy@example.com>", reply_to="replies@example.com", headers={"X-Run": "1"}))
    check_outgoing(MailMessage(bcc="hidden@example.com", sender=_SENDER))


@pytest.mark.parametrize("message_fields, reason", [
    ({"to": ()}, "at least one recipient"),
    ({"sender": None}, "needs a sender"),
    ({"to": "a@example.com; b@example.com"}, "invalid address"),
    ({"cc": "nobody"}, "invalid address"),
    ({"reply_to": "a@"}, "invalid address"),
    ({"sender": "a@example.com, b@example.com"}, "invalid address"),
    ({"to": "a@example.com\r\nBcc: victim@example.com"}, "invalid address"),
    ({"subject": "Hello\r\nBcc: victim@example.com"}, "subject must be one line"),
    ({"headers": {"X-Run": "1\r\nBcc: victim@example.com"}}, "one-line text value"),
    ({"headers": {"X-Run": 1}}, "one-line text value"),
    ({"headers": {"Bad Name": "1"}}, "invalid header name"),
    ({"headers": {"X-Run:": "1"}}, "invalid header name"),
    ({"headers": {"Subject": "another"}}, "set by the message's own fields"),
    ({"headers": {"bcc": "victim@example.com"}}, "set by the message's own fields"),
])
def test_what_cannot_be_sent_is_refused(message_fields, reason):
    with pytest.raises(MailThunderMessageException, match=reason):
        check_outgoing(_message(**message_fields))


def test_text_only_is_a_plain_message():
    email_message = _round_trip(_message(text="plain body", subject="報表 😀", cc="Copy <copy@example.com>"))
    assert email_message.get_content_type() == "text/plain"
    assert email_message.get_content().strip() == "plain body"
    assert (email_message["Subject"], email_message["From"]) == ("報表 😀", _SENDER)
    assert (email_message["To"], email_message["Cc"]) == ("reader@example.com", "Copy <copy@example.com>")


def test_html_only_is_an_html_message():
    email_message = _round_trip(_message(text=None, html="<p>Hi</p>"))
    assert email_message.get_content_type() == "text/html"
    assert email_message.get_content().strip() == "<p>Hi</p>"


def test_text_and_html_are_alternatives():
    email_message = _round_trip(_message(text="plain", html="<p>rich</p>"))
    assert email_message.get_content_type() == "multipart/alternative"
    assert email_message.get_body(("plain",)).get_content().strip() == "plain"
    assert email_message.get_body(("html",)).get_content().strip() == "<p>rich</p>"


def test_no_body_is_an_empty_text_message():
    assert _round_trip(_message(text=None)).get_content().strip() == ""


def test_attachments_bcc_and_custom_headers_are_written(tmp_path):
    binary = tmp_path / "data.bin"
    binary.write_bytes(b"\x00\x01\x02\xff")
    saved_mail = tmp_path / "saved.eml"
    saved_mail.write_bytes(b"Subject: inner\r\n\r\nbody\r\n")
    notes = Attachment(filename="筆記.txt", content_type="text/plain", content="內容".encode("utf-8"))
    email_message = _round_trip(_message(
        attachments=[binary, saved_mail, notes], bcc="hidden@example.com", reply_to="replies@example.com",
        headers={"X-Run": "42"}))
    assert email_message.get_content_type() == "multipart/mixed"
    assert (email_message["Bcc"], email_message["Reply-To"], email_message["X-Run"]) == (
        "hidden@example.com", "replies@example.com", "42")
    attached = {part.get_filename(): part for part in email_message.iter_attachments()}
    assert attached["data.bin"].get_content_type() == "application/octet-stream"
    assert attached["data.bin"].get_payload(decode=True) == b"\x00\x01\x02\xff"
    assert attached["saved.eml"].get_content_type() == "application/octet-stream"
    assert attached["筆記.txt"].get_payload(decode=True).decode("utf-8") == "內容"


def test_a_sent_message_reads_back_as_the_same_message(tmp_path):
    report = tmp_path / "report.csv"
    report.write_bytes(b"a,b\n1,2\n")
    sent = _message(subject="Résumé 報表", to='"Doe, John" <j@example.com>, b@example.com', cc="陳 <chen@example.com>",
                    text="plain", html="<b>rich</b>", attachments=[report], reply_to="replies@example.com")
    received = parse_message(to_email_message(sent).as_bytes(), message_id="12")
    assert received.message_id == "12"
    assert (received.subject, received.sender) == (sent.subject, sent.sender)
    assert (received.to, received.cc, received.reply_to) == (sent.to, sent.cc, sent.reply_to)
    assert (received.text.strip(), received.html.strip()) == ("plain", "<b>rich</b>")
    assert [(a.filename, a.content_type, a.read()) for a in received.attachments] == [
        ("report.csv", sent.attachments[0].content_type, b"a,b\n1,2\n")]


def test_a_received_message_keeps_its_date_and_thread_headers():
    raw = (b"From: Sender <sender@example.com>\r\nTo: undisclosed-recipients:;\r\nSubject: =?utf-8?b?5aCx6KGo?=\r\n"
           b"Date: Thu, 01 Oct 2026 08:00:00 +0800\r\nMessage-ID: <1@example.com>\r\n"
           b"In-Reply-To: <0@example.com>\r\nReceived: from somewhere\r\n\r\nbody\r\n")
    message = parse_message(raw, "5")
    assert message.subject == "報表"
    assert message.sender == "Sender <sender@example.com>"
    assert message.to == ()
    assert message.date.isoformat() == "2026-10-01T08:00:00+08:00"
    assert dict(message.headers) == {"Message-ID": "<1@example.com>", "In-Reply-To": "<0@example.com>"}
    assert (message.text.strip(), message.html, message.attachments) == ("body", None, ())


def test_a_received_attachment_name_cannot_leave_a_directory(tmp_path):
    raw = (b"From: a@example.com\r\nTo: b@example.com\r\nSubject: s\r\nMIME-Version: 1.0\r\n"
           b'Content-Type: multipart/mixed; boundary="b"\r\n\r\n'
           b"--b\r\nContent-Type: text/plain\r\n\r\nbody\r\n"
           b'--b\r\nContent-Type: application/octet-stream\r\n'
           b'Content-Disposition: attachment; filename="../../../etc/cron.d/evil"\r\n'
           b"Content-Transfer-Encoding: base64\r\n\r\ncGF5bG9hZA==\r\n"
           b"--b\r\nContent-Type: message/rfc822\r\nContent-Disposition: attachment\r\n\r\n"
           b"Subject: inner\r\n\r\ninner body\r\n--b--\r\n")
    message = parse_message(raw)
    names = [attachment.filename for attachment in message.attachments]
    assert names == ["evil", "attachment"]
    assert message.attachments[0].read() == b"payload"
    assert b"inner body" in message.attachments[1].read()
    written = message.attachments[0].save(tmp_path)
    assert written == str(tmp_path / "evil")


@pytest.mark.parametrize("raw", [
    b"", b"no headers at all", b"Subject: only\r\n\r\n", b"Date: not a date\r\nFrom: \r\n\r\nbody",
    b"Content-Type: text/plain; charset=no-such-charset\r\n\r\n\xff\xfe",
])
def test_a_malformed_message_is_still_read(raw):
    message = parse_message(raw, "1")
    assert message.message_id == "1"
    assert message.date is None
