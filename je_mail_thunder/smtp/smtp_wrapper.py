import smtplib
from email.message import EmailMessage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mimetypes import guess_type
from os import path
from smtplib import SMTP, SMTP_SSL
from typing import Optional

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.attachments.policy import DEFAULT_ATTACHMENT_POLICY
from je_mail_thunder.attachments.validator import validate_attachments
from je_mail_thunder.utils.exception.exceptions import MailThunderOAuth2Exception
from je_mail_thunder.utils.lazy_instance.lazy_instance import LazyInstance
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.oauth2.oauth2 import oauth2_token_cache, xoauth2_string
from je_mail_thunder.utils.save_mail_user_content.credentials import (
    configured_oauth2_provider,
    resolve_login_credentials,
    resolve_oauth2_settings,
)
from je_mail_thunder.utils.tls.tls_context import verified_client_context


class SMTPClientMixin:
    """
    What MailThunder's SMTP clients add to :mod:`smtplib`: building messages, logging in with the content file or
    the environment, sending and quitting. It goes before the ``smtplib`` class in the bases.
    """

    #: What ``create_message_with_attach_and_send`` checks its attachment against before sending; ``None`` turns
    #: the check off.
    attachment_policy = DEFAULT_ATTACHMENT_POLICY

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def later_init(self):
        """
        Try to log in
        :return: None
        """
        mail_thunder_logger.info("MT_smtp_later_init")
        try:
            self.try_to_login_with_env_or_content()
        except Exception as error:
            mail_thunder_logger.error(f"smtp_later_init, failed: {error}")

    @staticmethod
    def create_message(message_content: str, message_setting_dict: dict, **kwargs):
        """
        Create new EmailMessage instance
        :param message_content: Mail content
        :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
        :param kwargs: EmailMessage setting
        :return: None
        """
        mail_thunder_logger.info(
            f"smtp_create_message, message_content{message_content}, message_setting_dict: {message_setting_dict}")
        try:
            message = EmailMessage(**kwargs)
            message.set_content(message_content)
            for key, value in message_setting_dict.items():
                message[key] = value
            return message
        except Exception as error:
            mail_thunder_logger.error(
                f"smtp_create_message, message_content{message_content}, "
                f"message_setting_dict: {message_setting_dict}, failed: {repr(error)}")

    @staticmethod
    def create_message_with_attach(message_content: str, message_setting_dict: dict,
                                   attach_file: str, use_html: bool = False):
        """
        Create new EmailMessage with attach file instance
        :param message_content: Mail content
        :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
        :param attach_file: File path as str
        :param use_html: Enable HTML format (If attach file is html)
        :return: None
        """
        mail_thunder_logger.info(
            f"smtp_create_message_with_attach, message_content{message_content}, "
            f"message_setting_dict: {message_setting_dict}, attach_file: {attach_file}, use_html: {use_html}")
        try:
            message = MIMEMultipart()
            for key, value in message_setting_dict.items():
                message[key] = value
            if use_html:
                mime_part = MIMEText(message_content, "html")
            else:
                mime_part = MIMEText(message_content)
            message.attach(mime_part)
            content_type, encoding = guess_type(attach_file)
            if content_type is None or encoding is not None:
                content_type = "application/octet-stream"
            main_type, sub_type = content_type.split("/", 1)
            if main_type == "text":
                with open(attach_file, "r", encoding="utf-8") as file_read:
                    mime_part = MIMEText(file_read.read(), _subtype=sub_type)
            elif main_type == "image":
                with open(attach_file, "rb") as file_read:
                    mime_part = MIMEImage(file_read.read(), _subtype=sub_type)
            elif main_type == "audio":
                with open(attach_file, "rb") as file_read:
                    mime_part = MIMEAudio(file_read.read(), _subtype=sub_type)
            else:
                with open(attach_file, "rb") as file_read:
                    mime_part = MIMEBase(main_type, sub_type)
                    mime_part.set_payload(file_read.read())
            filename = path.basename(attach_file)
            mime_part.add_header("Content-Disposition", "attachment", filename=filename)
            mime_part.add_header("Content-ID", filename)
            message.attach(mime_part)
            return message
        except Exception as error:
            mail_thunder_logger.error(
                f"smtp_create_message_with_attach, message_content{message_content}, "
                f"message_setting_dict: {message_setting_dict}, attach_file: {attach_file}, "
                f"use_html: {use_html}, failed: {repr(error)}")

    _resolve_credentials = staticmethod(resolve_login_credentials)

    def oauth2_login(self, user: str, access_token: str) -> None:
        """
        Log in with SASL ``XOAUTH2`` (OAuth2) instead of a password.

        :raises smtplib.SMTPAuthenticationError: the server refused the token.
        """
        mail_thunder_logger.info("smtp_oauth2_login")

        def respond(challenge: Optional[bytes] = None) -> str:
            # A challenge after the initial response carries the server's error; an empty reply ends the exchange.
            return xoauth2_string(user, access_token) if challenge is None else ""

        self.ehlo_or_helo_if_needed()
        self.auth("XOAUTH2", respond, initial_response_ok=True)

    def try_to_login_with_env_or_content(self):
        """
        Log in with the OAuth2 settings when there are any, else with the user and password
        (``mail_thunder_content.json`` in the current directory first, then the environment).
        :return: True when logged in, False otherwise (the failure is logged)
        """
        mail_thunder_logger.info("smtp_try_to_login_with_env_or_content")
        self.login_state = False
        try:
            oauth2 = resolve_oauth2_settings()
            if oauth2 is not None:
                self.oauth2_login(oauth2.user, oauth2_token_cache.access_token(oauth2))
            else:
                credentials = self._resolve_credentials()
                if credentials is None:
                    return self.login_state
                self.login(*credentials)
            self.login_state = True
            return self.login_state
        except (smtplib.SMTPAuthenticationError, MailThunderOAuth2Exception) as error:
            mail_thunder_logger.error(f"smtp_try_to_login_with_env_or_content, failed: {repr(error)}")
            return self.login_state
        except OSError as error:
            mail_thunder_logger.error(f"smtp_try_to_login_with_env_or_content, failed: {repr(error)}")
            return self.login_state

    def quit(self):
        """
        Quit service and close connect
        :return: None
        """
        mail_thunder_logger.info("SMTP quit")
        self.login_state = False
        try:
            super().quit()
        except Exception as error:
            mail_thunder_logger.error(f"SMTP quit failed: {repr(error)}")

    def create_message_with_attach_and_send(self, message_content: str, message_setting_dict: dict,
                                            attach_file: str, use_html: bool = False):
        """
        Create new EmailMessage with attach file instance then send EmailMessage instance.
        The file is first checked against ``attachment_policy``; one it refuses is logged and not sent.
        :param message_content: Mail content
        :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
        :param attach_file: File path as str
        :param use_html: Enable HTML format (If attach file is html)
        :return: None
        """
        mail_thunder_logger.info(
            f"smtp_create_message_with_attach_and_send, message_content: {message_content}, "
            f"message_setting_dict: {message_setting_dict}, attach_file:{attach_file}, use_html:{use_html}")
        try:
            if self.attachment_policy is not None:
                validate_attachments([Attachment.from_path(attach_file)], self.attachment_policy)
            self.send_message(
                self.create_message_with_attach(message_content, message_setting_dict, attach_file, use_html))
        except Exception as error:
            mail_thunder_logger.error(
                f"smtp_create_message_with_attach_and_send, message_content: {message_content}, "
                f"message_setting_dict: {message_setting_dict}, attach_file:{attach_file}, "
                f"use_html:{use_html}, failed: {repr(error)}")

    def create_message_and_send(self, message_content: str, message_setting_dict: dict, **kwargs):
        """
        Create new EmailMessage instance then send EmailMessage instance
        :param message_content: Mail content
        :param message_setting_dict: Dict include SUBJECT FROM TO and another EmailMessage Key and Value
        :return: None
        """
        mail_thunder_logger.info(
            f"smtp_create_message_and_send, message_content: {message_content}, "
            f"message_setting_dict: {message_setting_dict}, params:{kwargs}")
        try:
            self.send_message(self.create_message(message_content, message_setting_dict, **kwargs))
        except Exception as error:
            mail_thunder_logger.error(
                f"smtp_create_message_and_send, message_content: {message_content}, "
                f"message_setting_dict: {message_setting_dict}, params:{kwargs}, failed: {repr(error)}")


