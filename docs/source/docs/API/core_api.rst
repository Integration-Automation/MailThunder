Core Mail API
=============

The provider-agnostic layer of MailThunder. Everything on this page is exported from the
top-level ``je_mail_thunder`` package unless a module is named.

----

Attachments
-----------

**Modules:** ``je_mail_thunder.attachments.attachment``, ``je_mail_thunder.attachments.policy``,
``je_mail_thunder.attachments.validator``, ``je_mail_thunder.attachments.mime``

Attachment
~~~~~~~~~~

.. code-block:: python

   @dataclass(frozen=True)
   class Attachment:
       filename: str
       content_type: str = "application/octet-stream"
       path: Optional[str] = None
       content: Optional[bytes] = None

A file that goes with a message. One to send names a ``path``, read only when the message is
handed to the provider. One that arrived holds its bytes in ``content`` (kept out of the ``repr``).
Without a ``filename``, or with neither ``path`` nor ``content``, it raises
``MailThunderAttachmentException``.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Member
     - Description
   * - ``Attachment.from_path(path, filename=None, content_type=None)``
     - An attachment to send. ``filename`` defaults to the file's name and ``content_type`` to
       the type its name suggests
   * - ``Attachment.of(source)``
     - ``source`` itself when it is an ``Attachment``, else ``from_path(source)``; anything but a
       path raises ``MailThunderAttachmentException``
   * - ``size``
     - Size in bytes. Raises ``AttachmentNotFound`` when the file to send does not exist
   * - ``read()``
     - The attachment's bytes. Raises ``AttachmentNotFound`` when the file cannot be read
   * - ``save(directory)``
     - Write the attachment into ``directory`` under a safe name and return the path
   * - ``describe()``
     - ``{"filename": ..., "content_type": ..., "size": ...}``, for logs and action records

AttachmentPolicy
~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass(frozen=True)
   class AttachmentPolicy:
       max_file_size: Optional[int] = None
       max_total_size: Optional[int] = None
       max_count: Optional[int] = None
       allowed_extensions: Optional[FrozenSet[str]] = None
       allowed_mime_types: Optional[FrozenSet[str]] = None

