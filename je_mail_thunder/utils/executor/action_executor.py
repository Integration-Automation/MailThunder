import builtins
import types
from inspect import getmembers, isbuiltin

from je_mail_thunder.imap.imap_wrapper import imap_instance
from je_mail_thunder.smtp.smtp_wrapper import smtp_instance
from je_mail_thunder.utils.exception.exception_tags import cant_execute_action_error, executor_list_error, \
    action_is_null_error, add_command_exception
from je_mail_thunder.utils.exception.exceptions import ExecuteActionException, AddCommandException
from je_mail_thunder.utils.json.json_file import read_action_json
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.package_manager.package_manager_class import package_manager
from je_mail_thunder.utils.save_mail_user_content.save_on_env import set_mail_thunder_os_environ, \
    get_mail_thunder_os_environ


class Executor(object):

    def __init__(self):
        self.event_dict: dict = {
            # SMTP
            "MT_smtp_later_init": smtp_instance.smtp_later_init,
            "MT_smtp_create_message_with_attach_and_send": smtp_instance.smtp_create_message_with_attach_and_send,
            "MT_smtp_create_message_and_send": smtp_instance.smtp_create_message_and_send,
            "smtp_quit": smtp_instance.quit,
            # IMAP
            "MT_imap_later_init": imap_instance.imap_later_init,
            "MT_imap_select_mailbox": imap_instance.imap_select_mailbox,
            "MT_imap_search_mailbox": imap_instance.imap_search_mailbox,
            "MT_imap_mail_content_list": imap_instance.imap_mail_content_list,
            "MT_imap_output_all_mail_as_file": imap_instance.imap_output_all_mail_as_file,
            "MT_imap_quit": imap_instance.imap_quit,
            # Content
            "MT_set_mail_thunder_os_environ": set_mail_thunder_os_environ,
            "MT_get_mail_thunder_os_environ": get_mail_thunder_os_environ,
            # Package Manager
            "MT_add_package_to_executor": package_manager.add_package_to_executor,
        }
        # get all builtin function and add to event dict
        for function in getmembers(builtins, isbuiltin):
            self.event_dict.update({str(function[0]): function[1]})

    def _execute_event(self, action: list):
        event = self.event_dict.get(action[0])
        if len(action) == 2:
            if isinstance(action[1], dict):
                return event(**action[1])
            else:
                return event(*action[1])
        elif len(action) == 1:
            return event()
        else:
            raise ExecuteActionException(cant_execute_action_error + " " + str(action))

    def execute_action(self, action_list: [list, dict]) -> dict:
        """
        use to execute all action on action list(action file or program list)
        :param action_list the list include action
        for loop the list and execute action
        """
        if isinstance(action_list, dict):
            action_list: list = action_list.get("auto_control")
            if action_list is None:
                raise ExecuteActionException(executor_list_error)
        execute_record_dict = dict()
        try:
            if len(action_list) == 0 or isinstance(action_list, list) is False:
                raise ExecuteActionException(action_is_null_error)
        except Exception as error:
            mail_thunder_logger.error(
                f"Execute {action_list} failed. {repr(error)}"
            )
        for action in action_list:
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
            print(key, flush=True)
            print(value, flush=True)
        return execute_record_dict

    def execute_files(self, execute_files_list: list) -> list:
        """
        :param execute_files_list: list include execute files path
        :return: every execute detail as list
        """
        execute_detail_list: list = list()
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


def execute_action(action_list: list) -> dict:
    return executor.execute_action(action_list)


def execute_files(execute_files_list: list) -> list:
    return executor.execute_files(execute_files_list)
