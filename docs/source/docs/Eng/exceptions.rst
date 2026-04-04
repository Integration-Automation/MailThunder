Exceptions
==========

MailThunder defines a hierarchy of custom exceptions for different error scenarios.
All exceptions inherit from the base ``MailThunderException`` class.

----

Exception Hierarchy
-------------------

.. code-block:: text

   Exception (Python built-in)
     └── MailThunderException
           ├── MailThunderJsonException
           ├── MailThunderContentException
           ├── MailThunderArgparseException
           ├── ExecuteActionException
           ├── AddCommandException
           └── JsonActionException

----

Exception Reference
-------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Exception
     - When Raised
   * - ``MailThunderException``
     - Base exception for all MailThunder errors. Not raised directly.
   * - ``MailThunderJsonException``
     - JSON reformatting failures (invalid JSON data or type errors)
   * - ``MailThunderContentException``
     - Errors reading or writing ``mail_thunder_content.json``
   * - ``MailThunderArgparseException``
     - CLI receives no valid arguments or unknown function
   * - ``ExecuteActionException``
     - Executor receives invalid action format, null action list, or wrong data type
   * - ``AddCommandException``
     - ``add_command_to_executor()`` receives a non-callable value (not a function/method)
   * - ``JsonActionException``
     - JSON action file not found or cannot be saved

----

Error Tags
----------

Each exception is associated with a human-readable error tag string defined in
``je_mail_thunder.utils.exception.exception_tags``:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Error Tag
     - Message
   * - ``mail_thunder_cant_reformat_json_error``
     - ``"Can't reformat json is type right?"``
   * - ``mail_thunder_wrong_json_data_error``
     - ``"Can't parser json"``
   * - ``mail_thunder_content_set_compiler_error``
     - ``"When set compiler using content make an error"``
   * - ``mail_thunder_content_file_error``
     - ``"MailThunder content file error"``
   * - ``mail_thunder_content_login_failed``
     - ``"can't login with mail thunder content"``
   * - ``mail_thunder_service_file_error``
     - ``"service param -s got the wrong data"``
   * - ``mail_thunder_login_error``
     - ``"need set --user and --password to login"``
   * - ``mail_thunder_argparse_get_wrong_function``
     - ``"get unknown function"``
   * - ``add_command_exception``
     - ``"command value type should be as method or function"``
   * - ``executor_list_error``
     - ``"executor receive wrong data list is none or wrong type"``
   * - ``cant_execute_action_error``
     - ``"cant execute action"``
   * - ``cant_find_json_error``
     - ``"cant find json file"``
   * - ``cant_save_json_error``
     - ``"cant save json file"``
   * - ``action_is_null_error``
     - ``"json action is null"``

----

Catching Exceptions
-------------------

You can catch MailThunder exceptions in your code:

.. code-block:: python

   from je_mail_thunder import execute_action
   from je_mail_thunder.utils.exception.exceptions import (
       MailThunderException,
       ExecuteActionException,
       JsonActionException,
   )

   try:
       execute_action([["nonexistent_command"]])
   except ExecuteActionException as e:
       print(f"Executor error: {e}")
   except MailThunderException as e:
       print(f"MailThunder error: {e}")

.. note::

   Most MailThunder methods (especially in ``SMTPWrapper`` and ``IMAPWrapper``) catch
   exceptions internally and log them rather than propagating. Exceptions are more
   commonly raised by the executor, JSON file utilities, and CLI components.
