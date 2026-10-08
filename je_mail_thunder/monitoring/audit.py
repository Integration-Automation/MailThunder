"""
The audit log: who sent or received what, and when, as one JSON object per line.

It records the facts of a mail (addresses, subject, attachment names and sizes, the provider, the outcome) and
never its body, the content of an attachment or a credential. The file is only ever appended to.
"""
from __future__ import annotations

import json
import os
import threading
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

from je_mail_thunder.core.events import ANY_EVENT, MailEvent
from je_mail_thunder.triggers.dispatcher import EventDispatcher, Subscription
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

#: Environment variable that overrides where the audit log is written.
AUDIT_FILE_ENV = "MAIL_THUNDER_AUDIT_FILE"
#: A file past this size is moved to ``<name>.1`` before the next entry is written.
ROTATE_AT_BYTES = 10 * 1024 * 1024


def default_audit_file() -> Path:
    """
    :return: ``$MAIL_THUNDER_AUDIT_FILE``, else ``~/.je_mail_thunder/audit/mail_audit.jsonl``
    """
    configured = os.environ.get(AUDIT_FILE_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".je_mail_thunder" / "audit" / "mail_audit.jsonl"


def audit_entry(event: MailEvent, subjects: bool = True) -> Dict[str, Any]:
    """
    What the audit log keeps of an event.

    :param event: what happened
    :param subjects: keep the subject line; False leaves it out, for mail whose subjects are confidential
    :return: JSON-ready facts: no body, no attachment content, no credential
    """
    entry: Dict[str, Any] = {"timestamp": event.timestamp.isoformat(), "event": event.name,
                             "provider": event.provider, "folder": event.folder}
    message = event.message
    if message is not None:
        entry.update({
            "message_id": message.message_id, "internet_message_id": message.headers.get("Message-ID"),
            "sender": message.sender, "to": list(message.to), "cc": list(message.cc), "bcc": list(message.bcc),
            "attachments": [attachment.describe() for attachment in message.attachments],
        })
        if subjects:
            entry["subject"] = message.subject
    if event.attachment is not None:
        entry["attachment"] = event.attachment.describe()
    if event.error is not None:
        entry["error"] = {"type": type(event.error).__name__, "message": str(event.error)}
    if event.metadata:
        entry["metadata"] = {str(key): repr(value) for key, value in event.metadata.items()}
    return entry


class AuditLog:
    """Appends an entry for every mail event it is given. Safe to share between threads and processes."""

    def __init__(self, path: Optional[str | os.PathLike[str]] = None, subjects: bool = True) -> None:
        """
        :param path: the file to append to; ``default_audit_file()`` by default
        :param subjects: keep subject lines in the entries
        """
        self.path = Path(path) if path is not None else default_audit_file()
        self._subjects = subjects
        self._lock = threading.Lock()

    def attach(self, dispatcher: EventDispatcher) -> Subscription:
        """
        Record every event of a dispatcher: ``audit.attach(mail.events)``.

        :param dispatcher: a :class:`~je_mail_thunder.core.mail.Mail`'s ``events``
        :return: the subscription; ``dispatcher.off(subscription)`` stops the recording
        """
        return dispatcher.on(ANY_EVENT, self.record)

    def _rotate(self) -> None:
        if self.path.is_file() and self.path.stat().st_size > ROTATE_AT_BYTES:
            os.replace(self.path, self.path.with_name(self.path.name + ".1"))

    def record(self, event: MailEvent) -> None:
        """
        Append the entry of one event. A file that cannot be written is logged, never raised: an audit log
        that is out of disk must not stop the mail.

        :param event: what happened
        :return: None
        """
        line = json.dumps(audit_entry(event, self._subjects), ensure_ascii=False)
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._rotate()
                with open(self.path, "a", encoding="utf-8") as audit_file:
                    audit_file.write(line + "\n")
            except OSError as error:
                mail_thunder_logger.error(f"audit_log, {self.path} cannot be written: {repr(error)}")

    def entries(self, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """
        :param limit: the most entries to return; ``None`` for all of them
        :return: the newest entries, oldest first; a line that is not JSON is skipped
        """
        if not self.path.is_file():
            return []
        kept: deque = deque(maxlen=limit)
        with self._lock, open(self.path, "r", encoding="utf-8") as audit_file:
            for line in audit_file:
                try:
                    kept.append(json.loads(line))
                except ValueError:
                    continue
        return list(kept)