The limits attachments are checked against. ``None`` lifts a limit. Extensions are stored
lower-cased with their dot, MIME types lower-cased. An invalid limit or type set raises
``MailThunderAttachmentException``.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Member
     - Description
   * - ``allows_extension(filename)``
     - ``True`` when the file name's last extension is allowed
   * - ``allows_mime_type(content_type)``
     - ``True`` when the type, or its ``<main type>/*``, is allowed
   * - ``DEFAULT_ATTACHMENT_POLICY``
     - ``AttachmentPolicy(max_file_size=25 MiB, max_total_size=25 MiB)``

validate_attachments()
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def validate_attachments(attachments: Iterable[Attachment], policy: AttachmentPolicy) -> int

Check a message's attachments against a policy, in the order count, existence, size, extension,
MIME type, total size.

**Returns:** the attachments' total size in bytes.

**Raises:** ``AttachmentCountExceeded``, ``AttachmentNotFound``, ``AttachmentTooLarge``,
``AttachmentTypeNotAllowed`` or ``TotalAttachmentSizeExceeded`` (all
``MailThunderAttachmentException``), logged before it is raised.

MIME Helpers
~~~~~~~~~~~~

**Module:** ``je_mail_thunder.attachments.mime`` (not re-exported from the package)

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Function
     - Description
   * - ``guess_content_type(filename)``
     - The MIME type a file name suggests; ``application/octet-stream`` when it suggests none
       or a compressed encoding (``report.txt.gz``)
   * - ``file_extension(filename)``
     - The last extension, lower-cased and with its dot (``""`` without one)
   * - ``safe_filename(filename, fallback="attachment")``
     - A bare file name that cannot leave the directory it is written to

----

Authentication
--------------

**Modules:** ``je_mail_thunder.auth.base``, ``je_mail_thunder.auth.password``,
``je_mail_thunder.auth.oauth2``, ``je_mail_thunder.auth.xoauth2``

Authentication
~~~~~~~~~~~~~~

.. code-block:: python

   class Authentication(ABC):
       def __init__(self, user: str) -> None: ...

One way of logging an account in. A mechanism overrides what it can do; the rest raises
``MailThunderAuthenticationException``.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Member
     - Description
   * - ``user``
     - The account's mail address
   * - ``mechanism``
     - The mechanism's name, for logs and error messages (abstract)
   * - ``login(client)``
     - Log an SMTP or IMAP wrapper in
   * - ``authorization()``
     - The value of the HTTP ``Authorization`` header

Mechanisms
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Class
     - ``mechanism``
     - Notes
   * - ``PasswordAuth(user, password)``
     - ``password``
     - ``login`` calls ``client.login(user, password)``
   * - ``AppPasswordAuth(user, app_password)``
     - ``app-password``
     - A ``PasswordAuth`` that drops the whitespace an app password is shown with
   * - ``OAuth2Auth(settings, token_cache=None)``
     - ``oauth2``
     - ``access_token()`` and ``authorization()`` (``Bearer <token>``); no mail server login
   * - ``XOAUTH2Auth(settings, token_cache=None)``
     - ``xoauth2``
     - An ``OAuth2Auth`` whose ``login`` calls ``client.oauth2_login(user, access_token)``

``settings`` is an ``OAuth2Settings``. ``token_cache`` defaults to the shared ``oauth2_token_cache``,
looked up each time a token is needed. A missing user, password or settings object raises
``MailThunderAuthenticationException``; a refused or unreachable token endpoint raises
``MailThunderOAuth2Exception``, a subclass.

resolve_authentication()
~~~~~~~~~~~~~~~~~~~~~~~~

**Module:** ``je_mail_thunder.utils.save_mail_user_content.credentials``

.. code-block:: python

   def resolve_authentication() -> Optional[Authentication]

The login of ``mail_thunder_content.json`` or the environment: an ``XOAUTH2Auth`` when there are
OAuth2 settings, else a ``PasswordAuth``, else ``None``.

**Raises:** ``MailThunderOAuth2Exception`` when the OAuth2 settings found are incomplete or invalid.

----

Mail
----

**Module:** ``je_mail_thunder.core.mail``

.. code-block:: python

   class Mail:
       def __init__(self, provider: Optional[str] = None, auth: Optional[Authentication] = None,
                    account: Optional[MailAccount] = None, policy: Optional[AttachmentPolicy] = None,
                    providers: Optional[Sequence[MailProvider]] = None) -> None: ...

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Parameter
     - Description
   * - ``provider``
     - A registered provider name. Without one: the provider the OAuth2 settings name (those of
       ``auth``, else of the config file or the environment), else ``"google"``
   * - ``auth``
     - How the account logs in. By default ``resolve_authentication()``, looked up on first use
   * - ``account``
     - The whole ``MailAccount``, instead of ``provider`` and ``auth`` (giving both raises
       ``MailThunderProviderException``)
   * - ``policy``
     - The ``AttachmentPolicy`` checked before sending. ``DEFAULT_ATTACHMENT_POLICY`` by default;
       it can be replaced later through the ``policy`` attribute
   * - ``providers``
     - Ready providers to use instead of the ones the account's provider name stands for

Building a ``Mail`` reads and connects nothing. It is a context manager, and one instance
serialises the calls of the threads that share it.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Member
     - Description
   * - ``send(message=None, **message_fields)``
     - Check and send a ``MailMessage``, or the message built from the fields. Returns the message
       as sent
   * - ``create_draft(message=None, folder=None, **message_fields)``
     - Check a message like ``send`` and store it as a draft. Returns its ``message_id`` when the
       provider reports it, else ``None``
   * - ``get_messages(folder="INBOX", limit=None, unread_only=False, query=None)``
     - An iterator over a folder's messages, newest first, fetched one at a time. An invalid
       ``limit`` raises at the call
   * - ``get_message(message_id, folder="INBOX")``
     - One message
   * - ``delete_message(message_id, folder="INBOX")``
     - Delete one message
   * - ``close()``
     - Close the providers' connections; the next call connects again
   * - ``account``
     - The ``MailAccount`` in use (``None`` for a ``Mail`` built from providers without one)
   * - ``providers``
     - The providers in use, built without connecting on first access

**Raises:** ``MailThunderMessageException``, ``MailThunderAttachmentException``,
``MailThunderAuthenticationException``, ``MailThunderConnectionException``,
``MailThunderSendException`` or ``MailThunderProviderException``, each logged first.

``mail_instance`` is the ``Mail()`` the ``MT_mail_*`` commands use
(``je_mail_thunder.core.actions``: ``mail_send``, ``mail_create_draft``, ``mail_get_messages``,
``mail_get_message``).

MailMessage
~~~~~~~~~~~

**Module:** ``je_mail_thunder.core.message``

.. code-block:: python

   @dataclass(frozen=True)
   class MailMessage:
       subject: str = ""
       to: Tuple[str, ...] = ()
       cc: Tuple[str, ...] = ()
       bcc: Tuple[str, ...] = ()
       sender: Optional[str] = None
       reply_to: Tuple[str, ...] = ()
       text: Optional[str] = None
       html: Optional[str] = None
       attachments: Tuple[Attachment, ...] = ()
       headers: Mapping[str, str] = {}
       message_id: Optional[str] = None
       date: Optional[datetime] = None

The address fields accept an address, several separated by commas, or a list, and are stored as
tuples with one address each. ``attachments`` accepts paths or ``Attachment`` objects. ``headers``
is copied and read-only. A value of the wrong type raises ``MailThunderMessageException``.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Member
     - Description
   * - ``recipients``
     - ``to + cc + bcc``
   * - ``to_dict()``
     - JSON-ready values; attachments are described by name, type and size
   * - ``message_from_fields(fields)``
     - A message from a mapping of field names; an unknown name raises
       ``MailThunderMessageException``
   * - ``check_outgoing(message)``
     - Refuse a message without a recipient or sender, with an invalid address, or with a subject or
       header that is not one line
   * - ``parse_addresses(value)``
     - The addresses in one header value, or ``None`` when it is not a valid address list

``je_mail_thunder.core.rfc822`` converts to and from the MIME form: ``to_email_message(message)``,
``from_email_message(email_message, message_id=None)`` and ``parse_message(raw, message_id=None)``.

MailAccount and MailServers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Module:** ``je_mail_thunder.core.account``

.. code-block:: python

   @dataclass(frozen=True)
   class MailAccount:
       provider: str = "google"
       auth: Optional[Authentication] = None
       servers: Optional[MailServers] = None

   @dataclass(frozen=True)
   class MailServers:
       smtp_host: Optional[str] = None
       smtp_port: Optional[int] = None
       smtp_starttls: bool = False
       imap_host: Optional[str] = None
       drafts_folder: Optional[str] = None

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Member
     - Description
   * - ``MailAccount.provider``
     - Lower-cased; ``"gmail"`` becomes ``"google"``
   * - ``MailAccount.resolved_servers``
     - ``servers`` when given, else the provider's preset; raises ``MailThunderProviderException``
       when neither exists
   * - ``MailAccount.authentication()``
     - ``auth`` when given, else ``resolve_authentication()``; raises
       ``MailThunderAuthenticationException`` when there is nothing to log in with
   * - ``MailServers.port``
     - ``smtp_port`` when given, else 587 with ``smtp_starttls``, else 465
   * - ``default_account()``
     - The account of the config file or the environment, on the servers ``smtp_instance`` and
       ``imap_instance`` use

----

Providers
---------

**Modules:** ``je_mail_thunder.providers.base``, ``je_mail_thunder.providers.smtp``,
``je_mail_thunder.providers.imap``, ``je_mail_thunder.providers.registry``

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Class
     - Description
   * - ``MailProvider``
     - Base of every provider: a ``name``, an abstract ``close()``, and the context manager protocol
   * - ``MailSender``
     - A provider that sends: abstract ``send(message)``
   * - ``MailStore``
     - A provider that reads and manages stored mail: abstract ``get_messages``, ``get_message``,
       ``create_draft`` and ``delete_message``
   * - ``SMTPProvider(account=None, client=None)``
     - A ``MailSender`` over ``SMTPWrapper`` (implicit TLS) or ``SMTPStartTLSWrapper``. It reports
       recipients the server refused as ``MailThunderSendException.refused`` and never sends twice
   * - ``IMAPProvider(account=None, client=None)``
     - A ``MailStore`` over ``IMAPWrapper``. Messages are identified by UID and read with
       ``BODY.PEEK[]``; a draft goes to the folder flagged ``\Drafts``; a delete expunges only
       that message when the server has ``UIDPLUS``

Both connect and log in on first use, keep the connection, ask it for a sign of life after 30 idle
seconds and reconnect when it is dead. Given a ``client`` (a wrapper that is already logged in)
they use it as it is and never close it.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Function
     - Description
   * - ``register_provider(name, factory)``
     - Make a provider name usable. ``factory(account)`` returns the account's providers without
       connecting
   * - ``registered_providers()``
     - The registered names, sorted (``google``, ``microsoft``, ``smtp``)
   * - ``mailbox_name(folder)``
     - ``je_mail_thunder.providers.imap``: a folder name as IMAP takes it (modified UTF-7, quoted)

----

Bridges from the Wrapper API
----------------------------

**Module:** ``je_mail_thunder.core.compat``

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Function
     - Description
   * - ``legacy_message(message_content, message_setting_dict, attach_file=None, use_html=False)``
     - The ``MailMessage`` for the arguments of ``SMTPWrapper.create_message`` /
       ``create_message_with_attach``. ``Subject``, ``From``, ``To``, ``Cc``, ``Bcc`` and ``Reply-To``
       (any case) become fields, the rest ``headers``
   * - ``mail_from_wrappers(smtp=None, imap=None, policy=None)``
     - A ``Mail`` on wrappers that are already connected and logged in. They stay the caller's

----

Templates
---------

**Modules:** ``je_mail_thunder.templates.template``, ``je_mail_thunder.templates.loader``,
``je_mail_thunder.templates.engine``

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Name
     - Description
   * - ``MailTemplate(name, subject=None, text=None, html=None, variables=(), metadata={})``
     - A template. ``render(context)`` returns a ``RenderedTemplate``; ``context_for(context)`` adds the
       declared defaults and raises ``TemplateContextError`` for missing variables; ``referenced_variables``
       is every name the parts read; ``to_dict()`` is JSON-ready; ``MailTemplate.from_mapping(name, values)``
       builds one from the content of a template file
   * - ``RenderedTemplate(subject, text, html)``
     - What a template gave for one context; a part the template lacks is ``None``
   * - ``TemplateVariable(name, description="", default=<required>)``
     - A declared variable; ``required`` is true when it has no default
   * - ``TemplateLoader(directories=None)``
     - Finds templates by name: ``load(name)``, ``names()``, ``add(template)``, ``directories``. By default
       the project's ``mail/templates``, then ``shared_template_directory()``
   * - ``render_string(source, context=None, autoescape=False)``
     - Render template text in one step; ``CompiledTemplate(source)`` parses once and renders often
       (``names`` holds the context names it reads)
   * - ``Mail.render(template, context=None)``
     - The ``RenderedTemplate`` of a template name or ``MailTemplate``, without sending
   * - ``Mail(templates=...)`` / ``mail.templates``
     - The ``TemplateLoader`` ``send(template=...)`` uses

**Raises:** ``TemplateNotFound``, ``TemplateSyntaxError``, ``TemplateContextError`` or
``TemplateRenderError`` (all ``MailThunderTemplateException``).

----

Events and Triggers
-------------------

**Modules:** ``je_mail_thunder.core.events``, ``je_mail_thunder.triggers.filter``,
``je_mail_thunder.triggers.dispatcher``, ``je_mail_thunder.triggers.trigger``,
``je_mail_thunder.triggers.polling``, ``je_mail_thunder.triggers.imap``, ``je_mail_thunder.triggers.factory``

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Name
     - Description
   * - ``MailEvent(name, message=None, attachment=None, error=None, provider="", folder="", timestamp=now, metadata={})``
     - One thing that happened; ``to_dict()`` is JSON-ready. ``EVENT_NAMES`` lists the seven names
   * - ``failure_events(error, message=None, provider="", sending=False)``
     - The events a failed operation stands for, the most specific first
   * - ``MailFilter(sender, recipient, subject, body, has_attachments, attachment_type, since, until, metadata, predicate)``
     - ``matches(event)``; ``MailFilter.of(value)`` accepts ``None``, a mapping, a function or a filter;
       ``describe()`` is JSON-ready
   * - ``EventDispatcher``
     - ``on(event, handler, mail_filter=None)`` returns a ``Subscription``; ``off(subscription)``;
       ``emit(event)`` returns how many handlers were called; ``subscriptions``
   * - ``Mail.on(event, handler=None, filter=...)``
     - Subscribe on ``mail.events``; without a handler it is a decorator
   * - ``Mail.watch(folder="INBOX", idle=False, start=True, **options)``
     - Add a backend to ``mail.triggers`` and start it; ``options`` are ``interval``, ``include_existing``
       and ``batch_limit``
   * - ``MailTriggerBackend(interval=60.0)``
     - Abstract ``poll()``; ``bind(emit)``, ``start()``, ``stop()``, ``run()``, ``wait(seconds)``, ``close()``,
       ``running``, ``describe()``
   * - ``TriggerManager``
     - ``mail.triggers``: ``backends``, ``add``, ``remove``, ``poll``, ``start``, ``stop``
   * - ``PollingBackend(store, folder="INBOX", interval=60.0, include_existing=False, batch_limit=50, lock=None)``
     - Reports the messages a ``MailStore`` did not have at the last look
   * - ``IMAPPollingBackend`` / ``IMAPIdleBackend``
     - Polling with ``UID <last + 1>:*``; and waiting in ``IDLE`` between looks
   * - ``IMAPProvider.idle(folder="INBOX", timeout=300.0, should_stop=None)``
     - Wait in IMAP ``IDLE``; true when the server said something
   * - ``create_backend(store, folder="INBOX", idle=False, **options)`` / ``register_backends(store_type, polling, push=None)``
     - Which backend watches which kind of store

**Raises:** ``MailThunderTriggerException`` for an unknown event, filter rule or option, and for a backend
that cannot work with what it was given.

----

Microsoft Graph
---------------

**Modules:** ``je_mail_thunder.providers.microsoft_graph``, ``je_mail_thunder.providers.http``,
``je_mail_thunder.triggers.graph``

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Name
     - Description
   * - ``MicrosoftGraphProvider(account, transport=https_request)``
     - A ``MailSender`` and ``MailStore`` over ``https://graph.microsoft.com/v1.0``, registered as
       ``microsoft_graph``. ``call(method, path, payload=None, refusal=...)`` sends one Graph request;
       ``folder_path(folder)`` resolves a folder name
   * - ``graph_message(message, sender_is_account=True, attachments=True)``
     - A ``MailMessage`` as the Graph ``message`` resource
   * - ``mail_message(resource, attachments=None)``
     - A Graph ``message`` resource as a ``MailMessage``
   * - ``GRAPH_SCOPE``
     - The scopes a token is asked for when the OAuth2 settings name none
   * - ``https_request(method, url, headers, body=None)``
     - One HTTPS request with the standard library; returns ``(status, body)`` also for an error status
   * - ``GraphPollingBackend(store, ...)``
     - Polling that asks only for mail received since the last look
   * - ``GraphWebhookBackend(store, notification_url, folder="INBOX", host="localhost", port=9946, lifetime_minutes=60)``
     - Change notifications: ``subscribe()``, ``unsubscribe()``, ``poll()`` (creates or renews the
       subscription), ``handle_notification(payload)``, ``start()``, ``stop()``
   * - ``configured_mail_provider()``
     - ``je_mail_thunder.utils.save_mail_user_content.credentials``: ``"mail_provider"`` of the content
       file, else ``mail_thunder_mail_provider``, else ``None``

**Raises:** ``MailThunderAuthenticationException`` (HTTP 401 / 403, or a login that is not OAuth2),
``MailThunderConnectionException``, ``MailThunderSendException``, ``MailThunderProviderException``.
