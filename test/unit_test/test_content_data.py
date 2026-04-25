import secrets

from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_data import (
    is_need_to_save_content,
    mail_thunder_content_data_dict,
)


def setup_function():
    mail_thunder_content_data_dict.update({"user": None, "password": None})


def test_is_need_to_save_content_all_none():
    assert is_need_to_save_content() is False


def test_is_need_to_save_content_user_set():
    mail_thunder_content_data_dict["user"] = "test_user"
    assert is_need_to_save_content() is True


def test_is_need_to_save_content_password_set():
    mail_thunder_content_data_dict["password"] = secrets.token_hex(8)
    assert is_need_to_save_content() is True


def test_is_need_to_save_content_both_set():
    mail_thunder_content_data_dict["user"] = "test_user"
    mail_thunder_content_data_dict["password"] = secrets.token_hex(8)
    assert is_need_to_save_content() is True
