使用 IMAP 讀取郵件
==================

MailThunder 的 ``IMAPWrapper`` 繼承自 ``imaplib.IMAP4_SSL``，提供讀取、搜尋和匯出郵件的方法。
預設連接 ``imap.gmail.com`` (SSL)。

----

基本設定
--------

讀取郵件之前，您需要先設定認證。請參考 :doc:`zh_index` 頁面的認證設定說明。

.. note::

    **Gmail 使用者注意：** 請確認已在 Gmail 設定中
    `啟用 IMAP <https://support.google.com/mail/answer/7126229>`_。

----

讀取收件匣中的所有郵件
----------------------

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    with IMAPWrapper() as imap:
        imap.later_init()  # 使用設定檔或環境變數登入
        imap.select_mailbox("INBOX")
        emails = imap.mail_content_list()
        for mail in emails:
            print(f"主旨: {mail['SUBJECT']}")
            print(f"寄件者: {mail['FROM']}")
            print(f"收件者: {mail['TO']}")
            print(f"內文: {mail['BODY'][:200]}...")
            print("---")

每封郵件以字典格式回傳：

.. code-block:: python

    {
        "SUBJECT": "郵件主旨",
        "FROM": "sender@example.com",
        "TO": "receiver@example.com",
        "BODY": "郵件內文..."
    }

----

搜尋郵件
--------

``search_str`` 參數遵循
`IMAP SEARCH 指令語法 (RFC 3501) <https://datatracker.ietf.org/doc/html/rfc3501#section-6.4.4>`_。

**依寄件者搜尋：**

.. code-block:: python

    emails = imap.mail_content_list(search_str='FROM "someone@example.com"')

**依主旨搜尋：**

.. code-block:: python

    emails = imap.mail_content_list(search_str='SUBJECT "重要"')

**搜尋未讀郵件：**

.. code-block:: python

    emails = imap.mail_content_list(search_str="UNSEEN")

**依日期搜尋：**

.. code-block:: python

    emails = imap.mail_content_list(search_str='SINCE "01-Jan-2025"')

**搜尋全部郵件（預設）：**

.. code-block:: python

    emails = imap.mail_content_list(search_str="ALL")

----

匯出所有郵件為檔案
------------------

將選定信箱中的每封郵件匯出為本地檔案：

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX")
        imap.output_all_mail_as_file()

每封郵件以主旨命名。若主旨重複，會自動加上遞增數字後綴
（例如 ``My Subject0``、``My Subject1``）。

----

取得原始郵件資料
----------------

若需要進階操作，``search_mailbox()`` 回傳原始郵件資料：

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX")
        raw_list = imap.search_mailbox()
        for response, decode_info, message in raw_list:
            # response: IMAP 回應狀態（如 "OK"）
            # decode_info: 原始 RFC822 解碼標頭位元組
            # message: email.message.Message 物件（完整存取所有標頭與部分）
            print(f"主旨: {message.get('Subject')}")
            print(f"日期: {message.get('Date')}")

----

唯讀模式
--------

以唯讀模式開啟信箱，避免將郵件標記為已讀：

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    with IMAPWrapper() as imap:
        imap.later_init()
        imap.select_mailbox("INBOX", readonly=True)
        emails = imap.mail_content_list()

----

手動登入（不使用 Context Manager）
-----------------------------------

.. code-block:: python

    from je_mail_thunder import IMAPWrapper, set_mail_thunder_os_environ

    imap_host = "imap.gmail.com"
    imap_wrapper = IMAPWrapper(host=imap_host)

    set_mail_thunder_os_environ(
        "your_email@gmail.com",
        "your_app_password"
    )

    imap_wrapper.later_init()
    # 選擇收件匣
    imap_wrapper.select_mailbox("INBOX")
    # 取得郵件列表
    mail_list = imap_wrapper.mail_content_list()
    # 輸出基本資訊
    for mail in mail_list:
        print(mail.get("SUBJECT"))
        print(mail.get("FROM"))
        print(mail.get("TO"))
        print(mail.get("BODY"))
    # 離開
    imap_wrapper.quit()

----

使用其他 IMAP 服務供應商
-------------------------

透過建構子傳入自訂 ``host``：

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    # Outlook
    imap = IMAPWrapper(host="outlook.office365.com")

    # Yahoo
    imap = IMAPWrapper(host="imap.mail.yahoo.com")

    # 自訂伺服器
    imap = IMAPWrapper(host="imap.example.com")

----

使用 JSON 腳本引擎讀取
-----------------------

透過 JSON 腳本引擎讀取與匯出郵件：

.. code-block:: json

    {
        "auto_control": [
            ["MT_imap_later_init"],
            ["MT_imap_select_mailbox", {"mailbox": "INBOX", "readonly": true}],
            ["MT_imap_mail_content_list", {"search_str": "UNSEEN"}],
            ["MT_imap_quit"]
        ]
    }

匯出所有郵件：

.. code-block:: json

    {
        "auto_control": [
            ["MT_imap_later_init"],
            ["MT_imap_select_mailbox"],
            ["MT_imap_output_all_mail_as_file"],
            ["MT_imap_quit"]
        ]
    }

透過命令列執行：

.. code-block:: bash

    python -m je_mail_thunder -e /path/to/read_action.json

----
