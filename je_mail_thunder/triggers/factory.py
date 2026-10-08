"""
Which trigger backend watches which kind of store. A provider with a better way than plain polling registers it
here instead of changing :class:`~je_mail_thunder.core.mail.Mail`.
"""
from typing import Dict, Optional, Type

from je_mail_thunder.providers.base import DEFAULT_FOLDER, MailStore
from je_mail_thunder.providers.imap import IMAPProvider
from je_mail_thunder.triggers.imap import IMAPIdleBackend, IMAPPollingBackend
from je_mail_thunder.triggers.polling import PollingBackend
from je_mail_thunder.utils.exception.exceptions import MailThunderTriggerException

_polling_backends: Dict[Type[MailStore], Type[PollingBackend]] = {IMAPProvider: IMAPPollingBackend}
_push_backends: Dict[Type[MailStore], Type[PollingBackend]] = {IMAPProvider: IMAPIdleBackend}


def register_backends(store_type: Type[MailStore], polling: Type[PollingBackend],
                      push: Optional[Type[PollingBackend]] = None) -> None:
    """
    Say which backends watch a kind of store.

    :param store_type: a :class:`MailStore` class
    :param polling: the backend ``Mail.watch()`` uses for it
    :param push: the backend ``Mail.watch(idle=True)`` uses for it, when the provider can wait for the server
    :return: None
    :raises MailThunderTriggerException: a class is not what it should be
    """
    kinds = [polling] if push is None else [polling, push]
    if not (isinstance(store_type, type) and issubclass(store_type, MailStore)) or not all(
            isinstance(kind, type) and issubclass(kind, PollingBackend) for kind in kinds):
        raise MailThunderTriggerException("backends are registered as a MailStore class and PollingBackend classes")
    _polling_backends[store_type] = polling
    if push is not None:
        _push_backends[store_type] = push


def create_backend(store: MailStore, folder: str = DEFAULT_FOLDER, idle: bool = False, **options) -> PollingBackend:
    """
    The backend that watches a folder of ``store``.

    :param store: the provider to watch
    :param folder: the folder to watch
    :param idle: wait for the server to announce new mail instead of asking at intervals
    :param options: ``interval``, ``include_existing``, ``batch_limit`` and ``lock``, as the backend takes them
    :return: the backend, not started
    :raises MailThunderTriggerException: ``idle`` is asked of a store that can only be polled
    """
    registry = _push_backends if idle else _polling_backends
    for store_type, backend in registry.items():
        if isinstance(store, store_type):
            return backend(store, folder, **options)
    if idle:
        raise MailThunderTriggerException(f"the {store.name} provider cannot wait for the server; watch it by polling")
    return PollingBackend(store, folder, **options)
