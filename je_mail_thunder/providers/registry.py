"""
Which providers an account gets, by its provider name. A new backend registers a factory here instead of
changing :class:`~je_mail_thunder.core.mail.Mail`.
"""
from typing import Callable, Dict, Sequence, Tuple

from je_mail_thunder.core.account import SERVER_PRESETS, MailAccount
from je_mail_thunder.providers.base import MailProvider
from je_mail_thunder.providers.file import PROVIDER_NAME as FILE_PROVIDER, FileProvider
from je_mail_thunder.providers.imap import IMAPProvider
from je_mail_thunder.providers.microsoft_graph import PROVIDER_NAME as GRAPH_PROVIDER, MicrosoftGraphProvider
from je_mail_thunder.providers.smtp import SMTPProvider
from je_mail_thunder.utils.exception.exceptions import MailThunderProviderException

ProviderFactory = Callable[[MailAccount], Sequence[MailProvider]]
# Any SMTP / IMAP server; the account names its hosts.
GENERIC_PROVIDER = "smtp"


def smtp_and_imap_providers(account: MailAccount) -> Tuple[MailProvider, ...]:
    """
    :param account: an account reached over SMTP and IMAP
    :return: its SMTP sender and its IMAP store; neither connects until it is used
    """
    return SMTPProvider(account), IMAPProvider(account)


def graph_provider(account: MailAccount) -> Tuple[MailProvider, ...]:
    """
    :param account: a Microsoft 365 account that logs in with OAuth2
    :return: the one provider that both sends and reads over Microsoft Graph
    """
    return (MicrosoftGraphProvider(account),)


def file_provider(_account: MailAccount) -> Tuple[MailProvider, ...]:
    """
    :return: the provider that keeps mail as ``.eml`` files instead of sending it, for dry runs and tests
    """
    return (FileProvider(),)


_factories: Dict[str, ProviderFactory] = dict.fromkeys(SERVER_PRESETS, smtp_and_imap_providers)
_factories[GENERIC_PROVIDER] = smtp_and_imap_providers
_factories[GRAPH_PROVIDER] = graph_provider
_factories[FILE_PROVIDER] = file_provider


def register_provider(name: str, factory: ProviderFactory) -> None:
    """
    Make a provider name usable in :class:`~je_mail_thunder.core.account.MailAccount`.

    :param name: the provider's name (case does not matter); an existing name is replaced
    :param factory: builds the account's providers, without connecting
    :return: None
    :raises MailThunderProviderException: the name is not text, or the factory is not callable
    """
    if not isinstance(name, str) or not name.strip() or not callable(factory):
        raise MailThunderProviderException("a provider is registered with a name and a factory function")
    _factories[name.strip().lower()] = factory


def registered_providers() -> Tuple[str, ...]:
    """
    :return: the provider names an account can use, sorted
    """
    return tuple(sorted(_factories))


def create_providers(account: MailAccount) -> Tuple[MailProvider, ...]:
    """
    :param account: the account to reach
    :return: the providers its provider name stands for
    :raises MailThunderProviderException: no provider is registered under that name
    """
    factory = _factories.get(account.provider)
    if factory is None:
        raise MailThunderProviderException(
            f"unknown mail provider {account.provider!r}: use one of {list(registered_providers())}")
    return tuple(factory(account))
