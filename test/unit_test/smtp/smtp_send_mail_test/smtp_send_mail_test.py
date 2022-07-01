from configparser import ConfigParser
from je_mail_thunder import SMTPWrapper

config = ConfigParser()
config.read("../../test_config/config.ini")
print(config.sections())

user = config.get("USER", "user")
password = config.get("USER", "password")


host = "smtp.gmail.com"
port = 465
smtp_wrapper = SMTPWrapper(host, port)
smtp_wrapper.login(user, password)
message = smtp_wrapper.create_message("test", {"Subject": "test_subject", "To": user, "From": user})
smtp_wrapper.send_message(message)
smtp_wrapper.quit()
