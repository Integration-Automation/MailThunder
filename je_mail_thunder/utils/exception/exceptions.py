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


class MailThunderOAuth2Exception(MailThunderException):
    """OAuth2 settings are invalid, or the token endpoint refused or could not be reached."""
