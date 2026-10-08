"""
The authentication mechanisms a provider logs in with, and where the default one comes from.
"""
import json

import pytest

from je_mail_thunder.auth.base import Authentication
from je_mail_thunder.auth.oauth2 import OAuth2Auth
from je_mail_thunder.auth.password import AppPasswordAuth, PasswordAuth
from je_mail_thunder.auth.xoauth2 import XOAUTH2Auth
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderAuthenticationException,
    MailThunderException,
    MailThunderOAuth2Exception,
)
from je_mail_thunder.utils.oauth2 import oauth2
from je_mail_thunder.utils.oauth2.oauth2 import OAuth2Settings, OAuth2TokenCache
from je_mail_thunder.utils.save_mail_user_content.credentials import resolve_authentication

_USER = "someone@example.com"
_PASSWORD = "p4ss-word-secret"
_TOKEN = "ya29.access-token-secret"
_REFRESH = "1//refresh-token-secret"
_ENV_NAMES = ("mail_thunder_user", "mail_thunder_user_password") + tuple(
    f"mail_thunder_oauth2_{name}" for name in oauth2.OAUTH2_SETTING_NAMES)


class _Client:
    """Records the logins a mechanism performs."""

    def __init__(self):
        self.logins = []

    def login(self, user, password):
        self.logins.append(("login", user, password))

    def oauth2_login(self, user, access_token):
        self.logins.append(("oauth2_login", user, access_token))


@pytest.fixture()
def clean_place(tmp_path, monkeypatch):
    """An empty cwd (no mail_thunder_content.json) and no credential variables."""
    monkeypatch.chdir(tmp_path)
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _write_content(directory, content):
    (directory / "mail_thunder_content.json").write_text(json.dumps(content), encoding="utf-8")


def test_authentication_is_an_interface():
    with pytest.raises(TypeError):
        Authentication(_USER)  # pylint: disable=abstract-class-instantiated  # reason: the point of the test


def test_password_auth_logs_the_client_in():
    client = _Client()
    auth = PasswordAuth(_USER, _PASSWORD)
    auth.login(client)
    assert client.logins == [("login", _USER, _PASSWORD)]
    assert (auth.user, auth.mechanism) == (_USER, "password")


def test_an_app_password_is_used_without_the_spaces_it_is_shown_with():
    client = _Client()
    auth = AppPasswordAuth(_USER, "abcd efgh  ijkl\tmnop")
    auth.login(client)
    assert client.logins == [("login", _USER, "abcdefghijklmnop")]
    assert auth.mechanism == "app-password"
    assert isinstance(auth, PasswordAuth)


@pytest.mark.parametrize("build", [
    lambda: PasswordAuth("", _PASSWORD), lambda: PasswordAuth(None, _PASSWORD), lambda: PasswordAuth(_USER, ""),
    lambda: PasswordAuth(_USER, None), lambda: AppPasswordAuth(_USER, "   "), lambda: AppPasswordAuth(_USER, 1234),
])
def test_a_password_login_needs_a_user_and_a_password(build):
    with pytest.raises(MailThunderAuthenticationException):
        build()


def test_secrets_stay_out_of_the_repr():
    settings = OAuth2Settings(user=_USER, client_id="c", client_secret="client-secret", refresh_token=_REFRESH)
    for auth in (PasswordAuth(_USER, _PASSWORD), AppPasswordAuth(_USER, _PASSWORD), OAuth2Auth(settings),
                 XOAUTH2Auth(OAuth2Settings(user=_USER, access_token=_TOKEN))):
        shown = repr(auth)
        assert _USER in shown and type(auth).__name__ in shown
        for secret in (_PASSWORD, _TOKEN, _REFRESH, "client-secret"):
            assert secret not in shown


def test_a_password_cannot_authorise_an_http_request():
    with pytest.raises(MailThunderAuthenticationException, match="password authentication cannot authorise"):
        PasswordAuth(_USER, _PASSWORD).authorization()


