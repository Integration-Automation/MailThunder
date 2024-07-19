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

    def imap_later_init(self):
        """
        Try to log in
        :return: None
        """
        mail_thunder_logger.info("MT_imap_later_init")
        try:
            self.imap_try_to_login_with_env_or_content()
        except Exception as error:
            mail_thunder_logger.error(f"imap_later_init, failed: {repr(error)}")

    def imap_try_to_login_with_env_or_content(self):
        """
        Try to find user and password on cwd /mail_thunder_content.json or env var
        :return: None
        """
        mail_thunder_logger.info("imap_try_to_login_with_env_or_content")
        try:
            user_info = read_output_content()
            if user_info is not None and isinstance(user_info, dict):
                if user_info.get("user", None) is not None and user_info.get("password", None) is not None:
                    self.login(user_info.get("user"), user_info.get("password"))
            else:
                user_info = get_mail_thunder_os_environ()
                if user_info is not None and isinstance(user_info, dict):
                    if user_info.get("mail_thunder_user", None) is not None and user_info.get(
                            "mail_thunder_user_password", None) is not None:
                        self.login(user_info.get("mail_thunder_user"), user_info.get("mail_thunder_user_password"))
        except Exception as error:
            mail_thunder_logger.info(
                f"imap_try_to_login_with_env_or_content, "
                f"failed: {repr(error) + ' ' + mail_thunder_content_login_failed}")

    def imap_select_mailbox(self, mailbox: str = "INBOX", readonly: bool = False):
        """
        :param mailbox: Mailbox we want to select like INBOX
        :param readonly: Readonly or not
        :return: None
        """
        mail_thunder_logger.info(f"imap_select_mailbox, mailbox: {mailbox}, readonly: {readonly}")
        try:
            select_status = self.select(mailbox=mailbox, readonly=readonly)
            return True if select_status[0] == "OK" else False
        except Exception as error:
            mail_thunder_logger.error(
                f"imap_select_mailbox, mailbox: {mailbox}, readonly: {readonly}, failed: {repr(error)}")

    def imap_search_mailbox(self, search_str: [str, list] = "ALL", charset: str = None) -> list:
        """
        Get all mail detail as list
        :param search_str: Search pattern
        :param charset: Charset pattern
        :return: All mail detail as list [mail_response, mail_decode, mail_content]
        """
        mail_thunder_logger.info(f"imap_search_mailbox, search_str: {search_str}, charset: {charset}")
        try:
            response, mail_number_string = self.search(charset, search_str)
            mail_detail_list = list()
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

    def imap_mail_content_list(
            self, search_str: [str, list] = "ALL", charset: str = None) -> List[Dict[str, Union[str, bytes]]]:
        mail_thunder_logger.info(f"imap_mail_content_list, search_str: {search_str}, charset: {charset}")
        """
        Get all mail content as list
        :param search_str: Search pattern
        :param charset: Charset pattern 
        :return: All mail content as list [{"SUBJECT": "mail_subject", "FROM": "mail_from", "TO": "mail_to"}]
        """
        try:
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
        except Exception as error:
            mail_thunder_logger.error(
                f"imap_mail_content_list, search_str: {search_str}, charset: {charset}, failed: {repr(error)}")

    def imap_output_all_mail_as_file(
            self, search_str: [str, list] = "ALL", charset: str = None) -> List[Dict[str, Union[str, bytes]]]:
        mail_thunder_logger.info(f"imap_mail_content_list, search_str: {search_str}, charset: {charset}")
        """
        Get all mail content data and output as file
        :param search_str: Search pattern
        :param charset: Charset pattern 
        :return: All mail content as list [{"SUBJECT": "mail_subject", "FROM": "mail_from", "TO": "mail_to"}]
        """
        try:
            all_mail = self.imap_mail_content_list(search_str=search_str, charset=charset)
            same_name_dict: Dict[str, int] = dict()
            for mail in all_mail:
                if same_name_dict.get((mail.get("SUBJECT"))) is None:
                    same_name_dict.update({mail.get("SUBJECT"): 0})
                else:
                    same_name_dict.update({mail.get("SUBJECT"): same_name_dict.get(mail.get("SUBJECT")) + 1})
                with open(mail.get("SUBJECT") + str(same_name_dict.get(mail.get("SUBJECT"))), "w+") as file:
                    if isinstance(mail.get("BODY"), bytes):
                        file.write(mail.get("BODY").decode("utf-8"))
                    else:
                        file.write(mail.get("BODY"))
            return all_mail
        except Exception as error:
            mail_thunder_logger.error(
                f"imap_mail_content_list, search_str: {search_str}, charset: {charset}, failed: {repr(error)}")

    def imap_quit(self):
        """
        Quit service and close connect
        :return: None
        """
        mail_thunder_logger.info(f"MT_imap_quit")
        try:
            self.close()
            self.logout()
        except Exception as error:
            mail_thunder_logger.error(f"imap_quit, failed: {repr(error)}")


imap_instance = IMAPWrapper()
