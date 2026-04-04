讀取郵件 (IMAP)
================

MailThunder 的 ``IMAPWrapper`` 繼承自 ``imaplib.IMAP4_SSL``，提供讀取、搜尋和匯出郵件的方法。

預設連接：``imap.gmail.com`` (SSL)。

.. note::

   **Gmail 使用者注意：** 請確認已在 Gmail 設定中
   `啟用 IMAP <https://support.google.com/mail/answer/7126229>`_。

----

讀取收件匣中的所有郵件
----------------------

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       imap.select_mailbox("INBOX")
       emails = imap.mail_content_list()
       for mail in emails:
           print(f"主旨: {mail['SUBJECT']}")
           print(f"寄件者: {mail['FROM']}")
           print(f"收件者: {mail['TO']}")
           print(f"內文: {mail['BODY'][:200]}...")
           print("---")

**回傳的字典格式：**

每封郵件為一個包含四個鍵的字典：

.. code-block:: python

   {
       "SUBJECT": "郵件主旨",         # str — 解碼後的主旨
       "FROM": "sender@example.com",   # str — 寄件者地址
       "TO": "receiver@example.com",   # str — 收件者地址
       "BODY": "郵件內文..."           # str — 內文（已解碼）
   }

對於多部分（multipart）郵件，擷取第一個部分的內文。

----

搜尋郵件
--------

``search_str`` 參數遵循
`IMAP SEARCH 指令語法 (RFC 3501 第 6.4.4 節) <https://datatracker.ietf.org/doc/html/rfc3501#section-6.4.4>`_。

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
   emails = imap.mail_content_list(search_str='BEFORE "31-Dec-2025"')
   emails = imap.mail_content_list(search_str='ON "15-Jun-2025"')

**組合多個條件** (隱含 AND)：

.. code-block:: python

   emails = imap.mail_content_list(search_str='FROM "boss@company.com" UNSEEN')
   emails = imap.mail_content_list(search_str='SINCE "01-Jan-2025" SUBJECT "報告"')

**完整搜尋條件參考：**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 條件
     - 說明
   * - ``ALL``
     - 信箱中所有郵件（預設）
   * - ``UNSEEN``
     - 未讀郵件
   * - ``SEEN``
     - 已讀郵件
   * - ``FLAGGED``
     - 已標記的郵件（Gmail 中的星號郵件）
   * - ``UNFLAGGED``
     - 未標記的郵件
   * - ``ANSWERED``
     - 已回覆的郵件
   * - ``UNANSWERED``
     - 未回覆的郵件
   * - ``DELETED``
     - 已標記刪除的郵件
   * - ``FROM "字串"``
     - 來自指定寄件者的郵件
   * - ``TO "字串"``
     - 寄給指定收件者的郵件
   * - ``CC "字串"``
     - 指定副本收件者的郵件
   * - ``SUBJECT "字串"``
     - 主旨包含指定文字的郵件
   * - ``BODY "字串"``
     - 內文包含指定文字的郵件
   * - ``TEXT "字串"``
     - 標頭或內文包含指定文字的郵件
   * - ``SINCE "DD-Mon-YYYY"``
     - 指定日期當天或之後的郵件（例如 ``"01-Jan-2025"``）
   * - ``BEFORE "DD-Mon-YYYY"``
     - 指定日期之前的郵件
   * - ``ON "DD-Mon-YYYY"``
     - 指定日期當天的郵件
   * - ``LARGER n``
     - 大於 n 位元組的郵件
   * - ``SMALLER n``
     - 小於 n 位元組的郵件
   * - ``NEW``
     - 最近且未讀的郵件
   * - ``OLD``
     - 非最近的郵件

----

匯出所有郵件為檔案
------------------

將選定信箱中的每封郵件匯出為本地檔案：

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       imap.select_mailbox("INBOX")
       exported = imap.output_all_mail_as_file()
       print(f"已匯出 {len(exported)} 封郵件")

