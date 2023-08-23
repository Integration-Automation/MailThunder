Send Google Mail via SMTP
----

.. code-block:: python

    from je_mail_thunder import SMTPWrapper
    from je_mail_thunder import mail_thunder_content_data_dict

    # Init SMTPWrapper
    smtp_wrapper = SMTPWrapper()
    smtp_wrapper.smtp_later_init()
    user = mail_thunder_content_data_dict.get("user")
    # Read html file
    with open("test.html", "r+") as file:
        html_string = file.read()
    # Create message instance
    message = smtp_wrapper.smtp_create_message_with_attach(
        html_string,
        {"Subject": "test_subject", "To": user, "From": user},
        "test.html", use_html=True)
    # Send message instance
    smtp_wrapper.send_message(message)
    # QUIT
    smtp_wrapper.quit()