"""
Mail events and triggers: the events, the filters, the dispatcher, ``Mail.on`` / ``Mail.watch`` and the backends
that notice new mail. No server and no real waiting: stores and IMAP clients are fakes.
"""
import json
import re
import threading
from datetime import datetime, timedelta, timezone

import pytest

from je_mail_thunder import mail_instance
from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.attachments.policy import AttachmentPolicy
from je_mail_thunder.auth.password import PasswordAuth
from je_mail_thunder.core import mail as mail_module
from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.core.events import (
    ATTACHMENT_RECEIVED,
    ATTACHMENT_REJECTED,
    AUTHENTICATION_FAILED,
    CONNECTION_FAILED,
    EVENT_NAMES,
    MESSAGE_FAILED,
    MESSAGE_RECEIVED,
    MESSAGE_SENT,
    MailEvent,
    failure_events,
)
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers import imap as imap_provider
from je_mail_thunder.providers.imap import IMAPProvider
from je_mail_thunder.triggers.dispatcher import EventDispatcher
from je_mail_thunder.triggers.factory import create_backend, register_backends
from je_mail_thunder.triggers.filter import MailFilter
from je_mail_thunder.triggers.imap import IMAPIdleBackend, IMAPPollingBackend
from je_mail_thunder.triggers.polling import PollingBackend
from je_mail_thunder.triggers.trigger import MailTriggerBackend, TriggerManager
from je_mail_thunder.utils.exception.exceptions import (
    AttachmentTooLarge,
    MailThunderAuthenticationException,
    MailThunderConnectionException,
    MailThunderMessageException,
    MailThunderProviderException,
    MailThunderSendException,
    MailThunderTriggerException,
)
from je_mail_thunder.utils.executor.action_executor import execute_action
from mail_fakes import RAW_MESSAGE, FakeIMAPClient, RecordingSender, RecordingStore, stored_message

_USER = "someone@example.com"
_AUTH = PasswordAuth(_USER, "p4ss-word-secret")
_REPORT = Attachment(filename="report.pdf", content_type="application/pdf", content=b"%PDF")
_MESSAGE = MailMessage(
    subject="[TEST] Nightly run", to="qa@example.com", cc="lead@example.com", sender="CI <ci@example.com>",
    text="2 failed", html="<b>2 failed</b>", attachments=[_REPORT],
    date=datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc), message_id="7")


def _collector(dispatcher, event="*", mail_filter=None):
    seen = []
    dispatcher.on(event, seen.append, mail_filter)
    return seen


# --- events -----------------------------------------------------------------------------------------------------

def test_an_event_is_json_ready():
    event = MailEvent(MESSAGE_RECEIVED, message=_MESSAGE, attachment=_REPORT, error=ValueError("x"),
                      provider="imap", folder="INBOX", metadata={"run": 42})
    described = json.loads(json.dumps(event.to_dict()))
    assert described["name"] == "message_received" and described["message"]["subject"] == "[TEST] Nightly run"
    assert described["attachment"] == {"filename": "report.pdf", "content_type": "application/pdf", "size": 4}
    assert (described["error"], described["provider"], described["folder"]) == ("ValueError('x')", "imap", "INBOX")
    assert described["metadata"] == {"run": 42} and described["timestamp"].endswith("+00:00")
    assert MailEvent(MESSAGE_SENT).to_dict()["message"] is None
    assert len(EVENT_NAMES) == 7


@pytest.mark.parametrize("error, sending, expected", [
    (MailThunderAuthenticationException("no"), True, [AUTHENTICATION_FAILED, MESSAGE_FAILED]),
    (MailThunderConnectionException("down"), True, [CONNECTION_FAILED, MESSAGE_FAILED]),
    (AttachmentTooLarge("a.bin", 2, 1), True, [ATTACHMENT_REJECTED, MESSAGE_FAILED]),
    (MailThunderSendException("refused"), True, [MESSAGE_FAILED]),
    (MailThunderConnectionException("down"), False, [CONNECTION_FAILED]),
    (MailThunderProviderException("no folder"), False, []),
])
def test_the_events_a_failure_stands_for(error, sending, expected):
    events = failure_events(error, _MESSAGE, "smtp", sending)
    assert [event.name for event in events] == expected
    assert all(event.error is error and event.message is _MESSAGE and event.provider == "smtp" for event in events)


