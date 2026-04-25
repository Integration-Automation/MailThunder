import os
import re
from email import message_from_bytes
from email import policy
from email.header import decode_header
from imaplib import IMAP4_SSL
from typing import List, Dict, Union

from je_mail_thunder.utils.exception.exception_tags import mail_thunder_content_login_failed
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import read_output_content
from je_mail_thunder.utils.save_mail_user_content.save_on_env import get_mail_thunder_os_environ


class IMAPWrapper(IMAP4_SSL):

    def __init__(self, host: str = 'imap.gmail.com'):
        super().__init__(host)

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

    @staticmethod
    def _resolve_credentials():
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

    def try_to_login_with_env_or_content(self):
        """
        Try to find user and password on cwd /mail_thunder_content.json or env var
        :return: None
        """
        mail_thunder_logger.info("imap_try_to_login_with_env_or_content")
        try:
            credentials = self._resolve_credentials()
            if credentials is not None:
                self.login(*credentials)
        except OSError as error:
            mail_thunder_logger.info(
                f"imap_try_to_login_with_env_or_content, "
                f"failed: {repr(error) + ' ' + mail_thunder_content_login_failed}")

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
        Strips directory components and any separator / traversal token.
        Falls back to "mail" when the sanitized result is empty.
        """
        if subject is None:
            return "mail"
        name = os.path.basename(str(subject))
        name = name.replace("\x00", "")
        name = re.sub(r"[\\/\r\n\t]", "_", name)
        while ".." in name:
            name = name.replace("..", "_")
        name = name.strip(" .")
        return name if name else "mail"

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
                with open(target_path, "w+") as file:
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


try:
    imap_instance = IMAPWrapper()
except OSError as _imap_init_error:
    mail_thunder_logger.error(f"imap_instance init failed: {repr(_imap_init_error)}")
    imap_instance = None
