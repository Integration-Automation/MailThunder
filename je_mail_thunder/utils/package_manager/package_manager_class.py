"""
``MT_add_package_to_executor``: je_action_core's package manager with MailThunder's settings (members named
``<package>_<member>``, names must be dotted identifiers, import and attribute errors logged, the package gate on).
"""
from je_action_core import PackageManager as _CorePackageManager
from je_action_core import PackageManagerSettings, is_identifier_path

from je_mail_thunder.utils.exception.exceptions import ExecuteActionException
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

_SETTINGS = PackageManagerSettings(
    name_check=is_identifier_path,
    handled=(AttributeError, ImportError),
    refused=ExecuteActionException,
    log_info=mail_thunder_logger.info,
    log_error=mail_thunder_logger.error,
)


class PackageManager(_CorePackageManager):
    """Imports packages for ``MT_add_package_to_executor`` behind the package gate (see je_action_core)."""

    def __init__(self) -> None:
        super().__init__(_SETTINGS)


package_manager = PackageManager()
