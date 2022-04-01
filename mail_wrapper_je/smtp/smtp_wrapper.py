from smtplib import SMTP_SSL


class SMTPWrapper(SMTP_SSL):

    def __init__(self, host: str, port: int):
        super().__init__(host, port)
        self.ehlo()

