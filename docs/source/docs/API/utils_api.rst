Utility Functions API
=====================

This page documents all utility functions and modules in MailThunder.

----

Authentication Utilities
------------------------

**Module:** ``je_mail_thunder.utils.save_mail_user_content.save_on_env``

set_mail_thunder_os_environ()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def set_mail_thunder_os_environ(
       mail_thunder_user: str,
       mail_thunder_user_password: str
   ) -> None

Set authentication environment variables using ``os.environ.update()``.

**Parameters:**

- ``mail_thunder_user`` — Email address string
- ``mail_thunder_user_password`` — Password or app password string

**Sets:**

- ``os.environ["mail_thunder_user"]``
- ``os.environ["mail_thunder_user_password"]``

----

get_mail_thunder_os_environ()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_mail_thunder_os_environ() -> dict

Get current authentication environment variables.

**Returns:**

.. code-block:: python

   {
       "mail_thunder_user": str | None,
       "mail_thunder_user_password": str | None
   }

Returns ``None`` for unset variables.

----

Content File Utilities
----------------------

**Module:** ``je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_save``

read_output_content()
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def read_output_content() -> dict | None

Read ``mail_thunder_content.json`` from the current working directory.

**Returns:** A dict with ``"user"`` and ``"password"`` keys, or ``None`` if
the file does not exist.

**Side effect:** Updates the global ``mail_thunder_content_data_dict`` with
the file contents.

**Thread safety:** Uses ``threading.Lock``.

----

write_output_content()
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def write_output_content() -> None

Write the current ``mail_thunder_content_data_dict`` to
``mail_thunder_content.json`` in the current working directory.
The output is reformatted JSON (indented, sorted keys).

**Thread safety:** Uses ``threading.Lock``.

----

Content Data
~~~~~~~~~~~~

**Module:** ``je_mail_thunder.utils.save_mail_user_content.mail_thunder_content_data``

.. code-block:: python

   mail_thunder_content_data_dict = {
       "user": None,
       "password": None
   }

Global mutable dict holding the current credentials.
Updated by ``read_output_content()`` and can be manually modified.

.. code-block:: python

   def is_need_to_save_content() -> bool

Returns ``True`` if any value in ``mail_thunder_content_data_dict`` is not ``None``.

----

JSON File Utilities
-------------------

**Module:** ``je_mail_thunder.utils.json.json_file``

read_action_json()
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def read_action_json(json_file_path: str) -> list

Read and parse a JSON action file.

**Parameters:**

- ``json_file_path`` — Path to the JSON file

**Returns:** Parsed JSON data (typically a list or dict).

**Raises:** ``JsonActionException`` if the file is not found or cannot be parsed.

**Thread safety:** Uses ``threading.Lock``.

----

write_action_json()
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def write_action_json(json_save_path: str, action_json: list) -> None

Write action data to a JSON file (indented, 4 spaces).

**Parameters:**

- ``json_save_path`` — File path to write to
- ``action_json`` — Data to serialize as JSON

**Raises:** ``JsonActionException`` if the file cannot be saved.

**Thread safety:** Uses ``threading.Lock``.

----

JSON Formatting
~~~~~~~~~~~~~~~

**Module:** ``je_mail_thunder.utils.json_format.json_process``

.. code-block:: python

   def reformat_json(json_string: str, **kwargs) -> str

Reformat a JSON string with indentation (4 spaces) and sorted keys.

**Parameters:**

- ``json_string`` — JSON string to reformat
- ``**kwargs`` — Additional arguments passed to ``json.dumps()``

**Returns:** Reformatted JSON string.

**Raises:** ``MailThunderJsonException`` on parse or type errors.

----

File Process Utilities
----------------------

**Module:** ``je_mail_thunder.utils.file_process.get_dir_file_list``

get_dir_files_as_list()
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_dir_files_as_list(
       dir_path: str = os.getcwd(),
       default_search_file_extension: str = ".json"
   ) -> List[str]

Walk a directory tree and collect all files matching the given extension.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Parameter
     - Default
     - Description
   * - ``dir_path``
     - ``os.getcwd()``
     - Directory to walk
   * - ``default_search_file_extension``
     - ``".json"``
     - File extension filter (case-insensitive)

