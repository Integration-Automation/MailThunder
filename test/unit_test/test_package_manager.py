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
