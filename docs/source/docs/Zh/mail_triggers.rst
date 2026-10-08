郵件事件與觸發器
================

``Mail`` 會把郵件發生的事情以事件回報，不論供應商是哪一家都用同一套名稱；
觸發器後端則負責監看資料夾，讓新郵件也成為事件。

.. code-block:: python

   from je_mail_thunder import Mail

   mail = Mail()

   def handle_report(event):
       print("收到新報表", event.message.sender, event.message.subject)

   mail.on("message_received", handle_report, filter={"subject": "[TEST]", "has_attachments": True})
   mail.watch("INBOX")          # 在背景執行緒每 60 秒查看一次
   ...
   mail.close()                 # 停止監看並關閉連線

----

事件
----

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - 事件
     - 發生時機
   * - ``message_received``
     - 被監看的資料夾有新郵件
   * - ``attachment_received``
     - 新郵件的每個附件各一次
   * - ``message_sent``
     - ``send`` 已把郵件交給供應商
   * - ``message_failed``
     - ``send`` 或 ``create_draft`` 失敗，不論原因
   * - ``attachment_rejected``
     - 附件不存在或違反附件政策
   * - ``authentication_failed``
     - 沒有認證資訊，或伺服器拒絕登入
   * - ``connection_failed``
     - 無法連上伺服器，或連線中斷

失敗仍然會以例外回報給呼叫端；事件是讓其他程式得知這件事的方式。
寄送失敗時會先發出原因事件，再發出 ``message_failed``。``"*"`` 可以訂閱所有事件。

處理函式會收到一個 ``MailEvent``：

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - 屬性
     - 內容
   * - ``name``
     - 事件名稱
   * - ``message``
     - 相關的 ``MailMessage``\ （如果有）
   * - ``attachment``
     - ``attachment_received`` 事件的 ``Attachment``
   * - ``error``
     - 造成失敗的例外
   * - ``provider``、``folder``
     - 供應商名稱；收到的郵件還有所在的資料夾
   * - ``timestamp``、``metadata``
     - 發生時間（UTC），以及事件來源知道的其他資訊
   * - ``to_dict()``
     - 可轉成 JSON 的事件內容

處理函式引發的例外會被記錄，不會中斷其他處理函式，也不會中斷原本的操作。

----

訂閱
----

.. code-block:: python

   subscription = mail.on("message_failed", notify_team)
   mail.events.off(subscription)

   @mail.on("attachment_received", filter={"attachment_type": "pdf"})
   def save_report(event):
       event.attachment.save("reports")

``filter`` 可以是規則的 mapping、接收事件的函式，或 ``MailFilter``。每一條規則都符合時，事件才會通過：

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 規則
     - 符合條件
   * - ``sender``
     - 寄件者位址包含該文字
   * - ``recipient``
     - ``to`` / ``cc`` / ``bcc`` 其中一個位址包含該文字
   * - ``subject``、``body``
     - 主旨，或純文字／HTML 內文包含該文字
   * - ``has_attachments``
     - 郵件有附件（``True``）或沒有附件（``False``）
   * - ``attachment_type``
     - 其中一個附件是該副檔名（``"pdf"``）或該 MIME 類型（``"image/*"``）
   * - ``since``、``until``
     - 郵件日期在範圍內
   * - ``metadata``
     - 事件的 metadata 包含這些值
   * - ``predicate``
     - 函式對該事件回傳 true

文字規則不分大小寫，在欄位的任何位置比對；編譯過的正規表示式則以 ``search`` 套用。

----

監看資料夾
----------

.. code-block:: python

   mail.watch("INBOX", interval=30)            # 每 30 秒詢問一次
   mail.watch("INBOX", idle=True)              # IMAP IDLE：有新郵件時由伺服器通知
   backend = mail.watch("Reports", start=False)
   mail.triggers.poll()                        # 只查看一次，例如從排程工作呼叫

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 選項
     - 意義
   * - ``folder``
     - 要監看的資料夾（``"INBOX"``）
   * - ``idle``
     - 等待伺服器通知，而不是定時詢問。供應商必須支援（IMAP）
   * - ``start``
     - 從現在起在 daemon 執行緒上監看（``True``），或只在呼叫 ``mail.triggers.poll()`` 時查看
   * - ``interval``
     - 兩次查看之間的秒數（60）；使用 ``idle`` 時是單次 IDLE 的最長時間（300）
   * - ``include_existing``
     - 連已經存在的郵件也回報。預設第一次查看只會記下它們
   * - ``batch_limit``
     - 每次查看讀取的郵件數（50）。兩次查看之間若有更多郵件到達，超出的部分會被漏掉

監看使用自己的連線，所以不會妨礙 ``send`` 或 ``get_messages``。查看失敗時會被記錄；
若屬於 ``authentication_failed`` 或 ``connection_failed`` 就發出對應事件，並在 30 秒後重試。

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 後端
     - 如何發現新郵件
   * - ``PollingBackend``
     - 向任何 ``MailStore`` 詢問最新的郵件，回報還沒看過的
   * - ``IMAPPollingBackend``
     - 同上，但第一次查看之後只搜尋 ``UID <last + 1>:*``
   * - ``IMAPIdleBackend``
     - 兩次查看之間以 IMAP ``IDLE``\ （RFC 2177）等待；伺服器不支援 ``IDLE`` 時改為睡眠等待

``mail.triggers`` 保存這些後端（``backends``、``add``、``remove``、``poll``、``start``、``stop``）。
自訂後端繼承 ``MailTriggerBackend`` 並實作 ``poll()``；``je_mail_thunder.triggers.factory`` 的
``register_backends(store_class, polling, push)`` 可以告訴 ``Mail.watch`` 哪一種供應商由哪個後端監看。

----

在動作檔中使用
--------------

動作檔無法註冊處理函式，但可以詢問有什麼新郵件：

.. code-block:: json

   {
     "mail_thunder": [
       ["MT_mail_poll", {"folder": "INBOX"}]
     ]
   }

對同一個資料夾的第一次 ``MT_mail_poll`` 只會記下目前的郵件並回傳空清單；之後每一次
都回傳上一次以來的 ``message_received`` 與 ``attachment_received`` 事件。
