import pytest

from je_mail_thunder.utils.exception.exceptions import AddCommandException, ExecuteActionException
from je_mail_thunder.utils.executor.action_executor import (
    SAFE_BUILTINS,
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


@pytest.mark.parametrize("name", [
    "eval", "exec", "compile", "__import__", "open", "input", "breakpoint",
    "getattr", "setattr", "delattr", "globals", "locals", "vars", "dir",
])
def test_unsafe_builtin_is_not_registered(name):
    assert name not in executor.event_dict


def test_every_safe_builtin_is_registered():
    for name in SAFE_BUILTINS:
        assert callable(executor.event_dict[name])


def test_eval_action_is_rejected(tmp_path):
    marker = tmp_path / "pwned.txt"
    code = f"open({str(marker)!r}, 'w').write('x')"
    result = execute_action([["eval", [code]], ["exec", [code]]])
    assert not marker.exists()
    for value in result.values():
        assert "ExecuteActionException" in value


def test_execute_action_empty_list_logs_error():
    result = execute_action([])
    assert result == {}


def test_execute_action_invalid_action():
    result = execute_action([["nonexistent_action_xyz"]])
    assert len(result) == 1
    error_value = list(result.values())[0]
    assert "ExecuteActionException" in error_value


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


def test_smtp_quit_is_registered_under_both_names():
    """``MT_smtp_quit`` is the prefixed name; ``smtp_quit`` stays for stored action files."""
    assert executor.event_dict["MT_smtp_quit"].__name__ == "quit"
    assert executor.event_dict["smtp_quit"].__name__ == "quit"
