"""
The project mail layer: what ``create_project_dir`` scaffolds, and the ``Mail`` that ``project_mail`` builds
from a project's ``mail/`` directory.
"""
import json
import sys

import pytest

from je_mail_thunder import create_project_dir
from je_mail_thunder.attachments.policy import DEFAULT_ATTACHMENT_POLICY
from je_mail_thunder.core.project import describe_mail_layer, mail_layer_directory, project_mail
from je_mail_thunder.providers.file import FileProvider
from je_mail_thunder.templates.loader import shared_template_directory
from je_mail_thunder.utils.exception.exceptions import (
    AttachmentTypeNotAllowed,
    MailThunderProjectException,
    MailThunderTriggerException,
)

_LAYER_FILES = ["config.py", "templates/test_report/body.html", "templates/test_report/body.txt",
                "templates/test_report/subject.txt", "templates/test_report/template.json", "triggers.py"]


@pytest.fixture()
def project(tmp_path, monkeypatch):
    """A scaffolded project whose file provider writes inside it."""
    create_project_dir(project_path=str(tmp_path), parent_name="Demo")
    monkeypatch.setenv("MAIL_THUNDER_FILE_PROVIDER_DIR", str(tmp_path / "Demo" / "outbox"))
    return tmp_path / "Demo"


def _layer(tmp_path, config=None, triggers=None):
    """A project with only the layer files that are given."""
    mail_dir = tmp_path / "Bare" / "mail"
    mail_dir.mkdir(parents=True)
    if config is not None:
        (mail_dir / "config.py").write_text(config, encoding="utf-8")
    if triggers is not None:
        (mail_dir / "triggers.py").write_text(triggers, encoding="utf-8")
    return tmp_path / "Bare"


def test_a_scaffolded_project_has_a_mail_layer(project):
    mail_dir = project / "mail"
    found = sorted(path.relative_to(mail_dir).as_posix() for path in mail_dir.rglob("*") if path.is_file())
    assert found == _LAYER_FILES
    assert (project / "keyword" / "keyword1.json").is_file() and (project / "executor").is_dir()
    assert describe_mail_layer(project) == {
        "directory": str(mail_dir), "config": True, "triggers": True, "templates": ["test_report"]}
    assert json.loads((mail_dir / "templates" / "test_report" / "template.json").read_text(encoding="utf-8"))[
        "variables"]["failed"]["default"] == 0


def test_scaffolding_again_keeps_the_projects_own_files(project, tmp_path):
    config = project / "mail" / "config.py"
    config.write_text('PROVIDER = "google"\n', encoding="utf-8")
    (project / "mail" / "triggers.py").unlink()
    create_project_dir(project_path=str(tmp_path), parent_name="Demo")
    assert config.read_text(encoding="utf-8") == 'PROVIDER = "google"\n'
    assert (project / "mail" / "triggers.py").is_file()


