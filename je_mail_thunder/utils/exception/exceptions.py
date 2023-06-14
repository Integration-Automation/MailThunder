class MailThunderException(Exception):
    pass


class MailThunderJsonException(MailThunderException):
    pass


class MailThunderContentException(MailThunderException):
    pass


class MailThunderArgparseException(MailThunderException):
    pass


class ExecuteActionException(MailThunderException):
    pass


class AddCommandException(MailThunderException):
    pass


class JsonActionException(MailThunderException):
    pass