# --- filters ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("rules, matches", [
    ({}, True),
    ({"subject": "[test]"}, True),
    ({"subject": "weekly"}, False),
    ({"subject": re.compile(r"^\[TEST\] \w+")}, True),
    ({"sender": "ci@example.com"}, True),
    ({"sender": "someone-else"}, False),
    ({"recipient": "LEAD@example.com"}, True),
    ({"recipient": "nobody@example.com"}, False),
    ({"body": "2 failed"}, True),
    ({"body": "<b>"}, True),
    ({"body": "all passed"}, False),
    ({"has_attachments": True}, True),
    ({"has_attachments": False}, False),
    ({"attachment_type": "pdf"}, True),
    ({"attachment_type": ".PDF"}, True),
    ({"attachment_type": "csv"}, False),
    ({"attachment_type": "application/pdf"}, True),
    ({"attachment_type": "application/*"}, True),
    ({"attachment_type": "image/*"}, False),
    ({"since": datetime(2026, 10, 1, 7, 0, tzinfo=timezone.utc)}, True),
    ({"since": datetime(2026, 10, 1, 9, 0)}, False),
    ({"until": datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)}, True),
    ({"until": datetime(2026, 9, 30, tzinfo=timezone.utc)}, False),
    ({"metadata": {"run": 42}}, True),
    ({"metadata": {"run": 43}}, False),
    ({"metadata": {"missing": None}}, True),
    ({"predicate": lambda event: event.folder == "INBOX"}, True),
    ({"predicate": lambda event: event.folder == "Archive"}, False),
    ({"subject": "[TEST]", "sender": "ci@", "has_attachments": True, "attachment_type": "pdf"}, True),
    ({"subject": "[TEST]", "sender": "boss@"}, False),
])
def test_every_rule_of_a_filter_must_match(rules, matches):
    event = MailEvent(MESSAGE_RECEIVED, message=_MESSAGE, folder="INBOX", metadata={"run": 42})
    assert MailFilter.of(rules).matches(event) is matches


def test_a_filter_on_an_event_without_a_message():
    failure = MailEvent(CONNECTION_FAILED, error=MailThunderConnectionException("down"))
    assert MailFilter().matches(failure)
    assert not MailFilter(subject="x").matches(failure)
    assert MailFilter(has_attachments=False).matches(failure)
    recent = MailFilter(since=datetime.now(timezone.utc) - timedelta(minutes=1))
    assert recent.matches(failure)
    only_attachment = MailEvent(ATTACHMENT_RECEIVED, attachment=_REPORT)
    assert MailFilter(attachment_type="pdf", has_attachments=True).matches(only_attachment)


def test_what_a_filter_can_be_made_of():
    ready = MailFilter(subject="x")
    assert MailFilter.of(ready) is ready
    assert MailFilter.of(None) == MailFilter()
    assert MailFilter.of(lambda event: True).predicate is not None
    for bad in ("subject", 5, ["subject"]):
        with pytest.raises(MailThunderTriggerException, match="a filter is a mapping"):
            MailFilter.of(bad)
    with pytest.raises(MailThunderTriggerException, match="unknown filter rules \\['from'\\]"):
        MailFilter.of({"from": "a@example.com"})

    def only_reports(event):
        return bool(event.message)

    described = MailFilter(subject=re.compile("^Re:"), sender="ci@", has_attachments=True, metadata={"run": 1},
                           predicate=only_reports).describe()
    assert described == {"sender": "ci@", "subject": "^Re:", "has_attachments": "True",
                         "metadata": {"run": 1}, "predicate": "only_reports"}
    assert MailFilter().describe() == {}


# --- the dispatcher ---------------------------------------------------------------------------------------------

