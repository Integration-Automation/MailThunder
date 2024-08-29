from je_mail_thunder import SMTPWrapper
from je_mail_thunder import mail_thunder_content_data_dict

smtp_wrapper = SMTPWrapper()
# need have mail_thunder_content.json in current folder
# and need to init SMTPWrapper first

mail_thunder_content_data_dict.update({
    "user": "test_user",
    "password": "test_password",
})

user = mail_thunder_content_data_dict.get("user")

smtp_wrapper.try_to_login_with_env_or_content()

message = smtp_wrapper.create_message("test", {"Subject": "test_subject", "To": user, "From": user})
smtp_wrapper.send_message(message)
smtp_wrapper.quit()
