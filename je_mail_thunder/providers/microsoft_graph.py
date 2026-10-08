"""
Microsoft 365 mail over the Microsoft Graph API (``https://graph.microsoft.com/v1.0``): sending, drafts, reading
and deleting with an OAuth2 bearer token, and nothing but the standard library.

The account logs in with OAuth2 (:class:`~je_mail_thunder.auth.oauth2.OAuth2Auth` or its ``XOAUTH2Auth``
subclass). When its settings name no scope, the token is asked for with the Graph mail scopes.
"""
from __future__ import annotations

import base64
import json
import urllib.parse
from dataclasses import replace
from datetime import datetime
from email.utils import parseaddr
from typing import Any, Dict, Iterator, List, Mapping, Optional, Type

from je_mail_thunder.attachments.attachment import Attachment
from je_mail_thunder.attachments.mime import safe_filename
from je_mail_thunder.auth.oauth2 import OAuth2Auth
from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.providers.base import DEFAULT_FOLDER, MailSender, MailStore
from je_mail_thunder.providers.http import Transport, decode_json, https_request
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderAuthenticationException,
    MailThunderException,
    MailThunderProviderException,
    MailThunderSendException,
)
from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/Mail.ReadWrite offline_access"
PROVIDER_NAME = "microsoft_graph"
# Graph takes a file attachment inside a JSON request up to 3 MiB; larger ones go through an upload session.
MAX_INLINE_ATTACHMENT_BYTES = 3 * 1024 * 1024
# A sendMail request is limited to 4 MiB as a whole; attachments above this total are added to a draft first.
MAX_INLINE_TOTAL_BYTES = 2 * 1024 * 1024
# Upload sessions take the file in pieces; Graph asks for multiples of 320 KiB.
UPLOAD_CHUNK_BYTES = 10 * 320 * 1024
PAGE_SIZE = 25
_FILE_ATTACHMENT = "#microsoft.graph.fileAttachment"
# What a caller calls a folder, and the name Graph knows it by.
_WELL_KNOWN_FOLDERS = {
    "inbox": "inbox", "drafts": "drafts", "sent": "sentitems", "sent items": "sentitems", "sentitems": "sentitems",
    "deleted items": "deleteditems", "deleteditems": "deleteditems", "trash": "deleteditems",
    "junk": "junkemail", "junk email": "junkemail", "junkemail": "junkemail", "archive": "archive",
    "outbox": "outbox",
}
_MESSAGE_FIELDS = ("id,subject,from,toRecipients,ccRecipients,bccRecipients,replyTo,receivedDateTime,body,"
                   "hasAttachments,internetMessageId")


def _recipient(address: str) -> dict:
    name, mailbox = parseaddr(address)
    email_address = {"address": mailbox}
    if name:
        email_address["name"] = name
    return {"emailAddress": email_address}


def _address(recipient: Optional[Mapping[str, Any]]) -> Optional[str]:
    """``Name <address>`` or ``address`` from a Graph recipient."""
    email_address = (recipient or {}).get("emailAddress") or {}
    mailbox, name = email_address.get("address"), email_address.get("name")
    if not mailbox:
        return None
    return f"{name} <{mailbox}>" if name and name != mailbox else mailbox


def _addresses(recipients: Optional[List[Mapping[str, Any]]]) -> List[str]:
    return [address for address in (_address(recipient) for recipient in recipients or ()) if address]


