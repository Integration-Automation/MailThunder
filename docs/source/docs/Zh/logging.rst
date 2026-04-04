日誌記錄
========

MailThunder 使用 Python 標準 ``logging`` 模組記錄所有操作。
日誌對於除錯認證問題、追蹤寄送/接收的郵件以及監控腳本執行器非常有用。

----

日誌記錄器設定
--------------

日誌記錄器在 ``je_mail_thunder.utils.logging.loggin_instance`` 中設定：

.. code-block:: python

   import logging
   import sys

   mail_thunder_logger = logging.getLogger("Mail Thunder")
   mail_thunder_logger.setLevel(logging.INFO)

**記錄器名稱：** ``"Mail Thunder"``

----

日誌處理器
----------

MailThunder 註冊兩個日誌處理器：

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - 處理器
     - 輸出
     - 級別
     - 說明
   * - 檔案處理器
     - ``Mail_Thunder.log``
     - ``INFO``
     - 將所有操作（INFO 以上）記錄到目前工作目錄的檔案
   * - 串流處理器
     - ``stderr``
     - ``WARNING``
     - 僅將警告和錯誤印出到主控台

**日誌格式：**

.. code-block:: text

   %(asctime)s | %(name)s | %(levelname)s | %(message)s

**日誌範例：**

.. code-block:: text

   2025-01-15 10:30:00,123 | Mail Thunder | INFO | MT_smtp_later_init
   2025-01-15 10:30:01,456 | Mail Thunder | INFO | smtp_create_message_and_send, message_content: Hello!, ...
   2025-01-15 10:30:01,789 | Mail Thunder | INFO | SMTP quit
   2025-01-15 10:30:02,012 | Mail Thunder | ERROR | smtp_try_to_login_with_env_or_content, failed: ...

----

記錄的內容
----------

**SMTP 操作 (INFO 級別)：**

- ``MT_smtp_later_init`` — SMTP 登入嘗試
- ``smtp_create_message`` — 訊息建立，包含內容和設定
- ``smtp_create_message_with_attach`` — 附件訊息建立
- ``smtp_create_message_and_send`` — 寄送，包含內容詳情
- ``smtp_create_message_with_attach_and_send`` — 附件寄送詳情
- ``smtp_try_to_login_with_env_or_content`` — 登入嘗試
- ``SMTP quit`` — 斷開連線

**IMAP 操作 (INFO 級別)：**

- ``MT_imap_later_init`` — IMAP 登入嘗試
- ``imap_try_to_login_with_env_or_content`` — 登入嘗試
- ``imap_select_mailbox`` — 信箱選擇，包含名稱和唯讀旗標
- ``imap_search_mailbox`` — 搜尋條件
- ``imap_mail_content_list`` — 內容列表擷取
- ``MT_imap_quit`` — 斷開連線

**執行器操作 (INFO 級別)：**

- ``Execute {action}`` — 每個動作執行時
- ``Add command to executor {command_dict}`` — 自訂命令註冊

**套件管理器操作 (INFO 級別)：**

- ``add_package_to_executor, package: {package}`` — 套件載入

**錯誤記錄 (ERROR 級別)：**

SMTP、IMAP、執行器和套件管理器中的所有例外都被捕獲並以 ERROR 級別記錄，
包含完整的例外表示。

----

日誌檔位置
----------

日誌檔 ``Mail_Thunder.log`` 在模組首次匯入時於 **目前工作目錄** 建立。
檔案以 ``w+`` 模式開啟，��示每次程式執行時會被覆寫。

.. note::

   由於檔案處理器使用 ``mode="w+"``，先前執行的日誌不會被保留。
   若需要持久化日誌，請考慮設定自訂處理器或在每次執行後複製日誌檔。

----

存取日誌記錄器
--------------

您可以存取 MailThunder 的日誌記錄器來新增自訂處理器或變更級別：

.. code-block:: python

   from je_mail_thunder.utils.logging.loggin_instance import mail_thunder_logger
   import logging

   # 變更日誌級別
   mail_thunder_logger.setLevel(logging.DEBUG)

   # 新增自訂處理器
   custom_handler = logging.StreamHandler()
   custom_handler.setLevel(logging.DEBUG)
   mail_thunder_logger.addHandler(custom_handler)

   # 現在所有除錯訊息都會被印出
