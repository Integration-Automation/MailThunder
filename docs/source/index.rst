.. MailThunder documentation master file

MailThunder
===========

.. image:: https://img.shields.io/pypi/v/je_mail_thunder
   :target: https://pypi.org/project/je-mail-thunder/
   :alt: PyPI

.. image:: https://img.shields.io/badge/python-3.9%2B-blue.svg
   :target: https://www.python.org/
   :alt: Python 3.9+

.. image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://github.com/Integration-Automation/MailThunder/blob/main/LICENSE
   :alt: MIT License

**MailThunder** is a lightweight and flexible email automation tool for Python.
It wraps Python's ``smtplib.SMTP_SSL`` and ``imaplib.IMAP4_SSL`` protocols, provides a
JSON-based scripting engine and project templates, and makes sending, receiving, and
managing email content effortless.

----

Key Features
------------

- **SMTP support** — Send emails via SSL with Gmail (default) or any SMTP provider
- **IMAP4 support** — Read, search, and export emails via IMAP4 SSL
- **Attachment handling** — Automatically detect MIME types for text, image, audio, and binary files
- **HTML email** — Send HTML-formatted emails with attachments
- **JSON scripting engine** — Automate email workflows using JSON action files
- **Project templates** — Scaffold projects with pre-built keyword and executor templates
- **Socket server** — Control MailThunder remotely via TCP socket commands
- **Package manager** — Dynamically load Python packages into the scripting executor
- **Environment variable auth** — Authenticate via config file or OS environment variables
- **Context manager support** — Use ``with`` statement for both SMTP and IMAP connections
- **Command-line interface** — Execute action files, directories, or JSON strings from the terminal
- **Built-in logging** — All operations are logged to ``Mail_Thunder.log``

----

Quick Example
-------------

**Send an email:**

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   with SMTPWrapper() as smtp:
       smtp.later_init()
       smtp.create_message_and_send(
           message_content="Hello from MailThunder!",
           message_setting_dict={
               "Subject": "Test Email",
               "From": "sender@gmail.com",
               "To": "receiver@gmail.com"
           }
       )

**Read emails:**

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       imap.select_mailbox("INBOX")
       for mail in imap.mail_content_list():
           print(mail["SUBJECT"], mail["FROM"])

----

.. toctree::
   :maxdepth: 3
   :caption: English Documentation

   docs/Eng/eng_index
   docs/Eng/installation
   docs/Eng/authentication
   docs/Eng/send_google_mail
   docs/Eng/read_google_mail
   docs/Eng/scripting_engine
   docs/Eng/project_templates
   docs/Eng/cli
   docs/Eng/socket_server
   docs/Eng/package_manager
   docs/Eng/logging
   docs/Eng/exceptions

.. toctree::
   :maxdepth: 3
   :caption: 繁體中文文件

   docs/Zh/zh_index
   docs/Zh/installation
   docs/Zh/authentication
   docs/Zh/send_google_mail
   docs/Zh/read_google_mail
   docs/Zh/scripting_engine
   docs/Zh/project_templates
   docs/Zh/cli
   docs/Zh/socket_server
   docs/Zh/package_manager
   docs/Zh/logging
   docs/Zh/exceptions

.. toctree::
   :maxdepth: 3
   :caption: API Reference

   docs/API/api_index
   docs/API/smtp_api
   docs/API/imap_api
   docs/API/executor_api
   docs/API/utils_api

----

Links
-----

* `GitHub Repository <https://github.com/Integration-Automation/MailThunder>`_
* `PyPI Package <https://pypi.org/project/je-mail-thunder/>`_
* `Project Kanban <https://github.com/orgs/Integration-Automation/projects/2/views/1>`_
