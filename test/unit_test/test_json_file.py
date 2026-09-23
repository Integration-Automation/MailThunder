import json
import os

import pytest

from je_mail_thunder.utils.exception.exceptions import JsonActionException
from je_mail_thunder.utils.json.json_file import read_action_json, write_action_json

TEST_JSON_PATH = "test_action.json"


def teardown_function():
    if os.path.exists(TEST_JSON_PATH):
        os.remove(TEST_JSON_PATH)


def test_write_and_read_action_json():
    data = [["MT_smtp_later_init"], ["smtp_quit"]]
    write_action_json(TEST_JSON_PATH, data)
    result = read_action_json(TEST_JSON_PATH)
    assert result == data


def test_read_action_json_nonexistent_file():
    with pytest.raises(JsonActionException, match="nonexistent_file_12345.json"):
        read_action_json("nonexistent_file_12345.json")


def test_write_action_json_creates_file():
    data = [["some_action", {"key": "value"}]]
    write_action_json(TEST_JSON_PATH, data)
    assert os.path.exists(TEST_JSON_PATH)
    with open(TEST_JSON_PATH) as f:
        content = json.load(f)
    assert content == data


def test_read_action_json_with_nested_data():
    data = [["action", {"param1": "val1", "param2": [1, 2, 3]}]]
    write_action_json(TEST_JSON_PATH, data)
    result = read_action_json(TEST_JSON_PATH)
    assert result == data


def test_action_json_is_utf8_whatever_the_locale(tmp_path):
    # Characters outside cp950, the locale encoding of a zh-TW Windows console.
    path = tmp_path / "actions.json"
    data = [["MT_smtp_create_message_and_send", {"subject": "測試 😀"}]]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert read_action_json(str(path)) == data
    write_action_json(str(path), data)
    assert "測試 😀" in path.read_text(encoding="utf-8")


def test_read_action_json_invalid_json_raises(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("[[", encoding="utf-8")
    with pytest.raises(JsonActionException):
        read_action_json(str(path))
