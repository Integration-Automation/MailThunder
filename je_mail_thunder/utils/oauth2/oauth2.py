"""
OAuth2 login for SMTP and IMAP (SASL ``XOAUTH2``), with the standard library only.

Google and Microsoft are retiring password logins for mail. With OAuth2 the client keeps a refresh token,
obtained once through the provider's consent flow outside MailThunder, and exchanges it at the provider's token
endpoint for a short-lived access token. The server is then sent ``user=<user>^Aauth=Bearer <token>^A^A``.

Secrets (client secret, refresh token, access token) never appear in a ``repr``, a log line or an exception
message from this module.
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Dict, Mapping, Optional

from je_mail_thunder.utils.exception.exceptions import MailThunderOAuth2Exception

TOKEN_TIMEOUT_SECONDS = 30
# An access token is refreshed this long before it expires, so a login never races its expiry.
REFRESH_MARGIN_SECONDS = 60
# Used when the token endpoint gives no ``expires_in``; both providers issue one-hour tokens.
DEFAULT_TOKEN_LIFETIME_SECONDS = 3600
_TENANT_PATTERN = re.compile(r"[A-Za-z0-9.-]+")
# The settings besides ``user``: field names, content-file keys, and the environment variables' suffixes.
OAUTH2_SETTING_NAMES = (
    "provider", "client_id", "client_secret", "refresh_token", "access_token", "tenant", "token_url", "scope",
)

PostForm = Callable[[str, Mapping[str, str], float], Mapping[str, Any]]
Clock = Callable[[], float]


@dataclass(frozen=True)
class OAuth2Provider:
    """A provider's token endpoint (``{tenant}`` is filled in), mail scope and mail servers."""

    name: str
    token_url: str
    scope: str
    smtp_host: str
    smtp_port: int
    smtp_starttls: bool
    imap_host: str


# Where each provider issues tokens: public addresses, named here so that a preset is not read as holding a secret.
_GOOGLE_ENDPOINT = "https://oauth2.googleapis.com/token"
_MICROSOFT_ENDPOINT = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

OAUTH2_PROVIDERS: Mapping[str, OAuth2Provider] = MappingProxyType({
    "google": OAuth2Provider(
        name="google",
        token_url=_GOOGLE_ENDPOINT,
        scope="https://mail.google.com/",
        smtp_host="smtp.gmail.com", smtp_port=465, smtp_starttls=False,
        imap_host="imap.gmail.com",
    ),
    "microsoft": OAuth2Provider(
        name="microsoft",
        token_url=_MICROSOFT_ENDPOINT,
        scope="https://outlook.office.com/SMTP.Send https://outlook.office.com/IMAP.AccessAsUser.All offline_access",
        smtp_host="smtp.office365.com", smtp_port=587, smtp_starttls=True,
        imap_host="outlook.office365.com",
    ),
})


@dataclass(frozen=True)
class OAuth2Settings:
    """
    Who logs in and how their access token is obtained.

    Either ``access_token`` (used as given) or ``client_id`` plus ``refresh_token`` (exchanged at the token
    endpoint) is required. ``provider`` names a preset in :data:`OAUTH2_PROVIDERS`; ``token_url`` and ``scope``
    override the preset's, and with ``token_url`` set any other provider works too. The token endpoint must be
    ``https``.

    :raises MailThunderOAuth2Exception: the settings are incomplete or invalid.
    """

    user: str
    provider: str = "google"
    client_id: Optional[str] = None
    client_secret: Optional[str] = field(default=None, repr=False)
    refresh_token: Optional[str] = field(default=None, repr=False)
    access_token: Optional[str] = field(default=None, repr=False)
    tenant: str = "common"
    token_url: Optional[str] = None
    scope: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.user, str) or not self.user:
            raise MailThunderOAuth2Exception("OAuth2 needs the mail user")
        for name in OAUTH2_SETTING_NAMES:
            if getattr(self, name) is not None and not isinstance(getattr(self, name), str):
                raise MailThunderOAuth2Exception(f"the OAuth2 setting {name!r} must be a string")
        if self.access_token:
            return
        if not self.client_id or not self.refresh_token:
            raise MailThunderOAuth2Exception("OAuth2 needs an access_token, or a client_id and a refresh_token")
        if self.token_url is None and self.provider not in OAUTH2_PROVIDERS:
            raise MailThunderOAuth2Exception(
                f"unknown OAuth2 provider {self.provider!r}: use one of {sorted(OAUTH2_PROVIDERS)} or set token_url")
        if not _TENANT_PATTERN.fullmatch(self.tenant):
            raise MailThunderOAuth2Exception(f"invalid OAuth2 tenant {self.tenant!r}")
        if not self.endpoint.startswith("https://"):
            raise MailThunderOAuth2Exception("the OAuth2 token endpoint must use https")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any], user: Optional[str] = None) -> OAuth2Settings:
        """Settings from a mapping of the field names (``user`` there wins over the ``user`` argument)."""
        chosen = {name: values[name] for name in OAUTH2_SETTING_NAMES if values.get(name) not in (None, "")}
        return cls(user=values.get("user") or user or "", **chosen)

    @property
    def preset(self) -> Optional[OAuth2Provider]:
        """The :data:`OAUTH2_PROVIDERS` entry named by ``provider``, if there is one."""
        return OAUTH2_PROVIDERS.get(self.provider)

    @property
    def endpoint(self) -> str:
        """The token endpoint to post the refresh to."""
        preset = self.preset
        template = self.token_url or (preset.token_url if preset is not None else "")
        return template.replace("{tenant}", self.tenant)


