"""
Attachments and the policy they are checked against before a message is sent.
"""
import os

import pytest

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.attachments.mime import file_extension, guess_content_type, safe_filename
from je_mail_thunder.attachments.policy import DEFAULT_ATTACHMENT_POLICY, MEBIBYTE, AttachmentPolicy
from je_mail_thunder.attachments.validator import validate_attachments
from je_mail_thunder.utils.exception.exceptions import (
    AttachmentCountExceeded,
    AttachmentNotFound,
    AttachmentTooLarge,
    AttachmentTypeNotAllowed,
    MailThunderAttachmentException,
    MailThunderException,
    TotalAttachmentSizeExceeded,
)


def _file(directory, name, size=4):
    path = directory / name
    path.write_bytes(b"x" * size)
    return str(path)


@pytest.mark.parametrize("name, expected", [
    ("report.pdf", "application/pdf"),
    ("notes.txt", "text/plain"),
    ("photo.PNG", "image/png"),
    ("archive.txt.gz", "application/octet-stream"),
    ("no_extension", "application/octet-stream"),
])
def test_the_content_type_comes_from_the_name(name, expected):
    assert guess_content_type(name) == expected


@pytest.mark.parametrize("name, expected", [
    ("Report.PDF", ".pdf"), ("report.pdf.exe", ".exe"), ("folder.d/readme", ""), ("C:\\dir\\a.TXT", ".txt"),
])
def test_the_extension_is_the_last_one_lower_cased(name, expected):
    assert file_extension(name) == expected


@pytest.mark.parametrize("name, expected", [
    ("report.pdf", "report.pdf"),
    ("../../etc/passwd", "passwd"),
    ("..\\..\\windows\\system32\\evil.dll", "evil.dll"),
    ("/abs/olute.txt", "olute.txt"),
    ("C:\\abs\\olute.txt", "olute.txt"),
    ("a..b", "a_b"),
    ("re: quarterly?.txt", "re_ quarterly_.txt"),
    ("line\r\nbreak\x00.txt", "line__break_.txt"),
    ("NUL", "_NUL"),
    ("com1.txt", "_com1.txt"),
    ("...", "_"),
    (" . ", "attachment"),
    ("", "attachment"),
    (None, "attachment"),
])
def test_a_received_file_name_is_made_safe(name, expected):
    assert safe_filename(name) == expected


def test_an_attachment_from_a_path_takes_its_name_and_type(tmp_path):
    attachment = Attachment.from_path(_file(tmp_path, "report.pdf", size=10))
    assert attachment.filename == "report.pdf"
    assert attachment.content_type == "application/pdf"
    assert attachment.size == 10
    assert attachment.read() == b"x" * 10
    assert attachment.describe() == {"filename": "report.pdf", "content_type": "application/pdf", "size": 10}


def test_an_attachment_can_be_renamed_and_retyped(tmp_path):
    attachment = Attachment.from_path(tmp_path / "data.bin", filename="results.csv", content_type="text/csv")
    assert (attachment.filename, attachment.content_type) == ("results.csv", "text/csv")


def test_of_accepts_paths_and_attachments_only(tmp_path):
    attachment = Attachment.from_path(_file(tmp_path, "a.txt"))
    assert Attachment.of(attachment) is attachment
    assert Attachment.of(tmp_path / "a.txt").path == str(tmp_path / "a.txt")
    with pytest.raises(MailThunderAttachmentException):
        Attachment.of(42)


def test_an_attachment_needs_a_name_and_a_source():
    with pytest.raises(MailThunderAttachmentException):
        Attachment(filename="", content=b"x")
    with pytest.raises(MailThunderAttachmentException):
        Attachment(filename="a.txt")


def test_a_missing_file_is_attachment_not_found(tmp_path):
    attachment = Attachment.from_path(tmp_path / "missing.txt")
    with pytest.raises(AttachmentNotFound) as raised:
        _ = attachment.size
    assert raised.value.path == str(tmp_path / "missing.txt")
    with pytest.raises(AttachmentNotFound):
        attachment.read()
    directory = Attachment.from_path(tmp_path)
    with pytest.raises(AttachmentNotFound):
        directory.read()


def test_the_content_stays_out_of_the_repr():
    assert "secret-bytes" not in repr(Attachment(filename="a.txt", content=b"secret-bytes"))


def test_a_received_attachment_is_saved_inside_the_directory(tmp_path):
    attachment = Attachment(filename="../../outside.txt", content=b"payload")
    written = attachment.save(tmp_path)
    assert written == os.path.join(str(tmp_path), "outside.txt")
    assert (tmp_path / "outside.txt").read_bytes() == b"payload"
    assert not (tmp_path.parent / "outside.txt").exists()


