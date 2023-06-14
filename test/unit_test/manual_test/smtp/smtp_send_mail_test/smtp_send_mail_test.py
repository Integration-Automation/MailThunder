from je_mail_thunder import SMTPWrapper
from je_mail_thunder import mail_thunder_content_data_dict

smtp_wrapper = SMTPWrapper()
# need have mail_thunder_content.json in current folder
# and need to init SMTPWrapper first
user = mail_thunder_content_data_dict.get("user")

message = smtp_wrapper.create_message("test", {"Subject": "test_subject", "To": user, "From": user})
smtp_wrapper.send_message(message)
smtp_wrapper.quit()
