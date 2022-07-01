mail_thunder_content_data_dict = {
    "user": None,
    "password": None
}


def is_need_to_save_content():
    for value in mail_thunder_content_data_dict.values():
        if value is not None:
            return True
        else:
            return False
