MailThunder
===========

.. image:: https://img.shields.io/pypi/v/je_mail_thunder
   :target: https://pypi.org/project/je-mail-thunder/

.. image:: https://img.shields.io/badge/python-3.9%2B-blue.svg
   :target: https://www.python.org/

.. image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://github.com/Integration-Automation/MailThunder/blob/main/LICENSE

**MailThunder** is a lightweight and flexible email automation tool for Python.
It wraps SMTP and IMAP4 protocols, provides a JSON-based scripting engine and project templates,
and makes sending, receiving, and managing email content effortless.

----

Features
--------

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
- **Logging** — Built-in logging for all operations

----

Installation
------------

**Stable release:**

.. code-block:: bash

    pip install je_mail_thunder

**Development release:**

.. code-block:: bash

    pip install je_mail_thunder_dev

**Requirements:** Python 3.9 or later. No additional dependencies beyond the Python standard library.

----

Quick Start
-----------

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
        emails = imap.mail_content_list()
        for mail in emails:
            print(mail["SUBJECT"], mail["FROM"])

----

Documentation
-------------

.. toctree::
    :maxdepth: 4
    :caption: Contents

    docs/Eng/eng_index.rst
    docs/Zh/zh_index.rst
    docs/API/api_index.rst

----

Links
-----

* `GitHub Repository <https://github.com/Integration-Automation/MailThunder>`_
* `PyPI Package <https://pypi.org/project/je-mail-thunder/>`_
* `Project Kanban <https://github.com/orgs/Integration-Automation/projects/2/views/1>`_

----
