IMAPWrapper API
===============

**Module:** ``je_mail_thunder.imap.imap_wrapper``

``IMAPWrapper`` extends ``imaplib.IMAP4_SSL`` to provide a high-level interface for
reading, searching, and exporting emails via the IMAP4 protocol.

----

Class Definition
----------------

.. code-block:: python

   class IMAPWrapper(imaplib.IMAP4_SSL):
       """
       IMAP wrapper with auto-login, search, and export utilities.

       Inherits all methods from imaplib.IMAP4_SSL.
       Supports context manager (with statement).
       """

       def __init__(self, host: str = "imap.gmail.com"):
           ...

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Default
     - Description
   * - ``host``
     - ``"imap.gmail.com"``
     - IMAP server hostname (SSL)

----

Methods
-------

later_init()
~~~~~~~~~~~~

.. code-block:: python

   def later_init(self) -> None

Attempt to log in to the IMAP server. Calls ``try_to_login_with_env_or_content()``
internally. Catches and logs all exceptions without raising.

----

try_to_login_with_env_or_content()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def try_to_login_with_env_or_content(self) -> None

Attempt to log in using credentials from the config file or environment variables.

**Authentication flow:**

1. Read ``mail_thunder_content.json`` from ``Path.cwd()``
2. If valid ``user`` + ``password`` keys found → ``self.login(user, password)``
3. Else read ``mail_thunder_user`` + ``mail_thunder_user_password`` env vars
4. If env vars set → ``self.login(user, password)``
5. On failure → log error with ``mail_thunder_content_login_failed`` tag

----

select_mailbox()
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def select_mailbox(
       self,
       mailbox: str = "INBOX",
       readonly: bool = False
   ) -> bool

Select a mailbox for subsequent operations.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Default
     - Description
   * - ``mailbox``
     - ``"INBOX"``
     - Mailbox name. Common: ``"INBOX"``, ``"Sent"``, ``"Drafts"``, ``"Trash"``.
       Gmail: ``"[Gmail]/All Mail"``, ``"[Gmail]/Starred"``, ``"[Gmail]/Spam"``.
   * - ``readonly``
     - ``False``
     - If ``True``, opens in read-only mode (messages not marked as read)

**Returns:** ``True`` if IMAP status is ``"OK"``, ``False`` otherwise.

----

search_mailbox()
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def search_mailbox(
       self,
       search_str: [str, list] = "ALL",
       charset: str = None
   ) -> list

Search the selected mailbox and return raw mail details.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Default
     - Description
   * - ``search_str``
     - ``"ALL"``
     - IMAP search criteria (RFC 3501 Section 6.4.4)
   * - ``charset``
     - ``None``
     - Character set for the search

**Returns:** A list of ``[response, decode_info, message]`` tuples:

- ``response`` — IMAP response status string (e.g., ``"OK"``)
- ``decode_info`` — Raw RFC822 decode header bytes (e.g., ``b'1 (RFC822 {12345}'``)
- ``message`` — ``email.message.Message`` object (parsed with ``email.policy.default``)

**Internally:** For each matching email, calls ``self.fetch(num, "(RFC822)")`` and
parses the result with ``email.message_from_bytes()``.

----

mail_content_list()
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def mail_content_list(
       self,
       search_str: [str, list] = "ALL",
       charset: str = None
   ) -> List[Dict[str, Union[str, bytes]]]

Get all mail content as a list of parsed dictionaries.

**Parameters:** Same as ``search_mailbox()``.

**Returns:** A list of dicts, one per email:

.. code-block:: python

   {
       "SUBJECT": str,   # Decoded subject line
       "FROM": str,      # Sender address
       "TO": str,        # Recipient address
       "BODY": str       # Body text (first part for multipart emails)
   }

**Body extraction logic:**

- If the email ``is_multipart()``: extracts the payload of the first part
- Otherwise: extracts the full payload
- Decodes using ``email.header.decode_header()``

----

output_all_mail_as_file()
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def output_all_mail_as_file(
       self,
       search_str: [str, list] = "ALL",
       charset: str = None
   ) -> List[Dict[str, Union[str, bytes]]]

Export all matching emails to local files.

**Parameters:** Same as ``search_mailbox()``.

**Returns:** The same list of mail content dicts as ``mail_content_list()``.

**File naming logic:**

- Filename = ``{subject}{counter}`` (e.g., ``My Subject0``, ``My Subject1``)
- Counter starts at 0 and increments for duplicate subjects
- Files are created in the current working directory
- Body is written as UTF-8 text (decoded from bytes if necessary)

----

quit()
~~~~~~

.. code-block:: python

   def quit(self) -> None

Close the selected mailbox and log out from the IMAP server.
Calls ``self.close()`` followed by ``self.logout()``.
Catches and logs exceptions.

----

Context Manager
---------------

``IMAPWrapper`` supports the ``with`` statement. ``close()`` and ``logout()``
are called on exit:

.. code-block:: python

   with IMAPWrapper() as imap:
       imap.later_init()
       imap.select_mailbox("INBOX")
       emails = imap.mail_content_list()
   # imap.close() and imap.logout() called automatically

.. note::

   The context manager calls ``close()`` + ``logout()`` directly (without exception
   handling), while ``quit()`` wraps them in a try/except. For robustness, prefer
   using ``quit()`` explicitly or the context manager.

----

Global Instance
---------------

.. code-block:: python

   imap_instance: IMAPWrapper | None

A pre-created ``IMAPWrapper`` instance that attempts to connect to ``imap.gmail.com``
at import time. Set to ``None`` if the connection fails.
Used internally by the JSON scripting executor.

----

Inherited from IMAP4_SSL
-------------------------

All standard ``imaplib.IMAP4_SSL`` methods are available:

- ``login(user, password)`` — Manual authentication
- ``select(mailbox, readonly)`` — Low-level mailbox selection
- ``search(charset, *criteria)`` — Low-level IMAP SEARCH
- ``fetch(message_set, message_parts)`` — Fetch message data
- ``store(message_set, command, flags)`` — Alter message flags
- ``copy(message_set, new_mailbox)`` — Copy messages
- ``expunge()`` — Permanently remove deleted messages
- ``list(directory, pattern)`` — List available mailboxes
- ``close()`` — Close selected mailbox
- ``logout()`` — Log out from server

See `imaplib documentation <https://docs.python.org/3/library/imaplib.html>`_
for the full reference.

----

IMAP Search Criteria Quick Reference
-------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Criteria
     - Description
   * - ``ALL``
     - All messages
   * - ``UNSEEN``
     - Unread messages
   * - ``SEEN``
     - Read messages
   * - ``FLAGGED``
     - Flagged/starred messages
   * - ``FROM "addr"``
     - Messages from sender
   * - ``TO "addr"``
     - Messages to recipient
   * - ``SUBJECT "text"``
     - Subject contains text
   * - ``BODY "text"``
     - Body contains text
   * - ``SINCE "DD-Mon-YYYY"``
     - On or after date
   * - ``BEFORE "DD-Mon-YYYY"``
     - Before date
   * - ``LARGER n``
     - Larger than n bytes
   * - ``SMALLER n``
     - Smaller than n bytes

Multiple criteria are combined with implicit AND:

.. code-block:: python

   imap.mail_content_list(search_str='FROM "user@example.com" UNSEEN')
