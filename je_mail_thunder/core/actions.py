"""
The ``MT_mail_*`` actions: the :class:`~je_mail_thunder.core.mail.Mail` API on ``mail_instance``, taking and
returning JSON-ready values so an action file or the socket server can use it.
"""
from typing import List, Optional

from je_mail_thunder.core.mail import mail_instance
from je_mail_thunder.providers.base import DEFAULT_FOLDER


def mail_send(**message_fields) -> dict:
    """
    ``MT_mail_send``: send a message through the configured provider.

    :param message_fields: ``to``, ``cc``, ``bcc``, ``subject``, ``text``, ``html``, ``attachments`` (paths),
        ``sender``, ``reply_to``, ``headers``
    :return: the message as it was sent
    """
    return mail_instance.send(**message_fields).to_dict()


def mail_create_draft(folder: Optional[str] = None, **message_fields) -> Optional[str]:
    """
    ``MT_mail_create_draft``: store a message as a draft.

    :param folder: the drafts folder; the account's own by default
    :param message_fields: the message, as ``MT_mail_send`` takes it
    :return: the draft's id when the provider reports it, else ``None``
    """
    return mail_instance.create_draft(folder=folder, **message_fields)


def mail_get_messages(folder: str = DEFAULT_FOLDER, limit: Optional[int] = None, unread_only: bool = False,
                      query: Optional[str] = None) -> List[dict]:
    """
    ``MT_mail_get_messages``: the messages of a folder, newest first.

    :param folder: the folder to read
    :param limit: stop after this many messages; give one for a large folder, since the answer is one list
    :param unread_only: skip messages that were already read
    :param query: a search in the provider's own syntax (IMAP ``SEARCH`` criteria)
    :return: the messages; attachments are described by name, type and size
    """
    return [message.to_dict() for message in mail_instance.get_messages(folder, limit, unread_only, query)]


def mail_get_message(message_id: str, folder: str = DEFAULT_FOLDER) -> dict:
    """
    ``MT_mail_get_message``: one message by its id.

    :param message_id: the ``message_id`` of a message ``MT_mail_get_messages`` returned
    :param folder: the folder it is in
    :return: the message
    """
    return mail_instance.get_message(message_id, folder).to_dict()
