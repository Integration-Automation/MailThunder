核心郵件 API
============

``Mail`` 是 MailThunder 與供應商無關的 API：不論帳號用的是哪一家供應商，都用同一組呼叫來寄送、
讀取、建立草稿與刪除郵件。以它撰寫的程式不需要知道背後是 SMTP、IMAP 還是 HTTP API。

它使用 :doc:`authentication` 說明的認證資訊，在第一次使用時才連線，之後的呼叫沿用同一條連線；
發生錯誤時會引發例外，而不是只寫入日誌。

.. code-block:: text

   你的程式 / MT_mail_* 動作
              |
            Mail  ---- AttachmentPolicy（寄送前檢查）
              |
        MailProvider
        /          \
   MailSender    MailStore
   (SMTPProvider) (IMAPProvider)
        \          /
     Authentication（密碼、應用程式密碼、XOAUTH2）

----

寄送郵件
--------

.. code-block:: python

   from je_mail_thunder import Mail

   with Mail() as mail:                       # Gmail，或 OAuth2 設定指定的供應商
       mail.send(
           to="receiver@example.com",         # 一個位址、以逗號分隔的多個位址，或清單
           cc=["team@example.com"],
           subject="每夜報表",
           text="42 通過，0 失敗。",
           html="<b>42</b> 通過，0 失敗。",
           attachments=["report.html"],
       )

``send`` 以關鍵字引數接收 ``MailMessage`` 的欄位，也可以直接給一個 ``MailMessage``：

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - 欄位
     - 意義
   * - ``to``、``cc``、``bcc``
     - 收件者：一個位址、以逗號分隔的多個位址，或清單。可以寫成 ``Name <user@host>``。
       ``bcc`` 的收件者會收到郵件，但其他人看不到他們
   * - ``subject``
     - 主旨
   * - ``text``、``html``
     - 純文字與 HTML 內文。兩者都給時，郵件會同時攜帶兩種版本
   * - ``attachments``
     - 檔案路徑，或 ``Attachment`` 物件
   * - ``sender``
     - ``From`` 位址。省略時為帳號的使用者
   * - ``reply_to``
     - 回覆要寄到哪裡
   * - ``headers``
     - 其他標頭，以 dict 表示

回傳值是實際寄出的郵件。

寄送前的檢查
~~~~~~~~~~~~

在任何資料送到伺服器之前：

- 至少要有一位收件者，並且要有寄件者；
- 每個位址都必須有效（``a@example.com; b@example.com`` 會被拒絕：請用逗號分隔）；
- 主旨與標頭的值必須是單行，自訂標頭也不能取代 ``Subject``、``From``、``To``、``Cc``、``Bcc``
  或 MIME 標頭。因此無法透過某個值夾帶第二個標頭；
- 附件必須通過附件政策（:doc:`attachment_policy`）。

沒通過檢查的郵件會引發 ``MailThunderMessageException`` 或 ``MailThunderAttachmentException``，
而且不會寄出。

.. code-block:: python

   from je_mail_thunder import AttachmentPolicy, Mail

   reports_only = AttachmentPolicy(max_file_size=5 * 1024 * 1024, allowed_extensions={"html", "pdf"})
   mail = Mail(policy=reports_only)           # 預設為 25 MiB、任何類型

----

讀取、草稿與刪除
----------------

.. code-block:: python

   from je_mail_thunder import Mail

   with Mail() as mail:
       for message in mail.get_messages(folder="INBOX", limit=10, unread_only=True):
           print(message.message_id, message.sender, message.subject)
           for attachment in message.attachments:
               attachment.save("downloads")    # 寫入的檔名不會離開該目錄

       message = mail.get_message("4321")      # 使用 get_messages 給的 message_id
       draft_id = mail.create_draft(to="receiver@example.com", subject="稍後", text="...")
       mail.delete_message("4321")

- ``get_messages`` 回傳迭代器，最新的郵件在前。郵件在讀取迭代器時才一封一封取回，
  所以不會把整個大信箱放進記憶體。讀取不會把郵件標成已讀。
- ``query`` 接受供應商自己的搜尋語法。透過 IMAP 時是 ``SEARCH`` 條件，
  例如 ``'FROM "ci@example.com" SINCE 1-Oct-2026'`` 或 ``"SUBJECT 報表"``。
- ``message_id`` 是供應商對已儲存郵件的識別碼（透過 IMAP 時是 UID）。
- ``create_draft`` 會像 ``send`` 一樣檢查郵件，再存入草稿匣：先用指定的資料夾，
  其次是帳號的 ``drafts_folder``，最後是伺服器標記為 ``\Drafts`` 的資料夾。
