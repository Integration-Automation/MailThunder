import smtplib
from email.message import EmailMessage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mimetypes import guess_type
from os import path
from smtplib import SMTP_SSL

from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import read_output_content
from je_mail_thunder.utils.save_mail_user_content.save_on_env import get_mail_thunder_os_environ


class SMTPWrapper(SMTP_SSL):

    def __init__(self, host: str = "smtp.gmail.com", port: int = 465):
        super().__init__(host, port)
        self.login_state = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def smtp_later_init(self):
        """
        Try to log in
        :return: None
        """
        mail_thunder_logger.info("MT_smtp_later_init")
        try:
            self.smtp_try_to_login_with_env_or_content()
        except Exception as error:
            mail_thunder_logger.error(f"smtp_later_init, failed: {error}")

    @staticmethod
    def smtp_create_message(message_content: str, message_setting_dict: dict, **kwargs):
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
    def smtp_create_message_with_attach(message_content: str, message_setting_dict: dict,
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
                file_read = open(attach_file, "r+")
                mime_part = MIMEText(file_read.read(), _subtype=sub_type)
                file_read.close()
            elif main_type == "image":
                file_read = open(attach_file, "rb")
                mime_part = MIMEImage(file_read.read(), _subtype=sub_type)
                file_read.close()
            elif main_type == "audio":
                file_read = open(attach_file, "rb")
                mime_part = MIMEAudio(file_read.read(), _subtype=sub_type)
                file_read.close()
            else:
                file_read = open(attach_file, "rb")
                mime_part = MIMEBase(main_type, sub_type)
                mime_part.set_payload(file_read.read())
                file_read.close()
            filename = path.basename(attach_file)
            mime_part.add_header("Content-Disposition", "attachment", filename=filename)
            mime_part.add_header("Content-ID", "{filename}".format(filename=filename))
            message.attach(mime_part)
            return message
        except Exception as error:
            mail_thunder_logger.info(
                f"smtp_create_message_with_attach, message_content{message_content}, "
                f"message_setting_dict: {message_setting_dict}, attach_file: {attach_file}, "
                f"use_html: {use_html}, failed: {repr(error)}")

    def smtp_try_to_login_with_env_or_content(self):
        """
        Try to find user and password on cwd /mail_thunder_content.json or env var
        :return: None
        """
        mail_thunder_logger.info(f"smtp_try_to_login_with_env_or_content")
        try:
            user_info = read_output_content()
            self.login_state = False
            try:
                if user_info is not None and isinstance(user_info, dict):
                    if user_info.get("user", None) is not None and user_info.get("password", None) is not None:
                        self.login(user_info.get("user"), user_info.get("password"))
                        self.login_state = True
                else:
                    user_info = get_mail_thunder_os_environ()
                    if user_info is not None and isinstance(user_info, dict):
                        if user_info.get("mail_thunder_user", None) is not None and user_info.get(
                                "mail_thunder_user_password", None) is not None:
                            self.login(user_info.get("mail_thunder_user"), user_info.get("mail_thunder_user_password"))
                            self.login_state = True
                return self.login_state
            except smtplib.SMTPAuthenticationError as error:
                mail_thunder_logger.info(f"smtp_try_to_login_with_env_or_content, failed: {repr(error)}")
                return self.login_state
        except Exception as error:
            mail_thunder_logger.info(f"smtp_try_to_login_with_env_or_content, failed: {repr(error)}")

    def quit(self):
        """
        Quit service and close connect
        :return: None
        """
        mail_thunder_logger.info("SMTP quit")
        self.login_state = False

    def smtp_create_message_with_attach_and_send(self, message_content: str, message_setting_dict: dict,
                                                 attach_file: str, use_html: bool = False):
        """
        Create new EmailMessage with attach file instance then send EmailMessage instance
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
            self.send_message(
                self.smtp_create_message_with_attach(message_content, message_setting_dict, attach_file, use_html))
        except Exception as error:
            mail_thunder_logger.info(
                f"smtp_create_message_with_attach_and_send, message_content: {message_content}, "
                f"message_setting_dict: {message_setting_dict}, attach_file:{attach_file}, "
                f"use_html:{use_html}, failed: {repr(error)}")

    def smtp_create_message_and_send(self, message_content: str, message_setting_dict: dict, **kwargs):
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
            self.send_message(self.smtp_create_message(message_content, message_setting_dict, **kwargs))
        except Exception as error:
            mail_thunder_logger.info(
                f"smtp_create_message_and_send, message_content: {message_content}, "
                f"message_setting_dict: {message_setting_dict}, params:{kwargs}, failed: {repr(error)}")


smtp_instance = SMTPWrapper()
