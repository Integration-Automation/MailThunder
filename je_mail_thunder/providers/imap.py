"""
Reading and managing stored mail over IMAP, with MailThunder's IMAP wrapper as the connection (always over TLS).

Messages are identified by their UID, which stays the same while the session's sequence numbers shift, and are
read with ``BODY.PEEK[]``, so reading one never marks it as read.
"""
import base64
import imaplib
import re
import time
from email import policy
from typing import Iterator, List, Optional, Tuple

from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.core.rfc822 import parse_message, to_email_message
from je_mail_thunder.imap.imap_wrapper import IMAPWrapper
from je_mail_thunder.providers.base import DEFAULT_FOLDER, MailStore
from je_mail_thunder.providers.session import WrapperProvider
from je_mail_thunder.utils.exception.exceptions import MailThunderProviderException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

_FALLBACK_DRAFTS_FOLDER = '"Drafts"'
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
_NON_ASCII_RUN = re.compile(r"[^\x20-\x7e]+")
# One line of a LIST answer: (flags) "delimiter" name
_LIST_LINE = re.compile(rb'\((?P<flags>[^)]*)\) (?:"[^"]*"|NIL) (?P<name>.+)')
_APPEND_UID = re.compile(r"APPENDUID \d+ (\d+)")


def _utf7_run(match: "re.Match[str]") -> str:
    encoded = base64.b64encode(match.group().encode("utf-16-be")).decode("ascii")
    return "&" + encoded.rstrip("=").replace("/", ",") + "-"


def mailbox_name(folder: str) -> str:
    """
    A folder name as IMAP takes it: modified UTF-7 (RFC 3501 5.1.3) in a quoted string.

    :param folder: the folder's name as a person reads it, e.g. ``INBOX`` or ``[Gmail]/Sent Mail``
    :return: the quoted name
    :raises MailThunderProviderException: the name is empty or holds a control character
    """
    if not isinstance(folder, str) or not folder or _CONTROL_CHARACTER.search(folder):
        raise MailThunderProviderException(f"invalid folder name {folder!r}")
    encoded = _NON_ASCII_RUN.sub(_utf7_run, folder.replace("&", "&-"))
    return '"' + encoded.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _uid(message_id: object) -> str:
    """A message id as the UID it must be: digits only, so nothing else reaches the command line."""
    uid = str(message_id)
    if isinstance(message_id, bool) or not uid.isascii() or not uid.isdigit():
        raise MailThunderProviderException(f"an IMAP message id is a UID (digits), not {message_id!r}")
    return uid


def _search_arguments(unread_only: bool, query: Optional[str]) -> Tuple[object, ...]:
    """The arguments of ``UID SEARCH``; a search with non-ASCII text names its charset."""
    criteria = [part for part in ("UNSEEN" if unread_only else "", (query or "").strip()) if part]
    text = " ".join(criteria) or "ALL"
    if _CONTROL_CHARACTER.search(text):
        raise MailThunderProviderException("an IMAP search must be one line")
    if text.isascii():
        return (None, text)
    return ("CHARSET", "UTF-8", text.encode("utf-8"))


def _answer_text(data: object) -> str:
    parts = data if isinstance(data, (list, tuple)) else [data]
    return " ".join(part.decode("utf-8", "replace") for part in parts if isinstance(part, bytes))


