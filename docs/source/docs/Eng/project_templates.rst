Project Templates
=================

MailThunder can scaffold a new project directory with pre-built template files,
giving you a ready-to-use starting point for email automation.

----

Creating a Project
------------------

**From Python:**

.. code-block:: python

   from je_mail_thunder import create_project_dir

   # Create in the current working directory with default name "MailThunder"
   create_project_dir()

   # Create at a specific path with a custom name
   create_project_dir(project_path="/path/to/projects", parent_name="MyMailProject")

**From CLI:**

.. code-block:: bash

   python -m je_mail_thunder -c /path/to/project

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Parameter
     - Default
     - Description
   * - ``project_path``
     - ``os.getcwd()``
     - Directory where the project folder will be created
   * - ``parent_name``
     - ``"MailThunder"``
     - Name of the project root directory

----

Generated Structure
-------------------

.. code-block:: text

   MyMailProject/
     keyword/
       keyword1.json          # SMTP send email template
       keyword2.json          # IMAP read and export template
       bad_keyword_1.json     # Package loading example (security warning)
     executor/
       executor_one_file.py   # Execute a single action file
       executor_folder.py     # Execute all action files in a directory
       executor_bad_file.py   # Bad practice example (security warning)

----

Template Files: keyword/
-------------------------

**keyword1.json** — SMTP send email template:

.. code-block:: json

   [
     ["MT_smtp_later_init"],
     ["MT_smtp_create_message_and_send", {
       "message_content": "test",
       "message_setting_dict": {
         "Subject": "test_subject",
         "To": "example@gmail.com",
         "From": "example@gmail.com"
       }
     }],
     ["smtp_quit"]
   ]

**keyword2.json** — IMAP read and export template:

.. code-block:: json

   [
     ["MT_imap_later_init"],
     ["MT_imap_select_mailbox"],
     ["MT_imap_output_all_mail_as_file"]
   ]

**bad_keyword_1.json** — Package loading example:

.. code-block:: json

   [
     ["MT_add_package_to_executor", ["os"]],
     ["os_system", ["python --version"]],
     ["os_system", ["python -m pip --version"]]
   ]

.. warning::

   ``bad_keyword_1.json`` demonstrates loading the ``os`` package into the executor,
   which enables running arbitrary system commands. This is included as an educational
   example of what **not** to do in production. Never load ``os``, ``subprocess``, or
   similar packages when processing untrusted input.

----

Template Files: executor/
--------------------------

**executor_one_file.py** — Execute a single action file:

.. code-block:: python

   from je_mail_thunder import execute_action, read_action_json

   execute_action(
       read_action_json(
           r"/path/to/MyMailProject/keyword/keyword1.json"
       )
   )

**executor_folder.py** — Execute all JSON action files in a directory:

.. code-block:: python

   from je_mail_thunder import execute_files, get_dir_files_as_list

   execute_files(
       get_dir_files_as_list(
           r"/path/to/MyMailProject/keyword"
       )
   )

**executor_bad_file.py** — Bad practice example:

.. code-block:: python

   # This example is primarily intended to remind users of the importance of verifying input.
   from je_mail_thunder import execute_action, read_action_json

   execute_action(
       read_action_json(
           r"/path/to/MyMailProject/keyword/bad_keyword_1.json"
       )
   )

.. note::

   The ``{temp}`` placeholder in template source code is replaced with the actual
   absolute path during project creation.

----

Customizing Templates
---------------------

After scaffolding, you can freely modify the generated files:

1. Edit ``keyword/*.json`` files to match your email workflow
2. Update the email addresses, subjects, and content
3. Add new ``.json`` action files to the ``keyword/`` directory
4. Modify ``executor/*.py`` files to add error handling or custom logic

**Example: Adding a new workflow:**

Create ``keyword/weekly_report.json``:

.. code-block:: json

   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_with_attach_and_send", {
         "message_content": "Please find the weekly report attached.",
         "message_setting_dict": {
           "Subject": "Weekly Report",
           "To": "team@company.com",
           "From": "reporter@company.com"
         },
         "attach_file": "/data/reports/weekly.pdf",
         "use_html": false
       }],
       ["smtp_quit"]
     ]
   }

Then execute it:

.. code-block:: bash

   python -m je_mail_thunder -e MyMailProject/keyword/weekly_report.json
