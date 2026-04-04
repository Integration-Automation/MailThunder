寄送郵件 (SMTP)
================

MailThunder 的 ``SMTPWrapper`` 繼承自 ``smtplib.SMTP_SSL``，提供便捷的方法來建立和寄送郵件。
支援純文字、HTML 和檔案附件。

預設連接：``smtp.gmail.com:465`` (SSL)。

----

寄送純文字郵件
--------------

使用 context manager 的最簡方式：

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   with SMTPWrapper() as smtp:
       smtp.later_init()
       smtp.create_message_and_send(
           message_content="Hello from MailThunder!",
           message_setting_dict={
               "Subject": "測試郵件",
               "From": "sender@gmail.com",
               "To": "receiver@gmail.com"
           }
       )

``message_setting_dict`` 接受任何有效的 ``EmailMessage`` 標頭鍵：

- ``Subject`` — 郵件主旨
- ``From`` — 寄件者地址
- ``To`` — 收件者地址
- ``Cc`` — 副本收件者
- ``Bcc`` — 密件副本收件者
- ``Reply-To`` — 回覆地址
- 其他 RFC 2822 標頭

----

寄送附件郵件
------------

MailThunder 使用 ``mimetypes.guess_type()`` 自動偵測附件的 MIME 類型：

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

**MIME 類型偵測：**

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - 類別
     - MIME 類型
     - 副檔名
   * - 文字
     - ``text/*``
     - ``.txt``、``.csv``、``.html``、``.xml``、``.json``
   * - 圖片
     - ``image/*``
     - ``.png``、``.jpg``、``.jpeg``、``.gif``、``.svg``、``.bmp``
   * - 音訊
     - ``audio/*``
     - ``.mp3``、``.wav``、``.ogg``、``.flac``
   * - 其他
     - ``application/octet-stream``
     - ``.pdf``、``.zip``、``.exe``、``.docx``、``.xlsx`` 等

附件以 ``Content-Disposition: attachment`` 加入，並使用檔名設定 ``Content-ID`` 標頭。

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
       <ul>
           <li>功能一</li>
           <li>功能二</li>
       </ul>
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
           attach_file="/path/to/style.css",
           use_html=True
       )

當 ``use_html=True`` 時，內文以 ``MIMEText(content, "html")`` 包裝，
而非預設的 ``MIMEText(content)`` (預設為 ``"plain"``)。

----

分步操作：先建立訊息再寄送
---------------------------

分開建立訊息與寄送，獲得更多控制：

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   with SMTPWrapper() as smtp:
       smtp.later_init()

       # 步驟一：建立訊息物件（回傳 EmailMessage）
       message = smtp.create_message(
           message_content="你好！",
           message_setting_dict={
               "Subject": "分步郵件",
               "From": "sender@gmail.com",
               "To": "receiver@gmail.com"
           }
       )

       # 可在寄送前檢查或修改訊息
       print(message["Subject"])  # "分步郵件"

       # 步驟二：寄送（繼承自 SMTP_SSL）
       smtp.send_message(message)

建立附件訊息：

.. code-block:: python

   # 步驟一：建立附件訊息（回傳 MIMEMultipart）
   message = smtp.create_message_with_attach(
       message_content="請查看附件。",
       message_setting_dict={
           "Subject": "報告",
           "From": "sender@gmail.com",
           "To": "receiver@gmail.com"
       },
       attach_file="/path/to/report.pdf",
       use_html=False
   )

   # 步驟二：寄送
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

.. note::

   MailThunder 使用 ``SMTP_SSL``（連接時即啟用 SSL）。若您的供應商要求
   在 587 埠使用 STARTTLS，您可能需要直接使用底層 ``smtplib``
   或繼承 ``SMTPWrapper``。

----

手動登入（不使用 Context Manager）
-----------------------------------

.. code-block:: python

   from je_mail_thunder import SMTPWrapper
   from je_mail_thunder import mail_thunder_content_data_dict

   smtp = SMTPWrapper()

   # 手動注入認證資訊
   mail_thunder_content_data_dict.update({
       "user": "your_email@gmail.com",
       "password": "your_app_password",
   })

   # 登入
   smtp.try_to_login_with_env_or_content()
   print(smtp.login_state)  # True

   # 建立並寄送
   user = mail_thunder_content_data_dict.get("user")
   message = smtp.create_message(
       "Hello World!",
       {"Subject": "手動登入", "To": user, "From": user}
   )
   smtp.send_message(message)

   # 完成後務必關閉連線
   smtp.quit()

----

透過 JSON 腳本引擎寄送
-----------------------

使用 JSON 動作檔寄送郵件，無需撰寫 Python 程式碼：

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

附件版本：

.. code-block:: json

   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_with_attach_and_send", {
         "message_content": "請查看附件報告。",
         "message_setting_dict": {
           "Subject": "月報",
           "To": "receiver@gmail.com",
           "From": "sender@gmail.com"
         },
         "attach_file": "/path/to/report.pdf",
         "use_html": false
       }],
       ["smtp_quit"]
     ]
   }

透過命令列執行：

.. code-block:: bash

   python -m je_mail_thunder -e /path/to/send_action.json

----

錯誤處理
--------

所有 ``SMTPWrapper`` 方法內部捕獲例外並記錄。若需自行處理錯誤，
使用 ``try_to_login_with_env_or_content()``（回傳 ``bool``）：

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   smtp = SMTPWrapper()
   success = smtp.try_to_login_with_env_or_content()

   if success:
       smtp.create_message_and_send(
           message_content="已認證！",
           message_setting_dict={
               "Subject": "成功",
               "From": "sender@gmail.com",
               "To": "receiver@gmail.com"
           }
       )
   else:
       print("登入失敗 — 請檢查認證資訊")

   smtp.quit()
