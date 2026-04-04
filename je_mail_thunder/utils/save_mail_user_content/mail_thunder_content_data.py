mail_thunder_content_data_dict = {
    "user": None,
    "password": None
}


def is_need_to_save_content():
    return any(value is not None for value in mail_thunder_content_data_dict.values())