class SMTPWrapper(SMTPClientMixin, SMTP_SSL):
    """
    SMTP over implicit TLS (``smtplib.SMTP_SSL``); Gmail's ``smtp.gmail.com:465`` by default. The server's
    certificate and host name are verified: ``SMTP_SSL`` checks neither unless it is given a context.
    """

    def __init__(self, host: str = "smtp.gmail.com", port: int = 465):
        super().__init__(host, port, context=verified_client_context())
        self.login_state = False


class SMTPStartTLSWrapper(SMTPClientMixin, SMTP):
    """
    SMTP upgraded to TLS with ``STARTTLS`` before anything else is sent; Microsoft 365's
    ``smtp.office365.com:587`` by default. A server that does not offer ``STARTTLS`` is refused: the connection is
    closed and ``smtplib.SMTPNotSupportedError`` raised, so nothing is ever sent in the clear. The server's
    certificate and host name are verified.
    """

    def __init__(self, host: str = "smtp.office365.com", port: int = 587):
        super().__init__(host, port)
        try:
            self.starttls(context=verified_client_context())
        except (smtplib.SMTPException, OSError):
            self.close()
            raise
        self.login_state = False


def default_smtp_client() -> SMTPClientMixin:
    """
    The client ``smtp_instance`` builds: the server of the provider the OAuth2 settings name (Microsoft over
    ``STARTTLS``), else Gmail over implicit TLS.
    """
    provider = configured_oauth2_provider()
    if provider is None:
        return SMTPWrapper()
    if provider.smtp_starttls:
        return SMTPStartTLSWrapper(provider.smtp_host, provider.smtp_port)
    return SMTPWrapper(provider.smtp_host, provider.smtp_port)


# Connects to the SMTP server on first use, not at import (see utils/lazy_instance).
smtp_instance = LazyInstance(default_smtp_client, "smtp_instance")