def test_the_scaffolded_layer_gives_a_working_mail(project):
    before = set(sys.modules)
    mail = project_mail(project)
    assert not [name for name in set(sys.modules) - before if name.startswith("_mail_thunder_project_")]
    assert mail.account.provider == "file" and isinstance(mail.providers[0], FileProvider)
    assert mail.policy.max_count == 10 and ".html" in mail.policy.allowed_extensions
    assert mail.templates.directories == (project / "mail" / "templates", shared_template_directory())
    assert [subscription.event for subscription in mail.events.subscriptions] == [
        "*", "message_received", "message_failed"]
    (backend,) = mail.triggers.backends
    assert backend.folder == "INBOX" and not backend.running
    sent = mail.send(to="qa@example.com", sender="ci@example.com", template="test_report", context={
        "project": "Demo", "passed": 3, "failed": 1, "failures": [{"name": "login", "reason": "timeout"},
                                                                  {"name": "logout"}]})
    assert sent.subject == "[Demo] 3 passed, 1 failed"
    assert "  1. login: timeout\n  2. logout: no reason given\n" in sent.text
    assert "<li>login: timeout</li>" in sent.html and "Everything passed" not in sent.html
    passed = mail.render("test_report", {"project": "Demo", "passed": 4})
    assert passed.subject == "[Demo] 4 passed, 0 failed" and "Everything passed." in passed.text
    assert len(list((project / "outbox" / "Sent").glob("*.eml"))) == 1
    program = project / "setup.exe"
    program.write_bytes(b"MZ")
    with pytest.raises(AttachmentTypeNotAllowed):
        mail.send(to="qa@example.com", sender="ci@example.com", text="x", attachments=[program])
    events = [json.loads(line)["event"] for line in
              (project / "mail" / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events == ["message_sent", "attachment_rejected", "message_failed"]
    assert mail.triggers.poll() == 0
    mail.close()


def test_a_layer_without_files_is_the_default_mail(tmp_path, monkeypatch):
    monkeypatch.chdir(_layer(tmp_path))
    for name in ("mail_thunder_mail_provider", "mail_thunder_oauth2_access_token", "mail_thunder_oauth2_refresh_token"):
        monkeypatch.delenv(name, raising=False)
    mail = project_mail()
    assert mail.account.provider == "google" and mail.policy is DEFAULT_ATTACHMENT_POLICY
    assert mail.events.subscriptions == () and mail.triggers.backends == ()
    assert mail.templates.directories[0] == tmp_path / "Bare" / "mail" / "templates"
    assert mail_layer_directory() == tmp_path / "Bare" / "mail"
    assert describe_mail_layer() == {"directory": str(tmp_path / "Bare" / "mail"), "config": False,
                                     "triggers": False, "templates": []}


def test_the_config_can_name_a_login_or_a_whole_account(tmp_path):
    with_auth = _layer(tmp_path, config=(
        "from je_mail_thunder import AppPasswordAuth\n"
        'PROVIDER = "yahoo"\n'
        'AUTH = AppPasswordAuth("me@yahoo.com", "abcd efgh")\n'
        f'AUDIT = r"{tmp_path / "elsewhere.jsonl"}"\n'))
    mail = project_mail(with_auth)
    assert (mail.account.provider, mail.account.authentication().user) == ("yahoo", "me@yahoo.com")
    assert len(mail.events.subscriptions) == 1
    (tmp_path / "Bare" / "mail" / "config.py").write_text(
        "from je_mail_thunder import MailAccount, MailServers, PasswordAuth\n"
        'ACCOUNT = MailAccount(provider="smtp", auth=PasswordAuth("me@example.com", "secret"),\n'
        '                      servers=MailServers(smtp_host="smtp.example.com", imap_host="imap.example.com"))\n',
        encoding="utf-8")
    account = project_mail(with_auth).account
    assert (account.provider, account.resolved_servers.smtp_host) == ("smtp", "smtp.example.com")


@pytest.mark.parametrize("config, message", [
    ("PROVIDER = 5\n", "PROVIDER in .* must be a str"),
    ('AUTH = "me@example.com"\n', "AUTH in .* must be a Authentication"),
    ("ATTACHMENT_POLICY = {'max_count': 1}\n", "ATTACHMENT_POLICY in .* must be a AttachmentPolicy"),
    ("from je_mail_thunder import MailAccount\nACCOUNT = MailAccount()\nPROVIDER = 'google'\n", "not both"),
    ("AUDIT = 5\n", "AUDIT is True, False or the path"),
    ("raise RuntimeError('broken config')\n", "could not be loaded: RuntimeError\\('broken config'\\)"),
    ("def broken(:\n", "could not be loaded: SyntaxError"),
])
def test_a_config_that_cannot_be_used_names_its_file(config, message, tmp_path):
    with pytest.raises(MailThunderProjectException, match=message):
        project_mail(_layer(tmp_path, config=config))


def test_triggers_must_define_register_and_its_errors_are_reported(tmp_path):
    with pytest.raises(MailThunderProjectException, match="must define register\\(mail\\)"):
        project_mail(_layer(tmp_path, triggers="HANDLERS = []\n"))
    (tmp_path / "Bare" / "mail" / "triggers.py").write_text(
        "def register(mail):\n    mail.on('message_recieved', print)\n", encoding="utf-8")
    with pytest.raises(MailThunderTriggerException, match="unknown event 'message_recieved'"):
        project_mail(tmp_path / "Bare")


def test_describing_a_layer_runs_none_of_its_code_and_a_project_needs_a_layer(tmp_path):
    broken = _layer(tmp_path, config="raise SystemExit('never run')\n", triggers="raise SystemExit('never run')\n")
    assert describe_mail_layer(broken)["config"] is True
    for call in (project_mail, describe_mail_layer, mail_layer_directory):
        with pytest.raises(MailThunderProjectException, match="no mail layer"):
            call(tmp_path / "Nowhere")
