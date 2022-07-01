from configparser import ConfigParser

from je_mail_thunder import IMAPWrapper

config = ConfigParser()
config.read("../../test_config/config.ini")
print(config.sections())

imap_host = 'imap.gmail.com'
user = config.get("USER", "user")
password = config.get("USER", "password")

imap_wrapper = IMAPWrapper(host=imap_host)
imap_wrapper.login(user, password)
imap_wrapper.select()
mail_message_list = imap_wrapper.search_mailbox()
for mail in mail_message_list:
    print(str(mail[2]))
imap_wrapper.close()
imap_wrapper.logout()
