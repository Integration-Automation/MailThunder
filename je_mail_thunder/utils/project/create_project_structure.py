import json
from os import getcwd
from pathlib import Path
from threading import Lock

from je_mail_thunder.utils.json.json_file import write_action_json
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.project.template.template_executor import executor_template_1, \
    executor_template_2, bad_executor_template_1
from je_mail_thunder.utils.project.template.template_keyword import template_keyword_1, \
    template_keyword_2, bad_template_1
from je_mail_thunder.utils.project.template.template_mail import (
    mail_config_template,
    mail_template_details,
    mail_template_html,
    mail_template_subject,
    mail_template_text,
    mail_triggers_template,
)

_template_lock = Lock()


def create_dir(dir_name: str) -> None:
    """
    :param dir_name: create dir use dir name
    :return: None
    """
    Path(dir_name).mkdir(
        parents=True,
        exist_ok=True
    )


def _write_keyword_templates(keyword_dir: Path) -> None:
    """
    :param keyword_dir: directory to populate with keyword JSON templates
    :return: None
    """
    write_action_json(str(keyword_dir / "keyword1.json"), template_keyword_1)
    write_action_json(str(keyword_dir / "keyword2.json"), template_keyword_2)
    write_action_json(str(keyword_dir / "bad_keyword_1.json"), bad_template_1)


def _write_executor_template(executor_dir: Path, keyword_dir: Path) -> None:
    """
    :param executor_dir: directory to populate with executor Python templates
    :param keyword_dir: keyword directory referenced by the executor templates
    :return: None
    """
    substitutions = (
        ("executor_one_file.py", executor_template_1, str(keyword_dir / "keyword1.json")),
        ("executor_bad_file.py", bad_executor_template_1, str(keyword_dir / "bad_keyword_1.json")),
        ("executor_folder.py", executor_template_2, str(keyword_dir)),
    )
    for filename, template, replacement in substitutions:
        target = executor_dir / filename
        with open(str(target), "w", encoding="utf-8") as file:
            file.write(template.replace("{temp}", replacement))


def _write_mail_layer(mail_dir: Path) -> None:
    """
    :param mail_dir: the project's ``mail`` directory, to populate with its config, triggers and one template.
        A file that is already there is the project's own and is left as it is
    :return: None
    """
    report_dir = mail_dir / "templates" / "test_report"
    files = (
        (mail_dir / "config.py", mail_config_template),
        (mail_dir / "triggers.py", mail_triggers_template),
        (report_dir / "subject.txt", mail_template_subject),
        (report_dir / "body.txt", mail_template_text),
        (report_dir / "body.html", mail_template_html),
        (report_dir / "template.json", json.dumps(mail_template_details, indent=4) + "\n"),
    )
    for target, content in files:
        if not target.exists():
            with open(str(target), "w", encoding="utf-8") as file:
                file.write(content)


def create_template(parent_name: str, project_path: str = None) -> None:
    """
    :param parent_name: project subdirectory name under project_path
    :param project_path: base directory (defaults to cwd)
    :return: None
    """
    if project_path is None:
        project_path = getcwd()
    base = Path(project_path) / parent_name
    keyword_dir = base / "keyword"
    executor_dir = base / "executor"
    if keyword_dir.exists() and keyword_dir.is_dir():
        _write_keyword_templates(keyword_dir)
    if executor_dir.exists() and executor_dir.is_dir():
        with _template_lock:
            _write_executor_template(executor_dir, keyword_dir)
    mail_dir = base / "mail"
    if (mail_dir / "templates" / "test_report").is_dir():
        with _template_lock:
            _write_mail_layer(mail_dir)


def create_project_dir(project_path: str = None, parent_name: str = "MailThunder") -> None:
    """
    :param project_path: base directory (defaults to cwd)
    :param parent_name: project subdirectory name under project_path
    :return: None
    """
    mail_thunder_logger.info(f"create_project_dir, project_path: {project_path}, parent_name: {parent_name}")
    if project_path is None:
        project_path = getcwd()
    base = Path(project_path) / parent_name
    create_dir(str(base / "keyword"))
    create_dir(str(base / "executor"))
    create_dir(str(base / "mail" / "templates" / "test_report"))
    create_template(parent_name, project_path)
