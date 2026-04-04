Reading Emails (IMAP)
=====================

MailThunder's ``IMAPWrapper`` extends ``imaplib.IMAP4_SSL`` to provide methods for
reading, searching, and exporting emails via the IMAP4 protocol.

Default connection: ``imap.gmail.com`` (SSL).

.. note::

   **Gmail users:** Make sure you have
   `enabled IMAP <https://support.google.com/mail/answer/7126229>`_ in your Gmail settings.

----

Reading All Emails from INBOX
-----------------------------

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       imap.select_mailbox("INBOX")
       emails = imap.mail_content_list()
       for mail in emails:
           print(f"Subject: {mail['SUBJECT']}")
           print(f"From:    {mail['FROM']}")
           print(f"To:      {mail['TO']}")
           print(f"Body:    {mail['BODY'][:200]}...")
           print("---")

**Returned dictionary format:**

Each email is a dictionary with four keys:

.. code-block:: python

   {
       "SUBJECT": "Email subject line",     # str — decoded subject
       "FROM": "sender@example.com",        # str — sender address
       "TO": "receiver@example.com",        # str — recipient address
       "BODY": "Email body content..."      # str — body text (decoded)
   }

For multipart emails, the body of the first part is extracted.

----

Searching Emails
----------------

The ``search_str`` parameter follows the
`IMAP SEARCH command syntax (RFC 3501 Section 6.4.4) <https://datatracker.ietf.org/doc/html/rfc3501#section-6.4.4>`_.

**Search by sender:**

.. code-block:: python

   emails = imap.mail_content_list(search_str='FROM "someone@example.com"')

**Search by subject:**

.. code-block:: python

   emails = imap.mail_content_list(search_str='SUBJECT "Important"')

**Search unread emails:**

.. code-block:: python

   emails = imap.mail_content_list(search_str="UNSEEN")

**Search by date:**

.. code-block:: python

   emails = imap.mail_content_list(search_str='SINCE "01-Jan-2025"')
   emails = imap.mail_content_list(search_str='BEFORE "31-Dec-2025"')
   emails = imap.mail_content_list(search_str='ON "15-Jun-2025"')

**Combine multiple criteria** (implicit AND):

.. code-block:: python

   emails = imap.mail_content_list(search_str='FROM "boss@company.com" UNSEEN')
   emails = imap.mail_content_list(search_str='SINCE "01-Jan-2025" SUBJECT "Report"')

**Full search criteria reference:**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Criteria
     - Description
   * - ``ALL``
     - All messages in the mailbox (default)
   * - ``UNSEEN``
     - Messages not marked as read
   * - ``SEEN``
     - Messages marked as read
   * - ``FLAGGED``
     - Messages with the \\Flagged flag (starred in Gmail)
   * - ``UNFLAGGED``
     - Messages without the \\Flagged flag
   * - ``ANSWERED``
     - Messages that have been replied to
   * - ``UNANSWERED``
     - Messages that have not been replied to
   * - ``DELETED``
     - Messages marked for deletion
   * - ``FROM "string"``
     - Messages from the specified sender
   * - ``TO "string"``
     - Messages sent to the specified recipient
   * - ``CC "string"``
     - Messages with the specified CC recipient
   * - ``SUBJECT "string"``
     - Messages with text in the subject
   * - ``BODY "string"``
     - Messages containing text in the body
   * - ``TEXT "string"``
     - Messages containing text in headers or body
   * - ``SINCE "DD-Mon-YYYY"``
     - Messages on or after the date (e.g., ``"01-Jan-2025"``)
   * - ``BEFORE "DD-Mon-YYYY"``
     - Messages before the date
   * - ``ON "DD-Mon-YYYY"``
     - Messages on the exact date
   * - ``LARGER n``
     - Messages larger than n bytes
   * - ``SMALLER n``
     - Messages smaller than n bytes
   * - ``NEW``
     - Messages that are recent and unseen
   * - ``OLD``
     - Messages that are not recent

----

Exporting All Emails to Files
------------------------------

Export every email in the selected mailbox to local files:

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       imap.select_mailbox("INBOX")
       exported = imap.output_all_mail_as_file()
       print(f"Exported {len(exported)} emails")

