import json.decoder
import sys
from json import dumps
from json import loads

from je_mail_thunder.utils.exception.exception_tags import mail_thunder_cant_reformat_json_error
from je_mail_thunder.utils.exception.exception_tags import mail_thunder_wrong_json_data_error
from je_mail_thunder.utils.exception.exceptions import MailThunderJsonException


def __process_json(json_string: str, **kwargs):
    try:
        return dumps(loads(json_string), indent=4, sort_keys=True, **kwargs)
    except json.JSONDecodeError as error:
        print(mail_thunder_wrong_json_data_error, file=sys.stderr)
        raise error
    except TypeError:
        try:
            return dumps(json_string, indent=4, sort_keys=True, **kwargs)
        except TypeError:
            raise MailThunderJsonException(mail_thunder_wrong_json_data_error)


def reformat_json(json_string: str, **kwargs):
    try:
        return __process_json(json_string, **kwargs)
    except MailThunderJsonException:
        raise MailThunderJsonException(mail_thunder_cant_reformat_json_error)