class IMAPProvider(WrapperProvider, MailStore):
    """Reads, drafts and deletes mail over IMAP."""

    name = "imap"
    _server_errors = (imaplib.IMAP4.error, OSError)

    def __init__(self, account=None, client=None, clock=time.monotonic) -> None:
        """
        :param account: whose mail, on which servers; needed unless ``client`` is given
        :param client: an :class:`IMAPWrapper` that is already connected and logged in
        :param clock: the clock idle time is measured on
        """
        super().__init__(account, client, clock)
        # The folder this provider opened last, and whether it may change it.
        self._selected: Optional[Tuple[str, bool]] = None

    def _connect(self):
        host = self._account.resolved_servers.imap_host
        if not host:
            raise MailThunderProviderException("the account has no IMAP server")
        self._selected = None
        return IMAPWrapper(host)

    def _ping(self, client) -> None:
        status, _ = client.noop()
        if status != "OK":
            raise imaplib.IMAP4.abort(f"NOOP answered {status}")

    def _disconnect(self, client, alive: bool) -> None:
        if alive:
            client.logout()
        else:
            client.shutdown()

    def _is_lost(self, error: Exception) -> bool:
        return isinstance(error, (imaplib.IMAP4.abort, OSError))

    def _run(self, action: str, command, *arguments) -> List:
        """One IMAP command; anything but ``OK`` is a provider error."""
        try:
            status, data = command(*arguments)
        except self._server_errors as error:
            raise self._failure(action, error, MailThunderProviderException) from error
        if status != "OK":
            raise MailThunderProviderException(f"the imap server refused {action}: {_answer_text(data)}")
        return data

    def _select(self, client, folder: str, writable: bool = False, fresh: bool = False) -> None:
        """Open ``folder`` unless this provider has it open already; ``fresh`` opens it whatever it remembers."""
        if not fresh and self._selected is not None:
            selected, selected_writable = self._selected
            if selected == folder and (selected_writable or not writable):
                return
        self._run(f"opening the folder {folder!r}", client.select, mailbox_name(folder), not writable)
        self._selected = (folder, writable)

    def _open_folder(self, folder: str, writable: bool = False):
        """The live client with ``folder`` open; a client this provider was given may have been moved by its owner."""
        client = self._live_client()
        self._select(client, folder, writable, fresh=self._adopted)
        return client

    def _fetch(self, client, uid: str) -> Optional[MailMessage]:
        data = self._run(f"reading the message {uid}", client.uid, "FETCH", uid, "(BODY.PEEK[])")
        for item in data or ():
            if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes):
                return parse_message(item[1], uid)
        return None

    def get_messages(self, folder: str = DEFAULT_FOLDER, limit: Optional[int] = None,
                     unread_only: bool = False, query: Optional[str] = None) -> Iterator[MailMessage]:
        """
        The messages of a folder, newest first, fetched one at a time as the iterator is read.

        :param folder: the folder to read
        :param limit: stop after this many messages
        :param unread_only: only messages without the ``\\Seen`` flag
        :param query: IMAP ``SEARCH`` criteria, e.g. ``FROM "ci@example.com" SINCE 1-Oct-2026``
        :return: an iterator of messages whose ``message_id`` is the UID
        :raises MailThunderProviderException: the server refused the folder or the search
        """
        mail_thunder_logger.info(f"imap provider, get_messages: folder {folder!r}, limit {limit}")
        arguments = _search_arguments(unread_only, query)
        client = self._open_folder(folder)
        found = self._run("the search", client.uid, "SEARCH", *arguments)
        uids = found[0].split() if found and isinstance(found[0], bytes) else []
        # UIDs grow as mail arrives, so the last ones are the newest.
        uids.reverse()
        for uid in uids[:limit]:
            # Another call on this provider may have opened a different folder since the last message.
            self._select(client, folder)
            message = self._fetch(client, uid.decode("ascii"))
            if message is not None:
                yield message

    def get_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> MailMessage:
        """
        :param message_id: the message's UID
        :param folder: the folder it is in
        :return: the message
        :raises MailThunderProviderException: the id is not a UID, or the folder holds no such message
        """
        uid = _uid(message_id)
        mail_thunder_logger.info(f"imap provider, get_message: {uid} in {folder!r}")
        message = self._fetch(self._open_folder(folder), uid)
        if message is None:
            raise MailThunderProviderException(f"no message {uid} in the folder {folder!r}")
        return message

    def _drafts_mailbox(self, client) -> str:
        """The drafts folder as IMAP takes it: the account's setting, else the folder flagged ``\\Drafts``."""
        configured = self._account.resolved_servers.drafts_folder if self._account is not None else None
        if configured:
            return mailbox_name(configured)
        for line in self._run("listing the folders", client.list) or ():
            match = _LIST_LINE.match(line) if isinstance(line, bytes) else None
            if match and b"\\drafts" in match.group("flags").lower():
                # The server's own spelling, already encoded and quoted as it wants it back.
                return match.group("name").decode("ascii", "replace")
        return _FALLBACK_DRAFTS_FOLDER

    def create_draft(self, message: MailMessage, folder: Optional[str] = None) -> Optional[str]:
        """
        Store a message in the drafts folder with the ``\\Draft`` flag.

        :param message: the draft
        :param folder: the drafts folder; by default the account's, else the one the server flags ``\\Drafts``
        :return: the draft's UID when the server reports it (``UIDPLUS``), else ``None``
        :raises MailThunderProviderException: the server refused the draft
        """
        mail_thunder_logger.info("imap provider, create_draft")
        raw = to_email_message(message).as_bytes(policy=policy.SMTP)
        client = self._live_client()
        mailbox = mailbox_name(folder) if folder else self._drafts_mailbox(client)
        answer = self._run("the draft", client.append, mailbox, "\\Draft", time.time(), raw)
        stored = _APPEND_UID.search(_answer_text(answer))
        return stored.group(1) if stored else None

    def delete_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> None:
        """
        Flag a message ``\\Deleted`` and expunge it (only it, when the server has ``UIDPLUS``).

        :param message_id: the message's UID
        :param folder: the folder it is in
        :return: None
        :raises MailThunderProviderException: the id is not a UID, or the folder holds no such message
        """
        uid = _uid(message_id)
        mail_thunder_logger.info(f"imap provider, delete_message: {uid} in {folder!r}")
        client = self._open_folder(folder, writable=True)
        flagged = self._run(f"deleting the message {uid}", client.uid, "STORE", uid, "+FLAGS", "(\\Deleted)")
        if not any(flagged or ()):
            raise MailThunderProviderException(f"no message {uid} in the folder {folder!r}")
        if "UIDPLUS" in getattr(client, "capabilities", ()):
            self._run("the expunge", client.uid, "EXPUNGE", uid)
        else:
            self._run("the expunge", client.expunge)
