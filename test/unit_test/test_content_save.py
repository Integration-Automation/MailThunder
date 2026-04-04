import json
import os

from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_data import mail_thunder_content_data_dict
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import (
    read_output_content,
    write_output_content,
)

CONTENT_FILE = "mail_thunder_content.json"


def setup_function():
    mail_thunder_content_data_dict.update({"user": None, "password": None})


def teardown_function():
    if os.path.exists(CONTENT_FILE):
        os.remove(CONTENT_FILE)
    mail_thunder_content_data_dict.update({"user": None, "password": None})


def test_write_and_read_output_content():
    mail_thunder_content_data_dict.update({"user": "test_user", "password": "test_pw"})
    write_output_content()
    assert os.path.exists(CONTENT_FILE)
    with open(CONTENT_FILE) as f:
        data = json.load(f)
    assert data["user"] == "test_user"
    assert data["password"] == "test_pw"


def test_read_output_content_returns_dict():
    mail_thunder_content_data_dict.update({"user": "u", "password": "p"})
    write_output_content()
    mail_thunder_content_data_dict.update({"user": None, "password": None})
    result = read_output_content()
    assert isinstance(result, dict)
    assert result["user"] == "u"
    assert result["password"] == "p"


def test_read_output_content_updates_global_dict():
    mail_thunder_content_data_dict.update({"user": "u2", "password": "p2"})
    write_output_content()
    mail_thunder_content_data_dict.update({"user": None, "password": None})
    read_output_content()
    assert mail_thunder_content_data_dict["user"] == "u2"
    assert mail_thunder_content_data_dict["password"] == "p2"


def test_read_output_content_no_file():
    result = read_output_content()
    assert result is None


def test_write_none_content():
    write_output_content()
    assert os.path.exists(CONTENT_FILE)
    with open(CONTENT_FILE) as f:
        data = json.load(f)
    assert data["user"] is None
    assert data["password"] is None
