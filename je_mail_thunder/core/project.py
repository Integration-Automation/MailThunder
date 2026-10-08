"""
The project mail layer: an automation project keeps how it mails in its own ``mail/`` directory, and its code
asks for a ready :class:`~je_mail_thunder.core.mail.Mail` without naming a provider.

.. code-block:: text

    MyProject/
      mail/
        config.py       PROVIDER, AUTH or ACCOUNT, ATTACHMENT_POLICY, AUDIT (all optional)
        triggers.py     register(mail): the project's event handlers and watched folders
        templates/      the project's mail templates

``config.py`` and ``triggers.py`` are Python files of the project and are run when its layer is loaded, like any
other module of it: load only the layer of a project whose code is trusted.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Optional, Union

from je_mail_thunder.attachments.policy import AttachmentPolicy
from je_mail_thunder.auth.base import Authentication
from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.monitoring.audit import AuditLog
from je_mail_thunder.templates.loader import TemplateLoader, shared_template_directory
from je_mail_thunder.utils.exception.exceptions import MailThunderException, MailThunderProjectException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

MAIL_DIRECTORY = "mail"
CONFIG_FILE = "config.py"
TRIGGERS_FILE = "triggers.py"
TEMPLATES_DIRECTORY = "templates"
AUDIT_FILE = "audit.jsonl"
# The names config.py may define, and what each must be.
_SETTINGS: Dict[str, type] = {
    "PROVIDER": str, "AUTH": Authentication, "ACCOUNT": MailAccount, "ATTACHMENT_POLICY": AttachmentPolicy,
}
PathLike = Union[str, "os.PathLike[str]"]


def mail_layer_directory(project: Optional[PathLike] = None) -> Path:
    """
    :param project: the project's directory; the working directory by default
    :return: its ``mail`` directory
    :raises MailThunderProjectException: the project has no ``mail`` directory
    """
    directory = Path(project if project is not None else Path.cwd()) / MAIL_DIRECTORY
    if not directory.is_dir():
        raise MailThunderProjectException(f"no mail layer: {str(directory)!r} is not a directory")
    return directory


def _load(path: Path) -> ModuleType:
    """Run one Python file of the layer and return it as a module."""
    name = f"_mail_thunder_project_{abs(hash(str(path.resolve())))}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Registered while it runs, as importing it would: dataclasses and pickling look their module up by name.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except MailThunderException:
        raise
    except Exception as error:
        raise MailThunderProjectException(f"{str(path)!r} could not be loaded: {error!r}") from error
    finally:
        sys.modules.pop(name, None)
    return module


def _settings(directory: Path) -> Dict[str, Any]:
    """The names ``config.py`` defines, checked for their types."""
    config_file = directory / CONFIG_FILE
    if not config_file.is_file():
        return {}
    module = _load(config_file)
    settings: Dict[str, Any] = {}
    for name, expected in _SETTINGS.items():
        value = getattr(module, name, None)
        if value is None:
            continue
        if not isinstance(value, expected):
            raise MailThunderProjectException(f"{name} in {str(config_file)!r} must be a {expected.__name__}")
        settings[name] = value
    if "ACCOUNT" in settings and ("PROVIDER" in settings or "AUTH" in settings):
        raise MailThunderProjectException(f"{str(config_file)!r}: set ACCOUNT, or PROVIDER and AUTH, not both")
    settings["AUDIT"] = getattr(module, "AUDIT", False)
    return settings


def _audit_log(directory: Path, setting: Any) -> Optional[AuditLog]:
    if setting is True:
        return AuditLog(directory / AUDIT_FILE)
    if isinstance(setting, (str, os.PathLike)) and str(setting):
        return AuditLog(setting)
    if setting in (False, None):
        return None
    raise MailThunderProjectException("AUDIT is True, False or the path of the audit file")


def project_mail(project: Optional[PathLike] = None) -> Mail:
    """
    The ``Mail`` of a project, as its ``mail/`` directory describes it.

    :param project: the project's directory; the working directory by default
    :return: a ``Mail`` with the project's provider, login, attachment policy and templates
        (``mail/templates`` first, then the shared ones), its audit log attached and its triggers registered.
        Nothing connects until it is used, and no trigger runs unless ``triggers.py`` starts one
    :raises MailThunderProjectException: there is no mail layer, or a file of it cannot be used
    """
    directory = mail_layer_directory(project)
    mail_thunder_logger.info(f"project_mail, loading {str(directory)!r}")
    settings = _settings(directory)
    mail = Mail(
        provider=settings.get("PROVIDER"), auth=settings.get("AUTH"), account=settings.get("ACCOUNT"),
        policy=settings.get("ATTACHMENT_POLICY"),
        templates=TemplateLoader([directory / TEMPLATES_DIRECTORY, shared_template_directory()]),
    )
    audit = _audit_log(directory, settings.get("AUDIT", False))
    if audit is not None:
        audit.attach(mail.events)
    triggers_file = directory / TRIGGERS_FILE
    if triggers_file.is_file():
        module = _load(triggers_file)
        if not callable(getattr(module, "register", None)):
            raise MailThunderProjectException(f"{str(triggers_file)!r} must define register(mail)")
        module.register(mail)
    return mail


def describe_mail_layer(project: Optional[PathLike] = None) -> dict:
    """
    What a project's mail layer consists of, from the file system alone: no file of it is run.

    :param project: the project's directory; the working directory by default
    :return: the directory, which of ``config.py`` and ``triggers.py`` exist, and the template names
    :raises MailThunderProjectException: the project has no ``mail`` directory
    """
    directory = mail_layer_directory(project)
    return {
        "directory": str(directory),
        "config": (directory / CONFIG_FILE).is_file(),
        "triggers": (directory / TRIGGERS_FILE).is_file(),
        "templates": TemplateLoader([directory / TEMPLATES_DIRECTORY]).names(),
    }
