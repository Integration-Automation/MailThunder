import pytest

from je_mail_thunder.utils.exception.exceptions import AddCommandException, ExecuteActionException
from je_mail_thunder.utils.executor.action_executor import (
    executor,
    execute_action,
    execute_files,
    add_command_to_executor,
)
from je_mail_thunder.utils.json.json_file import write_action_json


def test_execute_builtin_print(capsys):
    execute_action([["print", ["hello from test"]]])
    captured = capsys.readouterr()
    assert "hello from test" in captured.out


def test_execute_builtin_len():
    result = execute_action([["len", [[1, 2, 3]]]])
    assert any(v == 3 for v in result.values())


def test_execute_action_empty_list_logs_error():
    result = execute_action([])
    assert result == {}


def test_execute_action_invalid_action():
    result = execute_action([["nonexistent_action_xyz"]])
    assert len(result) == 1
    error_value = list(result.values())[0]
    assert "Error" in error_value or "error" in error_value or "None" in str(type(error_value))


def test_add_command_to_executor():
    def custom_func(x):
        return x * 2

    add_command_to_executor({"my_double": custom_func})
    assert "my_double" in executor.event_dict
    result = execute_action([["my_double", [5]]])
    assert any(v == 10 for v in result.values())


def test_add_command_non_function_raises():
    with pytest.raises(AddCommandException):
        add_command_to_executor({"bad_command": "not_a_function"})


def test_execute_action_with_dict_input():
    def noop():
        return "ok"

    add_command_to_executor({"test_noop": noop})
    result = execute_action({"auto_control": [["test_noop"]]})
    assert any(v == "ok" for v in result.values())


def test_execute_action_dict_without_auto_control():
    with pytest.raises(ExecuteActionException):
        execute_action({"wrong_key": []})


def test_execute_files(tmp_path):
    def greet(name):
        return f"hello {name}"

    add_command_to_executor({"greet": greet})

    file1 = str(tmp_path / "action1.json")
    file2 = str(tmp_path / "action2.json")
    write_action_json(file1, [["greet", ["Alice"]]])
    write_action_json(file2, [["greet", ["Bob"]]])

    results = execute_files([file1, file2])
    assert len(results) == 2
    assert any("hello Alice" in str(v) for r in results for v in r.values())
    assert any("hello Bob" in str(v) for r in results for v in r.values())
