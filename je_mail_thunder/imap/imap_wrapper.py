import sys
from email import message_from_bytes
from email import policy
from email.header import decode_header
from imaplib import IMAP4_SSL
from typing import List, Dict, Union

from je_mail_thunder import get_mail_thunder_os_environ
from je_mail_thunder.utils.exception.exception_tags import mail_thunder_content_login_failed
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import read_output_content


class IMAPWrapper(IMAP4_SSL):

    def __init__(self, host: str = 'imap.gmail.com'):
        super().__init__(host)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self.logout()

    def imap_later_init(self):
        mail_thunder_logger.info(f"imap_later_init")
        self.imap_try_to_login_with_env_or_content()

    def imap_try_to_login_with_env_or_content(self):
        mail_thunder_logger.info(f"imap_try_to_login_with_env_or_content")
        user_info = read_output_content()
        try:
            if user_info is not None and type(user_info) == dict:
                if user_info.get("user", None) is not None and user_info.get("password", None) is not None:
                    self.login(user_info.get("user"), user_info.get("password"))
            else:
                user_info = get_mail_thunder_os_environ()
                if user_info is not None and type(user_info) == dict:
                    if user_info.get("mail_thunder_user", None) is not None and user_info.get(
                            "mail_thunder_user_password", None) is not None:
                        self.login(user_info.get("mail_thunder_user"), user_info.get("mail_thunder_user_password"))
            return self.login_state
        except Exception as error:
            mail_thunder_logger.info(
                f"imap_try_to_login_with_env_or_content, "
                f"failed: {repr(error) + ' ' + mail_thunder_content_login_failed}")
            return self.login_state

    def imap_select_mailbox(self, mailbox: str = "INBOX", readonly: bool = False):
        mail_thunder_logger.info(f"imap_select_mailbox, mailbox: {mailbox}, readonly: {readonly}")
        select_status = self.select(mailbox=mailbox, readonly=readonly)
        return True if select_status[0] == "OK" else False

    def imap_search_mailbox(self, search_str: [str, list] = "ALL", charset: str = None) -> list:
        mail_thunder_logger.info(f"imap_search_mailbox, search_str: {search_str}, charset: {charset}")
        response, mail_number_string = self.search(charset, search_str)
        mail_detail_list = list()
        for num_of_mail in mail_number_string[0].split():
            response, mail_data = self.fetch(num_of_mail, "(RFC822)")
            # [0][1] is message data [0][0] is message decode like RFC822 {565}
            message = message_from_bytes(mail_data[0][1], policy=policy.default)
            mail_detail_list.append([response, mail_data[0][0], message])
        return mail_detail_list

    def imap_mail_content_list(
            self, search_str: [str, list] = "ALL", charset: str = None) -> List[Dict[str, Union[str, bytes]]]:
        mail_thunder_logger.info(f"imap_mail_content_list, search_str: {search_str}, charset: {charset}")
        mail_list = self.imap_search_mailbox(search_str, charset)
        mail_content_dict = dict()
        mail_content_list = list()
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
            mail_content_dict = dict()
        return mail_content_list

    def imap_output_all_mail_as_file(
            self, search_str: [str, list] = "ALL", charset: str = None) -> List[Dict[str, Union[str, bytes]]]:
        mail_thunder_logger.info(f"imap_mail_content_list, search_str: {search_str}, charset: {charset}")
        all_mail = self.imap_mail_content_list(search_str=search_str, charset=charset)
        for mail in all_mail:
            with open(mail.get("SUBJECT"), "w+") as file:
                if isinstance(mail.get("BODY"), bytes):
                    file.write(mail.get("BODY").decode("utf-8"))
                else:
                    file.write(mail.get("BODY"))
        return all_mail

    def imap_quit(self):
        mail_thunder_logger.info(f"imap_quit")
        self.close()
        self.logout()


imap_instance = IMAPWrapper()
