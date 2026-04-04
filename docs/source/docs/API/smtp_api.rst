MailThunder SMTP API
====================

**Module:** ``je_mail_thunder.smtp.smtp_wrapper``

``SMTPWrapper`` extends ``smtplib.SMTP_SSL`` to provide a high-level interface for sending emails
with support for plain text, HTML, and attachments.

----

Class Definition
----------------

.. code-block:: python

    class SMTPWrapper(smtplib.SMTP_SSL):
        """
        SMTP wrapper with auto-login and message creation utilities.

        Inherits all methods from smtplib.SMTP_SSL.
        Supports context manager (with statement).

        :param host: SMTP server hostname (default: "smtp.gmail.com")
        :param port: SMTP server port (default: 465, SSL)
        """

        def __init__(self, host: str = "smtp.gmail.com", port: int = 465):
            ...

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

----

Methods
-------

later_init
~~~~~~~~~~

.. code-block:: python

    def later_init(self):
        """
        Attempt to log in to the SMTP server.

        Calls try_to_login_with_env_or_content() internally.
        Catches and logs all exceptions without raising.

        :return: None
        """

**Example:**

.. code-block:: python

    smtp = SMTPWrapper()
    smtp.later_init()

----

create_message
~~~~~~~~~~~~~~

.. code-block:: python

    @staticmethod
    def create_message(message_content: str, message_setting_dict: dict, **kwargs) -> EmailMessage:
        """
        Create a new EmailMessage instance.

        :param message_content: The email body content (plain text).
        :param message_setting_dict: A dict of email headers.
            Required keys: "Subject", "From", "To".
            Optional keys: "Cc", "Bcc", "Reply-To", and any other valid EmailMessage header.
        :param kwargs: Additional keyword arguments passed to the EmailMessage constructor.
        :return: An EmailMessage instance ready to be sent.
        """

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

create_message_with_attach
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    @staticmethod
    def create_message_with_attach(
        message_content: str,
        message_setting_dict: dict,
        attach_file: str,
        use_html: bool = False
    ) -> MIMEMultipart:
        """
        Create a new MIMEMultipart message with an attachment.

        The MIME type of the attachment is automatically detected using
        mimetypes.guess_type(). Supported categories:
        - text/*: read as text
        - image/*: read as binary image
        - audio/*: read as binary audio
        - other: read as binary with application/octet-stream fallback

        :param message_content: The email body content (plain text or HTML).
        :param message_setting_dict: A dict of email headers (Subject, From, To, etc.).
        :param attach_file: Absolute or relative path to the file to attach.
        :param use_html: If True, the message_content is treated as HTML (default: False).
        :return: A MIMEMultipart instance with the attachment.
        """

**Example:**

.. code-block:: python

    message = SMTPWrapper.create_message_with_attach(
        message_content="See attached.",
        message_setting_dict={
            "Subject": "Report",
            "From": "sender@gmail.com",
            "To": "receiver@gmail.com"
        },
        attach_file="/path/to/report.pdf",
        use_html=False
    )

----

create_message_and_send
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def create_message_and_send(self, message_content: str, message_setting_dict: dict, **kwargs):
        """
        Create a new EmailMessage and immediately send it.

        Combines create_message() and send_message() in one call.

        :param message_content: The email body content (plain text).
        :param message_setting_dict: A dict of email headers (Subject, From, To, etc.).
        :param kwargs: Additional keyword arguments passed to create_message().
        :return: None
        """

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

create_message_with_attach_and_send
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def create_message_with_attach_and_send(
        self,
        message_content: str,
        message_setting_dict: dict,
        attach_file: str,
        use_html: bool = False
    ):
        """
        Create a new MIMEMultipart message with an attachment and immediately send it.

        Combines create_message_with_attach() and send_message() in one call.

        :param message_content: The email body content (plain text or HTML).
        :param message_setting_dict: A dict of email headers (Subject, From, To, etc.).
        :param attach_file: Path to the file to attach.
        :param use_html: If True, the message_content is treated as HTML (default: False).
        :return: None
        """

**Example:**

.. code-block:: python

    with SMTPWrapper() as smtp:
        smtp.later_init()
        smtp.create_message_with_attach_and_send(
            message_content="Please review the attached document.",
            message_setting_dict={
                "Subject": "Document Review",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            },
            attach_file="/path/to/document.pdf",
            use_html=False
        )

----

try_to_login_with_env_or_content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def try_to_login_with_env_or_content(self) -> bool:
        """
        Attempt to log in using credentials from config file or environment variables.

        Authentication flow:
        1. Try to read mail_thunder_content.json from the current working directory.
        2. If found and valid, log in with "user" and "password" keys.
        3. If not found, read mail_thunder_user and mail_thunder_user_password env vars.
        4. If env vars are set, log in with those credentials.

        :return: True if login succeeded, False otherwise.
        """

----

quit
~~~~

.. code-block:: python

    def quit(self):
        """
        Disconnect from the SMTP server and close the connection.

        Resets login_state to False. Catches and logs exceptions
        (e.g., if already disconnected).

        :return: None
        """

----

Global Instance
---------------

.. code-block:: python

    smtp_instance: SMTPWrapper | None

A pre-created ``SMTPWrapper`` instance that attempts to connect to ``smtp.gmail.com:465``
at import time. Set to ``None`` if the connection fails (e.g., no network).

Used internally by the JSON scripting executor.

----

Context Manager
---------------

``SMTPWrapper`` supports the ``with`` statement:

.. code-block:: python

    with SMTPWrapper() as smtp:
        smtp.later_init()
        # ... send emails ...
    # smtp.quit() is called automatically on exit

----

Inherited Methods
-----------------

Since ``SMTPWrapper`` extends ``smtplib.SMTP_SSL``, all standard SMTP methods are available:

- ``login(user, password)`` — Manual SMTP authentication
- ``send_message(msg)`` — Send an ``EmailMessage`` or ``MIMEMultipart``
- ``sendmail(from_addr, to_addrs, msg)`` — Low-level send
- ``ehlo()`` / ``helo()`` — SMTP handshake
- ``noop()`` — No-operation (keepalive)
- ``starttls()`` — Upgrade to TLS (not needed for SSL connections)

See `smtplib.SMTP_SSL documentation <https://docs.python.org/3/library/smtplib.html#smtplib.SMTP_SSL>`_
for the full list.

----
