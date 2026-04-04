import json

import pytest

from je_mail_thunder.utils.exception.exceptions import MailThunderJsonException
from je_mail_thunder.utils.json_format.json_process import reformat_json


def test_reformat_valid_json():
    input_str = '{"b": 2, "a": 1}'
    result = reformat_json(input_str)
    parsed = json.loads(result)
    assert parsed == {"a": 1, "b": 2}


def test_reformat_json_sorted_keys():
    input_str = '{"z": 1, "a": 2, "m": 3}'
    result = reformat_json(input_str)
    lines = result.strip().split("\n")
    keys = [line.strip().split('"')[1] for line in lines if '"' in line and ":" in line]
    assert keys == ["a", "m", "z"]


def test_reformat_invalid_json_raises():
    with pytest.raises((json.JSONDecodeError, MailThunderJsonException)):
        reformat_json("{invalid json!!!")
