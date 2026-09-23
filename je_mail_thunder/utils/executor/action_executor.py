import builtins
import types
import warnings
from typing import Optional, Union

from je_mail_thunder.imap.imap_wrapper import imap_instance
from je_mail_thunder.smtp.smtp_wrapper import smtp_instance
from je_mail_thunder.utils.lazy_instance.lazy_instance import deferred
from je_mail_thunder.utils.exception.exception_tags import cant_execute_action_error, executor_list_error, \
    action_is_null_error, add_command_exception
from je_mail_thunder.utils.exception.exceptions import ExecuteActionException, AddCommandException
from je_mail_thunder.utils.json.json_file import read_action_json
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

# The key under which an action document holds its action list.
ACTION_LIST_KEY = "mail_thunder"
# The key copied from AutoControl; still read, with a DeprecationWarning, for existing files.
LEGACY_ACTION_LIST_KEY = "auto_control"


def action_list_from_mapping(document: dict) -> Optional[object]:
    """Return the action list of an action document, or ``None`` if it has neither key.

    ``{"mail_thunder": [...]}`` is the current form. ``{"auto_control": [...]}`` still works for
    at least two further releases and raises a ``DeprecationWarning``.
    """
    if ACTION_LIST_KEY in document:
        return document[ACTION_LIST_KEY]
    if LEGACY_ACTION_LIST_KEY in document:
        warnings.warn(
            f'the "{LEGACY_ACTION_LIST_KEY}" key is deprecated; use "{ACTION_LIST_KEY}"',
            DeprecationWarning, stacklevel=3)
        return document[LEGACY_ACTION_LIST_KEY]
    return None
from je_mail_thunder.utils.package_manager.package_manager_class import package_manager
from je_mail_thunder.utils.save_mail_user_content.save_on_env import set_mail_thunder_os_environ, \
    get_mail_thunder_os_environ

# Builtins a JSON action script may call. Anything that can run code, reach
# attributes or namespaces, or touch files and stdin (eval, exec, compile,
# __import__, open, input, getattr, globals, ...) is deliberately left out,
# because action lists also arrive over the socket server.
SAFE_BUILTINS = frozenset({
    "abs", "all", "any", "ascii", "bin", "callable", "chr", "divmod",
    "format", "hash", "hex", "len", "max", "min", "oct", "ord", "pow",
    "print", "repr", "round", "sorted", "sum",
})


class Executor:

    def __init__(self):
        self.event_dict: dict = {
            # SMTP
            "MT_smtp_later_init": deferred(smtp_instance, "later_init"),
            "MT_smtp_create_message_with_attach_and_send": deferred(
                smtp_instance, "create_message_with_attach_and_send"),
            "MT_smtp_create_message_and_send": deferred(smtp_instance, "create_message_and_send"),
            "MT_smtp_quit": deferred(smtp_instance, "quit"),
            # Pre-MT_ name, kept so stored action files keep working.
            "smtp_quit": deferred(smtp_instance, "quit"),
            # IMAP
            "MT_imap_later_init": deferred(imap_instance, "later_init"),
            "MT_imap_select_mailbox": deferred(imap_instance, "select_mailbox"),
            "MT_imap_search_mailbox": deferred(imap_instance, "search_mailbox"),
            "MT_imap_mail_content_list": deferred(imap_instance, "mail_content_list"),
            "MT_imap_output_all_mail_as_file": deferred(imap_instance, "output_all_mail_as_file"),
            "MT_imap_quit": deferred(imap_instance, "quit"),
            # Content
            "MT_set_mail_thunder_os_environ": set_mail_thunder_os_environ,
            "MT_get_mail_thunder_os_environ": get_mail_thunder_os_environ,
            # Package Manager
            "MT_add_package_to_executor": package_manager.add_package_to_executor,
        }
        for name in sorted(SAFE_BUILTINS):
            self.event_dict[name] = getattr(builtins, name)

    def _execute_event(self, action: list):
        event = self.event_dict.get(action[0])
        if event is None:
            raise ExecuteActionException(cant_execute_action_error + " " + str(action))
        if len(action) == 2:
            if isinstance(action[1], dict):
                return event(**action[1])
            else:
                return event(*action[1])
        elif len(action) == 1:
            return event()
        else:
            raise ExecuteActionException(cant_execute_action_error + " " + str(action))

    def execute_action(self, action_list: Union[list, dict]) -> dict:
        """
        use to execute all action on action list(action file or program list)
        :param action_list the list include action
        for loop the list and execute action
        """
        if isinstance(action_list, dict):
            actions = action_list_from_mapping(action_list)
            if actions is None:
                raise ExecuteActionException(executor_list_error)
        else:
            actions = action_list
        execute_record_dict = {}
        if not isinstance(actions, list) or len(actions) == 0:
            mail_thunder_logger.error(
                f"Execute {action_list} failed. {action_is_null_error}"
            )
            return execute_record_dict
        for action in actions:
            try:
                event_response = self._execute_event(action)
                execute_record = "execute: " + str(action)
                mail_thunder_logger.info(
                    f"Execute {action}"
                )
                execute_record_dict.update({execute_record: event_response})
            except Exception as error:
                mail_thunder_logger.error(
                    f"Execute {action} failed. {repr(error)}"
                )
                execute_record = "execute: " + str(action)
                execute_record_dict.update({execute_record: repr(error)})
        for key, value in execute_record_dict.items():
            mail_thunder_logger.info(f"{key} -> {value}")
        return execute_record_dict

    def execute_files(self, execute_files_list: list) -> list:
        """
        :param execute_files_list: list include execute files path
        :return: every execute detail as list
        """
        execute_detail_list: list = []
        for file in execute_files_list:
            execute_detail_list.append(self.execute_action(read_action_json(file)))
        return execute_detail_list


executor = Executor()
package_manager.executor = executor


def add_command_to_executor(command_dict: dict):
    """
    :param command_dict: dict include command we want to add to event_dict
    """
    mail_thunder_logger.info(
        f"Add command to executor {command_dict}"
    )
    for command_name, command in command_dict.items():
        if isinstance(command, (types.MethodType, types.FunctionType)):
            executor.event_dict.update({command_name: command})
        else:
            raise AddCommandException(add_command_exception)


def execute_action(action_list: Union[list, dict]) -> dict:
    return executor.execute_action(action_list)


def execute_files(execute_files_list: list) -> list:
    return executor.execute_files(execute_files_list)
