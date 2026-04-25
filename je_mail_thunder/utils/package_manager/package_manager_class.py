from importlib import import_module
from importlib.util import find_spec
from inspect import getmembers, isfunction, isbuiltin, isclass

from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger


def _is_safe_module_name(package: str) -> bool:
    if not isinstance(package, str) or not package:
        return False
    return all(part.isidentifier() for part in package.split("."))


class PackageManager:

    def __init__(self):
        self.installed_package_dict = {}
        self.executor = None
        self.callback_executor = None

    def check_package(self, package: str):
        """
        :param package: package to check exists or not
        :return: package if find else None
        """
        if not _is_safe_module_name(package):
            mail_thunder_logger.error(
                f"check_package: rejected non-conforming module name: {package!r}")
            return None
        if self.installed_package_dict.get(package, None) is None:
            found_spec = find_spec(package)
            if found_spec is not None and _is_safe_module_name(found_spec.name):
                try:
                    installed_package = import_module(found_spec.name)
                    self.installed_package_dict.update(
                        {found_spec.name: installed_package})
                except ModuleNotFoundError as error:
                    mail_thunder_logger.error(repr(error))
        return self.installed_package_dict.get(package, None)

    def add_package_to_executor(self, package):
        """
        :param package: package's function will add to executor
        """
        mail_thunder_logger.info(f"add_package_to_executor, package: {package}")
        self.add_package_to_target(
            package=package,
            target=self.executor
        )

    def add_package_to_callback_executor(self, package):
        """
        :param package: package's function will add to callback_executor
        """
        mail_thunder_logger.info(f"add_package_to_callback_executor, package: {package}")
        self.add_package_to_target(
            package=package,
            target=self.callback_executor
        )

    def get_member(self, package, predicate, target):
        """
        :param package: package we want to get member
        :param predicate: predicate
        :param target: which event_dict will be added
        """
        installed_package = self.check_package(package)
        if installed_package is not None and target is not None:
            for member in getmembers(installed_package, predicate):
                target.event_dict.update(
                    {str(package) + "_" + str(member[0]): member[1]})
        elif installed_package is None:
            mail_thunder_logger.error(
                repr(ModuleNotFoundError(f"Can't find package {package}")))
        else:
            mail_thunder_logger.error(f"Executor error {self.executor}")

    def add_package_to_target(self, package, target):
        """
        :param package: package we want to get member
        :param target: which event_dict will be added
        """
        try:
            self.get_member(
                package=package,
                predicate=isfunction,
                target=target
            )
            self.get_member(
                package=package,
                predicate=isbuiltin,
                target=target
            )
            self.get_member(
                package=package,
                predicate=isclass,
                target=target
            )
        except (AttributeError, ImportError) as error:
            mail_thunder_logger.error(repr(error))


package_manager = PackageManager()
