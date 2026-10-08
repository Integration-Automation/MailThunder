Microsoft Graph
===============

The ``microsoft_graph`` provider reaches a Microsoft 365 mailbox through the Microsoft Graph API
instead of SMTP and IMAP. The ``Mail`` calls stay the same; only the provider name changes.

.. code-block:: python

   from je_mail_thunder import Mail, OAuth2Auth, OAuth2Settings

   auth = OAuth2Auth(OAuth2Settings(
       user="you@contoso.com", provider="microsoft", tenant="contoso.onmicrosoft.com",
       client_id="...", client_secret="...", refresh_token="...",
   ))
   with Mail(provider="microsoft_graph", auth=auth) as mail:
       mail.send(to="qa@example.com", subject="Report", html="<b>42 passed</b>", attachments=["report.pdf"])
       for message in mail.get_messages(limit=10, unread_only=True):
           print(message.sender, message.subject)

----

Choosing It
-----------

- In code: ``Mail(provider="microsoft_graph")`` or ``MailAccount(provider="microsoft_graph")``.
- For ``Mail()`` and the ``MT_mail_*`` commands: ``"mail_provider": "microsoft_graph"`` in
  ``mail_thunder_content.json``, or the environment variable ``mail_thunder_mail_provider``.

.. code-block:: json

   {
     "user": "you@contoso.com",
     "mail_provider": "microsoft_graph",
     "oauth2": {
       "provider": "microsoft",
       "tenant": "contoso.onmicrosoft.com",
       "client_id": "...",
       "client_secret": "...",
       "refresh_token": "..."
     }
   }

``microsoft`` keeps meaning Microsoft 365 over SMTP and IMAP. ``mail_provider`` names any registered
provider, so it also selects ``smtp`` or a provider of your own.

----

Signing In
----------

Graph needs OAuth2: a password cannot authorise it. The app registration in Microsoft Entra needs the
delegated permissions ``Mail.Send`` and ``Mail.ReadWrite`` (and ``offline_access`` for the refresh token).

The OAuth2 settings are the ones described in :doc:`authentication`. When they name no ``scope``,
the provider asks for the token with the Graph scopes
(``https://graph.microsoft.com/Mail.Send``, ``https://graph.microsoft.com/Mail.ReadWrite``,
``offline_access``); a ``scope`` or an ``access_token`` given in the settings is used as it is.
The refresh token must come from a consent that included the Graph permissions.

----

What It Does
------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Call
     - Over Graph
   * - ``send``
     - One ``POST /me/sendMail`` when the attachments are small. Otherwise a draft is created, each
       attachment is added to it (through an upload session above 3 MiB) and the draft is sent
   * - ``create_draft``
     - ``POST /me/messages``, or into the folder that is named. Returns the draft's id
   * - ``get_messages``
     - ``GET /me/mailFolders/{folder}/messages``, newest first, a page of 25 at a time. ``query`` is an
       OData ``$filter`` expression, e.g. ``from/emailAddress/address eq 'ci@example.com'``
   * - ``get_message`` / ``delete_message``
     - ``GET`` / ``DELETE /me/messages/{id}``; ``message_id`` is the Graph id

Folders are named ``INBOX``, ``Drafts``, ``Sent``, ``Deleted Items``, ``Junk`` or ``Archive``, or by
their display name. Differences from SMTP worth knowing:

- a message has one body: with both ``text`` and ``html``, Graph gets the HTML;
- custom headers must start with ``X-``;
- a ``sender`` other than the account needs the *send as* permission in Microsoft 365.

Errors follow the rest of the API: a refused token (HTTP 401 or 403) is a
``MailThunderAuthenticationException``, an unreachable Graph a ``MailThunderConnectionException``, a
refused message a ``MailThunderSendException``, anything else a ``MailThunderProviderException``
with Graph's error code and message. Requests go only to ``https://graph.microsoft.com``.

----

Triggers
--------

``mail.watch()`` on a Graph account uses ``GraphPollingBackend``, which after the first look asks
only for the mail received since.

``GraphWebhookBackend`` lets Graph announce new mail instead (change notifications). Graph posts to a
public HTTPS address, so the backend's listener, which binds ``localhost:9946``, has to sit behind a
reverse proxy or a tunnel:

.. code-block:: python

   from je_mail_thunder import GraphWebhookBackend, Mail

   mail = Mail(provider="microsoft_graph")
   mail.on("message_received", lambda event: print(event.message.subject))
   provider = mail.providers[0]
   backend = mail.triggers.add(GraphWebhookBackend(provider, "https://hooks.example.com/mail"))
   backend.start()      # opens the listener, subscribes, and renews the subscription while it runs
   ...
   mail.close()         # removes the subscription and closes the listener

The backend answers Graph's validation request, and ignores any notification that does not carry the
random secret (``clientState``) and the id of its own subscription, since anyone can post to a
public address. The notification only names the message; the backend then reads it through Graph.