def test_handlers_get_the_events_they_subscribed_to():
    dispatcher = EventDispatcher()
    received, everything = _collector(dispatcher, MESSAGE_RECEIVED), _collector(dispatcher)
    tests_only = _collector(dispatcher, MESSAGE_RECEIVED, {"subject": "[TEST]"})
    arrived = MailEvent(MESSAGE_RECEIVED, message=_MESSAGE)
    other = MailEvent(MESSAGE_RECEIVED, message=MailMessage(subject="Lunch?"))
    sent = MailEvent(MESSAGE_SENT, message=_MESSAGE)
    assert [dispatcher.emit(event) for event in (arrived, other, sent)] == [3, 2, 1]
    assert (received, tests_only, everything) == ([arrived, other], [arrived], [arrived, other, sent])


def test_a_handler_that_fails_stops_nothing(caplog):
    dispatcher = EventDispatcher()

    def broken(_event):
        raise RuntimeError("handler bug")

    dispatcher.on(MESSAGE_SENT, broken)
    dispatcher.on(MESSAGE_SENT, lambda event: None, lambda event: 1 / 0)
    after = _collector(dispatcher, MESSAGE_SENT)
    assert dispatcher.emit(MailEvent(MESSAGE_SENT)) == 2
    assert len(after) == 1
    assert "handler bug" in caplog.text and "ZeroDivisionError" in caplog.text


def test_subscriptions_can_be_listed_and_ended():
    dispatcher = EventDispatcher()

    def handle(_event):
        return None

    subscription = dispatcher.on(MESSAGE_FAILED, handle, {"subject": "x"})
    assert dispatcher.subscriptions == (subscription,)
    described = subscription.describe()
    assert described["event"] == "message_failed" and described["filter"] == {"subject": "x"}
    assert described["handler"].endswith("handle") and isinstance(described["id"], int)
    assert dispatcher.off(subscription) is True and dispatcher.off(subscription) is False
    assert dispatcher.emit(MailEvent(MESSAGE_FAILED)) == 0
    with pytest.raises(MailThunderTriggerException, match="unknown event 'message_recieved'"):
        dispatcher.on("message_recieved", handle)
    with pytest.raises(MailThunderTriggerException, match="must be callable"):
        dispatcher.on(MESSAGE_SENT, "handle")


# --- Mail.on and what Mail emits --------------------------------------------------------------------------------

def _mail(policy=None, providers=None):
    sender = RecordingSender()
    return Mail(account=MailAccount(auth=_AUTH), providers=providers or [sender], policy=policy), sender


def test_a_sent_message_is_an_event():
    mail, sender = _mail()
    events = []
    subscription = mail.on("message_sent", events.append, filter={"subject": "Report"})
    sent = mail.send(to="qa@example.com", subject="Report", text="x")
    mail.send(to="qa@example.com", subject="Other", text="x")
    assert [(event.name, event.message, event.provider) for event in events] == [
        ("message_sent", sent, "recording-sender")]
    assert mail.events.off(subscription) and len(sender.sent) == 2


def test_on_is_also_a_decorator():
    mail, _sender = _mail()
    seen = []

    @mail.on("message_sent")
    def remember(event):
        seen.append(event.message.subject)

    @mail.on("message_failed", filter=lambda event: isinstance(event.error, MailThunderMessageException))
    def failed(event):
        seen.append(type(event.error).__name__)

    mail.send(to="qa@example.com", subject="Hello", text="x")
    with pytest.raises(MailThunderMessageException):
        mail.send(subject="nobody")
    assert seen == ["Hello", "MailThunderMessageException"]
    assert callable(remember) and callable(failed)
    with pytest.raises(MailThunderTriggerException, match="unknown options \\['when'\\]"):
        mail.on("message_sent", remember, when="always")
    with pytest.raises(MailThunderTriggerException, match="unknown event"):
        mail.on("sent", remember)


