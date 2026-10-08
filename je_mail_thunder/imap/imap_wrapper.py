import os
from email import message_from_bytes
from email import policy
from email.header import decode_header
from imaplib import IMAP4_SSL
from typing import Dict, List, Union

from je_mail_thunder.attachments.mime import safe_filename
from je_mail_thunder.utils.exception.exception_tags import mail_thunder_content_login_failed
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


class IMAPWrapper(IMAP4_SSL):
    """
    IMAP over TLS (``imaplib.IMAP4_SSL``); Gmail's ``imap.gmail.com`` by default. The server's certificate and
    host name are verified: ``IMAP4_SSL`` checks neither unless it is given a context.
    """

    def __init__(self, host: str = 'imap.gmail.com'):
        super().__init__(host, ssl_context=verified_client_context())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self.logout()

    def later_init(self):
        """
        Try to log in
        :return: None
        """
        mail_thunder_logger.info("MT_imap_later_init")
        try:
            self.try_to_login_with_env_or_content()
        except Exception as error:
            mail_thunder_logger.error(f"imap_later_init, failed: {repr(error)}")

    _resolve_credentials = staticmethod(resolve_login_credentials)

    def oauth2_login(self, user: str, access_token: str):
        """
        Log in with SASL ``XOAUTH2`` (OAuth2) instead of a password.

        :raises imaplib.IMAP4.error: the server refused the token.
        """
        mail_thunder_logger.info("imap_oauth2_login")
        # The first continuation gets the token; a second one carries the server's error, and the empty
        # answer to it ends the exchange.
        answers = iter([xoauth2_string(user, access_token).encode("utf-8")])
        return self.authenticate("XOAUTH2", lambda _challenge: next(answers, b""))

    def try_to_login_with_env_or_content(self):
        """
        Log in with the OAuth2 settings when there are any, else with the user and password
        (``mail_thunder_content.json`` in the current directory first, then the environment).
        A refused login raises ``imaplib.IMAP4.error``; network and OAuth2 setting errors are logged.
        :return: None
        """
        mail_thunder_logger.info("imap_try_to_login_with_env_or_content")
        try:
            oauth2 = resolve_oauth2_settings()
            if oauth2 is not None:
                self.oauth2_login(oauth2.user, oauth2_token_cache.access_token(oauth2))
                return
            credentials = self._resolve_credentials()
            if credentials is not None:
                self.login(*credentials)
        except OSError as error:
            mail_thunder_logger.info(
                f"imap_try_to_login_with_env_or_content, "
                f"failed: {repr(error) + ' ' + mail_thunder_content_login_failed}")
        except MailThunderOAuth2Exception as error:
            mail_thunder_logger.error(f"imap_try_to_login_with_env_or_content, failed: {repr(error)}")

    def select_mailbox(self, mailbox: str = "INBOX", readonly: bool = False):
        """
        :param mailbox: Mailbox we want to select like INBOX
        :param readonly: Readonly or not
        :return: None
        """
        mail_thunder_logger.info(f"imap_select_mailbox, mailbox: {mailbox}, readonly: {readonly}")
        try:
            select_status = self.select(mailbox=mailbox, readonly=readonly)
            return select_status[0] == "OK"
        except Exception as error:
            mail_thunder_logger.error(
                f"imap_select_mailbox, mailbox: {mailbox}, readonly: {readonly}, failed: {repr(error)}")

    def search_mailbox(self, search_str: [str, list] = "ALL", charset: str = None) -> list:
        """
        Get all mail detail as list
        :param search_str: Search pattern
        :param charset: Charset pattern
        :return: All mail detail as list [mail_response, mail_decode, mail_content]
        """
        mail_thunder_logger.info(f"imap_search_mailbox, search_str: {search_str}, charset: {charset}")
        try:
            response, mail_number_string = self.search(charset, search_str)
            mail_detail_list = []
            for num_of_mail in mail_number_string[0].split():
                response, mail_data = self.fetch(num_of_mail, "(RFC822)")
                mail_data: List[List]
                # [0][1] is message data [0][0] is message decode like RFC822 {565}
                message = message_from_bytes(mail_data[0][1], policy=policy.default)
                mail_detail_list.append([response, mail_data[0][0], message])
            return mail_detail_list
        except Exception as error:
            mail_thunder_logger.error(
                f"imap_search_mailbox, search_str: {search_str}, charset: {charset}, failed: {repr(error)}")

    def mail_content_list(
            self, search_str: [str, list] = "ALL", charset: str = None) -> List[Dict[str, Union[str, bytes]]]:
        """
        Get all mail content as list
        :param search_str: Search pattern
        :param charset: Charset pattern
        :return: All mail content as list [{"SUBJECT": "mail_subject", "FROM": "mail_from", "TO": "mail_to"}]
        """
        mail_thunder_logger.info(f"imap_mail_content_list, search_str: {search_str}, charset: {charset}")
        try:
            mail_list = self.search_mailbox(search_str, charset)
            mail_content_dict = {}
            mail_content_list = []
            for mail_data in mail_list:
                mail = mail_data[2]
                mail_content_dict.update({"SUBJECT": mail.get("Subject")})
                mail_content_dict.update({"FROM": mail.get("FROM")})
                mail_content_dict.update({"TO": mail.get("TO")})
                body = ""
                if mail.is_multipart():
                    for part in mail.get_payload():
                        body = part.get_payload(decode=False)
                else:
                    body = mail.get_payload(decode=False)
                body = str(decode_header(str(body))[0][0])
                mail_content_dict.update({"BODY": body})
                mail_content_list.append(mail_content_dict)
                mail_content_dict = {}
            return mail_content_list
        except Exception as error:
            mail_thunder_logger.error(
                f"imap_mail_content_list, search_str: {search_str}, charset: {charset}, failed: {repr(error)}")

    @staticmethod
    def _sanitize_subject_as_filename(subject) -> str:
        """
        Derive a safe filename from a mail SUBJECT header.
        Strips directory components, traversal tokens, control characters and what Windows refuses in a
        file name (a ``:`` there sends the content to an alternate data stream and leaves the file empty).
        Falls back to "mail" when the sanitized result is empty.
        """
        return safe_filename(subject, fallback="mail")

    def output_all_mail_as_file(
            self, search_str: [str, list] = "ALL", charset: str = None) -> List[Dict[str, Union[str, bytes]]]:
        """
        Get all mail content data and output as file
        :param search_str: Search pattern
        :param charset: Charset pattern
        :return: All mail content as list [{"SUBJECT": "mail_subject", "FROM": "mail_from", "TO": "mail_to"}]
        """
        mail_thunder_logger.info(f"imap_output_all_mail_as_file, search_str: {search_str}, charset: {charset}")
        try:
            all_mail = self.mail_content_list(search_str=search_str, charset=charset)
            same_name_dict: Dict[str, int] = {}
            cwd = os.path.abspath(os.getcwd())
            for mail in all_mail:
                safe_name = self._sanitize_subject_as_filename(mail.get("SUBJECT"))
                count = same_name_dict.get(safe_name, -1) + 1
                same_name_dict[safe_name] = count
                target_path = os.path.abspath(os.path.join(cwd, safe_name + str(count)))
                if os.path.commonpath([cwd, target_path]) != cwd:
                    mail_thunder_logger.error(
                        f"imap_output_all_mail_as_file, rejected path traversal: {target_path}")
                    continue
                with open(target_path, "w", encoding="utf-8") as file:
                    if isinstance(mail.get("BODY"), bytes):
                        file.write(mail.get("BODY").decode("utf-8"))
                    else:
                        file.write(mail.get("BODY"))
            return all_mail
        except Exception as error:
            mail_thunder_logger.error(
                f"imap_output_all_mail_as_file, search_str: {search_str}, charset: {charset}, failed: {repr(error)}")

    def quit(self):
        """
        Quit service and close connect
        :return: None
        """
        mail_thunder_logger.info("MT_imap_quit")
        try:
            self.close()
            self.logout()
        except Exception as error:
            mail_thunder_logger.error(f"imap_quit, failed: {repr(error)}")


def default_imap_client() -> IMAPWrapper:
    """The client ``imap_instance`` builds: the IMAP server of the provider the OAuth2 settings name, else Gmail."""
    provider = configured_oauth2_provider()
    return IMAPWrapper() if provider is None else IMAPWrapper(provider.imap_host)


# Connects to the IMAP server on first use, not at import (see utils/lazy_instance).
imap_instance = LazyInstance(default_imap_client, "imap_instance")
