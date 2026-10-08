"""
OAuth2 for SMTP and IMAP: the access token goes to the server as SASL ``XOAUTH2``.
"""
from je_mail_thunder.auth.oauth2 import OAuth2Auth


class XOAUTH2Auth(OAuth2Auth):
    """OAuth2 that can also log an SMTP or IMAP client in, which Gmail and Microsoft 365 ask for."""

    mechanism = "xoauth2"

    def login(self, client) -> None:
        """
        :param client: a connected MailThunder SMTP or IMAP wrapper
        :return: None
        :raises MailThunderOAuth2Exception: no access token could be obtained
        """
        client.oauth2_login(self.user, self.access_token())
