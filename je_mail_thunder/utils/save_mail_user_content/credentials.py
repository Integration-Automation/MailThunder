"""Where the SMTP and IMAP wrappers find a user and password: the content file first, then the environment."""
from typing import Optional, Tuple

from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import read_output_content
from je_mail_thunder.utils.save_mail_user_content.save_on_env import get_mail_thunder_os_environ


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
