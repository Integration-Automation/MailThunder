MailThunder IMAP API
====================

**Module:** ``je_mail_thunder.imap.imap_wrapper``

``IMAPWrapper`` extends ``imaplib.IMAP4_SSL`` to provide a high-level interface for reading,
searching, and exporting emails via the IMAP4 protocol.

----

Class Definition
----------------

.. code-block:: python

    class IMAPWrapper(imaplib.IMAP4_SSL):
        """
        IMAP wrapper with auto-login, search, and export utilities.

        Inherits all methods from imaplib.IMAP4_SSL.
        Supports context manager (with statement).

        :param host: IMAP server hostname (default: "imap.gmail.com")
        """

        def __init__(self, host: str = "imap.gmail.com"):
            ...

----

Methods
-------

later_init
~~~~~~~~~~

.. code-block:: python

    def later_init(self):
        """
        Attempt to log in to the IMAP server.

        Calls try_to_login_with_env_or_content() internally.
        Catches and logs all exceptions without raising.

        :return: None
        """

**Example:**

.. code-block:: python

    imap = IMAPWrapper()
    imap.later_init()

----

try_to_login_with_env_or_content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def try_to_login_with_env_or_content(self):
        """
        Attempt to log in using credentials from config file or environment variables.

        Authentication flow:
        1. Try to read mail_thunder_content.json from the current working directory.
        2. If found and valid, log in with "user" and "password" keys.
        3. If not found, read mail_thunder_user and mail_thunder_user_password env vars.
        4. If env vars are set, log in with those credentials.

        :return: None
        """

----

select_mailbox
~~~~~~~~~~~~~~

.. code-block:: python

    def select_mailbox(self, mailbox: str = "INBOX", readonly: bool = False) -> bool:
        """
        Select a mailbox for subsequent operations.

        :param mailbox: The mailbox name to select (default: "INBOX").
            Common mailbox names: "INBOX", "Sent", "Drafts", "Trash", "Spam".
            For Gmail-specific labels, use "[Gmail]/All Mail", "[Gmail]/Starred", etc.
        :param readonly: If True, the mailbox is opened in read-only mode,
            preventing messages from being marked as read (default: False).
        :return: True if the mailbox was selected successfully (status "OK"), False otherwise.
        """

**Example:**

.. code-block:: python

    with IMAPWrapper() as imap:
        imap.later_init()
        success = imap.select_mailbox("INBOX", readonly=True)
        if success:
            print("Mailbox selected successfully")

----

search_mailbox
~~~~~~~~~~~~~~

.. code-block:: python

    def search_mailbox(self, search_str: [str, list] = "ALL", charset: str = None) -> list:
        """
        Search the selected mailbox and return raw mail details.

        Uses the IMAP SEARCH command (RFC 3501 Section 6.4.4).

        :param search_str: IMAP search criteria (default: "ALL").
            Examples:
            - "ALL" — all messages
            - "UNSEEN" — unread messages
            - 'FROM "user@example.com"' — messages from a specific sender
            - 'SUBJECT "keyword"' — messages with keyword in subject
            - 'SINCE "01-Jan-2025"' — messages since a date
            - 'BEFORE "31-Dec-2025"' — messages before a date
            - '(FROM "user@example.com" UNSEEN)' — combined criteria
        :param charset: Character set for the search (default: None).
        :return: A list of [response, decode_info, message] tuples:
            - response: IMAP response status string (e.g., "OK")
            - decode_info: Raw RFC822 decode header bytes
            - message: email.message.Message object (parsed email)
        """

**Example:**

.. code-block:: python

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX")
        raw_list = imap.search_mailbox(search_str="UNSEEN")
        for response, decode_info, message in raw_list:
            print(f"Subject: {message.get('Subject')}")
            print(f"Date: {message.get('Date')}")
            print(f"Content-Type: {message.get_content_type()}")

----

mail_content_list
~~~~~~~~~~~~~~~~~

.. code-block:: python

    def mail_content_list(
        self,
        search_str: [str, list] = "ALL",
        charset: str = None
    ) -> List[Dict[str, Union[str, bytes]]]:
        """
        Get all mail content as a list of parsed dictionaries.

        Each dictionary contains:
        - "SUBJECT": Email subject line (str)
        - "FROM": Sender address (str)
        - "TO": Recipient address (str)
        - "BODY": Email body content (str). For multipart emails,
          the payload of the first part is used.

        :param search_str: IMAP search criteria (default: "ALL").
        :param charset: Character set for the search (default: None).
        :return: A list of dicts, one per email.
        """

**Example:**

