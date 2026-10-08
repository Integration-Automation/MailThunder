Attachment Policy
=================

An ``AttachmentPolicy`` says what a message may carry: how many attachments, how large,
and of which types. ``validate_attachments`` checks a message's attachments against it
before anything is sent, and raises a structured exception at the first rule that is broken.

----

Defining a Policy
-----------------

.. code-block:: python

   from je_mail_thunder import Attachment, AttachmentPolicy, validate_attachments

   policy = AttachmentPolicy(
       max_file_size=10 * 1024 * 1024,     # bytes one attachment may have
       max_total_size=20 * 1024 * 1024,    # bytes all attachments may have together
       max_count=5,
       allowed_extensions={"pdf", "csv", "html"},
       allowed_mime_types={"application/pdf", "text/*"},
   )

   attachments = [Attachment.from_path("report.pdf"), Attachment.from_path("results.csv")]
   total_bytes = validate_attachments(attachments, policy)

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Setting
     - Default
     - Meaning
   * - ``max_file_size``
     - ``None``
     - Bytes one attachment may have
   * - ``max_total_size``
     - ``None``
     - Bytes all attachments of a message may have together
   * - ``max_count``
     - ``None``
     - Attachments a message may carry
   * - ``allowed_extensions``
     - ``None``
     - The only extensions accepted. ``"pdf"`` and ``".PDF"`` are the same; the last
       extension counts, so ``report.pdf.exe`` is an ``.exe``
   * - ``allowed_mime_types``
     - ``None``
     - The only MIME types accepted. ``"image/*"`` accepts every image type

``None`` lifts a limit, so ``AttachmentPolicy()`` allows everything that exists. A negative or
fractional limit, or a type set that is not a collection of strings, raises
``MailThunderAttachmentException`` when the policy is built.

``DEFAULT_ATTACHMENT_POLICY`` allows 25 MiB per attachment and per message, of any type: the
message size Gmail and Microsoft 365 accept.

.. note::

   The type checks read the file name, not the file's content. They stop the wrong file
   being sent by mistake, not a file that was renamed on purpose.

----

The Validation Pipeline
-----------------------

The checks run in this order, and the first one that fails raises:

.. code-block:: text

   count -> existence -> size -> extension -> MIME type -> total size

.. list-table::
   :header-rows: 1
   :widths: 32 38 30

   * - Exception
     - Raised when
     - Attributes
   * - ``AttachmentCountExceeded``
     - There are more attachments than ``max_count``
     - ``count``, ``limit``
   * - ``AttachmentNotFound``
     - A file to attach does not exist or is not a regular file
     - ``path``
   * - ``AttachmentTooLarge``
     - One attachment is over ``max_file_size``
     - ``filename``, ``size``, ``limit``
   * - ``AttachmentTypeNotAllowed``
     - An extension or MIME type is not allowed
     - ``filename``, ``kind`` (``"extension"`` or ``"MIME type"``), ``value``
   * - ``TotalAttachmentSizeExceeded``
     - Together the attachments are over ``max_total_size``
     - ``size``, ``limit``

All of them subclass ``MailThunderAttachmentException``:

.. code-block:: python

   from je_mail_thunder.utils.exception.exceptions import (
       AttachmentTooLarge,
       MailThunderAttachmentException,
   )

   try:
       validate_attachments(attachments, policy)
   except AttachmentTooLarge as error:
       print(f"{error.filename} is {error.size} bytes; the limit is {error.limit}")
   except MailThunderAttachmentException as error:
       print(f"Attachment refused: {error}")

Each failure is also logged through ``mail_thunder_logger`` before it is raised.

----

Attachments
-----------

An ``Attachment`` is a file to send, or one that arrived with a message.

.. code-block:: python

   from je_mail_thunder import Attachment

   # A file to send. It is opened only when the message is built.
   report = Attachment.from_path("out/report-2026-10.pdf", filename="report.pdf")
   print(report.filename, report.content_type, report.size)

   # One that arrived: its bytes are in ``content``.
   received = Attachment(filename="notes.txt", content_type="text/plain", content=b"...")
   path = received.save("downloads")

``Attachment.from_path`` takes the name the recipient sees (the file's own name by default)
and the MIME type (guessed from the name by default; ``application/octet-stream`` when the
name suggests none).

Saving Received Attachments Safely
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The file name of a received attachment is whatever the sender wrote. ``Attachment.save(directory)``
writes it under a name made safe first, so the file cannot land outside ``directory``:

- directory parts of either separator style are dropped (``../../etc/passwd`` becomes ``passwd``);
- ``..``, control characters and the characters Windows refuses (``: * ? " < > |``) are replaced;
- a Windows device name (``NUL``, ``COM1``) gets a leading underscore;
- a name with nothing left becomes ``attachment``.

The same function is available as ``je_mail_thunder.attachments.mime.safe_filename``.

.. note::

   ``Mail`` applies its policy to every ``send`` and ``create_draft`` (``Mail(policy=...)``;
   ``DEFAULT_ATTACHMENT_POLICY`` unless one is given). See :doc:`mail_api`.

   The ``SMTPWrapper`` methods (``create_message_with_attach_and_send``) do not apply a policy.
   Call ``validate_attachments`` yourself before using them.
