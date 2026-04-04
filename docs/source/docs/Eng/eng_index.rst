MailThunder English Documentation
==================================

Welcome to the MailThunder English documentation. This section covers how to use MailThunder
for sending and reading emails, authentication setup, scripting, and more.

.. toctree::
    :maxdepth: 4
    :caption: English Guides

    send_google_mail.rst
    read_google_mail.rst

----

Prerequisites
-------------

Before using MailThunder, ensure you have:

1. **Python 3.9+** installed
2. **MailThunder** installed via ``pip install je_mail_thunder``
3. **Email credentials** configured (see Authentication below)

Authentication Setup
--------------------

MailThunder supports two authentication methods. It tries the JSON config file first,
then falls back to environment variables.

**Method 1: JSON Config File**

Create ``mail_thunder_content.json`` in your current working directory:

.. code-block:: json

    {
        "user": "your_email@gmail.com",
        "password": "your_app_password"
    }

**Method 2: Environment Variables**

.. code-block:: python

    from je_mail_thunder import set_mail_thunder_os_environ

    set_mail_thunder_os_environ(
        mail_thunder_user="your_email@gmail.com",
        mail_thunder_user_password="your_app_password"
    )

Or set them in your shell:

.. code-block:: bash

    export mail_thunder_user="your_email@gmail.com"
    export mail_thunder_user_password="your_app_password"

.. note::

    **Gmail users:** You must use an `App Password <https://support.google.com/accounts/answer/185833>`_,
    not your regular Google account password. You also need to
    `enable IMAP <https://support.google.com/mail/answer/7126229>`_ in your Gmail settings.

----
