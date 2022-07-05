import sys
from imaplib import IMAP4_SSL
from email import policy
from email import message_from_bytes
from email.header import decode_header

from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import read_output_content
from je_mail_thunder.utils.exception.exception_tags import mail_thunder_content_login_failed


class IMAPWrapper(IMAP4_SSL):

    def __init__(self, host: str = 'imap.gmail.com'):
        super().__init__(host)
        user_info = read_output_content()
        try:
            if user_info is not None and type(user_info) == dict:
                if "user" in user_info.keys() and "password" in user_info.keys():
                    if user_info.get("user") is not None and user_info.get("password") is not None:
                        self.login(user_info.get("user"), user_info.get("password"))
        except Exception as error:
            print(repr(error) + " " + mail_thunder_content_login_failed, file=sys.stderr)

    def search_mailbox(self, search_str: [str, list] = "ALL", charset: str = None):
        response, mail_number_string = self.search(charset, search_str)
        mail_detail_list = list()
        for num_of_mail in mail_number_string[0].split():
            response, mail_data = self.fetch(num_of_mail, "(RFC822)")
            # [0][1] is message data [0][0] is message decode like RFC822 {565}
            message = message_from_bytes(mail_data[0][1], policy=policy.default)
            mail_detail_list.append([response, mail_data[0][0], message])
        return mail_detail_list

    def mail_content_list(self, search_str: [str, list] = "ALL", charset: str = None):
        mail_list = self.search_mailbox(search_str, charset)
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
                    body = part.get_payload(decode=True)
            else:
                body = mail.get_payload(decode=True)

            body = str(decode_header(str(body))[0][0])
            mail_content_dict.update({"BODY": body})
            mail_content_list.append(mail_content_dict)
            mail_content_dict = dict()
        return mail_content_list

