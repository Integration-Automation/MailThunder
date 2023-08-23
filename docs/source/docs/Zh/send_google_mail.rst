寄送郵件使用 Google 信箱
----

.. code-block:: python

    from je_mail_thunder import SMTPWrapper
    from je_mail_thunder import mail_thunder_content_data_dict

    # 初始化 SMTPWrapper
    smtp_wrapper = SMTPWrapper()
    smtp_wrapper.smtp_later_init()
    user = mail_thunder_content_data_dict.get("user")
    # 讀取 html 檔案
    with open("test.html", "r+") as file:
        html_string = file.read()
    # 建立訊息
    message = smtp_wrapper.smtp_create_message_with_attach(
        html_string,
        {"Subject": "test_subject", "To": user, "From": user},
        "test.html", use_html=True)
    # 傳送訊息
    smtp_wrapper.send_message(message)
    # 退出
    smtp_wrapper.quit()

