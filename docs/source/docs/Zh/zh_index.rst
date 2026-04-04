總覽
====

**MailThunder** 是一個輕量且靈活的 Python 電子郵件自動化工具，
建構於 Python 標準函式庫的 ``smtplib`` 和 ``imaplib`` 模組之上。

什麼是 MailThunder？
--------------------

MailThunder 封裝了 Python 的 ``smtplib.SMTP_SSL`` 和 ``imaplib.IMAP4_SSL``，
提供更高階的介面來處理常見的電子郵件任務：

- **寄送** 純文字和 HTML 郵件，支援檔案附件，透過 SMTP
- **讀取**、搜尋和匯出郵件，透過 IMAP4
- **自動化** 郵件工作流程，使用 JSON 腳本引擎
- **建立專案** 使用預建模板快速開始
- **遠端控制** 透過 TCP Socket 伺服器控制郵件自動化

架構
----

MailThunder 核心模組架構：

.. code-block:: text

   je_mail_thunder/
     __init__.py              # 公開 API 匯出
     __main__.py              # CLI 進入點 (argparse)
     smtp/
       smtp_wrapper.py        # SMTPWrapper — 繼承 smtplib.SMTP_SSL
     imap/
       imap_wrapper.py        # IMAPWrapper — 繼承 imaplib.IMAP4_SSL
     utils/
       executor/              # JSON 腳本引擎 (Executor 類別)
       file_process/          # 檔案工具 (目錄列表)
       json/                  # JSON 檔案讀寫 (執行緒安全)
       json_format/           # JSON 格式化
       logging/               # 日誌記錄實體 (檔案 + 串流處理器)
       package_manager/       # 動態套件載入器 (PackageManager)
       project/               # 專案模板建立
         template/            # 模板定義 (keyword JSON + executor Python)
       save_mail_user_content/# 認證設定檔 + 環境變數處理
       socket_server/         # TCP Socket 伺服器 (ThreadingMixIn)
       exception/             # 自訂例外類別和錯誤標籤

運作原理
--------

1. **認證**: MailThunder 從目前工作目錄的 ``mail_thunder_content.json`` 讀取認證資訊，
   若找不到則使用 ``mail_thunder_user`` / ``mail_thunder_user_password`` 環境變數。

2. **SMTP (寄送)**: ``SMTPWrapper`` 透過 SSL 連接 SMTP 伺服器 (預設：
   ``smtp.gmail.com:465``)。提供方法來建立 ``EmailMessage`` 或 ``MIMEMultipart``
   物件並一次呼叫完成寄送。

3. **IMAP (讀取)**: ``IMAPWrapper`` 透過 SSL 連接 IMAP 伺服器 (預設：
   ``imap.gmail.com``)。提供方法來選擇信箱、使用 IMAP SEARCH 語法搜尋郵件、
   將結果解析為 Python 字典，以及匯出為檔案。

4. **腳本引擎**: ``Executor`` 類別將命令名稱對映到 Python 可呼叫物件。
   JSON 動作檔包含 ``["command_name", arguments]`` 元組列表，依序執行。
   可在執行期載入自訂函式和整個 Python 套件。

5. **日誌記錄**: 所有操作記錄到 ``Mail_Thunder.log`` (檔案處理器，INFO 級別)
   和 ``stderr`` (串流處理器，WARNING 級別)。

支援平台
--------

- **Python**: 3.9 以上
- **作業系統**: Windows、macOS、Linux
- **相依套件**: 無 (僅使用 Python 標準函式庫)

下一步
------

- :doc:`installation` — 安裝 MailThunder
- :doc:`authentication` — 設定郵件認證
- :doc:`send_google_mail` — 寄送第一封郵件
- :doc:`read_google_mail` — 讀取收件匣郵件
- :doc:`scripting_engine` — 使用 JSON 腳本自動化工作流程