**Returns:** A list of absolute file path strings. Empty list if nothing found.

**Example:**

.. code-block:: python

   from je_mail_thunder import get_dir_files_as_list

   # Get all .json files in a directory
   files = get_dir_files_as_list("/path/to/actions/")
   # ["/path/to/actions/action1.json", "/path/to/actions/action2.json"]

   # Get all .py files
   files = get_dir_files_as_list("/path/to/code/", ".py")

----

Project Scaffolding
-------------------

**Module:** ``je_mail_thunder.utils.project.create_project_structure``

create_project_dir()
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def create_project_dir(
       project_path: str = None,
       parent_name: str = "MailThunder"
   ) -> None

Create a project directory with template files.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Parameter
     - Default
     - Description
   * - ``project_path``
     - ``os.getcwd()``
     - Base directory for the project
   * - ``parent_name``
     - ``"MailThunder"``
     - Name of the project root folder

**Creates:**

.. code-block:: text

   {project_path}/{parent_name}/
     keyword/
       keyword1.json          # SMTP send template
       keyword2.json          # IMAP export template
       bad_keyword_1.json     # Security warning example
     executor/
       executor_one_file.py   # Single file executor
       executor_folder.py     # Directory executor
       executor_bad_file.py   # Bad practice example

Template ``{temp}`` placeholders are replaced with absolute paths during creation.

----

Socket Server
-------------

**Module:** ``je_mail_thunder.utils.socket_server.mail_thunder_socket_server``

start_autocontrol_socket_server()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def start_autocontrol_socket_server(
       host: str = "localhost",
       port: int = 9944
   ) -> TCPServer

Start a TCP socket server that accepts JSON action commands.

**Parameters:**

- ``host`` — Bind address (default: ``"localhost"``)
- ``port`` — TCP port (default: ``9944``)

**Returns:** ``TCPServer`` instance with ``close_flag`` attribute.

The server runs in a daemon background thread via ``threading.Thread(daemon=True)``.
Can also read ``host``/``port`` from ``sys.argv[1]``/``sys.argv[2]``.

----

TCPServer
~~~~~~~~~

.. code-block:: python

   class TCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
       close_flag: bool = False

Custom TCP server with threading support. ``close_flag`` is set to ``True``
when the ``"quit_server"`` command is received.

----

TCPServerHandler
~~~~~~~~~~~~~~~~

.. code-block:: python

   class TCPServerHandler(socketserver.BaseRequestHandler):
       def handle(self): ...

Handles incoming client connections:

- Receives up to 8192 bytes (UTF-8)
- If command is ``"quit_server"``: shuts down the server
- Otherwise: parses as JSON, calls ``execute_action()``, sends results back
- Response terminated with ``"Return_Data_Over_JE\n"``

----

Package Manager
---------------

**Module:** ``je_mail_thunder.utils.package_manager.package_manager_class``

.. code-block:: python

   class PackageManager:
       installed_package_dict: dict   # Cache of loaded packages
       executor: Executor | None      # Reference to the executor

**Methods:**

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Method
     - Description
   * - ``check_package(package: str)``
     - Check if a package exists and import it. Returns the module or ``None``.
   * - ``add_package_to_executor(package: str)``
     - Load all functions, builtins, and classes from a package into the executor.
       Members are prefixed with ``{package}_``.
   * - ``add_package_to_callback_executor(package: str)``
     - Same as above but for the callback executor reference.
   * - ``get_member(package, predicate, target)``
     - Extract members matching a predicate and register in target's ``event_dict``.
   * - ``add_package_to_target(package, target)``
     - Run ``get_member()`` for isfunction, isbuiltin, and isclass predicates.

**Singleton:**

.. code-block:: python

   package_manager = PackageManager()

Module-level singleton. Its ``executor`` attribute is set to the main ``Executor``
instance after initialization.

----

Logging
-------

**Module:** ``je_mail_thunder.utils.logging.loggin_instance``

.. code-block:: python

   mail_thunder_logger = logging.getLogger("Mail Thunder")

Pre-configured logger with:

- **File handler:** ``Mail_Thunder.log`` (INFO level, ``w+`` mode)
- **Stream handler:** ``stderr`` (WARNING level)
- **Format:** ``%(asctime)s | %(name)s | %(levelname)s | %(message)s``
