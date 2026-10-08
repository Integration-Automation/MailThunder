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