.. code-block:: python

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX")
        emails = imap.mail_content_list(search_str='FROM "boss@company.com"')
        for mail in emails:
            print(f"Subject: {mail['SUBJECT']}")
            print(f"From: {mail['FROM']}")
            print(f"To: {mail['TO']}")
            print(f"Body preview: {mail['BODY'][:100]}...")

----

output_all_mail_as_file
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def output_all_mail_as_file(
        self,
        search_str: [str, list] = "ALL",
        charset: str = None
    ) -> List[Dict[str, Union[str, bytes]]]:
        """
        Export all matching emails to local files.

        Each email is saved as a file in the current working directory,
        named by its subject line. If multiple emails share the same subject,
        a numeric suffix is appended (e.g., "Subject0", "Subject1").

        The file content is the email body (decoded to UTF-8 if bytes).

        :param search_str: IMAP search criteria (default: "ALL").
        :param charset: Character set for the search (default: None).
        :return: The list of mail content dicts (same as mail_content_list).
        """

**Example:**

.. code-block:: python

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX")
        exported = imap.output_all_mail_as_file()
        print(f"Exported {len(exported)} emails to files")

----

quit
~~~~

.. code-block:: python

    def quit(self):
        """
        Close the selected mailbox and log out from the IMAP server.

        Calls self.close() followed by self.logout().
        Catches and logs exceptions (e.g., if already disconnected).

        :return: None
        """

----

Global Instance
---------------

.. code-block:: python

    imap_instance: IMAPWrapper | None

A pre-created ``IMAPWrapper`` instance that attempts to connect to ``imap.gmail.com``
at import time. Set to ``None`` if the connection fails (e.g., no network).

Used internally by the JSON scripting executor.

----

Context Manager
---------------

``IMAPWrapper`` supports the ``with`` statement:

.. code-block:: python

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX")
        # ... read emails ...
    # imap.close() and imap.logout() are called automatically on exit

.. note::

    The context manager calls ``close()`` and ``logout()`` on exit,
    which is slightly different from the ``quit()`` method (which calls
    the same two methods but with exception handling).

----

Inherited Methods
-----------------

Since ``IMAPWrapper`` extends ``imaplib.IMAP4_SSL``, all standard IMAP methods are available:

- ``login(user, password)`` — Manual IMAP authentication
- ``select(mailbox, readonly)`` — Low-level mailbox selection
- ``search(charset, *criteria)`` — Low-level IMAP SEARCH
- ``fetch(message_set, message_parts)`` — Fetch message data
- ``store(message_set, command, flags)`` — Alter message flags
- ``copy(message_set, new_mailbox)`` — Copy messages
- ``expunge()`` — Permanently remove deleted messages
- ``list(directory, pattern)`` — List mailboxes
- ``close()`` — Close selected mailbox
- ``logout()`` — Log out from server

See `imaplib.IMAP4_SSL documentation <https://docs.python.org/3/library/imaplib.html#imaplib.IMAP4_SSL>`_
for the full list.

----

IMAP Search Syntax Reference
-----------------------------

The ``search_str`` parameter accepts IMAP SEARCH criteria as defined in
`RFC 3501 Section 6.4.4 <https://datatracker.ietf.org/doc/html/rfc3501#section-6.4.4>`_.

Common search criteria:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Criteria
     - Description
   * - ``ALL``
     - All messages in the mailbox
   * - ``UNSEEN``
     - Messages not marked as read
   * - ``SEEN``
     - Messages marked as read
   * - ``FLAGGED``
     - Messages with the \\Flagged flag (starred in Gmail)
   * - ``UNFLAGGED``
     - Messages without the \\Flagged flag
   * - ``FROM "address"``
     - Messages from the specified address
   * - ``TO "address"``
     - Messages sent to the specified address
   * - ``SUBJECT "text"``
     - Messages with the specified text in the subject
   * - ``BODY "text"``
     - Messages containing the specified text in the body
   * - ``SINCE "DD-Mon-YYYY"``
     - Messages with internal date on or after the specified date
   * - ``BEFORE "DD-Mon-YYYY"``
     - Messages with internal date before the specified date
   * - ``ON "DD-Mon-YYYY"``
     - Messages with internal date on the specified date
   * - ``LARGER n``
     - Messages larger than n bytes
   * - ``SMALLER n``
     - Messages smaller than n bytes

**Combining criteria:**

Multiple criteria can be combined (implicit AND):

.. code-block:: python

    # Unread emails from a specific sender
    imap.mail_content_list(search_str='FROM "user@example.com" UNSEEN')

    # Emails since a date with a specific subject
    imap.mail_content_list(search_str='SINCE "01-Jan-2025" SUBJECT "Report"')

----
