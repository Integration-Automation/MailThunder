使用 Google 信箱寄送郵件
----

.. code-block:: python

    from je_mail_thunder import SMTPWrapper
    from je_mail_thunder import mail_thunder_content_data_dict

    smtp_wrapper = SMTPWrapper()

    mail_thunder_content_data_dict.update({
        "user": "test_user", # 你的使用者
        "password": "test_password", # 你的密碼 (google 需使用應用程式密碼)
    })

    user = mail_thunder_content_data_dict.get("user")

    smtp_wrapper.try_to_login_with_env_or_content()

    message = smtp_wrapper.create_message("test", {"Subject": "test_subject", "To": user, "From": user})
    smtp_wrapper.send_message(message)
    smtp_wrapper.quit()

