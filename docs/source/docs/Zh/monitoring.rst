監控：稽核日誌、供應商健康狀態與 Webhook
==========================================

三種監聽者把郵件事件（:doc:`mail_triggers`）變成事後可以查看的資料：稽核日誌、每個供應商的健康報告，
以及對外送出的 webhook。它們都掛在 ``mail.events`` 上，而且都不會讓郵件停下來。

.. code-block:: python

   from je_mail_thunder import AuditLog, Mail, ProviderHealth, WebhookForwarder

   mail = Mail()
   audit = AuditLog()
   health = ProviderHealth()
   audit.attach(mail.events)
   health.attach(mail.events)
   mail.on("*", WebhookForwarder("https://hooks.example.com/mail", secret="shared-secret"))

----

稽核日誌
--------

``AuditLog`` 會為每個事件在檔案中附加一個 JSON 物件：誰在什麼時候寄出或收到了什麼。

.. code-block:: json

   {"timestamp": "2026-10-08T09:30:00+00:00", "event": "message_sent", "provider": "smtp", "folder": "",
    "message_id": null, "internet_message_id": null, "sender": "ci@example.com", "to": ["qa@example.com"],
    "cc": [], "bcc": [], "attachments": [{"filename": "q3.pdf", "content_type": "application/pdf", "size": 48213}],
    "subject": "Q3 report"}

- 它記錄位址、主旨、附件名稱與大小、供應商；失敗時還有錯誤的類型與訊息。
  它不會記錄內文、附件內容或任何認證資訊。
- ``AuditLog(subjects=False)`` 可以不記錄主旨。
- 檔案位於 ``~/.je_mail_thunder/audit/mail_audit.jsonl``，除非以 ``MAIL_THUNDER_AUDIT_FILE`` 或
  ``AuditLog(path)`` 指定其他位置。檔案只會附加，超過 10 MiB 時會被移到 ``<name>.1``。
- ``audit.entries(limit=100)`` 回傳最新的紀錄。
- 檔案無法寫入時只會記錄在日誌中，郵件照常處理。

----

供應商健康狀態
--------------

``ProviderHealth`` 統計每個供應商做了什麼，以及結果如何。

.. code-block:: python

   for status in health.report():
       print(status["provider"], status["state"], status["last_error"])

   health.probe(mail.providers)        # 立刻要求每個供應商連線並登入

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - 狀態
     - 意義
   * - ``unknown``
     - 這個供應商還沒有發生任何事
   * - ``healthy``
     - 最近一次操作成功
   * - ``degraded``
     - 曾經失敗，但連續失敗次數少於 ``failure_threshold``\ （預設 3）
   * - ``down``
     - 連續失敗達到 ``failure_threshold`` 次

每筆狀態還包含 ``successes``、``failures``、``consecutive_failures``、``last_success``、``last_failure`` 與
``last_error``。只有供應商本身的失敗才會計入：登入被拒、連線中斷、伺服器拒絕郵件。
缺少收件者或附件被拒絕是呼叫端的錯誤，不會改變任何狀態。

``probe`` 會呼叫每個供應商的 ``check()``\ （只連線並登入，不寄送也不讀取郵件），並記錄結果。

----

Webhook
-------

``WebhookForwarder`` 是一個事件處理函式，會把每個事件以 JSON POST 到一個 HTTPS 位址。

.. code-block:: python

   forwarder = WebhookForwarder("https://hooks.example.com/mail", secret="shared-secret")
   mail.on("message_failed", forwarder)
   mail.on("message_received", forwarder, filter={"subject": "[ALERT]"})
   ...
   forwarder.close()                   # 送出還在佇列中的事件

- 事件會先進入佇列，再由一條背景執行緒依序送出，所以接收端再慢也不會拖慢 ``send``。
  佇列中有 1000 個事件（``queue_size``）在等待時，新的事件會被丟棄並記錄。
- 內容是事件的 ``to_dict()``，不含郵件內文；``bodies=True`` 才會包含。附件只有描述，不會包含內容。
- 有 ``secret`` 時，每個請求都帶有 ``X-MailThunder-Signature: sha256=<內容的 HMAC-SHA256>``。
  接收端對原始內容計算同樣的值再比對；``X-MailThunder-Event`` 是事件名稱。
- 只接受 ``https`` 位址。接收端回應錯誤狀態時會被記錄。

在接收端檢查簽章：

.. code-block:: python

   import hashlib
   import hmac

   def is_from_mail_thunder(secret: str, body: bytes, signature_header: str) -> bool:
       expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
       return hmac.compare_digest(expected, signature_header)
