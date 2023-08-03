import json
import os
from pathlib import Path
from threading import Lock

from je_mail_thunder.utils.exception.exceptions import MailThunderContentException
from je_mail_thunder.utils.json_format.json_process import reformat_json
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_data import mail_thunder_content_data_dict


def read_output_content():
    """
    read the editor content
    """
    lock = Lock()
    try:
        lock.acquire()
        cwd = str(Path.cwd())
        file_path = Path(cwd + "/mail_thunder_content.json")
        if file_path.exists() and file_path.is_file():
            with open(cwd + "/mail_thunder_content.json", "r+") as read_file:
                user_info = json.loads(read_file.read())
                mail_thunder_content_data_dict.update(user_info)
                return user_info
    except MailThunderContentException:
        raise MailThunderContentException
    finally:
        lock.release()


def write_output_content():
    """
    write the editor content
    """
    lock = Lock()
    try:
        lock.acquire()
        cwd = str(Path.cwd())
        with open(cwd + "/mail_thunder_content.json", "w+") as file_to_write:
            file_to_write.write(reformat_json(json.dumps(mail_thunder_content_data_dict)))
    except MailThunderContentException:
        raise MailThunderContentException
    finally:
        lock.release()
