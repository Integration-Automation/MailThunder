from je_mail_thunder import SMTPWrapper
from je_mail_thunder import mail_thunder_content_data_dict

smtp_wrapper = SMTPWrapper()
smtp_wrapper.later_init()
user = mail_thunder_content_data_dict.get("user")
with open("test.html", "r+") as file:
    html_string = file.read()
message = smtp_wrapper.create_message_with_attach(
    html_string,
    {"Subject": "test_subject", "To": user, "From": user},
    "test.html", use_html=True)

smtp_wrapper.send_message(message)
smtp_wrapper.quit()
