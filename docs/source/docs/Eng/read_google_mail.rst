Read Emails via IMAP
====================

MailThunder's ``IMAPWrapper`` extends ``imaplib.IMAP4_SSL`` to provide methods for reading,
searching, and exporting emails. By default it connects to ``imap.gmail.com`` (SSL).

----

Basic Setup
-----------

Before reading emails, you need to configure authentication. See the
:doc:`eng_index` page for authentication setup instructions.

.. note::

    **Gmail users:** Make sure you have
    `enabled IMAP <https://support.google.com/mail/answer/7126229>`_ in your Gmail settings.

----

Reading All Emails from INBOX
-----------------------------

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    with IMAPWrapper() as imap:
        imap.later_init()  # Log in using config file or env vars
        imap.select_mailbox("INBOX")
        emails = imap.mail_content_list()
        for mail in emails:
            print(f"Subject: {mail['SUBJECT']}")
            print(f"From:    {mail['FROM']}")
            print(f"To:      {mail['TO']}")
            print(f"Body:    {mail['BODY'][:200]}...")
            print("---")

Each email is returned as a dictionary:

.. code-block:: python

    {
        "SUBJECT": "Email subject line",
        "FROM": "sender@example.com",
        "TO": "receiver@example.com",
        "BODY": "Email body content..."
    }

----

Searching Emails
----------------

The ``search_str`` parameter follows the
`IMAP SEARCH command syntax (RFC 3501) <https://datatracker.ietf.org/doc/html/rfc3501#section-6.4.4>`_.

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

**Search all emails (default):**

.. code-block:: python

    emails = imap.mail_content_list(search_str="ALL")

----

Exporting All Emails to Files
------------------------------

Export every email in the selected mailbox to local files:

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX")
        imap.output_all_mail_as_file()

Each email is saved as a file named by its subject line. Duplicate subjects are
automatically suffixed with an incrementing number (e.g., ``My Subject0``, ``My Subject1``).

----

Getting Raw Mail Details
------------------------

For advanced use cases, ``search_mailbox()`` returns raw mail data:

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX")
        raw_list = imap.search_mailbox()
        for response, decode_info, message in raw_list:
            # response: IMAP response status (e.g., "OK")
            # decode_info: raw RFC822 decode header bytes
            # message: email.message.Message object (full access to all headers and parts)
            print(f"Subject: {message.get('Subject')}")
            print(f"Date: {message.get('Date')}")
            print(f"Content-Type: {message.get_content_type()}")

----

Read-Only Mode
--------------

Open the mailbox in read-only mode to prevent marking emails as read:

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX", readonly=True)
        emails = imap.mail_content_list()

----

Manual Login (Without Context Manager)
---------------------------------------

.. code-block:: python

    from je_mail_thunder import IMAPWrapper, set_mail_thunder_os_environ

    imap_host = "imap.gmail.com"
    imap_wrapper = IMAPWrapper(host=imap_host)

    set_mail_thunder_os_environ(
        "your_email@gmail.com",
        "your_app_password"
    )

    imap_wrapper.later_init()
    imap_wrapper.select_mailbox("INBOX")

    mail_list = imap_wrapper.mail_content_list()
    for mail in mail_list:
        print(mail.get("SUBJECT"))
        print(mail.get("FROM"))
        print(mail.get("TO"))
        print(mail.get("BODY"))

    imap_wrapper.quit()

----

Using a Different IMAP Provider
---------------------------------

Pass a custom ``host`` to the constructor:

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    # Outlook
    imap = IMAPWrapper(host="outlook.office365.com")

    # Yahoo
    imap = IMAPWrapper(host="imap.mail.yahoo.com")

    # Custom server
    imap = IMAPWrapper(host="imap.example.com")

----

Reading via JSON Scripting Engine
---------------------------------

Read and export emails using the JSON scripting engine:

.. code-block:: json

    {
        "auto_control": [
            ["MT_imap_later_init"],
            ["MT_imap_select_mailbox", {"mailbox": "INBOX", "readonly": true}],
            ["MT_imap_mail_content_list", {"search_str": "UNSEEN"}],
            ["MT_imap_quit"]
        ]
    }

Export all emails:

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

----