def test_extensions_and_mime_types_are_normalised():
    policy = AttachmentPolicy(allowed_extensions=["PDF", ".Txt"], allowed_mime_types=["Image/*", "application/PDF"])
    assert policy.allowed_extensions == frozenset({".pdf", ".txt"})
    assert policy.allows_extension("Report.PDF")
    assert not policy.allows_extension("report.pdf.exe")
    assert policy.allows_mime_type("image/png")
    assert policy.allows_mime_type("APPLICATION/pdf")
    assert not policy.allows_mime_type("text/html")


def test_a_policy_without_type_sets_allows_every_type():
    policy = AttachmentPolicy()
    assert policy.allows_extension("anything.exe")
    assert policy.allows_mime_type("application/x-msdownload")


@pytest.mark.parametrize("settings", [
    {"max_file_size": -1}, {"max_total_size": 1.5}, {"max_count": True}, {"max_count": "3"},
    {"allowed_extensions": "pdf"}, {"allowed_extensions": [""]}, {"allowed_mime_types": [1]},
    {"allowed_mime_types": 7},
])
def test_an_invalid_policy_is_refused(settings):
    with pytest.raises(MailThunderAttachmentException):
        AttachmentPolicy(**settings)


def test_the_default_policy_is_25_mebibytes_of_any_type():
    assert DEFAULT_ATTACHMENT_POLICY.max_file_size == 25 * MEBIBYTE
    assert DEFAULT_ATTACHMENT_POLICY.max_total_size == 25 * MEBIBYTE
    assert DEFAULT_ATTACHMENT_POLICY.max_count is None
    assert DEFAULT_ATTACHMENT_POLICY.allowed_extensions is None


def test_attachments_within_the_policy_pass_and_report_their_total(tmp_path):
    attachments = [Attachment.from_path(_file(tmp_path, "a.txt", 3)), Attachment(filename="b.txt", content=b"12345")]
    policy = AttachmentPolicy(max_file_size=5, max_total_size=8, max_count=2, allowed_extensions={"txt"})
    assert validate_attachments(attachments, policy) == 8
    assert validate_attachments([], policy) == 0


def test_too_many_attachments(tmp_path):
    attachments = [Attachment(filename=f"{number}.txt", content=b"x") for number in range(3)]
    policy = AttachmentPolicy(max_count=2)
    with pytest.raises(AttachmentCountExceeded) as raised:
        validate_attachments(attachments, policy)
    assert (raised.value.count, raised.value.limit) == (3, 2)


def test_a_missing_file_fails_before_the_size_rules(tmp_path):
    attachments = [Attachment.from_path(tmp_path / "missing.pdf")]
    policy = AttachmentPolicy(max_file_size=1)
    with pytest.raises(AttachmentNotFound):
        validate_attachments(attachments, policy)


def test_one_attachment_too_large():
    attachments = [Attachment(filename="big.bin", content=b"x" * 11)]
    policy = AttachmentPolicy(max_file_size=10)
    with pytest.raises(AttachmentTooLarge) as raised:
        validate_attachments(attachments, policy)
    assert (raised.value.filename, raised.value.size, raised.value.limit) == ("big.bin", 11, 10)


def test_an_extension_that_is_not_allowed():
    policy = AttachmentPolicy(allowed_extensions={".pdf"})
    attachments = [Attachment(filename="report.pdf.exe", content=b"x")]
    with pytest.raises(AttachmentTypeNotAllowed) as raised:
        validate_attachments(attachments, policy)
    assert (raised.value.kind, raised.value.value) == ("extension", ".exe")


def test_a_mime_type_that_is_not_allowed():
    policy = AttachmentPolicy(allowed_mime_types={"image/*"})
    attachment = Attachment(filename="page.html", content_type="text/html", content=b"x")
    with pytest.raises(AttachmentTypeNotAllowed) as raised:
        validate_attachments([attachment], policy)
    assert (raised.value.kind, raised.value.value) == ("MIME type", "text/html")


def test_the_total_size_is_checked_after_each_file():
    attachments = [Attachment(filename="a.bin", content=b"x" * 6), Attachment(filename="b.bin", content=b"x" * 6)]
    policy = AttachmentPolicy(max_file_size=10, max_total_size=10)
    with pytest.raises(TotalAttachmentSizeExceeded) as raised:
        validate_attachments(attachments, policy)
    assert (raised.value.size, raised.value.limit) == (12, 10)


@pytest.mark.parametrize("error", [
    AttachmentNotFound("a"), AttachmentTooLarge("a", 2, 1), AttachmentTypeNotAllowed("a", "extension", ".exe"),
    AttachmentCountExceeded(2, 1), TotalAttachmentSizeExceeded(2, 1),
])
def test_every_attachment_error_is_a_mail_thunder_exception(error):
    assert isinstance(error, MailThunderAttachmentException)
    assert isinstance(error, MailThunderException)
    assert str(error)
