"""
Where mail templates come from: the project's own ``mail/templates`` directory first, then the templates shared
by every project of the account.

A template is either one JSON file, ``<name>.json``, holding ``subject`` / ``text`` / ``html`` / ``variables`` /
``metadata``, or a directory ``<name>/`` with ``subject.txt``, ``body.txt``, ``body.html`` and an optional
``template.json`` for the variables and metadata.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from je_mail_thunder.templates.template import MailTemplate
from je_mail_thunder.utils.exception.exceptions import MailThunderTemplateException, TemplateNotFound
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

#: Environment variable that names the shared template directory.
TEMPLATE_DIRECTORY_ENV = "MAIL_THUNDER_TEMPLATE_DIR"
#: Where a project keeps its own templates, under its working directory.
PROJECT_TEMPLATE_DIRECTORY = Path("mail") / "templates"
# A template part is a mail, not a document store.
MAX_TEMPLATE_FILE_BYTES = 1024 * 1024
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_PART_FILES = {"subject": "subject.txt", "text": "body.txt", "html": "body.html"}
_DETAILS_FILE = "template.json"


def shared_template_directory() -> Path:
    """
    :return: ``$MAIL_THUNDER_TEMPLATE_DIR``, else ``~/.je_mail_thunder/templates``
    """
    configured = os.environ.get(TEMPLATE_DIRECTORY_ENV, "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".je_mail_thunder" / "templates"


def _read(path: Path) -> str:
    if path.stat().st_size > MAX_TEMPLATE_FILE_BYTES:
        raise MailThunderTemplateException(f"the template file {path} is over {MAX_TEMPLATE_FILE_BYTES} bytes")
    with open(path, "r", encoding="utf-8") as template_file:
        return template_file.read()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(_read(path))
    except ValueError as error:
        raise MailThunderTemplateException(f"the template file {path} is not valid JSON: {error}") from error


def _from_directory(name: str, directory: Path) -> MailTemplate:
    details_file = directory / _DETAILS_FILE
    values: Dict[str, Any] = dict(_read_json(details_file)) if details_file.is_file() else {}
    for part, filename in _PART_FILES.items():
        if (directory / filename).is_file():
            values[part] = _read(directory / filename)
    return MailTemplate.from_mapping(name, values)


class TemplateLoader:
    """Finds templates by name in a list of directories; the first directory that has the name wins."""

    def __init__(self, directories: Optional[Iterable[Union[str, "os.PathLike[str]"]]] = None) -> None:
        """
        :param directories: where to look, in order; by default the project's ``mail/templates`` (under the
            working directory at the time of the lookup), then the shared directory
        """
        self._directories = None if directories is None else tuple(Path(directory) for directory in directories)
        self._registered: Dict[str, MailTemplate] = {}

    @property
    def directories(self) -> Tuple[Path, ...]:
        """The directories searched, in order."""
        if self._directories is not None:
            return self._directories
        return Path.cwd() / PROJECT_TEMPLATE_DIRECTORY, shared_template_directory()

    def add(self, template: MailTemplate) -> None:
        """
        Register a template built in code. It is found before any file of the same name.

        :param template: the template
        :return: None
        """
        if not isinstance(template, MailTemplate):
            raise MailThunderTemplateException(f"expected a MailTemplate, got {type(template).__name__}")
        self._registered[template.name] = template

    def load(self, name: str) -> MailTemplate:
        """
        :param name: a template's name: letters, digits, ``_``, ``-`` and ``.``, never a path
        :return: the template
        :raises TemplateNotFound: no directory has it, or the name is not a template name
        :raises MailThunderTemplateException: its files cannot be read as a template
        """
        if not isinstance(name, str) or not _NAME.fullmatch(name) or ".." in name:
            raise TemplateNotFound(str(name), ())
        if name in self._registered:
            return self._registered[name]
        try:
            for directory in self.directories:
                if (directory / f"{name}.json").is_file():
                    return MailTemplate.from_mapping(name, _read_json(directory / f"{name}.json"))
                if (directory / name).is_dir():
                    return _from_directory(name, directory / name)
        except OSError as error:
            mail_thunder_logger.error(f"template_loader, {name!r} cannot be read: {error!r}")
            raise MailThunderTemplateException(f"the template {name!r} cannot be read: {error!r}") from error
        raise TemplateNotFound(name, [str(directory) for directory in self.directories])

    def names(self) -> List[str]:
        """
        :return: the names of every template that can be loaded, sorted
        """
        found = set(self._registered)
        for directory in self.directories:
            if not directory.is_dir():
                continue
            for entry in directory.iterdir():
                name = entry.stem if entry.is_file() and entry.suffix == ".json" else entry.name
                if (entry.is_dir() or entry.suffix == ".json") and _NAME.fullmatch(name):
                    found.add(name)
        return sorted(found)
