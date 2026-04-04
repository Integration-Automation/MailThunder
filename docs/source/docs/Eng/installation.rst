Installation
============

This page covers all the ways to install MailThunder.

Requirements
------------

- **Python 3.9** or later
- No additional dependencies beyond the Python standard library
- ``pip`` for package installation

Install from PyPI
-----------------

**Stable release:**

.. code-block:: bash

   pip install je_mail_thunder

**Development release** (latest features, may be unstable):

.. code-block:: bash

   pip install je_mail_thunder_dev

Install from Source
-------------------

Clone the repository and install in editable (development) mode:

.. code-block:: bash

   git clone https://github.com/Integration-Automation/MailThunder.git
   cd MailThunder
   pip install -e .

Install Development Dependencies
---------------------------------

If you plan to contribute or run the test suite:

.. code-block:: bash

   pip install -r dev_requirements.txt

This installs:

- ``pytest`` — for running unit tests
- ``coverage`` — for code coverage reports

Verify Installation
-------------------

After installing, verify that MailThunder is available:

.. code-block:: bash

   python -c "import je_mail_thunder; print('MailThunder installed successfully')"

You can also check the version via PyPI metadata:

.. code-block:: bash

   pip show je_mail_thunder

Upgrade
-------

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade je_mail_thunder

Uninstall
---------

.. code-block:: bash

   pip uninstall je_mail_thunder
