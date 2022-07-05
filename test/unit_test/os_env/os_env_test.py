from je_mail_thunder import set_mail_thunder_os_environ
from je_mail_thunder import get_mail_thunder_os_environ

print(get_mail_thunder_os_environ())
set_mail_thunder_os_environ("test_user", "test_password")
print(get_mail_thunder_os_environ())
