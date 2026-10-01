"""Action files: je_action_core's JSON reader and writer with MailThunder's exception and messages."""
from typing import Any

from je_action_core import ActionJsonFile, JsonFileMessages, JsonFileSettings

from je_mail_thunder.utils.exception.exception_tags import cant_find_json_error, cant_save_json_error
from je_mail_thunder.utils.exception.exceptions import JsonActionException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

_json_file = ActionJsonFile(JsonFileSettings(
    error=JsonActionException,
    messages=JsonFileMessages(missing=f"{cant_find_json_error}: {{path}}",
                              unreadable=f"{cant_find_json_error}: {{error!r}}",
                              unwritable=f"{cant_save_json_error}: {{error!r}}"),
    log_info=mail_thunder_logger.info,
))


def read_action_json(json_file_path: str) -> Any:
    """
    use to read action file (UTF-8)
    :param json_file_path json file's path to read
    :raises JsonActionException: the file is missing, unreadable or not valid JSON
    """
    return _json_file.read(json_file_path)


def write_action_json(json_save_path: str, action_json: Any) -> None:
    """
    use to save action file (UTF-8, non-ASCII text kept as is)
    :param json_save_path  json save path
    :param action_json the json str include action to write
    :raises JsonActionException: the data cannot be serialised (the file is left as it was) or written
    """
    _json_file.write(json_save_path, action_json)