@dataclass(frozen=True)
class AccessToken:
    """An access token and when it expires, on the clock it was issued against."""

    value: str = field(repr=False)
    expires_at: float

    def fresh(self, now: float) -> bool:
        """True while the token has more than :data:`REFRESH_MARGIN_SECONDS` left."""
        return now < self.expires_at - REFRESH_MARGIN_SECONDS


def xoauth2_string(user: str, access_token: str) -> str:
    """The SASL ``XOAUTH2`` initial response, before base64."""
    return f"user={user}\x01auth=Bearer {access_token}\x01\x01"


def _error_text(answer: Mapping[str, Any]) -> str:
    error = answer.get("error", "no error code")
    description = answer.get("error_description")
    return f"{error}: {description}" if description else str(error)


def _post_form(url: str, form: Mapping[str, str], timeout: float) -> Mapping[str, Any]:
    """POST ``form`` URL-encoded to ``url`` (checked to be https) and return the JSON answer."""
    if not url.startswith("https://"):
        raise MailThunderOAuth2Exception("the OAuth2 token endpoint must use https")
    request = urllib.request.Request(
        url, data=urllib.parse.urlencode(form).encode("ascii"), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - https only, checked above
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            answer = json.loads(error.read().decode("utf-8"))
        except ValueError:
            answer = {}
        detail = _error_text(answer) if isinstance(answer, dict) else "no details"
        raise MailThunderOAuth2Exception(f"the token endpoint refused the refresh (HTTP {error.code}): {detail}") \
            from None
    except (OSError, ValueError) as error:
        raise MailThunderOAuth2Exception(f"the token endpoint could not be used: {type(error).__name__}") from None


def _lifetime(answer: Mapping[str, Any]) -> float:
    try:
        return float(answer.get("expires_in", DEFAULT_TOKEN_LIFETIME_SECONDS))
    except (TypeError, ValueError):
        return float(DEFAULT_TOKEN_LIFETIME_SECONDS)


def refresh_access_token(settings: OAuth2Settings, post: PostForm = _post_form,
                         clock: Clock = time.monotonic) -> AccessToken:
    """
    Exchange the refresh token for an access token at ``settings.endpoint``.

    :param post: sends the form and returns the JSON answer (replaceable for tests or a proxy-aware client).
    :param clock: the clock ``expires_at`` is measured on.
    :raises MailThunderOAuth2Exception: the endpoint refused, was unreachable or gave no access token.
    """
    if not settings.refresh_token or not settings.client_id:
        raise MailThunderOAuth2Exception("OAuth2 refresh needs a client_id and a refresh_token")
    form: Dict[str, str] = {
        "grant_type": "refresh_token",
        "client_id": settings.client_id,
        "refresh_token": settings.refresh_token,
    }
    if settings.client_secret:
        form["client_secret"] = settings.client_secret
    preset = settings.preset
    scope = settings.scope or (preset.scope if preset is not None and settings.token_url is None else None)
    if scope:
        form["scope"] = scope
    answer = post(settings.endpoint, form, TOKEN_TIMEOUT_SECONDS)
    token = answer.get("access_token") if isinstance(answer, Mapping) else None
    if not isinstance(token, str) or not token:
        detail = _error_text(answer) if isinstance(answer, Mapping) else "not a JSON object"
        raise MailThunderOAuth2Exception(f"the token endpoint gave no access token: {detail}")
    return AccessToken(token, clock() + _lifetime(answer))


class OAuth2TokenCache:
    """Access tokens by settings, refreshed when missing or about to expire. Safe to share between threads."""

    def __init__(self, post: PostForm = _post_form, clock: Clock = time.monotonic) -> None:
        self._post = post
        self._clock = clock
        self._tokens: Dict[OAuth2Settings, AccessToken] = {}
        self._lock = threading.Lock()

    def access_token(self, settings: OAuth2Settings) -> str:
        """``settings.access_token`` when given, else a cached token that is still fresh, else a new one."""
        if settings.access_token:
            return settings.access_token
        with self._lock:
            cached = self._tokens.get(settings)
            if cached is not None and cached.fresh(self._clock()):
                return cached.value
            token = refresh_access_token(settings, self._post, self._clock)
            self._tokens[settings] = token
            return token.value

    def clear(self) -> None:
        """Forget every cached token."""
        with self._lock:
            self._tokens.clear()


# The cache the SMTP and IMAP wrappers log in with.
oauth2_token_cache = OAuth2TokenCache()