def test_a_failed_send_says_why(tmp_path, monkeypatch):
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * 9)
    mail, sender = _mail(policy=AttachmentPolicy(max_file_size=4))
    events = _collector(mail.events)
    with pytest.raises(AttachmentTooLarge):
        mail.send(to="qa@example.com", subject="Big", attachments=[big])
    assert [event.name for event in events] == [ATTACHMENT_REJECTED, MESSAGE_FAILED]
    assert events[0].message is None and isinstance(events[0].error, AttachmentTooLarge)

    events.clear()
    sender.send = lambda message: (_ for _ in ()).throw(MailThunderConnectionException("smtp down"))
    mail.policy = AttachmentPolicy()
    with pytest.raises(MailThunderConnectionException):
        mail.send(to="qa@example.com", subject="Later", text="x")
    assert [(event.name, event.provider) for event in events] == [
        (CONNECTION_FAILED, "recording-sender"), (MESSAGE_FAILED, "recording-sender")]
    assert events[1].message.subject == "Later"

    events.clear()
    monkeypatch.chdir(tmp_path)
    for name in ("mail_thunder_user", "mail_thunder_user_password", "mail_thunder_oauth2_access_token",
                 "mail_thunder_oauth2_refresh_token"):
        monkeypatch.delenv(name, raising=False)
    anonymous = Mail(account=MailAccount(), providers=[RecordingSender()])
    failures = _collector(anonymous.events)
    with pytest.raises(MailThunderAuthenticationException):
        anonymous.send(to="qa@example.com", text="x")
    assert [event.name for event in failures] == [AUTHENTICATION_FAILED, MESSAGE_FAILED]


def test_a_failed_read_is_a_connection_or_authentication_event():
    store = RecordingStore()
    store.get_message = lambda message_id, folder="INBOX": (_ for _ in ()).throw(
        MailThunderConnectionException("imap down"))
    mail, _sender = _mail(providers=[store])
    events = _collector(mail.events)
    with pytest.raises(MailThunderConnectionException):
        mail.get_message("1")
    with pytest.raises(MailThunderProviderException, match="limit"):
        mail.get_messages(limit=-1)
    assert [event.name for event in events] == [CONNECTION_FAILED]


def test_a_handler_cannot_break_a_send():
    mail, sender = _mail()
    mail.on("message_sent", lambda event: 1 / 0)
    assert mail.send(to="qa@example.com", subject="Still sent", text="x").subject == "Still sent"
    assert len(sender.sent) == 1


# --- polling ----------------------------------------------------------------------------------------------------

def _store(*ids):
    """A store whose newest message comes first, as providers answer."""
    return RecordingStore([stored_message(str(identifier), f"Mail {identifier}") for identifier in ids])


def _arrive(store, message):
    store.messages = {message.message_id: message, **store.messages}


def test_polling_reports_only_what_arrived_after_the_first_look():
    store = _store(2, 1)
    backend = PollingBackend(store, folder="Reports")
    events = []
    backend.bind(events.append)
    assert backend.poll() == 0 and events == []
    assert backend.poll() == 0
    _arrive(store, stored_message("3", "Mail 3"))
    with_file = MailMessage(subject="Mail 4", to="a@example.com", attachments=[_REPORT], message_id="4")
    _arrive(store, with_file)
    assert backend.poll() == 3
    assert [(event.name, event.message.message_id) for event in events] == [
        (MESSAGE_RECEIVED, "3"), (MESSAGE_RECEIVED, "4"), (ATTACHMENT_RECEIVED, "4")]
    assert events[2].attachment is _REPORT
    assert all(event.folder == "Reports" and event.provider == "recording-store" for event in events)
    assert backend.poll() == 0
    assert store.calls[0] == ("get_messages", "Reports", 50, False, None)
    assert backend.describe() == {"name": "polling", "interval": 60.0, "running": False, "folder": "Reports",
                                  "provider": "recording-store"}


def test_polling_can_report_what_is_already_there_and_reads_in_batches():
    store = _store(3, 2, 1)
    backend = PollingBackend(store, include_existing=True, batch_limit=2)
    events = []
    backend.bind(events.append)
    assert backend.poll() == 2
    assert [event.message.message_id for event in events] == ["2", "3"]
    assert backend.poll() == 0


def test_a_message_deleted_between_two_looks_is_not_a_new_message():
    store = _store(3, 2, 1)
    backend = PollingBackend(store)
    backend.bind(lambda event: None)
    backend.poll()
    del store.messages["3"]
    assert backend.poll() == 0


