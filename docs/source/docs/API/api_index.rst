MailThunder API Reference
=========================

This section provides the complete API reference for MailThunder's public classes and functions.

.. toctree::
    :maxdepth: 4
    :caption: API Documentation

    smtp_api.rst
    imap_api.rst

----

Public Exports
--------------

All public APIs are accessible from the top-level ``je_mail_thunder`` package:

.. code-block:: python

    from je_mail_thunder import (
        # SMTP
        SMTPWrapper,
        smtp_instance,
        # IMAP
        IMAPWrapper,
        imap_instance,
        # Authentication
        set_mail_thunder_os_environ,
        get_mail_thunder_os_environ,
        mail_thunder_content_data_dict,
        is_need_to_save_content,
        read_output_content,
        write_output_content,
        # Executor
        execute_action,
        execute_files,
        add_command_to_executor,
        # JSON
        read_action_json,
        # File Utilities
        get_dir_files_as_list,
        # Project
        create_project_dir,
    )

----

Executor Functions
------------------

**Module:** ``je_mail_thunder.utils.executor.action_executor``

.. code-block:: python

    def execute_action(action_list: [list, dict]) -> dict:
        """
        Execute a list of action commands.

        :param action_list: A list of action commands, or a dict with an "auto_control" key.
            Each action is a list where:
            - [0] is the command name (str)
            - [1] (optional) is a dict for keyword arguments or a list for positional arguments
        :return: A dict mapping "execute: [action]" to the return value of each command.
        """

.. code-block:: python

    def execute_files(execute_files_list: list) -> list:
        """
        Execute multiple JSON action files.

        :param execute_files_list: A list of file paths to JSON action files.
        :return: A list of execution result dicts (one per file).
        """

.. code-block:: python

    def add_command_to_executor(command_dict: dict):
        """
        Add custom functions to the executor.

        :param command_dict: A dict mapping command names (str) to callable functions.
            Values must be types.MethodType or types.FunctionType.
        :raises AddCommandException: If a value is not a valid function type.
        """

----

Utility Functions
-----------------

**Authentication:**

.. code-block:: python

    def set_mail_thunder_os_environ(mail_thunder_user: str, mail_thunder_user_password: str):
        """
        Set authentication environment variables.

        :param mail_thunder_user: Email address
        :param mail_thunder_user_password: Email password or app password
        """

.. code-block:: python

    def get_mail_thunder_os_environ() -> dict:
        """
        Get authentication environment variables.

        :return: {"mail_thunder_user": str or None, "mail_thunder_user_password": str or None}
        """

**Content File:**

.. code-block:: python

    def read_output_content() -> dict:
        """
        Read mail_thunder_content.json from the current working directory.

        :return: Dict with "user" and "password" keys, or None if file not found.
        """

.. code-block:: python

    def write_output_content():
        """
        Write content data to mail_thunder_content.json in the current working directory.
        """

**JSON:**

.. code-block:: python

    def read_action_json(file_path: str) -> dict:
        """
        Read and parse a JSON action file.

        :param file_path: Path to the JSON file.
        :return: Parsed JSON data as dict or list.
        """

**File Utilities:**

.. code-block:: python

    def get_dir_files_as_list(path: str) -> list:
        """
        Get all file paths in a directory as a list.

        :param path: Directory path to scan.
        :return: List of file path strings.
        """

**Project:**

.. code-block:: python

    def create_project_dir(project_path=None, parent_name=None):
        """
        Create a project directory with pre-built templates.

        :param project_path: Path where the project will be created (default: current directory).
        :param parent_name: Name of the project root directory.
        """

----
