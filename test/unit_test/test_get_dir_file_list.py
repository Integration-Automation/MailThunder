import os
import tempfile

from je_mail_thunder.utils.file_process.get_dir_file_list import get_dir_files_as_list


def test_get_dir_files_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = get_dir_files_as_list(tmpdir)
        assert result == []


def test_get_dir_files_finds_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "test.json")
        txt_path = os.path.join(tmpdir, "test.txt")
        with open(json_path, "w") as f:
            f.write("{}")
        with open(txt_path, "w") as f:
            f.write("hello")
        result = get_dir_files_as_list(tmpdir)
        assert len(result) == 1
        assert result[0].endswith("test.json")


def test_get_dir_files_custom_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        py_path = os.path.join(tmpdir, "script.py")
        with open(py_path, "w") as f:
            f.write("pass")
        result = get_dir_files_as_list(tmpdir, ".py")
        assert len(result) == 1
        assert result[0].endswith("script.py")


def test_get_dir_files_subdirectory():
    with tempfile.TemporaryDirectory() as tmpdir:
        subdir = os.path.join(tmpdir, "sub")
        os.makedirs(subdir)
        json_path = os.path.join(subdir, "nested.json")
        with open(json_path, "w") as f:
            f.write("{}")
        result = get_dir_files_as_list(tmpdir)
        assert len(result) == 1
        assert "sub" in result[0]
        assert result[0].endswith("nested.json")
        assert os.path.isfile(result[0])
