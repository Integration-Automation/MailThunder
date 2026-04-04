Package Manager
===============

MailThunder's ``PackageManager`` allows you to dynamically load any installed Python
package into the scripting executor at runtime, making all of its functions, built-in
functions, and classes available as action commands.

----

How It Works
------------

When ``MT_add_package_to_executor`` is called with a package name:

1. ``importlib.find_spec()`` checks if the package is installed
2. ``importlib.import_module()`` imports the package
3. ``inspect.getmembers()`` extracts all functions, builtins, and classes
4. Each member is registered in the executor's ``event_dict`` with the naming
   convention ``{package_name}_{member_name}``

.. code-block:: text

   MT_add_package_to_executor("os")
       │
       ▼
   find_spec("os") → found
       │
       ▼
   import_module("os")
       │
       ▼
   getmembers(os, isfunction)  → os_getcwd, os_listdir, os_makedirs, ...
   getmembers(os, isbuiltin)   → os_system, os_open, os_close, ...
   getmembers(os, isclass)     → os_error, ...
       │
       ▼
   All registered in executor.event_dict

----

Usage in JSON Scripts
---------------------

.. code-block:: json

   {
     "auto_control": [
       ["MT_add_package_to_executor", ["os"]],
       ["os_system", ["echo Hello from os.system"]],
       ["os_getcwd"]
     ]
   }

.. code-block:: json

   {
     "auto_control": [
       ["MT_add_package_to_executor", ["json"]],
       ["json_dumps", [{"key": "value"}]]
     ]
   }

----

Usage in Python
---------------

.. code-block:: python

   from je_mail_thunder import execute_action

   execute_action([
       ["MT_add_package_to_executor", ["math"]],
       ["math_sqrt", [144]],
       ["math_factorial", [10]]
   ])

----

Naming Convention
-----------------

All members are prefixed with the package name and an underscore:

.. code-block:: text

   Package "os"    → os_system, os_getcwd, os_path, os_listdir, ...
   Package "json"  → json_dumps, json_loads, json_dump, json_load, ...
   Package "math"  → math_sqrt, math_ceil, math_floor, math_factorial, ...

This prevents name collisions between packages and with built-in commands.

----

Loaded Package Cache
--------------------

The ``PackageManager`` caches loaded packages in ``installed_package_dict``.
If a package has already been loaded, subsequent calls to
``MT_add_package_to_executor`` with the same package name will reuse the
cached import rather than re-importing.

----

What Gets Loaded
----------------

Three categories of members are extracted from each package:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Category
     - Detection
     - Example
   * - Functions
     - ``inspect.isfunction``
     - ``os.getcwd``, ``json.dumps``
   * - Built-in functions
     - ``inspect.isbuiltin``
     - ``os.system``, ``os.open``
   * - Classes
     - ``inspect.isclass``
     - ``os.error``, ``json.JSONDecodeError``

.. note::

   Sub-modules are **not** automatically loaded. For example, loading ``os`` does
   not automatically make ``os.path`` functions available. You would need to
   separately load ``os.path``:

   .. code-block:: json

      {
        "auto_control": [
          ["MT_add_package_to_executor", ["os.path"]],
          ["os.path_join", ["/home", "user", "file.txt"]]
        ]
      }

----

Error Handling
--------------

- If the package is not installed, a ``ModuleNotFoundError`` message is printed
  to ``stderr`` (not raised as an exception)
- If the executor is not available (``None``), an error message is printed
- Import errors during module loading are caught and printed to ``stderr``

----

Security Warning
----------------

.. warning::

   **Loading packages like ``os``, ``subprocess``, ``shutil``, or ``sys`` into
   the executor grants the scripting engine access to system-level operations.**

   This is a significant security risk when:

   - Processing untrusted JSON action files
   - Exposing the socket server to external clients
   - Running in multi-tenant environments

   **Best practices:**

   - Only load packages you explicitly need
   - Never load system packages (``os``, ``subprocess``, ``sys``) in production
   - Validate and sanitize all inputs
   - Do not expose the socket server to untrusted networks
   - Review JSON action files before executing them

   The ``bad_keyword_1.json`` template is included as an educational example of
   what to avoid.
