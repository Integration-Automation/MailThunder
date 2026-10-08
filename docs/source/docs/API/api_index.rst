API Reference
=============

This section provides the complete API reference for all public classes, methods,
and functions in MailThunder.

Public Exports
--------------

All public APIs are accessible from the top-level ``je_mail_thunder`` package:

.. code-block:: python

   from je_mail_thunder import (
       # SMTP
       SMTPWrapper,              # SMTP wrapper class
       smtp_instance,            # Pre-created SMTP instance (or None)

       # IMAP
       IMAPWrapper,              # IMAP wrapper class
       imap_instance,            # Pre-created IMAP instance (or None)

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
