"""
What MailThunder Studio shows and does, as plain functions over the core mail API: every method takes and
returns JSON-ready values, and none of them touches SMTP, IMAP or Graph directly.

Nothing here returns a password, a token or a client secret.
"""
from __future__ import annotations

import platform
from collections import deque
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from je_mail_thunder.attachments.policy import AttachmentPolicy
from je_mail_thunder.core.events import ANY_EVENT, EVENT_NAMES
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.core.project import describe_mail_layer
from je_mail_thunder.monitoring.audit import AuditLog
from je_mail_thunder.monitoring.health import ProviderHealth
from je_mail_thunder.providers.file import DIRECTORY_ENV as FILE_PROVIDER_ENV
from je_mail_thunder.providers.registry import registered_providers
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderException,
    MailThunderProjectException,
    MailThunderStudioException,
)
from je_mail_thunder.utils.logging.loggin_instance import default_log_file

MAX_LOG_LINES = 1000
_POLICY_FIELDS = ("max_file_size", "max_total_size", "max_count", "allowed_extensions", "allowed_mime_types")
_SEND_FIELDS = ("to", "cc", "bcc", "subject", "text", "html", "sender", "reply_to", "template", "context")
Route = Tuple[str, str]


def _version() -> str:
    for distribution in ("je_mail_thunder", "je_mail_thunder_dev"):
        try:
            return metadata.version(distribution)
        except metadata.PackageNotFoundError:
            continue
    return "source checkout"