**檔案命名規則：**

- 每封郵件儲存在目前工作目錄
- 檔名 = 郵件主旨 + 數字後綴
- 第一封：``My Subject0``
- 重複主旨：``My Subject1``、``My Subject2``、...
- 檔案內容 = 解碼後的郵件內文

----

取得原始郵件資料
----------------

進階用途可使用 ``search_mailbox()`` 取得原始資料：

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       imap.select_mailbox("INBOX")
       raw_list = imap.search_mailbox()
       for response, decode_info, message in raw_list:
           # response:    IMAP 回應狀態字串（例如 "OK"）
           # decode_info: 原始 RFC822 解碼標頭位元組
           # message:     email.message.Message 物件 — 完整的 Python 郵件物件
           print(f"主旨: {message.get('Subject')}")
           print(f"日期: {message.get('Date')}")
           print(f"內容類型: {message.get_content_type()}")

           # 存取所有標頭
           for key in message.keys():
               print(f"  {key}: {message[key]}")

           # 存取多部分郵件的各部分
           if message.is_multipart():
               for i, part in enumerate(message.get_payload()):
                   print(f"  部分 {i}: {part.get_content_type()}")

``message`` 物件是標準的 Python ``email.message.Message``
（使用 ``email.policy.default`` 解析），提供完整的標頭、部分和解碼工具存取。

----

唯讀模式
--------

以唯讀模式開啟信箱，防止副作用（如將郵件標記為已讀）：

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   with IMAPWrapper() as imap:
       imap.later_init()
       success = imap.select_mailbox("INBOX", readonly=True)
       if success:
           emails = imap.mail_content_list()

----

選擇不同的信箱
--------------

除了 ``INBOX``，您可以選擇其他標準或供應商特定的信箱：

.. code-block:: python

   # 標準信箱
   imap.select_mailbox("Sent")
   imap.select_mailbox("Drafts")
   imap.select_mailbox("Trash")

   # Gmail 特定標籤
   imap.select_mailbox("[Gmail]/All Mail")
   imap.select_mailbox("[Gmail]/Starred")
   imap.select_mailbox("[Gmail]/Spam")
   imap.select_mailbox("[Gmail]/Important")

``select_mailbox()`` 方法在選擇成功時回傳 ``True``（IMAP 狀態 ``"OK"``），
否則回傳 ``False``。

----

使用其他 IMAP 服務供應商
-------------------------

透過建構子傳入自訂 ``host``：

.. code-block:: python

   from je_mail_thunder import IMAPWrapper

   # Outlook / Office 365
   imap = IMAPWrapper(host="outlook.office365.com")

   # Yahoo Mail
   imap = IMAPWrapper(host="imap.mail.yahoo.com")

   # 自訂伺服器
   imap = IMAPWrapper(host="imap.example.com")

----

手動登入（不使用 Context Manager）
-----------------------------------

.. code-block:: python

   from je_mail_thunder import IMAPWrapper, set_mail_thunder_os_environ

   imap = IMAPWrapper(host="imap.gmail.com")

   set_mail_thunder_os_environ(
       "your_email@gmail.com",
       "your_app_password"
   )

   imap.later_init()
   imap.select_mailbox("INBOX")

   for mail in imap.mail_content_list():
       print(mail.get("SUBJECT"))
       print(mail.get("FROM"))
       print(mail.get("TO"))
       print(mail.get("BODY"))

   # 完成後務必關閉連線
   imap.quit()

----

透過 JSON 腳本引擎讀取
-----------------------

**讀取並顯示郵件：**

.. code-block:: json

   {
     "auto_control": [
       ["MT_imap_later_init"],
       ["MT_imap_select_mailbox", {"mailbox": "INBOX", "readonly": true}],
       ["MT_imap_mail_content_list", {"search_str": "UNSEEN"}],
       ["MT_imap_quit"]
     ]
   }

**匯出所有郵件為檔案：**

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