def test_polling_holds_the_lock_it_is_given_and_closes_only_its_own_store():
    store = _store(1)
    lock = threading.RLock()
    held = []
    original = store.get_messages

    def watching(*arguments, **options):
        held.append(lock._is_owned())  # noqa: SLF001 - the only way to see who holds an RLock
        return original(*arguments, **options)

    store.get_messages = watching
    backend = PollingBackend(store, lock=lock)
    backend.poll()
    backend.close()
    assert held == [True] and store.closed == 0
    backend.owns_store = True
    backend.close()
    assert store.closed == 1


@pytest.mark.parametrize("build", [
    lambda: PollingBackend(RecordingSender()),
    lambda: PollingBackend(_store(), batch_limit=0),
    lambda: PollingBackend(_store(), batch_limit=True),
    lambda: PollingBackend(_store(), interval=0),
    lambda: PollingBackend(_store(), interval="60"),
    lambda: IMAPPollingBackend(_store()),
])
def test_a_backend_refuses_what_it_cannot_work_with(build):
    with pytest.raises(MailThunderTriggerException):
        build()


# --- IMAP -------------------------------------------------------------------------------------------------------

def _imap():
    client = FakeIMAPClient()
    client.capabilities = ("IMAP4REV1", "UIDPLUS", "IDLE")
    return IMAPProvider(client=client), client


def test_imap_polling_asks_only_for_uids_above_the_last_one():
    provider, client = _imap()
    backend = IMAPPollingBackend(provider)
    events = []
    backend.bind(events.append)
    assert backend.poll() == 0
    assert backend.poll() == 0
    client.mailbox[4] = RAW_MESSAGE % (4, 4, 4)
    client.mailbox[5] = RAW_MESSAGE % (5, 5, 5)
    assert backend.poll() == 2
    assert [(event.message.message_id, event.message.subject) for event in events] == [
        ("4", "Report 4"), ("5", "Report 5")]
    searches = [call[3] for call in client.calls if call[:2] == ("uid", "SEARCH")]
    assert searches == ["ALL", "UID 4:*", "UID 4:*"]
    assert backend.poll() == 0 and backend.name == "imap-polling"


def test_imap_polling_starts_from_an_empty_mailbox():
    provider, client = _imap()
    client.mailbox.clear()
    backend = IMAPPollingBackend(provider)
    events = []
    backend.bind(events.append)
    assert backend.poll() == 0
    client.mailbox[1] = RAW_MESSAGE % (1, 1, 1)
    assert backend.poll() == 1 and events[0].message.message_id == "1"


def test_idle_waits_for_the_server_and_ends_with_done(monkeypatch):
    provider, client = _imap()
    waits = []
    monkeypatch.setattr(imap_provider, "_readable", lambda connection, seconds: waits.append(seconds) or True)
    client.lines.extend([b"+ idling\r\n", b"* 4 EXISTS\r\n", b"MTIDLE1 OK IDLE terminated\r\n"])
    assert provider.idle("INBOX", timeout=30) is True
    assert client.written == [b"MTIDLE1 IDLE\r\n", b"DONE\r\n"]
    assert waits == [imap_provider.IDLE_SLICE_SECONDS]
    assert client.named("select") == [("select", '"INBOX"', True)]
    client.lines.extend([b"+ idling\r\n", b"MTIDLE2 OK IDLE terminated\r\n"])
    monkeypatch.setattr(imap_provider, "_readable", lambda connection, seconds: False)
    assert provider.idle("INBOX", timeout=5, should_stop=lambda: True) is False
    assert client.written[2:] == [b"MTIDLE2 IDLE\r\n", b"DONE\r\n"]


def test_idle_ends_when_the_time_is_up_and_still_hears_a_late_notice(monkeypatch):
    client = FakeIMAPClient()
    client.capabilities = ("IDLE",)
    now = [0.0]

    def no_data(_connection, seconds):
        now[0] += seconds
        return False

    monkeypatch.setattr(imap_provider, "_readable", no_data)
    provider = IMAPProvider(client=client, clock=lambda: now[0])
    client.lines.extend([b"+ idling\r\n", b"* 9 EXISTS\r\n", b"* 1 RECENT\r\n", b"MTIDLE1 OK done\r\n"])
    assert provider.idle(timeout=3) is True
    assert now[0] == 3.0