**File naming:**

- Each email is saved in the current working directory
- Filename = email subject + numeric suffix
- First occurrence: ``My Subject0``
- Duplicate subjects: ``My Subject1``, ``My Subject2``, ...
- File content = decoded email body text

----

Getting Raw Mail Details
------------------------

For advanced use cases, ``search_mailbox()`` returns the raw parsed data:

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       imap.select_mailbox("INBOX")
       raw_list = imap.search_mailbox()
       for response, decode_info, message in raw_list:
           # response:    IMAP response status string (e.g., "OK")
           # decode_info: raw RFC822 decode header bytes (e.g., b'1 (RFC822 {12345}')
           # message:     email.message.Message object — full Python email object
           print(f"Subject: {message.get('Subject')}")
           print(f"Date: {message.get('Date')}")
           print(f"Content-Type: {message.get_content_type()}")
           print(f"Message-ID: {message.get('Message-ID')}")

           # Access all headers
           for key in message.keys():
               print(f"  {key}: {message[key]}")

           # Access parts of multipart messages
           if message.is_multipart():
               for i, part in enumerate(message.get_payload()):
                   print(f"  Part {i}: {part.get_content_type()}")

The ``message`` object is a standard Python ``email.message.Message`` (parsed with
``email.policy.default``), giving you full access to all headers, parts, and
decoding utilities.

----

Read-Only Mode
--------------

Open the mailbox in read-only mode to prevent any side effects (e.g., marking
emails as read):

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       success = imap.select_mailbox("INBOX", readonly=True)
       if success:
           emails = imap.mail_content_list()

----

Selecting Different Mailboxes
-----------------------------

Besides ``INBOX``, you can select other standard or provider-specific mailboxes:

.. code-block:: python

   # Standard mailboxes
   imap.select_mailbox("Sent")
   imap.select_mailbox("Drafts")
   imap.select_mailbox("Trash")

   # Gmail-specific labels
   imap.select_mailbox("[Gmail]/All Mail")
   imap.select_mailbox("[Gmail]/Starred")
   imap.select_mailbox("[Gmail]/Spam")
   imap.select_mailbox("[Gmail]/Important")

The ``select_mailbox()`` method returns ``True`` if the selection succeeded
(IMAP status ``"OK"``), ``False`` otherwise.

----

Using a Different IMAP Provider
---------------------------------

Pass a custom ``host`` to the constructor:

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   # Outlook / Office 365
   imap = IMAPWrapper(host="outlook.office365.com")

   # Yahoo Mail
   imap = IMAPWrapper(host="imap.mail.yahoo.com")

   # Custom server
   imap = IMAPWrapper(host="imap.example.com")

----

Manual Login Without Context Manager
--------------------------------------

.. code-block:: python

   from je_mail_thunder import IMAPWrapper, set_mail_thunder_os_environ

   imap = IMAPWrapper(host="imap.gmail.com")

   set_mail_thunder_os_environ(
       "your_email@gmail.com",
       "your_app_password"
   )

   imap.later_init()
   imap.select_mailbox("INBOX")

   for mail in imap.mail_content_list():
       print(mail.get("SUBJECT"))
       print(mail.get("FROM"))
       print(mail.get("TO"))
       print(mail.get("BODY"))

   # Always quit when done
   imap.quit()

----

Reading via JSON Scripting Engine
---------------------------------

**Read and display emails:**

.. code-block:: json

   {
     "auto_control": [
       ["MT_imap_later_init"],
       ["MT_imap_select_mailbox", {"mailbox": "INBOX", "readonly": true}],
       ["MT_imap_mail_content_list", {"search_str": "UNSEEN"}],
       ["MT_imap_quit"]
     ]
   }

**Export all emails to files:**

.. code-block:: json

   {
     "auto_control": [
       ["MT_imap_later_init"],
       ["MT_imap_select_mailbox"],
       ["MT_imap_output_all_mail_as_file"],
       ["MT_imap_quit"]
     ]
   }

Execute via CLI:

.. code-block:: bash

   python -m je_mail_thunder -e /path/to/read_action.json
