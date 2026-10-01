from je_mail_thunder.utils.package_manager.package_manager_class import PackageManager


def test_check_package_existing():
    pm = PackageManager()
    result = pm.check_package("json")
    assert result is not None


def test_check_package_nonexistent():
    pm = PackageManager()
    result = pm.check_package("nonexistent_package_xyz_12345")
    assert result is None


def test_check_package_caches_result():
    pm = PackageManager()
    pm.check_package("json")
    assert "json" in pm.installed_package_dict
    result2 = pm.check_package("json")
    assert result2 is not None


def test_add_package_to_executor_returns_none():
    """``MT_add_package_to_executor``'s record stays ``None`` (je_action_core U-20261001-03)."""

    class FakeExecutor:
        def __init__(self):
            self.event_dict = {}

    pm = PackageManager()
    pm.executor = FakeExecutor()
    assert pm.add_package_to_executor("json") is None
    assert "json_dumps" in pm.executor.event_dict
