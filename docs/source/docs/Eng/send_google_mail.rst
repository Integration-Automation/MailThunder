Send Emails via SMTP
====================

MailThunder's ``SMTPWrapper`` extends ``smtplib.SMTP_SSL`` to provide convenient methods
for creating and sending emails. By default it connects to ``smtp.gmail.com`` on port ``465`` (SSL).

----

Basic Setup
-----------

Before sending emails, you need to configure authentication. See the
:doc:`eng_index` page for authentication setup instructions.

----

Sending a Plain Text Email
--------------------------

The simplest way to send an email using the context manager:

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    with SMTPWrapper() as smtp:
        smtp.later_init()  # Log in using config file or env vars
        smtp.create_message_and_send(
            message_content="Hello from MailThunder!",
            message_setting_dict={
                "Subject": "Test Email",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            }
        )

The ``message_setting_dict`` supports any valid ``EmailMessage`` header key-value pairs,
including ``Subject``, ``From``, ``To``, ``Cc``, ``Bcc``, ``Reply-To``, etc.

----

Sending an Email with Attachment
--------------------------------

MailThunder automatically detects the MIME type of attachments:

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    with SMTPWrapper() as smtp:
        smtp.later_init()
        smtp.create_message_with_attach_and_send(
            message_content="Please see the attached file.",
            message_setting_dict={
                "Subject": "Email with Attachment",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            },
            attach_file="/path/to/file.pdf",
            use_html=False
        )

**Supported MIME types:**

- **Text** (``text/*``): ``.txt``, ``.csv``, ``.html``, ``.xml``
- **Image** (``image/*``): ``.png``, ``.jpg``, ``.gif``, ``.svg``
- **Audio** (``audio/*``): ``.mp3``, ``.wav``, ``.ogg``
- **Other** (``application/octet-stream``): ``.pdf``, ``.zip``, ``.exe``, etc.

----

Sending an HTML Email
---------------------

Set ``use_html=True`` to send HTML-formatted email content:

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    html_content = """
    <html>
    <body>
        <h1>Hello!</h1>
        <p>This is an <b>HTML email</b> sent via MailThunder.</p>
    </body>
    </html>
    """

    with SMTPWrapper() as smtp:
        smtp.later_init()
        smtp.create_message_with_attach_and_send(
            message_content=html_content,
            message_setting_dict={
                "Subject": "HTML Email",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            },
            attach_file="/path/to/report.html",
            use_html=True
        )

----

Two-Step: Create Then Send
--------------------------

You can separate message creation from sending for more control:

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    with SMTPWrapper() as smtp:
        smtp.later_init()

        # Step 1: Create the message object
        message = smtp.create_message(
            message_content="Hello!",
            message_setting_dict={
                "Subject": "Two-Step Email",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            }
        )

        # Step 2: Send it (inherited from SMTP_SSL)
        smtp.send_message(message)

----

Using a Different SMTP Provider
--------------------------------

Pass custom ``host`` and ``port`` to the constructor:

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    # Outlook / Office 365
    smtp = SMTPWrapper(host="smtp-mail.outlook.com", port=465)

    # Yahoo Mail
    smtp = SMTPWrapper(host="smtp.mail.yahoo.com", port=465)

    # Custom SMTP server
    smtp = SMTPWrapper(host="mail.example.com", port=465)

----

Manual Login (Without Context Manager)
---------------------------------------

.. code-block:: python

    from je_mail_thunder import SMTPWrapper
    from je_mail_thunder import mail_thunder_content_data_dict

    smtp_wrapper = SMTPWrapper()

    # Manually set credentials
    mail_thunder_content_data_dict.update({
        "user": "your_email@gmail.com",
        "password": "your_app_password",
    })

    user = mail_thunder_content_data_dict.get("user")

    smtp_wrapper.try_to_login_with_env_or_content()

    message = smtp_wrapper.create_message(
        "Hello World!",
        {"Subject": "test_subject", "To": user, "From": user}
    )
    smtp_wrapper.send_message(message)
    smtp_wrapper.quit()

----

Sending via JSON Scripting Engine
---------------------------------

You can also send emails using the JSON scripting engine without writing Python code:

.. code-block:: json

    {
        "auto_control": [
            ["MT_smtp_later_init"],
            ["MT_smtp_create_message_and_send", {
                "message_content": "Hello from scripting engine!",
                "message_setting_dict": {
                    "Subject": "Automated Email",
                    "To": "receiver@gmail.com",
                    "From": "sender@gmail.com"
                }
            }],
            ["smtp_quit"]
        ]
    }

Execute the action file via CLI:

.. code-block:: bash

    python -m je_mail_thunder -e /path/to/send_action.json

----

Sending via Command Line
-------------------------

Execute a JSON action string directly from the command line:

.. code-block:: bash

    python -m je_mail_thunder --execute_str '[["MT_smtp_later_init"], ["MT_smtp_create_message_and_send", {"message_content": "Hello!", "message_setting_dict": {"Subject": "CLI Email", "To": "receiver@gmail.com", "From": "sender@gmail.com"}}], ["smtp_quit"]]'

----
