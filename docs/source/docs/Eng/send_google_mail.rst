Sending Emails (SMTP)
=====================

MailThunder's ``SMTPWrapper`` extends ``smtplib.SMTP_SSL`` to provide convenient methods
for creating and sending emails. It supports plain text, HTML, and file attachments.

Default connection: ``smtp.gmail.com:465`` (SSL).

----

Sending a Plain Text Email
---------------------------

The simplest way to send an email using the context manager:

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   with SMTPWrapper() as smtp:
       smtp.later_init()
       smtp.create_message_and_send(
           message_content="Hello from MailThunder!",
           message_setting_dict={
               "Subject": "Test Email",
               "From": "sender@gmail.com",
               "To": "receiver@gmail.com"
           }
       )

The ``message_setting_dict`` accepts any valid ``EmailMessage`` header key:

- ``Subject`` — Email subject line
- ``From`` — Sender address
- ``To`` — Recipient address
- ``Cc`` — Carbon copy recipients
- ``Bcc`` — Blind carbon copy recipients
- ``Reply-To`` — Reply address
- Any other RFC 2822 header

----

Sending an Email with Attachment
--------------------------------

MailThunder auto-detects the MIME type of the attachment file using
``mimetypes.guess_type()``:

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

**MIME type detection:**

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Category
     - MIME Type
     - File Extensions
   * - Text
     - ``text/*``
     - ``.txt``, ``.csv``, ``.html``, ``.xml``, ``.json``
   * - Image
     - ``image/*``
     - ``.png``, ``.jpg``, ``.jpeg``, ``.gif``, ``.svg``, ``.bmp``
   * - Audio
     - ``audio/*``
     - ``.mp3``, ``.wav``, ``.ogg``, ``.flac``
   * - Fallback
     - ``application/octet-stream``
     - ``.pdf``, ``.zip``, ``.exe``, ``.docx``, ``.xlsx``, etc.

The attachment is added with ``Content-Disposition: attachment`` and a
``Content-ID`` header using the filename.

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
       <ul>
           <li>Feature 1</li>
           <li>Feature 2</li>
       </ul>
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
           attach_file="/path/to/style.css",
           use_html=True
       )

When ``use_html=True``, the body is wrapped in ``MIMEText(content, "html")``
instead of ``MIMEText(content)`` (which defaults to ``"plain"``).

----

Two-Step: Create Then Send
--------------------------

Separate message creation from sending for more control:

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   with SMTPWrapper() as smtp:
       smtp.later_init()

       # Step 1: Create the message object (returns EmailMessage)
       message = smtp.create_message(
           message_content="Hello!",
           message_setting_dict={
               "Subject": "Two-Step Email",
               "From": "sender@gmail.com",
               "To": "receiver@gmail.com"
           }
       )

       # Inspect or modify the message before sending
       print(message["Subject"])  # "Two-Step Email"

       # Step 2: Send it (inherited from SMTP_SSL)
       smtp.send_message(message)

For attachments:

.. code-block:: python

   # Step 1: Create with attachment (returns MIMEMultipart)
   message = smtp.create_message_with_attach(
       message_content="See attached.",
       message_setting_dict={
           "Subject": "Report",
           "From": "sender@gmail.com",
           "To": "receiver@gmail.com"
       },
       attach_file="/path/to/report.pdf",
       use_html=False
   )

   # Step 2: Send
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

.. note::

   MailThunder uses ``SMTP_SSL`` (implicit SSL on connect). If your provider
   requires STARTTLS on port 587, you may need to use the underlying
   ``smtplib`` directly or subclass ``SMTPWrapper``.

----

Manual Login Without Context Manager
--------------------------------------

If you prefer explicit lifecycle management:

.. code-block:: python

   from je_mail_thunder import SMTPWrapper
   from je_mail_thunder import mail_thunder_content_data_dict

   smtp = SMTPWrapper()

   # Inject credentials manually
   mail_thunder_content_data_dict.update({
       "user": "your_email@gmail.com",
       "password": "your_app_password",
   })

   # Login
   smtp.try_to_login_with_env_or_content()
   print(smtp.login_state)  # True

   # Create and send
   user = mail_thunder_content_data_dict.get("user")
   message = smtp.create_message(
       "Hello World!",
       {"Subject": "Manual Login", "To": user, "From": user}
   )
   smtp.send_message(message)

   # Always quit when done
   smtp.quit()

----

Sending via JSON Scripting Engine
---------------------------------

Send emails without writing Python code by using a JSON action file:

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

With attachment:

.. code-block:: json

   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_with_attach_and_send", {
         "message_content": "Report attached.",
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

Execute via CLI:

.. code-block:: bash

   python -m je_mail_thunder -e /path/to/send_action.json

----

Sending via Command Line
-------------------------

Execute a JSON string directly from the terminal:

.. code-block:: bash

   python -m je_mail_thunder --execute_str '[["MT_smtp_later_init"], ["MT_smtp_create_message_and_send", {"message_content": "Hello!", "message_setting_dict": {"Subject": "CLI Email", "To": "receiver@gmail.com", "From": "sender@gmail.com"}}], ["smtp_quit"]]'

----

Error Handling
--------------

All ``SMTPWrapper`` methods catch exceptions internally and log them. If you need
to handle errors yourself, use ``try_to_login_with_env_or_content()`` which returns
a ``bool``:

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   smtp = SMTPWrapper()
   success = smtp.try_to_login_with_env_or_content()

   if success:
       smtp.create_message_and_send(
           message_content="Authenticated!",
           message_setting_dict={
               "Subject": "Success",
               "From": "sender@gmail.com",
               "To": "receiver@gmail.com"
           }
       )
   else:
       print("Login failed — check credentials")

   smtp.quit()
