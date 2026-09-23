import json
from pathlib import Path
from threading import Lock

from je_mail_thunder.utils.exception.exception_tags import cant_find_json_error, cant_save_json_error
from je_mail_thunder.utils.exception.exceptions import JsonActionException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

_lock = Lock()


def read_action_json(json_file_path: str) -> list:
    """
    use to read action file (UTF-8)
    :param json_file_path json file's path to read
    :raises JsonActionException: the file is missing, unreadable or not valid JSON
    """
    file_path = Path(json_file_path)
    if not file_path.is_file():
        raise JsonActionException(f"{cant_find_json_error}: {json_file_path}")
    with _lock:
        try:
            mail_thunder_logger.info(f"Read json file {json_file_path}")
            with open(file_path, encoding="utf-8") as read_file:
                return json.loads(read_file.read())
        except (OSError, ValueError) as error:
            raise JsonActionException(cant_find_json_error + f": {repr(error)}") from error


def write_action_json(json_save_path: str, action_json: list) -> None:
    """
    use to save action file (UTF-8, non-ASCII text kept as is)
    :param json_save_path  json save path
    :param action_json the json str include action to write
    """
    with _lock:
        try:
            mail_thunder_logger.info(
                f"Write {action_json} as file {json_save_path}"
            )
            content = json.dumps(action_json, indent=4, ensure_ascii=False)
            with open(json_save_path, "w", encoding="utf-8") as file_to_write:
                file_to_write.write(content)
        except (OSError, TypeError, ValueError) as error:
            raise JsonActionException(cant_save_json_error + f": {repr(error)}") from error
