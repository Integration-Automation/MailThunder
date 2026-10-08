"""Setup shared by every unit test."""
import pytest

from je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_data import mail_thunder_content_data_dict


@pytest.fixture(autouse=True)
def restore_content_data():
    """
    ``read_output_content()`` copies the content file it finds into a module-level dict. It is put back after
    each test, so a test that reads a content file cannot change what a later test sees.
    """
    before = dict(mail_thunder_content_data_dict)
    yield
    mail_thunder_content_data_dict.clear()
    mail_thunder_content_data_dict.update(before)
