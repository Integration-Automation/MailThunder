from smtplib import SMTP_SSL
from email.message import EmailMessage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mimetypes import guess_type
from os import path
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save import read_output_content


class SMTPWrapper(SMTP_SSL):

    def __init__(self, host: str = "smtp.gmail.com", port: int = 465):
        super().__init__(host, port)
        user_info = read_output_content()
        if user_info is not None and type(user_info) == dict:
            if "user" in user_info.keys() and "password" in user_info.keys():
                self.login(user_info.get("user"), user_info.get("password"))

    @staticmethod
    def create_message(message_content: str, message_setting_dict: dict, **kwargs):
        message = EmailMessage(**kwargs)
        message.set_content(message_content)
        for key, value in message_setting_dict.items():
            message[key] = value
        return message

    @staticmethod
    def create_message_with_attach(message_content: str, message_setting_dict: dict,
                                   attach_file: str, use_html: bool = False):
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

    def create_message_with_attach_and_send(self, message_content: str, message_setting_dict: dict,
                                            attach_file: str, use_html: bool = False):

        self.send_message(self.create_message_with_attach(message_content, message_setting_dict, attach_file, use_html))

    def create_message_and_send(self, message_content: str, message_setting_dict: dict, **kwargs):
        self.send_message(self.create_message(message_content, message_setting_dict, **kwargs))
