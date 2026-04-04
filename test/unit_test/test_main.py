import json
import os
import subprocess
import sys
import tempfile

from je_mail_thunder.utils.executor.action_executor import add_command_to_executor
from je_mail_thunder.utils.json.json_file import write_action_json


def test_main_execute_file(tmp_path):
    action_file = str(tmp_path / "action.json")
    write_action_json(action_file, [["print", ["main_test_output"]]])
    result = subprocess.run(
        [sys.executable, "-m", "je_mail_thunder", "-e", action_file],
        capture_output=True,
        text=True,
    )
    assert "main_test_output" in result.stdout


def test_main_execute_dir(tmp_path):
    action_file = str(tmp_path / "action.json")
    write_action_json(action_file, [["print", ["dir_test_output"]]])
    result = subprocess.run(
        [sys.executable, "-m", "je_mail_thunder", "-d", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert "dir_test_output" in result.stdout


def test_main_execute_str():
    action_list = [["print", ["str_test_output"]]]
    if sys.platform in ["win32", "cygwin", "msys"]:
        # Windows: __main__.py does double json.loads, so double-encode
        action_json = json.dumps(json.dumps(action_list))
    else:
        action_json = json.dumps(action_list)
    result = subprocess.run(
        [sys.executable, "-m", "je_mail_thunder", "--execute_str", action_json],
        capture_output=True,
        text=True,
    )
    assert "str_test_output" in result.stdout


def test_main_no_args_exits_with_error():
    result = subprocess.run(
        [sys.executable, "-m", "je_mail_thunder"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "MailThunderArgparseException" in result.stderr


def test_main_create_project(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "je_mail_thunder", "-c", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert os.path.isdir(os.path.join(str(tmp_path), "MailThunder"))