def test_oauth2_gives_a_bearer_authorization():
    auth = OAuth2Auth(OAuth2Settings(user=_USER, access_token=_TOKEN))
    assert auth.access_token() == _TOKEN
    assert auth.authorization() == f"Bearer {_TOKEN}"
    assert (auth.user, auth.mechanism) == (_USER, "oauth2")


def test_oauth2_refreshes_through_its_token_cache():
    posts = []

    def post(url, form, _timeout):
        posts.append((url, form["grant_type"]))
        return {"access_token": "fresh-token", "expires_in": 3600}

    settings = OAuth2Settings(user=_USER, client_id="c", refresh_token=_REFRESH)
    auth = OAuth2Auth(settings, token_cache=OAuth2TokenCache(post=post, clock=lambda: 0.0))
    assert auth.authorization() == "Bearer fresh-token"
    assert auth.access_token() == "fresh-token"
    assert posts == [("https://oauth2.googleapis.com/token", "refresh_token")]


def test_oauth2_uses_the_shared_cache_by_default(monkeypatch):
    cache = OAuth2TokenCache(post=lambda *_: {"access_token": "shared-token"}, clock=lambda: 0.0)
    monkeypatch.setattr(oauth2, "oauth2_token_cache", cache)
    auth = OAuth2Auth(OAuth2Settings(user=_USER, client_id="c", refresh_token=_REFRESH))
    assert auth.access_token() == "shared-token"


def test_plain_oauth2_has_no_mail_server_login():
    with pytest.raises(MailThunderAuthenticationException, match="oauth2 authentication cannot log in _Client"):
        OAuth2Auth(OAuth2Settings(user=_USER, access_token=_TOKEN)).login(_Client())


def test_xoauth2_logs_the_client_in_with_the_token():
    client = _Client()
    auth = XOAUTH2Auth(OAuth2Settings(user=_USER, access_token=_TOKEN))
    auth.login(client)
    assert client.logins == [("oauth2_login", _USER, _TOKEN)]
    assert auth.mechanism == "xoauth2"
    assert auth.authorization() == f"Bearer {_TOKEN}"


def test_oauth2_needs_oauth2_settings():
    with pytest.raises(MailThunderAuthenticationException, match="needs OAuth2Settings"):
        OAuth2Auth({"user": _USER, "access_token": _TOKEN})


def test_an_oauth2_error_is_an_authentication_error():
    assert issubclass(MailThunderOAuth2Exception, MailThunderAuthenticationException)
    assert issubclass(MailThunderAuthenticationException, MailThunderException)


def test_no_credentials_anywhere_is_no_authentication(clean_place):
    assert resolve_authentication() is None


def test_the_content_file_password_becomes_password_auth(clean_place):
    _write_content(clean_place, {"user": _USER, "password": _PASSWORD})
    client = _Client()
    auth = resolve_authentication()
    auth.login(client)
    assert type(auth) is PasswordAuth
    assert client.logins == [("login", _USER, _PASSWORD)]


def test_the_environment_password_is_used_without_a_file(clean_place, monkeypatch):
    monkeypatch.setenv("mail_thunder_user", _USER)
    monkeypatch.setenv("mail_thunder_user_password", _PASSWORD)
    assert resolve_authentication().user == _USER


def test_oauth2_settings_win_over_the_password(clean_place):
    _write_content(clean_place, {"user": _USER, "password": _PASSWORD,
                                 "oauth2": {"provider": "microsoft", "access_token": _TOKEN}})
    client = _Client()
    auth = resolve_authentication()
    auth.login(client)
    assert type(auth) is XOAUTH2Auth
    assert auth.settings.provider == "microsoft"
    assert client.logins == [("oauth2_login", _USER, _TOKEN)]


def test_invalid_oauth2_settings_are_reported_not_skipped(clean_place):
    _write_content(clean_place, {"user": _USER, "password": _PASSWORD, "oauth2": {"refresh_token": _REFRESH}})
    with pytest.raises(MailThunderOAuth2Exception):
        resolve_authentication()
