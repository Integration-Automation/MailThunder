"""
Whose mail a :class:`~je_mail_thunder.core.mail.Mail` handles: the provider, its servers and the login.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional

from je_mail_thunder.auth.base import Authentication
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderAuthenticationException,
    MailThunderProviderException,
)
from je_mail_thunder.utils.oauth2.oauth2 import OAUTH2_PROVIDERS
from je_mail_thunder.utils.save_mail_user_content.credentials import (
    configured_mail_provider,
    configured_oauth2_provider,
    resolve_authentication,
)

IMPLICIT_TLS_PORT = 465
STARTTLS_PORT = 587
# The provider an account has when nothing names one: Gmail, where the SMTP and IMAP wrappers connect by default.
DEFAULT_PROVIDER = "google"
# Other names a provider is known by.
PROVIDER_ALIASES: Mapping[str, str] = MappingProxyType({"gmail": "google"})


@dataclass(frozen=True)
class MailServers:
    """
    The servers of an account that is reached over SMTP and IMAP.

    :param smtp_host: the SMTP server
    :param smtp_port: its port; 587 with ``smtp_starttls``, else 465
    :param smtp_starttls: upgrade with ``STARTTLS`` instead of connecting over implicit TLS
    :param imap_host: the IMAP server (implicit TLS, port 993)
    :param drafts_folder: the IMAP folder drafts are stored in; found by its ``\\Drafts`` flag when not given
    """

    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_starttls: bool = False
    imap_host: Optional[str] = None
    drafts_folder: Optional[str] = None

    @property
    def port(self) -> int:
        """The SMTP port to connect to."""
        if self.smtp_port is not None:
            return self.smtp_port
        return STARTTLS_PORT if self.smtp_starttls else IMPLICIT_TLS_PORT


# Providers that log in with an app password over SMTP and IMAP.
_PASSWORD_PRESETS = {
    "yahoo": MailServers("smtp.mail.yahoo.com", IMPLICIT_TLS_PORT, False, "imap.mail.yahoo.com"),
    "icloud": MailServers("smtp.mail.me.com", STARTTLS_PORT, True, "imap.mail.me.com"),
    "zoho": MailServers("smtp.zoho.com", IMPLICIT_TLS_PORT, False, "imap.zoho.com"),
    "fastmail": MailServers("smtp.fastmail.com", IMPLICIT_TLS_PORT, False, "imap.fastmail.com"),
}
# The servers of the providers MailThunder knows. Google's and Microsoft's are taken from the OAuth2 presets, so
# both name the same hosts.
SERVER_PRESETS: Mapping[str, MailServers] = MappingProxyType({
    **{name: MailServers(preset.smtp_host, preset.smtp_port, preset.smtp_starttls, preset.imap_host)
       for name, preset in OAUTH2_PROVIDERS.items()},
    **_PASSWORD_PRESETS,
})


@dataclass(frozen=True)
class MailAccount:
    """
    An account and how it is reached.

    :param provider: a registered provider name: ``"google"`` (or ``"gmail"``), ``"microsoft"``,
        ``"microsoft_graph"``, ``"yahoo"``, ``"icloud"``, ``"zoho"``, ``"fastmail"``, ``"file"``, or ``"smtp"`` for
        any other SMTP / IMAP server, which needs ``servers``
    :param auth: how the account logs in; by default what ``mail_thunder_content.json`` or the environment
        holds, looked up when the account first connects
    :param servers: the SMTP and IMAP servers, replacing the provider's own
    :raises MailThunderProviderException: the provider name is not text
    """

    provider: str = DEFAULT_PROVIDER
    auth: Optional[Authentication] = None
    servers: Optional[MailServers] = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise MailThunderProviderException("a mail account needs a provider name")
        name = self.provider.strip().lower()
        # A frozen dataclass normalises its own fields through object.__setattr__.
        object.__setattr__(self, "provider", PROVIDER_ALIASES.get(name, name))

    @property
    def resolved_servers(self) -> MailServers:
        """
        :return: ``servers`` when given, else the provider's preset
        :raises MailThunderProviderException: neither exists
        """
        servers = self.servers or SERVER_PRESETS.get(self.provider)
        if servers is None:
            raise MailThunderProviderException(
                f"the provider {self.provider!r} has no known servers: give the account its MailServers")
        return servers

    def authentication(self) -> Authentication:
        """
        :return: ``auth`` when given, else the login of the content file or the environment
        :raises MailThunderAuthenticationException: there is nothing to log in with
        """
        auth = self.auth if self.auth is not None else resolve_authentication()
        if auth is None:
            raise MailThunderAuthenticationException(
                "no credentials: give the account an Authentication, or set them in mail_thunder_content.json "
                "or the mail_thunder_user / mail_thunder_user_password environment variables")
        return auth


def default_account() -> MailAccount:
    """
    The account of the content file or the environment. Its provider is the one ``"mail_provider"`` in the
    content file or ``mail_thunder_mail_provider`` in the environment names; without either, the servers the
    ``smtp_instance`` and ``imap_instance`` of the same settings use: the OAuth2 provider's when one is named,
    else Gmail's.

    :return: the account; its login is looked up when it first connects
    """
    named = configured_mail_provider()
    if named is not None:
        return MailAccount(provider=named)
    preset = configured_oauth2_provider()
    return MailAccount(provider=preset.name if preset is not None else DEFAULT_PROVIDER)