- 資料夾名稱照人讀的樣子寫即可（``"收件匣"``、``"[Gmail]/Sent Mail"``），會自動編碼成伺服器要的格式。

收到的 ``MailMessage`` 有 ``subject``、``sender``、``to``、``cc``、``reply_to``、``date``、
``text``、``html``、``attachments``\ （位元組內容在 ``content``）、``message_id``，
以及放在 ``headers`` 裡的 ``Message-ID``、``In-Reply-To`` 與 ``References`` 標頭。
``to_dict()`` 回傳可直接轉成 JSON 的值。無法解碼的標頭與部分會被略過，不會讓整封郵件讀取失敗。

----

帳號與供應商
------------

.. code-block:: python

   from je_mail_thunder import AppPasswordAuth, Mail, MailAccount, MailServers

   # Microsoft 365，以設定檔或環境變數登入
   Mail(provider="microsoft")

   # Gmail，在程式中提供應用程式密碼
   Mail(provider="gmail", auth=AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop"))

   # 其他任何 SMTP / IMAP 伺服器
   Mail(account=MailAccount(
       provider="smtp",
       auth=AppPasswordAuth("you@example.com", "..."),
       servers=MailServers(smtp_host="smtp.example.com", imap_host="imap.example.com"),
   ))

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - 供應商名稱
     - 寄送方式
     - 讀取方式
   * - ``google``\ （或 ``gmail``）
     - SMTP，``smtp.gmail.com:465``，隱含式 TLS
     - IMAP，``imap.gmail.com``
   * - ``microsoft``
     - SMTP，``smtp.office365.com:587``，STARTTLS
     - IMAP，``outlook.office365.com``
   * - ``microsoft_graph``
     - Microsoft Graph（只能用 OAuth2），見 :doc:`microsoft_graph`
     - Microsoft Graph
   * - ``smtp``
     - 帳號 ``MailServers`` 指定的 SMTP：465 埠的隱含式 TLS，或 ``smtp_starttls=True`` 的 587 埠
     - 帳號 ``MailServers`` 指定的 IMAP

沒有指定供應商名稱時，``Mail()`` 使用 OAuth2 設定指定的供應商（先看 ``auth`` 的設定，
再看設定檔或環境變數），都沒有則使用 Gmail：與 ``smtp_instance``、``imap_instance`` 連線的伺服器相同。
連線一律使用 TLS。

``MailServers`` 另外接受 ``smtp_port`` 與 ``drafts_folder``。

新增供應商
~~~~~~~~~~

後端實作 ``MailSender``\ （``send``）、``MailStore``\ （``get_messages``、``get_message``、
``create_draft``、``delete_message``），或兩者都實作，再以一個名稱註冊。
``Mail`` 與使用它的程式都不需要修改。

.. code-block:: python

   from je_mail_thunder import Mail, MailSender, register_provider

   class LoggingSender(MailSender):
       name = "logging"

       def send(self, message):
           print(f"would send {message.subject!r} to {message.recipients}")

       def close(self):
           pass

   register_provider("logging", lambda account: [LoggingSender()])
   Mail(provider="logging").send(to="a@example.com", sender="me@example.com", subject="Hi", text="...")

工廠函式會收到 ``MailAccount``，並回傳尚未連線的供應商。

----

錯誤
----

每一次失敗都會透過 ``mail_thunder_logger`` 記錄，並以
``je_mail_thunder.utils.exception.exceptions`` 中 ``MailThunderException`` 的子類別引發：

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - 例外
     - 意義
   * - ``MailThunderMessageException``
     - 郵件無法照現在的樣子寄出：沒有收件者、沒有寄件者、位址或標頭無效
   * - ``MailThunderAttachmentException``
     - 附件不存在或違反政策（:doc:`attachment_policy`）
   * - ``MailThunderAuthenticationException``
     - 沒有認證資訊，或伺服器拒絕登入
   * - ``MailThunderConnectionException``
     - 無法連上伺服器，或連線中斷
   * - ``MailThunderSendException``
     - 伺服器拒絕這封郵件，或拒絕其中部分收件者（``refused`` 將每位被拒絕的收件者對應到伺服器的回應）
   * - ``MailThunderProviderException``
     - 上面兩者的基底；未知的供應商、被拒絕的資料夾或未知的郵件識別碼也會引發

.. code-block:: python

   from je_mail_thunder import Mail
   from je_mail_thunder.utils.exception.exceptions import (
       MailThunderAuthenticationException,
       MailThunderException,
       MailThunderSendException,
   )

   try:
       Mail().send(to="receiver@example.com", subject="Report", text="...")
   except MailThunderAuthenticationException:
       print("請檢查認證資訊")
   except MailThunderSendException as error:
       print("被拒絕：", error.refused)
   except MailThunderException as error:
       print("未寄出：", error)

郵件絕不會寄出兩次：寄送途中發生的失敗只會回報，不會重試。閒置時被伺服器中斷的連線，
會在下一次呼叫前重新建立；等待伺服器回應的時間最長為 60 秒。

----

在動作檔中使用
--------------

``MT_mail_*`` 命令在 ``mail_instance`` 上執行，它是一個使用設定檔或環境變數帳號的 ``Mail()``。
這些命令接收並回傳可轉成 JSON 的值，因此也能透過 Socket 伺服器使用。

.. code-block:: json

   {
     "mail_thunder": [
       ["MT_mail_send", {
         "to": "receiver@example.com",
         "subject": "自動化郵件",
         "text": "Hello World!",
         "attachments": ["report.html"]
       }],
       ["MT_mail_get_messages", {"limit": 5, "unread_only": true}],
       ["MT_mail_close"]
     ]
   }

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 命令
     - 引數與結果
   * - ``MT_mail_send``
     - 郵件欄位（``to``、``subject``、``text``、``html``、``cc``、``bcc``、``attachments``、
       ``sender``、``reply_to``、``headers``）。回傳寄出的郵件
   * - ``MT_mail_create_draft``
     - 郵件欄位，另加 ``folder``。回傳草稿的識別碼，或 ``null``
   * - ``MT_mail_get_messages``
     - ``folder``、``limit``、``unread_only``、``query``。回傳郵件清單；資料夾很大時請給 ``limit``
   * - ``MT_mail_get_message``
     - ``message_id``、``folder``。回傳該封郵件
   * - ``MT_mail_delete_message``
     - ``message_id``、``folder``
   * - ``MT_mail_close``
     - 無。關閉連線；下一個命令會重新連線

``mail_instance`` 的附件政策只能從 Python 設定（``mail_instance.policy = ...``），
不能由動作設定，所以動作檔無法放寬它。

----

從 Wrapper 遷移
---------------

``SMTPWrapper``、``IMAPWrapper``、``smtp_instance``、``imap_instance`` 以及 ``MT_smtp_*`` /
``MT_imap_*`` 命令都照舊運作。程式可以一次只搬一個呼叫。

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Wrapper 呼叫
     - ``Mail`` 呼叫
   * - ``smtp.later_init()`` / ``imap.later_init()``
     - 不需要：``Mail`` 會在第一次使用時登入
   * - ``smtp.create_message_and_send(content, settings)``
     - ``mail.send(to=..., subject=..., text=content)``
   * - ``smtp.create_message_with_attach_and_send(content, settings, file, use_html=True)``
     - ``mail.send(to=..., subject=..., html=content, attachments=[file])``
   * - ``imap.select_mailbox("INBOX")`` 之後 ``imap.mail_content_list()``
     - ``mail.get_messages(folder="INBOX")``
   * - ``smtp.quit()`` / ``imap.quit()``
     - ``mail.close()``，或 ``with Mail() as mail:``

兩個輔助函式連接這兩套 API：

.. code-block:: python

   from je_mail_thunder import Mail, legacy_message, mail_from_wrappers, smtp_instance

   # 把 create_message_and_send / create_message_with_attach_and_send 的引數轉成郵件
   message = legacy_message(
       "Hello", {"Subject": "Hi", "From": "me@gmail.com", "To": "you@example.com"},
       attach_file="report.pdf", use_html=False)
   Mail().send(message)

   # 或沿用已經登入的 wrapper，透過它寄送，同時得到 Mail 加上的檢查
   smtp_instance.later_init()
   mail_from_wrappers(smtp=smtp_instance).send(message)

``mail_from_wrappers(smtp=None, imap=None, policy=None)`` 不會接管 wrapper：
關閉 ``Mail`` 不會關閉它們，而且每封郵件都要自己提供 ``sender``。

與 wrapper 的差異：

- wrapper 的方法記錄錯誤後回傳 ``None``，``Mail`` 則會引發例外；
- 郵件至少要有一位有效的收件者，並且要通過上述檢查；
- 讀取不會把郵件標成已讀，``get_messages`` 回傳 ``MailMessage`` 物件，
  而不是 ``{"SUBJECT": ..., "FROM": ..., "TO": ..., "BODY": ...}`` 字典。
