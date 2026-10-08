Authentication
==============

MailThunder logs in with a password or with OAuth2. When ``later_init()`` or
``try_to_login_with_env_or_content()`` is called, it uses the OAuth2 settings if
there are any, else the user and password: the JSON config file first, then the
environment variables.

Authentication Flow
-------------------

.. code-block:: text

   later_init() called
       │
       ▼
   OAuth2 settings? ("oauth2" in mail_thunder_content.json, else mail_thunder_oauth2_* env vars)
       │
       ├── Found ──▶ access token (cached, or refreshed at the token endpoint) ──▶ AUTH XOAUTH2
       │
       ▼ None
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

Method 3: OAuth2 (Google and Microsoft)
---------------------------------------

Google and Microsoft are retiring password logins for mail. With OAuth2, MailThunder exchanges a refresh token
for a short-lived access token at the provider's token endpoint (standard library only, ``https`` required),
caches it until a minute before it expires, and logs in with SASL ``XOAUTH2``. OAuth2 settings, when present,
are used instead of a password. Get the client ID, client secret and refresh token once through the provider's
consent flow (a Google Cloud OAuth client, or a Microsoft Entra app registration); MailThunder does not run it.

**In** ``mail_thunder_content.json`` (the ``user`` may also sit inside ``oauth2``):

.. code-block:: json

   {
     "user": "you@example.com",
     "oauth2": {
       "provider": "microsoft",
       "client_id": "...",
       "client_secret": "...",
       "refresh_token": "...",
       "tenant": "common"
     }
   }

**Or in the environment:** ``mail_thunder_user`` plus ``mail_thunder_oauth2_provider``,
``mail_thunder_oauth2_client_id``, ``mail_thunder_oauth2_client_secret`` and ``mail_thunder_oauth2_refresh_token``;
optionally ``mail_thunder_oauth2_tenant``, ``mail_thunder_oauth2_scope``, ``mail_thunder_oauth2_token_url``, or
``mail_thunder_oauth2_access_token`` to use a token as given.

.. list-table::
   :header-rows: 1

   * - Provider
     - SMTP
     - IMAP
     - Scope it asks for
   * - ``google`` (default)
     - ``smtp.gmail.com:465``, implicit TLS (``SMTPWrapper``)
     - ``imap.gmail.com``
     - ``https://mail.google.com/``
   * - ``microsoft``
     - ``smtp.office365.com:587``, STARTTLS (``SMTPStartTLSWrapper``)
     - ``outlook.office365.com``
     - ``SMTP.Send`` and ``IMAP.AccessAsUser.All`` on ``https://outlook.office.com/``, ``offline_access``

``smtp_instance`` and ``imap_instance`` (and so the ``MT_smtp_*`` / ``MT_imap_*`` commands) connect to the
servers of the provider the settings name. ``SMTPStartTLSWrapper`` upgrades with ``STARTTLS`` before anything
else is sent and refuses a server that does not offer it. Another provider works with ``token_url`` (and
``scope``); create the wrappers with its hosts. Client secrets and tokens never appear in log lines, error
messages or the settings' ``repr``.

.. code-block:: python

   from je_mail_thunder import OAuth2Settings, SMTPStartTLSWrapper, oauth2_token_cache

   settings = OAuth2Settings(user="you@contoso.com", provider="microsoft", client_id="...",
                             client_secret="...", refresh_token="...", tenant="contoso.onmicrosoft.com")
   with SMTPStartTLSWrapper() as smtp:
       smtp.oauth2_login(settings.user, oauth2_token_cache.access_token(settings))

Authentication Objects
----------------------

Each way of logging in is an ``Authentication`` object, so the code that connects does not care
which one it is given.

.. list-table::
   :header-rows: 1
   :widths: 38 42 20

   * - Class
     - Logs in with
     - Works for
   * - ``PasswordAuth(user, password)``
     - The account's password
     - SMTP, IMAP
   * - ``AppPasswordAuth(user, app_password)``
     - An app password (Google, Yahoo, iCloud). The spaces it is shown with are dropped
     - SMTP, IMAP
   * - ``OAuth2Auth(settings)``
     - An OAuth2 access token, as ``Authorization: Bearer ...``
     - HTTP APIs
   * - ``XOAUTH2Auth(settings)``
     - The same token, as SASL ``XOAUTH2``
     - SMTP, IMAP, HTTP APIs

.. code-block:: python

   from je_mail_thunder import AppPasswordAuth, OAuth2Settings, SMTPWrapper, XOAUTH2Auth, resolve_authentication

   auth = AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop")
   auth = XOAUTH2Auth(OAuth2Settings(user="you@gmail.com", client_id="...",
                                     client_secret="...", refresh_token="..."))
   auth = resolve_authentication()   # what the config file or the environment holds, or None

   with SMTPWrapper() as smtp:
       auth.login(smtp)              # the same call logs an IMAPWrapper in

- ``auth.login(client)`` logs an SMTP or IMAP wrapper in.
- ``auth.authorization()`` gives the value of an HTTP ``Authorization`` header.
- ``auth.user`` is the account's address and ``auth.mechanism`` the mechanism's name
  (``"password"``, ``"app-password"``, ``"oauth2"``, ``"xoauth2"``).

A mechanism that cannot do what it is asked raises ``MailThunderAuthenticationException``:
a password has no HTTP authorization, and plain ``OAuth2Auth`` has no mail server login
(use ``XOAUTH2Auth``). ``MailThunderOAuth2Exception`` is now a subclass of it.

``settings`` is an ``OAuth2Settings`` (see Method 3). The token comes from the shared
``oauth2_token_cache`` unless the class is given its own ``token_cache``, and is refreshed a
minute before it expires.

``resolve_authentication()`` returns the login of the config file or the environment: an
``XOAUTH2Auth`` when there are OAuth2 settings, else a ``PasswordAuth``, else ``None``. It
raises ``MailThunderOAuth2Exception`` when the OAuth2 settings it finds are incomplete.

Passwords and tokens never appear in a ``repr``, a log line or an exception message.

Credentials From Code
---------------------

The login reads ``mail_thunder_content.json`` or the environment, not ``mail_thunder_content_data_dict``: that
dict is what ``write_output_content()`` writes to the file. To log in with credentials from a vault or a
database, set the environment variables (``set_mail_thunder_os_environ``), or fill the dict and call
``write_output_content()`` (the file then holds them in plain text).

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
     "mail_thunder": [
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
       ["MT_smtp_quit"]
     ]
   }
