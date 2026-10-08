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


class MailThunderAttachmentException(MailThunderException):
    """An attachment cannot be read or breaks the attachment policy."""


class AttachmentNotFound(MailThunderAttachmentException):
    """The file to attach does not exist or is not a regular file."""

    def __init__(self, path: str) -> None:
        super().__init__(f"attachment not found: {path!r}")
        self.path = path


class AttachmentTooLarge(MailThunderAttachmentException):
    """One attachment is larger than the policy's per-file limit."""

    def __init__(self, filename: str, size: int, limit: int) -> None:
        super().__init__(f"attachment {filename!r} is {size} bytes, over the limit of {limit}")
        self.filename = filename
        self.size = size
        self.limit = limit


class AttachmentTypeNotAllowed(MailThunderAttachmentException):
    """The attachment's extension or MIME type is not one the policy allows."""

    def __init__(self, filename: str, kind: str, value: str) -> None:
        super().__init__(f"attachment {filename!r} has the {kind} {value!r}, which the policy does not allow")
        self.filename = filename
        self.kind = kind
        self.value = value


class AttachmentCountExceeded(MailThunderAttachmentException):
    """The message carries more attachments than the policy allows."""

    def __init__(self, count: int, limit: int) -> None:
        super().__init__(f"{count} attachments, over the limit of {limit}")
        self.count = count
        self.limit = limit


class TotalAttachmentSizeExceeded(MailThunderAttachmentException):
    """The attachments together are larger than the policy's total limit."""

    def __init__(self, size: int, limit: int) -> None:
        super().__init__(f"attachments total {size} bytes, over the limit of {limit}")
        self.size = size
        self.limit = limit
