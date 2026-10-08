API Reference
=============

This section provides the complete API reference for all public classes, methods,
and functions in MailThunder.

Public Exports
--------------

All public APIs are accessible from the top-level ``je_mail_thunder`` package:

.. code-block:: python

   from je_mail_thunder import (
       # Core mail API
       Mail,                     # Provider-agnostic mail API
       mail_instance,            # The Mail the MT_mail_* commands use
       MailMessage,              # Provider-independent message
       MailAccount,              # Provider, login and servers of an account
       MailServers,              # SMTP / IMAP servers of an account
       MailProvider,             # Base of the providers
       MailSender,               # Interface of a provider that sends
       MailStore,                # Interface of a provider that reads
       SMTPProvider,             # MailSender over SMTP
       IMAPProvider,             # MailStore over IMAP
       register_provider,        # Add a provider name
       registered_providers,     # The provider names
       legacy_message,           # Wrapper arguments as a MailMessage
       mail_from_wrappers,       # Mail on wrappers that are already logged in

       # SMTP
       SMTPWrapper,              # SMTP wrapper class
       smtp_instance,            # Pre-created SMTP instance (or None)

       # IMAP
       IMAPWrapper,              # IMAP wrapper class
       imap_instance,            # Pre-created IMAP instance (or None)

       # Templates
       MailTemplate,             # Subject / text / HTML template
       RenderedTemplate,         # What a template gave for a context
       TemplateLoader,           # Finds templates by name
       render_string,            # Render template text

       # Events and triggers
       MailEvent,                # One thing that happened to mail
       EVENT_NAMES,              # The seven event names
       MailFilter,               # Which events a handler wants
       EventDispatcher,          # Calls the subscribed handlers
       MailTriggerBackend,       # Base of what watches a mailbox
       PollingBackend,           # Watches any MailStore by polling
       IMAPPollingBackend,       # IMAP polling by UID
       IMAPIdleBackend,          # IMAP IDLE

       # Microsoft Graph
       MicrosoftGraphProvider,   # Microsoft 365 mail over the Graph API
       GraphPollingBackend,      # Graph polling by received time
       GraphWebhookBackend,      # Graph change notifications

       # Monitoring and more providers
       AuditLog,                 # Append-only record of mail events
       ProviderHealth,           # healthy / degraded / down per provider
       WebhookForwarder,         # Posts events to an HTTPS address
       FileProvider,             # Keeps mail as .eml files (dry runs)

       # Project mail layer
       project_mail,             # The Mail a project's mail/ directory describes
       describe_mail_layer,      # What a project's mail/ directory holds

       # Authentication objects
       Authentication,           # Interface of the login mechanisms
       PasswordAuth,             # The account's password
       AppPasswordAuth,          # An app password
       OAuth2Auth,               # OAuth2 bearer token (HTTP APIs)
       XOAUTH2Auth,              # OAuth2 as SASL XOAUTH2 (SMTP / IMAP)
       resolve_authentication,   # The login of the config file or the environment
       OAuth2Settings,           # Who logs in and how the token is obtained
       oauth2_token_cache,       # Shared access-token cache

       # Attachments
       Attachment,               # A file to send, or one that arrived
       AttachmentPolicy,         # Count, size and type limits
       DEFAULT_ATTACHMENT_POLICY,  # 25 MiB of any type
       validate_attachments,     # Check attachments against a policy

       # Authentication
       set_mail_thunder_os_environ,        # Set auth env vars
       get_mail_thunder_os_environ,        # Get auth env vars
       mail_thunder_content_data_dict,     # Global credential dict
       is_need_to_save_content,            # Check if credentials need saving
       read_output_content,                # Read mail_thunder_content.json
       write_output_content,               # Write mail_thunder_content.json

       # Executor
       execute_action,           # Execute action list
       execute_files,            # Execute multiple action files
       add_command_to_executor,  # Register custom commands

       # JSON
       read_action_json,         # Read JSON action file

       # File Utilities
       get_dir_files_as_list,    # List directory files

       # Project
       create_project_dir,       # Scaffold project with templates
   )

----

