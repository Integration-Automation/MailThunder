"""
Where the SMTP and IMAP wrappers find how to log in: the content file first, then the environment.

OAuth2 settings, when present, are used instead of a password: an ``"oauth2"`` object in
``mail_thunder_content.json``, else the ``mail_thunder_oauth2_*`` environment variables.
"""
import os
from typing import Mapping, Optional, Tuple

from je_mail_thunder.utils.exception.exceptions import MailThunderOAuth2Exception
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.oauth2.oauth2 import OAUTH2_SETTING_NAMES, OAuth2Provider, OAuth2Settings
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import read_output_content
from je_mail_thunder.utils.save_mail_user_content.save_on_env import get_mail_thunder_os_environ

OAUTH2_ENVIRONMENT_PREFIX = "mail_thunder_oauth2_"
_USER_VARIABLE = "mail_thunder_user"


def resolve_login_credentials() -> Optional[Tuple[str, str]]:
    """
    ``(user, password)`` from ``mail_thunder_content.json`` in the current directory when it has both, else from
    the ``mail_thunder_user`` / ``mail_thunder_user_password`` environment variables, else ``None``.
    """
    user_info = read_output_content()
    if isinstance(user_info, dict):
        user = user_info.get("user")
        password = user_info.get("password")
        if user is not None and password is not None:
            return user, password
    env_info = get_mail_thunder_os_environ()
    user = env_info.get("mail_thunder_user")
    password = env_info.get("mail_thunder_user_password")
    if user is not None and password is not None:
        return user, password
    return None


def oauth2_settings_from_environ(environ: Optional[Mapping[str, str]] = None) -> Optional[OAuth2Settings]:
    """
    Settings from ``mail_thunder_oauth2_<field>`` variables (``provider``, ``client_id``, ``client_secret``,
    ``refresh_token``, ``access_token``, ``tenant``, ``token_url``, ``scope``) and ``mail_thunder_user``;
    ``None`` when neither a refresh token nor an access token is set.

    :raises MailThunderOAuth2Exception: the variables are set but incomplete or invalid.
    """
    environ = os.environ if environ is None else environ
    # Looked up by name: Windows keeps environment names upper-cased, and only its lookups ignore case.
    values = {name: environ.get(OAUTH2_ENVIRONMENT_PREFIX + name) for name in OAUTH2_SETTING_NAMES}
    if not values.get("refresh_token") and not values.get("access_token"):
        return None
    return OAuth2Settings.from_mapping(values, user=environ.get(_USER_VARIABLE))


def resolve_oauth2_settings() -> Optional[OAuth2Settings]:
    """
    The ``"oauth2"`` object of ``mail_thunder_content.json`` (its ``user``, else the file's ``user``), else the
    environment (:func:`oauth2_settings_from_environ`), else ``None``.

    :raises MailThunderOAuth2Exception: the settings found are incomplete or invalid.
    """
    content = read_output_content()
    if isinstance(content, dict) and content.get("oauth2") is not None:
        block = content["oauth2"]
        if not isinstance(block, dict):
            raise MailThunderOAuth2Exception('"oauth2" in mail_thunder_content.json must be a JSON object')
        return OAuth2Settings.from_mapping(block, user=content.get("user"))
    return oauth2_settings_from_environ()


def configured_oauth2_provider() -> Optional[OAuth2Provider]:
    """The provider preset the OAuth2 settings name, or ``None`` (no settings, invalid ones, or a custom endpoint)."""
    try:
        settings = resolve_oauth2_settings()
    except MailThunderOAuth2Exception as error:
        mail_thunder_logger.error(f"OAuth2 settings ignored for choosing the server: {error}")
        return None
    if settings is None or settings.token_url is not None:
        return None
    return settings.preset
