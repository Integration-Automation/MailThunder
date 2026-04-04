import os

from je_mail_thunder.utils.save_mail_user_content.save_on_env import (
    get_mail_thunder_os_environ,
    set_mail_thunder_os_environ,
)


def teardown_function():
    os.environ.pop("mail_thunder_user", None)
    os.environ.pop("mail_thunder_user_password", None)


def test_get_returns_none_when_not_set():
    os.environ.pop("mail_thunder_user", None)
    os.environ.pop("mail_thunder_user_password", None)
    result = get_mail_thunder_os_environ()
    assert result["mail_thunder_user"] is None
    assert result["mail_thunder_user_password"] is None


def test_set_and_get():
    set_mail_thunder_os_environ("user@test.com", "secret123")
    result = get_mail_thunder_os_environ()
    assert result["mail_thunder_user"] == "user@test.com"
    assert result["mail_thunder_user_password"] == "secret123"


def test_set_overwrites_previous():
    set_mail_thunder_os_environ("old_user", "old_pw")
    set_mail_thunder_os_environ("new_user", "new_pw")
    result = get_mail_thunder_os_environ()
    assert result["mail_thunder_user"] == "new_user"
    assert result["mail_thunder_user_password"] == "new_pw"
