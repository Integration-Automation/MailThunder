from os import environ


def set_mail_thunder_os_environ(mail_thunder_user: str, mail_thunder_user_password: str):
    environ.update({"mail_thunder_user": mail_thunder_user})
    environ.update({"mail_thunder_user_password": mail_thunder_user_password})


def get_mail_thunder_os_environ():
    return {
        "mail_thunder_user": environ.get("mail_thunder_user", None),
        "mail_thunder_user_password": environ.get("mail_thunder_user_password", None)
    }


