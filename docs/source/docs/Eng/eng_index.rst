Overview
========

**MailThunder** is a lightweight and flexible email automation tool for Python,
built on top of the standard library's ``smtplib`` and ``imaplib`` modules.

What is MailThunder?
--------------------

MailThunder wraps Python's ``smtplib.SMTP_SSL`` and ``imaplib.IMAP4_SSL`` to provide
a higher-level interface for common email tasks:

- **Sending** plain-text and HTML emails with file attachments via SMTP
- **Reading**, searching, and exporting emails via IMAP4
- **Automating** email workflows using a JSON-based scripting engine
- **Scaffolding** projects with pre-built templates
- **Controlling** email automation remotely via a TCP socket server

Architecture
------------

MailThunder is organized into the following core modules:

.. code-block:: text

   je_mail_thunder/
     __init__.py              # Public API exports
     __main__.py              # CLI entry point (argparse)
     smtp/
       smtp_wrapper.py        # SMTPWrapper — extends smtplib.SMTP_SSL
     imap/
       imap_wrapper.py        # IMAPWrapper — extends imaplib.IMAP4_SSL
     utils/
       executor/              # JSON scripting engine (Executor class)
       file_process/          # File utility (directory listing)
       json/                  # JSON file read/write with thread safety
       json_format/           # JSON reformatting
       logging/               # Logger instance (file + stream handlers)
       package_manager/       # Dynamic package loader (PackageManager)
       project/               # Project template scaffolding
         template/            # Template definitions (keyword JSON + executor Python)
       save_mail_user_content/# Auth config file + env var handling
       socket_server/         # TCP socket server (ThreadingMixIn)
       exception/             # Custom exception classes and error tags

How It Works
------------

1. **Authentication**: MailThunder reads credentials from ``mail_thunder_content.json``
   in the current working directory, or falls back to ``mail_thunder_user`` /
   ``mail_thunder_user_password`` environment variables.

2. **SMTP (Sending)**: ``SMTPWrapper`` connects to an SMTP server over SSL (default:
   ``smtp.gmail.com:465``). It provides methods to create ``EmailMessage`` or
   ``MIMEMultipart`` objects and send them in a single call.

3. **IMAP (Reading)**: ``IMAPWrapper`` connects to an IMAP server over SSL (default:
   ``imap.gmail.com``). It provides methods to select mailboxes, search emails using
   IMAP SEARCH syntax, parse results into Python dicts, and export them to files.

4. **Scripting Engine**: The ``Executor`` class maps command names to Python callables.
   JSON action files contain lists of ``["command_name", arguments]`` tuples that are
   executed sequentially. Custom functions and entire Python packages can be loaded
   at runtime.

5. **Logging**: All operations are logged to ``Mail_Thunder.log`` (file handler at
   INFO level) and ``stderr`` (stream handler at WARNING level).

Supported Platforms
-------------------

- **Python**: 3.9 or later
- **OS**: Windows, macOS, Linux
- **Dependencies**: None beyond the Python standard library

Next Steps
----------

- :doc:`installation` — Install MailThunder
- :doc:`authentication` — Configure email credentials
- :doc:`send_google_mail` — Send your first email
- :doc:`read_google_mail` — Read emails from your inbox
- :doc:`scripting_engine` — Automate workflows with JSON scripts
