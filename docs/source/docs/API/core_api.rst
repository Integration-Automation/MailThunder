Core Mail API
=============

The provider-agnostic layer of MailThunder. Everything on this page is exported from the
top-level ``je_mail_thunder`` package unless a module is named.

----

Attachments
-----------

**Modules:** ``je_mail_thunder.attachments.attachment``, ``je_mail_thunder.attachments.policy``,
``je_mail_thunder.attachments.validator``, ``je_mail_thunder.attachments.mime``

Attachment
~~~~~~~~~~

.. code-block:: python

   @dataclass(frozen=True)
   class Attachment:
       filename: str
       content_type: str = "application/octet-stream"
       path: Optional[str] = None
       content: Optional[bytes] = None

A file that goes with a message. One to send names a ``path``, read only when the message is
handed to the provider. One that arrived holds its bytes in ``content`` (kept out of the ``repr``).
Without a ``filename``, or with neither ``path`` nor ``content``, it raises
``MailThunderAttachmentException``.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Member
     - Description
   * - ``Attachment.from_path(path, filename=None, content_type=None)``
     - An attachment to send. ``filename`` defaults to the file's name and ``content_type`` to
       the type its name suggests
   * - ``Attachment.of(source)``
     - ``source`` itself when it is an ``Attachment``, else ``from_path(source)``; anything but a
       path raises ``MailThunderAttachmentException``
   * - ``size``
     - Size in bytes. Raises ``AttachmentNotFound`` when the file to send does not exist
   * - ``read()``
     - The attachment's bytes. Raises ``AttachmentNotFound`` when the file cannot be read
   * - ``save(directory)``
     - Write the attachment into ``directory`` under a safe name and return the path
   * - ``describe()``
     - ``{"filename": ..., "content_type": ..., "size": ...}``, for logs and action records

AttachmentPolicy
~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass(frozen=True)
   class AttachmentPolicy:
       max_file_size: Optional[int] = None
       max_total_size: Optional[int] = None
       max_count: Optional[int] = None
       allowed_extensions: Optional[FrozenSet[str]] = None
       allowed_mime_types: Optional[FrozenSet[str]] = None

The limits attachments are checked against. ``None`` lifts a limit. Extensions are stored
lower-cased with their dot, MIME types lower-cased. An invalid limit or type set raises
``MailThunderAttachmentException``.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Member
     - Description
   * - ``allows_extension(filename)``
     - ``True`` when the file name's last extension is allowed
   * - ``allows_mime_type(content_type)``
     - ``True`` when the type, or its ``<main type>/*``, is allowed
   * - ``DEFAULT_ATTACHMENT_POLICY``
     - ``AttachmentPolicy(max_file_size=25 MiB, max_total_size=25 MiB)``

validate_attachments()
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def validate_attachments(attachments: Iterable[Attachment], policy: AttachmentPolicy) -> int

Check a message's attachments against a policy, in the order count, existence, size, extension,
MIME type, total size.

**Returns:** the attachments' total size in bytes.

**Raises:** ``AttachmentCountExceeded``, ``AttachmentNotFound``, ``AttachmentTooLarge``,
``AttachmentTypeNotAllowed`` or ``TotalAttachmentSizeExceeded`` (all
``MailThunderAttachmentException``), logged before it is raised.

MIME Helpers
~~~~~~~~~~~~

**Module:** ``je_mail_thunder.attachments.mime`` (not re-exported from the package)

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Function
     - Description
   * - ``guess_content_type(filename)``
     - The MIME type a file name suggests; ``application/octet-stream`` when it suggests none
       or a compressed encoding (``report.txt.gz``)
   * - ``file_extension(filename)``
     - The last extension, lower-cased and with its dot (``""`` without one)
   * - ``safe_filename(filename, fallback="attachment")``
     - A bare file name that cannot leave the directory it is written to

----

Authentication
--------------

**Modules:** ``je_mail_thunder.auth.base``, ``je_mail_thunder.auth.password``,
``je_mail_thunder.auth.oauth2``, ``je_mail_thunder.auth.xoauth2``

Authentication
~~~~~~~~~~~~~~

.. code-block:: python

   class Authentication(ABC):
       def __init__(self, user: str) -> None: ...

One way of logging an account in. A mechanism overrides what it can do; the rest raises
``MailThunderAuthenticationException``.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Member
     - Description
   * - ``user``
     - The account's mail address
   * - ``mechanism``
     - The mechanism's name, for logs and error messages (abstract)
   * - ``login(client)``
     - Log an SMTP or IMAP wrapper in
   * - ``authorization()``
     - The value of the HTTP ``Authorization`` header

Mechanisms
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Class
     - ``mechanism``
     - Notes
   * - ``PasswordAuth(user, password)``
     - ``password``
     - ``login`` calls ``client.login(user, password)``
   * - ``AppPasswordAuth(user, app_password)``
     - ``app-password``
     - A ``PasswordAuth`` that drops the whitespace an app password is shown with
   * - ``OAuth2Auth(settings, token_cache=None)``
     - ``oauth2``
     - ``access_token()`` and ``authorization()`` (``Bearer <token>``); no mail server login
   * - ``XOAUTH2Auth(settings, token_cache=None)``
     - ``xoauth2``
     - An ``OAuth2Auth`` whose ``login`` calls ``client.oauth2_login(user, access_token)``

``settings`` is an ``OAuth2Settings``. ``token_cache`` defaults to the shared ``oauth2_token_cache``,
looked up each time a token is needed. A missing user, password or settings object raises
``MailThunderAuthenticationException``; a refused or unreachable token endpoint raises
``MailThunderOAuth2Exception``, a subclass.

resolve_authentication()
~~~~~~~~~~~~~~~~~~~~~~~~

**Module:** ``je_mail_thunder.utils.save_mail_user_content.credentials``

.. code-block:: python

   def resolve_authentication() -> Optional[Authentication]

The login of ``mail_thunder_content.json`` or the environment: an ``XOAUTH2Auth`` when there are
OAuth2 settings, else a ``PasswordAuth``, else ``None``.

**Raises:** ``MailThunderOAuth2Exception`` when the OAuth2 settings found are incomplete or invalid.
