Authentication
==============

MailThunder supports two authentication methods. When ``later_init()`` or
``try_to_login_with_env_or_content()`` is called, it tries the JSON config file
first, then falls back to environment variables.

Authentication Flow
-------------------

.. code-block:: text

   later_init() called
       │
       ▼
   Read mail_thunder_content.json from cwd
       │
       ├── File found and has "user" + "password"
       │       │
       │       ▼
       │   Login with file credentials ─── Success ──▶ Done (login_state = True)
       │                                │
       │                                └── Failure ──▶ Log error
       │
       └── File not found or invalid
               │
               ▼
           Read env vars: mail_thunder_user + mail_thunder_user_password
               │
               ├── Env vars set
               │       │
               │       ▼
               │   Login with env credentials ─── Success ──▶ Done (login_state = True)
               │                                  │
               │                                  └── Failure ──▶ Log error
               │
               └── Env vars not set ──▶ Log error

Method 1: JSON Config File
---------------------------

Create a file named ``mail_thunder_content.json`` in your **current working directory**:

.. code-block:: json

   {
     "user": "your_email@gmail.com",
     "password": "your_app_password"
   }

.. warning::

   This file contains your email credentials in plain text. Do not commit it to
   version control. Add ``mail_thunder_content.json`` to your ``.gitignore``.

**How it works internally:**

1. ``read_output_content()`` checks if ``mail_thunder_content.json`` exists in ``Path.cwd()``
2. If found, it reads the JSON and updates ``mail_thunder_content_data_dict``
3. The ``user`` and ``password`` values are passed to ``smtplib.SMTP_SSL.login()``
   or ``imaplib.IMAP4_SSL.login()``

Method 2: Environment Variables
-------------------------------

**Option A — Set via Python at runtime:**

.. code-block:: python

   from je_mail_thunder import set_mail_thunder_os_environ

   set_mail_thunder_os_environ(
       mail_thunder_user="your_email@gmail.com",
       mail_thunder_user_password="your_app_password"
   )

This calls ``os.environ.update()`` to set two environment variables:

- ``mail_thunder_user``
- ``mail_thunder_user_password``

**Option B — Set in your shell before running the script:**

.. code-block:: bash

   # Linux / macOS
   export mail_thunder_user="your_email@gmail.com"
   export mail_thunder_user_password="your_app_password"

.. code-block:: batch

   :: Windows CMD
   set mail_thunder_user=your_email@gmail.com
   set mail_thunder_user_password=your_app_password

.. code-block:: powershell

   # Windows PowerShell
   $env:mail_thunder_user = "your_email@gmail.com"
   $env:mail_thunder_user_password = "your_app_password"

**Retrieve current env var values:**

.. code-block:: python

   from je_mail_thunder import get_mail_thunder_os_environ

   creds = get_mail_thunder_os_environ()
   # Returns: {"mail_thunder_user": "...", "mail_thunder_user_password": "..."}

Method 3: Manual Credential Injection
--------------------------------------

You can directly update the global credential dict before calling login:

.. code-block:: python

   from je_mail_thunder import mail_thunder_content_data_dict

   mail_thunder_content_data_dict.update({
       "user": "your_email@gmail.com",
       "password": "your_app_password",
   })

This is useful for programmatic scenarios where credentials come from a vault,
database, or other external source.

Gmail-Specific Setup
--------------------

If you are using Gmail, there are two extra requirements:

1. **Use an App Password** — Gmail does not allow login with your regular Google
   account password. You must generate an App Password:

   - Go to `Google App Passwords <https://myaccount.google.com/apppasswords>`_
   - Select "Mail" and your device
   - Copy the generated 16-character password
   - Use this as the ``password`` value

2. **Enable IMAP** (for reading emails) — By default, IMAP access is disabled in Gmail:

   - Go to Gmail Settings > See all settings > Forwarding and POP/IMAP
   - Under "IMAP access", select "Enable IMAP"
   - Save changes

.. note::

   App Passwords require 2-Step Verification to be enabled on your Google account.

Checking Login State (SMTP)
----------------------------

``SMTPWrapper`` tracks authentication state via the ``login_state`` property:

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   smtp = SMTPWrapper()
   print(smtp.login_state)  # False

   success = smtp.try_to_login_with_env_or_content()
   print(smtp.login_state)  # True if login succeeded
   print(success)           # True or False

Via JSON Scripting Engine
-------------------------

Set authentication credentials in a JSON action file:

.. code-block:: json

   {
     "auto_control": [
       ["MT_set_mail_thunder_os_environ", {
         "mail_thunder_user": "your_email@gmail.com",
         "mail_thunder_user_password": "your_app_password"
       }],
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
         "message_content": "Hello!",
         "message_setting_dict": {
           "Subject": "Test",
           "From": "your_email@gmail.com",
           "To": "receiver@gmail.com"
         }
       }],
       ["smtp_quit"]
     ]
   }
