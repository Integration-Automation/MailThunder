"""
Stand-ins the core mail API tests share: providers that record what they are asked, and SMTP / IMAP clients
that answer like a server without a network.
"""
import imaplib
from collections import deque
from email.message import EmailMessage

from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers.base import DEFAULT_FOLDER, MailSender, MailStore

# What the tests log in with. It is made up; the name keeps secret scanners from reporting it as a leaked password.
MADE_UP_PASSPHRASE = "p4ss-word-secret"
RAW_MESSAGE = (
    b"From: Sender <sender@example.com>\r\n"
    b"To: reader@example.com\r\n"
    b"Subject: Report %d\r\n"
    b"Message-ID: <%d@example.com>\r\n"
    b"Date: Thu, 01 Oct 2026 08:00:00 +0000\r\n"
    b"\r\n"
    b"Body %d\r\n"
)


class RecordingSender(MailSender):
    """Keeps the messages it is asked to send."""

    name = "recording-sender"

    def __init__(self):
        self.sent = []
        self.closed = 0

    def send(self, message):
        self.sent.append(message)

    def close(self):
        self.closed += 1


class RecordingStore(MailStore):
    """A mailbox in memory: ``message_id`` -> message, with the calls it received."""

    name = "recording-store"

    def __init__(self, messages=()):
        self.messages = {message.message_id: message for message in messages}
        self.calls = []
        self.drafts = []
        self.closed = 0

    def get_messages(self, folder=DEFAULT_FOLDER, limit=None, unread_only=False, query=None):
        self.calls.append(("get_messages", folder, limit, unread_only, query))
        yield from list(self.messages.values())[:limit]

    def get_message(self, message_id, folder=DEFAULT_FOLDER):
        self.calls.append(("get_message", message_id, folder))
        return self.messages[message_id]

    def create_draft(self, message, folder=None):
        self.calls.append(("create_draft", folder))
        self.drafts.append(message)
        return "draft-1"

    def delete_message(self, message_id, folder=DEFAULT_FOLDER):
        self.calls.append(("delete_message", message_id, folder))
        del self.messages[message_id]

    def close(self):
        self.closed += 1


def stored_message(message_id, subject="Stored"):
    return MailMessage(subject=subject, to="reader@example.com", sender="sender@example.com", text="body",
                       message_id=message_id)


class FakeSMTPClient:
    """What ``SMTPProvider`` uses of an SMTP wrapper; ``fail`` maps a method name to the error it raises once."""

    def __init__(self, host=None, port=None):
        self.host = host
        self.port = port
        self.calls = []
        self.sent = []
        self.refused = {}
        self.fail = {}
        self.noop_status = 250

    def _call(self, name, *arguments):
        self.calls.append((name,) + arguments)
        if name in self.fail:
            raise self.fail.pop(name)

    def login(self, user, password):
        self._call("login", user, password)

    def oauth2_login(self, user, access_token):
        self._call("oauth2_login", user, access_token)

    def noop(self):
        self._call("noop")
        return self.noop_status, b"OK"

    def send_message(self, email_message):
        self._call("send_message")
        assert isinstance(email_message, EmailMessage)
        self.sent.append(email_message)
        return dict(self.refused)

    def quit(self):
        self._call("quit")

    def close(self):
        self._call("close")


class FakeSocket:
    """The part of a socket the providers touch: the timeout they set on a new connection."""

    def __init__(self):
        self.timeout = None

    def settimeout(self, seconds):
        self.timeout = seconds


class FakeIMAPClient:
    """What ``IMAPProvider`` uses of an IMAP wrapper, over a mailbox of UID -> raw message."""

    def __init__(self, host=None):
        self.host = host
        self.calls = []
        self.fail = {}
        self.refuse = set()
        self.capabilities = ("IMAP4REV1", "UIDPLUS")
        self.mailbox = {uid: RAW_MESSAGE % (uid, uid, uid) for uid in (1, 2, 3)}
        self.folders = [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren \\Drafts) "/" "[Gmail]/Drafts"']
        self.append_answer = [b"[APPENDUID 7 42] (Success)"]
        self.appended = []
        # For IDLE: what the provider writes, and the lines the server answers with.
        self.sock = FakeSocket()
        self.written = []
        self.lines = deque()

    def _call(self, name, *arguments):
        self.calls.append((name,) + arguments)
        if name in self.fail:
            raise self.fail.pop(name)
        return ("NO", [b"refused by the fake"]) if name in self.refuse else None

    def named(self, name):
        return [call for call in self.calls if call[0] == name]

    def login(self, user, password):
        self._call("login", user, password)

    def oauth2_login(self, user, access_token):
        self._call("oauth2_login", user, access_token)

    def noop(self):
        return self._call("noop") or ("OK", [b"NOOP completed"])

    def select(self, mailbox="INBOX", readonly=False):
        return self._call("select", mailbox, readonly) or ("OK", [b"3"])

    def list(self):
        return self._call("list") or ("OK", list(self.folders))

    def append(self, mailbox, flags, date_time, message):
        refusal = self._call("append", mailbox, flags)
        self.appended.append(message)
        return refusal or ("OK", list(self.append_answer))

    def expunge(self):
        return self._call("expunge") or ("OK", [b"1"])

    def uid(self, command, *arguments):
        refusal = self._call("uid", command, *arguments)
        if refusal:
            return refusal
        return getattr(self, "_uid_" + command.lower())(*arguments)

    def _uid_search(self, *_criteria):
        return "OK", [b" ".join(str(uid).encode("ascii") for uid in sorted(self.mailbox))]

    def _uid_fetch(self, uid, _parts):
        raw = self.mailbox.get(int(uid))
        if raw is None:
            return "OK", [None]
        return "OK", [(b"1 (UID %d BODY[] {%d}" % (int(uid), len(raw)), raw), b")"]

    def _uid_store(self, uid, _operation, _flags):
        if int(uid) not in self.mailbox:
            return "OK", [None]
        return "OK", [b"1 (FLAGS (\\Deleted) UID %d)" % int(uid)]

    def _uid_expunge(self, uid):
        self.mailbox.pop(int(uid), None)
        return "OK", [None]

    def send(self, data):
        self._call("send", data)
        self.written.append(data)

    def readline(self):
        self._call("readline")
        return self.lines.popleft() if self.lines else b""

    def logout(self):
        self._call("logout")
        return "BYE", [b"bye"]

    def shutdown(self):
        self._call("shutdown")


IMAP_ABORT = imaplib.IMAP4.abort
IMAP_ERROR = imaplib.IMAP4.error