def test_what_idle_cannot_do(monkeypatch):
    monkeypatch.setattr(imap_provider, "_readable", lambda connection, seconds: True)
    provider, client = _imap()
    client.capabilities = ("IMAP4REV1",)
    with pytest.raises(MailThunderProviderException, match="does not offer IDLE"):
        provider.idle()
    client.capabilities = ("IDLE",)
    client.lines.append(b"MTIDLE1 BAD not now\r\n")
    with pytest.raises(MailThunderProviderException, match="refused idling"):
        provider.idle()
    client.lines.extend([b"+ idling\r\n"])
    with pytest.raises(MailThunderConnectionException, match="lost while idling"):
        provider.idle()
    client.lines.extend([b"+ idling\r\n"] + [b"* 1 FETCH (FLAGS ())\r\n"] * 1000)
    with pytest.raises(MailThunderConnectionException, match="IDLE did not end"):
        provider.idle()


def test_the_readable_check_sees_buffered_and_arriving_data(monkeypatch):
    class _Buffered:
        def pending(self):
            return 3

    assert imap_provider._readable(_Buffered(), 5) is True
    calls = []

    def select(read, _write, _error, seconds):
        calls.append(seconds)
        return (read if len(calls) > 1 else []), [], []

    monkeypatch.setattr(imap_provider.select, "select", select)
    connection = object()
    assert imap_provider._readable(connection, 0.5) is False
    assert imap_provider._readable(connection, 0.5) is True


def test_the_idle_backend_idles_between_looks_and_falls_back_to_sleeping(monkeypatch):
    provider, client = _imap()
    backend = IMAPIdleBackend(provider)
    assert backend.interval == 300.0 and backend.name == "imap-idle"
    idled = []
    monkeypatch.setattr(provider, "idle", lambda folder, timeout, should_stop: idled.append((folder, timeout)))
    backend.wait(12)
    assert idled == [("INBOX", 12)]

    def no_idle(folder, timeout, should_stop):
        raise MailThunderProviderException("the imap server does not offer IDLE")

    monkeypatch.setattr(provider, "idle", no_idle)
    slept = []
    monkeypatch.setattr(backend._stopping, "wait", slept.append)
    backend.wait(120)
    assert slept == [backend.retry_seconds]


# --- running, the manager and Mail.watch -------------------------------------------------------------------------

class _Scripted(MailTriggerBackend):
    """A backend whose looks are scripted: each one is a number of events or an error."""

    name = "scripted"
    retry_seconds = 0.01

    def __init__(self, script, interval=0.01):
        super().__init__(interval)
        self.script = list(script)
        self.looked = threading.Event()
        self.waits = []
        self.closed = 0

    def poll(self):
        if not self.script:
            self.looked.set()
            return 0
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        self._emit(MailEvent(MESSAGE_RECEIVED, metadata={"step": step}))
        return step

    def wait(self, seconds):
        self.waits.append(seconds)
        super().wait(seconds)

    def close(self):
        self.closed += 1


def test_a_running_backend_survives_failures_and_reports_them():
    backend = _Scripted([MailThunderAuthenticationException("refused"), MailThunderProviderException("no folder"),
                         MailThunderConnectionException("down"), 1])
    events = []
    backend.bind(events.append)
    assert backend.running is False
    backend.start()
    backend.start()
    assert backend.looked.wait(5) and backend.running
    backend.stop()
    assert backend.running is False and backend.closed == 1
    assert [event.name for event in events] == [AUTHENTICATION_FAILED, CONNECTION_FAILED, MESSAGE_RECEIVED]
    assert events[0].provider == "scripted"
    assert backend.waits[:4] == [0.01, 0.01, 0.01, 0.01]
    assert _Scripted([]).poll() == 0


def test_the_manager_runs_the_backends_it_is_given():
    dispatcher = EventDispatcher()
    seen = _collector(dispatcher)
    manager = TriggerManager(dispatcher.emit)
    first, second = manager.add(_Scripted([2])), manager.add(_Scripted([3, 1]))
    assert manager.backends == (first, second)
    assert manager.poll() == 5 and len(seen) == 2
    manager.start()
    assert first.looked.wait(5) and second.looked.wait(5)
    manager.stop()
    manager.remove(first)
    manager.remove(first)
    assert manager.backends == (second,) and (first.closed, second.closed) == (2, 1)
    with pytest.raises(MailThunderTriggerException, match="expected a MailTriggerBackend"):
        manager.add(object())


