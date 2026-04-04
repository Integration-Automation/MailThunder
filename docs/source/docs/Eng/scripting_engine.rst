JSON Scripting Engine
=====================

MailThunder includes a powerful JSON-based scripting engine that lets you automate
email workflows without writing Python code. The engine is built around the
``Executor`` class, which maps command names to Python callables.

----

How It Works
------------

1. You write a JSON file (or dict) containing an ``auto_control`` key
2. The value is a list of action commands
3. Each command is executed sequentially by the ``Executor``
4. Results are collected and returned as a dict

.. code-block:: text

   JSON Action File
       │
       ▼
   execute_action(action_list)
       │
       ├── If dict: extract action_list["auto_control"]
       ├── If list: use directly
       │
       ▼
   For each action in action_list:
       │
       ├── action = ["command_name"]          ──▶ executor.event_dict["command_name"]()
       ├── action = ["command_name", {k: v}]  ──▶ executor.event_dict["command_name"](**{k: v})
       └── action = ["command_name", [a, b]]  ──▶ executor.event_dict["command_name"](*[a, b])

----

Action File Format
------------------

Action files use the ``auto_control`` key containing a list of commands:

.. code-block:: json

   {
     "auto_control": [
       ["command_name"],
       ["command_name", {"key": "value"}],
       ["command_name", ["arg1", "arg2"]]
     ]
   }

**Argument conventions:**

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Format
     - Type
     - Python Equivalent
   * - ``["command"]``
     - No arguments
     - ``command()``
   * - ``["command", {"k": "v"}]``
     - Keyword arguments
     - ``command(**{"k": "v"})``
   * - ``["command", ["a", "b"]]``
     - Positional arguments
     - ``command(*["a", "b"])``

You can also pass a plain list (without the ``auto_control`` wrapper) directly to
``execute_action()``:

.. code-block:: python

   from je_mail_thunder import execute_action

   execute_action([
       ["MT_smtp_later_init"],
       ["smtp_quit"]
   ])

----

Built-in Commands
-----------------

**SMTP commands:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``MT_smtp_later_init``
     - Initialize and log in to SMTP server
   * - ``MT_smtp_create_message_and_send``
     - Create and send a plain text email
   * - ``MT_smtp_create_message_with_attach_and_send``
     - Create and send an email with attachment
   * - ``smtp_quit``
     - Disconnect from SMTP server

**IMAP commands:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``MT_imap_later_init``
     - Initialize and log in to IMAP server
   * - ``MT_imap_select_mailbox``
     - Select a mailbox (default: INBOX)
   * - ``MT_imap_search_mailbox``
     - Search and get raw mail details
   * - ``MT_imap_mail_content_list``
     - Get parsed mail content as list of dicts
   * - ``MT_imap_output_all_mail_as_file``
     - Export all emails to local files
   * - ``MT_imap_quit``
     - Disconnect from IMAP server

**Authentication commands:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``MT_set_mail_thunder_os_environ``
     - Set auth environment variables
   * - ``MT_get_mail_thunder_os_environ``
     - Get current auth environment variables

**Package management:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``MT_add_package_to_executor``
     - Load a Python package into the executor

**Python builtins:**

All Python built-in functions (``print``, ``len``, ``range``, ``type``, ``str``,
``int``, ``list``, ``dict``, etc.) are automatically registered and available as
commands.

----

Examples
--------

**Send a plain text email:**

.. code-block:: json

   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
         "message_content": "Hello from the scripting engine!",
         "message_setting_dict": {
           "Subject": "Automated Email",
           "To": "receiver@gmail.com",
           "From": "sender@gmail.com"
         }
       }],
       ["smtp_quit"]
     ]
   }

**Send an email with attachment:**

.. code-block:: json

   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_with_attach_and_send", {
         "message_content": "Please review the attached report.",
         "message_setting_dict": {
           "Subject": "Monthly Report",
           "To": "receiver@gmail.com",
           "From": "sender@gmail.com"
         },
         "attach_file": "/path/to/report.pdf",
         "use_html": false
       }],
       ["smtp_quit"]
     ]
   }

