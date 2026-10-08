"""
Password logins: the account's own password, or an app password issued for one application.
"""
from je_mail_thunder.auth.base import Authentication
from je_mail_thunder.utils.exception.exceptions import MailThunderAuthenticationException


class PasswordAuth(Authentication):
    """The account's password, sent with the server's own login once TLS is up."""

    mechanism = "password"

    def __init__(self, user: str, password: str) -> None:
        """
        :param user: the account's mail address
        :param password: its password
        :raises MailThunderAuthenticationException: the user or the password is missing
        """
        super().__init__(user)
        if not isinstance(password, str) or not password:
            raise MailThunderAuthenticationException(f"{self.mechanism} authentication needs the password")
        self._password = password

    def login(self, client) -> None:
        """
        :param client: a connected MailThunder SMTP or IMAP wrapper
        :return: None
        """
        client.login(self.user, self._password)


class AppPasswordAuth(PasswordAuth):
    """
    An app password: what Google, Yahoo or iCloud issue to one application of an account with two-step
    verification. Providers show it in groups separated by spaces, which are not part of it.
    """

    mechanism = "app-password"

    def __init__(self, user: str, app_password: str) -> None:
        """
        :param user: the account's mail address
        :param app_password: the app password, with or without the spaces it is shown with
        :raises MailThunderAuthenticationException: the user or the app password is missing
        """
        super().__init__(user, "".join(app_password.split()) if isinstance(app_password, str) else app_password)
