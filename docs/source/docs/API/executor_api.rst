Executor API
============

**Module:** ``je_mail_thunder.utils.executor.action_executor``

The Executor is the core engine that powers MailThunder's JSON scripting system.
It maps command names to Python callables and executes action lists sequentially.

----

Executor Class
--------------

.. code-block:: python

   class Executor:
       """
       Action executor that maps command names to callables.

       The event_dict contains all registered commands, including:
       - Built-in MailThunder commands (MT_smtp_*, MT_imap_*, etc.)
       - Python built-in functions (print, len, range, etc.)
       - Dynamically loaded package members
       - User-registered custom commands
       """

       def __init__(self):
           self.event_dict: dict = {...}

**Pre-registered commands in ``event_dict``:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Bound To
   * - ``MT_smtp_later_init``
     - ``smtp_instance.later_init``
   * - ``MT_smtp_create_message_with_attach_and_send``
     - ``smtp_instance.create_message_with_attach_and_send``
   * - ``MT_smtp_create_message_and_send``
     - ``smtp_instance.create_message_and_send``
   * - ``smtp_quit``
     - ``smtp_instance.quit``
   * - ``MT_imap_later_init``
     - ``imap_instance.later_init``
   * - ``MT_imap_select_mailbox``
     - ``imap_instance.select_mailbox``
   * - ``MT_imap_search_mailbox``
     - ``imap_instance.search_mailbox``
   * - ``MT_imap_mail_content_list``
     - ``imap_instance.mail_content_list``
   * - ``MT_imap_output_all_mail_as_file``
     - ``imap_instance.output_all_mail_as_file``
   * - ``MT_imap_quit``
     - ``imap_instance.quit``
   * - ``MT_set_mail_thunder_os_environ``
     - ``set_mail_thunder_os_environ``
   * - ``MT_get_mail_thunder_os_environ``
     - ``get_mail_thunder_os_environ``
   * - ``MT_add_package_to_executor``
     - ``package_manager.add_package_to_executor``
   * - *(all Python builtins)*
     - ``print``, ``len``, ``range``, ``type``, ``str``, ``int``, etc.

----

Module-Level Functions
----------------------

execute_action()
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def execute_action(action_list: [list, dict]) -> dict

Execute a list of action commands.

**Parameters:**

- ``action_list`` — Either:

  - A ``list`` of actions: ``[["cmd1"], ["cmd2", args], ...]``
  - A ``dict`` with an ``"auto_control"`` key: ``{"auto_control": [["cmd1"], ...]}``

**Returns:** A ``dict`` mapping ``"execute: [action]"`` to the return value of each
command. If a command fails, the value is the exception's ``repr()``.

**Action dispatch logic:**

.. code-block:: text

   action = ["command_name"]
   → event_dict["command_name"]()

   action = ["command_name", {"k1": "v1", "k2": "v2"}]
   → event_dict["command_name"](**{"k1": "v1", "k2": "v2"})

   action = ["command_name", ["arg1", "arg2"]]
   → event_dict["command_name"](*["arg1", "arg2"])

   action = ["command_name", "something", "extra"]  (len > 2)
   → raises ExecuteActionException

**Error handling:** The executor does **not** stop on errors. It catches exceptions
per-action, logs them, and continues executing remaining actions.

**Output:** Each action and its result are printed to stdout.

**Example:**

.. code-block:: python

   from je_mail_thunder import execute_action

   result = execute_action([
       ["print", ["Hello!"]],
       ["MT_smtp_later_init"],
       ["smtp_quit"]
   ])
   # result = {
   #     "execute: ['print', ['Hello!']]": None,
   #     "execute: ['MT_smtp_later_init']": None,
   #     "execute: ['smtp_quit']": None,
   # }

----

execute_files()
~~~~~~~~~~~~~~~~

.. code-block:: python

   def execute_files(execute_files_list: list) -> list

Execute multiple JSON action files sequentially.

**Parameters:**

- ``execute_files_list`` — A list of file paths to JSON action files

**Returns:** A list of result dicts (one per file, same format as ``execute_action()``).

**Example:**

.. code-block:: python

   from je_mail_thunder import execute_files, get_dir_files_as_list

   files = get_dir_files_as_list("/path/to/actions/")
   results = execute_files(files)

----

add_command_to_executor()
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def add_command_to_executor(command_dict: dict) -> None

Register custom functions in the executor's ``event_dict``.

**Parameters:**

- ``command_dict`` — A dict mapping command name strings to callable functions.
  Values **must** be ``types.MethodType`` or ``types.FunctionType``.

**Raises:** ``AddCommandException`` if any value is not a valid function type.

**Example:**

.. code-block:: python

   from je_mail_thunder import add_command_to_executor

   def my_handler(msg):
       print(f"Custom: {msg}")

   add_command_to_executor({"my_cmd": my_handler})

----

Singleton Instance
------------------

.. code-block:: python

   executor = Executor()
   package_manager.executor = executor

The ``Executor`` is instantiated as a module-level singleton. The
``PackageManager``'s ``executor`` reference is set to this instance, allowing
dynamically loaded packages to register their members.

----

Exceptions
----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Exception
     - Condition
   * - ``ExecuteActionException``
     - Action list is empty, wrong type, ``auto_control`` key missing,
       or action has more than 2 elements
   * - ``AddCommandException``
     - ``add_command_to_executor()`` receives a non-callable value

----

Thread Safety
-------------

- ``read_action_json()`` and ``write_action_json()`` use ``threading.Lock`` for
  thread-safe file I/O
- The ``event_dict`` is **not** thread-safe — avoid concurrent modifications
- The executor singleton is shared across the process