def test_watch_gives_the_watcher_its_own_store_when_the_account_can(monkeypatch):
    built = []

    def providers(_account):
        store = _store(1)
        built.append(store)
        return [RecordingSender(), store]

    monkeypatch.setattr(mail_module, "create_providers", providers)
    mail = Mail(provider="google", auth=_AUTH)
    events = _collector(mail.events, MESSAGE_RECEIVED)
    backend = mail.watch("Reports", start=False, interval=5, batch_limit=10)
    assert isinstance(backend, PollingBackend) and backend.owns_store and backend.interval == 5.0
    assert mail.triggers.backends == (backend,) and backend.store is built[0] and not backend.running
    assert mail.triggers.poll() == 0
    _arrive(backend.store, stored_message("2", "New"))
    assert mail.triggers.poll() == 1 and events[0].message.subject == "New" and events[0].folder == "Reports"
    mail.close()
    assert backend.store.closed == 1


def test_watch_shares_the_store_of_a_mail_built_from_providers():
    store = _store(1)
    mail, _sender = _mail(providers=[store])
    backend = mail.watch(start=False)
    assert backend.store is store and backend.owns_store is False and backend._lock is mail._lock
    with pytest.raises(MailThunderTriggerException, match="idle needs a connection of its own"):
        mail.watch(idle=True, start=False)
    with pytest.raises(MailThunderProviderException, match="no configured provider can read mail"):
        Mail(account=MailAccount(auth=_AUTH), providers=[RecordingSender()]).watch(start=False)


def test_watch_starts_a_thread_that_close_stops():
    store = _store(1)
    mail, _sender = _mail(providers=[store])
    arrived = threading.Event()
    mail.on("message_received", lambda event: arrived.set())
    backend = mail.watch(interval=0.01)
    assert backend.running
    _arrive(store, stored_message("2", "New"))
    assert arrived.wait(5)
    mail.close()
    assert not backend.running


def test_the_backend_follows_the_kind_of_store():
    provider, _client = _imap()
    assert type(create_backend(provider)) is IMAPPollingBackend
    assert type(create_backend(provider, "Archive", idle=True)) is IMAPIdleBackend
    assert type(create_backend(_store(), interval=5)) is PollingBackend
    with pytest.raises(MailThunderTriggerException, match="cannot wait for the server"):
        create_backend(_store(), idle=True)

    class _Push(PollingBackend):
        name = "push"

    register_backends(RecordingStore, PollingBackend, _Push)
    try:
        assert type(create_backend(_store(), idle=True)) is _Push
    finally:
        from je_mail_thunder.triggers import factory
        factory._polling_backends.pop(RecordingStore)
        factory._push_backends.pop(RecordingStore)
    for arguments in ((object, PollingBackend), (RecordingStore, object), (RecordingStore, PollingBackend, int)):
        with pytest.raises(MailThunderTriggerException, match="backends are registered"):
            register_backends(*arguments)


def test_the_poll_action_answers_with_what_arrived(monkeypatch):
    store = _store(1)
    monkeypatch.setattr(mail_instance, "_account", None)
    monkeypatch.setattr(mail_instance, "_uses_given_providers", True)
    monkeypatch.setattr(mail_instance, "_providers", (store,))
    monkeypatch.setattr(mail_instance, "triggers", TriggerManager(mail_instance.events.emit))
    first = execute_action([["MT_mail_poll"]])
    _arrive(store, stored_message("2", "New"))
    second = execute_action([["MT_mail_poll", {"folder": "INBOX"}]])
    assert list(first.values()) == [[]]
    (events,) = second.values()
    assert [(event["name"], event["message"]["subject"]) for event in json.loads(json.dumps(events))] == [
        ("message_received", "New")]
    assert len(mail_instance.triggers.backends) == 1 and mail_instance.events.subscriptions == ()
