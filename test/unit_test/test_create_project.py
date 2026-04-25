import os
import tempfile

from je_mail_thunder.utils.project.create_project_structure import create_project_dir


def test_create_project_dir_default_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        create_project_dir(project_path=tmpdir)
        assert os.path.isdir(os.path.join(tmpdir, "MailThunder"))
        assert os.path.isdir(os.path.join(tmpdir, "MailThunder", "keyword"))
        assert os.path.isdir(os.path.join(tmpdir, "MailThunder", "executor"))


def test_create_project_dir_custom_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        create_project_dir(project_path=tmpdir, parent_name="MyProject")
        assert os.path.isdir(os.path.join(tmpdir, "MyProject"))
        assert os.path.isdir(os.path.join(tmpdir, "MyProject", "keyword"))
        assert os.path.isdir(os.path.join(tmpdir, "MyProject", "executor"))


def test_create_project_dir_generates_templates():
    with tempfile.TemporaryDirectory() as tmpdir:
        create_project_dir(project_path=tmpdir)
        keyword_dir = os.path.join(tmpdir, "MailThunder", "keyword")
        executor_dir = os.path.join(tmpdir, "MailThunder", "executor")
        assert os.path.isfile(os.path.join(keyword_dir, "keyword1.json"))
        assert os.path.isfile(os.path.join(keyword_dir, "keyword2.json"))
        assert os.path.isfile(os.path.join(keyword_dir, "bad_keyword_1.json"))
        assert os.path.isfile(os.path.join(executor_dir, "executor_one_file.py"))
        assert os.path.isfile(os.path.join(executor_dir, "executor_folder.py"))
        assert os.path.isfile(os.path.join(executor_dir, "executor_bad_file.py"))


def test_create_project_dir_idempotent():
    with tempfile.TemporaryDirectory() as tmpdir:
        create_project_dir(project_path=tmpdir)
        create_project_dir(project_path=tmpdir)
        assert os.path.isdir(os.path.join(tmpdir, "MailThunder", "keyword"))
