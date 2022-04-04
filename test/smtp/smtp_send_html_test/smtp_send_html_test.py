from configparser import ConfigParser
from mail_wrapper_je import SMTPWrapper

config = ConfigParser()
config.read("../../test_config/config.ini")
print(config.sections())

user = config.get("USER", "user")
password = config.get("USER", "password")
another_use = config.get("USER", "another_user")

host = "smtp.gmail.com"
port = 465
smtp_wrapper = SMTPWrapper(host, port)
smtp_wrapper.login(user, password)
with open("autocontorl.html", "r+") as file:
    html_string = file.read()
message = smtp_wrapper.create_message_with_attach(html_string,
    {"Subject": "test_subject", "To": user, "From": user},
    "autocontorl.html", use_html=True)
smtp_wrapper.sendmail(user,  another_use, message.as_string())
smtp_wrapper.quit()
