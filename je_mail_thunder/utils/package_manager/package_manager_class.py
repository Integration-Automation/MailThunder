"""
``MT_add_package_to_executor``: je_action_core's package manager with MailThunder's settings (members named
``<package>_<member>``, names must be dotted identifiers, import and attribute errors logged).
"""
from je_action_core import PackageGate, PackageManagerSettings, is_identifier_path
from je_action_core import PackageManager as _CorePackageManager

from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

_SETTINGS = PackageManagerSettings(
    name_check=is_identifier_path,
    handled=(AttributeError, ImportError),
    # The package gate (workspace X-12) is not switched on here yet.
    gate=PackageGate.OFF,
    log_info=mail_thunder_logger.info,
    log_error=mail_thunder_logger.error,
)


class PackageManager(_CorePackageManager):
    """Imports packages for ``MT_add_package_to_executor`` (see je_action_core)."""

    def __init__(self) -> None:
        super().__init__(_SETTINGS)


package_manager = PackageManager()
