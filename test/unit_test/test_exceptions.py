import pytest

from je_mail_thunder.utils.exception.exceptions import (
    MailThunderException,
    MailThunderJsonException,
    MailThunderContentException,
    MailThunderArgparseException,
    ExecuteActionException,
    AddCommandException,
    JsonActionException,
)


def test_base_exception_hierarchy():
    assert issubclass(MailThunderJsonException, MailThunderException)
    assert issubclass(MailThunderContentException, MailThunderException)
    assert issubclass(MailThunderArgparseException, MailThunderException)
    assert issubclass(ExecuteActionException, MailThunderException)
    assert issubclass(AddCommandException, MailThunderException)
    assert issubclass(JsonActionException, MailThunderException)


def test_base_exception_is_exception():
    assert issubclass(MailThunderException, Exception)


def test_exceptions_carry_message():
    msg = "test error message"
    for exc_class in [
        MailThunderException,
        MailThunderJsonException,
        MailThunderContentException,
        MailThunderArgparseException,
        ExecuteActionException,
        AddCommandException,
        JsonActionException,
    ]:
        exc = exc_class(msg)
        assert str(exc) == msg
        with pytest.raises(exc_class):
            raise exc
