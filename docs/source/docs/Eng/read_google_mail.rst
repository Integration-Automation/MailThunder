Read Google Mail via IMAP
----

.. code-block:: python

    from je_mail_thunder import IMAPWrapper, set_mail_thunder_os_environ

    # Set imap host
    imap_host = 'imap.gmail.com'
    # Init IMAPWrapper
    imap_wrapper = IMAPWrapper(host=imap_host)

    set_mail_thunder_os_environ(
        "test_user", # your user
        "test_password" # your password
    )

    imap_wrapper.later_init()
    # Select INBOX
    imap_wrapper.select()
    # Get mail list
    mail_list = imap_wrapper.mail_content_list()
    # Print SUBJECT FROM TO BODY
    for mail in mail_list:
        print(mail.get("SUBJECT"))
        print(mail.get("FROM"))
        print(mail.get("TO"))
        print(mail.get("BODY"))
    # Quit
    imap_wrapper.quit()
