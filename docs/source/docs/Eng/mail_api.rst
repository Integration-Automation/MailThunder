Core Mail API
=============

``Mail`` is the provider-agnostic API of MailThunder: the same calls send, read, draft and
delete mail whatever the account's provider is. Code written against it does not know
whether SMTP, IMAP or an HTTP API is behind it.

It uses the credentials described in :doc:`authentication`, connects on first use, keeps the
connection for the calls that follow, and raises an exception when something fails instead
of only logging it.

.. code-block:: text

   your code / MT_mail_* actions
              |
            Mail  ---- AttachmentPolicy (checked before sending)
              |
        MailProvider
        /          \
   MailSender    MailStore
   (SMTPProvider) (IMAPProvider)
        \          /
     Authentication (password, app password, XOAUTH2)

----

Sending Mail
------------

.. code-block:: python

   from je_mail_thunder import Mail

   with Mail() as mail:                       # Gmail, or the provider the OAuth2 settings name
       mail.send(
           to="receiver@example.com",         # one address, several separated by commas, or a list
           cc=["team@example.com"],
           subject="Nightly report",
           text="42 passed, 0 failed.",
           html="<b>42</b> passed, 0 failed.",
           attachments=["report.html"],
       )

``send`` takes the fields of a ``MailMessage`` as keyword arguments, or a ready ``MailMessage``:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Meaning
   * - ``to``, ``cc``, ``bcc``
     - Recipients: an address, several separated by commas, or a list. ``Name <user@host>`` works.
       ``bcc`` recipients get the message without the others seeing them
   * - ``subject``
     - The subject line
   * - ``text``, ``html``
     - The plain-text and HTML bodies. With both, the message carries them as alternatives
   * - ``attachments``
     - Paths, or ``Attachment`` objects
   * - ``sender``
     - The ``From`` address. The account's user when left out
   * - ``reply_to``
     - Where replies go
   * - ``headers``
     - Further headers, as a dict

It returns the message as it was sent.

What Is Checked First
~~~~~~~~~~~~~~~~~~~~~

Before anything reaches the server:

- there is at least one recipient and a sender;
- every address is valid (``a@example.com; b@example.com`` is refused: separate with commas);
- the subject and the header values are one line, and a custom header does not replace
  ``Subject``, ``From``, ``To``, ``Cc``, ``Bcc`` or the MIME headers. A value therefore cannot
  smuggle in a second header;
- the attachments pass the attachment policy (:doc:`attachment_policy`).

A message that fails a check raises ``MailThunderMessageException`` or a
``MailThunderAttachmentException`` and is not sent.

.. code-block:: python

   from je_mail_thunder import AttachmentPolicy, Mail

   reports_only = AttachmentPolicy(max_file_size=5 * 1024 * 1024, allowed_extensions={"html", "pdf"})
   mail = Mail(policy=reports_only)           # the default is 25 MiB of any type

----

Reading, Drafts and Deleting
----------------------------

.. code-block:: python

   from je_mail_thunder import Mail

   with Mail() as mail:
       for message in mail.get_messages(folder="INBOX", limit=10, unread_only=True):
           print(message.message_id, message.sender, message.subject)
           for attachment in message.attachments:
               attachment.save("downloads")    # under a name that cannot leave the directory

       message = mail.get_message("4321")      # by the message_id get_messages gave
       draft_id = mail.create_draft(to="receiver@example.com", subject="Later", text="...")
       mail.delete_message("4321")

- ``get_messages`` returns an iterator, newest first. Messages are fetched one at a time as it is
  read, so a large mailbox is never held in memory. Reading does not mark a message as read.
- ``query`` takes a search in the provider's own syntax. Over IMAP that is ``SEARCH`` criteria,
  e.g. ``'FROM "ci@example.com" SINCE 1-Oct-2026'`` or ``"SUBJECT 報表"``.
- ``message_id`` is the provider's identifier of a stored message (over IMAP, the UID).
- ``create_draft`` checks the message like ``send`` and stores it in the drafts folder: the one
  given, else the account's ``drafts_folder``, else the folder the server flags ``\Drafts``.
