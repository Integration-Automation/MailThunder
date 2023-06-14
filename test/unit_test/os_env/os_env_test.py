from je_mail_thunder import set_mail_thunder_os_environ
from je_mail_thunder import get_mail_thunder_os_environ
from je_mail_thunder import SMTPWrapper

smtp_wrapper = SMTPWrapper()
print(get_mail_thunder_os_environ())
# no content and os env
print(smtp_wrapper.smtp_try_to_login_with_env_or_content())
# now have os env but will raise SMTPAuthenticationError
set_mail_thunder_os_environ("test_user", "test_password")
print(get_mail_thunder_os_environ())
print(smtp_wrapper.smtp_try_to_login_with_env_or_content())
