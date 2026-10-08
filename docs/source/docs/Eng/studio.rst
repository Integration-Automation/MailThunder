MailThunder Studio
==================

MailThunder Studio is a local page for looking at and trying what the mail API is set up to do: the
account, the templates, the triggers, the attachment policy, the project's mail layer and the logs.
It is served by the standard library, needs no extra package, and only ever talks to the core API
(:doc:`mail_api`), so it works the same on every provider.

.. code-block:: bash

   python -m je_mail_thunder.studio

.. code-block:: text

   MailThunder Studio: http://localhost:9947/#token=mL0n...
   Anyone with this address can use the mailbox while Studio runs. Ctrl+C stops it.

The page opens in the browser. The button in the corner switches between English and 中文.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Meaning
   * - ``--host HOST``
     - The loopback address to bind: ``localhost`` (the default) or a ``127.x.x.x`` address. Any other is refused
   * - ``--port PORT``
     - The port to bind (9947)
   * - ``--project DIR``
     - Use the mail layer of this project (:doc:`project_mail_layer`). This runs its ``mail/config.py``
       and ``mail/triggers.py``
   * - ``--no-browser``
     - Print the address without opening it

From Python:

.. code-block:: python

   from je_mail_thunder import Mail
   from je_mail_thunder.studio.server import start_studio

   server = start_studio(Mail(provider="microsoft_graph"))    # on a daemon thread
   print(server.url)
   ...
   server.stop()

----

Pages
-----

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Page
     - What it shows and does
   * - Dashboard
     - The account (provider, user, login mechanism; never the secret), each provider's health, how
       many templates, handlers and trigger backends there are, the newest audit entries, and a form
       that sends a mail
   * - Accounts
     - The account and the servers it reaches, the provider names that can be chosen, and a button
       that asks every provider to connect and log in
   * - Templates
     - The template directories and every template with its variables; a context can be typed in as
       JSON and rendered, without sending
   * - Triggers
     - The event names, the subscribed handlers with their filters, the trigger backends and their
       state, and a button that looks for new mail once
   * - Policies
     - The attachment policy, which can be changed for as long as Studio runs
   * - Projects
     - The mail layer of the project directory: which files and templates it has. Nothing of it is run
   * - Logs
     - The end of the MailThunder log file and the audit log
   * - Settings
     - Where MailThunder keeps its files, the registered providers and the versions it runs on

Studio attaches an audit log and a health monitor to the ``Mail`` it shows (:doc:`monitoring`), so
what is sent from the page is recorded like any other mail.

----

Security
--------

Studio can send mail and read logs, so it is built as a tool for the person at the keyboard:

- It speaks plain HTTP, so it serves only a loopback address (``localhost`` or ``127.x.x.x``) and refuses
  any other. To use it from another machine, forward the port through SSH
  (``ssh -L 9947:localhost:9947 host``).
- Every API request must carry a random token that is created when the server starts. The token is
  in the fragment of the printed address (after ``#``), which a browser does not send to any server
  or put in a ``Referer``.
- A request whose ``Host`` header is not the address Studio was started on is refused, so a web page
  open in the same browser cannot reach it through another name.
- The page loads no script or style from anywhere else (``Content-Security-Policy``), cannot be
  framed, and writes everything it shows as text, never as markup: a subject or a sender that arrived
  by mail cannot run in the browser.
- No answer contains a password, a token or a client secret.
- A mail sent from the page cannot name attachments, so the page cannot be used to mail a file of
  the machine. A request body is limited to 1 MiB.

Stop Studio when it is not in use. It is not meant to be left running on a shared machine or put
behind a public address.

----

The API Behind the Page
-----------------------

``je_mail_thunder.studio.api.StudioApi`` is what the page calls. Each method takes and returns
JSON-ready values, so it can be used from a test or another front end.

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - Request
     - ``StudioApi`` method
   * - ``GET /api/dashboard``
     - ``dashboard()``
   * - ``GET /api/accounts``, ``POST /api/accounts/check``
     - ``accounts()``, ``check_accounts()``
   * - ``GET /api/templates``, ``POST /api/templates/render``
     - ``templates()``, ``render_template({"name", "context"})``
   * - ``GET /api/triggers``, ``POST /api/triggers/poll``
     - ``triggers()``, ``poll_triggers()``
   * - ``GET /api/policies``, ``POST /api/policies``
     - ``policies()``, ``set_policy({...})``
   * - ``GET /api/projects``
     - ``projects()``
   * - ``GET /api/logs?lines=200``
     - ``logs({"lines": 200})``
   * - ``GET /api/settings``
     - ``settings()``
   * - ``POST /api/send``
     - ``send({"to", "cc", "bcc", "subject", "text", "html", "sender", "reply_to", "template", "context"})``

A request needs the header ``X-MailThunder-Token``. A MailThunder error is answered with HTTP 400 and
``{"error": "<exception name>", "message": "..."}``; a missing or wrong token, or a wrong ``Host``,
with 403.