Module Map
----------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Import Path
     - Description
   * - ``je_mail_thunder.smtp.smtp_wrapper``
     - ``SMTPWrapper`` class, ``smtp_instance``
   * - ``je_mail_thunder.imap.imap_wrapper``
     - ``IMAPWrapper`` class, ``imap_instance``
   * - ``je_mail_thunder.core.mail``
     - ``Mail`` class, ``mail_instance``
   * - ``je_mail_thunder.core.message``
     - ``MailMessage`` class, ``message_from_fields()``, ``check_outgoing()``, ``parse_addresses()``
   * - ``je_mail_thunder.core.rfc822``
     - ``to_email_message()``, ``from_email_message()``, ``parse_message()``
   * - ``je_mail_thunder.core.account``
     - ``MailAccount``, ``MailServers``, ``default_account()``, ``SERVER_PRESETS``
   * - ``je_mail_thunder.core.actions``
     - ``mail_send()``, ``mail_create_draft()``, ``mail_get_messages()``, ``mail_get_message()``
   * - ``je_mail_thunder.core.compat``
     - ``legacy_message()``, ``mail_from_wrappers()``
   * - ``je_mail_thunder.providers.base``
     - ``MailProvider``, ``MailSender``, ``MailStore``
   * - ``je_mail_thunder.providers.smtp``
     - ``SMTPProvider``
   * - ``je_mail_thunder.providers.imap``
     - ``IMAPProvider``, ``mailbox_name()``
   * - ``je_mail_thunder.providers.registry``
     - ``register_provider()``, ``registered_providers()``, ``create_providers()``
   * - ``je_mail_thunder.providers.session``
     - ``WrapperProvider`` (the connection of a provider built on a wrapper)
   * - ``je_mail_thunder.templates.engine``
     - ``CompiledTemplate``, ``render_string()``, ``SafeText``
   * - ``je_mail_thunder.templates.template``
     - ``MailTemplate``, ``RenderedTemplate``, ``TemplateVariable``
   * - ``je_mail_thunder.templates.loader``
     - ``TemplateLoader``, ``shared_template_directory()``
   * - ``je_mail_thunder.core.events``
     - ``MailEvent``, ``EVENT_NAMES``, ``ANY_EVENT``, ``failure_events()``
   * - ``je_mail_thunder.triggers.filter``
     - ``MailFilter``
   * - ``je_mail_thunder.triggers.dispatcher``
     - ``EventDispatcher``, ``Subscription``
   * - ``je_mail_thunder.triggers.trigger``
     - ``MailTriggerBackend``, ``TriggerManager``
   * - ``je_mail_thunder.triggers.polling``
     - ``PollingBackend``
   * - ``je_mail_thunder.triggers.imap``
     - ``IMAPPollingBackend``, ``IMAPIdleBackend``
   * - ``je_mail_thunder.triggers.factory``
     - ``create_backend()``, ``register_backends()``
   * - ``je_mail_thunder.providers.microsoft_graph``
     - ``MicrosoftGraphProvider``, ``graph_message()``, ``mail_message()``, ``GRAPH_SCOPE``
   * - ``je_mail_thunder.providers.http``
     - ``https_request()``, ``decode_json()``
   * - ``je_mail_thunder.triggers.graph``
     - ``GraphPollingBackend``, ``GraphWebhookBackend``
   * - ``je_mail_thunder.monitoring.audit``
     - ``AuditLog``, ``audit_entry()``, ``default_audit_file()``
   * - ``je_mail_thunder.monitoring.health``
     - ``ProviderHealth``
   * - ``je_mail_thunder.triggers.webhook``
     - ``WebhookForwarder``, ``webhook_payload()``, ``sign()``
   * - ``je_mail_thunder.providers.file``
     - ``FileProvider``
   * - ``je_mail_thunder.core.project``
     - ``project_mail()``, ``describe_mail_layer()``, ``mail_layer_directory()``
   * - ``je_mail_thunder.studio.api``
     - ``StudioApi``
   * - ``je_mail_thunder.studio.server``
     - ``StudioServer``, ``start_studio()``, ``DEFAULT_PORT``
   * - ``je_mail_thunder.auth.base``
     - ``Authentication`` class
   * - ``je_mail_thunder.auth.password``
     - ``PasswordAuth``, ``AppPasswordAuth``
   * - ``je_mail_thunder.auth.oauth2``
     - ``OAuth2Auth``
   * - ``je_mail_thunder.auth.xoauth2``
     - ``XOAUTH2Auth``
   * - ``je_mail_thunder.utils.oauth2.oauth2``
     - ``OAuth2Settings``, ``OAuth2Provider``, ``OAUTH2_PROVIDERS``, ``OAuth2TokenCache``, ``oauth2_token_cache``,
       ``refresh_access_token()``, ``xoauth2_string()``
   * - ``je_mail_thunder.utils.tls.tls_context``
     - ``verified_client_context()``
   * - ``je_mail_thunder.utils.save_mail_user_content.credentials``
     - ``resolve_authentication()``, ``resolve_oauth2_settings()``, ``resolve_login_credentials()``
   * - ``je_mail_thunder.attachments.attachment``
     - ``Attachment`` class
   * - ``je_mail_thunder.attachments.policy``
     - ``AttachmentPolicy`` class, ``DEFAULT_ATTACHMENT_POLICY``, ``MEBIBYTE``
   * - ``je_mail_thunder.attachments.validator``
     - ``validate_attachments()``
   * - ``je_mail_thunder.attachments.mime``
     - ``guess_content_type()``, ``file_extension()``, ``safe_filename()``
   * - ``je_mail_thunder.utils.executor.action_executor``
     - ``Executor`` class, ``execute_action()``, ``execute_files()``, ``add_command_to_executor()``
   * - ``je_mail_thunder.utils.save_mail_user_content.save_on_env``
     - ``set_mail_thunder_os_environ()``, ``get_mail_thunder_os_environ()``
   * - ``je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save``
     - ``read_output_content()``, ``write_output_content()``
   * - ``je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_data``
     - ``mail_thunder_content_data_dict``, ``is_need_to_save_content()``
   * - ``je_mail_thunder.utils.json.json_file``
     - ``read_action_json()``, ``write_action_json()``
   * - ``je_mail_thunder.utils.json_format.json_process``
     - ``reformat_json()``
   * - ``je_mail_thunder.utils.file_process.get_dir_file_list``
     - ``get_dir_files_as_list()``
   * - ``je_mail_thunder.utils.project.create_project_structure``
     - ``create_project_dir()``
   * - ``je_mail_thunder.utils.package_manager.package_manager_class``
     - ``PackageManager`` class, ``package_manager``
   * - ``je_mail_thunder.utils.socket_server.mail_thunder_socket_server``
     - ``TCPServer``, ``TCPServerHandler``, ``start_mail_thunder_socket_server()`` (old name ``start_autocontrol_socket_server()`` is deprecated)
   * - ``je_mail_thunder.utils.logging.loggin_instance``
     - ``mail_thunder_logger``
   * - ``je_mail_thunder.utils.exception.exceptions``
     - All custom exception classes
   * - ``je_mail_thunder.utils.exception.exception_tags``
     - Error tag strings
