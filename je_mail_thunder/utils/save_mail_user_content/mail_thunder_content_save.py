import json
from pathlib import Path
from threading import Lock

from je_mail_thunder.utils.json_format.json_process import reformat_json
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_data import mail_thunder_content_data_dict

_CONTENT_FILENAME = "/mail_thunder_content.json"
_lock = Lock()


def read_output_content():
    """
    Read ``mail_thunder_content.json`` from the current directory into the content dict and return it.

    :return: the file's JSON object, or ``None`` when there is no file or it holds something other than an
        object (that case is logged; the credential lookup then falls back to the environment).
    """
    with _lock:
        cwd = str(Path.cwd())
        file_path = Path(cwd + _CONTENT_FILENAME)
        if file_path.exists() and file_path.is_file():
            with open(cwd + _CONTENT_FILENAME, "r", encoding="utf-8") as read_file:
                user_info = json.loads(read_file.read())
            if not isinstance(user_info, dict):
                mail_thunder_logger.error(
                    f"read_output_content: {_CONTENT_FILENAME.lstrip('/')} must hold a JSON object, "
                    f"got {type(user_info).__name__}; ignored")
                return None
            mail_thunder_content_data_dict.update(user_info)
            return user_info
        return None


def write_output_content():
    """
    write the editor content
    """
    with _lock:
        cwd = str(Path.cwd())
        with open(cwd + _CONTENT_FILENAME, "w", encoding="utf-8") as file_to_write:
            file_to_write.write(reformat_json(json.dumps(mail_thunder_content_data_dict)))