def _mapping(payload: Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise MailThunderStudioException("the request body must be a JSON object")
    return payload


class StudioApi:
    """The operations behind the Studio pages, on one :class:`~je_mail_thunder.core.mail.Mail`."""

    def __init__(self, mail: Optional[Mail] = None, project: Optional[str] = None,
                 audit: Optional[AuditLog] = None) -> None:
        """
        :param mail: the ``Mail`` to show and use; ``Mail()`` by default
        :param project: the project directory the Projects page describes; the working directory by default
        :param audit: the audit log the pages read and that records what Studio does; the default one otherwise
        """
        self.mail = mail if mail is not None else Mail()
        self.project = project
        self.audit = audit if audit is not None else AuditLog()
        self.health = ProviderHealth()
        self.audit.attach(self.mail.events)
        self.health.attach(self.mail.events)
        self.routes: Dict[Route, Callable[[Any], Any]] = {
            ("GET", "/api/dashboard"): self.dashboard,
            ("GET", "/api/accounts"): self.accounts,
            ("POST", "/api/accounts/check"): self.check_accounts,
            ("GET", "/api/templates"): self.templates,
            ("POST", "/api/templates/render"): self.render_template,
            ("GET", "/api/triggers"): self.triggers,
            ("POST", "/api/triggers/poll"): self.poll_triggers,
            ("GET", "/api/policies"): self.policies,
            ("POST", "/api/policies"): self.set_policy,
            ("GET", "/api/projects"): self.projects,
            ("GET", "/api/logs"): self.logs,
            ("GET", "/api/settings"): self.settings,
            ("POST", "/api/send"): self.send,
        }

    def _account(self) -> dict:
        """Who the mail belongs to: the provider and, when there are credentials, the user and the mechanism."""
        account = self.mail.account
        described: Dict[str, Any] = {"provider": account.provider if account is not None else None,
                                     "user": None, "mechanism": None, "problem": None}
        if account is None:
            return described
        try:
            authentication = account.authentication()
        except MailThunderException as error:
            described["problem"] = str(error)
            return described
        described.update(user=authentication.user, mechanism=authentication.mechanism)
        return described

    def dashboard(self, _payload: Any = None) -> dict:
        """
        :return: the account, each provider's health, how much there is of everything, and the newest audit entries
        """
        return {
            "version": _version(),
            "account": self._account(),
            "health": self.health.report(),
            "counts": {
                "templates": len(self.mail.templates.names()),
                "subscriptions": len(self.mail.events.subscriptions),
                "triggers": len(self.mail.triggers.backends),
                "providers": len(registered_providers()),
            },
            "recent": self.audit.entries(limit=10),
        }

    def accounts(self, _payload: Any = None) -> dict:
        """
        :return: the account in use, the servers it reaches, and the provider names that can be chosen
        """
        account = self.mail.account
        servers = None
        if account is not None:
            try:
                resolved = account.resolved_servers
                servers = {"smtp_host": resolved.smtp_host, "smtp_port": resolved.port,
                           "smtp_starttls": resolved.smtp_starttls, "imap_host": resolved.imap_host}
            except MailThunderException:
                servers = None
        return {"account": self._account(), "servers": servers, "registered_providers": list(registered_providers())}

    def check_accounts(self, _payload: Any = None) -> dict:
        """
        Ask every provider of the account to connect and log in.

        :return: the health report afterwards
        """
        return {"health": self.health.probe(self.mail.providers)}

    def templates(self, _payload: Any = None) -> dict:
        """
        :return: the directories searched and every template that can be loaded; one that cannot be read is
            listed with its error
        """
        listed: List[dict] = []
        for name in self.mail.templates.names():
            try:
                listed.append(self.mail.templates.load(name).to_dict())
            except MailThunderException as error:
                listed.append({"name": name, "error": str(error)})
        return {"directories": [str(directory) for directory in self.mail.templates.directories],
                "templates": listed}

    def render_template(self, payload: Any) -> dict:
        """
        :param payload: ``{"name": ..., "context": {...}}``
        :return: the rendered subject, text and HTML; nothing is sent
        """
        payload = _mapping(payload)
        return self.mail.render(str(payload.get("name", "")), payload.get("context") or {}).to_dict()

    def triggers(self, _payload: Any = None) -> dict:
        """
        :return: the event names, the handlers subscribed to them and the trigger backends
        """
        return {
            "events": list(EVENT_NAMES),
            "subscriptions": [subscription.describe() for subscription in self.mail.events.subscriptions],
            "backends": [backend.describe() for backend in self.mail.triggers.backends],
        }

    def poll_triggers(self, _payload: Any = None) -> dict:
        """
        Ask every trigger backend to look once.

        :return: how many events were emitted, and the events
        """
        collected: List[dict] = []
        subscription = self.mail.events.on(ANY_EVENT, lambda event: collected.append(event.to_dict()))
        try:
            emitted = self.mail.triggers.poll()
        finally:
            self.mail.events.off(subscription)
        return {"emitted": emitted, "events": collected}

    def policies(self, _payload: Any = None) -> dict:
        """
        :return: the attachment policy in force
        """
        policy = self.mail.policy
        return {field: sorted(value) if isinstance(value, frozenset) else value
                for field, value in ((field, getattr(policy, field)) for field in _POLICY_FIELDS)}

    def set_policy(self, payload: Any) -> dict:
        """
        Replace the attachment policy of this ``Mail`` for as long as Studio runs.

        :param payload: the policy's fields; one that is left out or ``null`` lifts that limit
        :return: the policy now in force
        :raises MailThunderStudioException: the payload names something that is not a policy field
        """
        payload = _mapping(payload)
        unknown = sorted(set(payload) - set(_POLICY_FIELDS))
        if unknown:
            raise MailThunderStudioException(f"unknown policy fields {unknown}")
        self.mail.policy = AttachmentPolicy(**payload)
        return self.policies()

    def projects(self, _payload: Any = None) -> dict:
        """
        :return: the mail layer of the project directory, from its files alone, or why there is none
        """
        try:
            return {"layer": describe_mail_layer(self.project), "problem": None}
        except MailThunderProjectException as error:
            return {"layer": None, "problem": str(error)}

    def logs(self, payload: Any = None) -> dict:
        """
        :param payload: ``{"lines": n}``, at most 1000
        :return: the end of the MailThunder log file and the newest audit entries
        """
        try:
            wanted = max(1, min(int((payload or {}).get("lines", 200)), MAX_LOG_LINES))
        except (TypeError, ValueError, AttributeError):
            wanted = 200
        log_file = default_log_file()
        lines: List[str] = []
        if log_file.is_file():
            with open(log_file, "r", encoding="utf-8", errors="backslashreplace") as handle:
                lines = [line.rstrip("\n") for line in deque(handle, maxlen=wanted)]
        return {"log_file": str(log_file), "lines": lines, "audit_file": str(self.audit.path),
                "audit": self.audit.entries(limit=wanted)}

    def settings(self, _payload: Any = None) -> dict:
        """
        :return: where MailThunder keeps its files, and what it runs on
        """
        return {
            "version": _version(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "working_directory": str(Path.cwd()),
            "project_directory": str(Path(self.project) if self.project else Path.cwd()),
            "log_file": str(default_log_file()),
            "audit_file": str(self.audit.path),
            "template_directories": [str(directory) for directory in self.mail.templates.directories],
            "file_provider_variable": FILE_PROVIDER_ENV,
            "registered_providers": list(registered_providers()),
        }

    def send(self, payload: Any) -> dict:
        """
        Send a mail through the account, with every check ``Mail.send`` makes. Attachments cannot be named
        from the browser.

        :param payload: ``to``, ``cc``, ``bcc``, ``subject``, ``text``, ``html``, ``sender``, ``reply_to``,
            or ``template`` with ``context``
        :return: the message as it was sent
        :raises MailThunderStudioException: the payload names another field
        """
        payload = _mapping(payload)
        unknown = sorted(set(payload) - set(_SEND_FIELDS))
        if unknown:
            raise MailThunderStudioException(f"unknown message fields {unknown}; Studio sends {list(_SEND_FIELDS)}")
        fields = {name: value for name, value in payload.items() if value not in (None, "")}
        return self.mail.send(**fields).to_dict()
