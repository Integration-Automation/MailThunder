"""
How the SMTP and IMAP wrappers find credentials and log in, pinned before the login code is reorganised.

No server is contacted: the wrappers are built without connecting and their ``login`` is replaced.
"""
import inspect
import json
import smtplib
from imaplib import IMAP4_SSL
from smtplib import SMTP_SSL

import pytest

from je_mail_thunder.imap.imap_wrapper import IMAPWrapper
from je_mail_thunder.smtp.smtp_wrapper import SMTPWrapper
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import read_output_content

_ENV_USER = "mail_thunder_user"
_ENV_PASSWORD = _ENV_USER + "_password"


@pytest.fixture
def clean_place(tmp_path, monkeypatch):
    """An empty cwd (no mail_thunder_content.json) and no credential variables."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(_ENV_USER, raising=False)
    monkeypatch.delenv(_ENV_PASSWORD, raising=False)
    return tmp_path


def _write_content(directory, content):
    (directory / "mail_thunder_content.json").write_text(json.dumps(content), encoding="utf-8")


@pytest.mark.parametrize("wrapper", [SMTPWrapper, IMAPWrapper])
def test_the_content_file_wins_over_the_environment(wrapper, clean_place, monkeypatch):
    _write_content(clean_place, {"user": "file@example.com", "password": "file-secret"})
    monkeypatch.setenv(_ENV_USER, "env@example.com")
    monkeypatch.setenv(_ENV_PASSWORD, "env-secret")
    assert wrapper._resolve_credentials() == ("file@example.com", "file-secret")


@pytest.mark.parametrize("wrapper", [SMTPWrapper, IMAPWrapper])
@pytest.mark.parametrize("content", [None, {"user": "file@example.com"}, {"password": "only"}])
def test_an_incomplete_or_missing_file_falls_back_to_the_environment(wrapper, content, clean_place, monkeypatch):
    if content is not None:
        _write_content(clean_place, content)
    monkeypatch.setenv(_ENV_USER, "env@example.com")
    monkeypatch.setenv(_ENV_PASSWORD, "env-secret")
    assert wrapper._resolve_credentials() == ("env@example.com", "env-secret")


@pytest.mark.parametrize("wrapper", [SMTPWrapper, IMAPWrapper])
def test_a_content_file_that_is_not_an_object_is_ignored(wrapper, clean_place, monkeypatch):
    """It used to raise ValueError inside read_output_content (dict.update of a list)."""
    _write_content(clean_place, ["not", "an object"])
    monkeypatch.setenv(_ENV_USER, "env@example.com")
    monkeypatch.setenv(_ENV_PASSWORD, "env-secret")
    assert read_output_content() is None
    assert wrapper._resolve_credentials() == ("env@example.com", "env-secret")


@pytest.mark.parametrize("wrapper", [SMTPWrapper, IMAPWrapper])
def test_no_credentials_anywhere_is_none(wrapper, clean_place, monkeypatch):
    monkeypatch.setenv(_ENV_USER, "env@example.com")
    assert wrapper._resolve_credentials() is None


def _unconnected(wrapper):
    instance = wrapper.__new__(wrapper)
    instance.calls = []
    return instance


def test_smtp_login_uses_the_credentials_and_sets_the_state(clean_place):
    _write_content(clean_place, {"user": "file@example.com", "password": "file-secret"})
    smtp = _unconnected(SMTPWrapper)
    smtp.login = lambda user, password: smtp.calls.append((user, password))
    assert smtp.try_to_login_with_env_or_content() is True
    assert smtp.login_state is True
    assert smtp.calls == [("file@example.com", "file-secret")]


@pytest.mark.parametrize("error", [smtplib.SMTPAuthenticationError(535, b"rejected"), OSError("network down")])
def test_smtp_login_failure_is_logged_and_returns_false(error, clean_place):
    _write_content(clean_place, {"user": "file@example.com", "password": "file-secret"})
    smtp = _unconnected(SMTPWrapper)

    def refuse(_user, _password):
        raise error

    smtp.login = refuse
    assert smtp.try_to_login_with_env_or_content() is False
    assert smtp.login_state is False


def test_smtp_without_credentials_does_not_log_in(clean_place):
    smtp = _unconnected(SMTPWrapper)
    smtp.login = lambda *args: smtp.calls.append(args)
    assert smtp.try_to_login_with_env_or_content() is False
    assert smtp.calls == []


def test_smtp_later_init_swallows_what_the_login_raises(clean_place):
    _write_content(clean_place, {"user": "u", "password": "p"})
    smtp = _unconnected(SMTPWrapper)

    def explode(_user, _password):
        raise smtplib.SMTPServerDisconnected("gone")

    smtp.login = explode
    assert smtp.later_init() is None


def test_imap_login_uses_the_credentials_and_logs_os_errors(clean_place):
    _write_content(clean_place, {"user": "file@example.com", "password": "file-secret"})
    imap = _unconnected(IMAPWrapper)
    imap.login = lambda user, password: imap.calls.append((user, password))
    assert imap.try_to_login_with_env_or_content() is None
    assert imap.calls == [("file@example.com", "file-secret")]

    def refuse(_user, _password):
        raise OSError("network down")

    imap.login = refuse
    assert imap.try_to_login_with_env_or_content() is None


def test_smtp_quit_clears_the_state_even_without_a_connection():
    smtp = _unconnected(SMTPWrapper)
    smtp.login_state = True
    smtp.sock = None
    smtp.quit()
    assert smtp.login_state is False


def test_the_wrappers_keep_their_bases_and_defaults():
    assert issubclass(SMTPWrapper, SMTP_SSL)
    assert issubclass(IMAPWrapper, IMAP4_SSL)
    smtp_defaults = inspect.signature(SMTPWrapper.__init__).parameters
    assert smtp_defaults["host"].default == "smtp.gmail.com"
    assert smtp_defaults["port"].default == 465
    assert inspect.signature(IMAPWrapper.__init__).parameters["host"].default == "imap.gmail.com"
    for name in ("create_message", "create_message_with_attach"):
        assert isinstance(inspect.getattr_static(SMTPWrapper, name), staticmethod)
