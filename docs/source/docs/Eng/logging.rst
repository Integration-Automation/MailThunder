Logging
=======

MailThunder uses Python's standard ``logging`` module to log all operations.
Logs are useful for debugging authentication issues, tracking sent/received emails,
and monitoring the scripting executor.

----

Logger Configuration
--------------------

The logger is configured in ``je_mail_thunder.utils.logging.loggin_instance``:

.. code-block:: python

   import logging
   import sys

   mail_thunder_logger = logging.getLogger("Mail Thunder")
   mail_thunder_logger.setLevel(logging.INFO)

**Logger name:** ``"Mail Thunder"``

----

Log Handlers
------------

MailThunder registers two log handlers:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Handler
     - Output
     - Level
     - Description
   * - File handler
     - ``Mail_Thunder.log``
     - ``INFO``
     - Logs all operations (INFO and above) to a file in the current working directory
   * - Stream handler
     - ``stderr``
     - ``WARNING``
     - Only prints warnings and errors to the console

**Log format:**

.. code-block:: text

   %(asctime)s | %(name)s | %(levelname)s | %(message)s

**Example log entries:**

.. code-block:: text

   2025-01-15 10:30:00,123 | Mail Thunder | INFO | MT_smtp_later_init
   2025-01-15 10:30:01,456 | Mail Thunder | INFO | smtp_create_message_and_send, message_content: Hello!, message_setting_dict: {...}
   2025-01-15 10:30:01,789 | Mail Thunder | INFO | SMTP quit
   2025-01-15 10:30:02,012 | Mail Thunder | ERROR | smtp_try_to_login_with_env_or_content, failed: SMTPAuthenticationError(...)

----

What Gets Logged
----------------

**SMTP operations (INFO level):**

- ``MT_smtp_later_init`` — SMTP login attempt
- ``smtp_create_message`` — Message creation with content and settings
- ``smtp_create_message_with_attach`` — Attachment message creation
- ``smtp_create_message_and_send`` — Send with content details
- ``smtp_create_message_with_attach_and_send`` — Send with attachment details
- ``smtp_try_to_login_with_env_or_content`` — Login attempt
- ``SMTP quit`` — Disconnection

**IMAP operations (INFO level):**

- ``MT_imap_later_init`` — IMAP login attempt
- ``imap_try_to_login_with_env_or_content`` — Login attempt
- ``imap_select_mailbox`` — Mailbox selection with name and readonly flag
- ``imap_search_mailbox`` — Search with criteria
- ``imap_mail_content_list`` — Content list retrieval
- ``MT_imap_quit`` — Disconnection

**Executor operations (INFO level):**

- ``Execute {action}`` — Each action as it is executed
- ``Add command to executor {command_dict}`` — Custom command registration

**Package manager operations (INFO level):**

- ``add_package_to_executor, package: {package}`` — Package loading

**Error logging (ERROR level):**

All exceptions in SMTP, IMAP, executor, and package manager operations are caught
and logged at ERROR level with the full exception representation.

----

Log File Location
-----------------

The log file ``Mail_Thunder.log`` is created in the **current working directory**
when the module is first imported. The file is opened in ``w+`` mode, meaning
it is overwritten on each program run.

.. note::

   Since the file handler uses ``mode="w+"``, logs from previous runs are not
   preserved. If you need persistent logging, consider configuring a custom
   handler or copying the log file after each run.

----

Accessing the Logger
--------------------

You can access MailThunder's logger to add custom handlers or change the level:

.. code-block:: python

   from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger

   # Change log level
   mail_thunder_logger.setLevel(logging.DEBUG)

   # Add a custom handler
   custom_handler = logging.StreamHandler()
   custom_handler.setLevel(logging.DEBUG)
   mail_thunder_logger.addHandler(custom_handler)

   # Now all debug messages will be printed
