import json
from pathlib import Path
from threading import Lock

from je_mail_thunder.utils.json_format.json_process import reformat_json
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_data import mail_thunder_content_data_dict

_CONTENT_FILENAME = "/mail_thunder_content.json"
_lock = Lock()


def read_output_content():
    """
    read the editor content
    """
    with _lock:
        cwd = str(Path.cwd())
        file_path = Path(cwd + _CONTENT_FILENAME)
        if file_path.exists() and file_path.is_file():
            with open(cwd + _CONTENT_FILENAME, "r+") as read_file:
                user_info = json.loads(read_file.read())
                mail_thunder_content_data_dict.update(user_info)
                return user_info
        return None


def write_output_content():
    """
    write the editor content
    """
    with _lock:
        cwd = str(Path.cwd())
        with open(cwd + _CONTENT_FILENAME, "w+") as file_to_write:
            file_to_write.write(reformat_json(json.dumps(mail_thunder_content_data_dict)))
