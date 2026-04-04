Command-Line Interface
======================

MailThunder provides a CLI via ``python -m je_mail_thunder`` for executing JSON
action files, running JSON strings, and scaffolding projects directly from the
terminal.

----

Usage
-----

.. code-block:: bash

   python -m je_mail_thunder [OPTIONS]

----

Options
-------

.. list-table::
   :header-rows: 1
   :widths: 10 25 65

   * - Flag
     - Long Flag
     - Description
   * - ``-e``
     - ``--execute_file``
     - Execute a single JSON action file
   * - ``-d``
     - ``--execute_dir``
     - Execute all JSON action files in a directory
   * -
     - ``--execute_str``
     - Execute a JSON string directly
   * - ``-c``
     - ``--create_project``
     - Create a project directory with templates

If no flags are provided, the CLI raises ``MailThunderArgparseException``.

----

Execute a Single Action File
-----------------------------

.. code-block:: bash

   python -m je_mail_thunder -e /path/to/action.json

This reads the JSON file, parses the action list, and passes it to ``execute_action()``.

**Example:**

.. code-block:: bash

   python -m je_mail_thunder -e my_project/keyword/keyword1.json

----

Execute All Files in a Directory
---------------------------------

.. code-block:: bash

   python -m je_mail_thunder -d /path/to/actions/

This scans the directory for all ``.json`` files (using ``get_dir_files_as_list()``)
and executes each one sequentially via ``execute_files()``.

**Example:**

.. code-block:: bash

   python -m je_mail_thunder -d my_project/keyword/

----

Execute a JSON String
---------------------

.. code-block:: bash

   python -m je_mail_thunder --execute_str '[["print", ["Hello from CLI!"]]]'

This parses the JSON string and executes it directly.

.. note::

   **Windows note:** On Windows platforms (``win32``, ``cygwin``, ``msys``), the
   JSON string is double-parsed (``json.loads`` is called twice) to handle shell
   escaping differences. You may need to wrap the string in extra quotes:

   .. code-block:: batch

      python -m je_mail_thunder --execute_str "\"[[\\\"print\\\", [\\\"Hello!\\\"]]]]\""

   On Linux/macOS, single quoting works directly:

   .. code-block:: bash

      python -m je_mail_thunder --execute_str '[["print", ["Hello!"]]]'

----

Create a Project
----------------

.. code-block:: bash

   python -m je_mail_thunder -c /path/to/project

This creates a project directory with template files at the specified path.
See :doc:`project_templates` for details on the generated structure.

----

Exit Codes
----------

- **0** — All actions executed successfully
- **1** — An error occurred (exception printed to ``stderr``)

----

Examples
--------

**Send an email from the command line:**

.. code-block:: bash

   # Create a JSON action file
   cat > send.json << 'EOF'
   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
         "message_content": "Hello from CLI!",
         "message_setting_dict": {
           "Subject": "CLI Test",
           "To": "receiver@gmail.com",
           "From": "sender@gmail.com"
         }
       }],
       ["smtp_quit"]
     ]
   }
   EOF

   # Execute it
   python -m je_mail_thunder -e send.json

**Run multiple action files:**

.. code-block:: bash

   # Create action directory
   mkdir -p actions/

   # Copy/create action files
   cp send.json actions/
   cp read.json actions/

   # Execute all
   python -m je_mail_thunder -d actions/

**Scaffold a new project:**

.. code-block:: bash

   python -m je_mail_thunder -c /home/user/projects
   # Creates /home/user/projects/MailThunder/ with templates
