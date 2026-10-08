"""
OAuth2 as an authentication mechanism: an access token that authorises HTTP APIs with ``Bearer``.

Acquiring, caching and refreshing the token, its expiry and the provider's scope stay in
:mod:`je_mail_thunder.utils.oauth2.oauth2`; this class is how a provider asks for one.
"""
from typing import Optional

from je_mail_thunder.auth.base import Authentication
from je_mail_thunder.utils.exception.exceptions import MailThunderAuthenticationException
from je_mail_thunder.utils.oauth2 import oauth2
from je_mail_thunder.utils.oauth2.oauth2 import OAuth2Settings, OAuth2TokenCache


class OAuth2Auth(Authentication):
    """An OAuth2 access token for the account, refreshed when it is about to expire."""

    mechanism = "oauth2"

    def __init__(self, settings: OAuth2Settings, token_cache: Optional[OAuth2TokenCache] = None) -> None:
        """
        :param settings: who logs in and how their access token is obtained
        :param token_cache: where tokens are kept and refreshed; the package's shared cache by default
        :raises MailThunderAuthenticationException: ``settings`` is not an :class:`OAuth2Settings`
        """
        if not isinstance(settings, OAuth2Settings):
            raise MailThunderAuthenticationException("OAuth2 authentication needs OAuth2Settings")
        super().__init__(settings.user)
        self.settings = settings
        self._token_cache = token_cache

    def access_token(self) -> str:
        """
        :return: an access token with more than a minute left
        :raises MailThunderOAuth2Exception: the token endpoint refused the refresh or could not be reached
        """
        # Read at call time, so the shared cache is the one in use even after it is replaced.
        cache = self._token_cache if self._token_cache is not None else oauth2.oauth2_token_cache
        return cache.access_token(self.settings)

    def authorization(self) -> str:
        """
        :return: ``Bearer <access token>``, the HTTP ``Authorization`` header's value
        """
        return f"Bearer {self.access_token()}"
