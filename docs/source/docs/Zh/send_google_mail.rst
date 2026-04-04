使用 SMTP 寄送郵件
==================

MailThunder 的 ``SMTPWrapper`` 繼承自 ``smtplib.SMTP_SSL``，提供便捷的方法來建立和寄送郵件。
預設連接 ``smtp.gmail.com``，埠號 ``465`` (SSL)。

----

基本設定
--------

寄送郵件之前，您需要先設定認證。請參考 :doc:`zh_index` 頁面的認證設定說明。

----

寄送純文字郵件
--------------

使用 context manager 的最簡方式：

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    with SMTPWrapper() as smtp:
        smtp.later_init()  # 使用設定檔或環境變數登入
        smtp.create_message_and_send(
            message_content="Hello from MailThunder!",
            message_setting_dict={
                "Subject": "測試郵件",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            }
        )

``message_setting_dict`` 支援所有 ``EmailMessage`` 標頭鍵值，
包含 ``Subject``、``From``、``To``、``Cc``、``Bcc``、``Reply-To`` 等。

----

寄送附件郵件
------------

MailThunder 會自動偵測附件的 MIME 類型：

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    with SMTPWrapper() as smtp:
        smtp.later_init()
        smtp.create_message_with_attach_and_send(
            message_content="請查看附件。",
            message_setting_dict={
                "Subject": "附件郵件",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            },
            attach_file="/path/to/file.pdf",
            use_html=False
        )

**支援的 MIME 類型：**

- **文字** (``text/*``)：``.txt``、``.csv``、``.html``、``.xml``
- **圖片** (``image/*``)：``.png``、``.jpg``、``.gif``、``.svg``
- **音訊** (``audio/*``)：``.mp3``、``.wav``、``.ogg``
- **其他** (``application/octet-stream``)：``.pdf``、``.zip``、``.exe`` 等

----

寄送 HTML 格式郵件
-------------------

將 ``use_html`` 設為 ``True`` 即可寄送 HTML 格式郵件：

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    html_content = """
    <html>
    <body>
        <h1>你好！</h1>
        <p>這是透過 MailThunder 寄送的 <b>HTML 郵件</b>。</p>
    </body>
    </html>
    """

    with SMTPWrapper() as smtp:
        smtp.later_init()
        smtp.create_message_with_attach_and_send(
            message_content=html_content,
            message_setting_dict={
                "Subject": "HTML 郵件",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            },
            attach_file="/path/to/report.html",
            use_html=True
        )

----

分步操作：先建立訊息再寄送
---------------------------

您可以分開建立訊息與寄送，以獲得更多控制：

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    with SMTPWrapper() as smtp:
        smtp.later_init()

        # 步驟一：建立訊息物件
        message = smtp.create_message(
            message_content="你好！",
            message_setting_dict={
                "Subject": "分步郵件",
                "From": "sender@gmail.com",
                "To": "receiver@gmail.com"
            }
        )

        # 步驟二：寄送（繼承自 SMTP_SSL）
        smtp.send_message(message)

----

使用其他 SMTP 服務供應商
-------------------------

透過建構子傳入自訂 ``host`` 和 ``port``：

.. code-block:: python

    from je_mail_thunder import SMTPWrapper

    # Outlook / Office 365
    smtp = SMTPWrapper(host="smtp-mail.outlook.com", port=465)

    # Yahoo Mail
    smtp = SMTPWrapper(host="smtp.mail.yahoo.com", port=465)

    # 自訂 SMTP 伺服器
    smtp = SMTPWrapper(host="mail.example.com", port=465)

----

手動登入（不使用 Context Manager）
-----------------------------------

.. code-block:: python

    from je_mail_thunder import SMTPWrapper
    from je_mail_thunder import mail_thunder_content_data_dict

    smtp_wrapper = SMTPWrapper()

    # 手動設定認證資訊
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

使用 JSON 腳本引擎寄送
-----------------------

您也可以透過 JSON 腳本引擎寄送郵件，無需撰寫 Python 程式碼：

.. code-block:: json

    {
        "auto_control": [
            ["MT_smtp_later_init"],
            ["MT_smtp_create_message_and_send", {
                "message_content": "Hello from scripting engine!",
                "message_setting_dict": {
                    "Subject": "自動化郵件",
                    "To": "receiver@gmail.com",
                    "From": "sender@gmail.com"
                }
            }],
            ["smtp_quit"]
        ]
    }

透過命令列執行：

.. code-block:: bash

    python -m je_mail_thunder -e /path/to/send_action.json

----
