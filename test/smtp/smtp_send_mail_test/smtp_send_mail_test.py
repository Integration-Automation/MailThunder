import time
from configparser import ConfigParser
from mail_wrapper_je import SMTPWrapper

config = ConfigParser()
config.read("../../test_config/config.ini")
print(config.sections())

user = config.get("USER", "user")
password = config.get("USER", "password")


host = "smtp.gmail.com"
port = 465
smtp_wrapper = SMTPWrapper(host, port)
smtp_wrapper.login(user, password)
smtp_wrapper.quit()
