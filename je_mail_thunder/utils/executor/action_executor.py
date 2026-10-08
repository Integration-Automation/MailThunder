"""
The ``MT_*`` action executor: je_action_core's executor with MailThunder's commands, document key and messages.
"""
from typing import Optional, Union

from je_action_core import (
    SAFE_BUILTINS,
    ActionExecutor,
    ActionListRules,
    CommandPolicy,
    CommandRegistry,
    EmptyListPolicy,
    ExecutorSettings,
    LegacyActionParser,
    LoggingReporter,
    safe_builtin_commands,
)

from je_mail_thunder.core.actions import (
    mail_create_draft,
    mail_get_message,
    mail_get_messages,
    mail_render_template,
    mail_send,
)
from je_mail_thunder.core.mail import mail_instance
from je_mail_thunder.imap.imap_wrapper import imap_instance
from je_mail_thunder.smtp.smtp_wrapper import smtp_instance
from je_mail_thunder.utils.exception.exception_tags import (
    action_is_null_error,
    add_command_exception,
    cant_execute_action_error,
    executor_list_error,
)
from je_mail_thunder.utils.exception.exceptions import AddCommandException, ExecuteActionException
from je_mail_thunder.utils.json.json_file import read_action_json
from je_mail_thunder.utils.lazy_instance.lazy_instance import deferred
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
from je_mail_thunder.utils.package_manager.package_manager_class import package_manager
from je_mail_thunder.utils.save_mail_user_content.save_on_env import (
    get_mail_thunder_os_environ,
    set_mail_thunder_os_environ,
)

# The key under which an action document holds its action list.
ACTION_LIST_KEY = "mail_thunder"
# The key copied from AutoControl; still read, with a DeprecationWarning, for existing files.
LEGACY_ACTION_LIST_KEY = "auto_control"
_RULES = ActionListRules(ACTION_LIST_KEY, legacy_keys=(LEGACY_ACTION_LIST_KEY,), error=ExecuteActionException,
                         missing_message=executor_list_error, empty=EmptyListPolicy.RETURN_EMPTY)
# warnings.warn -> from_document -> action_list_from_mapping -> its caller -> that caller's caller
_LEGACY_KEY_STACKLEVEL = 3


def action_list_from_mapping(document: dict) -> Optional[object]:
    """Return the action list of an action document, or ``None`` if it has neither key.

    ``{"mail_thunder": [...]}`` is the current form. ``{"auto_control": [...]}`` still works for
    at least two further releases and raises a ``DeprecationWarning``.
    """
    return _RULES.from_document(document, stacklevel=_LEGACY_KEY_STACKLEVEL)


# Builtins a JSON action script may call: je_action_core's SAFE_BUILTINS (the workspace's shared allowlist),
# because action lists also arrive over the socket server. The name stays exported here.
__all__ = ["ACTION_LIST_KEY", "LEGACY_ACTION_LIST_KEY", "SAFE_BUILTINS", "Executor", "action_list_from_mapping",
           "add_command_to_executor", "execute_action", "execute_files", "executor"]
_SETTINGS = ExecutorSettings(
    rules=_RULES,
    parser=LegacyActionParser(error=ExecuteActionException, message=cant_execute_action_error),
    # An empty or non-list action list runs nothing and is logged with action_is_null_error.
    reporter=LoggingReporter(mail_thunder_logger, empty_message=action_is_null_error),
    read_json=read_action_json,
)


class Executor(ActionExecutor):
    """The ``MT_*`` commands and the safe builtins over je_action_core's executor."""

    def __init__(self) -> None:
        super().__init__(_SETTINGS, CommandRegistry(
            policy=CommandPolicy.FUNCTIONS_ONLY, rejection=lambda _name: AddCommandException(add_command_exception)))
        self.event_dict = {
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
            # Mail: the provider-agnostic API, on mail_instance (it connects on first use)
            "MT_mail_send": mail_send,
            "MT_mail_render_template": mail_render_template,
            "MT_mail_create_draft": mail_create_draft,
            "MT_mail_get_messages": mail_get_messages,
            "MT_mail_get_message": mail_get_message,
            "MT_mail_delete_message": mail_instance.delete_message,
            "MT_mail_close": mail_instance.close,
            # Content
            "MT_set_mail_thunder_os_environ": set_mail_thunder_os_environ,
            "MT_get_mail_thunder_os_environ": get_mail_thunder_os_environ,
            # Package Manager
            "MT_add_package_to_executor": package_manager.add_package_to_executor,
        }
        self.event_dict.update(safe_builtin_commands())

    @staticmethod
    def set_allow_arbitrary_packages(enabled: bool) -> None:
        """
        Allow (True) or refuse (False) ``MT_add_package_to_executor`` for packages outside the allowlist.
        Python only, never an action command, so an action file cannot open its own gate. Until it is
        called, any package loads with a ``DeprecationWarning``.
        """
        package_manager.set_allow_arbitrary_packages(enabled)

    @staticmethod
    def allow_packages(*packages: str) -> None:
        """Add packages, and their submodules, to the allowlist of ``MT_add_package_to_executor``."""
        package_manager.allow_packages(*packages)


executor = Executor()
package_manager.executor = executor


def add_command_to_executor(command_dict: dict) -> None:
    """
    Add functions or methods to the executor.

    :param command_dict: name -> function or method
    :raises AddCommandException: a value is neither (the ones before it stay added)
    """
    mail_thunder_logger.info(f"Add command to executor {command_dict}")
    executor.add_command_to_executor(command_dict)


def execute_action(action_list: Union[list, dict]) -> dict:
    """Run an action list (or a ``{"mail_thunder": [...]}`` document) and return the records."""
    return executor.execute_action(action_list)


def execute_files(execute_files_list: list) -> list:
    """Run every action file in order and return their records."""
    return executor.execute_files(execute_files_list)