**Read and export all emails:**

.. code-block:: json

   {
     "auto_control": [
       ["MT_imap_later_init"],
       ["MT_imap_select_mailbox"],
       ["MT_imap_output_all_mail_as_file"],
       ["MT_imap_quit"]
     ]
   }

**Search unread emails in read-only mode:**

.. code-block:: json

   {
     "auto_control": [
       ["MT_imap_later_init"],
       ["MT_imap_select_mailbox", {"mailbox": "INBOX", "readonly": true}],
       ["MT_imap_mail_content_list", {"search_str": "UNSEEN"}],
       ["MT_imap_quit"]
     ]
   }

**Set credentials then send:**

.. code-block:: json

   {
     "auto_control": [
       ["MT_set_mail_thunder_os_environ", {
         "mail_thunder_user": "sender@gmail.com",
         "mail_thunder_user_password": "your_app_password"
       }],
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
         "message_content": "Credentials set via script!",
         "message_setting_dict": {
           "Subject": "Auth Test",
           "To": "receiver@gmail.com",
           "From": "sender@gmail.com"
         }
       }],
       ["smtp_quit"]
     ]
   }

**Using Python builtins:**

.. code-block:: json

   {
     "auto_control": [
       ["print", ["Hello from the executor!"]],
       ["print", ["The answer is: 42"]]
     ]
   }

----

Executing Action Files
----------------------

**From Python:**

.. code-block:: python

   from je_mail_thunder import execute_action, read_action_json

   # Execute a single file
   result = execute_action(read_action_json("/path/to/action.json"))

   # The result is a dict mapping "execute: [action]" to return values
   for action, return_value in result.items():
       print(action, return_value)

**Execute multiple files in a directory:**

.. code-block:: python

   from je_mail_thunder import execute_files, get_dir_files_as_list

   # Get all .json files in the directory
   files = get_dir_files_as_list("/path/to/actions/")
   results = execute_files(files)

   # results is a list of dicts, one per file
   for i, result in enumerate(results):
       print(f"File {i}: {result}")

**From CLI:**

.. code-block:: bash

   # Execute a single file
   python -m je_mail_thunder -e /path/to/action.json

   # Execute all JSON files in a directory
   python -m je_mail_thunder -d /path/to/actions/

   # Execute a JSON string
   python -m je_mail_thunder --execute_str '[["print", ["Hello!"]]]'

----

Extending with Custom Commands
------------------------------

Add your own functions to the executor:

.. code-block:: python

   from je_mail_thunder import add_command_to_executor, execute_action

   def send_notification(channel, message):
       print(f"[{channel}] {message}")
       return {"status": "sent", "channel": channel}

   def process_data(filename):
       print(f"Processing {filename}...")
       return {"processed": filename}

   # Register custom commands
   add_command_to_executor({
       "notify": send_notification,
       "process": process_data
   })

   # Use them in action lists
   execute_action([
       ["process", ["data.csv"]],
       ["notify", {"channel": "#alerts", "message": "Processing complete"}]
   ])

.. warning::

   Only ``types.MethodType`` and ``types.FunctionType`` instances can be added.
   Passing a non-callable (e.g., a string or int) will raise ``AddCommandException``.

----

Execution Output
----------------

When actions are executed, each command and its return value are printed to stdout:

.. code-block:: text

   execute: ['MT_smtp_later_init']
   None
   execute: ['MT_smtp_create_message_and_send', {...}]
   None
   execute: ['smtp_quit']
   None

If an action fails, the exception is caught, logged, and stored in the result dict:

.. code-block:: text

   execute: ['invalid_command']
   TypeError("'NoneType' object is not callable")

The executor does **not** stop on errors — it continues executing subsequent actions
and collects all results.

----

Thread Safety
-------------

The ``Executor`` class is instantiated as a module-level singleton (``executor``).
JSON file reads (``read_action_json``) use a ``threading.Lock`` for thread-safe
file access. However, the executor's ``event_dict`` itself is not locked, so
concurrent modifications to the command registry should be avoided.
