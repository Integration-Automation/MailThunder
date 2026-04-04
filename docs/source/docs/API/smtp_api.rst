SMTPWrapper API
===============

**Module:** ``je_mail_thunder.smtp.smtp_wrapper``

``SMTPWrapper`` extends ``smtplib.SMTP_SSL`` to provide a high-level interface for
sending emails with support for plain text, HTML, and attachments.

----

Class Definition
----------------

.. code-block:: python

   class SMTPWrapper(smtplib.SMTP_SSL):
       """
       SMTP wrapper with auto-login and message creation utilities.

       Inherits all methods from smtplib.SMTP_SSL.
       Supports context manager (with statement).
       """

       def __init__(self, host: str = "smtp.gmail.com", port: int = 465):
           ...

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Default
     - Description
   * - ``host``
     - ``"smtp.gmail.com"``
     - SMTP server hostname
   * - ``port``
     - ``465``
     - SMTP server port (SSL)

----

Properties
----------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``login_state``
     - ``bool``
     - ``True`` if the SMTP session is authenticated, ``False`` otherwise.
       Set by ``try_to_login_with_env_or_content()`` and reset by ``quit()``.

----

Methods
-------

later_init()
~~~~~~~~~~~~

.. code-block:: python

   def later_init(self) -> None

Attempt to log in to the SMTP server. Calls ``try_to_login_with_env_or_content()``
internally. Catches and logs all exceptions without raising.

**Example:**

.. code-block:: python

   smtp = SMTPWrapper()
   smtp.later_init()

----

create_message()
~~~~~~~~~~~~~~~~~

.. code-block:: python

   @staticmethod
   def create_message(
       message_content: str,
       message_setting_dict: dict,
       **kwargs
   ) -> EmailMessage

Create a new ``EmailMessage`` instance.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``message_content``
     - ``str``
     - The email body content (plain text)
   * - ``message_setting_dict``
     - ``dict``
     - Email headers. Required: ``"Subject"``, ``"From"``, ``"To"``.
       Optional: ``"Cc"``, ``"Bcc"``, ``"Reply-To"``, any RFC 2822 header.
   * - ``**kwargs``
     - ``dict``
     - Additional keyword arguments passed to the ``EmailMessage`` constructor

**Returns:** ``EmailMessage`` instance.

**Example:**

.. code-block:: python

   message = SMTPWrapper.create_message(
       message_content="Hello!",
       message_setting_dict={
           "Subject": "Test",
           "From": "sender@gmail.com",
           "To": "receiver@gmail.com"
       }
   )

----

create_message_with_attach()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @staticmethod
   def create_message_with_attach(
       message_content: str,
       message_setting_dict: dict,
       attach_file: str,
       use_html: bool = False
   ) -> MIMEMultipart

Create a new ``MIMEMultipart`` message with an attachment. MIME type is
auto-detected using ``mimetypes.guess_type()``.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``message_content``
     - ``str``
     - Email body (plain text or HTML)
   * - ``message_setting_dict``
     - ``dict``
     - Email headers (Subject, From, To, etc.)
   * - ``attach_file``
     - ``str``
     - Path to the file to attach
   * - ``use_html``
     - ``bool``
     - If ``True``, body is ``MIMEText(content, "html")``. Default: ``False``.

**Returns:** ``MIMEMultipart`` instance.

**MIME type handling:**

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Main Type
     - Handler
     - Class
   * - ``text``
     - ``open(file, "r+")``
     - ``MIMEText``
   * - ``image``
     - ``open(file, "rb")``
     - ``MIMEImage``
   * - ``audio``
     - ``open(file, "rb")``
     - ``MIMEAudio``
   * - other
     - ``open(file, "rb")``
     - ``MIMEBase`` with ``set_payload()``

The attachment gets ``Content-Disposition: attachment`` and ``Content-ID`` headers
set to the filename.

----

create_message_and_send()
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def create_message_and_send(
       self,
       message_content: str,
       message_setting_dict: dict,
       **kwargs
   ) -> None

Create a new ``EmailMessage`` and immediately send it via ``send_message()``.

**Parameters:** Same as ``create_message()``.

**Example:**

.. code-block:: python

   with SMTPWrapper() as smtp:
       smtp.later_init()
       smtp.create_message_and_send(
           message_content="Hello!",
           message_setting_dict={
               "Subject": "Quick Email",
               "From": "sender@gmail.com",
               "To": "receiver@gmail.com"
           }
       )

----

create_message_with_attach_and_send()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def create_message_with_attach_and_send(
       self,
       message_content: str,
       message_setting_dict: dict,
       attach_file: str,
       use_html: bool = False
   ) -> None

Create a ``MIMEMultipart`` message with attachment and immediately send it.

**Parameters:** Same as ``create_message_with_attach()``.

----

try_to_login_with_env_or_content()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def try_to_login_with_env_or_content(self) -> bool

Attempt to log in using credentials from the config file or environment variables.

**Authentication flow:**

1. Read ``mail_thunder_content.json`` from ``Path.cwd()``
2. If valid ``user`` + ``password`` keys found → ``self.login(user, password)``
3. Else read ``mail_thunder_user`` + ``mail_thunder_user_password`` env vars
4. If env vars set → ``self.login(user, password)``
5. On ``SMTPAuthenticationError`` → log error, return ``False``

**Returns:** ``True`` if login succeeded, ``False`` otherwise.
Sets ``self.login_state`` accordingly.

----

quit()
~~~~~~

.. code-block:: python

   def quit(self) -> None

Disconnect from the SMTP server. Resets ``login_state`` to ``False``.
Catches and logs exceptions (e.g., if already disconnected).

----

Context Manager
---------------

``SMTPWrapper`` supports the ``with`` statement. ``quit()`` is called on exit:

.. code-block:: python

   with SMTPWrapper() as smtp:
       smtp.later_init()
       smtp.create_message_and_send(...)
   # smtp.quit() called automatically

----

Global Instance
---------------

.. code-block:: python

   smtp_instance: SMTPWrapper | None

A pre-created ``SMTPWrapper`` instance that attempts to connect to
``smtp.gmail.com:465`` at import time. Set to ``None`` if the connection fails.
Used internally by the JSON scripting executor.

----

Inherited from SMTP_SSL
------------------------

All standard ``smtplib.SMTP_SSL`` methods are available:

- ``login(user, password)`` — Manual authentication
- ``send_message(msg)`` — Send an ``EmailMessage`` or ``MIMEMultipart``
- ``sendmail(from_addr, to_addrs, msg)`` — Low-level send
- ``ehlo()`` / ``helo()`` — SMTP handshake
- ``noop()`` — No-operation (keepalive)

See `smtplib documentation <https://docs.python.org/3/library/smtplib.html>`_
for the full reference.
