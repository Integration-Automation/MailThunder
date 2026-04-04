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
    result = read_action_json("nonexistent_file_12345.json")
    assert result is None


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