- Folder names are written as a person reads them (``"收件匣"``, ``"[Gmail]/Sent Mail"``); they
  are encoded for the server.

A received ``MailMessage`` has ``subject``, ``sender``, ``to``, ``cc``, ``reply_to``, ``date``,
``text``, ``html``, ``attachments`` (their bytes in ``content``), ``message_id``, and the
``Message-ID``, ``In-Reply-To`` and ``References`` headers in ``headers``. ``to_dict()`` gives
JSON-ready values. Headers and parts that cannot be decoded are left out rather than failing
the whole message.

----

Accounts and Providers
----------------------

.. code-block:: python

   from je_mail_thunder import AppPasswordAuth, Mail, MailAccount, MailServers

   # Microsoft 365, logging in with the config file or the environment
   Mail(provider="microsoft")

   # Gmail with an app password given in code
   Mail(provider="gmail", auth=AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop"))

   # Any other SMTP / IMAP server
   Mail(account=MailAccount(
       provider="smtp",
       auth=AppPasswordAuth("you@example.com", "..."),
       servers=MailServers(smtp_host="smtp.example.com", imap_host="imap.example.com"),
   ))

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Provider name
     - Sends over
     - Reads over
   * - ``google`` (or ``gmail``)
     - SMTP, ``smtp.gmail.com:465``, implicit TLS
     - IMAP, ``imap.gmail.com``
   * - ``microsoft``
     - SMTP, ``smtp.office365.com:587``, STARTTLS
     - IMAP, ``outlook.office365.com``
   * - ``smtp``
     - SMTP on the account's ``MailServers``: implicit TLS on 465, or ``smtp_starttls=True`` on 587
     - IMAP on the account's ``MailServers``

Without a provider name, ``Mail()`` uses the provider the OAuth2 settings name (those of ``auth``,
else of the config file or the environment), else Gmail: the same servers ``smtp_instance`` and
``imap_instance`` use. Connections always use TLS.

``MailServers`` also takes ``smtp_port`` and ``drafts_folder``.

Adding a Provider
~~~~~~~~~~~~~~~~~

A backend implements ``MailSender`` (``send``), ``MailStore`` (``get_messages``, ``get_message``,
``create_draft``, ``delete_message``) or both, and is registered under a name. ``Mail`` and the
code that uses it stay the same.

.. code-block:: python

   from je_mail_thunder import Mail, MailSender, register_provider

   class LoggingSender(MailSender):
       name = "logging"

       def send(self, message):
           print(f"would send {message.subject!r} to {message.recipients}")

       def close(self):
           pass

   register_provider("logging", lambda account: [LoggingSender()])
   Mail(provider="logging").send(to="a@example.com", sender="me@example.com", subject="Hi", text="...")

A factory receives the ``MailAccount`` and returns the providers without connecting.

----

Errors
------

Every failure is logged through ``mail_thunder_logger`` and raised as a ``MailThunderException``
subclass from ``je_mail_thunder.utils.exception.exceptions``:

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - Exception
     - Meaning
   * - ``MailThunderMessageException``
     - The message cannot be sent as it is: no recipient, no sender, an invalid address or header
   * - ``MailThunderAttachmentException``
     - An attachment is missing or breaks the policy (:doc:`attachment_policy`)
   * - ``MailThunderAuthenticationException``
     - There are no credentials, or the server refused the login
   * - ``MailThunderConnectionException``
     - The server could not be reached, or the connection was lost
   * - ``MailThunderSendException``
     - The server refused the message, or some of its recipients (``refused`` maps each one to
       the server's answer)
   * - ``MailThunderProviderException``
     - Base of the two above; also an unknown provider, a refused folder or an unknown message id

.. code-block:: python

   from je_mail_thunder import Mail
   from je_mail_thunder.utils.exception.exceptions import (
       MailThunderAuthenticationException,
       MailThunderException,
       MailThunderSendException,
   )

   try:
       Mail().send(to="receiver@example.com", subject="Report", text="...")
   except MailThunderAuthenticationException:
       print("check the credentials")
   except MailThunderSendException as error:
       print("refused:", error.refused)
   except MailThunderException as error:
       print("not sent:", error)

A message is never sent twice: a failure while sending is reported, not retried. A connection
the server dropped while it sat idle is replaced before the next call, and one answer from the
server is waited for at most 60 seconds.

----

In Action Files
---------------

The ``MT_mail_*`` commands run on ``mail_instance``, a ``Mail()`` for the account of the config
file or the environment. They take and return JSON-ready values, so they also work through the
socket server.

.. code-block:: json

   {
     "mail_thunder": [
       ["MT_mail_send", {
         "to": "receiver@example.com",
         "subject": "Automated Email",
         "text": "Hello World!",
         "attachments": ["report.html"]
       }],
       ["MT_mail_get_messages", {"limit": 5, "unread_only": true}],
       ["MT_mail_close"]
     ]
   }

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - Arguments and result
   * - ``MT_mail_send``
     - The message fields (``to``, ``subject``, ``text``, ``html``, ``cc``, ``bcc``,
       ``attachments``, ``sender``, ``reply_to``, ``headers``). Returns the sent message
   * - ``MT_mail_create_draft``
     - The message fields, plus ``folder``. Returns the draft's id, or ``null``
   * - ``MT_mail_get_messages``
     - ``folder``, ``limit``, ``unread_only``, ``query``. Returns a list of messages; give a
       ``limit`` for a large folder
   * - ``MT_mail_get_message``
     - ``message_id``, ``folder``. Returns the message
   * - ``MT_mail_delete_message``
     - ``message_id``, ``folder``
   * - ``MT_mail_close``
     - None. Closes the connections; the next command connects again

The attachment policy of ``mail_instance`` is set from Python (``mail_instance.policy = ...``),
never by an action, so an action file cannot loosen it.

----

Moving from the Wrappers
------------------------

``SMTPWrapper``, ``IMAPWrapper``, ``smtp_instance``, ``imap_instance`` and the ``MT_smtp_*`` /
``MT_imap_*`` commands keep working as before. Code can move one call at a time.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Wrapper call
     - ``Mail`` call
   * - ``smtp.later_init()`` / ``imap.later_init()``
     - Not needed: ``Mail`` logs in on first use
   * - ``smtp.create_message_and_send(content, settings)``
     - ``mail.send(to=..., subject=..., text=content)``
   * - ``smtp.create_message_with_attach_and_send(content, settings, file, use_html=True)``
     - ``mail.send(to=..., subject=..., html=content, attachments=[file])``
   * - ``imap.select_mailbox("INBOX")`` then ``imap.mail_content_list()``
     - ``mail.get_messages(folder="INBOX")``
   * - ``smtp.quit()`` / ``imap.quit()``
     - ``mail.close()``, or ``with Mail() as mail:``

Two helpers bridge the two APIs:

.. code-block:: python

   from je_mail_thunder import Mail, legacy_message, mail_from_wrappers, smtp_instance

   # The arguments of create_message_and_send / create_message_with_attach_and_send, as a message
   message = legacy_message(
       "Hello", {"Subject": "Hi", "From": "me@gmail.com", "To": "you@example.com"},
       attach_file="report.pdf", use_html=False)
   Mail().send(message)

   # Or keep a wrapper that is already logged in, and send through it with the checks Mail adds
   smtp_instance.later_init()
   mail_from_wrappers(smtp=smtp_instance).send(message)

``mail_from_wrappers(smtp=None, imap=None, policy=None)`` leaves the wrappers to their owner:
closing the ``Mail`` does not close them, and each message needs its own ``sender``.

What differs from the wrappers:

- ``Mail`` raises where the wrapper methods log the error and return ``None``;
- a message needs at least one valid recipient and passes the checks above;
- reading does not mark messages as read, and ``get_messages`` returns ``MailMessage`` objects
  instead of ``{"SUBJECT": ..., "FROM": ..., "TO": ..., "BODY": ...}`` dicts.