def _received(value: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def _file_attachment(attachment: Attachment) -> dict:
    return {"@odata.type": _FILE_ATTACHMENT, "name": attachment.filename, "contentType": attachment.content_type,
            "contentBytes": base64.b64encode(attachment.read()).decode("ascii")}


def graph_message(message: MailMessage, sender_is_account: bool = True, attachments: bool = True) -> dict:
    """
    A message as Graph takes it.

    :param message: a message that passed :func:`~je_mail_thunder.core.message.check_outgoing`
    :param sender_is_account: leave ``from`` to Graph, which fills in the signed-in user
    :param attachments: put the attachments into the message; False when they are added afterwards
    :return: the Graph ``message`` resource
    :raises MailThunderProviderException: a custom header does not start with ``X-``, the only kind Graph takes
    """
    body_type, content = ("HTML", message.html) if message.html is not None else ("Text", message.text or "")
    resource: Dict[str, Any] = {
        "subject": message.subject,
        "body": {"contentType": body_type, "content": content},
        "toRecipients": [_recipient(address) for address in message.to],
        "ccRecipients": [_recipient(address) for address in message.cc],
        "bccRecipients": [_recipient(address) for address in message.bcc],
        "replyTo": [_recipient(address) for address in message.reply_to],
    }
    if not sender_is_account and message.sender:
        resource["from"] = _recipient(message.sender)
    if message.headers:
        refused = sorted(name for name in message.headers if not name.lower().startswith("x-"))
        if refused:
            raise MailThunderProviderException(
                f"Microsoft Graph only takes custom headers that start with X-: {refused}")
        resource["internetMessageHeaders"] = [{"name": name, "value": value} for name, value in message.headers.items()]
    if attachments and message.attachments:
        resource["attachments"] = [_file_attachment(attachment) for attachment in message.attachments]
    return resource


def mail_message(resource: Mapping[str, Any], attachments: Optional[List[Mapping[str, Any]]] = None) -> MailMessage:
    """
    A Graph ``message`` resource as a :class:`MailMessage`.

    :param resource: the message as Graph answered it
    :param attachments: its ``attachments`` collection; only file attachments have content
    :return: the message, with attachment names made safe to write to disk
    """
    body = resource.get("body") or {}
    is_html = str(body.get("contentType", "")).lower() == "html"
    files = [
        Attachment(filename=safe_filename(item.get("name")),
                   content_type=item.get("contentType") or "application/octet-stream",
                   content=base64.b64decode(item["contentBytes"]))
        for item in attachments or () if item.get("contentBytes") is not None
    ]
    internet_id = resource.get("internetMessageId")
    return MailMessage(
        subject=resource.get("subject") or "",
        to=_addresses(resource.get("toRecipients")), cc=_addresses(resource.get("ccRecipients")),
        bcc=_addresses(resource.get("bccRecipients")), reply_to=_addresses(resource.get("replyTo")),
        sender=_address(resource.get("from")),
        text=None if is_html else body.get("content"), html=body.get("content") if is_html else None,
        attachments=files, headers={"Message-ID": internet_id} if internet_id else {},
        message_id=resource.get("id"), date=_received(resource.get("receivedDateTime")),
    )


class MicrosoftGraphProvider(MailSender, MailStore):
    """Sends, drafts, reads and deletes Microsoft 365 mail through Microsoft Graph."""

    name = PROVIDER_NAME

    def __init__(self, account: MailAccount, transport: Transport = https_request) -> None:
        """
        :param account: whose mail; it must log in with OAuth2
        :param transport: sends one HTTPS request and returns the status and the body (replaceable for tests or
            a proxy-aware client)
        """
        self._account = account
        self._transport = transport
        self._graph_auth: Optional[OAuth2Auth] = None
        self._folders: Dict[str, str] = {}

    def close(self) -> None:
        """
        Nothing is kept open between two requests.

        :return: None
        """

    def _authorization(self) -> str:
        """The ``Authorization`` header: the account's OAuth2 token, asked for with the Graph scopes."""
        auth = self._account.authentication()
        if isinstance(auth, OAuth2Auth) and auth.settings.scope is None and not auth.settings.access_token:
            if self._graph_auth is None or self._graph_auth.settings != replace(auth.settings, scope=GRAPH_SCOPE):
                self._graph_auth = OAuth2Auth(replace(auth.settings, scope=GRAPH_SCOPE))
            auth = self._graph_auth
        return auth.authorization()

    def call(self, method: str, path: str, payload: Any = None,
             refusal: Type[MailThunderException] = MailThunderProviderException) -> Any:
        """
        One Graph request.

        :param method: the HTTP method
        :param path: a path under ``/v1.0`` (``/me/messages``), or a full Graph URL such as an ``@odata.nextLink``
        :param payload: the JSON body
        :param refusal: the exception a refused request raises
        :return: the JSON answer, ``{}`` when there is none
        :raises MailThunderAuthenticationException: Graph answered 401 or 403
        :raises MailThunderConnectionException: Graph could not be reached
        :raises MailThunderProviderException: Graph refused the request (``refusal``), or the URL is not Graph's
        """
        url = path if path.startswith("https://") else GRAPH_ROOT + path
        if not url.startswith(GRAPH_ROOT + "/"):
            raise MailThunderProviderException("a Microsoft Graph request stays on graph.microsoft.com")
        headers = {"Authorization": self._authorization(), "Accept": "application/json"}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        status, answer = self._transport(method, url, headers, body)
        data = decode_json(answer)
        if status < 400:
            return data
        error = data.get("error", {}) if isinstance(data, dict) else {}
        detail = f"HTTP {status} {error.get('code', '')}: {error.get('message', '')}".strip(" :")
        if status in (401, 403):
            raise MailThunderAuthenticationException(f"Microsoft Graph refused the token ({detail})")
        raise refusal(f"Microsoft Graph refused the request ({detail})")

    def folder_path(self, folder: str) -> str:
        """
        :param folder: a well-known name (``INBOX``, ``Drafts``, ...) or a folder's display name
        :return: the folder's well-known name or id, ready to be a path segment
        :raises MailThunderProviderException: the mailbox has no such folder
        """
        if not isinstance(folder, str) or not folder.strip():
            raise MailThunderProviderException(f"invalid folder name {folder!r}")
        known = _WELL_KNOWN_FOLDERS.get(folder.strip().lower())
        if known is not None:
            return known
        if folder not in self._folders:
            name = folder.replace("'", "''")
            query = urllib.parse.urlencode({"$filter": f"displayName eq '{name}'", "$top": "1", "$select": "id"})
            found = self.call("GET", f"/me/mailFolders?{query}").get("value") or []
            if not found:
                raise MailThunderProviderException(f"no folder {folder!r} in the mailbox")
            self._folders[folder] = found[0]["id"]
        return urllib.parse.quote(self._folders[folder], safe="")

    @staticmethod
    def _message_path(message_id: Any) -> str:
        if not isinstance(message_id, str) or not message_id.strip():
            raise MailThunderProviderException(f"a Microsoft Graph message id is text, not {message_id!r}")
        return "/me/messages/" + urllib.parse.quote(message_id, safe="")

    def _upload(self, message_path: str, attachment: Attachment) -> None:
        """Add one attachment to a draft: inside the request when it is small, else through an upload session."""
        if attachment.size <= MAX_INLINE_ATTACHMENT_BYTES:
            self.call("POST", f"{message_path}/attachments", _file_attachment(attachment), MailThunderSendException)
            return
        item = {"AttachmentItem": {"attachmentType": "file", "name": attachment.filename, "size": attachment.size,
                                   "contentType": attachment.content_type}}
        session = self.call("POST", f"{message_path}/attachments/createUploadSession", item, MailThunderSendException)
        content = attachment.read()
        for start in range(0, len(content), UPLOAD_CHUNK_BYTES):
            chunk = content[start:start + UPLOAD_CHUNK_BYTES]
            headers = {"Content-Type": "application/octet-stream", "Content-Length": str(len(chunk)),
                       "Content-Range": f"bytes {start}-{start + len(chunk) - 1}/{len(content)}"}
            # The upload URL is already authorised: no token is sent to it.
            status, _ = self._transport("PUT", str(session.get("uploadUrl", "")), headers, chunk)
            if status >= 400:
                raise MailThunderSendException(
                    f"Microsoft Graph refused the attachment {attachment.filename!r} (HTTP {status})")

    def _draft(self, message: MailMessage, folder: Optional[str], inline: bool) -> str:
        """Create a draft and return its id; attachments are added one by one unless ``inline``."""
        target = f"/me/mailFolders/{self.folder_path(folder)}/messages" if folder else "/me/messages"
        resource = graph_message(message, self._sender_is_account(message), attachments=inline)
        draft_id = self.call("POST", target, resource, MailThunderSendException).get("id")
        if not draft_id:
            raise MailThunderSendException("Microsoft Graph created no draft")
        if not inline:
            for attachment in message.attachments:
                self._upload(self._message_path(draft_id), attachment)
        return draft_id

    def _sender_is_account(self, message: MailMessage) -> bool:
        return parseaddr(message.sender or "")[1].lower() == self._account.authentication().user.lower()

    @staticmethod
    def _fits_inline(message: MailMessage) -> bool:
        sizes = [attachment.size for attachment in message.attachments]
        return sum(sizes) <= MAX_INLINE_TOTAL_BYTES and all(size <= MAX_INLINE_ATTACHMENT_BYTES for size in sizes)

    def send(self, message: MailMessage) -> None:
        """
        Send a message: in one ``sendMail`` request when its attachments are small, else as a draft that gets
        its attachments one by one and is then sent.

        :param message: a message that passed :func:`~je_mail_thunder.core.message.check_outgoing`
        :return: None
        :raises MailThunderSendException: Graph refused the message or an attachment
        :raises MailThunderAuthenticationException: there is no OAuth2 login, or Graph refused the token
        :raises MailThunderConnectionException: Graph could not be reached
        """
        mail_thunder_logger.info(
            f"graph provider, send: {len(message.recipients)} recipients, {len(message.attachments)} attachments")
        if self._fits_inline(message):
            payload = {"message": graph_message(message, self._sender_is_account(message)), "saveToSentItems": True}
            self.call("POST", "/me/sendMail", payload, MailThunderSendException)
            return
        draft_id = self._draft(message, None, inline=False)
        self.call("POST", f"{self._message_path(draft_id)}/send", refusal=MailThunderSendException)

    def create_draft(self, message: MailMessage, folder: Optional[str] = None) -> Optional[str]:
        """
        :param message: the draft
        :param folder: the folder to create it in; the Drafts folder by default
        :return: the draft's id
        :raises MailThunderSendException: Graph refused the draft or an attachment
        """
        mail_thunder_logger.info("graph provider, create_draft")
        return self._draft(message, folder, inline=self._fits_inline(message))

    def _complete(self, resource: Mapping[str, Any]) -> MailMessage:
        """The message with its attachments, which Graph lists separately."""
        attachments = None
        if resource.get("hasAttachments"):
            attachments = self.call("GET", f"{self._message_path(resource['id'])}/attachments").get("value")
        return mail_message(resource, attachments)

    def get_messages(self, folder: str = DEFAULT_FOLDER, limit: Optional[int] = None,
                     unread_only: bool = False, query: Optional[str] = None) -> Iterator[MailMessage]:
        """
        The messages of a folder, newest first, read a page at a time as the iterator is read.

        :param folder: a well-known name (``INBOX``, ``Drafts``, ``Sent``, ``Deleted Items``, ``Junk``,
            ``Archive``) or a folder's display name
        :param limit: stop after this many messages
        :param unread_only: only messages that are not read
        :param query: an OData ``$filter`` expression, e.g. ``from/emailAddress/address eq 'ci@example.com'``
        :return: an iterator of messages whose ``message_id`` is the Graph id
        """
        mail_thunder_logger.info(f"graph provider, get_messages: folder {folder!r}, limit {limit}")
        # Graph only orders by receivedDateTime when the filter starts with it.
        conditions = ["receivedDateTime ge 1900-01-01T00:00:00Z"]
        conditions += ["isRead eq false"] if unread_only else []
        conditions += [f"({query})"] if query else []
        parameters = {"$select": _MESSAGE_FIELDS, "$orderby": "receivedDateTime desc",
                      "$top": str(min(limit, PAGE_SIZE) if limit else PAGE_SIZE),
                      "$filter": " and ".join(conditions)}
        path: Optional[str] = (
            f"/me/mailFolders/{self.folder_path(folder)}/messages?{urllib.parse.urlencode(parameters)}")
        count = 0
        while path and limit != 0:
            page = self.call("GET", path)
            for resource in page.get("value") or ():
                if limit is not None and count >= limit:
                    return
                count += 1
                yield self._complete(resource)
            path = page.get("@odata.nextLink")

    def get_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> MailMessage:
        """
        :param message_id: the message's Graph id
        :param folder: not needed: a Graph id is unique in the mailbox
        :return: the message
        :raises MailThunderProviderException: there is no such message
        """
        mail_thunder_logger.info(f"graph provider, get_message in {folder!r}")
        query = urllib.parse.urlencode({"$select": _MESSAGE_FIELDS})
        return self._complete(self.call("GET", f"{self._message_path(message_id)}?{query}"))

    def delete_message(self, message_id: str, folder: str = DEFAULT_FOLDER) -> None:
        """
        :param message_id: the message's Graph id
        :param folder: not needed: a Graph id is unique in the mailbox
        :return: None
        :raises MailThunderProviderException: there is no such message
        """
        mail_thunder_logger.info(f"graph provider, delete_message in {folder!r}")
        self.call("DELETE", self._message_path(message_id))
